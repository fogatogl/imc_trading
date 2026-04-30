# ROBOT — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `ROBOT_DISHES | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.1242`, frac_clear = `0.154` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0119 → FAIL
- C3 per-day PnL: D4=-32760.00 → FAIL
- C4 vol-regime PnL: q0=-9365.00, q1=-3430.00, q2=-14805.00, q3=-3340.00, q4=-1820.00 → PASS

### `ROBOT_DISHES | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.1304`, frac_clear = `0.707` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1326 → FAIL
- C3 per-day PnL: D4=-64790.00 → FAIL
- C4 vol-regime PnL: q0=-9540.00, q1=-17245.00, q2=-7215.00, q3=-19500.00, q4=-11290.00 → PASS

### `ROBOT_DISHES | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.0017`, frac_clear = `0.372` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0362 → PASS
- C3 per-day PnL: D4=-54250.00 → FAIL
- C4 vol-regime PnL: q0=-14335.00, q1=-5605.00, q2=-16515.00, q3=-14705.00, q4=-3090.00 → PASS

### `ROBOT_DISHES | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `7.4180`, frac_clear = `0.818` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1246 → FAIL
- C3 per-day PnL: D4=-70740.00 → FAIL
- C4 vol-regime PnL: q0=-16660.00, q1=-11480.00, q2=-12695.00, q3=-19460.00, q4=-10445.00 → PASS

### `ROBOT_IRONING | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `2.3994`, frac_clear = `0.781` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0243 → FAIL
- C3 per-day PnL: D4=-44770.00 → FAIL
- C4 vol-regime PnL: q0=-1560.00, q1=-7060.00, q2=-9390.00, q3=-11410.00, q4=-15350.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_IRONING | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.9590`, frac_clear = `0.765` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0803 → PASS
- C3 per-day PnL: D4=-45870.00 → FAIL
- C4 vol-regime PnL: q0=-4440.00, q1=-4400.00, q2=-12400.00, q3=-14705.00, q4=-9925.00 → PASS

### `ROBOT_IRONING | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `7.4251`, frac_clear = `0.915` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0447 → FAIL
- C3 per-day PnL: D4=-32940.00 → FAIL
- C4 vol-regime PnL: q0=+380.00, q1=-1495.00, q2=-7345.00, q3=-6600.00, q4=-17880.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_IRONING | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.2112`, frac_clear = `0.872` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.1030 → PASS
- C3 per-day PnL: D4=-34240.00 → FAIL
- C4 vol-regime PnL: q0=-1800.00, q1=-3505.00, q2=-10095.00, q3=-5770.00, q4=-13070.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_LAUNDRY | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.7669`, frac_clear = `0.382` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0651 → FAIL
- C3 per-day PnL: D4=-60570.00 → FAIL
- C4 vol-regime PnL: q0=-12850.00, q1=-10360.00, q2=-15555.00, q3=-5705.00, q4=-16100.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.6538`, frac_clear = `0.751` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0648 → FAIL
- C3 per-day PnL: D4=-81550.00 → FAIL
- C4 vol-regime PnL: q0=-21020.00, q1=-16060.00, q2=-21900.00, q3=-10615.00, q4=-11955.00 → PASS

### `ROBOT_LAUNDRY | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `1.2339`, frac_clear = `0.627` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0835 → FAIL
- C3 per-day PnL: D4=-59190.00 → FAIL
- C4 vol-regime PnL: q0=-6100.00, q1=-13630.00, q2=-20125.00, q3=-5080.00, q4=-14255.00 → PASS

### `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `8.5033`, frac_clear = `0.852` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0548 → FAIL
- C3 per-day PnL: D4=-59850.00 → FAIL
- C4 vol-regime PnL: q0=-13760.00, q1=-12835.00, q2=-14230.00, q3=-8575.00, q4=-10450.00 → PASS

### `ROBOT_MOPPING | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.0814`, frac_clear = `0.205` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0445 → PASS
- C3 per-day PnL: D4=-32310.00 → FAIL
- C4 vol-regime PnL: q0=-5680.00, q1=-5380.00, q2=-9215.00, q3=-7585.00, q4=-4450.00 → PASS

### `ROBOT_MOPPING | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.2802`, frac_clear = `0.709` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0084 → PASS
- C3 per-day PnL: D4=-93650.00 → FAIL
- C4 vol-regime PnL: q0=-23245.00, q1=-16210.00, q2=-13960.00, q3=-18285.00, q4=-21950.00 → PASS

### `ROBOT_MOPPING | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.6950`, frac_clear = `0.420` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0290 → FAIL
- C3 per-day PnL: D4=-58170.00 → FAIL
- C4 vol-regime PnL: q0=-8925.00, q1=-10320.00, q2=-11860.00, q3=-12850.00, q4=-14215.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_MOPPING | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `6.5404`, frac_clear = `0.792` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0476 → FAIL
- C3 per-day PnL: D4=-94360.00 → FAIL
- C4 vol-regime PnL: q0=-25280.00, q1=-19655.00, q2=-7855.00, q3=-14360.00, q4=-27210.00 → FAIL — worst PnL in top trend quintile

### `ROBOT_VACUUMING | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.7644`, frac_clear = `0.136` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0381 → FAIL
- C3 per-day PnL: D4=-34410.00 → FAIL
- C4 vol-regime PnL: q0=-6110.00, q1=-4255.00, q2=-10025.00, q3=-6485.00, q4=-7535.00 → PASS

