# HYDROGEL_PACK — Research → Strategy Plan

**Companion to** [`hydrogel_research_study.md`](hydrogel_research_study.md).
**Date:** 2026-04-26.
**Current champion:** [`trader_hydrogel_v16_softema.py`](trader_hydrogel_v16_softema.py) — backtest +34 683 / 3 days, max position ±50, anchor = slow EMA halflife 5 000.
**Goal:** translate the four research-supported strategy ideas (S1–S4) into shippable, backtested variants without re-introducing v9-class anchor risk.

---

## 0. Operating principles (re-affirmed before any code is written)

These come from `feedback_alpha_not_backtest.md` and `feedback_separate_products.md`. Re-stated here so the plan respects them:

1. **Backtest is a gating filter, not an optimiser.** Day-by-day positivity ⇒ promote candidate. Total PnL is secondary; a 5 % bigger total at +20 % position-tail is worse, not better.
2. **No hardcoded 10 000 anchor.** Every variant uses an EMA-derived reference price.
3. **CAP stays at 50 across all four ideas.** That is the structural risk budget agreed after the v9 post-mortem. Any idea that *requires* CAP > 50 to show alpha should be reformulated, not deployed.
4. **One alpha per file.** S2 alone, then S2+S4, then S1, then S3. No god-strategy that mixes everything before any one piece is validated independently.
5. **Promotion threshold:** ΔPnL ≥ +2 000 vs v16 over 3 days AND positive on every individual day AND no day worse than v16 by > 500. Anything inside ±2 000 is noise on 3 days.
6. **Per CLAUDE.md research-workflow rule 5:** keep every experiment file until the user reviews the kevin-fu1 visualizer output and approves removal.

---

## 1. Decision tree (read top-to-bottom)

```
                          v16 (current champion, +34 683)
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
       Phase A: S2 imbalance overlay              Phase A': S1 tanh anchor
       (orthogonal alpha, unused signal)          (cheap drop-in test, 1-line change)
                │                                             │
        promote if ΔPnL ≥ 2 k AND                  promote if ΔPnL ≥ 2 k AND
        positive every day                          positive every day
                │                                             │
                ▼                                             ▼
            v24_imb                                       v_tanh
                │                                             │
                ▼                                             │
       Phase B: S4 triple-EMA TP                              │
       (additive on top of v24_imb)                           │
                │                                             │
        promote if ΔPnL ≥ 2 k AND                             │
        positive every day                                    │
                │                                             │
                ▼                                             │
            v25_imb_tp ─────── compare in merged trader ──────┘
                │
                ▼
       Phase C: S3 Avellaneda–Stoikov size law
       (variance reduction, may not improve total)
                │
                ▼
        Promote only if total ≥ v25_imb_tp − 500 AND
        position std reduced ≥ 30 %.

       Final: ship the best of {v16, v24_imb, v25_imb_tp, vAS, v_tanh}
              based on per-day stability + tail bound.
```

The two **independent** branches (S2 and S1) run in parallel because they touch disjoint pieces of v16 (S1 changes target function; S2 changes quote suppression). Phases B and C are sequential gates after S2 lands.

---

## 2. File-by-file specification

All files live in `round3/`. All copy `trader_hydrogel_v16_softema.py` verbatim except where noted; the **Logger** class, import shim, EMA halflife, CAP=50, K_FV=1, INV_MAX_SKEW=4, OF block, and anchor-warmup logic are **identical to v16**. Only the marked region changes.

### 2.1 `strat_hg_v24_imbalance.py` (S2 — imbalance overlay)

**One-line summary.** Suppress the maker quote on the side that imbalance predicts will move adversely.

**Statistical justification (from study §6.1).** L1+L2 imbalance has corr = +0.33 with Δmid_{t+1}. When |imb| > 0.10 (n = 795 / 30 000 = 2.65 % of ticks), conditional E[Δmid_{t+1}] = ±4.15 SeaShells — about half a quoted spread. Suppressing the side facing the imbalance avoids these adverse fills.

**Mechanism.** Replace the v16 quote-block (lines 222–248) with:

```python
# Order-book imbalance signal (L1 + L2)
bv1 = abs(bs[0][1]) if len(bs) > 0 else 0
bv2 = abs(bs[1][1]) if len(bs) > 1 else 0
av1 = abs(asks[0][1]) if len(asks) > 0 else 0
av2 = abs(asks[1][1]) if len(asks) > 1 else 0
denom = bv1 + bv2 + av1 + av2
imb = ((bv1 + bv2) - (av1 + av2)) / denom if denom > 0 else 0.0

IMB_THRESH = 0.10  # below this, signal is noise (study §6.1 conditional table)

if best_ask - best_bid >= 2:
    our_bid = best_bid + 1 + inv_skew
    our_ask = best_ask - 1 + inv_skew
    if our_bid >= our_ask:
        if inv_skew > 0:
            our_bid = our_ask - 1
        else:
            our_ask = our_bid + 1

    bsz = asz = QUOTE_SIZE
    # Existing OF size-skew (kept verbatim from v16)
    if of_dir >= OF_THRESH:    bsz = int(QUOTE_SIZE * SHRINK)
    if of_dir <= -OF_THRESH:   asz = int(QUOTE_SIZE * SHRINK)
    if of_dir >= OF_EXTREME:   bsz = 0
    if of_dir <= -OF_EXTREME:  asz = 0

    # NEW: imbalance-based side suppression
    if imb > IMB_THRESH:
        bsz = 0          # imb favours buyers → mid expected up → drop our bid
    elif imb < -IMB_THRESH:
        asz = 0          # imb favours sellers → mid expected down → drop our ask

    bsz = min(bsz, buy_cap)
    asz = min(asz, sell_cap)
    if bsz > 0:
        orders.append(Order(SYMBOL, int(our_bid), bsz))
    if asz > 0:
        orders.append(Order(SYMBOL, int(our_ask), -asz))
```

**Parameter choices.**

| Constant | Value | Justification |
|---|---:|---|
| `IMB_THRESH` | **0.10** | Study §6.1 conditional table: bucket [−0.10, +0.10] has E[Δ] = −0.01 (noise), bucket [+0.10, +0.50] has E[Δ] = +4.15 (signal). 0.10 is the natural cutoff. |
| Other constants | unchanged from v16 | One-alpha-per-file rule. |

**No new state.** L1/L2 sizes are read from the current order book; nothing extra to persist.

**Predicted backtest.** +5 to +13 k over v16 → **+40 to +48 k / 3 days**. Mechanism: avoids ~50–100 toxic-fill ticks/day (where the bid would be filled at bb just before mid moves up by 4 SeaShells); also captures the same ~50–100 ticks of "ask gets richer" by holding the lone ask. Floor: it never *adds* fills, so it cannot make v16 worse than v16's pure-MM floor minus a few hundred SeaShells.

**Risk math.** Same CAP=50, same skew bounds, same anchor logic. Worst case: imbalance signal is 100 % wrong → we miss 50–100 maker fills × 7 SeaShells half-spread = up to 700 SeaShells lost vs v16. Tail-bounded.

### 2.2 `strat_hg_v25_imb_tp.py` (S2 + S4 — imbalance + triple-EMA take-profit)

**Prereq:** v24 must be promoted before this is run. Otherwise the Δ from v16 is mixing two effects.

**One-line summary.** Add an explicit liquidator that flattens to half-target when the slow reversion is *confirmed* by both a 500-tick trend EMA and a 50-tick speed EMA agreeing with the anchor direction.

**Statistical justification (from study §6.3).** Pure-maker decomposition: half-spread PnL = +27.8 k; inventory drag = −8.3 k. v16 partially recovers the inventory drag by leaning slow EMA, but it has **no explicit exit logic when the reversion has actually happened**. A take-profit overlay should convert most of the residual inventory drag from negative to neutral.

**Mechanism.** Three EMAs on three timescales:

| EMA | Halflife | α | Role |
|---|---:|---:|---|
| `anchor_ema` | 5 000 | 1.39e-4 | Long-run fair value (v16 unchanged) |
| `trend_ema` | 500 | 1.39e-3 | Confirm regime (slower than speed, faster than anchor) |
| `speed_ema` | 50 | 1.39e-2 | Detect immediate direction |

Persist all three across ticks via `mem`.

After the v16 target line (`target = round(-K_FV * (mid - anchor_ema))`):

