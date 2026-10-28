"""Opt-in User-source authority for a bounded mixed rewrite + past-place request.

This gate certifies what a delivered User turn said, not what occurred in the
world. It deliberately does not claim to fulfil the other (rewrite) subtask.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from datetime import date
import hashlib
import json
import re
import unicodedata

import uruha_current_turn_source_role_p4 as source_role
from uruha_local_fact_answer_authority_p4 import _handed_user_sources, _protected_or_other_route


LABEL = "mixed_past_place_source_authority_p4"
SCHEMA = "uruha_mixed_past_place_source_authority_p4_v1"
PLANNER_PATH = LABEL
MAX_CORE_CHARS = 40
_INSTALLED = False
_ORIGINAL_TICK = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_ACTIVE_HISTORY_TRANSACTION = ContextVar("mixed_past_place_history_transaction_p4", default=None)

_DATE = r"(?:20\d{2}年(?:0?[1-9]|1[0-2])月(?:0?[1-9]|[12]\d|3[01])日)"
_ABS_DATE = re.compile(_DATE)
_REL_DATE = re.compile(r"一昨日|昨日")
_RECALL = re.compile(r"思い出して|教えて|覚えて")
_OWN_CHOICE = re.compile(r"(?:私|僕|俺|うち)が.{0,8}(?:選んだ|決めた).{0,20}場所")
_ASSERTION = re.compile(
    rf"私は(?P<date>{_DATE})の集合場所を(?P<value>[^。.!?？「」『』\n\r]{{1,24}})に決めた[。.]?"
)
_RETRACTION = re.compile(r"違う|間違い|訂正|撤回|じゃない|じゃなく|ではない|ではなく|なかった|やめた|変更|変えた|けど|代わり")
_UNCERTAIN = re.compile(r"かも|たぶん|多分|らしい|そうだ|かな|おそらく|聞いた|友達|先生|同僚")
_NON_NOUN_VALUE = re.compile(r"決めた|選んだ|にした|変更|変えた|から|けど|ではなく|じゃなく|[、,;；]")
_SHADOW_LABELS = frozenset({
    "personhood_action_choice_v2_13", "personhood_persona_appraisal_v2_13",
    "active_validation_strategy_v2_13", "desired_response_prediction_m18",
    "adaptive_response_dimensions_m18", "candidate_plans", "planner_ticks",
    "bdi_state", "open_loops", "memory_gravity", "internal_monologue",
    "next_user_prediction_v2_12", "bounded_slow_path_planner_m21",
    "semantic_route_outcome_m22",
})


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or "")).strip())


def _valid_date(value: str) -> bool:
    match = re.fullmatch(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", value)
    if not match:
        return False
    try:
        date(*(int(part) for part in match.groups()))
    except ValueError:
        return False
    return True


def classify_mixed_past_place_query_p4(user_input: str) -> dict:
    role = source_role.classify_current_turn_source_role_p4(user_input)
    cert = {
        "schema": SCHEMA, "eligible": False, "input_sha256": _sha(user_input),
        "source_role_act": role.get("act"), "date_anchor": None,
        "date_kind": None, "current_correction": False,
        "reason": "outside_bounded_mixed_place_request",
        "raw_dialogue_persisted": False, "private_state_truth_claimed": False,
        "model_calls_added": 0, "rewrite_subtask_fulfilled": False,
    }
    if role.get("act") != "mixed_request" or role.get("quote_role") != "rewrite_object":
        return cert
    outer = str(role.get("_outside_nfkc") or "")
    quote = str(role.get("_quote_nfkc") or "")
    if not (re.search(r"集合場所|集合先", quote)
            and _RECALL.search(outer) and _OWN_CHOICE.search(outer)):
        return cert
    dates = _ABS_DATE.findall(outer)
    relative = _REL_DATE.findall(outer)
    if len(dates) + len(relative) != 1:
        return {**cert, "reason": "date_anchor_missing_or_ambiguous"}
    anchor = (dates or relative)[0]
    if dates and not _valid_date(anchor):
        return {**cert, "reason": "invalid_absolute_date"}
    return {**cert, "eligible": True, "date_anchor": anchor,
            "date_kind": "absolute" if dates else "relative",
            "current_correction": bool(_RETRACTION.search(outer)
                                       and re.search(r"集合場所|集合先", outer)),
            "reason": "bounded_mixed_past_place_request"}


def _direct_choice(user_text: str, date_anchor: str) -> str | None:
    raw = str(user_text or "")
    text = _norm(raw)
    if (not text or len(text) > 120 or any(mark in raw for mark in (
            "「", "」", "『", "』", '"', "'", "?", "？", "|", "\n", "\r", "User:", "Uruha:", "->"))
            or _RETRACTION.search(text) or _UNCERTAIN.search(text)):
        return None
    match = _ASSERTION.fullmatch(text)
    if not match or match.group("date") != date_anchor:
        return None
    value = match.group("value").strip()
    if (not value or _RETRACTION.search(value) or _UNCERTAIN.search(value)
            or _NON_NOUN_VALUE.search(value)
            or re.search(r"\d{4}年|集合場所|認証|暗証|パスワード", value)):
        return None
    return value


def _validated_user_sources(memory_data: dict | None) -> tuple[list[dict], dict]:
    """Fail closed on malformed or duplicate provenance before legacy parsing."""
    memory_data = memory_data if isinstance(memory_data, dict) else {}
    provenance = memory_data.get("memory_provenance") or {}
    if not isinstance(provenance, dict):
        return [], {"source_transport_status": "malformed_provenance"}
    passed = provenance.get("passed_to_leftbrain") or []
    ids = provenance.get("passed_to_leftbrain_trace_ids") or []
    if (not isinstance(passed, list) or not isinstance(ids, list)
            or any(not isinstance(value, str) for value in ids)):
        return [], {"source_transport_status": "malformed_provenance"}
    seen = {}
    for row in passed:
        if not isinstance(row, dict):
            continue
        trace_id = row.get("trace_id")
        if not isinstance(trace_id, str):
            continue
        identity = tuple(row.get(key) for key in (
            "source", "collection_name", "memory_id", "text",
            "episode_record_kind", "episode_record_kind_origin",
        ))
        if trace_id in seen and seen[trace_id] != identity:
            return [], {"source_transport_status": "conflicting_duplicate_trace_id"}
        seen[trace_id] = identity
    try:
        sources, audit = _handed_user_sources(memory_data)
    except (TypeError, ValueError, KeyError, AttributeError):
        return [], {"source_transport_status": "malformed_provenance"}
    return sources, {**audit, "source_transport_status": "validated"}


def build_mixed_past_place_certificate_p4(user_input: str, memory_data: dict | None) -> dict:
    query = classify_mixed_past_place_query_p4(user_input)
    if not query["eligible"]:
        return {**query, "status": "ineligible"}
    sources, audit = _validated_user_sources(memory_data)
    matches = []
    retracted = False
    if query["date_kind"] == "absolute":
        for source in sources:
            text = _norm(source["user"])
            dates_in_source = set(_ABS_DATE.findall(text))
            same_or_unstated_date = (
                query["date_anchor"] in dates_in_source or not dates_in_source
            )
            if (same_or_unstated_date and re.search(r"集合場所|集合先", text)
                    and _RETRACTION.search(text)
                    and not any(marker in text for marker in ("「", "」", "『", "』", '"'))):
                retracted = True
            value = _direct_choice(source["user"], query["date_anchor"])
            if value is not None:
                matches.append({**source, "value": value})
    values = sorted({row["value"] for row in matches})
    if audit["source_transport_status"] != "validated":
        status = "source_transport_ambiguous"
    elif query["current_correction"]:
        status = "current_turn_change_ambiguous"
    elif query["date_kind"] == "relative":
        status = "relative_time_unverifiable"
    elif retracted:
        status = "source_retracted_or_ambiguous"
    elif len(values) > 1:
        status = "conflicting_user_sources"
    elif len(values) == 1:
        status = "source_backed"
    else:
        status = "no_admitted_user_source"
    chosen = matches[-1] if status == "source_backed" else None
    value = chosen["value"] if chosen else None
    reply = (
        f"{query['date_anchor']}の集合場所は{value}にしたって言ってたな。"
        if chosen else "その日の集合場所は、今ある会話だけじゃ分からないな。"
    )
    if len(reply) > MAX_CORE_CHARS:
        status, chosen, value = "source_value_outside_surface_budget", None, None
        reply = "ん、今は正確に答えられないな。"
    cert = {
        **query, **audit, "status": status, "selected_status": "pending",
        "admitted_source_count": len(matches), "distinct_value_count": len(values),
        "admitted_value": value, "source_channel": chosen["source_channel"] if chosen else None,
        "source_trace_id": chosen["trace_id"] if chosen else None,
        "source_memory_id": (chosen["memory_id"] if chosen and chosen["source_channel"] == "direct_episode" else None),
        "source_memory_id_status": (
            "typed_episode" if chosen and chosen["source_channel"] == "direct_episode"
            else "recent_turn_episode_id_not_certified" if chosen else "none"
        ),
        "authorized_reply": reply, "authorized_reply_sha256": _sha(reply),
        "claim_boundary": "User said this; world truth and rewrite quality not certified",
        "bounded_source_value_in_trace": bool(value),
    }
    cert["binding_sha256"] = _sha(json.dumps({
        key: cert.get(key) for key in (
            "input_sha256", "date_anchor", "date_kind", "status", "admitted_value",
            "source_channel", "source_trace_id", "authorized_reply_sha256",
        )
    }, sort_keys=True, ensure_ascii=False))
    return cert


def _has_competing_authority(logic: dict, route_info: dict, right_brain=None) -> bool:
    return bool(
        _protected_or_other_route(logic, route_info, right_brain)
        or (logic.get("semantic_authorization_m31") or {}).get("surface_authority") is True
        or (logic.get("semantic_commit_repair_m32") or {}).get("surface_authority") is True
    )


def cognitive_tick_with_mixed_past_place_source_authority_p4(self, event):
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    user_input = str((event or {}).get("user_input") or "")
    cert = build_mixed_past_place_certificate_p4(user_input, (event or {}).get("memory_data"))
    if not cert["eligible"]:
        return tick
    logic = tick.get("logic") or {}
    if _has_competing_authority(logic, tick.get("route_info") or {}, getattr(self, "right_brain", None)):
        return tick
    prior = {"intent": str(logic.get("intent") or ""),
             "planner_path": str(logic.get("planner_path") or ""),
             "selected_core_sha256": _sha(logic.get("core_message_jp"))}
    source_backed = bool(cert["source_trace_id"])
    source_anchor = ({
        "kind": "source_bound_past_place", "source": (
            "episode" if cert["source_channel"] == "direct_episode" else "recent_turn"
        ), "trace_id": cert["source_trace_id"], "memory_id": cert["source_memory_id"],
        "provenance_channel": cert["source_channel"],
        "jp_anchor": cert["admitted_value"], "terms": [cert["admitted_value"]],
        "relevance": 1.0,
    } if source_backed else {})
    core = cert["authorized_reply"]
    logic.update({
        "reply_goal": "直接の User 発話で確かめられる集合場所だけ答える",
        "jp_summary": core, "core_message_jp": core,
        "planner_path": PLANNER_PATH, "candidate_label": LABEL,
        "response_mode": "direct_answer", "surface_act": "plain_reply",
        "dialogue_act": "direct_chat_answer", "payload_level": "low",
        "grounding": {}, "memory_anchor": source_anchor,
        "memory_relevance": 1.0 if source_backed else 0.0,
        "memory_relevance_label": "high" if source_backed else "none",
        "memory_speakability": "explicit_ok" if source_backed else "no_memory",
        "memory_speakability_reason": "direct_User_source_certificate_controls_past_fact",
        "memory_gravity": 1.0 if source_backed else 0.0,
        "memory_use_expected": source_backed,
        "user_belief": "以前に選んだ集合場所を聞いている。",
        "my_hidden_knowledge": "直接の User 発話以外から過去の場所を断定しない。",
        "user_expectation": "根拠のある短い返答。",
        "internal_monologue": "", "bayes_candidates": [],
        "planner_tick_count": 0, "self_correction_applied": False,
        "planner_repair_applied": False, "planner_repair_success": False,
    })
    for key in ("human_speech_plan", "reference_subject_jp", "planner_tick_trace",
                "planner_detected_issues", "planner_unresolved_issues"):
        logic.pop(key, None)
    for key in ("bounded_slow_path_m21", "semantic_route_m22"):
        old = logic.get(key)
        if isinstance(old, dict):
            old["pre_gate_plan_status"] = "shadowed_not_selected"
            old["post_gate_selected_plan_authority"] = LABEL
            if key == "bounded_slow_path_m21":
                old["observed_compute_cost_retained"] = True
    cert = {**cert, "selected_status": "source_authorized_plan_selected",
            "pre_gate_selected_plan": prior, "pre_gate_cognitive_nodes_retained_as_shadow": True}
    logic[LABEL] = deepcopy(cert)
    tick["logic"] = logic
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        runtime.active_goal = logic["reply_goal"]
        runtime.last_internal_monologue = ""
        runtime.last_candidates = []
        runtime.planner_tick_trace = []
        runtime.planner_tick_count = 0
        runtime.self_correction_applied = False
        personhood = getattr(runtime, "last_personhood_loop", None)
        if isinstance(personhood, dict):
            personhood = deepcopy(personhood)
            choice = personhood.get("action_choice")
            if isinstance(choice, dict):
                choice["post_gate_status"] = "shadowed_not_selected"
                choice["post_gate_selected_plan_authority"] = LABEL
            runtime.last_personhood_loop = personhood
        logic["personhood_action_context_v2_13"] = {
            "status": "pre_gate_action_shadowed",
            "post_gate_selected_plan_authority": LABEL,
            "selected_intent": str(logic.get("intent") or ""),
        }
        if hasattr(self, "_derive_open_loops"):
            runtime.open_loops = self._derive_open_loops(logic)
            runtime.latent_goal_stack = deepcopy(runtime.open_loops)
        if hasattr(self, "_infer_focus_label"):
            runtime.current_focus = self._infer_focus_label(
                user_input, (event or {}).get("memory_data") or {}, logic,
            )
        if hasattr(self, "left_brain") and hasattr(runtime, "set_prediction"):
            prediction = self.left_brain.predict_next_user_signal(
                logic, user_input, (event or {}).get("psyche_before") or {},
                (event or {}).get("memory_data") or {}, mode="reactive",
            )
            logic["prediction_hint"] = prediction
            runtime.set_prediction(
                prediction.get("expected_intent", ""), prediction.get("expected_valence", 0.0),
                source_plan_intent=prediction.get("source_plan_intent", logic.get("intent", "")),
            )
        runtime.last_selected_plan = self._plan_trace_summary(logic)
        for row in getattr(runtime, "blackboard", []):
            if row.get("label") == "selected_plan":
                row["payload"] = deepcopy(runtime.last_selected_plan)
                row["payload"]["post_gate_selected_plan_authority"] = LABEL
            elif row.get("label") in _SHADOW_LABELS and isinstance(row.get("payload"), dict):
                row["payload"] = {**row["payload"],
                                  "post_gate_plan_status": "shadowed_not_selected",
                                  "post_gate_selected_plan_authority": LABEL}
                if row.get("label") == "bounded_slow_path_planner_m21":
                    row["payload"]["observed_compute_cost_retained"] = True
        index = next((i for i, row in enumerate(runtime.blackboard)
                      if row.get("label") == "selected_plan"), len(runtime.blackboard))
        runtime.blackboard.insert(index, {
            "stage": "evidence", "label": LABEL, "payload": deepcopy(cert), "salience": 1.0,
        })
    return tick


def _history_snapshot(right_brain, logic_data: dict) -> dict | None:
    history = getattr(right_brain, "history", None)
    names = (
        "reply_variant_counts", "intent_variant_counts",
        "normalized_reply_counts", "intent_normalized_counts",
    )
    counters = {name: getattr(right_brain, name, None) for name in names}
    if (not isinstance(history, list)
            or any(not isinstance(counter, dict) for counter in counters.values())
            or not callable(getattr(right_brain, "_remember_turn", None))):
        return None
    return {
        "right_brain": right_brain, "logic_id": id(logic_data),
        "history": deepcopy(history),
        "counters": {name: deepcopy(counter) for name, counter in counters.items()},
    }


def _commit_visible_history(self, logic_data: dict, selected: str) -> str:
    """Roll back all pre-guard speak attempts, then record one delivered reply."""
    tx = _ACTIVE_HISTORY_TRANSACTION.get()
    if (not isinstance(tx, dict) or tx.get("right_brain") is not self
            or tx.get("logic_id") != id(logic_data)):
        return "transaction_context_unavailable"
    history = getattr(self, "history", None)
    if not isinstance(history, list):
        return "history_unavailable"
    counters = {name: getattr(self, name, None) for name in tx["counters"]}
    if any(not isinstance(counter, dict) for counter in counters.values()):
        return "counter_receipt_unavailable"
    history[:] = deepcopy(tx["history"])
    for name, counter in counters.items():
        counter.clear()
        counter.update(deepcopy(tx["counters"][name]))
    self._remember_turn(
        str(logic_data.get("jp_summary") or ""), selected,
        str(logic_data.get("intent") or "chat"),
    )
    return "pre_guard_speech_rolled_back_final_visible_committed"


def emit_response_with_mixed_past_place_source_authority_p4(self, event, tick_result):
    logic = (tick_result or {}).get("logic") or {}
    cert = logic.get(LABEL) or {}
    tx = (
        _history_snapshot(getattr(self, "right_brain", None), logic)
        if cert.get("selected_status") == "source_authorized_plan_selected" else None
    )
    token = _ACTIVE_HISTORY_TRANSACTION.set(tx)
    try:
        return _ORIGINAL_EMIT(self, event, tick_result)
    finally:
        _ACTIVE_HISTORY_TRANSACTION.reset(token)


def visible_guard_with_mixed_past_place_source_authority_p4(
    self, reply, logic_data, user_input="", memory_data=None,
):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data,
    )
    if not isinstance(logic_data, dict):
        return visible
    bound = logic_data.get(LABEL) or {}
    if bound.get("schema") != SCHEMA or bound.get("selected_status") != "source_authorized_plan_selected":
        return visible
    fresh = build_mixed_past_place_certificate_p4(user_input, memory_data)
    integrity = (
        fresh.get("binding_sha256") == bound.get("binding_sha256")
        and logic_data.get("planner_path") == PLANNER_PATH
        and logic_data.get("core_message_jp") == fresh.get("authorized_reply")
        and logic_data.get("surface_act") == "plain_reply"
        and not _has_competing_authority(logic_data, {}, self)
    )
    selected = fresh.get("authorized_reply") if integrity else "ん、今は確かめられないな。"
    checker = getattr(self, "_user_visible_language_rejection_reasons", None)
    try:
        reasons = checker(selected, user_input=user_input, logic_data=logic_data,
                          memory_data=memory_data) if callable(checker) else ["checker_missing"]
    except Exception:
        reasons = ["checker_exception"]
    if reasons:
        selected = "ん、もう一回だけ聞かせて。"
    receipt = deepcopy(bound)
    receipt["visible_surface_status"] = "matched" if integrity and not reasons else "failed_closed"
    receipt["visible_failure_reason"] = (
        None if integrity and not reasons else
        "source_or_plan_integrity_mismatch" if not integrity else "language_guard_rejected"
    )
    receipt["pre_authority_surface_sha256"] = _sha(visible)
    receipt["final_visible_surface_sha256"] = _sha(selected)
    receipt["final_visible_surface_matches_contract"] = selected == fresh.get("authorized_reply")
    receipt["right_brain_history_surface_status"] = _commit_visible_history(self, logic_data, selected)
    logic_data[LABEL] = receipt
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    original_reply = str(guard.get("original_reply") or reply or "")
    guard.update({
        "changed": selected != original_reply,
        "pre_mixed_place_repair_action": guard.get("repair_action"),
        "repair_action": "mixed_past_place_source_authority_" + receipt["visible_surface_status"],
        "final_rejection_reasons": reasons,
        "final_reply": selected, "final_reply_sha256": _sha(selected),
    })
    logic_data["visible_language_guard"] = guard
    return selected


def materialize_mixed_past_place_source_authority_p4(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    cert = logic.get(LABEL) or {}
    trace = result.get("runtime_trace")
    if cert.get("schema") != SCHEMA or not isinstance(trace, dict):
        return result
    final = str(result.get("reply") or "").strip()
    receipt = deepcopy(cert)
    receipt["final_visible_surface_sha256"] = _sha(final)
    receipt["final_visible_surface_matches_contract"] = (
        receipt.get("visible_surface_status") == "matched"
        and final == receipt.get("authorized_reply")
    )
    if not receipt["final_visible_surface_matches_contract"] and receipt.get("visible_surface_status") == "matched":
        receipt["visible_surface_status"] = "post_guard_surface_mismatch"
    logic[LABEL] = receipt
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), len(rows))
    rows.insert(index, {"stage": "evidence", "label": LABEL,
                        "payload": deepcopy(receipt), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(receipt)
    return result


def install_mixed_past_place_source_authority_p4() -> bool:
    """Install outside the existing rewrite chain in the opt-in product entry."""
    global _INSTALLED, _ORIGINAL_TICK, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_mixed_past_place_source_authority_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_mixed_past_place_source_authority_p4

    def finish(self, result):
        if not isinstance(result, dict) or (result.get("logic") or {}).get(LABEL, {}).get("schema") != SCHEMA:
            return result
        materialize_mixed_past_place_source_authority_p4(result)
        trace = result.get("runtime_trace")
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (getattr(runtime, "turn_traces", None)
                    and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")):
                runtime.turn_traces[-1] = deepcopy(trace)
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, emit_response_with_mixed_past_place_source_authority_p4(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "PLANNER_PATH", "classify_mixed_past_place_query_p4",
    "build_mixed_past_place_certificate_p4",
    "cognitive_tick_with_mixed_past_place_source_authority_p4",
    "emit_response_with_mixed_past_place_source_authority_p4",
    "visible_guard_with_mixed_past_place_source_authority_p4",
    "materialize_mixed_past_place_source_authority_p4",
    "install_mixed_past_place_source_authority_p4",
]
