"""Whole-page Latin → English translation for comparison with line-by-line output.

Instead of the two-stage pipeline (line-by-line literal → polish pass), this
module sends the complete Latin of each page to Claude in a single call and
asks for idiomatic English returned as a JSON object keyed by segment_id.

The model sees full sentences before committing to any English word, which
eliminates the mid-clause fragment problem inherent in the line-by-line
approach. Output is written to a separate artifact
``03_segmented_text/<part>/segments_wholepage.jsonl`` and never touches
``segments_with_translations.jsonl``, so the two methods can be compared
side-by-side.

Prompt design
-------------
- Uses the ussher_v5 TRANSLATOR_BRIEF and HARD_RULES verbatim.
- Body lines are presented as a numbered Latin block; footnotes follow.
- Output contract: JSON object mapping each segment_id to a single
  English string. No line-by-line key IDs in the prompt — the model
  works from the whole-page Latin and maps back to segment IDs.
- Cross-page context (prev-tail / next-head bleed) is included as
  additional context, same as translate_segments.py.

Resume behaviour
----------------
Pages whose segment_ids are all present in the output artifact are
skipped on re-run. ``--force`` re-translates everything.

Usage
-----
    python 08_working_scratch/pipeline_scripts/translate_wholepage.py \\
        --part part1 --start-page 32 --end-page 45

    # Dry-run: build prompts, print sizes, no API call
    python ... --dry-run

    # Force re-translation of already-done pages
    python ... --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from provider_config import default_config                       # noqa: E402
from translation_adapters import (                               # noqa: E402
    AnthropicTranslationAdapter,
    TranslationError,
)
import translation_prompts_ussher_v5 as _v5                     # noqa: E402
from translate_segments import (                                 # noqa: E402
    load_phase3b_page,
    extract_units,
    _load_cross_page_context,
    _resolve_page_path,
    _iter_page_files,
)

# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = _HERE.parent.parent
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"


def _output_path(part: str) -> Path:
    return ARTIFACTS_DIR / part / "segments_wholepage.jsonl"


def _logs_dir(part: str) -> Path:
    return ARTIFACTS_DIR / part / ".logs"


# ---------------------------------------------------------------------------
# Loading the existing segments_wholepage artifact
# ---------------------------------------------------------------------------


def load_existing(part: str) -> dict[str, dict]:
    """Return {segment_id: record} from the wholepage artifact, or {}."""
    path = _output_path(part)
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}: malformed JSON on line {lineno}: {exc}"
                ) from exc
            sid = rec.get("segment_id")
            if sid:
                out[sid] = rec
    return out


def write_artifact(part: str, segments: dict[str, dict]) -> Path:
    """Atomically rewrite the wholepage artifact from the in-memory map."""
    path = _output_path(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    def _sort_key(rec: dict) -> tuple:
        page = str(rec.get("page_id", ""))
        type_rank = 1 if rec.get("segment_type") == "footnote" else 0
        seq = rec.get("seq")
        seq_k = int(seq) if isinstance(seq, int) else 10 ** 9
        return (page, type_rank, seq_k, str(rec.get("segment_id", "")))

    ordered = sorted(segments.values(), key=_sort_key)
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in ordered:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_OUTPUT_CONTRACT = """\
Return a single JSON object — no prose, no markdown, no code fences.
Keys are the segment_ids listed in the request. Values are the English
translation strings. Translate each Latin segment as part of the whole
page — let sentences flow naturally across line boundaries. Preserve
every '^X' footnote-anchor sentinel from the Latin in the corresponding
English segment. Omit no segment_id from the output object."""


def _segment_id_for_body(line: dict) -> str:
    lid = line.get("line_id", "unknown")
    return f"seg_{lid}"


def _segment_id_for_footnote(fn: dict) -> str:
    fid = fn.get("footnote_id", "unknown")
    return f"seg_{fid}"


def _latin_text(unit: dict) -> str:
    return (unit.get("text_gold") or unit.get("text_ocr_original") or "").strip()


def build_wholepage_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict],
    segment_ids: list[str],
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Build the whole-page translation prompt."""
    combined = " ".join(_latin_text(u) for u in list(body_lines) + list(footnotes))
    greek_present = _v5.contains_greek(combined)

    include_latin = lexicon_profile in ("auto", "latin_only", "latin_greek")
    include_greek = greek_present if lexicon_profile == "auto" else (
        lexicon_profile == "latin_greek"
    )

    lexicon_parts: list[str] = []
    if include_latin:
        lexicon_parts.append(_v5.LEXICON_LATIN_HINTS)
    if include_greek:
        lexicon_parts.append(_v5.LEXICON_GREEK_HINTS)

    # Body block: numbered lines with segment_id labels
    body_block_lines: list[str] = []
    for i, line in enumerate(body_lines, 1):
        sid = _segment_id_for_body(line)
        lat = _latin_text(line)
        body_block_lines.append(f"[{sid}] {lat}")
    body_block = "\n".join(body_block_lines)

    # Footnote block
    fn_block_lines: list[str] = []
    for fn in footnotes:
        sid = _segment_id_for_footnote(fn)
        lat = _latin_text(fn)
        marker = fn.get("marker_id", "")
        label = f"^{marker} " if marker else ""
        fn_block_lines.append(f"[{sid}] {label}{lat}")
    fn_block = "\n".join(fn_block_lines) if fn_block_lines else "(none)"

    ids_str = ", ".join(segment_ids)

    sections: list[str] = [
        _v5.TRANSLATOR_BRIEF,
        f"Page identifier: {page_id}",
        _v5.HARD_RULES,
    ]
    if lexicon_parts:
        sections.append("Lexicon hints:\n\n" + "\n\n".join(lexicon_parts))
    sections.append(
        "Body lines (translate as flowing whole-page English; "
        "sentence boundaries may cross line labels):\n\n" + body_block
    )
    sections.append("Linked footnotes:\n\n" + fn_block)
    if extra_context:
        sections.append("Additional page context:\n" + extra_context.rstrip())
    sections.append(f"Requested segment IDs: {ids_str}")
    sections.append(_OUTPUT_CONTRACT)

    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Per-page orchestration
