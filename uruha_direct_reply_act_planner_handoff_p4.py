"""Transient, opt-in handoff of an observed User reply act to the full planner.

This is an action constraint, not a desired-response truth label or a surface
template.  It may be constructed only from the current turn's admitted M29
certificate and is revalidated at the planner boundary.
"""

from __future__ import annotations

from uruha_direct_reply_act_m29_priority_p4 import (
    LABEL as M29_LABEL,
    SCHEMA as M29_SCHEMA,
    _sha,
    classify_direct_reply_act_p4,
)


LABEL = "direct_reply_act_planner_handoff_p4"
SCHEMA = "uruha_direct_reply_act_planner_handoff_p4_v1"
ARM_ENV = "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"
_ACTS = {"brief_care", "brief_encouragement"}


def validate_handoff_p4(source: str, projection: dict, source_atoms: dict) -> dict | None:
    """Fail closed on source, M29 authority, or competing M33 source atoms."""
    if not isinstance(source, str) or not isinstance(projection, dict) or not isinstance(source_atoms, dict):
        return None
    admitted = projection.get(M29_LABEL)
    expected = classify_direct_reply_act_p4(source)
    if not isinstance(admitted, dict) or expected["status"] != "direct":
        return None
    if not (
        projection.get("status") == "direct_reply_act_precedes_literal_projection_p4"
        and projection.get("projection_required") is False
        and projection.get("surface_authority") is False
        and projection.get("input_digest") == expected["input_sha256"][:16]
        and not projection.get("source_statement_priority_p4")
        and not projection.get("source_bound_preference_priority_p4")
        and not projection.get("required_observable_act")
        # The admission gate already checked the original M33 candidate as
        # unavailable.  After M29 veto, the actual M33 pass is not_applicable
        # because projection_required is now false; it must not be extracted.
        and source_atoms.get("status") == "not_applicable"
        and source_atoms.get("reason") == "m29_projection_not_required"
        and admitted.get("schema") == M29_SCHEMA
        and admitted.get("status") == "admitted_direct_reply_act"
        and admitted.get("source_kind") == "current_user_direct_request"
        and admitted.get("original_projection_required") is True
        and admitted.get("original_m33_status") == "source_pattern_unavailable"
        and admitted.get("m29_projection_after") is False
        and admitted.get("requested_act") in _ACTS
    ):
        return None
    for key in ("input_sha256", "cue_sha256", "cue_span", "requested_act"):
        if admitted.get(key) != expected[key]:
            return None
    return {
        "schema": SCHEMA,
        "requested_act": expected["requested_act"],
        "input_sha256": expected["input_sha256"],
        "cue_sha256": expected["cue_sha256"],
        "cue_span": expected["cue_span"],
        "source_kind": "current_user_direct_request",
        "m29_status": projection["status"],
        "m33_status": source_atoms["status"],
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def planner_constraint_p4(source: str, handoff: dict | None) -> str:
    """Return one internal prompt segment only for a still-matching source."""
    if not isinstance(handoff, dict) or handoff.get("schema") != SCHEMA:
        return ""
    expected = classify_direct_reply_act_p4(source)
    if expected["status"] != "direct" or any(
        handoff.get(key) != expected[key]
        for key in ("requested_act", "input_sha256", "cue_sha256", "cue_span")
    ):
        return ""
    if handoff.get("source_kind") != "current_user_direct_request" or (
        handoff.get("m29_status") != "direct_reply_act_precedes_literal_projection_p4"
        or handoff.get("m33_status") != "not_applicable"
    ):
        return ""
    action = {
        "brief_care": "briefly acknowledge and appreciate the User's stated effort",
        "brief_encouragement": "offer one brief, modest encouragement",
    }.get(handoff["requested_act"])
    if action is None:
        return ""
    # Digest fields make the binding inspectable without copying raw dialogue
    # into the plan or graph.  The exact source remains in the existing User
    # message, not in this added system segment.
    return (
        "\n[Current User direct reply act — P4 opt-in]\n"
        f"source_sha256={handoff['input_sha256']}\n"
        f"cue_sha256={handoff['cue_sha256']}\n"
        f"requested_act={handoff['requested_act']}\n"
        f"For each candidate plan, {action}. A bare restatement of the event "
        "does not fulfil this explicit request. Do not infer an unreported "
        "emotion, fatigue, achievement, private motive, or desired reply. "
        "Keep the eventual Japanese utterance natural and short; this is an "
        "internal planning constraint, not text to quote to the User.\n"
    )


def route_receipt_p4(*, arm: str, source: str, handoff: dict | None, route: str,
                     planner_prompt_injected: bool) -> dict:
    """Bounded, raw-free evidence of the actual route and intervention."""
    certificate = handoff if isinstance(handoff, dict) else None
    eligible = certificate is not None
    injected = bool(arm == "treatment" and route == "full_planner" and eligible and planner_prompt_injected)
    if not eligible:
        status = "not_admitted"
    elif route != "full_planner":
        status = "not_full_planner"
    elif arm == "control":
        status = "control_no_handoff"
    elif injected:
        status = "treatment_prompt_injected"
    else:
        status = "treatment_handoff_not_injected"
    return {
        "schema": SCHEMA,
        "arm": arm,
        "status": status,
        "actual_route": route,
        "requested_act": certificate.get("requested_act") if eligible else None,
        "input_sha256": _sha(source),
        "cue_sha256": certificate.get("cue_sha256") if eligible else None,
        "m29_status": certificate.get("m29_status") if eligible else None,
        "m33_status": certificate.get("m33_status") if eligible else None,
        "planner_prompt_injected": injected,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }
