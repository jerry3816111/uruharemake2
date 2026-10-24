"""Opt-in answer authority for a selected relationship act.

Retrieval may legitimately surface a recent conversation about a quoted line.
That generic context is still useful evidence, but it is not an answer to a
current ``ask_miss_me`` act.  This adapter changes only the selected turn's
permission to quote a generic context anchor; it does not rerank, rewrite, or
persist any retrieved memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re

import uruha_adaptive_person_model as adaptive_person


LABEL = "relationship_context_answer_authority_p4"
SCHEMA = "uruha_relationship_context_answer_authority_p4"
_INSTALLED = False
_ORIGINAL_GRAVITY = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_SERIALIZED_ROLE = re.compile(r"(?:^|[^A-Za-z])(?:User|Uruha|Assistant)\s*[:：]", re.I)
_HIDDEN_FIELDS = ("my_hidden_knowledge", "user_expectation")
_PROTECTED_SCENES = set(adaptive_person.PROTECTED_SCENES) | {"support", "jealousy"}


def _sha(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _source_role(anchor, memory_data):
    """Return only auditable metadata, never an inferred user intention."""
    source = str(anchor.get("source") or "")
    source_text = str(anchor.get("source_text") or "")
    trace_id = str(anchor.get("trace_id") or "")
    def same_visible_source(item):
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        return (text if len(text) <= 120 else text[:119] + "…") == source_text

    matches = [
        item
        for item in (memory_data or {}).get("working_memory_items") or []
        if isinstance(item, dict)
        and str(item.get("source") or "") == source
        and (not trace_id or str(item.get("trace_id") or "") == trace_id)
        and same_visible_source(item)
    ]
    roles = {
        str((item.get("metadata") or {}).get("intent") or "")
        for item in matches
    }
    role = next(iter(roles)) if len(matches) == 1 and len(roles) == 1 else ""
    return role or "unavailable", len(matches)


def _is_protected(self, logic):
    route = (logic.get("semantic_route_m22") or {}).get("selected_type")
    runtime_route = (getattr(getattr(self, "runtime", None), "last_route", None) or {}).get("route")
    right_brain = getattr(self, "right_brain", None)
    structured = getattr(right_brain, "_structured_surface_required", lambda: False)()
    return bool(
        runtime_route != "high_road"
        or logic.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic.get("scene") in _PROTECTED_SCENES
        or route == "safety_sensitive"
        or runtime_route == "low_road"
        or structured
    )


def attach_relationship_context_answer_authority_p4(self, logic, user_input, memory_data):
    """Revoke *answer* authority, after the ordinary selected plan and anchor.

    The preceding gravity hook may have appended the anchor to hidden planning
    fields.  Restore those two fields if this particular anchor is revoked so
    it cannot reach a later surface through a secondary path.
    """
    before = {
        key: (key in logic, deepcopy(logic.get(key)))
        for key in _HIDDEN_FIELDS
    } if isinstance(logic, dict) else {}
    result = _ORIGINAL_GRAVITY(self, logic, user_input, memory_data)
    if not isinstance(result, dict) or result.get("intent") != "ask_miss_me" or _is_protected(self, result):
        return result
    anchor = result.get("memory_anchor") or {}
    if anchor.get("kind") != "context" or anchor.get("source") in {"profile", "current_input"}:
        return result

    role, match_count = _source_role(anchor, memory_data)
    receipt = {
        "schema": SCHEMA,
        "status": "generic_context_answer_authority_revoked",
        "selected_intent": "ask_miss_me",
        "selected_surface_act": str(result.get("surface_act") or ""),
        "selected_core_sha256": _sha(result.get("core_message_jp")),
        "rejected_anchor_kind": "context",
        "source": str(anchor.get("source") or "unavailable"),
        "source_trace_id": anchor.get("trace_id"),
        "source_memory_id": anchor.get("memory_id"),
        "source_role": role,
        "source_match_count": match_count,
        "prior_memory_use_expected": bool(result.get("memory_use_expected")),
        "prior_memory_speakability": str(result.get("memory_speakability") or ""),
        "answer_use_authorized": False,
        "retrieval_or_ranking_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "claim_boundary": "generic context is not a factual answer to a selected relationship act",
    }
    result.update({
        "memory_anchor": {},
        "memory_relevance": 0.0,
        "memory_relevance_label": "none",
        "memory_speakability": "no_memory",
        "memory_speakability_reason": "generic_context_not_answer_for_relationship_act",
        "memory_gravity": 0.0,
        "memory_use_expected": False,
        LABEL: receipt,
    })
    for key, (existed, value) in before.items():
        if existed:
            result[key] = value
        else:
            result.pop(key, None)
    return result


def materialize_relationship_context_answer_authority_p4(result):
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    receipt = logic.get(LABEL) or {}
    trace = result.get("runtime_trace")
    if receipt.get("schema") != SCHEMA or not isinstance(trace, dict):
        return result
    final = str(result.get("reply") or result.get("response") or "").strip()
    receipt = deepcopy(receipt)
    receipt["final_visible_surface_sha256"] = _sha(final)
    receipt["final_contains_serialized_memory_role"] = bool(_SERIALIZED_ROLE.search(final))
    receipt["selected_core_still_same"] = receipt.get("selected_core_sha256") == _sha(logic.get("core_message_jp"))
    receipt["semantic_product_gate"] = "requires_fresh_visible_turn_review"
    logic[LABEL] = receipt
    rows = [row for row in trace.get("blackboard") or [] if row.get("label") != LABEL]
    index = next(
        (i + 1 for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
        next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
    )
    rows.insert(index, {"stage": "select", "label": LABEL, "payload": deepcopy(receipt), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(receipt)
    return result


def install_relationship_context_answer_authority_p4():
    """Install only after the prior quoted-line product overlay."""
    global _INSTALLED, _ORIGINAL_GRAVITY, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_GRAVITY = UruhaBrainV4_Mac._attach_memory_gravity
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    UruhaBrainV4_Mac._attach_memory_gravity = attach_relationship_context_answer_authority_p4

    def finish(self, result):
        if not isinstance(result, dict) or (result.get("logic") or {}).get(LABEL, {}).get("schema") != SCHEMA:
            return result
        materialize_relationship_context_answer_authority_p4(result)
        trace = result.get("runtime_trace")
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (
                getattr(runtime, "turn_traces", None)
                and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")
            ):
                runtime.turn_traces[-1] = deepcopy(trace)
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, _ORIGINAL_EMIT(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "attach_relationship_context_answer_authority_p4",
    "materialize_relationship_context_answer_authority_p4",
    "install_relationship_context_answer_authority_p4",
]
