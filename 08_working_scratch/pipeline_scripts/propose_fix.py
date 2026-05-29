"""Propose targeted corrections for fidelity-flagged translation units.

Runs AFTER ``author_fidelity_judge.py``. For each unit the judge scored
below threshold, issues a SEPARATE LLM call (defaults to the translator
model ``claude-opus-4-7``) carrying the same TRANSLATOR_BRIEF + HARD_RULES
the original translation prompt uses, plus the unit's Latin, the prior
English, and the judge's reason as the diagnostic hint. The model is
asked for the MINIMAL correction that addresses the flagged issue, or to
mark ``no_change=true`` if it judges the prior English actually correct.

Architectural notes
-------------------
- This is a *separate* call from the judge, not a bolt-on to the judge
  prompt. The §7.3 ablation showed prompt bloat regresses quality; a
  combined judge+fix prompt would force HARD_RULES (~1-2 kB) into the
  judge's context, putting it in the same size regime as the exemplar
  block that regressed cf -0.125.
- Fixes are PROPOSALS, never silently applied. Output is a sibling JSONL
  for editor review. The translation_history in the segments file is
  untouched by this script.
- Trigger: any rubric (cf, rf, gp, ph) with a numeric score <= --max-cf
  (default 3). 'na' scores do not trigger; judge errors do not trigger.

Usage
-----
    python propose_fix.py \\
        --scores-jsonl 08_working_scratch/phase3b/ch1_fidelity_scores.jsonl \\
        --inputs-jsonl 08_working_scratch/phase3b/ch1_fidelity_input.jsonl \\
        --output      08_working_scratch/phase3b/ch1_fidelity_fixes.jsonl

Resume behavior matches the judge: re-run without ``--no-resume`` and
already-completed unit_ids are skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Bootstrap sys.path: pipeline_scripts (for ussher_v5 imports) and
# phase3b/scripts (for ab_judge). Matches author_fidelity_judge.py.
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

FIX_OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped exactly as:

{
  "proposed_english": "<the minimal-correction English rendering>",
  "fix_reason": "<one short sentence explaining what you changed and why>",
  "no_change": <true|false>
}

Rules:
- Set no_change=true ONLY if you judge the prior English already correct
  and the flagged issue is a judge over-call. In that case set
  proposed_english to the prior English unchanged and explain in
  fix_reason why you disagree with the judge.
- Otherwise produce the MINIMAL correction. Keep correctly-rendered
  phrasing intact; do not rewrite for style. The goal is to fix the
  specific defect the judge identified, not to re-translate the unit.
- Apply the HARD RULES above (Rule 1 Greek+bracket-gloss / collapse
  Latin paraphrase, Rule 2 register, Rule 6 footnote-marker sentinels
  preserved as ^X tokens, etc.) so the fix is consistent with the
  surrounding chapter.
- Output nothing outside the JSON object."""


def build_fix_prompt(*, latin: str, prior_english: str,
                     judge_reason: str, judge_scores: dict) -> str:
    scores_line = ", ".join(
        f"{k}={judge_scores.get(k, '?')}"
        for k in ("content_fidelity", "register_fidelity",
                  "greek_preservation", "paraphrase_handling")
    )
    sections = [
        TRANSLATOR_BRIEF,
        HARD_RULES,
        ("You are revising a SINGLE previously-translated unit. A separate "
         "author-fidelity judge (a different model) flagged it for the issue "
         "below. Apply the HARD RULES above and produce a minimal correction."),
        f"LATIN SOURCE:\n{latin.rstrip()}",
        f"PRIOR ENGLISH:\n{prior_english.rstrip() or '(empty)'}",
        f"JUDGE SCORES: {scores_line}",
        f"JUDGE REASON:\n{judge_reason.strip() or '(no reason recorded)'}",
        FIX_OUTPUT_CONTRACT,
    ]
    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRIGGER_RUBRICS = ("content_fidelity", "register_fidelity",
                    "greek_preservation", "paraphrase_handling")


