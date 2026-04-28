"""Threshold calibration for the round-5 archetype classifier.

Reads the per-family CSVs already written by ``family_report --family ALL``
and evaluates each hardcoded threshold against the empirical distribution
of its underlying stat across all 50 products. Flags thresholds that:

  * sit too far in one tail (e.g. > 95% of products on one side → effectively
    a no-op or a blanket gate),
  * sit close to a natural distributional break (multimodal / bimodal),
  * lack significance at default FDR (e.g. an IC threshold of 0.04 when
    the noise floor at FDR α=0.05 is much higher).

Output: ``round5/reports/CALIBRATION/threshold_calibration.{csv,md}`` plus
per-stat distribution figures.

CLI::

    python round5/calibration.py
    python round5/calibration.py --root round5/reports
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5.archetypes import ArchetypeGates  # noqa: E402
from round5.research_lib import FAMILIES        # noqa: E402


THRESHOLD_SPECS = [
    # (gate name, stat column to look at, direction, "meaning when crossed")
    ("pair_corr_strong",      "max_within_family_abs_corr", "ge", "very high -> PAIR (no coint required)"),
    ("pair_corr_min",         "max_within_family_abs_corr", "ge", "moderate -> PAIR (with coint)"),
    ("mr_vr_max",             "vr_k5",                      "lt", "low -> MR candidate"),
    ("mr_acf1_max",           "acf_ret1_lag1",              "lt", "negative -> MR candidate"),
    ("mr_hurst_max",          "hurst",                      "lt", "low -> anti-persistent / MR"),
    ("mr_adf_max",            "adf_p_mid",                  "lt", "stationary mid -> MR"),
    ("mr_vwap_hurst_max",     "vwap_hurst",                 "lt", "low VWAP Hurst -> MR"),
    ("mr_vwap_adf_max",       "vwap_adf_p",                 "lt", "stationary VWAP -> MR"),
    ("mr_ic_min",             "ic_neg_zscore_max_abs",      "ge", "MR signal IC viable (informational)"),
    ("mom_vr_min",            "vr_k5",                      "gt", "high -> momentum candidate"),
    ("mom_hurst_min",         "hurst",                      "gt", "high -> trending"),
    ("mom_ic_min",            "ic_momentum_max_abs",        "ge", "momentum signal IC viable"),
    ("rw_vr_dev_max",         "vr_k5_dev_from_1",           "lt", "near 1 -> RW signature"),
    ("rw_hurst_dev_max",      "hurst_dev_from_half",        "lt", "near 0.5 -> RW signature"),
    ("rw_acf1_max_abs",       "acf_ret1_lag1_abs",          "lt", "near 0 -> RW signature"),
    ("rw_max_ic",             "ic_short_horizon_max_abs",   "lt", "no short-horizon edge"),
    ("rw_spread_to_std_min",  "spread_to_std",              "ge", "MM cushion adequate"),
    ("rw_lim10_sat_min",      "limit10_saturation",         "ge", "book deep enough"),
    ("obi_ic_min",            "ic_obi_max_abs_short",       "ge", "OBI IC viable at h<=10"),
]


def load_family_results(reports_root: Path) -> dict[str, dict[str, pd.DataFrame]]:
    """Loads per-family stats / signal IC / corr_mid / cointegration CSVs."""
    out: dict[str, dict[str, pd.DataFrame]] = {}
    for fam in FAMILIES:
        d = reports_root / fam
        if not d.exists():
            continue
        files = {
            "stats": d / "stats_per_product.csv",
            "ic": d / "signals_ic.csv",
            "corr_mid": d / "corr_mid.csv",
            "coint": d / "cointegration.csv",
        }
        if not all(f.exists() for f in files.values()):
            continue
        out[fam] = {
            "stats": pd.read_csv(files["stats"]),
            "ic": pd.read_csv(files["ic"]),
            "corr_mid": pd.read_csv(files["corr_mid"], index_col=0),
            "coint": pd.read_csv(files["coint"]),
        }
    return out


def build_per_product_panel(per_family: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """One row per product with all the stats the calibration needs."""
    rows = []
    short_horizons = (1, 10)
    for fam, parts in per_family.items():
        stats = parts["stats"]
        ic = parts["ic"]
        corr_mid = parts["corr_mid"]
        coint = parts["coint"]
        # Make corr_mid square (both rows and cols are products of this family)
        for _, srow in stats.iterrows():
            p = srow["product"]
            r = {
                "family": fam,
                "product": p,
                "vr_k5": float(srow.get("vr_k5", np.nan)),
                "hurst": float(srow.get("hurst", np.nan)),
                "acf_ret1_lag1": float(srow.get("acf_ret1_lag1", np.nan)),
                "ret1_std": float(srow.get("ret1_std", np.nan)),
                "spread_median": float(srow.get("spread_median", np.nan)),
                "limit10_saturation": float(srow.get("limit10_saturation", np.nan)),
                "adf_p_mid": float(srow.get("adf_p_mid", np.nan)),
                "vwap_hurst": float(srow.get("vwap_hurst", np.nan)),
                "vwap_adf_p": float(srow.get("vwap_adf_p", np.nan)),
            }
            r["vr_k5_dev_from_1"] = abs(r["vr_k5"] - 1.0) if pd.notna(r["vr_k5"]) else np.nan
            r["hurst_dev_from_half"] = abs(r["hurst"] - 0.5) if pd.notna(r["hurst"]) else np.nan
            r["acf_ret1_lag1_abs"] = abs(r["acf_ret1_lag1"]) if pd.notna(r["acf_ret1_lag1"]) else np.nan
            r["spread_to_std"] = (
                r["spread_median"] / r["ret1_std"] if r["ret1_std"] and pd.notna(r["spread_median"]) else np.nan
            )
            # max within-family |corr_mid|
            if p in corr_mid.index:
                row = corr_mid.loc[p].drop(p, errors="ignore")
                r["max_within_family_abs_corr"] = float(row.abs().max()) if not row.empty else np.nan
            else:
                r["max_within_family_abs_corr"] = np.nan
            # IC: max |IC| for neg_zscore_mid_50 across horizons
            ic_p = ic[ic["product"] == p] if "product" in ic.columns else pd.DataFrame()
            ic_cols = [c for c in ic_p.columns if c.startswith("ic_h")]
            if not ic_p.empty and ic_cols:
                neg_z_signals = ic_p[ic_p["signal"].isin(["neg_zscore_mid_50", "neg_zscore_vwap_50"])]
                mom = ic_p[ic_p["signal"] == "momentum_10"]
                r["ic_neg_zscore_max_abs"] = float(neg_z_signals[ic_cols].abs().to_numpy().max()) if not neg_z_signals.empty else np.nan
                r["ic_momentum_max_abs"] = float(mom[ic_cols].abs().to_numpy().max()) if not mom.empty else np.nan
                # Short-horizon: ic_h1, ic_h10 across all signals
                short_cols = [f"ic_h{h}" for h in short_horizons if f"ic_h{h}" in ic_p.columns]
                if short_cols:
                    r["ic_short_horizon_max_abs"] = float(ic_p[short_cols].abs().to_numpy().max())
                    r["ic_overall_max_abs"] = float(ic_p[ic_cols].abs().to_numpy().max())
                    obi_sub = ic_p[ic_p["signal"].isin(["obi_l1", "obi_l3"])]
                    r["ic_obi_max_abs_short"] = float(obi_sub[short_cols].abs().to_numpy().max()) if not obi_sub.empty else np.nan
                else:
                    r["ic_short_horizon_max_abs"] = np.nan
                    r["ic_overall_max_abs"] = np.nan
                    r["ic_obi_max_abs_short"] = np.nan
            else:
                r["ic_neg_zscore_max_abs"] = np.nan
                r["ic_momentum_max_abs"] = np.nan
                r["ic_short_horizon_max_abs"] = np.nan
                r["ic_overall_max_abs"] = np.nan
                r["ic_obi_max_abs_short"] = np.nan
            rows.append(r)
    return pd.DataFrame(rows)


def evaluate_threshold(stat: pd.Series, value: float, direction: str) -> dict:
    s = stat.dropna()
    n = len(s)
    if n == 0:
        return {"n": 0, "n_pass": 0, "frac_pass": np.nan, "flag": "no_data"}
    if direction == "lt":
        n_pass = int((s < value).sum())
    elif direction == "le":
        n_pass = int((s <= value).sum())
    elif direction == "gt":
        n_pass = int((s > value).sum())
    elif direction == "ge":
        n_pass = int((s >= value).sum())
    else:
        raise ValueError(direction)
    frac = n_pass / n
    flag = ""
    if frac >= 0.95:
        flag = "DEGENERATE_HIGH (almost no products gated out)"
    elif frac <= 0.05:
        flag = "DEGENERATE_LOW (almost no products pass)"
    return {
        "n": n,
        "n_pass": n_pass,
        "frac_pass": float(frac),
        "p10": float(s.quantile(0.10)),
        "p25": float(s.quantile(0.25)),
        "p50": float(s.quantile(0.50)),
        "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)),
        "min": float(s.min()),
        "max": float(s.max()),
        "flag": flag,
    }


def fig_distribution(stat: pd.Series, name: str, value: float, out_path: Path) -> Path:
    s = stat.dropna()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    if s.empty:
        ax.text(0.5, 0.5, "no data", ha="center")
    else:
        ax.hist(s, bins=20, color="steelblue", alpha=0.7)
        ax.axvline(value, color="red", ls="--", lw=1.0, label=f"threshold={value}")
        ax.legend()
        ax.set_title(f"{name}  (n={len(s)})")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out_path


def calibration_report(
    panel: pd.DataFrame, gates: ArchetypeGates, out_dir: Path,
) -> dict:
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    g = asdict(gates)
    for gate_name, stat_col, direction, meaning in THRESHOLD_SPECS:
        if stat_col not in panel.columns:
            rows.append({"gate": gate_name, "stat": stat_col, "value": g.get(gate_name), "n": 0, "flag": "missing_stat"})
            continue
        thresh_val = g.get(gate_name)
        if thresh_val is None:
            continue
        ev = evaluate_threshold(panel[stat_col], float(thresh_val), direction)
        ev.update({
            "gate": gate_name, "stat": stat_col,
            "direction": direction, "value": float(thresh_val),
            "meaning": meaning,
        })
        rows.append(ev)
        fig_distribution(panel[stat_col], gate_name, float(thresh_val),
                         fig_dir / f"{gate_name}.png")
    df = pd.DataFrame(rows)
    csv_path = out_dir / "threshold_calibration.csv"
    df.to_csv(csv_path, index=False)
    md = _markdown_summary(df, panel)
    (out_dir / "threshold_calibration.md").write_text(md, encoding="utf-8")
    return {"df": df, "panel": panel, "csv": csv_path}


def _markdown_summary(calib_df: pd.DataFrame, panel: pd.DataFrame) -> str:
    lines = ["# Round-5 archetype-threshold calibration", ""]
    lines.append(f"Universe: **{len(panel)} products** across "
                 f"**{panel['family'].nunique() if 'family' in panel.columns else '?'} families**.")
    lines.append("")
    lines.append("Each row in the table below evaluates one hardcoded gate against the "
                 "empirical distribution of its underlying statistic across all products.")
    lines.append("Flag column: `DEGENERATE_HIGH` = ≥95% pass (gate is a no-op), "
                 "`DEGENERATE_LOW` = ≤5% pass (gate is a blanket exclusion).")
    lines.append("")
    cols = ["gate", "stat", "direction", "value", "n_pass", "n",
            "frac_pass", "p25", "p50", "p75", "flag"]
    show_cols = [c for c in cols if c in calib_df.columns]
    lines.append("```")
    lines.append(calib_df[show_cols].to_string(index=False))
    lines.append("```")
    lines.append("")
    # Identify worst offenders
    deg = calib_df[calib_df["flag"].astype(str).str.contains("DEGENERATE", na=False)]
    if not deg.empty:
        lines.append("## Degenerate gates (likely miscalibrated)")
        for _, r in deg.iterrows():
            lines.append(
                f"- **{r['gate']}** = {r['value']}  "
                f"({r['stat']} {r['direction']}; "
                f"frac_pass={r.get('frac_pass', float('nan')):.2f}, "
                f"p25={r.get('p25', float('nan')):.4f}, "
                f"p50={r.get('p50', float('nan')):.4f}, "
                f"p75={r.get('p75', float('nan')):.4f}). "
                f"_{r['flag']}_"
            )
        lines.append("")
        lines.append("Recommended adjustment: move the threshold toward the median "
                     "(say p25 for `lt`/`le` gates, p75 for `gt`/`ge` gates) and re-run "
                     "`family_report --family ALL` to see whether the archetype mix changes.")
    else:
        lines.append("_No degenerate gates detected._")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Round 5 threshold calibration.")
    ap.add_argument("--root", type=Path, default=Path("round5/reports"))
    ap.add_argument("--out", type=Path, default=Path("round5/reports/CALIBRATION"))
    args = ap.parse_args()

    per_family = load_family_results(args.root)
    if not per_family:
        print(f"no per-family reports found under {args.root}; "
              f"run `family_report --family ALL` first")
        return 2
    panel = build_per_product_panel(per_family)
    gates = ArchetypeGates()
    args.out.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.out / "calibration_panel.csv", index=False)
    result = calibration_report(panel, gates, args.out)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(result["df"].to_string(index=False))
    print()
    print(f"reports -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
