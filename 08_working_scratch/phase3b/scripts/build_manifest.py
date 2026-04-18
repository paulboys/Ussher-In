import csv
import json
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


def main() -> None:
    root = Path("08_working_scratch/phase3b")
    annotation_dir = root / "annotations"
    manifest_path = root / "manifests" / "gold_set_manifest.csv"

    annotation_files = sorted(annotation_dir.glob("page_p*.json"))

    rows = []
    for file_path in annotation_files:
        payload = read_annotation(file_path)
        meta = payload.get("meta", {})

        rows.append(
            {
                "page_id": payload.get("page_id", ""),
                "part": payload.get("part", ""),
                "source_pdf": payload.get("source_pdf", ""),
                "page_num": payload.get("page_num", ""),
                "stratum": infer_stratum(payload),
                "split": meta.get("split", ""),
                "annotation_status": meta.get("annotation_status", "draft"),
                "contains_ae_focus": str(bool(meta.get("contains_ae_focus", False))).lower(),
                "contains_marker_focus": str(bool(meta.get("contains_marker_focus", False))).lower(),
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
                "review_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Manifest updated: {manifest_path} rows={len(rows)}")


if __name__ == "__main__":
    main()
