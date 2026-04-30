"""Hold-h-or-flip trade simulator for round-5 ML alpha gating.

Replaces the prior tick-by-tick `simulate_pnl` (which charged full spread per
tick) with a discrete trade simulator that:
  - opens at most one position per product (size = 1 unit)
  - pays half-spread on entry, half-spread on exit (round-trip = full spread)
  - holds until horizon `h` ticks elapse, OR predicted edge flips with
    sufficient magnitude, OR end-of-day forced flat
  - returns one row per round-trip with gross (mid-mid), cost (full spread),
    net (= pos·gross − cost), entry/exit timestamps and prices, exit reason.

Per-product, per-day independent simulation. Caller groups the trade-level
DataFrame by day / fold-block / product to aggregate PnL.

Public API
----------
simulate_trades(df, edge, horizon, position_limit=10, buffer=0.0) -> pd.DataFrame

Required df columns: day, product, timestamp, mid, spread.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

_REQUIRED_COLUMNS = ("day", "product", "timestamp", "mid", "spread")


def simulate_trades(
    df: pd.DataFrame,
    edge: Sequence[float],
    horizon: int,
    position_limit: int = 10,
    buffer: float = 0.0,
) -> pd.DataFrame:
    """Simulate hold-h-or-flip trades on a per-(product, day) basis.

    Parameters
    ----------
    df : DataFrame with columns day, product, timestamp, mid, spread.
        Sort order within (day, product) by timestamp is required; if not
        already sorted we re-sort defensively (cheap when already sorted).
    edge : array-like, same length as df, predicted forward return (mid-units).
    horizon : timeout in ticks (force flat after `horizon` bars held).
    position_limit : per-product cap on |pos|. Unit-trades only, so binding
        only as a safety check.
    buffer : extra threshold above half-spread before opening / flipping.

    Returns
    -------
    DataFrame with columns: product, day, entry_t, exit_t, side, entry_price,
    exit_price, gross, cost, net, bars_held, exit_reason
    ('flip' | 'timeout' | 'eod'). One row per round-trip. Empty if no trades.
    """
    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"simulate_trades: df missing columns {missing}")

    edge_arr = np.asarray(edge, dtype=float)
    if len(edge_arr) != len(df):
        raise ValueError(
            f"simulate_trades: edge length {len(edge_arr)} != df length {len(df)}"
        )

    if position_limit < 1:
        raise ValueError("position_limit must be >= 1")

    # Defensive sort + retain alignment of edge to df rows.
    work = df.assign(_edge=edge_arr).reset_index(drop=True)
    work = work.sort_values(["day", "product", "timestamp"], kind="mergesort").reset_index(drop=True)

    trades: list[dict] = []

    for (d, p), grp in work.groupby(["day", "product"], sort=False):
        mids = grp["mid"].to_numpy(dtype=float)
        spreads = grp["spread"].to_numpy(dtype=float)
        ts = grp["timestamp"].to_numpy()
        edges = grp["_edge"].to_numpy(dtype=float)
        n = len(grp)
        if n == 0:
            continue

        pos = 0
        entry_price = 0.0
        entry_t = None
        bars_held = 0
        last_valid_i = -1

        for i in range(n):
            mid = mids[i]
            spread = spreads[i]
            e = edges[i]
            if not (np.isfinite(mid) and np.isfinite(spread) and spread >= 0.0):
                continue
            last_valid_i = i
            half_sp = 0.5 * spread
            threshold = half_sp + buffer

            if pos == 0:
                if not np.isfinite(e):
                    continue
                if e > threshold:
                    pos = +1
                    entry_price = mid + half_sp
                    entry_t = ts[i]
                    bars_held = 0
                elif e < -threshold:
                    pos = -1
                    entry_price = mid - half_sp
                    entry_t = ts[i]
                    bars_held = 0
                # else: stay flat
                continue

            # pos != 0
            bars_held += 1
            flip = False
            if np.isfinite(e):
                if (np.sign(e) != np.sign(pos)) and (abs(e) > threshold):
                    flip = True
            timeout = bars_held >= horizon
            if not (flip or timeout):
                continue

            if pos == +1:
                exit_price = mid - half_sp
            else:
                exit_price = mid + half_sp
            net = (exit_price - entry_price) * pos
            cost = spread  # exit-tick spread snapshot; informational. `net` already reflects both crossings.
            gross = net + cost

            trades.append({
                "product": p,
                "day": int(d),
                "entry_t": entry_t,
                "exit_t": ts[i],
                "side": int(pos),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "gross": float(gross),
                "cost": float(cost),
                "net": float(net),
                "bars_held": int(bars_held),
                "exit_reason": "flip" if flip else "timeout",
            })

            pos = 0
            entry_t = None
            bars_held = 0

            if flip:
                new_side = +1 if e > 0 else -1
                pos = new_side
                entry_price = (mid + half_sp) if new_side == +1 else (mid - half_sp)
                entry_t = ts[i]
                bars_held = 0

            # safety clamp (single-unit trades never breach, but assert)
            if abs(pos) > position_limit:
                raise RuntimeError(f"position_limit {position_limit} breached: pos={pos}")

        # End-of-day forced flat
        if pos != 0 and entry_t is not None and last_valid_i >= 0:
            i = last_valid_i
            mid = mids[i]
            spread = spreads[i]
            half_sp = 0.5 * spread
            if pos == +1:
                exit_price = mid - half_sp
            else:
                exit_price = mid + half_sp
            net = (exit_price - entry_price) * pos
            cost = spread
            gross = net + cost
            trades.append({
                "product": p,
                "day": int(d),
                "entry_t": entry_t,
                "exit_t": ts[i],
                "side": int(pos),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "gross": float(gross),
                "cost": float(cost),
                "net": float(net),
                "bars_held": int(bars_held),
                "exit_reason": "eod",
            })

    return pd.DataFrame(trades)
