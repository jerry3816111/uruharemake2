#!/usr/bin/env python3
"""Fail-closed gate for the P4-Q-REAL Safari correction lifecycle."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_q_real_safari_correction_lifecycle_acceptance_v1.json"


class P4QRealGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_q_real_safari_correction_lifecycle_acceptance_v1":
        raise P4QRealGateError("contract_schema_invalid")
    novelty = contract.get("novelty_requirements") or {}
    write = contract.get("session_1_write_turn") or {}
    correction = contract.get("session_1_correction_turn") or {}
    recall = contract.get("session_2_recall_turn") or {}
    old_value = str(novelty.get("old_value") or "")
    new_value = str(novelty.get("new_value") or "")
    if not old_value or not new_value or old_value == new_value:
        raise P4QRealGateError("value_pair_invalid")
    if old_value not in str(write.get("input") or ""):
        raise P4QRealGateError("write_value_missing")
    if old_value not in str(correction.get("input") or "") or new_value not in str(
        correction.get("input") or ""
    ):
        raise P4QRealGateError("correction_pair_missing")
    if old_value in str(recall.get("input") or "") or new_value in str(recall.get("input") or ""):
        raise P4QRealGateError("recall_answer_leak")
    if novelty.get("old_value_repository_occurrences_before_freeze") != 0 or novelty.get(
        "new_value_repository_occurrences_before_freeze"
    ) != 0:
        raise P4QRealGateError("value_pair_not_novel")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("product_entry") != "uruha_web_ui_product_p4_o.py":
        raise P4QRealGateError("wrong_product_entry")
    if runtime.get("installed_builder_module") != "uruha_persisted_reference_time_p4":
        raise P4QRealGateError("wrong_builder_module")
    if runtime.get("process_starts") != 2 or runtime.get("real_product_turns") != 3:
        raise P4QRealGateError("execution_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4QRealGateError("retry_not_forbidden")
    if (contract.get("failure_policy") or {}).get("same_case_rerun_allowed") is not False:
        raise P4QRealGateError("same_case_rerun_not_forbidden")


def _expect(failures, observed, expected, prefix):
    for field, value in expected.items():
        if observed.get(field) != value:
            failures.append(f"{prefix}_mismatch:{field}")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    common = contract["per_turn_requirements"]
    expected_write = contract["session_1_write_turn"]
    expected_correction = contract["session_1_correction_turn"]
    expected_recall = contract["session_2_recall_turn"]
    write = evidence.get("session_1_write_turn") or {}
    correction = evidence.get("session_1_correction_turn") or {}
    recall = evidence.get("session_2_recall_turn") or {}
    restart = evidence.get("restart") or {}

    _expect(failures, write, {
        "input": expected_write["input"], "visible_output": expected_write["expected_visible_output"],
        "visible_output_language": "Japanese", "act": "write", "input_language": "zh",
        "scope": "drink", "scope_source": "canonical_alias_projection",
        "current_value": expected_write["expected_current_value"],
        "p4_l_alias_id": expected_write["expected_alias_id"],
        "p4_i_status": "typed_current_preference_written", "p4_l_status": "canonical_scope_projected",
        "durable_episode_write_count": 1, "product_planner_model_call_count": 0, "fallback_count": 0,
    }, "write")
    if not write.get("episode_id") or not write.get("current_memory_id"):
        failures.append("write_identity_missing")

    _expect(failures, correction, {
        "input": expected_correction["input"], "visible_output": expected_correction["expected_visible_output"],
        "visible_output_language": "Japanese", "act": "correction", "input_language": "ja",
        "scope": "drink", "scope_source": "canonical_alias_projection",
        "previous_value": expected_correction["expected_previous_value"],
        "current_value": expected_correction["expected_current_value"],
        "p4_l_alias_id": expected_correction["expected_alias_id"],
        "profile_likes": expected_correction["expected_profile_likes"],
        "profile_dislikes": expected_correction["expected_profile_dislikes"],
        "profile_write_count": 2, "active_current_count": 1, "historical_current_count": 1,
        "explicit_negative_count": 1, "history_preserved": True,
        "p4_i_status": "typed_current_preference_written", "p4_l_status": "canonical_scope_projected",
        "durable_episode_write_count": 1, "product_planner_model_call_count": 0, "fallback_count": 0,
    }, "correction")
    if not correction.get("episode_id") or not correction.get("current_memory_id") or not correction.get(
        "negative_old_memory_id"
    ):
        failures.append("correction_identity_missing")
    if correction.get("previous_current_memory_id") != write.get("current_memory_id"):
        failures.append("correction_not_linked_to_write")
    if correction.get("active_current_ids") != [correction.get("current_memory_id")]:
        failures.append("correction_not_unique_active")
    if correction.get("historical_current_ids") != [write.get("current_memory_id")]:
        failures.append("write_not_unique_historical")

    _expect(failures, recall, {
        "input": expected_recall["input"], "visible_output": expected_recall["expected_visible_output"],
        "visible_output_language": "Japanese", "p4_j_status": expected_recall["expected_contract_status"],
        "p4_j_answer_use_authorized": True, "query_language": "en", "scope": "drink",
        "localized_value_jp": expected_recall["expected_localized_value_jp"],
        "value_surface_strategy": "bounded_japanese_identity", "identity_localization_applied": True,
        "p4_n_status": "bounded_japanese_identity_authorized",
        "p4_j_graph_label": "typed_current_preference_recall_p4", "p4_j_graph_stage": "select",
        "p4_j_final_surface_exact": True, "p4_j_raw_dialogue_persisted": False,
        "p4_i_typed_write_count": 0, "p4_l_canonicalization_count": 0, "profile_write_count": 0,
        "historical_answer_use_count": 0, "explicit_negative_answer_use_count": 0,
        "episode_answer_use_count": 0, "durable_episode_write_count": 1,
        "product_planner_model_call_count": 0, "fallback_count": 0,
    }, "recall")
    if recall.get("active_memory_id") != correction.get("current_memory_id"):
        failures.append("recall_did_not_use_correction")
    if recall.get("answer_memory_ids") != [correction.get("current_memory_id")]:
        failures.append("recall_answer_lineage_invalid")
    if contract["novelty_requirements"]["old_value"] in str(recall.get("visible_output") or ""):
        failures.append("historical_value_leaked_to_surface")

    for name, turn in (("write", write), ("correction", correction), ("recall", recall)):
        if float(turn.get("end_to_end_seconds", 10**9)) > common["latency_target_seconds"]:
            failures.append(f"{name}_latency_target_missed")

    if restart.get("old_process_exit_observed") is not True:
        failures.append("old_process_exit_not_observed")
    if restart.get("old_listener_closed_before_new_process") is not True:
        failures.append("old_listener_not_closed")
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
    if restart.get("process_2_start_negative_ids") != [correction.get("negative_old_memory_id")]:
        failures.append("restart_negative_lineage_mismatch")

    for field, expected in contract["persistent_state_requirements"].items():
        if (evidence.get("persistent_state") or {}).get(field) != expected:
            failures.append(f"persistent_state_mismatch:{field}")
    ceiling = contract["runtime_requirements"]
    _expect(failures, evidence.get("runtime") or {}, {
        "fresh_isolated_root": True, "runtime_root_mode": "0700", "listener": ceiling["listener"],
        "product_entry": ceiling["product_entry"], "installed_builder_module": ceiling["installed_builder_module"],
    }, "runtime")
    accounting = evidence.get("accounting") or {}
    for field in (
        "process_starts", "process_restart_count", "real_product_turns", "retry_count", "fallback_count",
        "paid_api_call_count", "external_deployment_count", "production_memory_access_count",
        "function_tool_execution_count", "vrm_action_execution_count",
    ):
        if accounting.get(field) != ceiling[field]:
            failures.append(f"accounting_mismatch:{field}")
    if not isinstance(accounting.get("local_product_planner_model_calls"), int) or accounting.get(
        "local_product_planner_model_calls"
    ) > ceiling["local_product_planner_model_calls_maximum"]:
        failures.append("accounting_model_call_ceiling_exceeded")
    safari = evidence.get("safari") or {}
    _expect(failures, safari, {
        "actual_two_process_three_turn_acceptance": True, "closed_tab_count": 0,
        "p4_l_graph_node_visible_on_write_and_correction": True,
        "p4_j_graph_node_visible_on_recall": True, "bounded_japanese_identity_visible_in_graph": True,
    }, "safari")
    return {
        "schema": "uruha_p4_q_real_safari_correction_lifecycle_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
