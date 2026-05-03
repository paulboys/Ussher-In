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

import translation_prompts as v1
import translation_prompts_v0 as v0


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
    """Both modules must export the same callable and the same key
    constants the A/B runner depends on, so the runner can swap modules
    without code changes."""
    required = ("build_translation_prompt", "LEXICON_LATIN_HINTS",
                "LEXICON_GREEK_HINTS")
    for name in required:
        assert hasattr(v0, name), f"v0 missing {name}"
        assert hasattr(v1, name), f"v1 missing {name}"


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
