"""
Trend vs. Mean-Reversion Analysis
----------------------------------
Loads mid_price series per product from all available price CSV files and runs:
  1. Stationarity Tests   — ADF + KPSS
  2. Hurst Exponent       — Rescaled Range (R/S)
  3. Variance Ratio Test  — manual implementation (no arch dependency)
  4. Linear Regression    — price vs. time (R², t-stat of slope)

Usage:
    python TUTORIAL_ROUND_1/analysis_trend_vs_mr.py
    python TUTORIAL_ROUND_1/analysis_trend_vs_mr.py --product TOMATOES
    python TUTORIAL_ROUND_1/analysis_trend_vs_mr.py --csv path/to/prices.csv
"""

import argparse
import io
import math
import os
import statistics
import sys
from glob import glob

# Force UTF-8 output on Windows to support box-drawing characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_prices(csv_paths: list[str], product: str | None = None) -> dict[str, list[float]]:
    """
    Read one or more semicolon-delimited price CSVs.
    Returns {product: [mid_price, ...]} sorted by (day, timestamp).
    """
    rows: dict[str, list[tuple[int, int, float]]] = {}

    for path in csv_paths:
        with open(path, "r", encoding="utf-8") as fh:
            header = fh.readline().strip().split(";")
            try:
                idx_day   = header.index("day")
                idx_ts    = header.index("timestamp")
                idx_prod  = header.index("product")
                idx_mid   = header.index("mid_price")
            except ValueError as exc:
                print(f"[WARN] Skipping {path}: missing column ({exc})")
                continue

            for line in fh:
                parts = line.strip().split(";")
                if len(parts) <= max(idx_day, idx_ts, idx_prod, idx_mid):
                    continue
                prod = parts[idx_prod].strip()
                if product and prod != product:
                    continue
                try:
                    day = int(parts[idx_day])
                    ts  = int(parts[idx_ts])
                    mid = float(parts[idx_mid])
                except ValueError:
                    continue
                rows.setdefault(prod, []).append((day, ts, mid))

    # Sort and strip the sort keys
    return {
        prod: [v for _, _, v in sorted(vals)]
        for prod, vals in rows.items()
    }


def find_price_csvs(base_dir: str) -> list[str]:
    """Recursively locate all price CSV files under base_dir."""
    pattern = os.path.join(base_dir, "**", "prices_*.csv")
    return sorted(glob(pattern, recursive=True))


# ─────────────────────────────────────────────────────────────────────────────
# 2. Statistical Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)

def _std(xs: list[float], ddof: int = 0) -> float:
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - ddof)
    return math.sqrt(var)

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

def _autocorr(xs: list[float], lag: int) -> float:
    """Pearson autocorrelation at given lag."""
    n  = len(xs)
    m  = _mean(xs)
    y  = [x - m for x in xs]
    num   = sum(y[i] * y[i + lag] for i in range(n - lag))
    denom = sum(v ** 2 for v in y)
    return num / denom if denom > 1e-12 else 0.0

def _ols(x: list[float], y: list[float]) -> tuple[float, float, float, float]:
    """
    Simple OLS regression of y on x.
    Returns (intercept, slope, r_squared, t_stat_slope).
    """
    n = len(x)
    mx, my = _mean(x), _mean(y)
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    slope     = sxy / sxx
    intercept = my - slope * mx
    y_hat     = [intercept + slope * xi for xi in x]
    ss_res    = sum((yi - yhi) ** 2 for yi, yhi in zip(y, y_hat))
    ss_tot    = sum((yi - my)  ** 2 for yi in y)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    # t-stat = slope / SE(slope);  SE(slope) = sqrt(MSE / Sxx)
    mse     = ss_res / (n - 2) if n > 2 else float("nan")
    se_slope = math.sqrt(mse / sxx) if sxx > 1e-12 else float("nan")
    t_stat   = slope / se_slope if se_slope and not math.isnan(se_slope) else float("nan")
    return intercept, slope, r_squared, t_stat


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stationarity Tests
# ─────────────────────────────────────────────────────────────────────────────

