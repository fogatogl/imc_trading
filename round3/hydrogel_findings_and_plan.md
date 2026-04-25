# HYDROGEL_PACK — Round 3 Statistical Findings & Strategy Plan

**Companion to** [`round3_findings.md`](round3_findings.md) (which covered VE / vouchers and explicitly deferred hydrogel).
**Data:** `dataset/ROUND_3/prices_round_3_day_{0,1,2}.csv` + `trades_round_3_day_{0,1,2}.csv`
**Position limit:** 200. **Mid range over 3 days:** [9891, 10079]. **Tick = 1 SeaShell.**

---

## 1. Statistical results

### 1.1 Spread regime

| Spread (ask₁ − bid₁) | Count over 30 000 ticks | Share |
|---:|---:|---:|
| 7 | 275 | 0.9% |
| 8 | 490 | 1.6% |
| 9 | 225 | 0.8% |
| **15–16 (typical)** | 28 618 | **95.4%** |
| 17 | 392 | 1.3% |

- Median spread = **16**. Mean = 15.73.
- Tight regime (≤9) lasts a median of **1 tick**; wide-regime runs are 21 ticks median, max 243.
- Order book has 2 levels populated 98.3% of ticks; top-of-book size ~12 each side.

**Implication.** A maker quoting at best_bid+1 / best_ask−1 captures a ~14-tick *theoretical* round-trip on every full fill. Hydrogel is by far the widest-spread product in the round.

### 1.2 Mid-price dynamics

- Per-tick mid Δ std = **2.17**; range [−11.5, +11.5].
- 1-tick autocorrelation of Δmid = **−0.129** → essentially bid-ask bounce (lag-2..50 sit inside the random-walk band).
- Returns at dt = 5, 10, 50 ticks all show AC ≈ 0 (decays like classic microstructure noise).
- Daily mid mean: 9991 / 9992 / 9989. Pooled mean = **9990.8**, std 31.9.
- P(|mid − 10000| < 30) = **62%**, P(< 50) = **86%**, P(< 100) = **99.9%**.

### 1.3 Strong long-horizon mean reversion to 10 000

AR(1) on (mid − 10 000):
- Coefficient = **0.99787** → half-life **325 ticks** (~3.25% of a day).
- Correlation between current deviation and forward change at horizon h:

| h ticks | corr(mid−10 000, mid_{t+h}−mid_t) |
|---:|---:|
| 50 | −0.20 |
| 200 | −0.37 |
| 500 | −0.49 |
| 1000 | **−0.62** |
| 2000 | **−0.70** |

This is the dominant tradable alpha for the product.

### 1.4 Cross-asset and microstructure

- Mid-return correlation with VE: **0.006** at lag 0; max |lag-corr| over ±10 = 0.008. **No spread-trade against VE.**
- After a market trade, signed forward mid drift = ±0.2 SeaShells at any horizon — **adverse selection ≈ 0**. Maker flow is non-toxic.
- Bid-ask volume imbalance correlates 0.30 with next-tick Δmid, but only 1.7% of ticks have non-negative imbalance, so it's a sparse confirming signal, not a primary one.

### 1.5 Trade flow

- 1 010 market trades / 30 000 ticks (≈ 1 every 30 ticks). Avg trade size **4** (range 2–6).
- 524 buys / 486 sells — balanced. All trades are at exactly bid_1 or ask_1 (no inside-spread crosses).

---

## 2. Maker simulation (worse-mode fills, identical to backtester)

Simulator: for every tick, place quotes at best_bid+1 / best_ask−1 with inventory skew. A historical market trade at price p strictly above our ask fills our ask (and symmetric for bid). Mark P&L to mid + cash.

### 2.1 Baseline (current `trader_hydrogel_v7`)

| Variant | 3-day P&L | End pos | Buy fills | Sell fills |
|---|---:|---:|---:|---:|
| target_pos = 0 (pure MM) | **+25 297** | −20…+7 | 1 960 | 1 953 |

This matches the documented `trader_round3_robust.py` hydrogel bucket (+26 173). The `±2 %` gap is OF size-skew and quote-shrink rules in v7 that the simple sim doesn't replicate; baseline is consistent.

### 2.2 New alpha — inventory target leans on (mid − 10 000)

