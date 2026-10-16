"""Product-only fast fallback for one source-admitted Japanese self preference.

The previous rule planner keeps priority.  This layer runs only where that
planner would have returned ``None``; it reads the already-postposed profile
owner admission without invoking either profile writer or a model.
"""

from __future__ import annotations

import re
from copy import deepcopy

import uruha_profile_owner_admission_p4 as owner
import uruha_profile_postposed_self_denial_p4 as postposed
import uruha_relationship_question_evidence_p4 as question


LABEL = "source_bound_preference_fallback_p4"
SCHEMA = "uruha_source_bound_preference_fallback_p4_v1"
MAX_INPUT_CHARS = 40
MAX_VALUE_CHARS = 24
_JAPANESE_CHAR = r"[\u3041-\u3096\u30a1-\u30fa\u30fc\u3400-\u9fff\u3005\u3006\u30f5\u30f6]"
_VALUE_CHAR = r"[A-Za-z0-9\u3041-\u3096\u30a1-\u30fa\u30fc\u3400-\u9fff\u3005\u3006\u30f5\u30f6]"
_SIMPLE_SELF_LIKE = re.compile(
    rf"(?P<speaker>私は|わたしは|僕は|ぼくは|うちは|自分は)"
    rf"(?P<value>{_VALUE_CHAR}{{1,{MAX_VALUE_CHARS}}})が好き(?P<stop>。|\.)?"
)
_HAS_JAPANESE = re.compile(_JAPANESE_CHAR)
# Bounded lexical object heads, not a list of probe items.  Source admission
# proves speaker and value but cannot distinguish a bare, unknown person name
# from an object; ambiguous values keep the inherited planner path.
_OBJECT_HEAD_SUFFIXES = (
    "餅", "団子", "ソーダ", "茶", "コーヒー", "クッキー", "せんべい",
    "タルト", "甘酒", "スープ", "ケーキ", "パン", "羊羹", "チョコ",
    "チョコレート", "カレー", "麺", "アイス", "ジュース", "おにぎり",
    "弁当", "料理", "菓子", "映画", "ゲーム", "漫画", "アニメ",
    "曲", "音楽",
)
_OBJECT_HEAD_PREFIXES = ("映画",)
# Known person referents/honorifics are denied even if a future category cue
# happens to overlap. Unknown aliases can still collide with object heads.
_PERSON_REFERENTS = frozenset({
    "あなた", "あんた", "君", "きみ", "お前", "おまえ", "彼", "彼女", "あの人",
    "人", "誰", "みんな", "皆", "私", "わたし", "僕", "ぼく", "うち", "自分",
    "友達", "友人", "母", "父", "兄", "姉", "弟", "妹", "先生", "先輩",
    "うるは", "一ノ瀬うるは", "推し", "恋人", "彼氏", "彼女",
})
_PERSON_SUFFIX = re.compile(r"(?:さん|ちゃん|くん|君|様|先生|先輩|氏)$")
_PERSON_SCOPE = re.compile(r"(?:友達|友人|彼|彼女|恋人|家族|母|父|兄|姉|弟|妹)の")
_MEMORY_ACT = re.compile(r"(?:覚え|記憶|メモ|保存|訂正|更正)")

_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _owner_chain_ready():
    return bool(
        owner._INSTALLED
        and postposed._INSTALLED
        and owner.admit_legacy_profile_facts
        is postposed.admit_legacy_profile_facts_with_postposed_self_denial_p4
    )


def _source_value(text):
    """Return the exact value and undelimited source, or fail closed."""
    if not isinstance(text, str) or len(text) > MAX_INPUT_CHARS:
        return None
    match = _SIMPLE_SELF_LIKE.fullmatch(text)
    if match is None:
        return None
    value = match.group("value")
    if (
        not _HAS_JAPANESE.search(value)
        or value in _PERSON_REFERENTS
        or _PERSON_SUFFIX.search(value)
        or _PERSON_SCOPE.search(value)
        or _MEMORY_ACT.search(value)
        or not (
            value.endswith(_OBJECT_HEAD_SUFFIXES)
            or value.startswith(_OBJECT_HEAD_PREFIXES)
        )
    ):
        return None
    source_span = text[:-1] if match.group("stop") else text
    return value, source_span


