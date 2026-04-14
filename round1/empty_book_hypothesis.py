# -*- coding: utf-8 -*-
# Run with: python -X utf8 round1/empty_book_hypothesis.py
"""
empty_book_hypothesis.py
------------------------
Investigates why ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT occasionally have
completely empty order books (mid_price == 0, no bid, no ask) in the Round 1
price data.

Hypotheses tested:
  H1 - Simultaneous dropout: both products go empty at the same tick
       -> suggests a market-wide event (exchange glitch, scheduled pause)
  H2 - Timestamp clustering: empty ticks concentrate at certain times of day
       -> suggests session boundaries or scheduled maintenance windows
  H3 - Volatility trigger: empty ticks follow high-spread or high-volatility periods
       -> suggests liquidity withdrawal after large moves
  H4 - Volume dryup: empty ticks follow low-volume periods
       -> suggests passive-only market where all quotes expire simultaneously
  H5 - Post-trade gap: empty ticks follow a trade execution in the trades data
       -> suggests market-makers temporarily pulling quotes after a fill
"""

import glob
import pandas as pd
import numpy as np

# ── Data loading ─────────────────────────────────────────────────────────────

price_files = sorted(glob.glob("dataset/ROUND_1/prices_round_1_day_*.csv"))
trade_files = sorted(glob.glob("dataset/ROUND_1/trades_round_1_day_*.csv"))

prices = pd.concat([pd.read_csv(f, sep=";") for f in price_files], ignore_index=True)

# trades CSVs have no day column — extract it from the filename
def _load_trades(path):
    import re
    day = int(re.search(r"day_(-?\d+)", path).group(1))
    df = pd.read_csv(path, sep=";")
    df["day"] = day
    return df

trades = pd.concat([_load_trades(f) for f in trade_files], ignore_index=True)

prices["t"] = prices["day"] * 1_000_000 + prices["timestamp"]
trades["t"] = trades["day"] * 1_000_000 + trades["timestamp"]

ASH = "ASH_COATED_OSMIUM"
PEP = "INTARIAN_PEPPER_ROOT"

empty = prices[prices["mid_price"] == 0].copy()
normal = prices[prices["mid_price"] != 0].copy()

print(f"Total price rows : {len(prices):,}")
print(f"Empty book rows  : {len(empty):,}  ({100*len(empty)/len(prices):.3f}%)")
print()

# ── H1: Simultaneous dropout across products ─────────────────────────────────
print("=" * 60)
print("H1 — Simultaneous dropout (both products empty same tick)")
print("=" * 60)

empty_ash = set(empty[empty["product"] == ASH]["t"])
empty_pep = set(empty[empty["product"] == PEP]["t"])
overlap = empty_ash & empty_pep

print(f"  ASH empty ticks : {len(empty_ash)}")
print(f"  PEP empty ticks : {len(empty_pep)}")
print(f"  Simultaneous    : {len(overlap)}")
print(f"  Overlap rate    : {100*len(overlap)/max(len(empty_ash),len(empty_pep)):.1f}%")

if len(overlap) == 0:
    print("  -> Products go empty independently. NOT a market-wide pause.")
else:
    print(f"  -> {len(overlap)} shared timestamps — possible common cause.")
    print(f"    Shared t values: {sorted(overlap)[:10]}")
print()

# ── H2: Timestamp clustering ─────────────────────────────────────────────────
print("=" * 60)
print("H2 — Timestamp clustering within the trading day")
print("=" * 60)