`target_pos = clip(−k·(mid − 10 000), −cap, +cap)`. Same MM rule, but inventory skew is computed around `target_pos` instead of 0, so when mid is below 10 000 we accumulate long inventory (and vice versa).

| k | cap | Day 0 | Day 1 | Day 2 | **Total** |
|---:|---:|---:|---:|---:|---:|
| 0 | — | +9 077 | +13 257 | +2 963 | +25 297 |
| 1 | 200 | +9 686 | +18 018 | +7 789 | +35 493 |
| 2 | 200 | +13 658 | +22 904 | +11 235 | **+47 797** |
| **3** | 200 | **+15 227** | **+25 126** | **+13 086** | **+53 439** |

- Profitable on every day, scaling monotonically with k up to ≈3.
- End-of-day net inventory stays in [−46, +23] — not a directional bet.
- Fill count drops (1960 → 1445 at k=3) because skew sometimes shifts our quotes outside the spread; the **quality** of fills (buying low, selling high) more than makes up for the volume loss.

### 2.3 Robustness: adaptive anchor (2 000-tick rolling mean)

If 10 000 is overfit (live anchor could drift), an adaptive anchor still wins:

| k | Day 0 | Day 1 | Day 2 | Total |
|---:|---:|---:|---:|---:|
| 1 | +9 636 | +15 277 | +4 730 | +29 643 |
| 2 | +10 962 | +17 563 | +7 208 | +35 733 |
| 3 | +12 100 | +18 669 | +8 793 | +39 562 |

Adaptive variant gives up ~25% of the in-sample edge for protection against a structural shift in fair value.

### 2.4 Things that did NOT help

- Quoting deeper inside the spread (offset_in = 2..7): **monotonically worse**, fills are price-priority, deeper just hands edge back.
- Larger quote size (≤200): no change — historical trades are all qty ≤ 6, never size-constrained.
- Skewing quote prices directly by `−k·(mid−10000)` instead of via inventory target: −12k to −44k P&L, because it pushes quotes out of the 1-penny-inside zone and kills fills.
- Cross-hedging with VE: zero correlation, no edge.
- VE-style underlying mean-reversion model on hydrogel returns: lag-1 AC is bid-ask bounce, not tradable on its own.

---

## 3. Strategy plan

### 3.1 Architecture

Two layers on top of the existing v7 chassis (`round3/trader_hydrogel_v7.py`).

**Layer A — Market making (already implemented).** Quote `best_bid + 1` / `best_ask − 1` whenever spread ≥ 2. Quote size = 25. Inventory skew = `round(−2 · (pos − target) / 200)`. Order-flow size-skew on the side being aggressively hit.

**Layer B (NEW) — Mean-reversion inventory target.**
```
target = clip(round(-K_FV * (mid - ANCHOR)), -CAP, +CAP)
```
The inventory skew in Layer A is then computed against `(pos − target)` instead of `pos`. This biases us toward long when mid < anchor and short when mid > anchor.

**Recommended parameters (in-sample optimal, validated per-day):**
- `ANCHOR = 10000` (fixed). Pooled-mid is 9990.8, but the round-number 10000 is the natural attractor and produced the best per-day P&L.
- `K_FV = 3.0` (units: contracts per SeaShell of deviation from anchor).
- `CAP = 150` (leaves a 50-contract buffer below the 200 limit for MM inventory drift).

**Defensive parameters (recommended for live submission):**
- `ANCHOR_MODE = "ema"` — exponential moving average with span ≈ 2 000 ticks, fallback to 10000 when EMA hasn't warmed up.
- `K_FV = 2.0`, `CAP = 100`. Costs ~10–15k of in-sample edge but immunises against an anchor shift.

### 3.2 Why this works (short version)

Hydrogel mid is mean-reverting with half-life 325 ticks and 2 000-tick reversion correlation −0.70. By making the maker accumulate inventory in the *correct* direction of expected reversion, we earn:
1. Standard MM half-spread on every fill (~7 SeaShells gross per round-trip), AND
2. The full mean-reversion move (typically 20–60 SeaShells) on the fraction of inventory we hold through the reversion.

In-sample this lifts 3-day P&L from +25 k to +53 k.

### 3.3 Risk controls

