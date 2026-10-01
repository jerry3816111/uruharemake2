"""Product-only authority for an observable request to stop interacting.

The frozen adaptive response vocabulary can listen, help, tease, care, share,
or clarify, but it cannot represent "leave me alone" as an action.  Treating
that explicit request as latent uncertainty creates another question and the
wrong pending prediction.  This adapter adds no mental-state inference: it
recognises a bounded current-turn response request, lets a short Japanese
acknowledgement-and-withdraw action pre-empt the legacy candidate, and keeps
the rejected proposal visible in trace evidence.
"""
from copy import deepcopy
import hashlib
import json
import re

import uruha_adaptive_person_model as adaptive
import uruha_counterfactual_pragmatic_branch_m34 as branch_m34


LABEL = "explicit_space_authority_p2"
SCHEMA = "uruha_explicit_space_authority_p2"
_INSTALLED = False
_ORIGINAL_BUILD_STATE = None
_ORIGINAL_APPLY_PLAN = None
_ORIGINAL_BUILD_MODE = None
_ORIGINAL_BRANCH_AUDIT = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_CLAUSE_START = r"(?:^|(?<=[。！？!?；;，,、\n]))\s*"
_POSITIVE_PATTERNS = {
    "zh": (
        _CLAUSE_START
        + r"(?:(?:不對|不对|不是|不|但|但是|現在|现在|今天)\s*[，,、]?\s*){0,3}"
          r"(?:請|请)?\s*(?:讓|让|給|给)我(?:先|暫時|暂时)?\s*(?:一個人|一个人)"
          r"(?:待著|待着|待一會|待一会|靜一靜|静一静)?",
        _CLAUSE_START
        + r"(?:(?:不對|不对|不是|不|但|但是|現在|现在|今天)\s*[，,、]?\s*){0,3}"
          r"(?:我)?(?:想|要|需要)(?:先|暫時|暂时)?\s*(?:一個人|一个人)"
          r"(?:待著|待着|待一會|待一会|靜一靜|静一静)",
        _CLAUSE_START
        + r"(?:(?:不對|不对|不是|不|但|但是|現在|现在|今天)\s*[，,、]?\s*){0,3}"
          r"(?:先)?(?:別|别)(?:理我|跟我說話|跟我说话)",
        _CLAUSE_START
        + r"(?:(?:不對|不对|不是|不|但|但是|現在|现在|今天)\s*[，,、]?\s*){0,3}"
          r"(?:讓|让)我(?:先)?(?:靜一靜|静一静)",
    ),
    "en": (
        _CLAUSE_START
        + r"(?:(?:no|not that|that's not it|but|today|right now|for now)\s*[,;:]?\s*){0,3}"
          r"(?:(?:please|just)\s+)?leave\s+me\s+alone\b",
        _CLAUSE_START
        + r"(?:(?:no|not that|that's not it|but|today|right now|for now)\s*[,;:]?\s*){0,3}"
          r"i\s+(?:want|need|would\s+rather)\s+(?:to\s+be\s+alone|some\s+space)\b",
        _CLAUSE_START
        + r"(?:(?:no|not that|that's not it|but|today|right now|for now)\s*[,;:]?\s*){0,3}"
          r"(?:please\s+)?give\s+me\s+some\s+space\b",
        _CLAUSE_START
        + r"(?:(?:no|not that|that's not it|but|today|right now|for now)\s*[,;:]?\s*){0,3}"
          r"(?:please\s+)?(?:don't|do\s+not)\s+talk\s+to\s+me\b",
    ),
    "ja": (
        _CLAUSE_START
        + r"(?:(?:違う|いや|そうじゃない|でも|今日は|今は)\s*[、,]?\s*){0,3}"
          r"(?:今日は|今は|しばらく)?\s*(?:一人|ひとり)にして(?:ほしい|くれ|ください)?",
        _CLAUSE_START
        + r"(?:(?:違う|いや|そうじゃない|でも|今日は|今は)\s*[、,]?\s*){0,3}"
          r"(?:今日は|今は|しばらく)?\s*(?:一人|ひとり)で(?:いたい|居たい)",
        _CLAUSE_START
        + r"(?:(?:違う|いや|そうじゃない|でも|今日は|今は)\s*[、,]?\s*){0,3}"
          r"(?:今日は|今は|しばらく)?\s*(?:放っておいて|ほっといて|そっとしておいて)",
    ),
}

