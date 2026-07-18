"""Typed persistence contract for user profile facts."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from uruha_memory_validity import VALIDITY_FIELDS, resolve_memory_validity


PREFERENCE_FACT_TYPES = frozenset({"favorite", "like", "dislike"})


def normalize_profile_value(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def profile_predicate(fact_type, value):
    """Return a language-independent state identity without interpreting content."""
    kind = str(fact_type or "").strip().casefold()
    normalized = normalize_profile_value(value)
    if not kind or not normalized:
        raise ValueError("fact_type and value are required")
    if kind == "name":
        return "preferred_name"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    namespace = "preference_item" if kind in PREFERENCE_FACT_TYPES else f"profile_fact:{kind}"
    return f"{namespace}:{digest}"


def compile_profile_memory_record(
    fact_type,
    value,
    *,
    timestamp,
    memory_id,
    typed_state,
):
    fact_type = str(fact_type).strip().casefold()
    value = str(value).strip()
    timestamp = str(timestamp).strip()
    memory_id = str(memory_id).strip()
    if not fact_type or not value or not timestamp or not memory_id:
        raise ValueError("fact_type, value, timestamp, and memory_id are required")
    metadata = {
        "fact_type": fact_type,
        "value": value,
        "timestamp": timestamp,
        "last_accessed_at": timestamp,
        "decay_flag": False,
        "decay_multiplier": 1.0,
    }
    if typed_state:
        metadata.update(
            {
                "subject": "user",
                "predicate": profile_predicate(fact_type, value),
                "fact_cardinality": "single",
                "memory_state": "active",
                "valid_from": timestamp,
            }
        )
    return {
        "memory_id": memory_id,
        "document": f"FactType={fact_type} | Value={value}",
        "metadata": metadata,
    }


def read_profile_candidates(collection):
    payload = collection.get(include=["documents", "metadatas"])
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [
        {
            "memory_id": str(memory_id),
            "text": str(document or ""),
            "metadata": dict(metadata or {}),
            "source": "profile",
            "collection_name": "profile",
            "distance": None,
            "retrieval_rank": index,
        }
        for index, (memory_id, document, metadata) in enumerate(zip(ids, documents, metadatas))
    ]


def profile_state_shadow_snapshot(collection, *, reference_time):
    """Observe persistent profile state without feeding it into answer generation."""
    candidates = read_profile_candidates(collection)
    resolved = resolve_memory_validity(candidates, reference_time=reference_time)
    decisions = resolved["decisions"]
    typed_ids = {
        row["memory_id"]
        for row in candidates
        if any(field in row["metadata"] for field in VALIDITY_FIELDS)
    }
    invalid_typed_ids = {
        memory_id
        for memory_id, decision in decisions.items()
        if decision["reason"] == "invalid_contract_fail_open"
    }
    eligible_ids = {row["memory_id"] for row in resolved["eligible_candidates"]}
    return {
        "status": "observed",
        "shadow_only": True,
        "affects_working_memory": False,
        "answer_use_authorized": False,
        "reference_time": str(reference_time),
        "candidate_count": len(candidates),
        "typed_candidate_count": len(typed_ids),
        "legacy_candidate_count": len(candidates) - len(typed_ids),
        "invalid_typed_candidate_count": len(invalid_typed_ids),
        "active_ids": [row["memory_id"] for row in resolved["eligible_candidates"]],
        "typed_active_ids": sorted((eligible_ids & typed_ids) - invalid_typed_ids),
        "legacy_eligible_ids": sorted(eligible_ids - typed_ids),
        "historical_ids": [row["memory_id"] for row in resolved["historical_candidates"]],
        "inapplicable_ids": [row["memory_id"] for row in resolved["inapplicable_candidates"]],
        "decision_reasons": {
            memory_id: decision["reason"] for memory_id, decision in decisions.items()
        },
    }
