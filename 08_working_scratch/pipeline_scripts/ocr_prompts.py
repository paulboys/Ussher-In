"""OCR prompt assembly for Gemini and other vision-capable LLM providers.

The prompt enforces paleography and layout requirements, but the *typographic*
expectations differ by edition:

- Genuinely early-modern printings (the 1639/1687 Ussher editions, Whitaker's
  1610/1690 ``Disputatio``) use **long-s** and historical ligatures, which must
  be preserved verbatim.
- The **1847 Elrington/Todd** collected-works reissue of the *Antiquitates* is a
  modernized 19th-century typesetting that uses **round 's'**. Telling the model
  it is "early-modern Latin with long-s 'ſ'" (the old behaviour) primed it to
  emit ``ſ`` on plainly-round ``s``. For that edition the prompt now flips the
  default to round 's' and only allows ``ſ`` when a glyph is unmistakably
  long-s (which, if it occurs at all, is confined to reproduced older
  quotations).

Polytonic Greek must round-trip without normalization, marginalia must remain
anchored to their source line, and watermark/show-through noise must be
suppressed (never transcribed as text).

Output contract is line-oriented JSON so confidence and metadata can be lifted
into the existing OCR result + QA pipeline.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Edition profiles
# --------------------------------------------------------------------------
# Each profile supplies the edition-specific pieces of the prompt: how to frame
# the page, the Latin language hint, the long-s rule, the ligature set, and the
# verb describing the failure mode to avoid.

EDITION_PROFILES: dict[str, dict[str, str]] = {
    # Default: genuinely early-modern printings that DO use long-s.
    "early_modern": {
        "framing": "a printed early-modern scholarly edition",
        "lat_hint": "Latin (early-modern, with long-s 'ſ' and ligatures æ, œ, ct, st)",
        "long_s_rule": (
            "- Preserve long-s ('ſ') wherever it occurs; do NOT replace it with 's'."
        ),
        "ligatures": "æ Æ œ Œ ﬀ ﬁ ﬂ ﬃ ﬄ ﬅ",
        "anti": "silently modernize",
    },
    # 1847 Elrington/Todd reissue: modernized 19th-century typesetting, round 's'.
    "1847_elrington_todd": {
        "framing": (
            "a modernized 19th-century scholarly reissue (the 1847 Elrington/Todd "
            "collected works); its type is set in modern round 's', NOT early-modern long-s"
        ),
        "lat_hint": (
            "Latin (19th-century scholarly typesetting; modern round 's' — long-s "
            "'ſ' is NOT used in the running text)"
        ),
        "long_s_rule": (
            "- This edition is a MODERNIZED 19th-century reissue set in modern round\n"
            "  's'. Transcribe 's' as 's'. Emit long-s ('ſ') ONLY when a glyph is\n"
            "  UNMISTAKABLY long-s — which, if it appears at all, is confined to\n"
            "  directly reproduced older quotations. When a glyph is the least bit\n"
            "  ambiguous, transcribe 's' and lower 'confidence'; never default to 'ſ'."
        ),
        "ligatures": "æ Æ œ Œ",
        "anti": "over-archaize (e.g. inventing long-s or ligatures the modern type does not use)",
    },
}

DEFAULT_EDITION = "early_modern"

# Map external edition identifiers (as used by the batch pipeline / ALLOWED_EDITIONS)
# onto profile keys.
_EDITION_ALIASES: dict[str, str] = {
    "1639_first": "early_modern",
    "1687_second": "early_modern",
    "1847_elrington_todd": "1847_elrington_todd",
}


def _resolve_profile(edition: str | None) -> dict[str, str]:
    """Resolve an edition identifier to its prompt profile (lenient: unknown
    editions fall back to the early-modern default)."""
    if not edition:
        return EDITION_PROFILES[DEFAULT_EDITION]
    if edition in EDITION_PROFILES:
        return EDITION_PROFILES[edition]
    alias = _EDITION_ALIASES.get(edition)
    if alias and alias in EDITION_PROFILES:
        return EDITION_PROFILES[alias]
    return EDITION_PROFILES[DEFAULT_EDITION]


LANG_HINTS: dict[str, str] = {
    "lat": "Latin (early-modern, with long-s 'ſ' and ligatures æ, œ, ct, st)",
    "grc": "polytonic Ancient Greek (preserve breathings, accents, iota subscript)",
    "eng": "Early Modern English",
    "heb": "Hebrew (preserve niqqud and cantillation if visible)",
}


def _lang_clause(lang: str, profile: dict[str, str] | None = None) -> str:
    parts = [code.strip() for code in (lang or "lat").replace(",", "+").split("+") if code.strip()]
    if not parts:
        parts = ["lat"]
    lat_hint = (profile or EDITION_PROFILES[DEFAULT_EDITION]).get("lat_hint", LANG_HINTS["lat"])
    descs = [(lat_hint if code == "lat" else LANG_HINTS.get(code, code)) for code in parts]
    return "; ".join(descs)


# Footnote-marker rules are edition-independent typographic anchors.
_FOOTNOTE_MARKER_RULES = """\
Footnote-marker rules (REQUIRED — these are the typographic anchors
that link body text to marginalia/footnotes):
- Inline superscript markers in BODY text: when a small superscript
  letter or symbol sits above the line attached to a word (e.g. a tiny
  italic 'y' just after 'Arnobius'), emit it in 'text' using a caret
  sentinel: write 'Arnobius^y' (literal '^' + the marker symbol with
  no space). The marker symbol must be a single character drawn from
  [A-Za-z0-9*†‡§]. Do NOT use '^' for anything else; ordinary on-the-
  line text is preserved verbatim with no caret.
