
"""Phase A neuro-symbolic layer: controlled-glossary consistency validator.

The deterministic half of the LLM-drafts / symbolic-layer-validates split.
Claude produces the creative translation; this layer checks the draft
against a formalized termbase and emits EDITOR FLAGS — never silent
rewrites. It runs post-hoc over a translated segments JSONL, so it adds
zero attention-budget cost to the prompt (the §7.3 ablation lesson:
consistency enforcement belongs in code, not in the prompt).

Flag types
----------
BANNED            A forbidden rendering of a glossary term appears in the
                  English. (severity: high)
SCRIPTURE_        The English reproduces a received English Bible (KJV /
SUBSTITUTION      Douay) instead of translating the Vulgate Latin Ussher
                  actually printed. Ussher argues FROM the Latin wording, so
                  reciting a remembered verse silently swaps out his
                  evidence — and it is near-invisible in review because the
                  received English reads beautifully. Raised by glossary
                  entries carrying "category": "scripture". (severity: high)
ARCHAISM          Archaic diction (thou/hath/unto/...) in a body rendering.
                  The target register is modern academic English, so this
                  usually means a received Bible was recited — it catches
                  verses not yet enumerated in the glossary. (severity:
                  medium)
MISSING_APPROVED  The Latin term is present but no approved English
                  rendering was found — possible drift to an unlisted
                  synonym, OR a legitimate Rule 1 collapse / empty render.
                  Editor decides. (severity: medium)
DRIFT             Across the run, one term was rendered with >1 distinct
                  approved variant (e.g. ecclesia -> church vs congregation).
                  Informational: confirm each is contextually justified.
                  (severity: info)

Glossary format: see glossary_ussher.jsonl. One JSON entry per line;
lines lacking both "term" and "latin_pattern" are skipped.

Usage
-----
    python glossary_validate.py \\
        --segments 03_segmented_text/part1/segments_with_translations.jsonl \\
        --glossary 08_working_scratch/pipeline_scripts/glossary_ussher.jsonl \\
        --output   08_working_scratch/phase3b/glossary_flags.jsonl \\
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

_HERE = Path(__file__).resolve().parent
_DEFAULT_SEGMENTS = Path("03_segmented_text/part1/segments_with_translations.jsonl")
_DEFAULT_GLOSSARY = _HERE / "glossary_ussher.jsonl"
_DEFAULT_OUTPUT = Path("08_working_scratch/phase3b/glossary_flags.jsonl")

_SEVERITY = {
    "BANNED": "high",
    "SCRIPTURE_SUBSTITUTION": "high",
    "ARCHAISM": "medium",
    "MISSING_APPROVED": "medium",
    "DRIFT": "info",
}

# Caret sentinels ('^b') mark footnote anchors in the English. They are
# pipeline metadata, not text, and must not defeat a phrase match that
# happens to straddle one.
_CARET_RE = re.compile(r"\^[A-Za-z0-9]{1,2}")


def _strip_carets(text: str) -> str:
    return _CARET_RE.sub("", text or "")


# Archaic English that betrays recitation of a received Bible (KJV/Douay)
# rather than translation of Ussher's Latin. Our target register is modern
# academic English, so any of these in a body rendering is a red flag —
# including for verses not yet enumerated in the glossary.
_ARCHAISM_RE = re.compile(
    r"\b(?:thee|thou|thy|thine|ye|hath|doth|dost|saith|shalt|wilt|"
    r"cometh|goeth|whosoever|verily|thereof|unto)\b",
    re.IGNORECASE,
)


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
    """Within-page ordering of a segment: prefer the record's seq, else the
    trailing number of its segment_id (line/footnote index)."""
    seq = record.get("seq")
    if isinstance(seq, int):
        return seq
    m = re.search(r"(\d+)\D*$", str(record.get("segment_id") or ""))
    return int(m.group(1)) if m else 0


def _eng_pattern(s: str) -> re.Pattern:
    """Case-insensitive, word-boundaried matcher for an English rendering,
    tolerant of a simple plural ('church' -> church/churches).

    Whitespace in a multi-word phrase is matched flexibly (``\\s+``) so a
    line-wrapped or re-spaced rendering of a scripture phrase still matches.
    """
    escaped = re.escape(s)
    # re.escape may or may not backslash a space depending on version; handle both.
    escaped = escaped.replace(r"\ ", r"\s+").replace(" ", r"\s+")
    return re.compile(r"\b" + escaped + r"(?:e?s)?\b", re.IGNORECASE)


def load_glossary(path: Path) -> list[dict]:
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if not e.get("term") or not e.get("latin_pattern"):
            continue  # skip header / malformed lines
        e["_latin_re"] = re.compile(e["latin_pattern"], re.IGNORECASE)
        e["_approved_re"] = [(a, _eng_pattern(a)) for a in e.get("approved", [])]
        e["_banned_re"] = [(b, _eng_pattern(b)) for b in e.get("banned", [])]
        entries.append(e)
    return entries


def _excerpt(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def validate(segments_path: Path, glossary: list[dict], *,
             start_page: int | None, end_page: int | None,
             window: int = 1) -> list[dict]:
    """Scan a translated segments JSONL against the glossary.

    The English rendering of a glossary term often lands on the *adjacent*
    line when the Latin token sits at a line break (line-keyed segmentation).
    To suppress those false positives, the approved/banned check looks at the
    segment's English plus ``window`` neighbours on either side (same page,
    same kind, ordered by seq/line number). ``--window 0`` restores strict
    line-exact matching. DRIFT remains corpus-wide.
    """
    # ---- load in-range segments ----
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

    # ---- per-(page, kind) ordered groups + position map for windowing ----
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

    # ---- scan ----
    flags: list[dict] = []
    usage: dict[str, dict[str, set]] = {e["term"]: {} for e in glossary}
    for seg in segs:
        win = _strip_carets(window_english(seg))

        # Archaic English in a body rendering betrays recitation of a received
        # Bible rather than translation of Ussher's Latin. Checked on the
        # segment's own English (not the window) so the flag names the culprit.
        if seg["kind"] == "body":
            archaic = sorted({m.group(0).lower()
                              for m in _ARCHAISM_RE.finditer(_strip_carets(seg["english"]))})
            if archaic:
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "term": "(archaic register)", "flag": "ARCHAISM",
                    "severity": _SEVERITY["ARCHAISM"],
                    "found": archaic, "expected": ["modern English"],
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": "Archaic diction suggests a received English Bible "
                            "(KJV/Douay) was recited instead of translating "
                            "Ussher's Latin. Confirm against the Latin.",
                })

        # Carets are footnote-anchor sentinels, not text. A marker sitting
        # inside a quoted verse ('A^w summo caelo') would otherwise defeat the
        # Latin pattern and silently disable the check.
        seg_latin = _strip_carets(seg["latin"])
        for e in glossary:
            if not e["_latin_re"].search(seg_latin):
                continue  # term not in this segment's Latin

            is_scripture = e.get("category") == "scripture"
            banned_hit = next((b for b, rx in e["_banned_re"] if rx.search(win)), None)
            if banned_hit:
                kind = "SCRIPTURE_SUBSTITUTION" if is_scripture else "BANNED"
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "term": e["term"], "flag": kind, "severity": _SEVERITY[kind],
                    "found": banned_hit, "expected": e.get("approved", []),
                    "latin": _excerpt(seg["latin"]), "english": _excerpt(win),
                    "note": e.get("note", ""),
                })

            approved_hits = [a for a, rx in e["_approved_re"] if rx.search(win)]
            if approved_hits:
                for a in approved_hits:
                    usage[e["term"]].setdefault(a, set()).add(seg["seg_id"])
            elif not banned_hit and e.get("approved"):
                # Term in Latin, no approved English in the window, nothing
                # banned. Entries with an empty 'approved' list are
                # banned-only detectors (e.g. scripture substitution: there is
                # no single required rendering, only forbidden ones), so they
                # never raise MISSING_APPROVED.
                flags.append({
                    "segment_id": seg["seg_id"], "page_id": seg["page_id"],
                    "term": e["term"], "flag": "MISSING_APPROVED",
                    "severity": _SEVERITY["MISSING_APPROVED"],
                    "found": None, "expected": e.get("approved", []),
                    "latin": _excerpt(seg["latin"]),
                    "english": _excerpt(seg["english"]) or "(empty)",
                    "note": e.get("note", ""),
                })

    # Drift: term rendered with >1 distinct approved variant across the run.
    for term, variants in usage.items():
        if len(variants) > 1:
            flags.append({
                "segment_id": "", "page_id": "", "term": term,
                "flag": "DRIFT", "severity": _SEVERITY["DRIFT"],
                "found": {v: len(ids) for v, ids in variants.items()},
                "expected": sorted(variants), "latin": "", "english": "",
                "note": "Term rendered with multiple approved variants; confirm "
                        "each occurrence is contextually justified.",
            })
    return flags


def main() -> int:
    p = argparse.ArgumentParser(description="Controlled-glossary consistency validator.")
    p.add_argument("--segments", type=Path, default=_DEFAULT_SEGMENTS)
    p.add_argument("--glossary", type=Path, default=_DEFAULT_GLOSSARY)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--window", type=int, default=1,
                   help="Neighbour lines each side to include when checking "
                        "approved/banned renderings (suppresses line-break "
                        "false positives). 0 = strict line-exact. Default 1.")
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2
    if not args.glossary.exists():
        print(f"glossary file not found: {args.glossary}", file=sys.stderr)
        return 2

    glossary = load_glossary(args.glossary)
    flags = validate(args.segments, glossary,
                     start_page=args.start_page, end_page=args.end_page,
                     window=args.window)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as h:
        for f in flags:
            h.write(json.dumps(f, ensure_ascii=False) + "\n")

    by_flag: dict[str, int] = {}
    for f in flags:
        by_flag[f["flag"]] = by_flag.get(f["flag"], 0) + 1
    print(f"Loaded {len(glossary)} glossary terms; scanned {args.segments}")
    rng = ""
    if args.start_page is not None or args.end_page is not None:
        rng = f" (pages {args.start_page}-{args.end_page})"
    print(f"Wrote {len(flags)} flag(s) to {args.output}{rng}")
    # Iterate _SEVERITY so a newly-added flag kind can never be silently
    # omitted from the summary (SCRIPTURE_SUBSTITUTION was, once).
    for flag in _SEVERITY:
        if by_flag.get(flag):
            print(f"  {flag:22s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
