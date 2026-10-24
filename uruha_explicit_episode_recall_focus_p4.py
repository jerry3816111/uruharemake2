"""Opt-in, source-bound recall of one explicit Japanese user assertion.

The ordinary retriever remains authoritative about what it retrieved and how it
ranked it.  This adapter may pass an otherwise unselected *episode* to the
planner only when an explicit, narrow question matches one unique User span.
It does not infer a fact from the episode's Summary or Uruha span, alter global
ranking, or write a profile fact.  The same receipt binds handoff, plan, final
surface, and the debug graph; it is not an open-domain memory resolver.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata
import uuid

import uruha_adaptive_person_model as adaptive_person
import uruha_memory_runtime as umr


LABEL = "explicit_episode_recall_focus_p4"
SCHEMA = "uruha_explicit_episode_recall_focus_p4"
PLANNER_PATH = "explicit_episode_recall_focus_p4"
HANDOFF_CHANNEL = "explicit_recall_focus_handoff"
_INSTALLED = False
_ORIGINAL_QUERY = None
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_QUERY = re.compile(
    r"(?:さっき|前に|以前)(?:私が|うちが)?"
    r"(?:言った|話した|教えた|決めた)"
    r"(?P<focus>[^、，,。.!！？?「」『』\n]{2,32})"
    r"[、，,\s]*覚えて(?:る|いる)[?？]"
)
_ASSERTION = re.compile(
    r"(?P<lhs>[^は。.!！？?「」『』|:\n：]{2,40})は"
    r"(?P<rhs>[^。.!！？?「」『』|:\n：]{1,80})[。.!]?"
)
_RETRACTION = re.compile(
    r"(?:取り消|撤回|訂正|修正|変更|違った|違う|じゃなくて|ではなく|変えた|"
    r"変わった|やめた|まだ.{0,12}(?:決めてない|決まってない|未定|分からない))"
)
_REPORTED = re.compile(r"(?:と(?:言った|言ってた|聞いた)|によると|そう言って)")
_PROTECTED = re.compile(
    r"(?:死にたい|自殺|自傷|傷つけ|救急|緊急|今すぐ助けて|"
    r"パスワード|暗証番号|口座番号|住所|電話番号|秘密|password|secret)",
    re.I,
)
_SOURCE_SECRET = re.compile(
    r"(?:合言葉|パスワード|パスコード|暗証番号|認証コード|確認コード|"
    r"ワンタイムコード|秘密の番号|口座番号|電話番号|住所|password|passcode|secret)",
    re.I,
)
_EPISODE_FIELDS = (" | User: ", " | Summary: ", " | Uruha: ", " | Mood: ")
_UNKNOWN_CORE = "そこは今、確かには言えない。もう一度教えて。"


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _focus_key(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"[\s\u3000、，,。.!！？?「」『』()（）]", "", text)
    # Japanese attributive phrasing, not a topic-specific answer dictionary.
    return text.replace("する", "").replace("の", "")


def _focus_bigrams(value: str) -> set[str]:
    key = _focus_key(value)
    return {key[index : index + 2] for index in range(len(key) - 1)}


def classify_explicit_episode_recall_focus_p4(user_input: str) -> dict:
    """Recognize only an unquoted, concrete Japanese past-utterance question."""
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    base = {
        "schema": SCHEMA,
        "input_sha256": _sha(text),
        "eligible": False,
        "status": "not_applicable",
        "surface_authority": False,
        "model_call_added": False,
        "profile_write_count": 0,
    }
    if not text or any(mark in text for mark in "「」『』“”\"'") or _PROTECTED.search(text):
        return {**base, "reason": "quoted_or_protected_or_empty"}
    match = _QUERY.fullmatch(text)
    if not match:
        return {**base, "reason": "not_concrete_japanese_recall_query"}
    focus = match.group("focus").strip()
    key = _focus_key(focus)
    if len(key) < 2 or not re.search(r"[\u3400-\u9fff]{2}", key):
        return {**base, "reason": "focus_not_sufficiently_specific"}
    return {
        **base,
        "eligible": True,
        "status": "query_recognized",
        "reason": "explicit_concrete_past_utterance_query",
        "focus_text": focus,
        "focus_key": key,
        "focus_sha256": _sha(key),
    }


def _episode_user_span(document: str) -> str:
    """Read the serializer's User span; reject delimiter injection/ambiguity."""
    text = str(document or "")
    if any(text.count(field) != 1 for field in _EPISODE_FIELDS):
        return ""
    positions = [text.index(field) for field in _EPISODE_FIELDS]
    if positions != sorted(positions):
        return ""
    user = text[positions[0] + len(_EPISODE_FIELDS[0]) : positions[1]].strip()
    if not user or len(user) > 120 or "|" in user or "\n" in user:
        return ""
    return user


