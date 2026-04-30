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

### 2.4 Confirmed findings from `research_round4.ipynb` (2026-04-26)

Notebook executed end-to-end on round-4 hydrogel data. Concrete results that change the plan:

#### Counterparties (hydrogel only)

Three IDs on the tape: `Mark 14`, `Mark 22`, `Mark 38`. Pair frequency: Mark 14 ↔ Mark 38 = 99% of prints; Mark 22 = 19 prints across 3 days (sub-sample, ignore).

Drift after trade (signed so positive = CP was right; horizons in ticks):

| CP | side | n | drift t+10 | t+50 | t+100 | t+500 | label |
|----|------|--:|-----------:|-----:|------:|------:|-------|
| Mark 14 | buy | 496 | +8.2 | +8.6 | +8.8 | +9.8 | **informed** |
| Mark 14 | sell | 507 | +8.1 | +9.1 | +8.5 | +5.4 | **informed** |
| Mark 38 | buy | 515 | −7.9 | −9.0 | −8.5 | −5.2 | **passive** |
| Mark 38 | sell | 507 | −8.0 | −8.2 | −8.5 | −9.4 | **passive** |
| Mark 22 | both | 19 | unstable | — | — | — | ignore (n too small) |

Volume-weighted version is identical magnitude. Signal is consistent across all 4 horizons and both sides → structural, not noise.

**Mechanism (interpretation, not fitted):** Mark 14 lifts/hits when mid will keep moving their way. Mark 38 quotes both sides and is being adverse-selected by Mark 14. The book is essentially a duel; we sit between them.

**Trader change (single discrete gate, L3-compliant):**
- When the most recent print's aggressor is **Mark 14** and they are on the *opposite* side of our intended take/make → **skip or shrink to 1**.
- When aggressor is **Mark 38** → **full size**, possibly +1 unit (passive flow signals reversion).
- When aggressor is **Mark 22** or unknown → baseline behaviour.

Invariance check (L5): the labels are about *direction of mid drift after the print*, not about the CP names. If round 4 swaps in different bot IDs that exhibit the same drift pattern, the gate still works *after a notebook re-run + manual relabel* — but the trader code itself hardcodes the strings. [`trader_v1_cp_hydrogel.py`](trader_v1_cp_hydrogel.py) defines `HP_INFORMED = frozenset({"Mark 14"})` and `HP_PASSIVE_CP = frozenset({"Mark 38"})`. **If live R4 ships different IDs the gate silently no-ops** (no fallback, no auto-detection). Operator action required at round start: print the first ~1 000 live `state.market_trades` aggressors, confirm the IDs match — if not, relabel and redeploy. Do not rely on the gate working out-of-the-box.

#### Vol-armor verdict — inert in both rounds

Round-3 trader uses `vol_scale = min(1, 30 / std50)` where `std50` = rolling 50 stdev of mid (wap in trader, mid in notebook — equivalent). Cap = 30.

| stat | R3 std50 | R4 std50 |
|------|---------:|---------:|
| max | 14.06 | 14.06 |
| 75% | 6.12 | 6.25 |
| mean | 5.08 | 5.15 |

Max realized std ≈ 14, so `30/std50 ≥ 2.14` always → clipped to 1.0. **Activation rate = 0%** in both rounds. Position limit = 200 every tick. Armor contributed **zero PnL** to the +19,712 hydrogel result. The actual position-management work was done by the inventory skew (`fair_anchor − (hp_curr/200)·6`) and the dev gates.

**Action:** remove the lever from `trader_baseline.py`. We have **zero evidence** it helps; tuning a never-fired param is overfit risk (L7). Remove or — if kept defensively — set cap=10 with explicit acknowledgement that we have no PnL evidence either way and that it'll only fire on regime breaks not in our 6 days of samples.

#### Anchor verdict — keep `HP_MEAN = 9991`

R4 pooled mean = 9994.65, median = 9999. Mean `|mid - anchor|` over R4 is ~28-29 across all candidate anchors (9991, pooled mean, pooled median). Spread between the best and worst candidate is **0.7 ticks** of mean abs deviation — sub-noise. Day 3 drifts to median 10007.25, but switching anchors to chase that is exactly the v9 archetype on a 3-day sample. **Keep 9991.**

#### Dev-band verdict — keep 14 / 22

Trade band split on R4: silent 23% / make 15% / take 61% (n=1022 trades; this is trades, not ticks — ticks would weight silent higher). The take band still dominates and the gate still discriminates. No reason to retune (L7).

#### Net plan after notebook

