"""Product-only plan authority for selected profile memory acts.

The prior profile acknowledgement overlay owns the writer and final surface.
This layer only prevents a general M29 literal projection from becoming the
selected plan for that already-recognized act, then verifies the real selected
plan in the prior writeback truth node.  It never redraws a selected plan after
the core has chosen one.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib

import uruha_adaptive_person_model as adaptive_person
import uruha_explicit_preference_acknowledgement_p4 as p4h
import uruha_profile_write_ack_truth_p4 as ack


LABEL = "profile_plan_authority_repair_p4"
SCHEMA = "uruha_profile_plan_authority_repair_p4_v1"
_INSTALLED = False
_ORIGINAL_M29_CANDIDATE = None
_ORIGINAL_COGNITIVE_TICK = None
_ORIGINAL_CLASSIFY_SIGNAL = None
_ORIGINAL_ACK_MATERIALIZE = None
_ACTIVE_TURN = ContextVar("p4_profile_plan_authority_active_turn", default=None)


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def veto_m29_candidate_for_profile_memory_act_p4(
    candidate, user_input, preflight, *, protected=False
):
    """Veto only an actual M29 candidate for the same selected memory act."""
    if not isinstance(candidate, dict) or candidate.get("projection_required") is not True:
        return candidate
    if protected or not isinstance(preflight, dict):
        return candidate
    if (
        preflight.get("schema") != ack.SCHEMA
        or preflight.get("selected") is not True
        or preflight.get("act") not in p4h.AUTHORITATIVE_SURFACES
        or preflight.get("input_sha256") != _digest(str(user_input or "").strip())
    ):
        return candidate
    vetoed = deepcopy(candidate)
    vetoed.update(
        status="superseded_by_profile_memory_act_p4",
        reason="selected_profile_memory_act_outranks_general_literal_projection",
        projection_required=False,
        surface_authority=False,
        pre_veto_status=candidate.get("status"),
        pre_veto_reason=candidate.get("reason"),
        pre_veto_projection_required=candidate.get("projection_required"),
        pre_veto_surface_authority=candidate.get("surface_authority"),
        profile_memory_act=preflight.get("act"),
        profile_owner_reason=preflight.get("reason"),
        profile_input_sha256=preflight["input_sha256"],
        profile_ack_schema=ack.SCHEMA,
        model_call_added=False,
        raw_dialogue_persisted=False,
    )
    return vetoed


def _protected_before_m29(context):
    """Use this turn's classification, which occurs before M29 candidate build."""
    signal = context.get("actual_signal") if isinstance(context, dict) else None
    if not isinstance(signal, dict):
        return True  # No current-turn provenance: do not grant a new veto.
    seed = signal.get("seed_plan") or {}
    if not isinstance(seed, dict):
        return True
    return bool(
        signal.get("abuse_like")
        or str(signal.get("actual_intent") or "") in adaptive_person.PROTECTED_INTENTS
        or str(signal.get("actual_scene") or "") in adaptive_person.PROTECTED_SCENES
        or str(seed.get("intent") or "") in adaptive_person.PROTECTED_INTENTS
        or str(seed.get("scene") or "") in adaptive_person.PROTECTED_SCENES
    )


def classify_user_signal_with_profile_plan_authority_p4(
    self, user_input, current_psyche, memory_data=None
):
    signal = _ORIGINAL_CLASSIFY_SIGNAL(self, user_input, current_psyche, memory_data)
    context = _ACTIVE_TURN.get()
    if (
        isinstance(context, dict)
        and context.get("input_sha256") == _digest(str(user_input or "").strip())
    ):
        context["actual_signal"] = deepcopy(signal)
    return signal


def build_literal_topic_projection_candidate_with_profile_plan_authority_p4(
    user_input, adaptive_feedback, pragmatic_understanding,
    feedback_topic_transition_m28=None,
):
    candidate = _ORIGINAL_M29_CANDIDATE(
        user_input,
        adaptive_feedback,
        pragmatic_understanding,
        feedback_topic_transition_m28,
    )
    context = _ACTIVE_TURN.get()
    if not isinstance(context, dict):
        return candidate
    if context.get("input_sha256") != _digest(str(user_input or "").strip()):
        return candidate
    return veto_m29_candidate_for_profile_memory_act_p4(
        candidate,
        user_input,
        context.get("preflight"),
        protected=_protected_before_m29(context),
    )


def cognitive_tick_with_profile_plan_authority_p4(self, event):
    source = (event or {}).get("user_input")
    memory_data = (event or {}).get("memory_data") or {}
    preflight = memory_data.get(ack.LABEL) if isinstance(memory_data, dict) else None
    context = {
        "brain": self,
        "input_sha256": _digest(str(source or "").strip()),
        "preflight": deepcopy(preflight) if isinstance(preflight, dict) else None,
    }
    token = _ACTIVE_TURN.set(context)
    try:
        return _ORIGINAL_COGNITIVE_TICK(self, event)
    finally:
        _ACTIVE_TURN.reset(token)


