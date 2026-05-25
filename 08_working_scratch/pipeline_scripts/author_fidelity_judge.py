"""Author-fidelity LLM-judge for Whitaker and Ussher corpora.

Purpose
-------
COMET treats a human reference translation as ground truth, which
conflates two distinct error modes:

1. Genuine translation error: the machine misrenders what the author wrote.
2. Editor drift: the machine preserved what the author wrote, but the
   human reference editorially diverged.

The user prioritizes AUTHOR-FIDELITY (mode 1 is bad; mode 2 is not).
This judge scores each unit on rubrics that target what the AUTHOR
wrote, with any human reference as informational context only.

Scoring
-------
Per unit, four 1-5 rubrics:
- greek_preservation: did the translation preserve Greek script that
  the author wrote? Score 'na' if source has no Greek.
- paraphrase_handling: when the author wrote Greek + a Latin paraphrase
  of the same content, did the translation render the paraphrase's
  meaning as English (typically in brackets after the Greek)? Score
  'na' if no Greek+Latin-paraphrase pair in the source.
- content_fidelity: did the translation add or drop content vs the
  Latin source?
- register_fidelity: scholarly English appropriate to the corpus,
  neither modernized nor Tudor-archaic.

Input field names
-----------------
Accepts both the Whitaker COMET format (``unit_id``, ``latin_concat``,
``english_concat``) and the Annals chunked-COMET format (``chunk_id``,
``latin``, ``machine``). The ``reference`` field is optional in both.

Resume
------
By default, if ``--output`` already exists, completed unit IDs are
loaded and skipped; new results are appended. Pass ``--no-resume`` to
ignore any existing output and start fresh.

Reuses ``ab_judge.py``'s ``_make_default_judge`` / quota detection.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

# Bootstrap pipeline_scripts onto sys.path so phase3b/scripts/ab_judge
# imports translation_adapters cleanly.
_HERE = Path(__file__).resolve()
_PIPELINE = _HERE.parent
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))
_AB_JUDGE_DIR = _HERE.parents[1] / "phase3b" / "scripts"
if str(_AB_JUDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_AB_JUDGE_DIR))

import ab_judge as aj  # noqa: E402


JUDGE_SYSTEM_WHITAKER = """\
You are an expert classical philologist scoring an English translation
of a Latin sentence from William Whitaker's Disputatio de Sacra
Scriptura (1588; cited from the 1690 Latin edition), a 16th-century
Reformation polemical work. The source Latin frequently embeds
Patristic Greek citations.

Your job is AUTHOR-FIDELITY scoring: does the translation reflect what
WHITAKER actually wrote? You are given the 1849 Parker Society
English translation (William Fitzgerald, tr.) as INFORMATIONAL
CONTEXT only — Parker sometimes editorially diverges from Whitaker
(notably by dropping Greek script in patristic citations). Do NOT
penalize the translation for matching Whitaker rather than Parker
when the two diverge. Reward author-fidelity, not editor-fidelity.

Rubrics — each scored 1-5 where 5 is best (or 'na' if not applicable):

1. greek_preservation (1-5 or 'na')
   - 5: All Greek script in the Latin source is preserved verbatim
     in the translation (polytonic accents, breathings intact).
   - 3: Greek partially preserved (some preserved, some transliterated
     or omitted).
   - 1: Greek silently omitted or replaced by English alone.
   - 'na': source contains no Greek.

2. paraphrase_handling (1-5 or 'na')
   - Applies ONLY when Whitaker followed a Greek phrase with his own
     adjacent Latin paraphrase of that same Greek content (his
     reading-aid for Latin-only readers).
   - 5: Greek preserved + paraphrase's meaning rendered as English
     (typically in brackets after the Greek); Latin paraphrase itself
     not echoed verbatim.
   - 3: Either Greek preserved without English gloss, OR Latin
     paraphrase echoed verbatim untranslated.
   - 1: Both Greek and Latin paraphrase mishandled (omitted, doubled,
     or scrambled).
   - 'na': source has no Greek+Latin-paraphrase pair.

3. content_fidelity (1-5)
   - 5: Translation contains exactly the content Whitaker wrote — no
     added phrases, no dropped clauses, no shifted referents.
   - 3: Minor paraphrase liberties but core meaning preserved.
   - 1: Significant additions, omissions, or content shifts vs the
     Latin source.

