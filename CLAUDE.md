# CLAUDE.md

This repository is used for IMC trading research and experiments.

## Scope

- Keep changes small and reviewable.
- Prefer deterministic scripts over ad-hoc notebook edits when logic becomes reusable.
- Do not commit credentials, tokens, or local environment files.

## Python Conventions

- Target Python 3.10+.
- Prefer clear, typed functions for strategy logic.
- Keep strategy code side-effect-light and separate from I/O.
- Use small helper modules instead of very large single-file traders.

## Data and Outputs

- Treat datasets and generated backtest outputs as local artifacts unless explicitly required.
- Avoid committing large generated files (plots, logs, checkpoints, temporary reports).
- Keep reproducible scripts under version control; keep generated outputs ignored.

## Repo Hygiene

- Respect `.gitignore` and avoid force-adding ignored files.
- Keep top-level clutter low; place new work in clearly named subfolders.
- Remove dead experimental files once superseded by documented alternatives.

## Backtesting

**Always run candidate strategies through BOTH engines** (Python `prosperity4bt` + Rust `rust_backtester`) on the round-4 days. They are independent implementations of the same exchange — agreement (< ~1% PnL delta) is a sanity check; large divergence flags engine-specific exploitation rather than real edge. Observed baseline agreement on `round3/486411/486411.py` against round-4 data: Python 360,149 vs Rust 360,281.50 (Δ 0.04%).

**Python backtester** (from repo root, PowerShell):
```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0
```

Or as a one-liner:
```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"; .venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0
```

Omit `--no-vis` so the backtester opens the external visualizer automatically with the log pre-loaded.

**Rust backtester** (cross-check engine, from repo root):
```bash
imc_trading/prosperity_rust_backtester/target/release/rust_backtester.exe --trader <trader.py> --dataset round4
```

Dataset aliases: `round1`..`round8`, `tutorial`, `latest`. Single day: `--day 1`. Persist artifacts (`combined.log`, `pnl_by_product.csv`, `trades.csv`, `metrics.json`) under `runs/<id>/`: add `--persist`. Uses PyO3 to call the Python trader — same `Logger` contract applies.

**Visualizer log format (kevin-fu1 visualizer):**
The kevin-fu1 visualizer (`https://kevin-fu1.github.io/imc-prosperity-4-visualizer/`) requires per-tick `lambdaLog` output embedded in the log JSON. The backtester only emits this when the trader itself prints a compressed-state JSON line to stdout each tick. Traders MUST include the standard `Logger` class and call `logger.flush(state, orders, conversions, trader_data)` at the end of `run()`. Without this, the visualizer renders only the activities CSV (PnL chart) and order-book / depth / trades panels stay empty.

Logger contract:
- Single global `logger = Logger()` instance.
- `logger.flush(...)` is the **last** call before `return result, conversions, trader_data` in `run()`.
- Custom debug output via `logger.print(...)` (NOT `print()`) — the global stdout `print` is reserved for the compressed-state line.
- Truncates `state.traderData`, returned `trader_data`, and accumulated `logger.logs` to fit within `max_log_length = 3750` chars combined.

Reference template: see the docstring/header of `round3/trader_merged_v4.py`. Copy the Logger class verbatim — do not modify it.

Import shim for backtester vs sandbox compatibility:
```python
try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
```

**Fill model — `worse` mode (default):**
An order is filled against a historical market trade only when the market trade price is *strictly worse* than your quote (strictly below your bid, or strictly above your ask).

**How to read a result without overconfidence:**
- Backtest score ≈ live score. Compare strategies by *relative* ranking across all three days, not absolute PnL of any single day.
- A strategy consistent across all three days is more trustworthy than one that spikes on a single day.
- Only 3 days of data exist per round. Any parameter tuned specifically to maximise these numbers is likely overfit.

## Research Workflow

