"""One-off sanity check: does COMET agree with the LLM judge on p0041?

Background
----------
The LLM judge (``ab_judge.py``) ran on p0041 (Ussher, v0 baseline vs v2
challenger) and ruled v0 the winner: 37 wins vs 24, lost 3 of 6
rubrics, fail. Before adopting COMET as the primary gating oracle for
the Whitaker exercise, we want directional agreement between COMET
and that LLM verdict — if COMET says v2 wins, we have a calibration
problem (likely from the modern-WMT vs 16C-Latin domain mismatch).

Method
------
1. Load v0 and v2 segments from all three p0041 runs (run01/02/03).
2. Build per-segment ``ScoredPair`` records (Latin source + both
   English candidates). No Parker Society reference — Ussher has
   no aligned gold standard.
3. Score with CometKiwi reference-free (``wmt22-cometkiwi-da``).
4. Aggregate across all segments × all 3 runs.
5. Emit a markdown report at
   ``04_translation_work/ab/whitaker_ch1/comet_sanity_p0041.md``.

Pass criterion (directional)
----------------------------
COMET aggregate v0_mean > v1_mean AND v0_segment_wins > v1_segment_wins.
This matches the LLM judge's directional verdict (v0 won the page).
If COMET *disagrees* directionally, investigate before adopting it.

Usage
-----
::

    python 08_working_scratch/pipeline_scripts/comet_sanity_p0041.py

No CLI args — paths are hardcoded since this is a one-off.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import comet_score as cs


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
P0041_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0041"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
SCORES_JSONL = SANITY_DIR / "comet_sanity_p0041_scores.jsonl"
REPORT_MD = SANITY_DIR / "comet_sanity_p0041.md"

RUNS = ("run01", "run02", "run03")
MODEL = "Unbabel/wmt22-cometkiwi-da"

# Numbers from p0041_report.md (LLM judge verdict).
LLM_VERDICT = {
    "verdict": "FAIL",
    "v0_wins": 37,
    "v1_wins": 24,
    "ties": 17,
    "v1_win_rate": 0.31,
    "rubric": {
        "accuracy":          {"v0": 36, "v1": 17, "equal": 25},
        "fluency":           {"v0": 47, "v1": 15, "equal": 16},
        "format_compliance": {"v0":  8, "v1": 22, "equal": 48},
        "register":          {"v0": 38, "v1": 13, "equal": 27},
        "source_preservation": {"v0": 6, "v1": 20, "equal": 52},
        "titles":            {"v0":  0, "v1":  6, "equal": 72},
    },
    "v1_lost_rubrics": ("fluency", "accuracy", "register"),
    "v1_won_rubrics":  ("format_compliance", "source_preservation", "titles"),
}


def _format_pct(num: int, denom: int) -> str:
    return f"{(100.0 * num / denom):.0f}%" if denom else "n/a"


def main() -> int:
    # ----- Gather pairs across 3 runs ---------------------------------
    all_pairs: list[cs.ScoredPair] = []
    per_run_counts: dict[str, int] = {}
    for run in RUNS:
        v0 = P0041_DIR / "v0" / run / "segments_with_translations.jsonl"
        v1 = P0041_DIR / "v2" / run / "segments_with_translations.jsonl"
        if not v0.exists() or not v1.exists():
            print(f"[skip] missing run {run}: {v0.exists()=} {v1.exists()=}")
            continue
        pairs = cs.build_pairs(v0, v1)
        # Tag segment_id with run for de-duplication / inspection
        for p in pairs:
            p.segment_id = f"{run}__{p.segment_id}"
        all_pairs.extend(pairs)
        per_run_counts[run] = len(pairs)

    if not all_pairs:
        print("comet_sanity_p0041: no pairs loaded; aborting.")
        return 2
    print(
        f"Loaded {len(all_pairs)} pairs from {len(per_run_counts)} runs "
        f"({per_run_counts})"
    )

    # ----- Score ------------------------------------------------------
    print(f"Loading COMET model {MODEL!r} (first run will download ~2.4 GB)...")
    scored = cs.score_with_comet(all_pairs, model_name=MODEL, batch_size=8, gpus=0)

    # ----- Persist per-segment scores --------------------------------
    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with SCORES_JSONL.open("w", encoding="utf-8") as h:
        for p in scored:
            h.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    # ----- Aggregate --------------------------------------------------
    summary = cs.aggregate(scored)
    summary["model"] = MODEL
    summary["reference_based"] = False
    summary["runs"] = list(per_run_counts.keys())

    # Per-run aggregates (helps spot a single-run outlier)
    per_run_summary: dict[str, dict] = {}
    for run in per_run_counts:
        run_pairs = [p for p in scored if p.segment_id.startswith(f"{run}__")]
        per_run_summary[run] = cs.aggregate(run_pairs)

    # ----- Compare to LLM verdict ------------------------------------
    valid = [p for p in scored if p.v0_score is not None and p.v1_score is not None]
    if not valid:
        comet_dir = "no_valid_scores"
        agrees_overall = False
    else:
        comet_v0_mean = statistics.mean(p.v0_score for p in valid)
        comet_v1_mean = statistics.mean(p.v1_score for p in valid)
        comet_v0_wins = sum(1 for p in valid if p.delta < 0)
        comet_v1_wins = sum(1 for p in valid if p.delta > 0)
        comet_dir = "v0_wins" if comet_v0_mean > comet_v1_mean else (
            "v1_wins" if comet_v1_mean > comet_v0_mean else "tie"
        )
        # LLM said v0 wins; COMET agrees if v0_mean > v1_mean AND v0_wins > v1_wins.
        agrees_overall = (
            comet_v0_mean > comet_v1_mean and comet_v0_wins > comet_v1_wins
        )

    # ----- Markdown report -------------------------------------------
    lines: list[str] = []
    lines.append(f"# COMET sanity check on p0041")
    lines.append("")
    lines.append(
        f"**Verdict:** {'PASS — COMET agrees with LLM judge directionally' if agrees_overall else 'INVESTIGATE — COMET diverges from LLM judge'}"
    )
    lines.append("")
    lines.append(f"- Model: `{MODEL}`")
    lines.append(f"- Mode: reference-free (CometKiwi)")
    lines.append(f"- Runs aggregated: {', '.join(per_run_counts.keys())}")
    lines.append(f"- Segments scored: {summary.get('n_scored', 0)} / {summary.get('n_segments', 0)}")
    lines.append("")
    lines.append("## Aggregate COMET scores")
    lines.append("")
    lines.append("| metric | v0 (baseline) | v1 (= v2 challenger) | delta (v1 − v0) |")
    lines.append("|---|---:|---:|---:|")
    if valid:
        lines.append(
            f"| mean | {summary['v0_mean']:.4f} | {summary['v1_mean']:.4f} "
            f"| {summary['mean_delta_v1_minus_v0']:+.4f} |"
        )
        lines.append(
            f"| median | {summary['v0_median']:.4f} | {summary['v1_median']:.4f} "
            f"| — |"
        )
        lines.append(
            f"| segment wins | {summary['v0_segment_wins']} "
            f"| {summary['v1_segment_wins']} | — |"
        )
    lines.append("")
    lines.append("## Per-run aggregates")
    lines.append("")
    lines.append("| run | n_scored | v0_mean | v1_mean | mean_delta | v0_wins | v1_wins |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for run, s in per_run_summary.items():
        if s.get("n_scored"):
            lines.append(
                f"| {run} | {s['n_scored']} | {s['v0_mean']:.4f} | "
                f"{s['v1_mean']:.4f} | {s['mean_delta_v1_minus_v0']:+.4f} | "
                f"{s['v0_segment_wins']} | {s['v1_segment_wins']} |"
            )
        else:
            lines.append(f"| {run} | 0 | n/a | n/a | n/a | n/a | n/a |")
    lines.append("")
    lines.append("## LLM judge verdict (from p0041_report.md)")
    lines.append("")
    lines.append(f"- Overall: **{LLM_VERDICT['verdict']}** — v0 wins")
    lines.append(
        f"- Wins (v0 / v1 / tie): {LLM_VERDICT['v0_wins']} / "
        f"{LLM_VERDICT['v1_wins']} / {LLM_VERDICT['ties']}"
    )
    lines.append(
        f"- v1 win-rate: {LLM_VERDICT['v1_win_rate']:.0%} (gate was ≥55%)"
    )
    lines.append(f"- v1 lost rubrics: {', '.join(LLM_VERDICT['v1_lost_rubrics'])}")
    lines.append(f"- v1 won rubrics: {', '.join(LLM_VERDICT['v1_won_rubrics'])}")
    lines.append("")
    lines.append("## Directional comparison")
    lines.append("")
    lines.append(f"- LLM judge: **v0 wins**")
    if valid:
        lines.append(f"- COMET: **{comet_dir}**")
        lines.append(
            f"- Agreement: **{'YES' if agrees_overall else 'NO'}**"
        )
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **PASS** = COMET says v0 mean > v1 mean AND v0 segment-wins > v1 segment-wins. ")
    lines.append("  This is the sanity floor: directionally agree with the LLM judge.")
    lines.append("- Absolute COMET scores in 0.5–0.9 range are expected for modern WMT data; ")
    lines.append("  16C scholastic Latin → Victorian English may produce lower absolute scores. ")
    lines.append("  Don't compare to WMT benchmarks; only compare v0 vs v1 within this run.")
    lines.append("- If COMET disagrees but v0 was an obvious win on fluency/register, the most ")
    lines.append("  likely cause is domain mismatch (modern news training data). Investigate ")
    lines.append("  per-segment deltas before discarding the hybrid plan.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote per-segment scores to {SCORES_JSONL}")
    print(f"Wrote report to {REPORT_MD}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
