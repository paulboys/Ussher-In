"""CLI: verify provider config and (optionally) ping Gemini.

Usage:

    python claw_health.py                 # show provider readiness, no network
    python claw_health.py --ping-gemini   # also do a tiny live OCR call

The script reads `.env` automatically (via provider_config.load_config) and
prints a per-provider readiness report. `--ping-gemini` sends a 1x1 PNG to
Gemini to confirm the API key actually authenticates; the response payload
will not be valid OCR but a successful HTTP round-trip proves the wiring.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Ensure sibling modules are importable when running as a script.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ocr_adapters import GeminiOcrEngine, GeminiOcrError  # noqa: E402
from provider_config import default_config, health_check, load_config  # noqa: E402
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _make_blank_png() -> bytes:
    """Return bytes for a minimal 1x1 white PNG."""
    try:
        from PIL import Image
    except ImportError:
        # Hard-coded 1x1 white PNG fallback (67 bytes).
        return bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4"
            "890000000D49444154789C636060606000000004000018E3FA9D000000004945"
            "4E44AE426082"
        )
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Provider config health check")
    parser.add_argument(
        "--config",
        default="06_tools_config/providers.json",
        help="Path to providers.json (missing file is OK)",
    )
    parser.add_argument(
        "--ping-gemini",
        action="store_true",
        help="Send a tiny image to Gemini to verify the API key authenticates",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    config = load_config(config_path)

    report = health_check(config)
    print("Provider readiness")
    print("------------------")
    for name, info in report.items():
        marker = "OK " if info["configured"] else "?  "
        missing = (", missing: " + ", ".join(info["missing"])) if info["missing"] else ""
        caps = ", ".join(info["capabilities"]) or "-"
        model = info.get("model") or "-"
        print(f"  [{marker}] {name:10s}  model={model:30s}  caps={caps}{missing}")
    print()
    print(f"Default OCR provider:         {config.default_ocr_provider}")
    print(f"Default translation provider: {config.default_translation_provider}")

    if not args.ping_gemini:
        return 0

    logging.info("Pinging Gemini with a tiny 1x1 image to verify API key authentication.")
    gemini = config.get("gemini")
    if not gemini.is_configured():
        logging.warning("Gemini is not configured; cannot ping.")
        return 1

    engine = GeminiOcrEngine(gemini)
    image_bytes = _make_blank_png()
    try:
        logging.info("Sending image to Gemini API...")
        result = engine.extract(image_bytes, lang="lat", config="")
        logging.info(f"Gemini API response: Text preview: {result.text[:80]}, Avg confidence: {result.avg_confidence}")
    except GeminiOcrError as exc:
        logging.warning(f"Gemini API round-trip OK but response not JSON-parsable: {exc}")
        return 0
    except Exception as exc:
        logging.error(f"Gemini API call failed: {type(exc).__name__}: {exc}")
        return 1

    logging.info("Gemini API round-trip successful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
