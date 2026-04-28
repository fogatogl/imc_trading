"""CLI runner for the round-5 per-family research pipeline.

Usage::

    python round5/family_report.py --family MICROCHIP
    python round5/family_report.py --family ALL
    python round5/family_report.py --family MICROCHIP --days 2 3
    python round5/family_report.py --family ALL --out round5/reports
    python round5/family_report.py --family MICROCHIP --deep   # run deep-dive research

Deep-dive triggers (mean-reversion / trending / pairs) are always detected
and written to ``deep_triggers.md`` regardless of ``--deep``. The flag only
controls whether the dive bodies (OU fits, threshold curves, β-stability,
etc.) are computed.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root on sys.path so ``round5.research_lib`` resolves whether
# launched from repo root or from the round5/ directory.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import research_lib as rl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Round 5 per-family research pipeline.")
    ap.add_argument(
        "--family",
        required=True,
        help=f"Family name (one of {list(rl.FAMILIES)} or ALL).",
    )
    ap.add_argument(
        "--days",
        type=int,
        nargs="+",
        default=list(rl.DEFAULT_DAYS),
        help="Days to include (default: 2 3 4).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("round5/reports"),
        help="Output directory (default: round5/reports).",
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=rl.DATASET_ROOT,
        help="Dataset root (default: dataset/ROUND_5).",
    )
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument(
        "--deep",
        action="store_true",
        help="Run optional deep-dive research (MR / trending / pairs) on auto-triggered candidates.",
    )
    args = ap.parse_args()

    families = list(rl.FAMILIES) if args.family == "ALL" else [args.family]
    for fam in families:
        if fam not in rl.FAMILIES:
            print(f"unknown family: {fam}", file=sys.stderr)
            return 2

    t0 = time.time()
    for fam in families:
        rl.family_report(
            fam,
            out_dir=args.out,
            days=tuple(args.days),
            root=args.root,
            verbose=not args.quiet,
            deep=args.deep,
        )
    if not args.quiet:
        print(f"done. {len(families)} family report(s) in {time.time() - t0:.1f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
