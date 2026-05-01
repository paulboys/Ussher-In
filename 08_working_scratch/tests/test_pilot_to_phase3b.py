"""Tests for the pilot OCR -> Phase 3b annotation converter."""

from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "pipeline_scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pytest

from pilot_to_phase3b import convert_record, write_phase3b_files


def _sample_record() -> dict:
    """Minimal three-marginalia page exercising both same-anchor and
    adjacent-anchor coalescing."""
    return {
        "part": "part1",
        "page_num": 1,
        "page_id": "p0001",
        "ocr_engine": "gemini",
        "ocr_provider_model": "gemini-3.1-pro-preview",
        "ocr_lang": ["lat", "grc"],
        "raw_confidence_avg": 93.0,
        "raw_confidence_min": 90.0,
        "page_summary": "summary",
        "lines": [
            {
                "region": "header",
                "line_index": 0,
                "text_raw_ocr": "2",
                "confidence": 1.0,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "First body line.",
                "confidence": 0.95,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "body",
                "line_index": 1,
                "text_raw_ocr": "Second body line.",
                "confidence": 0.95,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "body",
                "line_index": 2,
                "text_raw_ocr": "Third body line.",
                "confidence": 0.95,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            # Two same-anchor fragments for body line 1 -> coalesce.
            {
                "region": "marginalia",
                "line_index": 0,
                "text_raw_ocr": "Niceph. hist.",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "b",
                "marginalia_anchor_index": 1,
            },
            {
                "region": "marginalia",
                "line_index": 1,
                "text_raw_ocr": "Eccleſiaſt.",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": 1,
            },
            # Adjacent-anchor continuation (lowercase start) -> coalesce.
            {
                "region": "marginalia",
                "line_index": 2,
                "text_raw_ocr": "lib.2. cap.40.",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": 2,
            },
            # Distinct note for body line 2 (capital start, gap to line 0/1).
            {
                "region": "marginalia",
                "line_index": 3,
                "text_raw_ocr": "Pſal. 19.6.",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "f",
                "marginalia_anchor_index": 2,
            },
            {
                "region": "catchword",
                "line_index": 0,
                "text_raw_ocr": "Σαυ-",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
        ],
    }


def test_convert_record_emits_four_regions_and_footnotes_array():
    payload = convert_record(_sample_record(), source_pdf="00_source_pdf/x.pdf")
    regions = payload["regions"]
    assert set(regions.keys()) == {"header", "body", "marginalia", "catchword"}
    assert len(regions["header"]) == 1
    assert len(regions["body"]) == 3
    assert len(regions["marginalia"]) == 4
    assert len(regions["catchword"]) == 1
    assert "footnote" not in regions
    assert isinstance(payload["footnotes"], list)


def test_legacy_phase3a_fields_are_dropped():
    payload = convert_record(_sample_record())
    body0 = payload["regions"]["body"][0]
    for field in (
        "contains_ae_target",
        "contains_marker",
        "uncertain_ae",
        "marker_uncertain",
        "glyph_counts",
        "marker_link_target",
    ):
        assert field not in body0, f"{field} should not be present"


def test_text_ocr_original_baseline_is_set():
    payload = convert_record(_sample_record())
    for region_lines in payload["regions"].values():
        for line in region_lines:
            assert "text_ocr_original" in line
            assert line["text_ocr_original"] == line["text_gold"]


def test_body_lines_have_markers_array():
    payload = convert_record(_sample_record())
    for body_line in payload["regions"]["body"]:
        assert isinstance(body_line.get("markers"), list)


def test_marginalia_coalesce_into_two_footnotes():
    """Same-anchor + adjacent-anchor continuation should produce 2 logical
    footnotes from 4 raw marginalia fragments."""
    payload = convert_record(_sample_record())
    footnotes = payload["footnotes"]
    assert len(footnotes) == 2
    # Numbered sequentially per page.
    assert [fn["marker_number"] for fn in footnotes] == [1, 2]
    # Both footnotes get a kind defaulted to citation.
    assert all(fn["kind"] == "citation" for fn in footnotes)
    # Each carries provenance.
    assert all(fn["source_region"] == "marginalia" for fn in footnotes)


def test_first_footnote_coalesces_three_fragments():
    payload = convert_record(_sample_record())
    fn1 = payload["footnotes"][0]
    # Anchored to body line 1 -> body_l0002 (1-based index in line_id).
    assert fn1["body_line_id"] == payload["regions"]["body"][1]["line_id"]
    assert "Niceph" in fn1["text_gold"]
    assert "Eccleſiaſt" in fn1["text_gold"]
    assert "lib.2" in fn1["text_gold"]
    assert len(fn1["source_marginalia_line_ids"]) == 3


def test_anchored_body_line_gets_marker_record():
    payload = convert_record(_sample_record())
    body1 = payload["regions"]["body"][1]
    assert len(body1["markers"]) == 1
    marker = body1["markers"][0]
    assert marker["number"] == 1
    assert marker["footnote_id"] == payload["footnotes"][0]["footnote_id"]
    assert marker["char_offset"] is None


def test_meta_carries_ocr_provenance():
    payload = convert_record(_sample_record(), source_pdf="00_source_pdf/x.pdf")
    meta = payload["meta"]
    assert meta["ocr_engine"] == "gemini"
    assert meta["ocr_provider_model"] == "gemini-3.1-pro-preview"
    assert meta["ocr_lang"] == ["lat", "grc"]
    assert meta["annotation_status"] == "ocr_seeded"
    assert payload["source_pdf"] == "00_source_pdf/x.pdf"


def test_pilot_footnote_region_mapped_into_marginalia():
    record = _sample_record()
    record["lines"].append(
        {
            "region": "footnote",
            "line_index": 99,
            "text_raw_ocr": "stray footnote text",
            "confidence": 0.9,
            "illegible": False,
            "marker_id": "",
            "marginalia_anchor_index": None,
        }
    )
    payload = convert_record(record)
    assert "footnote" not in payload["regions"]
    # Stray footnote text rolled into marginalia for preservation.
    marg_texts = [m["text_gold"] for m in payload["regions"]["marginalia"]]
    assert "stray footnote text" in marg_texts


def test_orphan_marginalia_appears_in_footnotes_without_body_anchor():
    record = _sample_record()
    record["lines"].append(
        {
            "region": "marginalia",
            "line_index": 50,
            "text_raw_ocr": "Orphan note.",
            "confidence": 0.9,
            "illegible": False,
            "marker_id": "",
            "marginalia_anchor_index": 999,  # No body line at this index.
        }
    )
    payload = convert_record(record)
    orphans = [fn for fn in payload["footnotes"] if fn["body_line_id"] == ""]
    assert len(orphans) == 1
    assert orphans[0]["text_gold"] == "Orphan note."


# --------------------------------------------------------------------------
# Inline superscript sentinels (^X) and marker_id linking
# --------------------------------------------------------------------------


def _record_with_inline_sentinel() -> dict:
    """Body line with ^y sentinel + marginalia carrying marker_id='y'."""
    return {
        "part": "part1",
        "page_num": 36,
        "page_id": "p0036",
        "lines": [
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "Hinc Arnobius^y Tam velociter currit",
                "confidence": 0.97,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "marginalia",
                "line_index": 1,
                "text_raw_ocr": "in Psalm. 147.",
                "confidence": 0.9,
                "marker_id": "y",
                # No anchor index; should still match by symbol.
                "marginalia_anchor_index": None,
            },
        ],
    }


def test_inline_sentinel_strips_caret_and_links_marker_to_footnote():
    payload = convert_record(_record_with_inline_sentinel())
    body = payload["regions"]["body"]
    assert body[0]["text_gold"] == "Hinc Arnobius Tam velociter currit"
    assert "_pending_inline_markers" not in body[0]

    assert len(body[0]["markers"]) == 1
    marker = body[0]["markers"][0]
    # 'Hinc Arnobius' is 13 chars; superscript anchored immediately after.
    assert marker["char_offset"] == 13

    fns = payload["footnotes"]
    assert len(fns) == 1
    fn = fns[0]
    assert fn["marker_id"] == "y"
    assert fn["text_gold"] == "in Psalm. 147."
    assert fn["body_line_id"] == body[0]["line_id"]
    assert marker["footnote_id"] == fn["footnote_id"]


def test_multiple_sentinels_one_line_link_to_distinct_footnotes():
    record = {
        "part": "part1",
        "page_num": 2,
        "page_id": "p0002",
        "lines": [
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "alpha^a beta^b end",
                "confidence": 0.95,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "marginalia",
                "line_index": 1,
                "text_raw_ocr": "first note.",
                "confidence": 0.9,
                "marker_id": "a",
                "marginalia_anchor_index": None,
            },
            {
                "region": "marginalia",
                "line_index": 2,
                "text_raw_ocr": "second note.",
                "confidence": 0.9,
                "marker_id": "b",
                "marginalia_anchor_index": None,
            },
        ],
    }
    payload = convert_record(record)
    body = payload["regions"]["body"][0]
    assert body["text_gold"] == "alpha beta end"
    offsets = sorted(m["char_offset"] for m in body["markers"])
    assert offsets == [5, 10]  # after 'alpha' and after 'alpha beta'.

    by_symbol = {fn["marker_id"]: fn for fn in payload["footnotes"]}
    assert by_symbol["a"]["text_gold"] == "first note."
    assert by_symbol["b"]["text_gold"] == "second note."
    assert all(fn["body_line_id"] == body["line_id"] for fn in payload["footnotes"])


