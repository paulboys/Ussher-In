"""Sentence-level Latin → English translation.

Uses ``sentence_segment.py`` to group locked body lines into complete
sentence units, then translates each page in one Claude call — one entry
per sentence in the returned JSON. Footnotes are translated as individual
units appended after the body sentences.

Compared with ``translate_segments.py`` (line-by-line):
- The model sees complete sentences before committing to any English word.
- Fewer units per page → less fragmentation pressure.
- Still whole-page context for cross-sentence coherence.

Compared with ``translate_wholepage.py`` (whole-page prose):
- Output remains keyed to discrete units (sentence_ids) → compatible with
  per-unit validation and fidelity scoring.
- Sentence units map back to source line_ids for interlinear rendering.

Output artifact: ``03_segmented_text/<part>/segments_sentences.jsonl``
Never touches ``segments_with_translations.jsonl``.

Usage
-----
    python 08_working_scratch/pipeline_scripts/translate_sentences.py \\
        --part part1 --start-page 32 --end-page 45

    python ... --dry-run     # prompt sizes only, no API call
    python ... --force       # re-translate already-done pages
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from provider_config import default_config                      # noqa: E402
from translation_adapters import (                              # noqa: E402
    AnthropicTranslationAdapter,
    TranslationError,
)
import translation_prompts_ussher_v5 as _v5                    # noqa: E402
from translation_prompts import _build_marker_lookup           # noqa: E402
from sentence_segment import (                                  # noqa: E402
    SentenceUnit,
    group_lines_into_sentences,
    group_pages_into_sentences,
    load_page_body,
    _iter_page_ids,
)
from translate_segments import (                                # noqa: E402
    load_phase3b_page,
    extract_units,
    _load_cross_page_context,
    _resolve_page_path,
)

# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = _HERE.parent.parent
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"

# Output artifact name. Overridable from the CLI; the cross-page run defaults
# to a distinct file so the two segmentations never mix in one artifact.
_OUTPUT_NAME = "segments_sentences.jsonl"


def _output_path(part: str) -> Path:
    return ARTIFACTS_DIR / part / _OUTPUT_NAME


def _logs_dir(part: str) -> Path:
    return ARTIFACTS_DIR / part / ".logs"


# ---------------------------------------------------------------------------
# Artifact I/O
# ---------------------------------------------------------------------------


def find_seam_clashes(
    units: Sequence,
    existing: dict[str, dict],
) -> list[tuple[str, list[str]]]:
    """Resume-window guard for cross-page grouping.

    Cross-page grouping only sees the pages in THIS run's range. If the
    range starts mid-seam — an earlier run's cross-page sentence (homed
    before the window) already absorbed the first page's leading lines —
    those lines look like a fresh sentence to the narrow window and would
    be segmented, translated, and merged AGAIN. (A ch2 usage-recovery
    probe over p0059 alone duplicated eight lines already owned by
    seg_p0058_s0003 this way.)

    Returns ``[(new_unit_id, [owning_segment_ids]), ...]`` for every new
    unit whose source lines are claimed by a DIFFERENT existing segment.
    An identical id (the normal skip-and-resume case) is not a clash.
    Callers should refuse to proceed on any clash: re-running with a
    wide-enough range costs nothing, since completed pages are skipped.
    """
    claimed: dict[str, str] = {}
    for sid, rec in existing.items():
        if rec.get("segment_type") == "footnote":
            continue
        for lid in rec.get("source_line_ids") or []:
            claimed[lid] = sid
    out: list[tuple[str, list[str]]] = []
    for u in units:
        owners = sorted({
            claimed[lid] for lid in u.source_line_ids
            if lid in claimed and claimed[lid] != u.sentence_id
        })
        if owners:
            out.append((u.sentence_id, owners))
    return out


def load_existing(part: str) -> dict[str, dict]:
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
                raise ValueError(f"{path}: line {lineno}: {exc}") from exc
            sid = rec.get("segment_id")
            if sid:
                out[sid] = rec
    return out


def write_artifact(part: str, segments: dict[str, dict]) -> Path:
    path = _output_path(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    def _key(rec: dict) -> tuple:
        page = str(rec.get("page_id", ""))
        stype = 1 if rec.get("segment_type") == "footnote" else 0
        seq = rec.get("seq")
        seq_k = int(seq) if isinstance(seq, int) else 10 ** 9
        return (page, stype, seq_k, str(rec.get("segment_id", "")))

    with tmp.open("w", encoding="utf-8") as fh:
        for rec in sorted(segments.values(), key=_key):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_OUTPUT_CONTRACT = """\
