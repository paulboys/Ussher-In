from text_normalization import (
    AeHeuristicNormalizer,
    CompositeTextNormalizer,
    HistoricalNumeralNormalizer,
    LigatureNormalizer,
)


def test_ligature_normalizer_replaces_latin_ligatures() -> None:
    text = "Æterna æternitas Ǣon ǣon"
    assert LigatureNormalizer().apply(text) == "AEterna aeternitas AEon aeon"


def test_ae_heuristic_normalizer_fixes_known_patterns() -> None:
    text = "Predic Quse Ztern terré"
    assert AeHeuristicNormalizer().apply(text) == "Praedic Quae aetern terrae"


def test_historical_numeral_normalizer_fixes_open_c_confusions() -> None:
    text = "anno CID et I2C; C1D et I2G"
    assert HistoricalNumeralNormalizer().apply(text) == "anno CIƆ et IƆC; CIƆ et IƆC"


def test_composite_normalizer_applies_transforms_in_order() -> None:
    normalizer = CompositeTextNormalizer(
        transforms=[LigatureNormalizer(), AeHeuristicNormalizer(), HistoricalNumeralNormalizer()]
    )
    text = "Ætern CID Predic"
    assert normalizer.apply(text) == "AEtern CIƆ Praedic"
