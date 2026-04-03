"""
Stratégie Avellaneda-Stoikov (AS) pour TOMATOES — IMC Prosperity 4
===================================================================

Le modèle AS fournit des quotes (bid/ask) qui minimisent simultanément :
  - le risque d'inventaire (via le prix de réservation ajusté)
  - la capture du spread (via le demi-spread optimal)

Paramètres calibrés via as_analysis.py sur les données historiques :
  σ   ≈ 1.35 pts/tick  (std des variations de prix sur 20 ticks)
  κ   = 0.125           (intensité de décroissance des ordres = 1/demi_spread_mural)
  γ   = 0.05            (aversion au risque)

Formules du modèle :
  r(q) = s − q · γ · σ²              [prix de réservation, inventaire q]
  δ*   = γ·σ²/2 + (1/κ)·ln(1+γ/κ)  [demi-spread optimal constant]
  bid* = r(q) − δ*
  ask* = r(q) + δ*

Déroulement par tick :
  1. Calcul WallMid comme FV (résistant au spoofing des bots)
  2. Estimation σ glissant (20 ticks)
  3. Prise opportuniste de tout ce qui croise r(q)
  4. Pose des quotes maker à bid*/ask*
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List
import json
import math


class Trader:

    # ── Produit ───────────────────────────────────────────────────────────────
    PRODUCT        = "TOMATOES"
    POSITION_LIMIT = 80

    # ── Paramètres AS (calibrés depuis as_analysis.py) ────────────────────────
    KAPPA       = 0.125   # 1 / demi_spread_mural (mur à ±8 pts du WallMid)
    GAMMA       = 0.05    # aversion au risque (plus grand → écart de quotes plus large)
    SIGMA_FLOOR = 0.5     # floor σ pour éviter un spread nul en marché calme
    WINDOW_VOL  = 20      # fenêtre de calcul du σ glissant

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _wall_mid(self, depth: OrderDepth) -> float | None:
        """
        Mid-price du bid et de l'ask ayant le plus grand volume.
        Plus robuste que le plain mid contre les ordres de leurre des bots.
        """
        if not depth.buy_orders or not depth.sell_orders:
            return None
        # Le bid avec le plus grand volume (int positif)
        wall_bid = max(depth.buy_orders, key=lambda p: depth.buy_orders[p])
        # Le ask avec le plus grand volume (convention IMC : int négatif)
        wall_ask = max(depth.sell_orders, key=lambda p: abs(depth.sell_orders[p]))
        return (wall_bid + wall_ask) / 2.0

    def _sigma(self, price_history: list) -> float:
        """Écart-type des variations de prix sur la fenêtre glissante."""
        if len(price_history) < 3:
            return self.SIGMA_FLOOR
        window = price_history[-self.WINDOW_VOL:]
        diffs  = [window[i + 1] - window[i] for i in range(len(window) - 1)]
        if not diffs:
            return self.SIGMA_FLOOR
        mean_d = sum(diffs) / len(diffs)
        var_d  = sum((d - mean_d) ** 2 for d in diffs) / max(len(diffs) - 1, 1)
        return max(math.sqrt(var_d), self.SIGMA_FLOOR)

    # ── Logique principale ────────────────────────────────────────────────────

    def run(self, state: TradingState):
        result      = {}
        conversions = 0

        # ── 1. Mémoire ────────────────────────────────────────────────────────
        data          = json.loads(state.traderData) if state.traderData else {}
        price_history = data.get("prices", [])

        # ── 2. Lecture du carnet ──────────────────────────────────────────────
        if self.PRODUCT not in state.order_depths:
            return result, conversions, json.dumps({"prices": price_history})

        depth    = state.order_depths[self.PRODUCT]
        best_bid = max(depth.buy_orders)  if depth.buy_orders  else None
        best_ask = min(depth.sell_orders) if depth.sell_orders else None

        if best_bid is None or best_ask is None:
            return result, conversions, json.dumps({"prices": price_history})

        # ── 3. Fair Value (WallMid) ───────────────────────────────────────────
        s = self._wall_mid(depth)
        if s is None:
            return result, conversions, json.dumps({"prices": price_history})

        price_history.append(s)
        price_history = price_history[-(self.WINDOW_VOL + 5):]

        # ── 4. Volatilité σ ───────────────────────────────────────────────────
        sigma = self._sigma(price_history)

        # ── 5. Calculs AS ─────────────────────────────────────────────────────
        pos = state.position.get(self.PRODUCT, 0)

        # Prix de réservation : r = s − q·γ·σ²
        # Skew vers le bas si long (q>0), vers le haut si short (q<0)
        r = s - pos * self.GAMMA * sigma ** 2

        # Demi-spread optimal : δ* = γ·σ²/2 + (1/κ)·ln(1+γ/κ)
        delta = (self.GAMMA * sigma ** 2 / 2.0
                 + (1.0 / self.KAPPA) * math.log(1.0 + self.GAMMA / self.KAPPA))

        bid_price = round(r - delta)
        ask_price = round(r + delta)

        # Anti-crossing
        if bid_price >= ask_price:
            bid_price = round(r) - 1
            ask_price = round(r) + 1

        # ── 6. Ordres ─────────────────────────────────────────────────────────
        orders: List[Order] = []

        # Layer 1 — prise opportuniste (cross contre r)
        for ap in sorted(depth.sell_orders):
            if ap < r and pos < self.POSITION_LIMIT:
                qty = min(abs(depth.sell_orders[ap]), self.POSITION_LIMIT - pos)
                if qty > 0:
                    orders.append(Order(self.PRODUCT, ap, qty))
                    pos += qty
            else:
                break

        for bp in sorted(depth.buy_orders, reverse=True):
            if bp > r and pos > -self.POSITION_LIMIT:
                qty = min(depth.buy_orders[bp], self.POSITION_LIMIT + pos)
                if qty > 0:
                    orders.append(Order(self.PRODUCT, bp, -qty))
                    pos -= qty
            else:
                break

        # Layer 2 — quotes maker optimaux
        buy_cap  = self.POSITION_LIMIT - pos
        sell_cap = self.POSITION_LIMIT + pos

        if buy_cap > 0:
            orders.append(Order(self.PRODUCT, bid_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order(self.PRODUCT, ask_price, -sell_cap))

        result[self.PRODUCT] = orders

        # ── 7. Sauvegarde mémoire ─────────────────────────────────────────────
        return result, conversions, json.dumps({"prices": price_history})
