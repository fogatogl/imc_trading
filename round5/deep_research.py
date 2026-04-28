"""Conditional deep-dive research for round-5 families.

Always-on:
  ``detect_triggers`` + ``write_triggers_report`` — cheap; lists products that
  cross the looser deep-dive thresholds and pairs worth examining further.

Opt-in (``family_report(deep=True)`` or CLI ``--deep``):
  ``run_deep_research`` runs three kinds of deep dives on the auto-triggered
  candidates:

    * ``mr_deep_dive``    — OU fit, half-life, threshold-PnL curve,
                            vol-regime split, anchor-sensitivity.
    * ``trend_deep_dive`` — momentum decay, window×horizon IC grid,
                            threshold-PnL curve, vol-regime split.
    * ``pairs_deep_dive`` — β estimation, residual stationarity, rolling β,
                            residual threshold-PnL curve.

Each dive emits a markdown summary + a small figure set under
``round5/reports/<FAMILY>/deep/``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from .research_lib import (
    HORIZONS,
    POSITION_LIMIT,
    ProductData,
    _aligned_panel,
    _save,
)

# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Triggers:
    mr: list[str]               # products
    trending: list[str]         # products
    pairs: list[tuple[str, str]]  # (a, b)


def detect_triggers(
    stats_df: pd.DataFrame,
    ic_by_product: dict[str, pd.DataFrame],
    corr_mid: pd.DataFrame,
    corr_ret: pd.DataFrame,
    coint_df: pd.DataFrame,
) -> Triggers:
    """Majority-vote trigger detection (>=2 conditions per category).

    MR and Trending are mutually exclusive: if a product fires both, it
    lands in whichever has more votes (tie -> MR). Pair candidates are
    orthogonal — a product can show up in pairs *and* in MR/Trending.
    """

    def ic_at(p: str, signal: str, h: int) -> float:
        df = ic_by_product.get(p)
        if df is None or df.empty:
            return np.nan
        df2 = df.set_index("signal")
        col = f"ic_h{h}"
        if signal not in df2.index or col not in df2.columns:
            return np.nan
        v = df2.loc[signal, col]
        return float(v) if pd.notna(v) else np.nan

    mr: list[str] = []
    trending: list[str] = []
    if not stats_df.empty:
        for _, r in stats_df.iterrows():
            p = r["product"]

            # MR votes (loosened thresholds to match archetype gates).
            mr_votes = 0
            if pd.notna(r.get("vr_k5")) and r["vr_k5"] < 0.97:
                mr_votes += 1
            if pd.notna(r.get("hurst")) and r["hurst"] < 0.50:
                mr_votes += 1
            if pd.notna(r.get("acf_ret1_lag1")) and r["acf_ret1_lag1"] < -0.01:
                mr_votes += 1
            # MR IC: positive sign required (MR strategy needs forward-
            # return correlation in the direction of mean-reversion).
            ic_mr_z = ic_at(p, "neg_zscore_mid_50", 10)
            if pd.notna(ic_mr_z) and ic_mr_z > 0.02:
                mr_votes += 1

            # Trending votes (loosened too).
            tr_votes = 0
            if pd.notna(r.get("vr_k5")) and r["vr_k5"] > 1.005:
                tr_votes += 1
            if pd.notna(r.get("hurst")) and r["hurst"] > 0.51:
                tr_votes += 1
            if pd.notna(r.get("acf_ret1_lag1")) and r["acf_ret1_lag1"] > 0.01:
                tr_votes += 1
            # MOM IC: positive sign required (trending = past up predicts
            # future up). Negative IC at long horizons signals contrarian
            # behaviour, not momentum.
            ic_mom = ic_at(p, "momentum_10", 10)
            if pd.notna(ic_mom) and ic_mom > 0.02:
                tr_votes += 1

            # Discriminant assignment: a product cannot be both MR and trending.
            if mr_votes >= 2 and tr_votes >= 2:
                if mr_votes >= tr_votes:
                    mr.append(p)
                else:
                    trending.append(p)
            elif mr_votes >= 2:
                mr.append(p)
            elif tr_votes >= 2:
                trending.append(p)

    pair_candidates: list[tuple[str, str, float]] = []
    if not corr_mid.empty:
        prods = list(corr_mid.columns)
        coint_lookup: dict[tuple[str, str], float] = {}
        if not coint_df.empty:
            for _, r in coint_df.iterrows():
                coint_lookup[(r["a"], r["b"])] = float(r["coint_p"])
                coint_lookup[(r["b"], r["a"])] = float(r["coint_p"])

        for i, a in enumerate(prods):
            for b in prods[i + 1:]:
                votes = 0
                cm_ab = corr_mid.loc[a, b] if a in corr_mid.index else np.nan
                cr_ab = corr_ret.loc[a, b] if (not corr_ret.empty and a in corr_ret.index) else np.nan
                cp_ab = coint_lookup.get((a, b), np.nan)
                if pd.notna(cm_ab) and abs(cm_ab) > 0.5:
                    votes += 1
                if pd.notna(cp_ab) and cp_ab < 0.10:
                    votes += 1
                if pd.notna(cr_ab) and abs(cr_ab) > 0.3:
                    votes += 1
                if votes >= 2:
                    score = (
                        (abs(cm_ab) if pd.notna(cm_ab) else 0)
                        + (1 - cp_ab if pd.notna(cp_ab) else 0)
                        + (abs(cr_ab) if pd.notna(cr_ab) else 0)
                    )
                    pair_candidates.append((a, b, score))

    pair_candidates.sort(key=lambda x: x[2], reverse=True)
    pairs = [(a, b) for a, b, _ in pair_candidates[:3]]  # cap at top-3

    return Triggers(mr=mr, trending=trending, pairs=pairs)


def write_triggers_report(triggers: Triggers, out_path: Path) -> None:
    lines = ["# Deep-dive triggers", ""]
    lines.append(
        "_Auto-generated. Lists products/pairs that cross the looser "
        "deep-dive thresholds (>=2 votes per category). Run with "
        "`--deep` to execute the dives._"
    )
    lines.append("")

    lines.append("## Mean-reversion candidates")
    lines.extend([f"- {p}" for p in triggers.mr] or ["- _(none)_"])
    lines.append("")

    lines.append("## Trending candidates")
    lines.extend([f"- {p}" for p in triggers.trending] or ["- _(none)_"])
    lines.append("")

    lines.append("## Pair-trading candidates (top 3 by combined score)")
    lines.extend([f"- {a} <-> {b}" for a, b in triggers.pairs] or ["- _(none)_"])
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# OU fit + threshold sim helpers (shared by MR / pairs)
# ---------------------------------------------------------------------------

def fit_ou(series: pd.Series) -> dict:
    """AR(1) discrete approximation of OU: dX = κ(θ − X)dt + σ dW.

    Estimates via OLS on Δx_t = α + β·x_t + ε. Returns kappa, theta, sigma
    (per-tick), half_life_ticks (np.inf if non-stationary)."""
    s = series.dropna().values
    if len(s) < 100:
        return {"kappa": np.nan, "theta": np.nan, "sigma": np.nan, "half_life_ticks": np.nan, "r2": np.nan}
    dx = np.diff(s)
    x = s[:-1]
    X = np.column_stack([np.ones_like(x), x])
    coefs, *_ = np.linalg.lstsq(X, dx, rcond=None)
    alpha, beta = coefs
    resid = dx - X @ coefs
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((dx - dx.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    if beta >= 0:  # not mean-reverting; return marker values
        return {
            "kappa": float(-beta), "theta": np.nan,
            "sigma": float(resid.std(ddof=1)), "half_life_ticks": np.inf, "r2": float(r2),
        }
    kappa = -float(beta)
    theta = -float(alpha) / float(beta)
    sigma = float(resid.std(ddof=1))
    half_life = float(np.log(2) / kappa) if kappa > 0 else np.inf
    return {"kappa": kappa, "theta": theta, "sigma": sigma, "half_life_ticks": half_life, "r2": float(r2)}


def threshold_pnl_curve(
    z: pd.Series,
    fwd_ret: pd.Series,
    thresholds: Sequence[float] = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0),
    fade: bool = True,
) -> pd.DataFrame:
    """Simulate a contemporaneous-taker strategy at each threshold.

    fade=True: position = -sign(z) when |z| > thresh (fade the move; MR taker).
    fade=False: position = +sign(z) (follow; momentum taker).
    """
    aligned = pd.concat([z.rename("z"), fwd_ret.rename("ret")], axis=1).dropna()
    if len(aligned) < 200:
        return pd.DataFrame()
    rows = []
    for thresh in thresholds:
        sign = np.sign(aligned["z"].values)
        active = np.abs(aligned["z"].values) > thresh
        pos = (-sign if fade else sign) * active
        pnl = pos * aligned["ret"].values
        n_trades = int((np.diff(pos, prepend=0) != 0).sum())
        rows.append({
            "threshold": float(thresh),
            "n_active": int(active.sum()),
            "frac_active": float(active.mean()),
            "n_trades": n_trades,
            "pnl_total": float(pnl.sum()),
            "pnl_mean": float(pnl.mean()),
            "pnl_std": float(pnl.std()),
            "sharpe": float(pnl.mean() / pnl.std()) if pnl.std() > 0 else np.nan,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mean-reversion deep dive
# ---------------------------------------------------------------------------

def mr_deep_dive(d: ProductData, out_dir: Path) -> Path:
    out = out_dir / f"mr_{d.product}"
    out.mkdir(parents=True, exist_ok=True)

    px = d.px
    mid = px["mid"]
    z = -px["mid"]  # placeholder, replaced below
    z = (mid - mid.rolling(50, min_periods=20).mean()) / mid.rolling(50, min_periods=20).std().replace(0, np.nan)
    fwd_ret = px["fwd_10"] if "fwd_10" in px.columns else mid.shift(-10) - mid

    # 1. OU fit (full pooled + per day)
    ou_full = fit_ou(mid)
    per_day_rows = []
    for day, sub in px.groupby("day"):
        ou_d = fit_ou(sub["mid"])
        ou_d["day"] = int(day)
        per_day_rows.append(ou_d)
    per_day = pd.DataFrame(per_day_rows)

    # 2. Threshold-PnL curve (fade)
    curve = threshold_pnl_curve(z, fwd_ret, fade=True)

    # 3. Vol-regime split: low/mid/high std_50 buckets, PnL at best threshold
    std_50 = px["std_50"]
    regime_pnls: list[dict] = []
    if not curve.empty and std_50.notna().sum() > 100:
        best_t = float(curve.sort_values("sharpe", ascending=False)["threshold"].iloc[0])
        sign = np.sign(z.values)
        active = np.abs(z.values) > best_t
        pos = -sign * active
        pnl = pos * fwd_ret.values
        # Tertiles of std_50
        q = std_50.dropna().quantile([1 / 3, 2 / 3]).values
        bands = np.where(std_50.values <= q[0], "low",
                         np.where(std_50.values <= q[1], "mid", "high"))
        df = pd.DataFrame({"pnl": pnl, "band": bands}).dropna()
        for band in ["low", "mid", "high"]:
            sub = df[df["band"] == band]
            regime_pnls.append({
                "regime": band,
                "n": int(len(sub)),
                "pnl_total": float(sub["pnl"].sum()) if len(sub) else 0.0,
                "pnl_mean": float(sub["pnl"].mean()) if len(sub) else np.nan,
                "sharpe": float(sub["pnl"].mean() / sub["pnl"].std()) if len(sub) and sub["pnl"].std() > 0 else np.nan,
            })

    # 4. Anchor sensitivity — dev under three anchors
    anchors = {
        "rolling_50": mid.rolling(50, min_periods=20).mean(),
        "day_mean": px.groupby("day")["mid"].transform("mean"),
        "pooled_mean": pd.Series(mid.mean(), index=mid.index),
    }
    anchor_summary = pd.DataFrame({
        name: {
            "dev_mean": float((mid - a).mean()),
            "dev_std": float((mid - a).std()),
            "adf_p": _safe_adf(mid - a),
        } for name, a in anchors.items()
    }).T

    # ---------- Write CSVs / Markdown ----------
    pd.DataFrame([ou_full]).to_csv(out / "ou_full.csv", index=False)
    per_day.to_csv(out / "ou_per_day.csv", index=False)
    if not curve.empty:
        curve.to_csv(out / "threshold_curve.csv", index=False)
    pd.DataFrame(regime_pnls).to_csv(out / "vol_regime_pnl.csv", index=False)
    anchor_summary.to_csv(out / "anchor_summary.csv")

    md = _mr_markdown(d.product, ou_full, per_day, curve, regime_pnls, anchor_summary)
    (out / "REPORT.md").write_text(md, encoding="utf-8")

    # ---------- Figures ----------
    _fig_ou(d.product, mid, ou_full, out / "ou_fit.png")
    if not curve.empty:
        _fig_threshold_curve(d.product, curve, out / "threshold_curve.png", title_tag="MR fade taker")
    _fig_vol_regime(d.product, regime_pnls, out / "vol_regime_pnl.png")
    _fig_anchor_compare(d.product, mid, anchors, out / "anchor_compare.png")

    return out


def _mr_markdown(product, ou_full, per_day, curve, regime_pnls, anchor_summary) -> str:
    lines = [f"# {product} — Mean-Reversion Deep Dive", ""]
    lines.append("## OU fit (pooled)")
    lines.append("")
    lines.append(f"- κ = {ou_full['kappa']:.6f}  (per-tick mean-reversion rate)")
    lines.append(f"- θ = {ou_full['theta']:.2f}  (long-run mean)")
    lines.append(f"- σ = {ou_full['sigma']:.3f}  (innovation std)")
    lines.append(f"- half-life = {ou_full['half_life_ticks']:.1f} ticks")
    lines.append(f"- AR(1) R² = {ou_full['r2']:.4f}")
    lines.append("")
    lines.append("## OU fit (per day)")
    lines.append("")
    lines.append(per_day.round(4).to_string(index=False))
    lines.append("")
    if not curve.empty:
        lines.append("## Threshold-PnL curve (MR fade taker on rolling-50 z-score)")
        lines.append("")
        lines.append(curve.round(4).to_string(index=False))
        lines.append("")
    if regime_pnls:
        lines.append("## Vol-regime decomposition (PnL at best Sharpe threshold)")
        lines.append("")
        lines.append(pd.DataFrame(regime_pnls).round(4).to_string(index=False))
        lines.append("")
    lines.append("## Anchor sensitivity")
    lines.append("")
    lines.append(anchor_summary.round(4).to_string())
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trending deep dive
# ---------------------------------------------------------------------------

def trend_deep_dive(d: ProductData, out_dir: Path) -> Path:
    out = out_dir / f"trend_{d.product}"
    out.mkdir(parents=True, exist_ok=True)

    px = d.px
    mid = px["mid"]
    ret1 = mid.diff()

    # 1. Momentum decay: corr(ret_t, ret_{t+k})
    decay_lags = list(range(1, 201))
    decay = []
    for k in decay_lags:
        v = ret1.autocorr(k)
        decay.append({"lag": k, "ac": float(v) if pd.notna(v) else np.nan})
    decay_df = pd.DataFrame(decay)

    # 2. Window x horizon IC grid
    windows = [5, 10, 20, 50, 100]
    horizons = [1, 5, 10, 50, 100, 500]
    grid = pd.DataFrame(index=windows, columns=horizons, dtype=float)
    grid.index.name = "window"
    grid.columns.name = "horizon"
    for w in windows:
        signal = mid - mid.shift(w)
        for h in horizons:
            fwd = mid.shift(-h) - mid
            joined = pd.concat([signal, fwd], axis=1).dropna()
            if len(joined) < 200:
                continue
            grid.loc[w, h] = float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))

    # 3. Threshold-PnL on best (window, horizon) combo
    best_curve = pd.DataFrame()
    best_combo: tuple[Optional[int], Optional[int]] = (None, None)
    if grid.notna().any().any():
        flat = grid.stack().abs()
        if not flat.empty:
            best_w, best_h = flat.idxmax()
            best_combo = (int(best_w), int(best_h))
            signal = mid - mid.shift(best_w)
            z_signal = (signal - signal.rolling(200, min_periods=50).mean()) / signal.rolling(200, min_periods=50).std().replace(0, np.nan)
            fwd = mid.shift(-best_h) - mid
            best_curve = threshold_pnl_curve(z_signal, fwd, fade=False)
            best_curve.insert(0, "window", best_w)
            best_curve.insert(1, "horizon", best_h)

    # 4. Vol-regime decomposition
    regime_pnls: list[dict] = []
    if not best_curve.empty and px["std_50"].notna().sum() > 100:
        best_t = float(best_curve.sort_values("sharpe", ascending=False)["threshold"].iloc[0])
        signal = mid - mid.shift(best_combo[0])
        z_signal = (signal - signal.rolling(200, min_periods=50).mean()) / signal.rolling(200, min_periods=50).std().replace(0, np.nan)
        fwd = mid.shift(-best_combo[1]) - mid
        sign = np.sign(z_signal.values)
        active = np.abs(z_signal.values) > best_t
        pos = sign * active   # follow
        pnl = pos * fwd.values
        std_50 = px["std_50"].values
        q = pd.Series(std_50).dropna().quantile([1 / 3, 2 / 3]).values
        bands = np.where(std_50 <= q[0], "low",
                         np.where(std_50 <= q[1], "mid", "high"))
        df = pd.DataFrame({"pnl": pnl, "band": bands}).dropna()
        for band in ["low", "mid", "high"]:
            sub = df[df["band"] == band]
            regime_pnls.append({
                "regime": band,
                "n": int(len(sub)),
                "pnl_total": float(sub["pnl"].sum()) if len(sub) else 0.0,
                "pnl_mean": float(sub["pnl"].mean()) if len(sub) else np.nan,
                "sharpe": float(sub["pnl"].mean() / sub["pnl"].std()) if len(sub) and sub["pnl"].std() > 0 else np.nan,
            })

    # ---------- Write artifacts ----------
    decay_df.to_csv(out / "momentum_decay.csv", index=False)
    grid.to_csv(out / "momentum_grid.csv")
    if not best_curve.empty:
        best_curve.to_csv(out / "best_threshold_curve.csv", index=False)
    pd.DataFrame(regime_pnls).to_csv(out / "vol_regime_pnl.csv", index=False)

    md = _trend_markdown(d.product, decay_df, grid, best_combo, best_curve, regime_pnls)
    (out / "REPORT.md").write_text(md, encoding="utf-8")

    # ---------- Figures ----------
    _fig_momentum_decay(d.product, decay_df, out / "momentum_decay.png")
    _fig_momentum_grid(d.product, grid, out / "momentum_grid.png")
    if not best_curve.empty:
        _fig_threshold_curve(
            d.product, best_curve, out / "best_threshold_curve.png",
            title_tag=f"Momentum follow (w={best_combo[0]}, h={best_combo[1]})",
        )
    _fig_vol_regime(d.product, regime_pnls, out / "vol_regime_pnl.png")

    return out


def _trend_markdown(product, decay_df, grid, best_combo, best_curve, regime_pnls) -> str:
    lines = [f"# {product} — Trending Deep Dive", ""]
    lines.append("## Momentum decay (autocorrelation of ret_1 by lag)")
    lines.append("")
    head = decay_df.head(20).round(4)
    lines.append(head.to_string(index=False))
    lines.append(f"... ({len(decay_df)} lags total — see momentum_decay.csv)")
    lines.append("")
    lines.append("## Window × horizon IC grid (corr(mid - mid.shift(w), fwd_h))")
    lines.append("")
    lines.append(grid.round(4).to_string())
    lines.append("")
    if best_combo[0] is not None:
        lines.append(f"Best (window, horizon) by |IC| = ({best_combo[0]}, {best_combo[1]})")
        lines.append("")
    if not best_curve.empty:
        lines.append("## Threshold-PnL curve at best combo (momentum follow)")
        lines.append("")
        lines.append(best_curve.round(4).to_string(index=False))
        lines.append("")
    if regime_pnls:
        lines.append("## Vol-regime decomposition")
        lines.append("")
        lines.append(pd.DataFrame(regime_pnls).round(4).to_string(index=False))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pairs deep dive
# ---------------------------------------------------------------------------

def pairs_deep_dive(family_data: dict[str, ProductData], a: str, b: str, out_dir: Path) -> Path:
    out = out_dir / f"pair_{a}__{b}"
    out.mkdir(parents=True, exist_ok=True)

    panel = _aligned_panel(family_data, "mid").dropna()
    if a not in panel or b not in panel:
        (out / "REPORT.md").write_text(f"# {a} ↔ {b} — no aligned panel\n", encoding="utf-8")
        return out
    sub = panel[[a, b]].copy()

    # 1. β / R² on full panel
    x = sub[b].values
    y = sub[a].values
    X = np.column_stack([np.ones_like(x), x])
    coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha_, beta_ = float(coefs[0]), float(coefs[1])
    resid_full = y - X @ coefs
    ss_res = float(np.sum(resid_full ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    fit = {"alpha": alpha_, "beta": beta_, "r2": float(r2)}

    # 2. Residual stationarity + half-life
    resid_series = pd.Series(resid_full, index=sub.index)
    adf_p = _safe_adf(resid_series)
    ou = fit_ou(resid_series)
    fit.update({"resid_adf_p": adf_p, "resid_half_life_ticks": ou["half_life_ticks"]})

    # 3. Rolling β stability
    window = max(2000, len(sub) // 6)
    rb = []
    arr_x = sub[b].values
    arr_y = sub[a].values
    for i in range(window, len(sub), max(1, window // 4)):
        xs = arr_x[i - window:i]
        ys = arr_y[i - window:i]
        Xw = np.column_stack([np.ones_like(xs), xs])
        cw, *_ = np.linalg.lstsq(Xw, ys, rcond=None)
        rb.append({"end_idx": int(i), "alpha": float(cw[0]), "beta": float(cw[1])})
    rolling_beta = pd.DataFrame(rb)

    # 4. Threshold-PnL on residual z-score (β-hedged: long A, short β·B)
    z_resid = (resid_series - resid_series.rolling(200, min_periods=50).mean()) / resid_series.rolling(200, min_periods=50).std().replace(0, np.nan)
    # PnL of long-A short-β·B per tick = Δresid (the residual itself moves toward 0)
    # so naive MR fade taker on z_resid against -Δresid (next-tick) approximates pair PnL
    fwd_resid = -resid_series.shift(-1).sub(resid_series)
    # Note: when |z_resid|>thresh and we fade (pos = -sign(z)), pnl = pos * (resid_t+1 - resid_t)
    # Equivalent to following the spread reversion.
    curve = threshold_pnl_curve(z_resid, resid_series.shift(-1) - resid_series, fade=True)

    # ---------- Write artifacts ----------
    pd.DataFrame([fit]).to_csv(out / "fit.csv", index=False)
    if not rolling_beta.empty:
        rolling_beta.to_csv(out / "rolling_beta.csv", index=False)
    if not curve.empty:
        curve.to_csv(out / "threshold_curve.csv", index=False)

    md = _pairs_markdown(a, b, fit, rolling_beta, curve)
    (out / "REPORT.md").write_text(md, encoding="utf-8")

    # ---------- Figures ----------
    _fig_pair_regression(a, b, sub, alpha_, beta_, out / "regression.png")
    _fig_pair_residuals(a, b, resid_series, out / "residuals.png")
    if not rolling_beta.empty:
        _fig_rolling_beta(a, b, rolling_beta, out / "rolling_beta.png")
    if not curve.empty:
        _fig_threshold_curve(f"{a}__{b}", curve, out / "threshold_curve.png", title_tag="Pair MR fade")

    return out


def _pairs_markdown(a, b, fit, rolling_beta, curve) -> str:
    lines = [f"# {a} <-> {b} — Pairs Deep Dive", ""]
    lines.append("## OLS fit (full panel)")
    lines.append("")
    lines.append(f"- A = {a}    B = {b}")
    lines.append(f"- A_t ≈ α + β·B_t")
    lines.append(f"- α = {fit['alpha']:.3f}")
    lines.append(f"- β = {fit['beta']:.4f}")
    lines.append(f"- R² = {fit['r2']:.4f}")
    lines.append(f"- residual ADF p = {fit.get('resid_adf_p', float('nan')):.4f}")
    hl = fit.get("resid_half_life_ticks", float("nan"))
    lines.append(f"- residual MR half-life = {hl:.1f} ticks" if np.isfinite(hl) else "- residual MR half-life = inf (non-MR)")
    lines.append("")
    if not rolling_beta.empty:
        lines.append("## Rolling β stability")
        lines.append("")
        lines.append(rolling_beta.round(4).to_string(index=False))
        lines.append("")
    if not curve.empty:
        lines.append("## Threshold-PnL curve on residual z-score (MR fade)")
        lines.append("")
        lines.append(curve.round(4).to_string(index=False))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def _fig_ou(product, mid, ou, out_path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(np.arange(len(mid)), mid.values, color="black", lw=0.4)
    if pd.notna(ou.get("theta")):
        axes[0].axhline(ou["theta"], color="red", ls="--", lw=0.7, label=f"θ={ou['theta']:.2f}")
        axes[0].legend()
    axes[0].set_title(f"{product} — mid + OU long-run mean")
    axes[0].set_xlabel("tick")

    dev = (mid - ou.get("theta", mid.mean())).dropna()
    axes[1].hist(dev, bins=60, color="steelblue", alpha=0.7, density=True)
    if pd.notna(ou.get("sigma")) and ou["sigma"] > 0 and pd.notna(ou.get("kappa")) and ou["kappa"] > 0:
        # Stationary OU std = sigma / sqrt(2 kappa)
        std_inf = ou["sigma"] / np.sqrt(2 * ou["kappa"])
        x = np.linspace(dev.min(), dev.max(), 200)
        pdf = np.exp(-x ** 2 / (2 * std_inf ** 2)) / np.sqrt(2 * np.pi * std_inf ** 2)
        axes[1].plot(x, pdf, color="red", lw=1, label=f"OU stationary  σ∞={std_inf:.2f}")
        axes[1].legend()
    hl = ou.get("half_life_ticks", float("nan"))
    title_tail = f"  half-life={hl:.0f}t" if np.isfinite(hl) else "  half-life=inf"
    axes[1].set_title(f"dev hist{title_tail}")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_threshold_curve(product, curve: pd.DataFrame, out_path: Path, title_tag: str = "") -> Path:
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(curve["threshold"], curve["pnl_total"], "o-", color="steelblue", label="pnl_total")
    ax1.set_xlabel("z threshold")
    ax1.set_ylabel("pnl_total", color="steelblue")
    ax2 = ax1.twinx()
    ax2.plot(curve["threshold"], curve["sharpe"], "s--", color="firebrick", label="sharpe")
    ax2.set_ylabel("sharpe (per-tick)", color="firebrick")
    ax1.set_title(f"{product} — threshold curve {title_tag}")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_vol_regime(product, regime_pnls, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    if not regime_pnls:
        ax.text(0.5, 0.5, "no regime data", ha="center")
    else:
        df = pd.DataFrame(regime_pnls)
        x = np.arange(len(df))
        ax.bar(x, df["pnl_total"].values, color="seagreen")
        ax.set_xticks(x)
        ax.set_xticklabels(df["regime"].astype(str).tolist())
        ax.set_ylabel("pnl_total")
        for i, sh in enumerate(df["sharpe"].values):
            ax.text(i, df["pnl_total"].values[i], f"sh={sh:.3f}" if pd.notna(sh) else "sh=NA",
                    ha="center", va="bottom", fontsize=8)
    ax.set_title(f"{product} — vol-regime PnL")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_anchor_compare(product, mid, anchors, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4))
    for name, a in anchors.items():
        dev = (mid - a).dropna()
        ax.plot(np.arange(len(dev)), dev.values, lw=0.4, label=f"dev vs {name}  σ={dev.std():.2f}")
    ax.axhline(0, color="black", lw=0.4)
    ax.legend(fontsize=8)
    ax.set_title(f"{product} — anchor sensitivity")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_momentum_decay(product, decay_df: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.bar(decay_df["lag"].values, decay_df["ac"].values, color="steelblue", width=0.8)
    n_eff = max(1, decay_df["lag"].max() * 100)
    band = 1.96 / np.sqrt(n_eff)  # rough
    ax.axhline(band, color="grey", ls="--", lw=0.5)
    ax.axhline(-band, color="grey", ls="--", lw=0.5)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(f"{product} — momentum decay (ret_1 ACF)")
    ax.set_xlabel("lag")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_momentum_grid(product, grid: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    if grid.empty or not grid.notna().any().any():
        ax.text(0.5, 0.5, "no data", ha="center")
    else:
        arr = grid.values.astype(float)
        vmax = max(0.05, np.nanmax(np.abs(arr)))
        im = ax.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(grid.shape[1]))
        ax.set_xticklabels([str(c) for c in grid.columns])
        ax.set_yticks(np.arange(grid.shape[0]))
        ax.set_yticklabels([str(i) for i in grid.index])
        ax.set_xlabel("horizon")
        ax.set_ylabel("window")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                v = arr[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=7,
                            color="white" if abs(v) > vmax * 0.5 else "black")
        fig.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title(f"{product} — momentum window×horizon IC")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_pair_regression(a, b, sub: pd.DataFrame, alpha_, beta_, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 5))
    # Subsample for plotting to keep PNG light
    n = len(sub)
    idx = np.linspace(0, n - 1, min(n, 5000)).astype(int)
    ax.scatter(sub[b].values[idx], sub[a].values[idx], s=4, alpha=0.3, color="steelblue")
    xs = np.linspace(sub[b].min(), sub[b].max(), 100)
    ax.plot(xs, alpha_ + beta_ * xs, color="red", lw=1, label=f"y={alpha_:.2f}+{beta_:.3f}·x")
    ax.set_xlabel(b)
    ax.set_ylabel(a)
    ax.legend(fontsize=8)
    ax.set_title(f"{a} vs {b} — OLS")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_pair_residuals(a, b, resid_series: pd.Series, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(np.arange(len(resid_series)), resid_series.values, lw=0.5, color="black")
    sd = resid_series.std()
    ax.axhline(0, color="grey", lw=0.4)
    ax.axhline(2 * sd, color="red", ls="--", lw=0.5, label="±2σ")
    ax.axhline(-2 * sd, color="red", ls="--", lw=0.5)
    ax.legend()
    ax.set_title(f"{a} − β·{b} residual")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


def _fig_rolling_beta(a, b, rolling_beta: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(rolling_beta["end_idx"].values, rolling_beta["beta"].values, "o-", color="steelblue")
    ax.set_xlabel("end-of-window tick index")
    ax.set_ylabel("β")
    ax.set_title(f"rolling β stability: {a} on {b}")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _safe_adf(s: pd.Series) -> float:
    s = s.dropna()
    if len(s) < 50:
        return float("nan")
    try:
        return float(adfuller(s.values, regression="c", autolag="AIC")[1])
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_deep_research(
    family: str,
    family_data: dict[str, ProductData],
    triggers: Triggers,
    out_dir: Path,
    verbose: bool = True,
) -> dict:
    """Execute deep dives on triggered products / pairs. Returns a manifest."""
    deep_dir = out_dir / "deep"
    deep_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[str]] = {"mr": [], "trending": [], "pairs": []}

    for p in triggers.mr:
        if p not in family_data or family_data[p].px.empty:
            continue
        if verbose:
            print(f"  [{family}] MR deep dive -> {p}")
        path = mr_deep_dive(family_data[p], deep_dir)
        manifest["mr"].append(str(path))

    for p in triggers.trending:
        if p not in family_data or family_data[p].px.empty:
            continue
        if verbose:
            print(f"  [{family}] trending deep dive -> {p}")
        path = trend_deep_dive(family_data[p], deep_dir)
        manifest["trending"].append(str(path))

    for a, b in triggers.pairs:
        if a not in family_data or b not in family_data:
            continue
        if verbose:
            print(f"  [{family}] pairs deep dive -> {a} <-> {b}")
        path = pairs_deep_dive(family_data, a, b, deep_dir)
        manifest["pairs"].append(str(path))

    # Manifest
    manifest_lines = ["# Deep-Research Manifest", ""]
    for kind in ("mr", "trending", "pairs"):
        manifest_lines.append(f"## {kind}")
        manifest_lines.extend([f"- {p}" for p in manifest[kind]] or ["- _(none)_"])
        manifest_lines.append("")
    (deep_dir / "MANIFEST.md").write_text("\n".join(manifest_lines), encoding="utf-8")

    return manifest
