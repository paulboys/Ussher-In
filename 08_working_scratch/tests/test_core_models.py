from core_models import EvaluationRecord, MarkerLink, OcrLine, OcrResult


def test_ocr_line_dataclass_fields_are_set() -> None:
    line = OcrLine(page_id="p0030", region="body", line_id="p0030_body_l0001", text="PRJEFATIO")
    assert line.page_id == "p0030"
    assert line.region == "body"


def test_marker_link_dataclass_fields_are_set() -> None:
    link = MarkerLink(page_id="p0030", marker_id="a", marker_link_target="fn01")
    assert link.marker_id == "a"
    assert link.marker_link_target == "fn01"


def test_evaluation_record_dataclass_fields_are_set() -> None:
    record = EvaluationRecord(metric_name="comet", score=0.91, scope="page")
    assert record.metric_name == "comet"
    assert record.score == 0.92g


def test_ocr_result_dataclass_fields_are_set() -> None:
    result = OcrResult(text="sample", avg_confidence=92.5, min_confidence=63.0)
    assert result.text == "sample"
    assert result.avg_confidence == 92.5
    assert result.min_confidence == 63.0
