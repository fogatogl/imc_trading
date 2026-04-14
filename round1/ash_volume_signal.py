"""
ASH_COATED_OSMIUM: Mid-price movement vs market volume position.
Volume position = order book imbalance (bid_vol vs ask_vol) + trade flow direction.

Clean: filters out rows with mid_price=0 (data artifact = empty book, both sides).
Uses within-day forward returns only.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent / "dataset" / "round1"
PRODUCT = "ASH_COATED_OSMIUM"
DAYS = [-2, -1, 0]

# ── 1. Load data ─────────────────────────────────────────────────────────────

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

# ── 2. Clean and compute OBI ──────────────────────────────────────────────────
ash_p["bid_vol_1"] = pd.to_numeric(ash_p["bid_volume_1"], errors="coerce").fillna(0)
ash_p["ask_vol_1"] = pd.to_numeric(ash_p["ask_volume_1"], errors="coerce").fillna(0)
ash_p["bid_price_1"] = pd.to_numeric(ash_p["bid_price_1"], errors="coerce")
ash_p["ask_price_1"] = pd.to_numeric(ash_p["ask_price_1"], errors="coerce")
ash_p["mid_price"]   = pd.to_numeric(ash_p["mid_price"], errors="coerce")

# Filter out rows where mid_price=0 (artifact: both sides of book absent)
ash_p = ash_p[ash_p["mid_price"] > 0].copy()

total_vol = ash_p["bid_vol_1"] + ash_p["ask_vol_1"]
ash_p["obi"] = np.where(
    total_vol > 0,
    (ash_p["bid_vol_1"] - ash_p["ask_vol_1"]) / total_vol,
    np.nan,
)

# ── 3. Trade flow: infer direction from price vs book ────────────────────────
ash_p_sorted = ash_p.sort_values(["day", "timestamp"])
ash_t_sorted = ash_t.sort_values(["day", "timestamp"])

def classify_trade(row, price_snap):
    mask = (price_snap["day"] == row["day"]) & (price_snap["timestamp"] <= row["timestamp"])
    snaps = price_snap[mask]
    if snaps.empty:
        return 0
    snap = snaps.iloc[-1]
    bp, ap = snap["bid_price_1"], snap["ask_price_1"]
    tp, qty = row["price"], row["quantity"]
    if pd.isna(ap) and pd.isna(bp):
        return 0
    if not pd.isna(ap) and (pd.isna(bp) or abs(tp - ap) <= abs(tp - bp)):
        return qty    # closer to ask → aggressive buy
    return -qty       # closer to bid → aggressive sell

ash_t_sorted["signed_qty"] = ash_t_sorted.apply(
    classify_trade, axis=1, price_snap=ash_p_sorted
)

BUCKET = 100
ash_t_sorted["ts_bucket"] = (ash_t_sorted["timestamp"] // BUCKET) * BUCKET
flow = (
    ash_t_sorted.groupby(["day", "ts_bucket"])["signed_qty"]
    .sum()
    .reset_index()
    .rename(columns={"ts_bucket": "timestamp", "signed_qty": "net_flow"})
)

ash_p["ts_bucket"] = (ash_p["timestamp"] // BUCKET) * BUCKET
merged = ash_p.merge(
    flow.rename(columns={"timestamp": "ts_bucket"}),
    on=["day", "ts_bucket"],
    how="left",
)
merged["net_flow"] = merged["net_flow"].fillna(0)
merged = merged.sort_values(["day", "timestamp"]).reset_index(drop=True)

# ── 4. Label volume position ──────────────────────────────────────────────────
OBI_THRESH = 0.25

nonzero_flow = merged["net_flow"][merged["net_flow"] != 0]
flow_hi = np.percentile(nonzero_flow, 75) if len(nonzero_flow) else 1
flow_lo = np.percentile(nonzero_flow, 25) if len(nonzero_flow) else -1

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

# ── 5. Within-day forward returns ────────────────────────────────────────────
HORIZONS = [1, 3, 5, 10]

for h in HORIZONS:
    merged[f"fwd_{h}"] = np.nan
    for d in DAYS:
        mask = merged["day"] == d
        dm = merged.loc[mask, "mid_price"]
        merged.loc[mask, f"fwd_{h}"] = dm.shift(-h).values - dm.values

# ── 6. Stats ──────────────────────────────────────────────────────────────────
print("=" * 65)
print(f"ASH_COATED_OSMIUM — Mid-price movement vs Volume Position")
print(f"Rows (mid>0): {len(merged)} | Days: {DAYS} | OBI threshold: +-{OBI_THRESH:.0%}")
print("=" * 65)

print("\n-- OBI distribution --")
obi_valid = merged["obi"].dropna()
print(f"  count={len(obi_valid)}  mean={obi_valid.mean():+.4f}  std={obi_valid.std():.4f}")
print(merged["obi_label"].value_counts().to_string())

print("\n-- Net flow distribution --")
print(f"  flow_hi (75th pct of nonzero): {flow_hi:.1f}   flow_lo: {flow_lo:.1f}")
print(merged["flow_label"].value_counts().to_string())

print("\n-- fwd_1 sanity check (should be ~0 mean, small std) --")
print(merged["fwd_1"].describe().round(4).to_string())

print("\n-- OBI vs forward returns (within-day, mid>0 only) --")
for h in HORIZONS:
    grp = merged.groupby("obi_label")[f"fwd_{h}"].agg(["mean", "std", "count"])
    grp.columns = ["mean_ret", "std_ret", "n"]
    grp["t_stat"] = grp["mean_ret"] / (grp["std_ret"] / np.sqrt(grp["n"]))
    print(f"\n  Horizon {h} rows (~{h*100} ts):")
    print(grp.round(4).to_string())

print("\n-- Trade flow vs forward returns --")
for h in HORIZONS:
    grp = merged.groupby("flow_label")[f"fwd_{h}"].agg(["mean", "std", "count"])
    grp.columns = ["mean_ret", "std_ret", "n"]
    grp["t_stat"] = grp["mean_ret"] / (grp["std_ret"] / np.sqrt(grp["n"]))
    print(f"\n  Horizon {h} rows (~{h*100} ts):")
    print(grp.round(4).to_string())

print("\n-- Pearson correlation: OBI & net_flow vs fwd returns --")
for h in HORIZONS:
    corr_obi  = merged[["obi", f"fwd_{h}"]].dropna().corr().iloc[0, 1]
    corr_flow = merged[["net_flow", f"fwd_{h}"]].dropna().corr().iloc[0, 1]
    print(f"  h={h:2d}: OBI corr={corr_obi:+.4f}   flow corr={corr_flow:+.4f}")

print("\n-- Within-day lag analysis --")
lags = [1, 2, 3, 5, 10]
all_pairs_obi  = {lag: ([], []) for lag in lags}
all_pairs_flow = {lag: ([], []) for lag in lags}

for d in DAYS:
    dm = merged[merged["day"] == d].sort_values("timestamp")
    mid  = dm["mid_price"].values
    obi  = dm["obi"].values
    flow = dm["net_flow"].values
    for lag in lags:
        if lag >= len(mid): continue
        ret = mid[lag:] - mid[:-lag]
        valid_obi  = ~np.isnan(obi[:-lag]) & ~np.isnan(ret)
        valid_flow = ~np.isnan(ret)
        all_pairs_obi[lag][0].extend(obi[:-lag][valid_obi].tolist())
        all_pairs_obi[lag][1].extend(ret[valid_obi].tolist())
        all_pairs_flow[lag][0].extend(flow[:-lag][valid_flow].tolist())
        all_pairs_flow[lag][1].extend(ret[valid_flow].tolist())

print("  lag | OBI corr | flow corr | n_obi")
for lag in lags:
    ox, oy = np.array(all_pairs_obi[lag][0]), np.array(all_pairs_obi[lag][1])
    fx, fy = np.array(all_pairs_flow[lag][0]), np.array(all_pairs_flow[lag][1])
    c_obi  = np.corrcoef(ox, oy)[0, 1] if len(ox) > 5 else np.nan
    c_flow = np.corrcoef(fx, fy)[0, 1] if len(fx) > 5 else np.nan
    print(f"  {lag:3d} | {c_obi:+.4f}   | {c_flow:+.4f}    | {len(ox)}")

print("\n-- OBI signal hit rate (fraction correct directional predictions) --")
for h in HORIZONS:
    df = merged[["obi", f"fwd_{h}"]].dropna()
    buy_mask  = df["obi"] > OBI_THRESH
    sell_mask = df["obi"] < -OBI_THRESH

    b_ret = df.loc[buy_mask,  f"fwd_{h}"]
    s_ret = df.loc[sell_mask, f"fwd_{h}"]

    buy_hit  = (b_ret > 0).mean()
    sell_hit = (s_ret < 0).mean()
    buy_mean, sell_mean = b_ret.mean(), s_ret.mean()
    nb, ns = buy_mask.sum(), sell_mask.sum()
    print(f"  h={h:2d}:  large_buy  hit={buy_hit:.2%} mean={buy_mean:+.3f} (n={nb})"
          f"  |  large_sell hit={sell_hit:.2%} mean={sell_mean:+.3f} (n={ns})")

print("\n-- Combined OBI + flow signal --")
combined_buy  = merged[(merged["obi_label"] == "large_buy")  & (merged["flow_label"] == "large_buy")]
combined_sell = merged[(merged["obi_label"] == "large_sell") & (merged["flow_label"] == "large_sell")]
print("  h  | BUY mean  | BUY t   | BUY n  | SELL mean | SELL t  | SELL n")
for h in HORIZONS:
    bfwd = combined_buy[f"fwd_{h}"].dropna()
    sfwd = combined_sell[f"fwd_{h}"].dropna()
    mb, sb, nb = bfwd.mean(), bfwd.std(), len(bfwd)
    ms, ss, ns = sfwd.mean(), sfwd.std(), len(sfwd)
    tb = mb / (sb / np.sqrt(nb)) if nb > 1 else np.nan
    ts = ms / (ss / np.sqrt(ns)) if ns > 1 else np.nan
    print(f"  {h:2d} | {mb:+.4f}    | {tb:+.3f}  | {nb:5d}  | {ms:+.4f}    | {ts:+.3f}  | {ns}")

print("\n-- Per-day OBI correlation --")
for d in DAYS:
    dm = merged[merged["day"] == d].sort_values("timestamp")
    df = dm[["obi", "fwd_1"]].dropna()
    if len(df) < 5: continue
    c = df.corr().iloc[0, 1]
    mean_obi = df["obi"].mean()
    mean_fwd = df["fwd_1"].mean()
    print(f"  day {d:2d}: corr(OBI, fwd_1)={c:+.4f}  mean_OBI={mean_obi:+.4f}  mean_fwd={mean_fwd:+.4f}")

print("\n-- OBI mean by bucket (quantile breakdown) --")
merged_clean = merged[["obi", "fwd_1"]].dropna()
merged_clean["obi_bin"] = pd.cut(merged_clean["obi"], bins=[-1.01, -0.5, -0.25, 0, 0.25, 0.5, 1.01],
                                   labels=["[-1,-0.5]", "(-0.5,-0.25]", "(-0.25,0]",
                                           "(0,0.25]", "(0.25,0.5]", "(0.5,1]"])
grp = merged_clean.groupby("obi_bin")["fwd_1"].agg(["mean", "std", "count"])
grp["t_stat"] = grp["mean"] / (grp["std"] / np.sqrt(grp["count"]))
print(grp.round(4).to_string())
