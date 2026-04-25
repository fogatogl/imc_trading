# Round 3 Smile-Alternative & Layered-Strategy Results

Branch: `claude/improve-options-strategy-NVQYn`
Backtester: `prosperity4bt 0.0.0` (pip), `--match-trades worse`, days `3-0 3-1 3-2`.

## Headline

| Strategy | Day 0 | Day 1 | Day 2 | **Total** | vs baseline |
|----------|------:|------:|------:|----------:|-----------:|
| `trader_gamma_v7.py` (baseline) | 4,236 | 2,838 | 1,439 | **8,513** | — |
| `trader_round3_robust.py` (full MM) | 15,522 | 19,058 | 9,278 | 43,859 | 5.15x |
| `strat_smile_vegawls.py` (online vega-WLS parabola) | 4,112 | 3,062 | 2,086 | 9,260 | +9% |
| `strat_smile_svi.py` (online SVI raw) | 4,096 | 3,111 | 1,998 | 9,206 | +8% |
| `strat_layered_v2.py` (robust + 5400 carry) | 11,488 | 15,331 | 6,210 | 33,030 | 3.9x |
| `strat_layered_v3.py` (carry + MM on every other strike) | 17,020 | 19,550 | 6,874 | 43,443 | 5.10x |
| `strat_layered_full.py` (carry + MM on HYDROGEL/4000) | 17,040 | 19,604 | 6,851 | 43,496 | 5.11x |
| **`strat_layered_smile.py`** (layered + SVI hedge) | **16,916** | **19,828** | **7,498** | **44,242** | **5.20x** |
| `strat_iv_scalp_revival.py` (per-strike IV residuals) | −499,490 | −501,640 | −486,648 | −1,487,778 | failed |

Promotion rule (per CLAUDE.md): a candidate replaces baseline only if it beats
on total PnL AND on ≥2 of 3 days individually. **`strat_layered_smile.py`
satisfies both** (44,242 > 8,513; wins all 3 days).

## What worked

- **Layering market-making PnL on top of gamma carry.** MM on `HYDROGEL_PACK`
  (+26.2k over 3 days) and `VEV_4000` (+8.8k) is orthogonal to the options
  layer. The gamma carry book on `VEV_5200/5300/5400` runs unchanged on top.
  Gross uplift: ~+35k over the carry-only baseline.
- **Smile-aware hedge ratios.** Replacing the constant `SIGMA = 0.234` with a
  rolling vega-weighted parabola sigma gave another +746 SeaShells (+1.7%) on
  top of the layered baseline. The improvement is small because the inner
  smile is genuinely near-flat for the carry strikes (5200/5300/5400) — the
  notebook's "smile is flat" finding holds for the inner band.

## What didn't work

- **Per-strike IV-residual scalping (`strat_iv_scalp_revival.py`).** Backtest
  losses up to −500k/day. Two compounding failure modes:
  1. Wing strikes (5400, 5500) produce IV estimates dominated by 0.5-tick
     premium quantization on thin OTM premia. The "residual" is mostly noise.
  2. The hedger reacts to every smile refit, crossing the VE spread on each
     basket-delta swing. A conservative rewrite (drop wings, threshold 2σ,
     warmup 2,000 ticks, hedge band 5) still bled −150k+/day from VE
     rehedging. The signal-to-noise ratio is too low for this fill model.
  Last year's IV-scalping playbook (100–150k/round) does not transplant to
  this dataset given the tick-quantized premium.
- **Adding MM on under-explored vouchers** (`VEV_4500/5000/5100/5500/6000/6500`)
  in `strat_layered_v3.py` produced essentially zero extra PnL. These books
  have no counterparty flow in the historical data — confirms the robust
  trader's docstring claim.
- **Cross-product MM + carry conflict.** `strat_layered_v2.py` (full robust MM
  set including VE/5200/5300 + carry on 5300/5400) underperforms layered_full
  by ~10k because VE MM and the gamma hedger fight over the VE position.

## Files added

- `round3/options_lib.py` — shared BS pricing, IV solver (bracketed
  bisection, no scipy), poly/SVI smile fitters, `RollingSmile` class.
  Pure-stdlib so it imports inside the prosperity4bt sandbox.
- `round3/_bt_setup.py` — patches `prosperity4bt.data.LIMITS` in-place to
  register Round 3 product caps. Imported by every strat file.
- `round3/_baseline_v7.py`, `round3/_baseline_robust.py` — wrappers used to
  reproduce the baselines (+8,513 and +43,859 respectively).
- `round3/strat_smile_vegawls.py` — online vega-WLS parabola hedge sigma.
- `round3/strat_smile_svi.py` — online SVI raw hedge sigma.
- `round3/strat_iv_scalp_revival.py` — per-strike residual scalping (kept
  for record despite negative result; `Trader` class compiles cleanly).
- `round3/strat_layered_full.py` — carry + MM on HYDROGEL/4000.
- `round3/strat_layered_v2.py` — full robust MM + 5400/5300 carry overlay.
- `round3/strat_layered_v3.py` — carry + MM on every non-carry voucher.
- `round3/strat_layered_smile.py` — layered_full + SVI hedge sigma. **Best.**

## Reproduce

```bash
# from /home/user/imc_trading
python -m prosperity4bt round3/strat_layered_smile.py 3-0 3-1 3-2 \
    --no-out --data dataset --no-progress --match-trades worse
```

CLAUDE.md's documented PowerShell variant (with the custom-fork backtester at
`imc_trading/imc-prosperity-4-backtester`) is unavailable on this Linux
machine; we use the pip-installed `prosperity4bt 0.0.0` against the Round 3
data via a `dataset/round3 -> ROUND_3` symlink.

## Closing the 600–800k gap

This work closed ~5x of the gap. The remaining 13–18x to 600–800k is unlikely
to come from smile alternatives — the analysis confirms the inner smile is
genuinely near-flat for tradable strikes. The structural alpha sources
identified in the plan but not yet realised:

1. **HYDROGEL_PACK MM tuning** — quote size, OF threshold, inv skew. The
   product contributes 60% of total PnL; a 2x improvement here equals a 50%
   total uplift. Outside this PR's smile-alternative scope.
2. **Manual trade / Bio-Pods** — competitor scores almost certainly include
   the manual trading challenge (uniform-prior reserve auction). Not a
   programmatic strategy.
3. **Round 1/2 carryover** — competitor totals are cumulative.
4. **Joint $(K, T)$ surface** (`strat_surface_kt.py` in the plan) — calibrated
   offline on all 3 days, frozen for live. Would matter at TTE = 5d (live)
   more than on backtest. Not implemented in this batch.
