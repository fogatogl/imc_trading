#!/usr/bin/env python3
"""
backtest_visualize.py  ─  IMC Prosperity 4 Strategy Analyser
=============================================================
Runs a single trader.py strategy through the kevin-fu1 backtester,
then generates a rich HTML report with interactive charts and statistics.

Usage:
    python backtest_visualize.py <trader.py> [--round 0] [--open]

Options:
    --round N        Backtester round to use (default: 0)
    --open           Open the HTML report in the browser automatically
    --out PATH       Write the report to PATH (default: backtest_report.html)

Prerequisites:
    git  (to clone the backtester on first run)
    Python 3.10+
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path

# ── ANSI colours ──────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; B = "\033[1m";  X = "\033[0m"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Backtester paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BT_DIR     = SCRIPT_DIR / "imc-prosperity-4-backtester"


def ensure_backtester() -> None:
    if BT_DIR.is_dir():
        return
    print(f"  {C}Cloning backtester…{X}", end=" ", flush=True)
    r = subprocess.run(
        ["git", "clone",
         "https://github.com/kevin-fu1/imc-prosperity-4-backtester.git",
         str(BT_DIR)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"\n{R}git clone failed:\n{r.stderr}{X}")
        sys.exit(1)
    print(f"{G}OK{X}")


def build_env() -> dict:
    env = os.environ.copy()
    bt_pkg = str(BT_DIR)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = bt_pkg + (os.pathsep + existing if existing else "")
    return env


# ── Log parsing ───────────────────────────────────────────────────────────────

ACTIVITIES_HEADER_FIELDS = [
    "day", "timestamp", "product",
    "bid_price_1", "bid_volume_1", "bid_price_2", "bid_volume_2",
    "bid_price_3", "bid_volume_3",
    "ask_price_1", "ask_volume_1", "ask_price_2", "ask_volume_2",
    "ask_price_3", "ask_volume_3",
    "mid_price", "profit_and_loss",
]


def _safe_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return default


def parse_log(log_path: str) -> dict:
    """
    Parse a prosperity4bt log file.

    Returns
    -------
    {
      "rows"    : list[dict],          # one row per (day, timestamp, product)
      "products": list[str],
      "days"    : list[int],
      "sandbox" : str,                 # raw sandbox output
    }
    """
    rows: list[dict] = []
    sandbox_lines: list[str] = []

    with open(log_path, encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    try:
        data = json.loads(content)
        activities = data.get("activitiesLog", "").splitlines()
        if data.get("sandboxLog"):
            sandbox_lines = data.get("sandboxLog", "").splitlines()
        elif data.get("sandboxLogs"): # just in case
            sandbox_lines = data.get("sandboxLogs", "").splitlines()
            
        header = []
        for line in activities:
            if not line.strip(): continue
            # handle case where first line could be 'Activities log:' if it sneaks in
            if line.strip() == "Activities log:": continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 3: continue
            if not header or "day" not in header:
                header = parts
                continue
            row_raw = dict(zip(header, parts))
            row: dict = {
                "day":       int(_safe_float(row_raw.get("day", "0"))),
                "timestamp": int(_safe_float(row_raw.get("timestamp", "0"))),
                "product":   row_raw.get("product", "UNKNOWN").strip(),
                "mid_price": _safe_float(row_raw.get("mid_price", "0")),
                "pnl":       _safe_float(row_raw.get("profit_and_loss", "0")),
            }
            rows.append(row)
            
    except json.JSONDecodeError:
        section = None
        header = []

        for line in content.splitlines():
            line = line.rstrip("\n")

            # ── section detection ──────────────────────────────────────────
            if line.strip() == "Activities log:":
                section = "activities"
                header = []
                continue
            if line.strip() == "Sandbox logs:":
                section = "sandbox"
                continue
            if line.strip() == "Trade History:":
                section = "trades"
                continue

            # ── blank line resets section ──────────────────────────────────
            if not line.strip():
                section = None
                continue

            # ── parse activities ───────────────────────────────────────────
            if section == "activities":
                parts = [p.strip() for p in line.split(";")]
                if not header:
                    header = parts
                    continue
                row_raw = dict(zip(header, parts))
                row: dict = {
                    "day":       int(_safe_float(row_raw.get("day", "0"))),
                    "timestamp": int(_safe_float(row_raw.get("timestamp", "0"))),
                    "product":   row_raw.get("product", "UNKNOWN").strip(),
                    "mid_price": _safe_float(row_raw.get("mid_price", "0")),
                    "pnl":       _safe_float(row_raw.get("profit_and_loss", "0")),
                }
                rows.append(row)

            elif section == "sandbox":
                sandbox_lines.append(line)

    products = sorted({r["product"] for r in rows})
    days     = sorted({r["day"]     for r in rows})

    return {
        "rows":     rows,
        "products": products,
        "days":     days,
        "sandbox":  "\n".join(sandbox_lines),
    }

def latest_log(directory: str) -> str | None:
    logs = glob.glob(os.path.join(directory, "*.log"))
    return max(logs, key=os.path.getmtime) if logs else None


# ── Statistics ────────────────────────────────────────────────────────────────

def compute_stats(parsed: dict) -> dict:
    rows     = parsed["rows"]
    products = parsed["products"]
    days     = parsed["days"]

    # ── raw PnL per (day, timestamp) aggregated across products ──────────────
    ts_pnl: dict[tuple[int, int], float] = defaultdict(float)
    for r in rows:
        ts_pnl[(r["day"], r["timestamp"])] += r["pnl"]

    timeline = sorted(ts_pnl.keys())

    # ── per-day last timestamp ────────────────────────────────────────────────
    day_max_ts: dict[int, int] = {}
    for (day, ts) in timeline:
        if day not in day_max_ts or ts > day_max_ts[day]:
            day_max_ts[day] = ts

    sorted_days = sorted(days)
    day_raw_final: dict[int, float] = {
        day: ts_pnl[(day, day_max_ts[day])] for day in sorted_days
    }

    # per-day contribution = its own raw final (already cumulative within day)
    day_final: dict[int, float] = {day: day_raw_final[day] for day in sorted_days}
    total_pnl = sum(day_final.values())

    # ── cross-day offset so the equity curve is truly continuous ─────────────
    # offset[day] = sum of all previous days raw finals
    day_offset: dict[int, float] = {}
    running = 0.0
    for day in sorted_days:
        day_offset[day] = running
        running += day_raw_final[day]

    cum_pnl = [ts_pnl[k] + day_offset[k[0]] for k in timeline]

    # ── per-product cumulative pnl (cross-day continuous) ────────────────────
    prod_ts_pnl: dict[str, dict[tuple, float]] = {p: defaultdict(float) for p in products}
    for r in rows:
        prod_ts_pnl[r["product"]][(r["day"], r["timestamp"])] += r["pnl"]

    prod_day_offset: dict[str, dict[int, float]] = {p: {} for p in products}
    for p in products:
        running_p = 0.0
        for day in sorted_days:
            prod_day_offset[p][day] = running_p
            last_ts  = day_max_ts.get(day)
            last_val = prod_ts_pnl[p].get((day, last_ts), 0.0) if last_ts else 0.0
            running_p += last_val

    prod_cum: dict[str, list[float]] = {}
    for p in products:
        prod_cum[p] = [
            prod_ts_pnl[p].get(k, 0.0) + prod_day_offset[p][k[0]]
            for k in timeline
        ]

    # ── returns series (∆PnL between consecutive ticks) ──────────────────────
    returns = [0.0] + [cum_pnl[i] - cum_pnl[i - 1] for i in range(1, len(cum_pnl))]

    # Sharpe (annualised — rough, no risk-free rate)
    if len(returns) > 1:
        mu  = sum(returns) / len(returns)
        var = sum((x - mu) ** 2 for x in returns) / (len(returns) - 1)
        std = math.sqrt(var) if var > 0 else 1e-9
        sharpe = (mu / std) * math.sqrt(len(returns))
    else:
        sharpe = 0.0

    # Max drawdown
    peak = cum_pnl[0] if cum_pnl else 0.0
    max_dd = 0.0
    for v in cum_pnl:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd

    # Volatility (std of returns)
    if len(returns) > 1:
        mu2  = sum(returns) / len(returns)
        vol  = math.sqrt(sum((x - mu2) ** 2 for x in returns) / len(returns))
    else:
        vol = 0.0

    # Win rate (positive return ticks)
    non_zero = [x for x in returns if x != 0]
    win_rate = sum(1 for x in non_zero if x > 0) / len(non_zero) if non_zero else 0.0

    # Best / worst tick
    best_tick  = max(returns) if returns else 0
    worst_tick = min(returns) if returns else 0

    # Per-product final PnL
    prod_final: dict[str, float] = {}
    for p in products:
        last_val = prod_cum[p][-1] if prod_cum[p] else 0.0
        prod_final[p] = last_val

    return {
        "timeline":   [[d, t] for d, t in timeline],
        "cum_pnl":    cum_pnl,
        "prod_cum":   prod_cum,
        "returns":    returns,
        "day_final":  day_final,
        "total_pnl":  total_pnl,
        "sharpe":     sharpe,
        "max_dd":     max_dd,
        "volatility": vol,
        "win_rate":   win_rate,
        "best_tick":  best_tick,
        "worst_tick": worst_tick,
        "prod_final": prod_final,
        "products":   products,
        "days":       days,
        "n_ticks":    len(timeline),
    }


# ── Run backtest ──────────────────────────────────────────────────────────────

def run_backtest(strategy_file: str, round_num: str) -> tuple[dict, dict]:
    """
    Run prosperity4bt and return (raw_parsed_log, stats).

    The kevin-fu1 backtester writes its log to a 'backtests/' subfolder
    relative to cwd, so we run it from SCRIPT_DIR and look there.
    """
    env = build_env()

    # Run from the directory where this script lives so the backtester's
    # 'backtests/' output folder lands somewhere predictable.
    run_cwd = str(SCRIPT_DIR)
    backtests_dir = SCRIPT_DIR / "backtests"

    # Snapshot existing logs so we can identify the new one afterwards
    existing_logs: set[str] = set(
        glob.glob(str(backtests_dir / "*.log"))
    )

    cmd = [sys.executable, "-m", "prosperity4bt", strategy_file, round_num]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=240, cwd=run_cwd, env=env,
        )
    except FileNotFoundError:
        print(f"\n{R}prosperity4bt module not found. "
              f"Is the backtester cloned? (--help){X}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"\n{R}Timeout running backtest.{X}")
        sys.exit(1)

    if proc.returncode != 0:
        print(f"\n{R}Backtester exited with code {proc.returncode}:{X}")
        print(proc.stderr[-2000:])

    # Find the newly written log (prefer backtests/ folder, fall back to cwd)
    new_logs = set(glob.glob(str(backtests_dir / "*.log"))) - existing_logs
    if new_logs:
        log_file = max(new_logs, key=os.path.getmtime)
    else:
        # Fallback: any .log anywhere under SCRIPT_DIR written just now
        log_file = latest_log(str(SCRIPT_DIR))

    if not log_file:
        print(f"{R}No log file found — backtester may have failed.{X}")
        print(proc.stdout[-3000:])
        sys.exit(1)

    print(f"\n  {C}Log:{X} {log_file}")
    parsed = parse_log(log_file)
    stats  = compute_stats(parsed)
    return parsed, stats


# ── HTML report ───────────────────────────────────────────────────────────────

_PALETTE = [
    "#00e5ff", "#ff4081", "#76ff03", "#ffd740",
    "#e040fb", "#ff6d00", "#1de9b6", "#f50057",
]


def _sparkline_data(values: list[float], width=120, height=40) -> str:
    """Return an inline SVG sparkline path."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    n   = len(values)

    def sx(i):  return i / (n - 1) * width if n > 1 else width / 2
    def sy(v):  return height - (v - mn) / rng * height

    pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(values))
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{pts}" '
        f'fill="none" stroke="currentColor" stroke-width="1.8"/>'
        f'</svg>'
    )


