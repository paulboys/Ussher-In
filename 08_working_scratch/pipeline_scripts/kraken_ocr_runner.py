"""Kraken OCR runner script — intended to be executed inside WSL.

Processes a PDF page range through Kraken OCR and writes per-page raw text
files plus a JSON manifest compatible with the existing pilot OCR schema.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ocr_page_with_kraken(image, model_path: str) -> tuple[str, float]:
    """Run Kraken segmentation and OCR on a single PIL image.

    Returns (text, avg_confidence).
    """
    from kraken import blla, rpred
    from kraken.lib import models

    nn = models.load_any(model_path)
    baseline_seg = blla.segment(image)

    lines = []
    confidences = []

    for record in rpred.rpred(nn, image, baseline_seg):
        lines.append(record.prediction)
        if hasattr(record, "cuts") and record.cuts:
            line_confs = [
                c for c in (getattr(record, "confidences", None) or []) if c >= 0
            ]
            if line_confs:
                confidences.extend(line_confs)

    text = "\n".join(lines)
    avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else 0.0
    return text, avg_conf


def split_body_footnotes(text: str, footnote_marker: str = "[FOOTNOTES]") -> tuple[str, str]:
    """Split OCR text into body and footnote sections."""
    if footnote_marker in text:
        body, footnotes = text.split(footnote_marker, 1)
        return body.strip(), footnotes.strip()
    return text.strip(), ""


def run_kraken_pilot(
    pdf_path: Path,
    part: str,
    start_page: int,
    end_page: int,
    output_root: Path,
    model: str,
) -> Path:
    """Run Kraken OCR on a range of PDF pages and write output files."""
    from pdf2image import convert_from_path

    part_dir = output_root / part
    ensure_dir(part_dir)

    images = convert_from_path(
        str(pdf_path),
        first_page=start_page,
        last_page=end_page,
        dpi=400,
    )

    records = []
    for index, image in enumerate(images, start=start_page):
        text, avg_conf = ocr_page_with_kraken(image, model)

        page_id = f"p{index:04d}"
        txt_path = part_dir / f"page_{index:04d}_raw.txt"
        txt_path.write_text(text, encoding="utf-8")

        records.append(
            {
                "part": part,
                "page_num": index,
                "page_id": page_id,
                "ocr_engine": "kraken",
                "ocr_model": model,
                "ocr_lang": ["lat"],
                "raw_text_path": str(txt_path),
                "raw_confidence_avg": avg_conf,
                "raw_confidence_min": 0.0,
                "body_confidence_avg": avg_conf,
                "body_confidence_min": 0.0,
                "footnote_confidence_avg": 0.0,
                "footnote_confidence_min": 0.0,
                "footnote_split_enabled": False,
                "footnote_top_ratio": 0.0,
                "qc_status": "pending",
            }
        )

        print(f"  Page {index}: {len(text)} chars, confidence={avg_conf:.1f}%")

    output_json = part_dir / f"{part}_pilot_ocr.json"
    output_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kraken OCR on a PDF page range (execute inside WSL).")
    parser.add_argument("--pdf", required=True, help="Path to source PDF (WSL path)")
    parser.add_argument("--part", required=True, choices=["part1", "part2"], help="Part label")
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--output-root", default="01_raw_ocr_output", help="Output root directory")
    parser.add_argument("--model", default="default", help="Kraken model name or path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_path = run_kraken_pilot(
        pdf_path=pdf_path,
        part=args.part,
        start_page=args.start_page,
        end_page=args.end_page,
        output_root=Path(args.output_root),
        model=args.model,
    )

    print(f"Kraken OCR written to {output_path}")


if __name__ == "__main__":
    main()
