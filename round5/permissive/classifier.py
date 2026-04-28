"""Multi-flag classifier (round-5 permissive pipeline).

Computes 5 independent flags per product (MR, MOM, MM, OBI, PAIR). Each flag
is OR-gated across multiple statistical arms — a product is MR-flagged if
ANY of {vr_p arm, acf_p arm, hurst arm, broader-IC arm} fires. This is
deliberately less discriminant than the legacy priority-ordered classifier
in ``round5/archetypes.py``, which routes to NO_EDGE whenever the narrow
``IC[neg_zscore_mid_50]`` cell fails to FDR-pass.

Input:
  - stats_row         : dict from ``stats_per_product.csv``
  - ic_for_product    : long-form IC frame (one row per signal, columns
                        ``ic_h{h}/n_h{h}/t_h{h}/p_h{h}/significant``)
  - corr_mid          : 5×5 family corr matrix (DataFrame, indexed by product)
  - coint_df          : long-form Engle-Granger pairs frame
                        (columns: ``a, b, coint_t, coint_p``)
  - gates             : ``Gates`` dataclass (single source of truth)

Output: dict with keys
  - flags             : 5 bool flags
  - scores_inputs     : raw stats needed for downstream per-family scoring
  - pair_info         : {pair_partner, pair_corr, pair_coint_p}
  - obi_info          : {obi_signal, obi_horizon, obi_ic}
  - segments          : per-flag rationale segments (None when flag didn't fire)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from round5.significance import (
    bartlett_acf_p,
    best_significant_ic,
    vr_p_value,
)


# Signed MR signal set: positive sign means raw IC ≥ threshold counts as MR;
# negative sign means raw IC ≤ -threshold counts as MR (continuation-fade).
MR_SIGNALS_SIGNED: dict[str, int] = {
    "neg_zscore_mid_50": +1,
    "neg_spread":        +1,
    "momentum_10":       -1,
    "trade_imbalance":   -1,
}

OBI_SIGNALS = ("obi_l1", "obi_l3")
OBI_HORIZONS = (1, 10)

ALL_HORIZONS = (1, 10, 100, 1000)
SHORT_HORIZONS = (1, 10)


@dataclass(frozen=True)
class Gates:
    # MR_FLAG arms
    mr_vr_max: float = 0.97
    mr_vr_p_max: float = 0.05
    mr_acf1_max: float = -0.01
    mr_acf_p_max: float = 0.05
    mr_hurst_max: float = 0.51
    mr_ic_min: float = 0.02

    # MOM_FLAG arms
    mom_vr_min: float = 1.005
    mom_vr_p_max: float = 0.05
    mom_hurst_min: float = 0.55
    mom_ic_min: float = 0.02

    # MM_FLAG (6-condition AND)
    mm_vr_dev_max: float = 0.05
    mm_hurst_dev_max: float = 0.05
    mm_acf1_max_abs: float = 0.05
    mm_short_ic_max: float = 0.05
    mm_spread_to_std_min: float = 1.5
    mm_lim10_sat_min: float = 0.3

    # OBI_FLAG
    obi_ic_min: float = 0.04

    # PAIR_FLAG (two-tier; either lane suffices)
    #   - Strong-corr lane: |corr| >= pair_corr_strong, no coint test required
    #     (Engle-Granger loses power on short series; very high correlation
    #     is suggestive on its own)
    #   - Cointegration lane: coint_p < pair_coint_p_max, regardless of |corr|
    #     (a cointegrated pair with moderate correlation is just as tradeable
    #     as one with high correlation; cointegration is the stronger
    #     statistical statement)
    pair_corr_strong: float = 0.7
    pair_coint_p_max: float = 0.10

    # Per-family ranking
    top_k_per_axis: int = 2

    # Significance
    fdr_alpha: float = 0.05


def _coint_lookup(coint_df: pd.DataFrame) -> dict[tuple[str, str], float]:
    """Symmetric (a,b) -> coint_p lookup."""
    if coint_df is None or coint_df.empty:
        return {}
    out: dict[tuple[str, str], float] = {}
    for _, r in coint_df.iterrows():
        a, b = r["a"], r["b"]
        p = float(r["coint_p"]) if pd.notna(r["coint_p"]) else float("nan")
        out[(a, b)] = p
        out[(b, a)] = p
    return out


def best_pair_partner(
    product: str,
    corr_mid: pd.DataFrame,
    coint_df: pd.DataFrame,
    gates: Gates,
) -> Optional[tuple[str, float, float]]:
    """Best within-family partner under the two-tier pair gate.

    Strong-corr lane: |corr| >= pair_corr_strong passes alone. Cointegration
    lane: coint_p < pair_coint_p_max passes alone. A partner satisfying
    either lane is admissible. Returns the candidate with strongest |corr|.
    """
    if corr_mid is None or corr_mid.empty or product not in corr_mid.index:
        return None
    coint_pair = _coint_lookup(coint_df)
    row = corr_mid.loc[product].drop(product, errors="ignore")
    candidates: list[tuple[str, float, float]] = []
    for partner, c in row.items():
        if not np.isfinite(c):
            continue
        ac = abs(float(c))
        cp = coint_pair.get((product, partner), float("nan"))
        passes_strong = ac >= gates.pair_corr_strong
        passes_coint = np.isfinite(cp) and cp < gates.pair_coint_p_max
        if not (passes_strong or passes_coint):
            continue
        candidates.append((partner, float(c), float(cp) if np.isfinite(cp) else float("nan")))
    if not candidates:
        return None
    candidates.sort(key=lambda t: abs(t[1]), reverse=True)
    return candidates[0]


def best_mr_signal_ic(ic_for_product: Optional[pd.DataFrame], alpha: float) -> dict:
    """Best signed-MR IC across MR_SIGNALS_SIGNED.

    Each candidate's IC is multiplied by the signal's MR sign convention; we
    keep only positive products (i.e. genuinely MR-flavoured). Returns the
    same dict shape as ``best_significant_ic`` plus ``signed_ic`` (always
    positive when valid) and ``raw_ic``.
    """
    out_default = {
        "ic": float("nan"), "raw_ic": float("nan"), "signed_ic": float("nan"),
        "signal": None, "horizon": None,
        "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False,
        "sign": 0,
    }
    if ic_for_product is None or ic_for_product.empty:
        return out_default
    candidates: list[dict] = []
    for sig, sign in MR_SIGNALS_SIGNED.items():
        c = best_significant_ic(ic_for_product, signal=sig, alpha=alpha)
        if not c.get("passes_fdr") or pd.isna(c.get("ic")):
            continue
        signed = sign * float(c["ic"])
        if signed <= 0:
            continue
        c2 = dict(c)
        c2["raw_ic"] = float(c["ic"])
        c2["signed_ic"] = float(signed)
        c2["sign"] = int(sign)
        candidates.append(c2)
    if not candidates:
        return out_default
    return max(candidates, key=lambda c: c["signed_ic"])


def best_mom_signal_ic(ic_for_product: Optional[pd.DataFrame], alpha: float) -> dict:
    """Best FDR-pass IC[momentum_10] with positive sign."""
    out_default = {
        "ic": float("nan"), "signal": "momentum_10", "horizon": None,
        "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False,
    }
    c = best_significant_ic(ic_for_product, signal="momentum_10", alpha=alpha)
    if not c.get("passes_fdr") or pd.isna(c.get("ic")) or float(c["ic"]) <= 0:
        return out_default
    return c


def best_obi_signal_ic(ic_for_product: Optional[pd.DataFrame], alpha: float) -> dict:
    """Best FDR-pass IC across OBI_SIGNALS at OBI_HORIZONS, positive sign."""
    out_default = {
        "ic": float("nan"), "signal": None, "horizon": None,
        "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False,
    }
    candidates = []
    for s in OBI_SIGNALS:
        c = best_significant_ic(ic_for_product, signal=s, horizons=OBI_HORIZONS, alpha=alpha)
        if c.get("passes_fdr") and pd.notna(c.get("ic")) and float(c["ic"]) > 0:
            candidates.append(c)
    if not candidates:
        return out_default
    return max(candidates, key=lambda c: abs(c["ic"]))


def _short_horizon_ic_basis(ic_for_product: Optional[pd.DataFrame], alpha: float) -> dict:
    """Best short-horizon IC across all signals (for MM no-predictability check)."""
    return best_significant_ic(ic_for_product, horizons=SHORT_HORIZONS, alpha=alpha)


def compute_flags(
    stats_row: dict,
    ic_for_product: Optional[pd.DataFrame],
    corr_mid: pd.DataFrame,
    coint_df: pd.DataFrame,
    gates: Gates = Gates(),
) -> dict:
    p = stats_row["product"]
    vr = float(stats_row.get("vr_k5", np.nan))
    vr_z = float(stats_row.get("vr_z_k5", np.nan))
    hurst = float(stats_row.get("hurst", np.nan))
    acf1 = float(stats_row.get("acf_ret1_lag1", np.nan))
    ret1_std = float(stats_row.get("ret1_std", np.nan))
    n_ticks = int(stats_row.get("n_ticks", 0) or 0)
    spread_med = float(stats_row.get("spread_median", np.nan))
    lim10_sat = float(stats_row.get("limit10_saturation", np.nan))

    vr_p = vr_p_value(vr_z) if pd.notna(vr_z) else float("nan")
    acf1_p = bartlett_acf_p(acf1, n_ticks) if pd.notna(acf1) else float("nan")

    best_mr = best_mr_signal_ic(ic_for_product, alpha=gates.fdr_alpha)
    best_mom = best_mom_signal_ic(ic_for_product, alpha=gates.fdr_alpha)
    best_obi = best_obi_signal_ic(ic_for_product, alpha=gates.fdr_alpha)
    best_short = _short_horizon_ic_basis(ic_for_product, alpha=gates.fdr_alpha)

    # ---- MR_FLAG ----
    mr_arms: list[str] = []
    if np.isfinite(vr) and vr < gates.mr_vr_max and np.isfinite(vr_p) and vr_p < gates.mr_vr_p_max:
        mr_arms.append(f"vr_k5={vr:.3f}<{gates.mr_vr_max} (z={vr_z:+.2f}, p={vr_p:.3g})")
    if np.isfinite(acf1) and acf1 < gates.mr_acf1_max and np.isfinite(acf1_p) and acf1_p < gates.mr_acf_p_max:
        mr_arms.append(f"acf1={acf1:+.3f}<{gates.mr_acf1_max} (Bartlett p={acf1_p:.3g})")
    if np.isfinite(hurst) and hurst < gates.mr_hurst_max:
        mr_arms.append(f"hurst={hurst:.2f}<{gates.mr_hurst_max} (informational)")
    mr_ic_signed = float(best_mr.get("signed_ic", np.nan))
    if pd.notna(mr_ic_signed) and mr_ic_signed >= gates.mr_ic_min:
        mr_arms.append(
            f"IC[{best_mr['signal']}]={best_mr['raw_ic']:+.3f} @ h={best_mr['horizon']} "
            f"(sign={best_mr['sign']:+d}, t={best_mr['t']:+.2f}, p={best_mr['p']:.3g}, FDR-pass)"
        )
    mr_flag = bool(mr_arms)
    mr_segment = f"[MR] " + " | ".join(mr_arms) if mr_flag else None

    # ---- MOM_FLAG ----
    mom_arms: list[str] = []
    if np.isfinite(vr) and vr > gates.mom_vr_min and np.isfinite(vr_p) and vr_p < gates.mom_vr_p_max:
        mom_arms.append(f"vr_k5={vr:.3f}>{gates.mom_vr_min} (z={vr_z:+.2f}, p={vr_p:.3g})")
    if np.isfinite(hurst) and hurst > gates.mom_hurst_min:
        mom_arms.append(f"hurst={hurst:.2f}>{gates.mom_hurst_min}")
    mom_ic = float(best_mom.get("ic", np.nan))
    if best_mom.get("passes_fdr") and pd.notna(mom_ic) and mom_ic >= gates.mom_ic_min:
        mom_arms.append(
            f"IC[momentum_10]={mom_ic:+.3f} @ h={best_mom['horizon']} "
            f"(t={best_mom['t']:+.2f}, p={best_mom['p']:.3g}, FDR-pass)"
        )
    mom_flag = bool(mom_arms)
    mom_segment = f"[MOM] " + " | ".join(mom_arms) if mom_flag else None

    # ---- MM_FLAG (6-condition AND, no sim) ----
    short_ic_passes_fdr = bool(best_short.get("passes_fdr", False))
    short_ic_abs = abs(float(best_short.get("ic", np.nan))) if pd.notna(best_short.get("ic")) else float("nan")
    mm_checks = [
        np.isfinite(vr) and abs(vr - 1.0) < gates.mm_vr_dev_max,
        np.isfinite(hurst) and abs(hurst - 0.5) < gates.mm_hurst_dev_max,
        np.isfinite(acf1) and abs(acf1) < gates.mm_acf1_max_abs,
        (not short_ic_passes_fdr) or (pd.notna(short_ic_abs) and short_ic_abs < gates.mm_short_ic_max),
        (np.isfinite(spread_med) and np.isfinite(ret1_std) and ret1_std > 0
         and spread_med / ret1_std >= gates.mm_spread_to_std_min),
        np.isfinite(lim10_sat) and lim10_sat >= gates.mm_lim10_sat_min,
    ]
    mm_flag = bool(all(mm_checks))
    mm_segment: Optional[str]
    if mm_flag:
        spread_to_std = spread_med / ret1_std if (np.isfinite(spread_med) and np.isfinite(ret1_std) and ret1_std > 0) else float("nan")
        mm_segment = (
            f"[MM] |vr-1|={abs(vr-1):.3f} | |hurst-0.5|={abs(hurst-0.5):.3f} | "
            f"|acf1|={abs(acf1):.3f} | spread/std={spread_to_std:.2f} | lim10_sat={lim10_sat:.2f}"
        )
    else:
        mm_segment = None

    # ---- OBI_FLAG ----
    obi_ic = float(best_obi.get("ic", np.nan))
    obi_flag = bool(best_obi.get("passes_fdr") and pd.notna(obi_ic) and obi_ic >= gates.obi_ic_min)
    obi_segment = (
        f"[OBI] IC[{best_obi['signal']}]={obi_ic:+.3f} @ h={best_obi['horizon']} "
        f"(t={best_obi['t']:+.2f}, p={best_obi['p']:.3g}, FDR-pass)"
    ) if obi_flag else None

    # ---- PAIR_FLAG ----
    pair = best_pair_partner(p, corr_mid, coint_df, gates)
    if pair is not None:
        pair_partner, pair_corr, pair_coint_p = pair
        pair_flag = True
        pair_segment = (
            f"[PAIR] partner={pair_partner} corr={pair_corr:+.2f} coint_p={pair_coint_p:.3g}"
        )
    else:
        pair_partner = None
        pair_corr = float("nan")
        pair_coint_p = float("nan")
        pair_flag = False
        pair_segment = None

    # ---- Pair-score input: max within-family corr (for ranking even when gate fails) ----
    if corr_mid is not None and not corr_mid.empty and p in corr_mid.index:
        row_corr = corr_mid.loc[p].drop(p, errors="ignore")
        max_within_corr = float(row_corr.abs().max()) if not row_corr.empty else float("nan")
    else:
        max_within_corr = float("nan")
    coint_pair = _coint_lookup(coint_df)
    coint_ps = [coint_pair.get((p, q), np.nan) for q in (corr_mid.index if corr_mid is not None else [])
                if q != p and (p, q) in coint_pair]
    coint_ps = [x for x in coint_ps if pd.notna(x)]
    min_coint_p = float(min(coint_ps)) if coint_ps else float("nan")

    return {
        "product": p,
        "flags": {
            "mr_flag": mr_flag,
            "mom_flag": mom_flag,
            "mm_flag": mm_flag,
            "obi_flag": obi_flag,
            "pair_flag": pair_flag,
        },
        "scores_inputs": {
            "vr_k5": vr,
            "acf1": acf1,
            "hurst": hurst,
            "best_mr_ic_signed": float(mr_ic_signed) if pd.notna(mr_ic_signed) else 0.0,
            "best_mom_ic": float(mom_ic) if pd.notna(mom_ic) else 0.0,
            "best_obi_ic_abs": float(abs(obi_ic)) if pd.notna(obi_ic) else 0.0,
            "best_obi_ic_passes_fdr": bool(best_obi.get("passes_fdr", False)),
            "spread_med_over_std": (spread_med / ret1_std) if (np.isfinite(spread_med) and np.isfinite(ret1_std) and ret1_std > 0) else float("nan"),
            "lim10_sat": lim10_sat,
            "max_within_corr": max_within_corr,
            "min_coint_p": min_coint_p,
        },
        "pair_info": {
            "pair_partner": pair_partner,
            "pair_corr": pair_corr,
            "pair_coint_p": pair_coint_p,
        },
        "obi_info": {
            "obi_signal": best_obi.get("signal") if obi_flag else None,
            "obi_horizon": int(best_obi.get("horizon") or 0) if obi_flag else 0,
            "obi_ic": float(obi_ic) if obi_flag else float("nan"),
        },
        "segments": {
            "mr": mr_segment,
            "mom": mom_segment,
            "mm": mm_segment,
            "obi": obi_segment,
            "pair": pair_segment,
        },
    }
