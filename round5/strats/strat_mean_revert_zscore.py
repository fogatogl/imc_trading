"""
Mean-reverting strategy — rolling z-score.

Signal:
    z = (mid - rolling_mean) / rolling_std
    z > +ENTRY_Z  → SHORT (price extended above mean, expect down-revert)
    z < -ENTRY_Z  → LONG  (price extended below mean, expect up-revert)
    |z| < EXIT_Z  → flatten + post passive maker quotes around mid
    |z| > STOP_Z  → step out (regime broke, do not fight it)

Use when: a single product's mid price oscillates around a slow-moving
mean (stationary spread, no persistent trend).

Tune: WINDOW (longer = slower mean), ENTRY_Z (lower = more trades, less edge).
"""
from __future__ import annotations

import json
import statistics
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- config ----------
PRODUCT: str = "MICROCHIP_CIRCLE"      # change to target product
POSITION_LIMIT: int = 10
WINDOW: int = 100                      # rolling window for mean/std (in ticks)
WARMUP: int = 20                       # min observations before trading
ENTRY_Z: float = 1.5                   # |z| above this → take liquidity
EXIT_Z: float = 0.3                    # |z| below this → flatten + maker
STOP_Z: float = 4.0                    # |z| above this → freeze (regime break)
MAKER_OFFSET: int = 2                  # ticks beyond mid for passive quotes
MAKER_SIZE: int = 5                    # passive quote size per side


# ---------- Logger (verbatim from CLAUDE.md spec) ----------
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

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp, trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        return [[l.symbol, l.product, l.denomination] for l in listings.values()]

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        return {s: [d.buy_orders, d.sell_orders] for s, d in order_depths.items()}

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        out = []
        for arr in trades.values():
            for t in arr:
                out.append([t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp])
        return out

    def compress_observations(self, observations: Observation) -> list[Any]:
        conv = {}
        for product, o in observations.conversionObservations.items():
            conv[product] = [
                getattr(o, "bidPrice", None), getattr(o, "askPrice", None),
                getattr(o, "transportFees", None), getattr(o, "exportTariff", None),
                getattr(o, "importTariff", None), getattr(o, "sugarPrice", None),
                getattr(o, "sunlightIndex", None),
            ]
        return [observations.plainValueObservations, conv]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[: max_length - 3] + "..."


logger = Logger()


# ---------- helpers ----------
def best_bid_ask(depth: OrderDepth) -> tuple[int | None, int | None]:
    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    return bid, ask


def mid_of(depth: OrderDepth) -> float | None:
    bid, ask = best_bid_ask(depth)
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2.0


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        # load persistent state
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        history: list[float] = data.get("mid_history", [])

        result: dict[Symbol, list[Order]] = {}
        depth = state.order_depths.get(PRODUCT)
        if depth is None:
            logger.flush(state, result, 0, json.dumps({"mid_history": history}))
            return result, 0, json.dumps({"mid_history": history})

        mid = mid_of(depth)
        bid, ask = best_bid_ask(depth)
        pos = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if mid is not None:
            history.append(mid)
            if len(history) > WINDOW:
                history = history[-WINDOW:]

        if mid is not None and bid is not None and ask is not None and len(history) >= WARMUP:
            mu = statistics.fmean(history)
            sigma = statistics.pstdev(history) or 1e-9
            z = (mid - mu) / sigma
            logger.print(f"mid={mid:.2f} mu={mu:.2f} sd={sigma:.2f} z={z:.2f} pos={pos}")

            if abs(z) > STOP_Z:
                # regime break — do nothing, let position decay
                pass

            elif z > ENTRY_Z:
                # SELL: take the bid down to position floor
                room = POSITION_LIMIT + pos                     # how much more we can sell
                bid_size = depth.buy_orders.get(bid, 0)
                fill = min(room, bid_size)
                if fill > 0:
                    orders.append(Order(PRODUCT, bid, -fill))

            elif z < -ENTRY_Z:
                # BUY: lift the ask up to position cap
                room = POSITION_LIMIT - pos
                ask_size = -depth.sell_orders.get(ask, 0)       # asks stored as negative qty
                fill = min(room, ask_size)
                if fill > 0:
                    orders.append(Order(PRODUCT, ask, fill))

            elif abs(z) < EXIT_Z:
                # flatten any open inventory at touch
                if pos > 0:
                    orders.append(Order(PRODUCT, bid, -pos))
                elif pos < 0:
                    orders.append(Order(PRODUCT, ask, -pos))
                # passive maker layer around mu (mean) — earns spread when range-bound
                buy_px = int(round(mu - MAKER_OFFSET))
                sell_px = int(round(mu + MAKER_OFFSET))
                buy_room = POSITION_LIMIT - pos
                sell_room = POSITION_LIMIT + pos
                if buy_room > 0 and buy_px < ask:
                    orders.append(Order(PRODUCT, buy_px, min(MAKER_SIZE, buy_room)))
                if sell_room > 0 and sell_px > bid:
                    orders.append(Order(PRODUCT, sell_px, -min(MAKER_SIZE, sell_room)))

        if orders:
            result[PRODUCT] = orders

        trader_data = json.dumps({"mid_history": history})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
