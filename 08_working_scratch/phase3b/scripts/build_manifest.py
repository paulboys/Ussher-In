import csv
import json
import re
from pathlib import Path


def read_annotation(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_stratum(payload: dict) -> str:
    ae = bool(payload.get("meta", {}).get("contains_ae_focus", False))
    marker = bool(payload.get("meta", {}).get("contains_marker_focus", False))
    if ae and marker:
        return "mixed_layout"
    if ae:
        return "ae_dense"
    if marker:
        return "footnote_heavy"
    return "unassigned"


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


def derive_header_meta(payload: dict) -> dict:
    regions = payload.get("regions", {})
    header_lines = regions.get("header", []) if isinstance(regions, dict) else []
    if not isinstance(header_lines, list):
        header_lines = []

    page_num_value = payload.get("page_num")
    try:
        page_num = int(page_num_value)
    except (TypeError, ValueError):
        page_num = None

    page_side = ""
    chapter_side = ""
    contains_page = False
    contains_chapter = False

    total_header = len(header_lines)
    for index, line in enumerate(header_lines):
        if not isinstance(line, dict):
            continue
        text = str(line.get("text_gold", ""))
        side = _side_for_header_index(index, total_header)

        if page_num is not None and re.search(rf"(?<!\\d){page_num}(?!\\d)", text):
            contains_page = True
            if side in {"left", "right"} and page_side == "":
                page_side = side

        if re.search(r"\bCAP\.?\s*[IVXLCDM]+\.?\b", text, flags=re.IGNORECASE):
            contains_chapter = True
            if side in {"left", "right"} and chapter_side == "":
                chapter_side = side

    expected_side = _expected_page_number_side(page_num)
    if contains_page and page_side == "" and expected_side:
        page_side = expected_side

    parity_ok = bool(
        contains_page
        and page_side in {"left", "right"}
        and expected_side in {"left", "right"}
        and page_side == expected_side
    )

    return {
        "contains_header_page_number": contains_page,
        "contains_header_chapter_number": contains_chapter,
        "header_page_number_side": page_side,
        "header_chapter_side": chapter_side,
        "header_parity_consistent": parity_ok,
    }


def main() -> None:
    root = Path("08_working_scratch/phase3b")
    annotation_dir = root / "annotations"
    manifest_path = root / "manifests" / "gold_set_manifest.csv"

    annotation_files = sorted(annotation_dir.glob("page_p*.json"))

    rows = []
    for file_path in annotation_files:
        payload = read_annotation(file_path)
        meta = payload.get("meta", {})
        derived_header_meta = derive_header_meta(payload)

        rows.append(
            {
                "page_id": payload.get("page_id", ""),
                "part": payload.get("part", ""),
                "source_pdf": payload.get("source_pdf", ""),
                "page_num": payload.get("page_num", ""),
                "stratum": infer_stratum(payload),
                "split": meta.get("split", ""),
                "annotation_status": meta.get("annotation_status", "draft"),
                "contains_ae_focus": str(
                    bool(meta.get("contains_ae_focus", False))
                ).lower(),
                "contains_marker_focus": str(
                    bool(meta.get("contains_marker_focus", False))
                ).lower(),
                "contains_header_page_number": str(
                    bool(
                        meta.get(
                            "contains_header_page_number",
                            derived_header_meta["contains_header_page_number"],
                        )
                    )
                ).lower(),
                "contains_header_chapter_number": str(
                    bool(
                        meta.get(
                            "contains_header_chapter_number",
                            derived_header_meta["contains_header_chapter_number"],
                        )
                    )
                ).lower(),
                "header_page_number_side": str(
                    meta.get(
                        "header_page_number_side",
                        derived_header_meta["header_page_number_side"],
                    )
                ),
                "header_chapter_side": str(
                    meta.get(
                        "header_chapter_side",
                        derived_header_meta["header_chapter_side"],
                    )
                ),
                "header_parity_consistent": str(
                    bool(
                        meta.get(
                            "header_parity_consistent",
                            derived_header_meta["header_parity_consistent"],
                        )
                    )
                ).lower(),
                "review_status": meta.get("review_status", "draft"),
                "notes": meta.get("notes", ""),
            }
        )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "page_id",
                "part",
                "source_pdf",
                "page_num",
                "stratum",
                "split",
                "annotation_status",
                "contains_ae_focus",
                "contains_marker_focus",
                "contains_header_page_number",
                "contains_header_chapter_number",
                "header_page_number_side",
                "header_chapter_side",
                "header_parity_consistent",
                "review_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Manifest updated: {manifest_path} rows={len(rows)}")


if __name__ == "__main__":
    main()
