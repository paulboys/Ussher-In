"""COMET-based scoring for translation A/B comparison.

Replaces (for *gating* decisions) the LLM-as-judge approach in
``ab_judge.py``. Use ``ab_judge.py`` for Phase 2 *diagnostic* analysis;
this module is for the headline pass/fail score.

Why COMET
---------
- Deterministic: same inputs → same outputs. LLM judges drift.
- Calibrated against millions of human MT-quality judgments.
- Free at the per-segment level once the model is downloaded.
- Reference-based (``wmt22-comet-da``) when a gold standard exists
  (Whitaker → 1849 Parker Society); reference-free (CometKiwi) when
  it doesn't (most of Ussher).

Caveat: COMET was trained on modern WMT data (news, Wikipedia). Our
domain (16th–17th-century scholastic Latin → Victorian scholarly
English) is well outside distribution. The directional verdict
should still be valid, but absolute scores may be uncalibrated.
Sanity-check on p0041 against the existing LLM-judge verdict before
trusting it on new data — see ``comet_sanity_p0041.py`` calling
``compare_runs``.

CLI
---
::

    # Reference-free (Kiwi) on two runs
    python comet_score.py \\
        v0_run.jsonl v1_run.jsonl \\
        --output comet_scores.jsonl \\
        --summary comet_summary.json \\
        --model wmt22-cometkiwi-da

    # Reference-based with Parker Society alignment
    python comet_score.py \\
        v0_run.jsonl v1_run.jsonl \\
        --output comet_scores.jsonl \\
        --summary comet_summary.json \\
        --model wmt22-comet-da \\
        --alignment 04_translation_work/ab/whitaker_ch1/chapter1_alignment.jsonl \\
        --reference-part whitaker_english
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
WORKSPACE_ROOT = _HERE.parent.parent  # .../UssherIn
ANNOTATIONS_DIR = WORKSPACE_ROOT / "08_working_scratch" / "phase3b" / "annotations"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _english_for(record: dict) -> str:
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def load_run(path: Path) -> dict[str, dict]:
    """Return ``{segment_id: record}`` from a segments JSONL artifact."""
    out: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            seg_id = rec.get("segment_id")
            if seg_id:
                out[str(seg_id)] = rec
    return out


# ---------------------------------------------------------------------------
# Alignment + reference lookup
# ---------------------------------------------------------------------------


def load_alignment(path: Path) -> list[dict]:
    """Read a chapter1_alignment.jsonl file."""
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def load_english_line_texts(
    line_ids: set[str], *, part: str
) -> dict[str, str]:
    """Map ``line_id`` -> ``text_gold`` by reading the relevant page JSONs."""
    pages: dict[str, list[str]] = {}
    for lid in line_ids:
        # line_id shape: p0041_body_l0001
        page = lid.split("_", 1)[0]
        pages.setdefault(page, []).append(lid)

    out: dict[str, str] = {}
    for page, ids in pages.items():
        ann_path = ANNOTATIONS_DIR / part / f"page_{page}.json"
        if not ann_path.exists():
            continue
        with ann_path.open("r", encoding="utf-8") as h:
            payload = json.load(h)
        wanted = set(ids)
        for region_name, entries in (payload.get("regions") or {}).items():
            for entry in entries or []:
                lid = entry.get("line_id")
                if lid in wanted:
                    out[lid] = (
                        entry.get("text_gold")
                        or entry.get("text_ocr_original")
                        or ""
                    )
    return out


def build_reference_lookup(
    alignment: list[dict], *, part: str
) -> dict[str, str]:
    """Return ``{latin_line_id: aligned_english_text}``.

    The English text for each alignment unit is the space-joined
    ``text_gold`` of its ``english_line_ids``. Every Latin line_id in
    the unit maps to that same English string (since the alignment is
    sentence-level, not line-level).
    """
    eng_ids_needed: set[str] = set()
    for unit in alignment:
        for eid in unit.get("english_line_ids") or []:
            eng_ids_needed.add(eid)
    eng_texts = load_english_line_texts(eng_ids_needed, part=part)

    out: dict[str, str] = {}
    for unit in alignment:
        eng_ids = unit.get("english_line_ids") or []
        eng_text = " ".join(
            (eng_texts.get(eid) or "").strip() for eid in eng_ids
        ).strip()
        for lid in unit.get("latin_line_ids") or []:
            out[lid] = eng_text
    return out


def segment_id_to_line_id(seg_id: str) -> str:
    """Strip the ``seg_`` prefix used by the runner."""
    return seg_id[4:] if seg_id.startswith("seg_") else seg_id


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class ScoredPair:
    segment_id: str
    latin: str
    v0_english: str
    v1_english: str
    reference: str = ""
    v0_score: float | None = None
    v1_score: float | None = None
    delta: float | None = None  # v1 - v0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "latin": self.latin,
            "reference": self.reference,
            "v0_english": self.v0_english,
            "v1_english": self.v1_english,
            "v0_score": self.v0_score,
            "v1_score": self.v1_score,
            "delta_v1_minus_v0": self.delta,
            "error": self.error,
        }


def _build_comet_records(
    pairs: Sequence[ScoredPair], *, reference_based: bool
) -> tuple[list[dict], list[dict]]:
    """Return the two payload lists (v0, v1) the COMET model expects."""
    v0_records: list[dict] = []
    v1_records: list[dict] = []
    for p in pairs:
        base = {"src": p.latin}
        if reference_based:
            base["ref"] = p.reference
        v0_records.append({**base, "mt": p.v0_english})
        v1_records.append({**base, "mt": p.v1_english})
    return v0_records, v1_records


def score_with_comet(
    pairs: list[ScoredPair],
    *,
    model_name: str = "Unbabel/wmt22-cometkiwi-da",
    batch_size: int = 8,
    gpus: int = 0,
) -> list[ScoredPair]:
    """Run COMET on a list of ``ScoredPair`` records, fill in scores.

    Loads the model lazily so the rest of this module is importable
    without COMET installed (useful for tests).
    """
    from comet import download_model, load_from_checkpoint  # type: ignore

    reference_based = "kiwi" not in model_name.lower()

    # Drop pairs with missing data so they don't crash COMET
    runnable = [
        p for p in pairs
        if p.latin.strip()
        and p.v0_english.strip()
        and p.v1_english.strip()
        and (not reference_based or p.reference.strip())
    ]
    for p in pairs:
        if p not in runnable and not p.error:
            p.error = (
                "missing reference" if reference_based and not p.reference.strip()
                else "missing english on one side" if not (p.v0_english.strip() and p.v1_english.strip())
                else "missing latin"
            )

    if not runnable:
        return pairs

    model_path = download_model(model_name)
    model = load_from_checkpoint(model_path)

    v0_records, v1_records = _build_comet_records(
        runnable, reference_based=reference_based
    )
    v0_out = model.predict(v0_records, batch_size=batch_size, gpus=gpus)
    v1_out = model.predict(v1_records, batch_size=batch_size, gpus=gpus)

    # COMET .predict returns an object with .scores (per-segment list)
    v0_scores = list(v0_out.scores) if hasattr(v0_out, "scores") else list(v0_out)
    v1_scores = list(v1_out.scores) if hasattr(v1_out, "scores") else list(v1_out)

    for p, s0, s1 in zip(runnable, v0_scores, v1_scores):
        p.v0_score = float(s0)
        p.v1_score = float(s1)
        p.delta = p.v1_score - p.v0_score

    return pairs


# ---------------------------------------------------------------------------
# Pair construction
# ---------------------------------------------------------------------------


def build_pairs(
    v0_path: Path,
    v1_path: Path,
    *,
    reference_lookup: dict[str, str] | None = None,
) -> list[ScoredPair]:
    """Build ``ScoredPair`` records for every segment shared between the two runs."""
    v0 = load_run(v0_path)
    v1 = load_run(v1_path)
    shared = sorted(set(v0) & set(v1))
    pairs: list[ScoredPair] = []
    for seg_id in shared:
        v0_rec = v0[seg_id]
        v1_rec = v1[seg_id]
        latin = (
            v0_rec.get("latin_text")
            or v1_rec.get("latin_text")
            or ""
        )
        v0_text = _english_for(v0_rec)
        v1_text = _english_for(v1_rec)
        ref = ""
        if reference_lookup is not None:
            line_id = segment_id_to_line_id(seg_id)
            ref = reference_lookup.get(line_id, "")
        pairs.append(ScoredPair(
            segment_id=seg_id,
            latin=latin,
            v0_english=v0_text,
            v1_english=v1_text,
            reference=ref,
        ))
    return pairs


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(pairs: Sequence[ScoredPair]) -> dict:
    """Reduce per-segment scores into a summary."""
    valid = [p for p in pairs if p.v0_score is not None and p.v1_score is not None]
    if not valid:
        return {
            "n_segments": len(pairs),
            "n_scored": 0,
            "n_errored": len(pairs),
        }

    v0_scores = [p.v0_score for p in valid]
    v1_scores = [p.v1_score for p in valid]
    deltas = [p.delta for p in valid]

    v1_wins = sum(1 for d in deltas if d > 0)
    v0_wins = sum(1 for d in deltas if d < 0)
    ties = sum(1 for d in deltas if d == 0)

    return {
        "n_segments": len(pairs),
        "n_scored": len(valid),
        "n_errored": len(pairs) - len(valid),
        "v0_mean": statistics.mean(v0_scores),
        "v0_median": statistics.median(v0_scores),
        "v1_mean": statistics.mean(v1_scores),
        "v1_median": statistics.median(v1_scores),
        "mean_delta_v1_minus_v0": statistics.mean(deltas),
        "v1_segment_wins": v1_wins,
        "v0_segment_wins": v0_wins,
        "ties": ties,
        "v1_win_rate": v1_wins / len(valid) if valid else 0.0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "COMET-based scoring for A/B prompt comparison. "
            "Reference-free (CometKiwi) by default; supply --alignment "
            "to use a reference-based COMET model."
        ),
    )
    parser.add_argument("v0_jsonl", type=Path, help="Baseline run artifact.")
    parser.add_argument("v1_jsonl", type=Path, help="Challenger run artifact.")
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Per-segment scores JSONL.",
    )
    parser.add_argument(
        "--summary", type=Path, default=None,
        help="Aggregate summary JSON.",
    )
    parser.add_argument(
        "--model", default="Unbabel/wmt22-cometkiwi-da",
        help=(
            "COMET model id on HuggingFace. Use 'Unbabel/wmt22-cometkiwi-da' "
            "for reference-free, 'Unbabel/wmt22-comet-da' for reference-based."
        ),
    )
    parser.add_argument(
        "--alignment", type=Path, default=None,
        help=(
            "Optional alignment JSONL (one row per unit with latin_line_ids "
            "and english_line_ids). Required when using a reference-based model."
        ),
    )
    parser.add_argument(
        "--reference-part", default="whitaker_english",
        help=(
            "Which phase3b/annotations/<part> directory to load reference "
            "English from. Defaults to whitaker_english."
        ),
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="COMET batch size. CPU default; raise on GPU.",
    )
    parser.add_argument(
        "--gpus", type=int, default=0,
        help="Number of GPUs to use (0 = CPU).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.v0_jsonl.exists():
        print(f"comet_score: {args.v0_jsonl} not found", file=sys.stderr)
        return 2
    if not args.v1_jsonl.exists():
        print(f"comet_score: {args.v1_jsonl} not found", file=sys.stderr)
        return 2

    reference_lookup: dict[str, str] | None = None
    reference_based = "kiwi" not in args.model.lower()
    if args.alignment:
        if not args.alignment.exists():
            print(
                f"comet_score: alignment file {args.alignment} not found",
                file=sys.stderr,
            )
            return 2
        alignment = load_alignment(args.alignment)
        reference_lookup = build_reference_lookup(
            alignment, part=args.reference_part
        )
    elif reference_based:
        print(
            f"comet_score: model {args.model} is reference-based but "
            f"--alignment was not provided",
            file=sys.stderr,
        )
        return 2

    pairs = build_pairs(
        args.v0_jsonl, args.v1_jsonl, reference_lookup=reference_lookup
    )
    pairs = score_with_comet(
        pairs,
        model_name=args.model,
        batch_size=args.batch_size,
        gpus=args.gpus,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for p in pairs:
            handle.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    summary = aggregate(pairs)
    summary["model"] = args.model
    summary["reference_based"] = reference_based
    summary["v0_path"] = str(args.v0_jsonl)
    summary["v1_path"] = str(args.v1_jsonl)
    if args.alignment:
        summary["alignment_path"] = str(args.alignment)

    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    n = summary.get("n_scored", 0)
    print(
        f"comet_score: scored={n}/{summary.get('n_segments', 0)}  "
        f"mean_v0={summary.get('v0_mean', 0):.4f}  "
        f"mean_v1={summary.get('v1_mean', 0):.4f}  "
        f"mean_delta_v1-v0={summary.get('mean_delta_v1_minus_v0', 0):+.4f}  "
        f"v1_segment_wins={summary.get('v1_segment_wins', 0)}  "
        f"v0_segment_wins={summary.get('v0_segment_wins', 0)}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ScoredPair",
    "aggregate",
    "build_pairs",
    "build_reference_lookup",
    "load_alignment",
    "load_english_line_texts",
    "load_run",
    "score_with_comet",
    "segment_id_to_line_id",
]
