# Round 1 — Strategy Documentation

**Competition:** IMC Prosperity 4  
**Round closed:** 2026-04-17  
**Products:** `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`  
**Position limits:** 80 each

---

## Chosen Submissions

| Product | File | Notes |
|---------|------|-------|
| ASH_COATED_OSMIUM | `round1/trader_ash6_fix_doublefire.py` | Wall sniper + z-score taker + OBI maker |
| INTARIAN_PEPPER_ROOT | `round1/2800ash_final.py` (PEPPER layer) | Buy-and-hold base + swing |

---

## ASH_COATED_OSMIUM Strategy

### Final Architecture (`trader_ash6_fix_doublefire.py`)

Three-layer architecture sharing a position budget via `committed_buy` / `committed_sell`:

```
Tick
 ├─ [P1 — TAKER Z-SCORE]   MA20 z-score, fires when spread < 9 and |z| > 2.0
 │    → sell at best_bid (z > +2), buy at best_ask (z < −2)
 │    → cap: min(TAKER_LIMIT=30, residual capacity)
 │    → sets taker_action flag to prevent contradictory P2 signal
 │
 ├─ [P2 — TAKER WALL (SNIPER)]   rolling 30-tick wall mid, fires when spread < 9
 │    → sell if best_bid > rolling_wall_mid + 0.1 (price anomaly above wall)
 │    → buy  if best_ask < rolling_wall_mid − 0.1 (price anomaly below wall)
 │    → passive unwind: if |mid − wall_mid| ≤ 0.5 and pos ≠ 0 → close at int(mid)
 │    → only fires if taker_action is None (no contradiction with P1)
 │
 └─ [P3 — MAKER OBI-DRIVEN]   always runs on residual capacity
      → penny-jump: bid+1/ask−1 when spread > 2; join when spread ≤ 2
      → OBI continuous scaling: buy_size = int(BASE×(1+obi)), sell_size = int(BASE×(1−obi))
      → inventory ramp: linear scale-down between SOFT_LIMIT=70 and ASH_LIMIT=80
      → NO suppress (both sides always active)
```

### Key Parameters

```python
ASH_LIMIT        = 80
WALL_THRESHOLD   = 15    # min volume for a "wall" level
WALL_WINDOW      = 30    # rolling window for wall mid
ANOMALY_THRESHOLD= 0.1   # price deviation to trigger wall snipe
SPREAD_THRESHOLD = 9     # gate for both takers
TAKER_LIMIT      = 30    # max units per taker fire
BASE_ORDER_SIZE  = 20    # maker base size
SOFT_LIMIT       = 70    # maker ramp starts here
MA_WINDOW        = 20    # z-score MA window
Z_THRESHOLD      = 2     # z-score fire threshold
```

### Wall Signal

- Scans both sides of the book for levels with volume ≥ `WALL_THRESHOLD` (15)
- Tracks the most recent bid wall and ask wall across ticks
- Computes `instant_wall_mid = (last_bid_wall + last_ask_wall) / 2`
- Rolling 30-tick average of `instant_wall_mid` → `rolling_wall_mid`
- Snipe when live best_bid/ask diverges more than 0.1 from `rolling_wall_mid`

### Z-Score Signal

- 20-period rolling MA of mid-price, persisted in `trader_data["ash_prices"]`
- `z = (mid − MA20) / std20`
- Fires at |z| > 2.0 with spread < 9

### Inventory Ramp (Maker)

```python
ramp = ASH_LIMIT - SOFT_LIMIT  # = 10
if ash_pos > SOFT_LIMIT:
    buy_size  = int(buy_size  * max(0.0, (ASH_LIMIT - ash_pos) / ramp))
elif ash_pos < -SOFT_LIMIT:
    sell_size = int(sell_size * max(0.0, (ASH_LIMIT + ash_pos) / ramp))
```

---

## INTARIAN_PEPPER_ROOT Strategy

### Final Architecture (`2800ash_final.py` PEPPER layer)

Two-layer approach with a linear fair-value model:

```python
PEPPER_LIMIT         = 80
PEPPER_BASE_POSITION = 75
PEPPER_SWING_MAX     = 5
PEPPER_PENTE         = 0.001
PEPPER_INTERCEPT     = 9999.9

fair_price = PEPPER_INTERCEPT + PEPPER_PENTE * abs_timestamp
```

**Day detection:** on first tick, inspects best_ask to infer which day of the round it is (offset 0/1/2) and corrects `abs_timestamp` accordingly.

**Layer 1 — Base fill (pos < 75):**
- Sweeps all ask levels until position reaches 75
- First 3000 ticks: place bids at `ask − 2` (passive, during price discovery)
- After: buy at ask aggressively

**Layer 2 — Swing (pos ≥ 75, remaining 5 units):**
- Buy up to +5 if `ask ≤ fair_price + 3`
- Sell swing position if `bid > fair_price + 3`

