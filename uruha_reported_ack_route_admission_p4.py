"""Opt-in route admission for a bounded third-party reported-ack M31 defer.

Source/action proof alone cannot override a protected route.  The ordinary
reported-ack fast path additionally requires explicit, same-turn seed/router/
M22 evidence.  Absent or contradictory evidence returns to original M31.
This is routing evidence, not a statement about the speaker's mental state.
"""

from __future__ import annotations

from copy import deepcopy

import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_m31_priority_p4 as priority


SCHEMA = "uruha_reported_ack_route_admission_p4_v1"
CONTEXT_SCHEMA = "uruha_m31_route_context_p4_v1"
LABEL = "reported_ack_route_admission_p4"
_INSTALLED = False
_ORIGINAL_M31 = None


def route_admission_contract_p4(user_input, projection, context, certificate):
    """Decide only whether an existing source certificate may defer M31."""

    digest = priority._digest(str(user_input or ""))
    valid_certificate = bool(
        isinstance(certificate, dict)
        and certificate.get("schema") == priority.SCHEMA
        and certificate.get("status") == "source_qualified_reported_ack_precedes_m31"
        and certificate.get("source_kind") == "third_party_report"
        and certificate.get("actor") == "third_party"
        and certificate.get("action") == "reported_check_instruction"
        and certificate.get("input_digest") == digest
        and certificate.get("m31_model_call_skipped") is True
        and certificate.get("raw_dialogue_persisted") is False
        and certificate.get("private_state_truth_claimed") is False
    )
    result = {
        "schema": SCHEMA,
        "status": "rejected",
        "reason": "route_context_missing_or_malformed",
        "input_digest": digest,
        "source_certificate_present": valid_certificate,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "model_call_added_by_admission": False,
        "claim_boundary": "operational M31 admission, not private-state inference",
    }
    if not valid_certificate:
        result["status"] = "not_source_candidate"
        result["reason"] = "source_action_m29_certificate_absent"
        return result
    if not isinstance(context, dict) or context.get("schema") != CONTEXT_SCHEMA:
        return result
    if not isinstance(projection, dict) or not (
        context.get("input_digest") == digest
        and projection.get("input_digest") == digest
        and certificate.get("input_digest") == digest
    ):
        result["reason"] = "same_turn_digest_missing_or_mismatched"
        return result

    seed = context.get("seed_plan")
    route = context.get("route_info")
    m22 = context.get("semantic_route_m22")
    if not all(isinstance(item, dict) for item in (seed, route, m22)):
        return result
    result.update(
        {
            "seed_intent": seed.get("intent"),
            "seed_scene": seed.get("scene"),
            "signal_route": route.get("route"),
            "m22_task_shape": m22.get("selected_type"),
            "m22_recommended_route": m22.get("recommended_route"),
        }
    )
    if not (
        seed.get("intent") == "chat"
        and seed.get("scene") == "casual"
        and context.get("actual_intent") == "chat"
        and context.get("actual_scene") == "casual"
    ):
        result["reason"] = "seed_or_actual_signal_not_ordinary_chat"
        return result
    if not (
        route.get("route") == "high_road"
        and route.get("reason") == "deliberative"
        and not route.get("intent")
        and route.get("cognitive_hijack") in (None, False)
    ):
        result["reason"] = "protected_or_unverified_signal_route"
        return result
    if not (
        m22.get("schema") == "uruha_semantic_route_taxonomy_m22"
        and m22.get("selected_type") == "general_conversation"
        and m22.get("recommended_route") == "existing_guarded_router"
        and m22.get("decisive_evidence") == ["no_decisive_specialized_cue"]
        and m22.get("overlap_types") == []
        and isinstance(m22.get("candidates"), list)
        and len(m22["candidates"]) == 1
        and isinstance(m22["candidates"][0], dict)
        and m22["candidates"][0].get("task_type") == "general_conversation"
        and isinstance(m22.get("evidence"), list)
        and len(m22["evidence"]) == 1
        and isinstance(m22["evidence"][0], dict)
        and m22["evidence"][0].get("task_type") == "general_conversation"
        and m22["evidence"][0].get("cue_id") == "no_decisive_specialized_cue"
    ):
        result["reason"] = "m22_not_exclusively_general_conversation"
        return result
    if context.get("grounded_profile_logic_present") is not False:
        result["reason"] = "factual_grounding_present_or_unknown"
        return result

    result["status"] = "admitted"
    result["reason"] = "source_certificate_and_ordinary_route_agree"
    result["m31_model_call_skipped"] = True
    return result


def _call_original_m31(self, user_input, projection):
    if not callable(_ORIGINAL_M31):
        raise RuntimeError("route_admission_original_m31_unavailable")
    return _ORIGINAL_M31(self, user_input, projection)


def authorize_literal_topic_without_route_context_p4(self, user_input, projection):
    """Late repair and all contextless callers cannot inherit report priority."""

    return _call_original_m31(self, user_input, projection)


def authorize_literal_topic_with_route_context_p4(
    self, user_input, projection, context
):
    certificate = priority.reported_ack_m31_certificate_p4(
        user_input,
        projection,
        adaptive.classify_explicit_desired_response_m25,
    )
    admission = route_admission_contract_p4(
        user_input, projection, context, certificate
    )
    if admission["status"] == "admitted":
        plan, authorization = priority.authorize_literal_topic_with_reported_ack_priority_p4(
            self, user_input, projection
        )
        if (authorization or {}).get("status") != "deferred_to_reported_ack_p4":
            admission["status"] = "rejected"
            admission["reason"] = "source_certificate_changed_before_commit"
    else:
        plan, authorization = _call_original_m31(self, user_input, projection)
    authorization = deepcopy(authorization or {})
    authorization[LABEL] = admission
    return plan, authorization


def install_reported_ack_route_admission_p4():
    """Install after the earlier priority overlay in the new product entry."""

    global _INSTALLED, _ORIGINAL_M31
    if _INSTALLED:
        return False
    if not priority._INSTALLED or not callable(priority._ORIGINAL_M31):
        raise RuntimeError("reported_ack_m31_priority_must_be_installed_first")
    from uruha_brain_mac import LeftBrain

    if (
        LeftBrain.authorize_literal_topic_m31
        is not priority.authorize_literal_topic_with_reported_ack_priority_p4
    ):
        raise RuntimeError("reported_ack_m31_priority_chain_changed")
    _ORIGINAL_M31 = priority._ORIGINAL_M31
    LeftBrain.authorize_literal_topic_m31 = (
        authorize_literal_topic_without_route_context_p4
    )
    LeftBrain.authorize_literal_topic_m31_with_route_context_p4 = (
        authorize_literal_topic_with_route_context_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "SCHEMA", "CONTEXT_SCHEMA", "LABEL", "route_admission_contract_p4",
    "authorize_literal_topic_without_route_context_p4",
    "authorize_literal_topic_with_route_context_p4",
    "install_reported_ack_route_admission_p4",
]
