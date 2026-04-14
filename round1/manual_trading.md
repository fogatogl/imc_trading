# Round 1 Manual Trading — "An Intarian Welcome"

## Overview

Two one-shot sealed auctions: **Dryland Flax** and **Ember Mushroom**.
You submit a single limit order (price + quantity) for each. Orders submitted last — last in time priority at any price level you join.

### Auction mechanics

1. A single **clearing price** is computed from the full order book (including your order).
2. Clearing price = price that **maximises total traded volume**; ties broken by **higher price**.
3. All bids ≥ clearing price fill at the clearing price. All asks ≤ clearing price fill at the clearing price.
4. Allocation: price priority → time priority. You are last at any level you join.

### Guaranteed buyback (post-auction)

| Product | Buyback | Fee |
|---------|---------|-----|
| `DRYLAND_FLAX` | 30 XIRECs/unit | none |
| `EMBER_MUSHROOM` | 20 XIRECs/unit | 0.05 buy + 0.05 sell = **0.10/unit** |

Net profit per unit = `buyback − clearing_price − fee`.

---

## Dryland Flax

### Stale order book

**Bids (buy orders already in book)**

| Volume | Price |
|--------|-------|
| 30k    | 30    |
| 5k     | 29    |
| 12k    | 28    |
| 28k    | 27    |

**Asks (sell orders already in book)**

| Price | Volume |
|-------|--------|
| 28    | 40k    |
| 31    | 20k    |
| 32    | 20k    |
| 33    | 30k    |

### Clearing price without your order

