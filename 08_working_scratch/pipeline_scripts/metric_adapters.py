from __future__ import annotations

from collections import Counter


def _safe_tokens(text: str) -> list[str]:
    return [tok for tok in text.lower().split() if tok]


class ExactMatchEvaluator:
    def score(self, prediction: str, reference: str) -> float:
        return 1.0 if prediction.strip() == reference.strip() else 0.0


class UnigramBleuEvaluator:
    """Lightweight BLEU-like evaluator without external dependencies.

    This is a unigram precision metric with brevity penalty in [0, 1].
    """

    def score(self, prediction: str, reference: str) -> float:
        pred_tokens = _safe_tokens(prediction)
        ref_tokens = _safe_tokens(reference)

        if not pred_tokens and not ref_tokens:
            return 1.0
        if not pred_tokens or not ref_tokens:
            return 0.0

        pred_counts = Counter(pred_tokens)
        ref_counts = Counter(ref_tokens)
        overlap = sum(min(pred_counts[tok], ref_counts[tok]) for tok in pred_counts)
        precision = overlap / len(pred_tokens)

        pred_len = len(pred_tokens)
        ref_len = len(ref_tokens)
        brevity_penalty = 1.0 if pred_len >= ref_len else pow(2.718281828, 1 - (ref_len / pred_len))
        return max(0.0, min(1.0, brevity_penalty * precision))
