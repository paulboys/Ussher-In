import argparse
import json
import re
from pathlib import Path


def split_body_and_footnotes(text: str) -> tuple[list[str], list[str]]:
    marker = "[FOOTNOTES]"
    if marker in text:
        body_text, footnote_text = text.split(marker, 1)
    else:
        body_text, footnote_text = text, ""

    body_lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    footnote_lines = [
        line.strip() for line in footnote_text.splitlines() if line.strip()
    ]
    return body_lines, footnote_lines


def has_ae_target(text: str) -> bool:
    return bool(re.search(r"(ae|AE|Æ|æ)", text))


def has_marker(text: str) -> bool:
    return bool(re.search(r"\[[^\]]+\]|^[\?\*!†‡]\s|\bfn\d+\b", text))


def make_line(
    page_id: str,
    region: str,
    index: int,
    text_gold: str,
    *,
    text_raw_ocr: str | None = None,
    normalized_form: str | None = None,
    alignment_index: int | None = None,
    confidence: float | None = None,
) -> dict:
    line_id = f"{page_id}_{region}_l{index:04d}"
    return {
        "page_id": page_id,
        "region": region,
        "line_id": line_id,
        "text_gold": text_gold,
        "text_raw_ocr": text_raw_ocr if text_raw_ocr is not None else text_gold,
        "normalized_form": normalized_form if normalized_form is not None else text_gold,
        "alignment_index": alignment_index if alignment_index is not None else index - 1,
        "confidence": confidence,
        "contains_ae_target": has_ae_target(text_gold),
        "contains_marker": has_marker(text_gold),
        "marker_id": "",
        "marker_link_target": "",
        "uncertain_ae": False,
        "marker_uncertain": False,
        "reviewer": "",
        "review_status": "draft",
        "notes": "",
    }


def build_payload(part: str, source_pdf: str, page_num: int, raw_text: str) -> dict:
    page_id = f"p{page_num:04d}"
    body_lines, footnote_lines = split_body_and_footnotes(raw_text)

    body_payload = [
        make_line(page_id, "body", i, text)
        for i, text in enumerate(body_lines, start=1)
    ]
    footnote_payload = [
        make_line(page_id, "footnote", i, text)
        for i, text in enumerate(footnote_lines, start=1)
    ]

    return _wrap_payload(part, source_pdf, page_num, page_id, body_payload, footnote_payload, header_payload=[])


def build_payload_from_gemini_record(part: str, source_pdf: str, record: dict) -> dict:
    """Build an annotation payload from a Gemini pilot OCR record.

    The record shape matches what ``pilot_ocr.run_gemini_pilot`` writes: a dict
    with ``page_num`` plus a ``lines`` array of structured per-line entries.
    """
    page_num = int(record["page_num"])
    page_id = record.get("page_id", f"p{page_num:04d}")
    lines = record.get("lines", [])
    if not isinstance(lines, list):
        lines = []

    region_payloads: dict[str, list[dict]] = {"header": [], "body": [], "footnote": []}
    counters: dict[str, int] = {"header": 0, "body": 0, "footnote": 0}
    for entry in lines:
        if not isinstance(entry, dict):
            continue
        region = str(entry.get("region", "body"))
        # Marginalia and catchword are folded into the body region for now;
        # downstream Go verification (Step 10) reads them from raw pilot JSON.
        if region not in region_payloads:
            region = "body"
        counters[region] += 1
        gold = str(entry.get("normalized_form") or entry.get("text_raw_ocr") or "")
        region_payloads[region].append(
            make_line(
                page_id,
                region,
                counters[region],
                gold,
                text_raw_ocr=str(entry.get("text_raw_ocr", gold)),
                normalized_form=str(entry.get("normalized_form", gold)),
                alignment_index=int(entry.get("alignment_index", counters[region] - 1)),
                confidence=(
                    float(entry["confidence"])
                    if isinstance(entry.get("confidence"), (int, float))
                    else None
                ),
            )
        )

    return _wrap_payload(
        part,
        source_pdf,
        page_num,
        page_id,
        region_payloads["body"],
        region_payloads["footnote"],
        header_payload=region_payloads["header"],
    )


def _wrap_payload(
    part: str,
    source_pdf: str,
    page_num: int,
    page_id: str,
    body_payload: list[dict],
    footnote_payload: list[dict],
    *,
    header_payload: list[dict] | None = None,
) -> dict:
    return {
        "page_id": page_id,
        "part": part,
        "source_pdf": source_pdf,
        "page_num": page_num,
        "regions": {
            "header": list(header_payload or []),
            "body": body_payload,
            "footnote": footnote_payload,
        },
        "marker_links": [],
        "meta": {
            "contains_ae_focus": any(
                line["contains_ae_target"] for line in body_payload + footnote_payload
            ),
            "contains_marker_focus": any(
                line["contains_marker"] for line in body_payload + footnote_payload
            ),
            "derived_contains_header_page_number": False,
            "derived_contains_header_chapter_number": False,
            "derived_header_page_number_side": "",
            "derived_header_chapter_side": "",
            "derived_header_parity_consistent": False,
            "contains_header_page_number": False,
            "contains_header_chapter_number": False,
            "header_page_number_side": "",
            "header_chapter_side": "",
            "header_parity_consistent": False,
            "override_contains_header_page_number_enabled": False,
            "override_contains_header_page_number_value": False,
            "override_contains_header_chapter_number_enabled": False,
            "override_contains_header_chapter_number_value": False,
            "override_header_page_number_side_enabled": False,
            "override_header_page_number_side_value": "",
            "override_header_chapter_side_enabled": False,
            "override_header_chapter_side_value": "",
            "override_header_parity_consistent_enabled": False,
            "override_header_parity_consistent_value": False,
            "annotation_status": "draft",
            "review_status": "draft",
            "reviewer": "",
            "notes": "Seeded from raw OCR output; verify against PDF and then lock reviewed lines.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Phase 3b annotation files from raw OCR text output."
    )
    parser.add_argument("--part", required=True, choices=["part1", "part2"])
    parser.add_argument("--source-pdf", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--raw-ocr-dir",
        default="01_raw_ocr_output",
        help="Root raw OCR directory containing part folders",
    )
    parser.add_argument(
        "--annotations-dir",
        default="08_working_scratch/phase3b/annotations",
        help="Output directory for annotation JSON files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing page annotation JSON files",
    )
    args = parser.parse_args()

    if args.start_page > args.end_page:
        raise ValueError("--start-page must be <= --end-page")

    raw_part_dir = Path(args.raw_ocr_dir) / args.part
    annotations_dir = Path(args.annotations_dir)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    missing_raw = 0

    for page_num in range(args.start_page, args.end_page + 1):
        page_id = f"p{page_num:04d}"
        raw_txt = raw_part_dir / f"page_{page_num:04d}_raw.txt"
        out_json = annotations_dir / f"page_{page_id}.json"

        if out_json.exists() and not args.force:
            skipped += 1
            continue

        if not raw_txt.exists():
            missing_raw += 1
            continue

        raw_text = raw_txt.read_text(encoding="utf-8")
        payload = build_payload(args.part, args.source_pdf, page_num, raw_text)
        out_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        created += 1

    print(
        "Seed complete. "
        f"created={created} skipped={skipped} missing_raw={missing_raw} "
        f"annotations_dir={annotations_dir}"
    )


if __name__ == "__main__":
    main()
