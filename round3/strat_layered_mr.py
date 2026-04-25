"""Phase 6c: layered MM + MR on VE, no options carry.

Drops the gamma carry (so VE is no longer needed as a delta hedge) and
dedicates the VE position budget to the EMA-deviation mean-reversion signal,
implemented as a market-maker with MR-driven quote skew.

Layers (all on disjoint products, so PnLs are additive):
  - HYDROGEL_PACK : v7 MM                           (+26.2k)
  - VEV_4000      : v7 MM                           (+8.8k)
  - VE            : v7 MM with deep MR-driven skew  (+58k)
  ------------------------------------------------------------
  3-day backtest total                              +93,040

Parameter rationale (3-day backtest sweep, --match-trades worse):
  HL_TICKS = 2000 — half-life ~ 5x the AC1-peak step. Long-window EMA gives
                    a stable intraday mean; too short and bid-ask bounce
                    swamps the dev signal.
  SKEW_FACTOR = 2 — multiply z by 2 before rounding to a tick offset.
  SKEW_CLIP = 5  — clip quote skew to ±5 ticks. Large enough that when |z|>2
                   the quote crosses the inside book and effectively *takes*
                   the resting liquidity at favourable prices — converting
                   "deep MM" into a soft-take whenever the EMA-dev signal
                   is strong, while staying passive in the normal regime.
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import json
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
VE_LIMIT = 200

# MR signal — see module docstring for parameter rationale.
HL_TICKS = 2000
DEV_WINDOW = 3000
WARMUP_TICKS = 2000
ALPHA = 1.0 - 0.5 ** (1.0 / HL_TICKS)
SKEW_Z = 0.5
MAX_Z = 3.0
SKEW_FACTOR = 2          # multiplier on z before rounding to ticks.
SKEW_CLIP = 5            # clip quote skew at ±5 ticks (deep skew → soft take).

# v7 MM params (shared across all MM products)
INV_MAX_SKEW = 2
QUOTE_SIZE = 25
OF_THRESH = 1.5
OF_EXTREME = 5.0
SKEW_SHRINK = 0.3

# Pure MM products (no MR overlay)
PURE_MM_LIMITS: Dict[str, int] = {"HYDROGEL_PACK": 200, "VEV_4000": 300}


def _v7_mm(state: TradingState, sym: str, limit: int, mem: dict) -> List[Order]:
    od = state.order_depths.get(sym)
    if od is None or not od.buy_orders or not od.sell_orders:
        return []
    pos = state.position.get(sym, 0)
    bs_ = sorted(od.buy_orders.items(), key=lambda kv: -kv[0])
    as_ = sorted(od.sell_orders.items(), key=lambda kv: kv[0])
    best_bid = bs_[0][0]
    best_ask = as_[0][0]
    prev_bv = mem.get(f"{sym}_pb", [0, 0, 0])
    prev_av = mem.get(f"{sym}_pa", [0, 0, 0])
    cur_bv = [abs(bs_[i][1]) if i < len(bs_) else 0 for i in range(3)]
    cur_av = [abs(as_[i][1]) if i < len(as_) else 0 for i in range(3)]
    of_dir = (sum(c - p for c, p in zip(cur_bv, prev_bv))
              - sum(c - p for c, p in zip(cur_av, prev_av)))
    mem[f"{sym}_pb"] = cur_bv
    mem[f"{sym}_pa"] = cur_av
    inv_skew = round(-INV_MAX_SKEW * (pos / limit))
    out: List[Order] = []
    if best_ask - best_bid >= 2:
        our_bid = best_bid + 1 + inv_skew
        our_ask = best_ask - 1 + inv_skew
        if our_bid >= our_ask:
            if inv_skew > 0:
                our_bid = our_ask - 1
            else:
                our_ask = our_bid + 1
        bsz = asz = QUOTE_SIZE
        if of_dir >= OF_THRESH:
            bsz = int(QUOTE_SIZE * SKEW_SHRINK)
        if of_dir <= -OF_THRESH:
            asz = int(QUOTE_SIZE * SKEW_SHRINK)
        if of_dir >= OF_EXTREME:
            bsz = 0
        if of_dir <= -OF_EXTREME:
            asz = 0
        bsz = min(bsz, limit - pos)
        asz = min(asz, limit + pos)
        if bsz > 0:
            out.append(Order(sym, int(our_bid), int(bsz)))
        if asz > 0:
            out.append(Order(sym, int(our_ask), -int(asz)))
    return out


class Trader:
    def __init__(self):
        self._ema: float | None = None
        self._dev_buf: list[float] = []
        self._t_seen = 0

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

    def _ve_mr_mm(self, state: TradingState, mem: dict) -> List[Order]:
        od = state.order_depths.get(VE)
        if od is None or not od.buy_orders or not od.sell_orders:
            return []
        pos = state.position.get(VE, 0)
        bs_ = sorted(od.buy_orders.items(), key=lambda kv: -kv[0])
        as_ = sorted(od.sell_orders.items(), key=lambda kv: kv[0])
        best_bid = bs_[0][0]
        best_ask = as_[0][0]
        mid = 0.5 * (best_bid + best_ask)

        dev, sd = self._signal(mid)
        self._t_seen += 1
        z = dev / sd if self._t_seen >= WARMUP_TICKS else 0.0

        prev_bv = mem.get(f"{VE}_pb", [0, 0, 0])
        prev_av = mem.get(f"{VE}_pa", [0, 0, 0])
        cur_bv = [abs(bs_[i][1]) if i < len(bs_) else 0 for i in range(3)]
        cur_av = [abs(as_[i][1]) if i < len(as_) else 0 for i in range(3)]
        of_dir = (sum(c - p for c, p in zip(cur_bv, prev_bv))
                  - sum(c - p for c, p in zip(cur_av, prev_av)))
        mem[f"{VE}_pb"] = cur_bv
        mem[f"{VE}_pa"] = cur_av

        out: List[Order] = []
        if best_ask - best_bid >= 2:
            inv_skew = round(-INV_MAX_SKEW * (pos / VE_LIMIT))
            mr_skew = -int(round(SKEW_FACTOR * z))
            mr_skew = max(-SKEW_CLIP, min(SKEW_CLIP, mr_skew))
            total_skew = inv_skew + mr_skew

            our_bid = best_bid + 1 + total_skew
            our_ask = best_ask - 1 + total_skew
            if our_bid >= our_ask:
                if total_skew > 0:
                    our_bid = our_ask - 1
                else:
                    our_ask = our_bid + 1

            bsz = asz = QUOTE_SIZE
            if of_dir >= OF_THRESH:
                bsz = int(QUOTE_SIZE * SKEW_SHRINK)
            if of_dir <= -OF_THRESH:
                asz = int(QUOTE_SIZE * SKEW_SHRINK)
            if of_dir >= OF_EXTREME:
                bsz = 0
            if of_dir <= -OF_EXTREME:
                asz = 0
            if z < -SKEW_Z:
                bsz = int(bsz * 1.5)
                asz = int(asz * 0.6)
            elif z > SKEW_Z:
                bsz = int(bsz * 0.6)
                asz = int(asz * 1.5)

            bsz = min(bsz, VE_LIMIT - pos)
            asz = min(asz, VE_LIMIT + pos)
            if bsz > 0:
                out.append(Order(VE, int(our_bid), int(bsz)))
            if asz > 0:
                out.append(Order(VE, int(our_ask), -int(asz)))
        return out

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}

        for sym, lim in PURE_MM_LIMITS.items():
            ords = _v7_mm(state, sym, lim, mem)
            if ords:
                result[sym] = ords

        ve_orders = self._ve_mr_mm(state, mem)
        if ve_orders:
            result[VE] = ve_orders

        return result, 0, json.dumps(mem)
