"""Score whitaker_v2 runs and compare against the baseline.

Reads the 3 whitaker_v2 baseline runs on c1_ch1 (p0030-p0031), scores
each alignment unit (sentence-level) against the 1849 Parker Society
reference with reference-based COMET (``Unbabel/wmt22-comet-da``), and
diffs against the prior baseline's unit scores
(``whitaker_baseline_unit_scores.jsonl``).

Output
------
- ``04_translation_work/ab/whitaker_ch1/whitaker_v2_unit_scores.jsonl``
  one row per (run, alignment_unit).
- ``04_translation_work/ab/whitaker_ch1/whitaker_v2_vs_baseline_report.md``
  side-by-side comparison, per-unit deltas, headline aggregate diff.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import comet_score as cs


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V2_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0030_p0031" / "whitaker_v2"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
ALIGNMENT_PATH = SANITY_DIR / "chapter1_alignment.jsonl"
BASELINE_SCORES = SANITY_DIR / "whitaker_baseline_unit_scores.jsonl"

V2_SCORES_JSONL = SANITY_DIR / "whitaker_v2_unit_scores.jsonl"
REPORT_MD = SANITY_DIR / "whitaker_v2_vs_baseline_report.md"

RUNS = ("whitaker_v2_run01", "whitaker_v2_run02", "whitaker_v2_run03")
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

    def to_dict(self) -> dict:
        return {
            "run": self.run,
            "unit_id": self.unit_id,
            "segment_ids": self.segment_ids,
            "latin_concat": self.latin_concat,
            "english_concat": self.english_concat,
            "reference": self.reference,
            "score": self.score,
        }


def _score_runs(runs_dir: Path, run_tags: tuple[str, ...], unit_specs: list[tuple[str, list[str], str]]) -> list[UnitScore]:
    """Build per-(run, unit) records by gluing per-line segments back into
    sentences, then score in one batched COMET call.
    """
    all_units: list[UnitScore] = []
    for run_tag in run_tags:
        run_path = runs_dir / run_tag / "segments_with_translations.jsonl"
        if not run_path.exists():
            print(f"  [skip] missing {run_tag}: {run_path}")
            continue
        run_records = cs.load_run(run_path)
        seg_by_line = {
            cs.segment_id_to_line_id(sid): {**rec, "_segment_id": sid}
            for sid, rec in run_records.items()
        }
        for uid, lat_ids, ref in unit_specs:
            if not lat_ids:
                continue
            seg_ids, latin_parts, english_parts = [], [], []
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

    scorable = [u for u in all_units if u.latin_concat.strip() and u.english_concat.strip() and u.reference.strip()]
    if not scorable:
        return all_units

    print(f"Loading COMET model {MODEL!r}...")
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
    return all_units


def _load_baseline_scores(path: Path) -> dict[tuple[str, str], float]:
    """Return ``{(run, unit_id): score}`` from the baseline unit-scores JSONL."""
    out: dict[tuple[str, str], float] = {}
    with path.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("score") is None:
                continue
            out[(rec["run"], rec["unit_id"])] = float(rec["score"])
    return out


def main() -> int:
    if not ALIGNMENT_PATH.exists():
        print(f"missing alignment file: {ALIGNMENT_PATH}")
        return 2
    alignment = cs.load_alignment(ALIGNMENT_PATH)
    ref_lookup = cs.build_reference_lookup(alignment, part=REFERENCE_PART)

    # Build unit_id -> (latin_line_ids, reference text) spec list
    unit_specs: list[tuple[str, list[str], str]] = []
    for unit in alignment:
        uid = unit.get("unit_id") or "unknown_unit"
        lat_ids = unit.get("latin_line_ids") or []
        ref = ref_lookup.get(lat_ids[0], "") if lat_ids else ""
        unit_specs.append((uid, lat_ids, ref))

    print(f"Scoring v2 runs from {V2_DIR}...")
    v2_units = _score_runs(V2_DIR, RUNS, unit_specs)
    print(f"v2 records: {len(v2_units)}; scored: {sum(1 for u in v2_units if u.score is not None)}")

    # Persist v2 per-unit scores
    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with V2_SCORES_JSONL.open("w", encoding="utf-8") as h:
        for u in v2_units:
            h.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")

    # Load baseline scores
    if not BASELINE_SCORES.exists():
        print(f"missing baseline scores: {BASELINE_SCORES}")
        return 2
    baseline_by_key = _load_baseline_scores(BASELINE_SCORES)
    print(f"baseline records loaded: {len(baseline_by_key)}")

    # Build comparison records — match on unit_id only (run01 of v2 vs run01 of baseline)
    # but since the baseline runs were named whitaker_baseline_runNN we map by suffix.
    def _baseline_run_for(v2_run: str) -> str:
        # whitaker_v2_runNN -> whitaker_baseline_runNN
        suffix = v2_run.rsplit("_run", 1)[-1] if "_run" in v2_run else "01"
        return f"whitaker_baseline_run{suffix}"

    v2_scored = [u for u in v2_units if u.score is not None]
    paired: list[tuple[UnitScore, float | None]] = []
    for u in v2_scored:
        b_key = (_baseline_run_for(u.run), u.unit_id)
        paired.append((u, baseline_by_key.get(b_key)))

    # ----- Aggregates ----------------------------------------------------
    v2_scores = [u.score for u, _ in paired]
    base_scores = [b for _, b in paired if b is not None]
    deltas = [u.score - b for u, b in paired if b is not None]
    v2_mean = statistics.mean(v2_scores) if v2_scores else 0.0
    base_mean = statistics.mean(base_scores) if base_scores else 0.0
    delta_mean = statistics.mean(deltas) if deltas else 0.0
    delta_median = statistics.median(deltas) if deltas else 0.0
    n_v2_wins = sum(1 for d in deltas if d > 0)
    n_base_wins = sum(1 for d in deltas if d < 0)
    n_ties = sum(1 for d in deltas if d == 0)

    # Per-run aggregates
    v2_per_run: dict[str, list[float]] = {}
    base_per_run: dict[str, list[float]] = {}
    delta_per_run: dict[str, list[float]] = {}
    for u, b in paired:
        v2_per_run.setdefault(u.run, []).append(u.score)
        if b is not None:
            base_per_run.setdefault(u.run, []).append(b)
            delta_per_run.setdefault(u.run, []).append(u.score - b)

    # Per-unit aggregates (average across runs)
    by_unit_v2: dict[str, list[float]] = {}
    by_unit_base: dict[str, list[float]] = {}
    for u, b in paired:
        by_unit_v2.setdefault(u.unit_id, []).append(u.score)
        if b is not None:
            by_unit_base.setdefault(u.unit_id, []).append(b)

    unit_means: list[tuple[str, float, float, float]] = []  # uid, v2_mean, base_mean, delta
    for uid in sorted(by_unit_v2):
        v2_m = statistics.mean(by_unit_v2[uid])
        base_m = statistics.mean(by_unit_base[uid]) if uid in by_unit_base else float("nan")
        delta = v2_m - base_m
        unit_means.append((uid, v2_m, base_m, delta))
    unit_means.sort(key=lambda x: x[3])  # ascending by delta (biggest regressions first)

    # ----- Markdown report ------------------------------------------
    lines: list[str] = []
    lines.append("# whitaker_v2 vs baseline — Phase 3 A/B comparison")
    lines.append("")
    lines.append(
        f"Both prompts scored at the **alignment-unit level** against "
        f"the 1849 Parker Society reference using `Unbabel/wmt22-comet-da`."
    )
    lines.append("")
    lines.append("## Headline result")
    lines.append("")
    lines.append("| metric | baseline | v2 | delta |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| mean | {base_mean:.4f} | {v2_mean:.4f} | **{delta_mean:+.4f}** |")
    rel_change = (delta_mean / base_mean * 100) if base_mean else 0.0
    lines.append(f"| relative change | — | — | **{rel_change:+.2f}%** |")
    lines.append(f"| unit-wins for v2 | — | {n_v2_wins} | — |")
    lines.append(f"| unit-wins for baseline | {n_base_wins} | — | — |")
    lines.append(f"| ties | — | — | {n_ties} |")
    lines.append("")
    verdict = "v2 improves on baseline" if delta_mean > 0 else (
        "v2 regresses against baseline" if delta_mean < 0 else "v2 ties baseline"
    )
    lines.append(f"**Verdict:** {verdict}.")
    lines.append("")
    lines.append("## Per-run aggregates")
    lines.append("")
    lines.append("| run | baseline mean | v2 mean | delta |")
    lines.append("|---|---:|---:|---:|")
    for run_tag in RUNS:
        bm = statistics.mean(base_per_run[run_tag]) if base_per_run.get(run_tag) else float("nan")
        vm = statistics.mean(v2_per_run[run_tag]) if v2_per_run.get(run_tag) else float("nan")
        lines.append(f"| {run_tag} | {bm:.4f} | {vm:.4f} | {vm - bm:+.4f} |")
    lines.append("")
    lines.append("## Per-unit deltas (sorted: biggest regressions first, biggest improvements last)")
    lines.append("")
    lines.append("| unit_id | baseline mean | v2 mean | delta |")
    lines.append("|---|---:|---:|---:|")
    for uid, vm, bm, d in unit_means:
        bm_str = f"{bm:.4f}" if not (bm != bm) else "n/a"
        lines.append(f"| {uid} | {bm_str} | {vm:.4f} | {d:+.4f} |")
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **Positive delta** = v2 closer to Parker Society than baseline on that unit.")
    lines.append("- **Negative delta** = v2 farther from Parker Society than baseline (a regression).")
    lines.append("- Aspirational target was aggregate mean ≥ 0.78 (per diagnostic_categories.md).")
    lines.append("- If aggregate is positive but some units regressed, investigate the regressors ")
    lines.append("  segment-by-segment and consider ablating the responsible rule.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {V2_SCORES_JSONL}")
    print(f"Wrote {REPORT_MD}")
    print(f"\nHEADLINE: baseline={base_mean:.4f}  v2={v2_mean:.4f}  delta={delta_mean:+.4f}  "
          f"({rel_change:+.2f}%)  v2_wins={n_v2_wins}/{len(deltas)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
