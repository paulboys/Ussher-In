"""V5 — Ussher translation prompt. Phase 5 of the Whitaker-trained pipeline.

Purpose
-------
Inherits the locked v4-Whitaker shared core (Rule 1 Greek+English-in-
brackets / Latin-paraphrase-collapse; Rule 5 subject continuity; Rule 6
footnote sentinels; Rule 7 idiomatic English — authorial-I, litotes,
antithesis collapse, voice flexibility; lexicon and output contract)
and replaces only the corpus-skin sections per plan.md §3.

Corpus-skin replacements (this file):
- TRANSLATOR_BRIEF: Ussher's Britannicarum Ecclesiarum Antiquitates
  (1639; cited from the 1847 Elrington-Todd Latin edition) — 17th-
  century ecclesiastical-historical Latin, not 16th-century polemic.
- Rule 2 (REGISTER): no gold-standard English translation exists for
  this corpus, so the target is MODERN SCHOLARLY ENGLISH with
  Latinate doctrinal/scholastic vocabulary preserved (same lexical
  discipline as v4-Whitaker 2c, no Parker anchor). Tudor/KJV
  constructions still forbidden; the period-construction allow-list
  from v4-Whitaker 2a is DROPPED (no Parker register to match).
- Rule 3 (proper nouns / citations / casing): adapted for Ussher's
  patristic-historical citation style; the Parker-specific
  lowercase-papists convention is removed.
- Rule 4 (titles): Ussher's source uses 'CAP. I.' (abbreviated form)
  for chapter headings, not Whitaker's 'CAPVT PRIMVM.' Updated.

Rule 1 explicitly supersedes the old translation_prompts_v4.py Rule 1
(which directed PRESERVING Latin paraphrase verbatim untranslated).
User direction 2026-05-18: that rule is stale. The Whitaker-learned
rule applies to Ussher too — where Whitaker or Ussher follow Greek
with a Latin paraphrase, render the Greek + English meaning in
brackets (collapsing the Latin into the English-in-brackets slot).

Author-fidelity rubric (per Phase 4 outcome): score against the Latin
source, NOT against any editorial English translation.

Public surface
--------------
Identical to all prior prompts: build_translation_prompt,
LEXICON_LATIN_HINTS, LEXICON_GREEK_HINTS, OUTPUT_CONTRACT,
LEXICON_PROFILES, contains_greek, HARD_RULES, TRANSLATOR_BRIEF.
"""

from __future__ import annotations

from typing import Sequence

from translation_prompts import (
    LEXICON_GREEK_HINTS,
    LEXICON_LATIN_HINTS,
    LEXICON_PROFILES,
    OUTPUT_CONTRACT,
    _build_marker_lookup,
    _format_body_lines,
    _format_footnotes,
    _format_unit_ids,
    _inject_markers,
    contains_greek,
)


# ---------------------------------------------------------------------------
# Translator brief — Ussher corpus skin
# ---------------------------------------------------------------------------

TRANSLATOR_BRIEF = (
    "You are translating reviewed lines from James Ussher's "
    "Britannicarum Ecclesiarum Antiquitates (1639; cited from the "
    "1847 Elrington-Todd collected-works edition). Source language "
    "is 17th-century ecclesiastical-historical Latin with Patristic "
    "and biblical Greek citations embedded throughout. The work is "
    "Ussher's scholarly history of the early British and Irish "
    "churches, dense with patristic citations, ecclesiastical "
    "history, and place-name discussions. No gold-standard English "
    "translation exists for this corpus; target modern scholarly "
    "English of the kind appropriate to academic ecclesiastical "
    "history, with Latinate doctrinal and scholastic vocabulary "
    "preserved. The Hard Rules below are stricter than the Lexicon "
    "Hints; when they conflict, follow the Hard Rules."
)


# ---------------------------------------------------------------------------
# Hard rules — Ussher v5
# Rules 1, 5, 6, 7 inherited verbatim from v4-Whitaker (shared core).
# Rules 2, 3, 4 replaced for the Ussher corpus skin.
# ---------------------------------------------------------------------------