# ---------------------------------------------------------------------------


def _page_num_from_id(page_id: str) -> int | None:
    m = re.match(r"p(\d+)$", page_id)
    return int(m.group(1)) if m else None


def translate_page(
    payload: dict,
    *,
    adapter: AnthropicTranslationAdapter | None,
    existing: dict[str, dict],
    lexicon_profile: str,
    extra_context: str | None,
    force: bool,
    dry_run: bool,
    timestamp: str,
    model: str,
    part: str,
) -> dict[str, Any]:
    """Translate one page and update *existing* in place. Returns a log dict."""
    page_id = payload["page_id"]
    body_lines, footnotes = extract_units(payload)

    # Build segment_ids in order
    body_seg_ids = [_segment_id_for_body(ln) for ln in body_lines]
    fn_seg_ids = [_segment_id_for_footnote(fn) for fn in footnotes]
    all_seg_ids = body_seg_ids + fn_seg_ids

    if not all_seg_ids:
        return {"page_id": page_id, "status": "no_units", "warnings": []}

    # Resume check: skip if all segments already translated
    if not force and all(sid in existing for sid in all_seg_ids):
        return {"page_id": page_id, "status": "skipped", "warnings": []}

    # Cross-page context (same as translate_segments.py)
    page_num = _page_num_from_id(page_id)
    ctx_block: str | None = None
    if page_num is not None:
        ctx_block = _load_cross_page_context(page_num=page_num, part=part)

    combined_ctx: str | None = None
    parts = [b for b in (ctx_block, extra_context) if b]
    if parts:
        combined_ctx = "\n\n".join(parts)

    prompt = build_wholepage_prompt(
        page_id=page_id,
        body_lines=body_lines,
        footnotes=footnotes,
        segment_ids=all_seg_ids,
        lexicon_profile=lexicon_profile,
        extra_context=combined_ctx,
    )

    if dry_run:
        return {
            "page_id": page_id,
            "status": "dry_run",
            "prompt_chars": len(prompt),
            "segment_count": len(all_seg_ids),
            "warnings": [],
        }

    warnings: list[str] = []

    # Call the model
    try:
        raw_json = adapter.complete_text(prompt)
    except TranslationError as exc:
        return {
            "page_id": page_id,
            "status": f"error:{exc.category}",
            "error": str(exc),
            "warnings": [],
        }

    # Parse the response
    try:
        translations: dict[str, str] = _parse_response(raw_json)
    except ValueError as exc:
        return {
            "page_id": page_id,
            "status": "parse_error",
            "error": str(exc),
            "raw_response": raw_json[:500],
            "warnings": [],
        }

    # Check completeness
    missing = [sid for sid in all_seg_ids if sid not in translations]
    if missing:
        warnings.append(f"Missing segment IDs in response: {', '.join(missing)}")

    # Build / update records
    seq_counter = 1
    for line in body_lines:
        sid = _segment_id_for_body(line)
        english = translations.get(sid, "")
        lat = _latin_text(line)
        existing[sid] = _build_record(
            segment_id=sid,
            page_id=page_id,
            segment_type="body",
            latin_text=lat,
            english=english,
            timestamp=timestamp,
            model=model,
            lexicon_profile=lexicon_profile,
            seq=line.get("seq") or seq_counter,
        )
        seq_counter += 1

    for fn in footnotes:
        sid = _segment_id_for_footnote(fn)
        english = translations.get(sid, "")
        lat = _latin_text(fn)
        body_link = fn.get("body_line_id", "")
        rec = _build_record(
            segment_id=sid,
            page_id=page_id,
            segment_type="footnote",
            latin_text=lat,
            english=english,
            timestamp=timestamp,
            model=model,
            lexicon_profile=lexicon_profile,
            seq=fn.get("seq") or seq_counter,
        )
        rec["body_segment_id"] = f"seg_{body_link}" if body_link else ""
        rec["marker_id"] = fn.get("marker_id", "")
        existing[sid] = rec
        seq_counter += 1

    return {
        "page_id": page_id,
        "status": "translated",
        "segment_count": len(all_seg_ids),
        "missing": missing,
        "warnings": warnings,
    }