def generate_report(
    strategy_path: str,
    round_num: str,
    parsed: dict,
    stats: dict,
    out_path: str,
) -> None:
    strat_name = Path(strategy_path).name

    # ── serialise data for JS ─────────────────────────────────────────────────
    # Build x-axis labels: "D{day}@{ts}"
    labels   = [f"D{d}@{t}" for d, t in stats["timeline"]]
    cum_pnl  = stats["cum_pnl"]

    prod_datasets_js = []
    for i, p in enumerate(stats["products"]):
        color = _PALETTE[i % len(_PALETTE)]
        data  = stats["prod_cum"][p]
        prod_datasets_js.append({
            "label": p,
            "data":  data,
            "borderColor": color,
            "backgroundColor": color + "22",
            "fill": False,
            "tension": 0.3,
            "pointRadius": 0,
            "borderWidth": 1.8,
        })

    returns_hist = stats["returns"]
    # bucket into 40 bins
    if returns_hist:
        rmin, rmax = min(returns_hist), max(returns_hist)
        rng = rmax - rmin or 1
        N_BINS = 40
        bins  = [rmin + i * rng / N_BINS for i in range(N_BINS + 1)]
        counts = [0] * N_BINS
        for v in returns_hist:
            idx = min(int((v - rmin) / rng * N_BINS), N_BINS - 1)
            counts[idx] += 1
        hist_labels = [f"{(bins[i] + bins[i+1]) / 2:.0f}" for i in range(N_BINS)]
    else:
        hist_labels, counts = [], []

    # day bars
    day_keys   = sorted(stats["day_final"].keys())
    day_labels = [f"Day {d}" for d in day_keys]
    day_vals   = [stats["day_final"][d] for d in day_keys]
    day_colors = ["#00e5ff44" if v >= 0 else "#ff408144" for v in day_vals]
    day_border = ["#00e5ff"   if v >= 0 else "#ff4081"   for v in day_vals]

    # product bar
    prod_labels = list(stats["prod_final"].keys())
    prod_vals   = [stats["prod_final"][p] for p in prod_labels]
    prod_colors = [_PALETTE[i % len(_PALETTE)] + "88" for i in range(len(prod_labels))]
    prod_border = [_PALETTE[i % len(_PALETTE)]        for i in range(len(prod_labels))]

    def fmt(v: float, decimals: int = 0) -> str:
        return f"{v:,.{decimals}f}"

    total_color = "#00e5ff" if stats["total_pnl"] >= 0 else "#ff4081"

    # ── sparklines ────────────────────────────────────────────────────────────
    spark_overall = _sparkline_data(cum_pnl)

    # ── HTML ──────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Backtest Report — {strat_name}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
