"""V4 — REPURPOSED FOR USSHER. Not the Whitaker baseline.

ROUTING NOTE (2026-05-16)
-------------------------
v4 was originally drafted as the Whitaker baseline. During Phase 0
prerequisite investigation for the whitaker_ch1 optimization plan
(see ``04_translation_work/ab/whitaker_ch1/plan.md``), we discovered
that ``translation_prompts_whitaker.py`` already exists with a
Whitaker-correct Rule 1 (Greek + English-in-square-brackets; no
Latin-paraphrase assumption). v4's Rule 1 was inherited from the
Ussher pattern (Greek followed by author's Latin gloss) and is wrong
for Whitaker.

Decision: v4 is retained as a candidate prompt for the **Ussher**
exercise, where its Latin-preservation insight genuinely applies.
``translation_prompts_whitaker.py`` is the Whitaker baseline.

The Parker-Society register notes in v4's TRANSLATOR_BRIEF and Rule 2
are Whitaker-specific and would need replacement when v4 is brought
forward to the Ussher exercise.

Original purpose
----------------
V2 ADAPTED FOR WHITAKER with Greek-paraphrase rule clarified.

Purpose
-------
v2 is the performance baseline: in the p0041 A/B test it beat v3
decisively on fluency, accuracy, and register — the rubrics that matter
most for readable scholarly translation.

v3 introduced a three-slot bracket structure (⟦⟧/⟪⟫) that improved
format_compliance and source_preservation scores but at severe cost to
fluency, accuracy, and register — a net loss. v4 abandons the bracket
apparatus entirely.

The one genuine insight from v3 worth keeping: v2's Rule 1 said "render
only the Latin" when Whitaker follows a Greek quote with his own Latin
rendering. That wording was ambiguous — it could be read as "translate
the Latin into English." v3 showed the correct behaviour is to preserve
the author's Latin verbatim (not translate it), because it is his own
authoritative gloss. v4 adds that single clarification to Rule 1.

v4 also updates the TRANSLATOR_BRIEF for the Whitaker corpus and adjusts
Rule 2 to target the register of the 1849 Parker Society English
translation (William Fitzgerald, tr.), the gold standard for this
corpus. That translation uses formal Victorian scholarly English with
occasional period constructions. Blanket-forbidding those constructions
would cause systematic divergence from the gold standard on register
rubrics.

Headline deltas vs. v2
----------------------
1. TRANSLATOR_BRIEF rewritten for Whitaker's Disputatio de Sacra
   Scriptura (1690 Latin edition), goal set to match the register and
   rendering choices of the 1849 Parker Society English translation
   (William Fitzgerald, tr.).
2. Hard Rule 1 gains one sentence: the adjacent Latin is to be preserved
   verbatim in the output, not translated into English.
3. Hard Rule 2 (register) is softened from "no archaisms" to "match the
   Parker Society register" — Fitzgerald's translation uses formal
   Victorian scholarly English with occasional period constructions
   (e.g. 'hath') that must not be systematically excluded.
4. All other rules, lexicon hints, output contract, and builder logic are
   unchanged from v2.

Public surface
--------------
Identical to v0/v2/v3:

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

from translation_prompts import (
    LEXICON_PROFILES,
    _build_marker_lookup,
    _format_body_lines,
    _format_footnotes,
    _format_unit_ids,
    _inject_markers,
    contains_greek,
)


# ---------------------------------------------------------------------------
# Lexicon hints — unchanged from v2
# ---------------------------------------------------------------------------

LEXICON_LATIN_HINTS = """\
Latin lexical priorities (late 16th-century Protestant scholastic usage):
- Treat senses, idioms, and orthography as belonging to early-modern
  scholarly Latin first; classical-only readings are a fallback.