def _expected_selected_plan(preflight):
    if preflight.get("admitted"):
        act = preflight.get("act")
        return (
            "explicit_preference_memory_correction"
            if act == "correction" else "explicit_preference_memory_write",
            p4h.AUTHORITATIVE_SURFACES.get(act),
        )
    return "profile_write_ack_rejected", ack._rejection_reply(preflight)


def _selected_plan_authority_audit(result, preflight):
    expected_intent, expected_core = _expected_selected_plan(preflight)
    logic = result.get("logic") or {}
    trace = result.get("runtime_trace") or {}
    rows = [
        row for row in trace.get("blackboard", [])
        if isinstance(row, dict) and row.get("label") == "selected_plan"
    ]
    payload = rows[0].get("payload") if len(rows) == 1 else None
    payload = payload if isinstance(payload, dict) else {}
    logic_matches = bool(
        logic.get("intent") == expected_intent
        and logic.get("core_message_jp") == expected_core
    )
    selected_matches = bool(
        len(rows) == 1
        and payload.get("intent") == expected_intent
        and payload.get("core_message_jp") == expected_core
    )
    return {
        "schema": SCHEMA,
        "status": "matched" if logic_matches and selected_matches else "mismatch",
        "reason": (
            "selected_profile_memory_act_plan_matches_preflight"
            if logic_matches and selected_matches
            else "selected_plan_or_logic_does_not_match_profile_memory_act"
        ),
        "input_sha256": preflight.get("input_sha256"),
        "expected_intent": expected_intent,
        "expected_core_sha256": _digest(expected_core),
        "actual_logic_intent": logic.get("intent"),
        "actual_logic_core_sha256": _digest(logic.get("core_message_jp")),
        "selected_plan_row_count": len(rows),
        "actual_selected_intent": payload.get("intent"),
        "actual_selected_core_sha256": _digest(payload.get("core_message_jp")),
        "logic_matches": logic_matches,
        "selected_plan_matches": selected_matches,
        "raw_dialogue_persisted": False,
    }


def materialize_profile_plan_authority_repair_p4(brain, result):
    """Extend the prior truth node; never rewrite the selected plan or reply."""
    result = _ORIGINAL_ACK_MATERIALIZE(brain, result)
    logic = result.get("logic") or {}
    prior_audit = logic.get(ack.LABEL)
    if not isinstance(prior_audit, dict) or prior_audit.get("schema") != ack.SCHEMA:
        return result
    if prior_audit.get("selected") is not True or prior_audit.get("protected_logic"):
        return result
    authority = _selected_plan_authority_audit(result, prior_audit)
    updated = deepcopy(prior_audit)
    checks = dict(updated.get("checks") or {})
    checks["selected_plan_authority"] = authority["status"]
    updated["checks"] = checks
    updated["selected_plan_authority"] = authority
    updated["status"] = (
        "mismatch" if "mismatch" in checks.values()
        else "unknown" if "unknown" in checks.values()
        else "matched"
    )
    updated["writeback_observed"] = bool(
        updated.get("writeback_observed") and updated["status"] == "matched"
    )
    logic[ack.LABEL] = deepcopy(updated)
    result["logic"] = logic
    trace = result.setdefault("runtime_trace", {})
    trace[ack.LABEL] = deepcopy(updated)
    for row in trace.get("blackboard", []):
        if isinstance(row, dict) and row.get("label") == ack.LABEL:
            row["payload"] = deepcopy(updated)
            row["salience"] = 0.99 if updated["status"] != "matched" else 0.9
    return result


def install_profile_plan_authority_repair_p4():
    global _INSTALLED, _ORIGINAL_M29_CANDIDATE, _ORIGINAL_COGNITIVE_TICK
    global _ORIGINAL_CLASSIFY_SIGNAL, _ORIGINAL_ACK_MATERIALIZE
    if _INSTALLED:
        return False
    if not ack._INSTALLED:
        raise ack.ProfileWriteAckIntegrityError(f"{LABEL}:profile_ack_overlay_not_installed")
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    _ORIGINAL_M29_CANDIDATE = adaptive_person.build_literal_topic_projection_candidate_m29
    _ORIGINAL_COGNITIVE_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_CLASSIFY_SIGNAL = LeftBrain.classify_user_signal
    _ORIGINAL_ACK_MATERIALIZE = ack.materialize_profile_write_ack_truth_p4
    adaptive_person.build_literal_topic_projection_candidate_m29 = (
        build_literal_topic_projection_candidate_with_profile_plan_authority_p4
    )
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_profile_plan_authority_p4
    LeftBrain.classify_user_signal = classify_user_signal_with_profile_plan_authority_p4
    ack.materialize_profile_write_ack_truth_p4 = materialize_profile_plan_authority_repair_p4
    _INSTALLED = True
    return True
