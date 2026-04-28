# Round 5 Strategy Templates

Drop-in `Trader` skeletons for the four behaviour classes you'd want to
fit a round-5 product (or pair) to, after the cluster + lead-lag scan
recommended in `analysis_brief.md`.

Each file is **self-contained**: standard `Logger` contract, the
`datamodel` import shim, single `Trader` class. Copy a file, change
`PRODUCT` (or `PRODUCT_A`/`PRODUCT_B` / `LEADER`/`FOLLOWER`) at the top,
backtest with both engines per `CLAUDE.md`. Default `POSITION_LIMIT = 10`
matches round-5 spec.

## Files

| File | Class | When to use |
|---|---|---|
| `strat_mean_revert_zscore.py` | mean reverting | Mid oscillates around a slow-moving mean. Rolling z-score, take at \|z\|>1.5, flatten + maker at \|z\|<0.3, freeze at \|z\|>4. |
| `strat_mean_revert_anchor.py` | mean reverting | Mid sits at a near-constant fair value. Fixed `ANCHOR` + vol-armor (`vol_scale = min(1, VOL_CAP/σ)`). Generalisation of the round-3 hydrogel block (PnL +19,712 → +39,970 after r4 anchor lift). |
| `strat_momentum_ema.py` | momentum | Persistent drift within rolling windows. Fast/slow EMA crossover, target = ±limit, take liquidity into the move. |
| `strat_momentum_breakout.py` | momentum | Regime shifts — quiet ranges punctuated by sustained moves. Donchian channel breakout with shorter-period trailing exit. |
| `strat_random_walk_mm.py` | random walk | Mid is martingale-like — no signal in returns. Passive market-making, inventory-skewed fair, opportunistic take on book dislocations. |
| `strat_pairs_spread.py` | pairs trading | Two products co-move at zero lag, residual stationary. Trade `spread = A - β·B` on z-score; β fixed or rolling regression. Hedge-aware sizing under the per-leg limit of 10. |
| `strat_pairs_leadlag.py` | pairs trading | Leader's `LAG`-tick return predicts follower's next move (analysis_brief case 2). Trade follower only. |

## Decision tree (which to try first)

```
Cluster scan finds a stable lead-lag pair (k stable across windows)?
└── yes  → strat_pairs_leadlag.py
└── no
    └── Two products with stationary spread (corr at lag 0, residual mean-reverts)?
        └── yes  → strat_pairs_spread.py
        └── no
            └── Single product. ADF/half-life on the mid:
                ├── stationary, fast half-life          → strat_mean_revert_anchor.py
                ├── stationary, slow half-life          → strat_mean_revert_zscore.py
                ├── positive return autocorrelation     → strat_momentum_ema.py
                ├── breakout-pattern (long flats, jumps)→ strat_momentum_breakout.py
                └── unit root, no autocorr              → strat_random_walk_mm.py
```

## Backtesting (per CLAUDE.md)

Always run **both** engines on round-5 days. Δ should be < ~1%; larger
divergence flags engine-specific exploitation, not real edge.

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round5/templates/strat_mean_revert_zscore.py 5-2 5-3 5-4
```

```bash
imc_trading/prosperity_rust_backtester/target/release/rust_backtester.exe \
    --trader round5/templates/strat_mean_revert_zscore.py --dataset round5
```

(Adjust day flags once round-5 dataset aliases are wired in
`prosperity_rust_backtester`.)

## Config tuning notes

- **`POSITION_LIMIT = 10`**: hard cap from round-5 spec. Edge per fill
  must dominate spread — naive MM at limit-10 grinds tiny.
- **`WARMUP`**: do *not* trade before this many ticks of history. Z-scores
  on 5 samples are nonsense.
- **`VOL_CAP` (anchor template)**: tune to product noise scale. If
  realised σ is typically 8 and you set `VOL_CAP = 30`, vol_scale stays
  ≈1 most of the time and shrinks only on real spikes — that's the
  intended behaviour.
- **`ENTRY_Z` / `RET_THRESHOLD`**: trade off frequency vs edge. The
  CLAUDE.md feedback `feedback_alpha_not_backtest` applies — don't tune
  these to maximise round-5 day-2/3/4 PnL specifically; you'll overfit.

## What to *not* do

- **Don't mix categories in one file.** One product family per template.
  See `feedback_separate_products` in CLAUDE.md.
- **Don't modify the `Logger` class.** It's the visualizer contract.
- **Don't promote a template to "current best" until** it beats the
  prior best on **all three** round-5 days, not just total.
- **Don't delete an experiment file** until backtest results have been
  reviewed and approval given (CLAUDE.md research workflow rule 5).
