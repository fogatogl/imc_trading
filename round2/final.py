import json
from round2.datamodel import (
    Listing, Observation, Order, OrderDepth,
    ProsperityEncoder, Symbol, Trade, TradingState,
)
from typing import List, Any, Dict, Tuple

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

# ─────────────────────────── Paramètres ASH ───────────────────────────

ASH                    = "ASH_COATED_OSMIUM"
ASH_LIMIT              = 80
WALL_THRESHOLD         = 15    # Taille min d'un mur
WALL_WINDOW            = 30    # Fenêtre rolling wall mid
ANOMALY_THRESHOLD      = 0.1   # Écart pour déclencher le snipe wall
SPREAD_THRESHOLD       = 9
TAKER_LIMIT            = 30
BASE_ORDER_SIZE        = 20
SOFT_LIMIT             = 60    # Au-delà, le maker réduit progressivement le côté lourd
MA_WINDOW              = 20    # Fenêtre MA pour le z-score
Z_THRESHOLD            = 2.5   # Z-score min pour déclencher le taker z-score

# ─────────────────────────── Paramètres PEPPER ───────────────────────────

PEPPER               = "INTARIAN_PEPPER_ROOT"
MAX_POSITION         = 80
WARMUP_TICKS         = 2000
SLOPE_THRESHOLD      = 0.0003
SLOPE_WINDOW         = 20
BASE_POSITION        = 75
SWING_MAX            = 5
PENTE                = 0.001
INTERCEPT            = 9999.9

# ─────────────────────────── SlopeTracker ───────────────────────────

class SlopeTracker:
    """Régression linéaire online (Welford-style) — O(1) par mise à jour."""
    __slots__ = ("n", "mx", "my", "sxx", "sxy", "tick0")

    def __init__(self) -> None:
        self.n     = 0
        self.mx    = 0.0
        self.my    = 0.0
        self.sxx   = 0.0
        self.sxy   = 0.0
        self.tick0 = None

    def update(self, timestamp: int, mid_price: float) -> None:
        if self.tick0 is None:
            self.tick0 = timestamp
        x = (timestamp - self.tick0) / 1_000_000
        self.n += 1
        dx = x - self.mx
        self.mx  += dx / self.n
        dy = mid_price - self.my
        self.my  += dy / self.n
        self.sxx += dx * (x - self.mx)
        self.sxy += dx * (mid_price - self.my)

    def slope(self) -> float | None:
        if self.n < WARMUP_TICKS or self.sxx == 0.0:
            return None
        return self.sxy / self.sxx

    def to_dict(self) -> dict:
        return {"n": self.n, "mx": self.mx, "my": self.my,
                "sxx": self.sxx, "sxy": self.sxy, "tick0": self.tick0}

    @staticmethod
    def from_dict(d: dict) -> "SlopeTracker":
        t = SlopeTracker()
        t.n = d["n"]; t.mx = d["mx"]; t.my = d["my"]
        t.sxx = d["sxx"]; t.sxy = d["sxy"]; t.tick0 = d["tick0"]
        return t

# ─────────────────────────── Trader ───────────────────────────

