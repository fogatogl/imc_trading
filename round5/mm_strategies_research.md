# Live Market-Making Arsenal — Round 5 Research Notes

Research compiled 2026-04-29. Goal: replace naive "best_bid+1 / best_ask-1" pattern (the
default MM scaffold used across round-5 attempts) with techniques actually documented to
work live. Backtest inflation (~10x) on round-5 MM means BT is a gating filter — only
techniques with theoretical justification *and* live track records get into the arsenal.

Each section: (1) what it is, (2) explicit formula, (3) code pattern, (4) when it helps,
(5) failure mode.

---

## 0. Iron rule — start simple, add ONE thing at a time

**This rule overrides everything else in this document.** The arsenal below is a
*menu*, not a recipe. Stacking techniques before validating each one in isolation is
the dominant failure mode of past round-5 strategies.

### Why complexity loses live

- Backtest inflation on round-5 MM is ~10× (`feedback_bt_inflation_round5_mm`).
  Each parameter you add fits noise; the more knobs, the more BT/live divergence.
- Closed-form models (AS, full microprice) assume Poisson fills, geometric Brownian
  mid, stationary OFI distribution — none holds in Prosperity simulator.
- Tight simple MM beat loose tuned MM live on PEBBLES even after losing 8.4k on BT
  (`feedback_pebbles_tight_mm_live`). Smaller surface = less to break.
- Hydrogel v9 (regime + EMA + cross-book) lost ~10k live vs +112k BT
  (`feedback_alpha_not_backtest`). The simple anchor + vol-armor (round-3 baseline)
  was the unlock.

### Mandatory progression

Build any new family strategy in this exact order. Each rung must beat the previous
on **per-day live-realised** PnL (or BT × 0.1 budget) before adding the next.

| Rung | Strategy | What it tests |
|---|---|---|
| 0 | Static anchor: `bid = anchor − w`, `ask = anchor + w`, posted inside touch | Is the family even tradeable? |
| 1 | Dynamic mid: `fair = (Pa + Pb) / 2`, post inside touch with vol-scaled half | Does mid move enough to need tracking? |
| 2 | Inventory skew: add `reserv = fair − k·pos` | Does inventory bleed dominate fills? |
| 3 | Take-then-make: cross any order favorable vs `fair − take_edge`, then post | Are there resting mispriced orders? |
| 4 | Weighted mid: replace mid with `I·Pa + (1−I)·Pb` | Is depth asymmetry predictive? |
| 5 | OFI alpha: add `fair += c1·zscore(OFI)` | Does flow predict 1-tick moves? |
| 6 | Toxicity guard: widen/pull on `tox_score > thr` | Are fills systematically adversely selected? |
| 7 | Asymmetric half-spread on OFI sign | Does directional toxicity have a sign? |
| 8 | AS closed form / full Stoikov microprice | Only if rungs 0–7 all paid off |

### Promotion criteria

A rung graduates only if **all** of:
1. Live PnL (or BT×0.1) ≥ previous rung +5% AND
2. Markout-1 (mean post-fill 1-tick markout in fill direction) ≥ 0 AND
3. Per-day positive on every BT day (`feedback_per_day_positive_selection`).

If a rung fails: roll back to the previous rung *and document why*. Do not stack.

### Anti-patterns to refuse

- "Let me add OFI + microprice + skew + toxicity guard in one PR." → No. One at a
  time, validate, commit, next.
- "The BT loves it, ship it." → No. BT is gating filter, not optimizer
  (`feedback_alpha_not_backtest`).
- "More features = better fair value." → False. Each feature has its own estimation
  noise that compounds. The fair value of a 50-product universe estimated from 3
  days of data is a fundamentally noisy object.
- "I'll calibrate γ, k, and σ jointly." → 3-parameter fit on 3 days = guaranteed
  overfit. Either fix two, or skip the model.

### One-line summary for future me

> The arsenal exists to be drawn from selectively. The best round-5 strategy uses
> at most 2–3 techniques from §1–§7, validated independently, with parameters
> chosen by reasoning about the family's data — not by joint BT optimization.

---

