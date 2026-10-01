"""Interpretable multiclass behavior predictor and temperature calibration."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Mapping, Sequence


def _softmax(logits: Mapping[str, float], labels: Sequence[str], temperature: float = 1.0) -> dict[str, float]:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive")
    scaled = {label: float(logits[label]) / temperature for label in labels}
    maximum = max(scaled.values())
    exponentials = {label: math.exp(value - maximum) for label, value in scaled.items()}
    total = sum(exponentials.values())
    return {label: exponentials[label] / total for label in labels}


def feature_vector(features: Mapping[str, float], feature_names: Sequence[str]) -> list[float]:
    if set(features) != set(feature_names):
        missing = sorted(set(feature_names) - set(features))
        unknown = sorted(set(features) - set(feature_names))
        raise ValueError(f"predictor feature keys mismatch; missing={missing}, unknown={unknown}")
    vector = []
    for name in feature_names:
        value = float(features[name])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"predictor feature {name} must be within [0, 1]")
        vector.append(value)
    return vector


def fit_softmax_classifier(
    rows: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    feature_names: Sequence[str],
    *,
    l2_alpha: float,
    learning_rate: float,
    epochs: int,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot fit predictor without rows")
    if l2_alpha < 0 or not math.isfinite(l2_alpha):
        raise ValueError("l2_alpha must be finite and non-negative")
    if learning_rate <= 0 or epochs < 1:
        raise ValueError("learning rate and epochs must be positive")
    label_set = set(labels)
    counts = Counter(str(row["behavior_label"]) for row in rows)
    if set(counts) != label_set:
        raise ValueError("training rows must contain every behavior label")
    width = len(feature_names) + 1
    weights = {label: [0.0] * width for label in labels}
    class_weights = {label: len(rows) / (len(labels) * counts[label]) for label in labels}
    objective_trace = []
    for epoch in range(epochs):
        gradients = {label: [0.0] * width for label in labels}
        loss = 0.0
        for row in rows:
            actual = str(row["behavior_label"])
            vector = [1.0, *feature_vector(row["features"], feature_names)]
            logits = {label: sum(weight * value for weight, value in zip(weights[label], vector)) for label in labels}
            probabilities = _softmax(logits, labels)
            importance = class_weights[actual]
            loss += -importance * math.log(max(probabilities[actual], 1e-12))
            for label in labels:
                residual = importance * (probabilities[label] - float(label == actual))
                for index, value in enumerate(vector):
                    gradients[label][index] += residual * value
        scale = 1.0 / len(rows)
        for label in labels:
            for index in range(width):
                regularization = 0.0 if index == 0 else l2_alpha * weights[label][index]
                weights[label][index] -= learning_rate * (gradients[label][index] * scale + regularization)
        if epoch in {0, epochs - 1} or (epoch + 1) % max(1, epochs // 10) == 0:
            penalty = 0.5 * l2_alpha * sum(
                value * value for label in labels for value in weights[label][1:]
            )
            objective_trace.append({"epoch": epoch + 1, "weighted_cross_entropy_plus_l2": loss * scale + penalty})
    names = ["bias", *feature_names]
    return {
        "family": "multiclass_softmax_linear",
        "labels": list(labels),
        "feature_names": list(feature_names),
        "l2_alpha": l2_alpha,
        "learning_rate": learning_rate,
        "epochs": epochs,
        "class_weights": class_weights,
        "coefficients": {label: dict(zip(names, weights[label])) for label in labels},
        "objective_trace": objective_trace,
        "training_ids": [str(row["example_id"]) for row in rows],
    }


def behavior_logits(model: Mapping[str, Any], features: Mapping[str, float]) -> dict[str, Any]:
    checked = feature_vector(features, model["feature_names"])
    vector = {"bias": 1.0, **dict(zip(model["feature_names"], checked))}
    contributions = {
        label: {name: float(weight) * vector[name] for name, weight in model["coefficients"][label].items()}
        for label in model["labels"]
    }
    logits = {label: sum(terms.values()) for label, terms in contributions.items()}
    return {"logits": logits, "contributions": contributions}


def predict_behavior(
    model: Mapping[str, Any],
    features: Mapping[str, float],
    *,
    temperature: float,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    calculated = behavior_logits(model, features)
    probabilities = _softmax(calculated["logits"], model["labels"], temperature)
    selected = max(model["labels"], key=lambda label: (probabilities[label], -model["labels"].index(label)))
    entropy = -sum(value * math.log(max(value, 1e-12)) for value in probabilities.values())
    normalized_entropy = entropy / math.log(len(model["labels"]))
    selected_terms = calculated["contributions"][selected]
    ranked_terms = sorted(selected_terms.items(), key=lambda item: (-abs(item[1]), item[0]))
    return {
        "behavior_candidates": [
            {
                "label": label,
                "probability": probabilities[label],
                "logit": calculated["logits"][label],
            }
            for label in sorted(model["labels"], key=lambda label: (-probabilities[label], model["labels"].index(label)))
        ],
        "probabilities": probabilities,
        "selected_behavior": selected,
        "uncertainty": normalized_entropy,
        "temperature": temperature,
        "explanation": {
            "kind": "direct_model_contributions_not_posthoc_llm",
            "selected_label_top_contributions": [
                {"feature": name, "contribution": value} for name, value in ranked_terms[:8]
            ],
            "evidence": dict(evidence),
        },
        "language_realization_performed": False,
    }


def mean_nll(rows: Sequence[Mapping[str, Any]], model: Mapping[str, Any], temperature: float) -> float:
    total = 0.0
    for row in rows:
        probabilities = predict_behavior(model, row["features"], temperature=temperature, evidence={})["probabilities"]
        total += -math.log(max(probabilities[row["behavior_label"]], 1e-12))
    return total / len(rows)


def select_temperature(
    rows: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    candidates: Sequence[float],
) -> dict[str, Any]:
    if 1.0 not in candidates:
        raise ValueError("temperature candidates must include 1.0 for a no-change comparison")
    evaluations = [
        {"temperature": float(value), "dev_negative_log_likelihood": mean_nll(rows, model, float(value))}
        for value in candidates
    ]
    evaluations.sort(key=lambda item: (item["dev_negative_log_likelihood"], item["temperature"]))
    return {"selected_temperature": evaluations[0]["temperature"], "candidates": evaluations}