4. register_fidelity (1-5)
   - 5: Formal Victorian scholarly English appropriate to a Reformed
     polemic — Latinate doctrinal vocabulary preserved
     (perspicuity, canonical, controversy), plain Anglo-Saxon for
     ordinary words. No KJV/Tudor archaisms (doth, verily, thee,
     thou, in no wise).
   - 3: Mostly appropriate but uneven (occasional modern slip or
     Tudor archaism).
   - 1: Wholly inappropriate register (modernized, slang, or
     thick Tudor/KJV pastiche).

The Parker reference shows ONE editor's choices; do not anchor on it.
Greek script in the Latin source that Parker dropped should still be
preserved by a good translation (high greek_preservation = 5), even
if Parker's English shows no Greek.
"""


JUDGE_SYSTEM_USSHER = """\
You are an expert classical philologist scoring an English translation
of a Latin sentence from James Ussher's Britannicarum Ecclesiarum
Antiquitates (1639; cited from the 1847 Elrington-Todd edition), a
17th-century scholarly history of the early British and Irish
churches. The source Latin frequently embeds Patristic Greek
citations and dense patristic-historical references.

Your job is AUTHOR-FIDELITY scoring: does the translation reflect what
USSHER actually wrote? No gold-standard English translation exists
for this corpus; score against the Latin source directly.

Rubrics — each scored 1-5 where 5 is best (or 'na' if not applicable):

1. greek_preservation (1-5 or 'na')
   - 5: All Greek script in the Latin source is preserved verbatim
     in the translation (polytonic accents, breathings intact).
   - 3: Greek partially preserved (some preserved, some transliterated
     or omitted).
   - 1: Greek silently omitted or replaced by English alone.
   - 'na': source contains no Greek.

2. paraphrase_handling (1-5 or 'na')
   - Applies ONLY when Ussher followed a Greek phrase with his own
     adjacent Latin paraphrase of that same Greek content (his
     reading-aid for Latin-only readers).
   - 5: Greek preserved + paraphrase's meaning rendered as English
     (typically in brackets after the Greek); Latin paraphrase itself
     not echoed verbatim.
   - 3: Either Greek preserved without English gloss, OR Latin
     paraphrase echoed verbatim untranslated.
   - 1: Both Greek and Latin paraphrase mishandled.
   - 'na': source has no Greek+Latin-paraphrase pair.

3. content_fidelity (1-5)
   - 5: Translation contains exactly the content Ussher wrote — no
     added phrases, no dropped clauses, no shifted referents.
   - 3: Minor paraphrase liberties but core meaning preserved.
   - 1: Significant additions, omissions, or content shifts.

4. register_fidelity (1-5)
   - 5: Modern scholarly English appropriate to academic
     ecclesiastical history — Latinate doctrinal/scholastic
     vocabulary preserved (canonical, episcopate, see, schism,
     orthodox, conciliar). No Tudor/KJV archaisms (doth, verily,
     thee, thou, hath, whilst).
   - 3: Mostly appropriate but uneven (occasional modernism or
     period archaism).
   - 1: Wholly inappropriate (modernized prose, slang, or
     pseudo-archaic pastiche).
"""

# Default for back-compat
JUDGE_SYSTEM = JUDGE_SYSTEM_WHITAKER

JUDGE_OUTPUT_CONTRACT_WITH_PARKER = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "scores": {
    "greek_preservation": 1 | 2 | 3 | 4 | 5 | "na",
    "paraphrase_handling": 1 | 2 | 3 | 4 | 5 | "na",
    "content_fidelity":   1 | 2 | 3 | 4 | 5,
    "register_fidelity":  1 | 2 | 3 | 4 | 5
  },
  "parker_divergence": "none" | "minor" | "major",
  "reason": "<one sentence; mention any divergence between author-fidelity and Parker-fidelity>"
}

Rules:
- Each score key must be present.
- greek_preservation and paraphrase_handling may be 'na'; the other two must be 1-5 integers.
- parker_divergence: "none" if v4 and Parker agree, "minor" if small editorial differences,
  "major" if v4 follows the author but Parker editorially diverged (e.g. Parker dropped Greek
  that the author wrote).
- 'reason' is <= 400 chars.
- No other top-level keys.
"""

