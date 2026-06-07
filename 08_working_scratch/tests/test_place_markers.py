"""Tests for the sentence-pipeline marker-placement pass (place_markers.py)."""
import sys
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "pipeline_scripts"
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

import place_markers as pm  # noqa: E402
from translate_segments import _place_markers_in_english  # noqa: E402


def test_placement_markers_resolves_symbols_in_order():
    markers = [
        {"footnote_id": "p0036_fn_001", "char_offset": 5},
        {"footnote_id": "p0036_fn_002", "char_offset": 20},
    ]
    lookup = {"p0036_fn_001": "y", "p0036_fn_002": "z"}
    out = pm._placement_markers(markers, lookup, english="some english text")
    assert out == [{"marker_id": "y"}, {"marker_id": "z"}]


def test_placement_markers_skips_already_present():
    markers = [
        {"footnote_id": "p0036_fn_001"},
        {"footnote_id": "p0036_fn_002"},
    ]
    lookup = {"p0036_fn_001": "y", "p0036_fn_002": "z"}
    # English already carries ^y -> only ^z should be queued.
    out = pm._placement_markers(markers, lookup, english="text^y more")
    assert out == [{"marker_id": "z"}]


def test_placement_markers_skips_unresolvable():
    markers = [{"footnote_id": "p9999_fn_999"}]
    out = pm._placement_markers(markers, {}, english="text")
    assert out == []


def test_fallback_appends_caret_when_no_adapter():
    # With no adapter, _place_markers_in_english appends ^<id> at end-of-line.
    placed, warnings = _place_markers_in_english(
        english="So swiftly does his word run.",
        latin_with_caret="Hinc Arnobius^y ...",
        markers=[{"marker_id": "y"}],
        adapter=None,
    )
    assert placed == "So swiftly does his word run.^y"
    assert warnings == []  # no-adapter path is silent, not a failure


def test_page_num_and_latest_english():
    assert pm._page_num({"page_id": "p0036"}) == 36
    rec = {"translation_history": [{"english": "old"}, {"english": "new"}]}
    assert pm._latest_english(rec) == "new"
    assert pm._latest_english({"final_english": "fallback"}) == "fallback"
