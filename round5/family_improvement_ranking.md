# Round 5 — Family Improvement Ranking

Compiled 2026-04-29 from current best-per-family PnL (single live D4) cross-referenced
with pipeline `tradeable_ideas.md` outputs (per-product archetype, FDR-verified IC,
stationary pair flags, OBI taker scores).

Method: for each family, look at (a) **untouched products** with strong pipeline
signals, (b) **untapped layers** on already-traded products (OBI tilt, pair leg, MR
override), and (c) **structural cap** (variance-bound? all-paired? family-untradeable?).

Floor / ceiling / effort estimated qualitatively from the pipeline's IC sign + |IC|
plus the live evidence already on the table (e.g. ORANGE went from +2,697 with
`qty=1` to +4,124 with `qty=cap` — that's the proven scaling delta).

## Headline ranking

| Rank | Family | Live now | Untouched signal | Estimated uplift | Effort |
|---:|---|---:|---|---:|---|
| **1** | **MICROCHIP** | +1,792 | 3 untouched MR + 2 stationary pairs (incl. coint_p=0.020) | +3,000–6,000 | low |
| **2** | **UV_VISOR** | +8,640 | AMBER untouched + AMBER↔MAGENTA stationary pair + 5/5 OBI follow signals | +3,000–6,000 | low |
| **3** | **PANEL** | 0 | family virgin, 1 high-conf + 2 low-conf MR | +1,000–3,000 | medium |
| 4 | OXYGEN_SHAKE | +3,497 | MORNING_BREATH untouched (high-conf MR) | +500–1,500 | low |
| 5 | GALAXY_SOUNDS | +3,441 | SOLAR_WINDS untouched (low-conf MR) | +500–1,500 | low |
| 6 | SLEEP_POD | +9,710 | LAMB_WOOL/SUEDE untouched but contradictions/non-stat | +500–1,000 | medium |
| — | TRANSLATOR | +4,832 | 2 untouched but ASTRO failed → likely engineered books | ~0 | high |
| — | ROBOT | +4,165 | LAUNDRY untouched (live loser) — already covered in v7 | ~0 | high |
| — | PEBBLES | +10,428 | all paired, at integration optimum | variance-bound | none |
| — | SNACKPACK | +4,546 | all paired, basket integrated | variance-bound | none |

**Top-3 expected stack**: +7,000 to +15,000 SeaShells. With current +51,051 baseline,
that puts the next-submission target in the **+58k to +66k SeaShells** range.

---

## #1 — MICROCHIP (+1,792 → ~+5,000–7,000)

**Pipeline signals (top in the universe by FDR-pass density):**

| Product | Archetype | IC | FDR-pass | Pair | Status |
|---|---|---:|---|---|---|
| MICROCHIP_TRIANGLE | MR_TAKER | **0.111** @ h=1000 | ✅ | ↔ OVAL stationary | **traded** (+1,528) |
| MICROCHIP_OVAL | MR_TAKER | 0.097 @ h=1000 | ✅ | ↔ TRIANGLE stationary | untouched |
| MICROCHIP_RECTANGLE | MR_TAKER | 0.079 @ h=1000 | ✅ | ↔ SQUARE stationary | untouched |
| MICROCHIP_SQUARE | MR_TAKER | (high-conf, 3 triggers) | structural | ↔ RECTANGLE stationary (coint_p=**0.020**) | untouched |
| MICROCHIP_CIRCLE | MR_TAKER | (low-conf, 1 trigger) | — | none | traded (+264) |

**Why it's #1:**
- Only family in the universe with **3 IC-verified MR signals at FDR-pass**.
- 2 stationary cointegrated pairs **completely unexploited**: OVAL↔TRIANGLE and
  SQUARE↔RECTANGLE. SQUARE↔RECTANGLE has the strongest cointegration p in the
  entire universe (0.020) — and the corr is *negative* (−0.88), so the pair-trade
  signal is sharper than a typical positive-corr basket.
- Spreads 7–12, depth 11–16 at L1 — comfortable book for a taker.
- **Spike caveat**: spike-fade study rejected MIC_TRIANGLE/SQUARE/OVAL/RECT on the
  per-day positivity gate. That was for *spike-conditional* taker only. **Continuous
  MR_TAKER is the pipeline's recommendation, untouched.**

**Iron-rule progression** (per [`mm_strategies_research.md §0`](mm_strategies_research.md)):

1. **Rung 0**: copy 549159's naive top-of-book MM `qty=cap, spread≥2 gate` as proof
   the book is tradeable on OVAL/SQUARE/RECT individually.
2. **Rung 2**: add MR_TAKER overlay using `neg_zscore_mid_50` (or `_vwap_50` for
   OVAL/RECT) on each. Disjoint legs (no symbol in two pairs).
3. **Rung 3** (only if rung 2 wins per-day): pair-trade SQUARE↔RECTANGLE with
   β-hedge from OLS. Negative corr means short one + short other when residual is
   too negative, etc. Use existing `slp_cp` pair scaffolding from 555509.
4. Validate each rung: BT × 0.1 budget, per-day positive, markout-1 ≥ 0.

**Constraint check**: pair_disjoint_legs satisfied — OVAL with TRIANGLE, SQUARE
with RECTANGLE, no symbol used twice.

---

## #2 — UV_VISOR (+8,640 → ~+12,000–14,000)

**Pipeline signals:**

| Product | Archetype | OBI follow IC@h=1 | Pair | Live |
|---|---|---:|---|---:|
| UV_VISOR_AMBER | MR_TAKER (low) | +0.059 | ↔ MAGENTA stationary, **coint_p=0.042** | **untouched** |
| UV_VISOR_MAGENTA | MR_TAKER (med) | +0.059 | ↔ AMBER stationary | +695 (qty=cap) |
| UV_VISOR_ORANGE | NO_EDGE | +0.058 | ↔ AMBER non-stat | +4,124 (qty=cap) |
| UV_VISOR_RED | NO_EDGE | +0.059 | none | +3,822 (qty=cap) |
| UV_VISOR_YELLOW | MR_TAKER (low) | +0.061 | none | −214 (drop) |

**Why it's #2:**
- AMBER is the last UV product never traded. Sister products RED (+3,822) and ORANGE
  (+4,124) confirm naive `qty=cap` MM works on UV.
- **AMBER↔MAGENTA stationary pair (corr=−0.87)** is the only stationary UV pair —
  not yet exploited. Negative correlation is unusual within a 5-product family;
  pipeline hint that these 2 may be *substitutes* in the synthesis. Pair trade
  could add ~2–4k.
- All 5 products show **OBI L1 follow signal IC≈+0.06 in the same direction**. None
  individually FDR-pass, but the cross-section consistency is itself evidence — 5
  products independently giving +0.06 same-sign is extremely unlikely under H0. An
  OBI tilt grafted onto the existing naive-MM `qty=cap` recipe would shift the fair
  toward depth-heavy side without changing the structural bet.

**Iron-rule progression:**

1. **Rung 0**: AMBER alone with the 558897 recipe (`qty=cap, spread≥2 gate`,
   inside-touch quote). Validate it's even tradeable — AMBER could be like YELLOW
   (drop −214). Spread is 10 (vs 13 for ORANGE/MAGENTA), depth 36 — book healthier
   than YELLOW's.
2. **Rung 4** (only if rung 0 wins): graft OBI tilt on AMBER + MAGENTA + ORANGE +
   RED. Just the L1 OBI: `fair = mid + c1 · standardized_obi_l1`. Start `c1 = 0.5`
   (small).
3. **Rung 3** (in parallel): AMBER↔MAGENTA pair-trade as a **separate** strategy
   layer. Take pair when residual z >2; flat when |z|<0.5. Disjoint from the naive
   MM by using the position-net rule (pair leg adds to family position, capped at
   limit=10).

**Caveat**: feedback `external_signal_redundancy` warns OBI overlay can correlate
with the existing dev variable. Run an attribution control (OBI-off vs OBI-on,
otherwise identical) before claiming the OBI lift is real.

---

## #3 — PANEL (0 → ~+1,500–3,000)

**Pipeline signals:**

| Product | Archetype | Triggers | Spread | Notes |
|---|---|---:|---:|---|
| PANEL_2X2 | MR_TAKER (high) | 4 | 9 | vr_k5=0.975 z=−1.95, vwap_acf=−0.060, no contradictions |
| PANEL_4X4 | MR_TAKER (low) | 1 | 9 | acf_lag1=−0.006 marginal |
| PANEL_1X2 | MR_TAKER (low) | 1 | **12** | 1 trigger + 2 contradictions (hurst+vwap acf both positive) |
| PANEL_1X4 | NO_EDGE | 0 | 8 | hurst=0.58 (persistent) — skip |
| PANEL_2X4 | NO_EDGE | 0 | 10 | OBI fade IC=−0.044 (informational) — skip |

**Why it's #3:**
- Only family with 5 untouched products; floor is provably 0 (currently 0).
- PANEL_2X2 has the strongest structural MR signature outside MICROCHIP_SQUARE
  (4 triggers, vr p=0.05, no contradictions).
- No FDR-verified IC — risk this is statistical-significance-without-economic-edge
  (per `feedback_ic_significance_vs_tradeability`). Half-spread = 4–6 ticks; need
  IC × σ_target to clear that to be tradeable. Compute before deploying.

**Iron-rule progression:**

1. **Rung 0**: deploy 549159's naive `qty=1` MM on **only PANEL_2X2** (highest
   signal). 30-min triage: does it fill? does it hit per-day positive on BT?
