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

**How to run** (from repo root, PowerShell):
```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0
```

Or as a one-liner:
```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"; .venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0
```

Omit `--no-vis` so the backtester opens the external visualizer automatically with the log pre-loaded.

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
| 4 | HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_{4000..6500} (10 vouchers) — **same as round 3, now with counterparty IDs** + manual `AETHER_CRYSTAL` exotics | — (research in progress) | [`round4/`](round4/) |

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

## Round 4 — "The More The Merrier" (Current Focus)

Round 3 is closed. New work goes in `round4/`. Spec: [`round4/Round 4 - "The More The Merrier" 1e43d50cdd2383929a6981dced4dbc53.md`](round4/).

**Algorithmic challenge — "Hello, I'm Mark":**
- Same three product families as Round 3: `HYDROGEL_PACK` (limit 200), `VELVETFRUIT_EXTRACT` (limit 200), 10 `VEV_*` vouchers (limit 300 each).
- **New for round 4:** `Trade.buyer` and `Trade.seller` fields are now populated with counterparty IDs (previously always `None`). Both in `state.market_trades` and historical CSV. The edge is: identify which counterparties are toxic / informed / passive and condition behavior on them.
- VEV TTE in round 4 = **4 days** at start (down from 5 in round 3). Adjust `T_rem` initialisation in any options pricer.

**Manual challenge — "Vanilla Just Isn't Exotic Enough":**
- Underlying `AETHER_CRYSTAL` simulated as GBM, zero drift, **σ_annual = 251 %**, 4 steps per trading day, 252 trading days per year.
- Tradable: spot, 2-week and 3-week vanilla calls/puts, plus three exotics:
  - **Chooser** (3-week expiry; at 2-week mark you pick call-or-put, taking whichever is ITM).
  - **Binary put** (fixed payoff if S_T < K, else 0).
  - **Knock-out put** (vanilla put unless S ever trades below the barrier — knocked to 0 if so).
- Score = average PnL over 100 simulations of the underlying. Volume capped per product.

**What carries from round 3:**
- The submitted hydrogel block (`HP_MEAN=9991`, vol-armor `min(1, 30/std50)`, dual-tier dev thresholds 14/22) was the largest contributor at +19,712. Use it as the round-4 baseline before adding counterparty conditioning.
- The OU-corrected BS pricer for VEV (`MR_STRENGTH=1.0`, `EDGE=1.5`, `TAKE_CAP=30`) was net-positive across the smile. VEV_4500 was the one bad strike — investigate before re-deploying as-is.
- VE's z-score taker + tight maker was sub-noise. Worth re-considering whether to trade VE at all in round 4, or only as a hedge against the option book.

**Workflow rules carried over:**
- One strategy file per product family — never mix products in a single research/ablation file (`feedback_separate_products`).
- Backtest is a *gating filter*, not an optimiser. 3-day historical samples can't rank close strategies; prefer structural alpha (`feedback_alpha_not_backtest`).
- No local plotting/comparison scripts. Open the kevin-fu1 visualizer once per variant (`feedback_no_local_compare_files`).
- Keep `round3/` read-only as historical reference.

**Research entrypoint:** to be created at `round4/round4_analysis.ipynb` once round 4 data ships.

---

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.
