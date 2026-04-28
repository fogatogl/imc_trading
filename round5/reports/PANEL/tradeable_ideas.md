# PANEL — Tradeable-Ideas Shortlist

_Auto-generated. Position limit per product = 10._

## Per-product candidates

- **PANEL_1X2**: MR_TAKER + OBI_TAKER[obi_l1@h=1, IC=+0.057]  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
- **PANEL_1X4**: NO_EDGE
- **PANEL_2X2**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
- **PANEL_2X4**: NO_EDGE + OBI_TAKER[obi_l3@h=1, IC=-0.044]
- **PANEL_4X4**: MR_TAKER  params={'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}

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
- PAIR_ANCHOR (flag): 0
- OBI_TAKER (flag): 2
- MM_CANDIDATE (flag): 0

MR_TAKER confidence breakdown:
- mr_confidence=high: 1
- mr_confidence=medium: 0
- mr_confidence=low: 2
- with FDR-passing IC (mr_ic_verified=True): 0
- with at least one contradiction signal: 1

### MR_TAKER
- **PANEL_1X2**  [low conf, 1 trigger(s)]  [+ OBI_TAKER follow obi_l1 h=1 IC=+0.057]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_vwap_50', 'ic_horizon': 0}
  - rationale: vwap_hurst=0.474<0.5; structural MR; no FDR-significant IC — anchor default = neg_zscore_vwap_50; mr_confidence=low (n_triggers=1, ic_verified=False); MR_CONTRADICTION: hurst=0.553>0.55 (persistent); vwap_acf_lag1=+0.027>0.01 (vwap positive autocorr)
- **PANEL_2X2**  [high conf, 4 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: vr_k5=0.975<0.985 (z=-1.95, p=0.0514); acf_lag1=-0.011<-0.005 (Bartlett p=0.0514); hurst=0.525<0.535; vwap_acf_lag1=-0.060<-0.01; structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=high (n_triggers=4, ic_verified=False)
- **PANEL_4X4**  [low conf, 1 trigger(s)]
  - params: {'ic_mr': nan, 'ic_signal': 'neg_zscore_mid_50', 'ic_horizon': 0}
  - rationale: acf_lag1=-0.006<-0.005 (Bartlett p=0.326); structural MR; no FDR-significant IC — anchor default = neg_zscore_mid_50; mr_confidence=low (n_triggers=1, ic_verified=False)

### NO_EDGE
- **PANEL_1X4**
  - rationale: no primary trigger fired; vr=0.987 (p=0.306), hurst=0.58, acf1=-0.002 (p=0.784); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=0.057; overall best |IC|=0.104 @ neg_zscore_mid_50 h=100 (informational)
- **PANEL_2X4**  [+ OBI_TAKER fade obi_l3 h=1 IC=-0.044]
  - rationale: no primary trigger fired; vr=0.986 (p=0.26), hurst=0.54, acf1=+0.000 (p=0.993); MR-IC|max[neg_z]|=nan, MOM-IC|max[mom10]|=nan; overall best |IC|=0.150 @ neg_spread h=1000 (informational)

### PAIR_ANCHOR (orthogonal flag)
- _(no products cleared the PAIR gate vs any family member)_

### OBI_TAKER (orthogonal flag)
_1 follow signals, 1 fade signals (sign of IC determines strategy direction)._
- **PANEL_1X2**  direction=follow  signal=obi_l1  h=1  IC=+0.057  primary=MR_TAKER
- **PANEL_2X4**  direction=fade  signal=obi_l3  h=1  IC=-0.044  primary=NO_EDGE

### MM_CANDIDATE (orthogonal flag — passive Template-A MM)
- _(no products passed the structural MM gate + Template-A sim with PnL > 0)_
