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
from dataclasses import asdict, replace
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
    _build_marker_lookup,
    _inject_markers,
    build_marker_placement_prompt,
    build_translation_prompt,
)
import translation_prompts as _prompt_v1  # noqa: E402
import translation_prompts_v0 as _prompt_v0  # noqa: E402
import translation_prompts_v2 as _prompt_v2  # noqa: E402
import translation_prompts_v3 as _prompt_v3  # noqa: E402
import translation_prompts_v4 as _prompt_v4  # noqa: E402
import translation_prompts_whitaker as _prompt_whitaker  # noqa: E402
import translation_prompts_whitaker_v2 as _prompt_whitaker_v2  # noqa: E402
import translation_prompts_whitaker_v3 as _prompt_whitaker_v3  # noqa: E402
import translation_prompts_whitaker_v4 as _prompt_whitaker_v4  # noqa: E402
import translation_prompts_ussher_v5 as _prompt_ussher_v5  # noqa: E402
import translation_prompts_ussher_v5_annals as _prompt_ussher_v5_annals  # noqa: E402
import translation_prompts_ussher_v5_exemplars as _prompt_ussher_v5_exemplars  # noqa: E402

# Mapping for --prompt-version dispatch. All modules expose
# ``build_translation_prompt`` with the same signature; the drift-guard
# in ``tests/test_prompt_versions.py`` keeps that contract honest.
_PROMPT_VERSIONS = {
    "v0": _prompt_v0,
    "v1": _prompt_v1,
    "v2": _prompt_v2,
    "v3": _prompt_v3,
    "v4": _prompt_v4,
    "whitaker": _prompt_whitaker,
    "whitaker_v2": _prompt_whitaker_v2,
    "whitaker_v3": _prompt_whitaker_v3,
    "whitaker_v4": _prompt_whitaker_v4,
    "ussher_v5": _prompt_ussher_v5,
    "ussher_v5_annals": _prompt_ussher_v5_annals,
    "ussher_v5_exemplars": _prompt_ussher_v5_exemplars,
}

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
    markers: Sequence[dict] | None = None,
    seq: int | None = None,
) -> dict:
    """Build the persisted segment record matching SCHEMA.md semantics.

    ``seq`` carries the source line/footnote's 1-based ordering value
    so downstream consumers (polish_translations, render_interlinear)
    can sort by it instead of regex-parsing ``segment_id``.
    """

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
        "markers": list(markers) if markers else [],
        "translation_history": [history_entry],
        "final_english": "",
        "translation_status": "machine_draft" if unit else "pending",
    }
    if seq is not None:
        record["seq"] = int(seq)
    if extra_links:
        record.update(extra_links)
    return record


def _refresh_metadata_fields(
    existing: dict,
    *,
    latin_text: str,
    markers: Sequence[dict] | None = None,
    extra_links: dict[str, Any] | None = None,
    seq: int | None = None,
) -> dict:
    """Overwrite annotation-derived fields on an existing record.

    These fields (``latin_text``, ``markers``, footnote backlinks,
    ``seq``) are derived from the current annotation file and are NOT
    history-stable; they should always reflect the latest annotation
    state. The ``translation_history`` list is left untouched.
    """
    updated = dict(existing)
    updated["latin_text"] = latin_text
    updated["markers"] = list(markers) if markers else []
    if seq is not None:
        updated["seq"] = int(seq)
    if extra_links:
        updated.update(extra_links)
    return updated


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


def _segment_write_key(record: dict) -> tuple:
    """Sort key for the persisted JSONL: by page_id, then body before
    footnotes, then ``seq`` (ordering authority), with ``segment_id``
    as a deterministic tie-breaker for legacy records lacking ``seq``.
    """
    page = str(record.get("page_id", ""))
    type_rank = 1 if record.get("segment_type") == "footnote" else 0
    seq = record.get("seq")
    seq_key = int(seq) if isinstance(seq, int) else 10**9
    seg_id = str(record.get("segment_id", ""))
    return (page, type_rank, seq_key, seg_id)


