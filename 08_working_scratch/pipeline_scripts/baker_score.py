"""Score a machine translation of Antiquitates ch. 2 against Baker (1930).

Reference-based COMET (``Unbabel/wmt22-comet-da``): src = Ussher's Latin,
mt = the machine English, ref = H. Kendra Baker's published translation,
paired by ``baker_align.py``. This is the project's first reference-based
score on the Antiquitates itself (Whitaker had the 1849 Parker Society
reference; Baker covers exactly this chapter).

Usage
-----
    python baker_score.py --label fable-5
    python baker_score.py --label opus-4-8 \\
        --alignment path/to/other_alignment.jsonl

Writes ``baker_scores_<label>.jsonl`` (per-unit) and
``baker_scores_<label>_summary.json`` next to the alignment artifact.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
WORKSPACE = _HERE.parent.parent
BENCH_DIR = WORKSPACE / "04_translation_work" / "ab" / "antiquitates_ch2" / "baker_benchmark"
MODEL = "Unbabel/wmt22-comet-da"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="COMET-score ch2 MT against Baker 1930.")
    ap.add_argument("--alignment", type=Path,
                    default=BENCH_DIR / "baker_alignment.jsonl")
    ap.add_argument("--label", required=True,
                    help="System label for the output filenames (e.g. fable-5).")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--gpus", type=int, default=0)
    args = ap.parse_args(argv)

    rows = [json.loads(l) for l in
            args.alignment.read_text(encoding="utf-8").splitlines() if l.strip()]
    scoreable = [r for r in rows
                 if r.get("baker_ref", "").strip() and r.get("mt_english", "").strip()]
    skipped = [r["unit_id"] for r in rows if r not in scoreable]
    print(f"{len(scoreable)} scoreable units; skipped {len(skipped)}: {skipped}")

    print(f"Loading {MODEL} ...")
    from comet import download_model, load_from_checkpoint  # type: ignore
    model = load_from_checkpoint(download_model(MODEL))

    data = [{"src": r["latin"], "mt": r["mt_english"], "ref": r["baker_ref"]}
            for r in scoreable]
    out = model.predict(data, batch_size=args.batch_size, gpus=args.gpus)
    scores = list(out.scores)

    out_dir = args.alignment.parent
    per_unit = out_dir / f"baker_scores_{args.label}.jsonl"
    with per_unit.open("w", encoding="utf-8") as fh:
        for r, s in zip(scoreable, scores):
            fh.write(json.dumps({
                "unit_id": r["unit_id"],
                "comet": round(float(s), 4),
                "latin": r["latin"],
                "mt_english": r["mt_english"],
                "baker_ref": r["baker_ref"],
                "manual_fix": r.get("manual_fix"),
            }, ensure_ascii=False) + "\n")

    summary = {
        "model": MODEL,
        "system": args.label,
        "units_scored": len(scores),
        "units_skipped": skipped,
        "mean": round(statistics.mean(scores), 4),
        "median": round(statistics.median(scores), 4),
        "stdev": round(statistics.stdev(scores), 4) if len(scores) > 1 else None,
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "system_score": round(float(out.system_score), 4),
    }
    (out_dir / f"baker_scores_{args.label}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    worst = sorted(zip(scores, scoreable))[:5]
    print("\nLowest-scoring units:")
    for s, r in worst:
        print(f"  {s:.3f}  {r['unit_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
