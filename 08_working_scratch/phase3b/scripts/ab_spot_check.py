"""Phase 5 — A/B spot-check picker.

Selects a small set of segments from the pooled A/B judgments for
human review and renders them as a markdown form. The form lets a
classicist sanity-check the LLM judge's verdicts before any merge or
prompt-revision decision.

Selection
---------
Two buckets, both sampled from the segments common to all judgment
files under ``<base>/judgments/run*.jsonl``:

* **high-swing**: largest absolute net rubric advantage (one side won
  the rubrics decisively across the 3 pairings). Ties broken by
  segment_id. Up to ``--n-swing`` (default 5).
* **tied**: pooled decoded_winner counts equal between v0 and v1
  across the 3 pairings, randomly sampled with a fixed seed. Up to
  ``--n-tied`` (default 5).

Output
------
A single markdown file (default ``<base>/spot_check.md``) with one
section per pick. Each pick shows the Latin source, the v0 and v1
candidates from every pairing, the judge's decoded rubric and reason,
and an empty reviewer checkbox.

CLI
---
::

    python ab_spot_check.py 04_translation_work/ab/p0039 \\
        [--page p0039] \\
        [--output spot_check.md] \\
        [--n-swing 5] [--n-tied 5] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


RUBRICS = ("fluency", "accuracy", "proper_nouns", "titles", "register")


GREEK_RULE_PREAMBLE = """\
**Reviewer rule — embedded Greek (read before scoring):**

Ussher routinely quotes a Greek source and then paraphrases it into
Latin in the same or adjacent clause. When that pattern is present,
the *correct* editorial behavior is to **leave the Greek
untranslated** and render only the Latin into English — the Latin
paraphrase already serves as Ussher's gloss, and double-translating
produces redundant English.

Score with this rule in mind:

- Greek + adjacent Latin paraphrase → leaving the Greek verbatim is
  CORRECT. Do not mark a candidate down for omitting an English
  gloss of such Greek.
- Greek standing alone (no Latin paraphrase nearby; the Greek
  carries new substantive content) → it SHOULD be rendered into
  English (or English-glossed in brackets).
- Signals that Ussher is paraphrasing the Greek: quotation marks
  around or just after the Greek; a Latin clause that visibly
  echoes the Greek; connectives like *id est*, *hoc est*, *sive*,
  *inquit* near the Greek.

