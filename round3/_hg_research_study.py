"""HYDROGEL_PACK research-grade microstructure study.

Outputs printed in a single pass: descriptives, microstructure noise, reversion,
regime structure, OB imbalance predictive power, adverse-selection profile, and
maker-PnL decomposition (worse-mode fill simulator).
"""
from __future__ import annotations

import math
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "dataset" / "ROUND_3"
SYM = "HYDROGEL_PACK"


def load_prices() -> pd.DataFrame:
    parts = []
    for d in (0, 1, 2):
        p = ROOT / f"prices_round_3_day_{d}.csv"
        df = pd.read_csv(p, sep=";")
        df = df[df["product"] == SYM].copy()
        df["abs_ts"] = d * 1_000_000 + df["timestamp"]
        df["day"] = d
        parts.append(df)
    out = pd.concat(parts, ignore_index=True).sort_values("abs_ts").reset_index(drop=True)
    return out


def load_trades() -> pd.DataFrame:
    parts = []
    for d in (0, 1, 2):
        p = ROOT / f"trades_round_3_day_{d}.csv"
        df = pd.read_csv(p, sep=";")
        df = df[df["symbol"] == SYM].copy()
        df["abs_ts"] = d * 1_000_000 + df["timestamp"]
        df["day"] = d
        parts.append(df)
    out = pd.concat(parts, ignore_index=True).sort_values("abs_ts").reset_index(drop=True)
    return out


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def describe_basic(px: pd.DataFrame) -> None:
    section("1. BASIC DESCRIPTIVES")
    mid = px["mid_price"].astype(float).values
    bid = px["bid_price_1"].astype(float).values
    ask = px["ask_price_1"].astype(float).values
    spread = ask - bid
    print(f"ticks total         : {len(px)}")
    print(f"per-day ticks       : {px.groupby('day').size().tolist()}")
    print(f"mid mean / std      : {mid.mean():.3f} / {mid.std():.3f}")
    print(f"mid min / max       : {mid.min():.1f} / {mid.max():.1f}")
    print(f"per-day mid mean    : {px.groupby('day')['mid_price'].mean().round(3).tolist()}")
    print(f"per-day mid std     : {px.groupby('day')['mid_price'].std().round(3).tolist()}")
    print(f"spread mean/std/med : {spread.mean():.3f} / {spread.std():.3f} / {np.median(spread):.1f}")
    print()
    s_counts = Counter(spread.astype(int))
    print("spread distribution (count, share):")
    for s, c in sorted(s_counts.items())[:20]:
        print(f"  spread={s:>3}  n={c:>6}  share={c/len(spread):.4f}")
    print()
    p10 = (np.abs(mid - 10000) < 30).mean()
    p20 = (np.abs(mid - 10000) < 50).mean()
    p30 = (np.abs(mid - 10000) < 100).mean()
    print(f"P(|mid-10000|<30)   : {p10:.4f}")
    print(f"P(|mid-10000|<50)   : {p20:.4f}")
    print(f"P(|mid-10000|<100)  : {p30:.4f}")
    print(f"per-day distance from 10000:")
    print(px.groupby('day')['mid_price'].apply(lambda s: float((s - 10000).abs().mean())).round(3))


def autocorrs(arr: np.ndarray, lags: list[int]) -> dict[int, float]:
    arr = arr - arr.mean()
    var = arr.var()
    return {lag: float(np.dot(arr[:-lag], arr[lag:]) / (len(arr) - lag) / var) for lag in lags}