Single structural change vs round-3 baseline: add a **counterparty size gate** keyed on the most recent print's aggressor. Remove the dead vol-armor. Anchor and dev thresholds untouched.

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
| `round4/research_round4.ipynb` | Hydrogel CP + vol-armor + anchor analysis (existing, executed 2026-04-26) | 1 ✅ |
| `round4/research_vev.ipynb` | VEV smile + per-strike CP profile + VEV_4500 post-mortem | 1 |
| `round4/trader_baseline_hydrogel.py` | Round-3 winner, TTE=4d patch, **vol-armor removed** (notebook §5 verdict) | 1 ✅ |
| `round4/trader_v1_cp_hydrogel.py` | Baseline + last-aggressor size gate (Mark 14 → shrink, Mark 38 → full) | 2 ✅ |
| `round4/trader_v2_cp_vev.py` | If VEV CP profiling shows a clean signal, add same gate to voucher quotes | 3 |
| `round4/manual_aether.ipynb` | Pricers + edge computation for manual exotics | 4 |
| `round4/round4_findings.md` | Audited write-up of phase-1 analysis (companion to notebook) | 1 |

**Do not create** files that mix product families (L6), or scripts that compare strategies locally with custom plots (use the kevin-fu1 visualizer).

---

### 5.1 Inventory-control study — outcome (2026-04-27)

Question: is the existing `HP_SKEW_TICKS=6` anchor skew sized correctly?

Empirical finding on R4 data: position pins at ±200 for **~84%** of ticks under skew=6 (replay of baseline trade log). Notebook §5 claim ("position management was done by inventory skew") was wrong — the skew was barely active. A skew × anchor grid (skew ∈ {0, 6, 12, 20}, anchors {9991, 9995, 9997, 9999, 10000, 10003}) was run end-to-end during the 2026-04-27 inventory-control study; bigger skew lifted PnL +7k to +21k at every anchor except 9999 (which sits ≈ R4 pooled median; small skew suffices when anchor matches data center).

> **Audit caveat (2026-04-29).** The 24-cell grid logs in `_invctl_probes/` were deleted on 2026-04-27 after promoting the two winners (see "Removed" list below), and the notebook does not contain reproducible cells for the sweep. The two surviving claims that *are* reproducible from current artefacts are (a) the three canonical backtests (`baseline / principled / gridbest`) and (b) the +9k principled-vs-baseline / +43k gridbest-vs-principled gaps. The "+7k to +21k at every anchor except 9999" sentence is preserved as historical record but **cannot be re-verified without re-running the grid**.

**Surviving hydrogel files in `round4/`:**

| File | Anchor | Skew | R4 backtest | Defence |
|------|-------:|-----:|------------:|--------|
| `trader_baseline_hydrogel.py` | 9991 | 6 | 57,063 | R3-live control |
| `trader_v1_cp_hydrogel.py` | 9991 | 6 | 56,015 | Negative CP-taker-gate result (see §5.2) |
| **`trader_principled_hydrogel.py` (post-fix 2026-04-27)** | **9991** | **14** | **110,871** | **Same anchor/skew/dev structure as before; only the taker capacity formula changed (see §5.2). Pre-fix value 69,136 retained in git history.** |
| `trader_gridbest_hydrogel.py` | 10003 | 20 | 112,734 | Comparison ceiling only. Anchor 10003 is fitted to R4 day-3 drift = v9 archetype. Not a ship target. Now within 1.9k of post-fix principled — gridbest's residual edge collapses once the taker formula is corrected. |

**Removed (2026-04-27, after user sign-off):**
- `trader_v2_adaptive_anchor.py`, `trader_v3_passive_boost.py` — no structural defence; v2 chased anchor drift (v9 archetype).
- `trader_anchor_{9995,9997,9999,10000,10003}.py` — single-anchor sweep, superseded by the 24-cell grid.
- `_invctl_probes/` (24 anchor×skew variants) — exhausted; two winners promoted out.

**Headline takeaway:** the lessons-compliant choice is `HP_MEAN=9991` + `HP_SKEW_TICKS=14`. The +9k gap to grid-best (s=20) sits inside the L7 noise band. The +43k gap to absolute grid-best (a=10003, s=20) is anchor-fitted and structurally indefensible.

Canonical backtest logs at `backtests/round4_{baseline,principled,gridbest}_hydrogel.log`.

---

### 5.2 Taker-formula fix + CP-cap-shrink negative result (2026-04-27)

