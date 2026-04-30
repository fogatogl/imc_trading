# Round 5 — The Final Stretch

**Active live day:** 2026-04-30
**Products:** 50 brand-new instruments in 10 categories × 5 each:
`GALAXY_SOUNDS_*`, `SLEEP_POD_*`, `MICROCHIP_*`, `PEBBLES_*`, `ROBOT_*`,
`UV_VISOR_*`, `TRANSLATOR_*`, `PANEL_*`, `OXYGEN_SHAKE_*`, `SNACKPACK_*`.
**Position limit:** 10 per product.
**Hard reset:** none of rounds 1-4 carries over.
**Platform doc:** [`Round 5 - "The Final Stretch" ...md`](Round%205%20-%20%E2%80%9CThe%20Final%20Stretch%E2%80%9D%20eba3d50cdd238364a8ea01415d9a1afb.md)

## Final submission

[`strats/research/strat_ens_v1_snk_coint.py`](strats/research/strat_ens_v1_snk_coint.py)
— a disjoint-block ensemble that ships the live D5 winner of each family
in one trader. Block composition:

| Block | Source | Products / mechanic |
|---|---|---|
| **A** — naive MM, qty=1, no spread gate | [`549159/`](549159/) | TRANS_GRAPHITE_MIST, TRANS_VOID_BLUE, ROBOT_IRONING, ROBOT_MOPPING, OXYGEN_SHAKE_CHOCOLATE, MICROCHIP_CIRCLE |
| **B** — naive MM, qty=cap, spread ≥ 2 gate | [`558897/`](558897/) + [`560161/`](560161/) | UV_VISOR_RED/ORANGE/MAGENTA, MICROCHIP_OVAL |
| **C** — smart MM (mean-rev + OBI graft + SNK basket + PEB star + sleep-pod pair + per-product params + inventory taper) | [`555509/`](555509/) + [`../556909/`](../556909/) + [`556852/`](556852/) | SNACKPACK ×5, PEBBLES ×5, SLEEP_POD COTTON/POLYESTER/NYLON, OXYGEN_SHAKE_GARLIC (OBI), GALAXY_SOUNDS_BLACK_HOLES (OBI), MICROCHIP_TRIANGLE, ROBOT_VACUUMING, TRANSLATOR_ASTRO_BLACK |
| **E** — spike-fade taker (4σ, hold=20) | [`strats/strat_combined_v7_spike.py`](strats/strat_combined_v7_spike.py) | ROBOT_DISHES (FADE side, qty=10) |
| **F** — galaxy cointegration oracle | [`final/566031.py`](final/566031.py) | GALAXY_SOUNDS_SOLAR_FLAMES, GALAXY_SOUNDS_DARK_MATTER (fair = const + Σ wᵢ·midᵢ; \|z\|>2 take, else maker quotes inside fair±dyn) |

Per-family attribution and audit: [`best_strategies/MANIFEST.md`](best_strategies/MANIFEST.md).
Theoretical disjoint-stack live total: **+53,681 SeaShells**.

Excluded from the stack (loss/no-edge per family in the manifest):
`UV_YELLOW −214`, `ROBOT_LAUNDRY −391`, `OXY_EVENING_BREATH −255`,
`MIC_SQUARE`, `MIC_RECTANGLE −849`, and the entire `PANEL` family (live
naive MM lost on smooth down-drift days).

## Discovery pipeline

The journey from raw data to the final ensemble runs through three stages,
each with its own scripts and per-family CSV outputs.

### 1. Per-family statistics + archetype routing
- [`research_lib.py`](research_lib.py) — loaders, microstructure, statistical battery, alpha-signal IC scorecard, lead-lag, cointegration, tradeable-ideas synthesizer
- [`volatility.py`](volatility.py) — realized-vol stats, vol-of-vol, vol-conditioned signal IC, sizing recommendations
- [`archetypes.py`](archetypes.py) — priority-ordered routing into `MR_TAKER`, `MOMENTUM`, `RANDOM_WALK`, `NO_EDGE` + orthogonal `PAIR_ANCHOR` / `OBI_TAKER` flags
- [`significance.py`](significance.py) — HAC (Newey-West) t-stats + Bartlett ACF + BH-FDR control across IC cells
- [`data_quality.py`](data_quality.py) — NaN / crossed / locked / stale-run gates
- [`calibration.py`](calibration.py) — threshold sanity check against empirical distributions
- [`family_report.py`](family_report.py) — CLI that drives all the above per family
- [`family_template.ipynb`](family_template.ipynb) — interactive notebook driver

Outputs land in [`reports/<FAMILY>/`](reports/) (`stats_per_product.csv`,
`microstructure.csv`, `signals_ic.csv`, `corr_mid.csv`, `corr_returns.csv`,
`lead_lag.csv`, `cointegration.csv`, `tradeable_ideas.md`, `volatility.csv`,
`vol_regime*.csv`).

### 2. Permissive re-classifier
The legacy classifier routes 43/50 products to `NO_EDGE`. Permissive
([`permissive/`](permissive/)) reads the same per-family CSVs and emits a
flag-based schema (`MR_FLAG`, `MOM_FLAG`, `OBI_FLAG`, `PAIR_FLAG`,
`SPIKE_FLAG`) in [`reports_permissive/`](reports_permissive/). Lets a
product carry several flags simultaneously rather than one primary
archetype.

