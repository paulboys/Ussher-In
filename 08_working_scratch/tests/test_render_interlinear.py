"""Tests for render_interlinear.

The renderer is read-only and consumes the JSONL artifact written by
translate_segments. We exercise it with synthetic in-memory bundles so
the test suite stays portable and does not depend on the live artifact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import render_interlinear as ri


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _body_seg(line_no: int, latin: str, english: str) -> dict:
    seg_id = f"seg_p0036_body_l{line_no:04d}"
    return {
        "segment_id": seg_id,
        "page_id": "p0036",
        "segment_type": "body",
        "latin_text": latin,
        "translation_history": [
            {
                "version": 1,
                "stage": "machine_draft",
                "timestamp": "2026-05-01T00:00:00Z",
                "english": english,
            }
        ],
        "markers": [],
    }


def _fn_seg(num: int, marker_id: str, body_line_no: int,
            latin: str, english: str) -> dict:
    seg_id = f"seg_p0036_fn_{num:03d}"
    return {
        "segment_id": seg_id,
        "page_id": "p0036",
        "segment_type": "footnote",
        "latin_text": latin,
        "marker_id": marker_id,
        "body_segment_id": f"seg_p0036_body_l{body_line_no:04d}",
        "translation_history": [
            {
                "version": 1,
                "stage": "machine_draft",
                "timestamp": "2026-05-01T00:00:00Z",
                "english": english,
            }
        ],
        "markers": [],
    }


@pytest.fixture()
def page_bundle() -> ri.PageBundle:
    body = [
        _body_seg(
            1,
            "Hinc Arnobius^y “ Tam velociter currit sermo ejus ut,",
            'Hence Arnobius^y: "So swiftly does his word run that,',
        ),
        _body_seg(
            2,
            "cum per tot millia annorum in sola Judæa notus fuerit",
            "though for so many thousands of years God had been known in Judea alone,",
        ),
    ]
    footnotes = [
        _fn_seg(1, "y", 1, "in Psalm. 147.", "On Psalm 147."),
    ]
    return ri.PageBundle(page_id="p0036", body=body, footnotes=footnotes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_latest_english_returns_last_history_entry():
    seg = {
        "translation_history": [
            {"english": "v1"},
            {"english": "v2"},
            {"english": "v3"},
        ]
    }
    assert ri.latest_english(seg) == "v3"


def test_latest_english_handles_empty_history():
    assert ri.latest_english({"translation_history": []}) == ""
    assert ri.latest_english({}) == ""


def test_group_by_page_sorts_body_then_footnotes_in_order():
    segments = [
        _fn_seg(2, "z", 2, "fn2 LA", "fn2 EN"),
        _body_seg(2, "body 2 LA", "body 2 EN"),
        _fn_seg(1, "y", 1, "fn1 LA", "fn1 EN"),
        _body_seg(1, "body 1 LA", "body 1 EN"),
    ]
    bundles = ri.group_by_page(segments)
    assert len(bundles) == 1
    bundle = bundles[0]
    assert [s["segment_id"] for s in bundle.body] == [
        "seg_p0036_body_l0001",
        "seg_p0036_body_l0002",
    ]
    assert [s["segment_id"] for s in bundle.footnotes] == [
        "seg_p0036_fn_001",
        "seg_p0036_fn_002",
    ]


# ---------------------------------------------------------------------------
# Caret-to-anchor transformation
# ---------------------------------------------------------------------------


def test_carets_to_anchors_html_links_to_footnote_segment(page_bundle):
    fn_lookup = ri._fn_lookup_for_page(page_bundle.footnotes)
    out = ri._carets_to_anchors(
        "Hinc Arnobius^y “",
        page_id="p0036",
        fn_id_for_marker=fn_lookup,
        fmt="html",
    )
    assert "<sup" in out
    assert 'href="#fn-seg_p0036_fn_001"' in out
    # backref id present for footnote-to-body return navigation.
    assert 'id="fnref-p0036-y"' in out
    # Caret consumed.
    assert "^y" not in out


def test_carets_to_anchors_falls_back_when_marker_unknown():
    out = ri._carets_to_anchors(
        "Lorem^q ipsum",
        page_id="p0036",
        fn_id_for_marker={},  # no footnote registered
        fmt="html",
    )
    # Marker still rendered as a sup, but with no link target.
    assert "<sup" in out
    assert "href" not in out
    assert ">q<" in out


def test_carets_to_anchors_markdown_uses_raw_html_supers(page_bundle):
    fn_lookup = ri._fn_lookup_for_page(page_bundle.footnotes)
    out = ri._carets_to_anchors(
        "Hinc Arnobius^y “",
        page_id="p0036",
        fn_id_for_marker=fn_lookup,
        fmt="markdown",
    )
    # Pandoc passes raw HTML through, so emitting <sup> directly is
    # the simplest cross-target approach.
    assert "<sup" in out
    assert 'href="#fn-seg_p0036_fn_001"' in out


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------


def test_render_page_markdown_includes_body_and_footnotes(page_bundle):
    md = ri.render_page_markdown(page_bundle)
    assert "# Page p0036" in md
    # Body shows up with both languages.
    assert "**LA**" in md and "**EN**" in md
    # Latin carries the backref id (so the footnote can return here).
    assert 'Hinc Arnobius<sup id="fnref-p0036-y">' in md
    # English carries the link to the footnote, but NOT a duplicate id
    # (HTML id attributes must be unique within a document).
    assert 'Hence Arnobius<sup><a href="#fn-seg_p0036_fn_001">y</a>' in md
    # Footnote section present with backref.
    assert "## Footnotes" in md
    assert 'id="fn-seg_p0036_fn_001"' in md
    assert "On Psalm 147." in md
    assert "in Psalm. 147." in md


def test_render_page_html_is_self_contained_and_links_resolve(page_bundle):
    out = ri.render_page_html(page_bundle)
    assert out.startswith("<!DOCTYPE html>")
    assert "<title>Ussher Antiquitates — p0036</title>" in out
    # Body anchor links to footnote anchor by id.
    assert 'href="#fn-seg_p0036_fn_001"' in out
    assert 'id="fn-seg_p0036_fn_001"' in out
    # Footnote backref points to the body anchor id.
    assert 'href="#fnref-p0036-y"' in out
    assert 'id="fnref-p0036-y"' in out
    # The plain caret never leaks into rendered output.
    assert "^y" not in out
    # Latin styled distinctly.
    assert 'class="la"' in out and 'class="en"' in out


def test_render_pages_writes_files_to_part_subdir(tmp_path, monkeypatch):
    # Build a tiny synthetic part artifact.
    part = "demo"
    art_dir = tmp_path / "in" / part
    art_dir.mkdir(parents=True)
    record_lines = []
    for seg in (
        _body_seg(1, "alpha^y", "Alpha^y"),
        _fn_seg(1, "y", 1, "fn LA", "fn EN"),
    ):
        record_lines.append(__import__("json").dumps(seg))
    (art_dir / "segments_with_translations.jsonl").write_text(
        "\n".join(record_lines) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path / "in")

    out_dir = tmp_path / "out"
    written = ri.render_pages(
        part=part,
        out_dir=out_dir,
        fmt="html",
        start_page=None,
        end_page=None,
    )
    assert len(written) == 1
    assert written[0].name == "p0036_interlinear.html"
    assert written[0].parent == out_dir / part
    content = written[0].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_render_pages_respects_page_range(tmp_path, monkeypatch):
    part = "demo"
    art_dir = tmp_path / "in" / part
    art_dir.mkdir(parents=True)
    seg_a = _body_seg(1, "a", "A")
    seg_a["page_id"] = "p0010"
    seg_a["segment_id"] = "seg_p0010_body_l0001"
    seg_b = _body_seg(1, "b", "B")
    seg_b["page_id"] = "p0050"
    seg_b["segment_id"] = "seg_p0050_body_l0001"
    import json as _json
    (art_dir / "segments_with_translations.jsonl").write_text(
        _json.dumps(seg_a) + "\n" + _json.dumps(seg_b) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path / "in")

    out_dir = tmp_path / "out"
    written = ri.render_pages(
        part=part,
        out_dir=out_dir,
        fmt="markdown",
        start_page=20,
        end_page=99,
    )
    # Only p0050 falls in [20, 99].
    assert [p.name for p in written] == ["p0050_interlinear.md"]


def test_render_pages_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError):
        ri.render_pages(
            part="x",
            out_dir=tmp_path,
            fmt="rtf",  # not in FORMATS
            start_page=None,
            end_page=None,
        )


def test_load_segments_missing_artifact_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        ri.load_segments("nonexistent")


# ---------------------------------------------------------------------------
# Polished translation: Reading section
# ---------------------------------------------------------------------------


def _polished_artifact(english: str) -> dict:
    return {
        "page_id": "p0036",
        "stage": "polished",
        "version": 1,
        "timestamp": "2026-05-01T16:00:00Z",
        "model": "claude-opus-4-6",
        "lexicon_profile": "auto",
        "source_versions": {"seg_p0036_body_l0001": 4},
        "english": english,
        "warnings": [],
    }


def test_render_page_markdown_includes_reading_section_when_polished_present(page_bundle):
    page_bundle.polished = _polished_artifact(
        "Hence Arnobius^y declared that the gospel ran swiftly across the world."
    )
    md = ri.render_page_markdown(page_bundle)
    assert "## Interlinear" in md
    assert "## Reading" in md
    # Polished prose appears under Reading with caret converted to a
    # link-only sup (no duplicate id attr from the polished line).
    assert "Hence Arnobius<sup>" in md.split("## Reading", 1)[1]
    # The Reading caret links to the same footnote target.
    assert 'href="#fn-seg_p0036_fn_001"' in md


def test_render_page_markdown_polished_caret_has_no_duplicate_backref_id(page_bundle):
    page_bundle.polished = _polished_artifact("Polished prose with anchor^y here.")
    md = ri.render_page_markdown(page_bundle)
    # The fnref backref id must appear exactly ONCE (on the Latin
    # interlinear line); not in the polished prose.
    assert md.count('id="fnref-p0036-y"') == 1


def test_render_page_markdown_skips_reading_when_no_polished(page_bundle):
    page_bundle.polished = None
    md = ri.render_page_markdown(page_bundle)
    assert "## Reading" not in md
    assert "## Interlinear" in md


def test_render_page_markdown_reading_only_omits_interlinear(page_bundle):
    page_bundle.polished = _polished_artifact("Just the reading^y.")
    md = ri.render_page_markdown(page_bundle, reading_only=True)
    assert "## Interlinear" not in md
    assert "## Footnotes" not in md
    assert "## Reading" in md


def test_render_page_markdown_no_reading_flag_suppresses_section(page_bundle):
    page_bundle.polished = _polished_artifact("Polished prose^y.")
    md = ri.render_page_markdown(page_bundle, include_reading=False)
    assert "## Reading" not in md
    assert "## Interlinear" in md


def test_render_page_html_includes_reading_section_when_polished_present(page_bundle):
    page_bundle.polished = _polished_artifact(
        "Hence Arnobius^y declared that the gospel ran swiftly."
    )
    out = ri.render_page_html(page_bundle)
    assert "<h2>Interlinear</h2>" in out
    assert "<h2>Reading</h2>" in out
    assert '<section class="reading">' in out
    # Each polished paragraph wrapped in <p>.
    assert "<p>" in out.split("Reading", 1)[1]
    # No second copy of the body's backref id ends up in the polished prose.
    assert out.count('id="fnref-p0036-y"') == 1


def test_render_page_html_paragraph_breaks_split_on_blank_lines(page_bundle):
    page_bundle.polished = _polished_artifact(
        "First paragraph^y here.\n\nSecond paragraph follows."
    )
    out = ri.render_page_html(page_bundle)
    reading = out.split("Reading", 1)[1]
    # Two distinct <p> blocks under the reading section.
    assert reading.count("<p>") >= 2


def test_load_polished_returns_none_when_artifact_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path / "03_segmented_text")
    assert ri.load_polished("part1", "p0036") is None


def test_load_polished_reads_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path / "03_segmented_text")
    pdir = tmp_path / "03_segmented_text" / "part1" / "polished"
    pdir.mkdir(parents=True)
    (pdir / "p0036.json").write_text(
        '{"page_id": "p0036", "english": "x^y"}', encoding="utf-8"
    )
    artifact = ri.load_polished("part1", "p0036")
    assert artifact == {"page_id": "p0036", "english": "x^y"}


def test_group_by_page_attaches_polished_when_part_supplied(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "ARTIFACTS_DIR", tmp_path / "03_segmented_text")
    pdir = tmp_path / "03_segmented_text" / "part1" / "polished"
    pdir.mkdir(parents=True)
    (pdir / "p0036.json").write_text(
        '{"page_id": "p0036", "english": "polished^y here"}', encoding="utf-8"
    )
    bundles = ri.group_by_page(
        [_body_seg(1, "alpha^y", "Alpha^y"), _fn_seg(1, "y", 1, "fn", "fn")],
        part="part1",
    )
    assert bundles[0].polished is not None
    assert bundles[0].polished["english"] == "polished^y here"



# ---------------------------------------------------------------------------
# Per-line anchor ids (for deep-linking comments to body lines)
# ---------------------------------------------------------------------------


def test_render_page_markdown_includes_per_line_anchors(page_bundle):
    md = ri.render_page_markdown(page_bundle)
    # Each body line gets its own id="line-<page>-l<NNNN>".
    assert 'id="line-p0036-l0001"' in md
    assert 'id="line-p0036-l0002"' in md


def test_render_page_html_row_carries_line_id(page_bundle):
    out = ri.render_page_html(page_bundle)
    # The row div carries the id so anchor links jump to the LA/EN pair.
    assert '<div class="row" id="line-p0036-l0001">' in out
    assert '<div class="row" id="line-p0036-l0002">' in out


def test_line_anchor_id_helper_returns_blank_for_unrecognized_segment():
    assert ri._line_anchor_id({"segment_id": "seg_p0036_fn_001"}, "p0036") == ""
    assert ri._line_anchor_id({}, "p0036") == ""

