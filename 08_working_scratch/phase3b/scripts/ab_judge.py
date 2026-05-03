"""Anonymized A/B judge for the prompt-version comparison.

Phase 3 of the p0039 translation-prompt A/B test. Reads two
``segments_with_translations.jsonl`` artifacts (one v0 run, one v1
run of the same page) and asks an LLM to pick the better translation
for each shared segment, anonymized, with side-swap to neutralize
position bias.

The judge model is, by default, Claude Sonnet 4.6 — different from the
translator (Opus 4.7) so the judge can't trivially recognize its own
output. Both go through the same Claude Code CLI transport, so no new
auth path is needed.

Determinism
-----------
The side-swap assignment is ``hash(segment_id) % 2`` keyed on a
user-supplied integer seed (default 0). Same seed -> same assignment,
which makes runs reproducible. The judge model itself is non-
deterministic, so re-running the judge will produce slightly
different rubric scores; the side-swap layer is what we control.

CLI
---
::

    python ab_judge.py <v0_run.jsonl> <v1_run.jsonl> \\
        --output judgments.jsonl \\
        [--judge-model claude-sonnet-4-6] \\
        [--seed 0] [--dry-run]

In ``--dry-run`` mode the judge prints the prompts it would send and
the side-swap map but does not call the CLI. Useful for sanity-
checking before spending tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

# When invoked as a CLI, ``pipeline_scripts`` is not on sys.path; the
# tests get it from conftest.py. Bootstrap it here so the import below
# works in both contexts.
_PIPELINE_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "pipeline_scripts"
)
if str(_PIPELINE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_SCRIPTS))

# Reuse the translation adapter's CLI plumbing. The judge call is just
# another `claude -p <prompt> --model X` invocation.
import translation_adapters as ta  # noqa: E402


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are an expert classical translator and editor evaluating two
candidate English translations of the same Latin sentence from a
17th-century scholarly work (James Ussher's Britannicarum Ecclesiarum
Antiquitates, 1847 Elrington reissue). Latin sources are early-modern
ecclesiastical/humanist Latin with embedded Patristic Greek citations.

Your task is to pick the better English rendering on five rubrics,
each scored as A_better / B_better / equal:

* fluency: reads as natural modern scholarly English (prefer plain
  prose; penalize archaisms like 'vouchsafed', 'verily', 'thee',
  'hath', 'doth', 'whilst').
* accuracy: faithful to the Latin's meaning; no dropped clauses,
  invented content, or shifted referents.
* proper_nouns: prefers Anglicized forms ('Boudica' over 'Boadicia',
  'Caesar' over 'Caesariis', 'Ethiopians' over 'Aethiopas',
  'Antiochenes' over 'Antiocheni', 'Theodoret' over 'Theodoretus').
* titles: treatise / book titles are italicized (or in quotes) rather
  than left bare in running text.
* register: scholarly, modern, neutral. Penalize KJV cadence,
  pseudo-archaic word order, and unnecessary Latinisms.

Then return a single overall winner: A / B / tie.

You MUST NOT reveal which translation comes from which source — you
do not know, and they were assigned randomly. Judge the text only.
"""


JUDGE_OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "rubric": {
    "fluency":      "A" | "B" | "equal",
    "accuracy":     "A" | "B" | "equal",
    "proper_nouns": "A" | "B" | "equal",
    "titles":       "A" | "B" | "equal",
    "register":     "A" | "B" | "equal"
  },
  "winner": "A" | "B" | "tie",
  "reason": "<one or two sentences explaining the call>"
}

