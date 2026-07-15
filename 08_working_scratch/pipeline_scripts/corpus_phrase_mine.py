"""Mine the Latin corpus for frequent words and phrases.

Discovery half of the neuro-symbolic loop: this surfaces recurring words
and multi-word units so a human (the classicist) can decide which need
consistency rules. Those rules become entries in ``glossary_ussher.jsonl``,
which ``glossary_validate.py`` then enforces. This script writes only a
reviewable candidate report — it never decides anything.

Deliberately surface-form (no lemmatizer): a human reviews the output, and
inflected variants (``ecclesiae Britannicae`` / ``ecclesiam Britannicam``)
are sorted ADJACENT via a rough "loose key" so the reviewer merges a cluster
at a glance, without the tool risking false merges from a classical-Latin
lemmatizer on Neo-Latin vocabulary.

Method
------
- Normalize: lowercase, ligatures (æ->ae, œ->oe), strip footnote carets,
  split the enclitic ``-que`` (with the standard non-enclitic exceptions).
- Clause-chunk on punctuation; generate 2..MAXN word n-grams within a chunk
  only (so phrases don't span clause breaks), stopword-trimmed at both ends.
- Words: frequency + a likely-proper-noun flag (capitalized when not
  sentence-initial).
- Phrases: raw count + Dunning log-likelihood (bigrams) + maximal-repeat
  dedup (drop an n-gram wholly explained by a longer one of equal count).

Outputs (default 09_analysis/phrase_mining/)
------
- ``words.tsv``   : word, count, pct, proper?, loose_key
- ``phrases.tsv`` : phrase, n, count, loglik, pages, proper?, example, loose_key
- ``report.md``   : top-N of each for eyeballing, with corpus stats

Usage
-----
    python corpus_phrase_mine.py                       # p0032-p0567, body+marg
    python corpus_phrase_mine.py --start-page 32 --end-page 68 --min-count 2
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
WORKSPACE = _HERE.parent.parent
ANNOT_DIR = WORKSPACE / "08_working_scratch" / "phase3b" / "annotations"
DEFAULT_OUT = WORKSPACE / "09_analysis" / "phrase_mining"

MAXN = 6  # longest phrase to mine

# Latin function words: no phrase may begin or end on one, and they are
# excluded from the word-frequency table. Not exhaustive — extend as the
# classicist flags additions.
STOPWORDS = {
    # coordinators / particles
    "et", "ac", "atque", "aut", "vel", "nec", "neque", "sed", "que", "ve",
    "enim", "autem", "vero", "igitur", "ergo", "tamen", "quoque", "etiam",
    "quidem", "nam", "namque", "itaque", "adeo", "scilicet", "nempe",
    # subordinators
    "ut", "uti", "ne", "si", "nisi", "quia", "quod", "quoniam", "quum",
    "cum", "dum", "donec", "quamvis", "quamquam", "licet", "postquam",
    "antequam", "priusquam", "ubi", "unde", "quando", "quatenus",
    # prepositions
    "in", "ad", "de", "ex", "e", "a", "ab", "abs", "per", "pro", "prae",
    "sub", "super", "ante", "post", "sine", "cum", "apud", "contra",
    "inter", "circa", "circum", "erga", "extra", "intra", "iuxta", "juxta",
    "penes", "propter", "trans", "ultra", "versus", "coram", "tenus",
    "secundum", "supra", "infra", "usque", "ob",
    # pronouns / determiners (high-frequency, low content)
    "qui", "quae", "quod", "quem", "quam", "quo", "qua", "quos", "quas",
    "cuius", "cui", "quibus", "quorum", "quarum", "quibusdam",
    "hic", "haec", "hoc", "huius", "huic", "hunc", "hanc", "hac", "his",
    "hae", "hos", "has", "horum", "harum",
    "ille", "illa", "illud", "illius", "illi", "illum", "illam", "illo",
    "illos", "illas", "illorum", "illarum",
    "is", "ea", "id", "eius", "ei", "eum", "eam", "eo", "eorum", "earum",
    "iis", "eis", "eos", "eas",
    "ipse", "ipsa", "ipsum", "ipsius", "ipsi", "ipso", "ipsam", "ipsos",
    "idem", "eadem", "eodem", "eundem", "eiusdem", "ejusdem",
    "iste", "ista", "istud", "se", "sui", "sibi", "sese",
    "suus", "sua", "suum", "suis", "sui", "suam", "suo", "suorum",
    "meus", "mea", "tuus", "noster", "nostra", "nostri", "nostrae",
    "vester", "quidam", "quaedam", "quoddam", "quisque", "quaeque",
    "aliquis", "aliqua", "aliquod", "quisquam", "nullus", "nulla",
    "totus", "tota", "unus", "una", "unum", "duo", "tres",
    # esse + common auxiliaries / high-freq verbs of low content
    "est", "sunt", "esse", "erat", "erant", "fuit", "fuerat", "fuisse",
    "sit", "sint", "esset", "essent", "fuerit", "fuisset", "fore", "sum",
    "es", "eram", "ero", "sis", "estne", "fuerunt", "fuere",
    # adverbs / misc high-frequency
    "non", "iam", "jam", "nunc", "tunc", "tum", "sic", "ita", "tam",
    "magis", "minus", "valde", "satis", "modo", "vix", "fere", "paene",
    "pene", "adhuc", "semper", "saepe", "olim", "deinde", "denique",
    "praeterea", "insuper", "item", "similiter", "primum", "primo",
    "hinc", "inde", "illinc", "eo", "huc", "illuc", "ubique", "undique",
    "o", "an", "num", "utrum", "ne", "seu", "sive", "velut", "veluti",
    "tanquam", "tamquam", "quasi", "prout", "prope", "longe",
}

_NONLETTER = re.compile(r"[^A-Za-zÀ-ÿ]+")
_CARET = re.compile(r"\^[a-z0-9]{1,2}", re.IGNORECASE)
_ROMAN = re.compile(r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")
_ROMAN_KEEP = {"vi", "di", "mi", "ci"}  # real Latin words that look Roman

# -que words that are NOT the enclitic "and" (do not split these).
_QUE_EXCEPTIONS = {
    "atque", "neque", "itaque", "utique", "usque", "undique", "denique",
    "quoque", "quinque", "cumque", "plerumque", "ubique", "uterque",
    "utraque", "utrumque", "namque", "absque", "cunque", "unusquisque",
    "quisque", "quaeque", "quicunque", "quocunque", "peraeque", "susque",
    "oblique", "antique", "propinque", "seque", "torque", "quaque",
}

_LIG = str.maketrans({"æ": "ae", "œ": "oe", "ſ": "s", "Æ": "Ae", "Œ": "Oe"})


def _split_que(tok: str) -> list[str]:
    low = tok.lower()
    if low.endswith("que") and low not in _QUE_EXCEPTIONS and len(low) > 4:
        return [tok[:-3], tok[-3:]]
    return [tok]


def _is_dropworthy(low: str) -> bool:
    if len(low) < 2:
        return True
    if low.isdigit():
        return True
    if low not in _ROMAN_KEEP and _ROMAN.match(low) and len(low) >= 2:
        return True
    return False


def _loose_key(phrase: str) -> str:
    """Rough inflection fold for ADJACENCY SORTING ONLY — not a lemma.

    Strips the commonest Latin nominal/verbal endings so inflected variants
    of the same phrase sort next to each other for the reviewer. Deliberately
    crude; never used for counting or merging.
    """
    out = []
    for w in phrase.split():
        w = re.sub(r"(ibus|arum|orum|erum|ium| arum)$", "", w)
        w = re.sub(r"(que)$", "", w)
        w = re.sub(r"(is|es|em|um|us|as|os|ae|am|os|is|os|"
                   r"i|o|a|e|m|s)$", "", w)
        out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def _page_num(path: Path) -> int | None:
    m = re.search(r"p(\d+)", path.stem)
    return int(m.group(1)) if m else None


def _join_lines(parts: list[str]) -> str:
    """Join OCR line items, undoing end-of-line hyphenation (``indig-`` +
    ``esta`` -> ``indigesta``) so split words aren't mined as two fragments."""
    text = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not text:
            text = p
        elif text[-1] in "-¬—­":  # hyphen / not-sign / em-dash / soft-hyphen
            text = text[:-1] + p
        else:
            text = text + " " + p
    return text