def describe_returns(px: pd.DataFrame) -> None:
    section("2. RETURN DYNAMICS / AUTOCORRELATION (sub-sampled)")
    mid = px["mid_price"].astype(float).values
    for dt in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        s = mid[::dt]
        r = np.diff(s)
        if len(r) < 50:
            continue
        ac = autocorrs(r, [1, 2, 5, 10])
        print(
            f"dt={dt:>4}  n={len(r):>6}  std(Δ)={r.std():>7.4f}  "
            f"ac1={ac[1]:>+0.4f}  ac2={ac[2]:>+0.4f}  ac5={ac[5]:>+0.4f}  ac10={ac[10]:>+0.4f}"
        )
    print()
    section("2b. VARIANCE RATIO TEST (Lo-MacKinlay, Δlog mid)")
    logp = np.log(mid)
    r1 = np.diff(logp)
    var1 = r1.var()
    for q in (2, 4, 8, 16, 32, 64, 128, 256):
        rq = logp[q::q] - logp[:-q:q]
        rq = rq[: len(rq) - 1] if len(rq) > 1 else rq
        if len(rq) < 50:
            continue
        vr = rq.var() / (q * var1)
        print(f"q={q:>4}  VR(q)={vr:.4f}   (1.0 = random walk; <1 mean-revert; >1 trend)")


def two_scale_var(px: pd.DataFrame) -> None:
    section("3. NOISE-CORRECTED VARIANCE (two-scale fit)")
    mid = px["mid_price"].astype(float).values
    pts = []
    for dt in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        r = np.diff(mid[::dt])
        if len(r) < 50:
            continue
        v = r.var()
        pts.append((dt, v))
    print("dt, var(Δmid_dt):")
    for dt, v in pts:
        print(f"  dt={dt:>4}  Var={v:.4f}")
    # σ²_meas(dt) = σ²_true * dt + 2η²    (per-tick model with iid noise η)
    x = np.array([dt for dt, _ in pts], dtype=float)
    y = np.array([v for _, v in pts], dtype=float)
    A = np.column_stack([x, np.ones_like(x)])
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    sigma2_per_tick, twoeta2 = sol
    print()
    print(f"σ²_true per tick    = {sigma2_per_tick:.5f}")
    print(f"σ_true  per tick    = {math.sqrt(max(sigma2_per_tick, 0)):.4f}")
    print(f"2 η²                = {twoeta2:.4f}  →  η ≈ {math.sqrt(max(twoeta2, 0) / 2):.4f}")
    print(f"signal/noise per Δ1 = σ_true / η  = "
          f"{math.sqrt(max(sigma2_per_tick, 0)) / max(math.sqrt(max(twoeta2, 0)/2), 1e-9):.4f}")


def reversion_strength(px: pd.DataFrame) -> None:
    section("4. SLOW REVERSION — corr(mid - μ_window, Δmid_h)")
    mid = px["mid_price"].astype(float).values
    for win in (500, 2000, 5000, 20000):
        if len(mid) <= win + 50:
            continue
        mu = pd.Series(mid).rolling(win, min_periods=win).mean().values
        dev = mid - mu
        for h in (50, 200, 500, 1000, 2000):
            if h >= len(mid) - win:
                continue
            d = mid[win + h:] - mid[win:-h]
            x = dev[win:-h]
            mask = ~np.isnan(x)
            if mask.sum() < 200:
                continue
            c = float(np.corrcoef(x[mask], d[mask])[0, 1])
            print(f"window={win:>5}  horizon={h:>5}  corr={c:+.3f}")
    print()
    section("4b. Reversion vs FIXED 10000 anchor (the v9 thesis)")
    for h in (50, 200, 500, 1000, 2000, 5000):
        if h >= len(mid):
            continue
        d = mid[h:] - mid[:-h]
        x = mid[:-h] - 10000
        c = float(np.corrcoef(x, d)[0, 1])
        print(f"anchor=10000  horizon={h:>5}  corr={c:+.3f}")


