# Round 5 — Spike Mechanism Study

Companion to [`vol_spikes_report.md`](../vol_spikes_report.md). The
prior study found 8 of 50 products carry meaningful spike density.
This one asks **why** — what microstructural event creates the spike,
and **how** to use it.

Drivers:
- [`round5/spike_anatomy.py`](../../../../spike_anatomy.py) — per-product mechanism classifier.
- [`round5/spike_strategy_sim.py`](../../../../spike_strategy_sim.py) — fade-vs-follow taker PnL with limit=10.

## TL;DR

Volatility spikes in round-5 are **not** Gaussian tail events. They are the
visible artefact of three distinct microstructural regimes, each with a
different price-formation process and an opposite trading prescription:

| Mechanism | Members | What's happening | Trade |
|---|---|---|---|
| **QUANTIZED_QUOTE_REFRESH** | OXYGEN_SHAKE_EVENING_BREATH, ROBOT_IRONING, OXYGEN_SHAKE_CHOCOLATE | Spread is locked (12 / 6-8 / 12). The MM steps both quotes ±10 in lockstep. Mid jumps by 10 with no trade in 96-100% of cases. ~35-50% of jumps reverse within 200 ticks. | **FADE**: short the spike at next tick, hold ~20-200 ticks. Marginal as a taker (spread cost); strong as a maker. |
| **FAST_NOISE_OSCILLATOR** | ROBOT_DISHES | Mid is granular (80 unique \|ret\|s, smooth distribution), but `acf_lag1 = -0.232` — every tick reverts. "Spikes" are oversized samples from the oscillation, not regime breaks. | **FADE**: 117 events × +139 SS at h=20 = **+16.3k** over 3 days. |
| **PRICE_DISCOVERY_BREAKOUT** | MICROCHIP_RECTANGLE, MICROCHIP_SQUARE, MICROCHIP_OVAL | Spike *continues* — `reversion_pct_h50` is **negative** (-0.34, -2.18, -0.90). The spike is a real informational shock; price keeps moving. | **FOLLOW**: 33 events ≈ +6.6k at h=20, up to +12.7k on SQUARE alone at h=200. |
| HEAVY_TAIL_GAUSSIAN | MICROCHIP_TRIANGLE | Diffuse jumps, weak structure | Skip / re-examine. |

The current archetype classifier routes all 8 products to `MR_TAKER`. **The
3 PRICE_DISCOVERY products are misclassified — fading them loses money,
following them wins.** Recommended action: add a spike-conditional
override on top of the existing MR_TAKER for those three.

## Mechanism evidence

### 1. Quantized quote refresh (3 products)

`OXYGEN_SHAKE_EVENING_BREATH` day 2:
- **Spread**: 12 ticks, 87 % of the day; 14 ticks 9 %; 6 ticks 3 %. Locked.
- **Mid jumps**: 21 unique values; ±10 carries 43 % of all moves, ±20 another 10 %.
- **Trades at spike tick**: 1.8 % (1 of 56). The spike has nothing to do with flow.
- **Recovery curve**: 24 % at h=1 → 36 % at h=10 → 41 % at h=200. Half the move is permanent.

This is a market-maker stepping its book in fixed increments. Bid and ask
move together, spread stays locked. There is no aggressor crossing — the
trader is simply repricing fair value. From our side, the move is observable
*before* a counterparty appears, which is what makes it tradeable on the
maker side.

`ROBOT_IRONING` and `OXYGEN_SHAKE_CHOCOLATE` show the same pattern.
CHOCOLATE has slightly more jump diversity (top1 = 17 % rather than 43 %)
— smaller MM step layered on noise — which is why the partial-quantization
gate caught it.

### 2. Fast-noise oscillator (1 product)

`ROBOT_DISHES`:
- 80 unique jump sizes; smooth distribution (top1 = 5 %). No quantization.
- `acf_lag1 = −0.232` — every up-tick is followed by a down-tick on average.
- 47 % of the time spread = 8 (locked-ish), but mid takes 2,119 unique values.

This is a counterparty whose model produces fine-grained, fast-mean-reverting
quotes. Each "spike" is a draw from the upper tail of an already
heavy-mean-reverting series; the post-spike reversion is just the average
behaviour amplified.

### 3. Price-discovery breakout (3 products)

