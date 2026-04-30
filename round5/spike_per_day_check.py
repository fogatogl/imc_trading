"""Per-day positivity gate for spike strats.

Aggregate `spike_strategy_pnl.csv` mixes 3 days. Memory rule
`feedback_per_day_positive_selection` says drop products that lose on any
single day. Recompute per (product, day, side) at h=20 directly from the
event list and historical mids.

Methodology (mid-based, no spread cost — sign-only gate):
    PnL_event = sign · POSITION_LIMIT · (mid_{t+h} − mid_t)        (FOLLOW)
    PnL_event = -sign · POSITION_LIMIT · (mid_{t+h} − mid_t)       (FADE)
where h = 20 ticks, sign = direction of the spike at t.

Mid-based numbers diverge from sim (which crosses spread) but the *sign*
per day is what the gate checks; if a product loses sign-on-mid for a day,
a taker paying spread will lose more.

Inputs:
    round5/reports/CROSS/vol_spikes/spike_events.csv
    dataset/ROUND_5/prices_round_5_day_{2,3,4}.csv
Output:
    round5/reports/CROSS/vol_spikes/per_day_pnl.csv

Reuse: round5.research_lib.load_prices for the per-day mid stream.

Decision rule:
    A (product, side) survives only if pnl_h20 ≥ 0 on each of D2, D3, D4.

Run:
    .venv/Scripts/python.exe round5/spike_per_day_check.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from research_lib import load_prices

POSITION_LIMIT = 10
H = 20  # ticks
ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "round5" / "reports" / "CROSS" / "vol_spikes" / "spike_events.csv"
OUT = ROOT / "round5" / "reports" / "CROSS" / "vol_spikes" / "per_day_pnl.csv"

CANDIDATES: dict[str, str] = {
    "ROBOT_DISHES": "FADE",
    "ROBOT_IRONING": "FADE",
    "OXYGEN_SHAKE_CHOCOLATE": "FADE",
    "OXYGEN_SHAKE_EVENING_BREATH": "FADE",
    "MICROCHIP_TRIANGLE": "FADE",
    "MICROCHIP_SQUARE": "FOLLOW",
    "MICROCHIP_RECTANGLE": "FOLLOW",
    "MICROCHIP_OVAL": "FOLLOW",
}


def per_day_pnl(events: pd.DataFrame, product: str, side: str) -> dict[int, tuple[int, float]]:
    out: dict[int, tuple[int, float]] = {}
    sub = events[events["product"] == product]
    if sub.empty:
        return out
    days = sorted(sub["day"].unique().tolist())
    for d in days:
        ev = sub[sub["day"] == d]
        px = load_prices(product, days=(d,))
        if px.empty:
            out[int(d)] = (0, 0.0)
            continue
        mid = ((px["bid_price_1"] + px["ask_price_1"]) / 2.0).to_numpy()
        ts = px["timestamp"].to_numpy()
        ts_to_idx = {int(t): i for i, t in enumerate(ts)}
        pnl_total = 0.0
        n = 0
        for _, row in ev.iterrows():
            t = int(row["ts"])
            sign = int(row["sign"])
            i = ts_to_idx.get(t)
            if i is None:
                continue
            j = i + H
            if j >= len(mid):
                continue
            move = mid[j] - mid[i]
            if side == "FADE":
                pnl_event = -sign * POSITION_LIMIT * move
            else:
                pnl_event = sign * POSITION_LIMIT * move
            pnl_total += pnl_event
            n += 1
        out[int(d)] = (n, pnl_total)
    return out


def main() -> None:
    events = pd.read_csv(EVENTS)
    rows = []
    for product, side in CANDIDATES.items():
        per_day = per_day_pnl(events, product, side)
        for d, (n, pnl) in per_day.items():
            rows.append({"product": product, "side": side, "day": d, "n_events": n, "pnl_h20": pnl})
    df = pd.DataFrame(rows).sort_values(["product", "day"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(df.to_string(index=False))

    print("\n=== gating decision (strict per-day positive at h=20) ===")
    for product, side in CANDIDATES.items():
        sub = df[(df["product"] == product) & (df["side"] == side)]
        if sub.empty:
            verdict = "DROP (no events)"
        elif (sub["pnl_h20"] >= 0).all():
            verdict = f"KEEP  total={sub['pnl_h20'].sum():.0f}"
        else:
            losing = sub[sub["pnl_h20"] < 0]["day"].tolist()
            verdict = f"DROP (negative on day {losing}, total={sub['pnl_h20'].sum():.0f})"
        print(f"  {product:<32} {side:<6} -> {verdict}")


if __name__ == "__main__":
    main()