- If a glyph is ambiguous between superscript and on-the-line, emit
  it as on-the-line text and lower 'confidence' rather than guessing.
- Marginalia / footnote LEADING marker: when a marginalia or footnote
  line begins with a letter or symbol that identifies which body
  anchor it belongs to (typically printed italic or superscript at
  the start of the note), put that symbol in the 'marker_id' field
  and OMIT it from 'text'. Example: a marginalia line printed as
  'y in Psalm. 147.' must be emitted as
  marker_id='y', text='in Psalm. 147.'.
- If no leading marker is visible on a marginalia/footnote line,
  leave marker_id=''."""


def _paleography_rules(profile: dict[str, str]) -> str:
    """Assemble the paleography block for a given edition profile."""
    return f"""\
Paleography rules (strict — transcribe the glyphs actually printed; do not {profile['anti']}):
{profile['long_s_rule']}
- Preserve ligatures exactly: {profile['ligatures']}. Do NOT decompose them.
- Preserve abbreviations and tildes (e.g. q̃, p̃, ñ) as written.
- Preserve polytonic Greek breathings, accents, iota subscript, and
  diaeresis exactly as printed; do not normalize to monotonic.
- Preserve italic vs roman as plain text (do not mark up); do not
  re-order text for italic emphasis.
- Preserve historical numerals (Roman numerals, including 'IIJ', 'iiij').
- Marginalia (printed in the outer margin) MUST remain anchored to the
  body line they sit beside. Emit them on their own line with
  region='marginalia' and the index of the body line they reference.

{_FOOTNOTE_MARKER_RULES}"""


# Backward-compatible module constant (early-modern default).
PALEOGRAPHY_RULES = _paleography_rules(EDITION_PROFILES[DEFAULT_EDITION])

LAYOUT_RULES = """\
Layout rules:
- Treat the page as having three regions: 'header' (top folio line, may
  contain a page number on one side and a chapter marker 'CAP. II.' on
  the other), 'body' (main type block), 'footnote' (separated by a rule
  or whitespace at the bottom; bracketed letter or symbol markers).
- Catchword (single isolated word at bottom-right under the body) must
  be emitted with region='catchword'.
- Do NOT transcribe show-through, watermarks, paper damage, or stamps.
  If a region is illegible, return text='' and set illegible=true.
- One JSON line entry per physical line; do NOT join wrapped lines."""

OUTPUT_CONTRACT = """\
Return ONLY a JSON object matching this shape (no prose, no code fence):

{
  "page_summary": "short note about layout anomalies, if any",
  "lines": [
    {
      "region": "header" | "body" | "footnote" | "marginalia" | "catchword",
      "line_index": <int, 0-based within region>,
      "text": "<verbatim paleography-preserving transcription>",
      "confidence": <float in [0.0, 1.0], your self-assessed accuracy>,
      "illegible": <bool>,
      "marker_id": "<footnote marker symbol or empty string>",
      "marginalia_anchor_index": <int or null, only for marginalia>
    }
  ]
}

Confidence semantics: 1.0 means certain; <0.6 means likely error;
treat smudged / partial glyphs by lowering confidence rather than
guessing.

Reminder: '^X' sentinels in body 'text' are the ONLY use of the caret
character. They MUST appear wherever a printed superscript marker
attaches to a body word, and the same symbol MUST appear as
marker_id on the corresponding marginalia/footnote line."""


def build_ocr_prompt(
    lang: str = "lat+grc",
    *,
    page_id: str | None = None,
    edition: str | None = None,
) -> str:
    """Assemble the full OCR instruction prompt for a single page image.

    ``edition`` selects the typographic profile (see ``EDITION_PROFILES``).
    Pass ``"1847_elrington_todd"`` for the modernized Antiquitates reissue so
    the model defaults to round 's' instead of long-s; omit it (or pass an
    early-modern edition) to preserve long-s and historical ligatures.
    """
    profile = _resolve_profile(edition)
    page_clause = f"\nPage identifier: {page_id}\n" if page_id else ""
    return (
        "You are a careful paleographer transcribing "
        f"{profile['framing']}. Languages on this page: "
        f"{_lang_clause(lang, profile)}.{page_clause}\n\n"
        f"{_paleography_rules(profile)}\n\n"
        f"{LAYOUT_RULES}\n\n"
        f"{OUTPUT_CONTRACT}\n"
    )


__all__ = [
    "build_ocr_prompt",
    "EDITION_PROFILES",
    "DEFAULT_EDITION",
    "PALEOGRAPHY_RULES",
    "LAYOUT_RULES",
    "OUTPUT_CONTRACT",
]
