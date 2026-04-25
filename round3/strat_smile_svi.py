"""Phase 4 step 4: SVI raw smile + gamma carry.

Same long-gamma carry skeleton as `trader_gamma_v7.py`, but per-strike sigma comes
from an online SVI raw fit refit every 200 ticks over a 5,000-tick FIFO of
(K, m, iv, vega) tuples.  SVI residuals live in total-variance space, which is
TTE-invariant — a defensive choice for live TTE = 5d outside the historical
{6,7,8}d range.

w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2)),  k = ln(K/F), w = sigma^2 * T

Falls back to vega-weighted parabola sigma when SVI fails (insufficient strikes /
poor convergence).
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import math
import json
from typing import Dict, List, Optional, Sequence

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
SIGMA_FALLBACK = 0.234
TTE_AT_START_DAYS = 8
TICKS_PER_DAY_MS = 1_000_000
REFIT_EVERY = 200
WINDOW_TICKS = 5000

TARGET_POS: Dict[str, int] = {"VEV_5300": 250, "VEV_5400": 250, "VEV_5200": 35}
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


class _SVISmile:
    def __init__(self):
        self._buf: list[tuple[int, float, float, float, float, float]] = []
        self._svi: Optional[list[float]] = None
        self._para: Optional[list[float]] = None
        self._last_refit = -10**9

    def observe(self, t: int, S: float, K: float, T: float, mid: float) -> None:
        iv = ol.implied_vol_call(mid, S, K, T)
        if iv is None or iv < 0.05 or iv > 1.5:
            return
        v = ol.bs_call_vega(S, K, T, iv)
        if v < 5.0:
            return
        self._buf.append((t, S, K, T, iv, v))
        cut = t - WINDOW_TICKS
        if self._buf and self._buf[0][0] < cut:
            self._buf = [r for r in self._buf if r[0] >= cut]

    def maybe_refit(self, t: int) -> None:
        if t - self._last_refit < REFIT_EVERY:
            return
        if len(self._buf) < 30:
            return
        ks = [math.log(r[2] / r[1]) for r in self._buf]
        ws = [r[4] * r[4] * r[3] for r in self._buf]
        wts = [r[5] for r in self._buf]
        ms = [ol.log_moneyness(r[1], r[2], r[3]) for r in self._buf]
        ivs = [r[4] for r in self._buf]
        self._para = ol.fit_poly(ms, ivs, degree=2, weights=wts)
        try:
            self._svi = ol.fit_svi_raw(ks, ws, weights=wts)
        except Exception:
            self._svi = None
        self._last_refit = t

    def sigma_hat(self, S: float, K: float, T: float) -> float:
        if self._svi is not None and T > 0:
            try:
                return max(0.05, ol.svi_iv(self._svi, K, S, T))
            except Exception:
                pass
        if self._para is not None:
            return max(0.05, ol.eval_poly(self._para, ol.log_moneyness(S, K, T)))
        return SIGMA_FALLBACK


class Trader:
    def __init__(self):
        self.smile = _SVISmile()

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
        S = 0.5 * (ve_bid + ve_ask)

        elapsed_days = state.timestamp / TICKS_PER_DAY_MS
        tte_days = max(0.01, TTE_AT_START_DAYS - elapsed_days)
        T = tte_days / 365.0
        flatten_mode = tte_days <= 2.0

        for sym, K in ALL_VOUCHERS.items():
            od = state.order_depths.get(sym)
            if od is None:
                continue
            bid, ask, _, _ = ol.best_bid_ask(od)
            if bid is None:
                continue
            self.smile.observe(state.timestamp, S, K, T, 0.5 * (bid + ask))
        self.smile.maybe_refit(state.timestamp)

        target_basket_delta = 0.0
        for sym, target in TARGET_POS.items():
            tgt = 0 if flatten_mode else target
            sig = self.smile.sigma_hat(S, STRIKES[sym], T)
            target_basket_delta += tgt * ol.bs_call_delta(S, STRIKES[sym], T, sig)

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
