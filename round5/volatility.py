"""Volatility analysis and trading-usage helpers for round-5 family research.

Always-on (cheap) outputs invoked from ``family_report``:

  * ``volatility_stats``         — per-product realized-vol stats at multiple
                                    windows + vol-of-vol + clustering.
  * ``vol_regime_table``         — tertile (low/mid/high) decomposition of
                                    ``std_50`` with per-regime spread, depth,
                                    OBI, and absolute-return averages.
  * ``vol_conditioned_ic``       — IC of each alpha signal evaluated *within*
                                    each vol regime. This is the key
                                    trading-usage table: it shows which
                                    signal works in which regime.
  * ``vol_trading_recommendations``  — markdown bullets translating those
                                    tables into sizing rules and
                                    regime-gated signal usage.

Plot helpers: per-product 3-panel volatility figure + family-level rv_50
overlay.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .research_lib import HORIZONS, ProductData, _save


VOL_WINDOWS = (20, 50, 200, 500)
REGIME_LABELS = ("low", "mid", "high")


# ---------------------------------------------------------------------------
# Per-product realized-vol stats
# ---------------------------------------------------------------------------

def volatility_stats(d: ProductData) -> dict:
    px = d.px
    out: dict = {"product": d.product}
    if px.empty:
        return out

    ret = px["ret_1"]
    abs_ret = ret.abs()

    for w in VOL_WINDOWS:
        rv = ret.rolling(w, min_periods=max(5, w // 4)).std()
        rv_clean = rv.dropna()
        out[f"rv_{w}_mean"] = float(rv_clean.mean()) if len(rv_clean) else np.nan
        out[f"rv_{w}_std"] = float(rv_clean.std()) if len(rv_clean) else np.nan
        out[f"rv_{w}_p10"] = float(rv_clean.quantile(0.10)) if len(rv_clean) else np.nan
        out[f"rv_{w}_p90"] = float(rv_clean.quantile(0.90)) if len(rv_clean) else np.nan

    rv50 = ret.rolling(50, min_periods=10).std().dropna()
    if len(rv50) and rv50.mean() > 0:
        out["vol_of_vol"] = float(rv50.std() / rv50.mean())
        p10 = float(rv50.quantile(0.10))
        p90 = float(rv50.quantile(0.90))
        out["vol_p90_p10_ratio"] = float(p90 / p10) if p10 > 0 else np.nan
    else:
        out["vol_of_vol"] = np.nan
        out["vol_p90_p10_ratio"] = np.nan

    # Clustering: positive autocorrelation of |ret| -> GARCH-like clustering.
    out["vol_cluster_lag1"] = float(abs_ret.autocorr(lag=1)) if len(abs_ret.dropna()) > 1 else np.nan
    out["vol_cluster_lag10"] = float(abs_ret.autocorr(lag=10)) if len(abs_ret.dropna()) > 10 else np.nan

    # Per-day stability (does mean rv_50 differ across days?)
    if "day" in px.columns:
        per_day = []
        for _, sub in px.groupby("day"):
            rv_d = sub["ret_1"].rolling(50, min_periods=10).std().dropna()
            per_day.append(float(rv_d.mean()) if len(rv_d) else np.nan)
        per_day_arr = np.array(per_day, dtype=float)
        if np.isfinite(per_day_arr).any():
            out["rv_50_day_max_min_ratio"] = float(np.nanmax(per_day_arr) / np.nanmin(per_day_arr)) if np.nanmin(per_day_arr) > 0 else np.nan

    return out


# ---------------------------------------------------------------------------
# Vol regime decomposition
# ---------------------------------------------------------------------------

def _regime_bands(rv: pd.Series) -> pd.Series:
    rv_clean = rv.dropna()
    if len(rv_clean) < 30:
        return pd.Series(index=rv.index, dtype="object")
    qs = rv_clean.quantile([1 / 3, 2 / 3]).values
    bands = pd.Series(index=rv.index, dtype="object")
    bands[rv <= qs[0]] = "low"
    bands[(rv > qs[0]) & (rv <= qs[1])] = "mid"
    bands[rv > qs[1]] = "high"
    return bands


def vol_regime_table(d: ProductData) -> pd.DataFrame:
    """Per-regime stats at tertile bands of std_50.

    Columns include per-regime spread, depth_l1, |OBI|, |ret_1|, mean rv_50."""
    px = d.px
    if px.empty or "std_50" not in px.columns:
        return pd.DataFrame()
    rv50 = px["std_50"]
    bands = _regime_bands(rv50)
    abs_ret = px["ret_1"].abs()
    rows = []
    for label in REGIME_LABELS:
        mask = bands == label
        n = int(mask.sum())
        if n == 0:
            rows.append({"product": d.product, "regime": label, "n_ticks": 0})
            continue
        rows.append({
            "product": d.product,
            "regime": label,
            "n_ticks": n,
            "frac_time": float(mask.mean()),
            "rv_50_mean": float(rv50[mask].mean()),
            "abs_ret_mean": float(abs_ret[mask].mean()),
            "spread_mean": float(px.loc[mask, "spread"].mean()) if "spread" in px else np.nan,
            "depth_l1_mean": float(px.loc[mask, "depth_l1"].mean()) if "depth_l1" in px else np.nan,
            "abs_obi_l1_mean": float(px.loc[mask, "obi_l1"].abs().mean()) if "obi_l1" in px else np.nan,
        })
    return pd.DataFrame(rows)


def vol_regime_transitions(d: ProductData) -> pd.DataFrame:
    """Row-stochastic transition matrix between regimes (rows = from, cols = to)."""
    px = d.px
    if px.empty or "std_50" not in px.columns:
        return pd.DataFrame()
    bands = _regime_bands(px["std_50"]).astype("object")
    pairs = pd.DataFrame({"from": bands, "to": bands.shift(-1)}).dropna()
    if pairs.empty:
        return pd.DataFrame()
    pairs = pairs[pairs["from"].isin(REGIME_LABELS) & pairs["to"].isin(REGIME_LABELS)]
    counts = pairs.groupby("from")["to"].value_counts().unstack(fill_value=0)
    counts = counts.reindex(index=REGIME_LABELS, columns=REGIME_LABELS, fill_value=0)
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)
    return probs


# ---------------------------------------------------------------------------
# Vol-conditioned signal IC (trading-usage core)
# ---------------------------------------------------------------------------

def vol_conditioned_ic(
    d: ProductData,
    signals_df: pd.DataFrame,
    horizons: Sequence[int] = HORIZONS,
) -> pd.DataFrame:
    """IC of each (signal, horizon) computed within each vol regime."""
    px = d.px
    if px.empty or signals_df.empty or "std_50" not in px.columns:
        return pd.DataFrame()
    bands = _regime_bands(px["std_50"])
    rows = []
    for sig_name in signals_df.columns:
        s = signals_df[sig_name]
        for h in horizons:
            f = px.get(f"fwd_{h}")
            if f is None:
                continue
            for regime in REGIME_LABELS:
                mask = (bands == regime).reindex(s.index, fill_value=False).fillna(False).astype(bool)
                if mask.sum() < 50:
                    rows.append({"product": d.product, "signal": sig_name, "horizon": h,
                                 "regime": regime, "n": int(mask.sum()), "ic": np.nan})
                    continue
                joined = pd.concat([s[mask], f[mask]], axis=1).dropna()
                if len(joined) < 50:
                    rows.append({"product": d.product, "signal": sig_name, "horizon": h,
                                 "regime": regime, "n": int(len(joined)), "ic": np.nan})
                    continue
                rows.append({
                    "product": d.product,
                    "signal": sig_name,
                    "horizon": h,
                    "regime": regime,
                    "n": int(len(joined)),
                    "ic": float(joined.iloc[:, 0].corr(joined.iloc[:, 1])),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Trading-usage recommendations (markdown)
# ---------------------------------------------------------------------------

def vol_trading_recommendations(
    vol_summary: pd.DataFrame,
    regime_df: pd.DataFrame,
    vci_df: pd.DataFrame,
    ic_baseline: pd.DataFrame,
    *,
    sizing_ratio_min: float = 1.5,
    regime_ic_diff_min: float = 0.04,
    spread_widen_min: float = 1.10,
) -> str:
    """Translate vol tables into trading-usage bullets.

    * **Sizing**: when vol_p90_p10_ratio >= sizing_ratio_min, suggest inverse-vol
      sizing with a target rv_50 (we use the median).
    * **Regime-gated signal**: signals whose |IC| differs across regimes by at
      least ``regime_ic_diff_min`` get flagged as regime-gated (turn on/off).
    * **MM risk**: products whose high-regime spread does not widen by at
      least ``spread_widen_min`` × low-regime spread are flagged because
      passive MM gives no extra cushion in the high-vol regime.
    """
    lines = ["## Volatility & sizing usage", ""]
    if vol_summary.empty:
        lines.append("- _(no volatility data)_")
        return "\n".join(lines)

    products = vol_summary["product"].tolist()
    for p in products:
        bullets: list[str] = []
        prow = vol_summary[vol_summary["product"] == p].iloc[0]

        # --- Sizing ---
        ratio = prow.get("vol_p90_p10_ratio")
        median_rv50 = prow.get("rv_50_mean")
        if pd.notna(ratio) and ratio >= sizing_ratio_min:
            bullets.append(
                f"VOL_SIZING: rv_50 spans {ratio:.2f}x between p10/p90. "
                f"Use inverse-vol scale = min(1, {median_rv50:.2f}/rv_50_t) "
                f"to keep risk-per-unit roughly constant."
            )

        # --- Vol clustering ---
        clust = prow.get("vol_cluster_lag1")
        if pd.notna(clust) and clust > 0.05:
            bullets.append(
                f"VOL_CLUSTERING: |ret| autocorr(lag=1) = {clust:+.3f}. "
                f"Vol shocks persist; recent rv_50 is informative for next-tick risk."
            )

        # --- Spread vs vol (passive MM cushion) ---
        if not regime_df.empty:
            rsub = regime_df[regime_df["product"] == p]
            if not rsub.empty and "spread_mean" in rsub.columns:
                low_sp = rsub.loc[rsub["regime"] == "low", "spread_mean"]
                high_sp = rsub.loc[rsub["regime"] == "high", "spread_mean"]
                if len(low_sp) and len(high_sp) and float(low_sp.iloc[0]) > 0:
                    widen = float(high_sp.iloc[0]) / float(low_sp.iloc[0])
                    if widen < spread_widen_min:
                        bullets.append(
                            f"MM_RISK_HIGH_VOL: spread widens only {widen:.2f}x between low/high vol. "
                            f"Passive MM gets squeezed in high-vol — gate maker quotes by std_50."
                        )

        # --- Regime-gated signal ---
        if not vci_df.empty:
            sub = vci_df[vci_df["product"] == p]
            for sig_name in sub["signal"].unique():
                for h in sub["horizon"].unique():
                    cell = sub[(sub["signal"] == sig_name) & (sub["horizon"] == h)]
                    if len(cell) < 3:
                        continue
                    pivot = cell.set_index("regime")["ic"].reindex(REGIME_LABELS)
                    if pivot.dropna().empty:
                        continue
                    diff = float(pivot.abs().max() - pivot.abs().min())
                    if pd.isna(diff) or diff < regime_ic_diff_min:
                        continue
                    best = pivot.abs().idxmax()
                    worst = pivot.abs().idxmin()
                    if best == worst:
                        continue
                    bullets.append(
                        f"REGIME_GATED_SIGNAL: {sig_name} @ h={h}  "
                        f"|IC|_{best}={abs(pivot[best]):.3f} vs |IC|_{worst}={abs(pivot[worst]):.3f} — "
                        f"trade only in {best}-vol regime."
                    )

        if bullets:
            lines.append(f"- **{p}**:")
            lines.extend([f"  - {b}" for b in bullets])
        else:
            lines.append(f"- {p}: _(no flags)_")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_vol_panel(
    d: ProductData,
    vci_df_for_p: pd.DataFrame,
    out_path: Path,
) -> Path:
    """3-panel per-product volatility figure: rv_50 distribution + tertiles,
    |ret_1| ACF (clustering), and IC × regime heatmap at h=10."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.suptitle(f"{d.product} — Volatility Panel", fontsize=12, fontweight="bold")

    # Panel 1: rv_50 distribution + tertile bands
    axA = axes[0]
    if not d.px.empty and "std_50" in d.px.columns:
        rv50 = d.px["std_50"].dropna()
        if len(rv50):
            axA.hist(rv50, bins=60, color="steelblue", alpha=0.7)
            qs = rv50.quantile([1 / 3, 2 / 3]).values
            for q, lab in zip(qs, ["33%", "67%"]):
                axA.axvline(q, color="red", ls="--", lw=0.6, label=f"{lab}={q:.2f}")
            axA.legend(fontsize=8)
        axA.set_title("rv_50 distribution + tertile bands")
        axA.set_xlabel("std_50")

    # Panel 2: |ret_1| ACF (clustering)
    axB = axes[1]
    if not d.px.empty:
        abs_ret = d.px["ret_1"].abs().dropna()
        max_lag = min(100, max(2, len(abs_ret) // 10))
        lags = np.arange(1, max_lag + 1)
        ac = np.array([abs_ret.autocorr(int(l)) for l in lags])
        n = len(abs_ret)
        band = 1.96 / np.sqrt(n) if n > 0 else 0
        axB.bar(lags, ac, color="seagreen", width=0.8)
        axB.axhline(band, color="grey", ls="--", lw=0.5)
        axB.axhline(-band, color="grey", ls="--", lw=0.5)
        axB.axhline(0, color="black", lw=0.5)
        axB.set_title("|ret_1| ACF (vol clustering)")
        axB.set_xlabel("lag")

    # Panel 3: IC heatmap (signal × regime) at h=10
    axC = axes[2]
    if not vci_df_for_p.empty:
        sub = vci_df_for_p[vci_df_for_p["horizon"] == 10]
        if not sub.empty:
            pivot = sub.pivot(index="signal", columns="regime", values="ic").reindex(columns=REGIME_LABELS)
            arr = pivot.values.astype(float)
            vmax = max(0.05, float(np.nanmax(np.abs(arr))) if np.isfinite(arr).any() else 0.05)
            im = axC.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
            axC.set_xticks(np.arange(arr.shape[1]))
            axC.set_xticklabels(pivot.columns, fontsize=8)
            axC.set_yticks(np.arange(arr.shape[0]))
            axC.set_yticklabels(pivot.index, fontsize=8)
            for i in range(arr.shape[0]):
                for j in range(arr.shape[1]):
                    v = arr[i, j]
                    if np.isfinite(v):
                        axC.text(j, i, f"{v:+.02f}", ha="center", va="center", fontsize=7,
                                 color="white" if abs(v) > vmax * 0.5 else "black")
            fig.colorbar(im, ax=axC, fraction=0.04)
        axC.set_title("Signal IC × regime @ h=10")
    else:
        axC.text(0.5, 0.5, "no vci data", ha="center")

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, out_path)
    return out_path


def fig_family_vol_compare(family_data: dict[str, ProductData], out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    any_data = False
    for p, d in family_data.items():
        if d.px.empty or "std_50" not in d.px.columns:
            continue
        rv50 = d.px["std_50"].dropna()
        if not len(rv50):
            continue
        ax.hist(
            rv50, bins=60, alpha=0.35, density=True,
            label=p.split("_", 1)[-1] if "_" in p else p,
        )
        any_data = True
    if any_data:
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "no rv_50 data", ha="center")
    ax.set_xlabel("std_50")
    ax.set_title("Family rv_50 distribution overlay")
    fig.tight_layout()
    _save(fig, out_path)
    return out_path
