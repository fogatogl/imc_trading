"""CLI entry point for the permissive multi-flag classifier.

Reads each family's per-product CSVs from the *legacy* report tree
(``round5/reports/<FAMILY>/``) and writes new outputs under
``round5/reports_permissive/<FAMILY>/``. Never mutates the legacy tree.

Usage::

    python -m round5.permissive.cli --family ALL
    python -m round5.permissive.cli --family MICROCHIP
    python -m round5.permissive.cli --family MICROCHIP --in round5/reports --out round5/reports_permissive
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

# Ensure project root on sys.path when launched as a script (so ``round5.*``
# imports resolve regardless of cwd).
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5.research_lib import FAMILIES  # noqa: E402
from round5.significance import add_significance_columns  # noqa: E402
from round5.permissive.classifier import Gates, compute_flags  # noqa: E402
from round5.permissive.ranking import assemble_family_df, build_summary_md  # noqa: E402


REQUIRED_FILES = (
    "stats_per_product.csv",
    "signals_ic.csv",
    "corr_mid.csv",
    "cointegration.csv",
)


def _load_family_inputs(in_family_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stats_df = pd.read_csv(in_family_dir / "stats_per_product.csv")
    ic_long = pd.read_csv(in_family_dir / "signals_ic.csv")
    if "significant" not in ic_long.columns:
        ic_long = add_significance_columns(ic_long)
    corr_mid = pd.read_csv(in_family_dir / "corr_mid.csv", index_col=0)
    coint_df = pd.read_csv(in_family_dir / "cointegration.csv")
    return stats_df, ic_long, corr_mid, coint_df


def run_family(
    family: str,
    in_root: Path,
    out_root: Path,
    gates: Gates = Gates(),
    verbose: bool = True,
) -> Path:
    in_family_dir = in_root / family
    missing = [f for f in REQUIRED_FILES if not (in_family_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"[{family}] missing legacy artifacts {missing} under {in_family_dir}. "
            f"Run `python round5/family_report.py --family {family}` first."
        )

    stats_df, ic_long, corr_mid, coint_df = _load_family_inputs(in_family_dir)

    # Per-product significance is FDR-pooled across the row's (signal, horizon)
    # cells in legacy add_significance_columns. We re-augment per-product so
    # best_significant_ic sees the column even on legacy frames missing it.
    rows: list[dict] = []
    for _, srow in stats_df.iterrows():
        p = srow["product"]
        ic_for_product = ic_long[ic_long["product"] == p].copy()
        if "significant" not in ic_for_product.columns:
            ic_for_product = add_significance_columns(ic_for_product)
        flags_dict = compute_flags(
            stats_row=srow.to_dict(),
            ic_for_product=ic_for_product,
            corr_mid=corr_mid,
            coint_df=coint_df,
            gates=gates,
        )
        rows.append(flags_dict)

    df = assemble_family_df(rows, gates=gates)
    summary_md = build_summary_md(family, df)

    out_family_dir = out_root / family
    out_family_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_family_dir / "archetype_assignment.csv"
    md_path = out_family_dir / "archetype_summary.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(summary_md, encoding="utf-8")

    if verbose:
        flagged = int((~df["no_edge"]).sum())
        total = len(df)
        flag_counts = {axis: int(df[f"{axis}_flag"].sum()) for axis in ("mr", "mom", "mm", "obi", "pair")}
        print(
            f"[{family}] {flagged}/{total} flagged (no_edge={total - flagged}); "
            f"flags: {flag_counts}  ->  {out_family_dir}"
        )

    return out_family_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="Round-5 permissive multi-flag classifier.")
    ap.add_argument(
        "--family",
        required=True,
        help=f"Family name (one of {list(FAMILIES)}) or ALL.",
    )
    ap.add_argument(
        "--in",
        dest="in_root",
        type=Path,
        default=Path("round5/reports"),
        help="Legacy report tree root (default: round5/reports).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("round5/reports_permissive"),
        help="Output tree root (default: round5/reports_permissive).",
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    families = list(FAMILIES) if args.family == "ALL" else [args.family]
    for fam in families:
        if fam not in FAMILIES:
            print(f"unknown family: {fam}", file=sys.stderr)
            return 2

    t0 = time.time()
    summary: list[tuple[str, int, int]] = []
    for fam in families:
        out_dir = run_family(fam, args.in_root, args.out, verbose=not args.quiet)
        df = pd.read_csv(out_dir / "archetype_assignment.csv")
        summary.append((fam, int((~df["no_edge"]).sum()), len(df)))

    if not args.quiet:
        total_flagged = sum(s[1] for s in summary)
        total = sum(s[2] for s in summary)
        print(
            f"done. {len(families)} family/families in {time.time() - t0:.1f}s. "
            f"Universe-wide: {total_flagged}/{total} flagged "
            f"({total - total_flagged} NO_EDGE) -> {args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
