# TOMATOES Market Making Strategy
## IMC Prosperity 4 — AR-Adjusted Asymmetric Market Maker

---

## Overview

This document is a full specification of the market making strategy for the TOMATOES product in IMC Prosperity 4. It is intended both as a human-readable strategy description and as a precise implementation brief for Claude Code.

The strategy is an **AR(5)-adjusted, inventory-skewed market maker**. It quotes a bid and an ask every tick, shifts both quotes toward the statistically predicted next price using an AR(5) signal, and continuously skews quotes away from the current inventory position to avoid breaching hard limits.

The statistical basis is documented in `tomato_statistical_analysis.md`. The key findings that drive every design decision are:

- TOMATOES returns are strongly **mean-reverting** (Hurst H≈0.39, VR(k=2)≈0.57)
- An **AR(5) model** fully captures the autocorrelation structure (Durbin-Watson = 2.00)
- The **L1 AR coefficient ≈ −0.55** — roughly 43% of each tick's move is expected to reverse immediately
- **No reliable drift** — the intercept is statistically zero on both days
- The process is **I(1) in levels, I(0) in log returns** — all signals are computed on returns

---

## File Structure (expected by Claude Code)

```
trader.py          ← main entry point, contains the Trader class
strategy/
  ar_signal.py     ← AR(5) signal computation
  quoting.py       ← bid/ask quote generation
  inventory.py     ← inventory tracking and skew logic
  params.py        ← all tunable parameters in one place
```

---

## Parameters

All tunable parameters live in `strategy/params.py`. Do not hardcode them elsewhere.

```python
# strategy/params.py

PRODUCT = "TOMATOES"

# AR(5) coefficients — averaged across day -1 and day -2
# Order: [L1, L2, L3, L4, L5]
AR_COEFS = [-0.549, -0.317, -0.174, -0.093, -0.043]

# Quoting
HALF_SPREAD   = 4.5    # points — half the quoted bid-ask width
SKEW_PER_UNIT = 0.2    # points of quote shift per unit of net inventory
MAX_POSITION  = 20     # hard inventory limit in either direction

# Order sizing
ORDER_SIZE = 5         # units per quote (tune to book depth at L1)

# Signal staleness — cancel resting orders if mid has moved more than this
REQUOTE_THRESHOLD = 2.0   # points

# Minimum number of returns needed before the AR signal is trusted
AR_WARMUP_TICKS = 10
```

---

## Data Structures

### Input per tick (from the IMC framework)
```python
# Available from the OrderDepth and TradingState objects
mid_price: float          # (best_bid + best_ask) / 2
best_bid:  float
best_ask:  float
timestamp: int
current_position: int     # net inventory, positive = long
```

### Internal state (maintained across ticks)
```python
log_return_history: deque(maxlen=5)   # last 5 log returns, index 0 = most recent
prev_mid: float | None                # mid price at the previous tick
```

---

## Module Specifications

### `strategy/ar_signal.py`

**Purpose:** Compute the AR(5) predicted log return for the next tick.

```python
def compute_log_return(prev_mid: float, curr_mid: float) -> float:
    """
    Returns log(curr_mid / prev_mid).
    Called every tick to update the return history.
    """

def compute_ar_signal(return_history: list[float], coefs: list[float]) -> float:
    """
    Args:
        return_history: list of last N log returns, index 0 = most recent.
                        Must have len >= len(coefs); if shorter, return 0.0.
        coefs:          AR coefficients [phi_1, phi_2, ..., phi_p].
                        phi_i multiplies return_history[i-1].

    Returns:
        signal: float — predicted next log return.
                Positive → price expected to rise → lean long.
                Negative → price expected to fall → lean short.

    Formula:
        signal = sum(coefs[i] * return_history[i] for i in range(len(coefs)))

    Note: intercept is omitted (statistically zero on both training days).
    """
```

