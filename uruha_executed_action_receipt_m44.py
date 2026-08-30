"""M44: prospective feedback for an action verified at final emission.

Human pragmatic understanding is a corrigible operational loop, not private
mental truth. This receipt says which previously selected action was actually
expressed. It does not invent an earlier plan or a user's later approval.
No examples, reserve files or new language patterns are loaded by runtime.
"""
from copy import deepcopy
import hashlib
import re
import time

import uruha_adaptive_person_model as adaptive
from uruha_runtime import RuntimeState as _RuntimeState  # initialize existing M38 adapter
from uruha_supported_feedback_closure_m43 import _protected

LABEL = "executed_action_receipt_m44"
OUTCOME_LABEL = "executed_action_outcome_m44"
STORE = "executed_action_receipts_m44"
SCHEMA = "uruha_executed_action_receipt_m44"
_BASE_NORMALISE = adaptive._normalise_model
_BASE_OBSERVE = adaptive.observe_next_turn
_INSTALLED = False
_LITERAL_LAYERS = ("literal_topic_projection_m29", "semantic_authorization_m31",
                   "semantic_commit_repair_m32", "source_anchored_semantic_commit_m33")


def _digest(text):
    return hashlib.sha256(str(text or "").encode()).hexdigest()[:16]


def _clean_receipt(row):
    if not isinstance(row, dict) or row.get("schema") != SCHEMA:
        return None
    required = ("prediction_id", "relation_id", "policy_id", "input_digest", "reply_digest")
    if not all(isinstance(row.get(k), str) and row[k] for k in required):
        return None
    if row["policy_id"] not in adaptive.POLICIES:
        return None
    if not all(re.fullmatch(r"[a-f0-9]{16}", row[k]) for k in ("input_digest", "reply_digest")):
        return None
    try:
        turn = int(row.get("created_turn", -1))
        confidence = float(row.get("relation_confidence", 0))
        resolved = int(row.get("resolved_turn", 0))
    except (TypeError, ValueError, OverflowError):
        return None
    if turn < 0 or not 0 <= confidence <= 1:
        return None
    outcome = row.get("outcome", "pending")
    if outcome not in {"pending", "supported", "contradicted", "uncertain", "expired"}:
        return None
    return {"schema": SCHEMA, "prediction_id": row["prediction_id"][:80],
            "relation_id": row["relation_id"][:80], "policy_id": row["policy_id"],
            "input_digest": row["input_digest"], "reply_digest": row["reply_digest"],
            "created_turn": turn, "valid_next_user_turn": turn + 1,
            "relation_confidence": confidence, "source_kind": "verified_final_emission",
            "outcome": outcome, "resolved_turn": max(0, resolved),
            "feedback_digest": str(row.get("feedback_digest") or "")[:16],
            "raw_dialogue_persisted": False, "mental_fact_write_count": 0}


def normalise_model_m44(model):
    result = _BASE_NORMALISE(model)
    if isinstance(model, dict) and STORE in model:
        result[STORE] = [clean for row in (model.get(STORE) or [])[-32:]
                         if (clean := _clean_receipt(row)) is not None]
    return result


