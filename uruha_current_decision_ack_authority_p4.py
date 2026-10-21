"""Opt-in, current-event authority for a reported User place decision.

This is an acknowledgment of what the current User said, not an assertion that
the location is now a settled world fact.  Selected reports bypass automatic
factive profile extraction; the model's M31/M32 paraphrase is not evidence.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from datetime import date
import hashlib
import json
import re
import unicodedata
import uuid

import uruha_local_fact_answer_authority_p4 as prior_gate


LABEL = "current_user_decision_ack_authority_p4"
SCHEMA = "uruha_current_user_decision_ack_authority_p4_v1"
PLANNER_PATH = LABEL
MAX_REPLY_CHARS = 88
_INSTALLED = False
_ORIGINAL_INGEST = None
_ORIGINAL_TICK = None
_ORIGINAL_GUARD = None
_ORIGINAL_POST_CHECK = None
_ORIGINAL_EMIT = None
_ORIGINAL_RUN = None
_ORIGINAL_PROFILE_REMEMBER = None
_ACTIVE_TURN = ContextVar("current_user_decision_ack_turn_p4", default=None)

_DECISION = re.compile(
    r"(?P<correction>訂正[、,])?私は"
    r"(?P<year>[0-9]{4})年(?P<month>[0-9]{1,2})月(?P<day>[0-9]{1,2})日に"
    r"(?P<subject>[^\n\r。！？!?「」『』“”\"']{2,62}場所)を"
    r"(?P<place>[^\n\r。！？!?「」『』“”\"']{1,36})に決めた。?"
)
_UNSUPPORTED = re.compile(
    r"かも|かもしれ|らしい|たぶん|多分|おそらく|もし|仮に|例えば|"
    r"言った|言って|聞いた|教わった|引用|メモ|友人|友達|先生|同僚|"
    r"違う|じゃない|ではない|しなかった|決めてない|疑問|"
    r"うるは|一ノ瀬|User:|Uruha:|[\\/|;；:]"
)
_SENSITIVE = re.compile(
    r"パスワード|パスコード|暗証番号|認証コード|合言葉|住所|電話番号|口座|秘密|"
    r"鍵|カギ|キー|財布|現金|貴重品|隠す|隠し|自殺|自傷|死にたい|"
    r"殺|銃|爆弾|薬物|性的|性行為|裸|虐待|暴力"
)
_SHADOW_LABELS = frozenset({
    "personhood_action_choice_v2_13", "personhood_persona_appraisal_v2_13",
    "active_validation_strategy_v2_13", "desired_response_prediction_m18",
    "adaptive_response_dimensions_m18", "candidate_plans", "planner_ticks",
    "bdi_state", "open_loops", "memory_gravity", "internal_monologue",
    "bounded_slow_path_planner_m21", "semantic_route_outcome_m22",
})


class CurrentDecisionAckDeliveryError(RuntimeError):
    """Do not release a selected turn whose source/surface contract failed."""


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def classify_current_decision_ack_p4(user_input: str) -> dict | None:
    """Admit one exact, unquoted direct statement; no semantic inference."""
    raw = str(user_input or "")
    if (
        not raw or len(raw) > 148 or raw != raw.strip()
        or _UNSUPPORTED.search(raw)
        or any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for ch in raw)
    ):
        return None
    if re.search(r"[\n\r\t]|[「」『』“”\"'？?！!]|\.\s*\S", raw):
        return None
    matched = _DECISION.fullmatch(raw)
    if not matched:
        return None
    subject = matched.group("subject")
    place = matched.group("place")
    if (
        _UNSUPPORTED.search(subject) or _UNSUPPORTED.search(place)
        or _SENSITIVE.search(subject) or _SENSITIVE.search(place)
        or "。" in subject or "。" in place
        or subject.count("場所") != 1
        or place.endswith(("かも", "らしい", "かな"))
        or raw.count("決めた") != 1
        or "決め" in subject or "決め" in place
    ):
        return None
    try:
        parsed_date = date(
            int(matched.group("year")), int(matched.group("month")),
            int(matched.group("day")),
        )
    except ValueError:
        return None
    date_text = f"{parsed_date.year}年{parsed_date.month}月{parsed_date.day}日"
    # The exact surface date is part of the receipt.  No silent normalization
    # of leading-zero or malformed source dates is allowed.
    if raw[raw.index("私は") + 2:].find(date_text) != 0:
        return None
    kind = "correction_reported" if matched.group("correction") else "ordinary_decision_reported"
    reply = (
        f"訂正ね。そっちが{date_text}に{subject}を{place}に決めたって話な。"
        if kind == "correction_reported" else
        f"そっちが{date_text}に{subject}を{place}に決めたんだな。"
    )
    if len(reply) > MAX_REPLY_CHARS:
        return None
    return {
        "kind": kind, "date": date_text, "subject": subject, "place": place,
        "correction_marker": matched.group("correction") or "",
        "source_raw_sha256": _sha(raw), "source_subject_sha256": _sha(subject),
        "source_place_sha256": _sha(place),
        "authorized_reply": reply, "authorized_reply_sha256": _sha(reply),
    }


def _source_stamp(self, event: dict | None) -> dict | None:
    """Bind to this brain's actual ingest object, cycle, and raw bytes."""
    if not isinstance(event, dict) or getattr(self, "_p4_current_decision_event", None) is not event:
        return None
    stamp = event.get("_p4_current_decision_event")
    runtime = getattr(self, "runtime", None)
    if not isinstance(stamp, dict) or runtime is None:
        return None
    if not (
        stamp.get("schema") == SCHEMA
        and stamp.get("owner_id") == getattr(self, "_p4_current_decision_owner", None)
        and stamp.get("cycle_index") == getattr(runtime, "cycle_index", None)
        and stamp.get("source_raw_sha256") == _sha(event.get("user_input"))
        and isinstance(stamp.get("event_id"), str)
        and re.fullmatch(r"[0-9a-f]{32}", stamp["event_id"]) is not None
    ):
        return None
    return stamp


