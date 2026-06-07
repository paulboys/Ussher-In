from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PHASE3B_SCRIPTS = Path(__file__).resolve().parents[1] / "phase3b" / "scripts"
if str(PHASE3B_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PHASE3B_SCRIPTS))

from batch_ocr_missing_pages import (  # noqa: E402
    BatchConfig,
    annotation_path_for,
    build_page_jobs,
    corpus_subdir,
    resolve_part,
    run_batch,
)


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_elrington_todd_edition_uses_flat_annotation_directory(tmp_path):
    assert corpus_subdir("1847_elrington_todd") == ""
    assert (
        annotation_path_for(101, "1847_elrington_todd", tmp_path)
        == tmp_path / "page_p0101.json"
    )


def test_subfoldered_editions_use_namespaced_annotation_directory(tmp_path):
    assert corpus_subdir("whitaker_latin") == "whitaker_latin"
    assert (
        annotation_path_for(44, "whitaker_latin", tmp_path)
        == tmp_path / "whitaker_latin" / "page_p0044.json"
    )


def test_build_page_jobs_skips_existing_pages_inside_requested_range(tmp_path):
    (tmp_path / "page_p0101.json").write_text("{}", encoding="utf-8")

    jobs = build_page_jobs(
        edition="1847_elrington_todd",
        start_page=101,
        end_page=103,
        annotations_root=tmp_path,
    )

    assert [(job.page_id, job.should_run, job.reason) for job in jobs] == [
        ("p0101", False, "annotation exists"),
        ("p0102", True, "missing"),
        ("p0103", True, "missing"),
    ]


def test_build_page_jobs_overwrite_marks_existing_pages_runnable(tmp_path):
    (tmp_path / "page_p0101.json").write_text("{}", encoding="utf-8")

    jobs = build_page_jobs(
        edition="1847_elrington_todd",
        start_page=101,
        end_page=101,
        annotations_root=tmp_path,
        overwrite=True,
    )

    assert jobs[0].should_run is True
    assert jobs[0].reason == "overwrite requested"


def test_resolve_part_matches_ui_behavior_for_ussher_and_subfoldered_editions():
    assert resolve_part("1847_elrington_todd", "part2") == "part2"
    assert resolve_part("whitaker_latin", "part1") == "whitaker_latin"
    assert resolve_part("annals_english", None) == "annals_english"

    with pytest.raises(ValueError):
        resolve_part("1847_elrington_todd", "whitaker_latin")


def test_run_batch_dry_run_logs_skips_and_missing_without_calling_runner(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "page_p0101.json").write_text("{}", encoding="utf-8")

    config = BatchConfig(
        pdf_path=pdf_path,
        edition="1847_elrington_todd",
        part="part1",
        start_page=101,
        end_page=102,
        annotations_dir=annotations_dir,
        output_root=tmp_path / "raw",
        provider_config=None,
        dry_run=True,
        log_dir=tmp_path / "logs",
    )

    def fail_runner(_config, _job):
        raise AssertionError("dry-run must not invoke OCR")

    result = run_batch(config, page_runner=fail_runner)

    assert result["skipped"] == 1
    assert result["run"] == 1
    assert result["done"] == 0
    assert result["error"] == 0
    rows = _read_jsonl(Path(result["log_path"]))
    assert [row["status"] for row in rows] == ["skipped", "dry_run"]
    assert rows[1]["page_id"] == "p0102"


def test_run_batch_processes_only_missing_pages_with_injected_runner(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "page_p0101.json").write_text("{}", encoding="utf-8")
    called: list[str] = []

    config = BatchConfig(
        pdf_path=pdf_path,
        edition="1847_elrington_todd",
        part="part1",
        start_page=101,
        end_page=103,
        annotations_dir=annotations_dir,
        output_root=tmp_path / "raw",
        provider_config=None,
        log_dir=tmp_path / "logs",
    )

    def fake_runner(_config, job):
        called.append(job.page_id)
        job.target_path.write_text("{}", encoding="utf-8")
        return job.target_path

    result = run_batch(config, page_runner=fake_runner)

    assert called == ["p0102", "p0103"]
    assert result["skipped"] == 1
    assert result["done"] == 2
    rows = _read_jsonl(Path(result["log_path"]))
    assert [row["status"] for row in rows] == ["skipped", "done", "done"]
