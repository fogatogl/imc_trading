# Round 3 Strategy — Long-Gamma Vol Carry on VE Vouchers

**Version:** draft v1, 2026-04-24.
**Companion:** [`round3_analysis.ipynb`](round3_analysis.ipynb), [`round3_findings.md`](round3_findings.md).
**Status:** pre-backtest. Numbers grounded in corrected historical analysis; live fills and hedging cost need backtest validation.

---

## 1. Executive summary

The corrected analysis shows **implied vol systematically below realised vol** on Velvetfruit Extract options, with a tradable edge of ~9 vol-pts after microstructure correction:

| Quantity | Value |
|----------|------:|
| $\sigma_\text{implied}$ (ATM, smile level $c$) | **0.234** |
| $\sigma_\text{realised}$ (two-scale asymptote) | **0.325** |
| Edge in vol space | **+0.091** |
| Edge in variance space | $\sigma_r^2 - \sigma_i^2$ = **+0.051** |
| Pathwise-verified gamma P&L per 1 contract per 3 days | 6–17 SeaShells, peaks at K=5200, 5300 |

**The strategy:** hold a long-gamma basket of ATM Velvetfruit vouchers, continuously delta-hedged with VE, sized to the 200-contract VE limit. No underlying mean-reversion signal (bid-ask bounce only). No smile-curvature signal (unstable across TTE). Core edge is the $\sigma_r > \sigma_i$ carry.

**Expected P&L:** ~3 000 SeaShells/day gross on the recommended basket, before hedging costs. Net target after execution costs: **~2 000 SeaShells/day**.

---

## 2. What the corrected data rules out

Before writing rules, let's state clearly what is *not* tradable:

- **Underlying VE mean-reversion.** Lag-1 AC = −0.159 at tick scale, but decays to ~0 at subsampling dt=10 ([`fix-ac-multi-code`](round3/round3_analysis.ipynb)). Textbook bid-ask bounce. No EMA / mean-reversion overlay on VE.
- **Smile curvature.** Extrapolated $a$ flips sign across TTE 8→7→6 days; live 5d value is noise. Do **not** price wings with the parabola; use the **level $c = 0.234$** as a constant live baseline.
- **Far-OTM vouchers (VEV_6000, VEV_6500).** Floor-pegged at 0.5 tick; solver correctly returns NaN. Do not quote, do not hold.
- **Deep-ITM vouchers (VEV_4000, VEV_4500).** At intrinsic; zero time value to scalp. Do not trade.
- **Thin-priced tail (VEV_5500).** Price ≈ 8.5, so delta-hedged P&L is dominated by 0.5-tick bounce on the option side. Use only at reduced weight or skip.

---

## 3. Live greeks snapshot (T=5d, S=5250, σ=0.234)

| Strike | Delta | Gamma | Vega | Mid at t=0 | Pathwise P&L / contract / 3d (hist) |
|-------:|------:|------:|-----:|-----------:|------------------------------------:|
| 5000 | 0.964 | 0.00055 | 48.9 | ~250 | 6.8 |
| 5100 | 0.858 | 0.00156 | 138.0 | ~170 | 11.5 |
| **5200** | **0.642** | **0.00260** | **229.5** | ~101 | **17.5** |
| **5300** | **0.370** | **0.00263** | **232.0** | ~53 | **16.1** |
| 5400 | 0.155 | 0.00166 | 146.5 | ~23 | 10.0 |
| 5500 | 0.046 | 0.00067 | 59.3 | ~8.5 | 6.4 |

The two best strikes for gamma scalping are **VEV_5200 and VEV_5300** — highest gamma, highest vega, and (non-coincidentally) highest historical pathwise P&L per contract.

---

## 4. Strategy architecture — three layers

### Layer 1 (core) — Long-gamma carry, delta-hedged

Buy ATM vouchers, short $\Delta \cdot S$ of VE continuously. Captures $\tfrac12 \Gamma S^2 (\sigma_r^2 - \sigma_i^2) \cdot dt$ per tick.

**Which strikes.** 5200 + 5300 (primary), 5400 (supplementary if delta budget allows).

**Why not all six.** Delta budget is capped by the 200-contract VE position limit. A 300-contract position in every strike would require ≈ 900 VE short, 4.5× the limit. We must be selective.

**LP sizing (delta budget = 180 VE to leave safety margin against 200 limit).**

Rank strikes by P&L / |delta| ratio and fill greedy:

| Strike | N (contracts) | |Δ|·N | Cumulative |Δ| budget | Contribution to P&L / 3d |
|-------:|--------------:|------:|----------------------:|-------------------------:|
| 5300 | 300 | 111.0 | 111.0 | 4 830 |
| 5400 | 300 | 46.5 | 157.5 | 3 000 |
| 5200 | **35** | 22.5 | **180.0** | 613 |
| — | | | | **= 8 443 total** |

> **Recommended initial allocation: N_5300 = 300, N_5400 = 300, N_5200 = 35.**
> Expected gross P&L ≈ **8 400 SeaShells per 3 days** ≈ **2 800 / day** before hedging cost.

**Simpler baseline (if you prefer equal-weight instead of LP):**
N_5200 = N_5300 = 160, N_5400 = 0 → |Δ_port| ≈ 162 → P&L ≈ (17.5 + 16.1) × 160 = 5 376 / 3d ≈ 1 800 / day. Less edge, more robust.

### Layer 2 (overlay) — IV-residual mean-reversion

The smile **level** $c ≈ 0.234$ is stable across days. Intra-day, $v_t - 0.234$ has std ≈ **0.007** vol-pts. When the whole surface goes rich/cheap together (common-factor move visible in IV-deviation plot), we can shade Layer 1 sizing:

**Rule:**

$$
\bar{v}_\text{dev}(t) = \frac{1}{4} \sum_{K \in \{5100, 5200, 5300, 5400\}} \bigl(v_{K,t} - 0.234\bigr)
$$