def _parse_response(raw: str) -> dict[str, str]:
    """Extract a {segment_id: english_string} dict from the model response."""
    raw = raw.strip()
    # Strip optional markdown code fence
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    # Find the JSON object
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    obj = json.loads(raw[start: end + 1])
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object, got {type(obj).__name__}")
    return {k: str(v) for k, v in obj.items()}


def _build_record(
    *,
    segment_id: str,
    page_id: str,
    segment_type: str,
    latin_text: str,
    english: str,
    timestamp: str,
    model: str,
    lexicon_profile: str,
    seq: int,
) -> dict:
    return {
        "segment_id": segment_id,
        "page_id": page_id,
        "segment_type": segment_type,
        "latin_text": latin_text,
        "seq": seq,
        "translation_history": [{
            "version": 1,
            "stage": "wholepage_draft",
            "timestamp": timestamp,
            "english": english,
            "model": model,
            "lexicon_profile": lexicon_profile,
        }],
        "final_english": "",
        "translation_status": "wholepage_draft",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Whole-page Latin → English translation. "
            "Writes to segments_wholepage.jsonl; never touches "
            "segments_with_translations.jsonl."
        )
    )
    p.add_argument("--part", default="part1")
    p.add_argument("--start-page", type=int, required=True)
    p.add_argument("--end-page", type=int, required=True)
    p.add_argument(
        "--lexicon-profile", default="auto",
        choices=list(_v5.LEXICON_PROFILES),
    )
    p.add_argument(
        "--extra-context", type=Path, default=None,
        help="File whose contents are appended verbatim to every page prompt.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Build prompts but do not call Claude.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Re-translate pages already present in the output artifact.",
    )
    p.add_argument(
        "--timeout-seconds", type=float, default=None,
        help="Override provider timeout for this run.",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    config = default_config()
    provider = config.translation_provider()
    if args.timeout_seconds is not None:
        from dataclasses import replace
        provider = replace(provider, timeout_seconds=float(args.timeout_seconds))

    adapter: AnthropicTranslationAdapter | None = None
    if not args.dry_run:
        adapter = AnthropicTranslationAdapter(provider)

    extra_context: str | None = None
    if args.extra_context is not None:
        try:
            extra_context = args.extra_context.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"could not read --extra-context: {exc}", file=sys.stderr)
            return 2

    existing = load_existing(args.part)
    timestamp = _now_iso()
    model = provider.model

    run_log: dict[str, Any] = {
        "started_at": timestamp,
        "part": args.part,
        "start_page": args.start_page,
        "end_page": args.end_page,
        "model": model,
        "dry_run": args.dry_run,
        "force": args.force,
        "pages": [],
    }

    for page_path in _iter_page_files(args.part, args.start_page, args.end_page):
        m = re.search(r"p(\d+)", page_path.stem)
        if not m:
            continue
        page_num = int(m.group(1))

        payload = load_phase3b_page(page_path)
        page_log = translate_page(
            payload,
            adapter=adapter,
            existing=existing,
            lexicon_profile=args.lexicon_profile,
            extra_context=extra_context,
            force=args.force,
            dry_run=args.dry_run,
            timestamp=timestamp,
            model=model,
            part=args.part,
        )
        run_log["pages"].append(page_log)

        status = page_log["status"]
        if args.dry_run:
            print(
                f"{page_log['page_id']}: {status} "
                f"prompt_chars={page_log.get('prompt_chars', 0)} "
                f"segments={page_log.get('segment_count', 0)}"
            )
        else:
            print(f"{page_log['page_id']}: {status}")
            if page_log.get("missing"):
                print(f"  MISSING: {', '.join(page_log['missing'])}")
            for w in page_log.get("warnings", []):
                print(f"  WARN: {w}")

        # Flush after each page (resume-safe)
        if not args.dry_run and status == "translated":
            write_artifact(args.part, existing)

    # Write run log
    logs_dir = _logs_dir(args.part)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / (
        f"wholepage_run_{timestamp.replace(':', '').replace('-', '')}.json"
    )
    log_path.write_text(
        json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    translated = sum(1 for p in run_log["pages"] if p["status"] == "translated")
    skipped = sum(1 for p in run_log["pages"] if p["status"] == "skipped")
    print(f"\nDone. translated={translated} skipped={skipped}")
    print(f"Output: {_output_path(args.part)}")
    print(f"Log:    {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
