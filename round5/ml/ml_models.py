"""ML model wrappers, CV splitters, tradeability gate, PnL simulator.

All gates honour the round-5 memory guardrails:
  - per-day positive (no aggregate-across-days positive selection)
  - live-haircut applied to predicted edge before tradeability test
  - regime-conditioned PnL check (no PANEL-style trend-failure mode)

Public API:
    cv_block_purged(df, ...)      -> iterator of (label, train_mask, test_mask)
    fit_predict(model_name, ...)  -> (y_pred_test, fitted_model, info)
    simulate_pnl(...)             -> pd.Series of per-tick PnL contribution
    tradeability_gate(...)        -> dict with pass/fail per condition
"""
from __future__ import annotations

from typing import Iterator, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, Ridge
from sklearn.ensemble import RandomForestRegressor

try:
    import lightgbm as lgb
    _HAS_LGBM = True
except ImportError:  # let the CLI report missing dep at runtime
    _HAS_LGBM = False


# ---------------------------------------------------------------------------
# CV splitters
# ---------------------------------------------------------------------------

def cv_block_purged(
    df: pd.DataFrame,
    n_blocks_per_day: int = 5,
    embargo_ticks: int = 200,
) -> Iterator[Tuple[str, pd.Series, pd.Series]]:
    """Block-purged intra-day k-fold splitter.

    Cuts each day's unique-timestamp axis into ``n_blocks_per_day`` contiguous
    blocks. For each block yields ``(label, train_mask, test_mask)`` where:
      - ``test_mask`` selects rows whose ``timestamp`` falls inside the block
        (all products simultaneously — a tick is one fold-row regardless of
        symbol).
      - ``train_mask`` selects every other row, EXCEPT same-day rows lying
        within ``embargo_ticks`` (counted in unique timestamps) of the test
        block. Other-day rows are always train (no inter-day leakage exists by
        construction in research_lib).

    With round-5 defaults (3 days × 5 blocks) this yields 15 folds, each test
    block ~2,000 ticks wide. Replaces the prior single-D4 walk-forward fold,
    giving 15 independent test windows for IC / PnL aggregation.
    """
    days = sorted(df["day"].unique())
    for d in days:
        day_mask = df["day"] == d
        unique_ts = np.sort(df.loc[day_mask, "timestamp"].unique())
        n_ts = len(unique_ts)
        if n_ts == 0:
            continue
        edges = np.linspace(0, n_ts, n_blocks_per_day + 1).astype(int)
        for b in range(n_blocks_per_day):
            i_lo, i_hi = edges[b], edges[b + 1]
            if i_hi <= i_lo:
                continue
            lo_ts = unique_ts[i_lo]
            hi_ts = unique_ts[i_hi - 1]
            emb_lo_idx = max(0, i_lo - embargo_ticks)
            emb_hi_idx = min(n_ts - 1, i_hi - 1 + embargo_ticks)
            emb_lo_ts = unique_ts[emb_lo_idx]
            emb_hi_ts = unique_ts[emb_hi_idx]
            test_mask = day_mask & (df["timestamp"] >= lo_ts) & (df["timestamp"] <= hi_ts)
            embargo_mask = day_mask & (df["timestamp"] >= emb_lo_ts) & (df["timestamp"] <= emb_hi_ts)
            train_mask = ~embargo_mask  # excludes test block + embargo halos; other-day rows stay True
            yield (f"D{int(d)}_b{b}", train_mask, test_mask)


def apply_vol_gate(df: pd.DataFrame, train_mask: pd.Series, quintile: int) -> pd.Series:
    """Drop training rows above the `quintile/5` percentile of `std_500`.

    `quintile=4` keeps the bottom 80% (drops top quintile). `quintile=5` is a
    no-op. Test rows are NOT filtered — the gate only quiets training so the
    model fits low-vol microstructure rather than the trend-spike tail that
    drove the PANEL D5 −3,155 inversion.
    """
    if quintile is None or quintile >= 5 or quintile <= 0:
        return train_mask
    if "std_500" not in df.columns:
        return train_mask
    s500 = df["std_500"].astype(float)
    valid = s500.notna() & train_mask
    if valid.sum() < 1000:
        return train_mask
    threshold = s500[valid].quantile(quintile / 5.0)
    keep = (s500 <= threshold).fillna(False)
    return train_mask & keep


# ---------------------------------------------------------------------------
# Model wrappers
# ---------------------------------------------------------------------------

