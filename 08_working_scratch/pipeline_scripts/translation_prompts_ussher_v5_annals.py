"""V5-Annals — Ussher's Annales Veteris Testamenti.

Sibling of ``translation_prompts_ussher_v5.py``. Shares HARD_RULES,
lexicon, output contract, and builder verbatim from ussher_v5 (which
in turn inherits the locked v4-Whitaker shared core). The only
difference is the TRANSLATOR_BRIEF, which is rewritten for Ussher's
Annales Veteris Testamenti (1650) rather than his Britannicarum
Ecclesiarum Antiquitates (1639).

Rationale for forking instead of editing v5 in place:

- v5 just passed Phase 4 generalization on Britannicarum's Cap. II
  (author-fidelity 4.85/5 register, 5.00/5 Greek preservation). It
  is the working baseline for that corpus.
- Annals is a different *genre* of Ussher's Latin: biblical-
  chronological computation rather than ecclesiastical history.
  Dense classical citations (Cicero correspondence, Suetonius),
  embedded Hebrew/Greek with Latin paraphrases, and chronological
  annotations (Anno Mundi, Julian Period, regnal years) appear
  pervasively in Annals but never in Britannicarum.
- Forking keeps v5 stable for its tested corpus while letting the
  BRIEF surface what's distinctive about Annals to the model.

If author-fidelity scores look good on the 5-page Annals sample,
we can later consider lifting any genuinely Annals-specific lessons
into a shared "ussher_core" pattern. For now, two BRIEFs and one
shared HARD_RULES is the disciplined separation.

Phase 6 (2026-05-18+): test v5 rules on Annals p0384-p0388 (Vol I
Latin) against the 1658 English translation (modernized to Parker
1849 register via a separate sidecar pipeline).
"""

from __future__ import annotations

from typing import Sequence

# Reuse the v5 shared core unchanged. Only the BRIEF is different.
from translation_prompts_ussher_v5 import (
    HARD_RULES,
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
# Translator brief — Annals corpus skin (overrides ussher_v5's BRIEF)
# ---------------------------------------------------------------------------

TRANSLATOR_BRIEF = (
    "You are translating reviewed lines from James Ussher's Annales "
    "Veteris Testamenti (1650; with the companion Annales Novi "
    "Testamenti), Ussher's biblical-chronological history of the "
    "world from Creation to A.D. 70 — the work that established the "
    "Anno Mundi 4004 BC dating. Source language is 17th-century "
    "chronological-historical Latin, much denser in classical "
    "citations (Cicero's letters, Suetonius, Tacitus, Plutarch) "
    "than Ussher's ecclesiastical-history writing, with Hebrew, "
    "Patristic and biblical Greek citations also embedded throughout. "
    "Chronological annotations are pervasive: Anno Mundi years, "
    "Julian Period numbers, Olympiad and consular dating, regnal "
    "years. Preserve all source citations and date markers verbatim; "
    "render Latin date phrases ('anno mundi', 'periodi Julianae', "
    "'Olympiadis') into English equivalents only when natural. "
    "No gold-standard modern English translation exists for this "
    "work; a 1658 contemporary English translation (Sir James "
    "Hamilton, tr.) exists but in Restoration-era English. Target "
    "modern scholarly English of the kind appropriate to academic "
    "ancient-history and biblical-studies prose, with Latinate "
    "doctrinal and scholastic vocabulary preserved. The Hard Rules "
    "below are stricter than the Lexicon Hints; when they conflict, "
    "follow the Hard Rules."
)


# ---------------------------------------------------------------------------
# Prompt builder — identical structure to ussher_v5 / v4-Whitaker
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Ussher v5 Annals translation prompt."""

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
