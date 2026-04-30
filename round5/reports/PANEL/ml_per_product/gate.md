# PANEL — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `PANEL_1X2 | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.3021`, frac_clear = `0.040` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0290 → PASS
- C3 per-day PnL: D4=-15200.00 → FAIL
- C4 vol-regime PnL: q0=-1745.00, q1=-1730.00, q2=-2415.00, q3=-1150.00, q4=-8160.00 → FAIL — worst PnL in top trend quintile

### `PANEL_1X2 | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.9212`, frac_clear = `0.426` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0446 → PASS
- C3 per-day PnL: D4=-109370.00 → FAIL
- C4 vol-regime PnL: q0=-22355.00, q1=-26350.00, q2=-25620.00, q3=-20350.00, q4=-14695.00 → PASS

### `PANEL_1X2 | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.7578`, frac_clear = `0.124` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0497 → PASS
- C3 per-day PnL: D4=-47680.00 → FAIL
- C4 vol-regime PnL: q0=-7095.00, q1=-6940.00, q2=-8370.00, q3=-10660.00, q4=-14615.00 → FAIL — worst PnL in top trend quintile

### `PANEL_1X2 | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.3318`, frac_clear = `0.581` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0402 → PASS
- C3 per-day PnL: D4=-140780.00 → FAIL
- C4 vol-regime PnL: q0=-24025.00, q1=-31550.00, q2=-31700.00, q3=-34395.00, q4=-19110.00 → PASS

### `PANEL_1X4 | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.4667`, frac_clear = `0.291` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0303 → PASS
- C3 per-day PnL: D4=-44460.00 → FAIL
- C4 vol-regime PnL: q0=-10005.00, q1=-10715.00, q2=-7045.00, q3=-8845.00, q4=-7850.00 → PASS

### `PANEL_1X4 | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.0512`, frac_clear = `0.666` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1153 → FAIL
- C3 per-day PnL: D4=-103510.00 → FAIL
- C4 vol-regime PnL: q0=-22440.00, q1=-12015.00, q2=-24255.00, q3=-23900.00, q4=-20900.00 → PASS

### `PANEL_1X4 | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `0.1792`, frac_clear = `0.517` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0884 → PASS
- C3 per-day PnL: D4=-60580.00 → FAIL
- C4 vol-regime PnL: q0=-16685.00, q1=-11420.00, q2=-12540.00, q3=-10450.00, q4=-9485.00 → PASS

### `PANEL_1X4 | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.7315`, frac_clear = `0.777` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0880 → FAIL
- C3 per-day PnL: D4=-103960.00 → FAIL
- C4 vol-regime PnL: q0=-22210.00, q1=-15570.00, q2=-22670.00, q3=-22490.00, q4=-21020.00 → PASS

### `PANEL_2X2 | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.8264`, frac_clear = `0.225` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0187 → FAIL
- C3 per-day PnL: D4=-43090.00 → FAIL
- C4 vol-regime PnL: q0=-7545.00, q1=-6570.00, q2=-10875.00, q3=-10400.00, q4=-7700.00 → PASS

### `PANEL_2X2 | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.4726`, frac_clear = `0.675` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0012 → FAIL
- C3 per-day PnL: D4=-92520.00 → FAIL
- C4 vol-regime PnL: q0=-22345.00, q1=-19165.00, q2=-23080.00, q3=-16345.00, q4=-11585.00 → PASS

### `PANEL_2X2 | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.4543`, frac_clear = `0.294` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0791 → FAIL
- C3 per-day PnL: D4=-63660.00 → FAIL
- C4 vol-regime PnL: q0=-10600.00, q1=-11980.00, q2=-11705.00, q3=-13325.00, q4=-16050.00 → FAIL — worst PnL in top trend quintile

### `PANEL_2X2 | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.6622`, frac_clear = `0.758` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0072 → FAIL
- C3 per-day PnL: D4=-90820.00 → FAIL
- C4 vol-regime PnL: q0=-22460.00, q1=-14575.00, q2=-17175.00, q3=-16480.00, q4=-20130.00 → PASS

### `PANEL_2X4 | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.0940`, frac_clear = `0.104` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0160 → PASS
- C3 per-day PnL: D4=-33980.00 → FAIL
- C4 vol-regime PnL: q0=-6290.00, q1=-6500.00, q2=-6015.00, q3=-8305.00, q4=-6870.00 → PASS

### `PANEL_2X4 | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.3841`, frac_clear = `0.642` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0213 → FAIL
- C3 per-day PnL: D4=-125190.00 → FAIL
- C4 vol-regime PnL: q0=-20900.00, q1=-27225.00, q2=-30690.00, q3=-18035.00, q4=-28340.00 → PASS

### `PANEL_2X4 | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.2762`, frac_clear = `0.365` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.1158 → PASS
- C3 per-day PnL: D4=-63080.00 → FAIL
- C4 vol-regime PnL: q0=-10585.00, q1=-14580.00, q2=-12165.00, q3=-14495.00, q4=-11255.00 → PASS

### `PANEL_2X4 | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `7.2274`, frac_clear = `0.773` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0501 → FAIL
- C3 per-day PnL: D4=-129150.00 → FAIL
- C4 vol-regime PnL: q0=-18545.00, q1=-23360.00, q2=-34160.00, q3=-17745.00, q4=-35340.00 → FAIL — worst PnL in top trend quintile

### `PANEL_4X4 | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.5506`, frac_clear = `0.127` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0536 → FAIL
- C3 per-day PnL: D4=-37110.00 → FAIL
- C4 vol-regime PnL: q0=-10690.00, q1=-7235.00, q2=-7090.00, q3=-5160.00, q4=-6935.00 → PASS

