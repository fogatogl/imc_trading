# Round 5 — Final Live Result & Postmortem

**Combined result: +90,958 SeaShells** (algorithmic −4,791 + manual +95,749).

| Side | Result |
|---|---:|
| Algorithmic ([`580385/580385.py`](../580385/580385.py)) | **−4,791** |
| Manual (Ignith news portfolio, see [`manual/FINAL_strategy.md`](manual/FINAL_strategy.md)) | **+95,749** |
| **Round 5 total** | **+90,958** |

The manual side carried the round. The algorithmic submission lost slightly vs a +53,681 pre-submission theoretical stack (Δ −58,472) — the stack was built on the assumption that each family's best **single live D4 outcome** would replicate when shipped together on D5. It did not. This document records what worked, what broke, and what the next-year team should carry forward, on both the algorithmic and manual sides.

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

## 7. Manual round — Ignith news portfolio (+95,749)

**Result: +95,749 SeaShells** on 48% budget deployment.

The manual side used the audit-corrected event-study framework in [`round5/manual/FINAL_strategy.md`](manual/FINAL_strategy.md) and [`round5/manual/final_strategy.py`](manual/final_strategy.py): translate each Ashflow Alpha article into `(r_est, σ)` anchored to a real-world event analogue, apply the closed-form optimum `x* = r/2` under quadratic fees, stop deploying volume past the optimum (47.5% of budget intentionally held in cash because marginal contribution turns negative).

The submitted allocation deviated from the audit table on four names where we judged the wider competitor pool would systematically mis-price relative to the news magnitude. Round-5 manual scoring is partly relative to the field's positions, so behavioural-overlay logic was applied on top of the calibrated `r_est`.

### Result vs audit expectation

| Metric | Audit point estimate | Audit range | **Realised** |
|---|---:|---|---:|
| Total PnL | +$41,000 | $1k–$108k | **+$95,749** |
| Budget deployed | 52.5% | — | 48% |

Realised PnL sits near the upper end of the audit's plausible-worlds range, just below the aggressive-world estimate (+$107,825).

### Per-product result

| Product | Direction | % | Investment | Fee | PnL |
|---|:-:|:-:|---:|---:|---:|
| **Lava Cakes** | SELL | 17% | 170,000 | 28,900 | **+78,801** |
| **Thermalite Core** | BUY | 10% | 100,000 | 10,000 | **+12,160** |
| Pyroflex Cells | SELL | 6% | 60,000 | 3,600 | +8,121 |
| Sulfur Reactor | BUY | 3% | 30,000 | 900 | +4,327 |
| Ashes of Phoenix | SELL | 2% | 20,000 | 400 | +301 |
| Scoria Paste | — | 0% | 0 | 0 | 0 |
| Obsidian Cutlery | SELL | 2% | 20,000 | 400 | −2,383 |
| Magma Ink | BUY | 6% | 60,000 | 3,600 | −2,264 |
| Volcanic Incense | **BUY** | 2% | 20,000 | 400 | **−3,314** |
| **Total** | — | **48%** | **480,000** | **48,200** | **+95,749** |

Lava Cakes alone delivered **82% of total PnL** (+78,801 of +95,749). Top three names (Lava + Thermalite + Pyroflex) delivered **+99,082**, with the rest of the portfolio netting −3,333.

### Behavioural deviations from the audit table

| Product | Audit | Submitted | Reasoning | Outcome |
|---|:-:|:-:|---|:-:|
| Lava Cakes | SHORT 12.5% | **SHORT 17%** | Triple-driver recall (recall + lawsuits + vendor returns) is unambiguous. Crowd likely under-shorts due to caution; size up to capture relative-scoring edge. | ✅ correct |
| Volcanic Incense | SHORT 7.5% | **LONG 2%** | Pump-pattern article will trigger reflexive crowd SHORT; fade with small LONG. | ❌ wrong (−3,314) |
| Ashes of Phoenix | SHORT 5% | SHORT 2% | PR scandal but defensive corporate response → expect crowd over-shoots short side; haircut. | ≈ flat |
| Obsidian Cutlery | SHORT 3.5% | SHORT 2% | Genuinely ambiguous; field also expected to size small; edge too thin. | ≈ flat |

