from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_h_multilingual_preference_memory_act_acceptance_v1.json"


def load_contract(path: Path = CONTRACT):
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_evidence(contract, evidence):
    failures = []
    expected_turns = contract.get("turns") or []
    actual_turns = evidence.get("turns") or []
    common = contract.get("per_turn_requirements") or {}
    if len(actual_turns) != len(expected_turns):
        failures.append("turn_count_mismatch")
    for index, expected in enumerate(expected_turns):
        if index >= len(actual_turns):
            failures.append(f"turn{index + 1}_missing")
            continue
        actual = actual_turns[index]
        fields = {
            "turn_index": expected["turn_index"],
            "input": expected["input"],
            "visible_output": expected["expected_visible_output"],
            "visible_output_language": common["visible_output_language"],
            "p4_h_status": common["p4_h_status"],
            "act": expected["expected_act"],
            "input_language": expected["expected_language"],
            "selected_intent": expected["expected_intent"],
            "plan_authority": common["plan_authority"],
            "surface_authority": common["surface_authority"],
            "planner_path": common["planner_path"],
            "planner_route": common["planner_route"],
            "product_planner_model_call_count": common["product_planner_model_call_count"],
            "fallback_count": common["fallback_count"],
            "graph_node_visible": common["graph_node_visible"],
            "graph_node_stage": common["graph_node_stage"],
            "final_visible_surface_matches_contract": common["final_visible_surface_matches_contract"],
            "durable_episode_write_count": common["durable_episode_write_count"],
            "raw_dialogue_persisted_in_p4_h_trace": common["raw_dialogue_persisted_in_p4_h_trace"],
        }
        for field, value in fields.items():
            if actual.get(field) != value:
                failures.append(f"turn{index + 1}_mismatch:{field}")
        if float(actual.get("end_to_end_seconds", 10**9)) > float(
            common["latency_target_seconds"]
        ):
            failures.append(f"turn{index + 1}_latency_target_missed")

    episode_ids = [row.get("episode_id") for row in actual_turns]
    if len(episode_ids) != len(expected_turns) or any(not value for value in episode_ids):
        failures.append("episode_id_missing")
    elif len(set(episode_ids)) != len(episode_ids):
        failures.append("episode_ids_not_distinct")

    runtime = contract.get("runtime_requirements") or {}
    actual_runtime = evidence.get("runtime") or {}
    actual_accounting = evidence.get("accounting") or {}
    accounting_fields = {
        "process_starts": runtime["process_starts"],
        "real_product_turns": runtime["real_product_turns"],
        "retry_count": runtime["retry_count"],
        "fallback_count": runtime["fallback_count"],
        "paid_api_call_count": runtime["paid_api_call_count"],
        "external_deployment_count": runtime["external_deployment_count"],
        "production_memory_access_count": runtime["production_memory_access_count"],
        "function_tool_execution_count": runtime["function_tool_execution_count"],
        "vrm_action_execution_count": runtime["vrm_action_execution_count"],
    }
    for field, value in accounting_fields.items():
        if actual_accounting.get(field) != value:
            failures.append(f"accounting_mismatch:{field}")
    if actual_accounting.get("local_product_planner_model_calls", 10**9) > runtime[
        "local_product_planner_model_calls_maximum"
    ]:
        failures.append("model_call_ceiling_exceeded")
    if actual_runtime.get("fresh_isolated_root") is not True:
        failures.append("runtime_not_fresh_isolated")
    if actual_runtime.get("listener") != runtime["listener"]:
        failures.append("runtime_listener_mismatch")
    if actual_runtime.get("production_memory_access_count") != 0:
        failures.append("runtime_production_memory_accessed")

    safari = evidence.get("safari") or {}
    if safari.get("actual_two_turn_acceptance") is not True:
        failures.append("safari_two_turn_acceptance_missing")
    if safari.get("closed_tab_count") != runtime["closed_user_tab_count"]:
        failures.append("safari_tab_closed")
    return {
        "schema": "uruha_p4_h_preference_memory_act_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
    }

