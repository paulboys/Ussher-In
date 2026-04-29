"""Tests for the pilot OCR -> Phase 3b annotation converter."""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Make the pipeline scripts directory importable.
SCRIPTS = Path(__file__).resolve().parents[1] / "pipeline_scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pytest

from pilot_to_phase3b import convert_record, write_phase3b_files


def _sample_record() -> dict:
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
                "normalized_form": "2",
                "confidence": 1.0,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "First body æ line",
                "normalized_form": "First body ae line",
                "confidence": 0.95,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "region": "marginalia",
                "line_index": 0,
                "text_raw_ocr": "ⁱ Rom. 16. 25.",
                "normalized_form": "ⁱ Rom. 16. 25.",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "ⁱ",
                "marginalia_anchor_index": 0,
            },
            {
                "region": "catchword",
                "line_index": 0,
                "text_raw_ocr": "Σαυ-",
                "normalized_form": "Σαυ-",
                "confidence": 0.9,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
        ],
    }


def test_convert_record_emits_all_five_regions():
    payload = convert_record(_sample_record(), source_pdf="00_source_pdf/x.pdf")
    regions = payload["regions"]
    assert set(regions.keys()) == {"header", "body", "footnote", "marginalia", "catchword"}
    assert len(regions["header"]) == 1
    assert len(regions["body"]) == 1
    assert len(regions["marginalia"]) == 1
    assert len(regions["catchword"]) == 1
    assert regions["footnote"] == []


def test_marginalia_anchor_resolves_to_body_line_id():
    payload = convert_record(_sample_record())
    body_line_id = payload["regions"]["body"][0]["line_id"]
    marg = payload["regions"]["marginalia"][0]
    assert marg["marker_id"] == "ⁱ"
    assert marg["marker_link_target"] == body_line_id


def test_text_gold_uses_raw_ocr_text_in_place():
    payload = convert_record(_sample_record())
    body0 = payload["regions"]["body"][0]
    assert body0["text_gold"] == "First body æ line"
    assert body0["contains_ae_target"] is True
    assert body0["review_status"] == "draft"
    assert body0["reviewer"] == ""
    # OCR provenance preserved alongside.
    assert body0["ocr_confidence"] == 0.95


def test_meta_carries_ocr_provenance():
    payload = convert_record(_sample_record(), source_pdf="00_source_pdf/x.pdf")
    meta = payload["meta"]
    assert meta["ocr_engine"] == "gemini"
    assert meta["ocr_provider_model"] == "gemini-3.1-pro-preview"
    assert meta["ocr_lang"] == ["lat", "grc"]
    assert meta["annotation_status"] == "ocr_seeded"
    assert payload["source_pdf"] == "00_source_pdf/x.pdf"


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
    assert payload["regions"]["body"][0]["text_gold"] == "First body æ line"