## 1. Microprice (Stoikov, 2017) — replaces naive mid as fair value

The mid is autocorrelated and not a martingale. The Stoikov microprice is, by
construction, the conditional expected mid given current (imbalance, spread) state.

### 1a. Quick microprice (weighted mid)

Cheap level-1 estimator:

```
I  = Vb / (Vb + Va)                # bid-volume share, in [0,1]
weighted_mid = I * Pa + (1 - I) * Pb
```

This is **not** a martingale (it has bid-ask bounce when I flips). But it is one-line
and beats naive mid.

### 1b. Full Stoikov microprice (Markov-chain adjustment)

State: discretized `(I_bucket, S_bucket)` where `S = Pa - Pb`. Estimate transition
matrix Q (state→state without mid move) and absorption R (state→mid move).
Adjustment converges in ~6 iterations:

```
G^1   = (I - Q)^-1  R  g   # g = tick-size vector of absorbed mid moves
G^k   = G^1 + Q G^(k-1)
microprice_t = mid_t + G^6[state_t]
```

Implement once per family using day-2 data; cache the lookup table; apply at runtime.

### 1c. When to use which

- **Low spread (1–2 ticks), large size at touch** — weighted_mid is enough, full
  microprice gain is small.
- **Wider books, asymmetric depth** — full microprice clearly better.
- **Round 5 limit=10 regime** — weighted_mid first; full microprice only for the 4–6
  edge-bearing families.

---

## 2. Order Flow Imbalance (OFI / OBI) as alpha

Two distinct quantities — easy to confuse:

| Name | Formula | Captures |
|---|---|---|
| **OBI (state)** | `(Vb - Va) / (Vb + Va)` | static order book asymmetry |
| **OFI (event)** | sum over events of: `+ΔVb if bid pushes up, -ΔVa if ask pushes down, ...` (Cont) | dynamic flow direction |

OFI is the predictor — out-of-sample R² ≈ 65% on US equities for high-freq returns.
OBI is a contemporaneous proxy that is much cheaper to compute.

### Cont-style OFI (level-1)

For each tick update:

```
e_n =  +ΔVb_n  if Pb_n  > Pb_{n-1}
       -Vb_{n-1} if Pb_n < Pb_{n-1}
       ΔVb_n   if Pb_n == Pb_{n-1}
       (mirror with negative for ask side)
OFI_t = sum of e_n over interval t
```

Multi-Level OFI (MLOFI) extends to depth >1; helps for large-tick assets (most round-5
products fit this).

### Wiring OFI into the quote

```
alpha_t   = c1 * standardize(OFI_t, rolling window 1h)
fair_t    = mid_t + alpha_t                 # OBI/OFI shifts perceived fair value
reserv_t  = fair_t - skew * (pos_t / pos_max)   # inventory pull
bid       = reserv_t - half_spread
ask       = reserv_t + half_spread
```

`hftbacktest` published parameters that produced Sharpe ~10–14 on crypto:

| Asset | half_spread (ticks) | skew | c1 | window |
|---|---|---|---|---|
| BTC/USDT (large tick=$1) | 80 | 3.5 | 160 | 1h |
| ETH/USDT (small tick) | 5 | 0.2 | 10 | 1h |

Round-5 ticks are 1; products are mostly small-tick; start near ETH-style: half_spread
2–5 ticks, skew ≈ 0.2–0.5, c1 estimated by regressing 1-tick-ahead returns on
standardized OBI.

---

## 3. Avellaneda-Stoikov (2008) — inventory-aware spread

Closed-form optimal bid/ask under a Brownian mid + Poisson fills + CARA utility:

```
reservation = S - q * gamma * sigma^2 * (T - t)
half_spread = (1/gamma) * ln(1 + gamma/k) + 0.5 * gamma * sigma^2 * (T - t)
bid = reservation - half_spread
ask = reservation + half_spread
```

Variables:
- `S`: mid (or microprice — substitute in)
- `q`: inventory (signed)
- `gamma`: risk aversion (try 0.1–2.0)
- `sigma^2`: per-step variance of mid
- `T - t`: time to horizon (in same units as sigma)
- `k`: order arrival intensity decay (fills/sec at half_spread=0)

