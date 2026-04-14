"""
ash_mm_trader.py
----------------
ASH_COATED_OSMIUM pure market-making trader.

Quoting logic:
  fair_value  = EMA(mid_price, span=EMA_SPAN)
  half_spread = max(MIN_HALF_SPREAD, VOL_MULT * rolling_std(1-bar changes, VOL_WINDOW))
  skew        = INV_SKEW * position          (positive pos → push quotes down)
  my_bid      = round(fair_value - half_spread - skew)
  my_ask      = round(fair_value + half_spread - skew)
  buy_qty     = POS_LIMIT - pos              (full remaining capacity)
  sell_qty    = POS_LIMIT + pos

Statistical basis:
  VR(2)=0.506 → ρ(1)≈-0.494  strong mean-reversion at 1-bar horizon
  VR(4)=0.258 → extreme mean-reversion at 4-bar horizon
  AR(10): all coefficients negative → price reliably reverts after moves
  Position limit: 50 units

Parameter origin:
  Constants below are initial defaults.
  Run  python round1/ash_mm_param_search.py  and paste best params here.

Backtest:
  cd <project_root>
  python -m prosperity4bt round1/ash_mm_trader.py 1 --data dataset/ROUND_1 --no-vis
"""

try:
    from datamodel import Order, TradingState
except ImportError:
    from prosperity4bt.datamodel import Order, TradingState

import json
import math
from typing import Any

# ── Strategy parameters ────────────────────────────────────────────────────────
# Update these from ash_mm_param_search.py results.

PRODUCT = "ASH_COATED_OSMIUM"
POS_LIMIT: int = 50

EMA_SPAN: int        = 5     # EMA window for fair-value estimate        | sweep best
VOL_WINDOW: int      = 10    # rolling window (bars) for realized vol       | sweep best
VOL_MULT: float      = 0.5   # half_spread = max(MIN_HALF_SPREAD, VOL_MULT*sigma) | sweep best
MIN_HALF_SPREAD: float = 2.0 # absolute minimum half-spread in price ticks  | sweep best
INV_SKEW: float      = 0.5   # per-unit inventory skew (shift quotes toward flat)  | sweep best
# Sweep result: Sharpe=0.82, PnL=1306, MaxDD=-161 over 30,000 bars (3 days)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rolling_std(buf: list[float]) -> float:
    """Unbiased std of 1-bar price changes within buf."""
    if len(buf) < 3:
        return MIN_HALF_SPREAD
    changes = [buf[k + 1] - buf[k] for k in range(len(buf) - 1)]
    n = len(changes)
    mean = sum(changes) / n
    var = sum((c - mean) ** 2 for c in changes) / max(n - 1, 1)
    return math.sqrt(var) if var > 0.0 else MIN_HALF_SPREAD


def _get_mid(od: Any) -> float | None:
    """Mid price from order depth; None if fully empty."""
    best_bid = max(od.buy_orders)  if od.buy_orders  else None
    best_ask = min(od.sell_orders) if od.sell_orders else None
    if best_bid is not None and best_ask is not None:
        return (best_bid + best_ask) / 2.0
    if best_bid is not None:
        return float(best_bid)
    if best_ask is not None:
        return float(best_ask)
    return None


# ── Trader ─────────────────────────────────────────────────────────────────────

class Trader:
    """
    Pure market-making strategy for ASH_COATED_OSMIUM.

    State persisted via traderData JSON:
      {
        "ema":     float,          # current EMA of mid-price
        "mid_buf": [float, ...]    # last (VOL_WINDOW + 1) mid-prices for vol
      }
    """

    # EMA decay constant — computed at class load from module-level EMA_SPAN
    _ALPHA: float = 2.0 / (EMA_SPAN + 1)   # = 2/(5+1) = 0.333

    def run(self, state: TradingState) -> tuple[dict, int, str]:
        # ── Restore state ──────────────────────────────────────────────────────
        try:
            st: dict = json.loads(state.traderData) if state.traderData else {}
        except (json.JSONDecodeError, TypeError):
            st = {}

        ema: float       = st.get("ema", 0.0)
        mid_buf: list    = st.get("mid_buf", [])

        # Initialise with empty lists for every product the exchange sends us
        orders: dict = {p: [] for p in state.order_depths}

        # ── Order depth for our product ────────────────────────────────────────
        od = state.order_depths.get(PRODUCT)
        if od is None:
            return orders, 0, self._dump(ema, mid_buf)

        # ── Mid-price ──────────────────────────────────────────────────────────
        mid = _get_mid(od)
        if mid is None:
            # Empty book — skip quoting but preserve state
            return orders, 0, self._dump(ema, mid_buf)

        # ── EMA update (incremental) ───────────────────────────────────────────
        ema = mid if ema == 0.0 else self._ALPHA * mid + (1.0 - self._ALPHA) * ema

        # ── Rolling price buffer ───────────────────────────────────────────────
        mid_buf.append(mid)
        if len(mid_buf) > VOL_WINDOW + 1:
            mid_buf = mid_buf[-(VOL_WINDOW + 1):]

        # ── Realized vol ───────────────────────────────────────────────────────
        sigma = _rolling_std(mid_buf)

        # ── Quote levels ───────────────────────────────────────────────────────
        half_spread = max(MIN_HALF_SPREAD, VOL_MULT * sigma)
        pos: int = state.position.get(PRODUCT, 0)
        skew = INV_SKEW * pos    # long → push both quotes down (sell more)

        my_bid = int(round(ema - half_spread - skew))
        my_ask = int(round(ema + half_spread - skew))
        if my_bid >= my_ask:
            my_ask = my_bid + 1

        # ── Order sizing: post the full remaining capacity on each side ────────
        buy_qty  = POS_LIMIT - pos    # max additional longs we can hold
        sell_qty = POS_LIMIT + pos    # max additional shorts we can hold

        product_orders = []
        if buy_qty  > 0:
            product_orders.append(Order(PRODUCT, my_bid,   buy_qty))
        if sell_qty > 0:
            product_orders.append(Order(PRODUCT, my_ask,  -sell_qty))

        orders[PRODUCT] = product_orders

        return orders, 0, self._dump(ema, mid_buf)

    # ── State serialisation ────────────────────────────────────────────────────
    @staticmethod
    def _dump(ema: float, mid_buf: list) -> str:
        return json.dumps({"ema": ema, "mid_buf": mid_buf}, separators=(",", ":"))