def write_segments(part: str, segments: dict[str, dict]) -> Path:
    """Rewrite the part's JSONL artifact from the in-memory map."""
    path = _artifact_path_for_part(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    ordered = sorted(segments.values(), key=_segment_write_key)
    with tmp.open("w", encoding="utf-8") as handle:
        for record in ordered:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Page-level orchestration
# ---------------------------------------------------------------------------


def _segment_id_for_body(line: dict) -> str:
    return f"seg_{line.get('line_id', 'unknown')}"


def _segment_id_for_footnote(fn: dict) -> str:
    return f"seg_{fn.get('footnote_id', 'unknown')}"


def _build_body_marker_metadata(
    line: dict,
    footnotes: Sequence[dict],
) -> tuple[str, list[dict]]:
    """Return ``(latin_text_with_carets, markers_metadata)`` for a body line.

    The Latin text gains ``^<marker_id>`` sentinels at each marker offset
    so the persisted artifact carries the same anchor information the
    translation prompt sent to Claude. The metadata list provides
    machine-readable cross-references to footnote segments.

    Markers without a resolvable footnote in *footnotes* are dropped
    from both outputs to keep the artifact internally consistent.
    """
    raw_text = line.get("text_gold") or line.get("text_ocr_original") or ""
    raw_markers = line.get("markers") or []
    if not raw_markers:
        return raw_text, []

    fn_lookup = _build_marker_lookup(footnotes)
    fn_by_id = {fn.get("footnote_id"): fn for fn in footnotes if fn.get("footnote_id")}

    metadata: list[dict] = []
    valid_for_injection: list[dict] = []
    for m in raw_markers:
        fn_id = m.get("footnote_id")
        offset = m.get("char_offset")
        if not fn_id or fn_id not in fn_by_id:
            continue
        marker_symbol = fn_lookup.get(str(fn_id))
        if not marker_symbol:
            continue
        try:
            offset_int = int(offset) if offset is not None else None
        except (TypeError, ValueError):
            offset_int = None
        metadata.append({
            "marker_id": marker_symbol,
            "char_offset": offset_int,
            "footnote_segment_id": f"seg_{fn_id}",
        })
        valid_for_injection.append(m)

    injected_text = _inject_markers(raw_text, valid_for_injection, fn_lookup)
    return injected_text, metadata


# ---------------------------------------------------------------------------
# Marker placement (second-pass LLM call with end-of-line fallback)
# ---------------------------------------------------------------------------


def _normalize_ws(text: str) -> str:
    return " ".join((text or "").split())


def _validate_placement(
    response: str,
    *,
    input_english: str,
    marker_id: str,
) -> str | None:
    """Return *response* unchanged if it differs from *input_english*
    only by exactly one inserted ``^<marker_id>`` token (modulo
    whitespace normalization). Otherwise return ``None`` so the
    caller can fall back.
    """
    token = f"^{marker_id}"
    if response is None:
        return None
    response = response.strip()
    if not response or token not in response:
        return None
    idx = response.find(token)
    stripped = response[:idx] + response[idx + len(token):]
    if _normalize_ws(stripped) != _normalize_ws(input_english):
        return None
    return response


def _place_markers_in_english(
    *,
    english: str,
    latin_with_caret: str,
    markers: Sequence[dict],
    adapter: AnthropicTranslationAdapter | None,
) -> tuple[str, list[str]]:
    """Insert one ``^<marker_id>`` token per marker into *english*.

    Strategy: for each marker, ask Claude to place that single token
    in the English at the position equivalent to the Latin anchor.
    On any failure (no adapter, CLI error, malformed response), fall
    back to appending ``^<marker_id>`` at the end of the English so
    the footnote anchor is never silently dropped.

    Returns ``(english_with_carets, warnings)``.
    """
    warnings: list[str] = []
    if not markers:
        return english, warnings

    current = english
    for m in markers:
        marker_id = (m or {}).get("marker_id")
        if not marker_id:
            continue
        placed: str | None = None
        if adapter is not None:
            prompt = build_marker_placement_prompt(
                english=current,
                marker_id=marker_id,
                latin_with_caret=latin_with_caret,
            )
            try:
                raw = adapter.complete_text(prompt)
            except TranslationError as exc:
                warnings.append(
                    f"marker '{marker_id}' placement call failed: "
                    f"{exc.__class__.__name__}; using end-of-line fallback"
                )
                raw = ""
            placed = _validate_placement(
                raw, input_english=current, marker_id=marker_id
            )
            if placed is None and raw:
                warnings.append(
                    f"marker '{marker_id}' placement validation failed; "
                    f"using end-of-line fallback"
                )
        if placed is None:
            placed = current.rstrip() + f"^{marker_id}"
        current = placed
    return current, warnings


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
    metadata_only: bool = False,
) -> dict[str, Any]:
    """Translate one page payload and update *existing_segments* in place.

    Returns a per-page log dict.

    When ``metadata_only`` is True, the runner refreshes annotation-derived
    fields (``latin_text`` with caret sentinels, ``markers``, footnote
    backlinks) on existing records without invoking Claude. This is a
    cheap way to backfill schema changes after the prompt-side marker
    work landed.
    """

    page_id = payload["page_id"]
    body_lines, footnotes = extract_units(payload)

    # ---------- metadata-only path: no Claude call ---------------------
    if metadata_only:
        refreshed: list[str] = []
        for line in body_lines:
            seg_id = _segment_id_for_body(line)
            if seg_id not in existing_segments:
                continue
            latin_with_carets, markers_meta = _build_body_marker_metadata(
                line, footnotes
            )
            existing_segments[seg_id] = _refresh_metadata_fields(
                existing_segments[seg_id],
                latin_text=latin_with_carets,
                markers=markers_meta,
            )
            refreshed.append(seg_id)
        for fn in footnotes:
            seg_id = _segment_id_for_footnote(fn)
            if seg_id not in existing_segments:
                continue
            body_link_id = fn.get("body_line_id", "")
            existing_segments[seg_id] = _refresh_metadata_fields(
                existing_segments[seg_id],
                latin_text=fn.get("text_gold")
                or fn.get("text_ocr_original")
                or "",
                markers=[],
                extra_links={
                    "body_segment_id": f"seg_{body_link_id}" if body_link_id else "",
                    "marker_id": fn.get("marker_id", ""),
                },
            )
            refreshed.append(seg_id)
        return {
            "page_id": page_id,
            "status": "metadata_refreshed",
            "skipped": [],
            "translated": [],
            "refreshed": refreshed,
            "warnings": [],
        }

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
    placement_warnings: list[str] = []

    for line in units_for_prompt:
        seg_id = _segment_id_for_body(line)
        unit = result.translations.get(line.get("line_id", ""))
        latin_with_carets, markers_meta = _build_body_marker_metadata(
            line, footnotes
        )
        # Second-pass marker placement: insert each ^<marker_id> token
        # into the English at the position equivalent to the Latin
        # anchor. End-of-line fallback if any call fails.
        if unit is not None and markers_meta:
            placed_english, placement_msgs = _place_markers_in_english(
                english=unit.english,
                latin_with_caret=latin_with_carets,
                markers=markers_meta,
                adapter=adapter,
            )
            if placed_english != unit.english:
                unit = TranslationUnit(
                    unit_id=unit.unit_id,
                    english=placed_english,
                    notes=unit.notes,
                    uncertain=unit.uncertain,
                )
            for msg in placement_msgs:
                placement_warnings.append(f"{seg_id}: {msg}")
        if seg_id in existing_segments:
            existing_segments[seg_id] = _append_translation_history(
                existing_segments[seg_id],
                unit=unit,
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                source_unit_id=line.get("line_id", ""),
            )
            existing_segments[seg_id] = _refresh_metadata_fields(
                existing_segments[seg_id],
                latin_text=latin_with_carets,
                markers=markers_meta,
                seq=line.get("seq"),
            )
        else:
            existing_segments[seg_id] = _build_segment_record(
                page_id=page_id,
                segment_id=seg_id,
                segment_type="body",
                latin_text=latin_with_carets,
                unit=unit,
                source_unit_id=line.get("line_id", ""),
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                markers=markers_meta,
                seq=line.get("seq"),
            )
        translated_ids.append(seg_id)

    for fn in fns_for_prompt:
        seg_id = _segment_id_for_footnote(fn)
        unit = result.translations.get(fn.get("footnote_id", ""))
        body_link_id = fn.get("body_line_id", "")
        body_seg_link = f"seg_{body_link_id}" if body_link_id else ""
        fn_extra_links = {
            "body_segment_id": body_seg_link,
            "marker_id": fn.get("marker_id", ""),
        }
        if seg_id in existing_segments:
            existing_segments[seg_id] = _append_translation_history(
                existing_segments[seg_id],
                unit=unit,
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                source_unit_id=fn.get("footnote_id", ""),
            )
            existing_segments[seg_id] = _refresh_metadata_fields(
                existing_segments[seg_id],
                latin_text=fn.get("text_gold")
                or fn.get("text_ocr_original")
                or "",
                markers=[],
                extra_links=fn_extra_links,
                seq=fn.get("seq"),
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
                extra_links=fn_extra_links,
                timestamp=timestamp,
                model=model,
                lexicon_profile=lexicon_profile,
                seq=fn.get("seq"),
            )
        translated_ids.append(seg_id)

    return {
        "page_id": page_id,
        "status": "ok",
        "skipped": skipped,
        "translated": translated_ids,
        "warnings": list(result.errors) + placement_warnings,
        "usage_tokens": result.usage_tokens,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _resolve_page_path(part: str | None, page_id: str) -> Path | None:
    """Locate a page JSON for *page_id*, honoring the corpus *part*.

    Lookup order:
      1. ``ANNOTATIONS_DIR / part / page_<page_id>.json`` (new layout —
         where corpora live in named subfolders like ``whitaker_latin``).
      2. ``ANNOTATIONS_DIR / page_<page_id>.json`` (legacy flat layout,
         Ussher era).

    Returns the first that exists, or None.
    """
    filename = f"page_{page_id}.json"
    if part:
        sub = ANNOTATIONS_DIR / part / filename
        if sub.exists():
            return sub
    root = ANNOTATIONS_DIR / filename
    return root if root.exists() else None


def _iter_page_files(part: str, start: int, end: int) -> Iterable[Path]:
    for page_num in range(start, end + 1):
        page_id = f"p{page_num:04d}"
        path = _resolve_page_path(part, page_id)
        if path is not None:
            yield path


def _page_file_for(page_num: int, part: str | None = None) -> Path | None:
    """Return the on-disk page-payload path for *page_num*, or None if
    the page is out of range or the file is not present.

    Used by ``_load_cross_page_context`` to look up the immediate
    neighbors of the current page. Path naming mirrors
    ``_iter_page_files`` so both share one source of truth.
    """
    if page_num < 1:
        return None
    return _resolve_page_path(part, f"p{page_num:04d}")


def _payload_body_concatenated(payload: dict) -> str:
    """Concatenate body-line text from *payload* in printed order,
    preferring ``text_gold`` and falling back to ``text_ocr_original``.

    Returns plain Latin text WITHOUT any '^X' caret sentinels. Cross-
    page context is purely for stitching broken tokens and clarifying
    antecedents; it does not participate in marker placement, so
    leaving carets out keeps the prompt clean and prevents the model
    from emitting a marker that belongs to a neighbor's translation
    pass.
    """
    body_lines, _ = extract_units(payload)
    return " ".join(
        (line.get("text_gold") or line.get("text_ocr_original") or "").strip()
        for line in body_lines
        if (line.get("text_gold") or line.get("text_ocr_original"))
    ).strip()


def _load_cross_page_context(
    *,
    page_num: int,
    part: str | None = None,
    tail_chars: int = 240,
    head_chars: int = 240,
) -> str | None:
    """Build a 'Previous page tail / Next page head' context block for
    Hard Rule 9 ("CROSS-PAGE CONTEXT") in the v3 prompt.

    Each neighbor is truncated to roughly one printed line of context
    (~240 chars) — enough to stitch a hyphen-broken word or recover
    a stranded subject without inflating the prompt budget.

    Returns None when neither neighbor exists (e.g. the very first or
    last page of the corpus). Older prompt versions ignore this
    extra-context block silently, so it is safe to populate
    unconditionally.
    """
    blocks: list[str] = []

    prev_path = _page_file_for(page_num - 1, part=part)
    if prev_path is not None:
        prev_text = _payload_body_concatenated(load_phase3b_page(prev_path))
        if prev_text:
            blocks.append(
                "Previous page tail: …" + prev_text[-tail_chars:].lstrip()
            )

    next_path = _page_file_for(page_num + 1, part=part)
    if next_path is not None:
        next_text = _payload_body_concatenated(load_phase3b_page(next_path))
        if next_text:
            blocks.append(
                "Next page head: " + next_text[:head_chars].rstrip() + "…"
            )

    return "\n\n".join(blocks) if blocks else None


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
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help=(
            "Refresh annotation-derived fields (latin_text with caret "
            "sentinels, markers[], footnote backlinks) on existing "
            "segment records without calling Claude. Useful for "
            "backfilling schema changes."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help=(
            "Override the translation provider timeout (in seconds) "
            "for this run. Defaults to the value in providers.json or "
            "the built-in default."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Override the Claude Code CLI --model id for this run. "
            "Defaults to providers.json (anthropic.model). "
            "Recommended pins: 'claude-opus-4-7' for translation, "
            "'claude-sonnet-4-6' for the A/B judge. Each model already "
            "includes its 1M context window; no extra flag is needed."
        ),
    )
    parser.add_argument(
        "--prompt-version",
        choices=sorted(_PROMPT_VERSIONS),
        default="v1",
        help=(
            "Which translation prompt module to use. 'v1' (default) is "
            "the live ``translation_prompts.py``; 'v0' is the frozen "
            "pre-refinement snapshot used only for A/B comparison; "
            "'v2' is the structural rewrite that promotes hard rules "
            "above the lexicon block and adds the Greek-paraphrase "
            "directive; 'v3' refines v2 with three-slot Greek output "
            "(deprecated, failed A/B p0041); 'v4' is v2 + clarified "
            "Latin-preservation for the Ussher exercise; 'whitaker' "
            "is the Whitaker-corpus baseline (Greek + English in "
            "square brackets, no Latin-paraphrase assumption)."
        ),
    )
    parser.add_argument(
        "--run-tag",
        default=None,
        help=(
            "When set, redirect artifacts to "
            "``04_translation_work/ab/<page-key>/<prompt-version>/<run-tag>/`` "
            "instead of the production ``03_segmented_text/<part>/`` "
            "path, and write a ``meta.json`` describing the run. "
            "Used by the A/B test harness."
        ),
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

    # ---- Prompt-version dispatch (A/B harness) ------------------------
    # Rebind the module-level ``build_translation_prompt`` symbol so
    # ``translate_page`` uses the selected version without further
    # plumbing. This is intentionally a small, local monkey-patch; the
    # drift-guard test guarantees the two versions share a signature.
    global build_translation_prompt
    build_translation_prompt = _PROMPT_VERSIONS[args.prompt_version].build_translation_prompt

    # Preserve the user-supplied part (the corpus subfolder under
    # ``annotations/``, e.g. ``whitaker_latin``) BEFORE the A/B override
    # below clobbers ``args.part``. Annotation INPUTS are loaded under
    # ``input_part``; artifact OUTPUTS go under ``args.part`` (which the
    # A/B block rewrites to ``<prompt_version>/<run_tag>``).
    input_part = args.part

    # ---- A/B output redirection --------------------------------------
    # When --run-tag is set, redirect ARTIFACTS_DIR to a per-run path
    # under 04_translation_work/ab/ and remember it so we can also drop
    # a meta.json next to the artifact. We achieve this by repointing
    # ARTIFACTS_DIR (the module global used by every path helper) at
    # the A/B parent and rewriting args.part to the version/tag suffix
    # so existing helpers naturally produce the desired layout:
    #   04_translation_work/ab/<page-key>/<version>/<run-tag>/
    #     segments_with_translations.jsonl
    #     .logs/
    #     meta.json
    ab_run_dir: Path | None = None
    if args.run_tag:
        if args.start_page == args.end_page:
            page_key = f"p{args.start_page:04d}"
        else:
            page_key = f"p{args.start_page:04d}_p{args.end_page:04d}"
        ab_parent = WORKSPACE_ROOT / "04_translation_work" / "ab" / page_key
        ab_synthetic_part = f"{args.prompt_version}/{args.run_tag}"
        ab_run_dir = ab_parent / ab_synthetic_part
        ab_run_dir.mkdir(parents=True, exist_ok=True)
        global ARTIFACTS_DIR
        ARTIFACTS_DIR = ab_parent
        args.part = ab_synthetic_part

    config = default_config()
    provider = config.translation_provider()
    if args.timeout_seconds is not None:
        provider = replace(provider, timeout_seconds=float(args.timeout_seconds))
    if args.model is not None:
        provider = replace(provider, model=args.model)

    adapter: AnthropicTranslationAdapter | None = None
    if not args.dry_run and not args.metadata_only:
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
        "metadata_only": args.metadata_only,
        "model": provider.model,
        "prompt_version": args.prompt_version,
        "run_tag": args.run_tag,
        "pages": [],
    }

    for page_path in _iter_page_files(input_part, args.start_page, args.end_page):
        payload = load_phase3b_page(page_path)

        # Cross-page context (v3 Hard Rule 9). Always populated when
        # neighbors exist; older prompt versions ignore it, so this is
        # version-agnostic.
        try:
            page_num = int(str(payload["page_id"]).lstrip("p"))
        except (KeyError, ValueError):
            page_num = -1
        cross_page_ctx = (
            _load_cross_page_context(page_num=page_num, part=input_part)
            if page_num >= 1
            else None
        )
        per_page_extra = "\n\n".join(
            block for block in (cross_page_ctx, extra_context) if block
        ) or None

        page_log = translate_page(
            payload,
            adapter=adapter,
            existing_segments=existing_segments,
            lexicon_profile=args.lexicon_profile,
            extra_context=per_page_extra,
            force=args.force,
            dry_run=args.dry_run,
            timestamp=timestamp,
            metadata_only=args.metadata_only,
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

    # A/B harness: drop a sibling meta.json describing the run so the
    # downstream scoring tools can match artifacts to prompt versions
    # without parsing the .logs/ filenames.
    if ab_run_dir is not None:
        meta = {
            "prompt_version": args.prompt_version,
            "run_tag": args.run_tag,
            "started_at": timestamp,
            "model": provider.model,
            "lexicon_profile": args.lexicon_profile,
            "start_page": args.start_page,
            "end_page": args.end_page,
            "page_ids": [p.get("page_id") for p in run_log["pages"]],
            "force": args.force,
            "dry_run": args.dry_run,
        }
        (ab_run_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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
