"""
mmstrat.py — TOMATOES Market Making Strategy
Implementation of tomatoes_market_making_plan.md with real empirical values.

Statistical observations from round 0 data (20 000 ticks across 2 days):
  - Median spread:       13 ticks
  - Avg |return|/tick:   0.786 → VOL_THRESHOLD = 2.0 (avg > threshold → high vol)
  - Lag-1 ACF returns:   -0.41 → strongly mean-reverting → passive maker optimal
  - Typical BBO volume:  ~7-8 units each side
  - POSITION_LIMIT:      80

Strategy: last+im+v with inventory skew (§4.4 + §5 of plan)
  - Base price = latest trade price (fallback: mid-quote)
  - Spread widened in high-vol regime (avg |return| over window > VOL_THRESHOLD)
  - Quotes skewed when order book imbalance |λ| > 0.5
  - Inventory skew applied continuously
  - Emergency liquidation if |pos| > 70
"""

import json
import math
from typing import Any, List

from datamodel import (
    Listing, Observation, Order, OrderDepth, ProsperityEncoder,
    Symbol, Trade, TradingState,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Empirically-tuned constants (from round 0 data analysis)
# ---------------------------------------------------------------------------

PRODUCT             = "TOMATOES"
POSITION_LIMIT      = 80
TS                  = 1          # tick size (integer prices)

# Volatility filter: avg |return| over last VOL_WINDOW ticks vs threshold
# Observed avg = 0.786; 2.0 triggers only in genuinely elevated vol regimes
VOL_WINDOW          = 20
VOL_THRESHOLD       = 2.0        # avg |Δprice| above which we widen spread

# Order imbalance filter (§4.4)
LAMBDA1             = 0.5        # imbalance trigger threshold

# Inventory skew (§5.1)
# ACF = -0.41 → positions mean-revert quickly, mild skew is sufficient
SKEW_FACTOR         = 0.3        # ticks per unit of normalised position

# Emergency liquidation threshold (§5.3)
LIQUIDATION_THRESHOLD = 70       # |pos| above which we hit market to reduce

# Quote order size: use full remaining capacity (same as trader.py approach)
# With POSITION_LIMIT=80 and median spread=13, filling the full book is correct
ORDER_SIZE          = None       # None = use full remaining capacity

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_state(trader_data: str) -> dict:
    if not trader_data:
        return {"price_history": [], "last_price": None}
    try:
        return json.loads(trader_data)
    except Exception:
        return {"price_history": [], "last_price": None}


def save_state(s: dict) -> str:
    s["price_history"] = s["price_history"][-50:]
    return json.dumps(s)


def get_base_price(state: TradingState, depth: OrderDepth) -> float:
    """Latest trade price (plan §4.1). Fallback to mid-quote."""
    trades = state.market_trades.get(PRODUCT, [])
    if trades:
        return float(trades[-1].price)
    best_bid = max(depth.buy_orders)
    best_ask = min(depth.sell_orders)
    return (best_bid + best_ask) / 2.0


def is_high_volatility(price_history: list, window: int = VOL_WINDOW,
                        threshold: float = VOL_THRESHOLD) -> bool:
    """True when rolling average |return| exceeds threshold (plan §4.3)."""
    if len(price_history) < window:
        return False
    recent = price_history[-window:]
    avg_abs_return = sum(abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))) / (len(recent) - 1)
    return avg_abs_return > threshold


def compute_imbalance(depth: OrderDepth) -> float:
    """Order-book imbalance in [-1, +1] (plan §4.4)."""
    qb = sum(depth.buy_orders.values())        # positive
    qs = -sum(depth.sell_orders.values())      # make positive
    total = qb + qs
    if total == 0:
        return 0.0
    return (qb - qs) / total


def apply_inventory_skew(ask: float, bid: float, pos: int) -> tuple:
    """Shift both quotes down when long, up when short (plan §5.1)."""
    skew_ticks = round(SKEW_FACTOR * pos / POSITION_LIMIT * POSITION_LIMIT)
    # simpler: skew proportional to raw position
    skew_ticks = round(SKEW_FACTOR * pos / POSITION_LIMIT)
    return ask - skew_ticks, bid - skew_ticks


