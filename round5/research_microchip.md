# MICROCHIP — Family-Specific Research

Compiled 2026-04-29. Scope: MICROCHIP family only — CIRCLE, OVAL, SQUARE, RECTANGLE,
TRIANGLE. Current best live PnL: **+1,792** (TRIANGLE +1,528 from 556909, CIRCLE +264
from 549159, OVAL/SQUARE/RECTANGLE never traded). Goal: take family to ~+5–7k.

This file lives **next to** the cross-family ranking doc and the MM arsenal — but
applies *only* to MICROCHIP, per `feedback_separate_products`.

---

## Pre-flight check — what PANEL just taught us

`project_round5_panel` recorded: pipeline-classified `MR_TAKER` products on PANEL
**lost −154,593 BT** under the structural MR z-score taker template. Reason: PANEL
mids trend over 30k ticks, while a `neg_zscore_mid_50` taker with rolling-50 anchor
fights the trend (anchor lags, taker keeps shorting tops / buying bottoms in the
wrong direction). On PANEL, **naive MM won** instead — `qty=cap, spread≥2 gate, post
inside touch` returned BT +54,985.

**Therefore for MICROCHIP**: do **not** ship a MR z-score taker as the first attempt
just because the pipeline flags 4 of 5 MR_TAKER products. Validate naive MM first;
only consider MR taker if a per-product short-horizon (h=1, h=10) signal survives
FDR — the long-horizon h=1000 ICs are likely the same trend trap PANEL fell into.

---

## Per-product fact table

From [`reports/MICROCHIP/stats_per_product.csv`](reports/MICROCHIP/stats_per_product.csv) and
[`signals_ic.csv`](reports/MICROCHIP/signals_ic.csv).

| Product | mid_mean | mid_range | ret1_std | spread_med | depth_l1 | l10_sat | acf_lag1 | vr_k5 (z) | hurst | mid drift / 30k |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| CIRCLE | 9215 | 2428 | 9.2 | 8 | 14 | 0.15 | −0.005 | 1.005 (+0.4) | 0.537 | +382 |
| OVAL | 8180 | **5058** | 12.5 | 8 | 16 | 0.30 | −0.007 | 0.990 (−0.8) | 0.537 | **−4466** |
| SQUARE | 13595 | **6742** | **20.7** | **12** | 12 | 0.001 | **−0.024** | **0.960 (−3.2)** | 0.542 | +3617 |
| RECTANGLE | 8732 | 3115 | 13.1 | 8 | 14 | 0.23 | −0.003 | 1.007 (+0.5) | 0.536 | −1211 |
| TRIANGLE | 9686 | 3123 | 14.5 | 9 | 13 | 0.09 | −0.007 | 0.972 (−2.2) | 0.565 | −2080 |

**Short-horizon FDR-passing IC** (h ∈ {1, 10}, the only horizons that matter for
tick-level MM):

| Product | obi_l1 IC@h=1 (FDR) | obi_l3 IC@h=1 (FDR) | obi_l3 IC@h=10 (FDR) |
|---|---:|---:|---:|
| CIRCLE | **+0.022** ✓ | **−0.035** ✓ | −0.012 ✓ |
| OVAL | **+0.015** ✓ | **−0.030** ✓ | −0.011 ✗ |
| SQUARE | **+0.025** ✓ | **−0.029** ✓ | −0.013 ✓ |
| RECTANGLE | +0.007 ✗ | **−0.024** ✓ | **−0.014** ✓ |
| TRIANGLE | **+0.017** ✓ | **−0.027** ✓ | **−0.019** ✓ |

The long-horizon `neg_zscore_*` IC at h=1000 (OVAL +0.097, RECT +0.079, TRI +0.111
— all FDR-pass) **does not give h=1 alpha**. None of the `neg_zscore` ICs at h=1 or
h=10 are FDR-pass. The h=1000 IC captures slow drift, same trap as PANEL.

The reliable, short-horizon edge in this family is **OBI_L3 fade** at h=1 / h=10:
4–5 of 5 products consistent, IC −0.02 to −0.03, FDR-pass. This is a *book-pressure
fade* — depth at L3 is contrarian over 1–10 ticks. Useful as a quote tilt, not as a
standalone taker.

---

## Sanity check — ARE these naive-MM-tradeable?