def build_current_decision_ack_certificate_p4(user_input: str, stamp: dict | None) -> dict | None:
    parsed = classify_current_decision_ack_p4(user_input)
    if parsed is None or not isinstance(stamp, dict):
        return None
    if stamp.get("schema") != SCHEMA or stamp.get("source_raw_sha256") != parsed["source_raw_sha256"]:
        return None
    if not (
        isinstance(stamp.get("owner_id"), str)
        and re.fullmatch(r"[0-9a-f]{32}", stamp["owner_id"]) is not None
        and isinstance(stamp.get("event_id"), str)
        and re.fullmatch(r"[0-9a-f]{32}", stamp["event_id"]) is not None
        and isinstance(stamp.get("cycle_index"), int) and stamp["cycle_index"] > 0
    ):
        return None
    cert = {
        "schema": SCHEMA, "status": "source_admitted_current_user_report",
        "selected_status": "pending", "source_type": "actual_current_user_ingest_event",
        "owner": "current_user", "brain_owner_id": stamp["owner_id"],
        "cycle_index": stamp["cycle_index"], "event_id": stamp["event_id"],
        **parsed, "model_calls_added": 0, "profile_write_authority": "none",
        "correction_supersession": "unresolved" if parsed["kind"] == "correction_reported" else "not_claimed",
        "world_state_truth_claimed": False,
    }
    cert["binding_sha256"] = _sha(json.dumps({
        key: cert[key] for key in (
            "schema", "source_type", "owner", "brain_owner_id", "cycle_index",
            "event_id", "kind", "date", "subject", "place", "correction_marker",
            "source_raw_sha256", "source_subject_sha256", "source_place_sha256",
            "authorized_reply_sha256", "correction_supersession",
        )
    }, sort_keys=True, ensure_ascii=False))
    return cert


def _fresh_certificate(self, event: dict | None) -> dict | None:
    stamp = _source_stamp(self, event)
    return build_current_decision_ack_certificate_p4(event.get("user_input", ""), stamp) if stamp else None


