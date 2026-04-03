from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    
    def bid(self):
        return 15
    
    def run(self, state: TradingState):
        result = {}
        conversions = 1
        traderData = state.traderData
        
        # --- PARAMÈTRES DE LA STRATÉGIE ---
        FAIR_VALUE = 10000
        POSITION_LIMIT = 80
        ASYMMETRY_THRESHOLD = 60 # À partir de combien on considère le portefeuille "trop asymétrique"
        
        for product in state.order_depths:
            # On applique cette stratégie aux produits avec une valeur cible autour de 10k
            if product not in ["EMERALDS"]: 
                continue
                
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            
            # On récupère notre inventaire actuel
            current_position = state.position.get(product, 0)
            
            # ---------------------------------------------------------
            # 1. GESTION DU RISQUE (Flattening si trop asymétrique)
            # ---------------------------------------------------------
            if current_position >= ASYMMETRY_THRESHOLD:
                # Excès positif : Liquidation agressive à 10 000
                orders.append(Order(product, FAIR_VALUE, -current_position))
                result[product] = orders
                continue # On passe au produit suivant, pas besoin d'ajouter d'autres ordres
                
            elif current_position <= -ASYMMETRY_THRESHOLD:
                # Manque (excès négatif) : Rachat à découvert à 10 000
                orders.append(Order(product, FAIR_VALUE, -current_position))
                result[product] = orders
                continue
                
            # Variables pour suivre combien on a encore le droit d'acheter/vendre
            acceptable_buy_volume = POSITION_LIMIT - current_position
            acceptable_sell_volume = -POSITION_LIMIT - current_position # Valeur négative
            
            # ---------------------------------------------------------
            # 2. STRATÉGIE TAKER (Prendre les opportunités immédiates)
            # ---------------------------------------------------------
            
            # A. Acheter en dessous de 10 000
            if len(order_depth.sell_orders) != 0:
                # On parcourt les vendeurs du moins cher au plus cher
                for ask_price, ask_vol in list(order_depth.sell_orders.items()):
                    if ask_price < FAIR_VALUE and acceptable_buy_volume > 0:
                        # On prend le maximum qu'on a le droit de prendre (ask_vol est négatif)
                        trade_vol = min(acceptable_buy_volume, abs(ask_vol))
                        orders.append(Order(product, ask_price, trade_vol))
                        acceptable_buy_volume -= trade_vol
                        
            # B. Vendre au dessus de 10 000
            if len(order_depth.buy_orders) != 0:
                # On parcourt les acheteurs du plus cher au moins cher
                for bid_price, bid_vol in list(order_depth.buy_orders.items()):
                    if bid_price > FAIR_VALUE and acceptable_sell_volume < 0:
                        # trade_vol sera négatif. (bid_vol est positif)
                        trade_vol = max(acceptable_sell_volume, -bid_vol) 
                        orders.append(Order(product, bid_price, trade_vol))
                        acceptable_sell_volume -= trade_vol
                        
            # ---------------------------------------------------------
            # 3. STRATÉGIE MAKER (Se placer à peine mieux que le marché)
            # ---------------------------------------------------------
            
            # A. Se placer en acheteur (Bid)
            if acceptable_buy_volume > 0 and len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                # On propose 1 XIREC de plus que le meilleur acheteur pour être prioritaire,
                # MAIS on refuse d'acheter à plus de 9999 pour garder notre marge
                maker_buy_price = min(best_bid + 1, FAIR_VALUE - 1)
                orders.append(Order(product, maker_buy_price, acceptable_buy_volume))
                
            # B. Se placer en vendeur (Ask)
            if acceptable_sell_volume < 0 and len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                # On propose 1 XIREC de moins que le meilleur vendeur pour être prioritaire,
                # MAIS on refuse de vendre à moins de 10001
                maker_sell_price = max(best_ask - 1, FAIR_VALUE + 1)
                orders.append(Order(product, maker_sell_price, acceptable_sell_volume))

            # On enregistre la liste d'ordres pour ce produit
            result[product] = orders

        return result, conversions, traderData