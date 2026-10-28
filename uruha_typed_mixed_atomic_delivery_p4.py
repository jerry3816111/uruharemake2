"""Opt-in terminal transaction for two bounded, source-distinct dialogue acts.

The old M31/M32 producer authority remains immutable evidence. This module
prepares one quoted rewrite plus one source-bound past-place answer, then makes
an explicit *terminal* surface choice before episode persistence. A generated
rewrite remains semantically unverified; product quality needs external review.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import os
import re
import unicodedata

import uruha_adaptive_person_model as adaptive
import uruha_current_turn_source_role_p4 as source_role
import uruha_explicit_rewrite_action_p4 as rewrite
import uruha_mixed_act_lineage_p4 as lineage
import uruha_mixed_past_place_source_authority_p4 as past_place
import uruha_typed_act_semantic_ledger_p4 as semantic_ledger
from uruha_local_fact_answer_authority_p4 import _protected_or_other_route
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1


LABEL = "typed_mixed_atomic_delivery_p4"
SCHEMA = "uruha_typed_mixed_atomic_delivery_p4_v1"
FLAG = "URUHA_P4_TYPED_MIXED_ATOMIC_DELIVERY"
_ACTIVE = ContextVar("uruha_typed_mixed_atomic_delivery_active", default=None)
_INSTALLED = False
_ORIGINAL_EMIT = None
_ORIGINAL_SPEAK = None
_ORIGINAL_GUARD = None
_ORIGINAL_SAVE_EPISODE = None
_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_PAST = re.compile(r"昨日|一昨日|今日|明日|先週|来週")
_DONE = re.compile(r"(?:もう|すでに|既に)?(?:決まった|決めた|確定した|確認できた|終わった)")
_NOT_DECIDED = re.compile(r"決まっていません|決まってない|決めていません|決めてない|未確定|未定")
_UNSETTLED = re.compile(r"まだ|未|仮|保留|確認中|確認待ち|待ち|検討中|見直し中|再検討中|調整中")
_MIXED_STYLE_COMMAND = re.compile(
    r"を友達(?:向けに|に(?:送る|話す|返す)感じで)"
    r"(?:もう少し|少し|もっと)?(?P<tone>柔らかく|やわらかく|カジュアルに|親しみやすく)"
    r"(?:言い換えて|書き換えて)[、,](?P<recall>.+)"
)
_BOUNDED_RECALL_SUFFIX = re.compile(
    rf"(?:{past_place._DATE}|一昨日|昨日)に(?:私|僕|俺|うち)が"
    r"(?:選んだ|決めた)(?:集合)?場所も?(?:教えて|思い出して|覚えて)[。.!！]?"
)
_CONTRADICTORY_STYLE = re.compile(
    r"堅い|硬い|固い|かたい|敬語|丁寧語|フォーマル|ビジネス|公式|"
    r"くだけない|砕けない|柔らかく(?:しない|ない)|やわらかく(?:しない|ない)|"
    r"カジュアル(?:にしない|じゃない)"
)
_CANONICAL_STYLE = {
    "柔らかく": "友達向けの柔らかい日本語",
    "やわらかく": "友達向けの柔らかい日本語",
    "カジュアルに": "友達向けのカジュアルな日本語",
    "親しみやすく": "友達向けの親しみやすい日本語",
}


def _sha(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _uuid(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _bounded_requested_style(role: dict) -> str | None:
    """Use only the certified outer rewrite cue, never its separate recall act.

    This is a deliberately narrow style boundary, not an intent inference.
    Unrecognized or conflicting wording retains the original route without an
    added rewrite call. The quoted source (including any inner date) is not
    shortened or altered here.
    """
    if not isinstance(role, dict) or (
        role.get("act") != "mixed_request"
        or role.get("quote_role") != "rewrite_object"
        or role.get("outer_role") != "current_user_context_or_instruction"
    ):
        return None
    cues = role.get("evidence_ids")
    outside = role.get("_outside_nfkc")
    quote = role.get("_quote_nfkc")
    if (
        not isinstance(cues, list)
        or not {"rewrite_request", "style_goal", "other_action"}.issubset(cues)
        or not isinstance(outside, str)
        or not isinstance(quote, str)
        or not outside or not quote or "\n" in outside
        or _sha(outside) != role.get("outside_classifier_normalized_sha256")
        or _sha(quote) != role.get("quote_normalized_sha256")
        or _CONTRADICTORY_STYLE.search(outside)
    ):
        return None
    match = _MIXED_STYLE_COMMAND.fullmatch(outside)
    if not match or not _BOUNDED_RECALL_SUFFIX.fullmatch(match.group("recall")):
        return None
    return _CANONICAL_STYLE[match.group("tone")]


def verify_typed_mixed_atomic_admission_p4(event: dict, tick_result: dict) -> dict:
    """Reverify observable current-turn lineage; never decide by answer text."""
    failed = lambda reason: {"schema": SCHEMA, "eligible": False, "reason": reason, "actions": []}
    if not isinstance(event, dict) or not isinstance(tick_result, dict):
        return failed("missing_event_or_tick")
    raw = event.get("user_input")
    logic = tick_result.get("logic")
    if not isinstance(raw, str) or not raw or not isinstance(logic, dict):
        return failed("missing_raw_or_logic")
    certificate = event.get(lineage.EVENT_KEY)
    receipt = logic.get(lineage.LABEL)
    m31 = logic.get("semantic_authorization_m31")
    m32 = logic.get("semantic_commit_repair_m32")
    if not all(isinstance(value, dict) for value in (certificate, receipt, m31, m32)):
        return failed("missing_lineage_or_producer")
    if not all(key not in logic or isinstance(logic[key], dict) for key in (
        "source_anchored_semantic_commit_m33", "semantic_route_m22",
        "memory_recall_contract", "profile_grounding_shadow",
    )) or not isinstance(tick_result.get("route_info"), dict) or not all(
        isinstance(receipt.get(key), dict) for key in ("m31", "m32")
    ):
        return failed("malformed_competing_contract_or_receipt")
    digest = _sha(raw)
    event_id = certificate.get("event_id")
    cycle = certificate.get("cycle_index")
    role = source_role.classify_current_turn_source_role_p4(raw, cycle_index=cycle)
    query = past_place.classify_mixed_past_place_query_p4(raw)
    if role.get("act") != "mixed_request" or role.get("quote_role") != "rewrite_object" or not query.get("eligible"):
        return failed("not_bounded_mixed_request")
    actions = lineage._actions(raw, role, event_id) if _uuid(event_id) else []
    if (
        certificate.get("schema") != lineage.SCHEMA
        or not _uuid(event_id) or type(cycle) is not int or cycle < 0
        or certificate.get("raw_input_sha256") != digest
        or certificate.get("source_role_act") != "mixed_request"
        or certificate.get("source_role_quote_sha256") != role.get("quote_raw_sha256")
        or certificate.get("actions") != actions or len(actions) != 2
        or [a.get("type") for a in actions] != ["quoted_rewrite", "past_user_place_recall"]
        or certificate.get("raw_dialogue_persisted") is not False
        or certificate.get("authority_transfer_permitted") is not False
        or certificate.get("model_calls_added") != 0
    ):
        return failed("event_action_span_or_digest_mismatch")
    m31_stamp = m31.get(lineage.PRODUCER_KEY)
    m32_stamp = m32.get(lineage.PRODUCER_KEY)
    if not isinstance(m31_stamp, dict) or not isinstance(m32_stamp, dict):
        return failed("missing_direct_producer_stamps")
    m31_id = m31_stamp.get("proposal_id")
    m32_id = m32_stamp.get("proposal_id")
    if not (
        isinstance(m31_id, str) and m31_id.startswith(f"{event_id}:m31:")
        and _uuid(m31_id[len(f"{event_id}:m31:"):])
        and isinstance(m32_id, str) and m32_id.startswith(f"{event_id}:m32:")
        and _uuid(m32_id[len(f"{event_id}:m32:"):])
        and len({event_id, m31_id, m32_id, *(a["action_id"] for a in actions)}) == 5
    ):
        return failed("missing_or_duplicate_producer_id")
    common = {
        "schema": lineage.SCHEMA, "parent_event_id": event_id,
        "raw_input_sha256": digest, "cycle_index": cycle,
        "action_coverage_status": "unverified", "authority_transfer_permitted": False,
        "raw_dialogue_persisted": False,
    }
    if any(stamp.get(key) != value for stamp in (m31_stamp, m32_stamp) for key, value in common.items()):
        return failed("producer_event_digest_or_cycle_mismatch")
    if (
        m31.get("schema") != adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31
        or m32.get("schema") != adaptive.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32
        or m31_stamp.get("schema") != lineage.SCHEMA
        or m32_stamp.get("schema") != lineage.SCHEMA
        or m31_stamp.get("producer") != "m31" or m32_stamp.get("producer") != "m32"
        or m32_stamp.get("parent_m31_id") != m31_id
        or m32_stamp.get("parent_m31_direct_argument") is not True
        or m32_stamp.get("parent_m31_status_at_build") != m31_stamp.get("status_at_return")
        or m31_stamp.get("status_at_return") != m31.get("status")
        or m32_stamp.get("status_at_return") != m32.get("status")
        or m32.get("source_m31_status") != m31.get("status")
        or m31.get("input_digest") != digest[:16]
    ):
        return failed("producer_direct_parent_or_status_mismatch")
    expected_edges = [
        {"from_id": event_id, "to_id": m31_id, "type": "event_to_m31"},
        {"from_id": m31_id, "to_id": m32_id, "type": "m31_to_m32"},
    ]
    if (
        receipt.get("schema") != lineage.SCHEMA
        or receipt.get("status") != "linked"
        or receipt.get("reason") != "producer_parent_chain_verified"
        or receipt.get("event_id") != event_id
        or receipt.get("raw_input_sha256") != digest
        or receipt.get("cycle_index") != cycle
        or receipt.get("source_role_act") != "mixed_request"
        or receipt.get("actions") != actions
        or receipt.get("producer_edges") != expected_edges
        or receipt.get("action_coverage_status") != "unverified"
        or receipt.get("authority_transfer_permitted") is not False
        or receipt.get("reply_changed_by_lineage") is not False
        or receipt.get("raw_dialogue_persisted") is not False
        or receipt.get("model_calls_added") != 0
        or receipt.get("authority_blockers") != []
        or receipt["m31"].get("status") != "produced"
        or receipt["m32"].get("status") != "produced"
        or (receipt.get("m31") or {}).get("proposal_id") != m31_id
        or (receipt.get("m32") or {}).get("proposal_id") != m32_id
        or type(m31.get("surface_authority")) is not bool
        or (receipt.get("m31") or {}).get("surface_authority_retained") is not m31.get("surface_authority")
        or (receipt.get("m32") or {}).get("surface_authority_retained") is not True
        or m32.get("surface_authority") is not True
    ):
        return failed("lineage_receipt_or_authority_mismatch")
    if (
        (logic.get("source_anchored_semantic_commit_m33") or {}).get("surface_authority") is True
        or receipt.get("m33_authoritative") is not False
        or "memory_recall_contract" in logic or "profile_grounding_shadow" in logic
        or _protected_or_other_route(logic, tick_result.get("route_info") or {})
    ):
        return failed("protected_or_competing_authority")
    return {
        "schema": SCHEMA, "eligible": True, "reason": "current_two_action_direct_parent_verified",
        "event_id": event_id, "raw_input_sha256": digest, "cycle_index": cycle,
        "m31_proposal_id": m31_id, "m32_proposal_id": m32_id,
        "prior_m31_surface_authority": m31["surface_authority"],
        "prior_m32_surface_authority": True,
        "actions": deepcopy(actions), "source_role": role,
        "query": query,
    }


def validate_typed_mixed_rewrite_phrase_p4(phrase: object, source: str) -> tuple[bool, str]:
    """Conservative contrast checks, explicitly not semantic equivalence."""
    valid, reason = rewrite._validate_phrase(phrase, source)
    if not valid:
        return False, reason
    source = unicodedata.normalize("NFKC", str(source or ""))
    candidate = unicodedata.normalize("NFKC", str(phrase).strip())
    if set(_PAST.findall(source)) != set(_PAST.findall(candidate)):
        return False, "time_anchor_changed_or_dropped"
    if _UNSETTLED.search(source) and _DONE.search(candidate):
        return False, "unsettled_to_decided_contradiction"
    if "まだ" in source and not _UNSETTLED.search(candidate):
        return False, "unsettled_status_dropped"
    if _NOT_DECIDED.search(source) and not (
        _NOT_DECIDED.search(candidate)
        or ("まだ" in candidate and re.search(r"決ま|決め", candidate))
    ):
        return False, "not_decided_polarity_dropped"
    if "仮" in source and not re.search(r"仮|暫定|まだ.{0,9}(?:確定|決ま|決め)", candidate):
        return False, "provisional_status_dropped"
    if re.search(r"確認中|確認待ち", source) and not re.search(r"確認|確かめ|待ち|チェック", candidate):
        return False, "verification_status_dropped"
    if "再検討中" in source and not re.search(r"検討|見直|考え直", candidate):
        return False, "reconsideration_status_dropped"
    return True, "bounded_contrast_accepted_semantics_unverified"


def _valid_rewrite_call(phrase: object, call: object) -> bool:
    """Do not grant terminal priority on an unverified or over-budget call."""
    if not isinstance(phrase, str) or not isinstance(call, dict):
        return False
    latency = call.get("call_latency_seconds")
    completion = call.get("completion_tokens")
    return bool(
        call.get("stage") == rewrite.STAGE
        and call.get("model") == rewrite.MODEL
        and call.get("attempted_calls") == 1
        and call.get("completed_calls") == 1
        and call.get("temperature") == 0
        and call.get("max_tokens") == 80
        and call.get("timeout_seconds") == 6.0
        and isinstance(latency, (int, float)) and not isinstance(latency, bool)
        and 0 <= latency <= 6.25
        and (completion == "unavailable" or (
            isinstance(completion, int) and not isinstance(completion, bool) and 0 <= completion <= 80
        ))
        and call.get("status") == "bounded_shape_accepted_semantics_unverified"
        and call.get("model_phrase_sha256") == _sha(phrase.strip())
    )


def _history_snapshot(right_brain, logic: dict) -> dict | None:
    if right_brain is None:
        return None
    names = ("reply_variant_counts", "intent_variant_counts", "normalized_reply_counts", "intent_normalized_counts")
    history = getattr(right_brain, "history", None)
    counts = {name: getattr(right_brain, name, None) for name in names}
    if not isinstance(history, list) or any(not isinstance(v, dict) for v in counts.values()) or not callable(getattr(right_brain, "_remember_turn", None)):
        return None
    return {"owner": right_brain, "logic_id": id(logic), "history": deepcopy(history),
            "counts": {name: deepcopy(value) for name, value in counts.items()}}


def _commit_history(tx: dict, reply: str, logic: dict) -> str:
    snapshot = tx.get("history_snapshot")
    brain = tx.get("right_brain")
    if not isinstance(snapshot, dict) or snapshot.get("owner") is not brain or snapshot.get("logic_id") != id(logic):
        return "history_transaction_unavailable"
    history = getattr(brain, "history", None)
    counts = {name: getattr(brain, name, None) for name in snapshot["counts"]}
    if not isinstance(history, list) or any(not isinstance(value, dict) for value in counts.values()):
        return "history_counter_unavailable"
    history[:] = deepcopy(snapshot["history"])
    for name, counter in counts.items():
        counter.clear()
        counter.update(deepcopy(snapshot["counts"][name]))
    brain._remember_turn(str(logic.get("jp_summary") or ""), reply, str(logic.get("intent") or "chat"))
    tx["history_committed"] = True
    return "pre_guard_draft_rolled_back_final_visible_committed"


def speak_with_typed_mixed_atomic_delivery_p4(self, user_input, logic_data, memory_data, current_psyche):
    tx = _ACTIVE.get()
    if isinstance(tx, dict) and tx.get("right_brain") is self and tx.get("logic_id") == id(logic_data):
        candidate = tx.get("candidate")
        if isinstance(candidate, str) and _sha(candidate) == tx.get("candidate_sha256"):
            self._remember_turn(str(logic_data.get("jp_summary") or ""), candidate, str(logic_data.get("intent") or "chat"))
            tx["speak_candidate_sha256"] = _sha(candidate)
            return candidate
    return _ORIGINAL_SPEAK(self, user_input, logic_data, memory_data, current_psyche)


def visible_guard_with_typed_mixed_atomic_delivery_p4(self, reply, logic_data, user_input="", memory_data=None):
    tx = _ACTIVE.get()
    if not (isinstance(tx, dict) and tx.get("right_brain") is self and tx.get("logic_id") == id(logic_data)):
        return _ORIGINAL_GUARD(self, reply, logic_data, user_input=user_input, memory_data=memory_data)
    receipt = logic_data.get(LABEL) or {}
    fresh_admission = verify_typed_mixed_atomic_admission_p4(tx["event"], tx["tick"])
    fresh_source = past_place.build_mixed_past_place_certificate_p4(user_input, memory_data)
    fresh_ledger = (
        semantic_ledger.build_typed_act_semantic_ledger_p4(
            tx["event"], fresh_admission, fresh_source, tx["requested_style"],
        ) if tx.get("semantic_ledger_mode") else None
    )
    valid = (
        fresh_admission.get("eligible") is True
        and fresh_admission.get("event_id") == receipt.get("event_id")
        and fresh_admission.get("prior_m31_surface_authority") is receipt.get("prior_m31_surface_authority")
        and fresh_admission.get("prior_m32_surface_authority") is receipt.get("prior_m32_surface_authority")
        and fresh_source.get("binding_sha256") == receipt.get("source_binding_sha256")
        and fresh_source.get("authorized_reply_sha256") == receipt.get("source_reply_sha256")
        and _sha(tx.get("candidate")) == receipt.get("committed_visible_candidate_sha256")
        and tx.get("speak_candidate_sha256") == receipt.get("committed_visible_candidate_sha256")
        and user_input == tx["event"].get("user_input")
        and getattr(tx.get("owner_runtime"), "cycle_index", None) == receipt.get("cycle_index")
        and (not tx.get("semantic_ledger_mode") or (
            isinstance(fresh_ledger, dict)
            and fresh_ledger.get("eligible") is True
            and fresh_ledger.get("candidate") == tx.get("candidate")
            and fresh_ledger.get("receipt") == receipt.get("semantic_ledger")
        ))
    )
    if valid:
        selected = _ORIGINAL_GUARD(self, tx["candidate"], logic_data, user_input=user_input, memory_data=memory_data)
        guard = logic_data.get("visible_language_guard") or {}
        valid = (
            selected == tx["candidate"]
            and guard.get("final_reply") == selected
            and not guard.get("final_rejection_reasons")
        )
    if not valid:
        # `reply` may itself be the fast-path speech candidate. Reusing it after
        # a lost/retracted source would publish a stale fact despite rejecting
        # the transaction. Fail closed on a neutral, source-free utterance.
        selected = _ORIGINAL_GUARD(
            self, "ん、今は正確に確かめられないな。", logic_data,
            user_input=user_input, memory_data=memory_data,
        )
    receipt = deepcopy(receipt)
    receipt["terminal_priority_status"] = "applied_after_legacy_m32" if valid else "rejected_at_final_guard"
    receipt["terminal_priority_reason"] = (
        "two_current_actions_direct_parent_and_source_rechecked"
        if valid else "lineage_source_candidate_or_guard_mismatch"
    )
    receipt["pre_transaction_surface_sha256"] = _sha(reply)
    receipt["final_guard_reply_sha256"] = _sha(selected)
    receipt["history_commit_status"] = _commit_history(tx, selected, logic_data)
    receipt["rewrite_action_surface_status"] = (
        ("bounded_slot_visible_semantics_unverified" if tx.get("semantic_ledger_mode")
         else "shape_visible_semantics_unverified") if valid else "not_delivered"
    )
    receipt["recall_action_surface_status"] = (
        ("source_backed_visible" if receipt.get("source_status") == "source_backed" else "honest_unknown_visible")
        if valid else "not_delivered"
    )
    logic_data[LABEL] = receipt
    if valid and isinstance(logic_data.get("semantic_commit_repair_m32"), dict):
        logic_data["semantic_commit_repair_m32"]["terminal_transaction_shadowed_surface_p4"] = LABEL
    return selected


def save_episode_with_typed_mixed_atomic_delivery_p4(self, user_input, ai_response, mood_state, logic_data=None):
    doc = _ORIGINAL_SAVE_EPISODE(self, user_input, ai_response, mood_state, logic_data)
    tx = _ACTIVE.get()
    if isinstance(tx, dict) and tx.get("memory_object") is self and user_input == tx.get("event", {}).get("user_input"):
        tx["episode_call_reply_sha256"] = _sha(ai_response)
    return doc


def audit_typed_mixed_atomic_delivery_p4(result: dict, receipt: dict, *, right_brain=None) -> dict:
    """Audit delivered structure, not rewrite semantics or DB durability."""
    final = str((result or {}).get("reply") or "")
    logic = (result or {}).get("logic") or {}
    trace = (result or {}).get("runtime_trace") or {}
    guard = logic.get("visible_language_guard") or {}
    utterances = [row for row in trace.get("blackboard") or [] if isinstance(row, dict) and row.get("label") == "utterance"]
    graph_reply = str(((utterances[-1].get("payload") or {}).get("reply") or "")) if utterances else ""
    episode_doc = str((result or {}).get("episode_doc") or "")
    history = getattr(right_brain, "history", None)
    history_reply = str(history[-1].get("content") or "") if isinstance(history, list) and history and isinstance(history[-1], dict) and history[-1].get("role") == "assistant" else ""
    target = receipt.get("committed_visible_candidate_sha256")
    checks = {
        "candidate_equals_final": bool(target and target == _sha(final)),
        "guard_equals_final": bool(final and guard.get("final_reply") == final and guard.get("final_reply_sha256") == _sha(final)),
        "graph_utterance_equals_final": bool(final and graph_reply == final),
        "episode_argument_equals_final": bool(final and receipt.get("episode_call_reply_sha256") == _sha(final)),
        "episode_doc_equals_final": bool(final and f" | Uruha: {final} | Mood: " in episode_doc),
        "right_brain_history_equals_final": bool(final and history_reply == final),
        "terminal_priority_applied": receipt.get("terminal_priority_status") == "applied_after_legacy_m32",
        "history_committed": receipt.get("history_commit_status") == "pre_guard_draft_rolled_back_final_visible_committed",
    }
    consistent = all(checks.values())
    return {**checks, "final_consistent": consistent,
            "status": "delivered_structure_semantics_unverified" if consistent else "downstream_surface_or_episode_mismatch",
            "final_visible_sha256": _sha(final),
            "semantic_equivalence_certified": False,
            "db_readback_verified": False}


def _materialize(self, result: dict, tx: dict) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    receipt = deepcopy(logic.get(LABEL) or tx.get("receipt") or {})
    if receipt.get("schema") != SCHEMA:
        return result
    receipt["episode_call_reply_sha256"] = tx.get("episode_call_reply_sha256", "unavailable")
    if receipt.get("status") == "candidate_prepared":
        receipt.update(audit_typed_mixed_atomic_delivery_p4(result, receipt, right_brain=getattr(self, "right_brain", None)))
        receipt["action_coverage_status"] = (
            "visible_structure_delivered_semantics_unverified"
            if receipt["final_consistent"] else "not_verified"
        )
    else:
        receipt["final_consistent"] = False
        receipt["final_visible_sha256"] = _sha(result.get("reply"))
        receipt["action_coverage_status"] = "not_verified"
    logic[LABEL] = deepcopy(receipt)
    rows = [row for row in trace.get("blackboard") or [] if not (isinstance(row, dict) and row.get("label") == LABEL)]
    index = next((i for i, row in enumerate(rows) if isinstance(row, dict) and row.get("label") == "utterance"), len(rows))
    rows.insert(index, {"stage": "surface", "label": LABEL, "payload": deepcopy(receipt), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(receipt)
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        runtime.blackboard = deepcopy(rows)
    sync_current_history_m41_1(result)
    if runtime is not None:
        if getattr(runtime, "turn_traces", None) and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index"):
            runtime.turn_traces[-1] = deepcopy(trace)
    return result


def emit_response_with_typed_mixed_atomic_delivery_p4(self, event, tick_result):
    if os.environ.get(FLAG) != "1":
        return _ORIGINAL_EMIT(self, event, tick_result)
    admission = verify_typed_mixed_atomic_admission_p4(event, tick_result)
    if not admission.get("eligible"):
        return _ORIGINAL_EMIT(self, event, tick_result)
    logic = tick_result["logic"]
    if (
        getattr(getattr(self, "runtime", None), "cycle_index", None) != admission["cycle_index"]
        or _protected_or_other_route(logic, tick_result.get("route_info") or {}, getattr(self, "right_brain", None))
    ):
        return _ORIGINAL_EMIT(self, event, tick_result)
    raw = event["user_input"]
    source_cert = past_place.build_mixed_past_place_certificate_p4(raw, event.get("memory_data"))
    if not source_cert.get("eligible") or not isinstance(source_cert.get("binding_sha256"), str):
        return _ORIGINAL_EMIT(self, event, tick_result)
    role = admission["source_role"]
    quote = role["_quote_nfkc"]
    requested_style = _bounded_requested_style(role)
    if requested_style is None:
        return _ORIGINAL_EMIT(self, event, tick_result)
    semantic_ledger_mode = os.environ.get(semantic_ledger.FLAG) == "1"
    receipt = {
        "schema": SCHEMA, "status": "candidate_rejected_original_route_kept",
        "event_id": admission["event_id"], "raw_input_sha256": admission["raw_input_sha256"],
        "cycle_index": admission["cycle_index"], "m31_proposal_id": admission["m31_proposal_id"],
        "m32_proposal_id": admission["m32_proposal_id"],
        "action_ids": [action["action_id"] for action in admission["actions"]],
        "prior_m31_surface_authority": admission["prior_m31_surface_authority"],
        "prior_m32_surface_authority": admission["prior_m32_surface_authority"],
        "lineage_authority_transfer_permitted": False,
        "terminal_priority_status": "not_requested",
        "source_status": source_cert.get("status"),
        "source_binding_sha256": source_cert["binding_sha256"],
        "source_reply_sha256": source_cert["authorized_reply_sha256"],
        "source_trace_id": source_cert.get("source_trace_id"),
        "source_channel": source_cert.get("source_channel"),
        "quote_sha256": _sha(quote),
        "raw_dialogue_persisted_in_receipt": False,
        "persistent_fact_write": False,
        "semantic_equivalence_certified": False,
        "claim_boundary": "bounded two-action terminal delivery; rewrite semantics unverified; DB durability and quality require external validation",
    }
    if semantic_ledger_mode:
        ledger_result = semantic_ledger.build_typed_act_semantic_ledger_p4(
            event, admission, source_cert, requested_style,
        )
        if not ledger_result.get("eligible"):
            receipt["semantic_ledger_status"] = ledger_result.get("reason", "not_eligible")
            logic[LABEL] = deepcopy(receipt)
            return _materialize(self, _ORIGINAL_EMIT(self, event, tick_result), {"receipt": receipt})
        phrase = ledger_result["rewrite_phrase"]
        candidate = ledger_result["candidate"]
        receipt["semantic_ledger"] = deepcopy(ledger_result["receipt"])
        receipt["model_call"] = deepcopy(ledger_result["receipt"]["model_call"])
        receipt["rewrite_contrast_status"] = "bounded_slot_fidelity_verified"
    else:
        phrase, call = rewrite._generate(self, quote, requested_style)
        receipt["model_call"] = call
        if not _valid_rewrite_call(phrase, call):
            valid, reason = False, "rewrite_call_receipt_missing_invalid_or_over_budget"
        else:
            valid, reason = validate_typed_mixed_rewrite_phrase_p4(phrase, quote)
        receipt["rewrite_contrast_status"] = reason
        if not valid:
            logic[LABEL] = deepcopy(receipt)
            return _materialize(self, _ORIGINAL_EMIT(self, event, tick_result), {"receipt": receipt})
        candidate = f"「{phrase}」って感じかな。{source_cert['authorized_reply']}"
    receipt["status"] = "candidate_prepared"
    receipt["rewrite_phrase_sha256"] = _sha(phrase)
    receipt["committed_visible_candidate_sha256"] = _sha(candidate)
    receipt["terminal_priority_status"] = "requested_pending_final_guard"
    logic[LABEL] = deepcopy(receipt)
    tx = {
        "event": event, "tick": tick_result, "receipt": receipt, "candidate": candidate,
        "candidate_sha256": _sha(candidate), "right_brain": getattr(self, "right_brain", None),
        "logic_id": id(logic), "owner_runtime": getattr(self, "runtime", None),
        "memory_object": getattr(self, "memory", None),
        "history_snapshot": _history_snapshot(getattr(self, "right_brain", None), logic),
        "semantic_ledger_mode": semantic_ledger_mode,
        "requested_style": requested_style,
    }
    if tx["history_snapshot"] is None:
        receipt["status"] = "history_transaction_unavailable_original_route_kept"
        logic[LABEL] = deepcopy(receipt)
        return _materialize(self, _ORIGINAL_EMIT(self, event, tick_result), {"receipt": receipt})
    token = _ACTIVE.set(tx)
    try:
        result = _ORIGINAL_EMIT(self, event, tick_result)
    finally:
        _ACTIVE.reset(token)
        if not tx.get("history_committed") and tx.get("history_snapshot"):
            snapshot = tx["history_snapshot"]
            brain = tx["right_brain"]
            if isinstance(getattr(brain, "history", None), list):
                brain.history[:] = deepcopy(snapshot["history"])
            for name, value in snapshot["counts"].items():
                counter = getattr(brain, name, None)
                if isinstance(counter, dict):
                    counter.clear()
                    counter.update(deepcopy(value))
    return _materialize(self, result, tx)


def install_typed_mixed_atomic_delivery_p4() -> bool:
    """Install only after the existing lineage wrapper in a dedicated entry."""
    global _INSTALLED, _ORIGINAL_EMIT, _ORIGINAL_SPEAK, _ORIGINAL_GUARD, _ORIGINAL_SAVE_EPISODE
    from uruha_brain_mac import MemoryManager, RightBrain, UruhaBrainV4_Mac
    if _INSTALLED:
        return False
    if not lineage._INSTALLED or UruhaBrainV4_Mac.emit_response_if_ready is not lineage.emit_response_with_mixed_act_lineage_p4:
        raise RuntimeError("typed_mixed_atomic_requires_installed_lineage_last")
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_SPEAK = RightBrain.speak
    _ORIGINAL_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_SAVE_EPISODE = MemoryManager.save_episode
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_with_typed_mixed_atomic_delivery_p4
    RightBrain.speak = speak_with_typed_mixed_atomic_delivery_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_typed_mixed_atomic_delivery_p4
    MemoryManager.save_episode = save_episode_with_typed_mixed_atomic_delivery_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "FLAG", "verify_typed_mixed_atomic_admission_p4",
    "validate_typed_mixed_rewrite_phrase_p4", "audit_typed_mixed_atomic_delivery_p4",
    "emit_response_with_typed_mixed_atomic_delivery_p4", "install_typed_mixed_atomic_delivery_p4",
]