def _adf_test(prices: list[float], max_lags: int = 10) -> tuple[float, float, str]:
    """
    Augmented Dickey-Fuller test (pure Python).

    Model: Δy_t = α + β·y_{t-1} + Σ γ_k·Δy_{t-k} + ε_t
    H0: β = 0  (unit root, non-stationary)
    H1: β < 0  (stationary)

    Returns (test_statistic, approx_p_value, interpretation).
    P-value approximated via MacKinnon (1994) critical values.
    """
    n = len(prices)
    # Determine optimal lag via AIC
    best_aic, best_lag = float("inf"), 1
    for lag in range(1, min(max_lags, n // 5) + 1):
        # Build regression matrices
        Y    = [prices[i] - prices[i - 1] for i in range(lag + 1, n)]
        X_lag = prices[lag:-1]
        lags_mat = [
            [prices[i - k] - prices[i - k - 1] for k in range(1, lag + 1)]
            for i in range(lag + 1, n)
        ]
        m = len(Y)
        # Pack X with intercept, lagged level, lagged diffs
        X = [[1.0, X_lag[i]] + lags_mat[i] for i in range(m)]
        try:
            beta = _ols_matrix(X, Y)
            resid = [Y[i] - sum(beta[j] * X[i][j] for j in range(len(beta))) for i in range(m)]
            sse   = sum(r ** 2 for r in resid)
            k     = len(beta)
            aic   = m * math.log(sse / m) + 2 * k if sse > 0 else float("inf")
            if aic < best_aic:
                best_aic, best_lag = aic, lag
        except Exception:
            continue

    lag = best_lag
    Y   = [prices[i] - prices[i - 1] for i in range(lag + 1, n)]
    X_lag = prices[lag:-1]
    lags_mat = [
        [prices[i - k] - prices[i - k - 1] for k in range(1, lag + 1)]
        for i in range(lag + 1, n)
    ]
    m = len(Y)
    X = [[1.0, X_lag[i]] + lags_mat[i] for i in range(m)]

    beta  = _ols_matrix(X, Y)
    resid = [Y[i] - sum(beta[j] * X[i][j] for j in range(len(beta))) for i in range(m)]
    sse   = sum(r ** 2 for r in resid)
    mse   = sse / (m - len(beta))

    # Variance of β[1] (coefficient on y_{t-1})
    # Var(β) = mse * (X'X)^{-1}
    k  = len(beta)
    XtX = [[sum(X[i][a] * X[i][b] for i in range(m)) for b in range(k)] for a in range(k)]
    try:
        XtX_inv = _invert_matrix(XtX)
        se_beta1 = math.sqrt(mse * XtX_inv[1][1])
        t_stat   = beta[1] / se_beta1
    except Exception:
        t_stat = float("nan")

    # MacKinnon (1994) approximate p-values for ADF (constant, no trend)
    # Critical values for T→∞: 1%=-3.4336, 5%=-2.8621, 10%=-2.5671
    # Approximate p from linear interpolation of the empirical distribution
    p_value = _adf_pvalue(t_stat, n)

    if p_value < 0.05:
        interpretation = "Stationary (reject H0)"
    elif p_value < 0.10:
        interpretation = "Weakly Stationary (marginal)"
    else:
        interpretation = "Non-Stationary (fail to reject H0)"

    return t_stat, p_value, interpretation


def _kpss_test(prices: list[float], lags: int | None = None) -> tuple[float, float, str]:
    """
    KPSS test for level-stationarity.
    H0: series is stationary.
    H1: series has a unit root.

    Returns (test_statistic, approx_p_value, interpretation).
    """
    n = len(prices)
    m = _mean(prices)
    resid = [p - m for p in prices]

    # Partial sums
    cumsum = []
    s = 0.0
    for r in resid:
        s += r
        cumsum.append(s)

    # Long-run variance (Newey-West with Bartlett kernel)
    if lags is None:
        lags = int(math.sqrt(n))
    sigma2 = sum(r ** 2 for r in resid) / n
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1)
        cov    = sum(resid[i] * resid[i - lag] for i in range(lag, n)) / n
        sigma2 += 2 * weight * cov

    kpss_stat = sum(s ** 2 for s in cumsum) / (n ** 2 * sigma2)

    # Approximate p-value: critical values (level, from Kwiatkowski et al. 1992)
    # 10%=0.347, 5%=0.463, 2.5%=0.574, 1%=0.739
    if kpss_stat > 0.739:
        p_value = 0.01
    elif kpss_stat > 0.574:
        p_value = 0.025
    elif kpss_stat > 0.463:
        p_value = 0.05
    elif kpss_stat > 0.347:
        p_value = 0.10
    else:
        p_value = 0.20   # > 10%: clearly stationary

    if p_value <= 0.05:
        interpretation = "Non-Stationary (reject H0 — series is NOT level-stationary)"
    else:
        interpretation = "Stationary (fail to reject H0)"

    return kpss_stat, p_value, interpretation


# ─────────────────────────────────────────────────────────────────────────────
# 4. Hurst Exponent (Rescaled Range R/S)
# ─────────────────────────────────────────────────────────────────────────────

def hurst_exponent(prices: list[float], min_window: int = 10) -> tuple[float, str]:
    """
    Hurst Exponent via Rescaled Range (R/S) analysis.
    H < 0.45 → Mean-reverting
    0.45 ≤ H ≤ 0.55 → Random walk (Brownian motion)
    H > 0.55 → Trending / persistent
    """
    n = len(prices)
    # Use log of price to work with returns
    log_prices = [math.log(p) for p in prices if p > 0]
    returns    = [log_prices[i] - log_prices[i - 1] for i in range(1, len(log_prices))]
    m = len(returns)

    windows: list[int] = []
    rs_vals: list[float] = []

    window = min_window
    while window <= m // 2:
        rs_list = []
        for start in range(0, m - window + 1, window):
            chunk = returns[start:start + window]
            mean_c = _mean(chunk)
            devs   = [c - mean_c for c in chunk]
            cumdev = []
            s = 0.0
            for d in devs:
                s += d
                cumdev.append(s)
            R = max(cumdev) - min(cumdev)
            S = _std(chunk)
            if S > 1e-12:
                rs_list.append(R / S)
        if rs_list:
            windows.append(window)
            rs_vals.append(_mean(rs_list))
        window = int(window * 1.5) + 1

    if len(windows) < 3:
        return float("nan"), "Insufficient data"

    log_n  = [math.log(w) for w in windows]
    log_rs = [math.log(r) for r in rs_vals]

    _, H, r2, _ = _ols(log_n, log_rs)

    if H < 0.45:
        label = "Mean-Reverting (H < 0.45)"
    elif H > 0.55:
        label = "Trending / Persistent (H > 0.55)"
    else:
        label = "Random Walk (0.45 ≤ H ≤ 0.55)"

    return H, label


# ─────────────────────────────────────────────────────────────────────────────
# 5. Variance Ratio Test (Lo-MacKinlay)
# ─────────────────────────────────────────────────────────────────────────────

def variance_ratio_test(
    prices: list[float], lags: list[int] | None = None
) -> list[tuple[int, float, float, str]]:
    """
    Lo-MacKinlay (1988) Variance Ratio Test.
    Under a random walk: Var(r_k) / k·Var(r_1) = 1.

    Returns list of (lag, VR, z_stat, interpretation) for each lag.
    """
    if lags is None:
        lags = [2, 4, 8, 16]

    log_p = [math.log(p) for p in prices if p > 0]
    n     = len(log_p)
    r1    = [log_p[i] - log_p[i - 1] for i in range(1, n)]
    mu    = _mean(r1)
    T     = len(r1)

    var1 = sum((r - mu) ** 2 for r in r1) / (T - 1)

    results = []
    for q in lags:
        rq     = [log_p[i] - log_p[i - q] for i in range(q, n)]
        var_q  = sum((r - q * mu) ** 2 for r in rq) / (len(rq) * (q - 1))
        if var1 < 1e-15:
            continue
        vr = var_q / var1

        # Asymptotic variance of VR under homoskedasticity
        # δ(q) = 2(2q-1)(q-1) / (3qT)
        delta = 2 * (2 * q - 1) * (q - 1) / (3 * q * T)
        z     = (vr - 1) / math.sqrt(delta) if delta > 0 else float("nan")

        if abs(z) > 2.576:
            p_approx = "< 0.01"
            verdict  = "Reject Random Walk (p<0.01)"
        elif abs(z) > 1.960:
            p_approx = "< 0.05"
            verdict  = "Reject Random Walk (p<0.05)"
        elif abs(z) > 1.645:
            p_approx = "< 0.10"
            verdict  = "Reject Random Walk (p<0.10)"
        else:
            p_approx = "> 0.10"
            verdict  = "Cannot Reject Random Walk"

        if not math.isnan(z):
            if vr > 1:
                direction = " → Positive autocorrelation (Trending)"
            else:
                direction = " → Negative autocorrelation (Mean-Reverting)"
            verdict += direction

        results.append((q, vr, z, p_approx, verdict))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 6. Linear Regression (price vs. time)
# ─────────────────────────────────────────────────────────────────────────────

def trend_regression(prices: list[float]) -> dict:
    """
    OLS regression of price on a time index [0, 1, ..., n-1].
    Returns a dict with slope, intercept, r_squared, t_stat, interpretation.
    """
    n  = len(prices)
    t  = list(range(n))
    intercept, slope, r2, t_stat = _ols(t, prices)

    if abs(t_stat) > 2.576:
        significance = "highly significant (p < 0.01)"
    elif abs(t_stat) > 1.960:
        significance = "significant (p < 0.05)"
    elif abs(t_stat) > 1.645:
        significance = "marginally significant (p < 0.10)"
    else:
        significance = "not significant (p > 0.10)"

    trend_direction = "upward" if slope > 0 else "downward"
    if abs(t_stat) < 1.645 or r2 < 0.01:
        interpretation = "No meaningful linear trend detected"
    else:
        interpretation = f"Linear {trend_direction} trend, {significance} (R²={r2:.4f})"

    return {
        "intercept":      intercept,
        "slope":          slope,
        "r_squared":      r2,
        "t_stat_slope":   t_stat,
        "significance":   significance,
        "interpretation": interpretation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Matrix helpers (no numpy)
# ─────────────────────────────────────────────────────────────────────────────

def _ols_matrix(X: list[list[float]], y: list[float]) -> list[float]:
    """Solve OLS via normal equations: β = (X'X)^{-1} X'y."""
    k = len(X[0])
    n = len(y)
    # X'X
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    # X'y
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    # Solve via Gaussian elimination
    return _solve(XtX, Xty)


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve Ax = b via Gaussian elimination with partial pivoting."""
    n = len(b)
    # Augmented matrix
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        # Pivot
        max_row = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[max_row] = M[max_row], M[col]
        if abs(M[col][col]) < 1e-14:
            raise ValueError("Singular matrix")
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            M[row] = [M[row][j] - factor * M[col][j] for j in range(n + 1)]
    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]
    return x


def _invert_matrix(A: list[list[float]]) -> list[list[float]]:
    """Invert a square matrix via Gaussian elimination."""
    n = len(A)
    # Augmented with identity
    M = [A[i][:] + [float(i == j) for j in range(n)] for i in range(n)]
    for col in range(n):
        max_row = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[max_row] = M[max_row], M[col]
        if abs(M[col][col]) < 1e-14:
            raise ValueError("Singular matrix")
        pivot = M[col][col]
        M[col] = [v / pivot for v in M[col]]
        for row in range(n):
            if row == col:
                continue
            factor = M[row][col]
            M[row] = [M[row][j] - factor * M[col][j] for j in range(2 * n)]
    return [row[n:] for row in M]


def _adf_pvalue(t_stat: float, n: int) -> float:
    """
    Approximate ADF p-value using MacKinnon (1994) response surface.
    For the no-trend, with-intercept case.
    """
    # MacKinnon critical values at 1%, 5%, 10% for T→∞
    # Fitted as: cv(p) = cv_inf + c1/T + c2/T²
    cv_params = {
        0.01:  (-3.4336, -5.999, -29.25),
        0.05:  (-2.8621, -2.738, -8.36),
        0.10:  (-2.5671, -1.438, -4.48),
    }
    # Compute critical values at this sample size
    cvs = {}
    for p, (cv_inf, c1, c2) in cv_params.items():
        cvs[p] = cv_inf + c1 / n + c2 / (n ** 2)

    if t_stat < cvs[0.01]:
        return 0.005
    elif t_stat < cvs[0.05]:
        return 0.025
    elif t_stat < cvs[0.10]:
        return 0.075
    else:
        # Linearly extrapolate between 10% and a rough 20% critical value
        cv20 = -2.20  # rough approximation
        if t_stat < cv20:
            # interpolate between 0.10 and 0.20
            frac = (t_stat - cvs[0.10]) / (cv20 - cvs[0.10])
            return 0.10 + 0.10 * frac
        return min(0.99, 0.20 + (t_stat - cv20) * 0.08)


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

SEPARATOR = "=" * 70

def run_analysis(product: str, prices: list[float]) -> None:
    n = len(prices)
    print(f"\n{SEPARATOR}")
    print(f"  PRODUCT: {product}   |   n = {n} observations")
    print(f"  Price range: [{min(prices):.2f}, {max(prices):.2f}]   "
          f"mean={_mean(prices):.2f}   std={_std(prices):.2f}")
    print(SEPARATOR)

    if n < 30:
        print("  [SKIP] Too few observations for reliable tests (need ≥ 30)")
        return

    # ── 1. Stationarity ──────────────────────────────────────────────────────
    print("\n── 1. STATIONARITY TESTS ──────────────────────────────────────────")

    adf_stat, adf_p, adf_interp = _adf_test(prices)
    print(f"  ADF  Test Statistic : {adf_stat:>10.4f}")
    print(f"  ADF  p-value (approx): {adf_p:>9.4f}")
    print(f"  ADF  Interpretation : {adf_interp}")

    kpss_stat, kpss_p, kpss_interp = _kpss_test(prices)
    print(f"\n  KPSS Test Statistic : {kpss_stat:>10.4f}")
    print(f"  KPSS p-value (bound) : {kpss_p:>9.4f}")
    print(f"  KPSS Interpretation : {kpss_interp}")

    # Combined verdict
    adf_stationary  = adf_p  < 0.05
    kpss_stationary = kpss_p > 0.05
    print("\n  Combined verdict:")
    if adf_stationary and kpss_stationary:
        print("  → STATIONARY  (both ADF rejects unit root AND KPSS cannot reject stationarity)")
    elif not adf_stationary and not kpss_stationary:
        print("  → NON-STATIONARY  (both tests agree series has a unit root)")
    elif adf_stationary and not kpss_stationary:
        print("  → TREND-STATIONARY  (ADF rejects unit root but KPSS rejects level-stationarity)")
        print("     Consider differencing or de-trending.")
    else:
        print("  → AMBIGUOUS  (tests disagree — may need fractional integration or structural break analysis)")

    # ── 2. Hurst Exponent ────────────────────────────────────────────────────
    print("\n── 2. HURST EXPONENT (R/S Analysis) ───────────────────────────────")
    H, h_label = hurst_exponent(prices)
    print(f"  H = {H:.4f}")
    print(f"  Interpretation : {h_label}")
    print(f"  Confidence note: R/S estimates are biased upward for short series (< 500 obs)")

    # ── 3. Variance Ratio Test ───────────────────────────────────────────────
    print("\n── 3. VARIANCE RATIO TEST (Lo-MacKinlay) ───────────────────────────")
    vr_results = variance_ratio_test(prices)
    print(f"  {'Lag q':>6}  {'VR':>8}  {'Z-stat':>8}  {'p-value':>8}  Verdict")
    print(f"  {'──────':>6}  {'────────':>8}  {'────────':>8}  {'────────':>8}  ─────────────────────────────────")
    for q, vr, z, p_approx, verdict in vr_results:
        print(f"  {q:>6}  {vr:>8.4f}  {z:>8.3f}  {p_approx:>8}  {verdict}")

    # ── 4. Trend Regression ──────────────────────────────────────────────────
    print("\n── 4. LINEAR TREND REGRESSION (price ~ time) ──────────────────────")
    reg = trend_regression(prices)
    print(f"  Slope           : {reg['slope']:>12.6f}  per tick")
    print(f"  Intercept       : {reg['intercept']:>12.4f}")
    print(f"  R²              : {reg['r_squared']:>12.4f}")
    print(f"  t-stat (slope)  : {reg['t_stat_slope']:>12.4f}")
    print(f"  Significance    : {reg['significance']}")
    print(f"  Interpretation  : {reg['interpretation']}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n── SUMMARY ─────────────────────────────────────────────────────────")
    signals = []
    if adf_stationary and kpss_stationary:
        signals.append("Stationary (ADF+KPSS)")
    if H < 0.45:
        signals.append("Mean-Reverting (H)")
    elif H > 0.55:
        signals.append("Trending (H)")
    vr_rejections = [(q, vr) for q, vr, z, _, v in vr_results if "Reject" in v]
    if vr_rejections:
        directions = ["↑ Trend" if vr > 1 else "↓ MR" for _, vr in vr_rejections]
        signals.append(f"VR rejects RW at lags {[q for q, _ in vr_rejections]} ({', '.join(directions)})")
    if abs(reg["t_stat_slope"]) > 1.96:
        signals.append(f"Significant linear trend (R²={reg['r_squared']:.4f})")

    if signals:
        print("  Key findings: " + " | ".join(signals))
    else:
        print("  Key findings: No strong evidence of either trending or mean-reversion → likely a Random Walk")

    # Trading recommendation
    print("\n  Trading implication:")
    mr_signals = sum([
        H < 0.45,
        adf_stationary and kpss_stationary,
        any(vr < 1 and "Reject" in v for _, vr, _, _, v in vr_results),
    ])
    trend_signals = sum([
        H > 0.55,
        abs(reg["t_stat_slope"]) > 1.96 and reg["r_squared"] > 0.05,
        any(vr > 1 and "Reject" in v for _, vr, _, _, v in vr_results),
    ])
    if mr_signals >= 2 and mr_signals > trend_signals:
        print("  → MEAN-REVERSION strategy recommended (e.g. Z-score entry/exit)")
    elif trend_signals >= 2 and trend_signals > mr_signals:
        print("  → TREND-FOLLOWING strategy recommended (e.g. momentum / breakout)")
    else:
        print("  → MARKET-MAKING (random walk) strategy recommended (e.g. WallMid + inventory skew)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Trend vs. Mean-Reversion Analysis")
    parser.add_argument("--csv",     nargs="+", help="Path(s) to price CSV file(s)")
    parser.add_argument("--product", help="Filter to a single product (e.g. TOMATOES)")
    parser.add_argument("--dir",     default=None,
                        help="Directory to recursively search for price CSVs (default: TUTORIAL_ROUND_1)")
    args = parser.parse_args()

    if args.csv:
        csv_paths = args.csv
    else:
        search_dir = args.dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__))
        )
        csv_paths = find_price_csvs(search_dir)
        if not csv_paths:
            print(f"[ERROR] No price CSV files found under {search_dir}")
            sys.exit(1)
        print(f"Found {len(csv_paths)} price file(s):")
        for p in csv_paths:
            print(f"  {p}")

    data = load_prices(csv_paths, product=args.product)

    if not data:
        print("[ERROR] No data loaded. Check --product filter or CSV paths.")
        sys.exit(1)

    for product, prices in sorted(data.items()):
        run_analysis(product, prices)

    print(f"\n{SEPARATOR}")
    print("  Analysis complete.")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
