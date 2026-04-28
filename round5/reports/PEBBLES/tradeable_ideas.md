# PEBBLES — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **PEBBLES_XS**: MR_TAKER + PAIR_ANCHOR<->PEBBLES_XL  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **PEBBLES_S**: MR_TAKER + PAIR_ANCHOR<->PEBBLES_XL  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **PEBBLES_M**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **PEBBLES_L**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **PEBBLES_XL**: MR_TAKER + PAIR_ANCHOR<->PEBBLES_S  params={'ic_mr': 0.077590495044855, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 100}

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
- PAIR_ANCHOR (flag): 3
- OBI_TAKER (flag): 0
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 1
- mr_confidence=medium: 1
- mr_confidence=low: 3
- with FDR-passing IC (mr_ic_verified=True): 1
- with at least one contradiction signal: 3

### MR_TAKER
- **PEBBLES_XS**  [high conf, 3 trigger(s)]  [+ PAIR_ANCHOR with PEBBLES_XL (non-stat)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.016<-0.005 (Bartlett p=0.00684); hurst=0.528<0.535; vwap_hurst=0.484<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=high (n_triggers=3, ic_verified=False)
- **PEBBLES_S**  [low conf, 1 trigger(s)]  [+ PAIR_ANCHOR with PEBBLES_XL (non-stat)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vwap_hurst=0.476<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: acf_lag1=+0.008>0.005 (positive autocorr); hurst=0.551>0.55 (persistent); vwap_acf_lag1=+0.015>0.01 (vwap positive autocorr)
- **PEBBLES_M**  [medium conf, 2 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: hurst=0.517<0.535; vwap_acf_lag1=-0.033<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=medium (n_triggers=2, ic_verified=False)
- **PEBBLES_L**  [low conf, 2 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: hurst=0.535<0.535; vwap_acf_lag1=-0.031<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=2, ic_verified=False); MR_CONTRADICTION: vr_k5=1.014>1.005 (trending signal); acf_lag1=+0.007>0.005 (positive autocorr)
- **PEBBLES_XL**  [low conf, 1 trigger(s), IC-verified]  [+ PAIR_ANCHOR with PEBBLES_S (non-stat)]
  - params: {'ic_mr': 0.077590495044855, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 100}
  - rationale: hurst=0.511<0.535; max |IC[neg_zscore_mid_50]|=0.078 @ h=100  (t=+2.98, p=0.00287, FDR-pass); mr_confidence=low (n_triggers=1, ic_verified=True); MR_CONTRADICTION: vr_k5=1.015>1.005 (trending signal); acf_lag1=+0.008>0.005 (positive autocorr); vwap_acf_lag1=+0.012>0.01 (vwap positive autocorr)

### PAIR_ANCHOR (orthogonal flag)
_0/3 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **PEBBLES_XS** ↔ PEBBLES_XL  (corr=-0.83, coint_p=0.482, non-stat)  primary=MR_TAKER
- **PEBBLES_S** ↔ PEBBLES_XL  (corr=-0.83, coint_p=0.229, non-stat)  primary=MR_TAKER
- **PEBBLES_XL** ↔ PEBBLES_S  (corr=-0.83, coint_p=0.229, non-stat)  primary=MR_TAKER

### OBI_TAKER (orthogonal flag)
- _(no products cleared the OBI gate with FDR-pass at h ∈ {1, 10})_

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
