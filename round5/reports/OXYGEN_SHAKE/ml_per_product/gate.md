# OXYGEN_SHAKE — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.7979`, frac_clear = `0.022` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0035 → PASS
- C3 per-day PnL: D4=-20560.00 → FAIL
- C4 vol-regime PnL: q0=-4040.00, q1=-2140.00, q2=-4960.00, q3=-3400.00, q4=-6020.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.1923`, frac_clear = `0.510` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0542 → FAIL
- C3 per-day PnL: D4=-155330.00 → FAIL
- C4 vol-regime PnL: q0=-23580.00, q1=-25220.00, q2=-28490.00, q3=-36925.00, q4=-41115.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.2561`, frac_clear = `0.188` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0497 → PASS
- C3 per-day PnL: D4=-92800.00 → FAIL
- C4 vol-regime PnL: q0=-19850.00, q1=-19015.00, q2=-18825.00, q3=-17915.00, q4=-17195.00 → PASS

### `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.9607`, frac_clear = `0.676` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0866 → FAIL
- C3 per-day PnL: D4=-171800.00 → FAIL
- C4 vol-regime PnL: q0=-31740.00, q1=-35325.00, q2=-33600.00, q3=-37390.00, q4=-33745.00 → PASS

### `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.0421`, frac_clear = `0.042` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0454 → PASS
- C3 per-day PnL: D4=-19920.00 → FAIL
- C4 vol-regime PnL: q0=-5480.00, q1=-2850.00, q2=-5730.00, q3=-2100.00, q4=-3760.00 → PASS

### `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.9608`, frac_clear = `0.566` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0422 → FAIL
- C3 per-day PnL: D4=-84360.00 → FAIL
- C4 vol-regime PnL: q0=-10090.00, q1=-18360.00, q2=-15010.00, q3=-20210.00, q4=-20690.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.4230`, frac_clear = `0.233` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0746 → PASS
- C3 per-day PnL: D4=-63160.00 → FAIL
- C4 vol-regime PnL: q0=-15960.00, q1=-12760.00, q2=-14540.00, q3=-10440.00, q4=-9460.00 → PASS

### `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `6.4376`, frac_clear = `0.743` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0556 → PASS
- C3 per-day PnL: D4=-69080.00 → FAIL
- C4 vol-regime PnL: q0=-7540.00, q1=-16520.00, q2=-14560.00, q3=-17060.00, q4=-13400.00 → PASS

### `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-5.8235`, frac_clear = `0.040` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0344 → PASS
- C3 per-day PnL: D4=-22500.00 → FAIL
- C4 vol-regime PnL: q0=-2800.00, q1=-3015.00, q2=-3105.00, q3=-3180.00, q4=-10400.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.0658`, frac_clear = `0.496` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0508 → FAIL
- C3 per-day PnL: D4=-162590.00 → FAIL
- C4 vol-regime PnL: q0=-25205.00, q1=-36590.00, q2=-36220.00, q3=-31300.00, q4=-33275.00 → PASS

### `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.7013`, frac_clear = `0.204` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0533 → PASS
- C3 per-day PnL: D4=-72720.00 → FAIL
- C4 vol-regime PnL: q0=-11105.00, q1=-12675.00, q2=-13175.00, q3=-14540.00, q4=-21225.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.2771`, frac_clear = `0.660` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0717 → FAIL
- C3 per-day PnL: D4=-161010.00 → FAIL
- C4 vol-regime PnL: q0=-23850.00, q1=-38805.00, q2=-39555.00, q3=-40325.00, q4=-18475.00 → PASS

### `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.5884`, frac_clear = `0.117` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0024 → FAIL
- C3 per-day PnL: D4=-45590.00 → FAIL
- C4 vol-regime PnL: q0=-7850.00, q1=-13295.00, q2=-5400.00, q3=-9985.00, q4=-9060.00 → PASS

### `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.0155`, frac_clear = `0.562` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0893 → FAIL
- C3 per-day PnL: D4=-127420.00 → FAIL
- C4 vol-regime PnL: q0=-24555.00, q1=-22305.00, q2=-25870.00, q3=-21645.00, q4=-33045.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.6545`, frac_clear = `0.352` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0016 → PASS
- C3 per-day PnL: D4=-94970.00 → FAIL
- C4 vol-regime PnL: q0=-16790.00, q1=-27160.00, q2=-17700.00, q3=-17750.00, q4=-15570.00 → PASS

### `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.6558`, frac_clear = `0.706` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0308 → FAIL
- C3 per-day PnL: D4=-131970.00 → FAIL
- C4 vol-regime PnL: q0=-25645.00, q1=-35215.00, q2=-24525.00, q3=-24040.00, q4=-22545.00 → PASS

### `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.6809`, frac_clear = `0.064` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0097 → PASS
- C3 per-day PnL: D4=-24620.00 → FAIL
- C4 vol-regime PnL: q0=-3000.00, q1=-4020.00, q2=-6260.00, q3=-4775.00, q4=-6565.00 → FAIL — worst PnL in top trend quintile

### `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.5787`, frac_clear = `0.538` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0972 → PASS
- C3 per-day PnL: D4=-115600.00 → FAIL
- C4 vol-regime PnL: q0=-29650.00, q1=-13985.00, q2=-22570.00, q3=-23665.00, q4=-25730.00 → PASS

### `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.7267`, frac_clear = `0.188` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0342 → PASS
- C3 per-day PnL: D4=-52720.00 → FAIL
- C4 vol-regime PnL: q0=-10055.00, q1=-13205.00, q2=-9790.00, q3=-7975.00, q4=-11695.00 → PASS

### `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.1639`, frac_clear = `0.656` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0609 → PASS
- C3 per-day PnL: D4=-149560.00 → FAIL
- C4 vol-regime PnL: q0=-33865.00, q1=-28230.00, q2=-27995.00, q3=-26685.00, q4=-32785.00 → PASS

## All folds (IC summary)

- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0542`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0318`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0247`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0117`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0542`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0035`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0243`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0621`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0055`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0035`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0866`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0099`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0112`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0267`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0866`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0497`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0066`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0236`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0269`
- `OXYGEN_SHAKE_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0497`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0422`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0833`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0018`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0020`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0422`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0454`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0282`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0038`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0174`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0454`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0556`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.1756`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0640`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0309`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0556`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0746`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0216`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0154`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0302`
- `OXYGEN_SHAKE_EVENING_BREATH | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0746`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0508`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0484`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0118`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0922`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0508`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0344`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0156`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0002`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0290`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0344`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0717`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0165`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0128`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0469`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0717`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0533`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0270`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0237`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0231`
- `OXYGEN_SHAKE_GARLIC | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0533`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0893`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0255`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0909`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0316`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0893`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0024`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0582`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0137`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0556`
- `OXYGEN_SHAKE_MINT | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0024`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0308`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0459`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1284`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0167`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0308`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0016`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0939`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0064`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0677`
- `OXYGEN_SHAKE_MINT | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0016`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0972`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0005`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0102`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0015`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0972`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0097`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0341`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0102`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0506`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0097`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0609`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0120`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0664`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0062`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0609`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0342`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0713`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0524`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0567`
- `OXYGEN_SHAKE_MORNING_BREATH | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0342`
