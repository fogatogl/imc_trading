"""Cross-family / cluster-level research for round 5.

Implements the playbook from ``round5/analysis_brief.md``:

    1. Load + align all 50 products.
    2. Cluster products by structural characteristics (correlation-distance
       hierarchical + k-means on standardised features).
    3. Build per-cluster aggregate series; rank clusters by rolling
       performance.
    4. Detect cross-cluster lead-lag at multiple lags; require stability
       across rolling windows.
    5. Optional Granger-causality confirmation on stable pairs.

Logic gates: every stage carries a permissive threshold. When the data does
not pass the gate, the stage emits a "skipped — reason" line rather than a
spurious finding. Gate thresholds are configurable via ``Gates``.

Per-family analysis stays in ``research_lib`` / ``deep_research`` /
``volatility``. This module is *only* the inter-family layer.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

try:
    from imc_stats.stats import variance_ratio
except ModuleNotFoundError:
    from imc_commun.stats import variance_ratio

from .research_lib import (
    DATASET_ROOT,
    DEFAULT_DAYS,
    FAMILIES,
    ProductData,
    _save,
    add_microstructure,
    load_prices,
    load_trades,
)

ALL_PRODUCTS: list[str] = [p for fam_list in FAMILIES.values() for p in fam_list]
PRODUCT_TO_FAMILY: dict[str, str] = {
    p: fam for fam, members in FAMILIES.items() for p in members
}


@dataclass(frozen=True)
class Gates:
    """All thresholds in one place for transparency.

    The pipeline emits "skipped" rather than misleading output when a stage
    fails its gate.
    """
    silhouette_min: float = 0.05            # cluster structure must clear this
    cluster_k_min: int = 2
    cluster_k_max: int = 12
    min_cluster_size: int = 4               # every cluster must have >= this many members
    leadlag_corr_min: float = 0.05          # |corr| at optimal lag
    leadlag_max_lag: int = 30               # ticks (search window ±)
    stability_min: float = 0.6              # frac of windows where lag matches global
    stability_n_windows: int = 5
    granger_p_max: float = 0.10
    granger_max_lag: int = 5
    bootstrap_n: int = 30                   # bootstrap resamples for cluster stability
    bootstrap_frac: float = 0.7             # frac of timestamps drawn each resample
    bootstrap_ari_min: float = 0.5          # mean ARI gate; below this, structure is unstable


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_all(
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
    verbose: bool = True,
) -> dict[str, ProductData]:
    out: dict[str, ProductData] = {}
    for i, p in enumerate(ALL_PRODUCTS, 1):
        if verbose and i % 10 == 0:
            print(f"  loaded {i}/{len(ALL_PRODUCTS)} ...")
        px = load_prices(p, days=days, root=root)
        px = add_microstructure(px)
        tr = load_trades(p, days=days, root=root)
        out[p] = ProductData(product=p, px=px, tr=tr)
    return out


def returns_panel(all_data: dict[str, ProductData], col: str = "ret_1") -> pd.DataFrame:
    """Aligned panel: rows = (day, timestamp), cols = product."""
    series = {}
    for p, d in all_data.items():
        if d.px.empty or col not in d.px.columns:
            continue
        s = d.px.set_index(["day", "timestamp"])[col]
        s = s[~s.index.duplicated(keep="first")]
        series[p] = s
    if not series:
        return pd.DataFrame()
    panel = pd.DataFrame(series)
    return panel


def rolling_vol_panel(
    all_data: dict[str, ProductData], window: int = 50
) -> pd.DataFrame:
    """Aligned panel of rolling realised vol per product (std of ret_1 over
    ``window`` ticks). Used to cluster on vol co-movement, distinct from
    return co-movement.
    """
    series = {}
    for p, d in all_data.items():
        if d.px.empty or "ret_1" not in d.px.columns:
            continue
        s = d.px.set_index(["day", "timestamp"])["ret_1"]
        s = s[~s.index.duplicated(keep="first")]
        rv = s.rolling(window, min_periods=window // 2).std()
        series[p] = rv
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series)


# ---------------------------------------------------------------------------
# Features for clustering
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "rv_50_mean", "vol_of_vol", "vol_cluster_lag1",
    "hurst", "acf_ret1_lag1", "kurt_ret1",
    "spread_rel", "depth_l1_mean", "abs_obi_mean",
    "limit10_saturation",
    "adf_p_mid", "vr_k2", "vr_k5", "vr_k10", "half_life",
]


def _adf_p_safe(s: pd.Series) -> float:
    s = s.dropna()
    if len(s) < 50:
        return np.nan
    try:
        return float(adfuller(s.values, regression="c", autolag="AIC")[1])
    except Exception:
        return np.nan


def _half_life_ar1(s: pd.Series) -> float:
    """OU half-life from AR(1) on the price level: Δp_t = α + β·p_{t-1} + ε.

    half_life = -ln(2)/β when β ∈ (-1, 0); NaN otherwise (random-walk or
    explosive — half-life undefined / not mean-reverting).
    """
    s = s.dropna().astype(float).values
    if len(s) < 100:
        return np.nan
    try:
        x = s[:-1]
        dy = np.diff(s)
        beta = float(np.cov(x, dy, ddof=0)[0, 1] / np.var(x, ddof=0))
        if not (-1 < beta < 0):
            return np.nan
        return float(-np.log(2) / beta)
    except Exception:
        return np.nan


def product_features(all_data: dict[str, ProductData]) -> pd.DataFrame:
    rows = []
    for p, d in all_data.items():
        if d.px.empty:
            continue
        ret = d.px["ret_1"].dropna()
        abs_ret = ret.abs()
        rv50 = ret.rolling(50, min_periods=10).std().dropna()
        rv50_mean = float(rv50.mean()) if len(rv50) else np.nan
        vol_of_vol = float(rv50.std() / rv50.mean()) if len(rv50) and rv50.mean() > 0 else np.nan
        vol_cluster_lag1 = float(abs_ret.autocorr(1)) if len(abs_ret) > 1 else np.nan
        # Hurst on log-returns (cheap version: window 2000)
        try:
            try:
                from imc_stats.stats import hurst_rs
            except ModuleNotFoundError:
                from imc_commun.stats import hurst_rs
            log_ret = np.log(d.px["mid"]).diff().dropna().values
            H, _, _, _ = hurst_rs(log_ret, n_max=2000)
            hurst = float(H) if H == H else np.nan
        except Exception:
            hurst = np.nan
        acf_lag1 = float(ret.autocorr(1)) if len(ret) > 1 else np.nan
        kurt_ret1 = float(ret.kurt()) if len(ret) > 3 else np.nan
        spread_rel = float((d.px["spread"] / d.px["mid"]).mean()) if "spread" in d.px else np.nan
        depth_l1_mean = float(d.px["depth_l1"].mean()) if "depth_l1" in d.px else np.nan
        abs_obi_mean = float(d.px["obi_l1"].abs().mean()) if "obi_l1" in d.px else np.nan
        limit10_saturation = float(((d.px["bid_volume_1"] > 10) | (d.px["ask_volume_1"] > 10)).mean())

        adf_p_mid = _adf_p_safe(d.px["mid"])
        vr_k2, _ = variance_ratio(ret.values, 2)
        vr_k5, _ = variance_ratio(ret.values, 5)
        vr_k10, _ = variance_ratio(ret.values, 10)
        half_life = _half_life_ar1(d.px["mid"])

        rows.append({
            "product": p,
            "family": PRODUCT_TO_FAMILY.get(p, "?"),
            "rv_50_mean": rv50_mean,
            "vol_of_vol": vol_of_vol,
            "vol_cluster_lag1": vol_cluster_lag1,
            "hurst": hurst,
            "acf_ret1_lag1": acf_lag1,
            "kurt_ret1": kurt_ret1,
            "spread_rel": spread_rel,
            "depth_l1_mean": depth_l1_mean,
            "abs_obi_mean": abs_obi_mean,
            "limit10_saturation": limit10_saturation,
            "adf_p_mid": float(adf_p_mid) if adf_p_mid == adf_p_mid else np.nan,
            "vr_k2": float(vr_k2) if vr_k2 == vr_k2 else np.nan,
            "vr_k5": float(vr_k5) if vr_k5 == vr_k5 else np.nan,
            "vr_k10": float(vr_k10) if vr_k10 == vr_k10 else np.nan,
            "half_life": half_life,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def hierarchical_cluster_panel(
    panel: pd.DataFrame, method: str = "average"
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Correlation-distance hierarchical clustering on any aligned panel.

    Distance = 1 − |corr|. Caller chooses panel semantics: pass ``ret_1``
    panel for return co-movement, ``rolling_vol_panel`` output for vol
    co-movement.

    Returns (linkage_matrix, distance_matrix, ordered_products).
    """
    panel = panel.dropna(how="any")
    if panel.empty or panel.shape[1] < 2:
        return np.empty((0, 4)), np.empty((0, 0)), []
    corr = panel.corr().values
    dist = 1 - np.abs(corr)
    np.fill_diagonal(dist, 0)
    dist = (dist + dist.T) / 2
    cond = squareform(dist, checks=False)
    Z = linkage(cond, method=method)
    return Z, dist, list(panel.columns)


