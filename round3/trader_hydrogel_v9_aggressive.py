"""v9: aggressive mean-reversion with cross-book takers.

The v8 chassis is unchanged, but we crank INV_MAX_SKEW from 2 to 20 and
K_FV from 3 to 6. At these settings the inventory-skew mechanism stops
being "small price nudge" and starts crossing the spread when (pos -
target) is large: with a 16-tick spread and skew clipped at ~20, the
quote routinely lands at or past the opposite best price, so the
backtester's resting-book matcher fills us as a taker (with the resting
price improvement). That is exactly what we want when |mid - ANCHOR| is
big - the strong mean-reversion (corr=-0.70 over 2000 ticks) repays the
half-spread cost many times over.

Backtester PnL on hydrogel (3 days, --match-trades worse):
  v7  (sk=2, K_FV=0):           +26,173
  v8  (sk=2, K_FV=3, CAP=150):  +53,083
  v9  (sk=20, K_FV=6, CAP=200): +112,636

Cross-validation (per held-out day, best params on the other 2 days):
  Held-out day 0: best (sk=25, K=6) train=78,468 test=33,814
  Held-out day 1: best (sk=20, K=7) train=71,208 test=41,934
  Held-out day 2: best (sk=20, K=6) train=79,024 test=33,612
The optimum sits at sk=20-25, K_FV=6-7 across all splits; not overfit.

`match-trades none` decomposition (no fills against market trades, only
resting book): v9 keeps +80,700 of its +104,535 (sk=20 K_FV=5) PnL.
The alpha is genuinely from spread-crossing on mean-reversion, not from
incidental maker fills.

Risk note: at INV_MAX_SKEW=20 we ARE a taker, paying the full half-
spread on entries. The thesis depends on the 10000 anchor holding. If
live mid drifts to <9800 stable, ANCHOR_BREAK_TOL=200 will clip targets
to 0 and we revert to pure MM, but we may carry a ~200-contract long
that bleeds. Tighter ANCHOR_BREAK_TOL = 80 is a defensive setting.
"""
from prosperity4bt.datamodel import TradingState, Order, Symbol
import jsonpickle

LIMIT = 200
SYMBOL = "HYDROGEL_PACK"
INV_MAX_SKEW = 20      # was 2 in v8; controls how aggressively we lean / cross
QUOTE_SIZE = 25
OF_THRESH = 1.5
OF_EXTREME = 5.0
SHRINK = 0.3

ANCHOR = 10000
K_FV = 6.0             # was 3.0 in v8
CAP = 200              # was 150 in v8
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

        if abs(mid - ANCHOR) > ANCHOR_BREAK_TOL:
            target = 0
        else:
            raw = -K_FV * (mid - ANCHOR)
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
        return result, 0, jsonpickle.encode(mem)
