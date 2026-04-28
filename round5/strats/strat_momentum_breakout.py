"""
Momentum strategy — Donchian channel breakout.

Signal:
    upper = max(mid over last LOOKBACK)
    lower = min(mid over last LOOKBACK)
    mid > prev_upper (excluding current) → enter LONG  at market
    mid < prev_lower                     → enter SHORT at market
    Exit when mid crosses opposite-side EXIT_LOOKBACK channel
    (shorter lookback → faster exit, classic Turtle pattern)

Use when: a product makes regime shifts — long quiet ranges punctuated
by sustained moves to a new level. EMA crossover smooths the entry;
Donchian fires *only* on extremes, so signal is rarer but cleaner.

Tune: longer LOOKBACK = fewer false breakouts but more slippage.
"""
from __future__ import annotations

import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- config ----------
PRODUCT: str = "PANEL_2X4"
POSITION_LIMIT: int = 10
LOOKBACK: int = 50                     # entry channel length
EXIT_LOOKBACK: int = 20                # exit channel length (shorter = trailing stop)
WARMUP: int = 50


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
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        history: list[float] = data.get("mid_history", [])

        result: dict[Symbol, list[Order]] = {}
        depth = state.order_depths.get(PRODUCT)
        if depth is None:
            td = json.dumps({"mid_history": history})
            logger.flush(state, result, 0, td); return result, 0, td

        mid = mid_of(depth)
        bid, ask = best_bid_ask(depth)
        pos = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if mid is not None:
            history.append(mid)
            cap = max(LOOKBACK, EXIT_LOOKBACK) + 5
            if len(history) > cap:
                history = history[-cap:]

        if (mid is not None and bid is not None and ask is not None
                and len(history) >= max(WARMUP, LOOKBACK + 1)):
            # use the LOOKBACK-period extremes BEFORE the current bar
            entry_window = history[-LOOKBACK - 1:-1]
            exit_window = history[-EXIT_LOOKBACK - 1:-1]
            upper = max(entry_window)
            lower = min(entry_window)
            exit_upper = max(exit_window)
            exit_lower = min(exit_window)
            logger.print(f"mid={mid:.2f} upper={upper:.2f} lower={lower:.2f} pos={pos}")

            target = pos
            # ---- entries ----
            if mid > upper:
                target = POSITION_LIMIT                # breakout up
            elif mid < lower:
                target = -POSITION_LIMIT               # breakout down
            # ---- exits (trailing) ----
            if pos > 0 and mid < exit_lower:
                target = 0
            elif pos < 0 and mid > exit_upper:
                target = 0

            delta = target - pos
            if delta > 0:
                fill = min(delta, -depth.sell_orders.get(ask, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, ask, fill))
            elif delta < 0:
                fill = min(-delta, depth.buy_orders.get(bid, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, bid, -fill))

        if orders:
            result[PRODUCT] = orders

        trader_data = json.dumps({"mid_history": history})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
