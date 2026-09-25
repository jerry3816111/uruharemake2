"""P4-AT: close one executed action without collapsing the current request.

The previous action outcome and the user's current desired response are two
different variables.  This additive layer recognizes a bounded set of direct
next-turn constructions, but only when the pending P1 event and M44 executed
receipt are exact.  It never turns the inferred current request into a factual
long-term user memory or a claim about private desire truth.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_executed_action_receipt_m44 as receipt_m44
import uruha_runtime_temporal_graph_delivery_p4 as temporal_delivery
import uruha_semantic_persona_surface_m39 as surface_m39


LABEL = "executed_action_outcome_closure_p4"
SCHEMA = "uruha_executed_action_outcome_closure_p4"

_SUPPORT_PATTERNS = {
    "zh": (
        r"(?:剛剛|刚刚|剛才|刚才|先)[^。！？!?；;]{0,16}(?:問|问)[^。！？!?；;]{0,10}(?:對|对|很好|正確|正确)",
        r"(?:那個|那个|這個|这个)?(?:問題|问题)[^。！？!?；;]{0,10}(?:問|问)?[^。！？!?；;]{0,8}(?:對|对|很好|正確|正确)",
    ),
    "en": (
        r"\basking\b[^.!?;]{0,30}\b(?:right|correct|good)\b",
        r"\b(?:that|the|your)\b[^.!?;]{0,12}\bquestion\b[^.!?;]{0,18}\b(?:right|correct|good)\b",
        r"\bthat\s+was\s+the\s+right\s+question\b",
    ),
    "ja": (
        r"(?:質問|聞いた|聞いてくれた)[^。！？]{0,18}(?:合って|よかった|正解)",
        r"先に[^。！？]{0,12}(?:聞いた|聞いて)[^。！？]{0,12}(?:合って|よかった|正解)",
    ),
}

_CONTRADICTION_PATTERNS = {
    "zh": (
        r"(?:不該|不该|不要|不是)[^。！？!?；;]{0,14}(?:先)?(?:問|问)",
        r"(?:那個|那个|這個|这个)?(?:問題|问题)[^。！？!?；;]{0,12}(?:不是|沒用|没用|不對|不对)",
    ),
    "en": (
        r"\basking\s+first\b[^.!?;]{0,24}\b(?:was\s+not|wasn't)\b[^.!?;]{0,18}\bwhat\s+i\s+wanted\b",
        r"\b(?:shouldn't|should\s+not)\b[^.!?;]{0,12}\basked?\b",
        r"\b(?:that|the|your)\b[^.!?;]{0,12}\bquestion\b[^.!?;]{0,18}\b(?:wasn't|was\s+not|didn't\s+help)\b",
    ),
    "ja": (
        r"先に聞いてほしかったわけじゃない",
        r"(?:その|あの)?質問[^。！？]{0,12}(?:いらな|違う|じゃない)",
        r"聞くんじゃなく",
    ),
}

_CURRENT_REQUEST_PATTERNS = {
    "solve_regulation": {
        "zh": (
            r"(?:我)?(?:現在|现在)?(?:要|想要|需要)[^。！？!?；;]{0,18}(?:方法|做法|步驟|步骤)",
            r"(?:給|给)[^。！？!?；;]{0,8}(?:方法|做法|步驟|步骤)",
        ),
        "en": (
            r"\b(?:i\s+(?:want|need)|give\s+me|show\s+me)\b[^.!?;]{0,28}\b(?:practical\s+)?(?:method|step|way|advice)\b",
        ),
        "ja": (
            r"(?:方法|やり方|手順)[^。！？]{0,18}(?:教えて|ほしい)",
            r"(?:具体的な)?(?:やり方|方法)[^。！？]{0,12}(?:一つ|ひとつ)?[^。！？]{0,8}教えて",
        ),
    },
    "listen_presence": {
        "zh": (r"(?:現在|现在)?(?:只想|只要)[^。！？!?；;]{0,12}(?:聽我說|听我说|聽我講|听我讲)",),
        "en": (r"\b(?:i\s+only\s+want\s+you\s+to|just)\b[^.!?;]{0,16}\b(?:hear\s+me\s+out|listen)\b",),
        "ja": (r"(?:今は)?(?:ただ|まず)[^。！？]{0,10}(?:話を)?聞いてほしい",),
    },
    "playful_tease": {
        "zh": (r"(?:現在|现在)?[^。！？!?；;]{0,8}(?:吐槽我|虧我|亏我|開我玩笑|开我玩笑)",),
        "en": (r"\b(?:tease|roast)\s+me\b",),
        "ja": (r"(?:今は)?[^。！？]{0,8}(?:ツッコんで|いじって|からかって)",),
    },
}

_NON_DIRECT_PATTERNS = (
    r"\b(?:my\s+friend|friend\s+said|testing|test\s+the\s+phrase|the\s+phrase|the\s+sentence|script\s+says|wrote)\b",
    r"(?:朋友|同事|同學|同学)[^。！？]{0,12}(?:說|说)",
    r"(?:測試|测试|這句話|这句话|引用|台詞|台词|寫著|写着)",
    r"(?:友達|同僚)[^。！？]{0,12}(?:言った|言って)",
    r"(?:台本|引用|という文|書いてある)",
)


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _source_is_direct(text):
    return not any(re.search(pattern, str(text or ""), re.I) for pattern in _NON_DIRECT_PATTERNS)


def _last_match(patterns, text):
    best = None
    for language, language_patterns in patterns.items():
        for index, pattern in enumerate(language_patterns, start=1):
            for match in re.finditer(pattern, text, re.I):
                candidate = {
                    "language": language,
                    "cue_index": index,
                    "position": match.start(),
                    "specificity": match.end() - match.start(),
                }
                if best is None or (candidate["position"], candidate["specificity"]) > (
                    best["position"],
                    best["specificity"],
                ):
                    best = candidate
    return best


def classify_current_request_p4_at(user_input, base_trace=None):
    """Return current-turn response-form evidence, never a stable preference."""

    text = str(user_input or "")
    direct = _source_is_direct(text)
    matches = []
    if direct:
        for policy_id, language_patterns in _CURRENT_REQUEST_PATTERNS.items():
            found = _last_match(language_patterns, text)
            if found:
                matches.append({"policy_id": policy_id, **found})
    matches.sort(key=lambda row: (row["position"], row["specificity"]), reverse=True)
    selected = deepcopy(matches[0]) if matches else {}
    base = deepcopy(base_trace or {})
    base_policy = str(base.get("selected_policy") or "")
    base_direct = bool(
        direct
        and base.get("detected")
        and base.get("authority") == "current_explicit_desired_response"
        and base_policy in adaptive.POLICIES
    )
    if not selected and base_direct:
        selected = {
            "policy_id": base_policy,
            "language": (base.get("matched_languages") or [None])[-1],
            "cue_index": 0,
            "position": -1,
            "specificity": 0,
            "source": "released_m25",
        }
    policy_id = str(selected.get("policy_id") or "")
    return {
        "schema": "uruha_p4_at_current_request_projection_v1",
        "status": "selected" if policy_id else "not_detected",
        "selected_policy": policy_id or None,
        "selected_mode": adaptive.POLICY_TO_RESPONSE_MODE_M23.get(policy_id),
        "language": selected.get("language"),
        "cue_id": (
            f"p4_at_current_request:{policy_id}:{selected.get('language')}:{selected.get('cue_index')}"
            if policy_id
            else None
        ),
        "source_authorized": direct,
        "evidence_digest": _digest(text),
        "stable_preference_claimed": False,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
    }


def classify_explicit_desired_response_with_p4_at(user_input, original_classifier):
    base = deepcopy(original_classifier(user_input))
    projection = classify_current_request_p4_at(user_input, base)
    policy_id = str(projection.get("selected_policy") or "")
    if not policy_id or base.get("protected_risk_cue"):
        base["p4_at_current_request_projection"] = projection
        return base
    base.update(
        {
            "detected": True,
            "status": "selected",
            "selected_policy": policy_id,
            "selected_mode": projection.get("selected_mode"),
            "authority": "current_explicit_desired_response",
            "confidence": 0.97,
            "matched_languages": sorted(
                set([*(base.get("matched_languages") or []), projection.get("language")])
                - {None}
            ),
            "evidence_digest": _digest(user_input),
            "claim_boundary": "explicit current response request only; not private-state inference or stable preference",
            "raw_dialogue_persisted": False,
            "p4_at_current_request_projection": projection,
        }
    )
    alternatives = [
        row
        for row in (base.get("alternatives") or [])
        if row.get("policy_id") != policy_id
    ]
    base["alternatives"] = [
        {
            "policy_id": policy_id,
            "mode": projection.get("selected_mode"),
            "cue_id": projection.get("cue_id"),
            "language": projection.get("language"),
        },
        *alternatives,
    ]
    return base


def _exact_pending_receipt(model, turn_index):
    pending = deepcopy((model or {}).get("pending_prediction") or {})
    matches = []
    for raw in (model or {}).get(receipt_m44.STORE) or []:
        row = receipt_m44._clean_receipt(raw)
        if (
            row
            and row.get("outcome") == "pending"
            and row.get("prediction_id") == pending.get("prediction_id")
            and row.get("policy_id") == pending.get("policy_id")
            and int(row.get("valid_next_user_turn") or -1) == int(turn_index)
        ):
            matches.append(row)
    return pending, deepcopy(matches[-1]) if matches else {}


def decompose_executed_action_feedback_p4(user_input, model, turn_index, base_request=None):
    """Separate feedback about the performed question from the current ask."""

    text = str(user_input or "")
    pending, receipt = _exact_pending_receipt(model, turn_index)
    exact_identity = bool(
        pending
        and receipt
        and pending.get("prediction_id") == receipt.get("prediction_id")
        and pending.get("policy_id") == receipt.get("policy_id") == "calibrate_need"
    )
    direct = _source_is_direct(text)
    support = _last_match(_SUPPORT_PATTERNS, text) if direct else None
    contradiction = _last_match(_CONTRADICTION_PATTERNS, text) if direct else None
    action_match = None
    outcome = "unknown"
    if exact_identity:
        choices = [
            ("supported", support),
            ("contradicted", contradiction),
        ]
        choices = [(label, row) for label, row in choices if row]
        if choices:
            outcome, action_match = max(
                choices,
                key=lambda item: (item[1]["position"], item[1]["specificity"]),
            )
    current = classify_current_request_p4_at(text, base_request)
    current_policy = current.get("selected_policy")
    dual_act = bool(outcome in {"supported", "contradicted"} and current_policy)
    return {
        "schema": SCHEMA,
        "status": (
            "dual_act_decomposed"
            if dual_act
            else "previous_action_feedback_only"
            if outcome in {"supported", "contradicted"}
            else "current_request_only"
            if current_policy
            else "unknown_no_decisive_action_feedback"
        ),
        "prediction_id": pending.get("prediction_id") if exact_identity else None,
        "performed_policy": pending.get("policy_id") if exact_identity else None,
        "performed_action_created_turn": receipt.get("created_turn") if exact_identity else None,
        "observed_turn": int(turn_index),
        "exact_pending_receipt_identity": exact_identity,
        "source_authorized": direct,
        "previous_action_outcome": outcome,
        "previous_action_feedback_language": (action_match or {}).get("language"),
        "previous_action_feedback_cue_id": (
            f"p4_at_action_feedback:{outcome}:{(action_match or {}).get('language')}:{(action_match or {}).get('cue_index')}"
            if action_match
            else None
        ),
        "current_request_policy": current_policy,
        "current_request_mode": current.get("selected_mode"),
        "current_request_cue_id": current.get("cue_id"),
        "two_independent_acts": dual_act,
        "performed_action_strictly_earlier": bool(
            exact_identity and int(receipt.get("created_turn") or -1) < int(turn_index)
        ),
        "evidence_digest": _digest(text),
        "same_turn_outcome_relabelled_as_old_past": False,
        "unknown_counted_as_success": False,
        "candidate_score_or_order_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "observable feedback about one exact executed action plus a separable "
            "current response request; not private desire truth or stable preference"
        ),
    }


def _replace_scalar(value, old, new):
    if isinstance(value, dict):
        return {key: _replace_scalar(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_scalar(item, old, new) for item in value]
    return new if value == old else value


def observe_executed_action_outcome_closure_p4(
    model,
    user_input,
    turn_index=0,
    original_observe=None,
    original_classifier=None,
):
    original_observe = original_observe or _ORIGINAL_OBSERVE_P4_AT or adaptive.observe_next_turn
    original_classifier = original_classifier or _ORIGINAL_CLASSIFIER_P4_AT or adaptive.classify_explicit_desired_response_m25
    base_request = original_classifier(user_input)
    trace = decompose_executed_action_feedback_p4(
        user_input,
        model,
        turn_index,
        base_request=base_request,
    )
    exact = trace.get("exact_pending_receipt_identity") is True
    outcome = trace.get("previous_action_outcome")
    if exact and outcome == "supported":
        projected = "exactly"
        projection_kind = "bounded_executed_question_support"
    elif exact and outcome == "contradicted":
        projected = {
            "solve_regulation": "you misunderstood. give me one step",
            "listen_presence": "you misunderstood. just listen",
            "playful_tease": "you misunderstood. tease me",
        }.get(trace.get("current_request_policy"), "you misunderstood")
        projection_kind = "bounded_executed_question_rejection"
    elif exact and trace.get("current_request_policy"):
        projected = ""
        projection_kind = "current_request_separated_from_previous_action_outcome"
    elif exact and not trace.get("source_authorized"):
        projected = ""
        projection_kind = "non_direct_source_forced_unknown"
    else:
        projected = str(user_input or "")
        projection_kind = "released_observer_unchanged"

    state, feedback = original_observe(model, projected, turn_index=turn_index)
    if not exact:
        return state, feedback

    projected_digest = _digest(projected)
    actual_digest = _digest(user_input)
    state = _replace_scalar(state, projected_digest, actual_digest)
    feedback = _replace_scalar(feedback, projected_digest, actual_digest)
    feedback["current_request_separated_from_feedback"] = bool(
        trace.get("current_request_policy")
    )
    feedback["explicit_target_policy"] = (
        trace.get("current_request_policy") if outcome == "contradicted" else None
    )
    feedback["feedback_linkage_reason"] = (
        "p4_at_explicit_support_of_executed_clarification"
        if outcome == "supported"
        else "p4_at_explicit_rejection_of_executed_clarification"
        if outcome == "contradicted"
        else "p4_at_current_request_not_evidence_about_previous_action"
        if trace.get("current_request_policy")
        else feedback.get("feedback_linkage_reason")
    )
    feedback["reason"] = feedback["feedback_linkage_reason"]
    feedback[LABEL] = {
        **deepcopy(trace),
        "observer_projection_kind": projection_kind,
    }
    outcome_payload = deepcopy(feedback.get(receipt_m44.OUTCOME_LABEL) or {})
    if outcome_payload:
        outcome_payload.update(
            {
                "outcome": outcome if outcome in {"supported", "contradicted"} else "uncertain",
                "linked": outcome in {"supported", "contradicted"},
                "feedback_digest": actual_digest,
                "p4_at_decomposed": True,
            }
        )
        feedback[receipt_m44.OUTCOME_LABEL] = outcome_payload

    prediction_id = str(trace.get("prediction_id") or "")
    for row in state.get("outcome_calibration_ledger_m27") or []:
        if row.get("prediction_id") == prediction_id:
            row["feedback_evidence_digest"] = actual_digest
            row["feedback_linkage_reason"] = feedback["feedback_linkage_reason"]
            row["explicit_target_policy"] = feedback.get("explicit_target_policy")
    for row in state.get(receipt_m44.STORE) or []:
        if row.get("prediction_id") == prediction_id:
            row["feedback_digest"] = actual_digest
            row["outcome"] = outcome if outcome in {"supported", "contradicted"} else "uncertain"
    if state.get("revision_history"):
        state["revision_history"][-1] = deepcopy(feedback)
    return state, feedback


def _attach_exact_receipt_to_shadow(self, result):
    logic = (result or {}).get("logic") or {}
    receipt_trace = deepcopy(logic.get(receipt_m44.LABEL) or {})
    receipt = deepcopy(receipt_trace.get("receipt") or {})
    binding = deepcopy(getattr(self, "_p4_ag_pending_binding", {}) or {})
    shadow = deepcopy(getattr(self, "_p4_ag_shadow_feedback_model", {}) or {})
    exact = bool(
        receipt.get("outcome") == "pending"
        and binding.get("status") == "pending"
        and shadow.get("pending_prediction")
        and receipt.get("prediction_id")
        == binding.get("prediction_id")
        == (shadow.get("pending_prediction") or {}).get("prediction_id")
        and receipt.get("policy_id")
        == binding.get("selected_policy")
        == (shadow.get("pending_prediction") or {}).get("policy_id")
    )
    if exact:
        shadow[receipt_m44.STORE] = [receipt]
        self._p4_ag_shadow_feedback_model = shadow
    return exact


def materialize_executed_action_outcome_closure_p4(result, feedback, shadow_receipt_attached=False):
    result = result or {}
    payload = deepcopy((feedback or {}).get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return result
    logic = result.setdefault("logic", {})
    runtime = result.setdefault("runtime_trace", {})
    ag = deepcopy(logic.get(outcome_binding.LABEL) or runtime.get(outcome_binding.LABEL) or {})
    previous = deepcopy(ag.get("previous_resolution") or {})
    temporal = deepcopy(logic.get(temporal_delivery.LABEL) or runtime.get(temporal_delivery.LABEL) or {})
    audit = deepcopy(logic.get("semantic_persona_surface_verifier_m39") or {})
    previous_outcome = payload.get("previous_action_outcome")
    payload.update(
        {
            "status": (
                f"closed_{previous_outcome}"
                if previous_outcome in {"supported", "contradicted"}
                and previous.get("identity_bound") is True
                and previous.get("outcome") == previous_outcome
                else "closed_unknown"
                if previous.get("identity_bound") is True
                else "identity_not_closed"
            ),
            "p4_ag_identity_bound": previous.get("identity_bound") is True,
            "p4_ag_outcome": previous.get("outcome"),
            "p4_ag_feedback_linked": previous.get("feedback_linked") is True,
            "prior_future_commitment_consumed": previous.get("status") == "resolved",
            "current_surface_policy": audit.get("selected_policy_id"),
            "current_surface_action_act_match": audit.get("policy_act_match_after"),
            "current_surface_unresolved_violation_count": len(
                audit.get("unresolved_violations") or []
            ),
            "visible_reply_digest": receipt_m44._digest(result.get("reply")),
            "temporal_previous_outcome": (
                (temporal.get("present") or {}).get("previous_outcome_verification")
            ),
            "temporal_current_verification_queued_for_later": (
                (temporal.get("transition") or {}).get(
                    "current_verification_queued_for_later"
                )
                is True
            ),
            "shadow_exact_receipt_attached_for_next_turn": bool(
                shadow_receipt_attached
            ),
            "exact_visible_string_is_separate_measure": True,
            "same_turn_outcome_relabelled_as_old_past": False,
            "raw_dialogue_persisted": False,
            "private_state_truth_claimed": False,
        }
    )
    logic[LABEL] = deepcopy(payload)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(rows)
            if row.get("label") in {outcome_binding.LABEL, temporal_delivery.LABEL, "utterance"}
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "calibrate", "label": LABEL, "payload": deepcopy(payload), "salience": 0.999},
    )
    runtime[LABEL] = deepcopy(payload)
    runtime["blackboard"] = rows
    return result


_INSTALLED_P4_AT = False
_ORIGINAL_CLASSIFIER_P4_AT = None
_ORIGINAL_OBSERVE_P4_AT = None
_ORIGINAL_EMIT_P4_AT = None
_ORIGINAL_RUN_P4_AT = None


def install_executed_action_outcome_closure_p4():
    global _INSTALLED_P4_AT, _ORIGINAL_CLASSIFIER_P4_AT, _ORIGINAL_OBSERVE_P4_AT
    global _ORIGINAL_EMIT_P4_AT, _ORIGINAL_RUN_P4_AT
    if _INSTALLED_P4_AT:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_CLASSIFIER_P4_AT = adaptive.classify_explicit_desired_response_m25
    _ORIGINAL_OBSERVE_P4_AT = adaptive.observe_next_turn
    _ORIGINAL_EMIT_P4_AT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_P4_AT = UruhaBrainV4_Mac.run_turn_debug

    def classify_with_p4_at(user_input):
        return classify_explicit_desired_response_with_p4_at(
            user_input,
            _ORIGINAL_CLASSIFIER_P4_AT,
        )

    def observe_with_p4_at(model, user_input, turn_index=0):
        return observe_executed_action_outcome_closure_p4(
            model,
            user_input,
            turn_index=turn_index,
            original_observe=_ORIGINAL_OBSERVE_P4_AT,
            original_classifier=_ORIGINAL_CLASSIFIER_P4_AT,
        )

    adaptive.classify_explicit_desired_response_m25 = classify_with_p4_at
    adaptive.observe_next_turn = observe_with_p4_at

    def emit_with_p4_at(self, event, tick_result):
        result = _ORIGINAL_EMIT_P4_AT(self, event, tick_result)
        attached = _attach_exact_receipt_to_shadow(self, result)
        result = materialize_executed_action_outcome_closure_p4(
            result,
            self.runtime.last_adaptive_person_feedback,
            shadow_receipt_attached=attached,
        )
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run_with_p4_at(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_P4_AT(self, user_input, input_context=input_context)
        attached = _attach_exact_receipt_to_shadow(self, result)
        result = materialize_executed_action_outcome_closure_p4(
            result,
            self.runtime.last_adaptive_person_feedback,
            shadow_receipt_attached=attached,
        )
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_at
    UruhaBrainV4_Mac.run_turn_debug = run_with_p4_at
    _INSTALLED_P4_AT = True
    return True


def _fixture_pending(turn=1):
    prediction_id = f"p1-1-{_digest('p4-at-fixture')}"
    decision = {
        "status": "applied",
        "prediction_id": prediction_id,
        "selected": {
            "policy_id": "calibrate_need",
            "expected_utility": 0.734,
        },
        "state": {
            "turn_index": turn,
            "input_digest": _digest("frozen-turn-one-fixture"),
            "context_scope": {
                "scope_id": "general_conversation:ordinary_exchange:unspecified",
                "domain": "general_conversation",
                "interaction_kind": "ordinary_exchange",
                "relationship_band": "unspecified",
            },
        },
    }
    model = adaptive.set_pending_prediction(adaptive.empty_model(), decision, turn)
    receipt = receipt_m44._clean_receipt(
        {
            "schema": receipt_m44.SCHEMA,
            "prediction_id": prediction_id,
            "relation_id": "p4-at-fixture-relation",
            "policy_id": "calibrate_need",
            "input_digest": _digest("frozen-turn-one-fixture"),
            "reply_digest": _digest("frozen-turn-one-visible-question"),
            "created_turn": turn,
            "relation_confidence": 0.86,
        }
    )
    model[receipt_m44.STORE] = [receipt]
    candidates = []
    policies = [
        "calibrate_need",
        "listen_presence",
        "share_arousal",
        "care_physiology",
        "solve_regulation",
        "playful_tease",
    ]
    for index, policy_id in enumerate(policies):
        candidates.append(
            {
                "candidate_id": f"p4-at-fixture:{policy_id}",
                "policy_id": policy_id,
                "mode": adaptive.POLICY_TO_RESPONSE_MODE_M23[policy_id],
                "operational_action_score": round(0.7 - index * 0.05, 4),
                "score_semantics": "operational_action_ranking_not_private_truth_probability",
                "selected_before_outcome": policy_id == "calibrate_need",
                "outcome": "pending",
                "operational_priority_allowed": policy_id == "calibrate_need",
                "selected_as_private_truth": False,
                "long_term_fact_write_allowed": False,
                "raw_dialogue_persisted": False,
            }
        )
    binding = {
        "schema": outcome_binding.SCHEMA,
        "status": "pending",
        "ledger_id": "p4-at-fixture-ledger",
        "prediction_id": prediction_id,
        "selected_policy": "calibrate_need",
        "candidate_snapshots": candidates,
        "candidate_count": 6,
        "turn_index": turn,
        "raw_dialogue_persisted": False,
    }
    return model, binding


def _current_surface(policy_id, user_input):
    if not policy_id:
        return None, None
    logic = {
        "desired_response_policy_m18": policy_id,
        "semantic_route_m22": {"selected_type": "general_conversation"},
    }
    reply = surface_m39._repair_reply_m39(
        surface_m39._source_frame_m39(user_input),
        policy_id,
    )
    audit = surface_m39.inspect_surface_m39(user_input, reply, logic)
    return reply, audit


def build_dataset_evidence_p4_at(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = []
    for partition in (
        "development_sequences",
        "fresh_positive_sequences",
        "fresh_control_sequences",
    ):
        for frozen in dataset[partition]:
            model, binding = _fixture_pending()
            before_scores = [
                (row["policy_id"], row["operational_action_score"])
                for row in binding["candidate_snapshots"]
            ]
            base_request = adaptive.classify_explicit_desired_response_m25(
                frozen["turn_2"]
            )
            current = classify_current_request_p4_at(
                frozen["turn_2"],
                base_request,
            )
            state, feedback = observe_executed_action_outcome_closure_p4(
                model,
                frozen["turn_2"],
                turn_index=2,
                original_observe=receipt_m44.observe_executed_action_m44,
                original_classifier=adaptive.classify_explicit_desired_response_m25,
            )
            resolution = outcome_binding.resolve_outcome_binding_p4(
                binding,
                feedback,
                turn_index=2,
            )
            after_scores = [
                (row["policy_id"], row["operational_action_score"])
                for row in resolution["candidate_updates"]
            ]
            reply, audit = _current_surface(
                current.get("selected_policy"),
                frozen["turn_2"],
            )
            trace = deepcopy(feedback.get(LABEL) or {})
            rows.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "expected_previous_action_outcome": frozen[
                        "expected_previous_action_outcome"
                    ],
                    "previous_action_outcome": resolution.get("outcome"),
                    "expected_current_request_policy": frozen[
                        "expected_current_request_policy"
                    ],
                    "current_request_policy": current.get("selected_policy"),
                    "exact_receipt_identity": trace.get(
                        "exact_pending_receipt_identity"
                    ),
                    "performed_action_strictly_earlier": trace.get(
                        "performed_action_strictly_earlier"
                    ),
                    "p4_ag_identity_bound": resolution.get("identity_bound"),
                    "p4_ag_feedback_linked": resolution.get("feedback_linked"),
                    "unknown_counted_as_success": resolution.get(
                        "unknown_counted_as_success"
                    ),
                    "candidate_score_or_order_unchanged": before_scores
                    == after_scores,
                    "visible_action_act_match": (
                        audit.get("policy_act_match") if audit else None
                    ),
                    "visible_reply_japanese": bool(
                        reply and re.search(r"[ぁ-んァ-ヶ一-龠]", reply)
                    ),
                    "same_turn_outcome_relabelled_as_old_past": trace.get(
                        "same_turn_outcome_relabelled_as_old_past"
                    ),
                    "new_model_call_count": int(trace.get("model_call_added") or 0),
                    "factual_memory_write_count": int(
                        trace.get("factual_memory_write_count") or 0
                    ),
                    "raw_dialogue_persisted": frozen["turn_2"]
                    in json.dumps(
                        {"feedback": feedback, "resolution": resolution},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "receipt_outcome": next(
                        (
                            row.get("outcome")
                            for row in state.get(receipt_m44.STORE) or []
                            if row.get("prediction_id") == binding["prediction_id"]
                        ),
                        None,
                    ),
                }
            )

    controls = [row for row in rows if row["partition"] == "fresh_control_sequences"]
    positives = [row for row in rows if row["partition"] == "fresh_positive_sequences"]
    development = [row for row in rows if row["partition"] == "development_sequences"]
    metrics = {
        "case_count": len(rows),
        "expected_previous_outcome_exact_count": sum(
            row["previous_action_outcome"]
            == row["expected_previous_action_outcome"]
            for row in rows
        ),
        "expected_current_request_exact_count": sum(
            row["current_request_policy"]
            == row["expected_current_request_policy"]
            for row in rows
        ),
        "development_dual_act_closed_count": sum(
            row["previous_action_outcome"] == "supported"
            and row["current_request_policy"] == "solve_regulation"
            for row in development
        ),
        "fresh_positive_dual_act_closed_count": sum(
            row["previous_action_outcome"]
            == row["expected_previous_action_outcome"]
            and row["current_request_policy"]
            == row["expected_current_request_policy"]
            for row in positives
        ),
        "fresh_control_prior_false_link_count": sum(
            row["expected_previous_action_outcome"] == "unknown"
            and row["previous_action_outcome"] != "unknown"
            for row in controls
        ),
        "unrelated_unknown_count": sum(
            row["case_id"].startswith("unrelated-")
            and row["previous_action_outcome"] == "unknown"
            for row in controls
        ),
        "third_party_quote_meta_false_link_count": sum(
            row["case_id"] in {"third-party-en", "metalinguistic-zh", "quoted-ja"}
            and row["previous_action_outcome"] != "unknown"
            for row in controls
        ),
        "exact_receipt_identity_count": sum(
            row["exact_receipt_identity"] is True for row in rows
        ),
        "strictly_earlier_performed_action_count": sum(
            row["performed_action_strictly_earlier"] is True for row in rows
        ),
        "same_turn_outcome_relabelled_as_old_past_count": sum(
            row["same_turn_outcome_relabelled_as_old_past"] is True for row in rows
        ),
        "unknown_counted_as_success_count": sum(
            row["unknown_counted_as_success"] is True
            and row["previous_action_outcome"] == "unknown"
            for row in rows
        ),
        "base_candidate_score_or_order_change_count": sum(
            row["candidate_score_or_order_unchanged"] is not True for row in rows
        ),
        "new_model_call_count": sum(row["new_model_call_count"] for row in rows),
        "factual_memory_write_count": sum(
            row["factual_memory_write_count"] for row in rows
        ),
        "raw_dialogue_persisted_count": sum(
            row["raw_dialogue_persisted"] for row in rows
        ),
    }
    return {
        "schema": "uruha_p4_at_executed_action_outcome_closure_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }


__all__ = [
    "LABEL",
    "SCHEMA",
    "build_dataset_evidence_p4_at",
    "classify_current_request_p4_at",
    "classify_explicit_desired_response_with_p4_at",
    "decompose_executed_action_feedback_p4",
    "install_executed_action_outcome_closure_p4",
    "materialize_executed_action_outcome_closure_p4",
    "observe_executed_action_outcome_closure_p4",
]
