"""Marker-placement pass for the sentence pipeline.

``translate_sentences.py`` produces English without ``^x`` footnote-anchor
superscripts (the model is told by Rule 6 not to echo the carets it sees in
the Latin). The line-by-line runner closes this with an in-flow placement
step; the sentence runner does not. This script is that pass, decoupled so it
can run over an already-translated artifact without re-translating:

  for each body sentence carrying footnote markers, insert ``^<symbol>`` into
  its English at the position equivalent to the Latin caret, reusing the
  proven per-marker placement from ``translate_segments`` (LLM placement with
  an end-of-line fallback).

It is idempotent: a marker whose ``^<symbol>`` is already in the English is
skipped, and a record is only rewritten (new ``translation_history`` version,
stage ``marker_placement``) when something actually changed.

The marker→symbol lookup is built RANGE-WIDE from the annotation footnotes, so
a cross-page sentence resolves markers whose footnotes live on the
continuation page. (Render-time forward-linking of such a marker to a footnote
on a *different* page is a separate cross-page edge, out of scope here.)

Usage
-----
    python place_markers.py --part part1 \\
        --segments-name segments_sentences_xpage.jsonl \\
        [--start-page 32 --end-page 45] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from provider_config import default_config                      # noqa: E402
from translation_adapters import AnthropicTranslationAdapter    # noqa: E402
from translation_prompts import _build_marker_lookup            # noqa: E402
from translate_segments import (                                # noqa: E402
    load_phase3b_page,
    extract_units,
    _resolve_page_path,
    _place_markers_in_english,
)

WORKSPACE_ROOT = _HERE.parent.parent
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"


def _page_num(seg: dict) -> int | None:
    m = re.search(r"(\d+)", str(seg.get("page_id") or ""))
    return int(m.group(1)) if m else None


def _latest_english(rec: dict) -> str:
    hist = rec.get("translation_history") or []
    if hist:
        t = (hist[-1] or {}).get("english") or ""
        if t.strip():
            return t
    return rec.get("final_english") or ""


def _placement_markers(rec_markers: list[dict], lookup: dict[str, str],
                       english: str) -> list[dict]:
    """Resolve a sentence's markers to ``[{"marker_id": symbol}, ...]`` in
    order, dropping any whose ``^<symbol>`` is already present (idempotency)."""
    out: list[dict] = []
    for m in rec_markers or []:
        fn_id = m.get("footnote_id")
        sym = lookup.get(str(fn_id)) if fn_id else None
        if not sym:
            continue
        if f"^{sym}" in english:
            continue
        out.append({"marker_id": sym})
    return out


def build_range_lookup(part: str, page_ids: list[str]) -> dict[str, str]:
    """Range-wide footnote_id -> symbol lookup from annotation footnotes."""
    all_fns: list[dict] = []
    for pid in page_ids:
        pp = _resolve_page_path(part, pid)
        if pp is not None and pp.exists():
            _, fns = extract_units(load_phase3b_page(pp))
            all_fns.extend(fns)
    return _build_marker_lookup(all_fns)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sentence-pipeline marker-placement pass.")
    ap.add_argument("--part", default="part1")
    ap.add_argument("--segments-name", default="segments_sentences_xpage.jsonl")
    ap.add_argument("--start-page", type=int, default=None)
    ap.add_argument("--end-page", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="Report which markers would be placed; no model calls, "
                         "no writes.")
    ap.add_argument("--timeout-seconds", type=float, default=None)
    args = ap.parse_args(argv)

    path = ARTIFACTS_DIR / args.part / args.segments_name
    if not path.exists():
        print(f"segments artifact not found: {path}", file=sys.stderr)
        return 2

    records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Page range filter (applies to which body records we touch).
    def in_range(rec: dict) -> bool:
        n = _page_num(rec)
        if n is None:
            return True
        if args.start_page is not None and n < args.start_page:
            return False
        if args.end_page is not None and n > args.end_page:
            return False
        return True

    page_ids = sorted({str(r.get("page_id")) for r in records if r.get("page_id")})
    lookup = build_range_lookup(args.part, page_ids)

    adapter: AnthropicTranslationAdapter | None = None
    if not args.dry_run:
        from dataclasses import replace
        provider = default_config().translation_provider()
        if args.timeout_seconds is not None:
            provider = replace(provider, timeout_seconds=float(args.timeout_seconds))
        adapter = AnthropicTranslationAdapter(provider)

    timestamp = _now_iso()
    model = adapter.provider.model if adapter else "(dry-run)"

    n_records = 0
    n_markers = 0
    n_changed = 0
    all_warnings: list[str] = []

    for rec in records:
        if rec.get("segment_type") == "footnote" or not in_range(rec):
            continue
        eng = _latest_english(rec)
        if not eng.strip():
            continue
        to_place = _placement_markers(rec.get("markers") or [], lookup, eng)
        if not to_place:
            continue
        n_records += 1
        n_markers += len(to_place)
        syms = ", ".join("^" + m["marker_id"] for m in to_place)
        if args.dry_run:
            print(f"{rec.get('segment_id')}: would place {syms}")
            continue
        placed, warnings = _place_markers_in_english(
            english=eng,
            latin_with_caret=rec.get("latin_text") or "",
            markers=to_place,
            adapter=adapter,
        )
        for w in warnings:
            all_warnings.append(f"{rec.get('segment_id')}: {w}")
        if placed != eng:
            n_changed += 1
            hist = rec.setdefault("translation_history", [])
            next_ver = (hist[-1].get("version", 0) + 1) if hist else 1
            hist.append({
                "version": next_ver,
                "stage": "marker_placement",
                "timestamp": timestamp,
                "english": placed,
                "model": model,
            })
            print(f"{rec.get('segment_id')}: placed {syms}")

    if args.dry_run:
        print(f"\n[dry-run] {n_markers} marker(s) across {n_records} sentence(s) "
              f"would be placed.")
        return 0

    # Atomic rewrite preserving record order.
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)

    print(f"\nPlaced {n_markers} marker(s) across {n_records} sentence(s); "
          f"{n_changed} record(s) updated.")
    for w in all_warnings:
        print(f"  WARN: {w}")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
