"""Read-only recall for one explicit typed current-preference relation.

P4-I persists multilingual current preferences but deliberately keeps the
profile shadow out of answer generation.  P4-J opens one narrower seam: an
explicit first-person question about the current value of an exact supported
scope may read the active P4-I record.  Historical, negative, ambiguous and
unsupported records never become current answers.
"""

from __future__ import annotations

from copy import deepcopy
import datetime
import hashlib
import json
import re
import unicodedata

import uruha_multilingual_current_preference_p4 as p4i


LABEL = "typed_current_preference_recall_p4"
SCHEMA = "uruha_typed_current_preference_recall_p4"
_INSTALLED = False
_ORIGINAL_QUERY_ALL_LAYERS = None
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


_QUERY_PATTERNS = (
    (
        "en",
        re.compile(
            r"^\s*what(?:'s|\s+is)\s+my\s+current\s+"
            r"(?P<scope>drink|beverage)\s+preference\s*[?？]?\s*$",
            re.I,
        ),
    ),
    (
        "zh",
        re.compile(
            r"^\s*我(?:現在|现在)(?:的)?(?P<scope>飲料|饮料|飲品|饮品)"
            r"(?:偏好|喜好)是(?:什麼|什么)\s*[?？]?\s*$"
        ),
    ),
    (
        "ja",
        re.compile(
            r"^\s*(?:私|うち)の(?:今|現在)の(?P<scope>飲み物)の好み"
            r"(?:は)?(?:何|なに)\s*[?？]?\s*$"
        ),
    ),
)

_SCOPE_ALIASES = {
    "drink": "drink",
    "beverage": "drink",
    "飲料": "drink",
    "饮料": "drink",
    "飲品": "drink",
    "饮品": "drink",
    "飲み物": "drink",
}

_SCOPE_SURFACE_JP = {"drink": "飲み物"}

_VALUE_SURFACE_JP = {
    "rooibos tea": "ルイボスティー",
    "barley tea": "麦茶",
    "oolong tea": "ウーロン茶",
    "herbal tea": "ハーブティー",
    "black tea": "紅茶",
    "sparkling water": "炭酸水",
    "hot cocoa": "ホットココア",
    "氣泡水": "炭酸水",
    "气泡水": "炭酸水",
    "熱可可": "ホットココア",
    "热可可": "ホットココア",
    "ルイボスティー": "ルイボスティー",
    "麦茶": "麦茶",
    "ウーロン茶": "ウーロン茶",
    "紅茶": "紅茶",
    "炭酸水": "炭酸水",
}

