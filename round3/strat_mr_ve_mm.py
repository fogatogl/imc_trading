"""Phase 6b: VELVETFRUIT_EXTRACT market-maker with MR-driven directional skew.

Inspired by last year's "lightweight EMA-based model" (round3_old_strategy.md).
Posts both sides of VE every tick like the v7 MM, but the quote midpoint and
size skew tilt with the EMA-deviation z-score:

  - z > 0  (mid is rich)  → quote tighter on the ask, wider on the bid;
                             also reduce buy size, increase sell size.
  - z < 0  (mid is cheap) → mirror.

When |z| > AGGR_Z, switch to take-style behaviour: lift the offer when cheap,
hit the bid when rich, with size scaled to z.

Critically: this *combines* MM (mean-reverting around 0 by default) with MR
(directional bias from EMA deviation). v7 MM on VE alone makes +6.2k/3d; with
MR overlay we expect substantially more.
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import json
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
VE_LIMIT = 200

# MR signal
HL_TICKS = 200
DEV_WINDOW = 3000
WARMUP_TICKS = 2000
ALPHA = 1.0 - 0.5 ** (1.0 / HL_TICKS)

# Skew / aggression thresholds
SKEW_Z = 0.5               # below this z, run plain MM with inv skew only.
AGGR_Z = 1.5               # above this z, take aggressively.
MAX_Z = 3.0

# MM params (v7 baseline)
QUOTE_SIZE = 25
INV_MAX_SKEW = 2
OF_THRESH = 1.5
OF_EXTREME = 5.0
SKEW_SHRINK = 0.3


class Trader:
    def __init__(self):
        self._ema: float | None = None
        self._dev_buf: list[float] = []
        self._t_seen = 0
        self._prev_bv = [0, 0, 0]
        self._prev_av = [0, 0, 0]

    def _signal(self, mid: float) -> tuple[float, float]:
        if self._ema is None:
            self._ema = mid
        else:
            self._ema = ALPHA * mid + (1.0 - ALPHA) * self._ema
        dev = mid - self._ema
        self._dev_buf.append(dev)
        if len(self._dev_buf) > DEV_WINDOW:
            del self._dev_buf[0 : len(self._dev_buf) - DEV_WINDOW]
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
        if ve_od is None or not ve_od.buy_orders or not ve_od.sell_orders:
            return result, 0, json.dumps(mem)
        bs_ = sorted(ve_od.buy_orders.items(), key=lambda kv: -kv[0])
        as_ = sorted(ve_od.sell_orders.items(), key=lambda kv: kv[0])
        best_bid = bs_[0][0]
        best_ask = as_[0][0]
        best_bid_sz = bs_[0][1]
        best_ask_sz = abs(as_[0][1])
        mid = 0.5 * (best_bid + best_ask)
        pos = state.position.get(VE, 0)

        dev, sd = self._signal(mid)
        self._t_seen += 1
        z = dev / sd if self._t_seen >= WARMUP_TICKS else 0.0

        # Order-flow direction (v7 logic).
        cur_bv = [abs(bs_[i][1]) if i < len(bs_) else 0 for i in range(3)]
        cur_av = [abs(as_[i][1]) if i < len(as_) else 0 for i in range(3)]
        of_dir = (sum(c - p for c, p in zip(cur_bv, self._prev_bv))
                  - sum(c - p for c, p in zip(cur_av, self._prev_av)))
        self._prev_bv = cur_bv
        self._prev_av = cur_av

        orders: List[Order] = []

        # Standard MM with MR-driven skew (no aggressive take — bid-ask bounce
        # can produce extreme z spuriously).
        if best_ask - best_bid >= 2:
            inv_skew = round(-INV_MAX_SKEW * (pos / VE_LIMIT))
            mr_skew = -int(round(z))           # rich → quote lower (negative skew).
            mr_skew = max(-2, min(2, mr_skew))
            total_skew = inv_skew + mr_skew

            our_bid = best_bid + 1 + total_skew
            our_ask = best_ask - 1 + total_skew
            if our_bid >= our_ask:
                if total_skew > 0:
                    our_bid = our_ask - 1
                else:
                    our_ask = our_bid + 1

            bsz = asz = QUOTE_SIZE
            # OF size-skew (v7).
            if of_dir >= OF_THRESH:
                bsz = int(QUOTE_SIZE * SKEW_SHRINK)
            if of_dir <= -OF_THRESH:
                asz = int(QUOTE_SIZE * SKEW_SHRINK)
            if of_dir >= OF_EXTREME:
                bsz = 0
            if of_dir <= -OF_EXTREME:
                asz = 0
            # MR size-skew: cheap (z<0) → buy bigger / ask smaller; rich → opposite.
            if z < -SKEW_Z:
                bsz = int(bsz * 1.5)
                asz = int(asz * 0.6)
            elif z > SKEW_Z:
                bsz = int(bsz * 0.6)
                asz = int(asz * 1.5)

            bsz = min(bsz, VE_LIMIT - pos)
            asz = min(asz, VE_LIMIT + pos)
            if bsz > 0:
                orders.append(Order(VE, int(our_bid), int(bsz)))
            if asz > 0:
                orders.append(Order(VE, int(our_ask), -int(asz)))

        if orders:
            result[VE] = orders
        return result, 0, json.dumps(mem)
