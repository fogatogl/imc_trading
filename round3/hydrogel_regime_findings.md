# HYDROGEL_PACK — regime-shift research

**Date:** 2026-04-25.
**Baseline:** [`overfit_hydrogel.py`](overfit_hydrogel.py) — `K_FV=6, CAP=200, INV_MAX_SKEW=20, ANCHOR=10000, ANCHOR_BREAK_TOL=200`.

## Problem

`overfit_hydrogel` posted **+5 k** then collapsed to **−4 k** on the live submission (max-PnL 5 k). Backtest shows +112 k / 3 days. The live failure mode is structural: when mid drifts persistently away from 10 000, the strategy keeps loading inventory at full slope until `|mid − 10 000| > 200`, at which point target snaps to 0 and we are stuck at full long/short on a moving market.

## Goal

Keep the aggressive winning behaviour (full ±200 inventory, K_FV=6, taker fills via inv-skew) when the anchor regime holds. Detect regime shift early enough to stop bleeding, without surrendering backtest PnL on the days the anchor *does* hold.

## Variants tested

Three mechanisms, each layered on top of the baseline `overfit_hydrogel` aggression. None of them tunes `K_FV`, `CAP`, or `INV_MAX_SKEW` (those stay at v9 values).

| File | Detection type | Mechanism |
|---|---|---|
| [`strat_hg_regime_pnl.py`](strat_hg_regime_pnl.py) | Reactive | Mark-to-market drawdown > 1.5 k from session peak → defensive mode (target=0, skew=0) for 5 k ticks; resets after 50 % recovery |
| [`strat_hg_regime_drift.py`](strat_hg_regime_drift.py) | Predictive | Slow EMA of mid (HL ≈ 6 000 ticks). When `\|EMA − 10000\|` > 30 ticks, scale K_FV and CAP linearly toward 0; full kill at deviation 80 |
| [`strat_hg_regime_softcap.py`](strat_hg_regime_softcap.py) | Structural | Replace linear-then-clipped target with `target = CAP * tanh(K_FV * (mid − ANCHOR) / CAP)` — same slope at ANCHOR, smooth saturation, never snap to 0 |

## Backtest results (`prosperity4bt … 3 --match-trades worse`)

| Variant | Day 0 | Day 1 | Day 2 | **Total** | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| `overfit_hydrogel` (baseline) | 37,031 | 41,993 | 33,612 | **112,636** | — |
| `strat_hg_regime_drift` | 37,031 | 38,283 | 33,612 | **108,926** | −3.3 % |
| `strat_hg_regime_softcap` | 31,307 | 36,592 | 28,923 | **96,822** | −14.0 % |
| `strat_hg_regime_pnl` | 27,894 | 34,028 | 17,406 | **79,328** | −29.6 % |

All variants stay profitable on every individual day.

### Reading the rows

- **regime_drift** is the closest behavioural copy of the baseline. Days 0 and 2 are bit-identical — slow EMA never deviates more than 30 ticks from 10 000, so the gate stays open at `drift=0`. Day 1 loses 3.7 k because the EMA briefly enters the soft-fade band.
- **regime_softcap** is permanently active: every tick it builds a marginally smaller target than the baseline. The 14 % cost is the price of *always* leaving inventory on the table near the cap. The bonus is that the kill-cliff at `|mid − 10000| = 200` is gone; degradation is smooth.
- **regime_pnl** is pessimistic. `DD_THRESH=1500` is small relative to normal market-making oscillation — Day 2 in particular triggers repeatedly during otherwise-fine periods, halving its PnL. Threshold needs an order of magnitude more headroom; the prototype is calibrated wrong for backtest noise.

## Which one protects against the live failure mode?

The live failure mode is "mid drifts away from 10 000 for thousands of ticks". Reproducing that mentally on each variant:

| Variant | Behaviour in a sustained drift to mid = 10 050 (e.g.) |
|---|---|
| baseline | Loads full −300 contracts of slope (clipped at CAP=200), still active until `\|mid−10000\|=200`, then snaps target to 0 stuck at full inventory |
| `regime_drift` | EMA tracks mid up. By the time EMA reaches 10 050, drift = (50−30)/(80−30) = 0.4. K_FV down to 3.6, CAP down to 120. Inventory stops growing at ~120 contracts long instead of 200. **Predictive** — stops accumulation before the cliff. |
| `regime_softcap` | tanh saturates target ≈ 197 at deviation 50 — still nearly full inventory. **Marginal protection**: only really helps for very large deviations. The cliff at `\|mid−10000\|>200` is removed but the build-up is unchanged. |
| `regime_pnl` | Once cumulative MtM drawdown crosses 1.5 k, flips to passive MM. Reactive — already underwater when it fires. With unrealised loss = pos × adverse drift, on full inventory drift of ~10 ticks fires the killswitch. **Cuts the bleed but doesn't prevent the entry.** |

**Ranking on live-failure protection:** `regime_drift` (best — catches early), `regime_pnl` (reacts — caps loss but only after entry), `regime_softcap` (marginal — only the very tail).

## Combined design

The two best mechanisms are orthogonal: `regime_drift` is predictive, `regime_pnl` is a reactive fallback. They do not conflict. Recommended combined logic for a v17:

1. Slow-EMA drift gate (primary): scale `K_FV` and `CAP` by `(1 − drift)`. Same parameters as `strat_hg_regime_drift`.
2. PnL killswitch (fallback): only triggers if drift gate fails. Tune `DD_THRESH` to ~5 k (covers 200 contracts × 25 ticks adverse — i.e., a real drift loss, not normal MM noise). Defensive mode flips target=0, skew=0.

`regime_softcap` is dropped: it doesn't address the live failure mode and has a permanent ~14 % backtest tax.

## What the backtests cannot tell us

- Three days of mid ≈ 10 000 with no regime breach. Each variant's 'regime detector' is *idle most of the time on the 3-day data*. Backtest scores measure how much the detector costs *when nothing is wrong*, not how much it saves *when something is wrong*.
- The live submission's failure says something about the live regime that we cannot replicate. Any threshold (DRIFT_SOFT=30, DRIFT_KILL=80, DD_THRESH=1500) is a guess, and tuning them on backtest is the same trap that produced v9.

The defensible argument is: if the anchor holds, `regime_drift` costs ~3 % vs baseline. If the anchor breaks, it caps inventory build at ~60 % of CAP. That asymmetry is worth the 3 % insurance premium.

## Recommendation

1. Promote `strat_hg_regime_drift` as the new aggressive-with-safety candidate. Test it as a drop-in replacement for the v9-style block in `trader_merged_v4.py`.
2. Optional: write `strat_hg_regime_combined.py` adding a wide PnL killswitch (`DD_THRESH ≈ 5 000`) on top, as belt-and-suspenders. The wider threshold should keep backtest cost close to drift-only.
3. Do not ship `strat_hg_regime_pnl` standalone — `DD_THRESH` is mis-calibrated and the loss on Day 2 is substantial.
4. Do not ship `strat_hg_regime_softcap` — it gives up backtest PnL without addressing the live failure mode.

## Files

- [`strat_hg_regime_pnl.py`](strat_hg_regime_pnl.py)
- [`strat_hg_regime_drift.py`](strat_hg_regime_drift.py)
- [`strat_hg_regime_softcap.py`](strat_hg_regime_softcap.py)

Per CLAUDE.md research workflow: variants stay until the user reviews backtester output and approves removal/promotion.
