"""Tests for the mechanical A/B scoring rules.

Each test exercises one rule with a minimal, hand-crafted JSONL line so
the assertions stay readable and the regression mode is obvious. We
also run a tiny end-to-end scoring of a multi-line synthetic JSONL to
confirm aggregate counts match the per-rule expectations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ab_rules


def _seg(seg_id: str, english: str, *, latin: str = "") -> dict:
    """Build a minimal segment record with a single history entry."""
    return {
        "segment_id": seg_id,
        "page_id": "p9999",
        "segment_type": "body",
        "latin_text": latin,
        "markers": [],
        "translation_history": [
            {
                "version": 1,
                "stage": "machine_draft",
                "english": english,
                "notes": "",
                "uncertain": False,
                "model": "claude-opus-4-7",
                "lexicon_profile": "auto",
            }
        ],
        "final_english": "",
        "translation_status": "machine_draft",
    }


# ---------------------------------------------------------------------------
# Per-rule
# ---------------------------------------------------------------------------


def test_archaism_rule_flags_kjvisms():
    record = _seg("s1", "He hath spoken; verily I say unto thee, behold,")
    findings = ab_rules.score_record(record)
    rules = [f.rule for f in findings]
    assert rules.count("archaism") >= 3  # hath, verily, thee, behold,


def test_archaism_rule_skips_modern_prose():
    record = _seg("s2", "He spoke clearly: I tell you plainly, look here.")
    findings = ab_rules.score_record(record)
    assert all(f.rule != "archaism" for f in findings)


def test_proper_noun_rule_flags_unanglicized_form():
    record = _seg("s3", "Boadicia led the rebellion.")
    findings = ab_rules.score_record(record)
    pn = [f for f in findings if f.rule == "proper_noun"]
    assert len(pn) == 1
    assert "Boudica" in pn[0].note


def test_proper_noun_rule_accepts_explicit_gloss():
    """When both forms are present, treat it as a deliberate gloss."""
    record = _seg("s4", "Boudica (Boadicia) led the rebellion.")
    findings = ab_rules.score_record(record)
    assert all(f.rule != "proper_noun" for f in findings)


def test_title_rule_flags_bare_treatise_title():
    record = _seg("s5", "as he writes in Adversus Haereses.")
    findings = ab_rules.score_record(record)
    titles = [f for f in findings if f.rule == "title_unformatted"]
    assert len(titles) == 1


@pytest.mark.parametrize("formatted", [
    "as he writes in *Adversus Haereses*.",
    "as he writes in _Adversus Haereses_.",
    'as he writes in "Adversus Haereses".',
    "as he writes in 'Adversus Haereses'.",
])
def test_title_rule_accepts_formatted_titles(formatted):
    record = _seg("s6", formatted)
    findings = ab_rules.score_record(record)
    assert all(f.rule != "title_unformatted" for f in findings)


def test_lexicon_leak_rule_fires():
    record = _seg("s7", "as Forcellini notes in his entry on imperium.")
    findings = ab_rules.score_record(record)
    assert any(f.rule == "lexicon_leak" for f in findings)


def test_code_fence_rule_fires():
    record = _seg("s8", "```\nThe text continues\n```")
    findings = ab_rules.score_record(record)
    assert any(f.rule == "code_fence" for f in findings)


def test_caret_in_english_rule_fires():
    record = _seg("s9", "the writings of Arnobius^y, who...")
    findings = ab_rules.score_record(record)
    assert any(f.rule == "caret_in_english" for f in findings)


def test_empty_english_rule_fires_on_blank():
    record = _seg("s10", "   ")
    findings = ab_rules.score_record(record)
    assert any(f.rule == "empty_english" for f in findings)


def test_empty_english_rule_uses_final_english_fallback():
    """If translation_history has no english but final_english does,
    the segment is not flagged as empty."""
    record = _seg("s11", "")
    record["final_english"] = "Polished prose."
    findings = ab_rules.score_record(record)
    assert all(f.rule != "empty_english" for f in findings)


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


def test_score_run_aggregates_counts(tmp_path: Path):
    records = [
        _seg("a1", "He hath spoken truly."),                # 1 archaism (hath)
        _seg("a2", "Boadicia revolted."),                   # 1 proper_noun
        _seg("a3", "in Adversus Haereses he argues..."),    # 1 title_unformatted
        _seg("a4", "as Forcellini notes."),                 # 1 lexicon_leak
        _seg("a5", "modern prose with no issues."),         # clean
    ]
    path = tmp_path / "run.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = ab_rules.score_run(path)
    assert summary.segments == 5
    by_rule = summary.by_rule()
    assert by_rule.get("archaism", 0) == 1
    assert by_rule.get("proper_noun", 0) == 1
    assert by_rule.get("title_unformatted", 0) == 1
    assert by_rule.get("lexicon_leak", 0) == 1
    # "clean" segment must not contribute findings.
    assert sum(by_rule.values()) == 4


def test_score_run_handles_malformed_jsonl(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    good = json.dumps(_seg("a1", "modern prose."))
    path.write_text(good + "\nnot json at all\n", encoding="utf-8")
    summary = ab_rules.score_run(path)
    # 1 well-formed record counted; the bad line lands as a
    # malformed_record finding rather than crashing the run.
    assert summary.segments == 1
    assert any(f.rule == "malformed_record" for f in summary.findings)


def test_to_dict_round_trip(tmp_path: Path):
    record = _seg("a1", "He hath spoken.")
    path = tmp_path / "one.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    summary = ab_rules.score_run(path)
    d = summary.to_dict()
    # Re-encode/decode to confirm JSON-cleanness.
    again = json.loads(json.dumps(d, ensure_ascii=False))
    assert again["segments"] == 1
    assert again["by_rule"].get("archaism") == 1
