"""Opt-in, source-bound action for an explicitly requested quoted rewrite.

The quoted words are the *object* to rewrite, not the assistant's own reply.
This is a bounded product intervention, not a general semantic equivalence judge.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
import re
import time
import unicodedata

import uruha_compute_ledger as compute_ledger
import uruha_current_turn_source_role_p4 as source_role
from uruha_local_fact_answer_authority_p4 import _protected_or_other_route
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
import uruha_utterance_frame_shadow_extension_p4 as frame_extension


LABEL = "explicit_rewrite_action_p4"
SCHEMA = "uruha_explicit_rewrite_action_p4_v1"
FLAG = "URUHA_P4_EXPLICIT_REWRITE_ACTION"
MODEL = "qwen2.5:7b"
STAGE = "p4_explicit_rewrite_action"
_OTHER_QUOTES = re.compile(r'[「」“”"『』]')
_JAPANESE = re.compile(r'[ぁ-んァ-ン]')
_FORMAL = re.compile(r'です|ます|でした|ました|承知|かしこまり|了解しました|わかりました|分かりました')
_NEW_REASON = re.compile(r'から|ので|せいで|理由|because|because of')
_NEW_PROMISE = re.compile(r'後で|あとで|明日|今度|必ず|later|tomorrow')
_NUMBER = re.compile(r'[0-9０-９]+')
_BAD_CHAR = re.compile(r'[\x00-\x1f\x7f<>`{}\[\]]')
_INSTALLED = False
_ORIGINAL_EMIT = None
_ORIGINAL_SPEAK = None


def _sha(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def classify_explicit_rewrite_action_p4(user_input: str, *, cycle_index: int | None = None) -> dict:
    """Admit only a single observable outer rewrite act over quoted data."""
    role = source_role.classify_current_turn_source_role_p4(user_input, cycle_index=cycle_index)
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    base = {
        "schema": SCHEMA,
        "input_sha256": _sha(text),
        "eligible": False,
        "reason": role["reason"],
        "source_role": "current_user_quoted_object_only",
        "source_role_certificate": source_role.public_source_role_certificate_p4(role),
        "_source_certificate": role,
    }
    if not role["rewrite_eligible"]:
        return base
    source = role["_quote_nfkc"]
    outside = role["_outside_nfkc"]
    return {
        **base,
        "eligible": True,
        "reason": "current_turn_quoted_rewrite_requested",
        "source_sha256": _sha(source),
        "outside_sha256": _sha(outside),
        "source_length": len(source),
        # Source is returned to the action locally, never copied into its graph receipt.
        "_source": source,
        "_outside": outside,
    }


def _validate_phrase(phrase: object, source: str) -> tuple[bool, str]:
    if not isinstance(phrase, str):
        return False, "not_a_string"
    value = phrase.strip()
    if not value or len(value) > 48 or value == source:
        return False, "empty_long_or_source_copy"
    if _BAD_CHAR.search(value) or _OTHER_QUOTES.search(value) or "\n" in value:
        return False, "unsafe_phrase_shape"
    if not _JAPANESE.search(value) or re.search(r'[A-Za-z]', value):
        return False, "not_japanese_only"
    if _FORMAL.search(value):
        return False, "formal_register"
    if set(_NUMBER.findall(value)) - set(_NUMBER.findall(source)):
        return False, "new_number"
    if _NEW_REASON.search(value) and not _NEW_REASON.search(source):
        return False, "new_reason"
    if _NEW_PROMISE.search(value) and not _NEW_PROMISE.search(source):
        return False, "new_future_promise"
    return True, "bounded_shape_accepted_semantics_unverified"


def _usage(response: object) -> dict:
    raw = getattr(response, "usage", None)
    if isinstance(raw, dict):
        prompt = raw.get("prompt_tokens")
        completion = raw.get("completion_tokens")
    else:
        prompt = getattr(raw, "prompt_tokens", None)
        completion = getattr(raw, "completion_tokens", None)
    return {
        "prompt_tokens": prompt if isinstance(prompt, int) and prompt >= 0 else "unavailable",
        "completion_tokens": completion if isinstance(completion, int) and completion >= 0 else "unavailable",
    }


def _candidate_has_competing_authority(logic: dict) -> bool:
    """Do not displace an independently authoritative protected/factual reply."""
    if logic.get("memory_recall_contract") is not None or logic.get("profile_grounding_shadow") is not None:
        return True
    route = logic.get("semantic_route_m22")
    if route is not None and (
        not isinstance(route, dict)
        or route.get("schema") != "uruha_semantic_route_taxonomy_m22"
        or route.get("selected_type") in {"factual_or_memory", "safety_sensitive"}
    ):
        return True
    if logic.get(frame_extension.LABEL) is not None and not isinstance(
        logic.get(frame_extension.LABEL), dict
    ):
        return True
    schemas = {
        "semantic_commit_repair_m32": "uruha_deterministic_semantic_commit_m32",
        "semantic_authorization_m31": "uruha_semantic_authorization_m31",
        "source_anchored_semantic_commit_m33": "uruha_source_anchored_semantic_commit_m33",
        "literal_topic_projection_m29": "uruha_generalized_literal_topic_projection_m29",
        "feedback_topic_transition_m28": "uruha_feedback_topic_transition_m28",
    }
    for key, schema in schemas.items():
        contract = logic.get(key)
        if contract is not None and (
            not isinstance(contract, dict)
            or contract.get("schema") != schema
            or contract.get("surface_authority") is not False
        ):
            return True
    return False


def _transfer_surface_authority(logic: dict, user_input: str, candidate: str, receipt: dict) -> None:
    """Move only this turn's *surface* authority from the old plan to the new act."""
    old_m32 = deepcopy(logic.get("semantic_commit_repair_m32") or {})
    if not isinstance(old_m32, dict):
        raise TypeError("malformed M32 surface contract")
    if old_m32 and old_m32.get("surface_authority") is not False:
        raise ValueError("authoritative or malformed M32 cannot be shadowed without lineage")
    receipt["m32_surface_authority_shadowed"] = False
    previous_frame = logic.get(frame_extension.LABEL) or {}
    effective_frame = frame_extension.inspect_utterance_frame_coverage_extension_p4(
        user_input, candidate
    )
    logic[frame_extension.LABEL] = effective_frame
    receipt["pre_action_frame_reply_sha256"] = previous_frame.get("reply_digest", "unavailable")
    receipt["effective_frame_reply_sha256"] = effective_frame.get("reply_digest", "unavailable")
    receipt["effective_frame_violations"] = list(effective_frame.get("violations") or [])
    logic["human_speech_plan"] = {
        "dialogue_act": "direct_chat_answer",
        "content_units": [candidate],
        "speech_moves": [],
        "content_density_target": "low",
        "turn_opening_potential": False,
        "grounding_terms": [],
    }