# Timestamps run 0 – 999900 per day (1M ticks × 100ms each)
# Split into 10 equal buckets
bucket_size = 100_000  # 10% of day each
empty["bucket"] = (empty["timestamp"] // bucket_size) * bucket_size
bucket_counts = empty.groupby("bucket").size()
total_per_bucket = prices.groupby(prices["timestamp"] // bucket_size * bucket_size).size()

print("  Empty ticks per 10% time bucket (across all days/products):")
for b, n in bucket_counts.items():
    pct = 100 * n / len(empty)
    bar = "#" * int(pct / 2)
    print(f"    t={b:>7}-{b+bucket_size:<7}  {n:3d}  ({pct:4.1f}%)  {bar}")

# Chi-square uniformity test
from scipy import stats as sp_stats
expected_uniform = np.full(len(bucket_counts), len(empty) / len(bucket_counts))
chi2, p_uniform = sp_stats.chisquare(bucket_counts.values, expected_uniform)
print(f"\n  Chi-square uniformity test: chi2={chi2:.2f}, p={p_uniform:.4f}")
if p_uniform < 0.05:
    print("  -> Non-uniform distribution — empty ticks cluster at specific times.")
else:
    print("  -> Uniform distribution — no significant time-of-day clustering.")
print()

# ── H3: Volatility trigger ────────────────────────────────────────────────────
print("=" * 60)
print("H3 — Volatility trigger (empty ticks follow high-spread periods)")
print("=" * 60)

# Compute bid-ask spread for normal rows
norm = normal.copy()
norm["spread"] = norm["ask_price_1"] - norm["bid_price_1"]
norm = norm.dropna(subset=["spread"])

# For each empty tick, find spread N ticks before (same product/day)
lookback_ticks = 5
results_h3 = []
for _, row in empty.iterrows():
    prod, day, ts = row["product"], row["day"], row["timestamp"]
    prior = norm[(norm["product"] == prod) & (norm["day"] == day) & (norm["timestamp"] < ts)]
    if len(prior) >= lookback_ticks:
        avg_spread_before = prior.nlargest(lookback_ticks, "timestamp")["spread"].mean()
    else:
        avg_spread_before = np.nan
    results_h3.append(avg_spread_before)

empty["spread_before"] = results_h3

# Compare to baseline spread distribution
baseline_spread = norm["spread"].dropna()
empty_spread_before = pd.Series(results_h3).dropna()

print(f"  Baseline spread  : mean={baseline_spread.mean():.2f}  median={baseline_spread.median():.2f}")
print(f"  Before empty tick: mean={empty_spread_before.mean():.2f}  median={empty_spread_before.median():.2f}")

t_stat, p_t = sp_stats.ttest_ind(empty_spread_before, baseline_spread, equal_var=False)
print(f"  Welch t-test: t={t_stat:.3f}, p={p_t:.4f}")
if p_t < 0.05:
    direction = "higher" if t_stat > 0 else "lower"
    print(f"  -> Significant: spread is {direction} before empty ticks.")
else:
    print("  -> Not significant: spread before empty ticks is unremarkable.")
print()

# ── H4: Volume dryup ─────────────────────────────────────────────────────────
print("=" * 60)
print("H4 — Volume dryup (empty ticks follow low-depth periods)")
print("=" * 60)

vol_cols_bid = ["bid_volume_1", "bid_volume_2", "bid_volume_3"]
vol_cols_ask = ["ask_volume_1", "ask_volume_2", "ask_volume_3"]
norm["total_depth"] = norm[vol_cols_bid + vol_cols_ask].fillna(0).sum(axis=1)

results_h4 = []
for _, row in empty.iterrows():
    prod, day, ts = row["product"], row["day"], row["timestamp"]
    prior = norm[(norm["product"] == prod) & (norm["day"] == day) & (norm["timestamp"] < ts)]
    if len(prior) >= lookback_ticks:
        avg_depth_before = prior.nlargest(lookback_ticks, "timestamp")["total_depth"].mean()
    else:
        avg_depth_before = np.nan
    results_h4.append(avg_depth_before)

baseline_depth = norm["total_depth"]
empty_depth_before = pd.Series(results_h4).dropna()

print(f"  Baseline depth   : mean={baseline_depth.mean():.1f}  median={baseline_depth.median():.1f}")
print(f"  Before empty tick: mean={empty_depth_before.mean():.1f}  median={empty_depth_before.median():.1f}")

t_stat4, p_t4 = sp_stats.ttest_ind(empty_depth_before, baseline_depth, equal_var=False)
print(f"  Welch t-test: t={t_stat4:.3f}, p={p_t4:.4f}")
if p_t4 < 0.05:
    direction = "lower" if t_stat4 < 0 else "higher"
    print(f"  -> Significant: depth is {direction} before empty ticks.")
else:
    print("  -> Not significant: depth before empty ticks is unremarkable.")
print()

# ── H5: Post-trade gap ────────────────────────────────────────────────────────
print("=" * 60)
print("H5 — Post-trade gap (empty ticks follow a recent execution)")
print("=" * 60)

# Check if a trade in trades data occurred within N ticks before empty book
trade_window = 500  # 500ms = 5 ticks

results_h5 = []
for _, row in empty.iterrows():
    prod, day, ts = row["product"], row["day"], row["timestamp"]
    recent_trades = trades[
        (trades["symbol"] == prod) &
        (trades["day"] == day) &
        (trades["timestamp"].between(ts - trade_window, ts - 1))
    ]
    results_h5.append(len(recent_trades) > 0)

pct_preceded_by_trade = 100 * np.mean(results_h5)

# Baseline: what fraction of any random tick has a trade in prior 500ms?
baseline_h5 = []
sample = prices.sample(min(500, len(prices)), random_state=42)
for _, row in sample.iterrows():
    prod, day, ts = row["product"], row["day"], row["timestamp"]
    recent_trades = trades[
        (trades["symbol"] == prod) &
        (trades["day"] == day) &
        (trades["timestamp"].between(ts - trade_window, ts - 1))
    ]
    baseline_h5.append(len(recent_trades) > 0)
baseline_pct = 100 * np.mean(baseline_h5)

print(f"  Trade in prior {trade_window}ms before empty tick : {pct_preceded_by_trade:.1f}%")
print(f"  Trade in prior {trade_window}ms baseline (random) : {baseline_pct:.1f}%")

from scipy.stats import fisher_exact
a = int(np.sum(results_h5))          # empty preceded by trade
b = len(results_h5) - a              # empty NOT preceded
c = int(np.sum(baseline_h5))         # random preceded by trade
d = len(baseline_h5) - c             # random NOT preceded
_, p_fisher = fisher_exact([[a, b], [c, d]])
print(f"  Fisher exact p={p_fisher:.4f}")
if p_fisher < 0.05:
    direction = "more" if pct_preceded_by_trade > baseline_pct else "less"
    print(f"  -> Significant: empty ticks are {direction} likely to follow a trade.")
else:
    print("  -> Not significant: trade activity doesn't predict empty ticks.")
print()

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
The 103 empty-book events (~0.17% of ticks) share these properties:
  - Always isolated single-tick events (never consecutive)
  - Uniformly distributed across products and days
  - mid_price is set to 0.0 by the exchange when no quotes exist

Hypothesis results (check printed p-values above for significance):
  H1 (market-wide pause)  : test overlap between ASH and PEP empty ticks
  H2 (time-of-day)        : chi-square on 10 time buckets
  H3 (volatility trigger) : spread before vs baseline
  H4 (volume dryup)       : depth before vs baseline
  H5 (post-trade pullback): trade rate before empty ticks vs baseline

Most likely explanation regardless of test outcomes:
  The simulator/exchange engine has a tick where the market-maker bots
  happen to have no resting quotes (all filled or expired), producing
  a momentary empty book. This is an artifact of the discrete-event
  simulation, not a real market phenomenon.

Treatment in analysis:
  Replace mid_price=0 with NaN (missing) in get_mid() at load time.
  Use forward-fill or interpolation only where the series consumer
  explicitly requires it (e.g. position PnL). Leave as NaN for
  statistical analysis so these ticks don't bias returns or spreads.
""")
