import json
import re
import tempfile
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parents[3]
PHASE3B_ROOT = ROOT / "08_working_scratch" / "phase3b"
ANNOTATIONS_DIR = PHASE3B_ROOT / "annotations"
TEMPLATE_DIR = PHASE3B_ROOT / "ui" / "templates"
STATIC_DIR = PHASE3B_ROOT / "ui" / "static"

ALLOWED_REVIEW_STATUS = {"draft", "reviewed", "locked"}

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


def _all_lines(payload: dict) -> list[dict]:
    regions = payload.get("regions", {})
    lines = []
    for region in ("header", "body", "footnote"):
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


def _refresh_meta_flags(payload: dict) -> None:
    lines = _all_lines(payload)
    header_lines = _header_lines(payload)
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

    total_header = len(header_lines)
    for index, line in enumerate(header_lines):
        text = str(line.get("text_gold", ""))
        side = _side_for_header_index(index, total_header)

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

    header_parity_consistent = bool(
        contains_header_page_number
        and header_page_number_side in {"left", "right"}
        and expected_side in {"left", "right"}
        and header_page_number_side == expected_side
    )

    meta = payload.setdefault("meta", {})
    meta["contains_ae_focus"] = bool(contains_ae_focus)
    meta["contains_marker_focus"] = bool(contains_marker_focus)
    meta["contains_header_page_number"] = bool(contains_header_page_number)
    meta["contains_header_chapter_number"] = bool(contains_header_chapter_number)
    meta["header_page_number_side"] = header_page_number_side
    meta["header_chapter_side"] = header_chapter_side
    meta["header_parity_consistent"] = bool(header_parity_consistent)


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

    return errors


@app.get("/")
def index() -> str:
    pages = [path.stem.replace("page_", "") for path in _annotation_paths()]
    if not pages:
        return (
            "No annotation JSON files found in 08_working_scratch/phase3b/annotations",
            404,
        )
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
    return jsonify({"ok": True})


@app.get("/pdf/<page_id>")
def page_pdf(page_id: str):
    try:
        path = _annotation_path(page_id)
    except ValueError:
        abort(400)

    if not path.exists():
        abort(404)

    payload = _read_payload(path)
    source_pdf_value = str(payload.get("source_pdf", "")).strip()
    source_pdf = Path(source_pdf_value)
    if not source_pdf.is_absolute():
        candidates = [
            ROOT / source_pdf,
            ROOT / "00_source_pdf" / source_pdf_value,
        ]
        source_pdf = next(
            (candidate for candidate in candidates if candidate.exists()), source_pdf
        )

    if not source_pdf.exists():
        return f"Source PDF not found: {source_pdf_value}", 404

    return send_file(source_pdf)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
