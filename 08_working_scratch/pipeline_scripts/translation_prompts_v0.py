"""V0 SNAPSHOT — frozen pre-refinement translation prompt.

This module is an exact copy of ``translation_prompts.py`` at git ref
``de5ff00`` (i.e. the parent of commit ``61a7afe`` "prompts: refine
lexical and normalization guidance for translation and polish"). It
exists ONLY for the A/B test of v0 (this file) vs v1 (the live
``translation_prompts`` module) on p0039.

Do not edit. The drift-guard in ``tests/test_prompt_versions.py``
asserts the substantive content here matches v1's ancestor.

Original docstring follows.

Translation prompt assembly for Claude (and other LLM) translation runs.

The prompt is structured around three concerns:

1. Era/lexicon awareness — Ussher's 1639 corpus and the 1847 Elrington
   reissue reflect 17th-century ecclesiastical/humanist Latin and quote
   Patristic-era Greek heavily. Translations should prefer era-appropriate
   senses over classical baselines, while still using classical lexica
   for fallback disambiguation.
2. Whole-page context — even when a request renders a single locked body
   line into English, the model receives the surrounding selected lines
   plus any linked footnotes so cross-line constructions translate
   coherently.
3. Strict output contract — Claude returns one JSON object keyed by
   line_id and footnote_id so the runner can persist append-only
   translation history without lossy free-text parsing.

Lexicon hints are interpretive priorities only: the prompt names the
lexica by authority and era, but never quotes or reproduces entries.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Lexicon hint blocks
# ---------------------------------------------------------------------------

LEXICON_LATIN_HINTS = """\
Latin lexical priorities (17th-century ecclesiastical/humanist usage):
- Treat senses, idioms, and orthography as belonging to early-modern
  scholarly Latin first; classical-only readings are a fallback.
