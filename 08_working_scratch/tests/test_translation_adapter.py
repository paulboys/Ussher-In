"""Tests for the Claude CLI translation adapter."""

from __future__ import annotations

import json

import pytest

from provider_config import default_config
from translation_adapters import (
    AnthropicTranslationAdapter,
    CommandResult,
    MalformedOutputError,
    TranslationPermissionError,
    TranslationTimeoutError,
    parse_translation_payload,
)


def _anthropic_provider(*, max_retries: int = 1, timeout: float = 5.0):
    cfg = default_config()
    base = cfg.get("anthropic")
    return base.__class__(
        name=base.name,
        model=base.model,
        api_key="ignored-by-cli",
        base_url=base.base_url,
        timeout_seconds=timeout,
        max_retries=max_retries,
        supports_ocr=base.supports_ocr,
        supports_translation=base.supports_translation,
        supports_vision=base.supports_vision,
    )


def _good_response(units):
    return json.dumps({"translations": units})


# ---------------------------------------------------------------------------
# Init / readiness
# ---------------------------------------------------------------------------


def test_adapter_rejects_non_anthropic_provider():
    gemini = default_config().get("gemini")
    with pytest.raises(ValueError):
        AnthropicTranslationAdapter(gemini)


def test_adapter_rejects_provider_without_translation_support():
    cfg = default_config()
    base = cfg.get("anthropic")
    no_tr = base.__class__(
        name=base.name,
        model=base.model,
        supports_translation=False,
    )
    with pytest.raises(ValueError):
        AnthropicTranslationAdapter(no_tr)


def test_adapter_is_ready_when_translation_supported():
    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(),
        command_runner=lambda *a, **k: CommandResult(stdout="{}"),
    )
    assert adapter.is_ready() is True


# ---------------------------------------------------------------------------
# JSON payload parsing
# ---------------------------------------------------------------------------


def test_parse_extracts_translations_from_plain_json():
    raw = _good_response({"l1": {"english": "hi", "notes": "", "uncertain": False}})
    units, warnings = parse_translation_payload(raw, expected_unit_ids=["l1"])
    assert units["l1"].english == "hi"
    assert warnings == []


def test_parse_strips_code_fence():
    raw = "```json\n" + _good_response(
        {"l1": {"english": "x", "notes": "", "uncertain": False}}
    ) + "\n```"
    units, warnings = parse_translation_payload(raw, expected_unit_ids=["l1"])
    assert units["l1"].english == "x"
    assert warnings == []


def test_parse_recovers_json_after_leading_prose():
    raw = (
        "Sure! Here is the translation as requested.\n\n"
        + _good_response({"l1": {"english": "ok", "notes": "", "uncertain": False}})
    )
    units, _ = parse_translation_payload(raw, expected_unit_ids=["l1"])
    assert units["l1"].english == "ok"


def test_parse_raises_on_non_json_payload():
    with pytest.raises(MalformedOutputError):
        parse_translation_payload("no json at all here", expected_unit_ids=["l1"])


def test_parse_raises_when_translations_key_missing():
    with pytest.raises(MalformedOutputError):
        parse_translation_payload(json.dumps({"foo": 1}))


def test_parse_warns_on_missing_unit_ids():
    raw = _good_response({"l1": {"english": "ok", "notes": "", "uncertain": False}})
    units, warnings = parse_translation_payload(
        raw, expected_unit_ids=["l1", "l2"]
    )
    assert "l1" in units
    assert any("missing translations" in w for w in warnings)


def test_parse_handles_non_object_entry_gracefully():
    raw = json.dumps({"translations": {"l1": "not an object"}})
    units, warnings = parse_translation_payload(raw)
    assert units == {}
    assert any("non-object entry" in w for w in warnings)


# ---------------------------------------------------------------------------
# translate_units behavior with injected runner
# ---------------------------------------------------------------------------


def test_translate_units_returns_structured_result():
    canned = _good_response({
        "l1": {"english": "Hello", "notes": "", "uncertain": False}
    })

    def fake_runner(argv, stdin, timeout):
        assert argv[0] == "claude"
        assert "-p" in argv
        assert "--dangerously-skip-permissions" in argv
        return CommandResult(stdout=canned)

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(), command_runner=fake_runner
    )
    result = adapter.translate_units("PROMPT", expected_unit_ids=["l1"])
    assert result.translations["l1"].english == "Hello"
    assert result.errors == []
    assert result.prompt == "PROMPT"


def test_translate_units_retries_on_malformed_then_succeeds():
    calls = {"n": 0}
    good = _good_response({"l1": {"english": "ok", "notes": "", "uncertain": False}})

    def fake_runner(argv, stdin, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return CommandResult(stdout="garbage no json")
        return CommandResult(stdout=good)

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(max_retries=2), command_runner=fake_runner
    )
    result = adapter.translate_units("PROMPT", expected_unit_ids=["l1"])
    assert calls["n"] == 2
    assert result.translations["l1"].english == "ok"


def test_translate_units_raises_after_retry_exhaustion():
    def fake_runner(argv, stdin, timeout):
        return CommandResult(stdout="still no json")

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(max_retries=1), command_runner=fake_runner
    )
    with pytest.raises(MalformedOutputError):
        adapter.translate_units("PROMPT", expected_unit_ids=["l1"])


def test_translate_units_raises_permission_error_on_stderr_signal():
    def fake_runner(argv, stdin, timeout):
        return CommandResult(
            stdout="",
            stderr="permission denied: tool not allowed by allowlist",
            returncode=1,
        )

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(), command_runner=fake_runner
    )
    with pytest.raises(TranslationPermissionError):
        adapter.translate_units("PROMPT", expected_unit_ids=["l1"])


def test_translate_units_propagates_timeout_error():
    def fake_runner(argv, stdin, timeout):
        raise TranslationTimeoutError("simulated")

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(), command_runner=fake_runner
    )
    with pytest.raises(TranslationTimeoutError):
        adapter.translate_units("PROMPT", expected_unit_ids=["l1"])


def test_translate_text_compatibility_returns_plain_english():
    canned = _good_response({
        "unit_0": {"english": "hi", "notes": "", "uncertain": False}
    })
    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(),
        command_runner=lambda argv, stdin, timeout: CommandResult(stdout=canned),
    )
    out = adapter.translate_text("Salve")
    assert out == "hi"


def test_translate_units_extracts_usage_tokens_when_present():
    canned = _good_response({"l1": {"english": "ok", "notes": "", "uncertain": False}})

    def fake_runner(argv, stdin, timeout):
        return CommandResult(
            stdout=canned,
            stderr="info: input_tokens=42 output_tokens=17",
        )

    adapter = AnthropicTranslationAdapter(
        _anthropic_provider(), command_runner=fake_runner
    )
    result = adapter.translate_units("PROMPT", expected_unit_ids=["l1"])
    assert result.usage_tokens == {"input_tokens": 42, "output_tokens": 17}
