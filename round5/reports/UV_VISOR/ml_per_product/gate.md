# UV_VISOR — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `UV_VISOR_AMBER | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.8209`, frac_clear = `0.224` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0286 → PASS
- C3 per-day PnL: D4=-51160.00 → FAIL
- C4 vol-regime PnL: q0=-12175.00, q1=-12210.00, q2=-7940.00, q3=-10195.00, q4=-8640.00 → PASS

### `UV_VISOR_AMBER | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.6455`, frac_clear = `0.556` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0598 → PASS
- C3 per-day PnL: D4=-89490.00 → FAIL
- C4 vol-regime PnL: q0=-17210.00, q1=-20015.00, q2=-16370.00, q3=-19805.00, q4=-16090.00 → PASS

### `UV_VISOR_AMBER | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.1429`, frac_clear = `0.479` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0600 → PASS
- C3 per-day PnL: D4=-68350.00 → FAIL
- C4 vol-regime PnL: q0=-15595.00, q1=-15380.00, q2=-12200.00, q3=-19025.00, q4=-6150.00 → PASS

### `UV_VISOR_AMBER | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.3859`, frac_clear = `0.698` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0721 → PASS
- C3 per-day PnL: D4=-86580.00 → FAIL
- C4 vol-regime PnL: q0=-16640.00, q1=-20865.00, q2=-13490.00, q3=-19625.00, q4=-15960.00 → PASS

### `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.9342`, frac_clear = `0.040` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0203 → FAIL
- C3 per-day PnL: D4=-20300.00 → FAIL
- C4 vol-regime PnL: q0=-2970.00, q1=-2450.00, q2=-4190.00, q3=-6325.00, q4=-4365.00 → PASS

### `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.2969`, frac_clear = `0.484` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0195 → FAIL
- C3 per-day PnL: D4=-126680.00 → FAIL
- C4 vol-regime PnL: q0=-25890.00, q1=-25495.00, q2=-24730.00, q3=-28295.00, q4=-22270.00 → PASS

### `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.3331`, frac_clear = `0.198` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0086 → FAIL
- C3 per-day PnL: D4=-59900.00 → FAIL
- C4 vol-regime PnL: q0=-10150.00, q1=-11570.00, q2=-12095.00, q3=-15970.00, q4=-10115.00 → PASS

### `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.0210`, frac_clear = `0.627` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0567 → FAIL
- C3 per-day PnL: D4=-132440.00 → FAIL
- C4 vol-regime PnL: q0=-30570.00, q1=-24530.00, q2=-24375.00, q3=-28440.00, q4=-24525.00 → PASS

### `UV_VISOR_ORANGE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-5.2394`, frac_clear = `0.016` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0271 → FAIL
- C3 per-day PnL: D4=-10380.00 → FAIL
- C4 vol-regime PnL: q0=-725.00, q1=-2105.00, q2=-2950.00, q3=-2655.00, q4=-1945.00 → PASS

### `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.0007`, frac_clear = `0.500` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0935 → PASS
- C3 per-day PnL: D4=-130670.00 → FAIL
- C4 vol-regime PnL: q0=-28780.00, q1=-26175.00, q2=-25905.00, q3=-29820.00, q4=-19990.00 → PASS

### `UV_VISOR_ORANGE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.5351`, frac_clear = `0.070` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0402 → FAIL
- C3 per-day PnL: D4=-33640.00 → FAIL
- C4 vol-regime PnL: q0=-4760.00, q1=-6320.00, q2=-7430.00, q3=-6780.00, q4=-8350.00 → FAIL — worst PnL in top trend quintile

### `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.1562`, frac_clear = `0.646` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0300 → PASS
- C3 per-day PnL: D4=-145560.00 → FAIL
- C4 vol-regime PnL: q0=-26860.00, q1=-30805.00, q2=-31070.00, q3=-33485.00, q4=-23340.00 → PASS

### `UV_VISOR_RED | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-5.3545`, frac_clear = `0.045` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0283 → FAIL
- C3 per-day PnL: D4=-18130.00 → FAIL
- C4 vol-regime PnL: q0=-3050.00, q1=-4170.00, q2=-4310.00, q3=-2695.00, q4=-3905.00 → PASS

### `UV_VISOR_RED | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.9102`, frac_clear = `0.445` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0860 → PASS
- C3 per-day PnL: D4=-138300.00 → FAIL
- C4 vol-regime PnL: q0=-34105.00, q1=-27770.00, q2=-28425.00, q3=-18565.00, q4=-29435.00 → PASS

### `UV_VISOR_RED | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.6217`, frac_clear = `0.201` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0710 → FAIL
- C3 per-day PnL: D4=-61650.00 → FAIL
- C4 vol-regime PnL: q0=-18060.00, q1=-8645.00, q2=-13285.00, q3=-8155.00, q4=-13505.00 → PASS

### `UV_VISOR_RED | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.6349`, frac_clear = `0.578` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0163 → PASS
- C3 per-day PnL: D4=-173000.00 → FAIL
- C4 vol-regime PnL: q0=-34675.00, q1=-37430.00, q2=-40915.00, q3=-31110.00, q4=-28870.00 → PASS

