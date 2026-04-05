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

class Trader:
    
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result = {}
        conversions = 1
        
        PRODUCT = "TOMATOES" 
        POSITION_LIMIT = 80
        # On définit un seuil à partir duquel on commence à "pousser" pour rééquilibrer
        REBALANCE_THRESHOLD = 50 
        
        if PRODUCT not in state.order_depths:
            return result, conversions, ""
            
        order_depth = state.order_depths[PRODUCT]
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        
        if not best_bid or not best_ask:
            return result, conversions, ""

        fair_price = (best_bid + best_ask) / 2
        orders: List[Order] = []
        current_pos = state.position.get(PRODUCT, 0)

        # ---------------------------------------------------------
        # 1. TAKER BERSERKER (TOUJOURS ACTIF)
        # ---------------------------------------------------------
        # On ne coupe jamais l'agressivité, on prend tout ce qui est rentable
        for price, vol in order_depth.sell_orders.items():
            if price < fair_price:
                vol_to_buy = min(abs(vol), POSITION_LIMIT - current_pos)
                if vol_to_buy > 0:
                    orders.append(Order(PRODUCT, price, vol_to_buy))
                    current_pos += vol_to_buy

        for price, vol in order_depth.buy_orders.items():
            if price > fair_price:
                vol_to_sell = min(vol, POSITION_LIMIT + current_pos)
                if vol_to_sell > 0:
                    orders.append(Order(PRODUCT, price, -vol_to_sell))
                    current_pos -= vol_to_sell

        # ---------------------------------------------------------
        # 2. MAKER DYNAMIQUE AVEC REEQUILIBRAGE PASSIF
        # ---------------------------------------------------------
        remaining_buy_cap = POSITION_LIMIT - current_pos
        remaining_sell_cap = -POSITION_LIMIT - current_pos

        # Logique de prix Maker
        if current_pos >= REBALANCE_THRESHOLD:
            # SKEW LONG : On veut vendre agressivement en passif
            # On place la vente au Fair Price (très attractif)
            maker_ask = math.ceil(fair_price) 
            # On reste très timide sur l'achat (on se met loin derrière le best_bid)
            maker_bid = best_bid - 1
            logger.print(f"🔄 SKEW LONG ({current_pos}): Maker Sell placé au Fair Price ({maker_ask})")
            
        elif current_pos <= -REBALANCE_THRESHOLD:
            # SKEW SHORT : On veut racheter agressivement en passif
            # On place l'achat au Fair Price
            maker_bid = math.floor(fair_price)
            # On reste timide sur la vente
            maker_ask = best_ask + 1
            logger.print(f"🔄 SKEW SHORT ({current_pos}): Maker Buy placé au Fair Price ({maker_bid})")
            
        else:
            # POSITION NEUTRE : Pennying classique pour maximiser le profit
            maker_bid = best_bid + 1
            maker_ask = best_ask - 1

        # Envoi des ordres Maker
        if remaining_buy_cap > 0:
            orders.append(Order(PRODUCT, int(maker_bid), remaining_buy_cap))
        if remaining_sell_cap < 0:
            orders.append(Order(PRODUCT, int(maker_ask), remaining_sell_cap))

        result[PRODUCT] = orders
        logger.flush(state, result, conversions, "")
        return result, conversions, ""