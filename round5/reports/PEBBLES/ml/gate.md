# PEBBLES — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `POOLED | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.4242`, frac_clear = `0.055` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0407 → PASS
- C3 per-day PnL: D4=-28760.00 → FAIL
- C4 vol-regime PnL: q0=+1907.00, q1=-11926.00, q2=+3020.00, q3=-23204.00, q4=+1443.00 → PASS

### `POOLED | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-1.1141`, frac_clear = `0.418` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0053 → PASS
- C3 per-day PnL: D4=-164393.50 → FAIL
- C4 vol-regime PnL: q0=+20940.50, q1=-40731.00, q2=+36799.00, q3=-53135.00, q4=-128267.00 → FAIL — worst PnL in top trend quintile

### `POOLED | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.4209`, frac_clear = `0.270` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0487 → PASS
- C3 per-day PnL: D4=-59298.00 → FAIL
- C4 vol-regime PnL: q0=-22549.50, q1=-30801.00, q2=+18764.50, q3=-18918.50, q4=-5793.50 → PASS

### `POOLED | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.1663`, frac_clear = `0.608` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0055 → PASS
- C3 per-day PnL: D4=-362800.00 → FAIL
- C4 vol-regime PnL: q0=-3146.00, q1=-95976.50, q2=-15783.00, q3=-141668.50, q4=-106226.00 → PASS

## All folds (IC summary)

- `POOLED | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0053`
- `POOLED | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0074`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0049`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0193`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0053`
- `POOLED | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `0.0407`
- `POOLED | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0077`
- `POOLED | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0155`
- `POOLED | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0135`
- `POOLED | fwd_ret h=50 ridge` [LOO_D4]: IC = `0.0407`
- `POOLED | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0055`
- `POOLED | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0429`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0223`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0506`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0055`
- `POOLED | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0487`
- `POOLED | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0143`
- `POOLED | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0461`
- `POOLED | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0286`
- `POOLED | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0487`
