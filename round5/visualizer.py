"""Streamlit visualizer for the round-5 pipeline outputs.

Run from repo root::

    .venv/Scripts/streamlit.exe run round5/visualizer.py

Six views in the sidebar:
    1. Universe Overview  — 50-product table, archetype distribution, filters.
    2. Family Drilldown    — per-family stats, within-family heatmaps + figures.
    3. Product Detail      — full per-product card with IC heatmap + figures.
    4. Cross-Family        — clustering + lead-lag findings.
    5. Vol Spikes          — 4σ event study, post-spike profile, co-occurrence.
    6. Calibration         — gate threshold validation.

Reads from ``round5/reports/`` (no recomputation). Cache decorators keep the
DataFrames warm across reruns. To refresh after a pipeline rerun, hit
``Rerun`` in the Streamlit toolbar (clears the cache).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5.research_lib import FAMILIES, HORIZONS, SIGNAL_NAMES  # noqa: E402

REPORTS = HERE / "reports"
ALL_PRODUCTS = [p for fam in FAMILIES.values() for p in fam]
PRODUCT_TO_FAMILY = {p: fam for fam, members in FAMILIES.items() for p in members}


# ---------------------------------------------------------------------------
# Data loaders (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_archetypes() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "archetype_assignment.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    # Coerce flag columns.
    for col in ["is_pair", "is_obi", "is_mm", "mr_ic_verified", "pair_residual_stationary"]:
        if col in out.columns:
            out[col] = out[col].fillna(False).astype(bool)
    return out


@st.cache_data
def load_stats() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "stats_per_product.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


@st.cache_data
def load_micro() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "microstructure.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


@st.cache_data
def load_ic_long() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "signals_ic.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


@st.cache_data
def load_volatility() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "volatility.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


@st.cache_data
def load_data_quality() -> pd.DataFrame:
    rows = []
    for fam in FAMILIES:
        f = REPORTS / fam / "data_quality.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df["family"] = fam
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


@st.cache_data
def load_vol_regime(fam: str) -> pd.DataFrame:
    f = REPORTS / fam / "vol_regime.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_vol_regime_transitions(fam: str) -> pd.DataFrame:
    f = REPORTS / fam / "vol_regime_transitions.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_vol_conditioned_ic(fam: str) -> pd.DataFrame:
    f = REPORTS / fam / "vol_conditioned_ic.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_deep_triggers(fam: str) -> str:
    f = REPORTS / fam / "deep_triggers.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# Raw px/tr loaders — day-level CSVs cached once, then per-product filter.
DATASET_ROOT_VIZ = ROOT / "dataset" / "ROUND_5"
DEFAULT_DAYS = (2, 3, 4)


@st.cache_data
def _load_day_prices_csv(day: int) -> pd.DataFrame:
    f = DATASET_ROOT_VIZ / f"prices_round_5_day_{day}.csv"
    return pd.read_csv(f, sep=";")


@st.cache_data
def _load_day_trades_csv(day: int) -> pd.DataFrame:
    f = DATASET_ROOT_VIZ / f"trades_round_5_day_{day}.csv"
    return pd.read_csv(f, sep=";")


@st.cache_data
def load_product_px_tr(product: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load microstructure-augmented prices + raw trades for one product
    across all three days. Cached after first call.
    """
    from round5.research_lib import add_microstructure, add_vwap

    px_frames, tr_frames = [], []
    for d in DEFAULT_DAYS:
        df = _load_day_prices_csv(d)
        sub = df[df["product"] == product].copy()
        sub["day"] = d
        sub = sub.sort_values("timestamp").reset_index(drop=True)
        px_frames.append(sub)

        tdf = _load_day_trades_csv(d)
        tsub = tdf[tdf["symbol"] == product].copy()
        tsub["day"] = d
        tsub = tsub.sort_values("timestamp").reset_index(drop=True)
        tr_frames.append(tsub)

    px = pd.concat(px_frames, ignore_index=True) if px_frames else pd.DataFrame()
    tr = pd.concat(tr_frames, ignore_index=True) if tr_frames else pd.DataFrame()
    if not px.empty:
        px = add_microstructure(px)
        px = add_vwap(px, tr)
    return px, tr


@st.cache_data
def load_family_matrix(fam: str, kind: str) -> pd.DataFrame:
    """``kind`` one of: corr_mid, corr_returns, lead_lag."""
    f = REPORTS / fam / f"{kind}.csv"
    if not f.exists():
        return pd.DataFrame()
    return pd.read_csv(f, index_col=0)


@st.cache_data
def load_cointegration(fam: str) -> pd.DataFrame:
    f = REPORTS / fam / "cointegration.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_calibration() -> pd.DataFrame:
    f = REPORTS / "CALIBRATION" / "threshold_calibration.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_calibration_panel() -> pd.DataFrame:
    f = REPORTS / "CALIBRATION" / "calibration_panel.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_cross_findings_md() -> str:
    f = REPORTS / "CROSS" / "cross_findings.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


@st.cache_data
def load_cross_pairs() -> pd.DataFrame:
    f = REPORTS / "CROSS" / "leadlag_stable_pairs.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_cross_clusters() -> pd.DataFrame:
    f = REPORTS / "CROSS" / "clusters.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_cluster_perf() -> pd.DataFrame:
    f = REPORTS / "CROSS" / "cluster_rolling_performance.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_cluster_aggregate() -> pd.DataFrame:
    f = REPORTS / "CROSS" / "cluster_aggregate.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_leadlag_full() -> pd.DataFrame:
    f = REPORTS / "CROSS" / "leadlag_full.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


# Volatility-spike study (round5/vol_spikes.py)
VOL_SPIKES_DIR = REPORTS / "CROSS" / "vol_spikes"


@st.cache_data
def load_spike_summary() -> pd.DataFrame:
    f = VOL_SPIKES_DIR / "spike_summary.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_cooccurrence() -> pd.DataFrame:
    f = VOL_SPIKES_DIR / "spike_cooccurrence.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_cooccurrence_matrix() -> pd.DataFrame:
    f = VOL_SPIKES_DIR / "spike_cooccurrence_matrix.csv"
    return pd.read_csv(f, index_col=0) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_post_returns() -> pd.DataFrame:
    f = VOL_SPIKES_DIR / "spike_post_returns.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_family_summary() -> pd.DataFrame:
    f = VOL_SPIKES_DIR / "family_summary.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_report_md() -> str:
    f = VOL_SPIKES_DIR / "vol_spikes_report.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


SPIKE_ANATOMY_DIR = VOL_SPIKES_DIR / "anatomy"


@st.cache_data
def load_spike_anatomy() -> pd.DataFrame:
    f = SPIKE_ANATOMY_DIR / "spike_anatomy.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_recovery() -> pd.DataFrame:
    f = SPIKE_ANATOMY_DIR / "spike_recovery_curve.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_strategy_pnl() -> pd.DataFrame:
    f = SPIKE_ANATOMY_DIR / "spike_strategy_pnl.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_spike_mechanism_report_md() -> str:
    f = SPIKE_ANATOMY_DIR / "spike_mechanism_report.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def figure_path(fam: str, name: str) -> Path:
    return REPORTS / fam / "figures" / name


# ---------------------------------------------------------------------------
# Interactive Plotly plot helpers (build figures from px/tr DataFrames)
# ---------------------------------------------------------------------------

def _x_index(px: pd.DataFrame) -> np.ndarray:
    """Concatenated tick index (1..N) so x-axis is monotone across days."""
    return np.arange(len(px))


def _day_boundaries(px: pd.DataFrame) -> list[int]:
    out = []
    for d in sorted(px["day"].unique())[1:]:
        idx = px.index[px["day"] == d].min()
        out.append(int(idx))
    return out


def plot_price_series(px: pd.DataFrame, tr: pd.DataFrame, sample_step: int = 1) -> go.Figure:
    """Mid + bid₁ / ask₁ + VWAP overlay + day boundaries. Uses WebGL traces
    so 30k points scroll smoothly. Hover shows day, timestamp, all four prices.
    """
    if px.empty:
        return go.Figure()
    sub = px.iloc[::sample_step].copy()
    x = sub.index
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=x, y=sub["mid"], mode="lines",
                                name="mid", line=dict(color="black", width=1.0),
                                hovertemplate="day=%{customdata[0]}<br>ts=%{customdata[1]}<br>mid=%{y}<extra></extra>",
                                customdata=sub[["day", "timestamp"]].values))
    fig.add_trace(go.Scattergl(x=x, y=sub["bid_price_1"], mode="lines",
                                name="bid₁", line=dict(color="steelblue", width=0.6),
                                opacity=0.6, hovertemplate="bid₁=%{y}<extra></extra>"))
    fig.add_trace(go.Scattergl(x=x, y=sub["ask_price_1"], mode="lines",
                                name="ask₁", line=dict(color="firebrick", width=0.6),
                                opacity=0.6, hovertemplate="ask₁=%{y}<extra></extra>"))
    if "vwap" in sub.columns:
        fig.add_trace(go.Scattergl(x=x, y=sub["vwap"], mode="lines",
                                    name="trade VWAP", line=dict(color="orange", width=0.8, dash="dot"),
                                    opacity=0.8, hovertemplate="vwap=%{y}<extra></extra>"))
    for b in _day_boundaries(px):
        fig.add_vline(x=b, line_color="grey", line_dash="dash", line_width=1, opacity=0.5)
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="tick (concatenated days, vertical lines = day boundaries)",
                       yaxis_title="price",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def plot_returns_hist(px: pd.DataFrame, n_bins: int = 80) -> go.Figure:
    if px.empty or "ret_1" not in px.columns:
        return go.Figure()
    s = px["ret_1"].dropna()
    fig = go.Figure(go.Histogram(x=s, nbinsx=n_bins, marker_color="seagreen",
                                  hovertemplate="ret_1 ∈ [%{x}]<br>n=%{y}<extra></extra>"))
    mean = float(s.mean())
    std = float(s.std())
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.add_vline(x=mean, line_color="red", line_dash="dash",
                  annotation_text=f"μ={mean:+.2f}", annotation_position="top right")
    fig.add_vline(x=mean + std, line_color="grey", line_dash="dot",
                  annotation_text="μ+σ", annotation_position="top right")
    fig.add_vline(x=mean - std, line_color="grey", line_dash="dot",
                  annotation_text="μ-σ", annotation_position="top left")
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="ret_1 (mid diff per tick)",
                       yaxis_title="count")
    return fig


def plot_acf(px: pd.DataFrame, max_lag: int = 100) -> go.Figure:
    """ACF of ret_1 with Bartlett ±1.96/√n confidence band."""
    if px.empty or "ret_1" not in px.columns:
        return go.Figure()
    s = px["ret_1"].dropna()
    n = len(s)
    if n < 10:
        return go.Figure()
    lags = np.arange(1, max_lag + 1)
    vals = np.array([s.autocorr(lag=int(k)) for k in lags])
    band = 1.96 / np.sqrt(n) if n > 0 else 0
    sig = (np.abs(vals) > band)
    colors = ["#d62728" if s_ else "#7f7f7f" for s_ in sig]
    fig = go.Figure(go.Bar(x=lags, y=vals, marker_color=colors,
                            hovertemplate="lag=%{x}<br>ACF=%{y:+.4f}<extra></extra>"))
    fig.add_hrect(y0=-band, y1=band, line_width=0, fillcolor="grey", opacity=0.15,
                  annotation_text=f"±1.96/√n = ±{band:.3f}", annotation_position="top right")
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="lag (ticks)", yaxis_title="ACF(ret_1)",
                       title=f"Bars outside grey band = significant at 95% (n={n})")
    return fig


def plot_spread_hist(px: pd.DataFrame, n_bins: int = 60) -> go.Figure:
    if px.empty or "spread" not in px.columns:
        return go.Figure()
    s = px["spread"].dropna()
    fig = go.Figure(go.Histogram(x=s, nbinsx=n_bins, marker_color="steelblue"))
    med = float(s.median())
    p95 = float(s.quantile(0.95))
    fig.add_vline(x=med, line_color="red", line_dash="dash",
                  annotation_text=f"median={med:.2f}", annotation_position="top right")
    fig.add_vline(x=p95, line_color="orange", line_dash="dot",
                  annotation_text=f"p95={p95:.2f}", annotation_position="top right")
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="spread (ask − bid)", yaxis_title="count")
    return fig


def plot_depth_profile(px: pd.DataFrame) -> go.Figure:
    """Mean bid/ask volume at L1, L2, L3."""
    if px.empty:
        return go.Figure()
    levels = ["L1", "L2", "L3"]
    bid_means = [px[f"bid_volume_{i}"].mean() for i in (1, 2, 3) if f"bid_volume_{i}" in px.columns]
    ask_means = [px[f"ask_volume_{i}"].mean() for i in (1, 2, 3) if f"ask_volume_{i}" in px.columns]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="bid", x=levels[:len(bid_means)], y=bid_means,
                          marker_color="steelblue",
                          hovertemplate="%{x}<br>mean bid vol=%{y:.1f}<extra></extra>"))
    fig.add_trace(go.Bar(name="ask", x=levels[:len(ask_means)], y=ask_means,
                          marker_color="firebrick",
                          hovertemplate="%{x}<br>mean ask vol=%{y:.1f}<extra></extra>"))
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="book level", yaxis_title="mean volume",
                       barmode="group")
    return fig


