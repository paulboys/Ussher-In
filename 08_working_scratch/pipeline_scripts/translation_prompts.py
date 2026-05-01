"""Translation prompt assembly for Claude (and other LLM) translation runs.

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
        "echoing the caret or the marker symbol in the English; the "
        "footnote itself is translated separately under its "
        "footnote_id. The caret character ('^') is reserved for this "
        "sentinel and never appears as ordinary punctuation."
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


__all__ = [
    "LEXICON_LATIN_HINTS",
    "LEXICON_GREEK_HINTS",
    "LEXICON_PROFILES",
    "OUTPUT_CONTRACT",
    "build_translation_prompt",
    "contains_greek",
    "_inject_markers",
    "_build_marker_lookup",
]