1. **Hard inventory cap** at `CAP` (= 150 in primary; 100 in defensive) for the *target*, plus the existing 200 hard limit on `pos`.
2. **Fail-safe flatten** — if cumulative product P&L < −2 000 SeaShells at any tick, force `target = 0` and resume pure MM. (Not triggered in any in-sample day; pre-emptive.)
3. **Anchor sanity check** — if |mid − ANCHOR| > 200, treat the anchor as broken and fall back to `target = 0` for the rest of the round.
4. **Keep Layer A's order-flow size-skew** intact. It's the existing toxic-trade dampener.
5. **Don't combine with the Layer 2 IV-overlay logic from VE strategy** — these are independent products; nothing to share.

### 3.4 Implementation plan

Concrete code path (everything in `round3/`):

1. **`trader_hydrogel_v8_meanrev.py`** — copy of `trader_hydrogel_v7.py` with:
   - Add `K_FV`, `CAP`, `ANCHOR` constants at top.
   - Compute `mid = (best_bid + best_ask) / 2` (already implicit in current OF logic — refactor).
   - Compute `target = max(-CAP, min(CAP, round(-K_FV * (mid - ANCHOR))))`.
   - Replace `inv_skew = round(-INV_MAX_SKEW * (pos / LIMIT))` with
     `inv_skew = round(-INV_MAX_SKEW * ((pos - target) / LIMIT))`.
   - Add anchor-broken kill switch (if `abs(mid - ANCHOR) > 200`, set `target = 0`).
   - Persist nothing extra in `mem` (signal is stateless from current mid).

2. **Backtest** with the prosperity-4 backtester per CLAUDE.md (`PYTHONPATH=imc_trading/imc-prosperity-4-backtester ; python -m prosperity4bt round3/trader_hydrogel_v8_meanrev.py 1--2 1--1 1-0`). Compare PnL by day vs `trader_hydrogel_v7.py`.

3. **Sweep `K_FV ∈ {1.5, 2.0, 2.5, 3.0}` × `CAP ∈ {100, 150, 200}`** in the backtester, not just the simulator, to verify the v7 size-skew interactions don't change the optimum.

4. **Decide aggressive vs defensive** based on per-day backtest stability. If the (fixed-anchor, K_FV=3, CAP=150) variant degrades on any day vs v7, ship the defensive (EMA-anchor, K_FV=2, CAP=100) variant.

5. **Promote winner** by integrating into the round-3 multi-product trader (`trader_round3_robust.py`-style) — replace the `_v7` block for HYDROGEL only; leave VE / vouchers untouched.

6. **Do NOT delete the v7 file** until the user has reviewed the backtest comparison and explicitly approves the swap (per CLAUDE.md research-workflow rule).

### 3.5 Open questions for the next session

1. **Does mean-reversion edge survive the v7 OF size-skew interaction?** The simulator omits the order-flow shrink rule; backtester will show whether the two effects compound or cancel.
2. **What is the right anchor in live trading?** 10 000 is round; the in-sample mean is 9990.8. A pre-round mini-burn of 200 ticks could pin the live anchor before going aggressive.
3. **Take-profit overlay?** Once `pos ≈ ±CAP` and `mid` has crossed the anchor in our favour, an aggressive market-order exit at the *opposite* best price could lock the move faster than waiting for a maker fill. Worth a separate ablation.
4. **Per-tick skew quantisation.** `inv_skew` is rounded to integer ticks; with a 16-tick spread the 2-tick max is fine, but a finer 4-tick cap may lift P&L further. Sweep in the backtester.

### 3.6 Expected P&L

In-sample: **+47 k to +53 k over 3 days** at K_FV ∈ [2, 3] (vs +25 k baseline). Defensive variant: **+30 k to +40 k**. Round 3 has 3 live days, so expect roughly the same numbers if the anchor holds.

---

## 4. Backtest validation (prosperity4bt, `--match-trades worse`)

Implementation files committed to this branch:
- `round3/trader_hydrogel_v8_meanrev.py` — fixed anchor = 10 000, K_FV = 3, CAP = 150 (recommended primary).
- `round3/trader_hydrogel_v8_ema.py` — EMA anchor, K_FV = 2, CAP = 100 (defensive).

