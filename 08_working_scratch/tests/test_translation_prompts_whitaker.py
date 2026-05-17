"""Tests for the Whitaker translation prompt builder.

The Whitaker prompt is built on v1's lexicon content but reorganized in
the v2 style (translator brief / hard rules / lexicon hints). The
hard-rules block diverges from v2 in exactly one place: rule #1.
v2 tells the model to skip the English when an adjacent Latin paraphrase
is present; the Whitaker rule requires the model to ALWAYS supply an
English translation alongside the preserved Greek, regardless of any
Latin paraphrase in the surrounding text.
"""

from __future__ import annotations

from translation_prompts_whitaker import (
    HARD_RULES,
    LEXICON_GREEK_HINTS,
    LEXICON_LATIN_HINTS,
    LEXICON_PROFILES,
    OUTPUT_CONTRACT,
    TRANSLATOR_BRIEF,
    build_translation_prompt,
    contains_greek,
)


_BODY_LATIN = [
    {
        "line_id": "wlat_p0001_body_l0001",
        "text_gold": "Bellarminus negat scripturam esse perspicuam.",
    },
    {
        "line_id": "wlat_p0001_body_l0002",
        "text_gold": "sed nos contendimus contra eum.",
    },
]

_BODY_WITH_GREEK = [
    {
        "line_id": "wlat_p0001_body_l0010",
        "text_gold": "ut Origenes inquit, ὁ λόγος αὐτοῦ τρέχει ταχέως",
    }
]


# ---------------------------------------------------------------------------
# Translator brief
# ---------------------------------------------------------------------------


def test_translator_brief_names_whitaker_disputatio():
    assert "Whitaker" in TRANSLATOR_BRIEF
    assert "Disputatio de Sacra Scriptura" in TRANSLATOR_BRIEF
    # Must not accidentally still reference Ussher's Antiquitates.
    assert "Ussher" not in TRANSLATOR_BRIEF
    assert "Antiquitates" not in TRANSLATOR_BRIEF


# ---------------------------------------------------------------------------
# Hard rules: Greek preservation rule diverges from v2
# ---------------------------------------------------------------------------


def test_hard_rule_one_requires_greek_preservation_with_english():
    # The Whitaker Greek rule must require BOTH the Greek and an English
    # translation in square brackets — never the Greek alone.
    text = HARD_RULES.upper()
    assert "GREEK PRESERVATION" in text
    assert "SQUARE BRACKETS" in text


def test_hard_rule_one_explicitly_disables_latin_paraphrase_logic():
    # The whole point of switching off v1: the model must NOT skip the
    # English on the assumption that an adjacent Latin clause glosses
    # the Greek. In the locked Whitaker prompt, this is expressed by
    # collapsing the Latin paraphrase into the English-in-brackets slot.
    rule_text = HARD_RULES.lower()
    assert "latin paraphrase" in rule_text
    assert "collapse that latin into" in rule_text
    assert "english-in-brackets slot" in rule_text
    assert "do not separately render the latin" in rule_text


def test_hard_rules_do_not_carry_over_v2_skip_english_directive():
    # v2's rule says: "LEAVE THE GREEK UNTRANSLATED in your English".
    # That phrasing must not appear in the Whitaker prompt — it would
    # contradict the new rule.
    assert "leave the greek untranslated" not in HARD_RULES.lower()


def test_hard_rules_keep_carry_over_directives_from_v2():
    # The non-Greek hard rules from v2 are still useful for Whitaker.
    # Smoke-check that the headings are present (they're rough proxies
    # for the underlying directives being intact).
    upper = HARD_RULES.upper()
    assert "MODERN ENGLISH REGISTER" in upper
    assert "PROPER-NOUN NORMALIZATION" in upper
    assert "BOOK AND TREATISE TITLES" in upper
    assert "SUBJECT CONTINUITY" in upper
    assert "FOOTNOTE-MARKER SENTINELS" in upper


def test_proper_noun_rule_uses_whitaker_relevant_examples():
    # Bellarmine / Stapleton are the named adversaries in the Disputatio,
    # so they should appear as the proper-noun normalization examples
    # (rather than Ussher's Boudica / Theodoret).
    assert "Bellarmine" in HARD_RULES
    assert "Stapleton" in HARD_RULES


# ---------------------------------------------------------------------------
# build_translation_prompt: structure and lexicon profile behavior
# ---------------------------------------------------------------------------


def test_contains_greek_detects_polytonic():
    assert contains_greek("ἀρχή") is True
    assert contains_greek("Hello world") is False


def test_build_prompt_includes_brief_and_hard_rules_and_contract():
    prompt = build_translation_prompt(
        page_id="wlat_p0001",
        body_lines=_BODY_LATIN,
    )
    assert TRANSLATOR_BRIEF in prompt
    assert "Page identifier: wlat_p0001" in prompt
    assert HARD_RULES in prompt
    assert OUTPUT_CONTRACT in prompt


def test_auto_profile_omits_greek_hints_when_no_greek_in_batch():
    prompt = build_translation_prompt(
        page_id="wlat_p0001",
        body_lines=_BODY_LATIN,
    )
    assert LEXICON_LATIN_HINTS in prompt
    assert LEXICON_GREEK_HINTS not in prompt


def test_auto_profile_includes_greek_hints_when_greek_in_batch():
    prompt = build_translation_prompt(
        page_id="wlat_p0001",
        body_lines=_BODY_WITH_GREEK,
    )
    assert LEXICON_LATIN_HINTS in prompt
    assert LEXICON_GREEK_HINTS in prompt


def test_minimal_profile_omits_all_lexicon_hints():
    prompt = build_translation_prompt(
        page_id="wlat_p0001",
        body_lines=_BODY_WITH_GREEK,
        lexicon_profile="minimal",
    )
    assert LEXICON_LATIN_HINTS not in prompt
    assert LEXICON_GREEK_HINTS not in prompt
    # Hard rules must always be present, even under minimal lexicon.
    assert HARD_RULES in prompt


def test_lexicon_profiles_constant_is_inherited_from_v1():
    # The Whitaker module reuses v1's LEXICON_PROFILES tuple verbatim;
    # the dispatcher relies on identical option names across versions.
    assert "auto" in LEXICON_PROFILES
    assert "latin_only" in LEXICON_PROFILES
    assert "latin_greek" in LEXICON_PROFILES
    assert "minimal" in LEXICON_PROFILES


def test_extra_context_is_appended_when_provided():
    prompt = build_translation_prompt(
        page_id="wlat_p0001",
        body_lines=_BODY_LATIN,
        extra_context="Catchword on previous page: 'igitur'.",
    )
    assert "Additional page context:" in prompt
    assert "Catchword on previous page: 'igitur'." in prompt


def test_unknown_lexicon_profile_raises():
    import pytest

    with pytest.raises(ValueError):
        build_translation_prompt(
            page_id="wlat_p0001",
            body_lines=_BODY_LATIN,
            lexicon_profile="not_a_real_profile",
        )
