"""Tests for the controlled-glossary validator (Phase A symbolic layer).

Focus: the scripture-substitution guard added after the ch1 classicist
review. Ussher quotes the Vulgate and argues FROM its wording; a model that
recognizes a famous verse and recites a remembered English Bible silently
replaces his evidence. That failure is near-invisible in human review
because the received English reads beautifully — so it must be caught in
code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import glossary_validate as gv


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seg(seg_id: str, latin: str, english: str, page_id: str = "p0032",
         seq: int = 1) -> dict:
    return {
        "segment_id": seg_id,
        "page_id": page_id,
        "segment_type": "body",
        "seq": seq,
        "latin_text": latin,
        "translation_history": [{"version": 1, "english": english}],
    }


def _write(tmp_path: Path, name: str, records: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def _glossary(tmp_path: Path, entries: list[dict]) -> list[dict]:
    path = _write(tmp_path, "gloss.jsonl", entries)
    return gv.load_glossary(path)


_EPH = {
    "term": "Eph 2:12",
    "category": "scripture",
    "latin_pattern": r"alienos\s+a\s+republica\s+Israelis",
    "approved": [],
    "banned": ["aliens from the commonwealth of Israel"],
    "note": "KJV recitation.",
}


def _flags(tmp_path, segments, entries):
    seg_path = _write(tmp_path, "segs.jsonl", segments)
    return gv.validate(
        seg_path, _glossary(tmp_path, entries),
        start_page=None, end_page=None,
    )


# ---------------------------------------------------------------------------
# Scripture substitution
# ---------------------------------------------------------------------------


def test_kjv_recitation_raises_scripture_substitution(tmp_path):
    segs = [_seg(
        "seg_p0032_s0001",
        "id est, fuisse absque Christo, alienos a republica Israelis,",
        'they were "without Christ, aliens from the commonwealth of Israel,"',
    )]
    flags = _flags(tmp_path, segs, [_EPH])
    scripture = [f for f in flags if f["flag"] == "SCRIPTURE_SUBSTITUTION"]
    assert len(scripture) == 1
    assert scripture[0]["found"] == "aliens from the commonwealth of Israel"
    assert scripture[0]["severity"] == "high"


def test_translating_the_latin_is_not_flagged(tmp_path):
    """A faithful rendering of Ussher's Latin must pass cleanly."""
    segs = [_seg(
        "seg_p0032_s0001",
        "id est, fuisse absque Christo, alienos a republica Israelis,",
        'they were "without Christ, foreign to the commonwealth of Israel,"',
    )]
    flags = _flags(tmp_path, segs, [_EPH])
    assert flags == []


def test_caret_sentinel_inside_a_verse_cannot_defeat_the_check(tmp_path):
    """Footnote carets are pipeline metadata, not text.

    Psalm 19:6 anchors a footnote on its first word ('A^w summo caelo'), and
    the English carries carets too. Neither may hide a KJV substitution --
    and the KJV here INVERTS the Latin ('a summo caelo' = 'from the highest
    heaven'; KJV reads 'from the end of the heaven').
    """
    entry = {
        "term": "Ps 19:6",
        "category": "scripture",
        "latin_pattern": r"a\s+summo\s+c(?:ae|æ)lo\s+egressio",
        "approved": [],
        "banned": ["from the end of heaven"],
        "note": "KJV inverts the Latin.",
    }
    segs = [_seg(
        "seg_p0040_s0001",
        "de quo legimus; A^w summo cælo egressio ejus,",
        "of whom we read: 'His going forth is from the end of heaven,'^w",
        page_id="p0040",
    )]
    flags = _flags(tmp_path, segs, [entry])
    assert [f["flag"] for f in flags] == ["SCRIPTURE_SUBSTITUTION"]


def test_banned_only_entry_never_raises_missing_approved(tmp_path):
    """Scripture entries have no single required rendering -- only forbidden
    ones. An empty 'approved' list must not trigger MISSING_APPROVED on every
    occurrence of the verse."""
    segs = [_seg(
        "seg_p0032_s0001",
        "id est, fuisse absque Christo, alienos a republica Israelis,",
        "an entirely unobjectionable rendering of the verse",
    )]
    flags = _flags(tmp_path, segs, [_EPH])
    assert not [f for f in flags if f["flag"] == "MISSING_APPROVED"]


def test_ordinary_entry_still_raises_missing_approved(tmp_path):
    """The banned-only behaviour must not disable the existing check for
    entries that DO declare approved renderings."""
    entry = {
        "term": "ecclesia",
        "latin_pattern": r"\becclesia\b",
        "approved": ["church"],
        "banned": [],
        "note": "",
    }
    segs = [_seg("seg_p0032_s0001", "ecclesia Britannica", "a wholly unrelated gloss")]
    flags = _flags(tmp_path, segs, [entry])
    assert [f["flag"] for f in flags] == ["MISSING_APPROVED"]


# ---------------------------------------------------------------------------
# Archaism (catches recitation of verses NOT yet in the glossary)
# ---------------------------------------------------------------------------


def test_archaic_diction_is_flagged_without_a_glossary_entry(tmp_path):
    segs = [_seg(
        "seg_p0035_s0001",
        "et in fines orbis terrae verba eorum",
        "and their words unto the ends of the world",
        page_id="p0035",
    )]
    flags = _flags(tmp_path, segs, [])  # no glossary entries at all
    archaism = [f for f in flags if f["flag"] == "ARCHAISM"]
    assert len(archaism) == 1
    assert archaism[0]["found"] == ["unto"]


def test_modern_register_is_not_flagged_as_archaic(tmp_path):
    segs = [_seg(
        "seg_p0035_s0001",
        "et in fines orbis terrae verba eorum",
        "and their words to the ends of the world",
        page_id="p0035",
    )]
    assert _flags(tmp_path, segs, []) == []


@pytest.mark.parametrize("archaism", ["thou", "hath", "saith", "shalt", "whosoever"])
def test_archaism_vocabulary_is_detected(tmp_path, archaism):
    segs = [_seg("seg_p0032_s0001", "verbum Dei", f"the word which {archaism} spoken")]
    flags = _flags(tmp_path, segs, [])
    assert [f["flag"] for f in flags] == ["ARCHAISM"]


# ---------------------------------------------------------------------------
# Summary completeness
# ---------------------------------------------------------------------------


def test_every_flag_kind_has_a_severity(tmp_path):
    """The CLI summary iterates _SEVERITY; a kind missing from it would be
    written to the artifact but silently omitted from the report (which is
    exactly what happened to SCRIPTURE_SUBSTITUTION when it was added)."""
    for kind in ("BANNED", "SCRIPTURE_SUBSTITUTION", "ARCHAISM",
                 "MISSING_APPROVED", "DRIFT"):
        assert kind in gv._SEVERITY
