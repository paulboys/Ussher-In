
"""Phase A+ neuro-symbolic layer: citation / title-preservation validator.

Ussher's citations come in two styles, both of which the translator can
silently degrade:

1. Standard citations -
   ``Camden. Britann. pag. 47, 48. edit. Londini ann. 1607.``
   -> English carries each component (``Camden, Britannia, pages 47, 48,
   London edition of the year 1607``). Each Latin abbreviation has an
   English counterpart.

2. Biblical citations -
   ``Act. cap. 17. ver. 30.`` -> English collapses to ``Acts 17:30``.
   ``cap.`` and ``ver.`` are absorbed into the ``book chapter:verse``
   convention, so a missing literal ``chapter`` is not a defect when
   ``17:30`` (or similar) appears in the window.

Flag classes
------------
CITATION_KEYWORD_DROPPED   Latin citation keyword (``lib.``, ``cap.``,
                           ``ver.``, ``pag.``, ``tom.``, ``edit.``,
                           ``epigram.``, ``proœmio``, ``epist.``,
                           ``part.``, ``op.``) has no English equivalent
                           in the window. For ``cap.`` / ``ver.`` the
                           ``\\d+:\\d+`` biblical pattern counts as an
                           equivalent.

BIBLICAL_BOOK_DROPPED      A Latin biblical-book abbreviation has no
                           corresponding English book name in the window.

Author / work proper-name preservation (``Camden``, ``Britann.``,
``Xiphilin.``, etc.) is out of scope for v1 - too noisy to flag without
an explicit author/work lexicon.

Numbers in citations are NOT re-checked here - they belong to
``numeral_validate.py``.

Usage
-----
    python citation_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --output   08_working_scratch/phase3b/citation_flags.jsonl \\
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
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/citation_flags.jsonl")

_SEVERITY = {
    "CITATION_KEYWORD_DROPPED": "medium",
    "BIBLICAL_BOOK_DROPPED":    "high",
}


# Each entry: (latin_keyword, english_match_patterns, human_expected_label).
# The english patterns are joined with `|` into a single regex (case-i).
# Patterns include the chapter:verse fallback for cap./ver. since the
# biblical short-form absorbs them.
_CHV = r"\d+\s*:\s*\d+"

_CITATION_KEYWORDS: list[tuple[str, list[str], list[str]]] = [
    ("lib",     [r"\bbooks?\b", r"\bbk\.", r"\bvolumes?\b"],
                 ["book", "bk.", "volume"]),
    ("cap",     [r"\bchapters?\b", r"\bchap\.", r"\bchaps?\.", _CHV],
                 ["chapter", "chap.", "N:N"]),
    ("ver",     [r"\bverses?\b", r"\blines?\b", r"\bv\.", _CHV],
                 ["verse", "line", "v.", "N:N"]),
    ("pag",     [r"\bpages?\b", r"\bpp?\."],
                 ["page", "p.", "pp."]),
    ("tom",     [r"\bvolumes?\b", r"\bvol\.", r"\btomes?\b"],
                 ["volume", "vol.", "tome"]),
    ("edit",    [r"\beditions?\b", r"\bed\."],
                 ["edition", "ed."]),
    ("epigram", [r"\bepigrams?\b"],
                 ["epigram"]),
    ("epist",   [r"\bepistles?\b", r"\bletters?\b", r"\bep\."],
                 ["epistle", "letter", "ep."]),
    ("part",    [r"\bparts?\b", r"\bsections?\b", r"\bsect\."],
                 ["part", "section", "sect."]),
    ("op",      [r"\bworks\b", r"\bopera\b", r"\bop\."],
                 ["Works", "opera", "op."]),
]

# proœmio handled separately because the Latin form is a full word, not an
# abbreviation with trailing period.
_PROOEM_PATTERNS = [
    r"\bproems?\b",
    r"\bprooemium\b",
    r"\bpreface\b",
    r"\bintroductions?\b",
]

# Latin biblical-book abbreviations -> English book-name regex.
# Stem-matched (\b{lat}) followed by a required period (\b{lat}\.) so the
# Latin word "rom" inside "romanus" doesn't trigger.
#
# Even with the trailing-period guard, "Rom." / "Eccl." / "Num." also serve
# as Latin adjective/noun abbreviations ("Roman", "ecclesiastical",
# "number") — see ``_BIBLICAL_CONTEXT_RE`` below for the canonical-citation
# context filter that suppresses those uses. The one residual false-positive
# pattern this validator does NOT catch is ``<NounAbbrev>. <Book>. cap.``
# (e.g. ``Martyrolog. Rom. cap. 9.`` = "Roman Martyrology, chapter 9"),
# because ``cap.`` does follow — the disambiguator is the preceding noun.
# Editors should expect to reject the rare flag of that shape.
_BIBLICAL_BOOKS: list[tuple[str, str, str]] = [
    # (latin_stem, english_regex, expected_label)
    ("matth",  r"\bmatthew\b",                                "Matthew"),
    ("marc",   r"\bmark\b",                                   "Mark"),
    ("luc",    r"\bluke\b",                                   "Luke"),
    ("joh",    r"\bjohn\b",                                   "John"),
    ("joan",   r"\bjohn\b",                                   "John"),
    ("act",    r"\bacts?\b",                                  "Acts"),
    ("rom",    r"\bromans\b",                                 "Romans"),
    ("cor",    r"\bcorinthians?\b",                           "Corinthians"),
    ("gal",    r"\bgalatians?\b",                             "Galatians"),
    ("ephes",  r"\bephesians?\b",                             "Ephesians"),
    ("phil",   r"\bphilippians?\b",                           "Philippians"),
    ("coloss", r"\bcolossians?\b",                            "Colossians"),
    ("colos",  r"\bcolossians?\b",                            "Colossians"),
    ("thess",  r"\bthessalonians?\b",                         "Thessalonians"),
    ("tim",    r"\btimothy\b",                                "Timothy"),
    ("tit",    r"\btitus\b",                                  "Titus"),
    ("philem", r"\bphilemon\b",                               "Philemon"),
    ("hebr",   r"\bhebrews?\b",                               "Hebrews"),
    ("jac",    r"\bjames\b",                                  "James"),
    ("pet",    r"\bpeter\b",                                  "Peter"),
    ("apoc",   r"\b(?:revelation|apocalypse)\b",              "Revelation"),
    ("apocal", r"\b(?:revelation|apocalypse)\b",              "Revelation"),
    ("esai",   r"\bisaiah\b",                                 "Isaiah"),
    ("esa",    r"\bisaiah\b",                                 "Isaiah"),
    ("isai",   r"\bisaiah\b",                                 "Isaiah"),
    ("jer",    r"\bjeremiah\b",                               "Jeremiah"),
    ("ezech",  r"\bezekiel\b",                                "Ezekiel"),
    ("dan",    r"\bdaniel\b",                                 "Daniel"),
    ("psal",   r"\bpsalms?\b",                                "Psalm"),
    ("prov",   r"\bproverbs\b",                               "Proverbs"),
    ("eccl",   r"\becclesiastes\b",                           "Ecclesiastes"),
    ("cant",   r"\b(?:song of songs|canticles?)\b",           "Canticles"),
    ("gen",    r"\bgenesis\b",                                "Genesis"),
    ("exod",   r"\bexodus\b",                                 "Exodus"),
    ("levit",  r"\bleviticus\b",                              "Leviticus"),
    ("num",    r"\bnumbers\b",                                "Numbers"),
    ("deut",   r"\bdeuteronomy\b",                            "Deuteronomy"),
    ("jos",    r"\bjoshua\b",                                 "Joshua"),
    ("jud",    r"\bjudges\b",                                 "Judges"),
]


def _compile_keyword_rules():
    rules = []
    for kw, en_pats, expected in _CITATION_KEYWORDS:
        lat_re = re.compile(r"\b" + kw + r"\b\.", re.IGNORECASE)
        en_re = re.compile("|".join(en_pats), re.IGNORECASE)
        rules.append((kw + ".", lat_re, en_re, expected, "keyword"))
    # proœmio is a word, not an abbreviation
    rules.append((
        "proœmio",
        re.compile(r"\bpro[œoe]+mi[oa]\b", re.IGNORECASE),
        re.compile("|".join(_PROOEM_PATTERNS), re.IGNORECASE),
        ["proem", "preface"],
        "keyword",
    ))
    return rules


def _compile_book_rules():
    rules = []
    for lat, en_pat, expected in _BIBLICAL_BOOKS:
        lat_re = re.compile(r"\b" + lat + r"\b\.", re.IGNORECASE)
        en_re = re.compile(en_pat, re.IGNORECASE)
        rules.append((lat.capitalize() + ".", lat_re, en_re, [expected], "book"))
    return rules


# Canonical biblical-citation context: a real biblical reference is followed
# within ~15 chars by either ``cap.`` (chapter) or ``<digit>. ver.`` (Psal.
# 97. ver. 1.). When neither follows, the Latin "Rom." / "Eccl." / "Num."
# is overwhelmingly an adjective or count noun, not a book.
_BIBLICAL_CONTEXT_RE = re.compile(
    r"^.{0,15}?(?:\bcap\b\.|\d+\s*\.\s*ver\b\.|\d+\s*:\s*\d+)",
    re.IGNORECASE | re.DOTALL,
)


_KEYWORD_RULES = _compile_keyword_rules()
_BOOK_RULES = _compile_book_rules()


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


def validate(segments_path: Path, *,
             start_page: int | None, end_page: int | None,
             window: int = 1) -> list[dict]:
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

    def _check_rules(seg: dict, rules, flag_name: str) -> None:
        win_en = window_english(seg)
        seen: set[str] = set()
        for label, lat_re, en_re, expected, ttype in rules:
            m = lat_re.search(seg["latin"])
            if not m:
                continue
            if ttype == "book":
                # Require canonical biblical-citation context after the
                # Latin abbreviation; otherwise "Rom." / "Num." / "Eccl."
                # are almost always adjective/count noun usages.
                tail = seg["latin"][m.end():]
                if not _BIBLICAL_CONTEXT_RE.match(tail):
                    continue
            if en_re.search(win_en):
                continue
            if label in seen:
                continue
            seen.add(label)
            flags.append({
                "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                "flag": flag_name, "severity": _SEVERITY[flag_name],
                "term": label, "term_type": ttype, "expected_en": expected,
                "latin": _excerpt(seg["latin"]),
                "english": _excerpt(seg["english"]) or "(empty)",
                "note": f"Latin citation term '{label}' has no English equivalent in window.",
            })

    for seg in segs:
        _check_rules(seg, _KEYWORD_RULES, "CITATION_KEYWORD_DROPPED")
        _check_rules(seg, _BOOK_RULES, "BIBLICAL_BOOK_DROPPED")

    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Citation / title-preservation validator.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--window", type=int, default=1,
                   help="Neighbour lines each side included in the English "
                        "search. Citations frequently cross a line break. "
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
    by_flag: dict[str, int] = {}
    for f in flags:
        by_flag[f["flag"]] = by_flag.get(f["flag"], 0) + 1
    for flag in ("CITATION_KEYWORD_DROPPED", "BIBLICAL_BOOK_DROPPED"):
        if by_flag.get(flag):
            print(f"  {flag:26s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
