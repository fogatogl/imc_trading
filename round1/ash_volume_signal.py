"""
ASH_COATED_OSMIUM: Mid-price movement vs market volume position.
Volume position = order book imbalance (bid_vol vs ask_vol) + trade flow direction.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent / "dataset" / "round1"
PRODUCT = "ASH_COATED_OSMIUM"
DAYS = [-2, -1, 0]

# ── 1. Load data ────────────────────────────────────────────────────────────

price_frames, trade_frames = [], []
for d in DAYS:
    pf = pd.read_csv(ROOT / f"prices_round_1_day_{d}.csv", sep=";")
    tf = pd.read_csv(ROOT / f"trades_round_1_day_{d}.csv", sep=";")
    pf["day"] = d
    tf["day"] = d
    price_frames.append(pf)
    trade_frames.append(tf)

prices = pd.concat(price_frames, ignore_index=True)
trades = pd.concat(trade_frames, ignore_index=True)

ash_p = prices[prices["product"] == PRODUCT].copy()
ash_t = trades[trades["symbol"] == PRODUCT].copy()

# ── 2. Order-book imbalance ──────────────────────────────────────────────────
# Use level-1 only (most reliable). Fill NaN volumes with 0.
ash_p["bid_vol_1"] = pd.to_numeric(ash_p["bid_volume_1"], errors="coerce").fillna(0)
ash_p["ask_vol_1"] = pd.to_numeric(ash_p["ask_volume_1"], errors="coerce").fillna(0)
ash_p["bid_price_1"] = pd.to_numeric(ash_p["bid_price_1"], errors="coerce")
ash_p["ask_price_1"] = pd.to_numeric(ash_p["ask_price_1"], errors="coerce")
ash_p["mid_price"]   = pd.to_numeric(ash_p["mid_price"], errors="coerce")

total_vol = ash_p["bid_vol_1"] + ash_p["ask_vol_1"]
ash_p["obi"] = np.where(
    total_vol > 0,
    (ash_p["bid_vol_1"] - ash_p["ask_vol_1"]) / total_vol,
    np.nan,
)

# ── 3. Trade flow: infer direction from price vs book ────────────────────────
# Merge nearest price snapshot onto each trade (same day, timestamp ≤ trade ts)
ash_p_sorted = ash_p.sort_values(["day", "timestamp"])
ash_t_sorted = ash_t.sort_values(["day", "timestamp"])

def classify_trade(row, price_snap):
    """Return +qty if trade at ask (buy), -qty if at bid (sell), 0 if unclear."""
    mask = (price_snap["day"] == row["day"]) & (price_snap["timestamp"] <= row["timestamp"])
    snaps = price_snap[mask]
    if snaps.empty:
        return 0
    snap = snaps.iloc[-1]
    bp, ap = snap["bid_price_1"], snap["ask_price_1"]
    tp = row["price"]
    qty = row["quantity"]
    if pd.isna(ap) and pd.isna(bp):
        return 0
    if not pd.isna(ap) and abs(tp - ap) <= abs(tp - (bp if not pd.isna(bp) else ap)):
        return qty   # closer to ask → aggressive buy
    elif not pd.isna(bp):
        return -qty  # closer to bid → aggressive sell
    return 0

ash_t_sorted["signed_qty"] = ash_t_sorted.apply(
    classify_trade, axis=1, price_snap=ash_p_sorted
)

# Aggregate signed flow per (day, timestamp) bucket
BUCKET = 100  # 100-unit timestamp buckets
ash_t_sorted["ts_bucket"] = (ash_t_sorted["timestamp"] // BUCKET) * BUCKET
flow = (
    ash_t_sorted.groupby(["day", "ts_bucket"])["signed_qty"]
    .sum()
    .reset_index()
    .rename(columns={"ts_bucket": "timestamp", "signed_qty": "net_flow"})
)

# ── 4. Merge flow onto price snapshots ──────────────────────────────────────
ash_p["ts_bucket"] = (ash_p["timestamp"] // BUCKET) * BUCKET
merged = ash_p.merge(
    flow.rename(columns={"timestamp": "ts_bucket"}),
    on=["day", "ts_bucket"],
    how="left",
)
merged["net_flow"] = merged["net_flow"].fillna(0)

# ── 5. Label volume position ─────────────────────────────────────────────────
# Three signals:
#   a) OBI-based
#   b) Net trade flow-based
#   c) Combined

OBI_THRESH = 0.25          # >25% imbalance = large
FLOW_THRESH_PCT = 75       # top/bottom quartile of nonzero flow

nonzero_flow = merged["net_flow"][merged["net_flow"] != 0]
flow_hi =  np.percentile(nonzero_flow, FLOW_THRESH_PCT) if len(nonzero_flow) else 1
flow_lo = -np.percentile(-nonzero_flow[nonzero_flow < 0], FLOW_THRESH_PCT) if any(nonzero_flow < 0) else -1

def label_obi(x):
    if pd.isna(x): return "no_book"
    if x > OBI_THRESH:  return "large_buy"
    if x < -OBI_THRESH: return "large_sell"
    return "neutral"

def label_flow(x):
    if x >= flow_hi:  return "large_buy"
    if x <= flow_lo:  return "large_sell"
    if x == 0:        return "no_trade"
    return "neutral"

merged["obi_label"]  = merged["obi"].apply(label_obi)
merged["flow_label"] = merged["net_flow"].apply(label_flow)

# ── 6. Forward returns ───────────────────────────────────────────────────────
HORIZONS = [1, 3, 5, 10]  # in rows (each row ≈ 100 ts)

merged = merged.sort_values(["day", "timestamp"]).reset_index(drop=True)
for h in HORIZONS:
    merged[f"fwd_{h}"] = merged["mid_price"].shift(-h) - merged["mid_price"]

# ── 7. Correlation analysis ──────────────────────────────────────────────────

print("=" * 60)
print(f"ASH_COATED_OSMIUM — Mid-price movement vs Volume Position")
print(f"Rows: {len(merged)} | Days: {DAYS}")
print("=" * 60)

print("\n-- OBI vs forward returns (OBI threshold +-{:.0%}) --".format(OBI_THRESH))
for h in HORIZONS:
    grp = merged.groupby("obi_label")[f"fwd_{h}"].agg(["mean", "std", "count"])
    grp.columns = ["mean_ret", "std_ret", "n"]
    grp["t_stat"] = grp["mean_ret"] / (grp["std_ret"] / np.sqrt(grp["n"]))
    print(f"\n  Horizon {h} rows (~{h*100} ts):")
    print(grp.round(4).to_string())

print("\n── Trade flow vs forward returns ──")
for h in HORIZONS:
    grp = merged.groupby("flow_label")[f"fwd_{h}"].agg(["mean", "std", "count"])
    grp.columns = ["mean_ret", "std_ret", "n"]
    grp["t_stat"] = grp["mean_ret"] / (grp["std_ret"] / np.sqrt(grp["n"]))
    print(f"\n  Horizon {h} rows (~{h*100} ts):")
    print(grp.round(4).to_string())

print("\n── Pearson correlation: OBI & net_flow vs fwd returns ──")
for h in HORIZONS:
    corr_obi  = merged[["obi", f"fwd_{h}"]].dropna().corr().iloc[0, 1]
    corr_flow = merged[["net_flow", f"fwd_{h}"]].dropna().corr().iloc[0, 1]
    print(f"  h={h:2d}: OBI corr={corr_obi:+.4f}   flow corr={corr_flow:+.4f}")

# ── 8. Lag analysis — does volume LEAD price? ────────────────────────────────
print("\n── OBI Lag analysis (does OBI at t predict price at t+lag?) ──")
lags = [1, 2, 3, 5, 10]
merged_clean = merged[["obi", "mid_price"]].dropna().copy()
mid = merged_clean["mid_price"].values
obi = merged_clean["obi"].values
for lag in lags:
    if lag >= len(mid): continue
    ret = mid[lag:] - mid[:-lag]
    obi_cut = obi[:-lag]
    corr = np.corrcoef(obi_cut, ret)[0, 1]
    print(f"  lag={lag:2d}: corr(OBI_t, ret_t→t+{lag}) = {corr:+.4f}")

print("\n── Net flow Lag analysis ──")
flow_vals = merged["net_flow"].values
mid_vals  = merged["mid_price"].values
valid_mask = ~np.isnan(mid_vals)
for lag in lags:
    if lag >= len(mid_vals): continue
    fv = flow_vals[:-lag][valid_mask[:-lag] & valid_mask[lag:]]
    mv = mid_vals[lag:][valid_mask[:-lag] & valid_mask[lag:]] - mid_vals[:-lag][valid_mask[:-lag] & valid_mask[lag:]]
    if len(fv) < 10: continue
    corr = np.corrcoef(fv, mv)[0, 1]
    print(f"  lag={lag:2d}: corr(flow_t, ret_t→t+{lag}) = {corr:+.4f}")

# ── 9. Summary: best signal ──────────────────────────────────────────────────
print("\n── Summary: mean forward return by combined signal ──")
print("  (large_buy OBI + large_buy flow vs large_sell OBI + large_sell flow)")
combined_buy  = merged[(merged["obi_label"] == "large_buy")  & (merged["flow_label"] == "large_buy")]
combined_sell = merged[(merged["obi_label"] == "large_sell") & (merged["flow_label"] == "large_sell")]
for h in HORIZONS:
    mb = combined_buy[f"fwd_{h}"].mean()
    ms = combined_sell[f"fwd_{h}"].mean()
    nb = len(combined_buy[f"fwd_{h}"].dropna())
    ns = len(combined_sell[f"fwd_{h}"].dropna())
    print(f"  h={h}: BUY mean={mb:+.3f} (n={nb})  SELL mean={ms:+.3f} (n={ns})")