| Variant | Day 0 | Day 1 | Day 2 | **Total** | Δ vs v7 |
|---|---:|---:|---:|---:|---:|
| `trader_hydrogel_v7` (baseline) | 9 766 | 13 432 | 2 975 | **26 173** | — |
| `trader_hydrogel_v8_meanrev` (K=3, CAP=150) | 15 701 | 24 306 | 13 076 | **53 083** | **+102.8%** |
| `trader_hydrogel_v8_ema` (K=2, CAP=100, α=0.0005) | 13 249 | 17 998 | 7 543 | **38 790** | +48.2% |

Both v8 variants are profitable on every day. The fixed-anchor primary doubles baseline.

### 4.1 K_FV × CAP parameter sweep (fixed anchor, full backtester)

|  K  | CAP=50 | CAP=100 | CAP=150 | CAP=200 |
|----:|-------:|--------:|--------:|--------:|
| 0.0 | 26 173 | 26 173 | 26 173 | 26 173 |
| 1.0 | 33 054 | 35 913 | 35 913 | 35 913 |
| 1.5 | 33 961 | 41 677 | 41 826 | 41 826 |
| 2.0 | 33 895 | 46 335 | 48 090 | 48 068 |
| 2.5 | 33 786 | 47 975 | 51 290 | 51 398 |
| 3.0 | 33 122 | 49 038 | **53 083** | 53 688 |
| 3.5 | 33 092 | 48 648 | 53 666 | 54 852 |
| 4.0 | 33 001 | 49 127 | 54 800 | 56 729 |
| 5.0 | 32 773 | 48 865 | 55 390 | 57 632 |

- Total P&L is monotonic in K up to ≈ 4 then flat. Reasoning to *not* push past K=3: the marginal gain (1.7 k → 4 k) comes from holding inventory closer to the 200 hard limit, which has zero margin for adverse fills. K=3, CAP=150 keeps a 50-contract buffer.
- All cap=50 rows saturate near 33 k — cap is binding. cap≥150 captures the full signal.
- All sweep rows are profitable on every day (no spike, no crash).

### 4.2 Per-day stability check (selected rows)

| K, CAP | Day 0 | Day 1 | Day 2 | Variance check |
|---|---:|---:|---:|---|
| 0, — | 9 766 | 13 432 | 2 975 | Day 2 is 23% of total |
| 2.0, 150 | 14 464 | 22 770 | 10 856 | 23% / 47% / 23%, balanced |
| 3.0, 150 | 15 701 | 24 306 | 13 076 | 30% / 46% / 25%, balanced |
| 4.0, 200 | 16 283 | 26 430 | 14 016 | 29% / 47% / 25%, balanced |

Day 1 is the largest contributor across all variants — that's where mid drifted highest above 10 000, giving the overlay the most signal to capture. Day 2 was the v7 weak day (3 k); the overlay lifts it to 13 k, the cleanest evidence that the alpha is real and not an artefact of any single day.

### 4.3 Decision

**Promote `trader_hydrogel_v8_meanrev` (K_FV=3, CAP=150) as the new primary hydrogel strategy.** It delivers +27 k more than v7, profitable on all three days, with sensible safety margins on the position limit. Keep `trader_hydrogel_v8_ema` as a defensive fallback if pre-round live data shows the anchor is shifting away from 10 000.

Per CLAUDE.md research-workflow rule: **`trader_hydrogel_v7.py` is NOT deleted** — kept until you've reviewed the backtester comparison and approved the swap. Once approved, the next step is to swap the hydrogel block in `trader_round3_robust.py` (or its successor) to call v8.

---

## 5. TL;DR

- Hydrogel has a 16-tick spread, near-zero adverse selection, and **strong mean-reversion to 10 000** (corr = −0.70 over 2 000 ticks, AR(1) half-life 325 ticks).
- Pure MM (current v7) earns +26 k / 3 days (backtester confirmed).
- Adding a mean-reversion-driven inventory target — **bias inventory long when mid < 10 000, short when mid > 10 000** — lifts P&L to **+53 k** at K_FV=3, CAP=150 in the actual backtester, profitable on every day.
- Implementation: `round3/trader_hydrogel_v8_meanrev.py` (primary) + `round3/trader_hydrogel_v8_ema.py` (defensive). v7 kept until you approve.
- Next step: swap hydrogel block in the merged round-3 trader to v8.