```python
# Take-profit overlay: only flatten when local + slow signals both confirm reversion.
TP_POS_THRESH = 30      # only fire when |pos| ≥ 30 (half of cap)
TP_FRACTION   = 0.5     # halve the target when TP fires (partial unwind)

if abs(pos) >= TP_POS_THRESH:
    pos_sign    = 1 if pos > 0 else -1
    anchor_dev  = mid - anchor_ema
    speed_drift = mid - speed_ema
    trend_drift = trend_ema - anchor_ema  # is the trend itself heading back?
    # Position is short (pos_sign=-1) AND mid is above anchor (anchor_dev>0):
    # we want mid to come DOWN. TP fires if speed_drift<0 AND trend_drift<=0.
    rev_align_speed = (speed_drift * pos_sign) > 0  # speed moving toward our pos
    rev_align_trend = (trend_drift * pos_sign) >= 0
    if rev_align_speed and rev_align_trend:
        target = round(target * TP_FRACTION)
```

**Why three EMAs and not two.** The `anchor_ema` is the fair-value reference; we don't want to confuse "anchor moved" with "speed moved". The `trend_ema` tells us whether the medium-term flow is back toward anchor (so the reversion is real, not a one-tick bounce); the `speed_ema` tells us the immediate direction. Both must agree, and both must agree with our position direction (so we exit only when actively winning).

**No stop-loss override.** A stop-loss on PnL was tried in `strat_hg_regime_pnl.py` and lost 30 % of total because it fires on normal MM oscillation. The slow-EMA `dev_kill` at |dev| > 100 already provides regime-shift protection.

**Predicted backtest.** +5 to +20 k over v24 → **+45 to +68 k / 3 days**. The wider band reflects uncertainty about how often the take-profit fires productively; on the high-drift day (day 1, +3886-tick run) it should help substantially.

**Risk math.** TP only *reduces* exposure when winning. It cannot increase loss. Worst case: reversion fails to complete after TP fires → we re-accumulate at slightly worse prices. Bounded by the slow-EMA target which itself caps at 50.

### 2.3 `strat_hg_v_tanh.py` (S1 — soft tanh anchor)

**Independent branch — runs in parallel to S2.**

**One-line summary.** Replace `target = round(-K_FV * (mid - ema))` with a smooth bounded `target = CAP * tanh((mid - ema) / SCALE)`, recalibrated so the slope at origin is **2× v16**.

**Statistical justification (from study §4).** Reversion correlation is strongest near the anchor (h=200 corr ≈ −0.29 → −0.37). v16's linear target has slope K_FV=1 throughout the regime where reversion is strongest. Tanh with `slope_at_origin = CAP / SCALE = 50/25 = 2` doubles aggression where signal is highest, while saturating gracefully past the high-drift band.

**Mechanism.** Replace v16 line ~213:

```python
SCALE = 25.0  # tanh-slope = CAP/SCALE = 2; reaches 80 % cap at dev = 35

if n >= EMA_WARMUP and abs(mid - ema) <= DEV_KILL:
    target = round(CAP * math.tanh((mid - ema) / SCALE))
else:
    target = 0
```

(Add `import math` at top.)

**Parameter choices.**

| Constant | Value | Justification |
|---|---:|---|
| `SCALE` | **25** | Realised mid-deviation std measured at ~25 (study §3 implies 1.29 × √(500-tick window) ≈ 28). Tanh saturates near 1× std → matches the regime where reversion is statistically significant. |
| `CAP` | 50 | Unchanged risk budget. |
| `DEV_KILL` | 100 | Unchanged. Tanh already smoothly bounds, but we keep dev-kill as an emergency brake. |

**Predicted backtest.** +3 to +10 k → **+38 to +45 k / 3 days**. Smaller lift than S2 because the curvature gain near origin is partly offset by gentler accumulation at moderate deviation.

**Risk math.** Identical to v16 (CAP=50 unchanged). Tanh is bounded by construction.

### 2.4 `strat_hg_vAS.py` (S3 — Avellaneda–Stoikov size law)

**Phase C only — run after S2 and S2+S4 are decided.**

**One-line summary.** Keep v16's quote at bb+1 / ba−1; replace the linear `inv_skew` with an A–S-derived asymmetric **size-only** rule.

