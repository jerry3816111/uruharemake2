"""Bounded current-turn authority for an explicit playful photography guess."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata


LABEL = "playful_guess_authority_p3"
SCHEMA = "uruha_playful_guess_authority_p3"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_POSITIVE_NOT_CALM = {
    "zh": re.compile(r"(?:不用|不要)(?:安慰|叫我冷靜|叫我冷静)|(?:我)?(?:不是焦慮|不是焦虑).{0,24}(?:興奮|兴奋|期待)|(?:我)?(?:很|只是)?(?:興奮|兴奋|期待)"),
    "en": re.compile(r"\b(?:do(?:n't| not)\s+calm\s+me\s+down|i(?:'m| am)\s+(?:not\s+anxious.{0,24})?(?:excited|thrilled)|this\s+is\s+excitement)\b", re.I),
    "ja": re.compile(r"(?:落ち着かせ|宥め)なくて(?:いい|平気)|(?:不安|心配)じゃなくて.{0,24}(?:楽しみ|興奮)|(?:うち|私|僕|俺)?(?:は)?(?:楽しみ|興奮してる)"),
}
_PHOTO_GUESS = {
    "zh": re.compile(r"猜猜(?:看)?我(?:第一張|第一张|最先|先)(?:會|会|要)?拍(?:什麼|什么)|猜我(?:第一張|第一张|最先|先)(?:會|会|要)?拍(?:什麼|什么)"),
    "en": re.compile(r"\bguess\s+what\s+i(?:'m| am)\s+going\s+to\s+(?:photograph|take\s+a\s+picture\s+of|shoot)\s+first\b", re.I),
    "ja": re.compile(r"(?:うち|私|僕|俺)が最初に何を撮るか(?:当てて|予想して)|最初に何を撮ると思う[？?]?"),
}
_NEGATED = re.compile(r"(?:猜わないで|予想しないで|不要猜|別猜|别猜|don't\s+guess|do\s+not\s+guess)", re.I)
_META_OR_QUOTED = re.compile(r"(?:引用|台本|脚本|例文|翻譯|翻译|どういう意味|\b(?:quote|script|example|translate|translation)\b)", re.I)
_THIRD_PERSON = re.compile(r"(?:彼|彼女|友達|友人)(?:は|が).{0,64}(?:当てて|予想して)|(?:他|她|朋友).{0,64}(?:猜猜|猜我)|\b(?:he|she|they|my\s+friend).{0,64}guess\b", re.I)
_ACTION_OR_AVATAR = re.compile(r"(?:VRM|avatar|function|アバター|モデル|表情|動作指令|动作指令|相機功能|相机功能).{0,64}(?:guess|猜|予想|撮)|(?:guess|猜|予想).{0,64}(?:VRM|avatar|function|アバター|モデル)", re.I)
_PROTECTED_RISK = re.compile(r"(?:死にたい|自殺したい|消えたい|不想活|想死|自殺|自杀|kill\s+myself|hurt\s+myself|want\s+to\s+die|end\s+my\s+life)", re.I)

_SELECTED_CORE_JP = "最初は、窓の外の景色……とか？ まあ、うちのただの予想だけど。"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalized(value):
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def classify_playful_guess_authority_p3(user_input):
    text = _normalized(user_input)
    input_digest = _digest(text)
    for pattern, reason in (
        (_PROTECTED_RISK, "protected_risk_cue"),
        (_META_OR_QUOTED, "metalinguistic_or_quoted_context"),
        (_THIRD_PERSON, "third_person_report"),
        (_ACTION_OR_AVATAR, "action_or_avatar_command"),
        (_NEGATED, "guess_negated"),
    ):
        if pattern.search(text):
            return {
                "schema": SCHEMA,
                "status": "not_selected",
                "selected": False,
                "reason": reason,
                "input_digest": input_digest,
                "raw_dialogue_persisted": False,
            }
    positive = [language for language, pattern in _POSITIVE_NOT_CALM.items() if pattern.search(text)]
    guess = [language for language, pattern in _PHOTO_GUESS.items() if pattern.search(text)]
    if not positive or not guess:
        missing = []
        if not positive:
            missing.append("explicit_positive_arousal_or_no_calm_clause")
        if not guess:
            missing.append("first_person_photography_guess_invitation")
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": "required_clause_missing",
            "missing": missing,
            "input_digest": input_digest,
            "raw_dialogue_persisted": False,
        }
    language = guess[0] if guess[0] in positive else positive[0]
    return {
        "schema": SCHEMA,
        "status": "explicit_playful_guess_authorized",
        "selected": True,
        "language": language,
        "observable_cues": [
            "explicit_positive_arousal_or_no_calm",
            "first_person_photography_guess_invitation",
        ],
        "authority": "current_explicit_desired_response",
        "surface_authority": True,
        "input_digest": input_digest,
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "explicit current-turn invitation to make one tentative photography guess; "
            "not a claim about the future, private state, or stable preference"
        ),
    }


def build_playful_guess_contract_p3(user_input):
    contract = classify_playful_guess_authority_p3(user_input)
    if not contract.get("selected"):
        return contract
    return {
        **contract,
        "selected_core_jp": _SELECTED_CORE_JP,
        "selected_core_sha256": _digest(_SELECTED_CORE_JP),
        "response_mode": "playful_tentative_guess",
        "must_not": [
            "calm_user_down",
            "ask_user_to_supply_answer_instead",
            "state_guess_as_fact",
            "write_guess_as_memory",
        ],
    }


def _plan_from_contract(contract):
    return {
        "candidate_label": "p3_playful_guess",
        "intent": "playful_invitation",
        "mood_impact": 1,
        "trust_impact": 1,
        "scene": "casual",
        "listener_state": "興奮を明示し、落ち着かせるより一つ予想してほしい",
        "reply_goal": "断定せず、短い予想で遊びに参加する",
        "jp_summary": "ユーザーが最初の撮影対象を当てるよう直接招いた。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.12,
        "premise_check": "accept_as_invitation_not_fact",
        "self_check": True,
        "subjective_note_jp": "予想だと明示して一つだけ答える",
        "hidden_intent": "playful_invitation",
        "user_belief": "不安ではなく興奮として受け取ってほしいと明示している。",
        "my_hidden_knowledge": "正解は不明なので、予想を事実にしない。",
        "user_expectation": "質問返しや安慰ではなく、一つ予想する返答。",
        "surface_act": "plain_reply",
        "payload_level": "low",
        "playful_guess_contract_p3": deepcopy(contract),
        "planner_path": "explicit_playful_guess_authority_p3",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 45,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["落ち着いて", "大丈夫", "何を撮るつもり", "AI"],
    }


def rule_plan_with_playful_guess_p3(self, user_input, current_psyche, memory_data=None):
    contract = build_playful_guess_contract_p3(user_input)
    if contract.get("selected") and contract.get("surface_authority"):
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def visible_guard_with_playful_guess_p3(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data
    )
    contract = build_playful_guess_contract_p3(user_input)
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    if not contract.get("selected") or route == "safety_sensitive":
        return visible
    before = str(visible or "").strip()
    visible = contract["selected_core_jp"]
    contract.update(
        visible_surface_status="matched",
        pre_authority_surface_sha256=_digest(before),
        final_visible_surface_jp=visible,
        final_visible_surface_sha256=_digest(visible),
        final_visible_surface_matches_contract=True,
        visible_surface_changed=visible != before,
    )
    logic_data["playful_guess_contract_p3"] = deepcopy(contract)
    explicit = deepcopy(logic_data.get("explicit_desired_response_m25") or {})
    explicit[LABEL] = {
        "status": contract["status"],
        "authority": contract["authority"],
        "surface_required": True,
        "surface_status": "matched",
        "raw_dialogue_persisted": False,
    }
    logic_data["explicit_desired_response_m25"] = explicit
    desired = deepcopy(logic_data.get("desired_response_mode_m23") or {})
    desired[LABEL] = {
        "selected_mode": "playful_tentative_guess",
        "source": "current_explicit_desired_response",
        "surface_authority": True,
        "raw_dialogue_persisted": False,
    }
    logic_data["desired_response_mode_m23"] = desired
    language = deepcopy(logic_data.get("visible_language_guard") or {})
    language.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        playful_guess_authority_p3=True,
        playful_guess_surface_status="matched",
    )
    logic_data["visible_language_guard"] = language
    return visible


def materialize_playful_guess_p3(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get("playful_guess_contract_p3") or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(
            visible_surface_status="matched" if final == payload.get("selected_core_jp") else "mismatch",
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=bool(final == payload.get("selected_core_jp")),
            flow=[
                "explicit_positive_arousal_or_no_calm",
                "first_person_photography_guess_invitation",
                "current_turn_response_authority",
                "bounded_tentative_japanese_guess",
            ],
        )
        logic["playful_guess_contract_p3"] = deepcopy(payload)
        index = next(
            (i for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
            next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(index, {"stage": "select", "label": LABEL, "payload": deepcopy(payload), "salience": 1.0})
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_playful_guess_authority_p3():
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_playful_guess_p3
    RightBrain.enforce_user_visible_japanese = visible_guard_with_playful_guess_p3

    def finish(self, result):
        materialize_playful_guess_p3(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"):
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

