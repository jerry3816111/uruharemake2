"""Inspectable temporal memory retrieval for the longitudinal human model.

The module deliberately stops before HumanState or behavior prediction.  It
turns provenance-bearing memory records into a cutoff-safe ranked retrieval
trace whose individual components can be removed for ablation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
import re
from typing import Any, Callable, Iterable, Mapping


COMPONENTS = (
    "semantic_relevance",
    "recency",
    "frequency",
    "importance",
    "emotional_salience",
    "relationship_relevance",
    "confidence",
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


def _unit_map(values: Mapping[str, float], field_name: str) -> dict[str, float]:
    clean: dict[str, float] = {}
    for key, value in values.items():
        if not str(key).strip():
            raise ValueError(f"{field_name} keys must be non-empty")
        clean[str(key)] = _unit(value, f"{field_name}.{key}")
    return clean


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    subject: str
    event: str
    timestamp_start: datetime
    timestamp_end: datetime
    available_at: datetime
    entities: tuple[str, ...]
    topics: tuple[str, ...]
    source_url_or_id: str
    source_timestamp: datetime
    confidence: float
    importance: float
    emotional_salience: Mapping[str, float]
    relationship_tags: Mapping[str, float]
    embedding_ref: str | None
    extraction_model: str
    dataset_version: str
    observation_count: int = 1
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    supersedes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for field_name in (
            "memory_id",
            "subject",
            "event",
            "source_url_or_id",
            "extraction_model",
            "dataset_version",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        start = _aware(self.timestamp_start, "timestamp_start")
        end = _aware(self.timestamp_end, "timestamp_end")
        available = _aware(self.available_at, "available_at")
        source = _aware(self.source_timestamp, "source_timestamp")
        if end < start:
            raise ValueError("timestamp_end must be at or after timestamp_start")
        if available < end:
            raise ValueError("available_at must be at or after timestamp_end")
        if source < start:
            raise ValueError("source_timestamp must be at or after timestamp_start")
        if self.valid_from is not None:
            _aware(self.valid_from, "valid_from")
        if self.valid_until is not None:
            _aware(self.valid_until, "valid_until")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be at or after valid_from")
        if int(self.observation_count) < 1:
            raise ValueError("observation_count must be at least 1")
        object.__setattr__(self, "confidence", _unit(self.confidence, "confidence"))
        object.__setattr__(self, "importance", _unit(self.importance, "importance"))
        object.__setattr__(
            self,
            "emotional_salience",
            _unit_map(self.emotional_salience, "emotional_salience"),
        )
        object.__setattr__(
            self,
            "relationship_tags",
            _unit_map(self.relationship_tags, "relationship_tags"),
        )

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "MemoryRecord":
        def parse(name: str) -> datetime:
            value = row.get(name)
            if not isinstance(value, str):
                raise ValueError(f"{name} must be an ISO-8601 string")
            return datetime.fromisoformat(value)

        def parse_optional(name: str) -> datetime | None:
            value = row.get(name)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError(f"{name} must be null or an ISO-8601 string")
            return datetime.fromisoformat(value)

        return cls(
            memory_id=str(row["memory_id"]),
            subject=str(row["subject"]),
            event=str(row["event"]),
            timestamp_start=parse("timestamp_start"),
            timestamp_end=parse("timestamp_end"),
            available_at=parse("available_at"),
            entities=tuple(str(value) for value in row.get("entities") or ()),
            topics=tuple(str(value) for value in row.get("topics") or ()),
            source_url_or_id=str(row["source_url_or_id"]),
            source_timestamp=parse("source_timestamp"),
            confidence=float(row["confidence"]),
            importance=float(row["importance"]),
            emotional_salience=dict(row.get("emotional_salience") or {}),
            relationship_tags=dict(row.get("relationship_tags") or {}),
            embedding_ref=(str(row["embedding_ref"]) if row.get("embedding_ref") else None),
            extraction_model=str(row["extraction_model"]),
            dataset_version=str(row["dataset_version"]),
            observation_count=int(row.get("observation_count") or 1),
            valid_from=parse_optional("valid_from"),
            valid_until=parse_optional("valid_until"),
            supersedes=tuple(str(value) for value in row.get("supersedes") or ()),
        )


@dataclass(frozen=True)
class MemoryQuery:
    query_id: str
    subject: str
    text: str
    prediction_time: datetime
    available_history_cutoff: datetime
    entities: tuple[str, ...] = field(default_factory=tuple)
    topics: tuple[str, ...] = field(default_factory=tuple)
    relationship_context: Mapping[str, float] = field(default_factory=dict)
    emotion_context: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("query_id", "subject", "text"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        prediction = _aware(self.prediction_time, "prediction_time")
        cutoff = _aware(self.available_history_cutoff, "available_history_cutoff")
        if cutoff > prediction:
            raise ValueError("available_history_cutoff cannot be after prediction_time")
        object.__setattr__(
            self,
            "relationship_context",
            _unit_map(self.relationship_context, "relationship_context"),
        )
        object.__setattr__(
            self,
            "emotion_context",
            _unit_map(self.emotion_context, "emotion_context"),
        )

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "MemoryQuery":
        return cls(
            query_id=str(row["query_id"]),
            subject=str(row["subject"]),
            text=str(row["text"]),
            prediction_time=datetime.fromisoformat(str(row["prediction_time"])),
            available_history_cutoff=datetime.fromisoformat(
                str(row["available_history_cutoff"])
            ),
            entities=tuple(str(value) for value in row.get("entities") or ()),
            topics=tuple(str(value) for value in row.get("topics") or ()),
            relationship_context=dict(row.get("relationship_context") or {}),
            emotion_context=dict(row.get("emotion_context") or {}),
        )


@dataclass(frozen=True)
class MemoryStrengthConfig:
    weights: Mapping[str, float]
    recency_half_life_days: float
    frequency_saturation_count: float

    def __post_init__(self) -> None:
        if set(self.weights) != set(COMPONENTS):
            missing = sorted(set(COMPONENTS) - set(self.weights))
            unknown = sorted(set(self.weights) - set(COMPONENTS))
            raise ValueError(f"weights must exactly match components; missing={missing}, unknown={unknown}")
        clean = {}
        for key, value in self.weights.items():
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"weight {key} must be finite and non-negative")
            clean[key] = number
        if not any(clean.values()):
            raise ValueError("at least one memory component weight must be positive")
        if not math.isfinite(self.recency_half_life_days) or self.recency_half_life_days <= 0:
            raise ValueError("recency_half_life_days must be positive")
        if (
            not math.isfinite(self.frequency_saturation_count)
            or self.frequency_saturation_count <= 0
        ):
            raise ValueError("frequency_saturation_count must be positive")
        object.__setattr__(self, "weights", clean)

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "MemoryStrengthConfig":
        return cls(
            weights=dict(row["weights"]),
            recency_half_life_days=float(row["recency_half_life_days"]),
            frequency_saturation_count=float(row["frequency_saturation_count"]),
        )


SemanticScorer = Callable[[MemoryRecord, MemoryQuery], float]


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\w'-]+", text, flags=re.UNICODE)}


def lexical_semantic_relevance(record: MemoryRecord, query: MemoryQuery) -> float:
    """A deterministic engineering proxy, not a learned semantic model."""

    memory_tokens = _tokens(" ".join((record.event, *record.topics, *record.entities)))
    query_tokens = _tokens(" ".join((query.text, *query.topics, *query.entities)))
    if not memory_tokens or not query_tokens:
        return 0.0
    return len(memory_tokens & query_tokens) / len(memory_tokens | query_tokens)


def _cosine_overlap(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    dot = sum(float(left.get(key, 0.0)) * float(right.get(key, 0.0)) for key in keys)
    left_norm = math.sqrt(sum(float(left.get(key, 0.0)) ** 2 for key in keys))
    right_norm = math.sqrt(sum(float(right.get(key, 0.0)) ** 2 for key in keys))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return min(1.0, max(0.0, dot / (left_norm * right_norm)))


def eligibility_reasons(record: MemoryRecord, query: MemoryQuery) -> list[str]:
    reasons: list[str] = []
    cutoff = query.available_history_cutoff
    if record.subject != query.subject:
        reasons.append("subject_mismatch")
    if record.timestamp_start > cutoff or record.timestamp_end > cutoff:
        reasons.append("event_after_cutoff")
    if record.available_at > cutoff:
        reasons.append("available_after_cutoff")
    if record.source_timestamp > cutoff:
        reasons.append("source_after_cutoff")
    if record.valid_from is not None and record.valid_from > query.prediction_time:
        reasons.append("not_yet_valid")
    if record.valid_until is not None and record.valid_until < query.prediction_time:
        reasons.append("expired")
    return reasons


def component_scores(
    record: MemoryRecord,
    query: MemoryQuery,
    config: MemoryStrengthConfig,
    *,
    semantic_scorer: SemanticScorer = lexical_semantic_relevance,
) -> dict[str, float]:
    semantic = _unit(semantic_scorer(record, query), "semantic_relevance")
    age_seconds = max(0.0, (query.prediction_time - record.timestamp_end).total_seconds())
    age_days = age_seconds / 86_400.0
    recency = 0.5 ** (age_days / config.recency_half_life_days)
    frequency = 1.0 - math.exp(-record.observation_count / config.frequency_saturation_count)
    return {
        "semantic_relevance": semantic,
        "recency": recency,
        "frequency": frequency,
        "importance": record.importance,
        "emotional_salience": _cosine_overlap(
            record.emotional_salience, query.emotion_context
        ),
        "relationship_relevance": _cosine_overlap(
            record.relationship_tags, query.relationship_context
        ),
        "confidence": record.confidence,
    }


def score_memory(
    record: MemoryRecord,
    query: MemoryQuery,
    config: MemoryStrengthConfig,
    *,
    semantic_scorer: SemanticScorer = lexical_semantic_relevance,
    ablate: Iterable[str] = (),
) -> dict[str, Any]:
    removed = set(ablate)
    unknown = removed - set(COMPONENTS)
    if unknown:
        raise ValueError(f"unknown ablation components: {sorted(unknown)}")
    scores = component_scores(record, query, config, semantic_scorer=semantic_scorer)
    effective_weights = {
        name: (0.0 if name in removed else float(config.weights[name])) for name in COMPONENTS
    }
    denominator = sum(effective_weights.values())
    if denominator <= 0:
        raise ValueError("ablation removed every positive-weight component")
    contributions = {
        name: effective_weights[name] * scores[name] / denominator for name in COMPONENTS
    }
    return {
        "memory_id": record.memory_id,
        "score": sum(contributions.values()),
        "components": scores,
        "effective_weights": effective_weights,
        "contributions": contributions,
        "ablated_components": sorted(removed),
        "provenance": {
            "source_url_or_id": record.source_url_or_id,
            "source_timestamp": record.source_timestamp.isoformat(),
            "available_at": record.available_at.isoformat(),
            "extraction_model": record.extraction_model,
            "dataset_version": record.dataset_version,
        },
        "validity": {
            "valid_from": record.valid_from.isoformat() if record.valid_from else None,
            "valid_until": record.valid_until.isoformat() if record.valid_until else None,
            "supersedes": list(record.supersedes),
        },
    }


def retrieve_memories(
    records: Iterable[MemoryRecord],
    query: MemoryQuery,
    config: MemoryStrengthConfig,
    *,
    top_k: int,
    semantic_scorer: SemanticScorer = lexical_semantic_relevance,
    ablate: Iterable[str] = (),
) -> dict[str, Any]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    scored: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in records:
        reasons = eligibility_reasons(record, query)
        if reasons:
            excluded.append({"memory_id": record.memory_id, "reasons": reasons})
            continue
        scored.append(
            score_memory(
                record,
                query,
                config,
                semantic_scorer=semantic_scorer,
                ablate=ablate,
            )
        )
    scored.sort(key=lambda row: (-row["score"], row["memory_id"]))
    selected = scored[:top_k]
    return {
        "query_id": query.query_id,
        "subject": query.subject,
        "prediction_time": query.prediction_time.isoformat(),
        "available_history_cutoff": query.available_history_cutoff.isoformat(),
        "top_k": top_k,
        "ablated_components": sorted(set(ablate)),
        "selected": selected,
        "eligible_ranked": scored,
        "excluded": sorted(excluded, key=lambda row: row["memory_id"]),
    }
