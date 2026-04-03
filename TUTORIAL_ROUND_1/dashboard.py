"""
IMC Prosperity 4 — Tutorial Round Data Visualisation Dashboard
=============================================================
Panels:
  1. Bid-Ask Spread oscillation  (TOMATOES vs EMERALDS, both days)
  2. Fair Value comparison        (plain mid vs WallMid — TOMATOES)
  3. TOMATOES price volatility    (rolling σ of mid-price levels + price diffs)
  4. Order-book depth snapshot    (bid/ask volume heatmap across price levels)
  5. VWAP vs mid-price            (trade VWAP anchored against book mid)
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

# ── paths ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)

prices_files = {
    "day -1": os.path.join(BASE, "prices_round_0_day_-1.csv"),
    "day -2": os.path.join(BASE, "prices_round_0_day_-2.csv"),
}
trades_files = {
    "day -1": os.path.join(BASE, "trades_round_0_day_-1.csv"),
    "day -2": os.path.join(BASE, "trades_round_0_day_-2.csv"),
}

# ── load data ─────────────────────────────────────────────────────────────────
def load_prices(path):
    df = pd.read_csv(path, sep=";")
    df.columns = df.columns.str.strip()
    numeric_cols = [c for c in df.columns if c not in ("product",)]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def load_trades(path):
    df = pd.read_csv(path, sep=";")
    df.columns = df.columns.str.strip()
    df["price"]    = pd.to_numeric(df["price"],    errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["timestamp"]= pd.to_numeric(df["timestamp"],errors="coerce")
    return df

all_prices = pd.concat(
    [load_prices(p).assign(source=k) for k, p in prices_files.items()],
    ignore_index=True,
)
all_trades = pd.concat(
    [load_trades(p).assign(source=k) for k, p in trades_files.items()],
    ignore_index=True,
)

# Create a global x-axis that doesn't reset between days:
# day -2 comes before day -1 → map day -2 → offset 0, day -1 → offset + max_ts
day_order   = {"day -2": 0, "day -1": 1}
MAX_TS      = all_prices["timestamp"].max()
all_prices["t_global"] = (
    all_prices["source"].map(day_order) * (MAX_TS + 100)
    + all_prices["timestamp"]
)
all_trades["t_global"] = (
    all_trades["source"].map(day_order) * (MAX_TS + 100)
    + all_trades["timestamp"]
)

tom = all_prices[all_prices["product"] == "TOMATOES"].copy().sort_values("t_global")
em  = all_prices[all_prices["product"] == "EMERALDS"].copy().sort_values("t_global")
tom_trades = all_trades[all_trades["symbol"] == "TOMATOES"].copy().sort_values("t_global")
em_trades  = all_trades[all_trades["symbol"] == "EMERALDS"].copy().sort_values("t_global")

# ── WallMid: mid of the largest bid & ask (best FV for drifting products) ─────
def wall_mid(row):
    """Return mid of the level with the largest bid volume and largest ask volume."""
    bids = {
        row["bid_price_1"]: row.get("bid_volume_1", 0),
        row["bid_price_2"]: row.get("bid_volume_2", 0),
        row["bid_price_3"]: row.get("bid_volume_3", 0),
    }
    asks = {
        row["ask_price_1"]: row.get("ask_volume_1", 0),
        row["ask_price_2"]: row.get("ask_volume_2", 0),
        row["ask_price_3"]: row.get("ask_volume_3", 0),
    }
    bids = {p: v for p, v in bids.items() if pd.notna(p) and pd.notna(v) and v > 0}
    asks = {p: v for p, v in asks.items() if pd.notna(p) and pd.notna(v) and v > 0}
    if not bids or not asks:
        return np.nan
    wall_bid = max(bids, key=bids.get)
    wall_ask = min(asks, key=asks.get)  # smallest ask price with largest volume heuristic
    # Use volume-weighted: pick the ask level with the largest volume
    wall_ask = max(asks, key=asks.get)
    return (wall_bid + wall_ask) / 2.0

tom["wall_mid"]  = tom.apply(wall_mid, axis=1)
tom["spread"]    = tom["ask_price_1"] - tom["bid_price_1"]
em["spread"]     = em["ask_price_1"]  - em["bid_price_1"]

# Rolling volatility (window = 50 ticks ≈ 5 s)
WINDOW = 50
tom["roll_vol_level"] = tom["mid_price"].rolling(WINDOW).std()
tom["price_diff"]     = tom["mid_price"].diff()
tom["roll_vol_diff"]  = tom["price_diff"].rolling(WINDOW).std()

# Rolling VWAP from trade data (expanding window within each day)
def rolling_vwap(trades_df):
    """Expanding VWAP from executed trades."""
    trades_df = trades_df.copy().sort_values("t_global")
    trades_df["cum_pv"] = (trades_df["price"] * trades_df["quantity"]).cumsum()
    trades_df["cum_v"]  = trades_df["quantity"].cumsum()
    trades_df["vwap"]   = trades_df["cum_pv"] / trades_df["cum_v"]
    return trades_df

tom_trades = rolling_vwap(tom_trades)
em_trades  = rolling_vwap(em_trades)

# ── colour scheme ─────────────────────────────────────────────────────────────
TOMATO_C = "#E74C3C"
EMRLD_C  = "#2ECC71"
MID_C    = "#3498DB"
WALL_C   = "#F39C12"
VOL_C    = "#9B59B6"
VWAP_C   = "#1ABC9C"
BID_C    = "#27AE60"
ASK_C    = "#E74C3C"
DAY_SPLIT_COLOR = "#95A5A6"

# ── figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(20, 26), facecolor="#1A1A2E")
fig.suptitle(
    "IMC Prosperity 4 — Tutorial Round  |  Order Book & Price Behaviour Analysis",
    fontsize=16, fontweight="bold", color="white", y=0.99,
)

gs = gridspec.GridSpec(
    5, 2,
    figure=fig,
    hspace=0.55,
    wspace=0.35,
    left=0.07, right=0.97,
    top=0.96, bottom=0.04,
)

PANEL_BG  = "#16213E"
TEXT_C    = "#ECF0F1"
GRID_C    = "#2C3E50"

def style_ax(ax, title):
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, color=TEXT_C, fontsize=11, fontweight="bold", pad=8)
    ax.tick_params(colors=TEXT_C, labelsize=8)
    ax.xaxis.label.set_color(TEXT_C)
    ax.yaxis.label.set_color(TEXT_C)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_C)
    ax.grid(True, color=GRID_C, linewidth=0.5, alpha=0.7)

def add_day_separator(ax, ymin, ymax):
    sep = MAX_TS + 100
    ax.axvline(sep, color=DAY_SPLIT_COLOR, linewidth=1.2, linestyle="--", alpha=0.6)
    ax.text(sep, ymax * 0.98, "day -2 | day -1",
            color=DAY_SPLIT_COLOR, fontsize=7, ha="center", va="top")

# ── PANEL 1 (top-left): Bid-Ask Spread — TOMATOES ────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
style_ax(ax1, "1 · Bid-Ask Spread Oscillation — TOMATOES")

ax1.fill_between(tom["t_global"], tom["spread"], alpha=0.25, color=TOMATO_C)
ax1.plot(tom["t_global"], tom["spread"], color=TOMATO_C, linewidth=0.8, label="Spread")
roll_mean = tom["spread"].rolling(200).mean()
ax1.plot(tom["t_global"], roll_mean, color="white", linewidth=1.5,
         linestyle="--", label="200-tick MA")

ax1.set_ylabel("Spread (ask₁ − bid₁)", fontsize=9)
ax1.set_xlabel("Timestamp (ms, both days)")
add_day_separator(ax1, tom["spread"].min(), tom["spread"].max())
ax1.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C, loc="upper right")

# Annotate mean spread
mean_sp = tom["spread"].mean()
ax1.axhline(mean_sp, color=WALL_C, linewidth=1, linestyle=":")
ax1.text(ax1.get_xlim()[0], mean_sp + 0.1, f"μ={mean_sp:.1f}", color=WALL_C, fontsize=8)

# ── PANEL 2 (top-right): Bid-Ask Spread — EMERALDS ───────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
style_ax(ax2, "2 · Bid-Ask Spread Oscillation — EMERALDS")

ax2.fill_between(em["t_global"], em["spread"], alpha=0.25, color=EMRLD_C)
ax2.plot(em["t_global"], em["spread"], color=EMRLD_C, linewidth=0.8, label="Spread")
roll_mean_em = em["spread"].rolling(200).mean()
ax2.plot(em["t_global"], roll_mean_em, color="white", linewidth=1.5,
         linestyle="--", label="200-tick MA")

ax2.set_ylabel("Spread (ask₁ − bid₁)", fontsize=9)
ax2.set_xlabel("Timestamp (ms, both days)")
add_day_separator(ax2, em["spread"].min(), em["spread"].max())
ax2.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C, loc="upper right")

mean_sp_em = em["spread"].mean()
ax2.axhline(mean_sp_em, color=WALL_C, linewidth=1, linestyle=":")
ax2.text(ax2.get_xlim()[0], mean_sp_em + 0.1, f"μ={mean_sp_em:.1f}", color=WALL_C, fontsize=8)

# ── PANEL 3 (row 2, full width): Fair Value — Plain Mid vs WallMid ───────────
ax3 = fig.add_subplot(gs[1, :])
style_ax(ax3, "3 · TOMATOES Fair Value — Plain Mid vs WallMid (large-order mid)")

ax3.plot(tom["t_global"], tom["mid_price"],
         color=MID_C,  linewidth=0.9, alpha=0.8, label="Plain mid  (best_bid+best_ask)/2")
ax3.plot(tom["t_global"], tom["wall_mid"],
         color=WALL_C, linewidth=1.3, alpha=0.9, label="WallMid  (largest bid/ask levels)")

# Shade the difference
ax3.fill_between(
    tom["t_global"], tom["mid_price"], tom["wall_mid"],
    where=tom["wall_mid"] > tom["mid_price"],
    alpha=0.15, color=WALL_C, label="WallMid > PlainMid"
)
ax3.fill_between(
    tom["t_global"], tom["mid_price"], tom["wall_mid"],
    where=tom["wall_mid"] <= tom["mid_price"],
    alpha=0.15, color=MID_C
)

# Overlay actual trades
if not tom_trades.empty:
    ax3.scatter(tom_trades["t_global"], tom_trades["price"],
                s=12, color="white", alpha=0.5, zorder=5, label="Executed trades")

add_day_separator(ax3, tom["mid_price"].min() * 0.999, tom["mid_price"].max() * 1.001)
ax3.set_ylabel("Price (XIRECs)", fontsize=9)
ax3.set_xlabel("Timestamp (ms, both days)")
ax3.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C, ncol=2, loc="upper left")

# ── PANEL 4 (row 3, left): Rolling Volatility of Tomatoes mid-price ──────────
ax4 = fig.add_subplot(gs[2, 0])
style_ax(ax4, f"4 · TOMATOES Rolling Volatility — σ({WINDOW}-tick) of Mid-Price Level")

ax4.plot(tom["t_global"], tom["roll_vol_level"],
         color=VOL_C, linewidth=1.2, label=f"σ of mid-price (window={WINDOW})")
ax4.fill_between(tom["t_global"], tom["roll_vol_level"], alpha=0.2, color=VOL_C)
ax4.set_ylabel("Rolling σ (XIRECs)", fontsize=9)
ax4.set_xlabel("Timestamp (ms)")
ax4.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C)
add_day_separator(ax4, 0, tom["roll_vol_level"].max() * 1.05)

# ── PANEL 5 (row 3, right): Rolling Volatility of price differences ──────────
ax5 = fig.add_subplot(gs[2, 1])
style_ax(ax5, f"5 · TOMATOES Rolling Volatility — σ({WINDOW}-tick) of Price Changes")

ax5.plot(tom["t_global"], tom["roll_vol_diff"],
         color="#E67E22", linewidth=1.2, label=f"σ of Δprice (window={WINDOW})")
ax5.fill_between(tom["t_global"], tom["roll_vol_diff"], alpha=0.2, color="#E67E22")

# Z-score threshold reference line (from CLAUDE.md: σ_diff > 20 → spike entry)
ax5.axhline(20, color="red", linewidth=1.2, linestyle="--", alpha=0.8, label="σ=20 spike threshold")
ax5.set_ylabel("Rolling σ of Δprice", fontsize=9)
ax5.set_xlabel("Timestamp (ms)")
ax5.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C)
add_day_separator(ax5, 0, max(tom["roll_vol_diff"].max() * 1.05, 22))

# ── PANEL 6 (row 4, full width): VWAP vs mid-price ───────────────────────────
ax6 = fig.add_subplot(gs[3, :])
style_ax(ax6, "6 · TOMATOES — VWAP (from executed trades) vs Mid-Price")

ax6.plot(tom["t_global"], tom["mid_price"],
         color=MID_C, linewidth=0.8, alpha=0.7, label="Mid-price (book)")
ax6.plot(tom["t_global"], tom["wall_mid"],
         color=WALL_C, linewidth=0.8, alpha=0.7, linestyle="--", label="WallMid")

if not tom_trades.empty:
    ax6.plot(tom_trades["t_global"], tom_trades["vwap"],
             color=VWAP_C, linewidth=2.0, label="Expanding VWAP (trades)")
    ax6.scatter(tom_trades["t_global"], tom_trades["price"],
                s=15, color="white", alpha=0.5, zorder=5, label="Trade prices")

add_day_separator(ax6, tom["mid_price"].min() * 0.999, tom["mid_price"].max() * 1.001)
ax6.set_ylabel("Price (XIRECs)", fontsize=9)
ax6.set_xlabel("Timestamp (ms, both days)")
ax6.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C, ncol=2, loc="upper left")

# ── PANEL 7 (row 5, left): Spread distribution histogram ──────────────────────
ax7 = fig.add_subplot(gs[4, 0])
style_ax(ax7, "7 · Spread Distribution — TOMATOES vs EMERALDS")

bins = range(int(min(tom["spread"].min(), em["spread"].min())) - 1,
             int(max(tom["spread"].max(), em["spread"].max())) + 3)

ax7.hist(tom["spread"].dropna(), bins=bins, color=TOMATO_C,
         alpha=0.65, label="TOMATOES", density=True, edgecolor="none")
ax7.hist(em["spread"].dropna(),  bins=bins, color=EMRLD_C,
         alpha=0.65, label="EMERALDS",  density=True, edgecolor="none")

ax7.axvline(tom["spread"].median(), color=TOMATO_C, linewidth=2,
            linestyle="--", label=f"TOMATOES median = {tom['spread'].median():.0f}")
ax7.axvline(em["spread"].median(),  color=EMRLD_C,  linewidth=2,
            linestyle="--", label=f"EMERALDS  median = {em['spread'].median():.0f}")

ax7.set_xlabel("Bid-Ask Spread", fontsize=9)
ax7.set_ylabel("Density", fontsize=9)
ax7.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C)

# ── PANEL 8 (row 5, right): Mid-price return distribution ─────────────────────
ax8 = fig.add_subplot(gs[4, 1])
style_ax(ax8, "8 · TOMATOES — Mid-Price Return Distribution")

returns = tom["mid_price"].diff().dropna()
ax8.hist(returns, bins=60, color=VOL_C, alpha=0.75, edgecolor="none", density=True)

# Overlay a normal distribution for comparison
mu, sigma = returns.mean(), returns.std()
x = np.linspace(returns.min(), returns.max(), 300)
normal_pdf = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
ax8.plot(x, normal_pdf, color="white", linewidth=1.8, linestyle="--", label=f"Normal(μ={mu:.2f}, σ={sigma:.2f})")

ax8.axvline(0, color="white", linewidth=0.8, alpha=0.4)
ax8.set_xlabel("Δmid-price (tick-to-tick)", fontsize=9)
ax8.set_ylabel("Density", fontsize=9)
ax8.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT_C)

# ── save & show ───────────────────────────────────────────────────────────────
out_path = os.path.join(BASE, "market_analysis.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {out_path}")
plt.show()
