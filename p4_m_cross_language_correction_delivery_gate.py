#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-M cross-language correction case."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_m_cross_language_correction_delivery_acceptance_v1.json"


class P4MCorrectionDeliveryGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_m_cross_language_correction_delivery_acceptance_v1":
        raise P4MCorrectionDeliveryGateError("contract_schema_invalid")
    write = contract.get("session_1_write_turn") or {}
    correction = contract.get("session_1_correction_turn") or {}
    recall = contract.get("session_2_recall_turn") or {}
    if "飲料" not in str(write.get("input") or "") or "梅子ソーダ" not in str(write.get("input") or ""):
        raise P4MCorrectionDeliveryGateError("write_alias_or_value_missing")
    if "飲み物" not in str(correction.get("input") or ""):
        raise P4MCorrectionDeliveryGateError("correction_alias_missing")
    if "梅子ソーダ" not in str(correction.get("input") or "") or "柚子茶" not in str(correction.get("input") or ""):
        raise P4MCorrectionDeliveryGateError("correction_pair_missing")
    if "柚子茶" in str(recall.get("input") or "") or recall.get("input_must_not_contain_answer") is not True:
        raise P4MCorrectionDeliveryGateError("recall_answer_leak")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("process_starts") != 2 or runtime.get("real_product_turns") != 3:
        raise P4MCorrectionDeliveryGateError("execution_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4MCorrectionDeliveryGateError("retry_not_forbidden")


def _check(failures, observed, expected, prefix):
    for field, value in expected.items():
        if observed.get(field) != value:
            failures.append(f"{prefix}_mismatch:{field}")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    write = evidence.get("session_1_write_turn") or {}
    correction = evidence.get("session_1_correction_turn") or {}
    restart = evidence.get("restart") or {}
    recall = evidence.get("session_2_recall_turn") or {}
    persistence = evidence.get("persistent_state") or {}
    accounting = evidence.get("accounting") or {}
    safari = evidence.get("safari") or {}
    common = contract["per_turn_requirements"]

    _check(failures, write, {
        "input": contract["session_1_write_turn"]["input"],
        "visible_output": contract["session_1_write_turn"]["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "act": "write",
        "input_language": contract["session_1_write_turn"]["expected_language"],
        "scope": "drink",
        "scope_source": "canonical_alias_projection",
        "current_value": contract["session_1_write_turn"]["expected_current_value"],
        "p4_l_alias_id": contract["session_1_write_turn"]["expected_alias_id"],
        "p4_i_status": "typed_current_preference_written",
        "p4_l_status": "canonical_scope_projected",
        "durable_episode_write_count": 1,
        "product_planner_model_call_count": 0,
        "fallback_count": 0,
    }, "write")
    if not write.get("episode_id") or not write.get("current_memory_id"):
        failures.append("write_identity_missing")

    _check(failures, correction, {
        "input": contract["session_1_correction_turn"]["input"],
        "visible_output": contract["session_1_correction_turn"]["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "act": "correction",
        "input_language": contract["session_1_correction_turn"]["expected_language"],
        "scope": "drink",
        "scope_source": "canonical_alias_projection",
        "previous_value": contract["session_1_correction_turn"]["expected_previous_value"],
        "current_value": contract["session_1_correction_turn"]["expected_current_value"],
        "p4_l_alias_id": contract["session_1_correction_turn"]["expected_alias_id"],
        "profile_likes": contract["session_1_correction_turn"]["expected_profile_likes"],
        "profile_dislikes": contract["session_1_correction_turn"]["expected_profile_dislikes"],
        "profile_write_count": contract["session_1_correction_turn"]["expected_profile_write_count"],
        "active_current_count": 1,
        "historical_current_count": 1,
        "explicit_negative_count": 1,
        "history_preserved": True,
        "p4_i_status": "typed_current_preference_written",
        "p4_l_status": "canonical_scope_projected",
        "durable_episode_write_count": 1,
        "product_planner_model_call_count": 0,
        "fallback_count": 0,
    }, "correction")
    if not correction.get("episode_id") or not correction.get("current_memory_id") or not correction.get("negative_old_memory_id"):
        failures.append("correction_identity_missing")
    if correction.get("previous_current_memory_id") != write.get("current_memory_id"):
        failures.append("correction_not_linked_to_write")
    if correction.get("active_current_ids") != [correction.get("current_memory_id")]:
        failures.append("correction_not_unique_active")
    if correction.get("historical_current_ids") != [write.get("current_memory_id")]:
        failures.append("write_not_unique_historical")

    _check(failures, recall, {
        "input": contract["session_2_recall_turn"]["input"],
        "visible_output": contract["session_2_recall_turn"]["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "p4_j_status": contract["session_2_recall_turn"]["expected_contract_status"],
        "p4_j_answer_use_authorized": True,
        "query_language": "en",
        "scope": "drink",
        "localized_value_jp": contract["session_2_recall_turn"]["expected_localized_value_jp"],
        "p4_j_graph_label": "typed_current_preference_recall_p4",
        "p4_j_graph_stage": "select",
        "p4_j_final_surface_exact": True,
        "p4_j_raw_dialogue_persisted": False,
        "p4_i_typed_write_count": 0,
        "p4_l_canonicalization_count": 0,
        "profile_write_count": 0,
        "historical_answer_use_count": 0,
        "explicit_negative_answer_use_count": 0,
        "episode_answer_use_count": 0,
        "durable_episode_write_count": 1,
        "product_planner_model_call_count": 0,
        "fallback_count": 0,
    }, "recall")
    if recall.get("active_memory_id") != correction.get("current_memory_id"):
        failures.append("recall_did_not_use_correction")
    if write.get("current_memory_id") in (recall.get("answer_memory_ids") or []):
        failures.append("historical_write_used_in_answer")

    for turn_name, turn in (("write", write), ("correction", correction), ("recall", recall)):
        if float(turn.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
            failures.append(f"{turn_name}_latency_target_missed")

    if restart.get("old_process_exit_observed") is not True:
        failures.append("old_process_exit_not_observed")
    if not restart.get("new_pid") or restart.get("old_pid") == restart.get("new_pid"):
        failures.append("pid_not_changed")
    if not restart.get("new_session_id") or restart.get("old_session_id") == restart.get("new_session_id"):
        failures.append("session_id_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failures.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failures.append("memory_db_changed")
    if restart.get("process_2_start_active_id") != correction.get("current_memory_id"):
        failures.append("restart_active_id_mismatch")
    if restart.get("process_2_start_historical_ids") != [write.get("current_memory_id")]:
        failures.append("restart_historical_lineage_mismatch")
    if restart.get("post_turn_memory_injection_count") != 0:
        failures.append("post_turn_memory_injection_nonzero")

    for field, expected in contract["persistent_state_requirements"].items():
        if persistence.get(field) != expected:
            failures.append(f"persistent_state_mismatch:{field}")

    ceiling = contract["runtime_requirements"]
    for field in (
        "process_starts", "process_restart_count", "real_product_turns", "retry_count",
        "fallback_count", "paid_api_call_count", "external_deployment_count",
        "production_memory_access_count", "function_tool_execution_count", "vrm_action_execution_count",
    ):
        if accounting.get(field) != ceiling[field]:
            failures.append(f"accounting_mismatch:{field}")
    calls = accounting.get("local_product_planner_model_calls")
    if not isinstance(calls, int) or calls > ceiling["local_product_planner_model_calls_maximum"]:
        failures.append("accounting_model_call_ceiling_exceeded")
    if evidence.get("runtime", {}).get("fresh_isolated_root") is not True:
        failures.append("runtime_not_fresh_isolated")
    if evidence.get("runtime", {}).get("listener") != ceiling["listener"]:
        failures.append("runtime_listener_mismatch")
    if safari.get("actual_two_process_three_turn_acceptance") is not True:
        failures.append("safari_acceptance_missing")
    if safari.get("closed_tab_count") != 0:
        failures.append("safari_tab_closed")
    if safari.get("p4_l_graph_node_visible_on_write_and_correction") is not True:
        failures.append("safari_p4_l_graph_missing")
    if safari.get("p4_j_graph_node_visible_on_recall") is not True:
        failures.append("safari_p4_j_graph_missing")
    return {
        "schema": "uruha_p4_m_cross_language_correction_delivery_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
