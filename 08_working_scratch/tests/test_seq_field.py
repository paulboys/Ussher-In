"""Tests for the ``seq`` ordering field.

Covers:
- annotation_ui server stamps ``seq`` from array order on save
- backfill_seq.stamp_seq is idempotent and respects array order
- backfill_seq CLI ``--check`` flag
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


def _payload(page_id: str = "p0050") -> dict:
    return {
        "page_id": page_id,
        "part": "part1",
        "source_pdf": "00_source_pdf/sample.pdf",
        "page_num": 50,
        "regions": {
            "header": [
                {
                    "page_id": page_id,
                    "region": "header",
                    "line_id": f"{page_id}_header_l0001",
                    "text_gold": "Header",
                    "review_status": "draft",
                }
            ],
            "body": [
                {
                    "page_id": page_id,
                    "region": "body",
                    "line_id": f"{page_id}_body_l0001",
                    "text_gold": "Alpha",
                    "review_status": "draft",
                    "markers": [],
                },
                {
                    "page_id": page_id,
                    "region": "body",
                    "line_id": f"{page_id}_body_l0002",
                    "text_gold": "Beta",
                    "review_status": "draft",
                    "markers": [],
                },
                {
                    "page_id": page_id,
                    "region": "body",
                    "line_id": f"{page_id}_body_l0003",
                    "text_gold": "Gamma",
                    "review_status": "draft",
                    "markers": [],
                },
            ],
            "marginalia": [],
            "catchword": [],
        },
        "footnotes": [
            {
                "footnote_id": f"{page_id}_fn_001",
                "page_id": page_id,
                "marker_number": 1,
                "body_line_id": f"{page_id}_body_l0001",
                "text_gold": "fn 1",
                "kind": "citation",
                "review_status": "draft",
            },
            {
                "footnote_id": f"{page_id}_fn_002",
                "page_id": page_id,
                "marker_number": 2,
                "body_line_id": f"{page_id}_body_l0002",
                "text_gold": "fn 2",
                "kind": "citation",
                "review_status": "draft",
            },
        ],
        "meta": {
            "annotation_status": "draft",
            "review_status": "draft",
            "reviewer": "",
            "notes": "",
        },
    }


# ---------------------------------------------------------------------------
# Backfill: pure helper
# ---------------------------------------------------------------------------


def test_stamp_seq_assigns_dense_1_based_per_region():
    from backfill_seq import stamp_seq

    p = _payload()
    changed = stamp_seq(p)
    assert changed > 0  # nothing had seq before
    assert [l["seq"] for l in p["regions"]["body"]] == [1, 2, 3]
    assert p["regions"]["header"][0]["seq"] == 1
    assert [fn["seq"] for fn in p["footnotes"]] == [1, 2]


def test_stamp_seq_is_idempotent():
    from backfill_seq import stamp_seq

    p = _payload()
    stamp_seq(p)
    changed_second = stamp_seq(p)
    assert changed_second == 0


def test_stamp_seq_follows_array_order_not_line_id_suffix():
    """If the user dragged l0003 above l0001, seq must follow array order."""
    from backfill_seq import stamp_seq

    p = _payload()
    body = p["regions"]["body"]
    # Simulate drag: move l0003 to position 0
    body.insert(0, body.pop(2))
    # line_ids are still l0001,l0002,l0003 but in array order [l0003, l0001, l0002]
    assert [l["line_id"][-5:] for l in body] == ["l0003", "l0001", "l0002"]
    stamp_seq(p)
    # seq follows array order, not the numeric suffix
    assert [l["seq"] for l in body] == [1, 2, 3]
    # The line whose line_id ends in l0003 is now seq=1
    assert next(l for l in body if l["line_id"].endswith("l0003"))["seq"] == 1


def test_stamp_seq_empty_regions_safe():
    from backfill_seq import stamp_seq

    p = {"regions": {"body": [], "header": []}, "footnotes": []}
    assert stamp_seq(p) == 0


# ---------------------------------------------------------------------------
# Backfill CLI: --check dry-run
# ---------------------------------------------------------------------------


def test_backfill_cli_check_does_not_modify(tmp_path):
    import backfill_seq

    target = tmp_path / "page_p0050.json"
    p = _payload()
    target.write_text(json.dumps(p), encoding="utf-8")
    rc = backfill_seq.main(["--check", "--paths", str(target)])
    # --check returns nonzero when changes would happen
    assert rc == 1
    # File untouched
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert "seq" not in on_disk["regions"]["body"][0]


def test_backfill_cli_writes_when_not_check(tmp_path):
    import backfill_seq

    target = tmp_path / "page_p0050.json"
    p = _payload()
    target.write_text(json.dumps(p), encoding="utf-8")
    rc = backfill_seq.main(["--paths", str(target)])
    assert rc == 0
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert [l["seq"] for l in on_disk["regions"]["body"]] == [1, 2, 3]
    # Second run finds nothing to do
    rc2 = backfill_seq.main(["--paths", str(target)])
    assert rc2 == 0


# ---------------------------------------------------------------------------
# Server-side stamping via /api/page/<page_id>
# ---------------------------------------------------------------------------

pytest.importorskip("flask")


@pytest.fixture
def annotation_app(tmp_path, monkeypatch):
    target = tmp_path / "page_p0050.json"
    target.write_text(json.dumps(_payload()), encoding="utf-8")

    import annotation_ui

    monkeypatch.setattr(annotation_ui, "ANNOTATIONS_DIR", tmp_path)
    annotation_ui.app.testing = True
    return annotation_ui.app, tmp_path


def test_save_stamps_seq_from_array_order(annotation_app):
    app, dirpath = annotation_app
    payload = _payload()
    # Drag-style: reorder body so l0003 is first
    body = payload["regions"]["body"]
    body.insert(0, body.pop(2))
    # Send WITHOUT seq fields — server should stamp them
    client = app.test_client()
    res = client.post(
        "/api/page/p0050",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 200, res.get_data(as_text=True)

    saved = json.loads((dirpath / "page_p0050.json").read_text(encoding="utf-8"))
    saved_body = saved["regions"]["body"]
    assert [l["seq"] for l in saved_body] == [1, 2, 3]
    # The line currently at position 0 has line_id ending in l0003 (drag preserved id)
    assert saved_body[0]["line_id"].endswith("l0003")
    assert saved_body[0]["seq"] == 1


def test_save_overrides_inconsistent_client_seq(annotation_app):
    """If the client sends seq values that don't match array order, the
    server stamps from array order. Ordering authority is the array."""
    app, dirpath = annotation_app
    payload = _payload()
    # Sabotage seq values
    for idx, line in enumerate(payload["regions"]["body"]):
        line["seq"] = 99 - idx
    client = app.test_client()
    res = client.post(
        "/api/page/p0050",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 200

    saved = json.loads((dirpath / "page_p0050.json").read_text(encoding="utf-8"))
    assert [l["seq"] for l in saved["regions"]["body"]] == [1, 2, 3]
