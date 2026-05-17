"""V4 of the Whitaker translation prompt — Phase 3 third iteration.

Purpose
-------
v3 regressed against v2 on COMET-DA (mean 0.7557 vs 0.7612, -0.72%)
despite no defect in any individual rule change. Diagnosis
(see ``04_translation_work/ab/whitaker_ch1/whitaker_v3_vs_v2_report.md``
and the side-by-side translation comparison on units
ch1_u004/u009/u010/u012/u013):

1. Rule 2c (Latinate-vocabulary preservation) grew to ~65 lines —
   word-count tables, a per-Question (Q I–VI) whitelist, paragraph-
   long counterpoints with examples. The bulk consumed the model's
   attention budget.

2. Segment-boundary leakage appeared in v3: sentence fragments bled
   across alignment-unit boundaries in run01 of u009/u010/u012/u013
   (e.g. ``u010 run1`` v3 began ``"mony to Christ. The scriptures,
   moreover…"`` — the ``mony to Christ`` tail belongs to u009).
   Almost certainly downstream of the same attention drain.

3. Ironically, v3 sometimes reverted to literal Latin word order in
   u012 (``"the whole of it on this plan into six questions I judge
   can be distributed"``), violating its own new Rule 2d.

4. Run-to-run variance widened (u010 swings 0.676–0.775 across v3
   runs; v2 was stable). Bigger prompts → less determinism.

v4 keeps v3's small targeted clauses (2a register list, 2b forbid
list, 2d word order, 7c antithesis collapse) but shrinks Rule 2c
back to its principle plus a compact flat whitelist — moving the
word-count justification into the diagnostic log where it belongs.
Rule count remains 7.

Headline deltas vs. v3
----------------------
1. **Rule 2c slimmed from ~65 lines to ~15.** Keep the
   Latinate-vs-plain principle, keep a single flat doctrinal
   whitelist, keep the ordinary-words counter-list. Drop the
   per-Question categorization, the word-count tables, and the
   paragraph-long ``WHEN UNCERTAIN`` / ``PARKER ALSO USES THE PLAIN
   FORMS`` prose. Those are diagnostic justifications, not
   instructions the model needs at inference time.

All other rules unchanged from v3.

Architectural discipline
------------------------
This is a pure shared-core change — a rule audit, not a new
behaviour. Demoting the verbose Latinate-justification from rule
text to source-file comments is exactly the "Prefer rule
consolidation over addition" discipline in plan.md §5 / §9.

Public surface
--------------
Identical to v3.
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
# Translator brief — unchanged from v2/v3
# ---------------------------------------------------------------------------

TRANSLATOR_BRIEF = (
    "You are translating reviewed lines from William Whitaker's "
    "Disputatio de Sacra Scriptura contra huius temporis Papistas, "
    "imprimis Robertum Bellarminum Iesuitam, et Thomam Stapletonum "
    "(1588; cited from the 1690 Latin edition). Source language is "
    "16th-century scholastic Latin with Patristic and Hellenistic "
    "Greek citations embedded throughout. Your goal is English that "
    "matches the register, voice, and conventions of the 1849 Parker "
    "Society English translation (William Fitzgerald, tr.) — the "
    "gold standard for this corpus. The Hard Rules below are stricter "
    "than the Lexicon Hints; when they conflict, follow the Hard Rules."
)


# ---------------------------------------------------------------------------
# Hard rules — v4: Rule 2c slimmed from v3; everything else unchanged
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

   When Whitaker follows the Greek with his own Latin paraphrase of
   the same content (signaled by adjacency, an optional introducer
   like 'id est', 'hoc est', 'inquit', 'sive', or by quoted Latin
   whose meaning visibly mirrors the Greek), COLLAPSE that Latin into
   the English-in-brackets slot. Do NOT separately render the Latin
   paraphrase as English prose; do NOT preserve the Latin paraphrase
   verbatim either. The Latin is Whitaker's translation aid for his
   16th-century reader; its meaning is fully captured by your single
   English-in-brackets rendering of the Greek.

   Examples:

   Standalone Greek (no Latin gloss):
     Source: 'as Origen says, ὁ λόγος αὐτοῦ τρέχει ταχέως, and...'
     Output: 'as Origen says, ὁ λόγος αὐτοῦ τρέχει ταχέως [his word
       runs swiftly], and...'

   Greek followed by Whitaker's Latin paraphrase (collapse the Latin):
     Source: 'Ἐρευνᾶτε τὰς γραφὰς, Scrutamini Scripturas. Fuerat
       enim Chriſtus...'
     Correct: 'Ἐρευνᾶτε τὰς γραφὰς [Search the scriptures]. For
       Christ had been...'
     Wrong (double-rendered): 'Ἐρευνᾶτε τὰς γραφὰς [Search the
       scriptures], Search the Scriptures. For Christ had been...'
     Wrong (preserved Latin): 'Ἐρευνᾶτε τὰς γραφὰς [Search the
       scriptures], Scrutamini Scripturas. For Christ had been...'

2. REGISTER — MATCH THE 1849 PARKER SOCIETY TRANSLATION.

   2a. Target the register, vocabulary, and phrasing conventions of
   the 1849 Parker Society English translation. That translation
   uses formal Victorian scholarly English. The following period
   constructions appear in the gold standard and are ACCEPTABLE
   when natural:

   - 'wherein', 'whence', 'whither', 'thither', 'hereby', 'thereby',
     'thereof', 'wherewithal'
   - 'hath' (3rd person sg. of 'have'), particularly in scriptural
     and credal contexts
   - 'whilst' (interchangeable with 'while')
   - 'shall' for first-person future ('I shall lay...'); 'will' for
     resolved intention

   Example: 'In quo Controuerſia hæc omnis…' opening a chapter
   description renders as 'Wherein this whole controversy…',
   matching Parker's chapter-subtitle convention.

   2b. STRICTLY FORBIDDEN — these do NOT appear in Parker and produce
   a Tudor/KJV register that Parker explicitly avoids:

   - 'doth', 'dost', 'didst', 'wast', 'art' (as 2nd-person sg.)
   - 'in no wise', 'in nowise', 'in any wise'
   - 'verily', 'vouchsafed', 'thee', 'thou', 'thy', 'thine', 'ye'
   - 'whereunto', 'betwixt', 'hither', 'thence'
   - inverted word order ('him spoke', 'spoke he')

   When you find yourself reaching for one of these, use the plain
   modern equivalent:
     'doth' -> 'does'
     'in no wise' / 'by no means' -> 'not'; or drop the negation
        entirely if a positive antithesis follows (see Rule 7c)
     'verily' -> 'truly' (and consider whether the rhetorical
        emphasis is needed at all)

   2c. LATINATE FOR DOCTRINAL VOCABULARY; PLAIN ENGLISH FOR
   ORDINARY WORDS. Default Latinate when in doubt.

   Keep Latinate (do not normalize to plain English):
     canonical, apocryphal, authority, tradition, testimony,
     inspiration, divinely inspired, perspicuity, perspicuous,
     perspicuously, obscure, obscurity, interpretation, the literal
     sense, analogy of faith, sufficiency, perfection, justification,
     sanctification, predestination, grace, merit(s), purgatory,
     transubstantiation, real presence, consubstantial, article(s)
     of faith, controversy, doctrine, version (of scripture),
     vernacular, papist(s) (lowercase per Rule 3c).

   For genuinely ordinary (non-doctrinal) words, prefer plain English:
     'satis' -> 'enough'      'multum' -> 'much'
     'omnino' -> 'altogether' 'fortè' -> 'perhaps'
     'magnitudo' -> 'greatness' / 'size' (not 'magnitude')

   2d. NATURAL ENGLISH WORD ORDER. Don't preserve Latin's frequent
   fronting of prepositional or adverbial phrases unless the
   discourse focus genuinely requires it. English typically puts
   the subject first.

     LAT: 'Et quidem de Scripturis Iudæi honorificè sentiebant'
     Wrong: 'And indeed concerning the scriptures the Jews thought
        honourably' (preserves Latin fronting)
     Right: 'And indeed the Jews thought honourably of the
        scriptures' (subject first, matches Parker)

3. PROPER NOUNS, CITATIONS, AND POLEMICAL TERMS.

   3a. Proper-noun normalization. Render well-known historical and
   ecclesiastical proper nouns in their conventional modern English
   form. Examples: 'Bellarminus' -> 'Bellarmine'; 'Stapletonus' ->
   'Stapleton'; 'Hieronymus' -> 'Jerome'; 'Augustinus' -> 'Augustine';
   'Theodoretus' -> 'Theodoret'. Less-familiar names keep the source
   spelling.

   3b. Scripture citations expand to Victorian scholarly style.
   Abbreviated Latin forms expand to spelled-out ordinals with full
   biblical-book names. Examples:
     'cap. 5. 39' -> 'the fifth chapter… the thirty-ninth verse'
     'Iohanem Euangeliſtam… cap. 5. 39' -> 'St John's Gospel… the
        thirty-ninth verse of the fifth chapter' (or analogous;
        match Parker Society phrasing where possible)
     'lib. 2. cap. 40' -> 'book 2, chapter 40' (footnote-style short
        citations stay short; only running-prose Scripture references
        expand)

   3c. Polemical common nouns follow Parker's lowercase convention
   in running prose:
     'Papistæ', 'Papista' -> 'papists', 'papist' (lowercase p)
     'Scripturas', 'Scripturis' -> 'scriptures' (lowercase s) in
        ordinary running prose; preserve capitalization only when the
        source emphasizes typographically (caps, italics) or when in
        a title/heading.

4. TITLES — BOOKS, TREATISES, CHAPTERS.

   4a. When the source names a Latin or Greek work — typically
   signposted by 'libro [N]', 'liber X', 'in [topic] book', 'contra
   [author]', or a Greek genitive title — render the English title
   in italics-style quotation marks and capitalize as a title (e.g.
   '"Against Jovinian"', '"On Christian Doctrine"').

   4b. Chapter titles in the source ('CAPVT PRIMVM.', 'CAPVT
   SECVNDVM.', 'CAPVT TERTIVM.', etc.) render with English 'CHAPTER'
   followed by the Roman numeral and a terminal period:
     'CAPVT PRIMVM.' -> 'CHAPTER I.'
     'CAPVT SECVNDVM.' -> 'CHAPTER II.'
     'CAPVT TERTIVM.' -> 'CHAPTER III.'
   Do NOT spell out as 'CHAPTER ONE.' / 'CHAPTER TWO.' — Parker
   Society uses Roman numerals.

5. SUBJECT CONTINUITY ACROSS LINES. When a line carries a third-
   person verb whose subject was established in an earlier line of
   the same batch, keep the subject reference clear. If ambiguity is
   high (antecedent several lines earlier, multiple candidates
   intervene), insert a short clarifying parenthetical naming the
   antecedent on first occurrence (e.g. 'he (Bellarmine) argues
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
     'nobis nulla controuerſia eſt' -> 'there is no controversy on
        my part' or 'I do not dispute…'
   EXCEPTION: when the Latin plural clearly refers to a group
   including the author (e.g. 'nos omnes', 'nos Reformati', 'we the
   Reformed'), keep the English plural.

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
   rather than echoing the negation in English. Parker Society
   consistently collapses these antithetical pairs:

     LAT: 'Quod illorum… iudicium Chriſtus minime reprehendit, sed
        laudat potius'
     Wrong: 'Which judgement of theirs… Christ in no way reproves,
        but rather praises'
     Right: 'Christ does not blame this judgement of theirs… in the
        least, but rather praises it' (Parker style)
     Even better when natural: 'Christ rather praises this
        judgement of theirs…' (drop the negation entirely;
        antithesis carries the meaning)

   When the negative is the substantive point (rare; usually a
   denial without antithesis) keep the negation.

   7d. VOICE FLEXIBILITY. Choose active or passive voice based on
   English idiom and discourse focus, not mechanical mirroring of
   Latin syntax. This SUPERSEDES the inherited v1 lexicon hint that
   directed strict active-voice rendering. When the discourse topic
   is the patient rather than the agent, English passive is often
   preferred:
     'Scripturas Papiſtæ celebrant' (topic: scriptures) -> 'the
        scriptures are praised by the papists' (passive — topic
        first), NOT 'the Papists celebrate the Scriptures' (active
        — agent first) when the surrounding discourse is about the
        scriptures.
   Active remains the default for narrative and where the agent IS
   the topic."""


# ---------------------------------------------------------------------------
# Prompt builder — unchanged from v3 except for the slimmed HARD_RULES
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Whitaker v4 translation prompt."""

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
