"""Bounded response authority for an explicit neutral wait-and-see request."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata


LABEL = "wait_and_see_authority_p3"
SCHEMA = "uruha_wait_and_see_authority_p3"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_NO_REASSURANCE = {
    "zh": re.compile(r"(?:不要|別|别)(?:安慰|鼓勵|鼓励)(?:我)?(?:說|说)?(?:一定)?(?:沒事|没事|有希望|沒問題|没问题)|(?:比起|不要)(?:叫我|跟我說|跟我说)?(?:期待|樂觀|乐观)"),
    "en": re.compile(r"\b(?:do(?:n't| not)\s+reassure\s+me|do(?:n't| not)\s+tell\s+me\s+(?:it(?:'ll| will)\s+be\s+fine|to\s+keep\s+hoping)|rather\s+than\s+(?:reassuring|telling)\s+me\s+to\s+hope)\b", re.I),
    "ja": re.compile(r"期待していいって励ますより|(?:大丈夫|期待していい)(?:って|と)(?:励まさ|言わ)ないで|楽観(?:させ|し)ないで"),
}
_WAIT_AND_SEE = {
    "zh": re.compile(r"(?:一起|陪我)?(?:整理成|當成|当成)?(?:先)?(?:觀望|观望|觀察|观察|看情況|看情况)"),
    "en": re.compile(r"\b(?:sort\s+it\s+out\s+(?:with\s+me\s+)?as\s+wait\s+and\s+see|let(?:'s| us)\s+(?:call\s+it\s+)?wait\s+and\s+see|just\s+help\s+me\s+frame\s+it\s+as\s+wait\s+and\s+see)\b", re.I),
    "ja": re.compile(r"(?:今回は|いったん|今は)?様子見(?:って|で|として).{0,20}(?:一緒に整理して|整理しよう|見ておこう)|一緒に.{0,12}様子見(?:って|で)整理して"),
}
_NEGATED = re.compile(r"(?:様子見(?:に)?(?:は)?しないで|不要觀望|不要观望|別等|别等|don't\s+wait\s+and\s+see|do\s+not\s+wait\s+and\s+see)", re.I)
_META = re.compile(r"(?:引用|台本|脚本|例文|翻譯|翻译|\b(?:quote|script|example|translate|translation)\b)", re.I)
_THIRD_PERSON = re.compile(r"(?:彼|彼女|友達|友人)(?:は|が).{0,72}(?:励まさない|様子見)|(?:他|她|朋友).{0,72}(?:不要安慰|觀望|观望)|\b(?:he|she|they|my\s+friend).{0,72}(?:reassure|wait\s+and\s+see)\b", re.I)
_ACTION = re.compile(r"(?:VRM|avatar|function|アバター|モデル|表情|動作指令|动作指令).{0,72}(?:様子見|wait|觀望|观望)|(?:様子見|wait\s+and\s+see).{0,72}(?:VRM|avatar|function|アバター|モデル)", re.I)
_RISK = re.compile(r"(?:死にたい|自殺したい|消えたい|不想活|想死|自殺|自杀|kill\s+myself|hurt\s+myself|want\s+to\s+die|end\s+my\s+life)", re.I)

_SELECTED_CORE_JP = "うん。期待していいとも断られたとも決めず、今回はいったん様子見でいいだろ。"


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def classify_wait_and_see_authority_p3(user_input):
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    digest = _digest(text)
    for pattern, reason in (
        (_RISK, "protected_risk_cue"), (_META, "metalinguistic_or_quoted_context"),
        (_THIRD_PERSON, "third_person_report"), (_ACTION, "action_or_avatar_command"),
        (_NEGATED, "wait_and_see_negated"),
    ):
        if pattern.search(text):
            return {"schema": SCHEMA, "status": "not_selected", "selected": False, "reason": reason, "input_digest": digest, "raw_dialogue_persisted": False}
    no_reassurance = [language for language, pattern in _NO_REASSURANCE.items() if pattern.search(text)]
    wait = [language for language, pattern in _WAIT_AND_SEE.items() if pattern.search(text)]
    if not no_reassurance or not wait:
        missing = []
        if not no_reassurance: missing.append("explicit_no_false_reassurance_clause")
        if not wait: missing.append("joint_wait_and_see_request")
        return {"schema": SCHEMA, "status": "not_selected", "selected": False, "reason": "required_clause_missing", "missing": missing, "input_digest": digest, "raw_dialogue_persisted": False}
    language = wait[0] if wait[0] in no_reassurance else no_reassurance[0]
    return {
        "schema": SCHEMA, "status": "explicit_wait_and_see_authorized", "selected": True,
        "language": language,
        "observable_cues": ["explicit_no_false_reassurance", "joint_wait_and_see_request"],
        "authority": "current_explicit_desired_response", "surface_authority": True,
        "input_digest": digest, "model_call_added": False, "fact_memory_write_count": 0,
        "private_state_truth_claimed": False, "raw_dialogue_persisted": False,
        "claim_boundary": "explicit current-turn request for a neutral provisional frame; not a claim about another person's intent or the relationship outcome",
    }


def build_wait_and_see_contract_p3(user_input):
    contract = classify_wait_and_see_authority_p3(user_input)
    if not contract.get("selected"): return contract
    return {
        **contract, "selected_core_jp": _SELECTED_CORE_JP,
        "selected_core_sha256": _digest(_SELECTED_CORE_JP), "response_mode": "neutral_wait_and_see",
        "must_not": ["promise_positive_outcome", "declare_rejection", "give_action_plan", "write_relationship_fact"],
    }


def _plan(contract):
    return {
        "candidate_label": "p3_wait_and_see", "intent": "relational_uncertainty",
        "mood_impact": 0, "trust_impact": 1, "scene": "casual",
        "listener_state": "楽観的な保証ではなく、両側を決めない整理を求めている",
        "reply_goal": "希望とも拒絶とも断定せず、当面の様子見として短く整理する",
        "jp_summary": "ユーザーが関係結果を決めず、様子見として一緒に整理するよう求めた。",
        "core_message_jp": contract["selected_core_jp"], "cognitive_mode": "direct",
        "response_mode": "direct_answer", "uncertainty": 0.08,
        "premise_check": "hold_both_outcomes_open", "self_check": True,
        "subjective_note_jp": "相手の意図は未知のまま保つ", "hidden_intent": "uncertainty_co_regulation",
        "user_belief": "楽観も拒絶もまだ確定させたくない。",
        "my_hidden_knowledge": "相手の意図と関係結果は不明。",
        "user_expectation": "保証や助言ではなく、現在を様子見として整理する返答。",
        "surface_act": "plain_reply", "payload_level": "low",
        "wait_and_see_contract_p3": deepcopy(contract),
        "planner_path": "explicit_wait_and_see_authority_p3",
        "constraints": {"first_person": "うち", "sentence_count": 2, "max_chars": 48, "casual_japanese_only": True, "forbid_polite": True, "forbid_knowledge": True, "forbid_lore": True, "forbid_self_variants": True},
        "must_avoid": ["絶対", "きっと", "脈あり", "振られた", "どうする", "AI"],
    }


def rule_plan_with_wait_and_see_p3(self, user_input, current_psyche, memory_data=None):
    contract = build_wait_and_see_contract_p3(user_input)
    if contract.get("selected") and contract.get("surface_authority"): return _plan(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def visible_guard_with_wait_and_see_p3(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(self, reply, logic_data, user_input=user_input, memory_data=memory_data)
    contract = build_wait_and_see_contract_p3(user_input)
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    if not contract.get("selected") or route == "safety_sensitive": return visible
    before = str(visible or "").strip()
    visible = contract["selected_core_jp"]
    contract.update(visible_surface_status="matched", pre_authority_surface_sha256=_digest(before), final_visible_surface_jp=visible, final_visible_surface_sha256=_digest(visible), final_visible_surface_matches_contract=True, visible_surface_changed=visible != before)
    logic_data["wait_and_see_contract_p3"] = deepcopy(contract)
    explicit = deepcopy(logic_data.get("explicit_desired_response_m25") or {})
    explicit[LABEL] = {"status": contract["status"], "authority": contract["authority"], "surface_required": True, "surface_status": "matched", "raw_dialogue_persisted": False}
    logic_data["explicit_desired_response_m25"] = explicit
    desired = deepcopy(logic_data.get("desired_response_mode_m23") or {})
    desired[LABEL] = {"selected_mode": "neutral_wait_and_see", "source": "current_explicit_desired_response", "surface_authority": True, "raw_dialogue_persisted": False}
    logic_data["desired_response_mode_m23"] = desired
    language = deepcopy(logic_data.get("visible_language_guard") or {})
    language.update(final_reply=visible, final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(), wait_and_see_authority_p3=True, wait_and_see_surface_status="matched")
    logic_data["visible_language_guard"] = language
    return visible


def materialize_wait_and_see_p3(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get("wait_and_see_contract_p3") or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(visible_surface_status="matched" if final == payload.get("selected_core_jp") else "mismatch", final_visible_surface_jp=final, final_visible_surface_sha256=_digest(final), final_visible_surface_matches_contract=bool(final == payload.get("selected_core_jp")), flow=["explicit_no_false_reassurance", "joint_wait_and_see_request", "current_turn_response_authority", "neutral_provisional_japanese_frame"])
        logic["wait_and_see_contract_p3"] = deepcopy(payload)
        index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)))
        rows.insert(index, {"stage": "select", "label": LABEL, "payload": deepcopy(payload), "salience": 1.0})
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_wait_and_see_authority_p3():
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED: return False
    from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD = LeftBrain._rule_based_plan, RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN, _ORIGINAL_EMIT = UruhaBrainV4_Mac.run_turn_debug, UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_wait_and_see_p3
    RightBrain.enforce_user_visible_japanese = visible_guard_with_wait_and_see_p3
    def finish(self, result):
        materialize_wait_and_see_p3(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"): self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result
    def run(self, user_input, input_context=None): return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))
    def emit(self, event, tick_result): return finish(self, _ORIGINAL_EMIT(self, event, tick_result))
    UruhaBrainV4_Mac.run_turn_debug, UruhaBrainV4_Mac.emit_response_if_ready = run, emit
    _INSTALLED = True
    return True
