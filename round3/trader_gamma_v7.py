"""Round 3 v7 — FINAL long-gamma carry basket.

Backtest: +8,513 SeaShells over 3 historical days (day 0/1/2 = +4236/+2838/+1439).

Key design choices that made the strategy profitable:
1. Target-based delta hedge — compute desired VE short from the TARGET basket delta
   (not from currently-filled positions). Eliminates the entry-lag bleed that killed
   earlier versions.
2. All-passive voucher entry — post BUY at best_bid+1 (never cross). Phase-2 market-
   trade interception fills us well below mid on dips (fill price = our quote).
3. Tight hedge band = 1, passive VE posting at bid+1 / ask-1. Cross only when delta
   drift exceeds HARD_HEDGE_BAND=30 (rare; limits runaway delta).
4. Size = 250/250/35 on VEV_5300/5400/5200. Larger sizes (>=280) bleed P&L because
   basket delta approaches the 200 VE position limit.

Assumes TTE_AT_START_DAYS = 8 (historical day 0). For live Round 3 change to 5.
"""
import math
import jsonpickle
from prosperity4bt.datamodel import Order, TradingState
from typing import List, Dict

VE = "VELVETFRUIT_EXTRACT"
SIGMA = 0.234                     # smile-level baseline (stable across TTE)
TTE_AT_START_DAYS = 8             # set to 5 for live submission
TICKS_PER_DAY_MS = 1_000_000

TARGET_POS: Dict[str, int] = {
    "VEV_5300": 250,
    "VEV_5400": 250,
    "VEV_5200": 35,
}
STRIKES: Dict[str, int] = {
    "VEV_5200": 5200, "VEV_5300": 5300, "VEV_5400": 5400,
}

VOUCHER_LIMIT = 300
VE_LIMIT = 200
HEDGE_BAND = 1                    # rebalance threshold (passive VE orders)
HARD_HEDGE_BAND = 30              # cross VE spread if drift exceeds this
ENTRY_CHUNK = 60                  # per-tick cap on voucher order size


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def call_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 1.0 if S > K else 0.0
    vt = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * vt * vt) / vt
    return _ncdf(d1)


def best_bid_ask(od):
    if not od or not od.buy_orders or not od.sell_orders:
        return None, None, 0, 0
    bid = max(od.buy_orders.keys())
    ask = min(od.sell_orders.keys())
    return bid, ask, od.buy_orders[bid], abs(od.sell_orders[ask])


class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        try:
            mem = jsonpickle.decode(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        if not isinstance(mem, dict):
            mem = {}

        ve_od = state.order_depths.get(VE)
        if ve_od is None:
            return result, 0, jsonpickle.encode(mem)
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = best_bid_ask(ve_od)
        if ve_bid is None:
            return result, 0, jsonpickle.encode(mem)
        S = 0.5 * (ve_bid + ve_ask)

        elapsed_days = state.timestamp / TICKS_PER_DAY_MS
        tte_days = max(0.01, TTE_AT_START_DAYS - elapsed_days)
        T = tte_days / 365.0

        # Flatten at TTE <= 2d (out-of-sample risk; never triggered in backtest).
        flatten_mode = tte_days <= 2.0

        # Hedge target uses DESIRED basket delta (not current). Eliminates entry lag.
        target_basket_delta = 0.0
        for sym, target in TARGET_POS.items():
            tgt = 0 if flatten_mode else target
            target_basket_delta += tgt * call_delta(S, STRIKES[sym], T, SIGMA)

        # Layer 1a: passive voucher entries (never cross, phase-2 fills on dips).
        for sym, target in TARGET_POS.items():
            tgt = 0 if flatten_mode else target
            cur = state.position.get(sym, 0)
            gap = tgt - cur
            if gap == 0:
                continue
            od = state.order_depths.get(sym)
            if od is None:
                continue
            bid, ask, _, _ = best_bid_ask(od)
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

        # Layer 1b: VE delta hedge (passive post + hard-cross safety).
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

        return result, 0, jsonpickle.encode(mem)
