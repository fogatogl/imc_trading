# OXYGEN_SHAKE — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **OXYGEN_SHAKE_CHOCOLATE**: MR_TAKER + PAIR_ANCHOR<->OXYGEN_SHAKE_GARLIC + OBI_TAKER[obi_l1@h=1, IC=+0.057]  params={'ic_mr': 0.0243558991534577, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
- **OXYGEN_SHAKE_MINT**: NO_EDGE + OBI_TAKER[obi_l1@h=1, IC=+0.055]
- **OXYGEN_SHAKE_GARLIC**: NO_EDGE + PAIR_ANCHOR<->OXYGEN_SHAKE_CHOCOLATE + OBI_TAKER[obi_l1@h=1, IC=+0.066]
- **OXYGEN_SHAKE_MORNING_BREATH**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.051]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **OXYGEN_SHAKE_EVENING_BREATH**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.054]  params={'ic_mr': 0.0485709967825646, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}

## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)

- _(no pairs cleared corr>0.7 + coint_p<0.05)_

## Lead-lag candidates (lag=10 ticks)

- _(no |corr| >= 0.10 at lag=10)_

## Archetype assignment

_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, and MM_CANDIDATE are orthogonal flags — any product can carry one or more on top of its primary._

Counts:
- MR_TAKER: 3
- MOMENTUM: 0
- RANDOM_WALK: 0
- NO_EDGE: 2
- PAIR_ANCHOR (flag): 2
- OBI_TAKER (flag): 5
- MM_CANDIDATE (flag): 3

MR_TAKER confidence breakdown:
- mr_confidence=high: 3
- mr_confidence=medium: 0
- mr_confidence=low: 0
- with FDR-passing IC (mr_ic_verified=True): 2
- with at least one contradiction signal: 0

### MR_TAKER
- **OXYGEN_SHAKE_CHOCOLATE**  [high conf, 3 trigger(s), IC-verified]  [+ PAIR_ANCHOR with OXYGEN_SHAKE_GARLIC (stationary)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.057]
  - params: {'ic_mr': 0.0243558991534577, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
  - rationale: vr_k5=0.836<0.985 (z=-12.96, p=0); acf_lag1=-0.089<-0.005 (Bartlett p=0); hurst=0.515<0.535; max |IC[neg_zscore_mid_50]|=0.024 @ h=1  (t=+4.10, p=4.05e-05, FDR-pass); mr_confidence=high (n_triggers=3, ic_verified=True)
- **OXYGEN_SHAKE_MORNING_BREATH**  [high conf, 4 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.051]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.983<0.985 (z=-1.31, p=0.189); acf_lag1=-0.005<-0.005 (Bartlett p=0.365); hurst=0.516<0.535; vwap_acf_lag1=-0.036<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=4, ic_verified=False); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **OXYGEN_SHAKE_EVENING_BREATH**  [high conf, 3 trigger(s), IC-verified]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.054]
  - params: {'ic_mr': 0.0485709967825646, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1}
  - rationale: vr_k5=0.798<0.985 (z=-15.93, p=0); acf_lag1=-0.123<-0.005 (Bartlett p=0); hurst=0.518<0.535; max |IC[neg_zscore_mid_50]|=0.049 @ h=1  (t=+7.53, p=5.04e-14, FDR-pass); mr_confidence=high (n_triggers=3, ic_verified=True)

### NO_EDGE
- **OXYGEN_SHAKE_MINT**  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.055]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - rationale: no primary trigger fired; vr=1.004 (p=0.722), hurst=0.55, acf1=-0.003 (p=0.595); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.139 @ neg_spread h=1000 (informational); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **OXYGEN_SHAKE_GARLIC**  [+ PAIR_ANCHOR with OXYGEN_SHAKE_CHOCOLATE (stationary)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.066]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - rationale: no primary trigger fired; vr=1.008 (p=0.535), hurst=0.54, acf1=-0.003 (p=0.547); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.066 @ obi_l1 h=1 (informational); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)

### PAIR_ANCHOR (orthogonal flag)
_2/2 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **OXYGEN_SHAKE_CHOCOLATE** ↔ OXYGEN_SHAKE_GARLIC  (corr=+0.65, coint_p=0.0655, STATIONARY)  primary=MR_TAKER
- **OXYGEN_SHAKE_GARLIC** ↔ OXYGEN_SHAKE_CHOCOLATE  (corr=+0.65, coint_p=0.0655, STATIONARY)  primary=NO_EDGE

### OBI_TAKER (orthogonal flag)
_5 follow signals, 0 fade signals (sign of IC determines strategy direction)._
- **OXYGEN_SHAKE_CHOCOLATE**  direction=follow  signal=obi_l1  h=1  IC=+0.057  primary=MR_TAKER
- **OXYGEN_SHAKE_MINT**  direction=follow  signal=obi_l1  h=1  IC=+0.055  primary=NO_EDGE
- **OXYGEN_SHAKE_GARLIC**  direction=follow  signal=obi_l1  h=1  IC=+0.066  primary=NO_EDGE
- **OXYGEN_SHAKE_MORNING_BREATH**  direction=follow  signal=obi_l1  h=1  IC=+0.051  primary=MR_TAKER
- **OXYGEN_SHAKE_EVENING_BREATH**  direction=follow  signal=obi_l1  h=1  IC=+0.054  primary=MR_TAKER

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- **OXYGEN_SHAKE_MINT**  primary=NO_EDGE  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 6, 'k_vol': 1.6624, 'gamma': 0.001061}
- **OXYGEN_SHAKE_GARLIC**  primary=NO_EDGE  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6919, 'gamma': 0.001133}
- **OXYGEN_SHAKE_MORNING_BREATH**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 6, 'k_vol': 1.6861, 'gamma': 0.001}
