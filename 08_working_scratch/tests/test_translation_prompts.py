"""Tests for the translation prompt builder and lexicon hint logic."""

from __future__ import annotations

import pytest

from translation_prompts import (
    LEXICON_GREEK_HINTS,
    LEXICON_LATIN_HINTS,
    _build_marker_lookup,
    _inject_markers,
    build_translation_prompt,
    contains_greek,
)


_BODY_LATIN = [
    {
        "line_id": "p0036_body_l0001",
        "text_gold": "Hinc Arnobius “ Tam velociter currit sermo ejus ut,",
        "markers": [
            {"number": 1, "footnote_id": "p0036_fn_001", "char_offset": 13},
        ],
    },
    {
        "line_id": "p0036_body_l0002",
        "text_gold": "cum per tot millia annorum in sola Judæa notus fuerit",
        "markers": [],
    },
]

_BODY_WITH_GREEK = [
    {
        "line_id": "p0036_body_l0010",
        "text_gold": "ὁ λόγος αὐτοῦ τρέχει ταχέως",
    }
]

_FOOTNOTE = [
    {
        "footnote_id": "p0036_fn_001",
        "marker_id": "y",
        "body_line_id": "p0036_body_l0001",
        "text_gold": "in Psalm. 147.",
    }
]


def test_contains_greek_detects_polytonic():
    assert contains_greek("ἀρχή") is True
    assert contains_greek("Hello world") is False


def test_auto_profile_includes_only_latin_when_no_greek():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        footnotes=_FOOTNOTE,
        lexicon_profile="auto",
    )
    assert LEXICON_LATIN_HINTS in prompt
    assert LEXICON_GREEK_HINTS not in prompt


def test_auto_profile_includes_greek_when_greek_present():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_WITH_GREEK,
        lexicon_profile="auto",
    )
    assert LEXICON_LATIN_HINTS in prompt
    assert LEXICON_GREEK_HINTS in prompt


def test_minimal_profile_omits_all_lexicon_blocks():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        lexicon_profile="minimal",
    )
    assert "Forcellini" not in prompt
    assert "Lampe" not in prompt


def test_latin_greek_profile_forces_greek_block_even_without_greek():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        lexicon_profile="latin_greek",
    )
    assert LEXICON_GREEK_HINTS in prompt


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        build_translation_prompt(
            page_id="p0036",
            body_lines=_BODY_LATIN,
            lexicon_profile="bogus",
        )


def test_prompt_lists_each_unit_id_in_request_section():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        footnotes=_FOOTNOTE,
        lexicon_profile="auto",
    )
    assert "p0036_body_l0001" in prompt
    assert "p0036_body_l0002" in prompt
    assert "p0036_fn_001" in prompt
    # footnote anchored to body line is shown
    assert "anchored to p0036_body_l0001" in prompt


def test_prompt_includes_extra_context_when_provided():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        lexicon_profile="auto",
        extra_context="catchword: matched\nmarginalia anchors: 1",
    )
    assert "catchword: matched" in prompt


def test_lexicon_hints_do_not_quote_lexicon_entries():
    """Sanity-check: hint blocks describe authorities by name only and
    must not embed dictionary entries verbatim."""
    for block in (LEXICON_LATIN_HINTS, LEXICON_GREEK_HINTS):
        assert "definition" not in block.lower() or "do NOT" in block
        # No leading-quote dictionary-style entries
        assert '" :' not in block


# ---------------------------------------------------------------------------
# Footnote-marker caret-sentinel injection
# ---------------------------------------------------------------------------


def test_build_marker_lookup_maps_footnote_ids_to_marker_symbols():
    lookup = _build_marker_lookup(_FOOTNOTE)
    assert lookup == {"p0036_fn_001": "y"}


def test_inject_markers_inserts_caret_sentinel_at_offset():
    out = _inject_markers(
        "Hinc Arnobius “ Tam velociter",
        [{"footnote_id": "p0036_fn_001", "char_offset": 13}],
        {"p0036_fn_001": "y"},
    )
    assert out == "Hinc Arnobius^y “ Tam velociter"


def test_inject_markers_handles_multiple_markers_right_to_left():
    out = _inject_markers(
        "alpha beta gamma",
        [
            {"footnote_id": "fn1", "char_offset": 5},
            {"footnote_id": "fn2", "char_offset": 10},
        ],
        {"fn1": "a", "fn2": "b"},
    )
    assert out == "alpha^a beta^b gamma"


def test_inject_markers_skips_markers_without_resolvable_symbol():
    out = _inject_markers(
        "alpha beta",
        [{"footnote_id": "missing", "char_offset": 5}],
        {"fn1": "a"},
    )
    assert out == "alpha beta"


def test_inject_markers_skips_markers_with_missing_offset_or_id():
    out = _inject_markers(
        "alpha beta",
        [
            {"footnote_id": "fn1"},
            {"char_offset": 5},
            {"footnote_id": "fn1", "char_offset": "not-a-number"},
        ],
        {"fn1": "a"},
    )
    assert out == "alpha beta"


def test_inject_markers_clamps_out_of_range_offset_to_end():
    out = _inject_markers(
        "alpha",
        [{"footnote_id": "fn1", "char_offset": 999}],
        {"fn1": "a"},
    )
    assert out == "alpha^a"


def test_build_translation_prompt_emits_caret_sentinel_in_body_line():
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        footnotes=_FOOTNOTE,
        lexicon_profile="auto",
    )
    assert "Hinc Arnobius^y" in prompt
    # And the caret-sentinel instruction is present so Claude knows
    # to drop the marker symbol in its translation.
    assert "Footnote-marker sentinels" in prompt


def test_build_translation_prompt_omits_marker_when_footnote_excluded():
    """If the footnote is not in the batch (e.g. unlinked), no marker
    is injected even when the body line still has a markers[] entry."""
    prompt = build_translation_prompt(
        page_id="p0036",
        body_lines=_BODY_LATIN,
        footnotes=(),  # footnote absent
        lexicon_profile="auto",
    )
    assert "Hinc Arnobius^" not in prompt
    assert "Hinc Arnobius “" in prompt
