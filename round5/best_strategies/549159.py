from datamodel import Order, TradingState

class Trader:
    def __init__(self):
        # Définissez ici votre famille de produits "à la main"
        self.target_products =  ["PEBBLES_L",
                                "UV_VISOR_ORANGE",                               
                                "GALAXY_SOUNDS_SOLAR_FLAMES",  
                                "OXYGEN_SHAKE_CHOCOLATE",
                                "OXYGEN_SHAKE_EVENING_BREATH",
                                "ROBOT_IRONING",
                                "ROBOT_LAUNDRY",
                                "ROBOT_MOPPING",
                                "MICROCHIP_CIRCLE",
                                "TRANSLATOR_VOID_BLUE",
                                "TRANSLATOR_GRAPHITE_MIST"]
        self.quantity = 1 
        self.pos_limit = 10

    def run(self, state: TradingState) -> dict[str, list[Order]]:
        result = {}

        # On ne traite que les produits définis dans la famille
        for product in self.target_products:
            
            # Sécurité : Vérifie si le produit est bien dans le marché actuel
            if product not in state.order_depths:
                continue
                
            order_depth = state.order_depths[product]
            current_pos = state.position.get(product, 0)
            
            if not order_depth.buy_orders or not order_depth.sell_orders:
                continue
                
            # Calcul du prix "Best Maker"
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            
            my_bid = best_bid + 1
            my_ask = best_ask - 1
            
            orders = []
            
            # Gestion d'inventaire : Limite à +/- 10
            if current_pos < self.pos_limit:
                orders.append(Order(product, my_bid, self.quantity))
            
            if current_pos > -self.pos_limit:
                orders.append(Order(product, my_ask, -self.quantity))
                
            # Validation avant envoi
            if my_bid < my_ask:
                result[product] = orders
                
        return result, 0, ""