def _direct_assertion(user: str) -> tuple[str, str] | None:
    if (
        any(mark in user for mark in "「」『』“”\"'|\n")
        or _REPORTED.search(user)
        or re.search(r"[A-Za-z]", user)
    ):
        return None
    match = _ASSERTION.fullmatch(user.strip())
    if not match:
        return None
    lhs, rhs = match.group("lhs").strip(), match.group("rhs").strip()
    if not lhs or not rhs or len(user) > 90:
        return None
    # A Japanese utterance can be quoted without translating an unknown value.
    if not re.search(r"[ぁ-んァ-ヶ]", user):
        return None
    return lhs, rhs


def _valid_pool_rows(provenance: dict) -> tuple[list[dict], str | None]:
    pool = provenance.get("candidate_pool")
    retrieved = provenance.get("retrieved_candidates")
    selected_ids = provenance.get("selected_working_memory_trace_ids")
    if not isinstance(pool, list) or not isinstance(retrieved, list) or not isinstance(selected_ids, list):
        return [], "missing_provenance_lists"
    if provenance.get("candidate_count") != len(pool):
        return [], "candidate_count_mismatch"
    if not isinstance(provenance.get("working_memory_limit"), int):
        return [], "working_memory_limit_missing"
    retrieved_by_id = {
        row.get("trace_id"): row
        for row in retrieved
        if isinstance(row, dict) and row.get("ranking_status") == "ranked"
    }
    episode_rows = []
    for row in pool:
        if not isinstance(row, dict):
            return [], "malformed_candidate_row"
        if row.get("source") != "episode":
            continue
        memory_id = str(row.get("memory_id") or "")
        try:
            valid_id = str(uuid.UUID(memory_id)) == memory_id
        except (ValueError, AttributeError):
            valid_id = False
        trace_id = f"stored:episode:{memory_id}"
        original = retrieved_by_id.get(trace_id)
        if (
            not valid_id
            or row.get("collection_name") != "episode"
            or row.get("trace_id") != trace_id
            or row.get("channel") != "working_memory_candidate"
            or not isinstance(row.get("rank"), int)
            or not isinstance(row.get("selected"), bool)
            or bool(row["selected"]) != (trace_id in selected_ids)
            or not isinstance(row.get("text"), str)
            or original is None
            or original.get("source") != "episode"
            or original.get("memory_id") != memory_id
            or original.get("text") != row.get("text")
            or not _episode_user_span(row["text"])
        ):
            return [], "episode_provenance_incomplete"
        episode_rows.append(row)
    return episode_rows, None


def _abstention(query: dict, status: str, reason: str, *, candidates: int = 0) -> dict:
    return {
        **query,
        "status": status,
        "reason": reason,
        "surface_authority": True,
        "source_selected": False,
        "candidate_count": candidates,
        "selected_core_jp": _UNKNOWN_CORE,
        "selected_core_sha256": _sha(_UNKNOWN_CORE),
        "claim_boundary": "unverified or conflicting source; do not infer a past user fact",
    }


