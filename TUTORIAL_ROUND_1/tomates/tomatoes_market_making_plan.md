# TOMATOES Market Making Strategy — IMC Prosperity 4

## 1. Context & Objective

Implement a rigorous market making strategy for the `TOMATOES` product in IMC Prosperity 4.
The strategy draws from Xiong, Yamada & Terano (2014) and is adapted to the Prosperity
environment using `datamodel.py` types.

**Goal:** maximize daily PnL (spread capture) while managing inventory risk and avoiding
adverse selection from directional moves.

---

## 2. Prosperity 4 Data Types Reference

```python
from datamodel import TradingState, OrderDepth, Order, Trade

# TradingState fields used:
# state.timestamp                     : int — current time step
# state.order_depths["TOMATOES"]      : OrderDepth
# state.position.get("TOMATOES", 0)   : int — net position
# state.own_trades["TOMATOES"]        : List[Trade] — our fills last tick
# state.market_trades["TOMATOES"]     : List[Trade] — market fills last tick
# state.traderData                    : str — serialized state from prev tick

# OrderDepth fields:
# depth.buy_orders  : Dict[int, int]  — {price: volume}, volume > 0
# depth.sell_orders : Dict[int, int]  — {price: volume}, volume < 0

# Order constructor:
# Order(symbol: str, price: int, quantity: int)
# quantity > 0 = BUY limit order
# quantity < 0 = SELL limit order
```

**Position limit:** assumed `POSITION_LIMIT = 20` (verify in official rules each round).

**Output format:**
```python
def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
    orders: list[Order] = []
    # ...
    return {"TOMATOES": orders}, 0, trader_data_str
```

---

## 3. Statistical Observations on TOMATOES (to be filled from your analysis)

> Replace the placeholders below with your empirically measured values.

| Parameter | Value | Notes |
|---|---|---|
| Typical spread (ticks) | `ts_obs` | Observed median spread |
| Tick size `ts` | 1 | Integer prices |
| Mid-price mean reversion speed | — | Half-life in ticks |
| Volatility regime threshold | — | σ above which to widen |
| Order imbalance threshold λ₁ | 0.5 | (qb − qs) / (qb + qs) |
| Imbalance skew increment λ₂ | 1 × ts | Adjust quote offset |
| Autocorrelation of returns | — | Lag-1 ACF |
| Typical best bid/ask depth | — | Volume at BBO |

---

## 4. Strategy Architecture

### 4.1 Base Price Selection

Per the paper, **latest trade price** (`Pt`) as base outperforms mid-quote.

```
Pt  = last executed trade price from state.market_trades or state.own_trades
    fallback: mid-quote = (best_bid + best_ask) / 2
```

Implementation:
```python
def get_base_price(state: TradingState, depth: OrderDepth) -> float:
    trades = state.market_trades.get("TOMATOES", [])
    if trades:
        return trades[-1].price
    # fallback to mid-quote
    best_bid = max(depth.buy_orders)
    best_ask = min(depth.sell_orders)
    return (best_bid + best_ask) / 2
```

### 4.2 Quote Spread Strategies (from Table 2 & 3)

All strategies produce an `(ask_price, bid_price)` pair.

| Strategy | Ask | Bid | When to use |
|---|---|---|---|
| `ask/bid` | `Pa_t` | `Pb_t` | Baseline (tight spread) |
| `last` | `Pt + ts` | `Pt − ts` | Default active strategy |
| `last-` | `Pt + 2·ts` | `Pt − 2·ts` | Conservative / wide |
| `last+v` | `Pt + (Δ+1)·ts` | `Pt − (Δ+1)·ts` | High volatility |
| `last+im` | see §4.4 | see §4.4 | Imbalance detected |
| `last+im+v` | combined | combined | Imbalance + high vol |

Where `Δ = |Pt − Pt-1|` (absolute price change last tick, in ticks).

### 4.3 Volatility Filter (`+v` component)

```python
def is_high_volatility(price_history: list[float], window: int = 20,
                       threshold: float = VOL_THRESHOLD) -> bool:
    if len(price_history) < window:
        return False
    recent = price_history[-window:]
    returns = [abs(recent[i] - recent[i-1]) for i in range(1, len(recent))]
    return (sum(returns) / len(returns)) > threshold
```

