"""Polish whole-page translations into flowing English prose.

This runner consumes the literal ``machine_draft`` translations
already persisted in ``segments_with_translations.jsonl`` and asks
Claude to rewrite each page's body lines as a single flowing English
narrative (preserving every ``^X`` footnote-anchor sentinel). The
result is persisted as a per-page artifact under
``03_segmented_text/<part>/polished/<page_id>.json`` and is consumed
by :mod:`render_interlinear` to add a "Reading" section to the
rendered output.

Footnotes are NOT polished; they remain at ``machine_draft``. Only
body segments are rewritten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import replace
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
)
from translation_prompts import (  # noqa: E402
    LEXICON_PROFILES,
    build_polishing_prompt,
)


# ---------------------------------------------------------------------------
# Workspace layout (mirrors translate_segments)
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = _HERE.parent.parent  # .../UssherIn
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"


def _segments_path(part: str) -> Path:
    return ARTIFACTS_DIR / part / "segments_with_translations.jsonl"


def _polished_dir(part: str) -> Path:
    return ARTIFACTS_DIR / part / "polished"


def _polished_path(part: str, page_id: str) -> Path:
    return _polished_dir(part) / f"{page_id}.json"


def _logs_dir(part: str) -> Path:
    return ARTIFACTS_DIR / part / ".logs"


# ---------------------------------------------------------------------------
# Loading + grouping
# ---------------------------------------------------------------------------


def load_segments(part: str) -> list[dict]:
    """Read ``segments_with_translations.jsonl`` for *part*."""
    path = _segments_path(part)
    if not path.exists():
        raise FileNotFoundError(
            f"No segments artifact for part {part!r} at {path}"
        )
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}: malformed JSON on line {line_no}: {exc}"
                ) from exc
    return out


_BODY_LINE_RE = re.compile(r"_l(\d+)$")
_FN_RE = re.compile(r"_fn_(\d+)$")


def _body_sort_key(seg: dict) -> tuple:
    seg_id = seg.get("segment_id", "")
    match = _BODY_LINE_RE.search(seg_id)
    if match:
        return (0, int(match.group(1)), seg_id)
    return (1, 0, seg_id)


def _fn_sort_key(seg: dict) -> tuple:
    seg_id = seg.get("segment_id", "")
    match = _FN_RE.search(seg_id)
    if match:
        return (0, int(match.group(1)), seg_id)
    return (1, 0, seg_id)


def group_by_page(segments: Iterable[dict]) -> dict[str, dict]:
    """Group segments by ``page_id`` into ``{page_id: {body, footnotes}}``.

    Body and footnote lists are sorted by their numeric suffix.
    """
    pages: dict[str, dict] = {}
    for seg in segments:
        page_id = seg.get("page_id") or ""
        if not page_id:
            continue
        bucket = pages.setdefault(page_id, {"body": [], "footnotes": []})
        if seg.get("segment_type") == "footnote":
            bucket["footnotes"].append(seg)
        else:
            bucket["body"].append(seg)
    for bucket in pages.values():
        bucket["body"].sort(key=_body_sort_key)
        bucket["footnotes"].sort(key=_fn_sort_key)
    return pages


def _latest_history(seg: dict) -> dict | None:
    history = seg.get("translation_history") or []
    return history[-1] if history else None


def _latest_english(seg: dict) -> str:
    last = _latest_history(seg) or {}
    text = last.get("english")
    return text if isinstance(text, str) else ""


def _latest_version(seg: dict) -> int:
    last = _latest_history(seg) or {}
    version = last.get("version")
    return int(version) if isinstance(version, (int, float)) else 0


# ---------------------------------------------------------------------------
# Page payload assembly
# ---------------------------------------------------------------------------


def build_body_units(body_segments: Sequence[dict]) -> list[dict]:
    """Build the ``body_units`` list passed to ``build_polishing_prompt``."""
    units: list[dict] = []
    for seg in body_segments:
        units.append({
            "segment_id": seg.get("segment_id", ""),
            "latin_text": seg.get("latin_text") or "",
            "literal_english": _latest_english(seg),
        })
    return units


def build_footnote_glosses(fn_segments: Sequence[dict]) -> list[dict]:
    """Build the ``footnotes`` context list for the polishing prompt."""
    out: list[dict] = []
    for seg in fn_segments:
        out.append({
            "marker_id": seg.get("marker_id") or "",
            "segment_id": seg.get("segment_id") or "",
            "english": _latest_english(seg),
        })
    return out


def collect_required_markers(body_segments: Sequence[dict]) -> list[str]:
    """Return distinct marker ids in printed order from body Latin text."""
    pattern = re.compile(r"\^([A-Za-z0-9]{1,2})")
    seen: list[str] = []
    seen_set: set[str] = set()
    for seg in body_segments:
        latin = seg.get("latin_text") or ""
        for match in pattern.finditer(latin):
            marker = match.group(1)
            if marker not in seen_set:
                seen_set.add(marker)
                seen.append(marker)
    return seen


# ---------------------------------------------------------------------------
# Polished output validation
# ---------------------------------------------------------------------------


_OUTPUT_MARKER_RE = re.compile(r"\^([A-Za-z0-9]{1,2})")


class PolishValidationError(Exception):
    """Raised when the model's polished output fails marker validation."""