class Trader:
    def __init__(self) -> None:
        pass

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # ── Désérialisation de la mémoire ──────────────────────────────────────
        trader_data: dict = {}
        if state.traderData:
            try:
                trader_data = json.loads(state.traderData)
            except Exception:
                pass

        # ══════════════════════════════════════════════════════════════════════
        # ASH_COATED_OSMIUM
        # ══════════════════════════════════════════════════════════════════════

        last_bid_wall = trader_data.get("last_bid_wall", None)
        last_ask_wall = trader_data.get("last_ask_wall", None)
        wall_mids     = trader_data.get("wall_mids", [])
        ash_prices    = trader_data.get("ash_prices", [])

        if ASH in state.order_depths:
            od      = state.order_depths[ASH]
            ash_pos = state.position.get(ASH, 0)
            ash_orders: List[Order] = []

            best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
            best_ask = min(od.sell_orders.keys()) if od.sell_orders else None

            if best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid
                mid    = (best_bid + best_ask) / 2.0

                # Calcul du rolling wall mid
                curr_bid_wall = max([p for p, v in od.buy_orders.items() if v >= WALL_THRESHOLD], default=None)
                curr_ask_wall = min([p for p, v in od.sell_orders.items() if abs(v) >= WALL_THRESHOLD], default=None)

                if curr_bid_wall is not None: last_bid_wall = curr_bid_wall
                if curr_ask_wall is not None: last_ask_wall = curr_ask_wall
                if last_bid_wall is None: last_bid_wall = best_bid
                if last_ask_wall is None: last_ask_wall = best_ask

                instant_wall_mid = (last_bid_wall + last_ask_wall) / 2.0
                wall_mids.append(instant_wall_mid)
                if len(wall_mids) > WALL_WINDOW:
                    wall_mids.pop(0)

                ash_prices.append(mid)
                if len(ash_prices) > MA_WINDOW:
                    ash_prices = ash_prices[-MA_WINDOW:]

                committed_buy  = 0
                committed_sell = 0
                taker_action   = None

                # ── PRIORITÉ 1 : TAKER Z-SCORE ──────────────────────────────
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
                                taker_action = "sell"

                        elif z < -Z_THRESHOLD and buy_cap > 0:
                            qty = min(buy_cap, abs(od.sell_orders[best_ask]))
                            if qty > 0:
                                ash_orders.append(Order(ASH, best_ask, qty))
                                committed_buy += qty
                                taker_action = "buy"

                # ── PRIORITÉ 2 : TAKER WALL (SNIPER) ────────────────────────
                # N'agit que si le z-score n'a rien déclenché
                if len(wall_mids) == WALL_WINDOW and spread < SPREAD_THRESHOLD:
                    rolling_wall_mid = sum(wall_mids) / len(wall_mids)
                    buy_cap  = max(0, TAKER_LIMIT - ash_pos - committed_buy)
                    sell_cap = max(0, TAKER_LIMIT + ash_pos - committed_sell)

                    if best_bid > rolling_wall_mid + ANOMALY_THRESHOLD and sell_cap > 0 and taker_action is None:
                        qty = min(sell_cap, abs(od.buy_orders[best_bid]))
                        ash_orders.append(Order(ASH, best_bid, -qty))
                        committed_sell += qty
                        taker_action = "sell"

                    elif best_ask < rolling_wall_mid - ANOMALY_THRESHOLD and buy_cap > 0 and taker_action is None:
                        qty = min(buy_cap, abs(od.sell_orders[best_ask]))
                        ash_orders.append(Order(ASH, best_ask, qty))
                        committed_buy += qty
                        taker_action = "buy"

                    # Unwind passif
                    elif taker_action is None and abs(mid - rolling_wall_mid) <= 0.5 and ash_pos != 0:
                        unwind_price = int(mid)
                        if ash_pos > 0:
                            ash_orders.append(Order(ASH, unwind_price, -ash_pos))
                            committed_sell += ash_pos
                        else:
                            ash_orders.append(Order(ASH, unwind_price + 1, -ash_pos))
                            committed_buy += abs(ash_pos)

                # ── PRIORITÉ 3 : MAKER OBI-DRIVEN avec skew inventaire ───────
                best_bid_vol = od.buy_orders[best_bid]
                best_ask_vol = abs(od.sell_orders[best_ask])
                total_vol    = best_bid_vol + best_ask_vol
                obi          = (best_bid_vol - best_ask_vol) / total_vol if total_vol > 0 else 0

                my_bid = best_bid + 1 if spread > 2 else best_bid
                my_ask = best_ask - 1 if spread > 2 else best_ask

                buy_size  = int(BASE_ORDER_SIZE * (1 + obi))
                sell_size = int(BASE_ORDER_SIZE * (1 - obi))

                ramp = ASH_LIMIT - SOFT_LIMIT
                if ash_pos > SOFT_LIMIT:
                    buy_size  = int(buy_size  * max(0.0, (ASH_LIMIT - ash_pos) / ramp))
                elif ash_pos < -SOFT_LIMIT:
                    sell_size = int(sell_size * max(0.0, (ASH_LIMIT + ash_pos) / ramp))

                buy_size  = max(0, min(buy_size,  ASH_LIMIT - ash_pos  - committed_buy))
                sell_size = max(0, min(sell_size, ASH_LIMIT + ash_pos  - committed_sell))

                if buy_size > 0:
                    ash_orders.append(Order(ASH, my_bid,  buy_size))
                if sell_size > 0:
                    ash_orders.append(Order(ASH, my_ask, -sell_size))

            result[ASH] = ash_orders

        trader_data["last_bid_wall"] = last_bid_wall
        trader_data["last_ask_wall"] = last_ask_wall
        trader_data["wall_mids"]     = wall_mids
        trader_data["ash_prices"]    = ash_prices

        # ══════════════════════════════════════════════════════════════════════
        # INTARIAN_PEPPER_ROOT
        # ══════════════════════════════════════════════════════════════════════

        if "tracker" in trader_data:
            tracker = SlopeTracker.from_dict(trader_data["tracker"])
        else:
            tracker = SlopeTracker()
        day_offset: int | None = trader_data.get("day_offset", None)

        if PEPPER in state.order_depths:
            od          = state.order_depths[PEPPER]
            current_pos = state.position.get(PEPPER, 0)

            best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
            best_bid = max(od.buy_orders.keys())  if od.buy_orders  else None

            if day_offset is None and best_ask is not None:
                if best_ask < 10500:   day_offset = 0
                elif best_ask < 11500: day_offset = 1
                else:                  day_offset = 2

            if best_ask is not None and best_bid is not None:
                mid = (best_ask + best_bid) / 2.0
                tracker.update(state.timestamp, mid)
                slope = tracker.slope()

                product_orders: list[Order] = []

                # Cas 1 : warmup ou pente positive → base + swing
                if slope is None or slope > SLOPE_THRESHOLD:
                    abs_timestamp = state.timestamp + (day_offset * 1_000_000)
                    fair_price    = INTERCEPT + PENTE * abs_timestamp

                    if current_pos < BASE_POSITION:
                        qty = BASE_POSITION - current_pos
                        product_orders.append(Order(PEPPER, best_ask, qty))
                    else:
                        swing_pos            = current_pos - BASE_POSITION
                        swing_available_buy  = SWING_MAX - swing_pos
                        swing_available_sell = swing_pos

                        if swing_available_buy > 0 and best_ask <= fair_price + 2:
                            product_orders.append(Order(PEPPER, best_ask, swing_available_buy))
                        if swing_available_sell > 0 and best_bid > fair_price + 2:
                            product_orders.append(Order(PEPPER, best_bid, -swing_available_sell))

                # Cas 2 : pente nulle → market-making
                elif abs(slope) <= SLOPE_THRESHOLD:
                    buy_qty  = min(10, MAX_POSITION - current_pos)
                    sell_qty = min(10, MAX_POSITION + current_pos)
                    if buy_qty > 0:
                        product_orders.append(Order(PEPPER, best_bid,  buy_qty))
                    if sell_qty > 0:
                        product_orders.append(Order(PEPPER, best_ask, -sell_qty))

                # Cas 3 : pente négative → liquider et shorter
                else:
                    qty = MAX_POSITION + current_pos
                    if qty > 0:
                        product_orders.append(Order(PEPPER, best_bid, -qty))

                if product_orders:
                    result[PEPPER] = product_orders

        trader_data["tracker"]    = tracker.to_dict()
        trader_data["day_offset"] = day_offset

        # ── Flush ──────────────────────────────────────────────────────────────
        new_trader_data = json.dumps(trader_data)
        logger.flush(state, result, conversions, new_trader_data)
        return result, conversions, new_trader_data
