"""Tests for the polish_translations runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import polish_translations as pt
from translation_adapters import (
    AnthropicTranslationAdapter,
    CommandResult,
)
from provider_config import default_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _segments_jsonl(tmp_path: Path, *, body_english: str = 'Hence Arnobius^y: "swiftly."') -> Path:
    """Build a minimal segments JSONL fixture for one page (p0036)."""
    part_dir = tmp_path / "03_segmented_text" / "part1"
    part_dir.mkdir(parents=True)
    path = part_dir / "segments_with_translations.jsonl"
    body = {
        "segment_id": "seg_p0036_body_l0001",
        "page_id": "p0036",
        "segment_type": "body",
        "latin_text": "Hinc Arnobius^y velociter.",
        "translation_history": [
            {
                "version": 4,
                "stage": "machine_draft",
                "timestamp": "2026-05-01T15:27:01Z",
                "english": body_english,
                "notes": "",
                "uncertain": False,
                "model": "claude-opus-4-6",
                "lexicon_profile": "auto",
                "source_unit_id": "p0036_body_l0001",
            }
        ],
        "final_english": "",
        "translation_status": "machine_draft",
        "markers": [
            {
                "marker_id": "y",
                "char_offset": 13,
                "footnote_segment_id": "seg_p0036_fn_001",
            }
        ],
    }
    fn = {
        "segment_id": "seg_p0036_fn_001",
        "page_id": "p0036",
        "segment_type": "footnote",
        "latin_text": "in Psalm. 147.",
        "translation_history": [
            {
                "version": 1,
                "stage": "machine_draft",
                "timestamp": "2026-05-01T15:27:01Z",
                "english": "On Psalm 147.",
                "notes": "",
                "uncertain": False,
                "model": "claude-opus-4-6",
                "lexicon_profile": "auto",
                "source_unit_id": "p0036_fn_001",
            }
        ],
        "final_english": "",
        "translation_status": "machine_draft",
        "body_segment_id": "seg_p0036_body_l0001",
        "marker_id": "y",
        "markers": [],
    }
    with path.open("w", encoding="utf-8") as h:
        h.write(json.dumps(body, ensure_ascii=False) + "\n")
        h.write(json.dumps(fn, ensure_ascii=False) + "\n")
    return path


def _make_adapter(stdout: str) -> AnthropicTranslationAdapter:
    """Build an adapter whose CLI returns a fixed stdout string."""
    def fake_runner(argv, stdin, timeout):
        return CommandResult(stdout=stdout)

    return AnthropicTranslationAdapter(
        default_config().get("anthropic"),
        command_runner=fake_runner,
    )


# ---------------------------------------------------------------------------
# Page-payload helpers
# ---------------------------------------------------------------------------


def test_collect_required_markers_returns_distinct_in_printed_order():
    body = [
        {"latin_text": "alpha^a beta^b"},
        {"latin_text": "gamma^c delta^a"},  # ^a repeats — keep first occurrence
    ]
    assert pt.collect_required_markers(body) == ["a", "b", "c"]


def test_build_body_units_includes_latest_english_with_carets():
    body = [
        {
            "segment_id": "seg_p0036_body_l0001",
            "latin_text": "Hinc Arnobius^y",
            "translation_history": [
                {"version": 1, "english": "early"},
                {"version": 2, "english": "Hence Arnobius^y"},
            ],
        }
    ]
    units = pt.build_body_units(body)
    assert units == [
        {
            "segment_id": "seg_p0036_body_l0001",
            "latin_text": "Hinc Arnobius^y",
            "literal_english": "Hence Arnobius^y",
        }
    ]


def test_build_footnote_glosses_uses_latest_english_and_marker():
    fn_segs = [
        {
            "segment_id": "seg_p0036_fn_001",
            "marker_id": "y",
            "translation_history": [{"version": 1, "english": "On Psalm 147."}],
        }
    ]
    out = pt.build_footnote_glosses(fn_segs)
    assert out == [
        {"marker_id": "y", "segment_id": "seg_p0036_fn_001", "english": "On Psalm 147."}
    ]


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------


def test_validate_polished_output_accepts_each_required_marker_once():
    warnings = pt.validate_polished_output(
        text="Hence Arnobius^y said swiftly.",
        required_markers=["y"],
    )
    assert warnings == []


def test_validate_polished_output_raises_when_marker_missing():
    with pytest.raises(pt.PolishValidationError):
        pt.validate_polished_output(
            text="Hence Arnobius said swiftly.",
            required_markers=["y"],
        )


def test_validate_polished_output_raises_when_marker_duplicated():
    with pytest.raises(pt.PolishValidationError):
        pt.validate_polished_output(
            text="Hence^y Arnobius^y said swiftly.",
            required_markers=["y"],
        )


def test_validate_polished_output_warns_on_unexpected_marker():
    warnings = pt.validate_polished_output(
        text="Hence Arnobius^y said^z swiftly.",
        required_markers=["y"],
    )
    assert any("'^z'" in w for w in warnings)


def test_validate_polished_output_raises_on_empty():
    with pytest.raises(pt.PolishValidationError):
        pt.validate_polished_output(text="   ", required_markers=[])


# ---------------------------------------------------------------------------
# Full polish_page orchestration
# ---------------------------------------------------------------------------


def _patch_artifacts_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pt, "ARTIFACTS_DIR", tmp_path / "03_segmented_text")


def test_polish_page_dry_run_does_not_call_adapter(monkeypatch, tmp_path):
    _segments_jsonl(tmp_path)
    _patch_artifacts_dir(monkeypatch, tmp_path)
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0036",
        body_segments=pages["p0036"]["body"],
        fn_segments=pages["p0036"]["footnotes"],
        adapter=None,
        lexicon_profile="minimal",
        extra_context=None,
        force=False,
        dry_run=True,
        timestamp="2026-05-01T16:00:00Z",
        part="part1",
    )
    assert log["status"] == "dry_run"
    assert log["required_markers"] == ["y"]
    assert log["prompt_chars"] > 0
    # No artifact written.
    assert pt.load_polished_artifact("part1", "p0036") is None


def test_polish_page_writes_artifact_with_required_markers(monkeypatch, tmp_path):
    _segments_jsonl(tmp_path)
    _patch_artifacts_dir(monkeypatch, tmp_path)
    adapter = _make_adapter(
        "Hence Arnobius^y declared that the gospel ran swiftly across the world."
    )
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0036",
        body_segments=pages["p0036"]["body"],
        fn_segments=pages["p0036"]["footnotes"],
        adapter=adapter,
        lexicon_profile="minimal",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T16:00:00Z",
        part="part1",
    )
    assert log["status"] == "ok"
    assert log["version"] == 1
    artifact = pt.load_polished_artifact("part1", "p0036")
    assert artifact is not None
    assert artifact["page_id"] == "p0036"
    assert artifact["stage"] == "polished"
    assert artifact["version"] == 1
    assert "^y" in artifact["english"]
    assert artifact["source_versions"] == {"seg_p0036_body_l0001": 4}


def test_polish_page_skips_when_artifact_exists(monkeypatch, tmp_path):
    _segments_jsonl(tmp_path)
    _patch_artifacts_dir(monkeypatch, tmp_path)
    # Pre-write an artifact.
    pt.write_polished_artifact("part1", "p0036", {"version": 1, "english": "x^y"})
    adapter = _make_adapter("FRESH^y")
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0036",
        body_segments=pages["p0036"]["body"],
        fn_segments=pages["p0036"]["footnotes"],
        adapter=adapter,
        lexicon_profile="minimal",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T17:00:00Z",
        part="part1",
    )
    assert log["status"] == "skipped_artifact_exists"
    artifact = pt.load_polished_artifact("part1", "p0036")
    assert artifact["english"] == "x^y"  # untouched


def test_polish_page_force_bumps_version(monkeypatch, tmp_path):
    _segments_jsonl(tmp_path)
    _patch_artifacts_dir(monkeypatch, tmp_path)
    pt.write_polished_artifact(
        "part1", "p0036", {"version": 1, "english": "old^y"}
    )
    adapter = _make_adapter("Polished prose with anchor^y inserted.")
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0036",
        body_segments=pages["p0036"]["body"],
        fn_segments=pages["p0036"]["footnotes"],
        adapter=adapter,
        lexicon_profile="minimal",
        extra_context=None,
        force=True,
        dry_run=False,
        timestamp="2026-05-01T18:00:00Z",
        part="part1",
    )
    assert log["status"] == "ok"
    assert log["version"] == 2
    assert pt.load_polished_artifact("part1", "p0036")["version"] == 2


def test_polish_page_skips_when_body_lacks_history(monkeypatch, tmp_path):
    # Build a segments JSONL where the body has empty translation_history.
    part_dir = tmp_path / "03_segmented_text" / "part1"
    part_dir.mkdir(parents=True)
    (part_dir / "segments_with_translations.jsonl").write_text(
        json.dumps({
            "segment_id": "seg_p0050_body_l0001",
            "page_id": "p0050",
            "segment_type": "body",
            "latin_text": "Lorem ipsum",
            "translation_history": [],
        }) + "\n",
        encoding="utf-8",
    )
    _patch_artifacts_dir(monkeypatch, tmp_path)
    adapter = _make_adapter("anything")
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0050",
        body_segments=pages["p0050"]["body"],
        fn_segments=pages["p0050"]["footnotes"],
        adapter=adapter,
        lexicon_profile="minimal",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T16:00:00Z",
        part="part1",
    )
    assert log["status"] == "skipped_missing_history"


def test_polish_page_validation_error_when_marker_dropped(monkeypatch, tmp_path):
    _segments_jsonl(tmp_path)
    _patch_artifacts_dir(monkeypatch, tmp_path)
    # Adapter response omits the required ^y marker entirely.
    adapter = _make_adapter("Polished prose without any anchor at all.")
    segs = pt.load_segments("part1")
    pages = pt.group_by_page(segs)
    log = pt.polish_page(
        "p0036",
        body_segments=pages["p0036"]["body"],
        fn_segments=pages["p0036"]["footnotes"],
        adapter=adapter,
        lexicon_profile="minimal",
        extra_context=None,
        force=False,
        dry_run=False,
        timestamp="2026-05-01T16:00:00Z",
        part="part1",
    )
    assert log["status"] == "error:validation"
    assert pt.load_polished_artifact("part1", "p0036") is None