### `UV_VISOR_YELLOW | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-5.1723`, frac_clear = `0.011` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0618 → PASS
- C3 per-day PnL: D4=-7970.00 → FAIL
- C4 vol-regime PnL: q0=-510.00, q1=-1100.00, q2=-1240.00, q3=-1370.00, q4=-3750.00 → FAIL — worst PnL in top trend quintile

### `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.2573`, frac_clear = `0.483` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0636 → PASS
- C3 per-day PnL: D4=-133090.00 → FAIL
- C4 vol-regime PnL: q0=-22220.00, q1=-31130.00, q2=-27005.00, q3=-26485.00, q4=-26250.00 → PASS

### `UV_VISOR_YELLOW | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.0838`, frac_clear = `0.073` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0430 → PASS
- C3 per-day PnL: D4=-34120.00 → FAIL
- C4 vol-regime PnL: q0=-2390.00, q1=-5830.00, q2=-5415.00, q3=-9120.00, q4=-11365.00 → FAIL — worst PnL in top trend quintile

### `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.2853`, frac_clear = `0.644` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.1455 → PASS
- C3 per-day PnL: D4=-126510.00 → FAIL
- C4 vol-regime PnL: q0=-8950.00, q1=-29130.00, q2=-24540.00, q3=-28785.00, q4=-35105.00 → FAIL — worst PnL in top trend quintile

## All folds (IC summary)

- `UV_VISOR_AMBER | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0598`
- `UV_VISOR_AMBER | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0352`
- `UV_VISOR_AMBER | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0401`
- `UV_VISOR_AMBER | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0343`
- `UV_VISOR_AMBER | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0598`
- `UV_VISOR_AMBER | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0286`
- `UV_VISOR_AMBER | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0109`
- `UV_VISOR_AMBER | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.1134`
- `UV_VISOR_AMBER | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0053`
- `UV_VISOR_AMBER | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0286`
- `UV_VISOR_AMBER | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0721`
- `UV_VISOR_AMBER | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0266`
- `UV_VISOR_AMBER | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0498`
- `UV_VISOR_AMBER | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0018`
- `UV_VISOR_AMBER | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0721`
- `UV_VISOR_AMBER | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0600`
- `UV_VISOR_AMBER | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0094`
- `UV_VISOR_AMBER | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0532`
- `UV_VISOR_AMBER | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0075`
- `UV_VISOR_AMBER | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0600`
- `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0195`
- `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0767`
- `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0325`
- `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0085`
- `UV_VISOR_MAGENTA | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0195`
- `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0203`
- `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0732`
- `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0605`
- `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0527`
- `UV_VISOR_MAGENTA | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0203`
- `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0567`
- `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0063`
- `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0216`
- `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0387`
- `UV_VISOR_MAGENTA | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0567`
- `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0086`
- `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1057`
- `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0698`
- `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0964`
- `UV_VISOR_MAGENTA | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0086`
- `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0935`
- `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0615`
- `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0640`
- `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0649`
- `UV_VISOR_ORANGE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0935`
- `UV_VISOR_ORANGE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0271`
- `UV_VISOR_ORANGE | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0548`
- `UV_VISOR_ORANGE | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0169`
- `UV_VISOR_ORANGE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0733`
- `UV_VISOR_ORANGE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0271`
- `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0300`
- `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.2257`
- `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0978`
- `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.2418`
- `UV_VISOR_ORANGE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0300`
- `UV_VISOR_ORANGE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0402`
- `UV_VISOR_ORANGE | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0999`
- `UV_VISOR_ORANGE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0680`
- `UV_VISOR_ORANGE | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0899`
- `UV_VISOR_ORANGE | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0402`
- `UV_VISOR_RED | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0860`
- `UV_VISOR_RED | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0592`
- `UV_VISOR_RED | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0244`
- `UV_VISOR_RED | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0266`
- `UV_VISOR_RED | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0860`
- `UV_VISOR_RED | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0283`
- `UV_VISOR_RED | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0353`
- `UV_VISOR_RED | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0057`
- `UV_VISOR_RED | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0194`
- `UV_VISOR_RED | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0283`
- `UV_VISOR_RED | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0163`
- `UV_VISOR_RED | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0570`
- `UV_VISOR_RED | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0881`
- `UV_VISOR_RED | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0103`
- `UV_VISOR_RED | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0163`
- `UV_VISOR_RED | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0710`
- `UV_VISOR_RED | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0114`
- `UV_VISOR_RED | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0553`
- `UV_VISOR_RED | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0039`
- `UV_VISOR_RED | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0710`
- `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0636`
- `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0600`
- `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0358`
- `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0979`
- `UV_VISOR_YELLOW | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0636`
- `UV_VISOR_YELLOW | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0618`
- `UV_VISOR_YELLOW | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0726`
- `UV_VISOR_YELLOW | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0036`
- `UV_VISOR_YELLOW | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0317`
- `UV_VISOR_YELLOW | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0618`
- `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.1455`
- `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0474`
- `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.1127`
- `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0754`
- `UV_VISOR_YELLOW | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.1455`
- `UV_VISOR_YELLOW | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0430`
- `UV_VISOR_YELLOW | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0882`
- `UV_VISOR_YELLOW | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0275`
- `UV_VISOR_YELLOW | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0408`
- `UV_VISOR_YELLOW | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0430`
