"""
Round 4 hydrogel — adaptive anchor variant.

Idea: keep the round-3 mean-rev structure but let the CP signal shift the anchor
temporarily in the direction of expected mid drift, instead of skipping trades.
The signal predicts mid moves +/-8 ticks over ~50 ticks; treat that as a
short-lived target update, not a regime change.

  HP_MEAN_DYN = HP_MEAN_BASE + sig * HP_DRIFT_TICKS * (ttl / TTL_MAX)

When the signal expires, anchor returns to 9991. When a fresh signal arrives,
ttl resets to TTL_MAX. Linear decay keeps the bias bounded and predictable.

This variant exercises both tiers (taker + maker) on the shifted anchor —
no skip logic, just a moving target.
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
HP_MEAN_BASE      = 9991.0
HP_LIMIT          = 200
HP_SHARK_DEV      = 22.0
HP_MAKER_DEV      = 14.0
HP_PASSIVE_OFFSET = 5
HP_SKEW_TICKS     = 6

HP_INFORMED       = frozenset({"Mark 14"})
HP_PASSIVE_CP     = frozenset({"Mark 38"})
HP_DRIFT_TICKS    = 8.0    # measured mid drift magnitude over ~50 ticks (notebook §7)
HP_SIGNAL_TTL     = 50     # ticks; matches drift horizon


def _wap(od: OrderDepth):
    if not od or not od.buy_orders or not od.sell_orders:
        return None
    bp = max(od.buy_orders.keys())
    ap = min(od.sell_orders.keys())
    bv = od.buy_orders[bp]
    av = abs(od.sell_orders[ap])
    return (bp * av + ap * bv) / (bv + av)


def _hp_drift_sign(trades: List[Trade]) -> int:
    if not trades:
        return 0
    latest = max(trades, key=lambda t: t.timestamp)
    b, s = latest.buyer, latest.seller
    if b in HP_INFORMED:    return +1
    if s in HP_INFORMED:    return -1
    if b in HP_PASSIVE_CP:  return -1
    if s in HP_PASSIVE_CP:  return +1
    return 0


class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            td = {}

        hp_sig     = int(td.get("hp_sig", 0))
        hp_sig_ttl = int(td.get("hp_sig_ttl", 0))

        new_sig = _hp_drift_sign(state.market_trades.get(HP_PRODUCT, []))
        if new_sig != 0:
            hp_sig, hp_sig_ttl = new_sig, HP_SIGNAL_TTL
        else:
            hp_sig_ttl = max(0, hp_sig_ttl - 1)
            if hp_sig_ttl == 0:
                hp_sig = 0

        # Adaptive anchor: shift toward expected mid, decay linearly with ttl.
        anchor_shift = hp_sig * HP_DRIFT_TICKS * (hp_sig_ttl / HP_SIGNAL_TTL) if hp_sig_ttl > 0 else 0.0
        hp_mean = HP_MEAN_BASE + anchor_shift

        depths = state.order_depths
        pos    = state.position or {}
        hp_book = depths.get(HP_PRODUCT)
        hp_price = _wap(hp_book)

        if hp_book is not None and hp_price is not None:
            hp_curr = pos.get(HP_PRODUCT, 0)
            fair_anchor = hp_mean - int((hp_curr / HP_LIMIT) * HP_SKEW_TICKS)
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

        td["hp_sig"]     = hp_sig
        td["hp_sig_ttl"] = hp_sig_ttl
        trader_data = json.dumps(td, separators=(",", ":"))

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
