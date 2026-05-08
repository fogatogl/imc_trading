# IMC Prosperity 4 — Trading Research

A research repository tracking the discovery path through five rounds of the
IMC Prosperity 4 algorithmic trading competition. Each round folder contains
the research notebooks, written analyses, candidate strategies, and the
final submitted trader, so the route from raw data to shipped alpha can be
retraced and reproduced end-to-end.

---

## Final placement

| Leaderboard | Rank | Field | Percentile |
|---|---:|---:|---:|
| Worldwide | **581** | 18,803 | top 3.1% |
| France | **21** | 4,021 | top 0.6% |

---

## Round-by-round results

| Round | Products | Final submission | Official PnL (SeaShells) |
|------:|---|---|---:|
| 1 | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | [`round1/trader_ash6_fix_doublefire.py`](round1/trader_ash6_fix_doublefire.py) (ASH) + [`round1/2800ash_final.py`](round1/2800ash_final.py) (PEPPER) | — |
| 2 | manual challenge only | [`round2/final.py`](round2/final.py) | — |
| 3 | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, 10× `VEV_*` vouchers | [`round3/486411/486411.py`](round3/486411/486411.py) | **+36,116** |
| 4 | same instruments as round 3, plus counterparty IDs and `AETHER_CRYSTAL` exotic | [`round4/544098/544098.py`](round4/544098/544098.py) | **+99,202** |
| 5 | 50 new products (10 categories × 5), position limit 10 each + Ignith news manual | [`580385/580385.py`](580385/580385.py) (algo) + [`round5/manual/FINAL_strategy.md`](round5/manual/FINAL_strategy.md) (manual) | algo **−4,791**, manual **+95,749**, **total +90,958** |