def build_explicit_episode_recall_focus_contract_p4(user_input: str, memory_data: dict) -> dict:
    """Choose one retrieved, source-proven episode without changing top-k."""
    query = classify_explicit_episode_recall_focus_p4(user_input)
    if not query["eligible"]:
        return query
    provenance = (memory_data or {}).get("memory_provenance") or {}
    if not isinstance(provenance, dict):
        return _abstention(query, "unavailable", "memory_provenance_missing")
    pool, error = _valid_pool_rows(provenance)
    if error:
        return _abstention(query, "unavailable", error)
    focus = query["focus_key"]
    matches = []
    retracted = False
    sensitive = False
    max_competitor_overlap = 0
    query_bigrams = _focus_bigrams(focus)
    for row in pool:
        user = _episode_user_span(row["text"])
        assertion = _direct_assertion(user)
        if _RETRACTION.search(user) and focus in _focus_key(user):
            retracted = True
        if not assertion:
            continue
        lhs_key = _focus_key(assertion[0])
        if lhs_key != focus:
            max_competitor_overlap = max(
                max_competitor_overlap, len(query_bigrams & _focus_bigrams(lhs_key))
            )
            continue
        if _SOURCE_SECRET.search(user):
            sensitive = True
            continue
        speakability = umr.assess_memory_speakability(
            {"source_text": user, "value": user, "jp_anchor": user, "expected": True, "relevance": 1.0},
            user_input=user_input,
        )
        if not speakability.get("should_use_explicitly") or not speakability.get("can_quote"):
            sensitive = True
            continue
        matches.append((row, user, assertion))
    if retracted:
        return _abstention(query, "retracted_or_uncertain", "matching_source_retraction", candidates=len(matches))
    if sensitive:
        return _abstention(query, "suppressed", "matching_source_not_speakable", candidates=len(matches))
    if len(query_bigrams) < 2 or len(query_bigrams) - max_competitor_overlap < 1:
        return _abstention(query, "ambiguous_focus", "insufficient_focus_margin", candidates=len(matches))
    if len(matches) != 1:
        return _abstention(
            query,
            "unavailable" if not matches else "conflicting_or_nonunique",
            "no_unique_direct_user_assertion",
            candidates=len(matches),
        )
    row, user, (_, value) = matches[0]
    prior_passed_channels = sorted({
        str(item.get("channel") or "unknown")
        for item in provenance.get("passed_to_leftbrain") or []
        if isinstance(item, dict) and item.get("trace_id") == row["trace_id"]
    })
    quote = user.rstrip("。.! ")
    core = f"「{quote}」って言ってた。"
    if len(core) > 40:
        return _abstention(query, "unavailable", "source_quote_exceeds_plan_core_limit", candidates=1)
    return {
        **query,
        "status": "selected_unique_user_episode",
        "reason": "unique_direct_user_assertion_with_exact_focus",
        "surface_authority": True,
        "source_selected": True,
        "candidate_count": 1,
        "focus_shared_bigram_count": len(query_bigrams),
        "focus_runner_up_shared_bigram_count": max_competitor_overlap,
        "focus_margin": len(query_bigrams) - max_competitor_overlap,
        "source": "episode",
        "memory_id": row["memory_id"],
        "trace_id": row["trace_id"],
        "source_user_utterance": user,
        "source_user_sha256": _sha(user),
        "source_value_sha256": _sha(value),
        "candidate_rank": row["rank"],
        "ordinary_working_memory_selected": row["selected"],
        "prior_passed_channels": prior_passed_channels,
        "working_memory_limit": provenance["working_memory_limit"],
        "handoff_channel": HANDOFF_CHANNEL,
        "selected_core_jp": core,
        "selected_core_sha256": _sha(core),
        "claim_boundary": "one exact-focus Japanese direct User span from an already retrieved episode; not inferred psychology or open-domain recall",
    }


def query_all_layers_with_explicit_episode_recall_focus_p4(self, text: str) -> dict:
    memory_data = _ORIGINAL_QUERY(self, text)
    if not isinstance(memory_data, dict):
        return memory_data
    contract = build_explicit_episode_recall_focus_contract_p4(text, memory_data)
    if not contract.get("eligible"):
        return memory_data
    memory_data[LABEL] = deepcopy(contract)
    provenance = memory_data.get("memory_provenance")
    if not isinstance(provenance, dict):
        return memory_data
    provenance["explicit_recall_focus_handoff"] = {
        "schema": SCHEMA,
        "status": contract["status"],
        "trace_id": contract.get("trace_id"),
        "candidate_rank": contract.get("candidate_rank"),
        "channel": HANDOFF_CHANNEL if contract.get("source_selected") else None,
    }
    if contract.get("source_selected"):
        row = next(
            (item for item in provenance.get("candidate_pool") or [] if item.get("trace_id") == contract["trace_id"]),
            None,
        )
        if row is not None:
            handed = umr.memory_trace_row(row, channel=HANDOFF_CHANNEL)
            # The graph merges handoff rows after candidate_pool.  Carry the
            # retriever's rank and top-k flag so a rank>5 handoff cannot look
            # like an ordinary selected working-memory item in that view.
            handed["rank"] = row["rank"]
            handed["selected"] = row["selected"]
            provenance.setdefault("passed_to_leftbrain", []).append(handed)
            provenance["passed_to_leftbrain_trace_ids"] = list(
                dict.fromkeys(
                    [*provenance.get("passed_to_leftbrain_trace_ids", []), contract["trace_id"]]
                )
            )
    return memory_data