HARD_RULES = """\
Hard rules (apply every one to every line; if a rule conflicts with
the lexicon hints, the rule wins):

1. GREEK PRESERVATION + ENGLISH IN BRACKETS (LATIN PARAPHRASE COLLAPSED).
   Whenever Greek script appears in a body line or footnote, preserve
   the Greek verbatim in your English output (with its polytonic
   accents, breathings, and iota subscript intact), and immediately
   follow it with a concise English translation in square brackets.
   Both the Greek and the English MUST appear in the output.
   Do NOT replace the Greek with English alone.

   When Ussher follows the Greek with his own Latin paraphrase of
   the same content (signaled by adjacency, an optional introducer
   like 'id est', 'hoc est', 'inquit', 'sive', or by quoted Latin
   whose meaning visibly mirrors the Greek), COLLAPSE that Latin into
   the English-in-brackets slot. Do NOT separately render the Latin
   paraphrase as English prose; do NOT preserve the Latin paraphrase
   verbatim either. The Latin is Ussher's translation aid for his
   17th-century reader; its meaning is fully captured by your single
   English-in-brackets rendering of the Greek.

   Examples:

   Standalone Greek (no Latin gloss):
     Source: 'as Origen says, ὁ λόγος αὐτοῦ τρέχει ταχέως, and...'
     Output: 'as Origen says, ὁ λόγος αὐτοῦ τρέχει ταχέως [his word
       runs swiftly], and...'

   Greek followed by Ussher's Latin paraphrase (collapse the Latin):
     Source: 'καθὼς γέγραπται, sicut scriptum est. Erat enim...'
     Correct: 'καθὼς γέγραπται [as it is written]. For it was...'
     Wrong (double-rendered): 'καθὼς γέγραπται [as it is written],
       as it is written. For it was...'
     Wrong (preserved Latin): 'καθὼς γέγραπται [as it is written],
       sicut scriptum est. For it was...'

2. REGISTER — MODERN SCHOLARLY ENGLISH; LATINATE DOCTRINAL VOCABULARY.

   No gold-standard English translation of this corpus exists. The
   register target is MODERN SCHOLARLY ENGLISH appropriate to
   academic ecclesiastical history — clear, formal, unornamented.

   2a. FORBIDDEN — these produce Tudor/KJV register inappropriate to
   modern scholarly prose:

   - 'doth', 'dost', 'didst', 'wast', 'art' (as 2nd-person sg.)
   - 'in no wise', 'in nowise', 'in any wise'
   - 'verily', 'vouchsafed', 'thee', 'thou', 'thy', 'thine', 'ye'
   - 'whereunto', 'betwixt', 'hither', 'thence'
   - inverted word order ('him spoke', 'spoke he')
   - 'hath', 'doth' as 3rd-person singular (use 'has', 'does')
   - 'whilst' (use 'while')

   When you find yourself reaching for one of these, use the plain
   modern equivalent:
     'doth' -> 'does'
     'hath' -> 'has'
     'in no wise' -> 'not'; or drop the negation entirely if a
        positive antithesis follows (see Rule 7c)
     'verily' -> 'truly' (and consider whether the rhetorical
        emphasis is needed at all)

   2b. LATINATE FOR DOCTRINAL, SCHOLASTIC, AND ECCLESIASTICAL
   VOCABULARY; PLAIN ENGLISH FOR ORDINARY WORDS. Default Latinate
   when in doubt — Ussher writes in a scholarly idiom where Latinate
   terminology IS the technical vocabulary.

   Keep Latinate (do not normalize to plain English):
     canonical, apocryphal, authority, tradition, testimony,
     inspiration, divinely inspired, interpretation, the literal
     sense, perfection, sufficiency, justification, sanctification,
     predestination, grace, schism, heresy, orthodox, catholic
     (lowercase, meaning 'universal'), apostolic, episcopate,
     presbyterate, primacy, jurisdiction, ecclesiastical, patristic,
     conciliar, canon (of scripture), vernacular, controversy,
     doctrine, ordinance, see (as in episcopal see), province,
     metropolitan, suffragan, monastic, anachoretic.

   For genuinely ordinary (non-doctrinal) words, prefer plain English:
     'satis' -> 'enough'      'multum' -> 'much'
     'omnino' -> 'altogether' 'fortè' -> 'perhaps'
     'magnitudo' -> 'greatness' / 'size' (not 'magnitude')

   2c. NATURAL ENGLISH WORD ORDER. Don't preserve Latin's frequent
   fronting of prepositional or adverbial phrases unless the
   discourse focus genuinely requires it. English typically puts
   the subject first.

3. PROPER NOUNS, CITATIONS, AND ECCLESIASTICAL TERMS.

   3a. Proper-noun normalization. Render well-known historical and
   ecclesiastical proper nouns in their conventional modern English
   form. Examples: 'Hieronymus' -> 'Jerome'; 'Augustinus' ->
   'Augustine'; 'Beda' -> 'Bede'; 'Patricius' -> 'Patrick';
   'Columba' -> 'Columba'; 'Cuthbertus' -> 'Cuthbert'; 'Theodoretus'
   -> 'Theodoret'; 'Eusebius Caesariensis' -> 'Eusebius of
   Caesarea'. Less-familiar names (obscure persons, minor places,
   British/Irish toponyms whose modern form is contested or
   nonexistent) keep the source spelling.

   3b. Patristic and historical citations. Ussher's footnotes and
   inline citations are dense with abbreviated book/chapter
   references. Render them in standard modern scholarly form:
     'lib. 2. cap. 40' -> 'book 2, chapter 40' (or '2.40' when
        the surrounding context is heavily compressed)
     'Histor. Eccles. lib. 3. cap. 4' -> 'Ecclesiastical History,
        book 3, chapter 4'
     'apud Eusebium, Histor. Eccles.' -> 'in Eusebius,
        Ecclesiastical History'
   Scripture citations follow standard modern form: 'Matt. 5:39',
   'John 5:39', NOT the Latin 'Matthaei v. 39' or Victorian
   'the thirty-ninth verse of the fifth chapter'.

   3c. NO blanket lowercase convention for polemical nouns. Unlike
   Whitaker, Ussher's register is historical/ecclesiastical rather
   than polemical; render 'Scripturas' as 'Scriptures' in formal
   contexts. Common nouns like 'ecclesia' render as 'church'
   (lowercase) when referring to a particular congregation or
   building; 'Church' (capitalized) when referring to the universal
   Church or a specific institutional body ('the Roman Church',
   'the Eastern Church').

4. TITLES — BOOKS, TREATISES, CHAPTERS.

   4a. When the source names a Latin or Greek work — typically
   signposted by 'libro [N]', 'liber X', 'in [topic] book', 'contra
   [author]', or a Greek genitive title — render the English title
   in italics-style quotation marks and capitalize as a title (e.g.
   '"Ecclesiastical History"', '"On the Sufferings of the Martyrs"',
   '"Against Jovinian"').

   4b. Chapter titles in the source use the ABBREVIATED form
   ('CAP. I.', 'CAP. II.', 'CAP. III.', etc.) — Ussher's convention,
   not Whitaker's 'CAPVT PRIMVM.' Render with English 'CHAPTER'
   followed by the Roman numeral and a terminal period:
     'CAP. I.'   -> 'CHAPTER I.'
     'CAP. II.'  -> 'CHAPTER II.'
     'CAP. III.' -> 'CHAPTER III.'
   Do NOT spell out as 'CHAPTER ONE.' / 'CHAPTER TWO.'

5. SUBJECT CONTINUITY ACROSS LINES. When a line carries a third-
   person verb whose subject was established in an earlier line of
   the same batch, keep the subject reference clear. If ambiguity is
   high (antecedent several lines earlier, multiple candidates
   intervene), insert a short clarifying parenthetical naming the
   antecedent on first occurrence (e.g. 'he (Bede) records
   that...').

6. FOOTNOTE-MARKER SENTINELS. Body lines may contain '^X' (caret
   followed by a single letter or symbol). That mark locates a
   printed superscript footnote anchor in the source. Translate the
   body line WITHOUT echoing the caret or the marker symbol in the
   English; marker placement is handled by a separate downstream
   pass. The caret character ('^') is reserved for this sentinel.

7. IDIOMATIC ENGLISH OVER LITERAL LATIN MIRRORING.

   7a. AUTHORIAL FIRST-PERSON IS SINGULAR. In single-author works
   like this one, Latin first-person plural verbs and pronouns
   referring to the author render in English as first-person
   singular ('I', 'me', 'my', 'mine'), not plural ('we', 'our'):
     'ponemus' -> 'I will lay' (not 'we will lay')
     'iudicamus' -> 'I judge' / 'I think' (not 'we judge')
     'affirmamus' -> 'I affirm' (not 'we affirm')
   EXCEPTION: when the Latin plural clearly refers to a group
   including the author (e.g. 'nos omnes', 'nos Britanni', 'we the
   British'), keep the English plural.

   7b. LITOTES NORMALIZATION. Latin 'non' + negative adjective is a
   rhetorical figure (litotes) that often reads more naturally in
   English as the positive equivalent:
     'non obscurum testimonium' -> 'plain testimony' (not 'no
        obscure testimony')
     'non sine causa' -> 'with cause' or 'rightly' (not 'not
        without cause')
     'non parvum' -> 'considerable' (not 'no small')
   Preserve the litotes only when its rhetorical weight is doing
   real argumentative work and the negative form reads cleanly.

   7c. NEGATION + ANTITHESIS — DROP THE NEGATION. When Latin uses
   'minime', 'non', 'nullo modo' followed by a contrastive 'sed'
   clause supplying the positive, render the positive directly
   rather than echoing the negation in English:

     LAT: 'Quod illorum iudicium minime reprehendit, sed
        laudat potius'
     Right: 'rather praises this judgement of theirs' (drop the
        negation entirely; antithesis carries the meaning)

   When the negative is the substantive point (rare; usually a
   denial without antithesis) keep the negation.

   7d. VOICE FLEXIBILITY. Choose active or passive voice based on
   English idiom and discourse focus, not mechanical mirroring of
   Latin syntax. When the discourse topic is the patient rather
   than the agent, English passive is often preferred. Active
   remains the default for narrative and where the agent IS the
   topic."""


