"""LLM-assisted review of propose_fix.py outputs.

Reads ``ch*_fidelity_fixes.jsonl`` + the bridged inputs (for Latin), and
for each flagged unit issues ONE comparative review call (default
``claude-opus-4-7``) carrying the same TRANSLATOR_BRIEF + HARD_RULES as
the translator and the fixer. The reviewer sees Latin source, prior
English, proposed English, and the judge's original diagnosis as
context, and outputs a structured decision: accept_proposed /
keep_prior / edit (with the suggested edit) plus a confidence level.

Rationale
---------
The original author-fidelity judge scored the ORIGINAL English. We never
re-scored the proposed fixed English. Two options were considered:

1. Re-judge the proposed English with the same Sonnet 4.6 judge.
   Pros: apples-to-apples cf delta against the original score.
   Cons: small Latin fragments stretch the judge's signal-to-noise.

2. Direct comparative review with Opus 4.7 (this script).
   Pros: stronger model on fragmentary Latin; produces a directly
   actionable decision; mirrors how a human reviewer actually thinks
   (which of these two is more faithful to the Latin?). Output is
   structured for downstream auto-application of the high-confidence
   subset.
   Cons: same model family as the fixer (mitigated: separate cold
   call, the reviewer prompt asks for objective fidelity assessment
   of two labelled candidates, not preference for the 'proposed' one).

User selected option 2 on the grounds that ch1's units are mostly
line-fragments, where model strength dominates the bias concern.

Trigger
-------
One review per unit with a non-error, non-null proposed_english.
``no_change=true`` rows from the fixer are passed through (the
reviewer sees the fixer's no-change rationale and decides whether to
ratify or override).

Usage
-----
    python review_fixes.py \\
        --fixes-jsonl  08_working_scratch/phase3b/ch1_fidelity_fixes.jsonl \\
        --inputs-jsonl 08_working_scratch/phase3b/ch1_fidelity_input.jsonl \\
        --output       08_working_scratch/phase3b/ch1_fix_decisions.jsonl

Resume-by-default; ``--start-page`` / ``--end-page`` mirror the judge.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Bootstrap sys.path the same way author_fidelity_judge / propose_fix do.
_HERE = Path(__file__).resolve()
_PIPELINE = _HERE.parent
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))
_AB_JUDGE_DIR = _HERE.parents[1] / "phase3b" / "scripts"
if str(_AB_JUDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_AB_JUDGE_DIR))

import ab_judge as aj  # noqa: E402
from translation_prompts_ussher_v5 import (  # noqa: E402
    HARD_RULES,
    TRANSLATOR_BRIEF,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

REVIEW_OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped exactly as:

{
  "decision": "accept_proposed" | "keep_prior" | "edit",
  "reason": "<one short sentence explaining the choice>",
  "edited_english": "<your edited English if decision == 'edit'; empty string otherwise>",
  "confidence": "high" | "medium" | "low"
}

Decision rules:
- "accept_proposed" — the proposed English is genuinely more faithful to
  the Latin source than the prior English, and is itself acceptable.
- "keep_prior" — the prior English is more faithful, OR the proposed
  English introduces a NEW error worse than what it fixes.
- "edit" — neither is fully correct; provide a minimal corrected version
  in edited_english that addresses the residual issue.

Confidence rules:
- "high" — the decision is clear from the Latin and the rules.
- "medium" — the decision is defensible but a close call.
- "low" — the unit is genuinely ambiguous; a human philologist should look.

Apply the HARD RULES above (Rule 1 Greek+bracket-gloss / Latin paraphrase
collapse, Rule 2 register, Rule 6 footnote-marker sentinels preserved as
^X tokens). Output nothing outside the JSON object."""