When studying a new idea, **never modify the current best strategy file**.
Instead:
1. Copy the current best into a new file (e.g., `strat_<idea>.py`).
2. Implement the experiment in the new file.
3. Backtest both files and compare PnL across all three days.
4. Only promote to "current best" if the new file wins on total and is consistent across days.
5. **Do not delete the experiment file until the user has viewed the backtester results and explicitly gives permission.** Only then remove it and document the outcome in the relevant round's strategy doc.

## Competition Mechanics

- Exchange runs **deterministic, non-adaptive bots**
- Each team runs independently — no human-vs-human order book interaction
- Backtester is accurate: same fill opportunities as live
- Fill executes at **your order price**, not market trade price
- No transaction fees modelled
- Queue-position-aware quoting is not a current competition feature

---

## Round History

| Round | Products | Submitted strategy | Research doc |
|-------|----------|--------------------|--------------|
| 1 | ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT | `round1/trader_ash6_fix_doublefire.py` (ASH) + `round1/2800ash_final.py` (PEPPER) | [`round1/ROUND1_STRATEGY.md`](round1/ROUND1_STRATEGY.md) |
| 2 | (TBD — research in progress) | — | — |
| 3 | HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_{4000..6500} (10 vouchers) | [`round3/486411/486411.py`](round3/486411/486411.py) — official PnL **36,116** | [`round3/round3_findings.md`](round3/round3_findings.md), [`round3/round3_strategy.md`](round3/round3_strategy.md), [`round3/round3_analysis.ipynb`](round3/round3_analysis.ipynb) |
| 4 | HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_{4000..6500} (10 vouchers) — **same as round 3, now with counterparty IDs** + manual `AETHER_CRYSTAL` exotics | [`round4/544098/544098.py`](round4/544098/544098.py) — official PnL **+99,202** | [`round4/round4_research.md`](round4/round4_research.md), [`round4/round4_options_research.md`](round4/round4_options_research.md), [`round4/round4_ve_vev_research.md`](round4/round4_ve_vev_research.md) |
| 5 | 50 new products in 10 categories × 5 (galaxy sounds, sleep pods, microchips, pebbles, robots, UV-visors, translators, panels, oxygen shakes, snackpacks). **Limit = 10 per product.** Manual = Ignith news portfolio (Ashflow Alpha), quadratic fee `(vol/100)² · budget`, budget 1M | [`580385/580385.py`](580385/580385.py) (algo) + [`round5/manual/FINAL_strategy.md`](round5/manual/FINAL_strategy.md) (manual) — algo **−4,791**, manual **+95,749**, total **+90,958** | [`round5/ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md), [`round5/round5_research.md`](round5/round5_research.md), [`round5/best_strategies/MANIFEST.md`](round5/best_strategies/MANIFEST.md) |

---

## Round 3 — Final Result (closed)

Submitted strategy: [`round3/486411/486411.py`](round3/486411/486411.py). Official platform PnL **+36,116 SeaShells**.

Per-product breakdown (official):

| Product | PnL |
|---------|----:|
| HYDROGEL_PACK | +19,712 |
| VEV_5000 | +13,226 |
| VEV_5300 | +8,055 |
| VEV_5100 | +6,085 |
| VEV_5200 | +1,482 |
| VEV_5400 | -96 |
| VEV_5500 | -696 |
| VEV_4000 | -2,259 |
| VELVETFRUIT_EXTRACT | -2,531 |
| VEV_4500 | -6,864 |
| **Total** | **+36,116** |

**Hydrogel pivot — what worked.** Earlier v9 cross-book mean-rev (`sk=20, K=6`) lost ~10k live. The submitted hydrogel block reverts to a simple mean-rev around fixed anchor `HP_MEAN = 9991` with **volatility armor** (`vol_scale = min(1, 30 / std50)` shrinks position limit when realised vol spikes), shark-taker at `|dev| > 22`, passive maker at `|dev| > 14` quoting `5` ticks beyond mid. No EMA, no regime, no imbalance — pure stationary mean-rev with size-throttle. This was the largest single contributor.

**VEV vouchers.** OU-corrected Black-Scholes pricing: `theo = BS(σ_ATM) + MR_STRENGTH·(δ·E[ΔS] + ν·(σ_eff − σ))`, `MR_STRENGTH = 1.0`, `EDGE = 1.5`, `TAKE_CAP = 30`. Deep-ITM strikes (≤5000) priced via BS; ATM/OTM (>5000) priced as `mid + d_emp · E[ΔS]` with empirical delta. Mostly profitable; VEV_4500 was the one large loser.

**VE underlying.** Z-score taker (z=±1.5, cap 40) plus tight maker around rolling mean. Lost 2.5k — sub-noise; left as a hedge layer.

---

## Round 4 — Final Result (closed)

Submitted strategy: [`round4/544098/544098.py`](round4/544098/544098.py) — concat of `final_hydro` + `final_voucher` + `final_ve` (round-3 hydrogel block + OU-corrected BS pricer trading 5000-5500 only + M67-boosted VE). Official platform PnL **+99,202 SeaShells** (single live day).

Per-product breakdown (official):

| Product | PnL |
|---------|----:|
| HYDROGEL_PACK | +39,970 |
| VEV_5100 | +22,704 |
| VEV_5000 | +13,870 |
| VELVETFRUIT_EXTRACT | +12,760 |
| VEV_5200 | +6,001 |
| VEV_5300 | +2,919 |
| VEV_5400 | +779 |
| VEV_5500 | +197 |
| VEV_4000 / 4500 / 6000 / 6500 | 0 each (not quoted) |
| **Total** | **+99,202** |

**Submission progression** (each entry is one re-run on a different practice day):
- 417667 (day 2): +16,410
- 515364 (day 3): −23,531 — gradinv VEV pinned long, VE drifted −42 ticks
- 516536 (day 3): +19,881 — post-fix variant
- 544098 (day 4, final live): +99,202

**What worked vs round 3:**
- **HP +39,970** (vs r3 +19,712, +103%): trending-aware anchor lifted hydrogel.
- **VE +12,760** (vs r3 −2,531): M67 boost flipped VE from drag to alpha.
- **VEV +46,470** (vs r3 +18,933): skipping deep-ITM (4000/4500) and far-OTM (6000/6500) avoided r3's −9k VEV_4000+VEV_4500 pit.
- No catastrophic strike. Tightening the smile beat trying to fix it.

---

## Round 5 — Final Result (closed)

**Combined: +90,958 SeaShells** (algorithmic **−4,791** + manual **+95,749**). Manual side carried the round; algo was a slight loss vs theoretical stack. Full breakdown and lessons in [`round5/ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md).

