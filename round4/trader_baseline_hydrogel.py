"""
Round 4 hydrogel baseline — round-3 winner verbatim, vol-armor removed.
Used as control vs `trader_v1_cp_hydrogel.py` to isolate the CP-gate lift.
"""

from typing import List, Dict, Tuple, Any
import json
import math

try:
    from datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )
except ImportError:
    from prosperity4bt.datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders), conversions, "", "",
        ]))
        max_item = (self.max_log_length - base) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item),
            self.truncate(self.logs, max_item),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [
            state.timestamp, td,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.own_trades.values() for t in arr],
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.market_trades.values() for t in arr],
            state.position,
            [state.observations.plainValueObservations,
             {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff,
                  o.importTariff, getattr(o, "sugarPrice", 0),
                  getattr(o, "sunlightIndex", 0)]
              for p, o in state.observations.conversionObservations.items()}],
        ]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, v):
        return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, v, n):
        lo, hi, out = 0, min(len(v), n), ""
        while lo <= hi:
            mid = (lo + hi) // 2
            cand = v[:mid] + ("..." if mid < len(v) else "")
            if len(json.dumps(cand)) <= n:
                out, lo = cand, mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


HP_PRODUCT        = "HYDROGEL_PACK"
HP_MEAN           = 9991.0
HP_LIMIT          = 200
HP_SHARK_DEV      = 22.0
HP_MAKER_DEV      = 14.0
HP_PASSIVE_OFFSET = 5
HP_SKEW_TICKS     = 6


def _wap(od: OrderDepth):
    if not od or not od.buy_orders or not od.sell_orders:
        return None
    bp = max(od.buy_orders.keys())
    ap = min(od.sell_orders.keys())
    bv = od.buy_orders[bp]
    av = abs(od.sell_orders[ap])
    return (bp * av + ap * bv) / (bv + av)


class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            td = {}

        depths = state.order_depths
        pos    = state.position or {}
        hp_book = depths.get(HP_PRODUCT)
        hp_price = _wap(hp_book)

        if hp_book is not None and hp_price is not None:
            hp_curr = pos.get(HP_PRODUCT, 0)
            fair_anchor = HP_MEAN - int((hp_curr / HP_LIMIT) * HP_SKEW_TICKS)
            dev = hp_price - fair_anchor

            if abs(dev) > HP_SHARK_DEV:
                side_volume = sum(
                    abs(v) for v in (
                        hp_book.buy_orders if dev > 0 else hp_book.sell_orders
                    ).values()
                )
                qty = min(HP_LIMIT - abs(hp_curr), side_volume)
                if qty > 0:
                    px = (max(hp_book.buy_orders.keys()) if dev > 0
                          else min(hp_book.sell_orders.keys()))
                    result[HP_PRODUCT] = [
                        Order(HP_PRODUCT, int(px), int(-qty if dev > 0 else qty))
                    ]

            elif abs(dev) > HP_MAKER_DEV:
                if dev > 0 and hp_curr > -HP_LIMIT:
                    result[HP_PRODUCT] = [
                        Order(HP_PRODUCT,
                              int(math.ceil(hp_price + HP_PASSIVE_OFFSET)),
                              -(HP_LIMIT + hp_curr))
                    ]
                elif dev < 0 and hp_curr < HP_LIMIT:
                    result[HP_PRODUCT] = [
                        Order(HP_PRODUCT,
                              int(math.floor(hp_price - HP_PASSIVE_OFFSET)),
                              HP_LIMIT - hp_curr)
                    ]

        trader_data = json.dumps(td, separators=(",", ":"))
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
