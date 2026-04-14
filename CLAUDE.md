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

**How to run** (from repo root):
```
PYTHONPATH=imc_trading/imc-prosperity-4-backtester \
.venv/Scripts/python.exe -m prosperity4bt <trader.py> 1--2 1--1 1-0 --data dataset --no-vis
```

**Fill model — `worse` mode (default):**
An order is filled against a historical market trade only when the market trade price is *strictly worse* than your quote (strictly below your bid, or strictly above your ask). This is the conservative setting and is the default across both CLI and programmatic use.

**Why backtest PnL overstates live performance:**
- 100% of fills for passive market-making strategies come from the market-trades path, not the resting order book. Every fill assumes you had queue priority at your price level.
- In the real exchange other bots compete for the same queue position. You will lose some fills you were credited in the backtest.
- The fill executes at your *order price*, not the market trade price. This is correct LOB behaviour (your limit is your guarantee), but it compounds the queue-priority assumption.
- There are no transaction fees modelled.

**How to read a result without overconfidence:**
- Treat the day-0 number as an *upper bound*, not a target. Live score will typically be lower.
- Compare strategies by their *relative* ranking across all three days (−2, −1, 0), not by the absolute PnL of any single day.
- A strategy that is consistent across all three days is more trustworthy than one that spikes on a single day.
- Only 3 days of data exist per round. Any parameter tuned specifically to maximise these numbers is likely overfit.
- To calibrate the model: compare the backtest day-0 number to your actual website score for that round. The gap is your personal inflation factor.

**Position limits (Round 1, confirmed from official wiki):**
- `ASH_COATED_OSMIUM`: 80
- `INTARIAN_PEPPER_ROOT`: 80

## ASH_COATED_OSMIUM Strategy (Round 1 — Current Best)

**Reference implementation:** `round1/strat_taker_2664.py`

Do not rewrite from scratch. All future work must improve this strategy, not replace it.

### Architecture

Two non-overlapping layers per tick. The taker fires first; if it fires, the maker is skipped that tick.

```
Tick
 ├─ [TAKER]  fires if: MA window full AND spread < 7 AND |z-score| > 2
 │            → hit best bid/ask for mean-reversion; cap 20 units
 │            → also closes inventory when |z| < 0.5
 └─ [MAKER]  fires otherwise
              → penny-jump + inventory skew + OBI regime sizing
```

### Maker Layer

**Penny-jump baseline:**
- `spread > 2` → quote at `best_bid+1` / `best_ask-1` (inside the spread)
- `spread ≤ 2` → join at `best_bid` / `best_ask` (can't tighten further)

**Inventory skew** (applied after penny-jump):
- `position > 50`  → lower bid −2, lower ask −1 (want to sell, discourage buying)
- `position < −50` → raise bid +1, raise ask +2 (want to buy, discourage selling)

**OBI regime** (applied after skew, controls size and one-sided quote adjustment):

| Condition | Intent | Size cap | Quote adjustment |
|-----------|--------|----------|-----------------|
| imbalance > 0.75, delta > 100 (massive buy wall) | Accumulate long — price will rise | 40 | ask → best_ask+20 (refuse to sell cheap) |
| imbalance < 0.25, delta < −100 (massive sell wall) | Accumulate short — price will fall | 40 | bid → best_bid−20 (refuse to buy expensive) |
| imbalance > 0.70, delta > 40 (strong buy momentum) | Lean long | 25 | ask → best_ask+10 |
| imbalance < 0.30, delta < −40 (strong sell momentum) | Lean short | 25 | bid → best_bid−10 |
| otherwise (normal market) | Balanced MM | 15 | no adjustment |

Position limit: 80. `available_to_buy = min(80 − pos, size_cap)`.

### Taker Layer

- Uses a 20-period rolling MA of mid-price (persisted in `trader_data["ash_prices"]`).
- z-score = `(mid − MA20) / std20`
- `z > +2` → sell at best_bid (price is high, mean-revert down)
- `z < −2` → buy at best_ask (price is low, mean-revert up)
- `|z| < 0.5 and pos ≠ 0` → flatten at best_bid/ask
- Hard cap: 20 units per direction regardless of position limit.
- **Fires only when spread < 7** (wide spread = stale book or uncertain price; skip).

### Known improvement areas

1. **Low-spread maker** (`2 < spread < 7`): penny-jump still applies but the edge per fill is thin. Asymmetric OBI sizing was tested (lean bid/ask toward favored side) — **reverted, −4 k PnL across all 3 days**. In normal OBI the lean signal is too weak to justify reducing size on one side.

2. **Taker edge filter**: `deviation > spread` was tested as a minimum edge check — **reverted, same regression**. The taker's z-score signal is reliable enough without the extra filter; the filter blocks profitable trades.

3. **INTARIAN_PEPPER_ROOT**: no strategy implemented yet.

### Backtest baselines (worse fill mode, 3 days)
| Day | PnL |
|-----|-----|
| 1−2 | 15,608 |
| 1−1 | 17,350 |
| 1−0 | 16,340 |
| **Total** | **49,298** |

---

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.