Naive top-of-book MM under the IMC `worse` fill model fills when a market trade
crosses your improved-touch quote. Required:
- `quote_update_freq` ≈ 1 (you can re-quote every tick) ✓ all five at 0.97–0.99.
- `n_trades / n_ticks` not zero — there must be *some* trade flow.
- `spread ≥ 2` so `bid+1 / ask-1` does not cross.

All 5 share `n_trades=569` over 30k ticks (≈ 1.9% of ticks have a trade) and
`spread ≥ 2` always. So fill opportunities exist but are sparse.

**Worry**: SQUARE has `spread_median=12` and `l10_sat=0.001`. Position rarely
saturates because spread is wide — fills are rare. May still be net positive (round
trip = 10 ticks of spread × small fill count) but **expect SQUARE to be the
weakest** of the five.

---

## Pair candidates

| Pair | corr | coint_p | residual | comment |
|---|---:|---:|---|---|
| OVAL ↔ TRIANGLE | +0.87 | 0.053 | stationary | OVAL trends hard (−4466 / 30k); pair hedges out the trend |
| **SQUARE ↔ RECTANGLE** | **−0.88** | **0.020** | stationary | **strongest coint p in entire round-5 universe**; negatively correlated → unusual structure |

`feedback_pair_disjoint_legs`: a symbol must appear in at most one pair. Disjoint
assignment OVAL↔TRI + SQUARE↔RECT covers 4 of 5 products; CIRCLE has no pair.

`feedback_pairs_screen`: don't trust coint_p alone. SQUARE↔RECTANGLE has corr=−0.88,
which beats most positive-corr pairs even before cointegration. Half-life and rolling
β stability still need to be checked before sizing it.

---

## Strategy plan — iron-rule rungs

