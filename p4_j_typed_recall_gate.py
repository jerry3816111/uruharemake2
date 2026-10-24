#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-J cross-restart typed recall case."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_j_cross_restart_typed_recall_acceptance_v1.json"


class P4JTypedRecallGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_j_cross_restart_typed_recall_acceptance_v1":
        raise P4JTypedRecallGateError("contract_schema_invalid")
    first = contract.get("process_1") or {}
    second = contract.get("process_2") or {}
    if "rooibos tea" not in str(first.get("input") or "").casefold():
        raise P4JTypedRecallGateError("first_input_invalid")
    if "rooibos" in str(second.get("input") or "").casefold() or "ルイボス" in str(
        second.get("input") or ""
    ):
        raise P4JTypedRecallGateError("recall_input_contains_answer")
    if second.get("input_must_not_contain_answer") is not True:
        raise P4JTypedRecallGateError("answer_absent_requirement_missing")
    restart = contract.get("restart") or {}
    required_true = (
        "old_process_must_exit",
        "new_pid_required",
        "new_product_session_id_required",
        "same_runtime_root_required",
        "same_memory_db_required",
        "reuse_runtime_manifest_required",
        "process_2_start_must_observe_process_1_active_typed_record",
    )
    if not all(restart.get(key) is True for key in required_true):
        raise P4JTypedRecallGateError("restart_requirement_missing")
    if restart.get("post_turn_memory_injection_allowed") is not False:
        raise P4JTypedRecallGateError("memory_injection_not_forbidden")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("process_starts") != 2 or runtime.get("real_product_turns") != 2:
        raise P4JTypedRecallGateError("execution_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4JTypedRecallGateError("retry_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    runtime = evidence.get("runtime") or {}
    first = evidence.get("process_1_turn") or {}
    restart = evidence.get("restart") or {}
    second = evidence.get("process_2_turn") or {}
    persistence = evidence.get("persistent_state") or {}
    accounting = evidence.get("accounting") or {}
    safari = evidence.get("safari") or {}
    common = contract["per_turn_requirements"]
    first_expected = contract["process_1"]
    second_expected = contract["process_2"]
    first_trace = contract["process_1_trace_requirements"]
    second_trace = contract["process_2_trace_requirements"]

    first_exact = {
        "input": first_expected["input"],
        "visible_output": first_expected["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "act": first_expected["expected_act"],
        "input_language": first_expected["expected_language"],
        "scope": first_expected["expected_scope"],
        "current_value": first_expected["expected_current_value"],
        "profile_likes": first_expected["expected_profile_likes"],
        "profile_dislikes": first_expected["expected_profile_dislikes"],
        "profile_write_count": first_expected["expected_profile_write_count"],
        "p4_h_status": first_trace["p4_h_status"],
        "p4_h_graph_label": first_trace["p4_h_graph_label"],
        "p4_h_graph_stage": first_trace["p4_h_graph_stage"],
        "p4_i_status": first_trace["p4_i_status"],
        "p4_i_graph_label": first_trace["p4_i_graph_label"],
        "p4_i_graph_stage": first_trace["p4_i_graph_stage"],
        "p4_j_selected": first_trace["p4_j_selected"],
        "durable_episode_write_count": common["durable_episode_write_count"],
        "product_planner_model_call_count": common["product_planner_model_call_count"],
        "fallback_count": common["fallback_count"],
    }
    for field, expected in first_exact.items():
        if first.get(field) != expected:
            failures.append(f"process_1_mismatch:{field}")
    if not first.get("episode_id"):
        failures.append("process_1_episode_id_missing")
    if not first.get("current_memory_id"):
        failures.append("process_1_current_memory_id_missing")
    if float(first.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
        failures.append("process_1_latency_target_missed")

    second_exact = {
        "input": second_expected["input"],
        "visible_output": second_expected["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "p4_j_status": second_expected["expected_contract_status"],
        "p4_j_answer_use_authorized": second_expected["expected_answer_use_authorized"],
        "query_language": second_expected["expected_query_language"],
        "scope": second_expected["expected_scope"],
        "localized_value_jp": second_expected["expected_localized_value_jp"],
        "p4_j_graph_label": second_trace["p4_j_graph_label"],
        "p4_j_graph_stage": second_trace["p4_j_graph_stage"],
        "p4_j_final_surface_exact": second_trace["p4_j_final_surface_exact"],
        "p4_j_raw_dialogue_persisted": second_trace["p4_j_raw_dialogue_persisted"],
        "p4_h_selected": second_trace["p4_h_selected"],
        "p4_i_typed_write_count": second_trace["p4_i_typed_write_count"],
        "profile_write_count": second_expected["profile_write_count"],
        "historical_answer_use_count": second_expected["historical_answer_use_count"],
        "explicit_negative_answer_use_count": second_expected[
            "explicit_negative_answer_use_count"
        ],
        "episode_answer_use_count": second_expected["episode_answer_use_count"],
        "durable_episode_write_count": common["durable_episode_write_count"],
        "product_planner_model_call_count": common["product_planner_model_call_count"],
        "fallback_count": common["fallback_count"],
    }
    for field, expected in second_exact.items():
        if second.get(field) != expected:
            failures.append(f"process_2_mismatch:{field}")
    if not second.get("episode_id"):
        failures.append("process_2_episode_id_missing")
    if second.get("active_memory_id") != first.get("current_memory_id"):
        failures.append("process_2_did_not_use_process_1_typed_record")
    if float(second.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
        failures.append("process_2_latency_target_missed")

    if first.get("episode_id") == second.get("episode_id"):
        failures.append("episode_ids_not_distinct")
    if restart.get("old_process_exit_observed") is not True:
        failures.append("old_process_exit_not_observed")
    if not restart.get("new_pid") or restart.get("old_pid") == restart.get("new_pid"):
        failures.append("pid_not_changed")
    if not restart.get("new_session_id") or restart.get("old_session_id") == restart.get(
        "new_session_id"
    ):
        failures.append("session_id_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failures.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failures.append("memory_db_changed")
    if restart.get("process_2_start_observed_first_active_id") != first.get(
        "current_memory_id"
    ):
        failures.append("process_2_start_did_not_observe_first_active_record")
    if restart.get("post_turn_memory_injection_count") != 0:
        failures.append("post_turn_memory_injection_nonzero")

    for field, expected in contract["persistent_state_requirements"].items():
        if persistence.get(field) != expected:
            failures.append(f"persistent_state_mismatch:{field}")

    ceiling = contract["runtime_requirements"]
    for field in (
        "process_starts",
        "process_restart_count",
        "real_product_turns",
        "retry_count",
        "fallback_count",
        "paid_api_call_count",
        "external_deployment_count",
        "production_memory_access_count",
        "function_tool_execution_count",
        "vrm_action_execution_count",
    ):
        if accounting.get(field) != ceiling[field]:
            failures.append(f"accounting_mismatch:{field}")
    calls = accounting.get("local_product_planner_model_calls")
    if not isinstance(calls, int) or calls > ceiling["local_product_planner_model_calls_maximum"]:
        failures.append("accounting_model_call_ceiling_exceeded")
    if runtime.get("fresh_isolated_root") is not True:
        failures.append("runtime_not_fresh_isolated")
    if runtime.get("listener") != ceiling["listener"]:
        failures.append("runtime_listener_mismatch")
    if safari.get("actual_two_process_two_turn_acceptance") is not True:
        failures.append("safari_acceptance_missing")
    if safari.get("closed_tab_count") != ceiling["closed_user_tab_count"]:
        failures.append("safari_tab_closed")
    if safari.get("p4_j_graph_node_visible_on_recall") is not True:
        failures.append("safari_p4_j_graph_missing")
    return {
        "schema": "uruha_p4_j_typed_recall_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
