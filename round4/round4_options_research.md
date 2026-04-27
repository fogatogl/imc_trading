# Round 4 Options Research — VEV vouchers + VE underlying

**Opened:** 2026-04-27
**Scope:** algo options block only. Hydrogel handled in [`round4_research.md`](round4_research.md). Manual exotics out of scope here.
**Source data:** `dataset/ROUND_4/prices_round_4_day_{1,2,3}.csv` + matching `trades_*` (3 historical days).
**Live R4:** TTE = 4d at start, expiry = 4d later, 4 day-rollovers (10 000 ticks each).

> **Discipline carried in.** Same gates as the hydrogel research (L1–L7 of `round4_research.md` §0).
> Backtest is a *gating filter*, not an optimiser. Any continuous coefficient tuned on 3 days = v9 in disguise.
> One product family per file. Sizing first; signal second. Discrete thresholds beat sigmoids. Structural alpha survives backtest→live; statistical doesn't.

---

## 0. Round 3 closing audit — what to keep, what to kill

R3 submitted [`round3/486411/486411.py`](../round3/486411/486411.py). Options block PnL **+18,933**:

| Strike | R3 PnL |
|--------|------:|
| VEV_5000 | +13,226 |
| VEV_5300 | +8,055 |
| VEV_5100 | +6,085 |
| VEV_5200 | +1,482 |
| VEV_5400 | -96 |
| VEV_5500 | -696 |
| **VEV_4000** | **-2,259** |
| **VEV_4500** | **-6,864** |
| **Sum, K ≥ 5000** | **+28,056** |
| **Sum, K ≤ 4500** | **-9,123** |

### What the R3 block actually did
For each voucher tick:
```
if K <= 5000:                                       # deep ITM branch
    theo = BS(S, K, T, σ_ATM) + MR·(δ·E[ΔS] + ν·(σ_eff − σ_ATM))
else:                                                # OTM branch, K > 5000
    theo = mid + δ_emp · E[ΔS]                       # uses *current* market mid as anchor
take when ask < theo - 1.5  /  bid > theo + 1.5     # discrete edge
```
- σ_ATM = mean of inverted IVs at K∈{5200,5300} (online)
- E[ΔS] = (μ_VE − S) · (1 − e^(−κT)), κ = ln 2 / 30 000 ticks
- σ_eff = σ_ATM · √variance-of-OU-over-T_rem-vs-spot

The OTM branch uses **current option mid** as anchor and only adds drift correction. The ITM branch uses BS as anchor and adds both drift and vega correction. **Neither branch implements gamma scalping** — there is *no* delta hedge against VE in this code. The PnL came from taking against discrete dislocations of `mid` from the anchor as the underlying mean-reverted.

### Why VEV_4500 lost −6,864 (and 4000 lost −2,259)
- For K = 4000/4500: K << S, so BS(S, K, T, σ) ≈ S − K (intrinsic), vega ≈ 0, δ ≈ 1.
- `theo = (S − K) + MR·δ·E[ΔS] + 0`. The MR correction collapses to 1 · E[ΔS] which is **a tiny number** (≤ 1 SeaShell typically).
- So `theo ≈ S − K`. Edge = 1.5. Each fill is essentially a δ=1 directional bet on VE wrapped in an option contract.
- R4 spread on 4500 = **16 ticks** (mean), 4000 = **21 ticks** — wide. R3 had similar. Fills cross deep into the spread → adverse selection: every fill happens at a stale ask that is *about to* track VE.
- Net: a leveraged-VE position with adverse-selection drag. Same in R3 and R4.
- **Verdict: drop VEV_4000 and VEV_4500 entirely.** Removing them recovers +9,123 SeaShells of negative drag without giving up any positive contributor.

### Why the OTM branch worked
- 5200/5300 = peak gamma → biggest mid moves per Δσ, largest "edge" magnitudes
- Spread tight (2–3 ticks) → fills land near fair
- VE mean-reverts slowly inside [5200, 5300] → option mid systematically over/undershoots its OU-drift-corrected equilibrium → reverts → we profit.

This is a **VE-stationarity-driven** strategy, not a vol-mispricing strategy. Worth being explicit about: the R3 alpha source is mean reversion of the *spot*, propagated to the option via δ, not (RV² − IV²)·dt.

---

## 1. R4 microstructure — what changed vs R3

### 1.1 The single biggest change: VE spread blew up

| stat | R3 | R4 |
|------|---:|---:|
| VE bid-ask spread, median | 1 | **5** |
| VE bid-ask spread, mean | ≈ 1.0 | **5.0** |
| VE bid-ask spread, max | 1 | 6 |

