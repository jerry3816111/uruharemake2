"""Strict rolling-cutoff materialization and bounded history utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any, Mapping, Sequence


def materialize_cutoff(dataset: Mapping[str, Any], cutoff_id: str) -> dict[str, Any]:
    cutoff = next(row for row in dataset["rolling_cutoffs"] if row["cutoff_id"] == cutoff_id)
    prediction_time = datetime.fromisoformat(cutoff["prediction_time"])
    test_ids = set(cutoff["test_event_ids"])
    history_events = sorted(
        (row for row in dataset["events"] if datetime.fromisoformat(row["available_at"]) < prediction_time),
        key=lambda row: (row["available_at"], row["event_id"]),
    )
    history = [{
        "history_id": f'm8-history::{row["event_id"]}',
        "event_time": row["event_time"],
        "available_at": row["available_at"],
        "source_id": f'm8-source::{row["event_id"]}',
        "evidence_type": "fictional_synthetic_rolling_history",
        "observable_summary": row["observable_text"],
        "behavior_label": row["actual_observed_behavior"],
    } for row in history_events]
    history_ids = [row["history_id"] for row in history]
    samples = []
    for row in dataset["events"]:
        if row["event_id"] not in test_ids:
            continue
        samples.append({
            "sample_id": row["event_id"],
            "prediction_time": cutoff["prediction_time"],
            "available_history_cutoff": (prediction_time - timedelta(seconds=1)).isoformat(),
            "event_context": row["observable_text"],
            "participants": list(row["participants"]),
            "available_history_ids": history_ids,
            "actual_observed_behavior": row["actual_observed_behavior"],
            "acceptable_behavior_labels": [row["actual_observed_behavior"]],
            "actual_observed_at": row["actual_observed_at"],
            "source_id": f'm8-future::{row["event_id"]}',
            "source_timestamp": row["source_timestamp"],
            "annotation_confidence": 1.0,
            "evidence_type": "fictional_synthetic_rolling_future",
        })
    return {
        "schema": "ilhdt_temporal_dataset_v1",
        "dataset_id": f'{dataset["dataset_id"]}::{cutoff_id}',
        "dataset_version": dataset["dataset_version"],
        "status": dataset["status"],
        "authorizations": {"model_execution": True, "formal_target_claim": False},
        "target": dict(dataset["target"]),
        "taxonomy": dict(dataset["taxonomy"]),
        "history": history,
        "samples": samples,
    }


def available_events(dataset: Mapping[str, Any], cutoff_id: str, max_events: int | None) -> list[dict[str, Any]]:
    cutoff = next(row for row in dataset["rolling_cutoffs"] if row["cutoff_id"] == cutoff_id)
    prediction_time = datetime.fromisoformat(cutoff["prediction_time"])
    rows = sorted(
        (dict(row) for row in dataset["events"] if datetime.fromisoformat(row["available_at"]) < prediction_time),
        key=lambda row: (row["available_at"], row["event_id"]),
    )
    if max_events is None:
        return rows
    limit = max(0, int(max_events))
    return [] if limit == 0 else rows[-limit:]


def cosine_similarity(left: Mapping[str, float], right: Mapping[str, float], names: Sequence[str]) -> float:
    dot = sum(float(left[name]) * float(right[name]) for name in names)
    nl = math.sqrt(sum(float(left[name]) ** 2 for name in names))
    nr = math.sqrt(sum(float(right[name]) ** 2 for name in names))
    if nl == 0 or nr == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (nl * nr)))


def observable_memory_signals(
    current_features: Mapping[str, float],
    history: Sequence[Mapping[str, Any]],
    extracted: Mapping[str, Mapping[str, float]],
    feature_names: Sequence[str],
) -> dict[str, float]:
    if not history:
        return {"matching_memory_activation": 0.0, "contradictory_memory_activation": 0.0}
    scored = sorted(
        ((cosine_similarity(current_features, extracted[row["event_id"]], feature_names), row) for row in history),
        key=lambda item: (-item[0], item[1]["event_id"]),
    )
    top_score, top_row = scored[0]
    contradiction = max(
        (score for score, row in scored[1:] if row["actual_observed_behavior"] != top_row["actual_observed_behavior"]),
        default=0.0,
    )
    return {"matching_memory_activation": top_score, "contradictory_memory_activation": contradiction}