def test_inline_sentinel_without_matching_marker_is_dropped(capsys):
    record = {
        "part": "part1",
        "page_num": 3,
        "page_id": "p0003",
        "lines": [
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "lonely^q word",
                "confidence": 0.9,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
        ],
    }
    payload = convert_record(record)
    body = payload["regions"]["body"][0]
    # Sentinel stripped from text even when no footnote matches.
    assert body["text_gold"] == "lonely word"
    # No marker created (would be unlinked / invalid).
    assert body["markers"] == []
    assert payload["footnotes"] == []
    err = capsys.readouterr().err
    assert "p0003" in err and "'q'" in err


def test_legacy_anchor_index_path_still_links_when_no_sentinel():
    """Pages produced before the sentinel feature must keep working."""
    record = {
        "part": "part1",
        "page_num": 4,
        "page_id": "p0004",
        "lines": [
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "plain body text",
                "confidence": 0.95,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "marginalia",
                "line_index": 1,
                "text_raw_ocr": "legacy note.",
                "confidence": 0.9,
                "marker_id": "",
                "marginalia_anchor_index": 0,  # anchors to body line_index 0.
            },
        ],
    }
    payload = convert_record(record)
    body = payload["regions"]["body"][0]
    assert body["text_gold"] == "plain body text"
    assert len(body["markers"]) == 1
    # No sentinel → char_offset stays None (end-of-line render).
    assert body["markers"][0]["char_offset"] is None
    fn = payload["footnotes"][0]
    assert fn["body_line_id"] == body["line_id"]
    assert fn["marker_id"] == ""