R4 day 1/2/3 mean VE spread is 5.0; the spread is at exactly 5 ticks **74 % of all ticks** (22 314 / 30 000), at 6 ticks 18 %, at 1–4 ticks 7 %.

**Why this matters.** Every consequence of "delta-hedge with VE" gets multiplied by ~5×. Round-3-style continuous gamma scalping is dead in the water on R4 data. See §3.

### 1.2 Per-voucher spread + book depth (R4 pooled)

| K | mean spread | median spread | bid_v1 mean | ask_v1 mean | trades n (3d) |
|---|------:|---:|---:|---:|---:|
| 4000 | 20.75 | 21 | 10.92 | 10.91 | 442 |
| 4500 | 15.79 | 16 |  8.95 |  8.95 | **3** |
| 5000 |  5.96 |  6 | 15.54 | 15.67 | **3** |
| 5100 |  4.17 |  4 | 19.55 | 19.57 | **3** |
| 5200 |  2.76 |  3 | 22.81 | 22.81 | 47 |
| 5300 |  1.97 |  2 | 20.51 | 20.54 | 164 |
| 5400 |  1.30 |  1 | 21.91 | 21.88 | 276 |
| 5500 |  1.11 |  1 | 22.28 | 22.28 | 306 |
| 6000 |  1.00 |  1 | 22.49 | 22.49 | 317 (price 0) |
| 6500 |  1.00 |  1 | 15.50 | 15.50 | 317 (price 0) |

**Notes.**
- 5000/5100/4500 each have **3 trades over 3 days** total. The book quotes them, but counterparties barely cross. Treat as nearly untradeable (similar to "dead strikes" — unless WE provide liquidity).
- 6000/6500 trades print at **price 0** (1 105 contracts each over 3 days). All 317 prints are Mark 22 → Mark 01 (single pair). The book mid is 0.5 (ask=1, bid=0); the prints occur at 0 i.e. someone takes the bid. Effectively giveaway flow between two private bots — irrelevant to us; **do not quote these strikes**.
- Active fill-able universe: **5200, 5300, 5400, 5500** (47 / 164 / 276 / 306 trades).

### 1.3 Counterparty footprint on VEV options

Cross-tab of buyers × strikes (3 days pooled):

```
buyer     Mark01  Mark14  Mark22  Mark38   total
VEV_4000      0     232       1     209
VEV_5200     11      33       1       2
VEV_5300    132      30       1       1
VEV_5400    263      13       0       0
VEV_5500    299       7       0       0
VEV_6000    317       0       0       0  (free)
VEV_6500    317       0       0       0  (free)
```
```
seller    Mark14  Mark22  Mark38
VEV_4000     207       2     233
VEV_5200       0      46       1
VEV_5300       0     163       1
VEV_5400       0     276       0
VEV_5500       0     306       0
VEV_6000       0     317       0
VEV_6500       0     317       0
```

**Reading.**
- **Mark 01 = directional OTM-call buyer** (4 636 contracts bought, 0 sold). Concentrated on K ∈ {5300, 5400, 5500, 6000, 6500}.
- **Mark 22 = pure VEV seller** (4 954 sold, 6 bought). LP-like role. Sells across the OTM ladder.
- **Mark 14 / Mark 38** trade VEV_4000 (deep ITM intrinsic) almost exclusively — same dueling pair as on hydrogel; on options they only exchange intrinsic.
- 99 % of OTM voucher prints are the single pair **Mark 01 ↔ Mark 22**. Ours is the 1 % pair ("everyone else"). When we quote inside, we're competing with Mark 22's offers and Mark 01's bids.

### 1.4 CP drift signal — informed-vs-passive on options

For each VEV trade, signed drift in VE underlying after the print (positive = the CP "won" — VE moved in the direction of their option position):

| CP   | side | n    | sgn drift VE t+50 | t+500 | label |
|------|------|-----:|------------------:|------:|-------|
| Mark 01 | BUY VEV | 1 339 | **+0.59** | **+0.96** | mildly informed |
| Mark 22 | SELL VEV | 1 433 | (sgn flipped) +0.56 | +0.89 | uninformed (gets picked off) |
| Mark 14 | BUY VEV | 315 | +0.07 | −1.46 | noise / mixed |
| Mark 14 | SELL VEV | 207 | −0.01 | +0.41 | noise |
| Mark 38 | BUY VEV | 218 | −0.08 | −0.30 | noise |
| Mark 38 | SELL VEV | 238 | −0.25 | +1.73 | noise |

