# Round 5 — Lead-lag analysis & audit

_2026-04-29. Source scripts: [`round5/leadlag_products.py`](../../leadlag_products.py)._

## TL;DR

- **Question:** does a tradeable lead-lag signal exist between the 50 round-5 products at tick frequency?
- **Initial answer (pre-audit):** weak pairwise (max |corr| 0.026), but four families looked like they had strong basket→leg signals: SNACKPACK, PEBBLES, OXYGEN_SHAKE, ROBOT.
- **Audited answer:** **only SNACKPACK_PISTACHIO has a robust cross-product lag-1 signal**, with SNACKPACK_STRAWBERRY a weaker second. The PEBBLES, OXYGEN_SHAKE and ROBOT "signals" were largely self-contamination artifacts (the target leg was inside the basket and its own autocorrelation leaked into the cross-corr).
- **Tradeability:** PIS pooled LOO corr = -0.084 over 30k ticks (~12σ). Edge per signal ~0.05 ticks. Sub-spread for a taker, but a clean **maker quote-skew** input on PIS, and a starting point for a SNACKPACK basket-fade strat where PIS is the focal leg.

---

## Method

For each ordered product pair (A, B) and lag L ∈ {1..5}, compute
Pearson corr( Δmid_A(t-L), Δmid_B(t) ) per day, then pool across the 3
days. A pair is "sign-stable" if the sign of the corr agrees across all
three days (random-null sign-stability rate = 25%).

Tables in `round5/reports/CROSS/`:

- `leadlag_products_full.csv` — 36k rows (per day × pair × lag)
- `leadlag_products_stable.csv` — collapsed across days
- `leadlag_products_best.csv` — best lag per ordered pair
- `leadlag_products_summary.md` — top-N tables

For the basket-vs-leg follow-up: per family, basket = mean of the 5 leg
returns; compute corr( basket(t-1), leg(t) ).

**Audit added LOO basket:** for the target leg, basket excludes that leg.
This removes the self-autocorr contamination path described below.

---

## Pairwise scan — what it shows

- 2,450 ordered pairs × 5 lags = 12,250 hypotheses.
- **1,435 / 2,450 = 58.6% sign-stable.** Random null = 25%, so structure exists, but per-pair effect size is small.
- Top pair: `UV_VISOR_MAGENTA → GALAXY_SOUNDS_SOLAR_FLAMES` L=2, +0.026. Median best-pair |corr| = 0.009.
- Lag-1 dominates (66% sign-stable vs 54-59% at L≥2). Signal decays in <1 tick.
- **Intra-family vs inter-family pairwise corrs are statistically indistinguishable** (mean |corr| 0.011 vs 0.011). The spec hint about "groups with embedded patterns" does not show up at the pairwise level — it shows up only at the basket level (next section).
- ~57% of stable pairs are negative → the dominant motif is reversion, not momentum cascade.
- 426 mutual ordered pairs (both A→B and B→A sign-stable) → reciprocal reversion, not one-way information leakage.

**Statistical reality check.** N = 10,000 ticks/day × 3 = 30,000. Single-day SE(corr) ≈ 0.010, pooled ≈ 0.0058. Bonferroni for 12,250 tests sets a per-pair threshold of |corr| ≈ 0.026; only the very top pair clears it.

---

## Basket → leg scan (pre-audit)

Per family, corr( family-mean Δmid at t-1, leg Δmid at t ), pooled over 3 days:

| family | mean leg corr | strongest leg | strongest |corr| | tradeable? |
|---|---:|---|---:|---|
| SNACKPACK | -0.055 | PISTACHIO | 0.070 | yes |
| ROBOT | -0.030 | DISHES | 0.082 | flagged |
| OXYGEN_SHAKE | -0.024 | EVENING_BREATH | 0.066 | partial |
| PEBBLES | -0.022 | S | 0.026 | yes |
| GALAXY_SOUNDS | -0.010 | DARK_MATTER | 0.019 | weak |
| UV_VISOR | -0.007 | RED | 0.013 | noise |
| PANEL | -0.006 | 2X2 | 0.011 | noise |
| MICROCHIP | -0.006 | SQUARE | 0.012 | noise |
| TRANSLATOR | -0.006 | SPACE_GRAY | 0.014 | noise |
| SLEEP_POD | +0.000 | LAMB_WOOL | 0.004 | none |

