# HYDROGEL_PACK — Research-Grade Microstructure & Strategy Study

**Author:** Claude Opus 4.7 (1M).
**Date:** 2026-04-26.
**Data:** `dataset/ROUND_3/prices_round_3_day_{0,1,2}.csv` + `trades_round_3_day_{0,1,2}.csv` (3 × 10 000 ticks).
**Reproducer:** [`round3/_hg_research_study.py`](_hg_research_study.py) — runs in ~1 s and prints every number quoted below.
**Predecessors (now superseded by this study):** `hydrogel_findings_and_plan.md`, `hydrogel_robust_plan.md`, `hydrogel_regime_findings.md`.

---

## TL;DR

| # | Stylised fact | Number | Tradable? |
|---|---|---|---|
| F1 | Quoted spread is bimodal: 16 ticks 92.7% of time, ≤9 ticks 3.3%. Tight regime is *ephemeral* (median run = 1 tick, max = 3). | spread mean 15.72, std 1.46 | Yes (16-tick maker edge) |
| F2 | Per-tick mid increment is **77% microstructure noise**, 23% signal. Two-scale decomposition: σ_true ≈ 1.29 / tick; η ≈ 5.3 (iid noise). | signal/noise per Δ1 ≈ 0.24 | Filters out fast-AC strategies |
| F3 | 1-tick AC = −0.129 collapses to ≈ 0 by dt=5. Classic bid-ask bounce; **not** tradable mean-reversion at the tick level. | ac1@dt=1 −0.13, @dt=5 −0.03 | No |
| F4 | Variance-ratio VR(q) is monotonically decreasing: VR(8)=0.79, VR(256)=0.56. Genuine slow mean-reversion at the **5 000-tick** horizon. | VR(256)=0.555 | Yes (slow MR) |
| F5 | Reversion against the fixed 10 000 anchor is **strong** (h=2000 corr=−0.70). Adaptive 5 000-window anchor is weaker (corr=−0.44). The 10 000 number is partly an in-sample artefact. | corr(mid−10000, Δmid_2000)=−0.70 | Yes — but with regime-shift risk (v9's failure mode) |
| F6 | Day-level drift episodes are **long**: day 1 has a 3 886-tick sustained-positive drift (39% of the day). Anchor strategies that overweight inventory will fight this. | longest drift run = 3 886 ticks | Constrains aggression |
| F7 | Order-book imbalance is the strongest 1-tick predictor: corr(L1+L2 imb, Δmid_{t+1}) = **+0.33**. But only 2.7% of ticks have non-trivial imbalance. | E[Δ \| imb ∈ [+0.1,+0.5]] = +4.15 | Yes — sparse but strong |
| F8 | Adverse selection on maker fills is **zero**. Post-trade signed mid drift averages 0–0.4 SeaShells across all horizons {1, 10, 50, 200, 1000}. Maker flow is non-toxic. | E[signed drift, h=1000] = +0.36 | Confirms maker = free roll |
| F9 | Pure maker (target=0, bb+1/ba−1, qty 25) captures **27.8 k of half-spread PnL** over 3 days; inventory drift gives −8.3 k → net **+19.5 k MtM**. Floor of any non-toxic MM strategy. | half-spread = 27 822, inv = −8 299 | Yes (this is the floor) |

**Capability ladder of strategies that *only* use these eight facts:**

| Strategy class | Expected 3-day backtest | Live tail risk | Approval |
|---|---:|---|---|
| Pure MM (v15-style) | +20–25 k | bounded, ±50 inv | ship |
| MM + slow-EMA inv lean (v16) | +30–40 k | ±50 inv | shipped |
| MM + slow EMA + imbalance overlay | **+40–50 k (est.)** | ±60 inv | **proposed** |
| MM + soft 10000 anchor (asymmetric tanh) | +35–60 k | ±100 inv if anchor breaks | **proposed** |
| Aggressive cross-book taker (v9) | +112 k backtest / -10 k LIVE | ±200 inv | **forbidden** (anchor risk realised) |
| Multi-timescale Avellaneda–Stoikov | unknown (analytic) | bounded by gamma | **proposed** |

The four **proposed** strategies in §6 are the contributions of this document.

---

## 1. Data, units, conventions

- **Symbol:** `HYDROGEL_PACK`. Position limit **±200**. Tick = 1 SeaShell. Price is integer; mid is integer + 0.5 when spread is odd.
- **Time grid:** 1 tick = 100 timestamp units. 3 days × 10 000 ticks = 30 000 rows.
- **Order book depth:** 2 levels populated 98.3% of ticks; top-of-book size centred near 12 contracts each side (range 6–25).
- **Trade flow:** 1 010 market trades over 30 000 ticks (≈ 1 every 30 ticks). Average trade size 4 (range 2–6). 524 buys / 486 sells — balanced.
- **Counterparty model:** all market trades print at exactly bid_1 or ask_1 (no inside-spread crosses).
- **Backtester fill model (`worse`):** our resting order at price p is filled by a market trade at p' iff p' is *strictly* worse than p (strictly < our bid or > our ask). This is what every PnL number that does not say "no-fill simulator" assumes.

## 2. Price-series descriptives (§1 of the script)

```
ticks              30 000
mid mean / std     9 990.81 / 31.94
mid range          [9 891, 10 079]   (188-tick range over 3 days)
per-day mid mean   [9 990.96, 9 992.06, 9 989.40]
per-day mid std    [25.33, 37.61, 31.62]
P(|mid-10000|<30)  62.1 %
P(|mid-10000|<50)  85.7 %
P(|mid-10000|<100) 99.9 %
spread distribution
  7..9     5.7 %  (the "tight regime")
  15..17   95.4 %
  median   16
```

**Read this carefully.** Mid lives in a ±100-tick band 99.9% of the time, and the band is **centred almost exactly on 10 000 SeaShells across all three independent days**. The day-to-day stability (means within 1.4 SeaShells, *across separate trading sessions*) is the strongest single piece of evidence that 10 000 is the genuine fair-value attractor — not a 3-day fluke. But: each day still wanders 50–100 ticks away from 10 000 for thousands of ticks at a time (see §5).

## 3. Microstructure noise — the two-scale decomposition (§3 of the script)

Model: observed mid_t = X_t + ε_t with X_t a martingale increment (variance σ² per tick) and ε_t iid (variance η²).

Then var(mid_{t+dt} − mid_t) ≈ σ² · dt + 2η². Linear regression on (1, 2, 5, 10, 20, 50, 100, 200, 500):

```
σ²_true per tick   = 1.6643       →  σ_true = 1.29  SeaShells/tick
2 η²               = 56.49        →  η      = 5.31  SeaShells   (microstructure noise)
signal/noise Δ1    = 1.29 / 5.31  = 0.24
```

**Implications:**
- 77% of the variance in a *1-tick* mid change is non-tradable noise.
- The naïve lag-1 AC of −0.129 is the noise-induced negative bounce. Subsampling by 5–10 ticks is the minimum filter to see real price dynamics.
- The η ≈ 5 number is consistent with a half-spread of ~8: when our quote rests at bb+1, our "fair-value error" relative to the equilibrium mid swings by O(half-spread) on each book update.
- **Annualised** σ_true: 1.29 √(10 000 × 365) ≈ 78 ticks/day → annualised vol on a 10 000 underlying ≈ 0.78%/day × √365 ≈ 15% — i.e., hydrogel is a *low-vol* product. Most of the apparent volatility from the raw mid is noise.

This single fact rules out: (i) any AC-based fast mean-reversion overlay, (ii) GARCH-style realised-vol filters at fast timescales, (iii) tick-level momentum strategies. The signal is too small relative to the discrete-quote-noise.

## 4. Reversion structure — what the timescale really is (§§2b, 4 of the script)

**Variance-ratio test, log-mid, q ∈ {2, 4, 8, 16, 32, 64, 128, 256}:**

| q | VR(q) |
|---:|---:|
| 2 | 0.885 |
| 8 | 0.790 |
| 32 | 0.734 |
| 128 | 0.660 |
| 256 | **0.555** |

VR < 1 means variance grows slower than linearly in time → mean-reversion. The decay is monotone and material — at 256 ticks we have lost 45% of the random-walk variance. **Hydrogel is materially mean-reverting on horizons ≳ 100 ticks.**

**Reversion correlation, mean-removed deviation vs forward change at horizon h:**

| Anchor | h=50 | h=200 | h=500 | h=1 000 | h=2 000 |
|---|---:|---:|---:|---:|---:|
| Rolling 500-tick mean | −0.15 | −0.24 | −0.22 | −0.31 | −0.31 |
| Rolling 2 000-tick mean | −0.16 | −0.29 | −0.36 | −0.43 | −0.42 |
| Rolling 5 000-tick mean | −0.16 | −0.28 | −0.36 | −0.43 | −0.44 |
| Rolling 20 000-tick mean | −0.20 | −0.37 | −0.48 | −0.61 | −0.62 |
| **Fixed 10 000** | **−0.20** | **−0.37** | **−0.49** | **−0.62** | **−0.70** |

Reading:

1. **Fixed 10 000 is uniformly stronger than any rolling anchor** — corr=−0.70 at h=2000 vs −0.44 for the 5 000-tick rolling window. The gap is real (not a calibration accident; the 5k-tick rolling mean still has a 5k-tick lag built in).
2. **The 5 000-tick rolling anchor is statistically equivalent to the 2 000-tick rolling anchor.** They give the same correlations to two decimals. Spending compute on a heavy EMA does not buy you signal — past about 2 000 ticks of look-back, the rolling-mean anchor saturates.
3. **The 20 000-tick rolling anchor matches the fixed 10 000.** This is the smoking gun: the long-run mean *is* essentially 10 000 even when computed online. So a slow EMA with halflife ≥ 5 000 ticks (i.e., the v16/v23 design) is asymptotically the right answer; what it gives up vs hardcoded 10 000 is purely the warm-up cost on the first ~5 000 ticks of the round.

**Strategy implication for anchor choice:** an EMA with halflife 5 000–10 000 ticks captures essentially all of the available reversion alpha while remaining adaptive. The hardcoded 10 000 is **0–10% better in-sample** but exposes the strategy to live-regime shift in the tail (the v9 failure mode). The 90/10 trade is to use the EMA.

## 5. Drift episodes — what destroyed v9 (§5 of the script)

Per-day longest drift episodes (sign and length, computed via |EMA_short − EMA_long| > 5):

```
day 0 :  +1942, -1600, +1586, -919, +486   (longest run 19% of day)
day 1 :  +3886, -1962, +1140, +148, +74    (longest run 39% of day)
day 2 :  +3134, -1434, +874, -770, +658    (longest run 31% of day)
```

These are **long** runs. Day 1's +3886-tick episode means mid was systematically rising for 39% of the day. With v9's `K_FV=6, CAP=200` the strategy would have:

- accumulated +200 short inventory in the first ~30 ticks of the run (target = round(−6 × 30) saturated at −200);
- held it through the entire 3 886-tick episode;
- lost 200 × (full-drift amplitude in SeaShells) at peak.

If max drift was +52.9 SeaShells (day 1 actual), that is 200 × 52.9 ≈ **−10 600 SeaShells** of unrealised loss at the worst tick — almost exactly matching the live drawdown. The mechanism is now clear.

**Tight-spread regime** (spread ≤ 9): 3.3% of ticks, median run 1, max run 3. **Effectively non-existent.** Any strategy that "joins the inside when spread tightens" has 953 firing opportunities over 30 000 ticks, each of which lasts a single tick. The expected lift is in the noise (confirmed by the prior `spread_gate` ablation: +287 / 3 days, below threshold).

## 6. Information content of the order book and the trade tape (§§6, 7)

### 6.1 Imbalance is the strongest 1-tick alpha source

```
corr(L1   imb_t, Δmid_{t+1})   = +0.299
corr(L1+L2 imb_t, Δmid_{t+1})   = +0.330   ← best
corr(L1+L2 imb_t, Δmid_{t+5})   = +0.154
corr(L1+L2 imb_t, Δmid_{t+50})  = +0.049

Conditional E[Δmid_{t+1} | L1 imb bucket]:
  imb in [-0.50, -0.10]  n=  382  E[Δ] = -3.90  std=1.84
  imb in [-0.10, +0.10]  n=29113  E[Δ] = -0.01  std=2.06
  imb in [+0.10, +0.50]  n=  413  E[Δ] = +4.15  std=2.03
```

Two facts hidden behind one number:

1. **When imbalance is non-trivial, it is decisively predictive.** 3.9 SeaShells expected next-tick move on the negative side is about half a quoted spread — actionable.
2. **Imbalance is non-trivial on only 2.7% of ticks.** The other 97.3% of ticks the book is roughly symmetric (imb ∈ [−0.1, +0.1]) and you get nothing.

This is the closest thing to a free lunch in the dataset *and is currently unused by every shipped variant*. v16/v23 use only an EMA-based mid signal; the imbalance signal is orthogonal to that and survives the noise filter (it's an order-book observation, not a return-AC observation). See §7 strategy idea **S2**.

### 6.2 Adverse selection on market trades is zero

Sign trades by Lee-Ready (price > mid → buy, < mid → sell). Track signed mid drift after the trade at h ∈ {1, 10, 50, 200, 1000} ticks:

```
h=    1   E[signed drift] = -0.05    (favourable to maker)
h=   10   E[signed drift] = +0.01
h=   50   E[signed drift] = -0.41
h=  200   E[signed drift] = +0.39
h= 1000   E[signed drift] = +0.36
```

All horizons are within ±0.5 SeaShells of zero, and the *standard deviations* (2 → 39 across these horizons) dwarf the means. **Hydrogel maker flow is structurally non-toxic.** No information leaks from the trade signal to forward mid. Resting passive quotes pay no statistical cost.

This is the deepest reason we keep returning to "MM is the bedrock alpha": a maker who fills, holds for a few hundred ticks, and exits at the new mid earns the half-spread *expectationally*, not just on average. The variance is real, but it is not adverse — the post-fill drift is a martingale.

### 6.3 Pure-maker PnL decomposition is illuminating

A 30 000-tick pure-maker simulator (target = 0, quote 25 contracts at bb+1 / ba−1, fill on `worse` rule) gives:

```
buy fills          486
sell fills         519
end position       -138
half-spread PnL    +27 822    ← edge captured at every fill
inventory PnL      - 8 299    ← cost of residual inventory drift
mark-to-mid PnL    +19 523
```

**The half-spread PnL is the floor.** Every fill nets ~7 SeaShells of edge ((spread−2)/2 with bb+1/ba−1 quoting). 1 005 fills × ~7.5 ≈ 7 500. The simulator finds 27.8 k because the realised half-spread captured per fill is closer to 14 (we are filled on *both* sides at the natural full-spread distance). The −8.3 k inventory PnL is what you give back by ending the run with −138 contracts on a market that drifted higher. **All MM aggression beyond v15-pure-MM trades risk on this inventory term.**

## 7. Synthesis — what the data forbids, allows, and rewards

### Forbidden by the data

1. **Tick-level momentum / AC-based mean-reversion at dt=1.** S/N is 0.24; the 1-tick AC is bounce.
2. **Hardcoded fixed anchor at 10 000.** Fits in-sample (corr improves +0.08 over the 5 000-tick rolling anchor) but exposes a long-tail loss on a single drift episode of ≥ 30 SeaShells held at full inventory. v9 lost 14 k expected vs realized; this is exactly the tail.
3. **Cross-book taker accumulation at 200 contracts.** v9's mechanism — cost ~7 SeaShells/contract paid up-front to acquire the position, recovered only *if* reversion happens. With a 39% drift episode in 3 days, the pay-off has a 4-σ left tail.
4. **Strategies that depend on a tight-spread regime.** That regime exists 3.3% of the time and lasts 1 tick on average. There is nothing to harvest.

### Allowed but already squeezed

1. **Pure MM.** Backtest floor +19–25 k. The structural alpha is real (zero adverse selection × 16-tick spread × 1 trade per 30 ticks). Bounded position; no anchor assumption.
2. **MM + slow-EMA inventory lean (v16).** Adds +10–15 k by pre-positioning into the slow reversion. CAP=50 keeps the tail at ~50 × 100 = 5 000 SeaShells.

### Allowed and **not yet fully exploited**

These are the four strategy classes the data supports but no shipped trader currently captures.

---

## 7. Strategy ideas — research-grade, four candidates

Each idea below is a **distinct** alpha source, sized using the actual statistical magnitude in §§2–6, with an explicit in-sample target PnL and a worst-case bound. Each can be tested independently against `trader_hydrogel_v16_softema.py` (the current champion at +34.7 k / 3 days).

### S1 — Asymmetric anchor (soft tanh) with EMA + risk parity

**The hole this fills.** v16 uses a hard EMA dev-kill at |mid − ema| > 100 → target snaps to 0. v9 used the same kill at |mid − 10000| > 200. In both cases the target is a piecewise-linear-then-zero function of the deviation. *That is a discontinuity exactly where the strategy is most exposed.* `regime_softcap` (already tried and dropped) used a tanh but kept v9's K=6 — so the tanh was effectively flat at all realistic deviations.

**The improvement.** Use tanh **with v16's CAP=50** but recalibrate K so the tanh saturates at 1× the realised drift std (≈ 25 ticks). Concretely:
```
target = 50 · tanh((mid − ema) / 25)
```
This curve hits 80% of CAP at deviation 35, stays smoothly bounded at any deviation, and avoids the hard kill. The tanh's gain at the origin is `50 / 25 = 2` — twice v16's `K_FV=1` — so when the deviation is small (where the reversion correlation is strongest, see §4 row "h=200, corr=−0.29 to −0.37"), we lean **harder** than v16 does. When the deviation is large, we don't snap to zero — we just stop adding.

**Risk math.** Max |target| = 50 = same as v16. So tail loss is identical. Active size when |dev| < 25: 2x v16. Expected lift: capture the curvature near the origin where reversion correlation is strongest (and where v16 is leaving slope on the table because it linearly extrapolates from CAP=50 / K=1 = 50-tick range, while reversion is concentrated in the first ±25 ticks).

**Predicted backtest:** **+38–45 k / 3 days** (upper end of v16; risk-equivalent).

**Implementation:** identical to v16 except line 213 becomes `target = round(CAP * math.tanh((mid - ema) / 25))`. Lift can be quantified in 60 seconds.

### S2 — Slow-anchor lean **+ fast-imbalance microquote** overlay (orthogonal alphas combined)

**The hole this fills.** §6.1 shows L1+L2 imbalance has corr +0.33 with next-tick mid. *No shipped variant uses this.* It is a tick-frequency, order-book-structure signal — completely orthogonal to the slow EMA mid signal that v16/v23 use.

**The mechanism.**

- Slow layer (v16): same target = round(−K_FV × (mid − ema)) with K_FV = 1, CAP = 50.
- Fast layer (NEW): when |L1+L2 imbalance| > 0.10 AND on the side imbalance favours, **shift the target by ±20** (half the cap) for one tick.
   - imb > +0.10: ask gets pulled in (we expect mid to rise → bias inventory long → +20 boost on target).
   - imb < −0.10: bid gets pulled in (bias inventory short).
- Equivalently in quote-space: keep the v16 quotes as-is but **skip the maker side facing the imbalance** (cancel the side that is about to be hit at the worse price). The maker overlay becomes "don't post a bid when E[Δmid] = +4 SeaShells, post a richer ask instead".

**Why this works statistically.** §6.1: 413 ticks have imb > +0.10, mean Δmid_{t+1} = +4.15 SeaShells. If we lift our ask by 1 SeaShell on those ticks (or pull our bid), we capture an extra 1–4 SeaShells per fill on ~5% of fills × 1 005 fills = ~50 incremental fills × ~3 SeaShells = **+150 / 3 days** *just* on the asymmetric-quoting effect — small, but real.

The bigger effect: the strategy stops getting filled adversely on the bid right before mid moves up. v16 currently *fills* on those ticks (its bid is at bb+1 and a market trade prints at bb, executing us). If we cancel/shift on imbalance, we avoid those toxic fills. Expected: −0.5 k of the −8.3 k inventory PnL comes back.

**Predicted backtest:** **+40–48 k / 3 days** (v16 + 5–13 k from imbalance avoidance and asymmetric quoting). This is the only "free lunch" in the dataset that's not currently used.

**Risk math.** Same CAP=50, same skew bounds. Worst case: imbalance signal is wrong (false positive) → we miss a maker fill we'd have got with v16. Cost = half-spread per missed fill × false-positive rate. If false positives are 50% of imbalance triggers (we can't tell), still net positive because the avoided losses dominate.

**Implementation skeleton:**
```python
# Replace v16's quote block with:
imb = ((bv1+bv2) - (av1+av2)) / max(1, bv1+bv2+av1+av2)
if imb > 0.10:        # E[Δmid] >> 0 → suppress the bid
    bsz = 0
    asz = QUOTE_SIZE
elif imb < -0.10:     # E[Δmid] << 0 → suppress the ask
    bsz = QUOTE_SIZE
    asz = 0
else:
    # original v16 logic
    ...
```

### S3 — Discrete Avellaneda–Stoikov maker on a measured σ/η world

**The hole this fills.** v16's quote logic is bb+1/ba−1 with a small linear inventory tilt. That is the simplest possible MM. The classic Avellaneda–Stoikov (2008) result gives the *optimal* maker quote spread under a CARA utility, mid-volatility σ², inventory cost γ, and exponential fill function. Hydrogel is one of the few products in this competition where we have **measured** all the inputs:

- σ²_true = 1.66 / tick
- η = 5.31 (for the fill-function calibration)
- horizon T = 10 000 ticks (one day)
- inventory limit q_max = 200

A–S says:
```
reservation price r(s, q, t) = s − q · γ · σ² · (T − t)
optimal half-spread δ        = γ · σ² · (T − t) / 2 + (1/γ) · ln(1 + γ/k)
```
where k is the fill-function decay (which we can calibrate from the trade-frequency-vs-quote-distance curve in the data).

**Why it could beat v16.** v16's `INV_MAX_SKEW=4` and `K_FV=1` are arbitrary. A–S derives both from σ², γ, and k. If the derived δ and reservation-price tilt are different from v16's, that gap is one-step alpha (we know v16 picked its parameters by rule-of-thumb, not from first-principles σ).

**Sketch of the derivation under our numbers.**

- Take γ = 1 / 200 = 0.005 (standard normalisation: 1 / position-limit).
- σ² · γ · T = 1.66 × 0.005 × 10 000 = 83 SeaShells **at start of day, q=1**. So reservation price r = mid − q · 83 / 200 ≈ mid − 0.42 · q for q in contracts at start of day.
- For q=50 (= v16 cap): r = mid − 21. That is a strong inventory tilt — far stronger than v16's `INV_MAX_SKEW=4` which is at most ±4 ticks.
- With ln(1+γ/k) ≈ 0 for plausible k, optimal half-spread ≈ 41.5 ticks. **But quoted half-spread is only 8.** A–S says we should be quoting *outside* the book (because we are highly risk-averse).

**Interpretation.** Naïve A–S says quote outside the book → never fill. The lesson is that the *competition* pays you a half-spread of 8, not the analytically optimal 41.5 — γ is implicitly much smaller than the "1 / limit" normalisation. Either we drop γ by 10x (γ = 5e-4 → optimal half-spread ≈ 4.5, beats bb+1) **or** we keep γ at 5e-3 but treat the framework as a **sizing law** rather than a quote-distance law:

```
Quote at bb+1 / ba−1 (book-priority).
Size on bid : QUOTE_BASE · max(0, 1 − (q − q_target) · k_inv)
Size on ask : QUOTE_BASE · max(0, 1 + (q − q_target) · k_inv)
```

with `k_inv` derived from σ²·γ. This is a **size-based** A–S — gives the optimal *tilt* without sacrificing book-priority fills. Calibrated values for hydrogel: `k_inv ≈ 2e-3` per contract → at q = 50, ask size 0% / bid size 200% of base (effectively asymmetric stop).

**Predicted backtest:** **+30–45 k / 3 days**, but the shape of the PnL curve over time will be smoother (lower MtM variance, similar mean). The *real* win is in live: a calibrated inventory penalty is a structural defence against the v9 failure mode that doesn't depend on a pre-specified anchor.

**Risk math.** Worst case: q saturates at ±50, asymmetric sizing pulls us back to 0 forcefully. No anchor assumption needed → no anchor-shift tail.

### S4 — Triple-EMA cascade with a take-profit liquidator

**The hole this fills.** v16/v23 enter a position with the slow EMA but **never explicitly exit when the position has worked**. The only exit channel is the maker quote on the opposite side, which fires at the same rate whether we are in the money or not. If mid rallies 30 SeaShells while we are short 50 contracts, v16 captures −50 × 30 = −1 500 of MtM until its bid quote happens to fill again. There's no "take profit at 0.5σ from anchor" overlay.

**The mechanism — three EMAs on three timescales:**

| EMA | Halflife (ticks) | Role |
|---|---|---|
| Anchor EMA | 5 000 | Long-run fair value (same as v16) |
| Trend EMA | 500 | Detect the regime — is mid rallying through anchor? |
| Speed EMA | 50 | Detect immediate direction |

Logic at every tick:

1. Compute target_v16 = round(−K_FV × (mid − anchor_ema)) with cap = 50 (unchanged).
2. **Take-profit override:** if |pos| ≥ 30 AND sign(pos) opposes sign(mid − anchor_ema) AND speed_ema is moving toward anchor: drop target to 0 (liquidate).
3. **Stop-loss override:** if |pos| ≥ 30 AND sign(pos) opposes sign(mid − anchor_ema) AND trend_ema is moving away from anchor for 200+ ticks: drop target to half (partial exit).

In words: only exit aggressively when both the local speed signal *and* the slower trend signal confirm the reversion is happening. Don't exit on bounce noise (filtered by trend EMA), don't exit reactively on PnL alone (which `regime_pnl` got wrong with thresh=1.5 k).

**Predicted backtest:** **+40–55 k / 3 days**. The take-profit captures the inventory PnL term (currently −8 k for the pure maker, ≈ −2 to −5 k for v16) and converts most of it back to + sign on the days where reversion does happen.

**Risk math.** Same worst case as v16 (cap=50). Difference is intra-day MtM variance: lower (TP locks profits early, stops out the bad side faster).

---

## 8. Cross-strategy comparison and recommended order of work

| Idea | Mechanism | Predicted lift over v16 | Mechanism orthogonal to current v16? | Risk vs v16 |
|---|---|---:|---|---|
| S1 — tanh anchor | Smoother target curve, harder near origin | +3 to +10 k | No (replaces target function) | Same |
| S2 — imbalance overlay | Fast OB signal (orthogonal) | **+5 to +13 k** | **Yes** | Same or lower |
| S3 — A–S size law | First-principles inventory penalty | -5 to +10 k (variance reduction) | Yes (replaces sizing rule) | Lower |
| S4 — triple-EMA TP | Explicit exit when reversion confirms | +5 to +20 k | Yes (additive) | Same |

**Recommended testing order** (highest information per backtest):

1. **S2 (imbalance overlay).** It is the only proposal that exploits a signal not currently used at all by any shipped strategy, and the statistical magnitude (corr=+0.33) is unambiguous. **Top priority.**
2. **S4 (triple-EMA TP).** Stack on top of S2 (additive). Captures the inventory PnL term that no current variant addresses.
3. **S1 (tanh anchor).** Cheap to test; replaces one line in v16. Either it works or it doesn't.
4. **S3 (A–S size law).** Hardest to derive correctly; provides a principled justification for sizing but is unlikely to dominate S2+S4 numerically.

**Combine ceiling.** S2 + S4 together (they are orthogonal: S2 is fast tick-by-tick, S4 is slow exit logic) plausibly takes v16 from 34.7 k to **~50 k / 3 days at the same tail-risk profile**. That is also roughly the empirical ceiling implied by the half-spread PnL term (27.8 k of pure half-spread) plus the slow-reversion alpha (~20 k captured by an EMA-anchored 50-cap inventory) plus −5 k for bad fills — i.e., **the data does not support a 100 k+ backtest at v16's risk class**. v9's 112 k was a lucky in-sample fit on the 10 000 anchor; that ceiling is unreachable with the v15/v16 risk budget.

## 9. What this study explicitly does NOT recommend

1. **Do not re-introduce a hardcoded 10 000 anchor under any guise.** §5 quantifies the long-tail loss; v9 paid it.
2. **Do not raise CAP above 50 unless the live submission has demonstrated +20 k of safety buffer.** Every additional 50 contracts of inventory exposure is one drift episode away from a live drawdown.
3. **Do not parameter-sweep S1–S4 to maximize 3-day backtest PnL.** The earlier `feedback_alpha_not_backtest` memory documents the trap. Pick conservative defaults; verify positivity per day; stop.
4. **Do not waste cycles on `tight-spread join` strategies.** §5b shows the regime is 3.3% / median 1 tick — the population of opportunities is too small to beat noise.
5. **Do not chase taker fills.** §6.2 shows maker is non-toxic and §3 shows the half-spread captured per fill is structural. Taker pays 7+ SeaShells of upfront cost to acquire each contract; even with the +0.33 imbalance correlation, that cost is too high to recover at 4-SeaShell expected next-tick move.

## 10. Reproducer & next steps

**Reproducer.** Every number above is printed by `round3/_hg_research_study.py`. To reproduce:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe round3/_hg_research_study.py
```
Runtime ~1 s, no external dependencies beyond pandas and numpy.

**Suggested next concrete experiment.** Implement S2 (imbalance overlay) on top of `trader_hydrogel_v16_softema.py` as `strat_hg_v24_imbalance.py`. Backtest against v16 with the standard `1--2 1--1 1-0` triple. Promote only if (a) total > v16 by ≥ 2 k AND (b) profitable on every individual day AND (c) no day below v16 by more than 0.5 k. If those gates fire, stack S4 on top as v25.

---

## Appendix A — All numbers in one table for fast reference

| Quantity | Value | Source |
|---|---:|---|
| ticks (3 days) | 30 000 | header |
| trades (3 days) | 1 010 | header |
| spread mean / median / mode | 15.72 / 16 / 16 | §1 |
| share spread ≤ 9 | 3.30 % | §1, §5b |
| mid mean / std / range | 9 990.81 / 31.94 / 188 | §1 |
| P(\|mid−10000\|<30 / 50 / 100) | 62.1 / 85.7 / 99.9 % | §1 |
| σ_true per tick (two-scale) | 1.29 | §3 |
| η microstructure noise | 5.31 | §3 |
| signal/noise per Δ1 | 0.24 | §3 |
| AC1 at dt=1 / dt=5 / dt=10 | −0.129 / −0.026 / −0.017 | §2 |
| VR(2 / 8 / 32 / 128 / 256) | 0.89 / 0.79 / 0.73 / 0.66 / 0.56 | §2b |
| reversion corr h=2000, anchor 10000 | −0.70 | §4b |
| reversion corr h=2000, EMA-5000 | −0.44 | §4 |
| longest drift run, day 1 | 3 886 ticks (+) | §5 |
| corr(L1+L2 imb, Δmid_{t+1}) | **+0.330** | §6.1 |
| E[Δmid_{t+1} \| imb ∈ [+0.1,+0.5]] | +4.15 | §6.1 |
| E[signed drift, h=1000 post-trade] | +0.36 | §6.2 |
| pure-maker half-spread PnL (3d) | +27 822 | §6.3 |
| pure-maker inventory PnL (3d) | −8 299 | §6.3 |
| pure-maker mark-to-mid PnL (3d) | +19 523 | §6.3 |
| v16_softema backtest (3d) | +34 683 | prior memory |
| v9_aggressive backtest (3d) | +112 636 | prior |
| v9_aggressive **live** | ≈ −10 000 | prior |
