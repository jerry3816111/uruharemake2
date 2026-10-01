"""Bounded current-turn authority for an explicit shared-amusement request.

This product adapter covers one observable response request: the user says
that they are not asking for help / are not troubled and explicitly asks the
listener to share the laugh.  It does not infer humor from an isolated
``laugh`` command, quoted text, an avatar expression command, or a report
about another person.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata


LABEL = "shared_amusement_authority_p3"
SCHEMA = "uruha_shared_amusement_authority_p3"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_NO_SOLVE_PATTERNS = {
    "zh": re.compile(
        r"(?:不用|不需要)(?:你)?(?:幫忙|帮忙|建議|建议|解決|解决)|"
        r"(?:不是|並不是|并不是)(?:要|想要)(?:你)?(?:給|给)?(?:幫忙|帮忙|建議|建议|解決|解决)|"
        r"(?:沒|没|沒有|没有)(?:在)?(?:困擾|困扰|問題|问题)|(?:沒事|没事)"
    ),
    "en": re.compile(
        r"\b(?:i(?:'m| am)\s+not\s+(?:asking\s+(?:you\s+)?for\s+help|"
        r"looking\s+for\s+(?:help|advice|a\s+solution)|upset|bothered)|"
        r"i\s+do(?:n't| not)\s+need\s+(?:help|advice|a\s+solution)|"
        r"nothing(?:'s|\s+is)\s+wrong|it(?:'s|\s+is)\s+not\s+a\s+problem)\b",
        re.I,
    ),
    "ja": re.compile(
        r"(?:別に)?困って(?:い)?ない|助け(?:は|なんて)?いらない|"
        r"解決してほしいわけじゃない|別に問題(?:は)?ない|"
        r"(?:アドバイス|助言)(?:は|なんて)?いらない"
    ),
}

_SHARED_AMUSEMENT_PATTERNS = {
    "zh": re.compile(
        r"(?:只是|只|就)?(?:想|希望)(?:要)?(?:讓|让)?你(?:陪我|跟我|和我)?(?:一起)?笑(?:一下)?|"
        r"(?:陪我|跟我|和我)一起笑|你笑(?:一下)?就好"
    ),
    "en": re.compile(
        r"\b(?:i\s+just\s+wanted\s+you\s+to\s+laugh|"
        r"all\s+i\s+wanted\s+was\s+for\s+you\s+to\s+laugh|"
        r"(?:just\s+)?laugh(?:\s+at\s+it)?\s+with\s+me)\b",
        re.I,
    ),
    "ja": re.compile(
        r"(?:ただ)?笑ってほしかった(?:だけ)?|(?:ただ)?笑ってほしい(?:だけ)?|"
        r"一緒に笑って(?:ほしい)?|笑ってくれ(?:たら|れば)(?:それで)?(?:いい|よかった)|"
        r"笑ってくれるだけで(?:いい|よかった)"
    ),
}

_METALINGUISTIC_OR_QUOTED = re.compile(
    r"(?:引用|台本|脚本|例文|翻譯|翻译|どういう意味|意味は|"
    r"\b(?:quote|quoted|script|example|translate|translation)\b|"
    r"(?:って|と)(?:書いて|書かれて|言う例))",
    re.I,
)

_THIRD_PERSON_REPORT = re.compile(
    r"(?:彼|彼女|友達|友人|あの人)(?:は|が).{0,48}(?:困って(?:い)?ない|笑ってほし)|"
    r"(?:他|她|朋友)(?:說|说|表示|其實|其实|只是).{0,48}(?:不需要|沒困擾|没困扰|想讓你笑|想让你笑)|"
    r"\b(?:he|she|they|my\s+friend)\s+(?:isn't|wasn't|is\s+not|was\s+not|"
    r"just\s+wanted).{0,48}(?:help|troubled|laugh)\b",
    re.I,
)

_ACTION_OR_AVATAR = re.compile(
    r"(?:VRM|avatar|expression|アバター|モデル|表情|表情指令|動作指令|动作指令|"
    r"角色模型|キャラモデル).{0,40}(?:笑|laugh|smile)|"
    r"(?:笑|laugh|smile).{0,40}(?:VRM|avatar|expression|アバター|モデル|表情)",
    re.I,
)

_NEGATED_AMUSEMENT = re.compile(
    r"(?:笑ってほしくない|一緒に笑わないで|不要(?:陪我|跟我|和我)?笑|"
    r"別笑|don't\s+laugh|do\s+not\s+laugh|not\s+want\s+you\s+to\s+laugh)",
    re.I,
)

_PROTECTED_RISK = re.compile(
    r"(?:死にたい|自殺したい|消えたい|不想活|想死|自殺|自杀|"
    r"kill\s+myself|hurt\s+myself|want\s+to\s+die|end\s+my\s+life)",
    re.I,
)

_SELECTED_CORE_JP = "あー、そっちね。解決じゃなくて一緒に笑ってほしかったのか。なにそれ、ちょっと笑う。"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalized(value):
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def classify_shared_amusement_authority_p3(user_input):
    """Classify only the explicit two-clause act and retain no raw dialogue."""
    text = _normalized(user_input)
    input_digest = _digest(text)
    blocked_reason = ""
    if _PROTECTED_RISK.search(text):
        blocked_reason = "protected_risk_cue"
    elif _METALINGUISTIC_OR_QUOTED.search(text):
        blocked_reason = "metalinguistic_or_quoted_context"
    elif _THIRD_PERSON_REPORT.search(text):
        blocked_reason = "third_person_report"
    elif _ACTION_OR_AVATAR.search(text):
        blocked_reason = "action_or_avatar_expression_command"
    elif _NEGATED_AMUSEMENT.search(text):
        blocked_reason = "shared_amusement_negated"
    if blocked_reason:
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": blocked_reason,
            "input_digest": input_digest,
            "raw_dialogue_persisted": False,
        }

    no_solve = [
        language
        for language, pattern in _NO_SOLVE_PATTERNS.items()
        if pattern.search(text)
    ]
    amusement = [
        language
        for language, pattern in _SHARED_AMUSEMENT_PATTERNS.items()
        if pattern.search(text)
    ]
    if not no_solve or not amusement:
        missing = []
        if not no_solve:
            missing.append("explicit_no_solve_clause")
        if not amusement:
            missing.append("direct_shared_amusement_clause")
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": "required_clause_missing",
            "missing": missing,
            "input_digest": input_digest,
            "raw_dialogue_persisted": False,
        }

    language = amusement[0] if amusement[0] in no_solve else no_solve[0]
    return {
        "schema": SCHEMA,
        "status": "explicit_shared_amusement_authorized",
        "selected": True,
        "language": language,
        "observable_cues": [
            "explicit_no_solve_or_no_trouble",
            "direct_shared_amusement_request",
        ],
        "authority": "current_explicit_desired_response",
        "surface_authority": True,
        "input_digest": input_digest,
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "explicit current-turn request for shared amusement after rejecting "
            "problem-solving; not inferred humor preference or private state"
        ),
    }


def build_shared_amusement_contract_p3(user_input):
    contract = classify_shared_amusement_authority_p3(user_input)
    if not contract.get("selected"):
        return contract
    return {
        **contract,
        "selected_core_jp": _SELECTED_CORE_JP,
        "selected_core_sha256": _digest(_SELECTED_CORE_JP),
        "response_mode": "shared_amusement",
        "must_not": [
            "ask_follow_up_question",
            "offer_problem_solving",
            "continue_previous_problem",
            "invent_event_details",
        ],
    }


def _plan_from_contract(contract):
    return {
        "candidate_label": "p3_shared_amusement",
        "intent": "emotional_bid",
        "mood_impact": 1,
        "trust_impact": 1,
        "scene": "casual",
        "listener_state": "解決ではなく、一緒に笑う反応を明示的に求めている",
        "reply_goal": "追問や助言を止め、短く笑いを共有する",
        "jp_summary": "ユーザーが問題解決を否定し、共同の笑いを直接求めた。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.06,
        "premise_check": "accept",
        "self_check": True,
        "subjective_note_jp": "明示された返され方だけを当輪で優先する",
        "hidden_intent": "emotional_bid",
        "user_belief": "解決ではなく反応を共有してほしいと伝えている。",
        "my_hidden_knowledge": "出来事の詳細は推測せず、笑いだけ共有する。",
        "user_expectation": "追問せず一緒に笑う短い返答。",
        "surface_act": "plain_reply",
        "payload_level": "low",
        "shared_amusement_contract_p3": deepcopy(contract),
        "planner_path": "explicit_shared_amusement_authority_p3",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 3,
            "max_chars": 52,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["？", "?", "手伝う", "解決策", "詳しく", "AI"],
    }


def rule_plan_with_shared_amusement_p3(self, user_input, current_psyche, memory_data=None):
    contract = build_shared_amusement_contract_p3(user_input)
    if contract.get("selected") and contract.get("surface_authority"):
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def visible_guard_with_shared_amusement_p3(
    self,
    reply,
    logic_data,
    user_input="",
    memory_data=None,
):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self,
        reply,
        logic_data,
        user_input=user_input,
        memory_data=memory_data,
    )
    contract = build_shared_amusement_contract_p3(user_input)
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    if not contract.get("selected") or route == "safety_sensitive":
        return visible

    selected = str(contract.get("selected_core_jp") or "").strip()
    before = str(visible or "").strip()
    visible = selected or before
    contract.update(
        visible_surface_status="matched" if selected and visible == selected else "mismatch",
        pre_authority_surface_sha256=_digest(before),
        final_visible_surface_jp=visible,
        final_visible_surface_sha256=_digest(visible),
        final_visible_surface_matches_contract=bool(selected and visible == selected),
        visible_surface_changed=visible != before,
    )
    logic_data["shared_amusement_contract_p3"] = deepcopy(contract)

    explicit = deepcopy(logic_data.get("explicit_desired_response_m25") or {})
    explicit[LABEL] = {
        "status": contract["status"],
        "authority": contract["authority"],
        "surface_required": True,
        "surface_status": contract["visible_surface_status"],
        "raw_dialogue_persisted": False,
    }
    logic_data["explicit_desired_response_m25"] = explicit
    desired_mode = deepcopy(logic_data.get("desired_response_mode_m23") or {})
    desired_mode[LABEL] = {
        "selected_mode": "shared_amusement",
        "source": "current_explicit_desired_response",
        "surface_authority": True,
        "raw_dialogue_persisted": False,
    }
    logic_data["desired_response_mode_m23"] = desired_mode

    persona_guard = deepcopy(logic_data.get("semantic_persona_surface_verifier_m39") or {})
    if persona_guard:
        persona_guard.update(
            effective_after_shared_amusement_authority_p3=False,
            downstream_authority=LABEL,
            pre_authority_status=persona_guard.get("status"),
        )
        logic_data["semantic_persona_surface_verifier_m39"] = persona_guard
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        shared_amusement_authority_p3=True,
        shared_amusement_surface_status=contract["visible_surface_status"],
    )
    logic_data["visible_language_guard"] = language_guard
    return visible


def materialize_shared_amusement_p3(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get("shared_amusement_contract_p3") or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(
            visible_surface_status=(
                "matched" if final and final == payload.get("selected_core_jp") else "mismatch"
            ),
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=bool(
                final and final == payload.get("selected_core_jp")
            ),
            flow=[
                "explicit_no_solve_or_no_trouble",
                "direct_shared_amusement_request",
                "current_turn_response_authority",
                "bounded_japanese_shared_laugh",
            ],
        )
        logic["shared_amusement_contract_p3"] = deepcopy(payload)
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


def install_shared_amusement_authority_p3():
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD
    global _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready

    LeftBrain._rule_based_plan = rule_plan_with_shared_amusement_p3
    RightBrain.enforce_user_visible_japanese = visible_guard_with_shared_amusement_p3

    def finish(self, result):
        materialize_shared_amusement_p3(result)
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
