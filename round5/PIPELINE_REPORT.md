# Round 5 — Pipeline Report

This document explains how the round-5 research pipeline classifies the 50-product universe and what it found. It covers the data, the statistical machinery, the classifier design, the gate thresholds, the per-family results, and the cross-family findings.

The pipeline lives under [round5/](.). The report below describes the state captured in [round5/reports/](reports/) after the latest reclassification pass.

---

## 1. Executive summary

**Universe.** Round 5 introduces 50 brand-new tradable products in 10 categories of 5 each. Position limit per product is 10. Three days of historical prices + trades are available (`dataset/ROUND_5/{prices,trades}_round_5_day_{2,3,4}.csv`). None of the strategies from rounds 1–4 carry over.

**Classification axes.** Each product is assigned one *primary archetype* (mutually exclusive) and zero or more *orthogonal flags* (independent layered strategies). Flags can stack on any primary.

| Axis | Values |
|---|---|
| **Primary** (one per product) | `MR_TAKER`, `MOMENTUM`, `RANDOM_WALK`, `NO_EDGE` |
| **Flags** (any subset) | `PAIR_ANCHOR`, `OBI_TAKER`, `MM_CANDIDATE` |

`MR` and `MOMENTUM` are mutually exclusive (priority chain). `MR` and `MM_CANDIDATE` are *not* exclusive — alpha-taking and spread-capture can coexist on the same product.

**Final state (50 / 50 products).**

| Bucket | Count |
|---|---:|
| MR_TAKER (primary) | **41** |
| MOMENTUM (primary) | 0 |
| RANDOM_WALK (primary) | 0 |
| NO_EDGE (primary) | 9 |
| PAIR_ANCHOR (flag) | **23** |
| OBI_TAKER (flag) | **29** |
| MM_CANDIDATE (flag) | **15** |
| **Actionable** (any non-NO_EDGE primary OR any flag) | **48 / 50** |

Only `PANEL_1X4` and `TRANSLATOR_SPACE_GRAY` carry no archetype tag of any kind.

**MR_TAKER confidence breakdown** (41 products):

| Confidence | Count | Trigger basis |
|---|---:|---|
| **high** | 19 | FDR-passing IC OR ≥3 structural triggers, no contradictions |
| **medium** | 5 | 2 structural triggers, no contradictions |
| **low** | 17 | 1 trigger only OR at least one opposite-sign sister stat firing |

11 of 41 MR_TAKER products carry `mr_ic_verified = True` (HAC + BH-FDR-passing positive IC on a mean-reversion signal). The remaining 30 are admitted on structural triggers alone — the rationale string explicitly states "no FDR-significant IC — anchor default = …" so a strategy compositor can downweight them.

15 of 41 carry at least one `mr_contradiction` (opposite-sign sister stat firing alongside the MR triggers). These all degrade to `mr_confidence = low` regardless of trigger count — the classification is internally inconsistent and the trader should investigate before deploying.

**PAIR_ANCHOR residual stationarity**: 6 / 14 unique pairs have `pair_residual_stationary = True` (coint_p < 0.10 — suitable for a fixed-β hedge). The remaining 8 entered via the high-corr lane but the residual is non-stationary; their strategy template should use rolling β rather than a static spread.

**OBI_TAKER direction**: 20 `follow` (positive IC ⇒ trade in the direction of book pressure) + 9 `fade` (negative IC ⇒ trade against book pressure). The 9 fade signals concentrate in SLEEP_POD and TRANSLATOR families on `obi_l3` at h = 1.

---

## 2. Methodology

### 2.1 Data sources

Per product, per day:

- **Prices CSV** — quote-side L1/L2/L3 bid and ask (price + size), plus mid quote, sampled per tick.
- **Trades CSV** — actual transactions: timestamp, price, quantity. Round 5 has **no counterparty IDs by design** — they are always blank ([feedback memory](../../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/project_round5_no_counterparties.md)).

The loader (`research_lib.load_family`) concatenates the three days into a single per-product `ProductData(product, px, tr)` record and passes through:

1. `add_microstructure(px)` — derives spread, microprice, depth_l1/l2/l3, OBI_l1/l3, returns at horizons 1/10/100, forward returns at 1/10/100/1000, and rolling std at 50/500.
2. `add_vwap(px, tr)` — builds a per-tick volume-weighted average trade price by aggregating trades within each timestamp into one weighted point and forward-filling onto the px grid. Falls back to `mid` for ticks before the first trade of a day.

### 2.2 Statistical signals

For each product:

- **Volatility ratio** (Lo–MacKinlay) at lags k ∈ {2, 5, 10}: `vr_k5` ≈ 1 = random walk, < 1 = mean-reverting, > 1 = trending. Reported with z-statistic and two-sided p-value.
- **Autocorrelation function** (sample ACF) at lags 1, 5, 20, 100. ACF₁ < 0 ⇒ negative serial dependence in returns ⇒ MR signature. Bartlett p-value tests `H₀: ρ₁ = 0`.
- **Hurst exponent** via R/S analysis on log-mid returns. H < 0.5 = anti-persistent, H ≈ 0.5 = random walk, H > 0.5 = persistent.
- **Augmented Dickey–Fuller p-value** on mid level (`adf_p_mid`). p < 0.10 = stationary mid (rare in financial series).
- **VWAP-side analogues**: `vwap_hurst` on log-trade-VWAP returns (trade-event-only — forward-filled per-tick VWAP biases Hurst toward 0.5 due to constant runs); `vwap_adf_p` on log-trade-VWAP level; `vwap_acf_lag1` on log-trade-VWAP returns. Trade VWAP often mean-reverts even when mid looks I(1) because mid is quote-side noise + drift while VWAP tracks actual transaction levels.

