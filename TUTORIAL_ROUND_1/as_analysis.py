#!/usr/bin/env python3
"""
Avellaneda-Stoikov Model Feasibility Analysis
=============================================
Analyse les données historiques d'IMC Prosperity pour déterminer si le
modèle Avellaneda-Stoikov (AS) de market-making est applicable.

Dépendances :
    pip install pandas numpy statsmodels scipy

Usage :
    python TUTORIAL_ROUND_1/as_analysis.py
    python TUTORIAL_ROUND_1/as_analysis.py --product EMERALDS
"""

import os
import sys
import argparse
import warnings

# Force UTF-8 output on Windows (cp1252 terminal can't handle box-drawing/Greek chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Terminal colours ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

W = 64   # line width

def ok(s):        return f"{GREEN}✓  {s}{RESET}"
def warn(s):      return f"{YELLOW}⚠  {s}{RESET}"
def fail(s):      return f"{RED}✗  {s}{RESET}"
def info(s):      return f"{DIM}   {s}{RESET}"
def bold(s):      return f"{BOLD}{s}{RESET}"
def section(n, title):
    bar = "─" * W
    return f"\n{CYAN}{bar}\n  {n}. {title}\n{bar}{RESET}"
def summary_bar():
    return f"{CYAN}{'═' * W}{RESET}"

# ── 1. Chargement des données ──────────────────────────────────────────────────