- If $\bar{v}_\text{dev} > +0.007$ (surface 1σ rich): **reduce** Layer 1 position by 30% (sell some calls, de-hedge).
- If $\bar{v}_\text{dev} < -0.007$ (surface 1σ cheap): **hold at max** (don't add since Layer 1 already peaked at delta budget).
- Between ±0.007: baseline Layer 1 sizing.

This uses Layer 2 as a **volatility regime filter** on top of Layer 1 — it reduces long-gamma exposure when the market is already paying up for vol, leaving room to capture the mean-reversion back to 0.234.

### Layer 3 — Do nothing on VE directly

No standalone underlying position. VE is hedge instrument only.

---

## 5. Execution rules

### 5.1 Entry

At the start of the round (t=0), open positions to the target allocation in stages:
1. Buy N contracts of each target voucher at the current best ask (or posted 1 tick above the current mid to catch market-maker fills).
2. Immediately after each fill, rebalance VE short to target $\Delta_\text{port} = 0$.
3. Do **not** wait for a "better entry." The edge is a carry, so every tick you're not in position is edge lost.

### 5.2 Hedging band

Continuous rebalancing crosses the VE spread 30 000+ times → kills the edge. Use a threshold:

- Compute $\Delta_\text{port}(t) = \sum_K N_K \cdot \Delta_K(S_t, T_t, \hat\sigma)$ where $\hat\sigma = 0.234$ is fixed (don't chase live IV noise).
- **Rebalance VE short only when $|\Delta_\text{port}(t)| > 3$.**
- When triggered, trade VE to bring $\Delta_\text{port}$ back to 0.

Rationale: gamma rate at peak strikes is ~0.0026 × 300 contracts × 2 = 1.56 delta change per unit S. A 2 SeaShell VE move = ~3 delta drift. So we rebalance roughly once per 2-SeaShell VE move, ~every 20–50 ticks. Estimated 600–1 500 rebalances over 30 k ticks × ~1.5 SeaShell per rebalance = **900 – 2 200 SeaShells total hedge cost** over 3 days.

### 5.3 Position-limit safety

- Voucher limit: 300 each. Our largest single-leg is 300. **Watch for fills overshooting** — size orders to leave a buffer.
- VE limit: 200 each direction. Our target short is ~180 with buffer to 200. If $\Delta_\text{port}$ spikes beyond −200 VE reachable, **shrink the voucher book** by selling the highest-delta voucher first.

### 5.4 Layer 2 rebalance

Recompute $\bar{v}_\text{dev}$ every 50 ticks (not every tick — it's slow-moving). When crossing a threshold, adjust voucher position by ±30%:
- Rich trigger: sell 30% of each voucher, re-hedge VE long to match (effectively closing a fraction of the book).
- Return to neutral: buy back the 30% when $\bar{v}_\text{dev}$ crosses 0.

### 5.5 End-of-day / end-of-round

Options expire at the end of day 7 (live day 3 = 2 days remaining at round end). **Do not hold through expiry without a flat book** — gamma P&L decays with √T and theta grows; the carry edge shrinks to zero by expiry.

Plan:
- End of live day 1 (T=4d): continue.
- End of live day 2 (T=3d): begin reducing position; target 50% of Layer 1 notional.
- End of live day 3 (T=2d): flatten all vouchers, flatten VE.

(In-sample data covers TTE 8d → 6d only, so we cannot validate T<5d behaviour. Flatten defensively.)

---

## 6. Expected P&L and risk budget

### 6.1 Gross expected P&L per 3 live days

From historical pathwise simulation, scaled to the recommended allocation:

$$
\text{Gross} \approx 300 \cdot 16.1 + 300 \cdot 10.0 + 35 \cdot 17.5 \approx 8\,440 \text{ SeaShells / 3 days}
$$

### 6.2 Hedging cost (estimate)

Per §5.2, ~900–2 200 SeaShells over 3 days.

### 6.3 Net expected P&L

**Target: 6 000 – 7 500 SeaShells over 3 live days ≈ 2 000 – 2 500 / day.**

### 6.4 Variance and drawdown

Pathwise per-step std per contract (from notebook): ~0.4–0.7 SeaShells. With combined position std ≈ √(300²·0.42² + 300²·0.27² + 35²·0.52²) × √(29 999 steps) ≈ a few hundred SeaShells per 3 days. Sharpe should be high if edge is real. But if the realised-vs-implied edge is *smaller* than measured (due to remaining noise), we pay pure theta and lose ~1/2 of the expected P&L.

**Risk ceiling.** If cumulative P&L at end of live day 1 is below −500 SeaShells, **pause new entries** and hold the existing book. If below −1 500 by end of day 2, **exit the strategy entirely** — the edge is not behaving as in-sample.

---

## 7. Monitoring & guardrails (log at every tick)

| Metric | Why | Alert threshold |
|--------|-----|-----------------|
| $\Delta_\text{port}$ | Hedge error | > 10 in either direction |
| Voucher positions by strike | Avoid limit breach | ≥ 290 on any strike |
| VE position | Avoid limit breach | ≥ 180 short |
| $\hat v_t$ (live smile level, refit hourly) | Smile drift | > 0.24 or < 0.22 |
| $\bar v_\text{dev}$ | Layer 2 signal | crossings of ±0.007 |
| Realised vol (rolling 1 000 ticks, dt=10 subsample) | Realised-vol regime | < 0.28 — edge evaporating |
| Cum P&L | Strategy validity | see §6.4 |

---

## 8. Implementation checklist

- [ ] Implement BS pricer and greek calculator in the trader class (use the same `bs_call` / `bs_greeks` as notebook).
- [ ] Hard-code `SIGMA_BASELINE = 0.234`, `ATM_STRIKES = [5200, 5300, 5400]`, `N_TARGET = {5200: 35, 5300: 300, 5400: 300}`.
- [ ] Entry logic: at each `run()` call, if voucher position != target, submit orders to close the gap.
- [ ] Delta calculation: vectorised over positions, refresh every tick with current `S` and `T`.
- [ ] Hedge band: if `|Δ_port| > 3`, submit VE order to bring it to 0.
- [ ] Layer 2 (optional for v1): compute `mean(IV - 0.234)` every 50 ticks, scale voucher position by 0.7 when > +0.007.
- [ ] Defensive exit: flatten at the last 500 ticks of live day 3.
- [ ] Telemetry: log all metrics in §7 to the lambda log for post-run analysis.

---

## 9. Next research before submission

1. **Backtest the strategy spec** on 3 historical days. Verify P&L ≥ 5 000 SeaShells before live.
2. **Two-scale hedge-cost model.** Add VE spread crossing to the pathwise simulation; pick the optimal rebalance threshold (currently guessed at 3 VE drift).
3. **Live smile refit.** Every N ticks, re-solve IV from the 4 ATM vouchers and update `SIGMA_BASELINE`. Test whether online refitting improves or hurts vs. constant 0.234.
4. **Layer 2 ablation.** Backtest with and without Layer 2. If it adds <5% to net P&L, drop it — simpler is more robust with only 3 days of in-sample data.
5. **Hydrogel.** Separate strategy; not covered here.

---

## 10. TL;DR

- **Long gamma carry** on VEV_5300 (300) + VEV_5400 (300) + VEV_5200 (35 to fill delta budget).
- **Delta-hedge with VE**, rebalance band = 3 VE drift.
- **Use σ = 0.234 fixed** for deltas (smile level is stable; curvature is noise).
- **Expected net: ~2 000 SeaShells/day** over 3 live days.
- **Hard exit** at end of live day 3 (T=2d) — don't hold through expiry.
- **Kill-switch** if cum P&L < −1 500 at end of day 2.
