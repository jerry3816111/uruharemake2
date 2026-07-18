"""Generic temporal and contextual validity policy for retrieved memories."""

from __future__ import annotations

import datetime as dt


VALIDITY_FIELDS = frozenset(
    {
        "subject",
        "predicate",
        "fact_cardinality",
        "memory_state",
        "valid_from",
        "valid_until",
        "supersedes_ids",
        "condition_tags",
    }
)


def _candidate_id(candidate, index):
    return str(candidate.get("memory_id") or f"candidate:{index}")


def _parse_datetime(value):
    if isinstance(value, dt.datetime):
        return value
    if value in (None, ""):
        return None
    try:
        return dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _comparable(left, right):
    if left is None or right is None:
        return False
    return (left.tzinfo is None) == (right.tzinfo is None)


def _typed_contract(metadata):
    return any(field in metadata for field in VALIDITY_FIELDS)


def _valid_contract(metadata):
    if not metadata.get("subject") or not metadata.get("predicate"):
        return False
    if metadata.get("memory_state", "active") not in {"active", "retracted"}:
        return False
    if metadata.get("fact_cardinality") not in {None, "single", "multi"}:
        return False
    for field in ("valid_from", "valid_until"):
        if field in metadata and _parse_datetime(metadata[field]) is None:
            return False
    for field in ("supersedes_ids", "condition_tags"):
        if field in metadata and not isinstance(metadata[field], (list, tuple, set)):
            return False
    return True


def _identity(metadata):
    return (
        str(metadata.get("subject") or "").strip().casefold(),
        str(metadata.get("predicate") or "").strip().casefold(),
    )


def resolve_memory_validity(candidates, *, reference_time, condition_tags=()):
    """Partition candidates without deleting history or interpreting their text.

    Malformed or legacy metadata fails open so this policy cannot silently erase
    an existing memory. Callers can inspect ``decisions`` to migrate such rows.
    """
    now = _parse_datetime(reference_time)
    if now is None:
        raise ValueError("reference_time must be an ISO datetime or datetime instance")

    context = {str(tag).strip().casefold() for tag in condition_tags if str(tag).strip()}
    rows = []
    decisions = {}
    effective_superseders = []

    def classify(memory_id, partition, reason):
        decisions[memory_id] = {"partition": partition, "reason": reason}

    for index, candidate in enumerate(candidates or []):
        item = dict(candidate)
        item["metadata"] = dict(candidate.get("metadata") or {})
        memory_id = _candidate_id(item, index)
        rows.append((memory_id, item))
        metadata = item["metadata"]

        if not _typed_contract(metadata):
            classify(memory_id, "eligible", "legacy_metadata_fail_open")
            continue
        if not _valid_contract(metadata):
            classify(memory_id, "eligible", "invalid_contract_fail_open")
            continue

        valid_from = _parse_datetime(metadata.get("valid_from"))
        valid_until = _parse_datetime(metadata.get("valid_until"))
        if valid_from is not None and _comparable(now, valid_from) and now < valid_from:
            classify(memory_id, "inapplicable", "not_yet_valid")
            continue
        if valid_until is not None and _comparable(now, valid_until) and now > valid_until:
            classify(memory_id, "historical", "expired")
            continue

        required = {
            str(tag).strip().casefold()
            for tag in metadata.get("condition_tags") or []
            if str(tag).strip()
        }
        if required and not required.issubset(context):
            classify(memory_id, "inapplicable", "condition_mismatch")
            continue

        if metadata.get("memory_state", "active") == "retracted":
            classify(memory_id, "historical", "retraction_record")
            effective_superseders.append((memory_id, metadata))
            continue

        classify(memory_id, "eligible", "active")
        if metadata.get("supersedes_ids"):
            effective_superseders.append((memory_id, metadata))

    known_ids = {memory_id for memory_id, _ in rows}
    for _, metadata in effective_superseders:
        for target in metadata.get("supersedes_ids") or []:
            target_id = str(target)
            if target_id in known_ids and decisions[target_id]["partition"] == "eligible":
                classify(target_id, "historical", "explicitly_superseded")

    single_groups = {}
    for memory_id, item in rows:
        metadata = item["metadata"]
        if decisions[memory_id]["partition"] != "eligible":
            continue
        if not _valid_contract(metadata) or metadata.get("fact_cardinality") != "single":
            continue
        single_groups.setdefault(_identity(metadata), []).append((memory_id, metadata))

    for group in single_groups.values():
        dated = [(memory_id, _parse_datetime(metadata.get("valid_from"))) for memory_id, metadata in group]
        if len(dated) < 2 or any(value is None for _, value in dated):
            continue
        if any(not _comparable(dated[0][1], value) for _, value in dated[1:]):
            continue
        latest = max(value for _, value in dated)
        for memory_id, value in dated:
            if value < latest:
                classify(memory_id, "historical", "newer_single_value")

    result = {
        "eligible_candidates": [],
        "historical_candidates": [],
        "inapplicable_candidates": [],
        "decisions": decisions,
    }
    output_key = {
        "eligible": "eligible_candidates",
        "historical": "historical_candidates",
        "inapplicable": "inapplicable_candidates",
    }
    for memory_id, item in rows:
        result[output_key[decisions[memory_id]["partition"]]].append(item)
    return result
