"""Opt-in boundary between a quoted line and the user's current editing act.

This is a bounded text-scope contract, not a general pragmatic parser.  One
balanced quote is an object of evaluation only when the outside text clearly
asks about wording.  The same certificate binds routing, the selected plan,
memory-anchor admission, the visible Japanese answer, and the debug graph.
No retrieval ranking or persistent memory is changed.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata

import uruha_adaptive_person_model as adaptive_person


LABEL = "quoted_line_act_scope_p4"
SCHEMA = "uruha_quoted_line_act_scope_p4"
PLANNER_PATH = "quoted_line_act_scope_p4"
_INSTALLED = False
_ORIGINAL_QUERY = None
_ORIGINAL_ROUTE = None
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_GRAVITY = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_TICK = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_QUOTED_PREFIX = re.compile(
    r'^(?:「(?P<corner>[^「」『』"\n]{1,80})」|'
    r'『(?P<double>[^「」『』"\n]{1,80})』|'
    r'"(?P<ascii>[^"\n]{1,80})")(?P<outer>.+)$',
    re.S,
)
_META_NOUN = re.compile(r"台詞|セリフ|言い方|一文|句話|句话|句子|說法|说法|\b(?:line|sentence|wording|phrase)\b", re.I)
_EDIT_QUESTION = re.compile(
    r"自然|変(?:かな|じゃ|だ|\?)|不自然|重すぎ|重い|急すぎ|短く|短い|"
    r"太重|太直接|自然嗎|自然吗|簡短|简短|縮短|缩短|"
    r"\b(?:natural|awkward|too heavy|too direct|shorter|shorten)\b",
    re.I,
)
_OUTER_EDIT_GRAMMARS = (
    re.compile(
        r"^(?:って|という|は)?(?:台詞|セリフ|言い方|一文)[、,]?"
        r"(?:口語として)?(?:自然(?:かな|に聞こえる)?|変(?:かな|じゃない)?|"
        r"不自然(?:かな)?|重すぎる|重い|急すぎる|短くできる|短い)\?$"
    ),
    re.compile(
        r"^(?:這|这)(?:句話|句话|句子)(?:會不會|会不会)?"
        r"(?:自然嗎|自然吗|太重|太直接|太長|太长|能簡短一點嗎|能简短一点吗)\?$"
    ),
    re.compile(
        r"^as a (?:line|sentence|phrase), (?:does it sound "
        r"(?:natural|awkward|too heavy|too direct)|can it be shorter)\?$",
        re.I,
    ),
)
_OUTER_DIRECT_ACT = re.compile(
    r"覚えて|思い出|記憶|前に言った|さっき言った|まだ覚え|"
    r"\b(?:remember|recall|do you|can you check|please check)\b|"
    r"你還記得|你还记得|還記得我|还记得我|你喜歡|你喜欢|"
    r"送って|送信|読み上げ|読んで|そのまま言って|代わりに言って|"
    r"実行|開いて|傳給|传给|發送|发送|唸出|念出|"
    r"\b(?:send|post|read it|say it|call)\b",
    re.I,
)
_PROTECTED = re.compile(
    r"死にたい|自殺|自傷|殺す|助けて|緊急|救急|パスワード|暗証番号|"
    r"住所|電話番号|個人情報|password|passcode|secret|suicide|self.harm|"
    r"想死|自殺|自杀|傷害自己|伤害自己|密碼|密码",
    re.I,
)
_UNKNOWN_CORE = "その台詞の言い方の相談だよな。前後の場面も教えて。"
_MINIMAL_FALLBACK = "うん、もう少し聞かせて。"
_CORES = {
    "naturalness": "変ではないけど、前後の流れによっては少し唐突に聞こえるかも。",
    "tone": "少し重く聞こえるかも。相手との距離感次第だな。",
    "shorten": "短くするなら、分かりきった部分を省く。どこまで削れるかは前後次第だな。",
}


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def classify_quoted_line_act_scope_p4(user_input: str) -> dict:
    """Authorize only one explicit, outer metalinguistic question."""
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    base = {
        "schema": SCHEMA,
        "input_sha256": _sha(text),
        "eligible": False,
        "status": "not_applicable",
        "model_call_added": False,
        "profile_write_count": 0,
        "fact_write_count": 0,
        "claim_boundary": "bounded quote/outer-act scope, not open-domain intent inference",
    }
    if not text or len(text) > 200 or _PROTECTED.search(text):
        return {**base, "reason": "empty_long_or_protected"}
    match = _QUOTED_PREFIX.fullmatch(text)
    if not match:
        return {**base, "reason": "not_one_balanced_initial_quote"}
    quote = next((value for value in (match.group("corner"), match.group("double"), match.group("ascii")) if value is not None), "")
    outer = match.group("outer").strip()
    if (
        not quote.strip()
        or any(mark in outer for mark in "「」『』\"")
        or any(mark in quote for mark in "「」『』\"")
        or not outer.endswith("?")
        or outer.count("?") != 1
        or outer.count("、") > 1
        or outer.count(",") > 1
        or "。" in outer
        or _OUTER_DIRECT_ACT.search(outer)
        or not _META_NOUN.search(outer)
        or not _EDIT_QUESTION.search(outer)
        or not any(grammar.fullmatch(outer) for grammar in _OUTER_EDIT_GRAMMARS)
    ):
        return {**base, "reason": "outer_act_not_single_explicit_edit_question"}
    if re.search(r"短く|短い|簡短|简短|縮短|缩短|\b(?:shorter|shorten)\b", outer, re.I):
        outer_act = "shorten"
    elif re.search(r"重すぎ|重い|急すぎ|太重|太直接|\b(?:too heavy|too direct)\b", outer, re.I):
        outer_act = "tone"
    else:
        outer_act = "naturalness"
    core = _CORES[outer_act]
    return {
        **base,
        "eligible": True,
        "status": "outer_edit_question_selected",
        "reason": "balanced_quote_with_single_explicit_outer_edit_question",
        "quote_role": "object_of_evaluation_not_current_request",
        "outer_act": outer_act,
        "quoted_span_start": 0,
        "quoted_span_end": match.start("outer"),
        "quoted_span_sha256": _sha(quote),
        "outer_span_sha256": _sha(outer),
        "quoted_memory_or_relationship_cue_authorized": False,
        "prior_memory_anchor_answer_authorized": False,
        "selected_core_jp": core,
        "selected_core_sha256": _sha(core),
    }


def _bound_scope_matches(bound: dict, fresh: dict) -> bool:
    return bool(
        fresh.get("eligible")
        and bound.get("schema") == SCHEMA
        and all(
            bound.get(key) == fresh.get(key)
            for key in ("input_sha256", "quoted_span_sha256", "outer_span_sha256", "outer_act")
        )
    )


def query_all_layers_with_quoted_line_act_scope_p4(self, text: str) -> dict:
    memory_data = _ORIGINAL_QUERY(self, text)
    if isinstance(memory_data, dict):
        scope = classify_quoted_line_act_scope_p4(text)
        if scope["eligible"]:
            memory_data[LABEL] = deepcopy(scope)
    return memory_data


def route_with_quoted_line_act_scope_p4(
    user_input, actual_signal=None, route_info=None,
    grounded_profile_logic=None, correction_directive=None,
):
    route = _ORIGINAL_ROUTE(
        user_input, actual_signal=actual_signal, route_info=route_info,
        grounded_profile_logic=grounded_profile_logic,
        correction_directive=correction_directive,
    )
    scope = classify_quoted_line_act_scope_p4(user_input)
    seed = (actual_signal or {}).get("seed_plan") or {}
    protected_seed = (
        str(seed.get("intent") or "") in adaptive_person.PROTECTED_INTENTS
        or str(seed.get("scene") or "") in adaptive_person.PROTECTED_SCENES
    )
    if (
        not scope["eligible"]
        or not isinstance(route, dict)
        or route.get("selected_type") == "safety_sensitive"
        or protected_seed
        or (route_info or {}).get("route") == "low_road"
    ):
        return route
    previous = route.get("selected_type")
    route = deepcopy(route)
    route["pre_quote_scope_selected_type"] = previous
    route["selected_type"] = "general_conversation"
    route["recommended_route"] = "existing_guarded_router"
    route["confidence"] = 0.92
    route["decisive_evidence"] = ["bounded_outer_edit_question_p4"]
    route["scope_override"] = {"schema": SCHEMA, "outer_act": scope["outer_act"], "input_sha256": scope["input_sha256"]}
    route["evidence"] = [
        *(route.get("evidence") or []),
        {"task_type": "general_conversation", "cue_id": "bounded_outer_edit_question_p4", "source_kind": "opt_in_scope_certificate", "weight": 0.92, "epistemic_status": "routing_evidence_not_private_state_fact"},
    ]
    route["candidates"] = [
        {"task_type": "general_conversation", "score": 0.92},
        *[row for row in route.get("candidates") or [] if row.get("task_type") != "general_conversation"],
    ]
    route["alternatives"] = [row for row in route["candidates"] if row["task_type"] != "general_conversation"]
    route["overlap_types"] = [row["task_type"] for row in route["alternatives"]]
    return route


def _plan_from_scope(scope: dict) -> dict:
    core = scope["selected_core_jp"]
    return {
        "candidate_label": "p4_quoted_line_outer_edit",
        "intent": "quoted_line_feedback",
        "scene": "casual",
        "listener_state": "引用した台詞の言い方を気にしている",
        "reply_goal": "引用を実行せず、外側の編集相談に短く答える",
        "jp_summary": "ユーザーは引用した台詞の言い方を評価してほしい。",
        "core_message_jp": core,
        "mood_impact": 0,
        "trust_impact": 0,
        "cognitive_mode": "direct",
        "response_mode": "direct_answer_with_hedge",
        "uncertainty": 0.3,
        "premise_check": "accept",
        "self_check": True,
        "subjective_note_jp": "引用は対象テキストであり、今の依頼ではない",
        "hidden_intent": "edit_phrase_request",
        "surface_act": "plain_reply",
        "grounding": {"current_act": "quoted_line_edit_feedback"},
        "payload_level": "medium",
        "planner_path": PLANNER_PATH,
        "constraints": {
            "first_person": "うち", "sentence_count": 2, "max_chars": 44,
            "casual_japanese_only": True, "forbid_polite": True,
            "forbid_knowledge": True, "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "AI"],
    }


def rule_plan_with_quoted_line_act_scope_p4(self, user_input, current_psyche, memory_data=None):
    scope = classify_quoted_line_act_scope_p4(user_input)
    bound = (memory_data or {}).get(LABEL) or {}
    if not _bound_scope_matches(bound, scope):
        return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    predecessor = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    if (
        str((predecessor or {}).get("intent") or "") in adaptive_person.PROTECTED_INTENTS
        or str((predecessor or {}).get("scene") or "") in adaptive_person.PROTECTED_SCENES
    ):
        return predecessor
    return _plan_from_scope(scope)


def attach_memory_gravity_with_quoted_line_act_scope_p4(self, logic, user_input, memory_data):
    scope = (memory_data or {}).get(LABEL) or {}
    fresh = classify_quoted_line_act_scope_p4(user_input)
    if (
        not _bound_scope_matches(scope, fresh)
        or (logic or {}).get("intent") in adaptive_person.PROTECTED_INTENTS
        or (logic or {}).get("scene") in adaptive_person.PROTECTED_SCENES
    ):
        return _ORIGINAL_GRAVITY(self, logic, user_input, memory_data)
    logic.update({
        "memory_anchor": {}, "memory_relevance": 0.0,
        "memory_relevance_label": "none", "memory_speakability": "no_memory",
        "memory_speakability_reason": "quote_cue_not_current_recall",
        "memory_gravity": 0.0, "memory_use_expected": False,
        LABEL: {**deepcopy(scope), "memory_anchor_admission": "rejected_for_outer_edit_act"},
    })
    return logic


def cognitive_tick_with_quoted_line_act_scope_p4(self, event):
    """Bind the outer act after competing planners, before speech/writeback.

    Earlier M22/M31/personhood traces remain as pre-scope observations.  The
    selected-plan node is refreshed so it describes the plan actually handed
    to speech; the scope receipt explicitly records this late authority.
    """
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    user_input = str((event or {}).get("user_input") or "")
    bound = ((event or {}).get("memory_data") or {}).get(LABEL) or {}
    fresh = classify_quoted_line_act_scope_p4(user_input)
    logic = tick.get("logic") or {}
    route = logic.get("semantic_route_m22") or {}
    if (
        not _bound_scope_matches(bound, fresh)
        or (tick.get("route_info") or {}).get("route") == "low_road"
        or route.get("selected_type") != "general_conversation"
        or logic.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic.get("scene") in adaptive_person.PROTECTED_SCENES
        or getattr(self.right_brain, "_structured_surface_required", lambda: False)()
    ):
        return tick
    previous = {
        "intent": str(logic.get("intent") or ""),
        "planner_path": str(logic.get("planner_path") or ""),
        "core_sha256": _sha(logic.get("core_message_jp") or ""),
        "performed_route": str(route.get("performed_route") or ""),
    }
    for key, value in _plan_from_scope(fresh).items():
        logic[key] = deepcopy(value)
    logic.update({
        "memory_anchor": {}, "memory_relevance": 0.0,
        "memory_relevance_label": "none", "memory_speakability": "no_memory",
        "memory_speakability_reason": "quote_cue_not_current_recall",
        "memory_gravity": 0.0, "memory_use_expected": False,
        "user_belief": "引用した台詞の言い方を相談している。",
        "my_hidden_knowledge": "引述内の問いは今の依頼として実行しない。",
        "user_expectation": "外側の編集相談への短い返答。",
        "dialogue_act": "direct_chat_answer",
        LABEL: {
            **deepcopy(fresh),
            "selected_boundary_override": True,
            "pre_scope_selected_plan": previous,
            "memory_anchor_admission": "rejected_for_outer_edit_act",
            "pre_scope_cognitive_nodes_retained_as_shadow": True,
        },
    })
    route = deepcopy(route)
    route["post_scope_selected_plan_authority"] = LABEL
    logic["semantic_route_m22"] = route
    tick["logic"] = logic
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        runtime.last_selected_plan = self._plan_trace_summary(logic)
        runtime.active_goal = logic["reply_goal"]
        for row in runtime.blackboard:
            if row.get("label") == "selected_plan":
                row["payload"] = deepcopy(runtime.last_selected_plan)
            elif row.get("label") == "semantic_route_outcome_m22":
                row["payload"] = deepcopy(route)
    return tick


def _commit_visible(
    logic_data: dict, scope: dict, before: str, final: str, status: str,
    *, failure_reason: str = "", fallback_language_status: str = "not_applicable",
) -> str:
    receipt = deepcopy(scope)
    anchor_present = bool(logic_data.get("memory_anchor"))
    expected_memory = bool(logic_data.get("memory_use_expected"))
    receipt.update(
        selected_intent=str(logic_data.get("intent") or ""),
        selected_planner_path=str(logic_data.get("planner_path") or ""),
        memory_anchor_admission=(
            "rejected_for_outer_edit_act"
            if not anchor_present and not expected_memory
            else "anchor_present_or_expected_integrity_failure"
        ),
        observed_memory_anchor_present=anchor_present,
        observed_memory_use_expected=expected_memory,
        visible_surface_status=status,
        surface_failure_reason=failure_reason or None,
        fallback_language_status=fallback_language_status,
        pre_authority_surface_sha256=_sha(before),
        final_visible_surface_sha256=_sha(final),
        final_visible_surface_matches_contract=(
            status == "matched" and final == receipt.get("selected_core_jp")
        ),
    )
    logic_data[LABEL] = receipt
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    original_reply = str(guard.get("original_reply") or before)
    guard.update(
        changed=final != original_reply,
        pre_quote_scope_repair_action=guard.get("repair_action"),
        pre_quote_scope_rejection_reasons=deepcopy(guard.get("final_rejection_reasons") or []),
        repair_action="quoted_line_act_scope_" + status,
        final_rejection_reasons=[failure_reason] if failure_reason else [],
        final_reply=final,
        final_reply_sha256=_sha(final),
    )
    logic_data["visible_language_guard"] = guard
    model_selection = logic_data.get("model_surface_selection")
    if isinstance(model_selection, dict):
        model_selection["post_guard_visible_authority"] = LABEL
    return final


def _checked_fallback(self, logic_data: dict, user_input: str, memory_data: dict | None):
    checker = getattr(self, "_user_visible_language_rejection_reasons", None)
    if not callable(checker):
        return _UNKNOWN_CORE, "checker_unavailable"
    for candidate in (_UNKNOWN_CORE, _MINIMAL_FALLBACK):
        try:
            reasons = checker(
                candidate, user_input=user_input,
                logic_data=logic_data, memory_data=memory_data,
            )
        except Exception:
            return _MINIMAL_FALLBACK, "checker_exception"
        if not reasons:
            return candidate, "accepted"
    return _MINIMAL_FALLBACK, "both_fallbacks_rejected"


def visible_guard_with_quoted_line_act_scope_p4(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(self, reply, logic_data, user_input=user_input, memory_data=memory_data)
    if not isinstance(logic_data, dict):
        return visible
    scope = classify_quoted_line_act_scope_p4(user_input)
    if not scope["eligible"]:
        return visible
    route = str((logic_data.get("semantic_route_m22") or {}).get("selected_type") or "")
    if (
        route == "safety_sensitive"
        or logic_data.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic_data.get("scene") in adaptive_person.PROTECTED_SCENES
        or getattr(self, "_structured_surface_required", lambda: False)()
    ):
        return visible
    before = str(visible or "").strip()
    bound = (memory_data or {}).get(LABEL) or {}
    integrity = (
        _bound_scope_matches(bound, scope)
        and logic_data.get("planner_path") == PLANNER_PATH
        and logic_data.get("intent") == "quoted_line_feedback"
        and logic_data.get("surface_act") == "plain_reply"
        and logic_data.get("core_message_jp") == scope["selected_core_jp"]
        and route == "general_conversation"
        and not logic_data.get("memory_anchor")
        and logic_data.get("memory_use_expected") is False
    )
    if not integrity:
        failed = {**scope, "status": "surface_integrity_failed_closed"}
        fallback, fallback_status = _checked_fallback(self, logic_data, user_input, memory_data)
        return _commit_visible(
            logic_data, failed, before, fallback, "failed_closed",
            failure_reason="scope_plan_or_source_integrity_mismatch",
            fallback_language_status=fallback_status,
        )
    checker = getattr(self, "_user_visible_language_rejection_reasons", None)
    try:
        rejection = checker(scope["selected_core_jp"], user_input=user_input, logic_data=logic_data, memory_data=memory_data) if callable(checker) else ["checker_missing"]
    except Exception:
        rejection = ["checker_exception"]
    if rejection:
        failed = {**scope, "status": "surface_integrity_failed_closed"}
        fallback, fallback_status = _checked_fallback(self, logic_data, user_input, memory_data)
        return _commit_visible(
            logic_data, failed, before, fallback, "failed_closed",
            failure_reason="selected_core_language_guard_rejected",
            fallback_language_status=fallback_status,
        )
    return _commit_visible(logic_data, scope, before, scope["selected_core_jp"], "matched")


def materialize_quoted_line_act_scope_p4(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    scope = logic.get(LABEL) or {}
    trace = result.get("runtime_trace")
    if scope.get("schema") != SCHEMA or not isinstance(trace, dict):
        return result
    final = str(result.get("reply") or result.get("response") or "").strip()
    receipt = deepcopy(scope)
    receipt["final_visible_surface_sha256"] = _sha(final)
    receipt["final_visible_surface_matches_contract"] = (
        receipt.get("visible_surface_status") != "failed_closed"
        and final == receipt.get("selected_core_jp")
    )
    if receipt.get("visible_surface_status") != "failed_closed":
        receipt["visible_surface_status"] = "matched" if receipt["final_visible_surface_matches_contract"] else "mismatch"
    logic[LABEL] = receipt
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), len(rows))
    rows.insert(index, {"stage": "perceive", "label": LABEL, "payload": deepcopy(receipt), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(receipt)
    return result


def install_quoted_line_act_scope_p4() -> bool:
    """Install only after the prior P4 focus overlay in a new local entry."""
    global _INSTALLED, _ORIGINAL_QUERY, _ORIGINAL_ROUTE, _ORIGINAL_RULE_PLAN
    global _ORIGINAL_GRAVITY, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_TICK
    global _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_QUERY = MemoryManager.query_all_layers
    _ORIGINAL_ROUTE = UruhaBrainV4_Mac._classify_task_shape_m22
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_GRAVITY = UruhaBrainV4_Mac._attach_memory_gravity
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    MemoryManager.query_all_layers = query_all_layers_with_quoted_line_act_scope_p4
    UruhaBrainV4_Mac._classify_task_shape_m22 = staticmethod(route_with_quoted_line_act_scope_p4)
    LeftBrain._rule_based_plan = rule_plan_with_quoted_line_act_scope_p4
    UruhaBrainV4_Mac._attach_memory_gravity = attach_memory_gravity_with_quoted_line_act_scope_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_quoted_line_act_scope_p4
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_quoted_line_act_scope_p4

    def finish(self, result):
        if not isinstance(result, dict) or (result.get("logic") or {}).get(LABEL, {}).get("schema") != SCHEMA:
            return result
        materialize_quoted_line_act_scope_p4(result)
        trace = result.get("runtime_trace")
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (
                getattr(runtime, "turn_traces", None)
                and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")
            ):
                runtime.turn_traces[-1] = deepcopy(trace)
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
    "LABEL", "SCHEMA", "PLANNER_PATH", "classify_quoted_line_act_scope_p4",
    "query_all_layers_with_quoted_line_act_scope_p4", "route_with_quoted_line_act_scope_p4",
    "rule_plan_with_quoted_line_act_scope_p4", "attach_memory_gravity_with_quoted_line_act_scope_p4",
    "cognitive_tick_with_quoted_line_act_scope_p4",
    "visible_guard_with_quoted_line_act_scope_p4", "materialize_quoted_line_act_scope_p4",
    "install_quoted_line_act_scope_p4",
]
