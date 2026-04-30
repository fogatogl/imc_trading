"""BLOCKING test — live trader edge must equal offline Ridge prediction.

For a generated trader (ML or simple-signal), this script:
  1. Loads the same D4 frame the scan saw via research_lib.
  2. Builds a stub TradingState per tick from the panel's order-book columns.
  3. Imports the generated trader module, replays ticks, captures the per-tick
     `predict_edge` value via a monkey-patched wrapper.
  4. Computes the offline edge directly from artifact (intercept + coef·(x-μ)/σ).
  5. Asserts max |live - offline| < tolerance after the warm-up window.

Fails LOUD before any submission. A mismatch means feature-formula drift —
the trader and the simulator are scoring different signals.

Usage::

    .venv/Scripts/python.exe round5/ml/tests/test_live_offline_equality.py \\
        --family PEBBLES --day 4 --tolerance 1e-4

For ML kind (10 features) the test exercises the full standardization +
dot-product chain. For simple-signal kind (1 feature) the test reduces to
validating the chosen signal column matches between offline and live.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prosperity4bt.datamodel import (  # noqa: E402
    Listing,
    Observation,
    OrderDepth,
    Trade,
    TradingState,
)

from round5 import research_lib as rl  # noqa: E402
from round5.ml.simple_signals_gate import _build_product_frame  # noqa: E402

WARMUP_TICKS = 60
DEFAULT_TOLERANCE = 1e-4


def _load_trader_module(family: str, strats_dir: Path):
    path = strats_dir / f"strat_ml_{family.lower()}.py"
    if not path.exists():
        raise FileNotFoundError(f"trader file not found: {path}")
    spec = importlib.util.spec_from_file_location(f"strat_ml_{family.lower()}", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _make_order_depth(row: pd.Series) -> OrderDepth:
    od = OrderDepth()
    for lvl in (1, 2, 3):
        bid_p = row.get(f"bid_price_{lvl}")
        bid_v = row.get(f"bid_volume_{lvl}")
        if pd.notna(bid_p) and pd.notna(bid_v) and float(bid_v) > 0:
            od.buy_orders[int(bid_p)] = int(bid_v)
        ask_p = row.get(f"ask_price_{lvl}")
        ask_v = row.get(f"ask_volume_{lvl}")
        if pd.notna(ask_p) and pd.notna(ask_v) and float(ask_v) > 0:
            od.sell_orders[int(ask_p)] = -int(ask_v)
    return od


def _trades_for_tick(tr_df: pd.DataFrame, day: int, ts: int, symbol: str) -> list[Trade]:
    sub = tr_df[(tr_df["day"] == day) & (tr_df["timestamp"] == ts)]
    out = []
    for _, r in sub.iterrows():
        out.append(Trade(symbol=symbol, price=int(r["price"]),
                          quantity=int(r["quantity"]),
                          buyer="", seller="", timestamp=int(ts)))
    return out


def _build_state(td_str: str, timestamp: int, products: list[str],
                 row_per_product: dict[str, pd.Series],
                 trades_per_product: dict[str, list[Trade]]) -> TradingState:
    listings = {p: Listing(symbol=p, product=p, denomination="") for p in products}
    depths = {p: _make_order_depth(row_per_product[p]) for p in products if p in row_per_product}
    own = {p: [] for p in products}
    mkt = {p: trades_per_product.get(p, []) for p in products}
    pos = {p: 0 for p in products}
    obs = Observation(plainValueObservations={}, conversionObservations={})
    return TradingState(
        traderData=td_str,
        timestamp=timestamp,
        listings=listings,
        order_depths=depths,
        own_trades=own,
        market_trades=mkt,
        position=pos,
        observations=obs,
    )


def run_equality_test(family: str, day: int, strats_dir: Path,
                      tolerance: float = DEFAULT_TOLERANCE) -> int:
    mod = _load_trader_module(family, strats_dir)
    artifact = mod.MODEL  # already a Python dict
    targets = mod.PRODUCT_TARGETS
    fam_products = mod.FAMILY_PRODUCTS

    # Load the same panel the scan saw, restricted to one day.
    per_prod_frames: dict[str, pd.DataFrame] = {}
    for p in fam_products:
        df = _build_product_frame(p, days=(day,), root=rl.DATASET_ROOT)
        if df.empty:
            print(f"WARN: empty panel for {p} on day {day}", file=sys.stderr)
            continue
        df["microprice_dev"] = df["microprice"] - df["mid"]
        per_prod_frames[p] = df.sort_values("timestamp").reset_index(drop=True)

    if not per_prod_frames:
        print("FAIL: no panels loaded", file=sys.stderr)
        return 2

    # Trades for signed_flow_20 reproduction.
    tr_per_prod: dict[str, pd.DataFrame] = {}
    for p in fam_products:
        tr = rl.load_trades(p, days=(day,), root=rl.DATASET_ROOT)
        tr_per_prod[p] = tr if not tr.empty else pd.DataFrame(columns=["day", "timestamp", "price", "quantity"])

    # Monkey-patch predict_edge to capture per-tick edges + features.
    captured: list[tuple[int, str, float, dict]] = []
    orig_predict_edge = mod.predict_edge

    def patched_predict_edge(features):
        e = orig_predict_edge(features)
        captured.append((-1, "_pending_", e, dict(features)))  # ts/sym filled below
        return e

    mod.predict_edge = patched_predict_edge

    trader = mod.Trader()
    td_str = ""
    common_ts = sorted(per_prod_frames[fam_products[0]]["timestamp"].unique())
    # Logger.flush prints to stdout each tick; redirect during replay so the
    # equality summary remains readable.
    sink = io.StringIO()
    redir = contextlib.redirect_stdout(sink)
    redir.__enter__()
    for ts in common_ts:
        rows = {}
        trades_local = {}
        for p in fam_products:
            df = per_prod_frames.get(p)
            if df is None:
                continue
            r = df[df["timestamp"] == ts]
            if r.empty:
                continue
            rows[p] = r.iloc[0]
            trades_local[p] = _trades_for_tick(tr_per_prod[p], day, int(ts), p)

        if not rows:
            continue
        before_n = len(captured)
        state = _build_state(td_str, int(ts), fam_products, rows, trades_local)
        _, _, td_str = trader.run(state)
        # Tag captured rows with timestamp + symbol (we know the order they were emitted).
        if len(captured) > before_n:
            order_idx = 0
            for sym in targets:
                if sym in rows:
                    if order_idx + before_n < len(captured):
                        ts_, sym_, e_, feats_ = captured[before_n + order_idx]
                        captured[before_n + order_idx] = (int(ts), sym, e_, feats_)
                        order_idx += 1

    redir.__exit__(None, None, None)

    if not captured:
        print("FAIL: no captured edges (warmup never satisfied?)", file=sys.stderr)
        return 3

    # Compute offline edges per (ts, symbol) and compare.
    # For simple-signal kind the only feature is artifact['signal']; for ML it's the 10 features.
    feature_names = list(artifact.get("features") or [artifact.get("signal")])
    mus = list(artifact.get("feature_means", [0.0]))
    sds = list(artifact.get("feature_stds", [1.0]))
    coefs = list(artifact.get("coefs", [0.0]))
    intercept = float(artifact.get("intercept", 0.0))

    rows_out = []
    for ts, sym, live_edge, live_feats in captured:
        if sym not in per_prod_frames:
            continue
        df = per_prod_frames[sym]
        match = df[df["timestamp"] == ts]
        if match.empty:
            continue
        row = match.iloc[0]
        offline_edge = intercept
        for i, fname in enumerate(feature_names):
            mu = mus[i] if i < len(mus) else 0.0
            sd = sds[i] if i < len(sds) and sds[i] != 0 else 1.0
            offline_val = float(row.get(fname, np.nan))
            offline_edge += coefs[i] * (offline_val - mu) / sd
        live_val = float(live_feats.get(feature_names[0], np.nan)) if feature_names else float("nan")
        offline_val_first = float(row.get(feature_names[0], np.nan))
        rows_out.append({
            "ts": ts, "sym": sym,
            "live_edge": live_edge, "offline_edge": offline_edge,
            "live_feat0": live_val, "offline_feat0": offline_val_first,
        })

    res = pd.DataFrame(rows_out)
    after_warmup = res.iloc[WARMUP_TICKS:].copy()
    if after_warmup.empty:
        print("FAIL: no rows after warmup window", file=sys.stderr)
        return 4

    diff_edge = (after_warmup["live_edge"] - after_warmup["offline_edge"]).abs()
    diff_feat = (after_warmup["live_feat0"] - after_warmup["offline_feat0"]).abs()
    max_edge_diff = float(diff_edge.max())
    max_feat_diff = float(diff_feat.max())
    median_edge_diff = float(diff_edge.median())

    print(f"family            : {family}")
    print(f"kind              : {artifact.get('kind')}")
    print(f"feature names     : {feature_names}")
    print(f"rows tested       : {len(after_warmup)}")
    print(f"max  edge diff    : {max_edge_diff:.6e}")
    print(f"med  edge diff    : {median_edge_diff:.6e}")
    print(f"max  feat[0] diff : {max_feat_diff:.6e}")

    if not np.isfinite(max_edge_diff):
        print("FAIL: non-finite edge difference", file=sys.stderr)
        return 5
    if max_edge_diff > tolerance:
        print(f"FAIL: max edge diff {max_edge_diff:.3e} > tolerance {tolerance}", file=sys.stderr)
        # write a diff csv for inspection
        diff_path = Path("round5/ml/tests/_equality_diff.csv")
        after_warmup.assign(diff_edge=diff_edge, diff_feat=diff_feat).to_csv(diff_path, index=False)
        print(f"wrote diff to {diff_path}", file=sys.stderr)
        return 1

    print("PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Live vs offline edge equality test (BLOCKING).")
    ap.add_argument("--family", required=True)
    ap.add_argument("--day", type=int, default=4)
    ap.add_argument("--strats-dir", type=Path, default=Path("round5/strats"))
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    args = ap.parse_args()
    return run_equality_test(args.family, args.day, args.strats_dir, args.tolerance)


if __name__ == "__main__":
    raise SystemExit(main())
