"""Chunked reference-based COMET scoring for Ussher's Annals sample.

This script scores the three Annals translation runs against the modernized
English gold sidecar:

    08_working_scratch/phase3b/annotations/annals_english/
    annals_english_parker_style.jsonl

The Latin and English editions do not share line IDs, and their line breaks
do not match. To avoid hand-aligning every line before getting a useful
metric, the script uses one completed machine run as a bridge:

1. Token-align the bridge run's English output to the modernized reference.
2. Map each Latin source line to an approximate English reference line.
3. Build ordered reference-sized chunks.
4. Score every run's concatenated chunk against the same Latin source chunk
   and modernized reference chunk using reference-based COMET-DA.

The generated chunk alignment is deliberately written to disk so it can be
reviewed and corrected later. Use ``--no-score`` to produce only the alignment
and summary without loading COMET.
"""

from __future__ import annotations

import argparse
import difflib
import json
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_DIR = (
    WORKSPACE_ROOT
    / "04_translation_work"
    / "ab"
    / "p0383_p0388"
    / "ussher_v5_annals"
)
DEFAULT_REFERENCE_JSONL = (
    WORKSPACE_ROOT
    / "08_working_scratch"
    / "phase3b"
    / "annotations"
    / "annals_english"
    / "annals_english_parker_style.jsonl"
)
DEFAULT_OUTPUT_PREFIX = DEFAULT_RUNS_DIR / "annals_chunked_comet"


@dataclass(frozen=True)
class RunSegment:
    segment_id: str
    line_id: str
    page_id: str
    seq: int
    latin: str
    english: str


@dataclass(frozen=True)
class ReferenceLine:
    page_id: str
    line_id: str
    text: str
    source_text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    latin_line_ids: list[str]
    segment_ids: list[str]
    reference_line_ids: list[str]
    latin_concat: str
    bridge_english_concat: str
    reference_concat: str
    latin_start_index: int
    latin_end_index: int
    reference_start_index: int
    reference_end_index: int

    def to_alignment_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "latin_line_ids": self.latin_line_ids,
            "segment_ids": self.segment_ids,
            "english_line_ids": self.reference_line_ids,
            "latin_concat": self.latin_concat,
            "bridge_english_concat": self.bridge_english_concat,
            "reference": self.reference_concat,
            "latin_start_index": self.latin_start_index,
            "latin_end_index": self.latin_end_index,
            "reference_start_index": self.reference_start_index,
            "reference_end_index": self.reference_end_index,
        }


def _english_for(record: dict) -> str:
    history = record.get("translation_history") or []
    if history:
        text = (history[-1] or {}).get("english") or ""
        if text.strip():
            return text
    return record.get("final_english") or ""


def segment_id_to_line_id(segment_id: str) -> str:
    return segment_id[4:] if segment_id.startswith("seg_") else segment_id


def load_run_segments(path: Path) -> list[RunSegment]:
    """Load a ``segments_with_translations.jsonl`` run in source order."""
    segments: list[RunSegment] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: malformed JSON on line {line_no}") from exc
            segment_id = str(record.get("segment_id") or "")
            if not segment_id:
                continue
            line_id = segment_id_to_line_id(segment_id)
            segments.append(
                RunSegment(
                    segment_id=segment_id,
                    line_id=line_id,
                    page_id=str(record.get("page_id") or ""),
                    seq=int(record.get("seq") or 0),
                    latin=str(record.get("latin_text") or ""),
                    english=_english_for(record),
                )
            )
    return segments


