# CLAUDE.md — IMC Prosperity 4 Trading Competition Context

> This file provides all necessary context for an AI assistant helping develop trading algorithms
> for the IMC Prosperity 4 competition. Read this before writing or reviewing any code.

---

## 1. Competition Overview

IMC Prosperity 4 is a global algorithmic trading simulation run by IMC Trading, targeting
university students. It runs **April 14 – April 30, 2026**, across 5 competitive rounds plus
a tutorial round (March 16 – April 13). The currency is **XIRECs** (previously "SeaShells").

- **~12,000+ teams** compete worldwide.
- Top teams historically score **200,000+ XIRECs**.
- Each round adds **new tradable products** with new mechanics.
- Two components per round: **algorithmic trading** (code) + **manual trading** (puzzles).
- Only the **algorithmic** component is the focus of this repo.

**Round schedule:**

| Round | Dates | Notes |
|---|---|---|
| Tutorial (Round 0) | March 16 – April 13 | EMERALDS + TOMATOES confirmed |
| Round 1 | April 14–17 | New products introduced |
| Round 2 | April 17–20 | Basket/arbitrage mechanics likely |
| *Intermission* | April 20–24 | — |
| Round 3 | April 24–26 | More complexity |
| Round 4 | April 26–28 | Possibly options/derivatives |
| Round 5 | April 28–30 | Often de-anonymized trades (insider signal) |

---

## 2. Technical Environment & Hard Constraints

### Mandatory code structure

The submission must be a single `.py` file. The engine calls `Trader.run()` on every tick.

```python
from datamodel import OrderDepth, TradingState, Order
import json

class Trader:
    def run(self, state: TradingState):
        result = {}          # Dict[product, List[Order]]
        conversions = 0      # int — for conversion-based products only
        trader_data = ""     # str — your persistent memory (JSON)

        # ... your logic ...

        return result, conversions, trader_data
```

**Three mandatory elements** that must never change:
1. `from datamodel import ...` — IMC's own datamodel import
2. Class named exactly `Trader`
3. Method named exactly `run(self, state: TradingState)`

### The sandbox constraints

- **No external libraries**: no `xgboost`, `sklearn`, `pandas`, `numpy` (use only Python stdlib + `json`, `math`, `statistics`).
- **File size limit**: typically 50–100 KB. Transpiled ML models can blow this.
- **Time limit per tick**: a few tens of milliseconds. Keep logic O(n) where n = order book depth.
- **No state between ticks** unless explicitly passed through `traderData`.

### Memory: the `traderData` pattern

The class may be re-instantiated between ticks. `self.x` attributes are unreliable.
Use `traderData` as your only persistent store:

```python
def run(self, state: TradingState):
    # Load
    memory = json.loads(state.traderData) if state.traderData else {}
    price_history = memory.get("prices", {})   # Dict[str, List[float]]

    # ... compute ...

    # Save (cap history to control JSON size)
    for p in price_history:
        price_history[p] = price_history[p][-50:]   # keep last 50 ticks only

    trader_data_out = json.dumps({"prices": price_history})
    return result, 0, trader_data_out
```

---

## 3. The `TradingState` Object — Full Reference

`state` is the only window into the market. All attributes:

| Attribute | Type | Description |
|---|---|---|
| `order_depths` | `Dict[str, OrderDepth]` | The live order book per product. Core of all decisions. |
| `own_trades` | `Dict[str, List[Trade]]` | Your fills from the *previous* tick. |
| `market_trades` | `Dict[str, List[Trade]]` | Public trades from the *previous* tick (used for VWAP). |
| `position` | `Dict[str, int]` | Your current inventory. Positive = long, negative = short. |
| `traderData` | `str` | Your JSON memory string from last tick's return value. |
| `listings` | `Dict[str, Listing]` | Static product metadata. |
| `timestamp` | `int` | Current tick number (in ms). |
| `observations` | `Observation` | External signals (sunlight, humidity, shipping costs, etc.). |

### Reading the order book

```python
depth = state.order_depths["EMERALDS"]

# Buy side (bids) — sorted descending by price (best bid first)
best_bid = max(depth.buy_orders.keys())
best_bid_vol = depth.buy_orders[best_bid]   # positive int

# Sell side (asks) — sorted ascending by price (best ask first)
best_ask = min(depth.sell_orders.keys())
best_ask_vol = depth.sell_orders[best_ask]  # negative int (IMC convention!)
```

