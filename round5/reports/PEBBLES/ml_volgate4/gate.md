# PEBBLES — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `POOLED | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-4.3276`, frac_clear = `0.061` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0174 → FAIL
- C3 per-day PnL: D4=-79862.00 → FAIL
- C4 vol-regime PnL: q0=-2248.00, q1=-8658.50, q2=-10977.50, q3=-14585.00, q4=-43393.00 → FAIL — worst PnL in top trend quintile

### `POOLED | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `-0.0391`, frac_clear = `0.497` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0229 → PASS
- C3 per-day PnL: D4=-216554.00 → FAIL
- C4 vol-regime PnL: q0=-640.50, q1=-48700.00, q2=+31106.50, q3=-78015.00, q4=-120305.00 → FAIL — worst PnL in top trend quintile

### `POOLED | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.1632`, frac_clear = `0.316` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0419 → FAIL
- C3 per-day PnL: D4=-258954.00 → FAIL
- C4 vol-regime PnL: q0=-43327.00, q1=-28568.50, q2=-20.50, q3=-62990.50, q4=-124047.50 → FAIL — worst PnL in top trend quintile

### `POOLED | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.6349`, frac_clear = `0.661` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0011 → PASS
- C3 per-day PnL: D4=-330817.00 → FAIL
- C4 vol-regime PnL: q0=+23763.00, q1=-97601.50, q2=-28774.00, q3=-126525.50, q4=-101679.00 → PASS

## All folds (IC summary)

- `POOLED | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0229`
- `POOLED | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0239`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0132`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.0284`
- `POOLED | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0229`
- `POOLED | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0174`
- `POOLED | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0045`
- `POOLED | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0350`
- `POOLED | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0155`
- `POOLED | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0174`
- `POOLED | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0011`
- `POOLED | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0028`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0360`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0404`
- `POOLED | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0011`
- `POOLED | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0419`
- `POOLED | fwd_ret h=100 ridge` [D2->D3]: IC = `0.0422`
- `POOLED | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0859`
- `POOLED | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0685`
- `POOLED | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0419`