- Primary authorities for sense disambiguation:
    * Forcellini, Totius Latinitatis Lexicon (preferred for general
      classical-through-humanist range as understood in Ussher's milieu).
    * Du Cange, Glossarium Mediae et Infimae Latinitatis (preferred
      for post-classical, ecclesiastical, juridical, and liturgical
      vocabulary).
- Fallback authority (only when post-classical reading is contextually
  unsupported): Lewis & Short for classical baseline.
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
    * Lampe, A Patristic Greek Lexicon (preferred for theological
      and ecclesiastical senses).
- Secondary fallbacks:
    * Sophocles, Greek Lexicon of the Roman and Byzantine Periods.
    * LSJ (Liddell-Scott-Jones) only for residual classical senses.
- Preserve polytonic accents, breathings, and iota subscript exactly
  as printed when echoing the source; transliterate only inside notes
  if needed.
- Do NOT quote or paraphrase lexicon entries verbatim."""

# Detect Greek script presence so we can omit Greek hints when irrelevant.
_GREEK_RANGE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")


def contains_greek(text: str) -> bool:
    """Return True when *text* contains any Greek-block character."""
    return bool(_GREEK_RANGE.search(text or ""))


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
  back into Latin/Greek). Preserve proper nouns; transliterate Greek
  proper nouns conventionally.
- If a unit cannot be translated confidently, return your best
  attempt, set uncertain=true, and explain the issue in 'notes'.
- Do not collapse footnote markers into body text; the body line's
  caret sentinel (e.g. 'Arnobius^y') marks where a footnote attaches
  but the footnote itself is translated under its own footnote_id.
  Translate the body line WITHOUT echoing the caret or the marker
  symbol in the English; marker placement in the English is handled
  by a separate downstream pass.
- Do not echo lexicon entries verbatim under any circumstances."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

LEXICON_PROFILES = ("auto", "latin_only", "latin_greek", "minimal")


def _build_marker_lookup(footnotes: Sequence[dict]) -> dict[str, str]:
    """Map ``footnote_id -> marker_id`` for marker-symbol injection."""
    out: dict[str, str] = {}
    for fn in footnotes:
        fn_id = fn.get("footnote_id")
        marker = fn.get("marker_id")
        if fn_id and marker:
            out[str(fn_id)] = str(marker)
    return out


def _inject_markers(
    text: str,
    markers: Sequence[dict],
    marker_lookup: dict[str, str],
) -> str:
    """Insert ``^<marker_id>`` sentinels into *text* at each marker's
    ``char_offset``.

    Markers without a resolvable ``marker_id`` (e.g. footnote not in
    the current batch) are skipped silently. Offsets are interpreted
    as insertion indices into the ORIGINAL string and applied
    right-to-left so earlier offsets remain valid.
    """
    if not markers:
        return text
    resolved: list[tuple[int, str]] = []
    for m in markers:
        fn_id = m.get("footnote_id")
        offset = m.get("char_offset")
        if fn_id is None or offset is None:
            continue
        marker_symbol = marker_lookup.get(str(fn_id))
        if not marker_symbol:
            continue
        try:
            offset_int = int(offset)
        except (TypeError, ValueError):
            continue
        offset_int = max(0, min(offset_int, len(text)))
        resolved.append((offset_int, marker_symbol))
    if not resolved:
        return text
    resolved.sort(key=lambda pair: pair[0], reverse=True)
    out = text
    for offset_int, marker_symbol in resolved:
        out = out[:offset_int] + "^" + marker_symbol + out[offset_int:]
    return out


def _format_body_lines(
    lines: Sequence[dict],
    marker_lookup: dict[str, str],
) -> str:
    out = []
    for line in lines:
        line_id = line.get("line_id", "")
        text = line.get("text_gold") or line.get("text_ocr_original") or ""
        text = _inject_markers(text, line.get("markers") or [], marker_lookup)
        out.append(f"  {line_id}: {text}")
    return "\n".join(out) if out else "  (no body lines selected)"


def _format_footnotes(footnotes: Sequence[dict]) -> str:
    if not footnotes:
        return "  (no footnotes linked to selected body lines)"
    out = []
    for fn in footnotes:
        fn_id = fn.get("footnote_id", "")
        marker = fn.get("marker_id", "")
        body_link = fn.get("body_line_id", "")
        text = fn.get("text_gold") or fn.get("text_ocr_original") or ""
        out.append(
            f"  {fn_id} (marker '{marker}', anchored to {body_link}): {text}"
        )
    return "\n".join(out)


def _format_unit_ids(
    body_lines: Sequence[dict],
    footnotes: Sequence[dict],
) -> str:
    ids: list[str] = []
    ids.extend(line.get("line_id", "") for line in body_lines if line.get("line_id"))
    ids.extend(fn.get("footnote_id", "") for fn in footnotes if fn.get("footnote_id"))
    return ", ".join(ids) if ids else "(none)"


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the translation instruction prompt for a single page batch.

    Parameters
    ----------
    page_id:
        Identifier of the page being translated; included in the prompt
        so Claude can echo it back if needed.
    body_lines:
        Sequence of body-line dicts with at minimum 'line_id' and
        'text_gold' (or 'text_ocr_original' as fallback).
    footnotes:
        Linked footnote dicts to include in the same batch.
    lexicon_profile:
        One of LEXICON_PROFILES. 'auto' chooses Latin-only vs
        Latin+Greek by detecting Greek script in the batch input;
        'minimal' omits all lexicon hints (used for ablation tests).
    extra_context:
        Free-form context string (e.g. Go Claw catchword/marginalia
        report) appended verbatim to the prompt body.
    """

    if lexicon_profile not in LEXICON_PROFILES:
        raise ValueError(
            f"Unknown lexicon_profile {lexicon_profile!r}; "
            f"must be one of {LEXICON_PROFILES}"
        )

    # Decide which lexicon blocks apply.
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
        "You are translating reviewed lines from James Ussher's "
        "1639 Britannicarum Ecclesiarum Antiquitates (as reissued in "
        "the 1847 Elrington edition). Source languages are 17th-century "
        "Latin with embedded Patristic Greek citations. Render them "
        "into clear modern English while preserving proper nouns and "
        "scholarly precision.",
        f"Page identifier: {page_id}",
    ]
    if lexicon_section:
        sections.append(lexicon_section)
    sections.append(
        "Footnote-marker sentinels: where a body line contains '^X' "
        "(caret followed by a single letter or symbol), that mark "
        "locates a printed superscript footnote anchor in the source. "
        "The same symbol X appears as the marker_id of one of the "
        "linked footnotes below. Translate the body line WITHOUT "
        "echoing the caret or the marker symbol in the English; "
        "marker placement into the English is handled by a separate "
        "downstream pass. The caret character ('^') is reserved for "
        "this sentinel and never appears as ordinary punctuation."
    )
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


