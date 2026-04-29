"""
PANEL family — naive MM + position-aware trend filter.

v4 (`strat_panel_mm_v4_trend.py`) full one-sided skip on EMA crossover:
  BT total +15,434 (−72% vs v1) — broke PANEL_2X4 (BT −11,757) and PANEL_1X4
  D4 because skipping a whole side prevents round-trip exits.

v5 only skips the side that *adds* to an already-wrong-sided position when the
trend confirms the inventory direction is bad.

  trend = short_ema(30) − long_ema(200)
  if trend < −TREND_THRESHOLD and pos > 0:  skip BID  (don't add long on falling mid)
  if trend > +TREND_THRESHOLD and pos < 0:  skip ASK  (don't add short on rising mid)
  else: post both sides as v1

When pos=0 the filter is silent — both sides quote — round trips proceed
normally. When pos drifts onto the wrong side of trend, the addition channel
closes but the exit channel stays open.
"""
from __future__ import annotations

import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item = (self.max_log_length - base) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item),
            self.truncate(self.logs, max_item),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td,
                [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
                {s: [d.buy_orders, d.sell_orders] for s, d in state.order_depths.items()},
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                 for arr in state.own_trades.values() for t in arr],
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                 for arr in state.market_trades.values() for t in arr],
                state.position,
                [state.observations.plainValueObservations,
                 {p: [getattr(o, k, None) for k in
                      ("bidPrice", "askPrice", "transportFees", "exportTariff",
                       "importTariff", "sugarPrice", "sunlightIndex")]
                  for p, o in state.observations.conversionObservations.items()}]]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value):
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, v, n):
        return v if len(v) <= n else v[: n - 3] + "..."


logger = Logger()


PRODUCTS = ["PANEL_1X4", "PANEL_2X2", "PANEL_2X4"]
POSITION_LIMIT = 10
SPREAD_GATE = 2

SHORT_HALF = 30
LONG_HALF = 200
TREND_THRESHOLD = 5.0
WARMUP = 30

ALPHA_SHORT = 2.0 / (SHORT_HALF + 1)
ALPHA_LONG = 2.0 / (LONG_HALF + 1)


class Trader:
    def run(self, state: TradingState):
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        emas: dict[str, dict[str, float]] = data.get("emas", {})
        ticks_seen: dict[str, int] = data.get("ticks", {})

        result: dict[Symbol, list[Order]] = {}

        for product in PRODUCTS:
            depth = state.order_depths.get(product)
            if depth is None or not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders.keys())
            best_ask = min(depth.sell_orders.keys())
            if best_ask - best_bid < SPREAD_GATE:
                continue

            mid = (best_bid + best_ask) / 2.0

            prev = emas.get(product)
            if prev is None:
                short_ema = mid
                long_ema = mid
            else:
                short_ema = ALPHA_SHORT * mid + (1 - ALPHA_SHORT) * prev["s"]
                long_ema = ALPHA_LONG * mid + (1 - ALPHA_LONG) * prev["l"]
            emas[product] = {"s": short_ema, "l": long_ema}
            n = ticks_seen.get(product, 0) + 1
            ticks_seen[product] = n

            position = state.position.get(product, 0)
            buy_capacity = POSITION_LIMIT - position
            sell_capacity = POSITION_LIMIT + position

            post_bid = True
            post_ask = True
            if n >= WARMUP:
                trend = short_ema - long_ema
                if trend < -TREND_THRESHOLD and position > 0:
                    post_bid = False
                elif trend > +TREND_THRESHOLD and position < 0:
                    post_ask = False

            orders: list[Order] = []
            if post_bid and buy_capacity > 0:
                orders.append(Order(product, best_bid + 1, buy_capacity))
            if post_ask and sell_capacity > 0:
                orders.append(Order(product, best_ask - 1, -sell_capacity))

            if orders:
                result[product] = orders

        trader_data = json.dumps({"emas": emas, "ticks": ticks_seen})
        conversions = 0
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
