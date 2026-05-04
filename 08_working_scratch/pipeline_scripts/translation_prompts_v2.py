"""V2 — STRUCTURAL REWRITE of the translation prompt.

Purpose
-------
v0 is the pre-refinement baseline. v1 added a handful of useful
directives (active voice, polysemy, archaism, proper nouns, titles,
subject continuity, theological vocabulary), but it added them as
patches grafted onto v0's structure: new bullets buried inside the
Latin-lexicon block, new paragraphs interleaved between the body and
output-contract sections, etc. The result was that the new content
competed with v0's existing content for prominence and was obeyed
inconsistently.

v2 keeps the same *content* as v1 but reorganizes it into three
top-level sections:

1. Translator brief — one paragraph naming the work, era, and goal.
2. Hard rules — a numbered list (≤8) of cross-cutting directives the
   model must apply to every line, including the Greek-paraphrase
   rule discovered during the p0039 spot-check (which neither v0 nor
   v1 encoded).
3. Lexicon hints — lexicographic content only (lexica priorities,
   polysemy guidance, theological vocabulary). No style guidance.

Style and lexicon are now in different sections at different prompt
levels. The hard-rules section is short, numbered, and placed before
the bulky lexicon block so it gets read first.

Public surface
--------------
Identical to ``translation_prompts`` and ``translation_prompts_v0``:

* ``build_translation_prompt(...)``
* ``LEXICON_LATIN_HINTS``
* ``LEXICON_GREEK_HINTS``
* ``OUTPUT_CONTRACT``
* ``LEXICON_PROFILES``
* ``contains_greek``

Helpers (``_inject_markers``, ``_format_body_lines``, etc.) are
imported from the live v1 module rather than duplicated, since they
are mechanical and have no v2-specific semantics. Drift between v2
and v1 helpers is therefore impossible.
"""

from __future__ import annotations

from typing import Sequence

# Reuse mechanical helpers from v1. These are tested under v1's suite
# and have no version-specific behavior — they format body lines,
# inject footnote-marker carets, etc.
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
# Lexicon hints — LEXICOGRAPHIC CONTENT ONLY
# ---------------------------------------------------------------------------
#
# Style/register guidance that lived inside the v1 Latin block has been
# lifted out into the Hard Rules section below so it isn't competing with
# sense-disambiguation bullets for the model's attention.

LEXICON_LATIN_HINTS = """\
Latin lexical priorities (17th-century ecclesiastical/humanist usage):
- Treat senses, idioms, and orthography as belonging to early-modern
  scholarly Latin first; classical-only readings are a fallback.
- Primary authorities for sense disambiguation:
    * Forcellini, Totius Latinitatis Lexicon (general
      classical-through-humanist range as understood in Ussher's milieu).
    * Du Cange, Glossarium Mediae et Infimae Latinitatis
      (post-classical, ecclesiastical, juridical, and liturgical
      vocabulary).
- Fallback (only when post-classical reading is contextually
  unsupported): Lewis & Short for classical baseline.
- Polysemous nouns: for high-polysemy words (res, gens, lex, sermo,
  ratio, manus, ius, virtus, etc.), pick the sense the surrounding
  clause requires rather than the most literal or most common gloss.
  Examples: 'res' in a military context renders as 'campaign' or
  'operation', not 'thing' or 'action'; 'gentes' in an ecclesiastical
  context renders as 'peoples', not 'nations'.
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
# Hard rules — cross-cutting directives the model must apply per line
# ---------------------------------------------------------------------------
#
# Numbered (not bulleted) so the model can cite a specific rule in its
# 'notes' field if it has to override one. Order is rough priority:
# correctness rules first, formatting rules second.

HARD_RULES = """\
Hard rules (apply every one to every line; if a rule conflicts with
the lexicon hints, the rule wins):

1. EMBEDDED GREEK WITH ADJACENT LATIN PARAPHRASE.
   Ussher routinely quotes a Greek source and then paraphrases it
   into Latin in the same or adjacent clause. When that pattern is
   present, the correct editorial behavior is to LEAVE THE GREEK
   UNTRANSLATED in your English (carry the Greek through verbatim)
   and render only the Latin. The Latin already serves as Ussher's
   gloss; double-translating produces redundant English.
   Signals that Latin paraphrase is present: quotation marks around
   or just after the Greek; a Latin clause whose meaning visibly
   echoes the Greek; connectives like 'id est', 'hoc est', 'sive',
   'inquit' near the Greek.
   When Greek stands alone with no Latin paraphrase nearby (the
   Greek itself carries the substantive content), translate it
   normally or supply a brief English gloss in square brackets.

2. MODERN ENGLISH REGISTER. No archaisms. Specifically forbidden:
   vouchsafed, thee, thou, thy, verily, whereunto, whilst, betwixt,
   hath, doth, dost, ye, hither, thence. Use the plain modern
   equivalent (granted, you, your, truly, to which, while, between,
   has, does, do, you, here, then). Avoid pseudo-KJV cadence and
   inverted word order ('him spoke' / 'spoke he').

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
   antecedent on first occurrence (e.g. 'he (Gildas) indicates
   that...').

6. FOOTNOTE-MARKER SENTINELS. Body lines may contain '^X' (caret
   followed by a single letter or symbol). That mark locates a
   printed superscript footnote anchor in the source. Translate the
   body line WITHOUT echoing the caret or the marker symbol in the
   English; marker placement into the English is handled by a
   separate downstream pass. The caret character ('^') is reserved
   for this sentinel and never appears as ordinary punctuation."""


# ---------------------------------------------------------------------------
# Strict output contract
# ---------------------------------------------------------------------------

OUTPUT_CONTRACT = """\
Return ONLY a JSON object (no prose, no code fence) shaped as:

{
  "translations": {
    "<line_id_or_footnote_id>": {
      "english": "<modern English rendering>",
      "notes": "<short note for lexical uncertainty, era-sense
                 choices, or unresolved tokens; empty string if none>",
      "uncertain": <bool>
    }
  }
}

Rules:
- Include exactly one entry per requested unit (body line_id and
  footnote_id provided in the input). Do not invent IDs.
- 'english' MUST be a modern English translation (not a paraphrase
  back into Latin). Apply Hard Rule #1 (Greek-paraphrase) and Hard
  Rule #3 (proper-noun normalization).
- If a unit cannot be translated confidently, return your best
  attempt, set uncertain=true, and explain the issue in 'notes'.
- Do not echo lexicon entries verbatim under any circumstances."""


# ---------------------------------------------------------------------------
# Translator brief
# ---------------------------------------------------------------------------

TRANSLATOR_BRIEF = (
    "You are translating reviewed lines from James Ussher's 1639 "
    "Britannicarum Ecclesiarum Antiquitates (as reissued in the 1847 "
    "Elrington edition). Source language is 17th-century "
    "ecclesiastical/humanist Latin, with Patristic Greek citations "
    "embedded throughout. Your goal is clear modern scholarly English "
    "that preserves Ussher's argument and citations precisely. The "
    "Hard Rules below are stricter than the Lexicon Hints; when they "
    "conflict, follow the Hard Rules."
)


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
    """Assemble the v2 translation prompt.

    Same signature as v0/v1 so the A/B runner can dispatch to any
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