**Context.** Trying to combine the principled philosophy (anchor 9991, skew 14)
with a counterparty-conditioned lever, we wrote `trader_v2_cp_hydrogel.py`:
asymmetric position cap (long=200/short=100 when CP signal predicts mid up;
reversed when down). Attribution analysis revealed two findings.

**Finding 1 — taker capacity formula was clipped (bug-fix, +41,735 PnL).**

Pre-fix principled taker:
```
qty = min(HP_LIMIT - abs(hp_curr), side_volume)
```
At pos=+150, sell-take could only do 50 units (trim toward zero, not flip). The
maker tier already used the wider formula (`HP_LIMIT + hp_curr` for sell,
`HP_LIMIT - hp_curr` for buy) — letting the maker swing across ±limit while
the taker was clipped to "same |pos|". The taker was the inconsistent one.

Post-fix:
```
sell side: cap = HP_LIMIT + hp_curr      # mirrors maker
buy side:  cap = HP_LIMIT - hp_curr
```
Pure structural fix, no tunable, no historical fit.

| Day | Pre-fix | Post-fix | Δ |
|----:|--------:|---------:|--:|
| 1 | 20,965 | 26,796 | +5,831 |
| 2 | 18,598 | 37,286 | +18,688 |
| 3 | 29,573 | 46,789 | +17,216 |
| **Tot** | **69,136** | **110,871** | **+41,735** |

Lift consistent across all 3 days. Patched into `trader_principled_hydrogel.py`
in place; pre-fix value preserved in git history.

**Finding 2 — CP-cap-shrink lever contributes +337 / +42k. Statistical noise.**

Attribution test (`trader_v2_sigoff.py`, control with CP signal hard-disabled,
formula change still applied):
- v2 (CP on):     111,208
- v2_sigoff:      110,871
- **Δ = +337**, less than 1% of the total v2-vs-pre-fix lift.

Diagnostic instrumentation (`trader_v2_diag.py`, per-tick log of sig / pos /
tier / cap-bind) confirmed the mechanism is dead, not just sub-noise:

| Stat | Value |
|------|------:|
| Total ticks (R4 all days) | 30,000 |
| sig active (sig≠0) | **99.0%** |
| sig=0 (silent baseline) | 1.0% |
| Cap binding ticks | 7.2% of all, 7.3% of sig-active |
| sig run length (median) | 44 ticks |
| Median \|pos\| when sig active | 200 |

The signal is on 99% of ticks — saturated → no information. The cap binds
7.3% of sig-active ticks, mostly near saturation where it can't actually
prevent further accumulation (we're already pinned). CP-cap-shrink is dead.

**Why CP signal does nothing despite carrying real information.** This is the
deeper lesson — the §7 notebook drift signal IS structural (n=2025 across 4
horizons), but our PnL framework neutralises it for five separate reasons:

1. **Saturation kills information.** Mark 14 + Mark 38 = 99% of tape. With
   TTL=100, sig=0 fires 1% of ticks. A predictor that's always-on is the new
   baseline, not a conditioning variable.
2. **Anchor-relative PnL is mid-drift-invariant.** Our edge ≈ `(anchor − entry)·pos`.
   Mid wandering between entry and reversion is absorbed into reversion noise;
   skipping a fill because "mid will drift wrong" loses entry edge for zero
   gain.
3. **CP signal is redundant with `dev`.** Mark 14 buys when mid is below fair
   (= when dev<0) — the same condition that makes us want to buy. CP is a
   leading or coincident indicator of the *same mean-rev* the dev variable
   already captures. Not new alpha; same alpha re-stated.
4. **Mismatched time horizons.** CP drift horizon ≈ 50 ticks. Our entry→exit
   hold ≈ 50–100 ticks. Drift and reversion happen on the same timescale, so
   drift is absorbed into the realised PnL of the trade.
5. **Cap binds rarely + at the wrong moment.** Median \|pos\|=200; cap-shrink
   from 200→100 mostly fires when we're already over the cap (no further
   accumulation possible anyway). The moments when shrinking 100 *would*
   matter (pos≈50, sig adverse) are uncommon under saturation-loving mean-rev.

**Generalisation.** CP signal is real but worthless **for any anchor-pinned
mean-rev strategy on hydrogel**. It could matter for a different strategy
shape — momentum, drift-following, shorter holding periods, no anchor — but
under our shape, the dev variable already prices it in. Future rounds:
before adding any external-signal lever to an anchor-mean-rev block, ask
whether the signal is correlated with the dev variable already. If yes, it's
redundant.

**Files (research artefacts, kept per CLAUDE.md research workflow):**

