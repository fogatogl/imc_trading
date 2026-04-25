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
| 3 | HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_{4000..6500} (10 vouchers) | — (research in progress) | [`round3/round3_analysis.ipynb`](round3/round3_analysis.ipynb) |

---

## Round 3 Strategy (Current) — "Gloves Off"

**Products:**
- `HYDROGEL_PACK` — delta-1, position limit **200**
- `VELVETFRUIT_EXTRACT` (VE) — delta-1 underlying, position limit **200**
- `VELVETFRUIT_EXTRACT_VOUCHER` (VEV) — 10 European call options on VE, position limit **300 each**
  - Strikes: `VEV_4000`, `VEV_4500`, `VEV_5000`, `VEV_5100`, `VEV_5200`, `VEV_5300`, `VEV_5400`, `VEV_5500`, `VEV_6000`, `VEV_6500`
  - 7-day expiry starting Round 1. Round 3 start TTE = **5 days** (live).
  - Historical data TTE mapping: day 0 → 8d, day 1 → 7d, day 2 → 6d.

**Data:** `dataset/ROUND_3/prices_round_3_day_{0,1,2}.csv`, `trades_round_3_day_{0,1,2}.csv`.

**Reference prior-year strategy:** [`round3_old_strategy.md`](round3_old_strategy.md) — IV scalping via vol-smile fit + detrended IV deviations, Black-Scholes price deviation signals, underlying mean reversion (EMA) as hedge.

**Research entrypoint:** [`round3/round3_analysis.ipynb`](round3/round3_analysis.ipynb) — replicates last-year plots (vol smile, IV deviations, BS price deviations, underlying autocorrelation) on this year's VE/VEV data.

**Manual trade:** Ornamental Bio-Pods. Reserve prices uniform on `[670, 920]` in steps of 5, sell-out at 920. Two bids. Second-bid penalty `((920 - avg_b2) / (920 - b2))^3` when `b2 < avg_b2`. See `round3/manual_bidding.md` (to be written).

---

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.
