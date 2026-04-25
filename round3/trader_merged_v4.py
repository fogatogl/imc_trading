"""Round 3 — MERGED v4: upside + PASSIVE-ONLY VEV_5400 accumulation.

Upside's scalp code crosses-at-ask when spread=1 (VEV_5400's normal state),
making it a losing accumulation. v4 uses v7-style passive-only for 5400:
post at bid+1 when spread>=2, skip entirely when spread=1.

This removes the -1.5k drag from aggressive 5400 entry while still capturing
the +fills when spread widens.
"""
try:
    from datamodel import TradingState, Order
except ImportError:
    from prosperity4bt.datamodel import TradingState, Order
import json


class Trader:
    LIMITS = {
        "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300, "VEV_5100": 300,
        "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300,
    }
    MM_SYMS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", "VEV_4000", "VEV_5100"]
    SCALP_SYMS = ["VEV_5200", "VEV_5300"]
    PASSIVE_ONLY_SYMS = ["VEV_5400"]  # new: never cross
    SCALP_POS_CAP = 300
    SCALP_PASSIVE_SIZE = 50
    SCALP_TAKE_SIZE = 15
    PASSIVE_SIZE = 60

    INV_MAX_SKEW = 2
    QUOTE_SIZE = 25
    OF_THRESH = 1.5
    OF_EXTREME = 5.0
    SKEW_SHRINK = 0.3

    # v8 hydrogel mean-reversion overlay (HYDROGEL_PACK only).
    HG_ANCHOR = 10000
    HG_K_FV = 3.0
    HG_CAP = 150
    HG_ANCHOR_BREAK_TOL = 200

    def run(self, state: TradingState):
        orders: dict = {}
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        for sym in self.SCALP_SYMS:
            orders[sym] = self._scalp(state, sym)
        for sym in self.PASSIVE_ONLY_SYMS:
            orders[sym] = self._passive_only(state, sym)
        for sym in self.MM_SYMS:
            orders[sym] = self._v7(state, sym, mem)
        try:
            tdata = json.dumps(mem)
        except Exception:
            tdata = ""
        return orders, 0, tdata

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
        ask_vol = abs(od.sell_orders[best_ask])
        take = min(room, self.SCALP_TAKE_SIZE, ask_vol)
        return [Order(sym, int(best_ask), int(take))] if take > 0 else []

    def _passive_only(self, state, sym):
        """Only post bid+1 when spread>=2. Never cross. Accumulate long up to limit."""
        if sym not in state.order_depths:
            return []
        od = state.order_depths[sym]
        pos = state.position.get(sym, 0)
        room = self.SCALP_POS_CAP - pos
        if room <= 0 or not (od.buy_orders and od.sell_orders):
            return []
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        if best_ask - best_bid >= 2:
            size = min(self.PASSIVE_SIZE, room)
            return [Order(sym, int(best_bid + 1), int(size))] if size > 0 else []
        return []

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

        target = 0
        if sym == "HYDROGEL_PACK":
            mid = (best_bid + best_ask) / 2.0
            if abs(mid - self.HG_ANCHOR) <= self.HG_ANCHOR_BREAK_TOL:
                raw = -self.HG_K_FV * (mid - self.HG_ANCHOR)
                target = max(-self.HG_CAP, min(self.HG_CAP, int(round(raw))))

        inv_skew = round(-self.INV_MAX_SKEW * ((pos - target) / limit))
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
