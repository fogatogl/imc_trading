# Round 0 — Final Trading Strategy v3
## IMC Prosperity 4 | Products: EMERALDS + TOMATOES

---

## What This Document Is

The MA strategy (PnL ~2400) outperforms the pure AR strategy (PnL ~1880).
This document upgrades the MA strategy by grafting the AR(5) signal onto it as a lean.
The MA framework stays intact. The AR signal sharpens entry thresholds and maker quotes.

---

## Bugs Fixed vs the MA implementation

| Bug | Fix |
|---|---|
| `conversions = 1` | Set `conversions = 0` — no conversion product in Round 0 |
| EMERALDS liquidation dumps full position + skips taker | Dump only excess over threshold; do not `continue` |
| EMERALDS taker iterates dict unordered | Sort asks ascending, bids descending before iterating |
| TOMATOES maker bid uses `min(best_bid+1, mva_fast-1)` — places bid below market when MAs converge | See corrected maker logic below |
| TOMATOES maker order size = full remaining cap | Use fixed `TOM_ORDER_SIZE = 10` per quote |

Position limit is confirmed **80 for both products**.

---

## Parameters

```python
# ── EMERALDS ──────────────────────────────────────────────────────────────────
EME_PRODUCT               = "EMERALDS"
EME_FAIR_VALUE            = 10_000
EME_POSITION_LIMIT        = 80
EME_LIQUIDATION_THRESHOLD = 60      # reduce to this level, do not dump full position
EME_MAKER_SIZE            = 10      # fixed units per passive quote

# ── TOMATOES ──────────────────────────────────────────────────────────────────
TOM_PRODUCT               = "TOMATOES"
TOM_POSITION_LIMIT        = 80
TOM_REBALANCE_THRESHOLD   = 50      # force rebalance toward mva_fast when |pos| > this
TOM_ORDER_SIZE            = 10      # fixed units per passive maker quote
TOM_WINDOW_LONG           = 40      # slow MA window
TOM_WINDOW_FAST           = 5       # fast MA window
# AR(5) parameters
TOM_AR_COEFS              = [-0.549, -0.317, -0.174, -0.093, -0.043]  # L1..L5
TOM_AR_WARMUP             = 10      # ticks before AR signal is used
TOM_SIGNAL_CAP            = 0.003   # max AR signal magnitude (small — lean, not dominate)
```

**Why `TOM_SIGNAL_CAP = 0.003` and not 0.05?**
At a tomato price of ~3000, a signal of 0.05 shifts the reference by 150 pts — larger than the
std_dev band. That would override the MA signal entirely, breaking what already works.
A cap of 0.003 shifts the reference by ~9 pts (about 1 std_dev unit), enough to lean the thresholds
meaningfully without clobbering the MA bands.

---

# PRODUCT 1: EMERALDS

Unchanged logic. Three layers. Fair value is fixed at 10,000.

## Execution order per tick

```
1. TAKER SCAN
   - Sort asks ascending; for each ask < 10,000: BUY min(volume, room_to_limit)
   - Sort bids descending; for each bid > 10,000: SELL min(volume, room_to_limit)
   - Track remaining buy/sell capacity as you go

2. LIQUIDATION CHECK  (uses capacity remaining after taker)
   - if current_pos > EME_LIQUIDATION_THRESHOLD:
       SELL (current_pos - EME_LIQUIDATION_THRESHOLD) @ 10,000
   - if current_pos < -EME_LIQUIDATION_THRESHOLD:
       BUY  (|current_pos| - EME_LIQUIDATION_THRESHOLD) @ 10,000
   - Do NOT skip the rest of the tick. Do NOT dump the full position.

3. MAKER QUOTES  (uses capacity remaining after taker)
   - best_maker_bid = max bid in book strictly below 10,000  (default: 9,999)
   - best_maker_ask = min ask in book strictly above 10,000  (default: 10,001)
   - our_bid = clamp(best_maker_bid + 1, max=9,999)
   - our_ask = clamp(best_maker_ask - 1, min=10,001)
   - POST BUY  EME_MAKER_SIZE @ our_bid   if remaining_buy_cap > 0
   - POST SELL EME_MAKER_SIZE @ our_ask   if remaining_sell_cap < 0
```

**Capacity tracking:**

```python
remaining_buy  = EME_POSITION_LIMIT - current_pos   # starts full each tick
remaining_sell = EME_POSITION_LIMIT + current_pos   # starts full each tick

# After each taker buy order of qty q:
remaining_buy -= q

# After each taker sell order of qty q:
remaining_sell -= q

# Maker quotes use EME_MAKER_SIZE, not the full remaining capacity
```

---

# PRODUCT 2: TOMATOES — MA strategy + AR lean

