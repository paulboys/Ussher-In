
"""Phase A+ neuro-symbolic layer: numeral-preservation validator.

Catches the silent-miscount class of mistranslation. Ch1 surfaced
``octavum`` -> ``twenty-eighth`` and ``quintum`` -> ``fifteenth`` (both
cf=1 in the fidelity judge). Those errors slip past a reader because the
English is grammatical and contextually plausible — only the value is
wrong. A deterministic extract-and-compare is cheap and effective.

Approach
--------
For each segment with non-empty Latin, build a multiset of integer values
from the Latin (Arabic digits, Roman numerals length>=2, ordinal stems
with required Latin endings, cardinal words). Build the same from the
English window (segment plus +/- ``window`` neighbours on the same page
and kind — body or footnote — mirroring ``glossary_validate``). Any Latin
value with no English counterpart is flagged MISSING_NUMERAL.

The "non" trap: Latin ``non`` (= not) is far more frequent than ``nonus``
(= ninth). The ordinal stem ``\\bnon`` is gated by a required Latin
adjective ending (``-us/-a/-um/...``) so bare ``non`` never scores as 9.

Roman numerals length>=2 only: ``I`` collides with the English pronoun.
The narrow loss (citations of ``cap. I``) is worth the false-positive
suppression; ordinal stems still catch ``primum``.

Output
------
Per-flag JSON lines, schema parallel to ``glossary_validate.py``:

    {"segment_id": "...", "page_id": "...", "flag": "MISSING_NUMERAL",
     "severity": "high", "latin_value": 8, "latin_token": "octavum",
     "expected_en": ["8", "eight", "eighth", "VIII"],
     "latin": "...excerpt...", "english": "...excerpt...",
     "note": "..."}

Usage
-----
    python numeral_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --output   08_working_scratch/phase3b/numeral_flags.jsonl \\
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
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/numeral_flags.jsonl")

_SEVERITY = {"MISSING_NUMERAL": "high"}


# ---------- Latin number extraction ----------

# Adjective endings that confirm a stem is genuinely an ordinal (e.g.
# nonus/nona/nonum), so bare "non" (= not) is excluded.
_ORD_END = r"(?:us|a|um|i|o|ae|orum|arum|is|em|os|as|ius)"

_LATIN_ORDINAL_STEMS: list[tuple[str, int]] = [
    (r"prim",     1),
    (r"secund",   2),
    (r"terti",    3),
    (r"quart",    4),
    (r"quint",    5),
    (r"sext",     6),
    (r"septim",   7),
    (r"octav",    8),
    (r"non",      9),
    (r"decim",   10),
    (r"undecim", 11),
    (r"duodecim",12),
]
_LATIN_ORDINAL_RE = [
    (re.compile(rf"\b({stem}{_ORD_END})\b", re.IGNORECASE), val)
    for stem, val in _LATIN_ORDINAL_STEMS
]

# Cardinal Latin numbers. Multiple inflected forms per lemma; uncommon in
# this corpus (citations use Arabic/Roman) but cheap to cover.
_LATIN_CARDINALS: dict[str, int] = {
    "unus":1, "una":1, "unum":1, "unius":1, "uni":1, "uno":1,
    "duo":2, "duae":2, "duos":2, "duarum":2, "duobus":2, "duabus":2,
    "tres":3, "tria":3, "trium":3, "tribus":3,
    "quattuor":4, "quatuor":4,
    "quinque":5,
    "sex":6,
    "septem":7,
    "octo":8,
    "novem":9,
    "decem":10,
    "undecim":11, "duodecim":12, "tredecim":13, "quattuordecim":14,
    "quindecim":15, "sedecim":16, "septendecim":17,
    "duodeviginti":18, "undeviginti":19, "viginti":20,
    "triginta":30, "quadraginta":40, "quinquaginta":50,
    "sexaginta":60, "septuaginta":70, "octoginta":80, "nonaginta":90,
    "centum":100, "mille":1000,
}
_LATIN_CARDINAL_RE = re.compile(
    r"\b(" + "|".join(sorted(_LATIN_CARDINALS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Roman numerals: uppercase only, length >= 2, to avoid pronoun "I" and
# false matches on lowercase Latin words containing only IVXLCDM letters
# (e.g. "civi", "lividi"). The Latin scribes write them uppercase anyway.
_ROMAN_RE = re.compile(r"\b[IVXLCDM]{2,}\b")
_ROMAN_VAL = {"I":1, "V":5, "X":10, "L":50, "C":100, "D":500, "M":1000}

# Arabic digits — any run. No trailing \b so "36th" / "61st" parse as 36 / 61.
_DIGIT_RE = re.compile(r"\b(\d+)")


def roman_to_int(s: str) -> int | None:
    total = 0
    prev = 0
    for ch in reversed(s):
        v = _ROMAN_VAL.get(ch)
        if v is None:
            return None
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total if total > 0 else None


def extract_latin_numerals(text: str) -> list[tuple[int, str]]:
    """Return list of (value, source_token) tuples. Order preserved for
    reporting; duplicates kept so a multiset comparison is possible."""
    found: list[tuple[int, str]] = []
    for m in _DIGIT_RE.finditer(text):
        found.append((int(m.group(1)), m.group(0)))
    for m in _ROMAN_RE.finditer(text):
        v = roman_to_int(m.group(0))
        if v is not None:
            found.append((v, m.group(0)))
    for rx, val in _LATIN_ORDINAL_RE:
        for m in rx.finditer(text):
            found.append((val, m.group(1)))
    for m in _LATIN_CARDINAL_RE.finditer(text):
        found.append((_LATIN_CARDINALS[m.group(1).lower()], m.group(1)))
    return found


# ---------- English number extraction ----------

_EN_ONES = {
    "one":1, "two":2, "three":3, "four":4, "five":5,
    "six":6, "seven":7, "eight":8, "nine":9,
}
_EN_TEENS = {
    "ten":10, "eleven":11, "twelve":12, "thirteen":13, "fourteen":14,
    "fifteen":15, "sixteen":16, "seventeen":17, "eighteen":18, "nineteen":19,
}
_EN_TENS = {
    "twenty":20, "thirty":30, "forty":40, "fifty":50,
    "sixty":60, "seventy":70, "eighty":80, "ninety":90,
}
_EN_ORD_ONES = {
    "first":1, "second":2, "third":3, "fourth":4, "fifth":5,
    "sixth":6, "seventh":7, "eighth":8, "ninth":9,
}
_EN_ORD_TEENS = {
    "tenth":10, "eleventh":11, "twelfth":12, "thirteenth":13, "fourteenth":14,
    "fifteenth":15, "sixteenth":16, "seventeenth":17, "eighteenth":18, "nineteenth":19,
}
_EN_ORD_TENS = {
    "twentieth":20, "thirtieth":30, "fortieth":40, "fiftieth":50,
    "sixtieth":60, "seventieth":70, "eightieth":80, "ninetieth":90,
}

# Compounds first ("twenty-eighth" before standalone "twenty"+"eighth")
_EN_TENS_RX = "(?:" + "|".join(sorted(_EN_TENS, key=len, reverse=True)) + ")"
_EN_ONES_RX = "(?:" + "|".join(sorted(_EN_ONES, key=len, reverse=True)) + ")"
_EN_ORD_ONES_RX = "(?:" + "|".join(sorted(_EN_ORD_ONES, key=len, reverse=True)) + ")"

_EN_COMPOUND_CARD_RE = re.compile(
    rf"\b({_EN_TENS_RX})[-\s]({_EN_ONES_RX})\b", re.IGNORECASE)
_EN_COMPOUND_ORD_RE = re.compile(
    rf"\b({_EN_TENS_RX})[-\s]({_EN_ORD_ONES_RX})\b", re.IGNORECASE)

_EN_TENS_RE = re.compile(rf"\b({_EN_TENS_RX})\b", re.IGNORECASE)
_EN_TEENS_RE = re.compile(
    r"\b(" + "|".join(sorted(_EN_TEENS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)
_EN_ONES_RE = re.compile(rf"\b({_EN_ONES_RX})\b", re.IGNORECASE)
_EN_ORD_TENS_RE = re.compile(
    r"\b(" + "|".join(sorted(_EN_ORD_TENS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)
_EN_ORD_TEENS_RE = re.compile(
    r"\b(" + "|".join(sorted(_EN_ORD_TEENS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)
_EN_ORD_ONES_RE = re.compile(rf"\b({_EN_ORD_ONES_RX})\b", re.IGNORECASE)


def extract_english_numerals(text: str) -> set[int]:
    values: set[int] = set()
    work = text

    for m in _DIGIT_RE.finditer(work):
        values.add(int(m.group(1)))
    for m in _ROMAN_RE.finditer(work):
        v = roman_to_int(m.group(0))
        if v is not None:
            values.add(v)

    # Compounds first. Add the SUM and both COMPONENTS — Latin often
    # expresses 23 as "viginti et tres" (two discrete values 20 + 3),
    # while English contracts to "twenty-three". Counting both sides as
    # {23, 20, 3} avoids the asymmetric false positive.
    def _consume(rx: re.Pattern, table_a: dict, table_b: dict) -> str:
        nonlocal work
        out = work
        for m in rx.finditer(work):
            a = table_a[m.group(1).lower()]
            b = table_b[m.group(2).lower()]
            values.add(a + b)
            values.add(a)
            values.add(b)
            out = out.replace(m.group(0), " " * len(m.group(0)), 1)
        return out

    work = _consume(_EN_COMPOUND_ORD_RE, _EN_TENS, _EN_ORD_ONES)
    work = _consume(_EN_COMPOUND_CARD_RE, _EN_TENS, _EN_ONES)

    for m in _EN_ORD_TENS_RE.finditer(work):
        values.add(_EN_ORD_TENS[m.group(1).lower()])
    for m in _EN_ORD_TEENS_RE.finditer(work):
        values.add(_EN_ORD_TEENS[m.group(1).lower()])
    for m in _EN_ORD_ONES_RE.finditer(work):
        values.add(_EN_ORD_ONES[m.group(1).lower()])
    for m in _EN_TENS_RE.finditer(work):
        values.add(_EN_TENS[m.group(1).lower()])
    for m in _EN_TEENS_RE.finditer(work):
        values.add(_EN_TEENS[m.group(1).lower()])
    for m in _EN_ONES_RE.finditer(work):
        values.add(_EN_ONES[m.group(1).lower()])

    return values


def _expected_en_forms(value: int) -> list[str]:
    """Human-readable hint of what the English could have used."""
    forms = [str(value)]
    inv_card_ones = {v: k for k, v in _EN_ONES.items()}
    inv_card_teens = {v: k for k, v in _EN_TEENS.items()}
    inv_card_tens = {v: k for k, v in _EN_TENS.items()}
    inv_ord_ones = {v: k for k, v in _EN_ORD_ONES.items()}
    inv_ord_teens = {v: k for k, v in _EN_ORD_TEENS.items()}
    inv_ord_tens = {v: k for k, v in _EN_ORD_TENS.items()}
    if value in inv_card_ones:
        forms += [inv_card_ones[value], inv_ord_ones[value]]
    elif value in inv_card_teens:
        forms += [inv_card_teens[value], inv_ord_teens[value]]
    elif value in inv_card_tens:
        forms += [inv_card_tens[value], inv_ord_tens[value]]
    elif 21 <= value <= 99 and value % 10 != 0:
        t, o = (value // 10) * 10, value % 10
        if t in inv_card_tens and o in inv_card_ones:
            forms += [f"{inv_card_tens[t]}-{inv_card_ones[o]}",
                      f"{inv_card_tens[t]}-{inv_ord_ones[o]}"]
    # Roman, when reasonable
    if 1 <= value <= 3999:
        forms.append(_int_to_roman(value))
    return forms


def _int_to_roman(n: int) -> str:
    pairs = [(1000,"M"), (900,"CM"), (500,"D"), (400,"CD"),
             (100,"C"), (90,"XC"), (50,"L"), (40,"XL"),
             (10,"X"), (9,"IX"), (5,"V"), (4,"IV"), (1,"I")]
    out = []
    for v, s in pairs:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


# ---------- segments ----------

def english_for(record: dict) -> str:
    """Latest translation text: translation_history[-1].english, else final_english."""
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


def validate(segments_path: Path, *,
             start_page: int | None, end_page: int | None,
             window: int = 1) -> list[dict]:
    """Scan a translated segments JSONL for numeral-preservation failures.

    Latin/English number extraction is exact-line; the English check uses a
    +/- ``window`` neighbour bleed (same page, same kind, ordered by
    seq/line) because line-keyed segmentation often pushes the English
    rendering of a Latin token onto the next line.
    """
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

    def window_english(seg: dict) -> str:
        key, i = pos[seg["seg_id"]]
        g = groups[key]
        lo, hi = max(0, i - window), min(len(g), i + window + 1)
        return " ".join(g[j]["english"] for j in range(lo, hi))

    flags: list[dict] = []
    for seg in segs:
        latin_nums = extract_latin_numerals(seg["latin"])
        if not latin_nums:
            continue
        win_en = window_english(seg)
        en_values = extract_english_numerals(win_en)
        seen_pairs: set[tuple[int, str]] = set()
        for value, token in latin_nums:
            if value in en_values:
                continue
            # Translator preserved the Latin token verbatim (proper name
            # like "Secundus of Abula", or untranslated technical term).
            # Don't penalise as a numeral miss — that's a different class
            # of error caught by the completeness/trivial-english check.
            if re.search(r"\b" + re.escape(token) + r"\b", win_en):
                continue
            key = (value, token.lower())
            if key in seen_pairs:
                continue  # same token already flagged for this segment
            seen_pairs.add(key)
            flags.append({
                "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                "flag": "MISSING_NUMERAL", "severity": _SEVERITY["MISSING_NUMERAL"],
                "latin_value": value, "latin_token": token,
                "expected_en": _expected_en_forms(value),
                "latin": _excerpt(seg["latin"]),
                "english": _excerpt(seg["english"]) or "(empty)",
                "note": f"Latin numeral {value} ('{token}') not found in English window",
            })
    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Numeral-preservation validator.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--window", type=int, default=1,
                   help="Neighbour lines each side to include when checking "
                        "the English for the Latin's numerals (suppresses "
                        "line-break false positives). 0 = strict line-exact. "
                        "Default 1.")
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
    if flags:
        print(f"  MISSING_NUMERAL  {len(flags):4d}  [{_SEVERITY['MISSING_NUMERAL']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