### Algorithmic — −4,791

Submitted strategy: [`580385/580385.py`](580385/580385.py) — disjoint stack of per-family live-D4 winners (Block A naive MM ⊕ Block B naive MM with spread gate ⊕ Block C smart MM/pair/basket ⊕ Block E spike-fade taker ⊕ Block F galaxy cointegration oracle). Official platform PnL **−4,791 SeaShells** (single live day = D5). Pre-submission theoretical stack (per [`round5/best_strategies/MANIFEST.md`](round5/best_strategies/MANIFEST.md)): **+53,681**. Realised miss: **−58,472**.

### Manual — +95,749

Submitted allocation: see [`round5/manual/FINAL_strategy.md`](round5/manual/FINAL_strategy.md) (audit-corrected event-study framework). 48% of budget deployed; quadratic-fee discipline kept 52% in cash because marginal contribution turns negative past `x* = r/2`.

| Product | Direction | % | PnL |
|---|:-:|:-:|---:|
| Lava Cakes | SELL | 17% | **+78,801** |
| Thermalite Core | BUY | 10% | +12,160 |
| Pyroflex Cells | SELL | 6% | +8,121 |
| Sulfur Reactor | BUY | 3% | +4,327 |
| Ashes of Phoenix | SELL | 2% | +301 |
| Scoria Paste | — | 0% | 0 |
| Obsidian Cutlery | SELL | 2% | −2,383 |
| Magma Ink | BUY | 6% | −2,264 |
| Volcanic Incense | BUY | 2% | −3,314 |
| **Total** | — | **48%** | **+95,749** |

