"""V2 of the Whitaker translation prompt — Phase 3 refinement.

Purpose
-------
Baseline ``translation_prompts_whitaker.py`` scored a mean COMET-DA of
**0.7494** against the 1849 Parker Society reference on c1_ch1
(p0030-p0031). Phase 2 diagnostic analysis (see
``04_translation_work/ab/whitaker_ch1/diagnostic_categories.md``)
identified seven categories of divergence — all stylistic, not
substantive. v2 applies them as a single bundle.

Headline deltas vs. baseline
----------------------------
1. **Rule 2 (REGISTER) rewritten** — "match the 1849 Parker Society
   register" replaces "no archaisms". Period constructions like
   ``wherein``, ``hath``, ``whilst``, ``whence`` are *acceptable* when
   natural and modelled in the gold standard. Closes the C1 gap (the
   worst unit `ch1_u002` lost solely on `wherein` vs `In which`).
2. **Rule 3 (PROPER NOUNS) expanded** — adds (a) Scripture citation
   expansion to Victorian style (`cap. 5. 39` → `fifth chapter…
   thirty-ninth verse`), and (b) Parker's lowercase convention for
   polemical common nouns (`papists`, `scriptures` in running prose).
3. **Rule 4 (TITLES) expanded** — chapter titles (`CAPVT PRIMVM`)
   render with Roman numerals (`CHAPTER I.`), not spelled-out
   cardinals.
4. **New Rule 7 (IDIOMATIC OVER LITERAL)** — three changes bundled:
   - Authorial first-person plural (`-mus` verbs in single-author
     works) → English first-person singular ``I`` / ``my``.
   - Latin litotes (`non obscurum`) → positive English (`plain`) when
     natural.
   - Voice (active / passive) chosen for English idiom and discourse
     focus rather than mechanical Latin parallelism. Supersedes the
     strict active-voice clause in the inherited v1 lexicon.

Architectural discipline
------------------------
Per ``04_translation_work/ab/whitaker_ch1/plan.md`` §3, every change is
tagged shared-core or corpus-skin:

- C1 (register-by-reference), C2 (authorial I), C3 (litotes),
  C4 (voice flex), C5 (citation expansion *principle*) — **shared
  core**, expected to transfer to Ussher when its gold-standard
  reference is determined.
- C5 specifics (`fifth chapter` style), C6 (polemical-noun casing),
  C7 (chapter titles Roman) — **corpus skin**, Whitaker/Parker only.

Rule count stays at 7 (matching baseline). Consolidation rather than
addition: v3-Ussher's failure mode was rule sprawl (12 rules); v2-Ussher
won at 6. We stay lean.

Public surface
--------------
Identical to ``translation_prompts_whitaker.py``:

* ``build_translation_prompt(...)``
* ``LEXICON_LATIN_HINTS``
* ``LEXICON_GREEK_HINTS``
* ``OUTPUT_CONTRACT``
* ``LEXICON_PROFILES``
* ``contains_greek``
* ``HARD_RULES``
* ``TRANSLATOR_BRIEF``
"""

from __future__ import annotations

from typing import Sequence

# Reuse the v1 lexicon as the base. The voice override in Rule 7 below
# supersedes v1's strict active-voice clause when they conflict.
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
# Translator brief
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
# Hard rules
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
   Target the register, vocabulary, and phrasing conventions of the
   1849 Parker Society English translation (William Fitzgerald, tr.).
   That translation uses formal Victorian scholarly English with
   Latinate vocabulary and selective period constructions. The
   following constructions appear naturally in the gold standard and
   should NOT be stripped from your output:

   - 'wherein', 'whence', 'whither', 'thither', 'hereby', 'thereby',
     'thereof', 'wherewithal'
   - 'hath' (3rd person sg. of 'have'), 'doth' (3rd person sg. of
     'do'), particularly in scriptural and credal contexts
   - 'whilst' (interchangeable with 'while')
   - 'shall' for first-person future, 'will' for resolved intention

   Still FORBIDDEN (do not introduce these regardless of style):
   - 'vouchsafed', 'verily', 'thee', 'thou', 'thy', 'thine'
   - 'whereunto', 'betwixt', 'hither', 'thence'
   - inverted word order ('him spoke', 'spoke he')
   - pseudo-KJV cadence not modelled in the gold standard

   When in doubt: ask whether the construction would read naturally
   in a Victorian scholarly translation. If yes, use it; if it would
   read as deliberately archaic Tudor-ish or KJV-imitative, do not.

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
   Three sub-rules bundling related stylistic adjustments. All three
   serve the same principle: when literal mirroring of Latin syntax
   produces clumsy or unidiomatic English, prefer the natural English
   form — Parker Society does, and matching its register requires the
   same flexibility.

   7a. AUTHORIAL FIRST-PERSON IS SINGULAR. In single-author works
   like this one, Latin first-person plural verbs and pronouns
   referring to the author render in English as first-person
   singular ('I', 'me', 'my', 'mine'), not plural ('we', 'our'):
     'ponemus' -> 'I will lay' (not 'we will lay')
     'iudicamus' -> 'I judge' / 'I think' (not 'we judge')
     'affirmamus' -> 'I affirm' (not 'we affirm')
     'nobis nulla controuerſia eſt' -> 'there is no controversy
        on my part' or 'I do not dispute…'
   EXCEPTION: when the Latin plural clearly refers to a group
   including the author (e.g. 'nos omnes', 'nos Reformati', 'we
   the Reformed'), keep the English plural.

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

   7c. VOICE FLEXIBILITY. Choose active or passive voice based on
   English idiom and discourse focus, not mechanical mirroring of
   Latin syntax. This SUPERSEDES the inherited v1 lexicon hint that
   directed strict active-voice rendering. When the discourse topic
   is the patient rather than the agent, English passive is often
   preferred:
     'Scripturas Papiſtæ celebrant' (topic: scriptures) -> 'the
        scriptures are praised by the papists' (passive — topic
        first), NOT 'the Papists celebrate the Scriptures' (active
        — agent first) when the surrounding discourse is about
        the scriptures.
   Active remains the default for narrative and where the agent IS
   the topic."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Whitaker v2 translation prompt.

    Same signature as v0/v1/v2/v3/v4/whitaker so the runner can dispatch
    without code changes. Section order:

    1. Translator brief
    2. Page identifier
    3. Hard rules (numbered, always present)
    4. Lexicon hints (selected by lexicon_profile)
    5. Body lines
    6. Linked footnotes
    7. Requested unit IDs
    8. Optional extra context
    9. Output contract
    """

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
