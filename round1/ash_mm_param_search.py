"""
ash_mm_param_search.py
----------------------
Grid search for the ASH_COATED_OSMIUM pure market-making strategy.

Strategy recap:
  fair_value  = EMA(mid_price, span=ema_span)
  sigma       = rolling_std(1-bar price changes, window=vol_window)
  half_spread = max(min_half_spread, vol_mult * sigma)
  skew        = inv_skew * position  (push quotes toward unwinding inventory)
  my_bid      = round(fair_value - half_spread - skew)
  my_ask      = round(fair_value + half_spread - skew)

Fill model (conservative passive):
  BUY  fills at my_bid  when best_ask  <= my_bid   (seller crossed to our bid)
  SELL fills at my_ask  when best_bid  >= my_ask   (buyer  crossed to our ask)
  Volume = min(QUOTE_SIZE, position capacity, available book volume)

Statistical basis:
  VR(2)=0.506 → ρ(1)≈-0.494 (very strong mean-reversion)
  VR(4)=0.258 → 4-bar variance is only 26% of random walk
  FFT dominant cycles: 2-3 bars and 14 bars
  Position limit: 50 units

Run from project root:
  python round1/ash_mm_param_search.py
"""

import glob
import itertools
import math
import numpy as np
import pandas as pd
from dataclasses import dataclass

# ── Config ─────────────────────────────────────────────────────────────────────
DATA_DIR = "dataset/ROUND_1"
PRODUCT = "ASH_COATED_OSMIUM"
POS_LIMIT = 50
QUOTE_SIZE = 10   # max units filled per bar (models competition for fills)

# ── Parameter grid ─────────────────────────────────────────────────────────────
GRID: dict = dict(
    ema_span        = [5, 10, 20, 30],          # EMA smoothing window
    vol_window      = [5, 10, 20],              # rolling-std window for realized vol
    vol_mult        = [0.5, 1.0, 1.5, 2.0, 3.0],   # half_spread = max(min_hs, mult*σ)
    min_half_spread = [1.0, 2.0, 3.0, 5.0, 8.0],   # absolute floor (price ticks)
    inv_skew        = [0.0, 0.5, 1.0, 2.0],    # quote shift per unit of inventory
)


