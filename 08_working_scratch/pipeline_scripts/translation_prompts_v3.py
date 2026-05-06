"""V3 — REVIEW-INFORMED REFINEMENT of the translation prompt.

Purpose
-------
v2 was a structural rewrite of v0/v1 that promoted cross-cutting hard
rules above the lexicon block and introduced a Greek-paraphrase rule.
The first themistogenes-led trilinear review of p0039
(``04_translation_work/ab/p0039/trilinear_run01_p39_reviewed.md``)
validated the v2 architecture but surfaced a cluster of accuracy
regressions and missed opportunities. v3 keeps v2's structure and
codifies the review's findings as new or revised hard rules.

Headline deltas vs. v2
----------------------
1. Greek handling moves from "drop the Greek when Latin paraphrase is
   present" to a three-slot interlinear structure:
     Greek (verbatim) + ⟦English⟧ + optional ⟪Latin⟫
   The English slot is ALWAYS emitted; Ussher's Latin (when present)
   is preserved verbatim in the second slot. We use mathematical white
   square brackets (U+27E6/U+27E7) and white curly brackets
   (U+27EA/U+27EB) instead of ``[`` / ``[[`` to avoid colliding with
   the scholarly convention of ``[ ]`` for editorial supplements.
2. v2's "PROPER-NOUN NORMALIZATION" rule (which directed the model to
   modernize forms like ``Antiocheni`` -> ``of Antioch``) is replaced
   by a stricter "PRESERVE SOURCE FORMS WITH PARENTHETICAL GLOSS"
   rule. Orthographic/morphological normalization of the SAME name
   stays allowed; substituting a DIFFERENT toponym, epithet, or
   biographical identifier (the ``Uticensis`` -> ``Saint-Évroul`` move
   that both v0 and v2 made) is now explicitly forbidden.
3. New rules codify findings the review made line by line:
     - filiation genitives (``Eusebius Pamphili`` is a relation, not a
       compound name)
     - indirect-statement scaffolding (``That…``)
     - impersonal constructions (``legitur`` -> ``it is read that…``)
     - natural English word order for ablative-of-agent + PPP
     - cross-page context (use ``Previous page tail:`` /
       ``Next page head:`` material when present in extra_context to
       stitch tokens broken at page boundaries)
     - footnotes use a hybrid policy: preserve original-language
       book/work titles, translate everything else
4. Archaism list grows by ``tarried`` (caught at l0030).
5. Polysemy guidance picks up ``civitates`` -> ``communities`` when
   juxtaposed to specific cities/regions.
6. ``OUTPUT_CONTRACT`` gains a clause about the bracket characters
   ⟦⟧/⟪⟫ being semantically meaningful and an ``audit-trail`` clause
   asking the model to record preservation rationale in ``notes``.

Public surface
--------------
Identical to ``translation_prompts_v0`` and ``translation_prompts_v2``:

* ``build_translation_prompt(...)``
* ``LEXICON_LATIN_HINTS``
* ``LEXICON_GREEK_HINTS``
* ``OUTPUT_CONTRACT``
* ``LEXICON_PROFILES``
* ``contains_greek``
* ``HARD_RULES``
* ``TRANSLATOR_BRIEF``

Mechanical helpers (``_inject_markers``, ``_format_body_lines``, etc.)
are imported from the live v1 module rather than duplicated; they have
no v3-specific semantics so drift between v3 and v1 helpers is
impossible.
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
# Lexicon hints
# ---------------------------------------------------------------------------

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
  ratio, manus, ius, virtus, civitates, etc.), pick the sense the
  surrounding clause requires rather than the most literal or most
  common gloss. Examples:
    * 'res' in a military context renders as 'campaign' or
      'operation', not 'thing' or 'action'.
    * 'gentes' in an ecclesiastical context renders as 'peoples', not
      'nations'.
    * 'civitates' juxtaposed to specific cities and regions (e.g.
      Rome, Britain) renders as 'communities', not 'cities'.
- Voice: render Latin active verbs in English active voice; do not
  silently passivize (e.g., 'lateat' = 'lies hidden', not 'is hidden').
  Switch to passive only when English idiom genuinely requires it.
- Technical liturgical/ecclesiastical vocabulary (menologia, synaxaria,
  martyrologia, breviarium, etc.) is preserved per Hard Rule 2 (source
  form + parenthetical gloss on first occurrence).
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

HARD_RULES = """\
Hard rules (apply every one to every line; if a rule conflicts with
the lexicon hints, the rule wins):

