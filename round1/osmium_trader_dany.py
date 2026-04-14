from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict

PRODUCT = "ASH_COATED_OSMIUM"

class Trader:

    def run(self, state: TradingState):
        result = {}

        # On parcourt tous les produits disponibles dans l'état actuel

        order_depth: OrderDepth = state.order_depths[PRODUCT]
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
            current_position = state.position.get(PRODUCT, 0)
            POSITION_LIMIT = 80
            
            # On limite la taille de nos ordres par tick pour éviter de se faire 
            # remplir 80 unités d'un coup sur un mauvais prix
            MAX_ORDER_SIZE = 15 
            SKEW_TRESHHOLD = 30  # Seuil d'imbalance pour changer de régime
            
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
            
            if imbalance > 0.75:
                # PRESSION ACHETEUSE FORTE : Le prix va probablement monter.
                # On veut accumuler (Bid) mais on refuse de vendre à un prix normal !
                my_ask = best_ask + 20  # On met l'Ask sur la lune (très haut)
                
            elif imbalance < 0.25:
                # PRESSION VENDEUSE FORTE : Le prix va probablement s'effondrer.
                # On veut vendre notre stock (Ask) mais on refuse d'acheter la chute !
                my_bid = best_bid - 20  # On met le Bid dans les abysses (très bas)


            # --- 6. PLACEMENT DES ORDRES ---
            # On place le Bid (Achat) si on a de la place
            if available_to_buy > 0:
                orders.append(Order(PRODUCT, my_bid, available_to_buy))

            # On place l'Ask (Vente) si on a de la place (rappel: available_to_sell est < 0)
            if available_to_sell < 0:
                orders.append(Order(PRODUCT, my_ask, available_to_sell))

        # Enregistrement des ordres pour ce produit
        result[PRODUCT] = orders
            
        # logger.flush() n'est pas inclus ici car cela dépend de votre setup de logs
        return result, 1, ""