def speak_with_explicit_rewrite_action_p4(
    self, user_input, logic_data, memory_data, current_psyche
):
    """Use the accepted, complete action candidate without a second realization pass."""
    receipt = (logic_data or {}).get(LABEL) or {}
    candidate = str((logic_data or {}).get("core_message_jp") or "").strip()
    if (
        os.environ.get(FLAG) == "1"
        and receipt.get("status") == "candidate_committed"
        and receipt.get("committed_visible_candidate_sha256") == _sha(candidate)
        and candidate
    ):
        self._remember_turn(
            str(logic_data.get("jp_summary") or ""), candidate,
            str(logic_data.get("intent") or "chat"),
        )
        receipt["speak_delivery"] = "typed_candidate_no_second_generation"
        return candidate
    if _ORIGINAL_SPEAK is None:
        raise RuntimeError("explicit rewrite speech action not installed")
    return _ORIGINAL_SPEAK(self, user_input, logic_data, memory_data, current_psyche)


def _generate(self, source: str, outside: str) -> tuple[str | None, dict]:
    receipt = {
        "stage": STAGE, "model": MODEL, "attempted_calls": 1,
        "completed_calls": 0, "temperature": 0, "max_tokens": 80,
        "timeout_seconds": 6.0, "prompt_tokens": "unavailable",
        "completion_tokens": "unavailable", "call_latency_seconds": None,
    }
    system = (
        "You edit one quoted phrase for the user's requested softer or more casual Japanese tone. "
        "Return only JSON with one key rewrite_jp. Preserve the source meaning, speaker, "
        "negation and time; do not invent a reason, place, number, or future promise. "
        "Use natural casual Japanese, no formal register or English. Do not answer the "
        "quote as if it were addressed to you."
    )
    started = time.perf_counter()
    try:
        with compute_ledger.ledger_stage(getattr(self, "compute_ledger", None), STAGE):
            response = self.client_logic.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps({"source_quote": source, "requested_style": outside}, ensure_ascii=False)},
                ],
                temperature=0,
                max_tokens=80,
                timeout=6.0,
            )
        receipt["call_latency_seconds"] = round(time.perf_counter() - started, 6)
        receipt["completed_calls"] = 1
        receipt.update(_usage(response))
        if receipt["call_latency_seconds"] > 6.25:
            return None, {**receipt, "status": "call_budget_exceeded"}
        choices = getattr(response, "choices", None) or []
        if len(choices) != 1 or getattr(choices[0], "finish_reason", "stop") != "stop":
            return None, {**receipt, "status": "incomplete_or_ambiguous_response"}
        payload = json.loads(str(getattr(getattr(choices[0], "message", None), "content", "")))
        if not isinstance(payload, dict) or set(payload) != {"rewrite_jp"}:
            return None, {**receipt, "status": "invalid_json_shape"}
        phrase = payload["rewrite_jp"]
        valid, why = _validate_phrase(phrase, source)
        if not valid:
            return None, {**receipt, "status": why}
        return phrase.strip(), {**receipt, "status": why, "model_phrase_sha256": _sha(phrase.strip())}
    except Exception as exc:
        receipt["call_latency_seconds"] = round(time.perf_counter() - started, 6)
        return None, {**receipt, "status": "model_error", "error_type": type(exc).__name__}