Cumulative asks ≤ P: only 40k exists at P ≤ 30 (the 31/32/33 asks don't affect lower prices).

| Price | Bids ≥ P | Asks ≤ P | Volume |
|-------|----------|----------|--------|
| 27    | 75k      | 0        | 0      |
| 28    | 47k      | 40k      | **40k** |
| 29    | 35k      | 40k      | 35k    |
| 30    | 30k      | 40k      | 30k    |

Baseline clearing = **28** (max volume 40k, unique).

### Profit analysis

**Key insight**: supply is capped at 40k (only 40k asks at ≤ 30). Your bid affects the clearing price through the tie-breaking rule (ties → higher price).

| Your bid | vol@28 | vol@29 | vol@30 | Clearing | Your fills | Profit/unit | Total |
|----------|--------|--------|--------|----------|------------|-------------|-------|
| V < 5k @30 | 40k | <40k | <40k | 28 | V (behind 47k existing) | 2 | 2V |
| V = 4,999 @30 | 40k | <40k | <40k | 28 | 4,999 | 2 | **9,998** |
| 5k ≤ V < 10k @30 | 40k | 40k | <40k | 29 | V | 1 | V |
| V = **9,999** @30 | 40k | 40k | 39,999 | **29** | **9,999** | **1** | **9,999** |
| V ≥ 10k @30 | 40k | 40k | 40k | 30 | ≤ 10k | 0 | 0 |

At V = 9,999 @30, clearing becomes 29 (ties at 40k volume for prices 28 and 29; tie-break picks 29).
Fill order at clearing 29: 30k existing@30 → **9,999 mine@30** → 5k existing@29. Supply = 40k.
After 30k existing: 10k left → I get 9,999 fills ✓.

### Optimal order — Dryland Flax

> **BUY 9,999 units at price 30**

Expected clearing: 29. Profit = 9,999 × (30 − 29) = **9,999 XIRECs**.

---

## Ember Mushroom

### Stale order book

**Bids**

| Volume | Price |
|--------|-------|
| 43k    | 20    |
| 17k    | 19    |
| 6k     | 18    |
| 5k     | 17    |
| 10k    | 16    |
| 5k     | 15    |
| 10k    | 14    |
| 7k     | 13    |

**Asks**

| Price | Volume |
|-------|--------|
| 12    | 20k    |
| 13    | 25k    |
| 14    | 35k    |
| 15    | 6k     |
| 16    | 5k     |
| 17    | 0      |
| 18    | 10k    |
| 19    | 12k    |

### Clearing price without your order

Cumulative asks ≤ P: 12k / 37k / 72k / 78k / 83k / 83k / 93k / 105k at prices 12–19.

| Price | Bids ≥ P | Asks ≤ P | Volume |
|-------|----------|----------|--------|
| 12    | 103k     | 12k      | 12k    |
| 13    | 103k     | 37k      | 37k    |
| 14    | 96k      | 72k      | 72k    |
| 15    | 86k      | 78k      | 78k    |
| **16**| **81k**  | **83k**  | **81k** ← max |
| 17    | 71k      | 83k      | 71k    |
| 18    | 66k      | 93k      | 66k    |
| 19    | 60k      | 105k     | 60k    |

Baseline clearing = **16** (max volume 81k, unique).

### Profit per unit by clearing price

| Clearing | Buyback − clearing − fee | Profitable? |
|----------|--------------------------|-------------|
| 16 | 20 − 16 − 0.10 = **3.90** | ✓ |
| 17 | 20 − 17 − 0.10 = **2.90** | ✓ |
| 18 | 20 − 18 − 0.10 = **1.90** | ✓ |
| 19 | 20 − 19 − 0.10 = **0.90** | ✓ |
| 20 | 20 − 20 − 0.10 = **−0.10** | ✗ loss |

### Strategy: push clearing to 18 for maximum volume × margin

Your bid at price 20 gets inserted behind the existing 43k@20 (time priority) but ahead of all @19 and @18 bids (price priority). Adding volume V@20 raises the bid-side totals and shifts the maximum-volume price upward.

Volume table with V added @20:

| Price | Bids ≥ P (with V@20) | Asks ≤ P | Vol | Condition |
|-------|----------------------|----------|-----|-----------|
| 16    | 81k+V               | 83k      | min(81k+V, 83k) | capped at 83k for V≥2k |
| 17    | 71k+V               | 83k      | min(71k+V, 83k) | capped at 83k for V≥12k |
| **18**| **66k+V**           | **93k**  | min(66k+V, 93k) | **capped at 93k for V≥27k** |
| 19    | 60k+V               | 105k     | min(60k+V, 105k) | capped for V≥45k |

For clearing to be 18 (vol@18 strictly > vol@19):
- Need `min(66k+V, 93k) > min(60k+V, 105k)`
- For V ≥ 27k: vol@18 = 93k. vol@19 = 60k+V. Requires 60k+V < 93k → **V < 33k**.

**Optimal V**: maximise fills while keeping V < 33k.

At V = **32,999** @20, clearing = 18:
- Supply ≤ 18 = 93k. Demand ≥ 18 = 43k + 32,999 + 17k + 6k = 98,999 > 93k (supply-constrained).
- Fill order: 43k existing@20 → **32,999 mine@20** → 17k existing@19 → 6k existing@18.
  - After 43k: 50k left → all 32,999 fill → 17,001 left → 17k@19 fill → 1 left → 1 unit @18.
- I get **32,999 fills at clearing price 18**. ✓

Verification that clearing = 18:
- vol@18 = min(98,999, 93,000) = **93,000**
- vol@19 = min(92,999, 105,000) = **92,999**
- 93,000 > 92,999 → clearing = 18 ✓

At V = 33,000: vol@18 = vol@19 = 93,000 → tie → clearing = 19 → profit drops to 33,000 × 0.90 = 29,700. Do not cross this threshold.

### Optimal order — Ember Mushroom

> **BUY 32,999 units at price 20**

Expected clearing: 18. Profit = 32,999 × (20 − 18 − 0.10) = 32,999 × 1.90 = **62,698 XIRECs**.

---

## Combined strategy summary

| Product | Order | Clearing | Fills | Profit |
|---------|-------|----------|-------|--------|
| Dryland Flax | BUY 9,999 @ 30 | 29 | 9,999 | 9,999 XIRECs |
| Ember Mushroom | BUY 32,999 @ 20 | 18 | 32,999 | 62,698 XIRECs |
| **Total** | | | | **~72,697 XIRECs** |

---

## Risk notes

- These order books are **stale**. The clearing price depends on your exact order plus whatever the live book looks like at submission time. The analysis above assumes no book changes.
- The critical thresholds are **V < 10k for DRYLAND_FLAX** (else clearing jumps to 30, zero profit) and **V < 33k for EMBER_MUSHROOM** (else clearing jumps to 19, profit collapses to 0.90/unit).
- You can re-submit orders until the round ends. Watch for updated book snapshots and recalculate if the book changes significantly.
- EMBER_MUSHROOM: if the existing 43k@20 bids are NOT fully present at auction time, your priority improves but the clearing price analysis may shift. Re-verify vol@18 vs vol@19 with the live book.


Auctions are exciting, aren't they? A rare moment where everything pauses, everyone commits, and the outcome waits patiently for the final input. I have always liked that about them. They reward preparation, not speed.

In this exchange auction, you place your final orders after everyone else. That means the entire order book is already fixed in place. From that point on, your orders are no longer reacting to the market. They are actively shaping how the auction settles. Realizing that your input affects the auction clearing price is a good start.

The more important step is understanding how it affects that price. The auction is designed to prioritize maximum trade volume first, and only then price. Every order you submit nudges the system toward a specific clearing point, whether you intend it to or not.

This is where simulation becomes useful. By testing different order sizes and price levels, you can see how the clearing price shifts. I used to do that myself, long before anyone called it elegant. On a machine with 16 megabytes of memory. I can still smell the circuit board slowly heating up under the strain of its calculations. Took hours, but the patterns were there if you waited long enough.

When all of that knowledge comes together, the goal becomes clear. One carefully considered order per product. Placed with intent. Enough to guide the auction toward the outcome you want.
