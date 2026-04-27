# Research Plan — VEV Voucher Options Strategy

## Context

- **Underlying:** VELVETFRUIT_EXTRACT (spot ≈ 5,250)
- **Vouchers:** VEV_4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500 — European calls; strike = number in symbol
- **Current baseline:** 58,122 P/L. Known issues: VEV_5300 hits position limit twice with whipsaw between, VEV_5200 drifts to +75% long, mid-strikes (4500/5000/5100) nearly dormant
- **Advisor's framing:** Three sequential questions
  1. What is the market implying? → compute IV
  2. Where does the structure break? → find outliers
  3. How much to commit? → size by conviction, not hope

---

## Phase 1 — Build the IV Infrastructure

### 1.1 Black-Scholes pricing (calls)
```
C = S·N(d1) − K·exp(−rT)·N(d2)
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d2 = d1 − σ·√T
```
Inputs:
- `S` = mid-price of VELVETFRUIT_EXTRACT
- `K` = voucher strike
- `T` = time to expiry (confirm from competition rules — likely fraction of round elapsed)
- `r` = 0 (typical for competition; verify)
- `σ` = volatility (the unknown we solve for)

### 1.2 Implied Volatility solver
- **Primary:** Newton-Raphson using vega as derivative
- **Fallback:** Brent / bisection on `[1e-4, 5.0]` when Newton diverges
- **Skip conditions:** market price ≤ intrinsic, market price = floor (1), or vega < epsilon
- **Sanity gate:** discard IV outside `[0.001, 3.0]`

### 1.3 Moneyness definition
Use **log-moneyness**: `m = ln(K / S)`
- Symmetric around ATM
- Stable under spot drift
- Optionally normalize: `m_norm = ln(K/S) / (σ_atm · √T)` for cross-time comparability

### 1.4 Greeks (needed downstream)
- `delta = N(d1)` — for hedging
- `vega = S·√T·φ(d1)` — for converting IV residuals to dollar P/L and for sizing
- `gamma = φ(d1) / (S·σ·√T)` — for risk budget

---

## Phase 2 — Map the IV Surface

### 2.1 Per-tick snapshot
For each timestamp build a row per voucher: `{K, mid, moneyness, IV, vega, delta}`.

### 2.2 Visualize IV vs. moneyness
Expected shapes:
- **Smile** — IV elevated at both wings (fat tails)
- **Skew** — monotonic slope (one tail priced richer)
- **Smirk** — asymmetric hybrid

The shape itself is the signal of what the market expects. Don't assume; measure.

### 2.3 Fit a reference curve
Quadratic in log-moneyness is sufficient for 10 strikes:
```
σ_fit(m) = a + b·m + c·m²
```
Fit with weighted least squares — weight by vega (or by 1/spread²) so deep OTM points with thin liquidity don't dominate.

### 2.4 Track the surface over time
- Save `(a, b, c)` per timestamp → time series of curve parameters
- Detect regime shifts (rolling z-score on each parameter)
- Cross-reference regime breaks with VEV_5300's whipsaw timestamp (~1,000,000) — likely a real signal the previous strategy missed

---

## Phase 3 — Identify Mispricing

### 3.1 Per-voucher residual
```
residual_i = IV_market_i − σ_fit(m_i)
```
Standardize: `z_i = residual_i / std(residuals)`.

### 3.2 Convert to dollars
```
$_mispricing_i ≈ residual_i × vega_i
```
This tells you how much you expect to make per contract if IV reverts to the fitted curve.

### 3.3 Trade decision rules
| Condition | Action |
|---|---|
| `z_i > +threshold` (IV too high) | **Sell** the voucher |
| `z_i < −threshold` (IV too low) | **Buy** the voucher |
| `|z_i| < threshold` | Stay put — no edge |

Start with `threshold = 1.0`, then tune via walk-forward backtest.

### 3.4 Validate the signal before trading
- **Persistence:** same residual sign across N consecutive ticks
- **Mean-reversion check:** historically, does the residual shrink within K ticks?
- **Model breakdown guard:** if a voucher is *always* an outlier, the model is wrong — exclude it or reweight the fit

---

## Phase 4 — Volume / Position Sizing

### 4.1 Base size from signal strength
```
size_i ∝ z_i / vega_i      (vega-neutralized notional)
```
Stronger signal → larger position, but caps apply.

