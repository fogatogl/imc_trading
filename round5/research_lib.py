"""Round 5 per-family research pipeline.

Public entrypoint: ``family_report(family, out_dir)`` runs the full battery
(stats / microstructure / signal IC / within-family relationships / figures /
tradeable-ideas markdown) for one of the 10 families and writes everything
under ``out_dir/<FAMILY>/``.

The 10 families and their 5-product members are fixed in ``FAMILIES`` below
(derived from the round-5 spec + the unique product list in the prices CSV).

Library is import-safe: side effects (file writes, plotting) only happen when
the user calls ``family_report`` or one of the figure functions.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import matplotlib

matplotlib.use("Agg")  # headless save; notebook switches back via plt.show
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint

# Make project root importable so ``imc_commun.stats`` resolves regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from imc_stats.stats import hurst_rs, variance_ratio, zscore  # noqa: E402
except ModuleNotFoundError:  # legacy local layout
    from imc_commun.stats import hurst_rs, variance_ratio, zscore  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATASET_ROOT = _PROJECT_ROOT / "dataset" / "ROUND_5"
DEFAULT_DAYS = (2, 3, 4)
HORIZONS = (1, 10, 100, 1000)
SIGNAL_NAMES = (
    "neg_zscore_mid_50",
    "neg_zscore_vwap_50",
    "obi_l1",
    "obi_l3",
    "momentum_10",
    "trade_imbalance",
    "neg_spread",
)

FAMILIES: dict[str, list[str]] = {
    "GALAXY_SOUNDS": [
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_WINDS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
    ],
    "SLEEP_POD": [
        "SLEEP_POD_SUEDE",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_COTTON",
    ],
    "MICROCHIP": [
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_SQUARE",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_TRIANGLE",
    ],
    "PEBBLES": [
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    ],
    "ROBOT": [
        "ROBOT_VACUUMING",
        "ROBOT_MOPPING",
        "ROBOT_DISHES",
        "ROBOT_LAUNDRY",
        "ROBOT_IRONING",
    ],
    "UV_VISOR": [
        "UV_VISOR_AMBER",
        "UV_VISOR_MAGENTA",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_YELLOW",
    ],
    "TRANSLATOR": [
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_VOID_BLUE",
    ],
    "PANEL": [
        "PANEL_1X2",
        "PANEL_1X4",
        "PANEL_2X2",
        "PANEL_2X4",
        "PANEL_4X4",
    ],
    "OXYGEN_SHAKE": [
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_GARLIC",
        "OXYGEN_SHAKE_MORNING_BREATH",
        "OXYGEN_SHAKE_EVENING_BREATH",
    ],
    "SNACKPACK": [
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_VANILLA",
        "SNACKPACK_RASPBERRY",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_PISTACHIO",
    ],
}

POSITION_LIMIT = 10  # round-5 hard cap


def family_products(family: str) -> list[str]:
    if family not in FAMILIES:
        raise KeyError(f"Unknown family {family!r}. Known: {list(FAMILIES)}")
    return list(FAMILIES[family])


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_prices(
    product: str,
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
) -> pd.DataFrame:
    root = Path(root)
    frames = []
    for d in days:
        f = root / f"prices_round_5_day_{d}.csv"
        df = pd.read_csv(f, sep=";")
        df = df[df["product"] == product].copy()
        df["day"] = d
        df = df.sort_values("timestamp").reset_index(drop=True)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_trades(
    product: str,
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
) -> pd.DataFrame:
    root = Path(root)
    frames = []
    for d in days:
        f = root / f"trades_round_5_day_{d}.csv"
        df = pd.read_csv(f, sep=";")
        df = df[df["symbol"] == product].copy()
        df["day"] = d
        df = df.sort_values("timestamp").reset_index(drop=True)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@dataclass
class ProductData:
    product: str
    px: pd.DataFrame  # microstructure-augmented prices
    tr: pd.DataFrame  # raw trades


def load_family(
    family: str,
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
) -> dict[str, ProductData]:
    out: dict[str, ProductData] = {}
    for p in family_products(family):
        px = load_prices(p, days, root)
        px = add_microstructure(px)
        tr = load_trades(p, days, root)
        px = add_vwap(px, tr)
        out[p] = ProductData(product=p, px=px, tr=tr)
    return out


# ---------------------------------------------------------------------------
# Microstructure derivation
# ---------------------------------------------------------------------------

def add_microstructure(px: pd.DataFrame) -> pd.DataFrame:
    """Augment prices with derived microstructure columns.

    Per-day grouping: returns / rolling stats / forward returns are computed
    within each day so they don't bleed across day boundaries.
    """
    if px.empty:
        return px
    out_frames = []
    for d, sub in px.groupby("day", sort=True):
        sub = sub.sort_values("timestamp").reset_index(drop=True).copy()

        # Fill NaN volumes / prices for L2/L3 levels (sparse).
        for c in [
            "bid_volume_1", "bid_volume_2", "bid_volume_3",
            "ask_volume_1", "ask_volume_2", "ask_volume_3",
        ]:
            if c in sub.columns:
                sub[c] = sub[c].fillna(0.0)

        b1 = sub["bid_volume_1"].astype(float)
        a1 = sub["ask_volume_1"].astype(float)
        b2 = sub.get("bid_volume_2", pd.Series(0, index=sub.index)).astype(float)
        a2 = sub.get("ask_volume_2", pd.Series(0, index=sub.index)).astype(float)
        b3 = sub.get("bid_volume_3", pd.Series(0, index=sub.index)).astype(float)
        a3 = sub.get("ask_volume_3", pd.Series(0, index=sub.index)).astype(float)
        bT = b1 + b2 + b3
        aT = a1 + a2 + a3

        sub["spread"] = sub["ask_price_1"] - sub["bid_price_1"]
        sub["mid"] = sub["mid_price"]
        sub["microprice"] = (sub["bid_price_1"] * a1 + sub["ask_price_1"] * b1) / (b1 + a1).replace(0, np.nan)
        sub["depth_l1"] = b1 + a1
        sub["depth_l2"] = b2 + a2
        sub["depth_l3"] = b3 + a3
        sub["total_bid_size"] = bT
        sub["total_ask_size"] = aT
        sub["obi_l1"] = (b1 - a1) / (b1 + a1).replace(0, np.nan)
        sub["obi_l3"] = (bT - aT) / (bT + aT).replace(0, np.nan)
        sub["spread_bps"] = 1e4 * sub["spread"] / sub["mid"]

        for h in (1, 10, 100):
            sub[f"ret_{h}"] = sub["mid"].diff(h)
        for h in HORIZONS:
            sub[f"fwd_{h}"] = sub["mid"].shift(-h) - sub["mid"]
        sub["std_50"] = sub["mid"].rolling(50, min_periods=10).std()
        sub["std_500"] = sub["mid"].rolling(500, min_periods=50).std()

        out_frames.append(sub)
    return pd.concat(out_frames, ignore_index=True)


def add_vwap(px: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """Adds a per-tick volume-weighted average trade price column to ``px``.

    Per-day VWAP construction: for each day, aggregate trades within the same
    timestamp into a single VWAP point, then forward-fill onto every px tick.
    The resulting series tracks where actual transactions are clearing — a
    cleaner anchor than mid for MR analysis when traders cross the spread
    asymmetrically (toxic flow distorts mid but not VWAP). Falls back to mid
    when no trades occurred yet on a given day.
    """
    if px.empty:
        return px
    out = px.copy()
    out["vwap"] = np.nan
    if tr is None or tr.empty:
        out["vwap"] = out["mid"].astype(float)
        return out
    for d, sub_tr in tr.groupby("day"):
        if d not in out["day"].unique():
            continue
        sub = sub_tr.copy()
        sub["pq"] = sub["price"].astype(float) * sub["quantity"].astype(float)
        per_ts = sub.groupby("timestamp").agg(pq_sum=("pq", "sum"),
                                              q_sum=("quantity", "sum"))
        per_ts["vwap"] = per_ts["pq_sum"] / per_ts["q_sum"].replace(0, np.nan)
        mask = out["day"] == d
        sub_px = out.loc[mask, ["timestamp"]].copy()
        sub_px["vwap"] = sub_px["timestamp"].map(per_ts["vwap"])
        # Forward-fill within day; back-fill the head (before first trade) with mid.
        sub_px["vwap"] = sub_px["vwap"].ffill()
        out.loc[mask, "vwap"] = sub_px["vwap"].values
    # Fill any leading NaNs (no trades yet) with mid for that row.
    out["vwap"] = out["vwap"].fillna(out["mid"].astype(float))
    return out


# ---------------------------------------------------------------------------
# Per-product statistical battery
# ---------------------------------------------------------------------------

def _safe_acf(s: pd.Series, lag: int) -> float:
    s = s.dropna()
    if len(s) <= lag + 1:
        return np.nan
    return float(s.autocorr(lag=lag))


def _adf_p(s: pd.Series) -> float:
    s = s.dropna()
    if len(s) < 50:
        return np.nan
    try:
        return float(adfuller(s.values, regression="c", autolag="AIC")[1])
    except Exception:
        return np.nan


def per_product_stats(pd_data: ProductData) -> dict:
    px, tr = pd_data.px, pd_data.tr
    if px.empty:
        return {"product": pd_data.product}
    mid = px["mid"]
    ret1 = px["ret_1"].dropna()
    spread = px["spread"]
    out: dict = {"product": pd_data.product}
    out["n_ticks"] = int(len(px))
    out["n_days"] = int(px["day"].nunique())
    out["mid_mean"] = float(mid.mean())
    out["mid_std"] = float(mid.std())
    out["mid_min"] = float(mid.min())
    out["mid_max"] = float(mid.max())
    out["mid_range"] = out["mid_max"] - out["mid_min"]

    out["ret1_mean"] = float(ret1.mean())
    out["ret1_std"] = float(ret1.std())
    out["ret1_skew"] = float(ret1.skew())
    out["ret1_kurt"] = float(ret1.kurt())
    out["adf_p_mid"] = _adf_p(mid)

    for lag in (1, 5, 20, 100):
        out[f"acf_ret1_lag{lag}"] = _safe_acf(ret1, lag)

    for k in (2, 5, 10):
        vr, z = variance_ratio(ret1.values, k)
        out[f"vr_k{k}"] = float(vr) if vr == vr else np.nan
        out[f"vr_z_k{k}"] = float(z) if z == z else np.nan

    # Hurst on log-returns is informative; on raw mid (I(1)) it pegs near 1.
    log_ret = np.log(mid).diff().dropna()
    H, r2, _, _ = hurst_rs(log_ret.values, n_max=2000)
    out["hurst"] = float(H) if H == H else np.nan
    out["hurst_r2"] = float(r2) if r2 == r2 else np.nan

    # Trade-event MR signature. Computed on trade-by-trade prices (one
    # observation per trade), not per-tick forward-filled VWAP — the
    # latter has long constant runs that bias Hurst toward 0.5.
    out["vwap_hurst"] = np.nan
    out["vwap_hurst_r2"] = np.nan
    out["vwap_adf_p"] = np.nan
    out["vwap_acf_lag1"] = np.nan
    out["vwap_to_mid_corr"] = np.nan
    if tr is not None and not tr.empty and "price" in tr.columns:
        # Per-day trade-event VWAP series: aggregate trades within the same
        # timestamp into one weighted price, then concatenate across days.
        per_event_vwap: list[pd.Series] = []
        for d, sub_tr in tr.groupby("day"):
            sub = sub_tr.copy()
            sub["pq"] = sub["price"].astype(float) * sub["quantity"].astype(float)
            ev = (sub.groupby("timestamp")
                    .agg(pq_sum=("pq", "sum"), q_sum=("quantity", "sum")))
            ev = (ev["pq_sum"] / ev["q_sum"].replace(0, np.nan)).dropna()
            per_event_vwap.append(ev)
        if per_event_vwap:
            trade_vwap = pd.concat(per_event_vwap, ignore_index=True)
            if len(trade_vwap) > 50 and (trade_vwap > 0).all():
                log_tv = np.log(trade_vwap)
                log_tv_ret = log_tv.diff().dropna()
                if len(log_tv_ret) > 50:
                    Hv, rv2, _, _ = hurst_rs(log_tv_ret.values, n_max=2000)
                    out["vwap_hurst"] = float(Hv) if Hv == Hv else np.nan
                    out["vwap_hurst_r2"] = float(rv2) if rv2 == rv2 else np.nan
                    out["vwap_adf_p"] = _adf_p(log_tv)
                    out["vwap_acf_lag1"] = _safe_acf(log_tv_ret, 1)
                    if "vwap" in px.columns:
                        out["vwap_to_mid_corr"] = float(
                            np.log(mid.replace(0, np.nan)).corr(np.log(px["vwap"].replace(0, np.nan)))
                        )

    out["spread_mean"] = float(spread.mean())
    out["spread_median"] = float(spread.median())
    out["spread_p95"] = float(spread.quantile(0.95))
    out["depth_l1_mean"] = float(px["depth_l1"].mean())
    out["depth_total_mean"] = float((px["total_bid_size"] + px["total_ask_size"]).mean())

    # Limit-10 saturation: fraction of ticks where best level has > limit shares.
    out["limit10_saturation"] = float(((px["bid_volume_1"] > POSITION_LIMIT) | (px["ask_volume_1"] > POSITION_LIMIT)).mean())

    out["quote_update_freq"] = float((mid.diff() != 0).mean())

    # Trade-side stats. Round 5 has no counterparty IDs by design; we only
    # summarise raw flow shape.
    out["n_trades"] = int(len(tr))
    if len(tr):
        out["trade_freq"] = float(len(tr) / max(len(px), 1))
        out["trade_size_mean"] = float(tr["quantity"].mean())
        out["trade_size_max"] = float(tr["quantity"].max())
    else:
        out["trade_freq"] = 0.0
        out["trade_size_mean"] = np.nan
        out["trade_size_max"] = np.nan

    return out


# ---------------------------------------------------------------------------
# Signal scorecard
# ---------------------------------------------------------------------------

def compute_signals(px: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """Build the standard signal frame on a microstructure-augmented px.

    Each signal aligned to px['timestamp'] within each day. Output one column
    per signal name in SIGNAL_NAMES.
    """
    out = pd.DataFrame(index=px.index)
    out["neg_zscore_mid_50"] = -zscore(px["mid"], 50)
    if "vwap" in px.columns:
        out["neg_zscore_vwap_50"] = -zscore(px["vwap"].astype(float), 50)
    else:
        out["neg_zscore_vwap_50"] = -zscore(px["mid"], 50)
    out["obi_l1"] = px["obi_l1"]
    out["obi_l3"] = px["obi_l3"]
    out["momentum_10"] = px["mid"] - px["mid"].shift(10)
    out["neg_spread"] = -px["spread"]

    # Trade-flow imbalance: round-5 trades are unsigned. Approximate sign by
    # comparing trade price to mid quote at the same timestamp (price >= ask
    # midpoint -> buy aggressive). Aggregated within a 20-tick rolling window.
    out["trade_imbalance"] = _signed_trade_flow(px, tr)
    return out


def _signed_trade_flow(px: pd.DataFrame, tr: pd.DataFrame, window: int = 20) -> pd.Series:
    if tr.empty:
        return pd.Series(0.0, index=px.index)
    flow = pd.Series(0.0, index=px.index)
    # Build a (day, timestamp) -> mid lookup for aggressor inference.
    px_idx = px.set_index(["day", "timestamp"])["mid"]
    sign_chunks = []
    for d, sub_tr in tr.groupby("day"):
        if d not in px["day"].values:
            continue
        sub_mid = px_idx.xs(d, level=0)
        # Forward-fill mid onto the trade timestamps.
        joined = sub_tr.merge(
            sub_mid.rename("mid_at_t").reset_index(),
            on="timestamp",
            how="left",
        )
        joined["mid_at_t"] = joined["mid_at_t"].ffill()
        sign = np.where(
            joined["price"] > joined["mid_at_t"], 1.0,
            np.where(joined["price"] < joined["mid_at_t"], -1.0, 0.0),
        )
        signed_qty = sign * joined["quantity"].astype(float)
        per_ts = (
            pd.DataFrame({"timestamp": joined["timestamp"].values, "signed_qty": signed_qty})
            .groupby("timestamp")["signed_qty"].sum()
        )
        sign_chunks.append((d, per_ts))
    # Project per-day signed flow back onto px order
    for d, per_ts in sign_chunks:
        mask = px["day"] == d
        sub = px.loc[mask, ["timestamp"]].copy()
        sub["signed_qty"] = sub["timestamp"].map(per_ts).fillna(0.0)
        flow.loc[mask] = sub["signed_qty"].rolling(window, min_periods=1).sum().values
    return flow


def signal_ic_table(
    px: pd.DataFrame,
    signals: pd.DataFrame,
    horizons: Sequence[int] = HORIZONS,
) -> pd.DataFrame:
    """IC = Pearson corr(signal_t, fwd_h_t) plus HAC-adjusted t/p.

    For overlapping forward returns at horizon h, residuals are autocorrelated
    up to lag h. Newey-West HAC with maxlag=h corrects the variance estimate.
    Naive t-tests at h=1000 with n=30000 over-state significance by ~sqrt(h);
    HAC closes that gap.
    """
    from round5.significance import hac_ic_t

    rows = []
    for sig_name in signals.columns:
        s = signals[sig_name]
        row = {"signal": sig_name}
        for h in horizons:
            f = px.get(f"fwd_{h}")
            if f is None:
                row[f"ic_h{h}"] = np.nan
                row[f"n_h{h}"] = 0
                row[f"t_h{h}"] = np.nan
                row[f"p_h{h}"] = np.nan
                continue
            ic, t, p, n = hac_ic_t(s, f, hac_lag=int(h))
            row[f"ic_h{h}"] = float(ic) if pd.notna(ic) else np.nan
            row[f"n_h{h}"] = int(n)
            row[f"t_h{h}"] = float(t) if pd.notna(t) else np.nan
            row[f"p_h{h}"] = float(p) if pd.notna(p) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Within-family relationships
# ---------------------------------------------------------------------------

def _aligned_panel(family_data: dict[str, ProductData], col: str) -> pd.DataFrame:
    series_by_p = {}
    for p, d in family_data.items():
        if d.px.empty:
            continue
        s = d.px.set_index(["day", "timestamp"])[col]
        s = s[~s.index.duplicated(keep="first")]
        series_by_p[p] = s
    if not series_by_p:
        return pd.DataFrame()
    panel = pd.DataFrame(series_by_p)
    return panel


def family_corr(family_data: dict[str, ProductData], on: str = "mid") -> pd.DataFrame:
    panel = _aligned_panel(family_data, on)
    return panel.corr() if not panel.empty else pd.DataFrame()


def lead_lag_matrix(family_data: dict[str, ProductData], lag: int = 10) -> pd.DataFrame:
    """Entry [A, B] = corr(ret_1[A]_{t}, ret_1[B]_{t+lag}). Positive [A,B]
    means A leads B by `lag` ticks."""
    panel = _aligned_panel(family_data, "ret_1")
    if panel.empty:
        return pd.DataFrame()
    products = list(panel.columns)
    out = pd.DataFrame(np.nan, index=products, columns=products)
    for a in products:
        sa = panel[a]
        for b in products:
            sb = panel[b].shift(-lag)
            joined = pd.concat([sa, sb], axis=1).dropna()
            if len(joined) < 50:
                continue
            out.loc[a, b] = joined.iloc[:, 0].corr(joined.iloc[:, 1])
    return out


def cointegration_table(family_data: dict[str, ProductData]) -> pd.DataFrame:
    # Engle-Granger is direction-asymmetric: residuals from regressing A on B
    # differ from B on A, and the ADF on those residuals can flip a pair from
    # significant to insignificant. Run both directions and keep the more
    # significant one — testing only (a, b) misses ~half of legitimate pairs.
    panel = _aligned_panel(family_data, "mid").dropna()
    products = list(panel.columns)
    rows = []
    for i, a in enumerate(products):
        for b in products[i + 1:]:
            try:
                t_ab, p_ab, _ = coint(panel[a].values, panel[b].values)
                t_ba, p_ba, _ = coint(panel[b].values, panel[a].values)
                if p_ab <= p_ba:
                    t, p = t_ab, p_ab
                else:
                    t, p = t_ba, p_ba
                rows.append({"a": a, "b": b, "coint_t": float(t), "coint_p": float(p)})
            except Exception:
                rows.append({"a": a, "b": b, "coint_t": np.nan, "coint_p": np.nan})
    return pd.DataFrame(rows)


def basis_residuals(family_data: dict[str, ProductData], a: str, b: str) -> pd.Series:
    """OLS residual of A's mid on B's mid (intercept + beta) over the aligned
    panel. Used for pair-trade band figure."""
    panel = _aligned_panel(family_data, "mid").dropna()
    if a not in panel or b not in panel:
        return pd.Series(dtype=float)
    x = panel[b].values
    y = panel[a].values
    X = np.column_stack([np.ones_like(x), x])
    coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coefs
    return pd.Series(resid, index=panel.index)


# ---------------------------------------------------------------------------
# Tradeable-ideas synthesizer
# ---------------------------------------------------------------------------

def synthesize_ideas(
    family: str,
    stats_df: pd.DataFrame,
    ic_by_product: dict[str, pd.DataFrame],
    corr_mid: pd.DataFrame,
    leadlag: pd.DataFrame,
    coint_df: pd.DataFrame,
    archetype_df: Optional[pd.DataFrame] = None,
) -> str:
    """Markdown header for the tradeable-ideas file.

    Per-product candidates are read directly from ``archetype_df`` so the
    classifier (HAC+FDR controlled) is the single source of truth — no
    parallel threshold logic. Pair / lead-lag sections still come from the
    raw within-family tables.
    """
    lines = [f"# {family} — Tradeable-Ideas Shortlist", ""]
    lines.append(f"_Auto-generated. Position limit per product = {POSITION_LIMIT}._")
    lines.append("")

    # --- Per-product candidates (mirrors archetype_df) ---
    lines.append("## Per-product candidates")
    lines.append("")
    if archetype_df is None or archetype_df.empty:
        lines.append("- _(archetype not yet computed)_")
    else:
        for _, ar in archetype_df.iterrows():
            p = ar["product"]
            arch = ar["archetype"]
            tags: list[str] = [arch]
            if ar.get("is_pair"):
                tags.append(f"PAIR_ANCHOR<->{ar.get('pair_partner') or '?'}")
            if ar.get("is_obi"):
                tags.append(
                    f"OBI_TAKER[{ar.get('obi_signal')}@h={int(ar.get('obi_horizon') or 0)}, "
                    f"IC={float(ar.get('obi_ic') or 0):+.3f}]"
                )
            params = ar.get("params") or {}
            param_str = f"  params={params}" if params else ""
            lines.append(f"- **{p}**: {' + '.join(tags)}{param_str}")
    lines.append("")

    # --- Within-family pairs (raw view; PAIR_ANCHOR flag is the canonical decision) ---
    lines.append("## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)")
    lines.append("")
    pair_lines: list[str] = []
    if not coint_df.empty and not corr_mid.empty:
        merged = coint_df.copy()
        merged["corr_mid"] = merged.apply(
            lambda row: corr_mid.loc[row["a"], row["b"]] if row["a"] in corr_mid.index and row["b"] in corr_mid.columns else np.nan,
            axis=1,
        )
        for _, r in merged.iterrows():
            if pd.notna(r["corr_mid"]) and abs(r["corr_mid"]) >= 0.7 and pd.notna(r["coint_p"]) and r["coint_p"] < 0.05:
                pair_lines.append(f"- **PAIR_TRADE**: {r['a']} ↔ {r['b']}  corr={r['corr_mid']:+.2f}, coint_p={r['coint_p']:.3f}")
    if not pair_lines:
        pair_lines.append("- _(no pairs cleared corr>0.7 + coint_p<0.05)_")
    lines.extend(pair_lines)
    lines.append("")

    # --- Lead-lag ---
    lines.append("## Lead-lag candidates (lag=10 ticks)")
    lines.append("")
    ll_lines: list[str] = []
    if not leadlag.empty:
        for a in leadlag.index:
            for b in leadlag.columns:
                if a == b:
                    continue
                v = leadlag.loc[a, b]
                if pd.notna(v) and abs(v) >= 0.10:
                    ll_lines.append(f"- **LEAD_LAG**: {a} → {b}  corr={v:+.3f}")
    if not ll_lines:
        ll_lines.append("- _(no |corr| >= 0.10 at lag=10)_")
    lines.extend(ll_lines)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_price_series(d: ProductData, out: Path) -> Path:
    px = d.px
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(px.index, px["mid"], lw=0.6, color="black", label="mid")
    ax.plot(px.index, px["bid_price_1"], lw=0.4, color="steelblue", alpha=0.6)
    ax.plot(px.index, px["ask_price_1"], lw=0.4, color="firebrick", alpha=0.6)
    for d_ in sorted(px["day"].unique())[1:]:
        boundary = px.index[px["day"] == d_].min()
        ax.axvline(boundary, color="grey", lw=0.4, ls="--")
    ax.set_title(f"{d.product} — mid + bid1/ask1")
    ax.set_xlabel("tick (concatenated days)")
    fig.tight_layout()
    p = out / f"{d.product}_price_series.png"
    _save(fig, p)
    return p


def fig_returns_hist(d: ProductData, stats: dict, out: Path) -> Path:
    ret = d.px["ret_1"].dropna()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(ret, bins=80, color="steelblue", alpha=0.7, density=True)
    if len(ret) > 1 and ret.std() > 0:
        x = np.linspace(ret.min(), ret.max(), 200)
        ax.plot(x, np.exp(-(x - ret.mean()) ** 2 / (2 * ret.var())) / np.sqrt(2 * np.pi * ret.var()),
                color="red", lw=1, label="normal")
        ax.legend()
    ax.set_title(
        f"{d.product} — ret_1  skew={stats.get('ret1_skew', float('nan')):.2f}  "
        f"kurt={stats.get('ret1_kurt', float('nan')):.2f}  ADF_p(mid)={stats.get('adf_p_mid', float('nan')):.3f}"
    )
    fig.tight_layout()
    p = out / f"{d.product}_returns_hist.png"
    _save(fig, p)
    return p


def fig_acf(d: ProductData, out: Path, max_lag: int = 200) -> Path:
    ret = d.px["ret_1"].dropna()
    n = len(ret)
    lags = np.arange(1, min(max_lag, n // 4) + 1)
    acfs = np.array([ret.autocorr(int(l)) for l in lags])
    band = 1.96 / np.sqrt(n)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(lags, acfs, color="steelblue", width=0.8)
    ax.axhline(band, color="grey", ls="--", lw=0.5)
    ax.axhline(-band, color="grey", ls="--", lw=0.5)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(f"{d.product} — ACF(ret_1) lags 1..{lags[-1]}")
    ax.set_xlabel("lag")
    fig.tight_layout()
    p = out / f"{d.product}_acf.png"
    _save(fig, p)
    return p


def fig_spread_hist(d: ProductData, stats: dict, out: Path) -> Path:
    sp = d.px["spread"].dropna()
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist(sp, bins=min(60, max(int(sp.nunique()), 5)), color="firebrick", alpha=0.7)
    ax.axvline(stats.get("spread_median", np.nan), color="black", ls="--", lw=0.6, label=f"median={stats.get('spread_median', float('nan')):.2f}")
    ax.axvline(stats.get("spread_p95", np.nan), color="grey", ls="--", lw=0.6, label=f"p95={stats.get('spread_p95', float('nan')):.2f}")
    ax.set_title(f"{d.product} — spread distribution")
    ax.set_xlabel("ask1 − bid1")
    ax.legend()
    fig.tight_layout()
    p = out / f"{d.product}_spread_hist.png"
    _save(fig, p)
    return p


def fig_depth_profile(d: ProductData, stats: dict, out: Path) -> Path:
    px = d.px
    bid_means = [
        px["bid_volume_1"].mean(),
        px.get("bid_volume_2", pd.Series([0])).mean(),
        px.get("bid_volume_3", pd.Series([0])).mean(),
    ]
    ask_means = [
        px["ask_volume_1"].mean(),
        px.get("ask_volume_2", pd.Series([0])).mean(),
        px.get("ask_volume_3", pd.Series([0])).mean(),
    ]
    levels = ["L1", "L2", "L3"]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(x - 0.2, bid_means, width=0.4, color="steelblue", label="bid")
    ax.bar(x + 0.2, ask_means, width=0.4, color="firebrick", label="ask")
    ax.set_xticks(x)
    ax.set_xticklabels(levels)
    ax.set_title(
        f"{d.product} — mean depth  lim10_sat={stats.get('limit10_saturation', float('nan')):.2f}"
    )
    ax.set_ylabel("avg quantity")
    ax.legend()
    fig.tight_layout()
    p = out / f"{d.product}_depth_profile.png"
    _save(fig, p)
    return p


def fig_obi_vs_fwd_ret(d: ProductData, out: Path, h: int = 10) -> Path:
    px = d.px[["obi_l1", f"fwd_{h}"]].dropna()
    if px.empty:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.text(0.5, 0.5, "no OBI data", ha="center")
        p = out / f"{d.product}_obi_vs_fwd_ret.png"
        _save(fig, p)
        return p
    bins = pd.cut(px["obi_l1"], bins=10)
    grouped = px.groupby(bins, observed=True)[f"fwd_{h}"].agg(["mean", "sem", "count"])
    grouped = grouped[grouped["count"] >= 20]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.errorbar(
        np.arange(len(grouped)),
        grouped["mean"].values,
        yerr=1.96 * grouped["sem"].values,
        fmt="o-",
        color="darkorange",
    )
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xticks(np.arange(len(grouped)))
    ax.set_xticklabels([str(b) for b in grouped.index], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel(f"E[fwd_{h}]")
    ax.set_title(f"{d.product} — OBI L1 vs forward return (h={h})")
    fig.tight_layout()
    p = out / f"{d.product}_obi_vs_fwd_ret.png"
    _save(fig, p)
    return p


def fig_vol_regime(d: ProductData, out: Path) -> Path:
    px = d.px
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(px.index, px["std_50"], color="purple", lw=0.6, label="std_50")
    for d_ in sorted(px["day"].unique())[1:]:
        boundary = px.index[px["day"] == d_].min()
        ax.axvline(boundary, color="grey", lw=0.4, ls="--")
    ax.set_title(f"{d.product} — rolling std_50 (vol regime)")
    ax.set_xlabel("tick")
    fig.tight_layout()
    p = out / f"{d.product}_vol_regime.png"
    _save(fig, p)
    return p


def fig_signed_flow(d: ProductData, out: Path) -> Path:
    px, tr = d.px, d.tr
    fig, ax = plt.subplots(figsize=(10, 3.5))
    if tr.empty:
        ax.text(0.5, 0.5, "no trades", ha="center", va="center")
        ax.set_axis_off()
    else:
        signal = compute_signals(px, tr)["trade_imbalance"]
        cum = signal.cumsum()
        ax.plot(cum.index, cum.values, color="seagreen", lw=0.7)
        for d_ in sorted(px["day"].unique())[1:]:
            boundary = px.index[px["day"] == d_].min()
            ax.axvline(boundary, color="grey", lw=0.4, ls="--")
        ax.axhline(0, color="black", lw=0.4)
        ax.set_title(f"{d.product} — cumulative inferred-signed trade flow")
        ax.set_xlabel("tick")
    fig.tight_layout()
    p = out / f"{d.product}_signed_flow.png"
    _save(fig, p)
    return p


def fig_family_corr(corr: pd.DataFrame, title: str, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 5))
    if corr.empty:
        ax.text(0.5, 0.5, "no data", ha="center")
    else:
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(np.arange(len(corr)))
        ax.set_yticks(np.arange(len(corr)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(corr.index, fontsize=7)
        for i in range(len(corr)):
            for j in range(len(corr)):
                v = corr.iloc[i, j]
                if pd.notna(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                            color="white" if abs(v) > 0.5 else "black", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title(title)
    fig.tight_layout()
    _save(fig, out)
    return out


def fig_lead_lag(ll: pd.DataFrame, lag: int, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 5))
    if ll.empty:
        ax.text(0.5, 0.5, "no data", ha="center")
    else:
        vmax = max(0.05, np.nanmax(np.abs(ll.values)))
        im = ax.imshow(ll.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_xticks(np.arange(len(ll)))
        ax.set_yticks(np.arange(len(ll)))
        ax.set_xticklabels(ll.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(ll.index, fontsize=7)
        for i in range(len(ll)):
            for j in range(len(ll)):
                v = ll.iloc[i, j]
                if pd.notna(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title(f"lead-lag corr (rows lead cols by {lag} ticks)")
    fig.tight_layout()
    _save(fig, out)
    return out


def fig_basis_residuals(family_data: dict[str, ProductData], corr_mid: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.5))
    if corr_mid.empty or len(family_data) < 2:
        ax.text(0.5, 0.5, "no data", ha="center")
        _save(fig, out)
        return out
    cm_arr = np.array(corr_mid.values, dtype=float, copy=True)
    np.fill_diagonal(cm_arr, 0.0)
    if not np.isfinite(cm_arr).any():
        ax.text(0.5, 0.5, "no finite correlations", ha="center")
        _save(fig, out)
        return out
    flat_idx = np.nanargmax(np.abs(cm_arr))
    a, b = np.unravel_index(flat_idx, cm_arr.shape)
    pa, pb = corr_mid.index[a], corr_mid.columns[b]
    resid = basis_residuals(family_data, pa, pb)
    if resid.empty:
        ax.text(0.5, 0.5, "no aligned data", ha="center")
    else:
        ax.plot(np.arange(len(resid)), resid.values, lw=0.5, color="black")
        sd = resid.std()
        ax.axhline(0, color="grey", lw=0.4)
        ax.axhline(2 * sd, color="red", ls="--", lw=0.5, label="±2σ")
        ax.axhline(-2 * sd, color="red", ls="--", lw=0.5)
        ax.legend()
        ax.set_title(f"basis residual: {pa} − β·{pb}  (top |corr|={cm_arr[a, b]:+.2f})")
    fig.tight_layout()
    _save(fig, out)
    return out


def fig_signal_ic_heatmap(ic_by_product: dict[str, pd.DataFrame], out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    if not ic_by_product:
        ax.text(0.5, 0.5, "no data", ha="center")
        _save(fig, out)
        return out
    products = list(ic_by_product.keys())
    sigs = list(SIGNAL_NAMES)
    horizons_cols = [c for c in ic_by_product[products[0]].columns if c.startswith("ic_h")]
    rows = []
    row_labels = []
    for p in products:
        df = ic_by_product[p].set_index("signal")
        for s in sigs:
            if s in df.index:
                rows.append([df.loc[s, h] for h in horizons_cols])
                row_labels.append(f"{p}::{s}")
    arr = np.array(rows, dtype=float) if rows else np.zeros((1, len(horizons_cols)))
    vmax = max(0.05, np.nanmax(np.abs(arr)))
    im = ax.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(np.arange(len(horizons_cols)))
    ax.set_xticklabels(horizons_cols, fontsize=8)
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=6)
    fig.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title("Signal IC heatmap (signed Pearson)")
    fig.tight_layout()
    _save(fig, out)
    return out


# ---------------------------------------------------------------------------
# End-of-pipeline summary: dashboard figure + stdout print
# ---------------------------------------------------------------------------

def fig_family_summary(
    family: str,
    family_data: dict[str, ProductData],
    stats_df: pd.DataFrame,
    ic_by_product: dict[str, pd.DataFrame],
    corr_mid: pd.DataFrame,
    out: Path,
) -> Path:
    """One-shot 2x3 dashboard: normalized mids overlay, ret_1 std bar, spread
    median bar, mid corr heatmap, signal IC heatmap (h=10), top-pair basis
    residuals."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(f"{family} — Family Summary", fontsize=13, fontweight="bold")

    # Panel A — z-scored mids overlay (so all 5 fit on one axis)
    axA = axes[0, 0]
    for p, d in family_data.items():
        if d.px.empty:
            continue
        m = d.px["mid"]
        if m.std() > 0:
            axA.plot(np.arange(len(m)), (m - m.mean()) / m.std(), lw=0.5, label=p.split("_", 1)[-1] if "_" in p else p)
    axA.axhline(0, color="black", lw=0.4)
    axA.set_title("Mids (z-scored)")
    axA.set_xlabel("tick")
    axA.legend(fontsize=7, loc="best")

    # Panel B — ret_1 std per product
    axB = axes[0, 1]
    if not stats_df.empty:
        prods = stats_df["product"].tolist()
        labels = [p.split("_", 1)[-1] if "_" in p else p for p in prods]
        axB.bar(np.arange(len(prods)), stats_df["ret1_std"].values, color="steelblue")
        axB.set_xticks(np.arange(len(prods)))
        axB.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        axB.set_title("ret_1 std (per-tick noise)")

    # Panel C — spread median per product
    axC = axes[0, 2]
    if not stats_df.empty:
        prods = stats_df["product"].tolist()
        labels = [p.split("_", 1)[-1] if "_" in p else p for p in prods]
        axC.bar(np.arange(len(prods)), stats_df["spread_median"].values, color="firebrick")
        axC.set_xticks(np.arange(len(prods)))
        axC.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        axC.set_title("spread median")

    # Panel D — mid correlation heatmap
    axD = axes[1, 0]
    if not corr_mid.empty:
        im = axD.imshow(corr_mid.values, cmap="RdBu_r", vmin=-1, vmax=1)
        labels = [c.split("_", 1)[-1] if "_" in c else c for c in corr_mid.columns]
        axD.set_xticks(np.arange(len(labels)))
        axD.set_yticks(np.arange(len(labels)))
        axD.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        axD.set_yticklabels(labels, fontsize=7)
        for i in range(len(corr_mid)):
            for j in range(len(corr_mid)):
                v = corr_mid.iloc[i, j]
                if pd.notna(v):
                    axD.text(j, i, f"{v:.2f}", ha="center", va="center",
                             color="white" if abs(v) > 0.5 else "black", fontsize=7)
        fig.colorbar(im, ax=axD, fraction=0.04)
    axD.set_title("Mid correlation")

    # Panel E — signal IC heatmap at h=10
    axE = axes[1, 1]
    if ic_by_product:
        prods = list(ic_by_product.keys())
        sigs = list(SIGNAL_NAMES)
        arr = np.full((len(sigs), len(prods)), np.nan)
        for j, p in enumerate(prods):
            df = ic_by_product[p].set_index("signal")
            for i, s in enumerate(sigs):
                if s in df.index and "ic_h10" in df.columns:
                    arr[i, j] = df.loc[s, "ic_h10"]
        vmax = max(0.05, np.nanmax(np.abs(arr)) if np.isfinite(arr).any() else 0.05)
        im = axE.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
        labels = [p.split("_", 1)[-1] if "_" in p else p for p in prods]
        axE.set_xticks(np.arange(len(prods)))
        axE.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        axE.set_yticks(np.arange(len(sigs)))
        axE.set_yticklabels(sigs, fontsize=7)
        for i in range(len(sigs)):
            for j in range(len(prods)):
                v = arr[i, j]
                if np.isfinite(v):
                    axE.text(j, i, f"{v:+.02f}", ha="center", va="center", fontsize=6,
                             color="white" if abs(v) > vmax * 0.5 else "black")
        fig.colorbar(im, ax=axE, fraction=0.04)
    axE.set_title("Signal IC @ h=10")

    # Panel F — top-pair basis residuals
    axF = axes[1, 2]
    if not corr_mid.empty and len(family_data) >= 2:
        cm_arr = np.array(corr_mid.values, dtype=float, copy=True)
        np.fill_diagonal(cm_arr, 0.0)
        if np.isfinite(cm_arr).any():
            a, b = np.unravel_index(np.nanargmax(np.abs(cm_arr)), cm_arr.shape)
            pa, pb = corr_mid.index[a], corr_mid.columns[b]
            resid = basis_residuals(family_data, pa, pb)
            if not resid.empty:
                axF.plot(np.arange(len(resid)), resid.values, lw=0.4, color="black")
                sd = resid.std()
                axF.axhline(0, color="grey", lw=0.4)
                axF.axhline(2 * sd, color="red", ls="--", lw=0.5)
                axF.axhline(-2 * sd, color="red", ls="--", lw=0.5)
                axF.set_title(
                    f"Basis: {pa.split('_', 1)[-1]} − β·{pb.split('_', 1)[-1]}  "
                    f"(corr={cm_arr[a, b]:+.2f})", fontsize=10
                )
    if not axF.has_data():
        axF.text(0.5, 0.5, "no basis pair", ha="center", va="center")
        axF.set_title("Top-pair basis residuals")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, out)
    return out