def validate_polished_output(
    *,
    text: str,
    required_markers: Sequence[str],
) -> list[str]:
    """Check that *text* contains each required marker exactly once and
    introduces no foreign markers. Returns a list of warning strings
    (empty when output is clean). Raises ``PolishValidationError`` on
    fatal mismatch (missing or duplicated markers).
    """
    if not text or not text.strip():
        raise PolishValidationError("polished output was empty")

    found: list[str] = [m.group(1) for m in _OUTPUT_MARKER_RE.finditer(text)]
    counts: dict[str, int] = {}
    for marker in found:
        counts[marker] = counts.get(marker, 0) + 1

    warnings: list[str] = []

    for marker in required_markers:
        c = counts.get(marker, 0)
        if c == 0:
            raise PolishValidationError(
                f"required marker '^{marker}' missing from polished output"
            )
        if c > 1:
            raise PolishValidationError(
                f"required marker '^{marker}' appears {c} times "
                f"(must appear exactly once)"
            )

    extras = sorted(set(counts) - set(required_markers))
    for extra in extras:
        warnings.append(
            f"polished output contains unexpected marker '^{extra}'; "
            f"keeping it but it does not match any footnote on this page"
        )
    return warnings


# ---------------------------------------------------------------------------
# Artifact writing
# ---------------------------------------------------------------------------