### 3. ML pipeline (block-CV + JSON-artifact codegen)
[`ml/`](ml/) holds:
- `ml_features.py` — per-product feature matrix
- `ml_models.py` — block-CV (15 folds) ridge / logistic / gradient-boosted
- `pnl_sim.py` — hold-h-or-flip simulator with G1-G4 gate
- `simple_signals_gate.py` — per-day-positive baselines (4 of these passed: GLX, MIC, PANEL, UV)
- `family_alpha_scan.py` — per-family scan over signals × horizons
- `codegen.py` — converts passing models to JSON artefacts a Trader can load
- `tests/` — equality tests between live trading code and offline simulator

Outcome: **0 / 10 ML PASS** under the strict G1-G4 gate, confirming the
audit-null. The 4 simple-signal baselines that did pass per-day-positive
fed the naive-MM and spike-fade blocks of the final ensemble.

### Cross-family research
- [`leadlag_basket_ofi.py`](leadlag_basket_ofi.py), [`leadlag_products.py`](leadlag_products.py)
- [`cross_analysis.py`](cross_analysis.py), [`cross_family.py`](cross_family.py)
- [`spike_anatomy.py`](spike_anatomy.py), [`spike_strategy_sim.py`](spike_strategy_sim.py), [`spike_per_day_check.py`](spike_per_day_check.py), [`vol_spikes.py`](vol_spikes.py)
- [`mm_strategies_research.md`](mm_strategies_research.md) — MM technique catalogue (microprice, OFI, AS, toxicity guards, queue position, Prosperity-3 winner patterns) used as the menu for Block C smart MM
- [`research_microchip.md`](research_microchip.md), [`family_improvement_ranking.md`](family_improvement_ranking.md), [`analysis_brief.md`](analysis_brief.md), [`PIPELINE_REPORT.md`](PIPELINE_REPORT.md)
- [`round5_research.md`](round5_research.md) — top-level research log

### Manual challenge
[`manual/`](manual/) — Ignith news-portfolio allocation under the
quadratic fee `fee = (volume/100)² · budget`, budget 1,000,000 SeaShells.
[`manual/FINAL_strategy.md`](manual/FINAL_strategy.md) walks the
allocation calibration and robustness analysis.

## Live submissions (telemetry only)

Per `feedback_live_submission_telemetry_only`: numbered folders here are
ground-truth D5 logs for visualizer inspection. Do **not** iterate
parameters off them.

| Folder | Role in final ensemble |
|---|---|
| [`549159/`](549159/) | Block A source + parts of Block C |
| [`555509/`](555509/) | Block C — sleep-pod pair + GLX_BLACK_HOLES |
| [`556852/`](556852/) | Block C — SNACKPACK basket + PEBBLES star (tight params 5/2.0/1.0/2.0) |
| [`558897/`](558897/) | Block B — UV_VISOR (drop YELLOW) |
| [`560161/`](560161/) | Block B — MICROCHIP_OVAL |
| [`560470/`](560470/) | First PANEL break-even (+11) |
| [`../556909/`](../556909/) | Block C — TRANS_ASTRO, ROBOT_VAC, OXY_GARLIC, MIC_TRIANGLE |
| [`pebbles/557541/`](pebbles/) | PEBBLES live winner reference (Block C source) |
| [`final/566031`](final/) | Galaxy cointegration oracle (Block F source) |
| [`577195/`](577195/), [`579118/`](579118/) | later iteration variants |

## Reproducibility

```powershell
# Python backtester on round-5 days
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt \
    round5/strats/research/strat_ens_v1_snk_coint.py 5-2 5-3 5-4

# Full per-family pipeline + ML scan (writes round5/reports/, round5/ml/artifacts/)
.venv/Scripts/python.exe round5/family_report.py --family ALL
.venv/Scripts/python.exe -m round5.permissive.cli
.venv/Scripts/python.exe -m round5.ml.family_alpha_scan
.venv/Scripts/python.exe -m round5.ml.codegen
```

Round-5 dataset CSVs (`prices_round_5_day_{2,3,4}.csv` +
`trades_round_5_day_{2,3,4}.csv`) live under `dataset/ROUND_5/` and are
gitignored locally — sourced from the IMC platform.

## Key feedback rules from this round

These were forged by live submissions and are kept in user-memory; they
also shape the design of the final ensemble.

- `feedback_per_day_positive_selection` — pick products by per-day positive PnL on every day individually, never by 3-day total.
- `feedback_bt_inflation_round5_mm` — round-5 MM backtests inflated ~10× over live; treat BT as a gate, not an optimiser.
- `feedback_pebbles_tight_mm_live` — tight MM (5/2.0/2.0) beat loose MM (10/1.5/2.5) live by +2 k despite losing on BT.
- `feedback_naive_mm_no_trend_defense` — naive MM has no trend defence; fails on smooth directional days. PANEL 559949 lost −3,155 live vs BT +54,985.
- `feedback_post_spike_passive_direction` — a fade-after-spike implemented as a passive limit cannot fill via reversion; use a taker.
- `feedback_simple_first_mm` — build MM simple-first, one rung at a time. Static anchor → mid → skew → take-make → wmid → OFI → toxicity. One technique per iteration, validate live before next.