def print_family_summary(
    family: str,
    days: Sequence[int],
    stats_df: pd.DataFrame,
    ic_long: pd.DataFrame,
    corr_mid: pd.DataFrame,
    leadlag: pd.DataFrame,
    coint_df: pd.DataFrame,
    ideas_md: str,
    out_dir: Path,
    vol_summary_df: Optional[pd.DataFrame] = None,
    vci_df: Optional[pd.DataFrame] = None,
    archetype_df: Optional[pd.DataFrame] = None,
    sim_results: Optional[dict] = None,
    file: Optional[object] = None,
) -> None:
    """Pretty-print the headline results to ``file`` (default sys.stdout)."""
    if file is None:
        file = sys.stdout

    # Windows default cp1252 can't render the Unicode arrows / em-dashes used
    # in the synthesizer markdown. Reconfigure to UTF-8 with safe fallback.
    try:
        if hasattr(file, "reconfigure"):
            file.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    bar = "=" * 72
    sep = "-" * 72

    def w(*args):
        print(*args, file=file)

    w(bar)
    w(f"{family} - Family Report Summary")
    w(bar)
    w(f"days={list(days)}   products={len(stats_df)}   position_limit={POSITION_LIMIT}")
    w()

    # --- per-product stats ---
    if not stats_df.empty:
        cols = [
            "product", "mid_mean", "ret1_std", "spread_median",
            "limit10_saturation", "hurst", "vr_k5", "adf_p_mid",
            "n_trades",
        ]
        cols = [c for c in cols if c in stats_df.columns]
        compact = stats_df[cols].copy()
        for c in compact.columns:
            if c == "product":
                continue
            compact[c] = compact[c].astype(float).round(3)
        w("== Per-product stats ==")
        w(compact.to_string(index=False))
        w()

    # --- top signals by |IC| at each horizon ---
    if not ic_long.empty:
        w("== Top signals by |IC| ==")
        for h in HORIZONS:
            col = f"ic_h{h}"
            if col not in ic_long.columns:
                continue
            sub = ic_long[["product", "signal", col]].copy()
            sub["abs_ic"] = sub[col].abs()
            top = sub.sort_values("abs_ic", ascending=False, na_position="last").head(3)
            w(f"  h={h}:")
            for _, r in top.iterrows():
                if pd.notna(r[col]):
                    w(f"    {r['product']:<32s} {r['signal']:<22s} IC = {r[col]:+.4f}")
        w()

    # --- top correlations + cointegration ---
    if not corr_mid.empty:
        w("== Top |corr_mid| pairs (off-diagonal) ==")
        cm = corr_mid.copy()
        pairs = []
        prods = list(cm.columns)
        for i, a in enumerate(prods):
            for b in prods[i + 1:]:
                v = cm.loc[a, b]
                if pd.notna(v):
                    coint_p = np.nan
                    if not coint_df.empty:
                        match = coint_df[((coint_df["a"] == a) & (coint_df["b"] == b)) |
                                         ((coint_df["a"] == b) & (coint_df["b"] == a))]
                        if not match.empty:
                            coint_p = float(match["coint_p"].iloc[0])
                    pairs.append((a, b, v, coint_p))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        for a, b, v, cp in pairs[:5]:
            cp_str = f"coint_p={cp:.3f}" if pd.notna(cp) else "coint_p=NA"
            w(f"  {a} <-> {b}   corr={v:+.3f}   {cp_str}")
        w()

    # --- lead-lag candidates ---
    if not leadlag.empty:
        w("== Top |lead_lag| (lag=10) entries ==")
        ll_pairs = []
        for a in leadlag.index:
            for b in leadlag.columns:
                if a == b:
                    continue
                v = leadlag.loc[a, b]
                if pd.notna(v):
                    ll_pairs.append((a, b, v))
        ll_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        for a, b, v in ll_pairs[:5]:
            w(f"  {a} -> {b}   corr={v:+.4f}")
        w()

    # --- volatility summary ---
    if vol_summary_df is not None and not vol_summary_df.empty:
        w("== Volatility summary ==")
        cols = [
            "product", "rv_50_mean", "vol_of_vol",
            "vol_p90_p10_ratio", "vol_cluster_lag1", "vol_cluster_lag10",
        ]
        cols = [c for c in cols if c in vol_summary_df.columns]
        compact = vol_summary_df[cols].copy()
        for c in compact.columns:
            if c == "product":
                continue
            compact[c] = compact[c].astype(float).round(4)
        w(compact.to_string(index=False))
        w()

    # --- regime-gated signals (highest IC@h=10 per regime) ---
    if vci_df is not None and not vci_df.empty:
        w("== Top signal × regime (h=10) by |IC| ==")
        sub = vci_df[vci_df["horizon"] == 10].copy()
        sub["abs_ic"] = sub["ic"].abs()
        top = sub.sort_values("abs_ic", ascending=False, na_position="last").head(8)
        for _, r in top.iterrows():
            if pd.notna(r["ic"]):
                w(f"  {r['product']:<32s} {r['signal']:<22s} regime={r['regime']:<5s} "
                  f"IC = {r['ic']:+.4f}  (n={int(r['n'])})")
        w()

    # --- archetype assignment ---
    if archetype_df is not None and not archetype_df.empty:
        w("== Archetype assignment ==")
        counts = archetype_df["archetype"].value_counts()
        for arch in ("MR_TAKER", "MOMENTUM", "RANDOM_WALK", "NO_EDGE"):
            n = int(counts.get(arch, 0))
            w(f"  {arch:<14s} : {n}")
        if "is_pair" in archetype_df.columns:
            w(f"  {'PAIR_ANCHOR':<14s} : {int(archetype_df['is_pair'].sum())}  (orthogonal flag)")
        w()
        # Data-quality warnings inline (only if any non-empty)
        warned = archetype_df[archetype_df["rationale"].astype(str).str.contains("DATA_QUALITY_WARN", na=False)]
        if not warned.empty:
            w("== Data quality warnings ==")
            for _, r in warned.iterrows():
                w(f"  {r['product']}: {r['rationale']}")
            w()
        # RW simulation summary, if any
        if sim_results:
            w("== RANDOM_WALK simulation gate ==")
            for p, sim in sim_results.items():
                pnl = sim.get("pnl_total", 0.0)
                fills = sim.get("n_fills", 0)
                inv = sim.get("max_inventory_abs", 0)
                # Verdict from final archetype after potential downgrade
                row = archetype_df[archetype_df["product"] == p]
                verdict = row["archetype"].iloc[0] if not row.empty else "?"
                w(f"  {p:<32s} pnl={pnl:+.2f}  fills={fills:>4d}  max|inv|={inv:>2d}  -> {verdict}")
            w()

    # --- tradeable ideas (auto-flagged) ---
    if ideas_md:
        w("== Tradeable ideas (auto-flagged) ==")
        # Re-emit the body sans the redundant H1; keep section structure.
        for ln in ideas_md.splitlines():
            if ln.startswith("# "):
                continue
            w(ln)
        w()

    w(sep)
    w(f"artifacts: {out_dir}")
    w(bar)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def family_report(
    family: str,
    out_dir: Path | str = Path("round5/reports"),
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
    verbose: bool = True,
    deep: bool = False,
) -> Path:
    out_dir = Path(out_dir) / family
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[{family}] loading + microstructure ...")
    family_data = load_family(family, days=days, root=root)

    if verbose:
        print(f"[{family}] per-product stats + signals ...")
    stat_rows = []
    ic_by_product: dict[str, pd.DataFrame] = {}
    micro_rows = []
    for p, d in family_data.items():
        s = per_product_stats(d)
        stat_rows.append(s)
        if not d.px.empty:
            sigs = compute_signals(d.px, d.tr)
            ic = signal_ic_table(d.px, sigs, horizons=HORIZONS)
            ic.insert(0, "product", p)
            ic_by_product[p] = ic
            micro_rows.append({
                "product": p,
                "spread_mean": s.get("spread_mean"),
                "spread_median": s.get("spread_median"),
                "spread_p95": s.get("spread_p95"),
                "depth_l1_mean": s.get("depth_l1_mean"),
                "depth_total_mean": s.get("depth_total_mean"),
                "limit10_saturation": s.get("limit10_saturation"),
                "quote_update_freq": s.get("quote_update_freq"),
                "trade_freq": s.get("trade_freq"),
                "n_trades": s.get("n_trades"),
                "trade_size_mean": s.get("trade_size_mean"),
            })

    stats_df = pd.DataFrame(stat_rows)
    micro_df = pd.DataFrame(micro_rows)
    ic_long = pd.concat(ic_by_product.values(), ignore_index=True) if ic_by_product else pd.DataFrame()

    stats_df.to_csv(out_dir / "stats_per_product.csv", index=False)
    micro_df.to_csv(out_dir / "microstructure.csv", index=False)
    ic_long.to_csv(out_dir / "signals_ic.csv", index=False)

    if verbose:
        print(f"[{family}] within-family relationships ...")
    corr_mid = family_corr(family_data, on="mid")
    corr_ret = family_corr(family_data, on="ret_1")
    leadlag = lead_lag_matrix(family_data, lag=10)
    coint_df = cointegration_table(family_data)

    corr_mid.to_csv(out_dir / "corr_mid.csv")
    corr_ret.to_csv(out_dir / "corr_returns.csv")
    leadlag.to_csv(out_dir / "lead_lag.csv")
    coint_df.to_csv(out_dir / "cointegration.csv", index=False)

    if verbose:
        print(f"[{family}] figures ...")
    for p, d in family_data.items():
        if d.px.empty:
            continue
        s = next(r for r in stat_rows if r["product"] == p)
        fig_price_series(d, fig_dir)
        fig_returns_hist(d, s, fig_dir)
        fig_acf(d, fig_dir)
        fig_spread_hist(d, s, fig_dir)
        fig_depth_profile(d, s, fig_dir)
        fig_obi_vs_fwd_ret(d, fig_dir)
        fig_vol_regime(d, fig_dir)
        fig_signed_flow(d, fig_dir)
    fig_family_corr(corr_mid, "Family corr — mid", fig_dir / "family_corr_mid.png")
    fig_family_corr(corr_ret, "Family corr — ret_1", fig_dir / "family_corr_returns.png")
    fig_lead_lag(leadlag, 10, fig_dir / "family_lead_lag.png")
    fig_basis_residuals(family_data, corr_mid, fig_dir / "family_basis_residuals.png")
    fig_signal_ic_heatmap(ic_by_product, fig_dir / "family_signal_ic_heatmap.png")

    if verbose:
        print(f"[{family}] family-summary dashboard ...")
    fig_family_summary(family, family_data, stats_df, ic_by_product, corr_mid,
                       fig_dir / "family_summary.png")

    # ---- Volatility analysis (always run; cheap) ----
    if verbose:
        print(f"[{family}] volatility + vol-conditioned IC ...")
    from round5 import volatility as vol_mod
    vol_summary_rows = []
    vol_regime_rows: list[pd.DataFrame] = []
    vol_transitions: dict[str, pd.DataFrame] = {}
    vci_rows: list[pd.DataFrame] = []
    for p, d in family_data.items():
        if d.px.empty:
            continue
        vol_summary_rows.append(vol_mod.volatility_stats(d))
        rt = vol_mod.vol_regime_table(d)
        if not rt.empty:
            vol_regime_rows.append(rt)
        tr = vol_mod.vol_regime_transitions(d)
        if not tr.empty:
            vol_transitions[p] = tr
        sigs = compute_signals(d.px, d.tr)
        vci_p = vol_mod.vol_conditioned_ic(d, sigs)
        if not vci_p.empty:
            vci_rows.append(vci_p)
            vol_mod.fig_vol_panel(d, vci_p, fig_dir / f"{p}_vol_panel.png")

    vol_summary_df = pd.DataFrame(vol_summary_rows)
    vol_regime_df = pd.concat(vol_regime_rows, ignore_index=True) if vol_regime_rows else pd.DataFrame()
    vci_df = pd.concat(vci_rows, ignore_index=True) if vci_rows else pd.DataFrame()
    vol_summary_df.to_csv(out_dir / "volatility.csv", index=False)
    vol_regime_df.to_csv(out_dir / "vol_regime.csv", index=False)
    vci_df.to_csv(out_dir / "vol_conditioned_ic.csv", index=False)
    if vol_transitions:
        rows = []
        for p, m in vol_transitions.items():
            for f_ in m.index:
                for t_ in m.columns:
                    rows.append({"product": p, "from": f_, "to": t_, "p": float(m.loc[f_, t_]) if pd.notna(m.loc[f_, t_]) else np.nan})
        pd.DataFrame(rows).to_csv(out_dir / "vol_regime_transitions.csv", index=False)
    vol_mod.fig_family_vol_compare(family_data, fig_dir / "family_vol_compare.png")

    vol_md = vol_mod.vol_trading_recommendations(vol_summary_df, vol_regime_df, vci_df, ic_long)

    # ---- Data quality checks ----
    if verbose:
        print(f"[{family}] data-quality checks ...")
    from round5 import data_quality as dq
    quality_df = dq.family_quality_report(family_data)
    quality_df.to_csv(out_dir / "data_quality.csv", index=False)

    # ---- Significance augmentation on IC table ----
    if verbose:
        print(f"[{family}] adding significance columns to IC table ...")
    from round5 import significance as sig
    if not ic_long.empty:
        ic_long = sig.add_significance_columns(ic_long)
        ic_long.to_csv(out_dir / "signals_ic.csv", index=False)
        # Also re-augment the per-product cached frames so the classifier sees
        # the FDR column.
        for p in list(ic_by_product):
            ic_by_product[p] = sig.add_significance_columns(ic_by_product[p])

    # ---- Archetype classification + RW simulation gate ----
    if verbose:
        print(f"[{family}] archetype classification ...")
    from round5 import archetypes as ar
    archetype_df = ar.assign_archetypes(
        family_data=family_data,
        stats_df=stats_df,
        ic_by_product=ic_by_product,
        corr_mid=corr_mid,
        coint_df=coint_df,
        vol_summary_df=vol_summary_df,
        quality_df=quality_df,
    )
    sim_results = ar.run_rw_simulation_gate(
        family_data=family_data,
        archetype_df=archetype_df,
        out_dir=out_dir,
        verbose=verbose,
    )
    archetype_df.to_csv(out_dir / "archetype_assignment.csv", index=False)
    arch_md = ar.archetype_summary_md(archetype_df, sim_results)

    if verbose:
        print(f"[{family}] tradeable-ideas synthesis ...")
    md = synthesize_ideas(
        family, stats_df, ic_by_product, corr_mid, leadlag, coint_df,
        archetype_df=archetype_df,
    )
    md = md.rstrip() + "\n\n" + vol_md.rstrip() + "\n\n" + arch_md
    (out_dir / "tradeable_ideas.md").write_text(md, encoding="utf-8")

    # ---- Deep-dive triggers (always written; cheap) ----
    from round5 import deep_research as dr
    triggers = dr.detect_triggers(stats_df, ic_by_product, corr_mid, corr_ret, coint_df)
    dr.write_triggers_report(triggers, out_dir / "deep_triggers.md")

    # ---- Optional deep dives ----
    if deep:
        if verbose:
            print(f"[{family}] running deep dives "
                  f"(mr={len(triggers.mr)}, trending={len(triggers.trending)}, "
                  f"pairs={len(triggers.pairs)}) ...")
        dr.run_deep_research(family, family_data, triggers, out_dir, verbose=verbose)
    elif verbose:
        n = len(triggers.mr) + len(triggers.trending) + len(triggers.pairs)
        if n:
            print(f"[{family}] deep-dive triggers: {n} candidate(s) "
                  f"(mr={len(triggers.mr)}, trending={len(triggers.trending)}, "
                  f"pairs={len(triggers.pairs)}). re-run with --deep to execute.")
        else:
            print(f"[{family}] no deep-dive triggers fired.")

    if verbose:
        print(f"[{family}] done -> {out_dir}\n")
        print_family_summary(
            family=family,
            days=days,
            stats_df=stats_df,
            ic_long=ic_long,
            corr_mid=corr_mid,
            leadlag=leadlag,
            coint_df=coint_df,
            ideas_md=md,
            out_dir=out_dir,
            vol_summary_df=vol_summary_df,
            vci_df=vci_df,
            archetype_df=archetype_df,
            sim_results=sim_results,
        )
    return out_dir
