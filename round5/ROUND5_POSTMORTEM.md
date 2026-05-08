# Round 5 — Final Live Result & Postmortem

**Submission:** [`580385/580385.py`](../580385/580385.py) — disjoint stack of per-family live-D4 winners (Block A naive MM ⊕ Block B naive MM with spread gate ⊕ Block C smart MM/pair/basket ⊕ Block E spike-fade taker ⊕ Block F galaxy cointegration oracle).

**Live D5 PnL: −4,791 SeaShells.** Theoretical pre-submission stack: **+53,681**. Realised miss: **−58,472**.

The stack was built on the assumption that each family's best **single live D4 outcome** would replicate when shipped together on D5. It did not. This document records what worked, what broke, and what the next-year team should carry forward.

---

## 1. Per-product results

Extracted from `activitiesLog` in `580385/580385.log` at final timestamp `999900`.

| Family | Live D5 | Pre-stack expected | Δ |
|---|---:|---:|---:|
| GALAXY_SOUNDS | +13,801 | +3,441 | **+10,360** |
| SNACKPACK | +12,766 | +4,546 | **+8,220** |
| PEBBLES | +8,914 | +10,428 | −1,514 |
| ROBOT | +5,610 | +4,165 | +1,445 |
| PANEL | 0 | +11 | −11 |
| MICROCHIP | −859 | +4,411 | −5,270 |
| OXYGEN_SHAKE | −6,221 | +3,497 | −9,718 |
| UV_VISOR | −8,149 | +8,640 | **−16,789** |
| TRANSLATOR | −13,596 | +4,832 | **−18,428** |
| SLEEP_POD | −17,057 | +9,710 | **−26,767** |
| **Total** | **−4,791** | **+53,681** | **−58,472** |

### Top 5 winners
| Product | PnL | Mechanism |
|---|---:|---|
| PEBBLES_XL | +41,269 | Anchor leg of 4-pair PEB star — caught one-sided directional move |
| GALAXY_SOUNDS_SOLAR_FLAMES | +6,747 | Cointegration oracle — fair = const + Σ wᵢ·midᵢ |
| ROBOT_MOPPING | +4,744 | Naive MM, qty=1 |
| SNACKPACK_PISTACHIO | +4,436 | Basket leg, ent=2.0 |
| GALAXY_SOUNDS_DARK_MATTER | +4,042 | Cointegration oracle |

### Top 6 losers — concentrate 100% of the bleed
| Product | PnL | Failure mode |
|---|---:|---|
| PEBBLES_S | −30,141 | Short leg of PEB star — counterparty to XL's directional gain (basket-internal) |
| UV_VISOR_RED | −10,327 | Naive top-of-book MM, qty=cap, no trend defense |
| SLEEP_POD_POLYESTER | −10,045 | slp_cp pair (β=−0.795 on D2-D4) — β unstable on D5 |
| SLEEP_POD_NYLON | −8,929 | Same pair |
| TRANSLATOR_VOID_BLUE | −7,855 | Naive MM, qty=cap, directional D5 |
| OXYGEN_SHAKE_CHOCOLATE | −7,024 | Naive MM, qty=cap, directional D5 |
| **Combined** | **−74,321** | — |

The remaining 44 products net **+69,530** — the round was lost in 6 names.

---

## 2. What worked

### 2.1 Structural / fair-value alpha replicated
The **GLX cointegration oracle** (Block F: SOLAR_FLAMES, DARK_MATTER, BLACK_HOLES) priced a fair value from a regression of related galaxy mids and traded the residual against `|z|>2`. It returned **+13,801** vs an expected **+3,441** — the only family that *beat* its expectation, by 4×.

The mechanism is structural: as long as the linear relationship between the galaxy products holds, the residual mean-reverts. This is the same pattern as the round-4 hydrogel/voucher system — fair-value oracles dominate stationary mean-rev around fitted constants.

### 2.2 Multi-leg baskets with disjoint legs
The **SNACKPACK 4-pair basket** (CHOC↔VAN, PIST↔RASP, PIST↔STRAW, RASP↔STRAW, ent=2.0, units 2/2/3/3) returned **+12,766** vs **+4,546** expected. Disjoint pair legs distributed inventory across the family; entry threshold filtered noise. Survived the regime change.

