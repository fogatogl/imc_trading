"""VE mean-reversion / distribution / spread analysis (round 4).

Outputs a dict of summary stats and saves figures to figures_ve_vev/.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

DATA = r"c:\Users\fogat\Desktop\imc_trading\dataset\ROUND_4"
OUT = r"c:\Users\fogat\Desktop\imc_trading\round4\figures_ve_vev"
os.makedirs(OUT, exist_ok=True)


def load() -> pd.DataFrame:
    frames = []
    for d in (1, 2, 3):
        df = pd.read_csv(os.path.join(DATA, f"prices_round_4_day_{d}.csv"), sep=";")
        df = df[df["product"] == "VELVETFRUIT_EXTRACT"].copy()
        df["day"] = d
        df["t"] = df["timestamp"] // 100
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def adf_pvalue(x: np.ndarray) -> float:
    try:
        from statsmodels.tsa.stattools import adfuller
        return float(adfuller(x, autolag="AIC")[1])
    except Exception:
        return float("nan")


def variance_ratio(x: np.ndarray, q: int) -> float:
    """Lo-MacKinlay variance ratio. VR=1 random walk, <1 mean-revert, >1 trending."""
    r = np.diff(x)
    var1 = r.var(ddof=1)
    rq = x[q:] - x[:-q]
    varq = rq.var(ddof=1) / q
    return float(varq / var1)


def hurst(x: np.ndarray, lags=range(2, 100)) -> float:
    """Simple R/S-style Hurst via log-log of std of lag-differences."""
    tau = [np.std(x[lag:] - x[:-lag]) for lag in lags]
    poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return float(poly[0])


def half_life_ou(x: np.ndarray) -> float:
    """OLS on Δx_t = a + b·x_{t-1}. Half-life = -ln(2)/ln(1+b) if b<0."""
    dx = np.diff(x)
    xl = x[:-1]
    A = np.vstack([np.ones_like(xl), xl]).T
    coef, *_ = np.linalg.lstsq(A, dx, rcond=None)
    a, b = coef
    if b >= 0:
        return float("inf")
    return float(-np.log(2) / np.log(1 + b))


def main() -> None:
    df = load()
    df = df.sort_values(["day", "timestamp"]).reset_index(drop=True)

    # ---- spread ----
    df["spread"] = df["ask_price_1"] - df["bid_price_1"]

    print("=== VE mid summary ===")
    for d in (1, 2, 3):
        sub = df[df["day"] == d]
        m = sub["mid_price"].to_numpy()
        print(f"day {d}: n={len(m):5d} | mid mean={m.mean():.2f} std={m.std():.3f} | "
              f"min={m.min():.0f} max={m.max():.0f} | first={m[0]:.0f} last={m[-1]:.0f}")

    print("\n=== Spread (ask1-bid1) ===")
    print(df["spread"].describe())
    print("Spread value counts:")
    print(df["spread"].value_counts().sort_index())

    # ---- returns / log-returns ----
    df["ret"] = df.groupby("day")["mid_price"].diff()
    df["logret"] = df.groupby("day")["mid_price"].apply(lambda s: np.log(s).diff()).reset_index(level=0, drop=True)
    r = df["ret"].dropna().to_numpy()

    print(f"\n=== Tick returns (mid diff) ===")
    print(f"n={len(r)} mean={r.mean():.4f} std={r.std():.4f} "
          f"skew={stats.skew(r):.3f} kurt(excess)={stats.kurtosis(r):.3f}")
    print(f"P(r=0) = {(r==0).mean():.3f}")
    print(f"quantiles 1/5/50/95/99: {np.quantile(r, [.01,.05,.5,.95,.99])}")

    # Jarque-Bera
    jb = stats.jarque_bera(r)
    print(f"Jarque-Bera stat={jb.statistic:.1f} p={jb.pvalue:.2e} (reject normal)")

    # ---- per-day stationarity tests ----
    print("\n=== Per-day stationarity ===")
    rows = []
    for d in (1, 2, 3):
        m = df[df["day"] == d]["mid_price"].to_numpy()
        adf_p = adf_pvalue(m)
        vr2 = variance_ratio(m, 2)
        vr10 = variance_ratio(m, 10)
        vr50 = variance_ratio(m, 50)
        vr200 = variance_ratio(m, 200)
        H = hurst(m)
        hl = half_life_ou(m)
        rows.append((d, adf_p, vr2, vr10, vr50, vr200, H, hl,
                     m[-1] - m[0], m.std()))
        print(f"day {d}: ADF p={adf_p:.4g} | VR(2)={vr2:.3f} VR(10)={vr10:.3f} "
              f"VR(50)={vr50:.3f} VR(200)={vr200:.3f} | H={H:.3f} | "
              f"OU half-life={hl:.0f} ticks | net drift={m[-1]-m[0]:+.1f}")

    # pooled VR
    print("\n=== Pooled per-day-diff VR ===")
    diffs_2 = []
    diffs_10 = []
    for d in (1, 2, 3):
        m = df[df["day"] == d]["mid_price"].to_numpy()
        diffs_2.append(m[2:] - m[:-2])
        diffs_10.append(m[10:] - m[:-10])
    r1 = np.diff(np.concatenate([df[df.day == d]["mid_price"].to_numpy() for d in (1, 2, 3)]))
    var1 = r1.var(ddof=1)
    vr2_p = np.concatenate(diffs_2).var(ddof=1) / 2 / var1
    vr10_p = np.concatenate(diffs_10).var(ddof=1) / 10 / var1
    print(f"VR(2)={vr2_p:.3f} VR(10)={vr10_p:.3f}")

    # ---- autocorrelation of returns ----
    print("\n=== Return autocorrelation (lag 1..10) ===")
    rs = pd.Series(r)
    for k in (1, 2, 3, 5, 10, 50, 100):
        print(f"  acf({k:3d}) = {rs.autocorr(k):+.4f}")

    # ---- forward-move conditional on z-score (mean-rev test) ----
    print("\n=== Forward-move conditional on rolling-z-score (window=200) ===")
    rows_z = []
    for d in (1, 2, 3):
        sub = df[df["day"] == d].copy()
        m = sub["mid_price"].to_numpy()
        win = 200
        mean = pd.Series(m).rolling(win, min_periods=win).mean().to_numpy()
        std = pd.Series(m).rolling(win, min_periods=win).std().to_numpy()
        z = (m - mean) / std
        for h in (50, 200, 500):
            fwd = np.full_like(m, np.nan, dtype=float)
            fwd[:-h] = m[h:] - m[:-h]
            mask = ~np.isnan(z) & ~np.isnan(fwd)
            zh = z[mask]
            fh = fwd[mask]
            hi = zh > 1.5
            lo = zh < -1.5
            rows_z.append((d, h, win, hi.sum(), fh[hi].mean() if hi.any() else np.nan,
                           lo.sum(), fh[lo].mean() if lo.any() else np.nan))
    print(f"{'day':>3} {'h':>4} {'win':>4} {'n_hi':>6} {'fwd_hi':>8} {'n_lo':>6} {'fwd_lo':>8}")
    for d, h, w, nh, fh, nl, fl in rows_z:
        print(f"{d:>3} {h:>4} {w:>4} {nh:>6} {fh:>8.2f} {nl:>6} {fl:>8.2f}")

    # ---- figures ----
    fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=False)
    for i, d in enumerate((1, 2, 3)):
        sub = df[df["day"] == d]
        ax[i].plot(sub["timestamp"].to_numpy(), sub["mid_price"].to_numpy(), lw=0.6)
        ax[i].set_title(f"VE mid — day {d}")
        ax[i].set_ylabel("mid (SS)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig5_ve_mid_per_day.png"), dpi=120)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    rclip = r[(r > -10) & (r < 10)]
    ax[0].hist(rclip, bins=np.arange(-10, 11, 1) - 0.5, edgecolor="k")
    ax[0].set_title(f"VE 1-tick mid Δ (clipped ±10) — n={len(r)}")
    ax[0].set_xlabel("Δmid")
    ax[0].set_yscale("log")

    spreads = df["spread"].dropna().astype(int)
    vc = spreads.value_counts().sort_index()
    ax[1].bar(vc.index.to_numpy(), vc.values, edgecolor="k")
    ax[1].set_title("VE spread distribution (ask1 − bid1)")
    ax[1].set_xlabel("spread")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig6_ve_returns_spread.png"), dpi=120)

    print(f"\nFigures saved to {OUT}")


if __name__ == "__main__":
    main()
