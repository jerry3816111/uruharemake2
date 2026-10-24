"""Opt-in realization of an already-authorized, bounded reported-check act.

This changes neither source classification nor M31 admission.  A same-turn
ordinary A decision may be expressed without the generic direct-chat suffix;
all later guards still run, and the actual final utterance is audited.  The
reply is scoped to the current reported utterance: passive retrieved context
does not authorize either a memory answer or a global "unknown" claim.  The
receipt contains digests/status only, not a new factual or memory claim.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import re

import uruha_reported_ack_m31_priority_p4 as priority
import uruha_reported_ack_route_admission_p4 as admission
import uruha_temporal_actor_scope_p4 as actor_scope


SCHEMA = "uruha_reported_ack_selected_visible_p4_v2"
LABEL = "reported_ack_selected_visible_p4"
_BOUNDED_QUOTE = re.compile(r"(?:先に|まず)(?:確認|チェック)(?:して|しといて|してね)\Z")
_ALLOWED_PREFIXES = ("", "ん、", "まあ、", "いや、", "てか、", "一回、", "先に、", "普通に、", "はいはい、")
_INSTALLED = False
_ORIGINAL_EMIT = None
_ORIGINAL_RUN = None
_ORIGINAL_VARIANTS = None


def _receipt(user_input, status="not_applied", reason="not_eligible"):
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "input_digest": priority._digest(str(user_input or "")),
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "profile_write_count": 0,
        "raw_source_or_quote_in_receipt": False,
        "private_state_truth_claimed": False,
        "claim_boundary": "bounded selected-to-visible reported act, not report truth or general pragmatics",
    }


def _candidate_from_match(match):
    speaker, quote = match.group("speaker"), match.group("quote")
    return f"{speaker}が「{quote}」って言ってたんだね。"


def _passive_memory_context(anchor, logic):
    """Retrieved episode/short-term context is never a memory-answer warrant."""

    if not isinstance(anchor, dict) or not anchor:
        return False
    memory_id = anchor.get("memory_id")
    trace_id = anchor.get("trace_id")
    source = anchor.get("source")
    speakability = logic.get("memory_speakability")
    reason = logic.get("memory_speakability_reason")
    return bool(
        anchor.get("kind") == "context"
        and anchor.get("expected") is False
        and anchor.get("provenance_channel") == "selected_working_memory"
        and (
            (source == "episode" and isinstance(memory_id, str) and bool(memory_id)
             and trace_id == f"stored:episode:{memory_id}")
            or (source == "short_term" and memory_id in (None, "")
                and isinstance(trace_id, str)
                and re.fullmatch(r"derived:short_term:[0-9a-f]{20}", trace_id) is not None)
        )
        and (
            (speakability == "background_only" and reason == "relevant_but_not_requested")
            or (speakability == "latent_ok" and reason == "weak_contextual_memory")
        )
    )


def prepare_reported_ack_selected_visible_p4(user_input, logic, route_info, selected_plan):
    """Mutate only a proved A-selected plan, before RightBrain speaks."""

    receipt = _receipt(user_input)
    if not isinstance(logic, dict) or not isinstance(route_info, dict) or not isinstance(selected_plan, dict):
        receipt["reason"] = "selected_or_route_context_missing"
        return receipt
    match = priority._SINGLE_JA_REPORT.fullmatch(str(user_input or ""))
    if match is None or _BOUNDED_QUOTE.fullmatch(match.group("quote")) is None:
        receipt["reason"] = "bounded_single_report_absent"
        return receipt
    digest = receipt["input_digest"]
    auth = logic.get("semantic_authorization_m31") or {}
    certificate = auth.get(priority.LABEL) or {}
    route_admission = auth.get(admission.LABEL) or {}
    scope = logic.get(actor_scope.LABEL) or {}
    m22 = logic.get("semantic_route_m22") or {}
    if not (
        auth.get("status") == "deferred_to_reported_ack_p4"
        and auth.get("input_digest") == digest
        and certificate.get("schema") == priority.SCHEMA
        and certificate.get("status") == "source_qualified_reported_ack_precedes_m31"
        and certificate.get("input_digest") == digest
        and certificate.get("speaker_digest") == priority._digest(match.group("speaker"))
        and certificate.get("quote_digest") == priority._digest(match.group("quote"))
        and certificate.get("m31_model_call_skipped") is True
        and route_admission.get("schema") == admission.SCHEMA
        and route_admission.get("status") == "admitted"
        and route_admission.get("input_digest") == digest
        and route_admission.get("source_certificate_present") is True
        and route_admission.get("m31_model_call_skipped") is True
        and scope.get("schema") == actor_scope.SCHEMA
        and scope.get("input_digest") == digest
        and scope.get("source_kind") == "third_party_report"
        and scope.get("actor") == "third_party"
        and scope.get("action") == "reported_check_instruction"
        and scope.get("selected_action") == "ack_reported_check_instruction_p4"
        and scope.get("assistant_request_authorized") is False
        and scope.get("additional_clause_observed") is False
    ):
        receipt["reason"] = "same_turn_source_or_admission_not_proved"
        return receipt
    if not (
        logic.get("intent") == "chat"
        and logic.get("scene") == "casual"
        and logic.get("surface_act") == "ack_reported_check_instruction_p4"
        and logic.get("core_message_jp") == actor_scope._REPORTED_CHECK_REPLY_JP
        and selected_plan.get("surface_act") == logic.get("surface_act")
        and selected_plan.get("core_message_jp") == logic.get("core_message_jp")
        and route_info.get("route") == "high_road"
        and route_info.get("reason") == "deliberative"
        and not route_info.get("intent")
        and route_info.get("cognitive_hijack") in (None, False)
        and m22.get("schema") == "uruha_semantic_route_taxonomy_m22"
        and m22.get("selected_type") == "general_conversation"
        and m22.get("recommended_route") == "existing_guarded_router"
        and m22.get("decisive_evidence") == ["no_decisive_specialized_cue"]
        and m22.get("overlap_types") == []
        and isinstance(m22.get("candidates"), list)
        and len(m22["candidates"]) == 1
        and isinstance(m22["candidates"][0], dict)
        and m22["candidates"][0].get("task_type") == "general_conversation"
        and isinstance(m22.get("evidence"), list)
        and len(m22["evidence"]) == 1
        and isinstance(m22["evidence"][0], dict)
        and m22["evidence"][0].get("task_type") == "general_conversation"
        and m22["evidence"][0].get("cue_id") == "no_decisive_specialized_cue"
        and route_admission.get("signal_route") == "high_road"
        and route_admission.get("m22_task_shape") == "general_conversation"
        and route_admission.get("m22_recommended_route") == "existing_guarded_router"
    ):
        receipt["reason"] = "actual_selected_or_general_route_disagrees"
        return receipt
    anchor = logic.get("memory_anchor")
    if (
        logic.get("memory_use_expected") is not False
        or logic.get("memory_recall_contract")
        or logic.get("profile_grounding_shadow")
        or logic.get("grounded_profile_logic")
        or (anchor and not _passive_memory_context(anchor, logic))
    ):
        receipt["reason"] = "memory_or_profile_authority_present"
        return receipt

    speaker, quote = match.group("speaker"), match.group("quote")
    core = _candidate_from_match(match)
    if len(core) > 80:
        receipt["reason"] = "candidate_exceeds_bounded_length"
        return receipt
    old_core = str(logic["core_message_jp"])
    logic["core_message_jp"] = core
    logic["jp_summary"] = core
    context = logic.get("personhood_action_context_v2_13")
    if isinstance(context, dict) and context.get("core_message_jp") == old_core:
        context["core_message_jp"] = core
    speech = logic.get("human_speech_plan")
    if isinstance(speech, dict):
        speech["content_units"] = [core if unit == old_core else unit for unit in speech.get("content_units") or []]
    constraints = dict(logic.get("constraints") or {})
    constraints["max_chars"] = max(80, int(constraints.get("max_chars") or 0))
    logic["constraints"] = constraints
    receipt.update({
        "status": "selected",
        "reason": "same_turn_A_decision_realized_before_speech",
        "speaker_digest": priority._digest(speaker),
        "quote_digest": priority._digest(quote),
        "prior_core_digest": priority._digest(old_core),
        "selected_core_digest": priority._digest(core),
        "selected_core_length": len(core),
        "max_chars": constraints["max_chars"],
        "source_qualified": True,
        "claim_source_scope": "current_user_report_only",
        "memory_authority": "retrieved_background_not_answer" if anchor else "no_retrieved_anchor",
        "background_trace_digest": priority._digest(anchor["trace_id"]) if anchor else None,
        "global_unknown_claimed": False,
    })
    logic[LABEL] = receipt
    return receipt


def speech_plan_variants_with_reported_ack_p4(self, reply, logic_data, user_input, memory_data=None):
    receipt = (logic_data or {}).get(LABEL) or {}
    core = str((logic_data or {}).get("core_message_jp") or "")
    if (
        receipt.get("schema") == SCHEMA
        and receipt.get("status") == "selected"
        and receipt.get("input_digest") == priority._digest(str(user_input or ""))
        and receipt.get("selected_core_digest") == priority._digest(core)
        and (logic_data or {}).get("surface_act") == "ack_reported_check_instruction_p4"
    ):
        return [core]
    return _ORIGINAL_VARIANTS(self, reply, logic_data, user_input, memory_data=memory_data)


def materialize_reported_ack_selected_visible_p4(result, user_input=None, receipt=None):
    """Read the actual final utterance; never repair or replace it here."""

    if not isinstance(result, dict):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    receipt = deepcopy(receipt or logic.get(LABEL) or _receipt(result.get("user_input")))
    reply = str(result.get("reply") or "")
    selected = trace.get("selected_plan") or {}
    if receipt.get("status") in {"selected", "final_visible", "selected_not_visible"}:
        core = str(selected.get("core_message_jp") or "")
        source = str(user_input or "")
        match = priority._SINGLE_JA_REPORT.fullmatch(source)
        expected = _candidate_from_match(match) if match and _BOUNDED_QUOTE.fullmatch(match.group("quote")) else ""
        selected_rows = [row for row in trace.get("blackboard") or [] if isinstance(row, dict) and row.get("label") == "selected_plan"]
        utterance_rows = [row for row in trace.get("blackboard") or [] if isinstance(row, dict) and row.get("label") == "utterance"]
        p4t = logic.get("utterance_frame_shadow_p4") or {}
        p4v = logic.get("utterance_frame_coverage_extension_p4") or {}
        p4w = logic.get("frame_preserving_visible_repair_p4") or {}
        m39 = logic.get("semantic_persona_surface_verifier_m39") or {}
        language = logic.get("visible_language_guard") or {}
        full_reply_digest = hashlib.sha256(reply.encode("utf-8")).hexdigest()
        checks = {
            "same_turn_source": bool(
                match and expected
                and receipt.get("input_digest") == priority._digest(source)
                and receipt.get("speaker_digest") == priority._digest(match.group("speaker"))
                and receipt.get("quote_digest") == priority._digest(match.group("quote"))
            ),
            "selected_core": bool(
                expected and core == expected
                and logic.get("core_message_jp") == expected
                and receipt.get("selected_core_digest") == priority._digest(expected)
                and selected.get("surface_act") == "ack_reported_check_instruction_p4"
                and len(selected_rows) == 1
                and (selected_rows[0].get("payload") or {}).get("core_message_jp") == expected
            ),
            "final_shape": bool(expected and reply in {prefix + expected for prefix in _ALLOWED_PREFIXES}),
            "graph_utterance": bool(
                len(utterance_rows) == 1
                and (utterance_rows[0].get("payload") or {}).get("reply") == reply
            ),
            "language_guard": bool(
                language.get("final_rejection_reasons") == []
            ),
            "p4_t_frame": bool(
                p4t.get("violations") == []
                and p4t.get("reply_digest") == full_reply_digest
            ),
            "p4_v_frame": bool(
                p4v.get("violations") == []
                and p4v.get("reply_digest") == full_reply_digest
            ),
            "p4_w_repair": bool(
                p4w.get("changed") is False
                and p4w.get("after_violations") == []
                and p4w.get("after_digest") == full_reply_digest
            ),
            "m39_final": bool(
                m39.get("action") == "accept"
                and m39.get("changed") is False
                and m39.get("unresolved_violations") == []
                and m39.get("final_reply_digest") == priority._digest(reply)
            ),
        }
        receipt["final_verification"] = checks
        visible = all(checks.values())
        receipt["status"] = "final_visible" if visible else "selected_not_visible"
        receipt["reason"] = "source_bound_final_verified" if visible else "final_verification_failed"
    receipt["final_utterance_digest"] = priority._digest(reply)
    receipt["legacy_actor_surface_status"] = (logic.get(actor_scope.LABEL) or {}).get("surface_status")
    receipt["language_guard_changed"] = (logic.get("visible_language_guard") or {}).get("changed")
    logic[LABEL] = deepcopy(receipt)
    trace[LABEL] = deepcopy(receipt)
    rows = trace.get("blackboard")
    if isinstance(rows, list):
        rows[:] = [row for row in rows if not (isinstance(row, dict) and row.get("label") == LABEL)]
        insert_at = next((i for i, row in enumerate(rows) if isinstance(row, dict) and row.get("label") == "utterance"), len(rows))
        rows.insert(insert_at, {
            "stage": "verify", "label": LABEL, "payload": deepcopy(receipt),
            "salience": 1.0 if receipt.get("status") == "final_visible" else 0.95,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
    return result


def _sync_current_history(self, result):
    if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
        return
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    self.runtime.blackboard = deepcopy(result["runtime_trace"].get("blackboard") or [])
    sync_current_history_m41_1(result)
    current = result["runtime_trace"]
    if (
        getattr(self.runtime, "turn_traces", None)
        and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index")
    ):
        self.runtime.turn_traces[-1] = deepcopy(current)


def install_reported_ack_selected_visible_p4():
    """Install after A, only in the new local opt-in entrypoint."""

    global _INSTALLED, _ORIGINAL_EMIT, _ORIGINAL_RUN, _ORIGINAL_VARIANTS
    if _INSTALLED:
        return False
    if not admission._INSTALLED or not actor_scope._INSTALLED:
        raise RuntimeError("reported_ack_route_admission_must_be_installed_first")
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_VARIANTS = RightBrain._speech_plan_variants

    def emit_with_reported_ack(self, event, tick_result):
        user_input = str((event or {}).get("user_input") or "")
        logic = (tick_result or {}).get("logic")
        route_info = (tick_result or {}).get("route_info")
        selected_plan = getattr(self.runtime, "last_selected_plan", None)
        receipt = _receipt(user_input)
        if self.right_brain._structured_surface_required():
            receipt["reason"] = "structured_surface_required_not_overridden"
        else:
            receipt = prepare_reported_ack_selected_visible_p4(
                user_input, logic, route_info, selected_plan
            )
        if receipt["status"] == "selected":
            self.runtime.last_selected_plan = self._plan_trace_summary(logic)
            loop = getattr(self.runtime, "last_personhood_loop", None)
            if isinstance(loop, dict) and isinstance(loop.get("action_choice"), dict):
                if loop["action_choice"].get("core_message_jp") == actor_scope._REPORTED_CHECK_REPLY_JP:
                    loop["action_choice"]["core_message_jp"] = logic["core_message_jp"]
            for row in getattr(self.runtime, "blackboard", []) or []:
                if not isinstance(row, dict) or not isinstance(row.get("payload"), dict):
                    continue
                payload = row["payload"]
                if row.get("label") in {"selected_plan", "personhood_action_choice_v2_13"}:
                    payload["core_message_jp"] = logic["core_message_jp"]
                if row.get("label") == "selected_plan" and isinstance(payload.get("human_speech_plan"), dict):
                    payload["human_speech_plan"] = deepcopy(logic.get("human_speech_plan") or {})
        if isinstance(logic, dict):
            logic[LABEL] = deepcopy(receipt)
        result = _ORIGINAL_EMIT(self, event, tick_result)
        result = materialize_reported_ack_selected_visible_p4(result, user_input)
        _sync_current_history(self, result)
        return result

    def run_with_reported_ack(self, user_input, input_context=None):
        result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
        result = materialize_reported_ack_selected_visible_p4(result, user_input)
        _sync_current_history(self, result)
        return result

    RightBrain._speech_plan_variants = speech_plan_variants_with_reported_ack_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_reported_ack
    UruhaBrainV4_Mac.run_turn_debug = run_with_reported_ack
    _INSTALLED = True
    return True


__all__ = [
    "SCHEMA", "LABEL", "prepare_reported_ack_selected_visible_p4",
    "speech_plan_variants_with_reported_ack_p4",
    "materialize_reported_ack_selected_visible_p4",
    "install_reported_ack_selected_visible_p4",
]
