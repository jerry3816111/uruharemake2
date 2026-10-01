"""Product-only arbitration for repeated, still-unverified indirect refusals.

The pragmatic layer may reasonably surface one bounded interpretation of an
indirect refusal.  Repeating that interpretation, and then replacing a
completed compact reply with a generic active-validation question, increases
interaction pressure without adding evidence.  This adapter keeps the typed
hypothesis, verification, calibration and longitudinal updates, but lets the
already-generated compact direct plan win on the second still-uncertain
refusal.  It never treats the inferred private intent as fact.
"""
from copy import deepcopy
import hashlib
import json

import uruha_personhood_loop as personhood


LABEL = "repeated_refusal_arbitration_p2"
SCHEMA = "uruha_repeated_refusal_arbitration_p2"
_INSTALLED = False
_ORIGINAL_PRAGMATIC = None
_ORIGINAL_LONGITUDINAL = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_INSTALLED_UNDER_GROUNDED = False

_ACTION_FIELDS = (
    "intent",
    "scene",
    "hidden_intent",
    "reply_goal",
    "core_message_jp",
    "response_mode",
    "surface_act",
    "dialogue_act",
    "payload_level",
)
_DIRECT_RESPONSE_MODES = {"direct_answer", "direct_answer_with_hedge"}
_PROTECTED_ROUTE_TYPES = {"safety_sensitive", "explicit_correction", "factual_or_memory"}


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _action_snapshot(plan):
    return {
        field: deepcopy(plan[field])
        for field in _ACTION_FIELDS
        if field in (plan or {})
    }


def _restore_action(logic, snapshot):
    for field in _ACTION_FIELDS:
        if field in snapshot:
            logic[field] = deepcopy(snapshot[field])
        else:
            logic.pop(field, None)


def _compact_call_completed(plan):
    compact = (((plan or {}).get("bounded_slow_path_m21") or {}).get(
        "compact_general_plan_p2"
    ) or {})
    return bool(
        compact.get("schema") == "uruha_compact_general_plan_p2"
        and compact.get("completed") is True
        and compact.get("candidate_count") == 3
    )


def _protected_base_plan(plan, hypothesis):
    route_type = str((((plan or {}).get("semantic_route_m22") or {}).get("selected_type")) or "")
    intent = str((plan or {}).get("intent") or "")
    return bool(
        personhood._protected_plan(plan or {}, hypothesis or {})
        or route_type in _PROTECTED_ROUTE_TYPES
        or (plan or {}).get("memory_use_expected")
        or (plan or {}).get("memory_recall_contract")
        or (plan or {}).get("profile_grounding_shadow")
        or (plan or {}).get("correction_aware_surface_m20")
        or intent.startswith("recall_")
        or "correction" in intent
        or "identity" in intent
        or "boundary" in intent
    )


def _scope(plan, pragmatic, hypothesis, pragmatic_verification):
    if not _compact_call_completed(plan):
        return False, "compact_general_plan_not_completed", {}
    if _protected_base_plan(plan, hypothesis):
        return False, "protected_plan_contract", {}
    if str((plan or {}).get("scene") or "") != "casual":
        return False, "non_casual_base_plan", {}
    if str((plan or {}).get("response_mode") or "") not in _DIRECT_RESPONSE_MODES:
        return False, "non_direct_base_plan", {}
    if str((plan or {}).get("surface_act") or "") not in {"plain_reply", "direct_answer"}:
        return False, "non_plain_base_plan", {}

    previous = (pragmatic_verification or {}).get("previous_pragmatic_snapshot") or {}
    if str((pragmatic or {}).get("pragmatic_label") or "") != "indirect_refusal":
        return False, "current_pragmatic_label_not_indirect_refusal", {}
    if str(previous.get("pragmatic_label") or "") != "indirect_refusal":
        return False, "previous_pragmatic_label_not_indirect_refusal", {}
    if str((pragmatic_verification or {}).get("status") or "") != "uncertain":
        return False, "previous_pragmatic_outcome_not_uncertain", {}

    action = ((pragmatic or {}).get("inferences") or {}).get("action_tendency") or {}
    evidence = [
        row
        for row in action.get("evidence") or []
        if row.get("modality") == "text"
        and row.get("source") == "current_user_input"
        and row.get("epistemic_status") == "known_observation"
    ]
    if (
        action.get("value") != "decline_or_delay"
        or action.get("epistemic_status") != "provisional_inference"
        or not evidence
    ):
        return False, "current_decline_tendency_lacks_typed_text_evidence", {}
    return True, "repeated_uncertain_decline_with_completed_direct_plan", {
        "current_pragmatic_id": (pragmatic or {}).get("pragmatic_id"),
        "previous_pragmatic_id": previous.get("pragmatic_id"),
        "verification_status": "uncertain",
        "action_tendency": "decline_or_delay",
        "current_text_evidence_count": len(evidence),
        "current_text_evidence_shape_sha256": _digest(
            [
                {
                    "modality": row.get("modality"),
                    "source": row.get("source"),
                    "epistemic_status": row.get("epistemic_status"),
                }
                for row in evidence
            ]
        ),
    }