# ---------------------------------------------------------------------------
# Marker-placement prompt (second-pass, per-marker)
# ---------------------------------------------------------------------------


def build_marker_placement_prompt(
    *,
    english: str,
    marker_id: str,
    latin_with_caret: str,
) -> str:
    """Build a minimal prompt that asks Claude to insert a single
    ``^<marker_id>`` token into *english* at the position
    corresponding to the same anchor in *latin_with_caret*.

    The expected response is the English string with exactly one
    ``^<marker_id>`` token inserted and no other character changed.
    Code fences and surrounding commentary are tolerated by the
    downstream parser but discouraged here.
    """

    return (
        "You are inserting a single footnote-anchor sentinel into an "
        "English translation. The Latin source contains the sentinel "
        f"'^{marker_id}' at the exact character position where a "
        "printed superscript footnote letter attaches in the source. "
        "Your task is to insert the same single token "
        f"'^{marker_id}' into the English at the position that "
        "corresponds idiomatically to the same anchor (immediately "
        "after the equivalent word, phrase, or punctuation boundary "
        "in English word order). Do NOT change any other character "
        "of the English. Do NOT add quotation marks, code fences, or "
        "commentary. Output exactly the English sentence with "
        f"'^{marker_id}' inserted once.\n\n"
        f"Latin (with sentinel): {latin_with_caret}\n"
        f"English (no sentinel): {english}\n\n"
        f"English (with '^{marker_id}' inserted):"
    )


__all__ = [
    "LEXICON_LATIN_HINTS",
    "LEXICON_GREEK_HINTS",
    "LEXICON_PROFILES",
    "OUTPUT_CONTRACT",
    "POLISH_OUTPUT_CONTRACT",
    "build_marker_placement_prompt",
    "build_polishing_prompt",
    "build_translation_prompt",
    "contains_greek",
    "_inject_markers",
    "_build_marker_lookup",
]


# ---------------------------------------------------------------------------
# Polished translation prompt (page-scoped, prose output)
# ---------------------------------------------------------------------------

POLISH_OUTPUT_CONTRACT = """\
Output rules:
- Return ONLY the polished English prose. No JSON, no code fences, no
  preface, no commentary, no headings, no labels.
- The prose should read as continuous modern English suited for a
  scholarly but general reader. Break paragraphs by sense (topic
  shifts, change of speaker, change of cited authority); do NOT break
  paragraphs to mirror the printed line breaks of the source.
- Preserve every footnote-anchor sentinel. Each '^X' token from the
  source body lines below must appear exactly once in your output, at
  the idiomatic English position closest to where it sits in the
  Latin. Do not invent new '^X' tokens. Do not echo the footnote
  text; the reader sees footnotes as superscripts that link to the
  notes section.
- Preserve proper nouns. Transliterate Greek proper nouns by the
  same convention used in the literal pass.
- Do not introduce editorial brackets, scare quotes, or '[sic]'
  marks. Do not add translator's notes.
- The literal line-by-line English provided below is the source of
  meaning: rewrite for fluency, do not re-translate from the Latin.
  If the literal English is plainly wrong on a small point, prefer
  the literal reading over speculation.
- Do not quote lexicon entries verbatim under any circumstances."""


def _format_polish_body_block(body_units: Sequence[dict]) -> str:
    """Format body units for the polishing prompt.

    Each unit is presented with its Latin (carets preserved) and the
    existing literal English (carets preserved). The literal English
    is the source of meaning for the polishing pass; the Latin is
    provided for disambiguation only.
    """
    if not body_units:
        return "  (no body lines)"
    out: list[str] = []
    for unit in body_units:
        seg_id = unit.get("segment_id") or unit.get("line_id") or ""
        latin = unit.get("latin_text") or ""
        english = unit.get("literal_english") or unit.get("english") or ""
        out.append(f"  [{seg_id}]")
        out.append(f"    LA: {latin}")
        out.append(f"    EN: {english}")
    return "\n".join(out)


