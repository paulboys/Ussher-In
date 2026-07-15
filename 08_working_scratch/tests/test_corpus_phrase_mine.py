"""Tests for the surface-form phrase miner and the review-candidate curator.

The miner's value is that it PROPOSES and never DECIDES: it must group
inflected variants adjacently without ever fabricating a false merge (the
reason CLTK was rejected — 25.7% content / 70% proper-noun error on p0058).
These tests pin the fiddly normalization and counting logic that makes the
proposals trustworthy.
"""
from __future__ import annotations

import corpus_phrase_mine as m
import corpus_review_candidates as rc


def _phrase_index(corpus, *, min_count):
    _, phrase_rows, _ = m.mine(corpus, min_count=min_count)
    return {r["phrase"]: r for r in phrase_rows}


def _word_index(corpus, *, min_count):
    word_rows, _, _ = m.mine(corpus, min_count=min_count)
    return {r["word"]: r for r in word_rows}


# ---------------------------------------------------------------------------
# _join_lines — OCR end-of-line dehyphenation
# ---------------------------------------------------------------------------


def test_join_lines_dehyphenates_across_break():
    # "indig-" + "esta" must fuse into one word, not two fragments.
    assert m._join_lines(["licet quæ prorsus indig-", "esta habentur"]) \
        == "licet quæ prorsus indigesta habentur"


def test_join_lines_spaces_normal_break():
    assert m._join_lines(["alpha beta", "gamma"]) == "alpha beta gamma"


def test_join_lines_skips_blanks():
    assert m._join_lines(["alpha", "  ", "beta"]) == "alpha beta"


# ---------------------------------------------------------------------------
# _split_que — enclitic splitting with the standard exceptions
# ---------------------------------------------------------------------------


def test_split_que_splits_enclitic():
    assert m._split_que("gentesque") == ["gentes", "que"]
    assert m._split_que("Gentesque") == ["Gentes", "que"]  # case preserved


def test_split_que_respects_exceptions():
    for w in ("atque", "neque", "usque", "quinque", "denique", "quoque"):
        assert m._split_que(w) == [w]


def test_split_que_ignores_short_words():
    assert m._split_que("que") == ["que"]


# ---------------------------------------------------------------------------
# clause_tokens — normalization
# ---------------------------------------------------------------------------


def test_ligatures_folded():
    (clause,) = m.clause_tokens("hæresim Pelagianam")
    lows = [low for _, low in clause]
    assert "haeresim" in lows


def test_carets_stripped():
    (clause,) = m.clause_tokens("verbum^q sequens")
    lows = [low for _, low in clause]
    assert lows == ["verbum", "sequens"]  # no stray "q" token


def test_capital_letter_not_stripped_regression():
    # Regression: the first run decapitated every proper noun (Britannia ->
    # "ritannia") because the strip regex whitelisted only lowercase letters.
    (clause,) = m.clause_tokens("Britanniam Christi")
    surfaces = [surf for surf, _ in clause]
    assert surfaces == ["Britanniam", "Christi"]


def test_roman_numerals_dropped_but_real_words_kept():
    (clause,) = m.clause_tokens("liber xii capitulo vi mille")
    lows = [low for _, low in clause]
    assert "xii" not in lows          # pure numeral dropped
    assert "vi" in lows               # whitelisted real word kept
    assert "mille" in lows            # not a valid Roman numeral


def test_punctuation_splits_clauses():
    clauses = m.clause_tokens("alpha beta. gamma delta")
    assert len(clauses) == 2


# ---------------------------------------------------------------------------
# mine — counting, filtering, dedup, flags
# ---------------------------------------------------------------------------


def test_min_count_filters_rare_phrases():
    corpus = [("p0001", "rara avis. rara avis. unica occasio")]
    idx = _phrase_index(corpus, min_count=2)
    assert "rara avis" in idx
    assert "unica occasio" not in idx  # occurs once


def test_ngram_does_not_cross_clause_boundary():
    corpus = [("p0001", "alpha beta. gamma delta") for _ in range(3)]
    idx = _phrase_index(corpus, min_count=2)
    assert "alpha beta" in idx
    assert "gamma delta" in idx
    assert "beta gamma" not in idx  # spans the sentence break


