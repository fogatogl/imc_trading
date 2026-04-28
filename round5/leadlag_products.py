"""Product-level lead-lag scan across all 50 round-5 products.

Family-level analysis already exists at ``round5/reports/CROSS/cross_findings.md``.
This script drops down to the 50 individual products to surface intra-family
and cross-family pairs that the family-level aggregation washes out.

Output: ``round5/reports/CROSS/leadlag_products.csv`` (one row per ordered
pair / lag) + ``leadlag_products_summary.md`` (top stable pairs).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATASET = Path(__file__).resolve().parent.parent / "dataset" / "ROUND_5"
OUT_DIR = Path(__file__).resolve().parent / "reports" / "CROSS"
DAYS = (2, 3, 4)
LAGS = list(range(1, 6))  # leader leads follower by L ticks (positive only)
TOP_N = 60


def load_mid_panel() -> dict[int, pd.DataFrame]:
    """Per-day pivot: index=timestamp, columns=product, values=mid_price."""
    panels: dict[int, pd.DataFrame] = {}
    for d in DAYS:
        df = pd.read_csv(DATASET / f"prices_round_5_day_{d}.csv", sep=";")
        wide = (
            df.pivot_table(index="timestamp", columns="product", values="mid_price")
            .sort_index()
        )
        panels[d] = wide
    return panels


def returns_per_day(panels: dict[int, pd.DataFrame]) -> dict[int, pd.DataFrame]:
    """First-difference of mid per day (avoids cross-day jumps)."""
    return {d: w.diff().dropna(how="all") for d, w in panels.items()}


def leadlag_table(rets: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Per-day Pearson corr( leader[t-L], follower[t] ), L>=1."""
    products = sorted(set().union(*[set(r.columns) for r in rets.values()]))
    records = []
    for d, r in rets.items():
        # Standardise once per day for speed; lag via numpy slicing.
        z = (r - r.mean()) / r.std(ddof=0)
        z = z.fillna(0.0).to_numpy()
        cols = list(r.columns)
        idx = {p: i for i, p in enumerate(cols)}
        n = z.shape[0]
        for L in LAGS:
            if n <= L + 5:
                continue
            a = z[:-L, :]  # leader_{t-L}
            b = z[L:, :]   # follower_t
            # corr matrix = (a.T @ b) / (n-L), since columns standardised.
            denom = a.shape[0]
            mat = (a.T @ b) / denom
            for i, leader in enumerate(cols):
                if leader not in idx:
                    continue
                for j, follower in enumerate(cols):
                    if leader == follower:
                        continue
                    records.append(
                        (d, leader, follower, L, float(mat[i, j]))
                    )
    return pd.DataFrame.from_records(
        records, columns=["day", "leader", "follower", "lag", "corr"]
    )


def stable_pairs(table: pd.DataFrame) -> pd.DataFrame:
    """For each (leader, follower, lag) keep mean |corr| with sign-stability gate."""
    g = (
        table.groupby(["leader", "follower", "lag"], sort=False)
        .agg(
            mean_corr=("corr", "mean"),
            min_corr=("corr", "min"),
            max_corr=("corr", "max"),
            n_days=("corr", "count"),
        )
        .reset_index()
    )
    # Require sign agreement across all days observed.
    g["sign_stable"] = (g["min_corr"] > 0) | (g["max_corr"] < 0)
    g["abs_mean"] = g["mean_corr"].abs()
    return g.sort_values("abs_mean", ascending=False)


def best_lag_per_pair(stable: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one row per ordered pair = best lag by |mean_corr|."""
    idx = stable.groupby(["leader", "follower"])["abs_mean"].idxmax()
    return stable.loc[idx].sort_values("abs_mean", ascending=False).reset_index(drop=True)


def family_of(p: str) -> str:
    return p.rsplit("_", 1)[0] if not p.startswith(("PEBBLES_", "PANEL_")) else p.split("_")[0]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panels = load_mid_panel()
    rets = returns_per_day(panels)
    full = leadlag_table(rets)
    full.to_csv(OUT_DIR / "leadlag_products_full.csv", index=False)

    stable = stable_pairs(full)
    stable.to_csv(OUT_DIR / "leadlag_products_stable.csv", index=False)

    best = best_lag_per_pair(stable)
    best.to_csv(OUT_DIR / "leadlag_products_best.csv", index=False)

    # Markdown summary
    lines = []
    lines.append("# Product-level lead-lag scan\n")
    lines.append(f"Lags scanned: {LAGS}.  Days: {list(DAYS)}.  ")
    lines.append("Sign-stable = sign of corr agrees across all 3 days.\n\n")

    sign_stable = best[best["sign_stable"]].head(TOP_N)
    lines.append(f"## Top {len(sign_stable)} sign-stable ordered pairs (by |mean corr|)\n\n")
    lines.append("| leader | follower | lag | mean_corr | min | max | same_family |\n")
    lines.append("|---|---|---:|---:|---:|---:|:---:|\n")
    for _, r in sign_stable.iterrows():
        same = "yes" if r.leader.split("_")[0] == r.follower.split("_")[0] else ""
        lines.append(
            f"| {r.leader} | {r.follower} | {int(r.lag)} | "
            f"{r.mean_corr:+.4f} | {r.min_corr:+.4f} | {r.max_corr:+.4f} | {same} |\n"
        )

    # Top intra-family
    intra = best[
        best["sign_stable"]
        & (best["leader"].str.split("_").str[0] == best["follower"].str.split("_").str[0])
    ].head(40)
    lines.append(f"\n## Top {len(intra)} sign-stable INTRA-family pairs\n\n")
    lines.append("| leader | follower | lag | mean_corr | min | max |\n")
    lines.append("|---|---|---:|---:|---:|---:|\n")
    for _, r in intra.iterrows():
        lines.append(
            f"| {r.leader} | {r.follower} | {int(r.lag)} | "
            f"{r.mean_corr:+.4f} | {r.min_corr:+.4f} | {r.max_corr:+.4f} |\n"
        )

    (OUT_DIR / "leadlag_products_summary.md").write_text("".join(lines))
    print(f"wrote {OUT_DIR / 'leadlag_products_full.csv'}  ({len(full):,} rows)")
    print(f"wrote {OUT_DIR / 'leadlag_products_stable.csv'}  ({len(stable):,} rows)")
    print(f"wrote {OUT_DIR / 'leadlag_products_best.csv'}  ({len(best):,} rows)")
    print(f"wrote {OUT_DIR / 'leadlag_products_summary.md'}")
    print(f"sign-stable pairs (any |corr|): {int(best['sign_stable'].sum())}")
    print(f"top |corr|: {best.iloc[0]['leader']} -> {best.iloc[0]['follower']} "
          f"L={int(best.iloc[0]['lag'])}  mean={best.iloc[0]['mean_corr']:+.4f}")


if __name__ == "__main__":
    main()
