"""Per-chapter phrase-mining harness — one command per chapter.

Runs the surface-form miner then the review-candidate curator with the
chapter-local thresholds (``--min-count 2`` / ``--min-pages 2``, which suit a
~15-page slice of human-locked text) and drops the artifacts in a
per-chapter folder ``09_analysis/phrase_mining_<name>/``.

Intended workflow: after the OCR for a chapter is edited and locked, run

    python mine_chapter.py ch1

to regenerate that chapter's terminology-review worksheet from scratch. The
chapter->page-range table below is the single place those boundaries live;
edit it as later chapters are pinned down (or override per-run with
``--start`` / ``--end`` / ``--name``).

Examples
--------
    python mine_chapter.py ch2                 # pp.46-68 -> phrase_mining_ch2/
    python mine_chapter.py ch1 ch2             # both, in turn
    python mine_chapter.py --start 32 --end 68 --name ch1_2   # custom span
    python mine_chapter.py ch1 --with-marginalia --min-count 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import corpus_phrase_mine as miner  # noqa: E402
import corpus_review_candidates as curator  # noqa: E402

WORKSPACE = _HERE.parent.parent
ANALYSIS = WORKSPACE / "09_analysis"

# The one place chapter boundaries live. Ranges are inclusive physical page
# numbers (p0032 = 32). Extend as later chapters are pinned down.
CHAPTERS: dict[str, tuple[int, int, str]] = {
    "ch1": (32, 45, "Chapter 1"),
    "ch2": (46, 68, "Chapter 2"),
    "ch3": (69, 84, "Chapter 3 (Lucius / Taurinus)"),
    # combined ch1-2 view, the slice reviewed first
    "ch1_2": (32, 68, "Chapters 1-2"),
}


def _resolve(target: str, args) -> tuple[str, int, int, str]:
    """Return (name, start, end, label) for a chapter key or a custom span."""
    if target in CHAPTERS:
        start, end, label = CHAPTERS[target]
        return target, start, end, label
    # custom span requires explicit --start/--end/--name
    if args.start is None or args.end is None:
        raise SystemExit(
            f"Unknown chapter '{target}'. Known: {', '.join(CHAPTERS)}. "
            "For a custom span pass --start/--end (and --name)."
        )
    name = args.name or f"p{args.start:04d}_{args.end:04d}"
    return name, args.start, args.end, f"pp.{args.start}-{args.end}"


def run_one(name: str, start: int, end: int, label: str, args) -> Path:
    out_dir = ANALYSIS / f"phrase_mining_{name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    mine_argv = [
        "--start-page", str(start),
        "--end-page", str(end),
        "--min-count", str(args.min_count),
        "--out-dir", str(out_dir),
    ]
    if not args.with_marginalia:
        mine_argv.append("--no-marginalia")

    print(f"\n=== {name}: {label} (p{start:04d}-p{end:04d}) ===")
    print(f"mine   -> {out_dir}")
    rc = miner.main(mine_argv)
    if rc:
        raise SystemExit(f"miner failed for {name} (exit {rc})")

    curate_argv = [
        "--dir", str(out_dir),
        "--top-terms", str(args.top_terms),
        "--top-names", str(args.top_names),
        "--min-pages", str(args.min_pages),
    ]
    print("curate -> candidates_for_review.md")
    rc = curator.main(curate_argv)
    if rc:
        raise SystemExit(f"curator failed for {name} (exit {rc})")
    return out_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Run phrase mining + review-candidate curation per chapter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Known chapters: " + ", ".join(
            f"{k} (p{v[0]:04d}-p{v[1]:04d})" for k, v in CHAPTERS.items()),
    )
    ap.add_argument("chapters", nargs="*", default=["ch1"],
                    help="One or more chapter keys (ch1, ch2, ...) or a custom "
                         "span via --start/--end/--name. Default: ch1.")
    ap.add_argument("--start", type=int, help="Custom start page (with --end).")
    ap.add_argument("--end", type=int, help="Custom end page (with --start).")
    ap.add_argument("--name", help="Folder suffix for a custom span.")
    ap.add_argument("--min-count", type=int, default=2,
                    help="Min occurrences to keep a phrase (default 2 for a "
                         "single-chapter slice).")
    ap.add_argument("--min-pages", type=int, default=2,
                    help="Min page-spread for a review candidate (default 2).")
    ap.add_argument("--top-terms", type=int, default=70)
    ap.add_argument("--top-names", type=int, default=60)
    ap.add_argument("--with-marginalia", action="store_true",
                    help="Include marginalia/citation scaffolding (off by "
                         "default for a clean body-terminology view).")
    args = ap.parse_args(argv)

    targets = args.chapters or ["ch1"]
    written = []
    for target in targets:
        name, start, end, label = _resolve(target, args)
        written.append(run_one(name, start, end, label, args))

    print("\nDone. Worksheets:")
    for out_dir in written:
        print(f"  {out_dir / 'candidates_for_review.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
