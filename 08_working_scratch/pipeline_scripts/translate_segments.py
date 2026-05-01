"""Translate locked Phase 3b annotation pages via the Claude CLI.

This runner is invoked from the workspace root, e.g.::

    python 08_working_scratch/pipeline_scripts/translate_segments.py \\
        --part part1 --start-page 36 --end-page 36 --dry-run

It performs four jobs:

1. Loads each Phase 3b annotation JSON for the requested page range.
2. Extracts the units to translate using the gating policy:
     * body lines: only those with ``review_status == 'locked'``
     * footnotes: any whose ``body_line_id`` references a selected
       body line, regardless of footnote review_status
3. For each page, builds a single translation prompt (whole-page
   context, lexicon hints) and either prints it (``--dry-run``) or
   sends it through ``AnthropicTranslationAdapter``.
4. Writes append-only translation artifacts under
   ``03_segmented_text/<part>/segments_with_translations.jsonl`` and a
   per-run log under ``03_segmented_text/<part>/.logs/``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

# Allow execution either as a module or as a script.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from provider_config import default_config  # noqa: E402
from translation_adapters import (  # noqa: E402
    AnthropicTranslationAdapter,
    TranslationError,
    TranslationResult,
    TranslationUnit,
)
from translation_prompts import (  # noqa: E402
    LEXICON_PROFILES,
    build_translation_prompt,
)

# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = _HERE.parent.parent  # .../UssherIn
ANNOTATIONS_DIR = WORKSPACE_ROOT / "08_working_scratch" / "phase3b" / "annotations"
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"


# ---------------------------------------------------------------------------
# Page loading + extraction
# ---------------------------------------------------------------------------


def load_phase3b_page(path: Path) -> dict:
    """Load and minimally validate a Phase 3b annotation payload."""
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    for required in ("page_id", "regions", "footnotes"):
        if required not in payload:
            raise ValueError(
                f"{path.name}: missing required field {required!r}"
            )
    return payload


def extract_units(payload: dict) -> tuple[list[dict], list[dict]]:
    """Return ``(body_lines, linked_footnotes)`` to translate.

    Gating policy:
      * body: ``review_status == 'locked'`` only.
      * footnotes: include any whose ``body_line_id`` references a
        selected body line, regardless of footnote review_status.
    """

    regions = payload.get("regions", {}) or {}
    body = regions.get("body", []) or []
    selected_body = [
        line for line in body if (line.get("review_status") == "locked")
    ]
    selected_ids = {line.get("line_id") for line in selected_body}

    all_footnotes = payload.get("footnotes", []) or []
    linked_footnotes = [
        fn for fn in all_footnotes
        if fn.get("body_line_id") in selected_ids
    ]
    return selected_body, linked_footnotes


# ---------------------------------------------------------------------------
# Artifact writing (idempotent / append-only translation_history)
# ---------------------------------------------------------------------------


def _artifact_path_for_part(part: str) -> Path:
    return ARTIFACTS_DIR / part / "segments_with_translations.jsonl"


def _logs_dir_for_part(part: str) -> Path:
    return ARTIFACTS_DIR / part / ".logs"


def load_existing_segments(part: str) -> dict[str, dict]:
    """Read the JSONL artifact (if present) keyed by ``segment_id``."""
    path = _artifact_path_for_part(part)
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}: malformed JSON on line {line_no}: {exc}"
                ) from exc
            seg_id = record.get("segment_id")
            if seg_id:
                out[seg_id] = record
    return out


def _build_segment_record(
    *,
    page_id: str,
    segment_id: str,
    segment_type: str,
    latin_text: str,
    unit: TranslationUnit | None,
    source_unit_id: str,
    extra_links: dict[str, Any] | None = None,
    timestamp: str,
    model: str,
    lexicon_profile: str,
) -> dict:
    """Build the persisted segment record matching SCHEMA.md semantics."""

    history_entry: dict[str, Any] = {
        "version": 1,
        "stage": "machine_draft",
        "timestamp": timestamp,
        "english": unit.english if unit else "",
        "notes": unit.notes if unit else "",
        "uncertain": bool(unit.uncertain) if unit else True,
        "model": model,
        "lexicon_profile": lexicon_profile,
        "source_unit_id": source_unit_id,
    }
    record: dict[str, Any] = {
        "segment_id": segment_id,
        "page_id": page_id,
        "segment_type": segment_type,
        "latin_text": latin_text,
        "translation_history": [history_entry],
        "final_english": "",
        "translation_status": "machine_draft" if unit else "pending",
    }
    if extra_links:
        record.update(extra_links)
    return record


def _append_translation_history(
    existing: dict,
    *,
    unit: TranslationUnit | None,
    timestamp: str,
    model: str,
    lexicon_profile: str,
    source_unit_id: str,
) -> dict:
    """Append a new translation_history version to an existing record."""
    history = list(existing.get("translation_history") or [])
    next_version = (history[-1]["version"] + 1) if history else 1
    history.append({
        "version": next_version,
        "stage": "machine_draft",
        "timestamp": timestamp,
        "english": unit.english if unit else "",
        "notes": unit.notes if unit else "",
        "uncertain": bool(unit.uncertain) if unit else True,
        "model": model,
        "lexicon_profile": lexicon_profile,
        "source_unit_id": source_unit_id,
    })
    updated = dict(existing)
    updated["translation_history"] = history
    if existing.get("translation_status") in (None, "", "pending"):
        updated["translation_status"] = "machine_draft"
    return updated


def write_segments(part: str, segments: dict[str, dict]) -> Path:
    """Rewrite the part's JSONL artifact from the in-memory map."""
    path = _artifact_path_for_part(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for seg_id in sorted(segments.keys()):
            handle.write(json.dumps(segments[seg_id], ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Page-level orchestration
# ---------------------------------------------------------------------------


def _segment_id_for_body(line: dict) -> str:
    return f"seg_{line.get('line_id', 'unknown')}"


def _segment_id_for_footnote(fn: dict) -> str:
    return f"seg_{fn.get('footnote_id', 'unknown')}"


def translate_page(
    payload: dict,
    *,
    adapter: AnthropicTranslationAdapter | None,
    existing_segments: dict[str, dict],
    lexicon_profile: str,
    extra_context: str | None,
    force: bool,
    dry_run: bool,
    timestamp: str,
) -> dict[str, Any]:
    """Translate one page payload and update *existing_segments* in place.

    Returns a per-page log dict.
    """

    page_id = payload["page_id"]
    body_lines, footnotes = extract_units(payload)

    # Idempotency: skip units that already have at least one history entry,
    # unless --force is set.
    units_for_prompt: list[dict] = []
    fns_for_prompt: list[dict] = []
    skipped: list[str] = []

    if force:
        units_for_prompt = list(body_lines)
        fns_for_prompt = list(footnotes)
    else:
        for line in body_lines:
            seg_id = _segment_id_for_body(line)
            if seg_id in existing_segments and existing_segments[seg_id].get(
                "translation_history"
            ):
                skipped.append(seg_id)
            else:
                units_for_prompt.append(line)
        for fn in footnotes:
            seg_id = _segment_id_for_footnote(fn)
            if seg_id in existing_segments and existing_segments[seg_id].get(
                "translation_history"
            ):
                skipped.append(seg_id)
            else:
                fns_for_prompt.append(fn)

    if not units_for_prompt and not fns_for_prompt:
        return {
            "page_id": page_id,
            "status": "skipped_all_translated",
            "skipped": skipped,
            "translated": [],
            "warnings": [],
        }

    prompt = build_translation_prompt(
        page_id=page_id,
        body_lines=units_for_prompt,
        footnotes=fns_for_prompt,
        lexicon_profile=lexicon_profile,
        extra_context=extra_context,
    )

    expected_ids = (
        [line["line_id"] for line in units_for_prompt if line.get("line_id")]
        + [fn["footnote_id"] for fn in fns_for_prompt if fn.get("footnote_id")]
    )

    if dry_run or adapter is None:
        return {
            "page_id": page_id,
            "status": "dry_run",
            "skipped": skipped,
            "translated": [],
            "expected_unit_ids": expected_ids,
            "prompt_chars": len(prompt),
            "prompt": prompt if dry_run else "",
            "warnings": [],
        }

    try:
        result: TranslationResult = adapter.translate_units(
            prompt, expected_unit_ids=expected_ids
        )
    except TranslationError as exc:
        return {
            "page_id": page_id,
            "status": f"error:{exc.category}",
            "skipped": skipped,
            "translated": [],
            "warnings": [],
            "error_message": str(exc),
        }

    model = adapter.provider.model
    translated_ids: list[str] = []

    for line in units_for_prompt:
        seg_id = _segment_id_for_body(line)
        unit = result.translations.get(line.get("line_id", ""))
        if seg_id in existing_segments:
            existing_segments[seg_id] = _append_translation_history(
                existing_segments[seg_id],
                unit=unit,
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                source_unit_id=line.get("line_id", ""),
            )
        else:
            existing_segments[seg_id] = _build_segment_record(
                page_id=page_id,
                segment_id=seg_id,
                segment_type="body",
                latin_text=line.get("text_gold")
                or line.get("text_ocr_original")
                or "",
                unit=unit,
                source_unit_id=line.get("line_id", ""),
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
            )
        translated_ids.append(seg_id)

    for fn in fns_for_prompt:
        seg_id = _segment_id_for_footnote(fn)
        unit = result.translations.get(fn.get("footnote_id", ""))
        body_link_id = fn.get("body_line_id", "")
        body_seg_link = f"seg_{body_link_id}" if body_link_id else ""
        if seg_id in existing_segments:
            existing_segments[seg_id] = _append_translation_history(
                existing_segments[seg_id],
                unit=unit,
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                source_unit_id=fn.get("footnote_id", ""),
            )
        else:
            existing_segments[seg_id] = _build_segment_record(
                page_id=page_id,
                segment_id=seg_id,
                segment_type="footnote",
                latin_text=fn.get("text_gold")
                or fn.get("text_ocr_original")
                or "",
                unit=unit,
                source_unit_id=fn.get("footnote_id", ""),
                extra_links={
                    "body_segment_id": body_seg_link,
                    "marker_id": fn.get("marker_id", ""),
                },
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
            )
        translated_ids.append(seg_id)

    return {
        "page_id": page_id,
        "status": "ok",
        "skipped": skipped,
        "translated": translated_ids,
        "warnings": list(result.errors),
        "usage_tokens": result.usage_tokens,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _iter_page_files(part: str, start: int, end: int) -> Iterable[Path]:
    for page_num in range(start, end + 1):
        page_id = f"p{page_num:04d}"
        path = ANNOTATIONS_DIR / f"page_{page_id}.json"
        if path.exists():
            yield path


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate locked Phase 3b annotation pages via Claude CLI.",
    )
    parser.add_argument("--part", default="part1", help="Part name (default: part1).")
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--lexicon-profile",
        default="auto",
        choices=LEXICON_PROFILES,
    )
    parser.add_argument(
        "--claw-report",
        type=Path,
        help="Optional Go Claw combined report JSON file used as extra context.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts but do not invoke Claude.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-translate units that already have translation_history.",
    )
    return parser


def _load_claw_context(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # surface the path so users can fix the arg
        raise SystemExit(f"could not read claw report at {path}: {exc}")
    # Pass through verbatim; the prompt instructs the model to treat it as
    # context, not as authoritative ground truth.
    return text


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)

    config = default_config()
    provider = config.translation_provider()

    adapter: AnthropicTranslationAdapter | None = None
    if not args.dry_run:
        adapter = AnthropicTranslationAdapter(provider)

    extra_context = _load_claw_context(args.claw_report)
    existing_segments = load_existing_segments(args.part)

    timestamp = _now_iso()
    run_log: dict[str, Any] = {
        "started_at": timestamp,
        "part": args.part,
        "start_page": args.start_page,
        "end_page": args.end_page,
        "lexicon_profile": args.lexicon_profile,
        "dry_run": args.dry_run,
        "force": args.force,
        "model": provider.model,
        "pages": [],
    }

    for page_path in _iter_page_files(args.part, args.start_page, args.end_page):
        payload = load_phase3b_page(page_path)
        page_log = translate_page(
            payload,
            adapter=adapter,
            existing_segments=existing_segments,
            lexicon_profile=args.lexicon_profile,
            extra_context=extra_context,
            force=args.force,
            dry_run=args.dry_run,
            timestamp=timestamp,
        )
        run_log["pages"].append(page_log)
        # Persist progress per page so a long batch can resume cleanly.
        if not args.dry_run:
            write_segments(args.part, existing_segments)

    # Always write a run log.
    logs_dir = _logs_dir_for_part(args.part)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"translation_run_{timestamp.replace(':', '').replace('-', '')}.json"
    log_path.write_text(json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        # Surface prompt sizes to stdout so users can sanity-check before live run.
        for page in run_log["pages"]:
            print(
                f"[dry-run] {page['page_id']}: status={page['status']} "
                f"prompt_chars={page.get('prompt_chars', 0)} "
                f"expected_units={len(page.get('expected_unit_ids', []))}"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ANNOTATIONS_DIR",
    "ARTIFACTS_DIR",
    "WORKSPACE_ROOT",
    "extract_units",
    "load_existing_segments",
    "load_phase3b_page",
    "main",
    "translate_page",
    "write_segments",
]