1. EMBEDDED GREEK — THREE-SLOT STRUCTURE.
   Every Greek passage in your output emits up to three slots, in this
   order:
     (a) The Greek itself, preserved verbatim and untranslated.
     (b) An English translation of the Greek, in literal MATHEMATICAL
         WHITE SQUARE BRACKETS: ⟦English here⟧ (U+27E6 ... U+27E7).
         ALWAYS emit this slot, even when Ussher also supplies a Latin
         translation of the Greek.
     (c) IF AND ONLY IF Ussher follows the Greek with his own Latin
         rendering of it, preserve that Latin verbatim and
         untranslated in literal MATHEMATICAL WHITE CURLY BRACKETS:
         ⟪Latin here⟫ (U+27EA ... U+27EB). Do NOT translate the Latin
         in this slot.

   How to recognize an Ussher Latin rendering of the Greek: the Latin
   immediately follows the Greek; its sense visibly mirrors the Greek;
   it may be introduced by 'id est', 'hoc est', 'inquit', 'sive', or
   simply by adjacency. If the following Latin is ordinary continuing
   prose (not a translation of the Greek), do NOT wrap it in ⟪⟫ —
   translate it normally.

   Bracket discipline is load-bearing: ⟦⟧ = English gloss, ⟪⟫ =
   preserved Latin. Do not interchange. Do not nest. Do not omit the
   English slot just because the Latin slot is present. Do not use
   plain ASCII brackets [ ] or [[ ]] for these slots — those are
   reserved for editorial-insertion conventions and must remain
   unambiguous.

   Example shape:
     Ὕστερον δὲ ἐν Βρετανίᾳ γενόμενος ⟦And at a later time, having
     gone to Britain⟧ ⟪Postremo in Britanniam profectus⟫

2. PRESERVE SOURCE FORMS WITH PARENTHETICAL GLOSS.
   For toponyms, ethnonyms, biographical epithets, technical terms,
   and proper names whose modern English form is not unambiguous,
   retain the Latin (or Greek) form as printed, then supply a
   clarifying gloss in parentheses on first occurrence.

   Examples:
     'Hiberi' -> 'Hiberi (Iberians)'
     'Hibernis' -> 'Hibernis (the Irish)'
     'Hiberniam' -> 'Hibernia (Ireland)'
     'menologiis' -> 'menologia (liturgical calendars)'
     'Uticensis' -> 'Uticensis (i.e., the monk of Saint-Évroul)'

   ALLOWED: orthographic and morphological normalization of an
   unambiguous name — e.g., 'Boadicia' -> 'Boudica', 'Antiocheni' ->
   'of Antioch', 'Æthiopas' -> 'Ethiopians'. These are spelling/
   inflection adjustments to the SAME name, not substitutions.

   FORBIDDEN: substituting a different toponym, epithet, or
   biographical identifier that you think is more recognizable to a
   modern reader, even when historically defensible. 'Uticensis' ->
   'Saint-Évroul' is forbidden (different toponym). 'Vincentius' ->
   'Vincent' is forbidden when context does not disambiguate which
   Vincent is meant.

   Default when uncertain: preserve the source form, gloss in parens,
   and set uncertain=true with a brief note.

3. FILIATION GENITIVES ARE NOT SECOND NAMES.
   Latin patronymic/mentor genitives like 'Eusebius Pamphili' name a
   relation, not a compound name: 'Eusebius of Pamphilus' (the
   disciple/protégé of Pamphilus), not 'Eusebius Pamphili'. Apply
   the same logic to similar 'X-i / X-ii' patterns where a second
   personal name appears in the genitive.

4. INDIRECT-STATEMENT SCAFFOLDING.
   When the Latin uses accusative + infinitive (acc. subject of an
   infinitive verb governed by a verb of saying, knowing, reporting),
   render it in English with explicit subordination — typically
   'That X did Y' or 'X is said to have done Y'. Do not drop the
   'That…' scaffolding when the governing verb is several clauses
   away; the reader needs the marker.

5. IMPERSONAL CONSTRUCTIONS.
   Translate Latin impersonal verbs impersonally:
     'legitur' -> 'it is read that…' (NOT 'he is read to have…')
     'dicitur' -> 'it is said that…'
     'traditur' -> 'it is handed down that…'
   Reserve personal constructions for cases where the Latin itself is
   personal.

6. NATURAL ENGLISH WORD ORDER FOR COMMON LATIN PATTERNS.
   Some Latin constructions track poorly when rendered in source
   order. Reorder for natural English:
     - ablative-of-agent + perfect passive participle: 'ab infidelibus
       crucifixus' -> 'crucified by the unbelievers' (PPP first, agent
       phrase after).
     - Heavy ablative absolutes: prefer an English subordinate clause
       ('after he had X-ed…') over a literal participial echo.
   Otherwise, prefer to preserve Latin word order where it reads
   acceptably in English (this often improves emphasis fidelity).

7. MODERN ENGLISH REGISTER. No archaisms. Specifically forbidden:
   vouchsafed, thee, thou, thy, verily, whereunto, whilst, betwixt,
   hath, doth, dost, ye, hither, thence, tarried. Use the plain modern
   equivalent (granted, you, your, truly, to which, while, between,
   has, does, do, you, here, then, remained). Avoid pseudo-KJV cadence
   and inverted word order ('him spoke' / 'spoke he').

