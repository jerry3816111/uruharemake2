"""M34 counterfactual pragmatic branch ledger.

The ledger makes desired-response selection falsifiable without treating a
pragmatic hypothesis as a fact about the user's private mind.  It records only
typed evidence, digests, candidate action branches, and observable next-turn
predictions.  It never persists raw dialogue or raw model output.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy


BRANCH_LEDGER_SCHEMA_M34 = "uruha_counterfactual_pragmatic_branch_ledger_m34"
BRANCH_PREDICTION_SCHEMA_M34 = "uruha_pragmatic_branch_prediction_m34"
BRANCH_VERIFICATION_SCHEMA_M34 = "uruha_pragmatic_branch_verification_m34"
BRANCH_REVISION_SCHEMA_M34 = "uruha_pragmatic_branch_revision_m34"
BRANCH_SURFACE_SCHEMA_M34 = "uruha_pragmatic_branch_surface_m34"


POLICY_TO_MODE = {
    "care_physiology": "physiological_care",
    "solve_regulation": "practical_help",
    "listen_presence": "listening",
    "share_arousal": "companionship",
    "playful_tease": "playful_tease",
    "calibrate_need": "low_pressure_clarification",
}


POLICY_TO_COMMUNICATIVE_GOAL = {
    "care_physiology": "stabilize_observable_physical_strain",
    "solve_regulation": "obtain_actionable_next_step",
    "listen_presence": "continue_disclosure_without_immediate_solution",
    "share_arousal": "seek_low_pressure_companionship",
    "playful_tease": "invite_affiliative_humor",
    "calibrate_need": "clarify_desired_response_form",
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _candidate_rows(decision, implicit_contract):
    decision = decision or {}
    implicit_contract = implicit_contract or {}
    distribution = {
        str(row.get("policy_id") or ""): row
        for row in (implicit_contract.get("distribution") or [])
        if row.get("policy_id")
    }
    rows = []
    for candidate in decision.get("candidates") or []:
        policy_id = str(candidate.get("policy_id") or "")
        if not policy_id:
            continue
        distribution_row = distribution.get(policy_id) or {}
        evidence = []
        for atom in distribution_row.get("relevant_evidence") or []:
            evidence.append(
                {
                    "kind": "desired_response_atom",
                    "atom": str(atom.get("atom") or "unknown"),
                    "status": str(atom.get("status") or "unknown"),
                    "evidence_quality": round(_number(atom.get("evidence_quality")), 4),
                    "learned_and_reversible": bool(atom.get("learned_and_reversible")),
                }
            )
        rows.append(
            {
                "policy_id": policy_id,
                "mode": POLICY_TO_MODE.get(policy_id, "unknown"),
                "communicative_goal_hypothesis": POLICY_TO_COMMUNICATIVE_GOAL.get(
                    policy_id,
                    "unknown",
                ),
                "operational_utility": round(
                    _number(candidate.get("expected_utility")),
                    4,
                ),
                "outcome_weighted_probability": round(
                    _number(distribution_row.get("outcome_weighted_probability")),
                    4,
                ),
                "evidence": evidence,
                "claim_status": "reversible_action_hypothesis_not_private_fact",
            }
        )
    rows.sort(
        key=lambda row: (
            -row["outcome_weighted_probability"],
            -row["operational_utility"],
            row["policy_id"],
        )
    )
    return rows


def _authority_basis(state, decision, implicit_contract, selected_policy):
    explicit = deepcopy(
        decision.get("explicit_desired_response_m25")
        or state.get("explicit_desired_response_m25")
        or {}
    )
    correction = deepcopy(
        decision.get("correction_aware_surface_m20")
        or state.get("correction_directive_m20")
        or {}
    )
    trigger_relation_m37 = deepcopy(decision.get("trigger_relation_m37") or {})
    if correction.get("authoritative"):
        return "current_explicit_correction"
    if explicit.get("authoritative"):
        return "current_explicit_response_form"
    if (
        trigger_relation_m37.get("authoritative")
        and trigger_relation_m37.get("status")
        == "matched_verified_trigger_relation"
        and trigger_relation_m37.get("selected_policy") == selected_policy
    ):
        return "verified_reversible_context"
    if selected_policy == "calibrate_need":
        return "uncertainty_guarded_abstention"
    if implicit_contract.get("execute_implicit"):
        if implicit_contract.get("learned_relevant_atoms"):
            return "verified_reversible_context"
        if implicit_contract.get("strong_current_observation"):
            return "strong_current_observable_evidence"
        return "bounded_implicit_execution"
    return "bounded_operational_selection"


def _previous_verification(previous_branch, adaptive_feedback):
    previous_branch = deepcopy(previous_branch or {})
    feedback = deepcopy(adaptive_feedback or {})
    previous_id = str(previous_branch.get("branch_id") or "")
    previous_policy = str(
        ((previous_branch.get("selected_branch") or {}).get("policy_id")) or ""
    )
    feedback_status = str(feedback.get("status") or "not_available")
    linked = bool(feedback.get("feedback_linked_to_previous_prediction"))
    if not previous_id:
        status = "not_available"
        reason = "no_previous_m34_branch"
    elif linked and feedback_status in {"supported", "contradicted"}:
        status = feedback_status
        reason = "decisive_feedback_linked_to_previous_branch"
    elif previous_id and feedback_status == "uncertain":
        status = "uncertain"
        reason = "next_turn_did_not_decisively_evaluate_previous_branch"
    else:
        status = "not_available"
        reason = "feedback_not_linked_to_previous_branch"
    explicit_target = str(feedback.get("explicit_target_policy") or "") or None
    return {
        "schema": BRANCH_VERIFICATION_SCHEMA_M34,
        "status": status,
        "reason": reason,
        "previous_branch_id": previous_id or None,
        "previous_prediction_id": previous_branch.get("prediction_id"),
        "previous_policy_id": previous_policy or None,
        "feedback_linked": linked,
        "feedback_status_m18": feedback_status,
        "replacement_policy_id": explicit_target if status == "contradicted" else None,
        "original_evidence_rewritten": False,
        "raw_feedback_persisted": False,
        "private_state_truth_claimed": False,
    }


def _revision(previous_verification):
    verification = deepcopy(previous_verification or {})
    contradicted = verification.get("status") == "contradicted"
    return {
        "schema": BRANCH_REVISION_SCHEMA_M34,
        "status": "branch_revised" if contradicted else "no_revision",
        "revoked_policy_id": (
            verification.get("previous_policy_id") if contradicted else None
        ),
        "replacement_policy_id": (
            verification.get("replacement_policy_id") if contradicted else None
        ),
        "original_branch_retained_for_audit": bool(
            verification.get("previous_branch_id")
        ),
        "original_evidence_rewritten": False,
        "fact_memory_write_count": 0,
        "raw_dialogue_persisted": False,
    }


def build_counterfactual_pragmatic_branch_m34(
    *,
    pragmatic_understanding,
    desired_response_state,
    desired_response_decision,
    implicit_response_contract,
    adaptive_feedback,
    source_semantic_atoms_m33=None,
    previous_branch_m34=None,
    turn_index=0,
):
    """Build a falsifiable desired-response branch without exposing raw text."""

    pragmatic = deepcopy(pragmatic_understanding or {})
    state = deepcopy(desired_response_state or {})
    decision = deepcopy(desired_response_decision or {})
    implicit_contract = deepcopy(implicit_response_contract or {})
    source_atoms = deepcopy(source_semantic_atoms_m33 or {})
    candidates = _candidate_rows(decision, implicit_contract)
    selected = deepcopy(decision.get("selected") or {})
    selected_policy = str(selected.get("policy_id") or "")
    selected_mode = POLICY_TO_MODE.get(selected_policy)
    selected_candidate = next(
        (deepcopy(row) for row in candidates if row["policy_id"] == selected_policy),
        {},
    )
    runner_up = next(
        (deepcopy(row) for row in candidates if row["policy_id"] != selected_policy),
        {},
    )
    previous_verification = _previous_verification(
        previous_branch_m34,
        adaptive_feedback,
    )
    revision = _revision(previous_verification)
    acoustic = pragmatic.get("acoustic_evidence") or {}
    learned_atoms = list(state.get("learned_atoms_used") or [])
    used_scopes = [
        {
            "level": row.get("level"),
            "source_scope_id": row.get("source_scope_id"),
            "kind": row.get("kind"),
            "name": row.get("name"),
        }
        for row in ((state.get("scope_match") or {}).get("used") or [])
    ]
    current_digest = str(state.get("input_digest") or "")
    branch_id = (
        "m34-"
        + _digest(
            "|".join(
                [
                    str(turn_index),
                    str(decision.get("prediction_id") or ""),
                    selected_policy,
                    str((state.get("context_scope") or {}).get("scope_id") or ""),
                    current_digest,
                ]
            )
        )
    )
    authority_basis = _authority_basis(
        state,
        decision,
        implicit_contract,
        selected_policy,
    )
    selected_branch = {
        **selected_candidate,
        "policy_id": selected_policy or None,
        "mode": selected_mode,
        "authority_basis": authority_basis,
        "uncertainty": round(_number(implicit_contract.get("uncertainty")), 4),
        "selection_is_private_state_fact": False,
    }
    prediction = {
        "schema": BRANCH_PREDICTION_SCHEMA_M34,
        "branch_id": branch_id,
        "prediction_id": decision.get("prediction_id"),
        "selected_policy_id": selected_policy or None,
        "expected_next_observable_behavior": (
            "explicit_affirmation_or_continuation_consistent_with_selected_mode"
            if selected_policy and selected_policy != "calibrate_need"
            else "explicit_response_form_choice_or_continued_ambiguity"
        ),
        "contradiction_observation": "explicit_rejection_or_different_response_form_request",
        "verification_window": "next_user_turn",
        "private_state_prediction": False,
        "raw_dialogue_persisted": False,
    }
    status = "branch_selected" if selected_policy else "not_applied"
    return {
        "schema": BRANCH_LEDGER_SCHEMA_M34,
        "status": status,
        "branch_id": branch_id,
        "prediction_id": decision.get("prediction_id"),
        "turn_index": int(turn_index),
        "literal_observation": {
            "current_input_digest": current_digest,
            "pragmatic_label": pragmatic.get("pragmatic_label") or "unknown",
            "visible_signal_ids": sorted(
                set((pragmatic.get("visible_signal_ids") or []))
            ),
            "source_atom_status_m33": source_atoms.get("status") or "unavailable",
            "source_atom_types_m33": sorted(
                set(source_atoms.get("atom_types") or [])
            ),
            "acoustic_evidence_availability": acoustic.get("availability") or "unavailable",
            "acoustic_evidence_reliable": bool(acoustic.get("reliable")),
        },
        "candidate_branches": candidates,
        "selected_branch": selected_branch,
        "bounded_alternative": runner_up or None,
        "context_evidence": {
            "scope_id": (state.get("context_scope") or {}).get("scope_id"),
            "scope_match_status": (state.get("scope_match") or {}).get("status"),
            "verified_reversible_atoms": learned_atoms,
            "used_scopes": used_scopes,
            "current_explicit_authority": authority_basis.startswith("current_explicit"),
            "verified_context_authority": authority_basis == "verified_reversible_context",
        },
        "observable_prediction": prediction,
        "previous_branch_verification": previous_verification,
        "revision": revision,
        "surface_status": "pending" if selected_policy else "not_applicable",
        "evidence_boundary": {
            "known": "visible current signals and verified reversible interaction history",
            "inferred": "communicative goal and desired response are action hypotheses",
            "unknown": "private intent, private emotion, and human subjective preference",
            "unverified_mental_state_fact_write_allowed": False,
        },
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "fact_memory_write_count": 0,
        "claim_boundary": "counterfactual operational branch, not mind reading or private-state ground truth",
    }


def audit_pragmatic_branch_surface_m34(reply, logic, branch_ledger):
    """Audit that the already-selected branch reached the guarded surface."""

    audited = deepcopy(branch_ledger or {})
    selected_policy = str(
        ((audited.get("selected_branch") or {}).get("policy_id")) or ""
    )
    performed_policy = str((logic or {}).get("desired_response_policy_m18") or "")
    explicit = (logic or {}).get("explicit_desired_response_m25") or {}
    mode_contract = (logic or {}).get("desired_response_mode_m23") or {}
    relevant_surface = str(
        explicit.get("surface_status")
        if explicit.get("authoritative")
        else mode_contract.get("surface_status")
        or "not_applicable"
    )
    if not selected_policy:
        status = "not_applicable"
    elif performed_policy == selected_policy and relevant_surface in {
        "matched",
        "not_applicable",
    } and str(reply or "").strip():
        status = "matched"
    else:
        status = "mismatch"
    audited["surface_status"] = status
    audited["surface_audit_m34"] = {
        "schema": BRANCH_SURFACE_SCHEMA_M34,
        "status": status,
        "selected_policy_id": selected_policy or None,
        "performed_policy_id": performed_policy or None,
        "lower_surface_contract_status": relevant_surface,
        "reply_digest": _digest(reply),
        "raw_reply_persisted": False,
    }
    return audited
