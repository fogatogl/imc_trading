# Round 0 — Final Trading Strategy
## IMC Prosperity 4 | Products: EMERALDS + TOMATOES

---

## Overview

Round 0 contains two products with fundamentally different price dynamics that call for two fundamentally different strategies. They share no correlation and should be managed with completely independent logic, state, and position limits.

| Product | Price behaviour | Strategy family | Primary edge |
|---|---|---|---|
| EMERALDS | Constant fair value = 10,000 | Pure market making + opportunistic taking | Spread capture around a known anchor |
| TOMATOES | I(1) levels, mean-reverting returns (H≈0.39) | AR-adjusted asymmetric market making | AR(5) signal + spread capture |

Both strategies run inside a single `Trader.run()` method. They do not interact.

---

## File Structure

```
trader.py
strategy/
  params.py          ← all tunable parameters for both products
  emeralds.py        ← EMERALDS logic (taker scan + maker quoting + liquidation)
  ar_signal.py       ← AR(5) signal for TOMATOES
  tomatoes.py        ← TOMATOES quoting logic
  inventory.py       ← shared inventory helpers (skew, suppression, requote check)
```

---

## Parameters

```python
# strategy/params.py

# ── EMERALDS ──────────────────────────────────────────────────────────────────
EME_PRODUCT        = "EMERALDS"
EME_FAIR_VALUE     = 10_000          # constant, never changes
EME_MAKER_OFFSET   = 1               # place maker bids/asks 1 pt better than best market maker
EME_ORDER_SIZE     = 10              # units per maker quote
EME_TAKER_SIZE     = None            # None = take full available volume at favorable prices
EME_MAX_POSITION   = 50             # hard inventory limit
EME_LIQUIDATION_THRESHOLD = 30      # net position beyond which partial liquidation triggers
# Liquidation is done at fair value (10,000) — aggressive cross to reduce exposure

# ── TOMATOES ──────────────────────────────────────────────────────────────────
TOM_PRODUCT        = "TOMATOES"
TOM_AR_COEFS       = [-0.549, -0.317, -0.174, -0.093, -0.043]  # [L1..L5], avg days -1/-2
TOM_HALF_SPREAD    = 4.5             # points — half the quoted bid-ask width
TOM_SKEW_PER_UNIT  = 0.2            # points of quote shift per unit of net inventory
TOM_MAX_POSITION   = 20             # hard inventory limit
TOM_ORDER_SIZE     = 5              # units per quote
TOM_REQUOTE_THRESH = 2.0            # cancel resting orders if fair value shifts > this
TOM_WARMUP_TICKS   = 10             # ticks before AR signal is trusted
TOM_SIGNAL_CAP     = 0.05           # max AR signal magnitude (guard against data artefacts)
```

---

# PRODUCT 1: EMERALDS

## Economic Description

The EMERALDS fair value is fixed and public knowledge: **10,000 Xirecs**. It never moves. This creates a perfectly predictable two-sided market:

- **Takers** are participants who need to transact immediately. They cross the spread: they buy at prices above 10,000 or sell at prices below 10,000 — accepting a worse price in exchange for immediacy.
- **Makers** queue patiently below 10,000 (to buy) and above 10,000 (to sell), waiting for a taker to hit their order and collecting the spread as profit.

Because the fair value is known with certainty, there is **zero adverse selection risk** on EMERALDS. Any fill at a price different from 10,000 is guaranteed PnL — the position can always be unwound at 10,000.

---

## EMERALDS Strategy — Three Layers

### Layer 1 — Taker scan (highest priority, execute first)

Every tick, before placing any maker orders, scan the live order book for immediately profitable fills:

```
For every ask price p_ask in the order book:
    if p_ask < EME_FAIR_VALUE (10,000):
        BUY the full available volume at p_ask  ← guaranteed profit of (10,000 - p_ask) per unit

For every bid price p_bid in the order book:
    if p_bid > EME_FAIR_VALUE (10,000):
        SELL the full available volume at p_bid  ← guaranteed profit of (p_bid - 10,000) per unit
```

**Constraints on taker orders:**
- Do not take if the resulting position would breach `EME_MAX_POSITION` in either direction.
- If only a partial fill is possible within the position limit, take only the portion that stays within limits.
- Process the most profitable prices first (furthest from 10,000).

**Why full volume?** There is no adverse selection on EMERALDS. Every unit bought below 10,000 or sold above 10,000 is a riskless profit locked in at fill time. Leaving volume on the table is leaving guaranteed PnL behind.