### 2.3 Trend filter on naive MM
**PANEL** (560470 trend-filtered naive MM, ema30 vs ema200) closed **flat (0)**. Same construction without the filter would have lost on D5's directional drift — see the 559949 telemetry showing −3,155 on naive PANEL MM. The filter alone was enough to neutralise.

---

## 3. What broke

### 3.1 Naive top-of-book MM with `qty=cap` is short-trend
UV_RED, TRANSLATOR_VOID_BLUE, TRANSLATOR_GRAPHITE_MIST, OXYGEN_SHAKE_CHOCOLATE, MICROCHIP_CIRCLE all ship as naive top-of-book makers at `qty=position_limit`. On D5 these products had smooth directional drift; bid-fills clustered early on the way down, ask-fills clustered late after the bottom — every round-trip paid the spread the wrong direction.

This failure mode was already documented in [`feedback_naive_mm_no_trend_defense`](../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_naive_mm_no_trend_defense.md) after the PANEL 559949 run lost −3,155 the same way. The fix (trend filter, hard inventory cap, or inventory-fading skew) was applied to PANEL and *only* PANEL. Every other naive-MM block in 580385 shipped without protection.

### 3.2 Pair regression β unstable across days
The **SLEEP_POD slp_cp pair** (COTTON ↔ POLYESTER, β=−0.795 OLS, entry=1.6, fit on D2-D4) returned **−18,973** on POLYESTER+NYLON legs because the D5 residual went the wrong way. The pair passed the cointegration test on the in-sample window but the β was not stable on D5.

[`feedback_pairs_screen`](../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_pairs_screen.md) had explicitly warned to rank pairs by *β stability and intra-day half-life*, not by Engle-Granger p-value. The slp_cp pair was selected on coint p alone.

### 3.3 Theoretical stack with no combined backtest
The +53,681 figure was a **sum of per-family single-live-D4 winners**, not the result of running the combined trader through a backtest. Each family's "best" was the highest single live PnL across the team's submissions — n=1.

Because no combined BT was run, there was no opportunity for [`feedback_bt_inflation_round5_mm`](../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_bt_inflation_round5_mm.md) (BT/live ≈ 10×) to apply. The decay heuristic only activates when there is a BT number to decay from. The rule should be: **never ship a combined trader without first BT-ing the combined trader**, even if individual blocks are validated separately.

### 3.4 Concentration risk inside a "neutral" basket
The **PEBBLES star** netted +8,914 because PEBBLES_XL gained +41,269 against PEBBLES_S/M/L/XS shorts of −34k. The basket is sold as market-neutral via a regression hedge against XL. In practice, the residual of that hedge depends on the realised intra-day correlation — which on D5 was favourable for XL.

If XL had drawn the other direction, the basket would have lost ≈−34,000 with the same trader. The PnL was an n=1 directional draw on the anchor leg, not a clean residual capture.

---

## 4. Cross-family lessons

### Lesson 1: stop stacking n=1 outcomes
The manifest selected each family's best by single-live-D4 PnL. Stack assumed independence and replicability across families, which is what variance is *not*. On D5, half of the picks regressed.

> **Rule:** require per-day-positive on every available sample day before promoting a strategy block. If no block in a family clears that bar, **ship 0 quantity** for that family — not the least-bad option.

[`feedback_per_day_positive_selection`](../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_per_day_positive_selection.md) already encoded this rule. The override happened because the manifest used "best available D4" as a proxy when nothing was 3-of-3 positive. The proxy is the bug.

### Lesson 2: structural alpha > statistical alpha
Only the GLX cointegration oracle beat its expectation. Every block that relied on "this product happened to mean-revert in the BT window" lost on regime change.

> **Rule:** prefer fair-value/cointegration/basket structures over stationary mean-rev around a fitted constant. Re-validates [`feedback_alpha_not_backtest`](../../.claude/projects/c--Users-fogat-Desktop-imc-trading/memory/feedback_alpha_not_backtest.md) (originally from r3 hydrogel v9 disaster).

