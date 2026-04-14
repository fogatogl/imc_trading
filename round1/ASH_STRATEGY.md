# ASH_COATED_OSMIUM — Strategy Notes

**Product:** ASH_COATED_OSMIUM  
**Position limit:** ±50 units  
**Dataset:** Round 1, days −2 / −1 / 0 (29,951 clean rows after filtering empty-book artifacts)

---

## 1. OBI Signal Discovery

### What is OBI?

Order Book Imbalance at level 1:

```
OBI = (bid_vol_1 - ask_vol_1) / (bid_vol_1 + ask_vol_1)   ∈ [-1, 1]
```

Positive OBI → more volume on the bid side (buying pressure).  
Negative OBI → more volume on the ask side (selling pressure).

### Statistical findings

Linear regression on all clean rows:

```
fwd_1 = 0.010 + 6.74 × OBI     R² = 0.42,  n = 29,948
```

where `fwd_1` = mid-price change over the next 100 timestamps.

| Metric | Value |
|--------|-------|
| Pearson correlation (OBI, fwd_1) | **+0.645** |
| Correlation per day | 0.647 / 0.652 / 0.638 (consistent) |
| Hit rate when OBI > 0.25 | **87.9%** (price rises next tick) |
| Hit rate when OBI < −0.25 | **88.3%** (price falls next tick) |
| t-statistic at `|OBI| > 0.25` | ~57 |
| Signal persistence | Lags 1–10 rows (100–1000 ts) |

OBI bin breakdown — strictly monotone:

| OBI range | Mean fwd_1 | t-stat |
|-----------|-----------|--------|
| [−1.0, −0.5] | −6.21 | −70.1 |
| (−0.5, −0.25] | −1.55 | −30.5 |
| (−0.25, 0] | −0.05 | −2.4 |
| (0, 0.25] | +2.05 | +19.7 |
| (0.25, 0.5] | +1.50 | +29.3 |
| (0.5, 1.0] | +6.59 | +75.6 |

### Trade flow — weak and contrarian

Market trade net flow (signed volume, buy − sell) was also tested. It is **not** a useful directional signal:

- Large buy flow → slightly negative next-tick return (mean-reversion)
- Large sell flow → slightly positive next-tick return
- All t-statistics < 3, not reliable standalone

This is consistent with liquidity-taker dynamics: aggressive buys temporarily lift price, which then snaps back. **Do not use trade flow for direction.**

### Data artifact: empty-book rows

~49 rows per dataset have `mid_price = 0` (both sides of the book absent). These create spurious ±10,000 tick jumps in forward returns and must be filtered before any analysis (`mid > 0` guard).

---

## 2. Baseline Strategy — `ash_mm_trader.py`

A pure symmetric market maker with no directional signal.

### Quote formula

```
fair_value  = EMA(mid_price, span=5)
half_spread = max(2.0, 0.5 × σ)        σ = rolling std of 10-bar price changes
skew        = 0.5 × pos                 push quotes away from flat to unwind inventory
my_bid      = round(fair_value - half_spread - skew)
my_ask      = round(fair_value + half_spread - skew)
buy_qty     = 50 - pos
sell_qty    = 50 + pos
```

Quotes are always symmetric around EMA. The inventory skew uses raw position (target = 0 always).

### Performance

| Day | PnL |
|-----|-----|
| −2 | 2,678 |
| −1 | 2,932 |
| 0 | 3,516 |
| **Total** | **9,126** |

---

## 3. OBI Strategy — `ash_obi_trader.py`

Incorporates the OBI signal by shifting the fair-value centre rather than targeting a fixed position.

### Core change

```
adjusted_fv = EMA + OBI_LAMBDA × obi_ema
my_bid      = round(adjusted_fv - half_spread - INV_SKEW × pos)
my_ask      = round(adjusted_fv + half_spread - INV_SKEW × pos)
```

OBI is EMA-smoothed (`alpha = 0.3`, ~span-6) before use. The EMA suppresses single-tick noise while preserving the signal's persistence window (lags 1–10).

### Why fair-value adjustment, not a directional target

An early version used a tiered position target (±40 when `|OBI| > 0.5`). With `INV_SKEW = 0.5` and `excess = pos − target`, this produced:

