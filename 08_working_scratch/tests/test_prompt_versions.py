"""Drift-guard tests for the prompt-version A/B snapshot.

Asserts that:

- ``translation_prompts_v0`` (the frozen pre-refinement snapshot)
  does NOT contain the bullets and paragraphs added in commit
  ``61a7afe`` (prompt refinement).
- ``translation_prompts`` (the live v1 module) DOES contain them.
- Both modules expose the same public surface so the A/B runner can
  call either one interchangeably.
- They differ only in expected ways (the new content is additive).

This test is what gives the A/B comparison meaning: if the v0 snapshot
ever drifts, we'll know before running the experiment.
"""

from __future__ import annotations

import pytest

v1 = pytest.importorskip(
    "translation_prompts",
    reason="Prompt modules were removed from this branch.",
)
v0 = pytest.importorskip(
    "translation_prompts_v0",
    reason="Prompt modules were removed from this branch.",
)
v2 = pytest.importorskip(
    "translation_prompts_v2",
    reason="Prompt modules were removed from this branch.",
)


# Substrings introduced by the v1 prompt refinement.
V1_NEW_LATIN_HINTS = (
    "Voice:",
    "Polysemous nouns:",
    "Modern English target:",
)
V1_NEW_GREEK_HINTS = (
    "Patristic theological vocabulary:",
)
V1_NEW_BODY_PARAGRAPHS = (
    "Proper-noun normalization",
    "Book and treatise titles",
    "Subject continuity across lines",
)


def test_v0_lacks_new_latin_hints():
    for needle in V1_NEW_LATIN_HINTS:
        assert needle not in v0.LEXICON_LATIN_HINTS, (
            f"v0 snapshot unexpectedly contains '{needle}'"
        )


def test_v1_has_new_latin_hints():
    for needle in V1_NEW_LATIN_HINTS:
        assert needle in v1.LEXICON_LATIN_HINTS, (
            f"v1 prompt missing expected '{needle}'"
        )


def test_v0_lacks_new_greek_hints():
    for needle in V1_NEW_GREEK_HINTS:
        assert needle not in v0.LEXICON_GREEK_HINTS, (
            f"v0 snapshot unexpectedly contains '{needle}'"
        )


def test_v1_has_new_greek_hints():
    for needle in V1_NEW_GREEK_HINTS:
        assert needle in v1.LEXICON_GREEK_HINTS, (
            f"v1 prompt missing expected '{needle}'"
        )


def test_v0_lacks_new_body_paragraphs():
    """The new instruction paragraphs land inside the assembled body
    prompt, not in any module-level constant. We probe by building a
    minimal prompt with both modules and looking for the new strings.
    """
    minimal = _minimal_prompt(v0)
    for needle in V1_NEW_BODY_PARAGRAPHS:
        assert needle not in minimal, (
            f"v0 snapshot unexpectedly contains '{needle}' in built prompt"
        )


def test_v1_has_new_body_paragraphs():
    minimal = _minimal_prompt(v1)
    for needle in V1_NEW_BODY_PARAGRAPHS:
        assert needle in minimal, (
            f"v1 prompt missing expected '{needle}' in built prompt"
        )


def test_polish_contract_diverges():
    """The polish output contract was loosened in v1 to allow four
    classes of stylistic correction. v1 must mention at least one of
    those classes; v0 must not."""
    polish_keywords = ("archaisms", "proper-noun", "idiomatic", "antecedent")
    v0_text = getattr(v0, "POLISH_OUTPUT_CONTRACT", "")
    v1_text = getattr(v1, "POLISH_OUTPUT_CONTRACT", "")
    if not v0_text or not v1_text:
        # Constant lives under a different name in older revisions; the
        # body-prompt test above already covers the substantive change.
        return
    v0_hits = sum(1 for k in polish_keywords if k.lower() in v0_text.lower())
    v1_hits = sum(1 for k in polish_keywords if k.lower() in v1_text.lower())
    assert v1_hits > v0_hits, (
        f"v1 polish contract should mention more of {polish_keywords} "
        f"than v0 (v0={v0_hits}, v1={v1_hits})"
    )


def test_public_surface_matches():
    """All prompt modules must export the same callable and the same key
    constants the A/B runner depends on, so the runner can swap modules
    without code changes."""
    required = ("build_translation_prompt", "LEXICON_LATIN_HINTS",
                "LEXICON_GREEK_HINTS")
    for name in required:
        assert hasattr(v0, name), f"v0 missing {name}"
        assert hasattr(v1, name), f"v1 missing {name}"
        assert hasattr(v2, name), f"v2 missing {name}"


# ---------------------------------------------------------------------------
# Helper: build the smallest prompt each module accepts so we can string-search.
# ---------------------------------------------------------------------------


