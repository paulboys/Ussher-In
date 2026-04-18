from core_interfaces import MetricEvaluator
from metric_adapters import ExactMatchEvaluator, UnigramBleuEvaluator


def assert_metric_evaluator_contract(evaluator: MetricEvaluator) -> None:
    score = evaluator.score("lorem ipsum", "lorem ipsum")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

    # Determinism for identical inputs.
    score_again = evaluator.score("lorem ipsum", "lorem ipsum")
    assert score == score_again


def test_exact_match_evaluator_contract() -> None:
    evaluator = ExactMatchEvaluator()
    assert_metric_evaluator_contract(evaluator)
    assert evaluator.score("abc", "abc") == 1.0
    assert evaluator.score("abc", "xyz") == 0.0


def test_unigram_bleu_evaluator_contract() -> None:
    evaluator = UnigramBleuEvaluator()
    assert_metric_evaluator_contract(evaluator)
    assert evaluator.score("lorem ipsum", "lorem ipsum") == 1.0
    assert evaluator.score("", "reference") == 0.0
