from datamodel import OrderDepth, TradingState, Order
from typing import List


class Trader:
    
    PRODUCTS = [
        'UV_VISOR_YELLOW',
        'UV_VISOR_ORANGE',
        'UV_VISOR_RED',
        'UV_VISOR_MAGENTA',
    ]
    
    POSITION_LIMIT = 10
    
    def run(self, state: TradingState):
        result = {}
        
        for product in self.PRODUCTS:
            if product not in state.order_depths:
                continue
            
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            orders: List[Order] = []
            
            # Besoin des deux côtés du book
            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = orders
                continue
            
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            spread = best_ask - best_bid
            
            # Si spread trop serré, pas d'amélioration possible sans crosser
            if spread < 2:
                result[product] = orders
                continue
            
            # Capacités restantes selon position courante
            buy_capacity = self.POSITION_LIMIT - position
            sell_capacity = self.POSITION_LIMIT + position
            
            # Post bid à best_bid + 1
            if buy_capacity > 0:
                orders.append(Order(product, best_bid + 1, buy_capacity))
            
            # Post ask à best_ask - 1
            if sell_capacity > 0:
                orders.append(Order(product, best_ask - 1, -sell_capacity))
            
            result[product] = orders
        
        traderData = ""  # pas d'état à conserver
        conversions = 0
        return result, conversions, traderData