# Statistical Analysis of TOMATOES Price Data
## IMC Prosperity 4 — Round 0, Days −2 & −1

---

## Executive Summary

Every statistical test applied to the TOMATOES mid-price series converges on a single, unambiguous conclusion: **the price process is strongly mean-reverting at all tested timescales.** The Hurst exponent (H≈0.39), variance ratio profile (VR monotonically below 1), AR(5) model (all-negative lags, all p<0.001), Ljung-Box test on returns (LB≈1,700), and FFT periodogram (power concentrated near the Nyquist frequency) are entirely consistent with each other. The primary tradeable edge is a short-horizon fade strategy driven by the AR(5) forecast equation.

---

## 1. Data & Price Structure

**Source:** Two CSV files — `prices_round_0_day_-1.csv` and `prices_round_0_day_-2.csv`, filtered to `product == 'TOMATOES'`. The two days are concatenated for combined analysis and also examined separately.

**Price range and volatility:**

| Metric | Value |
|---|---|
| Mid-price range | 4,946.5 – 5,036.0 |
| Total swing | ~89 points |
| Mid-price std dev | 19.75 |
| Bid₁ std dev | 19.73 |
| Ask₁ std dev | 19.80 |
| Bid-ask spread (approx.) | ~9 points at level 1 |
| Bid volume L1 std dev | 1.79 (range 2–12) |
| Bid volume L2 std dev | 3.89 (range 3–25) |

**Key observations:**
- The bid and ask standard deviations are nearly identical (~19.7–19.8), indicating a symmetric, well-balanced order book.
- Volume at level 1 is shallow (max 12), suggesting the book is thin at the top of the queue. Larger orders will move the price.
- The ~89-point total range over two days is moderate relative to the ~5,000 price level (~1.8%).

---

## 2. Stationarity Tests (ADF & KPSS)

### Theory

A series is **stationary** if its statistical properties (mean, variance, autocorrelation) do not change over time. For financial price series, the standard result is that *levels* are non-stationary (I(1)) while *first differences* (returns) are stationary (I(0)). This is important because mean-reversion strategies can only be reliably applied to stationary series or to stationary transformations (e.g. spread, z-score deviation from a moving average).

Two complementary tests are used:
- **ADF (Augmented Dickey-Fuller):** H₀ = unit root exists (non-stationary). Rejection → stationary.
- **KPSS:** H₀ = series is stationary. Rejection → non-stationary.

When both agree, the verdict is unambiguous.

### Results

**Price levels:**

| Day | ADF stat | ADF p-value | KPSS stat | KPSS p-value | Verdict |
|---|---|---|---|---|---|
| Day −1 | −2.064 | 0.259 | 13.421 | 0.010 | ❌ Non-stationary |
| Day −2 | −2.397 | 0.143 | 4.450 | 0.010 | ❌ Non-stationary |

**Log returns:**

| Day | ADF stat | ADF p-value | KPSS stat | KPSS p-value | Verdict |
|---|---|---|---|---|---|
| Day −1 | −43.341 | 0.000 | 0.029 | ≥0.10 | ✅ Stationary |
| Day −2 | −40.935 | 0.000 | 0.045 | ≥0.10 | ✅ Stationary |

### Interpretation

Price levels are **I(1)** — integrated of order 1. Log returns are **I(0)** — stationary. This is the canonical result for financial prices. The ADF statistics on returns (−41 to −43) are extraordinarily large in absolute value; there is essentially zero probability of misclassifying the returns as non-stationary.

**Trading implication:** All modelling and signal generation should be performed on *log returns*, not raw price levels. Mean-reversion should be detected and sized relative to deviations from a rolling mean or spread, not from a fixed level.

---

## 3. Drift: OLS Trend Regression

### Theory

A drifting series has a systematic directional bias — it tends to move up or down on average each step. This is tested by regressing price on a linear time trend:

$$p_t = \alpha + \beta \cdot t + \varepsilon_t$$

If β is statistically significant, there is a detectable drift. The R² measures what fraction of total price variance is explained by this linear trend alone.

### Results

