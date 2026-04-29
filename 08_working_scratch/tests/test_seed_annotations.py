"""Tests for the annotation seed schema (Phase 3b).

Covers the dual-text fields (text_raw_ocr, normalized_form, alignment_index,
confidence) added for the Gemini OCR migration, and verifies that records
produced by ``pilot_ocr.run_gemini_pilot`` map cleanly into annotation JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path

PHASE3B_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "phase3b" / "scripts"
)
if str(PHASE3B_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PHASE3B_SCRIPTS))

from seed_annotations_from_raw_ocr import (  # noqa: E402
    build_payload,
    build_payload_from_gemini_record,
    make_line,
)


def test_make_line_includes_dual_text_fields_with_defaults():
    line = make_line("p0033", "body", 1, "Eccleſiarum")
    assert line["text_gold"] == "Eccleſiarum"
    assert line["text_raw_ocr"] == "Eccleſiarum"
    assert line["normalized_form"] == "Eccleſiarum"
    assert line["alignment_index"] == 0
    assert line["confidence"] is None


def test_make_line_accepts_explicit_dual_text_values():
    line = make_line(
        "p0033",
        "body",
        2,
        "antiquitates",
        text_raw_ocr="antiqui|tates",
        normalized_form="antiquitates",
        alignment_index=7,
        confidence=0.93,
    )
    assert line["text_raw_ocr"] == "antiqui|tates"
    assert line["normalized_form"] == "antiquitates"
    assert line["alignment_index"] == 7
    assert line["confidence"] == 0.93


def test_legacy_build_payload_seeds_new_fields_safely():
    payload = build_payload(
        part="part1",
        source_pdf="00_source_pdf/sample.pdf",
        page_num=33,
        raw_text="line one\nline two\n[FOOTNOTES]\n[a] gloss\n",
    )
    body = payload["regions"]["body"]
    assert len(body) == 2
    assert body[0]["text_raw_ocr"] == body[0]["text_gold"]
    assert body[0]["normalized_form"] == body[0]["text_gold"]
    assert body[0]["confidence"] is None
    footnotes = payload["regions"]["footnote"]
    assert len(footnotes) == 1
    assert footnotes[0]["region"] == "footnote"


def test_build_payload_from_gemini_record_preserves_per_line_fields():
    record = {
        "part": "part1",
        "page_num": 33,
        "page_id": "p0033",
        "ocr_engine": "gemini",
        "lines": [
            {
                "alignment_index": 0,
                "region": "header",
                "line_index": 0,
                "text_raw_ocr": "33",
                "normalized_form": "33",
                "confidence": 0.99,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "alignment_index": 1,
                "region": "body",
                "line_index": 0,
                "text_raw_ocr": "Eccleſiarum antiquita-",
                "normalized_form": "Ecclesiarum antiquita-",
                "confidence": 0.91,
                "illegible": False,
                "marker_id": "",
                "marginalia_anchor_index": None,
            },
            {
                "alignment_index": 2,
                "region": "footnote",
                "line_index": 0,
                "text_raw_ocr": "[a] gloſſa",
                "normalized_form": "[a] glossa",
                "confidence": 0.85,
                "illegible": False,
                "marker_id": "a",
                "marginalia_anchor_index": None,
            },
        ],
    }
    payload = build_payload_from_gemini_record(
        part="part1",
        source_pdf="00_source_pdf/sample.pdf",
        record=record,
    )
    assert payload["page_id"] == "p0033"
    assert len(payload["regions"]["header"]) == 1
    assert len(payload["regions"]["body"]) == 1
    assert len(payload["regions"]["footnote"]) == 1

    body_line = payload["regions"]["body"][0]
    assert body_line["text_raw_ocr"] == "Eccleſiarum antiquita-"
    assert body_line["normalized_form"] == "Ecclesiarum antiquita-"
    assert body_line["text_gold"] == "Ecclesiarum antiquita-"
    assert body_line["confidence"] == 0.91
    assert body_line["alignment_index"] == 1


def test_build_payload_from_gemini_record_folds_unknown_regions_into_body():
    record = {
        "part": "part1",
        "page_num": 34,
        "page_id": "p0034",
        "lines": [
            {
                "region": "marginalia",
                "text_raw_ocr": "Gen. 1.1",
                "normalized_form": "Gen. 1.1",
                "confidence": 0.88,
            },
            {
                "region": "catchword",
                "text_raw_ocr": "Sequitur",
                "normalized_form": "Sequitur",
                "confidence": 0.95,
            },
        ],
    }
    payload = build_payload_from_gemini_record(
        part="part1",
        source_pdf="00_source_pdf/sample.pdf",
        record=record,
    )
    body = payload["regions"]["body"]
    assert [line["text_gold"] for line in body] == ["Gen. 1.1", "Sequitur"]