### Placing orders

```python
from datamodel import Order

orders = []
orders.append(Order("EMERALDS", 9998, 10))   # buy 10 at 9998
orders.append(Order("EMERALDS", 10002, -10)) # sell 10 at 10002
result["EMERALDS"] = orders
```

Positive quantity = buy. Negative quantity = sell.
Orders live for **one tick only**. They are not persistent.

---

## 4. Known Products — Prosperity 3 Precedent + Prosperity 4 Tutorial

### Product taxonomy

Products follow a consistent pattern across editions. Each product has a **behaviour archetype**:

| Archetype | Behaviour | Primary Strategy |
|---|---|---|
| **Stationary** | Fixed fair value, oscillates in narrow band | Market making with hardcoded FV |
| **Drifting** | Random walk, no long-run mean | Market making using WallMid as FV |
| **Mean-reverting** | Occasional sharp spikes, reverts quickly | Z-score spike detection, take opposite |
| **Basket** | Synthetic value = weighted sum of components | Statistical arbitrage vs. components |
| **External signal** | FV driven by observable variable (sunlight, etc.) | Regression on observation |
| **Derivative** | Options / vouchers on underlying | Black-Scholes delta hedging |

### Prosperity 4 — Tutorial Round (confirmed)

| Product | Archetype | Known Fair Value | Position Limit | Strategy |
|---|---|---|---|---|
| `EMERALDS` | Stationary | ~10,000 +- oscillation | Unknown | Market making: hardcode FV=10000, quote ±1/±2 |
| `TOMATOES` | Drifting | Moves over time | Unknown | Market making using dynamic FV (WallMid or VWAP) |

**Emeralds** are equivalent to Prosperity 3's Rainforest Resin and Prosperity 2's Amethysts.
The mid-price stays centred at 10,000 with a spread. Pure market making.

**Tomatoes** are equivalent to Prosperity 3's Kelp. They drift but have no meaningful
adverse selection in takers — the optimal approach is the same market making framework
with a dynamic fair value estimate.

### Prosperity 3 — All Rounds (reference for what to expect later)

| Product | Round introduced | Archetype | Notes |
|---|---|---|---|
| `RAINFOREST_RESIN` | Tutorial | Stationary | FV = 10,000 exactly. ~39k shells/round from top teams. |
| `KELP` | Tutorial | Drifting | Slow random walk. Best FV = current WallMid. ~5k/round. |
| `SQUID_INK` | Round 1 | Mean-reverting | Tight spread + random 100-unit spikes. Z-score strategy. |
| `CROISSANTS` | Round 2 | Drifting | Component of baskets. Olivia insider signal in Round 5. |
| `JAMS` | Round 2 | Drifting | Component of baskets. |
| `DJEMBES` | Round 2 | Drifting | Component of baskets. |
| `PICNIC_BASKET1` | Round 2 | Basket | = 6 Croissants + 3 Jams + 1 Djembe. Stat arb vs components. |
| `PICNIC_BASKET2` | Round 2 | Basket | = 4 Croissants + 2 Jams. |
| `VOLCANIC_ROCK` | Round 3 | Underlying | Base asset for options. |
| `VOLCANIC_ROCK_VOUCHER_*` | Round 3 | Derivative | European call options at strikes 9500/9750/10000/10250/10500. Black-Scholes. |
| `MAGNIFICENT_MACARONS` | Round 4 | External signal | FV driven by sunlight index + humidity via `state.observations`. |

---

## 5. Core Strategy: Statistical Market Making

This is the foundation of every product. Master this before adding complexity.

### Step 1 — Compute Fair Value

Choose the method appropriate to the product archetype:

```python
def compute_fair_value(self, product, order_depth, market_trades):
    # Method 1: Hardcoded (Stationary products only)
    if product == "EMERALDS":
        return 10000.0

    # Method 2: WallMid — mid of the largest bid and ask (best for Drifting)
    # IMC bots post large "wall" orders; their mid is the true FV
    if depth.buy_orders and depth.sell_orders:
        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        return (best_bid + best_ask) / 2.0

    # Method 3: VWAP from market_trades (when recent trades available)
    if market_trades:
        total_vol = sum(abs(t.quantity) for t in market_trades)
        if total_vol > 0:
            return sum(t.price * abs(t.quantity) for t in market_trades) / total_vol

    # Fallback: plain mid
    return (best_bid + best_ask) / 2.0
```