def _format_polish_footnotes(footnotes: Sequence[dict]) -> str:
    """Format footnote glosses for polishing context.

    Footnotes are shown only so the model knows which markers are
    valid and what they refer to; the polished prose must NOT echo
    the footnote text.
    """
    if not footnotes:
        return "  (no footnotes on this page)"
    out: list[str] = []
    for fn in footnotes:
        marker = fn.get("marker_id") or ""
        english = fn.get("english") or ""
        out.append(f"  ^{marker}: {english}")
    return "\n".join(out)


def _required_markers(body_units: Sequence[dict]) -> list[str]:
    """Return the ordered list of distinct marker ids that appear in
    the body units' Latin text (which carries the caret sentinels)."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for unit in body_units:
        latin = unit.get("latin_text") or ""
        for match in _MARKER_SCAN_RE.finditer(latin):
            marker = match.group(1)
            if marker not in seen_set:
                seen_set.add(marker)
                seen.append(marker)
    return seen


_MARKER_SCAN_RE = re.compile(r"\^([A-Za-z0-9]{1,2})")


def build_polishing_prompt(
    *,
    page_id: str,
    body_units: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble a page-level prompt that rewrites literal English into
    flowing readable prose, preserving footnote-anchor sentinels.

    Parameters
    ----------
    page_id:
        Identifier of the page being polished; included in the prompt
        so Claude can echo it back if needed.
    body_units:
        Sequence of dicts with keys ``segment_id``, ``latin_text`` (the
        caret-bearing Latin), and ``literal_english`` (the existing
        machine-draft English with carets in place). The order of this
        sequence is the printed order on the page.
    footnotes:
        Sequence of dicts with ``marker_id`` and ``english`` describing
        the linked footnotes. Provided as context only; the polished
        prose must not echo footnote text.
    lexicon_profile:
        One of LEXICON_PROFILES. Same semantics as the literal pass:
        ``auto`` adds Greek hints when the page contains Greek script.
    extra_context:
        Optional free-form context string appended verbatim.
    """

    if lexicon_profile not in LEXICON_PROFILES:
        raise ValueError(
            f"Unknown lexicon_profile {lexicon_profile!r}; "
            f"must be one of {LEXICON_PROFILES}"
        )

    # Lexicon gating uses the Latin text on the page. Greek detection
    # mirrors the literal pass so the two stages stay in sync.
    combined_text = "\n".join(
        unit.get("latin_text") or "" for unit in body_units
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

    required_markers = _required_markers(body_units)
    if required_markers:
        marker_list = ", ".join(f"^{m}" for m in required_markers)
        marker_clause = (
            "Footnote anchors required in your output (each must "
            f"appear exactly once, in printed order): {marker_list}."
        )
    else:
        marker_clause = (
            "This page has no footnote anchors; do not introduce any "
            "'^X' tokens."
        )

    sections: list[str] = [
        "You are producing a polished, readable English translation "
        "of one page from James Ussher's 1639 Britannicarum "
        "Ecclesiarum Antiquitates (1847 Elrington edition). A literal "
        "machine-draft English already exists for each body line; your "
        "task is to rewrite that draft as flowing prose suited for a "
        "modern reader, while preserving the meaning of the literal "
        "rendering.",
        f"Page identifier: {page_id}",
    ]
    if lexicon_section:
        sections.append(lexicon_section)
    sections.append(marker_clause)
    sections.append(
        "Body lines (printed order; LA = Latin with footnote-anchor "
        "sentinels '^X', EN = existing literal English with carets "
        "already placed):\n"
        + _format_polish_body_block(body_units)
    )
    sections.append(
        "Linked footnotes (provided as context; do NOT include their "
        "text in the polished prose — readers will see them as "
        "footnotes via the '^X' superscripts):\n"
        + _format_polish_footnotes(footnotes)
    )
    if extra_context:
        sections.append("Additional page context:\n" + extra_context.rstrip())
    sections.append(POLISH_OUTPUT_CONTRACT)

    return "\n\n".join(sections) + "\n"
