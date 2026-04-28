"""
Pairs trading — round-5 cointegrated edges (combined trader).

Two pairs (only ones with coint_p < 0.05 across the 14 PAIR_ANCHOR candidates):

    PAIR 1 — MICROCHIP_SQUARE / MICROCHIP_RECTANGLE
        coint_p = 0.0196, corr_mid = -0.882
        β_seed  = corr · σ_S/σ_R = -0.882 · 1830.25 / 752.02 ≈ -2.146

    PAIR 2 — UV_VISOR_AMBER / UV_VISOR_MAGENTA
        coint_p = 0.0416, corr_mid = -0.867
        β_seed  = corr · σ_A/σ_M = -0.867 · 996.92 / 613.55 ≈ -1.409

Both pairs are anti-correlated yet cointegrated — their negative-β linear
combination is stationary. With β < 0 a "long-spread" position holds the
*same* sign on both legs (long both, or short both); a "short-spread"
position is the mirror. This is joint co-spike mean reversion.

Mechanics (per pair, independent state and orders):
    spread_t = mid_A - β · mid_B            β seeded from research, refined rolling
    z_t      = (spread_t - μ_W) / σ_W       W-tick rolling moments

    z >  ENTRY_Z → SHORT A, target_B = -round(β·target_A)
    z < -ENTRY_Z → LONG  A, target_B = -round(β·target_A)
    |z| < EXIT_Z → flatten
    |z| > STOP_Z → flatten (regime break)

Sizing under POSITION_LIMIT = 10 (round-5 spec):
    With |β| > 1, B-leg saturates first → max_A = floor(10 / |β|).
    Multi-level book walking on entry / exit / stop — at limit-10, single-touch
    fills routinely fall short of the target delta.

Adapted from `round5/strats/strat_pairs_spread.py`. Improvements:
    - β seeded per pair from research stats (no cold-start trading on noise).
    - Rolling β refinement clamped to ±BETA_CLAMP of seed (regime-break guard).
    - W = 300 ticks (cointegration timescale), WARMUP = 60.
    - Multi-level walk_buy / walk_sell instead of single-touch fills.
    - Two pairs in one trader; per-pair state isolated in trader_data.
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
    key: str                   # state-dict key
    a: str
    b: str
    beta_seed: float
    position_limit: int = 10
    window: int = 300
    warmup: int = 60
    entry_z: float = 2.0
    exit_z: float = 0.4
    stop_z: float = 4.0
    beta_clamp: float = 0.5    # rolling β must stay within ±50% of seed


PAIRS: list[PairConfig] = [
    PairConfig(key="mc_sr",  a="MICROCHIP_SQUARE", b="MICROCHIP_RECTANGLE", beta_seed=-2.146),
    PairConfig(key="uv_am",  a="UV_VISOR_AMBER",   b="UV_VISOR_MAGENTA",   beta_seed=-1.409),
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


def regression_beta(ys: list[float], xs: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs) or 1e-9
    return num / den


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


def trade_pair(cfg: PairConfig, state: TradingState, store: dict,
               result: dict[Symbol, list[Order]]) -> None:
    """Mutates `store` and `result` in place for one pair."""
    a_hist: list[float] = store.get("a_hist", [])
    b_hist: list[float] = store.get("b_hist", [])
    spreads: list[float] = store.get("spreads", [])

    d_a = state.order_depths.get(cfg.a)
    d_b = state.order_depths.get(cfg.b)
    if d_a is None or d_b is None:
        store["a_hist"], store["b_hist"], store["spreads"] = a_hist, b_hist, spreads
        return

    mid_a = mid_of(d_a)
    mid_b = mid_of(d_b)
    pos_a = state.position.get(cfg.a, 0)
    pos_b = state.position.get(cfg.b, 0)
    if mid_a is None or mid_b is None:
        store["a_hist"], store["b_hist"], store["spreads"] = a_hist, b_hist, spreads
        return

    a_hist.append(mid_a); b_hist.append(mid_b)
    if len(a_hist) > cfg.window: a_hist = a_hist[-cfg.window:]
    if len(b_hist) > cfg.window: b_hist = b_hist[-cfg.window:]

    beta = cfg.beta_seed
    if len(a_hist) >= cfg.warmup:
        beta_roll = regression_beta(a_hist, b_hist)
        lo = cfg.beta_seed * (1.0 - cfg.beta_clamp)
        hi = cfg.beta_seed * (1.0 + cfg.beta_clamp)
        if lo > hi:
            lo, hi = hi, lo
        beta = max(lo, min(hi, beta_roll))

    spread = mid_a - beta * mid_b
    spreads.append(spread)
    if len(spreads) > cfg.window: spreads = spreads[-cfg.window:]

    if len(spreads) >= cfg.warmup:
        mu = statistics.fmean(spreads)
        sd = statistics.pstdev(spreads) or 1e-9
        z = (spread - mu) / sd

        max_a_by_b = int(cfg.position_limit / max(abs(beta), 1e-9))
        max_a = max(1, min(cfg.position_limit, max_a_by_b))

        target_a: int = pos_a
        if abs(z) > cfg.stop_z:
            target_a = 0
        elif z > cfg.entry_z:
            target_a = -max_a
        elif z < -cfg.entry_z:
            target_a = +max_a
        elif abs(z) < cfg.exit_z:
            target_a = 0

        target_b = -int(round(beta * target_a))
        target_b = max(-cfg.position_limit, min(cfg.position_limit, target_b))

        logger.print(f"[{cfg.key}] mA={mid_a:.1f} mB={mid_b:.1f} β={beta:+.3f} "
                     f"spr={spread:+.1f} μ={mu:+.1f} σ={sd:.2f} z={z:+.2f} "
                     f"pA={pos_a}→{target_a} pB={pos_b}→{target_b}")

        d_pos_a = target_a - pos_a
        d_pos_b = target_b - pos_b
        orders_a: list[Order] = []
        orders_b: list[Order] = []
        if d_pos_a > 0:   orders_a += walk_buy(cfg.a, d_a,  d_pos_a)
        elif d_pos_a < 0: orders_a += walk_sell(cfg.a, d_a, -d_pos_a)
        if d_pos_b > 0:   orders_b += walk_buy(cfg.b, d_b,  d_pos_b)
        elif d_pos_b < 0: orders_b += walk_sell(cfg.b, d_b, -d_pos_b)

        if orders_a:
            result.setdefault(cfg.a, []).extend(orders_a)
        if orders_b:
            result.setdefault(cfg.b, []).extend(orders_b)

    store["a_hist"], store["b_hist"], store["spreads"] = a_hist, b_hist, spreads


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
