"""Phase 4 step 7-bis: extend layered_full's MM coverage to more strikes.

Target: + extra MM PnL on under-explored vouchers without conflicting with the
gamma carry book. Carry holds VEV_5200/5300/5400; we add MM on every other
voucher (VEV_4000/4500/5000/5100/5500/6000/6500). If a strike has no flow it
contributes ~0 (proven for VEV_5100 in the robust trader breakdown).

Hedge: carry uses VE delta hedge as in v7; MM does not touch VE so the hedger
keeps exclusive use of the VE position budget.
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import json
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
SIGMA = 0.234
TTE_AT_START_DAYS = 8
TICKS_PER_DAY_MS = 1_000_000

CARRY_TARGETS: Dict[str, int] = {"VEV_5300": 250, "VEV_5400": 250, "VEV_5200": 35}
CARRY_STRIKES: Dict[str, int] = {"VEV_5200": 5200, "VEV_5300": 5300, "VEV_5400": 5400}

VOUCHER_LIMIT = 300
VE_LIMIT = 200
HEDGE_BAND = 1
HARD_HEDGE_BAND = 30
ENTRY_CHUNK = 60

# MM the products NOT touched by the carry book.
MM_LIMITS: Dict[str, int] = {
    "HYDROGEL_PACK": 200,
    "VEV_4000": 300,
    "VEV_4500": 300,
    "VEV_5000": 300,
    "VEV_5100": 300,
    "VEV_5500": 300,
    "VEV_6000": 300,
    "VEV_6500": 300,
}

INV_MAX_SKEW = 2
QUOTE_SIZE = 25
OF_THRESH = 1.5
OF_EXTREME = 5.0
SKEW_SHRINK = 0.3


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
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}

        for sym, lim in MM_LIMITS.items():
            ords = _v7_mm(state, sym, lim, mem)
            if ords:
                result[sym] = ords

        ve_od = state.order_depths.get(VE)
        if ve_od is None:
            return result, 0, json.dumps(mem)
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = ol.best_bid_ask(ve_od)
        if ve_bid is None:
            return result, 0, json.dumps(mem)
        S = 0.5 * (ve_bid + ve_ask)

        elapsed_days = state.timestamp / TICKS_PER_DAY_MS
        tte_days = max(0.01, TTE_AT_START_DAYS - elapsed_days)
        T = tte_days / 365.0
        flatten_mode = tte_days <= 2.0

        target_basket_delta = 0.0
        for sym, target in CARRY_TARGETS.items():
            tgt = 0 if flatten_mode else target
            target_basket_delta += tgt * ol.bs_call_delta(S, CARRY_STRIKES[sym], T, SIGMA)

        for sym, target in CARRY_TARGETS.items():
            tgt = 0 if flatten_mode else target
            cur = state.position.get(sym, 0)
            gap = tgt - cur
            if gap == 0:
                continue
            od = state.order_depths.get(sym)
            if od is None:
                continue
            bid, ask, _, _ = ol.best_bid_ask(od)
            if bid is None:
                continue
            if gap > 0:
                price = bid + 1
                if price >= ask:
                    price = ask - 1 if ask - 1 > bid else bid + 1
                qty = min(gap, ENTRY_CHUNK, VOUCHER_LIMIT - cur)
                if qty > 0:
                    result[sym] = [Order(sym, price, qty)]
            else:
                price = ask - 1
                if price <= bid:
                    price = bid + 1 if bid + 1 < ask else ask - 1
                qty = min(-gap, ENTRY_CHUNK, VOUCHER_LIMIT + cur)
                if qty > 0:
                    result[sym] = [Order(sym, price, -qty)]

        ve_pos = state.position.get(VE, 0)
        target_ve = -int(round(target_basket_delta))
        target_ve = max(-VE_LIMIT, min(VE_LIMIT, target_ve))
        ve_gap = target_ve - ve_pos
        if abs(ve_gap) > HEDGE_BAND:
            hard_cross = abs(ve_gap) > HARD_HEDGE_BAND
            if ve_gap > 0:
                price = ve_ask if hard_cross else ve_bid + 1
                qty = min(ve_gap, VE_LIMIT - ve_pos)
                if hard_cross:
                    qty = min(qty, ve_ask_sz if ve_ask_sz > 0 else qty)
                if qty > 0:
                    result[VE] = [Order(VE, price, qty)]
            else:
                price = ve_bid if hard_cross else ve_ask - 1
                qty = min(-ve_gap, VE_LIMIT + ve_pos)
                if hard_cross:
                    qty = min(qty, ve_bid_sz if ve_bid_sz > 0 else qty)
                if qty > 0:
                    result[VE] = [Order(VE, price, -qty)]

        return result, 0, json.dumps(mem)
