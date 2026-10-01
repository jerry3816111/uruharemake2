"""P4-AL auditable past-present-future commitment cycle.

Past contains only provenance-bearing observations earlier than the present
turn.  Present contains observable evidence and competing operational action
hypotheses.  Future is committed before linked outcome evidence is available.
After observation, that outcome may become a non-factual evidence record for a
later turn.  None of these fields claim access to a private mental state.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_outcome_binding_p4 as outcome_binding


SCHEMA = "uruha_past_present_future_commitment_p4"
RESOLUTION_SCHEMA = "uruha_past_present_future_resolution_p4"
LABEL = "past_present_future_commitment_p4"

_PAST_FIELDS = {
    "evidence_id",
    "observed_turn",
    "source_kind",
    "epistemic_status",
    "provenance_digest",
}
_PAST_STATUSES = {"supported", "revoked", "unknown"}
_FORBIDDEN_KEYS = {
    "raw_text",
    "user_input",
    "dialogue",
    "private_emotion",
    "private_motive",
    "private_desire",
    "actual_outcome",
    "observed_outcome",
    "target_reply",
}


class P4ALTemporalError(ValueError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _forbidden_paths(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in _FORBIDDEN_KEYS:
                found.append(path)
            found.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{prefix}[{index}]"))
    return found


def _validated_past(past_records, present_turn):
    if not isinstance(past_records, list) or not past_records:
        raise P4ALTemporalError("past_records_required")
    observed = []
    seen = set()
    for row in past_records:
        if not isinstance(row, dict) or set(row) != _PAST_FIELDS:
            raise P4ALTemporalError("past_record_shape_invalid")
        evidence_id = str(row.get("evidence_id") or "")
        turn = row.get("observed_turn")
        status = str(row.get("epistemic_status") or "")
        digest = str(row.get("provenance_digest") or "")
        if not evidence_id or evidence_id in seen:
            raise P4ALTemporalError("past_evidence_identity_invalid")
        if isinstance(turn, bool) or not isinstance(turn, int) or turn >= present_turn or turn < 0:
            raise P4ALTemporalError("past_not_strictly_before_present")
        if status not in _PAST_STATUSES:
            raise P4ALTemporalError("past_epistemic_status_invalid")
        if len(digest) < 16:
            raise P4ALTemporalError("past_provenance_digest_invalid")
        seen.add(evidence_id)
        observed.append(deepcopy(row))
    observed.sort(key=lambda row: (row["observed_turn"], row["evidence_id"]))
    return observed


def build_temporal_commitment_p4(past_records, pending_binding, present_turn):
    """Commit current operational hypotheses before any next-turn outcome."""

    present_turn = int(present_turn)
    past = _validated_past(past_records, present_turn)
    pending = deepcopy(pending_binding or {})
    if pending.get("schema") != outcome_binding.SCHEMA or pending.get("status") != "pending":
        raise P4ALTemporalError("pending_binding_invalid")
    if pending.get("turn_index") != present_turn:
        raise P4ALTemporalError("present_turn_binding_mismatch")
    candidates = pending.get("candidate_snapshots") or []
    if pending.get("candidate_count") != 6 or len(candidates) != 6:
        raise P4ALTemporalError("six_candidate_binding_required")
    present_candidates = []
    for row in candidates:
        present_candidates.append(
            {
                "candidate_id": row.get("candidate_id"),
                "policy_id": row.get("policy_id"),
                "mode": row.get("mode"),
                "operational_action_score": row.get("operational_action_score"),
                "score_semantics": row.get("score_semantics"),
                "selected": row.get("policy_id") == pending.get("selected_policy"),
                "epistemic_status": "inferred_operational_action_hypothesis",
                "private_truth_claimed": False,
            }
        )
    material = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "past": {
            "status": "observed_before_present",
            "records": past,
            "record_count": len(past),
            "strictly_before_present": True,
        },
        "present": {
            "turn_index": present_turn,
            "input_digest": pending.get("input_digest"),
            "ledger_id": pending.get("ledger_id"),
            "prediction_id": pending.get("prediction_id"),
            "known": ["provenance_bound_past_observations", "current_input_digest"],
            "inferred": present_candidates,
            "unknown": [
                "private_reason_for_current_utterance",
                "which_response_will_be_accepted",
                "next_turn_observable_outcome",
            ],
            "selected_policy": pending.get("selected_policy"),
            "candidate_count": len(present_candidates),
            "selection_is_private_truth_commitment": False,
        },
        "future": {
            "status": "committed_outcome_locked",
            "target": "next_turn_linked_response_action_feedback",
            "earliest_observable_turn": present_turn + 1,
            "selected_policy_prediction": pending.get("selected_policy"),
            "possible_outcomes": ["supported", "contradicted", "unknown"],
            "outcome_accessed": False,
            "candidate_score_is_calibrated_human_probability": False,
        },
        "boundaries": {
            "past_lt_present_lt_future": True,
            "future_content_in_present": False,
            "private_state_truth_claimed": False,
            "raw_dialogue_persisted": False,
            "factual_memory_write_allowed": False,
        },
    }
    forbidden = _forbidden_paths(material)
    if forbidden:
        raise P4ALTemporalError("forbidden_content:" + ",".join(forbidden))
    return {
        **material,
        "commitment_hash": _digest(material),
        "claim_boundary": (
            "next-turn operational response-action commitment; not a private-state "
            "probability or evidence of real-person predictive validity"
        ),
    }


def validate_commitment_hash_p4(commitment):
    payload = deepcopy(commitment or {})
    observed = str(payload.pop("commitment_hash", ""))
    payload.pop("claim_boundary", None)
    return bool(observed and observed == _digest(payload))


def resolve_temporal_commitment_p4(commitment, outcome_resolution):
    """Unlock a later linked result without mutating the prior commitment."""

    frozen_commitment = deepcopy(commitment or {})
    if not validate_commitment_hash_p4(frozen_commitment):
        raise P4ALTemporalError("commitment_hash_invalid")
    resolved = deepcopy(outcome_resolution or {})
    if resolved.get("schema") != outcome_binding.SCHEMA:
        raise P4ALTemporalError("outcome_resolution_schema_invalid")
    present = frozen_commitment["present"]
    if (
        resolved.get("identity_bound") is not True
        or resolved.get("prediction_id") != present.get("prediction_id")
        or resolved.get("ledger_id") != present.get("ledger_id")
    ):
        raise P4ALTemporalError("outcome_identity_mismatch")
    if int(resolved.get("turn_index") or -1) <= int(present["turn_index"]):
        raise P4ALTemporalError("outcome_not_after_present")
    outcome = str(resolved.get("outcome") or "")
    if outcome not in {"supported", "contradicted", "unknown"}:
        raise P4ALTemporalError("outcome_invalid")
    next_status = "supported" if outcome == "supported" else "revoked" if outcome == "contradicted" else "unknown"
    evidence_digest = str(((resolved.get("observed_evidence") or {}).get("evidence_digest") or ""))
    next_past = {
        "evidence_id": f"temporal-outcome-{frozen_commitment['commitment_hash'][:20]}",
        "observed_turn": int(resolved["turn_index"]),
        "source_kind": "linked_interaction_feedback",
        "epistemic_status": next_status,
        "provenance_digest": evidence_digest or _digest(
            {
                "prediction_id": resolved.get("prediction_id"),
                "outcome": outcome,
                "turn_index": resolved.get("turn_index"),
            }
        )[:32],
        "policy_id": present.get("selected_policy"),
        "replacement_policy": resolved.get("replacement_policy"),
        "private_state_fact": False,
        "factual_long_term_memory_write_allowed": False,
        "raw_dialogue_persisted": False,
    }
    return {
        "schema": RESOLUTION_SCHEMA,
        "commitment_hash": frozen_commitment["commitment_hash"],
        "commitment_hash_valid": True,
        "commitment_mutated": False,
        "past_before_present_count": frozen_commitment["past"]["record_count"],
        "present_turn": present["turn_index"],
        "future_observed_turn": int(resolved["turn_index"]),
        "identity_bound": True,
        "outcome": outcome,
        "outcome_counts_as_success": outcome == "supported",
        "unknown_counted_as_success": False,
        "replacement_policy": resolved.get("replacement_policy"),
        "next_past_record": next_past,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "claim_boundary": (
            "observed linked feedback becomes non-factual evidence for a later turn; "
            "not private desire truth or general future-prediction accuracy"
        ),
    }


def append_temporal_commitment_node_p4(result, commitment, resolution=None):
    """Add a graph-ready three-slice payload before the visible utterance."""

    result = result or {}
    commitment = deepcopy(commitment or {})
    resolution = deepcopy(resolution or {})
    if not commitment:
        return result
    payload = {
        "schema": SCHEMA,
        "past": {
            "record_count": (commitment.get("past") or {}).get("record_count", 0),
            "statuses": [
                row.get("epistemic_status")
                for row in ((commitment.get("past") or {}).get("records") or [])
            ],
            "strictly_before_present": (commitment.get("past") or {}).get("strictly_before_present"),
        },
        "present": {
            "turn_index": (commitment.get("present") or {}).get("turn_index"),
            "candidate_count": (commitment.get("present") or {}).get("candidate_count"),
            "selected_policy": (commitment.get("present") or {}).get("selected_policy"),
            "private_truth_unknown": True,
        },
        "future": {
            "status": "observed" if resolution else "committed_outcome_locked",
            "target": (commitment.get("future") or {}).get("target"),
            "outcome": resolution.get("outcome") if resolution else None,
            "unknown_counted_as_success": resolution.get("unknown_counted_as_success") if resolution else False,
        },
        "commitment_hash": commitment.get("commitment_hash"),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(insert_at, {"stage": "predict", "label": LABEL, "payload": payload, "salience": 0.99})
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


def _synthetic_pending(case):
    policy_ids = list(ambiguity._POLICY_ATOMS)
    selected = case["selected_policy"]
    ledger_id = _digest(case["case_id"])[:16]
    candidates = []
    for index, policy_id in enumerate(policy_ids):
        candidates.append(
            {
                "policy_id": policy_id,
                "mode": adaptive.POLICY_TO_RESPONSE_MODE_M23[policy_id],
                "operational_action_score": round(0.9 - index * 0.1, 4),
                "score_semantics": ambiguity.ACTION_SCORE_SEMANTICS,
            }
        )
    eligibility = {
        "schema": "uruha_desired_response_eligibility_guard_p4",
        "status": "ambiguity_preserved",
        "input_digest": _digest({"case": case["case_id"], "phase": "present"}),
        "selected_action": {
            "policy_id": selected,
            "mode": adaptive.POLICY_TO_RESPONSE_MODE_M23[selected],
        },
        "candidate_expectations": candidates,
        "candidate_count": 6,
        "eligibility": {"authorized": True, "authority": "synthetic_contract_fixture"},
    }
    decision = {
        "prediction_id": f"p4-al-pred-{ledger_id}",
        "selected": {"policy_id": selected, "expected_utility": 0.9},
        "state": {"input_digest": eligibility["input_digest"]},
    }
    return outcome_binding.create_pending_outcome_binding_p4(
        eligibility,
        decision,
        case["current_turn"],
    )


def build_dataset_evidence_p4_al(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    for frozen in dataset["cases"]:
        pending = _synthetic_pending(frozen)
        commitment = build_temporal_commitment_p4(
            frozen["past_records"],
            pending,
            frozen["current_turn"],
        )
        outcome = frozen["expected_outcome"]
        linked = outcome in {"supported", "contradicted"}
        feedback = {
            "previous_prediction_id": pending["prediction_id"],
            "feedback_linked_to_previous_prediction": linked,
            "status": outcome if linked else "uncertain",
            "explicit_target_policy": frozen["expected_replacement_policy"],
            "feedback_linkage_reason": "synthetic_contract_fixture" if linked else "unlinked_fixture",
            "evidence": {"digest": _digest({"case": frozen["case_id"], "phase": "outcome"})[:32]},
        }
        binding_resolution = outcome_binding.resolve_outcome_binding_p4(
            pending,
            feedback,
            frozen["current_turn"] + 1,
        )
        temporal_resolution = resolve_temporal_commitment_p4(commitment, binding_resolution)
        tampered = deepcopy(commitment)
        tampered["present"]["selected_policy"] = "care_physiology"
        tamper_rejected = False
        try:
            resolve_temporal_commitment_p4(tampered, binding_resolution)
        except P4ALTemporalError:
            tamper_rejected = True
        serialized_commitment = _canonical(commitment)
        forbidden = _forbidden_paths(commitment)
        cases.append(
            {
                "case_id": frozen["case_id"],
                "past_strictly_before_present": all(
                    row["observed_turn"] < frozen["current_turn"]
                    for row in commitment["past"]["records"]
                ),
                "outcome_absent_before_unlock": (
                    '"actual_outcome"' not in serialized_commitment
                    and '"observed_outcome"' not in serialized_commitment
                    and commitment["future"]["outcome_accessed"] is False
                ),
                "candidate_count": commitment["present"]["candidate_count"],
                "commitment_hash_valid": validate_commitment_hash_p4(commitment),
                "exact_identity_bound": temporal_resolution["identity_bound"],
                "outcome": temporal_resolution["outcome"],
                "replacement_policy": temporal_resolution["replacement_policy"],
                "unknown_counted_as_success": temporal_resolution["unknown_counted_as_success"],
                "next_past_record_created": bool(temporal_resolution["next_past_record"]),
                "tampered_commitment_rejected": tamper_rejected,
                "raw_or_private_content_persisted": bool(forbidden),
                "visible_reply_changed": temporal_resolution["visible_reply_changed"],
                "model_call_added": temporal_resolution["model_call_added"],
                "factual_memory_write_count": temporal_resolution["factual_memory_write_count"],
            }
        )
    return {
        "schema": "uruha_p4_al_past_present_future_commitment_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "case_count": len(cases),
            "past_before_present_count": sum(row["past_strictly_before_present"] for row in cases),
            "outcome_absent_before_unlock_count": sum(row["outcome_absent_before_unlock"] for row in cases),
            "six_candidate_present_count": sum(row["candidate_count"] == 6 for row in cases),
            "stable_commitment_hash_count": sum(row["commitment_hash_valid"] for row in cases),
            "exact_identity_binding_count": sum(row["exact_identity_bound"] for row in cases),
            "supported_transition_count": sum(row["outcome"] == "supported" for row in cases),
            "contradicted_transition_count": sum(row["outcome"] == "contradicted" for row in cases),
            "unknown_transition_count": sum(row["outcome"] == "unknown" for row in cases),
            "unknown_counted_as_success_count": sum(row["unknown_counted_as_success"] for row in cases),
            "next_past_record_count": sum(row["next_past_record_created"] for row in cases),
            "tampered_commitment_rejected_count": sum(row["tampered_commitment_rejected"] for row in cases),
            "raw_or_private_content_persisted_count": sum(row["raw_or_private_content_persisted"] for row in cases),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
            "model_call_added_count": sum(row["model_call_added"] for row in cases),
            "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in cases),
        },
        "claim_boundary": dataset["claim_boundary"],
    }