_NEGATED = re.compile(
    r"(?:"
    r"(?:不想|不要|不需要)(?:先|暫時|暂时)?\s*(?:一個人|一个人)"
    r"|(?:一個人|一个人).{0,5}(?:不想|不要|不需要)"
    r"|\b(?:do\s+not|don't)\s+(?:want|need)\s+(?:to\s+be\s+alone|space)\b"
    r"|\bi\s+(?:do\s+not|don't)\s+want\s+you\s+to\s+leave\b"
    r"|(?:一人|ひとり)に(?:なりたくない|してほしくない)"
    r"|(?:一人|ひとり)で(?:いたくない|居たくない)"
    r")",
    re.I,
)
_METALINGUISTIC = re.compile(
    r"(?:怎麼翻|怎么翻|什麼意思|什么意思|どういう意味|何て意味|translate|translation|what\s+does.+mean)",
    re.I,
)
_THIRD_PARTY_ATTRIBUTION = re.compile(
    r"(?:"
    r"(?:他|她|朋友|同事|室友).{0,12}(?:說|说|表示|叫我)"
    r"|(?:he|she|they|my\s+(?:friend|coworker|roommate)).{0,18}\b(?:said|told|asked)\b"
    r"|(?:彼|彼女|友達|同僚|ルームメイト).{0,14}(?:言った|言われた|頼んだ)"
    r")",
    re.I,
)
_CORRECTION = re.compile(
    r"^\s*(?:不對|不对|不是|不[，,、]|違う|いや[、,]|そうじゃない|no\b|not\s+that\b|that's\s+not\s+it\b)",
    re.I,
)
_TODAY = re.compile(r"(?:今天|今日|今日は|きょうは|\btoday\b)", re.I)
_NOW = re.compile(r"(?:現在|现在|今は|今だけ|しばらく|暫時|暂时|先|\bright\s+now\b|\bfor\s+now\b|\ba\s+while\b)", re.I)
_PROTECTED_ROUTE_TYPES = {"safety_sensitive", "factual_or_memory", "deliberation"}


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _candidate_evidence(text):
    rows = []
    for language, patterns in _POSITIVE_PATTERNS.items():
        for index, pattern in enumerate(patterns, start=1):
            for match in re.finditer(pattern, text, re.I):
                rows.append(
                    {
                        "language": language,
                        "cue_id": f"respect_space:{language}:p2:{index}",
                        "start": match.start(),
                        "end": match.end(),
                        "length": match.end() - match.start(),
                        "span_digest": _digest(match.group(0)),
                    }
                )
    return sorted(rows, key=lambda row: (row["end"], row["length"]))


def classify_explicit_space_request_p2(user_input):
    """Classify a current observable response request without inferring cause."""
    text = str(user_input or "")
    rows = _candidate_evidence(text)
    blocked_reason = None
    if rows and _NEGATED.search(text):
        blocked_reason = "negated_space_request"
    elif rows and _METALINGUISTIC.search(text):
        blocked_reason = "metalinguistic_or_translation_context"
    elif rows and _THIRD_PARTY_ATTRIBUTION.search(text):
        blocked_reason = "third_party_attribution"
    if not rows or blocked_reason:
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": blocked_reason or "no_explicit_space_request",
            "candidate_count": len(rows),
            "input_digest": _digest(text),
            "model_call_added": False,
            "fact_memory_write_count": 0,
            "raw_dialogue_persisted": False,
        }

    decisive = rows[-1]
    correction = bool(_CORRECTION.search(text[: decisive["end"]]))
    temporal_scope = "today" if _TODAY.search(text) else "now" if _NOW.search(text) else "unspecified"
    if temporal_scope == "today":
        action_core = "あ、そっちか。分かった。今日は一人にしとく。" if correction else "分かった。今日は一人にしとく。"
    elif temporal_scope == "now":
        action_core = "あ、そっちか。分かった。今は一人にしとく。" if correction else "分かった。今は一人にしとく。"
    else:
        action_core = "あ、そっちか。分かった。しばらく一人にしとく。" if correction else "分かった。しばらく一人にしとく。"
    return {
        "schema": SCHEMA,
        "status": "selected_observable_explicit_space_request",
        "selected": True,
        "reason": "current_text_directly_requests_interaction_withdrawal",
        "action": "respect_space",
        "language": decisive["language"],
        "cue_id": decisive["cue_id"],
        "span_start": decisive["start"],
        "span_end": decisive["end"],
        "span_length": decisive["length"],
        "span_digest": decisive["span_digest"],
        "input_digest": _digest(text),
        "correction_observed": correction,
        "temporal_scope": temporal_scope,
        "selected_core_jp": action_core,
        "selected_core_sha256": _digest(action_core),
        "epistemic_status": "known_observable_response_request",
        "private_emotion_or_cause_inferred": False,
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": "current observable interaction request only; not emotion, cause, enduring preference, or private-state truth",
    }


