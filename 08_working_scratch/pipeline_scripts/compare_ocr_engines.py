"""Compare OCR output from Kraken and Tesseract on the same pilot pages.

Reads the pilot OCR JSON files produced by each engine and prints a
side-by-side summary of text length, confidence, and character-level
differences. Designed to run after both engines have processed the
same page range.

Usage (from project root):
    python 08_working_scratch/pipeline_scripts/compare_ocr_engines.py \
        --kraken-json 01_raw_ocr_output/part1/part1_pilot_ocr_kraken.json \
        --tesseract-json 01_raw_ocr_output/part1/part1_pilot_ocr.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_records(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_raw_text(record: dict) -> str:
    raw_path = record.get("raw_text_path", "")
    if raw_path and Path(raw_path).exists():
        return Path(raw_path).read_text(encoding="utf-8")
    return record.get("raw_text", "")


def char_diff_rate(text_a: str, text_b: str) -> float:
    """Simple character error rate: edit distance / max length."""
    if not text_a and not text_b:
        return 0.0
    max_len = max(len(text_a), len(text_b))
    if max_len == 0:
        return 0.0

    # Use a simplified LCS-based diff count for speed
    common = sum(1 for a, b in zip(text_a, text_b) if a == b)
    diff = max_len - common
    return round(diff / max_len * 100, 2)


def compare(kraken_records: list[dict], tesseract_records: list[dict]) -> list[dict]:
    tess_by_page = {r["page_id"]: r for r in tesseract_records}
    results = []

    for kr in kraken_records:
        page_id = kr["page_id"]
        ts = tess_by_page.get(page_id)
        if not ts:
            results.append({
                "page_id": page_id,
                "status": "kraken_only",
                "kraken_conf": kr.get("raw_confidence_avg", 0),
                "tesseract_conf": None,
                "char_diff_pct": None,
            })
            continue

        kr_text = read_raw_text(kr)
        ts_text = read_raw_text(ts)
        diff = char_diff_rate(kr_text, ts_text)

        results.append({
            "page_id": page_id,
            "status": "compared",
            "kraken_chars": len(kr_text),
            "tesseract_chars": len(ts_text),
            "kraken_conf": kr.get("raw_confidence_avg", 0),
            "tesseract_conf": ts.get("raw_confidence_avg", 0),
            "char_diff_pct": diff,
            "kraken_lines": kr_text.count("\n") + 1,
            "tesseract_lines": ts_text.count("\n") + 1,
        })

    return results


def print_report(results: list[dict]) -> None:
    print(f"\n{'Page':<10} {'Status':<14} {'K-Conf':>7} {'T-Conf':>7} {'K-Chars':>8} {'T-Chars':>8} {'Diff%':>6}")
    print("-" * 68)

    for r in results:
        k_conf = f"{r['kraken_conf']:.1f}" if r.get("kraken_conf") is not None else "N/A"
        t_conf = f"{r['tesseract_conf']:.1f}" if r.get("tesseract_conf") is not None else "N/A"
        k_chars = str(r.get("kraken_chars", "N/A"))
        t_chars = str(r.get("tesseract_chars", "N/A"))
        diff = f"{r['char_diff_pct']:.1f}" if r.get("char_diff_pct") is not None else "N/A"
        print(f"{r['page_id']:<10} {r['status']:<14} {k_conf:>7} {t_conf:>7} {k_chars:>8} {t_chars:>8} {diff:>6}")

    compared = [r for r in results if r["status"] == "compared"]
    if compared:
        avg_k = sum(r["kraken_conf"] for r in compared) / len(compared)
        avg_t = sum(r["tesseract_conf"] for r in compared) / len(compared)
        avg_diff = sum(r["char_diff_pct"] for r in compared) / len(compared)
        print("-" * 68)
        print(f"{'AVERAGE':<10} {'':14} {avg_k:>7.1f} {avg_t:>7.1f} {'':>8} {'':>8} {avg_diff:>6.1f}")

    print()

    # QA threshold check
    print("QA Threshold Check:")
    for r in compared:
        k = r["kraken_conf"]
        t = r["tesseract_conf"]
        if k < 75:
            print(f"  WARNING: {r['page_id']} Kraken confidence {k:.1f} < 75 (Red zone)")
        elif k < 85:
            print(f"  NOTE: {r['page_id']} Kraken confidence {k:.1f} in Yellow zone (75-85)")
        else:
            print(f"  OK: {r['page_id']} Kraken confidence {k:.1f} in Green zone")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Kraken vs Tesseract OCR output.")
    parser.add_argument("--kraken-json", required=True, help="Path to Kraken pilot OCR JSON")
    parser.add_argument("--tesseract-json", required=True, help="Path to Tesseract pilot OCR JSON")
    parser.add_argument("--output-json", default=None, help="Optional path to write comparison results as JSON")
    args = parser.parse_args()

    kr_path = Path(args.kraken_json)
    ts_path = Path(args.tesseract_json)

    if not kr_path.exists():
        print(f"Kraken JSON not found: {kr_path}", file=sys.stderr)
        sys.exit(1)
    if not ts_path.exists():
        print(f"Tesseract JSON not found: {ts_path}", file=sys.stderr)
        sys.exit(1)

    kr_records = load_records(kr_path)
    ts_records = load_records(ts_path)

    results = compare(kr_records, ts_records)
    print_report(results)

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Results written to {out}")


if __name__ == "__main__":
    main()