8. BOOK AND TREATISE TITLES.
   When the source names a Latin or Greek work — typically signposted
   by 'libro [N]', 'liber X', 'in [topic] book', or a Greek genitive
   title — render the English title in quotation marks and capitalize
   as a title (e.g. '"Ecclesiastical History"', '"Synopsis"'). Do not
   dissolve a cited title into ordinary prose.

9. CROSS-PAGE CONTEXT.
   If the input includes 'Previous page tail:' or 'Next page head:'
   material in the Additional page context section, USE IT to resolve
   sentences and tokens that begin or end mid-word at a page boundary.
   Diagnostic signals: a body line beginning with a partial token like
   'rum', 'que', 'tatis' (lowercase syllable, not a Latin word); a
   body line ending with a hyphen-broken word; a finite verb whose
   subject is established only on the previous page. Stitch these
   silently in the English; never invent a stitched word the source
   doesn't supply.

10. FOOTNOTE TRANSLATION POLICY.
    Footnotes use a HYBRID rule:
      - Preserve the original-language form of book/work titles
        exactly as printed (Latin, Greek, abbreviated). Do not
        translate them. Do not anglicize their spelling.
      - Translate everything else: glosses, citations, locators
        ('vol. 2', 'page 406', 'year 1598', 'on the 29th day of
        June'), connective prose ('on which see…', 'concerning
        which…'), and editorial commentary.

    Example:
      Latin: 'Niceph. hist. ecclesiast. lib. 2. cap. 40.'
      v3:    'Niceph. hist. ecclesiast., book 2, chapter 40.'

11. FOOTNOTE-MARKER SENTINELS. Body lines may contain '^X' (caret
    followed by a single letter or symbol). That mark locates a
    printed superscript footnote anchor in the source. Translate the
    body line WITHOUT echoing the caret or the marker symbol in the
    English; marker placement into the English is handled by a
    separate downstream pass. The caret character ('^') is reserved
    for this sentinel and never appears as ordinary punctuation.

12. SUBJECT CONTINUITY. When a line carries a third-person verb whose
    subject was established earlier in the batch (or, per Rule 9, on
    the previous page), keep the subject reference clear. If ambiguity
    is high (antecedent several lines earlier, multiple candidates
    intervene), insert a short clarifying parenthetical naming the
    antecedent on first occurrence (e.g. 'the same man (Simon)…')."""


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
                 choices, preservation decisions per Rule 2, or
                 unresolved tokens; empty string if none>",
      "uncertain": <bool>
    }
  }
}

Rules:
- Include exactly one entry per requested unit (body line_id and
  footnote_id provided in the input). Do not invent IDs.
- 'english' MUST be a modern English translation per the Hard Rules.
  In particular: apply Rule 1 (Greek three-slot structure with literal
  ⟦⟧ and ⟪⟫ characters in the string), Rule 2 (preserve + gloss),
  Rule 10 (footnote hybrid policy).
- The literal characters ⟦ ⟧ ⟪ ⟫ (U+27E6, U+27E7, U+27EA, U+27EB)
  inside 'english' are semantically meaningful per Rule 1; do not
  substitute plain ASCII brackets, do not HTML-escape, do not strip.
  JSON allows these characters in string values without escaping.
- If a unit cannot be translated confidently, return your best
  attempt, set uncertain=true, and explain the issue in 'notes'.
- When you preserve a source form per Rule 2 instead of normalizing,
  briefly note WHY in 'notes' (e.g., 'preserved Vincentius — multiple
  historical referents possible'). This produces an audit trail for
  the reviewer.
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
    "that preserves Ussher's argument, citations, and the texture of "
    "his sources precisely.\n\n"
    "Two operating principles override every other instinct:\n\n"
    "A. PRESERVE BEFORE YOU EXPLAIN. When in doubt between a faithful "
    "rendering of what the Latin literally says and a smoother "
    "rendering that imports outside knowledge, prefer the faithful "
    "rendering and clarify (if at all) with a parenthetical gloss. "
    "Never silently substitute one term, name, place, or epithet for "
    "another that you happen to recognize.\n\n"
    "B. TRANSLATE THE PAGE, NOT THE PERSON. Ussher's text reflects "
    "his sources and his era. If a name, epithet, or fact looks "
    "'wrong' by modern biographical knowledge, translate the Latin "
    "as written. Do not correct, modernize, or harmonize on the "
    "author's behalf.\n\n"
    "The Hard Rules below are stricter than the Lexicon Hints; when "
    "they conflict, follow the Hard Rules."
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
    """Assemble the v3 translation prompt.

    Same signature as v0/v1/v2 so the A/B runner can dispatch to any
    version without code changes. Order of sections (top-down):

    1. Translator brief
    2. Page identifier
    3. Hard rules (always present, numbered)
    4. Lexicon hints (selected by ``lexicon_profile``)
    5. Body lines
    6. Linked footnotes
    7. Requested unit IDs
    8. (optional) extra context — when the runner provides cross-page
       'Previous page tail:' / 'Next page head:' material it lands
       here, and Hard Rule 9 instructs the model to consume it.
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