### 2.3 Predictability signals (alpha IC)

The pipeline computes seven candidate alpha signals (`SIGNAL_NAMES` in [research_lib.py](research_lib.py)) and tests each against forward returns at four horizons h ∈ {1, 10, 100, 1000}:

| Signal | Definition | Strategy interpretation |
|---|---|---|
| `neg_zscore_mid_50` | −z(mid, window=50) | Anchor MR around recent mid |
| `neg_zscore_vwap_50` | −z(vwap, window=50) | Anchor MR around recent trade VWAP |
| `obi_l1` | (b₁ − a₁) / (b₁ + a₁) | Top-of-book imbalance — short-horizon book pressure |
| `obi_l3` | (b₁₊₂₊₃ − a₁₊₂₊₃) / (b₁₊₂₊₃ + a₁₊₂₊₃) | Total-book imbalance |
| `momentum_10` | mid_t − mid_{t−10} | Past-10-tick price change |
| `trade_imbalance` | rolling-20-tick signed trade flow | Aggressor-inferred order flow |
| `neg_spread` | −(ask − bid) | Spread as level signal |

For each (product, signal, horizon) cell, `signal_ic_table` runs an **HAC-adjusted Newey–West regression** of forward return on signal with `maxlag = h`. This corrects for the autocorrelation induced by overlapping forward-return windows: at h = 1000 with n = 30,000, naive Pearson t-stats overstate significance by ≈ √h ≈ 30×. The output is `(ic, t, p, n)` per cell.

The 28 IC cells per product (7 signals × 4 horizons) are then put through **Benjamini–Hochberg FDR correction** at α = 0.05 in `add_significance_columns` ([significance.py](significance.py)). The `significant` flag indicates whether a cell passes BH-FDR after HAC.

### 2.4 Within-family relationships

For each family of 5 products:

- **Mid correlation matrix** `corr_mid` (5 × 5).
- **Return correlation matrix** `corr_returns` on `ret_1` (5 × 5).
- **Lead-lag matrix** at lag = 10 ticks: entry [A, B] = corr(ret₁ᴬ_t, ret₁ᴮ_{t+10}). Positive [A, B] means A leads B.
- **Cointegration table** `coint`: Engle–Granger test on every C(5, 2) = 10 pair, returns `(coint_t, coint_p)`.

### 2.5 Volatility analysis

[volatility.py](volatility.py) computes per-product realized-vol stats at windows {20, 50, 200, 500}:

- `rv_w_mean / rv_w_std / p10 / p90` — distribution shape.
- `vol_of_vol = std(rv_50) / mean(rv_50)`.
- `vol_p90_p10_ratio` — sizing-relevant. ≥ 1.5 triggers an inverse-vol scaling recommendation.
- `vol_cluster_lag1 / lag10` — autocorrelation of |ret_1| (GARCH-like clustering).

Then it decomposes each product into low/mid/high tertiles of std_50 and recomputes per-regime spread, depth, |OBI|, and signal IC. When |IC| differs across regimes by ≥ 0.04, the signal is flagged `REGIME_GATED_SIGNAL` with the regime to trade in.

### 2.6 Data-quality gating

[data_quality.py](data_quality.py) runs blocking checks on every product before classification: NaN rate, crossed/locked markets, stale-run length, day-boundary jumps, empty L1, short history. Five conditions are blocking — a product hitting any one is forced to NO_EDGE primary with `DATA_QUALITY_WARN` rationale: `EMPTY_PX`, `SHORT_HISTORY`, `NAN_MID`, `CROSSED_MARKET`, `STALE_PRICES`.

Round 5 CSVs are clean by construction; **0 of 50** products tripped a blocking warning.

---

## 3. Classifier design

The classifier ([archetypes.py](archetypes.py)) uses two orthogonal axes:

### 3.1 Primary archetype (priority chain — exactly one per product)

```
1. MR_TAKER   → if any structural MR trigger fires
2. MOMENTUM   → if vr > 1.005 AND hurst > 0.545 AND HAC+FDR IC[momentum_10] ≥ 0.02
3. RANDOM_WALK→ if structural MM gates pass AND no MR/MOMENTUM trigger
4. NO_EDGE    → otherwise
```

`MR` and `MOMENTUM` are mutually exclusive because both compete to consume the same risk budget on the same timescale.

### 3.2 Orthogonal flags (independent — any subset can attach)

| Flag | Strategy template |
|---|---|
| `PAIR_ANCHOR` | β-hedged residual MR taker on the within-family partner spread |
| `OBI_TAKER` | Short-horizon book-pressure taker (h ∈ {1, 10}) |
| `MM_CANDIDATE` | Passive two-sided market-maker (Template-A: quote `mid ± max(min_edge, k_vol·rv) − γ·rv²·inventory`) |

A product can be e.g. `MR_TAKER` primary + `PAIR_ANCHOR` + `OBI_TAKER` + `MM_CANDIDATE` simultaneously. The strategy compositor downstream decides the mix.

### 3.3 Decoupling IC from MR routing

An earlier version of the classifier required *both* a structural MR signal *and* a HAC+FDR-passing `IC[neg_zscore]` to admit a product to MR_TAKER. With the loose round-5 trade activity, this gated out many genuinely mean-reverting products: the structural property (anti-persistent VWAP, stationary mid) was clearly there but the noisy mid-anchor IC didn't pass FDR after HAC at long horizons.

The current design **decouples** them:

- **Structural triggers gate** classification (any one of seven conditions admits to MR_TAKER).
- **IC value chooses** the anchor signal (`neg_zscore_mid_50` vs `neg_zscore_vwap_50`) for the strategy template:
  - If a FDR-passing IC exists at any horizon, the larger-|IC| signal is the anchor.
  - Otherwise, the anchor defaults to whichever underlying series is more anti-persistent: `vwap_hurst < hurst` ⇒ VWAP anchor, else mid anchor.

