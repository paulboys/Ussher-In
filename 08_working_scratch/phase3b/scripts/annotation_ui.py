import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file, url_for

ROOT = Path(__file__).resolve().parents[3]
PHASE3B_ROOT = ROOT / "08_working_scratch" / "phase3b"
ANNOTATIONS_DIR = PHASE3B_ROOT / "annotations"
TEMPLATE_DIR = PHASE3B_ROOT / "ui" / "templates"
STATIC_DIR = PHASE3B_ROOT / "ui" / "static"
SOURCE_PDF_DIR = ROOT / "00_source_pdf"
PILOT_OCR_DIR = ROOT / "01_raw_ocr_output"
PIPELINE_SCRIPTS_DIR = ROOT / "08_working_scratch" / "pipeline_scripts"

ALLOWED_REVIEW_STATUS = {"draft", "reviewed", "locked"}
SIDE_VALUES = {"", "left", "right"}

HEADER_OVERRIDE_FIELDS: dict[str, str] = {
    "contains_header_page_number": "bool",
    "contains_header_chapter_number": "bool",
    "header_page_number_side": "side",
    "header_chapter_side": "side",
    "header_parity_consistent": "bool",
}

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))


def _annotation_paths() -> list[Path]:
    return sorted(ANNOTATIONS_DIR.glob("page_p*.json"))


def _annotation_path(page_id: str) -> Path:
    if not re.fullmatch(r"p\d{4}", page_id):
        raise ValueError("Invalid page id")
    return ANNOTATIONS_DIR / f"page_{page_id}.json"


def _read_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_payload_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent), suffix=".tmp"
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    Path(temp_name).replace(path)


def _resolve_source_pdf(payload: dict) -> tuple[Path, str]:
    source_pdf_value = str(payload.get("source_pdf", "")).strip()
    source_pdf = Path(source_pdf_value)
    if not source_pdf.is_absolute():
        candidates = [
            ROOT / source_pdf,
            ROOT / "00_source_pdf" / source_pdf_value,
        ]
        source_pdf = next((candidate for candidate in candidates if candidate.exists()), source_pdf)
    return source_pdf, source_pdf_value


def _all_lines(payload: dict) -> list[dict]:
    regions = payload.get("regions", {})
    lines = []
    for region in ("header", "body", "footnote", "marginalia", "catchword"):
        values = regions.get(region, [])
        if isinstance(values, list):
            lines.extend([line for line in values if isinstance(line, dict)])
    return lines


def _header_lines(payload: dict) -> list[dict]:
    regions = payload.get("regions", {})
    values = regions.get("header", [])
    if not isinstance(values, list):
        return []
    return [line for line in values if isinstance(line, dict)]


def _body_lines(payload: dict) -> list[dict]:
    regions = payload.get("regions", {})
    values = regions.get("body", [])
    if not isinstance(values, list):
        return []
    return [line for line in values if isinstance(line, dict)]


def _opposite_side(side: str) -> str:
    if side == "left":
        return "right"
    if side == "right":
        return "left"
    return ""


def _side_for_header_index(index: int, total: int) -> str:
    if total < 2:
        return "unknown"
    if index == 0:
        return "left"
    if index == 1:
        return "right"
    return "unknown"


def _expected_page_number_side(page_num: int | None) -> str:
    if not isinstance(page_num, int):
        return ""
    return "left" if page_num % 2 == 0 else "right"


def _contains_page_number_token(text: str, page_num: int) -> bool:
    return bool(re.search(rf"(?<!\\d){page_num}(?!\\d)", text))


def _is_chapter_header(text: str) -> bool:
    # Accept forms like "CAP. II." and minor punctuation/spacing variants.
    return bool(re.search(r"\bCAP\.?\s*[IVXLCDM]+\.?\b", text, flags=re.IGNORECASE))


def _parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off", ""}:
            return False
    return bool(default)


def _parse_side(value: object, default: str = "") -> str:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in SIDE_VALUES:
        return normalized
    return default


