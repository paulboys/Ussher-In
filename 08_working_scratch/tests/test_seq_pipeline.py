"""Phase 2 tests: ``seq`` propagation and ordering through the pipeline.

Covers:
- translate_segments stores ``seq`` on segment records and writes JSONL in
  ``(page_id, type, seq)`` order.
- polish_translations.group_by_page sorts by ``seq`` (with regex fallback
  for legacy records lacking ``seq``).
- render_interlinear.group_by_page same.
- End-to-end: a "drag-reordered" page payload (line_id order disagrees
  with array order) produces translation/render output in array order.
"""

from __future__ import annotations

import json
from pathlib import Path

import polish_translations as polish
import render_interlinear as render
import translate_segments as ts
from provider_config import default_config
from translation_adapters import AnthropicTranslationAdapter, CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(*, body_array: list[tuple[str, str]], page_id: str = "p0099") -> dict:
    """Build a minimal page payload from (line_id_suffix, text) pairs.

    Array order = caller's order. ``seq`` is stamped per array index so
    downstream consumers must honor it instead of the line_id suffix.
    """
    body = []
    for idx, (lid_suffix, text) in enumerate(body_array, start=1):
        body.append({
            "page_id": page_id,
            "region": "body",
            "line_id": f"{page_id}_body_{lid_suffix}",
            "seq": idx,
            "text_gold": text,
            "text_ocr_original": text,
            "marker_id": "",
            "markers": [],
            "review_status": "locked",
            "reviewer": "tester",
            "notes": "",
        })
    return {
        "page_id": page_id,
        "part": "part1",
        "source_pdf": "00_source_pdf/sample.pdf",
        "page_num": int(page_id[1:]),
        "edition": "1687_second",
        "regions": {
            "header": [],
            "body": body,
            "marginalia": [],
            "catchword": [],
        },
        "footnotes": [],
        "meta": {
            "annotation_status": "draft",
            "review_status": "locked",
            "reviewer": "tester",
            "notes": "",
        },
    }


def _adapter(translations: dict[str, dict]) -> AnthropicTranslationAdapter:
    def runner(argv, stdin, timeout):
        return CommandResult(stdout=json.dumps({"translations": translations}))
    return AnthropicTranslationAdapter(
        default_config().get("anthropic"), command_runner=runner
    )


# ---------------------------------------------------------------------------
# translate_segments: seq is carried into segment records
# ---------------------------------------------------------------------------


def test_translate_page_carries_seq_into_segment_record():
    # Drag-style: l0003 first, l0001 second, l0002 last; seq matches array.
    payload = _make_payload(body_array=[
        ("l0003", "Gamma."),
        ("l0001", "Alpha."),
        ("l0002", "Beta."),
    ])
    canned = {
        f"p0099_body_{lid}": {"english": f"EN_{lid}.", "notes": "", "uncertain": False}
        for lid in ("l0001", "l0002", "l0003")
    }
    adapter = _adapter(canned)
    existing: dict[str, dict] = {}
    log = ts.translate_page(
        payload,
        adapter=adapter,
        existing_segments=existing,
        lexicon_profile="auto",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-02T00:00:00Z",
    )
    assert log["status"] == "ok"
    # Each segment carries the seq from its source line (NOT the line_id suffix).
    assert existing["seg_p0099_body_l0003"]["seq"] == 1
    assert existing["seg_p0099_body_l0001"]["seq"] == 2
    assert existing["seg_p0099_body_l0002"]["seq"] == 3


def test_segment_write_key_orders_by_seq_not_segment_id():
    a = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0003", "seq": 1}
    b = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0001", "seq": 2}
    c = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0002", "seq": 3}
    ordered = sorted([b, c, a], key=ts._segment_write_key)
    assert [r["segment_id"] for r in ordered] == [
        "seg_p0001_body_l0003",  # seq=1
        "seg_p0001_body_l0001",  # seq=2
        "seg_p0001_body_l0002",  # seq=3
    ]


def test_segment_write_key_groups_body_before_footnote():
    body = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0001", "seq": 5}
    fn = {"page_id": "p0001", "segment_type": "footnote", "segment_id": "seg_p0001_fn_001", "seq": 1}
    ordered = sorted([fn, body], key=ts._segment_write_key)
    assert ordered[0]["segment_type"] == "body"
    assert ordered[1]["segment_type"] == "footnote"


