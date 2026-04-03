from datamodel import OrderDepth, TradingState, Order
from typing import List
import json
import math


class Trader:

    # ── ÉMERAUDES ─────────────────────────────────────────────────────────────
    EM_FAIR_VALUE         = 10000
    EM_POSITION_LIMIT     = 80
    EM_ASYMMETRY_THRESH   = 60   # flattening agressif si |pos| >= seuil

    # ── TOMATES — Avellaneda-Stoikov ──────────────────────────────────────────
    TOM_POSITION_LIMIT = 80
    TOM_KAPPA          = 0.1     # calibré par grid search (180 combos, round 0)
    TOM_GAMMA          = 0.08    # aversion au risque  (↑ = quotes plus larges)
    TOM_SIGMA_FLOOR    = 0.5     # plancher σ pour marché calme
    TOM_WINDOW_VOL     = 20      # fenêtre σ glissant

    # ── Helpers TOMATES ───────────────────────────────────────────────────────

    def _wall_mid(self, depth: OrderDepth):
        if not depth.buy_orders or not depth.sell_orders:
            return None
        wall_bid = max(depth.buy_orders, key=lambda p: depth.buy_orders[p])
        wall_ask = max(depth.sell_orders, key=lambda p: abs(depth.sell_orders[p]))
        return (wall_bid + wall_ask) / 2.0

    def _sigma(self, history: list) -> float:
        if len(history) < 3:
            return self.TOM_SIGMA_FLOOR
        window = history[-self.TOM_WINDOW_VOL:]
        diffs  = [window[i + 1] - window[i] for i in range(len(window) - 1)]
        if not diffs:
            return self.TOM_SIGMA_FLOOR
        mean_d = sum(diffs) / len(diffs)
        var_d  = sum((d - mean_d) ** 2 for d in diffs) / max(len(diffs) - 1, 1)
        return max(math.sqrt(var_d), self.TOM_SIGMA_FLOOR)

    # ── Point d'entrée ────────────────────────────────────────────────────────

    def run(self, state: TradingState):
        result      = {}
        conversions = 0

        # ── Mémoire persistante ───────────────────────────────────────────────
        try:
            memory = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            memory = {}
        tom_prices = memory.get("tom_prices", [])

        # ── Boucle produits ───────────────────────────────────────────────────
        for product, depth in state.order_depths.items():

            pos    = state.position.get(product, 0)
            orders: List[Order] = []

            # ==================================================================
            # ÉMERAUDES — market making statique autour de 10 000
            # ==================================================================
            if product == "EMERALDS":
                FV    = self.EM_FAIR_VALUE
                LIMIT = self.EM_POSITION_LIMIT

                # Flattening d'urgence
                if abs(pos) >= self.EM_ASYMMETRY_THRESH:
                    orders.append(Order(product, FV, -pos))
                    result[product] = orders
                    continue

                buy_cap  = LIMIT - pos
                sell_cap = LIMIT + pos   # volume max à vendre (positif)

                # Layer 1 — taker : sweep tout ce qui croise FV
                for ap in sorted(depth.sell_orders):
                    if ap >= FV or buy_cap <= 0:
                        break
                    qty = min(abs(depth.sell_orders[ap]), buy_cap)
                    orders.append(Order(product, ap, qty))
                    buy_cap -= qty
                    pos     += qty

                for bp in sorted(depth.buy_orders, reverse=True):
                    if bp <= FV or sell_cap <= 0:
                        break
                    qty = min(depth.buy_orders[bp], sell_cap)
                    orders.append(Order(product, bp, -qty))
                    sell_cap -= qty
                    pos      -= qty

                # Layer 2 — maker : meilleur prix possible sans franchir FV
                if buy_cap > 0 and depth.buy_orders:
                    best_bid = max(depth.buy_orders)
                    bid_price = min(best_bid + 1, FV - 1)
                    orders.append(Order(product, bid_price, buy_cap))

                if sell_cap > 0 and depth.sell_orders:
                    best_ask  = min(depth.sell_orders)
                    ask_price = max(best_ask - 1, FV + 1)
                    orders.append(Order(product, ask_price, -sell_cap))

                result[product] = orders

            # ==================================================================
            # TOMATES — Avellaneda-Stoikov
            # ==================================================================
            elif product == "TOMATOES":
                LIMIT = self.TOM_POSITION_LIMIT

                best_bid = max(depth.buy_orders)  if depth.buy_orders  else None
                best_ask = min(depth.sell_orders) if depth.sell_orders else None
                if best_bid is None or best_ask is None:
                    continue

                # Fair value = WallMid
                s = self._wall_mid(depth)
                if s is None:
                    continue

                tom_prices.append(s)
                tom_prices = tom_prices[-(self.TOM_WINDOW_VOL + 5):]

                sigma = self._sigma(tom_prices)

                # Prix de réservation : r = s − q·γ·σ²
                r = s - pos * self.TOM_GAMMA * sigma ** 2

                # Demi-spread optimal : δ* = γσ²/2 + (1/κ)·ln(1 + γ/κ)
                delta = (
                    self.TOM_GAMMA * sigma ** 2 / 2.0
                    + (1.0 / self.TOM_KAPPA) * math.log(1.0 + self.TOM_GAMMA / self.TOM_KAPPA)
                )

                bid_price = round(r - delta)
                ask_price = round(r + delta)

                if bid_price >= ask_price:
                    bid_price = round(r) - 1
                    ask_price = round(r) + 1

                # Layer 1 — taker : opportuniste contre r
                for ap in sorted(depth.sell_orders):
                    if ap >= r or pos >= LIMIT:
                        break
                    qty = min(abs(depth.sell_orders[ap]), LIMIT - pos)
                    if qty > 0:
                        orders.append(Order(product, ap, qty))
                        pos += qty

                for bp in sorted(depth.buy_orders, reverse=True):
                    if bp <= r or pos <= -LIMIT:
                        break
                    qty = min(depth.buy_orders[bp], LIMIT + pos)
                    if qty > 0:
                        orders.append(Order(product, bp, -qty))
                        pos -= qty

                # Layer 2 — maker : quotes AS
                buy_cap  = LIMIT - pos
                sell_cap = LIMIT + pos

                if buy_cap > 0:
                    orders.append(Order(product, bid_price, buy_cap))
                if sell_cap > 0:
                    orders.append(Order(product, ask_price, -sell_cap))

                result[product] = orders

        # ── Sauvegarde mémoire ────────────────────────────────────────────────
        memory["tom_prices"] = tom_prices
        return result, conversions, json.dumps(memory)
