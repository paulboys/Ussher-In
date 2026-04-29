"""Regression tests for annotation_ui save/load preserving dual-text fields.

The Gemini OCR migration adds new per-line fields (``text_raw_ocr``,
``normalized_form``, ``alignment_index``, ``confidence``). The Flask
annotation UI must round-trip these fields without dropping them when
posting back via /api/page/<page_id>.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PHASE3B_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "phase3b" / "scripts"
)
if str(PHASE3B_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PHASE3B_SCRIPTS))

# Flask is an optional dep for the annotation UI server; skip these tests
# entirely when it is not installed in the active environment.
pytest.importorskip("flask")


def _build_payload() -> dict:
    return {
        "page_id": "p0033",
        "part": "part1",
        "source_pdf": "00_source_pdf/sample.pdf",
        "page_num": 33,
        "regions": {
            "header": [],
            "body": [
                {
                    "page_id": "p0033",
                    "region": "body",
                    "line_id": "p0033_body_l0001",
                    "text_gold": "Ecclesiarum",
                    "text_raw_ocr": "Eccleſiarum",
                    "normalized_form": "Ecclesiarum",
                    "alignment_index": 0,
                    "confidence": 0.91,
                    "contains_ae_target": False,
                    "contains_marker": False,
                    "marker_id": "",
                    "marker_link_target": "",
                    "uncertain_ae": False,
                    "marker_uncertain": False,
                    "reviewer": "",
                    "review_status": "draft",
                    "notes": "",
                }
            ],
            "footnote": [],
        },
        "marker_links": [],
        "meta": {
            "annotation_status": "draft",
            "review_status": "draft",
            "reviewer": "",
            "notes": "",
        },
    }


@pytest.fixture
def annotation_app(tmp_path, monkeypatch):
    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    payload = _build_payload()
    target = annotations_dir / "page_p0033.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    import importlib
    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", annotations_dir)
    annotation_ui.app.testing = True
    yield annotation_ui.app, annotations_dir


def test_save_preserves_new_dual_text_fields(annotation_app):
    app, annotations_dir = annotation_app
    payload = _build_payload()
    payload["regions"]["body"][0]["text_gold"] = "Ecclesiarum (edited)"

    client = app.test_client()
    response = client.post(
        "/api/page/p0033",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)

    saved = json.loads((annotations_dir / "page_p0033.json").read_text(encoding="utf-8"))
    body_line = saved["regions"]["body"][0]
    assert body_line["text_raw_ocr"] == "Eccleſiarum"
    assert body_line["normalized_form"] == "Ecclesiarum"
    assert body_line["alignment_index"] == 0
    assert body_line["confidence"] == 0.91
    assert body_line["text_gold"] == "Ecclesiarum (edited)"


def test_load_returns_new_dual_text_fields(annotation_app):
    app, _ = annotation_app
    client = app.test_client()
    response = client.get("/api/page/p0033")
    assert response.status_code == 200
    body_line = response.get_json()["regions"]["body"][0]
    assert body_line["text_raw_ocr"] == "Eccleſiarum"
    assert body_line["confidence"] == 0.91


# ---------------------------------------------------------------------------
# Edit log: each /api/page/<page_id> POST appends per-field diff entries to
# a sidecar JSONL alongside the page JSON. Used downstream for prompt tuning.
# ---------------------------------------------------------------------------


def _build_redesign_payload() -> dict:
    return {
        "page_id": "p0099",
        "part": "part1",
        "source_pdf": "00_source_pdf/sample.pdf",
        "page_num": 99,
        "regions": {
            "header": [],
            "body": [
                {
                    "page_id": "p0099",
                    "region": "body",
                    "line_id": "p0099_body_l0001",
                    "text_gold": "Body line one.",
                    "text_ocr_original": "Body line one.",
                    "marker_id": "",
                    "review_status": "draft",
                    "reviewer": "",
                    "notes": "",
                    "markers": [
                        {
                            "number": 1,
                            "footnote_id": "p0099_fn_001",
                            "char_offset": None,
                        }
                    ],
                }
            ],
            "marginalia": [],
            "catchword": [],
        },
        "footnotes": [
            {
                "footnote_id": "p0099_fn_001",
                "page_id": "p0099",
                "marker_number": 1,
                "body_line_id": "p0099_body_l0001",
                "text_gold": "Niceph. hist.",
                "text_ocr_original": "Niceph. hist.",
                "kind": "citation",
                "source_region": "marginalia",
                "source_marginalia_line_ids": [],
                "review_status": "draft",
                "notes": "",
            }
        ],
        "meta": {
            "annotation_status": "ocr_seeded",
            "review_status": "draft",
            "reviewer": "",
            "notes": "",
            "ocr_page_summary": "summary v1",
        },
    }


@pytest.fixture
def redesign_app(tmp_path, monkeypatch):
    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    payload = _build_redesign_payload()
    target = annotations_dir / "page_p0099.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", annotations_dir)
    annotation_ui.app.testing = True
    yield annotation_ui.app, annotations_dir


def _read_edits(annotations_dir: Path) -> list[dict]:
    path = annotations_dir / "page_p0099.edits.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_save_records_line_text_edit_to_sidecar(redesign_app):
    app, annotations_dir = redesign_app
    payload = _build_redesign_payload()
    payload["regions"]["body"][0]["text_gold"] = "Body line one. (edited)"

    client = app.test_client()
    response = client.post(
        "/api/page/p0099",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["edits_recorded"] >= 1

    edits = _read_edits(annotations_dir)
    line_edits = [e for e in edits if e["scope"] == "line" and e["field"] == "text_gold"]
    assert len(line_edits) == 1
    assert line_edits[0]["target_id"] == "p0099_body_l0001"
    assert line_edits[0]["before"] == "Body line one."
    assert line_edits[0]["after"] == "Body line one. (edited)"


def test_save_records_footnote_edit_and_kind_change(redesign_app):
    app, annotations_dir = redesign_app
    payload = _build_redesign_payload()
    payload["footnotes"][0]["text_gold"] = "Niceph. hist. lib.2."
    payload["footnotes"][0]["kind"] = "not_a_note"

    client = app.test_client()
    response = client.post(
        "/api/page/p0099",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200

    edits = _read_edits(annotations_dir)
    fn_edits = [e for e in edits if e["scope"] == "footnote"]
    fields = {e["field"] for e in fn_edits}
    assert "text_gold" in fields
    assert "kind" in fields


def test_save_records_page_meta_edit(redesign_app):
    app, annotations_dir = redesign_app
    payload = _build_redesign_payload()
    payload["meta"]["ocr_page_summary"] = "summary v2"
    payload["meta"]["notes"] = "Reviewed by Paul"

    client = app.test_client()
    response = client.post(
        "/api/page/p0099",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200

    edits = _read_edits(annotations_dir)
    meta_edits = [e for e in edits if e["scope"] == "page_meta"]
    fields = {e["field"] for e in meta_edits}
    assert "ocr_page_summary" in fields
    assert "notes" in fields


def test_edit_log_is_append_only(redesign_app):
    app, annotations_dir = redesign_app
    client = app.test_client()

    payload = _build_redesign_payload()
    payload["regions"]["body"][0]["text_gold"] = "edit 1"
    client.post("/api/page/p0099", data=json.dumps(payload), content_type="application/json")

    payload2 = _build_redesign_payload()
    payload2["regions"]["body"][0]["text_gold"] = "edit 2"
    client.post("/api/page/p0099", data=json.dumps(payload2), content_type="application/json")

    edits = _read_edits(annotations_dir)
    text_edits = [e for e in edits if e["field"] == "text_gold" and e["scope"] == "line"]
    # Two saves -> at least two text_gold entries.
    assert len(text_edits) >= 2


def test_legacy_payload_with_old_fields_still_loads_and_saves(redesign_app):
    """Old payloads with regions.footnote and legacy æ fields still validate."""
    app, annotations_dir = redesign_app
    legacy = {
        "page_id": "p0099",
        "part": "part1",
        "source_pdf": "00_source_pdf/sample.pdf",
        "page_num": 99,
        "regions": {
            "header": [],
            "body": [
                {
                    "page_id": "p0099",
                    "region": "body",
                    "line_id": "p0099_body_l0001",
                    "text_gold": "Legacy line",
                    "contains_ae_target": True,  # legacy
                    "contains_marker": False,    # legacy
                    "uncertain_ae": False,       # legacy
                    "marker_uncertain": False,   # legacy
                    "marker_id": "",
                    "marker_link_target": "",    # legacy
                    "review_status": "draft",
                    "reviewer": "",
                    "notes": "",
                }
            ],
            "footnote": [],  # legacy region
            "marginalia": [],
            "catchword": [],
        },
        "meta": {"annotation_status": "draft", "review_status": "draft", "reviewer": "", "notes": ""},
    }
    (annotations_dir / "page_p0099.json").write_text(json.dumps(legacy), encoding="utf-8")
    client = app.test_client()
    response = client.post(
        "/api/page/p0099",
        data=json.dumps(legacy),
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)

