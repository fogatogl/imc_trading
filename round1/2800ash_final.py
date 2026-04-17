import json
from typing import Any, Dict, List, Tuple

from datamodel import (
    Listing, Observation, Order, OrderDepth,
    ProsperityEncoder, Symbol, Trade, TradingState,
)


# ─────────────────────────── Logger ───────────────────────────

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [state.timestamp, trader_data,
                self.compress_listings(state.listings), self.compress_order_depths(state.order_depths),
                self.compress_trades(state.own_trades), self.compress_trades(state.market_trades),
                state.position, self.compress_observations(state.observations)]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        return [[l.symbol, l.product, l.denomination] for l in listings.values()]

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[str, list[Any]]:
        return {s: [od.buy_orders, od.sell_orders] for s, od in order_depths.items()}

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        return [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in trades.values() for t in arr]

    def compress_observations(self, observations: Observation) -> list[Any]:
        conv = {}
        for p, o in observations.conversionObservations.items():
            conv[p] = [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff, o.importTariff, o.sugarPrice, o.sunlightIndex]
        return [observations.plainValueObservations, conv]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
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


# ─────────────────────────── Constantes ───────────────────────────

ASH    = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"

# ASH — taker mean-reversion + maker OBI-driven
ASH_LIMIT        = 80
MA_WINDOW        = 20
SPREAD_THRESHOLD = 9
Z_THRESHOLD      = 2
TAKER_LIMIT      = 40
BASE_ORDER_SIZE  = 15

# PEPPER — buy & hold passif
PEPPER_LIMIT          = 80
PEPPER_BASE_POSITION  = 75
PEPPER_SWING_MAX      = 5
PEPPER_PENTE          = 0.001
PEPPER_INTERCEPT      = 9999.9

# ─────────────────────────── Trader ───────────────────────────