When `high_vol=True`, widen spread by `|Pt − Pt-1| + 1` ticks each side.

### 4.4 Order Imbalance Filter (`+im` component)

```python
def compute_imbalance(depth: OrderDepth) -> float:
    qb = sum(depth.buy_orders.values())   # positive volumes
    qs = -sum(depth.sell_orders.values()) # make positive
    total = qb + qs
    if total == 0:
        return 0.0
    return (qb - qs) / total  # in [-1, +1]
```

Quote adjustment (λ₁ = 0.5, λ₂ = ts = 1):

```
imbalance > +0.5  → buyers dominate → price likely UP
    ask = Pt + 2·ts   (don't sell cheap)
    bid = Pt          (buy aggressively)

imbalance < -0.5  → sellers dominate → price likely DOWN
    ask = Pt          (sell aggressively)
    bid = Pt − 2·ts   (don't buy expensive)

else (balanced):
    ask = Pt + ts
    bid = Pt − ts
```

---

## 5. Inventory Risk Management

### 5.1 Position Skew

When inventory `pos` drifts from 0, skew quotes to push it back:

```python
POSITION_LIMIT = 80
SKEW_FACTOR = 0.5  # ticks per unit of position, tune via backtest

def apply_inventory_skew(ask: float, bid: float, pos: int,
                          limit: int = POSITION_LIMIT,
                          skew: float = SKEW_FACTOR) -> tuple[float, float]:
    skew_ticks = round(skew * pos / limit)
    return ask - skew_ticks, bid - skew_ticks
```

When `pos > 0` (long): lower both quotes to attract sells.
When `pos < 0` (short): raise both quotes to attract buys.

### 5.2 Hard Stop — Quote Suppression

Do not post orders that would push position past limit:

```python
def clamp_volume(side_qty: int, pos: int, limit: int) -> int:
    if side_qty > 0:  # BUY
        return min(side_qty, limit - pos)
    else:             # SELL
        return max(side_qty, -limit - pos)
```

### 5.3 Emergency Liquidation

If `|pos| > LIQUIDATION_THRESHOLD` (e.g., 15), submit a market-crossing order
to reduce position, sacrificing spread:

```python
LIQUIDATION_THRESHOLD = 15

def liquidation_orders(depth: OrderDepth, pos: int) -> list[Order]:
    orders = []
    if pos > LIQUIDATION_THRESHOLD:
        # Hit best bid to reduce long
        best_bid = max(depth.buy_orders)
        orders.append(Order("TOMATOES", best_bid, -min(pos, 5)))
    elif pos < -LIQUIDATION_THRESHOLD:
        # Lift best ask to reduce short
        best_ask = min(depth.sell_orders)
        orders.append(Order("TOMATOES", best_ask, min(-pos, 5)))
    return orders
```

---

## 6. State Persistence via `traderData`

Persist rolling price history and volatility state across ticks using JSON:

```python
import json

DEFAULT_STATE = {"price_history": [], "last_price": None}

def load_state(trader_data: str) -> dict:
    if not trader_data:
        return DEFAULT_STATE.copy()
    try:
        return json.loads(trader_data)
    except Exception:
        return DEFAULT_STATE.copy()

def save_state(state_dict: dict) -> str:
    # Keep last 50 prices only to stay within traderData size limits
    state_dict["price_history"] = state_dict["price_history"][-50:]
    return json.dumps(state_dict)
```

---

## 7. Full `run()` Skeleton

