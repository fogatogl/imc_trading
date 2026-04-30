"""CLI for the round-5 per-family ML research pipeline.

Mirrors round5/family_report.py UX. Outputs land at round5/reports/<FAMILY>/ml/.

Usage::

    .venv/Scripts/python.exe round5/ml/ml_family_report.py \
        --family PEBBLES --target fwd_ret --horizon 20 50 100 --model ridge lgbm

    .venv/Scripts/python.exe round5/ml/ml_family_report.py \
        --family ALL --target fwd_ret toxic --horizon 50 100

For target='fwd_ret' the full 4-condition tradeability gate is applied.
For target='toxic' the gate is reported but typically fails condition 1 by
construction (binary scores are bounded [0,1], not in price units) — interpret
toxic-model outputs as a quality filter, not a directional alpha.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import research_lib as rl  # noqa: E402
from round5.ml import ml_features as mf  # noqa: E402
from round5.ml import ml_models as mm  # noqa: E402

DEFAULT_HORIZONS = (20, 50, 100)
DEFAULT_MODELS = ("ridge", "lgbm")


def _prepare_xy(df: pd.DataFrame, target: str, horizon: int):
    feats = mf.feature_columns(df)
    y = mf.build_labels(df, target=target, horizon=horizon)
    X = df[feats]
    keep = X.notna().all(axis=1) & y.notna()
    return X[keep], y[keep], df[keep], feats


def _run_one(target: str, horizon: int, model_name: str,
             df: pd.DataFrame, live_haircut: float,
             vol_gate_q: int, product_label: str):
    X, y, df_align, feats = _prepare_xy(df, target=target, horizon=horizon)
    fold_records = []
    pnl_records = []
    fi_records = []
    gate_records = []

    common = {
        "target": target, "horizon": horizon, "model": model_name,
        "product": product_label, "vol_gate_q": vol_gate_q,
    }

    folds = list(mm.cv_block_purged(df_align))
    headline_label = folds[-1][0] if folds else None  # last block of last day

    for fold_label, train_mask, test_mask in folds:
        train_mask = mm.apply_vol_gate(df_align, train_mask, vol_gate_q)
        tr_idx = train_mask.values
        te_idx = test_mask.values
        if tr_idx.sum() < 1000 or te_idx.sum() < 1000:
            continue
        X_tr, y_tr = X[tr_idx], y[tr_idx]
        X_te, y_te = X[te_idx], y[te_idx]
        df_te = df_align[te_idx].reset_index(drop=True)

        y_pred, model = mm.fit_predict(model_name, X_tr, y_tr, X_te)
        ic = mm.information_coefficient(y_pred, y_te.values)

        gate = mm.tradeability_gate(df_te, y_pred, horizon=horizon,
                                    live_haircut=live_haircut)

        fold_records.append({
            **common,
            "fold": fold_label, "n_train": int(tr_idx.sum()),
            "n_test": int(te_idx.sum()), "ic": ic,
            "median_edge_excess_half_spread": gate["cond1_median_excess"],
            "frac_edge_clears_half_spread": gate["cond1_frac_edge_clears_half_spread"],
            "passed_gate": gate["passed"],
        })

        for d, p in gate["cond3_per_day_pnl"].items():
            pnl_records.append({
                **common,
                "fold": fold_label, "day": d, "pnl": p,
                "ic_day": gate["cond2_per_day_ic"].get(d, float("nan")),
            })

        if fold_label == headline_label:
            fi = mm.feature_importance(model_name, model, feats)
            for k, v in common.items():
                fi[k] = v
            fi_records.append(fi)
            gate_records.append({**common, "fold": fold_label, "gate": gate})

    return fold_records, pnl_records, fi_records, gate_records


def _save_figures(out_dir: Path, metrics_df: pd.DataFrame, pnl_df: pd.DataFrame):
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    if not metrics_df.empty:
        plt.figure(figsize=(10, 4))
        # Median IC per (target, horizon, model) across the 15 block folds
        agg = metrics_df.groupby(["target", "horizon", "model"])["ic"].median().reset_index()
        if not agg.empty:
            labels = [f"{r['target']}\nh={int(r['horizon'])}\n{r['model']}"
                      for _, r in agg.iterrows()]
            plt.bar(labels, agg["ic"].values)
            plt.axhline(0, color="black", linewidth=0.5)
            plt.ylabel("median IC across block folds")
            plt.title("Block-CV median IC by (target, horizon, model)")
            plt.xticks(rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            plt.savefig(fig_dir / "ic_bars.png", dpi=110)
        plt.close("all")

    if not pnl_df.empty:
        plt.figure(figsize=(10, 4))
        # Sum block PnL by (target, horizon, model, day) across the 15 folds
        agg = pnl_df.groupby(["target", "horizon", "model", "day"])["pnl"].sum().reset_index()
        for (tgt, h, m), grp in agg.groupby(["target", "horizon", "model"]):
            label = f"{tgt} h={h} {m}"
            plt.bar([f"{label}\nD{int(d)}" for d in grp["day"]], grp["pnl"], label=label)
        plt.ylabel("summed block-CV PnL (mid-price units)")
        plt.title("Per-day summed simulated PnL — block-CV folds")
        plt.xticks(rotation=45, ha="right", fontsize=7)
        plt.tight_layout()
        plt.savefig(fig_dir / "per_day_pnl.png", dpi=110)
        plt.close("all")


def _write_gate_md(out_dir: Path, family: str, gate_records: list[dict],
                   metrics_df: pd.DataFrame, live_haircut: float):
    lines = [
        f"# {family} — ML Tradeability Gate",
        "",
        f"Live-haircut applied to predicted edge: **×{live_haircut:.2f}**",
        "",
        "Four gate conditions (all must pass):",
        "1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)",
        "2. Per-day positive IC (every fold day)",
        "3. Per-day positive simulated PnL (every day in fold)",
        "4. Trend-defense — worst PnL quintile is not the top |std_500| quintile",
        "",
        "Note: this CLI is exploratory only. Promotion gate is `family_alpha_scan.py`.",
        "Folds are block-purged intra-day (5 blocks/day × 3 days = 15 folds).",
        "Headline = last fold yielded (last block of last day).",
        "",
        "## Headline fold (last block)",
        "",
    ]
    for rec in gate_records:
        g = rec["gate"]
        verdict = "PASS" if g["passed"] else "FAIL"
        prod = rec.get("product", "POOLED")
        lines.append(
            f"### `{prod} | {rec['target']} h={rec['horizon']} {rec['model']}` — {verdict}"
        )
        lines.append("")
        lines.append(
            f"- C1 edge dominance: median_excess = `{g['cond1_median_excess']:.4f}`, "
            f"frac_clear = `{g['cond1_frac_edge_clears_half_spread']:.3f}` "
            f"(threshold {g['edge_clear_min_frac']}) → "
            f"{'PASS' if g['cond1_edge_dominance'] else 'FAIL'}"
        )
        ic_per_day = ", ".join(f"D{int(d)}={v:.4f}" for d, v in g["cond2_per_day_ic"].items())
        lines.append(
            f"- C2 per-day IC: {ic_per_day} → "
            f"{'PASS' if g['cond2_per_day_positive_ic'] else 'FAIL'}"
        )
        pnl_per_day = ", ".join(f"D{int(d)}={v:+.2f}" for d, v in g["cond3_per_day_pnl"].items())
        lines.append(
            f"- C3 per-day PnL: {pnl_per_day} → "
            f"{'PASS' if g['cond3_per_day_positive_pnl'] else 'FAIL'}"
        )
        if g["cond4_quintile_pnl"]:
            qpnl = ", ".join(f"q{q}={v:+.2f}" for q, v in g["cond4_quintile_pnl"].items())
            lines.append(
                f"- C4 vol-regime PnL: {qpnl} → "
                f"{'PASS' if g['cond4_trend_defense'] else 'FAIL — worst PnL in top trend quintile'}"
            )
        lines.append("")

    lines.append("## All folds (IC summary)")
    lines.append("")
    if not metrics_df.empty:
        group_cols = ["product", "target", "horizon", "model", "fold"] if "product" in metrics_df.columns \
            else ["target", "horizon", "model", "fold"]
        summary = metrics_df.groupby(group_cols)["ic"].mean().reset_index()
        for _, row in summary.iterrows():
            prod = row.get("product", "POOLED")
            lines.append(
                f"- `{prod} | {row['target']} h={int(row['horizon'])} {row['model']}` "
                f"[{row['fold']}]: IC = `{row['ic']:.4f}`"
            )

    (out_dir / "gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_family(family: str, targets: list[str], horizons: list[int],
               models: list[str], days: tuple[int, ...], out_root: Path,
               root: Path, live_haircut: float,
               per_product: bool = False, vol_gate_q: int = 5,
               verbose: bool = True):
    if verbose:
        print(f"[{family}] building feature frame for days {list(days)}")
    df = mf.build_feature_frame(family, days=days, root=root)
    if df.empty:
        print(f"[{family}] empty feature frame — skipping", file=sys.stderr)
        return
    if verbose:
        mode = "per-product" if per_product else "POOLED"
        gate_note = f" (vol-gate-q={vol_gate_q})" if vol_gate_q < 5 else ""
        print(f"[{family}] panel shape = {df.shape}, products = {df['product'].nunique()} | mode={mode}{gate_note}")

    suffix = "_per_product" if per_product else ""
    if vol_gate_q < 5:
        suffix += f"_volgate{vol_gate_q}"
    out_dir = out_root / family / ("ml" + suffix)
    out_dir.mkdir(parents=True, exist_ok=True)

    if per_product:
        product_iter = [(p, df[df["product"] == p].copy()) for p in sorted(df["product"].unique())]
    else:
        product_iter = [("POOLED", df)]

    all_metrics, all_pnl, all_fi, all_gates = [], [], [], []
    for prod_label, df_prod in product_iter:
        for target in targets:
            for h in horizons:
                for m in models:
                    if m == "lgbm" and not mm._HAS_LGBM:
                        print(f"[{family}] skipping lgbm — not installed", file=sys.stderr)
                        continue
                    if verbose:
                        t0 = time.time()
                        print(f"[{family}/{prod_label}] {target} h={h} {m} ...")
                    fr, pr, fi, gr = _run_one(target, h, m, df_prod, live_haircut,
                                              vol_gate_q=vol_gate_q,
                                              product_label=prod_label)
                    all_metrics.extend(fr)
                    all_pnl.extend(pr)
                    all_fi.extend(fi)
                    all_gates.extend(gr)
                    if verbose:
                        print(f"[{family}/{prod_label}]   done in {time.time() - t0:.1f}s, folds={len(fr)}")

    metrics_df = pd.DataFrame(all_metrics)
    pnl_df = pd.DataFrame(all_pnl)
    fi_df = pd.concat(all_fi, ignore_index=True) if all_fi else pd.DataFrame()

    metrics_df.to_csv(out_dir / "metrics.csv", index=False)
    pnl_df.to_csv(out_dir / "per_day_pnl.csv", index=False)
    if not fi_df.empty:
        fi_df.to_csv(out_dir / "feature_importance.csv", index=False)
    with open(out_dir / "gate_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_gates, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    _write_gate_md(out_dir, family, all_gates, metrics_df, live_haircut)
    _save_figures(out_dir, metrics_df, pnl_df)
    if verbose:
        print(f"[{family}] wrote {out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Round 5 per-family ML research pipeline.")
    ap.add_argument("--family", required=True,
                    help=f"Family name (one of {list(rl.FAMILIES)} or ALL).")
    ap.add_argument("--target", nargs="+", default=["fwd_ret"],
                    choices=["fwd_ret", "toxic"])
    ap.add_argument("--horizon", type=int, nargs="+", default=list(DEFAULT_HORIZONS))
    ap.add_argument("--model", nargs="+", default=list(DEFAULT_MODELS),
                    choices=["ridge", "lasso", "lgbm", "rf"])
    ap.add_argument("--days", type=int, nargs="+", default=list(rl.DEFAULT_DAYS))
    ap.add_argument("--live-haircut", type=float, default=0.3,
                    help="Multiply predicted edge by this before tradeability gate (default 0.3 — round-5 BT inflates ~10x).")
    ap.add_argument("--per-product", action="store_true",
                    help="Train one model per product (instead of pooled across the family).")
    ap.add_argument("--vol-gate-q", type=int, default=5,
                    help="Drop training rows above the q/5 percentile of std_500. 5=no-op (default), 4=drop top quintile.")
    ap.add_argument("--out", type=Path, default=Path("round5/reports"))
    ap.add_argument("--root", type=Path, default=rl.DATASET_ROOT)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    families = list(rl.FAMILIES) if args.family == "ALL" else [args.family]
    for fam in families:
        if fam not in rl.FAMILIES:
            print(f"unknown family: {fam}", file=sys.stderr)
            return 2

    t0 = time.time()
    for fam in families:
        run_family(fam, args.target, args.horizon, args.model,
                   tuple(args.days), args.out, args.root,
                   live_haircut=args.live_haircut,
                   per_product=args.per_product,
                   vol_gate_q=args.vol_gate_q,
                   verbose=not args.quiet)
    if not args.quiet:
        print(f"done. {len(families)} family report(s) in {time.time() - t0:.1f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
