"""
Mean-reverting strategy — fixed anchor + volatility armor.

Shape:
    dev = mid - ANCHOR
    |dev| > TAKE_DEV   → take liquidity (shark)
    |dev| > MAKER_DEV  → quote passive on the dislocated side
    vol_scale = min(1, VOL_CAP / realised_std)
    effective_position_limit = POSITION_LIMIT * vol_scale  (shrinks when vol spikes)

This is the round-3 hydrogel block (anchor 9991, dev 22/14, vol cap 30) generalised.
Use when: a product trades around a stable, near-constant fair value
(stationary, not drifting) — the anchor is the half-life-zero limit of a
very slow EMA. If anchor unknown, set ANCHOR = None and the strategy uses a
slow EMA fallback.
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
PRODUCT: str = "PEBBLES_M"
POSITION_LIMIT: int = 10
ANCHOR: float | None = 10000.0         # set None to use slow-EMA fallback
EMA_HALFLIFE: int = 500                # only used when ANCHOR is None
TAKE_DEV: float = 22.0                 # |dev| above this → take
MAKER_DEV: float = 14.0                # |dev| above this → quote passive only
MAKER_TICKS: int = 5                   # offset from anchor for passive quotes
MAKER_SIZE: int = 5
VOL_WINDOW: int = 50
VOL_CAP: float = 30.0                  # numerator in vol_scale; tune to product noise scale
WARMUP: int = 20


# ---------- Logger (shared contract) ----------
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

    def compress_listings(self, listings):  return [[l.symbol, l.product, l.denomination] for l in listings.values()]
    def compress_order_depths(self, ods):    return {s: [d.buy_orders, d.sell_orders] for s, d in ods.items()}
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
    def to_json(self, value): return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))
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
        slow_ema: float | None = data.get("slow_ema")

        result: dict[Symbol, list[Order]] = {}
        depth = state.order_depths.get(PRODUCT)
        if depth is None:
            td = json.dumps({"mid_history": history, "slow_ema": slow_ema})
            logger.flush(state, result, 0, td); return result, 0, td

        mid = mid_of(depth)
        bid, ask = best_bid_ask(depth)
        pos = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if mid is not None:
            history.append(mid)
            if len(history) > VOL_WINDOW * 2:
                history = history[-VOL_WINDOW * 2:]
            # update slow EMA (used only if ANCHOR is None)
            alpha = 2.0 / (EMA_HALFLIFE + 1)
            slow_ema = mid if slow_ema is None else alpha * mid + (1 - alpha) * slow_ema

        anchor = ANCHOR if ANCHOR is not None else slow_ema

        if mid is not None and bid is not None and ask is not None and anchor is not None and len(history) >= WARMUP:
            recent = history[-VOL_WINDOW:]
            sigma = statistics.pstdev(recent) or 1e-9
            vol_scale = min(1.0, VOL_CAP / sigma)
            eff_limit = max(1, int(round(POSITION_LIMIT * vol_scale)))
            dev = mid - anchor
            logger.print(f"mid={mid:.1f} anchor={anchor:.1f} dev={dev:+.1f} sd={sigma:.2f} "
                         f"scale={vol_scale:.2f} eff={eff_limit} pos={pos}")

            # ---- shark take ----
            if dev > TAKE_DEV:
                room = eff_limit + pos
                fill = min(room, depth.buy_orders.get(bid, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, bid, -fill))
            elif dev < -TAKE_DEV:
                room = eff_limit - pos
                fill = min(room, -depth.sell_orders.get(ask, 0))
                if fill > 0:
                    orders.append(Order(PRODUCT, ask, fill))

            # ---- passive maker layer ----
            # Only quote on the dislocated side when |dev| > MAKER_DEV.
            # When |dev| < MAKER_DEV, both sides quote symmetrically around anchor.
            buy_px = int(round(anchor - MAKER_TICKS))
            sell_px = int(round(anchor + MAKER_TICKS))
            buy_room = eff_limit - pos
            sell_room = eff_limit + pos

            if dev > MAKER_DEV:
                # price elevated → maker on sell only
                if sell_room > 0 and sell_px > bid:
                    orders.append(Order(PRODUCT, sell_px, -min(MAKER_SIZE, sell_room)))
            elif dev < -MAKER_DEV:
                if buy_room > 0 and buy_px < ask:
                    orders.append(Order(PRODUCT, buy_px, min(MAKER_SIZE, buy_room)))
            else:
                if buy_room > 0 and buy_px < ask:
                    orders.append(Order(PRODUCT, buy_px, min(MAKER_SIZE, buy_room)))
                if sell_room > 0 and sell_px > bid:
                    orders.append(Order(PRODUCT, sell_px, -min(MAKER_SIZE, sell_room)))

        if orders:
            result[PRODUCT] = orders

        trader_data = json.dumps({"mid_history": history, "slow_ema": slow_ema})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
