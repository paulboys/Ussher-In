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

_SEVERITY = {"BANNED": "high", "MISSING_APPROVED": "medium", "DRIFT": "info"}


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


def _eng_pattern(s: str) -> re.Pattern:
    """Case-insensitive, word-boundaried matcher for an English rendering,
    tolerant of a simple plural ('church' -> church/churches)."""
    return re.compile(r"\b" + re.escape(s) + r"(?:e?s)?\b", re.IGNORECASE)


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
             start_page: int | None, end_page: int | None) -> list[dict]:
    flags: list[dict] = []
    # term -> {approved_variant -> [segment_ids]} for cross-corpus drift
    usage: dict[str, dict[str, list[str]]] = {e["term"]: {} for e in glossary}

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
        english = english_for(rec).strip()
        if not latin:
            continue
        seg_id = rec.get("segment_id", "")
        pid = rec.get("page_id", "")

        for e in glossary:
            if not e["_latin_re"].search(latin):
                continue  # term not in this segment's Latin

            banned_hit = next((b for b, rx in e["_banned_re"] if rx.search(english)), None)
            if banned_hit:
                flags.append({
                    "segment_id": seg_id, "page_id": pid, "term": e["term"],
                    "flag": "BANNED", "severity": _SEVERITY["BANNED"],
                    "found": banned_hit, "expected": e.get("approved", []),
                    "latin": _excerpt(latin), "english": _excerpt(english),
                    "note": e.get("note", ""),
                })

            approved_hits = [a for a, rx in e["_approved_re"] if rx.search(english)]
            if approved_hits:
                for a in approved_hits:
                    usage[e["term"]].setdefault(a, []).append(seg_id)
            elif not banned_hit:
                # term present in Latin, no approved English found, nothing banned
                flags.append({
                    "segment_id": seg_id, "page_id": pid, "term": e["term"],
                    "flag": "MISSING_APPROVED", "severity": _SEVERITY["MISSING_APPROVED"],
                    "found": None, "expected": e.get("approved", []),
                    "latin": _excerpt(latin), "english": _excerpt(english) or "(empty)",
                    "note": e.get("note", ""),
                })

    # Cross-corpus drift: term rendered with >1 distinct approved variant.
    for term, variants in usage.items():
        if len(variants) > 1:
            flags.append({
                "segment_id": "", "page_id": "", "term": term,
                "flag": "DRIFT", "severity": _SEVERITY["DRIFT"],
                "found": {v: len(ids) for v, ids in variants.items()},
                "expected": sorted(variants),
                "latin": "", "english": "",
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
    args = p.parse_args()

    if not args.segments.exists():
        print(f"segments file not found: {args.segments}", file=sys.stderr)
        return 2
    if not args.glossary.exists():
        print(f"glossary file not found: {args.glossary}", file=sys.stderr)
        return 2

    glossary = load_glossary(args.glossary)
    flags = validate(args.segments, glossary,
                     start_page=args.start_page, end_page=args.end_page)

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
    for flag in ("BANNED", "MISSING_APPROVED", "DRIFT"):
        if by_flag.get(flag):
            print(f"  {flag:16s} {by_flag[flag]:4d}  [{_SEVERITY[flag]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
