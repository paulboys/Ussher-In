from __future__ import annotations

import base64
import io
import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable

import pytesseract

from core_models import OcrResult
from ocr_prompts import build_ocr_prompt
from provider_config import ProviderConfig


class TesseractOcrEngine:
    def __init__(
        self,
        image_to_string: Callable[..., str] | None = None,
        image_to_data: Callable[..., dict[str, list[Any]]] | None = None,
    ) -> None:
        self._image_to_string = image_to_string or pytesseract.image_to_string
        self._image_to_data = image_to_data or pytesseract.image_to_data

    def extract(self, image: Any, lang: str, config: str) -> OcrResult:
        text = self._image_to_string(image, lang=lang, config=config)
        data = self._image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        confidences = [float(c) for c in data.get("conf", []) if c not in ("-1", -1)]

        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
        min_conf = round(min(confidences), 2) if confidences else 0.0
        return OcrResult(text=text, avg_confidence=avg_conf, min_confidence=min_conf)


class KrakenOcrEngine:
    """OCR engine adapter for Kraken, conforming to the OcrEngine protocol.

    Can operate in two modes:
    - Direct mode: uses kraken Python library (for use inside WSL/Linux).
    - WSL mode: shells out to WSL from Windows (set use_wsl=True).
    """

    def __init__(
        self,
        model: str = "default",
        use_wsl: bool = False,
        *,
        _segment_fn: Callable[..., Any] | None = None,
        _predict_fn: Callable[..., Any] | None = None,
        _load_model_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.model = model
        self.use_wsl = use_wsl
        self._segment_fn = _segment_fn
        self._predict_fn = _predict_fn
        self._load_model_fn = _load_model_fn

    def extract(self, image: Any, lang: str, config: str) -> OcrResult:
        if self._segment_fn and self._predict_fn:
            return self._extract_injected(image)
        if self.use_wsl:
            return self._extract_wsl(image)
        return self._extract_direct(image)

    def _extract_injected(self, image: Any) -> OcrResult:
        """Use injected callables (for testing)."""
        seg = self._segment_fn(image)
        predictions = self._predict_fn(image, seg)
        lines = []
        confidences = []
        for pred in predictions:
            if isinstance(pred, dict):
                lines.append(pred.get("text", ""))
                conf = pred.get("confidence", -1)
                if conf >= 0:
                    confidences.append(float(conf))
            elif isinstance(pred, str):
                lines.append(pred)
        text = "\n".join(lines)
        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
        min_conf = round(min(confidences), 2) if confidences else 0.0
        return OcrResult(text=text, avg_confidence=avg_conf, min_confidence=min_conf)

    def _extract_direct(self, image: Any) -> OcrResult:
        """Use kraken Python library directly (Linux/WSL environment)."""
        from kraken import blla, rpred
        from kraken.lib import models

        nn = (self._load_model_fn or models.load_any)(self.model)
        baseline_seg = blla.segment(image)

        lines = []
        confidences = []
        for record in rpred.rpred(nn, image, baseline_seg):
            lines.append(record.prediction)
            line_confs = [c for c in (getattr(record, "confidences", None) or []) if c >= 0]
            confidences.extend(line_confs)

        text = "\n".join(lines)
        avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else 0.0
        min_conf = round(min(confidences) * 100, 2) if confidences else 0.0
        return OcrResult(text=text, avg_confidence=avg_conf, min_confidence=min_conf)

    def _extract_wsl(self, image: Any) -> OcrResult:
        """Shell out to WSL to run Kraken (Windows host mode).

        This is a lightweight bridge for single-image extraction.
        For batch processing, use the PowerShell wrapper or kraken_ocr_runner.py directly.
        """
        import tempfile
        from pathlib import Path
        from wsl_paths import windows_to_wsl

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = Path(tmp.name)

        try:
            wsl_path = windows_to_wsl(tmp_path)
            cmd = [
                "wsl", "--", "bash", "-c",
                f"source ~/kraken-env/bin/activate && kraken -i '{wsl_path}' /dev/stdout segment -bl ocr -m {self.model}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            text = result.stdout.strip() if result.returncode == 0 else ""
            return OcrResult(text=text, avg_confidence=0.0, min_confidence=0.0)
        finally:
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Gemini OCR adapter (primary OCR engine for the Ussher-In project)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeminiLineRecord:
    """Per-line record returned alongside the aggregate OcrResult.

    The aggregate ``OcrResult.text`` joins these lines with newlines so it
    remains compatible with downstream consumers that expect plain text;
    callers needing structured output can read the ``lines`` attribute
    attached by ``GeminiOcrEngine.extract_detailed``.
    """

    region: str
    line_index: int
    text: str
    confidence: float  # 0.0..1.0 as reported by the model
    illegible: bool = False
    marker_id: str = ""
    marginalia_anchor_index: int | None = None


@dataclass
class GeminiDetailedResult:
    """Rich OCR result preserving region-aware structure for the JSON schema."""

    result: OcrResult
    lines: list[GeminiLineRecord] = field(default_factory=list)
    page_summary: str = ""
    raw_response: str = ""


class GeminiOcrError(RuntimeError):
    """Raised when the Gemini API response cannot be parsed."""


def _encode_png_bytes(image: Any) -> bytes:
    """Return PNG-encoded bytes for a PIL Image-like or raw bytes input."""
    if isinstance(image, (bytes, bytearray)):
        return bytes(image)
    save = getattr(image, "save", None)
    if callable(save):
        buf = io.BytesIO()
        save(buf, format="PNG")
        return buf.getvalue()
    raise TypeError("GeminiOcrEngine requires a PIL Image or raw bytes")


_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_code_fence(payload: str) -> str:
    return _JSON_FENCE_RE.sub("", payload).strip()


def _parse_gemini_payload(payload: str) -> tuple[str, list[GeminiLineRecord]]:
    cleaned = _strip_code_fence(payload)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiOcrError(f"Gemini response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise GeminiOcrError("Gemini response root must be a JSON object")

    raw_lines = data.get("lines", [])
    if not isinstance(raw_lines, list):
        raise GeminiOcrError("Gemini response.lines must be a list")

    records: list[GeminiLineRecord] = []
    for entry in raw_lines:
        if not isinstance(entry, dict):
            continue
        records.append(
            GeminiLineRecord(
                region=str(entry.get("region", "body")),
                line_index=int(entry.get("line_index", len(records))),
                text=str(entry.get("text", "")),
                confidence=float(entry.get("confidence", 0.0) or 0.0),
                illegible=bool(entry.get("illegible", False)),
                marker_id=str(entry.get("marker_id", "")),
                marginalia_anchor_index=(
                    int(entry["marginalia_anchor_index"])
                    if isinstance(entry.get("marginalia_anchor_index"), (int, float))
                    else None
                ),
            )
        )
    summary = str(data.get("page_summary", ""))
    return summary, records


def _aggregate_to_ocr_result(records: list[GeminiLineRecord]) -> OcrResult:
    """Convert per-line model confidences (0..1) into the project's 0..100 scale."""
    text = "\n".join(record.text for record in records)
    confidences = [r.confidence for r in records if not r.illegible and r.confidence > 0]
    if not confidences:
        return OcrResult(text=text, avg_confidence=0.0, min_confidence=0.0)
    avg = round(sum(confidences) / len(confidences) * 100, 2)
    minimum = round(min(confidences) * 100, 2)
    return OcrResult(text=text, avg_confidence=avg, min_confidence=minimum)


# Type alias for the request callable so tests can inject a fake.
GeminiRequestFn = Callable[[str, str, bytes, ProviderConfig], str]


def _default_gemini_request(model: str, prompt: str, image_png: bytes, provider: ProviderConfig) -> str:
    """Default Gemini REST call (kept lazy so tests don't need google-genai).

    Uses the public Generative Language REST API. Tests inject a fake
    request function and never invoke this code path.
    """
    import urllib.request

    if not provider.api_key:
        raise GeminiOcrError("Gemini provider has no api_key configured")

    encoded = base64.b64encode(image_png).decode("ascii")
    url = (
        f"{provider.base_url.rstrip('/')}/v1beta/models/{model}:generateContent"
        f"?key={provider.api_key}"
    )
    body = json.dumps(
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": encoded}},
                    ],
                }
            ],
            "generationConfig": {"response_mime_type": "application/json"},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=provider.timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    candidates = parsed.get("candidates", [])
    if not candidates:
        raise GeminiOcrError("Gemini response contained no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "text" in part:
            return str(part["text"])
    raise GeminiOcrError("Gemini response had no text part")


class GeminiOcrEngine:
    """OCR engine adapter for Google Gemini vision models.

    Conforms to the ``OcrEngine`` protocol from ``core_interfaces``. The
    constructor accepts a ``ProviderConfig`` (typically obtained from
    ``provider_config.load_config``) and an optional injected
    ``request_fn`` for testing without network access.
    """

    def __init__(
        self,
        provider: ProviderConfig,
        *,
        request_fn: GeminiRequestFn | None = None,
    ) -> None:
        if not provider.supports_ocr:
            raise ValueError(
                f"Provider {provider.name!r} is not configured for OCR (supports_ocr=False)"
            )
        self.provider = provider
        self._request_fn = request_fn or _default_gemini_request

    def extract(self, image: Any, lang: str, config: str) -> OcrResult:
        return self.extract_detailed(image, lang=lang, config=config).result

    def extract_detailed(
        self,
        image: Any,
        *,
        lang: str = "lat+grc",
        config: str = "",
        page_id: str | None = None,
    ) -> GeminiDetailedResult:
        png_bytes = _encode_png_bytes(image)
        prompt = build_ocr_prompt(lang=lang, page_id=page_id)
        last_error: Exception | None = None
        attempts = max(1, self.provider.max_retries + 1)
        for _ in range(attempts):
            try:
                raw = self._request_fn(self.provider.model, prompt, png_bytes, self.provider)
                summary, records = _parse_gemini_payload(raw)
                return GeminiDetailedResult(
                    result=_aggregate_to_ocr_result(records),
                    lines=records,
                    page_summary=summary,
                    raw_response=raw,
                )
            except GeminiOcrError as exc:
                last_error = exc
                continue
        assert last_error is not None  # for type-checkers
        raise last_error


# ---------------------------------------------------------------------------
# Anthropic Claude provider hook (translation-ready, OCR not yet wired)
# ---------------------------------------------------------------------------


class ClaudeProvider:
    """Compatibility hook for Claude Opus 4.6.

    Claude is not used for OCR in this phase; this class exists so that
    provider config wiring, health checks, and downstream translation
    callers can address the same configuration surface as Gemini. The
    ``translate`` method intentionally raises ``NotImplementedError``
    until the translation phase lands.
    """

    def __init__(self, provider: ProviderConfig) -> None:
        if provider.name != "anthropic":
            raise ValueError(f"ClaudeProvider expects provider.name='anthropic', got {provider.name!r}")
        self.provider = provider

    def is_ready(self) -> bool:
        return self.provider.is_configured() and self.provider.supports_translation

    def translate(self, _text: str, *, source_lang: str, target_lang: str) -> str:
        raise NotImplementedError(
            "Claude translation is not yet implemented; configured for forward compatibility"
        )

