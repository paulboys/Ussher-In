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
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
WORKSPACE_ROOT = _HERE.parent.parent
ANNOTATIONS_DIR = WORKSPACE_ROOT / "08_working_scratch" / "phase3b" / "annotations"

from translation_prompts import _inject_markers  # noqa: E402


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
    page_id: str              # HOME page — where the sentence's first line sits
    seq: int                  # 1-based sentence number on the home page
    source_line_ids: list[str] = field(default_factory=list)
    latin_text: str = ""      # space-joined text of constituent lines
    markers: list[dict] = field(default_factory=list)
    # Pages the sentence's lines span, in order. Single-page sentences carry
    # ``[page_id]``; a cross-page sentence carries every page it touches, with
    # the home page first. The reviewer-facing render derives a "completes on
    # pNNNN" cue from this when ``len(spans_pages) > 1``.
    spans_pages: list[str] = field(default_factory=list)

    @property
    def is_cross_page(self) -> bool:
        return len(self.spans_pages) > 1

    def to_dict(self) -> dict:
        return {
            "sentence_id": self.sentence_id,
            "page_id": self.page_id,
            "seq": self.seq,
            "source_line_ids": self.source_line_ids,
            "latin_text": self.latin_text,
            "markers": self.markers,
            "spans_pages": self.spans_pages,
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
    marker_lookup: dict[str, str] | None = None,
) -> SentenceUnit:
    """Build one SentenceUnit from a list of consecutive body lines.

    Latin is concatenated with each line's start offset tracked, so two
    things are handled correctly:

    - **Hyphenated line breaks** join *without* a space (``Evange-`` + ``lii``
      -> ``Evangelii``, not ``Evange lii``). Non-hyphenated lines join with a
      single space.
    - **Footnote-anchor carets** (``^x``): when *marker_lookup*
      (``footnote_id -> symbol``) is supplied, ``^<symbol>`` sentinels are
      injected into the Latin at each marker's position, matching the
      line-by-line artifact. Without a lookup the Latin stays caret-free.
    """
    line_ids = [ln["line_id"] for ln in lines]

    # Concatenate Latin, de-hyphenating line breaks, tracking each line's
    # start offset within the joined string.
    chunks: list[str] = []
    line_start: list[int] = []
    pos = 0
    prev_hyphen = False
    for i, ln in enumerate(lines):
        t = _latin_text(ln)
        hyph = t.endswith("-") and i < len(lines) - 1
        body = t[:-1] if hyph else t
        if i > 0 and not prev_hyphen:
            chunks.append(" ")
            pos += 1
        line_start.append(pos)
        chunks.append(body)
        pos += len(body)
        prev_hyphen = hyph
    latin = "".join(chunks)

    # Collect markers, mapping each line-relative char_offset into the join.
    markers: list[dict] = []
    for i, ln in enumerate(lines):
        base = line_start[i]
        for m in ln.get("markers") or []:
            char_off = m.get("char_offset")
            adjusted_off = (base + char_off) if char_off is not None else None
            markers.append({
                **m,
                "char_offset": adjusted_off,
                "source_line_id": ln["line_id"],
            })

    # Inject ^<symbol> footnote-anchor carets when a lookup is available.
    if marker_lookup:
        latin = _inject_markers(latin, markers, marker_lookup)

    # Pages spanned, in order of first appearance. Derived from each line's
    # own page_id so single-page and cross-page sentences share one code path.
    spans: list[str] = []
    for ln in lines:
        lp = ln.get("page_id") or page_id
        if lp not in spans:
            spans.append(lp)
    if not spans:
        spans = [page_id]

    sid = f"seg_{page_id}_s{seq:04d}"
    return SentenceUnit(
        sentence_id=sid,
        page_id=page_id,
        seq=seq,
        source_line_ids=line_ids,
        latin_text=latin,
        markers=markers,
        spans_pages=spans,
    )


