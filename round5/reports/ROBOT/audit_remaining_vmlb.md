# ROBOT Remaining-Three Audit — VACUUMING / MOPPING / LAUNDRY

_Out of scope: ROBOT_DISHES (already covered by `strat_taker_robot_dishes.py` + `strat_spike_fade_robot_dishes.py`), ROBOT_IRONING (covered as spike-fade in `strat_combined_v7_spike.py:189`)._

## TL;DR

All three drop. The pipeline classifies VACUUMING / MOPPING / LAUNDRY as `MR_TAKER + PAIR_ANCHOR`, but every accept condition fails an economic check: no signal has |IC| ≥ 0.04 (the pipeline's own MR gate); the FDR-passing OBI signals that do exist (max |IC|=0.032 on VACUUMING) sit far below the half-spread threshold; LAUNDRY's TRENDING flag fails the MOMENTUM gate on hurst; and the family-wide PAIR_ANCHOR flag is invalidated by `corr_returns ≈ 0`. **No new strategy file is warranted.**

## Pipeline classifications under audit

From [archetype_assignment.csv](archetype_assignment.csv):

| Product | Confidence | Triggers fired | Contradictions | IC-verified |
|---|---|---|---|---|
| ROBOT_VACUUMING | medium | `acf1_neg`, `vwap_acf1_neg` | — | False |
| ROBOT_MOPPING | low | `vr_lt`, `acf1_neg`, `hurst_lt` | `vwap_acf_lag1=+0.012` | False |
| ROBOT_LAUNDRY | low | `hurst_lt` | `vr_k5=+1.010`, `acf_lag1=+0.006` | False |

All three carry `PAIR_ANCHOR` flag from [archetype_assignment.csv](archetype_assignment.csv) (corr_mid 0.79 / 0.82 / 0.79 within partner pairs).

## Audit method

1. **Statistical review.** Walk every fired trigger and contradiction against the underlying numbers in [stats_per_product.csv](stats_per_product.csv); compute break-even-z = spread_med / (2·|IC|·ret1_std) wherever `ic_signal` is FDR-significant; mark `n/a` otherwise.
2. **Pair-anchor sanity check.** Read [corr_returns.csv](corr_returns.csv) and reject the flag if return-correlations are near zero.
3. **Trend-follow sanity check** (LAUNDRY only). Apply the MOMENTUM gate from [archetypes.py](../../archetypes.py): `vr_k5>1.005 ∧ hurst>0.545 ∧ HAC+FDR IC[momentum_10] ≥ 0.02`.
4. **Untapped-signal sweep.** Walk every row in [signals_ic.csv](signals_ic.csv) for each product to check whether a non-MR signal (OBI, momentum, trade_imbalance, neg_spread) could carry edge that the MR-routed classifier missed.

## Per-product blocks

### ROBOT_VACUUMING — DROP

**Pipeline rationale.** Medium confidence on two stacked weak triggers (`acf_lag1=−0.008`, `vwap_acf_lag1=−0.021`); no FDR-significant IC; default anchor `neg_zscore_vwap_50`.

**Stats** ([stats_per_product.csv:2](stats_per_product.csv)).

| Stat | Value | Interpretation |
|---|---|---|
| `vr_k5` | 1.001 (z=+0.10, p≈0.92) | Statistically random walk |
| `acf_lag1` | −0.008 (Bartlett p=0.162) | Effect direction MR but **not significant** |
| `hurst` | 0.536 | Marginal (just at the 0.535 gate edge) |
| `vwap_acf_lag1` | −0.021 | Mild MR in transactions |
| `spread_median`, `ret1_std` | 7, 9.24 | — |

**Untapped-signal sweep** ([signals_ic.csv:4-5](signals_ic.csv)).

| Signal | h | IC | t | p | FDR-pass | Notes |
|---|---|---|---|---|---|---|
| `obi_l1` | 1 | +0.027 | 4.66 | 3.2e-6 | True | Below pipeline `obi_ic_min=0.04` |
| `obi_l3` | 1 | −0.032 | −5.64 | 1.7e-8 | True | Below pipeline `obi_ic_min=0.04` |
| `momentum_10` | 1 | −0.006 | −1.08 | 0.28 | False | — |
| `neg_zscore_mid_50` | 1 | +0.003 | 0.47 | 0.64 | False | The classifier's expected MR signal does not show edge |

**Verdict.** **DROP.** The MR call rests on two weak triggers, neither statistically significant in isolation. The only FDR-passing signals are OBI_L1/L3 with `|IC| ≈ 0.03`, below the pipeline's own `obi_ic_min=0.04` admission threshold. Economic check: predicted forward-return move per unit of OBI signal ≈ `0.03 · 9.24 ≈ 0.28` price units — fewer than 0.1 ticks vs spread=7. Half-spread tax dwarfs the predicted move.

**Note for future.** VACUUMING has the highest `depth_l1_mean` (17.1) and `limit10_saturation` (0.44) of the three. Cleanest defensive-MM candidate, but the pipeline's Template-A simulation gate already FAILED (no `MM_CANDIDATE` flag). Do not override without re-running the simulation.

### ROBOT_MOPPING — DROP

**Pipeline rationale.** Low confidence on three triggers (`vr_lt`, `acf1_neg`, `hurst_lt`) with explicit `MR_CONTRADICTION: vwap_acf_lag1=+0.012>0.01 (vwap positive autocorr)`.

**Stats** ([stats_per_product.csv:3](stats_per_product.csv)).

| Stat | Value | Interpretation |
|---|---|---|
| `vr_k5` | 0.961 (z=−3.09, p=0.002) | Statistically below 1 |
| `acf_lag1` | −0.011 (Bartlett p=0.056) | Borderline |
| `hurst` | 0.533 | Just under gate |
| `vwap_acf_lag1` | **+0.012** | **Trending** in transactions — contradiction |
| `spread_median`, `ret1_std` | 8, 11.15 | Widest spread of the three |

**Untapped-signal sweep** ([signals_ic.csv:9-15](signals_ic.csv)).

| Signal | h | IC | t | p | FDR-pass | Notes |
|---|---|---|---|---|---|---|
| `obi_l3` | 1 | −0.027 | −4.51 | 6.4e-6 | True | Below `obi_ic_min=0.04` |
| `obi_l1` | 1 | +0.013 | 2.25 | 0.025 | False | — |
| `momentum_10` | 1 | −0.010 | −1.82 | 0.069 | False | Sign = MR |
| `neg_zscore_mid_50` | 1 | +0.011 | 1.86 | 0.062 | False | Expected MR signal — not significant |
| `neg_spread` | 1000 | +0.136 | 2.15 | 0.032 | False | Long-horizon, untradeable in a tick-level taker |

**Verdict.** **DROP.** Mid is mildly mean-reverting, VWAP is trending — quote-side noise vs transaction reality conflict. Trading the z-score anchor on mid would systematically lose to toxic flow. The only FDR-passing signal (`obi_l3`, |IC|=0.027) is below the pipeline gate, and economic check identical to VACUUMING fails. The widest spread of the three (8) makes the half-spread tax even more punishing.

### ROBOT_LAUNDRY — DROP

**Pipeline rationale.** Low confidence on a single weak trigger (`hurst<0.535`) with **two** `MR_CONTRADICTION` flags: `vr_k5=1.010>1.005 (trending)`, `acf_lag1=+0.006>0.005 (positive autocorr)`. Also flagged in [deep_triggers.md](deep_triggers.md) as a TRENDING candidate.

**Stats** ([stats_per_product.csv:5](stats_per_product.csv)).

| Stat | Value | Interpretation |
|---|---|---|
| `vr_k5` | 1.010 (z=+0.80, p=0.42) | Trending direction but **not significant** |
| `acf_lag1` | +0.006 | Positive (trending), tiny magnitude |
| `hurst` | 0.517 | Just below MR gate (0.535) — the lone MR trigger |
| `vwap_acf_lag1` | −0.009 | Borderline |
| `spread_median`, `ret1_std` | 7, 9.82 | — |

**MOMENTUM gate check** ([archetypes.py](../../archetypes.py)). Required: `vr_k5>1.005 ∧ hurst>0.545 ∧ HAC+FDR IC[momentum_10] ≥ 0.02 sign-positive`.

| Condition | Value | Pass? |
|---|---|---|
| `vr_k5 > 1.005` | 1.010 | ✓ |
| `hurst > 0.545` | 0.517 | ✗ |
| FDR-pass `IC[momentum_10] ≥ 0.02` sign-positive | IC h=1 = +0.006 (p=0.34, FDR=False); IC h=10 = +0.024 (p=0.062, FDR=False) | ✗ |

MOMENTUM admission fails on hurst and on momentum IC.

**Untapped-signal sweep** ([signals_ic.csv:23-29](signals_ic.csv)).

| Signal | h | IC | t | p | FDR-pass | Notes |
|---|---|---|---|---|---|---|
| `obi_l1` | 1 | +0.025 | 4.37 | 1.3e-5 | True | Below `obi_ic_min=0.04` |
| `obi_l3` | 1 | −0.017 | −2.90 | 0.004 | False | — |
| `momentum_10` | 1 | +0.006 | 0.96 | 0.34 | False | Sign positive but insignificant |
| `neg_zscore_mid_50` | 1 | −0.006 | −0.97 | 0.33 | False | **Wrong sign** for MR |
| `neg_spread` | 1 | +0.014 | 2.57 | 0.010 | False | — |

**Verdict.** **DROP.** Neither MR (contradicted on every axis except hurst) nor MOMENTUM (gate fails). The classifier routes LAUNDRY to MR_TAKER because the priority chain checks MR first and `hurst<0.535` happens to fire — but every other MR signal trends in the opposite direction. The expected MR anchor (`neg_zscore_mid_50`) has IC=−0.006 at h=1: **wrong sign** for mean-reversion. OBI_L1 is FDR-significant but again below the pipeline gate and below economic break-even.

**Calibration concern.** Hurst gate is 0.535. LAUNDRY at 0.517 falls in the false-positive band — the threshold was already raised from 0.48 → 0.50 → 0.535 ([round5_research.md:111](../../round5_research.md)). One product squeaking through with every other indicator pointing the other way is mild evidence that 0.535 is still slightly too loose. Not a fix here, advisory only.

## Pair-anchor sanity check (family-wide)

[corr_returns.csv](corr_returns.csv) — every off-diagonal in the 5×5 ROBOT return-correlation matrix has `|r| < 0.013`:

```
                VAC      MOP      DIS      LAU      IRO
VACUUMING   1.0000  -0.0039   0.0053  -0.0019   0.0125
MOPPING    -0.0039   1.0000  -0.0063  -0.0094  -0.0002
DISHES      0.0053  -0.0063   1.0000   0.0013   0.0004
LAUNDRY    -0.0019  -0.0094   0.0013   1.0000  -0.0082
IRONING     0.0125  -0.0002   0.0004  -0.0082   1.0000
```

The PAIR_ANCHOR flag in `archetype_assignment.csv` is computed from `corr_mid` (price-level correlation on non-stationary series) and from `coint_p`. Both are unreliable on co-trending non-stationary series — a strong `corr_mid` signals shared drift, not co-movement, and `coint_p < 0.10` is reached only by the borderline VACUUMING/LAUNDRY pair.

**Conclusion:** **PAIR_ANCHOR rejected for the entire ROBOT family.** No β-hedged residual leg has economic basis. This finding extends to DISHES and IRONING as well (out of scope here, but the underlying matrix shows it).

## Family verdict

All three of VACUUMING / MOPPING / LAUNDRY drop. No new strategy file. The pipeline correctly classified these as low / medium confidence; the audit confirms the negative outcome:

- No FDR-significant signal clears the pipeline's own |IC| ≥ 0.04 gate.
- Where FDR-passes exist (OBI_L1/L3, all three products), `|IC| ≈ 0.025–0.032` is far below the half-spread economic threshold.
- MOPPING and LAUNDRY carry explicit MR contradictions; the classifier admitted them only because the priority chain stops at the first fired trigger.
- Family-wide PAIR_ANCHOR is invalidated by zero return-correlation.

`feedback_alpha_not_backtest` honoured: do not trade without structural justification.

## Recommended pipeline follow-ups (advisory)

1. **MR contradictions should demote, not annotate.** [archetypes.py](../../archetypes.py) currently flags contradictions in the rationale string but still admits the product to MR_TAKER. Consider a hard demotion: if `vwap_acf > +0.01` OR (`vr_k5 > 1.005` AND `acf_lag1 > 0`), route to NO_EDGE regardless of which MR triggers fired. MOPPING and LAUNDRY would auto-route to NO_EDGE under this rule.
2. **TRENDING_WEAK gap.** LAUNDRY has `vr_k5 > 1.005` (trending) but fails the `hurst > 0.545` MOMENTUM gate. It currently misroutes to MR_TAKER on the lone `hurst<0.535` trigger. Consider a TRENDING_WEAK archetype that catches `vr > 1.005 ∧ hurst < 0.545` and routes to NO_EDGE explicitly, so the priority chain doesn't fall through to MR.
3. **PAIR_ANCHOR uses the wrong correlation.** Replace `corr_mid` with `corr_returns` (or require both) in the pair-flag rule. ROBOT family demonstrates the failure mode: every pair has `|corr_mid| ≥ 0.7` but `|corr_returns| ≤ 0.013` — a co-trending artefact, not a tradeable pair.
4. **OBI economic threshold.** `obi_ic_min=0.04` is too coarse — it is right for products with `ret1_std ≈ 1` but generous for `ret1_std ≈ 10`. Consider scaling the gate: `|IC| × ret1_std × 2 ≥ spread_median` at the entry threshold the strategy will use.
