import argparse
import csv
import json
from pathlib import Path
from typing import Any


def is_locked(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() == "locked"


def clean_token(value: str) -> str:
    chars = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_"):
            chars.append(ch)
        else:
            chars.append("_")
    token = "".join(chars).strip("_")
    return token or "item"


def get_line_text(line: Any) -> str:
    if isinstance(line, dict):
        text = line.get("text_gold", "")
        return text.strip() if isinstance(text, str) else ""
    if isinstance(line, str):
        return line.strip()
    return ""


def get_line_status(line: Any) -> str:
    if isinstance(line, dict):
        value = line.get("review_status", "")
        return value.strip().lower() if isinstance(value, str) else ""
    return ""


def get_line_id(line: Any, region: str, index: int) -> str:
    if isinstance(line, dict):
        value = line.get("line_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"{region}_l{index:04d}"


def should_include_line(line: Any, page_locked: bool) -> bool:
    line_locked = is_locked(get_line_status(line))
    return page_locked or line_locked


def collect_annotation_files(annotations_dir: Path) -> list[Path]:
    files = sorted(annotations_dir.glob("page_p*.json"))
    return [file_path for file_path in files if file_path.is_file()]


def export_ground_truth(annotations_dir: Path, output_dir: Path, include_line_level_locked: bool) -> tuple[int, int]:
    lines_dir = output_dir / "lines"
    lines_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "ground_truth_manifest.csv"
    fieldnames = [
        "page_id",
        "part",
        "page_num",
        "region",
        "line_id",
        "source_annotation_file",
        "gt_file",
        "text_gold",
    ]

    files = collect_annotation_files(annotations_dir)
    pages_processed = 0
    lines_exported = 0

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for annotation_file in files:
            payload = json.loads(annotation_file.read_text(encoding="utf-8"))
            meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
            page_locked = is_locked(meta.get("review_status", ""))

            if not page_locked and not include_line_level_locked:
                continue

            page_id = str(payload.get("page_id", ""))
            part = str(payload.get("part", ""))
            page_num = payload.get("page_num", "")
            regions = payload.get("regions", {})

            if not isinstance(regions, dict):
                continue

            pages_processed += 1
            for region_name in ("header", "body", "footnote"):
                region_lines = regions.get(region_name, [])
                if not isinstance(region_lines, list):
                    continue

                for index, line in enumerate(region_lines, start=1):
                    if not should_include_line(line, page_locked):
                        continue

                    text_gold = get_line_text(line)
                    if not text_gold:
                        continue

                    line_id = get_line_id(line, region_name, index)
                    safe_page = clean_token(page_id or "page")
                    safe_line = clean_token(line_id)
                    gt_filename = f"{safe_page}__{region_name}__{safe_line}.gt.txt"
                    gt_path = lines_dir / gt_filename
                    gt_path.write_text(text_gold + "\n", encoding="utf-8")

                    writer.writerow(
                        {
                            "page_id": page_id,
                            "part": part,
                            "page_num": page_num,
                            "region": region_name,
                            "line_id": line_id,
                            "source_annotation_file": str(annotation_file),
                            "gt_file": str(gt_path),
                            "text_gold": text_gold,
                        }
                    )
                    lines_exported += 1

    return pages_processed, lines_exported


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export locked annotation JSON into line-level Tesseract ground-truth files.",
    )
    parser.add_argument(
        "--annotations-dir",
        default="08_working_scratch/phase3b/annotations",
        help="Directory containing page_pXXXX.json annotation files",
    )
    parser.add_argument(
        "--output-dir",
        default="08_working_scratch/phase3b/ground_truth/tesseract",
        help="Directory where .gt.txt files and manifest will be written",
    )
    parser.add_argument(
        "--include-line-level-locked",
        "--include-empty-pages",
        action="store_true",
        help="Include non-locked pages and export only line-level locked entries",
    )
    args = parser.parse_args()

    annotations_dir = Path(args.annotations_dir)
    output_dir = Path(args.output_dir)

    if not annotations_dir.exists():
        raise FileNotFoundError(f"Annotation directory not found: {annotations_dir}")

    pages_processed, lines_exported = export_ground_truth(
        annotations_dir=annotations_dir,
        output_dir=output_dir,
        include_line_level_locked=args.include_line_level_locked,
    )

    print(
        "Export complete. "
        f"pages_processed={pages_processed} "
        f"lines_exported={lines_exported} "
        f"output_dir={output_dir}"
    )


if __name__ == "__main__":
    main()