- Primary authorities for sense disambiguation:
    * Forcellini, Totius Latinitatis Lexicon (general
      classical-through-humanist range as understood in Whitaker's milieu).
    * Du Cange, Glossarium Mediae et Infimae Latinitatis
      (post-classical, ecclesiastical, juridical, and liturgical
      vocabulary).
- Fallback (only when post-classical reading is contextually
  unsupported): Lewis & Short for classical baseline.
- Polysemous nouns: for high-polysemy words (res, gens, lex, sermo,
  ratio, manus, ius, virtus, etc.), pick the sense the surrounding
  clause requires rather than the most literal or most common gloss.
  Examples: 'res' in a polemical context renders as 'matter' or 'point';
  'gentes' in an ecclesiastical context renders as 'peoples', not
  'nations'.
- Voice: render Latin active verbs in English active voice; do not
  silently passivize (e.g., 'lateat' = 'lies hidden', not 'is hidden').
  Switch to passive only when English idiom genuinely requires it.
- Do NOT quote or paraphrase lexicon entries verbatim. Use them only
  to choose the correct sense.
- Preserve early-modern orthography and ligatures (æ, œ, long-s) when
  echoing source tokens; render them in modernized form only in the
  English translation."""

LEXICON_GREEK_HINTS = """\
Greek lexical priorities (Patristic-era quotations are dominant):
- Treat citations as Patristic Greek first; Roman/Byzantine and
  classical readings are fallbacks.
- Primary authority:
    * Lampe, A Patristic Greek Lexicon (theological and
      ecclesiastical senses).
- Secondary fallbacks:
    * Sophocles, Greek Lexicon of the Roman and Byzantine Periods.
    * LSJ (Liddell-Scott-Jones) only for residual classical senses.
- Patristic theological vocabulary: in evangelical/ecclesiastical
  contexts, νόμος and ἐντολή typically mean 'teaching' or 'precept',
  not 'statute' or 'law' in the legal sense (e.g., νόμος εὐαγγελικός
  = 'the teaching of the Gospel', not 'the evangelical law'). Prefer
  the theological sense unless a legal/Mosaic sense is explicit.
- Preserve polytonic accents, breathings, and iota subscript exactly
  as printed when echoing the source; transliterate only inside notes
  if needed.
- Do NOT quote or paraphrase lexicon entries verbatim."""


# ---------------------------------------------------------------------------
# Hard rules
# ---------------------------------------------------------------------------

HARD_RULES = """\
Hard rules (apply every one to every line; if a rule conflicts with
the lexicon hints, the rule wins):

1. EMBEDDED GREEK WITH ADJACENT LATIN PARAPHRASE.
   Whitaker routinely quotes a Greek source and then paraphrases it
   into Latin in the same or adjacent clause. When that pattern is
   present, the correct editorial behaviour is to LEAVE THE GREEK
   UNTRANSLATED in your English (carry the Greek through verbatim)
   and PRESERVE WHITAKER'S LATIN RENDERING VERBATIM — do not translate
   that Latin into English. Whitaker's own Latin is his authoritative
   gloss; replacing it with your English rendering substitutes your
   voice for his. The Latin appears in your 'english' field as printed.
   Signals that Latin paraphrase is present: quotation marks around
   or just after the Greek; a Latin clause whose meaning visibly
   echoes the Greek; connectives like 'id est', 'hoc est', 'sive',
   'inquit' near the Greek.
   When Greek stands alone with no Latin paraphrase nearby (the
   Greek itself carries the substantive content), translate it
   normally or supply a brief English gloss in square brackets.

2. REGISTER — MATCH THE 1849 PARKER SOCIETY TRANSLATION. Target the
   register of the 1849 Parker Society English translation of the
   Disputatio de Sacra Scriptura (William Fitzgerald, tr.; the gold
   standard for this corpus). That translation uses formal Victorian
   scholarly English with Latinate vocabulary and occasional period
   constructions (e.g. 'hath', 'which are to be found'). Do not
   introduce archaisms gratuitously, but do not strip constructions
   that appear naturally in the gold standard. Avoid pseudo-KJV cadence
   and inverted word order ('him spoke' / 'spoke he') unless modelled
   in the Parker Society translation. Specifically avoid: vouchsafed,
   thee, thou, thy, verily, whereunto, betwixt, ye, hither, thence.

3. PROPER-NOUN NORMALIZATION. Render well-known historical and
   ethnographic proper nouns in their conventional modern English
   form, not the source spelling. Examples: 'Boadicia' -> 'Boudica';
   'Cæsariis' -> 'Caesar'; 'Antiocheni' -> 'of Antioch';
   'Theodoretus' -> 'Theodoret'; 'Æthiopas' -> 'Ethiopians'.
   Less-familiar names (obscure persons, minor places) keep the
   source spelling; when uncertain, keep the source spelling and
   note the choice in 'notes'.

4. BOOK AND TREATISE TITLES. When the source names a Latin or Greek
   work — typically signposted by 'libro [N]', 'liber X', 'in
   [topic] book', or a Greek genitive title — render the English
   title in italics-style quotation marks and capitalize as a title
   (e.g. '"On the Cure of the Greek Maladies"', '"On the Sufferings
   of the Martyrs"'). Do not dissolve a cited title into ordinary
   prose.

5. SUBJECT CONTINUITY ACROSS LINES. When a line carries a third-
   person verb whose subject was established in an earlier line of
   the same batch, keep the subject reference clear. If ambiguity
   is high (antecedent several lines earlier, multiple candidates
   intervene), insert a short clarifying parenthetical naming the
   antecedent on first occurrence (e.g. 'he (Bellarmine) argues
   that...').

6. FOOTNOTE-MARKER SENTINELS. Body lines may contain '^X' (caret
   followed by a single letter or symbol). That mark locates a
   printed superscript footnote anchor in the source. Translate the
   body line WITHOUT echoing the caret or the marker symbol in the
   English; marker placement into the English is handled by a
   separate downstream pass. The caret character ('^') is reserved
   for this sentinel and never appears as ordinary punctuation."""


# ---------------------------------------------------------------------------
# Strict output contract — Rule 1 reference updated
# ---------------------------------------------------------------------------

OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "translations": {
    "<line_id_or_footnote_id>": {
      "english": "<rendering in the register of the 1849 Parker Society English translation>",
      "notes": "<short note for lexical uncertainty, era-sense
                 choices, or unresolved tokens; empty string if none>",
      "uncertain": <bool>
    }
  }
}

Rules:
- Include exactly one entry per requested unit (body line_id and
  footnote_id provided in the input). Do not invent IDs.
- 'english' MUST follow the Hard Rules. In particular: apply Rule 1
  (Greek-paraphrase: carry Greek verbatim and preserve any adjacent
  Whitaker Latin verbatim — do not translate it) and Rule 3
  (proper-noun normalization).
- If a unit cannot be translated confidently, return your best
  attempt, set uncertain=true, and explain the issue in 'notes'.
- Do not echo lexicon entries verbatim under any circumstances."""


# ---------------------------------------------------------------------------
# Translator brief — rewritten for Whitaker
# ---------------------------------------------------------------------------

TRANSLATOR_BRIEF = (
    "You are translating reviewed lines from William Whitaker's "
    "Disputatio de Sacra Scriptura contra R. Bellarminum (1690 Latin "
    "edition). Source language is late 16th-century Protestant "
    "scholastic Latin, with Patristic and biblical Greek citations "
    "embedded throughout. Your goal is to produce English that matches "
    "the register and rendering choices of the 1849 Parker Society "
    "English translation of this work (William Fitzgerald, tr.) — "
    "formal Victorian scholarly English with Latinate vocabulary, "
    "faithful to Whitaker's argumentative structure and his handling "
    "of cited sources. The Hard Rules below are stricter than the "
    "Lexicon Hints; when they conflict, follow the Hard Rules."
)


# ---------------------------------------------------------------------------
# Prompt builder — unchanged from v2
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the v4 translation prompt.

    Same signature as v0/v2/v3 so the A/B runner can dispatch to any
    version without code changes. Order of sections (top-down):

    1. Translator brief
    2. Page identifier
    3. Hard rules (always present, numbered)
    4. Lexicon hints (selected by ``lexicon_profile``)
    5. Body lines
    6. Linked footnotes
    7. Requested unit IDs
    8. (optional) extra context
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