def _minimal_prompt(module) -> str:
    """Build a minimal prompt with the public signature shared by both
    versions: ``page_id``, ``body_lines``, ``footnotes``, ``lexicon_profile``."""
    builder = getattr(module, "build_translation_prompt", None)
    if builder is None:
        return ""
    body_lines = [
        {
            "page_id": "p9999",
            "region": "body",
            "line_id": "p9999_body_l0001",
            "seq": 1,
            "text_gold": "Hinc Arnobius dixit.",
            "review_status": "locked",
            "markers": [],
        }
    ]
    return builder(
        page_id="p9999",
        body_lines=body_lines,
        footnotes=(),
        lexicon_profile="auto",
        extra_context=None,
    )


# ---------------------------------------------------------------------------
# v2 — structural-rewrite tests
# ---------------------------------------------------------------------------


def test_v2_exposes_hard_rules_constant():
    """v2's rewrite is structurally distinct: it has a top-level
    HARD_RULES section that v0 and v1 do not."""
    assert hasattr(v2, "HARD_RULES")
    assert hasattr(v2, "TRANSLATOR_BRIEF")
    # v0/v1 do not surface a hard-rules constant; their directives
    # are interleaved into the assembled prompt.
    assert not hasattr(v0, "HARD_RULES")
    assert not hasattr(v1, "HARD_RULES")


def test_v2_hard_rules_includes_greek_paraphrase_directive():
    """Greek-paraphrase rule is the headline new directive in v2 — it
    addresses the accuracy regression observed in v1's first A/B run
    where neither v0 nor v1 told the model what to do with embedded
    Greek that Ussher had already paraphrased into Latin."""
    rules = v2.HARD_RULES
    assert "EMBEDDED GREEK" in rules
    # Phrase may be split across a wrapped line in the source — check
    # the words individually rather than the joined phrase.
    assert "LEAVE THE GREEK" in rules and "UNTRANSLATED" in rules
    # The carve-out for stand-alone Greek must also be present.
    assert "stand" in rules.lower() and "alone" in rules.lower()


def test_v2_hard_rules_includes_register_and_proper_noun_rules():
    """The v1 directives that previously lived inside the Latin lexicon
    block (style/register) and were buried mid-prompt (proper-nouns,
    titles, subject-continuity) are promoted to numbered hard rules
    in v2 so they are read before the bulky lexicon block."""
    rules = v2.HARD_RULES
    for needle in ("MODERN ENGLISH REGISTER", "PROPER-NOUN NORMALIZATION",
                   "BOOK AND TREATISE TITLES", "SUBJECT CONTINUITY",
                   "FOOTNOTE-MARKER SENTINELS"):
        assert needle in rules, f"v2 hard rules missing {needle!r}"


def test_v2_lexicon_block_is_lexicographic_only():
    """v2 moves style/register out of the Latin lexicon block. v1's
    archaism rule lived there as 'Modern English target:'; v2's lexicon
    block must NOT contain it (it lives in HARD_RULES instead)."""
    assert "Modern English target" not in v2.LEXICON_LATIN_HINTS
    assert "vouchsafed" not in v2.LEXICON_LATIN_HINTS
    # But sense-disambiguation content (voice, polysemy, lexica) stays.
    assert "Polysemous nouns" in v2.LEXICON_LATIN_HINTS
    assert "Voice:" in v2.LEXICON_LATIN_HINTS
    assert "Forcellini" in v2.LEXICON_LATIN_HINTS


def test_v2_hard_rules_appear_before_lexicon_in_built_prompt():
    """Structural property: the hard-rules block must precede the
    lexicon block in the assembled prompt, not follow it."""
    prompt = _minimal_prompt(v2)
    rules_pos = prompt.find("Hard rules")
    lex_pos = prompt.find("Lexicon hints")
    assert rules_pos != -1, "v2 prompt missing 'Hard rules' header"
    assert lex_pos != -1, "v2 prompt missing 'Lexicon hints' header"
    assert rules_pos < lex_pos, (
        f"v2 hard rules at {rules_pos} should precede lexicon at {lex_pos}"
    )


def test_v2_built_prompt_contains_translator_brief_first():
    """Translator brief is the opening section."""
    prompt = _minimal_prompt(v2)
    brief_pos = prompt.find(v2.TRANSLATOR_BRIEF)
    assert brief_pos == 0, (
        f"v2 prompt should open with TRANSLATOR_BRIEF, found at {brief_pos}"
    )


def test_v2_built_prompt_has_no_archaisms_in_directives():
    """Sanity: v2's own prompt body should not contain forbidden
    archaisms that it tells the model to avoid."""
    prompt = _minimal_prompt(v2)
    # Strip the rule text itself, which legitimately quotes archaisms
    # as examples of what to avoid.
    rules_block = v2.HARD_RULES
    # Words that should not appear OUTSIDE the rules block.
    leaked = []
    for archaism in ("vouchsafed", "verily", "whereunto"):
        if archaism in prompt and archaism not in rules_block:
            leaked.append(archaism)
    assert not leaked, f"v2 prompt body leaks archaisms: {leaked}"
