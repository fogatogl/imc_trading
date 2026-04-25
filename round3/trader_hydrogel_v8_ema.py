"""v8 EMA variant: mean-reversion target uses an EMA anchor instead of fixed 10000.

Trades some in-sample P&L for robustness against an anchor that shifts in live.
Defensive submission candidate.
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

ANCHOR_DEFAULT = 10000  # used until EMA warms up
EMA_ALPHA = 0.0005       # span ~ 2/alpha = 4000 ticks  (slow)
K_FV = 2.0
CAP = 100
ANCHOR_BREAK_TOL = 200


class Trader:
    def run(self, state):
        result = {}
        try: mem = jsonpickle.decode(state.traderData) if state.traderData else {}
        except: mem = {}
        if not isinstance(mem, dict): mem = {}
        prev_bids = mem.get("pb", [0, 0, 0])
        prev_asks = mem.get("pa", [0, 0, 0])
        ema = mem.get("ema", None)
        n = mem.get("n", 0)
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

        if ema is None:
            ema = mid
        else:
            ema = EMA_ALPHA * mid + (1 - EMA_ALPHA) * ema
        n += 1
        anchor = ema if n > 500 else ANCHOR_DEFAULT

        cb=[abs(bs[i][1]) if i<len(bs) else 0 for i in range(3)]
        ca=[abs(asks[i][1]) if i<len(asks) else 0 for i in range(3)]
        of_dir = sum(c-p for c,p in zip(cb,prev_bids)) - sum(c-p for c,p in zip(ca,prev_asks))

        if abs(mid - anchor) > ANCHOR_BREAK_TOL:
            target = 0
        else:
            raw = -K_FV * (mid - anchor)
            target = max(-CAP, min(CAP, int(round(raw))))

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
        mem["ema"]=ema; mem["n"]=n
        return result, 0, jsonpickle.encode(mem)
