"""Profile pages by Greek density, ecclesiastical/juridical Latin
vocabulary hits, footnote density, and current literal-pass uncertain
rate, to support data-driven pilot-page selection.

Sources, in order of preference per page:

1. ``03_segmented_text/<part>/segments_with_translations.jsonl`` — gives
   segment counts, footnote counts, and the latest-stage ``uncertain``
   flag per body segment. Greek and juridical hits are computed from
   ``latin_text`` joined across body + footnote segments.
2. ``01_raw_ocr_output/<part>/page_NNNN_raw.txt`` — fallback for pages
   that have OCR but are not yet segmented. Greek and juridical hits
   only; segment/footnote/uncertain columns are blank.

Output: CSV ranked by a composite "interest" score that mildly favors
pages that are both Greek-heavy *and* juridical-heavy, with a bump for
high uncertain rate. The score is a heuristic; the per-column metrics
are the actually useful signal — sort the CSV however you prefer.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

_GREEK_RANGE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")

# Stem-prefix matcher for ecclesiastical / juridical / liturgical Latin.
# Each entry matches \b<stem>\w* (case-insensitive) so inflections are
# captured cheaply without a lemmatizer. The list intentionally favors
# precision over recall — common-or-classical stems (e.g. "sanct") are
# excluded to keep the signal discriminating.
_ECCL_JURID_STEMS = (
    # ecclesiastical office / structure
    "ecclesi", "episcop", "presbyter", "diacon", "archidiacon",
    "archiepiscop", "metropolit", "patriarch", "primat", "pontif",
    "abbat", "monach", "monaster", "coenob", "eremit", "anachoret",
    "suffragan", "decan",
    # councils / canon law / decrees
    "synod", "concili", "canon", "decret", "constitut", "edict",
    "statut", "capitul", "rubric",
    # liturgy / sacraments
    "liturg", "sacrament", "baptism", "chrism", "chrismat",
    "eucharist", "vesper", "matutin", "communic",
    # juridical vocabulary
    "legat", "vicari", "palli", "immunit", "benefic", "prebend",
    "simon", "anathemat", "excommunicat", "censur", "indulgent",
    "dispensat", "jurisdict", "exemption",
    # related (martyrology, paschal, charters)
    "martyr", "hagi", "paschal", "codex",
)

_JURID_RE = re.compile(
    r"\b(?:" + "|".join(_ECCL_JURID_STEMS) + r")\w*",
    re.IGNORECASE,
)


@dataclass
class PageMetrics:
    page_id: str
    source: str  # "segments" | "raw_ocr"
    char_count: int = 0
    greek_chars: int = 0
    greek_ratio: float = 0.0
    juridical_hits: int = 0
    juridical_per_kchar: float = 0.0
    body_segment_count: int = 0
    footnote_segment_count: int = 0
    uncertain_body_count: int = 0
    uncertain_rate: float = 0.0
    score: float = 0.0
    sample_juridical_terms: str = ""

    def to_csv_row(self) -> dict:
        return asdict(self)


def _count_metrics(text: str) -> tuple[int, int, int, list[str]]:
    """Return (char_count, greek_chars, juridical_hits, sample_terms)."""
    char_count = sum(1 for ch in text if not ch.isspace())
    greek_chars = len(_GREEK_RANGE.findall(text))
    matches = _JURID_RE.findall(text)
    juridical_hits = len(matches)
    # Deduplicate while preserving order; keep up to 6 examples.
    seen: list[str] = []
    seen_set: set[str] = set()
    for m in matches:
        key = m.lower()
        if key not in seen_set:
            seen_set.add(key)
            seen.append(m)
        if len(seen) >= 6:
            break
    return char_count, greek_chars, juridical_hits, seen


def _latest_history_entry(seg: dict) -> dict | None:
    history = seg.get("translation_history") or []
    if not history:
        return None
    return history[-1]


def _profile_from_segments(
    segments_path: Path,
) -> dict[str, PageMetrics]:
    """Aggregate per-page metrics from a segments JSONL file."""
    pages: dict[str, PageMetrics] = {}
    text_buckets: dict[str, list[str]] = {}

    with segments_path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                seg = json.loads(line)
            except json.JSONDecodeError as exc:
                print(
                    f"warning: {segments_path}:{line_no} skipped "
                    f"(invalid JSON: {exc})",
                    file=sys.stderr,
                )
                continue

            page_id = seg.get("page_id") or "(unknown)"
            seg_type = seg.get("segment_type") or ""
            metrics = pages.setdefault(
                page_id,
                PageMetrics(page_id=page_id, source="segments"),
            )
            text_buckets.setdefault(page_id, []).append(
                seg.get("latin_text") or ""
            )

            if seg_type == "body":
                metrics.body_segment_count += 1
                last = _latest_history_entry(seg)
                if last and last.get("uncertain"):
                    metrics.uncertain_body_count += 1
            elif seg_type in ("footnote", "fn"):
                metrics.footnote_segment_count += 1

    for page_id, metrics in pages.items():
        text = "\n".join(text_buckets.get(page_id, []))
        char_count, greek, jurid, sample = _count_metrics(text)
        metrics.char_count = char_count
        metrics.greek_chars = greek
        metrics.greek_ratio = (greek / char_count) if char_count else 0.0
        metrics.juridical_hits = jurid
        metrics.juridical_per_kchar = (
            (jurid * 1000.0 / char_count) if char_count else 0.0
        )
        metrics.sample_juridical_terms = ", ".join(sample)
        if metrics.body_segment_count:
            metrics.uncertain_rate = (
                metrics.uncertain_body_count / metrics.body_segment_count
            )

    return pages


_PAGE_FILE_RE = re.compile(r"page_(\d{4})_raw\.txt$", re.IGNORECASE)


def _profile_from_raw_ocr(
    raw_ocr_dir: Path,
    skip_page_ids: Iterable[str] = (),
) -> dict[str, PageMetrics]:
    """Aggregate per-page metrics from raw OCR text files."""
    skip = set(skip_page_ids)
    pages: dict[str, PageMetrics] = {}
    if not raw_ocr_dir.is_dir():
        return pages
    for path in sorted(raw_ocr_dir.iterdir()):
        match = _PAGE_FILE_RE.search(path.name)
        if not match:
            continue
        page_id = f"p{match.group(1)}"
        if page_id in skip:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(
                f"warning: cannot read {path}: {exc}",
                file=sys.stderr,
            )
            continue
        char_count, greek, jurid, sample = _count_metrics(text)
        metrics = PageMetrics(
            page_id=page_id,
            source="raw_ocr",
            char_count=char_count,
            greek_chars=greek,
            greek_ratio=(greek / char_count) if char_count else 0.0,
            juridical_hits=jurid,
            juridical_per_kchar=(
                (jurid * 1000.0 / char_count) if char_count else 0.0
            ),
            sample_juridical_terms=", ".join(sample),
        )
        pages[page_id] = metrics
    return pages


def _compute_score(metrics: PageMetrics) -> float:
    """Composite interest score for ranking.

    Rewards:
    - Greek density (ratio, not raw count) — pages with any meaningful
      Greek content are scarcer than juridical-Latin pages.
    - Juridical-Latin density per 1000 chars.
    - Bonus for hitting both signals at once (multiplicative term).
    - Empirical bump from current uncertain rate (only meaningful when
      the page is segmented and has been translated).
    """
    greek_term = metrics.greek_ratio * 100.0          # 0–100ish
    jurid_term = metrics.juridical_per_kchar          # typically 0–10
    both_term = greek_term * jurid_term * 0.05        # rewards overlap
    uncertain_term = metrics.uncertain_rate * 5.0     # 0–5
    return greek_term + jurid_term + both_term + uncertain_term


def profile_part(
    *,
    part: str,
    segments_file: Path | None,
    raw_ocr_dir: Path | None,
) -> list[PageMetrics]:
    """Profile every page available for *part* under the given sources."""
    pages: dict[str, PageMetrics] = {}
    if segments_file and segments_file.is_file():
        pages.update(_profile_from_segments(segments_file))
    if raw_ocr_dir and raw_ocr_dir.is_dir():
        # raw OCR fills gaps only — segment-derived metrics win where both exist.
        pages_from_ocr = _profile_from_raw_ocr(
            raw_ocr_dir, skip_page_ids=pages.keys()
        )
        pages.update(pages_from_ocr)

    metrics_list = list(pages.values())
    for metrics in metrics_list:
        metrics.score = _compute_score(metrics)
    metrics_list.sort(key=lambda m: m.score, reverse=True)
    return metrics_list


def write_csv(metrics_list: list[PageMetrics], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(PageMetrics(page_id="", source="").to_csv_row().keys())
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for metrics in metrics_list:
            row = metrics.to_csv_row()
            # Round floats for readability.
            for key in (
                "greek_ratio",
                "juridical_per_kchar",
                "uncertain_rate",
                "score",
            ):
                if isinstance(row.get(key), float):
                    row[key] = round(row[key], 4)
            writer.writerow(row)


def print_top(metrics_list: list[PageMetrics], top: int) -> None:
    if not metrics_list:
        print("(no pages profiled)")
        return
    cols = (
        ("page", 8),
        ("source", 10),
        ("chars", 7),
        ("grk%", 6),
        ("jurid", 6),
        ("j/1k", 7),
        ("body", 5),
        ("fn", 4),
        ("unc%", 6),
        ("score", 7),
    )
    header = " ".join(f"{name:<{width}}" for name, width in cols)
    print(header)
    print("-" * len(header))
    for metrics in metrics_list[:top]:
        row = (
            f"{metrics.page_id:<8}"
            f" {metrics.source:<10}"
            f" {metrics.char_count:<7}"
            f" {metrics.greek_ratio*100:<6.2f}"
            f" {metrics.juridical_hits:<6}"
            f" {metrics.juridical_per_kchar:<7.2f}"
            f" {metrics.body_segment_count:<5}"
            f" {metrics.footnote_segment_count:<4}"
            f" {metrics.uncertain_rate*100:<6.1f}"
            f" {metrics.score:<7.2f}"
        )
        print(row)
        if metrics.sample_juridical_terms:
            print(f"           terms: {metrics.sample_juridical_terms}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Profile pages by Greek density, ecclesiastical/juridical "
            "Latin density, footnote count, and current uncertain rate."
        )
    )
    parser.add_argument(
        "--part",
        default="part1",
        help="Part folder name under 03_segmented_text/ (default: part1)",
    )
    parser.add_argument(
        "--segments-file",
        type=Path,
        default=None,
        help=(
            "Path to segments_with_translations.jsonl. "
            "Default: <repo>/03_segmented_text/<part>/segments_with_translations.jsonl"
        ),
    )
    parser.add_argument(
        "--raw-ocr-dir",
        type=Path,
        default=None,
        help=(
            "Directory of page_NNNN_raw.txt files. "
            "Default: <repo>/01_raw_ocr_output/<part>"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "CSV output path. Default: <repo>/08_working_scratch/"
            "page_profile_<part>.csv"
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="How many top-ranked pages to print to stdout (default: 20).",
    )
    args = parser.parse_args(argv)

    segments_file = args.segments_file or (
        REPO_ROOT
        / "03_segmented_text"
        / args.part
        / "segments_with_translations.jsonl"
    )
    raw_ocr_dir = args.raw_ocr_dir or (
        REPO_ROOT / "01_raw_ocr_output" / args.part
    )
    out_path = args.out or (
        REPO_ROOT
        / "08_working_scratch"
        / f"page_profile_{args.part}.csv"
    )

    metrics_list = profile_part(
        part=args.part,
        segments_file=segments_file,
        raw_ocr_dir=raw_ocr_dir,
    )

    if not metrics_list:
        print(
            f"No pages found. Looked at:\n"
            f"  segments: {segments_file}\n"
            f"  raw OCR : {raw_ocr_dir}",
            file=sys.stderr,
        )
        return 1

    write_csv(metrics_list, out_path)
    print(f"Profiled {len(metrics_list)} page(s); wrote {out_path}")
    print()
    print_top(metrics_list, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
