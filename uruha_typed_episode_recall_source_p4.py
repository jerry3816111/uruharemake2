"""Opt-in stored-record typing for the narrow P4 explicit-episode recall focus.

Chroma returns a turn and a consolidation summary from the same ``episode``
collection.  The ordinary retriever and visual candidate pool keep both.  Only
the focus adapter needs a copy in which a verified summary cannot masquerade as
a direct User utterance (or poison validation of a real one).
"""

from __future__ import annotations

from copy import deepcopy
import uuid

import uruha_explicit_episode_recall_focus_p4 as focus
import uruha_memory_runtime as umr


SCHEMA = "uruha_typed_episode_recall_source_p4"
_KINDS = frozenset({"turn_episode", "episodic_consolidation"})
_INSTALLED = False
_ORIGINAL_TRACE_ROW = None
_ORIGINAL_FOCUS_BUILDER = None


def trace_row_with_episode_record_kind_p4(candidate, *, rank=None, selected=None, channel=None):
    """Project only Chroma's bounded source enum, never its arbitrary metadata."""
    row = _ORIGINAL_TRACE_ROW(candidate, rank=rank, selected=selected, channel=channel)
    if row.get("source") != "episode":
        return row
    candidate = candidate or {}
    metadata = candidate.get("metadata")
    if isinstance(metadata, dict):
        kind = metadata.get("source")
        origin = "stored_metadata"
    else:
        # Focus handoff projects an already traced row a second time.  This
        # only preserves its audit label; candidate-pool validation below
        # requires the original stored_metadata origin.
        kind = candidate.get("episode_record_kind")
        origin = candidate.get("episode_record_kind_origin") or "unavailable"
    row["episode_record_kind"] = kind if isinstance(kind, str) and kind in _KINDS else "unavailable"
    row["episode_record_kind_origin"] = origin
    return row


def _episode_identity(row: dict) -> bool:
    memory_id = str(row.get("memory_id") or "")
    try:
        return (
            str(uuid.UUID(memory_id)) == memory_id
            and row.get("source") == "episode"
            and row.get("collection_name") == "episode"
            and row.get("trace_id") == f"stored:episode:{memory_id}"
            and isinstance(row.get("text"), str)
            and bool(row["text"].strip())
            and row.get("episode_record_kind") in _KINDS
            and row.get("episode_record_kind_origin") == "stored_metadata"
        )
    except (ValueError, AttributeError):
        return False


def _document_agrees_with_type(row: dict) -> bool:
    text = row["text"]
    kind = row["episode_record_kind"]
    if kind == "episodic_consolidation":
        return text.startswith("EpisodicSummary: ") and bool(text[len("EpisodicSummary: ") :].strip())
    return not text.startswith("EpisodicSummary:")