def apply_repeated_refusal_attunement_p2(
    plan,
    pragmatic_understanding,
    hypothesis=None,
    pragmatic_verification=None,
    hypothesis_verification=None,
):
    delegate = _ORIGINAL_PRAGMATIC or personhood.apply_pragmatic_attunement_to_plan
    if delegate is apply_repeated_refusal_attunement_p2:
        raise RuntimeError("repeated-refusal pragmatic delegate is unavailable")
    adjusted = delegate(
        plan,
        pragmatic_understanding,
        hypothesis=hypothesis,
        pragmatic_verification=pragmatic_verification,
        hypothesis_verification=hypothesis_verification,
    )
    eligible, reason, evidence = _scope(
        plan,
        pragmatic_understanding,
        hypothesis or {},
        pragmatic_verification or {},
    )
    if not eligible:
        return adjusted

    base_action = _action_snapshot(plan)
    pragmatic_proposal = _action_snapshot(adjusted)
    audit = {
        "schema": SCHEMA,
        "status": "candidate_reserved",
        "eligible": True,
        "reason": reason,
        **evidence,
        "base_compact_action": base_action,
        "base_compact_core_jp": base_action.get("core_message_jp"),
        "base_compact_core_sha256": _digest(base_action.get("core_message_jp")),
        "pragmatic_proposal_action": pragmatic_proposal,
        "pragmatic_proposal_core_jp": pragmatic_proposal.get("core_message_jp"),
        "pragmatic_proposal_core_sha256": _digest(
            pragmatic_proposal.get("core_message_jp")
        ),
        "validation_proposal": None,
        "selected_action": None,
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_intent_treated_as_fact": False,
        "claim_boundary": (
            "low-interference product response arbitration only; the indirect-refusal "
            "interpretation remains provisional and is not private-state truth"
        ),
    }
    logic = deepcopy(adjusted)
    logic[LABEL] = audit
    strategy = deepcopy(logic.get("pragmatic_attunement_strategy_v2_13") or {})
    strategy["downstream_arbitration_candidate"] = LABEL
    strategy["effective_after_downstream_arbitration"] = None
    logic["pragmatic_attunement_strategy_v2_13"] = strategy
    return logic


def apply_repeated_refusal_arbitration_p2(
    plan,
    model,
    hypothesis,
    turn_index,
    direct_user_report=None,
):
    delegate = _ORIGINAL_LONGITUDINAL or personhood.apply_longitudinal_model_to_plan
    if delegate is apply_repeated_refusal_arbitration_p2:
        raise RuntimeError("repeated-refusal longitudinal delegate is unavailable")
    validation_before = deepcopy(
        (model or {}).get("active_validation")
        or personhood.empty_longitudinal_model()["active_validation"]
    )
    logic, state, strategy = delegate(
        plan,
        model,
        hypothesis,
        turn_index,
        direct_user_report=direct_user_report,
    )
    audit = deepcopy((plan or {}).get(LABEL) or {})
    if audit.get("schema") != SCHEMA or not audit.get("eligible"):
        return logic, state, strategy

    pending_before = deepcopy(validation_before.get("pending"))
    pending_after = deepcopy(strategy.get("pending"))
    new_question = bool(
        strategy.get("changed_plan")
        and not pending_before
        and pending_after
        and pending_after.get("asked_turn") == int(turn_index)
    )
    expected_need = (
        (((hypothesis or {}).get("pragmatic_understanding_v2_13") or {}).get("inferences") or {})
        .get("implicit_need", {})
        .get("value")
    )
    proposal_matches = bool(
        not new_question
        or (
            pending_after.get("kind") == "pragmatic_implicit_need"
            and pending_after.get("value") == expected_need
        )
    )
    can_select = bool(
        not pending_before
        and not direct_user_report
        and not strategy.get("communication_preference_applied")
        and proposal_matches
    )
    audit["validation_proposal"] = (
        {
            "kind": pending_after.get("kind"),
            "value": pending_after.get("value"),
            "question_jp": pending_after.get("question_jp"),
            "question_sha256": _digest(pending_after.get("question_jp")),
            "proposal_sha256": _digest(pending_after),
        }
        if new_question
        else None
    )
    audit["upstream_validation_changed_plan"] = bool(strategy.get("changed_plan"))
    audit["existing_pending_validation_preserved"] = bool(pending_before)

    if can_select:
        _restore_action(logic, audit.get("base_compact_action") or {})
        if new_question:
            state["active_validation"] = deepcopy(validation_before)
        strategy = deepcopy(strategy)
        strategy.update(
            changed_plan=False,
            pending=deepcopy(pending_before),
            reason=(
                "repeated_decline_low_interference_plan_outranks_new_validation"
                if new_question
                else "repeated_decline_low_interference_plan_outranks_repeated_inference"
            ),
        )
        audit.update(
            status="selected_low_interference_compact_plan",
            selected_action=_action_snapshot(logic),
            selected_core_jp=logic.get("core_message_jp"),
            selected_core_sha256=_digest(logic.get("core_message_jp")),
            pragmatic_proposal_suppressed=True,
            new_validation_proposal_suppressed=new_question,
            longitudinal_updates_retained=True,
        )
        pragmatic_strategy = deepcopy(
            logic.get("pragmatic_attunement_strategy_v2_13") or {}
        )
        pragmatic_strategy.update(
            effective_after_downstream_arbitration=False,
            downstream_arbitration=LABEL,
            proposal_retained_for_trace=True,
        )
        logic["pragmatic_attunement_strategy_v2_13"] = pragmatic_strategy
        grounded = strategy.get("grounded_validation_p2")
        if isinstance(grounded, dict):
            grounded = deepcopy(grounded)
            grounded.update(
                downstream_arbitration=LABEL,
                effective_new_question_after_arbitration=False,
            )
            strategy["grounded_validation_p2"] = grounded
    else:
        if pending_before:
            reason = "existing_pending_validation_contract_owns_action"
        elif direct_user_report:
            reason = "direct_user_report_owns_action"
        elif strategy.get("communication_preference_applied"):
            reason = "verified_communication_preference_owns_action"
        else:
            reason = "validation_proposal_not_bound_to_repeated_implicit_need"
        audit.update(
            status="candidate_not_selected",
            reason=reason,
            selected_action=_action_snapshot(logic),
            selected_core_jp=logic.get("core_message_jp"),
            selected_core_sha256=_digest(logic.get("core_message_jp")),
            pragmatic_proposal_suppressed=False,
            new_validation_proposal_suppressed=False,
            longitudinal_updates_retained=True,
        )

    logic[LABEL] = audit
    strategy[LABEL] = {
        "schema": SCHEMA,
        "status": audit["status"],
        "selected_core_sha256": audit.get("selected_core_sha256"),
        "new_validation_proposal_suppressed": audit.get(
            "new_validation_proposal_suppressed", False
        ),
        "raw_dialogue_persisted": False,
    }
    logic["active_validation_strategy_v2_13"] = strategy
    return logic, state, strategy


