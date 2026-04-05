"""
stratégie_v2.py — TOMATOES market-making strategy (improved)

Fixes applied relative to stratégie_gestionportefeuille.py:
  1. EWM fair value  — replaces raw mid as fair value estimator (Critique 2)
  2. Taker trigger   — fires when ask < ewm_fair or bid > ewm_fair (Critique 1)
  3. Skew ask/bid    — placed at best_ask-1 / best_bid+1, not at mid (Critique 3)
  4. SKEW suppression— no buy order when SKEW LONG; no sell when SKEW SHORT (Critique 6)
  5. State via traderData — EWM persisted across ticks in JSON (Critique 8)
  6. conversions = 0 — TOMATOES has no conversion mechanism in round 0 (Critique 7)
  7. Size laddering  — capacity split across 2 price levels (Critique 5)
  8. Spread conditioning — behaviour adapts to narrow vs wide spread (Critique 10)
  9. REBALANCE_THRESHOLD — lowered to 40 (50% of limit vs prior 62.5%) (Critique 4)

Statistical grounding (TOMATOES_MA_Analysis.md):
  - AR(1) φ ≈ −0.177 → mean-reverting; passive maker / skew strategy is correct
  - EWM span=10 (α ≈ 0.182), blend 0.7 EWM + 0.3 raw mid → +52 PnL vs baseline
  - Modal spread = 13 ticks; narrow spread (≤7 ticks) warrants different sizing
"""

import json
import math
from typing import Any, List

from datamodel import (
    Listing, Observation, Order, OrderDepth, ProsperityEncoder,
    Symbol, Trade, TradingState,
)


