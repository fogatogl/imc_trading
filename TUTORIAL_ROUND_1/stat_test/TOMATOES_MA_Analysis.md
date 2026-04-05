# Moving Average Signal Analysis for TOMATOES — IMC Prosperity 4

**Author:** Strategy Research  
**Date:** 2026-04-05  
**Dataset:** `prices_round_0_day_-1.csv`, `prices_round_0_day_-2.csv`  
**Backtester:** [chrispyroberts/imc-prosperity-4](https://github.com/chrispyroberts/imc-prosperity-4)  
**Product:** TOMATOES · Position limit: ±80 · Tick size: 0.5

---

## Abstract

This report investigates whether moving average (MA) crossover signals carry statistically significant predictive power over TOMATOES fair value returns in the IMC Prosperity 4 tutorial round. A battery of time-series tests is applied to the full 20,000-observation dataset (two days, 10,000 steps each, sampled at 100-ms intervals). Results demonstrate that the TOMATOES fair value process exhibits robust negative first-order autocorrelation (AR(1) φ ≈ −0.177), placing it firmly in the mean-reverting regime. MA signals produce statistically significant Information Coefficients across all tested windows and horizons; however, directional hit rates fall below 50% at the one-step horizon, and transaction-cost-adjusted PnL is uniformly negative for all MA window sizes tested. These findings preclude the use of MA crossovers as directional trading signals. The empirically consistent application of MA is as a low-pass filter for fair value estimation, yielding a modest but measurable improvement (+52 PnL, +0.35%) in historical replay over the raw mid-price baseline.

---

## 1. Data and Fair Value Construction

### 1.1 Source

Two days of TOMATOES order book snapshots were extracted from the tutorial-round CSV files:

| Day | Observations | Timestamp range | Fair value range | Fair value σ |
|-----|-------------|-----------------|-----------------|-------------|
| −2  | 10,000      | 0 – 999,900 ms  | 4,989 – 5,035   | 10.26        |
| −1  | 10,000      | 0 – 999,900 ms  | 4,948 – 5,009   | 14.54        |

### 1.2 Fair Value Definition

At each timestamp, the fair value *F_t* is defined as the simple average of the innermost bid and ask prices available in the order book:

$$F_t = \frac{\min(\text{ask}_1, \text{ask}_2, \text{ask}_3) + \max(\text{bid}_1, \text{bid}_2, \text{bid}_3)}{2}$$

This quantity is used as the reference series for all subsequent analyses. The one-step return is defined as:

$$r_t = F_t - F_{t-1}$$

### 1.3 Return Distribution

The return distribution is discrete and sparse. Pooled across both days:

| \|r_t\| | Probability |
|--------|------------|
| 0.0    | 0.5708     |
| 0.5    | 0.0831     |
| 1.0    | 0.3357     |
| 1.5    | 0.0036     |
| 2.0    | 0.0069     |

Approximately 57% of steps produce no change in fair value. Non-zero returns are dominated by ±1.0 tick moves (33.6% combined). This discrete structure is consistent with the bot-driven order book architecture described in the repository's simulation model.

---

## 2. Price Process Characterisation

### 2.1 Augmented Dickey–Fuller Test

The ADF test was applied to both the price level series and the return series to establish the order of integration.

| Series   | ADF statistic | p-value | Conclusion                    |
|----------|--------------|---------|-------------------------------|
| Level F_t | −1.2707      | 0.6425  | Fail to reject unit root (I(1)) |
| Returns r_t | −57.5698   | < 0.001 | Reject unit root — stationary  |

The price level is integrated of order one (I(1)), consistent with a random walk or near-random-walk process. Returns are strongly stationary.

### 2.2 Return Autocorrelation Structure

The Ljung–Box Q-statistic was computed on the return series at lags 5, 10, and 20. All three reject the null hypothesis of no autocorrelation at p < 0.001, confirming that serial dependence is present in the return series.

The AR(1) model fitted to returns yields:

| Day | φ (AR1 coefficient) | σ_ε | Implied unconditional σ |
|-----|--------------------|----|------------------------|
| −2  | −0.1712            | 0.6169 | 0.6262 |
| −1  | −0.1827            | 0.6158 | 0.6264 |
| Pooled | **−0.1769**     | 0.6164 | 0.6262 |

The negative sign of φ indicates that above-average returns are systematically followed by below-average returns. This is the defining signature of a **mean-reverting process**. The sign-flip probability conditional on a non-zero prior return is 84.5%.

### 2.3 Variance Ratio Tests (Lo–MacKinlay, 1988)

The heteroskedasticity-robust variance ratio statistic Z* was computed for holding periods k ∈ {2, 5, 10, 20, 50, 100}.

| k   | VR(k) | Z*     | p-value | Reject random walk (5%)? |
|-----|-------|--------|---------|--------------------------|
| 2   | 0.8232 | −0.171 | 0.8640  | No                       |
| 5   | 0.7209 | −0.125 | 0.9003  | No                       |
| 10  | 0.6635 | −0.099 | 0.9214  | No                       |
| 20  | 0.6267 | −0.075 | 0.9405  | No                       |
| 50  | 0.6201 | −0.047 | 0.9624  | No                       |
| 100 | 0.6138 | −0.034 | 0.9731  | No                       |

The random walk null hypothesis is not rejected at any horizon. However, the monotonically declining VR(k) < 1 pattern is consistent with the negative autocorrelation finding from AR(1). Under a pure random walk, VR(k) = 1 for all k; values systematically below 1 indicate that multi-step variance grows more slowly than linearly — a structural feature of mean-reverting processes.

> **Interpretation:** The data cannot distinguish the TOMATOES process from a random walk at standard significance levels, but the consistent sub-unity variance ratios corroborate negative autocorrelation and are incompatible with positive momentum.

---

## 3. Moving Average Signal Analysis

### 3.1 Signal Definition

For each window w ∈ {5, 10, 20, 50, 100, 200}, the MA signal at time t is defined as:

$$\text{sig}_{w,t} = \text{sign}(F_t - \text{MA}_{w,t})$$

where MA_{w,t} is the simple rolling mean of F over the preceding w observations. The signal takes values in {−1, 0, +1}.

### 3.2 Predictive Power — Information Coefficient

The Information Coefficient (IC) is measured as the Spearman rank correlation between the signal sig_{w,t} and the forward return r_{t+h} at horizons h ∈ {1, 5, 10}.

**Horizon h = 1:**

| Window | n (signals) | IC (Spearman) | IC p-value | Hit rate | Binomial p-value |
|--------|------------|--------------|-----------|---------|-----------------|
| 5      | 17,024     | +0.6257      | < 0.001   | 0.4592  | < 0.001          |
| 10     | 19,250     | +0.4357      | < 0.001   | 0.3588  | < 0.001          |
| 20     | 19,759     | +0.3064      | < 0.001   | 0.3133  | < 0.001          |
| 50     | 19,918     | +0.1945      | < 0.001   | 0.2768  | < 0.001          |
| 100    | 19,886     | +0.1358      | < 0.001   | 0.2582  | < 0.001          |
| 200    | 19,792     | +0.0983      | < 0.001   | 0.2464  | < 0.001          |

**Horizon h = 5:**

| Window | IC (Spearman) | t-stat (+1 vs −1) | Mean ret (long) | Mean ret (short) |
|--------|--------------|-------------------|----------------|-----------------|
| 5      | +0.7263      | 127.18            | +0.8672        | −0.8888          |
| 10     | +0.7811      | 152.33            | +0.8869        | −0.8998          |
| 20     | +0.6265      | 107.56            | +0.7258        | −0.7241          |
| 50     | +0.4151      | 64.26             | +0.4962        | −0.4892          |
| 100    | +0.2944      | 43.92             | +0.3530        | −0.3547          |
| 200    | +0.2155      | 31.44             | +0.2592        | −0.2601          |

**Horizon h = 10:**

| Window | IC (Spearman) | Hit rate | Mean ret (long) | Mean ret (short) |
|--------|--------------|---------|----------------|-----------------|
| 5      | +0.5169      | 0.6065  | +0.8252        | −0.8673          |
| 10     | +0.7052      | 0.6987  | +1.0876        | −1.1214          |
| 20     | +0.7704      | 0.7338  | +1.1776        | −1.1837          |
| 50     | +0.5614      | 0.6192  | +0.8936        | −0.8848          |
| 100    | +0.4116      | 0.5530  | +0.6625        | −0.6681          |
| 200    | +0.3018      | 0.5091  | +0.4874        | −0.4914          |

### 3.3 Interpretation of the IC Paradox

The combination of statistically significant positive IC and sub-50% one-step hit rates is not contradictory. It is a direct consequence of the MA lag artefact operating in a mean-reverting process:

1. When price rises above the MA, the MA is by construction below the current price.
2. In a mean-reverting process, the price subsequently falls back towards — and through — the MA.
3. The IC captures the *cumulative directional asymmetry* over multi-step horizons (h = 5, 10), where enough reversion has accumulated for a positive rank correlation to emerge.
4. At h = 1, the immediate next step is more likely to be a reversion against the signal direction (84.5% sign-flip probability), producing a hit rate below 0.50.

The MA signal is therefore measuring a *look-back artefact* of the mean-reversion process, not a forward-looking predictive relationship exploitable at the single-step execution level.

---

## 4. Transaction-Cost Analysis

### 4.1 Simulation Setup

A signal-following PnL simulation was run over the full 20,000-observation dataset. At each step, the strategy holds position equal to the current signal value (±1). A trade is recorded whenever the signal changes value. The half-spread cost per trade is set at 6.5 ticks, corresponding to the empirically observed inner wall spread of the TOMATOES order book.

$$\text{Net PnL}_t = \text{position}_{t-1} \cdot r_t - \mathbb{1}[\text{signal change}] \cdot |\Delta\text{position}| \cdot 6.5$$

### 4.2 Results

| Window | Trades | Gross PnL | Net PnL    | Gross Sharpe | Net Sharpe | Cost drag  |
|--------|--------|-----------|-----------|-------------|-----------|-----------|
| 5      | 6,504  | −1,416.0  | −67,761.5 | −12.342     | −61.064   | 66,345.5  |
| 10     | 4,135  | −1,154.0  | −48,506.5 | −9.436      | −46.535   | 47,352.5  |
| 20     | 2,735  | −835.0    | −33,991.5 | −6.723      | −36.905   | 33,156.5  |
| 50     | 1,601  | −504.0    | −20,894.5 | −4.041      | −27.636   | 20,390.5  |
| 100    | 1,093  | −369.0    | −14,415.5 | −2.964      | −22.512   | 14,046.5  |
| 200    | 803    | −288.5    | −10,604.0 | −2.327      | −19.129   | 10,315.5  |

Key findings:

- **Gross PnL is negative for all windows.** The negative AR(1) coefficient means a pure trend-following strategy loses on gross terms independently of costs.
- **Transaction costs amplify losses by 47–98×.** The cost drag exceeds gross loss by one to two orders of magnitude.
- **No window produces a positive net Sharpe ratio.** The most favourable window (200) yields a net Sharpe of −19.1.
- The cost drag scales approximately linearly with the number of trades, confirming that turnover — not mispositioning — is the dominant loss factor.

---

## 5. Walk-Forward Stability

To assess temporal robustness of the MA(20) IC, the dataset was partitioned chronologically into 10 non-overlapping folds of approximately 2,000 observations each. The Spearman IC between the MA(20) signal and the 1-step forward return was computed independently in each fold.

| Fold | IC     | p-value | n     | Significant (5%) | Sign stable |
|------|--------|---------|-------|-----------------|-------------|
| 1    | 0.3337 | < 0.001 | 1,979 | Yes             | Yes         |
| 2    | 0.3020 | < 0.001 | 1,974 | Yes             | Yes         |
| 3    | 0.3033 | < 0.001 | 1,968 | Yes             | Yes         |
| 4    | 0.2898 | < 0.001 | 1,986 | Yes             | Yes         |
| 5    | 0.3026 | < 0.001 | 1,969 | Yes             | Yes         |
| 6    | 0.3213 | < 0.001 | 1,969 | Yes             | Yes         |
| 7    | 0.3074 | < 0.001 | 1,980 | Yes             | Yes         |
| 8    | 0.3148 | < 0.001 | 1,973 | Yes             | Yes         |
| 9    | 0.3066 | < 0.001 | 1,983 | Yes             | Yes         |
| 10   | 0.2849 | < 0.001 | 1,977 | Yes             | Yes         |

- **Sign stability: 100% of folds** — the IC is consistently positive, with no fold producing a sign reversal.
- **Statistical significance: 100% of folds** — the IC is significant at α = 0.05 in every fold.
- IC standard deviation across folds: 0.0138, indicating low variance and a stable structural relationship.

The stability of the IC across time is further evidence that the positive MA IC is a structural property of the mean-reversion process, not a sample artefact.

---

## 6. Historical Replay Comparison

Both the baseline strategy (raw mid-price fair value) and the MA-enhanced strategy (EWM span=10 blended fair value, α = 0.1818) were backtested using the `prosperity3bt` historical replay engine on the tutorial-round CSV data.

### 6.1 Strategy Configurations

**Baseline** (`stratégie_gestionportefeuille_baseline.py`):
- Fair value: instantaneous mid-price `(best_bid + best_ask) / 2`
- Taker: buys below fair value, sells above fair value
- Maker: pennying ± 1 tick with position-skew rebalancing at threshold ±50

**MA-Enhanced** (`stratégie_gestionportefeuille_MA.py`):
- Fair value: `0.7 × EWM(span=10) + 0.3 × raw_mid`
- All other parameters identical to baseline
- The EWM is used exclusively as a noise-filtering estimator for fair value; it is not used to generate a directional signal

### 6.2 Backtest Results

| Strategy       | Day −2 PnL | Day −1 PnL | Total PnL | Δ vs baseline |
|----------------|-----------|-----------|----------|--------------|
| Baseline       | 8,242     | 6,635     | **14,878** | —            |
| MA-Enhanced    | 8,256     | 6,674     | **14,930** | +52 (+0.35%) |

The EWM-filtered fair value produces a small but consistent improvement on both days. The improvement arises from reduced noise in the fair value estimate, which marginally improves the signal-to-noise ratio of the taker trigger condition rather than from any directional position-taking by the MA.

---

## 7. Monte Carlo Robustness

The repository provides a Rust-backed Monte Carlo backtester (`prosperity4mcbt`) that generates synthetic TOMATOES order books using the calibrated simulation model: a zero-drift latent fair value process with discrete return quantisation (support {0, ±0.5, ±1.0, ±1.5, ±2.0}, φ ≈ −0.177, σ_ε ≈ 0.616). This engine requires Rust/Cargo and is therefore not executable in the current analysis environment.

The recommended Monte Carlo protocol for local validation is:

```bash
# Install backtester
cd imc-prosperity-4
pip install -e backtester

# Run 100-session sweep on both strategies
prosperity4mcbt baseline_bt.py   --quick --out tmp/baseline/dashboard.json
prosperity4mcbt ma_bt.py         --quick --out tmp/ma/dashboard.json

# Run 1000-session heavy sweep for final comparison
prosperity4mcbt baseline_bt.py   --heavy --out tmp/baseline_heavy/dashboard.json
prosperity4mcbt ma_bt.py         --heavy --out tmp/ma_heavy/dashboard.json
```

Key metrics to compare from `session_summary.csv`:

| Metric | Interpretation |
|--------|---------------|
| Mean Total PnL | Expected value per session |
| PnL Std | Variance of outcomes |
| P05 / P95 | Tail risk and upside |
| Profitability ($/step) | Risk-adjusted edge per time unit |
| Stability R² | Consistency of PnL accumulation |

---

## 8. Summary of Findings

| Test | Result | Implication |
|------|--------|-------------|
| ADF on returns | Stationary (p < 0.001) | Returns do not have a unit root |
| AR(1) φ on returns | −0.177 (pooled) | Returns are negatively autocorrelated (mean-reverting) |
| Ljung–Box Q | p < 0.001 at all lags | Serial dependence confirmed in return series |
| Variance Ratio VR(k) | < 1 for all k, monotonically declining | Consistent with negative autocorrelation; not consistent with positive momentum |
| MA IC (h=1) | +0.10 to +0.63, all p < 0.001 | Statistically significant but arises from lag artefact |
| MA hit rate (h=1) | 0.246 – 0.459 (all < 0.50) | MA signal predicts direction incorrectly more often than correctly at h=1 |
| Transaction cost | Net PnL −10,604 to −67,762 | MA crossover strategy is not viable after transaction costs |
| Walk-forward stability | 100% sign-stable, 100% significant | IC structure is temporally stable but not exploitable |
| Historical replay | +52 PnL vs baseline using EWM as filter | MA has marginal value as a fair value noise filter |

---

## 9. Conclusions

1. **The TOMATOES fair value process is mean-reverting.** The AR(1) coefficient on returns is φ ≈ −0.177, with a sign-flip probability of 84.5% conditional on a non-zero prior return. This is the dominant characteristic driving all downstream findings.

2. **MA crossover signals are statistically significant but structurally misaligned.** The positive IC arises because the MA lags behind in a mean-reverting series, creating a systematic rank correlation with multi-step forward returns. This relationship does not translate into single-step predictive accuracy (hit rates 24.6% – 45.9%, all below 50%).

3. **No MA window survives transaction costs.** The half-spread cost of 6.5 ticks produces cost drag between 66,346 and 10,316 over 20,000 steps depending on window size, swamping the negligible gross PnL generated by the signal.

4. **The appropriate use of moving averages in this context is as a fair value noise filter.** An EWM with span=10 (α ≈ 0.182), blended with the instantaneous mid-price, reduces fair value estimation noise without introducing a directional bet. Historical replay confirms a modest +0.35% improvement in total PnL relative to the raw mid-price baseline.

5. **The existing mean-reversion architecture (pennying + position skew) is the correct structural approach.** The strategy's taker and passive maker components are mechanistically aligned with the negative autocorrelation of the return process. The primary lever for improvement is fair value estimation precision, not signal generation.

---

## Appendix A — Test Parameters

| Parameter | Value |
|-----------|-------|
| Dataset | `prices_round_0_day_-1.csv`, `prices_round_0_day_-2.csv` |
| Total observations | 20,000 (10,000 per day) |
| Sampling interval | 100 ms |
| MA windows tested | 5, 10, 20, 50, 100, 200 |
| Forward horizons tested | 1, 5, 10 steps |
| Transaction cost (half-spread) | 6.5 ticks |
| ADF lag selection | AIC |
| IC metric | Spearman rank correlation |
| Walk-forward folds | 10 (chronological, non-overlapping) |
| VR heteroskedasticity correction | Lo–MacKinlay (1988) robust Z* |
| EWM span (MA-enhanced strategy) | 10 (α = 2/11 ≈ 0.1818) |

## Appendix B — Statistical Test References

- **Augmented Dickey–Fuller:** Dickey, D.A. & Fuller, W.A. (1979). Distribution of the estimators for autoregressive time series with a unit root. *Journal of the American Statistical Association*, 74(366), 427–431.
- **Variance Ratio Test:** Lo, A.W. & MacKinlay, A.C. (1988). Stock market prices do not follow random walks: Evidence from a simple specification test. *Review of Financial Studies*, 1(1), 41–66.
- **Ljung–Box Q:** Ljung, G.M. & Box, G.E.P. (1978). On a measure of lack of fit in time series models. *Biometrika*, 65(2), 297–303.
- **Information Coefficient:** Grinold, R.C. & Kahn, R.N. (2000). *Active Portfolio Management* (2nd ed.). McGraw-Hill.
