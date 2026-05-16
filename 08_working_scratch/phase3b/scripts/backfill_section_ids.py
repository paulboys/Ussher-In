"""Backfill section_id and printed_page_num on existing annotation JSONs.

Reads all whitaker_english (or whitaker_latin) annotation files in reading
order, detects chapter headings from the already-OCR'd text, and carries the
current section_id forward to every page until the next heading is found.

Also extracts printed_page_num from the header region if not already set.

Run from the project root:
    python 08_working_scratch/phase3b/scripts/backfill_section_ids.py
    python 08_working_scratch/phase3b/scripts/backfill_section_ids.py --edition whitaker_latin
    python 08_working_scratch/phase3b/scripts/backfill_section_ids.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANNOTATIONS_DIR = ROOT / "08_working_scratch" / "phase3b" / "annotations"

# ---------------------------------------------------------------------------
# Roman numeral conversion
# ---------------------------------------------------------------------------

_ROMAN_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100,  "C"), (90,  "XC"), (50,  "L"), (40,  "XL"),
    (10,   "X"), (9,   "IX"), (5,   "V"), (4,   "IV"), (1, "I"),
]


def roman_to_int(s: str) -> int | None:
    """Convert a Roman numeral string to int, or return None if invalid."""
    s = s.upper().strip()
    if not s:
        return None
    val = 0
    i = 0
    for arabic, roman in _ROMAN_VALUES:
        while s[i : i + len(roman)] == roman:
            val += arabic
            i += len(roman)
            if i >= len(s):
                break
    return val if i == len(s) and val > 0 else None


# ---------------------------------------------------------------------------
# Latin ordinal word -> int (Whitaker Latin headings use classical spelling)
# ---------------------------------------------------------------------------

_LATIN_ORDINALS: dict[str, int] = {
    "PRIMVM": 1, "PRIMUM": 1, "PRIMA": 1, "PRIMUS": 1,
    "SECVNDVM": 2, "SECUNDVM": 2, "SECUNDUM": 2, "SECUNDA": 2,
    "TERTIVM": 3, "TERTIUM": 3, "TERTIA": 3,
    "QVARTVM": 4, "QUARTVM": 4, "QUARTUM": 4, "QUARTA": 4,
    "QVINTVM": 5, "QUINTVM": 5, "QUINTUM": 5, "QUINTA": 5,
    "SEXTVM": 6, "SEXTUM": 6, "SEXTA": 6,
    "SEPTIMVM": 7, "SEPTIMUM": 7,
    "OCTAVVM": 8, "OCTAVUM": 8,
    "NONVM": 9, "NONUM": 9,
    "DECIMVM": 10, "DECIMUM": 10,
}

# Controversy ordinals (English)
_ENGLISH_ORDINALS: dict[str, int] = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5,
    "SIXTH": 6, "SEVENTH": 7, "EIGHTH": 8, "NINTH": 9, "TENTH": 10,
}

# ---------------------------------------------------------------------------
# Heading detection patterns
# ---------------------------------------------------------------------------

# English: "CHAPTER II." or "CHAPTER II" (with optional trailing period/colon)
_EN_CHAPTER_RE = re.compile(r"\bCHAPTER\s+([IVXLCDM]+)\b", re.IGNORECASE)
# English: "THE FIRST CONTROVERSY." / "THE SECOND CONTROVERSY"
_EN_CONTROVERSY_RE = re.compile(r"\bTHE\s+(\w+)\s+CONTROVERSY\b", re.IGNORECASE)

# Latin: "CAPVT SECVNDVM" / "CAPUT SECUNDUM"
_LAT_CHAPTER_RE = re.compile(r"\bCAP[VU]T\s+(\w+)\b", re.IGNORECASE)
# Latin: "CONTROVERSIA PRIMA" etc.
_LAT_CONTROVERSY_RE = re.compile(r"\bCONTROVERSIA\s+(\w+)\b", re.IGNORECASE)


def _detect_controversy(text: str, edition: str) -> int | None:
    if "english" in edition:
        m = _EN_CONTROVERSY_RE.search(text)
        if m:
            return _ENGLISH_ORDINALS.get(m.group(1).upper())
    else:
        m = _LAT_CONTROVERSY_RE.search(text)
        if m:
            return _LATIN_ORDINALS.get(m.group(1).upper())
    return None


def _detect_chapter(text: str, edition: str) -> int | None:
    if "english" in edition:
        m = _EN_CHAPTER_RE.search(text)
        if m:
            return roman_to_int(m.group(1))
    else:
        m = _LAT_CHAPTER_RE.search(text)
        if m:
            return _LATIN_ORDINALS.get(m.group(1).upper()) or roman_to_int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Printed page number extraction from header lines
# ---------------------------------------------------------------------------

# Header lines typically look like: "38 THE FIRST CONTROVERSY. [CH."
# or "1.] QUESTION THE FIRST. 27"  (page number at end)
# or just "x" / "xi" (Roman, front matter)

_ARABIC_RE = re.compile(r"^\s*(\d+)\b|\b(\d+)\s*$")
_ROMAN_HEADER_RE = re.compile(r"^\s*([ivxlcdmIVXLCDM]+)\.?\s*$")


def _extract_printed_page(header_text: str) -> str:
    """Best-effort extraction of the printed page number from a header line."""
    # Try Arabic number at start or end of line
    m = _ARABIC_RE.search(header_text)
    if m:
        return m.group(1) or m.group(2) or ""
    # Try a header line that is purely a Roman numeral
    m = _ROMAN_HEADER_RE.match(header_text)
    if m and roman_to_int(m.group(1)) is not None:
        return m.group(1).lower()
    return ""


# ---------------------------------------------------------------------------
# Page sort key (mirrors annotation_ui.py logic)
# ---------------------------------------------------------------------------

def _sort_key(path: Path) -> tuple[int, int]:
    stem = path.stem  # "page_p0024"
    page_id = stem.replace("page_", "")
    physical = int(page_id[1:]) if page_id.startswith("p") and page_id[1:].isdigit() else 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        roi = payload.get("reading_order_index")
        if isinstance(roi, bool):
            roi = None
        if isinstance(roi, int):
            return (roi, physical)
        if isinstance(roi, float) and roi.is_integer():
            return (int(roi), physical)
    except Exception:
        pass
    return (physical, physical)


# ---------------------------------------------------------------------------
# Main backfill logic
# ---------------------------------------------------------------------------

def _all_line_texts(payload: dict, regions: tuple[str, ...] = ("header", "body")) -> list[str]:
    out = []
    for r in regions:
        for line in payload.get("regions", {}).get(r, []):
            t = str(line.get("text_gold") or line.get("text_ocr_original") or "").strip()
            if t:
                out.append(t)
    return out


def _header_texts(payload: dict) -> list[str]:
    return _all_line_texts(payload, ("header",))


def backfill(edition: str, dry_run: bool, overwrite_section: bool) -> None:
    ann_dir = ANNOTATIONS_DIR / edition
    if not ann_dir.exists():
        print(f"Annotations directory not found: {ann_dir}", file=sys.stderr)
        sys.exit(1)

    paths = sorted(ann_dir.glob("page_p*.json"), key=_sort_key)
    if not paths:
        print("No annotation files found.", file=sys.stderr)
        sys.exit(1)

    current_controversy = 1  # assume Controversy I until detected otherwise
    current_chapter: int | None = None
    changed = 0

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        dirty = False

        # Collect all text from header + body regions
        all_texts = _all_line_texts(payload, ("header", "body"))
        full_text = " ".join(all_texts)

        # --- Detect controversy change ---
        detected_controversy = _detect_controversy(full_text, edition)
        if detected_controversy is not None:
            current_controversy = detected_controversy

        # --- Detect chapter heading ---
        detected_chapter = _detect_chapter(full_text, edition)
        if detected_chapter is not None:
            current_chapter = detected_chapter

        # --- Determine section_id for this page ---
        if current_chapter is not None:
            new_section_id = f"c{current_controversy}_ch{current_chapter}"
        else:
            new_section_id = "front_matter"

        # --- Update section_id (only if not set, unless --overwrite-section) ---
        existing_section_id = payload.get("section_id", "")
        if not existing_section_id or overwrite_section:
            if payload.get("section_id") != new_section_id:
                payload["section_id"] = new_section_id
                dirty = True

        # --- Extract printed_page_num from header if not already set ---
        existing_ppn = payload.get("printed_page_num", "")
        if not existing_ppn:
            header_lines = _header_texts(payload)
            for hl in header_lines:
                extracted = _extract_printed_page(hl)
                if extracted:
                    payload["printed_page_num"] = extracted
                    dirty = True
                    break

        # --- Write back ---
        page_id = payload.get("page_id", path.stem)
        section_label = payload.get("section_id", new_section_id)
        ppn_label = payload.get("printed_page_num", "")
        status = "CHANGED" if dirty else "ok"
        print(
            f"  {path.name}  section={section_label!r:16s}  "
            f"printed_page={ppn_label!r:6s}  [{status}]"
        )

        if dirty and not dry_run:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", delete=False,
                dir=str(path.parent), suffix=".tmp"
            ) as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            Path(fh.name).replace(path)
            changed += 1

    if dry_run:
        print(f"\nDry run — no files written. Would have updated {sum(1 for p in paths if True)} pages.")
    else:
        print(f"\nDone. Updated {changed} of {len(paths)} files.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill section_id and printed_page_num on annotation JSONs.")
    parser.add_argument(
        "--edition",
        choices=["whitaker_english", "whitaker_latin"],
        default="whitaker_english",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing files.",
    )
    parser.add_argument(
        "--overwrite-section",
        action="store_true",
        help="Overwrite section_id even if already set (default: skip already-tagged pages).",
    )
    args = parser.parse_args()
    backfill(args.edition, args.dry_run, args.overwrite_section)


if __name__ == "__main__":
    main()
