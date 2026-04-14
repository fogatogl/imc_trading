# NaN Handling Strategy Analysis

Applies to: `ash_coated_osmium_analysis.ipynb` and `intarian_pepper_root_analysis.ipynb`

---

## Problem Context

Both notebooks concatenate 3 days of price data (`day -2, -1, 0`) into a single `ob` DataFrame.
Any operation that looks at consecutive rows (`.diff()`, `.pct_change()`, `.shift()`) will silently
cross day boundaries, treating the last price of day N and the first price of day N+1 as adjacent
intraday ticks. This is wrong: the gap represents an overnight session with no recorded activity.

Two distinct problems arise:

| Problem | Location | Effect |
|---|---|---|
| **Day-boundary contamination** | `diff()` / `pct_change()` across days | Overnight jump enters serial covariance, rolling vol |
| **Sparse intraday std bins** | `intra['std']` in §22d | NaN for bins with 0-1 observations, must choose fill strategy |

---

## Problem 1 — Day-Boundary Contamination

### Where it occurs

- **Cell 46** (`§22b` Roll Spread Estimator): `ob['mid_price'].diff()` used for serial covariance
- **Cell 52** (Volatility): `ob['log_ret'] = log(P_t / P_{t-1})` fed into rolling std

### Three methods compared

#### Method 1: `dropna` with boundary mask — Best

Set the first diff of each new day to `NaN`, then `dropna()`.

```python
boundary_mask = ob['day'].diff().fillna(0) != 0
dp = ob['mid_price'].diff().where(~boundary_mask)
dp_arr = dp.dropna().values
```

Pros:
- Removes contamination entirely — serial covariance computed on within-day returns only
- No artificial data introduced
- Loses only 2 rows out of ~30,000 (< 0.01%)
- Rolling window skips NaN cleanly with `min_periods`

Cons:
- Tiny sample size reduction (negligible)

---

#### Method 2: fill_last (zero return at boundary)

Replace boundary diff with 0 — assumes price stands still overnight.

```python
dp = ob['mid_price'].diff()
dp[boundary_mask] = 0
```

Pros:
- Keeps all rows
- Suppresses the overnight spike in rolling vol

Cons:
- Artificial: inserts a `return = 0` that never happened
- Biases serial covariance: `Cov(0, next_return)` is partially fabricated
- A false zero followed by a real return creates spurious mean-reversion signal
- For Roll estimator: the artificial zero paired with the next real return contaminates the
  covariance estimate in an unpredictable direction depending on what the overnight gap was

---

#### Method 3: linear interpolation

Smooth price across the boundary via `interpolate(method='index')`, then diff.

```python
price_interp = ob['mid_price'].interpolate(method='index')
dp = price_interp.diff().where(~boundary_mask)
```

Pros:
- Spreads the overnight move smoothly rather than creating a single spike

Cons:
- Manufactures price data that never existed
- The smoothed boundary return measures a modelling assumption, not market microstructure
- No information about what actually happened between sessions — interpolation is pure guesswork

### Verdict for Problem 1

| Method | Roll spread bias | Vol bias | Data integrity | Recommendation |
|---|---|---|---|---|
| keep all (original) | High — overnight spike enters cov | High — spike in rv | Honest | Do not use |
| fill_last (0 return) | Medium — zero distorts cov | Low | Artificial | Acceptable only if sessions are truly continuous |
| interpolate | Unpredictable | Unpredictable | Fabricated | Do not use |
| **dropna (mask)** | None | None | Honest | **Use this** |

**Adopted:** dropna with boundary mask in cells 46 and 52.

---

## Problem 2 — Sparse Intraday Std Bins

### Where it occurs

**Cell 50** (`§22d` Intraday Spread Pattern): `intra['std']` computed via
`groupby('ts_bin')['spread'].std()`. Bins at the very start or end of the day may contain only
1 observation across all 3 days, giving `std = NaN`. The `fill_between` band requires non-NaN.

### Three methods compared

#### Method 1: `fillna(0)` — original

```python
intra['std'].fillna(0)
```

Effect: Band collapses to a line at sparse bins. Visually identical to "zero uncertainty" —
misleads the reader into thinking variance is exactly zero at the edges of the day.

Verdict: Incorrect interpretation. Avoid.

---

#### Method 2: ffill (forward-carry)

```python
intra['std'].ffill().bfill()
```

Effect: Each sparse bin inherits the std of the nearest preceding non-sparse bin.

Pros:
- Preserves visual continuity
- The width reflects a real observed std, just from an adjacent bin

Cons:
- Step-function artefacts at transitions
- Could misrepresent structure if the adjacent bin is from a structurally different time-of-day

---

#### Method 3: linear interpolation — Best (for plotting only)

```python
intra['std'].interpolate(method='linear').ffill().bfill()
```

Effect: Smoothly transitions std between known non-sparse bins.

Pros:
- No step artefacts
- Makes the uncertainty band continuous and readable
- Reasonable assumption: adjacent time-of-day bins have similar spreads (spread is locally
  auto-correlated), so linear interpolation is mild
- `ffill/bfill` handles leading and trailing NaN at the band edges

Cons:
- Manufactures values for bins with no data
- Appropriate for visualisation only — do not use interpolated std in any statistical test

### Verdict for Problem 2

| Method | Visual quality | Statistical validity | Recommendation |
|---|---|---|---|
| fillna(0) | Poor — false precision | Wrong — implies zero variance | Do not use |
| ffill | Acceptable | Neutral | Acceptable |
| **interpolate** | Good — smooth | For plotting only | **Use this** |

**Adopted:** `interpolate` in cell 50 for the `fill_between` band only.
All statistical computations (ACF, breakeven analysis) continue to use `dropna()` on the raw series.

---

## Full Summary

| Section | Original method | Problem | New method |
|---|---|---|---|
| §22b Roll Estimator (cell 46) | dropna only | Kept cross-day diffs in cov | **dropna + boundary mask** |
| §22d Intraday std band (cell 50) | fillna(0) | False zero uncertainty at edges | **linear interpolation (plot only)** |
| §23 Volatility (cell 52) | No boundary handling | Overnight spikes inflate rolling vol | **dropna + boundary mask** |

---

## General Decision Rule for This Dataset

```
NaN is structural (day boundary, window warmup)  ->  dropna / mask
NaN means a value is truly absent (missing LOB level)  ->  fillna(0)
NaN is in a plot aesthetic (band width)  ->  interpolate (visual only, not for stats)
NaN comes from a denominator that could be zero  ->  replace(0, np.nan)
```
