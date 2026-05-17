"""V3 of the Whitaker translation prompt — Phase 3 second iteration.

Purpose
-------
``translation_prompts_whitaker_v2.py`` improved on the baseline by
+1.58% COMET-DA (0.7494 → 0.7612), winning 26 of 45 unit-runs. Three
units regressed; investigation
(``04_translation_work/ab/whitaker_ch1/whitaker_v2_vs_baseline_report.md``)
identified a single underlying cause: v2's Rule 2 register guidance
was too permissive. The model interpreted "Victorian register" as
license to use Tudor/KJV constructions (``doth``, ``in no wise``) and
over-Latinate vocabulary (``perspicuously``) that Parker Society does
NOT use.

Grep-validated facts (against ``whitaker_english/`` OCR):
- ``hath``, ``wherein``, ``whilst`` — **44 occurrences** across 14 pages.
  Parker uses these freely; baseline's strict-modern Rule 2 was wrong
  to forbid them.
- ``doth``, ``in no wise``, ``verily`` — **0 occurrences**. Parker
  does NOT use these. v2's allowed list mistakenly included ``doth``.

Headline deltas vs. v2
----------------------
1. **Rule 2 register list tightened**: ``doth`` removed from allowed
   constructions; ``doth``, ``in no wise``, ``verily`` added to the
   explicit-forbid list.
2. **New Rule 2 sub-clause — plain Anglo-Saxon for ordinary
   concepts, Latinate for doctrinal technical terms.** The Victorian
   register uses simple words for common ideas (``satis`` →
   ``enough``, ``multum`` → ``much``). But ``perspicuus`` /
   ``perspicuitas`` / ``perspicue`` are technical terms naming the
   Reformed doctrine of Scripture's clarity (Question IV's focus)
   and stay Latinate. User-verified word counts in Parker:
   ``perspicuous`` 13×, ``perspicuity`` 23×, ``perspicuously`` 7×,
   ``clearly`` 49×, ``clear`` 219× — both forms appear; doctrinal
   contexts use the Latinate, ordinary contexts use the plain form.
   The rule preserves the Latinate forms for the technical
   theological vocabulary and only prescribes plain English for
   genuinely ordinary words.
3. **New Rule 2 sub-clause — natural English word order**: don't
   preserve Latin's frequent fronting of prepositional/adverbial
   phrases. ``de Scripturis Iudæi… sentiebant`` → "The Jews thought
   ... of the scriptures" (subject first), NOT "Concerning the
   scriptures the Jews thought…".
4. **Rule 7c (litotes) strengthened** with an explicit antithesis
   example: when the Latin is ``X minime [negative verb]… sed
   [positive verb]``, prefer to render the negation as the positive
   ("not in the least … but rather …" → "rather …"), or drop the
   negation if the antithesis carries it. ``minime reprehendit, sed
   laudat`` → "rather praises" (not "in no way reproves, but
   rather praises").

All other rules are unchanged from v2. Rule count remains 7.

Architectural discipline
------------------------
Per the plan: every change tagged shared-core (transfers to Ussher)
or corpus-skin (Whitaker only). v3's three Rule 2 sub-clauses are all
**shared core**: they encode general translation principles
(register-by-reference with specific forbid-list; Anglo-Saxon over
Latinate; natural word order). Rule 7c's strengthening is also shared
core. No new corpus-skin content.

Public surface
--------------
Identical to v2 and the original Whitaker prompt.
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
# Translator brief — unchanged from v2
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
# Hard rules — v3 refinement of v2
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

   2c. THEOLOGICAL VOCABULARY STAYS LATINATE; PLAIN ANGLO-SAXON
   ONLY FOR GENUINELY ORDINARY WORDS.

   GOVERNING PRINCIPLE: in Parker Society's register, theological
   and Reformation-polemic vocabulary is preserved Latinate. Plain
   Anglo-Saxon English is reserved for genuinely ordinary words.
   When in doubt, default Latinate.

   The Parker Society's word counts (verified against the full
   English translation) confirm this overwhelmingly:

     - 'tradition' 636× / 'handing down' 0×
     - 'testimony' 378× / 'witness' 70×
     - 'version' 189× / 'translation' 79× / 'rendering' 5×
     - 'interpretation' 150× / 'exposition' 76×
     - 'obscure' 117× / 'dark' 32× / 'hidden' 22×
     - 'vernacular' 42× / 'native' 14×
     - 'perfection' 25× / 'completeness' 1×
     - 'perspicuity' 23× / 'perspicuous' 13× / 'perspicuously' 7×
     - 'divinely inspired' 12× / 'God-breathed' 0×
     - 'literal sense' 26× / 'plain meaning' 0×
     - 'justification' 10× / 'being made right' 0×

   PRESERVED-LATINATE WHITELIST (do not normalize to plain English):

     Q I (Canon):           'canonical', 'apocryphal', 'genuine'
     Q II (Versions):       'version' (biblical versions), 'vernacular'
     Q III (Authority):     'authority', 'tradition', 'testimony',
                            'inspiration', 'divinely inspired'
     Q IV (Perspicuity):    'perspicuous', 'perspicuity',
                            'perspicuously', 'obscure', 'obscurity'
     Q V (Interpretation):  'interpretation', 'the literal sense',
                            'analogy of faith', 'judge of controversies'
     Q VI (Perfection):     'sufficiency', 'perfection', 'scripture
                            alone', 'rule of faith'
     Soteriology:           'justification', 'sanctification',
                            'predestination', 'grace', 'merit(s)'
     Catholic-polemic:      'purgatory', 'transubstantiation',
                            'consubstantial', 'real presence',
                            'papist(s)' (lowercase per Rule 3c)
     Scholastic discourse:  'article(s) of faith', 'consensus of the
                            Fathers', 'controversy', 'doctrine'

   PARKER ALSO USES THE PLAIN FORMS, JUST LESS OFTEN. Where both
   forms appear substantially in Parker (e.g. 'obscure' 117× vs
   'dark' 32×; 'interpretation' 150× vs 'exposition' 76×), the
   choice is contextual. Plain forms are acceptable when the sense
   is ordinary rather than technical, but Latinate remains the
   default and should be reached for first.

   FOR GENUINELY ORDINARY WORDS, prefer plain Anglo-Saxon:

     'satis' -> 'enough' (not 'sufficiently' in routine usage)
     'multum' -> 'much' (not 'multitudinously')
     'omnino' -> 'altogether' / 'wholly'
     'fortè' -> 'perhaps' (not 'fortuitously')
     'manifesto' (adv) -> 'plainly' or 'manifestly'; both natural
     'magnitudo' -> 'greatness' / 'size' (not 'magnitude' unless
        astronomical)

   WHEN UNCERTAIN: if the word names a Reformation doctrinal
   category, a Catholic/Protestant polemical concept, a scholastic
   theological technicality, or any term associated with one of the
   six Controversy I Questions, keep it Latinate. Otherwise, ask
   whether a Victorian scholar would use the word naturally; if yes,
   use it; if it sounds like a literal Latin calque, replace with
   plain English.

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
# Prompt builder — unchanged from v2 except for the new HARD_RULES
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Whitaker v3 translation prompt."""

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