---

### Layer 2 — Maker quoting (passive, queue after taker scan)

After taking all immediately profitable volume, place passive maker quotes to capture the spread when takers arrive in future ticks.

**Quote placement rule:**

```
best_maker_bid = max bid price in order book that is STRICTLY BELOW 10,000
best_maker_ask = min ask price in order book that is STRICTLY ABOVE 10,000

our_bid = best_maker_bid + EME_MAKER_OFFSET   (must still be < 10,000)
our_ask = best_maker_ask - EME_MAKER_OFFSET   (must still be > 10,000)
```

If there are no existing maker bids below 10,000, default to `our_bid = 9,999`.
If there are no existing maker asks above 10,000, default to `our_ask = 10,001`.

**Why one point better than the market?** To sit at the front of the queue. When a taker arrives, the best-priced resting order is filled first. Quoting one point better than the existing market makers ensures priority without sacrificing meaningful spread.

**Order size:** `EME_ORDER_SIZE` units on each side. Do not post a bid if `position >= EME_MAX_POSITION`. Do not post an ask if `position <= -EME_MAX_POSITION`.

**Example:**

| Market best maker bid | Market best maker ask | Our bid | Our ask |
|---|---|---|---|
| 9,997 | 10,003 | 9,998 | 10,002 |
| 9,999 | 10,001 | 9,999* | 10,001* |
| (none) | (none) | 9,999 | 10,001 |

*When market makers are already at 9,999/10,001, match them (do not cross to 10,000).

---

### Layer 3 — Inventory liquidation (triggered when position is too large)

If the net position exceeds `EME_LIQUIDATION_THRESHOLD` in either direction, partially reduce it by crossing to fair value:

```
if position > +EME_LIQUIDATION_THRESHOLD:
    SELL (position - EME_LIQUIDATION_THRESHOLD) units AT 10,000
    ← willing to sell at fair value to reduce exposure

if position < -EME_LIQUIDATION_THRESHOLD:
    BUY  (|position| - EME_LIQUIDATION_THRESHOLD) units AT 10,000
    ← willing to buy at fair value to reduce exposure
```

**Why 10,000 and not better?** The goal is to offload the excess inventory immediately. Placing a limit order to sell at 10,001 might not fill if no taker arrives. At 10,000 we are acting as a taker ourselves — the fill is reliable. We do not lose money selling at 10,000 because we originally bought below 10,000 (Layer 1) or at 9,999 (Layer 2).

**Liquidation is partial:** We reduce to `EME_LIQUIDATION_THRESHOLD`, not to zero. This preserves some inventory to continue quoting as a maker. Full liquidation to zero would require re-entering the queue from scratch.

---

## EMERALDS — Execution Order Per Tick

```
1. Read order book for EMERALDS
2. TAKER SCAN
   └── Buy all asks < 10,000 (subject to position limit)
   └── Sell all bids > 10,000 (subject to position limit)
3. LIQUIDATION CHECK
   └── If |position| > EME_LIQUIDATION_THRESHOLD → cross at 10,000 to reduce
4. MAKER QUOTING
   └── Place bid at best_maker_bid + 1 (if < 10,000 and position < MAX)
   └── Place ask at best_maker_ask - 1 (if > 10,000 and position > -MAX)
```

---

## EMERALDS — Module Spec (`strategy/emeralds.py`)

```python
def scan_taker_orders(
    order_depth,          # IMC OrderDepth object
    position: int,
    max_position: int,
    fair_value: int = 10_000,
) -> list[Order]:
    """
    Returns a list of Orders to immediately take all profitable volume.

    Buy logic: iterate sell_orders (asks) sorted ascending by price.
               For each ask < fair_value, create a BUY order for min(available_vol, room_to_max).
               Stop if position would reach max_position.

    Sell logic: iterate buy_orders (bids) sorted descending by price.
                For each bid > fair_value, create a SELL order for min(available_vol, room_to_min).
                Stop if position would reach -max_position.

    Returns: list of Order objects (may be empty).
    """

def compute_maker_quotes(
    order_depth,
    position: int,
    max_position: int,
    fair_value: int      = 10_000,
    maker_offset: int    = 1,
    order_size: int      = 10,
) -> list[Order]:
    """
    Returns up to 2 Orders: one passive bid, one passive ask.

    bid_price = max(bid for bid in buy_orders if bid < fair_value) + maker_offset
                clamped to fair_value - 1 as an upper bound
                default 9,999 if no existing maker bids found

    ask_price = min(ask for ask in sell_orders if ask > fair_value) - maker_offset
                clamped to fair_value + 1 as a lower bound
                default 10,001 if no existing maker asks found

    Suppress bid if position >= max_position.
    Suppress ask if position <= -max_position.

    Returns: list of Order objects (0, 1, or 2 orders).
    """

def compute_liquidation_orders(
    position: int,
    liquidation_threshold: int,
    fair_value: int = 10_000,
) -> list[Order]:
    """
    Returns liquidation orders if |position| > liquidation_threshold.

    if position > +threshold: SELL (position - threshold) @ fair_value
    if position < -threshold: BUY  (|position| - threshold) @ fair_value
    else: return []

    These are aggressive orders at fair value — they will cross the spread
    and fill against any resting bid or ask at 10,000.
    """
```

