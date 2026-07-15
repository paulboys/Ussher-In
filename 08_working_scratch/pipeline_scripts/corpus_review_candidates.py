"""Turn the raw miner output into a classicist-review worksheet.

Consumes ``phrases.tsv`` / ``words.tsv`` from ``corpus_phrase_mine.py`` and
produces a curated, decision-per-concept worksheet:

- Inflectional variants are collapsed by ``loose_key`` so the reviewer makes
  ONE ruling per concept (``libero arbitrio`` / ``liberi arbitrii`` /
  ``liberum arbitrium`` -> one row), with the variants listed for context.
- Split into "source authors / proper names" and "recurring terms", the two
  rule categories the ch1 review produced.
- Each row carries frequency + page-spread + a real in-context example, and
  BLANK ``English rendering`` / ``note`` columns to fill.

Also emits ``candidates.glossary_seed.jsonl`` — one inert record per concept
(empty ``approved``/``banned`` -> raises no validator flag) mapped to the
``glossary_ussher.jsonl`` schema, so a filled-in worksheet graduates into the
live glossary mechanically. It is written to the analysis dir, NOT merged
into the live glossary; the reviewer decides what graduates.

Usage
-----
    python corpus_review_candidates.py                 # top 70 terms / 60 names
    python corpus_review_candidates.py --top-terms 100 --top-names 80
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
WORKSPACE = _HERE.parent.parent
DEFAULT_DIR = WORKSPACE / "09_analysis" / "phrase_mining"


def _load_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _cluster(rows: list[dict]) -> list[dict]:
    """Group rows sharing a loose_key into one concept, most-frequent surface
    as the representative; variants and totals attached."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["loose_key"]].append(r)
    out = []
    for key, members in groups.items():
        members.sort(key=lambda r: -int(r["count"]))
        rep = members[0]
        total = sum(int(m["count"]) for m in members)
        variants = [m["phrase"] for m in members]
        out.append({
            "term": rep["phrase"],
            "variants": variants,
            "total": total,
            "pages": max(int(m["pages"]) for m in members),
            "example": rep["example"],
            "proper": rep["proper"] == "True",
        })
    out.sort(key=lambda c: -c["total"])
    return out


def _md_table(concepts: list[dict]) -> list[str]:
    lines = ["| term (variants) | count | pages | example | English rendering | note |",
             "|---|---|---|---|---|---|"]
    for c in concepts:
        variants = c["term"]
        extra = [v for v in c["variants"] if v != c["term"]]
        if extra:
            variants += " · " + ", ".join(extra[:4])
        ex = c["example"].replace("|", "\\|")
        lines.append(f"| {variants} | {c['total']} | {c['pages']} | {ex} |  |  |")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build classicist-review worksheet from miner output.")
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--top-terms", type=int, default=70)
    ap.add_argument("--top-names", type=int, default=60)
    ap.add_argument("--min-pages", type=int, default=3,
                    help="Require a concept span at least this many pages "
                         "(a work-wide term, not a one-page quirk).")
    args = ap.parse_args(argv)

    phrases = _load_tsv(args.dir / "phrases.tsv")
    names_src = [r for r in phrases if r["proper"] == "True"]
    terms_src = [r for r in phrases if r["proper"] != "True"]

    names = [c for c in _cluster(names_src) if c["pages"] >= args.min_pages][:args.top_names]
    terms = [c for c in _cluster(terms_src) if c["pages"] >= args.min_pages][:args.top_terms]

    out_md = args.dir / "candidates_for_review.md"
    lines = [
        "# Ussher *Antiquitates* — terminology review worksheet",
        "",
        "Auto-mined recurring words/phrases across the OCR'd corpus "
        f"(p0032–p0567), curated for consistency-rule decisions. Inflectional "
        "variants are collapsed into one row (variants listed after `·`); "
        "decide ONCE per concept.",
        "",
        "**For each row, fill in:**",
        "- **English rendering** — the settled translation to use everywhere "
        "(leave blank if no fixed rule is warranted).",
        "- **note** — any consistency trap, or a *banned* rendering to reject "
        "(e.g. \"NOT 'Spain' — use 'the Spains'\").",
        "",
        "Answers map directly onto the glossary schema "
        "(`term` / `approved` / `banned` / `note` / `category`); the filled "
        "worksheet graduates into `glossary_ussher.jsonl` mechanically.",
        "",
        f"## Source authors & proper names ({len(names)})",
        "",
        "The medieval chroniclers Ussher cites and the persons/places named. "
        "These are the highest-value consistency rules (one settled English "
        "form per name).",
        "",
    ]
    lines += _md_table(names)
    lines += [
        "",
        f"## Recurring terms & phrases ({len(terms)})",
        "",
        "Doctrinal, ecclesiastical, and chronological vocabulary. Watch for "
        "technical theological terms that must not be flattened.",
        "",
    ]
    lines += _md_table(terms)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Inert glossary seed (empty approved/banned -> no validator flag).
    seed = args.dir / "candidates.glossary_seed.jsonl"
    with seed.open("w", encoding="utf-8") as fh:
        for c, cat in ([(c, "proper_name") for c in names]
                       + [(c, "term") for c in terms]):
            fh.write(json.dumps({
                "term": c["term"],
                "latin_pattern": c["term"],
                "approved": [],
                "banned": [],
                "note": f"[REVIEW] variants: {', '.join(c['variants'])}; "
                        f"{c['total']}x over {c['pages']} pages",
                "category": cat,
                "_needs_review": True,
            }, ensure_ascii=False) + "\n")

    print(f"names: {len(names)} concepts | terms: {len(terms)} concepts")
    print(f"Wrote {out_md}")
    print(f"Wrote {seed}  (inert seed — not merged into live glossary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