2. **Rung 0 expanded**: if 2X2 wins, layer 4X4 (low-conf MR) + 1X4 / 2X4 (NO_EDGE
   but maybe naive MM still profitable on the spread alone, like ORANGE was when
   classified NO_EDGE). Skip 1X2 because it has explicit contradictions.
3. **Rung 2**: graft MR z-score taker on 2X2 only — its high-conf MR is the only
   one with no contradictions in the family.

**Caveat**: low trade frequency family-wide (n_trades = 733 / 30k ticks × 5 products
= 0.005 per tick per product). `worse` mode means few fill opportunities. Naive MM
may sit and not fill. Check the BT fill count before betting on it.

---

## #4 — OXYGEN_SHAKE (+3,497 → ~+4,000–5,000)

- **MORNING_BREATH untouched + high-conf MR_TAKER** (4 triggers, hurst=0.516).
  Plus OBI L1 follow IC=+0.051. Already analogous to EVENING_BREATH (which is in
  the v7 spike trader at IC=0.049 FDR-pass).
- **CHOCOLATE↔GARLIC stationary pair untraded** (corr=+0.65, coint_p=0.066 —
  marginal). But CHOCOLATE alone is +2,230 in 549159 and the 555509/556502 tries
  on GARLIC swung wildly (−1,391, −390, +1,267). Pair would smooth the variance.
