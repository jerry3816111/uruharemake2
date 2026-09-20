#!/usr/bin/env python3
"""Fail-closed P4-E contract and evidence validator."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_e_cross_restart_memory_recall_contract_v1.json"


class P4ECrossRestartMemoryError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(payload)
    return payload


def validate_contract(contract: dict) -> None:
    if contract.get("schema") != "uruha_p4_e_cross_restart_memory_recall_contract_v1":
        raise P4ECrossRestartMemoryError("contract_schema_invalid")
    first = contract.get("session_1") or {}
    second = contract.get("session_2") or {}
    first_input = str(first.get("input") or "")
    second_input = str(second.get("input") or "")
    if "Rina" not in first_input or "black coffee" not in first_input or "herbal tea" not in first_input:
        raise P4ECrossRestartMemoryError("session_1_fact_pair_invalid")
    absent = str(second.get("answer_value_absent_from_input") or "").casefold()
    if not absent or absent in second_input.casefold():
        raise P4ECrossRestartMemoryError("recall_prompt_contains_answer_value")
    if first.get("visible_output_language_required") != "Japanese":
        raise P4ECrossRestartMemoryError("session_1_visible_language_invalid")
    if second.get("visible_output_language_required") != "Japanese":
        raise P4ECrossRestartMemoryError("session_2_visible_language_invalid")
    if second.get("maximum_product_planner_model_calls") != 0:
        raise P4ECrossRestartMemoryError("recall_model_call_ceiling_invalid")
    restart = contract.get("restart") or {}
    required_true = (
        "old_process_must_exit",
        "new_pid_required",
        "new_product_session_id_required",
        "same_runtime_root_required",
        "same_memory_db_required",
        "reuse_runtime_manifest_required",
    )
    if not all(restart.get(key) is True for key in required_true):
        raise P4ECrossRestartMemoryError("restart_proof_requirement_missing")
    if restart.get("server_side_injection_or_seed_after_session_1_allowed") is not False:
        raise P4ECrossRestartMemoryError("post_turn_seed_not_forbidden")
    ceiling = contract.get("execution_ceiling") or {}
    if ceiling.get("real_product_turns") != 2 or ceiling.get("retry_count") != 0:
        raise P4ECrossRestartMemoryError("execution_ceiling_invalid")


def evaluate_evidence(contract: dict, evidence: dict) -> dict:
    """Return exact failed gates without repairing or interpreting the evidence."""
    validate_contract(contract)
    failed = []
    runtime = evidence.get("runtime") or {}
    turn_1 = evidence.get("session_1_turn") or {}
    restart = evidence.get("restart") or {}
    turn_2 = evidence.get("session_2_turn") or {}
    vrm = evidence.get("vrm_restart_boundary") or {}
    accounting = evidence.get("accounting") or {}

    if runtime.get("production_memory_access_count") != 0:
        failed.append("production_memory_access_nonzero")
    if turn_1.get("input") != contract["session_1"]["input"]:
        failed.append("session_1_input_mismatch")
    if turn_1.get("visible_output_language") != "Japanese":
        failed.append("session_1_visible_language_mismatch")
    if restart.get("old_process_exit_observed") is not True:
        failed.append("old_process_exit_not_observed")
    if restart.get("old_pid") == restart.get("new_pid") or not restart.get("new_pid"):
        failed.append("pid_not_changed")
    if restart.get("old_session_id") == restart.get("new_session_id") or not restart.get("new_session_id"):
        failed.append("session_id_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failed.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failed.append("memory_db_changed")
    if restart.get("post_turn_memory_injection_count") != 0:
        failed.append("post_turn_memory_injection_nonzero")
    if turn_2.get("input") != contract["session_2"]["input"]:
        failed.append("session_2_input_mismatch")
    if turn_2.get("visible_output") != contract["session_2"]["expected_visible_output"]:
        failed.append("recall_visible_output_mismatch")
    if turn_2.get("visible_output_language") != "Japanese":
        failed.append("session_2_visible_language_mismatch")
    if turn_2.get("contract_status") != contract["session_2"]["expected_contract_status"]:
        failed.append("recall_contract_status_mismatch")
    if turn_2.get("selected_speaker") != contract["session_2"]["expected_selected_speaker"]:
        failed.append("selected_speaker_mismatch")
    if turn_2.get("candidate_count") != contract["session_2"]["expected_candidate_count"]:
        failed.append("candidate_count_mismatch")
    if turn_2.get("planner_path") != contract["session_2"]["expected_planner_path"]:
        failed.append("planner_path_mismatch")
    trace_id = str(turn_2.get("retrieved_trace_id") or "")
    if not trace_id.startswith(contract["session_2"]["retrieved_trace_id_prefix"]):
        failed.append("retrieved_trace_id_missing")
    if not turn_2.get("retrieved_memory_id"):
        failed.append("retrieved_memory_id_missing")
    if turn_2.get("retrieved_source_predates_new_session") is not True:
        failed.append("retrieved_source_not_proven_pre_restart")
    if turn_2.get("graph_node_visible") != contract["session_2"]["graph_node_required"]:
        failed.append("graph_node_not_visible")
    if turn_2.get("product_planner_model_call_count") != 0:
        failed.append("recall_product_planner_model_call_nonzero")
    if vrm.get("stage_after_new_page_load") != contract["browser_only_vrm_restart_boundary"]["expected_stage_after_new_page_load"]:
        failed.append("vrm_stage_persisted_across_restart")
    if vrm.get("server_persisted_previous_local_file") is not False:
        failed.append("vrm_local_file_persisted_by_server")
    ceilings = contract["execution_ceiling"]
    for key in (
        "real_product_turns",
        "process_starts",
        "process_restart_count",
        "retry_count",
        "paid_api_call_count",
        "external_deployment_count",
        "function_tool_execution_count",
        "vrm_action_execution_count",
    ):
        if accounting.get(key) != ceilings.get(key):
            failed.append(f"accounting_mismatch:{key}")
    return {
        "schema": "uruha_p4_e_cross_restart_memory_gate_result_v1",
        "status": "pass" if not failed else "fail",
        "failed_gates": failed,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