def load_corpus(start: int, end: int, *, include_marginalia: bool
                ) -> list[tuple[str, str]]:
    """Return ``[(page_id, raw_latin_text), ...]`` for pages in [start, end]."""
    out: list[tuple[str, str]] = []
    for path in sorted(ANNOT_DIR.glob("page_p*.json")):
        n = _page_num(path)
        if n is None or not (start <= n <= end):
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        regions = d.get("regions") or {}
        page_id = f"p{n:04d}"
        body = [(r.get("text_gold") or r.get("text_ocr_original") or "")
                for r in regions.get("body", [])]
        text = _join_lines(body)
        if include_marginalia:
            marg = [(r.get("text_gold") or r.get("text_ocr_original") or "")
                    for r in regions.get("marginalia", [])]
            marg_text = _join_lines(marg)
            if marg_text:
                # keep body/marginalia from dehyphenating into each other
                text = (text + " . " + marg_text) if text else marg_text
        if text.strip():
            out.append((page_id, text))
    return out


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


def clause_tokens(text: str) -> list[list[tuple[str, str]]]:
    """Return clauses, each a list of (surface, lower) content-token pairs.

    Punctuation delimits clauses, so an n-gram never spans a clause break.
    Carets and ligatures normalized; enclitic -que split; numerals dropped.
    """
    text = _CARET.sub(" ", text).translate(_LIG)
    clauses: list[list[tuple[str, str]]] = []
    for raw_clause in re.split(r"[.,;:!?()\[\]“”\"'«»—–]+", text):
        toks: list[tuple[str, str]] = []
        for word in raw_clause.split():
            for piece in _split_que(word):
                surface = _NONLETTER.sub("", piece)
                if not surface:
                    continue
                low = surface.lower()
                if _is_dropworthy(low):
                    continue
                toks.append((surface, low))
        if toks:
            clauses.append(toks)
    return clauses


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------


