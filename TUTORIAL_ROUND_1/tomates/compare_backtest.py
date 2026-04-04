#!/usr/bin/env python3
"""
Comparaison Backtester — subtom.py (MVA) vs artomtrader.py (AR)
==============================================================================
Clones kevin-fu1/imc-prosperity-4-backtester (if needed) then runs both
strategies and prints a PnL comparison table.

Usage:
    python TUTORIAL_ROUND_1/tomates/compare_backtest.py

Prerequisites:
    gh  (GitHub CLI, used to clone the backtester)
    Python 3.10+
"""

import os
import re
import subprocess
import sys
import glob
import tempfile

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE       = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(os.path.dirname(HERE))           # imc_trading/
BT_DIR     = os.path.join(REPO_ROOT, "imc-prosperity-4-backtester")
ROUND      = "0"   # tutorial round

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W = 68


# ── Backtester setup ──────────────────────────────────────────────────────────

def ensure_backtester() -> None:
    """Clone the backtester repo with git if it is not already present."""
    if os.path.isdir(BT_DIR):
        return
    print(f"  {CYAN}Cloning backtester…{RESET}", end=" ", flush=True)
    result = subprocess.run(
        ["git", "clone", "https://github.com/kevin-fu1/imc-prosperity-4-backtester.git", BT_DIR],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"\n{RED}git clone failed:\n{result.stderr}{RESET}")
        sys.exit(1)
    print(f"{GREEN}OK{RESET}")


def build_env() -> dict:
    """Return an env dict with PYTHONPATH pointing at the backtester package."""
    env = os.environ.copy()
    bt_pkg = os.path.join(BT_DIR, "prosperity4bt")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = bt_pkg + (os.pathsep + existing if existing else "")
    return env


# ── Run & parse ───────────────────────────────────────────────────────────────

def _latest_log(directory: str) -> str | None:
    """Return the most-recently-modified .log file in *directory*."""
    logs = glob.glob(os.path.join(directory, "*.log"))
    return max(logs, key=os.path.getmtime) if logs else None


def _pnl_from_log(log_path: str) -> dict:
    """
    Parse the Activities section of a backtester log file.

    The log format has a section:
        Activities log:
        day;timestamp;product;...;profit_and_loss

    We read the last profit_and_loss value for each day.
    """
    day_pnl: dict[str, int] = {}

    with open(log_path, encoding="utf-8", errors="replace") as fh:
        in_activities = False
        header: list[str] = []
        for line in fh:
            line = line.rstrip("\n")
            if line.strip() == "Activities log:":
                in_activities = True
                header = []
                continue
            if in_activities:
                if not line.strip():   # blank line ends the section
                    break
                parts = line.split(";")
                if not header:
                    header = [h.strip() for h in parts]
                    continue
                row = dict(zip(header, parts))
                day_key = f"day_{row.get('day', '?').strip()}"
                pnl_str = row.get("profit_and_loss", "0").strip().replace(",", "")
                try:
                    day_pnl[day_key] = int(float(pnl_str))
                except ValueError:
                    pass

    return day_pnl


def _pnl_from_stdout(output: str) -> dict:
    """
    Fallback: try to parse PnL directly from captured stdout/stderr.
    Handles lines like:  Round 0 day -2: 1,234
    and:                 Total profit: 2,345
    """
    day_pnl: dict[str, int] = {}
    for m in re.finditer(r"Round\s+\d+\s+day\s+([-\d]+):\s+([\d,]+)", output):
        day_pnl[f"day_{m.group(1)}"] = int(m.group(2).replace(",", ""))
    return day_pnl


