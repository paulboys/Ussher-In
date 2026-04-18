from typing import Protocol


class TextTransform(Protocol):
    def apply(self, text: str) -> str:
        ...


class MetricEvaluator(Protocol):
    def score(self, prediction: str, reference: str) -> float:
        ...
