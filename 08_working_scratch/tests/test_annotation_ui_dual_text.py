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
