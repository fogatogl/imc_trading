#!/usr/bin/env bash
# run_backtests.sh — run the prosperity4bt backtester for every round1 strategy
# Usage: bash run_backtests.sh [--vis]   (pass --vis to open the visualizer per run)
#
# Backtester: https://github.com/kevin-fu1/imc-prosperity-4-backtester

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
BT="$REPO_ROOT/imc_trading/imc-prosperity-4-backtester/prosperity4bt/__main__.py"
PYTHONPATH_DIR="$REPO_ROOT/imc_trading/imc-prosperity-4-backtester"
DAYS="1--2 1--1 1-0"
OUTDIR="$REPO_ROOT/backtests"

# Pass --vis as first arg to open the visualizer after each run
NO_VIS="--no-vis"
[[ "${1:-}" == "--vis" ]] && NO_VIS=""

# Strategies with a Trader class in round1/
STRATEGIES=(
    round1/test_total.py
    round1/strat_cooperative.py
    round1/strat_taker_2664.py
    round1/strat_taker_diag.py
    round1/ash_mm_trader.py
    round1/ash_obi_trader.py
    round1/ash_penny_trader.py
    round1/ash_pennyjump_trader_dany.py
    round1/osmium_trader_dany.py
)

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SUMMARY_FILE="$OUTDIR/summary_${TIMESTAMP}.txt"
mkdir -p "$OUTDIR"

declare -a RESULTS

echo "Running backtest for ${#STRATEGIES[@]} strategies..."
echo "Days: $DAYS"
echo "Output: $OUTDIR"
echo ""

for STRAT in "${STRATEGIES[@]}"; do
    NAME=$(basename "$STRAT" .py)
    LOG="$OUTDIR/${TIMESTAMP}_${NAME}.log"

    echo "=== $NAME ==="
    PYTHONPATH="$PYTHONPATH_DIR" \
        "$PYTHON" "$BT" "$REPO_ROOT/$STRAT" $DAYS \
        --out "$LOG" $NO_VIS --no-merge-pnl 2>&1

    # Extract per-day PnL from the log (JSON activitiesLog field, last row per day)
    if [[ -f "$LOG" ]]; then
        PNLS=$(
            "$PYTHON" - "$LOG" <<'PYEOF'
import sys, json, csv, io

log_path = sys.argv[1]
with open(log_path) as f:
    data = json.load(f)

activities = data.get("activitiesLog", "")
reader = csv.DictReader(io.StringIO(activities), delimiter=";")
rows = list(reader)

# Group by day — last row per day has the running PnL
by_day = {}
for row in rows:
    day = row.get("day", "?")
    by_day[day] = row

total = 0
parts = []
for day in sorted(by_day):
    pnl = float(by_day[day].get("profit and loss", 0))
    total += pnl
    parts.append(f"  day {day}: {pnl:>10,.0f}")

print("\n".join(parts))
print(f"  TOTAL  : {total:>10,.0f}")
PYEOF
        )
        echo "$PNLS"
        RESULTS+=("$NAME|$PNLS")
    fi
    echo ""
done

# Write summary
{
    echo "Backtest summary — $TIMESTAMP"
    echo "Days: $DAYS"
    echo ""
    for ENTRY in "${RESULTS[@]}"; do
        NAME="${ENTRY%%|*}"
        REST="${ENTRY#*|}"
        echo "=== $NAME ==="
        echo "$REST"
        echo ""
    done
} > "$SUMMARY_FILE"

echo "Summary written to: $SUMMARY_FILE"