```python
from datamodel import TradingState, OrderDepth, Order
import json, math

PRODUCT        = "TOMATOES"
POSITION_LIMIT = 20
TS             = 1          # tick size
VOL_THRESHOLD  = 2.0        # avg |return| threshold to trigger +v
LAMBDA1        = 0.5        # imbalance threshold
SKEW_FACTOR    = 0.5
LIQUIDATION_THRESHOLD = 15

class Trader:
    def run(self, state: TradingState):
        s = load_state(state.traderData)
        depth: OrderDepth = state.order_depths.get(PRODUCT, None)
        pos: int = state.position.get(PRODUCT, 0)
        orders: list[Order] = []

        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return {PRODUCT: orders}, 0, save_state(s)

        # --- 1. Base price ---
        Pt = get_base_price(state, depth)
        if s["last_price"] is not None:
            delta = abs(Pt - s["last_price"])
        else:
            delta = 0
        s["price_history"].append(Pt)
        s["last_price"] = Pt

        # --- 2. Select strategy components ---
        high_vol  = is_high_volatility(s["price_history"], threshold=VOL_THRESHOLD)
        imbalance = compute_imbalance(depth)

        # Compute raw ask/bid (last+im+v)
        if imbalance > LAMBDA1:
            ask = Pt + (delta + 2) * TS if high_vol else Pt + 2 * TS
            bid = Pt - delta * TS       if high_vol else Pt
        elif imbalance < -LAMBDA1:
            ask = Pt + delta * TS       if high_vol else Pt
            bid = Pt - (delta + 2) * TS if high_vol else Pt - 2 * TS
        else:
            ask = Pt + (delta + 1) * TS if high_vol else Pt + TS
            bid = Pt - (delta + 1) * TS if high_vol else Pt - TS

        # --- 3. Inventory skew ---
        ask, bid = apply_inventory_skew(ask, bid, pos)
        ask_price = math.ceil(ask)
        bid_price = math.floor(bid)

        # --- 4. Emergency liquidation (overrides quoting) ---
        liq = liquidation_orders(depth, pos)
        if liq:
            return {PRODUCT: liq}, 0, save_state(s)

        # --- 5. Submit quote orders ---
        ask_vol = clamp_volume(-3, pos, POSITION_LIMIT)  # sell 3
        bid_vol = clamp_volume(+3, pos, POSITION_LIMIT)  # buy  3
        if ask_vol < 0:
            orders.append(Order(PRODUCT, ask_price, ask_vol))
        if bid_vol > 0:
            orders.append(Order(PRODUCT, bid_price, bid_vol))

        return {PRODUCT: orders}, 0, save_state(s)
```

---

## 8. Backtesting & Tuning Plan

### 8.1 Setup (kevin-fu1 backtester)

```bash
git clone https://github.com/kevin-fu1/imc-prosperity-4-backtester.git
cd imc-prosperity-4-backtester
pip install -e .
# Place trader.py in project root
python backtester.py --algo trader.py --round 0
```

### 8.2 Parameter Grid Search

Tune the following via systematic grid search on historical data:

| Parameter | Search Range | Metric |
|---|---|---|
| `VOL_THRESHOLD` | [0.5, 1.0, 2.0, 3.0] | Daily PnL |
| `LAMBDA1` | [0.3, 0.5, 0.7] | PnL & end inventory |
| `SKEW_FACTOR` | [0.2, 0.5, 1.0] | PnL & max drawdown |
| `LIQUIDATION_THRESHOLD` | [10, 15, 18] | Max position hit |
| Order size per quote | [1, 3, 5] | Fill rate & PnL |

### 8.3 Evaluation Metrics (matching paper Figure 4 & 5)

- **Daily return (bps):** PnL / (avg mid-price × avg position × ticks per day)
- **End-of-day inventory:** `|pos|` at final timestamp
- **Fill rate:** fraction of submitted orders that execute
- **Max drawdown:** max cumulative PnL drop intraday

### 8.4 Strategy Progression

Implement and backtest in order:
1. `last` baseline
2. `last+v`
3. `last+im`
4. `last+im+v` (full strategy)
5. Add inventory skew on top of best performer
6. Add liquidation logic

---

## 9. Edge Cases & Known Pitfalls

- **Empty order book:** guard with `if not depth.buy_orders` before accessing `max()`.
- **Integer price rounding:** always use `math.ceil` for ask, `math.floor` for bid.
- **Position limit violation:** the exchange cancels ALL orders if any single order
  would breach the limit — use `clamp_volume` before every submission.
- **traderData size:** keep JSON small; store only last 50 prices and scalar state.
- **Stale `last_price`:** if TOMATOES has no trades for several ticks, `delta = 0`
  correctly falls back to `last` strategy rather than widening unnecessarily.
- **Market impact of own orders:** the backtester does not model this, but on live
  submission with thin books, large quote sizes can move prices adversely.

---

## 10. File Structure

```
trader.py          ← submission file (single file required)
backtest/
  run_backtest.py  ← grid search harness
  results/         ← CSV logs of (params, PnL, inventory)
analysis/
  tomatoes_eda.ipynb  ← your statistical analysis notebook
```
