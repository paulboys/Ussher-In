"""Align H. Kendra Baker's 1930 English translation of Antiquitates ch. 2
to the sentence-level machine translation units.

Baker ("Glastonbury Traditions concerning Joseph of Arimathea", Covenant
Publishing, 1930) is the only published extended English rendering of any
part of the Antiquitates — it covers exactly chapter 2, and the translator's
note declares it "intended to be literal rather than free". That makes it
the one human reference against which the machine translation can be scored
with reference-based COMET rather than a reference-free estimate.

Inputs
------
- ``01_raw_ocr_output/baker_english/page_NNN_raw.txt`` — per-page text
  extracted from the HathiTrust scans' Google OCR layer (pages 13–52 are
  the translation proper).
- ``03_segmented_text/part1/segments_sentences_xpage.jsonl`` — the ch2
  sentence units (pages p0046–p0068).

Outputs (under ``04_translation_work/ab/antiquitates_ch2/baker_benchmark/``)
------
- ``baker_stitched.txt`` — the cleaned, continuous Baker body text.
- ``baker_alignment.jsonl`` — one record per machine unit:
  ``{unit_id, latin, mt_english, baker_ref, similarity, baker_sentences}``.
  Units with no plausible Baker counterpart carry ``baker_ref: ""`` and are
  excluded from scoring (e.g. the chapter argumentum, which Baker replaced
  with his own book heading).

Method
------
Monotonic dynamic-programming alignment: machine units in order, Baker
sentences in order, each unit consuming a contiguous span of 0..MAX_SPAN
Baker sentences. Span similarity is content-word Jaccard weighted by
length balance — cheap, robust to translation variance, and biased by
nothing except word overlap. The alignment artifact is written for human
review; scoring happens separately (``baker_score.py``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
WORKSPACE = _HERE.parent.parent
BAKER_DIR = WORKSPACE / "01_raw_ocr_output" / "baker_english"
SEGMENTS = WORKSPACE / "03_segmented_text" / "part1" / "segments_sentences_xpage.jsonl"
OUT_DIR = WORKSPACE / "04_translation_work" / "ab" / "antiquitates_ch2" / "baker_benchmark"

TRANSLATION_PAGES = range(13, 53)  # pages 013-052 hold the translation
CH2_PAGE_RANGE = (46, 68)
MAX_SPAN = 24  # a long Ussher sentence can spread over many Baker sentences

# A footnote line at a page bottom: a single marker letter, then a citation.
_FOOTNOTE_LINE = re.compile(r"^[a-z]\s+[A-Z“”\"'(]")
_PAGE_NO = re.compile(r"^\s*\d{1,3}\s*$")
_NOISE_LINE = re.compile(r'^\s*["“”<>\'‘’]{1,3}\s*$')

_ABBREV = {
    "st", "mr", "mrs", "dr", "revd", "rev", "cap", "lib", "vol", "ch",
    "chap", "viz", "cf", "vid", "no", "eccl", "hist", "specul", "i.e",
    "e.g", "a.d", "b.c",
}


def _clean_page(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    # Strip trailing page number.
    while lines and _PAGE_NO.match(lines[-1]):
        lines.pop()
    # Strip the contiguous footnote block at the bottom.
    while lines and _FOOTNOTE_LINE.match(lines[-1].strip()):
        lines.pop()
    # Drop OCR noise lines anywhere.
    lines = [ln for ln in lines if not _NOISE_LINE.match(ln)]
    return "\n".join(lines)


def stitch(pages=TRANSLATION_PAGES) -> str:
    """Concatenate cleaned pages, joining hyphenated line breaks."""
    chunks: list[str] = []
    for n in pages:
        p = BAKER_DIR / f"page_{n:03d}_raw.txt"
        if not p.exists():
            continue
        chunks.append(_clean_page(p.read_text(encoding="utf-8")))
    text = "\n".join(chunks)
    # Re-join words split by end-of-line hyphenation ("be-\nlievers").
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Newlines to spaces; collapse runs.
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    # Detach OCR-fused punctuation spacing (" ," -> ",").
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Abbreviation-aware sentence split for Baker's English."""
    out: list[str] = []
    buf: list[str] = []
    # Split after terminal punctuation, INCLUDING when it is wrapped in a
    # closing quote ('...Glaston."'). Without the quote-aware branch, every
    # quotation-final sentence fuses with its successor — and Baker (like
    # Ussher) is quotation-dense, so whole passages merged into
    # mega-sentences and derailed the alignment around p0046.
    tokens = re.split(r"(?<=[.!?][\"'”’])\s+|(?<=[.!?])\s+", text)
    for tok in tokens:
        buf.append(tok)
        last_word = re.findall(r"[\w.]+$", tok.rstrip(".!?").lower())
        last = last_word[-1].strip(".") if last_word else ""
        # Don't break after a known abbreviation ("Lib.", "cap.", "St.").
        if last in _ABBREV:
            continue
        out.append(" ".join(buf).strip())
        buf = []
    if buf:
        out.append(" ".join(buf).strip())
    return [s for s in out if s]


