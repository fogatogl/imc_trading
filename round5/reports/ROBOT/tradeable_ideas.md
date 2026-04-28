# ROBOT — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **ROBOT_VACUUMING**: MR_TAKER + PAIR_ANCHOR<->ROBOT_LAUNDRY  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **ROBOT_MOPPING**: MR_TAKER + PAIR_ANCHOR<->ROBOT_IRONING  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **ROBOT_DISHES**: MR_TAKER + PAIR_ANCHOR<->ROBOT_LAUNDRY  params={'ic_mr': 0.114535751859458, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
- **ROBOT_LAUNDRY**: MR_TAKER + PAIR_ANCHOR<->ROBOT_VACUUMING  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **ROBOT_IRONING**: MR_TAKER + PAIR_ANCHOR<->ROBOT_MOPPING  params={'ic_mr': 0.0418463855662395, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}

## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)

- _(no pairs cleared corr>0.7 + coint_p<0.05)_

## Lead-lag candidates (lag=10 ticks)

- _(no |corr| >= 0.10 at lag=10)_

## Archetype assignment

_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, and MM_CANDIDATE are orthogonal flags — any product can carry one or more on top of its primary._

Counts:
- MR_TAKER: 5
- MOMENTUM: 0
- RANDOM_WALK: 0
- NO_EDGE: 0
- PAIR_ANCHOR (flag): 5
- OBI_TAKER (flag): 0
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 2
- mr_confidence=medium: 1
- mr_confidence=low: 2
- with FDR-passing IC (mr_ic_verified=True): 2
- with at least one contradiction signal: 2

### MR_TAKER
- **ROBOT_VACUUMING**  [medium conf, 2 trigger(s)]  [+ PAIR_ANCHOR with ROBOT_LAUNDRY (stationary)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.008<-0.005 (Bartlett p=0.162); vwap_acf_lag1=-0.021<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=medium (n_triggers=2, ic_verified=False)
- **ROBOT_MOPPING**  [low conf, 3 trigger(s)]  [+ PAIR_ANCHOR with ROBOT_IRONING (non-stat)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.961<0.985 (z=-3.09, p=0.00198); acf_lag1=-0.011<-0.005 (Bartlett p=0.0564); hurst=0.533<0.535; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=3, ic_verified=False); MR_CONTRADICTION: vwap_acf_lag1=+0.012>0.01 (vwap positive autocorr)
- **ROBOT_DISHES**  [high conf, 3 trigger(s), IC-verified]  [+ PAIR_ANCHOR with ROBOT_LAUNDRY (non-stat)]
  - params: {'ic_mr': 0.114535751859458, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
  - rationale: vr_k5=0.555<0.985 (z=-35.15, p=0); acf_lag1=-0.232<-0.005 (Bartlett p=0); hurst=0.525<0.535; max |IC[neg_zscore_mid_50]|=0.115 @ h=1  (t=+15.84, p=0, FDR-pass); mr_confidence=high (n_triggers=3, ic_verified=True)
- **ROBOT_LAUNDRY**  [low conf, 1 trigger(s)]  [+ PAIR_ANCHOR with ROBOT_VACUUMING (stationary)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: hurst=0.517<0.535; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: vr_k5=1.010>1.005 (trending signal); acf_lag1=+0.006>0.005 (positive autocorr)
- **ROBOT_IRONING**  [high conf, 4 trigger(s), IC-verified]  [+ PAIR_ANCHOR with ROBOT_MOPPING (non-stat)]
  - params: {'ic_mr': 0.0418463855662395, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
  - rationale: vr_k5=0.782<0.985 (z=-17.24, p=0); acf_lag1=-0.125<-0.005 (Bartlett p=0); hurst=0.519<0.535; vwap_acf_lag1=-0.028<-0.01; max |IC[neg_zscore_mid_50]|=0.042 @ h=1  (t=+7.10, p=1.23e-12, FDR-pass); mr_confidence=high (n_triggers=4, ic_verified=True)

### PAIR_ANCHOR (orthogonal flag)
_2/5 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **ROBOT_VACUUMING** ↔ ROBOT_LAUNDRY  (corr=+0.79, coint_p=0.0701, STATIONARY)  primary=MR_TAKER
- **ROBOT_MOPPING** ↔ ROBOT_IRONING  (corr=-0.82, coint_p=0.266, non-stat)  primary=MR_TAKER
- **ROBOT_DISHES** ↔ ROBOT_LAUNDRY  (corr=-0.72, coint_p=0.257, non-stat)  primary=MR_TAKER
- **ROBOT_LAUNDRY** ↔ ROBOT_VACUUMING  (corr=+0.79, coint_p=0.0701, STATIONARY)  primary=MR_TAKER
- **ROBOT_IRONING** ↔ ROBOT_MOPPING  (corr=-0.82, coint_p=0.266, non-stat)  primary=MR_TAKER

### OBI_TAKER (orthogonal flag)
- _(no products cleared the OBI gate with FDR-pass at h ∈ {1, 10})_

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