**Interpretation.** Mark 01 and Mark 22 are in the same direction: when Mark 01 buys, VE drifts up afterwards; when Mark 22 sells (same trade, other side), VE drifts up — Mark 22 loses on the call they sold. *Mark 01 picks off Mark 22 on options, just like Mark 14 picks off Mark 38 on hydrogel.*

**Magnitude check (L5 gate).** σ_VE per 50 ticks ≈ 0.33·5247·√(50 / 3.65 M) ≈ 6.1 SeaShells. Drift +0.59 at t+50 = **0.10 σ**. Sub-noise on a 3-day, 1 339-print sample. The sign is consistent with the structural pattern (informed buyer + LP seller) but the magnitude isn't reliably > random in this window.

→ **Use as a *sizing* gate on top of an existing block, not as a fresh signal.** Same conclusion the hydrogel CP analysis reached for Mark 14/38.

---

## 2. The vol surface on R4 — confirming the "flat smile"

### 2.1 IV smile, pooled across 3 days

Brentq inversion of BS(call, S=VE_mid_t, T=TTE_day, σ); cut: extrinsic (= mid − intrinsic) > 2 SeaShells; brent over [1e-4, 5.0].

| K    | day1 (TTE 7d) | day2 (TTE 6d) | day3 (TTE 5d) | pooled IV | n |
|------|------:|------:|------:|------:|---:|
| 5000 | 0.2324 | 0.2352 | 0.2361 | 0.2343 | 24 130 |
| 5100 | 0.2293 | 0.2264 | 0.2244 | 0.2267 | 30 000 |
| 5200 | 0.2355 | 0.2324 | 0.2280 | 0.2320 | 30 000 |
| 5300 | 0.2384 | 0.2370 | 0.2318 | 0.2357 | 30 000 |
| 5400 | 0.2211 | 0.2202 | 0.2208 | 0.2207 | 30 000 |
| 5500 | 0.2404 | 0.2406 | 0.2359 | 0.2396 | 25 266 |

**Pooled cross-strike spread = 1.9 vol-pts** (5400 = 0.221 → 5500 = 0.240). Within-strike day-to-day drift ≈ 0.5 vol-pts. **The smile is flat; the user already knew this and the R3 doc confirmed it.**

The "5400 dip below the level" pattern is identical to R3 (R3 doc §4: "VEV_5400 sits ~1 vol-pt below the others — probably an artefact"). Two rounds in a row → not noise; a real per-strike level shift, but **nothing tradeable across strikes** because the gap is 1–2 vol-pts and within-strike variation is the same magnitude.

### 2.2 Realised vol of VE (two-scale, noise-corrected)

Subsampled annualised vol (1 day = 10 000 ticks, year = 365 days):

| dt (ticks) | σ_annualised |
|---:|---:|
|   1 | 0.4142 |
|   2 | 0.3810 |
|   5 | 0.3527 |
|  10 | 0.3452 |
|  20 | 0.3471 |
|  50 | 0.3370 |
| 100 | 0.3229 |
| 200 | 0.3191 |
| 500 | 0.3227 |

Two-scale fit σ²(dt) = σ²_true + 2η²/dt → intercept σ_true = **0.3302**.
Per-day at dt=200: day1 0.3190 / day2 0.3137 / day3 0.3245. **Stable across days.**

### 2.3 The RV–IV gap

| measure | value |
|---|---:|
| σ_real (de-noised) | **0.330** |
| σ_implied (cross-strike pooled) | **0.230** |
| **gap** | **+0.100 vol-pts** |

**This is the alpha the Discord mod is pointing at.** Market consistently underprices vol by ~10 vol-pts on R4 historical days. With ATM vega ≈ 200 SS / vol-pt, the theoretical edge per voucher held to expiry is ≈ 200 × 0.10 = **20 SS per ATM voucher**, or ~6 000 SS per strike at the 300-position limit, or ~12–15 k across the active 5200–5500 ladder.

**But — see §3. The naïve gamma-scalp route to capture this gap dies on the VE bid-ask.**

---

## 3. Why textbook gamma scalping is dead on R4

Pathwise simulation: long 1 VEV_K call, delta-hedge with VE every 10 ticks using σ_hedge for delta calculation, charge VE_spread / 2 = 2.5 SS per unit of underlying traded.

**Pure gamma capture, no hedge cost (DOWN=10):**