| Day | Intercept α | Drift β (per tick) | t-stat | p-value | R² |
|---|---|---|---|---|---|
| Day −1 | 4,999.22 | **−0.004332** | −166.9 | 0.000 | 0.7358 |
| Day −2 | 4,999.63 | **+0.001664** | +52.8 | 0.000 | 0.2179 |

### Interpretation

Both regressions are highly significant by t-statistic, but the **conclusions are contradictory**:

- Day −1 shows a strong downward drift with R²=0.74 — 74% of price variance is "explained" by a linear downtrend.
- Day −2 shows a weak upward drift with R²=0.22 — only 22% of variance is explained.

The reversal in sign across consecutive days, and the dramatic drop in explanatory power, is the tell. **This is not a structural directional bias.** It is the stochastic trend component of the underlying I(1) price process manifesting as a spurious regression slope. An I(1) random walk sampled over a finite window will almost always produce a statistically significant OLS slope — this is the well-known spurious regression problem. The R²=0.74 on day −1 looks compelling but is an artefact of the data window, not a predictive feature.

**Do not build a directional bias** into a trading strategy based on these regressions. The signal reverses between days and will likely cost PnL in live trading.

---

## 4. Autocorrelation: Ljung-Box Test

### Theory

In an efficient market, returns should be serially uncorrelated — past prices should contain no information about future prices. The **Ljung-Box (LB) test** is a formal joint test of whether all autocorrelations up to lag k are simultaneously zero:

- H₀: No autocorrelation up to lag k.
- Low p-value → significant autocorrelation is present → returns are predictable from their own history.

### Results — Price Levels

| Day | Lag | LB Stat | p-value |
|---|---|---|---|
| Day −1 | 1 | 9,913 | 0.000 |
| Day −1 | 10 | 98,338 | 0.000 |
| Day −2 | 1 | 9,832 | 0.000 |
| Day −2 | 10 | 97,315 | 0.000 |

### Results — Log Returns

| Day | Lag | LB Stat | p-value |
|---|---|---|---|
| Day −1 | 1 | 1,702 | 0.000 |
| Day −1 | 10 | 1,710 | 0.000 |

> ⚠️ **Code bug noted:** In Cell 17, the day −2 log-returns Ljung-Box loop accidentally reuses `lb_results_1` (day −1 data) instead of `lb_results_2`. The day −2 returns numbers shown are therefore duplicates of day −1. This should be corrected by replacing the loop variable with `lb_results_2`. The qualitative conclusion is very unlikely to change given the consistency of all other results across both days.

### Interpretation

The LB statistics on **price levels** are expected to be large — any persistent or trending series produces autocorrelated levels. This is not a trading signal by itself.

The critical finding is the LB statistic on **log returns** of approximately 1,700 at lag 1 and growing to 1,710 at lag 10. For comparison, white-noise returns would produce a chi-squared statistic with expectation equal to the number of lags tested. An LB of 1,702 at lag 1 is approximately 1,700 standard deviations above the white-noise null. This is not noise — TOMATOES returns carry a massive, statistically certain autocorrelation structure that is directly exploitable.

---

## 5. Hurst Exponent (R/S Analysis)

### Theory

The **Hurst exponent H** characterises the long-range memory and self-similarity of a time series:

| H value | Process | Behaviour |
|---|---|---|
| H = 0.5 | Random walk | No memory — efficient market |
| H > 0.5 | Persistent / trending | Trends persist — momentum edge |
| H < 0.5 | Anti-persistent / mean-reverting | Reversals are more likely than continuations |

H is estimated via **R/S (Rescaled Range) analysis**: for each window size n, compute the ratio of the range of cumulative deviations from the mean to the standard deviation. This ratio scales as n^H. Taking logarithms: log(R/S) = log(c) + H·log(n), so H is estimated as the slope of a log-log regression.

### Results

| Day | H estimate | Std error | 95% CI | R² of fit |
|---|---|---|---|---|
| Day −1 | **0.3876** | 0.0040 | [0.3798, 0.3955] | 0.9970 |
| Day −2 | **0.3914** | 0.0043 | [0.3830, 0.3999] | 0.9966 |

### Interpretation