def ingest_event_with_current_decision_ack_p4(self, user_input, input_context=None):
    event = _ORIGINAL_INGEST(self, user_input, input_context=input_context)
    self._p4_current_decision_selected = None
    if not isinstance(event, dict) or event.get("user_input") != user_input:
        return event
    owner = getattr(self, "_p4_current_decision_owner", None)
    if not owner:
        owner = uuid.uuid4().hex
        self._p4_current_decision_owner = owner
    event["_p4_current_decision_event"] = {
        "schema": SCHEMA, "owner_id": owner,
        "event_id": uuid.uuid4().hex,
        "cycle_index": self.runtime.cycle_index,
        "source_raw_sha256": _sha(user_input),
    }
    self._p4_current_decision_event = event
    return event


def cognitive_tick_with_current_decision_ack_p4(self, event):
    prior_selection = getattr(self, "_p4_current_decision_selected", None)
    if isinstance(prior_selection, dict) and prior_selection.get("event") is event:
        raise CurrentDecisionAckDeliveryError("selected_event_replayed_at_cognitive_tick")
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    cert = _fresh_certificate(self, event)
    if cert is None:
        return tick
    logic = tick.get("logic") or {}
    route = tick.get("route_info") or {}
    if prior_gate._protected_or_other_route(logic, route, getattr(self, "right_brain", None)):
        return tick
    previous = {
        "intent": str(logic.get("intent") or ""),
        "planner_path": str(logic.get("planner_path") or ""),
        "selected_core_sha256": _sha(logic.get("core_message_jp")),
        "performed_route": str(route.get("performed_route") or ""),
    }
    cert.update({
        "selected_status": "source_authorized_plan_selected",
        "pre_gate_selected_plan": previous,
        "pre_gate_cognitive_nodes_retained_as_shadow": True,
    })
    reply = cert["authorized_reply"]
    logic.update({
        "reply_goal": "当輪の使用者自身の決定申告を、訂正も含めて短く受け止める",
        "jp_summary": reply, "core_message_jp": reply,
        "planner_path": PLANNER_PATH, "candidate_label": LABEL,
        "response_mode": "direct_answer", "surface_act": "plain_reply",
        "dialogue_act": "direct_chat_answer", "payload_level": "low",
        "grounding": {}, "memory_anchor": {}, "memory_relevance": 0.0,
        "memory_relevance_label": "none", "memory_speakability": "no_memory",
        "memory_use_expected": False,
        "user_belief": "使用者が自分の決定を話した。",
        "my_hidden_knowledge": "決定の申告以外や訂正の確定範囲は知らない。",
        "user_expectation": "短く自然に受け止める。",
        "internal_monologue": "", "bayes_candidates": [],
        "planner_tick_count": 0, "self_correction_applied": False,
        "planner_repair_applied": False, "planner_repair_success": False,
    })
    for key in ("human_speech_plan", "reference_subject_jp", "planner_tick_trace",
                "planner_detected_issues", "planner_unresolved_issues"):
        logic.pop(key, None)
    for key in ("bounded_slow_path_m21", "semantic_route_m22"):
        prior = logic.get(key)
        if isinstance(prior, dict):
            prior["pre_gate_plan_status"] = "shadowed_not_selected"
            prior["post_gate_selected_plan_authority"] = LABEL
            if key == "bounded_slow_path_m21":
                prior["observed_compute_cost_retained"] = True
    logic[LABEL] = deepcopy(cert)
    tick["logic"] = logic
    self._p4_current_decision_selected = {
        "event": event, "logic": logic,
        "binding_sha256": cert["binding_sha256"],
        "cycle_index": cert["cycle_index"], "emit_started": False,
    }
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        runtime.active_goal = logic["reply_goal"]
        runtime.last_internal_monologue = ""
        runtime.last_candidates = []
        runtime.planner_tick_trace = []
        runtime.planner_tick_count = 0
        runtime.self_correction_applied = False
        runtime.last_selected_plan = self._plan_trace_summary(logic)
        for row in getattr(runtime, "blackboard", []):
            if row.get("label") == "selected_plan":
                row["payload"] = deepcopy(runtime.last_selected_plan)
                row["payload"]["post_gate_selected_plan_authority"] = LABEL
            elif row.get("label") in _SHADOW_LABELS and isinstance(row.get("payload"), dict):
                row["payload"] = {
                    **row["payload"], "post_gate_plan_status": "shadowed_not_selected",
                    "post_gate_selected_plan_authority": LABEL,
                }
        index = next((i for i, row in enumerate(runtime.blackboard)
                      if row.get("label") == "selected_plan"), len(runtime.blackboard))
        runtime.blackboard.insert(index, {
            "stage": "evidence", "label": LABEL, "payload": deepcopy(cert), "salience": 1.0,
        })
    return tick


