# Provider Configuration

Ussher-In supports multiple OCR and translation providers via a unified
configuration layer. The primary OCR engine is **Gemini 3.1 Pro** and the
primary translation engine is **Claude Opus 4.6**, with legacy local
engines (Tesseract, Kraken) retained as a temporary fallback during the
Gemini OCR migration.

## Files

- [providers.example.json](providers.example.json) — copy this to
  `providers.json` (gitignored) and fill in API keys, or rely on
  environment variables described below.

## Environment variables

Any field on a provider can be overridden via:

```
USSHERIN_PROVIDERS_<PROVIDER>_<FIELD>
```

Examples:

```powershell
$env:USSHERIN_PROVIDERS_GEMINI_API_KEY = "..."
$env:USSHERIN_PROVIDERS_ANTHROPIC_API_KEY = "..."
$env:USSHERIN_DEFAULT_OCR_PROVIDER = "gemini"
$env:USSHERIN_DEFAULT_TRANSLATION_PROVIDER = "anthropic"
```

Field names are lower-cased (e.g. `API_KEY` → `api_key`,
`TIMEOUT_SECONDS` → `timeout_seconds`).

## Loader contract

```python
from provider_config import load_config, health_check

config = load_config(Path("06_tools_config/providers.json"))
report = health_check(config)
```

`health_check` returns per-provider readiness without making network
calls. Live pings are wired into the adapter modules.
