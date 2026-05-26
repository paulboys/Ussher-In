"""V5-Exemplars — Ussher Britannicarum with cross-corpus register exemplars.

Sibling of ``translation_prompts_ussher_v5.py``. Shares HARD_RULES,
lexicon, output contract, builder helpers, and TRANSLATOR_BRIEF
verbatim from ussher_v5. The ONLY addition is a REGISTER_EXEMPLARS
section, injected after HARD_RULES, carrying 3 Latin->English pairs
drawn from Whitaker's Disputatio (ch2) with Parker-grade / author-
fidelity-validated English.

Rationale (plan.md Phase 7, §7.3)
---------------------------------
Whitaker's Disputatio and Ussher's Britannicarum are genre-adjacent:
both are polemical/ecclesiastical-scholarly Latin embedding Patristic
Greek citations, both target Victorian-scholarly / modern-scholarly
English. Parker Society's 1849 Fitzgerald translation is therefore a
ready-made register exemplar source for the Ussher prompt.

The three exemplars were selected from ch2 units scoring content_
fidelity = 5 AND register_fidelity = 5 (the fidelity-first filter;
the original COMET >= 0.78 gate was dropped because it excludes the
best Greek-preservation units by design — preserving Greek that Parker
dropped tanks COMET while being exactly the behavior we want to teach).

Pattern coverage:
- u006: Greek + author's Latin paraphrase COLLAPSED into the bracket,
  inside a named Patristic citation (Eusebius, bk 7 ch 30). The
  canonical Rule 1 case plus citation form.
- u017: bare Greek + bracketed English gloss with NO Latin paraphrase
  present — the contrast case (gloss still supplied).
- u029: plain scholarly prose with crisp antithesis ("They affirm it;
  we deny it") — register/voice anchor, no Greek.

DISCIPLINE: these are REGISTER exemplars (target style), not content
few-shot answers. They must earn their place via the §7.3 ablation
test: run this prompt and plain ussher_v5 on the same Britannicarum
page (p0036, Greek-heavy, locked), score both with
author_fidelity_judge.py --corpus ussher, and accept only if
register_fidelity or content_fidelity improves by >= 0.1. Otherwise
delete this file and keep plain ussher_v5.
"""

from __future__ import annotations

from typing import Sequence

# Reuse the v5 shared core AND brief unchanged. Only the exemplars are new.
from translation_prompts_ussher_v5 import (
    HARD_RULES,
    LEXICON_GREEK_HINTS,
    LEXICON_LATIN_HINTS,
    LEXICON_PROFILES,
    OUTPUT_CONTRACT,
    TRANSLATOR_BRIEF,
    _build_marker_lookup,
    _format_body_lines,
    _format_footnotes,
    _format_unit_ids,
    _inject_markers,
    contains_greek,
)


# ---------------------------------------------------------------------------
# Register exemplars — Whitaker Disputatio ch2 (cross-corpus, genre-adjacent)
# ---------------------------------------------------------------------------

REGISTER_EXEMPLARS = """\
Worked examples (from a genre-adjacent sibling corpus — Whitaker's
Disputatio, with validated English). These show the TARGET register
and the Greek/citation handling the Hard Rules require. Match this
style; do NOT reuse their subject matter.

Example A — Greek + author's Latin paraphrase, inside a Patristic
citation. The Greek is preserved verbatim and glossed in brackets;
the author's adjacent Latin paraphrase (here 'a regula discedens')
is COLLAPSED into that bracket, not rendered separately:
  LATIN: Itaque apud Eusebium, lib. 7. cap. 30. sancti Patres Paulum
    Samosatenum accusant, quod ἀποστὰς τοῦ κανόνος, a regula
    discedens, haeretici dogmatis author extitisset.
  ENGLISH: And so in Eusebius, book 7, chapter 30, the holy Fathers
    accuse Paul of Samosata, because, ἀποστὰς τοῦ κανόνος [departing
    from the rule], he had stood forth as the author of a heretical
    doctrine.

Example B — bare Greek with NO Latin paraphrase in the source. A
concise English gloss is still supplied in brackets after the Greek:
  LATIN: ...quinam libri sint vere κανονικοὶ καὶ ἐνδιάθηκοι. De multis
    & praecipuis constat atque convenit: de quibusdam litigatur.
  ENGLISH: ...which books are truly κανονικοὶ καὶ ἐνδιάθηκοι [canonical
    and of the testament]. Concerning many of them, and the principal
    ones, there is settled agreement; about certain others there is
    dispute.

Example C — plain scholarly prose, no Greek. Note the formal but
unornamented modern register, the preserved Latinate doctrinal
vocabulary ('canonical'), and the crisp antithesis rendered directly
('They affirm it; we deny it') rather than padded:
  LATIN: Est ergo status huius quaestionis, Utrum hi libri, & hae
    librorum particulae pro sacra & Canonica Scriptura recipi
    debeant. Illi statuunt: Nos negamus.
  ENGLISH: The state of this question, then, is, whether these books
    and these portions of books ought to be received as sacred and
    canonical scripture. They affirm it; we deny it.
"""


# ---------------------------------------------------------------------------
# Prompt builder — identical to ussher_v5 except the exemplars section
# ---------------------------------------------------------------------------


def build_translation_prompt(
    *,
    page_id: str,
    body_lines: Sequence[dict],
    footnotes: Sequence[dict] = (),
    lexicon_profile: str = "auto",
    extra_context: str | None = None,
) -> str:
    """Assemble the Ussher v5 prompt with register exemplars injected."""

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
        REGISTER_EXEMPLARS,
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
    "REGISTER_EXEMPLARS",
    "TRANSLATOR_BRIEF",
    "build_translation_prompt",
    "contains_greek",
]
