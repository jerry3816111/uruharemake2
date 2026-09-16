"""Bounded speaker-qualified fact recall from already-selected evidence.

This product adapter covers one explicit act that the quoted-source P2 adapter
does not: asking for the user's own previously stated preference. It never
searches unselected memory and never asks a model to infer the speaker.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata


LABEL = "speaker_qualified_fact_p3"
SCHEMA = "uruha_speaker_qualified_fact_p3"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_PREFERENCE_QUERIES = (
    (
        "en",
        re.compile(
            r"\bwhat(?:\s+kind|\s+type)?\s+of\s+"
            r"(?P<category>[a-z][a-z0-9 -]{0,32}?)\s+did\s+i\s+say\s+i\s+"
            r"(?:prefer|like)\b",
            re.I,
        ),
    ),
    (
        "zh",
        re.compile(
            r"我(?:之前|剛才|刚才|剛剛|刚刚)?(?:有)?(?:說|说)(?:過|过)?我"
            r"(?:比較|比较)?(?:喜歡|喜欢)(?:哪(?:一)?種|哪种|什麼樣|什么样)"
            r"(?P<category>[^？?，。]{1,20})"
        ),
    ),
    (
        "ja",
        re.compile(
            r"(?:前に|さっき)?どんな(?P<category>[^？?、。]{1,20}?)"
            r"(?:が|を)(?:好き|好み)(?:って|と)言った"
        ),
    ),
)

_METALINGUISTIC = re.compile(
    r"(?:どういう意味|意味は|什麼意思|什么意思|怎麼翻|怎么翻|翻譯|翻译|"
    r"\bwhat\s+does\b.+\bmean\b|\btranslate\b|\btranslation\b)",
    re.I,
)


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalize(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`「」『』“”()（）:：;；]+", "", text)


def classify_speaker_qualified_fact_p3(user_input):
    """Classify only explicit observable wording; retain no raw input."""
    text = str(user_input or "")
    input_digest = _digest(text)
    if _METALINGUISTIC.search(text):
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": "metalinguistic_or_translation_context",
            "input_digest": input_digest,
            "raw_dialogue_persisted": False,
        }
    for language, pattern in _PREFERENCE_QUERIES:
        match = pattern.search(text)
        if match:
            category = match.group("category").strip()
            return {
                "schema": SCHEMA,
                "status": "explicit_first_person_preference_recall",
                "selected": True,
                "fact_kind": "first_person_preference_recall",
                "query_language": language,
                "input_digest": input_digest,
                "category_digest": _digest(_normalize(category)),
                "epistemic_status": "selected_memory_required",
                "raw_dialogue_persisted": False,
                "_category_runtime_only": category,
            }
    return {
        "schema": SCHEMA,
        "status": "not_selected",
        "selected": False,
        "reason": "explicit_speaker_qualified_fact_act_not_detected",
        "input_digest": input_digest,
        "raw_dialogue_persisted": False,
    }


def _parse_memory_user(text):
    text = str(text or "")
    episode = re.search(
        r"(?:^|\|\s*)User:\s*(.*?)\s*\|\s*Summary:.*?\|\s*Uruha:",
        text,
        re.S,
    )
    if episode:
        return episode.group(1).strip()
    short = re.search(r"User:\s*(.*?)\s*->\s*Uruha:", text, re.S)
    return short.group(1).strip() if short else ""


def _selected_user_evidence(memory_data):
    rows = []
    for turn in (memory_data or {}).get("recent_turns") or []:
        user = str((turn or {}).get("user") or "").strip()
        if user:
            episode_id = str((turn or {}).get("episode_id") or "") or None
            rows.append({
                "user": user,
                "source": "recent_turn",
                "trace_id": f"stored:episode:{episode_id}" if episode_id else None,
                "memory_id": episode_id,
                "score": 1.0,
            })
    for item in (memory_data or {}).get("working_memory_items") or []:
        if item.get("selected") is False:
            continue
        user = _parse_memory_user(item.get("text"))
        if user:
            rows.append({
                "user": user,
                "source": str(item.get("source") or "working_memory"),
                "trace_id": item.get("trace_id"),
                "memory_id": item.get("memory_id"),
                "score": float(item.get("score") or 0.0),
            })
    deduped = {}
    for row in rows:
        key = row.get("memory_id") or row.get("trace_id") or _digest(row["user"])
        previous = deduped.get(key)
        if previous is None or row["score"] > previous["score"]:
            deduped[key] = row
    return list(deduped.values())


def _preference_values(user_utterance):
    text = str(user_utterance or "")
    patterns = (
        re.compile(
            r"\bI\s+(?:said\s+(?:that\s+)?I\s+)?(?:prefer|like)\s+"
            r"(?P<value>[^.!?]{2,80})",
            re.I,
        ),
        re.compile(
            r"我(?:說|说)(?:我)?(?:比較|比较)?(?:喜歡|喜欢)"
            r"(?P<value>[^，。！？?]{1,40})"
        ),
        re.compile(
            r"(?:私は|うちは|自分は)(?P<value>[^、。！？?]{1,40}?)"
            r"(?:が|を)(?:好き|好み)(?:って言った|と言った)?"
        ),
    )
    values = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = re.sub(r"\s+", " ", match.group("value")).strip(" 、,，。.!！?")
            if value and value not in values:
                values.append(value)
    return values


def _category_matches(category, value):
    category_norm, value_norm = _normalize(category), _normalize(value)
    if not category_norm or not value_norm:
        return False
    if re.search(r"[a-z]", str(category).lower()):
        category_tokens = re.findall(r"[a-z]+", str(category).lower())
        value_tokens = re.findall(r"[a-z]+", str(value).lower())
        stems = {token[:-1] if token.endswith("s") and len(token) > 3 else token for token in value_tokens}
        return any(
            (token[:-1] if token.endswith("s") and len(token) > 3 else token) in stems
            for token in category_tokens
        )
    return category_norm in value_norm or value_norm in category_norm


def _localize_preference_value(value):
    normalized = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    replacements = {
        "plain glass cups": "無地のガラスコップ",
        "plain glass cup": "無地のガラスコップ",
        "black coffee": "ブラックコーヒー",
        "herbal tea": "ハーブティー",
        "ceramic mugs": "陶器のマグカップ",
        "ceramic mug": "陶器のマグカップ",
        "透明玻璃杯": "透明なガラスコップ",
        "無糖茶": "無糖のお茶",
        "无糖茶": "無糖のお茶",
    }
    if normalized in replacements:
        return replacements[normalized]
    value = str(value or "").strip()
    if re.search(r"[ぁ-んァ-ヶー]", value) and not re.search(r"[A-Za-z]", value):
        return value
    return ""


def build_speaker_qualified_fact_contract_p3(user_input, memory_data):
    query = classify_speaker_qualified_fact_p3(user_input)
    category = query.pop("_category_runtime_only", "")
    if not query.get("selected"):
        return query
    candidates = []
    for row in _selected_user_evidence(memory_data or {}):
        for value in _preference_values(row["user"]):
            if not _category_matches(category, value):
                continue
            localized = _localize_preference_value(value)
            candidates.append({
                "speaker_role": "user",
                "value_digest": _digest(_normalize(value)),
                "localized_value_jp": localized or None,
                "localized_value_sha256": _digest(localized) if localized else None,
                "source": row.get("source"),
                "trace_id": row.get("trace_id"),
                "memory_id": row.get("memory_id"),
                "retrieval_score": round(float(row.get("score") or 0.0), 4),
            })
    unique = {}
    for candidate in candidates:
        key = candidate["value_digest"]
        previous = unique.get(key)
        if previous is None or candidate["retrieval_score"] > previous["retrieval_score"]:
            unique[key] = candidate
    values = sorted(unique.values(), key=lambda row: -row["retrieval_score"])
    if len(values) == 1 and values[0]["localized_value_jp"]:
        status = "resolved_unique_user_preference"
        selected_speaker = "user"
        core = f"あんたが好みって言ってたのは{values[0]['localized_value_jp']}。"
        reason = "one_category_matching_first_person_preference_in_selected_memory"
    elif len(values) > 1:
        status = "ambiguous_multiple_user_preferences"
        selected_speaker = None
        core = "候補が二つある。どっちの好みの話？"
        reason = "multiple_category_matching_first_person_preferences"
    elif len(values) == 1:
        status = "unsupported_value_localization"
        selected_speaker = "user"
        core = "その好み、今の記憶だけじゃ日本語で確実に答えられない。"
        reason = "selected_preference_value_cannot_be_safely_localized"
    else:
        status = "not_found_in_selected_memory"
        selected_speaker = None
        core = "その好み、今の記憶からは確認できない。"
        reason = "no_category_matching_first_person_preference_in_selected_memory"
    return {
        **query,
        "status": status,
        "reason": reason,
        "surface_authority": True,
        "selected_speaker": selected_speaker,
        "candidate_count": len(values),
        "candidates": values[:12],
        "selected_core_jp": core,
        "selected_core_sha256": _digest(core),
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "first-person preference from already-selected speaker-qualified evidence; category match and bounded localization, not open-domain recall",
    }


def _plan_from_contract(contract):
    resolved = contract.get("status") == "resolved_unique_user_preference"
    return {
        "candidate_label": "p3_speaker_fact",
        "intent": "speaker_qualified_fact_recall",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "前に話した事実の持ち主を確かめている",
        "reply_goal": "選択済みの話者根拠だけで答える",
        "jp_summary": "ユーザーが人ごとの情報を混同せず扱うよう求めている。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct" if resolved else "reflective",
        "response_mode": "direct_answer" if resolved else "clarify_light",
        "uncertainty": 0.08 if resolved else 0.72,
        "premise_check": "accept" if resolved else "question",
        "self_check": True,
        "subjective_note_jp": "話者付きの選択済み根拠以外は使わない",
        "hidden_intent": "memory_probe",
        "user_belief": "人ごとの情報を区別できると思っている。",
        "my_hidden_knowledge": "選択済み記憶だけを使う。",
        "user_expectation": "誰の情報かを混ぜず短く答える。",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "speaker_role": contract.get("selected_speaker") or "unknown",
            "evidence_status": contract.get("status"),
        },
        "payload_level": "medium",
        "memory_recall_contract": deepcopy(contract),
        "planner_path": "speaker_qualified_selected_fact_p3",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 46,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "たぶん", "きっと", "AI"],
    }


def rule_plan_with_speaker_qualified_fact_p3(self, user_input, current_psyche, memory_data=None):
    contract = build_speaker_qualified_fact_contract_p3(user_input, memory_data or {})
    if contract.get("selected") and contract.get("surface_authority"):
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def visible_guard_with_speaker_qualified_fact_p3(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self,
        reply,
        logic_data,
        user_input=user_input,
        memory_data=memory_data,
    )
    contract = deepcopy((logic_data or {}).get("memory_recall_contract") or {})
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    if contract.get("schema") != SCHEMA or not contract.get("surface_authority") or route == "safety_sensitive":
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
    logic_data["memory_recall_contract"] = contract
    m39 = deepcopy(logic_data.get("semantic_persona_surface_verifier_m39") or {})
    if m39:
        m39.update(
            effective_after_speaker_qualified_fact_p3=False,
            downstream_authority=LABEL,
            pre_authority_status=m39.get("status"),
        )
        logic_data["semantic_persona_surface_verifier_m39"] = m39
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        speaker_qualified_fact_p3=True,
        speaker_qualified_fact_surface_status=contract["visible_surface_status"],
    )
    logic_data["visible_language_guard"] = language_guard
    return visible


def materialize_speaker_qualified_fact_p3(result):
    logic = result.setdefault("logic", {})
    payload = deepcopy(logic.get("memory_recall_contract") or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        payload.update(
            visible_surface_status="matched" if final and final == payload.get("selected_core_jp") else "mismatch",
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=bool(final and final == payload.get("selected_core_jp")),
            flow=[
                "explicit_speaker_qualified_fact_act",
                "selected_memory_evidence",
                "speaker_role_and_category_join",
                "unique_or_abstain",
                "visible_japanese_surface",
            ],
        )
        logic["memory_recall_contract"] = deepcopy(payload)
        index = next(
            (i for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
            next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(index, {
            "stage": "select",
            "label": LABEL,
            "payload": deepcopy(payload),
            "salience": 1.0,
        })
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_speaker_qualified_fact_p3():
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

    LeftBrain._rule_based_plan = rule_plan_with_speaker_qualified_fact_p3
    RightBrain.enforce_user_visible_japanese = visible_guard_with_speaker_qualified_fact_p3

    def finish(self, result):
        materialize_speaker_qualified_fact_p3(result)
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