## Conceptual design

The MA strategy earns PnL from two sources:
1. **Mean reversion taker fills** — buy cheap (below `mva_long - σ`), sell expensive (above `mva_long + σ`)
2. **Spread capture** — passive maker quotes placed between market and `mva_fast`

The AR(5) model tells us the direction prices are statistically expected to move next tick.
We use it to **lean the thresholds asymmetrically**:

- When AR predicts a fall (`signal < 0`): shift reference down → sell threshold drops (sell sooner) + buy threshold drops (require more cheapness before buying)
- When AR predicts a rise (`signal > 0`): shift reference up → buy threshold rises (buy sooner) + sell threshold rises (require more expensiveness before selling)

The lean is small and additive — it does not replace the MA logic.

---

## State to persist in `traderData`

```python
memory["TOMATOES"] = {
    "price_history":  [],    # list of mid prices, max TOM_WINDOW_LONG entries
    "return_history": [],    # list of log returns, index 0 = most recent, max 5
    "prev_mid":       None,  # float or null
    "tick_count":     0      # int
}
```

---

## Signal computation

```
# Step 1: update price history
price_history.append(mid_price)
if len(price_history) > TOM_WINDOW_LONG:
    price_history.pop(0)

# Step 2: compute log return and update return history
if prev_mid is not None:
    lr = log(mid_price / prev_mid)
    return_history.insert(0, lr)       # index 0 = most recent
    return_history = return_history[:5]
prev_mid = mid_price
tick_count += 1

# Step 3: slow MA, fast MA, std_dev
mva_long = mean(price_history)         # requires len >= TOM_WINDOW_LONG
mva_fast = mean(price_history[-TOM_WINDOW_FAST:])
std_dev  = population_std(price_history, mva_long)

# Step 4: AR(5) signal
if tick_count < TOM_AR_WARMUP or len(return_history) < 5:
    ar_signal = 0.0
else:
    ar_signal = sum(TOM_AR_COEFS[i] * return_history[i] for i in range(5))
    ar_signal = clip(ar_signal, -TOM_SIGNAL_CAP, +TOM_SIGNAL_CAP)

# Step 5: AR-adjusted reference price
ar_ref = mva_long * (1.0 + ar_signal)
```

---

## Layer 1 — Taker scan (AR-adjusted thresholds)

```
buy_threshold  = ar_ref - std_dev
sell_threshold = ar_ref + std_dev

if best_ask < buy_threshold:
    vol = min(abs(sell_orders[best_ask]), TOM_POSITION_LIMIT - current_pos)
    if vol > 0:
        BUY vol @ best_ask
        current_pos += vol

if best_bid > sell_threshold:
    vol = min(buy_orders[best_bid], TOM_POSITION_LIMIT + current_pos)
    if vol > 0:
        SELL vol @ best_bid
        current_pos -= vol
```

---

## Layer 2 — Rebalance toward fast MA

```
if abs(current_pos) > TOM_REBALANCE_THRESHOLD:
    stabilization_price = round(mva_fast)
    SUBMIT Order @ stabilization_price for quantity -current_pos
    current_pos = 0
```

This is a limit order at `mva_fast`. It will fill when the market passes through that level.

---

## Layer 3 — Passive maker quotes (AR-adjusted, fixed size, corrected logic)

The maker bid must be:
- Above the existing best bid (to get queue priority)
- Below `ar_fast` (which is `mva_fast * (1 + ar_signal)`) — we never quote above our own reference

The maker ask must be:
- Below the existing best ask (to get queue priority)
- Above `ar_fast`

```
ar_fast = mva_fast * (1.0 + ar_signal)

# BID: one tick above best_bid, but do not exceed ar_fast - 1
maker_bid = best_bid + 1
if maker_bid >= ar_fast:         # would quote at or above reference — skip bid
    maker_bid = None             # suppress; do not place a bid this tick

# ASK: one tick below best_ask, but do not go below ar_fast + 1
maker_ask = best_ask - 1
if maker_ask <= ar_fast:         # would quote at or below reference — skip ask
    maker_ask = None             # suppress; do not place an ask this tick

if maker_bid is not None and (TOM_POSITION_LIMIT - current_pos) > 0:
    POST BUY  TOM_ORDER_SIZE @ int(maker_bid)

if maker_ask is not None and (TOM_POSITION_LIMIT + current_pos) > 0:
    POST SELL TOM_ORDER_SIZE @ int(maker_ask)
```

**Why this fixes the original bug:** The original `min(best_bid+1, mva_fast-1)` could produce a
bid *below* `best_bid` when `mva_fast - 1 < best_bid`. The new logic detects this situation
and suppresses the quote entirely, avoiding a useless low bid.