**Insight from 2nd place (TimoDiehm):** The "WallMid" — mid-price of the consistently
large bot orders — is a far better fair value estimate than the plain mid. IMC bots
post large limit orders that bracket the true hidden fair value. Their average closely
matches what IMC uses for PnL calculation internally.

### Step 2 — Inventory Skew

Quote symmetrically around FV, but skew based on your current position:

```python
POSITION_LIMIT = 50   # check per product from competition wiki

pos = state.position.get(product, 0)
skew = pos / POSITION_LIMIT          # -1.0 to +1.0

SPREAD = 2                            # half-spread
SKEW_FACTOR = 1                       # how aggressively to skew

bid_price = round(fv - SPREAD - skew * SKEW_FACTOR)
ask_price = round(fv + SPREAD - skew * SKEW_FACTOR)
```

When long (pos > 0): both prices shift down → you become more eager to sell,
less eager to buy. This is the mechanism that keeps inventory near zero.

### Step 3 — Opportunistic Taking

Before posting passive quotes, sweep any obvious mispricings:

```python
orders = []

# Take any asks priced below fair value
for ask_price, ask_vol in sorted(order_depth.sell_orders.items()):
    if ask_price < fv:
        qty = min(-ask_vol, POSITION_LIMIT - pos)  # ask_vol is negative
        if qty > 0:
            orders.append(Order(product, ask_price, qty))
            pos += qty
    else:
        break

# Take any bids priced above fair value
for bid_price, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
    if bid_price > fv:
        qty = min(bid_vol, POSITION_LIMIT + pos)
        if qty > 0:
            orders.append(Order(product, bid_price, -qty))
            pos -= qty
    else:
        break
```

### Step 4 — Passive Quotes

After taking, place passive maker quotes using remaining headroom:

```python
buy_headroom  = POSITION_LIMIT - pos
sell_headroom = POSITION_LIMIT + pos

if buy_headroom > 0:
    orders.append(Order(product, bid_price, buy_headroom))
if sell_headroom > 0:
    orders.append(Order(product, ask_price, -sell_headroom))
```

---

## 6. Mean-Reversion Strategy (for Squid Ink equivalents)

For volatile products with random spikes that revert to a rolling mean:

```python
# In run(), after loading history:
history = price_history.get(product, [])
history.append(current_mid)
price_history[product] = history[-20:]     # 20-tick rolling window

if len(history) >= 10:
    mean = sum(history) / len(history)
    variance = sum((p - mean)**2 for p in history) / len(history)
    std = variance ** 0.5

    z_score = (current_mid - mean) / std if std > 1e-6 else 0.0

    Z_THRESHOLD = 1.5

    if z_score > Z_THRESHOLD:        # price is unusually high → sell
        qty = int((POSITION_LIMIT + pos) * min(abs(z_score) / 3.0, 1.0))
        if qty > 0:
            orders.append(Order(product, best_bid, -qty))

    elif z_score < -Z_THRESHOLD:     # price is unusually low → buy
        qty = int((POSITION_LIMIT - pos) * min(abs(z_score) / 3.0, 1.0))
        if qty > 0:
            orders.append(Order(product, best_ask, qty))
```

**Key calibration insight:** The Z-threshold of 1.5 is a starting point. For Squid Ink
in Prosperity 3, a rolling standard deviation of the *price differences* (not prices)
was a better volatility measure. If rolling std of diffs > 20, enter full-size opposite.

---

## 7. Basket Arbitrage (for Rounds 2+)

When baskets are introduced, trade the spread between synthetic and market value:

