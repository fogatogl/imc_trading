"""v8: v7 chassis + mean-reversion inventory target.

Hydrogel mid mean-reverts to ~10000 (AR(1) coef 0.998, half-life 325 ticks,
corr(deviation, fwd_change @ 2000 ticks) = -0.70). v7 keeps inventory at
zero, leaving the reversion uncaptured. v8 sets a target inventory that
leans into the reversion: long when mid<anchor, short when mid>anchor.

In-sample (worse-mode simulator): v7 +25k, v8 with K_FV=3, CAP=150 +53k.
"""
from prosperity4bt.datamodel import TradingState, Order, Symbol
import jsonpickle

LIMIT = 200
SYMBOL = "HYDROGEL_PACK"
INV_MAX_SKEW = 2
QUOTE_SIZE = 25
OF_THRESH = 1.5
OF_EXTREME = 5.0
SHRINK = 0.3

# Mean-reversion overlay
ANCHOR = 10000
K_FV = 3.0
CAP = 150
ANCHOR_BREAK_TOL = 200  # |mid-anchor|>this => disable overlay


class Trader:
    def run(self, state):
        result = {}
        try: mem = jsonpickle.decode(state.traderData) if state.traderData else {}
        except: mem = {}
        if not isinstance(mem, dict): mem = {}
        prev_bids = mem.get("pb", [0, 0, 0])
        prev_asks = mem.get("pa", [0, 0, 0])
        if SYMBOL not in state.order_depths:
            return result, 0, jsonpickle.encode(mem)
        od = state.order_depths[SYMBOL]
        pos = state.position.get(SYMBOL, 0)
        orders = []
        if not (od.buy_orders and od.sell_orders):
            mem["pb"]=prev_bids; mem["pa"]=prev_asks
            return result, 0, jsonpickle.encode(mem)
        bs = sorted(od.buy_orders.items(), key=lambda kv: -kv[0])
        asks = sorted(od.sell_orders.items(), key=lambda kv: kv[0])
        best_bid=bs[0][0]; best_ask=asks[0][0]
        mid = (best_bid + best_ask) / 2.0
        cb=[abs(bs[i][1]) if i<len(bs) else 0 for i in range(3)]
        ca=[abs(asks[i][1]) if i<len(asks) else 0 for i in range(3)]
        of_dir = sum(c-p for c,p in zip(cb,prev_bids)) - sum(c-p for c,p in zip(ca,prev_asks))

        # Mean-reversion target
        if abs(mid - ANCHOR) > ANCHOR_BREAK_TOL:
            target = 0
        else:
            raw = -K_FV * (mid - ANCHOR)
            target = max(-CAP, min(CAP, int(round(raw))))

        # Inventory skew is now around target instead of 0
        deviation = pos - target
        inv_skew = round(-INV_MAX_SKEW*(deviation/LIMIT))

        buy_cap=LIMIT-pos; sell_cap=LIMIT+pos
        if best_ask-best_bid >= 2:
            our_bid=best_bid+1+inv_skew; our_ask=best_ask-1+inv_skew
            if our_bid>=our_ask:
                if inv_skew>0: our_bid=our_ask-1
                else: our_ask=our_bid+1
            bsz=asz=QUOTE_SIZE
            if of_dir >= OF_THRESH: bsz=int(QUOTE_SIZE*SHRINK)
            if of_dir <= -OF_THRESH: asz=int(QUOTE_SIZE*SHRINK)
            if of_dir >= OF_EXTREME: bsz=0
            if of_dir <= -OF_EXTREME: asz=0
            bsz=min(bsz,buy_cap); asz=min(asz,sell_cap)
            if bsz>0: orders.append(Order(SYMBOL, int(our_bid), bsz))
            if asz>0: orders.append(Order(SYMBOL, int(our_ask), -asz))
        result[SYMBOL] = orders
        mem["pb"]=cb; mem["pa"]=ca
        return result, 0, jsonpickle.encode(mem)
