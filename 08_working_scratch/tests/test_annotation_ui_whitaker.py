"""Tests for Whitaker corpus support in the annotation UI.

Two concerns covered:

1. ``_annotation_path`` / ``_annotations_dir`` namespace Whitaker pages
   into per-edition subdirectories (``annotations/whitaker_english/``
   and ``annotations/whitaker_latin/``) while leaving Ussher pages flat
   in the top-level annotations directory.
2. The HTTP routes accept an ``?edition=`` query parameter and route
   reads/writes through the same subdirectory namespacing, so a
   Whitaker ``p0001`` does not collide with an Ussher ``p0001``.
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

pytest.importorskip("flask")


def _build_payload(page_id: str, source_pdf: str = "00_source_pdf/sample.pdf") -> dict:
    page_num = int(page_id[1:])
    return {
        "page_id": page_id,
        "part": "whitaker_latin",
        "source_pdf": source_pdf,
        "page_num": page_num,
        "edition": "whitaker_latin",
        "regions": {
            "header": [],
            "body": [
                {
                    "page_id": page_id,
                    "region": "body",
                    "line_id": f"{page_id}_body_l0001",
                    "text_gold": "Bellarminus negat.",
                    "review_status": "draft",
                    "reviewer": "",
                    "notes": "",
                }
            ],
            "marginalia": [],
            "catchword": [],
        },
        "footnotes": [],
        "meta": {
            "annotation_status": "draft",
            "review_status": "draft",
            "reviewer": "",
            "notes": "",
        },
    }


@pytest.fixture
def whitaker_app(tmp_path, monkeypatch):
    """Annotations dir with one Whitaker-Latin page seeded under its
    namespaced subdirectory."""
    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()

    whitaker_latin_dir = annotations_dir / "whitaker_latin"
    whitaker_latin_dir.mkdir()

    payload = _build_payload("p0001")
    (whitaker_latin_dir / "page_p0001.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", annotations_dir)
    annotation_ui.app.testing = True
    yield annotation_ui.app, annotations_dir


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def test_corpus_subdir_routes_whitaker_to_namespaced_dirs():
    import annotation_ui

    assert annotation_ui._corpus_subdir("whitaker_english") == "whitaker_english"
    assert annotation_ui._corpus_subdir("whitaker_latin") == "whitaker_latin"


def test_corpus_subdir_returns_empty_for_ussher_editions():
    import annotation_ui

    assert annotation_ui._corpus_subdir("1687_second") == ""
    assert annotation_ui._corpus_subdir("1847_elrington_todd") == ""
    assert annotation_ui._corpus_subdir(None) == ""
    assert annotation_ui._corpus_subdir("") == ""


def test_annotation_path_namespaces_whitaker_pages(tmp_path, monkeypatch):
    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", tmp_path)

    ussher_path = annotation_ui._annotation_path("p0030")
    whitaker_eng_path = annotation_ui._annotation_path("p0001", "whitaker_english")
    whitaker_lat_path = annotation_ui._annotation_path("p0001", "whitaker_latin")

    assert ussher_path == tmp_path / "page_p0030.json"
    assert whitaker_eng_path == tmp_path / "whitaker_english" / "page_p0001.json"
    assert whitaker_lat_path == tmp_path / "whitaker_latin" / "page_p0001.json"


def test_whitaker_p0001_does_not_collide_with_ussher_p0001(tmp_path, monkeypatch):
    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", tmp_path)
    ussher_path = annotation_ui._annotation_path("p0001")
    whitaker_path = annotation_ui._annotation_path("p0001", "whitaker_english")
    assert ussher_path != whitaker_path


def test_annotation_paths_filters_to_corpus_when_edition_passed(tmp_path, monkeypatch):
    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", tmp_path)
    (tmp_path / "page_p0030.json").write_text("{}", encoding="utf-8")
    (tmp_path / "whitaker_english").mkdir()
    (tmp_path / "whitaker_english" / "page_p0001.json").write_text("{}", encoding="utf-8")
    (tmp_path / "whitaker_english" / "page_p0002.json").write_text("{}", encoding="utf-8")

    ussher = [p.name for p in annotation_ui._annotation_paths()]
    whitaker = [p.name for p in annotation_ui._annotation_paths("whitaker_english")]

    assert ussher == ["page_p0030.json"]
    assert whitaker == ["page_p0001.json", "page_p0002.json"]


# ---------------------------------------------------------------------------
# HTTP routes with ?edition= query parameter
# ---------------------------------------------------------------------------


def test_get_page_with_edition_query_returns_whitaker_payload(whitaker_app):
    app, _ = whitaker_app
    client = app.test_client()
    response = client.get("/api/page/p0001?edition=whitaker_latin")
    assert response.status_code == 200
    data = response.get_json()
    assert data["page_id"] == "p0001"
    assert data["edition"] == "whitaker_latin"


def test_get_page_without_edition_does_not_find_whitaker_page(whitaker_app):
    # Without ?edition= the route looks in the flat Ussher dir; the
    # Whitaker page must NOT be reachable via a flat URL.
    app, _ = whitaker_app
    client = app.test_client()
    response = client.get("/api/page/p0001")
    assert response.status_code == 404


def test_save_page_with_edition_query_writes_to_subdir(whitaker_app):
    app, annotations_dir = whitaker_app
    payload = _build_payload("p0001")
    payload["regions"]["body"][0]["text_gold"] = "Bellarminus negat (edited)."

    client = app.test_client()
    response = client.post(
        "/api/page/p0001?edition=whitaker_latin",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)

    saved_path = annotations_dir / "whitaker_latin" / "page_p0001.json"
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved["regions"]["body"][0]["text_gold"] == "Bellarminus negat (edited)."

    # Edits sidecar lands next to the saved JSON, also under the subdir.
    edits_path = annotations_dir / "whitaker_latin" / "page_p0001.edits.jsonl"
    assert edits_path.exists()


def test_api_pages_filters_by_edition_query(whitaker_app):
    app, annotations_dir = whitaker_app
    # Add an Ussher page to the flat dir so we can confirm the filter.
    (annotations_dir / "page_p0030.json").write_text("{}", encoding="utf-8")

    client = app.test_client()
    ussher_resp = client.get("/api/pages")
    whitaker_resp = client.get("/api/pages?edition=whitaker_latin")

    assert ussher_resp.get_json()["pages"] == ["p0030"]
    assert whitaker_resp.get_json()["pages"] == ["p0001"]


# ---------------------------------------------------------------------------
# OCR start endpoint accepts Whitaker editions and forces the part value
# ---------------------------------------------------------------------------


def test_ocr_start_rejects_unknown_edition(tmp_path, monkeypatch):
    import annotation_ui

    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", annotations_dir)
    annotation_ui.app.testing = True

    client = annotation_ui.app.test_client()
    response = client.post(
        "/api/ocr/start",
        data=json.dumps(
            {
                "pdf": "Disputatio_de_Sacra_Scriptura_contra_R_B_LATIN.pdf",
                "page": 1,
                "edition": "not_a_real_edition",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "edition" in response.get_data(as_text=True)


def test_ocr_start_validation_accepts_whitaker_editions(tmp_path, monkeypatch):
    """The OCR start endpoint must accept whitaker_english /
    whitaker_latin without a separate ``part`` argument and must not
    reject the request on the Ussher-only ``part`` constraint."""
    import annotation_ui

    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    source_dir = tmp_path / "00_source_pdf"
    source_dir.mkdir()
    fake_pdf = source_dir / "Disputatio_de_Sacra_Scriptura_contra_R_B_LATIN.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", annotations_dir)
    monkeypatch.setattr(annotation_ui, "SOURCE_PDF_DIR", source_dir)
    annotation_ui.app.testing = True

    # Stub the background thread so the test does not actually invoke
    # the subprocess-based OCR runner.
    monkeypatch.setattr(
        annotation_ui.threading,
        "Thread",
        lambda *a, **kw: type(
            "_DummyThread", (), {"start": lambda self: None, "daemon": False}
        )(),
    )

    client = annotation_ui.app.test_client()
    response = client.post(
        "/api/ocr/start",
        data=json.dumps(
            {
                "pdf": "Disputatio_de_Sacra_Scriptura_contra_R_B_LATIN.pdf",
                "page": 1,
                "edition": "whitaker_latin",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 202, response.get_data(as_text=True)
    body = response.get_json()
    assert body["ok"] is True
    assert body["page_id"] == "p0001"
