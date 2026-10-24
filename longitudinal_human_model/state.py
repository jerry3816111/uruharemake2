"""Timestamped, replayable and evidence-bound HumanState snapshots.

All psychological-looking values are model estimates.  The schema records
status, confidence and evidence; it never treats a private state as ground
truth.  State transition intentionally lives outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import json
import math
from typing import Any, Mapping


ESTIMATE_STATUSES = ("observed", "inferred", "unknown")
REQUIRED_DIMENSIONS = (
    "emotion",
    "preferences",
    "goals",
    "habits",
    "personality",
    "context",
)
RELATIONSHIP_FIELDS = (
    "role",
    "familiarity",
    "trust",
    "affinity",
    "conflict",
    "interaction_frequency",
)


def _aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _unit(value: float, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{field_name} must be finite and within [0, 1]")
    return number


def _json_scalar(value: Any, field_name: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError(f"{field_name} must be a finite JSON scalar or null")


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    evidence_kind: str
    source_url_or_id: str
    observed_at: datetime
    available_at: datetime
    extraction_model: str
    dataset_version: str

    def __post_init__(self) -> None:
        for name in (
            "evidence_id",
            "evidence_kind",
            "source_url_or_id",
            "extraction_model",
            "dataset_version",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        _aware(self.observed_at, "observed_at")
        _aware(self.available_at, "available_at")
        if self.available_at < self.observed_at:
            raise ValueError("evidence available_at must not precede observed_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_kind": self.evidence_kind,
            "source_url_or_id": self.source_url_or_id,
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "extraction_model": self.extraction_model,
            "dataset_version": self.dataset_version,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "EvidenceRef":
        return cls(
            evidence_id=str(row["evidence_id"]),
            evidence_kind=str(row["evidence_kind"]),
            source_url_or_id=str(row["source_url_or_id"]),
            observed_at=datetime.fromisoformat(str(row["observed_at"])),
            available_at=datetime.fromisoformat(str(row["available_at"])),
            extraction_model=str(row["extraction_model"]),
            dataset_version=str(row["dataset_version"]),
        )


@dataclass(frozen=True)
class StateEstimate:
    value: Any
    confidence: float
    status: str
    evidence_ids: tuple[str, ...]
    updated_at: datetime
    hypothesis_note: str

    def __post_init__(self) -> None:
        if self.status not in ESTIMATE_STATUSES:
            raise ValueError(f"status must be one of {ESTIMATE_STATUSES}")
        _json_scalar(self.value, "StateEstimate.value")
        confidence = _unit(self.confidence, "StateEstimate.confidence")
        _aware(self.updated_at, "StateEstimate.updated_at")
        if self.status == "unknown":
            if self.value is not None or confidence != 0.0 or self.evidence_ids:
                raise ValueError("unknown estimate must have null value, zero confidence, and no evidence")
        elif not self.evidence_ids:
            raise ValueError("observed or inferred estimate requires evidence_ids")
        if not str(self.hypothesis_note).strip():
            raise ValueError("hypothesis_note must state the evidence boundary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "updated_at": self.updated_at.isoformat(),
            "hypothesis_note": self.hypothesis_note,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "StateEstimate":
        return cls(
            value=row.get("value"),
            confidence=float(row["confidence"]),
            status=str(row["status"]),
            evidence_ids=tuple(str(value) for value in row.get("evidence_ids") or ()),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            hypothesis_note=str(row["hypothesis_note"]),
        )


@dataclass(frozen=True)
class RelationshipState:
    entity_id: str
    fields: Mapping[str, StateEstimate]

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("relationship entity_id must be non-empty")
        if set(self.fields) != set(RELATIONSHIP_FIELDS):
            missing = sorted(set(RELATIONSHIP_FIELDS) - set(self.fields))
            unknown = sorted(set(self.fields) - set(RELATIONSHIP_FIELDS))
            raise ValueError(
                f"relationship fields must be exact; missing={missing}, unknown={unknown}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "fields": {key: self.fields[key].to_dict() for key in sorted(self.fields)},
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "RelationshipState":
        fields = row.get("fields")
        if not isinstance(fields, Mapping):
            raise ValueError("relationship fields must be an object")
        return cls(
            entity_id=str(row["entity_id"]),
            fields={str(key): StateEstimate.from_dict(value) for key, value in fields.items()},
        )


@dataclass(frozen=True)
class MemoryActivationSnapshot:
    memory_id: str
    score: float
    components: Mapping[str, float]
    contributions: Mapping[str, float]
    evidence_id: str

    def __post_init__(self) -> None:
        if not self.memory_id.strip() or not self.evidence_id.strip():
            raise ValueError("memory_id and evidence_id must be non-empty")
        _unit(self.score, "MemoryActivationSnapshot.score")
        if set(self.components) != set(self.contributions):
            raise ValueError("memory component and contribution names must match")
        for name, value in self.components.items():
            _unit(value, f"memory component {name}")
        for name, value in self.contributions.items():
            number = float(value)
            if not math.isfinite(number) or number < 0.0:
                raise ValueError(f"memory contribution {name} must be finite and non-negative")
        if not math.isclose(sum(self.contributions.values()), self.score, abs_tol=1e-9):
            raise ValueError("memory contributions must sum to score")

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "score": self.score,
            "components": {key: self.components[key] for key in sorted(self.components)},
            "contributions": {key: self.contributions[key] for key in sorted(self.contributions)},
            "evidence_id": self.evidence_id,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "MemoryActivationSnapshot":
        return cls(
            memory_id=str(row["memory_id"]),
            score=float(row["score"]),
            components={str(key): float(value) for key, value in row["components"].items()},
            contributions={
                str(key): float(value) for key, value in row["contributions"].items()
            },
            evidence_id=str(row["evidence_id"]),
        )


@dataclass(frozen=True)
class UncertaintyState:
    average_confidence: float
    unknown_fields: tuple[str, ...]
    low_confidence_fields: tuple[str, ...]
    low_confidence_threshold: float

    def __post_init__(self) -> None:
        _unit(self.average_confidence, "average_confidence")
        _unit(self.low_confidence_threshold, "low_confidence_threshold")

    def to_dict(self) -> dict[str, Any]:
        return {
            "average_confidence": self.average_confidence,
            "unknown_fields": list(self.unknown_fields),
            "low_confidence_fields": list(self.low_confidence_fields),
            "low_confidence_threshold": self.low_confidence_threshold,
        }


def _estimate_map_from_dict(row: Mapping[str, Any], name: str) -> dict[str, StateEstimate]:
    value = row.get(name)
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a non-empty object of StateEstimate values")
    return {str(key): StateEstimate.from_dict(item) for key, item in value.items()}


@dataclass(frozen=True)
class HumanStateSnapshot:
    snapshot_id: str
    schema_version: str
    subject: str
    timestamp: datetime
    available_history_cutoff: datetime
    current_event_id: str
    state_model_id: str
    dataset_version: str
    evidence_catalog: tuple[EvidenceRef, ...]
    memory_activations: tuple[MemoryActivationSnapshot, ...]
    emotion: Mapping[str, StateEstimate]
    relationships: Mapping[str, RelationshipState]
    preferences: Mapping[str, StateEstimate]
    goals: Mapping[str, StateEstimate]
    habits: Mapping[str, StateEstimate]
    personality: Mapping[str, StateEstimate]
    context: Mapping[str, StateEstimate]
    uncertainty: UncertaintyState

    def __post_init__(self) -> None:
        for name in (
            "schema_version",
            "subject",
            "current_event_id",
            "state_model_id",
            "dataset_version",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        timestamp = _aware(self.timestamp, "timestamp")
        cutoff = _aware(self.available_history_cutoff, "available_history_cutoff")
        if cutoff > timestamp:
            raise ValueError("available_history_cutoff cannot be after state timestamp")
        evidence_by_id = {item.evidence_id: item for item in self.evidence_catalog}
        if len(evidence_by_id) != len(self.evidence_catalog):
            raise ValueError("evidence_id values must be unique")
        for evidence in self.evidence_catalog:
            boundary = cutoff if evidence.evidence_kind == "memory" else timestamp
            if evidence.available_at > boundary:
                raise ValueError(
                    f"evidence {evidence.evidence_id} is unavailable at its state boundary"
                )
        for activation in self.memory_activations:
            evidence = evidence_by_id.get(activation.evidence_id)
            if evidence is None or evidence.evidence_kind != "memory":
                raise ValueError(f"memory activation {activation.memory_id} lacks memory evidence")
        paths = self.estimate_paths()
        for path, estimate in paths.items():
            if estimate.updated_at > timestamp:
                raise ValueError(f"{path} updated after snapshot timestamp")
            unknown_ids = sorted(set(estimate.evidence_ids) - set(evidence_by_id))
            if unknown_ids:
                raise ValueError(f"{path} references unknown evidence IDs {unknown_ids}")
        expected_uncertainty = derive_uncertainty(paths, self.uncertainty.low_confidence_threshold)
        if self.uncertainty != expected_uncertainty:
            raise ValueError("uncertainty summary does not match state estimates")
        if self.snapshot_id and self.snapshot_id != self.compute_snapshot_id():
            raise ValueError("snapshot_id does not match canonical state payload")

    def estimate_paths(self) -> dict[str, StateEstimate]:
        paths: dict[str, StateEstimate] = {}
        for dimension in REQUIRED_DIMENSIONS:
            values = getattr(self, dimension)
            if not values:
                raise ValueError(f"{dimension} must not be empty")
            for name, estimate in values.items():
                paths[f"{dimension}.{name}"] = estimate
        if not self.relationships:
            raise ValueError("relationships must not be empty")
        for entity_id, relationship in self.relationships.items():
            if entity_id != relationship.entity_id:
                raise ValueError("relationship map key must equal entity_id")
            for name, estimate in relationship.fields.items():
                paths[f"relationships.{entity_id}.{name}"] = estimate
        return paths

    def to_dict(self, *, include_snapshot_id: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "subject": self.subject,
            "timestamp": self.timestamp.isoformat(),
            "available_history_cutoff": self.available_history_cutoff.isoformat(),
            "current_event_id": self.current_event_id,
            "state_model_id": self.state_model_id,
            "dataset_version": self.dataset_version,
            "evidence_catalog": [
                item.to_dict() for item in sorted(self.evidence_catalog, key=lambda item: item.evidence_id)
            ],
            "memory_activations": [item.to_dict() for item in self.memory_activations],
            "emotion": {key: self.emotion[key].to_dict() for key in sorted(self.emotion)},
            "relationships": {
                key: self.relationships[key].to_dict() for key in sorted(self.relationships)
            },
            "preferences": {
                key: self.preferences[key].to_dict() for key in sorted(self.preferences)
            },
            "goals": {key: self.goals[key].to_dict() for key in sorted(self.goals)},
            "habits": {key: self.habits[key].to_dict() for key in sorted(self.habits)},
            "personality": {
                key: self.personality[key].to_dict() for key in sorted(self.personality)
            },
            "context": {key: self.context[key].to_dict() for key in sorted(self.context)},
            "uncertainty": self.uncertainty.to_dict(),
        }
        if include_snapshot_id:
            payload["snapshot_id"] = self.snapshot_id
        return payload

    def compute_snapshot_id(self) -> str:
        payload = self.to_dict(include_snapshot_id=False)
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_computed_id(self) -> "HumanStateSnapshot":
        return replace(self, snapshot_id=self.compute_snapshot_id())

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "HumanStateSnapshot":
        relationships = row.get("relationships")
        if not isinstance(relationships, Mapping):
            raise ValueError("relationships must be an object")
        uncertainty = row["uncertainty"]
        return cls(
            snapshot_id=str(row.get("snapshot_id") or ""),
            schema_version=str(row["schema_version"]),
            subject=str(row["subject"]),
            timestamp=datetime.fromisoformat(str(row["timestamp"])),
            available_history_cutoff=datetime.fromisoformat(
                str(row["available_history_cutoff"])
            ),
            current_event_id=str(row["current_event_id"]),
            state_model_id=str(row["state_model_id"]),
            dataset_version=str(row["dataset_version"]),
            evidence_catalog=tuple(EvidenceRef.from_dict(item) for item in row["evidence_catalog"]),
            memory_activations=tuple(
                MemoryActivationSnapshot.from_dict(item) for item in row["memory_activations"]
            ),
            emotion=_estimate_map_from_dict(row, "emotion"),
            relationships={
                str(key): RelationshipState.from_dict(value)
                for key, value in relationships.items()
            },
            preferences=_estimate_map_from_dict(row, "preferences"),
            goals=_estimate_map_from_dict(row, "goals"),
            habits=_estimate_map_from_dict(row, "habits"),
            personality=_estimate_map_from_dict(row, "personality"),
            context=_estimate_map_from_dict(row, "context"),
            uncertainty=UncertaintyState(
                average_confidence=float(uncertainty["average_confidence"]),
                unknown_fields=tuple(str(value) for value in uncertainty["unknown_fields"]),
                low_confidence_fields=tuple(
                    str(value) for value in uncertainty["low_confidence_fields"]
                ),
                low_confidence_threshold=float(uncertainty["low_confidence_threshold"]),
            ),
        )


def derive_uncertainty(
    paths: Mapping[str, StateEstimate], low_confidence_threshold: float
) -> UncertaintyState:
    threshold = _unit(low_confidence_threshold, "low_confidence_threshold")
    ordered = sorted(paths.items())
    confidences = [estimate.confidence for _, estimate in ordered]
    unknown = tuple(path for path, estimate in ordered if estimate.status == "unknown")
    low = tuple(
        path
        for path, estimate in ordered
        if estimate.status != "unknown" and estimate.confidence < threshold
    )
    return UncertaintyState(
        average_confidence=sum(confidences) / len(confidences),
        unknown_fields=unknown,
        low_confidence_fields=low,
        low_confidence_threshold=threshold,
    )


def build_human_state_snapshot(
    draft: Mapping[str, Any],
    retrieval_row: Mapping[str, Any],
    *,
    low_confidence_threshold: float,
) -> HumanStateSnapshot:
    timestamp = datetime.fromisoformat(str(draft["timestamp"]))
    cutoff = datetime.fromisoformat(str(draft["available_history_cutoff"]))
    event_evidence_id = f"event:{draft['current_event_id']}"
    evidence = [
        EvidenceRef(
            evidence_id=event_evidence_id,
            evidence_kind="current_event",
            source_url_or_id=str(draft["current_event_source_id"]),
            observed_at=datetime.fromisoformat(str(draft["current_event_observed_at"])),
            available_at=datetime.fromisoformat(str(draft["current_event_available_at"])),
            extraction_model=str(draft["event_extraction_model"]),
            dataset_version=str(draft["dataset_version"]),
        )
    ]
    activations = []
    for trace in retrieval_row["selected"]:
        evidence_id = f"memory:{trace['memory_id']}"
        provenance = trace["provenance"]
        evidence.append(
            EvidenceRef(
                evidence_id=evidence_id,
                evidence_kind="memory",
                source_url_or_id=str(provenance["source_url_or_id"]),
                observed_at=datetime.fromisoformat(str(provenance["source_timestamp"])),
                available_at=datetime.fromisoformat(str(provenance["available_at"])),
                extraction_model=str(provenance["extraction_model"]),
                dataset_version=str(provenance["dataset_version"]),
            )
        )
        activations.append(
            MemoryActivationSnapshot(
                memory_id=str(trace["memory_id"]),
                score=float(trace["score"]),
                components={str(key): float(value) for key, value in trace["components"].items()},
                contributions={
                    str(key): float(value) for key, value in trace["contributions"].items()
                },
                evidence_id=evidence_id,
            )
        )
    dimensions = {
        name: _estimate_map_from_dict(draft["dimensions"], name) for name in REQUIRED_DIMENSIONS
    }
    relationships = {
        str(key): RelationshipState.from_dict(value)
        for key, value in draft["relationships"].items()
    }
    temporary = HumanStateSnapshot(
        snapshot_id="",
        schema_version="ilhdt_human_state_v1",
        subject=str(draft["subject"]),
        timestamp=timestamp,
        available_history_cutoff=cutoff,
        current_event_id=str(draft["current_event_id"]),
        state_model_id=str(draft["state_model_id"]),
        dataset_version=str(draft["dataset_version"]),
        evidence_catalog=tuple(evidence),
        memory_activations=tuple(activations),
        emotion=dimensions["emotion"],
        relationships=relationships,
        preferences=dimensions["preferences"],
        goals=dimensions["goals"],
        habits=dimensions["habits"],
        personality=dimensions["personality"],
        context=dimensions["context"],
        uncertainty=derive_uncertainty(
            {
                **{
                    f"{name}.{key}": value
                    for name, values in dimensions.items()
                    for key, value in values.items()
                },
                **{
                    f"relationships.{entity_id}.{key}": value
                    for entity_id, relationship in relationships.items()
                    for key, value in relationship.fields.items()
                },
            },
            low_confidence_threshold,
        ),
    )
    return temporary.with_computed_id()
