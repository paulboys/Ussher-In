from __future__ import annotations

import subprocess
from typing import Any, Callable

import pytesseract

from core_models import OcrResult


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