def build_current_state_with_space_p2(*args, **kwargs):
    state = _ORIGINAL_BUILD_STATE(*args, **kwargs)
    user_input = args[0] if args else kwargs.get("user_input")
    state = deepcopy(state)
    state[LABEL] = classify_explicit_space_request_p2(user_input)
    return state


def _protected_plan(plan):
    route = str((((plan or {}).get("semantic_route_m22") or {}).get("selected_type")) or "")
    intent = str((plan or {}).get("intent") or "")
    scene = str((plan or {}).get("scene") or "")
    return bool(
        route in _PROTECTED_ROUTE_TYPES
        or intent in {"safety_boundary", "identity_answer", "memory_recall"}
        or scene in {"safety", "boundary"}
        or (plan or {}).get("memory_recall_contract")
        or (plan or {}).get("profile_grounding_shadow")
    )


def apply_decision_to_plan_with_space_p2(plan, decision):
    adjusted, legacy_trace = _ORIGINAL_APPLY_PLAN(plan, decision)
    contract = deepcopy((((decision or {}).get("state") or {}).get(LABEL)) or {})
    if not contract.get("selected") or _protected_plan(plan):
        return adjusted, legacy_trace

    legacy_selected = deepcopy((decision or {}).get("selected") or {})
    audit = {
        **contract,
        "status": "selected_explicit_space_action",
        "legacy_candidate_policy": legacy_selected.get("policy_id"),
        "legacy_candidate_core_sha256": _digest(legacy_selected.get("core_message_jp")),
        "legacy_plan_application_sha256": _digest(legacy_trace),
        "legacy_pending_prediction_suppressed": True,
        "selected_action": "acknowledge_and_withdraw",
        "visible_surface_status": "pending",
    }
    logic = deepcopy(adjusted)
    logic.update(
        intent="respect_space",
        scene="casual",
        hidden_intent="honor_observable_current_interaction_request",
        reply_goal="明示された距離の要求を短く認め、追加質問をせず会話を止める",
        core_message_jp=contract["selected_core_jp"],
        response_mode="respect_space",
        surface_act="acknowledge_and_withdraw",
        dialogue_act="accept_current_space_request",
        payload_level="short",
    )
    suppressed_application = {
        **deepcopy(legacy_trace or {}),
        "applied": False,
        "reason": "observable_explicit_space_action_preempts_legacy_latent_candidate",
        "legacy_candidate_policy": legacy_selected.get("policy_id"),
        "explicit_space_authority_p2": True,
        "raw_dialogue_persisted": False,
    }
    for suffix in ("m16", "m17", "m18"):
        logic[f"adaptive_person_model_{suffix}"] = deepcopy(suppressed_application)
        logic[f"desired_response_policy_{suffix}"] = None
    logic[LABEL] = audit
    return logic, suppressed_application


def build_desired_response_mode_with_space_p2(task_shape, state, decision):
    contract = _ORIGINAL_BUILD_MODE(task_shape, state, decision)
    space = deepcopy((state or {}).get(LABEL) or {})
    selected_type = str((task_shape or {}).get("selected_type") or "")
    if not space.get("selected") or selected_type in _PROTECTED_ROUTE_TYPES:
        return contract
    return {
        **deepcopy(contract),
        "eligible": False,
        "status": "preempted_by_explicit_space_authority_p2",
        "reason": "observable_current_response_request_outranks_latent_response_mode",
        "selected_mode": None,
        "selected_policy": None,
        "surface_required": False,
        "surface_status": "not_applicable",
        "legacy_selected_mode": contract.get("selected_mode"),
        "legacy_selected_policy": contract.get("selected_policy"),
        LABEL: {
            "schema": SCHEMA,
            "status": "selected_explicit_space_action",
            "selected_core_sha256": space.get("selected_core_sha256"),
            "raw_dialogue_persisted": False,
        },
    }


