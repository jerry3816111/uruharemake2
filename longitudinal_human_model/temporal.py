"""Temporal dataset contracts and future-leakage checks.

The central rule is deliberately simple: a predictor may only receive evidence
whose ``available_at`` is no later than the sample's frozen history cutoff.  It
never receives the observed outcome or any post-prediction annotation field.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_ID = "ilhdt_temporal_dataset_v1"


class TemporalDatasetError(ValueError):
    """Raised when a temporal dataset violates the frozen information boundary."""


def parse_time(value: str, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TemporalDatasetError(f"{field}: expected a non-empty ISO-8601 string")
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise TemporalDatasetError(f"{field}: invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TemporalDatasetError(f"{field}: timezone offset is required")
    return parsed


def load_dataset(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TemporalDatasetError("dataset root must be an object")
    return data


def _require_string(record: dict[str, Any], field: str, *, scope: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TemporalDatasetError(f"{scope}.{field}: expected a non-empty string")
    return value.strip()


def _unique_ids(records: Iterable[dict[str, Any]], field: str, *, scope: str) -> set[str]:
    seen: set[str] = set()
    for index, record in enumerate(records):
        value = _require_string(record, field, scope=f"{scope}[{index}]")
        if value in seen:
            raise TemporalDatasetError(f"{scope}: duplicate {field} {value!r}")
        seen.add(value)
    return seen


def validate_temporal_dataset(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a compact leakage report.

    The function is intentionally fail-closed.  Missing timestamps, unknown
    history references, outcome-before-prediction records, and undeclared
    behavior labels invalidate the whole dataset.
    """

    if data.get("schema") != SCHEMA_ID:
        raise TemporalDatasetError(f"schema must be {SCHEMA_ID!r}")

    dataset_id = _require_string(data, "dataset_id", scope="dataset")
    _require_string(data, "dataset_version", scope="dataset")
    status = _require_string(data, "status", scope="dataset")

    authorizations = data.get("authorizations")
    if not isinstance(authorizations, dict):
        raise TemporalDatasetError("dataset.authorizations must be an object")
    for flag in ("model_execution", "formal_target_claim"):
        if not isinstance(authorizations.get(flag), bool):
            raise TemporalDatasetError(f"dataset.authorizations.{flag} must be boolean")
    if status.startswith("synthetic_") and authorizations["formal_target_claim"]:
        raise TemporalDatasetError("synthetic datasets cannot authorize a formal target claim")

    target = data.get("target")
    if not isinstance(target, dict):
        raise TemporalDatasetError("dataset.target must be an object")
    _require_string(target, "target_id", scope="dataset.target")
    _require_string(target, "display_name", scope="dataset.target")
    _require_string(target, "persona_summary", scope="dataset.target")

    taxonomy = data.get("taxonomy")
    if not isinstance(taxonomy, dict):
        raise TemporalDatasetError("dataset.taxonomy must be an object")
    labels_list = taxonomy.get("labels")
    if not isinstance(labels_list, list) or len(labels_list) < 2:
        raise TemporalDatasetError("dataset.taxonomy.labels must contain at least two labels")
    labels = set()
    for index, label in enumerate(labels_list):
        if not isinstance(label, str) or not label.strip():
            raise TemporalDatasetError(f"dataset.taxonomy.labels[{index}] must be a string")
        if label in labels:
            raise TemporalDatasetError(f"duplicate taxonomy label {label!r}")
        labels.add(label)

    history = data.get("history")
    samples = data.get("samples")
    if not isinstance(history, list):
        raise TemporalDatasetError("dataset.history must be an array")
    if not isinstance(samples, list) or not samples:
        raise TemporalDatasetError("dataset.samples must be a non-empty array")

    history_ids = _unique_ids(history, "history_id", scope="history")
    _unique_ids(samples, "sample_id", scope="samples")
    history_by_id: dict[str, dict[str, Any]] = {}
    source_ids: set[str] = set()

    for index, record in enumerate(history):
        scope = f"history[{index}]"
        history_id = _require_string(record, "history_id", scope=scope)
        event_time = parse_time(_require_string(record, "event_time", scope=scope), field=f"{scope}.event_time")
        available_at = parse_time(
            _require_string(record, "available_at", scope=scope), field=f"{scope}.available_at"
        )
        if available_at < event_time:
            raise TemporalDatasetError(f"{scope}: available_at precedes event_time")
        source_id = _require_string(record, "source_id", scope=scope)
        source_ids.add(source_id)
        _require_string(record, "observable_summary", scope=scope)
        label = _require_string(record, "behavior_label", scope=scope)
        if label not in labels:
            raise TemporalDatasetError(f"{scope}: unknown behavior_label {label!r}")
        history_by_id[history_id] = record

    checked_references = 0
    for index, sample in enumerate(samples):
        scope = f"samples[{index}]"
        prediction_time = parse_time(
            _require_string(sample, "prediction_time", scope=scope), field=f"{scope}.prediction_time"
        )
        cutoff = parse_time(
            _require_string(sample, "available_history_cutoff", scope=scope),
            field=f"{scope}.available_history_cutoff",
        )
        if cutoff > prediction_time:
            raise TemporalDatasetError(f"{scope}: history cutoff is after prediction time")
        observed_at = parse_time(
            _require_string(sample, "actual_observed_at", scope=scope), field=f"{scope}.actual_observed_at"
        )
        if observed_at <= prediction_time:
            raise TemporalDatasetError(f"{scope}: actual outcome is not strictly after prediction time")
        source_timestamp = parse_time(
            _require_string(sample, "source_timestamp", scope=scope), field=f"{scope}.source_timestamp"
        )
        if source_timestamp < observed_at:
            raise TemporalDatasetError(f"{scope}: source_timestamp precedes actual observation")
        source_ids.add(_require_string(sample, "source_id", scope=scope))
        _require_string(sample, "event_context", scope=scope)
        actual = _require_string(sample, "actual_observed_behavior", scope=scope)
        if actual not in labels:
            raise TemporalDatasetError(f"{scope}: unknown actual behavior {actual!r}")
        acceptable = sample.get("acceptable_behavior_labels")
        if not isinstance(acceptable, list) or not acceptable:
            raise TemporalDatasetError(f"{scope}.acceptable_behavior_labels must be a non-empty array")
        if actual not in acceptable:
            raise TemporalDatasetError(f"{scope}: actual outcome must be an acceptable label")
        for label in acceptable:
            if label not in labels:
                raise TemporalDatasetError(f"{scope}: unknown acceptable label {label!r}")
        confidence = sample.get("annotation_confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            raise TemporalDatasetError(f"{scope}.annotation_confidence must be in [0, 1]")

        available_ids = sample.get("available_history_ids")
        if not isinstance(available_ids, list):
            raise TemporalDatasetError(f"{scope}.available_history_ids must be an array")
        if len(available_ids) != len(set(available_ids)):
            raise TemporalDatasetError(f"{scope}: duplicate available_history_ids")
        for history_id in available_ids:
            if history_id not in history_ids:
                raise TemporalDatasetError(f"{scope}: unknown history reference {history_id!r}")
            record = history_by_id[history_id]
            available_at = parse_time(record["available_at"], field=f"history[{history_id}].available_at")
            if available_at > cutoff:
                raise TemporalDatasetError(
                    f"{scope}: future leakage: {history_id!r} became available after cutoff"
                )
            checked_references += 1

        safe_view = build_model_input(data, sample)
        serialized = json.dumps(safe_view, ensure_ascii=False, sort_keys=True)
        forbidden_keys = {
            "actual_observed_behavior",
            "actual_observed_at",
            "source_timestamp",
            "acceptable_behavior_labels",
            "annotation_confidence",
        }
        if forbidden_keys & set(safe_view):
            raise TemporalDatasetError(f"{scope}: outcome keys leaked into model input")
        forbidden_values = [sample["actual_observed_at"], sample["source_timestamp"]]
        for forbidden in forbidden_values:
            if forbidden in serialized:
                raise TemporalDatasetError(f"{scope}: outcome field leaked into model input")

    return {
        "valid": True,
        "dataset_id": dataset_id,
        "status": status,
        "history_records": len(history),
        "prediction_samples": len(samples),
        "checked_history_references": checked_references,
        "source_count": len(source_ids),
        "future_leakage_violations": 0,
        "formal_target_claim": authorizations["formal_target_claim"],
        "model_execution_authorized": authorizations["model_execution"],
    }


def build_model_input(data: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    """Return the only object that a model provider is allowed to inspect."""

    history_by_id = {record["history_id"]: record for record in data.get("history", [])}
    safe_history: list[dict[str, Any]] = []
    for history_id in sample.get("available_history_ids", []):
        record = history_by_id[history_id]
        safe_history.append(
            {
                "history_id": record["history_id"],
                "event_time": record["event_time"],
                "available_at": record["available_at"],
                "observable_summary": record["observable_summary"],
                "behavior_label": record["behavior_label"],
                "evidence_type": record.get("evidence_type", "unknown"),
            }
        )
    safe_history.sort(key=lambda item: (item["available_at"], item["history_id"]))
    target = data["target"]
    return {
        "dataset_id": data["dataset_id"],
        "sample_id": sample["sample_id"],
        "prediction_time": sample["prediction_time"],
        "available_history_cutoff": sample["available_history_cutoff"],
        "candidate_behavior_labels": list(data["taxonomy"]["labels"]),
        "target": {
            "target_id": target["target_id"],
            "display_name": target["display_name"],
            "persona_summary": target["persona_summary"],
        },
        "event_context": deepcopy(sample["event_context"]),
        "participants": deepcopy(sample.get("participants", [])),
        "available_history": safe_history,
    }
