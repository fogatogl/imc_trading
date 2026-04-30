# GALAXY_SOUNDS — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.6950`, frac_clear = `0.070` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0134 → FAIL
- C3 per-day PnL: D4=-34100.00 → FAIL
- C4 vol-regime PnL: q0=-8610.00, q1=-6760.00, q2=-3745.00, q3=-6145.00, q4=-8840.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.3276`, frac_clear = `0.483` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0425 → FAIL
- C3 per-day PnL: D4=-150720.00 → FAIL
- C4 vol-regime PnL: q0=-27060.00, q1=-28085.00, q2=-33160.00, q3=-28850.00, q4=-33565.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.1948`, frac_clear = `0.400` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1074 → FAIL
- C3 per-day PnL: D4=-94110.00 → FAIL
- C4 vol-regime PnL: q0=-30515.00, q1=-16345.00, q2=-14785.00, q3=-16055.00, q4=-16410.00 → PASS

### `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.3692`, frac_clear = `0.663` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1229 → FAIL
- C3 per-day PnL: D4=-168160.00 → FAIL
- C4 vol-regime PnL: q0=-21470.00, q1=-30705.00, q2=-37220.00, q3=-34790.00, q4=-43975.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.4733`, frac_clear = `0.038` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0815 → FAIL
- C3 per-day PnL: D4=-21870.00 → FAIL
- C4 vol-regime PnL: q0=-1560.00, q1=-4140.00, q2=-4170.00, q3=-5220.00, q4=-6780.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.4519`, frac_clear = `0.528` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1426 → FAIL
- C3 per-day PnL: D4=-144920.00 → FAIL
- C4 vol-regime PnL: q0=-33215.00, q1=-28290.00, q2=-28795.00, q3=-33610.00, q4=-21010.00 → PASS

### `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.0252`, frac_clear = `0.217` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1411 → FAIL
- C3 per-day PnL: D4=-64020.00 → FAIL
- C4 vol-regime PnL: q0=-12185.00, q1=-8510.00, q2=-11605.00, q3=-17275.00, q4=-14445.00 → PASS

### `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.7061`, frac_clear = `0.706` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1694 → FAIL
- C3 per-day PnL: D4=-132160.00 → FAIL
- C4 vol-regime PnL: q0=-24975.00, q1=-31415.00, q2=-34255.00, q3=-26110.00, q4=-15405.00 → PASS

### `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.9437`, frac_clear = `0.119` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0085 → FAIL
- C3 per-day PnL: D4=-38640.00 → FAIL
- C4 vol-regime PnL: q0=-8220.00, q1=-9435.00, q2=-5135.00, q3=-6530.00, q4=-9320.00 → PASS

### `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.5383`, frac_clear = `0.533` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0074 → FAIL
- C3 per-day PnL: D4=-141820.00 → FAIL
- C4 vol-regime PnL: q0=-33555.00, q1=-26015.00, q2=-32375.00, q3=-29095.00, q4=-20780.00 → PASS

### `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.9291`, frac_clear = `0.244` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0227 → FAIL
- C3 per-day PnL: D4=-83350.00 → FAIL
- C4 vol-regime PnL: q0=-17270.00, q1=-16465.00, q2=-10850.00, q3=-15115.00, q4=-23650.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.4839`, frac_clear = `0.693` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0231 → PASS
- C3 per-day PnL: D4=-132140.00 → FAIL
- C4 vol-regime PnL: q0=-37565.00, q1=-24950.00, q2=-19400.00, q3=-23145.00, q4=-27080.00 → PASS

### `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.8647`, frac_clear = `0.034` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0288 → FAIL
- C3 per-day PnL: D4=-16870.00 → FAIL
- C4 vol-regime PnL: q0=-1800.00, q1=-1680.00, q2=-2650.00, q3=-4045.00, q4=-6695.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.4015`, frac_clear = `0.522` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0009 → FAIL
- C3 per-day PnL: D4=-135740.00 → FAIL
- C4 vol-regime PnL: q0=-28555.00, q1=-31730.00, q2=-30360.00, q3=-21200.00, q4=-23895.00 → PASS

### `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.6417`, frac_clear = `0.187` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0194 → FAIL
- C3 per-day PnL: D4=-52490.00 → FAIL
- C4 vol-regime PnL: q0=-13655.00, q1=-11945.00, q2=-7785.00, q3=-8600.00, q4=-10505.00 → PASS

### `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.1448`, frac_clear = `0.690` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0725 → FAIL
- C3 per-day PnL: D4=-155680.00 → FAIL
- C4 vol-regime PnL: q0=-22905.00, q1=-44420.00, q2=-39185.00, q3=-21035.00, q4=-28135.00 → PASS

### `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.7294`, frac_clear = `0.052` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0003 → FAIL
- C3 per-day PnL: D4=-27130.00 → FAIL
- C4 vol-regime PnL: q0=-4450.00, q1=-4140.00, q2=-5635.00, q3=-4505.00, q4=-8400.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.0508`, frac_clear = `0.498` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0014 → PASS
- C3 per-day PnL: D4=-120060.00 → FAIL
- C4 vol-regime PnL: q0=-21150.00, q1=-25310.00, q2=-26350.00, q3=-27095.00, q4=-20155.00 → PASS

### `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.6823`, frac_clear = `0.149` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0328 → FAIL
- C3 per-day PnL: D4=-58790.00 → FAIL
- C4 vol-regime PnL: q0=-13430.00, q1=-9360.00, q2=-11725.00, q3=-8225.00, q4=-16050.00 → FAIL — worst PnL in top trend quintile

### `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.8871`, frac_clear = `0.633` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0186 → PASS
- C3 per-day PnL: D4=-127110.00 → FAIL
- C4 vol-regime PnL: q0=-26170.00, q1=-30490.00, q2=-29870.00, q3=-25365.00, q4=-15215.00 → PASS

## All folds (IC summary)

- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0425`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0466`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.1014`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0173`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0425`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0134`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0676`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0223`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0918`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0134`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1229`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0702`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1306`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0447`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1229`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.1074`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1123`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0593`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0986`
- `GALAXY_SOUNDS_BLACK_HOLES | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.1074`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.1426`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0277`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0547`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0511`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.1426`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0815`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0183`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0203`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0901`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0815`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1694`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0281`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1057`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0489`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1694`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.1411`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0058`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0189`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.1233`
- `GALAXY_SOUNDS_DARK_MATTER | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.1411`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0074`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0583`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0885`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0771`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0074`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0085`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0399`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0363`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0632`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0085`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0231`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0160`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0991`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0069`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0231`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0227`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0155`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.1193`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0362`
- `GALAXY_SOUNDS_PLANETARY_RINGS | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0227`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0009`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0593`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0036`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0771`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0009`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0288`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0202`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0036`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0211`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0288`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0725`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0643`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0287`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0626`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0725`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0194`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0760`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0621`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0759`
- `GALAXY_SOUNDS_SOLAR_FLAMES | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0194`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0014`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0057`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0684`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0146`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0014`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0003`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0675`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0489`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0580`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0003`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0186`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0838`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0706`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0314`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0186`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0328`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0280`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0190`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0019`
- `GALAXY_SOUNDS_SOLAR_WINDS | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0328`