def _refresh_meta_flags(payload: dict) -> None:
    lines = _all_lines(payload)
    header_lines = _header_lines(payload)
    body_lines = _body_lines(payload)
    ae_pattern = re.compile(r"(ae|AE|æ|Æ)")
    marker_pattern = re.compile(r"\[[^\]]+\]|\bfn\d+\b|[\*†‡]")

    contains_ae_focus = any(
        ae_pattern.search(str(line.get("text_gold", ""))) for line in lines
    )
    contains_marker_focus = any(
        bool(line.get("contains_marker", False))
        or marker_pattern.search(str(line.get("text_gold", "")))
        for line in lines
    )

    page_num_value = payload.get("page_num")
    try:
        page_num = int(page_num_value)
    except (TypeError, ValueError):
        page_num = None

    header_page_number_side = ""
    header_chapter_side = ""
    contains_header_page_number = False
    contains_header_chapter_number = False

    # Prefer explicit header region; if absent, scan first body lines where seeded OCR often keeps header text.
    candidate_lines = header_lines if header_lines else body_lines[:2]
    total_candidates = len(candidate_lines)
    for index, line in enumerate(candidate_lines):
        text = str(line.get("text_gold", ""))
        side = _side_for_header_index(index, total_candidates)

        if page_num is not None and _contains_page_number_token(text, page_num):
            contains_header_page_number = True
            if side in {"left", "right"} and header_page_number_side == "":
                header_page_number_side = side

        if _is_chapter_header(text):
            contains_header_chapter_number = True
            if side in {"left", "right"} and header_chapter_side == "":
                header_chapter_side = side

    expected_side = _expected_page_number_side(page_num)
    if contains_header_page_number and header_page_number_side == "" and expected_side:
        # Fallback to known layout rule when side is not inferable from header line structure.
        header_page_number_side = expected_side

    if (
        contains_header_chapter_number
        and header_chapter_side == ""
        and header_page_number_side in {"left", "right"}
    ):
        # Based on page design, chapter indicator appears opposite the page number.
        header_chapter_side = _opposite_side(header_page_number_side)

    header_parity_consistent = bool(
        contains_header_page_number
        and header_page_number_side in {"left", "right"}
        and expected_side in {"left", "right"}
        and header_page_number_side == expected_side
    )

    meta = payload.setdefault("meta", {})
    meta["contains_ae_focus"] = bool(contains_ae_focus)
    meta["contains_marker_focus"] = bool(contains_marker_focus)

    derived_values: dict[str, object] = {
        "contains_header_page_number": bool(contains_header_page_number),
        "contains_header_chapter_number": bool(contains_header_chapter_number),
        "header_page_number_side": header_page_number_side,
        "header_chapter_side": header_chapter_side,
        "header_parity_consistent": bool(header_parity_consistent),
    }

    for key, derived in derived_values.items():
        meta[f"derived_{key}"] = derived

    for key, field_type in HEADER_OVERRIDE_FIELDS.items():
        enabled_key = f"override_{key}_enabled"
        value_key = f"override_{key}_value"
        enabled = _parse_bool(meta.get(enabled_key, False), default=False)
        meta[enabled_key] = enabled

        if field_type == "bool":
            default_value = bool(derived_values[key])
            parsed_value = _parse_bool(
                meta.get(value_key, default_value), default=default_value
            )
            meta[value_key] = parsed_value
            meta[key] = parsed_value if enabled else default_value
        else:
            default_value = _parse_side(derived_values[key], default="")
            parsed_value = _parse_side(
                meta.get(value_key, default_value), default=default_value
            )
            meta[value_key] = parsed_value
            meta[key] = parsed_value if enabled else default_value


def _validate_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    regions = payload.get("regions", {})
    footnote_ids = {
        str(line.get("line_id", ""))
        for line in regions.get("footnote", [])
        if isinstance(line, dict) and line.get("line_id")
    }

    for line in _all_lines(payload):
        line_id = str(line.get("line_id", "<unknown>"))
        review_status = str(line.get("review_status", ""))
        if review_status not in ALLOWED_REVIEW_STATUS:
            errors.append(f"{line_id}: invalid review_status '{review_status}'")

        marker_id = str(line.get("marker_id", "")).strip()
        marker_target = str(line.get("marker_link_target", "")).strip()
        marker_uncertain = bool(line.get("marker_uncertain", False))

        if marker_id and not marker_target and not marker_uncertain:
            errors.append(f"{line_id}: marker_id set but marker_link_target is empty")

        if marker_target and marker_target not in footnote_ids:
            errors.append(
                f"{line_id}: marker_link_target '{marker_target}' not found in footnote line_ids"
            )

    meta_review_status = str(payload.get("meta", {}).get("review_status", ""))
    if meta_review_status and meta_review_status not in ALLOWED_REVIEW_STATUS:
        errors.append(f"meta.review_status: invalid value '{meta_review_status}'")

    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta: must be an object")
        return errors

    for key, field_type in HEADER_OVERRIDE_FIELDS.items():
        enabled_key = f"override_{key}_enabled"
        value_key = f"override_{key}_value"
        enabled = _parse_bool(meta.get(enabled_key, False), default=False)
        if not enabled:
            continue

        raw_value = meta.get(value_key)
        if field_type == "side":
            normalized = _parse_side(raw_value, default="<invalid>")
            if normalized not in SIDE_VALUES:
                errors.append(f"meta.{value_key}: invalid side '{raw_value}'")

    return errors