/* ── Reset & base ─────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
:root {{
  --bg:        #08090d;
  --surface:   #0f1117;
  --surface2:  #161923;
  --border:    #1e2535;
  --accent:    #00e5ff;
  --accent2:   #ff4081;
  --text:      #e0e8f0;
  --muted:     #5a6680;
  --green:     #39ff14;
  --red:       #ff4081;
  --font-mono: 'JetBrains Mono', 'Fira Mono', 'Cascadia Code', monospace;
  --font-ui:   'DM Sans', 'Sora', 'Outfit', sans-serif;
}}

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

html {{ scroll-behavior: smooth }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.6;
  min-height: 100vh;
}}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px }}
::-webkit-scrollbar-track {{ background: var(--bg) }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px }}

/* ── Layout ────────────────────────────────────────────────────────────── */
.page {{
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px 80px;
}}

/* ── Header ────────────────────────────────────────────────────────────── */
header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 36px 0 28px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
  gap: 24px;
  flex-wrap: wrap;
}}
.header-left h1 {{
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.5px;
  color: #fff;
}}
.header-left h1 span {{
  color: var(--accent);
  font-family: var(--font-mono);
}}
.header-meta {{
  display: flex;
  gap: 20px;
  margin-top: 8px;
  flex-wrap: wrap;
}}
.meta-chip {{
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 10px;
  letter-spacing: 0.4px;
}}
.header-pnl {{
  text-align: right;
}}
.header-pnl .label {{
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}}
.header-pnl .value {{
  font-family: var(--font-mono);
  font-size: 36px;
  font-weight: 600;
  color: {total_color};
  letter-spacing: -1px;
}}