def build_review_prompt(*, latin: str, prior_english: str,
                        proposed_english: str, judge_reason: str,
                        fixer_reason: str, no_change: bool) -> str:
    sections = [
        TRANSLATOR_BRIEF,
        HARD_RULES,
        ("You are COMPARATIVELY REVIEWING a translation unit that an "
         "author-fidelity judge flagged. A fixer model proposed a "
         "correction. Your job is NOT to retranslate from scratch — it "
         "is to decide which English (prior or proposed) is more "
         "faithful to the Latin source, given the HARD RULES above. If "
         "neither is fully correct, write a minimal edit. Be objective: "
         "the labels 'prior' and 'proposed' have no inherent preference."),
        f"LATIN SOURCE:\n{latin.rstrip()}",
        f"PRIOR ENGLISH:\n{prior_english.rstrip() or '(empty)'}",
        f"PROPOSED ENGLISH:\n{proposed_english.rstrip() or '(empty)'}",
        f"ORIGINAL JUDGE DIAGNOSIS:\n{judge_reason.strip() or '(none)'}",
        f"FIXER RATIONALE:\n{fixer_reason.strip() or '(none)'}"
        + (f"\n\nNote: the fixer marked no_change=true (i.e. proposed === prior, "
           "asserting the judge over-called). Confirm or override."
           if no_change else ""),
        REVIEW_OUTPUT_CONTRACT,
    ]
    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?")
_FENCE_CLOSE = re.compile(r"\n?\s*```\s*$")

_STRICTER_SUFFIX = (
    "\n\nIMPORTANT: your previous response failed JSON parsing. "
    "Return ONLY the JSON object — no markdown fences, no prose, no "
    "commentary. The response must start with '{' and end with '}'."
)

_VALID_DECISIONS = {"accept_proposed", "keep_prior", "edit"}
_VALID_CONFIDENCE = {"high", "medium", "low"}