# Back-compat alias — older callers/notebooks may still import this name.
hierarchical_cluster_returns = hierarchical_cluster_panel


def pick_k_silhouette(
    features_std: np.ndarray,
    k_range: Iterable[int],
    random_state: int = 0,
    min_cluster_size: int = 1,
) -> tuple[int, list[tuple[int, float, int]]]:
    """Pick k by silhouette, but reject any k whose smallest cluster has fewer
    than ``min_cluster_size`` members (outlier-isolation guard).

    Returns (best_k, scores) where scores is list of (k, silhouette, smallest_cluster).
    """
    scores: list[tuple[int, float, int]] = []
    if features_std.shape[0] < 4:
        return -1, scores
    for k in k_range:
        if k >= features_std.shape[0]:
            continue
        try:
            km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
            labels = km.fit_predict(features_std)
            counts = np.bincount(labels, minlength=k)
            sil = float(silhouette_score(features_std, labels)) if len(set(labels)) > 1 else float("nan")
            scores.append((int(k), sil, int(counts.min())))
        except Exception:
            scores.append((int(k), float("nan"), 0))
    valid = [(k, s, sm) for k, s, sm in scores if pd.notna(s) and sm >= min_cluster_size]
    if not valid:
        return -1, scores
    best_k = max(valid, key=lambda t: t[1])[0]
    return best_k, scores