**Statistical justification (from study §3).** σ²_true = 1.66 / tick measured. With γ = 1/200, the A–S inventory penalty over a horizon of T = 10 000 ticks evaluates to a strong tilt at any |q| > 10 contracts. v16's `INV_MAX_SKEW=4` is a heuristic; A–S derives the same direction with a calibrated magnitude.

**Mechanism (size law form).**

```python
# Avellaneda–Stoikov size tilt. γ = 0.005, T = 10000.
GAMMA   = 0.005
SIGMA2  = 1.66
T_DAY   = 10_000

t_remain = max(1, T_DAY - (state.timestamp // 100) % T_DAY)
penalty  = GAMMA * SIGMA2 * t_remain   # ~83 at t=0; decays linearly to 0 at end of day
# Asymmetric size: pull inventory toward q_target = target.
q_dev   = pos - target
size_tilt = penalty * q_dev / 200.0   # contracts of asymmetry per quote

bsz = max(0, round(QUOTE_SIZE * (1.0 - size_tilt)))
asz = max(0, round(QUOTE_SIZE * (1.0 + size_tilt)))
```

When `q_dev > 0` (over-target long), `size_tilt > 0` → bid gets smaller, ask gets larger → faster mean-reversion of position. Quote price logic (bb+1 / ba−1) is unchanged so book-priority fills are preserved.

**No `INV_MAX_SKEW`.** This rule replaces both v16's `inv_skew` and `OF size-skew`. (The OF flow detector is kept but the mechanism is now A–S-based size tilt, not bid-shifting.)

**Predicted backtest.** Likely **flat to +5 k vs v16** in total, but with **lower MtM variance**. The win is in the structural robustness of the inventory penalty, not in raw PnL.

**Decision rule for promotion (different from S1/S2/S4):** total within −500 of v25_imb_tp **AND** intraday position std reduced ≥ 30 %. If both hold, ship as a defensive variant and combine with v25's TP overlay for a final v26.

**Risk math.** Tighter than v16: the size law is a *continuous* mean-reversion of position toward target, not a piecewise linear one. Position never lingers near the cap as long as the strategy is filling.

---

## 3. Backtest plan

