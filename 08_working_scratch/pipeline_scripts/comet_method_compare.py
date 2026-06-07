"""CometKiwi comparison of the two literal translation methods, sentence-unit.

Compares, per sentence (reference-free CometKiwi):
  v0 = line-by-line literal, reassembled per sentence via source_line_ids
  v1 = sentence-level literal (one translation per whole sentence)

The sentence is the common unit: both candidates are scored against the same
sentence-Latin source. The line-by-line English is stitched together from the
constituent lines of each sentence (the sentence segmenter recorded which
line_ids compose each sentence), so the two methods are compared on identical
source spans. Sentence-sized inputs keep CometKiwi inside its 512-token window
(no page-level truncation) and on the granularity it was trained for.

This is literal-vs-literal — the polish layer is deliberately excluded.

Usage
-----
    python comet_method_compare.py [--part part1]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from comet_score import ScoredPair, score_with_comet  # noqa: E402

WORKSPACE_ROOT = _HERE.parent.parent
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"
_DEFAULT_OUT = WORKSPACE_ROOT / "08_working_scratch" / "phase3b"


def _latest_english(rec: dict) -> str:
    hist = rec.get("translation_history") or []
    if hist:
        t = (hist[-1] or {}).get("english") or ""
        if t.strip():
            return t
    return rec.get("final_english") or ""


def load_lineby_english(part: str) -> dict[str, str]:
    """Map line_id (e.g. 'p0036_body_l0007') -> line-by-line English."""
    path = ARTIFACTS_DIR / part / "segments_with_translations.jsonl"
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        sid = rec.get("segment_id") or ""
        # segment_id is 'seg_' + line_id; key by the bare line_id
        line_id = sid[4:] if sid.startswith("seg_") else sid
        out[line_id] = _latest_english(rec).strip()
    return out


def load_sentences(part: str) -> list[dict]:
    """Return sentence body records (segment_type body) from the sentence run."""
    path = ARTIFACTS_DIR / part / "segments_sentences.jsonl"
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        if rec.get("segment_type") == "footnote":
            continue
        out.append(rec)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="CometKiwi: line-by-line vs sentence literal, per sentence."
    )
    ap.add_argument("--part", default="part1")
    ap.add_argument("--output", type=Path,
                    default=_DEFAULT_OUT / "comet_lineby_vs_sentence.jsonl")
    ap.add_argument("--summary", type=Path,
                    default=_DEFAULT_OUT / "comet_lineby_vs_sentence_summary.json")
    args = ap.parse_args(argv)

    lineby = load_lineby_english(args.part)
    sentences = load_sentences(args.part)

    pairs: list[ScoredPair] = []
    unmatched_lines: list[str] = []
    for s in sentences:
        sid = s.get("segment_id") or ""
        latin = (s.get("latin_text") or "").strip()
        v1 = _latest_english(s).strip()
        src_line_ids = s.get("source_line_ids") or []
        parts: list[str] = []
        for lid in src_line_ids:
            if lid in lineby:
                parts.append(lineby[lid])
            else:
                unmatched_lines.append(lid)
        v0 = " ".join(p for p in parts if p).strip()
        pairs.append(ScoredPair(
            segment_id=sid, latin=latin, v0_english=v0, v1_english=v1,
        ))

    if unmatched_lines:
        print(f"WARN: {len(unmatched_lines)} source line(s) not found in "
              f"line-by-line artifact: {unmatched_lines[:5]}...", file=sys.stderr)

    pairs = score_with_comet(pairs)

    scored = [p for p in pairs if p.v0_score is not None and p.v1_score is not None]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    v0s = [p.v0_score for p in scored]
    v1s = [p.v1_score for p in scored]
    v1_wins = sum(1 for p in scored if p.v1_score > p.v0_score)
    v0_wins = sum(1 for p in scored if p.v0_score > p.v1_score)
    ties = sum(1 for p in scored if p.v0_score == p.v1_score)

    summary = {
        "n_sentences": len(pairs),
        "n_scored": len(scored),
        "n_errored": len(pairs) - len(scored),
        "v0_label": "line-by-line literal (stitched per sentence)",
        "v1_label": "sentence-level literal",
        "v0_mean": statistics.mean(v0s) if v0s else None,
        "v1_mean": statistics.mean(v1s) if v1s else None,
        "v0_median": statistics.median(v0s) if v0s else None,
        "v1_median": statistics.median(v1s) if v1s else None,
        "mean_delta_v1_minus_v0": (statistics.mean(v1s) - statistics.mean(v0s)) if v0s else None,
        "v1_sentence_wins": v1_wins,
        "v0_sentence_wins": v0_wins,
        "ties": ties,
        "model": "Unbabel/wmt22-cometkiwi-da",
        "reference_based": False,
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Scored {len(scored)}/{len(pairs)} sentences\n")
    print(f"v0 (line-by-line) mean: {summary['v0_mean']:.4f}  median: {summary['v0_median']:.4f}")
    print(f"v1 (sentence)     mean: {summary['v1_mean']:.4f}  median: {summary['v1_median']:.4f}")
    print(f"delta (v1-v0): {summary['mean_delta_v1_minus_v0']:+.4f}")
    print(f"sentence wins — v0: {v0_wins}  v1: {v1_wins}  ties: {ties}")
    print(f"\nOutput:  {args.output}")
    print(f"Summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