def load_polished_artifact(part: str, page_id: str) -> dict | None:
    """Return the parsed polished artifact for *page_id* or None."""
    path = _polished_path(part, page_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_polished_artifact(part: str, page_id: str, payload: dict) -> Path:
    """Write *payload* to the per-page polished artifact path."""
    path = _polished_path(part, page_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Page-level orchestration
# ---------------------------------------------------------------------------


def polish_page(
    page_id: str,
    *,
    body_segments: Sequence[dict],
    fn_segments: Sequence[dict],
    adapter: AnthropicTranslationAdapter | None,
    lexicon_profile: str,
    extra_context: str | None,
    force: bool,
    dry_run: bool,
    timestamp: str,
    part: str,
) -> dict[str, Any]:
    """Polish one page and write the artifact. Returns a per-page log."""

    # Skip pages where any body segment lacks a translation_history entry.
    missing = [
        seg.get("segment_id", "?")
        for seg in body_segments
        if not (seg.get("translation_history") or [])
    ]
    if missing:
        return {
            "page_id": page_id,
            "status": "skipped_missing_history",
            "missing_segments": missing,
        }

    # Idempotency: skip if artifact already exists and not forcing.
    existing = load_polished_artifact(part, page_id)
    if existing and not force:
        return {
            "page_id": page_id,
            "status": "skipped_artifact_exists",
            "existing_version": existing.get("version"),
        }

    body_units = build_body_units(body_segments)
    footnote_glosses = build_footnote_glosses(fn_segments)
    required_markers = collect_required_markers(body_segments)

    prompt = build_polishing_prompt(
        page_id=page_id,
        body_units=body_units,
        footnotes=footnote_glosses,
        lexicon_profile=lexicon_profile,
        extra_context=extra_context,
    )

    if dry_run or adapter is None:
        return {
            "page_id": page_id,
            "status": "dry_run",
            "prompt_chars": len(prompt),
            "required_markers": required_markers,
            "prompt": prompt if dry_run else "",
        }

    try:
        response = adapter.complete_text(prompt)
    except TranslationError as exc:
        return {
            "page_id": page_id,
            "status": f"error:{getattr(exc, 'category', 'unknown')}",
            "error_message": str(exc),
        }

    response = (response or "").strip()
    try:
        warnings = validate_polished_output(
            text=response, required_markers=required_markers
        )
    except PolishValidationError as exc:
        return {
            "page_id": page_id,
            "status": "error:validation",
            "error_message": str(exc),
            "raw_response": response,
        }

    next_version = (existing.get("version", 0) + 1) if existing else 1
    source_versions = {
        seg.get("segment_id", ""): _latest_version(seg)
        for seg in body_segments
        if seg.get("segment_id")
    }
    artifact = {
        "page_id": page_id,
        "stage": "polished",
        "version": next_version,
        "timestamp": timestamp,
        "model": adapter.provider.model,
        "lexicon_profile": lexicon_profile,
        "source_versions": source_versions,
        "english": response,
        "warnings": warnings,
    }
    write_polished_artifact(part, page_id, artifact)
    return {
        "page_id": page_id,
        "status": "ok",
        "version": next_version,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Polish whole-page literal translations into flowing English "
            "prose, preserving footnote-anchor sentinels."
        ),
    )
    parser.add_argument("--part", default="part1")
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument(
        "--lexicon-profile",
        default="auto",
        choices=LEXICON_PROFILES,
    )
    parser.add_argument(
        "--extra-context",
        type=Path,
        default=None,
        help="Optional file whose contents are appended verbatim to the prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts but do not invoke Claude.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-polish pages whose artifact already exists (bumps version).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Override the translation provider timeout for this run.",
    )
    return parser


def _page_in_range(page_id: str, start: int, end: int) -> bool:
    match = re.match(r"p(\d+)$", page_id)
    if not match:
        return False
    n = int(match.group(1))
    return start <= n <= end


def _load_extra_context(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"could not read --extra-context at {path}: {exc}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)

    config = default_config()
    provider = config.translation_provider()
    if args.timeout_seconds is not None:
        provider = replace(provider, timeout_seconds=float(args.timeout_seconds))

    adapter: AnthropicTranslationAdapter | None = None
    if not args.dry_run:
        adapter = AnthropicTranslationAdapter(provider)

    extra_context = _load_extra_context(args.extra_context)

    segments = load_segments(args.part)
    pages = group_by_page(segments)

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

    for page_id in sorted(pages.keys()):
        if not _page_in_range(page_id, args.start_page, args.end_page):
            continue
        bucket = pages[page_id]
        page_log = polish_page(
            page_id,
            body_segments=bucket["body"],
            fn_segments=bucket["footnotes"],
            adapter=adapter,
            lexicon_profile=args.lexicon_profile,
            extra_context=extra_context,
            force=args.force,
            dry_run=args.dry_run,
            timestamp=timestamp,
            part=args.part,
        )
        run_log["pages"].append(page_log)

    logs_dir = _logs_dir(args.part)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / (
        f"polish_run_{timestamp.replace(':', '').replace('-', '')}.json"
    )
    log_path.write_text(
        json.dumps(run_log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.dry_run:
        for page in run_log["pages"]:
            print(
                f"[dry-run] {page['page_id']}: status={page['status']} "
                f"prompt_chars={page.get('prompt_chars', 0)} "
                f"markers={page.get('required_markers', [])}"
            )
    else:
        for page in run_log["pages"]:
            print(f"{page['page_id']}: {page['status']}")

    return 0


__all__ = [
    "ARTIFACTS_DIR",
    "PolishValidationError",
    "build_body_units",
    "build_footnote_glosses",
    "collect_required_markers",
    "group_by_page",
    "load_polished_artifact",
    "load_segments",
    "main",
    "polish_page",
    "validate_polished_output",
    "write_polished_artifact",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
