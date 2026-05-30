"""Apply propose_fix.py corrections back into segments_with_translations.jsonl.

Audit-preserving: the original ``translation_history`` is kept intact;
the fix is appended as a NEW entry with ``stage = "fidelity_fix"`` so
the provenance chain (machine_draft -> fidelity_fix -> [polish]) is
readable in the segments file. polish_translations.py reads
``translation_history[-1].english``, so the appended entry is what the
polish pass will see.

Tier-based filter
-----------------
Default ``--max-cf 1`` applies only the catastrophic tier (cf == 1)
from the judge — the units where the literal English was genuinely
broken (bare em-dash, dropped clauses, wrong numerals, etc.) and where
the fixer's proposals are demonstrably restorations. Pass ``--max-cf 2``
to also apply the moderate tier; ``--max-cf 3`` for everything. Units
the fixer marked ``no_change=true`` are skipped (no fix to apply).

Atomic
------
The segments file is rewritten via ``temp + rename``, the same
write_segments pattern translate_segments uses, so a crash mid-write
leaves the prior good file intact.

Usage
-----
    python apply_fixes.py \\
        --fixes-jsonl   08_working_scratch/phase3b/ch1_fidelity_fixes.jsonl \\
        --scores-jsonl  08_working_scratch/phase3b/ch1_fidelity_scores.jsonl \\
        --segments-path 03_segmented_text/part1/segments_with_translations.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _excerpt(text: str, limit: int = 90) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


def _dedupe_fixes(path: Path) -> dict[str, dict]:
    """unit_id -> latest successful fix row."""
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
        ok = (not rec.get("error")) and rec.get("proposed_english") is not None
        prev = best.get(uid)
        if prev is None:
            best[uid] = rec
            continue
        prev_ok = (not prev.get("error")) and prev.get("proposed_english") is not None
        if ok and (not prev_ok):
            best[uid] = rec
        elif ok and prev_ok:
            best[uid] = rec  # latest OK wins
    # Only keep successful rows
    return {uid: r for uid, r in best.items()
            if (not r.get("error")) and r.get("proposed_english") is not None}


def _load_scores(path: Path) -> dict[str, dict]:
    """unit_id -> scores dict."""
    out: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        if rec.get("error"):
            continue
        uid = str(rec.get("unit_id") or "")
        if uid:
            out[uid] = rec.get("scores") or {}
    return out


def _load_segments_ordered(path: Path) -> tuple[list[str], dict[str, dict]]:
    """Return (order, by_id) preserving the file's original record order."""
    order: list[str] = []
    by_id: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        sid = str(rec.get("segment_id") or "")
        if not sid:
            continue
        order.append(sid)
        by_id[sid] = rec
    return order, by_id


def _write_segments_atomic(path: Path, order: list[str], by_id: dict[str, dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as h:
        for sid in order:
            rec = by_id[sid]
            h.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _append_fidelity_fix_entry(rec: dict, *, fix: dict, judge_scores: dict) -> None:
    history = list(rec.get("translation_history") or [])
    max_version = max((int(h.get("version") or 0)
                       for h in history if isinstance(h, dict)), default=0)
    last = history[-1] if history else {}
    new_entry = {
        "version": max_version + 1,
        "stage": "fidelity_fix",
        "timestamp": _now_iso(),
        "english": fix.get("proposed_english") or "",
        "notes": fix.get("fix_reason") or "",
        "uncertain": False,
        "model": fix.get("fix_model") or "claude-opus-4-7",
        "lexicon_profile": last.get("lexicon_profile") or "auto",
        "source_unit_id": last.get("source_unit_id")
                          or rec.get("segment_id", "").replace("seg_", ""),
        "stage_metadata": {
            "judge_cf": judge_scores.get("content_fidelity"),
            "judge_rf": judge_scores.get("register_fidelity"),
            "judge_gp": judge_scores.get("greek_preservation"),
            "judge_ph": judge_scores.get("paraphrase_handling"),
            "judge_reason": (fix.get("judge_reason") or "")[:600],
            "applied_from": "apply_fixes.py",
        },
    }
    history.append(new_entry)
    rec["translation_history"] = history


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixes-jsonl", required=True, type=Path)
    p.add_argument("--scores-jsonl", required=True, type=Path)
    p.add_argument("--segments-path", required=True, type=Path,
                   help="production segments_with_translations.jsonl")
    p.add_argument("--max-cf", type=int, default=1,
                   help="apply fixes for units with content_fidelity <= this "
                        "(default 1 = catastrophic tier only)")
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--dry-run", action="store_true",
                   help="show which fixes would apply; do not write")
    args = p.parse_args()

    fixes = _dedupe_fixes(args.fixes_jsonl)
    scores = _load_scores(args.scores_jsonl)
    order, by_id = _load_segments_ordered(args.segments_path)
    print(f"Loaded {len(fixes)} successful fixes, "
          f"{len(scores)} scored units, "
          f"{len(by_id)} segments")

    def _page_of(uid: str) -> int | None:
        m = re.search(r"p(\d+)", uid or "")
        return int(m.group(1)) if m else None

    # Select units: cf in [1..max_cf], no_change=false, in page range
    selected: list[tuple[str, dict, dict]] = []
    for uid, fix in sorted(fixes.items()):
        if fix.get("no_change"):
            continue
        s = scores.get(uid) or {}
        cf = s.get("content_fidelity")
        if not isinstance(cf, int) or cf > args.max_cf:
            continue
        pn = _page_of(uid)
        if args.start_page is not None and (pn is None or pn < args.start_page):
            continue
        if args.end_page is not None and (pn is None or pn > args.end_page):
            continue
        if uid not in by_id:
            print(f"  WARN: {uid} not in segments file; skipping", file=sys.stderr)
            continue
        selected.append((uid, fix, s))

    print(f"Selected for application: {len(selected)} unit(s) "
          f"(cf<={args.max_cf}, no_change=False, "
          f"pages {args.start_page}-{args.end_page})")
    print()

    for uid, fix, s in selected:
        rec = by_id[uid]
        last = (rec.get("translation_history") or [{}])[-1] or {}
        prior_en = last.get("english") or ""
        proposed = fix.get("proposed_english") or ""
        cf = s.get("content_fidelity")
        print(f"  [cf={cf}] {uid}")
        print(f"    prior:    {_excerpt(prior_en)}")
        print(f"    proposed: {_excerpt(proposed)}")
        print(f"    why:      {_excerpt(fix.get('fix_reason') or '', 120)}")
        print()

    if args.dry_run:
        print("DRY RUN — segments file not modified.")
        return 0

    if not selected:
        print("Nothing to apply.")
        return 0

    for uid, fix, s in selected:
        _append_fidelity_fix_entry(by_id[uid], fix=fix, judge_scores=s)

    _write_segments_atomic(args.segments_path, order, by_id)
    print(f"Applied {len(selected)} fix(es) to {args.segments_path}")
    print("Each unit now has an appended translation_history entry with "
          "stage='fidelity_fix'; polish_translations.py will use the new "
          "English on its next run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