| File | Role | R4 PnL | Status |
|------|------|-------:|--------|
| `trader_principled_hydrogel.py` | Production candidate (post-fix) | 110,871 | Promoted |
| `trader_v2_cp_hydrogel.py` | Asymmetric CP cap-shrink experiment | 111,208 | Negative result documented |
| `trader_v2_sigoff.py` | Control: v2 with CP hard-disabled (isolates formula change) | 110,871 | Attribution control |
| `trader_v2_diag.py` | Instrumented v2 (per-tick sig/pos/cap-bind log) | 111,208 | Mechanism diagnostic |
| `trader_v1_cp_hydrogel.py` | Earlier CP-taker-gate (pre-fix taker formula) | 56,015 | Negative result, retained |

Backtest logs: `backtests/round4_run_{baseline,principled,v1cp,v2cp,v2sigoff,v2diag,gridbest}.log`.
Post-fix principled re-verification: `backtests/round4_principled_postfix.log` (110,871 — matches sigoff to the unit, confirming the in-place patch is identical to the control).

---

### 5.3 Live test feedback loop + regime-detector experiment (2026-04-27)

**Live test result (submission 507225, principled at lim=200, anchor=9991):**
−782 SeaShells across HYDROGEL_PACK only. Live test was a 100,000-ts game
(1,000 calls × 100 ts step). Mid sat at median 10037, anchor 9991/9995 was
30+ ticks below the entire day's range. Strategy pinned at -200 short and
marked to market for the duration.

User's subsequent edit: `HP_LIMIT 200 → 100` (defensive halve, internal
soft cap; competition limit still 200). Then `HP_MEAN 9991 → 9995`
(R4 sample mean). Both changes are sub-noise on backtest; halving was the
real defensive lever.

**Time-scale finding.** Backtester historical day = 1,000,000 ts (10k calls
× 100 ts step). Live test = 100,000 ts (1k calls × 100 ts). 10× scale
mismatch. Threshold parameters tuned on backtester data may not translate
to live test scale.

**Daily-reset anchor experiment (`trader_v4_dailyreset_hydrogel.py`):**
warmup 5000 ticks at fallback anchor, then anchor = median of warmup mids
fixed for rest of day. R4 backtest **55,239** (-10,145 vs principled).
Diagnosis: mid is highly autocorrelated; first half of day is not
predictive of second half's center. Even at warmup=50% of day, the
warmup median is 12-48 ticks off the day's true median per day. The
"daily-reset from today's data" approach is structurally broken.

Analysis of yesterday's-median-as-today's-anchor: across-day median spread
is only ~14 ticks (R4 days 9999, 9993, 10007), dominated by ~170-tick
within-day wander. Daily anchor adaptation buys at most ~10 ticks of avg
|dev|; not a meaningful improvement.

**Regime-detector experiment (`trader_v5_pstuck_hydrogel.py`):**
Hypothesis: detect when dev has been clearly dislocated (|dev| > MAKER_DEV)
for too long, then suppress new positions on the bad side and unwind
aggressively. Iteratively developed:

| Variant | Param | R4 backtest | Comment |
|---------|-------|------------:|---------|
| v5 dev>0 detector, fixed 10k threshold | TICKS=10k | -48,304 | Catastrophic false positives |
| v5 dev>0 detector, fixed 300k | TICKS=300k | 65,384 | Identical to principled (inert) |
| v5 dev>0 detector, adaptive (FRAC=0.30, MIN=30k) | adaptive | 41,896 | False positives on dev oscillation |
| v5 |dev|>14 detector, adaptive (MIN=150k) | adaptive | 65,384 | **Clean on backtest, never fires within 100k-ts live test** |

The "clearly dislocated" condition (|dev| > MAKER_DEV for the threshold
duration, vs "dev > 0") was a real improvement — eliminated noise-band
false positives. But MIN_TS=150k still exceeds the 100k-ts live test
duration: detector cannot fire within the only platform we can test.

**L7 violation.** MIN_TS was empirically chosen as the lowest value that
produced zero false positives on R4 backtest (sweep: 30k → 50k → 100k →
150k). That is exactly what L7 prohibits — using backtest as an optimiser
rather than a gating filter.

**Mark 38 fade-in-silent-band experiment (`trader_v6_m38fade_hydrogel.py`):**
Cumulative imbalance fade overlay in the no-trade band, capped at 30 units,
only when |pos| < 30. R4 backtest 65,362 (-22 vs principled — noise).
Diagnostic: the overlay opportunity (silent band AND |pos|<30) exists for
only 2.8% of ticks; the imbalance threshold rarely crosses; net activation
0.23%. Anchor logic + skew keeps position at saturation or zero, rarely at
low-non-zero values inside the silent band. Structural constraint kills the
idea: silent-band-with-low-position is too rare to be a useful overlay window.

