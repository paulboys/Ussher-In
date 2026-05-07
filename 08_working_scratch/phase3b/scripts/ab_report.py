"""Aggregator + decision-gate report for the prompt A/B test.

Phase 4 of the p0039 translation-prompt A/B test. Reads:

* every ``v0/<run>/segments_with_translations.jsonl`` and
  ``v1/<run>/segments_with_translations.jsonl`` under the base dir,
  scoring each through ``ab_rules``;
* every ``judgments/*.jsonl`` under the base dir (or any
  ``--judgments-glob``), aggregating winner counts per pair and pooled
  across pairs.

Then it writes:

* ``summary.json`` — machine-readable rollup (mechanical deltas, judge
  win-rates, position-bias rate, decision verdict).
* ``<page>_report.md`` — human-readable report keyed off ``--page``.

Decision gate (pre-registered before any data was collected)
------------------------------------------------------------
v1 PASSES when ALL of:

1. **mechanical regressions == 0**: pooled net change in rule hits
   (v1 − v0) for every rule class is ≤ 0.
2. **judge overall win-rate ≥ 55 %** with **tie rate < 30 %**.
3. **per-rubric**: v1 wins on **≥ 5 of the 6** rubric classes with
   no losses (a "loss" is v0_wins > v1_wins on that class).
4. **position bias < 10 pp**: |P(A_picked) − 0.5| < 0.10.
5. **judge invalid+error rate < 10 %**: at least 90 % of pairs
   produced a usable verdict.

Anything weaker than PASS is FAIL or INSUFFICIENT (when sample size
or coverage rules out a confident call).

CLI
---
::

    python ab_report.py <base_dir> --page p0039
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# Bootstrap sibling scripts onto sys.path when invoked as a CLI.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import ab_rules  # noqa: E402
import ab_judge  # noqa: E402


# ---------------------------------------------------------------------------
# Pre-registered thresholds
# ---------------------------------------------------------------------------

# These constants live here, in module scope, so the report and the
# tests share one source of truth. Changing them after a run is a
# protocol violation; the report flags it as a "post-hoc threshold
# adjustment" if the file is edited after summary.json is written.

THRESHOLD_WIN_RATE = 0.55          # gate (2)
THRESHOLD_TIE_RATE_MAX = 0.30      # gate (2)
THRESHOLD_RUBRIC_WINS_MIN = 5      # gate (3): out of 6 rubrics
THRESHOLD_POSITION_BIAS_MAX = 0.10 # gate (4): |P(A_picked) - 0.5|
THRESHOLD_INVALID_RATE_MAX = 0.10  # gate (5)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RunArtifact:
    version: str   # "v0" or "v1"
    run_tag: str
    path: Path
    rule_summary: ab_rules.RunSummary | None = None


@dataclass
class JudgmentBatch:
    path: Path
    judgments: list[ab_judge.Judgment] = field(default_factory=list)
    a_picked: int = 0
    b_picked: int = 0
    tie: int = 0
    invalid: int = 0
    error: int = 0


@dataclass
class Verdict:
    label: str           # "PASS", "FAIL", or "INSUFFICIENT"
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_runs(base_dir: Path) -> list[RunArtifact]:
    """Find every ``<base>/<v0|v1>/<run-tag>/segments_with_translations.jsonl``."""
    out: list[RunArtifact] = []
    for version in ("v0", "v1"):
        version_dir = base_dir / version
        if not version_dir.is_dir():
            continue
        for run_dir in sorted(p for p in version_dir.iterdir() if p.is_dir()):
            jsonl = run_dir / "segments_with_translations.jsonl"
            if jsonl.is_file():
                out.append(RunArtifact(
                    version=version,
                    run_tag=run_dir.name,
                    path=jsonl,
                ))
    return out


def discover_judgments(
    base_dir: Path, *, glob: str = "judgments/*.jsonl",
) -> list[Path]:
    return sorted(base_dir.glob(glob))


# ---------------------------------------------------------------------------
# Mechanical layer
# ---------------------------------------------------------------------------


def score_runs_mechanical(runs: Sequence[RunArtifact]) -> None:
    """Populate ``run.rule_summary`` for each run in place."""
    for run in runs:
        run.rule_summary = ab_rules.score_run(run.path)


def pool_rule_counts(runs: Sequence[RunArtifact], version: str) -> dict[str, int]:
    """Sum rule findings across all runs of *version*."""
    pooled: dict[str, int] = {}
    for run in runs:
        if run.version != version or run.rule_summary is None:
            continue
        for rule, count in run.rule_summary.by_rule().items():
            pooled[rule] = pooled.get(rule, 0) + count
    return pooled


def normalize_rule_counts(
    pooled: dict[str, int], runs: Sequence[RunArtifact], version: str,
) -> dict[str, float]:
    """Per-segment rate so v0 (n runs) and v1 (n runs) are comparable.

    Without this, more v1 runs would always inflate v1's hit count.
    """
    total_segs = sum(
        (run.rule_summary.segments if run.rule_summary else 0)
        for run in runs if run.version == version
    )
    if total_segs == 0:
        return {k: 0.0 for k in pooled}
    return {k: v / total_segs for k, v in pooled.items()}


# ---------------------------------------------------------------------------
# Judge layer
# ---------------------------------------------------------------------------


def load_judgments(path: Path) -> JudgmentBatch:
    batch = JudgmentBatch(path=path)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            j = ab_judge.Judgment(
                segment_id=str(rec.get("segment_id", "")),
                swapped=bool(rec.get("swapped", False)),
                a_text=rec.get("a_text", ""),
                b_text=rec.get("b_text", ""),
                latin=rec.get("latin", ""),
                raw_winner=str(rec.get("raw_winner", "")),
                raw_rubric=dict(rec.get("raw_rubric") or {}),
                reason=str(rec.get("reason", "")),
                decoded_winner=str(rec.get("decoded_winner", "")),
                decoded_rubric=dict(rec.get("decoded_rubric") or {}),
                error=str(rec.get("error", "")),
            )
            batch.judgments.append(j)
            if j.error:
                batch.error += 1
                continue
            raw = j.raw_winner.strip().upper()
            if raw == "A":
                batch.a_picked += 1
            elif raw == "B":
                batch.b_picked += 1
            elif raw == "TIE":
                batch.tie += 1
            else:
                batch.invalid += 1
    return batch


def pool_judgments(batches: Sequence[JudgmentBatch]) -> dict:
    """Aggregate decoded counts across every judgment batch."""
    overall = {"v0": 0, "v1": 0, "tie": 0, "invalid": 0, "error": 0}
    rubric: dict[str, dict[str, int]] = {}
    a_picks = 0
    b_picks = 0
    n_total = 0
    for batch in batches:
        n_total += len(batch.judgments)
        a_picks += batch.a_picked
        b_picks += batch.b_picked
        for j in batch.judgments:
            if j.error:
                overall["error"] += 1
                continue
            key = j.decoded_winner if j.decoded_winner in overall else "invalid"
            overall[key] += 1
            for rk, verdict in j.decoded_rubric.items():
                slot = rubric.setdefault(
                    rk, {"v0": 0, "v1": 0, "equal": 0, "invalid": 0}
                )
                slot[verdict if verdict in slot else "invalid"] += 1
    return {
        "n": n_total,
        "overall": overall,
        "rubric": rubric,
        "a_picked": a_picks,
        "b_picked": b_picks,
    }


# ---------------------------------------------------------------------------
# Decision gate
# ---------------------------------------------------------------------------


def evaluate_verdict(
    *,
    rule_delta: dict[str, float],
    judge_pool: dict,
) -> Verdict:
    """Apply the five pre-registered gates; return PASS/FAIL/INSUFFICIENT.

    *rule_delta* is the per-segment v1−v0 rate per rule class. Positive
    numbers mean v1 has MORE hits than v0, i.e. a regression.
    """
    reasons: list[str] = []
    insufficient = False

    # Sample-size / coverage check first.
    n = judge_pool.get("n", 0)
    overall = judge_pool.get("overall") or {}
    decided = overall.get("v0", 0) + overall.get("v1", 0) + overall.get("tie", 0)
    invalid = overall.get("invalid", 0) + overall.get("error", 0)
    if n == 0:
        reasons.append("no judgments available; cannot evaluate.")
        return Verdict(label="INSUFFICIENT", reasons=reasons)
    invalid_rate = invalid / n if n else 0.0
    if invalid_rate >= THRESHOLD_INVALID_RATE_MAX:
        reasons.append(
            f"invalid+error rate {invalid_rate:.0%} ≥ "
            f"{THRESHOLD_INVALID_RATE_MAX:.0%} (gate 5)."
        )
        insufficient = True

    if decided == 0:
        reasons.append("no decoded verdicts; cannot evaluate gates 2–4.")
        return Verdict(label="INSUFFICIENT", reasons=reasons)

    # Gate 1: mechanical regressions.
    regressed = [k for k, d in rule_delta.items() if d > 0]
    if regressed:
        reasons.append(
            "mechanical regressions on: "
            + ", ".join(f"{k} (+{rule_delta[k]:.3f}/seg)" for k in regressed)
            + " (gate 1)."
        )

    # Gate 2: overall win-rate and tie cap.
    v1 = overall.get("v1", 0)
    v0 = overall.get("v0", 0)
    tie = overall.get("tie", 0)
    win_rate = v1 / decided
    tie_rate = tie / decided
    if win_rate < THRESHOLD_WIN_RATE:
        reasons.append(
            f"v1 win-rate {win_rate:.0%} < {THRESHOLD_WIN_RATE:.0%} (gate 2)."
        )
    if tie_rate >= THRESHOLD_TIE_RATE_MAX:
        reasons.append(
            f"tie-rate {tie_rate:.0%} ≥ {THRESHOLD_TIE_RATE_MAX:.0%} (gate 2)."
        )

    # Gate 3: per-rubric.
    rubric = judge_pool.get("rubric") or {}
    rubric_wins = 0
    rubric_losses = []
    for rk, slot in rubric.items():
        v1c = slot.get("v1", 0)
        v0c = slot.get("v0", 0)
        if v1c > v0c:
            rubric_wins += 1
        elif v0c > v1c:
            rubric_losses.append(rk)
    if rubric_wins < THRESHOLD_RUBRIC_WINS_MIN:
        reasons.append(
            f"v1 won only {rubric_wins} of 6 rubrics (need "
            f"≥{THRESHOLD_RUBRIC_WINS_MIN}, gate 3)."
        )
    if rubric_losses:
        reasons.append(
            "v1 lost on rubric(s): " + ", ".join(rubric_losses) + " (gate 3)."
        )

    # Gate 4: position bias.
    a = judge_pool.get("a_picked", 0)
    b = judge_pool.get("b_picked", 0)
    ab_decided = a + b
    if ab_decided:
        a_rate = a / ab_decided
        bias = abs(a_rate - 0.5)
        if bias >= THRESHOLD_POSITION_BIAS_MAX:
            reasons.append(
                f"position bias |P(A) - 0.5| = {bias:.0%} ≥ "
                f"{THRESHOLD_POSITION_BIAS_MAX:.0%} (gate 4)."
            )
    else:
        reasons.append("no A/B picks; cannot evaluate position bias.")
        insufficient = True

    if insufficient:
        return Verdict(label="INSUFFICIENT", reasons=reasons)
    if reasons:
        return Verdict(label="FAIL", reasons=reasons)
    return Verdict(label="PASS", reasons=["all five pre-registered gates met."])


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def build_summary(
    *,
    base_dir: Path,
    runs: Sequence[RunArtifact],
    batches: Sequence[JudgmentBatch],
) -> dict:
    score_runs_mechanical(runs)
    v0_pooled = pool_rule_counts(runs, "v0")
    v1_pooled = pool_rule_counts(runs, "v1")
    v0_rate = normalize_rule_counts(v0_pooled, runs, "v0")
    v1_rate = normalize_rule_counts(v1_pooled, runs, "v1")
    all_rules = sorted(set(v0_rate) | set(v1_rate))
    delta = {k: v1_rate.get(k, 0.0) - v0_rate.get(k, 0.0) for k in all_rules}

    judge_pool = pool_judgments(batches)
    verdict = evaluate_verdict(rule_delta=delta, judge_pool=judge_pool)

    return {
        "base_dir": str(base_dir),
        "runs": [
            {
                "version": r.version,
                "run_tag": r.run_tag,
                "path": str(r.path),
                "segments": (r.rule_summary.segments if r.rule_summary else 0),
                "by_rule": (r.rule_summary.by_rule() if r.rule_summary else {}),
            }
            for r in runs
        ],
        "mechanical": {
            "v0_pooled": v0_pooled,
            "v1_pooled": v1_pooled,
            "v0_per_segment": v0_rate,
            "v1_per_segment": v1_rate,
            "delta_per_segment_v1_minus_v0": delta,
        },
        "judgments": {
            "batches": [
                {
                    "path": str(b.path),
                    "n": len(b.judgments),
                    "a_picked": b.a_picked,
                    "b_picked": b.b_picked,
                    "tie": b.tie,
                    "invalid": b.invalid,
                    "error": b.error,
                }
                for b in batches
            ],
            "pooled": judge_pool,
        },
        "thresholds": {
            "win_rate": THRESHOLD_WIN_RATE,
            "tie_rate_max": THRESHOLD_TIE_RATE_MAX,
            "rubric_wins_min": THRESHOLD_RUBRIC_WINS_MIN,
            "position_bias_max": THRESHOLD_POSITION_BIAS_MAX,
            "invalid_rate_max": THRESHOLD_INVALID_RATE_MAX,
        },
        "verdict": {"label": verdict.label, "reasons": verdict.reasons},
    }


def render_markdown(summary: dict, *, page: str) -> str:
    """Render *summary* as a human-readable markdown report."""
    out: list[str] = []
    out.append(f"# A/B prompt test — {page}")
    out.append("")
    verdict = summary["verdict"]
    out.append(f"**Verdict:** **{verdict['label']}**")
    out.append("")
    if verdict["reasons"]:
        out.append("Reasons:")
        for r in verdict["reasons"]:
            out.append(f"- {r}")
        out.append("")

    # Runs
    out.append("## Runs scored")
    out.append("")
    out.append("| version | run_tag | segments | total findings |")
    out.append("|---|---|---:|---:|")
    for run in summary["runs"]:
        total = sum(run["by_rule"].values())
        out.append(
            f"| {run['version']} | {run['run_tag']} | {run['segments']} | {total} |"
        )
    out.append("")

    # Mechanical
    mech = summary["mechanical"]
    all_rules = sorted(set(mech["v0_per_segment"]) | set(mech["v1_per_segment"]))
    out.append("## Mechanical (per-segment rate)")
    out.append("")
    out.append("| rule | v0/seg | v1/seg | Δ (v1−v0) |")
    out.append("|---|---:|---:|---:|")
    for rk in all_rules:
        v0 = mech["v0_per_segment"].get(rk, 0.0)
        v1 = mech["v1_per_segment"].get(rk, 0.0)
        d = mech["delta_per_segment_v1_minus_v0"].get(rk, 0.0)
        marker = " ⚠" if d > 0 else ""
        out.append(f"| {rk} | {v0:.3f} | {v1:.3f} | {d:+.3f}{marker} |")
    out.append("")
    out.append("Negative Δ means v1 has fewer of that finding (improvement). "
               "Positive Δ marked ⚠ is a regression and trips gate 1.")
    out.append("")

    # Judge — pooled
    pool = summary["judgments"]["pooled"]
    overall = pool["overall"]
    n = pool["n"]
    decided = overall["v0"] + overall["v1"] + overall["tie"]
    out.append("## Judge — pooled")
    out.append("")
    out.append(f"- judgments total: **{n}**")
    out.append(f"- decoded: v0={overall['v0']}  v1={overall['v1']}  tie={overall['tie']}")
    out.append(f"- invalid: {overall['invalid']}  errors: {overall['error']}")
    if decided:
        wr = overall["v1"] / decided
        tr = overall["tie"] / decided
        out.append(f"- v1 win-rate: **{wr:.0%}**")
        out.append(f"- tie-rate: **{tr:.0%}**")
    a, b = pool.get("a_picked", 0), pool.get("b_picked", 0)
    if a + b:
        a_rate = a / (a + b)
        out.append(
            f"- position bias |P(A) − 0.5|: **{abs(a_rate - 0.5):.0%}** "
            f"(A picked {a}, B picked {b})"
        )
    out.append("")

    # Judge — per rubric
    rubric = pool.get("rubric") or {}
    if rubric:
        out.append("## Judge — per rubric")
        out.append("")
        out.append("| rubric | v0 | v1 | equal | invalid |")
        out.append("|---|---:|---:|---:|---:|")
        for rk in sorted(rubric):
            slot = rubric[rk]
            arrow = ""
            if slot.get("v1", 0) > slot.get("v0", 0):
                arrow = " ↑"
            elif slot.get("v0", 0) > slot.get("v1", 0):
                arrow = " ↓"
            out.append(
                f"| {rk}{arrow} | {slot.get('v0', 0)} | {slot.get('v1', 0)} "
                f"| {slot.get('equal', 0)} | {slot.get('invalid', 0)} |"
            )
        out.append("")

    # Thresholds
    th = summary["thresholds"]
    out.append("## Pre-registered thresholds")
    out.append("")
    out.append(f"- gate 1: mechanical regressions = 0")
    out.append(f"- gate 2: v1 win-rate ≥ {th['win_rate']:.0%}, "
               f"tie-rate < {th['tie_rate_max']:.0%}")
    out.append(f"- gate 3: v1 wins ≥ {th['rubric_wins_min']}/6 rubrics, "
               "no losses")
    out.append(f"- gate 4: |P(A) − 0.5| < {th['position_bias_max']:.0%}")
    out.append(f"- gate 5: invalid+error rate < {th['invalid_rate_max']:.0%}")
    out.append("")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate A/B mechanical + judge artifacts into a "
            "summary.json and a markdown report under <base_dir>."
        ),
    )
    parser.add_argument(
        "base_dir", type=Path,
        help="Base A/B dir (e.g. 04_translation_work/ab/p0039).",
    )
    parser.add_argument(
        "--page", required=True,
        help="Page key for the report title and filename (e.g. p0039).",
    )
    parser.add_argument(
        "--judgments-glob", default="judgments/*.jsonl",
        help="Glob for judgment files relative to base_dir.",
    )
    parser.add_argument(
        "--summary-out", type=Path, default=None,
        help="Override summary.json path.",
    )
    parser.add_argument(
        "--report-out", type=Path, default=None,
        help="Override <page>_report.md path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base = args.base_dir
    if not base.is_dir():
        print(f"ab_report: base dir not found: {base}", file=sys.stderr)
        return 2

    runs = discover_runs(base)
    if not runs:
        print(
            f"ab_report: no runs found under {base}/v0 or {base}/v1",
            file=sys.stderr,
        )
        return 2

    judgment_paths = discover_judgments(base, glob=args.judgments_glob)
    batches = [load_judgments(p) for p in judgment_paths]

    summary = build_summary(base_dir=base, runs=runs, batches=batches)

    summary_out = args.summary_out or (base / "summary.json")
    report_out = args.report_out or (base / f"{args.page}_report.md")
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_out.write_text(render_markdown(summary, page=args.page), encoding="utf-8")

    verdict = summary["verdict"]
    print(
        f"ab_report: {args.page} verdict={verdict['label']}  "
        f"runs={len(runs)}  judgments={len(judgment_paths)}  "
        f"-> {summary_out}, {report_out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "JudgmentBatch",
    "RunArtifact",
    "Verdict",
    "build_summary",
    "discover_judgments",
    "discover_runs",
    "evaluate_verdict",
    "load_judgments",
    "normalize_rule_counts",
    "pool_judgments",
    "pool_rule_counts",
    "render_markdown",
    "score_runs_mechanical",
    "THRESHOLD_INVALID_RATE_MAX",
    "THRESHOLD_POSITION_BIAS_MAX",
    "THRESHOLD_RUBRIC_WINS_MIN",
    "THRESHOLD_TIE_RATE_MAX",
    "THRESHOLD_WIN_RATE",
]