/* ── Stat cards ────────────────────────────────────────────────────────── */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 32px;
}}
.stat-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 18px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}}
.stat-card:hover {{ border-color: var(--accent); }}
.stat-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
  opacity: 0.6;
}}
.stat-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--muted);
  margin-bottom: 8px;
}}
.stat-value {{
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
  line-height: 1;
}}
.stat-sub {{
  font-size: 11px;
  color: var(--muted);
  margin-top: 6px;
  font-family: var(--font-mono);
}}
.stat-spark {{
  margin-top: 10px;
  color: var(--accent);
  opacity: 0.7;
}}

/* ── Section headers ───────────────────────────────────────────────────── */
.section-header {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 40px 0 16px;
}}
.section-header h2 {{
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--muted);
}}
.section-header::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}

/* ── Chart panels ──────────────────────────────────────────────────────── */
.chart-grid {{
  display: grid;
  gap: 16px;
  margin-bottom: 16px;
}}
.chart-grid.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.chart-grid.cols-3 {{ grid-template-columns: 2fr 1fr 1fr; }}

.panel {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  position: relative;
}}
.panel-title {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--muted);
  margin-bottom: 16px;
  font-weight: 500;
}}
.panel-canvas-wrap {{
  position: relative;
  width: 100%;
}}

/* ── Product breakdown table ───────────────────────────────────────────── */
.breakdown-table {{
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 13px;
}}
.breakdown-table th {{
  text-align: left;
  padding: 8px 12px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
  font-weight: 500;
}}
.breakdown-table td {{
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}}
.breakdown-table tr:last-child td {{ border-bottom: none }}
.breakdown-table tr:hover td {{ background: var(--surface2) }}
.product-dot {{
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}}
.bar-cell {{ width: 140px }}
.pnl-bar-wrap {{
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  width: 100%;
}}
.pnl-bar {{
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}}
.positive {{ color: #00e5ff }}
.negative {{ color: #ff4081 }}

/* ── Sandbox log ───────────────────────────────────────────────────────── */
.sandbox-pre {{
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted);
  max-height: 320px;
  overflow: auto;
  white-space: pre;
  line-height: 1.7;
}}

/* ── Footer ────────────────────────────────────────────────────────────── */
footer {{
  text-align: center;
  font-size: 11px;
  color: var(--muted);
  padding-top: 40px;
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
}}

/* ── Responsive ────────────────────────────────────────────────────────── */
@media (max-width: 860px) {{
  .chart-grid.cols-2, .chart-grid.cols-3 {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="page">

<!-- ══ HEADER ═══════════════════════════════════════════════════════════════ -->
<header>
  <div class="header-left">
    <h1>Backtest Report — <span>{strat_name}</span></h1>
    <div class="header-meta">
      <span class="meta-chip">Round {round_num}</span>
      <span class="meta-chip">{len(stats['days'])} day(s) — {stats['n_ticks']:,} ticks</span>
      <span class="meta-chip">{len(stats['products'])} product(s)</span>
    </div>
  </div>
  <div class="header-pnl">
    <div class="label">Total PnL (XIRECs)</div>
    <div class="value">{'+' if stats['total_pnl'] >= 0 else ''}{fmt(stats['total_pnl'])}</div>
  </div>
</header>

<!-- ══ STAT CARDS ════════════════════════════════════════════════════════════ -->
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Sharpe Ratio</div>
    <div class="stat-value" style="color:{'#39ff14' if stats['sharpe'] > 1 else '#ffd740' if stats['sharpe'] > 0 else '#ff4081'}">{fmt(stats['sharpe'], 3)}</div>
    <div class="stat-sub">risk-adjusted</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Max Drawdown</div>
    <div class="stat-value" style="color:#ff4081">-{fmt(stats['max_dd'])}</div>
    <div class="stat-sub">peak-to-trough</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Win Rate</div>
    <div class="stat-value">{fmt(stats['win_rate']*100, 1)}<span style="font-size:14px;color:var(--muted)">%</span></div>
    <div class="stat-sub">of non-zero ticks</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Tick Volatility</div>
    <div class="stat-value">{fmt(stats['volatility'], 1)}</div>
    <div class="stat-sub">std of ΔPnL</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Best Tick</div>
    <div class="stat-value" style="color:#00e5ff">+{fmt(stats['best_tick'])}</div>
    <div class="stat-sub">single timestamp</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Worst Tick</div>
    <div class="stat-value" style="color:#ff4081">{fmt(stats['worst_tick'])}</div>
    <div class="stat-sub">single timestamp</div>
  </div>
  <div class="stat-card" style="grid-column: span 2">
    <div class="stat-label">Equity curve</div>
    <div class="stat-spark">{spark_overall}</div>
    <div class="stat-sub" style="margin-top:6px">cumulative PnL over {stats['n_ticks']:,} ticks</div>
  </div>
</div>

<!-- ══ MAIN EQUITY CHART ══════════════════════════════════════════════════════ -->
<div class="section-header"><h2>Equity Curve</h2></div>
<div class="panel">
  <div class="panel-title">Cumulative PnL — all products combined</div>
  <div class="panel-canvas-wrap" style="height:280px">
    <canvas id="equity-chart"></canvas>
  </div>
</div>

<!-- ══ PER-DAY + RETURNS HIST ════════════════════════════════════════════════ -->
<div class="section-header"><h2>Distributions</h2></div>
<div class="chart-grid cols-2">
  <div class="panel">
    <div class="panel-title">PnL per day</div>
    <div class="panel-canvas-wrap" style="height:220px">
      <canvas id="day-chart"></canvas>
    </div>
  </div>
  <div class="panel">
    <div class="panel-title">Returns distribution (∆PnL histogram)</div>
    <div class="panel-canvas-wrap" style="height:220px">
      <canvas id="hist-chart"></canvas>
    </div>
  </div>
</div>

<!-- ══ PER-PRODUCT CHART ══════════════════════════════════════════════════════ -->
<div class="section-header"><h2>Per-product breakdown</h2></div>
<div class="chart-grid cols-3">
  <div class="panel">
    <div class="panel-title">Cumulative PnL by product</div>
    <div class="panel-canvas-wrap" style="height:260px">
      <canvas id="prod-chart"></canvas>
    </div>
  </div>
  <div class="panel" style="grid-column: span 2">
    <div class="panel-title">Final PnL by product</div>
    <table class="breakdown-table">
      <thead>
        <tr>
          <th>Product</th>
          <th>Final PnL</th>
          <th>% of total</th>
          <th class="bar-cell">Contribution</th>
        </tr>
      </thead>
      <tbody id="prod-table-body"></tbody>
    </table>
  </div>
</div>

<!-- ══ SANDBOX LOG ════════════════════════════════════════════════════════════ -->
{f'''
<div class="section-header"><h2>Sandbox logs</h2></div>
<pre class="sandbox-pre">{parsed["sandbox"][:8000]}</pre>
''' if parsed["sandbox"].strip() else ''}

</div><!-- .page -->

<footer>
  Generated by backtest_visualize.py · kevin-fu1/imc-prosperity-4-backtester · Round {round_num}
</footer>

<!-- ══ CHARTS JS ══════════════════════════════════════════════════════════════ -->
<script>
const LABELS      = {json.dumps(labels)};
const CUM_PNL     = {json.dumps(cum_pnl)};
const PROD_DS     = {json.dumps(prod_datasets_js)};
const HIST_LABELS = {json.dumps(hist_labels)};
const HIST_COUNTS = {json.dumps(counts)};
const DAY_LABELS  = {json.dumps(day_labels)};
const DAY_VALS    = {json.dumps(day_vals)};
const DAY_COLORS  = {json.dumps(day_colors)};
const DAY_BORDER  = {json.dumps(day_border)};
const PROD_LABELS = {json.dumps(prod_labels)};
const PROD_VALS   = {json.dumps(prod_vals)};
const PROD_COLORS = {json.dumps(prod_colors)};
const PROD_BORDER = {json.dumps(prod_border)};
const PALETTE     = {json.dumps(_PALETTE)};

Chart.defaults.color = '#5a6680';
Chart.defaults.borderColor = '#1e2535';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 11;

// ── Thin every-N-th to max MAX_PTS ──────────────────────────────────────────
function thin(arr, max=600) {{
  if (arr.length <= max) return arr;
  const step = Math.ceil(arr.length / max);
  return arr.filter((_, i) => i % step === 0);
}}
const xLabels = thin(LABELS);
const yVals   = thin(CUM_PNL);
const prodDS  = PROD_DS.map(d => ({{...d, data: thin(d.data)}}));

// ── colour helper ────────────────────────────────────────────────────────────
function pnlColor(v) {{ return v >= 0 ? '#00e5ff' : '#ff4081'; }}

// ── 1. Equity chart ──────────────────────────────────────────────────────────
new Chart(document.getElementById('equity-chart'), {{
  type: 'line',
  data: {{
    labels: xLabels,
    datasets: [{{
      label: 'Cumulative PnL',
      data: yVals,
      borderColor: '#00e5ff',
      backgroundColor: ctx => {{
        const g = ctx.chart.ctx.createLinearGradient(0,0,0,280);
        g.addColorStop(0, '#00e5ff33');
        g.addColorStop(1, '#00e5ff00');
        return g;
      }},
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    animation: {{ duration: 600 }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: t => t[0].label,
          label: t => ` PnL: ${{t.parsed.y.toLocaleString()}} XIRECs`,
        }}
      }}
    }},
    scales: {{
      x: {{ ticks: {{ maxTicksLimit: 10 }}, grid: {{ color: '#1e2535' }} }},
      y: {{ ticks: {{ callback: v => v.toLocaleString() }}, grid: {{ color: '#1e2535' }} }}
    }}
  }}
}});

// ── 2. Per-product chart ─────────────────────────────────────────────────────
new Chart(document.getElementById('prod-chart'), {{
  type: 'line',
  data: {{ labels: xLabels, datasets: prodDS }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    animation: {{ duration: 600 }},
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 10, padding: 12 }} }},
      tooltip: {{ callbacks: {{ label: t => ` ${{t.dataset.label}}: ${{t.parsed.y.toLocaleString()}}` }} }}
    }},
    scales: {{
      x: {{ ticks: {{ maxTicksLimit: 8 }}, grid: {{ color: '#1e2535' }} }},
      y: {{ ticks: {{ callback: v => v.toLocaleString() }}, grid: {{ color: '#1e2535' }} }}
    }}
  }}
}});

