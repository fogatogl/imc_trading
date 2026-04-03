import json
import math

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:

    def run(self, state: TradingState):

        result = {}
        conversions = 1
        
        # ---------------------------------------------------------
        # 1. CHARGEMENT DE LA MÉMOIRE GLOBALE
        # ---------------------------------------------------------
        try:
            global_memory = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            global_memory = {}
            
        if "TOMATOES" not in global_memory:
            global_memory["TOMATOES"] = {"history": []}
        if "EMERALDS" not in global_memory:
            global_memory["EMERALDS"] = {}

        # ---------------------------------------------------------
        # 2. BOUCLE SUR TOUS LES PRODUITS DU MARCHÉ
        # ---------------------------------------------------------
        for product in state.order_depths:
            
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            
            # On utilise bien current_pos partout !
            current_pos = state.position.get(product, 0)

            # =====================================================
            # STRATÉGIE ÉMERAUDE
            # =====================================================
            if product == "EMERALDS":
                FAIR_VALUE = 10000
                POSITION_LIMIT = 80
                ASYMMETRY_THRESHOLD = 60
                
                # Gestion du risque
                if current_pos >= ASYMMETRY_THRESHOLD:
                    orders.append(Order(product, FAIR_VALUE, -current_pos))
                    result[product] = orders
                    continue 
                
                elif current_pos <= -ASYMMETRY_THRESHOLD:
                    orders.append(Order(product, FAIR_VALUE, -current_pos))
                    result[product] = orders
                    continue
                
                acceptable_buy_volume = POSITION_LIMIT - current_pos
                acceptable_sell_volume = -POSITION_LIMIT - current_pos
            
                # Taker
                if len(order_depth.sell_orders) != 0:
                    for ask_price, ask_vol in list(order_depth.sell_orders.items()):
                        if ask_price < FAIR_VALUE and acceptable_buy_volume > 0:
                            trade_vol = min(acceptable_buy_volume, abs(ask_vol))
                            orders.append(Order(product, ask_price, trade_vol))
                            acceptable_buy_volume -= trade_vol
                        
                if len(order_depth.buy_orders) != 0:
                    for bid_price, bid_vol in list(order_depth.buy_orders.items()):
                        if bid_price > FAIR_VALUE and acceptable_sell_volume < 0:
                            trade_vol = max(acceptable_sell_volume, -bid_vol) 
                            orders.append(Order(product, bid_price, trade_vol))
                            acceptable_sell_volume -= trade_vol
                        
                # Maker
                if acceptable_buy_volume > 0 and len(order_depth.buy_orders) > 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    maker_buy_price = min(best_bid + 1, FAIR_VALUE - 1)
                    orders.append(Order(product, maker_buy_price, acceptable_buy_volume))
                
                if acceptable_sell_volume < 0 and len(order_depth.sell_orders) > 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    maker_sell_price = max(best_ask - 1, FAIR_VALUE + 1)
                    orders.append(Order(product, maker_sell_price, acceptable_sell_volume))

                result[product] = orders

            # =====================================================
            # STRATÉGIE TOMATE
            # =====================================================
            elif product == "TOMATOES":
                WINDOW_LONG = 40 
                WINDOW_FAST = 5  
                POSITION_LIMIT = 80
                REBALANCE_THRESHOLD=50

                # On pointe directement sur le tiroir mémoire des Tomates
                price_history = global_memory["TOMATOES"]["history"]

                best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
                best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        
                if best_bid and best_ask:
                    mid_price = (best_bid + best_ask) / 2
                    price_history.append(mid_price)
        
                if len(price_history) > WINDOW_LONG:
                    price_history.pop(0)
            
                # On met à jour la donnée dans le dictionnaire global
                global_memory["TOMATOES"]["history"] = price_history

                # CORRECTION : On passe au produit suivant au lieu de tuer le bot
                if len(price_history) < WINDOW_LONG:
                    continue

                # Calculs
                mva_long = sum(price_history) / WINDOW_LONG
                mva_fast = sum(price_history[-WINDOW_FAST:]) / WINDOW_FAST
        
                variance = sum((p - mva_long) ** 2 for p in price_history) / WINDOW_LONG
                std_dev = math.sqrt(variance)
        
                buy_threshold = mva_long - std_dev
                sell_threshold = mva_long + std_dev

                # Taker
                if best_ask and best_ask < buy_threshold:
                    vol_to_buy = min(abs(order_depth.sell_orders[best_ask]), POSITION_LIMIT - current_pos)
                    if vol_to_buy > 0:
                        orders.append(Order(product, best_ask, vol_to_buy))
                        current_pos += vol_to_buy

                if best_bid and best_bid > sell_threshold:
                    vol_to_sell = min(order_depth.buy_orders[best_bid], POSITION_LIMIT + current_pos)
                    if vol_to_sell > 0:
                        orders.append(Order(product , best_bid, -vol_to_sell))
                        current_pos -= vol_to_sell

                # Rééquilibrage
                if abs(current_pos) > REBALANCE_THRESHOLD:
                    stabilization_price = round(mva_fast)
                    orders.append(Order(product, stabilization_price, -current_pos))
                    current_pos = 0  # CORRECTION : Mise à jour du stock pour la suite

                # Maker
                remaining_buy_cap = POSITION_LIMIT - current_pos
                remaining_sell_cap = -POSITION_LIMIT - current_pos

                if best_bid and remaining_buy_cap > 0:
                    maker_bid_price = int(min(best_bid + 1, mva_fast - 1))
                    orders.append(Order(product, maker_bid_price, remaining_buy_cap))

                if best_ask and remaining_sell_cap < 0:
                    maker_ask_price = int(max(best_ask - 1, mva_fast + 1))
                    orders.append(Order(product, maker_ask_price, remaining_sell_cap))

                result[product] = orders

        # ---------------------------------------------------------
        # 3. SAUVEGARDE ET ENVOI (En dehors de la boucle)
        # ---------------------------------------------------------
        # On encode la totalité de la mémoire pour le prochain tour
        new_trader_data = json.dumps(global_memory)
        
        # Le return final obligatoire
        return result, conversions, new_trader_data
        




        