def materialize_repeated_refusal_arbitration_p2(result):
    logic = result.setdefault("logic", {})
    payload = logic.get(LABEL)
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if isinstance(payload, dict) and payload.get("schema") == SCHEMA:
        payload = deepcopy(payload)
        guard = logic.get("visible_language_guard") or {}
        final_surface = str(
            guard.get("final_reply") or result.get("reply") or result.get("response") or ""
        ).strip()
        payload.update(
            final_visible_surface_jp=final_surface,
            final_visible_surface_sha256=_digest(final_surface),
            final_visible_surface_matches_selected_core=bool(
                final_surface and final_surface == payload.get("selected_core_jp")
            ),
            visible_language_guard_applied=bool(guard),
            flow=[
                "completed_compact_plan",
                "repeated_pragmatic_proposal",
                "active_validation_proposal",
                "low_interference_selection",
                "visible_japanese_surface",
            ],
        )
        logic[LABEL] = payload
        index = next(
            (
                i
                for i, row in enumerate(rows)
                if row.get("label") == "active_validation_strategy_v2_13"
            ),
            next(
                (i for i, row in enumerate(rows) if row.get("label") == "utterance"),
                len(rows),
            ),
        )
        rows.insert(
            index,
            {
                "stage": "select",
                "label": LABEL,
                "payload": deepcopy(payload),
                "salience": 0.995,
            },
        )
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_repeated_refusal_arbitration_p2():
    global _INSTALLED, _ORIGINAL_PRAGMATIC, _ORIGINAL_LONGITUDINAL
    global _ORIGINAL_RUN, _ORIGINAL_EMIT, _INSTALLED_UNDER_GROUNDED
    if _INSTALLED:
        return False

    from uruha_brain_mac import UruhaBrainV4_Mac
    import uruha_grounded_validation_p2 as grounded
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_PRAGMATIC = personhood.apply_pragmatic_attunement_to_plan
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    personhood.apply_pragmatic_attunement_to_plan = apply_repeated_refusal_attunement_p2
    # Grounded validation is already the product owner for this hook.  Insert
    # arbitration immediately inside it so the legacy installer remains
    # idempotent and its trace still describes the effective post-arbitration
    # validation state.  A standalone installation keeps the ordinary wrapper
    # path for development use.
    if personhood.apply_longitudinal_model_to_plan is grounded.apply_grounded_validation_p2:
        _ORIGINAL_LONGITUDINAL = grounded._previous_apply
        grounded._previous_apply = apply_repeated_refusal_arbitration_p2
        _INSTALLED_UNDER_GROUNDED = True
    else:
        _ORIGINAL_LONGITUDINAL = personhood.apply_longitudinal_model_to_plan
        personhood.apply_longitudinal_model_to_plan = apply_repeated_refusal_arbitration_p2
        _INSTALLED_UNDER_GROUNDED = False

    def finish(self, result):
        materialize_repeated_refusal_arbitration_p2(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if (
            self.runtime.turn_traces
            and self.runtime.turn_traces[-1].get("cycle_index")
            == result["runtime_trace"].get("cycle_index")
        ):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, _ORIGINAL_EMIT(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True
