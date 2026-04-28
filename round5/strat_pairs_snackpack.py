"""
Pairs trading — SNACKPACK_CHOCOLATE / SNACKPACK_VANILLA.

Why this pair (full 100-pair scan, see audit notes):
    Single survivor of the audit-derived screen
        |corr_mid| >= 0.7  AND  no β sign flip across days
        AND  β range <= 2x  AND  per-day half-life <= 800.

    | metric           | value                                |
    | corr_mid         | -0.926  (highest of all 100 pairs)   |
    | β per day        | -0.81 / -1.00 / -0.98  (stable)      |
    | β range ratio    | 1.24x                                |
    | half-life (max)  | 530 ticks  (within W=200 → 2.6 HL)   |
    | σ_spread / day   | ~37 ticks                            |
    | bid-ask per leg  | ~2 ticks  → round-trip cost ~8       |
    | typical 2σ entry | ~74 ticks  →  ~9:1 alpha:cost        |

    coint_p was 0.46 (i.e. "not cointegrated") — but only because spread μ
    steps cleanly between days (18098 → 19976 → 19653). Engle-Granger
    interprets that across-day drift as non-stationarity. We don't trade
    across days; intra-day reversion is the cleanest in the universe.

Key changes vs the failed strat_pairs_coint.py:
    - β hardcoded at -1.0 (stable, no rolling refinement noise).
    - W = 200 (smaller — spread mean re-anchors fast across day boundaries).
    - WARMUP = 60.
    - No β-clamp gymnastics (β is already known stable).
    - Sizing: |β|=1 → full 10/10 size on both legs at limit-10.

Mechanics:
    spread_t = mid_C + mid_V              (β=-1 → spread = C - (-1)·V = C + V)
    z_t      = (spread_t - μ_W) / σ_W

    z >  ENTRY_Z → SHORT C, SHORT V       (joint co-spike: both elevated)
    z < -ENTRY_Z → LONG  C, LONG  V       (joint trough)
    |z| < EXIT_Z → flatten
    |z| > STOP_Z → flatten (regime break)
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
PRODUCT_A: str = "SNACKPACK_CHOCOLATE"
PRODUCT_B: str = "SNACKPACK_VANILLA"
POSITION_LIMIT: int = 10
WINDOW: int = 200
WARMUP: int = 60
ENTRY_Z: float = 2.0
EXIT_Z: float = 0.4
STOP_Z: float = 4.0
BETA: float = -1.0           # stable across days; no rolling refinement


# ---------- Logger (DO NOT MODIFY — visualizer contract) ----------
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


def walk_buy(symbol: str, depth: OrderDepth, qty: int) -> list[Order]:
    out: list[Order] = []
    remaining = qty
    for px in sorted(depth.sell_orders.keys()):
        if remaining <= 0:
            break
        avail = -depth.sell_orders[px]
        take = min(remaining, avail)
        if take > 0:
            out.append(Order(symbol, px, take))
            remaining -= take
    return out


def walk_sell(symbol: str, depth: OrderDepth, qty: int) -> list[Order]:
    out: list[Order] = []
    remaining = qty
    for px in sorted(depth.buy_orders.keys(), reverse=True):
        if remaining <= 0:
            break
        avail = depth.buy_orders[px]
        take = min(remaining, avail)
        if take > 0:
            out.append(Order(symbol, px, -take))
            remaining -= take
    return out


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        spreads: list[float] = data.get("spreads", [])
        last_ts: int = data.get("last_ts", -1)

        # day-boundary reset: timestamp jumped backwards or to 0 with prior history
        if state.timestamp < last_ts or (state.timestamp == 0 and last_ts > 0):
            spreads = []

        result: dict[Symbol, list[Order]] = {}
        d_a = state.order_depths.get(PRODUCT_A)
        d_b = state.order_depths.get(PRODUCT_B)
        if d_a is None or d_b is None:
            td = json.dumps({"spreads": spreads, "last_ts": state.timestamp})
            logger.flush(state, result, 0, td); return result, 0, td

        mid_a = mid_of(d_a)
        mid_b = mid_of(d_b)
        pos_a = state.position.get(PRODUCT_A, 0)
        pos_b = state.position.get(PRODUCT_B, 0)
        orders_a: list[Order] = []
        orders_b: list[Order] = []

        if mid_a is not None and mid_b is not None:
            spread = mid_a - BETA * mid_b
            spreads.append(spread)
            if len(spreads) > WINDOW: spreads = spreads[-WINDOW:]

            if len(spreads) >= WARMUP:
                mu = statistics.fmean(spreads)
                sd = statistics.pstdev(spreads) or 1e-9
                z = (spread - mu) / sd

                # |β|=1 → max size on both legs
                max_a = POSITION_LIMIT

                target_a: int = pos_a
                if abs(z) > STOP_Z:
                    target_a = 0
                elif z > ENTRY_Z:
                    target_a = -max_a
                elif z < -ENTRY_Z:
                    target_a = +max_a
                elif abs(z) < EXIT_Z:
                    target_a = 0

                # β=-1 → target_b = -β·target_a = +target_a (same sign)
                target_b = -int(round(BETA * target_a))
                target_b = max(-POSITION_LIMIT, min(POSITION_LIMIT, target_b))

                logger.print(f"mA={mid_a:.1f} mB={mid_b:.1f} spr={spread:+.1f} "
                             f"mu={mu:+.1f} sd={sd:.2f} z={z:+.2f} "
                             f"pA={pos_a}->{target_a} pB={pos_b}->{target_b}")

                d_pos_a = target_a - pos_a
                d_pos_b = target_b - pos_b
                if d_pos_a > 0:   orders_a += walk_buy(PRODUCT_A, d_a,  d_pos_a)
                elif d_pos_a < 0: orders_a += walk_sell(PRODUCT_A, d_a, -d_pos_a)
                if d_pos_b > 0:   orders_b += walk_buy(PRODUCT_B, d_b,  d_pos_b)
                elif d_pos_b < 0: orders_b += walk_sell(PRODUCT_B, d_b, -d_pos_b)

        if orders_a: result[PRODUCT_A] = orders_a
        if orders_b: result[PRODUCT_B] = orders_b

        trader_data = json.dumps({"spreads": spreads, "last_ts": state.timestamp})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
