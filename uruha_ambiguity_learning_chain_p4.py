"""P4-AI fixed-module composition of P4-AH -> P4-AF/AD -> P4-AG."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility
import uruha_desired_response_outcome_binding_p4 as binding
import uruha_multilingual_observable_trigger_p4 as trigger_coverage


SCHEMA = "uruha_p4_ai_fresh_ambiguity_learning_chain"


def run_fixed_chain_p4_ai(turn_1, turn_2, turn_index=1):
    state, _base_decision, _base_mode = ambiguity._isolated_inputs(turn_1, turn_index)
    trigger = trigger_coverage.extend_observable_trigger_p4(
        turn_1,
        state.get("observable_trigger_m37") or {},
    )
    shadow_state = trigger_coverage.apply_extended_trigger_to_shadow_state_p4(state, trigger)
    decision = adaptive.decide_response(shadow_state, adaptive.empty_model())
    mode = adaptive.build_desired_response_mode_contract(
        {"selected_type": "emotional_bid"},
        shadow_state,
        decision,
    )
    ledger = eligibility.build_desired_response_eligibility_guard_p4(
        shadow_state,
        decision,
        mode,
    )
    pending = binding.create_pending_outcome_binding_p4(ledger, decision, turn_index)
    feedback_model = binding.build_shadow_feedback_model_p4(pending, decision)
    _feedback_model, feedback = adaptive.observe_next_turn(
        feedback_model,
        turn_2,
        turn_index + 1,
    )
    resolution = binding.resolve_outcome_binding_p4(
        pending,
        feedback,
        turn_index + 1,
    )
    return {
        "schema": SCHEMA,
        "mode": "fixed_module_shadow_composition",
        "trigger": trigger,
        "eligibility": ledger.get("eligibility") or {},
        "ledger": ledger,
        "pending_binding": pending,
        "resolution": resolution,
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "fixed-module synthetic chain reachability; not private truth, visible quality or human preference"
        ),
    }


def build_dataset_evidence_p4_ai(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    sequences = []
    for index, frozen in enumerate(dataset["fresh_sequences"], start=1):
        trace = run_fixed_chain_p4_ai(frozen["turn_1"], frozen["turn_2"], 500 + index * 2)
        pending = trace["pending_binding"]
        resolved = trace["resolution"]
        updates = resolved.get("candidate_updates") or []
        selected = next((row for row in updates if row.get("policy_id") == pending.get("selected_policy")), {})
        replacement = next((row for row in updates if row.get("policy_id") == resolved.get("replacement_policy")), {}) if resolved.get("replacement_policy") else {}
        serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
        sequences.append(
            {
                "case_id": frozen["case_id"],
                "typed_trigger": "cognitive_overactivity" in set((trace["trigger"] or {}).get("predicates") or []),
                "eligibility_authorized": (trace["eligibility"] or {}).get("authorized") is True,
                "candidate_count": (trace["ledger"] or {}).get("candidate_count"),
                "first_policy": pending.get("selected_policy"),
                "identity_bound": resolved.get("identity_bound"),
                "outcome": resolved.get("outcome"),
                "replacement_policy": resolved.get("replacement_policy"),
                "selected_outcome": selected.get("outcome"),
                "selected_priority_allowed": selected.get("operational_priority_allowed"),
                "replacement_outcome": replacement.get("outcome"),
                "replacement_priority_allowed": replacement.get("operational_priority_allowed"),
                "all_candidates_unknown": all(row.get("outcome") == "unknown" for row in updates),
                "unknown_counted_as_success": resolved.get("unknown_counted_as_success"),
                "visible_reply_changed": trace.get("visible_reply_changed"),
                "new_model_call_count": int(trace.get("model_call_added") or 0),
                "fact_write_count": trace.get("fact_write_count"),
                "profile_write_count": trace.get("profile_write_count"),
                "episode_write_count": trace.get("episode_write_count"),
                "raw_dialogue_persisted": (
                    trace.get("raw_dialogue_persisted")
                    or frozen["turn_1"] in serialized
                    or frozen["turn_2"] in serialized
                ),
            }
        )
    frozen_rows = dataset["fresh_sequences"]
    return {
        "schema": "uruha_p4_ai_fresh_ambiguity_learning_chain_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "sequences": sequences,
        "metrics": {
            "sequence_count": len(sequences),
            "typed_trigger_count": sum(row["typed_trigger"] for row in sequences),
            "eligibility_authorized_count": sum(row["eligibility_authorized"] for row in sequences),
            "six_candidate_ledger_count": sum(row["candidate_count"] == 6 for row in sequences),
            "exact_identity_binding_count": sum(row["identity_bound"] for row in sequences),
            "exact_outcome_count": sum(row["outcome"] == frozen["expected_outcome"] for row, frozen in zip(sequences, frozen_rows)),
            "supported_selected_count": sum(row["outcome"] == "supported" and row["selected_outcome"] == "supported" and row["selected_priority_allowed"] is True for row in sequences),
            "contradicted_selected_revoked_count": sum(row["outcome"] == "contradicted" and row["selected_outcome"] == "contradicted" and row["selected_priority_allowed"] is False for row in sequences),
            "explicit_replacement_supported_count": sum(row["outcome"] == "contradicted" and row["replacement_outcome"] == "supported" and row["replacement_priority_allowed"] is True for row in sequences),
            "unknown_all_candidates_unknown_count": sum(row["outcome"] == "unknown" and row["all_candidates_unknown"] for row in sequences),
            "unknown_counted_as_success_count": sum(row["outcome"] == "unknown" and row["unknown_counted_as_success"] for row in sequences),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in sequences),
            "new_model_call_count": sum(row["new_model_call_count"] for row in sequences),
            "fact_write_count": sum(row["fact_write_count"] for row in sequences),
            "profile_write_count": sum(row["profile_write_count"] for row in sequences),
            "episode_write_count": sum(row["episode_write_count"] for row in sequences),
            "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in sequences),
        },
        "claim_boundary": dataset["claim_boundary"],
    }
