# Point-by-Point Critique of `stratégie_gestionportefeuille.py`

**Product:** TOMATOES · Position limit: ±80 · Tick size: 0.5  
**Dataset:** 20,000 observations across two tutorial-round days  
**Reference analysis:** `TOMATOES_MA_Analysis.md`

---

## Preamble

The strategy is structured around two concurrent components: an aggressive taker loop ("TAKER BERSERKER") and a passive market-making loop with position-skew rebalancing ("MAKER DYNAMIQUE"). Both components are evaluated below against the empirical properties of the TOMATOES price process established in the statistical analysis. Critiques are ordered from most to least severe, with supporting quantitative evidence from the tutorial-round data.

---

## Critique 1 — The Taker Component Is Mathematically Inert

**Severity: Critical**

**Code (lines 172–184):**
```python
for price, vol in order_depth.sell_orders.items():
    if price < fair_price:  # buy if ask is below fair
        ...
for price, vol in order_depth.buy_orders.items():
    if price > fair_price:  # sell if bid is above fair
        ...
```

**Fair value definition (line 164):**
```python
fair_price = (best_bid + best_ask) / 2
```

**Finding:** The taker condition `price < fair_price` applied to sell orders is algebraically impossible given the fair value definition. By construction:

$$\text{fair\_price} = \frac{\text{best\_bid} + \text{best\_ask}}{2} \implies \text{best\_ask} - \text{fair\_price} = \frac{\text{best\_ask} - \text{best\_bid}}{2} = \frac{\text{spread}}{2}$$

Since the spread is strictly positive at every observed tick (minimum spread observed: 5.0 ticks, minimum half-spread: 2.5 ticks), `best_ask ≥ fair_price + 2.5` holds universally. The sell-side taker condition `price < fair_price` is therefore **never true**. The same reasoning applies symmetrically to the buy-side condition. Over the full 20,000-observation dataset, the taker loop produces **zero executions**.

The module is labelled "TOUJOURS ACTIF" (always active). It is, in practice, always inactive.

**Consequence:** The strategy's only source of executed trades is the passive maker loop. The taker loop consumes compute and adds code complexity while contributing nothing to PnL.

**Correction:** The taker trigger must be defined relative to an estimate of fair value that is independent of the current bid-ask midpoint — for example, an EWM of historical mid-prices. Only when the best ask falls below the *smoothed* fair estimate, or the best bid rises above it, does a genuine mispricing exist worth taking.

---

## Critique 2 — Fair Value Is Estimated with Maximum Noise

**Severity: High**

**Code (line 164):**
```python
fair_price = (best_bid + best_ask) / 2
```

The instantaneous mid-price is the noisiest possible estimator of fair value in this market structure. The TOMATOES return distribution shows that 57.1% of 100-ms steps produce a zero change in fair value, and that observed returns are serially anti-correlated (AR(1) φ = −0.177). The raw mid-price inherits all tick-level noise without any smoothing.

Quantitatively, the mid-price is unchanged 32.1% of tick-to-tick comparisons — meaning at those steps the mid-price carries no incremental information over the previous tick, yet the strategy recalculates orders around it as though it does.

An EWM estimator with span=10 (α ≈ 0.182) reduces tick noise while maintaining responsiveness. The blended estimator `fair = 0.7 × EWM + 0.3 × mid` produced a +52 PnL improvement (+0.35%) in historical replay at zero architectural cost. At a 0.35% improvement per day, this compounds meaningfully over a multi-day round.

---

## Critique 3 — The Skew Maker Ask Is Placed at a Marketable Price

**Severity: High**

**Code (lines 193–199):**
```python
if current_pos >= REBALANCE_THRESHOLD:
    maker_ask = math.ceil(fair_price)
    maker_bid = best_bid - 1
```

When `current_pos ≥ 50`, the strategy sets `maker_ask = ceil(fair_price)`. With the modal spread of 13 ticks, `fair_price = best_bid + 6.5`, so `ceil(fair_price) = best_bid + 7`. The current `best_ask` is `best_bid + 13`. The strategy therefore places a sell order at `best_bid + 7`, which is **6 ticks inside the current best ask**.

An order placed at a price that improves on the best ask by 6 ticks is a *marketable limit order* — it will be immediately swept by any incoming buy-side bot taker, behaving as a taker order rather than a maker order. The strategy pays the spread implicitly rather than earning it.

