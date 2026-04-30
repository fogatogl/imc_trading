# SNACKPACK — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.9351`, frac_clear = `0.001` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1237 → FAIL
- C3 per-day PnL: D4=-990.00 → FAIL
- C4 vol-regime PnL: q0=+0.00, q1=-170.00, q2=-110.00, q3=-100.00, q4=-610.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-3.7978`, frac_clear = `0.193` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0627 → PASS
- C3 per-day PnL: D4=-89230.00 → FAIL
- C4 vol-regime PnL: q0=-20185.00, q1=-13775.00, q2=-15515.00, q3=-23795.00, q4=-15960.00 → PASS

### `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.3398`, frac_clear = `0.013` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1378 → FAIL
- C3 per-day PnL: D4=-9510.00 → FAIL
- C4 vol-regime PnL: q0=-1430.00, q1=-860.00, q2=-440.00, q3=-1230.00, q4=-5550.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `-1.3285`, frac_clear = `0.417` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.1165 → PASS
- C3 per-day PnL: D4=-122370.00 → FAIL
- C4 vol-regime PnL: q0=-21540.00, q1=-28660.00, q2=-24250.00, q3=-24415.00, q4=-23505.00 → PASS

### `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.8391`, frac_clear = `0.000` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0097 → PASS
- C3 per-day PnL: D4=-140.00 → FAIL
- C4 vol-regime PnL: q0=+0.00, q1=+0.00, q2=+0.00, q3=-140.00, q4=+0.00 → PASS

### `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-4.7055`, frac_clear = `0.095` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0080 → PASS
- C3 per-day PnL: D4=-43520.00 → FAIL
- C4 vol-regime PnL: q0=-9810.00, q1=-8860.00, q2=-7235.00, q3=-7050.00, q4=-10565.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.1695`, frac_clear = `0.005` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0164 → FAIL
- C3 per-day PnL: D4=-5540.00 → FAIL
- C4 vol-regime PnL: q0=-280.00, q1=-560.00, q2=-1520.00, q3=-2890.00, q4=-290.00 → PASS

### `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `-2.8027`, frac_clear = `0.279` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0838 → FAIL
- C3 per-day PnL: D4=-92590.00 → FAIL
- C4 vol-regime PnL: q0=-13855.00, q1=-15235.00, q2=-24155.00, q3=-20165.00, q4=-19180.00 → PASS

### `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.9836`, frac_clear = `0.003` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0544 → FAIL
- C3 per-day PnL: D4=-4270.00 → FAIL
- C4 vol-regime PnL: q0=-140.00, q1=-1060.00, q2=-370.00, q3=-1660.00, q4=-1040.00 → PASS

### `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-2.6023`, frac_clear = `0.327` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0418 → FAIL
- C3 per-day PnL: D4=-120140.00 → FAIL
- C4 vol-regime PnL: q0=-28260.00, q1=-23690.00, q2=-17565.00, q3=-29490.00, q4=-21135.00 → PASS

### `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-6.1736`, frac_clear = `0.022` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1183 → FAIL
- C3 per-day PnL: D4=-17780.00 → FAIL
- C4 vol-regime PnL: q0=-1350.00, q1=-3520.00, q2=-2180.00, q3=-6325.00, q4=-4405.00 → PASS