### `ROBOT_VACUUMING | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.1332`, frac_clear = `0.683` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0030 → FAIL
- C3 per-day PnL: D4=-79170.00 → FAIL
- C4 vol-regime PnL: q0=-12265.00, q1=-16860.00, q2=-20650.00, q3=-13650.00, q4=-15745.00 → PASS

### `ROBOT_VACUUMING | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.8938`, frac_clear = `0.343` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0046 → PASS
- C3 per-day PnL: D4=-74320.00 → FAIL
- C4 vol-regime PnL: q0=-14470.00, q1=-14910.00, q2=-16035.00, q3=-14395.00, q4=-14510.00 → PASS

### `ROBOT_VACUUMING | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.8115`, frac_clear = `0.804` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0109 → PASS
- C3 per-day PnL: D4=-98430.00 → FAIL
- C4 vol-regime PnL: q0=-13425.00, q1=-20360.00, q2=-18480.00, q3=-21180.00, q4=-24985.00 → FAIL — worst PnL in top trend quintile

## All folds (IC summary)

- `ROBOT_DISHES | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.1326`
- `ROBOT_DISHES | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0111`
- `ROBOT_DISHES | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0709`
- `ROBOT_DISHES | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0223`
- `ROBOT_DISHES | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.1326`
- `ROBOT_DISHES | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0119`
- `ROBOT_DISHES | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0325`
- `ROBOT_DISHES | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0607`
- `ROBOT_DISHES | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0487`
- `ROBOT_DISHES | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0119`
- `ROBOT_DISHES | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1246`
- `ROBOT_DISHES | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0449`
- `ROBOT_DISHES | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1300`
- `ROBOT_DISHES | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0365`
- `ROBOT_DISHES | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1246`
- `ROBOT_DISHES | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0362`
- `ROBOT_DISHES | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0415`
- `ROBOT_DISHES | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0793`
- `ROBOT_DISHES | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.1213`
- `ROBOT_DISHES | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0362`
- `ROBOT_IRONING | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0803`
- `ROBOT_IRONING | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0361`
- `ROBOT_IRONING | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0133`
- `ROBOT_IRONING | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0364`
- `ROBOT_IRONING | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0803`
- `ROBOT_IRONING | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0243`
- `ROBOT_IRONING | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0765`
- `ROBOT_IRONING | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0070`
- `ROBOT_IRONING | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0094`
- `ROBOT_IRONING | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0243`
- `ROBOT_IRONING | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.1030`
- `ROBOT_IRONING | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0248`
- `ROBOT_IRONING | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0058`
- `ROBOT_IRONING | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0685`
- `ROBOT_IRONING | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.1030`
- `ROBOT_IRONING | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0447`
- `ROBOT_IRONING | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0923`
- `ROBOT_IRONING | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0323`
- `ROBOT_IRONING | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0148`
- `ROBOT_IRONING | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0447`
- `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0648`
- `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0588`
- `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0496`
- `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0519`
- `ROBOT_LAUNDRY | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0648`
- `ROBOT_LAUNDRY | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0651`
- `ROBOT_LAUNDRY | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0715`
- `ROBOT_LAUNDRY | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0525`
- `ROBOT_LAUNDRY | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0218`
- `ROBOT_LAUNDRY | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0651`
- `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0548`
- `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0586`
- `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0483`
- `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0510`
- `ROBOT_LAUNDRY | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0548`
- `ROBOT_LAUNDRY | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0835`
- `ROBOT_LAUNDRY | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1111`
- `ROBOT_LAUNDRY | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0892`
- `ROBOT_LAUNDRY | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0366`
- `ROBOT_LAUNDRY | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0835`
- `ROBOT_MOPPING | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0084`
- `ROBOT_MOPPING | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0720`
- `ROBOT_MOPPING | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0027`
- `ROBOT_MOPPING | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0082`
- `ROBOT_MOPPING | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0084`
- `ROBOT_MOPPING | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0445`
- `ROBOT_MOPPING | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0130`
- `ROBOT_MOPPING | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0391`
- `ROBOT_MOPPING | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0131`
- `ROBOT_MOPPING | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0445`
- `ROBOT_MOPPING | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0476`
- `ROBOT_MOPPING | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.1147`
- `ROBOT_MOPPING | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0358`
- `ROBOT_MOPPING | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0186`
- `ROBOT_MOPPING | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0476`
- `ROBOT_MOPPING | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0290`
- `ROBOT_MOPPING | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.1032`
- `ROBOT_MOPPING | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0175`
- `ROBOT_MOPPING | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.1174`
- `ROBOT_MOPPING | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0290`
- `ROBOT_VACUUMING | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0030`
- `ROBOT_VACUUMING | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0331`
- `ROBOT_VACUUMING | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0481`
- `ROBOT_VACUUMING | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0049`
- `ROBOT_VACUUMING | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0030`
- `ROBOT_VACUUMING | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0381`
- `ROBOT_VACUUMING | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0072`
- `ROBOT_VACUUMING | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0298`
- `ROBOT_VACUUMING | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0003`
- `ROBOT_VACUUMING | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0381`
- `ROBOT_VACUUMING | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0109`
- `ROBOT_VACUUMING | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0440`
- `ROBOT_VACUUMING | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0696`
- `ROBOT_VACUUMING | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0185`
- `ROBOT_VACUUMING | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0109`
- `ROBOT_VACUUMING | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0046`
- `ROBOT_VACUUMING | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0225`
- `ROBOT_VACUUMING | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0078`
- `ROBOT_VACUUMING | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0056`
- `ROBOT_VACUUMING | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0046`