def plot_obi_vs_fwd_ret(px: pd.DataFrame, horizon: int = 10, sample: int = 5000) -> go.Figure:
    """Scatter of obi_l1 vs forward h-tick return. Bins x-axis into deciles
    and overlays the regression line of fwd_ret on obi_l1.
    """
    col_fwd = f"fwd_{horizon}"
    if px.empty or "obi_l1" not in px.columns or col_fwd not in px.columns:
        return go.Figure()
    s = px[["obi_l1", col_fwd]].dropna()
    if len(s) < 100:
        return go.Figure()
    # Downsample for scatter
    s_plot = s.sample(n=min(sample, len(s)), random_state=0) if len(s) > sample else s

    # Decile means (more legible than raw scatter)
    s["q"] = pd.qcut(s["obi_l1"], 10, labels=False, duplicates="drop")
    decile = s.groupby("q").agg(obi_mean=("obi_l1", "mean"),
                                 fwd_mean=(col_fwd, "mean"),
                                 fwd_se=(col_fwd, lambda x: x.std() / np.sqrt(len(x)))).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=s_plot["obi_l1"], y=s_plot[col_fwd], mode="markers",
                                marker=dict(color="lightgrey", size=3, opacity=0.4),
                                name="ticks (sample)", showlegend=True,
                                hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=decile["obi_mean"], y=decile["fwd_mean"],
                              error_y=dict(type="data", array=decile["fwd_se"], visible=True),
                              mode="lines+markers", line=dict(color="firebrick", width=2),
                              marker=dict(size=8), name="decile mean ±SE",
                              hovertemplate="OBI decile mean=%{x:+.2f}<br>fwd_ret mean=%{y:+.4f}<extra></extra>"))
    # Linear fit
    if len(s) > 1:
        coef = np.polyfit(s["obi_l1"], s[col_fwd], 1)
        xs = np.linspace(s["obi_l1"].min(), s["obi_l1"].max(), 100)
        ys = coef[0] * xs + coef[1]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="black", dash="dot"),
                                  name=f"OLS slope={coef[0]:+.4f}",
                                  hoverinfo="skip"))
    fig.add_hline(y=0, line_color="grey", line_width=0.6)
    fig.add_vline(x=0, line_color="grey", line_width=0.6)
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="obi_l1 (-1=bid empty, +1=ask empty)",
                       yaxis_title=f"fwd_ret over h={horizon} ticks")
    return fig


def plot_signed_flow(px: pd.DataFrame, tr: pd.DataFrame) -> go.Figure:
    """Cumulative signed trade flow per day."""
    if tr is None or tr.empty:
        return go.Figure()
    tr_calc = tr.copy()
    # Forward-fill mid onto trades
    px_idx = px.set_index(["day", "timestamp"])["mid"]
    tr_calc["mid_at_t"] = tr_calc.apply(
        lambda r: px_idx.get((r["day"], r["timestamp"]), np.nan), axis=1
    )
    # Sign by trade price vs mid quote
    tr_calc["sign"] = np.where(tr_calc["price"] > tr_calc["mid_at_t"], 1.0,
                                np.where(tr_calc["price"] < tr_calc["mid_at_t"], -1.0, 0.0))
    tr_calc["signed_qty"] = tr_calc["sign"] * tr_calc["quantity"].astype(float)
    fig = go.Figure()
    for d, sub in tr_calc.groupby("day"):
        sub = sub.sort_values("timestamp").copy()
        sub["cum"] = sub["signed_qty"].cumsum()
        fig.add_trace(go.Scattergl(x=sub["timestamp"], y=sub["cum"], mode="lines",
                                    name=f"day {d}",
                                    hovertemplate=f"day={d}<br>ts=%{{x}}<br>cum signed qty=%{{y}}<extra></extra>"))
    fig.add_hline(y=0, line_color="grey", line_width=0.6)
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="timestamp (within day)",
                       yaxis_title="cumulative signed trade qty")
    return fig


def plot_vol_over_time(px: pd.DataFrame) -> go.Figure:
    """std_50 over time with low/mid/high tertile bands."""
    if px.empty or "std_50" not in px.columns:
        return go.Figure()
    s = px["std_50"].dropna()
    if len(s) < 30:
        return go.Figure()
    qs = s.quantile([1/3, 2/3]).values
    fig = go.Figure(go.Scattergl(x=np.arange(len(px)), y=px["std_50"], mode="lines",
                                  line=dict(color="purple", width=0.8), name="std_50",
                                  hovertemplate="tick=%{x}<br>std_50=%{y:.3f}<extra></extra>"))
    fig.add_hrect(y0=0, y1=qs[0], fillcolor="green", opacity=0.08, line_width=0,
                  annotation_text="LOW", annotation_position="left top")
    fig.add_hrect(y0=qs[0], y1=qs[1], fillcolor="yellow", opacity=0.08, line_width=0,
                  annotation_text="MID", annotation_position="left top")
    fig.add_hrect(y0=qs[1], y1=float(s.max()) * 1.1, fillcolor="red", opacity=0.08, line_width=0,
                  annotation_text="HIGH", annotation_position="left top")
    for b in _day_boundaries(px):
        fig.add_vline(x=b, line_color="grey", line_dash="dash", line_width=1, opacity=0.4)
    fig.update_layout(height=320, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="tick", yaxis_title="std_50 (rolling 50-tick std of ret_1)")
    return fig


def plot_ic_bars(ic_p: pd.DataFrame, horizons: tuple, mr_signals_only: bool = False) -> go.Figure:
    """Horizontal grouped bar chart of IC across (signal, horizon) cells.

    More readable than a heatmap because:
      - Bar length encodes |IC| magnitude directly (not via colour).
      - Sign is unambiguous (left vs right of zero).
      - Significant cells (FDR-pass) are filled solid; others hollow / lower opacity.
      - Horizons are colour-coded — switching between them is instant.
    """
    if ic_p.empty:
        return go.Figure()
    rows = []
    for _, r in ic_p.iterrows():
        sig = r["signal"]
        if mr_signals_only and "zscore" not in sig:
            continue
        for h in horizons:
            ic = r.get(f"ic_h{h}")
            p = r.get(f"p_h{h}")
            t = r.get(f"t_h{h}")
            sig_pass = bool(r.get("significant", False)) and pd.notna(p) and p < 0.05
            if pd.notna(ic):
                rows.append({"signal": sig, "horizon": f"h={h}",
                             "ic": float(ic),
                             "abs_ic": abs(float(ic)),
                             "t": float(t) if pd.notna(t) else None,
                             "p": float(p) if pd.notna(p) else None,
                             "fdr_pass": sig_pass})
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    # Order signals by max |IC| descending
    sig_order = df.groupby("signal")["abs_ic"].max().sort_values(ascending=False).index.tolist()
    df["signal"] = pd.Categorical(df["signal"], categories=sig_order[::-1], ordered=True)

    h_palette = {f"h={h}": c for h, c in zip(horizons, ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])}
    fig = go.Figure()
    for h_label in [f"h={h}" for h in horizons]:
        sub = df[df["horizon"] == h_label].sort_values("signal")
        # Solid bar for FDR-pass, hollow (opacity 0.4) for not.
        opacities = sub["fdr_pass"].map({True: 1.0, False: 0.35}).values
        marker_line_width = sub["fdr_pass"].map({True: 0, False: 1.2}).values
        fig.add_trace(go.Bar(
            y=sub["signal"], x=sub["ic"],
            orientation="h", name=h_label,
            marker=dict(color=h_palette[h_label],
                        opacity=opacities,
                        line=dict(color=h_palette[h_label], width=marker_line_width)),
            text=[f"{v:+.3f}" for v in sub["ic"]],
            textposition="outside",
            hovertemplate=("signal=%{y}<br>"
                           f"horizon={h_label}<br>"
                           "IC=%{x:+.4f}<br>"
                           "t=%{customdata[0]:+.2f}<br>"
                           "p=%{customdata[1]:.3g}<br>"
                           "FDR-pass=%{customdata[2]}<extra></extra>"),
            customdata=sub[["t", "p", "fdr_pass"]].values,
        ))
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_layout(
        height=max(280, 70 + 60 * len(sig_order)),
        margin=dict(t=20, b=30, l=10, r=10),
        barmode="group",
        xaxis_title="HAC IC (signed)",
        yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_ic_lines(ic_p: pd.DataFrame, horizons: tuple) -> go.Figure:
    """Alternative IC view: line per signal with horizon on x-axis (log scale).
    Reveals decay shape over horizons.
    """
    if ic_p.empty:
        return go.Figure()
    rows = []
    for _, r in ic_p.iterrows():
        for h in horizons:
            ic = r.get(f"ic_h{h}")
            p = r.get(f"p_h{h}")
            if pd.notna(ic):
                rows.append({"signal": r["signal"], "horizon": h,
                             "ic": float(ic),
                             "p": float(p) if pd.notna(p) else None})
    df = pd.DataFrame(rows)
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="horizon", y="ic", color="signal", markers=True, log_x=True,
                  hover_data={"horizon": True, "ic": ":+.4f", "p": ":.3g"})
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                       xaxis_title="forward-return horizon (ticks, log scale)",
                       yaxis_title="HAC IC (signed)",
                       legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02))
    return fig


def plot_mm_health(px: pd.DataFrame, tr: pd.DataFrame, params: dict, sample_window: int = 2000) -> go.Figure:
    """Three-panel interactive MM-health figure (replaces mm_health.png).

    Top: mid + bid/ask quotes within a sample window (full series too dense).
    Middle: inventory across the full simulation.
    Bottom: cumulative PnL.
    """
    from plotly.subplots import make_subplots
    from round5.archetypes import simulate_template_a

    if px.empty:
        return go.Figure()
    sim = simulate_template_a(
        px, tr,
        min_edge_ticks=int(params.get("min_edge_ticks", 3)),
        k_vol=float(params.get("k_vol", 2.0)),
        gamma=float(params.get("gamma", 1e-3)),
    )
    n = len(sim.get("pnl_series", [])) if "pnl_series" in sim else 0
    if n == 0:
        fig = go.Figure()
        fig.add_annotation(text="No simulation data (sim returned 0 ticks)",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3],
        subplot_titles=(
            f"Mid + bid/ask quotes (sample window) — fills={sim.get('n_fills', 0)}",
            f"Inventory  (max |inv| = {sim.get('max_inventory_abs', 0)})",
            f"Cumulative PnL — total {sim.get('pnl_total', 0):+.1f}",
        ),
    )
    start = max(0, n // 2 - sample_window // 2)
    end = min(n, start + sample_window)
    mids = px["mid"].to_numpy()[:n]
    x_window = np.arange(start, end)
    bid_arr = np.array(sim["bid_series"])[start:end]
    ask_arr = np.array(sim["ask_series"])[start:end]

    fig.add_trace(go.Scattergl(x=x_window, y=mids[start:end], mode="lines",
                                name="mid", line=dict(color="black", width=1.0)), row=1, col=1)
    fig.add_trace(go.Scattergl(x=x_window, y=bid_arr, mode="lines",
                                name="bid quote", line=dict(color="steelblue", width=0.8)), row=1, col=1)
    fig.add_trace(go.Scattergl(x=x_window, y=ask_arr, mode="lines",
                                name="ask quote", line=dict(color="firebrick", width=0.8)), row=1, col=1)

    fig.add_trace(go.Scattergl(x=np.arange(n), y=sim["inv_series"], mode="lines",
                                name="inventory", line=dict(color="seagreen", width=0.8),
                                showlegend=False), row=2, col=1)
    fig.add_hline(y=0, line_color="black", line_width=0.5, row=2, col=1)
    fig.add_hline(y=10, line_color="red", line_dash="dash", line_width=0.5, row=2, col=1)
    fig.add_hline(y=-10, line_color="red", line_dash="dash", line_width=0.5, row=2, col=1)

    fig.add_trace(go.Scattergl(x=np.arange(n), y=sim["pnl_series"], mode="lines",
                                name="cum PnL", line=dict(color="purple", width=0.8),
                                showlegend=False), row=3, col=1)
    fig.add_hline(y=0, line_color="black", line_width=0.5, row=3, col=1)

    fig.update_xaxes(title_text="tick (sample window)", row=1, col=1)
    fig.update_xaxes(title_text="tick", row=2, col=1)
    fig.update_xaxes(title_text="tick", row=3, col=1)
    fig.update_yaxes(title_text="price", row=1, col=1)
    fig.update_yaxes(title_text="inv", row=2, col=1)
    fig.update_yaxes(title_text="PnL", row=3, col=1)
    fig.update_layout(height=720, margin=dict(t=50, b=30, l=10, r=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1))
    return fig


def plot_corr_heatmap(matrix: pd.DataFrame, title: str, zmin: float = -1.0, zmax: float = 1.0) -> go.Figure:
    """Interactive heatmap for a square correlation/lead-lag matrix."""
    if matrix.empty:
        return go.Figure()
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=matrix.columns.tolist(), y=matrix.index.tolist(),
        colorscale="RdBu_r", zmin=zmin, zmax=zmax,
        text=[[f"{v:+.2f}" for v in row] for row in matrix.values],
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x} = %{z:+.3f}<extra></extra>",
    ))
    fig.update_layout(title=title, height=480, margin=dict(t=50, b=20, l=10, r=10),
                      xaxis_tickangle=-30)
    return fig


def plot_family_ic_heatmap(ic_long_fam: pd.DataFrame, horizons: tuple) -> go.Figure:
    """Family-wide IC heatmap: rows = (product | signal), cols = horizons.
    Replaces family_signal_ic_heatmap.png.
    """
    if ic_long_fam.empty:
        return go.Figure()
    rows = []
    for _, r in ic_long_fam.iterrows():
        for h in horizons:
            ic = r.get(f"ic_h{h}")
            if pd.notna(ic):
                rows.append({"label": f"{r['product']} | {r['signal']}",
                             "horizon": f"h={h}", "ic": float(ic)})
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    pivot = df.pivot(index="label", columns="horizon", values="ic").reindex(
        columns=[f"h={h}" for h in horizons]
    )
    zmax = max(0.05, float(pivot.abs().to_numpy().max(initial=0.05)))
    text = [[f"{v:+.3f}" if pd.notna(v) else "" for v in row] for row in pivot.values]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="RdBu_r", zmin=-zmax, zmax=zmax,
        text=text, texttemplate="%{text}",
        hovertemplate="%{y}<br>%{x}<br>IC=%{z:+.3f}<extra></extra>",
    ))
    fig.update_layout(height=max(400, 18 * len(pivot)), margin=dict(t=20, b=20, l=10, r=10),
                      yaxis=dict(autorange="reversed"))
    return fig


