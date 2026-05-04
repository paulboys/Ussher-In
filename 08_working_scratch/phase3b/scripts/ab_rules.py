"""Mechanical (regex-only) scoring for prompt-version A/B runs.

This module is the cheap, deterministic half of the A/B scorer for
``ab/prompt-v0-snapshot``. It reads one
``segments_with_translations.jsonl`` produced by the harness and reports
per-segment rule findings plus aggregate counts. No LLM call. No
network. No randomness. Same input -> same output.

Rule classes
------------
The classes below were chosen because they are exactly what the v1
prompt refinement targets: archaism elimination, proper-noun
Anglicization, treatise-title formatting, and protection of the
caret/footnote-marker contract. Each class produces:

* ``hits``: list of ``(segment_id, snippet, span)`` findings.
* ``count``: integer for the aggregate.

The scorer is intentionally tolerant: it flags rather than rules. The
final A/B verdict counts net hits between v0 and v1 runs of the same
page; a rule that fires on both versions equally is not evidence
either way.

CLI
---
::

    python ab_rules.py <segments_with_translations.jsonl> [--json]

When ``--json`` is set the output is a machine-readable dict suitable
for the aggregator in Phase 4. Otherwise a short human summary is
printed.

The aggregator (``ab_report.py``, Phase 4) imports ``score_run`` and
calls it on every per-run JSONL the harness produced.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


# ---------------------------------------------------------------------------
# Rule patterns
# ---------------------------------------------------------------------------

# Word-boundary archaism list. Targeted at KJV-isms and 19th-century
# stylistic affectations that the v1 prompt's "Modern English target"
# bullet was added to suppress. Case-insensitive. The list is
# deliberately narrow: high-precision tokens whose modern usage is
# essentially zero in scholarly prose.
ARCHAISM_TOKENS = (
    "vouchsafed",
    "thee",
    "thou",
    "thy",
    "thine",
    "verily",
    "whereunto",
    "whilst",
    "betwixt",
    "hath",
    "doth",
    "saith",
    "wherefore",
    "behold,",  # "behold" alone is fine in some idioms; "behold," is archaic
    "ye",
    "twixt",
    "ere ",
)
ARCHAISM_RE = re.compile(
    r"\b(" + "|".join(re.escape(tok.strip()) for tok in ARCHAISM_TOKENS) + r")\b",
    re.IGNORECASE,
)

# Proper-noun Anglicization. Each entry is (latin_or_unanglicized,
# preferred_modern). The check fires when the unanglicized form
# appears in the English without the modern form also appearing
# anywhere in the same English (i.e. it isn't a deliberate gloss like
# "Boudica (Boadicia)").
#
# Forms here are conservative: only well-attested proper nouns whose
# modern English spelling differs unambiguously. Disagreements
# (Caesarea vs. Cæsarea, etc.) belong in human review, not here.
PROPER_NOUN_PAIRS = (
    ("Boadicia", "Boudica"),
    ("Boadicea", "Boudica"),
    ("Caesariis", "Caesar"),
    ("Aethiopas", "Ethiopians"),
    ("Aethiopibus", "Ethiopians"),
    ("Antiocheni", "Antiochenes"),
    ("Theodoretus", "Theodoret"),
)

# Treatise / book title detection. The v1 prompt added a "Book and
# treatise titles" instruction directing italics/quotes; we flag
# titles that show up bare in the English. The list is short and
# corpus-specific: titles we can be sure are titles in this work.
TITLE_TOKENS = (
    "Adversus Haereses",
    "Adversus Iudaeos",
    "Adversus Judaeos",
    "Historia Ecclesiastica",
    "Britannicarum Ecclesiarum Antiquitates",
    "De Civitate Dei",
    "De Praescriptione Haereticorum",
    "De Trinitate",
)
# Heuristic: a title is "formatted" if it is wrapped in either italics
# (markdown ``*...*`` or ``_..._``) or quotes (double or single). Bare
# occurrences are flagged.
TITLE_FORMATTED_RE_TEMPLATES = (
    r"\*{title}\*",
    r"_{title}_",
    r'"{title}"',
    r"'{title}'",
    r"\u201c{title}\u201d",
)

# Lexicon-name leak. The prompt explicitly forbids quoting lexicon
# entries, but a stray "as Forcellini notes" or similar would be a
# regression. We flag any of these names appearing in the English.
LEXICON_NAMES = ("Forcellini", "Du Cange", "DuCange", "Lampe", "LSJ",
                 "Liddell-Scott", "Lewis & Short", "Sophocles")
LEXICON_NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in LEXICON_NAMES) + r")\b"
)

# Code-fence leak — translation pass should never wrap output in fences.
CODE_FENCE_RE = re.compile(r"```|~~~")

# Caret-marker integrity. A body line's Latin carries ``^X``
# sentinels; the literal-pass English is supposed to NOT echo them
# (placement is a separate pass). So we flag carets in the English
# only as a regression signal, not in the Latin.
CARET_IN_ENGLISH_RE = re.compile(r"\^[A-Za-z0-9]{1,2}")


# ---------------------------------------------------------------------------
# Findings + summary dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    rule: str
    segment_id: str
    snippet: str
    span: tuple[int, int]
    note: str = ""


@dataclass
class RunSummary:
    """Aggregate counts for one A/B run."""
    path: str
    segments: int = 0
    findings: list[Finding] = field(default_factory=list)

    def by_rule(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.rule] = out.get(f.rule, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "segments": self.segments,
            "by_rule": self.by_rule(),
            "findings": [
                {
                    "rule": f.rule,
                    "segment_id": f.segment_id,
                    "snippet": f.snippet,
                    "span": list(f.span),
                    "note": f.note,
                }
                for f in self.findings
            ],
        }


# ---------------------------------------------------------------------------
# Per-segment rule application
# ---------------------------------------------------------------------------


def _english_for(record: dict) -> str:
    """Return the most-recent machine-draft English for a segment.

    Falls back to ``final_english`` then empty. Polish-pass output
    lives in ``final_english``; the A/B harness scores literal-pass
    output, so we read translation_history first.
    """
    history = record.get("translation_history") or []
    if history:
        last = history[-1] or {}
        text = (last.get("english") or "").strip()
        if text:
            return text
    return (record.get("final_english") or "").strip()


def _check_archaisms(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    for m in ARCHAISM_RE.finditer(english):
        out.append(Finding(
            rule="archaism",
            segment_id=seg_id,
            snippet=_clip(english, m.start(), m.end()),
            span=(m.start(), m.end()),
            note=f"archaic token: {m.group(0)!r}",
        ))
    return out


def _check_proper_nouns(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    for unanglicized, modern in PROPER_NOUN_PAIRS:
        # Only flag when the unanglicized form appears AND the modern
        # form does NOT also appear (a deliberate gloss like
        # "Boudica (Boadicia)" is fine).
        if unanglicized in english and modern not in english:
            idx = english.index(unanglicized)
            out.append(Finding(
                rule="proper_noun",
                segment_id=seg_id,
                snippet=_clip(english, idx, idx + len(unanglicized)),
                span=(idx, idx + len(unanglicized)),
                note=f"prefer {modern!r} over {unanglicized!r}",
            ))
    return out


def _check_titles(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    for title in TITLE_TOKENS:
        if title not in english:
            continue
        # Skip if any formatted variant is present.
        formatted = any(
            re.search(tmpl.format(title=re.escape(title)), english)
            for tmpl in TITLE_FORMATTED_RE_TEMPLATES
        )
        if formatted:
            continue
        idx = english.index(title)
        out.append(Finding(
            rule="title_unformatted",
            segment_id=seg_id,
            snippet=_clip(english, idx, idx + len(title)),
            span=(idx, idx + len(title)),
            note=f"treatise title not italicized/quoted: {title!r}",
        ))
    return out


def _check_lexicon_leak(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    for m in LEXICON_NAME_RE.finditer(english):
        out.append(Finding(
            rule="lexicon_leak",
            segment_id=seg_id,
            snippet=_clip(english, m.start(), m.end()),
            span=(m.start(), m.end()),
            note=f"lexicon name leaked into output: {m.group(0)!r}",
        ))
    return out


def _check_code_fence(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    m = CODE_FENCE_RE.search(english)
    if m:
        out.append(Finding(
            rule="code_fence",
            segment_id=seg_id,
            snippet=_clip(english, m.start(), m.end()),
            span=(m.start(), m.end()),
            note="code fence in literal-pass output",
        ))
    return out


def _check_caret_in_english(seg_id: str, english: str) -> list[Finding]:
    out: list[Finding] = []
    for m in CARET_IN_ENGLISH_RE.finditer(english):
        out.append(Finding(
            rule="caret_in_english",
            segment_id=seg_id,
            snippet=_clip(english, m.start(), m.end()),
            span=(m.start(), m.end()),
            note=(
                "literal-pass English contains a ^X marker; placement "
                "is supposed to be a separate downstream pass"
            ),
        ))
    return out


def _check_empty(seg_id: str, english: str) -> list[Finding]:
    if english.strip():
        return []
    return [Finding(
        rule="empty_english",
        segment_id=seg_id,
        snippet="",
        span=(0, 0),
        note="no English produced for this segment",
    )]


_RULES: tuple = (
    _check_archaisms,
    _check_proper_nouns,
    _check_titles,
    _check_lexicon_leak,
    _check_code_fence,
    _check_caret_in_english,
    _check_empty,
)


def score_record(record: dict) -> list[Finding]:
    """Apply every mechanical rule to one segment record."""
    seg_id = str(record.get("segment_id") or "")
    english = _english_for(record)
    out: list[Finding] = []
    for rule in _RULES:
        out.extend(rule(seg_id, english))
    return out


def score_run(jsonl_path: Path | str) -> RunSummary:
    """Apply every rule to every record in *jsonl_path*."""
    path = Path(jsonl_path)
    summary = RunSummary(path=str(path))
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # Treat a corrupt line as a single empty-output finding
                # so the run still produces a comparable summary.
                summary.findings.append(Finding(
                    rule="malformed_record",
                    segment_id="",
                    snippet=line[:60],
                    span=(0, len(line)),
                    note="JSON decode failed",
                ))
                continue
            summary.segments += 1
            summary.findings.extend(score_record(record))
    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clip(text: str, start: int, end: int, *, radius: int = 24) -> str:
    """Return *text* around [start:end] with a small surrounding context.

    Replaces newlines with spaces so the snippet stays a single line in
    reports. Clipped to ``radius`` characters either side.
    """
    a = max(0, start - radius)
    b = min(len(text), end + radius)
    snippet = text[a:b].replace("\n", " ")
    prefix = "…" if a > 0 else ""
    suffix = "…" if b < len(text) else ""
    return prefix + snippet + suffix


def _format_human(summary: RunSummary) -> str:
    by_rule = summary.by_rule()
    lines = [
        f"ab_rules: {summary.path}",
        f"  segments scored: {summary.segments}",
        f"  total findings:  {len(summary.findings)}",
    ]
    if by_rule:
        lines.append("  by rule:")
        for rule in sorted(by_rule):
            lines.append(f"    {rule:<22} {by_rule[rule]:>3}")
    else:
        lines.append("  by rule: (none)")
    if summary.findings:
        lines.append("")
        lines.append("  first 10 findings:")
        for f in summary.findings[:10]:
            lines.append(
                f"    [{f.rule}] {f.segment_id}: {f.snippet} -- {f.note}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply mechanical (regex-only) A/B scoring rules to one "
            "segments_with_translations.jsonl artifact."
        ),
    )
    parser.add_argument("jsonl", type=Path, help="Path to the JSONL artifact.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a human summary.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.jsonl.exists():
        print(f"ab_rules: file not found: {args.jsonl}", file=sys.stderr)
        return 2
    summary = score_run(args.jsonl)
    if args.json:
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(_format_human(summary))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ARCHAISM_RE",
    "ARCHAISM_TOKENS",
    "CARET_IN_ENGLISH_RE",
    "CODE_FENCE_RE",
    "Finding",
    "LEXICON_NAMES",
    "LEXICON_NAME_RE",
    "PROPER_NOUN_PAIRS",
    "RunSummary",
    "TITLE_TOKENS",
    "score_record",
    "score_run",
]