# ── Data loading ───────────────────────────────────────────────────────────────
def load_prices() -> pd.DataFrame:
    files = sorted(glob.glob(f"{DATA_DIR}/prices_round_1_day_*.csv"))
    if not files:
        raise FileNotFoundError(f"No price CSVs found in {DATA_DIR}/")

    dfs = [pd.read_csv(f, sep=";") for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = (
        df[df["product"] == PRODUCT]
        .sort_values(["day", "timestamp"])
        .reset_index(drop=True)
    )

    # Empty-book rows have mid_price == 0 → treat as missing, forward-fill
    df["mid_price"] = df["mid_price"].replace(0.0, np.nan).ffill()

    # Book levels: replace 0 with NaN so fill checks skip one-sided books cleanly
    for col in ["bid_price_1", "ask_price_1"]:
        df[col] = df[col].replace(0.0, np.nan)
    for col in ["bid_volume_1", "ask_volume_1"]:
        df[col] = df[col].fillna(0.0)

    return df.dropna(subset=["mid_price"]).reset_index(drop=True)


# ── Vectorised pre-computation (EMA and rolling σ) ────────────────────────────
def compute_ema(mids: np.ndarray, span: int) -> np.ndarray:
    """Incremental EMA — identical to pandas ewm(span=span, adjust=False)."""
    alpha = 2.0 / (span + 1)
    ema = np.empty_like(mids)
    ema[0] = mids[0]
    for i in range(1, len(mids)):
        ema[i] = alpha * mids[i] + (1.0 - alpha) * ema[i - 1]
    return ema


def compute_sigma(mids: np.ndarray, window: int) -> np.ndarray:
    """Rolling std of 1-bar price changes; NaN-filled to 1.0."""
    changes = np.diff(mids, prepend=mids[0])
    sigma = (
        pd.Series(changes)
        .rolling(window, min_periods=2)
        .std()
        .fillna(1.0)
        .values
    )
    return sigma


# ── Single-combo simulation ────────────────────────────────────────────────────
@dataclass
class Params:
    ema_span: int
    vol_window: int
    vol_mult: float
    min_half_spread: float
    inv_skew: float


def simulate(
    ema: np.ndarray,
    sigma: np.ndarray,
    best_bids: np.ndarray,
    best_asks: np.ndarray,
    bid_vols: np.ndarray,
    ask_vols: np.ndarray,
    mids: np.ndarray,
    p: Params,
) -> dict:
    n = len(mids)
    pos: int = 0
    cash: float = 0.0
    pnl = np.empty(n, dtype=np.float64)

    for i in range(n):
        hs = max(p.min_half_spread, p.vol_mult * sigma[i])
        skew = p.inv_skew * pos          # >0 when long → push quotes down
        fv = ema[i]

        my_bid = int(round(fv - hs - skew))
        my_ask = int(round(fv + hs - skew))
        if my_bid >= my_ask:
            my_ask = my_bid + 1

        ba = best_asks[i]
        bb = best_bids[i]

        # BUY fill: market ask crossed down to our bid
        if not math.isnan(ba) and ba <= my_bid:
            cap = POS_LIMIT - pos
            if cap > 0:
                vol = min(QUOTE_SIZE, cap, int(ask_vols[i]) if ask_vols[i] > 0 else QUOTE_SIZE)
                pos  += vol
                cash -= vol * my_bid     # we pay our quoted bid price

        # SELL fill: market bid crossed up to our ask
        if not math.isnan(bb) and bb >= my_ask:
            cap = POS_LIMIT + pos
            if cap > 0:
                vol = min(QUOTE_SIZE, cap, int(bid_vols[i]) if bid_vols[i] > 0 else QUOTE_SIZE)
                pos  -= vol
                cash += vol * my_ask     # we receive our quoted ask price

        pnl[i] = cash + pos * mids[i]   # mark-to-market

    returns = np.diff(pnl)
    std_r = returns.std()
    sharpe = float(returns.mean() / std_r * math.sqrt(len(returns))) if std_r > 1e-9 else 0.0
    cummax = np.maximum.accumulate(pnl)
    max_dd = float((pnl - cummax).min())
    n_trades = int(np.sum(np.abs(np.diff(np.array(
        [0] + [pos] * n   # rough proxy; real count tracked separately
    )))))

    return {
        "pnl":       float(pnl[-1]),
        "sharpe":    sharpe,
        "max_dd":    max_dd,
        "final_pos": pos,
    }


# ── Grid search ────────────────────────────────────────────────────────────────
def run_search(df: pd.DataFrame) -> pd.DataFrame:
    mids      = df["mid_price"].values.astype(float)
    best_bids = df["bid_price_1"].values.astype(float)
    best_asks = df["ask_price_1"].values.astype(float)
    bid_vols  = df["bid_volume_1"].values.astype(float)
    ask_vols  = df["ask_volume_1"].values.astype(float)

    # Pre-compute EMA & sigma for each unique span/window combo
    print("Pre-computing EMA and vol surfaces…")
    ema_cache   = {s: compute_ema(mids, s)   for s in GRID["ema_span"]}
    sigma_cache = {w: compute_sigma(mids, w) for w in GRID["vol_window"]}

    keys   = list(GRID.keys())
    combos = list(itertools.product(*GRID.values()))
    print(f"Running {len(combos):,} parameter combinations over {len(df):,} bars…\n")

    rows = []
    for combo in combos:
        p = Params(**dict(zip(keys, combo)))
        res = simulate(
            ema_cache[p.ema_span],
            sigma_cache[p.vol_window],
            best_bids, best_asks, bid_vols, ask_vols, mids,
            p,
        )
        rows.append({k: getattr(p, k) for k in keys} | res)

    return pd.DataFrame(rows)


# ── Reporting ──────────────────────────────────────────────────────────────────
def report(results: pd.DataFrame) -> None:
    param_keys = list(GRID.keys())

    def _fmt(df: pd.DataFrame) -> str:
        return df.to_string(
            index=False,
            float_format=lambda x: f"{x:>10.2f}",
        )

    by_sharpe = results.sort_values("sharpe", ascending=False)
    by_pnl    = results.sort_values("pnl",    ascending=False)

    print("=" * 72)
    print("TOP 20 by SHARPE")
    print("=" * 72)
    print(_fmt(by_sharpe.head(20)))

    print("\n" + "=" * 72)
    print("TOP 20 by PnL")
    print("=" * 72)
    print(_fmt(by_pnl.head(20)))

    best = by_sharpe.iloc[0]
    print("\n" + "=" * 72)
    print("BEST PARAMS  (highest Sharpe)")
    print("=" * 72)
    for k in param_keys:
        print(f"  {k:<22} = {best[k]}")
    print(f"  {'sharpe':<22} = {best['sharpe']:.4f}")
    print(f"  {'pnl':<22} = {best['pnl']:.0f}")
    print(f"  {'max_dd':<22} = {best['max_dd']:.0f}")

    print("\n" + "=" * 72)
    print("PARAMETER SENSITIVITY  (mean Sharpe per value)")
    print("=" * 72)
    for k in param_keys:
        print(f"\n  {k}:")
        tbl = results.groupby(k)["sharpe"].mean().sort_values(ascending=False)
        for val, avg in tbl.items():
            marker = "  ← best" if val == best[k] else ""
            print(f"    {str(val):>8}  ->  {avg:>8.4f}{marker}")


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"Loading {PRODUCT} data from {DATA_DIR}…")
    df = load_prices()
    print(f"  {len(df):,} bars across days {sorted(df['day'].unique())}\n")

    results = run_search(df)
    report(results)

    # Persist results for inspection
    out = "round1/ash_mm_param_results.csv"
    results.sort_values("sharpe", ascending=False).to_csv(out, index=False)
    print(f"\nFull results saved → {out}")


if __name__ == "__main__":
    main()
