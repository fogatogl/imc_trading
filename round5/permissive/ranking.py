"""Per-family ranking + DataFrame assembly for the permissive pipeline.

Takes the list of ``compute_flags`` outputs for a single family (5 products),
computes per-axis scores, ranks 1..5 within the family, sets
``top_<axis>_in_family`` for the top-K, derives ``no_edge``, builds the
``rationale`` and ``flags_concat`` columns, and returns a flat DataFrame
ready for CSV write.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from round5.permissive.classifier import Gates


AXES = ("mr", "mom", "mm", "obi", "pair")


def _z(arr: np.ndarray) -> np.ndarray:
    """Family-relative z-score; zero std ⇒ zero output."""
    a = np.asarray(arr, dtype=float)
    finite = np.isfinite(a)
    if not finite.any():
        return np.zeros_like(a)
    mu = float(np.nanmean(a[finite])) if finite.any() else 0.0
    sd = float(np.nanstd(a[finite])) if finite.any() else 0.0
    out = np.zeros_like(a)
    if sd > 0:
        out[finite] = (a[finite] - mu) / sd
    return out


def _score_mr(rows: list[dict]) -> np.ndarray:
    """mr_score = z(max(0.5-vr,0)) + z(max(-acf1,0)) + z(max(0.5-hurst,0)) + z(max(0, best_mr_ic_signed))."""
    vr = np.array([r["scores_inputs"]["vr_k5"] for r in rows], dtype=float)
    acf1 = np.array([r["scores_inputs"]["acf1"] for r in rows], dtype=float)
    hurst = np.array([r["scores_inputs"]["hurst"] for r in rows], dtype=float)
    ic = np.array([r["scores_inputs"]["best_mr_ic_signed"] for r in rows], dtype=float)
    t1 = np.maximum(0.5 - vr, 0.0)
    t2 = np.maximum(-acf1, 0.0)
    t3 = np.maximum(0.5 - hurst, 0.0)
    t4 = np.maximum(ic, 0.0)
    return _z(t1) + _z(t2) + _z(t3) + _z(t4)


def _score_mom(rows: list[dict]) -> np.ndarray:
    vr = np.array([r["scores_inputs"]["vr_k5"] for r in rows], dtype=float)
    hurst = np.array([r["scores_inputs"]["hurst"] for r in rows], dtype=float)
    ic = np.array([r["scores_inputs"]["best_mom_ic"] for r in rows], dtype=float)
    t1 = np.maximum(vr - 1.0, 0.0)
    t2 = np.maximum(hurst - 0.5, 0.0)
    t3 = np.maximum(ic, 0.0)
    return _z(t1) + _z(t2) + _z(t3)


def _score_mm(rows: list[dict]) -> np.ndarray:
    """mm_score = (spread/std)*lim10_sat - 5*|vr-1| - 5*|hurst-0.5|. Single
    composite (not z-summed) — passive-MM viability is an absolute concept."""
    out = []
    for r in rows:
        si = r["scores_inputs"]
        vr = si["vr_k5"]
        hurst = si["hurst"]
        sps = si["spread_med_over_std"]
        sat = si["lim10_sat"]
        if not np.isfinite(sps) or not np.isfinite(sat) or not np.isfinite(vr) or not np.isfinite(hurst):
            out.append(float("-inf"))
            continue
        out.append(sps * sat - 5.0 * abs(vr - 1.0) - 5.0 * abs(hurst - 0.5))
    return np.array(out, dtype=float)


def _score_obi(rows: list[dict]) -> np.ndarray:
    out = []
    for r in rows:
        si = r["scores_inputs"]
        if not si.get("best_obi_ic_passes_fdr"):
            out.append(0.0)
            continue
        out.append(max(0.0, float(si.get("best_obi_ic_abs", 0.0))))
    return np.array(out, dtype=float)


def _score_pair(rows: list[dict]) -> np.ndarray:
    out = []
    for r in rows:
        si = r["scores_inputs"]
        c = si["max_within_corr"]
        cp = si["min_coint_p"]
        if not np.isfinite(c):
            out.append(0.0)
            continue
        cp_eff = float(min(cp, 1.0)) if np.isfinite(cp) else 1.0
        out.append(abs(c) * (1.0 - cp_eff))
    return np.array(out, dtype=float)


def _rank_desc(arr: np.ndarray) -> np.ndarray:
    """1..N rank by descending value. NaN/-inf get worst rank. Ties: min."""
    a = np.asarray(arr, dtype=float)
    return pd.Series(a).rank(ascending=False, method="min", na_option="bottom").astype(int).to_numpy()


def assemble_family_df(rows: list[dict], gates: Gates = Gates()) -> pd.DataFrame:
    """Build the per-family classification DataFrame from compute_flags outputs."""
    if not rows:
        return pd.DataFrame()

    scorers = {
        "mr": _score_mr,
        "mom": _score_mom,
        "mm": _score_mm,
        "obi": _score_obi,
        "pair": _score_pair,
    }
    scores = {axis: fn(rows) for axis, fn in scorers.items()}
    ranks = {axis: _rank_desc(scores[axis]) for axis in AXES}
    top_k = gates.top_k_per_axis

    out_records = []
    for i, r in enumerate(rows):
        flags = r["flags"]
        segs = r["segments"]
        pair_info = r["pair_info"]
        obi_info = r["obi_info"]

        rec: dict = {"product": r["product"]}
        for axis in AXES:
            rec[f"{axis}_flag"] = bool(flags[f"{axis}_flag"])
        for axis in AXES:
            rec[f"{axis}_score"] = float(scores[axis][i]) if np.isfinite(scores[axis][i]) else float("nan")
            rec[f"{axis}_rank_in_family"] = int(ranks[axis][i])
            rec[f"top_{axis}_in_family"] = bool(ranks[axis][i] <= top_k)

        any_flag = any(flags.values())
        any_top = any(rec[f"top_{axis}_in_family"] for axis in AXES)
        rec["no_edge"] = bool(not any_flag and not any_top)

        fired = [axis.upper() for axis in AXES if flags[f"{axis}_flag"]]
        rec["flags_concat"] = "+".join(f"{name}_FLAG" for name in fired) if fired else "NO_EDGE"

        rec["pair_partner"] = pair_info["pair_partner"]
        rec["pair_corr"] = float(pair_info["pair_corr"]) if pd.notna(pair_info["pair_corr"]) else float("nan")
        rec["pair_coint_p"] = float(pair_info["pair_coint_p"]) if pd.notna(pair_info["pair_coint_p"]) else float("nan")
        rec["obi_signal"] = obi_info["obi_signal"]
        rec["obi_horizon"] = int(obi_info["obi_horizon"])
        rec["obi_ic"] = float(obi_info["obi_ic"]) if pd.notna(obi_info["obi_ic"]) else float("nan")

        # Rationale: fired-flag segments in fixed order, plus top-rank fallbacks
        # for axes where the universal gate missed but the product ranks top-K
        # in its family. This is what makes the pipeline "permissive": even
        # without a universal trigger, top-of-family on any axis is surfaced.
        segments: list[str] = []
        for axis in AXES:
            seg = segs.get(axis)
            if seg is not None:
                segments.append(seg)
        for axis in AXES:
            if not flags[f"{axis}_flag"] and rec[f"top_{axis}_in_family"]:
                segments.append(
                    f"[TOP_{axis.upper()}_IN_FAMILY rank={int(ranks[axis][i])}/{len(rows)} "
                    f"score={float(scores[axis][i]):+.3f}]"
                )
        rec["rationale"] = "; ".join(segments) if segments else ""

        out_records.append(rec)

    df = pd.DataFrame(out_records)
    return df


def build_summary_md(family: str, df: pd.DataFrame) -> str:
    """Per-family archetype_summary.md content."""
    if df.empty:
        return f"# {family} — permissive classifier\n\n_(no products)_\n"

    lines = [f"# {family} — permissive classifier", ""]
    lines.append("## Per-family ranking (1 = strongest on the axis)")
    lines.append("")
    header = "| product | mr | mom | mm | obi | pair |"
    sep = "|---|---:|---:|---:|---:|---:|"
    lines.append(header)
    lines.append(sep)
    for _, r in df.iterrows():
        lines.append(
            f"| {r['product']} | {int(r['mr_rank_in_family'])} | "
            f"{int(r['mom_rank_in_family'])} | {int(r['mm_rank_in_family'])} | "
            f"{int(r['obi_rank_in_family'])} | {int(r['pair_rank_in_family'])} |"
        )
    lines.append("")

    lines.append("## Counts")
    for axis in AXES:
        n = int(df[f"{axis}_flag"].sum())
        lines.append(f"- {axis.upper()}_FLAG: {n}")
    lines.append(f"- NO_EDGE: {int(df['no_edge'].sum())}")
    lines.append("")

    for axis in AXES:
        sub = df[df[f"{axis}_flag"]]
        lines.append(f"### {axis.upper()}_FLAG")
        if sub.empty:
            lines.append("- _(none)_")
        else:
            for _, r in sub.iterrows():
                lines.append(
                    f"- **{r['product']}** (rank {int(r[f'{axis}_rank_in_family'])}/{len(df)}, "
                    f"score={r[f'{axis}_score']:+.3f}) — {r['rationale']}"
                )
        lines.append("")

    # Top-rank-only (no universal flag fired but ranks top-K) products per axis,
    # to surface latent structure the universal gates missed.
    for axis in AXES:
        sub = df[(df[f"top_{axis}_in_family"]) & (~df[f"{axis}_flag"])]
        if sub.empty:
            continue
        lines.append(f"### TOP_{axis.upper()}_IN_FAMILY (rank ≤ K but {axis.upper()}_FLAG missed)")
        for _, r in sub.iterrows():
            lines.append(
                f"- **{r['product']}** (rank {int(r[f'{axis}_rank_in_family'])}/{len(df)}, "
                f"score={r[f'{axis}_score']:+.3f})"
            )
        lines.append("")

    no_edge_sub = df[df["no_edge"]]
    lines.append("### NO_EDGE")
    if no_edge_sub.empty:
        lines.append("- _(none — every product carries at least one flag or top-rank)_")
    else:
        for _, r in no_edge_sub.iterrows():
            lines.append(f"- **{r['product']}** — {r['rationale'] or 'no flag, no top-rank'}")
    lines.append("")
    return "\n".join(lines)