def clamp_volume(side_qty: int, pos: int) -> int:
    """Ensure order does not push position past limit (plan §5.2)."""
    if side_qty > 0:
        return min(side_qty, POSITION_LIMIT - pos)
    else:
        return max(side_qty, -POSITION_LIMIT - pos)


def liquidation_orders(depth: OrderDepth, pos: int) -> List[Order]:
    """Market-crossing orders to reduce extreme positions (plan §5.3)."""
    orders = []
    if pos > LIQUIDATION_THRESHOLD:
        best_bid = max(depth.buy_orders)
        qty = min(pos - LIQUIDATION_THRESHOLD + 5, 10)
        orders.append(Order(PRODUCT, best_bid, -qty))
    elif pos < -LIQUIDATION_THRESHOLD:
        best_ask = min(depth.sell_orders)
        qty = min(-pos - LIQUIDATION_THRESHOLD + 5, 10)
        orders.append(Order(PRODUCT, best_ask, qty))
    return orders


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------

class Trader:

    def run(self, state: TradingState) -> tuple:
        s = load_state(state.traderData)
        result: dict = {}
        conversions = 0

        depth: OrderDepth = state.order_depths.get(PRODUCT)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return result, conversions, save_state(s)

        pos: int = state.position.get(PRODUCT, 0)
        orders: List[Order] = []

        # ── 1. Base price ────────────────────────────────────────────────
        Pt = get_base_price(state, depth)
        delta = abs(Pt - s["last_price"]) if s["last_price"] is not None else 0.0
        s["price_history"].append(Pt)
        s["last_price"] = Pt

        # ── 2. Strategy component selection ─────────────────────────────
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        spread   = best_ask - best_bid

        high_vol  = is_high_volatility(s["price_history"])
        imbalance = compute_imbalance(depth)

        # BBO-relative pennying base (captures most of the 13-tick spread).
        # The plan's Pt±TS only made sense for tight-spread markets.
        # With median spread=13 we quote at best_bid+1 / best_ask-1 to penny.
        # Imbalance and volatility adjustments then move us away from BBO:
        #   +im: skew quote direction based on order flow signal
        #   +v:  widen spread when average |return| > VOL_THRESHOLD
        vol_widen = (math.ceil(delta) + 1) if high_vol else 0

        if imbalance > LAMBDA1:
            # Buyers dominate → price likely UP: lift ask, stay aggressive on bid
            ask_price = best_ask + vol_widen        # don't undersell
            bid_price = best_bid + 1 - vol_widen    # buy at best + 1 (aggressive)
        elif imbalance < -LAMBDA1:
            # Sellers dominate → price likely DOWN: lower bid, stay aggressive on ask
            ask_price = best_ask - 1 + vol_widen    # sell at best - 1 (aggressive)
            bid_price = best_bid - vol_widen         # don't overbuy
        else:
            # Balanced: penny both sides; widen symmetrically in high vol
            ask_price = best_ask - 1 + vol_widen
            bid_price = best_bid + 1 - vol_widen

        # ── 3. Inventory skew ────────────────────────────────────────────
        raw_ask, raw_bid = apply_inventory_skew(float(ask_price), float(bid_price), pos)
        ask_price = math.ceil(raw_ask)
        bid_price = math.floor(raw_bid)

        logger.print(
            f"t={state.timestamp} Pt={Pt} delta={delta:.2f} "
            f"imb={imbalance:.3f} high_vol={high_vol} pos={pos} "
            f"bid={bid_price} ask={ask_price}"
        )

        # ── 4. Emergency liquidation (overrides normal quoting) ──────────
        liq = liquidation_orders(depth, pos)
        if liq:
            result[PRODUCT] = liq
            logger.flush(state, result, conversions, save_state(s))
            return result, conversions, save_state(s)

        # ── 5. Submit passive quotes ─────────────────────────────────────
        # Use full remaining capacity (up to POSITION_LIMIT)
        bid_vol = POSITION_LIMIT - pos   # max units we can still buy
        ask_vol = POSITION_LIMIT + pos   # max units we can still sell (positive)

        if ask_vol > 0:
            orders.append(Order(PRODUCT, ask_price, -ask_vol))
        if bid_vol > 0:
            orders.append(Order(PRODUCT, bid_price, bid_vol))

        result[PRODUCT] = orders
        trader_data_str = save_state(s)
        logger.flush(state, result, conversions, trader_data_str)
        return result, conversions, trader_data_str
