"""P4-AR: prevent shadow-only actions from entering outcome verification.

P4-AQ can make a late fixed trigger visible to the candidate ledger after the
released response has already been selected and emitted.  Candidate creation
is useful, but an action that was never executed must not receive a product
prediction identity or a future outcome commitment.  This adapter requires an
exact released decision, applied plan, and product pending event before the
P4-AG binding may remain eligible for next-turn verification.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_executed_action_receipt_m44 as receipt_m44
import uruha_prediction_identity_p1 as identity
import uruha_runtime_temporal_graph_delivery_p4 as temporal_delivery


LABEL = "executed_action_identity_gate_p4"
SCHEMA = "uruha_executed_action_identity_gate_p4"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _views(result):
    result = result or {}
    runtime = result.get("runtime_trace") or {}
    logic = result.get("logic") or {}
    ag_trace = deepcopy(
        runtime.get(outcome_binding.LABEL)
        or logic.get(outcome_binding.LABEL)
        or {}
    )
    binding = deepcopy(ag_trace.get("current_binding") or {})
    decision = deepcopy(
        runtime.get("desired_response_decision_m18")
        or logic.get("desired_response_decision_m18")
        or {}
    )
    plan = deepcopy(
        runtime.get("adaptive_person_model_m18")
        or logic.get("adaptive_person_model_m18")
        or {}
    )
    receipt = deepcopy(
        runtime.get(receipt_m44.LABEL)
        or logic.get(receipt_m44.LABEL)
        or {}
    )
    product_model = deepcopy(
        ((result.get("runtime_state") or {}).get("adaptive_person_model"))
        or {}
    )
    return runtime, logic, ag_trace, binding, decision, plan, receipt, product_model


def assess_executed_action_identity_p4(result):
    """Return a raw-free authority decision without mutating the input."""

    (
        _runtime,
        _logic,
        _ag_trace,
        binding,
        decision,
        plan,
        receipt,
        product_model,
    ) = _views(result)
    prediction_id = str(binding.get("prediction_id") or "")
    selected_policy = str(binding.get("selected_policy") or "")
    pending_prediction_id = str(
        ((product_model.get("pending_prediction") or {}).get("prediction_id")) or ""
    )
    p1_sequence = identity._sequence_from_id(prediction_id)
    checks = {
        "binding_pending": binding.get("status") == "pending",
        "genuine_p1_identity": bool(p1_sequence),
        "existing_decision_identity_source": (
            binding.get("prediction_id_source")
            == "existing_desired_response_decision"
        ),
        "decision_applied": decision.get("status") == "applied",
        "decision_identity_exact": decision.get("prediction_id") == prediction_id,
        "decision_policy_exact": (
            ((decision.get("selected") or {}).get("policy_id")) == selected_policy
        ),
        "plan_applied": plan.get("applied") is True,
        "plan_identity_exact": plan.get("prediction_id") == prediction_id,
        "plan_policy_exact": plan.get("policy_id") == selected_policy,
        "product_pending_identity_exact": pending_prediction_id == prediction_id,
        "registered_receipt_exact_if_present": (
            receipt.get("status") != "registered_for_next_user_turn"
            or (
                receipt.get("prediction_id") == prediction_id
                and receipt.get("policy_id") == selected_policy
            )
        ),
    }
    binding_pending = checks["binding_pending"]
    required = tuple(key for key in checks if key != "binding_pending")
    authorized = bool(binding_pending and all(checks[key] for key in required))
    if not binding_pending:
        status = "not_applicable"
        reason = "no_pending_outcome_binding"
    elif authorized:
        status = "authorized_executed_product_event"
        reason = "released_decision_plan_and_product_pending_identity_are_exact"
    else:
        status = "blocked_unexecuted_shadow_action"
        reason = "pending_shadow_action_lacks_exact_executed_product_event"
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "prediction_id_digest": (
            hashlib.sha256(prediction_id.encode("utf-8")).hexdigest()[:16]
            if prediction_id
            else None
        ),
        "prediction_sequence": p1_sequence or None,
        "selected_policy": selected_policy or None,
        "checks": checks,
        "failed_checks": [key for key in required if not checks[key]],
        "outcome_verification_authorized": authorized,
        "fallback_identity_promoted_to_p1": False,
        "p1_guard_weakened": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "observable execution and exact event identity authority only; not "
            "action quality, user preference, or private mental truth"
        ),
    }


def append_executed_action_identity_gate_node_p4(result, payload):
    result = result or {}
    payload = deepcopy(payload or {})
    if payload.get("schema") != SCHEMA:
        return result
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(blackboard)
            if row.get("label") in {temporal_delivery.LABEL, "utterance"}
        ),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "verify", "label": LABEL, "payload": payload, "salience": 0.995},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


def _blocked_binding(binding):
    return {
        "schema": outcome_binding.SCHEMA,
        "status": "not_available",
        "reason": "unexecuted_action_not_eligible_for_outcome_verification",
        "turn_index": int(binding.get("turn_index") or 0),
        "candidate_count": 0,
        "suppressed_shadow_candidate_count": int(binding.get("candidate_count") or 0),
        "raw_dialogue_persisted": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
    }


def enforce_executed_action_identity_gate_p4(result, temporal_state_before=None):
    """Fail closed and remove a non-executed current action commitment."""

    source = deepcopy(result or {})
    reply_before = source.get("reply")
    (
        _runtime,
        _logic,
        ag_trace,
        binding,
        _decision,
        _plan,
        _receipt,
        _product_model,
    ) = _views(source)
    audit = assess_executed_action_identity_p4(source)
    if audit["status"] != "blocked_unexecuted_shadow_action":
        return {
            "blocked": False,
            "result": append_executed_action_identity_gate_node_p4(source, audit),
            "audit": audit,
            "pending_binding": deepcopy(binding),
            "shadow_feedback_model": None,
            "temporal_state": deepcopy(temporal_state_before),
        }

    blocked = _blocked_binding(binding)
    corrected_ag = deepcopy(ag_trace)
    corrected_ag["current_binding"] = blocked
    corrected_ag["execution_authority_gate"] = deepcopy(audit)
    present_turn = int((source.get("runtime_state") or {}).get("cycle_index") or 0)
    next_temporal_state, temporal_payload = temporal_delivery.advance_temporal_graph_delivery_p4(
        deepcopy(temporal_state_before),
        corrected_ag,
        present_turn,
    )
    output = outcome_binding.append_outcome_binding_node_p4(source, corrected_ag)
    output = append_executed_action_identity_gate_node_p4(output, audit)
    output = temporal_delivery.append_temporal_graph_delivery_node_p4(
        output,
        temporal_payload,
    )
    if output.get("reply") != reply_before:
        raise ValueError("p4_ar_visible_reply_changed")
    return {
        "blocked": True,
        "result": output,
        "audit": audit,
        "ag_trace": corrected_ag,
        "pending_binding": blocked,
        "shadow_feedback_model": adaptive.empty_model(),
        "temporal_state": next_temporal_state,
        "temporal_payload": temporal_payload,
    }


def deliver_existing_action_identity_gate_after_turn_p4(result):
    result = result or {}
    logic = result.get("logic") or {}
    payload = deepcopy(logic.get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return result
    if payload.get("status") == "blocked_unexecuted_shadow_action":
        ag_trace = deepcopy(logic.get(outcome_binding.LABEL) or {})
        temporal_payload = deepcopy(logic.get(temporal_delivery.LABEL) or {})
        result = outcome_binding.append_outcome_binding_node_p4(result, ag_trace)
        result = append_executed_action_identity_gate_node_p4(result, payload)
        result = temporal_delivery.append_temporal_graph_delivery_node_p4(
            result,
            temporal_payload,
        )
        return result
    return append_executed_action_identity_gate_node_p4(result, payload)


_INSTALLED_P4_AR = False
_ORIGINAL_EMIT_RESPONSE_P4_AR = None
_ORIGINAL_RUN_TURN_P4_AR = None


def install_executed_action_identity_gate_p4():
    global _INSTALLED_P4_AR, _ORIGINAL_EMIT_RESPONSE_P4_AR, _ORIGINAL_RUN_TURN_P4_AR
    if _INSTALLED_P4_AR:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AR = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_TURN_P4_AR = UruhaBrainV4_Mac.run_turn_debug

    def emit_with_p4_ar(self, event, tick_result):
        temporal_before = deepcopy(
            getattr(self, "_p4_am_temporal_delivery_state", None)
        )
        result = _ORIGINAL_EMIT_RESPONSE_P4_AR(self, event, tick_result)
        guarded = enforce_executed_action_identity_gate_p4(
            result,
            temporal_before,
        )
        result = guarded["result"]
        if guarded["blocked"]:
            self._p4_ag_pending_binding = deepcopy(guarded["pending_binding"])
            self._p4_ag_shadow_feedback_model = deepcopy(
                guarded["shadow_feedback_model"]
            )
            self._p4_am_temporal_delivery_state = deepcopy(
                guarded["temporal_state"]
            )
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_ar

    def run_turn_with_p4_ar(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AR(
            self,
            user_input,
            input_context=input_context,
        )
        result = deliver_existing_action_identity_gate_after_turn_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.run_turn_debug = run_turn_with_p4_ar
    _INSTALLED_P4_AR = True
    return True


def _case_result(case):
    prediction_id = case.get("prediction_id")
    selected_policy = case.get("selected_policy")
    pending_id = case.get("product_pending_prediction_id")
    return {
        "reply": "そのまま",
        "logic": {
            outcome_binding.LABEL: {
                "schema": outcome_binding.SCHEMA,
                "previous_resolution": {"status": "not_available"},
                "current_binding": {
                    "schema": outcome_binding.SCHEMA,
                    "status": case.get("binding_status"),
                    "prediction_id": prediction_id,
                    "prediction_id_source": case.get("prediction_id_source"),
                    "selected_policy": selected_policy,
                    "turn_index": 1,
                    "candidate_count": 6 if case.get("binding_status") == "pending" else 0,
                },
            },
            "desired_response_decision_m18": {
                "status": case.get("decision_status"),
                "prediction_id": case.get("decision_prediction_id"),
                "selected": (
                    {"policy_id": case.get("decision_selected_policy")}
                    if case.get("decision_selected_policy")
                    else None
                ),
            },
            "adaptive_person_model_m18": {
                "applied": case.get("plan_applied"),
                "prediction_id": case.get("plan_prediction_id"),
                "policy_id": case.get("plan_policy_id"),
            },
            receipt_m44.LABEL: {
                "schema": receipt_m44.SCHEMA,
                "status": case.get("receipt_status"),
                "prediction_id": case.get("receipt_prediction_id"),
                "policy_id": case.get("receipt_policy_id"),
            },
        },
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
        "runtime_state": {
            "cycle_index": 1,
            "adaptive_person_model": {
                "pending_prediction": (
                    {"prediction_id": pending_id}
                    if pending_id
                    else None
                )
            },
        },
    }


def build_offline_evidence_p4_ar(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = []
    partitions = (
        "development_cases",
        "fresh_authorized_cases",
        "fresh_blocked_cases",
        "control_cases",
    )
    for partition in partitions:
        for case in dataset.get(partition) or []:
            source = _case_result(case)
            before = deepcopy(source)
            audit = assess_executed_action_identity_p4(source)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "partition": partition,
                    "status": audit["status"],
                    "expected_status": case["expected_status"],
                    "outcome_verification_authorized": audit[
                        "outcome_verification_authorized"
                    ],
                    "genuine_p1_identity": audit["checks"]["genuine_p1_identity"],
                    "decision_applied": audit["checks"]["decision_applied"],
                    "plan_applied": audit["checks"]["plan_applied"],
                    "product_pending_identity_exact": audit["checks"][
                        "product_pending_identity_exact"
                    ],
                    "source_payload_mutated": source != before,
                    "visible_reply_changed": audit["visible_reply_changed"],
                    "model_call_added": audit["model_call_added"],
                    "factual_memory_write_count": audit[
                        "factual_memory_write_count"
                    ],
                    "raw_dialogue_persisted": audit["raw_dialogue_persisted"],
                }
            )
    blocked = [row for row in rows if row["status"] == "blocked_unexecuted_shadow_action"]
    expected_blocked = [row for row in rows if row["expected_status"] == "blocked_unexecuted_shadow_action"]
    metrics = {
        "case_count": len(rows),
        "development_blocked_count": sum(
            row["partition"] == "development_cases"
            and row["status"] == "blocked_unexecuted_shadow_action"
            for row in rows
        ),
        "fresh_authorized_count": sum(
            row["partition"] == "fresh_authorized_cases"
            and row["status"] == "authorized_executed_product_event"
            for row in rows
        ),
        "fresh_blocked_count": sum(
            row["partition"] == "fresh_blocked_cases"
            and row["status"] == "blocked_unexecuted_shadow_action"
            for row in rows
        ),
        "control_noop_count": sum(
            row["partition"] == "control_cases"
            and row["status"] == "not_applicable"
            for row in rows
        ),
        "expected_status_exact_count": sum(
            row["status"] == row["expected_status"] for row in rows
        ),
        "fallback_without_execution_blocked_count": sum(
            row["status"] == "blocked_unexecuted_shadow_action"
            and not row["genuine_p1_identity"]
            for row in rows
        ),
        "inactive_or_unapplied_blocked_count": sum(
            row["status"] == "blocked_unexecuted_shadow_action"
            and (not row["decision_applied"] or not row["plan_applied"])
            for row in rows
        ),
        "identity_or_policy_mismatch_blocked_count": sum(
            row["case_id"] in {
                "pending-product-identity-mismatch",
                "executed-policy-mismatch",
            }
            and row["status"] == "blocked_unexecuted_shadow_action"
            for row in rows
        ),
        "authorized_non_p1_identity_count": sum(
            row["outcome_verification_authorized"]
            and not row["genuine_p1_identity"]
            for row in rows
        ),
        "false_authorization_count": sum(
            row["outcome_verification_authorized"] for row in expected_blocked
        ),
        "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in rows),
        "model_call_added_count": sum(row["model_call_added"] for row in rows),
        "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in rows),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in rows),
        "source_payload_mutated_count": sum(row["source_payload_mutated"] for row in rows),
    }
    return {
        "schema": "uruha_p4_ar_executed_action_identity_gate_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }
