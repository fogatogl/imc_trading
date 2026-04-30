# Round 2 — Growing Your Outpost

**Products:** `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` (limit 80 each — unchanged from round 1)
**Platform doc:** [`Round 2 - "Growing Your Outpost" ...md`](Round%202%20-%20%E2%80%9CGrowing%20Your%20Outpost%E2%80%9D%205503d50cdd2383dba5b301c0d9f213fa.md)

Round 2 has two parts: an algorithmic challenge ("limited Market Access")
and a manual challenge ("Invest & Expand").

## Algorithmic challenge — limited Market Access

Same instruments and limits as round 1. The new mechanic is a one-time
**Market Access Fee (MAF)** auction: a `bid()` method on the `Trader`
class declares how many XIRECs you would pay for ~25 % more order-book
depth. The top 50 % of bids across all participants get extra access and
pay the price they bid. The MAF is subtracted from round-2 profit:

```
profit = round_2_pnl − bid       (if bid is in the top 50 %)
profit = round_2_pnl              (otherwise)
```

**What we shipped:** the round-1 trader was kept verbatim — see
[`final.py`](final.py). The `bid()` value chosen for the access auction
was set inside `final.py` and is the only round-2-specific change. The
research from round 1
([`../round1/ROUND1_STRATEGY.md`](../round1/ROUND1_STRATEGY.md),
[`../round1/ash_coated_osmium_analysis.ipynb`](../round1/ash_coated_osmium_analysis.ipynb))
applies unchanged.

## Manual challenge — Invest & Expand

Allocate a 50,000 XIRECs budget across three pillars:

- **Research** — log-growth `200_000 * log(1 + x) / log(101)`
- **Scale** — linear `7 * x / 100`
- **Speed** — rank-based across all players, multiplier in `[0.1, 0.9]`

Final PnL: `(Research × Scale × Speed) − budget_used`. Sub-100 %
allocation is allowed; only the part actually invested is deducted.

**Files:**

- [`manual.ipynb`](manual.ipynb) — clearing-price / pillar-multiplier
  analysis, expected-profit grid over allocations, robustness against
  the rank-based speed multiplier.
- [`invest_and_expand.tex`](invest_and_expand.tex) — written reasoning
  for the chosen allocation.
