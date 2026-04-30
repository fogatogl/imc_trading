# SLEEP_POD — ML Tradeability Gate

Live-haircut applied to predicted edge: **×0.30**

Four gate conditions (all must pass):
1. Predicted-edge dominance (post-haircut median excess > 0 AND >= 15% of ticks clear half-spread)
2. Per-day positive IC (every fold day)
3. Per-day positive simulated PnL (every day in fold)
4. Trend-defense — worst PnL quintile is not the top |std_500| quintile

## Headline fold: D2+D3 -> D4

### `SLEEP_POD_COTTON | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-3.0401`, frac_clear = `0.109` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0750 → FAIL
- C3 per-day PnL: D4=-33960.00 → FAIL
- C4 vol-regime PnL: q0=-7560.00, q1=-5655.00, q2=-7190.00, q3=-7290.00, q4=-6265.00 → PASS

### `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.9117`, frac_clear = `0.654` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0229 → FAIL
- C3 per-day PnL: D4=-111360.00 → FAIL
- C4 vol-regime PnL: q0=-19480.00, q1=-23860.00, q2=-25760.00, q3=-23995.00, q4=-18265.00 → PASS

### `SLEEP_POD_COTTON | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-1.2742`, frac_clear = `0.363` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0732 → FAIL
- C3 per-day PnL: D4=-68610.00 → FAIL
- C4 vol-regime PnL: q0=-17310.00, q1=-13550.00, q2=-18105.00, q3=-10170.00, q4=-9475.00 → PASS

### `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `9.6281`, frac_clear = `0.811` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0216 → FAIL
- C3 per-day PnL: D4=-89080.00 → FAIL
- C4 vol-regime PnL: q0=-20870.00, q1=-15425.00, q2=-20505.00, q3=-14035.00, q4=-18245.00 → PASS

### `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.0747`, frac_clear = `0.214` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0135 → FAIL
- C3 per-day PnL: D4=-53300.00 → FAIL
- C4 vol-regime PnL: q0=-11620.00, q1=-11665.00, q2=-12165.00, q3=-8140.00, q4=-9710.00 → PASS

### `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `3.0057`, frac_clear = `0.676` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0380 → FAIL
- C3 per-day PnL: D4=-89950.00 → FAIL
- C4 vol-regime PnL: q0=-18215.00, q1=-14510.00, q2=-23665.00, q3=-20025.00, q4=-13535.00 → PASS

### `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.7156`, frac_clear = `0.421` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0413 → PASS
- C3 per-day PnL: D4=-54440.00 → FAIL
- C4 vol-regime PnL: q0=-13765.00, q1=-13095.00, q2=-12755.00, q3=-7150.00, q4=-7675.00 → PASS

### `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `7.1408`, frac_clear = `0.775` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0009 → FAIL
- C3 per-day PnL: D4=-72820.00 → FAIL
- C4 vol-regime PnL: q0=-18140.00, q1=-4805.00, q2=-23175.00, q3=-11825.00, q4=-14875.00 → PASS

### `SLEEP_POD_NYLON | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.2533`, frac_clear = `0.208` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0103 → FAIL
- C3 per-day PnL: D4=-29730.00 → FAIL
- C4 vol-regime PnL: q0=-3795.00, q1=-3650.00, q2=-6425.00, q3=-7890.00, q4=-7970.00 → FAIL — worst PnL in top trend quintile

### `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.2693`, frac_clear = `0.599` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0118 → PASS
- C3 per-day PnL: D4=-95780.00 → FAIL
- C4 vol-regime PnL: q0=-18865.00, q1=-17790.00, q2=-19200.00, q3=-24675.00, q4=-15250.00 → PASS

### `SLEEP_POD_NYLON | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.8445`, frac_clear = `0.411` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0155 → FAIL
- C3 per-day PnL: D4=-57410.00 → FAIL
- C4 vol-regime PnL: q0=-14590.00, q1=-10680.00, q2=-8805.00, q3=-13045.00, q4=-10290.00 → PASS

### `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `4.7582`, frac_clear = `0.743` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0268 → FAIL
- C3 per-day PnL: D4=-104570.00 → FAIL
- C4 vol-regime PnL: q0=-24355.00, q1=-16285.00, q2=-24145.00, q3=-23530.00, q4=-16255.00 → PASS

### `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.6847`, frac_clear = `0.157` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0239 → FAIL
- C3 per-day PnL: D4=-41550.00 → FAIL
- C4 vol-regime PnL: q0=-11860.00, q1=-4205.00, q2=-7180.00, q3=-11915.00, q4=-6390.00 → PASS

### `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `2.7865`, frac_clear = `0.655` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.0544 → FAIL
- C3 per-day PnL: D4=-105860.00 → FAIL
- C4 vol-regime PnL: q0=-19240.00, q1=-22390.00, q2=-19290.00, q3=-21845.00, q4=-23095.00 → FAIL — worst PnL in top trend quintile

### `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.5462`, frac_clear = `0.441` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0292 → FAIL
- C3 per-day PnL: D4=-87890.00 → FAIL
- C4 vol-regime PnL: q0=-28505.00, q1=-13780.00, q2=-10115.00, q3=-21820.00, q4=-13670.00 → PASS

### `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `7.4754`, frac_clear = `0.789` (threshold 0.15) → PASS
- C2 per-day IC: D4=-0.1064 → FAIL
- C3 per-day PnL: D4=-95990.00 → FAIL
- C4 vol-regime PnL: q0=-16015.00, q1=-23695.00, q2=-20360.00, q3=-21035.00, q4=-14885.00 → PASS

### `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` — FAIL

