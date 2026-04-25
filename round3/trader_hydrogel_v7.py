"""v7: inv skew ±2 + OF size-skew only. The combo."""
from prosperity4bt.datamodel import TradingState, Order, Symbol
import jsonpickle

LIMIT = 200
SYMBOL = "HYDROGEL_PACK"
INV_MAX_SKEW = 2
QUOTE_SIZE = 25
OF_THRESH = 1.5
OF_EXTREME = 5.0
SHRINK = 0.3

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
        cb=[abs(bs[i][1]) if i<len(bs) else 0 for i in range(3)]
        ca=[abs(asks[i][1]) if i<len(asks) else 0 for i in range(3)]
        of_dir = sum(c-p for c,p in zip(cb,prev_bids)) - sum(c-p for c,p in zip(ca,prev_asks))
        inv_skew = round(-INV_MAX_SKEW*(pos/LIMIT))
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
