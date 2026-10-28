from copy import deepcopy

import p4_p_cross_language_correction_lifecycle_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    pair = contract["development_pair"]
    first = contract["process_1"]
    second = contract["process_2"]
    hashes = {"old": "a" * 64, "new": "b" * 64, "negative": "c" * 64}
    return {
        "process_1": {
            "write_status": "typed_current_preference_written",
            "write_language": "zh",
            "write_scope": "drink",
            "write_scope_source": "canonical_alias_projection",
            "write_alias_id": "drink:zh-Hant:v1",
            "write_value": pair["old_value"],
            "write_memory_id": "old",
            "correction_status": "typed_current_preference_written",
            "correction_language": "ja",
            "correction_scope": "drink",
            "correction_scope_source": "canonical_alias_projection",
            "correction_alias_id": "drink:ja:v1",
            "correction_previous_value": pair["old_value"],
            "correction_current_value": pair["new_value"],
            "correction_memory_id": "new",
            "previous_current_memory_id": "old",
            "negative_memory_id": "negative",
            "negative_correction_current_memory_id": "new",
            "active_current_ids": ["new"],
            "historical_current_ids": ["old"],
            "active_current_count": 1,
            "historical_current_count": 1,
            "explicit_negative_count": 1,
            "profile_record_count": 3,
            "history_preserved": True,
            "old_records_deleted_or_rewritten": False,
            "record_hashes_after": hashes,
        },
        "process_2": {
            "recall_status": second["expected_status"],
            "answer_use_authorized": True,
            "query_language": "en",
            "scope": "drink",
            "localized_value_jp": pair["new_value"],
            "visible_surface": second["expected_surface"],
            "value_surface_strategy": "bounded_japanese_identity",
            "source_bound_status": "bounded_japanese_identity_authorized",
            "active_memory_id": "new",
            "answer_memory_ids": ["new"],
            "process_start_active_ids": ["new"],
            "process_start_historical_ids": ["old"],
            "process_start_negative_ids": ["negative"],
            "profile_record_count_before": 3,
            "profile_record_count_after": 3,
            "profile_write_count": 0,
            "historical_answer_use_count": 0,
            "explicit_negative_answer_use_count": 0,
            "profile_snapshot_unchanged": True,
            "record_hashes_before": hashes,
            "record_hashes_after": hashes,
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 10,
            "new_pid": 20,
            "old_session_id": "first",
            "new_session_id": "second",
            "same_persistent_db": True,
        },
        "accounting": {
            key: value
            for key, value in contract["runtime_requirements"].items()
            if key != "storage"
        },
    }


def test_gate_accepts_complete_two_process_lifecycle():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_deleted_history_wrong_answer_and_retry():
    evidence = _passing_evidence()
    evidence["process_1"]["old_records_deleted_or_rewritten"] = True
    evidence["process_2"]["active_memory_id"] = "old"
    evidence["process_2"]["visible_surface"] += " 菊花茶"
    evidence["accounting"]["retry_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert "process_1_mismatch:old_records_deleted_or_rewritten" in result["failed_gates"]
    assert "recall_did_not_use_correction" in result["failed_gates"]
    assert "historical_value_leaked_to_surface" in result["failed_gates"]
    assert "accounting_mismatch:retry_count" in result["failed_gates"]


def test_contract_rejects_answer_leak_previous_value_and_second_execution():
    contract = gate.load_contract()
    leaked = deepcopy(contract)
    leaked["process_2"]["recall_input"] += " クロモジ茶"
    reused = deepcopy(contract)
    reused["forbidden_previous_values"].append("菊花茶")
    rerun = deepcopy(contract)
    rerun["failure_policy"]["exact_case_execution_count"] = 2
    for candidate, expected in (
        (leaked, "recall_answer_leak"),
        (reused, "previous_value_reused"),
        (rerun, "single_execution_not_frozen"),
    ):
        try:
            gate.validate_contract(candidate)
        except gate.P4PCorrectionLifecycleGateError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(expected)