def register_executed_action_m44(model, logic, user_input, reply, turn_index):
    """Add only a missing pending record; all pre-emission observations stay put."""
    started = time.perf_counter()
    state, plan = deepcopy(model or {}), logic or {}
    decision = plan.get("desired_response_decision_m18") or {}
    selected = decision.get("selected") or {}
    pid, policy = decision.get("prediction_id"), selected.get("policy_id")
    trace = {"schema": SCHEMA, "status": "not_registered", "reason": None,
             "created_turn": int(turn_index), "prediction_id": pid, "policy_id": policy,
             "previous_pending_id": (state.get("pending_prediction") or {}).get("prediction_id"),
             "next_pending_id": (state.get("pending_prediction") or {}).get("prediction_id"),
             "input_digest": _digest(user_input), "reply_digest": _digest(reply),
             "raw_dialogue_persisted": False, "mental_fact_write_count": 0,
             "added_model_calls": 0, "earlier_plan_or_outcome_rewritten": False,
             "claim_boundary": "observable policy execution; next outcome remains unknown"}

    def finish(reason):
        trace["reason"] = reason
        trace["added_seconds"] = round(time.perf_counter() - started, 8)
        return state, trace

    if state.get("pending_prediction"):
        return finish("existing_pending_preserved")
    if not reply or not str(reply).strip() or _protected(plan):
        return finish("no_visible_action_or_protected_route")
    if ((plan.get("supported_feedback_closure_m43") or {}).get("authoritative")
            or (plan.get("feedback_topic_transition_m28") or {}).get("surface_authority")):
        return finish("current_feedback_act_not_previous_policy_execution")
    suppressors = [key for key in _LITERAL_LAYERS
                   if (plan.get(key) or {}).get("suppresses_new_pending_prediction")]
    trace["literal_suppressors"] = suppressors
    if not suppressors:
        return finish("not_a_literal_suppression_gap")
    ds = decision.get("state") or {}
    if (not pid or policy not in adaptive.POLICIES or decision.get("status") != "applied"
            or ds.get("turn_index") != turn_index or ds.get("input_digest") != _digest(user_input)):
        return finish("missing_or_stale_applied_decision")
    branch = (plan.get("counterfactual_pragmatic_branch_m34") or {}).get("selected_branch") or {}
    if branch.get("policy_id") != policy:
        return finish("branch_policy_mismatch")
    match = adaptive.match_verified_trigger_relation_m37(state, user_input)
    source = plan.get("pragmatic_trigger_relation_m37") or {}
    prior = source.get("match") or {}
    decision_match = ds.get("trigger_relation_match_m37") or {}
    if (match.get("status") != "matched_verified_trigger_relation" or not source.get("authoritative")
            or match.get("response_policy") != policy
            or any(view.get("relation_id") != match.get("relation_id")
                   or view.get("response_policy") != policy
                   or view.get("current_evidence_digest") != _digest(user_input)
                   for view in (prior, decision_match))):
        return finish("no_current_active_verified_relation_agreement")
    audit = plan.get("semantic_persona_surface_verifier_m39") or {}
    if (audit.get("status") not in {"accepted_verified_surface", "repaired_and_verified"}
            or audit.get("protected_route") or audit.get("policy_act_match_after") is not True
            or audit.get("unresolved_violations") != [] or audit.get("selected_policy_id") != policy
            or audit.get("final_reply_digest") != _digest(reply)
            or (audit.get("source_frame") or {}).get("source_digest") != _digest(user_input)):
        return finish("final_surface_not_verified_for_this_action")
    ledger = state.get("outcome_calibration_ledger_m27") or []
    if any(row.get("prediction_id") == pid for row in ledger):
        return finish("existing_prediction_ledger_entry_preserved")
    if any(row.get("prediction_id") == pid for row in state.get(STORE) or []):
        return finish("existing_receipt_preserved")
    candidate = adaptive.set_pending_prediction(state, decision, turn_index=turn_index)
    # Preserve unrelated fields and existing ledger entries verbatim. Do not
    # upgrade the M26 distribution: a verified relation is not implicit truth.
    state["pending_prediction"] = deepcopy(candidate["pending_prediction"])
    entry = next(row for row in candidate["outcome_calibration_ledger_m27"]
                 if row["prediction_id"] == pid)
    state["outcome_calibration_ledger_m27"] = [*deepcopy(ledger), deepcopy(entry)][-adaptive.M27_MAX_LEDGER_ENTRIES:]
    state["outcome_calibration_summary_m27"] = adaptive.build_causal_outcome_calibration_summary_m27(state)
    state["last_turn"] = int(turn_index)
    receipt = _clean_receipt({"schema": SCHEMA, "prediction_id": pid,
                             "policy_id": policy, "relation_id": match["relation_id"],
                             "created_turn": int(turn_index), "input_digest": _digest(user_input),
                             "reply_digest": _digest(reply), "relation_confidence": match.get("confidence", 0)})
    state[STORE] = [*deepcopy(state.get(STORE) or []), receipt][-32:]
    trace.update(status="registered_for_next_user_turn", next_pending_id=pid,
                 relation_id=match["relation_id"], receipt=deepcopy(receipt),
                 eligible_for_implicit_calibration=bool(entry.get("eligible_for_implicit_calibration")))
    return finish("verified_final_action_restores_missing_feedback_link")


