# TRANSLATOR — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.3867`, frac_clear = `0.116` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0370 → PASS
- C3 per-day PnL: D4=-33660.00 → FAIL
- C4 vol-regime PnL: q0=-4785.00, q1=-7265.00, q2=-5110.00, q3=-10085.00, q4=-6415.00 → PASS

### `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.0910`, frac_clear = `0.707` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0516 → PASS
- C3 per-day PnL: D4=-94240.00 → FAIL
- C4 vol-regime PnL: q0=-22140.00, q1=-17020.00, q2=-13860.00, q3=-24895.00, q4=-16325.00 → PASS

### `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.7161`, frac_clear = `0.257` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0099 → FAIL
- C3 per-day PnL: D4=-48730.00 → FAIL
- C4 vol-regime PnL: q0=-7885.00, q1=-9205.00, q2=-8445.00, q3=-15205.00, q4=-7990.00 → PASS

### `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.0148`, frac_clear = `0.836` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0459 → PASS
- C3 per-day PnL: D4=-75230.00 → FAIL
- C4 vol-regime PnL: q0=-17050.00, q1=-16430.00, q2=-10325.00, q3=-21225.00, q4=-10200.00 → PASS

### `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.8647`, frac_clear = `0.058` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0053 → PASS
- C3 per-day PnL: D4=-19140.00 → FAIL
- C4 vol-regime PnL: q0=-4750.00, q1=-4115.00, q2=-4630.00, q3=-2535.00, q4=-3110.00 → PASS

### `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.2670`, frac_clear = `0.602` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0289 → PASS
- C3 per-day PnL: D4=-97810.00 → FAIL
- C4 vol-regime PnL: q0=-17045.00, q1=-22960.00, q2=-19740.00, q3=-19690.00, q4=-18375.00 → PASS

### `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.8203`, frac_clear = `0.245` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0425 → FAIL
- C3 per-day PnL: D4=-63370.00 → FAIL
- C4 vol-regime PnL: q0=-13045.00, q1=-14265.00, q2=-11900.00, q3=-13445.00, q4=-10715.00 → PASS

### `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.2040`, frac_clear = `0.734` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0139 → PASS
- C3 per-day PnL: D4=-108130.00 → FAIL
- C4 vol-regime PnL: q0=-9825.00, q1=-24095.00, q2=-26855.00, q3=-26395.00, q4=-20960.00 → PASS

### `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.6369`, frac_clear = `0.118` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.1164 → PASS
- C3 per-day PnL: D4=-30250.00 → FAIL
- C4 vol-regime PnL: q0=-5740.00, q1=-3595.00, q2=-5825.00, q3=-3365.00, q4=-11725.00 → FAIL — worst PnL in top trend quintile

### `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.3915`, frac_clear = `0.660` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0357 → FAIL
- C3 per-day PnL: D4=-90120.00 → FAIL
- C4 vol-regime PnL: q0=-19670.00, q1=-17265.00, q2=-20155.00, q3=-16350.00, q4=-16680.00 → PASS

### `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.0501`, frac_clear = `0.373` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0318 → PASS
- C3 per-day PnL: D4=-59390.00 → FAIL
- C4 vol-regime PnL: q0=-14730.00, q1=-14135.00, q2=-10855.00, q3=-11365.00, q4=-8305.00 → PASS

### `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `6.3431`, frac_clear = `0.774` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0042 → FAIL
- C3 per-day PnL: D4=-85460.00 → FAIL
- C4 vol-regime PnL: q0=-20895.00, q1=-20960.00, q2=-16085.00, q3=-11220.00, q4=-16300.00 → PASS

### `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.4445`, frac_clear = `0.449` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0649 → FAIL
- C3 per-day PnL: D4=-40740.00 → FAIL
- C4 vol-regime PnL: q0=-11580.00, q1=-5535.00, q2=-7145.00, q3=-9740.00, q4=-6740.00 → PASS

### `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.6242`, frac_clear = `0.723` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0297 → FAIL
- C3 per-day PnL: D4=-70110.00 → FAIL
- C4 vol-regime PnL: q0=-12935.00, q1=-14720.00, q2=-19145.00, q3=-15365.00, q4=-7945.00 → PASS

### `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `2.1091`, frac_clear = `0.648` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0899 → FAIL
- C3 per-day PnL: D4=-55130.00 → FAIL
- C4 vol-regime PnL: q0=-8805.00, q1=-11020.00, q2=-18610.00, q3=-10335.00, q4=-6360.00 → PASS

### `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `8.3020`, frac_clear = `0.830` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1203 → FAIL
- C3 per-day PnL: D4=-75890.00 → FAIL
- C4 vol-regime PnL: q0=-14700.00, q1=-17830.00, q2=-18435.00, q3=-14995.00, q4=-9930.00 → PASS

### `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.0377`, frac_clear = `0.099` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0176 → PASS
- C3 per-day PnL: D4=-20180.00 → FAIL
- C4 vol-regime PnL: q0=-2120.00, q1=-5470.00, q2=-3855.00, q3=-3805.00, q4=-4930.00 → PASS

### `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.2835`, frac_clear = `0.589` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0744 → PASS
- C3 per-day PnL: D4=-98980.00 → FAIL
- C4 vol-regime PnL: q0=-11200.00, q1=-20300.00, q2=-18770.00, q3=-19880.00, q4=-28830.00 → FAIL — worst PnL in top trend quintile

### `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.0681`, frac_clear = `0.236` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0149 → FAIL
- C3 per-day PnL: D4=-50250.00 → FAIL
- C4 vol-regime PnL: q0=-13985.00, q1=-13065.00, q2=-9540.00, q3=-4950.00, q4=-8710.00 → PASS

### `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.8595`, frac_clear = `0.705` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0672 → PASS
- C3 per-day PnL: D4=-84020.00 → FAIL
- C4 vol-regime PnL: q0=-13570.00, q1=-25470.00, q2=-8665.00, q3=-10315.00, q4=-26000.00 → FAIL — worst PnL in top trend quintile

## All folds (IC summary)

- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0516`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0480`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0035`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.1436`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0516`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0370`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0448`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0059`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0378`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0370`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0459`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0512`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0851`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.1466`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0459`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0099`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0021`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0094`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0314`
- `TRANSLATOR_ASTRO_BLACK | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0099`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0289`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0318`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0467`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0397`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0289`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0053`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0403`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0328`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0217`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0053`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0139`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0618`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0139`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0793`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0139`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0425`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0517`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0377`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0841`
- `TRANSLATOR_ECLIPSE_CHARCOAL | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0425`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0357`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0466`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0647`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0437`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0357`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.1164`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0093`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0390`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0558`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.1164`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0042`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0513`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0154`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0068`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0042`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0318`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0648`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0139`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0824`
- `TRANSLATOR_GRAPHITE_MIST | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0318`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0297`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0142`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0785`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0150`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0297`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0649`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` [D2->D3]: IC = `0.1357`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0051`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0662`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0649`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1203`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0580`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1311`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0102`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1203`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0899`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` [D2->D3]: IC = `0.2425`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0234`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0847`
- `TRANSLATOR_SPACE_GRAY | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0899`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0744`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0409`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0361`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0147`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0744`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0176`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0400`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0309`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0573`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0176`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0672`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.1137`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0334`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0640`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0672`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0149`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0226`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0417`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0018`
- `TRANSLATOR_VOID_BLUE | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0149`