_METALINGUISTIC_OR_EMBEDDED = re.compile(
    r"(?:^\s*(?:quote|translate)\s*:|\bif\s+i\s+asked\b|"
    r"\btranslate\b|翻譯|翻译|引用|假設|假设|という文)",
    re.I,
)


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalize(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`「」『』“”()（）:：;；]+", "", text)


def _public_base(text):
    return {
        "schema": SCHEMA,
        "input_sha256": _digest(str(text or "").strip()),
        "raw_dialogue_persisted": False,
    }


def classify_typed_current_preference_query_p4(user_input):
    """Select only an explicit first-person current query with one exact scope."""
    text = str(user_input or "")
    base = _public_base(text)
    if _METALINGUISTIC_OR_EMBEDDED.search(text):
        return {
            **base,
            "selected": False,
            "status": "not_selected",
            "reason": "embedded_quoted_hypothetical_or_metalinguistic_query",
        }
    for language, pattern in _QUERY_PATTERNS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        raw_scope = match.group("scope")
        scope = _SCOPE_ALIASES.get(raw_scope.casefold(), _SCOPE_ALIASES.get(raw_scope))
        if not scope:
            return {
                **base,
                "selected": False,
                "status": "not_selected",
                "reason": "unsupported_scope",
            }
        return {
            **base,
            "selected": True,
            "status": "explicit_first_person_current_preference_query",
            "query_language": language,
            "scope": scope,
            "scope_surface_jp": _SCOPE_SURFACE_JP[scope],
            "epistemic_status": "explicit_observable_query",
        }
    return {
        **base,
        "selected": False,
        "status": "not_selected",
        "reason": "explicit_first_person_current_preference_exact_scope_query_not_detected",
    }


def _localize_value(value):
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    return _VALUE_SURFACE_JP.get(text.casefold()) or _VALUE_SURFACE_JP.get(text) or ""


def _bounded_abstention(query, *, status, reason, candidate_count=0, active_ids=None):
    scope_jp = query["scope_surface_jp"]
    if status == "ambiguous_multiple_active_typed_current_preferences":
        surface = f"今の{scope_jp}の好みが複数残ってる。どれかは断定しない。"
    elif status == "unsupported_active_value_localization":
        surface = f"今の{scope_jp}の好みは見つかったけど、日本語で確実に言い換えられない。"
    elif status == "invalid_active_record_provenance":
        surface = f"今の{scope_jp}の好みは記録にあるけど、根拠が足りないから断定しない。"
    else:
        surface = f"今の{scope_jp}の好みは、記録から確認できない。"
    return {
        **query,
        "status": status,
        "reason": reason,
        "surface_authority": True,
        "answer_use_authorized": False,
        "candidate_count": int(candidate_count),
        "active_memory_ids": list(active_ids or []),
        "selected_core_jp": surface,
        "selected_core_sha256": _digest(surface),
        "profile_write_count": 0,
        "episode_write_changed": False,
        "model_call_added": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "bounded abstention for one explicit typed current-preference query; "
            "no episode fallback, score selection or open-domain inference"
        ),
    }


def build_typed_current_preference_recall_contract_p4(user_input, profile_collection, *, reference_time=None):
    """Read one active P4-I scope without mutating profile or episode state."""
    query = classify_typed_current_preference_query_p4(user_input)
    if not query.get("selected"):
        return query
    reference_time = reference_time or datetime.datetime.now().astimezone().isoformat(
        timespec="microseconds"
    )
    resolved = p4i._current_preference_rows(
        profile_collection,
        reference_time=reference_time,
    )
    scope = query["scope"]
    rows = [
        row
        for row in resolved.get("active") or []
        if _normalize((row.get("metadata") or {}).get("preference_scope")) == _normalize(scope)
    ]
    active_ids = [str(row.get("memory_id") or "") for row in rows if row.get("memory_id")]
    if not rows:
        return _bounded_abstention(
            query,
            status="no_active_typed_current_preference",
            reason="no_active_exact_scope_current_preference_record",
        )
    if len(rows) != 1:
        return _bounded_abstention(
            query,
            status="ambiguous_multiple_active_typed_current_preferences",
            reason="multiple_active_exact_scope_records_no_score_selection",
            candidate_count=len(rows),
            active_ids=active_ids,
        )

    row = rows[0]
    metadata = dict(row.get("metadata") or {})
    memory_id = str(row.get("memory_id") or "")
    required = (
        "source_language",
        "source_input_sha256",
        "preference_scope_sha256",
        "value",
    )
    if not memory_id or any(not metadata.get(field) for field in required):
        return _bounded_abstention(
            query,
            status="invalid_active_record_provenance",
            reason="required_active_record_provenance_missing",
            candidate_count=1,
            active_ids=active_ids,
        )
    value = str(metadata["value"])
    localized = _localize_value(value)
    if not localized:
        return _bounded_abstention(
            query,
            status="unsupported_active_value_localization",
            reason="active_value_not_in_bounded_japanese_localization",
            candidate_count=1,
            active_ids=active_ids,
        )

    scope_jp = query["scope_surface_jp"]
    surface = f"今の{scope_jp}の好みは{localized}。前のじゃなくて、今の方ね。"
    return {
        **query,
        "status": "resolved_unique_active_typed_current_preference",
        "reason": "one_active_exact_scope_p4_i_record_with_supported_localization",
        "surface_authority": True,
        "answer_use_authorized": True,
        "candidate_count": 1,
        "active_memory_id": memory_id,
        "active_memory_ids": [memory_id],
        "source_language": metadata["source_language"],
        "source_input_sha256": metadata["source_input_sha256"],
        "preference_scope_sha256": metadata["preference_scope_sha256"],
        "validity_reason": (resolved.get("decisions") or {}).get(memory_id, {}).get(
            "reason", "active"
        ),
        "value_sha256": _digest(_normalize(value)),
        "localized_value_jp": localized,
        "localized_value_jp_sha256": _digest(localized),
        "selected_core_jp": surface,
        "selected_core_sha256": _digest(surface),
        "historical_answer_use_count": 0,
        "explicit_negative_answer_use_count": 0,
        "episode_answer_use_count": 0,
        "profile_write_count": 0,
        "episode_write_changed": False,
        "model_call_added": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "one active P4-I typed current preference for an explicit first-person exact-scope query; "
            "not open-domain recall or general profile answer authority"
        ),
    }


def query_all_layers_with_typed_current_preference_recall_p4(self, text):
    data = _ORIGINAL_QUERY_ALL_LAYERS(self, text)
    query = classify_typed_current_preference_query_p4(text)
    if query.get("selected"):
        contract = build_typed_current_preference_recall_contract_p4(text, self.profile_col)
    else:
        contract = query
    data[LABEL] = deepcopy(contract)
    return data


def _plan_from_contract(contract):
    resolved = contract.get("status") == "resolved_unique_active_typed_current_preference"
    return {
        "candidate_label": "p4_typed_current_preference_recall",
        "intent": "typed_current_preference_recall",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "現在の明示的な好みを確認している",
        "reply_goal": "active typed stateだけで現在値を短く答える",
        "jp_summary": "ユーザーが現在の明示済みの好みを確認している。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct" if resolved else "reflective",
        "response_mode": "direct_answer" if resolved else "clarify_light",
        "uncertainty": 0.04 if resolved else 0.78,
        "premise_check": "accept" if resolved else "question",
        "self_check": True,
        "subjective_note_jp": "active typed current-preference以外は現在値に使わない",
        "hidden_intent": "memory_probe",
        "user_belief": "現在の好みが記録されていると思っている。",
        "my_hidden_knowledge": "active typed stateだけを使う。",
        "user_expectation": "過去値と混ぜず現在値を短く答える。",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "scope": contract.get("scope"),
            "evidence_status": contract.get("status"),
            "active_memory_id": contract.get("active_memory_id"),
        },
        "payload_level": "low",
        LABEL: deepcopy(contract),
        "planner_path": "typed_current_preference_recall_authority_p4",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 52,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "たぶん", "きっと", "AI"],
    }


def rule_plan_with_typed_current_preference_recall_p4(
    self, user_input, current_psyche, memory_data=None
):
    contract = deepcopy((memory_data or {}).get(LABEL) or {})
    if contract.get("schema") == SCHEMA and contract.get("selected") and contract.get(
        "surface_authority"
    ):
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def _selected_surface_contract(source):
    """Return one already-authorized P4-J contract from a current-turn payload."""
    if not isinstance(source, dict):
        return {}
    contract = deepcopy(source.get(LABEL) or {})
    if (
        contract.get("schema") != SCHEMA
        or contract.get("selected") is not True
        or contract.get("surface_authority") is not True
        or not str(contract.get("selected_core_jp") or "").strip()
    ):
        return {}
    return contract


def visible_guard_with_typed_current_preference_recall_p4(
    self, reply, logic_data, user_input="", memory_data=None
):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self,
        reply,
        logic_data,
        user_input=user_input,
        memory_data=memory_data,
    )
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    if route == "safety_sensitive":
        return visible
    contract = _selected_surface_contract(logic_data) or _selected_surface_contract(memory_data)
    if not contract:
        return visible
    selected = str(contract.get("selected_core_jp") or "").strip()
    before = str(visible or "").strip()
    visible = selected or before
    contract.update(
        visible_surface_status="matched" if selected and visible == selected else "mismatch",
        pre_authority_surface_sha256=_digest(before),
        final_visible_surface_jp=visible,
        final_visible_surface_sha256=_digest(visible),
        final_visible_surface_matches_contract=bool(selected and visible == selected),
        visible_surface_changed=visible != before,
    )
    # Planner normalization intentionally keeps only known plan fields.  The
    # query-stage P4-J contract therefore has to be reattached from this same
    # turn's memory payload before final trace materialization.
    logic_data[LABEL] = contract
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        typed_current_preference_recall_p4=True,
        typed_current_preference_surface_status=contract["visible_surface_status"],
    )
    logic_data["visible_language_guard"] = language_guard
    return visible


def materialize_typed_current_preference_recall_p4(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(
            visible_surface_status="matched"
            if final and final == payload.get("selected_core_jp")
            else "mismatch",
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=bool(
                final and final == payload.get("selected_core_jp")
            ),
            flow=[
                "explicit_first_person_current_preference_query",
                "active_p4_i_typed_state_read",
                "exact_scope_join",
                "unique_active_or_abstain",
                "natural_japanese_surface",
            ],
            raw_dialogue_persisted=False,
        )
        logic[LABEL] = deepcopy(payload)
        index = next(
            (i for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
            next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(
            index,
            {
                "stage": "select",
                "label": LABEL,
                "payload": deepcopy(payload),
                "salience": 1.0,
            },
        )
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_typed_current_preference_recall_p4():
    global _INSTALLED, _ORIGINAL_QUERY_ALL_LAYERS, _ORIGINAL_RULE_PLAN
    global _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_QUERY_ALL_LAYERS = MemoryManager.query_all_layers
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready

    MemoryManager.query_all_layers = query_all_layers_with_typed_current_preference_recall_p4
    LeftBrain._rule_based_plan = rule_plan_with_typed_current_preference_recall_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_typed_current_preference_recall_p4

    def finish(self, result):
        materialize_typed_current_preference_recall_p4(result)
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
