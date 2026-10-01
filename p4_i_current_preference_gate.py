#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-I cross-restart product case."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_i_cross_restart_current_preference_acceptance_v1.json"


class P4ICurrentPreferenceGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_i_cross_restart_current_preference_acceptance_v1":
        raise P4ICurrentPreferenceGateError("contract_schema_invalid")
    first = contract.get("process_1") or {}
    second = contract.get("process_2") or {}
    if "oolong tea" not in str(first.get("input") or "").casefold():
        raise P4ICurrentPreferenceGateError("first_input_invalid")
    if "barley tea" not in str(second.get("input") or "").casefold():
        raise P4ICurrentPreferenceGateError("second_input_invalid")
    if first.get("expected_current_value") != second.get("expected_previous_value"):
        raise P4ICurrentPreferenceGateError("correction_chain_invalid")
    if first.get("expected_scope") != second.get("expected_scope"):
        raise P4ICurrentPreferenceGateError("scope_chain_invalid")
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
        raise P4ICurrentPreferenceGateError("restart_requirement_missing")
    if restart.get("post_turn_memory_injection_allowed") is not False:
        raise P4ICurrentPreferenceGateError("memory_injection_not_forbidden")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("process_starts") != 2 or runtime.get("real_product_turns") != 2:
        raise P4ICurrentPreferenceGateError("execution_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4ICurrentPreferenceGateError("retry_not_forbidden")


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

    expected_turns = (
        ("process_1", contract["process_1"], first),
        ("process_2", contract["process_2"], second),
    )
    for label, expected, actual in expected_turns:
        exact = {
            "input": expected["input"],
            "visible_output": expected["expected_visible_output"],
            "visible_output_language": common["visible_output_language"],
            "p4_h_status": common["p4_h_status"],
            "p4_h_plan_authority": common["p4_h_plan_authority"],
            "p4_h_surface_authority": common["p4_h_surface_authority"],
            "p4_h_graph_label": common["p4_h_graph_label"],
            "p4_h_graph_stage": common["p4_h_graph_stage"],
            "p4_h_final_surface_exact": common["p4_h_final_surface_exact"],
            "p4_i_status": common["p4_i_status"],
            "p4_i_graph_label": common["p4_i_graph_label"],
            "p4_i_graph_stage": common["p4_i_graph_stage"],
            "p4_i_raw_dialogue_persisted": common["p4_i_raw_dialogue_persisted"],
            "p4_i_answer_use_authorized": common["p4_i_answer_use_authorized"],
            "act": expected["expected_act"],
            "input_language": expected["expected_language"],
            "scope": expected["expected_scope"],
            "current_value": expected["expected_current_value"],
            "profile_likes": expected["expected_profile_likes"],
            "profile_dislikes": expected["expected_profile_dislikes"],
            "profile_write_count": expected["expected_profile_write_count"],
            "durable_episode_write_count": common["durable_episode_write_count"],
            "product_planner_model_call_count": common["product_planner_model_call_count"],
            "fallback_count": common["fallback_count"],
        }
        if label == "process_2":
            exact.update(
                previous_value=expected["expected_previous_value"],
                scope_source=expected["expected_scope_source"],
            )
        for field, value in exact.items():
            if actual.get(field) != value:
                failures.append(f"{label}_mismatch:{field}")
        if not actual.get("episode_id"):
            failures.append(f"{label}_episode_id_missing")
        if not actual.get("current_memory_id"):
            failures.append(f"{label}_current_memory_id_missing")
        if len(actual.get("active_current_ids") or []) != expected["expected_active_current_count"]:
            failures.append(f"{label}_active_current_count_mismatch")
        if len(actual.get("historical_current_ids") or []) != expected["expected_historical_current_count"]:
            failures.append(f"{label}_historical_current_count_mismatch")
        if float(actual.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
            failures.append(f"{label}_latency_target_missed")

    if first.get("episode_id") == second.get("episode_id"):
        failures.append("episode_ids_not_distinct")
    if first.get("current_memory_id") == second.get("current_memory_id"):
        failures.append("current_memory_ids_not_distinct")
    if second.get("previous_current_memory_id") != first.get("current_memory_id"):
        failures.append("correction_link_not_first_current_memory")
    if first.get("current_memory_id") not in (second.get("historical_current_ids") or []):
        failures.append("old_current_memory_not_historical")
    if second.get("current_memory_id") not in (second.get("active_current_ids") or []):
        failures.append("new_current_memory_not_active")
    if not second.get("negative_old_memory_id"):
        failures.append("negative_old_memory_missing")
    if second.get("history_preserved") is not True:
        failures.append("history_preserved_flag_missing")

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
    if restart.get("process_2_start_observed_first_active_id") != first.get("current_memory_id"):
        failures.append("process_2_did_not_observe_first_active_record")
    if restart.get("post_turn_memory_injection_count") != 0:
        failures.append("post_turn_memory_injection_nonzero")

    required_persistence = {
        "total_profile_record_count": contract["runtime_requirements"]["total_profile_record_count"],
        "total_episode_record_count": contract["runtime_requirements"]["total_episode_record_count"],
        "old_positive_record_present": True,
        "old_positive_state": "historical",
        "new_positive_state": "active",
        "negative_old_record_present": True,
        "negative_old_record_state": "active",
        "old_and_new_positive_predicate_match": True,
        "old_records_deleted_or_rewritten": False,
    }
    for field, value in required_persistence.items():
        if persistence.get(field) != value:
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
    if safari.get("p4_i_graph_node_visible_both_turns") is not True:
        failures.append("safari_p4_i_graph_missing")
    return {
        "schema": "uruha_p4_i_current_preference_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
