#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-K cross-restart surface delivery case."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_k_cross_restart_surface_delivery_acceptance_v1.json"


class P4KSurfaceDeliveryGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_k_cross_restart_surface_delivery_acceptance_v1":
        raise P4KSurfaceDeliveryGateError("contract_schema_invalid")
    first = contract.get("process_1") or {}
    second = contract.get("process_2") or {}
    if "紅茶" not in str(first.get("input") or ""):
        raise P4KSurfaceDeliveryGateError("first_input_value_missing")
    if "紅茶" in str(second.get("input") or ""):
        raise P4KSurfaceDeliveryGateError("recall_input_contains_answer")
    if second.get("input_must_not_contain_answer") is not True:
        raise P4KSurfaceDeliveryGateError("answer_absent_requirement_missing")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("process_starts") != 2 or runtime.get("real_product_turns") != 2:
        raise P4KSurfaceDeliveryGateError("execution_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4KSurfaceDeliveryGateError("retry_not_forbidden")
    if contract.get("failure_policy", {}).get("p4_j_rooibos_case_rerun_allowed") is not False:
        raise P4KSurfaceDeliveryGateError("old_case_reuse_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    first = evidence.get("process_1_turn") or {}
    restart = evidence.get("restart") or {}
    second = evidence.get("process_2_turn") or {}
    persistence = evidence.get("persistent_state") or {}
    accounting = evidence.get("accounting") or {}
    safari = evidence.get("safari") or {}
    common = contract["per_turn_requirements"]

    first_expected = {
        "input": contract["process_1"]["input"],
        "visible_output": contract["process_1"]["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "act": contract["process_1"]["expected_act"],
        "input_language": contract["process_1"]["expected_language"],
        "scope": contract["process_1"]["expected_scope"],
        "current_value": contract["process_1"]["expected_current_value"],
        "profile_likes": contract["process_1"]["expected_profile_likes"],
        "profile_dislikes": contract["process_1"]["expected_profile_dislikes"],
        "profile_write_count": contract["process_1"]["expected_profile_write_count"],
        "p4_h_status": "explicit_preference_memory_act_committed",
        "p4_i_status": "typed_current_preference_written",
        "p4_j_selected": False,
        "durable_episode_write_count": common["durable_episode_write_count"],
        "product_planner_model_call_count": common["product_planner_model_call_count"],
        "fallback_count": common["fallback_count"],
    }
    for field, expected in first_expected.items():
        if first.get(field) != expected:
            failures.append(f"process_1_mismatch:{field}")
    if not first.get("episode_id") or not first.get("current_memory_id"):
        failures.append("process_1_identity_missing")
    if float(first.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
        failures.append("process_1_latency_target_missed")

    second_expected = {
        "input": contract["process_2"]["input"],
        "visible_output": contract["process_2"]["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "p4_j_status": contract["process_2"]["expected_contract_status"],
        "p4_j_answer_use_authorized": contract["process_2"]["expected_answer_use_authorized"],
        "query_language": contract["process_2"]["expected_query_language"],
        "scope": contract["process_2"]["expected_scope"],
        "localized_value_jp": contract["process_2"]["expected_localized_value_jp"],
        "p4_j_graph_label": contract["process_2"]["expected_p4_j_graph_label"],
        "p4_j_graph_stage": contract["process_2"]["expected_p4_j_graph_stage"],
        "p4_j_final_surface_exact": True,
        "p4_j_raw_dialogue_persisted": False,
        "p4_h_selected": False,
        "p4_i_typed_write_count": 0,
        "profile_write_count": contract["process_2"]["profile_write_count"],
        "historical_answer_use_count": contract["process_2"]["historical_answer_use_count"],
        "explicit_negative_answer_use_count": contract["process_2"]["explicit_negative_answer_use_count"],
        "episode_answer_use_count": contract["process_2"]["episode_answer_use_count"],
        "durable_episode_write_count": common["durable_episode_write_count"],
        "product_planner_model_call_count": common["product_planner_model_call_count"],
        "fallback_count": common["fallback_count"],
    }
    for field, expected in second_expected.items():
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
    if not restart.get("new_session_id") or restart.get("old_session_id") == restart.get("new_session_id"):
        failures.append("session_id_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failures.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failures.append("memory_db_changed")
    if restart.get("process_2_start_observed_first_active_id") != first.get("current_memory_id"):
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
    if evidence.get("runtime", {}).get("fresh_isolated_root") is not True:
        failures.append("runtime_not_fresh_isolated")
    if evidence.get("runtime", {}).get("listener") != ceiling["listener"]:
        failures.append("runtime_listener_mismatch")
    if safari.get("actual_two_process_two_turn_acceptance") is not True:
        failures.append("safari_acceptance_missing")
    if safari.get("closed_tab_count") != ceiling["closed_user_tab_count"]:
        failures.append("safari_tab_closed")
    if safari.get("p4_j_graph_node_visible_on_recall") is not True:
        failures.append("safari_p4_j_graph_missing")
    return {
        "schema": "uruha_p4_k_surface_delivery_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