`MICROCHIP_SQUARE` (n=10):

| h | mean_reversion_frac | P(snap_back ≥ 50%) |
|---:|---:|---:|
| 1 | +0.18 | 0.20 |
| 5 | -0.43 | 0.20 |
| 10 | **-3.02** | 0.20 |
| 20 | **-3.68** | 0.20 |
| 50 | **-2.18** | 0.30 |
| 100 | +1.29 | 0.40 |
| 200 | -4.86 | 0.30 |

Negative reversion fraction at h=10..50 means the price *continues* in the
spike's direction by 3-4× the original spike magnitude. P(snap_back) stays
below 0.5 across all horizons within 200 ticks. The spike is not noise; it
is information being absorbed slowly into the price.

`RECTANGLE` (rev_h50 = -0.34) and `OVAL` (rev_h50 = -0.90) show the same
sign, smaller magnitude.

## Strategy simulation

Fade vs follow taker, position-limit = 10, entry on tick after spike,
exit at horizon `h`, full bid/ask cross at both ends. Aggregate over 3 days
(events independent — assumes flat between events).

**Best total PnL per product** (across `h ∈ {5, 10, 20, 50, 100, 200}`):

| Product | Best strategy | Best h | n_events | Total PnL | PnL/event | Hit rate |
|---|---|---:|---:|---:|---:|---:|
| ROBOT_DISHES | FADE | 20 | 117 | **+16,250** | +139 | 36 % |
| MICROCHIP_SQUARE | FOLLOW | 200 | 10 | **+12,730** | +1,273 | 70 % |
| ROBOT_IRONING | FADE | 200 | 50 | **+10,690** | +214 | 46 % |
| MICROCHIP_OVAL | FOLLOW | 200 | 5 | +4,810 | +962 | 80 % |
| MICROCHIP_TRIANGLE | FADE | 20 | 17 | +3,250 | +191 | 53 % |
| OXYGEN_SHAKE_EVENING_BREATH | FADE | 200 | 56 | +2,750 | +49 | 30 % |
| OXYGEN_SHAKE_CHOCOLATE | FADE | 5 | 60 | +880 | +15 | 30 % |
| MICROCHIP_RECTANGLE | FOLLOW | 20 | 18 | +340 | +19 | 44 % |

**Honest single-horizon estimate** (no per-product `h` cherry-picking) at
`h = 20`:

| Side | Products | Aggregate PnL @ h=20 |
|---|---|---:|
| FADE the quantized + oscillator | DISHES, IRONING, EVENING_BREATH, CHOCOLATE, TRIANGLE | **+20.5 k** |
| FOLLOW the price-discovery | SQUARE, RECTANGLE, OVAL | **+6.6 k** |
| **Total spike-conditional, 3 days, taker** | | **≈ +27 k SS** |

Per spike event: ~+96 SS (taker, after spread cost). Limit=10 already binds
the size — there is no further scaling. In live trading the expected daily
contribution from the spike layer alone is ~+9 k SS.

### Why fade is only marginal on EVENING_BREATH / CHOCOLATE

Spread is 12 ticks; the typical jump is 10 ticks; ~50 % reverts. Taking the
spread at entry costs 12; the recovered move is ~5 ticks; net per
event is small (~+50 SS at h=200, even worse at short h). The signed-cumret
edge of +37 ticks at h=10 reported in `vol_spikes_report.md` is computed
on **mid-to-mid** moves — it ignores the spread the taker pays.
**These two products only deliver real PnL via passive making**, which is
already what the existing `MR_TAKER` does (passive z-score quote with
inventory skew, not aggressor crossing).

DISHES has spread = 8 with ±10 jumps and `acf=-0.23` — taking pays the
8-tick spread once and harvests +20-tick reversion. That's the cleanest
edge of the eight.

## Classification refinement (recommendation)