**Aggregate CP scorecard (post all 4 attempts):**

| Lever | Concept | Backtest Δ | Verdict |
|-------|---------|----------:|---------|
| v1 CP taker-gate | Skip take when CP says adverse drift | −1,048 | Skipping = opp cost |
| v2 CP cap-shrink | Asymmetric position cap | +337 | Statistical noise |
| v3 CP-VWAP anchor | Adaptive anchor from Mark 14 prints | −26,270 | Anchor noise > fixed |
| v6 M38 silent-band fade | Cumulative imbalance overlay | −22 | Opportunity rate 0.23% |
| **All 4 CP applications** | Various structural framings | **all ≤ 0** | **Mark 14/38 signal does not slot into anchor-mean-rev positively** |

Conclusion strengthened: in this strategy shape, CP signal is structurally
redundant with `dev`. The latency math (always 1+ tick late, spread cost
exceeds residual drift edge) and the anchor-relative PnL framework
combine to neutralise the signal regardless of how it's applied.

**Decision: ship `trader_principled_hydrogel.py` (anchor 9995, lim 100,
taker-formula fix). Drop v5/v6 from ship candidates.**

Rationale:
- Empirically: v5 detector inert on backtest, untested on live, threshold
  L7-tuned. Carrying complexity for a hedge against an n=1 failure is
  asymmetric.
- v6 overlay structurally constrained by rare silent-band-with-low-pos.
- principled is the simplest model with one live observation supporting it
  (R3 +19,712 with anchor=9991 invariance argument). One bad live day
  (-782 with lim=200, projected -391 with lim=100) is small absolute cost
  relative to backtest expectation.

Files retained as research artefacts (not for ship):
- `trader_v4_dailyreset_hydrogel.py` (daily-reset anchor — broken)
- `trader_v5_pstuck_hydrogel.py` (regime detector — L7 caveat documented)
- `trader_v6_m38fade_hydrogel.py` (Mark 38 silent-band fade — opportunity-rate-bound)

Backtest logs: `backtests/round4_run_{v4dailyreset,v5_*,v6m38fade*}.log`.

---

### 5.4 Anchor-free CP-momentum + CP-fade — both directions lose (2026-04-27)

**Hypothesis tested.** All four prior CP overlays (v1/v2/v3/v6) layered the
signal on top of an anchor-mean-rev core where `dev` already captures it.
Idea: drop the anchor entirely; let CP flow drive the position directly. If
the +8-tick drift after a Mark 14 print is real, a copier should profit.

**v7 — CP-momentum copy** (`trader_v7_cpmomentum_hydrogel.py`, removed
2026-04-27 after sign-off). Anchor-free. Rolling signed-volume window =
5000 ts (≈ drift horizon). Three-state target +HP_LIMIT / 0 / -HP_LIMIT
keyed on net signal vs threshold (10 = one typical informed print).
Aggressive taker on every signal flip.

R4 backtest: **−252,117 / −211,057 / −208,518 = −671,692.** Negative
all 3 days.

**v8 — CP-fade** (`trader_v8_cpfade_hydrogel.py`, removed 2026-04-27 after
sign-off). Same shape, sign inverted (bet on mean-reversion of CP-driven
drift).

R4 backtest: **−262,836 / −221,997 / −254,361 = −739,194.** Worse.

**Diagnosis.** Both directions lose → not a sign bug; the shape is wrong.
Hydrogel mid mean-reverts on ~200-tick scale. The +8-tick drift over
50 ticks reverts before we can exit through signal flip. Aggressive
cross-spread entry/exit on every threshold crossing burns 1-2 ticks each
side. Mark 14 + Mark 38 = 99% of tape → signal flips frequently → spread
bleed dominates whatever drift edge exists. The directional edge belongs
to the CP making the print, not to a downstream copier.

**Generalisation strengthened.** §5.2 said "CP signal redundant with dev
in any anchor-mean-rev shape". §5.4 strengthens to: **anchor-free
directional CP trading is structurally broken on stationary mid in either
sign.** The only viable use of this CP signal on hydrogel is no use at
all — principled remains the ship candidate.

**Aggregate CP scorecard (post 6 attempts):**