### Lesson 3: a hard inventory cap is the cheapest survival mechanic
Every losing position above is a story of inventory accumulating in the wrong direction and being held to the close. UV_VISOR_RED, SLEEP_POD_POLYESTER, OXYGEN_SHAKE_CHOCOLATE all ended at a heavy long position on a downtrend.

> **Rule:** for any naive MM block, ship a hard cap `|pos| ≤ 5` (half the position limit) regardless of what the BT shows. Combined with a trend filter, this would have saved an estimated 30-50k on this run with minimal cost to MM rebate capture.

### Lesson 4: every memory rule that would have prevented this was already written
Pre-submission memory contained:
- `feedback_naive_mm_no_trend_defense`
- `feedback_per_day_positive_selection`
- `feedback_pairs_screen`
- `feedback_bt_inflation_round5_mm`
- `feedback_simple_first_mm`
- `feedback_alpha_not_backtest`

Each was applied at the *per-product* level (each component file individually validated). None was applied at the *combined ensemble* level (the actual shipped artifact). When checking the combined trader before submission, the relevant question is: "does every memory entry from this round still hold for the proposed combined behaviour?" — not "did each component pass its own check?"

> **Rule for next year:** the final-round combined submission gets a memory-checklist review pass against every `feedback_*` entry collected during the round, before shipping. The reviewer treats the combined trader as a new artifact, not as the union of validated parts.

---

## 5. Recommendations for next year (Round 5 of Prosperity 5+)

### Engineering
1. **Single-trader combined backtest is mandatory before submission.** Even if `prosperity4bt` and `rust_backtester` agree on each family file, run the actual ensemble through both. Block submission if not done.
2. **Hard inventory cap on every MM block.** `|pos| ≤ position_limit / 2` is a default; relax only with structural alpha justification.
3. **Trend filter on every naive MM.** EMA-fast vs EMA-slow gating, or skew that fades inventory. PANEL 560470 is the working template.
4. **Per-product max drawdown kill switch.** `if pnl_today < −X: pull quotes for that product`. Does not require BT to validate — it is risk management, not alpha.

### Selection
5. **Per-day-positive on every available day** before promotion. Hard rule. No "best available" fallback.
6. **Pairs screen by β stability + intra-day half-life**, not by coint p-value or in-sample correlation.
7. **Distinguish structural alpha from statistical alpha.** Cointegration / basket / fair-value oracles get a multiplier; stationary mean-rev around a fitted constant gets a haircut.

### Process
8. **Combined-trader memory review** before final submission. Treat the ensemble as a new artifact.
9. **Document n in every PnL claim.** A single live D4 figure is "n=1 outcome", not "estimated alpha".
10. **Keep the postmortem in the repo.** Round 3 and Round 4 had final-result sections that fed into Round 4 success. Round 5 needed those sections written *before* Round 5 ended; this document is that input for the next year.

---

## 6. Comparison to previous rounds

| Round | Submitted | Live PnL | Outcome | Defining feature |
|---|---|---:|---|---|
| 3 | `486411.py` | +36,116 | Solid | Stationary mean-rev with vol armor on hydrogel |
| 4 | `544098.py` | **+99,202** | Best | Trending anchor + OU-corrected BS + skip-the-tails on VEV strikes |
| 5 | `580385.py` | **−4,791** | Loss | Stack of n=1 D4 winners; no combined BT; no inventory caps |

Round 4's win came from *removing* the round-3 strikes that didn't work (VEV_4000/4500/6000/6500) — tightening the smile rather than fixing it. Round 5 did the opposite: stacked everything that worked once, did not check what would happen when stacked.

---

## 7. Files of record

- **Strategy:** [`580385/580385.py`](../580385/580385.py)
- **Live log:** [`580385/580385.log`](../580385/580385.log) (88 MB; activities CSV embedded in JSON)
- **Live JSON snapshot:** [`580385/580385.json`](../580385/580385.json)
- **Pre-submission expected breakdown:** [`round5/best_strategies/MANIFEST.md`](best_strategies/MANIFEST.md)
- **Component sources:** [`round5/best_strategies/`](best_strategies/) (`549159.py`, `555509.py`, `556852.py`, `556909.py`, `558897.py`, `560161.py`, `560470.py`)
