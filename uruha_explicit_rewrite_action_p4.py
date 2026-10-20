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
from uruha_local_fact_answer_authority_p4 import _protected_or_other_route
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1


LABEL = "explicit_rewrite_action_p4"
SCHEMA = "uruha_explicit_rewrite_action_p4_v1"
FLAG = "URUHA_P4_EXPLICIT_REWRITE_ACTION"
MODEL = "qwen2.5:7b"
STAGE = "p4_explicit_rewrite_action"
_QUOTE = re.compile(r'「(?P<corner>[^「」\n]{2,40})」|“(?P<curly>[^“”\n]{2,40})”|"(?P<ascii>[^"\n]{2,40})"')
_OTHER_QUOTES = re.compile(r'[「」“”"『』]')
_REQUEST = re.compile(r'言い換え|書き換え|改成|改寫|改写|\b(?:rewrite|rephrase|paraphrase)\b', re.I)
_STYLE = re.compile(r'柔らか|やわらか|友達|親し|くだけ|カジュアル|委婉|柔和|口語|比较|比較|\b(?:warmer|casual|softer|gentler)\b', re.I)
_NOT_REWRITE = re.compile(r'意味|定義|とは|翻訳|英訳|和訳|translate|meaning|define|definition|翻譯|翻译|意思|第三者|友達が|友人が|朋友說|朋友说|my friend said', re.I)
_SENSITIVE = re.compile(r'パスワード|暗証番号|認証コード|ログイン|住所|電話番号|個人情報|自傷|自殺|死にたい|殺す|殺して|password|passcode|secret|suicide|self.harm|kill|密碼|密码|驗證碼|验证码|住址|電話|殺人|杀人', re.I)
_JAPANESE = re.compile(r'[ぁ-んァ-ン]')
_FORMAL = re.compile(r'です|ます|でした|ました|承知|かしこまり|了解しました|わかりました|分かりました')
_NEW_REASON = re.compile(r'から|ので|せいで|理由|because|because of')
_NEW_PROMISE = re.compile(r'後で|あとで|明日|今度|必ず|later|tomorrow')
_NUMBER = re.compile(r'[0-9０-９]+')
_BAD_CHAR = re.compile(r'[\x00-\x1f\x7f<>`{}\[\]]')
_INSTALLED = False
_ORIGINAL_EMIT = None


def _sha(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def classify_explicit_rewrite_action_p4(user_input: str) -> dict:
    """Require one current-turn quote, an overt rewrite act, and a style goal."""
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    base = {
        "schema": SCHEMA,
        "input_sha256": _sha(text),
        "eligible": False,
        "reason": "not_applicable",
        "source_role": "current_user_quoted_object_only",
    }
    if not text or len(text) > 240 or _SENSITIVE.search(text):
        return {**base, "reason": "empty_long_or_sensitive"}
    matches = list(_QUOTE.finditer(text))
    if len(matches) != 1:
        return {**base, "reason": "not_one_short_balanced_quote"}
    match = matches[0]
    outside = text[:match.start()] + " " + text[match.end():]
    if _OTHER_QUOTES.search(outside):
        return {**base, "reason": "unmatched_or_additional_quote"}
    source = next((part for part in match.groupdict().values() if part is not None), "").strip()
    if not source or _OTHER_QUOTES.search(source):
        return {**base, "reason": "nested_or_empty_quote"}
    if _NOT_REWRITE.search(outside):
        return {**base, "reason": "definition_translation_or_reported_speech"}
    if not _REQUEST.search(outside) or not _STYLE.search(outside):
        return {**base, "reason": "no_explicit_rewrite_and_style_request"}
    return {
        **base,
        "eligible": True,
        "reason": "current_turn_quoted_rewrite_requested",
        "source_sha256": _sha(source),
        "outside_sha256": _sha(outside),
        "source_length": len(source),
        # Source is returned to the action locally, never copied into its graph receipt.
        "_source": source,
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


def emit_response_with_explicit_rewrite_action_p4(self, event: dict, tick_result: dict):
    if _ORIGINAL_EMIT is None:
        raise RuntimeError("explicit rewrite action not installed")
    raw = str((event or {}).get("user_input") or "")
    scope = classify_explicit_rewrite_action_p4(raw)
    if os.environ.get(FLAG) != "1" or not scope.get("eligible") or not isinstance(tick_result, dict):
        return _ORIGINAL_EMIT(self, event, tick_result)
    logic = tick_result.get("logic") or {}
    if not isinstance(logic, dict) or _protected_or_other_route(
        logic, tick_result.get("route_info") or {}, getattr(self, "right_brain", None)
    ) or logic.get("surface_act") in {"repair_check", "memory_accounting"}:
        return _ORIGINAL_EMIT(self, event, tick_result)
    source = scope.pop("_source")
    normalized = unicodedata.normalize("NFKC", raw).strip()
    outside_match = _QUOTE.search(normalized)
    outside = normalized[:outside_match.start()] + " " + normalized[outside_match.end():] if outside_match else ""
    receipt = {key: value for key, value in scope.items() if not key.startswith("_")}
    receipt.update({
        "original_core_sha256": _sha(logic.get("core_message_jp")),
        "original_surface_act": str(logic.get("surface_act") or ""),
        "original_planner_path": str(logic.get("planner_path") or ""),
        "original_plan_role": "shadow_when_candidate_committed",
        "persistent_fact_write": False,
        "claim_boundary": "bounded explicit current-turn quote rewrite; not semantic-equivalence proof",
    })
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
        logic.pop("human_speech_plan", None)
        constraints = dict(logic.get("constraints") or {})
        constraints["max_chars"] = max(80, int(constraints.get("max_chars") or 0))
        logic["constraints"] = constraints
        logic[LABEL] = deepcopy(receipt)
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _materialize(self, result, receipt)


def install_explicit_rewrite_action_p4(brain_class=None) -> bool:
    """Install once after prior P4 wrappers; flag-off preserves their behavior."""
    global _INSTALLED, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    if brain_class is None:
        from uruha_brain_mac import UruhaBrainV4_Mac
        brain_class = UruhaBrainV4_Mac
    _ORIGINAL_EMIT = brain_class.emit_response_if_ready
    brain_class.emit_response_if_ready = emit_response_with_explicit_rewrite_action_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "FLAG", "classify_explicit_rewrite_action_p4",
    "emit_response_with_explicit_rewrite_action_p4", "install_explicit_rewrite_action_p4",
]