@app.get("/")
def index() -> str:
    pages = [path.stem.replace("page_", "") for path in _annotation_paths()]
    # Even with zero pages we render the UI so the user can run OCR from it.
    return render_template("annotation_ui.html", pages=pages)


@app.get("/api/pages")
def api_pages():
    pages = [path.stem.replace("page_", "") for path in _annotation_paths()]
    return jsonify({"pages": pages})


@app.get("/api/page/<page_id>")
def api_page(page_id: str):
    try:
        path = _annotation_path(page_id)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    payload = _read_payload(path)
    return jsonify(payload)


@app.post("/api/page/<page_id>")
def api_save_page(page_id: str):
    try:
        path = _annotation_path(page_id)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    incoming = request.get_json(silent=True)
    if not isinstance(incoming, dict):
        return (
            jsonify({"ok": False, "errors": ["Request body must be JSON object"]}),
            400,
        )

    errors = _validate_payload(incoming)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    _refresh_meta_flags(incoming)
    _write_payload_atomic(path, incoming)
    return jsonify({"ok": True, "meta": incoming.get("meta", {})})


@app.get("/pdf/<page_id>")
def page_pdf(page_id: str):
    try:
        path = _annotation_path(page_id)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    payload = _read_payload(path)
    source_pdf, source_pdf_value = _resolve_source_pdf(payload)

    if not source_pdf.exists():
        return f"Source PDF not found: {source_pdf_value}", 404

    return send_file(source_pdf)


@app.get("/pdfjs/<page_id>")
def pdfjs_viewer(page_id: str):
    try:
        path = _annotation_path(page_id)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    payload = _read_payload(path)
    source_pdf, source_pdf_value = _resolve_source_pdf(payload)
    if not source_pdf.exists():
        return f"Source PDF not found: {source_pdf_value}", 404

    requested_page = request.args.get("page", default="", type=str)
    try:
        initial_page = int(requested_page)
    except (TypeError, ValueError):
        initial_page = int(payload.get("page_num", 1) or 1)
    if initial_page < 1:
        initial_page = 1

    return render_template(
        "pdf_viewer.html",
        pdf_url=url_for("page_pdf", page_id=page_id),
        initial_page=initial_page,
    )


# ---------------------------------------------------------------------------
# OCR-from-UI: list source PDFs and run Gemini OCR on a chosen page in a
# background thread, then convert the result into a Phase 3b annotation file.
# Jobs are kept in-memory (single-user assumption matching the dev Flask app).
# ---------------------------------------------------------------------------

_OCR_JOBS: dict[str, dict] = {}
_OCR_JOBS_LOCK = threading.Lock()


def _list_source_pdfs() -> list[str]:
    if not SOURCE_PDF_DIR.exists():
        return []
    return sorted(p.name for p in SOURCE_PDF_DIR.iterdir() if p.suffix.lower() == ".pdf")


def _job_set(job_id: str, **fields) -> None:
    with _OCR_JOBS_LOCK:
        job = _OCR_JOBS.setdefault(job_id, {})
        job.update(fields)


def _job_get(job_id: str) -> dict | None:
    with _OCR_JOBS_LOCK:
        job = _OCR_JOBS.get(job_id)
        return dict(job) if job is not None else None


