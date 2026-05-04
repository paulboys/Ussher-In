"""Trilinear side-by-side renderer for the A/B prompt rig.

Produces a markdown view with three lines per segment:

    Line 1: Latin source
    Line 2: v0 translation (or whichever path is given as ``--a``)
    Line 3: v2 translation (or whichever path is given as ``--b``)

Each segment is rendered as its own block keyed by ``segment_id``,
in source order. Useful for a quick read-through comparing two
prompt versions on the same page.

CLI
---
::

    python ab_trilinear.py \\
        --a 04_translation_work/ab/p0039/v0/run01/segments_with_translations.jsonl \\
        --b 04_translation_work/ab/p0039/v2/run01/segments_with_translations.jsonl \\
        --output 04_translation_work/ab/p0039/trilinear_run01.md \\
        [--a-label v0] [--b-label v2] [--page p0039]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    segment_id: str
    seq: int
    latin: str
    english: str
    segment_type: str = "body"


def _english_of(rec: dict) -> str:
    """Latest non-empty english from translation_history, else final_english."""
    history = rec.get("translation_history") or []
    for entry in reversed(history):
        eng = (entry.get("english") or "").strip()
        if eng:
            return eng
    return (rec.get("final_english") or "").strip()


def load_segments(path: Path) -> dict[str, Segment]:
    """Read a translator JSONL artifact into a dict keyed by segment_id."""
    out: dict[str, Segment] = {}
    with path.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            seg_id = str(rec.get("segment_id") or "")
            if not seg_id:
                continue
            out[seg_id] = Segment(
                segment_id=seg_id,
                seq=int(rec.get("seq") or 0),
                latin=(rec.get("latin_text") or "").strip(),
                english=_english_of(rec),
                segment_type=str(rec.get("segment_type") or "body"),
            )
    return out


def render_markdown(
    a: dict[str, Segment],
    b: dict[str, Segment],
    *,
    page: str,
    a_label: str,
    b_label: str,
) -> str:
    """Render trilinear markdown over the union of segment_ids.

    Segments present in only one side are still rendered, with a
    placeholder on the missing side, so absences are visible.

    Layout: body segments first (in seq order), then a Footnotes
    section with all footnote segments (in seq order).
    """
    def _seg_for(sid: str) -> Segment:
        return a.get(sid) or b[sid]

    body_ids = sorted(
        (sid for sid in set(a) | set(b) if _seg_for(sid).segment_type == "body"),
        key=lambda sid: (_seg_for(sid).seq, sid),
    )
    fn_ids = sorted(
        (sid for sid in set(a) | set(b) if _seg_for(sid).segment_type != "body"),
        key=lambda sid: (_seg_for(sid).seq, sid),
    )

    lines: list[str] = []
    lines.append(f"# Trilinear — {page}  (`{a_label}` vs `{b_label}`)")
    lines.append("")
    lines.append(
        f"Body segments first (in seq order), then footnotes. "
        f"Each block shows Latin source, then `{a_label}` rendering, "
        f"then `{b_label}` rendering. "
        f"Counts: {a_label}={len(a)}, {b_label}={len(b)}, "
        f"shared={len(set(a) & set(b))}, body={len(body_ids)}, "
        f"footnotes={len(fn_ids)}."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Body")
    lines.append("")

    section_emitted_footnotes = False
    for sid in body_ids + fn_ids:
        if sid in fn_ids and not section_emitted_footnotes:
            lines.append("---")
            lines.append("")
            lines.append("## Footnotes")
            lines.append("")
            section_emitted_footnotes = True
        a_seg = a.get(sid)
        b_seg = b.get(sid)
        # Use whichever side has the latin (should agree if both
        # present; if they disagree, prefer A and note the divergence).
        latin = ""
        if a_seg and a_seg.latin:
            latin = a_seg.latin
        elif b_seg and b_seg.latin:
            latin = b_seg.latin
        latin_disagreement = (
            a_seg is not None and b_seg is not None
            and a_seg.latin and b_seg.latin
            and a_seg.latin != b_seg.latin
        )

        lines.append(f"### `{sid}`")
        lines.append("")
        lines.append(f"- **Latin:** {latin or '_(missing)_'}")
        if latin_disagreement:
            lines.append(
                f"  - _note: {a_label} and {b_label} disagree on Latin "
                f"source for this segment_id._"
            )
        lines.append(
            f"- **{a_label}:** {a_seg.english if a_seg and a_seg.english else '_(missing)_'}"
        )
        lines.append(
            f"- **{b_label}:** {b_seg.english if b_seg and b_seg.english else '_(missing)_'}"
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True,
                        help="Path to side-A segments_with_translations.jsonl")
    parser.add_argument("--b", type=Path, required=True,
                        help="Path to side-B segments_with_translations.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--a-label", default="v0")
    parser.add_argument("--b-label", default="v2")
    parser.add_argument("--page", default=None,
                        help="Page label (default: derived from path)")
    args = parser.parse_args(argv)

    if not args.a.is_file():
        parser.error(f"--a not found: {args.a}")
    if not args.b.is_file():
        parser.error(f"--b not found: {args.b}")

    a = load_segments(args.a)
    b = load_segments(args.b)
    page = args.page or _infer_page(args.a) or _infer_page(args.b) or "page"

    md = render_markdown(
        a, b, page=page, a_label=args.a_label, b_label=args.b_label,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(
        f"ab_trilinear: page={page} {args.a_label}={len(a)} "
        f"{args.b_label}={len(b)} -> {args.output}"
    )
    return 0


def _infer_page(path: Path) -> str | None:
    """Walk parents looking for a directory like ``p0039``."""
    for parent in path.parents:
        name = parent.name
        if len(name) == 5 and name.startswith("p") and name[1:].isdigit():
            return name
    return None


if __name__ == "__main__":
    raise SystemExit(main())
