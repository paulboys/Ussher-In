import argparse
import json
import re
import shutil
from pathlib import Path

import pytesseract
import logging

from core_interfaces import TextTransform
from pdf2image import convert_from_path
from ocr_adapters import GeminiOcrEngine, TesseractOcrEngine
from provider_config import load_config
from text_normalization import (
    AeHeuristicNormalizer,
    CompositeTextNormalizer,
    HistoricalNumeralNormalizer,
    LigatureNormalizer,
)


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
    lang: str,
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
            body_text, body_avg_conf, body_min_conf = score_image_text(ocr_engine, body_image, lang, body_config)
            footnote_text, footnote_avg_conf, footnote_min_conf = score_image_text(ocr_engine, footnote_image, lang, footnote_config)
        else:
            body_text, body_avg_conf, body_min_conf = score_image_text(ocr_engine, image, lang, body_config)
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
                "ocr_lang": lang.split("+"),
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


def run_gemini_pilot(
    pdf_path: Path,
    part: str,
    start_page: int,
    end_page: int,
    output_root: Path,
    provider_config_path: Path | None,
    lang: str,
) -> Path:
    logger.info("Starting Gemini OCR pipeline")
    config = load_config(provider_config_path)
    provider = config.get("gemini")
    missing = provider.missing_fields()
    if missing:
        logger.error(f"Gemini provider is not configured. Missing fields: {', '.join(missing)}")
        raise RuntimeError(
            "Gemini provider is not configured. Missing fields: "
            f"{', '.join(missing)}. Set USSHERIN_PROVIDERS_GEMINI_API_KEY or "
            "edit 06_tools_config/providers.json."
        )

    engine = GeminiOcrEngine(provider)
    text_normalizer = CompositeTextNormalizer(
        transforms=[LigatureNormalizer(), AeHeuristicNormalizer()]
    )

    part_dir = output_root / part
    ensure_dir(part_dir)

    images = convert_from_path(
        str(pdf_path),
        first_page=start_page,
        last_page=end_page,
        dpi=400,
    )

    records: list[dict] = []
    for index, image in enumerate(images, start=start_page):
        page_id = f"p{index:04d}"
        try:
            logger.info(f"Processing page {page_id} with Gemini OCR")
            detailed = engine.extract_detailed(image, lang=lang, page_id=page_id)
            logger.debug(f"Gemini API response for page {page_id}: {detailed}")
        except Exception as e:
            logger.error(f"Error during Gemini OCR for page {page_id}: {e}")
            raise

        line_records: list[dict] = []
        for alignment_index, line in enumerate(detailed.lines):
            normalized = text_normalizer.apply(line.text)
            line_records.append(
                {
                    "alignment_index": alignment_index,
                    "region": line.region,
                    "line_index": line.line_index,
                    "text_raw_ocr": line.text,
                    "normalized_form": normalized,
                    "confidence": line.confidence,
                    "illegible": line.illegible,
                    "marker_id": line.marker_id,
                    "marginalia_anchor_index": line.marginalia_anchor_index,
                }
            )

        body_text = "\n".join(
            line.text for line in detailed.lines if line.region == "body"
        )
        body_text = text_normalizer.apply(body_text)
        txt_path = part_dir / f"page_{index:04d}_raw.txt"
        txt_path.write_text(body_text, encoding="utf-8")
        logger.info(f"Written raw text for page {page_id} to {txt_path}")

        records.append(
            {
                "part": part,
                "page_num": index,
                "page_id": page_id,
                "ocr_engine": "gemini",
                "ocr_provider_model": provider.model,
                "ocr_lang": lang.split("+"),
                "raw_text_path": str(txt_path),
                "raw_confidence_avg": detailed.result.avg_confidence,
                "raw_confidence_min": detailed.result.min_confidence,
                "page_summary": detailed.page_summary,
                "lines": line_records,
                "qc_status": "pending",
            }
        )

    output_json = part_dir / f"{part}_pilot_ocr.json"
    output_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Gemini OCR results written to {output_json}")
    return output_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pilot OCR on a page range from a PDF.")
    parser.add_argument("--pdf", required=True, help="Path to source PDF")
    parser.add_argument(
        "--part",
        required=True,
        choices=[
            "part1",
            "part2",
            "whitaker_english",
            "whitaker_latin",
            "annals_latin",
            "annals_english",
        ],
        help=(
            "Part / corpus label. Ussher Britannicarum uses part1/part2; "
            "per-edition single-volume corpora use a label that matches "
            "the edition name (whitaker_english, whitaker_latin, "
            "annals_latin, annals_english). Keep this list in sync with "
            "annotation_ui.py's ALLOWED_EDITIONS."
        ),
    )
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--output-root",
        default="01_raw_ocr_output",
        help="Output root directory for OCR records",
    )
    parser.add_argument(
        "--ocr-engine",
        choices=["gemini", "kraken", "tesseract"],
        default="gemini",
        help="OCR engine to use (default: gemini)",
    )
    parser.add_argument(
        "--provider-config",
        default="06_tools_config/providers.json",
        help="Path to providers JSON config (env vars override; missing file is OK)",
    )
    parser.add_argument(
        "--kraken-model",
        default="default",
        help="Kraken model name or path (only used with --ocr-engine kraken)",
    )
    parser.add_argument(
        "--tessdata-dir",
        default="06_tools_config/tessdata",
        help="Directory containing traineddata files (default project local path)",
    )
    parser.add_argument(
        "--lang",
        default="lat+grc",
        help="Tesseract language string (default: lat+grc for Latin + Ancient Greek)",
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

    if args.ocr_engine == "gemini":
        provider_config_path = Path(args.provider_config) if args.provider_config else None
        output_path = run_gemini_pilot(
            pdf_path=Path(args.pdf),
            part=args.part,
            start_page=args.start_page,
            end_page=args.end_page,
            output_root=Path(args.output_root),
            provider_config_path=provider_config_path,
            lang=args.lang,
        )
        print(f"Gemini OCR written to {output_path}")
        return

    if args.ocr_engine == "kraken":
        # Kraken path: delegate to kraken_ocr_runner via WSL or direct call
        from wsl_paths import is_windows

        if is_windows():
            from wsl_paths import run_in_wsl, windows_to_wsl, ensure_wsl_available

            if not ensure_wsl_available():
                raise RuntimeError(
                    "WSL is not available. Install WSL2 and Ubuntu, then set up Kraken. "
                    "See 06_tools_config/wsl_kraken_setup.md"
                )

            wsl_pdf = windows_to_wsl(args.pdf)
            wsl_output = windows_to_wsl(args.output_root)
            project_root = Path(__file__).resolve().parents[2]
            wsl_script = windows_to_wsl(
                project_root / "08_working_scratch" / "pipeline_scripts" / "kraken_ocr_runner.py"
            )

            cmd = [
                "bash", "-c",
                f"source ~/kraken-env/bin/activate && python3 '{wsl_script}'"
                f" --pdf '{wsl_pdf}'"
                f" --part {args.part}"
                f" --start-page {args.start_page}"
                f" --end-page {args.end_page}"
                f" --output-root '{wsl_output}'"
                f" --model {args.kraken_model}",
            ]
            result = run_in_wsl(cmd, check=False)
            print(result.stdout)
            if result.returncode != 0:
                print(result.stderr, file=__import__("sys").stderr)
                raise RuntimeError(f"Kraken OCR failed with exit code {result.returncode}")
        else:
            # Running on Linux directly
            from kraken_ocr_runner import run_kraken_pilot

            output_path = run_kraken_pilot(
                pdf_path=Path(args.pdf),
                part=args.part,
                start_page=args.start_page,
                end_page=args.end_page,
                output_root=Path(args.output_root),
                model=args.kraken_model,
            )
            print(f"Kraken OCR written to {output_path}")

    else:
        # Tesseract fallback path
        tesseract_cmd = resolve_tesseract_cmd(args.tesseract_cmd)
        if tesseract_cmd is None:
            raise RuntimeError("Tesseract executable not found. Install Tesseract or pass --tesseract-cmd.")
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        tessdata_dir = Path(args.tessdata_dir)
        if not tessdata_dir.exists():
            raise RuntimeError(f"Tessdata directory not found: {tessdata_dir}")
        for lang_code in args.lang.split("+"):
            if not (tessdata_dir / f"{lang_code}.traineddata").exists():
                raise RuntimeError(f"Model not found: {tessdata_dir / f'{lang_code}.traineddata'}")

        tesseract_config = build_tesseract_config(tessdata_dir)

        output_path = run_pilot(
            pdf_path=Path(args.pdf),
            part=args.part,
            start_page=args.start_page,
            end_page=args.end_page,
            output_root=Path(args.output_root),
            tesseract_config=tesseract_config,
            lang=args.lang,
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
