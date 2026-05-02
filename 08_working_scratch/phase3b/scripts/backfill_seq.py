"""Backfill the ``seq`` ordering field on annotation page JSON files
and on the per-part ``segments_with_translations.jsonl`` artifact.

`seq` is the ordering authority for translation and rendering: a 1-based
dense integer per region (and per footnote list) that mirrors the array
order. `line_id` / `footnote_id` / `segment_id` remain immutable
identity strings.

This script:

1. Stamps `seq` onto every line and footnote in every page JSON under
   ``08_working_scratch/phase3b/annotations/``.
2. Stamps `seq` onto every segment in
   ``03_segmented_text/<part>/segments_with_translations.jsonl`` when
   missing (deriving from the ``_l<NNNN>`` / ``_fn_<NNN>`` regex on
   ``segment_id`` so existing order is preserved exactly).

Both passes are idempotent.

Usage:
    python backfill_seq.py                 # write changes (pages + all parts)
    python backfill_seq.py --check         # dry-run; report changes
    python backfill_seq.py --paths ...     # restrict pages to specific files
    python backfill_seq.py --skip-segments # only do page JSONs
    python backfill_seq.py --skip-pages    # only do segment JSONLs
    python backfill_seq.py --parts part1   # restrict segment scan to parts
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANNOTATIONS_DIR = ROOT / "08_working_scratch" / "phase3b" / "annotations"
ARTIFACTS_DIR = ROOT / "03_segmented_text"
SCHEMA_REGIONS = ("header", "body", "marginalia", "catchword")

_BODY_RE = re.compile(r"_l(\d+)$")
_FN_RE = re.compile(r"_fn_(\d+)$")


def stamp_seq(payload: dict) -> int:
    """Stamp ``seq`` per region and on footnotes. Returns the count of
    line/footnote entries whose ``seq`` was missing or wrong before
    stamping (i.e. the number of effective changes)."""
    if not isinstance(payload, dict):
        return 0
    changed = 0
    regions = payload.get("regions", {})
    if isinstance(regions, dict):
        for region in SCHEMA_REGIONS:
            arr = regions.get(region)
            if not isinstance(arr, list):
                continue
            for idx, line in enumerate(arr):
                if not isinstance(line, dict):
                    continue
                expected = idx + 1
                if line.get("seq") != expected:
                    changed += 1
                line["seq"] = expected
    footnotes = payload.get("footnotes")
    if isinstance(footnotes, list):
        for idx, fn in enumerate(footnotes):
            if not isinstance(fn, dict):
                continue
            expected = idx + 1
            if fn.get("seq") != expected:
                changed += 1
            fn["seq"] = expected
    return changed


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent), suffix=".tmp"
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        tmp = handle.name
    Path(tmp).replace(path)


def process_file(path: Path, *, check_only: bool) -> tuple[bool, int]:
    """Returns (would_change, changed_count)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"SKIP {path.name}: {exc}", file=sys.stderr)
        return False, 0
    changed = stamp_seq(payload)
    would_change = changed > 0
    if would_change and not check_only:
        write_atomic(path, payload)
    return would_change, changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Dry-run only")
    ap.add_argument(
        "--paths",
        nargs="*",
        type=Path,
        help="Specific page JSON files to process (default: all in annotations/)",
    )
    ap.add_argument(
        "--skip-pages", action="store_true", help="Skip page JSON pass"
    )
    ap.add_argument(
        "--skip-segments", action="store_true", help="Skip segments JSONL pass"
    )
    ap.add_argument(
        "--parts",
        nargs="*",
        default=None,
        help="Restrict segment scan to these parts (default: all under 03_segmented_text/)",
    )
    args = ap.parse_args(argv)

    rc = 0

    if not args.skip_pages:
        if args.paths:
            files = [p.resolve() for p in args.paths]
        else:
            files = sorted(ANNOTATIONS_DIR.glob("page_p*.json"))
        if not files and not args.skip_segments:
            print("No annotation files found.", file=sys.stderr)
        page_changed_files = 0
        page_changed_entries = 0
        for path in files:
            would_change, changed = process_file(path, check_only=args.check)
            if would_change:
                page_changed_files += 1
                page_changed_entries += changed
                verb = "WOULD UPDATE" if args.check else "UPDATED"
                print(f"{verb} {path.name}: {changed} entry/entries restamped")
        if args.check:
            print(
                f"Pages check: {page_changed_files} file(s) would change "
                f"({page_changed_entries} entries)."
            )
            if page_changed_files:
                rc = 1
        else:
            print(
                f"Pages: {page_changed_files} file(s) updated "
                f"({page_changed_entries} entries restamped)."
            )

    if not args.skip_segments:
        if args.paths:
            # When --paths is used (typically tests or one-off), skip the
            # global segments scan to keep the operation focused.
            part_dirs = []
        elif args.parts:
            part_dirs = [ARTIFACTS_DIR / p for p in args.parts]
        elif ARTIFACTS_DIR.exists():
            part_dirs = sorted(p for p in ARTIFACTS_DIR.iterdir() if p.is_dir())
        else:
            part_dirs = []
        seg_changed_files = 0
        seg_changed_entries = 0
        for part_dir in part_dirs:
            jsonl = part_dir / "segments_with_translations.jsonl"
            if not jsonl.exists():
                continue
            would_change, changed = process_segments_jsonl(jsonl, check_only=args.check)
            if would_change:
                seg_changed_files += 1
                seg_changed_entries += changed
                verb = "WOULD UPDATE" if args.check else "UPDATED"
                print(f"{verb} {jsonl}: {changed} segment(s) stamped")
        if args.check:
            print(
                f"Segments check: {seg_changed_files} file(s) would change "
                f"({seg_changed_entries} segments)."
            )
            if seg_changed_files:
                rc = 1
        else:
            print(
                f"Segments: {seg_changed_files} file(s) updated "
                f"({seg_changed_entries} segments stamped)."
            )

    return rc


def derive_seq_from_segment_id(seg_id: str) -> int | None:
    """Pull the trailing numeric suffix from a body or footnote
    ``segment_id`` so legacy JSONL records get a stable ``seq`` that
    preserves their previous (regex-driven) sort order."""
    m = _BODY_RE.search(seg_id) or _FN_RE.search(seg_id)
    if m:
        return int(m.group(1))
    return None


def process_segments_jsonl(path: Path, *, check_only: bool) -> tuple[bool, int]:
    """Stamp ``seq`` onto records that don't already have it. Existing
    ``seq`` values are left untouched (translate_segments has already
    written the authoritative value from the page JSON).

    Returns ``(would_change, changed_count)``.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"SKIP {path}: {exc}", file=sys.stderr)
        return False, 0
    lines: list[dict] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s:
            continue
        try:
            lines.append(json.loads(s))
        except json.JSONDecodeError as exc:
            print(f"SKIP {path}:{line_no}: {exc}", file=sys.stderr)
            return False, 0

    changed = 0
    for record in lines:
        if isinstance(record.get("seq"), int):
            continue
        seq = derive_seq_from_segment_id(str(record.get("segment_id", "")))
        if seq is not None:
            record["seq"] = seq
            changed += 1

    if changed == 0:
        return False, 0

    if not check_only:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for record in lines:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        tmp.replace(path)
    return True, changed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
