"""Product-only gate: absence of an inference is not a clarification target.

Human pragmatics is the research object; Uruha is an expression instance. This
adapter checks typed planner evidence, never user-word matching or test answers.
It neither verifies a person's intent nor credits the prediction outcome. The
existing frozen planner still proposes actions and handles all other turns.
"""
from copy import deepcopy
import hashlib
import json

import uruha_personhood_loop as personhood

TRACE = "grounded_validation_p2"
_previous_apply = personhood.apply_longitudinal_model_to_plan
_ACTION_FIELDS = (
    "intent", "scene", "hidden_intent", "reply_goal", "core_message_jp",
    "response_mode", "surface_act", "dialogue_act", "payload_level",
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _qualification(candidate, hypothesis):
    """Bounded structural eligibility, not independent semantic verification."""
    kind = str(candidate.get("kind") or "")
    if not kind.startswith("pragmatic_"):
        return True, "non_pragmatic_candidate_unchanged"
    pragmatic = (hypothesis or {}).get("pragmatic_understanding_v2_13") or {}
    if pragmatic.get("schema") != personhood.PRAGMATIC_SCHEMA:
        return False, "missing_typed_pragmatic_source"
    if not pragmatic.get("pragmatic_label") or pragmatic.get("pragmatic_label") == "literal_intent_unresolved":
        return False, "unresolved_slot_is_not_a_specific_hypothesis"
    source = (pragmatic.get("inferences") or {}).get(kind.removeprefix("pragmatic_")) or {}
    if not (hypothesis or {}).get("hypothesis_id") or hypothesis["hypothesis_id"] not in (candidate.get("hypothesis_ids") or []):
        return False, "candidate_not_linked_to_current_hypothesis"
    if not source.get("value") or source.get("value") != candidate.get("value"):
        return False, "candidate_value_not_bound_to_source_field"
    if source.get("epistemic_status") != "provisional_inference" or not source.get("evidence"):
        return False, "candidate_lacks_provisional_evidence"
    return True, "typed_candidate_retained_not_independently_verified"


def apply_grounded_validation_p2(plan, model, hypothesis, turn_index, direct_user_report=None):
    validation_before = deepcopy((model or {}).get("active_validation") or
                                 personhood.empty_longitudinal_model()["active_validation"])
    logic, state, strategy = _previous_apply(
        plan, model, hypothesis, turn_index, direct_user_report=direct_user_report)
    # Never withdraw an older pending question merely because this turn lacks
    # its source. The gate only controls a newly proposed action in this call.
    candidate = strategy.get("pending") or {}
    new_question = bool(strategy.get("changed_plan") and not validation_before.get("pending")
                        and candidate.get("asked_turn") == int(turn_index))
    eligible, reason = _qualification(candidate, hypothesis) if new_question else (True, "no_new_validation")
    blocked = bool(new_question and not eligible)
    if blocked:
        for field in _ACTION_FIELDS:
            if field in (plan or {}):
                logic[field] = deepcopy(plan[field])
            else:
                logic.pop(field, None)
        state["active_validation"] = validation_before
        strategy.update(changed_plan=False, pending=deepcopy(validation_before.get("pending")),
                        reason="p2_unresolved_inference_cannot_authorize_specific_question")
    audit = {
        "schema": "uruha_grounded_validation_p2",
        "status": "new_ungrounded_validation_withdrawn" if blocked else "existing_plan_retained",
        "reason": reason, "blocked": blocked, "new_question_proposed": new_question,
        "hypothesis_id": (hypothesis or {}).get("hypothesis_id"),
        "pragmatic_label": ((hypothesis or {}).get("pragmatic_understanding_v2_13") or {}).get("pragmatic_label"),
        "candidate_id": candidate.get("model_item_id") if new_question else None,
        "candidate_kind": candidate.get("kind") if new_question else None,
        "proposal_digest": _digest(candidate) if new_question else None,
        "previous_validation_preserved": bool(validation_before.get("pending")),
        "upstream_outcome_changed": False, "mental_fact_write_count": 0,
        "added_model_calls": 0, "raw_dialogue_persisted": False,
        "claim_boundary": "typed clarification eligibility only; no acknowledgement recognition or support credit",
    }
    strategy[TRACE] = audit
    logic["active_validation_strategy_v2_13"] = strategy
    return logic, state, strategy


def install_grounded_validation_p2():
    global _previous_apply
    if personhood.apply_longitudinal_model_to_plan is apply_grounded_validation_p2:
        return False
    _previous_apply = personhood.apply_longitudinal_model_to_plan
    personhood.apply_longitudinal_model_to_plan = apply_grounded_validation_p2
    return True