def _run_ocr_job(
    job_id: str, pdf_path: Path, page_num: int, part: str, page_id: str, overwrite: bool
) -> None:
    pilot_dir = PILOT_OCR_DIR / part
    pilot_json = pilot_dir / f"{part}_pilot_ocr.json"
    target_annotation = ANNOTATIONS_DIR / f"page_{page_id}.json"

    try:
        _job_set(job_id, state="running", message="Rendering and calling Gemini...")
        pilot_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(PIPELINE_SCRIPTS_DIR / "pilot_ocr.py"),
            "--pdf",
            str(pdf_path),
            "--part",
            part,
            "--start-page",
            str(page_num),
            "--end-page",
            str(page_num),
            "--ocr-engine",
            "gemini",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            _job_set(
                job_id,
                state="error",
                message=f"OCR subprocess failed (code {proc.returncode}). "
                f"stderr tail: {proc.stderr[-400:].strip()}",
            )
            return

        if not pilot_json.exists():
            _job_set(job_id, state="error", message=f"Pilot JSON not produced: {pilot_json}")
            return

        records = json.loads(pilot_json.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            _job_set(job_id, state="error", message="Pilot JSON empty (page out of range?)")
            return

        record = next((r for r in records if str(r.get("page_id")) == page_id), records[0])

        # Lazy import so plain Flask import doesn't pull in pilot deps.
        sys.path.insert(0, str(PIPELINE_SCRIPTS_DIR))
        try:
            from pilot_to_phase3b import convert_record  # noqa: WPS433
        finally:
            try:
                sys.path.remove(str(PIPELINE_SCRIPTS_DIR))
            except ValueError:
                pass

        # Source PDF stored relative to repo root for portability.
        try:
            rel_pdf = pdf_path.relative_to(ROOT).as_posix()
        except ValueError:
            rel_pdf = str(pdf_path)

        payload = convert_record(record, source_pdf=rel_pdf)

        if target_annotation.exists() and not overwrite:
            _job_set(
                job_id,
                state="error",
                message=f"Annotation already exists: {target_annotation.name}. "
                "Re-run with overwrite=true to replace.",
            )
            return

        _write_payload_atomic(target_annotation, payload)
        _job_set(
            job_id,
            state="done",
            message=f"Wrote {target_annotation.name}",
            page_id=page_id,
            stdout_tail=proc.stdout[-300:],
        )
    except Exception as exc:  # pragma: no cover - defensive
        _job_set(job_id, state="error", message=f"{type(exc).__name__}: {exc}")


@app.get("/api/source-pdfs")
def api_source_pdfs():
    return jsonify({"pdfs": _list_source_pdfs()})


@app.post("/api/ocr/start")
def api_ocr_start():
    body = request.get_json(silent=True) or {}
    pdf_name = str(body.get("pdf", "")).strip()
    try:
        page_num = int(body.get("page", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "page must be an integer"}), 400
    part = str(body.get("part", "part1")).strip() or "part1"
    overwrite = bool(body.get("overwrite", False))

    if not pdf_name:
        return jsonify({"ok": False, "error": "pdf is required"}), 400
    if page_num < 1:
        return jsonify({"ok": False, "error": "page must be >= 1"}), 400
    if part not in {"part1", "part2"}:
        return jsonify({"ok": False, "error": "part must be 'part1' or 'part2'"}), 400

    pdf_path = SOURCE_PDF_DIR / pdf_name
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return jsonify({"ok": False, "error": f"PDF not found: {pdf_name}"}), 404

    page_id = f"p{page_num:04d}"
    target = ANNOTATIONS_DIR / f"page_{page_id}.json"
    if target.exists() and not overwrite:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "annotation_exists",
                    "page_id": page_id,
                    "message": f"{target.name} already exists. Confirm overwrite to replace.",
                }
            ),
            409,
        )

    job_id = uuid.uuid4().hex
    _job_set(
        job_id,
        state="queued",
        message="Queued",
        started_at=time.time(),
        page_id=page_id,
        pdf=pdf_name,
    )
    thread = threading.Thread(
        target=_run_ocr_job,
        args=(job_id, pdf_path, page_num, part, page_id, overwrite),
        daemon=True,
    )
    thread.start()
    return jsonify({"ok": True, "job_id": job_id, "page_id": page_id}), 202


@app.get("/api/ocr/status/<job_id>")
def api_ocr_status(job_id: str):
    job = _job_get(job_id)
    if job is None:
        abort(404)
    return jsonify(job)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