def _typed_focus_view(memory_data: dict) -> tuple[dict | None, dict, str | None]:
    """Validate same-query stored rows, then copy-filter only summary rows."""
    provenance = memory_data.get("memory_provenance")
    if not isinstance(provenance, dict):
        return None, {}, "memory_provenance_missing"
    pool = provenance.get("candidate_pool")
    retrieved = provenance.get("retrieved_candidates")
    selected_ids = provenance.get("selected_working_memory_trace_ids")
    passed = provenance.get("passed_to_leftbrain", [])
    passed_ids = provenance.get("passed_to_leftbrain_trace_ids", [])
    working_items = memory_data.get("working_memory_items", [])
    if not isinstance(pool, list) or not isinstance(retrieved, list) or not isinstance(selected_ids, list):
        return None, {}, "missing_provenance_lists"
    if (
        any(not isinstance(row, dict) for row in [*pool, *retrieved])
        or any(not isinstance(trace_id, str) for trace_id in selected_ids)
        or not isinstance(passed, list)
        or not isinstance(passed_ids, list)
        or not isinstance(working_items, list)
        or any(not isinstance(row, dict) for row in [*passed, *working_items])
        or any(not isinstance(trace_id, str) for trace_id in passed_ids)
        or provenance.get("candidate_count") != len(pool)
        or len(selected_ids) != len(set(selected_ids))
    ):
        return None, {}, "episode_record_type_provenance_mismatch"

    episode_pool = [row for row in pool if isinstance(row, dict) and row.get("source") == "episode"]
    episode_retrieved = [
        row for row in retrieved if isinstance(row, dict) and row.get("source") == "episode"
    ]
    ranked = {}
    seen_retrieved = set()
    for row in episode_retrieved:
        if not _episode_identity(row) or not _document_agrees_with_type(row):
            return None, {}, "episode_record_type_unverified"
        trace_id = row["trace_id"]
        if trace_id in seen_retrieved or row.get("channel") != "retrieved_candidate":
            return None, {}, "episode_record_type_provenance_mismatch"
        seen_retrieved.add(trace_id)
        status = row.get("ranking_status")
        if status == "ranked":
            ranked[trace_id] = row
        elif status != "deduplicated":
            return None, {}, "episode_record_type_provenance_mismatch"

    seen_pool = set()
    summaries = []
    for row in episode_pool:
        if not _episode_identity(row) or not _document_agrees_with_type(row):
            return None, {}, "episode_record_type_unverified"
        trace_id = row["trace_id"]
        original = ranked.get(trace_id)
        if (
            trace_id in seen_pool
            or original is None
            or row.get("channel") != "working_memory_candidate"
            or type(row.get("rank")) is not int
            or row["rank"] < 1
            or type(row.get("selected")) is not bool
            or row["selected"] != (trace_id in selected_ids)
            or any(
                row.get(field) != original.get(field)
                for field in (
                    "memory_id", "source", "collection_name", "text",
                    "episode_record_kind", "episode_record_kind_origin", "selected",
                )
            )
        ):
            return None, {}, "episode_record_type_provenance_mismatch"
        seen_pool.add(trace_id)
        if row["episode_record_kind"] == "episodic_consolidation":
            summaries.append(row)
    if seen_pool != set(ranked):
        return None, {}, "episode_record_type_provenance_mismatch"

    summary_ids = {row["trace_id"] for row in summaries}
    audit = {
        "schema": SCHEMA,
        "summary_candidate_count": len(summaries),
        "summary_candidate_ranks": sorted(row["rank"] for row in summaries),
        "summary_trace_ids": sorted(summary_ids),
        "summary_answer_authority": False,
        "original_candidate_count": len(pool),
        "direct_turn_candidate_count": sum(
            row["episode_record_kind"] == "turn_episode" for row in episode_pool
        ),
    }
    copied = deepcopy(memory_data)
    view = copied["memory_provenance"]
    view["candidate_pool"] = [row for row in view["candidate_pool"] if row.get("trace_id") not in summary_ids]
    view["retrieved_candidates"] = [
        row for row in view["retrieved_candidates"] if row.get("trace_id") not in summary_ids
    ]
    view["candidate_count"] = len(view["candidate_pool"])
    view["retrieved_candidate_count"] = len(view["retrieved_candidates"])
    view["selected_working_memory_trace_ids"] = [
        trace_id for trace_id in view["selected_working_memory_trace_ids"] if trace_id not in summary_ids
    ]
    view["passed_to_leftbrain"] = [
        row for row in view.get("passed_to_leftbrain", [])
        if row.get("trace_id") not in summary_ids
    ]
    view["passed_to_leftbrain_trace_ids"] = [
        trace_id for trace_id in view.get("passed_to_leftbrain_trace_ids", [])
        if trace_id not in summary_ids
    ]
    copied["working_memory_items"] = [
        row for row in copied.get("working_memory_items", [])
        if row.get("trace_id") not in summary_ids
    ]
    return copied, audit, None


def build_typed_episode_recall_focus_contract_p4(user_input: str, memory_data: dict) -> dict:
    query = focus.classify_explicit_episode_recall_focus_p4(user_input)
    if not query.get("eligible"):
        return _ORIGINAL_FOCUS_BUILDER(user_input, memory_data)
    copied, audit, error = _typed_focus_view(memory_data or {})
    if error:
        return {
            **focus._abstention(query, "unavailable", error),
            "typed_episode_audit": {"schema": SCHEMA, "status": "failed_closed", "reason": error},
        }
    contract = _ORIGINAL_FOCUS_BUILDER(user_input, copied)
    contract["typed_episode_audit"] = {**audit, "status": "verified"}
    return contract


def install_typed_episode_recall_source_p4() -> bool:
    """Install after the frozen focus and its classifier adapter, in one Web entry."""
    global _INSTALLED, _ORIGINAL_TRACE_ROW, _ORIGINAL_FOCUS_BUILDER
    if _INSTALLED:
        return False
    if not focus._INSTALLED:
        raise RuntimeError("install explicit episode focus before typed source adapter")
    _ORIGINAL_TRACE_ROW = umr.memory_trace_row
    _ORIGINAL_FOCUS_BUILDER = focus.build_explicit_episode_recall_focus_contract_p4
    umr.memory_trace_row = trace_row_with_episode_record_kind_p4
    focus.build_explicit_episode_recall_focus_contract_p4 = build_typed_episode_recall_focus_contract_p4
    _INSTALLED = True
    return True
