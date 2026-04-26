# Round 4 Research Plan — "The More The Merrier"

**Date opened:** 2026-04-26
**Status:** pre-research. No backtests yet. No code in `round4/` yet.
**Source spec:** [`Round 4 - "The More The Merrier" 1e43d50cdd2383929a6981dced4dbc53.md`](Round%204%20-%20%E2%80%9CThe%20More%20The%20Merrier%E2%80%9D%201e43d50cdd2383929a6981dced4dbc53.md)
**Round 3 closing PnL:** +36,116 SeaShells (submitted [`round3/486411/486411.py`](../round3/486411/486411.py))

---

## 0. Lessons from round 3 (read this first, every time)

Before any new variant, these gates must pass. Each is a real failure mode we paid for.

| # | Rule | Why we paid for it |
|---|------|--------------------|
| L1 | **Pick the simplest model that matches the data's regime.** Stationary → constant. Drifting → EMA. Regime-switching → state model. Don't EMA a stationary series. | EMA / soft-EMA / regime detectors all underperformed a fixed `HP_MEAN=9991` because hydrogel is stationary. |
| L2 | **Size is alpha. Defensive levers come before another offensive signal.** | The vol-armor `min(1, 30/std50)` did more work than any signal stack. |
| L3 | **Two discrete thresholds beat any continuous policy.** Step functions defend from data; sigmoids/tanh slopes don't. | `dev>22 take / dev>14 make / else silent` beat every tanh, OBI-scaled, inventory-skewed continuous variant. |
| L4 | **A no-trade band is half the strategy.** Always-quote = always eat toxic flow at fair. | Below dev=14 the winning hydrogel does nothing. Variants that quoted at all deviations bled. |
| L5 | **Structural alpha survives backtest→live; statistical alpha does not.** | v9 cross-book mean-rev: backtest +112k, live -10k. Coefficients fitted on 3 days are noise. |
| L6 | **One product per file. Never mix product families in research/ablation.** | Discovered when rolling back v9 hydrogel without touching the option block. Modularity = recoverability. |
| L7 | **Backtest is a gating filter, not an optimiser.** Use it to *reject* obviously broken variants, not to *rank* close ones. | 3-day samples cannot distinguish strategies whose true PnL differs by less than ~10k SeaShells. |

**The gating questions for any new variant**:
1. Can I defend this from first principles (not from a backtest plot)?
2. What would break it live that wouldn't show in 3 historical days?
3. Is there a sizing/regime-gate change that captures the same idea more robustly?

If any answer is "no" or "I don't know", the variant is v9 in disguise.

---

## 1. What's actually new in round 4

| Change | Algo / Manual | Magnitude |
|--------|---------------|-----------|
| `Trade.buyer` and `Trade.seller` are now populated with counterparty IDs (in `state.market_trades` and historical CSVs) | Algo | **Large** — first datamodel change in 4 rounds. New alpha source. |
| VEV TTE at start = 4 days (was 5 in round 3) | Algo | Small — adjust `T_rem` init. |
| Manual challenge swaps from Bio-Pods bidding to AETHER_CRYSTAL vanilla + exotic options | Manual | Large — completely new mechanic. |
| Hydrogel, VE, vouchers, position limits | Algo | **Unchanged.** |

Everything else (fill model, position limits, tick rate, day length) is identical.

---

## 2. Algo strategy direction

### 2.1 Baseline: round 3 submission verbatim

Before a single line of new code, copy [`round3/486411/486411.py`](../round3/486411/486411.py) → `round4/trader_baseline.py` and adjust only:

- `T_rem` initial value: TTE 4 days, not 5. (Verify how `opt_days` rolls — check it doesn't start at 0 if round 4 begins at TTE=4.)
- Nothing else.

Backtest on round-4 data once it ships. If the baseline scores poorly, the structural alpha changed and we need a different starting point. If it scores reasonably, **counterparty conditioning is pure additive lift** on top of a known-working block.

### 2.2 The counterparty edge — how to mine it without falling into v9

Counterparty IDs are a new field. The wrong way to use them: fit a per-counterparty alpha model on 3 days of data. That's v9.

The right way: find the **structural** version of the signal.

**Profiling questions to answer first** (offline analysis, not in trader code):

1. **Per counterparty: what's their fill side ratio?** Always-buyers, always-sellers, two-sided.
2. **Per counterparty: what's the price drift in the 100/500/1000 ticks *after* they trade?** Adverse-selection signal: if X buys and price goes up 80% of the time, X is informed. If X buys and price reverts, X is liquidity-providing.
3. **Per counterparty: what's their typical trade size, and is it bursty or steady?** Noise traders vs algos.
4. **Per counterparty per product: do they show up in HG vs VE vs VEV with different patterns?**

These are answered with **histograms and conditional means**, not regressions. Histograms are robust; regression coefficients fitted on 3 days aren't (L5).

**Conversion to trading:**
- The signal becomes a **classification**, not a continuous coefficient. Each counterparty gets a label: `informed / passive / noise / unknown`.
- The strategy gates on the label discretely (L3): "if I'm filling against `informed` and `dev` is small, skip" or "if `passive` is on the other side, take an extra unit".
- **Sizing first, signal second** (L2): start by *shrinking* size when an informed counterparty is on the book; only later try to *initiate* trades against passive ones.

**Anti-pattern to avoid:** building a per-counterparty regression with 30 features and tuning weights on backtest. That's the v9 archetype. If you find yourself sweeping a parameter grid, stop.

### 2.3 Per-product plan

#### HYDROGEL_PACK
- Round-3 winner: anchor=9991 + vol-armor + dev thresholds 22/14. **Don't touch the structure.**
- One specific lift to test: when `dev > 22` and the maker quotes on the wrong side of the anchor are coming from an `informed` counterparty, *don't take* — they may know something. When from `passive` / `noise`, take with full confidence.
- Question to verify: is `HP_MEAN=9991` still the right anchor on round-4 data, or has it drifted?

#### VELVETFRUIT_EXTRACT
- Round 3: -2,531 (sub-noise loss). Z-score taker + tight maker.
- Honest question: **should we trade VE at all in round 4?** If the answer is "only as a delta hedge for the option book", then VE has no standalone strategy and we just quote tight against current option-book delta. That removes a complex z-score block and replaces it with a dumb hedge. Simpler is usually right (L1).

#### VEV vouchers
- Round 3: net positive across the smile, but VEV_4500 was -6,864.
- **Investigate VEV_4500 first** before re-deploying. Was it the OU correction overshooting on a deep-ITM strike? Was it a counterparty pattern (someone systematically picking us off)?
- Counterparty conditioning is especially relevant for options: option flow is more informed than spot flow in real markets. If round 4 follows that pattern, the counterparty filter is exactly the missing piece.

---

## 3. Manual challenge — AETHER_CRYSTAL exotics

This is independent of the algo trader. One-shot, scored on average PnL across **100 simulations** of the underlying.

**Underlying spec:**
- GBM, **zero risk-neutral drift**, **σ_annual = 251 %**, 4 steps/day, 252 trading days/year.
- 2-week TTE = 10 trading days, 3-week TTE = 15 trading days.
- σ over 3 weeks: σ√T = 2.51 · √(15/252) ≈ **0.612**. That is *enormous* — option prices will be far from intrinsic, vega is everything.

**Tradable products** (all on AETHER_CRYSTAL):
- Spot.
- 2-week vanilla calls and puts.
- 3-week vanilla calls and puts.
- **Chooser** (3-week expiry; at the 2-week mark, holder picks call-or-put, takes whichever is ITM at that moment).
- **Binary put** (fixed payoff if S_T < K, else 0).
- **Knock-out put** (vanilla put unless S ever trades below the barrier — then knocks to 0).

**Pricing approach (closed-form first, MC for path-dependents):**

| Product | Method | Notes |
|---------|--------|-------|
| Vanilla call/put | Black-Scholes, r=0 | Closed-form. |
| Binary (digital) put | `e^(-rT) · N(-d2)` × payoff | Closed-form. r=0 simplifies. |
| Chooser | Closed-form: `max(C, P)` at chooser date is `C(T_full) + max(0, K e^(-r(T-t)) − S e^(-q(T-t)))`; with r=q=0 that's `C + max(0, K-S)` priced at chooser time. Use Rubinstein decomposition. | Closed-form available; verify with MC. |
| Knock-out put | Closed-form barrier formula (Merton) under GBM, or MC with daily monitoring on the 4-step grid | The grid matters: 4 steps/day means barrier monitoring is *not* continuous. Discrete monitoring increases value vs continuous (less likely to knock). MC is safer than the continuous-barrier closed form. |

**Strategy direction:**
- **Look for mispricings vs theoretical, not directional bets.** σ=251% means any directional view is dwarfed by vol.
- Construct positions where the manual UI prices look wrong vs your models. Volume cap per product; pick the highest-edge legs.
- **Hedge or limit unhedged exposure** — the spec explicitly warns. A naked short on a 3-week put with σ=251% can blow up.
- Score is **average PnL over 100 sims** — variance reduction matters. Combinations of legs that are individually high-vol but collectively low-vol (e.g., short straddle vs long strangle, vega-neutral combos) get scored well.

**Open question to verify in spec:** is the displayed price on each manual product the price *we pay/receive*, or is it a quote we have to lift? Re-read the manual instructions before computing edges.

---

## 4. Workflow plan

### Phase 1 — Baseline + data audit (before any new code)
1. Copy [`round3/486411/486411.py`](../round3/486411/486411.py) → `round4/trader_baseline.py`. Update TTE to 4 days. Backtest on round-4 data once available.
2. Build `round4/round4_analysis.ipynb`:
   - Verify HP anchor (9991 still correct?), VE behaviour, VEV smile shape at TTE=4d.
   - Per-counterparty histograms (questions 1–4 in §2.2).
   - Compare: same plots as round 3, side-by-side with round-3 data, looking for regime breaks.

### Phase 2 — Counterparty layer
1. From phase-1 histograms, assign each counterparty a discrete label.
2. Add **size-shrinking gate** (L2 first) on hydrogel and VEV when an informed counterparty is on the book.
3. Backtest. Accept only if structural improvement, not parameter tuning.

### Phase 3 — Per-strike option investigation
1. Re-examine VEV_4500 loss from round 3. Identify the failure mode.
2. Patch the OU pricer or carve out VEV_4500 as a no-trade product.

### Phase 4 — Manual challenge
1. Implement closed-form pricers for all 7 product types (incl. Rubinstein chooser, Merton barrier).
2. Build MC simulator on the 4-step-per-day grid for knock-out put (sanity check).
3. Compute edges vs displayed prices. Construct a vega-bounded portfolio.
4. Submit, then iterate before round end.

### Anti-pattern checklist (gate every PR / variant against this)
- [ ] Does this variant introduce a continuous coefficient I tuned on backtest? (L3, L7)
- [ ] Does it always-quote, even at fair value? (L4)
- [ ] Is the underlying assumption (stationary / drifting / regime) verified, or just assumed? (L1)
- [ ] Did I add a defensive lever (sizing / no-trade band) before adding another signal? (L2)
- [ ] Does the edge survive a different counterparty mix, or only under historical participants? (L5)
- [ ] Is hydrogel logic isolated from option logic, recoverable independently? (L6)
- [ ] Am I using the backtest to *reject* variants, not to *rank* close ones? (L7)

If any box is unchecked, don't merge.

---

## 5. Files to create

| File | Purpose | Phase |
|------|---------|-------|
| `round4/round4_analysis.ipynb` | All offline analysis: anchor verification, smile fit, counterparty histograms | 1 |
| `round4/trader_baseline.py` | Round-3 winner with TTE patch | 1 |
| `round4/trader_v1_cp_size.py` | Baseline + counterparty size-shrink gate | 2 |
| `round4/manual_aether.ipynb` | Pricers + edge computation for manual exotics | 4 |
| `round4/round4_findings.md` | Audited write-up of phase-1 analysis (companion to notebook) | 1 |

**Do not create** files that mix product families (L6), or scripts that compare strategies locally with custom plots (use the kevin-fu1 visualizer).

---

## 6. North star

> **The round-3 winner was `simple anchor + vol-armor + discrete thresholds + no-trade band + isolated modules`. Every fancy variant lost money. Round 4 should look like the same shape: round-3 baseline, plus *one* counterparty-conditioned defensive lever, plus a clean manual exotic book.**
>
> If the strategy file gets longer than 486411.py, it's probably going wrong.