This was the headline. **It was largely wrong** — see audit.

---

## AUDIT — leave-one-out basket

Mechanism of the bug: each leg has its own lag-1 mean reversion (single-product autocorr around -0.02). When the leg is included in the family basket, basket(t-1) carries the leg's t-1 return, which then auto-correlates with leg(t). The "basket lead-lag" was partly the leg's own reversion reflected through the basket.

Audit: recompute with **basket = mean of the 4 *other* legs** (target leg removed).

| family | leg | basket-incl-leg | basket-excl-leg (LOO) | retained | verdict |
|---|---|---:|---:|---:|---|
| SNACKPACK | PISTACHIO | -0.0695 | **-0.0836** | 120% | **stronger under LOO — real cross-product signal** |
| SNACKPACK | STRAWBERRY | -0.0516 | -0.0490 | 95% | real |
| SNACKPACK | VANILLA | -0.0558 | -0.0287 | 52% | half-real |
| SNACKPACK | CHOCOLATE | -0.0551 | -0.0252 | 46% | half-real |
| SNACKPACK | RASPBERRY | -0.0415 | -0.0148 | 36% | mostly self |
| PEBBLES | S | -0.0258 | -0.0142 | 55% | weak survivor |
| PEBBLES | L | -0.0237 | -0.0128 | 54% | weak survivor |
| PEBBLES | XL | -0.0184 | -0.0099 | 54% | sub-noise |
| PEBBLES | M | -0.0202 | -0.0004 | 2% | gone |
| PEBBLES | XS | -0.0211 | **+0.0099** | sign flip | **artifact** |
| OXYGEN_SHAKE | EVENING_BREATH | -0.0664 | -0.0151 | 23% | mostly artifact |
| OXYGEN_SHAKE | CHOCOLATE | -0.0423 | -0.0064 | 15% | mostly artifact |
| ROBOT | DISHES | -0.0818 | -0.0019 | 2% | **was 100% self-autocorr** |
| ROBOT | IRONING | -0.0474 | +0.0019 | sign flip | **artifact** |

### Family-level basket autocorrelation

basket(t-1) → basket(t):

| family | basket AC | reading |
|---|---:|---|
| PEBBLES | **-0.49** | very strong family-level reversion, but no individual leg is more predictable than another |
| SNACKPACK | **-0.23** | family-level reversion + PIS-specific edge on top |
| ROBOT | -0.10 | weak family reversion |
| OXYGEN_SHAKE | -0.06 | weak |
| SLEEP_POD | +0.00 | no family structure at all |

PEBBLES has the strongest *basket-level* mean reversion of any family — when family-mean ticks up, family-mean ticks down next. But under LOO no individual leg leads the others, so this is a basket-only signal (trade the basket as a 5-leg unit, not a per-leg directional bet).

### What about the ROBOT_DISHES day-4 outlier?

In the basket-incl-leg readout, DISHES day-4 corr was **-0.239** (vs -0.004, -0.002 on days 2-3). I'd flagged it as a possible data-quality bug. The audit explains it without a bug: DISHES had a single-day own-autocorr spike that, when included in the basket, made basket(t-1) and DISHES(t) look strongly negatively coupled. Under LOO the day-4 corr is essentially zero. **No data-quality issue — just contamination math.**

---

## Conclusions

### Lead-lag signal: yes, but tiny and concentrated

Across all 50 round-5 products and 3 days, only one cross-product lead-lag signal survives strict auditing:

1. **SNACKPACK_PISTACHIO** — LOO basket(t-1) → PIS(t) corr = **-0.084 pooled** (~14σ over 30k ticks). Individual day LOO corrs: day 2 -0.097, day 3 -0.075, day 4 -0.079 → directionally stable, magnitudes consistent.
2. **SNACKPACK_STRAWBERRY** — LOO corr -0.049 (~6σ). Real but smaller.
3. **SNACKPACK_VANILLA / CHOCOLATE** — LOO corr -0.025 to -0.029. Borderline.
4. Everything else in the round-5 universe is at or below the multiple-comparisons noise floor at lag 1.

### What the spec hint actually means

> "some groups offer more market inefficiencies than others… in certain groups, strong patterns are embedded in the price movements"

Within the lag-1 cross-product frame, **the only group with embedded structure beyond own-product mean reversion is SNACKPACK**. Other "patterns" the spec refers to likely live in:

- single-product autocorr (mean reversion at lag 1; present in most of the 50 products at |corr| ~0.01–0.03 — not analysed here)
- basket-only mean reversion (PEBBLES family is the strongest example)
- non-mid-diff signals (signed trade flow / OFI typically gives 2-3× larger corrs than mid_diff)

### Tradeability

PIS LOO edge per signal ≈ 0.084 × σ_basket. With σ_basket per tick on the order of 0.5–1 tick, that's 0.04–0.08 ticks of expected move per event — **sub-spread for a taker**. Real value is:

- **Maker quote-skew on PIS:** tilt the mid by k × basket(t-1) when quoting. Free edge layered on baseline MM PnL.
- **5-leg SNACKPACK basket fade:** when basket ticks ≥ k·σ, fade with sized weights. Per-trip cost dominated by spread, but 5 legs of capacity at limit 10 each.
- **Don't build:** ROBOT, OXYGEN_SHAKE, PEBBLES per-leg fades (they were artifacts) or any inter-family pair (largest is 0.026).

### Methodology fix (DONE)

Future basket-vs-leg analyses in this repo must use **leave-one-out basket by default**. Implemented as `cross_family.basket_vs_leg_table(..., loo=True)` (default True). Docstring carries the LOO rationale + a pointer back to this audit.

### Follow-up: OFI predictor

Re-ran the basket→leg scan with **signed trade flow** as the predictor instead of mid-diff (script: [`round5/leadlag_basket_ofi.py`](../../leadlag_basket_ofi.py); output: [`leadlag_basket_ofi.md`](leadlag_basket_ofi.md)). Hypothesis was that OFI typically gives 2-3× larger lead-lag corrs than mid-diff in liquid books.

**Result: OFI did *not* help in round 5.**

- Top OFI sign-stable |corr| = 0.015 — same magnitude as the mid-diff noise floor.
- **SNACKPACK_PIS collapses under OFI:** mid-diff -0.084 → OFI -0.009 (10× weaker, sign retained).
- A handful of low-magnitude OFI > mid pairs exist (TRANSLATOR_VOID_BLUE, OXYGEN_SHAKE_MINT, UV_VISOR_YELLOW), all at |corr| ≤ 0.015 — likely chance survivors out of 250 tests, not Bonferroni-significant.

**Why OFI underperforms here:** position limit 10 means trades are tiny and many ticks have *zero* trade activity. Signed volume becomes sparse and quantised, while mid-diff updates on every quote change. OFI dominates mid-diff in normal liquid markets; the round-5 limit-10 regime inverts that.

**Conclusion unchanged after OFI test:** SNACKPACK_PIS basket-fade (mid-diff predictor) remains the only robust cross-product lead-lag signal. Don't bother with OFI variants for the rest of the universe.

---

## Files

- [`round5/leadlag_products.py`](../../leadlag_products.py) — pairwise scan generator
- [`leadlag_products_full.csv`](leadlag_products_full.csv) — per (day, pair, lag) corrs
- [`leadlag_products_best.csv`](leadlag_products_best.csv) — best-lag-per-pair table (input for hub analysis)
- [`leadlag_products_summary.md`](leadlag_products_summary.md) — top sign-stable pairs
- this file — basket-vs-leg + LOO audit
