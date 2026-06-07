"""Render interlinear pages from ``segments_with_translations.jsonl``.

Inputs
------
The JSONL artifact written by :mod:`translate_segments`. Each record
carries:
- ``page_id``, ``segment_id``, ``segment_type`` (``body`` or ``footnote``)
- ``latin_text`` with inline ``^<marker_id>`` caret sentinels at each
  footnote anchor (body lines only)
- ``markers`` — structured cross-references for body lines
- ``translation_history[]`` (latest entry's ``english`` carries inline
  ``^<marker_id>`` carets for body lines, placed by the second-pass
  marker-placement runner)
- For footnote records, ``body_segment_id`` and ``marker_id`` linking
  back to the anchoring body segment.

Outputs
-------
One file per page in ``05_final_output/<part>/`` (or a user-supplied
output directory). Two formats are supported:

- ``markdown`` — Pandoc-friendly Markdown using HTML ``<sup>`` for
  footnote anchors. Pandoc -> PDF/HTML/EPUB works directly.
- ``html`` — standalone HTML5 with bidirectional links between body
  anchors and the footnotes section.

The renderer never invents data; it consumes only what the artifact
already records, and it never modifies the JSONL.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


# ---------------------------------------------------------------------------
# Workspace layout (mirrors translate_segments)
# ---------------------------------------------------------------------------


_HERE = Path(__file__).resolve().parent
WORKSPACE_ROOT = _HERE.parent.parent  # .../UssherIn
ARTIFACTS_DIR = WORKSPACE_ROOT / "03_segmented_text"
DEFAULT_OUT_DIR = WORKSPACE_ROOT / "05_final_output"

# Source artifact + polished subdirectory. Overridable from the CLI so the
# same renderer serves the line-by-line run (defaults) and the sentence-level
# run (``--segments-name segments_sentences.jsonl --polished-subdir
# polished_sentences``) without disturbing either's outputs.
_SEGMENTS_NAME = "segments_with_translations.jsonl"
_POLISHED_SUBDIR = "polished"


# ---------------------------------------------------------------------------
# Polished-translation artifact loader
# ---------------------------------------------------------------------------


def _polished_path(part: str, page_id: str) -> Path:
    return ARTIFACTS_DIR / part / _POLISHED_SUBDIR / f"{page_id}.json"


def load_polished(part: str, page_id: str) -> dict | None:
    """Return the parsed polished artifact for *page_id* or None.

    The artifact is written by :mod:`polish_translations` and carries
    a single flowing-prose ``english`` field (with ``^X`` carets at
    footnote-anchor positions) plus provenance metadata.
    """
    path = _polished_path(part, page_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: malformed polished artifact: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public formats
# ---------------------------------------------------------------------------


FORMATS = ("markdown", "html")
_EXT_BY_FORMAT = {"markdown": "md", "html": "html"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_segments(part: str) -> list[dict]:
    """Read the segments JSONL for *part* and return records in file order."""
    path = ARTIFACTS_DIR / part / _SEGMENTS_NAME
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


# ---------------------------------------------------------------------------
# Page grouping
# ---------------------------------------------------------------------------


@dataclass
class PageBundle:
    """Body + footnote records for a single page, ready for rendering.

    ``polished`` is the parsed per-page polished artifact (or ``None``
    when no polished pass has run for this page). When present, its
    ``english`` field is rendered as a separate ``## Reading`` section
    after the interlinear block.
    """

    page_id: str
    body: list[dict]
    footnotes: list[dict]
    polished: dict | None = None
    # Set when a cross-page sentence homed on an earlier page absorbs this
    # page's opening lines: ``{"from_page": "p0036", "sentence_id": "..."}``.
    # Drives the "⟵ opening lines complete pNNNN's sentence" reviewer cue.
    continued_from: dict | None = None


def _segment_sort_key(seg: dict) -> tuple:
    """Order segments by ``seq`` (the explicit ordering field). Falls
    back to a regex on ``segment_id`` for legacy records that pre-date
    ``seq``, so the migration window stays stable. ``segment_id`` is
    always the final tie-breaker for determinism.
    """
    seg_id = seg.get("segment_id", "")
    seq = seg.get("seq")
    if isinstance(seq, int):
        return (0, seq, seg_id)
    body_match = re.search(r"_l(\d+)$", seg_id)
    if body_match:
        return (1, int(body_match.group(1)), seg_id)
    fn_match = re.search(r"_fn_(\d+)$", seg_id)
    if fn_match:
        return (1, int(fn_match.group(1)), seg_id)
    return (2, 0, seg_id)


def _line_anchor_id(seg: dict, page_id: str) -> str:
    """Return ``line-<page>-l<NNNN>`` for a body segment, or ``""``.

    These ids are emitted on each interlinear body row so collaborators
    can deep-link a comment to a specific line (e.g. the URL fragment
    ``#line-p0036-l0007`` jumps to the seventh body line of p0036).
    """
    seg_id = seg.get("segment_id", "")
    match = re.search(r"_l(\d+)$", seg_id)
    if not match:
        return ""
    return f"line-{page_id}-l{int(match.group(1)):04d}"


def group_by_page(
    segments: Iterable[dict],
    *,
    part: str | None = None,
) -> list[PageBundle]:
    """Group segments by ``page_id`` and split body vs. footnote.

    The output is sorted by page_id (lexicographic, which preserves
    p0001…pNNNN ordering), and within each page body lines come first
    in line-number order, then footnotes in marker order. When *part*
    is supplied, an attempt is made to load the per-page polished
    artifact for each page and attach it to the bundle.
    """
    by_page: dict[str, dict[str, list[dict]]] = {}
    # Continuation map: a cross-page sentence (``spans_pages`` longer than one,
    # home page first) absorbs the opening lines of each later page it touches.
    continued_from: dict[str, dict] = {}
    for seg in segments:
        page_id = seg.get("page_id") or ""
        if not page_id:
            continue
        bucket = by_page.setdefault(page_id, {"body": [], "footnote": []})
        seg_type = seg.get("segment_type") or "body"
        if seg_type == "footnote":
            bucket["footnote"].append(seg)
        else:
            bucket["body"].append(seg)
        spans = seg.get("spans_pages") or []
        if len(spans) > 1:
            home, sid = spans[0], seg.get("segment_id") or ""
            for cont_page in spans[1:]:
                continued_from.setdefault(
                    cont_page, {"from_page": home, "sentence_id": sid}
                )

    bundles: list[PageBundle] = []
    for page_id in sorted(by_page.keys()):
        body = sorted(by_page[page_id]["body"], key=_segment_sort_key)
        footnotes = sorted(by_page[page_id]["footnote"], key=_segment_sort_key)
        polished = load_polished(part, page_id) if part else None
        bundles.append(
            PageBundle(
                page_id=page_id,
                body=body,
                footnotes=footnotes,
                polished=polished,
                continued_from=continued_from.get(page_id),
            )
        )
    return bundles


# ---------------------------------------------------------------------------
# Latest-history accessor
# ---------------------------------------------------------------------------


def latest_english(seg: dict) -> str:
    """Return the most recent ``english`` value from translation_history.

    The artifact contract guarantees an append-only history; callers
    therefore want the *last* entry (the latest model output, possibly
    with marker carets inserted by the second-pass runner).
    """
    history = seg.get("translation_history") or []
    if not history:
        return ""
    last = history[-1] or {}
    text = last.get("english")
    return text if isinstance(text, str) else ""


# ---------------------------------------------------------------------------
# Caret-to-superscript transformation
# ---------------------------------------------------------------------------


# Marker ids in this corpus are short (single letters or letter-pairs),
# typically the printed superscript footnote letters (a–z, sometimes
# digits or letter pairs like 'aa'). Restricting to alphanumerics
# prevents adjacent punctuation from being absorbed into the marker.
_CARET_RE = re.compile(r"\^([A-Za-z0-9]{1,2})")


def _carets_to_anchors(
    text: str,
    *,
    page_id: str,
    fn_id_for_marker: dict[str, str],
    fmt: str,
    emit_backref_id: bool = True,
) -> str:
    """Replace ``^X`` sentinels in *text* with a footnote anchor.

    For HTML, links are emitted as ``<sup><a href="#fn-...">X</a></sup>``
    pointing to the in-page footnote target. For Markdown we emit raw
    ``<sup>`` so Pandoc preserves it; an empty ``href`` is used when no
    matching footnote is registered for the marker on this page.

    The ``id="fnref-..."`` attribute used for footnote-back-to-body
    navigation is emitted only when ``emit_backref_id`` is True. Pages
    render two parallel lines (Latin + English) per body segment, so
    only one of the two should claim the id; we put it on the Latin
    line by convention.
    """

    def replace(match: re.Match) -> str:
        marker = match.group(1)
        target_seg = fn_id_for_marker.get(marker)
        anchor_id = f"fn-{target_seg}" if target_seg else ""
        body_id = f"fnref-{page_id}-{marker}" if emit_backref_id else ""
        marker_safe = html.escape(marker, quote=True)
        id_attr = f' id="{body_id}"' if body_id else ""
        if anchor_id:
            return (
                f"<sup{id_attr}>"
                f'<a href="#{anchor_id}">{marker_safe}</a>'
                f"</sup>"
            )
        return f"<sup{id_attr}>{marker_safe}</sup>"

    return _CARET_RE.sub(replace, text or "")


def _strip_carets(text: str) -> str:
    """Remove ``^X`` sentinels entirely (used by the plain-text helper)."""
    return _CARET_RE.sub("", text or "")


def _split_paragraphs(text: str) -> list[str]:
    """Split *text* into paragraphs on blank lines.

    The polished pass writes flowing prose; we honor any blank-line
    breaks the model produced (sense-driven paragraphing) and fall
    back to a single paragraph when the model returned a continuous
    run of text. Empty paragraphs are dropped.
    """
    if not text:
        return []
    chunks = re.split(r"\n\s*\n+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _fn_lookup_for_page(footnotes: Sequence[dict]) -> dict[str, str]:
    """Map ``marker_id -> segment_id`` for a single page's footnotes."""
    out: dict[str, str] = {}
    for fn in footnotes:
        marker = fn.get("marker_id")
        seg_id = fn.get("segment_id")
        if marker and seg_id:
            out[str(marker)] = str(seg_id)
    return out


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _line_no_from_id(line_id: str) -> str:
    """'p0037_body_l0026' -> 'l0026' (or '' if no match)."""
    m = re.search(r"_l(\d+)$", line_id or "")
    return f"l{int(m.group(1)):04d}" if m else ""


def _spans_continuation(seg: dict) -> list[str]:
    """Pages after the home page that a cross-page sentence continues onto."""
    spans = seg.get("spans_pages") or []
    return spans[1:] if len(spans) > 1 else []


def _continued_from_text(bundle: PageBundle) -> str:
    """Reviewer cue (plain text) for a page whose opening lines were absorbed
    by a cross-page sentence homed on an earlier page. Empty when N/A."""
    cf = bundle.continued_from
    if not cf:
        return ""
    src = cf.get("from_page", "?")
    sid = cf.get("sentence_id", "")
    sid_part = f" ({sid})" if sid else ""
    if bundle.body:
        resumes = _line_no_from_id((bundle.body[0].get("source_line_ids") or [""])[0])
        tail = f"This page's own text begins below at {resumes}." if resumes \
            else "This page's own text begins below."
    else:
        tail = "This entire page completes that sentence; no new sentence begins here."
    return (f"⟵ The opening lines of this page complete the final sentence "
            f"of {src}{sid_part}, translated there. {tail}")


def render_page_markdown(
    bundle: PageBundle,
    *,
    include_reading: bool = True,
    reading_only: bool = False,
) -> str:
    """Render *bundle* as Pandoc-friendly Markdown with HTML supers.

    The output has up to two sections per page:

    - ``## Interlinear`` — paired Latin/English lines and the footnote
      block (always rendered unless ``reading_only`` is True).
    - ``## Reading`` — the polished flowing-prose translation, with
      ``^X`` carets converted to footnote-linked ``<sup>`` tags
      (rendered when ``include_reading`` is True and a polished
      artifact is attached to the bundle).
    """
    fn_lookup = _fn_lookup_for_page(bundle.footnotes)
    lines: list[str] = [f"# Page {bundle.page_id}", ""]

    if not reading_only:
        lines.append("## Interlinear")
        lines.append("")
        back_note = _continued_from_text(bundle)
        if back_note:
            lines.append(f"*{back_note}*")
            lines.append("")
        for seg in bundle.body:
            anchor_id = _line_anchor_id(seg, bundle.page_id)
            anchor = f'<a id="{anchor_id}"></a>' if anchor_id else ""
            latin = _carets_to_anchors(
                seg.get("latin_text") or "",
                page_id=bundle.page_id,
                fn_id_for_marker=fn_lookup,
                fmt="markdown",
                emit_backref_id=True,
            )
            english = _carets_to_anchors(
                latest_english(seg),
                page_id=bundle.page_id,
                fn_id_for_marker=fn_lookup,
                fmt="markdown",
                emit_backref_id=False,
            )
            lines.append(f"{anchor}**LA**  {latin}")
            lines.append("")
            lines.append(f"**EN**  {english}")
            lines.append("")
            cont = _spans_continuation(seg)
            if cont:
                lines.append(
                    f"*⟶ This sentence's Latin runs onto {', '.join(cont)}; "
                    f"it is translated whole here.*"
                )
                lines.append("")

        if bundle.footnotes:
            lines.append("## Footnotes")
            lines.append("")
            for fn in bundle.footnotes:
                marker = fn.get("marker_id") or ""
                seg_id = fn.get("segment_id") or ""
                anchor = f'<a id="fn-{seg_id}"></a>' if seg_id else ""
                backref_marker = (
                    f'<a href="#fnref-{bundle.page_id}-{marker}">^{marker}</a>'
                    if marker
                    else ""
                )
                latin_fn = _strip_carets(fn.get("latin_text") or "")
                english_fn = _strip_carets(latest_english(fn))
                lines.append(f"{anchor}**{backref_marker}**  *LA:* {latin_fn}")
                lines.append("")
                lines.append(f"**EN:** {english_fn}")
                lines.append("")

    if include_reading and bundle.polished:
        polished_english = bundle.polished.get("english") or ""
        rendered_reading = _carets_to_anchors(
            polished_english,
            page_id=bundle.page_id,
            fn_id_for_marker=fn_lookup,
            fmt="markdown",
            emit_backref_id=False,
        )
        lines.append("## Reading")
        lines.append("")
        for paragraph in _split_paragraphs(rendered_reading):
            lines.append(paragraph)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_HTML_DOCUMENT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ussher Antiquitates — {page_id}</title>
<style>
body {{ font-family: 'Cambria', Georgia, serif; max-width: 50rem;
       margin: 2rem auto; padding: 0 1.5rem; line-height: 1.55; }}
h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; }}
h2 {{ font-size: 1.1rem; margin-top: 2.5rem; border-top: 1px solid #ccc;
      padding-top: 1rem; }}
