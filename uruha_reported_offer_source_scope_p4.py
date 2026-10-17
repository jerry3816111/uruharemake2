"""Bounded product authority for a *reported* third-party food offer.

The speaker/addressee inference is licensed only by one complete Japanese
reported-speech sentence.  It is not a general quote parser, a claim that the
event happened, or authority to write a preference into long-term memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import uruha_leftbrain_rules as legacy_rules
import uruha_current_statement_source_authority_p4 as statement_authority
import uruha_selected_offer_action_surface_fidelity_p4 as offer_surface
import uruha_third_party_question_evidence_p4 as question_evidence


LABEL = "reported_offer_source_scope_p4"
SCHEMA = "uruha_reported_offer_source_scope_p4_v1"
_MAX_SOURCE_CHARS = 72
_REPORT = re.compile(
    r"(?P<role>友達|友人|母|父|兄|姉|弟|妹|祖母|祖父|先生|先輩|後輩|同僚)に"
    r"(?P<quoted>「[^「」『』\n\r]{1,42}」|『[^「」『』\n\r]{1,42}』)"
    r"(?P<verb>って言われた|と言われた|と聞かれた)。(?!.)"
)
_ACCEPTANCE = re.compile(r"(?:一口|少し|ちょっと).{0,8}(?:ほしい|欲しい|もらう|食べる|飲む|くれ)")
_PREFIXES = ("", "ん、", "まあ、", "いや、", "てか、", "先に、", "普通に、")

_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_REFINE = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _sha(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _reproducible_prior_seed(source):
    """Independent finite baseline: the exact legacy direct-daily offer branch."""
    return legacy_rules.get_direct_daily_query_plan(source, [])


def _admission_digest(source, quote, role, item, prior_intent, prior_surface, prior_core):
    parts = [
        SCHEMA, _sha(source)[:32], _sha(quote)[:32], role, item,
        prior_intent, prior_surface, _sha(prior_core)[:32],
    ]
    return _sha(json.dumps(parts, ensure_ascii=False, separators=(",", ":")))[:32]


def _parse_reported_offer(source):
    """Admit a whole one-sentence report, never an embedded/continued quote."""
    if (
        not isinstance(source, str)
        or not 1 <= len(source) <= _MAX_SOURCE_CHARS
        or statement_authority._PROTECTED_CUE.search(source)
    ):
        return None
    match = _REPORT.fullmatch(source)
    if match is None:
        return None
    quote = match.group("quoted")
    utterance = quote[1:-1]
    if not utterance.endswith("、一口いる？") or utterance.count("？") != 1:
        return None
    head = utterance[:-len("、一口いる？")]
    item = next((candidate for candidate in offer_surface._ITEMS if head.endswith(candidate)), None)
    if item is None:
        return None
    modifier = head[:-len(item)]
    if not offer_surface._MODIFIER.fullmatch(modifier):
        return None
    if offer_surface._PERSON.search(modifier) or offer_surface._PROTECTED.search(utterance):
        return None
    role = match.group("role")
    if role not in statement_authority._THIRD_PARTY_ROLES:
        return None
    return {"role": role, "item": item, "quoted": quote, "verb": match.group("verb")}


def reported_offer_certificate_p4(source, selected_seed):
    """Certify a source change only after the legacy plan chose an offer act."""
    parsed = _parse_reported_offer(source)
    if parsed is None or not isinstance(selected_seed, dict):
        return None
    # The frozen parent chain must have actually selected the reproducible
    # direct-daily rule, not merely carry an offer-like label.  This exact
    # source-bound baseline can be recomputed at final audit without memory,
    # model calls, or a mutable ContextVar.
    baseline = _reproducible_prior_seed(source)
    if not isinstance(baseline, dict) or any(
        selected_seed.get(key) != baseline.get(key)
        for key in ("intent", "scene", "surface_act", "core_message_jp")
    ) or (selected_seed.get("grounding") or {}).get("offered_item") != (
        baseline.get("grounding") or {}
    ).get("offered_item"):
        return None
    intent = selected_seed.get("intent")
    if not (
        intent in {"food_offer_generic", "food_offer_sweet"}
        and selected_seed.get("scene") == "casual"
        and selected_seed.get("surface_act") in {"named_offer_accept", "named_offer_light_accept"}
        and (selected_seed.get("grounding") or {}).get("offered_item") == parsed["item"]
        and isinstance(selected_seed.get("core_message_jp"), str)
    ):
        return None
    return {
        "schema": SCHEMA,
        "status": "reported_source_admitted",
        "source_sha256": _sha(source),
        "quoted_span_sha256": _sha(parsed["quoted"]),
        "reported_speaker_role": parsed["role"],
        "reported_speaker_role_sha256": _sha(parsed["role"]),
        "reported_item_sha256": _sha(parsed["item"]),
        "reported_verb": parsed["verb"],
        "addressee": "reported_user",
        "prior_selected_intent": intent,
        "prior_selected_intent_sha256": _sha(intent),
        "prior_selected_surface_act": selected_seed["surface_act"],
        "prior_selected_core_sha256": _sha(selected_seed["core_message_jp"]),
        "admission_sha32": _admission_digest(
            source, parsed["quoted"], parsed["role"], parsed["item"],
            intent, selected_seed["surface_act"], selected_seed["core_message_jp"],
        ),
        "event_truth": "unknown_user_report_only",
        "other_requests_outside_quote": "none_in_bounded_single_sentence",
        "profile_write_authority": "none",
        "memory_write_claimed": False,
        "model_call_added": False,
        "raw_dialogue_persisted": False,
    }


def reported_offer_plan_p4(source, selected_seed):
    certificate = reported_offer_certificate_p4(source, selected_seed)
    parsed = _parse_reported_offer(source)
    if certificate is None or parsed is None:
        return None
    role, item = parsed["role"], parsed["item"]
    core = f"{role}に{item}を一口勧められたのか。で、なんて返した？"
    # M21's deterministic normalizer has a 40-character core boundary.
    if len(core) > 40:
        return None
    return {
        "intent": "chat",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "ユーザーが第三者からの食べ物の誘いを報告している",
        "reply_goal": "本人が誘ったと誤認せず、ユーザーの返答を軽く聞く",
        "jp_summary": f"ユーザーは{role}に{item}を一口勧められたと報告している。",
        "core_message_jp": core,
        "stance": {"warmth": 0.32, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.18,
        "premise_check": "accept",
        "self_check": False,
        "subjective_note_jp": "引文はユーザーへの第三者の発話で、うちへの誘いではない",
        "hidden_intent": "plain_request",
        "surface_act": "plain_reply",
        "grounding": {
            "reported_role": role,
            "reported_item": item,
            "prior_selected_intent": certificate["prior_selected_intent"],
            # _normalize_plan limits grounding keys/values to 24/40 chars.
            "prior_intent_sha32": certificate["prior_selected_intent_sha256"][:32],
            "prior_surface_act": certificate["prior_selected_surface_act"],
            "prior_core_sha32": certificate["prior_selected_core_sha256"][:32],
            "source_sha32": certificate["source_sha256"][:32],
            "quoted_sha32": certificate["quoted_span_sha256"][:32],
            "admission_sha32": certificate["admission_sha32"],
        },
        "payload_level": "medium",
        "planner_path": LABEL,
        LABEL: deepcopy(certificate),
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
        "must_avoid": ["ほしい", "もらう", "知ってた", "覚えてる", "うちも好き"],
    }


def rule_plan_with_reported_offer_scope_p4(self, user_input, current_psyche, memory_data=None):
    original = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    return reported_offer_plan_p4(user_input, original) or original


def _surface_status(reply, expected_core):
    """Finite final form: known discourse prefix plus exact source-faithful core."""
    return bool(
        isinstance(reply, str)
        and isinstance(expected_core, str)
        and not _ACCEPTANCE.search(reply)
        and any(reply == prefix + expected_core for prefix in _PREFIXES)
    )


def _direct_acceptance_status(reply, item, expected_core):
    """True/False only for the finite positive/faithful forms; else unknown."""
    if _surface_status(reply, expected_core):
        return False
    if isinstance(reply, str) and item in reply and (
        offer_surface._accepted_action_link(reply, item) or _ACCEPTANCE.search(reply)
    ):
        return True
    return None


def refine_with_reported_offer_scope_p4(self, reply, logic_data, user_input, memory_data=None):
    refined = _ORIGINAL_REFINE(self, reply, logic_data, user_input, memory_data=memory_data)
    if not isinstance(logic_data, dict) or logic_data.get("planner_path") != LABEL:
        return refined
    parsed = _parse_reported_offer(user_input)
    if parsed is None or self._structured_surface_required():
        return refined
    expected_core = f"{parsed['role']}に{parsed['item']}を一口勧められたのか。で、なんて返した？"
    if not (
        logic_data.get("intent") == "chat"
        and logic_data.get("scene") == "casual"
        and logic_data.get("surface_act") == "plain_reply"
        and logic_data.get("core_message_jp") == expected_core
        and (logic_data.get("grounding") or {}).get("reported_item") == parsed["item"]
    ):
        return refined
    try:
        max_chars = int((logic_data.get("constraints") or {}).get("max_chars") or 44)
    except (TypeError, ValueError):
        return refined
    if not len(expected_core) <= max_chars <= 100:
        return refined
    preview = self._surface_preview(refined, max_chars=max_chars)
    chosen = refined if _surface_status(preview, expected_core) else expected_core
    logic_data[LABEL + "_candidate"] = {
        "schema": SCHEMA,
        "selection": "original_refine_preserved" if chosen == refined else "existing_selected_core_candidate",
        "returned_candidate_sha256": _sha(chosen),
        "returned_candidate_source_faithful": _surface_status(chosen, expected_core),
        "model_call_added": False,
    }
    return chosen


def materialize_reported_offer_scope_p4(result, source):
    """Audit actual selected/uttered content; never create a success from absence."""
    if not isinstance(result, dict) or not isinstance(source, str):
        return result
    parsed = _parse_reported_offer(source)
    logic, trace = result.get("logic"), result.get("runtime_trace")
    if parsed is None or not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    if logic.get("planner_path") != LABEL:
        return result
    rows, selected = trace.get("blackboard"), trace.get("selected_plan")
    if not isinstance(rows, list) or not isinstance(selected, dict):
        return result
    selected_rows = [row for row in rows if isinstance(row, dict) and row.get("label") == "selected_plan"]
    utterance_rows = [row for row in rows if isinstance(row, dict) and row.get("label") == "utterance"]
    if len(selected_rows) != 1 or len(utterance_rows) != 1:
        return result
    selected_row = selected_rows[0].get("payload")
    utterance = utterance_rows[0].get("payload")
    if not isinstance(selected_row, dict) or not isinstance(utterance, dict):
        return result
    role, item = parsed["role"], parsed["item"]
    expected_core = f"{role}に{item}を一口勧められたのか。で、なんて返した？"
    grounding = logic.get("grounding") or {}
    baseline = _reproducible_prior_seed(source)
    admission = reported_offer_certificate_p4(source, baseline)
    prior_intent = grounding.get("prior_selected_intent") if isinstance(grounding, dict) else None
    admission_matches = bool(
        isinstance(admission, dict)
        and isinstance(grounding, dict)
        and grounding.get("reported_role") == role
        and grounding.get("reported_item") == item
        and grounding.get("prior_selected_intent") == admission["prior_selected_intent"]
        and grounding.get("prior_intent_sha32") == admission["prior_selected_intent_sha256"][:32]
        and grounding.get("prior_surface_act") == admission["prior_selected_surface_act"]
        and grounding.get("prior_core_sha32") == admission["prior_selected_core_sha256"][:32]
        and grounding.get("source_sha32") == admission["source_sha256"][:32]
        and grounding.get("quoted_sha32") == admission["quoted_span_sha256"][:32]
        and grounding.get("admission_sha32") == admission["admission_sha32"]
    )
    # The selected_plan blackboard summary intentionally omits some plan
    # fields.  Missing fields are observed as missing, never invented there;
    # the complete selected_plan and logic still have to agree on the act.
    optional_row_fields_match = bool(
        ("surface_act" not in selected_row or selected_row["surface_act"] == "plain_reply")
        and ("dialogue_act" not in selected_row or selected_row["dialogue_act"] == "direct_chat_answer")
        and ("grounding" not in selected_row or selected_row["grounding"] == grounding)
    )
    route = logic.get("bounded_slow_path_m21") or {}
    selected_matches = bool(
        logic.get("intent") == selected.get("intent") == selected_row.get("intent") == "chat"
        and logic.get("scene") == selected.get("scene") == selected_row.get("scene") == "casual"
        and logic.get("surface_act") == selected.get("surface_act") == "plain_reply"
        and logic.get("core_message_jp") == selected.get("core_message_jp") == selected_row.get("core_message_jp") == expected_core
        and logic.get("dialogue_act") == selected.get("dialogue_act") == "direct_chat_answer"
        and selected.get("grounding") == grounding
        and optional_row_fields_match
        and admission_matches
        and route.get("route") == "deterministic_rule_plan"
        and route.get("model_call_attempted") is False
    )
    final_reply = result.get("reply")
    utterance_matches = isinstance(final_reply, str) and utterance.get("reply") == final_reply
    final_faithful = _surface_status(final_reply, expected_core)
    preserved = bool(selected_matches and utterance_matches and final_faithful)
    certificate = {
        "schema": SCHEMA,
        "status": "visible_report_preserved" if preserved else "selected_or_visible_mismatch",
        "source_scope": "reported_third_party_offer_to_user",
        "reported_speaker_role": role,
        "addressee": "reported_user",
        "prior_selected_intent": prior_intent,
        "prior_selected_intent_sha256": _sha(prior_intent),
        "prior_selected_core_sha256": admission.get("prior_selected_core_sha256") if admission else None,
        "admission_proof_matches": admission_matches,
        "admission_sha32": grounding.get("admission_sha32") if isinstance(grounding, dict) else None,
        "selected_act": logic.get("surface_act"),
        "selected_plan_matches_logic": selected_matches,
        "selected_row_surface_act_observed": "surface_act" in selected_row,
        "selected_row_dialogue_act_observed": "dialogue_act" in selected_row,
        "selected_row_grounding_observed": "grounding" in selected_row,
        "utterance_matches_reply": utterance_matches,
        "final_report_faithful": final_faithful,
        "final_direct_acceptance": _direct_acceptance_status(final_reply, item, expected_core),
        "direct_acceptance_check_scope": "finite; null means unresolved",
        "browser_bubble_observed": False,
        "source_sha256": _sha(source),
        "quoted_span_sha256": _sha(parsed["quoted"]),
        "reported_item_sha256": _sha(item),
        "final_reply_sha256": _sha(final_reply),
        "candidate_selection": (logic.get(LABEL + "_candidate") or {}).get("selection", "not_observed"),
        "event_truth": "unknown_user_report_only",
        "profile_write_authority": "none",
        "memory_write_claimed": False,
        "model_call_added": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "finite Japanese reported-offer source scope; not open-domain pragmatic understanding",
    }
    without_prior = [row for row in rows if not (isinstance(row, dict) and row.get("label") == LABEL)]
    index = next((i + 1 for i, row in enumerate(without_prior) if isinstance(row, dict) and row.get("label") == "selected_plan"), len(without_prior))
    without_prior.insert(index, {
        "stage": "verify", "label": LABEL, "payload": deepcopy(certificate),
        "salience": 0.97 if preserved else 1.0,
    })
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(certificate)
    logic[LABEL] = deepcopy(certificate)
    return result


def _finish(self, result, source):
    materialize_reported_offer_scope_p4(result, source)
    if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
        return result
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    current = result["runtime_trace"]
    self.runtime.last_selected_plan = deepcopy(current["selected_plan"])
    self.runtime.blackboard = deepcopy(current["blackboard"])
    snapshot = result.get("runtime_state")
    if isinstance(snapshot, dict):
        snapshot["last_selected_plan"] = deepcopy(current["selected_plan"])
    sync_current_history_m41_1(result)
    if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index"):
        self.runtime.turn_traces[-1] = deepcopy(current)
    return result


def run_turn_debug_with_reported_offer_scope_p4(self, user_input, input_context=None):
    result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    return _finish(self, result, user_input)


def emit_response_if_ready_with_reported_offer_scope_p4(self, event, tick_result):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _finish(self, result, (event or {}).get("user_input"))


def install_reported_offer_source_scope_p4():
    """Install after the frozen selected-offer product chain, once."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_REFINE, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac

    if not (
        question_evidence._INSTALLED
        and offer_surface._INSTALLED
        and LeftBrain._rule_based_plan is question_evidence.rule_plan_with_third_party_question_evidence_p4
        and RightBrain._refine_conversational_reply is offer_surface.refine_with_selected_offer_action_p4
        and UruhaBrainV4_Mac.run_turn_debug is question_evidence.run_turn_debug_with_third_party_question_evidence_p4
        and UruhaBrainV4_Mac.emit_response_if_ready is offer_surface.emit_response_if_ready_with_selected_offer_action_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_REFINE = RightBrain._refine_conversational_reply
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_reported_offer_scope_p4
    RightBrain._refine_conversational_reply = refine_with_reported_offer_scope_p4
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_reported_offer_scope_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_reported_offer_scope_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "reported_offer_certificate_p4", "reported_offer_plan_p4",
    "materialize_reported_offer_scope_p4", "install_reported_offer_source_scope_p4",
]
