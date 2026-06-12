import datetime as _dt
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import logging

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
ALLOWED_FOOTNOTE_KIND = {"citation", "gloss", "cross_ref", "not_a_note", "other"}
USSHER_EDITIONS = {"1687_second", "1847_elrington_todd"}
WHITAKER_EDITIONS = {"whitaker_english", "whitaker_latin"}
ANNALS_EDITIONS = {"annals_latin", "annals_english"}
ALLOWED_EDITIONS = USSHER_EDITIONS | WHITAKER_EDITIONS | ANNALS_EDITIONS

# Editions whose annotations live in a named subfolder under
# ``annotations/`` (and whose raw OCR output lives in a matching
# ``01_raw_ocr_output/<edition>/`` directory) rather than in the flat
# top-level Ussher namespace.
SUBFOLDERED_EDITIONS = WHITAKER_EDITIONS | ANNALS_EDITIONS
SCHEMA_REGIONS = ("header", "body", "marginalia", "catchword")

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))

# Configure logging for the Flask app
logger = logging.getLogger("flask_app")
logger.setLevel(logging.INFO)

# Add a file handler for persistent logs (optional)
file_handler = logging.FileHandler("annotation_ui.log")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def _corpus_subdir(edition: str | None) -> str:
    """Return the annotations subdirectory name for a given edition.

    Britannicarum Ussher editions live in the flat top-level
    ``annotations/`` dir for backward compatibility. Whitaker editions
    and Annals editions are namespaced one level deeper so their JSONs
    are completely separate, e.g. ``annotations/whitaker_english/``,
    ``annotations/annals_latin/``.
    """
    if edition in SUBFOLDERED_EDITIONS:
        return edition
    return ""


def _annotations_dir(edition: str | None = None) -> Path:
    subdir = _corpus_subdir(edition)
    return ANNOTATIONS_DIR / subdir if subdir else ANNOTATIONS_DIR


def _physical_index_from_stem(stem: str) -> int:
    """Extract the 1-based physical PDF page index from a ``page_pNNNN`` stem."""
    page_id = stem.replace("page_", "")
    if page_id.startswith("p") and page_id[1:].isdigit():
        return int(page_id[1:])
    return 0