def assignments_from_linkage(Z: np.ndarray, k: int) -> np.ndarray:
    if Z.size == 0:
        return np.array([])
    return fcluster(Z, t=k, criterion="maxclust")


def assignments_from_features(
    features_std: np.ndarray, k: int, random_state: int = 0
) -> np.ndarray:
    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    return km.fit_predict(features_std)


def bootstrap_cluster_stability(
    panel: pd.DataFrame,
    reference_labels: dict[str, object],
    k: int,
    n_resamples: int = 30,
    frac: float = 0.7,
    method: str = "average",
    random_state: int = 0,
) -> dict:
    """Resample timestamps with replacement, recompute the correlation-distance
    hierarchical clustering at the same ``k``, and measure agreement with the
    reference assignment via Adjusted Rand Index.

    Directly addresses the round-5 overfit risk: with only 3 days of data, a
    cluster structure that doesn't survive timestamp resampling is an
    artefact, not a structural finding.

    Returns a dict with ``mean_ari``, ``std_ari``, ``frac_above_0p6``, and the
    raw ``ari_scores`` list. Empty dict if the panel can't support the test.
    """
    panel = panel.dropna(how="any")
    if panel.empty or panel.shape[1] < 2 or k < 2:
        return {}
    products = list(panel.columns)
    ref = np.array([reference_labels.get(p) for p in products], dtype=object)
    if any(v is None for v in ref):
        return {}
    rng = np.random.default_rng(random_state)
    n_rows = len(panel)
    sample_size = max(200, int(frac * n_rows))
    aris: list[float] = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n_rows, size=sample_size)
        sub = panel.iloc[idx]
        # Re-cluster on the bootstrap correlation matrix.
        try:
            corr = sub.corr().values
            dist = 1 - np.abs(corr)
            np.fill_diagonal(dist, 0)
            dist = (dist + dist.T) / 2
            cond = squareform(dist, checks=False)
            Z = linkage(cond, method=method)
            labels = fcluster(Z, t=k, criterion="maxclust")
        except Exception:
            continue
        aris.append(float(adjusted_rand_score(ref.astype(str), labels.astype(str))))
    if not aris:
        return {}
    arr = np.asarray(aris)
    return {
        "mean_ari": float(arr.mean()),
        "std_ari": float(arr.std()),
        "frac_above_0p6": float((arr >= 0.6).mean()),
        "n_resamples": int(len(aris)),
        "ari_scores": aris,
    }


# ---------------------------------------------------------------------------
# Cluster aggregates + rolling performance
# ---------------------------------------------------------------------------

def cluster_aggregate(panel: pd.DataFrame, mapping: dict[str, object]) -> pd.DataFrame:
    """Per-cluster mean-of-products series. Index = (day, timestamp).

    Cluster IDs are used directly as column names (so family names like
    ``GALAXY_SOUNDS`` flow through unchanged; numeric IDs get a ``C`` prefix).
    """
    if panel.empty:
        return pd.DataFrame()
    df = pd.DataFrame(index=panel.index)
    for cid in sorted(set(mapping.values()), key=lambda x: str(x)):
        members = [p for p, c in mapping.items() if c == cid and p in panel.columns]
        if not members:
            continue
        col = f"C{cid}" if isinstance(cid, (int, np.integer)) else str(cid)
        df[col] = panel[members].mean(axis=1)
    return df