This shifted the universe from 7 MR_TAKER (over-discriminant) to 41 MR_TAKER while preserving the rigour of the IC/HAC/FDR layer for parameter selection.

### 3.4 Why `MR` and `MM` are not exclusive

A product can look like a quasi-random walk on tick scale (good for passive MM: spread > noise, deep book) yet still mean-revert at the 50-100-tick scale (good for an anchor MR taker). The two strategies operate on different timescales and consume different risk budgets:

- MR: directional, takes inventory deliberately, payoff from mean-reversion.
- MM: spread-capture, holds inventory only as a side-effect of fills, payoff from queue position × spread.

The classifier records both signals when both apply; the strategy compositor decides how to allocate risk between them.

---

## 4. Gate thresholds

All thresholds are calibrated against the empirical distribution of the underlying statistic across the 50-product universe in [calibration.py](calibration.py). The CLI `python round5/calibration.py` flags any gate that admits ≥ 95% of products (DEGENERATE_HIGH = no-op gate) or ≤ 5% of products (DEGENERATE_LOW = blanket exclusion).

### 4.1 MR_TAKER structural triggers (any one fires)

| Gate | Threshold | Rationale |
|---|---|---|
| `mr_vr_max` | `vr_k5 < 0.985` | 16% of products pass via VR alone |
| `mr_acf1_max` | `acf_lag1 < −0.005` | 32% pass — captures any meaningful negative serial dependence |
| `mr_hurst_max` | `hurst < 0.535` | ~p50 of mid Hurst distribution |
| `mr_adf_max` | `adf_p_mid < 0.10` | Weak stationarity on mid level (~p25) |
| `mr_vwap_hurst_max` | `vwap_hurst < 0.50` | Anti-persistent VWAP returns |
| `mr_vwap_adf_max` | `vwap_adf_p < 0.10` | Weak stationarity on log VWAP |
| `mr_vwap_acf1_max` | `vwap_acf_lag1 < −0.01` | Negative ACF on log-VWAP returns |

The IC gate `mr_ic_min ≥ 0.02` is **informational** — used to pick the anchor signal but not to gate classification.

### 4.2 MOMENTUM (all conjunctive)

| Gate | Threshold |
|---|---|
| `mom_vr_min` | `vr_k5 > 1.005` |
| `mom_hurst_min` | `hurst > 0.545` |
| `mom_ic_min` | `IC[momentum_10] ≥ 0.02` AND HAC+FDR-pass AND positive |

After HAC correction, no round-5 product clears all three.

### 4.3 RANDOM_WALK / MM_CANDIDATE structural (all conjunctive)

| Gate | Threshold |
|---|---|
| `rw_vr_dev_max` | `\|vr_k5 − 1\| < 0.05` |
| `rw_hurst_dev_max` | `\|hurst − 0.5\| < 0.05` |
| `rw_acf1_max_abs` | `\|acf_lag1\| < 0.05` |
| `rw_max_ic` | short-horizon `\|IC\| < 0.05` (or no FDR-pass) |
| `rw_spread_to_std_min` | `spread_median / ret1_std ≥ 1.0` |
| `rw_lim10_sat_min` | `limit10_saturation ≥ 0.2` |

For RANDOM_WALK as primary, structural pass + Template-A simulated PnL > 0 is required. Any product passing structural gates is also evaluated for the MM_CANDIDATE flag (orthogonal — does not depend on primary).

### 4.4 PAIR_ANCHOR (orthogonal flag)

Two-tier:

- **High-corr lane**: `|corr_mid| ≥ 0.7` admits regardless of cointegration.
- **Moderate lane**: `|corr_mid| ≥ 0.5 AND coint_p < 0.10`.

Only ONE partner per product (highest |corr| among passers) is recorded in `pair_partner`.

### 4.5 OBI_TAKER (orthogonal flag)

`|IC[obi_l1 OR obi_l3]| ≥ 0.04` at h ∈ {1, 10} with HAC+FDR-pass and positive sign. The signal/horizon with larger |IC| is recorded.

### 4.6 MM_CANDIDATE (orthogonal flag)

Two-stage:

1. **Structural gate** (same as RW above) → `mm_provisional = True`.
2. **Template-A simulation** on round-5 trades (IMC `worse` fill semantics, position-limit-10):
   - `pnl > 0` → **CONFIRMED** (`is_mm = True`)
   - `pnl ≤ 0 with fills > 0` → **REJECTED** (`is_mm = False`)
   - `pnl == 0 with 0 fills` → **UNTESTED** — sparse round-5 trade activity meant the strategy never got a fill opportunity; structural gate stays authoritative (`is_mm = True`)

A health figure is written for every product the sim ran on, regardless of outcome (`figures/<P>_mm_health.png`).

---

## 5. Universe results

### 5.1 Per-family distribution

| Family | MR | MOM | RW | NO_EDGE | PAIR | OBI | MM |
|---|---:|---:|---:|---:|---:|---:|---:|
| GALAXY_SOUNDS | 4 | 0 | 0 | 1 | 0 | 5 | 4 |
| SLEEP_POD | 4 | 0 | 0 | 1 | 3 | 4 | 0 |
| MICROCHIP | 5 | 0 | 0 | 0 | 4 | 0 | 0 |
| PEBBLES | 5 | 0 | 0 | 0 | 3 | 0 | 0 |
| ROBOT | 5 | 0 | 0 | 0 | 5 | 0 | 0 |
| UV_VISOR | 3 | 0 | 0 | 2 | 3 | 5 | 2 |
| TRANSLATOR | 4 | 0 | 0 | 1 | 0 | 3 | 0 |
| PANEL | 3 | 0 | 0 | 2 | 0 | 2 | 0 |
| OXYGEN_SHAKE | 3 | 0 | 0 | 2 | 2 | 5 | 1 |
| SNACKPACK | 5 | 0 | 0 | 0 | 3 | 5 | 4 |
| **Total** | **41** | **0** | **0** | **9** | **23** | **29** | **11** |