def load_prices() -> pd.DataFrame:
    frames = []
    for day in [-2, -1]:
        path = os.path.join(BASE, f"prices_round_0_day_{day}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, sep=";")
        df.columns = df.columns.str.strip()
        for c in df.columns:
            if c != "product":
                df[c] = pd.to_numeric(df[c], errors="coerce")
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_trades() -> pd.DataFrame:
    frames = []
    for day in [-2, -1]:
        path = os.path.join(BASE, f"trades_round_0_day_{day}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, sep=";")
        df.columns = df.columns.str.strip()
        df["price"]     = pd.to_numeric(df["price"],     errors="coerce")
        df["quantity"]  = pd.to_numeric(df["quantity"],  errors="coerce")
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["day"] = day
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def global_ts(df: pd.DataFrame, ts_col="timestamp") -> np.ndarray:
    """Ajoute un axe temporel global (day -2 → 0, day -1 → offset)."""
    days = sorted(df["day"].unique())
    max_ts = df[ts_col].max()
    offset = {d: i * (max_ts + 100) for i, d in enumerate(days)}
    return df[ts_col] + df["day"].map(offset)

# ── 2. Exposant de Hurst (méthode R/S) ────────────────────────────────────────

def hurst_rs(series: pd.Series, n_lags: int = 20) -> tuple[float, float]:
    """
    Exposant de Hurst via l'analyse Rescaled Range (R/S).

    Retourne (H, R²_du_fit_linéaire).
      H < 0.5 → mean-reverting   (idéal pour AS)
      H ≈ 0.5 → random walk      (hypothèse AS)
      H > 0.5 → tendance         (AS moins adapté)
    """
    x = np.array(series.dropna())
    n = len(x)
    min_lag = max(8, n // 100)
    max_lag = n // 4

    lags    = np.unique(np.logspace(np.log10(min_lag), np.log10(max_lag), n_lags).astype(int))
    rs_mean = []
    valid   = []

    for lag in lags:
        rs_sub = []
        for start in range(0, n - lag, lag):
            sub   = x[start: start + lag]
            mean  = sub.mean()
            dev   = np.cumsum(sub - mean)
            R     = dev.max() - dev.min()
            S     = sub.std(ddof=1)
            if S > 0:
                rs_sub.append(R / S)
        if rs_sub:
            rs_mean.append(np.mean(rs_sub))
            valid.append(lag)

    if len(valid) < 4:
        return np.nan, np.nan

    log_n  = np.log(valid)
    log_rs = np.log(rs_mean)
    slope, _, r, _, _ = stats.linregress(log_n, log_rs)
    return slope, r ** 2


# ── 3. Estimation de κ (intensité d'arrivée des ordres) ───────────────────────

def estimate_kappa(
    prices_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    product: str,
) -> tuple[float, float, float]:
    """
    Estime κ du modèle AS : λ(δ) = A · exp(−κ · δ)

    Méthode :
      Pour chaque snapshot du carnet, on calcule le demi-spread δ
      et on compte le nombre de trades sur la fenêtre suivante (200 ms).
      On ajuste log(λ̂) = log(A) − κ·δ par OLS.

    Retourne (κ, A, R²).
    """
    p = prices_df[prices_df["product"] == product].copy()
    t = trades_df[trades_df["symbol"]  == product].copy() if not trades_df.empty else pd.DataFrame()

    if p.empty or t.empty:
        return np.nan, np.nan, np.nan

    # Axe temporel global
    p = p.sort_values(["day", "timestamp"])
    t = t.sort_values(["day", "timestamp"])
    p["t_g"] = global_ts(p)
    t["t_g"] = global_ts(t)

    p["half_spread"] = (p["ask_price_1"] - p["bid_price_1"]) / 2.0

    price_ts = p["t_g"].values
    trade_ts = t["t_g"].values
    WINDOW   = 200   # fenêtre de 200 ms pour compter les trades

    # Comptage vectorisé des trades dans la fenêtre suivante
    trade_counts = np.array([
        int(np.sum((trade_ts >= ts) & (trade_ts < ts + WINDOW)))
        for ts in price_ts
    ])
    p["trade_count"] = trade_counts
    p["has_trade"]   = (trade_counts > 0).astype(float)

    # Filtrer les snapshots avec spread valide
    valid = p[p["half_spread"].notna() & (p["half_spread"] > 0)].copy()
    if len(valid) < 30:
        return np.nan, np.nan, np.nan

    # Binner par décile de half_spread
    bins = np.unique(np.percentile(valid["half_spread"], np.linspace(0, 100, 11)))
    if len(bins) < 3:
        return np.nan, np.nan, np.nan

    valid["bin"] = pd.cut(valid["half_spread"], bins=bins, include_lowest=True)
    grp = (
        valid.groupby("bin", observed=True)
             .agg(mean_spread=("half_spread", "mean"),
                  trade_rate  =("has_trade",   "mean"),
                  n           =("has_trade",   "count"))
             .dropna()
    )
    grp = grp[grp["trade_rate"] > 0]
    if len(grp) < 3:
        return np.nan, np.nan, np.nan

    # OLS : log(λ) = log(A) − κ · δ
    X = sm.add_constant(grp["mean_spread"].values)
    y = np.log(grp["trade_rate"].values)
    try:
        res   = sm.OLS(y, X).fit()
        kappa = -float(res.params[1])          # pente → −κ
        A_est = float(np.exp(res.params[0]))   # intercept → log(A)
        r2    = float(res.rsquared)
        return kappa, A_est, r2
    except Exception:
        return np.nan, np.nan, np.nan


# ── 4. Stabilité de la volatilité (fenêtres glissantes) ───────────────────────

def rolling_vol_stability(returns: pd.Series, windows=(20, 50, 100)) -> dict:
    """
    Pour chaque fenêtre, calcule σ glissant et son coefficient de variation (CV).
    Un CV faible indique une volatilité stable → σ fiable pour AS.
    """
    out = {}
    for w in windows:
        rv = returns.rolling(w, min_periods=max(5, w // 4)).std()
        out[w] = {
            "mean": float(rv.mean()),
            "std":  float(rv.std()),
            "cv":   float(rv.std() / rv.mean()) if rv.mean() > 0 else np.nan,
            "min":  float(rv.min()),
            "max":  float(rv.max()),
        }
    return out


# ── 5. Analyse principale par produit ─────────────────────────────────────────

def analyse(product: str, all_prices: pd.DataFrame, all_trades: pd.DataFrame) -> dict:
    """
    Lance les 6 analyses et retourne un dict de résultats pour le résumé Go/No-Go.
    """
    print(section("", f"Analyse Avellaneda-Stoikov — {bold(product)}"))

    prices = all_prices[all_prices["product"] == product].copy()
    prices = prices.sort_values(["day", "timestamp"]).reset_index(drop=True)

    if prices.empty:
        print(fail(f"Aucune donnée pour '{product}'."))
        return {}

    n_snaps = len(prices)
    days    = sorted(prices["day"].unique())
    print(info(f"{n_snaps} snapshots  |  jours : {days}"))

    # ── § 1 — Mid-Price et Log-Rendements ─────────────────────────────────────
    print(section(1, "Mid-Price & Log-Rendements"))

    mid    = prices["mid_price"]
    lr     = np.log(mid / mid.shift(1)).dropna()
    prices = prices.iloc[1:].copy()            # aligner avec lr
    prices["log_return"] = lr.values

    print(f"  Mid-price     : {mid.min():.2f} – {mid.max():.2f}  "
          f"(moy {mid.mean():.2f}, σ={mid.std():.2f})")
    print(f"  Log-rendement : μ = {lr.mean():.6f}   σ = {lr.std():.6f}")
    print(f"  N rendements  : {len(lr)}")

    # ── § 2 — Test de Stationnarité (ADF) ────────────────────────────────────
    print(section(2, "Stationnarité — Test ADF"))

    adf_stat, adf_p, adf_lags, _, adf_crit, _ = adfuller(lr, autolag="AIC")

    print(f"  Statistique ADF : {adf_stat:.4f}")
    print(f"  p-value         : {adf_p:.6f}")
    print(f"  Lags retenus    : {adf_lags}")
    for lvl, val in adf_crit.items():
        marker = " ←" if adf_stat < val else ""
        print(f"  Seuil {lvl:>4}      : {val:.4f}{marker}")

    adf_ok = adf_p < 0.05
    if adf_p < 0.01:
        print(ok(f"Rendements fortement stationnaires (p={adf_p:.4f}) → AS adapté"))
    elif adf_ok:
        print(ok(f"Rendements stationnaires à 5 % (p={adf_p:.4f}) → AS applicable"))
    else:
        print(fail(f"Rendements non-stationnaires (p={adf_p:.4f}) → risque pour AS"))

    # ── § 3 — Régime (Exposant de Hurst) ─────────────────────────────────────
    print(section(3, "Régime de Prix — Exposant de Hurst (R/S)"))

    H, H_r2 = hurst_rs(mid)

    print(f"  Exposant H   : {H:.4f}   (R² du fit = {H_r2:.4f})")
    print(info("H < 0.45 → mean-reversion forte (idéal pour AS)"))
    print(info("H ∈ [0.45, 0.55] → random walk (hypothèse AS)"))
    print(info("H > 0.55 → tendance (AS moins adapté)"))

    if   H < 0.45:
        hurst_ok  = True
        hurst_msg = ok(f"H={H:.3f} → Mean-reversion forte → AS très bien adapté")
    elif H < 0.55:
        hurst_ok  = True
        hurst_msg = ok(f"H={H:.3f} → Proche d'un random walk → AS applicable")
    elif H < 0.65:
        hurst_ok  = False
        hurst_msg = warn(f"H={H:.3f} → Légère tendance → AS moins optimal")
    else:
        hurst_ok  = False
        hurst_msg = fail(f"H={H:.3f} → Tendance forte → AS déconseillé")
    print(f"\n  {hurst_msg}")

    # ── § 4 — Distribution des Rendements (Fat Tails) ────────────────────────
    print(section(4, "Distribution des Rendements — Kurtosis & Skewness"))

    skew      = float(stats.skew(lr))
    kurt_exc  = float(stats.kurtosis(lr, fisher=True))   # excès (normal = 0)
    jb_s, jb_p = stats.jarque_bera(lr)
    p1, p99   = float(np.percentile(lr, 1)), float(np.percentile(lr, 99))

    print(f"  Skewness (asymétrie)   : {skew:+.4f}   (gaussienne = 0)")
    print(f"  Kurtosis excédentaire  : {kurt_exc:+.4f}   (gaussienne = 0)")
    print(f"  Jarque-Bera            : stat={jb_s:.2f}  p={jb_p:.4e}")
    print(f"  Queue basse (P1)       : {p1:.6f}")
    print(f"  Queue haute (P99)      : {p99:.6f}")
    print(f"  Ratio P99/|P1|         : {abs(p99 / p1):.3f}" if p1 != 0 else "")

    fat_ok = abs(skew) < 1.0 and kurt_exc < 10
    if abs(skew) < 0.5 and kurt_exc < 3:
        dist_msg = ok("Distribution quasi-gaussienne → hypothèses AS bien vérifiées")
    elif fat_ok:
        mult = 1 + kurt_exc / 10
        dist_msg = warn(f"Queues légèrement épaisses (kurt={kurt_exc:.1f}) → "
                        f"élargir les quotes d'un facteur ≈ {mult:.2f}×")
    else:
        dist_msg = fail(f"Queues épaisses sévères (kurt={kurt_exc:.1f}, skew={skew:.2f}) → "
                        f"AS sous-estime le risque extrême")
    print(f"\n  {dist_msg}")

    # ── § 5 — Estimation de κ ─────────────────────────────────────────────────
    print(section(5, "Intensité d'arrivée des ordres — Estimation de κ"))

    kappa, A_est, kappa_r2 = estimate_kappa(all_prices, all_trades, product)

    if not np.isnan(kappa):
        print(f"  κ (taux de décroissance) : {kappa:.4f}")
        print(f"  A (intensité à δ=0)      : {A_est:.4f}  trades / fenêtre")
        print(f"  R² du fit OLS            : {kappa_r2:.4f}")
        print()
        print(f"  λ(δ=1)  = {A_est * np.exp(-kappa * 1):.4f}")
        print(f"  λ(δ=5)  = {A_est * np.exp(-kappa * 5):.4f}")
        print(f"  λ(δ=10) = {A_est * np.exp(-kappa * 10):.4f}")

        if   kappa > 0 and kappa_r2 > 0.5:
            kappa_ok  = True
            kappa_msg = ok(f"κ={kappa:.3f} bien estimé (R²={kappa_r2:.2f}) → AS paramétrable")
        elif kappa > 0 and kappa_r2 > 0.2:
            kappa_ok  = True
            kappa_msg = warn(f"κ={kappa:.3f} estimé mais R² faible ({kappa_r2:.2f}) → traiter avec prudence")
        elif kappa > 0:
            kappa_ok  = False
            kappa_msg = warn(f"κ={kappa:.3f} mais fit médiocre (R²={kappa_r2:.2f}) → spread quasi-constant")
        else:
            kappa_ok  = False
            kappa_msg = fail(f"κ={kappa:.3f} ≤ 0 → intensité ne décroît pas avec le spread")
    else:
        kappa_ok  = False
        kappa_msg = fail("κ non estimable (données insuffisantes)")
    print(f"\n  {kappa_msg}")

    # ── § 6 — Volatilité σ et Stabilité ──────────────────────────────────────
    print(section(6, "Volatilité σ — Fenêtres Glissantes"))

    vol = rolling_vol_stability(lr, windows=(20, 50, 100))

    print(f"  {'Fenêtre':>8}  {'σ_moy':>10}  {'σ_std':>10}  {'CV':>8}  "
          f"{'σ_min':>10}  {'σ_max':>10}")
    print(f"  {'─' * 8}  {'─' * 10}  {'─' * 10}  {'─' * 8}  "
          f"{'─' * 10}  {'─' * 10}")

    cvs = []
    for w, v in vol.items():
        cv = v["cv"]
        cvs.append(cv if not np.isnan(cv) else 1.0)
        flag = "  ← instable" if cv > 0.6 else ""
        print(f"  {w:>8}  {v['mean']:>10.6f}  {v['std']:>10.6f}  "
              f"{cv:>8.3f}  {v['min']:>10.6f}  {v['max']:>10.6f}{flag}")

    mean_cv  = float(np.nanmean(cvs))
    sigma_tk = float(lr.std())      # σ par tick  (unité AS)

    print(f"\n  σ par tick   : {sigma_tk:.6f}")
    print(f"  CV moyen     : {mean_cv:.3f}")

    vol_ok = mean_cv < 0.6
    if   mean_cv < 0.3:
        vol_msg = ok(f"Volatilité stable (CV={mean_cv:.3f}) → σ fiable pour AS")
    elif mean_cv < 0.6:
        vol_msg = warn(f"Volatilité modérément instable (CV={mean_cv:.3f}) → "
                       f"fenêtre courte recommandée (w=20)")
    else:
        vol_msg = fail(f"Volatilité très instable (CV={mean_cv:.3f}) → σ peu fiable pour AS")
    print(f"\n  {vol_msg}")

    # ── § 7 — Résumé Go / No-Go ───────────────────────────────────────────────
    print(f"\n{summary_bar()}")
    print(f"{BOLD}{CYAN}  VERDICT GO / NO-GO  —  Modèle Avellaneda-Stoikov  →  {product}{RESET}")
    print(summary_bar())

    criteria = [
        # (label,                          passe,    idéal)
        ("Stationnarité (ADF)",            adf_ok,   adf_p < 0.01),
        ("Régime de prix (Hurst H)",       hurst_ok, H < 0.48),
        ("Distribution (fat tails)",       fat_ok,   abs(skew) < 0.5 and kurt_exc < 3),
        ("κ estimable et positif",         kappa_ok, not np.isnan(kappa) and kappa > 0 and kappa_r2 > 0.5),
        ("Stabilité de σ (CV)",            vol_ok,   mean_cv < 0.3),
    ]

    detail_values = [
        f"p={adf_p:.4f}",
        f"H={H:.3f}  R²={H_r2:.2f}",
        f"skew={skew:.2f}  kurt_exc={kurt_exc:.2f}",
        f"κ={kappa:.3f}  R²={kappa_r2:.2f}" if not np.isnan(kappa) else "N/A",
        f"CV={mean_cv:.3f}",
    ]

    n_pass = sum(1 for _, p, _ in criteria if p)
    n_all  = len(criteria)

    print(f"\n  {'Critère':<34}  {'Statut':<10}  {'Valeurs'}")
    print(f"  {'─' * 34}  {'─' * 10}  {'─' * 32}")
    for (name, passes, ideal), detail in zip(criteria, detail_values):
        if ideal:
            tag = f"{GREEN}IDÉAL {RESET}"
        elif passes:
            tag = f"{YELLOW}OK    {RESET}"
        else:
            tag = f"{RED}ÉCHEC {RESET}"
        print(f"  {name:<34}  {tag:<18}  {detail}")

    print(f"\n  Score : {n_pass}/{n_all} critères validés\n")

    # ── Verdict final ─────────────────────────────────────────────────────────
    if n_pass == n_all:
        verdict = f"{BOLD}{GREEN}★  GO  — Tous les critères passent. AS fortement recommandé.{RESET}"
        rec     = "Calibrer avec les paramètres ci-dessous."
    elif n_pass >= n_all - 1:
        verdict = f"{BOLD}{GREEN}GO  — {n_pass}/{n_all} critères validés. AS applicable.{RESET}"
        rec     = "Surveiller le critère défaillant en live."
    elif n_pass >= (n_all // 2) + 1:
        verdict = f"{BOLD}{YELLOW}GO CONDITIONNEL — {n_pass}/{n_all} critères.{RESET}"
        rec     = "Élargir les spreads et réduire q_max pour limiter le risque d'inventaire."
    else:
        verdict = f"{BOLD}{RED}NO-GO — {n_pass}/{n_all} critères. AS mal adapté.{RESET}"
        rec     = "Envisager une stratégie directionnelle ou un modèle différent."

    print(f"  {verdict}")
    print(f"\n  → {rec}")

    # ── Paramètres AS suggérés ────────────────────────────────────────────────
    print(f"\n  {'─' * W}")
    print(f"  {bold('Paramètres AS (si GO) :')}  γ=0.1 (risk-aversion standard)")
    print(f"    σ_tick       = {sigma_tk:.6f}  (écart-type du log-rendement par tick)")

    if not np.isnan(kappa) and kappa > 0:
        # Optimal AS spread : γσ²T + (2/γ)ln(1 + γ/κ)
        gamma  = 0.1
        T      = 1.0     # horizon normalisé à 1 session
        spread_as = gamma * sigma_tk**2 * T + (2.0 / gamma) * np.log(1.0 + gamma / kappa)
        print(f"    κ            = {kappa:.4f}")
        print(f"    A            = {A_est:.4f}  (trades/fenêtre à spread nul)")
        print(f"    Spread optimal (γ=0.1, T=1) :")
        print(f"      δ* = γσ²T + (2/γ)·ln(1 + γ/κ)  =  {spread_as:.4f} pts")
        print(f"    → Poster les quotes à mid ± {spread_as / 2:.3f} pts")
    else:
        print(f"    κ            = non estimé — calibrer manuellement")

    print(f"  {'─' * W}\n")

    return {
        "product":   product,
        "adf_ok":    adf_ok,   "adf_p":     adf_p,
        "hurst_ok":  hurst_ok, "H":         H,
        "fat_ok":    fat_ok,   "kurt":      kurt_exc, "skew": skew,
        "kappa_ok":  kappa_ok, "kappa":     kappa,    "kappa_r2": kappa_r2,
        "vol_ok":    vol_ok,   "mean_cv":   mean_cv,
        "sigma_tk":  sigma_tk,
        "n_pass":    n_pass,   "n_all":     n_all,
    }


# ── Tableau comparatif multi-produits ─────────────────────────────────────────

def comparison_table(results: list[dict]) -> None:
    if len(results) < 2:
        return
    bar = "═" * W
    print(f"\n{CYAN}{bar}")
    print(f"  TABLEAU COMPARATIF — Tous les Produits")
    print(f"{bar}{RESET}")
    print(f"  {'Produit':<14}  {'Score':>7}  {'ADF':>7}  {'Hurst':>7}  "
          f"{'Kurt':>7}  {'κ':>8}  {'CV σ':>7}  Verdict")
    print(f"  {'─' * 14}  {'─' * 7}  {'─' * 7}  {'─' * 7}  "
          f"{'─' * 7}  {'─' * 8}  {'─' * 7}  {'─' * 10}")

    for r in results:
        score  = f"{r['n_pass']}/{r['n_all']}"
        adf_s  = f"{GREEN}OK{RESET}" if r["adf_ok"]  else f"{RED}FAIL{RESET}"
        h_s    = f"{GREEN}{r['H']:.3f}{RESET}" if r["hurst_ok"] else f"{RED}{r['H']:.3f}{RESET}"
        k_s    = f"{GREEN}OK{RESET}" if r["kappa_ok"] else f"{RED}N/A{RESET}"
        cv_s   = f"{GREEN}{r['mean_cv']:.2f}{RESET}" if r["vol_ok"] else f"{RED}{r['mean_cv']:.2f}{RESET}"

        pct = r["n_pass"] / r["n_all"]
        if   pct == 1.0: verdict = f"{GREEN}GO ★{RESET}"
        elif pct >= 0.8:  verdict = f"{GREEN}GO{RESET}"
        elif pct >= 0.6:  verdict = f"{YELLOW}COND.{RESET}"
        else:             verdict = f"{RED}NO-GO{RESET}"

        print(f"  {r['product']:<14}  {score:>7}  {adf_s:>15}  {h_s:>15}  "
              f"{r['kurt']:>7.1f}  {r['kappa']:>8.3f}  {cv_s:>15}  {verdict}")
    print()


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse de faisabilité Avellaneda-Stoikov — IMC Prosperity"
    )
    parser.add_argument(
        "--product", default=None,
        help="Produit à analyser (ex. EMERALDS). Par défaut : tous."
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}{'═' * W}")
    print(f"  ANALYSE AVELLANEDA-STOIKOV  —  IMC Prosperity 4")
    print(f"{'═' * W}{RESET}")

    all_prices = load_prices()
    all_trades = load_trades()

    if all_prices.empty:
        print(fail("Aucun fichier CSV trouvé dans TUTORIAL_ROUND_1/"))
        sys.exit(1)

    print(info(f"Prix : {len(all_prices)} lignes  |  "
               f"Trades : {len(all_trades)} lignes  |  "
               f"Produits : {sorted(all_prices['product'].dropna().unique())}"))

    products = ([args.product] if args.product
                else sorted(all_prices["product"].dropna().unique()))

    results = []
    for prod in products:
        r = analyse(prod, all_prices, all_trades)
        if r:
            results.append(r)

    if len(results) > 1:
        comparison_table(results)


if __name__ == "__main__":
    main()