def _plan_from_contract(contract: dict) -> dict:
    resolved = bool(contract.get("source_selected"))
    core = contract["selected_core_jp"]
    return {
        "candidate_label": "p4_explicit_episode_recall_focus",
        "intent": "recall_context" if resolved else "memory_unknown",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "前の発言の具体的な内容を確かめている",
        "reply_goal": "本人の原話だけを返し、根拠がなければ断定しない",
        "jp_summary": "ユーザーが前に言った具体的な内容を確認している。",
        "core_message_jp": core,
        "cognitive_mode": "direct" if resolved else "reflective",
        "response_mode": "direct_answer" if resolved else "clarify_light",
        "uncertainty": 0.08 if resolved else 0.75,
        "premise_check": "accept" if resolved else "question",
        "self_check": True,
        "subjective_note_jp": "出所を追える本人の原話以外は答えにしない",
        "hidden_intent": "memory_probe",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "memory_source": contract.get("source") or "unknown",
            "trace_id": contract.get("trace_id") or "unavailable",
        },
        "payload_level": "medium",
        "memory_recall_contract": deepcopy(contract),
        "planner_path": PLANNER_PATH,
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
        "must_avoid": ["私", "わかりました", "たぶん", "きっと", "AI"],
    }


def rule_plan_with_explicit_episode_recall_focus_p4(self, user_input, current_psyche, memory_data=None):
    contract = (memory_data or {}).get(LABEL) or {}
    if contract.get("schema") == SCHEMA and contract.get("eligible") and contract.get("surface_authority"):
        predecessor = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
        if (
            str((predecessor or {}).get("intent") or "") in adaptive_person.PROTECTED_INTENTS
            or str((predecessor or {}).get("scene") or "") in adaptive_person.PROTECTED_SCENES
        ):
            return predecessor
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def _commit_visible(logic_data: dict, contract: dict, before: str, final: str, status: str) -> str:
    receipt = deepcopy(contract)
    receipt["visible_surface_status"] = status
    receipt["pre_authority_surface_sha256"] = _sha(before)
    receipt["final_visible_surface_sha256"] = _sha(final)
    receipt["final_visible_surface_matches_contract"] = final == receipt.get("selected_core_jp")
    logic_data["memory_recall_contract"] = deepcopy(receipt)
    logic_data[LABEL] = deepcopy(receipt)
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    original_reply = str(guard.get("original_reply") or before)
    guard.update(
        changed=final != original_reply,
        pre_focus_guard_repair_action=guard.get("repair_action"),
        repair_action="explicit_episode_recall_focus_" + status,
        final_rejection_reasons=[],
        final_reply=final,
        final_reply_sha256=_sha(final),
        explicit_episode_recall_focus_p4=True,
        explicit_episode_recall_focus_surface_status=status,
    )
    logic_data["visible_language_guard"] = guard
    shadow = logic_data.get("model_surface_forbidden_projection_shadow")
    if isinstance(shadow, dict):
        shadow["visible_reply_sha256"] = _sha(final)
        shadow["visible_reply_source"] = LABEL
    return final


def _fail_closed_visible(logic_data: dict, contract: dict, before: str, reason: str) -> str:
    receipt = deepcopy(contract)
    receipt.update(
        status="surface_integrity_failed_closed",
        reason=reason,
        source_selected=False,
        answer_use_authorized=False,
        selected_core_jp=_UNKNOWN_CORE,
        selected_core_sha256=_sha(_UNKNOWN_CORE),
        claim_boundary="source or plan integrity failed; no past user fact is asserted",
    )
    return _commit_visible(logic_data, receipt, before, _UNKNOWN_CORE, "failed_closed")


