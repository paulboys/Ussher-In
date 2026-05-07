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

pytest.importorskip(
    "translation_prompts_v0",
    reason="Prompt modules were removed from this branch.",
)
pytest.importorskip(
    "translation_prompts_v2",
    reason="Prompt modules were removed from this branch.",
)
pytest.importorskip(
    "translation_prompts_v3",
    reason="Prompt modules were removed from this branch.",
)

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
        prompt = argv[2] if len(argv) > 2 else ""
        # Detect a marker-placement (second-pass) prompt by its
        # signature footer and synthesize a deterministic placed
        # response: insert ^<marker_id> immediately before the first
        # period in the English (or at the end if no period).
        if "English (with '^" in prompt:
            import re as _re

            m = _re.search(r"English \(with '\^([^']+)' inserted\)", prompt)
            marker = m.group(1) if m else "?"
            m2 = _re.search(
                r"English \(no sentinel\): (.*?)\n\nEnglish", prompt, _re.DOTALL
            )
            english = (m2.group(1) if m2 else "").strip()
            if "." in english:
                idx = english.find(".")
                placed = english[:idx] + f"^{marker}" + english[idx:]
            else:
                placed = english + f"^{marker}"
            return CommandResult(stdout=placed)
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
            "english": f"EN:{line['line_id']}.",
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
    # Marker placement (second-pass) put ^y before the first period
    # in the English; this proves the placement seam fires for body
    # lines that have markers.
    assert (
        seg_body["translation_history"][0]["english"]
        == "EN:p0036_body_l0001^y."
    )
    assert seg_body["translation_history"][0]["lexicon_profile"] == "auto"

    # A body line without markers gets an empty markers list and no caret.
    seg_l2 = existing["seg_p0036_body_l0002"]
    assert seg_l2["markers"] == []
    assert "^" not in seg_l2["latin_text"]
    # Lines without markers do NOT trigger a placement call, so the
    # English stays exactly as the model returned it.
    assert (
        seg_l2["translation_history"][0]["english"]
        == "EN:p0036_body_l0002."
    )

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


# ---------------------------------------------------------------------------
# Marker placement (second-pass) helpers
# ---------------------------------------------------------------------------


def test_validate_placement_accepts_inserted_token_only():
    """Placement is valid when the response differs from the input
    by exactly one inserted ``^<marker>`` token."""
    out = ts._validate_placement(
        "Hence Arnobius^y: hello.",
        input_english="Hence Arnobius: hello.",
        marker_id="y",
    )
    assert out == "Hence Arnobius^y: hello."


def test_validate_placement_rejects_changed_text():
    """Placement is rejected if the LLM altered any other character."""
    out = ts._validate_placement(
        "Hence Arnobius^y: HELLO.",  # casing differs
        input_english="Hence Arnobius: hello.",
        marker_id="y",
    )
    assert out is None


def test_validate_placement_rejects_missing_token():
    out = ts._validate_placement(
        "Hence Arnobius: hello.",
        input_english="Hence Arnobius: hello.",
        marker_id="y",
    )
    assert out is None


def test_place_markers_falls_back_to_end_of_line_on_validation_failure():
    """If the placement call returns a malformed response, the
    fallback appends ``^<marker>`` so the anchor is never lost."""

    def bad_runner(argv, stdin, timeout):
        # Drop the marker entirely and rewrite the sentence — invalid.
        return CommandResult(stdout="something completely different")

    adapter = AnthropicTranslationAdapter(
        default_config().get("anthropic"),
        command_runner=bad_runner,
    )
    placed, warnings = ts._place_markers_in_english(
        english="Hence Arnobius: hello.",
        latin_with_caret="Hinc Arnobius^y hello.",
        markers=[
            {"marker_id": "y", "char_offset": 13, "footnote_segment_id": "x"}
        ],
        adapter=adapter,
    )
    assert placed == "Hence Arnobius: hello.^y"
    assert any("validation failed" in w for w in warnings)


def test_place_markers_handles_missing_adapter_with_fallback():
    """No adapter means no second pass: the fallback fires for every
    marker so the artifact still records the anchor."""
    placed, warnings = ts._place_markers_in_english(
        english="Hence Arnobius: hello.",
        latin_with_caret="Hinc Arnobius^y hello.",
        markers=[
            {"marker_id": "y", "char_offset": 13, "footnote_segment_id": "x"}
        ],
        adapter=None,
    )
    assert placed == "Hence Arnobius: hello.^y"
    # No warnings emitted when the adapter is absent (silent path).
    assert warnings == []


def test_place_markers_runs_per_marker_sequentially():
    """Multiple markers on one line each get their own placement call,
    and the input to each subsequent call carries the previously
    inserted token."""
    seen_prompts: list[str] = []

    def fake_runner(argv, stdin, timeout):
        prompt = argv[2] if len(argv) > 2 else ""
        seen_prompts.append(prompt)
        # Always return input_english + token (end-of-line style, but
        # delivered through the normal placement path so validation
        # accepts it).
        import re as _re

        m = _re.search(r"English \(with '\^([^']+)' inserted\)", prompt)
        marker = m.group(1) if m else "?"
        m2 = _re.search(
            r"English \(no sentinel\): (.*?)\n\nEnglish",
            prompt,
            _re.DOTALL,
        )
        english = (m2.group(1) if m2 else "").strip()
        return CommandResult(stdout=f"{english}^{marker}")

    adapter = AnthropicTranslationAdapter(
        default_config().get("anthropic"),
        command_runner=fake_runner,
    )
    placed, warnings = ts._place_markers_in_english(
        english="alpha beta",
        latin_with_caret="alpha^a beta^b",
        markers=[
            {"marker_id": "a", "char_offset": 5, "footnote_segment_id": "x"},
            {"marker_id": "b", "char_offset": 10, "footnote_segment_id": "y"},
        ],
        adapter=adapter,
    )
    # Two calls, one per marker.
    assert len(seen_prompts) == 2
    # First call asks for ^a placement; second asks for ^b.
    assert "English (with '^a' inserted)" in seen_prompts[0]
    assert "English (with '^b' inserted)" in seen_prompts[1]
    # Second call's input English already has ^a so the model can see
    # the previous placement context.
    assert "English (no sentinel): alpha beta^a" in seen_prompts[1]
    assert placed == "alpha beta^a^b"
    assert warnings == []


# ---------------------------------------------------------------------------
# Cross-page context resolution (v3 Hard Rule 9)
# ---------------------------------------------------------------------------


def test_page_file_for_resolves_present_and_absent_pages(tmp_path, monkeypatch):
    """Sanity check for ``_page_file_for``: it must return the path
    when the file exists, None when it doesn't, and None for
    non-positive page numbers."""
    monkeypatch.setattr(ts, "ANNOTATIONS_DIR", tmp_path)
    (tmp_path / "page_p0042.json").write_text("{}", encoding="utf-8")
    assert ts._page_file_for(42) == tmp_path / "page_p0042.json"
    assert ts._page_file_for(43) is None  # file absent
    assert ts._page_file_for(0) is None   # out of range