def _history_snapshot(right_brain, logic: dict, event: dict, route: dict) -> dict | None:
    history = getattr(right_brain, "history", None)
    names = ("reply_variant_counts", "intent_variant_counts",
             "normalized_reply_counts", "intent_normalized_counts")
    counters = {name: getattr(right_brain, name, None) for name in names}
    if not isinstance(history, list) or any(not isinstance(item, dict) for item in counters.values()):
        return None
    if not callable(getattr(right_brain, "_remember_turn", None)):
        return None
    return {
        "right_brain": right_brain, "logic_id": id(logic), "event": event,
        "route_info": deepcopy(route), "history": deepcopy(history),
        "counters": {name: deepcopy(value) for name, value in counters.items()},
    }


def _restore_history(tx: dict | None) -> bool:
    if not isinstance(tx, dict):
        return False
    right_brain = tx.get("right_brain")
    history = getattr(right_brain, "history", None)
    if not isinstance(history, list):
        return False
    counters = {name: getattr(right_brain, name, None) for name in tx["counters"]}
    if any(not isinstance(value, dict) for value in counters.values()):
        return False
    history[:] = deepcopy(tx["history"])
    for name, value in counters.items():
        value.clear()
        value.update(deepcopy(tx["counters"][name]))
    return True


def _commit_history(tx: dict | None, logic: dict, selected: str) -> str:
    if not isinstance(tx, dict) or tx.get("logic_id") != id(logic):
        return "transaction_context_unavailable"
    if not _restore_history(tx):
        return "history_rollback_unavailable"
    tx["right_brain"]._remember_turn(
        str(tx["event"].get("user_input") or ""), selected,
        str(logic.get("intent") or "chat"),
    )
    return "raw_user_and_final_visible_reply_committed"


def _selected(logic: dict) -> dict | None:
    cert = logic.get(LABEL) if isinstance(logic, dict) else None
    if isinstance(cert, dict) and cert.get("schema") == SCHEMA and cert.get("selected_status") == "source_authorized_plan_selected":
        return cert
    return None


def _plan_and_source_match(self, logic: dict, tx: dict | None, user_input: str) -> tuple[bool, dict | None]:
    cert = _selected(logic)
    event = tx.get("event") if isinstance(tx, dict) else None
    fresh = _fresh_certificate(self, event)
    bound_fields = (
        "schema", "source_type", "owner", "brain_owner_id", "cycle_index",
        "event_id", "kind", "date", "subject", "place", "correction_marker",
        "source_raw_sha256", "source_subject_sha256", "source_place_sha256",
        "authorized_reply", "authorized_reply_sha256", "correction_supersession",
        "model_calls_added", "profile_write_authority", "world_state_truth_claimed",
    )
    okay = bool(
        cert and fresh and tx.get("logic_id") == id(logic)
        and event.get("user_input") == user_input
        and cert.get("binding_sha256") == fresh.get("binding_sha256")
        and all(cert.get(key) == fresh.get(key) for key in bound_fields)
        and cert.get("kind") == fresh.get("kind")
        and cert.get("authorized_reply_sha256") == fresh.get("authorized_reply_sha256")
        and logic.get("planner_path") == PLANNER_PATH
        and logic.get("core_message_jp") == fresh.get("authorized_reply")
        and logic.get("surface_act") == "plain_reply"
        and not prior_gate._protected_or_other_route(
            logic, tx.get("route_info") or {}, getattr(self, "right_brain", None),
        )
    )
    return okay, fresh