```python
# Example: PICNIC_BASKET1 = 6*CROISSANTS + 3*JAMS + 1*DJEMBES
BASKET_COMPOSITION = {
    "PICNIC_BASKET1": {"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1}
}

def compute_synthetic_value(composition, fair_values):
    return sum(w * fair_values[p] for p, w in composition.items())

basket_mid = compute_fair_value("PICNIC_BASKET1", ...)
synthetic   = compute_synthetic_value(BASKET_COMPOSITION["PICNIC_BASKET1"], fvs)

spread = basket_mid - synthetic
spread_history.append(spread)

if len(spread_history) >= 20:
    s_mean = sum(spread_history) / len(spread_history)
    s_std  = (sum((x - s_mean)**2 for x in spread_history) / len(spread_history)) ** 0.5
    z = (spread - s_mean) / s_std if s_std > 1e-6 else 0

    if z > 2.0:    # basket overpriced → sell basket, buy components
        ...
    elif z < -2.0: # basket underpriced → buy basket, sell components
        ...
```

---

## 8. External Signal Strategy (for observations-driven products)

When `state.observations` contains predictive signals, use a pre-calibrated linear model.
**Compute coefficients offline in a Jupyter notebook. Never fit a model at runtime.**

```python
# Coefficients calibrated offline from historical data:
MACARON_COEF = {
    "intercept":  1250.0,
    "sunlight":   -3.5,    # more sun → lower import price
    "humidity":   1.2,
    "shipping":   -0.8,
}

def predict_fair_value(obs):
    return (MACARON_COEF["intercept"]
            + MACARON_COEF["sunlight"]  * obs.sunlight_index
            + MACARON_COEF["humidity"]  * obs.humidity
            + MACARON_COEF["shipping"]  * obs.shipping_cost)
```

Check the `state.observations` object structure via logging in early ticks.
The available fields differ per product and per round.

---

## 9. Insider / Bot Pattern Detection (Round 5+)

In Prosperity 3's final round, trades were de-anonymized. A bot named **"Olivia"**
consistently had directional insight into Squid Ink and Croissants.
Copy-trading Olivia's direction (buy when she buys, sell when she sells) was highly
profitable for those products in Round 5.

```python
for trade in state.market_trades.get(product, []):
    if hasattr(trade, 'buyer') and trade.buyer == "Olivia":
        # Bullish signal → go long
        ...
    if hasattr(trade, 'seller') and trade.seller == "Olivia":
        # Bearish signal → go short
        ...
```

**Note:** This only works after trade de-anonymization is enabled by IMC (typically Round 5).
In earlier rounds, `market_trades` are anonymized and this pattern cannot be detected.

---

## 10. The `traderData` Memory Schema

Standard layout used throughout this project:

```python
MEMORY_SCHEMA = {
    "prices":   {},    # Dict[product, List[float]] — rolling mid-price history
    "spreads":  {},    # Dict[pair_key, List[float]] — basket spread history
    "vwap":     {},    # Dict[product, float] — last VWAP per product
}

# Load
memory = json.loads(state.traderData) if state.traderData else MEMORY_SCHEMA.copy()

# Save (always cap history to prevent memory bloat)
MAX_HISTORY = 50
for product in memory["prices"]:
    memory["prices"][product] = memory["prices"][product][-MAX_HISTORY:]

return result, conversions, json.dumps(memory)
```

---

## 11. Position Limit Guard (mandatory)

**Violating position limits cancels ALL your orders for that product on that tick.**
Always clip before submitting:

```python
def safe_order(product, price, qty, current_pos, limit):
    """Clips order quantity to stay within position limits."""
    if qty > 0:
        max_buy = limit - current_pos
        qty = min(qty, max_buy)
    else:
        max_sell = limit + current_pos
        qty = max(-max_sell, qty)
    return qty

# Usage:
safe_qty = safe_order(product, price, desired_qty, pos, POSITION_LIMIT)
if safe_qty != 0:
    orders.append(Order(product, price, safe_qty))
```

---

## 12. Backtesting Setup

Use **Jmerle's backtester** (the community standard):

```bash
pip install -U prosperity4btx    # Prosperity 4 version
prosperity4btx trader.py 0       # backtest on tutorial round data
prosperity4btx trader.py 1       # backtest on round 1 data
prosperity4btx trader.py 1 --vis # open in visualizer
prosperity4btx trader.py 1 --merge-pnl  # merge PnL across days
```

