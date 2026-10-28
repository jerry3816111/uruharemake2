"""Product-only plan and surface authority for explicit preference memory acts.

P4-G first owned only an overly formal bare acknowledgement corner.  Its frozen
real result showed that arbitrary wording and a legacy intent collision can both
happen before that narrow repair.  P4-H therefore gives the already-frozen
explicit first-person preference write/correction classifier one deterministic
plan and exact acknowledgement surface.  It still does not change retrieval,
episode writes, preference semantics, ranking, or correction recall.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata


LABEL = "explicit_preference_acknowledgement_p4"
SCHEMA = "uruha_explicit_preference_acknowledgement_p4"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

AUTHORITATIVE_SURFACES = {
    "write": "ん、その好みは覚えとく。",
    "correction": "ん、訂正の内容はそのまま覚えとく。",
}
GENERIC_FORMAL_ACKNOWLEDGEMENTS = {
    "了解しました",
    "わかりました",
    "分かりました",
    "承知しました",
}

_METALINGUISTIC = re.compile(
    r"(?:translate|translation|quoted?|sentence|what\s+does.+mean|"
    r"翻[譯译]|引[用號号]|句子|什[麼么]意思|"
    r"翻訳|引用|文の意味|どういう意味)",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"(?:\bif\s+i\s+(?:prefer|preferred|like|liked)\b|如果|假如|假設|假设|もし)",
    re.I,
)
_PROTECTED_RISK = re.compile(
    r"(?:死にたい|自殺したい|消えたい|不想活|想死|自殺|自杀|"
    r"kill\s+myself|hurt\s+myself|want\s+to\s+die|end\s+my\s+life)",
    re.I,
)
_ACTION_OR_AVATAR = re.compile(
    r"(?:open|launch|start|close|run|execute|開|打開|打开|啟動|启动|關閉|关闭|"
    r"動か|動作|笑顔|表情).{0,72}(?:browser|function|tool|VRM|avatar|"
    r"瀏覽器|浏览器|函數|函数|工具|モデル|アバター)|"
    r"(?:browser|function|tool|VRM|avatar|瀏覽器|浏览器|函數|函数|工具|"
    r"モデル|アバター).{0,72}(?:open|launch|start|close|run|execute|開|"
    r"打開|打开|啟動|启动|關閉|关闭|動か|動作|笑顔|表情)",
    re.I,
)

_CORRECTION_PATTERNS = {
    "en": re.compile(
        r"\bI\s+(?:(?:do\s+not|don't)\s+(?:prefer|like)\b[^.!?\n]{1,100}?\banymore\b|"
        r"no\s+longer\s+(?:prefer|like)\b[^.!?\n]{1,100})"
        r"[.!?\s]+I\s+(?:prefer|like)\b[^.!?\n]{1,100}?\bnow\b",
        re.I,
    ),
    "zh": re.compile(
        r"我(?:現在|现在)?不(?:再)?(?:喜歡|喜欢)[^，。！？!?\n]{1,60}(?:了| anymore)"
        r"[，。；;！!？?\s]+(?:我)?(?:現在|现在)(?:比較|比较)?(?:喜歡|喜欢)[^，。！？!?\n]{1,60}",
        re.I,
    ),
    "ja": re.compile(
        r"(?:もう)(?:私は|うちは|自分は)?[^、。！？!?\n]{1,60}?は"
        r"(?:好みじゃない|好きじゃない|好みではない|好きではない)"
        r"[、。；;！!？?\s]+(?:私は|うちは|自分は)?今は[^、。！？!?\n]{1,60}?が"
        r"(?:好き|好み)",
        re.I,
    ),
}

_WRITE_PATTERNS = {
    "en": (
        re.compile(r"\bI\s+(?:prefer|like)\b[^.!?\n]{1,100}", re.I),
        re.compile(
            r"\b(?:please\s+)?remember\b[^.!?\n]{0,100}\b(?:my|current)\b"
            r"[^.!?\n]{0,60}\bpreference\b",
            re.I,
        ),
    ),
    "zh": (
        re.compile(r"我(?:現在|现在)?(?:比較|比较)?(?:喜歡|喜欢)[^，。！？!?\n]{1,60}"),
        re.compile(
            r"(?:請|请|幫我|帮我)?(?:記住|记住)[^，。！？!?\n]{0,80}"
            r"(?:我)?(?:現在|现在)?[^，。！？!?\n]{0,30}(?:偏好|喜好)"
        ),
    ),
    "ja": (
        re.compile(r"(?:私は|うちは|自分は|今は)[^、。！？!?\n]{1,60}?(?:が|を)(?:好き|好み)"),
        re.compile(r"(?:今の)?好みとして(?:覚えといて|覚えておいて|覚えてて|覚えておいてね)"),
    ),
}


def _digest(value) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _normalize_acknowledgement(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\s。．.!！?？、,]+", "", text).strip()


def classify_explicit_preference_acknowledgement_p4(user_input):
    """Classify only frozen observable wording and retain no raw dialogue."""
    text = str(user_input or "").strip()
    base = {
        "schema": SCHEMA,
        "selected": False,
        "status": "not_selected",
        "input_sha256": _digest(text),
        "raw_dialogue_persisted": False,
    }
    if not text:
        return {**base, "reason": "empty_input"}
    if _PROTECTED_RISK.search(text):
        return {**base, "reason": "protected_risk_cue"}
    if _ACTION_OR_AVATAR.search(text):
        return {**base, "reason": "function_or_vrm_action_command"}
    if _METALINGUISTIC.search(text):
        return {**base, "reason": "metalinguistic_or_quoted_context"}
    if _HYPOTHETICAL.search(text):
        return {**base, "reason": "hypothetical_context"}

    for language, pattern in _CORRECTION_PATTERNS.items():
        if pattern.search(text):
            return {
                **base,
                "selected": True,
                "status": "explicit_first_person_preference_correction",
                "act": "correction",
                "language": language,
                "cue_id": f"preference_ack:{language}:correction:v1",
                "epistemic_status": "known_observable_utterance",
            }

    for language, patterns in _WRITE_PATTERNS.items():
        if all(pattern.search(text) for pattern in patterns):
            return {
                **base,
                "selected": True,
                "status": "explicit_first_person_preference_memory_write",
                "act": "write",
                "language": language,
                "cue_id": f"preference_ack:{language}:write:v1",
                "epistemic_status": "known_observable_utterance",
            }
    return {**base, "reason": "explicit_preference_memory_act_not_detected"}


def build_explicit_preference_memory_act_contract_p4(user_input):
    """Promote only a selected P4-G classifier result to P4-H authority."""
    classification = classify_explicit_preference_acknowledgement_p4(user_input)
    if not classification.get("selected"):
        return classification
    act = classification["act"]
    return {
        **classification,
        "status": "explicit_preference_memory_act_authorized",
        "classifier_source": "p4_g_frozen_multilingual_classifier",
        "plan_authority": True,
        "surface_authority": True,
        "planner_path": "explicit_preference_memory_act_authority_p4",
        "selected_core_jp": AUTHORITATIVE_SURFACES[act],
        "model_call_added": False,
        "episode_write_count_changed": False,
        "memory_schema_or_ranking_changed": False,
        "p4_f_supersession_or_recall_changed": False,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "bounded explicit preference memory-act plan and surface only; not "
            "a semantic recall, understanding or research claim"
        ),
    }


def _plan_from_explicit_preference_memory_act_p4(contract):
    correction = contract.get("act") == "correction"
    return {
        "candidate_label": "p4_preference_memory_act",
        "intent": (
            "explicit_preference_memory_correction"
            if correction
            else "explicit_preference_memory_write"
        ),
        "mood_impact": 0,
        "trust_impact": 1,
        "scene": "casual",
        "listener_state": "現在の好みを明示して記憶への反映を求めている",
        "reply_goal": "記憶行為を短い自然な日本語で確認する",
        "jp_summary": (
            "ユーザーが以前の好みを訂正し、現在の好みを明示した。"
            if correction
            else "ユーザーが現在の好みを明示し、覚えるよう求めた。"
        ),
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.02,
        "premise_check": "accept",
        "self_check": True,
        "subjective_note_jp": "明示された記憶行為だけ確認する",
        "hidden_intent": "memory_probe",
        "user_belief": "明示した現在の好みを会話記憶に残してほしい。",
        "my_hidden_knowledge": "好みの内容はユーザー自身の現在発話に由来する。",
        "user_expectation": "記憶したことが分かる短い自然な確認。",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "source": "current_explicit_user_utterance",
            "act": contract["act"],
            "language": contract["language"],
        },
        "payload_level": "low",
        "explicit_preference_memory_act_contract_p4": deepcopy(contract),
        "planner_path": contract["planner_path"],
        "constraints": {
            "first_person": "うち",
            "sentence_count": 1,
            "max_chars": 28,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "了解しました", "わかりました", "承知しました", "AI"],
    }


def rule_plan_with_explicit_preference_memory_act_p4(
    self,
    user_input,
    current_psyche,
    memory_data=None,
):
    contract = build_explicit_preference_memory_act_contract_p4(user_input)
    if contract.get("selected") and contract.get("plan_authority"):
        return _plan_from_explicit_preference_memory_act_p4(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def apply_explicit_preference_acknowledgement_p4(reply, user_input):
    """Return the visible surface and a raw-dialogue-free audit."""
    before = str(reply or "").strip()
    classification = classify_explicit_preference_acknowledgement_p4(user_input)
    normalized = _normalize_acknowledgement(before)
    generic = normalized in GENERIC_FORMAL_ACKNOWLEDGEMENTS
    selected = bool(classification.get("selected"))
    changed = bool(selected and generic)
    final = AUTHORITATIVE_SURFACES[classification["act"]] if changed else before
    if not selected:
        status = "not_selected"
        reason = classification.get("reason")
    elif not generic:
        status = "eligible_surface_already_non_generic"
        reason = "post_guard_reply_not_in_generic_formal_allowlist"
    else:
        status = "casual_acknowledgement_committed"
        reason = "explicit_preference_act_and_generic_formal_surface"
    audit = {
        **classification,
        "status": status,
        "reason": reason,
        "post_language_guard_generic_formal_acknowledgement": generic,
        "surface_authority": changed,
        "surface_changed": changed,
        "pre_authority_surface_sha256": _digest(before),
        "final_visible_surface_sha256": _digest(final),
        "final_visible_surface_jp": final if changed else None,
        "model_call_added": False,
        "episode_write_count_changed": False,
        "memory_ranking_changed": False,
        "p4_f_supersession_or_recall_changed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "generic formal acknowledgement surface only; not a memory semantic, "
            "persona-wide, understanding or research claim"
        ),
    }
    return final, audit


def visible_guard_with_explicit_preference_acknowledgement_p4(
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
    contract = build_explicit_preference_memory_act_contract_p4(user_input)
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    before = str(visible or "").strip()
    if contract.get("selected") and route != "safety_sensitive":
        final = contract["selected_core_jp"]
        audit = {
            **contract,
            "status": "explicit_preference_memory_act_committed",
            "reason": "selected_typed_act_owns_plan_and_final_surface",
            "post_language_guard_generic_formal_acknowledgement": (
                _normalize_acknowledgement(before) in GENERIC_FORMAL_ACKNOWLEDGEMENTS
            ),
            "surface_changed": final != before,
            "pre_authority_surface_sha256": _digest(before),
            "final_visible_surface_sha256": _digest(final),
            "final_visible_surface_jp": final,
        }
    else:
        final, audit = apply_explicit_preference_acknowledgement_p4(visible, user_input)
        if contract.get("selected") and route == "safety_sensitive":
            audit.update(
                status="blocked_by_safety_sensitive_route",
                reason="safety_surface_remains_authoritative",
                plan_authority=False,
                surface_authority=False,
                surface_changed=False,
            )
    if not isinstance(logic_data, dict):
        return final
    logic_data[LABEL] = deepcopy(audit)
    if audit.get("surface_authority"):
        guard = deepcopy(logic_data.get("visible_language_guard") or {})
        guard.update(
            changed=bool(audit.get("surface_changed")),
            repair_action=LABEL,
            pre_p4_g_final_reply_sha256=_digest(visible),
            final_reply=final,
            final_reply_sha256=_digest(final),
            explicit_preference_acknowledgement_p4=True,
        )
        logic_data["visible_language_guard"] = guard
    return final


def materialize_explicit_preference_acknowledgement_p4(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("selected"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        expected = AUTHORITATIVE_SURFACES.get(payload.get("act"))
        payload.update(
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=bool(expected and final == expected),
            flow=[
                "explicit_preference_act",
                "deterministic_memory_act_plan",
                "current_turn_surface_authority",
                "bounded_casual_japanese_acknowledgement",
            ],
        )
        logic[LABEL] = deepcopy(payload)
        index = next(
            (i for i, row in enumerate(rows) if row.get("label") == "utterance"),
            len(rows),
        )
        rows.insert(
            index,
            {
                "stage": "select" if payload.get("plan_authority") else "surface",
                "label": LABEL,
                "payload": deepcopy(payload),
                "salience": 1.0 if payload.get("surface_changed") else 0.84,
            },
        )
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_explicit_preference_acknowledgement_p4():
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
    LeftBrain._rule_based_plan = rule_plan_with_explicit_preference_memory_act_p4
    RightBrain.enforce_user_visible_japanese = (
        visible_guard_with_explicit_preference_acknowledgement_p4
    )

    def finish(self, result):
        materialize_explicit_preference_acknowledgement_p4(result)
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
