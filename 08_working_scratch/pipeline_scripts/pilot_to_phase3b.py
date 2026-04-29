"""Convert a pilot OCR JSON record into the Phase 3b annotation file format.

The pilot output (``01_raw_ocr_output/<part>/<part>_pilot_ocr.json``) is a
flat list of pages, each with a ``lines[]`` array spanning every region
(``header``, ``body``, ``footnote``, ``marginalia``, ``catchword``).

The Phase 3b annotator expects one file per page at
``08_working_scratch/phase3b/annotations/page_pNNNN.json`` with a
``regions`` dict. We extend that schema with two new regions so Gemini's
marginalia and catchword output round-trip cleanly:

    {
      "regions": {
        "header": [...],
        "body": [...],
        "footnote": [...],
        "marginalia": [...],   # NEW: each line carries marker_id and
                               #      anchor_index pointing into body
        "catchword": [...]     # NEW: typically a single bottom-right token
      }
    }

The Gemini transcription is written into ``text_gold`` directly so the
annotator can edit-in-place; ``confidence`` and ``illegible`` are
preserved as ``ocr_confidence`` and ``ocr_illegible`` for QA filtering.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

PHASE3B_REGIONS = ("header", "body", "footnote", "marginalia", "catchword")


def _line_id(page_id: str, region: str, ordinal: int) -> str:
    return f"{page_id}_{region}_l{ordinal:04d}"


def _convert_line(
    page_id: str,
    region: str,
    ordinal: int,
    src: dict,
    body_anchor_to_lineid: dict[int, str] | None = None,
) -> dict:
    text_gold = str(src.get("text_raw_ocr") or src.get("normalized_form") or "")
    marker_id = str(src.get("marker_id") or "")
    anchor = src.get("marginalia_anchor_index")
    marker_link_target = ""
    if (
        region == "marginalia"
        and isinstance(anchor, int)
        and body_anchor_to_lineid
        and anchor in body_anchor_to_lineid
    ):
        marker_link_target = body_anchor_to_lineid[anchor]

    return {
        "page_id": page_id,
        "region": region,
        "line_id": _line_id(page_id, region, ordinal),
        "text_gold": text_gold,
        "contains_ae_target": bool(re.search(r"æ|Æ|ae|AE", text_gold)),
        "contains_marker": bool(marker_id),
        "marker_id": marker_id,
        "marker_link_target": marker_link_target,
        "uncertain_ae": False,
        "marker_uncertain": False,
        "reviewer": "",
        "review_status": "draft",
        "notes": "",
        # OCR provenance (preserved for QA, ignored by core editor).
        "ocr_confidence": src.get("confidence"),
        "ocr_illegible": bool(src.get("illegible", False)),
        "ocr_marginalia_anchor_index": anchor,
    }


def convert_record(record: dict, *, source_pdf: str | None = None) -> dict:
    """Convert a single pilot-OCR page record into a Phase 3b payload."""
    page_id = str(record.get("page_id") or f"p{int(record.get('page_num', 0)):04d}")
    part = str(record.get("part", ""))
    page_num = int(record.get("page_num", 0))

    raw_lines: list[dict] = list(record.get("lines", []))

    # First pass over body lines so marginalia anchor_index → line_id can map.
    body_anchor_to_lineid: dict[int, str] = {}
    body_ordinal = 0
    for src in raw_lines:
        if src.get("region") != "body":
            continue
        body_ordinal += 1
        line_id = _line_id(page_id, "body", body_ordinal)
        line_index = src.get("line_index")
        if isinstance(line_index, int):
            body_anchor_to_lineid[line_index] = line_id

    regions: dict[str, list[dict]] = {r: [] for r in PHASE3B_REGIONS}
    region_counters: dict[str, int] = {r: 0 for r in PHASE3B_REGIONS}

    for src in raw_lines:
        region = str(src.get("region", "body"))
        if region not in regions:
            region = "body"
        region_counters[region] += 1
        regions[region].append(
            _convert_line(
                page_id,
                region,
                region_counters[region],
                src,
                body_anchor_to_lineid=body_anchor_to_lineid,
            )
        )

    payload: dict = {
        "page_id": page_id,
        "part": part,
        "source_pdf": source_pdf or "",
        "page_num": page_num,
        "regions": regions,
        "meta": {
            "reviewer": "",
            "annotation_status": "ocr_seeded",
            "review_status": "draft",
            "notes": "",
            "ocr_engine": str(record.get("ocr_engine", "")),
            "ocr_provider_model": str(record.get("ocr_provider_model", "")),
            "ocr_lang": list(record.get("ocr_lang", [])),
            "ocr_confidence_avg": record.get("raw_confidence_avg"),
            "ocr_confidence_min": record.get("raw_confidence_min"),
            "ocr_page_summary": str(record.get("page_summary", "")),
        },
    }
    return payload


def write_phase3b_files(
    pilot_records: Iterable[dict],
    out_dir: Path,
    *,
    source_pdf: str | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Write one ``page_pNNNN.json`` per pilot record. Returns paths written.

    Raises ``FileExistsError`` if a target file exists and ``overwrite=False``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for record in pilot_records:
        payload = convert_record(record, source_pdf=source_pdf)
        target = out_dir / f"page_{payload['page_id']}.json"
        if target.exists() and not overwrite:
            raise FileExistsError(str(target))
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-json", required=True, help="Pilot OCR JSON file")
    parser.add_argument(
        "--out-dir",
        default="08_working_scratch/phase3b/annotations",
        help="Phase 3b annotations directory",
    )
    parser.add_argument("--source-pdf", default="", help="Source PDF path to embed")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    records = json.loads(Path(args.pilot_json).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        records = [records]
    written = write_phase3b_files(
        records,
        Path(args.out_dir),
        source_pdf=args.source_pdf or None,
        overwrite=args.overwrite,
    )
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
