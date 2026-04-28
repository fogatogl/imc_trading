# GALAXY_SOUNDS — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **GALAXY_SOUNDS_DARK_MATTER**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.052]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **GALAXY_SOUNDS_BLACK_HOLES**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.059]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **GALAXY_SOUNDS_PLANETARY_RINGS**: NO_EDGE + OBI_TAKER[obi_l1@h=1, IC=+0.059]
- **GALAXY_SOUNDS_SOLAR_WINDS**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.065]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **GALAXY_SOUNDS_SOLAR_FLAMES**: MR_TAKER + OBI_TAKER[obi_l3@h=1, IC=-0.054]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}

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
- OBI_TAKER (flag): 5
- MM_CANDIDATE (flag): 5

MR_TAKER confidence breakdown:
- mr_confidence=high: 1
- mr_confidence=medium: 1
- mr_confidence=low: 2
- with FDR-passing IC (mr_ic_verified=True): 0
- with at least one contradiction signal: 2

### MR_TAKER
- **GALAXY_SOUNDS_DARK_MATTER**  [low conf, 5 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.052]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.012<-0.005 (Bartlett p=0.0365); hurst=0.530<0.535; adf_p_mid=0.0705<0.1; vwap_hurst=0.493<0.5; vwap_adf_p=0.0785<0.1; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=5, ic_verified=False); MR_CONTRADICTION: vwap_acf_lag1=+0.011>0.01 (vwap positive autocorr); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **GALAXY_SOUNDS_BLACK_HOLES**  [medium conf, 2 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.059]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.981<0.985 (z=-1.51, p=0.132); acf_lag1=-0.017<-0.005 (Bartlett p=0.00407); structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=medium (n_triggers=2, ic_verified=False); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **GALAXY_SOUNDS_SOLAR_WINDS**  [low conf, 3 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.065]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.982<0.985 (z=-1.45, p=0.147); acf_lag1=-0.008<-0.005 (Bartlett p=0.176); hurst=0.534<0.535; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=3, ic_verified=False); MR_CONTRADICTION: vwap_acf_lag1=+0.011>0.01 (vwap positive autocorr); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **GALAXY_SOUNDS_SOLAR_FLAMES**  [high conf, 5 trigger(s)]  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.054]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.981<0.985 (z=-1.47, p=0.141); acf_lag1=-0.012<-0.005 (Bartlett p=0.0356); adf_p_mid=0.0639<0.1; vwap_adf_p=0.0353<0.1; vwap_acf_lag1=-0.017<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=5, ic_verified=False); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)

### NO_EDGE
- **GALAXY_SOUNDS_PLANETARY_RINGS**  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.059]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - rationale: no primary trigger fired; vr=1.003 (p=0.809), hurst=0.54, acf1=-0.004 (p=0.488); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.059 @ obi_l1 h=1 (informational); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)

### PAIR_ANCHOR (orthogonal flag)
- _(no products cleared the PAIR gate vs any family member)_

### OBI_TAKER (orthogonal flag)
_4 follow signals, 1 fade signals (sign of IC determines strategy direction)._
- **GALAXY_SOUNDS_DARK_MATTER**  direction=follow  signal=obi_l1  h=1  IC=+0.052  primary=MR_TAKER
- **GALAXY_SOUNDS_BLACK_HOLES**  direction=follow  signal=obi_l1  h=1  IC=+0.059  primary=MR_TAKER
- **GALAXY_SOUNDS_PLANETARY_RINGS**  direction=follow  signal=obi_l1  h=1  IC=+0.059  primary=NO_EDGE
- **GALAXY_SOUNDS_SOLAR_WINDS**  direction=follow  signal=obi_l1  h=1  IC=+0.065  primary=MR_TAKER
- **GALAXY_SOUNDS_SOLAR_FLAMES**  direction=fade  signal=obi_l3  h=1  IC=-0.054  primary=MR_TAKER

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- **GALAXY_SOUNDS_DARK_MATTER**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 6, 'k_vol': 1.6525, 'gamma': 0.001}
- **GALAXY_SOUNDS_BLACK_HOLES**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.7049, 'gamma': 0.001238}
- **GALAXY_SOUNDS_PLANETARY_RINGS**  primary=NO_EDGE  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6867, 'gamma': 0.001053}
- **GALAXY_SOUNDS_SOLAR_WINDS**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6735, 'gamma': 0.001115}
- **GALAXY_SOUNDS_SOLAR_FLAMES**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6656, 'gamma': 0.001103}
