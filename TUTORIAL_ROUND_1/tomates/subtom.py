from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import json
import math

class Trader:
    
    def run(self, state: TradingState):
        result = {}
        conversions = 1
        
        # --- PARAMÈTRES ---
        PRODUCT = "TOMATOES" 
        WINDOW_LONG = 40     # Fenêtre pour la MVA longue
        WINDOW_FAST = 5    # Fenêtre pour la MVA rapide
        POSITION_LIMIT = 80
        REBALANCE_THRESHOLD=50
        # 1. RÉCUPÉRATION DE L'HISTORIQUE (Mémoire du bot)
        # On stocke les prix mid dans traderData au format JSON
        if state.traderData:
            data = json.loads(state.traderData)
            price_history = data.get("history", [])
        else:
            price_history = []

        # 2. CALCUL DES INDICATEURS
        order_depth = state.order_depths[PRODUCT]
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        
        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
            price_history.append(mid_price)
        
        # On garde seulement ce dont on a besoin pour la MVA longue
        if len(price_history) > WINDOW_LONG:
            price_history.pop(0)
            
        # Sauvegarde pour le tour suivant
        new_trader_data = json.dumps({"history": price_history})

        # Si on n'a pas assez de données pour calculer les moyennes, on attend
        if len(price_history) < WINDOW_LONG:
            return result, conversions, new_trader_data

        # Calcul mathématique (logique ENSAE : on le fait en Python pur)
        mva_long = sum(price_history) / WINDOW_LONG
        mva_fast = sum(price_history[-WINDOW_FAST:]) / WINDOW_FAST
        
        # Calcul de l'écart-type (Standard Deviation)
        variance = sum((p - mva_long) ** 2 for p in price_history) / WINDOW_LONG
        std_dev = math.sqrt(variance)
        
        # Seuils d'entrée
        buy_threshold = mva_long - std_dev
        sell_threshold = mva_long + std_dev

        orders: List[Order] = []
        current_pos = state.position.get(PRODUCT, 0)
        
        # ---------------------------------------------------------
        # 1. STRATÉGIE TAKER (Agressif vs MVA Longue)
        # ---------------------------------------------------------
        # On cherche à acheter tout ce qui est < mva_long - std_dev
        if best_ask and best_ask < buy_threshold:
            vol_to_buy = min(abs(order_depth.sell_orders[best_ask]), POSITION_LIMIT - current_pos)
            if vol_to_buy > 0:
                orders.append(Order(PRODUCT, best_ask, vol_to_buy))
                current_pos += vol_to_buy

        # On cherche à vendre tout ce qui est > mva_long + std_dev
        if best_bid and best_bid > sell_threshold:
            vol_to_sell = min(order_depth.buy_orders[best_bid], POSITION_LIMIT + current_pos)
            if vol_to_sell > 0:
                orders.append(Order(PRODUCT, best_bid, -vol_to_sell))
                current_pos -= vol_to_sell

# ---------------------------------------------------------
        # 2. RÉÉQUILIBRAGE (Seulement si seuil dépassé)
        # ---------------------------------------------------------
        # On n'intervient que si le portefeuille est "déséquilibré"
        if abs(current_pos) > REBALANCE_THRESHOLD:
            # On cherche à ramener la position à 0 au prix de la MVA rapide
            # car on considère qu'on a pris trop de risque directionnel
            stabilization_price = round(mva_fast)
            orders.append(Order(PRODUCT, stabilization_price, -current_pos))
            # On peut aussi choisir de ne ramener qu'à 50 au lieu de 0 
            # pour rester exposé, mais ramener à 0 "nettoie" le risque.

        # ---------------------------------------------------------
        # 3. STRATÉGIE MAKER (Placement entre Marché et MVA Rapide)
        # ---------------------------------------------------------
        # On ne place des ordres makers que s'il nous reste de la capacité après le reste
        remaining_buy_cap = POSITION_LIMIT - current_pos
        remaining_sell_cap = -POSITION_LIMIT - current_pos

        if best_bid and remaining_buy_cap > 0:
            # On se place à peine mieux que le marché, mais pas au dessus de la MVA rapide
            maker_bid_price = int(min(best_bid + 1, mva_fast - 1))
            orders.append(Order(PRODUCT, maker_bid_price, remaining_buy_cap))

        if best_ask and remaining_sell_cap < 0:
            # On se place à peine mieux que le marché, mais pas en dessous de la MVA rapide
            maker_ask_price = int(max(best_ask - 1, mva_fast + 1))
            orders.append(Order(PRODUCT, maker_ask_price, remaining_sell_cap))

        result[PRODUCT] = orders
        return result, conversions, new_trader_data