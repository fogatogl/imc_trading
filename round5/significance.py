"""Statistical-strength helpers for round-5 archetype classification.

The classifier already gates on effect-size thresholds (e.g. ``|IC| > 0.04``).
This module adds the significance layer: HAC-adjusted (Newey-West) t-stats
on signal/forward-return regressions, Bartlett ACF p-values, VR z-stat →
p-value, and a multiple-testing correction (Benjamini-Hochberg FDR for the
24 IC cells per product).

Why both effect-size and significance?
  * 30 000 ticks per product makes the noise floor for IC ≈ 1/√30 000 ≈ 0.006.
    Any |IC| > 0.02 is "significant" naively, so significance alone is too
    permissive.
  * Forward returns at horizon h are nearly fully overlapping (consecutive
    pairs share h-1 ticks). Naive t-stats overstate significance by ~√h.
    ``signal_ic_table`` calls ``hac_ic_t`` with ``maxlag=h`` so reported
    p-values reflect the true effective sample size.
  * 6 signals × 4 horizons = 24 tests/product. Without correction we expect
    ≈ 1 false positive per product at α=0.05; BH-FDR keeps the false-
    discovery rate at α.

Functions in this module are stateless and side-effect-free.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Pearson correlation (IC) significance
# ---------------------------------------------------------------------------

def ic_t_stat(ic: float, n: int) -> tuple[float, float]:
    """Naive Pearson correlation t-test. Returns (t, two-sided p)."""
    if not np.isfinite(ic) or n is None or n <= 2:
        return float("nan"), float("nan")
    if abs(ic) >= 1.0:
        return float("inf") * np.sign(ic), 0.0
    t = float(ic * np.sqrt((n - 2) / (1 - ic * ic)))
    p = float(2 * (1 - stats.t.cdf(abs(t), df=n - 2)))
    return t, p


def hac_ic_t(
    signal: pd.Series, fwd_ret: pd.Series, hac_lag: Optional[int] = None
) -> tuple[float, float, float, int]:
    """HAC-adjusted IC test (Newey-West). Returns (ic, t_hac, p_hac, n).

    HAC accounts for autocorrelated residuals. For ICs measured on a price
    return series with horizon h, residuals are autocorrelated up to ~h
    lags; the rule-of-thumb default is ``hac_lag ≈ 4·(n/100)^(2/9)`` but we
    floor at the horizon to be safe.
    """
    s = pd.concat([signal, fwd_ret], axis=1).dropna()
    if len(s) < 30:
        return float("nan"), float("nan"), float("nan"), int(len(s))
    x = s.iloc[:, 0].values
    y = s.iloc[:, 1].values
    n = len(x)
    if x.std() == 0 or y.std() == 0:
        return float("nan"), float("nan"), float("nan"), n
    ic = float(np.corrcoef(x, y)[0, 1])
    if hac_lag is None:
        hac_lag = max(1, int(np.ceil(4 * (n / 100) ** (2 / 9))))
    try:
        import statsmodels.api as sm
        Xc = sm.add_constant(x.astype(float))
        model = sm.OLS(y, Xc).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lag})
        beta = float(model.params[1])
        se = float(model.bse[1])
        if se <= 0:
            return ic, float("nan"), float("nan"), n
        # The t-stat for beta in the regression y = α + β·x is the same as
        # the test statistic for ρ when y, x are demeaned (proportional).
        t = beta / se
        p = float(2 * (1 - stats.norm.cdf(abs(t))))
        return ic, float(t), p, n
    except Exception:
        # Fall back to naive t-test if statsmodels HAC fails.
        t, p = ic_t_stat(ic, n)
        return ic, t, p, n


# ---------------------------------------------------------------------------
# Other test statistics
# ---------------------------------------------------------------------------

def bartlett_acf_p(rho: float, n: int) -> float:
    """Bartlett's approximation for ACF significance (lag k ≥ 1).

    Under H0 ρ_k = 0,  ρ̂_k ~ N(0, 1/n) approximately.
    """
    if not np.isfinite(rho) or n is None or n <= 2:
        return float("nan")
    z = rho * np.sqrt(n)
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def vr_p_value(z: float) -> float:
    """Two-sided p-value from the Lo-MacKinlay VR z-statistic."""
    if not np.isfinite(z):
        return float("nan")
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def hurst_p_value(H: float, r2: float, n_lags: int) -> float:
    """Heuristic two-sided test of H == 0.5 from log-log R/S regression.

    SE ≈ sqrt((1 − R²) / max(n_lags − 2, 1)). Conservative; the regression
    uses ``n_lags`` aggregated R/S points, not raw ticks.
    """
    if not np.isfinite(H) or not np.isfinite(r2) or n_lags is None or n_lags < 3:
        return float("nan")
    se = float(np.sqrt(max(0.0, (1 - r2) / max(1, n_lags - 2))))
    if se <= 0:
        return 1.0
    z = (H - 0.5) / se
    return float(2 * (1 - stats.norm.cdf(abs(z))))


# ---------------------------------------------------------------------------
# Multiple testing
# ---------------------------------------------------------------------------

def bh_fdr(pvalues: Sequence[float], alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg FDR. Returns boolean mask of rejected hypotheses
    at family-wise FDR ``alpha``.
    """
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    if n == 0:
        return np.array([], dtype=bool)
    order = np.argsort(p)
    ranked = p[order]
    thresh = (np.arange(1, n + 1) / n) * alpha
    passing = ranked <= thresh
    if not passing.any():
        out = np.zeros(n, dtype=bool)
        return out
    last = np.where(passing)[0].max()
    cutoff = ranked[last]
    return p <= cutoff


