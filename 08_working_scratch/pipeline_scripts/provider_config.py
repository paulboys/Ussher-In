"""Provider configuration foundation for OCR and translation engines.

This module provides a SciClaw-inspired configuration layer that supports
multiple LLM/OCR providers (Gemini, Anthropic Claude) plus legacy local
engines (Tesseract, Kraken). Configuration is loaded from JSON and may be
overridden via environment variables using the prefix:

    USSHERIN_PROVIDERS_<PROVIDER>_<FIELD>

For example, ``USSHERIN_PROVIDERS_GEMINI_API_KEY`` overrides the API key
for the ``gemini`` provider. Defaults for the OCR and translation provider
selection can be overridden via:

    USSHERIN_DEFAULT_OCR_PROVIDER
    USSHERIN_DEFAULT_TRANSLATION_PROVIDER

The module is intentionally side-effect free: callers invoke
``load_config`` (or ``default_config``) and pass the resulting object to
adapter factories.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

ENV_PREFIX = "USSHERIN_"
PROVIDER_ENV_PREFIX = ENV_PREFIX + "PROVIDERS_"

SUPPORTED_PROVIDERS: tuple[str, ...] = ("gemini", "anthropic", "tesseract", "kraken")
REMOTE_PROVIDERS: frozenset[str] = frozenset({"gemini", "anthropic"})


@dataclass
class ProviderConfig:
    """Configuration for a single provider (model endpoint + capabilities)."""

    name: str
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: float = 60.0
    max_retries: int = 2
    supports_ocr: bool = False
    supports_translation: bool = False
    supports_vision: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def requires_api_key(self) -> bool:
        return self.name in REMOTE_PROVIDERS

    def is_configured(self) -> bool:
        """Return True if this provider has the minimum settings to be usable."""
        if self.requires_api_key():
            return bool(self.api_key) and bool(self.model)
        return True

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if self.requires_api_key() and not self.api_key:
            missing.append("api_key")
        if self.requires_api_key() and not self.model:
            missing.append("model")
        return missing


@dataclass
class Config:
    """Top-level configuration object."""

    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    default_ocr_provider: str = "gemini"
    default_translation_provider: str = "anthropic"

    def get(self, name: str) -> ProviderConfig:
        if name not in self.providers:
            raise KeyError(f"Unknown provider: {name!r}")
        return self.providers[name]

    def ocr_provider(self) -> ProviderConfig:
        return self.get(self.default_ocr_provider)

    def translation_provider(self) -> ProviderConfig:
        return self.get(self.default_translation_provider)


def default_config() -> Config:
    """Return the built-in default configuration.

    Defaults choose Gemini 3.1 Pro for OCR and Claude Opus 4.6 for
    translation. API keys remain empty until provided by JSON or env.
    """
    return Config(
        providers={
            "gemini": ProviderConfig(
                name="gemini",
                model="gemini-3.1-pro-preview",
                base_url="https://generativelanguage.googleapis.com",
                timeout_seconds=120.0,
                max_retries=2,
                supports_ocr=True,
                supports_translation=True,
                supports_vision=True,
            ),
            "anthropic": ProviderConfig(
                name="anthropic",
                model="claude-opus-4-6",
                base_url="https://api.anthropic.com",
                # The Claude Code CLI streams a long-running session;
                # 0 disables the wall-clock timeout so prompts run to
                # completion regardless of length.
                timeout_seconds=0.0,
                max_retries=2,
                supports_ocr=False,
                supports_translation=True,
                supports_vision=True,
            ),
            "tesseract": ProviderConfig(
                name="tesseract",
                model="local",
                supports_ocr=True,
                supports_translation=False,
                supports_vision=False,
            ),
            "kraken": ProviderConfig(
                name="kraken",
                model="local",
                supports_ocr=True,
                supports_translation=False,
                supports_vision=False,
            ),
        },
        default_ocr_provider="gemini",
        default_translation_provider="anthropic",
    )


def _coerce_value(current: Any, raw: str) -> Any:
    """Best-effort cast of an env string into the type of ``current``."""
    if isinstance(current, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on", "y"}
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            return int(raw)
        except ValueError:
            return current
    if isinstance(current, float):
        try:
            return float(raw)
        except ValueError:
            return current
    return raw


def _apply_provider_dict(provider: ProviderConfig, data: dict[str, Any]) -> ProviderConfig:
    known = {f for f in provider.__dataclass_fields__ if f not in {"name"}}
    updates: dict[str, Any] = {}
    extra: dict[str, Any] = dict(provider.extra)
    for key, value in data.items():
        if key == "name":
            continue
        if key in known:
            updates[key] = value
        else:
            extra[key] = value
    if extra != provider.extra:
        updates["extra"] = extra
    return replace(provider, **updates) if updates else provider


def _apply_env_overrides(config: Config, environ: dict[str, str]) -> Config:
    providers = {name: deepcopy(p) for name, p in config.providers.items()}

    default_ocr_key = ENV_PREFIX + "DEFAULT_OCR_PROVIDER"
    default_tr_key = ENV_PREFIX + "DEFAULT_TRANSLATION_PROVIDER"
    default_ocr = environ.get(default_ocr_key, config.default_ocr_provider)
    default_tr = environ.get(default_tr_key, config.default_translation_provider)

    # Convenience aliases: short-form env vars commonly used in .env files.
    # These only fill missing api_key values; explicit USSHERIN_PROVIDERS_*
    # variables and JSON config still take precedence.
    alias_map: dict[str, tuple[str, str]] = {
        "GEMINI_API_KEY": ("gemini", "api_key"),
        "GEMINI_API": ("gemini", "api_key"),
        "GOOGLE_API_KEY": ("gemini", "api_key"),
        "ANTHROPIC_API_KEY": ("anthropic", "api_key"),
        "CLAUDE_API_KEY": ("anthropic", "api_key"),
    }
    for alias, (provider_name, field_name) in alias_map.items():
        raw = environ.get(alias)
        if not raw or provider_name not in providers:
            continue
        provider = providers[provider_name]
        if getattr(provider, field_name, ""):  # don't override an already-set value
            continue
        current = getattr(provider, field_name)
        providers[provider_name] = replace(
            provider, **{field_name: _coerce_value(current, raw)}
        )

    for env_key, raw_value in environ.items():
        if not env_key.startswith(PROVIDER_ENV_PREFIX):
            continue
        remainder = env_key[len(PROVIDER_ENV_PREFIX):]
        # Match the longest known provider prefix (provider names are simple,
        # so a direct lookup with ``_`` as separator is sufficient).
        provider_name: str | None = None
        field_name: str | None = None
        for candidate in providers:
            prefix = candidate.upper() + "_"
            if remainder.startswith(prefix):
                provider_name = candidate
                field_name = remainder[len(prefix):].lower()
                break
        if provider_name is None or not field_name:
            continue
        provider = providers[provider_name]
        if field_name in provider.__dataclass_fields__ and field_name != "name":
            current = getattr(provider, field_name)
            providers[provider_name] = replace(
                provider, **{field_name: _coerce_value(current, raw_value)}
            )

    return Config(
        providers=providers,
        default_ocr_provider=default_ocr,
        default_translation_provider=default_tr,
    )


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser (no shell expansion, no quotes-with-escapes).

    Lines like ``KEY=VALUE`` or ``KEY = VALUE`` are accepted. Lines starting
    with ``#`` and blank lines are ignored. Surrounding single/double quotes
    and backticks are stripped from the value. This avoids a hard dependency
    on ``python-dotenv``.
    """
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"', "`"}:
            value = value[1:-1]
        out[key] = value
    return out


def load_config(
    path: Path | str | None = None,
    *,
    environ: dict[str, str] | None = None,
    dotenv_path: Path | str | None = None,
) -> Config:
    """Load configuration, layering: defaults < JSON file < .env < process env.

    ``path`` may be ``None`` to use defaults only. ``environ`` defaults to
    ``os.environ`` when not supplied (useful for tests). ``dotenv_path``
    defaults to ``<repo_root>/.env`` when not supplied; pass ``False`` (via
    ``Path("/dev/null")``) or an explicit non-existent path to skip.
    """
    config = default_config()

    if path is not None:
        json_path = Path(path)
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            config = _apply_json(config, data)

    env = dict(environ) if environ is not None else dict(os.environ)

    # Layer .env into the environment view, but only for keys not already set
    # in the process environment (process env wins for safety).
    if dotenv_path is None and environ is None:
        # Default lookup: <repo_root>/.env where repo_root is two parents up
        # from this file (08_working_scratch/pipeline_scripts/provider_config.py).
        candidate = Path(__file__).resolve().parents[2] / ".env"
        dotenv_values = _load_dotenv(candidate)
    elif dotenv_path is not None:
        dotenv_values = _load_dotenv(Path(dotenv_path))
    else:
        dotenv_values = {}
    for key, value in dotenv_values.items():
        env.setdefault(key, value)

    return _apply_env_overrides(config, env)


def _apply_json(config: Config, data: dict[str, Any]) -> Config:
    providers = {name: deepcopy(p) for name, p in config.providers.items()}
    raw_providers = data.get("providers", {})
    if isinstance(raw_providers, dict):
        for name, raw in raw_providers.items():
            if not isinstance(raw, dict):
                continue
            base = providers.get(name) or ProviderConfig(name=name)
            providers[name] = _apply_provider_dict(base, raw)

    return Config(
        providers=providers,
        default_ocr_provider=str(data.get("default_ocr_provider", config.default_ocr_provider)),
        default_translation_provider=str(
            data.get("default_translation_provider", config.default_translation_provider)
        ),
    )


def health_check(config: Config, providers: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """Return a per-provider readiness report.

    For each provider, returns ``{"configured": bool, "missing": [...],
    "capabilities": [...]}``. Network calls are intentionally NOT performed
    here; callers should wire live ping endpoints into adapter modules.
    """
    targets = list(providers) if providers is not None else list(config.providers.keys())
    report: dict[str, dict[str, Any]] = {}
    for name in targets:
        if name not in config.providers:
            report[name] = {"configured": False, "missing": ["provider_not_defined"], "capabilities": []}
            continue
        provider = config.providers[name]
        capabilities = [
            cap
            for cap, flag in (
                ("ocr", provider.supports_ocr),
                ("translation", provider.supports_translation),
                ("vision", provider.supports_vision),
            )
            if flag
        ]
        report[name] = {
            "configured": provider.is_configured(),
            "missing": provider.missing_fields(),
            "capabilities": capabilities,
            "model": provider.model,
        }
    return report


__all__ = [
    "Config",
    "ProviderConfig",
    "SUPPORTED_PROVIDERS",
    "REMOTE_PROVIDERS",
    "ENV_PREFIX",
    "PROVIDER_ENV_PREFIX",
    "default_config",
    "load_config",
    "health_check",
]
