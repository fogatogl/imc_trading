"""
ash_obi_trader.py
-----------------
ASH_COATED_OSMIUM OBI-adjusted fair-value market maker.

Signal:  OBI = (bid_vol_1 - ask_vol_1) / (bid_vol_1 + ask_vol_1)
         Linear regression: fwd_1 = 0.010 + 6.74 * OBI  (R²=0.42, n=29,948)
         Correlation 0.645, t-stat ~57 at |OBI|>0.25, hit-rate ~88%.

Architecture:
  Adjust the fair-value estimate by the OBI regression prediction, then
  quote the standard EMA ± vol-spread around the adjusted centre:

      adjusted_fv = ema + OBI_LAMBDA * obi_ema
      my_bid = round(adjusted_fv - half_spread - INV_SKEW * pos)
      my_ask = round(adjusted_fv + half_spread - INV_SKEW * pos)

  This is equivalent to a continuous directional target of
  target = (OBI_LAMBDA / INV_SKEW) * obi_ema ≈ ±13 units at |OBI|=1.
  Quotes shift into the signal — passively accumulating position toward
  the OBI-implied fair value without ever crossing the 16-tick spread.

  OBI is EMA-smoothed (alpha=0.4) to suppress boundary noise while
  preserving the lag-1 signal persistence seen in the data.

State persisted in traderData JSON:
  {"ema": float, "mid_buf": [float,...], "obi_ema": float}

Backtest (from project root):
  PYTHONPATH=imc_trading/imc-prosperity-4-backtester \\
  .venv/Scripts/python.exe -m prosperity4bt \\
  round1/ash_obi_trader.py 1--2 1--1 1-0 --data dataset --no-vis --no-out
"""

try:
    from datamodel import Order, TradingState
except ImportError:
    from prosperity4bt.datamodel import Order, TradingState

import json
import math
from typing import Any

# ── Parameters ─────────────────────────────────────────────────────────────────

PRODUCT   = "ASH_COATED_OSMIUM"
POS_LIMIT = 50

# OBI → fair-value adjustment
# Regression slope: fwd_1 = 6.74 * OBI (3-day dataset)
# OBI_LAMBDA tuned by grid search: best at 10.0 (total PnL 23,982 vs baseline 9,126)
OBI_LAMBDA: float = 10.0

# OBI EMA smoothing — alpha=0.3 ≈ span-6 bar EMA; tuned by grid search
OBI_EMA_ALPHA: float = 0.3

# Market-making spread — tuned by grid search
MIN_HALF_SPREAD: float = 4.0   # wider spread → earn more per fill; OBI signal pulls quotes in
VOL_MULT:        float = 0.5   # half_spread = max(MIN_HALF_SPREAD, VOL_MULT * sigma)
VOL_WINDOW:      int   = 10    # rolling window (bars) for realized vol

# Inventory skew — per unit of raw position; tuned by grid search
# Equilibrium pos = OBI_LAMBDA / INV_SKEW * obi_ema = 50 * obi_ema (max ±50 at |obi|=1)
INV_SKEW: float = 0.2

# EMA for fair-value
EMA_SPAN:   int   = 5
_EMA_ALPHA: float = 2.0 / (EMA_SPAN + 1)  # 0.333


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_mid(od: Any) -> float | None:
    best_bid = max(od.buy_orders)  if od.buy_orders  else None
    best_ask = min(od.sell_orders) if od.sell_orders else None
    if best_bid is not None and best_ask is not None:
        return (best_bid + best_ask) / 2.0
    if best_bid is not None:
        return float(best_bid)
    if best_ask is not None:
        return float(best_ask)
    return None


def _compute_obi(od: Any) -> float | None:
    """
    Level-1 OBI in [-1, 1]. Returns None when either side absent.
    NOTE: sell_orders stores negative quantities — abs() required.
    """
    if not od.buy_orders or not od.sell_orders:
        return None
    best_bid = max(od.buy_orders)
    best_ask = min(od.sell_orders)
    bid_vol  = od.buy_orders[best_bid]
    ask_vol  = abs(od.sell_orders[best_ask])
    total    = bid_vol + ask_vol
    if total == 0:
        return None
    return (bid_vol - ask_vol) / total


