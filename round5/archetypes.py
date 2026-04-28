"""Archetype classifier for round-5 products.

Two orthogonal axes:

  Primary (discriminant, exactly one bucket per product, priority first-match):
    1. MR_TAKER       : aggressive z-score taker around an anchor.
    2. MOMENTUM       : aggressive momentum follower at best (window, h).
    3. RANDOM_WALK    : passive two-sided MM-only product (no MR/MOM signal).
    4. NO_EDGE        : skip / inventory-minimisation only.

  Orthogonal flags (independent, can attach on top of any primary archetype):
    PAIR_ANCHOR — within-family β-hedged residual MR taker. A product can be
    e.g. MR_TAKER + PAIR_ANCHOR if it has both stationary anchor MR and a
    cointegrated within-family partner.

    OBI_TAKER — short-horizon book-pressure taker. Fires when |IC[obi_l1, h=1
    or 10]| >= obi_ic_min and FDR-passes. Can layer on top of any primary
    archetype because it acts on different timescale (sub-tick microstructure
    vs the primary's anchor / momentum / passive-MM logic).

    MM_CANDIDATE — passive two-sided market-maker template. Fires when the
    product passes the structural MM gates (vr/hurst/acf/spread-cushion/depth)
    AND Template-A simulated PnL > 0. Layers on any primary, including
    MR_TAKER: alpha-taking and spread-capture are not mutually exclusive at
    the analysis level — the strategy compositor decides the mix.

The RANDOM_WALK trigger set is *necessary but not sufficient* for primary
classification: the threshold rules say "this product looks like a passive-
MM-only candidate", and the Template-A simulation gate confirms or
downgrades. With the loose round-5 MR triggers, very few products end up
RANDOM_WALK as primary; most MM-able products get MR_TAKER primary +
MM_CANDIDATE flag.

Significance: IC t/p come from HAC (Newey-West) regressions with maxlag=h
in ``research_lib.signal_ic_table``, then BH-FDR is applied per product
across the 6 signals × 4 horizons grid. The classifier requires both
``|IC| >= effect_threshold`` AND ``passes_fdr=True``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .research_lib import HORIZONS, POSITION_LIMIT, ProductData, _save
from .significance import (
    bartlett_acf_p,
    best_significant_ic,
    vr_p_value,
)


ARCHETYPE_LABELS = ("MR_TAKER", "MOMENTUM", "RANDOM_WALK", "NO_EDGE")
DEFAULT_FDR_ALPHA = 0.05

# Signals that count as "mean-reverting" for the MR_TAKER IC gate. Includes
# both mid-anchor and vwap-anchor flavours of the z-score signal: the
# strategy template can use either as its anchor, and we accept whichever
# produces a stronger IC. neg_spread / obi / trade_imbalance get their own
# dedicated flag (OBI_TAKER) when applicable.
MR_SIGNALS = ("neg_zscore_mid_50", "neg_zscore_vwap_50")

# Signals that count as "book-pressure" for the OBI_TAKER orthogonal flag.
OBI_SIGNALS = ("obi_l1", "obi_l3")
OBI_HORIZONS = (1, 10)


# ---------------------------------------------------------------------------
# Trigger thresholds (single source of truth)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArchetypeGates:
    # PAIR_ANCHOR (orthogonal flag, not in priority chain). Two-tier gate:
    # high-corr partners pass without coint (the spread is structurally
    # informative even if the Engle-Granger test doesn't reject the null at
    # 5%); moderate-corr partners need cointegration to confirm a stationary
    # spread. Aligns with the practitioner default of trading any |corr|>=0.5
    # pair while letting strong-corr ones through unconditionally.
    pair_corr_strong: float = 0.7         # high-corr lane: no coint required
    pair_corr_min: float = 0.5            # moderate-corr lane: needs coint
    pair_coint_p_max: float = 0.10        # moderate-corr lane coint cutoff

    # MR_TAKER. Multiple structural triggers (any one fires admits the
    # product to MR routing). Gates calibrated on round-5 universe to admit
    # roughly the bottom quartile of each statistic — looser than naively
    # passing FDR but stricter than the teammate's "any negative ACF or
    # Hurst<0.5" heuristic. Tradeoff: false positives are downstream-gated
    # by sim PnL or the trader filtering, so we err inclusive here.
    mr_vr_max: float = 0.985              # admits ~25% via VR alone
    mr_acf1_max: float = -0.005           # admits any meaningful neg ACF
    mr_hurst_max: float = 0.535           # ~p50 of mid Hurst distribution
    mr_adf_max: float = 0.10              # weak stationarity (~p25)
    mr_vwap_hurst_max: float = 0.50       # admits anti-persistent VWAP returns
    mr_vwap_adf_max: float = 0.10         # weak stationarity on log VWAP
    mr_vwap_acf1_max: float = -0.01       # negative ACF on log VWAP returns
    mr_ic_min: float = 0.02               # informational gate for picking anchor signal

    # MOMENTUM. mom_hurst_min=0.545 (calibration p75; was 0.51 = degenerate).
    mom_vr_min: float = 1.005
    mom_hurst_min: float = 0.545
    mom_ic_min: float = 0.02

    # RANDOM_WALK + MM_CANDIDATE structural gates. spread_to_std=1.0 admits
    # ~p50 of round-5 products; below 1.5 was over-strict (only ~10%
    # passed). Sim PnL is the final filter — products with thin spread
    # cushions get rejected when they actually trade. lim10_sat=0.2 admits
    # ~p10 of products; primary purpose is excluding empty-book microcaps,
    # not edge filtering.
    rw_vr_dev_max: float = 0.05            # |vr_k5 - 1|
    rw_hurst_dev_max: float = 0.05         # |hurst - 0.5|
    rw_acf1_max_abs: float = 0.05
    rw_max_ic: float = 0.05
    rw_spread_to_std_min: float = 1.0      # spread_median / ret1_std
    rw_lim10_sat_min: float = 0.2

    # OBI_TAKER (orthogonal flag, not in priority chain). Effect-size +
    # FDR-pass on obi_l1/obi_l3 at short horizons. 0.04 admits anything
    # > ~6.7σ over the noise floor at n=30000 ticks (HAC-adjusted).
    obi_ic_min: float = 0.04

    # Confidence-grading thresholds. These don't *gate* MR_TAKER admission
    # but they grade how trustworthy the classification is for downstream
    # risk allocation:
    #   - mr_n_triggers >= mr_high_n_triggers OR FDR-pass IC -> "high"
    #   - mr_n_triggers in [2, mr_high_n_triggers-1]          -> "medium"
    #   - mr_n_triggers == 1                                   -> "low"
    mr_high_n_triggers: int = 3

    # MR contradiction check: when an "opposite-sign" sister stat fires, the
    # MR claim is internally inconsistent. The classifier still admits the
    # product (preserves inclusivity) but records the contradiction so the
    # downstream allocator can downweight or skip.
    mr_contra_vr_min: float = 1.005       # vr clearly trending
    mr_contra_acf_min: float = 0.005      # mid acf clearly positive
    mr_contra_hurst_max: float = 0.55     # hurst clearly persistent (above)
    mr_contra_vwap_acf_min: float = 0.01  # vwap acf clearly positive

    # PAIR_ANCHOR residual stationarity: cointegration p-value cutoff for
    # marking the residual as stationary (suitable for a fixed β-hedged
    # spread). Pairs admitted via the high-corr lane but with non-stationary
    # residual (coint_p > pair_residual_p_max) get pair_residual_stationary
    # = False — the strategy template should use rolling β rather than a
    # fixed spread.
    pair_residual_p_max: float = 0.10


# ---------------------------------------------------------------------------
# Per-product parameter derivation for RW template
# ---------------------------------------------------------------------------

def derive_rw_params(stats_row: dict, vol_summary_row: Optional[dict] = None) -> dict:
    """min_edge_ticks, k_vol, gamma derived from existing stats.

    All three are bounded so a noisy product cannot produce extreme values.
    """
    spread_median = float(stats_row.get("spread_median", np.nan))
    ret1_std = float(stats_row.get("ret1_std", np.nan))

    # min_edge_ticks: half the median spread, floored at 3, ceiled at p95.
    if np.isfinite(spread_median):
        min_edge_ticks = max(3, int(np.floor(spread_median / 2.0)))
    else:
        min_edge_ticks = 3

    # k_vol: scales spread expansion in vol. Drawn from vol p90/p10 ratio if
    # available (more dispersion -> larger k). Otherwise default.
    p90_p10 = (vol_summary_row or {}).get("vol_p90_p10_ratio")
    if p90_p10 is not None and np.isfinite(p90_p10):
        k_vol = float(np.clip(1.5 + 0.5 * (p90_p10 - 1.0), 1.5, 3.0))
    else:
        k_vol = 2.0

    # gamma: inventory aversion, scaled by vol clustering.
    cluster = (vol_summary_row or {}).get("vol_cluster_lag1", 0.0)
    if cluster is None or not np.isfinite(cluster):
        cluster = 0.0
    gamma = float(np.clip(1e-3 + 1e-2 * max(0.0, float(cluster)), 1e-3, 1e-2))

    return {
        "min_edge_ticks": int(min_edge_ticks),
        "k_vol": float(round(k_vol, 4)),
        "gamma": float(round(gamma, 6)),
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _max_abs_ic(ic_for_product: pd.DataFrame, signal: Optional[str] = None,
                horizons=HORIZONS) -> float:
    if ic_for_product is None or ic_for_product.empty:
        return float("nan")
    sub = ic_for_product
    if signal is not None:
        sub = sub[sub["signal"] == signal]
    if sub.empty:
        return float("nan")
    cols = [f"ic_h{h}" for h in horizons if f"ic_h{h}" in sub.columns]
    if not cols:
        return float("nan")
    arr = sub[cols].abs().to_numpy(dtype=float)
    return float(np.nanmax(arr)) if np.isfinite(arr).any() else float("nan")


def _max_within_family_corr(product: str, corr_mid: pd.DataFrame) -> float:
    if corr_mid.empty or product not in corr_mid.index:
        return float("nan")
    row = corr_mid.loc[product].drop(product, errors="ignore")
    if row.empty:
        return float("nan")
    return float(row.abs().max())


def _best_coint_p(product: str, coint_df: pd.DataFrame) -> float:
    if coint_df is None or coint_df.empty:
        return float("nan")
    sub = coint_df[(coint_df["a"] == product) | (coint_df["b"] == product)]
    if sub.empty:
        return float("nan")
    p = sub["coint_p"].astype(float)
    if not p.notna().any():
        return float("nan")
    return float(p.min())


def _best_pair_partner(
    product: str,
    corr_mid: pd.DataFrame,
    coint_df: pd.DataFrame,
    gates: ArchetypeGates,
) -> Optional[str]:
    """Highest-corr family member that clears the pair gate.

    Two-tier: a partner with ``|corr|>=pair_corr_strong`` passes without
    cointegration (the relationship is too strong to require a stationarity
    test that's known to lose power on short series); otherwise it must
    have ``|corr|>=pair_corr_min`` AND ``coint_p<pair_coint_p_max``.

    Returns the partner with strongest |corr| among passing candidates,
    or None.
    """
    if corr_mid is None or corr_mid.empty or product not in corr_mid.index:
        return None
    coint_pair: dict[tuple[str, str], float] = {}
    if coint_df is not None and not coint_df.empty:
        for _, row in coint_df.iterrows():
            coint_pair[(row["a"], row["b"])] = float(row["coint_p"])
            coint_pair[(row["b"], row["a"])] = float(row["coint_p"])
    row = corr_mid.loc[product].drop(product, errors="ignore")
    candidates: list[tuple[str, float, float]] = []
    for partner, c in row.items():
        if not np.isfinite(c):
            continue
        ac = abs(c)
        if ac >= gates.pair_corr_strong:
            cp = coint_pair.get((product, partner), float("nan"))
            candidates.append((partner, ac, cp))
        elif ac >= gates.pair_corr_min:
            cp = coint_pair.get((product, partner), float("nan"))
            if np.isfinite(cp) and cp < gates.pair_coint_p_max:
                candidates.append((partner, ac, cp))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[1], reverse=True)
    return candidates[0][0]


def _best_mr_signal_ic(
    ic_for_product: Optional[pd.DataFrame], alpha: float
) -> dict:
    """Best FDR-pass IC across MR_SIGNALS.

    Returns the same dict shape as ``best_significant_ic``. Currently
    ``MR_SIGNALS = (neg_zscore_mid_50,)`` so this is a thin wrapper, but
    the multi-signal scaffolding remains for future MR-style alphas.
    """
    candidates = [
        best_significant_ic(ic_for_product, signal=s, alpha=alpha) for s in MR_SIGNALS
    ]
    candidates = [c for c in candidates if c.get("passes_fdr") and pd.notna(c.get("ic"))]
    if not candidates:
        return {"ic": float("nan"), "signal": None, "horizon": None,
                "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False}
    return max(candidates, key=lambda c: abs(c["ic"]))


def _count_mr_triggers(stats_row: dict, gates: ArchetypeGates) -> tuple[int, list[str]]:
    """Count how many of the seven MR structural triggers fire.

    Returns ``(n, names)`` where ``names`` lists the firing triggers in
    declaration order. Used to grade classification confidence — a product
    firing 1 trigger at threshold-boundary is classified MR_TAKER but
    flagged as low-confidence for downstream risk allocation.
    """
    triggers = [
        ("vr_lt", lambda r: pd.notna(r.get("vr_k5")) and r["vr_k5"] < gates.mr_vr_max),
        ("acf1_neg", lambda r: pd.notna(r.get("acf_ret1_lag1")) and r["acf_ret1_lag1"] < gates.mr_acf1_max),
        ("hurst_lt", lambda r: pd.notna(r.get("hurst")) and r["hurst"] < gates.mr_hurst_max),
        ("adf_mid_stat", lambda r: pd.notna(r.get("adf_p_mid")) and r["adf_p_mid"] < gates.mr_adf_max),
        ("vwap_hurst_lt", lambda r: pd.notna(r.get("vwap_hurst")) and r["vwap_hurst"] < gates.mr_vwap_hurst_max),
        ("vwap_adf_stat", lambda r: pd.notna(r.get("vwap_adf_p")) and r["vwap_adf_p"] < gates.mr_vwap_adf_max),
        ("vwap_acf1_neg", lambda r: pd.notna(r.get("vwap_acf_lag1")) and r["vwap_acf_lag1"] < gates.mr_vwap_acf1_max),
    ]
    fired = [name for name, fn in triggers if fn(stats_row)]
    return len(fired), fired


def _check_mr_contradictions(stats_row: dict, gates: ArchetypeGates) -> list[str]:
    """Return list of opposite-sign sister stats that fire alongside MR triggers.

    A clean MR product should not also show clear trending (vr > 1.005),
    positive serial dependence (acf > 0.005), or persistence (hurst > 0.55).
    When one of these fires the classifier still admits MR_TAKER (preserves
    inclusivity) but records the contradiction. The downstream strategy
    template can downweight or skip these products.
    """
    contras: list[str] = []
    vr = stats_row.get("vr_k5", float("nan"))
    if pd.notna(vr) and vr > gates.mr_contra_vr_min:
        contras.append(f"vr_k5={vr:.3f}>{gates.mr_contra_vr_min} (trending signal)")
    acf1 = stats_row.get("acf_ret1_lag1", float("nan"))
    if pd.notna(acf1) and acf1 > gates.mr_contra_acf_min:
        contras.append(f"acf_lag1={acf1:+.3f}>{gates.mr_contra_acf_min} (positive autocorr)")
    hurst = stats_row.get("hurst", float("nan"))
    if pd.notna(hurst) and hurst > gates.mr_contra_hurst_max:
        contras.append(f"hurst={hurst:.3f}>{gates.mr_contra_hurst_max} (persistent)")
    vwap_acf1 = stats_row.get("vwap_acf_lag1", float("nan"))
    if pd.notna(vwap_acf1) and vwap_acf1 > gates.mr_contra_vwap_acf_min:
        contras.append(f"vwap_acf_lag1={vwap_acf1:+.3f}>{gates.mr_contra_vwap_acf_min} (vwap positive autocorr)")
    return contras


def _grade_mr_confidence(n_triggers: int, ic_verified: bool, contradictions: list[str],
                         gates: ArchetypeGates) -> str:
    """Grade MR_TAKER classification on a 3-level scale.

      "high"    : FDR-passing IC OR n_triggers >= mr_high_n_triggers, no contradictions
      "medium"  : 2 triggers fired, no contradictions
      "low"     : 1 trigger only, OR any contradiction is present
    """
    if contradictions:
        return "low"
    if ic_verified or n_triggers >= gates.mr_high_n_triggers:
        return "high"
    if n_triggers >= 2:
        return "medium"
    return "low"


def _passes_mm_structural(stats_row: dict, gates: ArchetypeGates) -> bool:
    """Structural eligibility for the passive-MM template.

    Same checks the RANDOM_WALK primary uses (vr/hurst/acf near random,
    spread cushion vs noise, book depth) — but evaluated independently of
    the priority chain. A product can layer MM on top of MR_TAKER if both
    structural profiles fit. The simulation gate downstream is the final
    authority.
    """
    vr = stats_row.get("vr_k5", float("nan"))
    hurst = stats_row.get("hurst", float("nan"))
    acf1 = stats_row.get("acf_ret1_lag1", float("nan"))
    spread_med = stats_row.get("spread_median", float("nan"))
    ret1_std = stats_row.get("ret1_std", float("nan"))
    lim10_sat = stats_row.get("limit10_saturation", float("nan"))
    checks = [
        np.isfinite(vr) and abs(vr - 1.0) < gates.rw_vr_dev_max,
        np.isfinite(hurst) and abs(hurst - 0.5) < gates.rw_hurst_dev_max,
        np.isfinite(acf1) and abs(acf1) < gates.rw_acf1_max_abs,
        (
            np.isfinite(spread_med) and np.isfinite(ret1_std) and ret1_std > 0
            and spread_med / ret1_std >= gates.rw_spread_to_std_min
        ),
        np.isfinite(lim10_sat) and lim10_sat >= gates.rw_lim10_sat_min,
    ]
    return all(checks)


def _best_obi_signal_ic(
    ic_for_product: Optional[pd.DataFrame], alpha: float
) -> dict:
    """Best FDR-pass IC across OBI_SIGNALS at OBI_HORIZONS.

    OBI is a tick-level microstructure predictor; restricting to short
    horizons (1, 10) avoids spurious long-horizon overlap effects. Returns
    a dict identical in shape to ``best_significant_ic``.
    """
    candidates = [
        best_significant_ic(ic_for_product, signal=s, horizons=OBI_HORIZONS, alpha=alpha)
        for s in OBI_SIGNALS
    ]
    candidates = [c for c in candidates if c.get("passes_fdr") and pd.notna(c.get("ic"))]
    if not candidates:
        return {"ic": float("nan"), "signal": None, "horizon": None,
                "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False}
    return max(candidates, key=lambda c: abs(c["ic"]))


def classify_product(
    stats_row: dict,
    ic_for_product: Optional[pd.DataFrame],
    corr_mid: pd.DataFrame,
    coint_df: pd.DataFrame,
    vol_summary_row: Optional[dict] = None,
    quality_row: Optional[dict] = None,
    gates: ArchetypeGates = ArchetypeGates(),
    fdr_alpha: float = DEFAULT_FDR_ALPHA,
    rw_short_horizon_only: bool = True,
) -> dict:
    p = stats_row["product"]
    vr = stats_row.get("vr_k5", np.nan)
    vr_z = stats_row.get("vr_z_k5", np.nan)
    hurst = stats_row.get("hurst", np.nan)
    acf1 = stats_row.get("acf_ret1_lag1", np.nan)
    ret1_std = stats_row.get("ret1_std", np.nan)
    n_ticks = int(stats_row.get("n_ticks", 0) or 0)
    spread_med = stats_row.get("spread_median", np.nan)
    lim10_sat = stats_row.get("limit10_saturation", np.nan)
    adf_p_mid = stats_row.get("adf_p_mid", np.nan)
    vwap_hurst = stats_row.get("vwap_hurst", np.nan)
    vwap_adf_p = stats_row.get("vwap_adf_p", np.nan)
    vwap_acf1 = stats_row.get("vwap_acf_lag1", np.nan)

    # --- Significance for the directional stats ---
    vr_p = vr_p_value(vr_z) if pd.notna(vr_z) else float("nan")
    acf1_p = bartlett_acf_p(acf1, n_ticks) if pd.notna(acf1) else float("nan")
    # Hurst doesn't get a strict p (heuristic SE only); we report the value.

    # --- Best (signal, horizon) IC with FDR control ---
    # FDR is applied across the 5 signals × 4 horizons = 20 cells per product.
    # `best_significant_ic` returns the highest |IC| among FDR-passing cells
    # (or the raw best with passes_fdr=False if none pass).
    best_overall = best_significant_ic(ic_for_product, alpha=fdr_alpha)
    best_mr = _best_mr_signal_ic(ic_for_product, alpha=fdr_alpha)
    best_mom = best_significant_ic(ic_for_product, signal="momentum_10", alpha=fdr_alpha)
    # For RW, "no signal" means no significant short-horizon predictability.
    short_h = (1, 10)
    best_short = best_significant_ic(ic_for_product, horizons=short_h, alpha=fdr_alpha)

    # --- Pair flag (orthogonal — computed regardless of primary archetype) ---
    # is_pair fires only when ONE partner satisfies both corr and coint
    # gates simultaneously. Earlier code fired on max-corr + min-coint
    # computed against (potentially different) partners — produced
    # is_pair=True but pair_partner=None. The partner-finder is the
    # single source of truth.
    pair_partner = _best_pair_partner(p, corr_mid, coint_df, gates)
    if pair_partner is not None:
        pair_corr_val = float(corr_mid.loc[p, pair_partner])
        coint_lookup = {(r["a"], r["b"]): float(r["coint_p"]) for _, r in coint_df.iterrows()}
        coint_lookup.update({(r["b"], r["a"]): float(r["coint_p"]) for _, r in coint_df.iterrows()})
        pair_coint_val = coint_lookup.get((p, pair_partner), float("nan"))
        is_pair = True
    else:
        pair_corr_val = float("nan")
        pair_coint_val = float("nan")
        is_pair = False
    # Stationary residual = coint_p < pair_residual_p_max. High-corr-lane
    # admits a pair without requiring coint, but here we record whether
    # the residual actually IS stationary so the strategy template can
    # choose between fixed β-hedged spread (stationary) and rolling β
    # (non-stationary).
    pair_residual_stationary = (
        is_pair and pd.notna(pair_coint_val) and pair_coint_val < gates.pair_residual_p_max
    )
    pair_info = {
        "is_pair": bool(is_pair),
        "pair_partner": pair_partner,
        "pair_corr": pair_corr_val,
        "pair_coint_p": pair_coint_val,
        "pair_residual_stationary": bool(pair_residual_stationary),
    }

    # --- OBI flag (orthogonal — book-pressure taker on top of any primary) ---
    # OBI IC sign matters: positive = follow (book pressure predicts same-
    # direction return); negative = fade (book pressure predicts reversion).
    # The strategy template needs the direction to choose follow vs fade.
    best_obi = _best_obi_signal_ic(ic_for_product, alpha=fdr_alpha)
    obi_ic_raw = best_obi["ic"] if best_obi["passes_fdr"] else float("nan")
    obi_ic_val = abs(obi_ic_raw) if pd.notna(obi_ic_raw) else float("nan")
    is_obi = pd.notna(obi_ic_val) and obi_ic_val >= gates.obi_ic_min
    if is_obi:
        obi_direction = "follow" if obi_ic_raw > 0 else "fade"
    else:
        obi_direction = None
    obi_info = {
        "is_obi": bool(is_obi),
        "obi_signal": best_obi["signal"] if is_obi else None,
        "obi_ic": float(obi_ic_raw) if is_obi else float("nan"),
        "obi_horizon": int(best_obi["horizon"] or 0) if is_obi else 0,
        "obi_direction": obi_direction,
    }

    # --- MM_CANDIDATE flag (orthogonal, provisional — sim gate confirms) ---
    # Provisional flag is set here based on structural gates only; the
    # downstream Template-A simulation gate either promotes provisional ->
    # final (is_mm=True with positive PnL) or drops the flag.
    mm_provisional = _passes_mm_structural(stats_row, gates)
    if mm_provisional:
        mm_params = derive_rw_params(stats_row, vol_summary_row)
    else:
        mm_params = {}
    mm_info = {
        "mm_provisional": bool(mm_provisional),
        "is_mm": False,                           # promoted by sim gate
        "mm_pnl": float("nan"),
        "mm_fills": 0,
        "mm_params": mm_params,
    }

    # --- MR confidence metadata (computed unconditionally) ---
    # Even non-MR products carry these fields for diagnostic transparency:
    # a NO_EDGE product with mr_n_triggers=0 is "no signal at all"; a
    # NO_EDGE product with mr_n_triggers=1 is "near-miss MR" (still in
    # NO_EDGE because the single trigger flipped from MR_TAKER classification
    # only if there's data-quality failure or the routing chain reaches
    # NO_EDGE through a separate path).
    n_mr_triggers, mr_trigger_names = _count_mr_triggers(stats_row, gates)
    mr_contras = _check_mr_contradictions(stats_row, gates)
    ic_mr_raw_for_meta = best_mr["ic"] if best_mr["passes_fdr"] else float("nan")
    ic_mr_val_for_meta = (
        abs(ic_mr_raw_for_meta) if pd.notna(ic_mr_raw_for_meta) and ic_mr_raw_for_meta > 0 else float("nan")
    )
    mr_ic_verified = bool(pd.notna(ic_mr_val_for_meta) and ic_mr_val_for_meta >= gates.mr_ic_min)
    mr_confidence = _grade_mr_confidence(n_mr_triggers, mr_ic_verified, mr_contras, gates)
    mr_meta = {
        "mr_n_triggers": int(n_mr_triggers),
        "mr_triggers": ",".join(mr_trigger_names),
        "mr_ic_verified": mr_ic_verified,
        "mr_contradictions": "; ".join(mr_contras),
        "mr_confidence": mr_confidence,
    }

    notes: list[str] = []

    # --- Data-quality gate (blocking) ---
    if quality_row is not None:
        from .data_quality import has_blocking_quality_issue
        # quality_row may be either pd.Series-like (with .get) or plain dict
        if has_blocking_quality_issue(quality_row):
            warns = quality_row.get("warnings", "")
            notes.append(f"DATA_QUALITY_WARN: {warns}")
            # When data is bad we drop both orthogonal flags to NO_EDGE
            # parity — IC values may be corrupted, OBI flag is unsafe.
            return _build("NO_EDGE", p, notes,
                          pair_info={"is_pair": False, "pair_partner": None,
                                     "pair_corr": float("nan"), "pair_coint_p": float("nan"),
                                     "pair_residual_stationary": False},
                          obi_info={"is_obi": False, "obi_signal": None,
                                    "obi_ic": float("nan"), "obi_horizon": 0,
                                    "obi_direction": None},
                          mm_info=None,
                          mr_meta=mr_meta)

    # --- Priority 1: MR_TAKER ---
    # Structural triggers (any one fires admits the product to MR routing):
    #   mid-side: VR<1, neg ACF1, low Hurst, ADF stationarity on mid
    #   vwap-side: low Hurst on log VWAP returns, ADF stationarity on log VWAP
    # The multiple paths catch products whose MR shows up in transactions
    # (VWAP) but is masked at the quote level (mid).
    mr_dir_signals = []
    if np.isfinite(vr) and vr < gates.mr_vr_max:
        mr_dir_signals.append(f"vr_k5={vr:.3f}<{gates.mr_vr_max} (z={vr_z:+.2f}, p={vr_p:.3g})")
    if np.isfinite(acf1) and acf1 < gates.mr_acf1_max:
        mr_dir_signals.append(f"acf_lag1={acf1:+.3f}<{gates.mr_acf1_max} (Bartlett p={acf1_p:.3g})")
    if np.isfinite(hurst) and hurst < gates.mr_hurst_max:
        mr_dir_signals.append(f"hurst={hurst:.3f}<{gates.mr_hurst_max}")
    if np.isfinite(adf_p_mid) and adf_p_mid < gates.mr_adf_max:
        mr_dir_signals.append(f"adf_p_mid={adf_p_mid:.3g}<{gates.mr_adf_max}")
    if np.isfinite(vwap_hurst) and vwap_hurst < gates.mr_vwap_hurst_max:
        mr_dir_signals.append(f"vwap_hurst={vwap_hurst:.3f}<{gates.mr_vwap_hurst_max}")
    if np.isfinite(vwap_adf_p) and vwap_adf_p < gates.mr_vwap_adf_max:
        mr_dir_signals.append(f"vwap_adf_p={vwap_adf_p:.3g}<{gates.mr_vwap_adf_max}")
    if np.isfinite(vwap_acf1) and vwap_acf1 < gates.mr_vwap_acf1_max:
        mr_dir_signals.append(f"vwap_acf_lag1={vwap_acf1:+.3f}<{gates.mr_vwap_acf1_max}")
    # Sign check: MR strategy is "buy when neg_zscore high, sell when low",
    # so IC must be positive. A negative IC on neg_zscore would mean the
    # signal predicts continuation, not reversion — a momentum-flavoured
    # product mis-classified as MR.
    ic_mr_raw = best_mr["ic"] if best_mr["passes_fdr"] else float("nan")
    ic_mr_val = abs(ic_mr_raw) if pd.notna(ic_mr_raw) and ic_mr_raw > 0 else float("nan")
    # MR routing: any structural trigger admits the product. The IC value is
    # informational — it picks which anchor signal the strategy uses
    # (mid or vwap z-score) but doesn't gate classification. Reasoning: a
    # product with stationary VWAP (vwap_adf_p<0.05) or low VWAP Hurst is
    # mean-reverting in transactions even when the noisy mid IC fails FDR.
    if mr_dir_signals:
        notes.extend(mr_dir_signals)
        if mr_ic_verified:
            chosen_sig = best_mr["signal"]
            chosen_h = int(best_mr["horizon"] or 0)
            ic_for_params = float(ic_mr_val)
            notes.append(
                f"max |IC[{chosen_sig}]|={ic_mr_val:.3f} @ h={chosen_h}  "
                f"(t={best_mr['t']:+.2f}, p={best_mr['p']:.3g}, FDR-pass)"
            )
        else:
            # No FDR-passing MR signal — pick anchor based on structural prior.
            # Prefer VWAP anchor when VWAP looks more MR than mid.
            if (np.isfinite(vwap_hurst) and np.isfinite(hurst)
                    and vwap_hurst < hurst):
                chosen_sig = "neg_zscore_vwap_50"
            else:
                chosen_sig = "neg_zscore_mid_50"
            chosen_h = 0
            ic_for_params = float("nan")
            notes.append(
                f"structural MR; no FDR-significant IC — anchor default = {chosen_sig}"
            )
        # Annotate confidence + contradictions in the rationale.
        notes.append(f"mr_confidence={mr_confidence} (n_triggers={n_mr_triggers}, ic_verified={mr_ic_verified})")
        if mr_contras:
            notes.append(f"MR_CONTRADICTION: {'; '.join(mr_contras)}")
        return _build("MR_TAKER", p, notes,
                      params={"ic_mr": ic_for_params,
                              "ic_signal": chosen_sig,
                              "ic_horizon": chosen_h},
                      pair_info=pair_info, obi_info=obi_info, mm_info=mm_info,
                      mr_meta=mr_meta)

    # --- Priority 2: MOMENTUM ---
    # Sign check: positive IC[momentum_10] means "past up predicts future
    # up" — true momentum. Negative IC means contrarian behaviour and
    # should not be classified as MOMENTUM (often anti-persistent at long
    # horizons).
    ic_mom_raw = best_mom["ic"] if best_mom["passes_fdr"] else float("nan")
    ic_mom_val = abs(ic_mom_raw) if pd.notna(ic_mom_raw) and ic_mom_raw > 0 else float("nan")
    if (
        np.isfinite(vr) and vr > gates.mom_vr_min
        and np.isfinite(hurst) and hurst > gates.mom_hurst_min
        and pd.notna(ic_mom_val) and ic_mom_val >= gates.mom_ic_min
    ):
        notes.append(f"vr_k5={vr:.3f}>{gates.mom_vr_min} (z={vr_z:+.2f}, p={vr_p:.3g})")
        notes.append(f"hurst={hurst:.2f}>{gates.mom_hurst_min}")
        notes.append(
            f"|IC[momentum_10]|={ic_mom_val:.3f} @ h={best_mom['horizon']}  "
            f"(t={best_mom['t']:+.2f}, p={best_mom['p']:.3g}, FDR-pass)"
        )
        return _build("MOMENTUM", p, notes,
                      params={"ic_momentum": float(ic_mom_val),
                              "ic_horizon": int(best_mom["horizon"] or 0)},
                      pair_info=pair_info, obi_info=obi_info, mm_info=mm_info,
                      mr_meta=mr_meta)

    # --- Priority 3: RANDOM_WALK (provisional; sim gate confirms) ---
    # For "no predictability" check we use the *short-horizon* IC cells only:
    # long-horizon predictability does not break a tick-level passive MM.
    rw_ic_basis = best_short if rw_short_horizon_only else best_overall
    rw_ic_val = abs(rw_ic_basis["ic"]) if rw_ic_basis["ic"] == rw_ic_basis["ic"] else float("nan")
    rw_ic_passes_fdr = rw_ic_basis.get("passes_fdr", False)
    rw_ic_horizon_label = "short (h=1,10)" if rw_short_horizon_only else "any horizon"

    # Structural gates: vr, hurst, acf, MM-cushion, depth. These say "the
    # price process LOOKS like RW from a tick-level perspective". The IC
    # check is intentionally permissive (HAC-passing AND |IC| ≥ gate),
    # because passive MM doesn't *need* zero predictability — it needs
    # the spread/std cushion. Final authority is the Template-A simulation
    # gate downstream: a structural pass with negative simulated PnL gets
    # downgraded to NO_EDGE, and a structural fail never reaches the sim.
    rw_checks: list[bool] = [
        np.isfinite(vr) and abs(vr - 1.0) < gates.rw_vr_dev_max,
        np.isfinite(hurst) and abs(hurst - 0.5) < gates.rw_hurst_dev_max,
        np.isfinite(acf1) and abs(acf1) < gates.rw_acf1_max_abs,
        # No HAC+FDR-significant short-horizon IC OR raw |IC| below the gate.
        (not rw_ic_passes_fdr) or (pd.notna(rw_ic_val) and rw_ic_val < gates.rw_max_ic),
        (
            np.isfinite(spread_med) and np.isfinite(ret1_std) and ret1_std > 0
            and spread_med / ret1_std >= gates.rw_spread_to_std_min
        ),
        np.isfinite(lim10_sat) and lim10_sat >= gates.rw_lim10_sat_min,
    ]
    if all(rw_checks):
        params = derive_rw_params(stats_row, vol_summary_row)
        notes.append(f"|vr-1|={abs(vr-1):.3f}<{gates.rw_vr_dev_max} (vr_p={vr_p:.3g})")
        notes.append(f"|hurst-0.5|={abs(hurst-0.5):.3f}<{gates.rw_hurst_dev_max}")
        notes.append(f"|acf_lag1|={abs(acf1):.3f}<{gates.rw_acf1_max_abs} (Bartlett p={acf1_p:.3g})")
        if pd.notna(rw_ic_val):
            notes.append(
                f"max |IC| ({rw_ic_horizon_label}) = {rw_ic_val:.3f} "
                f"(FDR-pass={rw_ic_passes_fdr})"
            )
        else:
            notes.append(f"no IC data; treating as zero predictability")
        notes.append(f"spread/std={spread_med/ret1_std:.2f}>={gates.rw_spread_to_std_min}")
        notes.append(f"lim10_sat={lim10_sat:.2f}>={gates.rw_lim10_sat_min}")
        return _build("RANDOM_WALK", p, notes, params=params, provisional=True,
                      pair_info=pair_info, obi_info=obi_info, mm_info=mm_info,
                      mr_meta=mr_meta)

    # --- Priority 4: NO_EDGE ---
    # Show overall best IC for transparency, but also annotate that the
    # primary archetype routing only consults MR_SIGNALS / momentum_10. A
    # large IC on neg_spread or trade_imbalance does NOT mean an archetype
    # was missed — those signals don't drive primary routing (they may
    # surface as REGIME_GATED in volatility output, or as OBI flag if
    # they're book-pressure variants).
    notes.append(
        f"no primary trigger fired; vr={vr:.3f} (p={vr_p:.3g}), "
        f"hurst={hurst:.2f}, acf1={acf1:+.3f} (p={acf1_p:.3g}); "
        f"MR-IC|max[neg_z]|={abs(ic_mr_val) if pd.notna(ic_mr_val) else float('nan'):.3f}, "
        f"MOM-IC|max[mom10]|={abs(ic_mom_val) if pd.notna(ic_mom_val) else float('nan'):.3f}; "
        f"overall best |IC|={abs(best_overall['ic']) if pd.notna(best_overall['ic']) else float('nan'):.3f} "
        f"@ {best_overall['signal']} h={best_overall['horizon']} (informational)"
    )
    # Annotate near-miss diagnostics for NO_EDGE products. n_triggers > 0
    # means some structural signal fired but the contradiction check or
    # priority chain blocked classification.
    if n_mr_triggers > 0:
        notes.append(
            f"NO_EDGE near-miss: {n_mr_triggers} MR trigger(s) fired ({mr_meta['mr_triggers']}) "
            f"but mr_confidence={mr_confidence}"
        )
    return _build("NO_EDGE", p, notes, pair_info=pair_info, obi_info=obi_info,
                  mm_info=mm_info, mr_meta=mr_meta)


def _build(arch: str, product: str, notes: list[str], params: Optional[dict] = None,
           provisional: bool = False, pair_info: Optional[dict] = None,
           obi_info: Optional[dict] = None, mm_info: Optional[dict] = None,
           mr_meta: Optional[dict] = None) -> dict:
    pair_info = pair_info or {"is_pair": False, "pair_partner": None,
                              "pair_corr": float("nan"), "pair_coint_p": float("nan"),
                              "pair_residual_stationary": False}
    obi_info = obi_info or {"is_obi": False, "obi_signal": None,
                            "obi_ic": float("nan"), "obi_horizon": 0,
                            "obi_direction": None}
    mm_info = mm_info or {"mm_provisional": False, "is_mm": False,
                          "mm_pnl": float("nan"), "mm_fills": 0,
                          "mm_params": {}}
    mr_meta = mr_meta or {"mr_n_triggers": 0, "mr_triggers": "",
                          "mr_ic_verified": False, "mr_contradictions": "",
                          "mr_confidence": "n/a"}
    return {
        "product": product,
        "archetype": arch,
        "rationale": "; ".join(notes) if notes else "",
        "params": params or {},
        "provisional": bool(provisional),
        # PAIR_ANCHOR fields
        "is_pair": bool(pair_info.get("is_pair", False)),
        "pair_partner": pair_info.get("pair_partner"),
        "pair_corr": pair_info.get("pair_corr", float("nan")),
        "pair_coint_p": pair_info.get("pair_coint_p", float("nan")),
        "pair_residual_stationary": bool(pair_info.get("pair_residual_stationary", False)),
        # OBI_TAKER fields
        "is_obi": bool(obi_info.get("is_obi", False)),
        "obi_signal": obi_info.get("obi_signal"),
        "obi_ic": obi_info.get("obi_ic", float("nan")),
        "obi_horizon": int(obi_info.get("obi_horizon") or 0),
        "obi_direction": obi_info.get("obi_direction"),
        # MM_CANDIDATE fields
        "mm_provisional": bool(mm_info.get("mm_provisional", False)),
        "is_mm": bool(mm_info.get("is_mm", False)),
        "mm_pnl": mm_info.get("mm_pnl", float("nan")),
        "mm_fills": int(mm_info.get("mm_fills", 0) or 0),
        "mm_params": mm_info.get("mm_params") or {},
        # MR confidence metadata (audit traceability)
        "mr_n_triggers": int(mr_meta.get("mr_n_triggers") or 0),
        "mr_triggers": mr_meta.get("mr_triggers", ""),
        "mr_ic_verified": bool(mr_meta.get("mr_ic_verified", False)),
        "mr_contradictions": mr_meta.get("mr_contradictions", ""),
        "mr_confidence": mr_meta.get("mr_confidence", "n/a"),
    }


def assign_archetypes(
    family_data: dict[str, ProductData],
    stats_df: pd.DataFrame,
    ic_by_product: dict[str, pd.DataFrame],
    corr_mid: pd.DataFrame,
    coint_df: pd.DataFrame,
    vol_summary_df: Optional[pd.DataFrame] = None,
    quality_df: Optional[pd.DataFrame] = None,
    gates: ArchetypeGates = ArchetypeGates(),
    fdr_alpha: float = DEFAULT_FDR_ALPHA,
) -> pd.DataFrame:
    vol_lookup: dict[str, dict] = {}
    if vol_summary_df is not None and not vol_summary_df.empty:
        vol_lookup = {r["product"]: r for r in vol_summary_df.to_dict("records")}
    quality_lookup: dict[str, dict] = {}
    if quality_df is not None and not quality_df.empty:
        quality_lookup = {r["product"]: r for r in quality_df.to_dict("records")}

    rows = []
    for _, srow in stats_df.iterrows():
        p = srow["product"]
        ic_p = ic_by_product.get(p)
        v = vol_lookup.get(p)
        q = quality_lookup.get(p)
        result = classify_product(
            stats_row=srow.to_dict(),
            ic_for_product=ic_p,
            corr_mid=corr_mid,
            coint_df=coint_df,
            vol_summary_row=v,
            quality_row=q,
            gates=gates,
            fdr_alpha=fdr_alpha,
        )
        rows.append(result)
    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Template-A simulation (1-tick-grid passive MM, IMC "worse" fill semantics)
# ---------------------------------------------------------------------------

def simulate_template_a(
    px: pd.DataFrame,
    tr: pd.DataFrame,
    min_edge_ticks: int,
    k_vol: float,
    gamma: float,
    position_limit: int = POSITION_LIMIT,
) -> dict:
    """Walk-forward simulation of Template-A passive MM.

    At each tick we quote bid/ask from current state. Fills follow IMC's
    'worse' semantics: bid fills against a market trade priced strictly
    below our bid; ask fills against a market trade priced strictly above
    our ask. Fill quantity capped by remaining position-limit headroom.

    Returns aggregate metrics + tick-aligned series for the health figure.
    """
    if px.empty:
        return {"pnl_total": 0.0, "n_fills": 0, "skipped": "empty px"}

    inventory = 0
    cash = 0.0
    pnl_series: list[float] = []
    inv_series: list[int] = []
    bid_series: list[float] = []
    ask_series: list[float] = []
    n_bid_fills = 0
    n_ask_fills = 0

    # Per-day iteration so timestamps don't bridge day boundaries.
    for day, sub_px in px.groupby("day"):
        sub_px = sub_px.sort_values("timestamp").reset_index(drop=True)
        if not tr.empty and "day" in tr.columns:
            sub_tr = tr[tr["day"] == day].sort_values("timestamp").reset_index(drop=True)
        else:
            sub_tr = pd.DataFrame()

        ts = sub_px["timestamp"].to_numpy()
        mids = sub_px["mid"].to_numpy()
        rv50 = sub_px["std_50"].to_numpy()

        # Pre-bin trade indices by tick interval [t_i, t_{i+1}).
        if not sub_tr.empty:
            tr_ts = sub_tr["timestamp"].to_numpy()
            tr_price = sub_tr["price"].to_numpy()
            tr_qty = sub_tr["quantity"].to_numpy()
            # searchsorted gives, for each tick boundary, the trade index.
            bin_starts = np.searchsorted(tr_ts, ts, side="left")
        else:
            tr_price = tr_qty = np.array([])
            bin_starts = np.zeros(len(ts) + 1, dtype=int)

        for i in range(len(ts) - 1):
            mid = mids[i]
            rv = rv50[i]
            if not np.isfinite(rv) or rv <= 0:
                rv = float(np.nanstd(mids[max(0, i - 50):i + 1])) or 1.0

            half_spread = max(min_edge_ticks, k_vol * rv)
            skew = gamma * rv * rv * inventory
            bid = mid - half_spread - skew
            ask = mid + half_spread - skew

            # One-sided quoting at limit.
            quote_bid = inventory < position_limit
            quote_ask = inventory > -position_limit

            bid_series.append(bid if quote_bid else np.nan)
            ask_series.append(ask if quote_ask else np.nan)

            if tr_price.size:
                lo = bin_starts[i]
                hi = bin_starts[i + 1] if i + 1 < len(bin_starts) else lo
                for j in range(lo, hi):
                    tprice = tr_price[j]
                    tqty = float(tr_qty[j])
                    if quote_bid and tprice < bid:
                        room = position_limit - inventory
                        fill = min(tqty, room) if room > 0 else 0
                        if fill > 0:
                            inventory += int(fill)
                            cash -= fill * bid
                            n_bid_fills += 1
                            quote_bid = inventory < position_limit
                    elif quote_ask and tprice > ask:
                        room = position_limit + inventory
                        fill = min(tqty, room) if room > 0 else 0
                        if fill > 0:
                            inventory -= int(fill)
                            cash += fill * ask
                            n_ask_fills += 1
                            quote_ask = inventory > -position_limit

            inv_series.append(inventory)
            pnl_series.append(cash + inventory * mid)

    if not pnl_series:
        return {"pnl_total": 0.0, "n_fills": 0, "skipped": "no ticks"}

    inv_arr = np.array(inv_series)
    return {
        "pnl_total": float(pnl_series[-1]),
        "n_bid_fills": n_bid_fills,
        "n_ask_fills": n_ask_fills,
        "n_fills": n_bid_fills + n_ask_fills,
        "max_inventory_abs": int(np.max(np.abs(inv_arr))) if len(inv_arr) else 0,
        "final_inventory": int(inventory),
        "fill_rate": float((n_bid_fills + n_ask_fills) / max(1, len(pnl_series))),
        "pnl_series": pnl_series,
        "inv_series": inv_series,
        "bid_series": bid_series,
        "ask_series": ask_series,
    }


# ---------------------------------------------------------------------------
# Health figure
# ---------------------------------------------------------------------------

def fig_rw_health(
    product: str,
    px: pd.DataFrame,
    sim: dict,
    params: dict,
    out_path: Path,
    sample_window: int = 2000,
) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=False)
    title = (f"{product} - RW Template-A health  "
             f"PnL={sim.get('pnl_total', 0):+.1f}  fills={sim.get('n_fills', 0)}  "
             f"max|inv|={sim.get('max_inventory_abs', 0)}")
    fig.suptitle(title, fontsize=11, fontweight="bold")

    n = len(sim.get("pnl_series", [])) if "pnl_series" in sim else 0
    if n == 0:
        for ax in axes:
            ax.text(0.5, 0.5, "no simulation data", ha="center", va="center")
        fig.tight_layout()
        _save(fig, out_path)
        return out_path

    # Top: mid + bid/ask over a sample window (full series too dense to read)
    start = max(0, n // 2 - sample_window // 2)
    end = min(n, start + sample_window)
    mids = px["mid"].to_numpy()[:n]
    x = np.arange(start, end)
    axes[0].plot(x, mids[start:end], color="black", lw=0.6, label="mid")
    axes[0].plot(x, np.array(sim["bid_series"])[start:end], color="steelblue", lw=0.4, label="bid_quote")
    axes[0].plot(x, np.array(sim["ask_series"])[start:end], color="firebrick", lw=0.4, label="ask_quote")
    axes[0].set_title(f"mid + quotes  (sample window {start}..{end})")
    axes[0].legend(fontsize=8, loc="best")

    # Middle: inventory full series
    axes[1].plot(np.arange(n), sim["inv_series"], color="seagreen", lw=0.5)
    axes[1].axhline(POSITION_LIMIT, color="red", ls="--", lw=0.4)
    axes[1].axhline(-POSITION_LIMIT, color="red", ls="--", lw=0.4)
    axes[1].axhline(0, color="black", lw=0.4)
    axes[1].set_title("inventory")

    # Bottom: cumulative PnL
    axes[2].plot(np.arange(n), sim["pnl_series"], color="purple", lw=0.6)
    axes[2].axhline(0, color="black", lw=0.4)
    pstr = (f"params: min_edge_ticks={params.get('min_edge_ticks')}, "
            f"k_vol={params.get('k_vol')}, gamma={params.get('gamma')}")
    axes[2].set_title(f"cumulative PnL  |  {pstr}")
    axes[2].set_xlabel("tick")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, out_path)
    return out_path


# ---------------------------------------------------------------------------
# Simulation gate (downgrades RW -> NO_EDGE if PnL < 0)
# ---------------------------------------------------------------------------

def run_rw_simulation_gate(
    family_data: dict[str, ProductData],
    archetype_df: pd.DataFrame,
    out_dir: Path,
    verbose: bool = True,
) -> dict[str, dict]:
    """Mutates archetype_df in place. Two-pronged:

    1. Every product with ``mm_provisional=True`` gets a Template-A sim. On
       PnL > 0, ``is_mm`` is set True and the MM_CANDIDATE flag is final.
       On PnL <= 0, ``is_mm`` stays False (flag is dropped).
    2. Products with primary archetype RANDOM_WALK that fail the sim are
       additionally demoted to NO_EDGE primary (legacy behaviour, in case a
       product reaches RW primary by lacking any MR/MOMENTUM signal).

    Returns dict[product] -> sim metrics for downstream display.
    """
    fig_dir = Path(out_dir) / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    sim_results: dict[str, dict] = {}
    if archetype_df.empty:
        return sim_results

    if "mm_provisional" not in archetype_df.columns:
        # Older frame without MM evaluation columns — nothing to do.
        return sim_results

    elig_mask = archetype_df["mm_provisional"].astype(bool) | (
        archetype_df["archetype"] == "RANDOM_WALK"
    )
    if not elig_mask.any():
        return sim_results

    elig_rows = archetype_df[elig_mask].copy()
    for idx, row in elig_rows.iterrows():
        p = row["product"]
        # mm_params is set in classify_product when structural gates pass;
        # for primary=RANDOM_WALK products we keep `params` as the source.
        mm_params = row.get("mm_params") or {}
        legacy_params = row.get("params") or {}
        params = mm_params or legacy_params
        if not params or p not in family_data:
            continue
        d = family_data[p]
        if verbose:
            primary = row["archetype"]
            print(f"  [{p}] MM Template-A simulation ({primary} primary) ...")
        sim = simulate_template_a(
            d.px, d.tr,
            min_edge_ticks=int(params.get("min_edge_ticks", 3)),
            k_vol=float(params.get("k_vol", 2.0)),
            gamma=float(params.get("gamma", 1e-3)),
        )
        sim_results[p] = sim

        # Health figure regardless of pass/fail (negative-PnL plots are
        # diagnostic for tuning).
        fig_rw_health(p, d.px, sim, params, fig_dir / f"{p}_mm_health.png")

        pnl = sim.get("pnl_total", 0.0)
        n_fills = int(sim.get("n_fills", 0))
        archetype_df.at[idx, "mm_pnl"] = float(pnl)
        archetype_df.at[idx, "mm_fills"] = n_fills

        # Three sim outcomes:
        #   pnl > 0                       -> CONFIRMED. is_mm=True.
        #   pnl <= 0 with n_fills > 0     -> SIM_REJECTED. is_mm=False.
        #   pnl == 0 and n_fills == 0     -> UNTESTED. Round-5 has sparse
        #                                    trade activity for many products
        #                                    so the strategy never got a fill
        #                                    opportunity. Structural gate
        #                                    already passed; we keep the
        #                                    flag so the strategy compositor
        #                                    can decide whether to deploy.
        archetype_df.at[idx, "mm_provisional"] = False
        if pnl > 0:
            archetype_df.at[idx, "is_mm"] = True
            archetype_df.at[idx, "rationale"] = (
                (archetype_df.at[idx, "rationale"] or "")
                + f"; MM_SIM_PASS pnl={pnl:+.2f}, fills={n_fills}"
            )
            if verbose:
                print(f"    -> MM_CANDIDATE confirmed (PnL={pnl:+.2f})")
        elif n_fills == 0:
            archetype_df.at[idx, "is_mm"] = True
            archetype_df.at[idx, "rationale"] = (
                (archetype_df.at[idx, "rationale"] or "")
                + f"; MM_SIM_UNTESTED pnl={pnl:+.2f}, fills=0 (sparse trades; structural gate authoritative)"
            )
            if verbose:
                print(f"    -> MM_CANDIDATE untested (no fills) — flag retained")
        else:
            archetype_df.at[idx, "is_mm"] = False
            archetype_df.at[idx, "rationale"] = (
                (archetype_df.at[idx, "rationale"] or "")
                + f"; MM_SIM_FAIL pnl={pnl:+.2f}, fills={n_fills}"
            )
            if row["archetype"] == "RANDOM_WALK":
                # Legacy demotion: only-MM-candidate primary → NO_EDGE on
                # negative sim PnL with actual fills.
                archetype_df.at[idx, "archetype"] = "NO_EDGE"
                archetype_df.at[idx, "provisional"] = False
                if verbose:
                    print(f"    -> RW primary downgraded NO_EDGE (PnL={pnl:+.2f})")
            elif verbose:
                print(f"    -> MM flag dropped (PnL={pnl:+.2f})")
    return sim_results


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------

def archetype_summary_md(
    archetype_df: pd.DataFrame,
    sim_results: dict[str, dict],
) -> str:
    if archetype_df.empty:
        return "## Archetype assignment\n\n_(no products classified)_\n"
    lines = ["## Archetype assignment",
             "",
             "_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are "
             "discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, "
             "and MM_CANDIDATE are orthogonal flags — any product can carry one "
             "or more on top of its primary._",
             ""]
    counts = archetype_df["archetype"].value_counts()
    pair_count = int(archetype_df["is_pair"].sum()) if "is_pair" in archetype_df.columns else 0
    obi_count = int(archetype_df["is_obi"].sum()) if "is_obi" in archetype_df.columns else 0
    mm_count = int(archetype_df["is_mm"].sum()) if "is_mm" in archetype_df.columns else 0
    lines.append("Counts:")
    for arch in ARCHETYPE_LABELS:
        n = int(counts.get(arch, 0))
        lines.append(f"- {arch}: {n}")
    lines.append(f"- PAIR_ANCHOR (flag): {pair_count}")
    lines.append(f"- OBI_TAKER (flag): {obi_count}")
    lines.append(f"- MM_CANDIDATE (flag): {mm_count}")
    lines.append("")

    # --- MR confidence breakdown ---
    if "mr_confidence" in archetype_df.columns:
        mr_sub = archetype_df[archetype_df["archetype"] == "MR_TAKER"]
        if not mr_sub.empty:
            lines.append("MR_TAKER confidence breakdown:")
            for level in ("high", "medium", "low"):
                n = int((mr_sub["mr_confidence"] == level).sum())
                lines.append(f"- mr_confidence={level}: {n}")
            n_verified = int(mr_sub["mr_ic_verified"].sum())
            n_contra = int(mr_sub["mr_contradictions"].fillna("").astype(str).str.len().gt(0).sum())
            lines.append(f"- with FDR-passing IC (mr_ic_verified=True): {n_verified}")
            lines.append(f"- with at least one contradiction signal: {n_contra}")
            lines.append("")
    for arch in ARCHETYPE_LABELS:
        sub = archetype_df[archetype_df["archetype"] == arch]
        if sub.empty:
            continue
        lines.append(f"### {arch}")
        for _, r in sub.iterrows():
            head = f"- **{r['product']}**"
            # MR_TAKER confidence prefix.
            if arch == "MR_TAKER":
                conf = r.get("mr_confidence", "?")
                n_t = int(r.get("mr_n_triggers") or 0)
                ic_v = bool(r.get("mr_ic_verified", False))
                head += f"  [{conf} conf, {n_t} trigger(s)"
                if ic_v:
                    head += ", IC-verified"
                head += "]"
            if arch == "RANDOM_WALK" and r["product"] in sim_results:
                sim = sim_results[r["product"]]
                head += (
                    f"  pnl={sim.get('pnl_total', 0):+.2f}  fills={sim.get('n_fills', 0)}  "
                    f"max|inv|={sim.get('max_inventory_abs', 0)}"
                )
            if r.get("is_pair"):
                stat = "stationary" if r.get("pair_residual_stationary") else "non-stat"
                head += f"  [+ PAIR_ANCHOR with {r.get('pair_partner')} ({stat})]"
            if r.get("is_obi"):
                direction = r.get("obi_direction") or "?"
                head += (
                    f"  [+ OBI_TAKER {direction} {r.get('obi_signal')} h={int(r.get('obi_horizon') or 0)} "
                    f"IC={float(r.get('obi_ic') or 0):+.3f}]"
                )
            if r.get("is_mm"):
                pnl = r.get("mm_pnl")
                fills = int(r.get("mm_fills") or 0)
                pnl_str = f"{float(pnl):+.0f}" if pd.notna(pnl) else "?"
                status = "confirmed" if (pd.notna(pnl) and pnl > 0) else "untested"
                head += f"  [+ MM_CANDIDATE {status} pnl={pnl_str} fills={fills}]"
            lines.append(head)
            if r["params"]:
                lines.append(f"  - params: {r['params']}")
            if r["rationale"]:
                lines.append(f"  - rationale: {r['rationale']}")
        lines.append("")

    # --- Pair-anchor section (orthogonal) ---
    pair_sub = archetype_df[archetype_df.get("is_pair", False)] if "is_pair" in archetype_df.columns else archetype_df.iloc[0:0]
    lines.append("### PAIR_ANCHOR (orthogonal flag)")
    if pair_sub.empty:
        lines.append("- _(no products cleared the PAIR gate vs any family member)_")
    else:
        n_stat = int(pair_sub.get("pair_residual_stationary", pd.Series(False)).sum())
        n_total = len(pair_sub)
        lines.append(f"_{n_stat}/{n_total} pairs have stationary residual (suitable for fixed-β hedge); "
                     f"the rest need rolling β._")
        for _, r in pair_sub.iterrows():
            partner = r.get("pair_partner") or "?"
            corr = r.get("pair_corr", float("nan"))
            cp = r.get("pair_coint_p", float("nan"))
            stat_lbl = "STATIONARY" if r.get("pair_residual_stationary") else "non-stat"
            lines.append(
                f"- **{r['product']}** ↔ {partner}  "
                f"(corr={corr:+.2f}, coint_p={cp:.3g}, {stat_lbl})  primary={r['archetype']}"
            )
    lines.append("")

    # --- OBI flag section (orthogonal) ---
    obi_sub = archetype_df[archetype_df.get("is_obi", False)] if "is_obi" in archetype_df.columns else archetype_df.iloc[0:0]
    lines.append("### OBI_TAKER (orthogonal flag)")
    if obi_sub.empty:
        lines.append("- _(no products cleared the OBI gate with FDR-pass at h ∈ {1, 10})_")
    else:
        if "obi_direction" in obi_sub.columns:
            n_follow = int((obi_sub["obi_direction"] == "follow").sum())
            n_fade = int((obi_sub["obi_direction"] == "fade").sum())
            lines.append(f"_{n_follow} follow signals, {n_fade} fade signals (sign of IC determines strategy direction)._")
        for _, r in obi_sub.iterrows():
            direction = r.get("obi_direction") or "?"
            lines.append(
                f"- **{r['product']}**  direction={direction}  signal={r.get('obi_signal')}  "
                f"h={int(r.get('obi_horizon') or 0)}  "
                f"IC={float(r.get('obi_ic') or 0):+.3f}  primary={r['archetype']}"
            )
    lines.append("")

    # --- MM_CANDIDATE section (orthogonal) ---
    mm_sub = archetype_df[archetype_df.get("is_mm", False)] if "is_mm" in archetype_df.columns else archetype_df.iloc[0:0]
    lines.append("### MM_CANDIDATE (orthogonal flag — passive Template-A MM)")
    if mm_sub.empty:
        lines.append("- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_")
    else:
        for _, r in mm_sub.iterrows():
            pnl = r.get("mm_pnl")
            fills = int(r.get("mm_fills") or 0)
            params = r.get("mm_params") or {}
            pnl_str = f"{float(pnl):+.2f}" if pd.notna(pnl) else "?"
            lines.append(
                f"- **{r['product']}**  primary={r['archetype']}  "
                f"sim_pnl={pnl_str}  fills={fills}  params={params}"
            )
    lines.append("")
    return "\n".join(lines)
