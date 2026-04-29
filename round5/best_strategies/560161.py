"""
MICROCHIP family — hybrid MM (best-per-product naive vs smart).

Companion research doc: round5/research_microchip.md.

Combines two MM templates per product:
- NAIVE = bid+1 / ask-1 with qty=cap, no overlays. Wins where the mid drifts
  smoothly (OVAL has hardest drift in family — MR skew fights the drift and
  loses). Best on OVAL, SQUARE, TRIANGLE.
- SMART = naive + inventory skew (INV_SKEW=2.0) + MR mid-bias as a SKEW (not a
  taker, MR_SKEW=1.5) + toxicity cutoff (Z_TOXIC=2.5). 556909-style. Wins where
  mid is tight to a stationary anchor — saves RECTANGLE from the −13,556 D4
  catastrophe naive incurs.

Per-product BT routing decision (3-day BT, qty=cap, both Python and Rust):

  Product       Naive    Smart    Δ        Per-day-pass    →  Variant
  CIRCLE       +10,381  +14,133  +3,752    neither (D3)    →  SMART (BT win, both fail gate)
  OVAL         +10,675   +7,618  -3,057    NAIVE only      →  NAIVE (gate-pass)
  SQUARE        +8,705   -1,219  -9,924    neither         →  drop
  RECTANGLE     +4,676  +22,032 +17,356    SMART only      →  SMART (gate-pass + huge BT)
  TRIANGLE     +12,214   +6,066  -6,148    neither (D3)    →  NAIVE (BT win)

STRICT default (both products pass per-day gate):
  - NAIVE: OVAL only
  - SMART: RECTANGLE only
  - BT total: +32,707 / 3 days; live projection ≈ +3.3k.

RELAXED extension (also include products with positive 3-day total but one
negative day, picking the better variant per product):
  - NAIVE: OVAL, TRIANGLE
  - SMART: RECTANGLE, CIRCLE
  - SQUARE dropped (smart -1,219 total, naive D3 fails too)
  - BT total: +59,054 / 3 days; live projection ≈ +5.9k. Risk: D3 swings.
"""
from __future__ import annotations

import json
import math
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

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
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
                [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
                {s: [d.buy_orders, d.sell_orders] for s, d in state.order_depths.items()},
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.own_trades.values() for t in arr],
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.market_trades.values() for t in arr],
                state.position,
                [state.observations.plainValueObservations,
                 {p: [getattr(o, k, None) for k in ("bidPrice", "askPrice", "transportFees", "exportTariff", "importTariff", "sugarPrice", "sunlightIndex")]
                  for p, o in state.observations.conversionObservations.items()}]]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value):
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, v, n):
        return v if len(v) <= n else v[: n - 3] + "..."


logger = Logger()


# Default = STRICT (both products pass per-day gate per
# `feedback_per_day_positive_selection`). Comment-flip below for RELAXED.
NAIVE_PRODUCTS = ["MICROCHIP_OVAL"]
SMART_PRODUCTS = ["MICROCHIP_RECTANGLE"]

# RELAXED variant — uncomment to ship 4 products. CIRCLE+TRIANGLE add D3 fails
# of -1,339 / -938 (<11% of their best winning day) but family stays positive
# every day. BT +59,054 / 3 days.
# NAIVE_PRODUCTS = ["MICROCHIP_OVAL", "MICROCHIP_TRIANGLE"]
# SMART_PRODUCTS = ["MICROCHIP_RECTANGLE", "MICROCHIP_CIRCLE"]

POSITION_LIMIT = 10
SPREAD_GATE = 2

# Smart-block params (556909 TRIANGLE settings)
WINDOW = 200
MIN_HIST = 50
INV_SKEW = 2.0
MR_SKEW = 1.5
Z_TOXIC = 2.5
BASE_QTY = 10


def naive_orders(sym, depth, position):
    best_bid = max(depth.buy_orders.keys())
    best_ask = min(depth.sell_orders.keys())
    if best_ask - best_bid < SPREAD_GATE:
        return []
    buy_capacity = POSITION_LIMIT - position
    sell_capacity = POSITION_LIMIT + position
    orders: list[Order] = []
    if buy_capacity > 0:
        orders.append(Order(sym, best_bid + 1, buy_capacity))
    if sell_capacity > 0:
        orders.append(Order(sym, best_ask - 1, -sell_capacity))
    return orders


def smart_orders(sym, depth, position, hist):
    best_bid = max(depth.buy_orders.keys())
    best_ask = min(depth.sell_orders.keys())
    mid = (best_bid + best_ask) / 2.0

    hist.append(math.log(mid))
    if len(hist) > WINDOW:
        del hist[: len(hist) - WINDOW]
    if len(hist) < MIN_HIST:
        return []

    n = len(hist)
    mu = sum(hist) / n
    var = sum((x - mu) ** 2 for x in hist) / max(n - 1, 1)
    std = var ** 0.5
    if std <= 0.0:
        return []
    mu_px = math.exp(mu)
    sigma_px = mid * std
    z = (math.log(mid) - mu) / std

    inv_off = int(round(INV_SKEW * position / POSITION_LIMIT))
    mr_bias = int(round(MR_SKEW * (mu_px - mid) / max(sigma_px, 1)))

    bid_px = best_bid + 1 - inv_off + mr_bias
    ask_px = best_ask - 1 - inv_off + mr_bias
    bid_px = min(bid_px, best_ask - 1)
    ask_px = max(ask_px, best_bid + 1)
    if bid_px >= ask_px:
        return []

    cap_bid = max(0, POSITION_LIMIT - position)
    cap_ask = max(0, POSITION_LIMIT + position)
    qty_bid = min(BASE_QTY, cap_bid)
    qty_ask = min(BASE_QTY, cap_ask)
    if z >= Z_TOXIC:
        qty_bid = 0
    elif z <= -Z_TOXIC:
        qty_ask = 0

    orders: list[Order] = []
    if qty_bid > 0:
        orders.append(Order(sym, bid_px, qty_bid))
    if qty_ask > 0:
        orders.append(Order(sym, ask_px, -qty_ask))
    return orders


class Trader:
    def run(self, state: TradingState):
        result: dict[Symbol, list[Order]] = {}
        td = json.loads(state.traderData) if state.traderData else {}
        prices_hist: dict[str, list[float]] = td.get("prices", {})

        for sym in NAIVE_PRODUCTS:
            depth = state.order_depths.get(sym)
            if depth is None or not depth.buy_orders or not depth.sell_orders:
                continue
            position = state.position.get(sym, 0)
            orders = naive_orders(sym, depth, position)
            if orders:
                result[sym] = orders

        for sym in SMART_PRODUCTS:
            depth = state.order_depths.get(sym)
            if depth is None or not depth.buy_orders or not depth.sell_orders:
                continue
            position = state.position.get(sym, 0)
            hist = prices_hist.setdefault(sym, [])
            orders = smart_orders(sym, depth, position, hist)
            if orders:
                result[sym] = orders

        td["prices"] = prices_hist
        trader_data = json.dumps(td)
        conversions = 0
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data