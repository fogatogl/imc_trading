# UV_VISOR — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **UV_VISOR_AMBER**: MR_TAKER + PAIR_ANCHOR<->UV_VISOR_MAGENTA + OBI_TAKER[obi_l1@h=1, IC=+0.059]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **UV_VISOR_MAGENTA**: MR_TAKER + PAIR_ANCHOR<->UV_VISOR_AMBER + OBI_TAKER[obi_l1@h=1, IC=+0.059]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **UV_VISOR_ORANGE**: NO_EDGE + PAIR_ANCHOR<->UV_VISOR_AMBER + OBI_TAKER[obi_l1@h=1, IC=+0.058]
- **UV_VISOR_RED**: NO_EDGE + OBI_TAKER[obi_l1@h=1, IC=+0.059]
- **UV_VISOR_YELLOW**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.061]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}

## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)

- **PAIR_TRADE**: UV_VISOR_AMBER ↔ UV_VISOR_MAGENTA  corr=-0.87, coint_p=0.042

## Lead-lag candidates (lag=10 ticks)

- _(no |corr| >= 0.10 at lag=10)_

## Archetype assignment

_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, and MM_CANDIDATE are orthogonal flags — any product can carry one or more on top of its primary._

Counts:
- MR_TAKER: 3
- MOMENTUM: 0
- RANDOM_WALK: 0
- NO_EDGE: 2
- PAIR_ANCHOR (flag): 3
- OBI_TAKER (flag): 5
- MM_CANDIDATE (flag): 3

MR_TAKER confidence breakdown:
- mr_confidence=high: 0
- mr_confidence=medium: 1
- mr_confidence=low: 2
- with FDR-passing IC (mr_ic_verified=True): 0
- with at least one contradiction signal: 2

### MR_TAKER
- **UV_VISOR_AMBER**  [low conf, 1 trigger(s)]  [+ PAIR_ANCHOR with UV_VISOR_MAGENTA (stationary)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.059]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vwap_hurst=0.441<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: hurst=0.556>0.55 (persistent)
- **UV_VISOR_MAGENTA**  [medium conf, 2 trigger(s)]  [+ PAIR_ANCHOR with UV_VISOR_AMBER (stationary)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.059]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: hurst=0.524<0.535; vwap_acf_lag1=-0.065<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=medium (n_triggers=2, ic_verified=False); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **UV_VISOR_YELLOW**  [low conf, 2 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.061]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: hurst=0.529<0.535; vwap_acf_lag1=-0.049<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=2, ic_verified=False); MR_CONTRADICTION: vr_k5=1.005>1.005 (trending signal); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)

### NO_EDGE
- **UV_VISOR_ORANGE**  [+ PAIR_ANCHOR with UV_VISOR_AMBER (non-stat)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.058]  [+ MM_CANDIDATE untested pnl=+0 fills=0]
  - rationale: no primary trigger fired; vr=1.010 (p=0.449), hurst=0.54, acf1=+0.002 (p=0.767); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.122 @ neg_spread h=1000 (informational); MM_SIM_UNTESTED pnl=+0.00, fills=0 (sparse trades; structural gate authoritative)
- **UV_VISOR_RED**  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.059]
  - rationale: no primary trigger fired; vr=0.987 (p=0.303), hurst=0.56, acf1=-0.003 (p=0.593); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.143 @ neg_spread h=1000 (informational)

### PAIR_ANCHOR (orthogonal flag)
_2/3 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **UV_VISOR_AMBER** ↔ UV_VISOR_MAGENTA  (corr=-0.87, coint_p=0.0416, STATIONARY)  primary=MR_TAKER
- **UV_VISOR_MAGENTA** ↔ UV_VISOR_AMBER  (corr=-0.87, coint_p=0.0416, STATIONARY)  primary=MR_TAKER
- **UV_VISOR_ORANGE** ↔ UV_VISOR_AMBER  (corr=-0.71, coint_p=0.826, non-stat)  primary=NO_EDGE

### OBI_TAKER (orthogonal flag)
_5 follow signals, 0 fade signals (sign of IC determines strategy direction)._
- **UV_VISOR_AMBER**  direction=follow  signal=obi_l1  h=1  IC=+0.059  primary=MR_TAKER
- **UV_VISOR_MAGENTA**  direction=follow  signal=obi_l1  h=1  IC=+0.059  primary=MR_TAKER
- **UV_VISOR_ORANGE**  direction=follow  signal=obi_l1  h=1  IC=+0.058  primary=NO_EDGE
- **UV_VISOR_RED**  direction=follow  signal=obi_l1  h=1  IC=+0.059  primary=NO_EDGE
- **UV_VISOR_YELLOW**  direction=follow  signal=obi_l1  h=1  IC=+0.061  primary=MR_TAKER

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- **UV_VISOR_MAGENTA**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6754, 'gamma': 0.001118}
- **UV_VISOR_ORANGE**  primary=NO_EDGE  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 6, 'k_vol': 1.6686, 'gamma': 0.001}
- **UV_VISOR_YELLOW**  primary=MR_TAKER  sim_pnl=+0.00  fills=0  params={'min_edge_ticks': 7, 'k_vol': 1.6778, 'gamma': 0.001}
