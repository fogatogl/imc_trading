# Round 3 — Gloves Off

**Closed:** 2026-04-26
**Products:** `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, ten `VEV_*` vouchers (strikes 4000–6500)
**Official PnL:** **+36,116 SeaShells**
**Platform doc:** [`Round 3 - "Gloves Off" ...md`](../Round%203%20-%20%E2%80%9CGloves%20Off%E2%80%9D%20fda3d50cdd238347a62601a66e0dae81.md)

## Final submission

[`486411/486411.py`](486411/486411.py) — telemetry archived in
`486411/486411.json`. Submission `417667/` (older variant) is kept under
the repo root for historical reference; both lived during this round's
iteration cycle.

| Product | PnL |
|---|---:|
| `HYDROGEL_PACK` | +19,712 |
| `VEV_5000` | +13,226 |
| `VEV_5300` | +8,055 |
| `VEV_5100` | +6,085 |
| `VEV_5200` | +1,482 |
| `VEV_5400` | −96 |
| `VEV_5500` | −696 |
| `VEV_4000` | −2,259 |
| `VELVETFRUIT_EXTRACT` | −2,531 |
| `VEV_4500` | −6,864 |
| **Total** | **+36,116** |

## What worked

**Hydrogel — anchor + vol armor.** An earlier v9 cross-book mean-rev
(`sk=20, K=6`) lost roughly 10 k live despite a +112 k backtest. The
shipped block reverts to a simple mean-rev around a fixed anchor
`HP_MEAN = 9991` with a `vol_scale = min(1, 30 / std50)` factor that
shrinks the position limit when realised volatility spikes. Shark-taker
at `|dev| > 22`, passive maker at `|dev| > 14` quoting 5 ticks beyond
mid. Largest single contributor.

**VEV vouchers — OU-corrected Black-Scholes.** Theoretical price
`theo = BS(σ_ATM) + MR_STRENGTH·(δ·E[ΔS] + ν·(σ_eff − σ))` with
`MR_STRENGTH = 1.0`, `EDGE = 1.5`, `TAKE_CAP = 30`. Deep-ITM strikes
(≤5000) priced via BS, ATM/OTM (>5000) priced as `mid + d_emp · E[ΔS]`
with empirical delta. Mostly profitable; `VEV_4500` was the one large
loser.

**VE underlying.** Z-score taker (`z=±1.5`, cap 40) plus tight maker
around the rolling mean. Lost 2.5 k — sub-noise; kept as a hedge layer.

## Research artefacts

- [`round3_strategy.md`](round3_strategy.md) — final strategy memo
- [`round3_findings.md`](round3_findings.md) — accumulated findings log
- [`hydrogel_research_study.md`](hydrogel_research_study.md), [`hydrogel_findings_and_plan.md`](hydrogel_findings_and_plan.md), [`hydrogel_regime_findings.md`](hydrogel_regime_findings.md), [`hydrogel_strategy_plan.md`](hydrogel_strategy_plan.md) — hydrogel deep-dives
- [`round3_analysis.ipynb`](round3_analysis.ipynb) — primary analysis notebook (anchor calibration, vol-armor sizing, VEV smile, voucher pricing)
- [`figures/`](figures/) — plots referenced from the docs above

## Reproducibility

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round3/486411/486411.py 1--2 1--1 1-0
```
