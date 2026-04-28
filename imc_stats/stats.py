"""Generic statistical helpers vendored from imc_commun/stats.py.

Vendored at the repo root so the round-5 pipeline (and Streamlit Cloud
deployment of round5/visualizer.py) does not need the imc_commun
submodule cloned. Submodule init has historically been unreliable on
Streamlit Community Cloud — this in-repo copy avoids the dependency.

The original lives in ``imc_commun/stats.py`` and is the canonical
source; if the canonical version changes, sync this file manually.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).rolling(n).mean()
    l = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))


def macd(s: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    line = ema(s, fast) - ema(s, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(s, n)
    std = s.rolling(n).std()
    return mid - k * std, mid, mid + k * std


def zscore(s: pd.Series, n: int = 20) -> pd.Series:
    return (s - s.rolling(n).mean()) / s.rolling(n).std().replace(0, np.nan)


def momentum(s: pd.Series, n: int = 10) -> pd.Series:
    return s - s.shift(n)


def hurst_rs(ts, n_max: int | None = None):
    """Hurst exponent via R/S analysis. Returns (H, R^2, lags, rs_vals).

    H < 0.45 -> mean-reverting; ~0.5 -> random walk; H > 0.55 -> trending.
    """
    ts = np.asarray(ts, dtype=float)
    ts = ts[~np.isnan(ts)]
    N = len(ts)
    if N < 20:
        return np.nan, np.nan, np.array([]), np.array([])
    if n_max is None:
        n_max = N // 2
    upper = min(n_max, N // 2)
    step = max(1, (upper - 10) // 50)
    lags, rs_vals = [], []
    for n in range(10, upper + 1, step):
        chunks = [ts[i:i + n] for i in range(0, N - n + 1, n)]
        rs_chunk = []
        for chunk in chunks:
            mean = chunk.mean()
            dev = np.cumsum(chunk - mean)
            R = dev.max() - dev.min()
            S = chunk.std(ddof=1)
            if S > 0:
                rs_chunk.append(R / S)
        if rs_chunk:
            lags.append(n)
            rs_vals.append(np.mean(rs_chunk))
    if len(lags) < 3:
        return np.nan, np.nan, np.array(lags), np.array(rs_vals)
    lags_a, rs_a = np.array(lags), np.array(rs_vals)
    log_n, log_rs = np.log(lags_a), np.log(rs_a)
    H, intercept = np.polyfit(log_n, log_rs, 1)
    ss_res = np.sum((log_rs - np.polyval([H, intercept], log_n)) ** 2)
    ss_tot = np.sum((log_rs - log_rs.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return H, r2, lags_a, rs_a


def variance_ratio(ret, k: int):
    """Lo-MacKinlay (1988) variance ratio at horizon k.

    Returns (vr, z). VR > 1 -> momentum; VR < 1 -> mean-reversion;
    VR ~ 1 -> random walk. z is the homoskedastic-version standard normal stat.
    """
    ret = np.asarray(ret, dtype=float)
    ret = ret[~np.isnan(ret)]
    T = len(ret)
    if T <= k + 1 or k < 2:
        return np.nan, np.nan
    mu = ret.mean()
    ret_k = np.array([ret[i:i + k].sum() for i in range(T - k + 1)])
    var1 = ((ret - mu) ** 2).sum() / (T - 1)
    vark = ((ret_k - k * mu) ** 2).sum() / (len(ret_k) - 1) / k
    if var1 == 0:
        return np.nan, np.nan
    vr = vark / var1
    z = (vr - 1) / np.sqrt(2 * (2 * k - 1) * (k - 1) / (3 * k * T))
    return vr, z