def plot_family_summary(stats_fam: pd.DataFrame) -> go.Figure:
    """Family-wide structural-stat scatter — 4 panels (replaces family_summary.png)."""
    from plotly.subplots import make_subplots
    if stats_fam.empty:
        return go.Figure()
    fig = make_subplots(rows=2, cols=2, subplot_titles=(
        "VR(k=5) vs Hurst", "ACF(lag1) vs Hurst",
        "Spread/std vs Limit10 saturation", "VWAP Hurst vs mid Hurst",
    ))
    sub = stats_fam.copy()
    sub["spread_std"] = sub["spread_median"] / sub["ret1_std"].replace(0, np.nan)
    short = sub["product"].str.split("_").str[-1]

    fig.add_trace(go.Scatter(x=sub["vr_k5"], y=sub["hurst"], mode="markers+text",
                              text=short, textposition="top center",
                              marker=dict(size=10, color="steelblue"),
                              hovertemplate="%{text}<br>vr_k5=%{x:.3f}<br>hurst=%{y:.3f}<extra></extra>",
                              showlegend=False), row=1, col=1)
    fig.add_vline(x=1.0, line_color="grey", line_dash="dash", row=1, col=1)
    fig.add_hline(y=0.5, line_color="grey", line_dash="dash", row=1, col=1)

    fig.add_trace(go.Scatter(x=sub["acf_ret1_lag1"], y=sub["hurst"], mode="markers+text",
                              text=short, textposition="top center",
                              marker=dict(size=10, color="firebrick"),
                              hovertemplate="%{text}<br>acf=%{x:+.3f}<br>hurst=%{y:.3f}<extra></extra>",
                              showlegend=False), row=1, col=2)
    fig.add_vline(x=0.0, line_color="grey", line_dash="dash", row=1, col=2)
    fig.add_hline(y=0.5, line_color="grey", line_dash="dash", row=1, col=2)

    fig.add_trace(go.Scatter(x=sub["limit10_saturation"], y=sub["spread_std"], mode="markers+text",
                              text=short, textposition="top center",
                              marker=dict(size=10, color="seagreen"),
                              hovertemplate="%{text}<br>lim10_sat=%{x:.2f}<br>spread/std=%{y:.2f}<extra></extra>",
                              showlegend=False), row=2, col=1)
    fig.add_hline(y=1.0, line_color="grey", line_dash="dash", row=2, col=1)
    fig.add_vline(x=0.3, line_color="grey", line_dash="dash", row=2, col=1)

    if "vwap_hurst" in sub.columns:
        fig.add_trace(go.Scatter(x=sub["hurst"], y=sub["vwap_hurst"], mode="markers+text",
                                  text=short, textposition="top center",
                                  marker=dict(size=10, color="purple"),
                                  hovertemplate="%{text}<br>mid_hurst=%{x:.3f}<br>vwap_hurst=%{y:.3f}<extra></extra>",
                                  showlegend=False), row=2, col=2)
        fig.add_shape(type="line", x0=0.4, y0=0.4, x1=0.6, y1=0.6,
                      line=dict(color="grey", dash="dash"), row=2, col=2)

    fig.update_xaxes(title="vr_k5", row=1, col=1); fig.update_yaxes(title="hurst", row=1, col=1)
    fig.update_xaxes(title="acf_lag1", row=1, col=2); fig.update_yaxes(title="hurst", row=1, col=2)
    fig.update_xaxes(title="lim10_sat", row=2, col=1); fig.update_yaxes(title="spread_med/std", row=2, col=1)
    fig.update_xaxes(title="mid hurst", row=2, col=2); fig.update_yaxes(title="vwap hurst", row=2, col=2)
    fig.update_layout(height=720, margin=dict(t=50, b=30, l=10, r=10), showlegend=False)
    return fig


def plot_family_vol_compare(family_pxs: dict[str, pd.DataFrame]) -> go.Figure:
    """Overlaid rv_50 distributions across the 5 family members.
    Replaces family_vol_compare.png.
    """
    fig = go.Figure()
    any_data = False
    for product, px in family_pxs.items():
        if px.empty or "std_50" not in px.columns:
            continue
        rv = px["std_50"].dropna()
        if rv.empty:
            continue
        any_data = True
        short = product.split("_", 1)[-1] if "_" in product else product
        fig.add_trace(go.Histogram(x=rv, name=short, opacity=0.45, nbinsx=60,
                                    histnorm="probability density"))
    if not any_data:
        return go.Figure()
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10), barmode="overlay",
                      xaxis_title="std_50 (rolling 50-tick std)", yaxis_title="density")
    return fig


def plot_family_basis_residuals(family_pxs: dict[str, pd.DataFrame]) -> go.Figure:
    """Each family member's mid minus the family-mean mid.
    Replaces family_basis_residuals.png.
    """
    if not family_pxs:
        return go.Figure()
    panel = {}
    min_len = None
    for p, px in family_pxs.items():
        if px.empty:
            continue
        s = px["mid"].reset_index(drop=True)
        panel[p] = s
        min_len = len(s) if min_len is None else min(min_len, len(s))
    if not panel:
        return go.Figure()
    df = pd.DataFrame({k: v.iloc[:min_len] for k, v in panel.items()})
    ref = df.mean(axis=1)
    fig = go.Figure()
    for p in df.columns:
        short = p.split("_", 1)[-1] if "_" in p else p
        fig.add_trace(go.Scattergl(x=df.index, y=df[p] - ref, mode="lines",
                                    name=short, line=dict(width=0.7),
                                    hovertemplate="tick=%{x}<br>residual=%{y:+.3f}<extra>" + short + "</extra>"))
    fig.add_hline(y=0, line_color="black", line_width=0.5)
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                      xaxis_title="tick", yaxis_title="mid − family-mean mid",
                      title="Basis residuals (each product vs family mean)")
    return fig


def plot_calibration_distribution(panel: pd.DataFrame, stat_col: str, threshold: float,
                                    direction: str, gate_name: str) -> go.Figure:
    """Histogram of the gate's underlying stat with the threshold line.
    Replaces CALIBRATION/figures/{gate}.png.
    """
    if panel.empty or stat_col not in panel.columns:
        return go.Figure()
    s = panel[stat_col].dropna()
    if s.empty:
        return go.Figure()
    if direction in ("ge", "gt"):
        n_pass = (s >= threshold).sum() if direction == "ge" else (s > threshold).sum()
    else:
        n_pass = (s <= threshold).sum() if direction == "le" else (s < threshold).sum()
    fig = go.Figure(go.Histogram(x=s, nbinsx=20, marker_color="steelblue", opacity=0.85))
    fig.add_vline(x=threshold, line_color="red", line_dash="dash", line_width=2,
                  annotation_text=f"thresh={threshold} ({direction})", annotation_position="top")
    fig.update_layout(height=320, margin=dict(t=40, b=30, l=10, r=10),
                      title=f"{gate_name}: {n_pass}/{len(s)} pass",
                      xaxis_title=stat_col, yaxis_title="count")
    return fig


def plot_cluster_aggregate(agg: pd.DataFrame) -> go.Figure:
    """Per-cluster mean-of-products series."""
    if agg.empty:
        return go.Figure()
    fig = go.Figure()
    if "cluster_id" in agg.columns and "value" in agg.columns:
        for cid, sub in agg.groupby("cluster_id"):
            fig.add_trace(go.Scattergl(x=sub.index, y=sub["value"], mode="lines", name=f"cluster {cid}"))
    else:
        for col in agg.columns:
            if col in ("timestamp", "tick", "ts"):
                continue
            fig.add_trace(go.Scattergl(x=agg.index, y=agg[col], mode="lines", name=str(col)))
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                      xaxis_title="tick", yaxis_title="cluster aggregate (mean of products)")
    return fig


def plot_cluster_rolling_rank(perf: pd.DataFrame) -> go.Figure:
    """Per-cluster rolling cumulative-return rank over time."""
    if perf.empty:
        return go.Figure()
    fig = go.Figure()
    if "cluster_id" in perf.columns and "rank" in perf.columns:
        for cid, sub in perf.groupby("cluster_id"):
            fig.add_trace(go.Scattergl(x=sub.index, y=sub["rank"], mode="lines", name=f"cluster {cid}"))
    elif "family" in perf.columns and "rank" in perf.columns:
        for fam, sub in perf.groupby("family"):
            fig.add_trace(go.Scattergl(x=sub.index, y=sub["rank"], mode="lines", name=fam))
    else:
        for col in perf.columns:
            fig.add_trace(go.Scattergl(x=perf.index, y=perf[col], mode="lines", name=str(col)))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=380, margin=dict(t=20, b=30, l=10, r=10),
                      xaxis_title="tick", yaxis_title="cross-sectional rank (1 = best)")
    return fig


def plot_leadlag_pairs_bar(pairs: pd.DataFrame, top_k: int = 20) -> go.Figure:
    """Top-K stable lead-lag pairs as a horizontal bar chart."""
    if pairs.empty:
        return go.Figure()
    df = pairs.copy()
    if "abs_corr" not in df.columns and "corr" in df.columns:
        df["abs_corr"] = df["corr"].abs()
    if "abs_corr" in df.columns:
        df = df.sort_values("abs_corr", ascending=False).head(top_k)
    df = df[::-1]
    label_col = None
    for cand in ("pair", "label"):
        if cand in df.columns:
            label_col = cand; break
    if label_col is None and {"leader", "follower"}.issubset(df.columns):
        df["label"] = df["leader"] + " → " + df["follower"]
        label_col = "label"
    if label_col is None:
        df["label"] = df.iloc[:, 0].astype(str)
        label_col = "label"
    corr_col = "corr" if "corr" in df.columns else df.select_dtypes("number").columns[0]
    df["color"] = df[corr_col].apply(lambda v: "#2ca02c" if v > 0 else "#d62728")
    fig = go.Figure(go.Bar(
        y=df[label_col], x=df[corr_col], orientation="h",
        marker_color=df["color"],
        text=[f"{v:+.3f}" for v in df[corr_col]], textposition="outside",
    ))
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_layout(height=max(280, 28 * len(df) + 80),
                      margin=dict(t=20, b=30, l=10, r=10),
                      xaxis_title="lead-lag correlation",
                      title=f"Top {len(df)} stable cross-cluster lead-lag pairs (by |corr|)")
    return fig


def plot_leadlag_full_heatmap(ll_full: pd.DataFrame, lag: int = 1) -> go.Figure:
    """Heatmap of leader×follower correlations at a single lag (replaces leadlag_heatmap.png)."""
    if ll_full.empty:
        return go.Figure()
    sub = ll_full[ll_full.get("lag", lag) == lag] if "lag" in ll_full.columns else ll_full
    if sub.empty or not {"leader", "follower", "corr"}.issubset(sub.columns):
        return go.Figure()
    pivot = sub.pivot(index="leader", columns="follower", values="corr")
    zmax = max(0.05, float(pivot.abs().to_numpy().max(initial=0.05)))
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="RdBu_r", zmin=-zmax, zmax=zmax,
        text=[[f"{v:+.3f}" if pd.notna(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        hovertemplate="leader=%{y}<br>follower=%{x}<br>corr=%{z:+.3f}<extra></extra>",
    ))
    fig.update_layout(height=480, margin=dict(t=40, b=20, l=10, r=10),
                      xaxis_tickangle=-30,
                      title=f"Cross-cluster lead-lag correlation @ lag={lag}")
    return fig


def plot_spike_panel(product: str, px: pd.DataFrame, tr: pd.DataFrame,
                     events: pd.DataFrame) -> go.Figure:
    """Per-product spike-panel (replaces {product}_spike_panel.png).

    Top: mid + bid/ask with red dashed lines at spike timestamps.
    Bottom: |ret_1| with horizontal threshold line at the spike-trigger z value.
    """
    from plotly.subplots import make_subplots
    if px.empty:
        return go.Figure()
    sub_events = events[events["product"] == product] if "product" in events.columns else events.iloc[0:0]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.10,
        row_heights=[0.6, 0.4],
        subplot_titles=(
            f"{product} — mid + bid/ask  (red dashed = spike events)",
            "|ret_1|  (vol-spike triggers)",
        ),
    )
    x = np.arange(len(px))
    fig.add_trace(go.Scattergl(x=x, y=px["mid"], mode="lines", name="mid",
                                line=dict(color="black", width=1.0)), row=1, col=1)
    fig.add_trace(go.Scattergl(x=x, y=px["bid_price_1"], mode="lines", name="bid₁",
                                line=dict(color="steelblue", width=0.6), opacity=0.7), row=1, col=1)
    fig.add_trace(go.Scattergl(x=x, y=px["ask_price_1"], mode="lines", name="ask₁",
                                line=dict(color="firebrick", width=0.6), opacity=0.7), row=1, col=1)

    abs_ret = px["ret_1"].abs() if "ret_1" in px.columns else pd.Series(np.nan, index=px.index)
    fig.add_trace(go.Scattergl(x=x, y=abs_ret, mode="lines", name="|ret_1|",
                                line=dict(color="purple", width=0.6), showlegend=False), row=2, col=1)

    if not sub_events.empty:
        # Map (day, ts) events back to concatenated tick index
        for _, ev in sub_events.iterrows():
            d = ev.get("day"); ts = ev.get("ts")
            mask = (px["day"] == d) & (px["timestamp"] == ts)
            if mask.any():
                idx = int(px.index[mask][0])
                fig.add_vline(x=idx, line_color="red", line_dash="dash", line_width=0.7,
                              opacity=0.4, row=1, col=1)
                fig.add_vline(x=idx, line_color="red", line_dash="dash", line_width=0.7,
                              opacity=0.4, row=2, col=1)

    fig.update_xaxes(title="tick", row=2, col=1)
    fig.update_yaxes(title="price", row=1, col=1)
    fig.update_yaxes(title="|ret_1|", row=2, col=1)
    fig.update_layout(height=600, margin=dict(t=50, b=30, l=10, r=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1))
    return fig