Rules:
- Every rubric key must be present and one of the three string values.
- 'winner' must be one of "A", "B", "tie".
- 'reason' is a short free-text explanation (<=400 chars).
- Do not include any other top-level keys. Do not wrap in code fences.
"""


def build_judge_prompt(
    *,
    segment_id: str,
    latin: str,
    a_text: str,
    b_text: str,
) -> str:
    """Build the per-segment judge prompt.

    The Latin is included so the judge can score 'accuracy' against
    the source rather than against either candidate alone. The two
    candidates are labelled A and B only; the side-swap layer above
    decides which version is which.
    """
    return (
        JUDGE_SYSTEM
        + "\n\nLatin source (segment "
        + segment_id
        + "):\n"
        + latin.rstrip()
        + "\n\nTranslation A:\n"
        + a_text.rstrip()
        + "\n\nTranslation B:\n"
        + b_text.rstrip()
        + "\n\n"
        + JUDGE_OUTPUT_CONTRACT
    )


# ---------------------------------------------------------------------------
# Side-swap
# ---------------------------------------------------------------------------


def assign_swap(segment_id: str, *, seed: int) -> bool:
    """Decide whether to swap v0/v1 -> A/B for this segment.

    Returns ``True`` when A=v1, B=v0 (i.e. v0 is on the "B" side);
    ``False`` when A=v0, B=v1. Uses sha1 keyed by the seed so the
    distribution is stable across machines and Python releases.
    """
    h = hashlib.sha1(f"{seed}:{segment_id}".encode("utf-8")).digest()
    return (h[0] & 1) == 1


def decode_winner(raw_winner: str, swapped: bool) -> str:
    """Map the judge's "A"/"B"/"tie" call back to "v0"/"v1"/"tie".

    When ``swapped`` is True, A=v1 and B=v0; otherwise A=v0, B=v1.
    """
    raw = (raw_winner or "").strip().upper()
    if raw == "TIE":
        return "tie"
    if raw == "A":
        return "v1" if swapped else "v0"
    if raw == "B":
        return "v0" if swapped else "v1"
    return "invalid"


def decode_rubric(rubric: dict, swapped: bool) -> dict:
    """Map every rubric verdict back to v0/v1/equal."""
    out: dict[str, str] = {}
    for key, verdict in (rubric or {}).items():
        v = (verdict or "").strip().upper()
        if v == "EQUAL":
            out[key] = "equal"
        elif v == "A":
            out[key] = "v1" if swapped else "v0"
        elif v == "B":
            out[key] = "v0" if swapped else "v1"
        else:
            out[key] = "invalid"
    return out


# ---------------------------------------------------------------------------
# Loading + pairing
# ---------------------------------------------------------------------------


def _english_for(record: dict) -> str:
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def _load_run(path: Path) -> dict[str, dict]:
    """Return ``{segment_id: record}`` from a JSONL artifact."""
    out: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            seg_id = rec.get("segment_id")
            if seg_id:
                out[str(seg_id)] = rec
    return out


# ---------------------------------------------------------------------------
# Judgment record
# ---------------------------------------------------------------------------


@dataclass
class Judgment:
    segment_id: str
    swapped: bool
    a_text: str
    b_text: str
    latin: str
    raw_response: str = ""
    raw_winner: str = ""
    raw_rubric: dict = field(default_factory=dict)
    reason: str = ""
    decoded_winner: str = ""
    decoded_rubric: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "swapped": self.swapped,
            "latin": self.latin,
            "a_text": self.a_text,
            "b_text": self.b_text,
            "raw_winner": self.raw_winner,
            "raw_rubric": self.raw_rubric,
            "reason": self.reason,
            "decoded_winner": self.decoded_winner,
            "decoded_rubric": self.decoded_rubric,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Judge runner
# ---------------------------------------------------------------------------


JudgeCallable = Callable[[str], str]
"""A callable that takes the judge prompt and returns the raw model
response string. The default implementation shells out to the Claude
Code CLI via ``translation_adapters._default_command_runner``."""


def _make_default_judge(
    *,
    judge_model: str,
    cli_path: str = "claude",
    timeout_seconds: float | None = None,
) -> JudgeCallable:
    """Build a callable that invokes Claude Code CLI with the judge model."""

    def call(prompt: str) -> str:
        argv = [cli_path, "-p", prompt, "--dangerously-skip-permissions"]
        if judge_model and judge_model != "local":
            argv.extend(["--model", judge_model])
        result = ta._default_command_runner(argv, "", timeout_seconds)
        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(
                f"judge CLI exit {result.returncode}: {result.stderr[:200]}"
            )
        return result.stdout

    return call


_JSON_OBJ_RE = __import__("re").compile(r"\{.*\}", __import__("re").DOTALL)


def parse_judge_response(raw: str) -> dict:
    """Pull the first JSON object out of *raw* and validate keys."""
    if not raw:
        raise ValueError("empty judge response")
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # drop optional language hint on first line
        if "\n" in text:
            _, text = text.split("\n", 1)
    match = _JSON_OBJ_RE.search(text)
    if not match:
        raise ValueError("no JSON object found in judge response")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("judge JSON is not an object")
    if "winner" not in parsed:
        raise ValueError("judge JSON missing 'winner'")
    if "rubric" not in parsed:
        raise ValueError("judge JSON missing 'rubric'")
    return parsed


def judge_pair(
    *,
    segment_id: str,
    latin: str,
    v0_text: str,
    v1_text: str,
    seed: int,
    call_judge: JudgeCallable,
) -> Judgment:
    """Run the judge on one segment and return a decoded Judgment."""
    swapped = assign_swap(segment_id, seed=seed)
    if swapped:
        a_text, b_text = v1_text, v0_text
    else:
        a_text, b_text = v0_text, v1_text
    j = Judgment(
        segment_id=segment_id,
        swapped=swapped,
        a_text=a_text,
        b_text=b_text,
        latin=latin,
    )
    prompt = build_judge_prompt(
        segment_id=segment_id, latin=latin, a_text=a_text, b_text=b_text,
    )
    try:
        raw = call_judge(prompt)
    except Exception as exc:  # surface but keep going on remaining segments
        j.error = f"judge call failed: {exc}"
        return j
    j.raw_response = raw
    try:
        parsed = parse_judge_response(raw)
    except Exception as exc:
        j.error = f"parse failed: {exc}"
        return j
    j.raw_winner = str(parsed.get("winner", ""))
    j.raw_rubric = dict(parsed.get("rubric") or {})
    j.reason = str(parsed.get("reason", ""))[:400]
    j.decoded_winner = decode_winner(j.raw_winner, swapped)
    j.decoded_rubric = decode_rubric(j.raw_rubric, swapped)
    return j


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


def judge_run(
    *,
    v0_path: Path,
    v1_path: Path,
    call_judge: JudgeCallable,
    seed: int = 0,
) -> list[Judgment]:
    """Pair shared segments across two A/B JSONL artifacts and judge each."""
    v0 = _load_run(v0_path)
    v1 = _load_run(v1_path)
    shared = sorted(set(v0) & set(v1))
    out: list[Judgment] = []
    for seg_id in shared:
        v0_rec, v1_rec = v0[seg_id], v1[seg_id]
        latin = (
            v0_rec.get("latin_text")
            or v1_rec.get("latin_text")
            or ""
        )
        v0_text = _english_for(v0_rec)
        v1_text = _english_for(v1_rec)
        if not v0_text.strip() or not v1_text.strip():
            j = Judgment(
                segment_id=seg_id,
                swapped=assign_swap(seg_id, seed=seed),
                a_text=v0_text,
                b_text=v1_text,
                latin=latin,
                error="missing english on one side",
            )
            out.append(j)
            continue
        out.append(judge_pair(
            segment_id=seg_id,
            latin=latin,
            v0_text=v0_text,
            v1_text=v1_text,
            seed=seed,
            call_judge=call_judge,
        ))
    return out


def aggregate_judgments(judgments: Sequence[Judgment]) -> dict:
    """Count v0/v1/tie wins overall and per rubric."""
    overall = {"v0": 0, "v1": 0, "tie": 0, "invalid": 0, "error": 0}
    rubric: dict[str, dict[str, int]] = {}
    for j in judgments:
        if j.error:
            overall["error"] += 1
            continue
        key = j.decoded_winner if j.decoded_winner in overall else "invalid"
        overall[key] += 1
        for rub_key, verdict in j.decoded_rubric.items():
            slot = rubric.setdefault(
                rub_key, {"v0": 0, "v1": 0, "equal": 0, "invalid": 0}
            )
            slot[verdict if verdict in slot else "invalid"] += 1
    return {
        "n": len(judgments),
        "overall": overall,
        "rubric": rubric,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Anonymized LLM A/B judge with side-swap. Compares two "
            "segments_with_translations.jsonl artifacts segment-by-"
            "segment using a different model from the translator."
        ),
    )
    parser.add_argument("v0_jsonl", type=Path, help="v0 run artifact.")
    parser.add_argument("v1_jsonl", type=Path, help="v1 run artifact.")
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to write the per-segment judgments JSONL.",
    )
    parser.add_argument(
        "--summary", type=Path, default=None,
        help="Optional path to write the aggregate summary JSON.",
    )
    parser.add_argument(
        "--judge-model", default="claude-sonnet-4-6",
        help=(
            "Claude Code CLI --model id for the judge. Defaults to "
            "claude-sonnet-4-6 (different family-size from the "
            "claude-opus-4-7 translator). The 1M context window is "
            "built in; no extra flag needed."
        ),
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Side-swap seed (default 0). Same seed => same A/B assignment.",
    )
    parser.add_argument(
        "--timeout-seconds", type=float, default=None,
        help="Per-call CLI timeout. Default: no timeout.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help=(
            "Print the side-swap map and prompt sizes but do not call "
            "the CLI. No tokens spent."
        ),
    )
    parser.add_argument(
        "--cli-path", default="claude",
        help="Override the Claude CLI executable name (default 'claude').",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.v0_jsonl.exists():
        print(f"ab_judge: file not found: {args.v0_jsonl}", file=sys.stderr)
        return 2
    if not args.v1_jsonl.exists():
        print(f"ab_judge: file not found: {args.v1_jsonl}", file=sys.stderr)
        return 2

    if args.dry_run:
        v0 = _load_run(args.v0_jsonl)
        v1 = _load_run(args.v1_jsonl)
        shared = sorted(set(v0) & set(v1))
        print(f"ab_judge dry-run: {len(shared)} shared segments")
        for seg_id in shared:
            swapped = assign_swap(seg_id, seed=args.seed)
            label = "A=v1,B=v0" if swapped else "A=v0,B=v1"
            v0_text = _english_for(v0[seg_id])
            v1_text = _english_for(v1[seg_id])
            prompt = build_judge_prompt(
                segment_id=seg_id,
                latin=v0[seg_id].get("latin_text") or "",
                a_text=v1_text if swapped else v0_text,
                b_text=v0_text if swapped else v1_text,
            )
            print(
                f"  {seg_id}  {label}  prompt_chars={len(prompt)}"
            )
        return 0

    call_judge = _make_default_judge(
        judge_model=args.judge_model,
        cli_path=args.cli_path,
        timeout_seconds=args.timeout_seconds,
    )
    judgments = judge_run(
        v0_path=args.v0_jsonl,
        v1_path=args.v1_jsonl,
        call_judge=call_judge,
        seed=args.seed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for j in judgments:
            handle.write(json.dumps(j.to_dict(), ensure_ascii=False) + "\n")

    summary = aggregate_judgments(judgments)
    summary["judge_model"] = args.judge_model
    summary["seed"] = args.seed
    summary["v0_path"] = str(args.v0_jsonl)
    summary["v1_path"] = str(args.v1_jsonl)

    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    overall = summary["overall"]
    print(
        f"ab_judge: n={summary['n']}  "
        f"v1_wins={overall['v1']}  v0_wins={overall['v0']}  "
        f"ties={overall['tie']}  invalid={overall['invalid']}  "
        f"errors={overall['error']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "JUDGE_SYSTEM",
    "JUDGE_OUTPUT_CONTRACT",
    "Judgment",
    "aggregate_judgments",
    "assign_swap",
    "build_judge_prompt",
    "decode_rubric",
    "decode_winner",
    "judge_pair",
    "judge_run",
    "parse_judge_response",
]
