#!/usr/bin/env python3
"""
Comparaison Backtester — subtom.py (MVA) vs subtom_as.py (Avellaneda-Stoikov)
==============================================================================
Lance prosperity4btx sur les deux stratégies et affiche un tableau de résultats.

Usage :
    python TUTORIAL_ROUND_1/tomates/compare_backtest.py

Prérequis :
    pip install prosperity4btx
"""

import os
import re
import subprocess
import sys

BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(os.path.dirname(BASE), "backtest_data")
DAYS      = "0"   # round 0, tous les jours (-2 et -1)

# ── Terminal colours ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W = 68

def run_backtest(strategy_file: str) -> dict:
    """
    Lance prosperity4btx et parse la sortie pour extraire les PnL.
    Retourne un dict : { "day_-2": int, "day_-1": int, "total": int }
    """
    cmd = [
        "prosperity4btx",
        strategy_file,
        DAYS,
        "--data",    DATA_DIR,
        "--no-out",
        "--no-progress",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = proc.stdout + proc.stderr
    except FileNotFoundError:
        print(f"{RED}Erreur : 'prosperity4btx' introuvable. "
              f"Installe-le via : pip install prosperity4btx{RESET}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"{RED}Timeout lors du backtest de {strategy_file}{RESET}")
        sys.exit(1)

    results = {"raw": output}
    # Extraire les lignes "Round X day Y: N,NNN" (dans la section Profit summary)
    day_pnl = {}
    for m in re.finditer(r"Round\s+\d+\s+day\s+([-\d]+):\s+([\d,]+)", output):
        key = f"day_{m.group(1)}"
        day_pnl[key] = int(m.group(2).replace(",", ""))

    # "Total profit:" apparaît à la fois par jour ET en grand total (dernier).
    all_totals = re.findall(r"Total profit:\s*([\d,]+)", output)
    total = int(all_totals[-1].replace(",", "")) if all_totals else sum(day_pnl.values())

    results.update(day_pnl)
    results["total"] = total
    return results


def fmt_pnl(val: int, ref: int | None = None) -> str:
    """Formate un PnL avec indication +/- par rapport à la référence."""
    s = f"{val:>8,}"
    if ref is not None:
        diff = val - ref
        color = GREEN if diff >= 0 else RED
        arrow = "+" if diff >= 0 else ""
        s += f"   {color}({arrow}{diff:,}){RESET}"
    return s


def main():
    strategies = {
        "MVA (subtom)":          os.path.join(BASE, "subtom.py"),
        "Avellaneda-Stoikov (AS)": os.path.join(BASE, "subtom_as.py"),
    }

    # Vérifier que les fichiers existent
    for name, path in strategies.items():
        if not os.path.exists(path):
            print(f"{RED}Fichier introuvable : {path}{RESET}")
            sys.exit(1)

    if not os.path.isdir(DATA_DIR):
        print(f"{RED}Répertoire de données introuvable : {DATA_DIR}")
        print(f"Crée-le avec :{RESET}")
        print(f"  mkdir -p {DATA_DIR}/round0")
        print(f"  cp données/prices_round_0_day_*.csv {DATA_DIR}/round0/")
        print(f"  cp données/trades_round_0_day_*.csv {DATA_DIR}/round0/")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}{'=' * W}")
    print(f"  COMPARAISON BACKTESTER — TOMATOES  |  Round 0 (jours -2 et -1)")
    print(f"{'=' * W}{RESET}\n")

    all_results = {}
    for name, path in strategies.items():
        short = os.path.basename(path)
        print(f"  {CYAN}Backtest{RESET} {short} ...", end=" ", flush=True)
        r = run_backtest(path)
        all_results[name] = r
        print(f"{GREEN}OK{RESET}  (total {r.get('total', '?'):,} XIRECs)")

    # ── Tableau de résultats ─────────────────────────────────────────────────
    names = list(strategies.keys())
    ref_r = all_results[names[0]]

    print(f"\n{CYAN}{'─' * W}{RESET}")
    print(f"  {'Stratégie':<36}  {'Jour -2':>10}  {'Jour -1':>10}  {'Total':>10}")
    print(f"  {'─' * 36}  {'─' * 10}  {'─' * 10}  {'─' * 10}")

    for i, name in enumerate(names):
        r   = all_results[name]
        ref = ref_r if i > 0 else None
        d2  = r.get("day_-2", 0)
        d1  = r.get("day_-1", 0)
        tot = r.get("total",  0)

        ref_d2  = ref_r.get("day_-2", 0) if ref else None
        ref_d1  = ref_r.get("day_-1", 0) if ref else None
        ref_tot = ref_r.get("total",  0) if ref else None

        tag = f"  {BOLD}" if i == 0 else "  "
        end = RESET if i == 0 else ""

        print(f"{tag}{name:<36}{end}  "
              f"{fmt_pnl(d2, ref_d2):>10}  "
              f"{fmt_pnl(d1, ref_d1):>10}  "
              f"{fmt_pnl(tot, ref_tot):>10}")

    print(f"{CYAN}{'─' * W}{RESET}")

    # ── Gagnant ───────────────────────────────────────────────────────────────
    best_name  = max(all_results, key=lambda n: all_results[n].get("total", 0))
    best_total = all_results[best_name]["total"]
    other_name = [n for n in names if n != best_name][0]
    gain       = best_total - all_results[other_name].get("total", 0)
    gain_pct   = gain / max(all_results[other_name].get("total", 1), 1) * 100

    print(f"\n  {BOLD}Gagnant : {GREEN}{best_name}{RESET}{BOLD} "
          f"(+{gain:,} XIRECs / +{gain_pct:.1f}% vs l'autre stratégie){RESET}")

    # ── Diagnostic AS ────────────────────────────────────────────────────────
    as_r   = all_results["Avellaneda-Stoikov (AS)"]
    mva_r  = all_results["MVA (subtom)"]
    as_tot = as_r.get("total", 0)
    mv_tot = mva_r.get("total", 0)

    print(f"\n  {BOLD}Analyse :{RESET}")
    if as_tot > mv_tot:
        print(f"  {GREEN}AS surperforme la MVA.{RESET} "
              f"Le modele AS capture mieux le spread en s'adaptant a l'inventaire.")
    elif as_tot == mv_tot:
        print(f"  {YELLOW}Strategies equivalentes.{RESET} "
              f"Envisage d'ajuster kappa/gamma.")
    else:
        gap = mv_tot - as_tot
        if gap < mv_tot * 0.1:
            print(f"  {YELLOW}AS legerement inferieur (-{gap:,}).{RESET} "
                  f"Augmenter gamma ou reduire kappa pour des quotes plus larges.")
        else:
            print(f"  {RED}AS inferieur (-{gap:,}).{RESET} "
                  f"sigma/kappa/gamma necessitent recalibration.")

    print(f"\n  Parametres AS actuels : kappa=0.125  gamma=0.05  sigma_floor=0.5")
    print(f"  Pour recalibrer : python TUTORIAL_ROUND_1/as_analysis.py --product TOMATOES\n")


if __name__ == "__main__":
    main()
