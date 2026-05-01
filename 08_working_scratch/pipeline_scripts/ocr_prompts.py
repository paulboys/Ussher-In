"""OCR prompt assembly for Gemini and other vision-capable LLM providers.

The prompt enforces the paleography and layout requirements of the
1639 Ussher edition: long-s and historical ligatures must be preserved,
polytonic Greek must round-trip without normalization, marginalia must
remain anchored to their source line, and watermark/show-through noise
must be suppressed (never transcribed as text).

Output contract is line-oriented JSON so confidence and metadata can
be lifted into the existing OCR result + QA pipeline.
"""

from __future__ import annotations

LANG_HINTS: dict[str, str] = {
    "lat": "Latin (early-modern, with long-s 'ſ' and ligatures æ, œ, ct, st)",
    "grc": "polytonic Ancient Greek (preserve breathings, accents, iota subscript)",
    "eng": "Early Modern English",
    "heb": "Hebrew (preserve niqqud and cantillation if visible)",
}


def _lang_clause(lang: str) -> str:
    parts = [code.strip() for code in (lang or "lat").replace(",", "+").split("+") if code.strip()]
    if not parts:
        parts = ["lat"]
    descs = [LANG_HINTS.get(code, code) for code in parts]
    return "; ".join(descs)


PALEOGRAPHY_RULES = """\
Paleography rules (strict, do not silently modernize):
- Preserve long-s ('ſ') wherever it occurs; do NOT replace it with 's'.
- Preserve ligatures exactly: æ Æ œ Œ ﬀ ﬁ ﬂ ﬃ ﬄ ﬅ. Do NOT decompose them.
- Preserve early-modern abbreviations and tildes (e.g. q̃, p̃, ñ) as written.
- Preserve polytonic Greek breathings, accents, iota subscript, and
  diaeresis exactly as printed; do not normalize to monotonic.
- Preserve italic vs roman as plain text (do not mark up); do not
  re-order text for italic emphasis.
- Preserve historical numerals (Roman numerals, including 'IIJ', 'iiij').
- Marginalia (printed in the outer margin) MUST remain anchored to the
  body line they sit beside. Emit them on their own line with
  region='marginalia' and the index of the body line they reference.

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


def build_ocr_prompt(lang: str = "lat+grc", *, page_id: str | None = None) -> str:
    """Assemble the full OCR instruction prompt for a single page image."""
    page_clause = f"\nPage identifier: {page_id}\n" if page_id else ""
    return (
        "You are a careful paleographer transcribing a printed early-modern "
        "scholarly edition. Languages on this page: "
        f"{_lang_clause(lang)}.{page_clause}\n\n"
        f"{PALEOGRAPHY_RULES}\n\n"
        f"{LAYOUT_RULES}\n\n"
        f"{OUTPUT_CONTRACT}\n"
    )


__all__ = ["build_ocr_prompt", "PALEOGRAPHY_RULES", "LAYOUT_RULES", "OUTPUT_CONTRACT"]
