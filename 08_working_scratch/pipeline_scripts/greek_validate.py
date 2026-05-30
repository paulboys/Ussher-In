
"""Phase A+ neuro-symbolic layer: Greek-preservation validator.

The Ussher convention is that Greek source is preserved verbatim in the
English. When Ussher himself follows the Greek with a Latin paraphrase
(``hoc est`` / ``id est`` / ``nempe`` / ``videlicet`` / ``scilicet`` /
``vel`` / ``seu`` / ``sive``), the translated Latin paraphrase IS the
gloss; no bracketed English gloss is wanted. Only when the Greek stands
alone — no Latin paraphrase cue — should an English bracket gloss
``[...]`` follow.

Flag classes
------------
GREEK_DROPPED          A Greek span of >=3 Greek letters in the Latin is
                       not a substring of the English window after NFC
                       normalisation. High severity — the reader cannot
                       reach what Ussher quoted.

BRACKET_GLOSS_MISSING  (opt-in via ``--check-gloss``) A Greek span
                       embedded in a Latin-prose line has no Latin
                       paraphrase cue within ~30 chars after it, and no
                       ``[...]`` bracket gloss follows the Greek in the
                       English window. Info severity — soft signal,
                       editor judgment.

Skip rules
----------
- Spans with fewer than 3 Greek letters (stray inline characters,
  isolated articles) are ignored.
- BRACKET_GLOSS_MISSING does not fire on lines that are *pure Greek*
  (no surrounding Latin prose); those are body-of-quotation lines whose
  gloss naturally lives elsewhere in the passage.

Output schema mirrors ``glossary_validate``/``numeral_validate`` etc.

Usage
-----
    python greek_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --output   08_working_scratch/phase3b/greek_flags.jsonl \\
        [--start-page 32 --end-page 45] [--check-gloss]
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
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/greek_flags.jsonl")

_SEVERITY = {
    "GREEK_DROPPED":         "high",
    "BRACKET_GLOSS_MISSING": "info",
}

# Greek letter ranges. Includes the basic block (incl. combining marks) and
# the extended block (precomposed accent/breathing combinations Ussher uses).
_GREEK_CHARS = "Ͱ-Ͽἀ-῿̀-ͯ"
# Characters allowed to *connect* Greek letters within a single span:
# whitespace, comma, and curly quotes. Period / colon / semicolon /
# middle-dot (Greek ano teleia) are sentence/title boundaries - they
# split spans so a bracketed English gloss inserted between two Greek
# phrases does not defeat a verbatim substring check.
_GREEK_CONNECT = r" \t,’'‘’"
_GREEK_SPAN_RE = re.compile(
    rf"[{_GREEK_CHARS}](?:[{_GREEK_CONNECT}{_GREEK_CHARS}]*[{_GREEK_CHARS}])?"
)
_GREEK_LETTER_RE = re.compile(rf"[{_GREEK_CHARS}]")

# Latin paraphrase cues that signal "Ussher is about to translate the Greek
# he just quoted" — when present, the bracket-gloss requirement is waived.
_PARAPHRASE_CUE_RE = re.compile(
    r"\b(?:hoc\s+est|id\s+est|nempe|videlicet|scilicet|vel|seu|sive|"
    r"h\.\s*e\.|i\.\s*e\.|viz\.|sc\.)\b",
    re.IGNORECASE,
)

# A bracketed English gloss: anything in [...] or [...]-like brackets.
_BRACKET_GLOSS_RE = re.compile(r"\[[^\]]+\]")

_MIN_GREEK_LETTERS = 3

# Diacritic stripping for accent-insensitive comparison. The Latin OCR
# sometimes drops accents the translator silently restores (e.g. "μονον"
# -> "μόνον"), and the OCR may leave a rough-breathing mark standalone
# before a rho where the translator emits the precomposed form (e.g.
# "῾Ρ" -> "Ῥ"). Both are the translator doing the right thing on a
# corrupted Greek source; a byte-strict substring check would call it
# a drop, which it isn't.
_GREEK_STRIP_RANGES = [
    (0x0300, 0x036F),  # combining diacritics
    (0x1FBD, 0x1FC1),  # standalone psili / koronis / perispomeni etc.
    (0x1FCD, 0x1FCF),
    (0x1FDD, 0x1FDF),
    (0x1FED, 0x1FEF),
    (0x1FFD, 0x1FFE),
]
_GREEK_STRIP_SET = {
    chr(c) for lo, hi in _GREEK_STRIP_RANGES for c in range(lo, hi + 1)
}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _accent_strip(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if c not in _GREEK_STRIP_SET)


def _greek_letter_count(s: str) -> int:
    return sum(1 for ch in s if _GREEK_LETTER_RE.match(ch))


def _latin_alpha_count(s: str) -> int:
    """Roughly: Latin-script letters (no Greek). Used to decide whether a
    line is 'mixed Latin+Greek prose' vs 'pure Greek quotation'."""
    n = 0
    for ch in s:
        if not ch.isalpha():
            continue
        if _GREEK_LETTER_RE.match(ch):
            continue
        n += 1
    return n


def extract_greek_spans(text: str) -> list[tuple[int, int, str]]:
    """Return [(start, end, span_text), ...] for each Greek span with
    >=3 Greek letters. Span text is taken from the source verbatim."""
    out: list[tuple[int, int, str]] = []
    for m in _GREEK_SPAN_RE.finditer(text):
        span = m.group(0)
        if _greek_letter_count(span) < _MIN_GREEK_LETTERS:
            continue
        out.append((m.start(), m.end(), span))
    return out


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


def _has_paraphrase_cue(latin_tail: str) -> bool:
    """True iff a Latin paraphrase cue appears within the first ~30 chars
    after the Greek span (allowing for punctuation/whitespace separation)."""
    head = latin_tail[:30]
    return bool(_PARAPHRASE_CUE_RE.search(head))


def _has_bracket_gloss_near(en_text: str, greek_span: str) -> bool:
    """True iff a bracket gloss opens anywhere in the English after the
    preserved Greek. We look for the opening `[` only (not a balanced
    `[...]`) because Ussher's English glosses regularly run hundreds of
    chars and may close past any reasonable tail window. And we look
    across the entire windowed English so a single gloss at the end of
    a multi-line Greek quotation discharges the duty for the whole
    quoted block."""
    en = _accent_strip(en_text)
    sp = _accent_strip(greek_span)
    idx = en.find(sp)
    if idx < 0:
        return False
    return "[" in en[idx + len(sp):]


def validate(segments_path: Path, *,
             start_page: int | None, end_page: int | None,
             window: int = 1, gloss_window: int = 5,
             check_gloss: bool = False) -> list[dict]:
    segs: list[dict] = []
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
        seg_id = str(rec.get("segment_id") or "")
        segs.append({
            "seg_id": seg_id, "page_id": rec.get("page_id", ""), "page_num": pn,
            "kind": "fn" if "_fn_" in seg_id else "body",
            "order": _order_key(rec), "latin": latin,
            "english": english_for(rec).strip(),
        })

    groups: dict[tuple, list[dict]] = {}
    for s in segs:
        groups.setdefault((s["page_num"], s["kind"]), []).append(s)
    for g in groups.values():
        g.sort(key=lambda s: s["order"])
    pos: dict[str, tuple] = {
        s["seg_id"]: (key, i) for key, g in groups.items() for i, s in enumerate(g)
    }

    def window_english(seg: dict, w: int) -> str:
        key, i = pos[seg["seg_id"]]
        g = groups[key]
        lo, hi = max(0, i - w), min(len(g), i + w + 1)
        return " ".join(g[j]["english"] for j in range(lo, hi))

    flags: list[dict] = []
    for seg in segs:
        spans = extract_greek_spans(seg["latin"])
        if not spans:
            continue
        win_en = window_english(seg, window)
        win_en_cmp = _accent_strip(win_en)

        # Track which spans got flagged DROPPED on THIS segment so we don't
        # also fire BRACKET_GLOSS_MISSING on the same span.
        dropped_spans: set[str] = set()
        for start, end, span in spans:
            if _accent_strip(span) not in win_en_cmp:
                dropped_spans.add(span)
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "flag": "GREEK_DROPPED", "severity": _SEVERITY["GREEK_DROPPED"],
                    "greek_span": _excerpt(span, 120),
                    "greek_letter_count": _greek_letter_count(span),
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": "Greek span from Latin not found in English window.",
                })

        if not check_gloss:
            continue

        # BRACKET_GLOSS_MISSING — only on mixed Latin/Greek prose lines.
        # Pure Greek quotation lines (no surrounding Latin) are skipped;
        # the gloss typically lives at the bookends of the quoted block,
        # often several lines away — hence a wider gloss_window.
        if _latin_alpha_count(seg["latin"]) < 4:
            continue
        gloss_search = window_english(seg, gloss_window)
        for start, end, span in spans:
            if span in dropped_spans:
                continue  # already flagged as dropped; gloss is moot
            latin_tail = seg["latin"][end:]
            if _has_paraphrase_cue(latin_tail):
                continue  # Ussher Latinates it — translation discharges the gloss
            if _has_bracket_gloss_near(gloss_search, span):
                continue  # translator already supplied a bracket gloss
            flags.append({
                "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                "flag": "BRACKET_GLOSS_MISSING",
                "severity": _SEVERITY["BRACKET_GLOSS_MISSING"],
                "greek_span": _excerpt(span, 120),
                "greek_letter_count": _greek_letter_count(span),
                "latin": _excerpt(seg["latin"]),
                "english": _excerpt(seg["english"]) or "(empty)",
                "note": "Standalone Greek (no Latin paraphrase cue) preserved in "
                        "English but no `[...]` gloss follows; soft flag.",
            })

    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Greek-preservation validator.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--window", type=int, default=1,
                   help="Neighbour lines each side included in the English "
                        "search for GREEK_DROPPED (handles Greek spans split "
                        "at line breaks). 0 = strict line-exact. Default 1.")
    p.add_argument("--gloss-window", type=int, default=5,
                   help="Neighbour lines each side included when looking for "
                        "a bracket gloss `[...]` near a Greek span "
                        "(multi-line Greek quotations typically attach a "
                        "single gloss at the end of the block). Default 5.")
    p.add_argument("--check-gloss", action="store_true",
                   help="Also emit BRACKET_GLOSS_MISSING flags for standalone "
                        "Greek (no Latin paraphrase cue, no English `[...]`).")
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2

    flags = validate(args.segments,
                     start_page=args.start_page, end_page=args.end_page,
                     window=args.window, gloss_window=args.gloss_window,
                     check_gloss=args.check_gloss)

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
    for flag in ("GREEK_DROPPED", "BRACKET_GLOSS_MISSING"):
        if by_flag.get(flag):
            print(f"  {flag:22s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