### Practical use in Prosperity (1M ticks per "day")

The `(T - t)` term and gamma can be collapsed into a single inventory-skew constant
when you don't actually have an end-of-day liquidation requirement. The simplified
form that keeps the AS *spirit*:

```
reservation = mid - skew_const * q
half_spread = base + width_const * sigma_recent
```

This is exactly what the OBI section above calls "fair − skew·pos" plus a vol-scaled
spread. AS gives the *rigorous* form; in practice the closed-form rarely beats a
hand-tuned linear skew on 1M-tick simulations.

### When AS beats heuristic skew

- Long sessions with terminal-inventory penalty (we have one — flat at session end).
- High vol relative to spread — the quadratic risk term dominates.
- When `k` (arrival intensity) is well-calibrated from the actual book.

---

## 4. Adverse selection / toxic flow guards

Adverse selection = informed trader picks off your stale quote. This is the dominant
failure mode of naive MM. Three layers of defense:

### 4a. Detect — signals that flow is currently toxic

| Signal | Compute | Toxic when |
|---|---|---|
| Recent OFI sign and magnitude | last 5–20 events | one-sided, large |
| Spread widening | `S_t / S_rolling_median` | > 1.5× |
| Mid-price jump | `|mid_t - mid_{t-k}| / sigma_recent` | > 2.0 |
| One-sided trade run | last 3 trades all aggressing same side | yes |
| VPIN (Volume PIN, Easley-Lopez) | rolling buy-vol vs sell-vol abs-imbalance per volume bucket | > historical 90th pct |

VPIN is the standard practitioner toxicity gauge. Cheap version: maintain rolling
classified buy/sell volume (Lee-Ready or trade-side from `buyer/seller` field if
present), report `|Vbuy - Vsell| / (Vbuy + Vsell)` over last N volume buckets.

### 4b. Respond — what to do when toxic

Three escalating responses:

1. **Widen** the half_spread by `tox_mult * tox_score` (e.g. 1 + 2*z).
2. **Skew** asymmetrically — when OFI is positive (buying pressure), pull the *bid*
   in (or remove it) and keep the ask tight; you want to sell into informed buyers
   only at a higher price, and not keep posting a stale bid that will get taken
   right before the move.
3. **Pull** entirely — if `tox_score > kill_threshold`, post nothing this tick. The
   value of doing nothing > value of being adversely selected.

```python
def quote(mid, sigma, pos, ofi_z, spread_z):
    tox = max(0.0, ofi_z) + max(0.0, spread_z - 1.0)
    if tox > 3.0:
        return None, None                # pull
    half = base_half + width * sigma + tox_mult * tox
    skew = inv_k * pos + ofi_skew * ofi_z
    bid = mid - skew - half
    ask = mid - skew + half
    if ofi_z > 1.5:                      # asymmetric: lift ask, drop bid harder
        bid -= tox_asym * ofi_z
    elif ofi_z < -1.5:
        ask += tox_asym * (-ofi_z)
    return bid, ask
```

### 4c. Post-fill markout — measure actual adverse selection

After every fill, compute `markout(h) = sign(side) * (mid_{t+h} - fill_price)` for
h ∈ {1, 5, 20, 100} ticks. Toxic clients show negative markout 1-tick out and worse
20-ticks out. If a *family* shows persistently negative markout, that family's MM is
fundamentally negative-edge — switch to taker-only or skip it. **This was the
mechanism by which round-5 PLANETARY_RINGS lost −7,011 live** (per-day BT positive
but markout would have warned).

---

## 5. Queue position & the fill-probability/post-fill-return trade-off

In large-tick assets (round-5 ticks=1, integer prices, often 1–5 wide books — most
round-5 families qualify), queue position dominates fill probability. Two key results:

- **Fill probability decays exponentially** with distance from the touch. Posting
  inside (`bid+1`) gets ~5–10× the fills of `bid`. Confirmed live by round-5
  feedback: `feedback_maker_quote_inside_touch` (SNACKPACK pair: −86,930 → +975
  flipped solely by inside-quoting).