### `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `0.0255`, frac_clear = `0.501` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1367 → FAIL
- C3 per-day PnL: D4=-142900.00 → FAIL
- C4 vol-regime PnL: q0=-28350.00, q1=-25950.00, q2=-25280.00, q3=-30450.00, q4=-32870.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-7.6194`, frac_clear = `0.004` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0436 → FAIL
- C3 per-day PnL: D4=-4240.00 → FAIL
- C4 vol-regime PnL: q0=-190.00, q1=-470.00, q2=-330.00, q3=-2130.00, q4=-1120.00 → PASS

### `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-3.9843`, frac_clear = `0.230` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0219 → FAIL
- C3 per-day PnL: D4=-117290.00 → FAIL
- C4 vol-regime PnL: q0=-25780.00, q1=-18645.00, q2=-21150.00, q3=-26115.00, q4=-25600.00 → PASS

### `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-7.0214`, frac_clear = `0.013` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0695 → FAIL
- C3 per-day PnL: D4=-11760.00 → FAIL
- C4 vol-regime PnL: q0=-1440.00, q1=-1910.00, q2=-2620.00, q3=-2350.00, q4=-3440.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `-1.9513`, frac_clear = `0.389` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0081 → FAIL
- C3 per-day PnL: D4=-160540.00 → FAIL
- C4 vol-regime PnL: q0=-29775.00, q1=-34630.00, q2=-28060.00, q3=-35960.00, q4=-32115.00 → PASS

### `SNACKPACK_VANILLA | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-7.5256`, frac_clear = `0.000` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.1059 → FAIL
- C3 per-day PnL: D4=+0.00 → FAIL
- C4 vol-regime PnL: q0=+0.00, q1=+0.00, q2=+0.00, q3=+0.00, q4=+0.00 → PASS

### `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-4.3658`, frac_clear = `0.165` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0499 → FAIL
- C3 per-day PnL: D4=-99360.00 → FAIL
- C4 vol-regime PnL: q0=-20275.00, q1=-13460.00, q2=-26885.00, q3=-22395.00, q4=-16345.00 → PASS

### `SNACKPACK_VANILLA | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-7.1383`, frac_clear = `0.002` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0740 → FAIL
- C3 per-day PnL: D4=-2020.00 → FAIL
- C4 vol-regime PnL: q0=-210.00, q1=-340.00, q2=+0.00, q3=-580.00, q4=-890.00 → FAIL — worst PnL in top trend quintile

### `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `-1.5434`, frac_clear = `0.405` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0701 → FAIL
- C3 per-day PnL: D4=-172250.00 → FAIL
- C4 vol-regime PnL: q0=-36220.00, q1=-35915.00, q2=-41875.00, q3=-30515.00, q4=-27725.00 → PASS

## All folds (IC summary)

- `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0627`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0103`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0645`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.1014`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0627`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.1237`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0006`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0527`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0436`
- `SNACKPACK_CHOCOLATE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.1237`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.1165`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0468`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0154`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.1259`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.1165`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.1378`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0392`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0836`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0916`
- `SNACKPACK_CHOCOLATE | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.1378`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0080`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0033`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0442`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0151`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0080`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0097`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0035`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0168`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0076`
- `SNACKPACK_PISTACHIO | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0097`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0838`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.1581`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.1480`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0899`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0838`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0164`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0333`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0145`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0621`
- `SNACKPACK_PISTACHIO | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0164`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0418`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0505`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0113`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0166`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0418`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0544`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0284`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0151`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0127`
- `SNACKPACK_RASPBERRY | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0544`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1367`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0828`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0427`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0113`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1367`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.1183`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0461`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.1031`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.1026`
- `SNACKPACK_RASPBERRY | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.1183`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0219`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0394`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0017`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0600`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0219`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0436`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0432`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0069`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0076`
- `SNACKPACK_STRAWBERRY | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0436`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0081`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0006`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0737`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0507`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0081`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0695`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0224`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0656`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0672`
- `SNACKPACK_STRAWBERRY | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0695`
- `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0499`
- `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0150`
- `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0443`
- `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0279`
- `SNACKPACK_VANILLA | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0499`
- `SNACKPACK_VANILLA | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.1059`
- `SNACKPACK_VANILLA | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0218`
- `SNACKPACK_VANILLA | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0348`
- `SNACKPACK_VANILLA | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0330`
- `SNACKPACK_VANILLA | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.1059`
- `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0701`
- `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0265`
- `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0430`
- `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0213`
- `SNACKPACK_VANILLA | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0701`
- `SNACKPACK_VANILLA | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0740`
- `SNACKPACK_VANILLA | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0203`
- `SNACKPACK_VANILLA | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0601`
- `SNACKPACK_VANILLA | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0290`
- `SNACKPACK_VANILLA | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0740`