### PEPPER PnL context

~79,700/day vs theoretical maximum ~80,000/day. Gap ≈ 300/day, within noise. PEPPER is not a source of competitive disadvantage.

---

## Research Log — ASH_COATED_OSMIUM

### Architecture evolution

| Version | Key feature | ASH PnL (3-day total) |
|---------|-------------|----------------------|
| `test_total.py` | Basic z-score + cooperative suppress | 50,277 |
| `strat_cooperative.py` | Tuned z=1.5 + discrete OBI | 51,005 |
| `ash_maker.py` | z=2.0 + continuous OBI, no suppress | 52,744 |
| `trader_ash6_fix_doublefire.py` | + wall sniper layer | TBD |

### Backtest Baselines (worse fill mode, 3 days)

**ash_maker.py (prior best, 2026-04-16):**

| Day | ASH | PEPPER | Total |
|-----|-----|--------|-------|
| 1−2 | 16,386 | 79,784 | 96,170 |
| 1−1 | 18,727 | 79,516 | 98,243 |
| 1−0 | 17,631 | 79,844 | 97,475 |
| **Total** | **52,744** | **239,144** | **291,888** |

**strat_cooperative.py (superseded 2026-04-16):**

| Day | ASH | PEPPER | Total |
|-----|-----|--------|-------|
| 1−2 | 16,115 | 79,780 | 95,895 |
| 1−1 | 17,573 | 79,454 | 97,027 |
| 1−0 | 17,317 | 79,852 | 97,169 |
| **Total** | **51,005** | **239,086** | **290,091** |

Note: ±500 tick variance across runs due to non-determinism in fill ordering.

---

### Market Microstructure (measured 2026-04-15)

- Tight spreads (<10): **3.9%** of ticks (1,083/27,644)
- Spread is bimodal: 64% at spread=16, 1.8% at spread≤6
- ASH market trades: 1–10 units/trade, mean 5.25; P50 ≈ 10 units/tick
- 1,795/1,825 ticks have a single fill; 30 have two
- L1 fill volume P50 ≈ 10 → **any maker cap > 15 or taker cap > 35 is dead code**
- `BASE_ORDER_SIZE=15` captures essentially all available volume
- Tight-spread ticks are bid-heavy 63.8% of the time
- L3 depth: 97% missing → unusable; L2 depth: 35% missing → marginal

---

### Z-Score Accuracy by Vol Regime (notebook cells 63–65)

| Vol regime | N (|z|>1.5) | Accuracy h=5 | Accuracy h=10 |
|------------|------------|-------------|--------------|
| low_vol (rv20 < P33) | 1892 | **75.1%** | 73.8% |
| mid_vol | 1264 | 90.3% | 88.3% |
| high_vol (rv20 > P67) | 884 | **95.4%** | 95.4% |

rv20 AR(1) = 0.970 (highly persistent); typical high-vol run = 15 bars.

Global accuracy at |z|>1.5: **84%**.

---

### OBI Statistical Validation (`ash_coated_osmium_analysis.ipynb` cells 58–61)

L1 OBI distribution: ratio mean=0.50, std=0.12; delta P25=P50=P75=0 (>50% of ticks perfectly balanced).

OLS regression (l1_ratio + l1_delta → h-bar forward return, N≈30k):

| Horizon | R² | beta_ratio | p-value |
|---------|-----|-----------|---------|
| h=1 | **0.346** | +1.53e-3 | *** |
| h=5 | **0.318** | +1.53e-3 | *** |
| h=10 | **0.282** | +1.56e-3 | *** |

OBI is highly significant but economically small: 2–5 ticks predicted vs 16-tick spread. Used for size modulation only, not quote adjustment.

Strategy regime forward returns (all *** p<0.001):

| Regime | N (% of ticks) | Mean h=5 fwd ret | t-stat |
|--------|---------------|-----------------|--------|
| GOLDEN_BUY | 64 (0.21%) | +4.5 ticks | 21 |
| GOLDEN_SELL | 101 (0.34%) | −3.9 ticks | −23 |
| GOOD_BUY | 1119 (3.73%) | +2 ticks | 32 |
| GOOD_SELL | 1113 (3.71%) | −1.9 ticks | −32 |
| NORMAL | 27602 (92%) | ≈0% | 0 |

---

### ML Alpha Research (`round1/ash_ml_alpha.py`, 2026-04-15)

Walk-forward IC on 36 features. RF max_depth=3, min_samples_leaf=50. Train: day −2, test: days −1 and 0.