**Calibration workflow:**
1. Run backtest, capture raw price/trade logs.
2. Analyse in a local notebook: compute optimal spread, Z-threshold, window size.
3. Hardcode the calibrated constants in `Trader`. Never tune at runtime.
4. Backtest score ≈ 35k → live score ≈ 9k (top 10%) is a known ratio from Prosperity 3.
   Don't over-optimise for backtester score specifically.

**What the backtester cannot simulate accurately:**
- Subtle bot fill behaviour for Rainforest Resin / Kelp (validate these on the live website).
- Conversion mechanics for externally-priced products.
- Potential position-limit violations that the website catches differently.

---

## 13. Key Insights from Top Teams (Prosperity 3 Reference)

**From TimoDiehm (2nd place globally, 1,433,876 SeaShells):**

- The WallMid (mid of the large bot orders) is a better fair value anchor than the plain mid.
  IMC uses a hidden floating-point true price; the wall bots' average brackets it.
- Rainforest Resin alone generated **~39,000 SeaShells per round** consistently. Never abandon
  a working stationary-product strategy in favour of complexity.
- Kelp behaves identically to Rainforest Resin once you verify takers have no predictive power.
  The slow random walk is too minor to change the core strategy. ~5,000 SeaShells per round.
- A fallback system is essential: if you detect anomalous bot behavior (e.g., bots are no
  longer posting their normal wall orders), automatically revert to the plain-mid strategy.
- Never optimize purely for website backtester score. Use Jmerle's backtester for calibration,
  the website only for validating specific bot interactions.

**From Alpha Animals (9th globally, 2nd USA):**

- For Kelp, filter out small noisy orders and track only the large consistent market maker's
  mid-price as fair value.
- For Squid Ink: detect spikes using rolling std of price *differences*. If rolling_std > 20,
  enter a full-size position opposite to the recent move.

**From multiple top-10 teams consensus:**

- The top 3 teams in Prosperity 3 consistently stayed ~100k SeaShells ahead of everyone else.
  The gap is explained by exploiting subtle bot patterns (timing, wall order structure) that
  require deep empirical analysis of the order book — not by using ML.
- **Round 5 de-anonymized trades** are the highest-alpha opportunity in the competition.
  Identifying which named bot has insider information and copy-trading their direction can
  dramatically boost PnL in the final round.

---

## 14. What We Do NOT Use

Per the competition constraints and strategic advice in `trader.txt`:

- No `xgboost`, `sklearn`, `lightgbm`, or any ML library (sandbox restriction).
- No deep learning (not enough data; complexity doesn't beat a good market maker).
- No models fitted at runtime (too slow; use offline calibration + hardcoded coefficients).
- No `m2cgen` transpiled models unless the model is extremely small (< 5 KB generated code).
- No strategies that purely chase PnL on the backtester without understanding the mechanism.

---

## 15. File Structure for This Project

```
.
├── CLAUDE.md           ← This file. Read before touching any code.
├── trader.py           ← The submission file. Must contain class Trader with run().
├── analysis/
│   ├── calibrate.ipynb ← Offline notebook: compute spreads, Z-thresholds, regression coefs.
│   └── backtest.sh     ← Convenience script wrapping prosperity4btx.
└── data/               ← Downloaded data capsules from IMC dashboard (CSV files).
```

**The only file uploaded to IMC is `trader.py`.** Everything else is local tooling.

---

## 16. Quick Reference — Strategy Decision Tree

```
For each new product introduced:
│
├─ Is fair value constant / hardcodeable?
│   └─ YES → Stationary strategy (hardcode FV=10000, quote ±1–2, take mispricings)
│
├─ Is fair value drifting but unpredictable?
│   └─ YES → Drifting strategy (WallMid as FV, same MM structure as stationary)
│
├─ Does price spike and revert sharply?
│   └─ YES → Mean-reversion (rolling Z-score, take opposite of spike)
│
├─ Is it composed of other tradable products?
│   └─ YES → Basket arbitrage (synthetic value = weighted sum, trade spread deviation)
│
├─ Does state.observations contain relevant external data?
│   └─ YES → Regression on observation (offline fit, hardcode coefficients)
│
└─ Is it an option/voucher on an underlying?
    └─ YES → Black-Scholes delta hedge (compute IV, hedge delta exposure)
```
