"""CLI runner for the round-5 cross-family / cluster-level analysis.

Runs the playbook from ``round5/analysis_brief.md``:

1. Cluster all 50 products by structural characteristics.
2. Build per-cluster aggregate series and rank by rolling performance.
3. Detect cross-cluster lead-lag at multiple lags, keep only stable pairs.
4. Optional Granger-causality confirmation.

Usage::

    python round5/cross_analysis.py
    python round5/cross_analysis.py --days 2 3 4 --out round5/reports/CROSS
    python round5/cross_analysis.py --silhouette-min 0.10 --leadlag-corr-min 0.08

Logic gates are exposed as flags. Stages that don't pass their gate emit a
"skipped: <reason>" line in the findings doc rather than a misleading result.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round5 import cross_family as cf  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Round 5 cross-family / cluster analysis.")
    ap.add_argument("--days", type=int, nargs="+", default=list(cf.DEFAULT_DAYS))
    ap.add_argument("--out", type=Path, default=Path("round5/reports/CROSS"))
    ap.add_argument("--root", type=Path, default=cf.DATASET_ROOT)
    ap.add_argument("--quiet", action="store_true")

    # Gate overrides
    ap.add_argument("--silhouette-min", type=float, default=cf.Gates.silhouette_min)
    ap.add_argument("--cluster-k-min", type=int, default=cf.Gates.cluster_k_min)
    ap.add_argument("--cluster-k-max", type=int, default=cf.Gates.cluster_k_max)
    ap.add_argument("--min-cluster-size", type=int, default=cf.Gates.min_cluster_size)
    ap.add_argument("--leadlag-corr-min", type=float, default=cf.Gates.leadlag_corr_min)
    ap.add_argument("--leadlag-max-lag", type=int, default=cf.Gates.leadlag_max_lag)
    ap.add_argument("--stability-min", type=float, default=cf.Gates.stability_min)
    ap.add_argument("--stability-n-windows", type=int, default=cf.Gates.stability_n_windows)
    ap.add_argument("--granger-p-max", type=float, default=cf.Gates.granger_p_max)
    ap.add_argument("--granger-max-lag", type=int, default=cf.Gates.granger_max_lag)

    args = ap.parse_args()
    gates = cf.Gates(
        silhouette_min=args.silhouette_min,
        cluster_k_min=args.cluster_k_min,
        cluster_k_max=args.cluster_k_max,
        min_cluster_size=args.min_cluster_size,
        leadlag_corr_min=args.leadlag_corr_min,
        leadlag_max_lag=args.leadlag_max_lag,
        stability_min=args.stability_min,
        stability_n_windows=args.stability_n_windows,
        granger_p_max=args.granger_p_max,
        granger_max_lag=args.granger_max_lag,
    )

    t0 = time.time()
    cf.cross_family_report(
        out_dir=args.out,
        days=tuple(args.days),
        root=args.root,
        gates=gates,
        verbose=not args.quiet,
    )
    if not args.quiet:
        print(f"done in {time.time() - t0:.1f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
