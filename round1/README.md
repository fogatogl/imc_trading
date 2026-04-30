# Round 1 — Trading Groundwork

**Closed:** 2026-04-17
**Products:** `ASH_COATED_OSMIUM` (limit 80), `INTARIAN_PEPPER_ROOT` (limit 80)
**Platform doc:** [`Round 1 - "Trading groundwork" ...md`](../Round%201%20-%20%E2%80%9CTrading%20groundwork%E2%80%9D%20bb83d50cdd2382c6ae7d01aaf8e929fa.md)

## What was shipped

| Product | Final trader | Mechanic |
|---|---|---|
| `ASH_COATED_OSMIUM` | [`trader_ash6_fix_doublefire.py`](trader_ash6_fix_doublefire.py) | Three-layer: z-score taker + wall sniper + OBI maker, sharing a common position budget |
| `INTARIAN_PEPPER_ROOT` | [`2800ash_final.py`](2800ash_final.py) (PEPPER layer) | Buy-and-hold base + swing |

Full architecture, parameters, and per-layer rationale: [`ROUND1_STRATEGY.md`](ROUND1_STRATEGY.md).
Manual round notes: [`ROUND1_manual_trading.md`](ROUND1_manual_trading.md).

## Research artefacts

- [`ash_coated_osmium_analysis.ipynb`](ash_coated_osmium_analysis.ipynb) — wall detection, z-score IC, vol-regime accuracy, OBI behaviour.
- [`intarian_pepper_root_analysis.ipynb`](intarian_pepper_root_analysis.ipynb) — swing classification, drift detection.
- [`ash_maker.py`](ash_maker.py) — earlier maker-only baseline, preserved for ablation context.

## Reproducibility

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round1/trader_ash6_fix_doublefire.py 1--2 1--1 1-0
```

Cross-check with the Rust engine — see top-level [README](../README.md#reproducing-the-alpha).