---

## TOMATOES — Execution order per tick

```
1. Read order book → best_bid, best_ask, mid_price
2. Skip if book is one-sided
3. Update price_history (append mid, trim to WINDOW_LONG)
4. Update return_history (insert log return at front, trim to 5)
5. Skip trading if len(price_history) < TOM_WINDOW_LONG  (warmup)
6. Compute mva_long, mva_fast, std_dev
7. Compute ar_signal and ar_ref = mva_long * (1 + ar_signal)
8. TAKER: buy if best_ask < ar_ref - std_dev
9. TAKER: sell if best_bid > ar_ref + std_dev
10. REBALANCE: if |current_pos| > TOM_REBALANCE_THRESHOLD → limit order at mva_fast
11. MAKER: compute ar_fast; place bid above best_bid if room below ar_fast;
           place ask below best_ask if room above ar_fast
```

---

# Complete `trader.py` Structure

Write the file in exactly this order. Everything in one flat file — no imports from sub-modules.

```
1. Imports
   import json, math
   from datamodel import OrderDepth, TradingState, Order
   from typing import List

2. Parameter constants (all caps, as listed above)

3. class Trader:
       def run(self, state: TradingState):
           conversions = 0                          ← always 0
           result = {}

           # Load memory
           try:
               memory = json.loads(state.traderData) if state.traderData else {}
           except Exception:
               memory = {}

           # Init memory slots if absent
           if "TOMATOES" not in memory:
               memory["TOMATOES"] = {
                   "price_history": [], "return_history": [],
                   "prev_mid": None, "tick_count": 0
               }

           # EMERALDS block (try/except)
           # TOMATOES block (try/except)

           # Save memory
           return result, conversions, json.dumps(memory)
```

Wrap each product block in `try/except Exception: pass` so a crash in one does not
prevent the other from submitting orders.

---

# Testing Checklist

### EMERALDS
- [ ] `conversions` is 0, not 1
- [ ] Taker buys asks in ascending price order
- [ ] Taker sells bids in descending price order
- [ ] Taker stops when remaining capacity reaches 0
- [ ] Liquidation fires at position = +61, sells exactly 1 unit at 10,000
- [ ] Liquidation does NOT `continue` — maker quotes still placed after liquidation
- [ ] Maker bid never placed at 10,000 or above
- [ ] Maker ask never placed at 10,000 or below
- [ ] Maker order size is EME_MAKER_SIZE (10), not the full remaining capacity

### TOMATOES — AR signal
- [ ] `ar_signal = 0.0` for first TOM_AR_WARMUP ticks
- [ ] `ar_signal` is clipped to ±TOM_SIGNAL_CAP (0.003)
- [ ] `return_history[0]` is always the most recent return
- [ ] `ar_ref` shifts below `mva_long` when signal is negative

### TOMATOES — taker
- [ ] Buys when `best_ask < ar_ref - std_dev`
- [ ] Does NOT buy when `best_ask >= ar_ref - std_dev`
- [ ] Position limit enforced (never exceeds ±80)

### TOMATOES — maker
- [ ] Maker bid is suppressed when `best_bid + 1 >= ar_fast`
- [ ] Maker ask is suppressed when `best_ask - 1 <= ar_fast`
- [ ] Maker order size is TOM_ORDER_SIZE (10), not remaining capacity
- [ ] All prices are integers (int() applied)

### Integration
- [ ] EMERALDS crash does not block TOMATOES orders
- [ ] `price_history` and `return_history` survive across ticks via traderData
- [ ] `tick_count` increments every tick even during warmup (no `continue` before it)

---

# Parameter Tuning Guide

| Parameter | Default | Raise if... | Lower if... |
|---|---|---|---|
| `TOM_SIGNAL_CAP` | 0.003 | AR lean has little effect on fills | AR lean overrides MA bands entirely |
| `TOM_WINDOW_LONG` | 40 | Price oscillates on a longer cycle | Mean reversion is faster |
| `TOM_WINDOW_FAST` | 5 | Fast MA too noisy, bad maker placement | Fast MA too slow, lags price |
| `TOM_REBALANCE_THRESHOLD` | 50 | Rebalance fires too often, disrupts maker | Inventory stuck at extremes too long |
| `TOM_ORDER_SIZE` | 10 | Fill rate too low, missing maker PnL | Single fills pushing position to limit |
| `EME_LIQUIDATION_THRESHOLD` | 60 | Inventory recovers naturally without help | Sitting at large position for many ticks |

---

*Strategy specification v3.0 — Round 0, IMC Prosperity 4.*
*MA framework by design. AR(5) lean additive. Validate on backtester before deploying.*