The intent of the skew logic — to reduce a long position passively — is sound. The execution is not. Passive rebalancing should place the ask at `best_ask` or `best_ask - 1`, not at the mid-price, to avoid immediate execution at an adversely selected price.

---

## Critique 4 — The Rebalance Threshold Is Uncalibrated

**Severity: Medium–High**

**Code (line 152):**
```python
REBALANCE_THRESHOLD = 50
```

The threshold is set at 50 out of 80, corresponding to 62.5% of the position limit. No empirical basis for this value is provided or derivable from the data. The threshold determines the fraction of position space in which the strategy operates in skew mode versus neutral mode. At 62.5%, the strategy spends the majority of its capacity in neutral (pennying) mode.

The correct calibration of this threshold depends on the expected position distribution, which in turn depends on the fill rate of the passive maker orders — a quantity that cannot be determined without simulation. The Monte Carlo backtester provides exactly this data via `session_summary.csv` (position histograms across 100–1,000 sessions). Using a hardcoded value without backtested position data means the threshold is as likely to be wrong as right.

Additionally, the threshold is symmetric (±50), whereas the optimal threshold for the buy side and sell side need not be equal if the order flow is directionally asymmetric on a given day.

---

## Critique 5 — Passive Maker Posts Full Remaining Capacity as a Single Order

**Severity: Medium–High**

**Code (lines 215–218):**
```python
remaining_buy_cap = POSITION_LIMIT - current_pos
...
if remaining_buy_cap > 0:
    orders.append(Order(PRODUCT, int(maker_bid), remaining_buy_cap))
```

At `current_pos = 0`, the strategy posts a single buy order for 80 units and a single sell order for 80 units simultaneously. A single bot taker filling the full order in one step moves the position from 0 to ±80 in a single tick. Given the mean-reverting structure of the price process (AR(1) φ = −0.177, sign-flip probability = 84.5%), this creates an immediate adverse inventory problem: the strategy is maximally long at a point where the next price move is more likely a reversion downward.

Size laddering — splitting the 80 units across two or three price levels — reduces single-step inventory risk at the cost of some queue-position degradation. The trade-off is empirically testable via the Monte Carlo engine.

---

## Critique 6 — The Skew Bid Placement in SKEW LONG Mode Is Counterproductive

**Severity: Medium**

**Code (lines 197–198):**
```python
# SKEW LONG
maker_bid = best_bid - 1
```

In SKEW LONG mode (`current_pos ≥ 50`), the strategy places a buy order at `best_bid - 1`. This order is one tick behind the current best bid and will only fill if a seller is willing to transact one tick below the prevailing market. Fill probability is negligible.

More importantly, placing any buy order when the position is already ≥ 50 is directionally inconsistent with the rebalancing objective. The stated goal of SKEW LONG mode is to reduce inventory. Simultaneously posting a buy order — however unlikely to fill — represents a structural contradiction between the two halves of the maker logic. In the event of an unusual fill (e.g., a distressed seller during a liquidity event), the strategy would be adding to an already oversized long position. The buy order in SKEW LONG mode should be suppressed entirely or capped at a token size for optionality.

---

## Critique 7 — Conversions Are Hardcoded to 1 Every Tick

**Severity: Medium**

**Code (line 147):**
```python
conversions = 1
```

The `conversions` field is set unconditionally to 1 at every timestep. In the IMC Prosperity 4 tutorial round, TOMATOES does not utilise the conversion mechanism — the conversion observation fields (importTariff, exportTariff, transportFees, sunlightIndex, sugarPrice) are present in the data model but carry no pricing signal for this product in round 0.

Sending `conversions = 1` every tick is at best a no-op and at worst a systematic error if the exchange enforces conversion constraints or charges fees per conversion request. The correct value for a product that does not use conversions is `conversions = 0`.

---

## Critique 8 — The Strategy Is Entirely Stateless

**Severity: Medium**

**Observation:** The `Trader` class has no `__init__` method. No price history, position history, or volatility estimate is maintained across ticks. The `traderData` string — the Prosperity API's explicit mechanism for persisting state between calls — is written as an empty string and never read:

```python
logger.flush(state, result, conversions, "")   # writes ""
return result, conversions, ""                 # returns ""
```

The statistical analysis demonstrates that the TOMATOES return process has structured serial dependence (AR(1) φ = −0.177, Ljung–Box p < 0.001 at all tested lags). Exploiting this dependence requires maintaining a rolling estimate of the price process. The EWM fair value estimator, a short-window realised volatility estimate for dynamic spread sizing, or a simple running position VWAP for skew calibration — none of these are implementable without state. The absence of any state management forecloses these improvements entirely.