def regime_structure(px: pd.DataFrame) -> None:
    section("5. REGIME STRUCTURE — drift episodes & spread clusters")
    mid = px["mid_price"].astype(float).values
    spread = (px["ask_price_1"] - px["bid_price_1"]).astype(float).values
    # Per-day longest sustained drift
    for d in (0, 1, 2):
        m = px[px["day"] == d]["mid_price"].astype(float).values
        if len(m) < 100:
            continue
        ema_short = pd.Series(m).ewm(halflife=200).mean().values
        ema_long = pd.Series(m).ewm(halflife=2000).mean().values
        drift = ema_short - ema_long
        max_pos = drift.max()
        max_neg = drift.min()
        # longest run with same sign of drift > 5
        sign = np.sign(np.where(np.abs(drift) > 5, drift, 0))
        runs = []
        cur_s, cur_n = 0, 0
        for s in sign:
            if s == cur_s and s != 0:
                cur_n += 1
            else:
                if cur_n > 0:
                    runs.append((cur_s, cur_n))
                cur_s, cur_n = s, 1 if s != 0 else 0
        if cur_n > 0:
            runs.append((cur_s, cur_n))
        runs_sorted = sorted(runs, key=lambda x: -x[1])[:5]
        print(f"day {d}: drift max +{max_pos:.1f} / {max_neg:.1f}, top drift episodes (sign,len): {runs_sorted}")
    print()
    section("5b. Tight-spread regime durations")
    tight = (spread <= 9).astype(int)
    runs = []
    cur = 0
    for t in tight:
        if t:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    if runs:
        a = np.array(runs)
        print(f"tight-spread runs: n={len(a)} median_len={np.median(a):.1f} max={a.max()} mean={a.mean():.2f}")
        print(f"share of ticks in tight regime: {tight.mean():.4f}")


def imbalance_predictive(px: pd.DataFrame) -> None:
    section("6. ORDER BOOK IMBALANCE → next-tick Δmid")
    bv = px["bid_volume_1"].fillna(0).astype(float).values
    av = px["ask_volume_1"].fillna(0).astype(float).values
    bv2 = px["bid_volume_2"].fillna(0).astype(float).values
    av2 = px["ask_volume_2"].fillna(0).astype(float).values
    mid = px["mid_price"].astype(float).values
    dmid = np.diff(mid)
    # L1 imbalance
    imb1 = (bv - av) / np.maximum(bv + av, 1)
    # L1+L2
    imb2 = ((bv + bv2) - (av + av2)) / np.maximum(bv + bv2 + av + av2, 1)
    print(f"corr(L1 imb_t, Δmid_{{t+1}})   = {np.corrcoef(imb1[:-1], dmid)[0,1]:+.4f}")
    print(f"corr(L1+L2 imb_t, Δmid_{{t+1}}) = {np.corrcoef(imb2[:-1], dmid)[0,1]:+.4f}")
    # multi-horizon
    for h in (1, 5, 10, 50):
        d = mid[h:] - mid[:-h]
        c1 = float(np.corrcoef(imb1[:-h], d)[0, 1])
        c2 = float(np.corrcoef(imb2[:-h], d)[0, 1])
        print(f"corr(L1 imb_t, mid_{{t+{h}}}-mid_t)  = {c1:+.4f}    L1+L2: {c2:+.4f}")
    # Conditional expected next-tick move by imb bucket
    print()
    print("Conditional E[Δmid_{t+1} | L1 imb bucket]:")
    for lo, hi in [(-1.01, -0.5), (-0.5, -0.1), (-0.1, 0.1), (0.1, 0.5), (0.5, 1.01)]:
        mask = (imb1[:-1] >= lo) & (imb1[:-1] < hi)
        if mask.sum() < 100:
            continue
        print(f"  imb in [{lo:+.2f},{hi:+.2f}]: n={mask.sum():>6}  E[Δ]={dmid[mask].mean():+.4f}  std={dmid[mask].std():.3f}")


