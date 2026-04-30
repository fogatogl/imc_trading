# PEBBLES — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `PEBBLES_L | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-5.0176`, frac_clear = `0.032` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0520 → FAIL
- C3 per-day PnL: D4=-24220.00 → FAIL
- C4 vol-regime PnL: q0=-70.00, q1=-3780.00, q2=-5040.00, q3=-6130.00, q4=-9200.00 → FAIL — worst PnL in top trend quintile

### `PEBBLES_L | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.6973`, frac_clear = `0.672` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0684 → PASS
- C3 per-day PnL: D4=-118760.00 → FAIL
- C4 vol-regime PnL: q0=-18880.00, q1=-26635.00, q2=-21995.00, q3=-23165.00, q4=-28085.00 → FAIL — worst PnL in top trend quintile

### `PEBBLES_L | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.4827`, frac_clear = `0.188` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0555 → FAIL
- C3 per-day PnL: D4=-52520.00 → FAIL
- C4 vol-regime PnL: q0=-6890.00, q1=-7415.00, q2=-15300.00, q3=-13050.00, q4=-9865.00 → PASS

### `PEBBLES_L | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.2972`, frac_clear = `0.789` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0810 → PASS
- C3 per-day PnL: D4=-131790.00 → FAIL
- C4 vol-regime PnL: q0=-26165.00, q1=-30190.00, q2=-26965.00, q3=-23035.00, q4=-25435.00 → PASS

### `PEBBLES_M | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.1906`, frac_clear = `0.110` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0274 → FAIL
- C3 per-day PnL: D4=-39940.00 → FAIL
- C4 vol-regime PnL: q0=-13840.00, q1=-7285.00, q2=-7445.00, q3=-7490.00, q4=-3880.00 → PASS

### `PEBBLES_M | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.8790`, frac_clear = `0.636` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0807 → PASS
- C3 per-day PnL: D4=-144160.00 → FAIL
- C4 vol-regime PnL: q0=-35655.00, q1=-30095.00, q2=-26860.00, q3=-22535.00, q4=-29015.00 → PASS

### `PEBBLES_M | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.6231`, frac_clear = `0.274` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0300 → FAIL
- C3 per-day PnL: D4=-80610.00 → FAIL
- C4 vol-regime PnL: q0=-20495.00, q1=-14720.00, q2=-17965.00, q3=-11785.00, q4=-15645.00 → PASS

### `PEBBLES_M | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `8.0662`, frac_clear = `0.755` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0707 → PASS
- C3 per-day PnL: D4=-113400.00 → FAIL
- C4 vol-regime PnL: q0=-37745.00, q1=-12865.00, q2=-18900.00, q3=-15740.00, q4=-28150.00 → PASS

### `PEBBLES_S | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.6973`, frac_clear = `0.330` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0032 → FAIL
- C3 per-day PnL: D4=-62620.00 → FAIL
- C4 vol-regime PnL: q0=-13070.00, q1=-10095.00, q2=-8005.00, q3=-17075.00, q4=-14375.00 → PASS

### `PEBBLES_S | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.6255`, frac_clear = `0.721` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0133 → PASS
- C3 per-day PnL: D4=-130960.00 → FAIL
- C4 vol-regime PnL: q0=-27830.00, q1=-27850.00, q2=-22955.00, q3=-27675.00, q4=-24650.00 → PASS

### `PEBBLES_S | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `0.8239`, frac_clear = `0.554` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0254 → PASS
- C3 per-day PnL: D4=-45710.00 → FAIL
- C4 vol-regime PnL: q0=-9725.00, q1=-9685.00, q2=-6005.00, q3=-8655.00, q4=-11640.00 → FAIL — worst PnL in top trend quintile

### `PEBBLES_S | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.2711`, frac_clear = `0.808` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0423 → PASS
- C3 per-day PnL: D4=-97520.00 → FAIL
- C4 vol-regime PnL: q0=-19405.00, q1=-22715.00, q2=-18460.00, q3=-21915.00, q4=-15025.00 → PASS

### `PEBBLES_XL | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.0346`, frac_clear = `0.320` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0697 → PASS
- C3 per-day PnL: D4=-98250.00 → FAIL
- C4 vol-regime PnL: q0=-24615.00, q1=-28220.00, q2=-20330.00, q3=-9510.00, q4=-15575.00 → PASS

### `PEBBLES_XL | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.8065`, frac_clear = `0.748` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0525 → FAIL
- C3 per-day PnL: D4=-189970.00 → FAIL
- C4 vol-regime PnL: q0=-23690.00, q1=-64460.00, q2=-26230.00, q3=-40885.00, q4=-34705.00 → PASS

### `PEBBLES_XL | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `1.6367`, frac_clear = `0.565` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0567 → PASS
- C3 per-day PnL: D4=-141260.00 → FAIL
- C4 vol-regime PnL: q0=-41570.00, q1=-45275.00, q2=-26940.00, q3=-7020.00, q4=-20455.00 → PASS

### `PEBBLES_XL | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `19.4775`, frac_clear = `0.832` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0336 → FAIL
- C3 per-day PnL: D4=-195570.00 → FAIL
- C4 vol-regime PnL: q0=-26230.00, q1=-72360.00, q2=-33225.00, q3=-22070.00, q4=-41685.00 → PASS

