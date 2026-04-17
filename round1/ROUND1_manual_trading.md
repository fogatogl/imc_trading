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

Cumulative asks ≤ P: 20k / 45k / 80k / 86k / 91k / 91k / 101k / 113k at prices 12–19.

| Price | Bids ≥ P | Asks ≤ P | Volume |
|-------|----------|----------|--------|
| 12    | 103k     | 20k      | 20k    |
| 13    | 103k     | 45k      | 45k    |
| 14    | 96k      | 80k      | 80k    |
| **15**| **86k**  | **86k**  | **86k** ← max |
| 16    | 81k      | 91k      | 81k    |
| 17    | 71k      | 91k      | 71k    |
| 18    | 66k      | 101k     | 66k    |
| 19    | 60k      | 113k     | 60k    |

Baseline clearing = **15** (max volume 86k, unique — demand equals supply exactly).

### Profit per unit by clearing price

| Clearing | Buyback − clearing − fee | Profitable? |
|----------|--------------------------|-------------|
| 15 | 20 − 15 − 0.10 = **4.90** | ✓ |
| 16 | 20 − 16 − 0.10 = **3.90** | ✓ |
| 17 | 20 − 17 − 0.10 = **2.90** | ✓ |
| 18 | 20 − 18 − 0.10 = **1.90** | ✓ |
| 19 | 20 − 19 − 0.10 = **0.90** | ✓ |
| 20 | 20 − 20 − 0.10 = **−0.10** | ✗ loss |

### Strategy: push clearing to 16 for maximum volume × margin

Baseline clearing is 15 — vol@15 = 86k because demand (86k) equals supply (86k) exactly. Adding any bid V@20 inflates bids≥P for all P ≤ 20, but vol@15 stays capped at 86k (supply side fixed). Meanwhile vol@16 grows, overtaking vol@15 and making 16 the new clearing price.

Volume table with V added @20:

| Price | Bids ≥ P (with V@20) | Asks ≤ P | Vol |
|-------|----------------------|----------|-----|
| 15    | 86k+V               | 86k      | **86k** (supply-capped, never grows) |
| **16**| **81k+V**           | **91k**  | min(81k+V, 91k) |
| 17    | 71k+V               | 91k      | min(71k+V, 91k) |
| 18    | 66k+V               | 101k     | min(66k+V, 101k) |
| 19    | 60k+V               | 113k     | min(60k+V, 113k) |

For clearing to be 16 (vol@16 strictly > vol@15 = 86k AND vol@16 > vol@17):
- vol@16 > 86k: 81k+V > 86k → **V ≥ 5k**
- vol@16 > vol@17: min(81k+V, 91k) > min(71k+V, 91k). Both cap at 91k for V ≥ 10k → tie → clearing = 17. So **V < 20k**.

Clearing = 16 for **5k ≤ V < 20k**.

At V = **19,999** @20, clearing = 16:
- Supply ≤ 16 = 91k. Demand ≥ 16 = 81k+19,999 = 100,999 > 91k (supply-constrained).
- Fill order: 43k existing@20 → **19,999 mine@20** → 17k@19 → 6k@18 → 5k@17 → 1k@16.
  - After 43k: 48k left → all 19,999 fill ✓.

Verification:
- vol@16 = min(100,999, 91,000) = **91,000**
- vol@15 = 86,000 < 91,000 ✓
- vol@17 = min(90,999, 91,000) = **90,999** < 91,000 ✓ — unique max → clearing = 16 ✓

At V = 20,000: vol@16 = vol@17 = 91,000 → tie → clearing = 17 → profit drops to 20,000 × 2.90 = 58,000. Do not cross this threshold.

Full comparison across all target clearings:

| Target clearing | V range | Max V | Profit/unit | Total |
|----------------|---------|-------|-------------|-------|
| 15 | V < 5k | 4,999 | 4.90 | 24,495 |
| **16** | 5k ≤ V < 20k | **19,999** | **3.90** | **77,996 ← optimal** |
| 17 | 20k ≤ V < 25k | 24,999 | 2.90 | 72,497 |
| 18 | 25k ≤ V < 41k | 40,999 | 1.90 | 77,898 |
| 19 | 41k ≤ V < 70k | 69,999 | 0.90 | 62,999 |

### Optimal order — Ember Mushroom

> **BUY 19,999 units at price 20**

Expected clearing: 16. Profit = 19,999 × (20 − 16 − 0.10) = 19,999 × 3.90 = **77,996 XIRECs**.

---

## Combined strategy summary

| Product | Order | Clearing | Fills | Profit |
|---------|-------|----------|-------|--------|
| Dryland Flax | BUY 9,999 @ 30 | 29 | 9,999 | 9,999 XIRECs |
| Ember Mushroom | BUY 19,999 @ 20 | 16 | 19,999 | 77,996 XIRECs |
| **Total** | | | | **~87,995 XIRECs** |

---

## Risk notes

- These order books are **stale**. The clearing price depends on your exact order plus whatever the live book looks like at submission time. The analysis above assumes no book changes.
- The critical thresholds are **V < 10k for DRYLAND_FLAX** (else clearing jumps to 30, zero profit) and **V < 20k for EMBER_MUSHROOM** (else clearing jumps to 17, profit collapses to 2.90/unit and total drops to ~72k).
- You can re-submit orders until the round ends. Watch for updated book snapshots and recalculate if the book changes significantly.
- EMBER_MUSHROOM: if the existing 43k@20 bids are NOT fully present at auction time, your priority improves but the clearing price analysis may shift. Re-verify vol@16 vs vol@17 with the live book. Also re-verify vol@15 (supply = asks ≤ 15); if it changes, the baseline clearing shifts.


Auctions are exciting, aren't they? A rare moment where everything pauses, everyone commits, and the outcome waits patiently for the final input. I have always liked that about them. They reward preparation, not speed.

In this exchange auction, you place your final orders after everyone else. That means the entire order book is already fixed in place. From that point on, your orders are no longer reacting to the market. They are actively shaping how the auction settles. Realizing that your input affects the auction clearing price is a good start.

The more important step is understanding how it affects that price. The auction is designed to prioritize maximum trade volume first, and only then price. Every order you submit nudges the system toward a specific clearing point, whether you intend it to or not.

This is where simulation becomes useful. By testing different order sizes and price levels, you can see how the clearing price shifts. I used to do that myself, long before anyone called it elegant. On a machine with 16 megabytes of memory. I can still smell the circuit board slowly heating up under the strain of its calculations. Took hours, but the patterns were there if you waited long enough.

When all of that knowledge comes together, the goal becomes clear. One carefully considered order per product. Placed with intent. Enough to guide the auction toward the outcome you want.