**Expected behaviour:**
- `compute_ar_signal([-0.01, 0.005, -0.002, 0.001, -0.003], AR_COEFS)`
  → roughly `−0.549 × (−0.01) + ... ≈ +0.0058` (positive signal, lean long)
- Returns `0.0` if fewer than `AR_WARMUP_TICKS` ticks have elapsed.

---

### `strategy/quoting.py`

**Purpose:** Compute the adjusted fair value and final bid/ask quotes.

```python
def compute_fair_value(mid: float, signal: float) -> float:
    """
    Adjusts the current mid price by the AR signal.

    Formula (first-order approximation of exp):
        fair_value = mid * (1 + signal)

    This shifts the quoting centre toward the predicted next price.
    A negative signal (price expected to fall) moves fair_value below mid,
    making the ask easier to fill and the bid harder — a natural short lean.
    """

def compute_quotes(
    fair_value:   float,
    inventory:    int,
    half_spread:  float = HALF_SPREAD,
    skew_per_unit: float = SKEW_PER_UNIT,
    max_position: int   = MAX_POSITION,
) -> tuple[float | None, float | None]:
    """
    Returns (bid_price, ask_price).
    Either may be None if the inventory limit suppresses that side.

    Formula:
        inv_adj  = skew_per_unit * inventory
        bid      = fair_value - half_spread - inv_adj
        ask      = fair_value + half_spread - inv_adj

    Inventory adjustment (inv_adj) interpretation:
        inventory > 0 (long)  → inv_adj > 0 → both quotes shift down
                                → ask becomes cheaper (offloads inventory)
                                → bid becomes cheaper (discourages buying more)
        inventory < 0 (short) → inv_adj < 0 → both quotes shift up
                                → bid becomes more expensive (covers short)
                                → ask becomes more expensive (discourages selling more)

    Hard limits:
        if inventory >= +MAX_POSITION: return (None, ask)   ← no more bids
        if inventory <= -MAX_POSITION: return (bid,  None)  ← no more asks

    Quotes should be rounded to the nearest integer (IMC uses integer prices).
    """
```

**Examples:**

| mid | signal | inventory | half_spread | → fair_value | → bid | → ask |
|-----|--------|-----------|-------------|--------------|-------|-------|
| 5000 | −0.002 | 0  | 4.5 | 4990.0 | 4985.5 | 4994.5 |
| 5000 | −0.002 | +10 | 4.5 | 4990.0 | 4983.5 | 4992.5 |
| 5000 | +0.001 | −5 | 4.5 | 5005.0 | 5001.5 | 5010.5 |
| 5000 | 0.000 | +20 | 4.5 | 5000.0 | None   | 4995.5 |

---

### `strategy/inventory.py`

**Purpose:** Track net inventory and decide whether to cancel stale resting orders.

```python
def should_requote(
    prev_fair_value: float,
    curr_fair_value: float,
    threshold: float = REQUOTE_THRESHOLD,
) -> bool:
    """
    Returns True if the fair value has moved by more than `threshold` points
    since the last time quotes were placed.
    When True, cancel all resting TOMATOES orders before placing new ones.

    Rationale: resting orders at a stale fair value are the primary source
    of adverse selection. Because the AR signal updates every tick, stale
    quotes can be hit by informed flow within 1–2 ticks.
    """
```

---

### `trader.py` — Main Logic

Implement the `Trader` class with a single `run` method as required by the IMC framework.