### `PEBBLES_XS | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.3253`, frac_clear = `0.328` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0631 → FAIL
- C3 per-day PnL: D4=-92480.00 → FAIL
- C4 vol-regime PnL: q0=-17915.00, q1=-21175.00, q2=-13735.00, q3=-21740.00, q4=-17915.00 → PASS

### `PEBBLES_XS | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.1600`, frac_clear = `0.764` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0143 → FAIL
- C3 per-day PnL: D4=-111490.00 → FAIL
- C4 vol-regime PnL: q0=-20325.00, q1=-24815.00, q2=-26505.00, q3=-18435.00, q4=-21410.00 → PASS

### `PEBBLES_XS | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `0.0375`, frac_clear = `0.503` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0815 → FAIL
- C3 per-day PnL: D4=-142770.00 → FAIL
- C4 vol-regime PnL: q0=-21885.00, q1=-32260.00, q2=-22895.00, q3=-35025.00, q4=-30705.00 → PASS

### `PEBBLES_XS | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `11.7871`, frac_clear = `0.872` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0130 → PASS
- C3 per-day PnL: D4=-117170.00 → FAIL
- C4 vol-regime PnL: q0=-16600.00, q1=-31710.00, q2=-28025.00, q3=-21105.00, q4=-19730.00 → PASS

## All folds (IC summary)

- `PEBBLES_L | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0684`
- `PEBBLES_L | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0129`
- `PEBBLES_L | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0576`
- `PEBBLES_L | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0329`
- `PEBBLES_L | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0684`
- `PEBBLES_L | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0520`
- `PEBBLES_L | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0859`
- `PEBBLES_L | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0634`
- `PEBBLES_L | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0516`
- `PEBBLES_L | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0520`
- `PEBBLES_L | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0810`
- `PEBBLES_L | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0740`
- `PEBBLES_L | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0382`
- `PEBBLES_L | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0499`
- `PEBBLES_L | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0810`
- `PEBBLES_L | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0555`
- `PEBBLES_L | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0445`
- `PEBBLES_L | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0021`
- `PEBBLES_L | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0406`
- `PEBBLES_L | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0555`
- `PEBBLES_M | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0807`
- `PEBBLES_M | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0115`
- `PEBBLES_M | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0927`
- `PEBBLES_M | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0710`
- `PEBBLES_M | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0807`
- `PEBBLES_M | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0274`
- `PEBBLES_M | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0840`
- `PEBBLES_M | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0279`
- `PEBBLES_M | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0994`
- `PEBBLES_M | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0274`
- `PEBBLES_M | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0707`
- `PEBBLES_M | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0589`
- `PEBBLES_M | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0243`
- `PEBBLES_M | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0873`
- `PEBBLES_M | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0707`
- `PEBBLES_M | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0300`
- `PEBBLES_M | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0728`
- `PEBBLES_M | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0070`
- `PEBBLES_M | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0457`
- `PEBBLES_M | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0300`
- `PEBBLES_S | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0133`
- `PEBBLES_S | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.1048`
- `PEBBLES_S | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0741`
- `PEBBLES_S | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0619`
- `PEBBLES_S | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0133`
- `PEBBLES_S | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0032`
- `PEBBLES_S | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0273`
- `PEBBLES_S | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0172`
- `PEBBLES_S | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0422`
- `PEBBLES_S | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0032`
- `PEBBLES_S | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0423`
- `PEBBLES_S | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0383`
- `PEBBLES_S | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0314`
- `PEBBLES_S | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0084`
- `PEBBLES_S | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0423`
- `PEBBLES_S | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0254`
- `PEBBLES_S | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0345`
- `PEBBLES_S | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0552`
- `PEBBLES_S | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0180`
- `PEBBLES_S | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0254`
- `PEBBLES_XL | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0525`
- `PEBBLES_XL | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0042`
- `PEBBLES_XL | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0078`
- `PEBBLES_XL | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0124`
- `PEBBLES_XL | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0525`
- `PEBBLES_XL | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0697`
- `PEBBLES_XL | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0810`
- `PEBBLES_XL | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0294`
- `PEBBLES_XL | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.1345`
- `PEBBLES_XL | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0697`
- `PEBBLES_XL | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0336`
- `PEBBLES_XL | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0914`
- `PEBBLES_XL | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0554`
- `PEBBLES_XL | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0613`
- `PEBBLES_XL | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0336`
- `PEBBLES_XL | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0567`
- `PEBBLES_XL | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1387`
- `PEBBLES_XL | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0498`
- `PEBBLES_XL | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.1511`
- `PEBBLES_XL | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0567`
- `PEBBLES_XS | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0143`
- `PEBBLES_XS | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0174`
- `PEBBLES_XS | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0239`
- `PEBBLES_XS | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0103`
- `PEBBLES_XS | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0143`
- `PEBBLES_XS | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0631`
- `PEBBLES_XS | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0225`
- `PEBBLES_XS | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0101`
- `PEBBLES_XS | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0017`
- `PEBBLES_XS | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0631`
- `PEBBLES_XS | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0130`
- `PEBBLES_XS | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0870`
- `PEBBLES_XS | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0189`
- `PEBBLES_XS | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0198`
- `PEBBLES_XS | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0130`
- `PEBBLES_XS | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0815`
- `PEBBLES_XS | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0237`
- `PEBBLES_XS | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0125`
- `PEBBLES_XS | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0226`
- `PEBBLES_XS | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0815`
