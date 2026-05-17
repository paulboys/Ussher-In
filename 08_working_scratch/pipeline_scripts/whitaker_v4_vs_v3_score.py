"""Score whitaker_v4 runs and compare against v3, v2, and the baseline.

Four-way comparison: baseline -> v2 -> v3 -> v4. v4's primary test is
against v3 (immediate predecessor); v2 and baseline give the longer
trajectory. Mirrors `whitaker_v3_vs_v2_score.py`.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import comet_score as cs


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V4_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "p0030_p0031" / "whitaker_v4"
SANITY_DIR = WORKSPACE_ROOT / "04_translation_work" / "ab" / "whitaker_ch1"
ALIGNMENT_PATH = SANITY_DIR / "chapter1_alignment.jsonl"
V3_SCORES = SANITY_DIR / "whitaker_v3_unit_scores.jsonl"
V2_SCORES = SANITY_DIR / "whitaker_v2_unit_scores.jsonl"
BASELINE_SCORES = SANITY_DIR / "whitaker_baseline_unit_scores.jsonl"

V4_SCORES_JSONL = SANITY_DIR / "whitaker_v4_unit_scores.jsonl"
REPORT_MD = SANITY_DIR / "whitaker_v4_vs_v3_report.md"

RUNS = ("whitaker_v4_run01", "whitaker_v4_run02", "whitaker_v4_run03")
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
    missing = [p for p in (V3_SCORES, V2_SCORES, BASELINE_SCORES) if not p.exists()]
    if missing:
        print(f"missing prior scores: {missing}")
        return 2

    alignment = cs.load_alignment(ALIGNMENT_PATH)
    ref_lookup = cs.build_reference_lookup(alignment, part=REFERENCE_PART)
    unit_specs: list[tuple[str, list[str], str]] = []
    for unit in alignment:
        uid = unit.get("unit_id") or "unknown_unit"
        lat_ids = unit.get("latin_line_ids") or []
        ref = ref_lookup.get(lat_ids[0], "") if lat_ids else ""
        unit_specs.append((uid, lat_ids, ref))

    print("Scoring v4 runs...")
    v4_units = _score_runs(V4_DIR, RUNS, unit_specs)
    print(f"v4 records: {len(v4_units)}; scored: {sum(1 for u in v4_units if u.score is not None)}")

    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    with V4_SCORES_JSONL.open("w", encoding="utf-8") as h:
        for u in v4_units:
            h.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")

    v3_by_key = _load_prior_scores(V3_SCORES)
    v2_by_key = _load_prior_scores(V2_SCORES)
    base_by_key = _load_prior_scores(BASELINE_SCORES)
    print(f"v3 records: {len(v3_by_key)}; v2 records: {len(v2_by_key)}; baseline records: {len(base_by_key)}")

    v4_scored = [u for u in v4_units if u.score is not None]

    paired: list[dict] = []
    for u in v4_scored:
        s = _suffix(u.run)
        paired.append({
            "run_suffix": s,
            "unit_id": u.unit_id,
            "v4": u.score,
            "v3": v3_by_key.get((s, u.unit_id)),
            "v2": v2_by_key.get((s, u.unit_id)),
            "base": base_by_key.get((s, u.unit_id)),
        })

    v4_scores = [p["v4"] for p in paired]
    v3_scores = [p["v3"] for p in paired if p["v3"] is not None]
    v2_scores = [p["v2"] for p in paired if p["v2"] is not None]
    base_scores = [p["base"] for p in paired if p["base"] is not None]

    v4_mean = statistics.mean(v4_scores)
    v3_mean = statistics.mean(v3_scores)
    v2_mean = statistics.mean(v2_scores)
    base_mean = statistics.mean(base_scores)

    deltas_vs_v3 = [p["v4"] - p["v3"] for p in paired if p["v3"] is not None]
    deltas_vs_v2 = [p["v4"] - p["v2"] for p in paired if p["v2"] is not None]
    deltas_vs_base = [p["v4"] - p["base"] for p in paired if p["base"] is not None]

    n_v4_wins_v3 = sum(1 for d in deltas_vs_v3 if d > 0)
    n_v3_wins_v4 = sum(1 for d in deltas_vs_v3 if d < 0)
    n_v4_wins_v2 = sum(1 for d in deltas_vs_v2 if d > 0)
    n_v2_wins_v4 = sum(1 for d in deltas_vs_v2 if d < 0)
    n_v4_wins_base = sum(1 for d in deltas_vs_base if d > 0)
    n_base_wins_v4 = sum(1 for d in deltas_vs_base if d < 0)

    per_run: dict[str, dict[str, list[float]]] = {}
    for p in paired:
        d = per_run.setdefault(p["run_suffix"], {"base": [], "v2": [], "v3": [], "v4": []})
        if p["base"] is not None: d["base"].append(p["base"])
        if p["v2"] is not None: d["v2"].append(p["v2"])
        if p["v3"] is not None: d["v3"].append(p["v3"])
        d["v4"].append(p["v4"])

    by_unit: dict[str, dict[str, list[float]]] = {}
    for p in paired:
        d = by_unit.setdefault(p["unit_id"], {"base": [], "v2": [], "v3": [], "v4": []})
        if p["base"] is not None: d["base"].append(p["base"])
        if p["v2"] is not None: d["v2"].append(p["v2"])
        if p["v3"] is not None: d["v3"].append(p["v3"])
        d["v4"].append(p["v4"])

    unit_rows: list[tuple[str, float, float, float, float, float, float, float]] = []
    for uid, scores in by_unit.items():
        bm = statistics.mean(scores["base"]) if scores["base"] else float("nan")
        v2m = statistics.mean(scores["v2"]) if scores["v2"] else float("nan")
        v3m = statistics.mean(scores["v3"]) if scores["v3"] else float("nan")
        v4m = statistics.mean(scores["v4"])
        unit_rows.append((uid, bm, v2m, v3m, v4m, v4m - v3m, v4m - v2m, v4m - bm))
    unit_rows.sort(key=lambda x: x[5])  # ascending by v4-v3 delta

    lines: list[str] = []
    lines.append("# whitaker_v4 vs v3 vs v2 vs baseline — Phase 3 iter3 comparison")
    lines.append("")
    lines.append("Four-way comparison at the alignment-unit level using `Unbabel/wmt22-comet-da`.")
    lines.append("")
    lines.append("## Headline trajectory")
    lines.append("")
    lines.append("| metric | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    d_v3 = v4_mean - v3_mean
    d_v2 = v4_mean - v2_mean
    d_base = v4_mean - base_mean
    lines.append(
        f"| mean | {base_mean:.4f} | {v2_mean:.4f} | {v3_mean:.4f} | **{v4_mean:.4f}** | "
        f"**{d_v3:+.4f}** | **{d_v2:+.4f}** | **{d_base:+.4f}** |"
    )
    rel_v3 = (d_v3 / v3_mean * 100) if v3_mean else 0.0
    rel_v2 = (d_v2 / v2_mean * 100) if v2_mean else 0.0
    rel_base = (d_base / base_mean * 100) if base_mean else 0.0
    lines.append(
        f"| relative change | — | — | — | — | {rel_v3:+.2f}% | {rel_v2:+.2f}% | {rel_base:+.2f}% |"
    )
    lines.append(
        f"| v4 unit-wins | — | — | — | — | {n_v4_wins_v3}/{len(deltas_vs_v3)} | "
        f"{n_v4_wins_v2}/{len(deltas_vs_v2)} | {n_v4_wins_base}/{len(deltas_vs_base)} |"
    )
    lines.append(f"| v4 unit-losses | — | — | — | — | {n_v3_wins_v4} | {n_v2_wins_v4} | {n_base_wins_v4} |")
    lines.append("")
    def _v(delta: float, name: str) -> str:
        if delta > 0: return f"v4 improves on {name}"
        if delta < 0: return f"v4 regresses against {name}"
        return f"v4 ties {name}"
    lines.append(f"**Verdict (vs v3):** {_v(d_v3, 'v3')}.")
    lines.append(f"**Verdict (vs v2):** {_v(d_v2, 'v2')}.")
    lines.append(f"**Verdict (vs baseline):** {_v(d_base, 'baseline')}.")
    lines.append("")
    lines.append("## Per-run aggregates")
    lines.append("")
    lines.append("| run | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in sorted(per_run.keys()):
        d = per_run[s]
        bm = statistics.mean(d["base"]) if d["base"] else float("nan")
        v2m = statistics.mean(d["v2"]) if d["v2"] else float("nan")
        v3m = statistics.mean(d["v3"]) if d["v3"] else float("nan")
        v4m = statistics.mean(d["v4"]) if d["v4"] else float("nan")
        lines.append(
            f"| run{s} | {bm:.4f} | {v2m:.4f} | {v3m:.4f} | {v4m:.4f} | "
            f"{v4m - v3m:+.4f} | {v4m - v2m:+.4f} | {v4m - bm:+.4f} |"
        )
    lines.append("")
    lines.append("## Per-unit (sorted: biggest v4-vs-v3 regressions first, biggest improvements last)")
    lines.append("")
    lines.append("| unit_id | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for uid, bm, v2m, v3m, v4m, dv3, dv2, dbase in unit_rows:
        def _s(x: float) -> str:
            return f"{x:.4f}" if not (x != x) else "n/a"
        lines.append(
            f"| {uid} | {_s(bm)} | {_s(v2m)} | {_s(v3m)} | {v4m:.4f} | "
            f"{dv3:+.4f} | {dv2:+.4f} | {dbase:+.4f} |"
        )
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **v4 − v3** is the primary test: does slimming Rule 2c restore the lost ground?")
    lines.append("- **v4 − v2** checks whether v4 regains the v2 ceiling (v2 was the prior best).")
    lines.append("- **v4 − baseline** is cumulative progress since the start of Phase 3.")
    lines.append("- Watch unit-run01 for ch1_u009/u010/u012/u013 specifically — the v3 segment-")
    lines.append("  boundary leakage diagnosis predicts those should normalize in v4.")
    lines.append("- Aspirational target (per diagnostic_categories.md) was aggregate mean ≥ 0.78.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {V4_SCORES_JSONL}")
    print(f"Wrote {REPORT_MD}")
    print(f"\nHEADLINE: base={base_mean:.4f}  v2={v2_mean:.4f}  v3={v3_mean:.4f}  v4={v4_mean:.4f}  "
          f"d(v4-v3)={d_v3:+.4f} ({rel_v3:+.2f}%)  d(v4-v2)={d_v2:+.4f} ({rel_v2:+.2f}%)  "
          f"d(v4-base)={d_base:+.4f} ({rel_base:+.2f}%)")
    print(f"          v4-wins-vs-v3={n_v4_wins_v3}/{len(deltas_vs_v3)}  "
          f"v4-wins-vs-v2={n_v4_wins_v2}/{len(deltas_vs_v2)}  "
          f"v4-wins-vs-base={n_v4_wins_base}/{len(deltas_vs_base)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
