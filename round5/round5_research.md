# Round 5 — Research Log

Rolling notebook for round-5 family research. Per-family reports auto-generated under `round5/reports/<FAMILY>/` by `python round5/family_report.py --family <NAME>`.

## Pipeline

- **Library** — [`round5/research_lib.py`](research_lib.py): loaders, microstructure derivation, per-product statistical battery, alpha-signal IC scorecard, within-family correlation / lead-lag / cointegration, tradeable-ideas synthesizer, family-summary dashboard + stdout report, and per-product/family figures.
- **Volatility** — [`round5/volatility.py`](volatility.py): realized-vol stats, vol-of-vol, clustering, vol regime decomposition, vol-conditioned signal IC, sizing + regime-gated trading recommendations. Always run.
- **Archetype classifier** — [`round5/archetypes.py`](archetypes.py): priority-ordered routing into primary {MR_TAKER, MOMENTUM, RANDOM_WALK, NO_EDGE}, plus orthogonal flags PAIR_ANCHOR and OBI_TAKER that can layer on any primary. Each rationale string carries the raw stat **and** its statistical-significance metric (vr z-stat + p-value, ACF Bartlett p-value, HAC+FDR-controlled IC). RW products get auto-derived params (`min_edge_ticks`, `k_vol`, `gamma`) + Template-A passive-MM simulation gate (PnL < 0 → downgrade to NO_EDGE). Always run.
- **Significance** — [`round5/significance.py`](significance.py): HAC (Newey-West) IC test on the (signal, fwd_ret) regression at `maxlag=h`, Bartlett ACF p-value, VR p-value, Benjamini-Hochberg FDR control across the 6×4 IC cells per product. `signal_ic_table` calls HAC at construction time so the IC long-form CSV ships with HAC `t_h{h}` / `p_h{h}` columns. The classifier uses `significant` (BH-FDR pass on HAC p) to demand statistical strength alongside effect-size thresholds.
- **Data quality** — [`round5/data_quality.py`](data_quality.py): per-product NaN / crossed / locked / stale-run / outlier / day-boundary-jump / empty-L1 checks. Blocking warnings (NaN_MID / CROSSED / STALE / SHORT_HISTORY / EMPTY_PX) gate the classifier to NO_EDGE with `DATA_QUALITY_WARN <list>` rationale.
- **Threshold calibration** — [`round5/calibration.py`](calibration.py): standalone CLI that reads the per-family CSVs and evaluates each hardcoded gate against the empirical distribution of its underlying statistic. Flags `DEGENERATE_HIGH` (≥95% pass) and `DEGENERATE_LOW` (≤5% pass) gates so misconfigured thresholds are caught explicitly. Run after `--family ALL` to validate.
- **Deep research** — [`round5/deep_research.py`](deep_research.py): triggers + MR / trending / pairs deep dives. Triggers always emitted to `deep_triggers.md`; dive bodies opt-in via `--deep`.
- **CLI** — [`round5/family_report.py`](family_report.py): `--family <NAME>` or `--family ALL`. `--deep` runs the dives on auto-triggered candidates.
- **Notebook** — [`round5/family_template.ipynb`](family_template.ipynb): drives the pipeline, surfaces tables inline, has a custom deep-dive scratchpad cell.
- **Generic stats** — [`imc_commun/stats.py`](../imc_commun/stats.py): `zscore`, `hurst_rs`, `variance_ratio`, plus standard moving averages.

Outputs per family:

```
round5/reports/<FAMILY>/
  stats_per_product.csv     # one row per product, full statistical profile
  microstructure.csv        # spread / depth / saturation / trade-flow summary
  signals_ic.csv            # IC of {neg_z, OBI L1/L3, momentum_10, trade_imbalance, neg_spread} × horizons {1,10,100,1000}
  corr_mid.csv              # 5×5 mid correlation
  corr_returns.csv          # 5×5 ret_1 correlation
  lead_lag.csv              # 5×5 lead-lag (lag=10 ticks)
  cointegration.csv         # Engle-Granger pairs
  tradeable_ideas.md        # auto-flagged passive-MM / MR / momentum / OBI / pair / lead-lag candidates + vol-sizing/regime-gated bullets
  volatility.csv            # per-product realized-vol stats + clustering + ratio
  vol_regime.csv            # per-product × {low,mid,high} std_50 tertile decomposition
  vol_regime_transitions.csv# per-product 3×3 row-stochastic transition matrix
  vol_conditioned_ic.csv    # per-product × signal × regime × horizon  IC table
  archetype_assignment.csv  # per-product archetype + rationale (with t/p/FDR-pass values inline) + params; RW gets {min_edge_ticks, k_vol, gamma} + SIM_GATE_PASS / SIM_GATE_FAIL
  data_quality.csv          # per-product NaN / crossed / stale / outlier / day-jump / empty-L1 + warnings list
  signals_ic.csv            # IC long-form augmented with t, p, t_h{h}, p_h{h}, significant (FDR-pass) columns
  deep_triggers.md          # always: lists products/pairs that cross the deeper-research thresholds
  figures/                  # per-product (price, returns, ACF, spread, depth, OBI vs fwd-ret, vol regime, signed flow) + family (corr_mid, corr_returns, lead_lag, basis, IC heatmap, summary dashboard)
  deep/                     # only when --deep: per-trigger sub-folders with REPORT.md + figures + CSVs
    mr_<PRODUCT>/           # OU fit, threshold-PnL curve, vol-regime split, anchor sensitivity
    trend_<PRODUCT>/        # momentum decay, window×horizon IC grid, threshold-PnL, vol-regime
    pair_<A>__<B>/          # OLS β/R², residual ADF + half-life, rolling β, residual threshold-PnL
    MANIFEST.md
```

