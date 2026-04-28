"""Round-5 spike strategy simulation.

After ``spike_anatomy.py`` classifies the mechanism per product, this
script asks the actionable question: **does fade (or follow) net positive
PnL after spread cost, given limit=10**?

For each product with ``n_spikes >= 5``:

    1. **Fade-taker**: at the spike tick, cross the spread to take the
       position opposite to the spike (sell at bid if spike was up, buy
       at ask if spike was down). Hold ``h`` ticks. Exit at the opposite
       side of the book. PnL = exec_in - exec_out (or vice versa).
    2. **Follow-taker**: same but in the spike direction.

Position-limit enforcement: each event sized at ``size = 10`` (the round-5
limit). Treats events as independent — i.e., assumes flat between events.
This is a *signal-strength check*, not a full strategy backtest.

Entry semantics: enter on the *next* tick after the spike (i.e., row_idx+1)
to avoid look-ahead. Exit ``h`` ticks later.

Outputs under ``round5/reports/CROSS/vol_spikes/anatomy/``:

    spike_strategy_pnl.csv   per-product × strategy × horizon: total PnL,
                             mean PnL/event, sharpe, n_events, hit-rate.
    figures/<P>_strategy.png two-line PnL curve (fade vs follow) across h.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from round5.research_lib import (  # noqa: E402
    DEFAULT_DAYS, FAMILIES, ProductData, add_microstructure, add_vwap,
    load_prices, load_trades,
)
from round5.vol_spikes import detect_spikes  # noqa: E402

POSITION = 10
HORIZONS = (5, 10, 20, 50, 100, 200)
MIN_SPIKES = 5


def simulate(d: ProductData, spikes: pd.DataFrame, horizons=HORIZONS) -> pd.DataFrame:
    """For each horizon, compute fade-taker and follow-taker per-event PnL.

    Per-event PnL semantics (taker, size=POSITION=10):
        FADE  + spike sign +1: open SHORT at bid_t+1, close LONG at ask_t+1+h
            pnl = (bid_{t+1} - ask_{t+1+h}) * 10
        FOLLOW+ spike sign +1: open LONG at ask_t+1, close SHORT at bid_t+1+h
            pnl = (bid_{t+1+h} - ask_{t+1}) * 10
        Sign-flipped for downside spikes.

    Entry next tick to avoid look-ahead.
    """
    rows = []
    if spikes.empty:
        return pd.DataFrame(rows)

    for h in horizons:
        fade_pnls = []
        follow_pnls = []
        for _, r in spikes.iterrows():
            day = int(r["day"])
            sign = int(r["sign"])
            i = int(r["row_idx"])
            sub = d.px[d.px["day"] == day].reset_index(drop=True)
            if i + 1 + h >= len(sub):
                continue
            entry = sub.iloc[i + 1]
            exitr = sub.iloc[i + 1 + h]
            bid_in = float(entry["bid_price_1"])
            ask_in = float(entry["ask_price_1"])
            bid_out = float(exitr["bid_price_1"])
            ask_out = float(exitr["ask_price_1"])
            if sign > 0:
                # Spike up: FADE = short -> sell at bid_in, buy back at ask_out
                fade_pnls.append((bid_in - ask_out) * POSITION)
                # Follow = long -> buy at ask_in, sell at bid_out
                follow_pnls.append((bid_out - ask_in) * POSITION)
            else:
                # Spike down: FADE = long
                fade_pnls.append((bid_out - ask_in) * POSITION)
                # Follow = short
                follow_pnls.append((bid_in - ask_out) * POSITION)

        for label, pnls in (("FADE", fade_pnls), ("FOLLOW", follow_pnls)):
            if not pnls:
                continue
            arr = np.asarray(pnls, dtype=float)
            rows.append({
                "product": d.product,
                "strategy": label,
                "horizon": h,
                "n_events": int(len(arr)),
                "total_pnl": float(arr.sum()),
                "mean_pnl_per_event": float(arr.mean()),
                "median_pnl_per_event": float(np.median(arr)),
                "std_pnl_per_event": float(arr.std()),
                "sharpe_per_event": float(arr.mean() / arr.std()) if arr.std() > 0 else np.nan,
                "hit_rate": float((arr > 0).mean()),
            })
    return pd.DataFrame(rows)


def fig_strategy(d: ProductData, df: pd.DataFrame, out_path: Path) -> None:
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle(f"{d.product} — Spike strategy PnL (size=10, taker)",
                 fontsize=11, fontweight="bold")

    axA = axes[0]
    for label, color in (("FADE", "darkorange"), ("FOLLOW", "steelblue")):
        sub = df[df["strategy"] == label].sort_values("horizon")
        if sub.empty:
            continue
        axA.plot(sub["horizon"], sub["total_pnl"], marker="o", color=color, label=label)
    axA.axhline(0, color="black", lw=0.5)
    axA.set_xscale("log")
    axA.legend(fontsize=8)
    axA.set_title("total PnL across all spike events")
    axA.set_xlabel("horizon (ticks)")
    axA.set_ylabel("PnL (sea shells)")

    axB = axes[1]
    for label, color in (("FADE", "darkorange"), ("FOLLOW", "steelblue")):
        sub = df[df["strategy"] == label].sort_values("horizon")
        if sub.empty:
            continue
        axB.plot(sub["horizon"], sub["mean_pnl_per_event"], marker="o", color=color, label=label)
    axB.axhline(0, color="black", lw=0.5)
    axB.set_xscale("log")
    axB.legend(fontsize=8)
    axB.set_title("mean PnL / event")
    axB.set_xlabel("horizon (ticks)")

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def run(k: float, lookback: int, days, out_dir: Path) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    rows = []
    products = [p for fam in FAMILIES.values() for p in fam]
    for fam, members in FAMILIES.items():
        for p in members:
            px = add_microstructure(load_prices(p, days))
            tr = load_trades(p, days)
            px = add_vwap(px, tr)
            d = ProductData(product=p, px=px, tr=tr)
            spikes = detect_spikes(d, k=k, lookback=lookback)
            if len(spikes) < MIN_SPIKES:
                continue
            sim = simulate(d, spikes)
            if sim.empty:
                continue
            sim["family"] = fam
            rows.append(sim)
            fig_strategy(d, sim, fig_dir / f"{p}_strategy.png")

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out.to_csv(out_dir / "spike_strategy_pnl.csv", index=False)
    print(f"[spike_strategy_sim] {out['product'].nunique() if not out.empty else 0} products simulated.")
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=float, default=4.0)
    p.add_argument("--lookback", type=int, default=500)
    p.add_argument("--days", type=int, nargs="+", default=list(DEFAULT_DAYS))
    p.add_argument("--out", type=Path,
                   default=_PROJECT_ROOT / "round5" / "reports" / "CROSS" / "vol_spikes" / "anatomy")
    args = p.parse_args(argv)
    run(k=args.k, lookback=args.lookback, days=args.days, out_dir=args.out)


if __name__ == "__main__":
    main()