def bonferroni_alpha(alpha: float, n_tests: int) -> float:
    return alpha / max(1, n_tests)


# ---------------------------------------------------------------------------
# Augment ic_long with significance columns
# ---------------------------------------------------------------------------

def add_significance_columns(ic_long: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """Adds Benjamini-Hochberg FDR `significant` boolean column to the
    long-form IC table emitted by ``signal_ic_table``.

    ``signal_ic_table`` already populates HAC-adjusted ``t_h{h}`` / ``p_h{h}``
    columns. This function only adds the multiple-testing layer: per-product
    BH-FDR across the 6 signals × 4 horizons = 24 cells. As a safety net, if
    the HAC columns are missing (legacy frames), it falls back to the naive
    t-test on ``ic_h{h}`` and ``n_h{h}``.
    """
    if ic_long.empty:
        return ic_long.copy()
    out = ic_long.copy()
    horizons = [int(c.replace("ic_h", "")) for c in out.columns if c.startswith("ic_h")]
    horizons = sorted(set(horizons))

    # Backfill t/p only for cells where HAC didn't write them (older frames).
    for h in horizons:
        ic_col, n_col, t_col, p_col = f"ic_h{h}", f"n_h{h}", f"t_h{h}", f"p_h{h}"
        if ic_col not in out.columns:
            continue
        if t_col not in out.columns:
            out[t_col] = np.nan
        if p_col not in out.columns:
            out[p_col] = np.nan
        if n_col not in out.columns:
            out[n_col] = 0
        missing = out[p_col].isna() & out[ic_col].notna()
        if missing.any():
            for idx in out.index[missing]:
                t, p = ic_t_stat(out.at[idx, ic_col], int(out.at[idx, n_col] or 0))
                out.at[idx, t_col] = t
                out.at[idx, p_col] = p

    # FDR per product, across the long-form (signal × horizon) cells.
    out["significant"] = False
    if "product" in out.columns:
        for product, sub in out.groupby("product"):
            ps: list[float] = []
            keys: list[tuple] = []
            for h in horizons:
                pcol = f"p_h{h}"
                if pcol not in sub.columns:
                    continue
                for idx, val in sub[pcol].items():
                    if pd.notna(val):
                        ps.append(float(val))
                        keys.append((idx, h))
            if not ps:
                continue
            mask = bh_fdr(ps, alpha=alpha)
            for (idx, h), passing in zip(keys, mask):
                if passing:
                    out.at[idx, "significant"] = True
    return out


def best_significant_ic(
    ic_for_product: Optional[pd.DataFrame],
    signal: Optional[str] = None,
    horizons: Optional[Iterable[int]] = None,
    alpha: float = 0.05,
) -> dict:
    """For one product's IC sub-frame, return the (signal, horizon) with
    highest |IC| among FDR-passing cells. If none pass, returns the best
    raw |IC| with ``passes_fdr=False``.

    Returns dict with keys: ic, signal, horizon, n, t, p, passes_fdr.
    """
    out = {"ic": float("nan"), "signal": None, "horizon": None,
           "n": 0, "t": float("nan"), "p": float("nan"), "passes_fdr": False}
    if ic_for_product is None or ic_for_product.empty:
        return out
    if "significant" not in ic_for_product.columns:
        ic_for_product = add_significance_columns(ic_for_product, alpha=alpha)
    sub = ic_for_product.copy()
    if signal is not None:
        sub = sub[sub["signal"] == signal]
    if sub.empty:
        return out

    horizon_cols = [int(c.replace("ic_h", "")) for c in sub.columns if c.startswith("ic_h")]
    if horizons is not None:
        horizon_cols = [h for h in horizon_cols if h in horizons]

    candidates = []
    for _, row in sub.iterrows():
        for h in horizon_cols:
            ic = row.get(f"ic_h{h}")
            if pd.isna(ic):
                continue
            n = int(row.get(f"n_h{h}", 0) or 0)
            p = row.get(f"p_h{h}", float("nan"))
            t = row.get(f"t_h{h}", float("nan"))
            candidates.append({
                "ic": float(ic), "signal": row.get("signal", "?"), "horizon": h,
                "n": n, "t": t, "p": p,
                "passes_fdr": bool(row.get("significant", False)),
            })
    if not candidates:
        return out
    fdr_pass = [c for c in candidates if c["passes_fdr"]]
    pool = fdr_pass if fdr_pass else candidates
    best = max(pool, key=lambda c: abs(c["ic"]))
    return best