def parse_review_response(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty response")
    raw = _FENCE_OPEN.sub("", raw)
    raw = _FENCE_CLOSE.sub("", raw).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise
        obj = json.loads(m.group(0))
    decision = str(obj.get("decision") or "").strip()
    if decision not in _VALID_DECISIONS:
        raise ValueError(f"invalid decision {decision!r}")
    conf = str(obj.get("confidence") or "").strip().lower()
    if conf not in _VALID_CONFIDENCE:
        raise ValueError(f"invalid confidence {conf!r}")
    return {
        "decision": decision,
        "reason": str(obj.get("reason") or ""),
        "edited_english": str(obj.get("edited_english") or ""),
        "confidence": conf,
    }


def _page_of(uid: str) -> int | None:
    m = re.search(r"p(\d+)", uid or "")
    return int(m.group(1)) if m else None


def _load_completed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        uid = str(rec.get("unit_id") or "")
        if uid and not rec.get("error") and rec.get("decision"):
            done.add(uid)
    return done


def _ensure_trailing_newline(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as h:
        h.seek(-1, 2)
        if h.read(1) != b"\n":
            h.write(b"\n")


def _dedupe_fixes(path: Path) -> list[dict]:
    """Latest successful row per unit_id wins; quota/error rows discarded
    if a successful row for the same unit_id is present."""
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
        if ok and not prev_ok:
            best[uid] = rec
        elif ok and prev_ok:
            best[uid] = rec  # latest OK wins
    return [r for r in best.values()
            if (not r.get("error")) and r.get("proposed_english") is not None]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixes-jsonl", required=True, type=Path,
                   help="output of propose_fix.py (e.g. ch1_fidelity_fixes.jsonl)")
    p.add_argument("--inputs-jsonl", required=True, type=Path,
                   help="bridged judge input — supplies Latin per unit_id")
    p.add_argument("--output", required=True, type=Path,
                   help="output JSONL of review decisions, one per flagged unit")
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    p.add_argument("--model", default="claude-opus-4-7",
                   help="reviewer model (default: claude-opus-4-7)")
    p.add_argument("--timeout-seconds", type=float, default=120.0)
    p.add_argument("--no-resume", action="store_true",
                   help="ignore any existing --output and start fresh "
                        "(default: resume by skipping completed unit_ids)")
    p.add_argument("--dry-run", action="store_true",
                   help="print prompt for the first candidate and exit")
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

    fixes = _dedupe_fixes(args.fixes_jsonl)
    # page-range filter
    if args.start_page is not None or args.end_page is not None:
        def _in_range(uid: str) -> bool:
            pn = _page_of(uid)
            if pn is None:
                return False
            if args.start_page is not None and pn < args.start_page:
                return False
            if args.end_page is not None and pn > args.end_page:
                return False
            return True
        fixes = [r for r in fixes if _in_range(r.get("unit_id", ""))]

    print(f"Loaded {len(latin_map)} Latin sources; "
          f"{len(fixes)} fix proposals to review "
          f"(pages {args.start_page}-{args.end_page})")

    completed: set[str] = set()
    if not args.no_resume:
        completed = _load_completed(args.output)
        if completed:
            print(f"Resume: skipping {len(completed)} already-reviewed.")
            _ensure_trailing_newline(args.output)
    elif args.output.exists():
        args.output.write_text("", encoding="utf-8")

    to_run = [r for r in fixes if r["unit_id"] not in completed]
    if not to_run:
        print("Nothing to do.")
        return 0

    if args.dry_run:
        r = to_run[0]
        uid = r["unit_id"]
        prompt = build_review_prompt(
            latin=latin_map.get(uid, ""),
            prior_english=r.get("original_english", ""),
            proposed_english=r.get("proposed_english", ""),
            judge_reason=r.get("judge_reason", ""),
            fixer_reason=r.get("fix_reason", ""),
            no_change=bool(r.get("no_change")),
        )
        print("=" * 80)
        print(f"DRY RUN — first unit: {uid}  ({len(to_run)} would run)")
        print(f"prompt chars: {len(prompt)}")
        print("-" * 80)
        print(prompt[:3500])
        if len(prompt) > 3500:
            print(f"... (truncated, full length {len(prompt)} chars)")
        return 0

    judge = aj._make_default_judge(judge_model=args.model,
                                    timeout_seconds=args.timeout_seconds)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    open_mode = "a" if (not args.no_resume and completed) else "w"
    total = len(fixes)
    done_before = len(completed)

    with args.output.open(open_mode, encoding="utf-8") as h:
        for i, r in enumerate(to_run, 1):
            display_i = done_before + i
            uid = r["unit_id"]
            latin = latin_map.get(uid, "")
            prompt = build_review_prompt(
                latin=latin,
                prior_english=r.get("original_english", ""),
                proposed_english=r.get("proposed_english", ""),
                judge_reason=r.get("judge_reason", ""),
                fixer_reason=r.get("fix_reason", ""),
                no_change=bool(r.get("no_change")),
            )

            t0 = time.time()
            err: str | None = None
            parsed: dict | None = None
            raw: str = ""
            quota = False

            for attempt in (1, 2):
                use_prompt = prompt if attempt == 1 else (prompt + _STRICTER_SUFFIX)
                try:
                    raw = judge(use_prompt)
                except aj.JudgeQuotaError as e:
                    err = f"quota: {e}"
                    quota = True
                    break
                if aj._looks_like_quota_refusal(raw):
                    err = f"quota: {raw.strip()[:140]}"
                    quota = True
                    break
                try:
                    parsed = parse_review_response(raw)
                    err = None
                    break
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    if attempt == 1:
                        continue
                    print(f"[{display_i}/{total}] {uid} PARSE FAIL after retry: {err}")

            if quota:
                print(f"[{display_i}/{total}] {uid} QUOTA REFUSAL — aborting "
                      "(re-run the same command after quota resets to resume)")
                break

            dt = time.time() - t0
            rec = {
                "unit_id": uid,
                "page": _page_of(uid),
                "reviewer_model": args.model,
                "elapsed_s": round(dt, 2),
                "error": err,
                "decision": parsed["decision"] if parsed else None,
                "reason": parsed["reason"] if parsed else "",
                "edited_english": parsed["edited_english"] if parsed else "",
                "confidence": parsed["confidence"] if parsed else None,
                # Carry through everything needed for downstream apply_fixes:
                "original_english": r.get("original_english", ""),
                "proposed_english": r.get("proposed_english", ""),
                "judge_scores": r.get("judge_scores", {}),
                "judge_reason": r.get("judge_reason", ""),
                "fix_reason": r.get("fix_reason", ""),
                "fixer_no_change": bool(r.get("no_change")),
            }
            if err and raw and not parsed:
                rec["raw"] = raw[:600]
            h.write(json.dumps(rec, ensure_ascii=False) + "\n")
            h.flush()

            if parsed:
                tag = parsed["decision"].upper()
                conf = parsed["confidence"]
                print(f"[{display_i:3}/{total}] {uid}  {tag:18s}  ({conf})  "
                      f"({dt:.1f}s)  {parsed['reason'][:80]}")

    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
