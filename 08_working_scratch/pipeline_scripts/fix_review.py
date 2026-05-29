"""Render an editor-facing side-by-side review document from propose_fix.py.

Reads ``ch*_fidelity_fixes.jsonl``, dedupes by unit_id (keeping a
successful row over any quota/error row), groups by the judge's
content_fidelity score (cf=1 catastrophic first), and emits a Markdown
file with one block per unit: judge reason, Latin, prior English,
proposed English, fixer reason, and a one-line decision template the
editor fills in (accept / reject / edit).

Designed to live alongside ``fidelity_report.py`` as the
post-author-fidelity human-review surface.

Usage
-----
    python fix_review.py \\
        --fixes-jsonl 08_working_scratch/phase3b/ch1_fidelity_fixes.jsonl \\
        --label "Chapter 1 (ussher_v5)" \\
        --output 04_translation_work/ab/antiquitates_ch1/ch1_fix_review.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _page_of(uid: str) -> int | None:
    m = re.search(r"p(\d+)", uid or "")
    return int(m.group(1)) if m else None


def _line_of(uid: str) -> int:
    m = re.search(r"_l(\d+)\b", uid or "") or re.search(r"_(\d+)\b", uid or "")
    return int(m.group(1)) if m else 0


def _score_str(s: dict, key: str) -> str:
    v = s.get(key)
    if v is None:
        return "?"
    return str(v)


def load_fixes(path: Path) -> list[dict]:
    """Dedupe by unit_id, keeping the latest successful row over any error row."""
    best: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        uid = str(rec.get("unit_id") or "")
        if not uid:
            continue
        is_ok = (not rec.get("error")) and rec.get("proposed_english") is not None
        prev = best.get(uid)
        # Prefer ok rows; among multiple ok rows prefer the last one seen.
        if prev is None:
            best[uid] = rec
        elif is_ok:
            prev_ok = (not prev.get("error")) and prev.get("proposed_english") is not None
            if not prev_ok or True:  # last successful wins
                best[uid] = rec
    return list(best.values())


def _block(rec: dict, latin_map: dict[str, str]) -> str:
    uid = rec["unit_id"]
    page = rec.get("page") or _page_of(uid)
    scores = rec.get("judge_scores") or {}
    judge_reason = (rec.get("judge_reason") or "").strip()
    latin = (latin_map.get(uid) or "").rstrip()
    prior_eng = (rec.get("original_english") or "").rstrip()
    proposed = (rec.get("proposed_english") or "").rstrip()
    fix_reason = (rec.get("fix_reason") or "").strip()
    no_change = rec.get("no_change")
    model = rec.get("fix_model", "")

    header = f"### `{uid}` &nbsp;·&nbsp; page p{page:04d}" if isinstance(page, int) else f"### `{uid}`"
    score_line = (
        f"**Scores:** cf={_score_str(scores,'content_fidelity')} · "
        f"rf={_score_str(scores,'register_fidelity')} · "
        f"gp={_score_str(scores,'greek_preservation')} · "
        f"ph={_score_str(scores,'paraphrase_handling')}"
        + (f"  &nbsp;·&nbsp; **NO CHANGE proposed** (fixer disagreed with judge)" if no_change else "")
    )

    parts = [
        header,
        score_line,
        "",
        f"**Judge:** {judge_reason}" if judge_reason else "_(no judge reason recorded)_",
        "",
        "**Latin source:**",
        "```",
        latin or "(not found in inputs file)",
        "```",
        "",
        "**Prior English:**",
        "```",
        prior_eng or "(empty)",
        "```",
        "",
        "**Proposed English:**" + (f" _(model: {model})_" if model else ""),
        "```",
        proposed or "(empty)",
        "```",
        "",
        f"**Fixer:** {fix_reason}" if fix_reason else "",
        "",
        "**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)",
        "",
        "---",
        "",
    ]
    return "\n".join(p for p in parts if p is not None)


def build(fixes: list[dict], *, label: str, source: Path,
          latin_map: dict[str, str]) -> str:
    n = len(fixes)
    n_nc = sum(1 for r in fixes if r.get("no_change"))
    n_real = n - n_nc
    cf_count: Counter = Counter()
    for r in fixes:
        cf = (r.get("judge_scores") or {}).get("content_fidelity")
        cf_count[cf] += 1

    parts: list[str] = []
    parts.append(f"# Fix Review — {label}")
    parts.append("")
    parts.append(f"Source: `{source}`  ")
    parts.append(f"Units with proposed corrections: **{n}**  ")
    parts.append(f"Of which **{n_real}** are real changes; **{n_nc}** marked NO CHANGE (fixer disagreed with the judge — the prior English is being kept).")
    parts.append("")
    parts.append("### Distribution by judge content-fidelity score")
    parts.append("")
    parts.append("| cf | n |")
    parts.append("|---:|---:|")
    for cf in sorted(cf_count, key=lambda x: (x is None, x or 0)):
        label_cf = "—" if cf is None else cf
        parts.append(f"| {label_cf} | {cf_count[cf]} |")
    parts.append("")
    parts.append("### How to review")
    parts.append("")
    parts.append("Walk top-to-bottom. cf=1 (catastrophic) comes first. For each block:")
    parts.append("")
    parts.append("- Compare **Prior English** with **Proposed English** against the judge's diagnosis.")
    parts.append("- Check the box next to your decision. If you choose **edit**, write your edited version on the line below the decision.")
    parts.append("- A separate `apply_fixes.py` pass (to be built) will read this file and apply your decisions back into `segments_with_translations.jsonl`.")
    parts.append("")
    parts.append("---")
    parts.append("")

    # Sort: cf=1 first, then 2, 3, 4, with 'na'/None last; within cf, by page then line.
    def sort_key(r: dict):
        cf = (r.get("judge_scores") or {}).get("content_fidelity")
        cf_rank = cf if isinstance(cf, int) else 99
        uid = r.get("unit_id", "")
        return (cf_rank, _page_of(uid) or 0, _line_of(uid))

    fixes_sorted = sorted(fixes, key=sort_key)
    # Section headers per cf bucket
    current_cf = None
    for r in fixes_sorted:
        cf = (r.get("judge_scores") or {}).get("content_fidelity")
        if cf != current_cf:
            label_cf = "cf = ?" if cf is None else f"cf = {cf}"
            tier = {1: " — catastrophic", 2: " — moderate",
                    3: " — minor", 4: " — borderline (flagged on rf/gp/ph)"}.get(cf, "")
            parts.append("")
            parts.append(f"## {label_cf}{tier}")
            parts.append("")
            current_cf = cf
        parts.append(_block(r, latin_map))

    return "\n".join(parts) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixes-jsonl", required=True, type=Path)
    p.add_argument("--inputs-jsonl", required=True, type=Path,
                   help="bridged judge input — supplies Latin per unit_id "
                        "(e.g. ch1_fidelity_input.jsonl)")
    p.add_argument("--label", required=True,
                   help="report header, e.g. 'Chapter 1 (ussher_v5)'")
    p.add_argument("--output", required=True, type=Path,
                   help="path to write the Markdown review document")
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    args = p.parse_args()

    latin_map: dict[str, str] = {}
    for raw in args.inputs_jsonl.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        r = json.loads(raw)
        uid = str(r.get("unit_id") or "")
        if uid:
            latin_map[uid] = r.get("latin_concat", "")

    fixes = load_fixes(args.fixes_jsonl)
    if args.start_page is not None or args.end_page is not None:
        fixes = [
            r for r in fixes
            if (pn := _page_of(r.get("unit_id", ""))) is not None
            and (args.start_page is None or pn >= args.start_page)
            and (args.end_page is None or pn <= args.end_page)
        ]
    fixes = [r for r in fixes
             if not r.get("error")
             and r.get("proposed_english") is not None]

    md = build(fixes, label=args.label, source=args.fixes_jsonl,
               latin_map=latin_map)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"Wrote {args.output} ({len(fixes)} unit blocks; "
          f"{len(latin_map)} Latin sources loaded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