def _materialize(self, result: dict, receipt: dict) -> dict:
    if not isinstance(result, dict):
        return result
    final = str(result.get("reply") or "")
    logic = result.get("logic") or {}
    trace = result.get("runtime_trace") or {}
    complete = receipt.get("committed_visible_candidate_sha256")
    receipt = deepcopy(receipt)
    receipt["speak_delivery"] = (logic.get(LABEL) or {}).get("speak_delivery", "unavailable")
    speech_history = getattr(getattr(self, "right_brain", None), "history", None) or []
    last_speech = speech_history[-1] if speech_history else {}
    speak_reply = str(last_speech.get("content") or "") if last_speech.get("role") == "assistant" else ""
    receipt["speak_reply_sha256"] = _sha(speak_reply) if speak_reply else "unavailable"
    receipt["candidate_equals_speak"] = bool(complete and speak_reply and complete == _sha(speak_reply))
    receipt["final_visible_sha256"] = _sha(final)
    receipt["candidate_equals_final"] = bool(complete and complete == _sha(final))
    guard = logic.get("visible_language_guard") or {}
    guard_reply = str(guard.get("final_reply") or "")
    receipt["candidate_equals_final_guard"] = bool(complete and complete == _sha(guard_reply))
    receipt["guard_equals_final"] = guard_reply == final
    p4w = logic.get("frame_preserving_visible_repair_p4") or {}
    receipt["p4w_changed"] = p4w.get("changed", "unavailable")
    utterance = next((row for row in reversed(list(trace.get("blackboard") or [])) if row.get("label") == "utterance"), {})
    utterance_reply = str((utterance.get("payload") or {}).get("reply") or "")
    receipt["graph_utterance_sha256"] = _sha(utterance_reply) if utterance_reply else "unavailable"
    receipt["graph_utterance_equals_final"] = bool(utterance_reply and utterance_reply == final)
    if receipt.get("status") == "candidate_committed" and not (
        receipt["candidate_equals_speak"] and receipt["candidate_equals_final"]
        and receipt["candidate_equals_final_guard"] and receipt["guard_equals_final"]
        and receipt["graph_utterance_equals_final"] and receipt["p4w_changed"] is False
    ):
        receipt["status"] = "downstream_surface_mismatch"
    logic[LABEL] = deepcopy(receipt)
    if isinstance(trace, dict):
        rows = [row for row in list(trace.get("blackboard") or []) if row.get("label") != LABEL]
        original = next((row for row in rows if row.get("label") == "selected_plan"), None)
        if original and receipt.get("committed_visible_candidate_sha256"):
            payload = deepcopy(original.get("payload") or {})
            payload["typed_rewrite_original_plan_role"] = "shadowed_by_explicit_rewrite_action_p4"
            original["payload"] = payload
        old_frame = next((row for row in rows if row.get("label") == frame_extension.LABEL), None)
        if old_frame and receipt.get("committed_visible_candidate_sha256"):
            payload = deepcopy(old_frame.get("payload") or {})
            payload["typed_rewrite_frame_role"] = "pre_action_shadow"
            old_frame["payload"] = payload
        before = next((index for index, row in enumerate(rows) if row.get("label") == "utterance"), len(rows))
        rows.insert(before, {"stage": "surface", "label": LABEL, "payload": deepcopy(receipt), "salience": 1.0})
        trace["blackboard"] = rows
        trace[LABEL] = deepcopy(receipt)
        selected = trace.get("selected_plan")
        if isinstance(selected, dict) and receipt.get("committed_visible_candidate_sha256"):
            selected["typed_rewrite_override"] = {
                "schema": SCHEMA, "source": "current_turn_quote",
                "original_core_sha256": receipt.get("original_core_sha256"),
                "committed_visible_candidate_sha256": complete,
            }
        runtime = getattr(self, "runtime", None)
        if runtime is not None:
            runtime.blackboard = deepcopy(rows)
            if getattr(runtime, "turn_traces", None) and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index"):
                runtime.turn_traces[-1] = deepcopy(trace)
        sync_current_history_m41_1(result)
    return result