### 5.2 NO_EDGE products (9)

| Product | Flags |
|---|---|
| GALAXY_SOUNDS_PLANETARY_RINGS | OBI |
| SLEEP_POD_COTTON | PAIR + OBI |
| UV_VISOR_ORANGE | PAIR + OBI |
| UV_VISOR_RED | OBI |
| TRANSLATOR_SPACE_GRAY | — |
| PANEL_1X4 | — |
| PANEL_2X4 | OBI |
| OXYGEN_SHAKE_MINT | OBI |
| OXYGEN_SHAKE_GARLIC | PAIR + OBI |

7 of 9 still carry an orthogonal flag. Only PANEL_1X4 and TRANSLATOR_SPACE_GRAY have no archetype tag at all.

### 5.3 PAIR_ANCHOR edges (deduplicated; 14 unique pairs — 23 product-side flags)

| Pair | corr_mid | coint_p | Lane |
|---|---:|---:|---|
| MICROCHIP_RECTANGLE ↔ MICROCHIP_SQUARE | −0.88 | 0.020 | high-corr |
| UV_VISOR_AMBER ↔ UV_VISOR_MAGENTA | −0.87 | 0.042 | high-corr |
| MICROCHIP_OVAL ↔ MICROCHIP_TRIANGLE | +0.87 | 0.053 | high-corr |
| SLEEP_POD_COTTON ↔ SLEEP_POD_POLYESTER | +0.88 | 0.101 | high-corr |
| SLEEP_POD_POLYESTER ↔ SLEEP_POD_SUEDE | +0.86 | 0.151 | high-corr |
| PEBBLES_S ↔ PEBBLES_XL | −0.83 | 0.229 | high-corr |
| PEBBLES_XL ↔ PEBBLES_XS | −0.83 | 0.482 | high-corr |
| ROBOT_IRONING ↔ ROBOT_MOPPING | −0.82 | 0.266 | high-corr |
| ROBOT_LAUNDRY ↔ ROBOT_VACUUMING | +0.79 | 0.070 | high-corr |
| ROBOT_DISHES ↔ ROBOT_LAUNDRY | −0.72 | 0.257 | high-corr |
| UV_VISOR_AMBER ↔ UV_VISOR_ORANGE | −0.71 | 0.826 | high-corr |
| OXYGEN_SHAKE_CHOCOLATE ↔ OXYGEN_SHAKE_GARLIC | +0.65 | 0.066 | moderate (coint) |
| SNACKPACK_CHOCOLATE ↔ SNACKPACK_VANILLA | −0.93 | 0.462 | high-corr |
| SNACKPACK_CHOCOLATE ↔ SNACKPACK_STRAWBERRY | −0.54 | 0.036 | moderate (coint) |

### 5.4 MM_CANDIDATE products (11)

| Product | Status | sim_pnl | fills | params |
|---|---|---:|---:|---|
| GALAXY_SOUNDS_DARK_MATTER | UNTESTED | 0.0 | 0 | min_edge=6, k_vol=1.65, γ=1e-3 |
| GALAXY_SOUNDS_BLACK_HOLES | UNTESTED | 0.0 | 0 | min_edge=7, k_vol=1.70, γ=1.2e-3 |
| GALAXY_SOUNDS_SOLAR_WINDS | UNTESTED | 0.0 | 0 | min_edge=7, k_vol=1.67, γ=1.1e-3 |
| GALAXY_SOUNDS_SOLAR_FLAMES | UNTESTED | 0.0 | 0 | min_edge=7, k_vol=1.67, γ=1.1e-3 |
| UV_VISOR_MAGENTA | UNTESTED | 0.0 | 0 | min_edge=7, k_vol=1.68, γ=1.1e-3 |
| UV_VISOR_YELLOW | UNTESTED | 0.0 | 0 | min_edge=7, k_vol=1.68, γ=1e-3 |
| OXYGEN_SHAKE_MORNING_BREATH | UNTESTED | 0.0 | 0 | min_edge=6, k_vol=1.69, γ=1e-3 |
| **SNACKPACK_VANILLA** | **CONFIRMED** | **+1350.4** | 1 | min_edge=8, k_vol=1.66, γ=1e-3 |
| SNACKPACK_RASPBERRY | UNTESTED | 0.0 | 0 | min_edge=8, k_vol=1.65, γ=1e-3 |
| SNACKPACK_STRAWBERRY | UNTESTED | 0.0 | 0 | min_edge=9, k_vol=1.65, γ=1.1e-3 |
| SNACKPACK_PISTACHIO | UNTESTED | 0.0 | 0 | min_edge=8, k_vol=1.65, γ=1.1e-3 |

All 11 MM products are also primary `MR_TAKER` — the orthogonal layering at work. SNACKPACK_CHOCOLATE was structurally eligible but the sim returned PnL = −1364 with 1 fill — REJECTED, `is_mm = False`.

### 5.5 Top OBI_TAKER products (sorted by |IC|)

The 5 SNACKPACK products dominate (IC[obi_l1, h=1] in 0.097–0.132 range), followed by GALAXY_SOUNDS, UV_VISOR, and OXYGEN_SHAKE families. SLEEP_POD and TRANSLATOR products show **negative** OBI IC at h=1 (i.e., book imbalance predicts opposite-direction return — consistent with a fade-the-book strategy rather than follow-the-book).