def run_backtest(strategy_file: str) -> dict:
    """
    Run prosperity4bt on *strategy_file* for ROUND and extract per-day PnL.
    Returns {"day_-2": int, "day_-1": int, "total": int, "raw": str}.
    """
    env = build_env()

    # prosperity4bt writes logs relative to cwd; use a temp dir to isolate them
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, "-m", "prosperity4bt", strategy_file, ROUND]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=tmp,
                env=env,
            )
        except FileNotFoundError:
            print(f"{RED}Error: Python module 'prosperity4bt' not found.{RESET}")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print(f"{RED}Timeout while backtesting {strategy_file}{RESET}")
            sys.exit(1)

        output = proc.stdout + proc.stderr

        # 1. Try to parse the generated log file
        log_file = _latest_log(tmp)
        if log_file:
            day_pnl = _pnl_from_log(log_file)
        else:
            day_pnl = _pnl_from_stdout(output)

        # 2. Also try stdout for an explicit "Total profit:" line
        all_totals = re.findall(r"Total profit:\s*([\d,]+)", output)
        total = (
            int(all_totals[-1].replace(",", ""))
            if all_totals
            else sum(day_pnl.values())
        )

    return {"raw": output, "total": total, **day_pnl}


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_pnl(val: int, ref: int | None = None) -> str:
    s = f"{val:>8,}"
    if ref is not None:
        diff  = val - ref
        color = GREEN if diff >= 0 else RED
        arrow = "+" if diff >= 0 else ""
        s += f"   {color}({arrow}{diff:,}){RESET}"
    return s


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    strategies = {
        "MVA  (subtom)":     os.path.join(HERE, "subtom.py"),
        "AR(5) (artomtrader)": os.path.join(os.path.dirname(HERE), "artomtrader.py"),
    }

    # Sanity checks
    for name, path in strategies.items():
        if not os.path.exists(path):
            print(f"{RED}File not found: {path}{RESET}")
            sys.exit(1)

    ensure_backtester()

    print(f"\n{BOLD}{CYAN}{'=' * W}")
    print(f"  BACKTEST COMPARISON — TOMATOES  |  Round 0 (days -2 and -1)")
    print(f"{'=' * W}{RESET}\n")

    all_results: dict[str, dict] = {}
    for name, path in strategies.items():
        short = os.path.basename(path)
        print(f"  {CYAN}Backtesting{RESET} {short} ...", end=" ", flush=True)
        r = run_backtest(path)
        all_results[name] = r
        print(f"{GREEN}OK{RESET}  (total {r.get('total', '?'):,} XIRECs)")

    # ── Results table ─────────────────────────────────────────────────────────
    names = list(strategies.keys())
    ref_r = all_results[names[0]]

    print(f"\n{CYAN}{'─' * W}{RESET}")
    print(f"  {'Strategy':<36}  {'Day -2':>10}  {'Day -1':>10}  {'Total':>10}")
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
        end = RESET        if i == 0 else ""

        print(
            f"{tag}{name:<36}{end}  "
            f"{fmt_pnl(d2, ref_d2):>10}  "
            f"{fmt_pnl(d1, ref_d1):>10}  "
            f"{fmt_pnl(tot, ref_tot):>10}"
        )

    print(f"{CYAN}{'─' * W}{RESET}")

    # ── Winner ────────────────────────────────────────────────────────────────
    best_name  = max(all_results, key=lambda n: all_results[n].get("total", 0))
    best_total = all_results[best_name]["total"]
    other_name = next(n for n in names if n != best_name)
    gain       = best_total - all_results[other_name].get("total", 0)
    other_tot  = max(all_results[other_name].get("total", 1), 1)
    gain_pct   = gain / other_tot * 100

    print(
        f"\n  {BOLD}Winner: {GREEN}{best_name}{RESET}{BOLD} "
        f"(+{gain:,} XIRECs / +{gain_pct:.1f}% vs the other strategy){RESET}"
    )

    # ── Diagnostic ────────────────────────────────────────────────────────────
    ar_tot  = all_results["AR(5) (artomtrader)"].get("total", 0)
    mva_tot = all_results["MVA  (subtom)"].get("total", 0)

    print(f"\n  {BOLD}Analysis:{RESET}")
    if ar_tot > mva_tot:
        gap = ar_tot - mva_tot
        print(f"  {GREEN}AR(5) outperforms MVA by {gap:,} XIRECs.{RESET} "
              f"Statistical study looks consistent.")
    elif ar_tot == mva_tot:
        print(f"  {YELLOW}Strategies are equivalent.{RESET} "
              f"Consider adjusting spread/skew parameters.")
    else:
        gap = mva_tot - ar_tot
        if gap < mva_tot * 0.1:
            print(f"  {YELLOW}AR(5) slightly underperforms (-{gap:,}).{RESET} "
                  f"Try increasing HALF_SPREAD or reducing SKEW_PER_UNIT.")
        else:
            print(f"  {RED}AR(5) significantly underperforms (-{gap:,}).{RESET} "
                  f"AR coefficients or spread/skew need recalibration.")

    print(f"\n  Current AR(5) params: HALF_SPREAD=4.5, SKEW_PER_UNIT=0.2")
    print(f"  To recalibrate: re-run the AR fitting notebook on fresh price data\n")


if __name__ == "__main__":
    main()