def _fit_ridge(X_tr, y_tr, alpha=1.0):
    m = Ridge(alpha=alpha, random_state=0)
    m.fit(X_tr, np.asarray(y_tr))
    return m


def _fit_lasso(X_tr, y_tr, alpha=1e-4):
    m = Lasso(alpha=alpha, random_state=0, max_iter=5000)
    m.fit(X_tr, np.asarray(y_tr))
    return m


def _fit_lgbm(X_tr, y_tr, params=None):
    if not _HAS_LGBM:
        raise ImportError("lightgbm not installed; run pip install -r requirements_ml.txt")
    p = dict(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=-1,
        num_leaves=31,
        min_data_in_leaf=200,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=0,
        verbose=-1,
    )
    if params:
        p.update(params)
    m = lgb.LGBMRegressor(**p)
    # Use DataFrame if available so feature_names_in_ aligns with predict-side DataFrame.
    m.fit(X_tr, np.asarray(y_tr))
    return m


def _fit_rf(X_tr, y_tr, params=None):
    p = dict(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=200,
        n_jobs=-1,
        random_state=0,
    )
    if params:
        p.update(params)
    m = RandomForestRegressor(**p)
    m.fit(X_tr, np.asarray(y_tr))
    return m


_MODEL_FITTERS = {
    "ridge": _fit_ridge,
    "lasso": _fit_lasso,
    "lgbm": _fit_lgbm,
    "rf": _fit_rf,
}


def available_models() -> list[str]:
    return [m for m in _MODEL_FITTERS if m != "lgbm" or _HAS_LGBM]


def fit_predict(
    model_name: str,
    X_tr: pd.DataFrame,
    y_tr: pd.Series,
    X_te: pd.DataFrame,
    **kwargs,
) -> Tuple[np.ndarray, object]:
    fitter = _MODEL_FITTERS[model_name]
    # Pass DataFrames through so feature_names stay consistent between fit/predict.
    model = fitter(X_tr, y_tr, **kwargs)
    y_pred = model.predict(X_te)
    return np.asarray(y_pred), model


def feature_importance(model_name: str, model, feature_names: list[str]) -> pd.DataFrame:
    if model_name == "lgbm":
        gain = model.booster_.feature_importance(importance_type="gain")
        return pd.DataFrame({"feature": feature_names, "importance": gain}).sort_values(
            "importance", ascending=False
        )
    if model_name in ("ridge", "lasso"):
        coef = np.asarray(model.coef_).ravel()
        # std-coef approximation: |coef| (features already on similar scale after lag construction)
        return pd.DataFrame({"feature": feature_names, "importance": np.abs(coef)}).sort_values(
            "importance", ascending=False
        )
    if model_name == "rf":
        imp = model.feature_importances_
        return pd.DataFrame({"feature": feature_names, "importance": imp}).sort_values(
            "importance", ascending=False
        )
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Diagnostics + simulator
# ---------------------------------------------------------------------------

def information_coefficient(y_pred: np.ndarray, y_true: np.ndarray) -> float:
    s = pd.Series(y_pred)
    t = pd.Series(y_true)
    mask = s.notna() & t.notna()
    if mask.sum() < 100:
        return float("nan")
    return float(s[mask].corr(t[mask]))


POSITION_LIMIT = 10  # round-5 hard cap, mirrors research_lib.POSITION_LIMIT


def simulate_pnl(
    df: pd.DataFrame,
    y_pred: np.ndarray,
    live_haircut: float,
    half_spread_buffer: float = 0.0,
    position_limit: int = POSITION_LIMIT,
) -> np.ndarray:
    """State-aware PnL simulator.

    Earlier sim (v1) charged a full round-trip spread on every signal tick AND
    summed per-tick fwd_h returns. Both legs were wrong: spread is paid only on
    |Δposition| (not every signal), and overlapping fwd_h windows triple-count
    the same forward return when the signal persists.

    v2 model: position evolves as a step function of the signal. At each tick,
    target_pos = ±position_limit if |edge| > half_spread + buffer, else 0.
    Day boundaries reset position to 0 (no overnight). PnL is mark-to-mid on
    the previously held position; cost is 0.5 × spread × |Δpos| each leg, paid
    once per position change.

    Returns per-tick PnL (mid-price units). Sum within a day for daily PnL.
    """
    edge = np.asarray(y_pred, dtype=float) * live_haircut
    spread = df["spread"].astype(float).values
    half_sp = 0.5 * spread
    threshold = half_sp + half_spread_buffer
    direction = np.sign(edge)
    target_pos = np.where(np.abs(edge) > threshold, direction * position_limit, 0.0)

    days = df["day"].astype(int).values
    mid = df["mid"].astype(float).values
    n = len(df)
    pnl = np.zeros(n)

    # Process each day independently (force flat at start and end of day).
    for d in np.unique(days):
        idx = np.where(days == d)[0]
        if len(idx) < 2:
            continue
        pos = target_pos[idx].copy()
        pos[0] = 0.0
        pos[-1] = 0.0

        sub_mid = mid[idx]
        sub_sp = spread[idx]

        position_held = np.concatenate([[0.0], pos[:-1]])  # held from t-1 → t
        mid_diff = np.concatenate([[0.0], np.diff(sub_mid)])
        gross = position_held * mid_diff

        delta = np.concatenate([[pos[0]], np.diff(pos)])  # entry/exit moves
        cost = 0.5 * sub_sp * np.abs(delta)

        pnl[idx] = gross - cost

    return np.where(np.isnan(pnl), 0.0, pnl)