| Feature | Global IC h=5 | Partial IC (after z_20) | Tight-spread IC | Status |
|---------|---------------|------------------------|-----------------|--------|
| gap_asym_12 | +0.367 | +0.311 | +0.762 | Mechanically correlated with z, untranslatable |
| obi_l1l2 | +0.185 | +0.190 | +0.448 | Real but fills still L1-capped |
| z_velocity | −0.395 | −0.171 | −0.689 | Separates z quality but filtering costs more than it saves |
| taper_imbalance | −0.304 | −0.172 | −0.364 | Mechanically correlated with z |
| spread dynamics | ~0 | −0.150 | ~0 | Wide-spread artifact |
| rv_5 | ~0 | ~0 | ~0 | Differs only in wide-spread regime |

**gap_asym_12:** bearish fires always have gap_asym ≈ −7; bullish ≈ +7. Consequence of book depletion, not independent signal. Tested as maker size skew → delta = 0. L1 binding confirmed.

**z_velocity:** correct fires z_velocity = −0.395; wrong fires = −0.008. Filtering only changes accuracy by 1.4pp and removing rising-z fires costs more revenue than saves. Net: −PnL.

**Binding constraint:** L1 fill volume P50 ≈ 10. Any maker size cap > 15 or taker cap > 35 is dead code. Maker size modulation of any kind is permanently ruled out.

---

### ML Signal Research (`round1/ash_signal_research.py`, 2026-04-15)

**Book Depletion Proxy (dep_net):** IC (Spearman, h=5) = 0.33 on both held-out days — second-strongest after z_20 (IC≈0.47). At z-fire ticks: dep agrees 81.1% (accuracy 95.4%), dep opposes 13.4% (accuracy 92.8%). Real signal, but cannot translate to PnL: 16-tick spread absorbs 2-3 tick directional signal.

**EMA z-score:** All alphas 0.05–0.50 produce lower |IC| than MA20 on day −1. MA20 is near-optimal.

**PEPPER cross-asset:** pep_mom IC < 0.015. Dead.

**Multi-scale z agreement:** 100% of tight-spread fires have z_5, z_10, z_20 agreeing. Filter is vacuous — never triggers.

---

### Open Experiments (ash_maker baseline, 2026-04-16)

These were identified but may or may not have been tested. Results to be recorded if backtested.

#### Experiment A — Fix Unwind Price
Unwind at `int(mid)` (= best_bid+8 at spread=16) earns 7 ticks less than penny-jump ask. Fix: unwind at `best_bid` (long) or `best_ask` (short). File: `strat_unwind_fix.py`.

#### Experiment B — Re-add Cooperative Suppress at z=2.0
When taker sells (z>2), maker simultaneously posts bids — conflict. Suppress the opposite maker side. File: `strat_suppress_z2.py`. Note: cooperative suppress was net-negative when ash_maker beat cooperative, so conviction is low.

#### Experiment C — Raise Taker Cap to ASH_LIMIT
`TAKER_LIMIT=40` blocks taker when maker has built pos>40. Fix: use `ASH_LIMIT=80`. File: `strat_taker_cap80.py`. Note: L1 binding makes this effectively dead code in practice.

#### Experiment D — Symmetric OBI Size Scaling
Current OBI asymmetry posts more bids AND fewer asks when bid-heavy. Symmetric variant uses `abs(obi)` to scale both sides equally. File: `strat_obi_sym.py`.

#### Experiment E — PEPPER Passive Window Fix
ash_maker uses `timestamp < 3000` vs cooperative's `timestamp < 2100`. Impact: negligible (PEPPER gap ≈ 300/day to theoretical max).

---

### Ruled Out (do not retry)

**Structural constraints underlying all failures:**
- L1 fill volume P50 ≈ 10 units — any maker cap > 15 or taker cap > 35 is dead code
- 1-tick discrete LOB — continuous inventory quote adjustment kills penny-jump fill rate
- Bots are price-triggered not time-triggered — temporal patterns fail OOS
- Spread gate is architecturally necessary — removing it inverts suppress economics

**Taker variants:**

