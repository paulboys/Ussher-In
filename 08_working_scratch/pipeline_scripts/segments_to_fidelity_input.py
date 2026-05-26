"""Adapt a translation run into author_fidelity_judge.py input.

`translate_segments.py` emits `segments_with_translations.jsonl` (one row
per segment: segment_id, latin_text, translation_history, final_english).
`author_fidelity_judge.py` expects rows with {run, unit_id, latin_concat,
english_concat}. For corpora with no English gold (Britannicarum,
Annals), there is no COMET step to produce that intermediate, so this
script bridges directly: one judge unit per translated segment.

Usage
-----
::

    python segments_to_fidelity_input.py \\
        --segments 04_translation_work/ab/p0036/ussher_v5/<tag>/segments_with_translations.jsonl \\
        --run v5_base \\
        --output 04_translation_work/ab/p0036/ussher_v5/<tag>/fidelity_input.jsonl

The `--run` label is written into each row's `run` field; pass the same
value to ``author_fidelity_judge.py --run-filter``. Segments with empty
Latin or empty English are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def english_for(record: dict) -> str:
    """Latest translation text: translation_history[-1].english, else final_english."""
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def main() -> int:
    p = argparse.ArgumentParser(
        description="Convert a segments_with_translations.jsonl run into "
                    "author_fidelity_judge.py input rows."
    )
    p.add_argument("--segments", required=True, type=Path,
                   help="path to segments_with_translations.jsonl")
    p.add_argument("--run", required=True,
                   help="run label written to each row's 'run' field "
                        "(pass the same value to --run-filter)")
    p.add_argument("--output", required=True, type=Path,
                   help="output JSONL in fidelity-judge input shape")
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    skipped = 0
    with args.segments.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            seg_id = str(rec.get("segment_id") or "")
            latin = str(rec.get("latin_text") or "").strip()
            english = english_for(rec).strip()
            if not seg_id or not latin or not english:
                skipped += 1
                continue
            rows.append({
                "run": args.run,
                "unit_id": seg_id,
                "latin_concat": latin,
                "english_concat": english,
                "score": None,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} units to {args.output} (run={args.run}); "
          f"skipped {skipped} empty/incomplete segment(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