### 4.2 Hard caps (apply in this order)
1. Per-symbol position limit (competition rule)
2. Total portfolio vega budget — limits exposure to a single shock to the IV surface
3. Total portfolio gamma budget — protects against fast spot moves; low-priced options burn this fast
4. Net delta budget after hedging — keep close to zero unless taking a directional view

### 4.3 Conviction discount
Multiply raw size by `C ∈ [0, 1]`:
- `C = 1.0` — persistent signal, low fit residuals overall, structurally clean
- `C = 0.5` — noisy or fresh signal, fit RMS elevated
- `C = 0.0` — fit residuals are bimodal (model is broken; don't trade)

### 4.4 Inventory skew (the missing piece in the current strategy)
The VEV_5200 drift to +75% is a textbook symptom of no inventory feedback. Fix:
```
quote_bid = fair − half_spread − k·position
quote_ask = fair + half_spread − k·position
```
With `k > 0`, inventory mean-reverts to zero on its own.

### 4.5 Worst-case loss check
Before entering, compute the loss if residual moves to the *opposite* extreme:
```
worst_case ≈ 2 · |residual| · vega · size
```
Sum across portfolio ≤ pre-set damage budget. If it isn't, cut size.

---

## Phase 5 — Risk Controls & Execution

### 5.1 Delta hedging
Hedge net delta with VELVETFRUIT_EXTRACT.
- VEV_4000 (deep ITM): delta ≈ 1.0 → hedge ~1:1
- ATM strikes (5200/5300): delta ≈ 0.5
- OTM strikes: delta < 0.3
Rebalance each tick if cumulative delta exceeds threshold.

### 5.2 Put-call parity (if puts exist)
```
C − P = S − K·exp(−rT)
```
Any deviation = riskless arbitrage; size into the limit.

### 5.3 Floor-priced strikes (VEV_6000, VEV_6500)
Pinned at price 1. If shorting is permitted and your IV model implies value < 1, short to collect premium. Currently leaving this on the table.

### 5.4 Diagnostic logging per fill
Record: timestamp, symbol, side, qty, fill price, IV at fill, residual at fill, predicted P/L, realized P/L. This data trains the threshold tuning loop.

---

## Phase 6 — Validation & Iteration

### 6.1 Walk-forward backtest
Never fit the IV curve on data you then trade against. Rolling window: fit on past N ticks, trade the next M, advance.

### 6.2 Metrics per voucher
- Sharpe ratio
- Hit rate of residual signals (sign correct on next K ticks)
- Mean P/L per unit of residual
- Max drawdown
- Correlation of voucher P/Ls (avoid hidden concentration)

### 6.3 Failure-mode tests (regression suite)
- VEV_5200 drift: does inventory skew now cap position < 30%?
- VEV_5300 whipsaw: does persistence filter prevent re-entry within K ticks of a flush?
- Dormant strikes (4500/5000/5100): does the residual signal now generate fills?
- Floor strikes: are short trades being placed when justified?

---

## Implementation Checklist (for Claude Code)

1. `bs_price(S, K, T, r, sigma)` — call price
2. `bs_vega(S, K, T, r, sigma)`, `bs_delta(...)`, `bs_gamma(...)`
3. `implied_vol(price, S, K, T, r)` — Newton + Brent fallback
4. `log_moneyness(K, S)`
5. `fit_iv_curve(strikes, ivs, vegas)` → `(a, b, c)`
6. `residual_signal(iv, fit, std)` → z-score
7. `position_sizer(z, vega, conviction, caps)` → target qty
8. `inventory_skew_quote(fair, spread, position, k)` → (bid, ask)
9. `delta_hedger(option_positions, underlying_pos)` → hedge order
10. `walk_forward_backtest(data, window_n, trade_m)` — validation harness
11. Per-fill diagnostic logger writing to CSV

---

## Open Questions to Resolve First

1. **Time to expiry T** — what's the convention? Round-end expiry? Confirm from competition rules.
2. **Risk-free rate** — assume 0 unless stated otherwise.
3. **Are puts available?** — if yes, put-call parity is the cleanest arb.
4. **Are short positions allowed on options?** — required for selling rich vol or floor strikes.
5. **Position limits per voucher** — needed for sizing caps.

Resolve these before writing the first line of pricing code.
