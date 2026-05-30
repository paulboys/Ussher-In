
"""Phase A+ neuro-symbolic layer: footnote-marker leakage validator.

Ussher's body text carries inline footnote anchors like ``bræis^e`` —
each ``^x`` ties a Latin token to a footnote with ``marker_id == 'x'``.
The translator's job is to preserve every anchor in the English at some
sensible position (often end-of-clause), neither dropping nor inventing
nor duplicating.

Per-segment ground truth comes from the structured ``markers`` field on
the body record (a list of ``{"marker_id", "char_offset", ...}``). The
English side is parsed for ``^x`` patterns. Three mismatch classes:

MARKER_DROPPED       Latin has marker ``^x`` but the English window has
                     no ``^x`` (anchor lost; reader cannot navigate to
                     the footnote).
MARKER_HALLUCINATED  English contains a marker ``^x`` that does not
                     appear on this body line or its neighbours.
MARKER_DUPLICATED    A marker ``^x`` appears more than once in the
                     English window — usually the model emitted the
                     anchor in two places.

Window
------
Markers, like glossary terms, frequently land on the adjacent English
line when the Latin anchor sits near a line break. ``--window 1`` (the
default) checks each Latin marker against the body line's English plus
+/- 1 neighbouring body line on the same page.

Footnote text lines (segment_type == 'footnote', segment_id contains
``_fn_``) are NOT checked — markers there are footnote *contents*, not
anchors, and may legitimately reference labels not on this page.

Usage
-----
    python marker_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --output   08_working_scratch/phase3b/marker_flags.jsonl \\
        [--start-page 32 --end-page 45]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_DEFAULT_SEGMENTS = Path("03_segmented_text/part1/segments_with_translations.jsonl")
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/marker_flags.jsonl")

_SEVERITY = {
    "MARKER_DROPPED":      "high",
    "MARKER_HALLUCINATED": "high",
    "MARKER_DUPLICATED":   "medium",
}

_MARKER_RE = re.compile(r"\^([a-z])\b")


def english_for(record: dict) -> str:
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def _page_num(record: dict) -> int | None:
    pid = str(record.get("page_id") or "")
    m = re.search(r"(\d+)", pid) or re.search(r"_p(\d+)_", str(record.get("segment_id") or ""))
    return int(m.group(1)) if m else None


def _order_key(record: dict) -> int:
    seq = record.get("seq")
    if isinstance(seq, int):
        return seq
    m = re.search(r"(\d+)\D*$", str(record.get("segment_id") or ""))
    return int(m.group(1)) if m else 0


def _excerpt(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def _is_body(seg_id: str) -> bool:
    return "_fn_" not in seg_id


def _latin_marker_ids(record: dict) -> list[str]:
    """Prefer the structured markers field; fall back to parsing latin_text."""
    out: list[str] = []
    for m in record.get("markers") or []:
        mid = (m or {}).get("marker_id")
        if isinstance(mid, str) and len(mid) == 1 and mid.isalpha():
            out.append(mid.lower())
    if out:
        return out
    return [m.group(1) for m in _MARKER_RE.finditer(str(record.get("latin_text") or ""))]


def _english_markers(text: str) -> list[str]:
    return [m.group(1) for m in _MARKER_RE.finditer(text)]


def validate(segments_path: Path, *,
             start_page: int | None, end_page: int | None,
             window: int = 1) -> list[dict]:
    body_segs: list[dict] = []
    for raw in segments_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        pn = _page_num(rec)
        if start_page is not None and (pn is None or pn < start_page):
            continue
        if end_page is not None and (pn is None or pn > end_page):
            continue
        seg_id = str(rec.get("segment_id") or "")
        if not _is_body(seg_id):
            continue  # only body lines anchor footnotes
        body_segs.append({
            "seg_id": seg_id, "page_id": rec.get("page_id", ""),
            "page_num": pn, "order": _order_key(rec),
            "latin": str(rec.get("latin_text") or ""),
            "english": english_for(rec),
            "latin_markers": _latin_marker_ids(rec),
        })

    # ordered groups by (page, body) — there is no fn kind here
    groups: dict[int, list[dict]] = {}
    for s in body_segs:
        groups.setdefault(s["page_num"], []).append(s)
    for g in groups.values():
        g.sort(key=lambda s: s["order"])
    pos: dict[str, tuple] = {
        s["seg_id"]: (s["page_num"], i)
        for g in groups.values() for i, s in enumerate(g)
    }

    def window_segs(seg: dict) -> list[dict]:
        pn, i = pos[seg["seg_id"]]
        g = groups[pn]
        lo, hi = max(0, i - window), min(len(g), i + window + 1)
        return g[lo:hi]

    flags: list[dict] = []
    for seg in body_segs:
        win = window_segs(seg)
        win_latin_ids: set[str] = set()
        for w in win:
            win_latin_ids.update(w["latin_markers"])
        win_en_text = " ".join(w["english"] for w in win)
        win_en_ids: list[str] = _english_markers(win_en_text)
        win_en_set = set(win_en_ids)
        en_counts: dict[str, int] = {}
        for mid in win_en_ids:
            en_counts[mid] = en_counts.get(mid, 0) + 1

        # DROPPED — only attribute to a segment for its own latin markers
        for mid in seg["latin_markers"]:
            if mid not in win_en_set:
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "flag": "MARKER_DROPPED", "severity": _SEVERITY["MARKER_DROPPED"],
                    "marker_id": mid,
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": f"Latin marker ^{mid} has no counterpart in the English window.",
                })

        # HALLUCINATED — markers in this segment's english that exist in
        # neither this line's nor any window neighbour's Latin markers
        for mid in set(_english_markers(seg["english"])):
            if mid not in win_latin_ids:
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "flag": "MARKER_HALLUCINATED", "severity": _SEVERITY["MARKER_HALLUCINATED"],
                    "marker_id": mid,
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": f"English carries marker ^{mid} not present in the Latin window.",
                })

        # DUPLICATED — attribute when the duplicate appears in this
        # segment's own english (avoid double-count across overlapping
        # neighbour windows).
        own_counts: dict[str, int] = {}
        for mid in _english_markers(seg["english"]):
            own_counts[mid] = own_counts.get(mid, 0) + 1
        for mid, n in own_counts.items():
            if n > 1:
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "flag": "MARKER_DUPLICATED", "severity": _SEVERITY["MARKER_DUPLICATED"],
                    "marker_id": mid, "count": n,
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": f"Marker ^{mid} appears {n} times in the English for this line.",
                })

    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Footnote-marker leakage validator.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--window", type=int, default=1,
                   help="Neighbour body lines each side to include when "
                        "matching markers (handles anchor drift across "
                        "line breaks). 0 = strict line-exact. Default 1.")
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2

    flags = validate(args.segments,
                     start_page=args.start_page, end_page=args.end_page,
                     window=args.window)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as h:
        for f in flags:
            h.write(json.dumps(f, ensure_ascii=False) + "\n")

    rng = ""
    if args.start_page is not None or args.end_page is not None:
        rng = f" (pages {args.start_page}-{args.end_page})"
    print(f"Scanned {args.segments}")
    print(f"Wrote {len(flags)} flag(s) to {args.output}{rng}")
    by_flag: dict[str, int] = {}
    for f in flags:
        by_flag[f["flag"]] = by_flag.get(f["flag"], 0) + 1
    for flag in ("MARKER_DROPPED", "MARKER_HALLUCINATED", "MARKER_DUPLICATED"):
        if by_flag.get(flag):
            print(f"  {flag:20s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
