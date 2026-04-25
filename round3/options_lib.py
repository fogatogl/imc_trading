"""Shared options pricing primitives for Round 3 strategies.

Pure-Python (stdlib only) so it imports cleanly inside the prosperity4bt sandbox.

Provides:
  * BS price + greeks for European calls (zero-rate forward = spot).
  * Robust implied-vol solver (bracket + bisection; no scipy).
  * Smile fitters: vega-weighted parabola/cubic in moneyness, SVI raw.
  * Rolling smile state for online refit inside `Trader.run`.

References:
  * `round3/trader_gamma_v7.py:48-53` for the call_delta convention.
  * `round3/round3_analysis.ipynb` cells around 7d12a55e for IV solver shape.
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Optional, Sequence

# ---------- normal CDF / PDF ----------

_SQRT_2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT_2))


def norm_pdf(x: float) -> float:
    return _INV_SQRT_2PI * math.exp(-0.5 * x * x)


# ---------- Black-Scholes (zero rate, European call on forward = spot) ----------


def _d1_d2(S: float, K: float, T: float, sigma: float) -> tuple[float, float]:
    vt = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * vt * vt) / vt
    d2 = d1 - vt
    return d1, d2


def bs_call(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.0, S - K)
    d1, d2 = _d1_d2(S, K, T, sigma)
    return S * norm_cdf(d1) - K * norm_cdf(d2)


def bs_call_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 1.0 if S > K else 0.0
    d1, _ = _d1_d2(S, K, T, sigma)
    return norm_cdf(d1)


def bs_call_gamma(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))


def bs_call_vega(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, sigma)
    return S * norm_pdf(d1) * math.sqrt(T)


def bs_call_theta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, sigma)
    return -S * norm_pdf(d1) * sigma / (2.0 * math.sqrt(T))


# ---------- IV solver ----------


def implied_vol_call(
    price: float,
    S: float,
    K: float,
    T: float,
    *,
    lo: float = 1e-3,
    hi: float = 3.0,
    tol: float = 1e-5,
    max_iter: int = 60,
) -> Optional[float]:
    """Bracketed bisection. Returns None if price is outside arbitrage bounds."""
    if T <= 0 or S <= 0 or K <= 0:
        return None
    intrinsic = max(0.0, S - K)
    upper = S
    if not (intrinsic - 1e-6 <= price <= upper + 1e-6):
        return None
    f_lo = bs_call(S, K, T, lo) - price
    f_hi = bs_call(S, K, T, hi) - price
    if f_lo > 0:
        return lo
    if f_hi < 0:
        return hi
    a, b = lo, hi
    for _ in range(max_iter):
        m = 0.5 * (a + b)
        fm = bs_call(S, K, T, m) - price
        if abs(fm) < tol:
            return m
        if fm < 0:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


# ---------- Moneyness helpers ----------


def log_moneyness(S: float, K: float, T: float) -> float:
    if T <= 0 or S <= 0 or K <= 0:
        return 0.0
    return math.log(S / K) / math.sqrt(T)


def log_strike(S: float, K: float) -> float:
    return math.log(K / S)


def total_variance(sigma: float, T: float) -> float:
    return sigma * sigma * T


# ---------- Polynomial-in-moneyness smile fitters ----------


def _solve_normal_eq(A: list[list[float]], b: list[float]) -> Optional[list[float]]:
    """Tiny Gaussian elimination for an n x n normal-equations system."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        pivot = i
        for r in range(i + 1, n):
            if abs(M[r][i]) > abs(M[pivot][i]):
                pivot = r
        if abs(M[pivot][i]) < 1e-14:
            return None
        M[i], M[pivot] = M[pivot], M[i]
        for r in range(i + 1, n):
            factor = M[r][i] / M[i][i]
            for c in range(i, n + 1):
                M[r][c] -= factor * M[i][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n]
        for c in range(i + 1, n):
            s -= M[i][c] * x[c]
        x[i] = s / M[i][i]
    return x


def fit_poly(
    ms: Sequence[float],
    ivs: Sequence[float],
    degree: int = 2,
    weights: Optional[Sequence[float]] = None,
) -> Optional[list[float]]:
    """Vega-weighted least squares poly fit. Returns coefs c0..cd (low→high)."""
    n = len(ms)
    if n < degree + 1:
        return None
    if weights is None:
        weights = [1.0] * n
    p = degree + 1
    A = [[0.0] * p for _ in range(p)]
    b = [0.0] * p
    for k in range(n):
        w = weights[k]
        if w <= 0:
            continue
        x = ms[k]
        y = ivs[k]
        # x^0..x^{2d} cached
        powers = [1.0]
        for _ in range(2 * degree):
            powers.append(powers[-1] * x)
        for i in range(p):
            for j in range(p):
                A[i][j] += w * powers[i + j]
            b[i] += w * y * powers[i]
    return _solve_normal_eq(A, b)


def eval_poly(coefs: Sequence[float], m: float) -> float:
    s = 0.0
    p = 1.0
    for c in coefs:
        s += c * p
        p *= m
    return s


# ---------- SVI raw ----------
# w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))
# k = ln(K/F),  w = sigma_BS^2 * T


def svi_w(params: Sequence[float], k: float) -> float:
    a, b, rho, m, sig = params
    z = k - m
    return a + b * (rho * z + math.sqrt(z * z + sig * sig))


def _svi_loss(params: Sequence[float], ks: Sequence[float], ws: Sequence[float],
              wts: Sequence[float]) -> float:
    a, b, rho, m, sig = params
    pen = 0.0
    if b < 0:
        pen += 1e6 * (-b) ** 2
    if abs(rho) >= 1:
        pen += 1e6 * (abs(rho) - 1.0 + 1e-6) ** 2
    if sig <= 0:
        pen += 1e6 * (1e-3 - sig) ** 2
    s = 0.0
    for i in range(len(ks)):
        z = ks[i] - m
        wm = a + b * (rho * z + math.sqrt(z * z + sig * sig))
        s += wts[i] * (wm - ws[i]) ** 2
    return s + pen


