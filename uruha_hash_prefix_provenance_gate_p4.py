"""Product-only provenance gate for legacy hash-selected discourse prefixes.

The old finalizer may append a fixed prefix after the response has already
been selected.  Such an addition has no source or plan authority.  This gate
removes only that *operation*, not a connective already present in the chosen
reply.  It does not validate arbitrary model-authored discourse or replace
the Japanese/persona/semantic guards.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib

import uruha_reported_offer_source_scope_p4 as reported_scope


LABEL = "hash_prefix_provenance_gate_p4"
SCHEMA = "uruha_hash_prefix_provenance_gate_p4_v1"
_FIXED_PREFIXES = ("ん、", "まあ、", "いや、", "てか、", "一回、", "先に、", "普通に、", "はいはい、")
_EVENT_KEY = "_hash_prefix_provenance_events_p4"
_INSTALLED = False
_ORIGINAL_FINALIZE = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _sha(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def finalize_with_hash_prefix_provenance_p4(self, reply, logic_data, user_input, max_chars):
    """Preserve the selected candidate unless the legacy method added a prefix."""
    legacy = _ORIGINAL_FINALIZE(self, reply, logic_data, user_input, max_chars)
    if not isinstance(legacy, str) or not isinstance(logic_data, dict):
        return legacy
    original = self._sanitize_reply(reply, max_chars=max_chars)
    if not isinstance(original, str) or not original:
        return legacy
    added = next((prefix for prefix in _FIXED_PREFIXES if legacy == prefix + original), None)
    if added is None:
        return legacy
    events = logic_data.setdefault(_EVENT_KEY, [])
    if isinstance(events, list) and len(events) < 16:
        events.append({
            "schema": SCHEMA,
            "action": "removed_unlicensed_hash_addition",
            "prefix": added,
            "selected_candidate_sha256": _sha(original),
            "legacy_candidate_sha256": _sha(legacy),
            "returned_candidate_sha256": _sha(original),
        })
    return original


def materialize_hash_prefix_provenance_p4(result):
    """Audit the *visible* reported-offer core; never trust an unused candidate."""
    if not isinstance(result, dict):
        return result
    logic, trace = result.get("logic"), result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    if logic.get("planner_path") != reported_scope.LABEL:
        return result
    selected, rows = trace.get("selected_plan"), trace.get("blackboard")
    if not isinstance(selected, dict) or not isinstance(rows, list):
        return result
    selected_rows = [r for r in rows if isinstance(r, dict) and r.get("label") == "selected_plan"]
    utterance_rows = [r for r in rows if isinstance(r, dict) and r.get("label") == "utterance"]
    if len(selected_rows) != 1 or len(utterance_rows) != 1:
        return result
    selected_row, utterance = selected_rows[0].get("payload"), utterance_rows[0].get("payload")
    if not isinstance(selected_row, dict) or not isinstance(utterance, dict):
        return result
    core = logic.get("core_message_jp")
    reply = result.get("reply")
    core_agrees = bool(
        isinstance(core, str) and core
        and selected.get("core_message_jp") == core
        and selected_row.get("core_message_jp") == core
    )
    prior_report = trace.get(reported_scope.LABEL)
    prior_report_matches = bool(
        isinstance(prior_report, dict)
        and prior_report.get("status") == "visible_report_preserved"
        and prior_report.get("admission_proof_matches") is True
        and prior_report.get("selected_plan_matches_logic") is True
        and prior_report.get("utterance_matches_reply") is True
        and prior_report.get("final_report_faithful") is True
    )
    utterance_agrees = isinstance(reply, str) and utterance.get("reply") == reply
    visible_core_exact = bool(core_agrees and prior_report_matches and utterance_agrees and reply == core)
    extra_fixed_prefix = next(
        (prefix for prefix in _FIXED_PREFIXES if core_agrees and reply == prefix + core),
        None,
    )
    events = logic.get(_EVENT_KEY)
    valid_events = [
        e for e in events
        if isinstance(e, dict) and e.get("schema") == SCHEMA
        and e.get("action") == "removed_unlicensed_hash_addition"
        and e.get("prefix") in _FIXED_PREFIXES
        and isinstance(reply, str)
        and e.get("returned_candidate_sha256") == e.get("selected_candidate_sha256") == _sha(reply)
        and e.get("legacy_candidate_sha256") == _sha(e["prefix"] + reply)
    ] if isinstance(events, list) else []
    status = (
        "visible_core_exact" if visible_core_exact
        else "unlicensed_fixed_prefix_visible" if extra_fixed_prefix
        else "selected_or_visible_mismatch"
    )
    certificate = {
        "schema": SCHEMA,
        "status": status,
        "source_scope": "reported_third_party_offer_to_user",
        "selected_core_agrees": core_agrees,
        "prior_report_audit_matches": prior_report_matches,
        "utterance_matches_reply": utterance_agrees,
        "visible_core_exact": visible_core_exact,
        "extra_fixed_prefix_visible": bool(extra_fixed_prefix),
        "extra_fixed_prefix": extra_fixed_prefix,
        "final_related_hash_additions_removed": len(valid_events),
        "removed_prefixes": [e["prefix"] for e in valid_events],
        "selected_core_sha256": _sha(core),
        "final_reply_sha256": _sha(reply),
        "prior_report_audit_status": (prior_report or {}).get("status") if isinstance(prior_report, dict) else None,
        "browser_bubble_observed": False,
        "model_call_added": False,
        "memory_write_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "hash-added prefix provenance and exact reported-offer core only; not open-domain naturalness",
    }
    without_prior = [r for r in rows if not (isinstance(r, dict) and r.get("label") == LABEL)]
    index = next(
        (i + 1 for i, r in enumerate(without_prior) if isinstance(r, dict) and r.get("label") == reported_scope.LABEL),
        next((i for i, r in enumerate(without_prior) if isinstance(r, dict) and r.get("label") == "utterance"), len(without_prior)),
    )
    without_prior.insert(index, {
        "stage": "verify", "label": LABEL, "payload": deepcopy(certificate),
        "salience": 0.97 if visible_core_exact else 1.0,
    })
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(certificate)
    logic[LABEL] = deepcopy(certificate)
    return result


def _finish(self, result):
    materialize_hash_prefix_provenance_p4(result)
    if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
        return result
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    trace = result["runtime_trace"]
    self.runtime.last_selected_plan = deepcopy(trace["selected_plan"])
    self.runtime.blackboard = deepcopy(trace["blackboard"])
    snapshot = result.get("runtime_state")
    if isinstance(snapshot, dict):
        snapshot["last_selected_plan"] = deepcopy(trace["selected_plan"])
    sync_current_history_m41_1(result)
    if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index"):
        self.runtime.turn_traces[-1] = deepcopy(trace)
    return result


def run_turn_debug_with_hash_prefix_provenance_p4(self, user_input, input_context=None):
    return _finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))


def emit_response_if_ready_with_hash_prefix_provenance_p4(self, event, tick_result):
    return _finish(self, _ORIGINAL_EMIT(self, event, tick_result))


def install_hash_prefix_provenance_gate_p4():
    """Install after the frozen reported-offer chain, once per product process."""
    global _INSTALLED, _ORIGINAL_FINALIZE, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    if not (
        reported_scope._INSTALLED
        and RightBrain._finalize_surface_reply.__module__ == "uruha_contextual_expression_commit_p2"
        and UruhaBrainV4_Mac.run_turn_debug is reported_scope.run_turn_debug_with_reported_offer_scope_p4
        and UruhaBrainV4_Mac.emit_response_if_ready is reported_scope.emit_response_if_ready_with_reported_offer_scope_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_FINALIZE = RightBrain._finalize_surface_reply
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    RightBrain._finalize_surface_reply = finalize_with_hash_prefix_provenance_p4
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_hash_prefix_provenance_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_hash_prefix_provenance_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "finalize_with_hash_prefix_provenance_p4",
    "materialize_hash_prefix_provenance_p4", "install_hash_prefix_provenance_gate_p4",
]
