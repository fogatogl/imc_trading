"""Round-5 volatility-spike study.

Spike definition (per product, per day):
    |ret_1_t| >= K * std_500_t-1, with K = 4 by default.

Why std_500 (long-window) and not std_50: a persistent high-vol regime
inflates std_50 and hides genuine outliers. std_500 lagged-by-1 keeps the
baseline robust and avoids the look-ahead bias that std_50_t carries.

Outputs under round5/reports/CROSS/vol_spikes/:
    spike_summary.csv         per-product spike count, rate, magnitude,
                              post-spike signed cumret at h ∈ {1,10,50,200},
                              spread/depth response.
    spike_cooccurrence.csv    per-product systemic-rate (fraction of own
                              spikes during which >=N other products spiked
                              within ±2 ticks); plus inter-family pair
                              co-spike rates.
    spike_post_returns.csv    long-form per-product × horizon mean signed
                              cumret + n.
    family_summary.csv        family-level aggregates.
    figures/<P>_spike_panel.png  4-panel per-product figure (top spikes,
                              post-spike profile, spread/depth response,
                              spike inter-arrival).
    figures/cooccurrence_heatmap.png  50×50 systemic-spike correlation.
    figures/family_post_spike.png    per-family mean post-spike profile.
    vol_spikes_report.md      narrative interpretation.

CLI: python round5/vol_spikes.py [--k 4.0] [--lookback 500] [--cooc-window 2]
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
    DATASET_ROOT, DEFAULT_DAYS, FAMILIES, ProductData, add_microstructure,
    add_vwap, family_products, load_prices, load_trades,
)


POST_HORIZONS = (1, 5, 10, 50, 200)
SYSTEMIC_PEERS_THRESHOLD = 5  # >= N other products spiking within ±W ticks


# ---------------------------------------------------------------------------
# Per-product spike detection
# ---------------------------------------------------------------------------

def detect_spikes(d: ProductData, k: float, lookback: int) -> pd.DataFrame:
    """Return one row per spike event: timestamp, day, sign, |ret|, baseline.

    Detection done per-day to avoid baseline leaking across day breaks.
    """
    px = d.px
    if px.empty or "ret_1" not in px.columns:
        return pd.DataFrame()
    rows = []
    for day, sub in px.groupby("day", sort=True):
        sub = sub.sort_values("timestamp").reset_index(drop=True)
        ret = sub["ret_1"]
        baseline = ret.rolling(lookback, min_periods=max(50, lookback // 5)).std().shift(1)
        thr = k * baseline
        is_spike = (ret.abs() >= thr) & thr.notna() & (thr > 0)
        if not is_spike.any():
            continue
        idx = np.where(is_spike.values)[0]
        for i in idx:
            rows.append({
                "product": d.product,
                "day": int(day),
                "ts": int(sub.loc[i, "timestamp"]),
                "row_idx": int(i),
                "sign": int(np.sign(ret.iloc[i])) or 1,
                "abs_ret": float(abs(ret.iloc[i])),
                "baseline_std": float(baseline.iloc[i]),
                "z": float(abs(ret.iloc[i]) / baseline.iloc[i]),
                "spread": float(sub.loc[i, "spread"]) if "spread" in sub.columns else np.nan,
                "depth_l1": float(sub.loc[i, "depth_l1"]) if "depth_l1" in sub.columns else np.nan,
                "n_ticks_day": int(len(sub)),
            })
    return pd.DataFrame(rows)


def post_spike_profile(d: ProductData, spikes: pd.DataFrame) -> dict[int, dict]:
    """Per-horizon mean signed cumret after each spike (per product).

    Returns {h: {mean, median, std, n}}. Signed = ret_h * (-sign(spike))
    so positive value ⇒ reversion (next ticks move *against* the spike).
    """
    out: dict[int, dict] = {h: {"mean": np.nan, "median": np.nan, "std": np.nan, "n": 0} for h in POST_HORIZONS}
    if spikes.empty:
        return out
    px = d.px.set_index(["day", "timestamp"]).sort_index()
    samples: dict[int, list[float]] = {h: [] for h in POST_HORIZONS}
    for _, row in spikes.iterrows():
        day = row["day"]
        i = int(row["row_idx"])
        sign = int(row["sign"])
        sub = d.px[d.px["day"] == day].reset_index(drop=True)
        if i >= len(sub):
            continue
        for h in POST_HORIZONS:
            j = i + h
            if j >= len(sub):
                continue
            cumret = float(sub.loc[j, "mid"] - sub.loc[i, "mid"])
            samples[h].append(-sign * cumret)  # positive ⇒ reversion
    for h, arr in samples.items():
        if not arr:
            continue
        a = np.asarray(arr, dtype=float)
        out[h] = {"mean": float(np.mean(a)), "median": float(np.median(a)),
                  "std": float(np.std(a)), "n": int(len(a))}
    return out


def microstructure_response(d: ProductData, spikes: pd.DataFrame) -> dict:
    """Spread/depth at-spike vs baseline ratios."""
    px = d.px
    out = {"spread_at_spike_mean": np.nan, "spread_baseline_mean": np.nan,
           "spread_widen_x": np.nan, "depth_at_spike_mean": np.nan,
           "depth_baseline_mean": np.nan, "depth_drop_x": np.nan}
    if spikes.empty or "spread" not in px.columns:
        return out
    spread_base = px["spread"].mean()
    depth_base = px["depth_l1"].mean() if "depth_l1" in px.columns else np.nan
    out["spread_baseline_mean"] = float(spread_base)
    out["depth_baseline_mean"] = float(depth_base) if depth_base == depth_base else np.nan
    out["spread_at_spike_mean"] = float(spikes["spread"].mean())
    if "depth_l1" in spikes.columns:
        out["depth_at_spike_mean"] = float(spikes["depth_l1"].mean())
    if spread_base and spread_base > 0:
        out["spread_widen_x"] = out["spread_at_spike_mean"] / spread_base
    if depth_base and depth_base > 0:
        out["depth_drop_x"] = out["depth_at_spike_mean"] / depth_base
    return out


# ---------------------------------------------------------------------------
# Cross-product co-occurrence
# ---------------------------------------------------------------------------

def build_spike_grid(spikes_by_product: dict[str, pd.DataFrame],
                     all_timestamps_by_day: dict[int, np.ndarray]) -> dict[int, pd.DataFrame]:
    """For each day, return a DataFrame indexed by timestamp, columns = products,
    1 if a spike occurred at that timestamp else 0."""
    grids: dict[int, pd.DataFrame] = {}
    for day, ts in all_timestamps_by_day.items():
        grid = pd.DataFrame(0, index=ts, columns=list(spikes_by_product.keys()), dtype=np.int8)
        for product, sp in spikes_by_product.items():
            if sp.empty:
                continue
            sub = sp[sp["day"] == day]
            if sub.empty:
                continue
            mask = grid.index.isin(sub["ts"].values)
            grid.loc[mask, product] = 1
        grids[day] = grid
    return grids


def cooccurrence_metrics(grids: dict[int, pd.DataFrame], cooc_window: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each spike, count peers spiking within ±cooc_window ticks.

    Returns:
        per_product: per-product systemic_rate + median_peer_count.
        peer_pairs:  product pair co-spike counts (symmetric).
    """
    if not grids:
        return pd.DataFrame(), pd.DataFrame()

    products = list(next(iter(grids.values())).columns)
    per_product_counts: dict[str, list[int]] = {p: [] for p in products}
    pair_count = pd.DataFrame(0.0, index=products, columns=products)

    for day, grid in grids.items():
        # Smooth ±W: rolling sum window=2W+1 over each column.
        win = 2 * cooc_window + 1
        smoothed = grid.rolling(win, min_periods=1, center=True).sum().clip(upper=1).astype(np.int8)
        # row_total = number of products that spiked in the ±W window of each ts.
        row_total = smoothed.sum(axis=1)
        for p in products:
            spike_ts = grid.index[grid[p] == 1]
            if len(spike_ts) == 0:
                continue
            peer_count = (row_total.loc[spike_ts] - smoothed.loc[spike_ts, p]).astype(int)
            per_product_counts[p].extend(peer_count.tolist())

        # Pair co-spike count: Σ_t smoothed[t, p] * grid[t, q]  (asymmetric → symmetrize)
        # Compute via dot product on a sample of spike rows.
        spike_rows = grid[grid.sum(axis=1) > 0]
        if len(spike_rows) > 0:
            sm_rows = smoothed.loc[spike_rows.index]
            pair_inc = sm_rows.T.values.astype(np.float64) @ spike_rows.values.astype(np.float64)
            pair_count = pair_count + pd.DataFrame(pair_inc, index=products, columns=products)

    rows = []
    for p in products:
        counts = np.array(per_product_counts[p], dtype=int)
        n = len(counts)
        if n == 0:
            rows.append({"product": p, "n_spikes": 0, "systemic_rate": np.nan,
                         "median_peer_count": np.nan, "mean_peer_count": np.nan})
            continue
        rows.append({
            "product": p,
            "n_spikes": int(n),
            "systemic_rate": float((counts >= SYSTEMIC_PEERS_THRESHOLD).mean()),
            "median_peer_count": float(np.median(counts)),
            "mean_peer_count": float(np.mean(counts)),
        })
    per_product = pd.DataFrame(rows)

    # Symmetrize pair_count (count_pq + count_qp) / 2 — diagonal = self spike count.
    pair_sym = (pair_count + pair_count.T) / 2.0
    return per_product, pair_sym


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_spike_panel(d: ProductData, spikes: pd.DataFrame, post: dict[int, dict],
                    out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(f"{d.product} — Volatility Spike Panel", fontsize=12, fontweight="bold")

    # Panel A: mid + spike markers (one day for clarity, the day with most spikes)
    axA = axes[0, 0]
    if not spikes.empty:
        top_day = int(spikes["day"].value_counts().idxmax())
        sub = d.px[d.px["day"] == top_day].reset_index(drop=True)
        sub_sp = spikes[spikes["day"] == top_day]
        axA.plot(sub["timestamp"], sub["mid"], color="steelblue", lw=0.5)
        if not sub_sp.empty:
            up = sub_sp[sub_sp["sign"] > 0]
            dn = sub_sp[sub_sp["sign"] < 0]
            axA.scatter(up["ts"], [sub.loc[i, "mid"] for i in up["row_idx"]],
                        s=18, c="green", marker="^", label=f"up ({len(up)})")
            axA.scatter(dn["ts"], [sub.loc[i, "mid"] for i in dn["row_idx"]],
                        s=18, c="red", marker="v", label=f"down ({len(dn)})")
            axA.legend(fontsize=8)
        axA.set_title(f"day {top_day} mid + spike events")
        axA.set_xlabel("timestamp")
    else:
        axA.text(0.5, 0.5, "no spikes", ha="center")

    # Panel B: post-spike signed cumret profile (positive ⇒ reversion)
    axB = axes[0, 1]
    hs = list(POST_HORIZONS)
    has_data = any(post[h]["n"] > 0 for h in hs)
    if has_data:
        means = [post[h]["mean"] for h in hs]
        stds = [post[h]["std"] / np.sqrt(max(1, post[h]["n"])) for h in hs]
        axB.errorbar(hs, means, yerr=stds, marker="o", color="darkorange", capsize=3)
        axB.axhline(0, color="black", lw=0.5)
        axB.set_xscale("log")
    else:
        axB.text(0.5, 0.5, "no spikes", ha="center")
    axB.set_title("Mean signed cumret after spike (>0 ⇒ revert, <0 ⇒ follow)")
    axB.set_xlabel("horizon (ticks)")
    axB.set_ylabel("cumret · -sign(spike)")

    # Panel C: spread response
    axC = axes[1, 0]
    if not spikes.empty and "spread" in d.px.columns:
        baseline_spread = d.px["spread"].dropna()
        axC.hist(baseline_spread, bins=40, alpha=0.55, density=True,
                 color="steelblue", label=f"baseline (n={len(baseline_spread)})")
        sp_spread = spikes["spread"].dropna()
        if len(sp_spread):
            axC.hist(sp_spread, bins=40, alpha=0.55, density=True,
                     color="firebrick", label=f"at-spike (n={len(sp_spread)})")
        axC.set_title("spread distribution: baseline vs at-spike")
        axC.set_xlabel("spread (ticks)")
        axC.legend(fontsize=8)

    # Panel D: spike inter-arrival distribution
    axD = axes[1, 1]
    if not spikes.empty:
        gaps_all = []
        for day, sub in spikes.groupby("day"):
            ts = sub["ts"].sort_values().values
            if len(ts) > 1:
                gaps_all.extend(np.diff(ts).tolist())
        if gaps_all:
            axD.hist(gaps_all, bins=40, color="seagreen", alpha=0.8)
            axD.set_yscale("log")
            axD.set_title(f"inter-arrival gaps (median={int(np.median(gaps_all))})")
            axD.set_xlabel("ticks between consecutive spikes")
        else:
            axD.text(0.5, 0.5, "<2 spikes per day", ha="center")
    else:
        axD.text(0.5, 0.5, "no spikes", ha="center")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_cooccurrence_heatmap(pair_sym: pd.DataFrame, products: list[str], out_path: Path) -> None:
    if pair_sym.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 10))
    diag = np.diag(pair_sym.values).copy()
    norm = np.outer(np.sqrt(diag), np.sqrt(diag))
    norm[norm == 0] = np.nan
    cosine = pair_sym.values / norm
    np.fill_diagonal(cosine, np.nan)
    im = ax.imshow(cosine, cmap="magma", vmin=0, vmax=np.nanpercentile(cosine, 95) or 1.0)
    ax.set_xticks(np.arange(len(products)))
    ax.set_yticks(np.arange(len(products)))
    short = [p.split("_", 1)[-1][:14] for p in products]
    ax.set_xticklabels(short, rotation=90, fontsize=6)
    ax.set_yticklabels(short, fontsize=6)
    ax.set_title("Spike co-occurrence (cosine: pair_count / sqrt(n_a · n_b))")
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_family_post_spike(family_post: dict[str, dict[int, dict]], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    hs = list(POST_HORIZONS)
    plotted = 0
    for fam, post in family_post.items():
        means = [post[h]["mean"] for h in hs]
        if all(not np.isfinite(m) for m in means):
            continue
        ax.plot(hs, means, marker="o", label=fam)
        plotted += 1
    ax.axhline(0, color="black", lw=0.6)
    if plotted:
        ax.set_xscale("log")
    ax.set_xlabel("horizon (ticks)")
    ax.set_ylabel("mean signed cumret (>0 ⇒ revert)")
    ax.set_title("Family-level post-spike profile (avg over members + spikes)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(k: float, lookback: int, cooc_window: int, days, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    products = [p for fam in FAMILIES.values() for p in fam]
    spikes_by_product: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict] = []
    post_long_rows: list[dict] = []
    family_post_acc: dict[str, dict[int, list[float]]] = {f: {h: [] for h in POST_HORIZONS} for f in FAMILIES}
    timestamps_by_day: dict[int, set] = {d: set() for d in days}

    print(f"[vol_spikes] loading {len(products)} products, days={list(days)}, K={k}, lookback={lookback}")
    for fam, members in FAMILIES.items():
        print(f"  family {fam}")
        for p in members:
            px = load_prices(p, days)
            px = add_microstructure(px)
            tr = load_trades(p, days)
            px = add_vwap(px, tr)
            d = ProductData(product=p, px=px, tr=tr)

            for day in days:
                timestamps_by_day[day].update(px.loc[px["day"] == day, "timestamp"].tolist())

            spikes = detect_spikes(d, k=k, lookback=lookback)
            spikes_by_product[p] = spikes
            post = post_spike_profile(d, spikes)
            micro = microstructure_response(d, spikes)

            n_ticks = int(len(px))
            n_sp = int(len(spikes))
            row = {
                "family": fam,
                "product": p,
                "n_ticks": n_ticks,
                "n_spikes": n_sp,
                "spike_rate_per_10k": (n_sp / n_ticks * 1e4) if n_ticks else np.nan,
                "abs_ret_mean": float(spikes["abs_ret"].mean()) if n_sp else np.nan,
                "abs_ret_p90": float(spikes["abs_ret"].quantile(0.9)) if n_sp else np.nan,
                "z_mean": float(spikes["z"].mean()) if n_sp else np.nan,
                "z_max": float(spikes["z"].max()) if n_sp else np.nan,
            }
            row.update({f"post_h{h}_mean": post[h]["mean"] for h in POST_HORIZONS})
            row.update({f"post_h{h}_n": post[h]["n"] for h in POST_HORIZONS})
            row.update(micro)
            summary_rows.append(row)

            for h in POST_HORIZONS:
                post_long_rows.append({
                    "family": fam, "product": p, "horizon": h,
                    "mean": post[h]["mean"], "median": post[h]["median"],
                    "std": post[h]["std"], "n": post[h]["n"],
                })
                if post[h]["n"] > 0:
                    family_post_acc[fam][h].append(post[h]["mean"])

            fig_spike_panel(d, spikes, post, fig_dir / f"{p}_spike_panel.png")

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_dir / "spike_summary.csv", index=False)
    pd.DataFrame(post_long_rows).to_csv(out_dir / "spike_post_returns.csv", index=False)

    # All spikes table
    all_spikes = pd.concat(
        [s.assign(family=fam) for fam, ms in FAMILIES.items() for p in ms
         for s in [spikes_by_product[p].assign(family=fam)] if not s.empty],
        ignore_index=True,
    ) if any(not s.empty for s in spikes_by_product.values()) else pd.DataFrame()
    if not all_spikes.empty:
        all_spikes.to_csv(out_dir / "spike_events.csv", index=False)

    # Co-occurrence
    ts_by_day_arr = {d: np.array(sorted(t)) for d, t in timestamps_by_day.items() if t}
    grids = build_spike_grid(spikes_by_product, ts_by_day_arr)
    cooc_per_product, pair_sym = cooccurrence_metrics(grids, cooc_window=cooc_window)
    cooc_per_product.to_csv(out_dir / "spike_cooccurrence.csv", index=False)
    pair_sym.to_csv(out_dir / "spike_cooccurrence_matrix.csv")
    fig_cooccurrence_heatmap(pair_sym, products, fig_dir / "cooccurrence_heatmap.png")

    # Family-level summary
    fam_rows = []
    family_post: dict[str, dict[int, dict]] = {}
    for fam, members in FAMILIES.items():
        sub = summary[summary["family"] == fam]
        cooc_sub = cooc_per_product[cooc_per_product["product"].isin(members)]
        post_means = {h: float(np.nanmean(family_post_acc[fam][h])) if family_post_acc[fam][h] else np.nan
                      for h in POST_HORIZONS}
        family_post[fam] = {h: {"mean": post_means[h], "median": np.nan, "std": np.nan, "n": 0}
                            for h in POST_HORIZONS}
        fam_rows.append({
            "family": fam,
            "n_spikes_total": int(sub["n_spikes"].sum()),
            "spike_rate_per_10k_mean": float(sub["spike_rate_per_10k"].mean()),
            "z_mean": float(sub["z_mean"].mean()),
            "spread_widen_x_mean": float(sub["spread_widen_x"].mean()),
            "depth_drop_x_mean": float(sub["depth_drop_x"].mean()),
            "systemic_rate_mean": float(cooc_sub["systemic_rate"].mean()) if not cooc_sub.empty else np.nan,
            **{f"post_h{h}_family_mean": post_means[h] for h in POST_HORIZONS},
        })
    pd.DataFrame(fam_rows).to_csv(out_dir / "family_summary.csv", index=False)
    fig_family_post_spike(family_post, fig_dir / "family_post_spike.png")

    print(f"[vol_spikes] done. wrote artifacts under {out_dir}")
    return summary, cooc_per_product, pair_sym, fam_rows


def main(argv=None):
    p = argparse.ArgumentParser(description="Round-5 volatility spike study")
    p.add_argument("--k", type=float, default=4.0,
                   help="spike threshold in std multiples (default 4.0)")
    p.add_argument("--lookback", type=int, default=500,
                   help="rolling-std window for baseline (default 500)")
    p.add_argument("--cooc-window", type=int, default=2,
                   help="co-occurrence ±tick window (default 2)")
    p.add_argument("--days", type=int, nargs="+", default=list(DEFAULT_DAYS))
    p.add_argument("--out", type=Path, default=_PROJECT_ROOT / "round5" / "reports" / "CROSS" / "vol_spikes")
    args = p.parse_args(argv)
    run(k=args.k, lookback=args.lookback, cooc_window=args.cooc_window,
        days=args.days, out_dir=args.out)


if __name__ == "__main__":
    main()
