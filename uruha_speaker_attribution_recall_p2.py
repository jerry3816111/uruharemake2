"""Product-only, evidence-bounded speaker attribution for quoted recall.

The normal memory retriever can surface a relevant episode while preserving
``User`` and ``Uruha`` roles, but the planner has no task contract for questions
such as ``「ありがとう」は誰の言葉だった？``.  This adapter joins an explicit
quoted-source query only to already-selected memory evidence.  It never scans
unretrieved memory and never asks a model to guess the speaker.
"""
from copy import deepcopy
import hashlib
import json
import re
import unicodedata


LABEL = "speaker_attribution_recall_p2"
SCHEMA = "uruha_speaker_attribution_recall_p2"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_QUOTED = re.compile(
    r"「(?P<corner>[^」]{1,80})」"
    r"|『(?P<double_corner>[^』]{1,80})』"
    r"|“(?P<curly>[^”]{1,80})”"
    r'|"(?P<double>[^"\n]{1,80})"'
    r"|'(?P<single>[^'\n]{1,80})'"
)
_SOURCE_QUERY = re.compile(
    r"(?:"
    r"(?:誰|だれ)(?:の言葉|が言った|が言ってた|が口にした)"
    r"|(?:是|係)?(?:誰|谁)(?:說|说|講|讲|的話|的话|講的|讲的)"
    r"|\bwho\s+(?:said|wrote)\b"
    r"|\bwhose\s+(?:words?|line|phrase)\b"
    r")",
    re.I,
)
_METALINGUISTIC = re.compile(
    r"(?:どういう意味|何て意味|意味は|什麼意思|什么意思|怎麼翻|怎么翻|翻譯|翻译|"
    r"\bwhat\s+does\b.+\bmean\b|\btranslate\b|\btranslation\b)",
    re.I,
)

