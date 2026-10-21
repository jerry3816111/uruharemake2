"""Opt-in authority boundary for a small class of local time/place answers.

This does not decide what happened in the world.  It permits a concrete answer
only when an affirmative User turn was actually handed to this turn's decision
path.  The same receipt binds the selected plan and the visible Japanese reply.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import re
import unicodedata
import uuid

import uruha_memory_runtime as memory_runtime


LABEL = "local_fact_answer_authority_p4"
SCHEMA = "uruha_local_fact_answer_authority_p4_v1"
PLANNER_PATH = "local_fact_answer_authority_p4"
MAX_AUTHORIZED_CORE_CHARS = 40
_INSTALLED = False
_ORIGINAL_TICK = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_ACTIVE_HISTORY_TRANSACTION = ContextVar("local_fact_history_transaction_p4", default=None)

_TIME_QUERY = re.compile(r"(?P<subject>[^「」『』!?？。]{2,40})は何時から(?:始まる|だった)[?？]$")
_PLACE_QUERY = re.compile(r"(?P<subject>[^「」『』!?？。]{2,40})はどこに置いた[?？]$")
_PLACE_QUERY_ALT = re.compile(r"(?P<subject>[^「」『』!?？。]{2,40})の置き場[、,]?どこ[?？]$")
_USER_DECIDED_PLACE_QUERY = re.compile(
    r"(?P<subject>[^「」『』!?？。]{2,72})[、,](?:さっき)?私が決めたのは"
    r"どこ(?:だっけ|だった)?[?？]$"
)
_TIME_ASSERTION = re.compile(r"(?P<subject>[^「」『』!?？。]{2,40})は(?P<value>[0-2]?[0-9]時(?:[0-5]?[0-9]分)?)から始まる[。.]?$")
_PLACE_ASSERTION = re.compile(r"(?P<subject>[^「」『』!?？。]{2,40})は(?P<value>[^「」『』!?？。]{1,40})に置いた[。.]?$")
_USER_DECIDED_PLACE_ASSERTION = re.compile(
    r"私は(?P<subject>[^「」『』!?？。]{2,72})を"
    r"(?P<value>[^「」『』!?？。]{1,40})に決めた[。.]?$"
)
_SENSITIVE_SUBJECT = re.compile(r"パスワード|パスコード|暗証番号|認証コード|合言葉|住所|電話番号|口座|秘密", re.I)
_SENSITIVE_PRIOR_DECISION = re.compile(
    r"鍵|カギ|キー|財布|現金|貴重品|隠す|隠し"
)
_PRIOR_DECISION_CORRECTION = re.compile(
    r"^(?:さっきのは違う|前のは違う|訂正[、,:：]?|やっぱり違う)[、,:：]?"
    r"私は(?P<subject>[^「」『』!?？。]{2,72})を"
    r"(?P<value>[^「」『』!?？。]{1,40})に決めた[。.]?$"
)
_UNSUPPORTED_ASSERTION = re.compile(
    r"(?:かも|らしい|たぶん|多分|そう|かな|でしょう|だろう|ない|なかった|違う|じゃない|"
    r"と言|って言|聞いた|教わった|友達|友人|先生|同僚|仮に|もし|例えば|引用|メモ|/|\\|\|)"
)
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


def classify_local_fact_query_p4(user_input: str) -> dict:
    raw = str(user_input or "")
    text = _norm(raw)
    base = {
        "schema": SCHEMA, "input_sha256": _sha(raw), "eligible": False,
        "slot": None, "subject": None, "reason": "outside_bounded_fact_query",
        "raw_dialogue_persisted": False, "private_state_truth_claimed": False,
        "model_calls_added": 0,
    }
    if not text or len(text) > 90 or "|" in text:
        return base
    for slot, pattern in (
        ("local_start_time", _TIME_QUERY),
        ("local_placement", _PLACE_QUERY),
        ("local_placement", _PLACE_QUERY_ALT),
        ("prior_user_decided_place", _USER_DECIDED_PLACE_QUERY),
    ):
        match = pattern.fullmatch(text)
        if match:
            subject = match.group("subject").strip()
            subject_limit = 48 if slot == "prior_user_decided_place" else 18
            if (subject and len(subject) <= subject_limit
                    and (slot != "prior_user_decided_place" or subject.endswith("場所"))
                    and not _UNSUPPORTED_ASSERTION.search(subject)
                    and not _SENSITIVE_SUBJECT.search(subject)
                    and (slot != "prior_user_decided_place"
                         or not _SENSITIVE_PRIOR_DECISION.search(subject))):
                return {**base, "eligible": True, "slot": slot,
                        "subject": subject, "reason": "bounded_local_fact_question"}
    return base


def _direct_user_assertion(user_text: str, slot: str, subject: str) -> str | None:
    text = _norm(user_text)
    if not text or len(text) > 120 or _UNSUPPORTED_ASSERTION.search(text):
        return None
    if any(marker in text for marker in (
        "「", "」", "『", "』", "\"", "'", "?", "？", "User:", "Uruha:", "->", "\n", "\r",
    )):
        return None
    pattern = (
        _TIME_ASSERTION if slot == "local_start_time" else
        _USER_DECIDED_PLACE_ASSERTION if slot == "prior_user_decided_place" else
        _PLACE_ASSERTION
    )
    match = pattern.fullmatch(text)
    if not match or match.group("subject").strip() != subject:
        return None
    value = match.group("value").strip()
    if slot == "local_start_time":
        hour = int(value.split("時", 1)[0])
        if hour > 23:
            return None
    if not value or _UNSUPPORTED_ASSERTION.search(value):
        return None
    if slot == "prior_user_decided_place" and (
        _SENSITIVE_SUBJECT.search(value) or _SENSITIVE_PRIOR_DECISION.search(value)
    ):
        return None
    return value


def _episode_user_field(text: str) -> str | None:
    if not isinstance(text, str) or len(text) > 5000:
        return None
    delimiters = (" | User: ", " | Summary: ", " | Uruha: ", " | Mood: ")
    if any(text.count(delimiter) != 1 for delimiter in delimiters):
        return None
    positions = [text.index(delimiter) for delimiter in delimiters]
    if positions != sorted(positions):
        return None
    user = text[positions[0] + len(delimiters[0]):positions[1]].strip()
    if not user or len(user) > 120 or "|" in user or "\n" in user or "\r" in user:
        return None
    return user.strip()


def _handed_user_sources(memory_data: dict) -> tuple[list[dict], dict]:
    """Read passed raw User turns only; never search the DB or use summaries."""
    memory_data = memory_data if isinstance(memory_data, dict) else {}
    provenance = memory_data.get("memory_provenance") or {}
    passed = provenance.get("passed_to_leftbrain") or []
    passed_ids = set(provenance.get("passed_to_leftbrain_trace_ids") or [])
    sources = []
    audit = {"recent_turns_examined": 0, "direct_episodes_examined": 0,
             "rejected_untyped_or_malformed": 0}
    for turn in memory_data.get("recent_turns") or []:
        if not isinstance(turn, dict):
            continue
        user, reply = str(turn.get("user") or ""), str(turn.get("reply") or "")
        if not user or not reply or any(marker in user for marker in ("User:", "Uruha:", "->", "\n", "\r")):
            continue
        expected = f"User:{user} -> Uruha:{reply}"
        candidate = memory_runtime.recent_turn_candidates([turn])
        if len(candidate) != 1 or candidate[0].get("text") != expected:
            continue
        expected_trace_id = memory_runtime.memory_trace_id(candidate[0])
        row = next((item for item in passed if isinstance(item, dict)
                    and item.get("source") == "recent_turn"
                    and item.get("channel") == "recent_turns"
                    and item.get("text") == expected
                    and item.get("trace_id") == expected_trace_id
                    and item.get("trace_id") in passed_ids), None)
        if row:
            audit["recent_turns_examined"] += 1
            sources.append({"user": user, "source_channel": "recent_turns",
                            "trace_id": row["trace_id"], "memory_id": turn.get("episode_id")})
    seen_episode_ids = set()
    for row in passed:
        if not isinstance(row, dict) or row.get("source") != "episode" or row.get("channel") != "direct_episode":
            continue
        memory_id = str(row.get("memory_id") or "")
        trace_id = str(row.get("trace_id") or "")
        try:
            valid_id = str(uuid.UUID(memory_id)) == memory_id
        except (ValueError, AttributeError):
            valid_id = False
        if (
            not valid_id or memory_id in seen_episode_ids
            or row.get("collection_name") != "episode"
            or trace_id != f"stored:episode:{memory_id}"
            or trace_id not in passed_ids
            or row.get("episode_record_kind") != "turn_episode"
            or row.get("episode_record_kind_origin") != "stored_metadata"
        ):
            audit["rejected_untyped_or_malformed"] += 1
            continue
        user = _episode_user_field(row.get("text"))
        if user is None:
            audit["rejected_untyped_or_malformed"] += 1
            continue
        seen_episode_ids.add(memory_id)
        audit["direct_episodes_examined"] += 1
        sources.append({"user": user, "source_channel": "direct_episode",
                        "trace_id": trace_id, "memory_id": memory_id})
    return sources, audit


def build_local_fact_certificate_p4(user_input: str, memory_data: dict | None) -> dict:
    query = classify_local_fact_query_p4(user_input)
    if not query["eligible"]:
        return query
    sources, audit = _handed_user_sources(memory_data or {})
    unresolved_correction = False
    if query["slot"] == "prior_user_decided_place":
        for source in sources:
            corrected = _PRIOR_DECISION_CORRECTION.fullmatch(_norm(source["user"]))
            if corrected and corrected.group("subject").strip() == query["subject"]:
                unresolved_correction = True
                break
    matches = []
    for source in sources:
        value = _direct_user_assertion(source["user"], query["slot"], query["subject"])
        if value is not None:
            matches.append({**source, "value": value, "source_user_sha256": _sha(source["user"])})
    if query["slot"] == "prior_user_decided_place":
        # The same raw User turn often arrives through both recent-turn and
        # typed-episode channels.  Two copies are one observation, not two
        # independent or conflicting decisions.
        distinct_sources = {}
        for row in matches:
            digest = row["source_user_sha256"]
            if digest not in distinct_sources or row["source_channel"] == "direct_episode":
                distinct_sources[digest] = row
        matches = list(distinct_sources.values())
    values = sorted(set(row["value"] for row in matches))
    if unresolved_correction:
        # This gate does not infer whether an explicit revision supersedes
        # every older statement.  Do not answer from a stale admitted source.
        reply = "前の場所は訂正してたな。今の決定を確認させて。"
        status = "unresolved_user_correction"
        value = source_type = trace_id = memory_id = None
    elif len(values) == 1:
        chosen = next((row for row in reversed(matches) if row["source_channel"] == "recent_turns"), matches[-1])
        value = values[0]
        reply = (
            f"{query['subject']}は{value}から始まるって言ってたな。"
            if query["slot"] == "local_start_time" else
            f"前にそっちが決めたのは{value}だよ。"
            if query["slot"] == "prior_user_decided_place" else
            f"{query['subject']}は{value}に置いたって言ってたな。"
        )
        status = "source_backed"
        source_type, trace_id, memory_id = chosen["source_channel"], chosen["trace_id"], chosen["memory_id"]
        if len(reply) > MAX_AUTHORIZED_CORE_CHARS:
            # The existing planner/speech path has a 40-character core budget.
            # Do not silently truncate a source value into a false answer.
            reply = "聞いた内容を今は正確に言い直せないな。"
            status = "source_value_outside_surface_budget"
            value = source_type = trace_id = memory_id = None
    else:
        conflicting_places_reply = "そっち、場所を二つ言ってる。今はどっちに決めた？"
        if query["slot"] == "prior_user_decided_place" and len(values) == 2:
            named_conflict = f"{values[0]}と{values[1]}、どっちが今の決定？"
            if len(named_conflict) <= MAX_AUTHORIZED_CORE_CHARS:
                conflicting_places_reply = named_conflict
        elif query["slot"] == "prior_user_decided_place" and len(values) > 2:
            conflicting_places_reply = "場所をいくつか言ってる。今はどれに決めた？"
        reply = (
            conflicting_places_reply
            if query["slot"] == "prior_user_decided_place" and values else
            "そっちが決めた場所は、まだ確認できないな。"
            if query["slot"] == "prior_user_decided_place" else
            f"{query['subject']}が何時からか、今の会話だけじゃ分からないな。"
            if query["slot"] == "local_start_time" else
            f"{query['subject']}の置き場は、今の会話だけじゃ分からないな。"
        )
        status = "conflicting_user_sources" if values else "no_admitted_user_source"
        value = source_type = trace_id = memory_id = None
    if len(reply) > MAX_AUTHORIZED_CORE_CHARS:
        # Defensive even if a future query template changes.
        reply = "ん、今は正確に答えられないな。"
        status = "reply_outside_surface_budget"
        value = source_type = trace_id = memory_id = None
    cert = {
        **query, **audit, "status": status, "selected_status": "pending",
        "admitted_source_count": len(matches), "distinct_value_count": len(values),
        "admitted_value": value, "source_channel": source_type,
        "source_trace_id": trace_id, "source_memory_id": memory_id,
        "authorized_reply": reply, "authorized_reply_sha256": _sha(reply),
    }
    binding_fields = (
        "input_sha256", "slot", "subject", "status", "admitted_value",
        "source_channel", "source_trace_id", "authorized_reply_sha256",
    )
    if query["slot"] == "prior_user_decided_place":
        cert.update({
            "source_user_sha256": (
                chosen["source_user_sha256"] if len(values) == 1 and status == "source_backed"
                else None
            ),
            "admitted_source_trace_ids": [row["trace_id"] for row in matches[:8]],
            "admitted_source_user_sha256s": [row["source_user_sha256"] for row in matches[:8]],
        })
        binding_fields += ("source_user_sha256", "admitted_source_user_sha256s")
    cert["binding_sha256"] = _sha(json.dumps({
        key: cert.get(key) for key in binding_fields
    }, sort_keys=True, ensure_ascii=False))
    return cert


def _protected_or_other_route(logic: dict, route_info: dict, right_brain=None) -> bool:
    import uruha_adaptive_person_model as adaptive_person

    return bool(
        (route_info or {}).get("route") == "low_road"
        or (logic.get("semantic_route_m22") or {}).get("selected_type") == "safety_sensitive"
        or logic.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic.get("scene") in adaptive_person.PROTECTED_SCENES
        or logic.get("intent") == "reference_probe"
        or logic.get("surface_act") == "reference_probe"
        or (right_brain is not None and getattr(right_brain, "_structured_surface_required", lambda: False)())
    )


def cognitive_tick_with_local_fact_answer_authority_p4(self, event):
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    user_input = str((event or {}).get("user_input") or "")
    cert = build_local_fact_certificate_p4(user_input, (event or {}).get("memory_data"))
    if not cert.get("eligible"):
        return tick
    logic = tick.get("logic") or {}
    if _protected_or_other_route(logic, tick.get("route_info") or {}, getattr(self, "right_brain", None)):
        return tick
    previous = {"intent": str(logic.get("intent") or ""),
                "planner_path": str(logic.get("planner_path") or ""),
                "selected_core_sha256": _sha(logic.get("core_message_jp")),
                "performed_route": str((tick.get("route_info") or {}).get("performed_route") or "")}
    core = cert["authorized_reply"]
    source_backed = bool(cert["source_trace_id"])
    source_anchor = ({
        "kind": "source_bound_local_fact", "source": (
            "episode" if cert["source_channel"] == "direct_episode" else "recent_turn"
        ),
        "trace_id": cert["source_trace_id"], "memory_id": cert["source_memory_id"],
        "provenance_channel": cert["source_channel"],
        "jp_anchor": cert["admitted_value"], "terms": [cert["admitted_value"]],
        "relevance": 1.0,
    } if source_backed else {})
    logic.update({
        "reply_goal": (
            "使用者自身が決めた場所を、直接発話の範囲だけで短く答える"
            if cert["slot"] == "prior_user_decided_place" else
            "使用者が話した範囲だけで、開始時刻または置き場を短く答える"
        ),
        "jp_summary": core, "core_message_jp": core,
        "planner_path": PLANNER_PATH, "candidate_label": LABEL,
        "response_mode": "direct_answer", "surface_act": "plain_reply",
        "dialogue_act": "direct_chat_answer", "payload_level": "low",
        "grounding": {}, "memory_anchor": source_anchor,
        "memory_relevance": 1.0 if source_backed else 0.0,
        "memory_relevance_label": "high" if source_backed else "none",
        "memory_speakability": "explicit_ok" if source_backed else "no_memory",
        "memory_speakability_reason": "source_certificate_controls_answer",
        "memory_gravity": 1.0 if source_backed else 0.0,
        "memory_use_expected": source_backed,
        "user_belief": (
            "前に自分で決めた場所を聞いている。"
            if cert["slot"] == "prior_user_decided_place" else
            "開始時刻か置き場を聞いている。"
        ),
        "my_hidden_knowledge": "確認できる User 発話以外は断定しない。",
        "user_expectation": "根拠のある短い返答。",
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
    cert = {**cert, "selected_status": "source_authorized_plan_selected",
            "pre_gate_selected_plan": previous,
            "pre_gate_cognitive_nodes_retained_as_shadow": True}
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
                prediction.get("expected_intent", ""),
                prediction.get("expected_valence", 0.0),
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


def _commit_visible_history(right_brain, logic_data: dict, user_input: str, selected: str) -> str:
    """For this new slot only, replace pre-guard speech with the visible reply."""
    tx = _ACTIVE_HISTORY_TRANSACTION.get()
    if (not isinstance(tx, dict) or tx.get("right_brain") is not right_brain
            or tx.get("logic_id") != id(logic_data)):
        return "transaction_context_unavailable"
    history = getattr(right_brain, "history", None)
    if not isinstance(history, list):
        return "history_unavailable"
    counters = {name: getattr(right_brain, name, None) for name in tx["counters"]}
    if any(not isinstance(counter, dict) for counter in counters.values()):
        return "counter_receipt_unavailable"
    history[:] = deepcopy(tx["history"])
    for name, counter in counters.items():
        counter.clear()
        counter.update(deepcopy(tx["counters"][name]))
    # The selected plan's jp_summary is the authorized *assistant* answer.
    # Never record it in the history entry labelled as a User utterance.
    right_brain._remember_turn(
        str(user_input or ""), selected,
        str(logic_data.get("intent") or "chat"),
    )
    return "pre_guard_speech_rolled_back_final_visible_committed"


def emit_response_with_local_fact_answer_authority_p4(self, event, tick_result):
    logic = (tick_result or {}).get("logic") or {}
    cert = logic.get(LABEL) or {}
    tx = (
        _history_snapshot(getattr(self, "right_brain", None), logic)
        if cert.get("selected_status") == "source_authorized_plan_selected"
        and cert.get("slot") == "prior_user_decided_place" else None
    )
    token = _ACTIVE_HISTORY_TRANSACTION.set(tx)
    try:
        return _ORIGINAL_EMIT(self, event, tick_result)
    finally:
        _ACTIVE_HISTORY_TRANSACTION.reset(token)


def visible_guard_with_local_fact_answer_authority_p4(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(self, reply, logic_data, user_input=user_input, memory_data=memory_data)
    if not isinstance(logic_data, dict):
        return visible
    bound = logic_data.get(LABEL) or {}
    if bound.get("schema") != SCHEMA or bound.get("selected_status") != "source_authorized_plan_selected":
        return visible
    fresh = build_local_fact_certificate_p4(user_input, memory_data)
    integrity = (
        fresh.get("binding_sha256") == bound.get("binding_sha256")
        and logic_data.get("planner_path") == PLANNER_PATH
        and logic_data.get("core_message_jp") == fresh.get("authorized_reply")
        and logic_data.get("surface_act") == "plain_reply"
        and not _protected_or_other_route(logic_data, {}, self)
    )
    selected = fresh.get("authorized_reply") if integrity else "ん、今の会話だけじゃ確かめられないな。"
    checker = getattr(self, "_user_visible_language_rejection_reasons", None)
    try:
        reasons = checker(selected, user_input=user_input, logic_data=logic_data,
                          memory_data=memory_data) if callable(checker) else ["checker_missing"]
    except Exception:
        reasons = ["checker_exception"]
    if reasons:
        selected = "ん、もう一回だけ聞かせて。"
    receipt = deepcopy(bound)
    receipt["visible_surface_status"] = (
        "matched" if integrity and not reasons else "failed_closed"
    )
    receipt["visible_failure_reason"] = (
        None if integrity and not reasons else
        "source_or_plan_integrity_mismatch" if not integrity else "language_guard_rejected"
    )
    receipt["pre_authority_surface_sha256"] = _sha(visible)
    receipt["final_visible_surface_sha256"] = _sha(selected)
    receipt["final_visible_surface_matches_contract"] = selected == fresh.get("authorized_reply")
    if bound.get("slot") == "prior_user_decided_place":
        receipt["right_brain_history_surface_status"] = _commit_visible_history(
            self, logic_data, user_input, selected,
        )
    logic_data[LABEL] = receipt
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    original_reply = str(guard.get("original_reply") or reply or "")
    guard.update({
        "changed": selected != original_reply,
        "pre_local_fact_repair_action": guard.get("repair_action"),
        "repair_action": "local_fact_answer_authority_" + receipt["visible_surface_status"],
        "final_rejection_reasons": reasons,
        "final_reply": selected, "final_reply_sha256": _sha(selected),
    })
    logic_data["visible_language_guard"] = guard
    return selected


def materialize_local_fact_answer_authority_p4(result: dict) -> dict:
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


def install_local_fact_answer_authority_p4() -> bool:
    """Install after the existing reference gate, only in the opt-in entry."""
    global _INSTALLED, _ORIGINAL_TICK, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_local_fact_answer_authority_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_local_fact_answer_authority_p4

    def finish(self, result):
        if not isinstance(result, dict) or (result.get("logic") or {}).get(LABEL, {}).get("schema") != SCHEMA:
            return result
        materialize_local_fact_answer_authority_p4(result)
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
        return finish(self, emit_response_with_local_fact_answer_authority_p4(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "PLANNER_PATH", "classify_local_fact_query_p4",
    "build_local_fact_certificate_p4", "cognitive_tick_with_local_fact_answer_authority_p4",
    "emit_response_with_local_fact_answer_authority_p4",
    "visible_guard_with_local_fact_answer_authority_p4",
    "materialize_local_fact_answer_authority_p4", "install_local_fact_answer_authority_p4",
]
