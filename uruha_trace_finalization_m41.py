"""Deliver existing per-turn evidence to the graph; never invent cognition.

M39/M40 emit overlays were lost when run_turn_debug replaced the returned
blackboard with RuntimeState.blackboard. Synchronize at the owning runtime
boundary so both debug and event/voice delivery retain exactly the same nodes.
"""
from copy import deepcopy
import hashlib
import json


SOURCES_M41 = (
    ("lexical_boundary_route_m40", "uruha_evidence_bounded_lexical_route_m40", "route", "semantic_route_classifier_m22"),
    ("semantic_persona_surface_verifier_m39", "uruha_semantic_persona_surface_verifier_m39", "surface", "utterance"),
)
_INSTALLED_M41 = False


def materialize_current_trace_m41(result):
    """Update trace-only containers in place from the current final logic.

    No model call, inference, reply edit, file write, or memory mutation occurs.
    Existing missing/invalid sources remain unavailable, not simulated success.
    """
    logic = result.get("logic") or {}
    runtime_trace = result.setdefault("runtime_trace", {})
    rows = list(runtime_trace.get("blackboard") or [])
    audit = []
    for label, schema, stage, anchor in SOURCES_M41:
        payload = logic.get(label)
        if label == "lexical_boundary_route_m40" and not payload:
            payload = (logic.get("semantic_route_m22") or {}).get(label)
        previous_count = sum(r.get("label") == label for r in rows)
        rows = [r for r in rows if r.get("label") != label]
        valid = isinstance(payload, dict) and payload.get("schema") == schema and payload.get("raw_dialogue_persisted") is False
        entry = {"node_label": label, "source": "current_final_logic", "previous_node_count": previous_count,
                 "status": "source_unavailable_or_invalid", "inserted_count": 0}
        if valid:
            position = next((i for i, r in enumerate(rows) if r.get("label") == anchor), len(rows))
            entry.update({"status": "materialized", "inserted_count": 1,
                          "anchor": anchor, "anchor_present": position < len(rows),
                          "source_sha256": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
            rows.insert(position, {"stage": stage, "label": label, "payload": deepcopy(payload), "salience": 0.98})
            runtime_trace[label] = deepcopy(payload)
        else:
            # A stale prior payload must not appear as this turn's execution.
            runtime_trace.pop(label, None)
        audit.append(entry)
    trace = {
        "schema": "uruha_current_trace_finalization_m41",
        "status": "current_trace_materialized",
        "cycle_index": runtime_trace.get("cycle_index"),
        "sources": audit,
        "materialized_node_count": sum(e["inserted_count"] for e in audit),
        "reply_or_policy_changed": False,
        "memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": "delivery integrity for existing evidence; not a new understanding or safety decision",
    }
    runtime_trace["blackboard"] = rows
    runtime_trace["trace_finalization_m41"] = trace
    if isinstance(result.get("runtime_state"), dict):
        result["runtime_state"]["blackboard"] = deepcopy(rows)
    return trace


def install_m41_trace_finalizer():
    """Install after M39/M40 overlays; synchronize before final snapshots."""
    global _INSTALLED_M41
    if _INSTALLED_M41:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    original_emit = UruhaBrainV4_Mac.emit_response_if_ready

    def emit_with_current_trace(self, event, tick_result):
        result = original_emit(self, event, tick_result)
        materialize_current_trace_m41(result)
        # run_turn_debug's final snapshot reads this owner. Returning a patched
        # trace alone is insufficient, which was the actual Safari failure.
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        if self.runtime.turn_traces:
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_current_trace
    _INSTALLED_M41 = True
    return True
