# SNACKPACK — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **SNACKPACK_CHOCOLATE**: MR_TAKER + PAIR_ANCHOR<->SNACKPACK_VANILLA + OBI_TAKER[obi_l1@h=1, IC=+0.118]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **SNACKPACK_VANILLA**: MR_TAKER + PAIR_ANCHOR<->SNACKPACK_CHOCOLATE + OBI_TAKER[obi_l1@h=1, IC=+0.114]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **SNACKPACK_RASPBERRY**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.102]  params={'ic_mr': 0.0513495999381919, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
- **SNACKPACK_STRAWBERRY**: MR_TAKER + PAIR_ANCHOR<->SNACKPACK_CHOCOLATE + OBI_TAKER[obi_l1@h=1, IC=+0.097]  params={'ic_mr': 0.0527720047436206, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
- **SNACKPACK_PISTACHIO**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.132]  params={'ic_mr': 0.0520522067277868, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}

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
- OBI_TAKER (flag): 5
- MM_CANDIDATE (flag): 4

MR_TAKER confidence breakdown:
- mr_confidence=high: 5
- mr_confidence=medium: 0
- mr_confidence=low: 0
- with FDR-passing IC (mr_ic_verified=True): 3
- with at least one contradiction signal: 0

### MR_TAKER
- **SNACKPACK_CHOCOLATE**  [high conf, 6 trigger(s)]  [+ PAIR_ANCHOR with SNACKPACK_VANILLA (non-stat)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.118]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.950<0.985 (z=-3.94, p=8.09e-05); acf_lag1=-0.031<-0.005 (Bartlett p=8.84e-08); adf_p_mid=0.0677<0.1; vwap_hurst=0.456<0.5; vwap_adf_p=0.053<0.1; vwap_acf_lag1=-0.033<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=high (n_triggers=6, ic_verified=False); MM_SIM_FAIL pnl=-1364.00, fills=1
- **SNACKPACK_VANILLA**  [high conf, 6 trigger(s)]  [+ PAIR_ANCHOR with SNACKPACK_CHOCOLATE (non-stat)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.114]  [+ MM_CANDIDATE confirmed pnl=+1350 fills=1]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.952<0.985 (z=-3.81, p=0.000141); acf_lag1=-0.027<-0.005 (Bartlett p=3.46e-06); adf_p_mid=0.0376<0.1; vwap_hurst=0.485<0.5; vwap_adf_p=0.0273<0.1; vwap_acf_lag1=-0.082<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=high (n_triggers=6, ic_verified=False); MM_SIM_PASS pnl=+1350.44, fills=1
- **SNACKPACK_RASPBERRY**  [high conf, 6 trigger(s), IC-verified]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.102]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': 0.0513495999381919, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
  - rationale: vr_k5=0.983<0.985 (z=-1.38, p=0.168); acf_lag1=-0.017<-0.005 (Bartlett p=0.0034); adf_p_mid=0.00136<0.1; vwap_hurst=0.459<0.5; vwap_adf_p=0.00754<0.1; vwap_acf_lag1=-0.016<-0.01; max |IC[neg_zscore_mid_50]|=0.051 @ h=1000  (t=+2.51, p=0.012, FDR-pass); mr_confidence=high (n_triggers=6, ic_verified=True); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **SNACKPACK_STRAWBERRY**  [high conf, 2 trigger(s), IC-verified]  [+ PAIR_ANCHOR with SNACKPACK_CHOCOLATE (stationary)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.097]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': 0.0527720047436206, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
  - rationale: acf_lag1=-0.014<-0.005 (Bartlett p=0.0143); vwap_hurst=0.454<0.5; max |IC[neg_zscore_mid_50]|=0.053 @ h=1000  (t=+2.47, p=0.0135, FDR-pass); mr_confidence=high (n_triggers=2, ic_verified=True); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **SNACKPACK_PISTACHIO**  [high conf, 6 trigger(s), IC-verified]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.132]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': 0.0520522067277868, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
  - rationale: vr_k5=0.972<0.985 (z=-2.22, p=0.0263); acf_lag1=-0.025<-0.005 (Bartlett p=1.27e-05); adf_p_mid=0.0781<0.1; vwap_hurst=0.464<0.5; vwap_adf_p=0.0895<0.1; vwap_acf_lag1=-0.051<-0.01; max |IC[neg_zscore_mid_50]|=0.052 @ h=1000  (t=+2.62, p=0.00868, FDR-pass); mr_confidence=high (n_triggers=6, ic_verified=True); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)

### PAIR_ANCHOR (orthogonal flag)
_1/3 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **SNACKPACK_CHOCOLATE** ↔ SNACKPACK_VANILLA  (corr=-0.93, coint_p=0.462, non-stat)  primary=MR_TAKER
- **SNACKPACK_VANILLA** ↔ SNACKPACK_CHOCOLATE  (corr=-0.93, coint_p=0.462, non-stat)  primary=MR_TAKER
- **SNACKPACK_STRAWBERRY** ↔ SNACKPACK_CHOCOLATE  (corr=-0.54, coint_p=0.0356, STATIONARY)  primary=MR_TAKER

### OBI_TAKER (orthogonal flag)
_5 follow signals, 0 fade signals (sign of IC determines strategy direction)._
- **SNACKPACK_CHOCOLATE**  direction=follow  signal=obi_l1  h=1  IC=+0.118  primary=MR_TAKER
- **SNACKPACK_VANILLA**  direction=follow  signal=obi_l1  h=1  IC=+0.114  primary=MR_TAKER
- **SNACKPACK_RASPBERRY**  direction=follow  signal=obi_l1  h=1  IC=+0.102  primary=MR_TAKER
- **SNACKPACK_STRAWBERRY**  direction=follow  signal=obi_l1  h=1  IC=+0.097  primary=MR_TAKER
- **SNACKPACK_PISTACHIO**  direction=follow  signal=obi_l1  h=1  IC=+0.132  primary=MR_TAKER

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- **SNACKPACK_VANILLA**  primary=MR_TAKER  sim_pnl=+1350.44  fills=1  params={'min_edge_ticks': 8, 'k_vol': 1.6564, 'gamma': 0.001}
- **SNACKPACK_RASPBERRY**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 8, 'k_vol': 1.6516, 'gamma': 0.00103}
- **SNACKPACK_STRAWBERRY**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 9, 'k_vol': 1.648, 'gamma': 0.001089}
- **SNACKPACK_PISTACHIO**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 8, 'k_vol': 1.6486, 'gamma': 0.001057}
