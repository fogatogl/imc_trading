"""
Random-walk strategy — passive market making with inventory skew.

Premise:
    If the price has no exploitable structure (no mean to revert to,
    no trend to follow), the only way to make money is to *be the spread*.
    Quote both sides; pay no spread; lean toward zero inventory so you
    don't accumulate directional exposure when one side fills repeatedly.

Mechanics:
    fair = mid - SKEW_PER_UNIT * pos    (when long, fair drops → easier to sell,
                                         harder to buy → bleeds inventory back to 0)
    buy  @ fair - HALF_SPREAD  size = min(QUOTE_SIZE, POSITION_LIMIT - pos)
    sell @ fair + HALF_SPREAD  size = min(QUOTE_SIZE, POSITION_LIMIT + pos)

    Optional: take book dislocations when best bid > fair + HALF_SPREAD
    (someone is paying us above our fair) — this is free edge.

Use when: a product's mid price is ~ a martingale (no signal in returns).
Don't run this on a trending or strongly mean-reverting product — the
skew alone won't save you from a one-sided drift.
"""
from __future__ import annotations

import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- config ----------
PRODUCT: str = "GALAXY_SOUNDS_DARK_MATTER"
POSITION_LIMIT: int = 10
HALF_SPREAD: int = 2                   # quote at fair ± HALF_SPREAD ticks
QUOTE_SIZE: int = 5                    # passive size per side
SKEW_PER_UNIT: float = 0.3             # fair shift per unit of inventory
TAKE_EDGE: int = 1                     # take when (best_bid - fair) > HALF_SPREAD + TAKE_EDGE


# ---------- Logger ----------
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base_length = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td,
                self.compress_listings(state.listings),
                self.compress_order_depths(state.order_depths),
                self.compress_trades(state.own_trades),
                self.compress_trades(state.market_trades),
                state.position,
                self.compress_observations(state.observations)]
    def compress_listings(self, listings): return [[l.symbol, l.product, l.denomination] for l in listings.values()]
    def compress_order_depths(self, ods): return {s: [d.buy_orders, d.sell_orders] for s, d in ods.items()}
    def compress_trades(self, trades):
        return [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in trades.values() for t in arr]
    def compress_observations(self, observations):
        conv = {}
        for p, o in observations.conversionObservations.items():
            conv[p] = [getattr(o, k, None) for k in
                       ("bidPrice","askPrice","transportFees","exportTariff","importTariff","sugarPrice","sunlightIndex")]
        return [observations.plainValueObservations, conv]
    def compress_orders(self, orders): return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]
    def to_json(self, v): return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))
    def truncate(self, v, n): return v if len(v) <= n else v[: n - 3] + "..."


logger = Logger()


# ---------- helpers ----------
def best_bid_ask(depth: OrderDepth) -> tuple[int | None, int | None]:
    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    return bid, ask


def mid_of(depth: OrderDepth) -> float | None:
    bid, ask = best_bid_ask(depth)
    return (bid + ask) / 2.0 if (bid is not None and ask is not None) else None


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result: dict[Symbol, list[Order]] = {}
        depth = state.order_depths.get(PRODUCT)
        if depth is None:
            logger.flush(state, result, 0, "")
            return result, 0, ""

        bid, ask = best_bid_ask(depth)
        mid = mid_of(depth)
        pos = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if mid is not None and bid is not None and ask is not None:
            fair = mid - SKEW_PER_UNIT * pos
            buy_px = int(round(fair - HALF_SPREAD))
            sell_px = int(round(fair + HALF_SPREAD))
            buy_room = POSITION_LIMIT - pos
            sell_room = POSITION_LIMIT + pos
            logger.print(f"mid={mid:.2f} fair={fair:.2f} bid={bid} ask={ask} pos={pos}")

            # ---- opportunistic take when book is dislocated past our fair ----
            # someone is bidding above (fair + HALF_SPREAD + TAKE_EDGE) → sell into it
            if bid >= fair + HALF_SPREAD + TAKE_EDGE and sell_room > 0:
                size = min(sell_room, depth.buy_orders.get(bid, 0))
                if size > 0:
                    orders.append(Order(PRODUCT, bid, -size))
                    sell_room -= size
            # someone is asking below (fair - HALF_SPREAD - TAKE_EDGE) → buy from them
            if ask <= fair - HALF_SPREAD - TAKE_EDGE and buy_room > 0:
                size = min(buy_room, -depth.sell_orders.get(ask, 0))
                if size > 0:
                    orders.append(Order(PRODUCT, ask, size))
                    buy_room -= size

            # ---- passive maker quotes (don't cross our own fills) ----
            # Ensure quotes don't cross the existing book the wrong way.
            if buy_px >= ask:
                buy_px = ask - 1
            if sell_px <= bid:
                sell_px = bid + 1

            if buy_room > 0:
                orders.append(Order(PRODUCT, buy_px, min(QUOTE_SIZE, buy_room)))
            if sell_room > 0:
                orders.append(Order(PRODUCT, sell_px, -min(QUOTE_SIZE, sell_room)))

        if orders:
            result[PRODUCT] = orders

        # no persistent state needed
        logger.flush(state, result, 0, "")
        return result, 0, ""