def _read_reading_order(path: Path) -> int | None:
    """Return ``reading_order_index`` from a page payload, or ``None`` if absent/invalid."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    value = payload.get("reading_order_index")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _annotation_paths(edition: str | None = None) -> list[Path]:
    base = _annotations_dir(edition)
    if not base.exists():
        return []
    paths = list(base.glob("page_p*.json"))

    def sort_key(path: Path) -> tuple[int, int]:
        physical = _physical_index_from_stem(path.stem)
        roi = _read_reading_order(path)
        # Pages without reading_order_index fall back to physical index so
        # tagged and untagged pages interleave correctly. Physical index is
        # the tiebreaker when two pages share a reading_order_index.
        return (roi if roi is not None else physical, physical)

    paths.sort(key=sort_key)
    return paths


def _annotation_path(page_id: str, edition: str | None = None) -> Path:
    if not re.fullmatch(r"p\d{4}", page_id):
        raise ValueError("Invalid page id")
    return _annotations_dir(edition) / f"page_{page_id}.json"


def _edition_from_request() -> str | None:
    """Extract a validated edition value from the request query string.

    Returns ``None`` when no edition query param is present or when it
    falls outside ``ALLOWED_EDITIONS`` (treat invalid values as Ussher
    so existing flat-path URLs keep working).
    """
    value = request.args.get("edition", default="", type=str).strip()
    if value and value in ALLOWED_EDITIONS:
        return value
    return None


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
    for region in SCHEMA_REGIONS:
        values = regions.get(region, [])
        if isinstance(values, list):
            lines.extend([line for line in values if isinstance(line, dict)])
    return lines


def _footnotes(payload: dict) -> list[dict]:
    values = payload.get("footnotes", [])
    if not isinstance(values, list):
        return []
    return [fn for fn in values if isinstance(fn, dict)]


def _stamp_seq(payload: dict) -> None:
    """Stamp ``seq`` (1-based, dense) on every line/footnote based on the
    current array order. ``seq`` is the ordering authority for
    translation and rendering; ``line_id`` / ``footnote_id`` remain
    immutable identity. Server-side stamping is defense-in-depth: even
    if a client forgets to send ``seq`` (or sends inconsistent values),
    the persisted file always carries a valid order key.
    """
    if not isinstance(payload, dict):
        return
    regions = payload.get("regions", {})
    if isinstance(regions, dict):
        for region in SCHEMA_REGIONS:
            arr = regions.get(region)
            if not isinstance(arr, list):
                continue
            for idx, line in enumerate(arr):
                if isinstance(line, dict):
                    line["seq"] = idx + 1
    footnotes = payload.get("footnotes")
    if isinstance(footnotes, list):
        for idx, fn in enumerate(footnotes):
            if isinstance(fn, dict):
                fn["seq"] = idx + 1


def _validate_payload(payload: dict) -> list[str]:
    """Slim validator for the post-redesign schema.

    Tolerates older payloads on read: legacy fields and the removed
    ``regions.footnote`` are simply ignored. We validate the things we need
    to be sure about for downstream consumers (review_status enums,
    footnote_id integrity, footnote.kind enum).
    """
    errors: list[str] = []

    body_line_ids = {
        str(line.get("line_id", ""))
        for line in payload.get("regions", {}).get("body", [])
        if isinstance(line, dict) and line.get("line_id")
    }

    footnote_ids = {
        str(fn.get("footnote_id", ""))
        for fn in _footnotes(payload)
        if fn.get("footnote_id")
    }

    for line in _all_lines(payload):
        line_id = str(line.get("line_id", "<unknown>"))
        review_status = str(line.get("review_status", "draft"))
        if review_status not in ALLOWED_REVIEW_STATUS:
            errors.append(f"{line_id}: invalid review_status '{review_status}'")

        # Validate body markers reference real footnotes.
        markers = line.get("markers")
        if isinstance(markers, list):
            for idx, marker in enumerate(markers):
                if not isinstance(marker, dict):
                    errors.append(f"{line_id}.markers[{idx}]: not an object")
                    continue
                fn_id = str(marker.get("footnote_id", ""))
                if fn_id and fn_id not in footnote_ids:
                    errors.append(
                        f"{line_id}.markers[{idx}]: footnote_id '{fn_id}' not in footnotes[]"
                    )

    for idx, fn in enumerate(_footnotes(payload)):
        fn_id = str(fn.get("footnote_id", f"<idx{idx}>"))
        kind = str(fn.get("kind", "citation"))
        if kind not in ALLOWED_FOOTNOTE_KIND:
            errors.append(f"footnotes[{fn_id}]: invalid kind '{kind}'")
        review_status = str(fn.get("review_status", "draft"))
        if review_status not in ALLOWED_REVIEW_STATUS:
            errors.append(
                f"footnotes[{fn_id}]: invalid review_status '{review_status}'"
            )
        body_line_id = str(fn.get("body_line_id", ""))
        if body_line_id and body_line_id not in body_line_ids:
            errors.append(
                f"footnotes[{fn_id}]: body_line_id '{body_line_id}' not in body line_ids"
            )

    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta: must be an object")
        return errors

    meta_review_status = str(meta.get("review_status", "draft"))
    if meta_review_status and meta_review_status not in ALLOWED_REVIEW_STATUS:
        errors.append(f"meta.review_status: invalid value '{meta_review_status}'")

    # Edition is optional for legacy payloads, but must be from the allowed
    # set when present. Treat empty/missing as legacy 1687.
    edition = payload.get("edition", "")
    if edition and str(edition) not in ALLOWED_EDITIONS:
        errors.append(f"edition: invalid value '{edition}'")

    return errors


# ---------------------------------------------------------------------------
# Edit log: append per-save diffs to a sidecar JSONL for prompt refinement.
# ---------------------------------------------------------------------------

# Fields we track per line/footnote/page-meta when computing the diff.
_LINE_DIFF_FIELDS = ("text_gold", "marker_id", "notes", "review_status")
_FOOTNOTE_DIFF_FIELDS = (
    "text_gold",
    "kind",
    "marker_number",
    "body_line_id",
    "notes",
    "review_status",
)
_PAGE_META_DIFF_FIELDS = (
    "annotation_status",
    "review_status",
    "notes",
    "ocr_page_summary",
)
_PAGE_TOPLEVEL_DIFF_FIELDS = (
    "page_num",
    "printed_page_num",
    "reading_order_index",
    "section_id",
    "source_pdf",
    "edition",
)


def _index_by(items, key: str) -> dict:
    out: dict = {}
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
            if value:
                out[str(value)] = item
    return out


def _diff_payloads(old: dict, new: dict) -> list[dict]:
    """Compute a flat list of edit entries between two payloads."""
    entries: list[dict] = []
    page_id = str(new.get("page_id") or old.get("page_id") or "")
    reviewer = str(new.get("meta", {}).get("reviewer", "")) if isinstance(new.get("meta"), dict) else ""
    timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat()

    def emit(scope: str, target_id: str, field: str, before, after) -> None:
        if before == after:
            return
        entries.append(
            {
                "ts": timestamp,
                "page_id": page_id,
                "scope": scope,
                "target_id": target_id,
                "field": field,
                "before": before,
                "after": after,
                "reviewer": reviewer,
            }
        )

    # Page-level top-level fields.
    for field in _PAGE_TOPLEVEL_DIFF_FIELDS:
        emit("page", page_id, field, old.get(field), new.get(field))

    # Page meta.
    old_meta = old.get("meta") if isinstance(old.get("meta"), dict) else {}
    new_meta = new.get("meta") if isinstance(new.get("meta"), dict) else {}
    for field in _PAGE_META_DIFF_FIELDS:
        emit("page_meta", page_id, field, old_meta.get(field), new_meta.get(field))

    # Lines (across all current regions).
    old_lines = {
        str(line.get("line_id", "")): line
        for line in _all_lines(old)
        if line.get("line_id")
    }
    new_lines = {
        str(line.get("line_id", "")): line
        for line in _all_lines(new)
        if line.get("line_id")
    }
    for line_id, new_line in new_lines.items():
        old_line = old_lines.get(line_id, {})
        for field in _LINE_DIFF_FIELDS:
            emit("line", line_id, field, old_line.get(field), new_line.get(field))
        # Marker structure changes (insert/delete/reorder) -> single entry.
        old_markers = old_line.get("markers")
        new_markers = new_line.get("markers")
        if (old_markers or []) != (new_markers or []):
            emit("body_marker", line_id, "markers", old_markers, new_markers)

    # Footnotes (matched by footnote_id).
    old_fn = _index_by(old.get("footnotes"), "footnote_id")
    new_fn = _index_by(new.get("footnotes"), "footnote_id")
    for fn_id, new_node in new_fn.items():
        old_node = old_fn.get(fn_id, {})
        for field in _FOOTNOTE_DIFF_FIELDS:
            emit("footnote", fn_id, field, old_node.get(field), new_node.get(field))
    for fn_id in old_fn.keys() - new_fn.keys():
        emit("footnote", fn_id, "_deleted", old_fn[fn_id], None)
    for fn_id in new_fn.keys() - old_fn.keys():
        emit("footnote", fn_id, "_added", None, new_fn[fn_id])

    return entries


def _edits_path(page_id: str, edition: str | None = None) -> Path:
    return _annotations_dir(edition) / f"page_{page_id}.edits.jsonl"


def _append_edit_log(
    page_id: str, entries: list[dict], edition: str | None = None
) -> None:
    if not entries:
        return
    path = _edits_path(page_id, edition)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.get("/")
def index() -> str:
    edition = _edition_from_request()
    pages = [path.stem.replace("page_", "") for path in _annotation_paths(edition)]
    # Even with zero pages we render the UI so the user can run OCR from it.
    return render_template("annotation_ui.html", pages=pages)


@app.get("/api/pages")
def api_pages():
    edition = _edition_from_request()
    pages = [path.stem.replace("page_", "") for path in _annotation_paths(edition)]
    return jsonify({"pages": pages})


@app.get("/api/page/<page_id>")
def api_page(page_id: str):
    edition = _edition_from_request()
    logger.info(f"Received GET request for page_id: {page_id} edition: {edition}")
    try:
        path = _annotation_path(page_id, edition)
    except ValueError as e:
        logger.error(f"Invalid page_id: {page_id}. Error: {e}")
        abort(400)

    if not path.exists():
        logger.warning(f"Page not found: {page_id}")
        abort(404)

    try:
        payload = _read_payload(path)
        logger.info(f"Successfully read payload for page_id: {page_id}")
        return jsonify(payload)
    except Exception as e:
        logger.error(f"Error reading payload for page_id: {page_id}. Error: {e}")
        abort(500)


@app.post("/api/page/<page_id>")
def api_save_page(page_id: str):
    edition = _edition_from_request()
    logger.info(
        f"Received POST request to save page_id: {page_id} edition: {edition}"
    )
    try:
        path = _annotation_path(page_id, edition)
    except ValueError as e:
        logger.error(f"Invalid page_id: {page_id}. Error: {e}")
        abort(400)

    if not path.exists():
        logger.warning(f"Page not found for saving: {page_id}")
        abort(404)

    incoming = request.get_json(silent=True)
    if not isinstance(incoming, dict):
        logger.error(f"Invalid request body for page_id: {page_id}. Must be JSON object.")
        return (
            jsonify({"ok": False, "errors": ["Request body must be JSON object"]}),
            400,
        )

    incoming_page_id = str(incoming.get("page_id", ""))
    if incoming_page_id and incoming_page_id != page_id:
        logger.error(
            f"Page ID mismatch: URL says '{page_id}' but body says '{incoming_page_id}'."
        )
        return (
            jsonify(
                {
                    "ok": False,
                    "errors": [
                        f"page_id mismatch: URL says '{page_id}' but body says '{incoming_page_id}'. Refusing to overwrite."
                    ],
                }
            ),
            409,
        )

    errors = _validate_payload(incoming)
    if errors:
        logger.error(f"Validation errors for page_id: {page_id}. Errors: {errors}")
        return jsonify({"ok": False, "errors": errors}), 400

    _stamp_seq(incoming)

    try:
        existing = _read_payload(path)
    except Exception as e:
        logger.warning(f"Error reading existing payload for page_id: {page_id}. Error: {e}")
        existing = {}

    edits = _diff_payloads(existing, incoming)
    _append_edit_log(page_id, edits, edition)
    logger.info(f"Recorded {len(edits)} edits for page_id: {page_id}")

    _write_payload_atomic(path, incoming)
    logger.info(f"Successfully saved payload for page_id: {page_id}")
    return jsonify(
        {"ok": True, "meta": incoming.get("meta", {}), "edits_recorded": len(edits)}
    )


@app.get("/pdf/<page_id>")
def page_pdf(page_id: str):
    edition = _edition_from_request()
    try:
        path = _annotation_path(page_id, edition)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    payload = _read_payload(path)
    source_pdf, source_pdf_value = _resolve_source_pdf(payload)

    if not source_pdf.exists():
        return f"Source PDF not found: {source_pdf_value}", 404

    return send_file(source_pdf)


@app.get("/source-pdf/<path:pdf_name>")
def source_pdf_file(pdf_name: str):
    """Stream a PDF directly from 00_source_pdf/ by filename."""
    # Reject paths that try to escape the source dir.
    candidate = (SOURCE_PDF_DIR / pdf_name).resolve()
    try:
        candidate.relative_to(SOURCE_PDF_DIR.resolve())
    except ValueError:
        abort(400)
    if not candidate.exists() or candidate.suffix.lower() != ".pdf":
        abort(404)
    return send_file(candidate)


@app.get("/pdfjs-source")
def pdfjs_source_viewer():
    """Render the PDF.js viewer for an arbitrary source PDF + page (no annotation required)."""
    pdf_name = request.args.get("pdf", default="", type=str).strip()
    if not pdf_name:
        abort(400)
    candidate = (SOURCE_PDF_DIR / pdf_name).resolve()
    try:
        candidate.relative_to(SOURCE_PDF_DIR.resolve())
    except ValueError:
        abort(400)
    if not candidate.exists() or candidate.suffix.lower() != ".pdf":
        abort(404)

    try:
        initial_page = int(request.args.get("page", default="1", type=str))
    except (TypeError, ValueError):
        initial_page = 1
    if initial_page < 1:
        initial_page = 1

    return render_template(
        "pdf_viewer.html",
        pdf_url=url_for("source_pdf_file", pdf_name=pdf_name),
        initial_page=initial_page,
    )


@app.get("/pdfjs/<page_id>")
def pdfjs_viewer(page_id: str):
    edition = _edition_from_request()
    try:
        path = _annotation_path(page_id, edition)
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
        pdf_url=url_for("source_pdf_file", pdf_name=source_pdf.name),
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
    job_id: str,
    pdf_path: Path,
    page_num: int,
    part: str,
    page_id: str,
    overwrite: bool,
    edition: str,
) -> None:
    pilot_dir = PILOT_OCR_DIR / part
    pilot_json = pilot_dir / f"{part}_pilot_ocr.json"
    target_annotation = _annotation_path(page_id, edition)

    try:
        _job_set(job_id, state="running", message="Rendering and calling Gemini...")
        logger.info(f"Starting OCR job for page {page_id} using Gemini.")
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
            "--edition",
            edition,
        ]
        logger.info(f"Executing command: {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        logger.info(f"Subprocess stdout: {proc.stdout}")
        if proc.returncode != 0:
            logger.error(f"Subprocess stderr: {proc.stderr}")
            _job_set(
                job_id,
                state="error",
                message=f"OCR subprocess failed (code {proc.returncode}). "
                f"stderr tail: {proc.stderr[-400:].strip()}",
            )
            return

        if not pilot_json.exists():
            logger.error(f"Pilot JSON not produced: {pilot_json}")
            _job_set(job_id, state="error", message=f"Pilot JSON not produced: {pilot_json}")
            return

        records = json.loads(pilot_json.read_text(encoding="utf-8"))
        logger.info(f"OCR job completed successfully for page {page_id}.")
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

        payload = convert_record(record, source_pdf=rel_pdf, edition=edition)

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
    except Exception as e:
        logger.exception(f"Unexpected error during OCR job: {e}")
        _job_set(job_id, state="error", message=f"Unexpected error: {e}")


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
    edition = str(body.get("edition", "")).strip() or "1687_second"
    overwrite = bool(body.get("overwrite", False))

    if not pdf_name:
        return jsonify({"ok": False, "error": "pdf is required"}), 400
    if page_num < 1:
        return jsonify({"ok": False, "error": "page must be >= 1"}), 400
    if edition not in ALLOWED_EDITIONS:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"edition must be one of {sorted(ALLOWED_EDITIONS)}",
                }
            ),
            400,
        )

    # For subfoldered editions (Whitaker, Annals), the corpus is
    # single-volume per edition: we force the part name to match the
    # edition so OCR output lands in its own
    # 01_raw_ocr_output/<edition>/ directory and stays completely
    # separate from Britannicarum's part1/part2 outputs.
    if edition in SUBFOLDERED_EDITIONS:
        part = edition
    elif part not in {"part1", "part2"}:
        return jsonify({"ok": False, "error": "part must be 'part1' or 'part2'"}), 400

    pdf_path = SOURCE_PDF_DIR / pdf_name
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return jsonify({"ok": False, "error": f"PDF not found: {pdf_name}"}), 404

    page_id = f"p{page_num:04d}"
    target = _annotation_path(page_id, edition)
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
        args=(job_id, pdf_path, page_num, part, page_id, overwrite, edition),
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
