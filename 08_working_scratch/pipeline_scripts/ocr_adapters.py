from __future__ import annotations

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
