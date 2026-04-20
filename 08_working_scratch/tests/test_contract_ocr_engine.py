from core_interfaces import OcrEngine
from ocr_adapters import TesseractOcrEngine, KrakenOcrEngine


class DummyImage:
    pass


def assert_ocr_engine_contract(engine: OcrEngine) -> None:
    result = engine.extract(DummyImage(), lang="lat", config="--oem 1")
    assert isinstance(result.text, str)
    assert isinstance(result.avg_confidence, float)
    assert isinstance(result.min_confidence, float)
    assert result.avg_confidence >= 0.0
    assert result.min_confidence >= 0.0


def test_tesseract_engine_contract_with_injected_callables() -> None:
    def fake_image_to_string(_image, **_kwargs):
        return "sample text"

    def fake_image_to_data(_image, **_kwargs):
        return {"conf": ["10", "20", "-1"]}

    engine = TesseractOcrEngine(
        image_to_string=fake_image_to_string,
        image_to_data=fake_image_to_data,
    )

    assert_ocr_engine_contract(engine)
    result = engine.extract(DummyImage(), lang="lat", config="--oem 1")
    assert result.text == "sample text"
    assert result.avg_confidence == 15.0
    assert result.min_confidence == 10.0


def test_kraken_engine_contract_with_injected_callables() -> None:
    """KrakenOcrEngine should satisfy the OcrEngine protocol using injected fakes."""

    def fake_segment(image):
        return {"lines": [{"boundary": [0, 0, 100, 20]}]}

    def fake_predict(image, seg):
        return [
            {"text": "Ecclesiarum antiquitates", "confidence": 0.92},
            {"text": "Britannicarum", "confidence": 0.87},
        ]

    engine = KrakenOcrEngine(
        model="test-model",
        _segment_fn=fake_segment,
        _predict_fn=fake_predict,
    )

    assert_ocr_engine_contract(engine)
    result = engine.extract(DummyImage(), lang="lat", config="")
    assert "Ecclesiarum" in result.text
    assert "Britannicarum" in result.text
    assert result.avg_confidence == 0.9
    assert result.min_confidence == 0.87


def test_kraken_engine_empty_predictions() -> None:
    """KrakenOcrEngine should handle empty predictions gracefully."""

    def fake_segment(image):
        return {}

    def fake_predict(image, seg):
        return []

    engine = KrakenOcrEngine(
        model="test-model",
        _segment_fn=fake_segment,
        _predict_fn=fake_predict,
    )

    result = engine.extract(DummyImage(), lang="lat", config="")
    assert result.text == ""
    assert result.avg_confidence == 0.0
    assert result.min_confidence == 0.0