The `traderData` field supports JSON serialisation of arbitrary state. Using it costs nothing in terms of execution time and is the intended mechanism for cross-tick memory.

---

## Critique 9 — Neutral-Mode Pennying Is Not Validated Against Order Book Depth

**Severity: Low–Medium**

**Code (lines 210–212):**
```python
maker_bid = best_bid + 1
maker_ask = best_ask - 1
```

The neutral-mode maker improves on both sides by 1 tick. This is a standard pennying strategy and is structurally correct given the bot-driven order book architecture. The reposited order sits 5.5 ticks from fair value (with the modal spread of 13), well inside the inner bot wall. The issue is not the price placement but the volume: posting 80 units at a single level with no depth check means the strategy relies entirely on bot taker flow for fills.

The strategy does not inspect `bid_volume_1` or `ask_volume_1` to gauge whether the pennied order is likely to receive flow, nor does it check whether the pennied price coincides with a bot wall price (which would create queue competition with mechanically large bot orders). At minimum, the order book depth fields available in the CSV — `bid_volume_1`, `bid_volume_2`, `bid_volume_3` — should inform size decisions.

---

## Critique 10 — No Spread-Conditioned Logic

**Severity: Low**

The spread varies between 5 and 14 ticks across observed states (distribution: 5 ticks 0.9%, 6 ticks 1.3%, 7 ticks 2.0%, 8 ticks 2.3%, 9 ticks 0.7%, 13 ticks 48.0%, 14 ticks 44.8%). The strategy applies identical maker pricing logic (`best_bid + 1`, `best_ask - 1`) regardless of whether the spread is 5 or 14 ticks.

When the spread is 5 ticks, `best_bid + 1` and `best_ask - 1` are 3 ticks apart. The maker is operating with a 3-tick gross edge, which may be insufficient to cover adverse selection risk. When the spread is 14 ticks, the edge is 12 ticks — significantly more favourable. Conditioning maker aggressiveness on spread width (quoting more volume at wider spreads, reducing size at narrow spreads) is a standard market-making adjustment that the strategy does not implement.

---

## Summary Table

| # | Issue | Severity | Lines | Quantitative Evidence |
|---|-------|----------|-------|-----------------------|
| 1 | Taker trigger is algebraically impossible | **Critical** | 172–184 | 0 executions in 20,000 ticks; min half-spread = 2.5 ticks |
| 2 | Fair value = raw mid (maximum noise) | **High** | 164 | Mid flat 32.1% of ticks; EWM yields +0.35% replay improvement |
| 3 | Skew ask placed at marketable price (mid) | **High** | 196 | ceil(fair) is 6 ticks inside best_ask at modal spread = 13 |
| 4 | Rebalance threshold uncalibrated | **Medium–High** | 152 | Hardcoded at 62.5% of limit; no Monte Carlo backing |
| 5 | Full capacity posted as one order | **Medium–High** | 215–218 | Single fill moves position 0 → ±80 in one tick |
| 6 | Buy order posted while SKEW LONG | **Medium** | 197–198 | Contradicts rebalancing objective; adversely fills if hit |
| 7 | conversions = 1 unconditionally | **Medium** | 147 | TOMATOES has no conversion mechanism in round 0 |
| 8 | No state persistence (traderData unused) | **Medium** | 221–222 | AR(1) serial dependence requires cross-tick memory |
| 9 | Maker size ignores order book depth | **Low–Medium** | 215–218 | bid/ask volume fields available but not read |
| 10 | No spread-conditioned logic | **Low** | 210–212 | Spread ranges 5–14 ticks; identical logic applied to all |

---

## Consolidated Corrective Priorities

In order of expected PnL impact:

1. **Reconstruct the taker trigger** around an EWM fair value estimate rather than the instantaneous mid-price. This is the only path to activating the taker component at all.
2. **Fix the skew ask placement.** Move it to `best_ask` or `best_ask - 1` to operate as a passive maker during rebalancing rather than an immediate taker.
3. **Implement state persistence** via `traderData` to support EWM, volatility estimation, and VWAP tracking across ticks.
4. **Suppress the buy order in SKEW LONG mode** (and the sell order in SKEW SHORT mode) to eliminate the directional contradiction.
5. **Set `conversions = 0`** for TOMATOES unless a conversion-eligible product is in scope.
6. **Calibrate REBALANCE_THRESHOLD** empirically using the Monte Carlo position distribution.