- **Effort**: low. MORNING_BREATH = drop-in MR_TAKER. CHOCOLATE-GARLIC pair = one
  more pair leg, disjoint from existing pairs.

---

## #5 — GALAXY_SOUNDS (+3,441 → ~+4,000–5,000)

- **SOLAR_WINDS untouched, low-conf MR** (3 triggers). Plus OBI L1 follow IC=+0.065
  (highest in family). Should add ~500–1,500.
- **PLANETARY_RINGS rejected** by `feedback_per_day_positive_selection` — per-day
  D5 was −7,011 live. Don't re-add.
- **DARK_MATTER rejected** (live loser in 550714).
- Cap: SOLAR_FLAMES (+1,212) + BLACK_HOLES (+2,229) is the existing universe.

---

## What's variance-bound (do nothing)

- **PEBBLES (+10,428)**: 4-pair star L/M/S/XS-vs-XL is at integration optimum on a
  single live day (557541). Same code returned +1,699 on PEB_S in 555509 and −588
  in 556502 — variance-dominated. Don't redesign on n=1 day.
- **SNACKPACK (+4,546)**: 4-pair basket, same caveat.
- **TRANSLATOR (+4,832)**: ASTRO_BLACK live-failed (engineered balanced books).
  ECLIPSE_CHARCOAL / SPACE_GRAY likely same archetype — risky to expand without
  microstructure validation first. The +4,832 is essentially ceiling.
- **ROBOT (+4,165)**: LAUNDRY is the only untouched product, classified MR_TAKER
  but with `vr_k5=1.010 trending` contradiction. Live evidence shows it as a loser.
  Improvement here means refining DISHES spike trader, which is already in v7.

---

## Suggested next-action sequence

Build **one strategy per family**, ship as a single combined submission `v8`:

1. `strat_mic_mr_pairs.py` — MICROCHIP (3 new MR + 2 pair legs).
2. Patch existing `strat_uv_qtycap.py` to add AMBER + AMBER-MAGENTA pair leg.
3. `strat_panel_mr_2x2.py` — PANEL_2X2 alone, naive `qty=1` MM as proof-of-life.
4. Patch OXY block to add MORNING_BREATH + (optionally) CHOCOLATE-GARLIC pair.
5. Patch GALAXY block to add SOLAR_WINDS.

Per family, BT (Python+Rust), validate each new product is per-day positive, then
fold into combined v8. Targets:

- **Conservative**: +57,000 (current 51k + 6k from MIC + PANEL + OXY incremental)
- **Realistic**: +60,000 (above + UV uplift to ~12k)
- **Aggressive**: +66,000 (everything stacks linearly, OBI tilt confirmed)

After live validation: kill anything that didn't move PnL >1k, refine winners,
re-stack for next round.
