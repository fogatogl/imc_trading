"""Per-family ML feature panel + label construction.

Reuses round5.research_lib for raw loading and microstructure derivation.

Public API:
    build_feature_frame(family, days) -> pd.DataFrame
    build_labels(df, target, horizon) -> pd.Series
    feature_columns(df) -> list[str]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import research_lib as rl  # noqa: E402

PER_PRODUCT_LAGS = (1, 5, 20, 50)
FAMILY_MEAN_LAGS = (5, 20)
PER_PRODUCT_LAG_COLS = (
    "obi_l1",
    "obi_l3",
    "microprice_dev",
    "ret_1",
    "ret_10",
    "std_50",
    "std_500",
    "spread_bps",
    "signed_flow_20",
    "vwap_dev",
)
FAMILY_MEAN_FEATURES = ("ret_10", "obi_l1", "microprice_dev")
EXTRA_HORIZONS = (20, 50)


def _add_extra_fwd(px: pd.DataFrame, horizons: Sequence[int] = EXTRA_HORIZONS) -> pd.DataFrame:
    out = px.copy()
    for h in horizons:
        if f"fwd_{h}" in out.columns:
            continue
        out[f"fwd_{h}"] = out.groupby("day")["mid"].shift(-h) - out["mid"]
    return out


def _add_per_product_features(px: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """Add `microprice_dev`, `vwap_dev`, `signed_flow_20`, plus all per-product lags."""
    out = _add_extra_fwd(px)
    out["microprice_dev"] = out["microprice"] - out["mid"]
    out["vwap_dev"] = out["vwap"] - out["mid"]
    out["signed_flow_20"] = rl._signed_trade_flow(out, tr, window=20)
    for col in PER_PRODUCT_LAG_COLS:
        if col not in out.columns:
            continue
        for k in PER_PRODUCT_LAGS:
            out[f"{col}_lag{k}"] = out.groupby("day")[col].shift(k)
    return out


def _add_family_mean_features(long_df: pd.DataFrame) -> pd.DataFrame:
    """Append family-mean lag columns for FAMILY_MEAN_FEATURES.

    Audit (round-5 PEBBLES smoke) showed the per-sibling pivot produced columns
    with identical Ridge importance to 9 decimals — perfect multicollinearity
    because variant products in a family co-move tightly. Family-mean replaces
    that 20-column block with `fam_mean_<feat>_lag<k>` (3 features × 2 lags = 6
    columns) which preserves the cross-product signal without the redundancy.
    """
    out = long_df.copy()
    for feat in FAMILY_MEAN_FEATURES:
        if feat not in out.columns:
            continue
        per_ts = (
            out.groupby(["day", "timestamp"])[feat].mean().rename(f"fam_mean_{feat}")
        )
        for k in FAMILY_MEAN_LAGS:
            lagged_name = f"fam_mean_{feat}_lag{k}"
            shifted = per_ts.groupby(level="day").shift(k).rename(lagged_name)
            out = out.merge(shifted.reset_index(), on=["day", "timestamp"], how="left")
    return out


def build_feature_frame(
    family: str,
    days: Sequence[int] = rl.DEFAULT_DAYS,
    root: Path | str = rl.DATASET_ROOT,
) -> pd.DataFrame:
    """Build the long-form ML feature panel for one family.

    Returns a DataFrame keyed by (day, timestamp, product) with:
      - microstructure columns from research_lib (mid, microprice, obi_*, std_*, fwd_*, ret_*)
      - microprice_dev, vwap_dev, signed_flow_20
      - per-product lags for PER_PRODUCT_LAG_COLS at PER_PRODUCT_LAGS
      - sibling lag columns for SIBLING_FEATURES at SIBLING_LAGS (one per product in family)

    NaN rows (head of each day from lags, tail from fwd labels) are kept; caller
    drops them when assembling X / y.
    """
    family_data = rl.load_family(family, days=days, root=root)
    per_product = []
    for p, pd_obj in family_data.items():
        if pd_obj.px.empty:
            continue
        px = _add_per_product_features(pd_obj.px, pd_obj.tr)
        px["product"] = p
        per_product.append(px)
    if not per_product:
        return pd.DataFrame()
    long_df = pd.concat(per_product, ignore_index=True)
    long_df = _add_family_mean_features(long_df)
    long_df = long_df.sort_values(["day", "product", "timestamp"]).reset_index(drop=True)
    return long_df


def build_labels(df: pd.DataFrame, target: str, horizon: int) -> pd.Series:
    """Return the supervised target as a Series aligned to df.index.

    target='fwd_ret' -> raw forward return at given horizon (continuous).
    target='toxic'   -> binary (0/1) adverse-selection label:
        toxic = 1 iff sign(fwd_h) * sign(microprice_dev) < 0
                  AND |fwd_h| > 0.5 * spread
    """
    if target == "fwd_ret":
        col = f"fwd_{horizon}"
        if col not in df.columns:
            raise KeyError(f"horizon {horizon} not pre-computed; column {col} missing")
        return df[col].astype(float)
    if target == "toxic":
        col = f"fwd_{horizon}"
        if col not in df.columns:
            raise KeyError(f"horizon {horizon} not pre-computed; column {col} missing")
        fwd = df[col].astype(float)
        mp_dev = df["microprice_dev"].astype(float)
        half_spread = 0.5 * df["spread"].astype(float)
        opposite_sign = (np.sign(fwd) * np.sign(mp_dev)) < 0
        magnitude_ok = fwd.abs() > half_spread
        toxic = (opposite_sign & magnitude_ok).astype(float)
        # Where fwd is NaN (end of day), label is NaN to be dropped downstream
        toxic[fwd.isna() | mp_dev.isna() | half_spread.isna()] = np.nan
        return toxic
    raise ValueError(f"unknown target {target!r}; expected 'fwd_ret' or 'toxic'")


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of feature columns to feed the model.

    Excludes raw / label / metadata columns. Any column ending in `_lag<k>` or
    starting with `fam_mean_` is a feature.
    """
    feat = []
    for c in df.columns:
        if c.startswith("fam_mean_") and "_lag" in c:
            feat.append(c)
        elif "_lag" in c and not c.startswith("fam_mean_"):
            feat.append(c)
    return feat
