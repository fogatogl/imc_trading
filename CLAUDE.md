# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Competition Context

This is an algorithmic trading project for **IMC Prosperity 4** (April 14–30, 2026). The goal is to maximize XIRECs (virtual currency) by submitting a single Python file implementing trading strategies. The submission runs server-side on every market tick.

**Tutorial Round:** March 16 – April 13 (products: EMERALDS, TOMATOES)
**Competitive rounds:** April 14–30 (5 rounds, new products each round)

---

## Running & Testing

There is no `requirements.txt`. Install dependencies manually for local analysis:

```bash
pip install pandas numpy matplotlib plotly
```

**Visualization dashboard** (analyze market data):
```bash
cd TUTORIAL_ROUND_1
python dashboard.py
```

**Backtesting** (requires external tool):
```bash
prosperity4btx TUTORIAL_ROUND_1/trader.py
```

**Jupyter notebooks** (exploratory analysis):
```bash
jupyter notebook TUTORIAL_ROUND_1/visuals.ipynb
```

There are no automated tests.

---

## Submission Constraints (Critical)

The submission is `TUTORIAL_ROUND_1/trader.py`. It must follow these hard constraints:

- **Single `.py` file** uploaded to the IMC website
- **No external libraries**: only Python stdlib + `json`, `math`, `statistics` — no `pandas`, `numpy`, `sklearn`, etc.
- **Mandatory structure** — the engine calls exactly `Trader.run()`:

```python
from datamodel import OrderDepth, TradingState, Order
import json

class Trader:
    def run(self, state: TradingState):
        result = {}       # Dict[product, List[Order]]
        conversions = 0   # int — conversion-based products only
        trader_data = ""  # str — your persistent JSON memory

        return result, conversions, trader_data
```

- **File size limit**: ~50–100 KB
- **Time limit per tick**: tens of milliseconds — keep logic O(n) in order book depth
- **No persistent state** via `self.x` — the class may be re-instantiated between ticks

---

## State Persistence Pattern

`self.*` attributes are unreliable between ticks. Use `traderData` as the only persistent store:

```python
memory = json.loads(state.traderData) if state.traderData else {}
price_history = memory.get("prices", {})  # Dict[str, List[float]]

# ... compute ...

price_history[p] = price_history[p][-50:]  # cap to control JSON size
return result, 0, json.dumps({"prices": price_history})
```

---

## Architecture

```
TUTORIAL_ROUND_1/
├── trader.py          # Submission file — must conform to IMC API
├── dashboard.py       # Visualization: 8-panel matplotlib market analysis
├── visuals.ipynb      # Exploratory Plotly charts
├── prices_round_0_day_-1.csv / _-2.csv   # Historical order book snapshots
├── trades_round_0_day_-1.csv / _-2.csv   # Historical trade executions
├── CLAUDE.md          # Deep strategy guide (read this for trading logic)
├── emmeraudes.txt     # EMERALDS-specific strategy notes (French)
├── trader.txt         # Technical implementation reference (French)
└── information.txt    # Competition rules (French)
```

**Data format:** All CSVs are semicolon-delimited (`;`). Price files have columns: `day`, `timestamp`, `product`, `bid_price_1–3`, `bid_volume_1–3`, `ask_price_1–3`, `ask_volume_1–3`, `mid_price`, `profit_and_loss`.

---

## Key Strategy Concepts

Detailed strategy is in [TUTORIAL_ROUND_1/CLAUDE.md](TUTORIAL_ROUND_1/CLAUDE.md). Summary:

- **EMERALDS**: Stationary fair value = 10,000. Pure market making — take favorable orders crossing 10,000, post maker quotes just inside the spread.
- **TOMATOES**: Drifting product. Use **WallMid** (mid-price of largest bid/ask volumes, not just best bid/ask) as fair value estimate. This is more robust than plain midprice against bot spoofing.
- **Position limits**: EMERALDS = 80, TOMATOES = 80. Always clip orders to stay within limits.
- **WallMid formula**: find the bid price with maximum volume and the ask price with maximum volume, average them.

---

## Known Issues

- [TUTORIAL_ROUND_1/trader.py:9](TUTORIAL_ROUND_1/trader.py#L9): type annotation uses `order` (lowercase) instead of `Order` — this is a syntax bug to fix before submission.
