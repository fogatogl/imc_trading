from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import json
import math

import json
from typing import Any

from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
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
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

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

            encoded_candidate = json.dumps(candidate)

            if len(encoded_candidate) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        return out


logger = Logger()
 

import math
from typing import Dict, List, Tuple

import math
from typing import Dict, List, Tuple
from datamodel import TradingState, Order, Symbol

class Trader:

    def __init__(self):
        self._tom_ema = None

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result = {}
        conversions = 0

        # Charger l'historique des mid_prices depuis trader_data
        trader_data = {}
        if state.traderData and state.traderData != "":
            trader_data = json.loads(state.traderData)

        # ══════════════════════════════════════════════════════════
        #  ASH_COATED_OSMIUM — TAKER mean-reversion + MAKER
        #  1) Taker : spread < 7 ET |z_score| > 2 → hit bid/ask
        #  2) Maker : penny-jumping + inventory skew + imbalance
        # ══════════════════════════════════════════════════════════
        ASH = "ASH_COATED_OSMIUM"
        POSITION_LIMIT = 80
        MA_WINDOW = 20
        SPREAD_THRESHOLD = 7
        Z_THRESHOLD = 2

        # Paramètres maker
        BASE_ORDER_SIZE = 15
        SKEW_THRESHOLD = 50

        ash_prices = trader_data.get("ash_prices", [])

        if ASH in state.order_depths:
            od = state.order_depths[ASH]
            ash_pos = state.position.get(ASH, 0)
            ash_orders: List[Order] = []

            best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
            best_ask = min(od.sell_orders.keys()) if od.sell_orders else None

            if best_bid and best_ask:
                mid = (best_bid + best_ask) / 2.0
                spread = best_ask - best_bid
                best_bid_vol = od.buy_orders[best_bid]
                best_ask_vol = abs(od.sell_orders[best_ask])

                ash_prices.append(mid)
                if len(ash_prices) > MA_WINDOW:
                    ash_prices = ash_prices[-MA_WINDOW:]

                taker_fired = False

                # --- TAKER : mean-reversion sur z-score ---
                if len(ash_prices) == MA_WINDOW and spread < SPREAD_THRESHOLD:
                    ma_20 = sum(ash_prices) / MA_WINDOW
                    std = (sum((p - ma_20) ** 2 for p in ash_prices) / MA_WINDOW) ** 0.5

                    if std > 0:
                        z_score = (mid - ma_20) / std

                        TAKER_LIMIT = 20
                        buy_cap = max(0, TAKER_LIMIT - ash_pos)
                        sell_cap = max(0, TAKER_LIMIT + ash_pos)

                        if z_score > Z_THRESHOLD and sell_cap > 0:
                            qty = min(sell_cap, abs(od.buy_orders[best_bid]))
                            if qty > 0:
                                ash_orders.append(Order(ASH, best_bid, -qty))
                                taker_fired = True

                        elif z_score < -Z_THRESHOLD and buy_cap > 0:
                            qty = min(buy_cap, abs(od.sell_orders[best_ask]))
                            if qty > 0:
                                ash_orders.append(Order(ASH, best_ask, qty))
                                taker_fired = True

                        elif abs(z_score) < 0.5 and ash_pos != 0:
                            if ash_pos > 0:
                                ash_orders.append(Order(ASH, best_bid, -ash_pos))
                            else:
                                ash_orders.append(Order(ASH, best_ask, -ash_pos))
                            taker_fired = True

                # --- MAKER : penny-jumping + skew + imbalance (dynamic sizing) ---
                if not taker_fired:
                    # Order book imbalance
                    total_volume = best_bid_vol + best_ask_vol
                    imbalance_ratio = best_bid_vol / total_volume if total_volume > 0 else 0.5
                    imbalance_delta = best_bid_vol - best_ask_vol

                    # Penny-jumping
                    if spread > 2:
                        my_bid = best_bid + 1
                        my_ask = best_ask - 1
                    else:
                        my_bid = best_bid
                        my_ask = best_ask

                    # Inventory skew
                    if ash_pos > SKEW_THRESHOLD:
                        my_ask -= 1
                        my_bid -= 2
                    elif ash_pos < -SKEW_THRESHOLD:
                        my_bid += 1
                        my_ask += 2

                    # Régime imbalance avec taille dynamique
                    if imbalance_ratio > 0.75 and imbalance_delta > 100:
                        # GOLDEN SETUP (Massive Buy Wall) — accumulate long, refuse to sell cheap
                        current_max_size = 40
                        my_ask = best_ask + 20
                    elif imbalance_ratio < 0.25 and imbalance_delta < -100:
                        # GOLDEN SETUP (Massive Sell Wall) — accumulate short, refuse to buy expensive
                        current_max_size = 40
                        my_bid = best_bid - 20
                    elif imbalance_ratio > 0.70 and imbalance_delta > 40:
                        # GOOD SETUP (Strong momentum)
                        current_max_size = 25
                        my_ask = best_ask + 10
                    elif imbalance_ratio < 0.30 and imbalance_delta < -40:
                        # GOOD SETUP (Strong momentum)
                        current_max_size = 25
                        my_bid = best_bid - 10
                    else:
                        # NORMAL MARKET (Low conviction, play it safe)
                        current_max_size = BASE_ORDER_SIZE

                    available_to_buy = min(POSITION_LIMIT - ash_pos, current_max_size)
                    available_to_sell = max(-POSITION_LIMIT - ash_pos, -current_max_size)

                    # Placement des ordres maker
                    if available_to_buy > 0:
                        ash_orders.append(Order(ASH, my_bid, available_to_buy))
                    if available_to_sell < 0:
                        ash_orders.append(Order(ASH, my_ask, available_to_sell))

            result[ASH] = ash_orders

        trader_data["ash_prices"] = ash_prices

        # Pas de trading sur INTARIAN_PEPPER_ROOT pour l'instant
        result["INTARIAN_PEPPER_ROOT"] = []


        logger.flush(state, result, conversions, json.dumps(trader_data))
        return result, conversions, json.dumps(trader_data)