"""Basket-vs-leg lead-lag using signed trade flow (OFI proxy) as the predictor.

Companion to ``leadlag_products.py`` and the audit at
``round5/reports/CROSS/leadlag_audit.md``. The audit established that LOO
basket is mandatory; this script defaults to LOO and uses the shared
``cross_family.basket_vs_leg_table`` helper.

Two predictor variants are compared:
  - ``mid``: basket of mid-diff returns (replicates audited result)
  - ``ofi``: basket of signed trade volume per tick

Trade signing rule: each trade is signed by sign(price - mid_at_t). At-mid
trades contribute 0. Signed volume per (timestamp, product) is then summed
into a wide panel aligned with the prices panel.

Round-5 trades CSV has empty buyer/seller columns by design
(``project_round5_no_counterparties``), so this trade-tape signing is the
only OFI proxy available without orderbook delta reconstruction.

Output:
  round5/reports/CROSS/leadlag_basket_ofi.csv  (per family/leg/lag/predictor)
  round5/reports/CROSS/leadlag_basket_ofi.md   (top-survivors readout)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from round5.cross_family import basket_vs_leg_table  # type: ignore
from round5.research_lib import DATASET_ROOT, FAMILIES

DAYS = (2, 3, 4)
LAGS = (1, 2, 3, 4, 5)
OUT = Path(__file__).resolve().parent / "reports" / "CROSS"


def load_day(d: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (mid_diff_panel, signed_vol_panel) aligned on timestamp."""
    px = pd.read_csv(DATASET_ROOT / f"prices_round_5_day_{d}.csv", sep=";")
    tr = pd.read_csv(DATASET_ROOT / f"trades_round_5_day_{d}.csv", sep=";")

    mid = (
        px.pivot_table(index="timestamp", columns="product", values="mid_price")
        .sort_index()
    )
    ret = mid.diff()

    # Sign each trade by price vs mid at that ts. Need to look up mid by (ts, sym).
    tr = tr.merge(
        px[["timestamp", "product", "mid_price"]].rename(columns={"product": "symbol"}),
        on=["timestamp", "symbol"],
        how="left",
    )
    tr["sign"] = np.sign(tr["price"] - tr["mid_price"]).fillna(0).astype(int)
    tr["signed_qty"] = tr["sign"] * tr["quantity"]
    sv = (
        tr.groupby(["timestamp", "symbol"])["signed_qty"]
        .sum()
        .unstack(fill_value=0.0)
    )
    # Align signed-volume panel to mid panel (fill missing ticks with 0).
    sv = sv.reindex(index=mid.index, columns=mid.columns, fill_value=0.0)
    return ret, sv


def per_day_table(predictor_kind: str) -> pd.DataFrame:
    """Run basket_vs_leg per day, tag with day + predictor."""
    rows = []
    for d in DAYS:
        ret, sv = load_day(d)
        target = ret  # always predict next-tick mid return
        if predictor_kind == "mid":
            pred = ret
        elif predictor_kind == "ofi":
            pred = sv
        else:
            raise ValueError(predictor_kind)
        tab = basket_vs_leg_table(
            panel=target, family_map=FAMILIES, lags=LAGS, loo=True,
            leg_signal_panel=pred,
        )
        tab["day"] = d
        tab["predictor"] = predictor_kind
        rows.append(tab)
    return pd.concat(rows, ignore_index=True)


