"""Tests for edition-aware OCR prompt assembly (ocr_prompts.py).

The 1847 Elrington/Todd reissue of the Antiquitates is a modernized 19th-century
typesetting that uses round 's'; the old prompt told the model every page was
"early-modern Latin with long-s 'ſ'", which biased it to emit 'ſ' on plainly
round 's'. These tests pin the edition split.
"""
import sys
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "pipeline_scripts"
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

import ocr_prompts as op  # noqa: E402


def test_default_edition_preserves_long_s():
    # No edition (and genuinely early-modern editions) must keep long-s.
    prompt = op.build_ocr_prompt(lang="lat+grc")
    assert "Preserve long-s" in prompt
    assert "ſ" in prompt
    # The Latin language hint announces long-s for early-modern sources.
    assert "with long-s" in prompt


def test_early_modern_alias_preserves_long_s():
    prompt = op.build_ocr_prompt(lang="lat", edition="1687_second")
    assert "Preserve long-s" in prompt


def test_1847_edition_defaults_to_round_s():
    prompt = op.build_ocr_prompt(lang="lat+grc", edition="1847_elrington_todd")
    # Must NOT carry the blanket early-modern preserve rule...
    assert "Preserve long-s ('ſ') wherever it occurs" not in prompt
    # ...and must instruct round 's' with 'ſ' only when unmistakable.
    assert "round" in prompt
    assert "UNMISTAKABLY long-s" in prompt
    assert "never default to 'ſ'" in prompt
    # The Latin hint tells the model long-s is NOT used in running text.
    assert "long-s\n  'ſ' is NOT used" in prompt or "is NOT used in the running text" in prompt
    # ct/st early-modern ligatures should be dropped for this edition.
    assert "ct, st" not in prompt


def test_unknown_edition_falls_back_to_early_modern():
    prompt = op.build_ocr_prompt(edition="some_unknown_edition")
    assert "Preserve long-s" in prompt


def test_footnote_caret_contract_is_edition_independent():
    for edition in (None, "1847_elrington_todd"):
        prompt = op.build_ocr_prompt(edition=edition)
        assert "Arnobius^y" in prompt
        assert "marker_id" in prompt


def test_resolve_profile_maps_aliases():
    assert op._resolve_profile("1847_elrington_todd")["ligatures"] == "æ Æ œ Œ"
    assert op._resolve_profile("1639_first") is op.EDITION_PROFILES["early_modern"]
    assert op._resolve_profile(None) is op.EDITION_PROFILES[op.DEFAULT_EDITION]