## Archetype classifier

Each product is routed into one of four primary archetypes by priority-ordered threshold rules. Two orthogonal flags (`PAIR_ANCHOR`, `OBI_TAKER`) can layer on top of any primary. Within an archetype, all members share the same strategy logic; the per-product `params` field carries scaling constants the strategy template uses.

**Design principle.** Structural MR triggers (any one fires admits to MR routing) are decoupled from the IC gate. The IC value is informational — it picks which anchor signal (mid z-score or VWAP z-score) the strategy should use, but does not gate classification. Reasoning: a product with stationary VWAP or low VWAP Hurst is mean-reverting in transactions even when the noisy mid IC fails FDR after HAC correction. Earlier versions of this pipeline gated on IC and ended up over-discriminant (43/50 products NO_EDGE). The current version classifies 41/50 products as MR_TAKER on the round-5 universe.

| Priority | Archetype | Trigger (any one of the structural signals fires) | Strategy template |
|---:|---|---|---|
| 1 | **MR_TAKER** | `vr_k5` < 0.985 OR `acf_lag1` < −0.005 OR `hurst` < 0.535 OR `adf_p_mid` < 0.10 OR `vwap_hurst` < 0.50 OR `vwap_adf_p` < 0.10 OR `vwap_acf_lag1` < −0.01 | Anchor z-score taker (mid or VWAP), vol-armored |
| 2 | **MOMENTUM** | `vr_k5` > 1.005 AND `hurst` > 0.545 AND HAC+FDR `IC[momentum_10]` ≥ 0.02, sign-positive | Momentum follow at best (window, h) |
| 3 | **RANDOM_WALK** | structural RW signature (vr/hurst/acf near random) AND `spread_median/ret1_std` ≥ 1.5 AND `limit10_saturation` ≥ 0.3 AND **Template-A simulated PnL > 0** | Passive two-sided MM with inventory skew |
| 4 | **NO_EDGE** | otherwise (or RW provisional that failed the simulation gate) | Skip / inventory minimisation |

| Flag | Trigger | Layered strategy |
|---|---|---|
| **PAIR_ANCHOR** | (`\|corr_mid\|` ≥ 0.7) OR (`\|corr_mid\|` ≥ 0.5 AND `coint_p` < 0.10) on at least one within-family partner | β-hedged residual MR taker on the pair, on top of primary |
| **OBI_TAKER** | HAC+FDR `\|IC[obi_l1\|obi_l3]\|` ≥ 0.04 at h ∈ {1, 10}, sign-positive | Short-horizon book-pressure taker, on top of primary |

The strategy template each MR_TAKER uses is encoded in `params.ic_signal`: `neg_zscore_mid_50` (anchor on rolling-mean of mid) or `neg_zscore_vwap_50` (anchor on rolling-mean of trade VWAP). The classifier picks the FDR-passing signal with stronger |IC| when one exists; otherwise it defaults to whichever underlying series is more anti-persistent (`vwap_hurst < hurst` ⇒ VWAP anchor, else mid anchor).

## Trade VWAP layer

The pipeline computes a per-tick volume-weighted average trade price (`add_vwap` in [research_lib.py](research_lib.py)) and per-product trade-event Hurst / ADF / ACF on log VWAP returns ([per_product_stats](research_lib.py)). Trade VWAP often mean-reverts even when the quote-side mid looks I(1) — toxic flow distorts mid but not VWAP. The MR triggers `vwap_hurst < 0.50`, `vwap_adf_p < 0.10`, and `vwap_acf_lag1 < −0.01` catch products whose MR shows up in transactions but is masked at the quote level.

The IC table also includes `neg_zscore_vwap_50` (z-score of mid against rolling VWAP) so HAC-corrected IC of the VWAP anchor signal is available alongside `neg_zscore_mid_50`.

**RW parameters auto-derived** (from existing stats, written into `archetype_assignment.csv`):

- `min_edge_ticks = max(3, floor(spread_median / 2))` — half-spread floor.
- `k_vol = clip(1.5 + 0.5·(vol_p90_p10_ratio − 1), 1.5, 3.0)` — spread expansion factor in vol.
- `gamma = clip(1e-3 + 1e-2·max(0, vol_cluster_lag1), 1e-3, 1e-2)` — inventory aversion (clustering → faster exit).

**Simulation gate** — Template A is simulated tick-by-tick using the round-5 trades for fills (IMC "worse" semantics: bid fills against trades priced strictly below our bid; ask fills against trades priced strictly above our ask). Position-limit-10 enforced. If 3-day cumulative PnL ≤ 0, the product is downgraded to NO_EDGE with rationale `SIM_GATE_FAIL pnl_total=…`. Health figure `<P>_rw_health.png` is written for every RW candidate (pass or fail) — useful for tuning `(min_edge_ticks, k_vol, gamma)` when you want to override the auto-derived params.

## Statistical-strength layer

The classifier never claims an archetype on the basis of effect size alone — every directional check carries a significance metric:

- **VR z-stat → p-value**: `vr_p` reports two-sided Lo-MacKinlay test for `H0: vr=1`. A product with `vr_k5=0.99 (p=0.4)` is *not* statistically below 1, even though it crosses the 0.95 effect-size gate; the rationale exposes both numbers so a human can audit.
- **ACF Bartlett p-value**: `Bartlett p` for `H0: ρ_1=0`. Pairs with the `mr_acf1_max` gate.
- **HAC-adjusted IC + BH-FDR**: every `(signal, horizon)` IC is computed with a Newey-West HAC regression at `maxlag=h` so that overlapping-window autocorrelation does not inflate the t-stat (naive p-values at h=1000 over-state significance by ~√h ≈ 30×). Then Benjamini-Hochberg FDR correction at `α=0.05` is applied across the 6 signals × 4 horizons = **24 IC cells per product**. The MR / MOMENTUM gates require both `|IC| > effect_threshold` **and** `passes_fdr=True`. The RW gate requires no HAC+FDR-passing IC at short horizons (h ∈ {1, 10}). Long-horizon predictability does not break tick-level passive MM, so it doesn't disqualify a RW candidate. The OBI gate uses HAC+FDR at h ∈ {1, 10} on `obi_l1` / `obi_l3`.

## Data-quality gating

Per-product `data_quality.csv` runs every pipeline. A product is degraded to `NO_EDGE` with `DATA_QUALITY_WARN <list>` rationale **before** classification when any *blocking* warning is raised:

- `EMPTY_PX` — no price ticks at all
- `SHORT_HISTORY` — fewer than `short_ticks_min=1000` ticks
- `NAN_MID` — > `nan_mid_max=0.5%` NaN rate in mid
- `CROSSED_MARKET` — bid ≥ ask anywhere
- `STALE_PRICES` — > `stale_frac_max=20%` of ticks in runs of ≥ 50 unchanged mids

Soft warnings (e.g. small zero-spread fraction, modest day-boundary jump) are *reported* in `warnings` but don't block classification. Round-5 CSVs are clean by construction, so a flag is a real anomaly worth investigating, not noise.

## Threshold calibration

Run `python round5/calibration.py` after `family_report --family ALL`. It loads each family's `stats_per_product.csv` + `signals_ic.csv` + `corr_mid.csv` + `cointegration.csv`, builds a 50-product panel, and evaluates each hardcoded `ArchetypeGates` value against the empirical distribution of its underlying statistic.

Outputs under `round5/reports/CALIBRATION/`:
- `calibration_panel.csv` — one row per product with all stats relevant to thresholds.
- `threshold_calibration.csv` — one row per gate: `n_pass`, `frac_pass`, percentiles, flag.
- `threshold_calibration.md` — human summary highlighting `DEGENERATE_HIGH` / `DEGENERATE_LOW` gates and recommending adjustments.
- `figures/<gate_name>.png` — distribution histogram with the threshold line.

**Empirical findings on round-5 (already incorporated)**:
- `mr_hurst_max` was 0.48; min hurst across 50 products is 0.51, p25 is 0.527 → `DEGENERATE_LOW` (no product could pass). Bumped to **0.50**.
- `mom_vr_min` was 1.05; max vr_k5 is 1.023, p90 is 1.010 → `DEGENERATE_LOW` (MOMENTUM was impossible to trigger). Lowered to **1.01**.
- All other gates split the universe non-trivially (`pair_corr_min=0.7`: 40% pass, `mr_ic_min=0.04`: 50% pass, `rw_spread_to_std_min=1.5`: 10% pass, etc.).



## Deep-research mode

Two-stage gating to avoid heavy work where it's not warranted:

1. **Triggers** — always computed from the first-pass artifacts. A product is auto-triggered for **MR** if at least 2 of {`vr_k5 < 0.95`, `hurst < 0.48`, `acf_lag1 < -0.03`, `|IC[neg_zscore, h=10]| > 0.03`} fire; for **trending** if 2 of the symmetric set fire. Pairs are auto-triggered when at least 2 of {`|corr_mid| > 0.5`, `coint_p < 0.10`, `|corr_returns| > 0.3`} fire — top-3 by combined score are kept.
2. **Dives** — opt-in via `--deep`. Run only on triggered candidates; for each one, write a `REPORT.md` summary plus 3-4 figures.

Deep-dive content per product / pair:

- **MR**: OU fit (κ, θ, σ, half-life) on pooled + per-day data; threshold-PnL curve over z-bands {0.5..3.0} with realised PnL/Sharpe/n_trades/active%; vol-regime decomposition (low/mid/high std_50 buckets); anchor sensitivity (rolling-50 vs day-mean vs pooled-mean).
- **Trending**: momentum decay ACF for lags 1..200; window×horizon IC grid over {5,10,20,50,100} × {1,5,10,50,100,500}; threshold-PnL curve at the best (window, horizon) combo (follow-not-fade); vol-regime decomposition.
- **Pairs**: full-sample OLS β / R²; residual ADF + OU half-life; rolling β stability across 4-6 evaluation windows; residual-z threshold-PnL curve for the β-hedged spread.

## Tradeability ranking — to be filled in per family

