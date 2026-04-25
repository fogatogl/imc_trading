"""Phase 4 step 2: vega-weighted online parabola in place of constant SIGMA.

Same skeleton as `trader_gamma_v7.py`: long-gamma carry on VEV_5200/5300/5400 with
a target-based VE delta hedge. The only difference: per-strike sigma comes from a
rolling vega-weighted parabola fit (re-fit every 100 ticks over a 5,000-tick FIFO),
falling back to 0.234 until the fit warms up.

Hypothesis: pricing each strike at its smile-implied IV rather than constant 0.234
yields better hedge ratios on the wings (5400, and any future 5000/5500 carry).
"""
from __future__ import annotations

import _bt_setup  # noqa: F401  -- patches prosperity4bt.data.LIMITS

import jsonpickle
from typing import Dict, List

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
SIGMA_FALLBACK = 0.234
TTE_AT_START_DAYS = 8
TICKS_PER_DAY_MS = 1_000_000

TARGET_POS: Dict[str, int] = {
    "VEV_5300": 250,
    "VEV_5400": 250,
    "VEV_5200": 35,
}
STRIKES: Dict[str, int] = {"VEV_5200": 5200, "VEV_5300": 5300, "VEV_5400": 5400}
ALL_VOUCHERS: Dict[str, int] = {
    "VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
    "VEV_5400": 5400, "VEV_5500": 5500,
}

VOUCHER_LIMIT = 300
VE_LIMIT = 200
HEDGE_BAND = 1
HARD_HEDGE_BAND = 30
ENTRY_CHUNK = 60


class Trader:
    def __init__(self):
        self.smile = ol.RollingSmile(window_ticks=5000, refit_every=100, vega_min=5.0)

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
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = ol.best_bid_ask(ve_od)
        if ve_bid is None:
            return result, 0, jsonpickle.encode(mem)
        S = 0.5 * (ve_bid + ve_ask)

        elapsed_days = state.timestamp / TICKS_PER_DAY_MS
        tte_days = max(0.01, TTE_AT_START_DAYS - elapsed_days)
        T = tte_days / 365.0
        flatten_mode = tte_days <= 2.0

        # Feed every tradable voucher into the rolling smile.
        for sym, K in ALL_VOUCHERS.items():
            od = state.order_depths.get(sym)
            if od is None:
                continue
            bid, ask, _, _ = ol.best_bid_ask(od)
            if bid is None:
                continue
            mid = 0.5 * (bid + ask)
            self.smile.observe(state.timestamp, S, K, T, mid)
        self.smile.maybe_refit(state.timestamp)

        def sigma(K: int) -> float:
            return self.smile.sigma_hat(S, K, T, fallback=SIGMA_FALLBACK)

        # Target-based basket delta with per-strike sigma.
        target_basket_delta = 0.0
        for sym, target in TARGET_POS.items():
            tgt = 0 if flatten_mode else target
            target_basket_delta += tgt * ol.bs_call_delta(S, STRIKES[sym], T, sigma(STRIKES[sym]))

        # Layer 1a: passive voucher entries.
        for sym, target in TARGET_POS.items():
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

        # Layer 1b: VE delta hedge.
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
