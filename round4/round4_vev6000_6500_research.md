# VEV_6000 / VEV_6500 — research log

Goal: identify exploitable edge in deep-OTM strikes 6000 and 6500.

## 1. Structural facts (r3 + r4, all 6 days)

- Order book locked at **bid=0 / ask=1** every single tick (10000/10000 across all days, both strikes).
- Only one level on each side; L2 / L3 always empty.
- Bid volume range: 6–34 contracts (median ~15–22). Ask volume similar.
- Mid = 0.5 every tick → reported "fair" of 0.5.
- Trade prints: **100% at price 0**, no exceptions across r3 D0–D2 and r4 D1–D3.

## 2. Counterparty flow (r4 only — CP IDs)

- **Buyer = Mark 01, Seller = Mark 22** on 100% of trades. No other CPs touch these strikes.
- Trade quantities for VEV_6000 and VEV_6500 are **byte-identical** per timestamp (paired bot artifact). Day totals: D1 345/345, D2 337/337, D3 423/423.
- Mark 22 also dominates seller side on VEV_5300 / 5400 / 5500 → `Mark 22 = systematic OTM call seller`. Mark 01 is the matching buyer at the bid for the deepest-OTM tail (6000/6500) only.
- Per-tick check: Mark 22's market-sell quantity is **never larger** than Mark 01's bid_volume_1 on the same tick (max overflow = -5 across all days). Mark 01 absorbs every Mark 22 sell entirely.

## 3. Empirical fair value

VE realized vol per-tick σ ≈ 2.17e-4, σ_annualized ≈ 34%. With S₀ ≈ 5260 and TTE = 4 trading days:

| Strike | log(K/S) | P(S_T ≥ K) | Empirical fair value |
|--------|----------|------------|----------------------|
| 6000   | 0.13     | ~0.001     | ~$0.001              |
| 6500   | 0.21     | ~0.00001   | ~$0                  |

Mid = 0.5 corresponds to BS implied vol of **42–63 % (6000)** / **63–92 % (6500)** — the integer-tick floor inflates implied. True fair value is essentially 0 under realized dynamics.

## 4. PnL mechanic (prosperity4bt)

`tools/log_creator.py`:
```python
product_profit_loss += position * row.mid_price
```

→ booked PnL = realized cash + position × mid. Mid is permanently 0.5 for both strikes. Therefore each 1 contract held at cost 0 books **+0.5 m2m**. Position cap 300 → cap-out books **+150 / voucher**.

## 5. Fill-mode test (probe trader: bid full size at price p)

| Mode               | Bid 0  | Bid 1   | Ask 0    | Ask 1 |
|--------------------|--------|---------|----------|-------|
| `server_like` (default CLI) | 0 fills | fills @1, **−150** | fills @0, position −300 | 0 fills |
| `worse`            | 0 fills | fills @1, **−150** | fills @0 | 0 fills |
| `all`              | **fills @0, +150/voucher/day** | fills @1, −150 | fills @0 | 0 fills |

Default fill model (server_like) requires the trader's bid to **strictly improve** the leftover best bid. Our bid at 0 ties Mark 01's bid at 0 → no fill. Bidding 1 is the only way to take fills against historical market prints — but pays $1 for an option worth ~$0.

## 6. Why BT in `all` mode doesn't translate to live

`--match-trades all` allows equal-price matching against historical prints. In `all`, our bid at 0 hoovers up Mark 22's market sells at price 0 → +900 across r4 days.

Live exchange is FIFO with strict-improve semantics (= server_like). Live obstacles:
- Mark 01's bid_volume_1 (11–34) refreshes every tick.
- Mark 22's per-tick sell quantity is always **≤** Mark 01's bid size (max overflow = -5, i.e. Mark 01 always absorbs the entire flow).
- We can't outbid at 0.5 (integer ticks) → next valid price is 1, which crosses the spread.

**Conclusion: the +900 BT edge is a backtester quirk. In live, queue sits behind Mark 01 forever and gets ~0 fills.**

## 7. What's actually exploitable (ranked)

### Tier 1 — none structurally
There is no integer-tick price that lets us extract value: bid 0 ties Mark 01, bid 1 pays full mid, ask 0 sells against bid (negative carry), ask 1 has no historical taker.

### Tier 2 — Mark 22 as a flow signal (untested, plausible)
- Mark 22 systematically dumps OTM call tail every day → short-vol bias.
- Hypothesis: Mark 22's per-tick volume in 6000/6500 should correlate with **lower** realized vol on VE going forward (Mark 22 is "right" about vol).
- Counter-hypothesis: Mark 22 is the toxic seller (already known signal on HP — `project_round4_m22_fade`). Mark 22 dumping vol → **fade** = expect higher vol → bid wider on ATM strikes when Mark 22 is active.
- Tested: per-tick Mark 22 sell quantity vs ΔVE over 100/500/1000 ticks → r ∈ [-0.12, +0.16] across days. **Noise; no directional signal at simple correlation level.**

### Tier 3 — convexity hedge (cost ≥ 1 / option)
If exposed short-gamma elsewhere (e.g. short ATM straddle), pay 1 to lift VEV_6000 ask as cheap insurance. Pure cost; only useful as risk decoration, not alpha.

### Tier 4 — sell ask 1 and hope
Post ask at 1 (joining Mark 22's standing ask). If any *new* taker (other team) lifts at 1, EV ≈ 1 − 0.001×250 = **+0.75/option**. No historical evidence anyone lifts. Place orders cost-free; accept that they probably never fill.

## 8. Strategy: passive bid-at-0 (zero-cost option)

Implemented in [`trader_r3options_deepotm.py`](trader_r3options_deepotm.py)
— fork of `trader_r3options_trendaware.py` with one block added at end of
`run`:

```python
for sym in ("VEV_6000", "VEV_6500"):
    if sym not in state.order_depths:
        continue
    pos = state.position.get(sym, 0)
    slack = OPT_BASE_LIMIT - pos
    if slack > 0:
        result[sym] = [Order(sym, 0, slack)]
```

Backtest r4 D1+D2+D3 vs trendaware baseline:

| Mode | Baseline (trendaware) | deepotm | Δ |
|------|----------------------:|--------:|--:|
| `server_like` (default) | 101,764 | 101,764 | **0** |
| `--match-trades all` | 101,764 | **102,664** | **+900** |

Per-day deepotm in `all` mode: each strike books +150 m2m every day, ramps to position cap fast.

**Live expectation.** Live engine semantics ≈ server_like (strict bid-improvement) with FIFO time priority within a level. Two scenarios:

- **Pro-rata or random-priority within level:** our 280-contract bid alongside Mark 01's 11–34 captures the bulk of Mark 22's per-tick flow. ~+900 / round books, scaling with however much of the flow we intercept.
- **Strict-FIFO with Mark 01 always first:** our bid sits behind Mark 01 forever, Mark 22's per-tick sell volume never overflows past Mark 01 (max overflow = -5 across all 6 days), → 0 fills. **Cost: 0. Risk: 0.** Same as not running it.

**Downside is bounded at 0.** No capital tied up unless fills occur, no inventory risk on a $0.001-fair option held to a 0.5-mid mark. Worst case the order sits on the book forever and we book nothing. Best case, +900 / round materializes from carry the rest of the field is paying Mark 01 for.

**Hard rules baked into the strategy.** Never bid >= 1 (lifts ask, pays $1 per ~$0 option). Never ask <= 0 (sells short against bid, negative carry vs mid 0.5). Both are explicit losses confirmed by probe BT (-300 / day each).

## 9. Mark 22 as flow signal (separate, not yet implemented)

Mark 22's per-tick volume in 6000/6500 is a clean readout of the systematic OTM-vol seller's activity. Hypothesis: spikes in Mark 22 OTM dumping correlate with vol regime — testable as a conditioning variable on the 5400/5500 pricer where edge actually lives. Per `feedback_external_signal_redundancy`, gate any deployment on attribution-vs-anchor-mean-rev passing, not raw correlation.

Quick test on r4: simple correlation of Mark 22 sell qty vs ΔVE over 100/500/1000 ticks → r ∈ [-0.12, +0.16]. Noise at zero-lag; deeper analysis (vol/volume-conditioned conditional moments) not yet done.

## 10. Reproduction

```bash
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"

# baseline trendaware
.venv/Scripts/python.exe -m prosperity4bt round4/trader_r3options_trendaware.py 4-1 4-2 4-3 --no-out --no-vis

# deepotm, default mode (no fills)
.venv/Scripts/python.exe -m prosperity4bt round4/trader_r3options_deepotm.py 4-1 4-2 4-3 --no-out --no-vis

# deepotm, equal-price match (proxy for live arb)
.venv/Scripts/python.exe -m prosperity4bt round4/trader_r3options_deepotm.py 4-1 4-2 4-3 --match-trades all --no-out --no-vis
```