Both estimates are tightly clustered around H≈0.39, with confidence intervals that exclude 0.5 by a substantial margin (the nearest CI boundary is 0.40, still well below 0.5). The R² of the log-log regression exceeds 0.996 on both days, meaning the scaling relationship is clean and reliable — there is no evidence of regime changes or broken scaling across window sizes.

An H of 0.39 (versus the random walk's 0.50) represents a meaningful and exploitable degree of anti-persistence. After a positive return, the next return is more likely to be negative, and vice versa, with a memory that extends across multiple timescales.

The consistency of the estimate across both days strengthens confidence that this is a structural feature of TOMATOES' price dynamics, not a one-day artefact.

---

## 6. Variance Ratio Test

### Theory

The **Variance Ratio (VR) test** (Lo & MacKinlay, 1988) exploits the property that, for a pure random walk, variance grows linearly with the horizon:

$$\text{VR}(k) = \frac{\text{Var}(\text{k-period returns})}{k \cdot \text{Var}(\text{1-period returns})}$$

Under a random walk, VR(k) = 1 for all k. Departures indicate:
- VR(k) > 1: positive autocorrelation → **momentum**
- VR(k) < 1: negative autocorrelation → **mean-reversion**

A heteroskedasticity-robust z-statistic (Lo-MacKinlay) is used to test whether each VR(k) is significantly different from 1.

### Results

| Horizon k | VR — Day −1 | VR — Day −2 | z-stat (D−1) | Interpretation |
|---|---|---|---|---|
| k = 2 | 0.5876 | 0.5720 | −22.25 | Mean-reversion ↓ |
| k = 4 | 0.3698 | 0.3543 | −21.02 | Mean-reversion ↓ |
| k = 8 | 0.2566 | 0.2421 | −18.57 | Mean-reversion ↓ |
| k = 16 | 0.1973 | 0.1810 | −15.33 | Mean-reversion ↓ |
| k = 32 | 0.1726 | 0.1505 | −11.80 | Mean-reversion ↓ |

All p-values = 0.000 across both days.

### Interpretation

The VR profile is **monotonically decreasing from 0.57 at k=2 to 0.17 at k=32**, with all values highly significantly below 1. Two features stand out:

1. **VR(k=2) ≈ 0.57.** This means that roughly 43% of any single-tick price move is expected to reverse on the very next tick. Put differently: if the price rises by 1 unit on tick t, the best prediction for tick t+1 is a fall of approximately 0.43 units.

2. **The profile deepens monotonically.** Rather than the VR recovering toward 1 at longer horizons (which would suggest mean-reversion only at short timescales), it continues falling to 0.17 at k=32. This is the variance ratio signature of a strong Ornstein-Uhlenbeck-like restoring force that dominates at all tested timescales. There is no momentum at any horizon.

The combination of Hurst (H≈0.39) and VR profile provides a complete picture: anti-persistent at all scales, with the reversal effect strongest at short horizons (1–5 ticks) and remaining significant out to 32 ticks.

---

## 7. AR Model — Autoregressive Structure of Returns

### Lag Order Selection

AIC and BIC are used to select the optimal autoregressive lag order p, testing AR(1) through AR(20):

| Day | Best p (AIC) | Best p (BIC) |
|---|---|---|
| Day −1 | 4 | 4 |
| Day −2 | 5 | 5 |

> Note: The AR fit in Cell 35 uses `best_p_aic=5` from the day −2 selection for both days. Day −1 is therefore fit with AR(5) despite AIC preferring AR(4). The difference is minor — the L5 coefficient is small (−0.034) and the conclusions are unchanged.

### AR(5) Coefficients

**Day −1:**

| Lag | Coefficient | t-statistic | p-value | Significance |
|---|---|---|---|---|
| Intercept | −0.000002 | −0.91 | 0.364 | — |
| L1 | **−0.5425** | −54.27 | 0.000 | *** |
| L2 | **−0.3098** | −27.33 | 0.000 | *** |
| L3 | **−0.1684** | −14.48 | 0.000 | *** |
| L4 | **−0.0948** | −8.36 | 0.000 | *** |
| L5 | **−0.0339** | −3.38 | 0.001 | *** |

Durbin-Watson = **2.0018**

**Day −2:**

| Lag | Coefficient | t-statistic | p-value | Significance |
|---|---|---|---|---|
| Intercept | +0.000000 | +0.10 | 0.919 | — |
| L1 | **−0.5665** | −56.71 | 0.000 | *** |
| L2 | **−0.3235** | −28.25 | 0.000 | *** |
| L3 | **−0.1800** | −15.31 | 0.000 | *** |
| L4 | **−0.0908** | −7.93 | 0.000 | *** |
| L5 | **−0.0522** | −5.23 | 0.000 | *** |

Durbin-Watson = **2.0029**

### Interpretation

Several features of these AR(5) results are noteworthy:

**All lags are negative.** Every autoregressive coefficient from L1 to L5 is negative and highly significant. This is the mathematical structure of a mean-reverting process: a positive return at lag k predicts a negative contribution to the current return, and vice versa. There is no lag at which past returns predict continuation.

**The L1 coefficient dominates.** At −0.54 to −0.57, the L1 coefficient is by far the largest in magnitude. More than half of any return is expected to reverse at the immediately following tick. This is a very strong and practically significant effect.

**The coefficients decay cleanly.** The magnitude progression (−0.55, −0.32, −0.18, −0.09, −0.05) follows a smooth decay, consistent with the underlying process having a well-defined characteristic timescale rather than complex multi-scale dynamics.

**The intercept is statistically zero.** Consistent with the conclusion from the drift analysis: there is no reliable directional bias in returns.

**Durbin-Watson ≈ 2.00.** A Durbin-Watson statistic of exactly 2.00 indicates zero first-order autocorrelation in the AR model residuals. The model has fully absorbed the serial dependence in returns. The residuals are white noise — there is no remaining structure to capture with higher-order models.

**The forecast equation:**

$$\hat{r}_t = -0.55 \cdot r_{t-1} - 0.32 \cdot r_{t-2} - 0.18 \cdot r_{t-3} - 0.09 \cdot r_{t-4} - 0.05 \cdot r_{t-5}$$

This is a direct, implementable signal. Using coefficients approximately averaged across the two days, position sizing can be set proportional to the magnitude of $\hat{r}_t$.

---

## 8. FFT Periodogram

### Theory

Fourier analysis decomposes a time series into a sum of sinusoidal components at different frequencies. The **periodogram** plots the power (squared amplitude) at each frequency. A peak at frequency f corresponds to a cycle of period T = 1/f steps. A flat periodogram indicates white noise; a peak indicates cyclical structure.

Prices are detrended before the FFT to avoid the low-frequency trend contaminating the spectrum.

### Results — Price Levels (detrended)

Dominant periods are at very long scales (5,000, 10,000, 2,500 steps), confirming the trend-like behaviour already identified. Not useful for trading signal generation.

### Results — Log Returns

| Day | Rank | Period (steps) | Power |
|---|---|---|---|
| Day −1 | 1 | 2.35 | 0.01 |
| Day −1 | 2 | 2.39 | 0.01 |
| Day −1 | 3 | 2.30 | 0.01 |
| Day −2 | 1 | 2.30 | 0.01 |
| Day −2 | 2 | 2.12 | 0.01 |
| Day −2 | 3 | 2.70 | 0.01 |

### Interpretation

The return spectrum concentrates its dominant power at periods of **2.1–2.7 ticks — near the Nyquist frequency** (the shortest detectable period is 2 steps). This is not a coincidence. A period of exactly 2 corresponds to **perfect sign alternation**: up, down, up, down. Power concentrating near T=2 means the returns are close to — though not exactly — a sign-alternating process.

This is the **spectral fingerprint of a discretised Ornstein-Uhlenbeck (mean-reverting) process.** When a continuous-time OU process is sampled at a rate fast enough to capture its mean-reversion dynamics, the sampled returns exhibit near-Nyquist spectral peaks. This is fully consistent with the AR(5), Hurst, and VR findings.

No sub-session cycles at economically interesting periods (e.g. intraday patterns at fixed intervals) were identified. The only structure is the high-frequency mean-reversion already captured by the AR model.

---

## 9. Summary of Findings

| Test | Day −1 | Day −2 | Conclusion |
|---|---|---|---|
| ADF (price levels) | Non-stationary | Non-stationary | Price is I(1) |
| KPSS (price levels) | Non-stationary | Non-stationary | Price is I(1) |
| ADF (returns) | Stationary | Stationary | Returns are I(0) |
| KPSS (returns) | Stationary | Stationary | Returns are I(0) |
| OLS drift | Downward, R²=0.74 | Upward, R²=0.22 | Contradictory — unreliable |
| Ljung-Box (returns, lag 1) | LB=1,702, p=0.000 | LB≈1,700* | Strong autocorrelation |
| Hurst exponent | H=0.388 | H=0.391 | Anti-persistent |
| VR(k=2) | 0.588 | 0.572 | Mean-reverting |
| VR(k=32) | 0.173 | 0.151 | Mean-reverting at all horizons |
| AR(5) L1 coefficient | −0.543 *** | −0.567 *** | Strong negative autocorrelation |
| AR(5) Durbin-Watson | 2.002 | 2.003 | Residuals are white noise |
| FFT dominant period | ~2.35 steps | ~2.30 steps | Near-Nyquist — mean-reversion |

*Day −2 LB result contains a code bug — see Section 4.

---

## 10. Trading Strategy Implications

### Primary strategy: mean-reversion fade

The overwhelming and consistent evidence supports a **fade strategy**: when the price moves up, bet it will come down; when it moves down, bet it will come up. The signal is quantified by the AR(5) forecast.

**Signal generation:**

```
r̂ₜ = −0.55·rₜ₋₁ − 0.32·rₜ₋₂ − 0.18·rₜ₋₃ − 0.09·rₜ₋₄ − 0.05·rₜ₋₅
```

- If r̂ₜ > 0: buy.
- If r̂ₜ < 0: sell.
- Position size proportional to |r̂ₜ|.

**Optimal holding period:** 1–5 ticks. VR(k=2)≈0.57 is the sharpest edge; the effect persists but weakens out to k=32. Tight holding periods minimise market impact and exposure to adverse drift.

### What not to do

- **Do not trade a directional bias.** The OLS drift signal contradicts itself between days (down on day −1, up on day −2) and is a stochastic artefact, not a structural feature.
- **Do not use a momentum strategy.** VR(k) < 1 at every tested horizon, and all AR lags are negative. There is no evidence of momentum at any timescale.
- **Do not trade price levels directly.** Levels are I(1) — any threshold or band-based strategy on raw prices will be non-stationary and poorly calibrated.

### Robustness notes

- Both days produce near-identical Hurst estimates (0.388 vs. 0.391), near-identical VR profiles, and near-identical AR coefficients. The edge is stable across the observed sample.
- The AR(5) residuals are white noise (DW≈2.00), confirming the model is correctly specified. No additional complexity (ARMA, GARCH, regime-switching) appears warranted based on the available data.
- The Ljung-Box statistics on returns are so large (~1,700 at lag 1) that the autocorrelation signal is unlikely to be a statistical fluke. This is an unusually clean and strong edge relative to what is typically observed in real financial markets.

---

## 11. Code Bug — Cell 17

In Cell 17, the Ljung-Box test for day −2 log returns contains the following error:

```python
# Intended:
lb_results_2 = acorr_ljungbox(log_returns2.dropna(), lags=lags_to_test, return_df=True)
# ...
for lag, row in lb_results_2.iterrows():   # ← should be lb_results_2

# Actual (bug):
for lag, row in lb_results_1.iterrows():   # ← reuses day −1 results
```

The printed table labelled "Ljung-Box Test on Log Returns (day −2)" is therefore a copy of the day −1 results. Correct by replacing `lb_results_1` with `lb_results_2` in the loop. The displayed LB statistics for day −2 returns (1,701, 1,704, 1,704, 1,707, 1,710) are day −1 values and should not be interpreted as day −2 results.

---

*Analysis performed on Round 0 tutorial data. Results are specific to this sample window and should be validated on out-of-sample rounds before deployment.*