def audit_branch_surface_with_space_p2(reply, logic, branch_ledger):
    audited = _ORIGINAL_BRANCH_AUDIT(reply, logic, branch_ledger)
    space = deepcopy((logic or {}).get(LABEL) or {})
    if space.get("status") != "selected_explicit_space_action":
        return audited
    legacy = deepcopy(audited.get("surface_audit_m34") or {})
    audited["surface_status"] = "preempted_by_explicit_space_authority_p2"
    audited["surface_audit_m34"] = {
        "schema": branch_m34.BRANCH_SURFACE_SCHEMA_M34,
        "status": "preempted_by_explicit_space_authority_p2",
        "legacy_surface_audit": legacy,
        "selected_product_action": "respect_space",
        "reply_digest": _digest(reply),
        "raw_reply_persisted": False,
    }
    return audited


def visible_guard_with_space_p2(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self,
        reply,
        logic_data,
        user_input=user_input,
        memory_data=memory_data,
    )
    audit = deepcopy((logic_data or {}).get(LABEL) or {})
    if audit.get("status") != "selected_explicit_space_action":
        return visible

    selected = str(audit.get("selected_core_jp") or "").strip()
    before = str(visible or "").strip()
    visible = selected or before
    audit.update(
        visible_surface_status="matched" if visible == selected and selected else "mismatch",
        pre_authority_surface_sha256=_digest(before),
        final_visible_surface_jp=visible,
        final_visible_surface_sha256=_digest(visible),
        final_visible_surface_matches_selected_action=bool(selected and visible == selected),
        visible_surface_changed=visible != before,
    )
    logic_data[LABEL] = audit
    m39 = deepcopy(logic_data.get("semantic_persona_surface_verifier_m39") or {})
    if m39:
        m39.update(
            effective_after_explicit_space_authority_p2=False,
            downstream_authority=LABEL,
            pre_authority_status=m39.get("status"),
        )
        logic_data["semantic_persona_surface_verifier_m39"] = m39
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        explicit_space_authority_p2=True,
        explicit_space_surface_status=audit["visible_surface_status"],
    )
    logic_data["visible_language_guard"] = language_guard
    return visible


def materialize_explicit_space_authority_p2(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("status") == "selected_explicit_space_action":
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(
            visible_surface_status=(
                "matched"
                if final and final == payload.get("selected_core_jp")
                else "mismatch"
            ),
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_selected_action=bool(
                final and final == payload.get("selected_core_jp")
            ),
            flow=[
                "observable_explicit_space_request",
                "legacy_candidate_proposal",
                "current_request_authority",
                "acknowledge_and_withdraw",
                "visible_japanese_surface",
            ],
        )
        logic[LABEL] = deepcopy(payload)
        index = next(
            (i for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
            next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(
            index,
            {
                "stage": "select",
                "label": LABEL,
                "payload": deepcopy(payload),
                "salience": 1.0,
            },
        )
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_explicit_space_authority_p2():
    global _INSTALLED, _ORIGINAL_BUILD_STATE, _ORIGINAL_APPLY_PLAN
    global _ORIGINAL_BUILD_MODE, _ORIGINAL_BRANCH_AUDIT, _ORIGINAL_VISIBLE_GUARD
    global _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False

    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_BUILD_STATE = adaptive.build_current_state
    _ORIGINAL_APPLY_PLAN = adaptive.apply_decision_to_plan
    _ORIGINAL_BUILD_MODE = adaptive.build_desired_response_mode_contract
    _ORIGINAL_BRANCH_AUDIT = branch_m34.audit_pragmatic_branch_surface_m34
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready

    adaptive.build_current_state = build_current_state_with_space_p2
    adaptive.apply_decision_to_plan = apply_decision_to_plan_with_space_p2
    adaptive.build_desired_response_mode_contract = build_desired_response_mode_with_space_p2
    branch_m34.audit_pragmatic_branch_surface_m34 = audit_branch_surface_with_space_p2
    RightBrain.enforce_user_visible_japanese = visible_guard_with_space_p2

    def finish(self, result):
        materialize_explicit_space_authority_p2(result)
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


__all__ = [
    "LABEL",
    "SCHEMA",
    "apply_decision_to_plan_with_space_p2",
    "classify_explicit_space_request_p2",
    "install_explicit_space_authority_p2",
    "materialize_explicit_space_authority_p2",
]