def test_phrase_ends_are_stopword_trimmed():
    corpus = [("p0001", "in libero arbitrio") for _ in range(3)]
    idx = _phrase_index(corpus, min_count=2)
    assert "libero arbitrio" in idx
    assert "in libero" not in idx   # would start on the stopword "in"


def test_maximal_repeat_dedup_drops_redundant_subgram():
    # "sancti petri pauli" recurs; its end-subgrams occur ONLY inside it, so
    # at equal count they are redundant and dropped.
    corpus = [("p%04d" % i, "sancti petri pauli") for i in range(3)]
    idx = _phrase_index(corpus, min_count=2)
    assert "sancti petri pauli" in idx
    assert "sancti petri" not in idx
    assert "petri pauli" not in idx


def test_bigram_has_loglik_longer_phrase_does_not():
    # "gratia dei" recurs in VARIED contexts, so it survives dedup on its own
    # (it isn't wholly explained by any single longer phrase); the identical
    # "sancti petri pauli" survives as a 3-gram.
    text = "gratia dei magna. gratia dei parva. sancti petri pauli"
    corpus = [("p%04d" % i, text) for i in range(3)]
    idx = _phrase_index(corpus, min_count=2)
    assert idx["gratia dei"]["loglik"] is not None
    assert idx["sancti petri pauli"]["loglik"] is None
    # every surviving 3-gram carries no loglik
    threes = [r for r in idx.values() if r["n"] == 3]
    assert threes and all(r["loglik"] is None for r in threes)


def test_head_key_folds_last_word():
    corpus = [("p%04d" % i, "libero arbitrio") for i in range(3)]
    idx = _phrase_index(corpus, min_count=2)
    row = idx["libero arbitrio"]
    # head_key is the loose-fold of the LAST word only, co-locating phrases
    # that share a head noun regardless of front-end inflection.
    assert row["head_key"] == m._loose_key("arbitrio")


def test_word_rows_carry_page_spread():
    # The curator folds single-word proper nouns into the names worksheet and
    # filters them by page-spread, so word rows MUST expose a "pages" count.
    corpus = [("p0001", "gildas scripsit"), ("p0002", "gildas iterum")]
    words = _word_index(corpus, min_count=1)
    assert words["gildas"]["pages"] == 2


def test_proper_noun_flag_on_midclause_capital():
    # "Roma" capitalized off clause-start twice -> flagged proper; a word only
    # ever lowercase -> not flagged.
    corpus = [("p0001", "ad Roma. apud Roma. de terra")]
    words = _word_index(corpus, min_count=1)
    assert words["roma"]["proper"] is True
    assert words["terra"]["proper"] is False


# ---------------------------------------------------------------------------
# curator — variant clustering (one decision per concept)
# ---------------------------------------------------------------------------


def _row(phrase, loose_key, count, pages="5", proper="False", example=None):
    return {"phrase": phrase, "loose_key": loose_key, "count": str(count),
            "pages": pages, "proper": proper, "example": example or phrase}


def test_cluster_collapses_variants_by_loose_key():
    rows = [
        _row("libero arbitrio", "liber arbitri", 18),
        _row("liberi arbitrii", "liber arbitri", 8),
        _row("gratia dei", "grat de", 54),
    ]
    clusters = rc._cluster(rows)
    # highest total first
    assert clusters[0]["term"] == "gratia dei"
    arb = next(c for c in clusters if "arbitr" in c["term"])
    assert arb["total"] == 26                     # 18 + 8 summed
    assert arb["term"] == "libero arbitrio"       # most-frequent representative
    assert set(arb["variants"]) == {"libero arbitrio", "liberi arbitrii"}


def test_cluster_representative_is_highest_count():
    rows = [
        _row("galfrido monemuthensi", "galfrid monemuthens", 5),
        _row("galfridus monemuthensis", "galfrid monemuthens", 34),
    ]
    (cluster,) = rc._cluster(rows)
    assert cluster["term"] == "galfridus monemuthensis"
    assert cluster["total"] == 39