def plot_ic_topk(ic_p: pd.DataFrame, horizons: tuple, k: int = 10) -> go.Figure:
    """Top-K (signal, horizon) cells by |IC|, coloured by sign + FDR-pass."""
    if ic_p.empty:
        return go.Figure()
    rows = []
    for _, r in ic_p.iterrows():
        for h in horizons:
            ic = r.get(f"ic_h{h}")
            p = r.get(f"p_h{h}")
            sig_pass = bool(r.get("significant", False)) and pd.notna(p) and p < 0.05
            if pd.notna(ic):
                rows.append({"label": f"{r['signal']} @ h={h}",
                             "ic": float(ic),
                             "abs_ic": abs(float(ic)),
                             "p": float(p) if pd.notna(p) else None,
                             "fdr_pass": sig_pass})
    df = pd.DataFrame(rows).sort_values("abs_ic", ascending=False).head(k)
    if df.empty:
        return go.Figure()
    df = df[::-1]  # so largest is at top
    df["color"] = df.apply(
        lambda r: ("#2ca02c" if r["ic"] > 0 else "#d62728") if r["fdr_pass"]
        else ("#9ad29a" if r["ic"] > 0 else "#e6a3a3"), axis=1)
    fig = go.Figure(go.Bar(
        y=df["label"], x=df["ic"], orientation="h",
        marker_color=df["color"],
        text=[f"{v:+.3f}{' ✓' if fp else ''}" for v, fp in zip(df["ic"], df["fdr_pass"])],
        textposition="outside",
        hovertemplate="%{y}<br>IC=%{x:+.4f}<br>p=%{customdata[0]:.3g}<br>FDR-pass=%{customdata[1]}<extra></extra>",
        customdata=df[["p", "fdr_pass"]].values,
    ))
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_layout(height=max(280, 30 * len(df) + 80),
                       margin=dict(t=20, b=30, l=10, r=10),
                       title=f"Top-{k} predictive cells by |IC|. ✓ = HAC+FDR-significant.",
                       xaxis_title="HAC IC (signed)")
    return fig


# ---------------------------------------------------------------------------
# Reusable UI components
# ---------------------------------------------------------------------------

CONFIDENCE_COLORS = {"high": "#2ca02c", "medium": "#ff7f0e", "low": "#d62728", "n/a": "#7f7f7f"}
ARCHETYPE_COLORS = {
    "MR_TAKER": "#1f77b4",
    "MOMENTUM": "#ff7f0e",
    "RANDOM_WALK": "#9467bd",
    "NO_EDGE": "#7f7f7f",
}


def archetype_badge(arch: str) -> str:
    color = ARCHETYPE_COLORS.get(arch, "#444")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">{arch}</span>'


def confidence_badge(conf: str) -> str:
    color = CONFIDENCE_COLORS.get(conf, "#7f7f7f")
    return f'<span style="background:{color};color:white;padding:2px 6px;border-radius:4px;font-size:0.8em;">{conf}</span>'


def flag_badges(row: pd.Series) -> str:
    out = []
    if row.get("is_pair"):
        stat = "stat" if row.get("pair_residual_stationary") else "non-stat"
        out.append(f'<span style="background:#17becf;color:white;padding:2px 6px;border-radius:4px;font-size:0.75em;">PAIR ({stat})</span>')
    if row.get("is_obi"):
        d = row.get("obi_direction") or "?"
        out.append(f'<span style="background:#bcbd22;color:white;padding:2px 6px;border-radius:4px;font-size:0.75em;">OBI {d}</span>')
    if row.get("is_mm"):
        pnl = row.get("mm_pnl")
        status = "✓" if pd.notna(pnl) and pnl > 0 else "?"
        out.append(f'<span style="background:#8c564b;color:white;padding:2px 6px;border-radius:4px;font-size:0.75em;">MM {status}</span>')
    return " ".join(out)


# ---------------------------------------------------------------------------
# View 1: Universe Overview
# ---------------------------------------------------------------------------