def load_reference_lines(
    path: Path,
    *,
    start_line_id: str,
    end_line_id: str | None,
    reference_field: str,
) -> list[ReferenceLine]:
    """Load sidecar reference rows from ``start_line_id`` through end."""
    out: list[ReferenceLine] = []
    started = False
    saw_start = False
    saw_end = False
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: malformed JSON on line {line_no}") from exc
            line_id = str(record.get("line_id") or "")
            if line_id == start_line_id:
                started = True
                saw_start = True
            if not started:
                continue
            text = (
                record.get(reference_field)
                or record.get("modernized")
                or record.get("source_text")
                or ""
            )
            out.append(
                ReferenceLine(
                    page_id=str(record.get("page_id") or ""),
                    line_id=line_id,
                    text=str(text),
                    source_text=str(record.get("source_text") or ""),
                )
            )
            if end_line_id and line_id == end_line_id:
                saw_end = True
                break
    if not saw_start:
        raise ValueError(f"reference start line not found: {start_line_id}")
    if end_line_id and not saw_end:
        raise ValueError(f"reference end line not found: {end_line_id}")
    return out


def normalize_tokens(text: str) -> list[str]:
    """Tokenize for rough cross-edition English alignment."""
    replacements = {
        "ſ": "s",
        "æ": "ae",
        "Æ": "Ae",
        "œ": "oe",
        "Œ": "Oe",
        "&": " and ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    normalized = unicodedata.normalize("NFKD", text)
    tokens: list[str] = []
    current: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category.startswith("M"):
            continue
        if category[0] in {"L", "N"}:
            current.append(char.lower())
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _token_stream(texts: Sequence[str]) -> tuple[list[str], list[int]]:
    tokens: list[str] = []
    line_for_token: list[int] = []
    for line_index, text in enumerate(texts):
        for token in normalize_tokens(text):
            tokens.append(token)
            line_for_token.append(line_index)
    return tokens, line_for_token


def map_bridge_to_reference(
    bridge_segments: Sequence[RunSegment],
    reference_lines: Sequence[ReferenceLine],
) -> tuple[list[int], list[int]]:
    """Map every bridge Latin line index to a reference line index.

    Returns ``(mapping, vote_counts)``. ``mapping[i]`` is the approximate
    reference-line index for bridge line ``i``. ``vote_counts[i]`` records how
    many token matches supported that line before interpolation.
    """
    bridge_tokens, bridge_line_for_token = _token_stream(
        [segment.english for segment in bridge_segments]
    )
    reference_tokens, reference_line_for_token = _token_stream(
        [line.text for line in reference_lines]
    )
    if not bridge_segments:
        return [], []
    if not reference_lines:
        return [0 for _ in bridge_segments], [0 for _ in bridge_segments]

    votes: list[Counter[int]] = [Counter() for _ in bridge_segments]
    matcher = difflib.SequenceMatcher(
        None, bridge_tokens, reference_tokens, autojunk=False
    )
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            bridge_line = bridge_line_for_token[block.a + offset]
            reference_line = reference_line_for_token[block.b + offset]
            votes[bridge_line][reference_line] += 1

    raw: list[float | None] = []
    vote_counts: list[int] = []
    for counter in votes:
        total = sum(counter.values())
        vote_counts.append(total)
        if total:
            raw.append(
                sum(reference_index * count for reference_index, count in counter.items())
                / total
            )
        else:
            raw.append(None)

    known = [index for index, value in enumerate(raw) if value is not None]
    if not known:
        return [0 for _ in bridge_segments], vote_counts

    filled: list[float] = [0.0 for _ in bridge_segments]
    for index, value in enumerate(raw):
        if value is not None:
            filled[index] = value
            continue
        prev_known = max((k for k in known if k < index), default=None)
        next_known = min((k for k in known if k > index), default=None)
        if prev_known is not None and next_known is not None:
            prev_val = raw[prev_known]
            next_val = raw[next_known]
            assert prev_val is not None and next_val is not None
            span = next_known - prev_known
            filled[index] = prev_val + (next_val - prev_val) * (
                (index - prev_known) / span
            )
        elif prev_known is not None:
            assert raw[prev_known] is not None
            filled[index] = float(raw[prev_known])
        else:
            assert next_known is not None and raw[next_known] is not None
            filled[index] = float(raw[next_known])

    mapping: list[int] = []
    last = 0
    max_reference = len(reference_lines) - 1
    for value in filled:
        mapped = max(last, min(max_reference, int(round(value))))
        mapping.append(mapped)
        last = mapped
    return mapping, vote_counts


def _join_nonempty(parts: Sequence[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip()).strip()


def build_chunks(
    bridge_segments: Sequence[RunSegment],
    reference_lines: Sequence[ReferenceLine],
    mapping: Sequence[int],
    *,
    chunk_ref_lines: int,
) -> list[Chunk]:
    """Build fixed-reference-window chunks using the bridge mapping."""
    if chunk_ref_lines < 1:
        raise ValueError("chunk_ref_lines must be >= 1")
    chunks: list[Chunk] = []
    if not bridge_segments or not reference_lines:
        return chunks
    for ref_start in range(0, len(reference_lines), chunk_ref_lines):
        ref_end = min(len(reference_lines) - 1, ref_start + chunk_ref_lines - 1)
        latin_indices = [
            index
            for index, ref_index in enumerate(mapping)
            if ref_start <= ref_index <= ref_end
        ]
        if not latin_indices:
            continue
        latin_start = min(latin_indices)
        latin_end = max(latin_indices)
        segment_slice = list(bridge_segments[latin_start : latin_end + 1])
        reference_slice = list(reference_lines[ref_start : ref_end + 1])
        chunk_number = len(chunks) + 1
        chunks.append(
            Chunk(
                chunk_id=f"annals_chunk_{chunk_number:03d}",
                latin_line_ids=[segment.line_id for segment in segment_slice],
                segment_ids=[segment.segment_id for segment in segment_slice],
                reference_line_ids=[line.line_id for line in reference_slice],
                latin_concat=_join_nonempty([segment.latin for segment in segment_slice]),
                bridge_english_concat=_join_nonempty(
                    [segment.english for segment in segment_slice]
                ),
                reference_concat=_join_nonempty([line.text for line in reference_slice]),
                latin_start_index=latin_start,
                latin_end_index=latin_end,
                reference_start_index=ref_start,
                reference_end_index=ref_end,
            )
        )
    return chunks


def machine_text_for_chunk(
    segments: Sequence[RunSegment],
    latin_line_ids: Sequence[str],
) -> str:
    by_line_id = {segment.line_id: segment for segment in segments}
    return _join_nonempty(
        [by_line_id[line_id].english for line_id in latin_line_ids if line_id in by_line_id]
    )


def build_score_rows(
    *,
    chunks: Sequence[Chunk],
    runs: dict[str, list[RunSegment]],
) -> list[dict]:
    rows: list[dict] = []
    for chunk in chunks:
        for run_tag, segments in runs.items():
            machine = machine_text_for_chunk(segments, chunk.latin_line_ids)
            error = ""
            if not machine.strip():
                error = "missing machine text"
            if not chunk.latin_concat.strip():
                error = "missing latin source"
            if not chunk.reference_concat.strip():
                error = "missing reference"
            rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "run": run_tag,
                    "latin_line_ids": chunk.latin_line_ids,
                    "segment_ids": chunk.segment_ids,
                    "english_line_ids": chunk.reference_line_ids,
                    "latin": chunk.latin_concat,
                    "machine": machine,
                    "reference": chunk.reference_concat,
                    "score": None,
                    "error": error,
                }
            )
    return rows


