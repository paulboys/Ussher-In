import argparse
import csv
import json
from pathlib import Path


def severity_from_confidence(avg_conf: float) -> str:
    if avg_conf < 75:
        return "red"
    if avg_conf < 85:
        return "yellow"
    return "green"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build QA CSV from pilot OCR JSON.")
    parser.add_argument("--input-json", required=True, help="Path to pilot OCR JSON")
    parser.add_argument("--output-csv", required=True, help="Path to QA CSV output")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output_csv)

    records = json.loads(input_path.read_text(encoding="utf-8"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "part",
            "page_num",
            "page_id",
            "avg_confidence",
            "severity",
            "review_required",
            "reviewed_by",
            "review_date",
            "qc_status",
            "notes",
        ])

        for row in records:
            avg_conf = float(row.get("raw_confidence_avg", 0.0))
            severity = severity_from_confidence(avg_conf)
            review_required = "yes" if severity in ("red", "yellow") else "no"
            writer.writerow([
                row.get("part", ""),
                row.get("page_num", ""),
                row.get("page_id", ""),
                avg_conf,
                severity,
                review_required,
                "",
                "",
                row.get("qc_status", "pending"),
                "",
            ])

    print(f"QA CSV written to {output_path}")


if __name__ == "__main__":
    main()
