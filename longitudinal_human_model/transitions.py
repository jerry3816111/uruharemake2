"""Comparable T0-T3 state-transition mechanisms.

T0 is static, T1 is a configurable weighted update, T2 is fitted ridge-linear,
and T3 uses the same fitted transition over externally extracted event features.
The module never generates behavior or language.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence

from .baselines import ProviderError, _extract_json_object


TRANSITION_FAMILIES = ("T0_STATIC", "T1_WEIGHTED", "T2_LINEAR", "T3_HYBRID")


def _unit(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and within [0, 1]")
    return number


def _exact_unit_map(values: Mapping[str, float], labels: Sequence[str], name: str) -> dict[str, float]:
    if set(values) != set(labels):
        missing = sorted(set(labels) - set(values))
        unknown = sorted(set(values) - set(labels))
        raise ValueError(f"{name} keys mismatch; missing={missing}, unknown={unknown}")
    return {label: _unit(values[label], f"{name}.{label}") for label in labels}


@dataclass(frozen=True)
class TransitionExample:
    example_id: str
    split: str
    event_text: str
    previous_state: Mapping[str, float]
    event_features: Mapping[str, float]
    memory_signals: Mapping[str, float]
    person_parameters: Mapping[str, float]
    next_state: Mapping[str, float]

    def validate(
        self,
        *,
        state_dimensions: Sequence[str],
        event_feature_names: Sequence[str],
        memory_signal_names: Sequence[str],
        person_parameter_names: Sequence[str],
    ) -> None:
        if not self.example_id or not self.event_text:
            raise ValueError("transition example identity and event_text must be non-empty")
        if self.split not in {"train", "dev", "holdout"}:
            raise ValueError("transition split must be train, dev, or holdout")
        _exact_unit_map(self.previous_state, state_dimensions, "previous_state")
        _exact_unit_map(self.next_state, state_dimensions, "next_state")
        _exact_unit_map(self.event_features, event_feature_names, "event_features")
        _exact_unit_map(self.memory_signals, memory_signal_names, "memory_signals")
        _exact_unit_map(self.person_parameters, person_parameter_names, "person_parameters")


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def static_transition(example: TransitionExample, state_dimensions: Sequence[str]) -> dict[str, Any]:
    next_state = {name: float(example.previous_state[name]) for name in state_dimensions}
    return _trace("T0_STATIC", example, next_state, feature_source="none")


def weighted_transition(
    example: TransitionExample,
    state_dimensions: Sequence[str],
    coefficients: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    next_state: dict[str, float] = {}
    contributions: dict[str, dict[str, float]] = {}
    for dimension in state_dimensions:
        weights = coefficients.get(dimension)
        if not isinstance(weights, Mapping):
            raise ValueError(f"missing T1 coefficients for {dimension}")
        terms = {"bias": float(weights.get("bias", 0.0))}
        for name, value in example.previous_state.items():
            terms[f"previous.{name}"] = float(weights.get(f"previous.{name}", 0.0)) * value
        for name, value in example.event_features.items():
            terms[f"event.{name}"] = float(weights.get(f"event.{name}", 0.0)) * value
        for name, value in example.memory_signals.items():
            terms[f"memory.{name}"] = float(weights.get(f"memory.{name}", 0.0)) * value
        for name, value in example.person_parameters.items():
            terms[f"person.{name}"] = float(weights.get(f"person.{name}", 0.0)) * value
        next_state[dimension] = _clip(sum(terms.values()))
        contributions[dimension] = terms
    trace = _trace("T1_WEIGHTED", example, next_state, feature_source="gold_structured_fixture")
    trace["contributions"] = contributions
    return trace


def design_feature_names(
    state_dimensions: Sequence[str],
    event_feature_names: Sequence[str],
    memory_signal_names: Sequence[str],
    person_parameter_names: Sequence[str],
) -> list[str]:
    return [
        "bias",
        *(f"previous.{name}" for name in state_dimensions),
        *(f"event.{name}" for name in event_feature_names),
        *(f"memory.{name}" for name in memory_signal_names),
        *(f"person.{name}" for name in person_parameter_names),
    ]


def design_vector(
    example: TransitionExample,
    names: Sequence[str],
    *,
    event_features: Mapping[str, float] | None = None,
) -> list[float]:
    features = event_features or example.event_features
    values = {"bias": 1.0}
    values.update({f"previous.{name}": float(value) for name, value in example.previous_state.items()})
    values.update({f"event.{name}": float(value) for name, value in features.items()})
    values.update({f"memory.{name}": float(value) for name, value in example.memory_signals.items()})
    values.update({f"person.{name}": float(value) for name, value in example.person_parameters.items()})
    return [values[name] for name in names]


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("linear system is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    augmented[row][index] - factor * augmented[column][index]
                    for index in range(size + 1)
                ]
    return [augmented[row][-1] for row in range(size)]


def fit_ridge_transition(
    examples: Sequence[TransitionExample],
    state_dimensions: Sequence[str],
    feature_names: Sequence[str],
    *,
    ridge_alpha: float,
    extracted_features: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    if not examples:
        raise ValueError("cannot fit transition without examples")
    if ridge_alpha < 0 or not math.isfinite(ridge_alpha):
        raise ValueError("ridge_alpha must be finite and non-negative")
    x_rows = [
        design_vector(
            example,
            feature_names,
            event_features=(extracted_features or {}).get(example.example_id),
        )
        for example in examples
    ]
    width = len(feature_names)
    xtx = [[sum(row[i] * row[j] for row in x_rows) for j in range(width)] for i in range(width)]
    for index in range(1, width):
        xtx[index][index] += ridge_alpha
    coefficients: dict[str, dict[str, float]] = {}
    for dimension in state_dimensions:
        targets = [float(example.next_state[dimension]) for example in examples]
        xty = [sum(row[index] * target for row, target in zip(x_rows, targets)) for index in range(width)]
        fitted = _solve(xtx, xty)
        coefficients[dimension] = dict(zip(feature_names, fitted))
    return {
        "ridge_alpha": ridge_alpha,
        "feature_names": list(feature_names),
        "coefficients": coefficients,
        "training_example_ids": [example.example_id for example in examples],
    }


def learned_transition(
    family: str,
    example: TransitionExample,
    model: Mapping[str, Any],
    state_dimensions: Sequence[str],
    *,
    event_features: Mapping[str, float] | None = None,
    feature_source: str,
) -> dict[str, Any]:
    if family not in {"T2_LINEAR", "T3_HYBRID"}:
        raise ValueError("learned_transition requires T2_LINEAR or T3_HYBRID")
    vector = design_vector(example, model["feature_names"], event_features=event_features)
    next_state: dict[str, float] = {}
    contributions: dict[str, dict[str, float]] = {}
    for dimension in state_dimensions:
        weights = model["coefficients"][dimension]
        terms = {
            name: float(weights[name]) * value
            for name, value in zip(model["feature_names"], vector)
        }
        next_state[dimension] = _clip(sum(terms.values()))
        contributions[dimension] = terms
    trace = _trace(family, example, next_state, feature_source=feature_source)
    trace["contributions"] = contributions
    trace["ridge_alpha"] = model["ridge_alpha"]
    return trace


def _trace(
    family: str,
    example: TransitionExample,
    next_state: Mapping[str, float],
    *,
    feature_source: str,
) -> dict[str, Any]:
    return {
        "family": family,
        "example_id": example.example_id,
        "split": example.split,
        "previous_state": dict(example.previous_state),
        "next_state": dict(next_state),
        "delta": {
            name: float(next_state[name]) - float(example.previous_state[name])
            for name in next_state
        },
        "feature_source": feature_source,
        "behavior_prediction_performed": False,
        "language_generation_performed": False,
    }


def feature_extraction_prompt(event_text: str, feature_names: Sequence[str]) -> str:
    payload = {
        "task": "Estimate only the observable event-feature intensities for state-transition input.",
        "event_text": event_text,
        "features": {name: "number from 0 to 1" for name in feature_names},
        "constraints": [
            "Return JSON only.",
            "Use every feature exactly once.",
            "Use only observable content in event_text.",
            "Do not infer private thoughts, diagnosis, identity, outcome, or next state.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def extract_event_features(
    event_text: str,
    feature_names: Sequence[str],
    *,
    model: str,
    provider: Callable[..., dict[str, Any]],
    options: Mapping[str, Any],
) -> dict[str, Any]:
    prompt = feature_extraction_prompt(event_text, feature_names)
    result = provider(model=model, prompt=prompt, options=dict(options))
    parsed = _extract_json_object(result["text"])
    features = parsed.get("features")
    if not isinstance(features, Mapping) and set(parsed) == set(feature_names):
        features = parsed
    if not isinstance(features, Mapping):
        raise ProviderError("feature extractor did not return an exact feature map")
    try:
        clean = _exact_unit_map(features, feature_names, "extracted_features")
    except (TypeError, ValueError) as exc:
        raise ProviderError(str(exc)) from exc
    return {
        "features": clean,
        "raw_response": str(result["text"]),
        "raw_response_sha256": hashlib.sha256(str(result["text"]).encode("utf-8")).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_tokens": int(result.get("prompt_tokens") or 0),
        "completion_tokens": int(result.get("completion_tokens") or 0),
        "latency_seconds": float(result.get("latency_seconds") or 0.0),
        "model_reported": result.get("model_reported") or model,
    }


def transition_metrics(rows: Sequence[Mapping[str, Any]], state_dimensions: Sequence[str]) -> dict[str, Any]:
    errors = []
    absolute = []
    direction_hits = []
    per_dimension = {}
    for dimension in state_dimensions:
        dim_errors = []
        dim_absolute = []
        dim_direction = []
        for row in rows:
            predicted = float(row["prediction"][dimension])
            actual = float(row["actual_next_state"][dimension])
            previous = float(row["previous_state"][dimension])
            error = predicted - actual
            dim_errors.append(error * error)
            dim_absolute.append(abs(error))
            predicted_direction = 0 if abs(predicted - previous) < 0.02 else (1 if predicted > previous else -1)
            actual_direction = 0 if abs(actual - previous) < 0.02 else (1 if actual > previous else -1)
            dim_direction.append(predicted_direction == actual_direction)
        errors.extend(dim_errors)
        absolute.extend(dim_absolute)
        direction_hits.extend(dim_direction)
        per_dimension[dimension] = {
            "rmse": math.sqrt(sum(dim_errors) / len(dim_errors)),
            "mae": sum(dim_absolute) / len(dim_absolute),
            "direction_accuracy": sum(dim_direction) / len(dim_direction),
        }
    return {
        "example_count": len(rows),
        "rmse": math.sqrt(sum(errors) / len(errors)),
        "mae": sum(absolute) / len(absolute),
        "direction_accuracy": sum(direction_hits) / len(direction_hits),
        "per_dimension": per_dimension,
    }


def feature_metrics(
    extracted: Mapping[str, Mapping[str, float]],
    examples: Sequence[TransitionExample],
    feature_names: Sequence[str],
) -> dict[str, Any]:
    absolute = []
    per_feature = {}
    for name in feature_names:
        values = [
            abs(float(extracted[item.example_id][name]) - float(item.event_features[name]))
            for item in examples
        ]
        absolute.extend(values)
        per_feature[name] = sum(values) / len(values)
    return {"mae": sum(absolute) / len(absolute), "per_feature_mae": per_feature}
