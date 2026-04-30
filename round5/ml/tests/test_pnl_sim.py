"""Unit tests for round5.ml.pnl_sim.simulate_trades.

Run:
    .venv/Scripts/python.exe -m pytest round5/ml/tests/test_pnl_sim.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5.ml.pnl_sim import simulate_trades  # noqa: E402


def _make_df(mids, spreads, day=2, product="P"):
    n = len(mids)
    return pd.DataFrame({
        "day": [day] * n,
        "product": [product] * n,
        "timestamp": list(range(n)),
        "mid": np.asarray(mids, dtype=float),
        "spread": np.asarray(spreads, dtype=float),
    })


def test_zero_edge_no_trades():
    df = _make_df(mids=[100.0] * 50, spreads=[1.0] * 50)
    edge = np.zeros(50)
    out = simulate_trades(df, edge, horizon=10)
    assert len(out) == 0


def test_long_timeout_breakeven_minus_spread():
    """Constant mid, spread=1, perpetual long edge -> long opens, holds h ticks,
    closes at timeout. PnL should be -1 (full spread cost), gross 0, cost 1."""
    df = _make_df(mids=[100.0] * 30, spreads=[1.0] * 30)
    edge = np.full(30, 5.0)  # well above half_spread = 0.5
    out = simulate_trades(df, edge, horizon=10)
    # First trade opens at i=0 (entry 100.5), times out at i=10 (exit 99.5), bars_held=10.
    # net = (99.5 - 100.5) * (+1) = -1.0
    assert len(out) >= 1
    first = out.iloc[0]
    assert first["side"] == 1
    assert first["bars_held"] == 10
    assert first["exit_reason"] == "timeout"
    np.testing.assert_allclose(first["net"], -1.0)
    np.testing.assert_allclose(first["cost"], 1.0)
    np.testing.assert_allclose(first["gross"], 0.0)


def test_short_timeout_symmetric():
    df = _make_df(mids=[100.0] * 30, spreads=[1.0] * 30)
    edge = np.full(30, -5.0)
    out = simulate_trades(df, edge, horizon=10)
    first = out.iloc[0]
    assert first["side"] == -1
    np.testing.assert_allclose(first["net"], -1.0)


def test_long_profitable_when_mid_rises():
    """Mid rises by 5 ticks over horizon=10. spread=1. Long should net +5 - 1 = +4."""
    mids = [100.0 + 0.5 * i for i in range(30)]  # +0.5/tick
    df = _make_df(mids=mids, spreads=[1.0] * 30)
    edge = np.full(30, 5.0)
    out = simulate_trades(df, edge, horizon=10)
    first = out.iloc[0]
    # entry at i=0: entry_price = 100 + 0.5 = 100.5
    # exit at i=10: mid = 105.0, exit_price = 104.5
    # net = (104.5 - 100.5) * 1 = +4.0
    np.testing.assert_allclose(first["net"], 4.0)
    np.testing.assert_allclose(first["gross"], 5.0)
    np.testing.assert_allclose(first["cost"], 1.0)


def test_flip_then_reentry_short():
    """Edge starts +5 (long), flips to -5 within horizon -> close long, open short.

    Walk: i=0 long opens; i=5 flip closes long (net -1) and opens short; i=25
    short times out (bars_held=20, net -1); i=26 opens fresh short; EOD at i=29
    forces flat (net -1). Three trades total.
    """
    mids = [100.0] * 30
    df = _make_df(mids=mids, spreads=[1.0] * 30)
    edge = np.array([5.0] * 5 + [-5.0] * 25)
    out = simulate_trades(df, edge, horizon=20)
    assert len(out) == 3
    long_close, short_timeout, short_eod = out.iloc[0], out.iloc[1], out.iloc[2]
    assert long_close["exit_reason"] == "flip"
    assert long_close["side"] == 1
    np.testing.assert_allclose(long_close["net"], -1.0)
    assert short_timeout["side"] == -1
    assert short_timeout["exit_reason"] == "timeout"
    np.testing.assert_allclose(short_timeout["net"], -1.0)
    assert short_eod["side"] == -1
    assert short_eod["exit_reason"] == "eod"
    np.testing.assert_allclose(short_eod["net"], -1.0)


def test_eod_force_close():
    """Open long late in the day; edge stays positive; horizon never hits -> EOD close."""
    df = _make_df(mids=[100.0] * 8, spreads=[1.0] * 8)
    edge = np.array([0.0] * 5 + [5.0] * 3)
    out = simulate_trades(df, edge, horizon=20)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["exit_reason"] == "eod"
    assert row["side"] == 1
    np.testing.assert_allclose(row["net"], -1.0)


def test_per_product_independence():
    """Two products on same day -> independent position state."""
    df1 = _make_df([100.0] * 30, [1.0] * 30, day=2, product="A")
    df2 = _make_df([200.0] * 30, [2.0] * 30, day=2, product="B")
    df = pd.concat([df1, df2], ignore_index=True)
    edge = np.concatenate([np.full(30, 5.0), np.full(30, -5.0)])
    out = simulate_trades(df, edge, horizon=10)
    a = out[out["product"] == "A"]
    b = out[out["product"] == "B"]
    assert (a["side"] == 1).all()
    assert (b["side"] == -1).all()
    # A net = -1 (spread=1); B net = -2 (spread=2 each round-trip)
    np.testing.assert_allclose(a.iloc[0]["net"], -1.0)
    np.testing.assert_allclose(b.iloc[0]["net"], -2.0)


def test_multi_day_independence():
    """Position resets across days (EOD forced flat in one, fresh open in next)."""
    df1 = _make_df([100.0] * 8, [1.0] * 8, day=2, product="X")
    df2 = _make_df([100.0] * 8, [1.0] * 8, day=3, product="X")
    df = pd.concat([df1, df2], ignore_index=True)
    edge = np.full(16, 5.0)
    out = simulate_trades(df, edge, horizon=20)
    # Day 2: opens at i=0, no timeout (h=20 > 8) -> EOD close. Day 3: same.
    assert len(out) == 2
    assert (out["exit_reason"] == "eod").all()
    assert sorted(out["day"].tolist()) == [2, 3]


def test_buffer_suppresses_marginal_signals():
    df = _make_df([100.0] * 30, [1.0] * 30)  # half_spread = 0.5
    edge = np.full(30, 0.6)  # only 0.1 above half_spread
    out_no_buffer = simulate_trades(df, edge, horizon=10, buffer=0.0)
    out_with_buffer = simulate_trades(df, edge, horizon=10, buffer=0.2)
    assert len(out_no_buffer) >= 1
    assert len(out_with_buffer) == 0


def test_length_mismatch_raises():
    df = _make_df([100.0] * 5, [1.0] * 5)
    edge = np.zeros(4)
    try:
        simulate_trades(df, edge, horizon=10)
    except ValueError as e:
        assert "edge length" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_missing_columns_raises():
    df = pd.DataFrame({"day": [2], "timestamp": [0], "mid": [100.0]})
    try:
        simulate_trades(df, [0.0], horizon=10)
    except KeyError as e:
        assert "missing columns" in str(e)
    else:
        raise AssertionError("expected KeyError")


if __name__ == "__main__":
    # Fallback runner — pytest not always installed in the .venv.
    import inspect

    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{failed} failure(s)")
    raise SystemExit(failed)
