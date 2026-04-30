# MICROCHIP — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.5799`, frac_clear = `0.064` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0134 → FAIL
- C3 per-day PnL: D4=-25020.00 → FAIL
- C4 vol-regime PnL: q0=-10815.00, q1=-4645.00, q2=-3140.00, q3=-2290.00, q4=-4130.00 → PASS

### `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.7818`, frac_clear = `0.628` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0113 → PASS
- C3 per-day PnL: D4=-98130.00 → FAIL
- C4 vol-regime PnL: q0=-25370.00, q1=-12810.00, q2=-22430.00, q3=-21965.00, q4=-15555.00 → PASS

### `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.4533`, frac_clear = `0.304` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0869 → FAIL
- C3 per-day PnL: D4=-62530.00 → FAIL
- C4 vol-regime PnL: q0=-15710.00, q1=-14480.00, q2=-12215.00, q3=-9510.00, q4=-10615.00 → PASS

### `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.3501`, frac_clear = `0.767` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0399 → PASS
- C3 per-day PnL: D4=-91820.00 → FAIL
- C4 vol-regime PnL: q0=-15935.00, q1=-14135.00, q2=-28575.00, q3=-17810.00, q4=-15365.00 → PASS

### `MICROCHIP_OVAL | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.2930`, frac_clear = `0.454` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0287 → PASS
- C3 per-day PnL: D4=-142160.00 → FAIL
- C4 vol-regime PnL: q0=-23700.00, q1=-27715.00, q2=-26565.00, q3=-33315.00, q4=-30865.00 → PASS

### `MICROCHIP_OVAL | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `7.3046`, frac_clear = `0.841` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0439 → PASS
- C3 per-day PnL: D4=-63930.00 → FAIL
- C4 vol-regime PnL: q0=-16575.00, q1=-14415.00, q2=-10385.00, q3=-13340.00, q4=-9215.00 → PASS

### `MICROCHIP_OVAL | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `2.2833`, frac_clear = `0.715` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0856 → PASS
- C3 per-day PnL: D4=-108130.00 → FAIL
- C4 vol-regime PnL: q0=-14305.00, q1=-16745.00, q2=-21775.00, q3=-26875.00, q4=-28430.00 → FAIL — worst PnL in top trend quintile

### `MICROCHIP_OVAL | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `13.8508`, frac_clear = `0.904` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0106 → PASS
- C3 per-day PnL: D4=-72070.00 → FAIL
- C4 vol-regime PnL: q0=-14650.00, q1=-18360.00, q2=-12335.00, q3=-17080.00, q4=-9645.00 → PASS

### `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.8480`, frac_clear = `0.390` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0027 → FAIL
- C3 per-day PnL: D4=-59390.00 → FAIL
- C4 vol-regime PnL: q0=-16155.00, q1=-12570.00, q2=-11190.00, q3=-8830.00, q4=-10645.00 → PASS

### `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.3575`, frac_clear = `0.744` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0037 → PASS
- C3 per-day PnL: D4=-91570.00 → FAIL
- C4 vol-regime PnL: q0=-12440.00, q1=-23990.00, q2=-13190.00, q3=-20500.00, q4=-21450.00 → PASS

### `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `1.0914`, frac_clear = `0.590` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0024 → PASS
- C3 per-day PnL: D4=-75790.00 → FAIL
- C4 vol-regime PnL: q0=-19340.00, q1=-17160.00, q2=-17205.00, q3=-11710.00, q4=-10375.00 → PASS

### `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.9325`, frac_clear = `0.845` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0092 → FAIL
- C3 per-day PnL: D4=-104480.00 → FAIL
- C4 vol-regime PnL: q0=-19455.00, q1=-18300.00, q2=-17435.00, q3=-25300.00, q4=-23990.00 → PASS

### `MICROCHIP_SQUARE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `1.4337`, frac_clear = `0.598` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0891 → FAIL
- C3 per-day PnL: D4=-71180.00 → FAIL
- C4 vol-regime PnL: q0=-10665.00, q1=-16780.00, q2=-11235.00, q3=-20325.00, q4=-12175.00 → PASS

### `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `8.9320`, frac_clear = `0.786` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0226 → FAIL
- C3 per-day PnL: D4=-145760.00 → FAIL
- C4 vol-regime PnL: q0=-21675.00, q1=-17540.00, q2=-43265.00, q3=-37300.00, q4=-25980.00 → PASS