Round-3 PnL breakdown lives in [`CLAUDE.md`](CLAUDE.md#round-3--final-result-closed)
and [`round3/round3_strategy.md`](round3/round3_strategy.md). Round-4
breakdown is in the same `CLAUDE.md` section and [`round4/round4_research.md`](round4/round4_research.md).
Round-5 breakdown and full postmortem are in [`round5/ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md).

---

## What this repo is for

The README at the root of each round folder narrates the path of the round:
the questions asked, the experiments run, the dead ends, and the strategy
that ended up shipped. The goal is that a reader who has never seen the
codebase can:

1. Read the per-round narrative,
2. Open the research notebook(s) referenced from it,
3. Run the same backtester used during the competition,
4. Reproduce the alpha numbers that drove the final submission decisions.

Reports of intermediate findings (ICs, archetype assignments, lead-lag
tables, ML calibration outputs) live under [`round5/reports/`](round5/reports/).
The pipeline that generated them lives under [`round5/ml/`](round5/ml/) and
[`round5/`](round5/) (`research_lib.py`, `family_report.py`,
`archetypes.py`, `permissive/`, etc.).

---

## Round 5 — final result

**Combined: +90,958 SeaShells** (algorithmic **−4,791** + manual **+95,749**). The manual side carried the round; the algorithmic submission was a slight loss vs a +53,681 pre-submission theoretical stack. Full postmortem in [`round5/ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md).

### Manual round — Ignith news portfolio (+95,749)

The manual side used the audit-corrected event-study framework in [`round5/manual/FINAL_strategy.md`](round5/manual/FINAL_strategy.md): translate each Ashflow Alpha article into `(r_est, σ)` anchored to a real-world event analogue, apply the closed-form optimum `x* = r/2` under quadratic fees, hold cash past the optimum because marginal contribution turns negative. The submitted allocation deviated from the audit table on four names where we judged the wider competitor pool would systematically mis-price relative to the news magnitude (round-5 manual scoring is partly relative to the field).

| Product | Direction | % | PnL |
|---|:-:|:-:|---:|
| **Lava Cakes** | SELL | 17% | **+78,801** |
| **Thermalite Core** | BUY | 10% | **+12,160** |
| Pyroflex Cells | SELL | 6% | +8,121 |
| Sulfur Reactor | BUY | 3% | +4,327 |
| Ashes of Phoenix | SELL | 2% | +301 |
| Scoria Paste | — | 0% | 0 |
| Obsidian Cutlery | SELL | 2% | −2,383 |
| Magma Ink | BUY | 6% | −2,264 |
| Volcanic Incense | BUY | 2% | −3,314 |
| **Total** | — | **48%** | **+95,749** |

Lava Cakes alone delivered 82% of total PnL. Audit point estimate was +$41k under skeptic priors with a $1k–$108k range across worlds; realised +$95,749 sits near the aggressive-world estimate (+$107,825). The framework gated the result — even with two directional misses (Volcanic Incense, Magma Ink), quadratic-fee discipline (48% deployed, not 100%) made the upside extraction efficient.

### Algorithmic round — final ensemble composition (live PnL **−4,791**)

The submitted ensemble [`580385/580385.py`](580385/580385.py) is a disjoint
stack of per-family **live D4** winners. Each block was the live-D4 winner
for its family, composed into one trader with shared `traderData` (state
never crosses block boundaries). The pre-submission theoretical stack
summed to **+53,681**; the realised live D5 result was **−4,791**
(Δ −58,472). Full postmortem in
[`round5/ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md).

### Per-family final result (live D5)

| Family | Live D5 | Pre-submission expected | Δ |
|---|---:|---:|---:|
| GALAXY_SOUNDS | +13,801 | +3,441 | **+10,360** |
| SNACKPACK | +12,766 | +4,546 | +8,220 |
| PEBBLES | +8,914 | +10,428 | −1,514 |
| ROBOT | +5,610 | +4,165 | +1,445 |
| PANEL | 0 | +11 | −11 |
| MICROCHIP | −859 | +4,411 | −5,270 |
| OXYGEN_SHAKE | −6,221 | +3,497 | −9,718 |
| UV_VISOR | −8,149 | +8,640 | −16,789 |
| TRANSLATOR | −13,596 | +4,832 | −18,428 |
| SLEEP_POD | −17,057 | +9,710 | **−26,767** |
| **Total** | **−4,791** | **+53,681** | **−58,472** |

The loss was concentrated in 6 products (`PEBBLES_S −30,141`,
`UV_VISOR_RED −10,327`, `SLEEP_POD_POLYESTER −10,045`,
`SLEEP_POD_NYLON −8,929`, `TRANSLATOR_VOID_BLUE −7,855`,
`OXYGEN_SHAKE_CHOCOLATE −7,024` = combined **−74,321**); the remaining
44 products netted **+69,530**.

Only the GALAXY cointegration oracle (Block F) beat its expectation
(4× over). The SNACKPACK 4-pair basket (Block C) also exceeded. PANEL's
trend-filtered MM neutralised cleanly on the directional D5 — the same
construction without the filter would have lost. Every family relying on
naive top-of-book MM with `qty=cap` and no trend defence regressed.

### Ensemble blocks

| Block | Source submission(s) | Products / mechanic |
|---|---|---|
| **A** — naive MM, qty=1, no spread gate | [`round5/549159/`](round5/549159/) | `TRANS_GRAPHITE_MIST`, `TRANS_VOID_BLUE`, `ROBOT_IRONING`, `ROBOT_MOPPING`, `OXYGEN_SHAKE_CHOCOLATE`, `MICROCHIP_CIRCLE` |
| **B** — naive MM, qty=cap, spread ≥ 2 gate | [`round5/558897/`](round5/558897/) + [`round5/560161/`](round5/560161/) | `UV_VISOR_RED/ORANGE/MAGENTA`, `MICROCHIP_OVAL` |
| **C** — smart MM (mean-rev + OBI graft + SNK basket + PEB star + sleep-pod pair + per-product params + inventory taper) | [`round5/555509/`](round5/555509/) + [`556909/`](556909/) + [`round5/556852/`](round5/556852/) | `SNACKPACK ×5`, `PEBBLES ×5`, `SLEEP_POD COTTON/POLYESTER/NYLON`, `OXYGEN_SHAKE_GARLIC` (OBI), `GALAXY_SOUNDS_BLACK_HOLES` (OBI), `MICROCHIP_TRIANGLE`, `ROBOT_VACUUMING`, `TRANSLATOR_ASTRO_BLACK` |
| **E** — spike-fade taker (4σ, hold=20) | [`round5/strats/strat_combined_v7_spike.py`](round5/strats/strat_combined_v7_spike.py) | `ROBOT_DISHES` (FADE side, qty=10) |
| **F** — galaxy cointegration oracle | [`round5/final/566031.py`](round5/final/566031.py) | `GALAXY_SOUNDS_SOLAR_FLAMES`, `GALAXY_SOUNDS_DARK_MATTER` (fair = const + Σ wᵢ·midᵢ on the full GALAXY family; `\|z\|>2` take, else maker quotes) |

Rationale and audit per family is in
[`round5/best_strategies/MANIFEST.md`](round5/best_strategies/MANIFEST.md).
Theoretical disjoint-stack live PnL **+53,681 SeaShells**.

Excluded from the stack (documented loss/no-edge per family in the
manifest): `UV_YELLOW −214`, `ROBOT_LAUNDRY −391`, `OXY_EVENING_BREATH −255`,
`MIC_SQUARE`, `MIC_RECTANGLE −849`, plus the entire `PANEL` family (live
submission underperformed website BT).

---

## Repo map

```
round1/   ASH + PEPPER strategies, analysis notebooks, strategy doc
round2/   Manual round only
round3/   Hydrogel + voucher research, OU-corrected BS pricer, submission 486411
round4/   Same products as r3 with counterparty IDs; HP anchor lift, VEV smile-trim, submission 544098
round5/   The Final Stretch — 50 new products
  ├─ research_lib.py, family_report.py, archetypes.py    pipeline backbone
  ├─ permissive/                                         relaxed re-classifier
  ├─ ml/                                                 block-CV ML pipeline + JSON-artefact codegen
  ├─ reports/                                            per-family stats / IC / archetypes / volatility / ML
  ├─ strats/                                             candidate traders (final = strats/research/strat_ens_v1_snk_coint.py)
  ├─ best_strategies/                                    per-family live D5 winners + MANIFEST.md
  ├─ final/566031.py                                     galaxy cointegration oracle (Block F source)
  ├─ pebbles/557541.py                                   PEBBLES live D5 winner (Block C source)
  ├─ manual/                                             round-5 manual challenge (quadratic-fee allocation)
  └─ <numeric>/                                          per-submission .py + .json telemetry
dataset/                                                round 1-4 prices + trades CSVs (round 5 ignored — local only)
imc_stats/                                              shared statistical helpers (vendored from imc_commun)
```

The two backtester engines used throughout (Python `prosperity4bt` + Rust
`rust_backtester`) live under `imc_trading/` and are gitignored as a
~32 GB local mirror — see CLAUDE.md for invocation.

---

## Reproducing the alpha

The two backtester engines used throughout the competition are independent
implementations of the same exchange. Cross-running every candidate
strategy on both is the sanity check used in this repo against
engine-specific exploitation. Round-3 submission `486411.py` on round-4
data agrees within 0.04 % between the two engines.

**Python backtester** (from repo root, PowerShell):

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0
```

**Rust backtester** (cross-check engine, from repo root):

```bash
imc_trading/prosperity_rust_backtester/target/release/rust_backtester.exe \
    --trader <trader.py> --dataset round4
```

Dataset aliases: `round1`..`round8`, `tutorial`, `latest`. Single day:
`--day 1`. Persist artefacts (`combined.log`, `pnl_by_product.csv`,
`trades.csv`, `metrics.json`) under `runs/<id>/`: add `--persist`.

The full backtester contract (logger requirements, fill model, dataset
layout) is in [`CLAUDE.md`](CLAUDE.md).

### Round-5 alpha pipeline

```bash
# Per-family stats / archetypes / IC / lead-lag / volatility reports
.venv/Scripts/python.exe round5/family_report.py <FAMILY>

# Permissive (less discriminant) re-classifier
.venv/Scripts/python.exe -m round5.permissive.cli

# ML pipeline (block-CV + hold-h-or-flip simulator + G1-G4 gate + JSON codegen)
.venv/Scripts/python.exe -m round5.ml.family_alpha_scan
.venv/Scripts/python.exe -m round5.ml.codegen
```

All outputs land in `round5/reports/<FAMILY>/` and `round5/ml/artifacts/`.

---

## Discoveries log

The single biggest lessons from the competition, with the round in which
they were learned:

- **R3 — anchor + vol armor beats fancy mean-rev.** Hydrogel earlier v9 cross-book mean-rev lost ~10 k live despite a +112 k backtest. Reverting to a stationary anchor `HP_MEAN = 9991` with `vol_scale = min(1, 30 / std50)` shrinking position when realised vol spikes was the unlock.
- **R4 — anchor lift, not anchor change.** The hydrogel mid drifted up between rounds; lifting the anchor (instead of replacing the model) doubled the P&L.
- **R4 — trim the smile, do not fix it.** Skipping deep-ITM (4000/4500) and far-OTM (6000/6500) VEV strikes turned a −9 k pit into a +46 k bucket.
- **R5 — backtest is a gate, not an optimiser.** Round-5 MM backtests inflated ~10× over live. Per-family live D5 ranking, not 3-day BT total, is the only valid selector.
- **R5 — naive top-of-book MM has zero trend defence.** PANEL submission 559949 lost −3,155 live on a smooth down-drift day after BT +54,985 on bouncier days; needs hard inventory cap or trend filter when the family lacks structural alpha.
- **R5 — n=1 D4 winners do not stack.** The submitted ensemble was a disjoint stack of each family's best single-live-D4 outcome. On D5 (another n=1 draw), half the picks regressed — final result **−4,791** vs theoretical **+53,681**. n=1 outcomes are draws, not alpha; require per-day-positive on every available day before promoting.
- **R5 — structural alpha replicates, statistical alpha does not.** GALAXY cointegration oracle returned **+13,801** vs **+3,441** expected (4× over) — fair value from regression of related mids, trade residual on `\|z\|>2`. Every block relying on stationary mean-rev around a fitted constant regressed.
- **R5 — pair β fit on 3 days is fragile on day 4.** The SLEEP_POD `slp_cp` pair (`COTTON ↔ POLYESTER`, β=−0.795 OLS on D2-D4, ent=1.6) lost **−18,973** on POLYESTER+NYLON legs because D5 residual diverged. Cointegration p-value passing in-sample is not the right screen; rank by β stability + intra-day half-life instead.
- **R5 — combined-trader backtest is mandatory.** No combined BT of `580385.py` was run before submission — only per-component validation. Component validation is not ensemble validation; ship-blocking rule for next year is one combined BT pass on both engines.
- **R5 — concentration risk hides inside hedged baskets.** PEBBLES star netted **+8,914** only because `PEBBLES_XL` drew **+41,269** against S/M/L/XS shorts of −34k. Same trader with XL drawing the other direction = ≈−34,000. The basket's "neutrality" was an n=1 directional draw on the anchor leg, not residual capture.
- **R5 manual — calibration framework + quadratic-fee discipline beats budget-filling.** Audit-corrected `r_est` anchored to event-study analogues, `x* = r/2` deployment, 48% of budget intentionally held in cash because marginal contribution turns negative past the optimum. Result: **+95,749** on the manual round vs +$41k point estimate. The original (pre-audit) plan deployed 100% of budget on inflated `r_est`; cross-world stress test showed −$59k under efficient-market priors. Filling the budget is what flawed plans do.
- **R5 manual — concentrate on structurally unambiguous signals.** Lava Cakes (triple-driver recall) was sized up from 12.5% to 17% and returned +78,801 — 82% of the manual round's total PnL. The crowd-fade behavioural override on the ambiguous Volcanic Incense pump pattern (LONG 2% against the audit's SHORT 7.5%) lost −3,314. Behavioural deviations from a calibrated table belong only on names where the underlying signal is structurally clear.

Each of these is also captured in
[`CLAUDE.md`](CLAUDE.md) and the per-round research docs.

---

## License & data

Datasets in `dataset/` are sourced from the IMC Prosperity 4 competition
platform and are kept here for reproducibility. Code authored in this repo
is for personal research and learning purposes; no separate license is
attached.