| Product | Signal | h | IC |
|---|---|---:|---:|
| SNACKPACK_PISTACHIO | obi_l1 | 1 | +0.132 |
| SNACKPACK_CHOCOLATE | obi_l1 | 1 | +0.118 |
| SNACKPACK_VANILLA | obi_l1 | 1 | +0.114 |
| SNACKPACK_RASPBERRY | obi_l1 | 1 | +0.102 |
| SNACKPACK_STRAWBERRY | obi_l1 | 1 | +0.097 |
| OXYGEN_SHAKE_GARLIC | obi_l1 | 1 | +0.066 |
| GALAXY_SOUNDS_SOLAR_WINDS | obi_l1 | 1 | +0.065 |
| UV_VISOR_YELLOW | obi_l1 | 1 | +0.061 |
| GALAXY_SOUNDS_SOLAR_FLAMES | obi_l3 | 1 | −0.054 |
| SLEEP_POD_COTTON | obi_l3 | 1 | −0.051 |
| SLEEP_POD_NYLON | obi_l3 | 1 | −0.049 |

(Full list in [round5/reports/SNACKPACK/signals_ic.csv](reports/SNACKPACK/signals_ic.csv) etc., or aggregated via `archetype_assignment.csv`.)

---

## 6. Per-family results

For brevity, each family below lists the primary classification and the dominant flags. Full per-product rationale strings live in `round5/reports/<FAMILY>/archetype_assignment.csv`.

### GALAXY_SOUNDS
- **MR_TAKER**: DARK_MATTER, BLACK_HOLES, SOLAR_WINDS, SOLAR_FLAMES (all primarily on negative ACF + Hurst + structural MR; weak IC).
- **NO_EDGE**: PLANETARY_RINGS (trending — Hurst ≈ 0.7 on log-VWAP returns).
- All 5 products carry `OBI_TAKER` flag.
- All 4 MR products carry `MM_CANDIDATE` flag (UNTESTED — no fills).
- No within-family pairs cleared the gate.

### SLEEP_POD
- **MR_TAKER**: SUEDE, LAMB_WOOL, POLYESTER, NYLON (mostly via vwap_acf_lag1 < −0.01 and vwap_hurst < 0.5).
- **NO_EDGE**: COTTON.
- 3 PAIR_ANCHOR edges: COTTON↔POLYESTER, POLYESTER↔SUEDE.
- 4 products carry `OBI_TAKER` flag (mostly **negative** obi_l3 IC — fade signal).

### MICROCHIP
- **MR_TAKER**: all 5 (CIRCLE via marginal acf, SQUARE via strong vr/acf, RECTANGLE/OVAL/TRIANGLE via vwap_hurst).
- 4 products carry PAIR_ANCHOR with various within-family partners (the family is highly correlated/anticorrelated).
- No OBI flags fire (book imbalance not predictive in this family).

### PEBBLES
- **MR_TAKER**: all 5 (mostly via Hurst + vwap_acf_lag1).
- 3 PAIR_ANCHOR edges: PEBBLES_S/XL/XS form a triangle of strong negative correlations.
- PEBBLES_XL has a HAC+FDR-passing `IC[neg_zscore_mid_50]` of +0.078 at h=100 — strongest mid-anchor IC in PEBBLES.

### ROBOT
- **MR_TAKER**: all 5. ROBOT_DISHES is the canonical case: vr_k5 = 0.555, acf_lag1 = −0.232, IC[neg_zscore_mid_50] = +0.115 at h = 1 (HAC t = +15.84, p ≈ 0). ROBOT_IRONING also strong.
- All 5 products are entangled in PAIR_ANCHOR edges.

### UV_VISOR
- **MR_TAKER**: AMBER, MAGENTA, YELLOW (mostly via vwap_acf_lag1).
- **NO_EDGE**: ORANGE, RED (no MR triggers fire).
- 3 PAIR_ANCHOR edges centred on AMBER (AMBER↔MAGENTA, AMBER↔ORANGE).
- All 5 products carry OBI_TAKER flag.
- 2 products carry MM_CANDIDATE flag (UNTESTED).

### TRANSLATOR
- **MR_TAKER**: ASTRO_BLACK, ECLIPSE_CHARCOAL, GRAPHITE_MIST, VOID_BLUE.
- **NO_EDGE**: SPACE_GRAY.
- 3 OBI_TAKER (negative obi_l3 IC — fade signal).
- No PAIR_ANCHOR (no within-family correlation cleared the gate).

### PANEL
- **MR_TAKER**: 1X2, 2X2, 4X4.
- **NO_EDGE**: 1X4, 2X4.
- 2 OBI_TAKER (PANEL_1X2 +obi_l1, PANEL_2X4 −obi_l3).
- No PAIR_ANCHOR.

### OXYGEN_SHAKE
- **MR_TAKER**: CHOCOLATE (vr=0.84, acf=−0.089, very strong MR), MORNING_BREATH, EVENING_BREATH (vr=0.80).
- **NO_EDGE**: MINT, GARLIC.
- 2 PAIR_ANCHOR (CHOCOLATE↔GARLIC).
- All 5 products carry OBI_TAKER flag.
- MORNING_BREATH carries MM_CANDIDATE flag.

### SNACKPACK
- **MR_TAKER**: all 5. CHOCOLATE/VANILLA via strong VR+ACF; RASPBERRY/STRAWBERRY/PISTACHIO via mid+VWAP combo.
- All 5 products carry OBI_TAKER flag with **strongest IC in the universe** (0.097–0.132).
- 3 PAIR_ANCHOR edges (CHOCOLATE↔VANILLA the dominant pair, corr=−0.93).
- 4 MM_CANDIDATE flags; SNACKPACK_VANILLA is the only **CONFIRMED** product (sim PnL +1350).
- **SNACKPACK_VANILLA carries all 4 archetype tags simultaneously**: MR_TAKER + PAIR_ANCHOR + OBI_TAKER + MM_CANDIDATE.

