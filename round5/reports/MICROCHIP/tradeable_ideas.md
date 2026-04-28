# MICROCHIP — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **MICROCHIP_CIRCLE**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **MICROCHIP_OVAL**: MR_TAKER + PAIR_ANCHOR<->MICROCHIP_TRIANGLE  params={'ic_mr': 0.0970153021125336, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 1000}
- **MICROCHIP_SQUARE**: MR_TAKER + PAIR_ANCHOR<->MICROCHIP_RECTANGLE  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **MICROCHIP_RECTANGLE**: MR_TAKER + PAIR_ANCHOR<->MICROCHIP_SQUARE  params={'ic_mr': 0.0794160329430307, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 1000}
- **MICROCHIP_TRIANGLE**: MR_TAKER + PAIR_ANCHOR<->MICROCHIP_OVAL  params={'ic_mr': 0.1107518452057002, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}

## Within-family pair candidates (raw — see PAIR_ANCHOR flag for canonical)

- **PAIR_TRADE**: MICROCHIP_SQUARE ↔ MICROCHIP_RECTANGLE  corr=-0.88, coint_p=0.020

## Lead-lag candidates (lag=10 ticks)

- _(no |corr| >= 0.10 at lag=10)_

## Archetype assignment

_Primary archetypes (MR / MOMENTUM / RANDOM_WALK / NO_EDGE) are discriminant — exactly one per product. PAIR_ANCHOR, OBI_TAKER, and MM_CANDIDATE are orthogonal flags — any product can carry one or more on top of its primary._

Counts:
- MR_TAKER: 5
- MOMENTUM: 0
- RANDOM_WALK: 0
- NO_EDGE: 0
- PAIR_ANCHOR (flag): 4
- OBI_TAKER (flag): 0
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 2
- mr_confidence=medium: 0
- mr_confidence=low: 3
- with FDR-passing IC (mr_ic_verified=True): 3
- with at least one contradiction signal: 3

### MR_TAKER
- **MICROCHIP_CIRCLE**  [low conf, 1 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.005<-0.005 (Bartlett p=0.378); structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: vwap_acf_lag1=+0.039>0.01 (vwap positive autocorr)
- **MICROCHIP_OVAL**  [high conf, 2 trigger(s), IC-verified]  [+ PAIR_ANCHOR with MICROCHIP_TRIANGLE (stationary)]
  - params: {'ic_mr': 0.0970153021125336, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 1000}
  - rationale: acf_lag1=-0.007<-0.005 (Bartlett p=0.219); vwap_hurst=0.466<0.5; max |IC[neg_zscore_vwap_50]|=0.097 @ h=1000  (t=+2.91, p=0.00367, FDR-pass); mr_confidence=high (n_triggers=2, ic_verified=True)
- **MICROCHIP_SQUARE**  [high conf, 3 trigger(s)]  [+ PAIR_ANCHOR with MICROCHIP_RECTANGLE (stationary)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.960<0.985 (z=-3.18, p=0.00145); acf_lag1=-0.024<-0.005 (Bartlett p=3.51e-05); vwap_acf_lag1=-0.014<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=high (n_triggers=3, ic_verified=False)
- **MICROCHIP_RECTANGLE**  [low conf, 2 trigger(s), IC-verified]  [+ PAIR_ANCHOR with MICROCHIP_SQUARE (stationary)]
  - params: {'ic_mr': 0.0794160329430307, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 1000}
  - rationale: vwap_hurst=0.456<0.5; vwap_acf_lag1=-0.044<-0.01; max |IC[neg_zscore_vwap_50]|=0.079 @ h=1000  (t=+3.42, p=0.000624, FDR-pass); mr_confidence=low (n_triggers=2, ic_verified=True); MR_CONTRADICTION: vr_k5=1.007>1.005 (trending signal)
- **MICROCHIP_TRIANGLE**  [low conf, 4 trigger(s), IC-verified]  [+ PAIR_ANCHOR with MICROCHIP_OVAL (stationary)]
  - params: {'ic_mr': 0.1107518452057002, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 1000}
  - rationale: vr_k5=0.972<0.985 (z=-2.20, p=0.0275); acf_lag1=-0.007<-0.005 (Bartlett p=0.233); vwap_hurst=0.462<0.5; vwap_acf_lag1=-0.033<-0.01; max |IC[neg_zscore_mid_50]|=0.111 @ h=1000  (t=+4.46, p=8.25e-06, FDR-pass); mr_confidence=low (n_triggers=4, ic_verified=True); MR_CONTRADICTION: hurst=0.565>0.55 (persistent)

### PAIR_ANCHOR (orthogonal flag)
_4/4 pairs have stationary residual (suitable for fixed-β hedge); the rest need rolling β._
- **MICROCHIP_OVAL** ↔ MICROCHIP_TRIANGLE  (corr=+0.87, coint_p=0.0526, STATIONARY)  primary=MR_TAKER
- **MICROCHIP_SQUARE** ↔ MICROCHIP_RECTANGLE  (corr=-0.88, coint_p=0.0196, STATIONARY)  primary=MR_TAKER
- **MICROCHIP_RECTANGLE** ↔ MICROCHIP_SQUARE  (corr=-0.88, coint_p=0.0196, STATIONARY)  primary=MR_TAKER
- **MICROCHIP_TRIANGLE** ↔ MICROCHIP_OVAL  (corr=+0.87, coint_p=0.0526, STATIONARY)  primary=MR_TAKER

### OBI_TAKER (orthogonal flag)
- _(no products cleared the OBI gate with FDR-pass at h ∈ {1, 10})_

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