def visible_guard_with_current_decision_ack_p4(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data,
    )
    tx = _ACTIVE_TURN.get()
    # The emit wrapper records that this turn selected D before any downstream
    # surface code runs.  A later mutation must not remove the certificate and
    # thereby turn the terminal guard into a no-op before save_episode.
    if not isinstance(tx, dict) and (
        not isinstance(logic_data, dict) or _selected(logic_data) is None
    ):
        return visible
    if not isinstance(logic_data, dict) or _selected(logic_data) is None:
        _restore_history(tx.get("history_tx") if isinstance(tx, dict) else None)
        raise CurrentDecisionAckDeliveryError("selected_certificate_missing_before_episode_write")
    brain = tx.get("brain") if isinstance(tx, dict) else None
    source_ok, fresh = _plan_and_source_match(brain, logic_data, tx, user_input) if brain else (False, None)
    checker = getattr(self, "_user_visible_language_rejection_reasons", None)
    reasons = ["source_or_plan_integrity_mismatch"] if not source_ok else []
    if not callable(checker):
        reasons.append("language_checker_missing")
    elif source_ok:
        try:
            reasons.extend(checker(
                fresh["authorized_reply"], user_input=user_input,
                logic_data=logic_data, memory_data=memory_data,
            ))
        except Exception:
            reasons.append("language_checker_exception")
    selected = fresh["authorized_reply"] if not reasons else "ん、今は正確に受け止められないな。"
    cert = deepcopy(logic_data[LABEL])
    cert.update({
        "visible_surface_status": "matched" if not reasons else "failed_closed",
        "visible_failure_reasons": reasons,
        "pre_authority_surface_sha256": _sha(visible),
        "final_visible_surface_sha256": _sha(selected),
        "final_visible_surface_matches_contract": bool(
            fresh and selected == fresh["authorized_reply"] and not reasons
        ),
    })
    tx_history = tx.get("history_tx") if isinstance(tx, dict) else None
    cert["right_brain_history_surface_status"] = _commit_history(tx_history, logic_data, selected)
    logic_data[LABEL] = cert
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    original_reply = str(guard.get("original_reply") or reply or "")
    guard.update({
        "changed": selected != original_reply,
        "pre_decision_ack_repair_action": guard.get("repair_action"),
        "repair_action": "current_user_decision_ack_" + cert["visible_surface_status"],
        "final_rejection_reasons": reasons,
        "final_reply": selected, "final_reply_sha256": _sha(selected),
    })
    logic_data["visible_language_guard"] = guard
    return selected


