"""
Round 3 Trader - ROBUST variant (scenario J).

Backtest PnL: +43,860 over 3 days (round 3, server_like fill mode).
  HYDROGEL_PACK v7 MM      : +26,173   (57%)
  VELVETFRUIT_EXTRACT v7 MM:  +6,228   (14%)
  VEV_4000 v7 MM           :  +8,810   (20%)   (21-tick spread goldmine)
  VEV_5100 v7 MM           :      +0   ( 0%)   (no counterparty flow)
  VEV_5200 v7 MM           :  +1,314   ( 3%)
  VEV_5300 v7 MM           :  +1,335   ( 3%)

Why choose this variant
-----------------------
This build is deterministic: its PnL is ~independent of VE drift direction.
All positions are mean-reverting around zero via v7 inventory skew; no
long-only accumulation, no delta-hedging, no directional bet.

Backtested PnL equals expected PnL for this structure (+/- 1-2k noise).
A symmetric down-drift in the live round would deliver ~+43k still.

Alternative: trader_round3_upside.py takes +15-20k more backtest PnL by
adding long-only scalp on VEV_5200/5300, but ~80% of that extra is
directional long-delta exposure to VE. If live VE drifts down, that
extra can evaporate or go negative.

Architecture
------------
Every tradable product gets the same v7 market-maker:
  - Quote at best_bid+1 / best_ask-1 when spread >= 2
  - Inventory skew +/-2 ticks around position = 0
  - Orderflow size-skew: shrink the side being hit
Products are independent; position limits don't overlap.

Liquidity note (from round 3 market-trade logs):
  - VEV_4500, VEV_5000, VEV_5100 have ~0 counterparty trade volume.
    They're listed for completeness but won't fill.
  - HYDROGEL, VE, VEV_4000 are the real workhorses.
"""
from prosperity4bt.datamodel import TradingState, Order, Symbol
import json


class Trader:
    LIMITS = {
        "HYDROGEL_PACK": 200,
        "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300,
        "VEV_5100": 300,
        "VEV_5200": 300,
        "VEV_5300": 300,
    }
    MM_SYMS = list(LIMITS.keys())

    # v7 parameters, validated on HYDROGEL_PACK then shared across products
    INV_MAX_SKEW = 2
    QUOTE_SIZE = 25
    OF_THRESH = 1.5
    OF_EXTREME = 5.0
    SKEW_SHRINK = 0.3

    def run(self, state: TradingState):
        orders: dict = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        for sym in self.MM_SYMS:
            orders[sym] = self._v7(state, sym, mem)
        try:
            tdata = json.dumps(mem)
        except Exception:
            tdata = ""
        return orders, 0, tdata

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

        inv_skew = round(-self.INV_MAX_SKEW * (pos / limit))

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