class Trader:

    def __init__(self) -> None:
        self.pepper_day_offset: int | None = None

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        trader_data: dict = {}
        if state.traderData:
            try:
                trader_data = json.loads(state.traderData)
            except Exception:
                pass

        # ══════════════════════════════════════════════════════════
        #  ASH_COATED_OSMIUM
        #  1) TAKER  : mean-reversion sur z-score (spread serré)
        #  2) MAKER  : OBI-driven sur la capacité résiduelle
        #
        #  Les deux partagent le budget de 80 positions via
        #  committed_buy / committed_sell.
        # ══════════════════════════════════════════════════════════
        ash_prices: list = trader_data.get("ash_prices", [])

        if ASH in state.order_depths:
            od      = state.order_depths[ASH]
            ash_pos = state.position.get(ASH, 0)
            ash_orders: List[Order] = []

            best_bid = max(od.buy_orders)  if od.buy_orders  else None
            best_ask = min(od.sell_orders) if od.sell_orders else None

            if best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid
                mid    = (best_bid + best_ask) / 2.0

                ash_prices.append(mid)
                if len(ash_prices) > MA_WINDOW:
                    ash_prices = ash_prices[-MA_WINDOW:]

                # Capacité réservée par le taker (partagée avec le maker)
                committed_buy  = 0
                committed_sell = 0

                # ── TAKER : mean-reversion sur z-score ────────────────
                if len(ash_prices) == MA_WINDOW and spread < SPREAD_THRESHOLD:
                    ma  = sum(ash_prices) / MA_WINDOW
                    std = (sum((p - ma) ** 2 for p in ash_prices) / MA_WINDOW) ** 0.5

                    if std > 0:
                        z        = (mid - ma) / std
                        buy_cap  = max(0, TAKER_LIMIT - ash_pos - committed_buy)
                        sell_cap = max(0, TAKER_LIMIT + ash_pos - committed_sell)

                        if z > Z_THRESHOLD and sell_cap > 0:
                            qty = min(sell_cap, abs(od.buy_orders[best_bid]))
                            if qty > 0:
                                ash_orders.append(Order(ASH, best_bid, -qty))
                                committed_sell += qty

                        elif z < -Z_THRESHOLD and buy_cap > 0:
                            qty = min(buy_cap, abs(od.sell_orders[best_ask]))
                            if qty > 0:
                                ash_orders.append(Order(ASH, best_ask, qty))
                                committed_buy += qty

                        elif abs(z) < 0.5 and ash_pos != 0:
                            # Unwind passif à mid quand le prix est revenu
                            unwind_price = int(mid)
                            if ash_pos > 0:
                                ash_orders.append(Order(ASH, unwind_price, -ash_pos))
                                committed_sell += ash_pos
                            else:
                                ash_orders.append(Order(ASH, unwind_price + 1, -ash_pos))
                                committed_buy += abs(ash_pos)

                # ── MAKER : OBI-driven sur la capacité résiduelle ─────
                best_bid_vol = od.buy_orders[best_bid]
                best_ask_vol = abs(od.sell_orders[best_ask])
                total_vol    = best_bid_vol + best_ask_vol
                obi          = (best_bid_vol - best_ask_vol) / total_vol  # ∈ [-1, +1]

                my_bid = best_bid + 1 if spread > 2 else best_bid
                my_ask = best_ask - 1 if spread > 2 else best_ask

                # Taille OBI : +obi → plus de bid, moins d'ask (et réciproquement)
                buy_size  = int(BASE_ORDER_SIZE * (1 + obi))
                sell_size = int(BASE_ORDER_SIZE * (1 - obi))

                # Capacité résiduelle après le taker
                buy_size  = max(0, min(buy_size,  ASH_LIMIT - ash_pos  - committed_buy))
                sell_size = max(0, min(sell_size, ASH_LIMIT + ash_pos  - committed_sell))

                if buy_size > 0:
                    ash_orders.append(Order(ASH, my_bid,  buy_size))
                if sell_size > 0:
                    ash_orders.append(Order(ASH, my_ask, -sell_size))

            result[ASH] = ash_orders

        trader_data["ash_prices"] = ash_prices

        # ══════════════════════════════════════════════════════════
        #  INTARIAN_PEPPER_ROOT — Buy & Hold passif
        #  Achète à tous les niveaux ask jusqu'à la limite de position
        # ══════════════════════════════════════════════════════════
        
        if PEPPER in state.order_depths:
            od         = state.order_depths[PEPPER]
            pepper_pos = state.position.get(PEPPER, 0)
            pepper_orders: List[Order] = []

            if self.pepper_day_offset is None and od.sell_orders:
                best_ask = min(od.sell_orders.keys())
                if best_ask < 10500:
                    self.pepper_day_offset = 0
                elif best_ask < 11500:
                    self.pepper_day_offset = 1
                else:
                    self.pepper_day_offset = 2

            if self.pepper_day_offset is not None:
                abs_timestamp = state.timestamp + self.pepper_day_offset * 1_000_000
                fair_price    = PEPPER_INTERCEPT + PEPPER_PENTE * abs_timestamp

                # ── Couche 1 : remplir la base (0 → 75) ─────────────
                if pepper_pos < PEPPER_BASE_POSITION:
                    missing = PEPPER_BASE_POSITION - pepper_pos
                    for ask, vol in sorted(od.sell_orders.items()):
                        if missing <= 0:
                            break
                        buy_vol = min(-vol, missing)
                        if buy_vol > 0:
                            price = ask - 2 if state.timestamp < 3000 else ask
                            pepper_orders.append(Order(PEPPER, price, buy_vol))
                            missing -= buy_vol

                # ── Couche 2 : swing sur les 5 units restantes ───────
                else:
                    swing_pos            = pepper_pos - PEPPER_BASE_POSITION
                    swing_available_buy  = PEPPER_SWING_MAX - swing_pos
                    swing_available_sell = max(0, swing_pos)

                    if swing_available_buy > 0 and od.sell_orders:
                        for ask, vol in sorted(od.sell_orders.items()):
                            if ask <= fair_price + 3 and swing_available_buy > 0:
                                buy_vol = min(-vol, swing_available_buy)
                                pepper_orders.append(Order(PEPPER, ask, buy_vol))
                                swing_available_buy -= buy_vol

                    if swing_available_sell > 0 and od.buy_orders:
                        for bid, vol in sorted(od.buy_orders.items(), reverse=True):
                            if bid > fair_price + 3 and swing_available_sell > 0:
                                sell_vol = min(vol, swing_available_sell)
                                pepper_orders.append(Order(PEPPER, bid, -sell_vol))
                                swing_available_sell -= sell_vol

            result[PEPPER] = pepper_orders
            

        logger.flush(state, result, conversions, json.dumps(trader_data))
        return result, conversions, json.dumps(trader_data)