# ---------------------------------------------------------------------------
# Prompt builder — identical structure to v4-Whitaker
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Ussher v5 translation prompt."""

    if lexicon_profile not in LEXICON_PROFILES:
        raise ValueError(
            f"Unknown lexicon_profile {lexicon_profile!r}; "
            f"must be one of {LEXICON_PROFILES}"
        )

    combined_text = "\n".join(
        (line.get("text_gold") or line.get("text_ocr_original") or "")
        for line in body_lines
    ) + "\n" + "\n".join(
        (fn.get("text_gold") or fn.get("text_ocr_original") or "")
        for fn in footnotes
    )
    greek_present = contains_greek(combined_text)

    include_latin = lexicon_profile in ("auto", "latin_only", "latin_greek")
    if lexicon_profile == "auto":
        include_greek = greek_present
    elif lexicon_profile == "latin_greek":
        include_greek = True
    else:
        include_greek = False

    lexicon_blocks: list[str] = []
    if include_latin:
        lexicon_blocks.append(LEXICON_LATIN_HINTS)
    if include_greek:
        lexicon_blocks.append(LEXICON_GREEK_HINTS)
    lexicon_section = "\n\n".join(lexicon_blocks) if lexicon_blocks else ""

    marker_lookup = _build_marker_lookup(footnotes)
    body_block = _format_body_lines(body_lines, marker_lookup)
    footnote_block = _format_footnotes(footnotes)
    requested_ids = _format_unit_ids(body_lines, footnotes)

    sections: list[str] = [
        TRANSLATOR_BRIEF,
        f"Page identifier: {page_id}",
        HARD_RULES,
    ]
    if lexicon_section:
        sections.append("Lexicon hints:\n\n" + lexicon_section)
    sections.append(
        "Body lines (each must be translated as a single unit, keyed "
        "by line_id):\n" + body_block
    )
    sections.append(
        "Linked footnotes (translate each as its own unit, keyed by "
        "footnote_id):\n" + footnote_block
    )
    sections.append(
        f"Requested translation units (return one entry per ID): "
        f"{requested_ids}"
    )
    if extra_context:
        sections.append("Additional page context:\n" + extra_context.rstrip())
    sections.append(OUTPUT_CONTRACT)

    return "\n\n".join(sections) + "\n"


__all__ = [
    "HARD_RULES",
    "LEXICON_GREEK_HINTS",
    "LEXICON_LATIN_HINTS",
    "LEXICON_PROFILES",
    "OUTPUT_CONTRACT",
    "TRANSLATOR_BRIEF",
    "build_translation_prompt",
    "contains_greek",
]