| Experiment | File | Delta ASH | Root cause |
|------------|------|-----------|------------|
| No taker | `strat_no_taker.py` | −7,341 | Taker prevents wrong-direction inventory on 84%-accurate z fires |
| Passive entry (bid+2/ask−2) | `strat_passive_entry.py` | −7,814 | Misses bot fills at bid+1/ask−1 in worse-fill mode |
| Wide-spread taker (spread≥10) | — | −12,587 | Round-trip = −1 tick/unit with no recovery leg |
| Z=1.0 threshold | `strat_z1pt0.py` | −245 | At z<1.5 gross EV < −1 tick round-trip cost |
| Z=1.2 unconditional | (implicit) | ~−200 | Same cost-benefit failure |
| Z=1.2 dep_net-gated | `strat_dep_lower_z.py` | −139 | dep_net real (IC=0.33) but EV at z=1.2–1.5 sub-threshold |
| Asymmetric z (sell=1.2, buy=1.5) | `strat_asym_z.py` | +10 (noise) | L1 volume caps extra fires |
| Vol-regime z (low=1.8, high=1.2) | `strat_ml_regime.py` | +31 (noise) | Absolute displacement equivalence; net zero |
| OBI ratio-only taker | `strat_obi_ratio.py` | −6,988 | OBI fires on momentum+reversion; z selects reversion only |
| OBI+z intersection taker | `strat_obi_z_intersect.py` | −6,470 | OBI filter removes profitable z fires |
| OBI+z union taker | `strat_obi_z_union.py` | −287 (noise) | OBI-only fires and conflict-blocking cancel out |
| OBI GOLDEN taker, no spread gate | `strat_obi_golden.py` | −58,394 | Without gate, wrong-side 35-unit short |
| Bot temporal bins | `strat_bot_schedule.py` | 0 (identical) | Bots are price-triggered; traderData doesn't persist across days |
| Price-level density taker | `strat_density.py` | −389 | Coarser proxy for z-score; −389 vs cooperative |
| Tight spread classifier | `strat_tight_spread.py` | n/a | ROC-AUC=0.513; L1 volume identical at tight vs wide |

**Maker variants:**

| Experiment | File | Delta ASH | Root cause |
|------------|------|-----------|------------|
| Graduated inventory skew (pos>30) | — | −1,400 | Fights OBI size; reduces fill rate |
| OBI quote pull-back (ask+2/+5) | — | negative | Valid statistically; spread opportunity cost dominates |
| Z-lean global | — | −243 | Maker suppression net-negative |
| Z-lean at |z|>2.0 | `strat_zlean_thresh.py` | −361 | Consistent across all 3 days |
| Z-lean high_vol only | `strat_zlean_regime.py` | −14 (noise) | Near-zero; not worth complexity |
| Gap asymmetry size skew | `strat_gap_maker.py` | 0 | L1 binding: min(cap×skew, ~10) = 10 regardless |
| Vol-regime taker sizing | `strat_vol_regime.py` | −32 (noise) | Cap raise dead code; threshold raise reduces recovery |
| Soft suppress (0.5<|z|<1.5) | `strat_soft_suppress.py` | 0 (identical) | No bot fills exist in that regime |
| Multi-tick suppress | `strat_multitick_suppress.py` | −11,239 | Suppressing maker across ticks starves income |
| Avellaneda-Stoikov OU maker | `strat_as_meanrev.py` | −10,607 | adj≥1 tick at |pos|≥3; drops bid to best_bid, misses all bot sells |
| Passive inside-spread limits | — | −361 | Dominated by penny-jump: same fill event, 1+ ticks worse |

**Fair value variants:**

| Experiment | File | Delta ASH | Root cause |
|------------|------|-----------|------------|
| Pure microprice z-score | `strat_microprice.py` | −517 | MA20 absorbs OBI; only OBI deviation enters z |
| Hybrid microprice z-score | `strat_microprice_hybrid.py` | −988 | OBI sign inverted for mean-reversion |
| Static per-day anchor | `ash_static_fair_research.py` | n/a | ASH drifts +4 ticks/day; accuracy 27–33% |
| EMA z-score (all alphas) | (research) | lower IC | All alphas 0.05–0.50 give lower IC than MA20 |

**Novel signal candidates (all ruled out):**

| Candidate | Outcome |
|-----------|---------|
| Price-Level Bot Activity Density Map | Pearson=0.791 but coarser proxy for z; delta −389 |
| Tight Spread Timing Classifier | ROC-AUC=0.513 (≈ random); L1 identical to wide |
| Kalman Filter Fair Value | Low conviction; microprice experiments showed −517 to −988 |
| Trade VWAP reference | 411 trades/day, VWAP window ≈ 1,200 ticks — too slow |
| Lee-Ready trade classification | dep_net IC=0.33 but untranslatable; Lee-Ready faces same ceiling |

---

### Competition Gap Analysis (2026-04-15)

Competitors outperform on Round 1. Three hypotheses ruled out:
- **Other products:** Round 1 only has ASH + PEPPER. Same product set for all.
- **PEPPER gap:** ~79,700/day vs theoretical ~80,000/day. Gap ≈ 300. Not the source.
- **Backtest noise:** Confirmed on live leaderboard. Real gap.

**Conclusion:** Competitors extract more from ASH. Bots are deterministic; all teams face same order book. Gap is pure strategy quality. Queue-position-aware quoting is not a current competition feature.

---

## Competition Mechanics

- Exchange runs **deterministic, non-adaptive bots**
- Each team runs independently against the same bot environment — no human-vs-human order book interaction
- Backtester is **accurate**: same fill opportunities as live
- Fill executes at **your order price**, not market trade price
- No transaction fees modelled
- Backtest score ≈ live score; gap vs competitors is pure strategy quality gap
