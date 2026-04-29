# Round 5 — Best strategies per family

Verified 2026-04-29 against single-live-D5 PnL in each `<sub>.json`
`activitiesLog`. Each family's best is the highest realised live PnL
reachable by stacking disjoint products across submissions (pair / basket
legs cannot be split — they ship locked together).

**Stacked total: +53,680 SeaShells**

## Per-family attribution

| Family | Best PnL | Sources | Products contributing |
|---|---:|---|---|
| PEBBLES | **+10,428** | `557541.py` (retired, deleted from disk) | full 4-pair star L/M/S/XS-vs-XL, tight MM. Current best on disk: `556852.py` PEB block = +10,099. |
| SLEEP_POD | **+9,709** | `555509.py` | slp_cp pair (COT/POL, β=−0.795 OLS, ent=1.6) + COT/NYL/POL MM |
| UV_VISOR | **+8,640** | `558897.py` minus YELLOW | naive top-of-book MM, qty=cap, spread≥2 gate. ORANGE/RED/MAGENTA. Drop YELLOW (−214). |
| SNACKPACK | **+4,546** | `556852.py` SNK block | 4-pair basket: CHOC↔VAN, PIST↔RASP, PIST↔STRAW, RASP↔STRAW. ent=2.0, units 2/2/3/3. |
| TRANSLATOR | **+4,832** | `549159.py` ⊕ `556909.py` | 549: MIST +1,991 + BLUE +1,920 (naive MM). 909: ASTRO_BLACK +921. |
| MICROCHIP | **+4,411** | `549159.py` ⊕ `556909.py` ⊕ `560161.py` | 549: CIRCLE +264. 909: TRIANGLE +1,528 (best of 4 subs). 161: OVAL +2,619. RECTANGLE −849 (drop). |
| ROBOT | **+4,165** | `549159.py` ⊕ `556909.py` | 549: IRONING +1,508 + MOPPING +1,457. 909: VACUUMING +1,200. LAUNDRY −391 (drop). DISHES untraded. |
| OXYGEN_SHAKE | **+3,497** | `549159.py` ⊕ `556909.py` | 549: CHOCOLATE +2,230 (drop EVENING_BREATH −255). 909: GARLIC +1,267. |
| GALAXY_SOUNDS | **+3,441** | `549159.py` ⊕ `555509.py` | 549: SOLAR_FLAMES +1,212. 555: BLACK_HOLES +2,229. |
| PANEL | **+11** | `560470.py` | naive MM + position-aware trend filter (ema30−ema200). 1X4 −919, 2X2 −1,323, 2X4 +2,252. First PANEL break-even. |

## Stacking rule

Across-submission stacking is valid only when contributing products are
disjoint. Multi-leg pair baskets (PEB star, SNK basket, slp_cp pair) ship
their legs locked together — cannot slice. Per-product best within a
single submission is the unit; you copy the whole basket if any leg from
it is the family best.

## Files in this folder

| File | Family roles |
|---|---|
| `549159.py` | TRANS (MIST/BLUE), ROBOT (IRON/MOP), OXY (CHOC), GLX (SOLAR_FLAMES), MIC (CIRCLE) |
| `555509.py` | SLEEP_POD (COT/NYL/POL pair+MM), GLX (BLACK_HOLES) |
| `556852.py` | SNACKPACK (4-pair basket), PEBBLES (4-pair star — current on-disk best) |
| `556909.py` | TRANS (ASTRO), ROBOT (VAC), OXY (GARLIC), MIC (TRIANGLE) |
| `558897.py` | UV_VISOR (RED/ORANGE/MAGENTA — drop YELLOW for +8,640) |
| `560161.py` | MICROCHIP (OVAL naive — drop RECTANGLE smart for −849) |
| `560470.py` | PANEL (trend-filtered naive MM) |

## Caveats

- All numbers are single live D5 outcomes (n=1). Variance dominates on
  most products — see `feedback_per_day_positive_selection`,
  `feedback_bt_inflation_round5_mm`.
- Stacked total +53,680 is theoretical — requires re-implementing every
  family's winner block in one submission. Not yet shipped as a single
  trader. Best actually-shipped total = `555509.py` at +21,881.
- `557541` (PEB +10,428) was deleted from disk in earlier cleanup. Number
  preserved in memory but unreproducible without the source. Treat
  current PEB best as `556852.py` +10,099 until a re-ship validates.
- These files are verbatim copies of the submission `.py` from
  `round5/<sub>/<sub>.py` (or `556909/556909.py` for the top-level one).
  Edit only the canonical source to keep this folder in sync.

## Per CLAUDE.md feedback rules

- `feedback_live_submission_telemetry_only`: use these files to inspect
  live trades on the kevin-fu1 visualizer; **do not** iterate parameters
  off them. Optimisation runs against the 3-day BT only.
- `feedback_simple_first_mm`: every winner here is a simple recipe
  (naive MM with one or two overlays). Resist adding rungs without
  per-day-positive validation.