Per [`mm_strategies_research.md §0`](mm_strategies_research.md#0-iron-rule--start-simple-add-one-thing-at-a-time):
add one thing per validation cycle.

### Rung 0 — naive MM on all 5 (deploy first)

Recipe: identical to [`strat_panel_naive_mm.py`](strats/strat_panel_naive_mm.py)
(BT +54,985 / 3 days on PANEL, 3 of 5 products).
- `qty = remaining_capacity` (proven scaling on UV: ORANGE went from +2,697 with
  `qty=1` to +4,124 with `qty=cap`).
- `spread ≥ 2` gate.
- Quote inside touch: `bid = best_bid + 1`, `ask = best_ask − 1`.
- `POSITION_LIMIT = 10`.

Apply to **all 5 products** (CIRCLE / OVAL / SQUARE / RECTANGLE / TRIANGLE).
Expected per-product live PnL on the analogous PANEL benchmark (BT ≈ 18.3k per
product avg → live × 0.10 inflation ≈ 1.8k):

| Product | Expected live PnL | Notes |
|---|---:|---|
| CIRCLE | +0.5–1.5k | already +264 with `qty=1`; `qty=cap` should lift |
| OVAL | +1–2k | l10_sat=0.30 (highest in family) — fills frequent; trend a tailwind for MM if bias mild |
| SQUARE | −500 to +500 | spread=12 wide but l10_sat=0.001 — few fills; could be net neutral |
| RECTANGLE | +1–2k | l10_sat=0.23, similar to OVAL |
| TRIANGLE | +1.5–2.5k | already +1,528 with `qty=1`; `qty=cap` should lift |

Stack target ≈ **+4–7k live**. Per-day positive on every BT day is the gate; drop any
product that goes negative on D2 / D3 / D4.

### Rung 1 — drop losers, keep winners

After rung-0 BT: keep only the products that pass per-day positivity. PANEL kept 3
of 5 (1X4, 2X2, 2X4); kicked 1X2 (−18,751) and 4X4 (−4,729). Expect a similar
filter here — likely SQUARE drops, possibly OVAL if the −5k drift hurts MM.

### Rung 2 (optional, only if rung 1 wins by ≥ 5%) — OBI_L3 fade tilt

For each surviving product, shift the fair away from depth-heavy side at L3:

```
obi_l3 = (sum_depth_3_bid - sum_depth_3_ask) / (sum_depth_3_bid + sum_depth_3_ask)
fair   = mid - c * obi_l3            # NEGATIVE because IC is negative (fade)
bid    = round(fair) - 0  i.e. quote-inside-touch from the shifted fair
ask    = round(fair) + 0
```

Pick `c` from the IC: `c ≈ |IC| × ret1_std × √(window for OBI norm)`. With
IC ≈ −0.027 and ret1_std ≈ 13, expect `c ≈ 0.35` ticks per unit of OBI — small.

**Validate via attribution control** (`feedback_external_signal_redundancy`): run
identical strategy with OBI tilt off, compare. Don't ship if delta < 5%.

### Rung 3 (optional, only if rungs 1+2 are stable) — SQUARE↔RECTANGLE pair

**Only** add if rung 1 confirmed both SQUARE and RECTANGLE are tradeable on naive MM.
If SQUARE was dropped at rung 1, also skip the pair (no leg to hedge with).

Spec:
1. Compute β by full-sample OLS of `mid_RECTANGLE` on `mid_SQUARE`.
2. Spread `s_t = mid_RECT − β · mid_SQUARE`. Z-score with rolling-100 mean / std.
3. Enter at |z|>2.0, exit at |z|<0.5 (use 555509 slp_cp ENTER_Z=1.6 as a starting
   point, adjust for half-life).
4. Per-leg unit = 1 (limit=10, naive MM also takes capacity — don't double-book).
5. Disjoint with OVAL↔TRIANGLE pair (don't ship both unless capacity allows).

### What we are NOT shipping

- ❌ MR z-score taker on h=50/h=100 anchor (PANEL trap).
- ❌ Long-horizon h=1000 IC trades — they catch drift, not reversion.
- ❌ Spike-conditional taker on TRI/SQUARE/RECT/OVAL (already failed per-day gate
  in `vol_spikes` study).
- ❌ DARK_MATTER / PLANETARY_RINGS analogues — not in this family, but the same
  reasoning kills any "structural MR + h=1000 IC" template here.

---

## Backtest plan

```bash
# Python BT
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round5/strats/strat_microchip_naive_mm.py 5--2 5--1 5-0

# Rust cross-check
imc_trading/prosperity_rust_backtester/target/release/rust_backtester.exe \
  --trader round5/strats/strat_microchip_naive_mm.py --dataset round5
```

Gate: per-product per-day PnL ≥ 0 on D2 / D3 / D4 (reject if any single day-product
combination is negative). Apply round-5 BT-inflation budget (`feedback_bt_inflation_round5_mm`):
target live = BT × 0.10.

## Backtest results — rung 0 naive MM (all 5 products, qty=cap)

Both engines (Python `prosperity4bt` + Rust `rust_backtester`) agree to within
rounding (Δ = +0.5 over 3 days = 0.001%). Same code, same fill model.

| Day | CIRCLE | OVAL | SQUARE | RECTANGLE | TRIANGLE | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| D2 | +222 | +4,638 | +1,475 | +12,737 | +4,961 | **+24,032** |
| D3 | **−1,208** | +5,001 | **−965** | +5,495 | **−938** | **+7,385** |
| D4 | +11,367 | +1,036 | +8,195 | **−13,556** | +8,191 | **+15,233** |
| **Sum** | +10,381 | +10,675 | +8,705 | +4,676 | +12,214 | **+46,650** |
| **Strict gate** | ❌ D3 | ✅ | ❌ D3 | ❌ D4 | ❌ D3 | |

**Strict per-day gate (`feedback_per_day_positive_selection`): only OVAL passes.**
4 of 5 products have one negative day. Three of those are small D3 losses (−938 to
−1,208) dwarfed by D2/D4 wins. **RECTANGLE D4 is the outlier**: −13,556 in a single
day, large enough to materially threaten any live submission that includes it.

### Per-product diagnosis

- **OVAL** ✅: positive every day, BT +10,675. **The only strict-gate ship-it pick**.
  Live projection (BT × 0.10) ≈ +1,000 SS. With higher actual ratios sometimes
  observed (TRIANGLE 549159 D5 +1,528 vs BT D4 +8,191 ≈ 18.6% live realisation),
  realistic range ≈ +1.0–2.0k.
- **CIRCLE** ⚠️: D3 −1,208 / +10,381 total. D3 loss is ~12% of D4 win — small
  fail. Risk profile manageable.
- **SQUARE** ⚠️: D3 −965 / +8,705 total. D3 loss is ~12% of D4 win. Wide spread
  (median 12) but l10_sat=0.001 had been a worry — turns out the few fills it
  does get are profitable.
- **TRIANGLE** ⚠️: D3 −938 / +12,214 total. D3 loss <8% of D4 win. **Best total
  in family**. Already +1,528 live with `qty=1`; `qty=cap` likely lifts.
- **RECTANGLE** ❌: D4 −13,556 / +4,676 total. **Largest single-day loss in the
  family by 14×**. Pattern is qualitatively different from the other 3 fails
  — looks pathological, not just per-day variance. Don't ship.

### Decision matrix

| Variant | Products | BT total | BT/day std | Live est. (× 0.10) | Risk |
|---|---|---:|---:|---:|---|
| Strict gate | OVAL only | +10,675 | 1,977 | ~1,070 | very low |
| Relaxed (drop pathological) | CIRCLE, OVAL, SQUARE, TRIANGLE | +41,975 | 7,196 | ~4,200 | medium (3 products have one small D3 loss) |
| Naive (ship all 5) | all | +46,650 | 8,427 | ~4,665 | high (RECTANGLE D4 −13,556) |

### Recommendation — STRICT (rung 0 ship)

Ship **OVAL alone** as the rung-0 baseline. Expected live ≈ +1k. Combined with the
existing live wins (TRIANGLE +1,528 from 556909 with `qty=1`, CIRCLE +264 from
549159), family live total projection: **~+2.8k** (vs current +1,792 baseline,
+1.0k uplift).

**However**: the established live evidence (TRIANGLE 18.6% BT/live realisation)
suggests the strict gate may be over-conservative for naive MM on this family. The
relaxed variant — ship 4 of 5 (drop only RECTANGLE) — has a defensible argument:
the D3 losses on CIRCLE/SQUARE/TRIANGLE are < 12% of their best winning day, well
below RECTANGLE's catastrophic D4 loss. Per `feedback_alpha_not_backtest`, the
*structural* alpha here is naive-MM-on-naive-MM-friendly-books — the same
structural argument that paid off on UV / TRANSLATOR / ROBOT.

### Recommendation — RELAXED (proposed escalation, awaiting user sign-off)

Ship **CIRCLE + OVAL + SQUARE + TRIANGLE** (drop RECTANGLE). Expected live:
~+4k–6k. Risk: ~+800 to −1,500 D3-day swing if D5 looks like D3. Reward: ~+3.5k
above strict gate.

Final call belongs to the user — both options are documented above.

### Next rung (deferred until rung-0 live result)

- Investigate **RECTANGLE D4 anomaly**. Walk the trade log; see whether it's a
  single bad event (a spike?) or persistent throughout the day. If isolated, may
  be salvageable with a vol gate. If persistent, drop permanently.
- Only if rung-0 lands ≥ +3k live: graft OBI_L3 fade tilt (rung 2). The signal
  is FDR-pass on 4/5 at h=1, IC ≈ −0.027.
- Pair trade SQUARE↔RECTANGLE deferred until RECTANGLE pathology is understood —
  pair-leg PnL on a one-sided pathology pollutes the basket.

---

## Comparison vs current best — naive vs 556909-style smart MM

The naive recipe was a *deliberate* choice (rung 0). The current live winners
(TRIANGLE +1,528 from 556909, CIRCLE +264 from 549159) used different recipes.
Cross-checking: which template wins per product on BT?

**Smart variant** (`strat_microchip_smart_mm.py`): 556909's MM block lifted as-is,
all 5 MIC products with TRIANGLE's settings (INV_SKEW=2.0, MR_SKEW=1.5,
Z_TOXIC=2.5, BASE_QTY=10). Rung 0 + inventory skew + MR mid-bias as a SKEW
(not taker) + toxicity z-cutoff.

| Product | Naive D2/D3/D4 | Smart D2/D3/D4 | Winner | Strict-gate variant |
|---|---|---|:---:|---|
| CIRCLE | +222 / **−1,208** / +11,367 (+10,381) | +3,168 / **−1,339** / +12,304 (+14,133) | smart (BT) | neither passes |
| **OVAL** | **+4,638 / +5,001 / +1,036 (+10,675)** | +11,263 / **−4,206** / +561 (+7,618) | **NAIVE** | **NAIVE only** ✅ |
| SQUARE | +1,475 / **−965** / +8,195 (+8,705) | **−3,084** / +1,305 / +560 (−1,219) | naive | neither passes |
| **RECTANGLE** | +12,737 / +5,495 / **−13,556** (+4,676) | **+13,964 / +6,495 / +1,573 (+22,032)** | **SMART** | **SMART only** ✅ |
| TRIANGLE | +4,961 / **−938** / +8,191 (+12,214) | **−825 / −3,257** / +10,148 (+6,066) | naive (BT) | neither passes |

**Two big findings**:

1. **Smart RESCUES RECTANGLE**. Naive bleeds −13,556 on D4 (the pathology that
   forced the strict-strict-rule drop). Smart's MR-skew + Z_TOXIC kills the bleed
   and turns RECT into +22,032 / 3 days, all days positive — **passes strict
   per-day gate**. This is the highest single-product PnL in the family on either
   variant.

2. **MR-skew kills OVAL**. Naive +10,675 (all 3 days positive, only strict-gate-
   pass naive product). Smart drops to +7,618 with D3 cratering at −4,206 — the
   PANEL trap. OVAL's mid drift (−4,466 / 30k) is too steep; the rolling-200
   anchor lags and `mr_bias` skews the wrong direction during D3.

The naive vs smart winner is **per-product, not template-wide**. Hybrid wins.

### Hybrid (`strat_microchip_hybrid.py`) — best variant per product

Per-product routing decision:

| Product | Variant | Reason |
|---|---|---|
| OVAL | **naive** | only naive passes per-day gate (+10,675); smart D3 craters |
| RECTANGLE | **smart** | only smart passes per-day gate (+22,032); naive D4 catastrophe |
| TRIANGLE | naive | both fail per-day gate; naive +12,214 BT > smart +6,066 |
| CIRCLE | smart | both fail per-day gate; smart +14,133 BT > naive +10,381 |
| SQUARE | (drop) | smart 3-day total negative; naive D3 fails too |

**STRICT default** (both products pass per-day gate):

| Day | OVAL (naive) | RECT (smart) | Total |
|---|---:|---:|---:|
| D2 | +4,638 | +13,964 | **+18,602** |
| D3 | +5,001 | +6,495 | **+11,496** |
| D4 | +1,036 | +1,573 | **+2,609** |
| **Sum** | **+10,675** | **+22,032** | **+32,707** |

Family-level all 3 days positive. Live projection BT × 0.10 ≈ **+3.3k**;
TRIANGLE's empirical 12.5% ratio ≈ **+4.1k**.

**RELAXED variant** (also include CIRCLE-smart + TRIANGLE-naive — drop SQUARE):

| Day | OVAL (n) | TRI (n) | RECT (s) | CIRCLE (s) | Total |
|---|---:|---:|---:|---:|---:|
| D2 | +4,638 | +4,961 | +13,964 | +3,168 | **+26,731** |
| D3 | +5,001 | −938 | +6,495 | −1,339 | **+9,219** |
| D4 | +1,036 | +8,191 | +1,573 | +12,304 | **+23,104** |
| **Sum** | +10,675 | +12,214 | +22,032 | +14,133 | **+59,054** |

Per-product strict gate fails 2/4 (CIRCLE and TRIANGLE both have D3 < 0). But:
- D3 losses are **−1,339 (CIRCLE) and −938 (TRIANGLE)** — < 11% of their best
  winning day. PLANETARY_RINGS (the precedent that motivated `feedback_per_day_positive_selection`)
  had D3+D4 cumulatively cancel ~25% of its D2 gain. The shape here is much milder.
- Family-level all 3 days remain positive (+9,219 on D3 even with both losses).
- Live projection BT × 0.10 ≈ **+5.9k**; BT × 0.125 (TRIANGLE empirical) ≈ **+7.4k**.

### Recommended ship — STRICT default, RELAXED one comment away

`strat_microchip_hybrid.py` ships STRICT (OVAL naive + RECTANGLE smart) by default.
Both products satisfy the established `feedback_per_day_positive_selection` rule.

The RELAXED option (4 products, drop SQUARE) is documented in the file with the
comment-flip and lifts BT to +59,054. Whether to ship it is a judgement call:
- Pro: family-level per-day gate still passes; D3 losses on CIRCLE/TRIANGLE are
  small in magnitude and dwarfed by D2/D4 wins; live projection +6–7k materially
  improves the round-5 family ranking.
- Con: violates the per-product strict rule; PLANETARY_RINGS taught us "one bad
  day on n=3" is dangerous signal even when 3-day total is positive.

Final call: present user. Default file ships STRICT to honour the established rule.

### Files

- [`round5/research_microchip.md`](research_microchip.md) — this doc.
- [`round5/strats/strat_microchip_naive_mm.py`](strats/strat_microchip_naive_mm.py) — naive baseline (rung 0).
- [`round5/strats/strat_microchip_smart_mm.py`](strats/strat_microchip_smart_mm.py) — 556909-style.
- [`round5/strats/strat_microchip_hybrid.py`](strats/strat_microchip_hybrid.py) — hybrid per-product.

---

## Live result — submission 560161 (STRICT hybrid: OVAL naive + RECT smart)

Submitted [`round5/560161/560161.py`](560161/560161.py) = STRICT hybrid file
verbatim. Single-day live (D5).

| Product | Variant | BT total (3d) | BT D4 | **Live D5** | Live / BT-total |
|---|---|---:|---:|---:|---:|
| OVAL | naive | +10,675 | +1,036 | **+2,619** | 24.5% |
| RECTANGLE | smart | +22,032 | +1,573 | **−849** | **−3.9%** |
| **MIC family** | | **+32,707** | **+2,609** | **+1,771** | 5.4% |

**Family total +1,771** vs prior MIC best **+1,792** (TRI 556909 + CIRCLE 549159) →
**−21 SS, statistically zero**. The hybrid neither helped nor hurt at family level.

But the *composition* changed:
- **OVAL naive PROFITED +2,619 live** with 24.5% realisation — **higher than the
  12.5% TRIANGLE-empirical anchor**. Confirms naive MM on naive-MM-friendly
  trending mid is robust.
- **RECTANGLE smart LOST −849 live** despite +22,032 BT (one of the highest
  per-product BT totals in the family). The SMART variant blew up on live.

### Forensic reconstruction — why RECT smart failed

8 own-fills on RECT, walked through:
```
ts=24700 SELL 3 @ 8003 → pos=-3
ts=26200 BUY  2 @ 7998 → pos=-1
ts=29700 BUY  3 @ 7940 → pos=+2     ← started loading long as mid fell
ts=73100 BUY  3 @ 7659 → pos=+5
ts=79300 BUY  3 @ 7592 → pos=+8     ← max long, mid still falling
ts=87300 SELL 1 @ 7571 → pos=+7     ← forced to sell at lower price
ts=94300 SELL 3 @ 7602 → pos=+4
ts=97400 SELL 1 @ 7611 → pos=+3
final: pos=+3, mid=7574 → MTM −849
```

Mid drifted **8003 → 7574 (−429 ticks, −5.4%)**. Smart's MR-skew
(`mr_bias = MR_SKEW · (mu_px − mid) / σ`) saw mid below rolling-200 mean and
lifted both bid and ask **upward** to lure long inventory — the "mean-reversion"
prior. RECT didn't mean-revert; it kept trending. **Smart caught the falling
knife by design**.

This is exactly the PANEL h=1000-IC trap (mid drifts persistently while the
rolling anchor lags), now confirmed on RECTANGLE LIVE. The MR-skew lost money
*even though it was a skew, not a taker* — the bias still pulled inventory the
wrong way. The Z_TOXIC=2.5 cutoff did not save it because the rolling-200
anchor moved with the trend slowly enough that |z| stayed below 2.5.

### Forensic reconstruction — why OVAL naive worked

OVAL mid drifted **7400 → 6964 (−436 ticks)** — same direction as RECT, similar
magnitude. Naive accumulated SHORT inventory passively (sold at 7408, 7313,
7240, 7229) as the mid rolled down, then partially covered at 7151, 7128. Final
pos=−6 short with 22 fills, MTM +2,619.

Same trend, **opposite outcome**: naive harvests spread + benefits from
short-bias on a falling mid; smart's MR overlay forces longs into the same fall.

### Reassessment — n=1 live is noise

**Initial reaction (now retracted)**: I drew strong conclusions from the n=1
live result — "MR-skew is a trending trap", "OVAL naive is robust at 24.5%
realisation", "drop RECT smart entirely". Those generalisations are not
supported by a single day of data.

**What the data actually says**, accounting for round-5 BT-inflation (~10×):

| Product | BT 3-day | Expected live (× 0.10) | Actual live D5 | Surprise |
|---|---:|---:|---:|---:|
| OVAL naive | +10,675 | +1,068 | +2,619 | +1,551 (UP) |
| RECT smart | +22,032 | +2,203 | −849 | −3,052 (DOWN) |
| **Family** | +32,707 | +3,271 | +1,771 | −1,500 (DOWN) |

The family-level realisation of **5.4%** sits inside the 1–11% empirical band
(`feedback_bt_inflation_round5_mm`: 550714 = 1%, v2 = 11%). **Both products are
within reasonable BT-inflation noise of expected**. We cannot distinguish "smart
is structurally bad on trending mids" from "smart caught a bad day, will be fine
on the next one" with one observation.

The forensic walk-through *is* factually correct: smart's MR-skew did pull longs
in as the mid fell, and that mechanically caused the inventory shape that
mark-to-market'd at −849. But:

- The **counterfactual is unknown**: naive RECT BT D4 was −13,556 (naive's own
  trending-day pathology). We do not know what naive RECT would have done on D5
  live without running a counterfactual on the live order book. Plausibly naive
  RECT loses MORE than smart's −849 on the same day.
- The PANEL precedent I cited is for **MR z-score taker**, not MR-skew. Different
  mechanism, different magnitude, different evidence weight. Conflating them was
  the overfit move.

### What we CAN say from n=1

- OVAL naive earned +2,619 on D5 (real number, additive to baseline).
- RECT smart earned −849 on D5 (real number, marginal loss inside BT-noise).
- Family delivered +1,771 vs prior +1,792 baseline — flat.
- One day is too few to update the prior on either variant. Keep both options
  open until n ≥ 2.

### What we CANNOT say from n=1

- "MR-skew is a structural trap on trending mids" — would need n ≥ 2 with same
  failure pattern to claim that. The PANEL trap was observed in *BT* on 3 days
  with 5 products = 15 product-days of consistent loss. The RECT case is 1
  product-day.
- "OVAL naive's realisation (24.5%) beats the 12.5% TRIANGLE rule" — single
  observation, not a rule update.
- "STRICT gate didn't catch a real failure" — STRICT gate gave a +1,068 EV on
  OVAL and +2,200 EV on RECT; total +3.2k. We landed +1.7k. That's within
  noise, not a gate failure.

### Decisions for next submission (revised)

- **Re-ship the same hybrid (OVAL naive + RECT smart) for ≥ 1 more live day**
  before concluding either way. n=1 is not enough to drop RECT smart.
- If RECT smart loses again on a second live day, drop. If it wins, n=2
  positive-on-aggregate makes the BT projection credible.
- **OVAL naive is a confirmed positive contributor on n=1.** Keep but don't
  promote. Replication needed.
- **Counterfactual experiment (proposed)**: extract D5 order-book and trade flow
  from `560161.log`, run naive-RECT through the same fill model, see what naive
  would have done on the same day. Only takes one script. Resolves the
  smart-vs-naive question on D5 specifically without committing capital.
- **Do NOT add new feedback rules from this submission** until replicated.
- The earlier conservative recommendation — try **OVAL naive + TRIANGLE naive +
  CIRCLE naive** — remains reasonable on its own merits (all 3 are naive, all 3
  passed BT thresholds with similar profiles) but should not be sold as
  "responding to RECT-smart's failure".

---

## Sources for this analysis

- [`reports/MICROCHIP/stats_per_product.csv`](reports/MICROCHIP/stats_per_product.csv)
- [`reports/MICROCHIP/signals_ic.csv`](reports/MICROCHIP/signals_ic.csv)
- [`reports/MICROCHIP/tradeable_ideas.md`](reports/MICROCHIP/tradeable_ideas.md)
- [`reports/MICROCHIP/microstructure.csv`](reports/MICROCHIP/microstructure.csv)
- [`reports/MICROCHIP/volatility.csv`](reports/MICROCHIP/volatility.csv)
- [`reports/MICROCHIP/cointegration.csv`](reports/MICROCHIP/cointegration.csv)
- Memory: `feedback_alpha_not_backtest`, `feedback_per_day_positive_selection`,
  `feedback_bt_inflation_round5_mm`, `feedback_pair_disjoint_legs`,
  `feedback_simple_first_mm`, `project_round5_panel`,
  `project_round5_best_per_family`.