def post_check_with_current_decision_ack_p4(self, logic, user_input, reply, memory_data):
    tx = _ACTIVE_TURN.get()
    if not isinstance(tx, dict) and _selected(logic) is None:
        return _ORIGINAL_POST_CHECK(self, logic, user_input, reply, memory_data)
    if _selected(logic) is None:
        _restore_history(tx.get("history_tx") if isinstance(tx, dict) else None)
        raise CurrentDecisionAckDeliveryError("selected_certificate_missing_before_episode_write")
    source_ok, fresh = _plan_and_source_match(self, logic, tx, user_input)
    guard = logic.get("visible_language_guard") or {}
    cert = logic[LABEL]
    history_tx = tx.get("history_tx") if isinstance(tx, dict) else None
    history = getattr(getattr(self, "right_brain", None), "history", None)
    checker = getattr(getattr(self, "right_brain", None), "_user_visible_language_rejection_reasons", None)
    try:
        language_reasons = checker(
            reply, user_input=user_input, logic_data=logic, memory_data=memory_data,
        ) if callable(checker) else ["language_checker_missing"]
    except Exception:
        language_reasons = ["language_checker_exception"]
    history_ok = bool(
        isinstance(history, list) and len(history) >= 2
        and history[-2].get("role") == "user"
        and history[-2].get("content") == user_input
        and history[-1].get("role") == "assistant"
        and history[-1].get("content") == reply
        and cert.get("right_brain_history_surface_status")
        == "raw_user_and_final_visible_reply_committed"
    )
    okay = bool(
        source_ok and fresh and reply == fresh["authorized_reply"]
        and _sha(reply) == fresh["authorized_reply_sha256"]
        and cert.get("visible_surface_status") == "matched"
        and cert.get("final_visible_surface_matches_contract") is True
        and cert.get("final_visible_surface_sha256") == _sha(reply)
        and guard.get("final_reply") == reply
        and guard.get("final_reply_sha256") == _sha(reply)
        and history_ok
        and not language_reasons
    )
    if not okay:
        _restore_history(history_tx)
        cert["pre_episode_status"] = "blocked_before_episode_write"
        cert["pre_episode_failure"] = "source_plan_guard_reply_or_history_mismatch"
        raise CurrentDecisionAckDeliveryError(cert["pre_episode_failure"])
    cert["pre_episode_status"] = "verified_before_episode_write"
    cert["pre_episode_reply_sha256"] = _sha(reply)
    try:
        return _ORIGINAL_POST_CHECK(self, logic, user_input, reply, memory_data)
    except Exception:
        _restore_history(history_tx)
        cert["pre_episode_status"] = "post_check_error_before_episode_write"
        raise


def remember_profile_facts_with_current_decision_ack_p4(self, user_input):
    """A current decision report is episodic evidence, not a stable profile fact.

    The base profile extractor can mistake a place containing `が好き` for a
    preference.  Suppress only this selected turn's automatic fact extraction;
    ordinary turns still use the unchanged base method.
    """
    tx = _ACTIVE_TURN.get()
    brain = tx.get("brain") if isinstance(tx, dict) else None
    if brain is not None and getattr(brain, "memory", None) is self:
        event = tx.get("event") or {}
        if event.get("user_input") != user_input:
            raise CurrentDecisionAckDeliveryError("profile_source_mismatch_after_episode_write")
        logic = tx.get("logic")
        cert = _selected(logic)
        if cert is None:
            raise CurrentDecisionAckDeliveryError("selected_certificate_missing_after_episode_write")
        cert["factive_profile_write_status"] = "suppressed_for_current_report"
        return None
    return _ORIGINAL_PROFILE_REMEMBER(self, user_input)


