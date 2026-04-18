from typing import Protocol

from core_models import OcrResult


class TextTransform(Protocol):
    def apply(self, text: str) -> str:
        ...


class MetricEvaluator(Protocol):
    def score(self, prediction: str, reference: str) -> float:
        ...


class OcrEngine(Protocol):
    def extract(self, image: object, lang: str, config: str) -> OcrResult:
        ...