| Lever | Concept | Shape | Backtest Δ |
|-------|---------|-------|----------:|
| v1 CP taker-gate | Skip take when CP says adverse drift | anchor-mean-rev + gate | −1,048 |
| v2 CP cap-shrink | Asymmetric position cap | anchor-mean-rev + size | +337 |
| v3 CP-VWAP anchor | Adaptive anchor from Mark 14 prints | anchor-rewriter | −26,270 |
| v6 M38 silent-band fade | Cumulative imbalance overlay | anchor-mean-rev + overlay | −22 |
| v7 CP-momentum | Copy CP drift, anchor-free | momentum | −671,692 |
| v8 CP-fade | Fade CP drift, anchor-free | reversion-of-drift | −739,194 |
| **6/6 attempts** | Across 4 distinct shapes | — | **all ≤ 0** |

Files removed (2026-04-27 after user sign-off):
- `trader_v7_cpmomentum_hydrogel.py`, `trader_v8_cpfade_hydrogel.py`,
  `backtests/round4_run_v7cpmomentum.log`, `backtests/round4_run_v8cpfade.log`.
Numbers above retained as historical record; not reproducible from current
artefacts. Research conclusion preserved in this section and in
`feedback_external_signal_redundancy.md`.

---

### 5.5 Reversion-confirmed entry gate (2026-04-27)

**Motivation.** Live -782 from §5.3 was caused by adding into a sustained
one-sided dev. Principled has no mechanism to recognise when the mean-rev
assumption is currently violated — it just trades, every tick, on the
assumption that reversion is around the corner. The v5/v6 attempts to add
defence layered detectors on top of the same shape and either failed
backtest (v5 L7 violation) or produced sub-noise (v6).

This pass: gate the strategy's ADD action on a direct test of the
assumption itself. Compare current `dev` to a 4-tick prior history. If
`|dev|` is at the recent max, the move is still extending and the
assumption isn't holding — skip. If `|dev|` is below recent max, reversion
is observable — trade.

  is_add(dev, hp_curr) = (dev > 0 and hp_curr <= 0) or (dev < 0 and hp_curr >= 0)
  is_reverting()       = sign-aware comparison vs max/min of last 4 prior dev
  allow_entry          = (not is_add) or is_reverting()

Flatten / flip side unchanged — closing or reducing |pos| is opportunistic.

**v9 — always-on gate** (`trader_v9_revconfirm_hydrogel.py`).

R4 backtest: **16,733 / 20,286 / 28,467 = 65,486** (vs principled 110,871,
Δ = −45,385). Loss is consistent across days — not regime-dependent on
the 3-day sample.

**v8-style — conditional gate (gate fires only when |hp_curr| ≥ HP_LIMIT/2,
tested locally and rejected, file removed).**

R4 backtest: **16,871 / 19,752 / 28,308 = 64,931** (≈ v9 to noise).