// ── 3. Day PnL bar ───────────────────────────────────────────────────────────
new Chart(document.getElementById('day-chart'), {{
  type: 'bar',
  data: {{
    labels: DAY_LABELS,
    datasets: [{{
      label: 'Day PnL',
      data: DAY_VALS,
      backgroundColor: DAY_COLORS,
      borderColor: DAY_BORDER,
      borderWidth: 2,
      borderRadius: 4,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: t => ` ${{t.parsed.y.toLocaleString()}} XIRECs` }} }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }} }},
      y: {{ ticks: {{ callback: v => v.toLocaleString() }}, grid: {{ color: '#1e2535' }} }}
    }}
  }}
}});

// ── 4. Returns histogram ─────────────────────────────────────────────────────
new Chart(document.getElementById('hist-chart'), {{
  type: 'bar',
  data: {{
    labels: HIST_LABELS,
    datasets: [{{
      label: 'Frequency',
      data: HIST_COUNTS,
      backgroundColor: HIST_LABELS.map(v => +v >= 0 ? '#00e5ff44' : '#ff408144'),
      borderColor:     HIST_LABELS.map(v => +v >= 0 ? '#00e5ff'   : '#ff4081'),
      borderWidth: 1,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ maxTicksLimit: 8 }}, grid: {{ color: '#1e2535' }} }},
      y: {{ grid: {{ color: '#1e2535' }} }}
    }}
  }}
}});

