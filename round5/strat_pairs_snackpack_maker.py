"""
Pairs trading — SNACKPACK_CHOCOLATE / SNACKPACK_VANILLA  (passive-maker variant).

Why this design:
    The taker variant (`strat_pairs_snackpack.py`) lost -86,930 over the 3
    round-5 days. Trade-level audit showed bought-high / sold-low by ~15
    ticks per round-trip per leg — pure execution cost from crossing the
    spread on entry AND exit, on both legs.

    Spread σ ≈ 37 ticks/day. Crossing cost per round-trip ≈ 30 ticks per
    unit (bid-ask + book-walk × 4 sides). Expected reversion at z=2 over
    the next 50 ticks ≈ 3 ticks per unit. Taker math is structurally
    negative; signal isn't.

    This variant POSTS at top-of-book instead of taking. Fills come when
    market flow crosses the spread to us — exactly the noise traders
    whose imbalance creates the z>2 deviation. Round-trip cost flips from
    -30 ticks/unit to ~+0 (we earn the spread we used to pay). Tiny
    expected reversion + bid-ask rebate = small but positive edge.

    Designed as an OVERLAY, not a primary — small size (TARGET_SIZE=5
    not 10), no taking on entry/exit, only taking on stop. If we don't
    get filled we don't trade. No bleed.

Mechanics:
    spread_t = mid_C + mid_V   (β=-1, stable across all 3 days)
    z_t      = (spread_t - μ_W) / σ_W

    z >  ENTRY_Z   → post passive SELL on A at best_ask, BUY on B at best_bid
    z < -ENTRY_Z   → post passive BUY  on A at best_bid, SELL on B at best_ask
    |z| < EXIT_Z   → post passive unwind at touch
    |z| > STOP_Z   → walk the book to flat (regime break — urgent)
    Day boundary detected via state.timestamp wrap → flush spread history.
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
TARGET_SIZE: int = 5         # half of limit — overlay, not primary
WINDOW: int = 200
WARMUP: int = 60
ENTRY_Z: float = 2.0
EXIT_Z: float = 0.4
STOP_Z: float = 4.0
BETA: float = -1.0


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
        if remaining <= 0: break
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
        if remaining <= 0: break
        avail = depth.buy_orders[px]
        take = min(remaining, avail)
        if take > 0:
            out.append(Order(symbol, px, -take))
            remaining -= take
    return out


def maker_buy(symbol: str, bid: int, ask: int, qty: int) -> list[Order]:
    """Post improved-bid one tick above best_bid. The backtester fills our quote against
    historical market sells at prices < our_quote (strictly worse), i.e. trades at the old
    best_bid. Falls back to best_bid only if the spread is 1 tick wide."""
    if qty <= 0: return []
    px = min(bid + 1, ask - 1) if ask is not None and ask > bid + 1 else bid
    return [Order(symbol, px, qty)]


def maker_sell(symbol: str, bid: int, ask: int, qty: int) -> list[Order]:
    """Post improved-ask one tick below best_ask."""
    if qty <= 0: return []
    px = max(ask - 1, bid + 1) if bid is not None and ask > bid + 1 else ask
    return [Order(symbol, px, -qty)]


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}
        spreads: list[float] = data.get("spreads", [])
        last_ts: int = data.get("last_ts", -1)

        # day-boundary reset
        if state.timestamp < last_ts or (state.timestamp == 0 and last_ts > 0):
            spreads = []

        result: dict[Symbol, list[Order]] = {}
        d_a = state.order_depths.get(PRODUCT_A)
        d_b = state.order_depths.get(PRODUCT_B)
        if d_a is None or d_b is None:
            td = json.dumps({"spreads": spreads, "last_ts": state.timestamp})
            logger.flush(state, result, 0, td); return result, 0, td

        bid_a, ask_a = best_bid_ask(d_a)
        bid_b, ask_b = best_bid_ask(d_b)
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

            if (len(spreads) >= WARMUP
                    and bid_a is not None and ask_a is not None
                    and bid_b is not None and ask_b is not None):
                mu = statistics.fmean(spreads)
                sd = statistics.pstdev(spreads) or 1e-9
                z = (spread - mu) / sd

                target_a: int = pos_a
                mode = "hold"
                if abs(z) > STOP_Z:
                    target_a = 0; mode = "STOP"
                elif z > ENTRY_Z:
                    target_a = -TARGET_SIZE; mode = "ENTRY-"
                elif z < -ENTRY_Z:
                    target_a = +TARGET_SIZE; mode = "ENTRY+"
                elif abs(z) < EXIT_Z:
                    target_a = 0; mode = "EXIT"

                target_b = -int(round(BETA * target_a))
                target_b = max(-POSITION_LIMIT, min(POSITION_LIMIT, target_b))

                d_a_qty = target_a - pos_a   # >0 buy, <0 sell
                d_b_qty = target_b - pos_b

                if mode == "STOP":
                    # walk book — regime break, exit now
                    if d_a_qty > 0:   orders_a += walk_buy(PRODUCT_A, d_a,  d_a_qty)
                    elif d_a_qty < 0: orders_a += walk_sell(PRODUCT_A, d_a, -d_a_qty)
                    if d_b_qty > 0:   orders_b += walk_buy(PRODUCT_B, d_b,  d_b_qty)
                    elif d_b_qty < 0: orders_b += walk_sell(PRODUCT_B, d_b, -d_b_qty)
                else:
                    # passive maker, one tick inside the touch — improves the BBO
                    if d_a_qty > 0:   orders_a += maker_buy(PRODUCT_A,  bid_a, ask_a,  d_a_qty)
                    elif d_a_qty < 0: orders_a += maker_sell(PRODUCT_A, bid_a, ask_a, -d_a_qty)
                    if d_b_qty > 0:   orders_b += maker_buy(PRODUCT_B,  bid_b, ask_b,  d_b_qty)
                    elif d_b_qty < 0: orders_b += maker_sell(PRODUCT_B, bid_b, ask_b, -d_b_qty)

                logger.print(f"{mode} mA={mid_a:.1f} mB={mid_b:.1f} spr={spread:+.1f} "
                             f"mu={mu:+.1f} sd={sd:.2f} z={z:+.2f} "
                             f"pA={pos_a}->{target_a} pB={pos_b}->{target_b}")

        if orders_a: result[PRODUCT_A] = orders_a
        if orders_b: result[PRODUCT_B] = orders_b

        trader_data = json.dumps({"spreads": spreads, "last_ts": state.timestamp})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