### `PANEL_4X4 | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.9120`, frac_clear = `0.639` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0522 → FAIL
- C3 per-day PnL: D4=-112200.00 → FAIL
- C4 vol-regime PnL: q0=-20000.00, q1=-21035.00, q2=-19370.00, q3=-34755.00, q4=-17040.00 → PASS

### `PANEL_4X4 | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.8713`, frac_clear = `0.401` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0478 → FAIL
- C3 per-day PnL: D4=-80860.00 → FAIL
- C4 vol-regime PnL: q0=-17995.00, q1=-11565.00, q2=-16900.00, q3=-18780.00, q4=-15620.00 → PASS

### `PANEL_4X4 | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `6.2623`, frac_clear = `0.786` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0208 → FAIL
- C3 per-day PnL: D4=-109000.00 → FAIL
- C4 vol-regime PnL: q0=-19590.00, q1=-16880.00, q2=-23420.00, q3=-29705.00, q4=-19405.00 → PASS

## All folds (IC summary)

- `PANEL_1X2 | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0446`
- `PANEL_1X2 | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0325`
- `PANEL_1X2 | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0474`
- `PANEL_1X2 | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0028`
- `PANEL_1X2 | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0446`
- `PANEL_1X2 | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0290`
- `PANEL_1X2 | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0044`
- `PANEL_1X2 | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0608`
- `PANEL_1X2 | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0191`
- `PANEL_1X2 | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0290`
- `PANEL_1X2 | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0402`
- `PANEL_1X2 | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0228`
- `PANEL_1X2 | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0158`
- `PANEL_1X2 | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0264`
- `PANEL_1X2 | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0402`
- `PANEL_1X2 | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0497`
- `PANEL_1X2 | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0019`
- `PANEL_1X2 | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0684`
- `PANEL_1X2 | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0327`
- `PANEL_1X2 | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0497`
- `PANEL_1X4 | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.1153`
- `PANEL_1X4 | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0514`
- `PANEL_1X4 | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.1085`
- `PANEL_1X4 | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0722`
- `PANEL_1X4 | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.1153`
- `PANEL_1X4 | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0303`
- `PANEL_1X4 | fwd_ret h=50 ridge` [D2->D3]: IC = `0.1162`
- `PANEL_1X4 | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.1076`
- `PANEL_1X4 | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.1284`
- `PANEL_1X4 | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0303`
- `PANEL_1X4 | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0880`
- `PANEL_1X4 | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0299`
- `PANEL_1X4 | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1078`
- `PANEL_1X4 | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0488`
- `PANEL_1X4 | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0880`
- `PANEL_1X4 | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0884`
- `PANEL_1X4 | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1204`
- `PANEL_1X4 | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.1652`
- `PANEL_1X4 | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.1180`
- `PANEL_1X4 | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0884`
- `PANEL_2X2 | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0012`
- `PANEL_2X2 | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0132`
- `PANEL_2X2 | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.1409`
- `PANEL_2X2 | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0258`
- `PANEL_2X2 | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0012`
- `PANEL_2X2 | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0187`
- `PANEL_2X2 | fwd_ret h=50 ridge` [D2->D3]: IC = `0.1008`
- `PANEL_2X2 | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0778`
- `PANEL_2X2 | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0664`
- `PANEL_2X2 | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0187`
- `PANEL_2X2 | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0072`
- `PANEL_2X2 | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0197`
- `PANEL_2X2 | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0895`
- `PANEL_2X2 | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0473`
- `PANEL_2X2 | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0072`
- `PANEL_2X2 | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0791`
- `PANEL_2X2 | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0590`
- `PANEL_2X2 | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0614`
- `PANEL_2X2 | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0113`
- `PANEL_2X2 | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0791`
- `PANEL_2X4 | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0213`
- `PANEL_2X4 | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0288`
- `PANEL_2X4 | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0497`
- `PANEL_2X4 | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0405`
- `PANEL_2X4 | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0213`
- `PANEL_2X4 | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0160`
- `PANEL_2X4 | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0071`
- `PANEL_2X4 | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0096`
- `PANEL_2X4 | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0041`
- `PANEL_2X4 | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0160`
- `PANEL_2X4 | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0501`
- `PANEL_2X4 | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0503`
- `PANEL_2X4 | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0803`
- `PANEL_2X4 | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0698`
- `PANEL_2X4 | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0501`
- `PANEL_2X4 | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.1158`
- `PANEL_2X4 | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0026`
- `PANEL_2X4 | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0291`
- `PANEL_2X4 | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0609`
- `PANEL_2X4 | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.1158`
- `PANEL_4X4 | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0522`
- `PANEL_4X4 | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0363`
- `PANEL_4X4 | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0505`
- `PANEL_4X4 | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0430`
- `PANEL_4X4 | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0522`
- `PANEL_4X4 | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0536`
- `PANEL_4X4 | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0346`
- `PANEL_4X4 | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0019`
- `PANEL_4X4 | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0953`
- `PANEL_4X4 | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0536`
- `PANEL_4X4 | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0208`
- `PANEL_4X4 | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0563`
- `PANEL_4X4 | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0191`
- `PANEL_4X4 | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0069`
- `PANEL_4X4 | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0208`
- `PANEL_4X4 | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0478`
- `PANEL_4X4 | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0172`
- `PANEL_4X4 | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0257`
- `PANEL_4X4 | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0478`
- `PANEL_4X4 | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0478`