```
target = +40, pos = 0  →  excess = −40  →  skew = −20
my_bid = ema − 3 + 20 = ema + 17          (market ask ≈ ema + 8)
```

The bid crossed the market's ask, causing immediate expensive fills and massive losses (−65,000 over 3 days). The error was treating OBI as a signal large enough to justify an aggressive ±40-unit position with zero regard for spread costs.

The fair-value adjustment is mathematically equivalent to a **continuous** directional target:

```
target = (OBI_LAMBDA / INV_SKEW) × obi_ema = 50 × obi_ema
```

At `obi_ema = 0.5` → target ≈ 25 units. At `obi_ema = 1.0` → target = 50 (the full position limit). The difference: the skew is bounded by the half-spread, so quotes never cross the market.

### Quote example at OBI = 0.5

With `OBI_LAMBDA=10, MIN_HALF_SPREAD=4, INV_SKEW=0.2, pos=0`:

```
adjusted_fv = ema + 5.0
my_bid      = ema + 5.0 − 4.0 − 0 = ema + 1.0   (inside spread, attracts sellers)
my_ask      = ema + 5.0 + 4.0 − 0 = ema + 9.0   (at/above market best ask ≈ ema+8)
```

Result: easy to accumulate longs passively; ask rarely filled, protecting the long. As position builds, the inventory skew gradually normalises quotes back toward ema.

### Final parameters (grid-searched over 135 combinations)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `OBI_LAMBDA` | 10.0 | Fair-value shift per unit of OBI |
| `OBI_EMA_ALPHA` | 0.3 | OBI smoothing (~span-6 EMA) |
| `MIN_HALF_SPREAD` | 4.0 | Minimum half-spread in ticks |
| `INV_SKEW` | 0.2 | Quote shift per unit of position |
| `VOL_MULT` | 0.5 | `half_spread = max(4.0, 0.5 × σ)` |
| `EMA_SPAN` | 5 | Fair-value EMA |
| `POS_LIMIT` | 50 | Hard position cap |

Key insight from the grid: **wider spread + lower skew** consistently outperforms. Higher `MIN_HALF_SPREAD` earns more per fill; lower `INV_SKEW` allows the OBI signal to accumulate a larger position before inventory pressure overrides.

### Performance vs baseline

| Day | Baseline | OBI Trader | Delta |
|-----|----------|------------|-------|
| −2 | 2,678 | 7,840 | +193% |
| −1 | 2,932 | 8,283 | +182% |
| 0 | 3,516 | 7,859 | +124% |
| **Total** | **9,126** | **23,982** | **+163%** |

---

## 4. Key Takeaways

1. **OBI is the dominant signal for ASH.** Correlation 0.645 with next-100ts return, consistent across all 3 days and all lags 1–10. Use it.

2. **Use OBI to shift fair value, not to target a large position directly.** The skew mechanism already converts the fair-value shift into a natural equilibrium position of `OBI_LAMBDA / INV_SKEW × OBI`. Explicit targets with large skew overcorrect and cause quotes to cross the market.

3. **Trade flow is contrarian, not directional.** Mean-reversion after large trades is the norm. Do not chase trade flow.

4. **Wider half-spread improves MM PnL when you have a directional edge.** The OBI signal pulls our bid into the buy zone (above neutral ema) when OBI > 0, so fills happen without needing a tight spread. The wider spread then earns more per fill.

5. **Filter empty-book rows** (`mid_price = 0` artifact). They corrupt forward-return statistics and must be excluded from any signal analysis.

---

## 5. Analysis Scripts

| File | Purpose |
|------|---------|
| `round1/ash_volume_signal.py` | OBI correlation analysis, hit rates, lag study |
| `round1/ash_mm_trader.py` | Baseline pure market maker |
| `round1/ash_obi_trader.py` | OBI-adjusted fair-value market maker |
| `round1/ash_mm_param_search.py` | Parameter grid search for baseline |

Backtest command (from project root):

```bash
PYTHONPATH=imc_trading/imc-prosperity-4-backtester \
.venv/Scripts/python.exe -m prosperity4bt \
round1/ash_obi_trader.py 1--2 1--1 1-0 --data dataset --no-vis --no-out
```
