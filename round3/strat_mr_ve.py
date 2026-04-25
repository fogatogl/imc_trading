"""Phase 6: mean-reversion on VELVETFRUIT_EXTRACT (the underlying).

The notebook's "VE has only bid-ask bounce, no real MR" conclusion came from
looking at lag-1 autocorrelation alone. At 100–500-tick subsampling, AC1 jumps
back to a strongly negative −0.20 to −0.52 across the 3 days — that is real
mean reversion at the multi-tick scale, not bounce.

Strategy:
  1. Maintain an EMA of VE mid with half-life HL ticks.
  2. Maintain a rolling std of (mid − EMA) over a 5,000-tick window.
  3. Target VE position = − round( clip(z, ±MAX_Z) / MAX_Z * VE_LIMIT )  where
     z = (mid − EMA) / std. Sells when price is rich, buys when cheap.
  4. Drive position toward target via passive quotes at best_bid+1 / best_ask−1;
     hard-cross only when the gap exceeds HARD_BAND.

This is the clean standalone MR baseline — no options, no hedge layer. Layered
versions follow in `strat_layered_mr.py`.
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import json
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
VE_LIMIT = 200
MAX_POS = 200              # use full VE position budget; no other VE consumer here.
HL_TICKS = 200             # short EMA — sim shows |AC1| peaks around this scale.
DEV_WINDOW = 3000
MAX_Z = 2.0
DEAD_ZONE = 0.5
SOFT_BAND = 2
HARD_BAND = 200            # passive only (hard-cross is too expensive on VE).
ENTRY_CHUNK = 200          # large chunks: post the full target gap as one passive order.
WARMUP_TICKS = 2000
ALPHA = 1.0 - 0.5 ** (1.0 / HL_TICKS)


class Trader:
    def __init__(self):
        self._ema: float | None = None
        self._dev_buf: list[float] = []
        self._t_seen = 0

    def _update(self, mid: float) -> tuple[float, float]:
        if self._ema is None:
            self._ema = mid
        else:
            self._ema = ALPHA * mid + (1.0 - ALPHA) * self._ema
        dev = mid - self._ema
        self._dev_buf.append(dev)
        if len(self._dev_buf) > DEV_WINDOW:
            del self._dev_buf[0 : len(self._dev_buf) - DEV_WINDOW]
        # population std of devs.
        n = len(self._dev_buf)
        m = sum(self._dev_buf) / n
        var = sum((x - m) ** 2 for x in self._dev_buf) / n
        sd = max(0.5, var ** 0.5)
        return dev, sd

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}

        ve_od = state.order_depths.get(VE)
        if ve_od is None:
            return result, 0, json.dumps(mem)
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = ol.best_bid_ask(ve_od)
        if ve_bid is None:
            return result, 0, json.dumps(mem)
        mid = 0.5 * (ve_bid + ve_ask)
        dev, sd = self._update(mid)
        self._t_seen += 1

        if self._t_seen < WARMUP_TICKS:
            return result, 0, json.dumps(mem)

        z = dev / sd
        # short when rich (positive z), long when cheap (negative z).
        if abs(z) < DEAD_ZONE:
            target = 0
        else:
            zc = max(-MAX_Z, min(MAX_Z, z))
            target = -int(round(zc / MAX_Z * MAX_POS))

        cur = state.position.get(VE, 0)
        gap = target - cur
        if abs(gap) <= SOFT_BAND:
            return result, 0, json.dumps(mem)

        hard_cross = abs(gap) > HARD_BAND
        if gap > 0:
            price = ve_ask if hard_cross else ve_bid + 1
            qty = min(gap, ENTRY_CHUNK, VE_LIMIT - cur)
            if hard_cross:
                qty = min(qty, ve_ask_sz if ve_ask_sz > 0 else qty)
            if qty > 0:
                result[VE] = [Order(VE, price, qty)]
        else:
            price = ve_bid if hard_cross else ve_ask - 1
            qty = min(-gap, ENTRY_CHUNK, VE_LIMIT + cur)
            if hard_cross:
                qty = min(qty, ve_bid_sz if ve_bid_sz > 0 else qty)
            if qty > 0:
                result[VE] = [Order(VE, price, -qty)]

        return result, 0, json.dumps(mem)