Other five names (Thermalite, Pyroflex, Magma Ink, Sulfur, Scoria) shipped within ±1% of the audit table.

### Manual-round lessons

1. **Audit framework gated the result.** Even with two directional losses (Volcanic Incense −3,314, Magma Ink −2,264), the portfolio cleared +$95k. Quadratic-fee discipline — 48% deployed not 100% — is what made the upside extraction efficient. The framework's design property was robustness across calibration worlds; the run is direct evidence of that holding.

2. **Concentrate on structurally unambiguous signals.** Lava Cakes was the only news article with three independent negative drivers (recall + lawsuits + vendor returns). Sizing it up from 12.5% to 17% delivered +78,801. The audit's `x* = r/2` rule already rewards confidence (sized by `r_est`), so the deviation was second-order — but in the right direction.

3. **Crowd-fading on ambiguous signals is uncorrelated with truth.** The Volcanic Incense fade (LONG against audit's SHORT) lost. The pump-pattern article was structurally suspect by audit standards, but the audit's call was still SHORT — guessing the crowd's reaction added nothing. Rule for next year: behavioural overrides only on names where the underlying signal is structurally clear, not on ambiguous ones.

4. **r_est anchored to event-study analogues beat gut judgment.** The original (pre-audit) plan deployed 100% of budget on inflated `r_est` values; modeled expected PnL was +$140k, but cross-world stress test showed −$59k under efficient-market priors. The audit-corrected r/σ table rebalanced to robust positive expectation across all five worlds. Realised result confirms the calibration was directionally right.

5. **Quadratic fee makes the unused-budget question backwards.** "Why am I only deploying 48%?" is the wrong question. The right question is: "what is the marginal PnL of the next dollar?" Past the optimum it's negative. Filling the budget is what the original (flawed) plan did, and it would have cost roughly $120k in expected PnL across realistic worlds.

---

## 8. Combined-round summary

| Side | Result | Driver |
|---|---:|---|
| Algorithmic (Ignith MM) | **−4,791** | Stack of n=1 D4 winners; half regressed on D5 regime change. Lessons §1–§5 above. |
| Manual (Ignith news portfolio) | **+95,749** | Audit-framework allocation with quadratic-fee discipline; Lava Cakes drove 82% of PnL. |
| **Round 5 total** | **+90,958** | Manual carried; algo was a wash. |

The two sides illustrate the same lesson from opposite directions:

- **Algorithmic side** failed because outcomes were stacked without a calibration framework — n=1 D4 PnLs treated as alpha estimates.
- **Manual side** worked because outcomes were stacked **with** a calibration framework — `r_est` anchored to event-study analogues, deployment derived from `x* = r/2`, stress-tested across multiple worlds before submission.

**Single most important takeaway for next year:** the framework matters more than the inputs. The manual side won despite two wrong directional calls because the framework bounded the downside. The algorithmic side lost despite per-component validation because there was no framework over the ensemble — just additive optimism.

---

## 9. Files of record

- **Algorithmic strategy:** [`580385/580385.py`](../580385/580385.py)
- **Algorithmic live log:** [`580385/580385.log`](../580385/580385.log) (88 MB; activities CSV embedded in JSON)
- **Algorithmic live JSON snapshot:** [`580385/580385.json`](../580385/580385.json)
- **Algorithmic pre-submission expected breakdown:** [`round5/best_strategies/MANIFEST.md`](best_strategies/MANIFEST.md)
- **Algorithmic component sources:** [`round5/best_strategies/`](best_strategies/) (`549159.py`, `555509.py`, `556852.py`, `556909.py`, `558897.py`, `560161.py`, `560470.py`)
- **Manual strategy doc:** [`round5/manual/FINAL_strategy.md`](manual/FINAL_strategy.md)
- **Manual calibration script:** [`round5/manual/final_strategy.py`](manual/final_strategy.py)
- **Manual figures:** [`round5/manual/F1_final_allocation.png`](manual/F1_final_allocation.png), [`F3_robustness.png`](manual/F3_robustness.png), [`F4_cdf_comparison.png`](manual/F4_cdf_comparison.png), [`F5_contribution.png`](manual/F5_contribution.png)