**Standard invocation** (per CLAUDE.md):

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round3/<file>.py 1--2 1--1 1-0
```

(`--no-vis` is omitted so the kevin-fu1 visualizer auto-opens — required for the user-review step in the research-workflow rule.)

**Phase A.** Run two backtests in parallel:

1. `trader_hydrogel_v16_softema.py` (re-run as the current baseline; numbers must match prior +34 683 within rounding).
2. `strat_hg_v24_imbalance.py` (new).
3. `strat_hg_v_tanh.py` (new, independent).

**Comparison table (fill in after running):**

| Variant | Day 0 | Day 1 | Day 2 | Total | Δ vs v16 | Per-day stable? |
|---|---:|---:|---:|---:|---:|---|
| v16 (re-run) | | | | | 0 | — |
| v24_imbalance | | | | | | |
| v_tanh | | | | | | |

**Promotion gates** (both must pass per variant):
- Total ≥ v16 + 2 000.
- Every day ≥ 0 PnL.
- No day < v16_day − 500.

**Phase B (only if v24_imbalance promoted).** Add S4 on top:

| Variant | Day 0 | Day 1 | Day 2 | Total | Δ vs v24_imbalance |
|---|---:|---:|---:|---:|---:|
| v24_imbalance (re-run) | | | | | 0 |
| v25_imb_tp | | | | | |

Same promotion gates.

**Phase C (after Phase B settles).** S3 with its own decision rule (variance ≥ 30 % reduction).

| Variant | Total | per-tick \|pos\| std | Promotion |
|---|---:|---:|---|
| best of {v16, v24, v25} | | | reference |
| vAS | | | promoted iff total within −500 of reference AND pos std reduced ≥ 30 % |

**Aggregate kevin-fu1 visualizer review.** After each phase, open the visualizer for the new candidate side-by-side with the current incumbent. Look for:
1. Day 1 (the high-drift day) — does the candidate avoid v16's worst inventory pile-up?
2. Tick-level fill cadence — has any change inadvertently killed the maker fill rate?
3. Position trace — does CAP=50 stay binding or do excursions stay below it?

Per `feedback_no_local_compare_files.md`: do not generate matplotlib plots or scripts to compare strategies. Use the kevin-fu1 visualizer once per variant and summarise findings in this doc.

---

## 4. Promotion outcomes — what gets shipped

After the four phases, the candidate set is `{v16, v24_imb, v25_imb_tp, v_tanh, vAS}`. The shippable trader is whichever of these passes the **most stringent** promotion bar:

1. Highest total PnL among candidates passing the per-day positivity gate.
2. Tie-break: lowest peak intra-day |pos|.
3. Tie-break: simplest implementation (fewer parameters).

The merged-trader update (`trader_merged_v4.py` or successor) replaces the hydrogel block only with the chosen variant. **VE and voucher logic must remain untouched** (per `feedback_separate_products.md`).

---

## 5. Open questions deferred to post-Phase-A

These are intentionally not addressed in the four candidates above — the candidates are tightly scoped to S1–S4 each in isolation. After Phase A produces data, the following may become tractable:

1. **Should `IMB_THRESH` be tuned?** S2 picks 0.10 from the conditional-expectation table. Raising to 0.15 or 0.20 trades fewer triggers for cleaner signals; lowering to 0.05 trades more triggers for noisier signals. **Do not sweep before Phase A** — pick the cleanest threshold (0.10) and validate first.
2. **Does S2 dominate v_tanh, or are they orthogonal?** They modify disjoint parts of v16 (target function vs quote suppression). If both pass Phase A, build `v_tanh_imb` as a stack and re-test.
3. **Is `TP_POS_THRESH = 30` the right level?** 30 = 60 % of CAP=50. If S4 fires too rarely (< 200 events / 3 days), drop to 20. If too often (> 1 000), raise to 35.
4. **Phase C: does the A–S `T_DAY = 10 000` resetting per day actually help?** Alternative: monotone decreasing penalty over the whole 3-day round. Test only after Phase B settles.

---

## 6. Files to create (checklist)

- [ ] `round3/strat_hg_v24_imbalance.py` (S2)
- [ ] `round3/strat_hg_v25_imb_tp.py` (S2 + S4)
- [ ] `round3/strat_hg_v_tanh.py` (S1)
- [ ] `round3/strat_hg_vAS.py` (S3)
- [ ] **Update this document** with Phase A / B / C result tables once backtests run.

All four files re-use v16's `Logger` class verbatim (per CLAUDE.md). All four use the `try / except ImportError` shim for `datamodel`. None of the four touch any product other than `HYDROGEL_PACK`.

---

## 7. Hard "do not" list

A defensive recap of what this plan explicitly forbids, derived from earlier failure modes:

1. **No hardcoded 10 000 anchor** in any of the four variants. The slow EMA is the only fair-value reference.
2. **No CAP > 50** in any of the four. v9's tail risk was direct consequence of CAP=200.
3. **No taker overlay.** v22 already explored this; the cost of crossing the spread is too high relative to the +0.33 imbalance correlation. Imbalance overlay is *quote suppression*, not taker.
4. **No parameter sweep before per-day positivity is verified** at the conservative defaults. Tuning at this stage is the v9 trap.
5. **No god-strategy file** that mixes all four ideas. One alpha per file until each is independently validated.
6. **No deletion of any v16, v24, v25, v_tanh, vAS file** until the user reviews the kevin-fu1 visualizer for each variant and explicitly approves removal (CLAUDE.md research-workflow rule 5).

---

## 8. Expected end state

After this plan executes:

- Champion strategy: most likely `strat_hg_v25_imb_tp` (S2 + S4 stack) at **~50 k / 3 days** if predictions hold.
- Defensive fallback: `strat_hg_vAS` if it passes its own variance-reduction gate.
- `trader_hydrogel_v16_softema` retained as the safety baseline.
- Total round-3 hydrogel contribution after merge: **~50 k baseline, ~25 k floor**, vs the current v16 contribution of ~35 k. Increment: ~15 k expected, ~10 k pessimistic.
- Tail loss bound: 50 contracts × 100-tick adverse drift = 5 000 SeaShells worst case. Same as v16; CAP unchanged.

Anything above 50 k requires accepting v9-class anchor risk. The research study explicitly does not support that trade.