def adverse_selection(px: pd.DataFrame, tr: pd.DataFrame) -> None:
    section("7. POST-TRADE ADVERSE SELECTION (signed mid drift after market trades)")
    # join market trade timestamp -> nearest mid before/at trade
    px_idx = px.set_index("abs_ts")
    mid_series = px_idx["mid_price"].astype(float)
    bid = px_idx["bid_price_1"].astype(float)
    ask = px_idx["ask_price_1"].astype(float)
    # classify market trade direction by Lee-Ready: trade above mid -> buyer initiated
    horizons = [1, 10, 50, 200, 1000]
    for h_ticks in horizons:
        h_ts = h_ticks * 100  # 1 tick = 100 timestamp units
        signed_drifts = []
        for ts, p in zip(tr["abs_ts"].values, tr["price"].astype(float).values):
            try:
                ref = mid_series.asof(ts)
                future = mid_series.asof(ts + h_ts)
            except Exception:
                continue
            if pd.isna(ref) or pd.isna(future):
                continue
            sign = 1 if p > ref else (-1 if p < ref else 0)
            if sign == 0:
                continue
            signed_drifts.append(sign * (future - ref))
        a = np.array(signed_drifts)
        if len(a) < 50:
            continue
        print(f"h={h_ticks:>5} ticks  n={len(a):>6}  E[signed drift]={a.mean():+.3f}  std={a.std():.3f}  "
              f"5/50/95%={np.percentile(a,5):+.2f} / {np.percentile(a,50):+.2f} / {np.percentile(a,95):+.2f}")


def maker_pnl_decomp(px: pd.DataFrame, tr: pd.DataFrame) -> None:
    section("8. PURE-MAKER PnL DECOMPOSITION (worse-mode sim, target=0)")
    # Quote bb+1 / ba-1 every tick. Fill if a market trade strictly beats our quote.
    px = px.copy().reset_index(drop=True)
    bid = px["bid_price_1"].astype(float).values
    ask = px["ask_price_1"].astype(float).values
    mid = px["mid_price"].astype(float).values
    abs_ts = px["abs_ts"].values

    # bucket trades by tick
    tr_by_ts: dict[int, list[tuple[float, float]]] = {}
    for ts, p, q in zip(tr["abs_ts"].values, tr["price"].astype(float).values, tr["quantity"].astype(float).values):
        tr_by_ts.setdefault(int(ts), []).append((float(p), float(q)))

    # map abs_ts to next available tick index
    ts_index = {int(t): i for i, t in enumerate(abs_ts)}

    pos = 0.0
    cash = 0.0
    half_spread_pnl = 0.0
    inventory_pnl_proxy = 0.0
    fills_buy = 0
    fills_sell = 0
    QUOTE = 25
    LIMIT = 200
    for i in range(len(px) - 1):
        my_bid = bid[i] + 1
        my_ask = ask[i] - 1
        ts = int(abs_ts[i])
        # any trade in this tick at strictly worse price executes
        for p, q in tr_by_ts.get(ts, []):
            qsz = min(QUOTE, q)
            if p < my_bid and pos + qsz <= LIMIT:
                # fill our bid
                fills_buy += 1
                pos += qsz
                cash -= my_bid * qsz
                half_spread_pnl += (mid[i] - my_bid) * qsz
            if p > my_ask and pos - qsz >= -LIMIT:
                fills_sell += 1
                pos -= qsz
                cash += my_ask * qsz
                half_spread_pnl += (my_ask - mid[i]) * qsz
    last_mid = mid[-1]
    pnl = cash + pos * last_mid
    print(f"ticks            : {len(px)}")
    print(f"buy fills        : {fills_buy}")
    print(f"sell fills       : {fills_sell}")
    print(f"end position     : {pos:+.0f}")
    print(f"end cash         : {cash:.0f}")
    print(f"mark-to-mid PnL  : {pnl:.0f}")
    print(f"half-spread PnL  : {half_spread_pnl:.0f}  (theoretical edge captured at fill)")
    print(f"inventory P&L    : {pnl - half_spread_pnl:.0f}  (price drift on residual inventory)")


def main() -> None:
    px = load_prices()
    tr = load_trades()
    print(f"hydrogel rows: prices={len(px)} trades={len(tr)}")
    describe_basic(px)
    describe_returns(px)
    two_scale_var(px)
    reversion_strength(px)
    regime_structure(px)
    imbalance_predictive(px)
    adverse_selection(px, tr)
    maker_pnl_decomp(px, tr)


if __name__ == "__main__":
    main()
