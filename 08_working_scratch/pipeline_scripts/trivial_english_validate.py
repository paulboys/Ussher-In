
"""Phase A+ neuro-symbolic layer: trivial-English / non-translation detector.

Three of the ten ch1 cf=1 cases were not mistranslations but
non-translations — the model returned something with the right line_id
but no actual English content. The completeness safety net catches
MISSING line_ids; this catches PRESENT-BUT-EMPTY-OF-MEANING line_ids.

Flag types
----------
EMPTY                English string is empty or whitespace only.
PUNCT_ONLY           English is one or two characters, all punctuation
                     (a bare em-dash, period, comma, etc.).
GREEK_ONLY           English is dominated by Greek code points while the
                     Latin is predominantly Latin script — the model
                     echoed the Greek source and produced no English.
LATIN_VERBATIM       English is byte-equal (after whitespace normalisation
                     and lowercasing) to the Latin — no translation.

Skip rules
----------
- If the Latin itself is trivially short (a 1-3 word title or label like
  "ANTIQUITATES." or "CAPUT I."), don't flag a likewise-short English —
  short titles aren't non-translations, they're just short.
- A few units legitimately end with a stranded em-dash because the line
  is a syntactic fragment continuing the previous one. The PUNCT_ONLY
  rule only fires when the English consists of NOTHING BUT punctuation;
  fragmentary lines with at least one word are fine.

Output schema mirrors ``glossary_validate``/``numeral_validate``.

Usage
-----
    python trivial_english_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --output   08_working_scratch/phase3b/trivial_flags.jsonl \\
        [--start-page 32 --end-page 45]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_DEFAULT_SEGMENTS = Path("03_segmented_text/part1/segments_with_translations.jsonl")
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/trivial_flags.jsonl")

_SEVERITY = {
    "EMPTY":          "high",
    "PUNCT_ONLY":     "high",
    "GREEK_ONLY":     "high",
    "LATIN_VERBATIM": "high",
}

# Punctuation set covers ASCII + the typographic chars that appear in OCR
# output (em-dash, en-dash, curly quotes, ellipsis, middle dot, etc.).
_PUNCT_CHARS = set(
    " \t\n\r" + "".join(chr(c) for c in range(0x21, 0x40))
    + "—–-‒―•·…“”‘’„‚«»()[]{}<>"
)


def _is_greek(ch: str) -> bool:
    cp = ord(ch)
    return 0x0370 <= cp <= 0x03FF or 0x1F00 <= cp <= 0x1FFF


def _alpha_breakdown(text: str) -> tuple[int, int, int]:
    """Return (latin_alpha, greek_alpha, other_alpha) counts."""
    lat = grk = oth = 0
    for ch in text:
        if not ch.isalpha():
            continue
        if _is_greek(ch):
            grk += 1
            continue
        # Decompose accented Latin letters so ç/æ/é all count as latin.
        base = unicodedata.normalize("NFD", ch)[0]
        if "A" <= base.upper() <= "Z" or base in "ÆŒæœß":
            lat += 1
        else:
            oth += 1
    return lat, grk, oth


def _normalise(text: str) -> str:
    return " ".join(text.split()).strip().lower()


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


def _excerpt(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def _classify(latin: str, english: str) -> tuple[str | None, str]:
    """Return (flag, note) or (None, '') when nothing to report."""
    en = english.strip()

    if not en:
        return "EMPTY", "English is empty or whitespace only."

    if len(en) <= 2 and all(ch in _PUNCT_CHARS for ch in en):
        return "PUNCT_ONLY", f"English is punctuation only ({en!r})."

    # GREEK_ONLY: english has no Latin-script alphabetic content while
    # the Latin source is predominantly Latin script.
    lat_l, lat_g, _ = _alpha_breakdown(latin)
    en_l, en_g, _ = _alpha_breakdown(en)
    if en_g > 0 and en_l == 0 and lat_l >= max(4, lat_g * 2):
        return ("GREEK_ONLY",
                f"English contains only Greek ({en_g} chars) while Latin is "
                f"predominantly Latin script ({lat_l} Latin vs {lat_g} Greek).")

    # LATIN_VERBATIM: english is identical to latin modulo whitespace+case.
    # Skip when Latin is short enough that identical English would just be
    # a 1-2 word title (CAPUT I. -> CHAPTER I. is fine; but a 30-char
    # Latin line echoed verbatim as English is not).
    if _normalise(en) == _normalise(latin) and len(_normalise(latin)) >= 12:
        return ("LATIN_VERBATIM",
                "English is a verbatim echo of the Latin (no translation).")

    return None, ""


def validate(segments_path: Path, *,
             start_page: int | None, end_page: int | None) -> list[dict]:
    flags: list[dict] = []
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
        latin = str(rec.get("latin_text") or "").strip()
        if not latin:
            continue
        english = english_for(rec)

        flag, note = _classify(latin, english)
        if flag is None:
            continue
        flags.append({
            "segment_id": rec.get("segment_id", ""),
            "page_id": rec.get("page_id", ""),
            "flag": flag, "severity": _SEVERITY[flag],
            "latin": _excerpt(latin),
            "english": _excerpt(english) or "(empty)",
            "note": note,
        })
    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Trivial-English / non-translation detector.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2

    flags = validate(args.segments,
                     start_page=args.start_page, end_page=args.end_page)

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
    for flag in ("EMPTY", "PUNCT_ONLY", "GREEK_ONLY", "LATIN_VERBATIM"):
        if by_flag.get(flag):
            print(f"  {flag:16s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
