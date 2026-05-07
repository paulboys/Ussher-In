"""Tests for the trilinear side-by-side renderer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

tr = pytest.importorskip(
    "ab_trilinear",
    reason="A/B helper scripts are not present in this branch.",
)


def _seg_record(seg_id: str, seq: int, latin: str, english: str) -> dict:
    return {
        "segment_id": seg_id,
        "page_id": "p9999",
        "segment_type": "body",
        "latin_text": latin,
        "markers": [],
        "translation_history": [
            {"version": 1, "stage": "machine_draft", "english": english,
             "notes": "", "uncertain": False, "model": "claude-opus-4-7",
             "lexicon_profile": "auto", "source_unit_id": seg_id}
        ],
        "final_english": "",
        "translation_status": "machine_draft",
        "seq": seq,
    }


def _write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in records:
            h.write(json.dumps(r) + "\n")


@pytest.fixture
def two_runs(tmp_path: Path) -> tuple[Path, Path]:
    a = tmp_path / "v0" / "run01" / "segments_with_translations.jsonl"
    b = tmp_path / "v2" / "run01" / "segments_with_translations.jsonl"
    _write(a, [
        _seg_record("seg_p9999_body_l0001", 1, "Hinc Arnobius dixit.", "From here Arnobius said."),
        _seg_record("seg_p9999_body_l0002", 2, "In quibus.",          "In which."),
    ])
    _write(b, [
        _seg_record("seg_p9999_body_l0001", 1, "Hinc Arnobius dixit.", "Hence Arnobius spoke."),
        _seg_record("seg_p9999_body_l0002", 2, "In quibus.",          "Among these."),
    ])
    return a, b


def test_load_segments_reads_latest_english(tmp_path: Path):
    rec = _seg_record("seg_x", 1, "L", "first")
    rec["translation_history"].append(
        {"version": 2, "stage": "polished", "english": "second",
         "notes": "", "uncertain": False, "model": "x",
         "lexicon_profile": "auto", "source_unit_id": "seg_x"}
    )
    p = tmp_path / "a.jsonl"
    _write(p, [rec])
    segs = tr.load_segments(p)
    assert segs["seg_x"].english == "second"
    assert segs["seg_x"].latin == "L"


def test_load_segments_falls_back_to_final_english(tmp_path: Path):
    rec = _seg_record("seg_y", 1, "L", "")
    rec["final_english"] = "polished prose"
    p = tmp_path / "a.jsonl"
    _write(p, [rec])
    assert tr.load_segments(p)["seg_y"].english == "polished prose"


def test_render_emits_one_block_per_segment_in_seq_order(two_runs):
    a_path, b_path = two_runs
    a = tr.load_segments(a_path)
    b = tr.load_segments(b_path)
    md = tr.render_markdown(a, b, page="p9999", a_label="v0", b_label="v2")
    # Header
    assert "# Trilinear — p9999" in md
    # One block per segment, each carrying Latin + both versions.
    assert "`seg_p9999_body_l0001`" in md
    assert "`seg_p9999_body_l0002`" in md
    # Trilinear order: latin first, then v0, then v2 within each block.
    block = md.split("`seg_p9999_body_l0001`", 1)[1].split("`seg_p9999_body_l0002`", 1)[0]
    latin_pos = block.find("**Latin:**")
    v0_pos = block.find("**v0:**")
    v2_pos = block.find("**v2:**")
    assert 0 <= latin_pos < v0_pos < v2_pos
    # Both renderings present and distinct.
    assert "From here Arnobius said." in block
    assert "Hence Arnobius spoke." in block


def test_render_handles_one_sided_segment(tmp_path: Path):
    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    _write(a_path, [_seg_record("seg_only_a", 1, "L1", "A only")])
    _write(b_path, [_seg_record("seg_only_b", 2, "L2", "B only")])
    a = tr.load_segments(a_path)
    b = tr.load_segments(b_path)
    md = tr.render_markdown(a, b, page="p9999", a_label="v0", b_label="v2")
    # Both segments rendered; missing side gets a placeholder.
    assert "seg_only_a" in md and "seg_only_b" in md
    assert "_(missing)_" in md


def test_render_flags_latin_disagreement(tmp_path: Path):
    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    _write(a_path, [_seg_record("seg_x", 1, "Latin v0 form.", "x")])
    _write(b_path, [_seg_record("seg_x", 1, "Latin v2 form.", "y")])
    md = tr.render_markdown(
        tr.load_segments(a_path),
        tr.load_segments(b_path),
        page="p9999", a_label="v0", b_label="v2",
    )
    assert "disagree on Latin" in md


def test_main_writes_output(tmp_path: Path, two_runs):
    a_path, b_path = two_runs
    out = tmp_path / "tri.md"
    rc = tr.main([
        "--a", str(a_path),
        "--b", str(b_path),
        "--output", str(out),
        "--a-label", "v0",
        "--b-label", "v2",
        "--page", "p9999",
    ])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "Trilinear" in text
    assert "seg_p9999_body_l0001" in text


def test_infer_page_walks_parents(tmp_path: Path):
    fake = tmp_path / "ab" / "p0039" / "v0" / "run01" / "segments_with_translations.jsonl"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text("", encoding="utf-8")
    assert tr._infer_page(fake) == "p0039"


def test_body_segments_precede_footnotes_regardless_of_seq(tmp_path: Path):
    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"

    def _fn(seg_id: str, seq: int, latin: str, english: str) -> dict:
        rec = _seg_record(seg_id, seq, latin, english)
        rec["segment_type"] = "footnote"
        return rec

    # Footnote seq numbers are interleaved with body seq numbers on the
    # printed page, but the trilinear must group body first then footnotes.
    records_a = [
        _seg_record("seg_p9999_body_l0001", 1, "Body line one.", "Body one A"),
        _fn("seg_p9999_fn_001", 2, "Footnote one.", "Footnote one A"),
        _seg_record("seg_p9999_body_l0002", 3, "Body line two.", "Body two A"),
        _fn("seg_p9999_fn_002", 4, "Footnote two.", "Footnote two A"),
    ]
    records_b = [
        _seg_record("seg_p9999_body_l0001", 1, "Body line one.", "Body one B"),
        _fn("seg_p9999_fn_001", 2, "Footnote one.", "Footnote one B"),
        _seg_record("seg_p9999_body_l0002", 3, "Body line two.", "Body two B"),
        _fn("seg_p9999_fn_002", 4, "Footnote two.", "Footnote two B"),
    ]
    _write(a_path, records_a)
    _write(b_path, records_b)

    md = tr.render_markdown(
        tr.load_segments(a_path),
        tr.load_segments(b_path),
        page="p9999", a_label="v0", b_label="v2",
    )

    body1 = md.find("seg_p9999_body_l0001")
    body2 = md.find("seg_p9999_body_l0002")
    fn1 = md.find("seg_p9999_fn_001")
    fn2 = md.find("seg_p9999_fn_002")
    fn_section = md.find("## Footnotes")

    # Body block ordered, footnote block ordered, body all before footnotes.
    assert 0 <= body1 < body2 < fn_section < fn1 < fn2
    assert "## Body" in md