---

# PRODUCT 2: TOMATOES

## Economic Description

TOMATOES has no fixed fair value. Its price is an I(1) process (non-stationary levels, stationary returns) with strongly mean-reverting returns (H≈0.39). The AR(5) model captures this structure with all-negative coefficients and white-noise residuals (DW≈2.00). Roughly 43% of each tick's move is expected to reverse on the immediately following tick.

The strategy is an **AR(5)-adjusted asymmetric market maker**: quotes are placed around a signal-adjusted fair value rather than the raw mid-price, and both quotes are continuously skewed based on net inventory.

Full statistical justification is in `tomato_statistical_analysis.md`.

---

## TOMATOES Strategy

### Signal computation

Every tick, compute the AR(5) predicted next log return:

```
signal_t = Σ AR_COEFS[i] × log_return_history[i]   for i in 0..4

           = −0.549·r_{t−1}  −0.317·r_{t−2}  −0.174·r_{t−3}  −0.093·r_{t−4}  −0.043·r_{t−5}
```

Cap: `signal_t = clip(signal_t, −TOM_SIGNAL_CAP, +TOM_SIGNAL_CAP)`

Use `signal_t = 0.0` for the first `TOM_WARMUP_TICKS` ticks.

### Fair value adjustment

```
fair_value_t = mid_t × (1 + signal_t)
```

This shifts the quoting centre toward the predicted next price. When `signal_t < 0` (price expected to fall), both quotes move below mid — the ask is cheaper (easier to sell), the bid is cheaper (harder to buy). This is the natural short lean.

### Quote generation

```
inv_adj  = TOM_SKEW_PER_UNIT × position
bid      = fair_value_t − TOM_HALF_SPREAD − inv_adj
ask      = fair_value_t + TOM_HALF_SPREAD − inv_adj
```

Suppress bid if `position >= +TOM_MAX_POSITION`.
Suppress ask if `position <= −TOM_MAX_POSITION`.
Round all prices to nearest integer.

### Requoting (cancel stale orders)

If `|fair_value_t − fair_value_{t−1}| > TOM_REQUOTE_THRESH`, cancel all resting TOMATOES orders before placing new ones. Stale resting orders are the primary source of adverse selection — the AR signal updates every tick so quotes older than one tick can be informationally stale.

---

## TOMATOES — Execution Order Per Tick

```
1. Read order book; compute mid_price
2. Compute log_return from prev_mid → update return history (deque, maxlen=5)
3. Compute AR(5) signal (0.0 during warmup)
4. Compute fair_value = mid × (1 + signal)
5. Check requote condition → cancel stale orders if triggered
6. Compute bid/ask with inventory skew
7. Apply hard position limits (suppress one side if at max)
8. Submit orders
```

---

## TOMATOES — Module Spec (`strategy/tomatoes.py`)

```python
def compute_log_return(prev_mid: float, curr_mid: float) -> float:
    """Returns log(curr_mid / prev_mid)."""

def compute_ar_signal(
    return_history: list[float],   # index 0 = most recent
    coefs: list[float],
    signal_cap: float,
) -> float:
    """
    Returns clipped AR(5) predicted next log return.
    Returns 0.0 if len(return_history) < len(coefs).
    """

def compute_fair_value(mid: float, signal: float) -> float:
    """Returns mid * (1 + signal)."""

def compute_quotes(
    fair_value:    float,
    position:      int,
    half_spread:   float,
    skew_per_unit: float,
    max_position:  int,
    order_size:    int,
) -> list[Order]:
    """
    Returns 0, 1, or 2 Order objects.

    inv_adj = skew_per_unit * position
    bid_px  = round(fair_value - half_spread - inv_adj)
    ask_px  = round(fair_value + half_spread - inv_adj)

    Suppress bid if position >= +max_position.
    Suppress ask if position <= -max_position.
    """

def should_requote(prev_fv: float, curr_fv: float, threshold: float) -> bool:
    """Returns True if |curr_fv - prev_fv| > threshold."""
```

