"""Score whitaker_v4 ch2 runs against the Parker Society alignment.

Phase 4 generalization check: does v4's ch1 win (mean COMET-DA 0.7651)
hold up on a chapter it wasn't tuned on? Only v4 was run on ch2 — no
prior versions to pair against — so the comparison is intra-version:
v4 on ch2 vs. v4 on ch1.

Pass condition (plan.md §5 Phase 4): aggregate mean within ~0.01 of
the ch1 mean, and no segment-boundary leakage recurrence.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import comet_score as cs


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V4_CH2_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0032_p0035" / "whitaker_v4"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
ALIGNMENT_PATH = SANITY_DIR / "chapter2_alignment.jsonl"

V4_CH2_SCORES_JSONL = SANITY_DIR / "whitaker_v4_ch2_unit_scores.jsonl"
REPORT_MD = SANITY_DIR / "whitaker_v4_ch2_report.md"

RUNS = ("whitaker_v4_ch2_run01", "whitaker_v4_ch2_run02", "whitaker_v4_ch2_run03")
MODEL = "Unbabel/wmt22-comet-da"
REFERENCE_PART = "whitaker_english"

# Ch1 reference means (from whitaker_v4_vs_v3_report.md) — for context only.
CH1_MEANS = {"baseline": 0.7494, "v2": 0.7612, "v3": 0.7557, "v4": 0.7651}
GATE_TOLERANCE = 0.01  # |ch2 - ch1| <= this to pass Phase 4 generalization


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


def _suffix(run: str) -> str:
    return run.rsplit("_run", 1)[-1] if "_run" in run else "01"


def main() -> int:
    if not ALIGNMENT_PATH.exists():
        print(f"missing alignment: {ALIGNMENT_PATH}")
        return 2

    alignment = cs.load_alignment(ALIGNMENT_PATH)
    ref_lookup = cs.build_reference_lookup(alignment, part=REFERENCE_PART)
    unit_specs: list[tuple[str, list[str], str]] = []
    for unit in alignment:
        uid = unit.get("unit_id") or "unknown_unit"
        lat_ids = unit.get("latin_line_ids") or []
        ref = ref_lookup.get(lat_ids[0], "") if lat_ids else ""
        unit_specs.append((uid, lat_ids, ref))

    print("Scoring v4 ch2 runs...")
    units = _score_runs(V4_CH2_DIR, RUNS, unit_specs)
    print(f"records: {len(units)}; scored: {sum(1 for u in units if u.score is not None)}")

    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with V4_CH2_SCORES_JSONL.open("w", encoding="utf-8") as h:
        for u in units:
            h.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")

    scored = [u for u in units if u.score is not None]
    if not scored:
        print("no scored records — aborting report")
        return 1

    overall_mean = statistics.mean(u.score for u in scored)
    ch1_v4 = CH1_MEANS["v4"]
    delta_vs_ch1 = overall_mean - ch1_v4
    abs_delta = abs(delta_vs_ch1)
    gate_pass = abs_delta <= GATE_TOLERANCE

    # Per-run aggregates
    per_run: dict[str, list[float]] = {}
    for u in scored:
        per_run.setdefault(_suffix(u.run), []).append(u.score)

    # Per-unit aggregates (mean across runs)
    by_unit: dict[str, list[float]] = {}
    for u in scored:
        by_unit.setdefault(u.unit_id, []).append(u.score)
    unit_rows = [(uid, statistics.mean(s), min(s), max(s), max(s) - min(s))
                 for uid, s in by_unit.items()]
    unit_rows.sort(key=lambda r: r[1])  # ascending by mean — worst first

    # Variance signal — wide intra-run spread on the same unit was the
    # v3 segment-boundary-leakage tell.
    high_variance = [r for r in unit_rows if r[4] >= 0.05]

    lines: list[str] = []
    lines.append("# whitaker_v4 ch2 — Phase 4 generalization check")
    lines.append("")
    lines.append("v4 was tuned on ch1; this run scores it on ch2 (no prior versions on ch2 to pair against).")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append("| corpus | mean | n_units (×3 runs) |")
    lines.append("|---|---:|---:|")
    lines.append(f"| ch1 (v4, from prior report) | {ch1_v4:.4f} | 45 |")
    lines.append(f"| **ch2 (v4, this report)**  | **{overall_mean:.4f}** | {len(scored)} |")
    lines.append(f"| delta (ch2 − ch1)         | {delta_vs_ch1:+.4f} | — |")
    lines.append("")
    lines.append(f"**Generalization gate** (|ch2 − ch1| ≤ {GATE_TOLERANCE:.2f}): "
                 f"{'PASS' if gate_pass else 'FAIL'} (|delta| = {abs_delta:.4f})")
    lines.append("")
    lines.append("## Trajectory context (ch1 baselines, for reference only)")
    lines.append("")
    lines.append("| version | ch1 mean |")
    lines.append("|---|---:|")
    for k in ("baseline", "v2", "v3", "v4"):
        lines.append(f"| {k} | {CH1_MEANS[k]:.4f} |")
    lines.append("")
    lines.append("## Per-run aggregates (ch2)")
    lines.append("")
    lines.append("| run | mean | n_units |")
    lines.append("|---|---:|---:|")
    for s in sorted(per_run.keys()):
        vals = per_run[s]
        lines.append(f"| run{s} | {statistics.mean(vals):.4f} | {len(vals)} |")
    lines.append("")
    lines.append("## Per-unit (sorted worst-first)")
    lines.append("")
    lines.append("| unit_id | mean | min | max | spread |")
    lines.append("|---|---:|---:|---:|---:|")
    for uid, mean, lo, hi, spread in unit_rows:
        bold = "**" if spread >= 0.05 else ""
        lines.append(f"| {uid} | {mean:.4f} | {lo:.4f} | {hi:.4f} | {bold}{spread:.4f}{bold} |")
    lines.append("")
    lines.append("## Variance check (segment-boundary-leakage tell)")
    lines.append("")
    if high_variance:
        lines.append(f"Units with intra-run spread ≥ 0.05 (potential boundary leakage): {len(high_variance)}")
        for uid, mean, lo, hi, spread in high_variance:
            lines.append(f"- `{uid}`: spread {spread:.4f}  (min {lo:.4f}, max {hi:.4f})")
        lines.append("")
        lines.append("Inspect these unit translations across runs to confirm — v3's tell was")
        lines.append("identical-unit translations starting with a fragment of the previous unit's text.")
    else:
        lines.append("No units with spread ≥ 0.05. Stability looks ch1-like (v4 ch1 max spread was ~0.003).")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if gate_pass:
        lines.append(f"- v4 generalizes from ch1 to ch2: mean within ±{GATE_TOLERANCE:.2f}. The Phase 3")
        lines.append("  improvements are not ch1-specific. Plan §5 Phase 4 gate cleared.")
    else:
        direction = "below" if delta_vs_ch1 < 0 else "above"
        lines.append(f"- v4 ch2 mean is {abs_delta:.4f} {direction} ch1 — outside the ±0.01 gate.")
        if delta_vs_ch1 < 0:
            lines.append("  Investigate worst-performing ch2 units for systematic register or content issues that")
            lines.append("  ch1 didn't exhibit. The ch1 wins may have been corpus-specific.")
        else:
            lines.append("  v4 is *better* on ch2 than ch1 — ch1's persistent low-scorers (u002, u009) may have")
            lines.append("  capped ch1's mean. Still worth checking that ch2's wins aren't paraphrase-luck.")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {V4_CH2_SCORES_JSONL}")
    print(f"Wrote {REPORT_MD}")
    print(f"\nHEADLINE: ch2 mean = {overall_mean:.4f}  ch1 mean = {ch1_v4:.4f}  delta = {delta_vs_ch1:+.4f}  "
          f"gate ({GATE_TOLERANCE:.2f}) = {'PASS' if gate_pass else 'FAIL'}")
    if high_variance:
        print(f"          variance flags: {len(high_variance)} unit(s) with spread ≥ 0.05")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