def mine(corpus: list[tuple[str, str]], *, min_count: int):
    word_count: Counter = Counter()
    word_pages: dict[str, set] = defaultdict(set)
    # proper-noun evidence: caps when NOT clause-initial
    caps_hits: Counter = Counter()
    caps_obs: Counter = Counter()

    # phrase -> [count, {pages}, example_surface]
    phrases: dict[tuple, list] = {}
    bigram_first: Counter = Counter()
    bigram_second: Counter = Counter()
    total_tokens = 0

    for page_id, text in corpus:
        for clause in clause_tokens(text):
            lows = [t[1] for t in clause]
            surfs = [t[0] for t in clause]
            total_tokens += len(lows)
            for i, (surf, low) in enumerate(clause):
                word_count[low] += 1
                word_pages[low].add(page_id)
                if i > 0:  # not clause-initial => caps is evidence of proper noun
                    caps_obs[low] += 1
                    if surf[:1].isupper():
                        caps_hits[low] += 1
            # bigram marginals (for log-likelihood)
            for i in range(len(lows) - 1):
                bigram_first[lows[i]] += 1
                bigram_second[lows[i + 1]] += 1
            # n-grams within the clause, stopword-trimmed at the ends
            for n in range(2, MAXN + 1):
                for i in range(len(lows) - n + 1):
                    gram = tuple(lows[i:i + n])
                    if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                        continue
                    rec = phrases.get(gram)
                    if rec is None:
                        phrases[gram] = [1, {page_id}, " ".join(surfs[i:i + n])]
                    else:
                        rec[0] += 1
                        rec[1].add(page_id)

    # Filter by min count
    phrases = {g: r for g, r in phrases.items() if r[0] >= min_count}

    # Maximal-repeat dedup: drop an n-gram fully explained by a longer one of
    # equal count (it only ever occurs inside that longer phrase).
    by_len = defaultdict(list)
    for g in phrases:
        by_len[len(g)].append(g)
    redundant = set()
    for n in range(MAXN, 2, -1):
        for g in by_len[n]:
            cnt = phrases[g][0]
            for sub in (g[:-1], g[1:]):  # the two (n-1)-subgrams at the ends
                if sub in phrases and phrases[sub][0] == cnt:
                    redundant.add(sub)
    for g in redundant:
        phrases.pop(g, None)

    # Log-likelihood for bigrams (Dunning G²).
    N = max(1, total_tokens)

    def loglik(w1: str, w2: str, c12: int) -> float:
        c1 = bigram_first.get(w1, 0)
        c2 = bigram_second.get(w2, 0)
        o11 = c12
        o12 = max(0, c1 - c12)
        o21 = max(0, c2 - c12)
        o22 = max(0, N - c1 - c2 + c12)
        tot = o11 + o12 + o21 + o22 or 1
        r1, r2 = o11 + o12, o21 + o22
        cc1, cc2 = o11 + o21, o12 + o22
        g = 0.0
        for o, e in ((o11, r1 * cc1 / tot), (o12, r1 * cc2 / tot),
                     (o21, r2 * cc1 / tot), (o22, r2 * cc2 / tot)):
            if o > 0 and e > 0:
                g += o * math.log(o / e)
        return round(2 * g, 2)

    def is_proper(low: str) -> bool:
        obs = caps_obs.get(low, 0)
        return obs >= 2 and caps_hits.get(low, 0) / obs >= 0.6

    word_rows = []
    total_content = sum(word_count[w] for w in word_count if w not in STOPWORDS)
    for low, c in word_count.most_common():
        if low in STOPWORDS or c < min_count:
            continue
        word_rows.append({
            "word": low, "count": c,
            "pct": round(100 * c / max(1, total_content), 3),
            "pages": len(word_pages[low]),
            "proper": is_proper(low),
            "loose_key": _loose_key(low),
        })

    phrase_rows = []
    for gram, (cnt, pages, example) in phrases.items():
        ll = loglik(gram[0], gram[1], cnt) if len(gram) == 2 else None
        phrase_rows.append({
            "phrase": " ".join(gram), "n": len(gram), "count": cnt,
            "loglik": ll, "pages": len(pages),
            "proper": all(is_proper(w) for w in gram),
            "example": example, "loose_key": _loose_key(" ".join(gram)),
            # head_key folds ONLY the last word, so phrases sharing a head noun
            # co-locate even when their front-end inflection differs and the
            # full loose_key doesn't line them up (libero arbitrio / arbitrii /
            # de arbitrio). Deterministic, inspectable — no lemmatizer.
            "head_key": _loose_key(gram[-1]),
        })
    # Sort: bigrams by loglik desc, longer phrases by count desc; interleave by
    # a blended key so the most "significant" surface first.
    phrase_rows.sort(key=lambda r: (-(r["loglik"] or 0), -r["count"], -r["n"]))

    return word_rows, phrase_rows, {
        "pages": len(corpus), "total_tokens": total_tokens,
        "content_tokens": total_content, "distinct_words": len(word_rows),
        "distinct_phrases": len(phrase_rows),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _write_tsv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")


def write_outputs(out_dir: Path, words, phrases, stats, *, start, end) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_tsv(out_dir / "words.tsv", words,
               ["word", "count", "pct", "pages", "proper", "loose_key"])
    _write_tsv(out_dir / "phrases.tsv", phrases,
               ["phrase", "n", "count", "loglik", "pages", "proper",
                "example", "loose_key", "head_key"])

    # Second view: grouped by head word (then by loose_key within a head), so
    # a reviewer sees every phrase built on the same head noun together —
    # catches variant clusters the front-folding loose_key sort splits apart.
    by_head = sorted(phrases, key=lambda r: (r["head_key"], r["loose_key"],
                                             -r["count"]))
    _write_tsv(out_dir / "phrases_by_head.tsv", by_head,
               ["head_key", "phrase", "count", "pages", "proper", "example"])

    top_w = [w for w in words if not w["proper"]][:40]
    top_names = [w for w in words if w["proper"]][:30]
    top_p = phrases[:50]
    lines = [
        f"# Latin corpus phrase-mining report (p{start:04d}-p{end:04d})",
        "",
        f"- pages: {stats['pages']}",
        f"- tokens: {stats['total_tokens']:,} "
        f"(content, stopwords excluded: {stats['content_tokens']:,})",
        f"- distinct content words (count≥min): {stats['distinct_words']:,}",
        f"- distinct phrases (count≥min): {stats['distinct_phrases']:,}",
        "",
        "Ranking: phrases by log-likelihood (bigrams) then raw count. "
        "`proper` marks likely proper nouns (capitalized off clause-start). "
        "`loose_key` sorts inflected variants adjacent — for the reviewer to "
        "merge; it is NOT a lemma.",
        "",
        "## Top content words",
        "",
        "| word | count | % |",
        "|---|---|---|",
    ]
    lines += [f"| {w['word']} | {w['count']} | {w['pct']} |" for w in top_w]
    lines += ["", "## Top likely proper nouns", "",
              "| name | count |", "|---|---|"]
    lines += [f"| {w['word']} | {w['count']} |" for w in top_names]
    lines += ["", "## Top phrases", "",
              "| phrase | n | count | loglik | pages |", "|---|---|---|---|---|"]
    lines += [f"| {p['phrase']} | {p['n']} | {p['count']} | "
              f"{p['loglik'] if p['loglik'] is not None else ''} | {p['pages']} |"
              for p in top_p]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mine Latin corpus for frequent words/phrases.")
    ap.add_argument("--start-page", type=int, default=32)
    ap.add_argument("--end-page", type=int, default=567)
    ap.add_argument("--min-count", type=int, default=3)
    ap.add_argument("--no-marginalia", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    corpus = load_corpus(args.start_page, args.end_page,
                         include_marginalia=not args.no_marginalia)
    if not corpus:
        print("No pages loaded.", file=sys.stderr)
        return 1
    words, phrases, stats = mine(corpus, min_count=args.min_count)
    write_outputs(args.out_dir, words, phrases, stats,
                 start=args.start_page, end=args.end_page)
    print(f"pages {stats['pages']} | tokens {stats['total_tokens']:,} | "
          f"words {stats['distinct_words']:,} | phrases {stats['distinct_phrases']:,}")
    print(f"Wrote {args.out_dir}/words.tsv, phrases.tsv, "
          f"phrases_by_head.tsv, report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