Lava Cakes alone drove **82%** of manual PnL. Audit point estimate +$41k under skeptic priors with $1k–$108k cross-world range; realised +$95,749 sits near the aggressive-world estimate (+$107,825). Behavioural overrides vs the audit table on Lava Cakes (sized up from 12.5% to 17% — correct), Volcanic Incense (flipped LONG vs audit's SHORT — wrong, lost −3,314), Ashes (sized down — flat), Obsidian (sized down — flat). Lesson: behavioural deviations from a calibrated table belong only on names where the underlying signal is structurally clear.

Per-family breakdown (official):

| Family | Live D5 | Expected | Δ |
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

**Where the loss came from:** 6 products (PEBBLES_S −30,141, UV_RED −10,327, SLP_POLY −10,045, SLP_NYLON −8,929, TRANS_BLUE −7,855, OXY_CHOC −7,024) lost a combined **−74,321**. The remaining 44 products netted +69,530.

**What worked:**
- **GLX cointegration oracle** (+13,801 vs +3,441 expected, 4× over) — fair value from regression of related galaxy mids; trade residual on `|z|>2`. Only family that beat its expectation.
- **SNACKPACK 4-pair basket** (+12,766 vs +4,546) — disjoint pair legs with entry threshold 2.0; survived regime change.
- **PANEL trend-filtered MM** (0, neutralised) — ema30 vs ema200 gating prevented the directional-drift losses that killed naive MM elsewhere.

**What broke:**
- **Naive `qty=cap` MM with no trend defense** lost on D5 directional drift (UV_RED, TRANS_VOID_BLUE, TRANS_GRAPHITE_MIST, OXY_CHOC, MIC_CIRCLE). Memory `feedback_naive_mm_no_trend_defense` flagged this exact mode after PANEL 559949; fix was applied to PANEL only.
- **Pair regression β unstable across days** — SLP slp_cp pair (β=−0.795 OLS on D2-D4) lost −19k on POL+NYL legs because D5 residual went the wrong way. Memory `feedback_pairs_screen` warned to rank by β stability, not coint p-value.
- **Theoretical stack from n=1 winners with no combined backtest** — manifest summed each family's best single-live-D4 PnL, never ran the combined trader through Python or Rust BT before shipping. No opportunity to apply BT-decay heuristic.
- **Concentration risk inside "neutral" PEB star** — basket netted +8,914 only because PEBBLES_XL drew +41,269 against S/M/L/XS shorts of −34k. Same trader with XL drawing the other way = ~−34k. n=1 directional draw on the anchor leg, not clean residual capture.

**Cross-family lessons (full version in [`ROUND5_POSTMORTEM.md`](round5/ROUND5_POSTMORTEM.md)):**
1. Stop stacking n=1 outcomes. Require per-day-positive on every available day before promotion; ship 0 if no block clears that bar.
2. Structural alpha (cointegration, baskets, fair-value oracles) replicates; statistical alpha (stationary mean-rev around a fitted constant) does not.
3. Hard inventory cap (`|pos| ≤ position_limit / 2`) on every naive MM block — cheapest survival mechanic, would have saved 30-50k on this run.
4. Single-trader combined backtest is mandatory before submission. Validating each component file individually is not sufficient.
5. Final-round combined submission gets a memory-checklist review against every `feedback_*` entry collected during the round, treating the ensemble as a new artifact.

---

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.