def score_rows_with_comet(
    rows: list[dict],
    *,
    model_name: str,
    batch_size: int,
    gpus: int,
) -> list[dict]:
    from comet import download_model, load_from_checkpoint  # type: ignore

    runnable = [
        row
        for row in rows
        if not row.get("error")
        and str(row.get("latin") or "").strip()
        and str(row.get("machine") or "").strip()
        and str(row.get("reference") or "").strip()
    ]
    if not runnable:
        return rows

    model_path = download_model(model_name)
    model = load_from_checkpoint(model_path)
    payloads = [
        {
            "src": row["latin"],
            "mt": row["machine"],
            "ref": row["reference"],
        }
        for row in runnable
    ]
    output = model.predict(payloads, batch_size=batch_size, gpus=gpus)
    scores = list(output.scores) if hasattr(output, "scores") else list(output)
    for row, score in zip(runnable, scores):
        row["score"] = float(score)
    return rows


def summarize_scores(
    rows: Sequence[dict],
    *,
    chunks: Sequence[Chunk],
    model: str,
    no_score: bool,
) -> dict:
    if no_score:
        pending_by_run: dict[str, int] = {}
        for row in rows:
            run = str(row.get("run") or "")
            pending_by_run[run] = pending_by_run.get(run, 0) + 1
        return {
            "model": model,
            "reference_based": True,
            "no_score": True,
            "n_chunks": len(chunks),
            "n_rows": len(rows),
            "run_summaries": {
                run: {
                    "n_scored": 0,
                    "n_errored": 0,
                    "n_pending": count,
                    "mean": None,
                    "median": None,
                    "min": None,
                    "max": None,
                }
                for run, count in sorted(pending_by_run.items())
            },
            "chunk_winners": {},
            "best_mean_run": None,
        }

    by_run: dict[str, list[float]] = {}
    errors_by_run: dict[str, int] = {}
    for row in rows:
        run = str(row.get("run") or "")
        if row.get("score") is None:
            errors_by_run[run] = errors_by_run.get(run, 0) + 1
            continue
        by_run.setdefault(run, []).append(float(row["score"]))

    run_summaries: dict[str, dict] = {}
    for run in sorted(set(by_run) | set(errors_by_run)):
        scores = by_run.get(run, [])
        run_summaries[run] = {
            "n_scored": len(scores),
            "n_errored": errors_by_run.get(run, 0),
            "mean": statistics.mean(scores) if scores else None,
            "median": statistics.median(scores) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        }

    chunk_winners: dict[str, int] = {}
    for chunk in chunks:
        candidates = [
            row
            for row in rows
            if row.get("chunk_id") == chunk.chunk_id and row.get("score") is not None
        ]
        if not candidates:
            continue
        best = max(float(row["score"]) for row in candidates)
        winners = [row for row in candidates if float(row["score"]) == best]
        if len(winners) == 1:
            run = str(winners[0].get("run") or "")
            chunk_winners[run] = chunk_winners.get(run, 0) + 1
        else:
            chunk_winners["tie"] = chunk_winners.get("tie", 0) + 1

    best_mean_run = None
    scored_runs = {
        run: summary["mean"]
        for run, summary in run_summaries.items()
        if summary["mean"] is not None
    }
    if scored_runs:
        best_mean_run = max(scored_runs, key=lambda run: scored_runs[run])

    return {
        "model": model,
        "reference_based": True,
        "no_score": no_score,
        "n_chunks": len(chunks),
        "n_rows": len(rows),
        "run_summaries": run_summaries,
        "chunk_winners": chunk_winners,
        "best_mean_run": best_mean_run,
    }