def test_write_phase3b_files_refuses_overwrite_by_default(tmp_path):
    target = tmp_path / "page_p0001.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_phase3b_files([_sample_record()], tmp_path, overwrite=False)


def test_write_phase3b_files_overwrite_replaces(tmp_path):
    target = tmp_path / "page_p0001.json"
    target.write_text("{}", encoding="utf-8")
    written = write_phase3b_files([_sample_record()], tmp_path, overwrite=True)
    assert written == [target]
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["page_id"] == "p0001"
    assert payload["regions"]["body"][0]["text_gold"] == "First body line."
    assert isinstance(payload["footnotes"], list)


def test_default_edition_is_1687_when_not_specified():
    payload = convert_record(_sample_record())
    assert payload["edition"] == "1687_second"


def test_edition_kwarg_overrides_default():
    payload = convert_record(_sample_record(), edition="1847_elrington_todd")
    assert payload["edition"] == "1847_elrington_todd"


def test_unknown_edition_falls_back_to_default():
    payload = convert_record(_sample_record(), edition="bogus_edition")
    assert payload["edition"] == "1687_second"


def test_edition_can_be_carried_on_record():
    record = _sample_record()
    record["edition"] = "1847_elrington_todd"
    payload = convert_record(record)
    assert payload["edition"] == "1847_elrington_todd"


