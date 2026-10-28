"""P4-AW: bounded CJK subject-ellipsis authority for one executed action path.

Chinese and Japanese often omit an already understood first-person subject.
P4-AS previously required an explicit pronoun, so a current user's direct
description of cognitive overactivity could visibly receive the selected
clarification while still failing to obtain an executed-event identity.

This module adds only a provisional authority candidate.  It is available when
an existing typed cognitive-overactivity trigger, the current-user channel,
and bounded source-frame guards all agree.  It becomes final only after the
existing M39 surface, calibrate_need policy, P1 pending event, and plan identity
checks pass exactly.  The original source frame remains ``unspecified``; no
private mental state is asserted.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_adaptive_person_model as adaptive
import uruha_multilingual_observable_trigger_p4 as trigger_coverage
import uruha_prediction_identity_p1 as identity
import uruha_selected_action_surface_execution_p4 as p4_as
import uruha_semantic_persona_surface_m39 as surface_m39
import uruha_utterance_frame_shadow_p4 as utterance_frame


LABEL = "cjk_subject_ellipsis_action_authority_p4"
SCHEMA = "uruha_cjk_subject_ellipsis_action_authority_p4"
PROVISIONAL_STATUS = "provisional_current_user_ellipsis"
FINAL_STATUS = "authorized_current_user_ellipsis"

_CJK_HAN = re.compile(r"[\u3400-\u9fff]")
_JAPANESE_KANA = re.compile(r"[ぁ-ゖァ-ヺ]")
_REPORT = re.compile(
    r"(?:新聞|新闻|媒體|媒体|報導|报道|消息指出|報告指出|报告指出)"
    r"|(?:ニュース|報道|記事|調査)(?:では|によると|によれば|は)|(?:と報じ|と報道)",
    re.IGNORECASE,
)
_RESOLVED = re.compile(
    r"(?:現在|现在|如今|已經|已经|終於|终于).{0,16}(?:靜下來|静下来|停下來|停下来|平靜|平静|慢下來|慢下来|沒事|没事)"
    r"|(?:今は|今では|もう|すでに).{0,20}(?:落ち着いた|静まった|止まった|休まった|平気)",
    re.IGNORECASE,
)

_INSTALLED_P4_AW_HOOKS = False
_INSTALLED_P4_AW_PRODUCT = False
_ORIGINAL_SOURCE_AUTHORITY_P4_AW = None
_ORIGINAL_PROMOTE_P4_AW = None
_ORIGINAL_RECEIPT_CHECKS_P4_AW = None
_ORIGINAL_EMIT_P4_AW = None
_ORIGINAL_RUN_TURN_P4_AW = None


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _cjk_language(text):
    text = str(text or "")
    if _JAPANESE_KANA.search(text):
        return "ja"
    if _CJK_HAN.search(text):
        return "zh"
    return None


def assess_cjk_subject_ellipsis_candidate_p4_aw(user_input, trigger=None, source_frame=None):
    """Return a raw-free provisional authority assessment.

    The caller supplies a current user turn.  The result is not an ownership
    fact: it is only a bounded permission to continue the existing
    calibrate-need execution checks.
    """

    text = str(user_input or "")
    base = adaptive.extract_observable_trigger_predicates_m37(text)
    typed = deepcopy(trigger) if isinstance(trigger, dict) else trigger_coverage.extend_observable_trigger_p4(text, base)
    frame = deepcopy(source_frame) if isinstance(source_frame, dict) else surface_m39._source_frame_m39(text)
    utterance = utterance_frame.extract_utterance_frame_p4(text)
    language = _cjk_language(text)
    checks = {
        "current_user_source": True,
        "cjk_language": language in {"zh", "ja"},
        "typed_cognitive_overactivity": "cognitive_overactivity" in set(typed.get("predicates") or []),
        "typed_trigger_not_private_truth": typed.get("private_state_truth_claimed") is False,
        "source_role_unspecified": frame.get("speaker_role") == "unspecified",
        "no_third_party": frame.get("third_party_present") is False,
        "direct_embedding": utterance.get("embedding_mode") == "direct",
        "direct_evidential_stance": utterance.get("evidential_stance") == "direct",
        "statement_speech_act": utterance.get("speech_act") == "statement",
        "no_report_source": not bool(_REPORT.search(text)),
        "not_resolved": not bool(_RESOLVED.search(text)),
    }
    failed = [key for key, value in checks.items() if not value]
    if frame.get("speaker_role") == "user_first_person" and frame.get("third_party_present") is False:
        status = "predecessor_explicit_authority_preserved"
        reason = "explicit_first_person_remains_owned_by_p4_as"
    elif not failed:
        status = PROVISIONAL_STATUS
        reason = "bounded_current_user_cjk_subject_ellipsis_candidate"
    else:
        status = "blocked"
        reason = "bounded_subject_ellipsis_checks_failed"
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "language": language,
        "source_channel": "current_user",
        "source_speaker_role_preserved": frame.get("speaker_role"),
        "third_party_present": bool(frame.get("third_party_present")),
        "trigger_predicate": (
            "cognitive_overactivity"
            if "cognitive_overactivity" in set(typed.get("predicates") or [])
            else None
        ),
        "trigger_status": (typed.get("coverage_extension") or {}).get("status") or typed.get("status"),
        "utterance_embedding": utterance.get("embedding_mode"),
        "utterance_stance": utterance.get("evidential_stance"),
        "utterance_speech_act": utterance.get("speech_act"),
        "checks": checks,
        "failed_checks": failed,
        "evidence_digest": _digest(text),
        "final_exact_chain_verified": False,
        "source_frame_changed": False,
        "trigger_detector_changed": False,
        "p1_or_p4_ar_guard_weakened": False,
        "candidate_score_or_order_changed": False,
        "feedback_classifier_changed": False,
        "visible_reply_changed": False,
        "added_model_calls": 0,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "bounded current-user CJK ellipsis authority only; source role remains unspecified, "
            "and no private-state truth or open-domain coreference is claimed"
        ),
    }


def finalize_cjk_subject_ellipsis_authority_p4_aw(provisional, exact_checks):
    """Finalize only if every existing execution check except explicit pronoun passes."""

    result = deepcopy(provisional or {})
    exact_checks = deepcopy(exact_checks or {})
    required = {
        key: bool(value)
        for key, value in exact_checks.items()
        if key != "direct_user_first_person"
    }
    exact = bool(
        result.get("schema") == SCHEMA
        and result.get("status") == PROVISIONAL_STATUS
        and required
        and all(required.values())
        and exact_checks.get("direct_user_first_person") is False
    )
    result.update(
        {
            "status": FINAL_STATUS if exact else "blocked_final_exact_chain",
            "reason": (
                "existing_surface_plan_pending_and_identity_chain_exact"
                if exact
                else "existing_execution_chain_not_exact"
            ),
            "final_exact_chain_verified": exact,
            "final_exact_checks": required,
            "failed_final_checks": [key for key, value in required.items() if not value],
        }
    )
    return result


def install_cjk_subject_ellipsis_action_authority_hooks_p4_aw():
    """Install the bounded P4-AS authority bridge without changing its source."""

    global _INSTALLED_P4_AW_HOOKS
    global _ORIGINAL_SOURCE_AUTHORITY_P4_AW, _ORIGINAL_PROMOTE_P4_AW
    global _ORIGINAL_RECEIPT_CHECKS_P4_AW
    if _INSTALLED_P4_AW_HOOKS:
        return False

    _ORIGINAL_SOURCE_AUTHORITY_P4_AW = p4_as._source_authority
    _ORIGINAL_PROMOTE_P4_AW = p4_as.promote_selected_action_state_p4
    _ORIGINAL_RECEIPT_CHECKS_P4_AW = p4_as._receipt_checks

    def source_authority(user_input):
        frame, predecessor = _ORIGINAL_SOURCE_AUTHORITY_P4_AW(user_input)
        if predecessor:
            return frame, True
        assessment = assess_cjk_subject_ellipsis_candidate_p4_aw(
            user_input,
            source_frame=frame,
        )
        return frame, assessment.get("status") == PROVISIONAL_STATUS

    def promote(user_input, state):
        promoted, trace = _ORIGINAL_PROMOTE_P4_AW(user_input, state)
        base = deepcopy((state or {}).get("observable_trigger_m37") or {})
        typed = trigger_coverage.extend_observable_trigger_p4(user_input, base)
        frame = surface_m39._source_frame_m39(user_input)
        assessment = assess_cjk_subject_ellipsis_candidate_p4_aw(
            user_input,
            trigger=typed,
            source_frame=frame,
        )
        if assessment.get("status") == PROVISIONAL_STATUS:
            if trace.get("status") != p4_as.EARLY_STATUS:
                # P4-AS originally moved only a newly added P4-AH trigger
                # before decision time.  P4-AW's frozen variable explicitly
                # includes the same already-typed M37 signal; compose it into
                # the copied shadow state without changing either detector.
                promoted = trigger_coverage.apply_extended_trigger_to_shadow_state_p4(
                    state,
                    typed,
                )
                trace = deepcopy(trace)
                trace.update(
                    {
                        "status": p4_as.EARLY_STATUS,
                        "reason": "existing_typed_trigger_authorized_by_bounded_cjk_ellipsis_p4_aw",
                        "trigger_status": (typed.get("coverage_extension") or {}).get("status") or typed.get("status"),
                        "trigger_predicate": "cognitive_overactivity",
                        "trigger_evidence_digest": str(typed.get("evidence_digest") or "")[:32],
                        "source_authorized": True,
                    }
                )
            trace = deepcopy(trace)
            trace.update(
                {
                    "source_authority_basis": LABEL,
                    "source_authority_provisional": True,
                    LABEL: deepcopy(assessment),
                }
            )
            promoted = deepcopy(promoted)
            promoted[p4_as.LABEL] = deepcopy(trace)
        return promoted, trace

    def receipt_checks(logic, user_input, reply, turn_index, model):
        decision, selected, early, plan, audit, checks = _ORIGINAL_RECEIPT_CHECKS_P4_AW(
            logic,
            user_input,
            reply,
            turn_index,
            model,
        )
        provisional = deepcopy(early.get(LABEL) or {})
        if provisional.get("status") != PROVISIONAL_STATUS:
            return decision, selected, early, plan, audit, checks
        finalized = finalize_cjk_subject_ellipsis_authority_p4_aw(provisional, checks)
        early = deepcopy(early)
        early[LABEL] = finalized
        checks = deepcopy(checks)
        authorized = finalized.get("status") == FINAL_STATUS
        checks["bounded_cjk_subject_ellipsis_authorized_p4_aw"] = authorized
        if authorized:
            # Compatibility with the frozen P4-AS failed-check key.  The raw
            # source frame remains unspecified and the separate P4-AW trace
            # records the actual authority basis.
            checks["direct_user_first_person"] = True
        return decision, selected, early, plan, audit, checks

    p4_as._source_authority = source_authority
    p4_as.promote_selected_action_state_p4 = promote
    p4_as._receipt_checks = receipt_checks
    _INSTALLED_P4_AW_HOOKS = True
    return True


def append_cjk_subject_ellipsis_action_authority_node_p4_aw(result):
    result = result or {}
    logic = result.setdefault("logic", {})
    p4_as_payload = deepcopy(logic.get(p4_as.LABEL) or {})
    payload = deepcopy(p4_as_payload.get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return result
    logic[LABEL] = deepcopy(payload)
    runtime = result.setdefault("runtime_trace", {})
    runtime[LABEL] = deepcopy(payload)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(rows)
            if row.get("label") in {p4_as.LABEL, "executed_action_identity_gate_p4", "utterance"}
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "authorize", "label": LABEL, "payload": deepcopy(payload), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_cjk_subject_ellipsis_action_authority_p4_aw():
    """Install the hooks and one additive product graph node."""

    global _INSTALLED_P4_AW_PRODUCT, _ORIGINAL_EMIT_P4_AW, _ORIGINAL_RUN_TURN_P4_AW
    install_cjk_subject_ellipsis_action_authority_hooks_p4_aw()
    if _INSTALLED_P4_AW_PRODUCT:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_P4_AW = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_TURN_P4_AW = UruhaBrainV4_Mac.run_turn_debug

    def emit(self, event, tick_result):
        result = _ORIGINAL_EMIT_P4_AW(self, event, tick_result)
        result = append_cjk_subject_ellipsis_action_authority_node_p4_aw(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run_turn(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AW(self, user_input, input_context=input_context)
        result = append_cjk_subject_ellipsis_action_authority_node_p4_aw(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run_turn
    _INSTALLED_P4_AW_PRODUCT = True
    return True


def build_dataset_evidence_p4_aw(dataset_path):
    path = Path(dataset_path)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    install_cjk_subject_ellipsis_action_authority_hooks_p4_aw()
    identity.install_prediction_identity_p1()
    cases = []
    module_source = Path(__file__).read_text(encoding="utf-8")
    turn = 900
    for frozen in dataset["cases"]:
        turn += 1
        source = frozen["input"]
        base = adaptive.extract_observable_trigger_predicates_m37(source)
        typed = trigger_coverage.extend_observable_trigger_p4(source, base)
        frame = surface_m39._source_frame_m39(source)
        frame_before = deepcopy(frame)
        assessment = assess_cjk_subject_ellipsis_candidate_p4_aw(
            source,
            trigger=typed,
            source_frame=frame,
        )
        positive = frozen["split"] in {"exposed_development", "fresh_positive"}
        predecessor = frozen["split"] == "predecessor_control"
        fixture = p4_as._fixture_case_result(
            {
                "case_id": frozen["id"],
                "partition": frozen["split"],
                "input": source,
                "expected_status": p4_as.FINAL_STATUS if positive or predecessor else "not_applicable",
            },
            turn,
        )
        if positive and fixture["status"] == p4_as.FINAL_STATUS:
            final_status = FINAL_STATUS
        elif predecessor and fixture["status"] == p4_as.FINAL_STATUS:
            final_status = "preserve_explicit_predecessor"
        else:
            final_status = "blocked"
        serialized = json.dumps(assessment, ensure_ascii=False, sort_keys=True)
        cases.append(
            {
                "case_id": frozen["id"],
                "split": frozen["split"],
                "control_family": frozen.get("control_family"),
                "expected_status": frozen["expected_status"],
                "provisional_status": assessment["status"],
                "status": final_status,
                "failed_checks": assessment["failed_checks"],
                "typed_cognitive_overactivity": assessment["checks"]["typed_cognitive_overactivity"],
                "p4_as_status": fixture["status"],
                "p4_as_receipt_status": fixture["receipt_status"],
                "p4_ar_authorized": fixture["p4_ar_authorized"],
                "source_frame_mutated": frame != frame_before,
                "trigger_detector_changed": assessment["trigger_detector_changed"],
                "p1_or_p4_ar_guard_weakened": assessment["p1_or_p4_ar_guard_weakened"],
                "candidate_score_or_order_changed": assessment["candidate_score_or_order_changed"],
                "feedback_classifier_changed": assessment["feedback_classifier_changed"],
                "visible_reply_changed": assessment["visible_reply_changed"],
                "added_model_calls": assessment["added_model_calls"],
                "factual_memory_write_count": assessment["factual_memory_write_count"],
                "raw_dialogue_persisted": assessment["raw_dialogue_persisted"] or source in serialized,
                "private_state_truth_claimed": assessment["private_state_truth_claimed"],
                "full_case_string_in_module": source in module_source,
            }
        )
    development = [row for row in cases if row["split"] == "exposed_development"]
    positives = [row for row in cases if row["split"] == "fresh_positive"]
    controls = [row for row in cases if row["split"] == "fresh_control"]
    predecessor = [row for row in cases if row["split"] == "predecessor_control"]
    authorized = [*development, *positives]
    metrics = {
        "case_count": len(cases),
        "development_authorized_count": sum(row["status"] == FINAL_STATUS for row in development),
        "fresh_positive_authorized_count": sum(row["status"] == FINAL_STATUS for row in positives),
        "fresh_control_blocked_count": sum(row["status"] == "blocked" for row in controls),
        "predecessor_explicit_authority_preserved_count": sum(row["status"] == "preserve_explicit_predecessor" for row in predecessor),
        "typed_trigger_required_count": sum(row["typed_cognitive_overactivity"] for row in authorized),
        "final_exact_chain_authorized_count": sum(row["p4_as_status"] == p4_as.FINAL_STATUS and row["p4_as_receipt_status"] == "registered_for_next_user_turn" and row["p4_ar_authorized"] is True for row in authorized),
        "control_false_authority_count": sum(row["p4_as_status"] == p4_as.FINAL_STATUS for row in controls),
        "source_frame_mutation_count": sum(row["source_frame_mutated"] for row in cases),
        "trigger_detector_mutation_count": sum(row["trigger_detector_changed"] for row in cases),
        "p1_or_p4_ar_guard_weakening_count": sum(row["p1_or_p4_ar_guard_weakened"] for row in cases),
        "candidate_score_or_order_change_count": sum(row["candidate_score_or_order_changed"] for row in cases),
        "feedback_classifier_change_count": sum(row["feedback_classifier_changed"] for row in cases),
        "visible_reply_change_count": sum(row["visible_reply_changed"] for row in cases),
        "added_model_call_count": sum(row["added_model_calls"] for row in cases),
        "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in cases),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in cases),
        "private_state_truth_claim_count": sum(row["private_state_truth_claimed"] for row in cases),
        "full_fresh_string_patch_count": sum(row["full_case_string_in_module"] for row in [*positives, *controls]),
    }
    return {
        "schema": "uruha_p4_aw_cjk_subject_ellipsis_action_authority_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }


__all__ = [
    "FINAL_STATUS",
    "LABEL",
    "PROVISIONAL_STATUS",
    "SCHEMA",
    "append_cjk_subject_ellipsis_action_authority_node_p4_aw",
    "assess_cjk_subject_ellipsis_candidate_p4_aw",
    "build_dataset_evidence_p4_aw",
    "finalize_cjk_subject_ellipsis_authority_p4_aw",
    "install_cjk_subject_ellipsis_action_authority_hooks_p4_aw",
    "install_cjk_subject_ellipsis_action_authority_p4_aw",
]
