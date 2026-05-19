"""Register-normalize 1658 English to Parker 1849 register.

Purpose
-------
The 1658 contemporary English translation of Ussher's Annals retains
long-s ligatures and Restoration-era English ("aſſure", "ſet ſaile",
"M, Brutus and Caius Caſſius"). For COMET scoring against v5's
modern-scholarly output we need a reference in a comparable register.
This script LLM-rewrites each English line in the register Parker
1849 used: formal Victorian scholarly English, Latinate doctrinal
vocabulary preserved, long-s/ligatures normalized, strictly-archaic
forms ('thou', 'doth', 'ye', etc.) replaced, period constructions
Parker allowed ('wherein', 'whence', 'whilst', 'hath') retained.

Per Phase 6 directive (user 2026-05-19): "The 1658 English will need
to be updated to a translation style that approximates that of the
Whitaker translation by Parker."

Output: a sidecar JSONL at
``08_working_scratch/phase3b/annotations/annals_english/<edition>_parker_style.jsonl``
(or a user-specified path) keyed by line_id, with the modernized text.

The source annotation JSONs are NOT touched. The sidecar is purely
a scoring artifact.

Usage
-----
::

    python modernize_to_parker_register.py \\
        --edition annals_english \\
        --start-page 695 --end-page 699 \\
        --output annals_english_parker_style.jsonl

The judge model defaults to claude-sonnet-4-6 (cost-efficient for
mechanical normalization; not the translator model).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Reuse the judge's CLI plumbing for calling claude -p.
_HERE = Path(__file__).resolve()
_PIPELINE = _HERE.parent
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))
_AB_JUDGE_DIR = _HERE.parents[1] / "phase3b" / "scripts"
if str(_AB_JUDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_AB_JUDGE_DIR))

import ab_judge as aj  # noqa: E402


ANNOTATIONS_DIR = (
    _HERE.parents[1] / "phase3b" / "annotations"
)


SYSTEM_PROMPT = """\
You are an English copy-editor performing a precise register
normalization. You are given ONE line of 1658 English (Restoration
era) and must rewrite it in the register of the 1849 Parker Society
English translation of Whitaker's Disputatio (William Fitzgerald,
tr.) — formal Victorian scholarly English.

Rules:

1. PRESERVE meaning, sentence structure, named entities, and ALL
   citations/numbers/dates exactly. Do not editorially restructure;
   this is normalization, not retranslation. If the source clause
   ends without a period or is mid-thought (the source is one line
   of a larger sentence), the output is mid-thought too.

2. NORMALIZE mechanical archaisms:
   - long-s 'ſ' -> 's' ('aſſure' -> 'assure', 'Caſſius' -> 'Cassius')
   - 'æ', 'œ' ligatures keep their form OR normalize per the
     surrounding pattern (Parker uses 'Caesar', not 'Cæsar'; but
     'Aeneid' is acceptable). When in doubt, normalize.
   - 'u/v' and 'i/j' alternations: normalize to modern English
     ('vsed' -> 'used', 'iudge' -> 'judge'); keep them in proper
     names where Parker would ('Caius', 'Iulius').
   - '&' -> 'and' when in running prose; '&c.' stays '&c.'.

3. REPLACE strict-archaic forms that Parker did NOT use:
   - 'doth', 'dost', 'didst', 'wast' -> 'does', 'do', 'did', 'was'
   - 'hast' (2nd-person sg.) -> 'have'
   - 'thee', 'thou', 'thy', 'thine', 'ye' -> 'you', 'your', 'yours'
   - 'verily', 'vouchsafed' -> 'truly', 'granted' (or drop emphasis)
   - 'in no wise' / 'in any wise' -> 'not' / 'in any way'
   - 'whereunto', 'betwixt' -> 'to which', 'between'
   - inverted constructions ('him spoke', 'spake he') -> standard
   - 'set saile' -> 'set sail'; 'shewed' -> 'showed'; 'shew' -> 'show'

4. KEEP period constructions Parker DID use:
   - 'hath' (3rd-person sg.), 'whilst' (= 'while')
   - 'wherein', 'whence', 'whither', 'thither', 'thereby', 'thereof'
   - 'shall' for first-person future
   - inverted word order is allowed only in formal expressions Parker
     would have written.

5. KEEP Latinate doctrinal/scholarly vocabulary (canonical,
   ecclesiastical, apostolic, jurisdiction, conciliar, etc.).

