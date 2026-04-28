"""Round-5 volatility-spike anatomy.

Companion to ``round5/vol_spikes.py``. Once we know *which* products spike
(8 of 50), this asks **why**: what microstructural event creates a 4σ move,
and how does the price recover?

For each product with ``n_spikes >= 5`` it computes:

    1. **Jump-distribution profile** — # unique |ret_1| values, dominant
       jump magnitudes, p(zero), top-1 / top-3 jump frequency. Identifies
       quantized vs continuous mid behaviour.
    2. **Spread profile** — dominant spread + locked-spread fraction.
       A locked-spread product whose mid jumps ±k means the *whole book
       translates* — passive MM quote refresh, not aggressor sweep.
    3. **Trade attribution** — what fraction of spikes coincide with a
       trade in the same tick. Low share (≪50%) ⇒ MM-driven repricing,
       not flow-driven sweep.
    4. **Recovery profile** — half-life of the post-spike reversion,
       fraction of spikes that fully snap back within 200 ticks.
    5. **Mechanism classification** — one of:
         * QUANTIZED_QUOTE_REFRESH — locked spread, ±k discrete jumps,
           almost no trade-coincidence  (strong MR_TAKER alpha already
           captured by neg_zscore taker; spread > jump ⇒ taking is
           sub-zero, must MAKE).
         * AGGRESSOR_SWEEP        — trade-coincident spike, book-side
           displacement (one side moves more than the other).
         * FAST_NOISE_OSCILLATOR  — fine-grained jump distribution,
           strong tick-by-tick MR (acf < −0.1) — DISHES profile.
         * HEAVY_TAIL_GAUSSIAN    — diffuse jumps, no quantization, no
           special structure (rare).

Outputs under ``round5/reports/CROSS/vol_spikes/anatomy/``:

    spike_anatomy.csv         per-product: jump profile, spread profile,
                              trade-coincidence rate, recovery half-life,
                              mechanism label.
    spike_recovery_curve.csv  per-product × horizon: P(snap_back), mean
                              reversion completed.
    figures/<P>_anatomy.png   3-panel: |ret_1| histogram (log-y),
                              spread-locked time series, post-spike
                              recovery curve.
    spike_mechanism_report.md  narrative + classification + utilization.

CLI: python round5/spike_anatomy.py [--k 4.0] [--lookback 500]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from round5.research_lib import (  # noqa: E402
    DEFAULT_DAYS, FAMILIES, ProductData, add_microstructure, add_vwap,
    load_prices, load_trades,
)
from round5.vol_spikes import detect_spikes, POST_HORIZONS  # noqa: E402


MIN_SPIKES_FOR_ANATOMY = 5
RECOVERY_HORIZONS = (1, 5, 10, 20, 50, 100, 200, 500)


# ---------------------------------------------------------------------------
# Per-product profile
# ---------------------------------------------------------------------------

def jump_profile(px: pd.DataFrame) -> dict:
    r = px["ret_1"].dropna()
    nz = r[r != 0]
    out = {
        "n_ret": int(len(r)),
        "ret_std": float(r.std()),
        "p_zero": float((r == 0).mean()),
        "n_unique_jumps": int(nz.abs().nunique()),
    }
    if len(nz):
        vc = nz.abs().value_counts().sort_values(ascending=False)
        top_size = float(vc.index[0])
        top_share = float(vc.iloc[0] / len(r))  # fraction of *all* ticks (incl zeros)
        out["dominant_jump_size"] = top_size
        out["dominant_jump_share"] = top_share
        out["top3_share"] = float(vc.head(3).sum() / len(r))
    else:
        out["dominant_jump_size"] = np.nan
        out["dominant_jump_share"] = np.nan
        out["top3_share"] = np.nan
    return out


def spread_profile(px: pd.DataFrame) -> dict:
    sp = px["spread"].dropna()
    out = {"spread_mean": float(sp.mean()), "spread_n_unique": int(sp.nunique())}
    if len(sp):
        vc = sp.value_counts()
        out["spread_dominant"] = float(vc.idxmax())
        out["spread_locked_share"] = float(vc.max() / len(sp))
    else:
        out["spread_dominant"] = np.nan
        out["spread_locked_share"] = np.nan
    return out


def trade_attribution(spikes: pd.DataFrame, tr: pd.DataFrame) -> dict:
    out = {"trade_at_spike_rate": np.nan, "n_spike_with_trade": 0,
           "n_spike_no_trade": 0, "spike_trade_qty_mean": np.nan}
    if spikes.empty:
        return out
    if tr is None or tr.empty:
        out["trade_at_spike_rate"] = 0.0
        out["n_spike_no_trade"] = int(len(spikes))
        return out
    # Trade-set per (day, ts)
    trade_keys = set(zip(tr["day"].astype(int), tr["timestamp"].astype(int)))
    spike_keys = list(zip(spikes["day"].astype(int), spikes["ts"].astype(int)))
    has_trade = np.array([k in trade_keys for k in spike_keys])
    out["n_spike_with_trade"] = int(has_trade.sum())
    out["n_spike_no_trade"] = int((~has_trade).sum())
    out["trade_at_spike_rate"] = float(has_trade.mean())
    if has_trade.any():
        # Match trade qty for the spike ticks
        tr_lookup = (tr.groupby(["day", "timestamp"])["quantity"]
                       .sum().to_dict())
        qtys = [tr_lookup.get(k, 0) for k, h in zip(spike_keys, has_trade) if h]
        out["spike_trade_qty_mean"] = float(np.mean(qtys)) if qtys else np.nan
    return out


def recovery_profile(d: ProductData, spikes: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Two outputs:
       (a) summary dict with mean reversion fraction at each horizon and
           half-life of the recovery (h at which P(snap_back >= 50%) = 0.5);
       (b) long-form DataFrame: per (horizon) → P(snap_back), mean reversion %.
    """
    out = {f"reversion_pct_h{h}": np.nan for h in RECOVERY_HORIZONS}
    out["snap_back_h_50pct"] = np.nan
    rows = []
    if spikes.empty:
        return out, pd.DataFrame(rows)

    px = d.px
    snap_back_hits = {h: [] for h in RECOVERY_HORIZONS}
    reversion_pcts = {h: [] for h in RECOVERY_HORIZONS}

    for _, row in spikes.iterrows():
        day = int(row["day"])
        i = int(row["row_idx"])
        sign = int(row["sign"])
        magnitude = float(row["abs_ret"])  # the spike's |ret_1|
        if magnitude <= 0:
            continue
        sub = px[px["day"] == day].reset_index(drop=True)
        if i >= len(sub):
            continue
        mid_at_spike = float(sub.loc[i, "mid"])
        for h in RECOVERY_HORIZONS:
            j = i + h
            if j >= len(sub):
                continue
            cumret = float(sub.loc[j, "mid"] - mid_at_spike)
            # Reversion fraction = how much of the spike has been undone
            #   spike was (+sign * magnitude), so reversion = -sign * cumret / magnitude
            rev_frac = -sign * cumret / magnitude
            reversion_pcts[h].append(rev_frac)
            snap_back_hits[h].append(rev_frac >= 0.5)

    for h in RECOVERY_HORIZONS:
        if reversion_pcts[h]:
            mean_rev = float(np.mean(reversion_pcts[h]))
            p_snap = float(np.mean(snap_back_hits[h]))
            rows.append({"product": d.product, "horizon": h,
                         "mean_reversion_frac": mean_rev,
                         "p_snap_back_50pct": p_snap,
                         "n": int(len(reversion_pcts[h]))})
            out[f"reversion_pct_h{h}"] = mean_rev

    # Half-life: smallest h where p_snap >= 0.5
    for h in RECOVERY_HORIZONS:
        ps = snap_back_hits[h]
        if ps and float(np.mean(ps)) >= 0.5:
            out["snap_back_h_50pct"] = h
            break

    return out, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mechanism classification
