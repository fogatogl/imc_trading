#!/usr/bin/env python3
"""
Grid Search — Hyperparamètres Avellaneda-Stoikov pour TOMATOES
==============================================================
Teste toutes les combinaisons de KAPPA × GAMMA × SIGMA_FLOOR
en exécutant prosperity4btx pour chacune.

Usage :
    python TUTORIAL_ROUND_1/tomates/grid_search_as.py

Prérequis :
    pip install prosperity4btx
"""

import os
import re
import subprocess
import sys
import itertools

BASE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE), "backtest_data")
DAYS     = "0"

TEMPLATE_FILE = os.path.join(BASE, "subtom_as.py")

# ── Grille de recherche ────────────────────────────────────────────────────────
KAPPA_VALUES       = [0.05, 0.10, 0.125, 0.15, 0.20, 0.25]
GAMMA_VALUES       = [0.01, 0.03, 0.05, 0.08, 0.10, 0.15]
SIGMA_FLOOR_VALUES = [0.3, 0.5, 0.8, 1.0, 1.5]

# ── Terminal colours ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def patch_and_run(kappa: float, gamma: float, sigma_floor: float) -> int | None:
    """
    Recopie subtom_as.py dans un fichier temporaire avec les paramètres patchés,
    lance prosperity4btx et retourne le PnL total (ou None si erreur).
    """
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        src = f.read()

    # Remplace les lignes de paramètres (valeur numérique uniquement)
    src = re.sub(r"(KAPPA\s*=\s*)[\d.]+", rf"\g<1>{kappa}", src)
    src = re.sub(r"(GAMMA\s*=\s*)[\d.]+", rf"\g<1>{gamma}", src)
    src = re.sub(r"(SIGMA_FLOOR\s*=\s*)[\d.]+", rf"\g<1>{sigma_floor}", src)

    # Fichier temp dans le même répertoire que subtom_as.py → datamodel.py accessible
    k_s  = str(kappa).replace(".", "_")
    g_s  = str(gamma).replace(".", "_")
    sf_s = str(sigma_floor).replace(".", "_")
    tmp_path = os.path.join(BASE, f"_gs_tmp_{k_s}_{g_s}_{sf_s}.py")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(src)

        cmd = [
            "prosperity4btx", tmp_path, DAYS,
            "--data", DATA_DIR,
            "--no-out", "--no-progress",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = proc.stdout + proc.stderr

        all_totals = re.findall(r"Total profit:\s*([\d,]+)", output)
        if all_totals:
            return int(all_totals[-1].replace(",", ""))
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    if not os.path.isfile(TEMPLATE_FILE):
        print(f"{RED}Fichier template introuvable : {TEMPLATE_FILE}{RESET}")
        sys.exit(1)

    if not os.path.isdir(DATA_DIR):
        print(f"{RED}Répertoire de données introuvable : {DATA_DIR}{RESET}")
        print(f"  mkdir -p {DATA_DIR}/round0")
        print(f"  cp données/prices_round_0_day_*.csv {DATA_DIR}/round0/")
        print(f"  cp données/trades_round_0_day_*.csv {DATA_DIR}/round0/")
        sys.exit(1)

    combos = list(itertools.product(KAPPA_VALUES, GAMMA_VALUES, SIGMA_FLOOR_VALUES))
    total  = len(combos)

    print(f"\n{BOLD}{CYAN}Grid Search AS — {total} combinaisons{RESET}")
    print(f"  kappa  : {KAPPA_VALUES}")
    print(f"  gamma  : {GAMMA_VALUES}")
    print(f"  σ_floor: {SIGMA_FLOOR_VALUES}\n")

    results = []

    for idx, (kappa, gamma, sigma_floor) in enumerate(combos, 1):
        label = f"κ={kappa:<6} γ={gamma:<6} σ_floor={sigma_floor}"
        print(f"  [{idx:>3}/{total}] {label} ... ", end="", flush=True)

        pnl = patch_and_run(kappa, gamma, sigma_floor)

        if pnl is None:
            print(f"{RED}ERREUR{RESET}")
        else:
            results.append((pnl, kappa, gamma, sigma_floor))
            color = GREEN if pnl >= 0 else RED
            print(f"{color}{pnl:>10,}{RESET}")

    if not results:
        print(f"\n{RED}Aucun résultat valide.{RESET}")
        sys.exit(1)

    # ── Classement ────────────────────────────────────────────────────────────
    results.sort(reverse=True)
    best_pnl, best_k, best_g, best_sf = results[0]

    W = 70
    print(f"\n{BOLD}{CYAN}{'=' * W}")
    print(f"  TOP 10 — Avellaneda-Stoikov (TOMATOES)")
    print(f"{'=' * W}{RESET}")
    print(f"  {'Rang':<5}  {'κ (kappa)':<12}  {'γ (gamma)':<12}  {'σ_floor':<10}  {'PnL total':>12}")
    print(f"  {'─' * 5}  {'─' * 12}  {'─' * 12}  {'─' * 10}  {'─' * 12}")

    for rank, (pnl, k, g, sf) in enumerate(results[:10], 1):
        mark = f"{BOLD}{GREEN}" if rank == 1 else ("" if pnl >= 0 else RED)
        end  = RESET if rank == 1 or pnl < 0 else ""
        print(f"  {mark}{rank:<5}  {k:<12}  {g:<12}  {sf:<10}  {pnl:>12,}{end}")

    print(f"{CYAN}{'─' * W}{RESET}")
    print(f"\n  {BOLD}Meilleurs paramètres :{RESET}")
    print(f"    KAPPA       = {best_k}")
    print(f"    GAMMA       = {best_g}")
    print(f"    SIGMA_FLOOR = {best_sf}")
    print(f"    PnL total   = {best_pnl:,} XIRECs\n")

    # ── Patch automatique de subtom_as.py ────────────────────────────────────
    answer = input("  Appliquer ces paramètres à subtom_as.py ? [o/N] ").strip().lower()
    if answer in ("o", "oui", "y", "yes"):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            src = f.read()
        src = re.sub(r"(KAPPA\s*=\s*)[\d.]+", rf"\g<1>{best_k}", src)
        src = re.sub(r"(GAMMA\s*=\s*)[\d.]+", rf"\g<1>{best_g}", src)
        src = re.sub(r"(SIGMA_FLOOR\s*=\s*)[\d.]+", rf"\g<1>{best_sf}", src)
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  {GREEN}subtom_as.py mis à jour.{RESET}\n")
    else:
        print(f"  Annulé — subtom_as.py inchangé.\n")


if __name__ == "__main__":
    main()