---

## 7. Cross-family findings

[cross_family.py](cross_family.py), driven by `cross_analysis.py`, runs once across the full 50-product universe to find structural clusters and inter-cluster lead-lag relationships. Results land in [round5/reports/CROSS/](reports/CROSS/).

### 7.1 Clustering

K-means on standardised features chooses **k = 2** with silhouette = +0.59 (strong separation):

- **C0** (46 products): broad cluster spanning all 10 families — dominant family GALAXY_SOUNDS but only 11% pure.
- **C1** (4 products): ROBOT and OXYGEN_SHAKE outliers — dominated by ROBOT (50% pure).

Bootstrap stability (timestamp resampling): mean ARI = 0.14 (gate = 0.5). **Family structure is NOT robust to resampling** — the named families don't map onto data-driven clusters. The named-family grouping is a labelling convention, not an emergent structural cluster.

### 7.2 Family rolling-performance ranking

Mean rank across rolling cumulative-return windows (1 = best):

| Family | Mean rank | Final cum return |
|---|---:|---:|
| SLEEP_POD | 4.02 | −238.3 |
| GALAXY_SOUNDS | 4.30 | −120.6 |
| OXYGEN_SHAKE | 5.32 | +139.0 |
| UV_VISOR | 5.61 | −171.3 |
| PANEL | 5.75 | +49.5 |
| SNACKPACK | 5.75 | −13.3 |
| PEBBLES | 5.79 | +0.1 |
| MICROCHIP | 6.10 | −138.2 |
| ROBOT | 6.18 | +41.5 |
| TRANSLATOR | 6.19 | +123.1 |

Note the spread: mean-rank doesn't correlate cleanly with cumulative return — TRANSLATOR has the worst rolling rank but the second-best cumulative outcome.

### 7.3 Stable cross-cluster lead-lag (1-tick)

Eight pairs hold their global lag in 100% of rolling windows. All center on SNACKPACK and operate at lag = 1 tick with negative correlation:

| Pair | corr | Granger p (lag 1) |
|---|---:|---:|
| OXYGEN_SHAKE → SNACKPACK | −0.069 | 1.7e-14 |
| SNACKPACK → UV_VISOR | −0.061 | 5.3e-25 |
| SNACKPACK → OXYGEN_SHAKE | −0.059 | 9.3e-20 |
| UV_VISOR → SNACKPACK | −0.058 | 5.7e-07 |
| GALAXY_SOUNDS → SNACKPACK | −0.056 | 3.1e-07 |
| TRANSLATOR → SNACKPACK | −0.056 | 4.0e-09 |
| SNACKPACK → GALAXY_SOUNDS | −0.055 | 8.2e-20 |
| PANEL → SNACKPACK | −0.051 | 9.3e-08 |

All pairs Granger-confirm at p < 1e-6 across lags 1–5. SNACKPACK is the central node — it both leads and lags multiple other families with persistent 1-tick negative correlation. The negative sign suggests a contrarian relationship (when other clusters move, SNACKPACK reacts opposite-direction at lag 1).

---

## 8. Output file inventory

Each family directory under `round5/reports/<FAMILY>/` contains:

| File | Content |
|---|---|
| `stats_per_product.csv` | One row per product. Mid stats (mean/std/range), returns (mean/std/skew/kurt), ACF at lags 1/5/20/100, VR at k=2/5/10, Hurst, ADF, VWAP analogues, microstructure (spread/depth/limit10), trade flow. |
| `microstructure.csv` | Spread / depth / saturation / trade-flow summary per product. |
| `signals_ic.csv` | Long-form: rows = (product, signal), cols include `ic_h{h}, n_h{h}, t_h{h}, p_h{h}` (HAC) and `significant` (BH-FDR pass). 7 signals × 4 horizons × 5 products. |
| `corr_mid.csv`, `corr_returns.csv`, `lead_lag.csv` | 5 × 5 within-family matrices on mid level / returns / 10-tick lead-lag. |
| `cointegration.csv` | Engle–Granger pair tests on all 10 within-family pairs. |
| `data_quality.csv` | Per-product NaN / crossed / stale / outlier / day-jump / empty-L1 + warnings. |
| `volatility.csv` | Per-product realised-vol distribution + clustering + day stability. |
| `vol_regime.csv`, `vol_regime_transitions.csv` | Tertile decomposition + 3 × 3 row-stochastic transition matrix. |
| `vol_conditioned_ic.csv` | Per-product × signal × regime × horizon IC table. |
| `archetype_assignment.csv` | Per-product primary archetype + rationale + params + all flag fields (see "Audit-traceability fields" below). |
| `tradeable_ideas.md` | Human-readable summary. Per-product candidates derived from `archetype_assignment.csv` (single source of truth — no parallel logic), pair listing, lead-lag listing, vol/sizing recommendations, and the archetype summary section. |
| `deep_triggers.md` | Lists products / pairs that crossed the deeper-research thresholds. Run with `--deep` to execute the dives. |
| `figures/` | 9 per-product PNGs (price, returns, ACF, spread, depth, OBI vs fwd-ret, signed flow, vol panel, vol regime) + 7 family-level PNGs (corr_mid, corr_returns, lead_lag, IC heatmap, summary, basis residuals, vol compare) + MM health figures for products that ran sim. |

Cross-cutting:

