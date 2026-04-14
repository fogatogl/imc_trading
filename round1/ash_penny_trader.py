"""
ash_penny_trader.py
-------------------
ASH_COATED_OSMIUM simple penny-jump spread-capture strategy.

Statistical basis (ash_coated_osmium_analysis.ipynb):
  - Spread = 16 in 66% of ticks → penny-jump earns 14 ticks per round-trip.
  - Mean-reverting (VR=0.506) → inventory skew self-corrects.
  - Large bid (imbalance > 0.75): avg fwd return = -0.089% ≈ -0.9 ticks → pull bid.
  - Large ask (imbalance < 0.25): avg fwd return = -0.169% ≈ -1.7 ticks → pull bid more.
  Both extreme-imbalance cases predict a price drop regardless of direction.
  Response: lower bid defensively to avoid adverse selection; leave ask at penny
  so we still capture sells before the drop.

    my_bid = best_bid + 1  -  skew  -  obi_offset
    my_ask = best_ask - 1  -  skew

    skew       = clip(INV_SKEW × pos, -MAX_SKEW, +MAX_SKEW)
    obi_offset = 2 when imbalance > 0.75
               = 3 when imbalance < 0.25
               = 0 otherwise

Backtest (from project root):
  PYTHONPATH=imc_trading/imc-prosperity-4-backtester \\
  .venv/Scripts/python.exe -m prosperity4bt \\
  round1/ash_penny_trader.py 1--2 1--1 1-0 --data dataset --no-vis --no-out
"""

try:
    from datamodel import Order, TradingState
except ImportError:
    from prosperity4bt.datamodel import Order, TradingState

from typing import List

# ── Parameters ─────────────────────────────────────────────────────────────────

PRODUCT   = "ASH_COATED_OSMIUM"
POS_LIMIT = 50   # backtester enforces 50; live limit may be 80

# Linear inventory skew: both quotes shift by (INV_SKEW × pos) ticks, capped.
# At pos=50 raw skew = 7.5 → capped to MAX_SKEW.
INV_SKEW = 0.15
MAX_SKEW = 7

# OBI defensive offsets — stat: both extreme-imbalance cases predict price drop.
# Sizes chosen to exceed the expected drop magnitude (0.9 and 1.7 ticks).
OBI_OFFSET_LARGE_BID = 2   # imbalance > 0.75 → expected -0.9 ticks
OBI_OFFSET_LARGE_ASK = 3   # imbalance < 0.25 → expected -1.7 ticks


# ── Trader ─────────────────────────────────────────────────────────────────────

class Trader:

    def run(self, state: TradingState) -> tuple[dict, int, str]:
        orders: dict = {p: [] for p in state.order_depths}

        od = state.order_depths.get(PRODUCT)
        if not od or not od.buy_orders or not od.sell_orders:
            return orders, 0, ""

        best_bid: int = max(od.buy_orders)
        best_ask: int = min(od.sell_orders)
        spread:   int = best_ask - best_bid

        pos: int = state.position.get(PRODUCT, 0)

        # ── OBI ───────────────────────────────────────────────────────────────
        bid_vol   = od.buy_orders[best_bid]
        ask_vol   = abs(od.sell_orders[best_ask])
        total     = bid_vol + ask_vol
        imbalance = bid_vol / total if total > 0 else 0.5

        # ── Inventory skew (same direction for both quotes) ────────────────────
        skew: int = int(max(-MAX_SKEW, min(MAX_SKEW, round(INV_SKEW * pos))))

        # ── OBI defensive bid offset ───────────────────────────────────────────
        if imbalance > 0.75:
            obi_offset = OBI_OFFSET_LARGE_BID
        elif imbalance < 0.25:
            obi_offset = OBI_OFFSET_LARGE_ASK
        else:
            obi_offset = 0

        # ── Penny-jump: bid lowered by OBI offset, ask unaffected ──────────────
        if spread > 2:
            my_bid = best_bid + 1 - skew - obi_offset
            my_ask = best_ask - 1 - skew
        else:
            my_bid = best_bid - skew - obi_offset
            my_ask = best_ask - skew

        # Guard: ensure quotes never cross
        if my_bid >= my_ask:
            my_ask = my_bid + 1

        # ── Sizes: full remaining capacity ─────────────────────────────────────
        buy_qty:  int = POS_LIMIT - pos
        sell_qty: int = POS_LIMIT + pos

        product_orders: List[Order] = []
        if buy_qty  > 0:
            product_orders.append(Order(PRODUCT, my_bid,   buy_qty))
        if sell_qty > 0:
            product_orders.append(Order(PRODUCT, my_ask,  -sell_qty))

        orders[PRODUCT] = product_orders
        return orders, 0, ""
