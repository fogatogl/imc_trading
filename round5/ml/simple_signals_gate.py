"""Apples-to-apples gate test for the existing 7 simple signals.

Pipes ``research_lib.compute_signals`` output through the same 4-condition
``tradeability_gate`` used by the ML CLI, with a 1-feature Ridge calibrating
signal → predicted edge in price units. Per-product, per-signal, per-horizon.

Purpose: decide whether the ML CLI's complexity earns its keep. If a simple
signal already passes the gate where ML does, ML is redundant for that family.

Usage::

    .venv/Scripts/python.exe round5/ml/simple_signals_gate.py \
        --family PEBBLES --horizon 50 100

    .venv/Scripts/python.exe round5/ml/simple_signals_gate.py --family ALL
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import research_lib as rl  # noqa: E402
from round5.ml import ml_models as mm  # noqa: E402
from round5.ml.pnl_sim import simulate_trades  # noqa: E402

DEFAULT_HORIZONS = (50, 100)
EXTRA_FWD_HORIZONS = (20, 50)


def _build_product_frame(p: str, days: tuple[int, ...], root: Path) -> pd.DataFrame:
    """Per-product frame: microstructure-augmented px + signals + extra fwd horizons."""
    px = rl.load_prices(p, days=days, root=root)
    if px.empty:
        return pd.DataFrame()
    px = rl.add_microstructure(px)
    tr = rl.load_trades(p, days=days, root=root)
    px = rl.add_vwap(px, tr)
    sigs = rl.compute_signals(px, tr)
    out = pd.concat([px.reset_index(drop=True), sigs.reset_index(drop=True)], axis=1)
    # compute_signals returns obi_l1/obi_l3 that also live on px after add_microstructure;
    # drop duplicate column labels so downstream `df[col]` returns a Series, not a 2-col frame.
    out = out.loc[:, ~out.columns.duplicated()]
    # Add 20/50 forward horizons (research_lib only ships 1/10/100/1000)
    for h in EXTRA_FWD_HORIZONS:
        col = f"fwd_{h}"
        if col not in out.columns:
            out[col] = out.groupby("day")["mid"].shift(-h) - out["mid"]
    out["product"] = p
    return out


def evaluate_signal_blocks(
    df: pd.DataFrame,
    signal: str,
    horizon: int,
    blocks,
    live_haircut: float = 0.3,
    buffer: float = 0.0,
) -> dict | None:
    """Block-CV evaluation of a 1-feature Ridge calibrated on `signal`.

    Trains a 1-feature Ridge per fold, predicts the test block, simulates
    trades via `pnl_sim.simulate_trades`, and aggregates per-block PnL.

    Parameters
    ----------
    df : product-level frame containing `signal`, `mid`, `spread`, `day`,
        `timestamp`, `microprice_dev`, and `fwd_<horizon>` columns. Caller
        should also include `product` if multi-product (otherwise we tag
        a synthetic value internally).
    signal : column name of the single feature.
    horizon : forward-return horizon used as the supervised label and as the
        hold-h timeout for the trade simulator.
    blocks : iterable of (label, train_mask, test_mask) over `df` (e.g. from
        `ml_models.cv_block_purged`).
    live_haircut : multiplier applied to predicted edge before threshold gate.
    buffer : extra threshold above half-spread for trade entry.

    Returns
    -------
    dict with keys:
        trade_df       — pd.DataFrame of round-trips across all test blocks
        block_pnl      — list[float] per block (sum of `net`)
        block_ic       — list[float] Pearson IC per block
        block_labels   — list[str]
        total_pnl      — float
        block_sharpe   — float (mean / std with ddof=1; nan if <2 blocks or 0 std)
        n_train_total, n_test_total — int
    None when no fold satisfied the size threshold.
    """
    if signal not in df.columns:
        return None
    label_col = f"fwd_{horizon}"
    if label_col not in df.columns:
        return None
    if "product" not in df.columns:
        df = df.assign(product="_signal_baseline")

    needed = ["mid", "spread", signal, label_col, "day", "timestamp", "product"]
    base = df[[c for c in needed if c in df.columns]].copy()
    keep = (base[signal].notna()
            & base[label_col].notna()
            & base["spread"].notna()
            & base["mid"].notna())
    df_a = base[keep].reset_index(drop=True)
    if len(df_a) < 1000:
        return None

    X_full = df_a[[signal]].astype(float)
    y_full = df_a[label_col].astype(float)

    # Re-align block masks to the filtered frame: pass-through via index intersection.
    base_index_in_df = df.index[keep].to_numpy()
    pos_in_filtered = pd.Series(np.arange(len(df_a)), index=base_index_in_df)

    trades_chunks: list[pd.DataFrame] = []
    block_pnl: list[float] = []
    block_ic: list[float] = []
    block_labels: list[str] = []
    n_train_total = 0
    n_test_total = 0

    for fold_label, train_mask, test_mask in blocks:
        # Translate full-df masks -> positional indices in df_a.
        tr_pos = pos_in_filtered.reindex(df.index[train_mask & keep]).dropna().astype(int).values
        te_pos = pos_in_filtered.reindex(df.index[test_mask & keep]).dropna().astype(int).values
        if len(tr_pos) < 500 or len(te_pos) < 500:
            continue
        n_train_total += len(tr_pos)
        n_test_total += len(te_pos)
        X_tr = X_full.iloc[tr_pos]
        y_tr = y_full.iloc[tr_pos]
        X_te = X_full.iloc[te_pos]
        y_te = y_full.iloc[te_pos]

        y_pred, _ = mm.fit_predict("ridge", X_tr, y_tr, X_te)
        ic = mm.information_coefficient(y_pred, y_te.values)
        edge = y_pred * live_haircut

        df_te = df_a.iloc[te_pos].reset_index(drop=True)
        block_trades = simulate_trades(df_te, edge, horizon=horizon, buffer=buffer)
        if not block_trades.empty:
            block_trades = block_trades.copy()
            block_trades["fold"] = fold_label
            block_trades["signal"] = signal
            block_trades["horizon"] = horizon
            trades_chunks.append(block_trades)
        block_pnl.append(float(block_trades["net"].sum()) if not block_trades.empty else 0.0)
        block_ic.append(float(ic) if np.isfinite(ic) else float("nan"))
        block_labels.append(fold_label)

    if not block_pnl:
        return None

    trade_df = (pd.concat(trades_chunks, ignore_index=True)
                if trades_chunks else pd.DataFrame())
    bp_arr = np.asarray(block_pnl, dtype=float)
    if bp_arr.size >= 2 and bp_arr.std(ddof=1) > 0:
        block_sharpe = float(bp_arr.mean() / bp_arr.std(ddof=1))
    else:
        block_sharpe = float("nan")
    return {
        "trade_df": trade_df,
        "block_pnl": block_pnl,
        "block_ic": block_ic,
        "block_labels": block_labels,
        "total_pnl": float(bp_arr.sum()),
        "block_sharpe": block_sharpe,
        "n_train_total": n_train_total,
        "n_test_total": n_test_total,
    }


def _run_signal(df: pd.DataFrame, signal: str, horizon: int,
                live_haircut: float) -> dict | None:
    """Legacy single-fold (D2+D3 -> D4) wrapper kept for the standalone CLI.

    For new code that already has block-CV folds, call `evaluate_signal_blocks`
    directly with those folds — that is the path used by `family_alpha_scan`.
    """
    X = df[[signal]].astype(float)
    y = df[f"fwd_{horizon}"].astype(float)
    keep = X.notna().all(axis=1) & y.notna() & df["spread"].notna() & df["microprice_dev"].notna()
    df_a = df[keep]
    X_a = X[keep]
    y_a = y[keep]

    tr_mask = df_a["day"].isin([2, 3])
    te_mask = df_a["day"] == 4
    if tr_mask.sum() < 1000 or te_mask.sum() < 1000:
        return None

    y_pred, _ = mm.fit_predict("ridge", X_a[tr_mask.values], y_a[tr_mask.values], X_a[te_mask.values])
    df_te = df_a[te_mask.values].reset_index(drop=True)
    ic = mm.information_coefficient(y_pred, y_a[te_mask.values].values)
    gate = mm.tradeability_gate(df_te, y_pred, horizon=horizon, live_haircut=live_haircut)
    return {"ic": ic, "gate": gate, "n_train": int(tr_mask.sum()), "n_test": int(te_mask.sum())}


def run_family(family: str, horizons: tuple[int, ...],
               days: tuple[int, ...], out_root: Path, root: Path,
               live_haircut: float, verbose: bool = True):
    out_dir = out_root / family / "simple_signals_gate"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    gate_rows = []
    products = rl.family_products(family)
    if verbose:
        print(f"[{family}] {len(products)} products × {len(rl.SIGNAL_NAMES)} signals × {len(horizons)} horizons")

    for p in products:
        if verbose:
            t0 = time.time()
        df = _build_product_frame(p, days, root)
        if df.empty:
            continue
        df["microprice_dev"] = df["microprice"] - df["mid"]
        for signal in rl.SIGNAL_NAMES:
            if signal not in df.columns:
                continue
            for h in horizons:
                res = _run_signal(df, signal, h, live_haircut)
                if res is None:
                    continue
                g = res["gate"]
                rows.append({
                    "product": p, "signal": signal, "horizon": h,
                    "fold": "D2+D3->D4",
                    "n_train": res["n_train"], "n_test": res["n_test"],
                    "ic": res["ic"],
                    "median_edge_excess_half_spread": g["cond1_median_excess"],
                    "frac_edge_clears_half_spread": g["cond1_frac_edge_clears_half_spread"],
                    "passed_gate": g["passed"],
                    "cond1": g["cond1_edge_dominance"],
                    "cond2": g["cond2_per_day_positive_ic"],
                    "cond3": g["cond3_per_day_positive_pnl"],
                    "cond4": g["cond4_trend_defense"],
                })
                gate_rows.append({"product": p, "signal": signal, "horizon": h, "gate": g, "ic": res["ic"]})
        if verbose:
            print(f"[{family}/{p}]   {time.time() - t0:.1f}s")

    metrics = pd.DataFrame(rows)
    metrics.to_csv(out_dir / "metrics.csv", index=False)

    # Markdown — only PASSING combos plus a summary table
    lines = [
        f"# {family} — Simple-Signal Gate Test",
        "",
        f"Live-haircut applied: ×{live_haircut:.2f}",
        f"Each signal feeds a 1-feature Ridge calibrating edge in price units.",
        "",
        "## Passes (all 4 conditions)",
        "",
    ]
    passed = metrics[metrics["passed_gate"]] if not metrics.empty else metrics
    if passed.empty:
        lines.append("_None._")
    else:
        for _, row in passed.iterrows():
            lines.append(
                f"- `{row['product']} | {row['signal']} | h={int(row['horizon'])}`: "
                f"IC=`{row['ic']:.4f}`, edge_clear=`{row['frac_edge_clears_half_spread']:.3f}`, "
                f"median_excess=`{row['median_edge_excess_half_spread']:+.3f}`"
            )

    lines += ["", "## Per-condition pass-rate", ""]
    if not metrics.empty:
        for c in ["cond1", "cond2", "cond3", "cond4"]:
            rate = float(metrics[c].mean()) if c in metrics else 0.0
            lines.append(f"- {c}: {rate * 100:.1f}% pass ({int(metrics[c].sum())} / {len(metrics)})")
    lines += ["", "## All combos (IC ranked)", ""]
    if not metrics.empty:
        ranked = metrics.sort_values("ic", ascending=False).head(30)
        for _, row in ranked.iterrows():
            lines.append(
                f"- `{row['product']} | {row['signal']} | h={int(row['horizon'])}`: "
                f"IC=`{row['ic']:+.4f}`, gate={'PASS' if row['passed_gate'] else 'FAIL'}, "
                f"frac_clear=`{row['frac_edge_clears_half_spread']:.3f}`"
            )

    (out_dir / "gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if verbose:
        print(f"[{family}] wrote {out_dir} ({len(metrics)} combos, {len(passed)} PASS)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Round 5 simple-signal apples-to-apples gate test.")
    ap.add_argument("--family", required=True)
    ap.add_argument("--horizon", type=int, nargs="+", default=list(DEFAULT_HORIZONS))
    ap.add_argument("--days", type=int, nargs="+", default=list(rl.DEFAULT_DAYS))
    ap.add_argument("--live-haircut", type=float, default=0.3)
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
        run_family(fam, tuple(args.horizon), tuple(args.days), args.out,
                   args.root, live_haircut=args.live_haircut, verbose=not args.quiet)
    if not args.quiet:
        print(f"done. {len(families)} family(ies) in {time.time() - t0:.1f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