| Path | Content |
|---|---|
| `round5/reports/CALIBRATION/` | Threshold calibration table (CSV + MD), per-product calibration panel, distribution figures per gate. |
| `round5/reports/CROSS/` | Clustering, cluster aggregate series, cross-cluster lead-lag, stable pairs, Granger tests, bootstrap ARI, rolling vol distance, findings MD. |

### Audit-traceability fields in `archetype_assignment.csv`

The CSV ships 25 columns. The flags + metadata are designed so a downstream strategy compositor can risk-grade each classification without re-deriving the underlying stats.

**Primary** — `archetype` (one of `MR_TAKER`, `MOMENTUM`, `RANDOM_WALK`, `NO_EDGE`), `rationale` (semicolon-joined notes), `params` (anchor-signal config dict), `provisional` (boolean — set `True` only briefly during the RW sim gate).

**MR confidence metadata** — surfaced for every product (not just MR_TAKER) so NO_EDGE near-misses are diagnosable:
- `mr_n_triggers` — count of structural triggers that fired (0–7).
- `mr_triggers` — comma-joined names of firing triggers (e.g. `vr_lt,acf1_neg,vwap_acf1_neg`).
- `mr_ic_verified` — boolean. `True` only when a HAC + BH-FDR-passing positive IC exists on a mean-reversion signal (`neg_zscore_mid_50` or `neg_zscore_vwap_50`).
- `mr_contradictions` — semicolon-joined list of opposite-sign sister stats that fired alongside the MR triggers (e.g. `vr_k5=1.014>1.005 (trending signal); acf_lag1=+0.008>0.005 (positive autocorr)`). Empty string when clean.
- `mr_confidence` — three-level grade: `high` (FDR-pass IC OR ≥3 triggers, no contradictions), `medium` (2 triggers, no contradictions), `low` (1 trigger only OR any contradiction firing). The strategy compositor should size differently per level.

**PAIR_ANCHOR fields** — `is_pair`, `pair_partner`, `pair_corr` (signed), `pair_coint_p`, `pair_residual_stationary` (boolean: `True` ⇒ coint_p < 0.10 ⇒ fixed-β-hedged spread is suitable; `False` ⇒ entered via high-corr lane but residual non-stationary ⇒ rolling β required).

**OBI_TAKER fields** — `is_obi`, `obi_signal` (`obi_l1` or `obi_l3`), `obi_ic` (signed), `obi_horizon`, `obi_direction` (`follow` if IC > 0, `fade` if IC < 0). Strategy template MUST consult `obi_direction` to choose follow vs fade — the two are opposite trades.

**MM_CANDIDATE fields** — `mm_provisional` (transient — `True` only during sim gate), `is_mm` (final flag), `mm_pnl`, `mm_fills`, `mm_params` (Template-A `(min_edge_ticks, k_vol, gamma)` config). Three sim outcomes encoded in the rationale string: `MM_SIM_PASS` (PnL > 0 ⇒ `is_mm = True`), `MM_SIM_FAIL` (PnL ≤ 0 with fills ⇒ `is_mm = False`), `MM_SIM_UNTESTED` (0 fills due to sparse round-5 trades ⇒ `is_mm = True`, structural gate authoritative).

Verified completeness:

- **120 / 120** per-family CSV files present.
- **50 / 50** products covered in every CSV.
- **532** per-family PNG figures present.
- **70 / 70** family-level figures.
- **12 / 12** MM health figures (one per product where sim ran).
- IC table cells: 1,400 cells (7 signals × 4 horizons × 50 products), all populated with HAC `(t, p)` and BH-FDR `significant` flag.
- VWAP stats populated for all 50 products.
- All cross / calibration artifacts present.

---

## 9. Reproduction

From repo root, with `.venv` activated:

```bash
# Full pipeline (loads px+tr, runs HAC IC, classifier, sim gate, figures, deep-dive triggers)
.venv/Scripts/python.exe round5/family_report.py --family ALL

# Single family
.venv/Scripts/python.exe round5/family_report.py --family SNACKPACK

# Single family with deep dives (MR / trending / pair OU fits + threshold curves)
.venv/Scripts/python.exe round5/family_report.py --family SNACKPACK --deep

# Threshold calibration (must run after --family ALL)
.venv/Scripts/python.exe round5/calibration.py

# Cross-family clustering + lead-lag + Granger (must run after --family ALL)
.venv/Scripts/python.exe round5/cross_analysis.py

# Fast-path reclassification (no IC recompute; uses existing CSVs + runs MM sim)
.venv/Scripts/python.exe round5/reclassify.py
```

`reclassify.py` is the iteration tool when tuning gates: it skips the expensive HAC IC computation (~3 min/family for 1,200 HAC fits) and only re-runs the classifier + MM sim + tradeable_ideas synthesis. Useful for threshold sweeps.

---

## 10. Limitations & known issues

1. **Three days of data.** With n_days = 3, statistical power is intrinsically limited. HAC corrects naive overlap inflation but the underlying sample size at long horizons is small (≈ 30 effectively independent windows at h = 1000 per day). Long-horizon IC values (h = 100 / 1000) should be treated as candidates, not commitments.
2. **MM sim under-tested.** Round-5 trade activity is sparse: 10 of 11 MM_CANDIDATE products never got a fill in the 3-day Template-A simulation. The structural gate is authoritative for these UNTESTED products. The single CONFIRMED product (SNACKPACK_VANILLA) has only 1 fill and PnL = +1350; this is suggestive, not conclusive.
3. **Hurst estimator drift.** The R/S Hurst values reported here (0.45–0.55 for VWAP returns) are consistently higher than alternative estimators (DFA, periodogram) which can give 0.30–0.40 on the same series. The classifier gates `vwap_hurst < 0.50` are calibrated against R/S; using a different estimator would require re-tuning.
4. **No counterparty data.** Round 5 ships no buyer/seller IDs. Counterparty fingerprinting (which was alpha-rich in round 4) is unavailable. The trade-flow signals (`trade_imbalance`) approximate sign by comparing trade price to mid quote, not by aggressor ID.
5. **Cluster structure is weak.** Bootstrap ARI = 0.14 — the named-family grouping doesn't survive timestamp resampling. Cross-family lead-lag results should be treated with caution; the SNACKPACK-centred 1-tick negative-correlation pattern is robust under the gate but small in magnitude (|corr| ≈ 0.05–0.07).
6. **Doc/code drift risk.** [round5_research.md](round5_research.md) is the rolling notebook and reflects ongoing tuning; this PIPELINE_REPORT captures the state at a single point in time. After future gate changes, regenerate via `family_report.py --family ALL && calibration.py && cross_analysis.py` and re-export this report.