```python
from dataclasses import dataclass, field
from collections import deque
from typing import Dict
from imc_framework import TradingState, OrderDepth, Order   # adjust import as needed

from strategy.params import *
from strategy.ar_signal import compute_log_return, compute_ar_signal
from strategy.quoting import compute_fair_value, compute_quotes
from strategy.inventory import should_requote

@dataclass
class TomatoState:
    log_return_history: deque = field(default_factory=lambda: deque(maxlen=5))
    prev_mid:           float | None = None
    prev_fair_value:    float | None = None
    tick_count:         int = 0

class Trader:

    def __init__(self):
        self.tomato = TomatoState()

    def run(self, state: TradingState) -> Dict[str, list[Order]]:
        orders = {}

        if PRODUCT not in state.order_depths:
            return orders

        depth    = state.order_depths[PRODUCT]
        best_bid = max(depth.buy_orders.keys(),  default=None)
        best_ask = min(depth.sell_orders.keys(), default=None)

        if best_bid is None or best_ask is None:
            return orders

        mid = (best_bid + best_ask) / 2.0
        s   = self.tomato   # shorthand

        # ── 1. Update return history ──────────────────────────────────────────
        if s.prev_mid is not None:
            lr = compute_log_return(s.prev_mid, mid)
            s.log_return_history.appendleft(lr)
        s.prev_mid   = mid
        s.tick_count += 1

        # ── 2. Compute AR(5) signal ───────────────────────────────────────────
        if s.tick_count < AR_WARMUP_TICKS:
            signal = 0.0
        else:
            signal = compute_ar_signal(list(s.log_return_history), AR_COEFS)

        # ── 3. Compute fair value and quotes ──────────────────────────────────
        fair_value  = compute_fair_value(mid, signal)
        position    = state.position.get(PRODUCT, 0)
        bid_px, ask_px = compute_quotes(fair_value, position)

        # ── 4. Cancel stale resting orders if fair value has shifted ──────────
        cancel = (
            s.prev_fair_value is not None
            and should_requote(s.prev_fair_value, fair_value)
        )
        # In the IMC framework, cancellation is done by submitting 0-volume orders
        # or by not resubmitting resting orders — implement per framework docs.
        # (cancel logic here)

        s.prev_fair_value = fair_value

        # ── 5. Place new orders ───────────────────────────────────────────────
        product_orders = []

        if bid_px is not None:
            product_orders.append(Order(PRODUCT, round(bid_px), +ORDER_SIZE))

        if ask_px is not None:
            product_orders.append(Order(PRODUCT, round(ask_px), -ORDER_SIZE))

        orders[PRODUCT] = product_orders
        return orders
```

---

## Signal Logic — Full Decision Tree

```
Every tick:
│
├── Is mid_price available (both sides of book non-empty)?
│   └── No  → return no orders
│
├── Update log_return_history with new log return
│
├── tick_count < AR_WARMUP_TICKS?
│   ├── Yes → signal = 0.0  (quote symmetrically, no AR lean)
│   └── No  → signal = AR(5) forecast
│
├── fair_value = mid × (1 + signal)
│
├── inventory = state.position[TOMATOES]  (default 0)
│
├── inv_adj = SKEW_PER_UNIT × inventory
│
├── bid = fair_value − HALF_SPREAD − inv_adj
│   ask = fair_value + HALF_SPREAD − inv_adj
│
├── inventory >= +MAX_POSITION?  → suppress bid (set to None)
│   inventory <= −MAX_POSITION?  → suppress ask (set to None)
│
├── |fair_value − prev_fair_value| > REQUOTE_THRESHOLD?
│   └── Yes → cancel all resting TOMATOES orders first
│
└── Submit (bid, ORDER_SIZE) and/or (ask, −ORDER_SIZE)
```

---

## Edge Cases & Defensive Coding Requirements

| Situation | Required behaviour |
|---|---|
| Book is one-sided (no bids or no asks) | Do not compute mid; skip tick; return `{}` |
| `log_return_history` has fewer than 5 elements | Pass partial list to `compute_ar_signal`; function returns 0.0 if `len < len(coefs)` |
| AR signal magnitude > 0.05 (5% predicted move) | Cap signal at ±0.05 — anything larger is likely a data artefact |
| `fair_value` lands inside the current best bid/ask | Normal — this is expected when signal is small. Do not force quotes outside the spread. |
| `fair_value` is more than 50 pts from mid | Abort quoting for this tick — stale or corrupt data |
| Both bid and ask suppressed by inventory limits | Return `{}` — do not submit orders |

---

## Parameter Tuning Guide