JUDGE_OUTPUT_CONTRACT_NO_REF = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "scores": {
    "greek_preservation": 1 | 2 | 3 | 4 | 5 | "na",
    "paraphrase_handling": 1 | 2 | 3 | 4 | 5 | "na",
    "content_fidelity":   1 | 2 | 3 | 4 | 5,
    "register_fidelity":  1 | 2 | 3 | 4 | 5
  },
  "reason": "<one sentence explaining the scores>"
}

Rules:
- Each score key must be present.
- greek_preservation and paraphrase_handling may be 'na'; the other two must be 1-5 integers.
- 'reason' is <= 400 chars.
- No other top-level keys.
"""

# Default for back-compat
JUDGE_OUTPUT_CONTRACT = JUDGE_OUTPUT_CONTRACT_WITH_PARKER


def build_prompt(*, latin: str, english: str, parker_ref: str = "",
                 corpus: str = "whitaker") -> str:
    """Build a judge prompt for one segment.

    corpus="whitaker": Whitaker source + Parker reference (informational).
    corpus="ussher":   Ussher source, no reference available.
    """
    if corpus == "ussher":
        return (
            JUDGE_SYSTEM_USSHER
            + "\n\nLATIN SOURCE (Ussher 1639 / 1847 Elrington-Todd):\n"
            + latin.strip()
            + "\n\nCANDIDATE TRANSLATION:\n"
            + english.strip()
            + "\n\n"
            + JUDGE_OUTPUT_CONTRACT_NO_REF
        )
    # default: whitaker with Parker reference
    body = (
        JUDGE_SYSTEM_WHITAKER
        + "\n\nLATIN SOURCE (Whitaker 1690):\n"
        + latin.strip()
        + "\n\nCANDIDATE TRANSLATION:\n"
        + english.strip()
    )
    if parker_ref.strip():
        body += (
            "\n\nPARKER REFERENCE (1849; informational only):\n"
            + parker_ref.strip()
            + "\n\n"
            + JUDGE_OUTPUT_CONTRACT_WITH_PARKER
        )
    else:
        body += "\n\n" + JUDGE_OUTPUT_CONTRACT_NO_REF
    return body


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_response(raw: str) -> dict:
    if not raw:
        raise ValueError("empty response")
    if aj._looks_like_quota_refusal(raw):
        raise aj.JudgeQuotaError(raw.strip())
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            _, text = text.split("\n", 1)
    m = _JSON_OBJ_RE.search(text)
    if not m:
        raise ValueError("no JSON object in response")
    obj = json.loads(m.group(0))
    if "scores" not in obj:
        raise ValueError("response missing 'scores'")
    return obj


def _normalize_row(r: dict) -> dict:
    """Normalize field names across Whitaker and Annals COMET formats.

    Whitaker format: unit_id, latin_concat, english_concat, score, reference
    Annals format:   chunk_id, latin, machine, score, reference
    """
    unit_id = r.get("unit_id") or r.get("chunk_id") or ""
    latin = r.get("latin_concat") or r.get("latin") or ""
    english = r.get("english_concat") or r.get("machine") or ""
    return {
        **r,
        "unit_id": unit_id,
        "latin_concat": latin,
        "english_concat": english,
    }


def _load_completed_ids(path: Path) -> set[str]:
    """Return unit_ids from a partial run that completed without error."""
    completed: set[str] = set()
    if not path.exists():
        return completed
    with path.open(encoding="utf-8") as h:
        for raw in h:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            uid = str(rec.get("unit_id") or "")
            if uid and rec.get("scores") and not rec.get("error"):
                completed.add(uid)
    return completed


def _ensure_trailing_newline(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as h:
        h.seek(-1, 2)
        if h.read(1) != b"\n":
            h.write(b"\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scores-jsonl", required=True,
                   help=(
                       "COMET scores JSONL. Accepts both Whitaker format "
                       "(unit_id, latin_concat, english_concat) and Annals "
                       "chunked-COMET format (chunk_id, latin, machine)."
                   ))
    p.add_argument("--run-filter", required=True,
                   help="judge only rows whose 'run' field matches this string exactly")
    p.add_argument("--output", required=True,
                   help="output JSONL with author-fidelity scores per unit")
    p.add_argument("--corpus", choices=("whitaker", "ussher"), default="whitaker",
                   help="rubric profile: 'whitaker' (with Parker reference if present) or 'ussher' (no reference)")
    p.add_argument("--judge-model", default="claude-sonnet-4-6")
    p.add_argument("--timeout-seconds", type=float, default=120.0)
    p.add_argument("--dry-run", action="store_true",
                   help="print prompts; do not call the judge")
    p.add_argument("--no-resume", action="store_true",
                   help=(
                       "Ignore any existing --output JSONL and start fresh. "
                       "Default: resume by skipping already-completed unit IDs."
                   ))
    args = p.parse_args()

    rows: list[dict] = []
    with open(args.scores_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("run") != args.run_filter:
                continue
            rows.append(_normalize_row(r))
    print(f"Loaded {len(rows)} units from {args.scores_jsonl} (run={args.run_filter})")

    out_path = Path(args.output)

    # Resume logic
    completed: set[str] = set()
    if not args.no_resume:
        completed = _load_completed_ids(out_path)
        if completed:
            print(f"Resume: skipping {len(completed)} already-completed unit(s).")
            _ensure_trailing_newline(out_path)
    elif out_path.exists():
        out_path.write_text("", encoding="utf-8")

    rows_to_judge = [r for r in rows if str(r.get("unit_id") or "") not in completed]
    print(f"Units to judge: {len(rows_to_judge)}/{len(rows)}")

    if args.dry_run:
        for r in rows_to_judge[:2]:
            prompt = build_prompt(latin=r["latin_concat"],
                                  english=r["english_concat"],
                                  parker_ref=r.get("reference", ""),
                                  corpus=args.corpus)
            print("=" * 80)
            comet = r.get("score")
            label = f"COMET={comet:.4f}" if comet is not None else "no-comet"
            print(f"UNIT {r['unit_id']}  {label}")
            print(prompt[:2000])
        return 0

    if not rows_to_judge:
        print(f"Nothing to do; all units already complete in {out_path}")
        return 0

    judge = aj._make_default_judge(judge_model=args.judge_model,
                                    timeout_seconds=args.timeout_seconds)

    results: list[dict] = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    open_mode = "a" if (not args.no_resume and completed) else "w"
    total = len(rows)
    done_before = len(completed)
    with out_path.open(open_mode, encoding="utf-8") as h:
        for i, r in enumerate(rows_to_judge, 1):
            display_i = done_before + i
            prompt = build_prompt(latin=r["latin_concat"],
                                  english=r["english_concat"],
                                  parker_ref=r.get("reference", ""),
                                  corpus=args.corpus)
            t0 = time.time()
            err: str | None = None
            parsed: dict | None = None
            raw: str = ""
            try:
                raw = judge(prompt)
                parsed = parse_response(raw)
            except aj.JudgeQuotaError as e:
                print(f"[{display_i}/{total}] {r['unit_id']} QUOTA REFUSAL — aborting")
                err = f"quota: {e}"
                break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                print(f"[{display_i}/{total}] {r['unit_id']} ERROR: {err}")
            dt = time.time() - t0
            rec = {
                "unit_id": r["unit_id"],
                "run": r["run"],
                "comet_score": r.get("score"),
                "elapsed_s": round(dt, 2),
                "error": err,
            }
            if parsed:
                rec["scores"] = parsed.get("scores", {})
                if "parker_divergence" in parsed:
                    rec["parker_divergence"] = parsed["parker_divergence"]
                rec["reason"] = parsed.get("reason", "")[:400]
            elif err and raw:
                rec["raw"] = raw[:600]
            results.append(rec)
            h.write(json.dumps(rec, ensure_ascii=False) + "\n")
            h.flush()
            scores = rec.get("scores", {})
            comet_str = f"COMET={r['score']:.3f}" if r.get("score") is not None else "no-comet"
            div_str = f"  div={rec['parker_divergence']}" if "parker_divergence" in rec else ""
            print(f"[{display_i:2}/{total}] {r['unit_id']}  {comet_str}  "
                  f"gp={scores.get('greek_preservation','?')}  "
                  f"ph={scores.get('paraphrase_handling','?')}  "
                  f"cf={scores.get('content_fidelity','?')}  "
                  f"rf={scores.get('register_fidelity','?')}  "
                  f"{div_str}"
                  f"({dt:.1f}s)")

    print(f"\nWrote {out_path}")
    n_ok = sum(1 for r in results if r.get("scores"))
    print(f"Scored this session: {n_ok}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
