"""CometKiwi: cross-page whole-sentence vs per-page fragments, at the 12 seams.

The cross-page run merges a seam-spanning sentence into one unit; the per-page
run split it into the trailing fragment of page N plus the leading fragment of
page N+1. This compares, for each cross-page sentence (``spans_pages`` > 1):

  src = the full cross-page sentence Latin
  v0  = per-page: the fragment translations stitched in reading order
  v1  = cross-page: the whole-sentence translation

Both candidates are scored against the same source, so the delta isolates the
seam effect — exactly the thing the cross-page change was built to fix.

Usage
-----
    python comet_xpage_compare.py [--part part1]
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


def _load_body(path: Path) -> list[dict]:
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
        description="CometKiwi: cross-page whole sentence vs per-page fragments."
    )
    ap.add_argument("--part", default="part1")
    ap.add_argument("--output", type=Path,
                    default=_DEFAULT_OUT / "comet_xpage_vs_perpage.jsonl")
    ap.add_argument("--summary", type=Path,
                    default=_DEFAULT_OUT / "comet_xpage_vs_perpage_summary.json")
    args = ap.parse_args(argv)

    xpage = _load_body(ARTIFACTS_DIR / args.part / "segments_sentences_xpage.jsonl")
    perpage = _load_body(ARTIFACTS_DIR / args.part / "segments_sentences.jsonl")

    # Index per-page sentences by their line set for subset matching.
    perpage_idx = [
        {
            "seg_id": r.get("segment_id"),
            "page_id": r.get("page_id"),
            "seq": r.get("seq") or 0,
            "lines": set(r.get("source_line_ids") or []),
            "english": _latest_english(r).strip(),
        }
        for r in perpage
    ]

    pairs: list[ScoredPair] = []
    skipped: list[str] = []
    for x in xpage:
        spans = x.get("spans_pages") or []
        if len(spans) <= 1:
            continue  # only the seam-spanning sentences differ between methods
        x_lines = set(x.get("source_line_ids") or [])
        # Per-page fragments whose lines are wholly inside this sentence.
        frags = [p for p in perpage_idx if p["lines"] and p["lines"] <= x_lines]
        frags.sort(key=lambda p: (p["page_id"], p["seq"]))
        covered = set().union(*[p["lines"] for p in frags]) if frags else set()
        if covered != x_lines:
            # Per-page segmentation did not tile this sentence exactly; skip
            # rather than score a mismatched stitch.
            skipped.append(f"{x.get('segment_id')} (covered {len(covered)}/{len(x_lines)} lines)")
            continue
        v0 = " ".join(p["english"] for p in frags if p["english"]).strip()
        v1 = _latest_english(x).strip()
        pairs.append(ScoredPair(
            segment_id=x.get("segment_id"),
            latin=(x.get("latin_text") or "").strip(),
            v0_english=v0, v1_english=v1,
        ))

    if skipped:
        print(f"WARN: skipped {len(skipped)} sentence(s) with imperfect "
              f"per-page tiling: {skipped}", file=sys.stderr)

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
        "n_cross_page_sentences": len(pairs),
        "n_scored": len(scored),
        "v0_label": "per-page fragments stitched",
        "v1_label": "cross-page whole sentence",
        "v0_mean": statistics.mean(v0s) if v0s else None,
        "v1_mean": statistics.mean(v1s) if v1s else None,
        "v0_median": statistics.median(v0s) if v0s else None,
        "v1_median": statistics.median(v1s) if v1s else None,
        "mean_delta_v1_minus_v0": (statistics.mean(v1s) - statistics.mean(v0s)) if v0s else None,
        "v1_wins": v1_wins,
        "v0_wins": v0_wins,
        "ties": ties,
        "model": "Unbabel/wmt22-cometkiwi-da",
        "reference_based": False,
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Scored {len(scored)}/{len(pairs)} cross-page sentences\n")
    print(f"{'sentence':20s} {'v0 frag':>9s} {'v1 whole':>9s} {'delta':>8s}")
    for p in scored:
        print(f"{p.segment_id:20s} {p.v0_score:9.4f} {p.v1_score:9.4f} "
              f"{p.v1_score - p.v0_score:+8.4f}")
    print()
    print(f"v0 (per-page fragments)  mean: {summary['v0_mean']:.4f}")
    print(f"v1 (cross-page whole)    mean: {summary['v1_mean']:.4f}")
    print(f"delta (v1-v0): {summary['mean_delta_v1_minus_v0']:+.4f}")
    print(f"wins — cross-page: {v1_wins}  per-page: {v0_wins}  ties: {ties}")
    print(f"\nOutput:  {args.output}")
    print(f"Summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