| Product | Current archetype | Action | Strategy spec |
|---|---|---|---|
| ROBOT_DISHES | MR_TAKER (high) | Keep — confirmed | Existing `neg_zscore_mid_50` taker is right; the spike layer is a quantification of the same edge. |
| ROBOT_IRONING | MR_TAKER (high) | Keep — passive maker | Spread (6-8) > jump (10), so taker is marginal. Maker captures full move. |
| OXYGEN_SHAKE_EVENING_BREATH | MR_TAKER (high) | Keep — passive maker | Spread = 12 binds; passive maker only. |
| OXYGEN_SHAKE_CHOCOLATE | MR_TAKER (high) | Keep — passive maker | Spread = 12 binds; partial quantization. |
| **MICROCHIP_SQUARE** | MR_TAKER | **Override on spike → MOMENTUM/FOLLOW** | When `\|ret_1\| ≥ 4·std_500.shift(1)`, take *with* the spike, hold ~20-200 ticks. Otherwise current MR template. |
| **MICROCHIP_RECTANGLE** | MR_TAKER | **Override on spike → MOMENTUM/FOLLOW** | Same as SQUARE; smaller magnitude per event. |
| **MICROCHIP_OVAL** | MR_TAKER | **Override on spike → MOMENTUM/FOLLOW** | Same as SQUARE; n=5, low confidence — gate cautiously. |
| MICROCHIP_TRIANGLE | MR_TAKER | Keep — confirmed | n=17 fade still profitable (+3.3k); price-discovery signal absent. |

### Strategy template for PRICE_DISCOVERY products

Pseudo-code, drops in alongside the existing `MR_TAKER`:

```python
# spike-follow override on MICROCHIP_{SQUARE, RECTANGLE, OVAL}
sigma = std(ret_1, window=500).shift(1)
if abs(ret_1[-1]) >= 4 * sigma:
    # Spike just happened. Follow.
    target = sign(ret_1[-1]) * POSITION_LIMIT  # = ±10
    # Place taker order: cross spread to enter at next tick.
    # Hold ~20 ticks, then exit by reversing or letting MR_TAKER unwind.
else:
    # Default: existing neg_zscore_mid_50 anchor taker.
```

## Risk + caveats

1. **Sample size on PRICE_DISCOVERY** — RECTANGLE (n=18), SQUARE (n=10),
   OVAL (n=5). 30 follow events across 3 days × 3 products underpin the
   +6.6k figure. The single-event PnL on SQUARE is +1,273 SS — large
   enough that 1-2 outliers carry the result. Recommend gating the
   live deployment by an in-sample / out-of-sample split inside day 4
   alone, or a smaller fade size (e.g. 5 instead of 10) until more
   spikes are observed.
2. **Spread misalignment** — taker semantics in this sim cross the
   *displayed* L1. The IMC backtester fills against historical trades at
   *strict-worse* prices. Fade-take fills are conservative; follow-take
   fills require an aggressor at the new (post-spike) book — that is
   plausible because price-discovery spikes correlate with directional
   flow even when no trade occurs at the exact spike tick. Need to
   replicate this sim through `prosperity4bt` to confirm.
3. **Independent-events assumption** — the simulation re-flattens between
   events. In live trading at limit=10, two spikes within `h` ticks
   collide. ROBOT_DISHES has 117 spikes over 90k ticks → mean inter-arrival
   ~770 ticks, well beyond `h=20`; collisions are rare. CHOCOLATE has 60
   over 90k → 1500 ticks — also rare. No need for special handling
   beyond hard-cap at limit.
4. **No detection latency** — the sim uses `t+1` entry against `t+1`
   book. In live trading a tick of latency would shave the +10-tick
   move down by ~1-2 ticks per event. Still positive expected value.

## Outputs

| File | Content |
|---|---|
| [`spike_anatomy.csv`](spike_anatomy.csv) | per-product jump profile, spread profile, trade attribution, recovery, mechanism label, rationale |
| [`spike_recovery_curve.csv`](spike_recovery_curve.csv) | per-product × horizon: P(snap_back), mean reversion fraction |
| [`spike_strategy_pnl.csv`](spike_strategy_pnl.csv) | per-product × {FADE, FOLLOW} × horizon: total PnL, mean per event, hit-rate, sharpe |
| `figures/<P>_anatomy.png` | 3-panel: jump distribution, spread distribution, recovery curve |
| `figures/<P>_strategy.png` | 2-panel: total PnL & per-event PnL across horizons, fade vs follow |

## CLI

```bash
.venv/Scripts/python.exe round5/spike_anatomy.py        # mechanism classification
.venv/Scripts/python.exe round5/spike_strategy_sim.py   # fade-vs-follow PnL
```