def tradeability_gate(
    df_test: pd.DataFrame,
    y_pred: np.ndarray,
    horizon: int,
    live_haircut: float,
    edge_clear_min_frac: float = 0.15,
) -> dict:
    """Apply the four-condition gate to a single fold.

    df_test must contain columns: day, mid, spread, microprice_dev,
    fwd_<horizon>, std_500 (for regime quintiles).
    """
    half_sp = 0.5 * df_test["spread"].astype(float).values
    edge = y_pred * live_haircut
    fwd = df_test[f"fwd_{horizon}"].astype(float).values

    # --- Condition 1: predicted-edge dominance (post-haircut) ---
    valid = ~np.isnan(edge) & ~np.isnan(half_sp)
    if valid.sum() == 0:
        return {"passed": False, "reason": "no valid predictions"}
    median_excess = float(np.nanmedian(np.abs(edge[valid]) - half_sp[valid]))
    frac_clear = float(np.mean(np.abs(edge[valid]) > half_sp[valid]))
    cond1 = (median_excess > 0) and (frac_clear >= edge_clear_min_frac)

    # --- Condition 2: per-day positive IC ---
    per_day_ic = {}
    days = sorted(df_test["day"].unique())
    for d in days:
        mask = (df_test["day"] == d).values & valid & ~np.isnan(fwd)
        if mask.sum() < 200:
            per_day_ic[int(d)] = float("nan")
            continue
        per_day_ic[int(d)] = float(pd.Series(y_pred[mask]).corr(pd.Series(fwd[mask])))
    cond2 = all(v is not None and not np.isnan(v) and v > 0 for v in per_day_ic.values())

    # --- Condition 3: per-day positive simulated PnL ---
    pnl = simulate_pnl(df_test, y_pred, live_haircut)
    per_day_pnl = {}
    for d in days:
        mask = (df_test["day"] == d).values
        per_day_pnl[int(d)] = float(np.nansum(pnl[mask]))
    cond3 = all(v > 0 for v in per_day_pnl.values())

    # --- Condition 4: trend-defense (PnL by |std_500| quintile) ---
    cond4 = True
    quintile_pnl: dict[int, float] = {}
    if "std_500" in df_test.columns:
        s500 = df_test["std_500"].astype(float).values
        v_std = ~np.isnan(s500)
        if v_std.sum() >= 1000:
            quintiles = pd.qcut(pd.Series(s500[v_std]), 5, labels=False, duplicates="drop")
            qarr = np.full(len(s500), -1, dtype=int)
            qarr[v_std] = quintiles.values.astype(int)
            for q in range(5):
                mask = qarr == q
                quintile_pnl[q] = float(np.nansum(pnl[mask])) if mask.any() else 0.0
            if quintile_pnl:
                worst_q = min(quintile_pnl, key=quintile_pnl.get)
                cond4 = worst_q != 4  # worst is not the top trend quintile

    return {
        "passed": bool(cond1 and cond2 and cond3 and cond4),
        "cond1_edge_dominance": bool(cond1),
        "cond1_median_excess": median_excess,
        "cond1_frac_edge_clears_half_spread": frac_clear,
        "cond2_per_day_positive_ic": bool(cond2),
        "cond2_per_day_ic": per_day_ic,
        "cond3_per_day_positive_pnl": bool(cond3),
        "cond3_per_day_pnl": per_day_pnl,
        "cond4_trend_defense": bool(cond4),
        "cond4_quintile_pnl": quintile_pnl,
        "live_haircut": live_haircut,
        "edge_clear_min_frac": edge_clear_min_frac,
    }