def _attach_source_role(self, result: dict, role: dict, *, admission: str) -> dict:
    """Expose the bounded source split in the graph without raw user words."""
    if not isinstance(result, dict):
        return result
    public = source_role.public_source_role_certificate_p4(role)
    logic = result.get("logic") or {}
    public["lineage"] = source_role.audit_current_turn_lineage_p4(role, logic)
    public["action_admission"] = admission
    if isinstance(logic, dict):
        logic[source_role.LABEL] = deepcopy(public)
    trace = result.get("runtime_trace") or {}
    if isinstance(trace, dict):
        rows = [row for row in list(trace.get("blackboard") or []) if row.get("label") != source_role.LABEL]
        insertion = next(
            (index for index, row in enumerate(rows) if row.get("label") in {LABEL, "utterance"}),
            len(rows),
        )
        rows.insert(insertion, {
            "stage": "pragmatics", "label": source_role.LABEL,
            "payload": deepcopy(public), "salience": 0.91,
        })
        trace["blackboard"] = rows
        trace[source_role.LABEL] = deepcopy(public)
        runtime = getattr(self, "runtime", None)
        if runtime is not None:
            runtime.blackboard = deepcopy(rows)
            if getattr(runtime, "turn_traces", None) and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index"):
                runtime.turn_traces[-1] = deepcopy(trace)
        sync_current_history_m41_1(result)
    return result


