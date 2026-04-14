try:
    from datamodel import OrderDepth, TradingState, Order, ProsperityEncoder
except ImportError:
    from prosperity4bt.datamodel import OrderDepth, TradingState, Order, ProsperityEncoder
from typing import List, Dict, Any
import json


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict, conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""
        ]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list:
        return [
            state.timestamp, trader_data,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {sym: [od.buy_orders, od.sell_orders] for sym, od in state.order_depths.items()},
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.own_trades.values() for t in arr],
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.market_trades.values() for t in arr],
            state.position,
            [state.observations.plainValueObservations, {}],
        ]

    def compress_orders(self, orders: dict) -> list:
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


class Trader:
    
    def run(self, state: TradingState):
        result = {}
        
        # On parcourt tous les produits disponibles dans l'état actuel
        
        order_depth: OrderDepth = state.order_depths["ASH_COATED_OSMIUM"]
        orders: List[Order] = []
        
        # 1. Vérification de sécurité : s'assurer que le carnet n'est pas vide
        if len(order_depth.buy_orders) != 0 and len(order_depth.sell_orders) != 0:
            
            # --- EXTRACTION DES DONNÉES DU CARNET ---
            best_bid = max(order_depth.buy_orders.keys())
            # Les volumes de vente sont négatifs dans Prosperity, on utilise abs()
            best_bid_vol = order_depth.buy_orders[best_bid] 
            
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_vol = abs(order_depth.sell_orders[best_ask])
            
            # Calcul du Spread et du Mid Price
            spread = best_ask - best_bid
            mid_price = (best_ask + best_bid) / 2
            
            # --- GESTION DE L'INVENTAIRE (POSITION LIMIT = 80) ---
            current_position = state.position.get("ASH_COATED_OSMIUM", 0)
            POSITION_LIMIT = 80
            
            # On limite la taille de nos ordres par tick pour éviter de se faire 
            # remplir 80 unités d'un coup sur un mauvais prix
            # Dynamic order size: throttle as position loads up (L1 mean volume ~12.8 units)
            abs_pos = abs(current_position)
            SKEW_TRESHHOLD = 20  # 25% of limit (was 30/37.5%); justified by mean-reversion (H=0.85, VR=0.51)
            if abs_pos >= SKEW_TRESHHOLD * 2:    # ≥40: near limit, slow down
                MAX_ORDER_SIZE = 8
            elif abs_pos >= SKEW_TRESHHOLD:       # 20-39: moderate load
                MAX_ORDER_SIZE = 12
            else:                                  # 0-19: normal
                MAX_ORDER_SIZE = 15

            # Calcul de l'espace disponible (sell est négatif)
            available_to_buy = min(POSITION_LIMIT - current_position, MAX_ORDER_SIZE)
            available_to_sell = max(-POSITION_LIMIT - current_position, -MAX_ORDER_SIZE)


            # --- 2. CALCUL DE L'ORDER BOOK IMBALANCE ---
            total_volume = best_bid_vol + best_ask_vol
            imbalance = best_bid_vol / total_volume if total_volume > 0 else 0.5


            # --- 3. DÉTERMINATION DES PRIX DE BASE (PENNY-JUMPING) ---
            # On se place juste devant les meilleurs prix, seulement si le spread le permet
            if spread > 2:
                my_bid = best_bid + 1
                my_ask = best_ask - 1
            else:
                # Si le spread est trop serré, on rejoint le meilleur prix existant
                my_bid = best_bid
                my_ask = best_ask


            # --- 4. INVENTORY SKEW AGRESSIF ---
            # Si on est trop chargé d'un côté, on décale nos prix pour forcer le marché à nous soulager
            if current_position > SKEW_TRESHHOLD:
                # On est très LONG (trop acheté). On veut vendre urgemment.
                my_ask -= 1  # On baisse notre prix de vente pour être super attractif
                my_bid -= 2  # On baisse notre prix d'achat pour arrêter d'acheter
            elif current_position < -SKEW_TRESHHOLD:
                # On est très SHORT (trop vendu). On veut acheter urgemment.
                my_bid += 1  # On monte notre prix d'achat
                my_ask += 2  # On monte notre prix de vente pour arrêter de vendre


            # --- 5. CHANGEMENT DE RÉGIME BASÉ SUR L'IMBALANCE ---
            # Écrase la logique précédente si un grand danger/opportunité est détecté
            # Offset dynamique: au minimum 14 ticks, au moins 1 spread complet (typiquement 16-18 ticks)
            # Justification: moves observés après OBI extrême = 9-17 ticks; être ≥ 1 spread évite les fills accidentels
            imbalance_offset = max(14, spread)

            if imbalance > 0.75:
                # PRESSION ACHETEUSE FORTE : Le prix va probablement monter.
                # On veut accumuler (Bid) mais on refuse de vendre à un prix normal !
                my_ask = best_ask + imbalance_offset  # Au-dessus du marché par ≥ 1 spread

            elif imbalance < 0.25:
                # PRESSION VENDEUSE FORTE : Le prix va probablement s'effondrer.
                # On veut vendre notre stock (Ask) mais on refuse d'acheter la chute !
                my_bid = best_bid - imbalance_offset  # En-dessous du marché par ≥ 1 spread


            # --- 6. PLACEMENT DES ORDRES ---
            # On place le Bid (Achat) si on a de la place
            if available_to_buy > 0:
                orders.append(Order("ASH_COATED_OSMIUM", my_bid, available_to_buy))
                
            # On place l'Ask (Vente) si on a de la place (rappel: available_to_sell est < 0)
            if available_to_sell < 0:
                orders.append(Order("ASH_COATED_OSMIUM", my_ask, available_to_sell))
        
        result["ASH_COATED_OSMIUM"] = orders
        result["INTARIAN_PEPPER_ROOT"] = []

        trader_data = ""
        logger.flush(state, result, 1, trader_data)
        return result, 1, trader_data