def group_lines_into_sentences(
    body_lines: Sequence[dict],
    page_id: str,
    marker_lookup: dict[str, str] | None = None,
) -> list[SentenceUnit]:
    """Return sentence units for *body_lines* (locked lines only).

    Lines whose ``review_status`` is not ``'locked'`` are skipped.
    *marker_lookup* (``footnote_id -> symbol``), when supplied, injects
    ``^x`` footnote-anchor carets into each unit's Latin.
    """
    locked = [ln for ln in body_lines if ln.get("review_status") == "locked"]

    units: list[SentenceUnit] = []
    current: list[dict] = []

    for line in locked:
        current.append(line)
        if _is_sentence_end(_latin_text(line)):
            units.append(_build_sentence_unit(
                current, page_id, len(units) + 1, marker_lookup))
            current = []

    # Flush any trailing lines (sentence runs to end of page / continues on next)
    if current:
        units.append(_build_sentence_unit(
            current, page_id, len(units) + 1, marker_lookup))

    return units


def group_pages_into_sentences(
    pages: Sequence[tuple[str, Sequence[dict]]],
    marker_lookup: dict[str, str] | None = None,
) -> list[SentenceUnit]:
    """Cross-page sentence grouping over an ordered sequence of pages.

    *pages* is ``[(page_id, body_lines), ...]`` in ascending page order.
    A sentence left open at a page's end absorbs the leading locked lines of
    the following page(s) until a sentence boundary is reached, so a sentence
    that straddles a page seam is translated as one whole unit instead of two
    fragments (the ``mar-`` / ``tyrum`` problem at the p0036/p0037 seam).

    Rules that keep the page-based review model intact:
    - **Home page** = the page of the sentence's *first* line. The sentence's
      ``sentence_id`` and ``page_id`` use that page; ``seq`` restarts per home
      page. A spanning sentence therefore appears exactly once, on its home
      page — never duplicated on the continuation page.
    - The continuation page's own sentences start at its first line that is
      *not* already absorbed by the previous page's trailing sentence, so no
      physical line is owned by two units.
    - ``spans_pages`` records every page the sentence touches (home first) so
      the renderer can show a "completes on pNNNN" cue.

    Only locked lines participate; callers that need the both-pages-locked
    guard should pre-filter the pages they pass in.
    """
    # Flatten to one ordered stream of locked lines across all pages.
    stream: list[dict] = []
    for _pid, body in pages:
        for ln in body:
            if ln.get("review_status") == "locked":
                stream.append(ln)

    units: list[SentenceUnit] = []
    page_seq: dict[str, int] = {}   # home page_id -> running sentence count
    current: list[dict] = []

    def flush() -> None:
        if not current:
            return
        home = current[0].get("page_id") or ""
        seq = page_seq.get(home, 0) + 1
        page_seq[home] = seq
        units.append(_build_sentence_unit(current, home, seq, marker_lookup))

    for line in stream:
        current.append(line)
        if _is_sentence_end(_latin_text(line)):
            flush()
            current = []
    flush()  # trailing open sentence at the very end of the range

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
    p.add_argument("--cross-page", action="store_true",
                   help="Group sentences across page seams (a sentence open "
                        "at a page's end absorbs the next page's leading "
                        "lines). Reports cross-page sentences.")
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

    # Load each page's body once.
    loaded: list[tuple[str, list[dict]]] = []
    for pid in page_ids:
        try:
            loaded.append((pid, load_page_body(args.part, pid)))
        except FileNotFoundError:
            print(f"  {pid}: annotation file not found — skipping", file=sys.stderr)

    if args.cross_page:
        units = group_pages_into_sentences(loaded)
        total_lines = sum(
            1 for _pid, body in loaded
            for ln in body if ln.get("review_status") == "locked"
        )
        crossers = [u for u in units if u.is_cross_page]
        avg_all = total_lines / len(units) if units else 0
        print(f"{'=' * 60}")
        print(f"CROSS-PAGE: {total_lines} locked lines → {len(units)} sentences "
              f"(avg {avg_all:.1f} lines/sentence); "
              f"{len(crossers)} cross-page sentence(s)")
        _print_units(units, debug=args.debug)
        if crossers:
            print(f"\n{'-' * 60}\nCross-page sentences:")
            for u in crossers:
                print(f"  {u.sentence_id}  spans {', '.join(u.spans_pages)}  "
                      f"({len(u.source_line_ids)} lines)")
                print(f"    {u.latin_text[:100]}"
                      f"{'…' if len(u.latin_text) > 100 else ''}")
        return 0

    total_lines = 0
    total_sentences = 0
    for pid, body in loaded:
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
