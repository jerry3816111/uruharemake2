"""Probability-aware behavior prediction metrics."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Iterable


def normalize_distribution(distribution: dict[str, float], labels: list[str]) -> dict[str, float]:
    if set(distribution) - set(labels):
        unknown = sorted(set(distribution) - set(labels))
        raise ValueError(f"prediction contains unknown labels: {unknown}")
    values: dict[str, float] = {}
    for label in labels:
        value = distribution.get(label, 0.0)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"invalid probability for {label!r}: {value!r}")
        values[label] = float(value)
    total = sum(values.values())
    if total <= 0:
        raise ValueError("probability distribution has zero mass")
    return {label: value / total for label, value in values.items()}


def _rank(distribution: dict[str, float], labels: list[str]) -> list[str]:
    order = {label: index for index, label in enumerate(labels)}
    return sorted(labels, key=lambda label: (-distribution[label], order[label]))


def evaluate_predictions(
    rows: Iterable[dict[str, Any]], labels: list[str], *, top_k: int = 3, ece_bins: int = 10
) -> dict[str, Any]:
    materialized = list(rows)
    if not materialized:
        raise ValueError("at least one prediction row is required")
    if top_k < 1 or ece_bins < 1:
        raise ValueError("top_k and ece_bins must be positive")

    confusion: Counter[tuple[str, str]] = Counter()
    supports: Counter[str] = Counter()
    top1_hits = topk_hits = 0
    brier_total = nll_total = reciprocal_rank_total = ndcg_total = 0.0
    confidence_records: list[tuple[float, float]] = []

    for row in materialized:
        actual = row["actual_observed_behavior"]
        acceptable = set(row.get("acceptable_behavior_labels") or [actual])
        if actual not in labels or not acceptable <= set(labels):
            raise ValueError("row contains an unknown ground-truth label")
        distribution = normalize_distribution(row["probabilities"], labels)
        ranked = _rank(distribution, labels)
        predicted = ranked[0]
        correctness = 1.0 if predicted in acceptable else 0.0
        top1_hits += int(correctness)
        topk_hits += int(bool(set(ranked[: min(top_k, len(labels))]) & acceptable))
        confidence_records.append((distribution[predicted], correctness))
        confusion[(actual, predicted)] += 1
        supports[actual] += 1

        # The primary observed label remains the proper-scoring-rule target.
        brier_total += sum((distribution[label] - float(label == actual)) ** 2 for label in labels)
        nll_total += -math.log(max(distribution[actual], 1e-12))
        first_acceptable_rank = min(ranked.index(label) + 1 for label in acceptable)
        reciprocal_rank_total += 1.0 / first_acceptable_rank
        ndcg_total += 1.0 / math.log2(first_acceptable_rank + 1)

    per_label: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    weighted_f1_total = 0.0
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(other, label)] for other in labels if other != label)
        fn = sum(confusion[(label, other)] for other in labels if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        support = supports[label]
        per_label[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
        f1_values.append(f1)
        weighted_f1_total += f1 * support

    bins: list[dict[str, Any]] = []
    ece = 0.0
    count = len(materialized)
    for index in range(ece_bins):
        lower = index / ece_bins
        upper = (index + 1) / ece_bins
        members = [
            (confidence, correct)
            for confidence, correct in confidence_records
            if confidence >= lower and (confidence < upper or (index == ece_bins - 1 and confidence <= upper))
        ]
        if members:
            average_confidence = sum(item[0] for item in members) / len(members)
            accuracy = sum(item[1] for item in members) / len(members)
            ece += len(members) / count * abs(accuracy - average_confidence)
        else:
            average_confidence = accuracy = None
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "average_confidence": average_confidence,
                "accuracy": accuracy,
            }
        )

    return {
        "sample_count": count,
        "top1_accuracy": top1_hits / count,
        "top_k": min(top_k, len(labels)),
        "top_k_accuracy": topk_hits / count,
        "macro_f1": sum(f1_values) / len(labels),
        "weighted_f1": weighted_f1_total / count,
        "brier_score": brier_total / count,
        "negative_log_likelihood": nll_total / count,
        "expected_calibration_error": ece,
        "mean_reciprocal_rank": reciprocal_rank_total / count,
        "mean_ndcg": ndcg_total / count,
        "per_label": per_label,
        "reliability_bins": bins,
    }