| K   | GS PnL over 3d (1 contract) |
|-----|---:|
| 5000 |  7.45 |
| 5100 |  8.31 |
| 5200 |  8.85 |
| 5300 |  9.28 |
| 5400 | 10.32 |
| 5500 |  6.31 |

Consistent with the +0.10 vol-pt theoretical (~17 SS per 4 days × 3/4 ≈ 13 SS per 3 days, observed 9 — same ballpark, modest model-vs-empirical slippage from quantisation/IV drift).

**Net of VE-spread hedge cost @ DOWN=10:**

| K | GS gross | VE hedge cost | net |
|---|---:|---:|---:|
| 5000 |  +7.45 | -15.56 |  -8.12 |
| 5100 |  +8.31 | -26.44 | -18.12 |
| 5200 |  +8.85 | -34.27 | **-25.41** |
| 5300 |  +9.28 | -34.35 | **-25.06** |
| 5400 | +10.32 | -27.04 | -16.71 |
| 5500 |  +6.31 | -17.01 | -10.70 |

**Hedge-band sweep** (rebalance only when |Δ_drift| > BAND, σ_hedge=0.23):

| K | b=0.05 | b=0.10 | b=0.20 | b=0.50 | no rebal |
|---|---:|---:|---:|---:|---:|
| 5100 | -4.94 | -14.61 | -15.06 | -15.06 | -22.00 |
| 5200 | -1.52 | +0.37  | -13.00 | -15.98 | -24.50 |
| 5300 | +2.23 | +7.86  | -11.85 | +11.41 | -20.50 |
| 5400 | -0.29 | -8.33  |  -4.63 | -11.00 | -11.00 |
| 5500 | -5.10 | -4.86  |  -6.00 |  -6.00 |  -6.00 |

The b=0.50 column for 5300 (+11.41) and the no-rebal results are **single-realization noise on a 3-day window**, not a strategy. (The VE direction across 3 days is not zero, so an unhedged long 5300 picked up an accidental +11. On a different 3-day window, sign flips. L5 / L7.)

**Verdict.** Continuous delta-hedged gamma scalping does not survive R4 hedge cost. The theoretical +20 SS / voucher edge is real *as a static expected value* but cannot be extracted via tick-by-tick rebalancing.

→ **L1 (simplest model that fits the regime): the regime here is "high RV, high spread cost". Gamma-scalp model doesn't fit. Don't force it.**

---

## 4. Strategies available with calls + underlying only

What the option ladder + VE permits, structurally:

| # | Strategy | Greek profile | Best at | Risk |
|---|----------|---------------|---------|------|
| A | Long-call gamma scalp (continuous Δ-hedge) | +γ +ν −θ Δ-flat | RV >> IV with low hedge cost | **Dead on R4 (§3)** — VE spread = 5 |
| B | Hold-to-expiry vol bet (long calls, one-shot Δ-hedge at entry) | +γ +ν −θ initially Δ-flat | RV >> IV with bounded TTE | High path variance, single 4-day realization |
| C | Maker-only on tight-spread strikes (5400, 5500) | small/balanced | Capturing 1-tick spread, no vol view | Adverse fill from Mark 01 |
| D | Per-strike mid-mean-reversion (R3 OTM branch reframed) | bounded Δ, near-zero ν | VE stationary, anchor stable | Stationarity assumption — verify online |
| E | Vertical bull call spread (long ATM, short OTM) | +Δ small +ν reduced | Cap risk on directional view; not a vol harvester | Low edge magnitude |
| F | Inverse butterfly (short 5200 + short 5400 + 2× long 5300) | +ν, ~Δ flat near ATM | Concentrate vega without naked long premium | Pin risk near 5300 at expiry |
| G | Synthetic straddle (2× long ATM call − 1× VE) | +γ +ν +θ-paying, Δ-flat at S=K | Pure vega/gamma exposure when Δ=0.5 | Same hedge-cost problem as A |
| H | Cross-strike vega arb (long 5400 vs short 5300 if 5400 IV stays cheap) | net ν-neutral, Δ-flat | Smile flat-but-non-monotone | 1.5 vol-pt edge below within-strike noise |

### Per-strategy assessment for R4

**A — Continuous gamma scalp.** Killed by §3.