### `MICROCHIP_SQUARE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `7.9390`, frac_clear = `0.831` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0111 → FAIL
- C3 per-day PnL: D4=-51550.00 → FAIL
- C4 vol-regime PnL: q0=-3980.00, q1=+4615.00, q2=-23810.00, q3=-14950.00, q4=-13425.00 → PASS

### `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `19.5748`, frac_clear = `0.875` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0332 → FAIL
- C3 per-day PnL: D4=-123680.00 → FAIL
- C4 vol-regime PnL: q0=-25425.00, q1=-21460.00, q2=-31085.00, q3=-28575.00, q4=-17135.00 → PASS

### `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.3325`, frac_clear = `0.463` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0188 → FAIL
- C3 per-day PnL: D4=-119640.00 → FAIL
- C4 vol-regime PnL: q0=-30560.00, q1=-22435.00, q2=-20775.00, q3=-22165.00, q4=-23705.00 → PASS

### `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.5664`, frac_clear = `0.784` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1006 → FAIL
- C3 per-day PnL: D4=-99990.00 → FAIL
- C4 vol-regime PnL: q0=-11505.00, q1=-27570.00, q2=-20525.00, q3=-18055.00, q4=-22335.00 → PASS

### `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `1.0466`, frac_clear = `0.601` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0248 → PASS
- C3 per-day PnL: D4=-119510.00 → FAIL
- C4 vol-regime PnL: q0=-26160.00, q1=-20340.00, q2=-20220.00, q3=-28200.00, q4=-24590.00 → PASS

### `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `11.5697`, frac_clear = `0.858` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0260 → PASS
- C3 per-day PnL: D4=-87550.00 → FAIL
- C4 vol-regime PnL: q0=-4080.00, q1=-22415.00, q2=-25425.00, q3=-14850.00, q4=-20780.00 → PASS

## All folds (IC summary)

- `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0113`
- `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0343`
- `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0206`
- `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0161`
- `MICROCHIP_CIRCLE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0113`
- `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0134`
- `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0581`
- `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0427`
- `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0138`
- `MICROCHIP_CIRCLE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0134`
- `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0399`
- `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0280`
- `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0121`
- `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0766`
- `MICROCHIP_CIRCLE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0399`
- `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0869`
- `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0872`
- `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.1287`
- `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0783`
- `MICROCHIP_CIRCLE | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0869`
- `MICROCHIP_OVAL | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0439`
- `MICROCHIP_OVAL | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0371`
- `MICROCHIP_OVAL | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0054`
- `MICROCHIP_OVAL | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0293`
- `MICROCHIP_OVAL | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0439`
- `MICROCHIP_OVAL | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0287`
- `MICROCHIP_OVAL | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0045`
- `MICROCHIP_OVAL | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0072`
- `MICROCHIP_OVAL | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0293`
- `MICROCHIP_OVAL | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0287`
- `MICROCHIP_OVAL | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0106`
- `MICROCHIP_OVAL | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0536`
- `MICROCHIP_OVAL | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0621`
- `MICROCHIP_OVAL | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0029`
- `MICROCHIP_OVAL | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0106`
- `MICROCHIP_OVAL | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0856`
- `MICROCHIP_OVAL | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0168`
- `MICROCHIP_OVAL | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0136`
- `MICROCHIP_OVAL | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0313`
- `MICROCHIP_OVAL | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0856`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0037`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0070`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0212`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0343`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0037`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0027`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0820`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0392`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0615`
- `MICROCHIP_RECTANGLE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0027`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0092`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0935`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0103`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0399`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0092`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0024`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0599`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0082`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0553`
- `MICROCHIP_RECTANGLE | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0024`
- `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0226`
- `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0870`
- `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0133`
- `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0807`
- `MICROCHIP_SQUARE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0226`
- `MICROCHIP_SQUARE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0891`
- `MICROCHIP_SQUARE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0591`
- `MICROCHIP_SQUARE | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0481`
- `MICROCHIP_SQUARE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0390`
- `MICROCHIP_SQUARE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0891`
- `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0332`
- `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0567`
- `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0452`
- `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0543`
- `MICROCHIP_SQUARE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0332`
- `MICROCHIP_SQUARE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0111`
- `MICROCHIP_SQUARE | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0092`
- `MICROCHIP_SQUARE | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0369`
- `MICROCHIP_SQUARE | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0168`
- `MICROCHIP_SQUARE | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0111`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.1006`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0190`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0696`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0999`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.1006`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0188`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0538`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0305`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0049`
- `MICROCHIP_TRIANGLE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0188`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0260`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0024`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0465`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0221`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0260`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0248`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0330`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0279`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0012`
- `MICROCHIP_TRIANGLE | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0248`