def cluster_rolling_performance(
    cluster_agg: pd.DataFrame, window: int = 2000
) -> pd.DataFrame:
    """Rolling cumulative return per cluster + cross-sectional rank per row."""
    if cluster_agg.empty:
        return pd.DataFrame()
    cum = cluster_agg.fillna(0).rolling(window, min_periods=window // 2).sum()
    ranks = cum.rank(axis=1, ascending=False)
    out = cum.add_suffix("_cum").join(ranks.add_suffix("_rank"))
    return out


# ---------------------------------------------------------------------------
# Lead-lag detection between clusters
# ---------------------------------------------------------------------------

def cluster_leadlag_table(
    cluster_agg: pd.DataFrame, max_lag: int = 30
) -> pd.DataFrame:
    """For each ordered pair (i, j), corr(i_t, j_{t+lag}) at lag in [-L, L].

    Returns long-form dataframe with cols: leader, follower, lag, corr.
    """
    if cluster_agg.empty or cluster_agg.shape[1] < 2:
        return pd.DataFrame()
    cols = list(cluster_agg.columns)
    rows = []
    for a in cols:
        sa = cluster_agg[a]
        for b in cols:
            if a == b:
                continue
            sb = cluster_agg[b]
            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    continue
                # corr(sa_t, sb_{t+lag}). lag>0 => a leads b by `lag`.
                joined = pd.concat([sa, sb.shift(-lag)], axis=1).dropna()
                if len(joined) < 200:
                    continue
                rows.append({
                    "leader": a,
                    "follower": b,
                    "lag": int(lag),
                    "corr": float(joined.iloc[:, 0].corr(joined.iloc[:, 1])),
                })
    return pd.DataFrame(rows)


def best_leadlag_per_pair(table: pd.DataFrame) -> pd.DataFrame:
    """Pick optimal (lag, corr) for each ordered pair by max |corr|. Keeps only
    pairs with positive lag (the leader→follower direction)."""
    if table.empty:
        return pd.DataFrame()
    table = table.copy()
    table["abs_corr"] = table["corr"].abs()
    pos = table[table["lag"] > 0]
    if pos.empty:
        return pd.DataFrame()
    idx = pos.groupby(["leader", "follower"])["abs_corr"].idxmax()
    return pos.loc[idx].sort_values("abs_corr", ascending=False).reset_index(drop=True)


def basket_vs_leg_table(
    panel: pd.DataFrame,
    family_map: dict[str, list[str]] | None = None,
    *,
    lags: Iterable[int] = (1, 2, 3, 4, 5),
    loo: bool = True,
    leg_signal_panel: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Per-family basket(t-L) -> leg(t) Pearson corr.

    ``loo=True`` (default) builds the basket from the *other* legs in the
    family — required because each leg has its own lag-1 mean reversion that,
    if included in the basket, leaks into the cross-corr and inflates the
    apparent signal (audited 2026-04-29: PEBBLES, ROBOT, OXYGEN_SHAKE
    "basket signals" were 50-100% contamination under this path; SNACKPACK_PIS
    was the only signal that survived LOO).

    ``leg_signal_panel`` lets the *predictor* be a different signal than the
    *target* (e.g. basket built from order-flow imbalance, leg target = mid
    return). Defaults to using ``panel`` for both.

    Index of ``panel`` may be a (day, timestamp) MultiIndex; corrs are
    computed pooled across the index. For per-day stability, group externally.
    """
    if panel.empty:
        return pd.DataFrame()
    if family_map is None:
        family_map = FAMILIES
    src = panel if leg_signal_panel is None else leg_signal_panel
    rows = []
    for fam, members in family_map.items():
        members = [m for m in members if m in panel.columns and m in src.columns]
        if len(members) < 2:
            continue
        for leg in members:
            if loo:
                others = [m for m in members if m != leg]
                basket = src[others].mean(axis=1)
            else:
                basket = src[members].mean(axis=1)
            target = panel[leg]
            for L in lags:
                pair = pd.concat([basket.shift(L), target], axis=1).dropna()
                if len(pair) < 200:
                    continue
                rows.append({
                    "family": fam,
                    "leg": leg,
                    "lag": int(L),
                    "loo": bool(loo),
                    "n": int(len(pair)),
                    "corr": float(pair.iloc[:, 0].corr(pair.iloc[:, 1])),
                })
    return pd.DataFrame(rows)


def leadlag_stability(
    cluster_agg: pd.DataFrame, candidate_pairs: pd.DataFrame, gates: Gates,
) -> pd.DataFrame:
    """For each candidate (leader, follower, global_lag), recompute optimal lag
    in each of N rolling sub-windows. Stability = fraction of sub-windows
    whose argmax lag falls within ±2 of global_lag."""
    if cluster_agg.empty or candidate_pairs.empty:
        return pd.DataFrame()
    n = len(cluster_agg)
    if n < 1000:
        return pd.DataFrame()
    n_windows = gates.stability_n_windows
    win_size = n // n_windows
    rows = []
    for _, row in candidate_pairs.iterrows():
        a, b, glob_lag = row["leader"], row["follower"], int(row["lag"])
        per_win_lags: list[int] = []
        for w in range(n_windows):
            chunk = cluster_agg.iloc[w * win_size:(w + 1) * win_size]
            if len(chunk) < 200:
                continue
            best_l, best_c = None, 0.0
            for lag in range(1, gates.leadlag_max_lag + 1):
                joined = pd.concat([chunk[a], chunk[b].shift(-lag)], axis=1).dropna()
                if len(joined) < 100:
                    continue
                c = abs(float(joined.iloc[:, 0].corr(joined.iloc[:, 1])))
                if c > best_c:
                    best_c, best_l = c, lag
            if best_l is not None:
                per_win_lags.append(best_l)
        if not per_win_lags:
            continue
        match_count = sum(1 for l in per_win_lags if abs(l - glob_lag) <= 2)
        stability = match_count / len(per_win_lags)
        rows.append({
            "leader": a,
            "follower": b,
            "global_lag": glob_lag,
            "global_corr": float(row["corr"]),
            "n_windows_evaluated": len(per_win_lags),
            "stability": float(stability),
            "per_window_lags": ";".join(map(str, per_win_lags)),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["stability", "global_corr"], ascending=[False, False],
                           key=lambda c: c.abs() if c.name == "global_corr" else c).reset_index(drop=True)


def granger_confirm(
    cluster_agg: pd.DataFrame, leader: str, follower: str, max_lag: int = 5
) -> dict:
    if cluster_agg.empty:
        return {}
    sub = cluster_agg[[follower, leader]].dropna()
    if len(sub) < 1000:
        return {}
    try:
        res = grangercausalitytests(sub.values, maxlag=max_lag, verbose=False)
        ps = [float(res[l][0]["ssr_ftest"][1]) for l in range(1, max_lag + 1)]
        return {f"granger_p_lag{l}": p for l, p in zip(range(1, max_lag + 1), ps)}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_dendrogram(Z: np.ndarray, products: list[str], out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(14, 6))
    if Z.size == 0:
        ax.text(0.5, 0.5, "no clustering data", ha="center")
    else:
        dendrogram(Z, labels=products, ax=ax, leaf_rotation=90, leaf_font_size=7)
    ax.set_title("Returns correlation-distance hierarchical clustering")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def fig_silhouette_curve(scores: list[tuple[int, float, int]], out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    if not scores:
        ax.text(0.5, 0.5, "no silhouette scores", ha="center")
    else:
        ks = [s[0] for s in scores]
        ss = [s[1] for s in scores]
        sm = [s[2] for s in scores]
        ax.plot(ks, ss, "o-", color="steelblue", label="silhouette")
        ax.set_xlabel("k")
        ax.set_ylabel("silhouette", color="steelblue")
        for k, s, m in zip(ks, ss, sm):
            ax.annotate(f"min={m}", (k, s), fontsize=7, xytext=(0, 5),
                        textcoords="offset points", ha="center")
    ax.set_title("Silhouette score by k (min cluster size annotated)")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def fig_cluster_aggregate_series(cluster_agg: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    if cluster_agg.empty:
        ax.text(0.5, 0.5, "no aggregate data", ha="center")
    else:
        cum = cluster_agg.fillna(0).cumsum()
        for col in cum.columns:
            ax.plot(np.arange(len(cum)), cum[col].values, lw=0.7, label=col)
        ax.legend(fontsize=8, loc="best")
        ax.set_xlabel("tick")
        ax.set_ylabel("cumulative cluster return")
    ax.set_title("Cluster aggregate cumulative returns")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def fig_cluster_performance_rank(rolling: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    rank_cols = [c for c in rolling.columns if c.endswith("_rank")]
    if not rank_cols:
        ax.text(0.5, 0.5, "no rank data", ha="center")
    else:
        for col in rank_cols:
            ax.plot(np.arange(len(rolling)), rolling[col].values, lw=0.7, label=col.replace("_rank", ""))
        ax.invert_yaxis()
        ax.set_ylabel("rank (1 = best)")
        ax.legend(fontsize=8)
    ax.set_title("Rolling cluster performance rank")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def fig_leadlag_heatmap(best_pairs: pd.DataFrame, cluster_ids: list[str], out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5))
    if best_pairs.empty:
        ax.text(0.5, 0.5, "no lead-lag pairs", ha="center")
    else:
        n = len(cluster_ids)
        m = np.full((n, n), np.nan)
        idx = {c: i for i, c in enumerate(cluster_ids)}
        for _, r in best_pairs.iterrows():
            i = idx.get(r["leader"]); j = idx.get(r["follower"])
            if i is None or j is None:
                continue
            m[i, j] = r["corr"]
        vmax = max(0.05, np.nanmax(np.abs(m)) if np.isfinite(m).any() else 0.05)
        im = ax.imshow(m, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_xticks(np.arange(n)); ax.set_yticks(np.arange(n))
        ax.set_xticklabels(cluster_ids); ax.set_yticklabels(cluster_ids)
        for i in range(n):
            for j in range(n):
                if np.isfinite(m[i, j]):
                    ax.text(j, i, f"{m[i, j]:+.2f}", ha="center", va="center", fontsize=8)
        ax.set_xlabel("follower")
        ax.set_ylabel("leader")
        fig.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title("Best |corr| at optimal positive lag")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def fig_leadlag_stability(stable: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    if stable.empty:
        ax.text(0.5, 0.5, "no stable pairs", ha="center")
    else:
        labels = [f"{r['leader']}>{r['follower']}" for _, r in stable.iterrows()]
        ax.bar(np.arange(len(stable)), stable["stability"].values, color="seagreen")
        ax.set_xticks(np.arange(len(stable)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("stability")
        for i, (_, r) in enumerate(stable.iterrows()):
            ax.text(i, r["stability"], f"k={r['global_lag']}\nρ={r['global_corr']:+.2f}",
                    ha="center", va="bottom", fontsize=7)
    ax.set_title("Lead-lag pair stability (frac of windows matching global lag ±2)")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------

def cross_findings_markdown(
    gates: Gates,
    feats: pd.DataFrame,
    sil_scores: list[tuple[int, float, int]],
    best_k: int,
    best_sil: float,
    cluster_map: dict[str, object],
    kmeans_map: dict[str, int],
    rolling: pd.DataFrame,
    best_pairs: pd.DataFrame,
    stable: pd.DataFrame,
    granger_results: dict,
    skipped_stages: dict[str, str],
    bootstrap_summary: Optional[dict] = None,
) -> str:
    lines = ["# Cross-family findings", ""]
    lines.append("_Auto-generated. Logic gates listed at top; stages emitting "
                 "'skipped: <reason>' did not pass them._")
    lines.append("")
    lines.append("## Gates in effect")
    lines.append("```")
    for f in gates.__dataclass_fields__:
        lines.append(f"  {f} = {getattr(gates, f)}")
    lines.append("```")
    lines.append("")

    lines.append("## Primary cluster assignment: families")
    lines.append("")
    lines.append("Round-5's 10 named families × 5 products are used as the primary "
                 "cluster assignment for lead-lag analysis (10 well-balanced clusters, 5 each).")
    lines.append("")

    lines.append("## Validation: data-driven clustering on standardised features")
    if sil_scores:
        for k, s, sm in sil_scores:
            mark = "  <-- chosen" if k == best_k else ""
            lines.append(f"- k={k:>2}  silhouette={s:+.4f}  min_cluster={sm}{mark}")
        lines.append("")
    if "clustering_validation" in skipped_stages:
        lines.append(f"- _validation skipped: {skipped_stages['clustering_validation']}_")
    elif best_k > 0 and kmeans_map:
        lines.append(f"k-means chose k={best_k}, silhouette={best_sil:+.4f}")
        lines.append("")
        lines.append("k-means cluster membership (does the data agree with families?):")
        for cid in sorted(set(kmeans_map.values())):
            members = [p for p, c in kmeans_map.items() if c == cid]
            families_in = sorted({PRODUCT_TO_FAMILY.get(p, "?") for p in members})
            lines.append(f"- **C{cid}** ({len(members)} products, families {', '.join(families_in)})")
            # Compute purity: fraction of members in the dominant family
            from collections import Counter
            counter = Counter(PRODUCT_TO_FAMILY.get(p, "?") for p in members)
            dom_fam, dom_count = counter.most_common(1)[0]
            purity = dom_count / len(members) if members else 0
            lines.append(f"  - dominant family: {dom_fam} ({dom_count}/{len(members)}, purity={purity:.2f})")
    lines.append("")

    lines.append("## Bootstrap stability (timestamp resampling vs family assignment)")
    if "bootstrap" in skipped_stages and not bootstrap_summary:
        lines.append(f"- _skipped: {skipped_stages['bootstrap']}_")
    elif not bootstrap_summary:
        lines.append("- _no bootstrap result (panel empty or fewer than 4 products)_")
    else:
        lines.append(
            f"- mean ARI = **{bootstrap_summary['mean_ari']:.3f}** "
            f"(std {bootstrap_summary['std_ari']:.3f}, "
            f"frac >= 0.6: {bootstrap_summary['frac_above_0p6']:.2f}, "
            f"n={bootstrap_summary['n_resamples']})"
        )
        if "bootstrap" in skipped_stages:
            lines.append(f"- _gate fired: {skipped_stages['bootstrap']}_")
        else:
            lines.append(
                f"- mean ARI clears gate {gates.bootstrap_ari_min}; family "
                "structure survives timestamp resampling, lead-lag findings "
                "below are not driven by 3-day sample noise"
            )
    lines.append("")

    lines.append("## Cluster rolling-performance ranking")
    if "rolling" in skipped_stages:
        lines.append(f"- _skipped: {skipped_stages['rolling']}_")
    elif rolling.empty:
        lines.append("- _no rolling data_")
    else:
        rank_cols = [c for c in rolling.columns if c.endswith("_rank")]
        cum_cols = [c for c in rolling.columns if c.endswith("_cum")]
        if rank_cols:
            mean_rank = rolling[rank_cols].mean().sort_values()
            lines.append("Mean rank across the rolling window (1 = best):")
            for c, v in mean_rank.items():
                lines.append(f"- {c.replace('_rank','')} : {v:.2f}")
            lines.append("")
        if cum_cols:
            final_cum = rolling[cum_cols].iloc[-1].sort_values(ascending=False)
            lines.append("Final-tick cumulative aggregate return:")
            for c, v in final_cum.items():
                lines.append(f"- {c.replace('_cum','')} : {v:+.2f}")
    lines.append("")

    lines.append("## Cross-cluster lead-lag — global pairs (top by |corr|)")
    if "leadlag" in skipped_stages:
        lines.append(f"- _skipped: {skipped_stages['leadlag']}_")
    elif best_pairs.empty:
        lines.append("- _(no pairs cleared corr gate)_")
    else:
        for _, r in best_pairs.head(10).iterrows():
            lines.append(f"- {r['leader']} -> {r['follower']}  lag={int(r['lag'])}t  corr={r['corr']:+.3f}")
    lines.append("")

    lines.append("## Stable lead-lag pairs (cluster level)")
    if "stability" in skipped_stages:
        lines.append(f"- _skipped: {skipped_stages['stability']}_")
    elif stable.empty:
        lines.append("- _(no pair achieved stability >= "
                     f"{gates.stability_min:.2f})_")
    else:
        for _, r in stable.iterrows():
            lines.append(
                f"- **{r['leader']} -> {r['follower']}**  global_lag={int(r['global_lag'])}t  "
                f"corr={r['global_corr']:+.3f}  stability={r['stability']:.2f}  "
                f"per-window lags=[{r['per_window_lags']}]"
            )
    lines.append("")

    lines.append("## Granger confirmation on stable pairs")
    if not granger_results:
        lines.append("- _(none — either no stable pairs, or Granger gate not exercised)_")
    else:
        for key, ps in granger_results.items():
            if not ps:
                lines.append(f"- {key}: _(test failed / insufficient data)_")
                continue
            best = min((v for v in ps.values() if pd.notna(v)), default=np.nan)
            lines.append(f"- {key}: best p = {best:.4f}  [{ps}]")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def cross_family_report(
    out_dir: Path | str = Path("round5/reports/CROSS"),
    days: Sequence[int] = DEFAULT_DAYS,
    root: Path | str = DATASET_ROOT,
    gates: Optional[Gates] = None,
    verbose: bool = True,
) -> Path:
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    if gates is None:
        gates = Gates()
    skipped: dict[str, str] = {}

    if verbose:
        print(f"[CROSS] loading 50 products ...")
    all_data = load_all(days=days, root=root, verbose=verbose)

    # Features
    if verbose:
        print(f"[CROSS] feature extraction ...")
    feats = product_features(all_data)
    feats.to_csv(out_dir / "features.csv", index=False)

    # Returns panel for clustering on correlations
    panel = returns_panel(all_data, col="ret_1")
    if not panel.empty:
        panel.to_parquet(out_dir / "returns_panel.parquet") if False else None  # parquet optional; skip

    # Hierarchical clustering on returns (visualisation only)
    Z, dist, prods_ordered = hierarchical_cluster_panel(panel)
    fig_dendrogram(Z, prods_ordered, fig_dir / "dendrogram.png")

    # Second distance matrix: 1 − |corr(rolling_vol)| — captures vol
    # co-movement, which is structurally distinct from return co-movement
    # (two products can have uncorrelated returns but correlated volatility
    # regimes, and vice versa).
    vol_panel = rolling_vol_panel(all_data, window=50)
    Z_vol, dist_vol, prods_vol_ordered = hierarchical_cluster_panel(vol_panel)
    if Z_vol.size:
        fig_dendrogram(Z_vol, prods_vol_ordered, fig_dir / "dendrogram_vol.png")
        pd.DataFrame(dist_vol, index=prods_vol_ordered, columns=prods_vol_ordered).to_csv(
            out_dir / "rolling_vol_distance.csv"
        )

    # ---- Primary cluster assignment: families ----
    # Round-5 ships with 10 named families × 5 products. They are the natural
    # structural groups. Lead-lag analysis runs on per-family aggregates
    # regardless of whether data-driven clustering converges.
    family_ids = {p: PRODUCT_TO_FAMILY[p] for p in feats["product"].tolist()
                  if PRODUCT_TO_FAMILY.get(p)}
    pd.DataFrame({
        "product": list(family_ids),
        "family": [family_ids[p] for p in family_ids],
        "cluster": [family_ids[p] for p in family_ids],   # cluster_id == family
    }).to_csv(out_dir / "clusters.csv", index=False)
    cluster_map: dict[str, str] = family_ids

    # ---- Validation: data-driven clustering vs families ----
    feature_matrix = feats[FEATURE_COLS].fillna(feats[FEATURE_COLS].median(numeric_only=True))
    sil_scores: list[tuple[int, float, int]] = []
    best_k = -1
    best_sil = float("nan")
    kmeans_map: dict[str, int] = {}
    if feature_matrix.shape[0] >= 4:
        scaler = StandardScaler()
        X = scaler.fit_transform(feature_matrix.values)
        sil_range = range(gates.cluster_k_min, min(gates.cluster_k_max, feature_matrix.shape[0]))
        best_k, sil_scores = pick_k_silhouette(X, sil_range, min_cluster_size=gates.min_cluster_size)
        fig_silhouette_curve(sil_scores, fig_dir / "silhouette.png")
        if best_k > 0:
            best_sil = next(s for k, s, _ in sil_scores if k == best_k)
            if best_sil >= gates.silhouette_min:
                labels = assignments_from_features(X, best_k)
                kmeans_map = dict(zip(feats["product"].tolist(), labels.tolist()))
                pd.DataFrame({
                    "product": list(kmeans_map),
                    "family": [PRODUCT_TO_FAMILY[p] for p in kmeans_map],
                    "kmeans_cluster": [kmeans_map[p] for p in kmeans_map],
                }).to_csv(out_dir / "kmeans_validation.csv", index=False)
            else:
                skipped["clustering_validation"] = (
                    f"best silhouette {best_sil:.3f} < gate {gates.silhouette_min}; "
                    "k-means did not converge on usable structure (reporting families only)"
                )
        else:
            skipped["clustering_validation"] = (
                f"no k passed min_cluster_size>={gates.min_cluster_size} "
                "(reporting families only)"
            )

    # ---- Bootstrap cluster stability (overfit guard) ----
    # Re-cluster the returns panel from resampled timestamps; ARI vs the
    # family assignment tells us whether the families survive perturbation,
    # or whether the apparent grouping is noise from the 3-day sample.
    bootstrap_summary: dict = {}
    if not panel.empty and len(cluster_map) >= 4:
        n_clusters = len(set(cluster_map.values()))
        if verbose:
            print(f"[CROSS] bootstrap stability ({gates.bootstrap_n} resamples, k={n_clusters}) ...")
        bootstrap_summary = bootstrap_cluster_stability(
            panel, cluster_map, k=n_clusters,
            n_resamples=gates.bootstrap_n, frac=gates.bootstrap_frac,
        )
        if bootstrap_summary:
            ari_scores = bootstrap_summary.pop("ari_scores", [])
            pd.DataFrame({
                "resample": list(range(len(ari_scores))),
                "ari_vs_families": ari_scores,
            }).to_csv(out_dir / "bootstrap_ari.csv", index=False)
            if bootstrap_summary["mean_ari"] < gates.bootstrap_ari_min:
                skipped["bootstrap"] = (
                    f"mean ARI {bootstrap_summary['mean_ari']:.2f} < gate "
                    f"{gates.bootstrap_ari_min}; family structure is not "
                    "robust to timestamp resampling — treat lead-lag results "
                    "with caution"
                )

    # ---- Family aggregate series + rolling performance (always runs) ----
    cluster_agg = cluster_aggregate(panel, cluster_map)
    rolling = pd.DataFrame()
    if cluster_agg.empty or cluster_agg.shape[1] < 2:
        skipped["rolling"] = "family aggregate panel empty (no aligned data)"
    else:
        cluster_agg.to_csv(out_dir / "cluster_aggregate.csv")
        rolling = cluster_rolling_performance(cluster_agg, window=2000)
        rolling.to_csv(out_dir / "cluster_rolling_performance.csv")
        fig_cluster_aggregate_series(cluster_agg, fig_dir / "cluster_aggregate.png")
        fig_cluster_performance_rank(rolling, fig_dir / "cluster_rolling_rank.png")

    # Lead-lag
    best_pairs = pd.DataFrame()
    stable = pd.DataFrame()
    granger_results: dict[str, dict] = {}
    if cluster_agg.empty or cluster_agg.shape[1] < 2:
        skipped["leadlag"] = "fewer than 2 clusters; cross-cluster lead-lag undefined"
    else:
        if verbose:
            print(f"[CROSS] cross-cluster lead-lag (max_lag={gates.leadlag_max_lag}) ...")
        ll_table = cluster_leadlag_table(cluster_agg, max_lag=gates.leadlag_max_lag)
        ll_table.to_csv(out_dir / "leadlag_full.csv", index=False)
        best_pairs = best_leadlag_per_pair(ll_table)
        if not best_pairs.empty:
            best_pairs = best_pairs[best_pairs["abs_corr"] >= gates.leadlag_corr_min].reset_index(drop=True)
        if best_pairs.empty:
            skipped["leadlag"] = (
                f"no pair cleared |corr| >= {gates.leadlag_corr_min} at any positive lag"
            )
        else:
            best_pairs.to_csv(out_dir / "leadlag_best_pairs.csv", index=False)
            fig_leadlag_heatmap(best_pairs, list(cluster_agg.columns),
                                fig_dir / "leadlag_heatmap.png")

            if verbose:
                print(f"[CROSS] lead-lag stability check ({gates.stability_n_windows} windows) ...")
            stable = leadlag_stability(cluster_agg, best_pairs, gates)
            stable = stable[stable["stability"] >= gates.stability_min].reset_index(drop=True) if not stable.empty else stable
            if stable.empty:
                skipped["stability"] = (
                    f"no pair achieved stability >= {gates.stability_min}"
                )
            else:
                stable.to_csv(out_dir / "leadlag_stable_pairs.csv", index=False)
                fig_leadlag_stability(stable, fig_dir / "leadlag_stability.png")
                if verbose:
                    print(f"[CROSS] Granger confirmation on {len(stable)} stable pair(s) ...")
                for _, r in stable.iterrows():
                    key = f"{r['leader']}->{r['follower']}"
                    granger_results[key] = granger_confirm(
                        cluster_agg, r["leader"], r["follower"], max_lag=gates.granger_max_lag
                    )
                if granger_results:
                    rows = []
                    for k, ps in granger_results.items():
                        row = {"pair": k}
                        row.update(ps)
                        rows.append(row)
                    pd.DataFrame(rows).to_csv(out_dir / "granger_tests.csv", index=False)

    md = cross_findings_markdown(
        gates, feats, sil_scores, best_k, best_sil,
        cluster_map, kmeans_map, rolling, best_pairs, stable, granger_results, skipped,
        bootstrap_summary=bootstrap_summary,
    )
    (out_dir / "cross_findings.md").write_text(md, encoding="utf-8")

    if verbose:
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print(f"[CROSS] done -> {out_dir}")
        print()
        print(md)

    return out_dir