Tune in this order on forward/unseen rounds. Change one parameter at a time.

### 1. `HALF_SPREAD`

Controls fill rate vs. PnL per fill. Start at 4.5 (just inside the natural ~9-pt spread). Tighten if fill rate is too low; widen if adverse selection is eroding PnL.

- **Too tight:** High fill rate but negative PnL — the spread doesn't cover the times the AR signal is wrong.
- **Too wide:** Low fill rate — you are rarely best bid/ask and miss most trades.

### 2. `SKEW_PER_UNIT`

Controls how aggressively quotes shift to reduce inventory. Start at 0.2.

- **Too low:** Inventory accumulates and you breach `MAX_POSITION` frequently, causing one side of quotes to be suppressed.
- **Too high:** Quote skew is so large that you miss fills on the side you want to offload.

### 3. `MAX_POSITION`

The hard safety limit. Start at ±20 and widen only after observing typical intraday inventory swings. Never set above ±50 without strong justification.

### 4. `ORDER_SIZE`

Set relative to the L1 volume in the book. L1 bid volume ranges 2–12 (σ=1.79). `ORDER_SIZE = 5` is a reasonable starting point — large enough to matter, small enough not to dominate the book.

### 5. `AR_COEFS`

Do not retrain on the tutorial round data alone. Wait until you have at least 2 additional rounds of data. When retraining, use OLS on log returns with 5 lags; confirm DW≈2.0 before deploying updated coefficients. If DW drifts materially from 2.0, the AR order may need revision.

---

## What This Strategy Does NOT Do

- **No directional position-taking.** The strategy is always two-sided. It does not go net long or short based on the AR signal alone — it only *leans* quotes.
- **No drift adjustment.** The intercept is zero; no directional bias is added. The OLS drift results were contradictory across days and should not be traded.
- **No GARCH / volatility model.** The AR(5) residuals are white noise (DW≈2.00). Adding a volatility layer is not warranted by the data and would add unnecessary complexity.
- **No multi-product hedging.** This spec covers TOMATOES only. Cross-product cointegration is not analysed here.

---

## Testing Checklist (for Claude Code)

Before submitting, verify each of the following:

- [ ] `compute_ar_signal` returns `0.0` when fewer than 5 returns are available
- [ ] `compute_ar_signal` returns a negative value when L1 return is strongly positive (fade signal)
- [ ] `compute_quotes` returns `(None, ask)` when `inventory == MAX_POSITION`
- [ ] `compute_quotes` returns `(bid, None)` when `inventory == -MAX_POSITION`
- [ ] `compute_quotes` shifts both quotes downward when inventory is long
- [ ] `should_requote` returns `True` when fair value shifts by more than `REQUOTE_THRESHOLD`
- [ ] `should_requote` returns `False` when fair value is stable
- [ ] Signal cap: AR signal of 0.10 is clamped to 0.05
- [ ] No orders are submitted when book is one-sided
- [ ] `round()` is applied to all submitted order prices
- [ ] `log_return_history` uses `appendleft` so index 0 is always the most recent return

---

## Quick Reference — Key Numbers

| Parameter | Value | Source |
|---|---|---|
| AR L1 coefficient | −0.549 | AR(5) fit, avg days −1/−2 |
| AR L2 coefficient | −0.317 | AR(5) fit |
| AR L3 coefficient | −0.174 | AR(5) fit |
| AR L4 coefficient | −0.093 | AR(5) fit |
| AR L5 coefficient | −0.043 | AR(5) fit |
| Hurst exponent | 0.389 | R/S analysis |
| VR at k=2 | 0.580 | Lo-MacKinlay VR test |
| Mid-price std dev | 19.75 | Raw data |
| Natural spread (approx.) | ~9 pts | Best bid/ask observation |
| L1 volume range | 2–12 | Raw data |

---

*Strategy specification v1.0 — based on Round 0 tutorial data (days −1 and −2). Validate AR coefficients and spread calibration on each new round before deploying unchanged.*
