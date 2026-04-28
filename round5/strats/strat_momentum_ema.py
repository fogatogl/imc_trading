"""
Momentum strategy — fast/slow EMA crossover.

Signal:
    fast_ema = EMA(N_FAST), slow_ema = EMA(N_SLOW)
    diff = fast_ema - slow_ema
    diff > +ENTRY_DELTA  → target = +POSITION_LIMIT (long, trend up)
    diff < -ENTRY_DELTA  → target = -POSITION_LIMIT (short, trend down)
    |diff| < EXIT_DELTA  → target = 0 (trend faded)

Take liquidity to reach target — momentum strategies pay the spread to
catch the move; passive quoting backwards into a trend bleeds.

Use when: a product persistently trends within rolling windows (positive
return autocorrelation, drift > noise).
"""
from __future__ import annotations

import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- config ----------
PRODUCT: str = "ROBOT_VACUUMING"
POSITION_LIMIT: int = 10
N_FAST: int = 20
N_SLOW: int = 100
ENTRY_DELTA: float = 1.5               # |fast - slow| above this → enter
EXIT_DELTA: float = 0.4                # |fast - slow| below this → flatten
WARMUP: int = 30


# ---------- Logger ----------
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
    def compress_observations(self, observations: Observation) -> list[Any]:
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


def update_ema(prev: float | None, x: float, n: int) -> float:
    alpha = 2.0 / (n + 1)
    return x if prev is None else alpha * x + (1 - alpha) * prev


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        ema_fast: float | None = data.get("ema_fast")
        ema_slow: float | None = data.get("ema_slow")
        seen: int = data.get("seen", 0)

        result: dict[Symbol, list[Order]] = {}
        depth = state.order_depths.get(PRODUCT)
        if depth is None:
            td = json.dumps({"ema_fast": ema_fast, "ema_slow": ema_slow, "seen": seen})
            logger.flush(state, result, 0, td); return result, 0, td

        mid = mid_of(depth)
        bid, ask = best_bid_ask(depth)
        pos = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if mid is not None:
            ema_fast = update_ema(ema_fast, mid, N_FAST)
            ema_slow = update_ema(ema_slow, mid, N_SLOW)
            seen += 1

        if (mid is not None and bid is not None and ask is not None
                and ema_fast is not None and ema_slow is not None and seen >= WARMUP):
            diff = ema_fast - ema_slow
            logger.print(f"mid={mid:.2f} fast={ema_fast:.2f} slow={ema_slow:.2f} diff={diff:+.2f} pos={pos}")

            # ---- target position ----
            if diff > ENTRY_DELTA:
                target = POSITION_LIMIT
            elif diff < -ENTRY_DELTA:
                target = -POSITION_LIMIT
            elif abs(diff) < EXIT_DELTA:
                target = 0
            else:
                target = pos                        # hold (between thresholds)

            delta = target - pos
            if delta > 0:
                # need to buy; lift the ask
                fill = min(delta, -depth.sell_orders.get(ask, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, ask, fill))
            elif delta < 0:
                # need to sell; hit the bid
                fill = min(-delta, depth.buy_orders.get(bid, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, bid, -fill))

        if orders:
            result[PRODUCT] = orders

        trader_data = json.dumps({"ema_fast": ema_fast, "ema_slow": ema_slow, "seen": seen})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
