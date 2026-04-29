"""Contract tests for the Gemini OCR adapter.

Network access is never required: tests inject a fake request function
that returns canned JSON payloads matching the prompt's output contract.
"""

from __future__ import annotations

import io
import json

import pytest

from core_interfaces import OcrEngine
from ocr_adapters import (
    ClaudeProvider,
    GeminiDetailedResult,
    GeminiOcrEngine,
    GeminiOcrError,
)
from provider_config import default_config


def _gemini_provider_with_key():
    config = default_config()
    provider = config.get("gemini")
    return provider.__class__(
        name=provider.name,
        model=provider.model,
        api_key="test-key",
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        supports_ocr=provider.supports_ocr,
        supports_translation=provider.supports_translation,
        supports_vision=provider.supports_vision,
    )


class _FakeImage:
    """Minimal PIL-Image-like that serializes as a 1x1 PNG via .save."""

    def save(self, buf: io.BytesIO, format: str = "PNG") -> None:  # noqa: A002
        buf.write(b"\x89PNG\r\n\x1a\n")  # PNG header bytes; content irrelevant


def _make_canned_response(lines):
    return json.dumps({"page_summary": "ok", "lines": lines})


def test_gemini_engine_satisfies_ocr_engine_contract():
    canned = _make_canned_response(
        [
            {"region": "header", "line_index": 0, "text": "1", "confidence": 0.99},
            {"region": "body", "line_index": 0, "text": "Eccleſiarum", "confidence": 0.92},
        ]
    )

    def fake_request(model, prompt, image_png, provider):
        assert model == provider.model
        assert "long-s" in prompt or "ſ" in prompt
        assert image_png.startswith(b"\x89PNG")
        return canned

    engine: OcrEngine = GeminiOcrEngine(_gemini_provider_with_key(), request_fn=fake_request)
    result = engine.extract(_FakeImage(), lang="lat+grc", config="")
    assert isinstance(result.text, str)
    assert "Eccleſiarum" in result.text
    assert 0.0 <= result.min_confidence <= result.avg_confidence <= 100.0


def test_gemini_engine_normalizes_confidence_to_0_100_scale():
    canned = _make_canned_response(
        [
            {"region": "body", "line_index": 0, "text": "a", "confidence": 0.8},
            {"region": "body", "line_index": 1, "text": "b", "confidence": 0.6},
        ]
    )

    def fake_request(*_args, **_kwargs):
        return canned

    engine = GeminiOcrEngine(_gemini_provider_with_key(), request_fn=fake_request)
    result = engine.extract(_FakeImage(), lang="lat", config="")
    assert result.avg_confidence == pytest.approx(70.0)
    assert result.min_confidence == pytest.approx(60.0)


def test_gemini_engine_returns_detailed_records_with_regions():
    canned = _make_canned_response(
        [
            {"region": "marginalia", "line_index": 0, "text": "Gen. 1.1",
             "confidence": 0.9, "marginalia_anchor_index": 3},
            {"region": "footnote", "line_index": 0, "text": "[a] gloss",
             "confidence": 0.85, "marker_id": "a"},
        ]
    )

    engine = GeminiOcrEngine(
        _gemini_provider_with_key(),
        request_fn=lambda *_a, **_k: canned,
    )
    detailed: GeminiDetailedResult = engine.extract_detailed(
        _FakeImage(), lang="lat", page_id="p0033"
    )
    assert detailed.page_summary == "ok"
    regions = [record.region for record in detailed.lines]
    assert regions == ["marginalia", "footnote"]
    assert detailed.lines[0].marginalia_anchor_index == 3
    assert detailed.lines[1].marker_id == "a"


def test_gemini_engine_strips_markdown_code_fence():
    canned = "```json\n" + _make_canned_response(
        [{"region": "body", "line_index": 0, "text": "x", "confidence": 0.5}]
    ) + "\n```"

    engine = GeminiOcrEngine(
        _gemini_provider_with_key(),
        request_fn=lambda *_a, **_k: canned,
    )
    result = engine.extract(_FakeImage(), lang="lat", config="")
    assert result.text == "x"


def test_gemini_engine_treats_illegible_lines_as_zero_confidence_for_aggregation():
    canned = _make_canned_response(
        [
            {"region": "body", "line_index": 0, "text": "", "confidence": 0.0, "illegible": True},
            {"region": "body", "line_index": 1, "text": "ok", "confidence": 0.9},
        ]
    )
    engine = GeminiOcrEngine(
        _gemini_provider_with_key(),
        request_fn=lambda *_a, **_k: canned,
    )
    result = engine.extract(_FakeImage(), lang="lat", config="")
    assert result.avg_confidence == pytest.approx(90.0)
    assert result.min_confidence == pytest.approx(90.0)


def test_gemini_engine_retries_on_invalid_json_then_succeeds():
    calls = {"n": 0}
    good = _make_canned_response(
        [{"region": "body", "line_index": 0, "text": "ok", "confidence": 0.9}]
    )

    def fake_request(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json {{"
        return good

    provider = _gemini_provider_with_key()
    engine = GeminiOcrEngine(provider, request_fn=fake_request)
    result = engine.extract(_FakeImage(), lang="lat", config="")
    assert calls["n"] == 2
    assert result.text == "ok"


def test_gemini_engine_raises_after_exhausting_retries():
    def always_bad(*_a, **_k):
        return "still not json"

    provider = _gemini_provider_with_key()
    engine = GeminiOcrEngine(provider, request_fn=always_bad)
    with pytest.raises(GeminiOcrError):
        engine.extract(_FakeImage(), lang="lat", config="")


def test_gemini_engine_rejects_provider_without_ocr_support():
    config = default_config()
    anthropic = config.get("anthropic")
    with pytest.raises(ValueError):
        GeminiOcrEngine(anthropic, request_fn=lambda *_a, **_k: "{}")


def test_claude_provider_is_not_ready_without_api_key():
    provider = default_config().get("anthropic")
    claude = ClaudeProvider(provider)
    assert claude.is_ready() is False


def test_claude_provider_translate_is_not_implemented():
    provider = default_config().get("anthropic")
    claude = ClaudeProvider(provider)
    with pytest.raises(NotImplementedError):
        claude.translate("text", source_lang="lat", target_lang="eng")


def test_claude_provider_rejects_wrong_provider_name():
    provider = default_config().get("gemini")
    with pytest.raises(ValueError):
        ClaudeProvider(provider)
