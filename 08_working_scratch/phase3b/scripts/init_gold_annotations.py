import argparse
import json
from pathlib import Path


def create_page_template(part: str, source_pdf: str, page_num: int) -> dict:
    page_id = f"p{page_num:04d}"
    return {
        "page_id": page_id,
        "part": part,
        "source_pdf": source_pdf,
        "page_num": page_num,
        "regions": {
            "header": [],
            "body": [],
            "footnote": [],
        },
        "marker_links": [],
        "meta": {
            "contains_ae_focus": False,
            "contains_marker_focus": False,
            "annotation_status": "draft",
            "review_status": "draft",
            "reviewer": "",
            "notes": "",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Phase 3b annotation JSON files for a page range.")
    parser.add_argument("--part", required=True, choices=["part1", "part2"])
    parser.add_argument("--source-pdf", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--output-dir",
        default="08_working_scratch/phase3b/annotations",
        help="Directory to write annotation JSON files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing page files if present",
    )
    args = parser.parse_args()

    if args.start_page > args.end_page:
        raise ValueError("--start-page must be <= --end-page")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for page_num in range(args.start_page, args.end_page + 1):
        page_id = f"p{page_num:04d}"
        target = output_dir / f"page_{page_id}.json"

        if target.exists() and not args.force:
            skipped += 1
            continue

        payload = create_page_template(args.part, args.source_pdf, page_num)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        created += 1

    print(f"Annotation init complete. created={created} skipped={skipped} output_dir={output_dir}")


if __name__ == "__main__":
    main()