.row {{ margin: 0 0 1.2rem 0; }}
.lang {{ display: inline-block; width: 2.5rem; font-weight: 600;
         color: #666; vertical-align: top; }}
.la, .en {{ display: inline-block; width: calc(100% - 3rem); }}
.la {{ font-style: italic; color: #333; }}
.fn {{ margin: 0.6rem 0 1.2rem 0; font-size: 0.95rem; }}
.fn-marker {{ font-weight: 700; margin-right: 0.4rem; }}
.fn-la {{ font-style: italic; color: #333; }}
section.reading {{ font-size: 1.05rem; line-height: 1.7;
                   text-align: justify; }}
section.reading p {{ margin: 0 0 1rem 0; }}
sup a {{ text-decoration: none; color: #0a58ca; }}
sup a:hover {{ text-decoration: underline; }}
.xpage {{ font-style: italic; color: #7a5; font-size: 0.9rem;
          margin: 0 0 1rem 0; }}
</style>
</head>
<body>
<h1>Page {page_id}</h1>
{interlinear}
{reading}
</body>
</html>
"""


def render_page_html(
    bundle: PageBundle,
    *,
    include_reading: bool = True,
    reading_only: bool = False,
) -> str:
    """Render *bundle* as a standalone HTML5 document.

    See :func:`render_page_markdown` for the section-structure rules.
    """
    fn_lookup = _fn_lookup_for_page(bundle.footnotes)
    interlinear_block = ""

    if not reading_only:
        body_parts: list[str] = ["<h2>Interlinear</h2>"]
        back_note = _continued_from_text(bundle)
        if back_note:
            body_parts.append(f'<p class="xpage">{html.escape(back_note)}</p>')
        for seg in bundle.body:
            anchor_id = _line_anchor_id(seg, bundle.page_id)
            row_id_attr = f' id="{anchor_id}"' if anchor_id else ""
            latin = _carets_to_anchors(
                seg.get("latin_text") or "",
                page_id=bundle.page_id,
                fn_id_for_marker=fn_lookup,
                fmt="html",
                emit_backref_id=True,
            )
            english = _carets_to_anchors(
                latest_english(seg),
                page_id=bundle.page_id,
                fn_id_for_marker=fn_lookup,
                fmt="html",
                emit_backref_id=False,
            )
            body_parts.append(
                f'<div class="row"{row_id_attr}>\n'
                f"  <div><span class=\"lang\">LA</span><span class=\"la\">{latin}</span></div>\n"
                f"  <div><span class=\"lang\">EN</span><span class=\"en\">{english}</span></div>\n"
                "</div>"
            )
            cont = _spans_continuation(seg)
            if cont:
                note = (f"⟶ This sentence's Latin runs onto {', '.join(cont)}; "
                        f"it is translated whole here.")
                body_parts.append(f'<p class="xpage">{html.escape(note)}</p>')

        if bundle.footnotes:
            body_parts.append("<h2>Footnotes</h2>")
            for fn in bundle.footnotes:
                marker = fn.get("marker_id") or ""
                seg_id = fn.get("segment_id") or ""
                marker_safe = html.escape(marker, quote=True)
                backref = (
                    f'<a href="#fnref-{bundle.page_id}-{marker_safe}">^</a>'
                    if marker
                    else ""
                )
                latin_fn = html.escape(_strip_carets(fn.get("latin_text") or ""))
                english_fn = html.escape(_strip_carets(latest_english(fn)))
                body_parts.append(
                    f'<div class="fn" id="fn-{seg_id}">\n'
                    f'  <span class="fn-marker">{backref}{marker_safe}</span>\n'
                    f'  <span class="fn-la"><em>LA:</em> {latin_fn}</span><br>\n'
                    f'  <span><em>EN:</em> {english_fn}</span>\n'
                    "</div>"
                )
        interlinear_block = "\n".join(body_parts)

    reading_block = ""
    if include_reading and bundle.polished:
        polished_english = bundle.polished.get("english") or ""
        rendered = _carets_to_anchors(
            polished_english,
            page_id=bundle.page_id,
            fn_id_for_marker=fn_lookup,
            fmt="html",
            emit_backref_id=False,
        )
        paragraphs = "\n".join(
            f"<p>{p}</p>" for p in _split_paragraphs(rendered)
        )
        reading_block = (
            "<h2>Reading</h2>\n"
            f'<section class="reading">\n{paragraphs}\n</section>'
        )

    return _HTML_DOCUMENT_TEMPLATE.format(
        page_id=html.escape(bundle.page_id),
        interlinear=interlinear_block,
        reading=reading_block,
    )


# ---------------------------------------------------------------------------
# Page-range filtering + write
# ---------------------------------------------------------------------------


def _page_in_range(page_id: str, start: int | None, end: int | None) -> bool:
    if start is None and end is None:
        return True
    match = re.match(r"p(\d+)$", page_id)
    if not match:
        return False
    n = int(match.group(1))
    if start is not None and n < start:
        return False
    if end is not None and n > end:
        return False
    return True


def render_pages(
    *,
    part: str,
    out_dir: Path,
    fmt: str,
    start_page: int | None,
    end_page: int | None,
    include_reading: bool = True,
    reading_only: bool = False,
) -> list[Path]:
    """Render selected pages and return the list of files written."""
    if fmt not in FORMATS:
        raise ValueError(f"format {fmt!r} not in {FORMATS}")
    segments = load_segments(part)
    bundles = [
        b for b in group_by_page(segments, part=part)
        if _page_in_range(b.page_id, start_page, end_page)
    ]
    if not bundles:
        return []

    target_dir = out_dir / part
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = _EXT_BY_FORMAT[fmt]
    written: list[Path] = []
    for bundle in bundles:
        if fmt == "markdown":
            text = render_page_markdown(
                bundle,
                include_reading=include_reading,
                reading_only=reading_only,
            )
        else:
            text = render_page_html(
                bundle,
                include_reading=include_reading,
                reading_only=reading_only,
            )
        out_path = target_dir / f"{bundle.page_id}_interlinear.{ext}"
        out_path.write_text(text, encoding="utf-8")
        written.append(out_path)
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render interlinear (Latin/Greek + English) pages from the "
            "segments_with_translations.jsonl artifact."
        ),
    )
    parser.add_argument("--part", default="part1")
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument(
        "--format",
        choices=FORMATS,
        default="html",
        help="Output format (default: html).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output root directory (default: 05_final_output/).",
    )
    parser.add_argument(
        "--segments-name",
        default=_SEGMENTS_NAME,
        help="Source JSONL filename under 03_segmented_text/<part>/ "
             "(default: segments_with_translations.jsonl; use "
             "segments_sentences.jsonl for the sentence-level run).",
    )
    parser.add_argument(
        "--polished-subdir",
        default=_POLISHED_SUBDIR,
        help="Polished-artifact subdirectory under "
             "03_segmented_text/<part>/ (default: polished; use "
             "polished_sentences for the sentence-level run).",
    )
    reading_group = parser.add_mutually_exclusive_group()
    reading_group.add_argument(
        "--no-reading",
        dest="include_reading",
        action="store_false",
        help=(
            "Suppress the polished-prose Reading section even when a "
            "polished artifact is available for the page."
        ),
    )
    reading_group.add_argument(
        "--reading-only",
        dest="reading_only",
        action="store_true",
        help=(
            "Emit only the Reading section (no Interlinear or Footnotes "
            "blocks). Has no effect when no polished artifact exists."
        ),
    )
    parser.set_defaults(include_reading=True, reading_only=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    global _SEGMENTS_NAME, _POLISHED_SUBDIR
    _SEGMENTS_NAME = args.segments_name
    _POLISHED_SUBDIR = args.polished_subdir
    written = render_pages(
        part=args.part,
        out_dir=args.out_dir,
        fmt=args.format,
        start_page=args.start_page,
        end_page=args.end_page,
        include_reading=args.include_reading,
        reading_only=args.reading_only,
    )
    if not written:
        print("No pages rendered (no matching records).", file=sys.stderr)
        return 1
    for path in written:
        print(path.relative_to(WORKSPACE_ROOT) if path.is_relative_to(WORKSPACE_ROOT)
              else path)
    return 0


__all__ = [
    "ARTIFACTS_DIR",
    "DEFAULT_OUT_DIR",
    "FORMATS",
    "PageBundle",
    "group_by_page",
    "latest_english",
    "load_polished",
    "load_segments",
    "render_page_html",
    "render_page_markdown",
    "render_pages",
]


if __name__ == "__main__":
    raise SystemExit(main())