def _nelder_mead(
    f: Callable[[Sequence[float]], float],
    x0: Sequence[float],
    *,
    step: Sequence[float],
    max_iter: int = 400,
    tol: float = 1e-8,
) -> list[float]:
    """Tiny Nelder-Mead. Stdlib-only. Sufficient for 5d SVI / 3d SABR."""
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        v = list(x0)
        v[i] = v[i] + step[i] if step[i] != 0 else v[i] + 0.05
        simplex.append(v)
    fvals = [f(v) for v in simplex]
    a_r, a_e, a_c, a_s = 1.0, 2.0, 0.5, 0.5
    for _ in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: fvals[i])
        simplex = [simplex[i] for i in order]
        fvals = [fvals[i] for i in order]
        if fvals[-1] - fvals[0] < tol:
            break
        # centroid of the n best
        centroid = [sum(simplex[i][d] for i in range(n)) / n for d in range(n)]
        worst = simplex[-1]
        x_r = [centroid[d] + a_r * (centroid[d] - worst[d]) for d in range(n)]
        f_r = f(x_r)
        if fvals[0] <= f_r < fvals[-2]:
            simplex[-1] = x_r
            fvals[-1] = f_r
            continue
        if f_r < fvals[0]:
            x_e = [centroid[d] + a_e * (x_r[d] - centroid[d]) for d in range(n)]
            f_e = f(x_e)
            if f_e < f_r:
                simplex[-1] = x_e
                fvals[-1] = f_e
            else:
                simplex[-1] = x_r
                fvals[-1] = f_r
            continue
        x_c = [centroid[d] + a_c * (worst[d] - centroid[d]) for d in range(n)]
        f_c = f(x_c)
        if f_c < fvals[-1]:
            simplex[-1] = x_c
            fvals[-1] = f_c
            continue
        # shrink
        best = simplex[0]
        for i in range(1, n + 1):
            simplex[i] = [best[d] + a_s * (simplex[i][d] - best[d]) for d in range(n)]
            fvals[i] = f(simplex[i])
    order = sorted(range(n + 1), key=lambda i: fvals[i])
    return simplex[order[0]]


def fit_svi_raw(
    ks: Sequence[float],
    ws: Sequence[float],
    weights: Optional[Sequence[float]] = None,
    init: Optional[Sequence[float]] = None,
) -> Optional[list[float]]:
    """Fit SVI raw to total-variance points. Returns (a, b, rho, m, sigma)."""
    n = len(ks)
    if n < 5:
        return None
    if weights is None:
        weights = [1.0] * n
    if init is None:
        w_mean = sum(weights[i] * ws[i] for i in range(n)) / max(1e-12, sum(weights))
        init = (max(1e-4, 0.5 * w_mean), 0.1, -0.3, 0.0, 0.1)
    f = lambda p: _svi_loss(p, ks, ws, weights)
    return _nelder_mead(f, init, step=(0.01, 0.05, 0.1, 0.05, 0.05), max_iter=600, tol=1e-10)


def svi_iv(params: Sequence[float], K: float, S: float, T: float) -> float:
    if T <= 0:
        return 0.0
    k = math.log(K / S)
    w = max(1e-10, svi_w(params, k))
    return math.sqrt(w / T)


# ---------- Rolling smile state ----------


class RollingSmile:
    """Online vega-weighted parabola refit; keep latest N (S, K, T, IV, vega) tuples.

    Cheap enough to call every tick for ≤8 strikes; refits at `refit_every` ticks.
    """

    def __init__(self, window_ticks: int = 5000, refit_every: int = 100,
                 vega_min: float = 5.0):
        self.window = window_ticks
        self.refit_every = refit_every
        self.vega_min = vega_min
        self._buf: list[tuple[int, float, float, float, float, float]] = []
        self._coefs: Optional[list[float]] = None
        self._last_refit: int = -10**9

    def observe(self, t: int, S: float, K: float, T: float, mid: float) -> None:
        iv = implied_vol_call(mid, S, K, T)
        if iv is None:
            return
        v = bs_call_vega(S, K, T, iv)
        if v < self.vega_min:
            return
        m = log_moneyness(S, K, T)
        self._buf.append((t, S, K, T, iv, v))
        # trim
        cut = t - self.window
        if self._buf and self._buf[0][0] < cut:
            self._buf = [r for r in self._buf if r[0] >= cut]

    def maybe_refit(self, t: int) -> None:
        if t - self._last_refit < self.refit_every:
            return
        if len(self._buf) < 8:
            return
        ms = [log_moneyness(r[1], r[2], r[3]) for r in self._buf]
        ivs = [r[4] for r in self._buf]
        wts = [r[5] for r in self._buf]
        coefs = fit_poly(ms, ivs, degree=2, weights=wts)
        if coefs is not None:
            self._coefs = coefs
            self._last_refit = t

    def sigma_hat(self, S: float, K: float, T: float, fallback: float = 0.234) -> float:
        if self._coefs is None:
            return fallback
        return max(0.05, eval_poly(self._coefs, log_moneyness(S, K, T)))


# ---------- Convenience: best bid/ask for an OrderDepth ----------


def best_bid_ask(od) -> tuple[Optional[int], Optional[int], int, int]:
    if not od or not od.buy_orders or not od.sell_orders:
        return None, None, 0, 0
    bid = max(od.buy_orders.keys())
    ask = min(od.sell_orders.keys())
    return bid, ask, od.buy_orders[bid], abs(od.sell_orders[ask])