def view_universe(arch: pd.DataFrame, stats: pd.DataFrame):
    st.header("Universe Overview")

    # Top row: headline metrics
    n_total = len(arch)
    n_mr = (arch["archetype"] == "MR_TAKER").sum()
    n_no = (arch["archetype"] == "NO_EDGE").sum()
    n_pair = int(arch["is_pair"].sum())
    n_obi = int(arch["is_obi"].sum())
    n_mm = int(arch["is_mm"].sum())
    n_actionable = ((arch["archetype"] != "NO_EDGE") | arch["is_pair"] | arch["is_obi"] | arch["is_mm"]).sum()

    cols = st.columns(7)
    cols[0].metric("Products", n_total)
    cols[1].metric("MR_TAKER", n_mr)
    cols[2].metric("NO_EDGE", n_no)
    cols[3].metric("PAIR flags", n_pair)
    cols[4].metric("OBI flags", n_obi)
    cols[5].metric("MM flags", n_mm)
    cols[6].metric("Actionable", f"{n_actionable}/{n_total}")

    # Distribution charts
    st.subheader("Distribution")
    c1, c2 = st.columns(2)

    with c1:
        # Archetype × confidence stacked bar
        if "mr_confidence" in arch.columns:
            chart_df = (arch.assign(conf=arch["mr_confidence"].fillna("n/a"))
                            .groupby(["archetype", "conf"]).size().reset_index(name="n"))
            fig = px.bar(chart_df, x="archetype", y="n", color="conf",
                         color_discrete_map=CONFIDENCE_COLORS,
                         category_orders={"conf": ["high", "medium", "low", "n/a"]},
                         title="Primary archetype × MR confidence")
            fig.update_layout(height=350, margin=dict(t=40, b=20, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Per-family flag counts
        flag_df = arch.groupby("family").agg(
            MR=("archetype", lambda x: (x == "MR_TAKER").sum()),
            NO_EDGE=("archetype", lambda x: (x == "NO_EDGE").sum()),
            PAIR=("is_pair", "sum"),
            OBI=("is_obi", "sum"),
            MM=("is_mm", "sum"),
        ).reset_index()
        long = flag_df.melt(id_vars="family", var_name="bucket", value_name="n")
        fig = px.bar(long, x="family", y="n", color="bucket", barmode="group",
                     title="Per-family bucket counts")
        fig.update_layout(height=350, margin=dict(t=40, b=20, l=10, r=10))
        fig.update_xaxes(tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # Filterable table
    st.subheader("Per-product table")
    with st.expander("Filters", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        sel_archs = f1.multiselect("Archetype", sorted(arch["archetype"].unique()),
                                   default=sorted(arch["archetype"].unique()))
        sel_fams = f2.multiselect("Family", sorted(arch["family"].unique()),
                                  default=sorted(arch["family"].unique()))
        sel_confs = f3.multiselect("MR confidence", ["high", "medium", "low", "n/a"],
                                   default=["high", "medium", "low", "n/a"])
        flag_filter = f4.multiselect("Must have flag",
                                     ["PAIR_ANCHOR", "OBI_TAKER", "MM_CANDIDATE", "mr_ic_verified"])

    mask = (
        arch["archetype"].isin(sel_archs)
        & arch["family"].isin(sel_fams)
        & arch.get("mr_confidence", pd.Series("n/a", index=arch.index)).fillna("n/a").isin(sel_confs)
    )
    if "PAIR_ANCHOR" in flag_filter: mask &= arch["is_pair"]
    if "OBI_TAKER" in flag_filter: mask &= arch["is_obi"]
    if "MM_CANDIDATE" in flag_filter: mask &= arch["is_mm"]
    if "mr_ic_verified" in flag_filter and "mr_ic_verified" in arch.columns:
        mask &= arch["mr_ic_verified"]

    show_cols = [
        "family", "product", "archetype", "mr_confidence",
        "mr_n_triggers", "mr_ic_verified",
        "is_pair", "pair_partner", "pair_residual_stationary",
        "is_obi", "obi_direction", "obi_ic",
        "is_mm", "mm_pnl",
    ]
    show_cols = [c for c in show_cols if c in arch.columns]
    st.dataframe(arch[mask][show_cols].sort_values(["family", "product"]),
                 use_container_width=True, height=520, hide_index=True)

    # Stats scatter
    st.subheader("Stats explorer")
    if not stats.empty:
        merged = arch[["product", "family", "archetype", "mr_confidence"]].merge(stats, on=["product", "family"])
        numeric_cols = [c for c in merged.columns
                        if merged[c].dtype in (np.float64, np.float32, np.int64) and c not in ("n_ticks", "n_days")]
        c1, c2, c3 = st.columns(3)
        x_var = c1.selectbox("X axis", numeric_cols, index=numeric_cols.index("vr_k5") if "vr_k5" in numeric_cols else 0)
        y_var = c2.selectbox("Y axis", numeric_cols, index=numeric_cols.index("hurst") if "hurst" in numeric_cols else 0)
        color_by = c3.selectbox("Colour by", ["archetype", "mr_confidence", "family"], index=0)
        fig = px.scatter(merged, x=x_var, y=y_var, color=color_by,
                         hover_name="product", hover_data=["family", "archetype", "mr_confidence"],
                         color_discrete_map=ARCHETYPE_COLORS if color_by == "archetype"
                         else (CONFIDENCE_COLORS if color_by == "mr_confidence" else None),
                         height=500)
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# View 2: Family Drilldown
# ---------------------------------------------------------------------------

def view_family(arch: pd.DataFrame, stats: pd.DataFrame, micro: pd.DataFrame, vol: pd.DataFrame):
    st.header("Family Drilldown")

    fam = st.selectbox("Family", list(FAMILIES.keys()), index=0)
    sub_arch = arch[arch["family"] == fam].copy()
    sub_stats = stats[stats["family"] == fam] if not stats.empty else pd.DataFrame()

    # Per-product summary table
    st.subheader(f"{fam} — products")
    cols_show = [
        "product", "archetype", "mr_confidence", "mr_n_triggers", "mr_ic_verified", "mr_contradictions",
        "is_pair", "pair_partner", "pair_corr", "pair_coint_p", "pair_residual_stationary",
        "is_obi", "obi_direction", "obi_ic",
        "is_mm", "mm_pnl", "mm_fills",
    ]
    cols_show = [c for c in cols_show if c in sub_arch.columns]
    st.dataframe(sub_arch[cols_show], use_container_width=True, hide_index=True)

    # Within-family matrices
    st.subheader("Within-family relationships")
    tab_corr, tab_ret, tab_lead, tab_coint = st.tabs(
        ["corr_mid", "corr_returns", "lead_lag (10t)", "cointegration"]
    )
    with tab_corr:
        m = load_family_matrix(fam, "corr_mid")
        if not m.empty:
            fig = px.imshow(m, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                            aspect="auto", text_auto=".2f", title="corr_mid")
            fig.update_layout(height=480)
            st.plotly_chart(fig, use_container_width=True)
    with tab_ret:
        m = load_family_matrix(fam, "corr_returns")
        if not m.empty:
            fig = px.imshow(m, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                            aspect="auto", text_auto=".2f", title="corr_returns")
            fig.update_layout(height=480)
            st.plotly_chart(fig, use_container_width=True)
    with tab_lead:
        m = load_family_matrix(fam, "lead_lag")
        if not m.empty:
            zmax = max(0.05, m.abs().max().max())
            fig = px.imshow(m, color_continuous_scale="RdBu_r", zmin=-zmax, zmax=zmax,
                            aspect="auto", text_auto=".3f",
                            title="lead_lag (lag=10): row leads col when positive")
            fig.update_layout(height=480)
            st.plotly_chart(fig, use_container_width=True)
    with tab_coint:
        c = load_cointegration(fam)
        if not c.empty:
            c["significant"] = c["coint_p"] < 0.05
            st.dataframe(c.sort_values("coint_p"), use_container_width=True, hide_index=True)

    # Family-level interactive figures
    st.subheader("Family-level interactive figures")
    fam_stats = stats[stats["family"] == fam] if not stats.empty else pd.DataFrame()
    fam_ic = load_ic_long()
    fam_ic = fam_ic[fam_ic["family"] == fam] if not fam_ic.empty else pd.DataFrame()

    f_tabs = st.tabs(["Family summary (4 scatters)",
                       "IC heatmap (all products)",
                       "Basis residuals",
                       "Vol distributions overlaid"])
    with f_tabs[0]:
        if not fam_stats.empty:
            st.plotly_chart(plot_family_summary(fam_stats), use_container_width=True)
            st.caption("Each dot = one family member. Dashed lines mark random-walk midpoints "
                       "(vr=1, hurst=0.5, acf=0) and the MM-cushion gate (spread/std=1, lim10=0.3). "
                       "Bottom-right scatter = mid_hurst vs vwap_hurst — points below the diagonal "
                       "are products where VWAP mean-reverts more than mid.")
    with f_tabs[1]:
        if not fam_ic.empty:
            st.plotly_chart(plot_family_ic_heatmap(fam_ic, HORIZONS), use_container_width=True)
            st.caption("HAC IC across (product × signal) rows × horizons.")
    with f_tabs[2]:
        with st.spinner("Loading family raw data ..."):
            family_pxs = {p: load_product_px_tr(p)[0] for p in FAMILIES[fam]}
        st.plotly_chart(plot_family_basis_residuals(family_pxs), use_container_width=True)
        st.caption("Each line = (product mid) − (family-mean mid). When a basis residual itself "
                   "looks stationary, the spread is tradeable as a stationary mean-reverter.")
    with f_tabs[3]:
        with st.spinner("Loading family raw data ..."):
            family_pxs = {p: load_product_px_tr(p)[0] for p in FAMILIES[fam]}
        st.plotly_chart(plot_family_vol_compare(family_pxs), use_container_width=True)
        st.caption("Density-normalised. Click legend names to toggle.")


# ---------------------------------------------------------------------------
# View 3: Product Detail
# ---------------------------------------------------------------------------

def view_product(arch: pd.DataFrame, stats: pd.DataFrame, ic_long: pd.DataFrame,
                 vol: pd.DataFrame, dq: pd.DataFrame):
    st.header("Product Detail")

    fam = st.selectbox("Family", list(FAMILIES.keys()), index=0)
    products = FAMILIES[fam]
    product = st.selectbox("Product", products, index=0)

    arch_row = arch[arch["product"] == product]
    if arch_row.empty:
        st.warning("No archetype data for this product.")
        return
    r = arch_row.iloc[0]
    stats_row = stats[stats["product"] == product].iloc[0] if not stats.empty else None

    # Header card
    badges = (
        archetype_badge(r["archetype"])
        + " &nbsp; "
        + confidence_badge(r.get("mr_confidence", "n/a"))
        + " &nbsp; "
        + flag_badges(r)
    )
    st.markdown(f"### {product} &nbsp; {badges}", unsafe_allow_html=True)

    # Summary metrics
    if stats_row is not None:
        cols = st.columns(8)
        cols[0].metric("vr_k5", f"{stats_row.get('vr_k5', float('nan')):.3f}")
        cols[1].metric("hurst", f"{stats_row.get('hurst', float('nan')):.3f}")
        cols[2].metric("acf_lag1", f"{stats_row.get('acf_ret1_lag1', float('nan')):+.3f}")
        cols[3].metric("adf_p_mid", f"{stats_row.get('adf_p_mid', float('nan')):.3f}")
        cols[4].metric("vwap_hurst", f"{stats_row.get('vwap_hurst', float('nan')):.3f}")
        cols[5].metric("vwap_adf_p", f"{stats_row.get('vwap_adf_p', float('nan')):.3f}")
        cols[6].metric("spread_med/std", f"{stats_row.get('spread_median', 0)/(stats_row.get('ret1_std', 1) or 1):.2f}")
        cols[7].metric("lim10_sat", f"{stats_row.get('limit10_saturation', float('nan')):.2f}")

    # Rationale
    with st.expander("Classifier rationale", expanded=True):
        st.text(r.get("rationale", ""))
        if r.get("mr_contradictions"):
            st.warning(f"**Contradictions detected:** {r['mr_contradictions']}")
        if r.get("mr_n_triggers", 0) > 0:
            st.caption(f"Triggers fired: {r.get('mr_triggers', '')}  ({int(r.get('mr_n_triggers', 0))})")

    # IC scorecard — bar chart (more readable than heatmap)
    st.subheader("IC scorecard (HAC + BH-FDR)")
    ic_p = ic_long[ic_long["product"] == product] if not ic_long.empty else pd.DataFrame()
    if not ic_p.empty:
        st.plotly_chart(plot_ic_bars(ic_p, HORIZONS), use_container_width=True)
        st.caption("Solid bars = HAC + BH-FDR-significant at α=0.05. Faded = not significant. Hover for HAC t/p.")
        with st.expander("IC values + HAC t/p", expanded=False):
            ic_show_cols = ["signal"] + [c for c in ic_p.columns if c.startswith(("ic_h", "t_h", "p_h", "n_h"))]
            ic_show_cols += ["significant"] if "significant" in ic_p.columns else []
            st.dataframe(ic_p[ic_show_cols], use_container_width=True, hide_index=True)

    # Per-product interactive figures
    st.subheader("Interactive figures")
    with st.spinner(f"Loading raw data for {product} ..."):
        px_p, tr_p = load_product_px_tr(product)
    if px_p.empty:
        st.warning("Could not load raw data for this product.")
    else:
        st.caption(f"Loaded {len(px_p):,} ticks across {px_p['day'].nunique()} day(s) "
                   f"and {len(tr_p):,} trades. Hover for values, drag to zoom, "
                   f"click legend to toggle traces.")
        p_tabs = st.tabs(["Price", "Returns", "ACF", "Spread", "Depth",
                            "OBI vs fwd_ret", "Signed flow", "Volatility"])
        with p_tabs[0]:
            st.plotly_chart(plot_price_series(px_p, tr_p, sample_step=1), use_container_width=True)
        with p_tabs[1]:
            st.plotly_chart(plot_returns_hist(px_p), use_container_width=True)
        with p_tabs[2]:
            st.plotly_chart(plot_acf(px_p, max_lag=100), use_container_width=True)
        with p_tabs[3]:
            st.plotly_chart(plot_spread_hist(px_p), use_container_width=True)
        with p_tabs[4]:
            st.plotly_chart(plot_depth_profile(px_p), use_container_width=True)
        with p_tabs[5]:
            st.plotly_chart(plot_obi_vs_fwd_ret(px_p, horizon=10), use_container_width=True)
        with p_tabs[6]:
            st.plotly_chart(plot_signed_flow(px_p, tr_p), use_container_width=True)
        with p_tabs[7]:
            st.plotly_chart(plot_vol_over_time(px_p), use_container_width=True)

    # Data quality
    if not dq.empty:
        dq_row = dq[dq["product"] == product]
        if not dq_row.empty:
            with st.expander("Data quality", expanded=False):
                st.dataframe(dq_row.T, use_container_width=True)


# ---------------------------------------------------------------------------
# View 4: Product Deep Dive — exhaustive single-product report
# ---------------------------------------------------------------------------

def _trigger_table(stats_row: pd.Series, gates) -> pd.DataFrame:
    """Per-gate evaluation: which structural triggers fired, with margins."""
    rows = [
        ("MR vr_lt",        "vr_k5",          "<", gates.mr_vr_max),
        ("MR acf1_neg",     "acf_ret1_lag1",  "<", gates.mr_acf1_max),
        ("MR hurst_lt",     "hurst",          "<", gates.mr_hurst_max),
        ("MR adf_mid_stat", "adf_p_mid",      "<", gates.mr_adf_max),
        ("MR vwap_hurst",   "vwap_hurst",     "<", gates.mr_vwap_hurst_max),
        ("MR vwap_adf",     "vwap_adf_p",     "<", gates.mr_vwap_adf_max),
        ("MR vwap_acf1",    "vwap_acf_lag1",  "<", gates.mr_vwap_acf1_max),
        ("MOM vr_gt",       "vr_k5",          ">", gates.mom_vr_min),
        ("MOM hurst_gt",    "hurst",          ">", gates.mom_hurst_min),
        ("MM |vr-1|",       "vr_k5",          "near1", gates.rw_vr_dev_max),
        ("MM |hurst-0.5|",  "hurst",          "near0.5", gates.rw_hurst_dev_max),
        ("MM |acf|<",       "acf_ret1_lag1",  "near0", gates.rw_acf1_max_abs),
        ("MM lim10>=",      "limit10_saturation", ">=", gates.rw_lim10_sat_min),
        ("CONTRA vr>",      "vr_k5",          ">", gates.mr_contra_vr_min),
        ("CONTRA acf>",     "acf_ret1_lag1",  ">", gates.mr_contra_acf_min),
        ("CONTRA hurst>",   "hurst",          ">", gates.mr_contra_hurst_max),
        ("CONTRA vwap_acf>","vwap_acf_lag1",  ">", gates.mr_contra_vwap_acf_min),
    ]
    out = []
    for label, col, op, thr in rows:
        v = stats_row.get(col, float("nan"))
        if not pd.notna(v):
            out.append({"trigger": label, "stat": col, "value": None,
                        "op": op, "threshold": thr, "fires": None, "margin_to_threshold": None})
            continue
        v = float(v)
        if op == "<":
            fires = v < thr
            margin = thr - v
        elif op == ">":
            fires = v > thr
            margin = v - thr
        elif op == ">=":
            fires = v >= thr
            margin = v - thr
        elif op == "near1":
            fires = abs(v - 1.0) < thr
            margin = thr - abs(v - 1.0)
        elif op == "near0.5":
            fires = abs(v - 0.5) < thr
            margin = thr - abs(v - 0.5)
        elif op == "near0":
            fires = abs(v) < thr
            margin = thr - abs(v)
        else:
            fires = None
            margin = None
        out.append({
            "trigger": label, "stat": col, "value": round(v, 4),
            "op": op, "threshold": thr,
            "fires": fires,
            "margin_to_threshold": round(margin, 4) if margin is not None else None,
        })
    return pd.DataFrame(out)


def _spec_categories(stats_row: pd.Series) -> dict[str, dict[str, float]]:
    """Bucket the per-product stats into thematic groups for display."""
    g = lambda *keys: {k: stats_row.get(k) for k in keys if k in stats_row.index}
    return {
        "Price level": g("mid_mean", "mid_std", "mid_min", "mid_max", "mid_range"),
        "Returns (ret_1)": g("ret1_mean", "ret1_std", "ret1_skew", "ret1_kurt"),
        "Mean-reversion (mid)": g("vr_k2", "vr_k5", "vr_k10", "vr_z_k2", "vr_z_k5", "vr_z_k10",
                                   "acf_ret1_lag1", "acf_ret1_lag5", "acf_ret1_lag20", "acf_ret1_lag100",
                                   "hurst", "hurst_r2", "adf_p_mid"),
        "VWAP analogues": g("vwap_hurst", "vwap_hurst_r2", "vwap_adf_p",
                             "vwap_acf_lag1", "vwap_to_mid_corr"),
        "Microstructure": g("spread_mean", "spread_median", "spread_p95",
                             "depth_l1_mean", "depth_total_mean",
                             "limit10_saturation", "quote_update_freq"),
        "Trade flow": g("n_trades", "trade_freq", "trade_size_mean", "trade_size_max"),
    }


def view_product_deep_dive(arch: pd.DataFrame, stats: pd.DataFrame, ic_long: pd.DataFrame,
                           vol: pd.DataFrame, dq: pd.DataFrame):
    st.header("Product Deep Dive")
    st.caption("Exhaustive single-product report — every pipeline output for this product. "
               "Use this view when investigating a borderline classification or before deploying a strategy.")

    # --- Pickers ---
    fam = st.selectbox("Family", list(FAMILIES.keys()), index=0, key="dd_fam")
    products = FAMILIES[fam]
    product = st.selectbox("Product", products, index=0, key="dd_prod")

    arch_row_df = arch[arch["product"] == product]
    if arch_row_df.empty:
        st.warning("No archetype data for this product.")
        return
    r = arch_row_df.iloc[0]
    stats_row_df = stats[stats["product"] == product]
    if stats_row_df.empty:
        st.warning("No stats data for this product.")
        return
    stats_row = stats_row_df.iloc[0]

    # --- 1. Header card ---
    badges = (
        archetype_badge(r["archetype"])
        + " &nbsp; "
        + confidence_badge(r.get("mr_confidence", "n/a"))
        + " &nbsp; "
        + flag_badges(r)
    )
    st.markdown(f"## {product} &nbsp; {badges}", unsafe_allow_html=True)
    st.markdown(f"**Family**: `{fam}` &nbsp;&nbsp; "
                f"**Triggers fired**: {int(r.get('mr_n_triggers') or 0)}/7 &nbsp;&nbsp; "
                f"**IC verified**: {bool(r.get('mr_ic_verified', False))}")

    # --- 2. Classifier rationale ---
    with st.container(border=True):
        st.markdown("**Classifier rationale**")
        st.code(r.get("rationale", ""), language="text")
        if r.get("mr_contradictions"):
            st.warning(f"⚠️ Contradictions: {r['mr_contradictions']}")

    # --- 3. Trigger evaluation table ---
    st.subheader("Gate evaluation")
    st.caption("Every classifier gate scored against this product, with margin to threshold. "
               "MR triggers (admission), MOM/MM gates (alternative classifications), "
               "CONTRA gates (opposite-sign sister stats that contradict MR).")
    try:
        from round5.archetypes import ArchetypeGates
        gates = ArchetypeGates()
        tt = _trigger_table(stats_row, gates)

        def _color_fires(val):
            if val is True: return "background-color: #d4edda"
            if val is False: return ""
            return "color: #999"
        st.dataframe(tt.style.map(_color_fires, subset=["fires"]),
                     use_container_width=True, hide_index=True, height=560)
    except Exception as e:
        st.error(f"Could not load gates: {e}")

    # --- 4. Statistical battery (full) ---
    st.subheader("Statistical battery")
    st.caption("All per-product stats from `stats_per_product.csv`, grouped thematically.")
    cats = _spec_categories(stats_row)
    cat_tabs = st.tabs(list(cats.keys()))
    for tab, (cat_name, cat_data) in zip(cat_tabs, cats.items()):
        with tab:
            tdf = pd.DataFrame({"stat": list(cat_data.keys()),
                                "value": [round(float(v), 6) if pd.notna(v) and isinstance(v, (int, float)) else v
                                          for v in cat_data.values()]})
            st.dataframe(tdf, use_container_width=True, hide_index=True)

    # --- 5. IC scorecard ---
    st.subheader("IC scorecard (HAC + BH-FDR)")
    ic_p = ic_long[ic_long["product"] == product] if not ic_long.empty else pd.DataFrame()
    if not ic_p.empty:
        # Default to bar chart (numerical magnitude as bar length).
        # Heatmaps obscure structure; bars + line + top-K give complementary views.
        ic_view = st.radio("IC view", ["Bars (signal × horizon)",
                                         "Lines (decay over horizon)",
                                         "Top-K predictive cells"],
                            horizontal=True, key="dd_ic_view")
        if ic_view.startswith("Bars"):
            st.plotly_chart(plot_ic_bars(ic_p, HORIZONS), use_container_width=True)
            st.caption("Solid bars = HAC + BH-FDR-significant at α=0.05. Faded bars = not significant. "
                       "Hover for HAC t-stat and p-value.")
        elif ic_view.startswith("Lines"):
            st.plotly_chart(plot_ic_lines(ic_p, HORIZONS), use_container_width=True)
            st.caption("X-axis = forward-return horizon (log scale). Each line is one signal — flat-near-zero means "
                       "the signal has no predictability at any horizon; large positive/negative spikes flag the "
                       "horizon where the signal works.")
        else:
            top_k = st.slider("K", 5, 28, 10, key="dd_ic_topk")
            st.plotly_chart(plot_ic_topk(ic_p, HORIZONS, k=top_k), use_container_width=True)
            st.caption("Sorted descending by |IC|. Bright colour = FDR-pass; faded = not significant.")
        with st.expander("HAC t / p-value table", expanded=False):
            keep_cols = ["signal"] + [c for c in ic_p.columns if c.startswith(("ic_h", "t_h", "p_h", "n_h"))]
            if "significant" in ic_p.columns:
                keep_cols.append("significant")
            st.dataframe(ic_p[keep_cols], use_container_width=True, hide_index=True)

    # --- 6. Volatility analysis ---
    st.subheader("Volatility analysis")
    vol_row = vol[vol["product"] == product] if not vol.empty else pd.DataFrame()
    if not vol_row.empty:
        vrow = vol_row.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("rv_50_mean", f"{vrow.get('rv_50_mean', float('nan')):.3f}")
        c2.metric("vol_of_vol", f"{vrow.get('vol_of_vol', float('nan')):.3f}")
        c3.metric("rv p90/p10", f"{vrow.get('vol_p90_p10_ratio', float('nan')):.2f}")
        c4.metric("clustering acf₁", f"{vrow.get('vol_cluster_lag1', float('nan')):+.3f}")

        with st.expander("All vol stats (per-window rv mean/std/p10/p90)", expanded=False):
            keep = [c for c in vol_row.columns if c not in ("product", "family")]
            display = pd.DataFrame({"stat": keep, "value": [vrow[c] for c in keep]})
            st.dataframe(display, use_container_width=True, hide_index=True)

    # --- 7. Vol regime decomposition ---
    st.subheader("Volatility regime decomposition")
    st.caption("Tertile decomposition of std_50: per-regime spread / depth / |OBI| / |ret_1| means. "
               "If spread fails to widen ≥ 1.10× from low to high regime, passive MM is squeezed.")
    vrt = load_vol_regime(fam)
    if not vrt.empty and "product" in vrt.columns:
        vrt_p = vrt[vrt["product"] == product]
        if not vrt_p.empty:
            display_cols = [c for c in vrt_p.columns if c != "product"]
            st.dataframe(vrt_p[display_cols], use_container_width=True, hide_index=True)

    # Vol regime transitions
    vt = load_vol_regime_transitions(fam)
    if not vt.empty and "product" in vt.columns:
        vt_p = vt[vt["product"] == product]
        if not vt_p.empty:
            with st.expander("Regime transition matrix (3×3, row-stochastic)", expanded=False):
                st.dataframe(vt_p, use_container_width=True, hide_index=True)

    # --- 8. Vol-conditioned IC ---
    st.subheader("Vol-conditioned IC")
    st.caption("IC of each signal recomputed within each vol regime. "
               "Where |IC| differs by ≥ 0.04 across regimes, the signal is regime-gated.")
    vci = load_vol_conditioned_ic(fam)
    if not vci.empty:
        vci_p = vci[vci["product"] == product]
        if not vci_p.empty:
            # Pivot: signal × (horizon, regime) IC
            sigs = sorted(vci_p["signal"].unique())
            horizons_present = sorted(vci_p["horizon"].unique())
            tabs = st.tabs([f"h={h}" for h in horizons_present])
            for tab, h in zip(tabs, horizons_present):
                with tab:
                    sub = vci_p[vci_p["horizon"] == h]
                    if sub.empty: continue
                    pivot = sub.pivot(index="signal", columns="regime", values="ic")
                    pivot = pivot.reindex(columns=["low", "mid", "high"])
                    arr = pivot.values.astype(float)
                    zmax = max(0.05, float(np.nanmax(np.abs(arr))) if np.isfinite(arr).any() else 0.05)
                    fig = go.Figure(go.Heatmap(
                        z=arr, x=pivot.columns.tolist(), y=pivot.index.tolist(),
                        colorscale="RdBu_r", zmin=-zmax, zmax=zmax,
                        text=[[f"{v:+.3f}" if pd.notna(v) else "" for v in row] for row in arr],
                        texttemplate="%{text}",
                        hovertemplate="signal=%{y}<br>regime=%{x}<br>IC=%{z:+.3f}<extra></extra>",
                    ))
                    fig.update_layout(height=320, margin=dict(t=20, b=20, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True, key=f"vci_h{h}")

    # --- 9. Within-family relationships ---
    st.subheader("Within-family relationships")
    cm_tab, cr_tab, ll_tab, ct_tab = st.tabs(
        ["corr_mid (this row)", "corr_returns (this row)", "lead_lag", "cointegration pairs"]
    )
    with cm_tab:
        cm = load_family_matrix(fam, "corr_mid")
        if not cm.empty and product in cm.index:
            row = cm.loc[product].drop(product, errors="ignore").to_frame("corr").reset_index()
            row.columns = ["partner", "corr"]
            row = row.sort_values("corr", key=abs, ascending=False)
            fig = px.bar(row, x="partner", y="corr", color="corr",
                         color_continuous_scale="RdBu_r", range_color=(-1, 1),
                         title=f"corr_mid({product}, *)")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(row, use_container_width=True, hide_index=True)
    with cr_tab:
        cr = load_family_matrix(fam, "corr_returns")
        if not cr.empty and product in cr.index:
            row = cr.loc[product].drop(product, errors="ignore").to_frame("corr").reset_index()
            row.columns = ["partner", "corr"]
            row = row.sort_values("corr", key=abs, ascending=False)
            st.dataframe(row, use_container_width=True, hide_index=True)
    with ll_tab:
        ll = load_family_matrix(fam, "lead_lag")
        if not ll.empty and product in ll.index:
            leads = ll.loc[product].drop(product, errors="ignore").to_frame("leads (this->other, lag=10)")
            lags = ll[product].drop(product, errors="ignore").to_frame("lags (other->this, lag=10)")
            joined = leads.join(lags).reset_index().rename(columns={"index": "partner"})
            st.dataframe(joined, use_container_width=True, hide_index=True)
    with ct_tab:
        coint = load_cointegration(fam)
        if not coint.empty:
            mine = coint[(coint["a"] == product) | (coint["b"] == product)].copy()
            mine["partner"] = mine.apply(lambda x: x["b"] if x["a"] == product else x["a"], axis=1)
            mine["stationary (p<0.10)"] = mine["coint_p"] < 0.10
            st.dataframe(mine[["partner", "coint_t", "coint_p", "stationary (p<0.10)"]].sort_values("coint_p"),
                         use_container_width=True, hide_index=True)

    # --- 10. PAIR partner profile (if PAIR_ANCHOR fires) ---
    if r.get("is_pair") and pd.notna(r.get("pair_partner")):
        st.subheader(f"PAIR_ANCHOR partner: {r['pair_partner']}")
        partner = r["pair_partner"]
        partner_arch_df = arch[arch["product"] == partner]
        partner_stats_df = stats[stats["product"] == partner]
        if not partner_arch_df.empty and not partner_stats_df.empty:
            pa = partner_arch_df.iloc[0]
            ps = partner_stats_df.iloc[0]
            st.markdown(
                f"**{partner}** — primary: {archetype_badge(pa['archetype'])} &nbsp; "
                f"confidence: {confidence_badge(pa.get('mr_confidence', 'n/a'))}",
                unsafe_allow_html=True,
            )
            cmp_df = pd.DataFrame({
                "stat": ["vr_k5", "hurst", "acf_ret1_lag1", "vwap_hurst", "vwap_acf_lag1",
                          "spread_median", "ret1_std", "limit10_saturation"],
                product: [stats_row.get(c) for c in ["vr_k5", "hurst", "acf_ret1_lag1", "vwap_hurst",
                                                      "vwap_acf_lag1", "spread_median", "ret1_std",
                                                      "limit10_saturation"]],
                partner: [ps.get(c) for c in ["vr_k5", "hurst", "acf_ret1_lag1", "vwap_hurst",
                                               "vwap_acf_lag1", "spread_median", "ret1_std",
                                               "limit10_saturation"]],
            })
            st.dataframe(cmp_df, use_container_width=True, hide_index=True)
            stat_status = "STATIONARY (fixed-β hedge OK)" if r.get("pair_residual_stationary") else "non-stationary (rolling β required)"
            corr_v = r.get("pair_corr", float("nan"))
            cp_v = r.get("pair_coint_p", float("nan"))
            st.info(f"**Pair stats**: corr={corr_v:+.3f}, coint_p={cp_v:.3f} → {stat_status}")

    # --- 11. MM template details (if is_mm or mm_provisional fired) ---
    if r.get("is_mm") or r.get("mm_pnl") is not None and pd.notna(r.get("mm_pnl")):
        st.subheader("MM_CANDIDATE template (Template-A passive MM)")
        c1, c2, c3 = st.columns(3)
        pnl = r.get("mm_pnl", float("nan"))
        fills = int(r.get("mm_fills") or 0)
        c1.metric("Sim PnL", f"{float(pnl):+.2f}" if pd.notna(pnl) else "—")
        c2.metric("Fills", fills)
        status = "CONFIRMED" if pd.notna(pnl) and pnl > 0 else ("UNTESTED (0 fills)" if fills == 0 else "REJECTED")
        c3.metric("Status", status)
        st.caption(f"Quote: `mid ± max(min_edge, k_vol·rv) − γ·rv²·inventory`. "
                   f"Params: {r.get('mm_params', {})}")
        # Interactive MM health: quotes, inventory, cumulative PnL
        import ast
        mm_params_raw = r.get("mm_params") or "{}"
        if isinstance(mm_params_raw, str):
            try:
                mm_params_dict = ast.literal_eval(mm_params_raw)
            except (ValueError, SyntaxError):
                mm_params_dict = {}
        else:
            mm_params_dict = dict(mm_params_raw)
        if mm_params_dict:
            with st.spinner("Running Template-A simulation for interactive health figure..."):
                px_mm, tr_mm = load_product_px_tr(product)
            if not px_mm.empty:
                st.plotly_chart(plot_mm_health(px_mm, tr_mm, mm_params_dict),
                                 use_container_width=True)
                st.caption("Top: mid + bid/ask quotes within a sample window (full series too dense). "
                           "Middle: inventory (dashed red = ±position-limit). "
                           "Bottom: cumulative simulated PnL.")

    # --- 12. Cross-family cluster context ---
    st.subheader("Cross-family cluster")
    clu = load_cross_clusters()
    if not clu.empty and "product" in clu.columns:
        my_cluster = clu[clu["product"] == product]
        if not my_cluster.empty:
            cid = my_cluster.iloc[0].get("cluster", my_cluster.iloc[0].get("cluster_id"))
            siblings = clu[clu.get("cluster", clu.get("cluster_id")) == cid]
            st.markdown(f"This product is in cluster **{cid}** alongside {len(siblings)} other products.")
            st.dataframe(siblings, use_container_width=True, hide_index=True, height=240)
        else:
            st.caption("Cluster assignment not found.")
    else:
        st.caption("Cross-family analysis not yet run.")

    # --- 13. Deep-research triggers ---
    st.subheader("Deep-research triggers")
    dt = load_deep_triggers(fam)
    if dt:
        # Just show whether THIS product is mentioned
        if product in dt:
            relevant_lines = [ln for ln in dt.split("\n") if product in ln]
            if relevant_lines:
                for ln in relevant_lines:
                    st.markdown(f"- {ln.strip()}")
            else:
                st.caption("Product mentioned in triggers file but no specific section.")
        else:
            st.caption(f"`{product}` did not cross any deep-research trigger threshold (>=2 of {{vr, hurst, acf, IC}} per direction).")

    # --- 14. Data quality ---
    if not dq.empty:
        st.subheader("Data quality")
        dq_p = dq[dq["product"] == product]
        if not dq_p.empty:
            warns = dq_p.iloc[0].get("warnings", "")
            if warns:
                st.warning(f"⚠️ {warns}")
            else:
                st.success("✓ No data-quality warnings.")
            with st.expander("Full data-quality row", expanded=False):
                st.dataframe(dq_p.T, use_container_width=True)

    # --- 15. Interactive figures (Plotly — re-derived from raw px/tr) ---
    st.subheader("Interactive figures")
    with st.spinner(f"Loading raw data for {product} (cached after first load)..."):
        px_p, tr_p = load_product_px_tr(product)
    if px_p.empty:
        st.warning("Could not load raw data for this product.")
    else:
        st.caption(f"Loaded {len(px_p):,} ticks across {px_p['day'].nunique()} day(s) "
                   f"and {len(tr_p):,} trades. All charts below are interactive — "
                   f"zoom, pan, hover for values, click legend to toggle traces.")

        fig_tabs = st.tabs(["Price", "Returns", "ACF", "Spread", "Depth", "OBI vs fwd_ret",
                             "Signed flow", "Volatility"])
        with fig_tabs[0]:
            sample_step = st.slider("Downsample step (1 = full resolution)", 1, 20, 1, key="dd_price_step")
            st.plotly_chart(plot_price_series(px_p, tr_p, sample_step=sample_step),
                             use_container_width=True)
        with fig_tabs[1]:
            st.plotly_chart(plot_returns_hist(px_p), use_container_width=True)
        with fig_tabs[2]:
            max_lag = st.slider("Max lag", 20, 500, 100, step=20, key="dd_acf_lag")
            st.plotly_chart(plot_acf(px_p, max_lag=max_lag), use_container_width=True)
        with fig_tabs[3]:
            st.plotly_chart(plot_spread_hist(px_p), use_container_width=True)
        with fig_tabs[4]:
            st.plotly_chart(plot_depth_profile(px_p), use_container_width=True)
        with fig_tabs[5]:
            h_choice = st.select_slider("Forward-return horizon",
                                          options=list(HORIZONS), value=10, key="dd_obi_h")
            st.plotly_chart(plot_obi_vs_fwd_ret(px_p, horizon=h_choice),
                             use_container_width=True)
            st.caption("Grey dots = sampled ticks. Red line = OBI-decile mean ±SE. "
                       "Black dotted = OLS fit. A non-flat red line ⇒ OBI predicts forward return.")
        with fig_tabs[6]:
            st.plotly_chart(plot_signed_flow(px_p, tr_p), use_container_width=True)
        with fig_tabs[7]:
            st.plotly_chart(plot_vol_over_time(px_p), use_container_width=True)
            st.caption("Tertile bands (low/mid/high) come from std_50 quantiles. "
                       "Vertical dashes = day boundaries.")



# ---------------------------------------------------------------------------
# View 5 (renamed from 4): Cross-Family
# ---------------------------------------------------------------------------

def view_cross():
    st.header("Cross-Family Findings")
    md = load_cross_findings_md()
    if not md:
        st.warning("Cross-family analysis not yet run. Execute "
                   "`.venv/Scripts/python.exe round5/cross_analysis.py` from repo root.")
        return

    tab_summary, tab_clusters, tab_leadlag, tab_perf = st.tabs(
        ["Summary", "Clusters", "Lead-lag pairs", "Cluster performance"]
    )

    with tab_summary:
        st.markdown(md)

    with tab_clusters:
        clu = load_cross_clusters()
        if not clu.empty:
            # Membership table
            st.markdown("**Cluster membership**")
            st.dataframe(clu, use_container_width=True, hide_index=True, height=240)

            # Bar chart of cluster sizes
            cid_col = "cluster_id" if "cluster_id" in clu.columns else (
                "cluster" if "cluster" in clu.columns else None
            )
            if cid_col:
                sizes = clu.groupby(cid_col).size().reset_index(name="n_products")
                bar = px.bar(sizes, x=cid_col, y="n_products",
                              text="n_products", color=cid_col,
                              color_discrete_sequence=px.colors.qualitative.Set2)
                bar.update_layout(height=300, margin=dict(t=20, b=30, l=10, r=10),
                                   showlegend=False, title="Products per cluster")
                st.plotly_chart(bar, use_container_width=True)

        # Cluster aggregate series
        agg = load_cluster_aggregate()
        if not agg.empty:
            st.markdown("**Cluster aggregate (mean of products) over time**")
            st.plotly_chart(plot_cluster_aggregate(agg), use_container_width=True)

    with tab_leadlag:
        pairs = load_cross_pairs()
        if not pairs.empty:
            st.markdown("**Stable cross-cluster lead-lag pairs**")
            st.plotly_chart(plot_leadlag_pairs_bar(pairs, top_k=20),
                             use_container_width=True)
            with st.expander("Stable pairs table", expanded=False):
                st.dataframe(pairs, use_container_width=True, hide_index=True)
        # Full lead-lag heatmap (one-lag at a time, slider)
        ll_full = load_leadlag_full()
        if not ll_full.empty:
            lags_avail = sorted(ll_full["lag"].unique()) if "lag" in ll_full.columns else [1]
            chosen_lag = st.select_slider("Lag (ticks)", options=lags_avail,
                                            value=1 if 1 in lags_avail else lags_avail[0],
                                            key="cross_ll_lag")
            st.plotly_chart(plot_leadlag_full_heatmap(ll_full, lag=chosen_lag),
                             use_container_width=True)

    with tab_perf:
        perf = load_cluster_perf()
        if not perf.empty:
            st.markdown("**Per-cluster rolling rank over time** (1 = best)")
            st.plotly_chart(plot_cluster_rolling_rank(perf), use_container_width=True)
            with st.expander("Performance table", expanded=False):
                st.dataframe(perf, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# View 5b: Volatility Spikes
# ---------------------------------------------------------------------------

POST_HORIZONS_VIZ = (1, 5, 10, 50, 200)


def view_vol_spikes():
    st.header("Volatility Spikes")
    summary = load_spike_summary()
    if summary.empty:
        st.warning("Vol-spike study not yet run. Execute "
                   "`.venv/Scripts/python.exe round5/vol_spikes.py` from repo root.")
        return

    cooc = load_spike_cooccurrence()
    cooc_mat = load_spike_cooccurrence_matrix()
    fam_sum = load_spike_family_summary()
    post_long = load_spike_post_returns()
    report_md = load_spike_report_md()

    n_total = int(summary["n_spikes"].sum())
    n_products_with_spikes = int((summary["n_spikes"] > 0).sum())
    weighted_peer = (
        (cooc["n_spikes"] * cooc["mean_peer_count"]).sum() / cooc["n_spikes"].sum()
        if not cooc.empty and cooc["n_spikes"].sum() > 0 else float("nan")
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total spikes (4σ)", f"{n_total}")
    c2.metric("Products w/ ≥1 spike", f"{n_products_with_spikes}/50")
    c3.metric("Mean peer count", f"{weighted_peer:.2f}",
              help="When a product spikes, mean # of *other* products spiking within ±2 ticks. "
                   "Weighted across all spike events.")
    big4_share = (
        summary.sort_values("n_spikes", ascending=False).head(4)["n_spikes"].sum()
        / max(1, n_total)
    )
    c4.metric("Top-4 share of spikes", f"{big4_share:.0%}")

    tab_summary, tab_post, tab_cooc, tab_family, tab_panels, tab_mech, tab_strat, tab_report = st.tabs(
        ["Summary", "Post-spike profile", "Co-occurrence", "Family", "Per-product panels",
         "Mechanism", "Strategy PnL", "Full report"]
    )

    with tab_summary:
        st.markdown("**Method** — spike = `|ret_1| ≥ 4 · std_500.shift(1)` per day.")
        st.markdown("Sorted by spike rate.")
        cols_show = [
            "family", "product", "n_ticks", "n_spikes", "spike_rate_per_10k",
            "z_mean", "z_max", "abs_ret_mean", "spread_widen_x", "depth_drop_x",
            "post_h10_mean", "post_h50_mean",
        ]
        cols_show = [c for c in cols_show if c in summary.columns]
        sorted_df = summary[cols_show].sort_values("n_spikes", ascending=False).reset_index(drop=True)

        def _highlight_post(row):
            v = row.get("post_h10_mean", float("nan"))
            if pd.notna(v) and row.get("n_spikes", 0) >= 10:
                if v >= 10:
                    return ["background-color: #d6efd6"] * len(row)
                if v <= -10:
                    return ["background-color: #f7d4d4"] * len(row)
            return [""] * len(row)

        st.dataframe(
            sorted_df.style.apply(_highlight_post, axis=1).format({
                "spike_rate_per_10k": "{:.2f}",
                "z_mean": "{:.2f}", "z_max": "{:.2f}",
                "abs_ret_mean": "{:.1f}",
                "spread_widen_x": "{:.2f}", "depth_drop_x": "{:.2f}",
                "post_h10_mean": "{:+.1f}", "post_h50_mean": "{:+.1f}",
            }),
            use_container_width=True, hide_index=True, height=520,
        )
        st.caption("Green = strong post-spike reversion (≥+10 ticks at h=10, n_spikes≥10); "
                   "red = momentum follow-through (≤−10).")

        # Spike count bar chart (top 15)
        top15 = summary.sort_values("n_spikes", ascending=False).head(15)
        fig = go.Figure()
        fig.add_bar(x=top15["product"], y=top15["n_spikes"],
                    marker_color=["#c0392b" if v >= 50 else "#3498db" for v in top15["n_spikes"]])
        fig.update_layout(
            title="Top 15 spike-prone products",
            xaxis_tickangle=-45, height=380, margin=dict(l=20, r=20, t=40, b=120),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_post:
        st.markdown("Per-spike mean signed cumret = `−sign(spike) · (mid_{t+h} − mid_t)`. "
                    "**Positive ⇒ reversion**, negative ⇒ momentum follow-through.")
        big = summary[summary["n_spikes"] >= 5].sort_values("n_spikes", ascending=False)
        if big.empty:
            st.info("No products with ≥5 spikes.")
        else:
            picks = st.multiselect(
                "Products to overlay",
                options=big["product"].tolist(),
                default=big["product"].head(8).tolist(),
            )
            fig = go.Figure()
            for p in picks:
                row = post_long[post_long["product"] == p].sort_values("horizon")
                if row.empty:
                    continue
                fig.add_scatter(
                    x=row["horizon"], y=row["mean"],
                    mode="lines+markers", name=p,
                    error_y=dict(
                        type="data",
                        array=row["std"] / np.sqrt(row["n"].clip(lower=1)),
                        thickness=0.8, width=2,
                    ),
                )
            fig.add_hline(y=0, line=dict(color="black", width=0.6))
            fig.update_xaxes(type="log", title="horizon (ticks)")
            fig.update_yaxes(title="mean signed cumret  (>0 ⇒ revert)")
            fig.update_layout(title="Post-spike profile", height=480, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    with tab_cooc:
        st.markdown(
            "Per-spike peer count: how many *other* products spiked within ±2 ticks. "
            "`systemic_rate = P(peer_count ≥ 5)`."
        )
        if cooc.empty:
            st.info("No co-occurrence data.")
        else:
            merged = cooc.merge(
                summary[["product", "family"]], on="product", how="left"
            )
            cols = ["family", "product", "n_spikes", "mean_peer_count",
                    "median_peer_count", "systemic_rate"]
            cols = [c for c in cols if c in merged.columns]
            st.dataframe(
                merged[cols].sort_values("n_spikes", ascending=False),
                use_container_width=True, hide_index=True, height=420,
            )
        if not cooc_mat.empty:
            st.markdown("**Co-occurrence matrix** (cosine: `pair_count / sqrt(n_a · n_b)`).")
            diag = np.diag(cooc_mat.values).astype(float).copy()
            denom = np.outer(np.sqrt(diag), np.sqrt(diag))
            with np.errstate(divide="ignore", invalid="ignore"):
                cosine = np.where(denom > 0, cooc_mat.values / denom, np.nan)
            np.fill_diagonal(cosine, np.nan)
            short = [p.split("_", 1)[-1][:14] for p in cooc_mat.columns]
            vmax_val = float(np.nanpercentile(cosine, 95)) if np.isfinite(cosine).any() else 1.0
            fig = go.Figure(go.Heatmap(
                z=cosine, x=short, y=short, colorscale="Magma",
                zmin=0, zmax=max(vmax_val, 1e-6),
                colorbar=dict(title="cosine"),
            ))
            fig.update_layout(
                title="Spike co-occurrence (cosine)",
                height=720, xaxis_tickangle=-90,
                xaxis=dict(tickfont=dict(size=8)),
                yaxis=dict(tickfont=dict(size=8), autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab_family:
        if fam_sum.empty:
            st.info("No family aggregate.")
        else:
            cols = [
                "family", "n_spikes_total", "spike_rate_per_10k_mean", "z_mean",
                "spread_widen_x_mean", "depth_drop_x_mean", "systemic_rate_mean",
                "post_h1_family_mean", "post_h10_family_mean",
                "post_h50_family_mean", "post_h200_family_mean",
            ]
            cols = [c for c in cols if c in fam_sum.columns]
            st.dataframe(
                fam_sum[cols].sort_values("n_spikes_total", ascending=False),
                use_container_width=True, hide_index=True,
            )
            # Family-level post-spike profile lines
            fig = go.Figure()
            for _, row in fam_sum.iterrows():
                ys = [row.get(f"post_h{h}_family_mean") for h in POST_HORIZONS_VIZ]
                if all(pd.isna(y) for y in ys):
                    continue
                fig.add_scatter(
                    x=list(POST_HORIZONS_VIZ), y=ys,
                    mode="lines+markers", name=row["family"],
                )
            fig.add_hline(y=0, line=dict(color="black", width=0.6))
            fig.update_xaxes(type="log", title="horizon (ticks)")
            fig.update_yaxes(title="mean signed cumret  (>0 ⇒ revert)")
            fig.update_layout(title="Family-level post-spike profile",
                              height=440, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    with tab_panels:
        spiky = summary[summary["n_spikes"] > 0].sort_values("n_spikes", ascending=False)
        if spiky.empty:
            st.info("No products with spikes.")
        else:
            product_pick = st.selectbox(
                "Product",
                options=spiky["product"].tolist(),
                index=0,
            )
            with st.spinner(f"Loading raw data for {product_pick} ..."):
                px_sp, tr_sp = load_product_px_tr(product_pick)
            events_df = load_spike_events() if "load_spike_events" in globals() else pd.DataFrame()
            if events_df.empty:
                events_path = VOL_SPIKES_DIR / "spike_events.csv"
                if events_path.exists():
                    events_df = pd.read_csv(events_path)
            st.plotly_chart(plot_spike_panel(product_pick, px_sp, tr_sp, events_df),
                             use_container_width=True)
            row = summary[summary["product"] == product_pick].iloc[0]
            st.markdown(
                f"**{product_pick}** — n_spikes={int(row['n_spikes'])}, "
                f"rate / 10k = {row['spike_rate_per_10k']:.2f}, "
                f"z_mean = {row['z_mean']:.2f}, z_max = {row['z_max']:.2f}, "
                f"spread_widen = {row['spread_widen_x']:.2f}×, "
                f"depth_at_spike = {row['depth_drop_x']:.2f}×."
            )

    with tab_mech:
        anatomy = load_spike_anatomy()
        recovery = load_spike_recovery()
        mech_md = load_spike_mechanism_report_md()
        if anatomy.empty:
            st.warning("Spike anatomy not yet run. Execute "
                       "`.venv/Scripts/python.exe round5/spike_anatomy.py` from repo root.")
        else:
            classified = anatomy[anatomy["mechanism"] != "INSUFFICIENT_DATA"].copy()
            st.markdown(
                "**Mechanism classifier** — three regimes drive 4σ events. "
                "Each implies an opposite trading prescription."
            )
            mech_palette = {
                "QUANTIZED_QUOTE_REFRESH": "#3498db",
                "FAST_NOISE_OSCILLATOR": "#16a085",
                "PRICE_DISCOVERY_BREAKOUT": "#c0392b",
                "AGGRESSOR_SWEEP": "#8e44ad",
                "PARTIAL_QUANTIZATION": "#5dade2",
                "HEAVY_TAIL_GAUSSIAN": "#7f8c8d",
            }

            def _row_color(row):
                col = mech_palette.get(row.get("mechanism", ""), "")
                if not col:
                    return [""] * len(row)
                return [f"background-color: {col}; color: white"] * len(row)

            cols = ["family", "product", "n_spikes", "mechanism",
                    "spread_locked_share", "spread_dominant",
                    "dominant_jump_size", "dominant_jump_share",
                    "n_unique_jumps", "trade_at_spike_rate", "acf_lag1",
                    "snap_back_h_50pct", "reversion_pct_h10", "reversion_pct_h50",
                    "rationale"]
            cols = [c for c in cols if c in classified.columns]
            st.dataframe(
                classified[cols].sort_values(["mechanism", "n_spikes"],
                                             ascending=[True, False])
                                .style.apply(_row_color, axis=1)
                                .format({
                                    "spread_locked_share": "{:.2%}",
                                    "spread_dominant": "{:.0f}",
                                    "dominant_jump_size": "{:.1f}",
                                    "dominant_jump_share": "{:.2%}",
                                    "n_unique_jumps": "{:.0f}",
                                    "trade_at_spike_rate": "{:.2%}",
                                    "acf_lag1": "{:+.3f}",
                                    "snap_back_h_50pct": "{:.0f}",
                                    "reversion_pct_h10": "{:+.2f}",
                                    "reversion_pct_h50": "{:+.2f}",
                                }),
                use_container_width=True, hide_index=True, height=320,
            )
            st.caption(
                "QUANTIZED + FAST_NOISE → fade. PRICE_DISCOVERY → follow. "
                "Rev fraction <0 ⇒ price *continues* past spike."
            )

            # Recovery curves overlay
            if not recovery.empty:
                st.markdown("**Recovery curve** — fraction of spike undone vs horizon.")
                fig = go.Figure()
                merged = recovery.merge(
                    classified[["product", "mechanism"]], on="product", how="left"
                )
                for p, sub in merged.groupby("product"):
                    sub = sub.sort_values("horizon")
                    mech = sub["mechanism"].iloc[0] if not sub.empty else ""
                    color = mech_palette.get(mech, None)
                    fig.add_scatter(
                        x=sub["horizon"], y=sub["mean_reversion_frac"],
                        mode="lines+markers", name=f"{p} [{mech}]",
                        line=dict(color=color),
                    )
                fig.add_hline(y=1.0, line=dict(color="grey", dash="dot", width=0.6))
                fig.add_hline(y=0.5, line=dict(color="grey", dash="dot", width=0.6))
                fig.add_hline(y=0.0, line=dict(color="black", width=0.6))
                fig.update_xaxes(type="log", title="horizon (ticks)")
                fig.update_yaxes(title="mean reversion fraction (1 = full snap-back, <0 = continues)")
                fig.update_layout(title="Spike recovery by mechanism", height=460,
                                  hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            # Per-product anatomy figure
            spiky = classified[classified["n_spikes"] >= 5].sort_values(
                "n_spikes", ascending=False)
            if not spiky.empty:
                pick = st.selectbox(
                    "Anatomy figure",
                    options=spiky["product"].tolist(),
                    key="mech_pick",
                )
                img = SPIKE_ANATOMY_DIR / "figures" / f"{pick}_anatomy.png"
                if img.exists():
                    st.image(str(img), use_container_width=True)
                else:
                    st.info(f"Figure not found: {img.name}")

    with tab_strat:
        strat = load_spike_strategy_pnl()
        if strat.empty:
            st.warning("Strategy sim not yet run. Execute "
                       "`.venv/Scripts/python.exe round5/spike_strategy_sim.py` from repo root.")
        else:
            anatomy = load_spike_anatomy()
            st.markdown(
                "**Spike-conditional taker PnL** — fade vs follow at the next tick "
                "after a 4σ event, exit at horizon `h`, full bid/ask cross at both ends, "
                "size = 10 (round-5 limit)."
            )
            # Per-product best strategy table
            best = (strat.sort_values("total_pnl", ascending=False)
                         .groupby("product").head(1)
                         .sort_values("total_pnl", ascending=False))
            best = best.merge(
                anatomy[["product", "mechanism"]], on="product", how="left"
            )
            cols = ["product", "mechanism", "strategy", "horizon", "n_events",
                    "total_pnl", "mean_pnl_per_event", "hit_rate", "sharpe_per_event"]
            cols = [c for c in cols if c in best.columns]

            def _strat_color(row):
                if row.get("strategy") == "FOLLOW":
                    return ["background-color: #fde2cf"] * len(row)
                if row.get("strategy") == "FADE":
                    return ["background-color: #d6efd6"] * len(row)
                return [""] * len(row)

            st.dataframe(
                best[cols].style.apply(_strat_color, axis=1)
                              .format({
                                  "total_pnl": "{:+.0f}",
                                  "mean_pnl_per_event": "{:+.1f}",
                                  "hit_rate": "{:.0%}",
                                  "sharpe_per_event": "{:+.3f}",
                              }),
                use_container_width=True, hide_index=True,
            )

            st.markdown("**Aggregate at h=20** (single horizon, no per-product cherry-pick):")
            agg_h20 = strat[strat["horizon"] == 20].copy()
            if not agg_h20.empty:
                # Pair with mechanism to recommend side per product
                agg_h20 = agg_h20.merge(
                    anatomy[["product", "mechanism"]], on="product", how="left"
                )
                agg_h20["recommended_side"] = agg_h20["mechanism"].map({
                    "QUANTIZED_QUOTE_REFRESH": "FADE",
                    "FAST_NOISE_OSCILLATOR": "FADE",
                    "PARTIAL_QUANTIZATION": "FADE",
                    "PRICE_DISCOVERY_BREAKOUT": "FOLLOW",
                    "HEAVY_TAIL_GAUSSIAN": "FADE",
                    "AGGRESSOR_SWEEP": "FOLLOW",
                })
                use_row = agg_h20[agg_h20["strategy"] == agg_h20["recommended_side"]]
                total = float(use_row["total_pnl"].sum()) if not use_row.empty else 0.0
                fade_total = float(use_row[use_row["strategy"] == "FADE"]["total_pnl"].sum())
                follow_total = float(use_row[use_row["strategy"] == "FOLLOW"]["total_pnl"].sum())
                c1, c2, c3 = st.columns(3)
                c1.metric("FADE side total", f"{fade_total:+,.0f}")
                c2.metric("FOLLOW side total", f"{follow_total:+,.0f}")
                c3.metric("Combined PnL @ h=20 (3 days)", f"{total:+,.0f}",
                          help="Sum of recommended side per product, single horizon h=20.")

            # PnL across horizons (lines per product)
            st.markdown("**Per-product PnL across horizons**:")
            picks = st.multiselect(
                "Products",
                options=sorted(strat["product"].unique()),
                default=sorted(strat["product"].unique()),
                key="strat_picks",
            )
            sub = strat[strat["product"].isin(picks)]
            for side, color in (("FADE", "#27ae60"), ("FOLLOW", "#e67e22")):
                fig = go.Figure()
                for p, g in sub[sub["strategy"] == side].groupby("product"):
                    g = g.sort_values("horizon")
                    fig.add_scatter(
                        x=g["horizon"], y=g["total_pnl"],
                        mode="lines+markers", name=p,
                    )
                fig.add_hline(y=0, line=dict(color="black", width=0.6))
                fig.update_xaxes(type="log", title="horizon (ticks)")
                fig.update_yaxes(title="total PnL (sea shells)")
                fig.update_layout(title=f"{side} taker — total PnL across horizons",
                                  height=380, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            # Per-product strategy figure
            with st.expander("Per-product strategy figure (matplotlib)", expanded=False):
                pick = st.selectbox(
                    "Product",
                    options=sorted(strat["product"].unique()),
                    key="strat_pick_img",
                )
                img = SPIKE_ANATOMY_DIR / "figures" / f"{pick}_strategy.png"
                if img.exists():
                    st.image(str(img), use_container_width=True)

    with tab_report:
        rep_choice = st.radio(
            "Report",
            options=["Vol-spike survey", "Mechanism + strategy"],
            horizontal=True,
        )
        if rep_choice == "Vol-spike survey":
            if report_md:
                st.markdown(report_md)
            else:
                st.info("vol_spikes_report.md not found.")
        else:
            mech_md = load_spike_mechanism_report_md()
            if mech_md:
                st.markdown(mech_md)
            else:
                st.info("spike_mechanism_report.md not found. "
                        "Run `round5/spike_anatomy.py` and `round5/spike_strategy_sim.py`.")


# ---------------------------------------------------------------------------
# View 5: Calibration
# ---------------------------------------------------------------------------

def view_calibration(arch: pd.DataFrame):
    st.header("Threshold Calibration")
    cal = load_calibration()
    panel = load_calibration_panel()

    if cal.empty:
        st.warning("Calibration not yet run. Execute "
                   "`.venv/Scripts/python.exe round5/calibration.py` from repo root.")
        return

    st.markdown("Each gate's empirical pass-rate against the universe. "
                "`DEGENERATE_HIGH` = ≥95% of products pass (no-op gate); "
                "`DEGENERATE_LOW` = ≤5% pass (blanket exclusion).")

    # Highlight degenerate gates
    def highlight(row):
        f = str(row.get("flag", ""))
        if "DEGENERATE_HIGH" in f:
            return ["background-color: #ffe0b3"] * len(row)
        if "DEGENERATE_LOW" in f:
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    show_cols = [c for c in ["gate", "stat", "direction", "value", "n_pass", "n",
                             "frac_pass", "p25", "p50", "p75", "flag", "meaning"]
                 if c in cal.columns]
    st.dataframe(cal[show_cols].style.apply(highlight, axis=1),
                 use_container_width=True, hide_index=True, height=520)

    # Per-gate interactive distribution histograms
    st.subheader("Gate distributions (interactive)")
    if not panel.empty and not cal.empty:
        # Map gate name → underlying stat column from the calibration spec
        gate_to_stat = dict(zip(cal["gate"], cal["stat"])) if "stat" in cal.columns else {}
        gate_to_dir = dict(zip(cal["gate"], cal["direction"])) if "direction" in cal.columns else {}
        gate_to_thr = dict(zip(cal["gate"], cal["value"])) if "value" in cal.columns else {}
        gate_names = sorted(cal["gate"].unique()) if "gate" in cal.columns else []
        cols = st.columns(2)
        for i, g in enumerate(gate_names):
            stat_col = gate_to_stat.get(g)
            thr = gate_to_thr.get(g)
            direction = gate_to_dir.get(g, "lt")
            if stat_col and thr is not None and stat_col in panel.columns:
                with cols[i % 2]:
                    st.plotly_chart(
                        plot_calibration_distribution(panel, stat_col, float(thr), direction, g),
                        use_container_width=True,
                        key=f"calib_{g}",
                    )

    if not panel.empty:
        with st.expander("Per-product calibration panel", expanded=False):
            st.dataframe(panel, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Round 5 Pipeline Visualizer", layout="wide",
                       initial_sidebar_state="expanded")

    arch = load_archetypes()
    stats = load_stats()
    micro = load_micro()
    ic_long = load_ic_long()
    vol = load_volatility()
    dq = load_data_quality()

    if arch.empty:
        st.error("No archetype reports found under round5/reports/. "
                 "Run `python round5/family_report.py --family ALL` first.")
        return

    with st.sidebar:
        st.title("Round 5")
        st.caption("Pipeline visualizer")
        view = st.radio("View", ["Universe", "Family", "Product", "Product Deep Dive",
                                  "Cross-Family", "Vol Spikes", "Calibration"])
        st.divider()
        st.caption(f"{len(arch)} products / {arch['family'].nunique()} families")
        st.caption(f"MR_TAKER: {(arch['archetype']=='MR_TAKER').sum()}  /  "
                   f"NO_EDGE: {(arch['archetype']=='NO_EDGE').sum()}")
        st.caption(f"Flags — PAIR: {int(arch['is_pair'].sum())}, "
                   f"OBI: {int(arch['is_obi'].sum())}, "
                   f"MM: {int(arch['is_mm'].sum())}")
        st.divider()
        if st.button("Reload data (clear cache)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if view == "Universe":
        view_universe(arch, stats)
    elif view == "Family":
        view_family(arch, stats, micro, vol)
    elif view == "Product":
        view_product(arch, stats, ic_long, vol, dq)
    elif view == "Product Deep Dive":
        view_product_deep_dive(arch, stats, ic_long, vol, dq)
    elif view == "Cross-Family":
        view_cross()
    elif view == "Vol Spikes":
        view_vol_spikes()
    elif view == "Calibration":
        view_calibration(arch)


if __name__ == "__main__":
    main()