---

## Shared State Objects

```python
# strategy/inventory.py

from dataclasses import dataclass, field
from collections import deque

@dataclass
class EmeraldsState:
    position: int = 0

@dataclass
class TomatoesState:
    log_return_history: deque = field(default_factory=lambda: deque(maxlen=5))
    prev_mid:           float | None = None
    prev_fair_value:    float | None = None
    tick_count:         int = 0
```

---

# Combined `trader.py`

```python
from imc_framework import TradingState, Order
from strategy.params  import *
from strategy.emeralds import scan_taker_orders, compute_maker_quotes, compute_liquidation_orders
from strategy.tomatoes import (compute_log_return, compute_ar_signal,
                                compute_fair_value, compute_quotes, should_requote)
from strategy.inventory import EmeraldsState, TomatoesState

class Trader:

    def __init__(self):
        self.eme = EmeraldsState()
        self.tom = TomatoesState()

    def run(self, state: TradingState) -> dict[str, list[Order]]:
        orders = {}

        # ── EMERALDS ──────────────────────────────────────────────────────────
        if EME_PRODUCT in state.order_depths:
            depth    = state.order_depths[EME_PRODUCT]
            position = state.position.get(EME_PRODUCT, 0)
            eme_orders = []

            # Layer 1: take all immediately profitable volume
            eme_orders += scan_taker_orders(depth, position, EME_MAX_POSITION, EME_FAIR_VALUE)

            # Recompute position after taker fills (optimistic — adjust if framework differs)
            simulated_pos = position + sum(o.quantity for o in eme_orders)

            # Layer 3: liquidate if oversized (before placing new maker orders)
            eme_orders += compute_liquidation_orders(
                simulated_pos, EME_LIQUIDATION_THRESHOLD, EME_FAIR_VALUE
            )
            simulated_pos = position + sum(o.quantity for o in eme_orders)

            # Layer 2: passive maker quotes
            eme_orders += compute_maker_quotes(
                depth, simulated_pos, EME_MAX_POSITION,
                EME_FAIR_VALUE, EME_MAKER_OFFSET, EME_ORDER_SIZE
            )

            if eme_orders:
                orders[EME_PRODUCT] = eme_orders

        # ── TOMATOES ──────────────────────────────────────────────────────────
        if TOM_PRODUCT in state.order_depths:
            depth    = state.order_depths[TOM_PRODUCT]
            position = state.position.get(TOM_PRODUCT, 0)
            s        = self.tom

            best_bid = max(depth.buy_orders.keys(),  default=None)
            best_ask = min(depth.sell_orders.keys(), default=None)

            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2.0

                # Update return history
                if s.prev_mid is not None:
                    lr = compute_log_return(s.prev_mid, mid)
                    s.log_return_history.appendleft(lr)
                s.prev_mid    = mid
                s.tick_count += 1

                # AR(5) signal
                if s.tick_count < TOM_WARMUP_TICKS:
                    signal = 0.0
                else:
                    signal = compute_ar_signal(
                        list(s.log_return_history), TOM_AR_COEFS, TOM_SIGNAL_CAP
                    )

                fair_value = compute_fair_value(mid, signal)

                # Cancel stale orders
                if s.prev_fair_value is not None and should_requote(
                    s.prev_fair_value, fair_value, TOM_REQUOTE_THRESH
                ):
                    pass  # cancel logic per IMC framework (submit 0-vol or omit resting)

                s.prev_fair_value = fair_value

                # Place new quotes
                tom_orders = compute_quotes(
                    fair_value, position,
                    TOM_HALF_SPREAD, TOM_SKEW_PER_UNIT,
                    TOM_MAX_POSITION, TOM_ORDER_SIZE
                )
                if tom_orders:
                    orders[TOM_PRODUCT] = tom_orders

        return orders
```

---

# Strategy Comparison at a Glance