def test_segment_write_key_legacy_records_without_seq_use_segment_id_tiebreak():
    a = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0002"}
    b = {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0001"}
    ordered = sorted([a, b], key=ts._segment_write_key)
    assert ordered[0]["segment_id"].endswith("l0001")


# ---------------------------------------------------------------------------
# polish_translations: _seq_key
# ---------------------------------------------------------------------------


def test_polish_seq_key_honors_seq_when_present():
    a = {"segment_id": "seg_p0001_body_l0003", "seq": 1}
    b = {"segment_id": "seg_p0001_body_l0001", "seq": 2}
    c = {"segment_id": "seg_p0001_body_l0002", "seq": 3}
    ordered = sorted([b, c, a], key=polish._seq_key)
    assert [r["seq"] for r in ordered] == [1, 2, 3]


def test_polish_seq_key_falls_back_to_regex_when_seq_absent():
    a = {"segment_id": "seg_p0001_body_l0003"}
    b = {"segment_id": "seg_p0001_body_l0001"}
    c = {"segment_id": "seg_p0001_body_l0002"}
    ordered = sorted([a, b, c], key=polish._seq_key)
    assert [r["segment_id"][-5:] for r in ordered] == ["l0001", "l0002", "l0003"]


def test_polish_group_by_page_sorts_body_by_seq():
    segs = [
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0001", "seq": 3},
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0002", "seq": 1},
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0003", "seq": 2},
    ]
    pages = polish.group_by_page(segs)
    body_seq = [s["seq"] for s in pages["p0001"]["body"]]
    assert body_seq == [1, 2, 3]


# ---------------------------------------------------------------------------
# render_interlinear: _segment_sort_key
# ---------------------------------------------------------------------------


def test_render_segment_sort_key_honors_seq():
    a = {"segment_id": "seg_p0001_body_l0003", "seq": 1}
    b = {"segment_id": "seg_p0001_body_l0001", "seq": 2}
    ordered = sorted([b, a], key=render._segment_sort_key)
    assert ordered[0]["seq"] == 1


def test_render_group_by_page_sorts_by_seq():
    segs = [
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0001", "seq": 3, "translation_history": []},
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0002", "seq": 1, "translation_history": []},
        {"page_id": "p0001", "segment_type": "body", "segment_id": "seg_p0001_body_l0003", "seq": 2, "translation_history": []},
    ]
    bundles = render.group_by_page(segs)
    assert len(bundles) == 1
    body = bundles[0].body
    assert [s["seq"] for s in body] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Integration: drag → translate → polish-grouping → render-grouping
# all honor array order
# ---------------------------------------------------------------------------


def test_end_to_end_drag_order_propagates_through_pipeline(tmp_path, monkeypatch):
    """Simulate the user dragging body lines so line_id suffix order
    disagrees with reading order. Verify that the final render bundle
    returns body segments in the post-drag order, not the line_id order.
    """
    payload = _make_payload(body_array=[
        ("l0005", "Fifth-by-id, first-by-reading."),
        ("l0001", "First-by-id, second-by-reading."),
        ("l0003", "Third-by-id, third-by-reading."),
    ])
    canned = {
        line["line_id"]: {
            "english": line["text_gold"],
            "notes": "",
            "uncertain": False,
        }
        for line in payload["regions"]["body"]
    }
    adapter = _adapter(canned)

    existing: dict[str, dict] = {}
    log = ts.translate_page(
        payload,
        adapter=adapter,
        existing_segments=existing,
        lexicon_profile="auto",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-02T00:00:00Z",
    )
    assert log["status"] == "ok"

    # Redirect the artifact path to tmp_path
    artifacts_root = tmp_path / "artifacts"
    monkeypatch.setattr(ts, "ARTIFACTS_DIR", artifacts_root)
    out_path = ts.write_segments("part1", existing)
    on_disk_lines = [
        json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    # Written in seq order (= array/reading order)
    assert [r["seq"] for r in on_disk_lines] == [1, 2, 3]
    # ... and that maps back to the line_ids in drag order
    assert [r["segment_id"] for r in on_disk_lines] == [
        "seg_p0099_body_l0005",
        "seg_p0099_body_l0001",
        "seg_p0099_body_l0003",
    ]

    # Render-side grouping respects seq (drag) order
    bundles = render.group_by_page(on_disk_lines)
    body = bundles[0].body
    assert [s["segment_id"] for s in body] == [
        "seg_p0099_body_l0005",
        "seg_p0099_body_l0001",
        "seg_p0099_body_l0003",
    ]

    # Polish-side grouping respects seq (drag) order
    pages = polish.group_by_page(on_disk_lines)
    polished_body = pages["p0099"]["body"]
    assert [s["segment_id"] for s in polished_body] == [
        "seg_p0099_body_l0005",
        "seg_p0099_body_l0001",
        "seg_p0099_body_l0003",
    ]


# ---------------------------------------------------------------------------
# Resume-window seam guard (ch2 p0058/p0059 duplication incident)
# ---------------------------------------------------------------------------


def test_find_seam_clashes_flags_lines_owned_by_another_segment():
    """A narrow resume window re-segments lines an earlier run's cross-page
    sentence already absorbed. The guard must name both the new unit and the
    owning segment so the operator widens the range."""
    from types import SimpleNamespace
    from translate_sentences import find_seam_clashes

    existing = {
        "seg_p0058_s0003": {
            "segment_type": "body",
            "source_line_ids": ["p0058_body_l0021", "p0059_body_l0004"],
        },
    }
    fresh_dup = SimpleNamespace(
        sentence_id="seg_p0059_s0001",
        source_line_ids=["p0059_body_l0004"],  # already absorbed upstream
    )
    clashes = find_seam_clashes([fresh_dup], existing)
    assert clashes == [("seg_p0059_s0001", ["seg_p0058_s0003"])]


def test_find_seam_clashes_ignores_identical_ids_and_footnotes():
    """Normal resume (same range) regenerates identical unit ids -- not a
    clash. Footnote records never own body lines."""
    from types import SimpleNamespace
    from translate_sentences import find_seam_clashes

    existing = {
        "seg_p0059_s0001": {
            "segment_type": "body",
            "source_line_ids": ["p0059_body_l0009"],
        },
        "seg_p0059_fn_001": {
            "segment_type": "footnote",
            "source_line_ids": ["p0059_body_l0009"],  # pathological; ignored
        },
    }
    same_unit = SimpleNamespace(
        sentence_id="seg_p0059_s0001",
        source_line_ids=["p0059_body_l0009"],
    )
    assert find_seam_clashes([same_unit], existing) == []
