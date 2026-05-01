"""Tests for the translate_segments runner.

These tests cover extraction gating, idempotent artifact writes, and a
dry-run smoke test against a static fixture committed under
``tests/fixtures/``. The fixture mirrors the structural invariants of
real Phase 3b annotation files (locked + draft body lines, a footnote
linked to a locked body line) without depending on live reviewer
state, so the suite is portable across local and CI environments.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import translate_segments as ts
from translation_adapters import (
    AnthropicTranslationAdapter,
    CommandResult,
)
from provider_config import default_config


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
P0036 = FIXTURE_DIR / "page_p0036_test.json"


# ---------------------------------------------------------------------------
# Extraction gating
# ---------------------------------------------------------------------------


def test_extract_units_includes_locked_body_only(tmp_path):
    payload = ts.load_phase3b_page(P0036)
    body, footnotes = ts.extract_units(payload)
    assert all(line["review_status"] == "locked" for line in body)
    assert len(body) > 0
    # The fixture's only footnote is anchored to a locked body line and
    # should be included regardless of its own (draft) review status.
    assert len(footnotes) == 1
    assert footnotes[0]["footnote_id"] == "p0036_fn_001"


def test_extract_units_drops_footnotes_when_body_anchor_unlocked():
    payload = ts.load_phase3b_page(P0036)
    # Mutate a copy: unlock the body line that the footnote anchors to.
    for line in payload["regions"]["body"]:
        if line["line_id"] == "p0036_body_l0001":
            line["review_status"] = "draft"
    body, footnotes = ts.extract_units(payload)
    assert all(b["line_id"] != "p0036_body_l0001" for b in body)
    assert footnotes == []


# ---------------------------------------------------------------------------
# translate_page with injected adapter
# ---------------------------------------------------------------------------


def _make_adapter_returning(translations: dict[str, dict]):
    def fake_runner(argv, stdin, timeout):
        return CommandResult(
            stdout=json.dumps({"translations": translations})
        )

    return AnthropicTranslationAdapter(
        default_config().get("anthropic"),
        command_runner=fake_runner,
    )


def test_translate_page_writes_segment_records_via_adapter():
    payload = ts.load_phase3b_page(P0036)
    body, footnotes = ts.extract_units(payload)
    canned = {}
    for line in body:
        canned[line["line_id"]] = {
            "english": f"EN:{line['line_id']}",
            "notes": "",
            "uncertain": False,
        }
    for fn in footnotes:
        canned[fn["footnote_id"]] = {
            "english": "EN_FN", "notes": "", "uncertain": False,
        }

    adapter = _make_adapter_returning(canned)
    existing: dict[str, dict] = {}

    page_log = ts.translate_page(
        payload,
        adapter=adapter,
        existing_segments=existing,
        lexicon_profile="auto",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-04-30T00:00:00Z",
    )

    assert page_log["status"] == "ok"
    # one segment per body line + one per linked footnote
    assert len(existing) == len(body) + len(footnotes)

    # Body segment shape
    seg_body = existing["seg_p0036_body_l0001"]
    assert seg_body["page_id"] == "p0036"
    assert seg_body["segment_type"] == "body"
    # latin_text carries the caret sentinel so the artifact is
    # self-describing (no need to cross-reference annotation files).
    assert seg_body["latin_text"] == (
        "Hinc Arnobius^y “ Tam velociter currit sermo ejus ut,"
    )
    # And the structured markers metadata cross-links to the footnote
    # segment so renderers don't have to parse the caret string.
    assert seg_body["markers"] == [
        {
            "marker_id": "y",
            "char_offset": 13,
            "footnote_segment_id": "seg_p0036_fn_001",
        }
    ]
    assert seg_body["translation_status"] == "machine_draft"
    assert len(seg_body["translation_history"]) == 1
    assert seg_body["translation_history"][0]["english"] == "EN:p0036_body_l0001"
    assert seg_body["translation_history"][0]["lexicon_profile"] == "auto"

    # A body line without markers gets an empty markers list and no caret.
    seg_l2 = existing["seg_p0036_body_l0002"]
    assert seg_l2["markers"] == []
    assert "^" not in seg_l2["latin_text"]

    # Footnote segment shape
    seg_fn = existing["seg_p0036_fn_001"]
    assert seg_fn["segment_type"] == "footnote"
    assert seg_fn["body_segment_id"] == "seg_p0036_body_l0001"
    assert seg_fn["marker_id"] == "y"
    assert seg_fn["markers"] == []


def test_translate_page_is_idempotent_unless_force():
    payload = ts.load_phase3b_page(P0036)
    body, footnotes = ts.extract_units(payload)
    canned = {
        line["line_id"]: {"english": "ok", "notes": "", "uncertain": False}
        for line in body
    }
    canned.update({
        fn["footnote_id"]: {"english": "ok", "notes": "", "uncertain": False}
        for fn in footnotes
    })
    adapter = _make_adapter_returning(canned)
    existing: dict[str, dict] = {}

    # First run: should translate everything.
    log1 = ts.translate_page(
        payload, adapter=adapter, existing_segments=existing,
        lexicon_profile="auto", extra_context=None,
        force=False, dry_run=False, timestamp="2026-04-30T00:00:00Z",
    )
    assert log1["status"] == "ok"
    first_count = len(existing)

    # Second run without force: nothing new translated, no new history.
    log2 = ts.translate_page(
        payload, adapter=adapter, existing_segments=existing,
        lexicon_profile="auto", extra_context=None,
        force=False, dry_run=False, timestamp="2026-04-30T00:00:00Z",
    )
    assert log2["status"] == "skipped_all_translated"
    assert len(existing) == first_count
    for seg in existing.values():
        assert len(seg["translation_history"]) == 1

    # Third run with force: appends version 2 to every history.
    log3 = ts.translate_page(
        payload, adapter=adapter, existing_segments=existing,
        lexicon_profile="auto", extra_context=None,
        force=True, dry_run=False, timestamp="2026-04-30T00:00:00Z",
    )
    assert log3["status"] == "ok"
    for seg in existing.values():
        history = seg["translation_history"]
        assert len(history) == 2
        assert history[-1]["version"] == 2


def test_translate_page_dry_run_does_not_call_adapter():
    payload = ts.load_phase3b_page(P0036)

    # Adapter that explodes if used.
    def fake_runner(argv, stdin, timeout):
        raise AssertionError("dry-run must not invoke the runner")

    adapter = AnthropicTranslationAdapter(
        default_config().get("anthropic"), command_runner=fake_runner
    )
    page_log = ts.translate_page(
        payload, adapter=adapter, existing_segments={},
        lexicon_profile="auto", extra_context=None,
        force=False, dry_run=True, timestamp="2026-04-30T00:00:00Z",
    )
    assert page_log["status"] == "dry_run"
    assert page_log["prompt_chars"] > 0
    # Lexicon Latin section should appear; no Greek in p0036 body→ omitted.
    assert "Forcellini" in page_log["prompt"]
    # Footnote marker 'y' must be injected at char_offset 13 of body line 1.
    assert "Hinc Arnobius^y" in page_log["prompt"]


# ---------------------------------------------------------------------------
# Round-trip artifact writes
# ---------------------------------------------------------------------------


def test_load_existing_segments_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, "ARTIFACTS_DIR", tmp_path)
    segments = {
        "seg_a": {"segment_id": "seg_a", "page_id": "p0001", "translation_history": []},
        "seg_b": {"segment_id": "seg_b", "page_id": "p0001", "translation_history": []},
    }
    ts.write_segments("part1", segments)
    loaded = ts.load_existing_segments("part1")
    assert loaded == segments


# ---------------------------------------------------------------------------
# Metadata-only backfill path (no Claude call)
# ---------------------------------------------------------------------------


def test_metadata_only_refreshes_latin_text_and_markers_without_adapter():
    """An older segment record (no caret, no markers[]) should be
    upgraded by a metadata-only run without invoking the adapter or
    appending a new translation_history entry."""
    payload = ts.load_phase3b_page(P0036)

    # Pre-populate "old" records as the v1 runner would have written them:
    # plain latin_text, no markers[], one history entry.
    existing = {
        "seg_p0036_body_l0001": {
            "segment_id": "seg_p0036_body_l0001",
            "page_id": "p0036",
            "segment_type": "body",
            "latin_text": "Hinc Arnobius “ Tam velociter currit sermo ejus ut,",
            "translation_history": [
                {"version": 1, "stage": "machine_draft", "english": "old"}
            ],
            "final_english": "",
            "translation_status": "machine_draft",
        },
        "seg_p0036_fn_001": {
            "segment_id": "seg_p0036_fn_001",
            "page_id": "p0036",
            "segment_type": "footnote",
            "latin_text": "in Psalm. 147.",
            "translation_history": [
                {"version": 1, "stage": "machine_draft", "english": "old fn"}
            ],
            "final_english": "",
            "translation_status": "machine_draft",
        },
    }

    page_log = ts.translate_page(
        payload,
        adapter=None,  # metadata-only path must not need an adapter
        existing_segments=existing,
        lexicon_profile="auto",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T00:00:00Z",
        metadata_only=True,
    )

    assert page_log["status"] == "metadata_refreshed"
    assert "seg_p0036_body_l0001" in page_log["refreshed"]

    body = existing["seg_p0036_body_l0001"]
    assert body["latin_text"] == (
        "Hinc Arnobius^y “ Tam velociter currit sermo ejus ut,"
    )
    assert body["markers"] == [
        {
            "marker_id": "y",
            "char_offset": 13,
            "footnote_segment_id": "seg_p0036_fn_001",
        }
    ]
    # History must NOT be appended on a metadata-only refresh.
    assert len(body["translation_history"]) == 1
    assert body["translation_history"][0]["english"] == "old"

    # Footnote backlinks are added/refreshed too.
    fn = existing["seg_p0036_fn_001"]
    assert fn["body_segment_id"] == "seg_p0036_body_l0001"
    assert fn["marker_id"] == "y"
    assert fn["markers"] == []
    assert len(fn["translation_history"]) == 1


def test_metadata_only_skips_segments_not_already_in_artifact():
    """A metadata-only run must not create new segments; it only
    refreshes derived fields on segments that already exist."""
    payload = ts.load_phase3b_page(P0036)
    existing: dict = {}

    page_log = ts.translate_page(
        payload,
        adapter=None,
        existing_segments=existing,
        lexicon_profile="auto",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T00:00:00Z",
        metadata_only=True,
    )

    assert page_log["status"] == "metadata_refreshed"
    assert page_log["refreshed"] == []
    assert existing == {}
