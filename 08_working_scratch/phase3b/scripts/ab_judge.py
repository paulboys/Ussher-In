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

By default, live runs are resumable. Each judgment is appended to
``--output`` as soon as it completes; if a later call hits a usage
limit, rerun the same command and already-written segment IDs are
skipped. Use ``--no-resume`` to ignore an existing output file and
start fresh.

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

The candidates may use a three-slot format for embedded Greek:
the Greek is preserved verbatim, immediately followed by an English
rendering inside ⟦…⟧ brackets (U+27E6/U+27E7), optionally followed
by Ussher's own Latin paraphrase inside ⟪…⟫ brackets (U+27EA/U+27EB)
when one is present in the source. Treat these brackets as
scaffolding, not as prose — they are semantically meaningful tags,
not noise.

Your task is to pick the better English rendering on six rubrics,
each scored as A_better / B_better / equal:

* fluency: reads as natural modern scholarly English (prefer plain
  prose; penalize archaisms like 'vouchsafed', 'verily', 'thee',
  'hath', 'doth', 'whilst'). Evaluate the English text inside ⟦…⟧
  plus the surrounding running prose; the bracket characters
  themselves are scaffolding and do NOT count as a fluency hit.
* accuracy: faithful to the Latin's meaning; no dropped clauses,
  invented content, or shifted referents.
  - When ⟦English⟧ follows Greek, the bracketed text must
    faithfully render the meaning of that Greek.
  - When ⟪Latin⟫ follows ⟦English⟧, the Latin must reproduce
    Ussher's actual Latin paraphrase from the source — invented
    Latin is an accuracy failure.
  - Filiation genitives (e.g. 'Eusebius Pamphili', 'Iacobus Alphaei')
    must render with 'of' ('Eusebius of Pamphilus', 'James of
    Alphaeus') — treating the second name as a separate person is
    an accuracy failure.
* source_preservation: prefers PRESERVING the source-language form
  of names and technical terms with a parenthetical English gloss,
  rather than substituting a modern equivalent. Reward
  'preserve+gloss' patterns like 'Uticensis (of Utica)',
  'menologia (calendars of saints)'. Penalize:
  - outright substitution (e.g. 'Uticensis' → 'Saint-Évroul',
    'Symeon Metaphrastes' → 'Simeon the Translator')
  - dropping the original form entirely so the scholarly identifier
    is lost
  - invented modern equivalents with no basis in the Latin
  Standard orthographic normalization for very common names is
  ALLOWED and not penalized: 'Aethiopas' → 'Ethiopians',
  'Theodoretus' → 'Theodoret', 'Antiocheni' → 'Antiochenes',
  'Caesar' for 'Caesar(em/is)'. The line is between *normalized
  spelling of a stable English form* (allowed) and *substitution
  of one identifier for another* (penalized).
* titles: treatise / book titles handled with a hybrid policy.
  Best: original-language title preserved in italics or quotes,
  followed by an optional descriptive English gloss in parentheses
  — '*Vita Constantini* (Life of Constantine)'. Acceptable: pure
  preserved Latin in italics. Worst: bare title in running text,
  or pure-English translation that erases the Latin identifier.
* register: scholarly, modern, neutral. Penalize KJV cadence,
  pseudo-archaic word order, and unnecessary Latinisms.
* format_compliance: mechanical use of the three-slot Greek format.
  - Greek must be preserved verbatim (not transliterated, not
    omitted, not silently translated away).
  - When Greek appears as substantive content, an ⟦English⟧ slot
    should follow.
  - When Ussher's Latin paraphrase is present near the Greek in
    the source (signals: 'id est', 'hoc est', 'sive', 'inquit',
    quotation punctuation, an adjacent Latin clause that visibly
    echoes the Greek), a ⟪Latin⟫ slot reproducing that Latin
    should follow the ⟦English⟧.
  - Bracket characters must be the correct ones: ⟦…⟧
    (U+27E6/U+27E7) for the English slot and ⟪…⟫
    (U+27EA/U+27EB) for the Latin slot. Plain '[]', '«»', or
    '<<>>' are non-compliant.
  - Slot order must be Greek → ⟦English⟧ → ⟪Latin⟫.
  Penalize any of: missing English slot after standalone Greek;
  missing Latin slot when Ussher provides a paraphrase; wrong
  bracket characters; out-of-order slots; invented Greek where
  the source has none.
  If the Latin source contains NO Greek at all in this segment,
  score this rubric 'equal' (the rubric is not applicable).

Then return a single overall winner: A / B / tie. All six rubrics
are equal-weight in the overall call; do not weight any rubric more
heavily than the others.

You MUST NOT reveal which translation comes from which source — you
do not know, and they were assigned randomly. Judge the text only.
"""


JUDGE_OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "rubric": {
    "fluency":             "A" | "B" | "equal",
    "accuracy":            "A" | "B" | "equal",
    "source_preservation": "A" | "B" | "equal",
    "titles":              "A" | "B" | "equal",
    "register":            "A" | "B" | "equal",
    "format_compliance":   "A" | "B" | "equal"
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
        out = {
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
        # Persist raw model output when parsing failed so post-mortems
        # don't require re-running the judge. Truncated to keep files
        # small. Skip on success because raw is redundant with decoded.
        if self.error and self.raw_response:
            out["raw_response"] = self.raw_response[:1500]
        return out


def judgment_from_dict(data: dict) -> Judgment:
    """Rehydrate a persisted JSONL row into a ``Judgment``."""
    return Judgment(
        segment_id=str(data.get("segment_id") or ""),
        swapped=bool(data.get("swapped")),
        a_text=str(data.get("a_text") or ""),
        b_text=str(data.get("b_text") or ""),
        latin=str(data.get("latin") or ""),
        raw_response=str(data.get("raw_response") or ""),
        raw_winner=str(data.get("raw_winner") or ""),
        raw_rubric=dict(data.get("raw_rubric") or {}),
        reason=str(data.get("reason") or ""),
        decoded_winner=str(data.get("decoded_winner") or ""),
        decoded_rubric=dict(data.get("decoded_rubric") or {}),
        error=str(data.get("error") or ""),
    )


def load_existing_judgments(path: Path) -> dict[str, Judgment]:
    """Load an existing judgment JSONL keyed by ``segment_id``.

    Malformed rows are ignored so a partially interrupted final line does
    not block resume. If duplicate segment IDs exist, the last complete
    row wins.
    """
    out: dict[str, Judgment] = {}
    if not path.exists():
        return out
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
                out[str(seg_id)] = judgment_from_dict(rec)
    return out


def ensure_trailing_newline(path: Path) -> None:
    """Make appending safe after an interrupted JSONL write."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as handle:
        handle.seek(-1, 2)
        if handle.read(1) != b"\n":
            handle.write(b"\n")


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

# Substrings that indicate the Claude Code CLI refused the request rather
# than returning a model response (quota, auth, model-not-available, etc.).
# Detected before parsing so the judge can abort the whole loop instead of
# burning through 36+ pairings producing identical "parse failed" rows.
_QUOTA_MARKERS = (
    "out of extra usage",
    "extra usage",
    "hit your session limit",
    "session limit",
    "usage limit reached",
    "rate limit",
    "please try again",
    "resets ",
)


class JudgeQuotaError(RuntimeError):
    """Raised when the judge CLI returns a quota/refusal sentinel."""


def _looks_like_quota_refusal(raw: str) -> bool:
    if not raw:
        return False
    head = raw.strip().lower()
    if len(head) > 400:  # real model responses are longer than refusals
        return False
    return any(marker in head for marker in _QUOTA_MARKERS)


def parse_judge_response(raw: str) -> dict:
    """Pull the first JSON object out of *raw* and validate keys."""
    if not raw:
        raise ValueError("empty judge response")
    if _looks_like_quota_refusal(raw):
        raise JudgeQuotaError(raw.strip())
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
        if _looks_like_quota_refusal(str(exc)):
            raise JudgeQuotaError(str(exc))
        j.error = f"judge call failed: {exc}"
        return j
    j.raw_response = raw
    # Detect CLI-level refusals (quota, auth) before trying to parse
    # JSON; otherwise every segment in the loop produces an identical
    # "parse failed" row that masks the real cause.
    if _looks_like_quota_refusal(raw):
        raise JudgeQuotaError(raw.strip())
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


def write_summary(
    *,
    path: Path | None,
    judgments: Sequence[Judgment],
    judge_model: str,
    seed: int,
    v0_path: Path,
    v1_path: Path,
    output_path: Path,
    total_shared_segments: int,
    skipped_existing: int,
    complete: bool,
) -> dict:
    """Write an aggregate summary, including resume/progress metadata."""
    summary = aggregate_judgments(judgments)
    completed_ids = {j.segment_id for j in judgments if j.segment_id}
    summary["judge_model"] = judge_model
    summary["seed"] = seed
    summary["v0_path"] = str(v0_path)
    summary["v1_path"] = str(v1_path)
    summary["output_path"] = str(output_path)
    summary["total_shared_segments"] = total_shared_segments
    summary["completed_segments"] = len(completed_ids)
    summary["remaining_segments"] = max(
        0, total_shared_segments - len(completed_ids)
    )
    summary["skipped_existing"] = skipped_existing
    summary["complete"] = complete
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


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
        "--no-resume", action="store_true",
        help=(
            "Ignore any existing --output JSONL and start a fresh run. "
            "Default behavior is to resume by skipping existing segment IDs."
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
    v0 = _load_run(args.v0_jsonl)
    v1 = _load_run(args.v1_jsonl)
    shared = sorted(set(v0) & set(v1))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Judgment] = {}
    if args.no_resume:
        args.output.write_text("", encoding="utf-8")
    else:
        existing = {
            seg_id: judgment
            for seg_id, judgment in load_existing_judgments(args.output).items()
            if seg_id in shared
        }
        ensure_trailing_newline(args.output)
    completed_ids = set(existing)
    judgments: list[Judgment] = [
        existing[seg_id] for seg_id in shared if seg_id in existing
    ]
    skipped_existing = len(judgments)
    if skipped_existing:
        print(
            f"ab_judge: resuming from {args.output}; "
            f"skipping {skipped_existing}/{len(shared)} completed segments"
        )

    summary = write_summary(
        path=args.summary,
        judgments=judgments,
        judge_model=args.judge_model,
        seed=args.seed,
        v0_path=args.v0_jsonl,
        v1_path=args.v1_jsonl,
        output_path=args.output,
        total_shared_segments=len(shared),
        skipped_existing=skipped_existing,
        complete=len(completed_ids) == len(shared),
    )

    with args.output.open("a", encoding="utf-8") as handle:
        for idx, seg_id in enumerate(shared, start=1):
            if seg_id in completed_ids:
                continue
            v0_rec, v1_rec = v0[seg_id], v1[seg_id]
            latin = (
                v0_rec.get("latin_text")
                or v1_rec.get("latin_text")
                or ""
            )
            v0_text = _english_for(v0_rec)
            v1_text = _english_for(v1_rec)
            swapped = assign_swap(seg_id, seed=args.seed)
            if not v0_text.strip() or not v1_text.strip():
                a_text, b_text = (
                    (v1_text, v0_text) if swapped else (v0_text, v1_text)
                )
                judgment = Judgment(
                    segment_id=seg_id,
                    swapped=swapped,
                    a_text=a_text,
                    b_text=b_text,
                    latin=latin,
                    error="missing english on one side",
                )
            else:
                try:
                    judgment = judge_pair(
                        segment_id=seg_id,
                        latin=latin,
                        v0_text=v0_text,
                        v1_text=v1_text,
                        seed=args.seed,
                        call_judge=call_judge,
                    )
                except JudgeQuotaError as exc:
                    summary = write_summary(
                        path=args.summary,
                        judgments=judgments,
                        judge_model=args.judge_model,
                        seed=args.seed,
                        v0_path=args.v0_jsonl,
                        v1_path=args.v1_jsonl,
                        output_path=args.output,
                        total_shared_segments=len(shared),
                        skipped_existing=skipped_existing,
                        complete=False,
                    )
                    print(
                        "ab_judge: paused — judge CLI refused with: "
                        f"{exc}\n"
                        f"Saved {summary['completed_segments']}/"
                        f"{summary['total_shared_segments']} judgments. "
                        "Rerun the same command after reset to resume.",
                        file=sys.stderr,
                    )
                    return 3
            judgments.append(judgment)
            completed_ids.add(seg_id)
            handle.write(
                json.dumps(judgment.to_dict(), ensure_ascii=False) + "\n"
            )
            handle.flush()
            summary = write_summary(
                path=args.summary,
                judgments=judgments,
                judge_model=args.judge_model,
                seed=args.seed,
                v0_path=args.v0_jsonl,
                v1_path=args.v1_jsonl,
                output_path=args.output,
                total_shared_segments=len(shared),
                skipped_existing=skipped_existing,
                complete=len(completed_ids) == len(shared),
            )
            status = (
                judgment.decoded_winner
                if not judgment.error else f"error: {judgment.error}"
            )
            print(
                f"[{idx}/{len(shared)}] {seg_id} -> {status} "
                f"(saved {summary['completed_segments']}/"
                f"{summary['total_shared_segments']})"
            )

    summary = write_summary(
        path=args.summary,
        judgments=judgments,
        judge_model=args.judge_model,
        seed=args.seed,
        v0_path=args.v0_jsonl,
        v1_path=args.v1_jsonl,
        output_path=args.output,
        total_shared_segments=len(shared),
        skipped_existing=skipped_existing,
        complete=True,
    )

    if skipped_existing and not shared:
        print("ab_judge: no shared segments to judge")
    elif len(completed_ids) == len(shared) and skipped_existing == len(shared):
        print(
            f"ab_judge: all {len(shared)} segments already present in "
            f"{args.output}; summary refreshed"
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
    "JudgeQuotaError",
    "Judgment",
    "aggregate_judgments",
    "assign_swap",
    "build_judge_prompt",
    "decode_rubric",
    "decode_winner",
    "judge_pair",
    "judge_run",
    "judgment_from_dict",
    "load_existing_judgments",
    "parse_judge_response",
    "write_summary",
]