def visible_guard_with_explicit_episode_recall_focus_p4(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data
    )
    if not isinstance(logic_data, dict):
        return visible
    fresh = build_explicit_episode_recall_focus_contract_p4(user_input, memory_data or {})
    if not fresh.get("eligible"):
        return visible
    route = str((logic_data.get("semantic_route_m22") or {}).get("selected_type") or "")
    intent = str(logic_data.get("intent") or "")
    scene = str(logic_data.get("scene") or "")
    if (
        route == "safety_sensitive"
        or intent in adaptive_person.PROTECTED_INTENTS
        or scene in adaptive_person.PROTECTED_SCENES
    ):
        return visible
    before = str(visible or "").strip()
    if getattr(self, "_structured_surface_required", lambda: False)():
        return _fail_closed_visible(logic_data, fresh, before, "structured_surface_not_authorized")
    contract = logic_data.get("memory_recall_contract") or {}
    bound = (memory_data or {}).get(LABEL) or {}
    integrity_fields = (
        "schema", "input_sha256", "status", "focus_sha256", "source_selected",
        "memory_id", "trace_id", "source_user_sha256", "candidate_rank",
        "selected_core_sha256", "selected_core_jp",
    )
    if (
        bound.get("schema") != SCHEMA
        or contract.get("schema") != SCHEMA
        or any(contract.get(key) != fresh.get(key) or bound.get(key) != fresh.get(key) for key in integrity_fields)
        or logic_data.get("planner_path") != PLANNER_PATH
        or scene != "casual"
        or intent != ("recall_context" if fresh.get("source_selected") else "memory_unknown")
        or logic_data.get("surface_act") != "memory_presence_reply"
        or logic_data.get("core_message_jp") != fresh.get("selected_core_jp")
        or route != "factual_or_memory"
    ):
        return _fail_closed_visible(logic_data, fresh, before, "recall_plan_or_source_integrity_mismatch")
    if fresh.get("source_selected") and not any(
        isinstance(row, dict)
        and row.get("trace_id") == fresh.get("trace_id")
        and row.get("channel") == HANDOFF_CHANNEL
        and row.get("memory_id") == fresh.get("memory_id")
        for row in ((memory_data or {}).get("memory_provenance") or {}).get("passed_to_leftbrain") or []
    ):
        return _fail_closed_visible(logic_data, fresh, before, "selected_source_not_passed_to_planner")
    selected = str(fresh.get("selected_core_jp") or "")
    language_check = getattr(self, "_user_visible_language_rejection_reasons", None)
    if not callable(language_check):
        return _fail_closed_visible(logic_data, fresh, before, "language_checker_unavailable")
    try:
        rejection = language_check(
            selected, user_input=user_input, logic_data=logic_data, memory_data=memory_data
        )
    except Exception:
        rejection = ["language_checker_exception"]
    if rejection:
        return _fail_closed_visible(logic_data, fresh, before, "selected_core_language_guard_rejected")
    return _commit_visible(logic_data, fresh, before, selected, "matched")


def materialize_explicit_episode_recall_focus_p4(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.setdefault("logic", {})
    contract = logic.get("memory_recall_contract") or {}
    if contract.get("schema") != SCHEMA or not contract.get("surface_authority"):
        return result
    trace = result.get("runtime_trace")
    if not isinstance(trace, dict):
        return result
    final = str(result.get("reply") or result.get("response") or "").strip()
    contract = deepcopy(contract)
    contract["final_visible_surface_sha256"] = _sha(final)
    contract["final_visible_surface_matches_contract"] = bool(
        final and final == contract.get("selected_core_jp")
    )
    if contract.get("visible_surface_status") != "failed_closed":
        contract["visible_surface_status"] = (
            "matched" if contract["final_visible_surface_matches_contract"] else "mismatch"
        )
    logic["memory_recall_contract"] = deepcopy(contract)
    logic[LABEL] = deepcopy(contract)
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next(
        (i for i, row in enumerate(rows) if row.get("label") == "selected_plan"),
        next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
    )
    rows.insert(index, {"stage": "select", "label": LABEL, "payload": deepcopy(contract), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(contract)
    return result


def install_explicit_episode_recall_focus_p4() -> bool:
    """Install only in the new local opt-in product entry."""
    global _INSTALLED, _ORIGINAL_QUERY, _ORIGINAL_RULE_PLAN
    global _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_QUERY = MemoryManager.query_all_layers
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    MemoryManager.query_all_layers = query_all_layers_with_explicit_episode_recall_focus_p4
    LeftBrain._rule_based_plan = rule_plan_with_explicit_episode_recall_focus_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_explicit_episode_recall_focus_p4

    def finish(self, result):
        if not isinstance(result, dict):
            return result
        contract = ((result.get("logic") or {}).get("memory_recall_contract") or {})
        if contract.get("schema") != SCHEMA:
            return result
        materialize_explicit_episode_recall_focus_p4(result)
        trace = result.get("runtime_trace")
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (
                getattr(runtime, "turn_traces", None)
                and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")
            ):
                runtime.turn_traces[-1] = deepcopy(trace)
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
    "HANDOFF_CHANNEL",
    "classify_explicit_episode_recall_focus_p4",
    "build_explicit_episode_recall_focus_contract_p4",
    "query_all_layers_with_explicit_episode_recall_focus_p4",
    "rule_plan_with_explicit_episode_recall_focus_p4",
    "visible_guard_with_explicit_episode_recall_focus_p4",
    "materialize_explicit_episode_recall_focus_p4",
    "install_explicit_episode_recall_focus_p4",
]