Return a single JSON object — no prose, no markdown, no code fences.
Keys are the segment_ids listed in the request.
For sentence units (seg_pNNNN_sNNNN): translate the full Latin sentence
as flowing idiomatic English. The sentence may span several source lines;
render it as a single natural English sentence. Preserve every '^X'
footnote-anchor sentinel from the Latin in the English translation at
the semantically equivalent position.
For footnote units (seg_pNNNN_fn_NNN): translate as a self-contained
scholarly footnote.
Omit no segment_id."""


def _fn_segment_id(fn: dict) -> str:
    return f"seg_{fn.get('footnote_id', 'unknown')}"


def _fn_latin(fn: dict) -> str:
    return (fn.get("text_gold") or fn.get("text_ocr_original") or "").strip()


def build_sentence_prompt(
    *,
    page_id: str,
    sentences: list[SentenceUnit],
    footnotes: Sequence[dict],
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    combined = " ".join(
        u.latin_text for u in sentences
    ) + " " + " ".join(_fn_latin(fn) for fn in footnotes)
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

    # Sentence block
    body_block_lines: list[str] = []
    for s in sentences:
        n = len(s.source_line_ids)
        body_block_lines.append(
            f"[{s.sentence_id}]  ({n} source line{'s' if n != 1 else ''})\n"
            f"  {s.latin_text}"
        )
    body_block = "\n\n".join(body_block_lines)

    # Footnote block
    fn_lines: list[str] = []
    for fn in footnotes:
        sid = _fn_segment_id(fn)
        lat = _fn_latin(fn)
        marker = fn.get("marker_id", "")
        label = f"^{marker} " if marker else ""
        fn_lines.append(f"[{sid}] {label}{lat}")
    fn_block = "\n".join(fn_lines) if fn_lines else "(none)"

    all_ids = [s.sentence_id for s in sentences] + [_fn_segment_id(fn) for fn in footnotes]
    ids_str = ", ".join(all_ids)

    sections: list[str] = [
        _v5.TRANSLATOR_BRIEF,
        f"Page identifier: {page_id}",
        _v5.HARD_RULES,
    ]
    if lexicon_parts:
        sections.append("Lexicon hints:\n\n" + "\n\n".join(lexicon_parts))
    sections.append(
        "Sentence units to translate (each is one complete Latin sentence "
        "spanning one or more source lines):\n\n" + body_block
    )
    sections.append("Linked footnotes:\n\n" + fn_block)
    if extra_context:
        sections.append("Additional page context:\n" + extra_context.rstrip())
    sections.append(f"Requested segment IDs: {ids_str}")
    sections.append(_OUTPUT_CONTRACT)

    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> dict[str, str]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    obj = json.loads(raw[start: end + 1])
    if not isinstance(obj, dict):
        raise ValueError(f"Expected dict, got {type(obj).__name__}")
    return {k: str(v) for k, v in obj.items()}


def _load_agent_written_file(
    part: str, page_id: str, *, run_started_epoch: float | None
) -> dict[str, str] | None:
    """Recover translations the ``claude -p`` agent wrote to a file.

    The agent has file-writing tools and occasionally writes the result to
    ``03_segmented_text/<part>/<page_id>_translation.json`` and returns a
    prose summary instead of the inline JSON the prompt asked for — which
    defeats :func:`_parse_response`. When inline parsing fails, look for
    that file and use it.

    When *run_started_epoch* is given, the file is only accepted if it was
    modified at/after the run start (1s grace), so a stale file left by a
    previous run is never silently substituted for a genuinely failed page.
    """
    path = ARTIFACTS_DIR / part / f"{page_id}_translation.json"
    if not path.exists():
        return None
    if run_started_epoch is not None:
        try:
            if path.stat().st_mtime < run_started_epoch - 1:
                return None
        except OSError:
            return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    return {k: str(v) for k, v in obj.items()}


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------


def _sentence_record(
    unit: SentenceUnit,
    english: str,
    *,
    timestamp: str,
    model: str,
    lexicon_profile: str,
) -> dict:
    return {
        "segment_id": unit.sentence_id,
        "page_id": unit.page_id,
        "segment_type": "body",
        "latin_text": unit.latin_text,
        "source_line_ids": unit.source_line_ids,
        "markers": unit.markers,
        "spans_pages": unit.spans_pages,
        "seq": unit.seq,
        "translation_history": [{
            "version": 1,
            "stage": "sentence_draft",
            "timestamp": timestamp,
            "english": english,
            "model": model,
            "lexicon_profile": lexicon_profile,
        }],
        "final_english": "",
        "translation_status": "sentence_draft",
    }


def _fn_record(
    fn: dict,
    english: str,
    page_id: str,
    seq: int,
    *,
    timestamp: str,
    model: str,
    lexicon_profile: str,
) -> dict:
    sid = _fn_segment_id(fn)
    body_link = fn.get("body_line_id", "")
    return {
        "segment_id": sid,
        "page_id": page_id,
        "segment_type": "footnote",
        "latin_text": _fn_latin(fn),
        "seq": seq,
        "body_segment_id": f"seg_{body_link}" if body_link else "",
        "marker_id": fn.get("marker_id", ""),
        "translation_history": [{
            "version": 1,
            "stage": "sentence_draft",
            "timestamp": timestamp,
            "english": english,
            "model": model,
            "lexicon_profile": lexicon_profile,
        }],
        "final_english": "",
        "translation_status": "sentence_draft",
    }


# ---------------------------------------------------------------------------
# Per-page orchestration
# ---------------------------------------------------------------------------


def _page_num_from_id(page_id: str) -> int | None:
    m = re.match(r"p(\d+)$", page_id)
    return int(m.group(1)) if m else None


def translate_page(
    page_id: str,
    *,
    part: str,
    adapter: AnthropicTranslationAdapter | None,
    existing: dict[str, dict],
    lexicon_profile: str,
    extra_context: str | None,
    force: bool,
    dry_run: bool,
    timestamp: str,
    model: str,
    sentences: list[SentenceUnit] | None = None,
) -> dict[str, Any]:
    """Translate one page. Updates *existing* in place. Returns log dict.

    When *sentences* is provided (cross-page mode) it is used verbatim — these
    are the units homed on *page_id*, possibly carrying lines absorbed from the
    next page. When None (per-page mode), the page's own lines are grouped.
    """

    # Load footnotes first — the marker lookup feeds caret injection into the
    # per-page segmentation below (cross-page units are already injected upstream).
    page_path = _resolve_page_path(part, page_id)
    if page_path is None or not page_path.exists():
        return {"page_id": page_id, "status": "annotation_not_found", "warnings": []}

    payload = load_phase3b_page(page_path)
    _, footnotes = extract_units(payload)

    # Sentence units: pre-computed (cross-page) or grouped per page.
    if sentences is None:
        body_lines = load_page_body(part or None, page_id)
        sentences = group_lines_into_sentences(
            body_lines, page_id, marker_lookup=_build_marker_lookup(footnotes))

    all_ids = (
        [s.sentence_id for s in sentences]
        + [_fn_segment_id(fn) for fn in footnotes]
    )

    if not all_ids:
        return {"page_id": page_id, "status": "no_units", "warnings": []}

    # Resume check
    if not force and all(sid in existing for sid in all_ids):
        return {"page_id": page_id, "status": "skipped", "warnings": []}

    # Cross-page context
    page_num = _page_num_from_id(page_id)
    ctx_block = (
        _load_cross_page_context(page_num=page_num, part=part)
        if page_num is not None else None
    )
    combined_ctx = "\n\n".join(b for b in (ctx_block, extra_context) if b) or None

    prompt = build_sentence_prompt(
        page_id=page_id,
        sentences=sentences,
        footnotes=footnotes,
        lexicon_profile=lexicon_profile,
        extra_context=combined_ctx,
    )

    if dry_run:
        return {
            "page_id": page_id,
            "status": "dry_run",
            "prompt_chars": len(prompt),
            "sentence_count": len(sentences),
            "footnote_count": len(footnotes),
            "warnings": [],
        }

    # Run start epoch, for the agent-written-file staleness guard.
    try:
        run_started_epoch: float | None = calendar.timegm(
            time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        )
    except (ValueError, TypeError):
        run_started_epoch = None

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

    warnings: list[str] = []
    try:
        translations = _parse_response(raw_json)
    except ValueError as exc:
        # The agent sometimes writes the JSON to a <page_id>_translation.json
        # file and returns a prose summary; recover from that file.
        recovered = _load_agent_written_file(
            part, page_id, run_started_epoch=run_started_epoch
        )
        if recovered is None:
            return {
                "page_id": page_id,
                "status": "parse_error",
                "error": str(exc),
                "raw_response": raw_json[:500],
                "warnings": [],
            }
        translations = recovered
        warnings.append(
            f"inline JSON parse failed ({exc}); recovered from "
            f"{page_id}_translation.json written by the agent"
        )

    missing = [sid for sid in all_ids if sid not in translations]
    if missing:
        warnings.append(f"Missing IDs: {', '.join(missing)}")

    # Persist sentence records
    for unit in sentences:
        existing[unit.sentence_id] = _sentence_record(
            unit,
            translations.get(unit.sentence_id, ""),
            timestamp=timestamp,
            model=model,
            lexicon_profile=lexicon_profile,
        )

    # Persist footnote records
    for i, fn in enumerate(footnotes, start=len(sentences) + 1):
        sid = _fn_segment_id(fn)
        existing[sid] = _fn_record(
            fn,
            translations.get(sid, ""),
            page_id,
            i,
            timestamp=timestamp,
            model=model,
            lexicon_profile=lexicon_profile,
        )

    return {
        "page_id": page_id,
        "status": "translated",
        "sentence_count": len(sentences),
        "footnote_count": len(footnotes),
        "missing": missing,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Sentence-level Latin → English translation. "
            "Writes to segments_sentences.jsonl."
        )
    )
    p.add_argument("--part", default="part1")
    p.add_argument("--start-page", type=int, required=True)
    p.add_argument("--end-page", type=int, required=True)
    p.add_argument("--lexicon-profile", default="auto",
                   choices=list(_v5.LEXICON_PROFILES))
    p.add_argument("--extra-context", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--timeout-seconds", type=float, default=None)
    p.add_argument(
        "--cross-page", action="store_true",
        help="Group sentences across page seams so a sentence that straddles "
             "a page boundary is translated as one whole unit. The spanning "
             "sentence is homed on the page where it begins; the continuation "
             "page's lines are not re-emitted. Defaults the output to "
             "segments_sentences_xpage.jsonl so the two segmentations never "
             "mix.",
    )
    p.add_argument(
        "--model", default=None,
        help="Override the provider's model id for this run (e.g. "
             "claude-opus-4-8 for an A/B comparison run; pair with "
             "--output-name so artifacts never mix).",
    )
    p.add_argument(
        "--output-name", default=None,
        help="Override the output JSONL filename under "
             "03_segmented_text/<part>/. Defaults to segments_sentences.jsonl "
             "(per-page) or segments_sentences_xpage.jsonl (--cross-page).",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Resolve the output artifact name (cross-page goes to its own file).
    global _OUTPUT_NAME
    if args.output_name:
        _OUTPUT_NAME = args.output_name
    elif args.cross_page:
        _OUTPUT_NAME = "segments_sentences_xpage.jsonl"

    config = default_config()
    provider = config.translation_provider()
    if args.timeout_seconds is not None:
        provider = replace(provider, timeout_seconds=float(args.timeout_seconds))
    if args.model:
        # Model override for A/B runs (e.g. re-translating a chapter with a
        # different model into a separate --output-name artifact). The
        # adapter pins --model on every CLI call, and each unit records the
        # producing model in translation_history.
        provider = replace(provider, model=args.model)

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

    page_ids = list(_iter_page_ids(args.part, args.start_page, args.end_page))

    # Cross-page mode: segment the whole range once, then group the resulting
    # sentence units by their home page so each page's translate_page call gets
    # exactly the units that begin on it (some carrying next-page lines).
    sentences_by_home: dict[str, list[SentenceUnit]] | None = None
    if args.cross_page:
        loaded = [(pid, load_page_body(args.part, pid)) for pid in page_ids]
        # Range-wide marker lookup: a cross-page sentence may carry markers
        # whose footnotes live on the continuation page, so the lookup must
        # cover every page in the range, not just the home page.
        all_fns: list[dict] = []
        for pid in page_ids:
            pp = _resolve_page_path(args.part, pid)
            if pp is not None and pp.exists():
                _, fns = extract_units(load_phase3b_page(pp))
                all_fns.extend(fns)
        marker_lookup = _build_marker_lookup(all_fns)
        all_units = group_pages_into_sentences(loaded, marker_lookup=marker_lookup)

        clashes = find_seam_clashes(all_units, existing)
        if clashes:
            unit_id, owners = clashes[0]
            homes = ", ".join(sorted({c.split("_")[1] for c in owners}))
            print(
                f"ERROR: lines of {unit_id} are already owned by "
                f"{', '.join(owners)} in the existing artifact. The page "
                f"range starts mid-seam; widen it to include the owning "
                f"sentence's home page ({homes}) and re-run — completed "
                f"pages are skipped automatically.",
                file=sys.stderr,
            )
            return 2

        sentences_by_home = {pid: [] for pid in page_ids}
        for u in all_units:
            sentences_by_home.setdefault(u.page_id, []).append(u)

    run_log: dict[str, Any] = {
        "started_at": timestamp,
        "part": args.part,
        "start_page": args.start_page,
        "end_page": args.end_page,
        "model": model,
        "dry_run": args.dry_run,
        "force": args.force,
        "cross_page": args.cross_page,
        "output": str(_output_path(args.part)),
        "pages": [],
    }

    # Fail fast on a dead provider: consecutive CLI process failures mean
    # usage exhaustion / an auth lapse, which will fail identically for every
    # remaining page. Abort and let resume-by-rerun pick up later, instead of
    # burning a retry cycle per page against a wall (a ch2 run hammered ten
    # pages in a row this way).
    _CLI_ABORT_AFTER = 2
    consecutive_cli_failures = 0

    for pid in page_ids:
        page_log = translate_page(
            pid,
            part=args.part,
            adapter=adapter,
            existing=existing,
            lexicon_profile=args.lexicon_profile,
            extra_context=extra_context,
            force=args.force,
            dry_run=args.dry_run,
            timestamp=timestamp,
            model=model,
            sentences=(sentences_by_home.get(pid, [])
                       if sentences_by_home is not None else None),
        )
        run_log["pages"].append(page_log)

        status = page_log["status"]
        if args.dry_run:
            print(
                f"{pid}: {status}  "
                f"prompt_chars={page_log.get('prompt_chars', 0)}  "
                f"sentences={page_log.get('sentence_count', 0)}  "
                f"footnotes={page_log.get('footnote_count', 0)}"
            )
        else:
            print(f"{pid}: {status}")
            for w in page_log.get("warnings", []):
                print(f"  WARN: {w}")

        if not args.dry_run and status == "translated":
            write_artifact(args.part, existing)

        if status == "error:cli_failure":
            consecutive_cli_failures += 1
            if consecutive_cli_failures >= _CLI_ABORT_AFTER:
                run_log["aborted"] = (
                    f"{consecutive_cli_failures} consecutive CLI process "
                    f"failures at {pid}"
                )
                print(
                    f"\nABORTING: {consecutive_cli_failures} consecutive CLI "
                    f"process failures (usage limit exhausted? auth lapsed?). "
                    f"Translated pages are already written; re-run the same "
                    f"command later to resume from {pid}.",
                    file=sys.stderr,
                )
                break
        elif status != "skipped":
            consecutive_cli_failures = 0

    logs_dir = _logs_dir(args.part)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / (
        f"sentences_run_{timestamp.replace(':', '').replace('-', '')}.json"
    )
    log_path.write_text(
        json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    translated = sum(1 for p in run_log["pages"] if p["status"] == "translated")
    skipped = sum(1 for p in run_log["pages"] if p["status"] == "skipped")
    print(f"\nDone. translated={translated} skipped={skipped}")
    print(f"Output: {_output_path(args.part)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