- C1 edge dominance: median_excess = `-2.9612`, frac_clear = `0.095` (threshold 0.15) → FAIL
- C2 per-day IC: D4=-0.0193 → FAIL
- C3 per-day PnL: D4=-29460.00 → FAIL
- C4 vol-regime PnL: q0=-5200.00, q1=-3205.00, q2=-3300.00, q3=-8910.00, q4=-8845.00 → PASS

### `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` — FAIL

- C1 edge dominance: median_excess = `1.8047`, frac_clear = `0.612` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0004 → PASS
- C3 per-day PnL: D4=-119280.00 → FAIL
- C4 vol-regime PnL: q0=-23785.00, q1=-29140.00, q2=-19710.00, q3=-23930.00, q4=-22715.00 → PASS

### `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` — FAIL

- C1 edge dominance: median_excess = `-0.3714`, frac_clear = `0.469` (threshold 0.15) → FAIL
- C2 per-day IC: D4=0.0166 → PASS
- C3 per-day PnL: D4=-47710.00 → FAIL
- C4 vol-regime PnL: q0=-6810.00, q1=-12210.00, q2=-9080.00, q3=-10460.00, q4=-9150.00 → PASS

### `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` — FAIL

- C1 edge dominance: median_excess = `5.0062`, frac_clear = `0.731` (threshold 0.15) → PASS
- C2 per-day IC: D4=0.0368 → PASS
- C3 per-day PnL: D4=-127270.00 → FAIL
- C4 vol-regime PnL: q0=-19990.00, q1=-29610.00, q2=-30110.00, q3=-25165.00, q4=-22395.00 → PASS

## All folds (IC summary)

- `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0229`
- `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0482`
- `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0578`
- `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0015`
- `SLEEP_POD_COTTON | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0229`
- `SLEEP_POD_COTTON | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0750`
- `SLEEP_POD_COTTON | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0021`
- `SLEEP_POD_COTTON | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0451`
- `SLEEP_POD_COTTON | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0348`
- `SLEEP_POD_COTTON | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0750`
- `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0216`
- `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0235`
- `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0836`
- `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.0701`
- `SLEEP_POD_COTTON | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0216`
- `SLEEP_POD_COTTON | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0732`
- `SLEEP_POD_COTTON | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0287`
- `SLEEP_POD_COTTON | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0414`
- `SLEEP_POD_COTTON | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0504`
- `SLEEP_POD_COTTON | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0732`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0380`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0153`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0154`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0429`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0380`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0135`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0211`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0782`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0557`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0135`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0009`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0588`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0254`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` [LOO_D3]: IC = `0.1070`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0009`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0413`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0081`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0897`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0629`
- `SLEEP_POD_LAMB_WOOL | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0413`
- `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0118`
- `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0500`
- `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0179`
- `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` [LOO_D3]: IC = `-0.1132`
- `SLEEP_POD_NYLON | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0118`
- `SLEEP_POD_NYLON | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0103`
- `SLEEP_POD_NYLON | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0464`
- `SLEEP_POD_NYLON | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0751`
- `SLEEP_POD_NYLON | fwd_ret h=50 ridge` [LOO_D3]: IC = `0.0148`
- `SLEEP_POD_NYLON | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0103`
- `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.0268`
- `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0590`
- `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` [LOO_D2]: IC = `-0.0260`
- `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.1760`
- `SLEEP_POD_NYLON | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.0268`
- `SLEEP_POD_NYLON | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0155`
- `SLEEP_POD_NYLON | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1033`
- `SLEEP_POD_NYLON | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.1109`
- `SLEEP_POD_NYLON | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0638`
- `SLEEP_POD_NYLON | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0155`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `-0.0544`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` [D2->D3]: IC = `-0.0308`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` [LOO_D2]: IC = `0.0214`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0050`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 lgbm` [LOO_D4]: IC = `-0.0544`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0239`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` [D2->D3]: IC = `-0.0380`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` [LOO_D2]: IC = `-0.0356`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0527`
- `SLEEP_POD_POLYESTER | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0239`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `-0.1064`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` [D2->D3]: IC = `-0.0540`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0087`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0499`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 lgbm` [LOO_D4]: IC = `-0.1064`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `-0.0292`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` [D2->D3]: IC = `-0.0250`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` [LOO_D2]: IC = `-0.0862`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` [LOO_D3]: IC = `-0.0387`
- `SLEEP_POD_POLYESTER | fwd_ret h=100 ridge` [LOO_D4]: IC = `-0.0292`
- `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` [D2+D3->D4]: IC = `0.0004`
- `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` [D2->D3]: IC = `0.0608`
- `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` [LOO_D2]: IC = `-0.0226`
- `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` [LOO_D3]: IC = `0.0215`
- `SLEEP_POD_SUEDE | fwd_ret h=50 lgbm` [LOO_D4]: IC = `0.0004`
- `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` [D2+D3->D4]: IC = `-0.0193`
- `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` [D2->D3]: IC = `0.0344`
- `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` [LOO_D2]: IC = `0.0051`
- `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` [LOO_D3]: IC = `-0.0042`
- `SLEEP_POD_SUEDE | fwd_ret h=50 ridge` [LOO_D4]: IC = `-0.0193`
- `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` [D2+D3->D4]: IC = `0.0368`
- `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` [D2->D3]: IC = `0.0646`
- `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` [LOO_D2]: IC = `0.0088`
- `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` [LOO_D3]: IC = `-0.0038`
- `SLEEP_POD_SUEDE | fwd_ret h=100 lgbm` [LOO_D4]: IC = `0.0368`
- `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` [D2+D3->D4]: IC = `0.0166`
- `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` [D2->D3]: IC = `0.1264`
- `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` [LOO_D2]: IC = `0.0747`
- `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` [LOO_D3]: IC = `0.0471`
- `SLEEP_POD_SUEDE | fwd_ret h=100 ridge` [LOO_D4]: IC = `0.0166`
