"""Group page body lines into sentence units for sentence-level translation.

The Phase 3b annotation JSONs are line-keyed. This module reads them
read-only and groups consecutive locked body lines into sentence units.
Each sentence unit carries all its constituent line IDs, concatenated
Latin text, and combined markers.

Sentence-boundary detection is abbreviation-aware: a period at the end of
a line is a sentence boundary only if the preceding token is not a known
Latin abbreviation, Roman numeral, or single-letter initial.

Usage (smoke-test)
------------------
    python sentence_segment.py --part part1 --start-page 32 --end-page 45
    python sentence_segment.py --part part1 --page 36 --debug
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
WORKSPACE_ROOT = _HERE.parent.parent
ANNOTATIONS_DIR = WORKSPACE_ROOT / "08_working_scratch" / "phase3b" / "annotations"


# ---------------------------------------------------------------------------
# Abbreviation vocabulary
# ---------------------------------------------------------------------------

# Citation keywords (from citation_validate.py)
_CITATION_ABBREVS = {
    "lib", "cap", "ver", "pag", "tom", "edit", "epigram", "epist", "part", "op",
}

# Biblical book stems (from citation_validate.py)
_BIBLICAL_ABBREVS = {
    "matth", "marc", "luc", "joh", "joan", "act", "rom", "cor", "gal", "ephes",
    "phil", "coloss", "colos", "thess", "tim", "tit", "philem", "hebr", "jac",
    "pet", "apoc", "apocal", "esai", "esa", "isai", "jer", "ezech", "dan",
    "psal", "prov", "eccl", "cant", "gen", "exod", "levit", "num", "deut",
    "jos", "jud",
}

# Common Latin scholarly abbreviations
_SCHOLARLY_ABBREVS = {
    "ann", "art", "cf", "col", "ep", "ff", "fol", "ibid", "id", "inst",
    "loc", "ms", "mss", "n", "no", "obs", "p", "pp", "prox", "q",
    "r", "s", "sc", "scil", "seq", "ser", "sess", "sig", "ss", "t",
    "ult", "v", "viz", "vol", "vs",
}

# Honorifics and titles (S. = Sanctus, B. = Beatus, D. = Dominus)
_HONORIFIC_ABBREVS = {"s", "b", "d", "dr", "mr", "st"}

_ALL_ABBREVS = (
    _CITATION_ABBREVS
    | _BIBLICAL_ABBREVS
    | _SCHOLARLY_ABBREVS
    | _HONORIFIC_ABBREVS
)

# Roman numeral pattern (uppercase only — Ussher uses uppercase Roman numerals)
_ROMAN_RE = re.compile(
    r"^M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$"
)

# Strip ^x caret sentinels before analysis
_CARET_RE = re.compile(r"\^[a-z]")


# ---------------------------------------------------------------------------
# Sentence-boundary detection
# ---------------------------------------------------------------------------


def _strip_carets(text: str) -> str:
    return _CARET_RE.sub("", text)


def _is_roman_numeral(token: str) -> bool:
    t = token.strip(".")
    return bool(t) and bool(_ROMAN_RE.match(t))


def _is_sentence_end(raw_text: str) -> bool:
    """Return True if *raw_text* ends a sentence.

    A line ends a sentence when:
    1. Its text (after stripping caret sentinels) ends with terminal
       punctuation — ``.`` ``!`` ``?`` — optionally followed by a
       closing quote/bracket.
    2. The last token before that punctuation is not a known abbreviation,
       Roman numeral, or single letter/initial.

    Lines ending with a hyphen (word broken across line break) never end
    a sentence regardless of trailing punctuation.
    """
    text = _strip_carets(raw_text).rstrip()

    if not text:
        return False

    # Hyphenated word-break — never a sentence end
    if text.endswith("-"):
        return False

    # Must end with terminal punctuation (optionally preceded by closing marks)
    m = re.search(r'[.!?][)\]"’”\xbb]?\s*$', text)
    if not m:
        return False

    # Get the token immediately before the terminal punctuation
    prefix = text[: m.start()].rstrip()
    if not prefix:
        # Period with nothing before it — treat as sentence end
        return True

    tokens = prefix.split()
    last = tokens[-1] if tokens else ""

    # Single letter or initial (e.g. "J.", "P.")
    if re.match(r"^[A-Za-z]$", last.strip(".")):
        return False

    # Roman numeral (e.g. "III", "XXXVI")
    if _is_roman_numeral(last):
        return False

    # Known abbreviation (case-insensitive, strip trailing period)
    stem = last.rstrip(".").lower()
    if stem in _ALL_ABBREVS:
        return False

    return True


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SentenceUnit:
    sentence_id: str          # e.g. "seg_p0036_s0001"
    page_id: str
    seq: int                  # 1-based sentence number on this page
    source_line_ids: list[str] = field(default_factory=list)
    latin_text: str = ""      # space-joined text of constituent lines
    markers: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sentence_id": self.sentence_id,
            "page_id": self.page_id,
            "seq": self.seq,
            "source_line_ids": self.source_line_ids,
            "latin_text": self.latin_text,
            "markers": self.markers,
        }


# ---------------------------------------------------------------------------
# Core grouping
# ---------------------------------------------------------------------------


def _latin_text(line: dict) -> str:
    return (line.get("text_gold") or line.get("text_ocr_original") or "").strip()


def _build_sentence_unit(
    lines: list[dict],
    page_id: str,
    seq: int,
) -> SentenceUnit:
    """Build one SentenceUnit from a list of consecutive body lines."""
    line_ids = [ln["line_id"] for ln in lines]
    # Join with space; handle hyphenated line-breaks by stripping the hyphen
    parts: list[str] = []
    for i, ln in enumerate(lines):
        t = _latin_text(ln)
        if t.endswith("-") and i < len(lines) - 1:
            parts.append(t[:-1])   # strip hyphen; next line continues the word
        else:
            parts.append(t)
    latin = " ".join(p for p in parts if p)

    # Collect markers from all constituent lines, adjusting char_offset to
    # the position within the concatenated latin string.
    markers: list[dict] = []
    offset = 0
    for i, ln in enumerate(lines):
        t = _latin_text(ln)
        raw_len = len(t[:-1] if t.endswith("-") and i < len(lines) - 1 else t)
        for m in ln.get("markers") or []:
            char_off = m.get("char_offset")
            adjusted_off = (offset + char_off) if char_off is not None else None
            markers.append({
                **m,
                "char_offset": adjusted_off,
                "source_line_id": ln["line_id"],
            })
        # +1 for the joining space (except after last line)
        offset += raw_len + (1 if i < len(lines) - 1 else 0)

    sid = f"seg_{page_id}_s{seq:04d}"
    return SentenceUnit(
        sentence_id=sid,
        page_id=page_id,
        seq=seq,
        source_line_ids=line_ids,
        latin_text=latin,
        markers=markers,
    )


def group_lines_into_sentences(
    body_lines: Sequence[dict],
    page_id: str,
) -> list[SentenceUnit]:
    """Return sentence units for *body_lines* (locked lines only).

    Lines whose ``review_status`` is not ``'locked'`` are skipped.
    """
    locked = [ln for ln in body_lines if ln.get("review_status") == "locked"]

    units: list[SentenceUnit] = []
    current: list[dict] = []

    for line in locked:
        current.append(line)
        if _is_sentence_end(_latin_text(line)):
            units.append(_build_sentence_unit(current, page_id, len(units) + 1))
            current = []

    # Flush any trailing lines (sentence runs to end of page / continues on next)
    if current:
        units.append(_build_sentence_unit(current, page_id, len(units) + 1))

    return units


# ---------------------------------------------------------------------------
# Page loading (mirrors translate_segments.py layout)
# ---------------------------------------------------------------------------


def _page_path(part: str | None, page_id: str) -> Path:
    if part:
        candidate = ANNOTATIONS_DIR / part / f"page_{page_id}.json"
        if candidate.exists():
            return candidate
    return ANNOTATIONS_DIR / f"page_{page_id}.json"


def load_page_body(part: str | None, page_id: str) -> list[dict]:
    path = _page_path(part, page_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = (payload.get("regions") or {}).get("body") or []
    body_sorted = sorted(body, key=lambda ln: ln.get("seq") or 0)
    return body_sorted


def _iter_page_ids(part: str, start: int, end: int):
    """Yield page_ids in range by scanning annotation filenames."""
    base = ANNOTATIONS_DIR / part if part else ANNOTATIONS_DIR
    if not base.exists():
        base = ANNOTATIONS_DIR
    for p in sorted(base.glob("page_p*.json")):
        m = re.search(r"p(\d+)", p.stem)
        if m and start <= int(m.group(1)) <= end:
            yield p.stem.replace("page_", "")


# ---------------------------------------------------------------------------
# CLI — smoke-test + debug
# ---------------------------------------------------------------------------


def _print_units(units: list[SentenceUnit], *, debug: bool) -> None:
    for u in units:
        n_lines = len(u.source_line_ids)
        n_markers = len(u.markers)
        if debug:
            print(f"\n{u.sentence_id}  ({n_lines} line{'s' if n_lines != 1 else ''}, "
                  f"{n_markers} marker{'s' if n_markers != 1 else ''})")
            print(f"  Lines : {', '.join(u.source_line_ids)}")
            print(f"  Latin : {u.latin_text[:120]}"
                  f"{'…' if len(u.latin_text) > 120 else ''}")
        else:
            print(f"{u.sentence_id}  lines={n_lines}  "
                  f"{u.latin_text[:80]}{'…' if len(u.latin_text) > 80 else ''}")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Smoke-test Latin sentence segmentation on ch1 pages."
    )
    p.add_argument("--part", default=None,
                   help="Annotation sub-directory (e.g. 'part1'). "
                        "Omit to search ANNOTATIONS_DIR root.")
    p.add_argument("--page", type=int, default=None,
                   help="Single page number (overrides --start/--end-page).")
    p.add_argument("--start-page", type=int, default=32)
    p.add_argument("--end-page", type=int, default=45)
    p.add_argument("--debug", action="store_true",
                   help="Show constituent line IDs and full Latin text.")
    args = p.parse_args(argv)

    if args.page is not None:
        page_ids = [f"p{args.page:04d}"]
    else:
        page_ids = list(_iter_page_ids(
            args.part or "", args.start_page, args.end_page
        ))

    if not page_ids:
        print("No pages found.", file=sys.stderr)
        return 1

    total_lines = 0
    total_sentences = 0

    for pid in page_ids:
        try:
            body = load_page_body(args.part, pid)
        except FileNotFoundError:
            print(f"  {pid}: annotation file not found — skipping", file=sys.stderr)
            continue

        locked = [ln for ln in body if ln.get("review_status") == "locked"]
        units = group_lines_into_sentences(body, pid)

        avg = len(locked) / len(units) if units else 0
        print(f"\n{'=' * 60}")
        print(f"{pid}: {len(locked)} locked lines → {len(units)} sentences "
              f"(avg {avg:.1f} lines/sentence)")
        _print_units(units, debug=args.debug)

        total_lines += len(locked)
        total_sentences += len(units)

    if len(page_ids) > 1:
        avg_all = total_lines / total_sentences if total_sentences else 0
        print(f"\n{'=' * 60}")
        print(f"TOTAL: {total_lines} lines → {total_sentences} sentences "
              f"(avg {avg_all:.1f} lines/sentence)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
