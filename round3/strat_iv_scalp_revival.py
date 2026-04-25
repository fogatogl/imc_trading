"""Phase 4 step 5: per-strike IV residual scalping (last year's playbook revived).

For each tradable VEV strike K:

  1. Fit an SVI raw smile from the latest 5,000 ticks of (S, K, T, IV) tuples
     across all valid strikes.
  2. Compute residual `iv_dev_K = iv_market_K - sigma_hat_K`.
  3. Maintain a rolling mean μ_K and std σ_K of `iv_dev_K` over the last 1,000
     ticks.
  4. Target position is `tanh((iv_dev_K - μ_K) / (THRESH * σ_K)) * MAX_POS_K`,
     negated (sell when residual is rich).
  5. Drive the actual position toward target via passive quoting at best_bid+1
     / best_ask-1. Hedge basket delta with VE, same band logic as v7.

This trades the *non-common* component of IV residuals — the per-strike signal
that the 4-strike-averaged Layer 2 in `round3_strategy.md` averages away.
"""
from __future__ import annotations

import _bt_setup  # noqa: F401

import math
import json
from typing import Dict, List, Optional

from prosperity4bt.datamodel import Order, TradingState

import options_lib as ol

VE = "VELVETFRUIT_EXTRACT"
SIGMA_FALLBACK = 0.234
TTE_AT_START_DAYS = 8
TICKS_PER_DAY_MS = 1_000_000

REFIT_EVERY = 200
SMILE_WINDOW = 5000
RESIDUAL_WINDOW = 1000

# Strikes we will actively scalp. Wings (5400, 5500) are excluded because their
# IV is noise-dominated by 0.5-tick premium quantization on thin OTM premia.
# Scalping the wings produced -1.5M PnL on a first attempt — keep to the core
# strikes where the IV inversion is well-conditioned.
SCALP_STRIKES: Dict[str, int] = {
    "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
}
SMILE_FEED_STRIKES: Dict[str, int] = {
    "VEV_5000": 5000, "VEV_5100": 5100,
    "VEV_5200": 5200, "VEV_5300": 5300,
    "VEV_5400": 5400, "VEV_5500": 5500,
}
MAX_POS_PER_STRIKE = 80
THRESH_SIGMAS = 2.0
MIN_SIGMA_DEV = 0.002      # vol-pts; below this, signal is dead.
WARMUP_TICKS = 2000

# Limits
VOUCHER_LIMIT = 300
VE_LIMIT = 200
HEDGE_BAND = 5             # wider band: scalp targets toggle, don't chase every tick.
HARD_HEDGE_BAND = 30
ENTRY_CHUNK = 30           # smaller chunks: limit per-tick spread crossing.


def _running_stats(samples: List[float]) -> tuple[float, float]:
    n = len(samples)
    if n == 0:
        return 0.0, 0.0
    m = sum(samples) / n
    if n == 1:
        return m, 0.0
    var = sum((x - m) ** 2 for x in samples) / n
    return m, math.sqrt(var)


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
        cut = t - SMILE_WINDOW
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
        self.iv_dev_hist: Dict[str, List[float]] = {s: [] for s in SCALP_STRIKES}

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

        # Phase A: feed smile state from the FULL strike set; only scalp the core.
        per_strike_iv: Dict[str, float] = {}
        for sym, K in SMILE_FEED_STRIKES.items():
            od = state.order_depths.get(sym)
            if od is None:
                continue
            bid, ask, _, _ = ol.best_bid_ask(od)
            if bid is None:
                continue
            mid = 0.5 * (bid + ask)
            self.smile.observe(state.timestamp, S, K, T, mid)
            if sym in SCALP_STRIKES:
                iv = ol.implied_vol_call(mid, S, K, T)
                if iv is not None:
                    per_strike_iv[sym] = iv
        self.smile.maybe_refit(state.timestamp)
        warming_up = state.timestamp < WARMUP_TICKS

        # Phase B: per-strike target position from residual signal.
        targets: Dict[str, int] = {}
        for sym, K in SCALP_STRIKES.items():
            iv_mkt = per_strike_iv.get(sym)
            if iv_mkt is None:
                targets[sym] = 0
                continue
            iv_hat = self.smile.sigma_hat(S, K, T)
            dev = iv_mkt - iv_hat
            hist = self.iv_dev_hist[sym]
            hist.append(dev)
            if len(hist) > RESIDUAL_WINDOW:
                del hist[0 : len(hist) - RESIDUAL_WINDOW]
            mu, sd = _running_stats(hist)
            sd_eff = max(sd, MIN_SIGMA_DEV)
            z = (dev - mu) / (THRESH_SIGMAS * sd_eff)
            # Sell when rich (positive z) → negative target; buy when cheap.
            sig = -math.tanh(z)
            tgt = int(round(sig * MAX_POS_PER_STRIKE))
            if flatten_mode or warming_up or len(hist) < WARMUP_TICKS // 2:
                tgt = 0
            targets[sym] = tgt

        # Phase C: passive quotes drive toward target.
        for sym, tgt in targets.items():
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

        # Phase D: VE delta hedge for the basket. Use sigma_hat per strike.
        target_basket_delta = 0.0
        for sym, K in SCALP_STRIKES.items():
            tgt = targets.get(sym, 0)
            if tgt == 0:
                continue
            sig = self.smile.sigma_hat(S, K, T)
            target_basket_delta += tgt * ol.bs_call_delta(S, K, T, sig)

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
