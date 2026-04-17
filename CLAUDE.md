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

---

## Round 2 Strategy (Current)

*(To be filled in as research progresses.)*

---

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.
