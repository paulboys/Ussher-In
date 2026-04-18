import re
from dataclasses import dataclass
from typing import Iterable

from core_interfaces import TextTransform


class LigatureNormalizer:
    def apply(self, text: str) -> str:
        return (
            text.replace("AE", "AE")
            .replace("ae", "ae")
            .replace("Æ", "AE")
            .replace("æ", "ae")
            .replace("Ǣ", "AE")
            .replace("ǣ", "ae")
        )


class AeHeuristicNormalizer:
    def apply(self, text: str) -> str:
        normalized = text
        pattern_replacements = [
            (r"\b([Pp])rzedix", r"\1raedix"),
            (r"\b([Pp])rz", r"\1rae"),
            (r"\b([Pp])redic", r"\1raedic"),
            (r"\b([Pp])refulg", r"\1raefulg"),
            (r"\b([Pp])racept", r"\1raecept"),
            (r"\b([Qq])use\b", r"\1uae"),
            (r"\b([Zz])tern", r"aetern"),
            (r"terr[eé]\b", "terrae"),
        ]
        for pattern, repl in pattern_replacements:
            normalized = re.sub(pattern, repl, normalized)
        normalized = normalized.replace("praeedix", "praedix")
        return normalized


class HistoricalNumeralNormalizer:
    def apply(self, text: str) -> str:
        normalized = text
        normalized = normalized.replace(" CID ", " CIƆ ")
        normalized = normalized.replace(" I2C ", " IƆC ")
        normalized = re.sub(r"\bCID\b", "CIƆ", normalized)
        normalized = re.sub(r"\bI2C\b", "IƆC", normalized)
        normalized = re.sub(r"\bC1D\b", "CIƆ", normalized)
        normalized = re.sub(r"\bI2G\b", "IƆC", normalized)
        return normalized


@dataclass
class CompositeTextNormalizer:
    transforms: Iterable[TextTransform]

    def apply(self, text: str) -> str:
        output = text
        for transform in self.transforms:
            output = transform.apply(output)
        return output
