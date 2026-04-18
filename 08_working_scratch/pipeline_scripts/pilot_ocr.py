import argparse
import json
import re
import shutil
from pathlib import Path

import pytesseract
from core_interfaces import TextTransform
from pdf2image import convert_from_path
from ocr_adapters import TesseractOcrEngine
from text_normalization import (
    AeHeuristicNormalizer,
    CompositeTextNormalizer,
    HistoricalNumeralNormalizer,
    LigatureNormalizer,
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def resolve_tesseract_cmd(user_value: str | None) -> str | None:
    if user_value:
        return user_value

    detected = shutil.which("tesseract")
    if detected:
        return detected

    default_windows_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if default_windows_path.exists():
        return str(default_windows_path)

    return None


def build_tesseract_config(tessdata_dir: Path | None) -> str:
    base = "--oem 1"
    if tessdata_dir is None:
        return base
    return f"{base} --tessdata-dir {tessdata_dir.resolve()}"


def normalize_ligatures(text: str) -> str:
    return LigatureNormalizer().apply(text)


def normalize_ae_heuristics(text: str) -> str:
    return AeHeuristicNormalizer().apply(text)


def normalize_historical_numerals(text: str) -> str:
    return HistoricalNumeralNormalizer().apply(text)


def clean_footnote_markers_in_body(text: str) -> str:
    cleaned = re.sub(r"\[([A-Za-z0-9]+)\]\??", r"[fn-\1]", text)

    lines = cleaned.splitlines()
    footnote_start = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*\[[A-Za-z0-9]+\]\s+", line):
            footnote_start = i
            break

    if footnote_start is not None:
        # Drop trailing explicit footnote block in body text output.
        lines = lines[:footnote_start]

    return "\n".join(lines).strip()


def relabel_footnotes(footnote_text: str) -> str:
    lines = [line.strip() for line in footnote_text.splitlines() if line.strip()]
    if not lines:
        return ""

    marker_pattern = re.compile(r"^([\[\(]?(?:[\?\*!†‡\d]+|[A-Z]{1,3}|[a-z])[\]\)\.]?)\s+(.*)$")
    entries = []
    current = None

    for line in lines:
        match = marker_pattern.match(line)
        if match:
            if current:
                entries.append(current)
            raw_marker = match.group(1)
            if raw_marker.islower() and len(raw_marker) > 1:
                # Treat lowercase words as continuation, not as a marker.
                current = {
                    "marker": current["marker"] if current else "?",
                    "text": f"{current['text']} {line}".strip() if current else line,
                }
                continue
            text_part = match.group(2).strip()
            current = {"marker": raw_marker, "text": text_part}
        else:
            if current is None:
                current = {"marker": "?", "text": line}
            else:
                current["text"] = f"{current['text']} {line}".strip()

    if current:
        entries.append(current)

    rendered = []
    for i, entry in enumerate(entries, start=1):
        marker = entry["marker"] if entry["marker"] else "?"
        rendered.append(f"[fn{i:02d}|{marker}] {entry['text']}")
    return "\n".join(rendered)


def score_image_text(ocr_engine: TesseractOcrEngine, image, lang: str, config: str) -> tuple[str, float, float]:
    result = ocr_engine.extract(image=image, lang=lang, config=config)
    return result.text, result.avg_confidence, result.min_confidence


def split_page_regions(image, footnote_top_ratio: float):
    width, height = image.size
    split_y = int(height * footnote_top_ratio)
    split_y = max(1, min(height - 1, split_y))
    body = image.crop((0, 0, width, split_y))
    footnotes = image.crop((0, split_y, width, height))
    return body, footnotes


def run_pilot(
    pdf_path: Path,
    part: str,
    start_page: int,
    end_page: int,
    output_root: Path,
    tesseract_config: str,
    body_psm: int,
    footnote_psm: int,
    split_footnotes: bool,
    footnote_top_ratio: float,
    normalize_open_c: bool,
    normalize_ae: bool,
) -> Path:
    part_dir = output_root / part
    ensure_dir(part_dir)

    transforms: list[TextTransform] = [LigatureNormalizer()]
    if normalize_ae:
        transforms.append(AeHeuristicNormalizer())
    if normalize_open_c:
        transforms.append(HistoricalNumeralNormalizer())
    text_normalizer = CompositeTextNormalizer(transforms=transforms)
    ocr_engine = TesseractOcrEngine()

    images = convert_from_path(
        str(pdf_path),
        first_page=start_page,
        last_page=end_page,
        dpi=400,
    )

    records = []
    for index, image in enumerate(images, start=start_page):
        body_config = f"{tesseract_config} --psm {body_psm}"
        footnote_config = f"{tesseract_config} --psm {footnote_psm}"

        if split_footnotes:
            body_image, footnote_image = split_page_regions(image, footnote_top_ratio)
            body_text, body_avg_conf, body_min_conf = score_image_text(ocr_engine, body_image, "lat", body_config)
            footnote_text, footnote_avg_conf, footnote_min_conf = score_image_text(ocr_engine, footnote_image, "lat", footnote_config)
        else:
            body_text, body_avg_conf, body_min_conf = score_image_text(ocr_engine, image, "lat", body_config)
            footnote_text, footnote_avg_conf, footnote_min_conf = "", 0.0, 0.0

        body_text = text_normalizer.apply(body_text)
        footnote_text = text_normalizer.apply(footnote_text)

        if split_footnotes:
            body_text = clean_footnote_markers_in_body(body_text)
            footnote_text = relabel_footnotes(footnote_text)

        text = body_text
        if split_footnotes and footnote_text.strip():
            text = f"{body_text}\n\n[FOOTNOTES]\n{footnote_text}"

        page_id = f"p{index:04d}"
        txt_path = part_dir / f"page_{index:04d}_raw.txt"
        txt_path.write_text(text, encoding="utf-8")

        records.append(
            {
                "part": part,
                "page_num": index,
                "page_id": page_id,
                "ocr_engine": "tesseract",
                "ocr_lang": ["lat"],
                "raw_text_path": str(txt_path),
                "raw_confidence_avg": body_avg_conf,
                "raw_confidence_min": body_min_conf,
                "body_confidence_avg": body_avg_conf,
                "body_confidence_min": body_min_conf,
                "footnote_confidence_avg": footnote_avg_conf,
                "footnote_confidence_min": footnote_min_conf,
                "footnote_split_enabled": split_footnotes,
                "footnote_top_ratio": footnote_top_ratio,
                "body_psm": body_psm,
                "footnote_psm": footnote_psm,
                "qc_status": "pending",
            }
        )

    output_json = part_dir / f"{part}_pilot_ocr.json"
    output_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pilot OCR on a page range from a PDF.")
    parser.add_argument("--pdf", required=True, help="Path to source PDF")
    parser.add_argument("--part", required=True, choices=["part1", "part2"], help="Part label")
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--output-root",
        default="01_raw_ocr_output",
        help="Output root directory for OCR records",
    )
    parser.add_argument(
        "--tessdata-dir",
        default="06_tools_config/tessdata",
        help="Directory containing traineddata files (default project local path)",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Explicit path to tesseract executable if not on PATH",
    )
    parser.add_argument(
        "--body-psm",
        type=int,
        default=3,
        help="Tesseract page segmentation mode for body region",
    )
    parser.add_argument(
        "--footnote-psm",
        type=int,
        default=6,
        help="Tesseract page segmentation mode for footnote region",
    )
    parser.add_argument(
        "--split-footnotes",
        action="store_true",
        help="Split page into body and footnote regions before OCR",
    )
    parser.add_argument(
        "--footnote-top-ratio",
        type=float,
        default=0.88,
        help="Vertical split ratio where footnotes begin (0.0-1.0)",
    )
    parser.add_argument(
        "--normalize-open-c",
        action="store_true",
        help="Normalize common OCR confusions for historical open-C numeral forms",
    )
    parser.add_argument(
        "--normalize-ae",
        action="store_true",
        help="Apply heuristic fixes for common OCR losses of ae/AE in Latin words",
    )
    args = parser.parse_args()

    tesseract_cmd = resolve_tesseract_cmd(args.tesseract_cmd)
    if tesseract_cmd is None:
        raise RuntimeError("Tesseract executable not found. Install Tesseract or pass --tesseract-cmd.")
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    tessdata_dir = Path(args.tessdata_dir)
    if not tessdata_dir.exists():
        raise RuntimeError(f"Tessdata directory not found: {tessdata_dir}")
    if not (tessdata_dir / "lat.traineddata").exists():
        raise RuntimeError(f"Latin model not found: {tessdata_dir / 'lat.traineddata'}")

    tesseract_config = build_tesseract_config(tessdata_dir)

    output_path = run_pilot(
        pdf_path=Path(args.pdf),
        part=args.part,
        start_page=args.start_page,
        end_page=args.end_page,
        output_root=Path(args.output_root),
        tesseract_config=tesseract_config,
        body_psm=args.body_psm,
        footnote_psm=args.footnote_psm,
        split_footnotes=args.split_footnotes,
        footnote_top_ratio=args.footnote_top_ratio,
        normalize_open_c=args.normalize_open_c,
        normalize_ae=args.normalize_ae,
    )

    print(f"Pilot OCR written to {output_path}")


if __name__ == "__main__":
    main()
