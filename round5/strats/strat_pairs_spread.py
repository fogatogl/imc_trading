"""
Pairs trading — spread mean reversion (case 1: no lag, structural similarity).

Premise:
    Two products move together. The spread is stationary and oscillates
    around a mean. Bet on convergence.

Mechanics:
    spread_t = price_A_t - β · price_B_t
    z_t = (spread_t - rolling_mean) / rolling_std

    z >  ENTRY_Z  → SHORT A, LONG  B  (spread too wide)
    z < -ENTRY_Z  → LONG  A, SHORT B  (spread too narrow)
    |z| < EXIT_Z  → flatten both legs
    |z| > STOP_Z  → flatten (regime broke)

Sizing under POSITION_LIMIT:
    With β ≠ 1 you cannot put on equal shares of A and B. Solve for the
    *largest A-quantity* such that |β · A_qty| ≤ POSITION_LIMIT on B.

Use when: cross-correlation is high, optimal lag is 0, and the regression
residual is stationary across rolling windows.
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
PRODUCT_A: str = "MICROCHIP_CIRCLE"
PRODUCT_B: str = "MICROCHIP_OVAL"
POSITION_LIMIT: int = 10
WINDOW: int = 100
WARMUP: int = 30
ENTRY_Z: float = 2.0
EXIT_Z: float = 0.3
STOP_Z: float = 3.5
HEDGE_RATIO: float | None = 1.0        # set None → rolling regression β estimated each tick


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


def regression_beta(ys: list[float], xs: list[float]) -> float:
    """OLS slope of ys on xs, no intercept centring (use centred series)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs) or 1e-9
    return num / den


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        a_hist: list[float] = data.get("a_hist", [])
        b_hist: list[float] = data.get("b_hist", [])
        spreads: list[float] = data.get("spreads", [])

        result: dict[Symbol, list[Order]] = {}
        d_a = state.order_depths.get(PRODUCT_A)
        d_b = state.order_depths.get(PRODUCT_B)
        if d_a is None or d_b is None:
            td = json.dumps({"a_hist": a_hist, "b_hist": b_hist, "spreads": spreads})
            logger.flush(state, result, 0, td); return result, 0, td

        mid_a = mid_of(d_a)
        mid_b = mid_of(d_b)
        bid_a, ask_a = best_bid_ask(d_a)
        bid_b, ask_b = best_bid_ask(d_b)
        pos_a = state.position.get(PRODUCT_A, 0)
        pos_b = state.position.get(PRODUCT_B, 0)
        orders_a: list[Order] = []
        orders_b: list[Order] = []

        if mid_a is not None and mid_b is not None:
            a_hist.append(mid_a); b_hist.append(mid_b)
            if len(a_hist) > WINDOW: a_hist = a_hist[-WINDOW:]
            if len(b_hist) > WINDOW: b_hist = b_hist[-WINDOW:]

            beta = HEDGE_RATIO
            if beta is None and len(a_hist) >= WARMUP:
                beta = regression_beta(a_hist, b_hist)
            if beta is None:
                beta = 1.0

            spread = mid_a - beta * mid_b
            spreads.append(spread)
            if len(spreads) > WINDOW: spreads = spreads[-WINDOW:]

            if (len(spreads) >= WARMUP
                    and bid_a is not None and ask_a is not None
                    and bid_b is not None and ask_b is not None):
                mu = statistics.fmean(spreads)
                sd = statistics.pstdev(spreads) or 1e-9
                z = (spread - mu) / sd
                logger.print(f"midA={mid_a:.1f} midB={mid_b:.1f} β={beta:.3f} "
                             f"spread={spread:+.2f} μ={mu:+.2f} σ={sd:.2f} z={z:+.2f} "
                             f"posA={pos_a} posB={pos_b}")

                # ---- pick target signed quantity for A ----
                # max |A| such that |β·A| ≤ POSITION_LIMIT
                max_a_by_b = int(POSITION_LIMIT / max(abs(beta), 1e-9))
                max_a = min(POSITION_LIMIT, max_a_by_b)

                target_a: int = pos_a       # default: hold
                if abs(z) > STOP_Z:
                    target_a = 0            # regime break → flatten
                elif z > ENTRY_Z:
                    target_a = -max_a       # short A, long B
                elif z < -ENTRY_Z:
                    target_a = +max_a       # long A, short B
                elif abs(z) < EXIT_Z:
                    target_a = 0

                target_b = -int(round(beta * target_a))
                # clamp to per-leg position limit
                target_b = max(-POSITION_LIMIT, min(POSITION_LIMIT, target_b))

                # ---- execute deltas (take liquidity at touch) ----
                d_pos_a = target_a - pos_a
                d_pos_b = target_b - pos_b

                if d_pos_a > 0:
                    fill = min(d_pos_a, -d_a.sell_orders.get(ask_a, 0))
                    if fill > 0: orders_a.append(Order(PRODUCT_A, ask_a, fill))
                elif d_pos_a < 0:
                    fill = min(-d_pos_a, d_a.buy_orders.get(bid_a, 0))
                    if fill > 0: orders_a.append(Order(PRODUCT_A, bid_a, -fill))

                if d_pos_b > 0:
                    fill = min(d_pos_b, -d_b.sell_orders.get(ask_b, 0))
                    if fill > 0: orders_b.append(Order(PRODUCT_B, ask_b, fill))
                elif d_pos_b < 0:
                    fill = min(-d_pos_b, d_b.buy_orders.get(bid_b, 0))
                    if fill > 0: orders_b.append(Order(PRODUCT_B, bid_b, -fill))

        if orders_a: result[PRODUCT_A] = orders_a
        if orders_b: result[PRODUCT_B] = orders_b

        trader_data = json.dumps({"a_hist": a_hist, "b_hist": b_hist, "spreads": spreads})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
