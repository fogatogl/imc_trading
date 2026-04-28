# SLEEP_POD — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **SLEEP_POD_SUEDE**: MR_TAKER + PAIR_ANCHOR<->SLEEP_POD_POLYESTER + OBI_TAKER[obi_l3@h=1, IC=-0.040]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **SLEEP_POD_LAMB_WOOL**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **SLEEP_POD_POLYESTER**: MR_TAKER + PAIR_ANCHOR<->SLEEP_POD_COTTON + OBI_TAKER[obi_l3@h=1, IC=-0.042]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **SLEEP_POD_NYLON**: MR_TAKER + OBI_TAKER[obi_l3@h=1, IC=-0.049]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **SLEEP_POD_COTTON**: NO_EDGE + PAIR_ANCHOR<->SLEEP_POD_POLYESTER + OBI_TAKER[obi_l3@h=1, IC=-0.051]

## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)

- _(no pairs cleared corr>0.7 + coint_p<0.05)_

## Lead-lag candidates (lag=10 ticks)

- _(no |corr| >= 0.10 at lag=10)_

## Archetype assignment

_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, and MM_CANDIDATE are orthogonal flags — any product can carry one or more on top of its primary._

Counts:
- MR_TAKER: 4
- MOMENTUM: 0
- RANDOM_WALK: 0
- NO_EDGE: 1
- PAIR_ANCHOR (flag): 3
- OBI_TAKER (flag): 4
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 1
- mr_confidence=medium: 1
- mr_confidence=low: 2
- with FDR-passing IC (mr_ic_verified=True): 0
- with at least one contradiction signal: 1

### MR_TAKER
- **SLEEP_POD_SUEDE**  [high conf, 3 trigger(s)]  [+ PAIR_ANCHOR with SLEEP_POD_POLYESTER (non-stat)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.040]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.006<-0.005 (Bartlett p=0.281); hurst=0.527<0.535; vwap_acf_lag1=-0.074<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=3, ic_verified=False)
- **SLEEP_POD_LAMB_WOOL**  [low conf, 1 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vwap_adf_p=0.0543<0.1; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: vr_k5=1.023>1.005 (trending signal); vwap_acf_lag1=+0.035>0.01 (vwap positive autocorr)
- **SLEEP_POD_POLYESTER**  [medium conf, 2 trigger(s)]  [+ PAIR_ANCHOR with SLEEP_POD_COTTON (non-stat)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.042]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: hurst=0.531<0.535; vwap_hurst=0.459<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=medium (n_triggers=2, ic_verified=False)
- **SLEEP_POD_NYLON**  [low conf, 1 trigger(s)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.049]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vwap_hurst=0.446<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=1, ic_verified=False)

### NO_EDGE
- **SLEEP_POD_COTTON**  [+ PAIR_ANCHOR with SLEEP_POD_POLYESTER (non-stat)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.051]
  - rationale: no primary trigger fired; vr=0.985 (p=0.244), hurst=0.56, acf1=-0.003 (p=0.582); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.206 @ neg_spread h=1000 (informational)

### PAIR_ANCHOR (orthogonal flag)
_0/3 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **SLEEP_POD_SUEDE** ↔ SLEEP_POD_POLYESTER  (corr=+0.86, coint_p=0.151, non-stat)  primary=MR_TAKER
- **SLEEP_POD_POLYESTER** ↔ SLEEP_POD_COTTON  (corr=+0.88, coint_p=0.101, non-stat)  primary=MR_TAKER
- **SLEEP_POD_COTTON** ↔ SLEEP_POD_POLYESTER  (corr=+0.88, coint_p=0.101, non-stat)  primary=NO_EDGE

### OBI_TAKER (orthogonal flag)
_0 follow signals, 4 fade signals (sign of IC determines strategy direction)._
- **SLEEP_POD_SUEDE**  direction=fade  signal=obi_l3  h=1  IC=-0.040  primary=MR_TAKER
- **SLEEP_POD_POLYESTER**  direction=fade  signal=obi_l3  h=1  IC=-0.042  primary=MR_TAKER
- **SLEEP_POD_NYLON**  direction=fade  signal=obi_l3  h=1  IC=-0.049  primary=MR_TAKER
- **SLEEP_POD_COTTON**  direction=fade  signal=obi_l3  h=1  IC=-0.051  primary=NO_EDGE

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
