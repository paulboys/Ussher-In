"""Bridge the symbolic validators into the LLM repair loop.

This closes the neuro-symbolic loop. Until now the two halves ran apart:

- the SYMBOLIC half (``glossary_validate.py`` and its siblings) detects
  defects deterministically and writes editor flags to a JSONL that nothing
  consumed;
- the NEURAL repair half (``propose_fix.py`` -> ``review_fixes.py`` ->
  ``apply_fixes.py``) re-translates a unit from its Latin with a diagnostic
  hint, but was triggered only by the LLM fidelity judge's scores.

This script converts validator flags into the two artifacts
``propose_fix.py`` already expects, so a deterministic finding becomes a
targeted re-translation request carrying the Latin and a precise diagnostic.

Why route symbolic flags here rather than leave them to a human:

- They are high-precision. A banned phrase either appears or it does not;
  there is no judgment to second-guess.
- The diagnostic is unusually specific -- not "this reads oddly" but "you
  printed the KJV's 'from the end of heaven'; the Latin reads 'a summo
  caelo' = 'from the highest heaven'". That is close to an ideal hint.
- SCRIPTURE_SUBSTITUTION in particular is the one error class a human
  reviewer reliably MISSES, because the received English reads beautifully.
  The classicist who reviewed ch1 objected to the wording without ever
  realising he was objecting to the King James Version. Sending that class
  to a human is the weakest available remedy.

The gating is preserved: ``propose_fix.py`` emits PROPOSALS. Nothing here
rewrites a translation. The editor still reviews and applies.

Usage
-----
    python symbolic_bridge.py \\
        --flags    08_working_scratch/phase3b/glossary_flags_ch1.jsonl \\
        --segments 03_segmented_text/part1/segments_sentences_xpage.jsonl \\
        --out-inputs 08_working_scratch/phase3b/ch1_symbolic_input.jsonl \\
        --out-scores 08_working_scratch/phase3b/ch1_symbolic_scores.jsonl

then feed those to the existing repair loop:

    python propose_fix.py \\
        --scores-jsonl 08_working_scratch/phase3b/ch1_symbolic_scores.jsonl \\
        --inputs-jsonl 08_working_scratch/phase3b/ch1_symbolic_input.jsonl \\
        --output       08_working_scratch/phase3b/ch1_symbolic_fixes.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Flag kinds worth re-translating for. DRIFT is informational (a term
# rendered two acceptable ways -- an editor decides, a model cannot).
# MISSING_APPROVED is frequently a legitimate Rule-1 collapse or an
# unlisted-but-fine synonym, so it is opt-in via --kinds rather than a
# default trigger; routing it by default would flood the loop with noise.
DEFAULT_KINDS = ("SCRIPTURE_SUBSTITUTION", "BANNED", "ARCHAISM")

# propose_fix.needs_fix() triggers on any rubric score <= --max-cf (default
# 3). A symbolic flag is a deterministic finding, not a graded opinion, so
# it enters at the floor to guarantee the unit is selected.
#
# The rubric key must be one of propose_fix._TRIGGER_RUBRICS. Those are the
# FULL names ('content_fidelity'), not the 'cf' abbreviations used in that
# module's docstring and CLI flag -- a mismatch here silently selects zero
# units, so the key is imported rather than hardcoded.
_SYMBOLIC_SCORE = 1
_SYMBOLIC_RUBRIC = "content_fidelity"


def english_for(record: dict) -> str:
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def _load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def describe(flag: dict) -> str:
    """One actionable diagnostic line for a single flag."""
    kind = flag.get("flag", "?")
    term = flag.get("term", "?")
    found = flag.get("found")
    expected = flag.get("expected") or []
    note = (flag.get("note") or "").strip()

    if isinstance(found, list):
        found_s = ", ".join(str(f) for f in found)
    elif isinstance(found, dict):
        found_s = ", ".join(f"{k} (x{v})" for k, v in found.items())
    else:
        found_s = str(found) if found else "(nothing)"

    if kind == "SCRIPTURE_SUBSTITUTION":
        head = (
            f"[{kind}] {term}: the English reproduces a received English "
            f"Bible -- found {found_s!r}. Ussher quotes the VULGATE and "
            f"argues from its wording. Re-translate this passage from the "
            f"Latin actually printed; do not reproduce the KJV/Douay."
        )
    elif kind == "ARCHAISM":
        head = (
            f"[{kind}] archaic diction in the English: {found_s}. The target "
            f"register is modern academic English. Archaism here usually "
            f"means a received English Bible was recited instead of the "
            f"Latin being translated. Check this passage against the Latin."
        )
    else:  # BANNED
        exp = f" Use instead: {', '.join(expected)}." if expected else ""
        head = (
            f"[{kind}] {term}: the English uses the forbidden rendering "
            f"{found_s!r}.{exp}"
        )
    return f"{head} {note}".strip()


def build_reason(flags: list[dict]) -> str:
    lines = [describe(f) for f in flags]
    return (
        "DETERMINISTIC VALIDATOR FINDINGS (these are code checks against the "
        "Latin source, not a model's opinion -- treat them as reliable):\n"
        + "\n".join(f"- {ln}" for ln in lines)
        + "\n\nCorrect ONLY these issues. Leave the rest of the English "
          "unchanged."
    )


def bridge(flags: list[dict], segments: list[dict], kinds: tuple[str, ...]
           ) -> tuple[list[dict], list[dict]]:
    """Return (inputs, scores) JSONL records for propose_fix.py."""
    by_seg: dict[str, list[dict]] = defaultdict(list)
    for f in flags:
        if f.get("flag") not in kinds:
            continue
        seg_id = str(f.get("segment_id") or "")
        if not seg_id:  # DRIFT rows are corpus-wide and carry no segment
            continue
        by_seg[seg_id].append(f)

    seg_index = {str(s.get("segment_id")): s for s in segments}

    inputs: list[dict] = []
    scores: list[dict] = []
    for seg_id, seg_flags in sorted(by_seg.items()):
        seg = seg_index.get(seg_id)
        if seg is None:
            print(f"  WARN: {seg_id} not found in segments; skipping",
                  file=sys.stderr)
            continue
        # Pull the FULL Latin/English from the segments artifact. The flag
        # records carry truncated excerpts, which must never be fed back to
        # the model as if they were the source.
        inputs.append({
            "unit_id": seg_id,
            "latin_concat": seg.get("latin_text") or "",
            "english_concat": english_for(seg),
        })
        scores.append({
            "unit_id": seg_id,
            "scores": {_SYMBOLIC_RUBRIC: _SYMBOLIC_SCORE},
            "reason": build_reason(seg_flags),
            "source": "symbolic",
            "flags": [f.get("flag") for f in seg_flags],
        })
    return inputs, scores


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Convert symbolic validator flags into propose_fix.py inputs."
    )
    p.add_argument("--flags", required=True, type=Path,
                   help="validator output (e.g. glossary_flags_ch1.jsonl)")
    p.add_argument("--segments", required=True, type=Path,
                   help="translated segments JSONL (supplies full Latin + English)")
    p.add_argument("--out-inputs", required=True, type=Path)
    p.add_argument("--out-scores", required=True, type=Path)
    p.add_argument("--kinds", default=",".join(DEFAULT_KINDS),
                   help=f"comma-separated flag kinds to route "
                        f"(default: {','.join(DEFAULT_KINDS)})")
    args = p.parse_args(argv)

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    flags = _load_jsonl(args.flags)
    segments = _load_jsonl(args.segments)
    inputs, scores = bridge(flags, segments, kinds)

    _write_jsonl(args.out_inputs, inputs)
    _write_jsonl(args.out_scores, scores)

    routed: dict[str, int] = defaultdict(int)
    for s in scores:
        for f in s["flags"]:
            routed[f] += 1
    print(f"Read {len(flags)} flag(s); routing kinds {kinds}")
    print(f"Wrote {len(inputs)} unit(s) to {args.out_inputs}")
    print(f"Wrote {len(scores)} score row(s) to {args.out_scores}")
    for k, n in sorted(routed.items()):
        print(f"  {k:24s} {n:4d}")
    if not inputs:
        print("No actionable flags — nothing to repair.")
    return 0


__all__ = ["bridge", "build_reason", "describe", "DEFAULT_KINDS"]


if __name__ == "__main__":
    raise SystemExit(main())
