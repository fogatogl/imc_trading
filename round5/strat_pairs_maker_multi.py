"""
Pairs trading — passive-maker overlay across 4 pairs.

Architecture: each pair runs the validated SNACKPACK maker pattern with
its own β / size / state. No cross-pair coupling — they share only the
Trader.run() entry point and the Logger.

Why each pair was included:

    | pair                                    | β_seed  | size_a/b | rationale                                                          |
    | SNACKPACK_CHOCOLATE  / SNACKPACK_VANILLA   | -1.000 | 5/5      | proven +975 standalone; β stable, |corr|=0.93                       |
    | MICROCHIP_SQUARE     / MICROCHIP_RECTANGLE | -2.146 | 4/9      | coint pair; failed taker but maker capture independent of β stability |
    | UV_VISOR_AMBER       / UV_VISOR_MAGENTA    | -1.409 | 5/7      | coint pair; same logic as MICROCHIP                                |
    | SLEEP_POD_COTTON     / SLEEP_POD_POLYESTER | +0.795 | 5/4      | high-corr (|corr|=0.88), β stable in sign                          |

All four products in each pair have bid-ask ≥ 7 ticks (SNACKPACK 17,
UV_VISOR 9-15, MICROCHIP 7-13, SLEEP_POD 9-12), so the +1/-1 inside-the-
touch maker pattern has room to operate.

Mechanics (per pair, applied independently):
    spread = mid_A - β · mid_B
    z      = (spread - μ_W) / σ_W              W=200, WARMUP=60

    z >  ENTRY_Z   → passive SELL A at ask-1, BUY B at bid+1   (improves BBO; fills off market sells/buys at old touch)
    z < -ENTRY_Z   → mirror
    |z| < EXIT_Z   → passive unwind at touch-1
    |z| > STOP_Z   → walk book to flat                          (regime-break exit)
    timestamp wrap → flush spread history                       (per-day reset)

This is an OVERLAY. Sizes are sub-limit on every leg so a primary
strategy on the same product (e.g. MR_TAKER on UV_VISOR_MAGENTA) can
co-exist within the position cap of 10.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- per-pair config ----------
@dataclass(frozen=True)
class PairConfig:
    key: str
    a: str
    b: str
    beta: float
    size_a: int
    size_b: int
    position_limit: int = 10
    window: int = 200
    warmup: int = 60
    entry_z: float = 2.0
    exit_z: float = 0.4
    stop_z: float = 4.0


PAIRS: list[PairConfig] = [
    PairConfig(key="snack",    a="SNACKPACK_CHOCOLATE",  b="SNACKPACK_VANILLA",    beta=-1.000, size_a=5, size_b=5),
    PairConfig(key="micro_sr", a="MICROCHIP_SQUARE",     b="MICROCHIP_RECTANGLE",  beta=-2.146, size_a=4, size_b=9),
    PairConfig(key="uv_am",    a="UV_VISOR_AMBER",       b="UV_VISOR_MAGENTA",     beta=-1.409, size_a=5, size_b=7),
    PairConfig(key="sleep_cp", a="SLEEP_POD_COTTON",     b="SLEEP_POD_POLYESTER",  beta=+0.795, size_a=5, size_b=4),
]


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
    """Improved-bid: bid+1 if there's room, else fall back to bid (won't fill at the touch)."""
    if qty <= 0: return []
    px = min(bid + 1, ask - 1) if ask is not None and ask > bid + 1 else bid
    return [Order(symbol, px, qty)]


def maker_sell(symbol: str, bid: int, ask: int, qty: int) -> list[Order]:
    """Improved-ask: ask-1 if there's room, else fall back to ask."""
    if qty <= 0: return []
    px = max(ask - 1, bid + 1) if bid is not None and ask > bid + 1 else ask
    return [Order(symbol, px, -qty)]