_GRATITUDE_MARKERS = {
    "ja": ("ありがとう", "ありがと", "感謝", "助かった"),
    "zh": ("謝謝", "谢谢", "感謝", "感谢"),
    "en": ("thankyou", "thanks", "thanksthatalot"),
}


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalize_surface(value):
    value = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`「」『』“”()（）:：;；]+", "", value)


def _semantic_atom(value):
    normalized = _normalize_surface(value)
    for markers in _GRATITUDE_MARKERS.values():
        if any(_normalize_surface(marker) in normalized for marker in markers):
            return "gratitude"
    return None


def _observable_surface_language(value):
    """Classify only the script/marker visible in the selected utterance."""
    normalized = _normalize_surface(value)
    marker_languages = {
        language
        for language, markers in _GRATITUDE_MARKERS.items()
        if any(_normalize_surface(marker) in normalized for marker in markers)
    }
    if len(marker_languages) == 1:
        return next(iter(marker_languages))
    text = str(value or "")
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def classify_quoted_source_query_p2(user_input):
    """Return quote geometry without retaining the quoted surface."""
    text = str(user_input or "")
    match = _QUOTED.search(text)
    if not match or not _SOURCE_QUERY.search(text) or _METALINGUISTIC.search(text):
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": (
                "metalinguistic_or_translation_context"
                if _METALINGUISTIC.search(text)
                else "quoted_speaker_source_query_not_detected"
            ),
            "input_digest": _digest(text),
            "raw_dialogue_persisted": False,
        }
    quote = next(value for value in match.groupdict().values() if value is not None).strip()
    normalized = _normalize_surface(quote)
    if not normalized:
        return {
            "schema": SCHEMA,
            "status": "not_selected",
            "selected": False,
            "reason": "empty_normalized_quote",
            "input_digest": _digest(text),
            "raw_dialogue_persisted": False,
        }
    return {
        "schema": SCHEMA,
        "status": "quoted_speaker_source_query",
        "selected": True,
        "reason": "explicit_quoted_phrase_and_speaker_question",
        "input_digest": _digest(text),
        "quote_start": match.start(),
        "quote_end": match.end(),
        "quote_length": len(quote),
        "quote_digest": _digest(normalized),
        "semantic_atom": _semantic_atom(quote),
        "epistemic_status": "known_observable_source_query",
        "raw_dialogue_persisted": False,
        "_normalized_quote_runtime_only": normalized,
    }


def _parse_combined_memory_text(text):
    text = str(text or "")
    episode = re.search(
        r"(?:^|\|\s*)User:\s*(.*?)\s*\|\s*Summary:.*?\|\s*Uruha:\s*(.*?)\s*\|\s*Mood:",
        text,
        re.S,
    )
    if episode:
        return episode.group(1).strip(), episode.group(2).strip()
    short = re.search(r"User:\s*(.*?)\s*->\s*Uruha:\s*(.*)$", text, re.S)
    if short:
        return short.group(1).strip(), short.group(2).strip()
    return None, None


def _selected_memory_turns(memory_data):
    memory_data = memory_data or {}
    rows = []
    for turn in memory_data.get("recent_turns") or []:
        user = str(turn.get("user") or "").strip()
        reply = str(turn.get("reply") or "").strip()
        if not user and not reply:
            continue
        episode_id = str(turn.get("episode_id") or "") or None
        rows.append(
            {
                "user": user,
                "uruha": reply,
                "source": "recent_turn",
                "trace_id": f"stored:episode:{episode_id}" if episode_id else None,
                "memory_id": episode_id,
                "source_key": episode_id or _digest([user, reply]),
                "score": 1.0,
            }
        )
    for item in memory_data.get("working_memory_items") or []:
        if item.get("selected") is False:
            continue
        user, reply = _parse_combined_memory_text(item.get("text"))
        if user is None and reply is None:
            continue
        memory_id = str(item.get("memory_id") or "") or None
        trace_id = str(item.get("trace_id") or "") or None
        rows.append(
            {
                "user": user or "",
                "uruha": reply or "",
                "source": str(item.get("source") or "working_memory"),
                "trace_id": trace_id,
                "memory_id": memory_id,
                "source_key": memory_id or trace_id or _digest([user, reply]),
                "score": float(item.get("score") or 0.0),
            }
        )
    deduped = {}
    for row in rows:
        key = row["source_key"]
        existing = deduped.get(key)
        if existing is None or (not existing.get("memory_id") and row.get("memory_id")):
            deduped[key] = row
    return list(deduped.values())


def _match_kind(normalized_quote, query_atom, utterance):
    normalized_utterance = _normalize_surface(utterance)
    if not normalized_utterance:
        return None
    if normalized_quote in normalized_utterance:
        return "normalized_exact"
    if query_atom and query_atom == _semantic_atom(utterance):
        return "bounded_crosslingual_semantic_atom"
    return None


def build_speaker_attribution_contract_p2(user_input, memory_data):
    """Join an explicit query to speaker-qualified, already-selected evidence."""
    query = classify_quoted_source_query_p2(user_input)
    runtime_quote = query.pop("_normalized_quote_runtime_only", None)
    if not query.get("selected"):
        return query

    candidates = []
    for turn in _selected_memory_turns(memory_data):
        for role in ("user", "uruha"):
            utterance = turn.get(role) or ""
            match_kind = _match_kind(runtime_quote, query.get("semantic_atom"), utterance)
            if not match_kind:
                continue
            candidates.append(
                {
                    "speaker_role": role,
                    "match_kind": match_kind,
                    "semantic_atom": query.get("semantic_atom"),
                    "utterance_language": _observable_surface_language(utterance),
                    "utterance_digest": _digest(_normalize_surface(utterance)),
                    "trace_id": turn.get("trace_id"),
                    "memory_id": turn.get("memory_id"),
                    "source": turn.get("source"),
                    "source_key_digest": _digest(turn.get("source_key")),
                    "retrieval_score": round(float(turn.get("score") or 0.0), 4),
                }
            )

    candidates.sort(
        key=lambda row: (
            row["match_kind"] != "normalized_exact",
            -row["retrieval_score"],
            row["speaker_role"],
        )
    )
    roles = sorted({row["speaker_role"] for row in candidates})
    if len(roles) == 1:
        status = "resolved_unique_speaker"
        selected_speaker = roles[0]
        selected_language = str(candidates[0].get("utterance_language") or "unknown")
        language_label = {"zh": "中国語", "en": "英語", "ja": "日本語"}.get(
            selected_language
        )
        core = (
            f"それ、あんたが言ったやつ。前に{language_label}でお礼を言ってた。"
            if selected_speaker == "user"
            and query.get("semantic_atom") == "gratitude"
            and language_label
            else "それ、あんたが言ったやつ。前にお礼を言ってた。"
            if selected_speaker == "user" and query.get("semantic_atom") == "gratitude"
            else "それ、あんたが言ったやつ。"
            if selected_speaker == "user"
            else "それ、うちが言ったやつ。"
        )
        reason = "selected_memory_evidence_points_to_one_speaker_role"
    elif len(roles) > 1:
        status = "ambiguous_multiple_speakers"
        selected_speaker = None
        selected_language = None
        core = "それ、あんたもうちも言ってる。どの場面のこと？"
        reason = "selected_memory_contains_matching_evidence_for_both_roles"
    else:
        status = "not_found_in_selected_memory"
        selected_speaker = None
        selected_language = None
        core = "その言葉、今の記憶からは誰のか確認できない。"
        reason = "no_matching_speaker_evidence_in_selected_memory"

    return {
        **query,
        "status": status,
        "reason": reason,
        "surface_authority": True,
        "selected_speaker": selected_speaker,
        "selected_utterance_language": selected_language,
        "candidate_roles": roles,
        "candidate_count": len(candidates),
        "candidates": candidates[:12],
        "selected_core_jp": core,
        "selected_core_sha256": _digest(core),
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "speaker role from selected memory provenance; exact quote plus bounded gratitude atom, not open-domain semantic recall",
    }


def _plan_from_contract(contract):
    ambiguity = contract.get("status") != "resolved_unique_speaker"
    return {
        "candidate_label": "p2_speaker_source",
        "intent": "speaker_attribution_recall",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "前の発話者を記憶から確かめている",
        "reply_goal": "取得済みの話者根拠だけで答え、なければ推測しない",
        "jp_summary": "ユーザーが引用した言葉を誰が発したか確認している。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "reflective" if ambiguity else "direct",
        "response_mode": "clarify_light" if contract.get("status") == "ambiguous_multiple_speakers" else "direct_answer_with_hedge" if ambiguity else "direct_answer",
        "uncertainty": 0.72 if ambiguity else 0.08,
        "premise_check": "question" if ambiguity else "accept",
        "self_check": True,
        "subjective_note_jp": "話者ラベルのある取得済み記憶だけを使う",
        "hidden_intent": "memory_probe",
        "user_belief": "以前の言葉の話者を確認できると思っている。",
        "my_hidden_knowledge": "取得済み記憶の話者ラベル以外は使わない。",
        "user_expectation": "誰が言ったかを短く直接答える。",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "speaker_role": contract.get("selected_speaker") or "unknown",
            "evidence_status": contract.get("status"),
        },
        "payload_level": "medium",
        "memory_recall_contract": deepcopy(contract),
        "planner_path": "speaker_qualified_selected_memory_p2",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 40,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "たぶん", "きっと", "AI"],
    }


def rule_plan_with_speaker_attribution_p2(self, user_input, current_psyche, memory_data=None):
    contract = build_speaker_attribution_contract_p2(user_input, memory_data or {})
    if contract.get("selected") and contract.get("surface_authority"):
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def visible_guard_with_speaker_attribution_p2(self, reply, logic_data, user_input="", memory_data=None):
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
            effective_after_speaker_attribution_recall_p2=False,
            downstream_authority=LABEL,
            pre_authority_status=m39.get("status"),
        )
        logic_data["semantic_persona_surface_verifier_m39"] = m39
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=visible,
        final_reply_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        speaker_attribution_recall_p2=True,
        speaker_attribution_surface_status=contract["visible_surface_status"],
    )
    logic_data["visible_language_guard"] = language_guard
    return visible


def materialize_speaker_attribution_recall_p2(result):
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
                "quoted_source_query",
                "selected_memory_evidence",
                "speaker_role_join",
                "unique_or_abstain",
                "visible_japanese_surface",
            ],
        )
        logic["memory_recall_contract"] = deepcopy(payload)
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


def install_speaker_attribution_recall_p2():
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

    LeftBrain._rule_based_plan = rule_plan_with_speaker_attribution_p2
    RightBrain.enforce_user_visible_japanese = visible_guard_with_speaker_attribution_p2

    def finish(self, result):
        materialize_speaker_attribution_recall_p2(result)
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


__all__ = [
    "LABEL",
    "SCHEMA",
    "build_speaker_attribution_contract_p2",
    "classify_quoted_source_query_p2",
    "install_speaker_attribution_recall_p2",
    "materialize_speaker_attribution_recall_p2",
]
