"""Convert a pilot OCR JSON record into the Phase 3b annotation file format.

The pilot output (``01_raw_ocr_output/<part>/<part>_pilot_ocr.json``) is a
flat list of pages, each with a ``lines[]`` array spanning every region
(``header``, ``body``, ``marginalia``, ``catchword``).

The Phase 3b annotator expects one file per page at
``08_working_scratch/phase3b/annotations/page_pNNNN.json`` shaped roughly
as follows::

    {
      "page_id": "p0025",
      "part": "part1",
      "source_pdf": "00_source_pdf/...pdf",
      "page_num": 25,
      "regions": {
        "header":     [...],
        "body":       [...],     # body lines carry markers[] of footnote refs
        "marginalia": [...],     # raw OCR fragments preserved for provenance
        "catchword":  [...]
      },
      "footnotes": [...],        # auto-built from coalesced marginalia
      "meta": {...}
    }

Each body line whose anchor was used carries a ``markers`` array linking
into ``footnotes[]`` by ``footnote_id``. Marginalia coalescing groups
fragments that share an anchor (or attach to adjacent body lines and
appear to be a single OCR-split note) into one logical footnote.

Legacy Phase-3a æ-research fields (``contains_ae_target``,
``contains_marker``, ``uncertain_ae``, ``marker_uncertain``,
``glyph_counts``, ``marker_link_target``) are no longer written. The
loader in ``annotation_ui.py`` tolerates them on read for older files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

PHASE3B_REGIONS = ("header", "body", "marginalia", "catchword")
FOOTNOTE_KIND_DEFAULT = "citation"

ALLOWED_EDITIONS = ("1687_second", "1847_elrington_todd")
DEFAULT_EDITION = "1687_second"
# Editions whose layout has no marginalia rail (footnotes typeset at bottom
# of page). The converter still preserves any marginalia text the OCR
# returned so a later edition switch is non-destructive, but the editor
# hides the rail for these editions.
EDITIONS_WITHOUT_MARGINALIA = frozenset({"1847_elrington_todd"})


def _line_id(page_id: str, region: str, ordinal: int) -> str:
    return f"{page_id}_{region}_l{ordinal:04d}"


def _footnote_id(page_id: str, ordinal: int) -> str:
    return f"{page_id}_fn_{ordinal:03d}"


def _convert_line(
    page_id: str,
    region: str,
    ordinal: int,
    src: dict,
) -> dict:
    text_gold = str(src.get("text_raw_ocr") or src.get("normalized_form") or "")
    marker_id = str(src.get("marker_id") or "")
    anchor = src.get("marginalia_anchor_index")

    line: dict = {
        "page_id": page_id,
        "region": region,
        "line_id": _line_id(page_id, region, ordinal),
        "text_gold": text_gold,
        "text_ocr_original": text_gold,  # Frozen baseline for diff/edit log.
        "marker_id": marker_id,
        "reviewer": "",
        "review_status": "draft",
        "notes": "",
        # OCR provenance (preserved for QA, ignored by core editor).
        "ocr_confidence": src.get("confidence"),
        "ocr_illegible": bool(src.get("illegible", False)),
        "ocr_marginalia_anchor_index": anchor,
    }
    if region == "body":
        line["markers"] = []  # Populated when footnotes are built.
    return line


def _starts_with_continuation(text: str) -> bool:
    """Return True if ``text`` looks like an OCR-split continuation."""
    if not text:
        return False
    first = text[0]
    if first in ("-", "—", "–"):
        return True
    # Lowercase first letter (Latin alphabet) suggests mid-word/sentence split.
    if first.isalpha() and first.islower():
        return True
    return False


def _coalesce_marginalia_groups(
    marginalia_lines: list[dict],
    body_anchor_to_lineid: dict[int, str],
) -> list[dict]:
    """Group fragmented marginalia lines into logical notes.

    Same-anchor fragments are always coalesced. Adjacent-anchor fragments are
    coalesced only when the next fragment looks like a continuation (lowercase
    or hyphenated start). The returned groups preserve document order.
    """
    groups: list[dict] = []
    current: dict | None = None

    for src in marginalia_lines:
        anchor = src.get("ocr_marginalia_anchor_index")
        body_line_id = (
            body_anchor_to_lineid.get(anchor) if isinstance(anchor, int) else None
        )
        text = str(src.get("text_gold") or "")

        if current is None:
            current = {
                "anchor": anchor,
                "body_line_id": body_line_id,
                "fragments": [src],
                "text_parts": [text] if text else [],
            }
            continue

        same_anchor = (
            isinstance(anchor, int)
            and isinstance(current["anchor"], int)
            and anchor == current["anchor"]
        )
        adjacent_anchor = (
            isinstance(anchor, int)
            and isinstance(current["anchor"], int)
            and anchor - current["anchor"] in (0, 1)
        )
        is_continuation = adjacent_anchor and _starts_with_continuation(text)

        if same_anchor or is_continuation:
            current["fragments"].append(src)
            if text:
                current["text_parts"].append(text)
        else:
            groups.append(current)
            current = {
                "anchor": anchor,
                "body_line_id": body_line_id,
                "fragments": [src],
                "text_parts": [text] if text else [],
            }

    if current is not None:
        groups.append(current)
    return groups


def _join_fragments(text_parts: list[str]) -> str:
    """Join fragment texts, repairing OCR end-of-line hyphenation."""
    if not text_parts:
        return ""
    out = text_parts[0]
    for part in text_parts[1:]:
        if not part:
            continue
        if out.endswith(("-", "—", "–")):
            out = out[:-1] + part
        else:
            out = out + " " + part
    return out


def _build_footnotes(
    page_id: str,
    body_lines: list[dict],
    marginalia_lines: list[dict],
    body_anchor_to_lineid: dict[int, str],
) -> list[dict]:
    """Construct footnotes[] from coalesced marginalia and attach markers[]."""
    body_id_to_line = {line["line_id"]: line for line in body_lines}
    body_id_to_index = {line["line_id"]: idx for idx, line in enumerate(body_lines)}

    groups = _coalesce_marginalia_groups(marginalia_lines, body_anchor_to_lineid)

    # Stable ordering: anchored notes by body-line position; orphans last in
    # the order they appeared. This drives marker_number assignment.
    orphan_index: dict[int, int] = {id(g): i for i, g in enumerate(groups)}

    def sort_key(group: dict) -> tuple[int, int]:
        body_line_id = group.get("body_line_id")
        if body_line_id and body_line_id in body_id_to_index:
            return (0, body_id_to_index[body_line_id])
        return (1, orphan_index[id(group)])

    groups_sorted = sorted(groups, key=sort_key)

    footnotes: list[dict] = []
    for ordinal, group in enumerate(groups_sorted, start=1):
        text_gold = _join_fragments(group["text_parts"])
        body_line_id = group.get("body_line_id") or ""
        fn_id = _footnote_id(page_id, ordinal)
        source_ids = [frag.get("line_id", "") for frag in group["fragments"]]

        footnotes.append(
            {
                "footnote_id": fn_id,
                "page_id": page_id,
                "marker_number": ordinal,
                "body_line_id": body_line_id,
                "text_gold": text_gold,
                "text_ocr_original": text_gold,
                "kind": FOOTNOTE_KIND_DEFAULT,
                "source_region": "marginalia",
                "source_marginalia_line_ids": source_ids,
                "review_status": "draft",
                "notes": "",
            }
        )

        if body_line_id and body_line_id in body_id_to_line:
            body_id_to_line[body_line_id].setdefault("markers", []).append(
                {
                    "number": ordinal,
                    "footnote_id": fn_id,
                    "char_offset": None,  # null = render at end of line.
                }
            )

    return footnotes


def convert_record(
    record: dict,
    *,
    source_pdf: str | None = None,
    edition: str | None = None,
) -> dict:
    """Convert a single pilot-OCR page record into a Phase 3b payload."""
    edition_value = edition or str(record.get("edition") or "") or DEFAULT_EDITION
    if edition_value not in ALLOWED_EDITIONS:
        edition_value = DEFAULT_EDITION
    page_id = str(record.get("page_id") or f"p{int(record.get('page_num', 0)):04d}")
    part = str(record.get("part", ""))
    page_num = int(record.get("page_num", 0))

    raw_lines: list[dict] = list(record.get("lines", []))

    # First pass over body lines so marginalia anchor_index → body line_id.
    body_anchor_to_lineid: dict[int, str] = {}
    body_ordinal = 0
    for src in raw_lines:
        if src.get("region") != "body":
            continue
        body_ordinal += 1
        line_id = _line_id(page_id, "body", body_ordinal)
        line_index = src.get("line_index")
        if isinstance(line_index, int):
            body_anchor_to_lineid[line_index] = line_id

    regions: dict[str, list[dict]] = {r: [] for r in PHASE3B_REGIONS}
    region_counters: dict[str, int] = {r: 0 for r in PHASE3B_REGIONS}

    for src in raw_lines:
        region = str(src.get("region", "body"))
        # Pilot OCR output may include a "footnote" region; we no longer emit
        # one (footnotes are derived from marginalia). Map any incoming
        # footnote lines into marginalia so the text isn't lost.
        if region == "footnote":
            region = "marginalia"
        if region not in regions:
            region = "body"
        region_counters[region] += 1
        regions[region].append(
            _convert_line(
                page_id,
                region,
                region_counters[region],
                src,
            )
        )

    footnotes = _build_footnotes(
        page_id,
        regions["body"],
        regions["marginalia"],
        body_anchor_to_lineid,
    )

    payload: dict = {
        "page_id": page_id,
        "part": part,
        "edition": edition_value,
        "source_pdf": source_pdf or "",
        "page_num": page_num,
        "regions": regions,
        "footnotes": footnotes,
        "meta": {
            "reviewer": "",
            "annotation_status": "ocr_seeded",
            "review_status": "draft",
            "notes": "",
            "ocr_engine": str(record.get("ocr_engine", "")),
            "ocr_provider_model": str(record.get("ocr_provider_model", "")),
            "ocr_lang": list(record.get("ocr_lang", [])),
            "ocr_confidence_avg": record.get("raw_confidence_avg"),
            "ocr_confidence_min": record.get("raw_confidence_min"),
            "ocr_page_summary": str(record.get("page_summary", "")),
        },
    }
    return payload


def write_phase3b_files(
    pilot_records: Iterable[dict],
    out_dir: Path,
    *,
    source_pdf: str | None = None,
    edition: str | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Write one ``page_pNNNN.json`` per pilot record. Returns paths written.

    Raises ``FileExistsError`` if a target file exists and ``overwrite=False``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for record in pilot_records:
        payload = convert_record(record, source_pdf=source_pdf, edition=edition)
        target = out_dir / f"page_{payload['page_id']}.json"
        if target.exists() and not overwrite:
            raise FileExistsError(str(target))
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-json", required=True, help="Pilot OCR JSON file")
    parser.add_argument(
        "--out-dir",
        default="08_working_scratch/phase3b/annotations",
        help="Phase 3b annotations directory",
    )
    parser.add_argument("--source-pdf", default="", help="Source PDF path to embed")
    parser.add_argument(
        "--edition",
        default=DEFAULT_EDITION,
        choices=list(ALLOWED_EDITIONS),
        help="Edition key written into the payload (default: %(default)s)",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    records = json.loads(Path(args.pilot_json).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        records = [records]
    written = write_phase3b_files(
        records,
        Path(args.out_dir),
        source_pdf=args.source_pdf or None,
        edition=args.edition,
        overwrite=args.overwrite,
    )
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