def trade_pair(cfg: PairConfig, state: TradingState, store: dict,
               result: dict[Symbol, list[Order]]) -> None:
    spreads: list[float] = store.get("spreads", [])
    last_ts: int = store.get("last_ts", -1)

    if state.timestamp < last_ts or (state.timestamp == 0 and last_ts > 0):
        spreads = []

    d_a = state.order_depths.get(cfg.a)
    d_b = state.order_depths.get(cfg.b)
    if d_a is None or d_b is None:
        store["spreads"] = spreads; store["last_ts"] = state.timestamp; return

    bid_a, ask_a = best_bid_ask(d_a)
    bid_b, ask_b = best_bid_ask(d_b)
    mid_a = mid_of(d_a)
    mid_b = mid_of(d_b)
    pos_a = state.position.get(cfg.a, 0)
    pos_b = state.position.get(cfg.b, 0)

    if mid_a is None or mid_b is None:
        store["spreads"] = spreads; store["last_ts"] = state.timestamp; return

    spread = mid_a - cfg.beta * mid_b
    spreads.append(spread)
    if len(spreads) > cfg.window: spreads = spreads[-cfg.window:]

    if (len(spreads) >= cfg.warmup
            and bid_a is not None and ask_a is not None
            and bid_b is not None and ask_b is not None):
        mu = statistics.fmean(spreads)
        sd = statistics.pstdev(spreads) or 1e-9
        z = (spread - mu) / sd

        target_a: int = pos_a
        target_b: int = pos_b
        mode = "hold"
        if abs(z) > cfg.stop_z:
            target_a = 0; target_b = 0; mode = "STOP"
        elif z > cfg.entry_z:
            # spread elevated → short A, long B (β<0 means same direction; β>0 opposite)
            target_a = -cfg.size_a
            target_b = -int(round(cfg.beta * (-cfg.size_a)))
            mode = "ENTRY-"
        elif z < -cfg.entry_z:
            target_a = +cfg.size_a
            target_b = -int(round(cfg.beta * (+cfg.size_a)))
            mode = "ENTRY+"
        elif abs(z) < cfg.exit_z:
            target_a = 0; target_b = 0; mode = "EXIT"

        target_a = max(-cfg.position_limit, min(cfg.position_limit, target_a))
        target_b = max(-cfg.position_limit, min(cfg.position_limit, target_b))
        # cap to per-pair size on B as well (not just position limit)
        target_b = max(-cfg.size_b, min(cfg.size_b, target_b))

        d_a_qty = target_a - pos_a
        d_b_qty = target_b - pos_b
        orders_a: list[Order] = []
        orders_b: list[Order] = []

        if mode == "STOP":
            if d_a_qty > 0:   orders_a += walk_buy(cfg.a, d_a,  d_a_qty)
            elif d_a_qty < 0: orders_a += walk_sell(cfg.a, d_a, -d_a_qty)
            if d_b_qty > 0:   orders_b += walk_buy(cfg.b, d_b,  d_b_qty)
            elif d_b_qty < 0: orders_b += walk_sell(cfg.b, d_b, -d_b_qty)
        else:
            if d_a_qty > 0:   orders_a += maker_buy(cfg.a, bid_a, ask_a,  d_a_qty)
            elif d_a_qty < 0: orders_a += maker_sell(cfg.a, bid_a, ask_a, -d_a_qty)
            if d_b_qty > 0:   orders_b += maker_buy(cfg.b, bid_b, ask_b,  d_b_qty)
            elif d_b_qty < 0: orders_b += maker_sell(cfg.b, bid_b, ask_b, -d_b_qty)

        if orders_a: result.setdefault(cfg.a, []).extend(orders_a)
        if orders_b: result.setdefault(cfg.b, []).extend(orders_b)

        logger.print(f"[{cfg.key}] {mode} z={z:+.2f} pA={pos_a}->{target_a} pB={pos_b}->{target_b}")

    store["spreads"] = spreads
    store["last_ts"] = state.timestamp


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            data: dict = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            data = {}

        result: dict[Symbol, list[Order]] = {}
        for cfg in PAIRS:
            store = data.setdefault(cfg.key, {})
            trade_pair(cfg, state, store, result)

        trader_data = json.dumps(data)
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