// ── 5. Product breakdown table ────────────────────────────────────────────────
const tbody = document.getElementById('prod-table-body');
const totalAbs = PROD_VALS.reduce((s, v) => s + Math.abs(v), 0) || 1;
const totalPnl = PROD_VALS.reduce((s, v) => s + v, 0) || 1;

PROD_LABELS.forEach((p, i) => {{
  const v    = PROD_VALS[i];
  const pct  = totalPnl !== 0 ? (v / Math.abs(totalPnl) * 100).toFixed(1) : '—';
  const barW = (Math.abs(v) / totalAbs * 100).toFixed(1);
  const col  = PALETTE[i % PALETTE.length];
  const tr   = document.createElement('tr');
  tr.innerHTML = `
    <td>
      <span class="product-dot" style="background:${{col}}"></span>${{p}}
    </td>
    <td class="${{v >= 0 ? 'positive' : 'negative'}}">${{v >= 0 ? '+' : ''}}${{v.toLocaleString()}}</td>
    <td class="${{v >= 0 ? 'positive' : 'negative'}}">${{v >= 0 ? '+' : ''}}${{pct}}%</td>
    <td class="bar-cell">
      <div class="pnl-bar-wrap">
        <div class="pnl-bar" style="width:${{barW}}%;background:${{col}}80"></div>
      </div>
    </td>`;
  tbody.appendChild(tr);
}});
</script>
</body>
</html>
"""

    Path(out_path).write_text(html, encoding="utf-8")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run a trader.py backtest and generate an HTML report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("strategy", help="Path to trader.py strategy file")
    ap.add_argument("--round",  default="0", metavar="N",
                    help="Backtester round (default: 0)")
    ap.add_argument("--out",    default="backtest_report.html", metavar="PATH",
                    help="Output HTML file (default: backtest_report.html)")
    ap.add_argument("--open",   action="store_true",
                    help="Open the report in the default browser after generation")
    args = ap.parse_args()

    strategy = os.path.abspath(args.strategy)
    if not os.path.isfile(strategy):
        print(f"{R}Strategy file not found: {strategy}{X}")
        sys.exit(1)

    strat_name = Path(strategy).name
    W = 66

    print(f"\n{B}{C}{'═' * W}{X}")
    print(f"{B}  IMC Prosperity 4 — Backtest Analyser{X}")
    print(f"{C}{'═' * W}{X}\n")
    print(f"  Strategy : {strat_name}")
    print(f"  Round    : {args.round}")
    print(f"  Output   : {args.out}\n")

    ensure_backtester()

    print(f"  {C}Running backtester…{X}", end=" ", flush=True)
    parsed, stats = run_backtest(strategy, args.round)
    print(f"{G}OK{X}")
    print(f"  {C}Parsing results…{X}  "
          f"products={len(stats['products'])}  "
          f"days={stats['days']}  "
          f"ticks={stats['n_ticks']:,}")

    print(f"  {C}Generating report…{X}", end=" ", flush=True)
    generate_report(strategy, args.round, parsed, stats, args.out)
    print(f"{G}OK{X}")

    # ── terminal summary ──────────────────────────────────────────────────────
    col = G if stats["total_pnl"] >= 0 else R
    print(f"\n{C}{'─' * W}{X}")
    print(f"  {'Metric':<28}  {'Value':>18}")
    print(f"  {'─' * 28}  {'─' * 18}")
    print(f"  {'Total PnL':<28}  {col}{stats['total_pnl']:>+18,.0f}{X}")
    for day in stats["days"]:
        v = stats["day_final"].get(day, 0)
        c = G if v >= 0 else R
        print(f"  {f'  Day {day} PnL':<28}  {c}{v:>+18,.0f}{X}")
    print(f"  {'─' * 28}  {'─' * 18}")
    print(f"  {'Sharpe Ratio':<28}  {stats['sharpe']:>18.4f}")
    print(f"  {'Max Drawdown':<28}  {-stats['max_dd']:>+18,.0f}")
    print(f"  {'Win Rate':<28}  {stats['win_rate']*100:>17.1f}%")
    print(f"  {'Tick Volatility':<28}  {stats['volatility']:>18.2f}")
    print(f"  {'Best Tick':<28}  {stats['best_tick']:>+18,.0f}")
    print(f"  {'Worst Tick':<28}  {stats['worst_tick']:>+18,.0f}")
    print(f"{C}{'─' * W}{X}")
    print(f"\n  Per-product final PnL:")
    for p, v in sorted(stats["prod_final"].items(), key=lambda kv: -kv[1]):
        c = G if v >= 0 else R
        print(f"    {p:<24}  {c}{v:>+12,.0f}{X}")

    print(f"\n  {G}Report written → {args.out}{X}\n")

    if args.open:
        webbrowser.open(Path(args.out).resolve().as_uri())


if __name__ == "__main__":
    main()