def needs_fix(scores: dict, max_cf: int) -> bool:
    """True if any numeric rubric score is <= max_cf. 'na'/missing do not trigger."""
    for k in _TRIGGER_RUBRICS:
        v = scores.get(k)
        if isinstance(v, int) and v <= max_cf:
            return True
    return False


_FENCE_OPEN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?")
_FENCE_CLOSE = re.compile(r"\n?\s*```\s*$")


def parse_fix_response(raw: str) -> dict:
    """Parse the fix-call output into {proposed_english, fix_reason, no_change}.

    Tolerates:
      - leading/trailing whitespace
      - markdown code fences (``` or ```json ... ```)
      - prose around the JSON object (extracts the largest {...} span)
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty response")
    # Strip markdown fences if present
    raw = _FENCE_OPEN.sub("", raw)
    raw = _FENCE_CLOSE.sub("", raw).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to extracting the largest brace-balanced span
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise
        obj = json.loads(m.group(0))
    if "proposed_english" not in obj:
        raise ValueError("response missing 'proposed_english'")
    obj["proposed_english"] = str(obj.get("proposed_english") or "")
    obj["fix_reason"] = str(obj.get("fix_reason") or "")
    obj["no_change"] = bool(obj.get("no_change"))
    return obj


_STRICTER_SUFFIX = (
    "\n\nIMPORTANT: your previous response failed JSON parsing. "
    "Return ONLY the JSON object — no markdown fences, no prose before "
    "or after, no commentary. The response must start with '{' and end "
    "with '}'. Re-emit the exact same content as valid strict JSON."
)


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
        if uid and not rec.get("error") and rec.get("proposed_english") is not None:
            done.add(uid)
    return done


def _ensure_trailing_newline(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as h:
        h.seek(-1, 2)
        if h.read(1) != b"\n":
            h.write(b"\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scores-jsonl", required=True, type=Path,
                   help="judge output (e.g. ch1_fidelity_scores.jsonl)")
    p.add_argument("--inputs-jsonl", required=True, type=Path,
                   help="bridged judge input — supplies latin + prior english "
                        "(e.g. ch1_fidelity_input.jsonl)")
    p.add_argument("--output", required=True, type=Path,
                   help="output JSONL of proposed fixes (one per flagged unit)")
    p.add_argument("--max-cf", type=int, default=3,
                   help="trigger a fix when any rubric (cf/rf/gp/ph) is "
                        "scored <= this. default 3 (the review queue).")
    p.add_argument("--start-page", type=int, default=None,
                   help="filter to units whose page (parsed from unit_id) "
                        ">= this")
    p.add_argument("--end-page", type=int, default=None,
                   help="filter to units whose page <= this")
    p.add_argument("--model", default="claude-opus-4-7",
                   help="model for the fix call (default: claude-opus-4-7, "
                        "same as the translator)")
    p.add_argument("--timeout-seconds", type=float, default=120.0)
    p.add_argument("--no-resume", action="store_true",
                   help="ignore any existing --output and start fresh "
                        "(default: resume by skipping completed unit_ids)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the prompt for the first flagged unit and exit")
    args = p.parse_args()

    # Load bridged inputs into a unit_id -> (latin, english) map.
    inputs: dict[str, tuple[str, str]] = {}
    for line in args.inputs_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        inputs[r["unit_id"]] = (r.get("latin_concat", ""),
                                r.get("english_concat", ""))

    # Walk scores; filter by page; select units needing a fix.
    candidates: list[dict] = []
    for raw in args.scores_jsonl.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        if rec.get("error"):
            continue
        scores = rec.get("scores") or {}
        uid = str(rec.get("unit_id") or "")
        pn = _page_of(uid)
        if args.start_page is not None and (pn is None or pn < args.start_page):
            continue
        if args.end_page is not None and (pn is None or pn > args.end_page):
            continue
        if not needs_fix(scores, args.max_cf):
            continue
        if uid not in inputs:
            print(f"  WARN: {uid} not in inputs file; skipping", file=sys.stderr)
            continue
        candidates.append({
            "unit_id": uid, "page": pn,
            "scores": scores,
            "reason": rec.get("reason", ""),
        })

    print(f"Loaded {len(inputs)} bridged inputs and "
          f"{sum(1 for _ in args.scores_jsonl.open(encoding='utf-8'))} score rows")
    print(f"Flagged (max-cf={args.max_cf}, pages {args.start_page}-{args.end_page}): "
          f"{len(candidates)}")

    completed: set[str] = set()
    if not args.no_resume:
        completed = _load_completed(args.output)
        if completed:
            print(f"Resume: skipping {len(completed)} already-completed.")
            _ensure_trailing_newline(args.output)
    elif args.output.exists():
        args.output.write_text("", encoding="utf-8")

    to_run = [c for c in candidates if c["unit_id"] not in completed]
    if not to_run:
        print("Nothing to do.")
        return 0

    if args.dry_run:
        c = to_run[0]
        latin, prior = inputs[c["unit_id"]]
        prompt = build_fix_prompt(latin=latin, prior_english=prior,
                                  judge_reason=c["reason"],
                                  judge_scores=c["scores"])
        print("=" * 80)
        print(f"DRY RUN — first unit: {c['unit_id']}  ({len(to_run)} would run)")
        print(f"prompt chars: {len(prompt)}")
        print("-" * 80)
        print(prompt[:3000])
        if len(prompt) > 3000:
            print(f"... (truncated, full length {len(prompt)} chars)")
        return 0

    judge = aj._make_default_judge(judge_model=args.model,
                                    timeout_seconds=args.timeout_seconds)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    open_mode = "a" if (not args.no_resume and completed) else "w"
    total = len(candidates)
    done_before = len(completed)
    with args.output.open(open_mode, encoding="utf-8") as h:
        for i, c in enumerate(to_run, 1):
            display_i = done_before + i
            uid = c["unit_id"]
            latin, prior = inputs[uid]
            prompt = build_fix_prompt(latin=latin, prior_english=prior,
                                      judge_reason=c["reason"],
                                      judge_scores=c["scores"])
            t0 = time.time()
            err: str | None = None
            parsed: dict | None = None
            raw: str = ""
            quota = False
            # Up to 2 attempts: first plain, second with a stricter
            # "valid-JSON-only" suffix if the first failed to parse.
            for attempt in (1, 2):
                use_prompt = prompt if attempt == 1 else (prompt + _STRICTER_SUFFIX)
                try:
                    raw = judge(use_prompt)
                except aj.JudgeQuotaError as e:
                    err = f"quota: {e}"
                    quota = True
                    break
                # Claude CLI sometimes delivers a quota refusal as plain
                # stdout (no exception). Detect and treat as quota.
                if aj._looks_like_quota_refusal(raw):
                    err = f"quota: {raw.strip()[:140]}"
                    quota = True
                    break
                try:
                    parsed = parse_fix_response(raw)
                    err = None
                    break
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    if attempt == 1:
                        continue  # retry once with stricter prompt
                    print(f"[{display_i}/{total}] {uid} PARSE FAIL after retry: {err}")
            if quota:
                print(f"[{display_i}/{total}] {uid} QUOTA REFUSAL — aborting "
                      "(re-run the same command after quota resets to resume)")
                break
            dt = time.time() - t0

            rec = {
                "unit_id": uid, "page": c["page"],
                "fix_model": args.model,
                "elapsed_s": round(dt, 2),
                "error": err,
                "original_english": prior,
                "proposed_english": parsed["proposed_english"] if parsed else None,
                "fix_reason": parsed["fix_reason"] if parsed else "",
                "no_change": parsed["no_change"] if parsed else None,
                "judge_scores": c["scores"],
                "judge_reason": c["reason"],
            }
            if err and raw and not parsed:
                rec["raw"] = raw[:600]
            h.write(json.dumps(rec, ensure_ascii=False) + "\n")
            h.flush()

            if parsed:
                marker = "NO CHANGE" if parsed["no_change"] else "FIX"
                print(f"[{display_i:3}/{total}] {uid}  {marker}  "
                      f"({dt:.1f}s)  {parsed['fix_reason'][:80]}")

    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
