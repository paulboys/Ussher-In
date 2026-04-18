from dataclasses import dataclass
from typing import Literal


RegionType = Literal["header", "body", "footnote"]


@dataclass(frozen=True)
class OcrLine:
    page_id: str
    region: RegionType
    line_id: str
    text: str


@dataclass(frozen=True)
class MarkerLink:
    page_id: str
    marker_id: str
    marker_link_target: str


@dataclass(frozen=True)
class EvaluationRecord:
    metric_name: str
    score: float
    scope: str


@dataclass(frozen=True)
class OcrResult:
    text: str
    avg_confidence: float
    min_confidence: float
