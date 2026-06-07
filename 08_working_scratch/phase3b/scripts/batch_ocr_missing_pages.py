"""Batch-run Gemini OCR for missing Phase 3b annotation pages.

This is the command-line companion to the OCR button in the annotation UI.
It uses the same underlying Gemini OCR path:

1. ``pipeline_scripts/pilot_ocr.py`` renders the PDF page and calls Gemini.
2. ``pipeline_scripts/pilot_to_phase3b.py`` converts the pilot record into
   the annotation JSON shape consumed by the UI.

The runner processes one page at a time so it can resume naturally: pages
whose ``page_pNNNN.json`` annotation file already exists are skipped unless
``--overwrite`` is passed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[3]
PHASE3B_ROOT = ROOT / "08_working_scratch" / "phase3b"
PIPELINE_SCRIPTS_DIR = ROOT / "08_working_scratch" / "pipeline_scripts"
ANNOTATIONS_DIR = PHASE3B_ROOT / "annotations"
PILOT_OCR_DIR = ROOT / "01_raw_ocr_output"
DEFAULT_PROVIDER_CONFIG = ROOT / "06_tools_config" / "providers.json"
DEFAULT_LOG_DIR = PHASE3B_ROOT / "ocr_batch_logs"

USSHER_EDITIONS = {"1687_second", "1847_elrington_todd"}
WHITAKER_EDITIONS = {"whitaker_english", "whitaker_latin"}
ANNALS_EDITIONS = {"annals_latin", "annals_english"}
ALLOWED_EDITIONS = USSHER_EDITIONS | WHITAKER_EDITIONS | ANNALS_EDITIONS
SUBFOLDERED_EDITIONS = WHITAKER_EDITIONS | ANNALS_EDITIONS
USSHER_PARTS = {"part1", "part2"}


@dataclass(frozen=True)
class PageJob:
    page_num: int
    page_id: str
    target_path: Path
    should_run: bool
    reason: str


@dataclass(frozen=True)
class BatchConfig:
    pdf_path: Path
    edition: str
    part: str
    start_page: int
    end_page: int
    annotations_dir: Path = ANNOTATIONS_DIR
    output_root: Path = PILOT_OCR_DIR
    provider_config: Path | None = DEFAULT_PROVIDER_CONFIG
    lang: str = "lat+grc"
    overwrite: bool = False
    dry_run: bool = False
    stop_on_error: bool = False
    delay_seconds: float = 0.0
    max_page_retries: int = 2
    retry_delay_seconds: float = 60.0
    continue_on_rate_limit: bool = False
    log_dir: Path = DEFAULT_LOG_DIR


def corpus_subdir(edition: str | None) -> str:
    """Return the annotation subdirectory for an edition.

    This mirrors ``annotation_ui.py``: Whitaker and Annals are namespaced
    under ``annotations/<edition>/``; Ussher editions stay in the flat
    ``annotations/`` directory for backward compatibility.
    """
    if edition in SUBFOLDERED_EDITIONS:
        return str(edition)
    return ""


def annotations_dir_for(edition: str, annotations_root: Path = ANNOTATIONS_DIR) -> Path:
    subdir = corpus_subdir(edition)
    return annotations_root / subdir if subdir else annotations_root


def page_id_for(page_num: int) -> str:
    if page_num < 1:
        raise ValueError("page number must be >= 1")
    return f"p{page_num:04d}"


def annotation_path_for(
    page_num: int,
    edition: str,
    annotations_root: Path = ANNOTATIONS_DIR,
) -> Path:
    return annotations_dir_for(edition, annotations_root) / f"page_{page_id_for(page_num)}.json"


def resolve_part(edition: str, requested_part: str | None) -> str:
    if edition in SUBFOLDERED_EDITIONS:
        return edition
    part = requested_part or "part1"
    if part not in USSHER_PARTS:
        raise ValueError("Ussher editions require --part part1 or --part part2")
    return part


def build_page_jobs(
    *,
    edition: str,
    start_page: int,
    end_page: int,
    annotations_root: Path = ANNOTATIONS_DIR,
    overwrite: bool = False,
) -> list[PageJob]:
    if edition not in ALLOWED_EDITIONS:
        raise ValueError(f"unknown edition: {edition}")
    if start_page < 1:
        raise ValueError("--start-page must be >= 1")
    if end_page < start_page:
        raise ValueError("--end-page must be >= --start-page")

    jobs: list[PageJob] = []
    for page_num in range(start_page, end_page + 1):
        target = annotation_path_for(page_num, edition, annotations_root)
        exists = target.exists()
        should_run = overwrite or not exists
        reason = "overwrite requested" if overwrite and exists else "missing"
        if exists and not overwrite:
            reason = "annotation exists"
        jobs.append(
            PageJob(
                page_num=page_num,
                page_id=page_id_for(page_num),
                target_path=target,
                should_run=should_run,
                reason=reason,
            )
        )
    return jobs


def _resolve_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _source_pdf_for_payload(pdf_path: Path) -> str:
    resolved = pdf_path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _write_json_atomic(target: Path, payload: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def _append_log(log_path: Path, row: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _make_log_path(config: BatchConfig) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = (
        f"{config.edition}_{config.part}_"
        f"p{config.start_page:04d}_p{config.end_page:04d}_{stamp}.jsonl"
    )
    return config.log_dir / stem


def _load_pilot_record(pilot_json: Path, page_id: str) -> dict:
    records = json.loads(pilot_json.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        raise RuntimeError(f"pilot OCR output was not a list: {pilot_json}")
    for record in records:
        if isinstance(record, dict) and str(record.get("page_id")) == page_id:
            return record
    raise RuntimeError(f"{page_id} not found in pilot OCR output: {pilot_json}")


def _http_status_code(exc: BaseException) -> int | None:
    code = getattr(exc, "code", None) or getattr(exc, "status", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _is_retryable_error(exc: BaseException) -> bool:
    status = _http_status_code(exc)
    if status in {429, 500, 502, 503, 504}:
        return True
    text = str(exc).lower()
    return "too many requests" in text or "rate limit" in text


def _is_rate_limit_error(exc: BaseException) -> bool:
    status = _http_status_code(exc)
    text = str(exc).lower()
    return status == 429 or "too many requests" in text or "rate limit" in text


def run_ocr_for_page(config: BatchConfig, job: PageJob) -> Path:
    """Run Gemini OCR for one page and write the UI annotation JSON."""
    if str(PIPELINE_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(PIPELINE_SCRIPTS_DIR))

    from pilot_ocr import run_gemini_pilot  # noqa: WPS433
    from pilot_to_phase3b import convert_record  # noqa: WPS433

    pilot_json = run_gemini_pilot(
        pdf_path=config.pdf_path,
        part=config.part,
        start_page=job.page_num,
        end_page=job.page_num,
        output_root=config.output_root,
        provider_config_path=config.provider_config,
        lang=config.lang,
    )
    record = _load_pilot_record(pilot_json, job.page_id)
    payload = convert_record(
        record,
        source_pdf=_source_pdf_for_payload(config.pdf_path),
        edition=config.edition,
    )

    if job.target_path.exists() and not config.overwrite:
        raise FileExistsError(str(job.target_path))

    _write_json_atomic(job.target_path, payload)
    return job.target_path


def run_batch(
    config: BatchConfig,
    *,
    page_runner: Callable[[BatchConfig, PageJob], Path] = run_ocr_for_page,
) -> dict:
    if config.edition not in ALLOWED_EDITIONS:
        raise ValueError(f"edition must be one of {sorted(ALLOWED_EDITIONS)}")
    if not config.pdf_path.exists():
        raise FileNotFoundError(str(config.pdf_path))

    jobs = build_page_jobs(
        edition=config.edition,
        start_page=config.start_page,
        end_page=config.end_page,
        annotations_root=config.annotations_dir,
        overwrite=config.overwrite,
    )
    log_path = _make_log_path(config)
    counts = {"run": 0, "done": 0, "skipped": 0, "error": 0}

    for job in jobs:
        base_row = {
            "page_num": job.page_num,
            "page_id": job.page_id,
            "edition": config.edition,
            "part": config.part,
            "target_path": str(job.target_path),
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        }

        if not job.should_run:
            counts["skipped"] += 1
            print(f"SKIP {job.page_id} {job.reason}: {job.target_path}")
            _append_log(log_path, {**base_row, "status": "skipped", "reason": job.reason})
            continue

        counts["run"] += 1
        if config.dry_run:
            print(f"DRY  {job.page_id} would OCR: {job.reason}")
            _append_log(log_path, {**base_row, "status": "dry_run", "reason": job.reason})
            continue

        started = time.time()
        written: Path | None = None
        last_exc: Exception | None = None
        for attempt in range(config.max_page_retries + 1):
            label = "RUN " if attempt == 0 else "TRY "
            suffix = "" if attempt == 0 else f" retry {attempt}/{config.max_page_retries}"
            print(f"{label} {job.page_id} {job.reason}{suffix}")
            try:
                written = page_runner(config, job)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001 - CLI should log retryable API failures.
                last_exc = exc
                retryable = _is_retryable_error(exc)
                has_retry = attempt < config.max_page_retries
                if retryable and has_retry:
                    wait = max(0.0, config.retry_delay_seconds * (attempt + 1))
                    print(
                        f"WAIT {job.page_id} {type(exc).__name__}: {exc}; "
                        f"retrying in {wait:g}s"
                    )
                    _append_log(
                        log_path,
                        {
                            **base_row,
                            "status": "retry_wait",
                            "attempt": attempt + 1,
                            "max_page_retries": config.max_page_retries,
                            "wait_seconds": wait,
                            "http_status": _http_status_code(exc),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    if wait > 0:
                        time.sleep(wait)
                    continue
                break

        if last_exc is not None:
            counts["error"] += 1
            print(f"ERR  {job.page_id} {type(last_exc).__name__}: {last_exc}")
            _append_log(
                log_path,
                {
                    **base_row,
                    "status": "error",
                    "error_type": type(last_exc).__name__,
                    "http_status": _http_status_code(last_exc),
                    "error": str(last_exc),
                    "elapsed_seconds": round(time.time() - started, 3),
                },
            )
            if config.stop_on_error or (
                _is_rate_limit_error(last_exc) and not config.continue_on_rate_limit
            ):
                print(
                    f"STOP {job.page_id} rate limit encountered; "
                    "rerun later starting from this page."
                )
                break
            continue

        assert written is not None

        counts["done"] += 1
        print(f"DONE {job.page_id} wrote {written}")
        _append_log(
            log_path,
            {
                **base_row,
                "status": "done",
                "written_path": str(written),
                "elapsed_seconds": round(time.time() - started, 3),
            },
        )
        if config.delay_seconds > 0:
            time.sleep(config.delay_seconds)

    result = {
        **counts,
        "total_pages": len(jobs),
        "log_path": str(log_path),
        "edition": config.edition,
        "part": config.part,
    }
    print(
        "batch_ocr_missing_pages: "
        f"done={counts['done']} skipped={counts['skipped']} "
        f"errors={counts['error']} dry_run={config.dry_run}"
    )
    print(f"log: {log_path}")
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the UI's Gemini OCR prompt over missing annotation pages."
    )
    parser.add_argument("--pdf", type=Path, required=True, help="Source PDF path.")
    parser.add_argument(
        "--edition",
        required=True,
        choices=sorted(ALLOWED_EDITIONS),
        help="Annotation edition key. Use 1847_elrington_todd for Elrington & Todd.",
    )
    parser.add_argument(
        "--part",
        choices=sorted(USSHER_PARTS),
        default="part1",
        help=(
            "Ussher corpus part for raw OCR output. Ignored for Whitaker/Annals, "
            "where the part is forced to the edition name."
        ),
    )
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--output-root", type=Path, default=PILOT_OCR_DIR)
    parser.add_argument("--provider-config", type=Path, default=DEFAULT_PROVIDER_CONFIG)
    parser.add_argument("--lang", default="lat+grc")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument(
        "--max-page-retries",
        type=int,
        default=2,
        help="Retry count for retryable API errors such as HTTP 429.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=60.0,
        help=(
            "Base cooldown before retrying retryable API errors. "
            "The wait scales by attempt number."
        ),
    )
    parser.add_argument(
        "--continue-on-rate-limit",
        action="store_true",
        help=(
            "Continue to later pages after a 429 exhausts retries. By default "
            "the batch stops so resume can restart from the rate-limited page."
        ),
    )
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pdf_path = _resolve_path(args.pdf)
    assert pdf_path is not None
    provider_config = _resolve_path(args.provider_config)
    output_root = _resolve_path(args.output_root)
    log_dir = _resolve_path(args.log_dir)
    assert output_root is not None
    assert log_dir is not None

    part = resolve_part(args.edition, args.part)
    config = BatchConfig(
        pdf_path=pdf_path,
        edition=args.edition,
        part=part,
        start_page=args.start_page,
        end_page=args.end_page,
        output_root=output_root,
        provider_config=provider_config,
        lang=args.lang,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        stop_on_error=args.stop_on_error,
        delay_seconds=args.delay_seconds,
        max_page_retries=args.max_page_retries,
        retry_delay_seconds=args.retry_delay_seconds,
        continue_on_rate_limit=args.continue_on_rate_limit,
        log_dir=log_dir,
    )
    run_batch(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALLOWED_EDITIONS",
    "BatchConfig",
    "PageJob",
    "annotation_path_for",
    "annotations_dir_for",
    "build_page_jobs",
    "corpus_subdir",
    "page_id_for",
    "resolve_part",
    "run_batch",
    "run_ocr_for_page",
]