def observe_executed_action_m44(model, user_input, turn_index=0):
    pending = (model or {}).get("pending_prediction") or {}
    receipts = [_clean_receipt(row) for row in (model or {}).get(STORE) or []]
    receipts = [row for row in receipts if row]
    prior = next((row for row in reversed(receipts)
                  if row["prediction_id"] == pending.get("prediction_id") and row["outcome"] == "pending"), None)
    expired = bool(prior and turn_index != prior["valid_next_user_turn"])
    # Blank observation invokes the original uncertain-outcome path when a
    # receipt is stale. The real current input still reaches the normal planner.
    state, feedback = _BASE_OBSERVE(model, "" if expired else user_input, turn_index=turn_index)
    if prior is None:
        return state, feedback
    outcome = "expired" if expired else feedback.get("status")
    if outcome not in {"supported", "contradicted", "uncertain", "expired"}:
        outcome = "uncertain"
    for row in receipts:
        if row["prediction_id"] == prior["prediction_id"]:
            row.update(outcome=outcome, resolved_turn=int(turn_index), feedback_digest=_digest(user_input))
    state[STORE] = receipts[-32:]
    feedback[OUTCOME_LABEL] = {"schema": "uruha_executed_action_outcome_m44",
                              "prediction_id": prior["prediction_id"], "relation_id": prior["relation_id"],
                              "performed_policy": prior["policy_id"], "created_turn": prior["created_turn"],
                              "observed_turn": int(turn_index), "outcome": outcome,
                              "linked": bool(feedback.get("feedback_linked_to_previous_prediction")) and not expired,
                              "verification_authority": "existing_M27_M38_not_receipt_creation",
                              "feedback_digest": _digest(user_input), "raw_dialogue_persisted": False,
                              "mental_fact_write_count": 0}
    return state, feedback


def materialize_trace_m44(result, feedback=None):
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    logic = result.setdefault("logic", {})
    current = result.setdefault("runtime_trace", {})
    outcome = (feedback or {}).get(OUTCOME_LABEL)
    if outcome and outcome.get("observed_turn") == current.get("cycle_index"):
        logic[OUTCOME_LABEL] = deepcopy(outcome)
    rows = [row for row in current.get("blackboard") or [] if row.get("label") not in {LABEL, OUTCOME_LABEL}]
    for label, stage in ((OUTCOME_LABEL, "calibrate"), (LABEL, "writeback")):
        payload = logic.get(label)
        if isinstance(payload, dict) and payload.get("raw_dialogue_persisted") is False:
            current[label] = deepcopy(payload)
            rows.append({"label": label, "stage": stage, "payload": deepcopy(payload), "salience": 0.98})
    current["blackboard"] = rows
    sync_current_history_m41_1(result)


def install_m44_executed_action_receipts():
    global _INSTALLED
    if _INSTALLED:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    old_emit, old_run = UruhaBrainV4_Mac.emit_response_if_ready, UruhaBrainV4_Mac.run_turn_debug

    def finish(self, result):
        materialize_trace_m44(result, self.runtime.last_adaptive_person_feedback)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def emit(self, event, tick_result):
        result = old_emit(self, event, tick_result)
        state, trace = register_executed_action_m44(self.runtime.adaptive_person_model,
            result.get("logic"), event.get("user_input"), result.get("reply"), self.runtime.cycle_index)
        if trace["status"] == "registered_for_next_user_turn":
            self.runtime.set_adaptive_person_model(state)
            trace["persistence"] = deepcopy(self._persist_adaptive_person_model())
            snapshot = result.get("runtime_state")
            if isinstance(snapshot, dict):
                snapshot["adaptive_person_model"] = deepcopy(self.runtime.adaptive_person_model)
                snapshot["last_adaptive_person_persistence"] = deepcopy(self.runtime.last_adaptive_person_persistence)
        result.setdefault("logic", {})[LABEL] = trace
        return finish(self, result)

    def run(self, user_input, input_context=None):
        return finish(self, old_run(self, user_input, input_context=input_context))

    adaptive._normalise_model = normalise_model_m44
    adaptive.observe_next_turn = observe_executed_action_m44
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True