Note: the LLM judge that produced the per-pairing winners shown
below was given this rule, but its application is imperfect.
Override the judge whenever your reading of the Latin source
disagrees.
"""


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class JudgmentRow:
    """Subset of an ab_judge.Judgment record needed for spot-check."""

    pair_name: str           # e.g. "run01"
    segment_id: str
    swapped: bool
    a_text: str
    b_text: str
    latin: str
    decoded_winner: str      # "v0" | "v1" | "equal" | ""
    decoded_rubric: dict
    reason: str
    error: str = ""

    @property
    def v0_text(self) -> str:
        return self.b_text if self.swapped else self.a_text

    @property
    def v1_text(self) -> str:
        return self.a_text if self.swapped else self.b_text


@dataclass
class SegmentPool:
    segment_id: str
    latin: str = ""
    pairings: list[JudgmentRow] = field(default_factory=list)

    def winners(self) -> list[str]:
        return [p.decoded_winner for p in self.pairings]

    def n_v1(self) -> int:
        return sum(1 for w in self.winners() if w == "v1")

    def n_v0(self) -> int:
        return sum(1 for w in self.winners() if w == "v0")

    def n_tie(self) -> int:
        return sum(1 for w in self.winners() if w == "equal")

    def rubric_swing(self) -> int:
        """Net rubric advantage for v1 across all pairings.

        Each rubric in each pairing contributes +1 (v1 won), -1 (v0 won),
        or 0 (equal/missing). Larger positive => v1 favored, larger
        negative => v0 favored.
        """
        total = 0
        for p in self.pairings:
            for rubric in RUBRICS:
                val = p.decoded_rubric.get(rubric, "")
                if val == "v1":
                    total += 1
                elif val == "v0":
                    total -= 1
        return total


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_judgment_rows(judgments_dir: Path, *, glob: str = "run*.jsonl") -> list[JudgmentRow]:
    """Read every judgment file matching ``glob`` under ``judgments_dir``.

    The file stem is used as the pair name (``run01.jsonl`` -> ``run01``).
    """
    rows: list[JudgmentRow] = []
    for path in sorted(judgments_dir.glob(glob)):
        pair = path.stem
        with path.open(encoding="utf-8") as h:
            for line in h:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rows.append(
                    JudgmentRow(
                        pair_name=pair,
                        segment_id=str(rec.get("segment_id", "")),
                        swapped=bool(rec.get("swapped", False)),
                        a_text=str(rec.get("a_text", "")),
                        b_text=str(rec.get("b_text", "")),
                        latin=str(rec.get("latin", "")),
                        decoded_winner=str(rec.get("decoded_winner", "")),
                        decoded_rubric=dict(rec.get("decoded_rubric", {})),
                        reason=str(rec.get("reason", "")),
                        error=str(rec.get("error", "")),
                    )
                )
    return rows


def pool_by_segment(rows: Iterable[JudgmentRow]) -> dict[str, SegmentPool]:
    pools: dict[str, SegmentPool] = {}
    for row in rows:
        pool = pools.setdefault(row.segment_id, SegmentPool(segment_id=row.segment_id))
        if not pool.latin and row.latin:
            pool.latin = row.latin
        pool.pairings.append(row)
    for pool in pools.values():
        pool.pairings.sort(key=lambda p: p.pair_name)
    return pools


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def pick_high_swing(pools: dict[str, SegmentPool], n: int) -> list[SegmentPool]:
    """Top-``n`` segments by |rubric_swing|, tie-break by segment_id."""
    candidates = [p for p in pools.values() if p.pairings]
    candidates.sort(key=lambda p: (-abs(p.rubric_swing()), p.segment_id))
    return candidates[:n]


def pick_tied(
    pools: dict[str, SegmentPool], n: int, *, seed: int, exclude: set[str]
) -> list[SegmentPool]:
    """Random sample of segments where pooled v0_wins == v1_wins.

    ``exclude`` removes segments already chosen for the swing bucket so
    a single segment never appears twice. Sampling is deterministic for
    a given seed.
    """
    candidates = [
        p
        for p in pools.values()
        if p.segment_id not in exclude and p.pairings and p.n_v0() == p.n_v1()
    ]
    candidates.sort(key=lambda p: p.segment_id)  # deterministic order
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:n]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fmt_rubric(rubric: dict) -> str:
    parts = []
    for r in RUBRICS:
        v = rubric.get(r, "—")
        parts.append(f"{r}={v}")
    return " ".join(parts)


def _fmt_pool_summary(pool: SegmentPool) -> str:
    return (
        f"v1 wins={pool.n_v1()}  v0 wins={pool.n_v0()}  "
        f"ties={pool.n_tie()}  rubric swing(v1)={pool.rubric_swing():+d}"
    )


def _render_pick(idx: int, pool: SegmentPool) -> list[str]:
    out: list[str] = []
    out.append(f"### {idx}. `{pool.segment_id}`")
    out.append("")
    out.append(f"_{_fmt_pool_summary(pool)}_")
    out.append("")
    out.append("**Latin source:**")
    out.append("")
    out.append("> " + (pool.latin or "_(missing)_"))
    out.append("")
    for p in pool.pairings:
        out.append(f"#### Pairing `{p.pair_name}`")
        out.append("")
        out.append(f"- **v0:** {p.v0_text}")
        out.append(f"- **v1:** {p.v1_text}")
        winner = p.decoded_winner or "—"
        out.append(f"- **Judge winner:** `{winner}`  (swapped={p.swapped})")
        out.append(f"- **Rubric:** {_fmt_rubric(p.decoded_rubric)}")
        if p.error:
            out.append(f"- **Judge error:** {p.error}")
        if p.reason:
            out.append("- **Reason:**")
            out.append("")
            out.append("  > " + p.reason.replace("\n", "\n  > "))
        out.append("")
    out.append("**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad")
    out.append("")
    out.append("**Reviewer notes:**")
    out.append("")
    out.append("> ")
    out.append("")
    out.append("---")
    out.append("")
    return out


def render_markdown(
    page: str,
    swing: list[SegmentPool],
    tied: list[SegmentPool],
    *,
    seed: int,
    n_segments_total: int,
) -> str:
    lines: list[str] = []
    lines.append(f"# A/B spot-check — {page}")
    lines.append("")
    lines.append(
        f"Sampled from {n_segments_total} pooled segments across the judgment files."
    )
    lines.append("")
    lines.append("Buckets:")
    lines.append(f"- **{len(swing)} high-swing segments** (largest |rubric swing|)")
    lines.append(
        f"- **{len(tied)} tied segments** (pooled v0 wins == v1 wins; seed={seed})"
    )
    lines.append("")
    lines.append("For each pick, mark a verdict and add a one-line note. The judge's")
    lines.append("decoded winner is shown for reference, not as a constraint.")
    lines.append("")
    lines.append(GREEK_RULE_PREAMBLE)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## High-swing picks")
    lines.append("")
    if not swing:
        lines.append("_(none)_")
        lines.append("")
    for i, pool in enumerate(swing, start=1):
        lines.extend(_render_pick(i, pool))
    lines.append("## Tied picks")
    lines.append("")
    if not tied:
        lines.append("_(none)_")
        lines.append("")
    for i, pool in enumerate(tied, start=1):
        lines.extend(_render_pick(i, pool))
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build(
    base_dir: Path,
    *,
    page: str,
    n_swing: int,
    n_tied: int,
    seed: int,
    glob: str = "run*.jsonl",
) -> tuple[str, list[SegmentPool], list[SegmentPool]]:
    judgments_dir = base_dir / "judgments"
    rows = load_judgment_rows(judgments_dir, glob=glob)
    pools = pool_by_segment(rows)
    swing = pick_high_swing(pools, n_swing)
    exclude = {p.segment_id for p in swing}
    tied = pick_tied(pools, n_tied, seed=seed, exclude=exclude)
    md = render_markdown(
        page,
        swing,
        tied,
        seed=seed,
        n_segments_total=len(pools),
    )
    return md, swing, tied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_dir", type=Path, help="A/B page dir, e.g. 04_translation_work/ab/p0039")
    parser.add_argument("--page", default=None, help="Page label (default: base_dir name)")
    parser.add_argument("--output", type=Path, default=None, help="Output markdown path (default: <base>/spot_check.md)")
    parser.add_argument("--n-swing", type=int, default=5)
    parser.add_argument("--n-tied", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--judgments-glob", default="run*.jsonl")
    args = parser.parse_args(argv)

    base = args.base_dir
    if not (base / "judgments").is_dir():
        parser.error(f"no judgments/ dir under {base}")

    page = args.page or base.name
    output = args.output or (base / "spot_check.md")

    md, swing, tied = build(
        base,
        page=page,
        n_swing=args.n_swing,
        n_tied=args.n_tied,
        seed=args.seed,
        glob=args.judgments_glob,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    print(
        f"ab_spot_check: page={page} swing={len(swing)} tied={len(tied)} "
        f"-> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