# ---------------------------------------------------------------------------
# Tradeability gate v2 — promotion path
# ---------------------------------------------------------------------------

def tradeability_gate_v2(
    trade_df: pd.DataFrame,
    block_pnl,
    simple_baseline: dict | None = None,
    min_trades: int = 30,
    min_win_rate: float = 0.55,
    min_block_sharpe: float = 1.0,
    pnl_uplift_vs_baseline: float = 1.10,
) -> dict:
    """Block-CV-aggregated tradeability gate. Replaces v1 for the promotion path.

    Inputs
    ------
    trade_df : DataFrame from `pnl_sim.simulate_trades`, aggregated across all
        block-purged folds. Required columns: day, side, net.
    block_pnl : iterable of per-block PnL totals (length = number of folds, e.g. 15).
    simple_baseline : optional dict with keys `total_pnl`, `block_sharpe`. The best
        single-signal Ridge result on the same blocks. If None, G4 is skipped.
    min_trades, min_win_rate, min_block_sharpe, pnl_uplift_vs_baseline : thresholds.

    Conditions
    ----------
    G1 trade-level edge: ≥`min_win_rate` of round-trips have net>0 AND mean(net)>0.
    G2 block Sharpe   : Sharpe of block_pnl across folds ≥ `min_block_sharpe`.
    G3 per-day PnL    : sum of `net` per day > 0 for every day appearing in
                        trade_df (D2/D3/D4 expected).
    G4 beats baseline : ML total block PnL ≥ uplift × baseline.total_pnl AND
                        ML block-Sharpe ≥ baseline.block_sharpe (skipped if no baseline).
    """
    bp = np.asarray(list(block_pnl), dtype=float)
    n_trades = int(len(trade_df))

    if n_trades < min_trades:
        return {
            "passed": False,
            "reason": f"too_few_trades n={n_trades} < {min_trades}",
            "n_trades": n_trades,
            "block_pnl_total": float(bp.sum()) if bp.size else 0.0,
        }

    nets = trade_df["net"].astype(float).to_numpy()
    win_rate = float((nets > 0).mean())
    mean_net = float(nets.mean())
    g1 = (win_rate >= min_win_rate) and (mean_net > 0)

    if bp.size >= 2 and bp.std(ddof=1) > 0:
        block_sharpe = float(bp.mean() / bp.std(ddof=1))
    else:
        block_sharpe = float("nan")
    g2 = bool(np.isfinite(block_sharpe) and block_sharpe >= min_block_sharpe)

    per_day = trade_df.groupby("day")["net"].sum()
    per_day_dict = {int(d): float(v) for d, v in per_day.items()}
    g3 = bool(len(per_day_dict) >= 2 and all(v > 0 for v in per_day_dict.values()))

    g4 = True
    g4_diag: dict = {}
    if simple_baseline is not None:
        baseline_pnl = float(simple_baseline.get("total_pnl", 0.0))
        baseline_sharpe = float(simple_baseline.get("block_sharpe", 0.0))
        ml_total = float(bp.sum())
        if baseline_pnl > 0:
            g4_pnl_ok = ml_total >= pnl_uplift_vs_baseline * baseline_pnl
        else:
            g4_pnl_ok = ml_total > baseline_pnl
        g4_sharpe_ok = bool(np.isfinite(block_sharpe) and block_sharpe >= baseline_sharpe)
        g4 = bool(g4_pnl_ok and g4_sharpe_ok)
        g4_diag = {
            "ml_total_pnl": ml_total,
            "baseline_total_pnl": baseline_pnl,
            "ml_block_sharpe": block_sharpe,
            "baseline_block_sharpe": baseline_sharpe,
            "uplift_required": pnl_uplift_vs_baseline,
            "g4_pnl_ok": bool(g4_pnl_ok),
            "g4_sharpe_ok": g4_sharpe_ok,
        }

    return {
        "passed": bool(g1 and g2 and g3 and g4),
        "n_trades": n_trades,
        "g1_trade_edge": bool(g1),
        "g1_win_rate": win_rate,
        "g1_mean_net": mean_net,
        "g1_threshold_win_rate": min_win_rate,
        "g2_block_sharpe": g2,
        "g2_sharpe_value": block_sharpe,
        "g2_threshold": min_block_sharpe,
        "g3_per_day_pnl": g3,
        "g3_per_day": per_day_dict,
        "g4_beats_baseline": bool(g4),
        "g4_diagnostics": g4_diag,
        "block_pnl_total": float(bp.sum()),
        "block_pnl_n": int(bp.size),
    }