| Dimension | EMERALDS | TOMATOES |
|---|---|---|
| Fair value source | Known constant (10,000) | AR(5) signal from price history |
| Adverse selection risk | Zero | Low (mean-reverting — takers lose on average) |
| Taker behaviour | Yes — aggressively take sub-10k asks and super-10k bids | No — passive maker only |
| Maker offset method | 1 pt better than best market maker | AR-adjusted fair value ± half-spread |
| Inventory skew | Liquidation at fair value beyond threshold | Continuous quote skew proportional to position |
| Drift component | None (fair value fixed) | None (intercept = 0, drift contradictory across days) |
| Position limit | ±50 (wider — zero adverse selection) | ±20 (tighter — price uncertainty exists) |
| Primary PnL source | Spread capture + opportunistic taker fills | Spread capture + AR signal lean |

---

# Parameter Tuning Guide

## EMERALDS

**`EME_MAKER_OFFSET` (default: 1)**
- Increase to 2 if the queue is too crowded at ±1 and fills are rare.
- Keep at 1 as long as fill rate is healthy — every extra point sacrificed is guaranteed PnL per fill.

**`EME_ORDER_SIZE` (default: 10)**
- Increase if L1 volume allows it without dominating the book.
- Decrease if inventory swings become too large before liquidation triggers.

**`EME_LIQUIDATION_THRESHOLD` (default: 30)**
- Lower this if you find yourself sitting at large positive/negative positions for extended periods.
- The PnL cost of liquidating at 10,000 is zero if you originally filled below/above 10,000.

**`EME_MAX_POSITION` (default: 50)**
- Hard safety limit. Rarely needs tuning — the liquidation threshold does the real work.

## TOMATOES

**`TOM_HALF_SPREAD` (default: 4.5)**
- The most sensitive parameter. Tighten by 0.5 pt at a time. Watch adverse selection.

**`TOM_SKEW_PER_UNIT` (default: 0.2)**
- Increase if inventory frequently hits the hard limit.
- Decrease if fill rate on the inventory-reducing side is too low.

**`TOM_MAX_POSITION` (default: 20)**
- Start conservative. Widen only after observing real intraday inventory swings.

**`TOM_AR_COEFS`**
- Do not retrain on Round 0 data alone. Retrain after accumulating Round 1–2 data.
- Always verify DW≈2.0 after retraining — if DW drifts, revise the AR lag order.

---

# Testing Checklist

### EMERALDS
- [ ] Taker scan buys ask at 9,995 → creates BUY order for full volume
- [ ] Taker scan sells bid at 10,005 → creates SELL order for full volume
- [ ] Taker scan does NOT buy ask at 10,000 (not strictly below fair value)
- [ ] Taker scan does NOT buy if `position >= EME_MAX_POSITION`
- [ ] Maker bid placed 1 pt above best existing maker bid, never at or above 10,000
- [ ] Maker ask placed 1 pt below best existing maker ask, never at or below 10,000
- [ ] Liquidation triggered at `position = +31` (threshold = 30): SELL 1 unit at 10,000
- [ ] No bid posted when `position >= EME_MAX_POSITION`
- [ ] No ask posted when `position <= -EME_MAX_POSITION`

### TOMATOES
- [ ] AR signal returns 0.0 during warmup (first 10 ticks)
- [ ] AR signal is negative when L1 return is strongly positive
- [ ] Signal is capped at ±0.05
- [ ] `log_return_history` index 0 is always the most recent return (appendleft)
- [ ] Both quotes shift downward when inventory is long
- [ ] Bid suppressed at `position == +MAX_POSITION`
- [ ] Ask suppressed at `position == -MAX_POSITION`
- [ ] `should_requote` returns True when fair value shifts > 2.0 pts
- [ ] All submitted prices are integers (round applied)
- [ ] No orders submitted when book is one-sided

### Integration
- [ ] EMERALDS and TOMATOES logic runs independently — state objects do not share fields
- [ ] Both products return orders in the same dict from `Trader.run()`
- [ ] A crash in one product's logic does not prevent the other from submitting orders
  (wrap each block in a try/except in production)

---

# Quick Reference

| Constant | Value |
|---|---|
| EMERALDS fair value | 10,000 Xirecs |
| TOMATOES AR L1 | −0.549 |
| TOMATOES AR L2 | −0.317 |
| TOMATOES AR L3 | −0.174 |
| TOMATOES AR L4 | −0.093 |
| TOMATOES AR L5 | −0.043 |
| TOMATOES Hurst exponent | 0.389 |
| TOMATOES VR(k=2) | 0.580 |
| TOMATOES mid-price std dev | 19.75 pts |
| TOMATOES natural spread | ~9 pts |

---

*Strategy specification v1.0 — Round 0, IMC Prosperity 4.
Validate parameters on each new round before deploying unchanged.*