The hypothesis was: position oscillates near zero on normal days, so a
position-conditional gate would skip the gate during those oscillations
and recover backtest PnL. Wrong: anchor mean-rev pins position to ±limit
(that's the design intent — saturate when dev is significant). `heavy`
condition is true on essentially every ADD-tick, so the conditional gate
collapses to v9. Position-conditional refinement adds zero PnL.

**Generalisation.** The 45k backtest cost of the reversion gate is
*genuine defensive cost*, not opportunity cost from over-firing. Anchor
mean-rev's edge IS adding into momentary dislocations every tick; any
mechanism that demands "wait, confirm reversion first" deletes a
meaningful fraction of that edge. There is no free lunch via a smarter
gate within this strategy family.

**Decision pending.** v9 is insurance against the live failure mode
(sustained dev → flat instead of pinned-and-bleeding). On 4 observations
(3 backtest + 1 live), principled still wins on total: 110,871 + (-782)
= 110,089 vs v9 ≈ 65,486 + ~0 = 65,486. v9 is only correct ship if the
user believes the live failure recurs at >40% frequency, which n=1 cannot
support.

Files retained:
- `trader_v9_revconfirm_hydrogel.py` (kept; alternative to principled
  pending live evidence on the failure-mode rate).

Files removed (2026-04-27 after user sign-off):
- `trader_v8_smartgate_hydrogel.py` (conditional-gate variant — equivalent
  to v9, no benefit).

---

### 5.6 Hypothesis-level fixes — adaptive anchor and silent-band MM (2026-04-27)

**Motivation.** Live -782 + R4 day-medians 9999/9993/10007 + live ~10037
suggest principled's "fixed cross-game anchor" assumption is wrong, not
just unlucky. v9's reversion gate defends a symptom; this section
attacks the hypothesis directly. Two model-level alternatives tested.

**v10 — EMA-adaptive anchor** (`trader_v10_emaadaptive_hydrogel.py`,
removed 2026-04-27 after sign-off).
Replace fixed `HP_MEAN` with `EMA(WAP)`, alpha = 1/500 (half-life ~347
ticks). Warmup 500 ticks, no trades. Justification: anchor adapts to
each game's actual center, eliminating the "wrong anchor" failure mode
at the source.

R4 backtest: **14,046 / 11,774 / 15,606 = 41,426** (vs principled
110,871, Δ = −69,445).

Diagnosis: adaptive anchor doesn't preserve the alpha — it removes it.
Principled's +110k comes from fading dev oscillations of 30-46 ticks
around a presumed-fixed anchor. If anchor adapts to mid, those
oscillations show up as dev ≈ 0 → no trade. The EMA literally erases
the signal that principled exploits. The +110k backtest is conditional
on the anchor being correct; if anchor is uncertain, the expected edge
collapses to ~37k regardless of mechanism.

**v11 — hybrid: silent-band MM + active-band anchor mean-rev**
(`trader_v11_hybrid_hydrogel.py`, removed 2026-04-27 after sign-off).
Three-band structure: shark and maker tiers identical to principled,
silent band (|dev| ≤ 14) gets pure inventory-skew MM with quote skew
capped at OFFSET-1 = 4 ticks (derived from HP_PASSIVE_OFFSET, not swept).

R4 backtest: **19,285 / 20,858 / 29,767 = 69,910** (vs principled
110,871, Δ = −40,961).

Hypothesis was: silent-band MM ADDS spread on top of principled's edge
(positive overlay). Wrong direction. Silent-band MM is net-negative for
two compounding reasons:

1. *Adverse selection.* MM gets filled when market trade goes BEYOND the
   quote — i.e., when mid moves against us. We buy just before mid drops,
   sell just before mid rises. Spread captured < adverse selection cost.

2. *Low opportunity rate.* Per §5.3 v6 m38fade diagnostic, silent-band-
   with-low-position is only 2.8% of ticks. Anchor logic + skew pins
   position to saturation; once saturated, the silent-band branch has
   one-sided MM (only the flatten side has remaining capacity), which
   collapses to "passive flatten quote at OFFSET" — a worse version of
   what principled's maker tier already does.

**Generalisation across 5.5 + 5.6.** No alternative to principled
dominates on backtest. v9 (gate) is the only one with structural live-
regime defense; v10 and v11 are negative results. The principled
backtest +110k embeds a wrong-anchor risk that no in-strategy mechanism
can both *detect* and *exploit*. Either ship principled and accept the
tail risk, or ship v9 and accept the lower mean.

Files removed (2026-04-27 after sign-off):
- `trader_v10_emaadaptive_hydrogel.py` (adaptive anchor erases alpha).
- `trader_v11_hybrid_hydrogel.py` (silent-band MM net-negative).

### 5.5 Trending-mid sweep (2026-04-27)

User reported live PnL improves monotonically as `HP_MEAN` rises above the
R3 anchor 9991. Hypothesis options: (a) live mid is genuinely drifting
within session, (b) live mid is stationary at a higher level than R3
(see also live `mid sat at 10037` from §4 diagnostic).

R4-BT sweep (Python BT / Rust BT, both engines agree to <0.05%):

| HP_MEAN | total | min day | notes |
|--------:|------:|--------:|-------|
| 9999 (baseline) | 73,756 / 73,672 | 19,606 | principled |
| **10010** | **80,624 / 80,718** | 20,113 | beats baseline |
| 10025 | 55,486 / 55,489 | 11,812 | over-shifted |
| 10040 | 29,055 / 29,026 | 666 | nearly idle on D2 |

BT-optimal anchor ≈ 10010 (one σ above BT mean 9994). Live-optimal is
likely higher — BT cannot rank points outside its own distribution.

Adaptive variants tried and rejected for BT:
- `ema halflife=200` — 25.5k / 25.5k. Anchor lag dev_steady ≈ v·h/ln2 ≈
  2.4 ticks, well below the 14-tick maker threshold; strategy falls
  silent. Confirms the EMA-erases-alpha lesson from §5 v10.
- `trendbias 50/400 EMA` — 22.7k / 22.7k. Same failure.

Long-pin gap fix on top of HP_MEAN=10010 (BT D1: idle 1814 ticks at
+100 long because mid stayed below 10010 sell threshold):
- `trader_hp10010eu_hydrogel.py` — split add/unwind thresholds
  (`UNWIND_DEV=5` for inventory reduction, `MAKER_DEV=14` for adds).
  R4-BT 83,726 / 83,769. Best total + best min-day (21,783).
  Doesn't visibly close the gap (mid never crossed 10001 during it)
  but harvests bigger reversions later.
- `trader_hp10010aoq3_hydrogel.py` — always-on inventory unwind quote
  at `fair±3`. R4-BT 82,379 / 82,030. Closes the gap structurally
  (max idle 1814 → ~1000 ticks) but slightly less PnL than `eu`.

Files removed (2026-04-27 after sign-off):
- `trader_ema_hydrogel.py` (-58k vs principled).
- `trader_trendbias_hydrogel.py` (-51k).
- `trader_hp10010_hydrogel.py` (superseded by `_eu`).
- `trader_hp10010aoq_hydrogel.py` (superseded by `_aoq3`).
- `trader_hp10025_hydrogel.py`, `trader_hp10040_hydrogel.py` (BT losers).

Live A/B candidate order: `hp10010eu` (max BT signal) → `hp10010aoq3`
(swap if gap-style behaviour appears live).

### 5.6 Live `aoq3` test (511631) + assessment upgrades (2026-04-27)

Live `aoq3` (single day, R4): HP +1,638. PnL path 0 → −2,745 → +1,638.
First positive R4-live hydrogel result (vs principled −782).

Live HP mid stats: mean 10033.5, median 10037.5, std 14.1, slope
+0.035/tick (~+35 ticks per 1k ticks). BT D1 slope +0.008. Live
distribution is *both* higher-mean *and* steeper-trending than any BT day.

Diagnostic upgrades (run on aoq3 BT log, not used for tuning):

1. **Counterparty attribution.** `<book>` fills (mostly our sells, n=386)
   drift −6.67 ticks against us at +5 ticks; Mark 38 fills (mostly our
   buys, n=218) drift +3.51 *for* us. Asymmetric edge by counterparty.
2. **Per-tier P&L (BT).** Maker tier `|dev|>14` is the alpha source: 92
   fills, +1.1M cash. Shark tier (374 fills) is the entry leg. Always-on
   unwind tier (138 fills) ~neutral.
3. **Position-time profile (BT).** 43% of all ticks at `|pos|≥90`; 60%
   on D1/D3. Anchor mismatch is structural, not tuning.
4. **BT-window match to live.** Closest 1k-tick BT window to live D3
   distribution earned +1,613 / 1k ticks. Top-10 BT match mean is
   +4,083 / 1k. Live earned +1,638 / 10k ticks. Live shortfall ≈ 10×
   even after shape-matching — unexplained by distribution alone.

Identified next-step lever: CP-conditioned maker quoting.

### 5.7 CP-flow-gated maker tier (2026-04-27, ruled out)

`trader_hp10010cp_hydrogel.py` — aoq3 base + structural maker-tier sizing
by aggressor flow imbalance from `state.market_trades`. Continuous size
scaling (no threshold), L5-compliant.

Attribution control (vs aoq3, same base, same days):
- Python BT: 81,847 vs 82,379 → −532. Sub-noise.
- Rust BT: 82,030 vs 82,030 → 0.

No BT lift. Per `feedback_external_signal_redundancy`, ruled out and
removed.

### 5.8 Principled-only inventory (2026-04-27)

After cleanup, hydrogel files retained:
- `trader_principled_hydrogel.py` — canonical (anchor 9999, HP_LIMIT 100)
- `trader_baseline_hydrogel.py` — R3 winner verbatim, control
- `trader_v9_revconfirm_hydrogel.py` — reversion-confirmed entry gate
- `trader_hp10010eu_hydrogel.py` — best BT (+13.6% vs principled)
- `trader_hp10010aoq3_hydrogel.py` — live-validated +1,638 single-day

Removed (not principled or not best):
- `trader_gridbest_hydrogel.py` (3-day-fitted; own docstring flags this).
- `trader_hp_multilevel_take.py` (untested experimental deep-take tier).
- `trader_hp10010cp_hydrogel.py` (CP-flow gate, no BT lift).
- `trader_m22fade_hydrogel.py` (CP-targeted but on stale 9999 anchor;
  BT 57k << 83k for `_eu`).

---

## 6. North star

> **The round-3 winner was `simple anchor + vol-armor + discrete thresholds + no-trade band + isolated modules`. Every fancy variant lost money. Round 4 should look like the same shape: round-3 baseline, plus *one* counterparty-conditioned defensive lever, plus a clean manual exotic book.**
>
> If the strategy file gets longer than 486411.py, it's probably going wrong.
