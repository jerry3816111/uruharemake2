"""Product-only, bounded selected food-offer action to visible Japanese contract.

This does not decide whether an offer should be accepted.  It only keeps an
already selected acceptance from disappearing in the legacy surface selector.
The finite source/utterance grammar is intentionally not open-domain semantics.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import re


LABEL = "selected_offer_action_surface_fidelity_p4"
SCHEMA = "uruha_selected_offer_action_surface_fidelity_p4_v1"
_CANDIDATE = ContextVar(LABEL + "_candidate", default=None)
_INSTALLED = False
_ORIGINAL_REFINE = None
_ORIGINAL_SPEAK = None
_ORIGINAL_EMIT = None

# Only precise objects that the existing grounder can already name.  Generic
# "甘いの"/"飲み物"/"揚げ物" cannot prove which object was offered.
_ITEMS = frozenset({
    "おにぎり", "ポテト", "アップルパイ", "ミルクシェイク", "バーガー", "ピザ",
})
# Explicitly finite mundane food descriptors.  Arbitrary kanji here could
# turn a poisoned/spoiled offer into a stronger affirmative commitment.
_MODIFIER = re.compile(r"(?:塩|胡椒|海苔|昆布|味噌|山椒|焼き|チーズ|バター|抹茶|玄米茶){0,3}\Z")
_SOURCE_SUFFIX = "、一口いる？"
_PROTECTED = re.compile(
    r"死|殺|自傷|自殺|消えたい|性的|セックス|レイプ|暴力|殴|銃|ナイフ|薬物"
)
_PERSON = re.compile(r"先生|友達|友人|同僚|先輩|後輩|彼|彼女|母|父|祖母|祖父|太郎|あなた|君|お前|そっち")
_REPLY_DISALLOWED = re.compile(
    r"[？?「」『』\"“”]|(?:いらない|要らない|欲しくない|ほしくない|"
    r"もらわない|食べない|食わない|飲まない|つままない|くれない|"
    r"遠慮|無理|じゃない|ではない|ない|なく|なかった|やめ|止め|断る|"
    r"もし|だったら|たら|れば|かも|けど要ら|でも要ら|"
    r"つもりはない|わけではない|予定はない|あげる|あげたい|"
    r"また|さっきから|前にも|この前|覚えてる|って言った|"
    r"(?:食べる|食う|飲む|もらう|つまむ)(?:な|なよ)(?:[。！!]|$))"
)
_ACCEPT = re.compile(r"(?:ほしい|欲しい|もらう|食べる|食う|飲む|つまむ|(?:一口|少し|ちょっと)くれ)")
_DIRECT_BRIDGE = r"(?:なら|は|を|、)?(?:(?:普通に|少し|ちょっと|一口|ほんとに|まじで|マジで|わりと)\s*){0,3}"
_TWO_CLAUSE_BRIDGE = r"(?:なら(?:普通に)?あり|出してくるのずるいな)[。！!]\s*(?:普通に)?(?:少し|ちょっと|一口)"
_SURFACE_PREFIXES = ("ん、", "まあ、", "いや、", "てか、", "一回、", "先に、", "普通に、", "はいはい、")
_DIRECT_TAIL = r"(?:よ|ね|わ)?(?:[。！!](?:今それくらいがちょうどいい[。！!]?)?)?"
_TWO_CLAUSE_TAIL = r"(?:よ|ね|わ)?[。！!]?"


def _accepted_action_link(reply, item):
    """Recognize only bounded no-subject acceptance shapes, including known persona prefixes."""
    body = reply.strip()
    for prefix in _SURFACE_PREFIXES:
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    escaped = re.escape(item)
    direct = re.fullmatch(escaped + _DIRECT_BRIDGE + _ACCEPT.pattern + _DIRECT_TAIL, body)
    two_clause = re.fullmatch(escaped + _TWO_CLAUSE_BRIDGE + _ACCEPT.pattern + _TWO_CLAUSE_TAIL, body)
    return bool(direct or two_clause)


def _sha(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def selected_offer_contract_p4(source, logic):
    """Admit only a direct, selected Japanese acceptance of a precise item."""
    if not isinstance(source, str) or not isinstance(logic, dict):
        return None
    if not 1 <= len(source) <= 48 or not source.endswith(_SOURCE_SUFFIX):
        return None
    if _PROTECTED.search(source) or any(ch in source for ch in "「」『』\"“”'\n\r。!?！"):
        return None
    head = source[:-len(_SOURCE_SUFFIX)]
    grounding = logic.get("grounding") or {}
    if not isinstance(grounding, dict) or not str(logic.get("core_message_jp") or "").strip():
        return None
    item = grounding.get("offered_item")
    if item not in _ITEMS or not head.endswith(item):
        return None
    modifier = head[:-len(item)]
    if not _MODIFIER.fullmatch(modifier) or _PERSON.search(modifier):
        return None
    if logic.get("intent") not in {"food_offer_generic", "food_offer_sweet", "store_offer"}:
        return None
    if logic.get("surface_act") not in {"named_offer_accept", "named_offer_light_accept"}:
        return None
    if logic.get("dialogue_act") != "concrete_offer_response":
        return None
    if logic.get("scene") not in {None, "casual"} or logic.get("memory_use_expected"):
        return None
    if logic.get("required_marker_groups") or logic.get("surface_required_marker_groups"):
        return None
    m31 = logic.get("semantic_authorization_m31") or {}
    if not isinstance(m31, dict) or m31.get("surface_authority"):
        return None
    contract = {
        "schema": SCHEMA,
        "source_sha256": _sha(source),
        "selected_core_sha256": _sha(logic.get("core_message_jp")),
        "item_jp": item,
        "item_sha256": _sha(item),
        "selected_dialogue_act": "concrete_offer_response",
        "selected_surface_act": logic["surface_act"],
        "source_type": "direct_current_user_food_offer",
        "decision": "accept_already_selected",
        "raw_dialogue_persisted": False,
        "memory_write_claimed": False,
        "model_call_added": False,
    }
    # The selected action, not just its metadata, must itself be an acceptance.
    # Otherwise an inconsistent plan could acquire an affirmative surface by
    # passing through this product-only repair.
    if offer_reply_status_p4(logic["core_message_jp"], contract)["status"] != "action_preserved":
        return None
    return contract


def offer_reply_status_p4(reply, contract):
    """Finite same-item positive-action check; never a general NLU claim."""
    reply = str(reply or "")
    item = (contract or {}).get("item_jp") if isinstance(contract, dict) else None
    item_present = bool(item and item in reply)
    other_item = bool(item and any(other != item and other in reply for other in _ITEMS))
    disallowed = bool(_REPLY_DISALLOWED.search(reply) or _PERSON.search(reply))
    # A positive verb without the offered item, or in a question/negated or
    # third-person sentence, does not execute the selected acceptance.
    affirmative = bool(
        item_present and not other_item and not disallowed
        and _accepted_action_link(reply, item)
    )
    return {
        "status": "action_preserved" if affirmative else "action_mismatch",
        "item_present": item_present,
        "affirmative_acceptance": affirmative,
        "contradiction_or_unsupported_relation": disallowed or other_item,
        "reply_sha256": _sha(reply),
        "raw_reply_persisted": False,
    }


def refine_with_selected_offer_action_p4(self, reply, logic_data, user_input, memory_data=None):
    refined = _ORIGINAL_REFINE(self, reply, logic_data, user_input, memory_data=memory_data)
    contract = selected_offer_contract_p4(user_input, logic_data)
    if contract is None or self._structured_surface_required():
        return refined
    try:
        max_chars = int((logic_data.get("constraints") or {}).get("max_chars") or 28)
    except (TypeError, ValueError):
        return refined
    if not 12 <= max_chars <= 100:
        return refined
    preview = self._surface_preview(refined, max_chars=max_chars)
    status = offer_reply_status_p4(preview, contract)
    chosen = refined
    selection = "original_refine_preserved"
    if status["status"] != "action_preserved":
        alternatives = [
            *self._speech_plan_variants(reply, logic_data, user_input, memory_data=memory_data),
            str(logic_data.get("core_message_jp") or ""),
        ]
        selection = "no_eligible_existing_candidate"
        for alternative in alternatives:
            candidate = self._surface_preview(alternative, max_chars=max_chars)
            if offer_reply_status_p4(candidate, contract)["status"] == "action_preserved":
                chosen = candidate
                selection = "existing_speech_or_core_candidate"
                break
    trace = {
        "schema": SCHEMA,
        "candidate_selection": selection,
        "refined_candidate_sha256": _sha(preview),
        "returned_candidate_sha256": _sha(chosen),
        "returned_candidate_status": offer_reply_status_p4(chosen, contract)["status"],
        "raw_reply_persisted": False,
        "model_call_added": False,
    }
    logic_data[LABEL + "_candidate"] = trace
    if _CANDIDATE.get() is not None:
        _CANDIDATE.set(trace)
    return chosen


def speak_with_selected_offer_action_p4(self, user_input, logic_data, memory_data, current_psyche):
    token = _CANDIDATE.set({})
    try:
        reply = _ORIGINAL_SPEAK(self, user_input, logic_data, memory_data, current_psyche)
        candidate = _CANDIDATE.get()
        if isinstance(logic_data, dict) and isinstance(candidate, dict) and candidate.get("schema") == SCHEMA:
            logic_data[LABEL + "_candidate"] = deepcopy(candidate)
        return reply
    finally:
        _CANDIDATE.reset(token)


def materialize_selected_offer_action_surface_fidelity_p4(result, source):
    """Audit the actual post-guard utterance without changing it or memory."""
    if not isinstance(result, dict):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    contract = selected_offer_contract_p4(source, logic)
    if contract is None:
        return result
    rows = trace.get("blackboard")
    selected = trace.get("selected_plan")
    if not isinstance(rows, list) or not isinstance(selected, dict):
        return result
    selected_rows = [row for row in rows if isinstance(row, dict) and row.get("label") == "selected_plan"]
    utterance_rows = [row for row in rows if isinstance(row, dict) and row.get("label") == "utterance"]
    if len(selected_rows) != 1 or len(utterance_rows) != 1:
        return result
    selected_row = selected_rows[0].get("payload") or {}
    utterance = utterance_rows[0].get("payload") or {}
    reply = result.get("reply")
    selected_matches = bool(
        selected.get("core_message_jp") == selected_row.get("core_message_jp") == logic.get("core_message_jp")
        and selected.get("intent") == selected_row.get("intent") == logic.get("intent")
        and selected.get("surface_act") == logic.get("surface_act")
        and ("surface_act" not in selected_row or selected_row.get("surface_act") == logic.get("surface_act"))
        and selected.get("dialogue_act") == logic.get("dialogue_act")
        and ("dialogue_act" not in selected_row or selected_row.get("dialogue_act") == logic.get("dialogue_act"))
        and (selected.get("grounding") or {}).get("offered_item") == contract["item_jp"]
        and ("grounding" not in selected_row or (selected_row.get("grounding") or {}).get("offered_item") == contract["item_jp"])
        and contract["selected_core_sha256"] == _sha(selected.get("core_message_jp"))
    )
    reply_matches_utterance = bool(isinstance(reply, str) and utterance.get("reply") == reply)
    action = offer_reply_status_p4(reply, contract)
    preserved = bool(selected_matches and reply_matches_utterance and action["status"] == "action_preserved")
    candidate = logic.get(LABEL + "_candidate") or {}
    payload = {
        "schema": SCHEMA,
        "status": "visible_action_preserved" if preserved else "selected_or_visible_action_mismatch",
        "selected_plan_matches_logic": selected_matches,
        "selected_row_surface_act_observed": "surface_act" in selected_row,
        "utterance_matches_reply": reply_matches_utterance,
        "candidate_selection": candidate.get("candidate_selection", "not_observed"),
        "candidate_status": candidate.get("returned_candidate_status", "not_observed"),
        "item_present": action["item_present"],
        "affirmative_acceptance": action["affirmative_acceptance"],
        "contradiction_or_unsupported_relation": action["contradiction_or_unsupported_relation"],
        "source_sha256": contract["source_sha256"],
        "item_sha256": contract["item_sha256"],
        "final_reply_sha256": action["reply_sha256"],
        "raw_dialogue_persisted": False,
        "memory_write_claimed": False,
        "model_call_added": False,
        "claim_boundary": "finite selected direct food-offer surface contract, not open-domain semantic equivalence",
    }
    without_prior = [row for row in rows if not (isinstance(row, dict) and row.get("label") == LABEL)]
    insertion = next(
        (i + 1 for i, row in enumerate(without_prior) if isinstance(row, dict) and row.get("label") == "selected_plan"),
        len(without_prior),
    )
    without_prior.insert(insertion, {
        "stage": "verify", "label": LABEL, "payload": deepcopy(payload),
        "salience": 0.97 if preserved else 1.0,
    })
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(payload)
    logic[LABEL] = deepcopy(payload)
    return result


def emit_response_if_ready_with_selected_offer_action_p4(self, event, tick_result):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    materialize_selected_offer_action_surface_fidelity_p4(result, (event or {}).get("user_input"))
    if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
        return result
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    current = result["runtime_trace"]
    self.runtime.blackboard = deepcopy(current["blackboard"])
    sync_current_history_m41_1(result)
    if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index"):
        self.runtime.turn_traces[-1] = deepcopy(current)
    return result


def install_selected_offer_action_surface_fidelity_p4():
    """Install after the prior P4 question-evidence product chain, once."""
    global _INSTALLED, _ORIGINAL_REFINE, _ORIGINAL_SPEAK, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    import uruha_third_party_question_evidence_p4 as previous
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    if not previous._INSTALLED or UruhaBrainV4_Mac.emit_response_if_ready is not previous.emit_response_if_ready_with_third_party_question_evidence_p4:
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_REFINE = RightBrain._refine_conversational_reply
    _ORIGINAL_SPEAK = RightBrain.speak
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    RightBrain._refine_conversational_reply = refine_with_selected_offer_action_p4
    RightBrain.speak = speak_with_selected_offer_action_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_selected_offer_action_p4
    _INSTALLED = True
    return True
