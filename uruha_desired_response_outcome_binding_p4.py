"""P4-AG additive multi-turn binding for desired-response hypotheses.

This layer binds the existing P4-AF candidate ledger to the existing M16/M27
feedback result.  It does not infer private desire, alter a visible reply, add
a model call, or write factual memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility


LABEL = "desired_response_outcome_binding_p4"
SCHEMA = "uruha_desired_response_outcome_binding_p4"


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _binding_id(prediction_id, input_digest, selected_policy):
    material = "|".join(
        [SCHEMA, str(prediction_id or ""), str(input_digest or ""), str(selected_policy or "")]
    )
    return f"p4-ag-{_digest(material)[:24]}"


def create_pending_outcome_binding_p4(eligibility_trace, decision, turn_index=0):
    """Snapshot a raw-free first-turn candidate ledger with stable identities."""

    trace = deepcopy(eligibility_trace or {})
    decision = deepcopy(decision or {})
    selected = deepcopy(trace.get("selected_action") or {})
    selected_policy = str(selected.get("policy_id") or "")
    candidates = deepcopy(trace.get("candidate_expectations") or [])
    authorized = bool(
        (trace.get("eligibility") or {}).get("authorized")
        and trace.get("status") != "not_applicable"
        and selected_policy
        and candidates
    )
    input_digest = str(trace.get("input_digest") or "")[:64]
    prediction_id = str(decision.get("prediction_id") or "")[:80]
    if authorized and not prediction_id:
        prediction_id = f"p4-ag-pred-{_digest(f'{input_digest}|{selected_policy}|{int(turn_index)}')[:24]}"
    ledger_id = _binding_id(prediction_id, input_digest, selected_policy) if authorized else None
    candidate_snapshots = []
    for row in candidates if authorized else []:
        policy_id = str(row.get("policy_id") or "")
        candidate_snapshots.append(
            {
                "candidate_id": f"{ledger_id}:{policy_id}",
                "policy_id": policy_id,
                "mode": row.get("mode"),
                "operational_action_score": row.get("operational_action_score"),
                "score_semantics": row.get("score_semantics"),
                "selected_before_outcome": policy_id == selected_policy,
                "outcome": "pending",
                "operational_priority_allowed": policy_id == selected_policy,
                "selected_as_private_truth": False,
                "long_term_fact_write_allowed": False,
                "raw_dialogue_persisted": False,
            }
        )
    return {
        "schema": SCHEMA,
        "status": "pending" if authorized else "not_available",
        "ledger_id": ledger_id,
        "prediction_id": prediction_id if authorized else None,
        "prediction_id_source": (
            "existing_desired_response_decision"
            if authorized and decision.get("prediction_id")
            else "additive_shadow_identity"
            if authorized
            else "not_available"
        ),
        "turn_index": int(turn_index),
        "input_digest": input_digest if authorized else None,
        "selected_policy": selected_policy if authorized else None,
        "selected_mode": selected.get("mode") if authorized else None,
        "eligibility_authority": (trace.get("eligibility") or {}).get("authority"),
        "candidate_snapshots": candidate_snapshots,
        "candidate_count": len(candidate_snapshots),
        "unknown_counts_as_success": False,
        "private_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
    }


def build_shadow_feedback_model_p4(binding, decision=None):
    """Create an isolated model that asks the released feedback classifier only."""

    binding = deepcopy(binding or {})
    if binding.get("status") != "pending":
        return adaptive.empty_model()
    decision = deepcopy(decision or {})
    chosen = next(
        (
            row
            for row in (binding.get("candidate_snapshots") or [])
            if row.get("policy_id") == binding.get("selected_policy")
        ),
        {},
    )
    source_state = deepcopy(decision.get("state") or {})
    source_state["input_digest"] = binding.get("input_digest")
    shadow_decision = {
        "prediction_id": binding.get("prediction_id"),
        "selected": {
            "policy_id": binding.get("selected_policy"),
            "expected_utility": chosen.get("operational_action_score"),
            "response_dimensions": {},
            "realization": {},
        },
        "utility_margin": decision.get("utility_margin"),
        "state": source_state,
    }
    return adaptive.set_pending_prediction(adaptive.empty_model(), shadow_decision, binding.get("turn_index") or 0)


def resolve_outcome_binding_p4(binding, feedback, turn_index=0):
    """Bind second-turn evidence to the exact first-turn prediction identity."""

    binding = deepcopy(binding or {})
    feedback = deepcopy(feedback or {})
    exact_identity = bool(
        binding.get("status") == "pending"
        and binding.get("prediction_id")
        and feedback.get("previous_prediction_id") == binding.get("prediction_id")
    )
    linked = bool(exact_identity and feedback.get("feedback_linked_to_previous_prediction"))
    feedback_status = str(feedback.get("status") or "uncertain")
    outcome = feedback_status if linked and feedback_status in {"supported", "contradicted"} else "unknown"
    selected_policy = str(binding.get("selected_policy") or "")
    explicit_target = str(feedback.get("explicit_target_policy") or "")
    candidate_policy_ids = {
        str(row.get("policy_id") or "") for row in (binding.get("candidate_snapshots") or [])
    }
    replacement_policy = (
        explicit_target
        if outcome == "contradicted"
        and explicit_target
        and explicit_target != selected_policy
        and explicit_target in candidate_policy_ids
        else None
    )
    updates = []
    for before in binding.get("candidate_snapshots") or []:
        row = deepcopy(before)
        policy_id = str(row.get("policy_id") or "")
        candidate_outcome = "unknown"
        outcome_role = "unresolved_alternative"
        priority_allowed = False
        if outcome == "supported" and policy_id == selected_policy:
            candidate_outcome = "supported"
            outcome_role = "selected_action_explicitly_supported"
            priority_allowed = True
        elif outcome == "contradicted" and policy_id == selected_policy:
            candidate_outcome = "contradicted"
            outcome_role = "selected_action_explicitly_revoked"
        elif outcome == "contradicted" and policy_id == replacement_policy:
            candidate_outcome = "supported"
            outcome_role = "explicit_replacement_supported"
            priority_allowed = True
        row.update(
            {
                "outcome": candidate_outcome,
                "outcome_role": outcome_role,
                "operational_priority_allowed": priority_allowed,
                "selected_as_private_truth": False,
                "private_truth_claimed": False,
                "long_term_fact_write_allowed": False,
                "raw_dialogue_persisted": False,
            }
        )
        updates.append(row)
    next_use_policy = (
        selected_policy
        if outcome == "supported"
        else replacement_policy
        if outcome == "contradicted"
        else None
    )
    return {
        "schema": SCHEMA,
        "status": "resolved" if exact_identity else "identity_mismatch",
        "ledger_id": binding.get("ledger_id"),
        "prediction_id": binding.get("prediction_id"),
        "previous_prediction_id_observed": feedback.get("previous_prediction_id"),
        "identity_bound": exact_identity,
        "feedback_linked": linked,
        "outcome": outcome,
        "outcome_counts_as_success": outcome == "supported",
        "unknown_counted_as_success": False,
        "selected_policy_before": selected_policy or None,
        "replacement_policy": replacement_policy,
        "previous_candidate_revoked": outcome == "contradicted",
        "candidate_updates": updates,
        "observed_evidence": {
            "source": "released_adaptive_feedback_m16",
            "status": feedback_status,
            "linkage_reason": feedback.get("feedback_linkage_reason"),
            "evidence_digest": ((feedback.get("evidence") or {}).get("digest") or ""),
            "raw_text_persisted": False,
        },
        "reversible_next_use": {
            "status": "available" if next_use_policy else "not_available",
            "policy_id": next_use_policy,
            "authority": (
                "linked_explicit_support"
                if outcome == "supported"
                else "linked_explicit_replacement"
                if outcome == "contradicted" and replacement_policy
                else "none_unknown_outcome"
            ),
            "reversible": True,
            "private_truth_commitment": False,
            "factual_long_term_memory_write_allowed": False,
        },
        "turn_index": int(turn_index),
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "linked interaction feedback about an operational response action; "
            "not private desire truth or a factual user-memory claim"
        ),
    }


def append_outcome_binding_node_p4(result, trace):
    result = result or {}
    payload = deepcopy(trace or {})
    if not payload:
        return result
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "learn", "label": LABEL, "payload": payload, "salience": 0.98},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


_INSTALLED_P4_AG = False
_ORIGINAL_EMIT_RESPONSE_P4_AG = None


def install_desired_response_outcome_binding_p4():
    global _INSTALLED_P4_AG, _ORIGINAL_EMIT_RESPONSE_P4_AG
    if _INSTALLED_P4_AG:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AG = UruhaBrainV4_Mac.emit_response_if_ready

    def emit_with_p4_ag(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_AG(self, event, tick_result)
        user_input = str((event or {}).get("user_input") or "")
        previous_binding = deepcopy(getattr(self, "_p4_ag_pending_binding", {}) or {})
        shadow_model = deepcopy(getattr(self, "_p4_ag_shadow_feedback_model", {}) or {})
        previous_resolution = {
            "schema": SCHEMA,
            "status": "not_available",
            "reason": "no_previous_p4_ag_binding",
            "raw_dialogue_persisted": False,
        }
        if previous_binding.get("status") == "pending":
            shadow_model, feedback = adaptive.observe_next_turn(
                shadow_model,
                user_input,
                int((result or {}).get("runtime_state", {}).get("cycle_index") or 0),
            )
            previous_resolution = resolve_outcome_binding_p4(
                previous_binding,
                feedback,
                int((result or {}).get("runtime_state", {}).get("cycle_index") or 0),
            )
        runtime = (result or {}).get("runtime_trace") or {}
        logic = (result or {}).get("logic") or {}
        state = runtime.get("desired_response_state_m18") or logic.get("desired_response_state_m18") or {}
        decision = runtime.get("desired_response_decision_m18") or logic.get("desired_response_decision_m18") or {}
        current_ledger = runtime.get(ambiguity.LABEL) or logic.get(ambiguity.LABEL) or {}
        current_binding = create_pending_outcome_binding_p4(
            current_ledger,
            decision,
            int((result or {}).get("runtime_state", {}).get("cycle_index") or 0),
        )
        self._p4_ag_pending_binding = deepcopy(current_binding)
        self._p4_ag_shadow_feedback_model = build_shadow_feedback_model_p4(current_binding, decision)
        trace = {
            "schema": SCHEMA,
            "mode": "shadow_only",
            "previous_resolution": previous_resolution,
            "current_binding": current_binding,
            "visible_reply_changed": False,
            "model_call_added": False,
            "fact_write_count": 0,
            "profile_write_count": 0,
            "episode_write_count": 0,
            "raw_dialogue_persisted": False,
        }
        result = append_outcome_binding_node_p4(result, trace)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_ag
    _INSTALLED_P4_AG = True
    return True


def build_dataset_evidence_p4_ag(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    expected = [
        *(dict(row, partition="development_sequences") for row in dataset["development_sequences"]),
        *(dict(row, partition="fresh_sequences") for row in dataset["fresh_sequences"]),
    ]
    sequences = []
    for index, frozen in enumerate(expected, start=1):
        state, decision, mode = ambiguity._isolated_inputs(frozen["turn_1"], 300 + index * 2)
        first_trace = eligibility.build_desired_response_eligibility_guard_p4(state, decision, mode)
        pending = create_pending_outcome_binding_p4(first_trace, decision, 300 + index * 2)
        shadow_model = build_shadow_feedback_model_p4(pending, decision)
        _model_after, feedback = adaptive.observe_next_turn(
            shadow_model,
            frozen["turn_2"],
            301 + index * 2,
        )
        resolved = resolve_outcome_binding_p4(pending, feedback, 301 + index * 2)
        selected_update = next(
            (row for row in resolved["candidate_updates"] if row.get("policy_id") == pending.get("selected_policy")),
            {},
        )
        replacement_update = next(
            (row for row in resolved["candidate_updates"] if row.get("policy_id") == resolved.get("replacement_policy")),
            {},
        ) if resolved.get("replacement_policy") else {}
        serialized = json.dumps(resolved, ensure_ascii=False, sort_keys=True)
        sequences.append(
            {
                "case_id": frozen["case_id"],
                "partition": frozen["partition"],
                "first_turn_eligible": first_trace.get("status") != "not_applicable",
                "first_policy": pending.get("selected_policy"),
                "ledger_id": pending.get("ledger_id"),
                "prediction_id": pending.get("prediction_id"),
                "previous_prediction_id_observed": resolved.get("previous_prediction_id_observed"),
                "identity_bound": resolved.get("identity_bound"),
                "outcome": resolved.get("outcome"),
                "replacement_policy": resolved.get("replacement_policy"),
                "selected_candidate_outcome": selected_update.get("outcome"),
                "selected_candidate_priority_allowed": selected_update.get("operational_priority_allowed"),
                "replacement_candidate_outcome": replacement_update.get("outcome"),
                "replacement_candidate_priority_allowed": replacement_update.get("operational_priority_allowed"),
                "all_candidates_unknown": all(row.get("outcome") == "unknown" for row in resolved["candidate_updates"]),
                "previous_candidate_revoked": resolved.get("previous_candidate_revoked"),
                "unknown_counted_as_success": resolved.get("unknown_counted_as_success"),
                "visible_reply_changed": resolved.get("visible_reply_changed"),
                "new_model_call_count": int(resolved.get("model_call_added") or 0),
                "fact_write_count": resolved.get("fact_write_count"),
                "profile_write_count": resolved.get("profile_write_count"),
                "episode_write_count": resolved.get("episode_write_count"),
                "raw_dialogue_persisted": (
                    resolved.get("raw_dialogue_persisted")
                    or frozen["turn_1"] in serialized
                    or frozen["turn_2"] in serialized
                ),
            }
        )
    product_path = Path(__file__).with_name("uruha_web_ui_product_p4_ag.py")
    product_source = product_path.read_text(encoding="utf-8") if product_path.is_file() else ""
    predecessor_probe = {
        "reply": "unchanged",
        "logic": {ambiguity.LABEL: {"status": "ambiguity_preserved"}},
        "runtime_trace": {
            "blackboard": [
                {"stage": "select", "label": ambiguity.LABEL, "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    graph_probe = append_outcome_binding_node_p4(predecessor_probe, {"status": "pending"})
    labels = [row.get("label") for row in graph_probe["runtime_trace"]["blackboard"]]
    metrics = {
        "sequence_count": len(sequences),
        "first_turn_eligible_count": sum(row["first_turn_eligible"] for row in sequences),
        "first_policy_exact_count": sum(row["first_policy"] == frozen["expected_first_policy"] for row, frozen in zip(sequences, expected)),
        "stable_prediction_binding_count": sum(row["identity_bound"] for row in sequences),
        "exact_outcome_count": sum(row["outcome"] == frozen["expected_outcome"] for row, frozen in zip(sequences, expected)),
        "supported_selected_candidate_count": sum(row["outcome"] == "supported" and row["selected_candidate_outcome"] == "supported" and row["selected_candidate_priority_allowed"] is True for row in sequences),
        "contradicted_selected_candidate_count": sum(row["outcome"] == "contradicted" and row["selected_candidate_outcome"] == "contradicted" and row["selected_candidate_priority_allowed"] is False for row in sequences),
        "supported_explicit_replacement_count": sum(row["outcome"] == "contradicted" and row["replacement_candidate_outcome"] == "supported" and row["replacement_candidate_priority_allowed"] is True for row in sequences),
        "contradicted_previous_candidate_revoked_count": sum(row["outcome"] == "contradicted" and row["previous_candidate_revoked"] is True for row in sequences),
        "unknown_all_candidates_unknown_count": sum(row["outcome"] == "unknown" and row["all_candidates_unknown"] for row in sequences),
        "unknown_counted_as_success_count": sum(row["outcome"] == "unknown" and row["unknown_counted_as_success"] for row in sequences),
        "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in sequences),
        "new_model_call_count": sum(row["new_model_call_count"] for row in sequences),
        "fact_write_count": sum(row["fact_write_count"] for row in sequences),
        "profile_write_count": sum(row["profile_write_count"] for row in sequences),
        "episode_write_count": sum(row["episode_write_count"] for row in sequences),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in sequences),
    }
    return {
        "schema": "uruha_p4_ag_multiturn_ambiguity_outcome_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "sequences": sequences,
        "metrics": metrics,
        "integration": {
            "additive_product_entry_installs_binding": (
                "import uruha_web_ui_product_p4_af as _p4_af" in product_source
                and "install_desired_response_outcome_binding_p4()" in product_source
            ),
            "single_graph_node_before_utterance": labels == [ambiguity.LABEL, LABEL, "utterance"],
            "predecessor_node_retained": ambiguity.LABEL in labels,
        },
        "claim_boundary": dataset["claim_boundary"],
    }
