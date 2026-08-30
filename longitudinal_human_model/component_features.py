"""Independent preference/value activations and history-derived habit priors."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


PREFERENCE_FEATURES = (
    "preference.boundary_safety",
    "preference.clarity",
    "preference.schedule_autonomy",
    "preference.collaborative_recovery",
    "preference.process_stability",
)


def fit_habit_centroids(
    train_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    event_feature_names: Sequence[str],
) -> dict[str, dict[str, float]]:
    centroids = {}
    for label in labels:
        members = [row for row in train_rows if row["behavior_label"] == label]
        if not members:
            raise ValueError(f"habit centroid has no pre-cutoff training observations for {label}")
        centroids[label] = {
            name: sum(float(row["features"][f"event.{name}"]) for row in members) / len(members)
            for name in event_feature_names
        }
    return centroids


def _cosine(left: Mapping[str, float], right: Mapping[str, float], names: Sequence[str]) -> float:
    dot = sum(float(left[name]) * float(right[name]) for name in names)
    left_norm = math.sqrt(sum(float(left[name]) ** 2 for name in names))
    right_norm = math.sqrt(sum(float(right[name]) ** 2 for name in names))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def augment_component_features(
    features: Mapping[str, float],
    habit_centroids: Mapping[str, Mapping[str, float]],
    event_feature_names: Sequence[str],
) -> dict[str, float]:
    augmented = {
        name: float(value)
        for name, value in features.items()
        if not name.startswith("preference.") and not name.startswith("habit.")
    }
    event = {name: augmented[f"event.{name}"] for name in event_feature_names}
    augmented.update({
        "preference.boundary_safety": event["boundary_threat"] * augmented["person.boundary_directness"],
        "preference.clarity": event["ambiguity"] * augmented["person.reassessment_tendency"],
        "preference.schedule_autonomy": event["public_pressure"] * augmented["person.pressure_sensitivity"],
        "preference.collaborative_recovery": event["support"] * (1.0 - augmented["state.relationship_tension"]),
        "preference.process_stability": ((event["technical_failure"] + event["repetition"]) / 2.0) * augmented["state.task_focus"],
    })
    for label, centroid in habit_centroids.items():
        augmented[f"habit.similarity.{label}"] = _cosine(event, centroid, event_feature_names)
    return augmented


def augmented_feature_names(base_names: Sequence[str], labels: Sequence[str]) -> list[str]:
    return [*base_names, *PREFERENCE_FEATURES, *(f"habit.similarity.{label}" for label in labels)]
