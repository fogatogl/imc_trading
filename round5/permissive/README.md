# Round-5 permissive classifier

Parallel pipeline that re-classifies round-5 products with a less discriminant,
multi-flag scheme. The legacy classifier in [`round5/archetypes.py`](../archetypes.py)
is **not modified** — it keeps producing `round5/reports/<FAMILY>/archetype_assignment.csv`
unchanged. This pipeline reads those legacy CSVs and emits a new schema under
`round5/reports_permissive/<FAMILY>/`.

## Why a parallel pipeline

The legacy classifier is priority-ordered (one primary archetype per product).
Combined with FDR across the 24 IC cells per product and a narrow MR signal
set (`neg_zscore_mid_50` only), it routes 43/50 products to NO_EDGE — including
ones with obvious structure on other axes. Examples:

| Product | Legacy primary | What was missed |
|---|---|---|
| MICROCHIP_TRIANGLE | NO_EDGE | `IC[neg_zscore_mid_50]=0.111 @ h=1000` (FDR-pass), but vr=0.972 missed the 0.97 cliff |
| MICROCHIP_SQUARE | NO_EDGE | vr=0.96 (p=1.5e-3), acf1=-0.024 (p=3.5e-5), pair with RECTANGLE (corr=-0.88, coint_p=0.027) |
| SNACKPACK_CHOCOLATE | NO_EDGE | vr=0.95 (p=8e-5), acf1=-0.031 (p=8.8e-8), OBI_IC=0.118 — but `IC[neg_z]=NaN` |

## Flag taxonomy (5 independent flags, OR-gated arms)

A product can carry any subset. NO_EDGE only when no flag fires AND no
top-K rank in any axis fires.

| Flag | Trigger (ANY arm fires the flag) |
|---|---|
| **MR_FLAG** | `vr_k5 < 0.97` AND `vr_p < 0.05` ▪ `acf1 < -0.01` AND `Bartlett p < 0.05` ▪ `hurst < 0.51` (informational) ▪ best signed-MR `IC ≥ 0.02` FDR-pass over the broader signal set |
| **MOM_FLAG** | `vr_k5 > 1.005` AND `vr_p < 0.05` ▪ `hurst > 0.55` ▪ `IC[momentum_10] ≥ 0.02` FDR-pass |
| **MM_FLAG** | `\|vr-1\|<0.05` AND `\|hurst-0.5\|<0.05` AND `\|acf1\|<0.05` AND no short-h IC predictability AND `spread/std≥1.5` AND `lim10_sat≥0.3` (no Template-A simulation gate — the legacy pipeline retains sim authority) |
| **OBI_FLAG** | `\|IC[obi_l1\|obi_l3]\| ≥ 0.04` FDR-pass at h ∈ {1, 10}, positive sign |
| **PAIR_FLAG** | two-tier — `\|corr_mid\| ≥ 0.7` (strong-corr lane, no coint required) OR `coint_p < 0.10` (cointegration lane, regardless of corr). Cointegration runs Engle-Granger in **both directions** with min p — see `round5/research_lib.py::cointegration_table`. |

**Broader MR signal set** (replaces the legacy singleton):

| Signal | MR sign | Interpretation |
|---|---:|---|
| `neg_zscore_mid_50` | +1 | classical anchor MR |
| `neg_spread` | +1 | wide spread predicts mean-reverting move |
| `momentum_10` | -1 | negative IC ⇒ continuation-fade ⇒ MR |
| `trade_imbalance` | -1 | negative IC ⇒ contrarian flow ⇒ MR |

Best signed-MR IC = max over the 4 signals × 4 horizons of `sign · IC` among
FDR-passing cells with positive product. The classifier feeds this single
scalar into the IC arm.

## Per-family ranking

For each family of 5, every product gets a score and a 1..5 rank per axis:

| Axis | Score (higher = stronger) |
|---|---|
| `mr_score` | z-normalized sum of `max(0.5-vr,0) + max(-acf1,0) + max(0.5-hurst,0) + max(0, best_mr_ic_signed)` |
| `mom_score` | z-normalized sum of `max(vr-1,0) + max(hurst-0.5,0) + max(0, best_mom_ic)` |
| `mm_score` | `(spread/std)·lim10_sat - 5·\|vr-1\| - 5·\|hurst-0.5\|` |
| `obi_score` | `max(0, \|best_obi_ic\|)` if FDR-pass else 0 |
| `pair_score` | `\|max_within_family_corr\| · (1 − min(coint_p, 1))` |

Top-2 per axis carries `top_<axis>_in_family=True` even if the universal gate
missed. With 5 axes × 2 top slots × 10 families = 100 ranking slots, no
product can fall into NO_EDGE on every axis unless its family is unusually
flat-on-flat across all dimensions.

## Output schema (`reports_permissive/<FAMILY>/archetype_assignment.csv`)

```
product,
mr_flag, mom_flag, mm_flag, obi_flag, pair_flag,
mr_score, mr_rank_in_family, top_mr_in_family,
mom_score, mom_rank_in_family, top_mom_in_family,
mm_score, mm_rank_in_family, top_mm_in_family,
obi_score, obi_rank_in_family, top_obi_in_family,
pair_score, pair_rank_in_family, top_pair_in_family,
no_edge,
flags_concat,
pair_partner, pair_corr, pair_coint_p,
obi_signal, obi_horizon, obi_ic,
rationale
```

Rationale is multi-segment, semicolon-joined, one bracket per fired flag.
Top-rank fallbacks (axis where the universal gate missed but the product
ranks top-K in its family) appear as `[TOP_<AXIS>_IN_FAMILY rank=k/5]`.

## How to run

Pre-requisite: legacy pipeline has populated `round5/reports/<FAMILY>/`. To
generate or refresh the legacy artifacts, run:

```bash
.venv/Scripts/python.exe round5/family_report.py --family ALL
```

Then run the permissive classifier:

```bash
.venv/Scripts/python.exe -m round5.permissive.cli --family ALL
```

Per-family run:

```bash
.venv/Scripts/python.exe -m round5.permissive.cli --family MICROCHIP
```

Custom paths:

```bash
.venv/Scripts/python.exe -m round5.permissive.cli --family ALL \
    --in round5/reports --out round5/reports_permissive
```

## What this pipeline does NOT do

- No new statistical computation. Reads the legacy CSVs only — does not
  recompute IC, ACF, vr, cointegration, etc. Numbers stay consistent with
  what the legacy pipeline already validated and committed to disk.
- No Template-A passive-MM simulation. `MM_FLAG` here is the *static*
  6-condition AND-conjunction. The legacy pipeline owns sim-gate authority.
- No volatility regime conditioning. The legacy `volatility.py` outputs
  (`vol_conditioned_ic.csv`, `vol_regime.csv`) are not consumed; their
  content is already reflected in the FDR-corrected IC table.
- No deep-research dives. `deep_triggers.md` and `--deep` flag continue to
  be the legacy pipeline's responsibility.

## Files

- [`classifier.py`](classifier.py) — `Gates` dataclass + `compute_flags`
- [`ranking.py`](ranking.py) — per-family scoring, ranking, DataFrame assembly, summary MD
- [`cli.py`](cli.py) — entry point (`python -m round5.permissive.cli`)
