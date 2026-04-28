"""Per-product data-quality checks for round-5 research.

Bad data silently corrupts every downstream stat. The classifier sees a
plausible vr_k5 / IC and assigns an archetype, but the stat was driven by
NaN runs, crossed quotes, or stale prices. This module flags such
products *before* classification, exposes the warnings in the rationale,
and (optionally) gates the classifier from emitting an archetype on
quality failures — degrading to NO_EDGE with a `DATA_QUALITY_WARN`
rationale.

The checks are conservative: round-5's CSVs are clean by construction,
so any quality flag is a real anomaly worth investigating.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .research_lib import ProductData


@dataclass(frozen=True)
class QualityGates:
    """Gate thresholds. A check 'fails' when its value crosses the gate.

    All gates are conservative: only flag when the anomaly is large enough
    to plausibly distort a stat (vr_k5, IC, hurst, etc.).
    """
    nan_mid_max: float = 0.005           # > 0.5% NaN in mid → suspicious
    nan_l1_max: float = 0.01             # > 1% NaN in best bid/ask
    crossed_max: float = 0.0001          # any crossed market is unusual
    zero_spread_max: float = 0.005       # > 0.5% zero-spread is unusual
    stale_run_min: int = 50              # consecutive ticks with mid unchanged
    stale_frac_max: float = 0.20         # > 20% time stuck → degrades stats
    outlier_n_max: int = 50              # > 50 ret_1 values > 5σ
    day_jump_z_max: float = 6.0          # day-boundary jump > 6 std → ETL split issue
    zero_l1_bid_max: float = 0.05
    zero_l1_ask_max: float = 0.05
    short_ticks_min: int = 1000          # absolute floor on tradable history


# ---------------------------------------------------------------------------
# Per-product checks
# ---------------------------------------------------------------------------

def check_product_data(d: ProductData, gates: QualityGates = QualityGates()) -> dict:
    """Run all checks on a product. Returns a dict of metrics + warnings."""
    px = d.px
    out: dict = {
        "product": d.product,
        "n_ticks": int(len(px)) if not px.empty else 0,
        "warnings": [],
    }
    if px.empty:
        out["warnings"].append("EMPTY_PX: no price data")
        return out

    # 1. NaN rates
    out["frac_nan_mid"] = float(px["mid"].isna().mean())
    out["frac_nan_bid1"] = float(px["bid_price_1"].isna().mean())
    out["frac_nan_ask1"] = float(px["ask_price_1"].isna().mean())

    # 2. Crossed (bid >= ask) and zero-spread
    valid_bid_ask = px[["bid_price_1", "ask_price_1"]].dropna()
    if len(valid_bid_ask):
        out["frac_crossed"] = float((valid_bid_ask["bid_price_1"] > valid_bid_ask["ask_price_1"]).mean())
        out["frac_locked"] = float((valid_bid_ask["bid_price_1"] == valid_bid_ask["ask_price_1"]).mean())
    else:
        out["frac_crossed"] = float("nan")
        out["frac_locked"] = float("nan")
    if "spread" in px.columns:
        sp = px["spread"].dropna()
        out["frac_zero_spread"] = float((sp == 0).mean()) if len(sp) else float("nan")
    else:
        out["frac_zero_spread"] = float("nan")

    # 3. Stale runs (mid unchanged for ≥ stale_run_min consecutive ticks)
    diff_zero = (px["mid"].diff() == 0).fillna(False)
    if diff_zero.any():
        # Run-length of consecutive True values.
        groups = (diff_zero != diff_zero.shift()).cumsum()
        run_lengths = diff_zero.groupby(groups).sum()
        long_runs = run_lengths[run_lengths >= gates.stale_run_min]
        out["n_stale_runs"] = int(len(long_runs))
        out["frac_stale_long"] = float(long_runs.sum() / len(px)) if len(px) else 0.0
    else:
        out["n_stale_runs"] = 0
        out["frac_stale_long"] = 0.0

    # 4. Outlier returns
    ret = px["ret_1"].dropna() if "ret_1" in px.columns else pd.Series(dtype=float)
    if len(ret) > 10:
        rstd = float(ret.std())
        out["ret_std"] = rstd
        out["n_outlier_5sig"] = int((ret.abs() > 5 * rstd).sum()) if rstd > 0 else 0
    else:
        out["ret_std"] = float("nan")
        out["n_outlier_5sig"] = 0

    # 5. Day-boundary jumps
    if "day" in px.columns and px["day"].nunique() > 1:
        ends = []
        starts = []
        for d_, sub in px.groupby("day"):
            ends.append((d_, float(sub["mid"].iloc[-1])))
            starts.append((d_, float(sub["mid"].iloc[0])))
        ends = sorted(ends, key=lambda x: x[0])
        starts = sorted(starts, key=lambda x: x[0])
        rstd = out.get("ret_std", float("nan"))
        max_z = 0.0
        for i in range(len(ends) - 1):
            jump = abs(starts[i + 1][1] - ends[i][1])
            if rstd and rstd > 0:
                z = jump / rstd
                if z > max_z:
                    max_z = z
        out["day_jump_z_max"] = float(max_z)
    else:
        out["day_jump_z_max"] = float("nan")

    # 6. Zero L1 volume frac
    if "bid_volume_1" in px.columns:
        out["frac_zero_l1_bid"] = float((px["bid_volume_1"] == 0).mean())
        out["frac_zero_l1_ask"] = float((px["ask_volume_1"] == 0).mean())

    # ---- Aggregate warnings against gates ----
    warns: list[str] = []
    if out["n_ticks"] < gates.short_ticks_min:
        warns.append(f"SHORT_HISTORY: n_ticks={out['n_ticks']} < {gates.short_ticks_min}")
    if out["frac_nan_mid"] > gates.nan_mid_max:
        warns.append(f"NAN_MID: {out['frac_nan_mid']:.4f} > {gates.nan_mid_max}")
    if out.get("frac_nan_bid1", 0) > gates.nan_l1_max:
        warns.append(f"NAN_L1_BID: {out['frac_nan_bid1']:.4f}")
    if out.get("frac_nan_ask1", 0) > gates.nan_l1_max:
        warns.append(f"NAN_L1_ASK: {out['frac_nan_ask1']:.4f}")
    if pd.notna(out.get("frac_crossed")) and out["frac_crossed"] > gates.crossed_max:
        warns.append(f"CROSSED_MARKET: {out['frac_crossed']:.5f}")
    if pd.notna(out.get("frac_zero_spread")) and out["frac_zero_spread"] > gates.zero_spread_max:
        warns.append(f"ZERO_SPREAD: {out['frac_zero_spread']:.4f}")
    if out["frac_stale_long"] > gates.stale_frac_max:
        warns.append(
            f"STALE_PRICES: {out['frac_stale_long']:.3f} of ticks in runs ≥ "
            f"{gates.stale_run_min}"
        )
    if out["n_outlier_5sig"] > gates.outlier_n_max:
        warns.append(f"OUTLIER_RETURNS: {out['n_outlier_5sig']} ret_1 |z|>5")
    if pd.notna(out.get("day_jump_z_max")) and out["day_jump_z_max"] > gates.day_jump_z_max:
        warns.append(f"DAY_JUMP: {out['day_jump_z_max']:.1f}σ at boundary")
    if out.get("frac_zero_l1_bid", 0) > gates.zero_l1_bid_max:
        warns.append(f"EMPTY_L1_BID: {out['frac_zero_l1_bid']:.3f}")
    if out.get("frac_zero_l1_ask", 0) > gates.zero_l1_ask_max:
        warns.append(f"EMPTY_L1_ASK: {out['frac_zero_l1_ask']:.3f}")

    out["warnings"] = warns
    out["has_warnings"] = bool(warns)
    return out


def family_quality_report(
    family_data: dict[str, ProductData],
    gates: QualityGates = QualityGates(),
) -> pd.DataFrame:
    """Per-family DataFrame: one row per product with quality metrics +
    warnings list. Empty data products are included with a single warning."""
    rows = [check_product_data(d, gates) for d in family_data.values()]
    df = pd.DataFrame(rows)
    if not df.empty:
        # Render warnings as semicolon-joined string for CSV friendliness.
        df["warnings"] = df["warnings"].apply(lambda lst: "; ".join(lst) if lst else "")
    return df


def has_blocking_quality_issue(quality_row: pd.Series, blocking_keys: tuple[str, ...] = (
    "EMPTY_PX", "SHORT_HISTORY", "NAN_MID", "CROSSED_MARKET", "STALE_PRICES",
)) -> bool:
    """Returns True if any *blocking* quality issue is present.

    By default only the structurally-fatal warnings block classification:
    empty data, short history, large NaN runs in the mid, crossed markets,
    or substantial stale runs. Soft warnings (e.g. small zero-spread
    fraction) are reported but don't gate the classifier.
    """
    s = str(quality_row.get("warnings", ""))
    if not s:
        return False
    return any(key in s for key in blocking_keys)
