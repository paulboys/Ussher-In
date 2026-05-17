"""Score whitaker_v3 runs and compare against v2 and the baseline.

Three-way comparison: baseline → v2 → v3. For each alignment unit
(sentence-level) we get three scores per run; aggregate per-unit and
overall. Produces a report showing v3's delta against v2 (immediate
predecessor) AND against the original baseline (trajectory).
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import comet_score as cs


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V3_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0030_p0031" / "whitaker_v3"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
ALIGNMENT_PATH = SANITY_DIR / "chapter1_alignment.jsonl"
V2_SCORES = SANITY_DIR / "whitaker_v2_unit_scores.jsonl"
BASELINE_SCORES = SANITY_DIR / "whitaker_baseline_unit_scores.jsonl"

V3_SCORES_JSONL = SANITY_DIR / "whitaker_v3_unit_scores.jsonl"
REPORT_MD = SANITY_DIR / "whitaker_v3_vs_v2_report.md"

RUNS = ("whitaker_v3_run01", "whitaker_v3_run02", "whitaker_v3_run03")
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


def _load_prior_scores(path: Path) -> dict[tuple[str, str], float]:
    """Return ``{(run_suffix, unit_id): score}`` for cross-version pairing."""
    out: dict[tuple[str, str], float] = {}
    with path.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("score") is None:
                continue
            suffix = rec["run"].rsplit("_run", 1)[-1] if "_run" in rec["run"] else "01"
            out[(suffix, rec["unit_id"])] = float(rec["score"])
    return out


def _suffix(run: str) -> str:
    return run.rsplit("_run", 1)[-1] if "_run" in run else "01"


def main() -> int:
    if not ALIGNMENT_PATH.exists():
        print(f"missing alignment: {ALIGNMENT_PATH}")
        return 2
    if not V2_SCORES.exists() or not BASELINE_SCORES.exists():
        print(f"missing prior scores: v2={V2_SCORES.exists()} base={BASELINE_SCORES.exists()}")
        return 2

    alignment = cs.load_alignment(ALIGNMENT_PATH)
    ref_lookup = cs.build_reference_lookup(alignment, part=REFERENCE_PART)
    unit_specs: list[tuple[str, list[str], str]] = []
    for unit in alignment:
        uid = unit.get("unit_id") or "unknown_unit"
        lat_ids = unit.get("latin_line_ids") or []
        ref = ref_lookup.get(lat_ids[0], "") if lat_ids else ""
        unit_specs.append((uid, lat_ids, ref))

    print("Scoring v3 runs...")
    v3_units = _score_runs(V3_DIR, RUNS, unit_specs)
    print(f"v3 records: {len(v3_units)}; scored: {sum(1 for u in v3_units if u.score is not None)}")

    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with V3_SCORES_JSONL.open("w", encoding="utf-8") as h:
        for u in v3_units:
            h.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")

    v2_by_key = _load_prior_scores(V2_SCORES)
    base_by_key = _load_prior_scores(BASELINE_SCORES)
    print(f"v2 records: {len(v2_by_key)}; baseline records: {len(base_by_key)}")

    v3_scored = [u for u in v3_units if u.score is not None]

    # Three-way pairing
    paired: list[dict] = []
    for u in v3_scored:
        s = _suffix(u.run)
        paired.append({
            "run_suffix": s,
            "unit_id": u.unit_id,
            "v3": u.score,
            "v2": v2_by_key.get((s, u.unit_id)),
            "base": base_by_key.get((s, u.unit_id)),
        })

    # Aggregates
    v3_scores = [p["v3"] for p in paired]
    v2_scores = [p["v2"] for p in paired if p["v2"] is not None]
    base_scores = [p["base"] for p in paired if p["base"] is not None]

    v3_mean = statistics.mean(v3_scores)
    v2_mean = statistics.mean(v2_scores)
    base_mean = statistics.mean(base_scores)

    # Deltas vs v2 (immediate predecessor) and vs baseline (trajectory)
    deltas_vs_v2 = [p["v3"] - p["v2"] for p in paired if p["v2"] is not None]
    deltas_vs_base = [p["v3"] - p["base"] for p in paired if p["base"] is not None]

    n_v3_wins_v2 = sum(1 for d in deltas_vs_v2 if d > 0)
    n_v2_wins_v3 = sum(1 for d in deltas_vs_v2 if d < 0)
    n_v3_wins_base = sum(1 for d in deltas_vs_base if d > 0)
    n_base_wins_v3 = sum(1 for d in deltas_vs_base if d < 0)

    # Per-run aggregates
    per_run: dict[str, dict[str, list[float]]] = {}
    for p in paired:
        d = per_run.setdefault(p["run_suffix"], {"base": [], "v2": [], "v3": []})
        if p["base"] is not None:
            d["base"].append(p["base"])
        if p["v2"] is not None:
            d["v2"].append(p["v2"])
        d["v3"].append(p["v3"])

    # Per-unit means (averaged across runs)
    by_unit: dict[str, dict[str, list[float]]] = {}
    for p in paired:
        d = by_unit.setdefault(p["unit_id"], {"base": [], "v2": [], "v3": []})
        if p["base"] is not None:
            d["base"].append(p["base"])
        if p["v2"] is not None:
            d["v2"].append(p["v2"])
        d["v3"].append(p["v3"])

    unit_rows: list[tuple[str, float, float, float, float, float]] = []
    for uid, scores in by_unit.items():
        bm = statistics.mean(scores["base"]) if scores["base"] else float("nan")
        v2m = statistics.mean(scores["v2"]) if scores["v2"] else float("nan")
        v3m = statistics.mean(scores["v3"])
        unit_rows.append((uid, bm, v2m, v3m, v3m - v2m, v3m - bm))
    unit_rows.sort(key=lambda x: x[4])  # ascending by v3-v2 delta

    # ----- Markdown report ------------------------------------------
    lines: list[str] = []
    lines.append("# whitaker_v3 vs v2 vs baseline — Phase 3 iter2 comparison")
    lines.append("")
    lines.append("Three-way comparison at the alignment-unit level using `Unbabel/wmt22-comet-da`.")
    lines.append("")
    lines.append("## Headline trajectory")
    lines.append("")
    lines.append("| metric | baseline | v2 | v3 | v3 − v2 | v3 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    d_v2 = v3_mean - v2_mean
    d_base = v3_mean - base_mean
    lines.append(
        f"| mean | {base_mean:.4f} | {v2_mean:.4f} | **{v3_mean:.4f}** "
        f"| **{d_v2:+.4f}** | **{d_base:+.4f}** |"
    )
    rel_v2 = (d_v2 / v2_mean * 100) if v2_mean else 0.0
    rel_base = (d_base / base_mean * 100) if base_mean else 0.0
    lines.append(
        f"| relative change | — | — | — | {rel_v2:+.2f}% | {rel_base:+.2f}% |"
    )
    lines.append(f"| v3 unit-wins | — | — | — | {n_v3_wins_v2}/{len(deltas_vs_v2)} | {n_v3_wins_base}/{len(deltas_vs_base)} |")
    lines.append(f"| v3 unit-losses | — | — | — | {n_v2_wins_v3} | {n_base_wins_v3} |")
    lines.append("")
    if d_v2 > 0:
        verdict_v2 = "v3 improves on v2"
    elif d_v2 < 0:
        verdict_v2 = "v3 regresses against v2"
    else:
        verdict_v2 = "v3 ties v2"
    lines.append(f"**Verdict (vs v2):** {verdict_v2}.")
    if d_base > 0:
        verdict_b = "v3 still improves on baseline"
    elif d_base < 0:
        verdict_b = "v3 has fallen back below baseline"
    else:
        verdict_b = "v3 ties baseline"
    lines.append(f"**Verdict (vs baseline):** {verdict_b}.")
    lines.append("")
    lines.append("## Per-run aggregates")
    lines.append("")
    lines.append("| run | baseline | v2 | v3 | v3 − v2 | v3 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in sorted(per_run.keys()):
        d = per_run[s]
        bm = statistics.mean(d["base"]) if d["base"] else float("nan")
        v2m = statistics.mean(d["v2"]) if d["v2"] else float("nan")
        v3m = statistics.mean(d["v3"]) if d["v3"] else float("nan")
        lines.append(
            f"| run{s} | {bm:.4f} | {v2m:.4f} | {v3m:.4f} | "
            f"{v3m - v2m:+.4f} | {v3m - bm:+.4f} |"
        )
    lines.append("")
    lines.append("## Per-unit (sorted: biggest v3-vs-v2 regressions first, biggest improvements last)")
    lines.append("")
    lines.append("| unit_id | baseline | v2 | v3 | v3 − v2 | v3 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for uid, bm, v2m, v3m, dv2, dbase in unit_rows:
        bm_s = f"{bm:.4f}" if not (bm != bm) else "n/a"
        v2_s = f"{v2m:.4f}" if not (v2m != v2m) else "n/a"
        lines.append(
            f"| {uid} | {bm_s} | {v2_s} | {v3m:.4f} | {dv2:+.4f} | {dbase:+.4f} |"
        )
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **v3 − v2** is the immediate iteration's contribution.")
    lines.append("- **v3 − baseline** is cumulative progress since the start of Phase 3.")
    lines.append("- Aspirational target (per diagnostic_categories.md) was aggregate mean ≥ 0.78.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {V3_SCORES_JSONL}")
    print(f"Wrote {REPORT_MD}")
    print(f"\nHEADLINE: base={base_mean:.4f}  v2={v2_mean:.4f}  v3={v3_mean:.4f}  "
          f"d(v3-v2)={d_v2:+.4f} ({rel_v2:+.2f}%)  d(v3-base)={d_base:+.4f} ({rel_base:+.2f}%)")
    print(f"          v3-wins-vs-v2={n_v3_wins_v2}/{len(deltas_vs_v2)}  "
          f"v3-wins-vs-base={n_v3_wins_base}/{len(deltas_vs_base)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