- **Negative correlation** between fill likelihood and post-fill return. The fills
  you get easily are the ones you wish you hadn't gotten. ⇒ **Contrarian quoting**:
  bias your quotes *against* the prevailing OBI direction. If buy pressure is high,
  you want to be the ask, not the bid (you fill less often, but the fills you get
  are the ones not informed).

Concrete: combine `fair = mid + c1·OBI` (which already shifts toward OBI) with
asymmetric *posting* — when OBI is strongly positive, post both quotes but make the
bid step *larger*-half-spread than the ask half-spread:

```
half_bid = base + tox_mult * max(0, ofi_z)
half_ask = base + tox_mult * max(0, -ofi_z)
bid = fair - skew*pos - half_bid
ask = fair - skew*pos + half_ask
```

Both layers (fair shift + asymmetric half) compound; that's the point.

---

## 6. Practitioner patterns from Prosperity-3 winners

Two top finishers (chrispyroberts: 1st USA 7th global, CarterT27: 9th global)
released code. Common patterns:

### 6a. Fixed anchor + 1-tick competitive overlay (chrispyroberts, RAINFOREST_RESIN)

```python
buy_price, sell_price = 9996, 10004    # static around fair=10000
if best_ask is not None and best_bid is not None:
    sell_price = best_ask - 1
    buy_price  = best_bid + 1
```

→ Post inside touch when there's a touch; fall back to fixed wide quotes when book
empty. **39k SeaShells per round** from this single product. Pattern: simple wins
when fair is known and stable.

### 6b. Persistent-MM-mid as fair value (chrispyroberts, KELP)

For products with one big resting market-maker, identify them once, then use
*their* mid (last/worst price in the book) as fair. Code:

```python
ask, _ = list(sell_orders.items())[-1]   # WORST ask = the big MM's ask
bid, _ = list(buy_orders.items())[-1]    # WORST bid = the big MM's bid
fair = (ask + bid) / 2
buy_price  = math.floor(fair) - 2
sell_price = math.ceil(fair) + 2
```

This treats small noise traders as uninformed and the big MM as informed.

### 6c. Skew via order *size* (CarterT27, MAGNIFICENT_MACARONS)

```python
position_ratio = abs(pos) / limit
if position_ratio > 0.3:
    scale = max(0.2, 1.0 - 1.5 * position_ratio)
    if pos > 0: buy_q  = int(base * scale)   # smaller longing add
    else:       sell_q = int(base * scale)
```

Skew the *quantity*, not the price. Works when you can't move price (tight book) but
need to slow inventory accumulation.

### 6d. Take-then-make ordering

Universal across winners:
1. Cross any resting orders that are already favorable vs your fair.
2. *Then* post passive maker orders inside the remaining touch.

This captures the cheap edge first (taker fill at favorable price) and the residual
spread second. Order matters: posting first then crossing doubles your size and
position.

### 6e. Trend-conditional one-sidedness (chrispyroberts, SQUID_INK)

```python
if long_mean < short_mean: buy_side = False    # uptrend → don't post bid
elif long_mean > short_mean: sell_side = False
```

Disable the side that would catch the trend in your face. Cousin of the asymmetric
toxicity response in §4b.

---

## 7. What I should stop doing (codified failures)

From `feedback_*` memory + this research:

- **Don't post AT touch** — `worse` mode means 0 fills. Always inside (`bid+1`).
- **Don't quote both sides equally under directional pressure** — asymmetric or pull.
- **Don't trust BT PnL alone** — round-5 MM BT/live ratio ≈ 10×. Compute markout per
  fill in BT and use it as the gating metric.
- **Don't pick products by 3-day total** — require positive on every day individually.
- **Don't add CP-fingerprint signals in round 5** — counterparties always blank.
- **Don't post passive maker after a spike to "fade"** — passive limit can't fill via
  reversion; spike direction crosses the wrong side.

---

## 8. A round-5 MM template combining the above

For a single family, single product, limit=10:

```python
def quote(state, product, params, history):
    od = state.order_depths[product]
    if not od.buy_orders or not od.sell_orders:
        return []
    Pb, Vb = max(od.buy_orders), od.buy_orders[max(od.buy_orders)]
    Pa, Va = min(od.sell_orders), -od.sell_orders[min(od.sell_orders)]
    spread = Pa - Pb
    mid    = (Pa + Pb) / 2

    # 1. Fair value = weighted mid + OFI alpha
    I       = Vb / (Vb + Va) if (Vb+Va) else 0.5
    wmid    = I * Pa + (1 - I) * Pb
    ofi_z   = history.update_ofi_zscore(product, Pb, Vb, Pa, Va)   # rolling 1h
    fair    = wmid + params["c1"] * ofi_z

    # 2. Toxicity guards
    spread_z = (spread - history.spread_med[product]) / max(1.0, history.spread_mad[product])
    tox      = max(0, ofi_z) * 0.5 + max(0, spread_z - 1.0)
    if tox > params["kill_thr"]:
        return []                                  # pull

    # 3. Inventory skew (price + size)
    pos      = state.position.get(product, 0)
    pos_ratio= pos / params["limit"]
    skew_px  = params["skew_k"] * pos
    base_h   = params["half_spread"]
    half_b   = base_h + params["tox_mult"] * max(0, ofi_z)
    half_a   = base_h + params["tox_mult"] * max(0, -ofi_z)

    bid = round(fair - skew_px - half_b)
    ask = round(fair - skew_px + half_a)
    bid = min(bid, Pb + 1)        # always inside touch (won't fire above ask)
    ask = max(ask, Pa - 1)
    if bid >= ask:                # crossed → widen by 1 tick each side
        bid, ask = bid - 1, ask + 1

    # 4. Size — skew quantity by position
    base_q   = params["qty"]
    scale_b  = max(0.2, 1.0 - 1.5 * max(0,  pos_ratio))   # shrink buy when long
    scale_a  = max(0.2, 1.0 - 1.5 * max(0, -pos_ratio))   # shrink sell when short
    qb = int(base_q * scale_b); qa = int(base_q * scale_a)

    orders = []
    # 5. Take-then-make
    if Pa < fair - params["take_edge"]:
        qty = min(qa_taker := params["limit"] - pos, Va)
        if qty > 0: orders.append(Order(product, Pa, qty))
    if Pb > fair + params["take_edge"]:
        qty = min(params["limit"] + pos, Vb)
        if qty > 0: orders.append(Order(product, Pb, -qty))
    # passive
    if qb > 0 and pos < params["limit"]: orders.append(Order(product, bid,  qb))
    if qa > 0 and pos > -params["limit"]: orders.append(Order(product, ask, -qa))

    return orders
```

Parameters to tune *per family* on day-2/day-3 BT, validated by day-4 markout:

| Param | Range | Notes |
|---|---|---|
| half_spread | 2–5 | tighter for tighter books |
| skew_k | 0.5–2.0 (per unit pos) | inventory pull |
| c1 | 0.5–5.0 | OFI gain |
| tox_mult | 1–4 | asymmetric widening on directional flow |
| kill_thr | 3–5 | how toxic before pulling |
| take_edge | 1–3 | minimum edge to cross |
| qty | 1–3 | base quote size (limit=10) |

---

## 9. Sources

- Stoikov, *The Micro-Price* (2017, SSRN 2970694)
- Avellaneda & Stoikov, *High-Frequency Trading in a Limit Order Book* (2008)
- Cont, Kukanov, Stoikov, *The price impact of order book events* — OFI definition
- Easley, Lopez de Prado, O'Hara, *VPIN: Flow Toxicity and Liquidity*
- Cartea, Jaimungal et al., *Algorithmic Trading with Adverse Selection*
- Moallemi, *The Value of Queue Position* (2014)
- Albers et al., *The Market Maker's Dilemma: Fill Probability vs Post-Fill Returns* (2024)
- hftbacktest docs — *Market Making with Alpha — Order Book Imbalance*
- chrispyroberts/imc-prosperity-3 — RAINFOREST_RESIN/KELP/SQUID_INK code
- CarterT27/imc-prosperity-3 — Magnificent Macarons code