6. KEEP all dates and named entities verbatim: 'A.U.C. 711', '36 B.C.',
   'M. Brutus', 'Caesar Octavianus', 'Tiberius Caesar'. Roman numerals
   stay as Roman numerals.

Return ONLY the modernized line of English. No commentary, no
quotation marks around the line, no JSON. If the input line is empty
or whitespace-only, return an empty string.
"""


def build_prompt(line_text: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\n1658 ENGLISH (input line):\n"
        + line_text
        + "\n\nMODERNIZED LINE (Parker 1849 register, output):"
    )


def normalize_one(judge_callable, line_text: str) -> str:
    """Call the model; strip any decoration around the returned line."""
    raw = judge_callable(build_prompt(line_text))
    if not raw:
        return ""
    text = raw.strip()
    # Tolerate fenced output even though we asked for none.
    if text.startswith("```"):
        text = text.strip("`").strip()
        if "\n" in text:
            first, rest = text.split("\n", 1)
            if first.lower().startswith(("text", "plain", "markdown")):
                text = rest
    # Strip leading 'MODERNIZED LINE:' label echoes.
    text = re.sub(r"^\s*MODERNIZED LINE[^:]*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Rewrite 1658 English annotation lines in Parker 1849 register.",
    )
    p.add_argument("--edition", default="annals_english",
                   help="Annotation edition subfolder (default: annals_english).")
    p.add_argument("--start-page", type=int, required=True)
    p.add_argument("--end-page", type=int, required=True)
    p.add_argument("--output", required=True,
                   help="Output JSONL path. Will be overwritten if it exists.")
    p.add_argument("--judge-model", default="claude-sonnet-4-6")
    p.add_argument("--timeout-seconds", type=float, default=60.0)
    p.add_argument("--dry-run", action="store_true",
                   help="Print first two prompts and exit; do not call the model.")
    args = p.parse_args()

    edition_dir = ANNOTATIONS_DIR / args.edition
    if not edition_dir.is_dir():
        print(f"missing edition directory: {edition_dir}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for page_num in range(args.start_page, args.end_page + 1):
        page_id = f"p{page_num:04d}"
        page_path = edition_dir / f"page_{page_id}.json"
        if not page_path.exists():
            print(f"  [skip] missing page: {page_path}")
            continue
        with page_path.open(encoding="utf-8") as h:
            payload = json.load(h)
        body = (payload.get("regions") or {}).get("body") or []
        for line in body:
            text = (line.get("text_gold") or line.get("text_ocr_original") or "").strip()
            if not text:
                continue
            rows.append({
                "page_id": page_id,
                "line_id": line.get("line_id"),
                "review_status": line.get("review_status"),
                "source_text": text,
            })

    print(f"Loaded {len(rows)} body lines from "
          f"{args.edition}/p{args.start_page:04d}-p{args.end_page:04d}")

    if args.dry_run:
        for r in rows[:2]:
            print("=" * 80)
            print(f"LINE {r['line_id']}")
            print(build_prompt(r["source_text"]))
        return 0

    judge = aj._make_default_judge(
        judge_model=args.judge_model,
        timeout_seconds=args.timeout_seconds,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    n_err = 0
    with out_path.open("w", encoding="utf-8") as h:
        for i, r in enumerate(rows, 1):
            t0 = time.time()
            err: str | None = None
            modernized: str = ""
            try:
                modernized = normalize_one(judge, r["source_text"])
            except aj.JudgeQuotaError as e:
                print(f"[{i}/{len(rows)}] {r['line_id']} QUOTA — aborting")
                err = f"quota: {e}"
                h.write(json.dumps({
                    **r,
                    "modernized": "",
                    "error": err,
                }, ensure_ascii=False) + "\n")
                break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                print(f"[{i}/{len(rows)}] {r['line_id']} ERROR: {err}")
            dt = time.time() - t0
            rec = {
                **r,
                "modernized": modernized,
                "elapsed_s": round(dt, 2),
            }
            if err:
                rec["error"] = err
                n_err += 1
            else:
                n_ok += 1
            h.write(json.dumps(rec, ensure_ascii=False) + "\n")
            h.flush()
            print(f"[{i:3}/{len(rows)}] {r['line_id']}  ({dt:.1f}s)  "
                  f"{r['source_text'][:60]!r}\n"
                  f"           -> {modernized[:80]!r}")

    print(f"\nWrote {out_path}  ok={n_ok}  err={n_err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