def source_bound_preference_plan_p4(text):
    """Build a chat seed only from one matching postposed-owner admission."""
    parsed = _source_value(text)
    if parsed is None or not _owner_chain_ready():
        return None
    value, source_span = parsed
    facts, audit = owner.admit_legacy_profile_facts(text)
    if not isinstance(audit, dict) or not isinstance(facts, list):
        return None
    decisions = audit.get("decisions")
    if not (
        facts == [("like", value)]
        and audit.get("schema") == owner.SCHEMA
        and audit.get("path") == "legacy"
        and audit.get("input_sha256") == owner._digest(text)
        and audit.get("candidate_count") == 1
        and audit.get("admitted_count") == 1
        and audit.get("rejected_count") == 0
        and not audit.get("reason")
        and isinstance(decisions, list)
        and len(decisions) == 1
    ):
        return None
    decision = decisions[0]
    if not (
        isinstance(decision, dict)
        and decision.get("admitted") is True
        and decision.get("owner") == "user"
        and decision.get("fact_type") == "like"
        and decision.get("reason") in {"direct_self", "explicit_self"}
        and decision.get("source_span_sha256") == owner._digest(source_span)
        and decision.get("value_sha256") == owner._digest(value)
    ):
        return None

    trace = {
        "schema": SCHEMA,
        "status": "source_admitted_current_self_like",
        "input_sha256": audit["input_sha256"],
        "source_span_sha256": decision["source_span_sha256"],
        "value_sha256": decision["value_sha256"],
        "candidate_count": 1,
        "admitted_count": 1,
        "model_call_attempted": False,
        "raw_dialogue_persisted": False,
    }
    return {
        "intent": "chat",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "自分の好みを話している",
        "reply_goal": "今の好みを軽く受け止める",
        "jp_summary": f"ユーザーは{value}が好きだと話している。",
        "core_message_jp": f"{value}が好きなんだ。いいじゃん。",
        "stance": {"warmth": 0.36, "tease": 0.08, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.08,
        "premise_check": "accept",
        "self_check": False,
        "subjective_note_jp": "当輪の本人申告だけを受け止める",
        "hidden_intent": "plain_request",
        "surface_act": "plain_reply",
        "grounding": {"preference_source": "current_user_self_assertion"},
        "payload_level": "medium",
        "planner_path": LABEL,
        LABEL: trace,
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 44,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["覚えた", "覚えとく", "覚えておく", "記憶した", "メモした", "私"],
    }


def rule_plan_with_source_bound_preference_fallback_p4(
    self, user_input, current_psyche, memory_data=None
):
    original = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    if original is not None:
        return original
    return source_bound_preference_plan_p4(user_input)


def materialize_source_bound_preference_fallback_p4(result, source):
    """Record the actual selected fallback, not merely an eligible seed."""
    if not isinstance(result, dict) or not isinstance(source, str):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    memory_runtime = result.get("memory_runtime")
    if not all(isinstance(part, dict) for part in (logic, trace, memory_runtime)):
        return result
    if logic.get("planner_path") != LABEL or logic.get("intent") != "chat" or logic.get("scene") != "casual":
        return result
    seed = source_bound_preference_plan_p4(source)
    if seed is None or logic.get("core_message_jp") != seed["core_message_jp"]:
        return result
    m21 = logic.get("bounded_slow_path_m21") or {}
    if not (
        m21.get("route") == "deterministic_rule_plan"
        and m21.get("model_call_attempted") is False
    ):
        return result
    admitted = memory_runtime.get(owner.LABEL) or {}
    decisions = admitted.get("decisions")
    source_audit = seed[LABEL]
    if not (
        admitted.get("schema") == owner.SCHEMA
        and admitted.get("path") == "legacy"
        and admitted.get("input_sha256") == source_audit["input_sha256"]
        and admitted.get("candidate_count") == 1
        and admitted.get("admitted_count") == 1
        and isinstance(decisions, list)
        and len(decisions) == 1
        and isinstance(decisions[0], dict)
        and decisions[0].get("admitted") is True
        and decisions[0].get("owner") == "user"
        and decisions[0].get("fact_type") == "like"
        and decisions[0].get("source_span_sha256") == source_audit["source_span_sha256"]
        and decisions[0].get("value_sha256") == source_audit["value_sha256"]
    ):
        return result
    selected = trace.get("selected_plan")
    rows = trace.get("blackboard")
    if not isinstance(selected, dict) or not isinstance(rows, list):
        return result
    matching_rows = [row for row in rows if isinstance(row, dict) and row.get("label") == "selected_plan"]
    if not (
        len(matching_rows) == 1
        and isinstance(matching_rows[0].get("payload"), dict)
        and matching_rows[0]["payload"].get("intent") == logic["intent"]
        and matching_rows[0]["payload"].get("scene") == logic["scene"]
        and matching_rows[0]["payload"].get("core_message_jp") == logic["core_message_jp"]
        and matching_rows[0]["payload"].get("planner_path") in (None, LABEL)
        and selected.get("intent") == logic["intent"]
        and selected.get("scene") == logic["scene"]
        and selected.get("core_message_jp") == logic["core_message_jp"]
        and selected.get("planner_path") in (None, LABEL)
    ):
        return result

    payload = {
        "schema": SCHEMA,
        "status": "selected_source_admitted_rule_fallback",
        # The graph renderer displays `route`; keep it fixed and raw-free so
        # viewers see why this node exists instead of an opaque field count.
        "route": "本人偏好來源一致 → 直接回覆計畫",
        "planner_path": LABEL,
        "input_sha256": source_audit["input_sha256"],
        "source_span_sha256": source_audit["source_span_sha256"],
        "value_sha256": source_audit["value_sha256"],
        "owner_admission_schema": owner.SCHEMA,
        "owner_admitted_count": 1,
        "m21_route": "deterministic_rule_plan",
        "general_planner_model_call_attempted": False,
        "memory_write_claimed": False,
        "raw_dialogue_persisted": False,
    }
    selected["planner_path"] = LABEL
    matching_rows[0]["payload"]["planner_path"] = LABEL
    without_prior = [row for row in rows if not (isinstance(row, dict) and row.get("label") == LABEL)]
    insertion = next(
        (index + 1 for index, row in enumerate(without_prior) if isinstance(row, dict) and row.get("label") == "selected_plan"),
        len(without_prior),
    )
    without_prior.insert(insertion, {"stage": "select", "label": LABEL, "payload": payload, "salience": 0.96})
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(payload)
    logic[LABEL] = deepcopy(payload)
    return result


def _finish_source_bound_preference_fallback_p4(self, result, source):
    materialize_source_bound_preference_fallback_p4(result, source)
    if not isinstance(result, dict) or LABEL not in (result.get("logic") or {}):
        return result
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    current = result["runtime_trace"]
    self.runtime.last_selected_plan = deepcopy(current["selected_plan"])
    self.runtime.blackboard = deepcopy(current["blackboard"])
    snapshot = result.get("runtime_state")
    if isinstance(snapshot, dict):
        snapshot["last_selected_plan"] = deepcopy(current["selected_plan"])
    sync_current_history_m41_1(result)
    if (
        self.runtime.turn_traces
        and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index")
    ):
        self.runtime.turn_traces[-1] = deepcopy(current)
    return result


def run_turn_debug_with_source_bound_preference_fallback_p4(self, user_input, input_context=None):
    result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    return _finish_source_bound_preference_fallback_p4(self, result, user_input)


def emit_response_if_ready_with_source_bound_preference_fallback_p4(self, event, tick_result):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _finish_source_bound_preference_fallback_p4(self, result, (event or {}).get("user_input"))


def install_source_bound_preference_fallback_p4():
    """Postpose one rule-plan fallback after the installed question overlay."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    if not _owner_chain_ready() or not question._INSTALLED:
        raise RuntimeError(f"{LABEL}:prior_source_and_question_overlays_required")
    if LeftBrain._rule_based_plan is not question._inline_plan_with_full_turn:
        raise RuntimeError(f"{LABEL}:prior_rule_plan_changed")
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_source_bound_preference_fallback_p4
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_source_bound_preference_fallback_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_source_bound_preference_fallback_p4
    _INSTALLED = True
    return True


def preference_fallback_preflight_p4():
    """Small no-model install/route check for the isolated entry launcher."""
    from uruha_brain_mac import LeftBrain

    left = LeftBrain.__new__(LeftBrain)
    psyche = {"mood": 0, "trust": 50}
    positive = "私は山椒海苔せんべいが好き。"
    negative = "友達は山椒海苔せんべいが好き。"
    seed = left._rule_based_plan(positive, psyche, {})
    route = source_bound_preference_plan_p4(positive)
    prior = _ORIGINAL_RULE_PLAN(left, "好き？", psyche, {}) if callable(_ORIGINAL_RULE_PLAN) else None
    protected = left._rule_based_plan("好き？", psyche, {})
    trace = (route or {}).get(LABEL) or {}
    contract = {
        "installed": bool(_INSTALLED and LeftBrain._rule_based_plan is rule_plan_with_source_bound_preference_fallback_p4),
        "owner_postposed": _owner_chain_ready(),
        "positive_route": bool(seed and seed.get("intent") == "chat" and seed.get("planner_path") == LABEL),
        "negative_route": source_bound_preference_plan_p4(negative) is None,
        "original_priority": bool(prior is not None and protected == prior and protected.get("intent") == "ask_like_me"),
        "raw_free_trace": bool(
            trace.get("schema") == SCHEMA
            and trace.get("raw_dialogue_persisted") is False
            and trace.get("model_call_attempted") is False
            and positive not in str(trace)
            and "山椒海苔せんべい" not in str(trace)
            and route.get("planner_path") == LABEL
        ),
    }
    if not all(contract.values()):
        raise RuntimeError(f"{LABEL}:preflight_failed:{contract}")
    return deepcopy(contract)


__all__ = [
    "LABEL",
    "SCHEMA",
    "source_bound_preference_plan_p4",
    "materialize_source_bound_preference_fallback_p4",
    "install_source_bound_preference_fallback_p4",
    "preference_fallback_preflight_p4",
]
