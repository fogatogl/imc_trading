"""Re-run archetype classification on existing stats CSVs without
regenerating the full pipeline. Fast path for gate-tuning iterations.

Loads each family's stats_per_product, signals_ic, corr_mid, coint, and
data_quality CSVs, calls ``assign_archetypes`` with current gates, and
overwrites archetype_assignment.csv + the archetype section of
tradeable_ideas.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import archetypes as ar  # noqa: E402
from round5.research_lib import (  # noqa: E402
    FAMILIES,
    load_family,
    synthesize_ideas,
)


def reclassify_family(fam: str, reports_root: Path, run_sim: bool = True) -> dict:
    d = reports_root / fam
    if not d.exists():
        return {"family": fam, "skipped": "missing dir"}
    stats_df = pd.read_csv(d / "stats_per_product.csv")
    ic_long = pd.read_csv(d / "signals_ic.csv")
    corr_mid = pd.read_csv(d / "corr_mid.csv", index_col=0)
    coint_df = pd.read_csv(d / "cointegration.csv")
    quality_df = pd.read_csv(d / "data_quality.csv")
    vol_summary_df = pd.read_csv(d / "volatility.csv") if (d / "volatility.csv").exists() else None

    ic_by_product: dict[str, pd.DataFrame] = {}
    if "product" in ic_long.columns:
        for p, sub in ic_long.groupby("product"):
            ic_by_product[p] = sub.copy()

    # Load price + trade data for the family if MM sim is requested. The sim
    # gate is the only step that needs px/tr; everything else is pure
    # reclassification on existing CSVs.
    family_data = load_family(fam) if run_sim else {}

    archetype_df = ar.assign_archetypes(
        family_data=family_data,
        stats_df=stats_df,
        ic_by_product=ic_by_product,
        corr_mid=corr_mid,
        coint_df=coint_df,
        vol_summary_df=vol_summary_df,
        quality_df=quality_df,
    )

    sim_results: dict = {}
    if run_sim and family_data:
        sim_results = ar.run_rw_simulation_gate(
            family_data=family_data,
            archetype_df=archetype_df,
            out_dir=d,
            verbose=False,
        )

    archetype_df.to_csv(d / "archetype_assignment.csv", index=False)

    # Refresh tradeable_ideas.md + the archetype summary block.
    leadlag_path = d / "lead_lag.csv"
    leadlag = pd.read_csv(leadlag_path, index_col=0) if leadlag_path.exists() else pd.DataFrame()
    body = synthesize_ideas(
        fam, stats_df, ic_by_product, corr_mid, leadlag, coint_df,
        archetype_df=archetype_df,
    )
    arch_md = ar.archetype_summary_md(archetype_df, sim_results=sim_results)
    (d / "tradeable_ideas.md").write_text(
        body.rstrip() + "\n\n" + arch_md, encoding="utf-8"
    )
    return {
        "family": fam,
        "MR_TAKER": int((archetype_df["archetype"] == "MR_TAKER").sum()),
        "MOMENTUM": int((archetype_df["archetype"] == "MOMENTUM").sum()),
        "RANDOM_WALK": int((archetype_df["archetype"] == "RANDOM_WALK").sum()),
        "NO_EDGE": int((archetype_df["archetype"] == "NO_EDGE").sum()),
        "PAIR": int(archetype_df["is_pair"].sum()),
        "OBI": int(archetype_df["is_obi"].sum()),
        "MM": int(archetype_df["is_mm"].sum()) if "is_mm" in archetype_df.columns else 0,
    }


def main() -> int:
    root = ROOT / "round5" / "reports"
    summary = []
    for fam in FAMILIES:
        s = reclassify_family(fam, root)
        summary.append(s)
        print(s)
    df = pd.DataFrame(summary)
    print()
    print("TOTAL:", df.drop(columns=["family"]).sum(numeric_only=True).to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
