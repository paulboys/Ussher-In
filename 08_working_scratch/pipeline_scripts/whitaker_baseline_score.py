"""Score the Whitaker baseline against the 1849 Parker Society reference.

Reads the 3 baseline runs of ``translation_prompts_whitaker.py`` on
c1_ch1 (p0030–p0031) and scores each ALIGNMENT UNIT (a sentence-level
group of Latin lines from chapter1_alignment.jsonl) against the
Parker Society aligned reference using reference-based COMET
(``Unbabel/wmt22-comet-da``).

WHY UNIT-LEVEL (not per-segment)
--------------------------------
A first pass scored each Latin segment (one body line) against its
unit's full reference. Latin sentences span multiple lines; the model
produces one English fragment per line. Comparing a one-line fragment
against a multi-line reference systematically tanks scores — the
fragment can match its slice of the reference perfectly and still
score ~0.30 because most of the reference is unaccounted for. This
script avoids that by:

1. Grouping the model's per-segment English by alignment unit.
2. Concatenating the per-segment Englishes in line order.
3. Scoring the concatenated unit-level English against the unit's
   reference, which is also the concatenation of multiple English
   lines (`english_line_ids` in chapter1_alignment.jsonl).

The per-segment scores are still written to the JSONL for diagnostic
inspection, but the **unit-level aggregate is the headline number**.

Output
------
- ``04_translation_work/ab/whitaker_ch1/whitaker_baseline_unit_scores.jsonl``
  one row per (run, alignment_unit): unit_score, latin_concat,
  english_concat, reference, contributing segment_ids.
- ``04_translation_work/ab/whitaker_ch1/whitaker_baseline_report.md``
  unit-level aggregate report.

Usage
-----
::

    python 08_working_scratch/pipeline_scripts/whitaker_baseline_score.py

No CLI args; paths are hardcoded since this is a Phase-1 one-off.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import comet_score as cs


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0030_p0031" / "whitaker"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
ALIGNMENT_PATH = SANITY_DIR / "chapter1_alignment.jsonl"

SCORES_JSONL = SANITY_DIR / "whitaker_baseline_unit_scores.jsonl"
REPORT_MD = SANITY_DIR / "whitaker_baseline_report.md"

RUNS = ("whitaker_baseline_run01", "whitaker_baseline_run02", "whitaker_baseline_run03")
MODEL = "Unbabel/wmt22-comet-da"
REFERENCE_PART = "whitaker_english"


@dataclass
class UnitScore:
    run: str
    unit_id: str
    segment_ids: list[str]
    latin_concat: str
    english_concat: str
    reference: str
    score: float | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "run": self.run,
            "unit_id": self.unit_id,
            "segment_ids": self.segment_ids,
            "latin_concat": self.latin_concat,
            "english_concat": self.english_concat,
            "reference": self.reference,
            "score": self.score,
            "error": self.error,
        }


def main() -> int:
    # ----- Alignment + reference lookup ------------------------------
    if not ALIGNMENT_PATH.exists():
        print(f"missing alignment file: {ALIGNMENT_PATH}")
        return 2
    alignment = cs.load_alignment(ALIGNMENT_PATH)
    ref_lookup = cs.build_reference_lookup(alignment, part=REFERENCE_PART)
    print(f"Loaded reference lookup: {len(ref_lookup)} latin line_ids covered")

    # Build unit lookup: unit_id -> (ordered latin_line_ids, reference text)
    unit_specs: list[tuple[str, list[str], str]] = []
    for unit in alignment:
        uid = unit.get("unit_id") or "unknown_unit"
        lat_ids = unit.get("latin_line_ids") or []
        # Reference is the same for every Latin line in this unit (built from
        # english_line_ids elsewhere). Pull it from ref_lookup via any contributing
        # latin id. Fall back to empty string if no latin lines.
        ref = ""
        if lat_ids:
            ref = ref_lookup.get(lat_ids[0], "")
        unit_specs.append((uid, lat_ids, ref))

    # ----- Per-run per-segment loading --------------------------------
    per_run_seg_count: dict[str, int] = {}
    all_units: list[UnitScore] = []
    for run_tag in RUNS:
        run_path = BASELINE_DIR / run_tag / "segments_with_translations.jsonl"
        if not run_path.exists():
            print(f"  [skip] missing run {run_tag}: {run_path}")
            continue
        run_records = cs.load_run(run_path)
        per_run_seg_count[run_tag] = len(run_records)

        # Index segments by line_id for easy unit lookup
        seg_by_line: dict[str, dict] = {}
        for seg_id, rec in run_records.items():
            line_id = cs.segment_id_to_line_id(seg_id)
            seg_by_line[line_id] = {**rec, "_segment_id": seg_id}

        for uid, lat_ids, ref in unit_specs:
            if not lat_ids:
                continue
            seg_ids: list[str] = []
            latin_parts: list[str] = []
            english_parts: list[str] = []
            for lid in lat_ids:
                rec = seg_by_line.get(lid)
                if not rec:
                    continue
                seg_ids.append(rec["_segment_id"])
                latin_parts.append((rec.get("latin_text") or "").strip())
                eng = (
                    (rec.get("translation_history") or [{}])[-1].get("english")
                    or rec.get("final_english")
                    or ""
                )
                english_parts.append(eng.strip())
            if not seg_ids:
                continue
            all_units.append(UnitScore(
                run=run_tag,
                unit_id=uid,
                segment_ids=seg_ids,
                latin_concat=" ".join(p for p in latin_parts if p),
                english_concat=" ".join(p for p in english_parts if p),
                reference=ref,
            ))

    print(f"Built {len(all_units)} (run × unit) scoring records "
          f"from {per_run_seg_count}")

    scorable = [u for u in all_units if u.latin_concat.strip() and u.english_concat.strip() and u.reference.strip()]
    skipped_no_ref = sum(1 for u in all_units if not u.reference.strip())
    skipped_empty = sum(1 for u in all_units if not u.english_concat.strip())
    print(
        f"Scorable units: {len(scorable)}  (skipped no_ref={skipped_no_ref}, "
        f"empty_english={skipped_empty})"
    )
    if not scorable:
        print("Nothing to score. Aborting.")
        return 2

    # ----- Run COMET --------------------------------------------------
    print(f"Loading model {MODEL!r}...")
    from comet import download_model, load_from_checkpoint  # type: ignore
    model_path = download_model(MODEL)
    model = load_from_checkpoint(model_path)

    payloads = [
        {"src": u.latin_concat, "mt": u.english_concat, "ref": u.reference}
        for u in scorable
    ]
    out = model.predict(payloads, batch_size=8, gpus=0)
    scores = list(out.scores) if hasattr(out, "scores") else list(out)
    for u, s in zip(scorable, scores):
        u.score = float(s)

    # ----- Persist per-unit scores -----------------------------------
    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with SCORES_JSONL.open("w", encoding="utf-8") as h:
        for u in all_units:
            h.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")

    # ----- Aggregate --------------------------------------------------
    scored = [u for u in scorable if u.score is not None]
    per_run: dict[str, list[float]] = {}
    for u in scored:
        per_run.setdefault(u.run, []).append(u.score)

    overall_mean = statistics.mean(u.score for u in scored)
    overall_median = statistics.median(u.score for u in scored)
    overall_stdev = (
        statistics.stdev(u.score for u in scored) if len(scored) > 1 else 0.0
    )
    overall_min = min(u.score for u in scored)
    overall_max = max(u.score for u in scored)

    per_run_stats: dict[str, dict] = {}
    for run_tag, vals in per_run.items():
        per_run_stats[run_tag] = {
            "n": len(vals),
            "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "min": min(vals),
            "max": max(vals),
        }

    # Cross-run variance per unit (how stable is the prompt across runs?)
    by_unit: dict[str, list[float]] = {}
    for u in scored:
        by_unit.setdefault(u.unit_id, []).append(u.score)
    unit_stats: list[tuple[str, float, float]] = [
        (uid, statistics.mean(scores), statistics.stdev(scores) if len(scores) > 1 else 0.0)
        for uid, scores in by_unit.items()
    ]
    unit_stats.sort(key=lambda x: x[2], reverse=True)
    top_unstable = unit_stats[:5]
    unit_means_sorted = sorted(unit_stats, key=lambda x: x[1])
    worst_5 = unit_means_sorted[:5]
    best_5 = unit_means_sorted[-5:][::-1]

    # ----- Markdown report -------------------------------------------
    lines: list[str] = []
    lines.append("# Whitaker baseline — Phase 1 scoring report (unit-level)")
    lines.append("")
    lines.append(
        f"Score: `translation_prompts_whitaker.py` over c1_ch1 "
        f"(p0030–p0031) scored at the **alignment-unit level** against "
        f"the 1849 Parker Society English reference using "
        f"[`Unbabel/wmt22-comet-da`](https://huggingface.co/Unbabel/wmt22-comet-da)."
    )
    lines.append("")
    lines.append(
        "Per-segment scoring was abandoned: a single Latin body-line "
        "fragment compared against its multi-line aligned reference "
        "scored systematically low because most of the reference was "
        "unaccounted for in the candidate. Unit-level scoring "
        "concatenates per-line candidates back into the sentence they "
        "belong to (per `chapter1_alignment.jsonl`) before scoring."
    )
    lines.append("")
    lines.append(f"- Alignment file: `{ALIGNMENT_PATH.relative_to(WORKSPACE_ROOT)}`")
    lines.append(f"- Runs scored: {', '.join(RUNS)}")
    lines.append(f"- Reference part: `{REFERENCE_PART}`")
    lines.append("")
    lines.append("## Aggregate (all runs)")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    lines.append(f"| (run × unit) records scored | {len(scored)} |")
    lines.append(f"| records skipped (no reference) | {skipped_no_ref} |")
    lines.append(f"| records skipped (empty english) | {skipped_empty} |")
    lines.append(f"| mean | **{overall_mean:.4f}** |")
    lines.append(f"| median | {overall_median:.4f} |")
    lines.append(f"| stdev | {overall_stdev:.4f} |")
    lines.append(f"| min | {overall_min:.4f} |")
    lines.append(f"| max | {overall_max:.4f} |")
    lines.append("")
    lines.append("## Per-run aggregates")
    lines.append("")
    lines.append("| run | n | mean | median | min | max |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for run_tag, stats in per_run_stats.items():
        lines.append(
            f"| {run_tag} | {stats['n']} | {stats['mean']:.4f} | "
            f"{stats['median']:.4f} | {stats['min']:.4f} | {stats['max']:.4f} |"
        )
    lines.append("")
    lines.append("## Run-to-run stability")
    lines.append("")
    lines.append(
        "Top-5 units with highest cross-run standard deviation — "
        "where the prompt is least deterministic:"
    )
    lines.append("")
    lines.append("| unit_id | mean score | stdev across runs |")
    lines.append("|---|---:|---:|")
    for uid, mean, stdev in top_unstable:
        lines.append(f"| {uid} | {mean:.4f} | {stdev:.4f} |")
    lines.append("")
    lines.append("## Lowest-scoring units (Phase 2 diagnostic starters)")
    lines.append("")
    lines.append("These are where the baseline diverges most from Parker Society. ")
    lines.append("Read the actual English vs reference in `whitaker_baseline_unit_scores.jsonl` ")
    lines.append("and classify by divergence category.")
    lines.append("")
    lines.append("| unit_id | mean score | stdev | run01 | run02 | run03 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for uid, mean, stdev in worst_5:
        scores_by_run = {u.run: u.score for u in scored if u.unit_id == uid}
        cells = []
        for run_tag in RUNS:
            v = scores_by_run.get(run_tag)
            cells.append(f"{v:.4f}" if v is not None else "n/a")
        lines.append(
            f"| {uid} | {mean:.4f} | {stdev:.4f} | "
            f"{cells[0]} | {cells[1]} | {cells[2]} |"
        )
    lines.append("")
    lines.append("## Highest-scoring units (where the baseline already matches Parker Society)")
    lines.append("")
    lines.append("| unit_id | mean score | stdev |")
    lines.append("|---|---:|---:|")
    for uid, mean, stdev in best_5:
        lines.append(f"| {uid} | {mean:.4f} | {stdev:.4f} |")
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- COMET-DA scores are in 0–1; for modern WMT translations, ")
    lines.append("  typical good scores land 0.75–0.90. 16C scholastic Latin → Victorian ")
    lines.append("  English is well out of distribution; absolute scores will be lower. ")
    lines.append("  **Only compare against other runs of this corpus, not against WMT benchmarks.**")
    lines.append("- The baseline mean is the number `v_next` needs to beat.")
    lines.append("- Low cross-run stdev = prompt is producing consistent output across runs. ")
    lines.append("  High stdev = same prompt yields meaningfully different translations.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {SCORES_JSONL}")
    print(f"Wrote {REPORT_MD}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