---

## 11. Audit-fix changelog

This section records the audit findings raised on the previous pipeline state and how they were addressed. The classifier was made *more transparent* rather than more conservative — every audit concern is now exposed as a queryable metadata field, so the strategy compositor can apply risk discounting without the pipeline having to choose a single threshold for everyone.

### 11.1 Findings raised

1. **Most MR_TAKER classifications lack predictability evidence.** 30 of 41 MR_TAKER products had no HAC + BH-FDR-passing IC on the anchor signal. The structural gates admit them, but only 11 have a verified alpha signal.
2. **PAIR_ANCHOR residual non-stationarity.** 8 of 14 unique pair edges were admitted via the high-corr lane (|corr| ≥ 0.7, no coint check) but have coint_p > 0.10 — the residual is non-stationary, so a fixed-β-hedged spread won't mean-revert.
3. **OBI sign ambiguity.** 9 of 29 OBI_TAKER flags have negative IC (fade signal). The classifier accepted both signs but the rationale didn't distinguish; a strategy can't deploy without knowing follow vs fade.
4. **Trigger fragility.** 10 of 41 MR products fired on exactly one structural trigger, often at threshold-boundary with non-significant Bartlett p-values (e.g. MICROCHIP_CIRCLE: acf₁ = −0.005 with Bartlett p = 0.378).
5. **Trigger contradictions.** Some MR products had opposite-sign sister stats firing simultaneously (e.g. UV_VISOR_YELLOW: structural MR triggers fired AND mid acf₁ = +0.003). The OR-conjunction admitted them anyway; the contradiction was invisible.
6. **Base-rate inflation.** Under independence, ~95% of products would fire ≥1 of the 7 structural triggers by chance at the calibrated thresholds. None of the gates is a formal-significance test.

### 11.2 Fixes applied

| Finding | Fix | New field(s) |
|---|---|---|
| #1 — IC support | Surface FDR-pass status per product | `mr_ic_verified` (bool) |
| #1, #4 — confidence grading | Three-level confidence grade based on trigger count + IC verification + contradictions | `mr_confidence` (`high` / `medium` / `low`), `mr_n_triggers` (int), `mr_triggers` (str) |
| #2 — pair non-stationarity | Distinguish stationary vs high-corr-only pairs in output | `pair_residual_stationary` (bool: `True` iff coint_p < 0.10) |
| #3 — OBI sign | Add explicit follow/fade direction from sign of IC | `obi_direction` (`follow` / `fade` / `None`) |
| #5 — contradictions | Compute opposite-sign sister stats firing alongside MR triggers; record in rationale; force `mr_confidence = low` when present | `mr_contradictions` (str — semicolon-joined list, empty when clean) |
| #6 — base-rate transparency | Documented in this report (Section 4 + the audit acknowledges the inclusivity tradeoff). Strategy compositor should treat `mr_confidence = low` as candidates pending live verification, not commitments. | (no new field — uses existing `mr_confidence`) |

### 11.3 Post-fix universe state

| Confidence | MR_TAKER count | Suggested risk allocation |
|---|---:|---|
| `high` | 19 | Full size — robust structural MR + (FDR-IC OR ≥3 triggers), no contradictions |
| `medium` | 5 | Half size — 2 triggers, no contradictions |
| `low` | 17 | Skip or 1/4 size — single trigger or contradicted; live data should confirm |

Of the 19 `high`-confidence MR products, 11 have HAC + BH-FDR-passing positive IC (`mr_ic_verified = True`); the other 8 are admitted on ≥ 3 corroborating structural triggers without an FDR-pass IC — still high confidence because three independent stats agreeing is unlikely under noise.

| Pair tier | Count | Strategy template |
|---|---:|---|
| Stationary (coint_p < 0.10) | 6 | Fixed-β hedged spread, threshold-z trade |
| Non-stationary high-corr | 8 | Rolling-β re-estimation; treat as relative-value not stationary spread |

| OBI direction | Count | Strategy direction |
|---|---:|---|
| `follow` (IC > 0) | 20 | Buy when book leans bid, sell when book leans ask |
| `fade` (IC < 0) | 9 | Opposite — book imbalance precedes reversal (mostly SLEEP_POD + TRANSLATOR families on `obi_l3`) |

### 11.4 What the fixes did NOT change

- The four primary archetype classes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) remain unchanged.
- The orthogonal flag set (PAIR_ANCHOR / OBI_TAKER / MM_CANDIDATE) is unchanged.
- The MR_TAKER count remains 41 (no products demoted) — the audit response was to *grade* classifications, not gate them out, so the inclusivity gain is preserved.
- Existing strategy templates that ignore the new metadata fields continue to work.

The fixes are purely additive metadata. A strategy compositor that uses `mr_confidence`, `pair_residual_stationary`, and `obi_direction` will deploy risk only to verified candidates; one that ignores them gets the same coverage as before. Both modes are supported.
