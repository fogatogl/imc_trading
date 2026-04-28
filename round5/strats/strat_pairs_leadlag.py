"""
Pairs trading — lead-lag (case 2: leader predicts follower with lag k).

Premise:
    Two products are related, but one moves first. The leader's return
    over the past LAG ticks predicts the follower's next move. Trade the
    follower directionally; do NOT trade the leader on this signal.

Mechanics:
    leader_ret_t = (leader_t - leader_{t-LAG}) / leader_{t-LAG}

    leader_ret >  RET_THRESHOLD  → target follower = +POSITION_LIMIT
    leader_ret < -RET_THRESHOLD  → target follower = -POSITION_LIMIT
    else                         → target = 0

Hold the position; re-evaluate the signal each tick. Use take-liquidity
to reach the target — passive quoting in the wrong direction of a
predicted move bleeds.

Use when: cross-correlation between the cluster aggregates is high *only*
at lag k > 0 (and stable across rolling windows — see analysis_brief.md
"stability test").
"""
from __future__ import annotations

import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- config ----------
LEADER: str = "MICROCHIP_CIRCLE"
FOLLOWER: str = "MICROCHIP_OVAL"
POSITION_LIMIT: int = 10               # applies to FOLLOWER (only leg traded)
LAG: int = 5                           # ticks: leader's t-LAG → t move predicts follower's next move
RET_THRESHOLD: float = 0.001           # |leader return over LAG| above this → act
NEUTRAL_BAND: float = 0.0003           # |return| below this → flatten


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
        leader_hist: list[float] = data.get("leader_hist", [])

        result: dict[Symbol, list[Order]] = {}
        d_lead = state.order_depths.get(LEADER)
        d_foll = state.order_depths.get(FOLLOWER)
        if d_lead is None or d_foll is None:
            td = json.dumps({"leader_hist": leader_hist})
            logger.flush(state, result, 0, td); return result, 0, td

        mid_lead = mid_of(d_lead)
        mid_foll = mid_of(d_foll)
        bid_f, ask_f = best_bid_ask(d_foll)
        pos_f = state.position.get(FOLLOWER, 0)
        orders_f: list[Order] = []

        if mid_lead is not None:
            leader_hist.append(mid_lead)
            if len(leader_hist) > LAG + 5:
                leader_hist = leader_hist[-(LAG + 5):]

        if (len(leader_hist) > LAG and bid_f is not None and ask_f is not None
                and mid_foll is not None):
            past = leader_hist[-(LAG + 1)]
            now = leader_hist[-1]
            ret = (now - past) / past if past else 0.0
            logger.print(f"leader: {past:.2f}→{now:.2f} ret={ret:+.5f} "
                         f"foll_mid={mid_foll:.2f} pos={pos_f}")

            if ret > RET_THRESHOLD:
                target = POSITION_LIMIT
            elif ret < -RET_THRESHOLD:
                target = -POSITION_LIMIT
            elif abs(ret) < NEUTRAL_BAND:
                target = 0
            else:
                target = pos_f                  # in dead zone → hold

            delta = target - pos_f
            if delta > 0:
                fill = min(delta, -d_foll.sell_orders.get(ask_f, 0))
                if fill > 0: orders_f.append(Order(FOLLOWER, ask_f, fill))
            elif delta < 0:
                fill = min(-delta, d_foll.buy_orders.get(bid_f, 0))
                if fill > 0: orders_f.append(Order(FOLLOWER, bid_f, -fill))

        if orders_f:
            result[FOLLOWER] = orders_f

        trader_data = json.dumps({"leader_hist": leader_hist})
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data