def pool(table: pd.DataFrame) -> pd.DataFrame:
    g = (
        table.groupby(["predictor", "family", "leg", "lag"])
        .agg(
            mean_corr=("corr", "mean"),
            min_corr=("corr", "min"),
            max_corr=("corr", "max"),
            n_days=("corr", "count"),
        )
        .reset_index()
    )
    g["sign_stable"] = (g["min_corr"] > 0) | (g["max_corr"] < 0)
    g["abs_mean"] = g["mean_corr"].abs()
    return g


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mid_tab = per_day_table("mid")
    ofi_tab = per_day_table("ofi")
    full = pd.concat([mid_tab, ofi_tab], ignore_index=True)
    full.to_csv(OUT / "leadlag_basket_ofi_full.csv", index=False)

    pooled = pool(full)
    pooled.to_csv(OUT / "leadlag_basket_ofi.csv", index=False)

    # Summary: top 15 sign-stable per predictor + comparison on best leg per family
    lines = []
    lines.append("# Basket-vs-leg lead-lag: mid vs OFI (LOO baskets)\n\n")
    lines.append(
        "Predictor: mid = basket Δmid_{t-L}. ofi = basket signed-volume_{t-L}. "
        "Target always Δmid_t. Basket excludes target leg (LOO). "
        f"Lags scanned: {list(LAGS)}. Sign-stability across days {list(DAYS)}.\n\n"
    )

    for pk in ("mid", "ofi"):
        sub = (
            pooled[(pooled["predictor"] == pk) & pooled["sign_stable"]]
            .sort_values("abs_mean", ascending=False)
            .head(15)
        )
        lines.append(f"## Top 15 sign-stable ({pk} predictor)\n\n")
        lines.append("| family | leg | lag | mean_corr | min | max |\n")
        lines.append("|---|---|---:|---:|---:|---:|\n")
        for _, r in sub.iterrows():
            short = r.leg.replace(r.family + "_", "")
            lines.append(
                f"| {r.family} | {short} | {int(r.lag)} | "
                f"{r.mean_corr:+.4f} | {r.min_corr:+.4f} | {r.max_corr:+.4f} |\n"
            )
        lines.append("\n")

    # Side-by-side: best lag per (family, leg) under each predictor
    best_per = (
        pooled.loc[pooled.groupby(["predictor", "family", "leg"])["abs_mean"].idxmax()]
        .copy()
    )
    pivot = best_per.pivot_table(
        index=["family", "leg"],
        columns="predictor",
        values=["mean_corr", "lag", "sign_stable"],
        aggfunc="first",
    )
    pivot.columns = [f"{a}_{b}" for a, b in pivot.columns]
    pivot = pivot.sort_values("mean_corr_ofi", key=lambda s: s.abs(), ascending=False)
    lines.append("## Side-by-side best-lag per leg (sorted by |OFI corr|)\n\n")
    lines.append(
        "| family | leg | mid_corr | mid_lag | mid_stable | ofi_corr | ofi_lag | ofi_stable | ofi/mid ratio |\n"
    )
    lines.append("|---|---|---:|---:|:---:|---:|---:|:---:|---:|\n")
    for (fam, leg), r in pivot.iterrows():
        short = leg.replace(fam + "_", "")
        mc, oc = r["mean_corr_mid"], r["mean_corr_ofi"]
        ratio = abs(oc) / abs(mc) if abs(mc) > 1e-6 else float("nan")
        lines.append(
            f"| {fam} | {short} | {mc:+.4f} | {int(r['lag_mid'])} | "
            f"{'Y' if r['sign_stable_mid'] else '-'} | "
            f"{oc:+.4f} | {int(r['lag_ofi'])} | "
            f"{'Y' if r['sign_stable_ofi'] else '-'} | "
            f"{ratio:.2f}x |\n"
        )

    (OUT / "leadlag_basket_ofi.md").write_text("".join(lines), encoding="utf-8")
    print(f"wrote {OUT / 'leadlag_basket_ofi_full.csv'}  ({len(full):,} rows)")
    print(f"wrote {OUT / 'leadlag_basket_ofi.csv'}  ({len(pooled):,} rows)")
    print(f"wrote {OUT / 'leadlag_basket_ofi.md'}")
    n_ofi_sig = int(((pooled.predictor == 'ofi') & pooled.sign_stable).sum())
    n_mid_sig = int(((pooled.predictor == 'mid') & pooled.sign_stable).sum())
    print(f"sign-stable count: mid={n_mid_sig}/250, ofi={n_ofi_sig}/250")


if __name__ == "__main__":
    main()