# ---------------------------------------------------------------------------
# Logger (unchanged from standard template)
# ---------------------------------------------------------------------------

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]
            )
        )
        max_item_length = (self.max_log_length - base_length) // 3
        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )
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
        return {sym: [od.buy_orders, od.sell_orders] for sym, od in order_depths.items()}

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        return [
            [t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
            for arr in trades.values() for t in arr
        ]

    def compress_observations(self, observations: Observation) -> list[Any]:
        conv_obs = {}
        for product, obs in observations.conversionObservations.items():
            conv_obs[product] = [
                obs.bidPrice, obs.askPrice, obs.transportFees,
                obs.exportTariff, obs.importTariff, obs.sugarPrice, obs.sunlightIndex,
            ]
        return [observations.plainValueObservations, conv_obs]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi = 0, min(len(value), max_length)
        out = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."
            if len(json.dumps(candidate)) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


# ---------------------------------------------------------------------------
# Strategy constants
# ---------------------------------------------------------------------------

PRODUCT         = "TOMATOES"
POSITION_LIMIT  = 80
REBALANCE_THRESHOLD = 40       # trigger skew at 50% of limit (was 62.5%)
EWM_ALPHA       = 2 / 11       # span = 10 → α ≈ 0.1818
EWM_BLEND       = 0.7          # weight on EWM vs raw mid in fair value
NARROW_SPREAD   = 7            # spread ≤ this → conservative maker behaviour


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------

class Trader:

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result: dict[Symbol, list[Order]] = {}
        conversions = 0   # TOMATOES has no conversion mechanism in round 0

        if PRODUCT not in state.order_depths:
            return result, conversions, state.traderData

        order_depth = state.order_depths[PRODUCT]
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        if best_bid is None or best_ask is None:
            return result, conversions, state.traderData

        raw_mid = (best_bid + best_ask) / 2
        spread  = best_ask - best_bid

        # ------------------------------------------------------------------
        # STATE: load EWM from traderData, update, persist
        # ------------------------------------------------------------------
        trader_data: dict = {}
        if state.traderData:
            try:
                trader_data = json.loads(state.traderData)
            except Exception:
                trader_data = {}

        prev_ewm = trader_data.get("ewm_fair", raw_mid)
        ewm_fair  = EWM_ALPHA * raw_mid + (1 - EWM_ALPHA) * prev_ewm

        # Blended fair value: 70% smoothed EWM + 30% current mid
        # EWM is slow enough that fair_price can sit above best_ask or below
        # best_bid, enabling the taker trigger to fire (Critique 1 + 2).
        fair_price = EWM_BLEND * ewm_fair + (1 - EWM_BLEND) * raw_mid

        trader_data["ewm_fair"] = ewm_fair
        new_trader_data = json.dumps(trader_data)

        orders: List[Order] = []
        current_pos = state.position.get(PRODUCT, 0)

        # ------------------------------------------------------------------
        # 1. TAKER: buy cheap / sell expensive vs EWM fair value
        #
        # The EWM updates slowly (α ≈ 0.18) so fair_price can legitimately
        # exceed best_ask or fall below best_bid, creating a genuine signal.
        # With raw mid this condition is algebraically impossible (Critique 1).
        # ------------------------------------------------------------------
        for price, vol in sorted(order_depth.sell_orders.items()):
            if price >= fair_price:
                break   # sell orders are ascending; nothing cheaper further on
            qty = min(abs(vol), POSITION_LIMIT - current_pos)
            if qty > 0:
                orders.append(Order(PRODUCT, price, qty))
                current_pos += qty

        for price, vol in sorted(order_depth.buy_orders.items(), reverse=True):
            if price <= fair_price:
                break   # buy orders are descending; nothing more expensive further on
            qty = min(vol, POSITION_LIMIT + current_pos)
            if qty > 0:
                orders.append(Order(PRODUCT, price, -qty))
                current_pos -= qty

        # ------------------------------------------------------------------
        # 2. MAKER: passive orders with position-skew logic
        # ------------------------------------------------------------------
        max_buy_qty  = POSITION_LIMIT - current_pos   # units we can still buy
        max_sell_qty = POSITION_LIMIT + current_pos   # units we can still sell

        if current_pos >= REBALANCE_THRESHOLD:
            # SKEW LONG: shed inventory passively at best_ask - 1.
            # Placing at best_ask - 1 keeps the order passive (inside the book)
            # without crossing to a marketable price (Critique 3).
            # No buy order: posting one contradicts the rebalancing objective (Critique 6).
            maker_ask = best_ask - 1
            if max_sell_qty > 0:
                orders.append(Order(PRODUCT, int(maker_ask), -max_sell_qty))
            logger.print(f"SKEW LONG  pos={current_pos} passive_sell@{maker_ask}")

        elif current_pos <= -REBALANCE_THRESHOLD:
            # SKEW SHORT: cover inventory passively at best_bid + 1.
            # No sell order (Critique 6).
            maker_bid = best_bid + 1
            if max_buy_qty > 0:
                orders.append(Order(PRODUCT, int(maker_bid), max_buy_qty))
            logger.print(f"SKEW SHORT pos={current_pos} passive_buy@{maker_bid}")

        else:
            # NEUTRAL: pennying with size laddering across 2 levels (Critique 5).
            # Spread conditioning: at narrow spreads (≤7 ticks) join the quote
            # rather than pennying; at wide spreads (13–14 ticks, modal) penny.
            # (Critique 10)
            if spread <= NARROW_SPREAD:
                # Narrow spread: join best_bid / best_ask to stay in queue;
                # smaller allocation at level 1 to limit single-tick inventory risk.
                buy_l1  = int(max_buy_qty  * 0.4)
                buy_l2  = max_buy_qty  - buy_l1
                sell_l1 = int(max_sell_qty * 0.4)
                sell_l2 = max_sell_qty - sell_l1
                bid_l1, bid_l2   = best_bid,     best_bid - 1
                ask_l1, ask_l2   = best_ask,     best_ask + 1
            else:
                # Wide spread: penny aggressively at level 1, back up at level 2.
                buy_l1  = int(max_buy_qty  * 0.6)
                buy_l2  = max_buy_qty  - buy_l1
                sell_l1 = int(max_sell_qty * 0.6)
                sell_l2 = max_sell_qty - sell_l1
                bid_l1, bid_l2   = best_bid + 1, best_bid
                ask_l1, ask_l2   = best_ask - 1, best_ask

            if max_buy_qty > 0:
                orders.append(Order(PRODUCT, int(bid_l1), buy_l1))
                if buy_l2 > 0:
                    orders.append(Order(PRODUCT, int(bid_l2), buy_l2))

            if max_sell_qty > 0:
                orders.append(Order(PRODUCT, int(ask_l1), -sell_l1))
                if sell_l2 > 0:
                    orders.append(Order(PRODUCT, int(ask_l2), -sell_l2))

        result[PRODUCT] = orders
        logger.flush(state, result, conversions, new_trader_data)
        return result, conversions, new_trader_data