_WORD = re.compile(r"[a-zà-ÿ]{3,}")
_STOP = {
    "the", "and", "that", "was", "his", "with", "for", "which", "this",
    "not", "are", "but", "have", "had", "from", "they", "were", "been",
    "their", "them", "also", "who", "him", "her", "she", "you", "all",
    "one", "out", "into", "when", "then", "there", "these", "those",
}


def _content_words(s: str) -> set[str]:
    return {w for w in _WORD.findall(s.lower()) if w not in _STOP}


def _sim(mt: str, ref_words_list: list[set[str]], j0: int, j1: int,
         mt_words: set[str]) -> float:
    """Jaccard of content words between the MT unit and Baker span [j0:j1)."""
    ref_words: set[str] = set()
    for j in range(j0, j1):
        ref_words |= ref_words_list[j]
    if not mt_words or not ref_words:
        return 0.0
    inter = len(mt_words & ref_words)
    union = len(mt_words | ref_words)
    jac = inter / union
    # Mild length-balance factor so a huge span can't win on vocabulary alone.
    balance = min(len(mt_words), len(ref_words)) / max(len(mt_words), len(ref_words))
    return jac * (0.5 + 0.5 * balance)


def align(units: list[dict], baker_sents: list[str]) -> list[dict]:
    """Monotonic DP: each unit takes a contiguous (possibly empty) span."""
    n, m = len(units), len(baker_sents)
    mt_words = [_content_words(u["mt_english"]) for u in units]
    ref_words = [_content_words(s) for s in baker_sents]

    NEG = float("-inf")
    # score[i][j]: best total using first i units and first j baker sentences.
    score = [[NEG] * (m + 1) for _ in range(n + 1)]
    back: dict[tuple[int, int], tuple[int, int]] = {}
    score[0][0] = 0.0
    SKIP_PENALTY = -0.05  # a unit with no counterpart costs a little

    for i in range(n):
        for j in range(m + 1):
            cur = score[i][j]
            if cur == NEG:
                continue
            # Unit i unaligned.
            if cur + SKIP_PENALTY > score[i + 1][j]:
                score[i + 1][j] = cur + SKIP_PENALTY
                back[(i + 1, j)] = (i, j)
            # Unit i takes span [j:k).
            for k in range(j + 1, min(j + MAX_SPAN, m) + 1):
                s = cur + _sim(units[i]["mt_english"], ref_words, j, k,
                               mt_words[i])
                if s > score[i + 1][k]:
                    score[i + 1][k] = s
                    back[(i + 1, k)] = (i, j)

    # Best end state: allow trailing Baker sentences to go unused.
    end_j = max(range(m + 1), key=lambda j: score[n][j])
    # Walk back.
    spans: dict[int, tuple[int, int]] = {}
    i, j = n, end_j
    while (i, j) in back:
        pi, pj = back[(i, j)]
        spans[pi] = (pj, j)
        i, j = pi, pj

    out: list[dict] = []
    for idx, u in enumerate(units):
        j0, j1 = spans.get(idx, (0, 0))
        span_sents = baker_sents[j0:j1]
        ref = " ".join(span_sents).strip()
        sim = _sim(u["mt_english"], ref_words, j0, j1, mt_words[idx]) if span_sents else 0.0
        out.append({
            "unit_id": u["unit_id"],
            "latin": u["latin"],
            "mt_english": u["mt_english"],
            "baker_ref": ref,
            "similarity": round(sim, 4),
            "baker_sentences": j1 - j0,
        })
    return out


def load_units() -> list[dict]:
    lo, hi = CH2_PAGE_RANGE
    units: list[dict] = []
    for line in SEGMENTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("segment_type") == "footnote":
            continue
        m = re.search(r"p(\d+)", r.get("page_id") or "")
        if not m or not (lo <= int(m.group(1)) <= hi):
            continue
        hist = r.get("translation_history") or [{}]
        eng = (hist[-1] or {}).get("english") or ""
        # Carets are metadata; keep them out of alignment and scoring.
        strip = lambda s: re.sub(r"\^[A-Za-z0-9]{1,2}", "", s or "")
        units.append({
            "unit_id": r["segment_id"],
            "latin": strip(r.get("latin_text") or ""),
            "mt_english": strip(eng),
        })
    return units


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Align Baker 1930 to ch2 units.")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    text = stitch()
    sents = split_sentences(text)
    units = load_units()
    print(f"Baker: {len(text)} chars, {len(sents)} sentences; "
          f"machine units: {len(units)}")

    aligned = align(units, sents)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "baker_stitched.txt").write_text(text, encoding="utf-8")
    with (args.out_dir / "baker_alignment.jsonl").open("w", encoding="utf-8") as fh:
        for rec in aligned:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    unaligned = [a for a in aligned if not a["baker_ref"]]
    weak = [a for a in aligned if a["baker_ref"] and a["similarity"] < 0.15]
    print(f"Aligned {len(aligned) - len(unaligned)}/{len(aligned)} units "
          f"({len(weak)} weak, sim<0.15)")
    for a in unaligned:
        print(f"  UNALIGNED: {a['unit_id']}")
    for a in weak:
        print(f"  WEAK {a['similarity']:.2f}: {a['unit_id']}")
    print(f"Wrote {args.out_dir / 'baker_alignment.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