def write_jsonl(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chunked reference-based COMET scoring for Annals runs."
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument(
        "--run-tags", nargs="+", default=["run01", "run02", "run03"]
    )
    parser.add_argument("--bridge-run", default="run01")
    parser.add_argument("--reference-jsonl", type=Path, default=DEFAULT_REFERENCE_JSONL)
    parser.add_argument("--reference-field", default="modernized")
    parser.add_argument("--reference-start-line", default="p0695_body_l0027")
    parser.add_argument("--reference-end-line", default="p0699_body_l0037")
    parser.add_argument("--chunk-ref-lines", type=int, default=8)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument("--model", default="Unbabel/wmt22-comet-da")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gpus", type=int, default=0)
    parser.add_argument(
        "--no-score",
        action="store_true",
        help="Write chunk alignment and score rows without loading COMET.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.bridge_run not in args.run_tags:
        print(
            f"bridge run {args.bridge_run!r} must be included in --run-tags",
            file=sys.stderr,
        )
        return 2

    runs: dict[str, list[RunSegment]] = {}
    for run_tag in args.run_tags:
        path = args.runs_dir / run_tag / "segments_with_translations.jsonl"
        if not path.exists():
            print(f"run artifact not found: {path}", file=sys.stderr)
            return 2
        runs[run_tag] = load_run_segments(path)

    if not args.reference_jsonl.exists():
        print(f"reference JSONL not found: {args.reference_jsonl}", file=sys.stderr)
        return 2
    reference_lines = load_reference_lines(
        args.reference_jsonl,
        start_line_id=args.reference_start_line,
        end_line_id=args.reference_end_line,
        reference_field=args.reference_field,
    )

    bridge_segments = runs[args.bridge_run]
    mapping, vote_counts = map_bridge_to_reference(bridge_segments, reference_lines)
    chunks = build_chunks(
        bridge_segments,
        reference_lines,
        mapping,
        chunk_ref_lines=args.chunk_ref_lines,
    )
    rows = build_score_rows(chunks=chunks, runs=runs)
    if not args.no_score:
        rows = score_rows_with_comet(
            rows,
            model_name=args.model,
            batch_size=args.batch_size,
            gpus=args.gpus,
        )

    alignment_rows = []
    for chunk in chunks:
        alignment = chunk.to_alignment_dict()
        alignment["bridge_run"] = args.bridge_run
        alignment["reference_field"] = args.reference_field
        alignment_rows.append(alignment)

    alignment_path = args.output_prefix.with_name(
        args.output_prefix.name + "_alignment.jsonl"
    )
    scores_path = args.output_prefix.with_name(args.output_prefix.name + "_scores.jsonl")
    summary_path = args.output_prefix.with_name(
        args.output_prefix.name + "_summary.json"
    )
    write_jsonl(alignment_path, alignment_rows)
    write_jsonl(scores_path, rows)
    summary = summarize_scores(
        rows, chunks=chunks, model=args.model, no_score=args.no_score
    )
    summary.update(
        {
            "runs_dir": str(args.runs_dir),
            "run_tags": args.run_tags,
            "bridge_run": args.bridge_run,
            "reference_jsonl": str(args.reference_jsonl),
            "reference_field": args.reference_field,
            "reference_start_line": args.reference_start_line,
            "reference_end_line": args.reference_end_line,
            "chunk_ref_lines": args.chunk_ref_lines,
            "alignment_path": str(alignment_path),
            "scores_path": str(scores_path),
            "summary_path": str(summary_path),
            "bridge_mapping_vote_counts": {
                "n_lines": len(vote_counts),
                "n_without_votes": sum(1 for count in vote_counts if count == 0),
                "mean_votes": statistics.mean(vote_counts) if vote_counts else 0,
            },
        }
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"annals_chunked_comet_score: chunks={len(chunks)} "
        f"rows={len(rows)} no_score={args.no_score}"
    )
    print(f"alignment: {alignment_path}")
    print(f"scores:    {scores_path}")
    print(f"summary:   {summary_path}")
    if not args.no_score:
        for run_tag, run_summary in summary["run_summaries"].items():
            mean = run_summary["mean"]
            mean_text = f"{mean:.4f}" if mean is not None else "n/a"
            print(
                f"{run_tag}: mean={mean_text} "
                f"scored={run_summary['n_scored']} "
                f"errors={run_summary['n_errored']}"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "Chunk",
    "ReferenceLine",
    "RunSegment",
    "build_chunks",
    "build_score_rows",
    "load_reference_lines",
    "load_run_segments",
    "map_bridge_to_reference",
    "machine_text_for_chunk",
    "normalize_tokens",
    "score_rows_with_comet",
    "segment_id_to_line_id",
    "summarize_scores",
]