**B — Hold-to-expiry vol bet.** TTE=4d means we can actually hold to expiry within the round.
- Per-voucher expected gain ≈ vega × Δσ = 200 × 0.10 ≈ 20 SS per ATM
- Total expected at full position: ~12–15 k SS across 5200/5300/5400 ladder
- Realized variance: payoff std ~ vega × σ_real × √T / N^{1/2} ≈ huge for a single realization
- **Risk:** if VE drops 30 SS in 4 days (within historical range), 5300 expires worthless = loss of premium 41 × 300 = 12 300. Bilateral exposure too big without delta hedging.
- **One-shot delta hedge at entry** mitigates: pay VE_spread/2 × Σ Δ once. For a balanced ATM/OTM portfolio (5200+5300+5400+5500), Σ Δ ≈ 0.65+0.34+0.12+0.03 = 1.14 per quartet. At 300 contracts × 1.14 = 342 VE units to short × 2.5 spread/2 cost = **~430 SeaShells of one-time hedge cost** for the entire portfolio. Negligible vs the +12k expected.
- **Re-hedging cadence: not at every tick. Once or twice per day is enough for a stationary underlying.** Compute the optimal cadence from §3-style sweeps with the ACTUAL portfolio Δ-drift.
- **Verdict: this is the single strongest candidate. Test next.**

**C — Maker on 5400 / 5500 (tight 1-tick spread).** Quote 1 inside the bid/ask at theo ± 0.5. Capture small repeated edges. No hedging if positions stay bounded around 0.
- 5400: 276 trades, 5500: 306 trades over 3 days. ≈ 100/day fill opportunities each. With 0.5 SS edge per round-trip × ~50 round-trips/day × 2 strikes = ~50 SS/day = ~200 SS over 4 days. Marginal.
- Bigger as a *risk-control layer* than a primary alpha source.
- **Verdict: keep as low-priority overlay.**

**D — Per-strike mid mean-reversion (R3 OTM branch).** Anchor each strike to its own slow-moving fair (e.g., per-strike rolling mean or per-strike-IV-anchored BS). Trade reversion of mid → anchor.
- Already what the R3 OTM branch does, with OU drift correction.
- VE stationary in [5191, 5300] × per-day means {5248, 5255, 5239} = stationary daily; small day-to-day shifts.
- **Verdict: start here. This is what worked in R3 (+18 933 minus 9 123 from deep-ITM = +28 056 across 5000–5500). Carry forward, drop the deep-ITM branch.**

**E — Vertical spreads.** Defensive only. No standalone alpha.

**F — Inverse butterfly.** Conceptually attractive (long vol, near-Δ-neutral) but on R4:
- 5200 spread 3 + 5400 spread 1 + 2 × 5300 spread 2 = ~8 ticks of round-trip cost
- Theoretical vega ≈ 2·vega_5300 − vega_5200 − vega_5400 = 2·202 − 203 − 110 = +91 SS per fly
- Edge ≈ 91 × 0.10 = 9 SS per fly, vs 8 SS spread cost. Almost wash.
- **Verdict: not promising.**

**G — Synthetic straddle (2 calls − 1 underlying).** Same hedge-cost problem as A; the long-vol exposure has to be either hedged dynamically (dies) or held (becomes B in disguise).

**H — Cross-strike vega arb.** 5400 vs 5300: 1.5 vol-pt gap × vega 110 ≈ 1.65 SS per pair. Within-strike day-to-day IV variation ≈ 0.5 vol-pts × vega ≈ 1 SS — same order as the signal. **Verdict: not a viable standalone trade.**

---

## 5. Recommended R4 options-only direction (research only — no code yet)

### 5.1 Net-delta proposal

**Phase 1 — Baseline: R3 OTM branch verbatim, deep-ITM dropped.**

Take the R3 voucher block (`round3/486411/486411.py` lines ~309–387) and:
1. **Remove K ≤ 5000 entirely** from `OPTIONS`. Drop VEV_4000, VEV_4500, VEV_5000, VEV_5100. Trade only K ∈ {5200, 5300, 5400, 5500}.
   - VEV_4000 / 4500: zero extrinsic, big spread, deterministic loss (§0).
   - VEV_5000: 3 trades in 3 days — book is quoted but no flow. Ours wouldn't fill either. Removing it costs ~0.
   - VEV_5100: same — 3 trades over 3 days.
2. **Initialise `T_rem` for TTE = 4 days** (was 5d in R3 spec, R4 starts at 4d).
3. Keep σ_ATM online inversion at K∈{5200,5300}.
4. Keep `EDGE = 1.5`, `OPT_TAKE_CAP = 30`.
5. Don't add any new continuous coefficient. (L7 — no parameter sweeps on 3 days.)