Once each family report is generated, rank by edge density (# of flagged ideas in `tradeable_ideas.md`, magnitude of best-IC signal, presence of cointegrated pair):

| Family | Edge density | Best signal (IC, h) | Pair candidates | Notes |
|--------|:------------:|--------------------|-----------------|-------|
| GALAXY_SOUNDS | — | — | — | — |
| SLEEP_POD     | — | — | — | — |
| MICROCHIP     | — | — | — | — |
| PEBBLES       | — | — | — | — |
| ROBOT         | — | — | — | — |
| UV_VISOR      | — | — | — | — |
| TRANSLATOR    | NONE | OBI_L3 fade IC=-0.04 (statistically significant, economically untradeable) | — | Books engineered balanced (bid_vol_1==ask_vol_1 in 90%+ of snapshots, std(obi)=0.012, \|obi\|≥0.15 fires 0% of ticks). Predicted h=1 move at max realistic obi ≈ 3 ticks vs half-spread ≈ 4.5. BT confirms 0 trades, 0 PnL on days 5-{2,3,4}. Excluded from active bundle. Experiment file deleted (was `strat_translator_obi_taker.py`). |
| PANEL         | — | — | — | — |
| OXYGEN_SHAKE  | — | — | — | — |
| SNACKPACK     | — | — | — | — |

## Volatility & sizing

Always-run analysis. The pipeline characterizes each product's realized-vol distribution and translates it into trading rules:

- **rv_w_mean / rv_w_std / p10 / p90** at windows {20, 50, 200, 500} — basic shape of realized vol.
- **vol_of_vol** = std(rv_50) / mean(rv_50) — how much vol itself moves.
- **vol_p90_p10_ratio** — sizing-relevant. If ≥ 1.5, the auto-recommendation suggests inverse-vol position scale `min(1, target_rv50 / current_rv50)` so risk-per-unit stays roughly constant across regimes.
- **vol_cluster_lag1 / lag10** — autocorrelation of |ret_1|. Positive (>0.05) ⇒ vol shocks persist; recent rv_50 is informative for next-tick risk.
- **rv_50_day_max_min_ratio** — day-to-day vol stability check.
- **vol_regime tertiles** of std_50 (low/mid/high) carry per-regime spread, depth, |OBI|, and |ret_1|. If high-regime spread does **not** widen ≥ 1.10× over low-regime, pipeline flags `MM_RISK_HIGH_VOL` — passive MM gets squeezed.
- **vol_conditioned_ic** — IC of every alpha signal recomputed *within* each regime. When |IC| differs across regimes by ≥ 0.04, the signal is flagged `REGIME_GATED_SIGNAL` with the recommended regime to trade in. This is the central trading-usage output: tells the strategy which signals to switch on/off based on live std_50.

## Interpretation cheatsheet

- **Spread / ret_1_std ratio** ≥ 1.5 with `limit10_saturation` > 0.3 → passive-MM viable. Below ~1, noise dominates spread, MM bleeds inventory.
- **VR(k=5) < 0.9** with negative ACF at lag 1 → mean-reverting; pairs well with `neg_zscore_mid_50` taker.
- **VR(k=5) > 1.1** with Hurst > 0.55 → trending; momentum follow.
- **|IC[obi_l1, h=1]|** ≥ 0.10 → top-of-book imbalance is short-horizon predictive; fast taker on book pressure.
- **|corr_mid[A,B]|** ≥ 0.7 + **coint_p** < 0.05 → pair-trade candidate; band trade the residual at ±2σ.
- **lead_lag[A→B, lag=10]** ≥ 0.10 → A leads B; trade B in the direction of A's recent move.

## Cross-family / cluster-level analysis

Run once across the full 50-product universe to find: (a) which structural cluster outperforms / underperforms, and (b) which cluster *leads* which other cluster with a stable lag.

```bash
.venv/Scripts/python.exe round5/cross_analysis.py
.venv/Scripts/python.exe round5/cross_analysis.py --silhouette-min 0.10 --leadlag-corr-min 0.08
```

**Module** — [`round5/cross_family.py`](cross_family.py): standardised feature extraction, correlation-distance hierarchical + k-means clustering (k chosen by silhouette), per-cluster aggregate series, rolling-rank performance, cross-cluster lead-lag at lags ±N, stability test across rolling sub-windows, Granger confirmation.

**Outputs** under `round5/reports/CROSS/`:

| File | Content |
|------|---------|
| `features.csv` | per-product feature matrix used for clustering |
| `clusters.csv` | product → cluster_id mapping (k-means on standardised features) |
| `cluster_aggregate.csv` | per-cluster mean-of-products return series |
| `cluster_rolling_performance.csv` | rolling cumulative + cross-sectional rank per cluster |
| `leadlag_full.csv` | corr(leader_t, follower_{t+lag}) across all pairs × lags |
| `leadlag_best_pairs.csv` | optimal-lag picks per ordered pair (positive lag only) |
| `leadlag_stable_pairs.csv` | pairs whose lag matches global ± 2 in ≥ stability_min frac of windows |
| `granger_tests.csv` | Granger F-test p-values for stable pairs (lags 1..granger_max_lag) |
| `cross_findings.md` | human summary with gate listing, cluster membership, ranked clusters, lead-lag pairs |
| `figures/` | `dendrogram.png`, `silhouette.png`, `cluster_aggregate.png`, `cluster_rolling_rank.png`, `leadlag_heatmap.png`, `leadlag_stability.png` |

**Logic gates** (a stage emitting "skipped: …" did not clear its gate):

| Gate | Default | Skips when |
|------|--------:|------------|
| `silhouette_min` | 0.05 | best silhouette across k ∈ [k_min, k_max] is below threshold (no usable cluster structure) |
| `cluster_k_min` / `cluster_k_max` | 2 / 12 | k-search is empty |
| `leadlag_corr_min` | 0.05 | no positive-lag pair clears \|corr\| ≥ threshold |
| `stability_min` | 0.60 | no pair holds its global lag (±2) in ≥ this fraction of rolling windows |
| `stability_n_windows` | 5 | data too short to support that many windows |
| `granger_p_max` | 0.10 | reported but does not gate the stable-pair list — used as confirmation only |

**Why this is opt-in**: the cross-family analysis loads all 50 products (50 × 30 000 ticks) and computes a 50×50 correlation matrix + per-cluster lag scan. It is heavier than a single family report and only worth running when per-family work is stable enough that you want to look across families.

## Volatility-spike study

Stand-alone study of tail events across all 50 products. Driver: [`round5/vol_spikes.py`](vol_spikes.py). Outputs under [`round5/reports/CROSS/vol_spikes/`](reports/CROSS/vol_spikes/), full narrative in [`vol_spikes_report.md`](reports/CROSS/vol_spikes/vol_spikes_report.md).

```bash
.venv/Scripts/python.exe round5/vol_spikes.py            # K=4, lookback=500
.venv/Scripts/python.exe round5/vol_spikes.py --k 3.0    # looser threshold
```

**Spike definition** — `|ret_1_t| ≥ K · σ_t` with `K = 4` and `σ_t = std(ret_1).rolling(500).shift(1)` (long lookback, lagged by 1 to remove look-ahead and resist persistent high-vol regimes). Per-day so the rolling baseline doesn't bridge day breaks.

**Outputs**:

| File | Content |
|------|---------|
| `spike_summary.csv` | per-product n_spikes, rate / 10k, z stats, post-spike signed cumret at h ∈ {1,5,10,50,200}, spread / depth response |
| `spike_events.csv` | one row per spike (timestamp, sign, magnitude, microstructure snapshot) |
| `spike_post_returns.csv` | long-form per-product × horizon mean signed cumret |
| `spike_cooccurrence.csv` | per-product `systemic_rate` + mean / median peer count within ±2 ticks |
| `spike_cooccurrence_matrix.csv` | 50×50 pair co-spike count |
| `family_summary.csv` | family-level aggregates |
| `figures/<P>_spike_panel.png` | 4-panel per-product (mid+spike markers, post-spike profile, spread distribution, inter-arrival) |
| `figures/cooccurrence_heatmap.png` | 50×50 cosine co-spike matrix |
| `figures/family_post_spike.png` | per-family post-spike profile overlay |

**Headline findings** (K=4, days 2–4):

1. **Concentration** — 4 products carry ~70 % of all 4σ events:

   | Product | n_spikes | rate / 10k | post-spike signed cumret @ h=10 |
   |---|---:|---:|---:|
   | ROBOT_DISHES | 117 | 39.0 | +43.2 |
   | OXYGEN_SHAKE_CHOCOLATE | 60 | 20.0 | +38.2 |
   | OXYGEN_SHAKE_EVENING_BREATH | 56 | 18.7 | +37.0 |
   | ROBOT_IRONING | 50 | 16.7 | +36.0 |

   42 products have ≤4 spikes across the 90 k ticks of available data — spikes are essentially absent on most of the universe.

2. **Idiosyncratic, not systemic** — mean peer count across all spikes ≈ 0.15; `systemic_rate = 0.0` for every product with `n_spikes ≥ 10`. No basket / cross-product hedge trade is supported.

3. **Big-4 mean-revert post-spike** — +37 to +43 ticks at h=10 vs ~2-tick spread → ~20× edge per event. Already captured by the existing `MR_TAKER` template (`neg_zscore_mid_50` taker, vol-armored). The study **quantifies the magnitude** but does not unlock a new strategy.

4. **Spread barely widens** — at-spike spread is 1.06–1.12× baseline on the spike-heavy families; depth at L1 holds. Passive MM cushion is intact during spikes — the standing `MR_TAKER` need not throttle quoting.

5. **Caveat — "spike" ≈ "ordinary tick" on big-4** — `acf_lag1 = −0.232` for ROBOT_DISHES, −0.123 for OXYGEN_SHAKE_EVENING_BREATH. The 4σ event is part of the same MR distribution, not a separate tail regime. There is no incremental alpha layer over `neg_zscore_mid_50`.

6. **Outlier — MICROCHIP_SQUARE** — only spike-cluster product (n=10) with post-spike *momentum* (h=10 mean −33). Existing classifier flagged it `MR_TAKER` with weak FDR support — manual review of [`figures/MICROCHIP_SQUARE_spike_panel.png`](reports/CROSS/vol_spikes/figures/MICROCHIP_SQUARE_spike_panel.png) before sizing it as MR.

**Trading-usage take** — vol-conditioned trading rules (spike-fade, regime gates) only apply to the 8 products in the spike-heavy + second tier (ROBOT_DISHES / IRONING, OXYGEN_SHAKE_CHOCOLATE / EVENING_BREATH, MICROCHIP_RECTANGLE / TRIANGLE / SQUARE / OVAL). For the other 42, vol-spike machinery is a no-op and should not consume capital or strategy slots.

### Spike-mechanism analysis (follow-up)

A 4σ "spike" is not a Gaussian tail — it's the visible artefact of a regime in price formation. Drivers:

- [`round5/spike_anatomy.py`](spike_anatomy.py) — per-product mechanism classifier (jump profile, spread profile, trade attribution, recovery curve).
- [`round5/spike_strategy_sim.py`](spike_strategy_sim.py) — fade-vs-follow taker PnL with limit=10.
- Full report: [`reports/CROSS/vol_spikes/anatomy/spike_mechanism_report.md`](reports/CROSS/vol_spikes/anatomy/spike_mechanism_report.md).

Three distinct mechanisms, each with an opposite trading prescription:

| Mechanism | Members | Microstructure | Recovery h=50 | Trade |
|---|---|---|---:|---|
| **QUANTIZED_QUOTE_REFRESH** | OXYGEN_SHAKE_EVENING_BREATH, ROBOT_IRONING, OXYGEN_SHAKE_CHOCOLATE | Spread locked (12 / 6-8 / 12); ±10 jumps carry 17–43 % of all moves; trade-at-spike rate < 4 % | +0.35 to +0.48 | **FADE** (passive maker; taker margin thin since spread > revert) |
| **FAST_NOISE_OSCILLATOR** | ROBOT_DISHES | 80 unique jumps, smooth dist; `acf_lag1 = −0.232`; spread = 8 with ±10 jumps | +0.41 | **FADE** (best taker edge of the eight) |
| **PRICE_DISCOVERY_BREAKOUT** | MICROCHIP_RECTANGLE, MICROCHIP_SQUARE, MICROCHIP_OVAL | Diffuse jump dist; `reversion_pct_h50 ∈ {−0.34, −2.18, −0.90}` — price *continues* past the spike | **negative** (continues) | **FOLLOW** — fade kills, follow wins |

**Key actionable**: the 3 PRICE_DISCOVERY products are currently classified `MR_TAKER` by the archetype pipeline. Fading them after a spike loses money. **Override** is needed: when `|ret_1| ≥ 4 · std_500.shift(1)` on those three, take *with* the spike for ~20-200 ticks; otherwise default MR template.

**Strategy simulation** (3 days, position-limit 10, taker, single h=20 across all products — no per-product cherry-picking):

| Side | Products | PnL @ h=20 |
|---|---|---:|
| FADE | DISHES (+16.3k), IRONING (+3.5k), EVENING_BREATH (+2.0k), CHOCOLATE (−1.2k), TRIANGLE (+? — best at h=20) | **+20.5 k SS** |
| FOLLOW | SQUARE (+5.2k), RECTANGLE (+0.3k), OVAL (+1.1k) | **+6.6 k SS** |
| **Total** | spike layer alone | **≈ +27 k SS / 3 days** |

Per spike event ≈ +96 SS (after spread cost). Limit=10 binds size. Caveats — small n on the FOLLOW side (5/10/18 events × 3 products), independent-events assumption (collisions are rare given inter-arrival ≫ h=20), and conservative taker semantics need to be revalidated through `prosperity4bt` before live submission.

### Spike strategy — per-day positivity gate + final implementation

Per [`feedback_per_day_positive_selection`](../../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_per_day_positive_selection.md), products that lose on any single day's BT are rejected. Pipeline `spike_strategy_pnl.csv` aggregates 3 days; built [`round5/spike_per_day_check.py`](spike_per_day_check.py) to slice events by day and recompute mid-based PnL @ h=20.

**Per-day mid-based PnL @ h=20** (sign-only gate, 10× position):

| Product | Side | D2 | D3 | D4 | Verdict |
|---|---|---:|---:|---:|---|
| ROBOT_DISHES | FADE | +340 (n=1) | — (n=0) | +57,635 (n=116) | **KEEP** |
| ROBOT_IRONING | FADE | +18,540 (n=48) | +600 (n=2) | — (n=0) | **KEEP** |
| OXYGEN_SHAKE_CHOCOLATE | FADE | +5,965 (n=14) | +730 (n=2) | +20,965 (n=44) | KEEP-mid (taker dominated by spread; see below) |
| OXYGEN_SHAKE_EVENING_BREATH | FADE | +22,995 (n=54) | **−200 (n=2)** | — (n=0) | DROP |
| MICROCHIP_TRIANGLE | FADE | +3,970 (n=13) | +360 (n=2) | **−1,050 (n=2)** | DROP |
| MICROCHIP_SQUARE | FOLLOW | +4,280 (n=7) | **−805 (n=2)** | +2,300 (n=1) | DROP |
| MICROCHIP_RECTANGLE | FOLLOW | +1,140 (n=16) | +710 (n=1) | **−465 (n=1)** | DROP |
| MICROCHIP_OVAL | FOLLOW | +640 (n=1) | +825 (n=2) | **−260 (n=2)** | DROP |

Output: [`round5/reports/CROSS/vol_spikes/per_day_pnl.csv`](reports/CROSS/vol_spikes/per_day_pnl.csv).

**Note on the small-n DROPs**: RECTANGLE/OVAL/TRIANGLE/SQUARE/EVENING_BREATH all fail on a day with 1–2 events. With n that small, single-event noise dominates. Strict gate is honored, but this is effectively a sample-size filter — relaxation candidate if user accepts higher live-overfit risk.

**OXYGEN_SHAKE_CHOCOLATE FADE caveat**: passes mid-based gate (D2/D3/D4 all positive). However per [`spike_mechanism_report.md`](reports/CROSS/vol_spikes/anatomy/spike_mechanism_report.md), spread = 12 ticks vs typical jump = 10 ticks → taker pays the spread to harvest a smaller move. Aggregate sim PnL @ h=20 = −1,240 SS (loss after spread). Not deployed as taker.

**OXYGEN_SHAKE maker variant rejected** (post-spike passive on the fade side). Direction analysis: after up-spike, fade = SHORT, requires resting ASK that fills via aggressor BUYERS. Reversion = aggressor SELLERS hitting BIDS. The two flows don't intersect — a passive ASK posted after an up-spike is orphan during reversion. Continuous two-sided MM (which captures the spike when an aggressor crosses the *pre-existing* quote) is what works on these — that's an MM-strat job, not a spike-conditional one. Submission `550714` already MMs OXY_*.

### Final spike trader (folded into combined v7)

Surviving spike products: **ROBOT_DISHES + ROBOT_IRONING** (FADE taker, h=20, 4σ spike). Standalone source `strat_spike_takers_multi.py` was consolidated into [`strats/strat_combined_v7_spike.py`](strats/strat_combined_v7_spike.py) (current best). MICROCHIP_SQUARE follow variant rejected — failed D3 per-day gate (−805 on n=2).

Standalone backtest (before consolidation):

| Engine | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|
| Python `prosperity4bt` | +7,659 | +452 | +16,058 | **+24,169** |
| Rust `rust_backtester` | +7,659 | +452 | +16,058 | **+24,169** |

Δ = 0 %. Strict per-day positive: ✅ (all 3 days ≥ 0). Apply round-5 BT inflation budget (`feedback_bt_inflation_round5_mm` ≈ 10 %): live realisation projection ≈ +2.4 k SS / day. Spike taker is event-driven (~167 events / 3 days) rather than continuous MM, so true inflation profile may differ — record live ratio at first submission.

**Open items** (not in scope of current submission, but on the list):
- Relaxed-gate variant: total positive AND ≤ 1 losing day → would re-include MICROCHIP_TRIANGLE FADE (+3.3k total, only D4 −1.0k on n=2).
- Per-day OXYGEN_SHAKE *MM* (not spike-conditional) — already covered by `550714`; verify it captures spike crossings of pre-existing quotes.

## How to use the live submission folders

The numbered folders under `round5/` (`549159/`, `555509/`, `556852/`,
`558897/`, `560161/`) each contain the trader `.py` actually submitted plus
the platform-returned `.json` and `.log` from the live D5 run. Treat them
as **ground-truth telemetry** for what filled, when, and at what price on
the live day — useful for inspecting per-trade timing and price movements
through the kevin-fu1 visualizer or the dashboard.

**Do NOT use them as input to optimize / select strategies.** The 3-day BT
on `dataset/ROUND_5/prices_round_5_day_{2,3,4}.csv` is the only sample
where re-running with different parameters is cheap; the live D5 file is a
fixed n=1 outcome that gets overfit the moment it drives a parameter
choice. Concrete pitfall: 556502 retuned SNACKPACK / added PIS-fade based
on inspecting 555509's live D5 trades and lost ≈3k vs 555509 on the next
live day. Per `feedback_alpha_not_backtest` and
`feedback_bt_inflation_round5_mm`, structural alpha is the gate; live
results are post-hoc validation.

**Cleaned (2026-04-29)**: only winning per-family submission folders are
retained. `556502/` (v6, retuned SNACKPACK overfit), `556665/` (early SNK
pair experiment, superseded by 556852), `559949/` (PANEL naive MM, live
−3,155 per `feedback_naive_mm_no_trend_defense`) were removed; their
lessons are summarized below and in feedback memories.

## MM submission history (round-5 multi-product MM)

Iterative path from `mr_tune.py` → v6, with live results. All iteration files
were removed during cleanup (2026-04-29); the lessons live here and in
`feedback_bt_inflation_round5_mm`.

| Submission | Strategy | BT (3-day) | Live D5 | Inflation | Notes |
|---|---|---:|---:|---:|---|
| 550714 | v3 (mm_multi_v3 + early OBI grafts) | 147,189 | +1,623 | 1.1% | First multi-product try; OBI overfit, tiny live |
| 555509 | v5 + 3 teammate edits (drop DARK_MATTER, FAMILLE-restricted INV_TAPER) | 241,080 | +21,881 | 9.1% | Adds slp_cp pair, PEBBLES star-XL, SLEEP_POD_COTTON. Largest unlock |
| 556502 | v6 (= 555509 + drop ASTRO_BLACK + SP ENTER_Z 1.6 + SP INV_SKEW 0.5 + PIS-fade) | 244,534 | +18,899 | 7.7% | BT+3,454 → live −2,982. SP retuning + PIS-fade overfit; only ASTRO drop validated |
| (next) | combined_v7_spike (= v5 base − ASTRO_BLACK − DARK_MATTER + spike taker DISHES/IRONING) | 261,138 | (pending) | est. ~9% | Reverts v6 BT-tuning, adds spike layer (+24k BT). Both engines Δ=0 % |

**Lessons baked into v7:**
- Drop ASTRO_BLACK (−470 in 555509, −284 in 550714 — consistent live loser)
- Drop DARK_MATTER (−1,295 in 550714)
- Keep SNACKPACK ENTER_Z=2.0 + INV_SKEW=1.5 (default) — v6's 1.6/0.5 retune cost live
- No PIS-fade — UNIT=2 contributed ≈0 live
- Keep PEBBLES star-XL topology (high-variance: +1,699 D5 in 555509, −588 D5 in 556502 on PEBBLES_S — same code; accept variance, don't redesign on n=2 days)
- Keep INV_TAPER global at 0.9 (rarely fires, defensive)

**Files removed (2026-04-29 cleanup) — preserved here for traceability:**
- `strat_mm_multi.py` / `_v2` / `_v3` / `_v4` / `_v5` / `_v6` (iteration history)
- `mr_tune.py` (pre-v3 base)
- `strat_pairs_basket_*.py` family (multi/pisfade/tune/v2/volaware/snackpack/snackpack_basket/snackpack_maker/coint/maker_multi) — pair experiments, all merged into v6/v7 PAIRS list
- `strat_spike_takers_multi.py`, `strat_spike_fade_robot_dishes.py`, `strat_spike_fade_robot_ironing.py`, `strat_spike_follow_microchip_square.py`, `strat_taker_robot_dishes.py` — folded into combined v7
- `strat_mm_snackpack.py`, `strat_mr_zscore_multi.py`, `strat_translator_obi_taker.py`, `MR_dishes.py` — single-family experiments, superseded
- 2026-04-29 follow-up: `strat_microchip_naive_mm.py` / `_smart_mm.py` (superseded by 560161 hybrid), `strat_panel_naive_mm.py` / `_v2_skew` / `_v3_obigate` / `_v4_trend` / `_mr_zscore` (PANEL family lost live, only `_v5_postrend.py` kept as reference for trend-defended naive MM), `strat_pebbles_only_555mm.py` (superseded by `_556mm`), losing submission dirs `556502/`, `556665/`, `559949/`

---

## Live results — best per family (D4) + improvement potential

Inspected 6 submissions (`549159 / 555509 / 556502 / 556665 / 556852 / 556909` + retired `557541`). All single live day = D4. Stacking rule: combine across submissions only when products are independent (single-product MM or naive maker). Multi-leg pair baskets (PEBBLES star, SNACKPACK basket, slp_cp pair) cannot be sliced.

| Family | Best PnL | Source | Products contributing |
|---|---:|---|---|
| PEBBLES | **+10,428** | 557541 (PEB-only, tight MM + 4-pair star) | all 5 (paired) |
| SLEEP_POD | **+9,710** | 555509 (slp_cp + COT/POL/NYL MM) | COT, POL, NYL |
| SNACKPACK | **+4,546** | 556852 (4-pair basket) | all 5 (paired) |
| TRANSLATOR | **+4,832** | 549159 ⊕ 556909 | MIST +1,991 / BLUE +1,920 / ASTRO +921 |
| ROBOT | **+4,165** | 549159 ⊕ 556909 | IRON +1,508 / MOP +1,457 / VAC +1,200 |
| OXYGEN_SHAKE | **+3,497** | 549159 ⊕ 556909 | CHOC +2,230 / GARLIC +1,267 |
| GALAXY_SOUNDS | **+3,441** | 555509 ⊕ 549159 | BH +2,229 / FLAMES +1,212 |
| UV_VISOR | **+8,640** | 558897 | ORANGE +4,124 / RED +3,822 / MAGENTA +695 (drop YELLOW −214) |
| MICROCHIP | **+1,792** | 556909 ⊕ 549159 | TRI +1,528 / CIRCLE +264 |
| PANEL | 0 | none | not traded |
| **TOTAL** | **+51,051** | | |

### Untouched products (improvement headroom)

22 of 50 products have never been traded across any inspected submission. Highest upside categories ranked by untouched-product count:

| Family | Untouched | Products |
|---|---:|---|
| **PANEL** | **5/5** | 1X2, 1X4, 2X2, 2X4, 4X4 — entire category unexplored |
| UV_VISOR | 1/5 | AMBER (558897 added ORANGE/RED/MAGENTA/YELLOW — YELLOW loses −214, drop) |
| MICROCHIP | 3/5 | OVAL, RECTANGLE, SQUARE |
| GALAXY_SOUNDS | 3/5 | DARK_MATTER, PLANETARY_RINGS, SOLAR_WINDS |
| OXYGEN_SHAKE | 2/5 | MINT, MORNING_BREATH |
| SLEEP_POD | 2/5 | LAMB_WOOL, SUEDE |
| TRANSLATOR | 2/5 | ECLIPSE_CHARCOAL, SPACE_GRAY |
| ROBOT | 1/5 | DISHES (DARK_MATTER -1,295 in 550714, ROBOT_DISHES "problématique" per 555509) |

### Where to spend research effort next

Highest priority — products with naive-MM-friendly profile but never quoted:
1. **PANEL family** — 5 untouched. Even +500 each via naive top-of-book MM could add +2.5k. Run pipeline `family_report.py --family PANEL` first.
2. **MICROCHIP (3 untouched)** — TRIANGLE +1,528 and CIRCLE +264 work. OVAL/SQUARE/RECT may stack similarly.
3. **UV_VISOR_AMBER** — last unexplored UV product. Sister products RED +3,822 and MAGENTA +695 confirm family is naive-MM-friendly. Likely +500-3k upside.

**UV_VISOR — proven recipe (558897, scale up):**
Naive top-of-book MM, `qty = remaining capacity` (not qty=1 like 549159), `spread ≥ 2` gate to avoid crossed quotes. ORANGE went from +2,697 (qty=1, 549159) → +4,124 (qty=cap, 558897) — qty=cap captures more fills on the same book. Apply this scaled recipe to other naive-MM families (PANEL, MIC OVAL/SQUARE/RECT, UV AMBER).

Lower priority — variance-bound:
- SNACKPACK / PEBBLES baskets are at integration optimum on this single live day. Re-tuning paired strategies on n=1 is overfit risk.
- OXYGEN_SHAKE_GARLIC swung from −1,391 to +1,267 across submissions of similar strategy class — variance dominates. Don't over-tune.
- TRANSLATOR_ASTRO_BLACK flipped from −470 to +921 same way. Single-day signal is noise-dominated for these.

**Caveat:** all numbers are single-day (D4). Treat ranking as suggestive, not statistical. The +45,108 ceiling assumes a single submission could combine the disjoint-product blocks — operationally feasible only by merging the source code (e.g. 549159's naive MM target_products list ⊕ 555509's MR_OTHER MM ⊕ 556852's PEB+SNK pair logic).
