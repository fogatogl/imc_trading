"""
Round 3 Trader - UPSIDE variant (scenario K).

Backtest PnL: +57,812 over 3 days (round 3, server_like fill mode).
  HYDROGEL_PACK v7 MM      : +26,173
  VELVETFRUIT_EXTRACT v7 MM:  +6,228
  VEV_4000 v7 MM           :  +8,810
  VEV_5100 v7 MM           :      +0
  VEV_5200 long scalp (300):  +11,872
  VEV_5300 long scalp (300):   +4,729

How the scalp PnL actually decomposes (critical to understand)
--------------------------------------------------------------
Of the +16,601 voucher-side PnL, ~80% is directional long-delta
exposure riding VE's +42.5 total drift in the backtest window.
The real gamma+spread edge is only ~+3.5k for these two strikes.

Hypothetical worst case if live VE drifts DOWN -30 instead of UP +42:
  - Scalp-side directional loss: 309 delta * (-72 drift swing) = -22k
  - Backtest shows +57.8k -> worst-case would be ~+35.4k

If live is roughly flat (VE range-bound): ~+51k expected.
Risk-reward compared to robust variant:
  Strategy  Best-case   Expected   Worst-case   Range
  robust    +43.9k      +43.9k     +43.9k       0
  upside    +57.8k      ~+46.6k    +35.4k       ~22k

Choose this variant if you want ranking upside and can afford the downside.

Architecture
------------
  1. Long-only scalp on VEV_5200 and VEV_5300 (post bid at best_bid+1
     when spread >= 2; fall back to take-at-ask when spread = 1).
     Accumulates toward +300 each, then holds.
  2. v7 MM on HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000, VEV_5100.

Why these two scalp strikes?
  - VEV_5200 (spread mode 3): highest gamma/contract in notebook study.
  - VEV_5300 (spread mode 2): second-highest gamma, spread too tight
    for aggressive scalp-MM combination but still contributes.
  - VEV_5100 was tested but contributes near-zero real edge;
    its fills are almost entirely on spread=1 ticks via fallback,
    so it's pure directional exposure with no spread capture. Dropped.
  - VEV_5400/5500 have spread mode = 1, can't post inside at all.
"""
from prosperity4bt.datamodel import TradingState, Order, Symbol
import json


class Trader:
    LIMITS = {
        "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300, "VEV_5100": 300,
        "VEV_5200": 300, "VEV_5300": 300,
    }
    MM_SYMS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", "VEV_4000", "VEV_5100"]
    SCALP_SYMS = ["VEV_5200", "VEV_5300"]
    SCALP_POS_CAP = 300
    SCALP_PASSIVE_SIZE = 50
    SCALP_TAKE_SIZE = 15

    INV_MAX_SKEW = 2
    QUOTE_SIZE = 25
    OF_THRESH = 1.5
    OF_EXTREME = 5.0
    SKEW_SHRINK = 0.3

    # v9 hydrogel aggressive overlay (HYDROGEL_PACK only).
    HG_INV_MAX_SKEW = 20
    HG_ANCHOR = 10000
    HG_K_FV = 6.0
    HG_CAP = 200
    HG_ANCHOR_BREAK_TOL = 200

    def run(self, state: TradingState):
        orders: dict = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        for sym in self.SCALP_SYMS:
            orders[sym] = self._scalp(state, sym)
        for sym in self.MM_SYMS:
            orders[sym] = self._v7(state, sym, mem)
        try:
            tdata = json.dumps(mem)
        except Exception:
            tdata = ""
        return orders, 0, tdata

    # ---- long-only accumulation toward +300 ----
    def _scalp(self, state, sym):
        if sym not in state.order_depths:
            return []
        od = state.order_depths[sym]
        pos = state.position.get(sym, 0)
        room = self.SCALP_POS_CAP - pos
        if room <= 0:
            return []
        if not (od.buy_orders and od.sell_orders):
            return []
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        if best_ask - best_bid >= 2:
            size = min(self.SCALP_PASSIVE_SIZE, room)
            return [Order(sym, int(best_bid + 1), int(size))] if size > 0 else []
        # spread = 1: can't post inside, cross the ask
        ask_vol = abs(od.sell_orders[best_ask])
        take = min(room, self.SCALP_TAKE_SIZE, ask_vol)
        return [Order(sym, int(best_ask), int(take))] if take > 0 else []

    # ---- two-sided v7 MM ----
    def _v7(self, state, sym, mem):
        if sym not in state.order_depths:
            return []
        od = state.order_depths[sym]
        pos = state.position.get(sym, 0)
        limit = self.LIMITS[sym]
        if not (od.buy_orders and od.sell_orders):
            return []
        bs_ = sorted(od.buy_orders.items(), key=lambda kv: -kv[0])
        as_ = sorted(od.sell_orders.items(), key=lambda kv: kv[0])
        best_bid = bs_[0][0]; best_ask = as_[0][0]

        prev_bv = mem.get(f"{sym}_pb", [0, 0, 0])
        prev_av = mem.get(f"{sym}_pa", [0, 0, 0])
        cur_bv = [abs(bs_[i][1]) if i < len(bs_) else 0 for i in range(3)]
        cur_av = [abs(as_[i][1]) if i < len(as_) else 0 for i in range(3)]
        of_dir = (sum(c - p for c, p in zip(cur_bv, prev_bv))
                - sum(c - p for c, p in zip(cur_av, prev_av)))
        mem[f"{sym}_pb"] = cur_bv
        mem[f"{sym}_pa"] = cur_av

        target = 0
        skew_max = self.INV_MAX_SKEW
        if sym == "HYDROGEL_PACK":
            mid = (best_bid + best_ask) / 2.0
            if abs(mid - self.HG_ANCHOR) <= self.HG_ANCHOR_BREAK_TOL:
                raw = -self.HG_K_FV * (mid - self.HG_ANCHOR)
                target = max(-self.HG_CAP, min(self.HG_CAP, int(round(raw))))
            skew_max = self.HG_INV_MAX_SKEW

        inv_skew = round(-skew_max * ((pos - target) / limit))
        orders = []
        if best_ask - best_bid >= 2:
            our_bid = best_bid + 1 + inv_skew
            our_ask = best_ask - 1 + inv_skew
            if our_bid >= our_ask:
                if inv_skew > 0: our_bid = our_ask - 1
                else:            our_ask = our_bid + 1
            bsz = asz = self.QUOTE_SIZE
            if of_dir >= self.OF_THRESH:
                bsz = int(self.QUOTE_SIZE * self.SKEW_SHRINK)
            if of_dir <= -self.OF_THRESH:
                asz = int(self.QUOTE_SIZE * self.SKEW_SHRINK)
            if of_dir >= self.OF_EXTREME: bsz = 0
            if of_dir <= -self.OF_EXTREME: asz = 0
            bsz = min(bsz, limit - pos)
            asz = min(asz, limit + pos)
            if bsz > 0:
                orders.append(Order(sym, int(our_bid), int(bsz)))
            if asz > 0:
                orders.append(Order(sym, int(our_ask), -int(asz)))
        return orders