Backtest this baseline first. Gating expectations:
- Should reproduce roughly +28 k that the K ≥ 5000 strikes contributed in R3 (scaled for whatever R4 day-by-day variation produces).
- If it loses on day 3 specifically, the OU half-life or σ_ATM may need to be rechecked at TTE=4d. Don't tune; just record the failure mode for phase 2.

**Phase 2 — Test "B" (hold-to-expiry vol bet) as a layered overlay.**

At round start (tick 0), compute portfolio premium for a target basket {5200: 100, 5300: 100, 5400: 100, 5500: 50} contracts long.
- Pay aggregate premium ≈ 100·90 + 100·40 + 100·12 + 50·5 = 13 700 SS.
- Compute aggregate Δ ≈ 100·0.65 + 100·0.34 + 100·0.12 + 50·0.03 = 113 ⇒ short 113 VE, paid 113 × 2.5 ≈ 280 SS spread cost.
- Hold position fixed. Re-hedge VE only at end of each trading day (3 rebalances × 30 VE each ≈ 220 SS spread cost over the round).
- Expected payoff at expiry assuming σ_real = 0.33: BS(σ=0.33) − BS(σ=0.235) per voucher ≈ +18 SS for ATM, +6 for 5500.
- Expected total = 100·18 + 100·18 + 100·8 + 50·3 = +4 550 SS gross; ≈ +4 050 SS net after total ≈ 500 SS hedge cost.
- Compare against phase-1 baseline backtest. Promote only if it adds material PnL with *bounded* worst-case across days (L5).

**Phase 3 — Maker overlay on 5400, 5500 (low priority).**

Only if phases 1+2 leave headroom. Skip if not needed.

### 5.2 What NOT to do

| Anti-pattern | Why |
|--------------|-----|
| Continuous Δ-rebalanced gamma scalp | §3 — VE spread (×5 vs R3) eats the entire RV-IV gap |
| Per-counterparty regression (Mark 01 / Mark 22 weighted alpha) | §1.4 — drift signal sub-noise on 3-day sample. v9 archetype. |
| Smile-skew arb (long 5400, short 5300 etc.) | §2.1 — gap 1.5 vol-pts within within-strike noise |
| Tuning OU half-life or σ_eff coefficients on R4 backtest | L7 — 3-day window can't rank close variants |
| Adding a "vol regime detector" toggle | L1 — RV is stable across 3 days at 0.32–0.33; no regime to detect |
| Re-introducing VEV_4000 / VEV_4500 with a "smarter pricer" | They are intrinsic-only; no edge to extract that is not already a directional VE bet wearing a costume |

### 5.3 Open questions (resolved before any code)

1. **TTE convention sanity.** R3 doc §12 already flagged this. CLAUDE.md says R4 starts at TTE = 4d. Verify by inspecting `state.timestamp` rollovers in the first live ticks; the round-3 strategy auto-detects via `opt_prev_ts` jumps and increments `opt_days`. Unchanged in R4 — still works as long as TTE init is 4d not 5d.
2. **σ_ATM stability at TTE = 4d.** Historical R4 days run 7d→6d→5d. Live round runs 4d→3d→2d→1d. We have no data at TTE ≤ 4d. Smiles steepen near expiry; per-strike IV may diverge from the 0.22–0.24 historical band. Plan a sanity print on the first 1 000 live ticks before letting the strategy take aggressively; circuit-break if `σ_ATM` exits a sane range (e.g., [0.10, 0.45]).
3. **Phase 2 portfolio sizing.** The proposed {100, 100, 100, 50} basket is an illustration, not a tuned figure. Decide based on (a) total premium-at-risk budget and (b) expected payoff-vs-variance ratio. Don't tune to maximise a 3-day backtest number.
4. **Fill realism.** The R3 backtester uses `worse` mode — fills only when historical print is strictly through your quote. The phase-1 strategy is a taker against thin OTM books. Confirm we're still capturing fills with VEV_5500 trade count = 306 over 3 days (most of these are Mark 01 ↔ Mark 22 private; we may not see them).

---

## 6. North star

> **The R3 voucher PnL came from VE-stationarity propagated through δ. The flat smile means smile-arb is dead. The +0.10 vol-pt RV-IV gap is real but the VE bid-ask makes continuous gamma-scalp un-extractable. The cleanest R4 options block is: R3's OTM branch verbatim with deep-ITM dropped, optionally layered with a one-shot hold-to-expiry vol position.**
>
> If a new file in `round4/` has more than ~150 lines or sweeps a parameter against backtest PnL, it has stopped being research and started being v9.