def emit_response_with_explicit_rewrite_action_p4(self, event: dict, tick_result: dict):
    if _ORIGINAL_EMIT is None:
        raise RuntimeError("explicit rewrite action not installed")
    raw = str((event or {}).get("user_input") or "")
    runtime = getattr(self, "runtime", None)
    scope = classify_explicit_rewrite_action_p4(raw, cycle_index=getattr(runtime, "cycle_index", None))
    if os.environ.get(FLAG) != "1" or not isinstance(tick_result, dict):
        return _ORIGINAL_EMIT(self, event, tick_result)
    role = scope.pop("_source_certificate")
    if not scope.get("eligible"):
        return _attach_source_role(
            self, _ORIGINAL_EMIT(self, event, tick_result), role,
            admission="not_a_single_rewrite_request",
        )
    logic = tick_result.get("logic") or {}
    if not isinstance(logic, dict) or _protected_or_other_route(
        logic, tick_result.get("route_info") or {}, getattr(self, "right_brain", None)
    ) or logic.get("surface_act") in {"repair_check", "memory_accounting"}:
        return _attach_source_role(
            self, _ORIGINAL_EMIT(self, event, tick_result), role,
            admission="protected_or_other_route_retained",
        )
    source = scope.pop("_source")
    outside = scope.pop("_outside")
    receipt = {key: value for key, value in scope.items() if not key.startswith("_") and key != "source_role_certificate"}
    receipt.update({
        "original_core_sha256": _sha(logic.get("core_message_jp")),
        "original_surface_act": str(logic.get("surface_act") or ""),
        "original_planner_path": str(logic.get("planner_path") or ""),
        "original_plan_role": "shadow_when_candidate_committed",
        "persistent_fact_write": False,
        "claim_boundary": "bounded explicit current-turn quote rewrite; not semantic-equivalence proof",
    })
    receipt["lineage"] = source_role.audit_current_turn_lineage_p4(role, logic)
    if _candidate_has_competing_authority(logic):
        receipt["status"] = "candidate_not_generated_competing_authority_unproven_lineage"
        receipt["model_call"] = {"attempted_calls": 0, "completed_calls": 0}
        result = _materialize(self, _ORIGINAL_EMIT(self, event, tick_result), receipt)
        return _attach_source_role(self, result, role, admission="competing_authority_retained")
    phrase, model_receipt = _generate(self, source, outside)
    receipt["model_call"] = model_receipt
    if phrase is None:
        receipt["status"] = "model_candidate_rejected_original_route_kept"
    else:
        candidate = f"「{phrase}」がいいかな。"
        receipt["model_phrase_sha256"] = _sha(phrase)
        receipt["committed_visible_candidate_sha256"] = _sha(candidate)
        receipt["status"] = "candidate_committed"
        logic["core_message_jp"] = candidate
        logic["surface_act"] = "plain_reply"
        _transfer_surface_authority(logic, raw, candidate, receipt)
        constraints = dict(logic.get("constraints") or {})
        constraints["max_chars"] = max(80, int(constraints.get("max_chars") or 0))
        logic["constraints"] = constraints
        logic[LABEL] = deepcopy(receipt)
    result = _ORIGINAL_EMIT(self, event, tick_result)
    result = _materialize(self, result, receipt)
    verified_status = ((result or {}).get("logic") or {}).get(LABEL, {}).get("status")
    return _attach_source_role(
        self, result, role,
        admission=verified_status if isinstance(verified_status, str) else "candidate_status_unavailable",
    )


def install_explicit_rewrite_action_p4(brain_class=None) -> bool:
    """Install once after prior P4 wrappers; flag-off preserves their behavior."""
    global _INSTALLED, _ORIGINAL_EMIT, _ORIGINAL_SPEAK
    if _INSTALLED:
        return False
    if brain_class is None:
        from uruha_brain_mac import UruhaBrainV4_Mac
        brain_class = UruhaBrainV4_Mac
    from uruha_brain_mac import RightBrain
    _ORIGINAL_EMIT = brain_class.emit_response_if_ready
    _ORIGINAL_SPEAK = RightBrain.speak
    brain_class.emit_response_if_ready = emit_response_with_explicit_rewrite_action_p4
    RightBrain.speak = speak_with_explicit_rewrite_action_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "FLAG", "classify_explicit_rewrite_action_p4",
    "emit_response_with_explicit_rewrite_action_p4", "speak_with_explicit_rewrite_action_p4",
    "install_explicit_rewrite_action_p4",
]
