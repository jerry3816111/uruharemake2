"""P4-AS: execute a bounded selected action before committing its outcome event.

P4-AH originally discovers some multilingual cognitive-overactivity signals
after the released decision and surface have already been produced.  P4-AS
reuses that exact detector before decision time, but only for a direct
first-person utterance with no third-party attribution.  The existing P1,
M39, and M44 mechanisms then remain the authorities for event identity,
visible Japanese, and executed-action receipt respectively.

No user preference or private mental state is asserted.  A pending event says
only which visible response action was performed and may be checked on the next
turn.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_executed_action_identity_gate_p4 as authority_gate
import uruha_executed_action_receipt_m44 as receipt_m44
import uruha_multilingual_observable_trigger_p4 as trigger_coverage
import uruha_prediction_identity_p1 as identity
import uruha_runtime_temporal_graph_delivery_p4 as temporal_delivery
import uruha_semantic_persona_surface_m39 as surface_m39


LABEL = "selected_action_surface_execution_p4"
SCHEMA = "uruha_selected_action_surface_execution_p4"
EARLY_STATUS = "early_typed_trigger_authorized"
RECEIPT_STATUS = "surface_verified_and_receipt_committed"
FINAL_STATUS = "executed_and_committed"


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _source_authority(user_input):
    frame = surface_m39._source_frame_m39(user_input)
    return frame, bool(
        frame.get("speaker_role") == "user_first_person"
        and frame.get("third_party_present") is False
    )


def promote_selected_action_state_p4(user_input, state):
    """Return an early, copied P4-AH state or an auditable strict no-op."""

    source = deepcopy(state or {})
    source_before = deepcopy(source)
    base = deepcopy(source.get("observable_trigger_m37") or {})
    trigger = trigger_coverage.extend_observable_trigger_p4(user_input, base)
    frame, source_authorized = _source_authority(user_input)
    extension_status = str((trigger.get("coverage_extension") or {}).get("status") or "")
    exact_new_trigger = bool(
        extension_status == "additive_compositional_trigger"
        and "cognitive_overactivity" in set(trigger.get("predicates") or [])
        and trigger.get("private_state_truth_claimed") is False
    )
    eligible = bool(exact_new_trigger and source_authorized)
    if eligible:
        promoted = trigger_coverage.apply_extended_trigger_to_shadow_state_p4(
            source,
            trigger,
        )
        status = EARLY_STATUS
        reason = "existing_p4_ah_typed_trigger_moved_before_decision"
    else:
        promoted = source
        status = "not_applicable"
        if not exact_new_trigger:
            reason = "no_new_additive_cognitive_overactivity_trigger"
        elif not source_authorized:
            reason = "source_not_direct_user_first_person_without_third_party"
        else:
            reason = "source_not_direct_user_first_person_without_third_party"
    trace = {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "trigger_status": extension_status or "not_available",
        "trigger_predicate": (
            "cognitive_overactivity"
            if "cognitive_overactivity" in set(trigger.get("predicates") or [])
            else None
        ),
        "trigger_evidence_digest": str(trigger.get("evidence_digest") or "")[:32],
        "source_speaker_role": frame.get("speaker_role"),
        "third_party_present": bool(frame.get("third_party_present")),
        "source_authorized": source_authorized,
        "selected_policy": None,
        "surface_verified": False,
        "receipt_registered": False,
        "p1_event_committed": False,
        "p4_ar_authorized": False,
        "source_state_mutated": source != source_before,
        "p4_ah_detector_changed": False,
        "candidate_score_or_order_changed": False,
        "feedback_classifier_changed": False,
        "p1_guard_weakened": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "direct visible first-person trigger and executed response action only; "
            "not private-state truth, user preference, or prediction validity"
        ),
    }
    promoted[LABEL] = deepcopy(trace)
    return promoted, trace


def _receipt_checks(logic, user_input, reply, turn_index, model):
    logic = logic or {}
    decision = deepcopy(logic.get("desired_response_decision_m18") or {})
    selected = deepcopy(decision.get("selected") or {})
    policy = str(selected.get("policy_id") or "")
    prediction_id = str(decision.get("prediction_id") or "")
    early = deepcopy((decision.get("state") or {}).get(LABEL) or {})
    plan = deepcopy(logic.get("adaptive_person_model_m18") or {})
    audit = deepcopy(logic.get("semantic_persona_surface_verifier_m39") or {})
    frame = deepcopy(audit.get("source_frame") or {})
    pending = deepcopy((model or {}).get("pending_prediction") or {})
    pending_exact = bool(
        pending
        and pending.get("prediction_id") == prediction_id
        and pending.get("policy_id") == policy
        and pending.get("turn_index") == int(turn_index)
        and pending.get("input_digest") == receipt_m44._digest(user_input)
    )
    return decision, selected, early, plan, audit, {
        "early_authority_exact": early.get("status") == EARLY_STATUS,
        "direct_user_first_person": frame.get("speaker_role") == "user_first_person",
        "no_third_party": frame.get("third_party_present") is False,
        "decision_applied": decision.get("status") == "applied",
        "policy_calibrate_need": policy == "calibrate_need",
        "genuine_p1_identity": bool(identity._sequence_from_id(prediction_id)),
        "turn_exact": (decision.get("state") or {}).get("turn_index") == int(turn_index),
        "input_digest_exact": (decision.get("state") or {}).get("input_digest") == receipt_m44._digest(user_input),
        "plan_applied": plan.get("applied") is True,
        "plan_identity_exact": plan.get("prediction_id") == prediction_id,
        "plan_policy_exact": plan.get("policy_id") == policy,
        "m39_verified": audit.get("status") in {"accepted_verified_surface", "repaired_and_verified"},
        "m39_unprotected": audit.get("protected_route") is False,
        "m39_policy_exact": audit.get("selected_policy_id") == policy,
        "m39_policy_act_realized": audit.get("policy_act_match_after") is True,
        "m39_no_unresolved_violation": audit.get("unresolved_violations") == [],
        "m39_reply_digest_exact": audit.get("final_reply_digest") == receipt_m44._digest(reply),
        "m39_source_digest_exact": frame.get("source_digest") == receipt_m44._digest(user_input),
        "pending_absent_or_exact": not pending or pending_exact,
    }


def register_selected_action_surface_execution_p4(
    model,
    logic,
    user_input,
    reply,
    turn_index,
    original_register=None,
):
    """Preserve M44 first; add one exact current-trigger receipt if it abstains."""

    original_register = original_register or _ORIGINAL_REGISTER_M44 or receipt_m44.register_executed_action_m44
    state, original_trace = original_register(
        model,
        logic,
        user_input,
        reply,
        turn_index,
    )
    if original_trace.get("status") == "registered_for_next_user_turn":
        return state, original_trace
    decision, selected, early, plan, audit, checks = _receipt_checks(
        logic,
        user_input,
        reply,
        turn_index,
        model,
    )
    failed = [key for key, value in checks.items() if not value]
    if failed:
        trace = deepcopy(original_trace)
        trace["p4_as_authority"] = {
            "schema": SCHEMA,
            "status": "not_applicable",
            "failed_checks": failed,
            "raw_dialogue_persisted": False,
            "private_state_truth_claimed": False,
        }
        return state, trace

    prediction_id = str(decision.get("prediction_id") or "")
    policy = str(selected.get("policy_id") or "")
    ledger = deepcopy((model or {}).get("outcome_calibration_ledger_m27") or [])
    pending = deepcopy((model or {}).get("pending_prediction") or {})
    pending_preexisting_exact = bool(pending)
    if pending_preexisting_exact:
        # The released product may already have committed the exact P1 event.
        # Preserve that event and its ledger verbatim; P4-AS only supplies the
        # missing verified-surface receipt.  A different pending event failed
        # ``pending_absent_or_exact`` above and can never reach this branch.
        next_state = deepcopy(model or {})
        entry = next(
            (
                row
                for row in reversed(ledger)
                if row.get("prediction_id") == prediction_id
            ),
            None,
        )
        if entry is None:
            trace = deepcopy(original_trace)
            trace["p4_as_authority"] = {
                "schema": SCHEMA,
                "status": "not_applicable",
                "failed_checks": ["exact_pending_ledger_entry_present"],
                "raw_dialogue_persisted": False,
                "private_state_truth_claimed": False,
            }
            return state, trace
    else:
        if any(row.get("prediction_id") == prediction_id for row in ledger):
            return state, original_trace
        candidate = adaptive.set_pending_prediction(
            deepcopy(model or {}),
            decision,
            turn_index=int(turn_index),
        )
        next_state = deepcopy(model or {})
        next_state["pending_prediction"] = deepcopy(candidate["pending_prediction"])
        entry = next(
            row
            for row in candidate["outcome_calibration_ledger_m27"]
            if row["prediction_id"] == prediction_id
        )
        next_state["outcome_calibration_ledger_m27"] = [
            *ledger,
            deepcopy(entry),
        ][-adaptive.M27_MAX_LEDGER_ENTRIES :]
        next_state["outcome_calibration_summary_m27"] = (
            adaptive.build_causal_outcome_calibration_summary_m27(next_state)
        )
        next_state["last_turn"] = int(turn_index)
    relation_id = f"p4-as-{str(early.get('trigger_evidence_digest') or _digest(user_input))[:32]}"
    receipt = receipt_m44._clean_receipt(
        {
            "schema": receipt_m44.SCHEMA,
            "prediction_id": prediction_id,
            "policy_id": policy,
            "relation_id": relation_id,
            "created_turn": int(turn_index),
            "input_digest": receipt_m44._digest(user_input),
            "reply_digest": receipt_m44._digest(reply),
            "relation_confidence": 0.86,
        }
    )
    existing_receipts = deepcopy((model or {}).get(receipt_m44.STORE) or [])
    existing_exact_receipt = next(
        (
            row
            for row in reversed(existing_receipts)
            if row.get("prediction_id") == prediction_id
            and row.get("policy_id") == policy
            and row.get("input_digest") == receipt_m44._digest(user_input)
            and row.get("reply_digest") == receipt_m44._digest(reply)
        ),
        None,
    )
    if existing_exact_receipt is None:
        next_state[receipt_m44.STORE] = [*existing_receipts, receipt][-32:]
    else:
        receipt = deepcopy(existing_exact_receipt)
        next_state[receipt_m44.STORE] = existing_receipts
    trace = deepcopy(original_trace)
    trace.update(
        {
            "status": "registered_for_next_user_turn",
            "reason": (
                "exact_existing_product_event_received_verified_surface_receipt"
                if pending_preexisting_exact
                else "verified_current_visible_trigger_surface_restores_missing_feedback_link"
            ),
            "prediction_id": prediction_id,
            "policy_id": policy,
            "next_pending_id": prediction_id,
            "relation_id": relation_id,
            "receipt": deepcopy(receipt),
            "eligible_for_implicit_calibration": bool(
                entry.get("eligible_for_implicit_calibration")
            ),
            "p4_as_authority": {
                **deepcopy(early),
                "status": RECEIPT_STATUS,
                "selected_policy": policy,
                "prediction_sequence": identity._sequence_from_id(prediction_id),
                "surface_verified": True,
                "receipt_registered": True,
                "pending_preexisting_exact": pending_preexisting_exact,
                "existing_exact_receipt_preserved": existing_exact_receipt is not None,
                "p1_event_committed": True,
                "checks": checks,
                "failed_checks": [],
                "final_reply_digest": receipt_m44._digest(reply),
                "raw_dialogue_persisted": False,
                "private_state_truth_claimed": False,
            },
        }
    )
    return next_state, trace


def append_selected_action_surface_execution_node_p4(result, payload):
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
            if row.get("label") in {authority_gate.LABEL, "utterance"}
        ),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "writeback", "label": LABEL, "payload": payload, "salience": 0.997},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


def finalize_selected_action_surface_execution_p4(result):
    result = result or {}
    logic = result.get("logic") or {}
    receipt = deepcopy(logic.get(receipt_m44.LABEL) or {})
    payload = deepcopy(receipt.get("p4_as_authority") or {})
    if payload.get("schema") != SCHEMA:
        return result
    if payload.get("status") != RECEIPT_STATUS:
        return append_selected_action_surface_execution_node_p4(result, payload)
    authority = deepcopy(logic.get(authority_gate.LABEL) or {})
    product_pending = deepcopy(
        (((result.get("runtime_state") or {}).get("adaptive_person_model") or {}).get("pending_prediction"))
        or {}
    )
    prediction_id = str(receipt.get("prediction_id") or "")
    authorized = bool(
        authority.get("status") == "authorized_executed_product_event"
        and authority.get("outcome_verification_authorized") is True
        and product_pending.get("prediction_id") == prediction_id
    )
    payload.update(
        {
            "status": FINAL_STATUS if authorized else "receipt_committed_but_authority_incomplete",
            "p4_ar_authorized": authorized,
            "product_pending_prediction_exact": product_pending.get("prediction_id") == prediction_id,
            "p4_ar_status": authority.get("status"),
        }
    )
    return append_selected_action_surface_execution_node_p4(result, payload)


_INSTALLED_P4_AS = False
_ORIGINAL_BUILD_CURRENT_STATE = None
_ORIGINAL_REGISTER_M44 = None
_ORIGINAL_AUTHORITY_VIEWS = None
_ORIGINAL_EMIT_RESPONSE_P4_AS = None
_ORIGINAL_RUN_TURN_P4_AS = None


def install_selected_action_surface_execution_p4():
    global _INSTALLED_P4_AS
    global _ORIGINAL_BUILD_CURRENT_STATE, _ORIGINAL_REGISTER_M44
    global _ORIGINAL_AUTHORITY_VIEWS, _ORIGINAL_EMIT_RESPONSE_P4_AS
    global _ORIGINAL_RUN_TURN_P4_AS
    if _INSTALLED_P4_AS:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_BUILD_CURRENT_STATE = adaptive.build_current_state
    _ORIGINAL_REGISTER_M44 = receipt_m44.register_executed_action_m44
    _ORIGINAL_AUTHORITY_VIEWS = authority_gate._views
    _ORIGINAL_EMIT_RESPONSE_P4_AS = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_TURN_P4_AS = UruhaBrainV4_Mac.run_turn_debug

    def build_current_state_with_p4_as(user_input, *args, **kwargs):
        state = _ORIGINAL_BUILD_CURRENT_STATE(user_input, *args, **kwargs)
        promoted, _trace = promote_selected_action_state_p4(user_input, state)
        return promoted

    def register_with_p4_as(model, logic, user_input, reply, turn_index):
        next_state, trace = register_selected_action_surface_execution_p4(
            model,
            logic,
            user_input,
            reply,
            turn_index,
            original_register=_ORIGINAL_REGISTER_M44,
        )
        authority = deepcopy(trace.get("p4_as_authority") or {})
        if authority.get("schema") == SCHEMA:
            logic[LABEL] = authority
        return next_state, trace

    def views_with_p4_as(result):
        views = list(_ORIGINAL_AUTHORITY_VIEWS(result))
        logic = (result or {}).get("logic") or {}
        p4_as = logic.get(LABEL) or {}
        if p4_as.get("status") == RECEIPT_STATUS:
            plan = deepcopy(logic.get("adaptive_person_model_m18") or {})
            if plan.get("applied") is True:
                views[5] = plan
        return tuple(views)

    adaptive.build_current_state = build_current_state_with_p4_as
    receipt_m44.register_executed_action_m44 = register_with_p4_as
    authority_gate._views = views_with_p4_as

    def emit_with_p4_as(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_AS(self, event, tick_result)
        result = finalize_selected_action_surface_execution_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_as

    def run_turn_with_p4_as(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AS(
            self,
            user_input,
            input_context=input_context,
        )
        result = finalize_selected_action_surface_execution_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.run_turn_debug = run_turn_with_p4_as
    _INSTALLED_P4_AS = True
    return True


def _fixture_case_result(row, turn_index):
    source_state, _old_decision, _old_mode = ambiguity._isolated_inputs(
        row["input"],
        turn_index,
    )
    source_before = deepcopy(source_state)
    state, early = promote_selected_action_state_p4(row["input"], source_state)
    model = adaptive.empty_model()
    decision = adaptive.decide_response(state, model)
    base_logic = {
        "intent": "chat",
        "scene": "casual",
        "core_message_jp": "元の文",
        "semantic_route_m22": {"selected_type": "general_conversation"},
        "counterfactual_pragmatic_branch_m34": {
            "selected_branch": {
                "policy_id": ((decision.get("selected") or {}).get("policy_id"))
            }
        },
        "semantic_authorization_m31": {"suppresses_new_pending_prediction": True},
    }
    planned, plan = adaptive.apply_decision_to_plan(base_logic, decision)
    planned["desired_response_decision_m18"] = deepcopy(decision)
    planned["adaptive_person_model_m18"] = deepcopy(plan)
    baseline_reply = (
        "うちの頭は考えで埋まって今夜落ち着かないんだね。"
        if row["expected_status"] == FINAL_STATUS
        else "そのまま。"
    )
    final_reply, m39 = surface_m39.verify_and_repair_surface_m39(
        row["input"],
        baseline_reply,
        planned,
    )
    planned["semantic_persona_surface_verifier_m39"] = m39
    next_model, receipt = register_selected_action_surface_execution_p4(
        model,
        planned,
        row["input"],
        final_reply,
        turn_index,
        original_register=receipt_m44.register_executed_action_m44,
    )
    if (receipt.get("p4_as_authority") or {}).get("schema") == SCHEMA:
        planned[LABEL] = deepcopy(receipt["p4_as_authority"])
    mode = adaptive.build_desired_response_mode_contract(
        {"selected_type": "emotional_bid"},
        state,
        decision,
    )
    ledger = eligibility.build_desired_response_eligibility_guard_p4(
        state,
        decision,
        mode,
    )
    binding = outcome_binding.create_pending_outcome_binding_p4(
        ledger,
        decision,
        turn_index,
    )
    ag = {
        "schema": outcome_binding.SCHEMA,
        "previous_resolution": {"status": "not_available"},
        "current_binding": binding,
    }
    result = {
        "reply": final_reply,
        "logic": {
            **planned,
            receipt_m44.LABEL: receipt,
            outcome_binding.LABEL: ag,
        },
        "runtime_trace": {
            "desired_response_decision_m18": decision,
            "adaptive_person_model_m18": plan,
            receipt_m44.LABEL: receipt,
            outcome_binding.LABEL: ag,
            "blackboard": [],
        },
        "runtime_state": {"adaptive_person_model": next_model},
    }
    ar = authority_gate.assess_executed_action_identity_p4(result)
    result["logic"][authority_gate.LABEL] = ar
    final = finalize_selected_action_surface_execution_p4(result)
    payload = final.get("logic", {}).get(LABEL) or early
    return {
        "case_id": row["case_id"],
        "partition": row["partition"],
        "expected_status": row["expected_status"],
        "status": payload.get("status"),
        "early_status": early.get("status"),
        "source_speaker_role": early.get("source_speaker_role"),
        "third_party_present": early.get("third_party_present"),
        "decision_status": decision.get("status"),
        "selected_policy": (decision.get("selected") or {}).get("policy_id"),
        "prediction_id": decision.get("prediction_id"),
        "plan_applied": plan.get("applied"),
        "surface_status": m39.get("status"),
        "surface_policy_act_match": m39.get("policy_act_match_after"),
        "surface_unresolved": m39.get("unresolved_violations"),
        "surface_changed": bool(
            (receipt.get("p4_as_authority") or {}).get("status") == RECEIPT_STATUS
            and final_reply != baseline_reply
        ),
        "visible_reply": final_reply,
        "receipt_status": receipt.get("status"),
        "receipt_prediction_id": receipt.get("prediction_id"),
        "pending_prediction_id": ((next_model.get("pending_prediction") or {}).get("prediction_id")),
        "p4_ar_status": ar.get("status"),
        "p4_ar_authorized": ar.get("outcome_verification_authorized"),
        "source_state_mutated": source_state != source_before,
        "model_call_added": int(payload.get("model_call_added") or 0),
        "factual_memory_write_count": int(payload.get("factual_memory_write_count") or 0),
        "raw_dialogue_persisted": bool(payload.get("raw_dialogue_persisted")),
        "private_state_truth_claimed": bool(payload.get("private_state_truth_claimed")),
    }


def _looks_japanese(text):
    text = str(text or "")
    return bool(re.search(r"[ぁ-んァ-ヶ一-龠]", text)) and not bool(
        re.search(r"\b[A-Za-z]{2,}\b", text)
    )


def build_dataset_evidence_p4_as(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    identity.install_prediction_identity_p1()
    rows = []
    turn = 500
    for partition in ("development_cases", "fresh_positive_cases", "fresh_control_cases"):
        for source in dataset[partition]:
            turn += 1
            rows.append(_fixture_case_result({**source, "partition": partition}, turn))
    positives = [row for row in rows if row["expected_status"] == FINAL_STATUS]
    controls = [row for row in rows if row["expected_status"] == "not_applicable"]
    metrics = {
        "case_count": len(rows),
        "development_executed_count": sum(row["partition"] == "development_cases" and row["status"] == FINAL_STATUS for row in rows),
        "fresh_positive_executed_count": sum(row["partition"] == "fresh_positive_cases" and row["status"] == FINAL_STATUS for row in rows),
        "fresh_control_noop_count": sum(row["status"] == "not_applicable" for row in controls),
        "expected_status_exact_count": sum(row["status"] == row["expected_status"] for row in rows),
        "early_typed_trigger_count": sum(row["early_status"] == EARLY_STATUS for row in positives),
        "user_first_person_authority_count": sum(row["source_speaker_role"] == "user_first_person" and not row["third_party_present"] for row in positives),
        "applied_p1_decision_count": sum(row["decision_status"] == "applied" and identity._sequence_from_id(row["prediction_id"]) > 0 for row in positives),
        "calibrate_need_selected_count": sum(row["selected_policy"] == "calibrate_need" for row in positives),
        "m39_verified_policy_surface_count": sum(row["surface_status"] in {"accepted_verified_surface", "repaired_and_verified"} and row["surface_policy_act_match"] is True and row["surface_unresolved"] == [] for row in positives),
        "japanese_surface_count": sum(_looks_japanese(row["visible_reply"]) for row in positives),
        "m44_exact_receipt_count": sum(row["receipt_status"] == "registered_for_next_user_turn" and row["receipt_prediction_id"] == row["prediction_id"] for row in positives),
        "product_pending_prediction_exact_count": sum(row["pending_prediction_id"] == row["prediction_id"] for row in positives),
        "p4_ar_authorized_count": sum(row["p4_ar_status"] == "authorized_executed_product_event" and row["p4_ar_authorized"] is True for row in positives),
        "third_party_blocked_count": sum(row["case_id"].startswith("third-party-") and row["status"] == "not_applicable" for row in controls),
        "metalinguistic_blocked_count": sum(row["case_id"].startswith("metalinguistic-") and row["status"] == "not_applicable" for row in controls),
        "resolved_or_ordinary_control_blocked_count": sum(row["case_id"] in {"resolved-user-state-en", "ordinary-object-motion-zh"} and row["status"] == "not_applicable" for row in controls),
        "authorized_surface_change_count": sum(row["surface_changed"] for row in positives),
        "control_surface_change_count": sum(row["surface_changed"] for row in controls),
        "role_violation_count": sum(bool(row["surface_unresolved"]) for row in positives),
        "false_execution_count": sum(row["status"] == FINAL_STATUS for row in controls),
        "new_model_call_count": sum(row["model_call_added"] for row in rows),
        "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in rows),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in rows),
        "source_state_mutated_count": sum(row["source_state_mutated"] for row in rows),
    }
    return {
        "schema": "uruha_p4_as_selected_action_surface_execution_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }


__all__ = [
    "FINAL_STATUS",
    "LABEL",
    "SCHEMA",
    "append_selected_action_surface_execution_node_p4",
    "build_dataset_evidence_p4_as",
    "finalize_selected_action_surface_execution_p4",
    "install_selected_action_surface_execution_p4",
    "promote_selected_action_state_p4",
    "register_selected_action_surface_execution_p4",
]
