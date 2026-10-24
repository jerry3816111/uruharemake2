#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-P offline correction lifecycle."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_p_cross_language_correction_lifecycle_offline_v1.json"


class P4PCorrectionLifecycleGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_p_cross_language_correction_lifecycle_offline_v1":
        raise P4PCorrectionLifecycleGateError("contract_schema_invalid")
    pair = contract.get("development_pair") or {}
    first = contract.get("process_1") or {}
    second = contract.get("process_2") or {}
    old_value = str(pair.get("old_value") or "")
    new_value = str(pair.get("new_value") or "")
    if not old_value or not new_value or old_value == new_value:
        raise P4PCorrectionLifecycleGateError("development_pair_invalid")
    if old_value not in str(first.get("write_input") or ""):
        raise P4PCorrectionLifecycleGateError("write_value_missing")
    correction_input = str(first.get("correction_input") or "")
    if old_value not in correction_input or new_value not in correction_input:
        raise P4PCorrectionLifecycleGateError("correction_pair_missing")
    recall_input = str(second.get("recall_input") or "")
    if old_value in recall_input or new_value in recall_input:
        raise P4PCorrectionLifecycleGateError("recall_answer_leak")
    if second.get("input_must_not_contain_answer") is not True:
        raise P4PCorrectionLifecycleGateError("answer_absence_not_required")
    if old_value in contract.get("forbidden_previous_values", []) or new_value in contract.get(
        "forbidden_previous_values", []
    ):
        raise P4PCorrectionLifecycleGateError("previous_value_reused")
    runtime = contract.get("runtime_requirements") or {}
    if runtime.get("process_starts") != 2 or runtime.get("true_process_restart_count") != 1:
        raise P4PCorrectionLifecycleGateError("process_count_invalid")
    if runtime.get("retry_count") != 0:
        raise P4PCorrectionLifecycleGateError("retry_not_forbidden")
    failure = contract.get("failure_policy") or {}
    if failure.get("exact_case_execution_count") != 1 or failure.get("same_case_retry_allowed") is not False:
        raise P4PCorrectionLifecycleGateError("single_execution_not_frozen")


def _expect(failures, observed, expected, prefix):
    for field, value in expected.items():
        if observed.get(field) != value:
            failures.append(f"{prefix}_mismatch:{field}")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    pair = contract["development_pair"]
    expected_first = contract["process_1"]
    expected_second = contract["process_2"]
    first = evidence.get("process_1") or {}
    second = evidence.get("process_2") or {}
    restart = evidence.get("restart") or {}
    accounting = evidence.get("accounting") or {}

    _expect(
        failures,
        first,
        {
            "write_status": "typed_current_preference_written",
            "write_language": expected_first["write_language"],
            "write_scope": expected_first["expected_scope"],
            "write_scope_source": "canonical_alias_projection",
            "write_alias_id": expected_first["write_alias_id"],
            "write_value": pair["old_value"],
            "correction_status": "typed_current_preference_written",
            "correction_language": expected_first["correction_language"],
            "correction_scope": expected_first["expected_scope"],
            "correction_scope_source": "canonical_alias_projection",
            "correction_alias_id": expected_first["correction_alias_id"],
            "correction_previous_value": pair["old_value"],
            "correction_current_value": pair["new_value"],
            "active_current_count": expected_first["expected_active_current_count"],
            "historical_current_count": expected_first["expected_historical_current_count"],
            "explicit_negative_count": expected_first["expected_explicit_negative_count"],
            "profile_record_count": expected_first["expected_profile_record_count"],
            "history_preserved": True,
            "old_records_deleted_or_rewritten": False,
        },
        "process_1",
    )
    write_id = first.get("write_memory_id")
    correction_id = first.get("correction_memory_id")
    negative_id = first.get("negative_memory_id")
    if not write_id or not correction_id or not negative_id:
        failures.append("process_1_lineage_identity_missing")
    if first.get("previous_current_memory_id") != write_id:
        failures.append("correction_not_linked_to_write")
    if first.get("active_current_ids") != [correction_id]:
        failures.append("correction_not_unique_active")
    if first.get("historical_current_ids") != [write_id]:
        failures.append("write_not_unique_historical")
    if first.get("negative_correction_current_memory_id") != correction_id:
        failures.append("negative_not_linked_to_correction")

    _expect(
        failures,
        second,
        {
            "recall_status": expected_second["expected_status"],
            "answer_use_authorized": True,
            "query_language": "en",
            "scope": expected_first["expected_scope"],
            "localized_value_jp": pair["new_value"],
            "visible_surface": expected_second["expected_surface"],
            "value_surface_strategy": expected_second["expected_value_surface_strategy"],
            "source_bound_status": expected_second["expected_source_bound_status"],
            "profile_record_count_before": expected_second["expected_profile_record_count"],
            "profile_record_count_after": expected_second["expected_profile_record_count"],
            "profile_write_count": expected_second["expected_profile_write_count"],
            "historical_answer_use_count": expected_second["expected_historical_answer_use_count"],
            "explicit_negative_answer_use_count": expected_second[
                "expected_explicit_negative_answer_use_count"
            ],
            "profile_snapshot_unchanged": True,
        },
        "process_2",
    )
    if second.get("active_memory_id") != correction_id:
        failures.append("recall_did_not_use_correction")
    if second.get("answer_memory_ids") != [correction_id]:
        failures.append("recall_answer_lineage_invalid")
    if pair["old_value"] in str(second.get("visible_surface") or ""):
        failures.append("historical_value_leaked_to_surface")
    if second.get("process_start_active_ids") != [correction_id]:
        failures.append("restart_active_lineage_invalid")
    if second.get("process_start_historical_ids") != [write_id]:
        failures.append("restart_historical_lineage_invalid")
    if second.get("process_start_negative_ids") != [negative_id]:
        failures.append("restart_negative_lineage_invalid")
    if second.get("record_hashes_before") != first.get("record_hashes_after"):
        failures.append("record_hashes_changed_across_restart")
    if second.get("record_hashes_after") != first.get("record_hashes_after"):
        failures.append("record_hashes_changed_during_recall")

    if restart.get("old_process_exit_observed") is not True:
        failures.append("old_process_exit_not_observed")
    if not restart.get("old_pid") or not restart.get("new_pid") or restart.get("old_pid") == restart.get("new_pid"):
        failures.append("process_identity_not_changed")
    if not restart.get("old_session_id") or not restart.get("new_session_id") or restart.get(
        "old_session_id"
    ) == restart.get("new_session_id"):
        failures.append("session_identity_not_changed")
    if restart.get("same_persistent_db") is not True:
        failures.append("persistent_db_not_reused")

    for field, expected in contract["runtime_requirements"].items():
        if field == "storage":
            continue
        if accounting.get(field) != expected:
            failures.append(f"accounting_mismatch:{field}")
    return {
        "schema": "uruha_p4_p_cross_language_correction_lifecycle_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