def _materialize(result: dict, *, selected_at_entry=False) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    cert = _selected(logic)
    if cert is None:
        if selected_at_entry:
            raise CurrentDecisionAckDeliveryError("selected_certificate_missing_after_episode_write")
        return result
    trace = result.get("runtime_trace")
    if not isinstance(trace, dict):
        raise CurrentDecisionAckDeliveryError("runtime_trace_missing_after_episode_write")
    reply = str(result.get("reply") or "")
    episode = str(result.get("episode_doc") or "")
    episode_user = (
        episode.split(" | User: ", 1)[1].split(" | Summary: ", 1)[0]
        if " | User: " in episode and " | Summary: " in episode else ""
    )
    utterances = [row.get("payload", {}).get("reply") for row in trace.get("blackboard", [])
                  if isinstance(row, dict) and row.get("label") == "utterance"]
    if not (
        cert.get("pre_episode_status") == "verified_before_episode_write"
        and cert.get("factive_profile_write_status") == "suppressed_for_current_report"
        and trace.get("cycle_index") == cert.get("cycle_index")
        and reply == cert.get("authorized_reply")
        and cert.get("pre_episode_reply_sha256") == _sha(reply)
        and utterances == [reply]
        and _sha(episode_user) == cert.get("source_raw_sha256")
        and f" | Uruha: {reply} | Mood: " in episode
    ):
        raise CurrentDecisionAckDeliveryError("post_episode_trace_or_reply_mismatch")
    cert = deepcopy(cert)
    cert["terminal_status"] = "trace_and_episode_reported_match"
    cert["terminal_reply_sha256"] = _sha(reply)
    logic[LABEL] = cert
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), len(rows))
    rows.insert(index, {"stage": "evidence", "label": LABEL,
                        "payload": deepcopy(cert), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(cert)
    return result


def emit_response_with_current_decision_ack_p4(self, event, tick_result):
    logic = (tick_result or {}).get("logic") or {}
    cert = _selected(logic)
    marker = getattr(self, "_p4_current_decision_selected", None)
    selected_event = isinstance(marker, dict) and marker.get("event") is event
    if not selected_event and cert is None:
        return _ORIGINAL_EMIT(self, event, tick_result)
    if not (
        selected_event and marker.get("logic") is logic
        and not marker.get("emit_started")
        and cert is not None
        and cert.get("binding_sha256") == marker.get("binding_sha256")
    ):
        raise CurrentDecisionAckDeliveryError("selected_event_or_certificate_mismatch_before_emit")
    # A selected event gets one no-retry delivery attempt, including failures.
    marker["emit_started"] = True
    history_tx = _history_snapshot(
        getattr(self, "right_brain", None), logic, event,
        (tick_result or {}).get("route_info") or {},
    )
    tx = {"brain": self, "event": event, "logic": logic, "logic_id": id(logic),
          "history_tx": history_tx, "route_info": deepcopy((tick_result or {}).get("route_info") or {})}
    token = _ACTIVE_TURN.set(tx)
    try:
        result = _ORIGINAL_EMIT(self, event, tick_result)
    except Exception:
        if (logic.get(LABEL) or {}).get("pre_episode_status") != "verified_before_episode_write":
            _restore_history(history_tx)
        raise
    finally:
        _ACTIVE_TURN.reset(token)
    return _materialize(result, selected_at_entry=True)


def install_current_decision_ack_authority_p4() -> bool:
    """Install after the frozen C chain, only in the new opt-in Web entry."""
    global _INSTALLED, _ORIGINAL_INGEST, _ORIGINAL_TICK, _ORIGINAL_GUARD
    global _ORIGINAL_POST_CHECK, _ORIGINAL_EMIT, _ORIGINAL_RUN, _ORIGINAL_PROFILE_REMEMBER
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_INGEST = UruhaBrainV4_Mac.ingest_event
    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_POST_CHECK = UruhaBrainV4_Mac._attach_reply_post_check
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_PROFILE_REMEMBER = MemoryManager._remember_profile_facts
    UruhaBrainV4_Mac.ingest_event = ingest_event_with_current_decision_ack_p4
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_current_decision_ack_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_current_decision_ack_p4
    UruhaBrainV4_Mac._attach_reply_post_check = post_check_with_current_decision_ack_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_with_current_decision_ack_p4
    MemoryManager._remember_profile_facts = remember_profile_facts_with_current_decision_ack_p4

    def run(self, user_input, input_context=None):
        result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
        marker = getattr(self, "_p4_current_decision_selected", None)
        current_selected = bool(
            isinstance(marker, dict) and marker.get("emit_started")
            and marker.get("event") is getattr(self, "_p4_current_decision_event", None)
            and marker["event"].get("user_input") == user_input
            and marker.get("cycle_index") == getattr(self.runtime, "cycle_index", None)
        )
        _materialize(
            result,
            selected_at_entry=current_selected,
        )
        runtime = getattr(self, "runtime", None)
        trace = result.get("runtime_trace") if isinstance(result, dict) else None
        if isinstance(trace, dict) and runtime is not None and _selected(result.get("logic") or {}):
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (getattr(runtime, "turn_traces", None)
                    and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")):
                runtime.turn_traces[-1] = deepcopy(trace)
        return result

    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "PLANNER_PATH", "CurrentDecisionAckDeliveryError",
    "classify_current_decision_ack_p4", "build_current_decision_ack_certificate_p4",
    "install_current_decision_ack_authority_p4",
]
