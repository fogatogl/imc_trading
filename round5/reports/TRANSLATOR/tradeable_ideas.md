# TRANSLATOR — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **TRANSLATOR_ASTRO_BLACK**: MR_TAKER + OBI_TAKER[obi_l3@h=1, IC=-0.042]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **TRANSLATOR_ECLIPSE_CHARCOAL**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **TRANSLATOR_GRAPHITE_MIST**: MR_TAKER + OBI_TAKER[obi_l3@h=1, IC=-0.040]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **TRANSLATOR_SPACE_GRAY**: NO_EDGE
- **TRANSLATOR_VOID_BLUE**: MR_TAKER + OBI_TAKER[obi_l3@h=1, IC=-0.044]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}

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
- PAIR_ANCHOR (flag): 0
- OBI_TAKER (flag): 3
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 3
- mr_confidence=medium: 0
- mr_confidence=low: 1
- with FDR-passing IC (mr_ic_verified=True): 0
- with at least one contradiction signal: 1

### MR_TAKER
- **TRANSLATOR_ASTRO_BLACK**  [low conf, 1 trigger(s)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.042]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.006<-0.005 (Bartlett p=0.284); structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: vwap_acf_lag1=+0.017>0.01 (vwap positive autocorr)
- **TRANSLATOR_ECLIPSE_CHARCOAL**  [high conf, 3 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.984<0.985 (z=-1.24, p=0.216); acf_lag1=-0.007<-0.005 (Bartlett p=0.195); vwap_acf_lag1=-0.031<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=3, ic_verified=False)
- **TRANSLATOR_GRAPHITE_MIST**  [high conf, 3 trigger(s)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.040]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.984<0.985 (z=-1.27, p=0.202); hurst=0.526<0.535; vwap_acf_lag1=-0.015<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=3, ic_verified=False)
- **TRANSLATOR_VOID_BLUE**  [high conf, 4 trigger(s)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.044]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.984<0.985 (z=-1.27, p=0.203); acf_lag1=-0.009<-0.005 (Bartlett p=0.137); hurst=0.525<0.535; vwap_acf_lag1=-0.032<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=4, ic_verified=False)

### NO_EDGE
- **TRANSLATOR_SPACE_GRAY**
  - rationale: no primary trigger fired; vr=1.019 (p=0.127), hurst=0.55, acf1=+0.008 (p=0.183); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.039 @ obi_l3 h=1 (informational)

### PAIR_ANCHOR (orthogonal flag)
- _(no products cleared the PAIR gate vs any family member)_

### OBI_TAKER (orthogonal flag)
_0 follow signals, 3 fade signals (sign of IC determines strategy direction)._
- **TRANSLATOR_ASTRO_BLACK**  direction=fade  signal=obi_l3  h=1  IC=-0.042  primary=MR_TAKER
- **TRANSLATOR_GRAPHITE_MIST**  direction=fade  signal=obi_l3  h=1  IC=-0.040  primary=MR_TAKER
- **TRANSLATOR_VOID_BLUE**  direction=fade  signal=obi_l3  h=1  IC=-0.044  primary=MR_TAKER

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
