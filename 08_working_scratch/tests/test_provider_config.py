from __future__ import annotations

import json
from pathlib import Path

import pytest

from provider_config import (
    Config,
    ProviderConfig,
    default_config,
    health_check,
    load_config,
)


def test_default_config_has_expected_providers():
    config = default_config()
    assert set(config.providers) >= {"gemini", "anthropic", "tesseract", "kraken"}
    assert config.default_ocr_provider == "gemini"
    assert config.default_translation_provider == "anthropic"


def test_default_gemini_supports_ocr_and_vision():
    gemini = default_config().get("gemini")
    assert gemini.supports_ocr is True
    assert gemini.supports_vision is True
    assert gemini.model == "gemini-3.1-pro-preview"


def test_default_anthropic_targets_opus_4_6():
    anthropic = default_config().get("anthropic")
    assert anthropic.model == "claude-opus-4-6"
    assert anthropic.supports_translation is True


def test_remote_provider_requires_api_key_for_configured():
    config = default_config()
    assert config.get("gemini").is_configured() is False
    assert "api_key" in config.get("gemini").missing_fields()
    assert config.get("tesseract").is_configured() is True


def test_env_override_sets_api_key_and_model():
    env = {
        "USSHERIN_PROVIDERS_GEMINI_API_KEY": "secret-123",
        "USSHERIN_PROVIDERS_GEMINI_MODEL": "gemini-3.1-pro-test",
    }
    config = load_config(path=None, environ=env)
    gemini = config.get("gemini")
    assert gemini.api_key == "secret-123"
    assert gemini.model == "gemini-3.1-pro-test"
    assert gemini.is_configured() is True


def test_env_override_coerces_numeric_and_bool_fields():
    env = {
        "USSHERIN_PROVIDERS_GEMINI_TIMEOUT_SECONDS": "30.5",
        "USSHERIN_PROVIDERS_GEMINI_MAX_RETRIES": "5",
        "USSHERIN_PROVIDERS_GEMINI_SUPPORTS_VISION": "false",
    }
    gemini = load_config(path=None, environ=env).get("gemini")
    assert gemini.timeout_seconds == pytest.approx(30.5)
    assert gemini.max_retries == 5
    assert gemini.supports_vision is False


def test_env_override_changes_default_ocr_and_translation_providers():
    env = {
        "USSHERIN_DEFAULT_OCR_PROVIDER": "tesseract",
        "USSHERIN_DEFAULT_TRANSLATION_PROVIDER": "gemini",
    }
    config = load_config(path=None, environ=env)
    assert config.default_ocr_provider == "tesseract"
    assert config.default_translation_provider == "gemini"


def test_unknown_env_provider_is_ignored():
    env = {"USSHERIN_PROVIDERS_UNKNOWN_API_KEY": "x"}
    config = load_config(path=None, environ=env)
    assert "unknown" not in config.providers


def test_load_config_reads_json_and_layers_with_env(tmp_path: Path):
    cfg_path = tmp_path / "providers.json"
    cfg_path.write_text(
        json.dumps(
            {
                "default_ocr_provider": "gemini",
                "providers": {
                    "gemini": {"api_key": "from-file", "model": "gemini-3.1-pro"},
                },
            }
        ),
        encoding="utf-8",
    )
    config = load_config(path=cfg_path, environ={})
    assert config.get("gemini").api_key == "from-file"

    config_with_env = load_config(
        path=cfg_path,
        environ={"USSHERIN_PROVIDERS_GEMINI_API_KEY": "from-env"},
    )
    assert config_with_env.get("gemini").api_key == "from-env"


def test_load_config_with_missing_path_returns_defaults(tmp_path: Path):
    config = load_config(path=tmp_path / "missing.json", environ={})
    assert config.default_ocr_provider == "gemini"
    assert config.get("gemini").api_key == ""


def test_health_check_reports_unconfigured_remote_provider():
    config = default_config()
    report = health_check(config, providers=["gemini", "tesseract"])
    assert report["gemini"]["configured"] is False
    assert "api_key" in report["gemini"]["missing"]
    assert report["tesseract"]["configured"] is True
    assert "ocr" in report["gemini"]["capabilities"]


def test_health_check_flags_undefined_provider():
    config = default_config()
    report = health_check(config, providers=["nope"])
    assert report["nope"]["configured"] is False
    assert "provider_not_defined" in report["nope"]["missing"]


def test_get_unknown_provider_raises():
    config = default_config()
    with pytest.raises(KeyError):
        config.get("does-not-exist")


def test_short_form_alias_GEMINI_API_fills_api_key():
    env = {"GEMINI_API": "sk-alias"}
    gemini = load_config(path=None, environ=env).get("gemini")
    assert gemini.api_key == "sk-alias"


def test_explicit_ussher_var_wins_over_alias():
    env = {
        "GEMINI_API": "alias",
        "USSHERIN_PROVIDERS_GEMINI_API_KEY": "explicit",
    }
    gemini = load_config(path=None, environ=env).get("gemini")
    assert gemini.api_key == "explicit"


def test_dotenv_file_is_loaded_when_present(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("GEMINI_API = abc-from-dotenv\n", encoding="utf-8")
    config = load_config(path=None, environ={}, dotenv_path=dotenv)
    assert config.get("gemini").api_key == "abc-from-dotenv"


def test_dotenv_does_not_override_process_env():
    import os
    dotenv_lines = "GEMINI_API=fromfile"
    from pathlib import Path as _P
    p = _P('.test.env.tmp')
    p.write_text(dotenv_lines, encoding='utf-8')
    try:
        env = {"GEMINI_API": "fromenv"}
        gemini = load_config(path=None, environ=env, dotenv_path=p).get("gemini")
        assert gemini.api_key == "fromenv"
    finally:
        p.unlink()