def _rolling_std(buf: list[float]) -> float:
    if len(buf) < 3:
        return MIN_HALF_SPREAD
    changes = [buf[k + 1] - buf[k] for k in range(len(buf) - 1)]
    n    = len(changes)
    mean = sum(changes) / n
    var  = sum((c - mean) ** 2 for c in changes) / max(n - 1, 1)
    return math.sqrt(var) if var > 0.0 else MIN_HALF_SPREAD


# ── Trader ─────────────────────────────────────────────────────────────────────

class Trader:
    """
    OBI-adjusted fair-value market maker for ASH_COATED_OSMIUM.

    Core change vs pure MM (ash_mm_trader.py):
      adjusted_fv = ema + OBI_LAMBDA * obi_ema
    Quotes are centred on adjusted_fv instead of ema.
    When OBI > 0 both quotes shift up → easier to buy, harder to sell → long accumulation.
    When OBI < 0 both quotes shift down → short accumulation.
    Standard INV_SKEW * pos limits runaway inventory.
    """

    def run(self, state: TradingState) -> tuple[dict, int, str]:
        # ── Restore state ──────────────────────────────────────────────────────
        try:
            st: dict = json.loads(state.traderData) if state.traderData else {}
        except (json.JSONDecodeError, TypeError):
            st = {}

        ema:     float = st.get("ema",     0.0)
        mid_buf: list  = st.get("mid_buf", [])
        obi_ema: float = st.get("obi_ema", 0.0)

        orders: dict = {p: [] for p in state.order_depths}

        od = state.order_depths.get(PRODUCT)
        if od is None:
            return orders, 0, _dump(ema, mid_buf, obi_ema)

        # ── Mid-price (skip mid=0 artifact: both book sides absent) ───────────
        mid = _get_mid(od)
        if mid is None or mid <= 0:
            return orders, 0, _dump(ema, mid_buf, obi_ema)

        # ── EMA fair-value ─────────────────────────────────────────────────────
        ema = mid if ema == 0.0 else _EMA_ALPHA * mid + (1.0 - _EMA_ALPHA) * ema

        # ── Rolling vol buffer ─────────────────────────────────────────────────
        mid_buf.append(mid)
        if len(mid_buf) > VOL_WINDOW + 1:
            mid_buf = mid_buf[-(VOL_WINDOW + 1):]

        # ── OBI EMA (only update when both sides present) ──────────────────────
        obi_raw = _compute_obi(od)
        if obi_raw is not None:
            obi_ema = OBI_EMA_ALPHA * obi_raw + (1.0 - OBI_EMA_ALPHA) * obi_ema

        # ── OBI-adjusted fair value ────────────────────────────────────────────
        adjusted_fv = ema + OBI_LAMBDA * obi_ema

        # ── Quote levels ───────────────────────────────────────────────────────
        sigma       = _rolling_std(mid_buf)
        half_spread = max(MIN_HALF_SPREAD, VOL_MULT * sigma)
        pos:   int  = state.position.get(PRODUCT, 0)
        skew        = INV_SKEW * pos

        my_bid = int(round(adjusted_fv - half_spread - skew))
        my_ask = int(round(adjusted_fv + half_spread - skew))
        if my_bid >= my_ask:
            my_ask = my_bid + 1

        buy_qty  = max(0, POS_LIMIT - pos)
        sell_qty = max(0, POS_LIMIT + pos)

        product_orders = []
        if buy_qty  > 0:
            product_orders.append(Order(PRODUCT, my_bid,   buy_qty))
        if sell_qty > 0:
            product_orders.append(Order(PRODUCT, my_ask,  -sell_qty))

        orders[PRODUCT] = product_orders
        return orders, 0, _dump(ema, mid_buf, obi_ema)


# ── State serialisation ────────────────────────────────────────────────────────

def _dump(ema: float, mid_buf: list, obi_ema: float) -> str:
    return json.dumps({"ema": ema, "mid_buf": mid_buf, "obi_ema": obi_ema},
                      separators=(",", ":"))