# ---------------------------------------------------------------------------

def classify_mechanism(row: dict) -> tuple[str, str]:
    """Return (label, rationale). Priority-ordered; first match wins.

    Inputs are the merged row of jump_profile + spread_profile +
    trade_attribution + recovery_profile + acf_lag1 (passed in via row).
    """
    n_spikes = row.get("n_spikes", 0)
    if n_spikes < MIN_SPIKES_FOR_ANATOMY:
        return ("INSUFFICIENT_DATA",
                f"n_spikes={n_spikes} < {MIN_SPIKES_FOR_ANATOMY}")

    locked = row.get("spread_locked_share", 0)
    n_unique = row.get("n_unique_jumps", 999)
    top1 = row.get("dominant_jump_share", 0)
    trade_rate = row.get("trade_at_spike_rate", 1.0)
    acf1 = row.get("acf_lag1", 0)
    rev_h50 = row.get("reversion_pct_h50", 0) or 0

    # 1. PRICE_DISCOVERY_BREAKOUT: spike continues, not reverts (momentum after shock)
    if rev_h50 <= -0.30:
        return ("PRICE_DISCOVERY_BREAKOUT",
                f"reversion_h50={rev_h50:+.2f}: post-spike price continues away "
                f"(spike was real information, not noise)")

    # 2. QUANTIZED_QUOTE_REFRESH: locked spread + dominant jump + low trade-coincidence
    quantized = (locked >= 0.6 and trade_rate <= 0.20 and
                 (n_unique <= 30 or top1 >= 0.15))
    if quantized:
        return ("QUANTIZED_QUOTE_REFRESH",
                f"spread_locked={locked:.2f}, top_jump={top1:.2%}, "
                f"unique_jumps={n_unique}, trade_at_spike={trade_rate:.2%}: "
                f"MM repricing in discrete steps")

    # 3. AGGRESSOR_SWEEP: trade-coincident with the spike
    if trade_rate >= 0.5:
        return ("AGGRESSOR_SWEEP",
                f"trade_at_spike={trade_rate:.2%} >= 50% — flow-driven")

    # 4. FAST_NOISE_OSCILLATOR: smooth jumps + strong tick-by-tick MR
    if (n_unique >= 50 and acf1 <= -0.10):
        return ("FAST_NOISE_OSCILLATOR",
                f"unique_jumps={n_unique}, acf_lag1={acf1:.3f}: "
                f"granular oscillator with strong tick-MR")

    # 5. PARTIAL_QUANTIZATION: dominant single jump but not locked spread
    if top1 >= 0.20 and trade_rate <= 0.30:
        return ("PARTIAL_QUANTIZATION",
                f"top_jump={top1:.2%}, trade={trade_rate:.2%}: "
                f"discrete repricing layered on noise")

    return ("HEAVY_TAIL_GAUSSIAN",
            f"diffuse jumps (unique={n_unique}, top1={top1:.2%}), "
            f"trade_rate={trade_rate:.2%}, acf1={acf1:.3f}: no clear structure")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_anatomy(d: ProductData, spikes: pd.DataFrame, recovery_df: pd.DataFrame,
                row: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    fig.suptitle(f"{d.product} — Spike Anatomy [{row['mechanism']}]",
                 fontsize=11, fontweight="bold")

    # Panel A: |ret_1| histogram (log-y)
    axA = axes[0]
    r = d.px["ret_1"].dropna()
    nz = r[r != 0].abs()
    if len(nz):
        bins = np.linspace(0, max(1.0, nz.quantile(0.999)), 80)
        axA.hist(nz, bins=bins, color="steelblue", alpha=0.85)
        axA.axvline(row.get("dominant_jump_size", np.nan), color="red", ls="--",
                    lw=0.8, label=f"top size={row.get('dominant_jump_size', float('nan')):.0f}")
        axA.legend(fontsize=8)
        axA.set_yscale("log")
    axA.set_title(f"|ret_1| dist (n_unique={row.get('n_unique_jumps', '-')})")
    axA.set_xlabel("|ret_1|")

    # Panel B: spread distribution + zero-bar
    axB = axes[1]
    sp = d.px["spread"].dropna()
    if len(sp):
        vc = sp.value_counts().sort_index().head(15)
        axB.bar(vc.index.astype(str), vc.values / len(sp), color="seagreen")
        axB.set_title(f"spread dist  locked={row.get('spread_locked_share', 0):.0%}")
        axB.set_xlabel("spread (ticks)")

    # Panel C: recovery curve
    axC = axes[2]
    if not recovery_df.empty:
        sub = recovery_df.sort_values("horizon")
        axC.plot(sub["horizon"], sub["mean_reversion_frac"],
                 marker="o", color="darkorange", label="mean reversion frac")
        axC.plot(sub["horizon"], sub["p_snap_back_50pct"],
                 marker="s", color="firebrick", label="P(reversion ≥ 50%)")
        axC.axhline(1.0, color="grey", ls=":", lw=0.6)
        axC.axhline(0.5, color="grey", ls=":", lw=0.6)
        axC.set_xscale("log")
        axC.legend(fontsize=8)
    axC.set_title(f"recovery (trade_at_spike={row.get('trade_at_spike_rate', 0):.0%})")
    axC.set_xlabel("horizon (ticks)")

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(k: float, lookback: int, days, out_dir: Path) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    rows = []
    recovery_long = []
    products = [p for fam in FAMILIES.values() for p in fam]

    for fam, members in FAMILIES.items():
        for p in members:
            px = add_microstructure(load_prices(p, days))
            tr = load_trades(p, days)
            px = add_vwap(px, tr)
            d = ProductData(product=p, px=px, tr=tr)
            spikes = detect_spikes(d, k=k, lookback=lookback)
            n_spikes = int(len(spikes))
            if n_spikes < MIN_SPIKES_FOR_ANATOMY:
                rows.append({"family": fam, "product": p, "n_spikes": n_spikes,
                             "mechanism": "INSUFFICIENT_DATA",
                             "rationale": f"n_spikes={n_spikes} < {MIN_SPIKES_FOR_ANATOMY}"})
                continue

            jp = jump_profile(px)
            sp = spread_profile(px)
            tatt = trade_attribution(spikes, tr)
            rp, rec_df = recovery_profile(d, spikes)
            acf1 = float(px["ret_1"].dropna().autocorr(1)) if len(px) > 2 else np.nan
            p_snap_h50 = float(rec_df.loc[rec_df["horizon"] == 50, "p_snap_back_50pct"].iloc[0]) \
                if (not rec_df.empty and (rec_df["horizon"] == 50).any()) else np.nan

            row = {"family": fam, "product": p, "n_spikes": n_spikes, "acf_lag1": acf1,
                   "p_snap_h50": p_snap_h50,
                   **jp, **sp, **tatt, **rp}
            label, rationale = classify_mechanism(row)
            row["mechanism"] = label
            row["rationale"] = rationale
            rows.append(row)

            recovery_long.append(rec_df)
            fig_anatomy(d, spikes, rec_df, row, fig_dir / f"{p}_anatomy.png")

    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "spike_anatomy.csv", index=False)
    if recovery_long:
        pd.concat(recovery_long, ignore_index=True).to_csv(
            out_dir / "spike_recovery_curve.csv", index=False)

    print(f"[spike_anatomy] {len(out)} products. mechanisms:")
    print(out["mechanism"].value_counts().to_string())
    print(f"  wrote -> {out_dir}")
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=float, default=4.0)
    p.add_argument("--lookback", type=int, default=500)
    p.add_argument("--days", type=int, nargs="+", default=list(DEFAULT_DAYS))
    p.add_argument("--out", type=Path,
                   default=_PROJECT_ROOT / "round5" / "reports" / "CROSS" / "vol_spikes" / "anatomy")
    args = p.parse_args(argv)
    run(k=args.k, lookback=args.lookback, days=args.days, out_dir=args.out)


if __name__ == "__main__":
    main()
