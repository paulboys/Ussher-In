"""Whitaker — translation prompt for *Disputatio de Sacra Scriptura*.

Built on v1 (``translation_prompts``) — its lexicon hints, output
contract, and helper functions are reused verbatim. The structural
reorganization comes from v2 (translator brief / hard rules / lexicon
hints, in that order), because the numbered hard-rules block makes
cross-cutting directives easier for the model to obey consistently.

The Whitaker corpus differs from Ussher's *Antiquitates* in one way
that materially affects the prompt: Whitaker quotes Greek without
routinely paraphrasing it into Latin in the same or adjacent clause.
v2's Hard Rule #1 (carry the Greek through verbatim and translate
only the Latin gloss) therefore does not apply here. The replacement
rule below requires the model to **always** preserve the Greek
verbatim AND supply an English translation in square brackets — no
search for an adjacent Latin paraphrase, no skipping the English on
the assumption that the surrounding Latin is already glossing.

Public surface mirrors ``translation_prompts`` and
``translation_prompts_v2`` so the runner can dispatch by edition
without code changes:

* ``build_translation_prompt(...)``
* ``LEXICON_LATIN_HINTS``
* ``LEXICON_GREEK_HINTS``
* ``OUTPUT_CONTRACT``
* ``LEXICON_PROFILES``
* ``contains_greek``
"""

from __future__ import annotations

from typing import Sequence

# Reuse v1 lexicon content and mechanical helpers. v1 is the
# best-performing baseline; the lexicon priorities apply equally to
# Whitaker's 16th-century scholastic Latin and Patristic Greek.
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
    "(1588). Source language is 16th-century scholastic Latin with "
    "Patristic and Hellenistic Greek citations embedded throughout. "
    "Your goal is clear modern scholarly English that preserves "
    "Whitaker's argument and citations precisely. The Hard Rules "
    "below are stricter than the Lexicon Hints; when they conflict, "
    "follow the Hard Rules."
)


# ---------------------------------------------------------------------------
# Hard rules — cross-cutting directives the model must apply per line
# ---------------------------------------------------------------------------
#
# Numbered (not bulleted) so the model can cite a specific rule in its
# 'notes' field if it has to override one. Order is rough priority:
# correctness rules first, formatting rules second.

HARD_RULES = """\
Hard rules (apply every one to every line; if a rule conflicts with
the lexicon hints, the rule wins):

1. GREEK PRESERVATION + TRANSLATION.
   Whenever Greek script appears in a body line or footnote, preserve
   the Greek verbatim in your English output (with its polytonic
   accents, breathings, and iota subscript intact), and immediately
   follow it with a concise English translation in square brackets.
   Both the Greek and the English MUST appear in the output.
   Do NOT replace the Greek with English alone.
   Do NOT search for or rely on adjacent Latin paraphrase: even if
   the Latin appears to gloss the Greek, still supply your own
   English translation of the Greek in square brackets.
   Example shape: 'as Origen says, ὁ λόγος αὐτοῦ τρέχει ταχέως
   [his word runs swiftly], and...'.

2. MODERN ENGLISH REGISTER. No archaisms. Specifically forbidden:
   vouchsafed, thee, thou, thy, verily, whereunto, whilst, betwixt,
   hath, doth, dost, ye, hither, thence. Use the plain modern
   equivalent (granted, you, your, truly, to which, while, between,
   has, does, do, you, here, then). Avoid pseudo-KJV cadence and
   inverted word order ('him spoke' / 'spoke he').

3. PROPER-NOUN NORMALIZATION. Render well-known historical and
   ecclesiastical proper nouns in their conventional modern English
   form, not the source spelling. Examples: 'Bellarminus' ->
   'Bellarmine'; 'Stapletonus' -> 'Stapleton'; 'Hieronymus' ->
   'Jerome'; 'Augustinus' -> 'Augustine'; 'Theodoretus' ->
   'Theodoret'; 'Cæsariis' -> 'Caesar'. Less-familiar names (obscure
   persons, minor places) keep the source spelling; when uncertain,
   keep the source spelling and note the choice in 'notes'.

4. BOOK AND TREATISE TITLES. When the source names a Latin or Greek
   work — typically signposted by 'libro [N]', 'liber X', 'in
   [topic] book', 'contra [author]', or a Greek genitive title —
   render the English title in italics-style quotation marks and
   capitalize as a title (e.g. '"Against Jovinian"', '"On
   Christian Doctrine"'). Do not dissolve a cited title into
   ordinary prose.

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
    """Assemble the Whitaker translation prompt.

    Same signature as v0/v1/v2 so the runner can dispatch to any
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
