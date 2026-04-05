import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    def bid(self):
        return 15

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
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
        # 2. BOUCLE SUR TOUS LES PRODUITS
        # ---------------------------------------------------------
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            current_pos = state.position.get(product, 0)

            # =====================================================
            # STRATÉGIE ÉMERAUDE (Market Making & Flattening à 10 000)
            # =====================================================
            if product == "EMERALDS":
                FAIR_VALUE = 10000
                POSITION_LIMIT = 80
                ASYMMETRY_THRESHOLD = 60
                
                # Gestion du risque (Flattening agressif)
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
            
                # Taker : prendre la liquidité avantageuse
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
                        
                # Maker : fournir de la liquidité autour du Fair Value
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
            # STRATÉGIE TOMATE (Modèle Statistique AR(5) sur Log Returns)
            # =====================================================
            elif product == "TOMATOES":
                POSITION_LIMIT = 80
                # MULTIPLIER va transformer des "points de prix" en "volume de tomates".
                # S'il y a un décalage de 0.5 points prévu, un multiplicateur de 10 prendra 5 tomates.
                MULTIPLIER = 10 
                
                price_history = global_memory["TOMATOES"]["history"]
                
                best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
                best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
                
                # Mise à jour de l'historique (Besoin de 6 prix pour 5 rendements)
                if best_bid and best_ask:
                    mid_price = (best_bid + best_ask) / 2
                    price_history.append(mid_price)
                
                if len(price_history) > 6:
                    price_history.pop(0)
                    
                global_memory["TOMATOES"]["history"] = price_history
                
                # Attente du buffer initial
                if len(price_history) < 6:
                    continue
                    
                # 1. CALCUL DES RENDEMENTS LOGARITHMIQUES
                # Ordre chronologique: [t-5, t-4, t-3, t-2, t-1, t]
                r5 = math.log(price_history[1] / price_history[0])
                r4 = math.log(price_history[2] / price_history[1])
                r3 = math.log(price_history[3] / price_history[2])
                r2 = math.log(price_history[4] / price_history[3])
                r1 = math.log(price_history[5] / price_history[4])
                
                # 2. LE MODÈLE AR(5)
                # Prédiction du log return pour le tick t+1
                r_hat = -0.55 * r1 - 0.32 * r2 - 0.18 * r3 - 0.09 * r4 - 0.05 * r5
                
                # 3. CONVERSION EN SIGNAUX OPÉRATIONNELS
                # Traduction du rendement logarithmique (très petit) en variation absolue estimée en points.
                predicted_price_diff = mid_price * r_hat
                
                # Détermination du volume cible (proportionnel à la force de l'anomalie)
                target_volume = int(abs(predicted_price_diff) * MULTIPLIER)
                
                # 4. EXÉCUTION TAKER (Profiter de la prédiction du modèle)
                if predicted_price_diff > 0 and best_ask:
                    vol_to_buy = min(target_volume, POSITION_LIMIT - current_pos)
                    vol_to_buy = min(vol_to_buy, abs(order_depth.sell_orders[best_ask]))
                    
                    if vol_to_buy > 0:
                        orders.append(Order(product, best_ask, vol_to_buy))
                        current_pos += vol_to_buy
                        
                elif predicted_price_diff < 0 and best_bid:
                    vol_to_sell = min(target_volume, POSITION_LIMIT + current_pos)
                    vol_to_sell = min(vol_to_sell, order_depth.buy_orders[best_bid])
                    
                    if vol_to_sell > 0:
                        orders.append(Order(product, best_bid, -vol_to_sell))
                        current_pos -= vol_to_sell

                # 5. GESTION DE L'INVENTAIRE (Période de détention optimale : 1-5 ticks)
                # Liquidation passive immédiate de tout stock au tick suivant pour sécuriser le spread.
                if current_pos > 0 and best_ask:
                    maker_ask = max(best_bid + 1, best_ask - 1)
                    orders.append(Order(product, maker_ask, -current_pos))
                    
                elif current_pos < 0 and best_bid:
                    maker_bid = min(best_ask - 1, best_bid + 1)
                    orders.append(Order(product, maker_bid, abs(current_pos)))

                result[product] = orders

        # ---------------------------------------------------------
        # 3. SAUVEGARDE ET ENVOI
        # ---------------------------------------------------------
        new_trader_data = json.dumps(global_memory)
        return result, conversions, new_trader_data