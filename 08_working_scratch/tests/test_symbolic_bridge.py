"""Tests for the symbolic -> repair-loop bridge.

The bridge turns a deterministic validator finding into a targeted
re-translation request. Its whole value depends on two contracts holding:

1. The score key it emits must be one propose_fix.needs_fix() actually
   triggers on. It emits the FULL rubric name ('content_fidelity'), not the
   'cf' abbreviation used in propose_fix's docstring/CLI. Getting this wrong
   selects ZERO units and silently disables the loop -- which is exactly what
   happened on the first run.
2. The Latin and prior English fed back must be the FULL text from the
   segments artifact, never the truncated excerpts carried on the flags.
"""

from __future__ import annotations

import json
from pathlib import Path

import propose_fix
import pytest

import symbolic_bridge as sb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_LONG_LATIN = "de quo legimus; A^w summo cælo egressio ejus, " + ("et cetera " * 40)
_LONG_ENGLISH = "of whom we read: 'His going forth is from the end of heaven' " + ("and so on " * 40)


def _segment() -> dict:
    return {
        "segment_id": "seg_p0040_body_l0008",
        "page_id": "p0040",
        "segment_type": "body",
        "latin_text": _LONG_LATIN,
        "translation_history": [{"version": 1, "english": _LONG_ENGLISH}],
    }


def _scripture_flag() -> dict:
    return {
        "segment_id": "seg_p0040_body_l0008",
        "page_id": "p0040",
        "term": "Ps 19:6 (a summo caelo egressio ejus)",
        "flag": "SCRIPTURE_SUBSTITUTION",
        "severity": "high",
        "found": "from the end of heaven",
        "expected": [],
        # The flag carries a TRUNCATED excerpt -- the bridge must not use it.
        "latin": "de quo legimus; A^w summo cælo egressio ejus, et cetera et…",
        "english": "of whom we read: 'His going forth is from the end of heaven'…",
        "note": 'KJV recitation that CONTRADICTS the Latin.',
    }


# ---------------------------------------------------------------------------
# Contract 1: the emitted score actually triggers propose_fix
# ---------------------------------------------------------------------------


def test_emitted_score_triggers_propose_fix():
    """The bridge is worthless if propose_fix does not select the unit."""
    _, scores = sb.bridge([_scripture_flag()], [_segment()], sb.DEFAULT_KINDS)
    assert len(scores) == 1
    assert propose_fix.needs_fix(scores[0]["scores"], 3) is True


def test_symbolic_rubric_key_is_a_real_trigger_rubric():
    """Pin the key against propose_fix's actual rubric list, so renaming a
    rubric there breaks this test rather than silently emptying the loop."""
    assert sb._SYMBOLIC_RUBRIC in propose_fix._TRIGGER_RUBRICS


# ---------------------------------------------------------------------------
# Contract 2: full source text is fed back, not the flag's excerpt
# ---------------------------------------------------------------------------


def test_bridge_feeds_full_latin_and_english_not_the_flag_excerpt():
    inputs, _ = sb.bridge([_scripture_flag()], [_segment()], sb.DEFAULT_KINDS)
    assert inputs[0]["latin_concat"] == _LONG_LATIN
    assert inputs[0]["english_concat"] == _LONG_ENGLISH
    # The truncation ellipsis from the flag excerpt must never reach the model.
    assert "…" not in inputs[0]["latin_concat"]
    assert "…" not in inputs[0]["english_concat"]


def test_unit_id_matches_segment_id_so_propose_fix_can_join():
    inputs, scores = sb.bridge([_scripture_flag()], [_segment()], sb.DEFAULT_KINDS)
    assert inputs[0]["unit_id"] == scores[0]["unit_id"] == "seg_p0040_body_l0008"


# ---------------------------------------------------------------------------
# Routing / filtering
# ---------------------------------------------------------------------------


def test_drift_and_missing_approved_are_not_routed_by_default():
    """DRIFT is corpus-wide and carries no segment; MISSING_APPROVED is
    frequently a legitimate synonym. Routing them by default floods the loop."""
    flags = [
        {"segment_id": "", "flag": "DRIFT", "term": "x", "found": {}, "note": ""},
        {"segment_id": "seg_p0040_body_l0008", "flag": "MISSING_APPROVED",
         "term": "y", "found": None, "expected": ["z"], "note": ""},
    ]
    inputs, scores = sb.bridge(flags, [_segment()], sb.DEFAULT_KINDS)
    assert inputs == [] and scores == []


def test_missing_approved_can_be_opted_in():
    flags = [{"segment_id": "seg_p0040_body_l0008", "flag": "MISSING_APPROVED",
              "term": "y", "found": None, "expected": ["z"], "note": ""}]
    inputs, _ = sb.bridge(flags, [_segment()], ("MISSING_APPROVED",))
    assert len(inputs) == 1


def test_multiple_flags_on_one_segment_become_one_repair_request():
    flags = [
        _scripture_flag(),
        {"segment_id": "seg_p0040_body_l0008", "flag": "ARCHAISM",
         "term": "(archaic register)", "found": ["unto"],
         "expected": ["modern English"], "note": ""},
    ]
    inputs, scores = sb.bridge(flags, [_segment()], sb.DEFAULT_KINDS)
    assert len(inputs) == 1  # one call, not two
    assert set(scores[0]["flags"]) == {"SCRIPTURE_SUBSTITUTION", "ARCHAISM"}
    assert "SCRIPTURE_SUBSTITUTION" in scores[0]["reason"]
    assert "ARCHAISM" in scores[0]["reason"]


def test_flag_for_unknown_segment_is_skipped_not_fabricated():
    flag = dict(_scripture_flag(), segment_id="seg_p9999_body_l0001")
    inputs, scores = sb.bridge([flag], [_segment()], sb.DEFAULT_KINDS)
    assert inputs == [] and scores == []


# ---------------------------------------------------------------------------
# The diagnostic itself
# ---------------------------------------------------------------------------


def test_scripture_diagnostic_names_the_offending_text_and_the_remedy():
    reason = sb.build_reason([_scripture_flag()])
    assert "from the end of heaven" in reason      # what it found
    assert "VULGATE" in reason                      # what to translate instead
    assert "CONTRADICTS the Latin" in reason        # the curated note survives
    # The model must not rewrite the whole unit.
    assert "Correct ONLY these issues" in reason


def test_archaism_diagnostic_lists_the_archaic_words():
    flag = {"segment_id": "s", "flag": "ARCHAISM", "term": "(archaic register)",
            "found": ["thou", "unto"], "expected": ["modern English"], "note": ""}
    assert "thou, unto" in sb.describe(flag)
