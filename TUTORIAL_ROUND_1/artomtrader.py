from datamodel import OrderDepth, TradingState, Order
import json
import math

# ─── Parameters ────────────────────────────────────────────────────────────────

PRODUCT = "TOMATOES"

# AR(5) coefficients — averaged across day -1 and day -2 [L1, L2, L3, L4, L5]
AR_COEFS = [-0.549, -0.317, -0.174, -0.093, -0.043]

HALF_SPREAD       = 4.5   # half the quoted bid-ask width (points)
SKEW_PER_UNIT     = 0.2   # points of quote shift per unit of net inventory
MAX_POSITION      = 80    # hard inventory limit in either direction
ORDER_SIZE        = 5     # units per quote
REQUOTE_THRESHOLD = 2.0   # not used for cancellation (orders auto-expire each tick)
AR_WARMUP_TICKS   = 10    # ticks before AR signal is trusted
SIGNAL_CAP        = 0.05  # cap AR signal at ±5% to filter data artefacts
FV_SANITY_LIMIT   = 50.0  # abort if fair_value drifts >50 pts from mid


# ─── AR(5) Signal ──────────────────────────────────────────────────────────────

def _compute_log_return(prev_mid: float, curr_mid: float) -> float:
    return math.log(curr_mid / prev_mid)


def _compute_ar_signal(return_history: list, coefs: list) -> float:
    """
    return_history: list of last N log returns, index 0 = most recent.
    Returns 0.0 if fewer returns than coefficients are available.
    Signal is capped at ±SIGNAL_CAP.
    """
    if len(return_history) < len(coefs):
        return 0.0
    raw = sum(coefs[i] * return_history[i] for i in range(len(coefs)))
    return max(-SIGNAL_CAP, min(SIGNAL_CAP, raw))


# ─── Quoting ───────────────────────────────────────────────────────────────────

def _compute_fair_value(mid: float, signal: float) -> float:
    """First-order approximation: fair_value = mid * (1 + signal)."""
    return mid * (1.0 + signal)


def _compute_quotes(fair_value: float, inventory: int):
    """
    Returns (bid_price, ask_price). Either may be None when at inventory limit.

    inv_adj shifts both quotes away from the current position:
      long  → quotes shift down (eager to sell, reluctant to buy more)
      short → quotes shift up  (eager to buy, reluctant to sell more)
    """
    inv_adj = SKEW_PER_UNIT * inventory
    bid = fair_value - HALF_SPREAD - inv_adj
    ask = fair_value + HALF_SPREAD - inv_adj

    if inventory >= +MAX_POSITION:
        return (None, ask)   # fully long — no more bids
    if inventory <= -MAX_POSITION:
        return (bid,  None)  # fully short — no more asks
    return (bid, ask)


# ─── Trader ────────────────────────────────────────────────────────────────────

class Trader:
    """
    AR(5)-adjusted, inventory-skewed market maker for TOMATOES.

    Strategy reference: TUTORIAL_ROUND_1/tomates/tomato_market_making_strategy.md

    Persistent state (via traderData JSON):
      return_history : list[float]  — last 5 log returns, index 0 = most recent
      prev_mid       : float|None   — mid price at the previous tick
      prev_fv        : float|None   — fair value at the previous tick
      tick_count     : int          — total ticks processed
    """

    def run(self, state: TradingState):
        # ── Load persistent memory ────────────────────────────────────────────
        memory = json.loads(state.traderData) if state.traderData else {}
        return_history = memory.get("return_history", [])
        prev_mid       = memory.get("prev_mid",   None)
        prev_fv        = memory.get("prev_fv",    None)
        tick_count     = memory.get("tick_count",  0)

        result = {}

        # ── Guard: product must be in state ───────────────────────────────────
        if PRODUCT not in state.order_depths:
            return result, 0, _save(return_history, prev_mid, prev_fv, tick_count)

        depth    = state.order_depths[PRODUCT]
        best_bid = max(depth.buy_orders.keys(),  default=None)
        best_ask = min(depth.sell_orders.keys(), default=None)

        # ── Guard: book must be two-sided ─────────────────────────────────────
        if best_bid is None or best_ask is None:
            return result, 0, _save(return_history, prev_mid, prev_fv, tick_count)

        mid = (best_bid + best_ask) / 2.0
        tick_count += 1

        # ── 1. Update log-return history ──────────────────────────────────────
        if prev_mid is not None:
            lr = _compute_log_return(prev_mid, mid)
            return_history.insert(0, lr)          # prepend → index 0 = most recent
            return_history = return_history[:5]   # keep only last 5

        prev_mid = mid

        # ── 2. Compute AR(5) signal ───────────────────────────────────────────
        if tick_count < AR_WARMUP_TICKS:
            signal = 0.0
        else:
            signal = _compute_ar_signal(return_history, AR_COEFS)

        # ── 3. Fair value + sanity check ──────────────────────────────────────
        fair_value = _compute_fair_value(mid, signal)
        if abs(fair_value - mid) > FV_SANITY_LIMIT:
            # Stale or corrupt data — skip this tick without submitting orders
            return result, 0, _save(return_history, prev_mid, prev_fv, tick_count)

        # ── 4. Compute bid / ask quotes ───────────────────────────────────────
        position       = state.position.get(PRODUCT, 0)
        bid_px, ask_px = _compute_quotes(fair_value, position)

        # Both suppressed by inventory limits — nothing to do
        if bid_px is None and ask_px is None:
            return result, 0, _save(return_history, prev_mid, fair_value, tick_count)

        # ── 5. Submit orders ──────────────────────────────────────────────────
        product_orders = []
        if bid_px is not None:
            product_orders.append(Order(PRODUCT, round(bid_px), +ORDER_SIZE))
        if ask_px is not None:
            product_orders.append(Order(PRODUCT, round(ask_px), -ORDER_SIZE))

        result[PRODUCT] = product_orders

        return result, 0, _save(return_history, prev_mid, fair_value, tick_count)


def _save(return_history, prev_mid, prev_fv, tick_count) -> str:
    return json.dumps({
        "return_history": return_history,
        "prev_mid":       prev_mid,
        "prev_fv":        prev_fv,
        "tick_count":     tick_count,
    })
