from copy import deepcopy

import p4_q_correction_lifecycle_protocol_repair_gate as gate


def test_contract_freezes_elapsed_order_and_new_values():
    contract = gate.load_contract()
    pair = contract["development_pair"]
    assert pair == {
        "old_value": "洛神花茶",
        "new_value": "はと麦茶",
        "old_value_previous_repository_occurrences": 0,
        "new_value_previous_repository_occurrences": 0,
    }
    assert contract["process_1"]["write_timestamp"] < contract["process_1"][
        "correction_timestamp"
    ] < contract["protocol_time_boundary"]["p4_p_post_execution_clock_observation"]
    assert contract["failure_policy"]["p4_p_case_rerun_allowed"] is False


def test_p4_q_reuses_p4_p_gate_semantics_and_fails_closed_on_empty_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), {})
    assert result["status"] == "fail"
    assert result["schema"] == "uruha_p4_q_correction_lifecycle_protocol_repair_gate_result_v1"
    assert "process_1_mismatch:write_status" in result["failed_gates"]
    assert "old_process_exit_not_observed" in result["failed_gates"]


def test_contract_rejects_future_boundary_and_p4_p_rerun():
    contract = gate.load_contract()
    future = deepcopy(contract)
    future["process_1"]["correction_timestamp"] = "2026-09-22T08:01:00+08:00"
    rerun = deepcopy(contract)
    rerun["failure_policy"]["p4_p_case_rerun_allowed"] = True
    for candidate, expected in (
        (future, "timestamps_not_strictly_elapsed"),
        (rerun, "p4_p_rerun_not_forbidden"),
    ):
        try:
            gate.validate_contract(candidate)
        except gate.P4QProtocolRepairGateError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(expected)
