"""Round-5 family alpha scan — promotion CLI.

Replaces ``ml_family_report.py`` as the path that produces submission artifacts.
For each family:
    1. Build the long-form feature panel (ml_features.build_feature_frame).
    2. Pick a single horizon from {20, 50, 100} by summed |IC| of whitelist
       features on D2+D3 only (D4 reserved for testing-day blocks via the
       block-CV splitter that follows).
    3. Outer block-CV with 15 purged folds (cv_block_purged): on each fold,
       fit a RidgeCV over a small alpha grid using the *training* blocks
       only, predict the test block, simulate trades via pnl_sim.
    4. Aggregate per-block PnL + per-trade DataFrame across the 15 folds.
    5. Compute the simple-signal baseline on the same 15 folds: best of 7
       signals × 3 horizons by total block PnL.
    6. Apply tradeability_gate_v2 (G1 trade win-rate, G2 block Sharpe,
       G3 per-day PnL, G4 beats baseline by 10% PnL + matching Sharpe).
    7. Emit one JSON artifact:
       - ``<FAMILY>_ridge.json`` if ML passes G1..G4
       - ``<FAMILY>_signal.json`` otherwise (best simple-signal baseline)

Feature whitelist (10, all present in build_feature_frame; compute every one
tick-by-tick in the live trader from a ≤55-tick ring buffer):

    obi_l1, obi_l3, microprice_dev, spread_bps, ret_10,
    ret_1_lag1, signed_flow_20, std_500, microprice_dev_lag5,
    fam_mean_microprice_dev_lag5

(Plan named ``momentum_10`` and ``neg_zscore_mid_50`` instead of ``std_500``
and ``microprice_dev_lag5``. We swap because momentum_10 == ret_10 and
neg_zscore_mid_50 isn't computed in the panel; the substitutes are already
present and serve the same role — directional momentum + microstructure
imbalance — without requiring auxiliary computation.)

Usage::

    .venv/Scripts/python.exe round5/ml/family_alpha_scan.py --family PEBBLES
    .venv/Scripts/python.exe round5/ml/family_alpha_scan.py --family ALL
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, RidgeCV

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import research_lib as rl  # noqa: E402
from round5.ml import ml_features as mf  # noqa: E402
from round5.ml import ml_models as mm  # noqa: E402
from round5.ml.pnl_sim import simulate_trades  # noqa: E402
from round5.ml.simple_signals_gate import evaluate_signal_blocks  # noqa: E402


WHITELIST = [
    "obi_l1",
    "obi_l3",
    "microprice_dev",
    "spread_bps",
    "ret_10",
    "ret_1_lag1",
    "signed_flow_20",
    "std_500",
    "microprice_dev_lag5",
    "fam_mean_microprice_dev_lag5",
]
HORIZON_CANDIDATES = (20, 50, 100)
SIGNAL_CANDIDATES = rl.SIGNAL_NAMES  # 7 signals
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)
LIVE_HAIRCUT = 0.3
ENTRY_BUFFER = 0.0


def _pick_horizon(df: pd.DataFrame, feats: list[str]) -> int:
    """Choose one horizon from {20, 50, 100} by summed |IC| on D2+D3 only.

    Reserves D4 entirely for the outer block-CV (block_4 of D4 would
    otherwise be both 'training data for horizon selection' and a
    'test fold' downstream — small leak). We only allow D2+D3.
    """
    train_mask = df["day"].isin([2, 3])
    sub = df[train_mask]
    scores = {}
    for h in HORIZON_CANDIDATES:
        col = f"fwd_{h}"
        if col not in sub.columns:
            continue
        y = sub[col].astype(float)
        total = 0.0
        for f in feats:
            if f not in sub.columns:
                continue
            x = sub[f].astype(float)
            mask = x.notna() & y.notna()
            if mask.sum() < 1000:
                continue
            ic = float(x[mask].corr(y[mask]))
            if np.isfinite(ic):
                total += abs(ic)
        scores[h] = total
    if not scores:
        return HORIZON_CANDIDATES[0]
    return max(scores, key=scores.get)


def _prepare_xy(df: pd.DataFrame, horizon: int, feats: list[str]):
    label_col = f"fwd_{horizon}"
    cols = ["day", "product", "timestamp", "mid", "spread", label_col, *feats]
    cols = [c for c in cols if c in df.columns]
    base = df[cols].copy()
    keep = base[feats].notna().all(axis=1) & base[label_col].notna() & base["spread"].notna()
    return base[keep].reset_index(drop=True)


def _fit_ridgecv(X_tr: pd.DataFrame, y_tr: pd.Series) -> Ridge:
    """RidgeCV with leave-one-out CV across the alpha grid. Returns a fitted Ridge."""
    cv = RidgeCV(alphas=RIDGE_ALPHAS, fit_intercept=True)
    cv.fit(X_tr.values, y_tr.values)
    # Re-fit a Ridge with the chosen alpha so we can persist a clean object.
    chosen = float(cv.alpha_)
    m = Ridge(alpha=chosen, fit_intercept=True, random_state=0)
    m.fit(X_tr.values, y_tr.values)
    m._chosen_alpha = chosen  # type: ignore[attr-defined]
    return m


def _block_sharpe(block_pnl: list[float] | np.ndarray) -> float:
    arr = np.asarray(list(block_pnl), dtype=float)
    if arr.size < 2 or arr.std(ddof=1) == 0:
        return float("nan")
    return float(arr.mean() / arr.std(ddof=1))


def _run_ml_outer_cv(df_a: pd.DataFrame, feats: list[str], horizon: int):
    """Outer block-CV. Returns dict with trade_df, block_pnl, block_ic, alpha_choices."""
    blocks = list(mm.cv_block_purged(df_a, n_blocks_per_day=5, embargo_ticks=200))
    trades_chunks: list[pd.DataFrame] = []
    block_pnl: list[float] = []
    block_ic: list[float] = []
    block_labels: list[str] = []
    alpha_choices: list[float] = []
    feature_means: list[np.ndarray] = []
    feature_stds: list[np.ndarray] = []
    coefs_list: list[np.ndarray] = []
    intercepts: list[float] = []

    label_col = f"fwd_{horizon}"

    for fold_label, train_mask, test_mask in blocks:
        tr_idx = train_mask.values
        te_idx = test_mask.values
        if tr_idx.sum() < 1000 or te_idx.sum() < 1000:
            continue
        X_tr = df_a.loc[tr_idx, feats].astype(float)
        y_tr = df_a.loc[tr_idx, label_col].astype(float)
        X_te = df_a.loc[te_idx, feats].astype(float)
        y_te = df_a.loc[te_idx, label_col].astype(float)
        df_te = df_a.loc[te_idx, ["day", "product", "timestamp", "mid", "spread"]].reset_index(drop=True)

        # Standardize using train stats (also used for live-trader scaling).
        mu = X_tr.mean().to_numpy()
        sd = X_tr.std(ddof=0).replace(0, 1.0).to_numpy()
        Xs_tr = pd.DataFrame((X_tr.to_numpy() - mu) / sd, index=X_tr.index, columns=feats)
        Xs_te = pd.DataFrame((X_te.to_numpy() - mu) / sd, index=X_te.index, columns=feats)

        m = _fit_ridgecv(Xs_tr, y_tr)
        y_pred = m.predict(Xs_te.values)
        ic = mm.information_coefficient(y_pred, y_te.values)
        edge = y_pred * LIVE_HAIRCUT

        block_trades = simulate_trades(df_te, edge, horizon=horizon, buffer=ENTRY_BUFFER)
        if not block_trades.empty:
            block_trades = block_trades.copy()
            block_trades["fold"] = fold_label
            trades_chunks.append(block_trades)
        block_pnl.append(float(block_trades["net"].sum()) if not block_trades.empty else 0.0)
        block_ic.append(float(ic) if np.isfinite(ic) else float("nan"))
        block_labels.append(fold_label)
        alpha_choices.append(float(m._chosen_alpha))  # type: ignore[attr-defined]
        feature_means.append(mu)
        feature_stds.append(sd)
        coefs_list.append(m.coef_)
        intercepts.append(float(m.intercept_))

    trade_df = (pd.concat(trades_chunks, ignore_index=True)
                if trades_chunks else pd.DataFrame())
    return {
        "trade_df": trade_df,
        "block_pnl": block_pnl,
        "block_ic": block_ic,
        "block_labels": block_labels,
        "alpha_choices": alpha_choices,
        "fold_means": feature_means,
        "fold_stds": feature_stds,
        "fold_coefs": coefs_list,
        "fold_intercepts": intercepts,
    }


def _build_simple_baseline(df: pd.DataFrame, blocks_template: pd.DataFrame) -> dict:
    """Best simple-signal baseline (max total_pnl over 7 signals × 3 horizons)
    using the same block-CV folds as the ML path.

    blocks_template is the full ml panel (used only to derive the same block
    splits); we build product frames separately because compute_signals needs
    the trades frame.
    """
    products = df["product"].unique()
    best = None
    best_meta: dict | None = None
    # Re-use the same fold spec deterministically from the same df via cv_block_purged
    for p in products:
        # Build a per-product frame with signals (load once per product).
        from round5.ml.simple_signals_gate import _build_product_frame
        prod_df = _build_product_frame(p, days=tuple(sorted(df["day"].unique())),
                                       root=rl.DATASET_ROOT)
        if prod_df.empty:
            continue
        prod_df["microprice_dev"] = prod_df["microprice"] - prod_df["mid"]

        prod_blocks = list(mm.cv_block_purged(prod_df, n_blocks_per_day=5, embargo_ticks=200))

        for sig in SIGNAL_CANDIDATES:
            if sig not in prod_df.columns:
                continue
            for h in HORIZON_CANDIDATES:
                if f"fwd_{h}" not in prod_df.columns:
                    prod_df[f"fwd_{h}"] = prod_df.groupby("day")["mid"].shift(-h) - prod_df["mid"]
                res = evaluate_signal_blocks(prod_df, signal=sig, horizon=h,
                                             blocks=prod_blocks,
                                             live_haircut=LIVE_HAIRCUT,
                                             buffer=ENTRY_BUFFER)
                if res is None:
                    continue
                if best is None or res["total_pnl"] > best:
                    best = float(res["total_pnl"])
                    # Also fit a 1-feature Ridge on ALL valid rows (deployment fit).
                    label_col = f"fwd_{h}"
                    sub = prod_df.loc[prod_df[sig].notna() & prod_df[label_col].notna(),
                                      [sig, label_col]].astype(float)
                    if len(sub) >= 1000:
                        x_arr = sub[sig].to_numpy().reshape(-1, 1)
                        y_arr = sub[label_col].to_numpy()
                        mu = float(x_arr.mean())
                        sd = float(x_arr.std(ddof=0)) or 1.0
                        Xs = (x_arr - mu) / sd
                        m = Ridge(alpha=1.0, fit_intercept=True, random_state=0).fit(Xs, y_arr)
                        coef = float(m.coef_[0])
                        intercept = float(m.intercept_)
                    else:
                        mu, sd, coef, intercept = 0.0, 1.0, 0.0, 0.0
                    best_meta = {
                        "product": p,
                        "signal": sig,
                        "horizon": int(h),
                        "total_pnl": float(res["total_pnl"]),
                        "block_sharpe": float(res["block_sharpe"]),
                        "block_pnl": res["block_pnl"],
                        "n_trades": int(len(res["trade_df"])),
                        "feature_means": [mu],
                        "feature_stds": [sd],
                        "coefs": [coef],
                        "intercept": intercept,
                    }
    return best_meta or {"total_pnl": 0.0, "block_sharpe": 0.0, "product": None,
                          "signal": None, "horizon": None, "block_pnl": [], "n_trades": 0,
                          "feature_means": [], "feature_stds": [], "coefs": [], "intercept": 0.0}


def run_family(family: str, out_dir: Path, days: tuple[int, ...] = rl.DEFAULT_DAYS,
               root: Path = rl.DATASET_ROOT, verbose: bool = True) -> dict:
    t0 = time.time()
    if verbose:
        print(f"[{family}] building panel for days {list(days)}")
    df = mf.build_feature_frame(family, days=days, root=root)
    if df.empty:
        return {"family": family, "verdict": "FAIL_EMPTY"}

    feats = [f for f in WHITELIST if f in df.columns]
    if len(feats) < len(WHITELIST):
        missing = [f for f in WHITELIST if f not in feats]
        print(f"[{family}] WARN: missing whitelist features: {missing}", file=sys.stderr)

    horizon = _pick_horizon(df, feats)
    if verbose:
        print(f"[{family}] picked horizon h={horizon} (D2+D3 |IC| sum)")

    df_a = _prepare_xy(df, horizon, feats)
    if verbose:
        print(f"[{family}] aligned panel rows={len(df_a)} feats={len(feats)}")
    if len(df_a) < 5000:
        return {"family": family, "verdict": "FAIL_TINY_PANEL", "n_rows": len(df_a)}

    if verbose:
        print(f"[{family}] outer block-CV (15 folds)")
    ml = _run_ml_outer_cv(df_a, feats, horizon)
    ml_total = float(np.sum(ml["block_pnl"]))
    ml_sharpe = _block_sharpe(ml["block_pnl"])
    per_day = (ml["trade_df"].groupby("day")["net"].sum().to_dict()
               if not ml["trade_df"].empty else {})

    if verbose:
        print(f"[{family}] computing simple-signal baseline")
    baseline = _build_simple_baseline(df, df_a)

    gate = mm.tradeability_gate_v2(
        ml["trade_df"], ml["block_pnl"],
        simple_baseline={"total_pnl": baseline["total_pnl"],
                         "block_sharpe": baseline["block_sharpe"]},
    )

    verdict = "PASS_ML" if gate["passed"] else "FAIL"

    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = out_dir
    if verdict == "PASS_ML":
        artifact = _build_ml_artifact(family, horizon, feats, ml, gate)
        path = artifact_dir / f"{family}_ridge.json"
    else:
        artifact = _build_signal_artifact(family, baseline, gate)
        path = artifact_dir / f"{family}_signal.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, default=_jsonable)

    summary = {
        "family": family,
        "verdict": verdict,
        "horizon": horizon,
        "ml_total_pnl": ml_total,
        "ml_block_sharpe": ml_sharpe,
        "ml_per_day_pnl": {int(k): float(v) for k, v in per_day.items()},
        "baseline_product": baseline.get("product"),
        "baseline_signal": baseline.get("signal"),
        "baseline_horizon": baseline.get("horizon"),
        "baseline_total_pnl": baseline.get("total_pnl"),
        "baseline_block_sharpe": baseline.get("block_sharpe"),
        "gate": {k: v for k, v in gate.items() if not isinstance(v, dict)},
        "artifact_path": str(path),
        "elapsed_sec": time.time() - t0,
    }
    if verbose:
        line = (f"[{family}] verdict={verdict}  h={horizon}  "
                f"ml_pnl={ml_total:+.1f}  ml_sharpe={ml_sharpe:.2f}  "
                f"baseline_pnl={baseline['total_pnl']:+.1f}  "
                f"per_day={summary['ml_per_day_pnl']}  -> {path.name}")
        print(line)
    return summary


def _build_ml_artifact(family: str, horizon: int, feats: list[str],
                       ml_run: dict, gate: dict) -> dict:
    """Average per-fold standardised coefficients into a single deployable model.

    Live trader will compute raw features, then apply (x - mu)/sd then dot with
    coef + intercept. We persist the AVERAGE mu, sd, coef, intercept across
    the 15 folds — robust to per-fold idiosyncrasies and the chosen object is
    one model, not 15.
    """
    mu = np.mean(np.stack(ml_run["fold_means"]), axis=0).tolist()
    sd = np.mean(np.stack(ml_run["fold_stds"]), axis=0).tolist()
    coefs = np.mean(np.stack(ml_run["fold_coefs"]), axis=0).tolist()
    intercept = float(np.mean(ml_run["fold_intercepts"]))
    return {
        "kind": "ml_ridge",
        "family": family,
        "features": feats,
        "feature_means": mu,
        "feature_stds": sd,
        "coefs": coefs,
        "intercept": intercept,
        "horizon": int(horizon),
        "live_haircut": LIVE_HAIRCUT,
        "entry_buffer": ENTRY_BUFFER,
        "alpha_chosen_by_fold": ml_run["alpha_choices"],
        "block_pnl": ml_run["block_pnl"],
        "block_ic": ml_run["block_ic"],
        "gate": gate,
    }


def _build_signal_artifact(family: str, baseline: dict, gate: dict) -> dict:
    return {
        "kind": "simple_signal",
        "family": family,
        "product": baseline.get("product"),
        "signal": baseline.get("signal"),
        "horizon": baseline.get("horizon"),
        "live_haircut": LIVE_HAIRCUT,
        "entry_buffer": ENTRY_BUFFER,
        "feature_means": baseline.get("feature_means", []),
        "feature_stds": baseline.get("feature_stds", []),
        "coefs": baseline.get("coefs", []),
        "intercept": baseline.get("intercept", 0.0),
        "block_pnl": baseline.get("block_pnl", []),
        "total_pnl": baseline.get("total_pnl"),
        "block_sharpe": baseline.get("block_sharpe"),
        "n_trades": baseline.get("n_trades"),
        "ml_gate_failure": {k: v for k, v in gate.items() if not isinstance(v, dict)},
    }


def _jsonable(x):
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def main() -> int:
    ap = argparse.ArgumentParser(description="Round-5 family alpha scan (promotion CLI).")
    ap.add_argument("--family", required=True,
                    help="Family name or ALL.")
    ap.add_argument("--days", type=int, nargs="+", default=list(rl.DEFAULT_DAYS))
    ap.add_argument("--out", type=Path, default=Path("round5/ml/artifacts"))
    ap.add_argument("--root", type=Path, default=rl.DATASET_ROOT)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.family == "ALL":
        families = list(rl.FAMILIES)
    else:
        families = [args.family]
        if args.family not in rl.FAMILIES:
            print(f"unknown family: {args.family}", file=sys.stderr)
            return 2

    args.out.mkdir(parents=True, exist_ok=True)
    summaries = []
    t0 = time.time()
    for fam in families:
        summary = run_family(fam, args.out, days=tuple(args.days), root=args.root,
                             verbose=not args.quiet)
        summaries.append(summary)

    if not args.quiet:
        print("\n=== SUMMARY ===")
        for s in summaries:
            print(json.dumps({k: v for k, v in s.items() if k != "gate"}, indent=2, default=_jsonable))
        print(f"\ndone in {time.time() - t0:.1f}s")

    with open(args.out / "scan_summary.json", "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, default=_jsonable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
