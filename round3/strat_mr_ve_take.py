"""Phase 6d: aggressive-take MR on VE with size scaling.

When |z| > entry threshold, *take* the resting order book up to a size scaled
with conviction. Exit by either crossing back or by the natural mean reversion
flipping z's sign.

Two timescales for robustness:
  - Fast EMA (HL=200) drives entry/exit signal.
  - Slow EMA (HL=2000) provides a regime filter: only take in the direction the
    slow EMA confirms (i.e. only buy if price is below BOTH fast and slow EMAs;
    avoids trading against an intraday drift).
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import json
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
VE_LIMIT = 200

HL_FAST = 200
HL_SLOW = 2000
DEV_WINDOW = 3000
WARMUP_TICKS = 2000
ALPHA_FAST = 1.0 - 0.5 ** (1.0 / HL_FAST)
ALPHA_SLOW = 1.0 - 0.5 ** (1.0 / HL_SLOW)

ENTRY_Z = 1.0          # take when |z| > 1.0 sigma.
MAX_Z = 3.0
TAKE_CHUNK_PER_TICK = 50   # cap per-tick aggressive crossing.


class Trader:
    def __init__(self):
        self._ema_f: float | None = None
        self._ema_s: float | None = None
        self._dev_buf: list[float] = []
        self._t_seen = 0

    def _signal(self, mid: float) -> tuple[float, float, float]:
        if self._ema_f is None:
            self._ema_f = mid
            self._ema_s = mid
        else:
            self._ema_f = ALPHA_FAST * mid + (1.0 - ALPHA_FAST) * self._ema_f
            self._ema_s = ALPHA_SLOW * mid + (1.0 - ALPHA_SLOW) * self._ema_s
        dev = mid - self._ema_f
        self._dev_buf.append(dev)
        if len(self._dev_buf) > DEV_WINDOW:
            del self._dev_buf[0 : len(self._dev_buf) - DEV_WINDOW]
        n = len(self._dev_buf)
        m = sum(self._dev_buf) / n
        var = sum((x - m) ** 2 for x in self._dev_buf) / n
        sd = max(0.5, var ** 0.5)
        return dev, sd, mid - self._ema_s

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}

        ve_od = state.order_depths.get(VE)
        if ve_od is None or not ve_od.buy_orders or not ve_od.sell_orders:
            return result, 0, json.dumps(mem)
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = ol.best_bid_ask(ve_od)
        if ve_bid is None:
            return result, 0, json.dumps(mem)
        mid = 0.5 * (ve_bid + ve_ask)
        dev, sd, dev_slow = self._signal(mid)
        self._t_seen += 1
        if self._t_seen < WARMUP_TICKS:
            return result, 0, json.dumps(mem)

        z = dev / sd
        pos = state.position.get(VE, 0)

        # Regime filter: trade only when fast and slow signals agree.
        if abs(z) < ENTRY_Z:
            return result, 0, json.dumps(mem)
        if dev * dev_slow < 0:
            # fast and slow disagree → no trade (drift is shifting).
            return result, 0, json.dumps(mem)

        zc = max(-MAX_Z, min(MAX_Z, z))
        target = -int(round(zc / MAX_Z * VE_LIMIT))
        gap = target - pos
        if gap == 0:
            return result, 0, json.dumps(mem)

        if gap > 0:
            qty = min(gap, ve_ask_sz, TAKE_CHUNK_PER_TICK, VE_LIMIT - pos)
            if qty > 0:
                result[VE] = [Order(VE, ve_ask, qty)]
        else:
            qty = min(-gap, ve_bid_sz, TAKE_CHUNK_PER_TICK, VE_LIMIT + pos)
            if qty > 0:
                result[VE] = [Order(VE, ve_bid, -qty)]

        return result, 0, json.dumps(mem)
