# IMC Prosperity 4 — Backtest Results Summary

**Final P/L: 58,122**

## 1. Product Universe (inferred structure)

| Symbol | Type | Notes |
|---|---|---|
| HYDROGEL_PACK | Standalone asset | Mean-reverting around 10,000 |
| VELVETFRUIT_EXTRACT | Underlying asset | Mean-reverting around 5,250 |
| VEV_4000 … VEV_6500 | Call options on VELVETFRUIT_EXTRACT | Strike = number in symbol |

**Key inference:** VEV_XXXX prices closely match max(VELVETFRUIT_EXTRACT − strike, 1), confirming these are calls on VELVETFRUIT_EXTRACT. VEV_6000 and VEV_6500 are pinned at price 1 (floor), deep OTM.

## 2. Price Behavior (per product)

| Symbol | Price Range | Center | Intrinsic vs Underlying (~5,250) | Trading Activity |
|---|---|---|---|---|
| HYDROGEL_PACK | 9,900–10,080 | ~10,000 | n/a | High — many buys & sells |
| VELVETFRUIT_EXTRACT | 5,180–5,290 | ~5,250 | n/a | Very high — dense fills |
| VEV_4000 | 1,180–1,295 | ~1,240 | Deep ITM (intr. ~1,250) | High — balanced |
| VEV_4500 | 685–790 | ~740 | ITM (intr. ~750) | Very low (~1 fill) |
| VEV_5000 | 205–285 | ~245 | ITM (intr. ~250) | Very low (~1 fill) |
| VEV_5100 | 125–200 | ~165 | Slightly ITM (intr. ~150 + TV) | Very low (~1 fill) |
| VEV_5200 | 65–122 | ~90 | Near ATM (intr. ~50 + TV) | Buy-heavy (green dominant) |
| VEV_5300 | 30–65 | ~47 | Slightly OTM (all TV) | Mixed buys & sells |
| VEV_5400 | 7–27 | ~16 | OTM | Mostly mid-price obs, few buys |
| VEV_5500 | 2–13 | ~6.5 | OTM | Sparse fills |
| VEV_6000 | flat at 1 | 1 | Deep OTM (floor) | None |
| VEV_6500 | flat at 1 | 1 | Deep OTM (floor) | None |

## 3. P/L Attribution (qualitative, from chart)

- **Total P/L curve:** Steady upward drift from 0 to ~25k mid-run, peaks above 25k near end. Final reported total = **58,122** (legend shows ~25k visible portion; total includes off-chart components).
- **Top contributors (positive):** HYDROGEL_PACK (consistent positive drift), VEV_4000 (modest positive).
- **Near-zero contributors:** Most other VEV strikes hover around 0 P/L.
- **Negative or volatile:** VEV_5200 and VEV_5300 show drawdowns coinciding with position swings.

## 4. Position Usage (% of position limit)

| Symbol | Behavior | Concern |
|---|---|---|
| HYDROGEL_PACK | Tight near 0 | Healthy market-making |
| VELVETFRUIT_EXTRACT | Small osc. around 0 (±10%) | Healthy |
| VEV_4500 / VEV_5000 / VEV_5500 / VEV_6000 | Near 0 throughout | Inactive / minimal exposure |
| VEV_5200 | Climbs steadily to ~+75% long by end | **Persistent long bias — directional drift** |
| VEV_5300 | +90% early → drops to negative ~ts 1,000,000 → returns to +90% | **Severe whipsaw, hits limit twice** |
| VEV_5400 | Oscillates ±15% | OK |

## 5. Strategy Diagnosis & Improvement Targets

### What's working
1. **HYDROGEL_PACK market-making** — tight position control, consistent P/L. Likely a stable mean-reverter strategy around 10,000.
2. **VEV_4000 (deep ITM call)** — behaves almost like the underlying; likely arbed against VELVETFRUIT_EXTRACT successfully.
3. **VELVETFRUIT_EXTRACT** — high-frequency neutral trading with controlled inventory.

### What's broken / underexploited
1. **VEV_5300 limit-saturation whipsaw** — hitting +90% twice with a flush in between is a sign of poor position sizing or a regime-switching signal that re-enters too aggressively. Investigate cooldown/position decay logic.
2. **VEV_5200 monotonic accumulation** — drift to +75% suggests the strategy is systematically biased long (e.g., quoting asks too narrow / bids too wide, or assumes a fair value above market). Audit fair-value model for this strike.
3. **VEV_4500 / VEV_5000 / VEV_5100 dormant** — only ~1 fill each despite being liquid ITM/near-ITM strikes. Likely overly conservative spreads or fair-value model mis-priced. **Significant alpha left on the table** — these are the strikes where put-call parity / delta-replication arbitrage is most reliable.
4. **VEV_5500 and below activity but no clear edge** — small P/L despite trades; likely getting picked off by adverse selection on low-priced (high-gamma %) options.
5. **VEV_6000 / VEV_6500 entirely untraded** — pinned at 1. Could harvest premium by selling these (collecting 1 per contract until expiry) if mechanic allows shorts.

### Concrete recommendations for Claude Code
1. **Implement Black-Scholes (or competition-appropriate) fair-value model** for all VEV strikes using VELVETFRUIT_EXTRACT as underlying. Quote around theoretical value, not market mid.
2. **Add put-call-parity/synthetic-replication arbitrage** between VEV_4000 (~delta 1) and VELVETFRUIT_EXTRACT.
3. **Position-size by gamma/vega risk**, not raw limit %. Lower-priced strikes carry disproportionate gamma per unit.
4. **Add inventory-skew quoting** so positions decay back toward 0 — the VEV_5200 drift is a textbook symptom of missing skew.
5. **Investigate VEV_5300's regime change at ts ≈ 1,000,000** — find what triggered the unwind and ensure entries/exits are smoothed.
6. **Consider selling VEV_6000 / VEV_6500** at price 1 if the venue permits short option positions and the implied vol justifies it.

## 6. Timeline Anchors (for log/replay correlation)
- Backtest spans ts 0 → ~1,900,000 (~1.9M ticks).
- Notable event: ts ≈ 1,000,000 — VEV_5300 position flush.
- Notable event: ts ≈ 1,500,000–1,700,000 — VELVETFRUIT_EXTRACT dips toward 5,180 (lowest); VEV_4500/5000/5100 also bottom; VEV_5300 spikes back to +90% position.
- Volatility regime: highest realized vol in first ~400k ticks, calmer mid-run, picks up again ts 1,500,000+.
