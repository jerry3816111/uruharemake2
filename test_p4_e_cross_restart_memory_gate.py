from copy import deepcopy

import pytest

import p4_e_cross_restart_memory_gate as gate


def _passing_evidence(contract):
    return {
        "runtime": {"production_memory_access_count": 0},
        "session_1_turn": {
            "input": contract["session_1"]["input"],
            "visible_output_language": "Japanese",
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 101,
            "new_pid": 202,
            "old_session_id": "old",
            "new_session_id": "new",
            "runtime_root_before": "/tmp/isolated",
            "runtime_root_after": "/tmp/isolated",
            "memory_db_before": "/tmp/isolated/memory_db",
            "memory_db_after": "/tmp/isolated/memory_db",
            "post_turn_memory_injection_count": 0,
        },
        "session_2_turn": {
            "input": contract["session_2"]["input"],
            "visible_output": contract["session_2"]["expected_visible_output"],
            "visible_output_language": "Japanese",
            "contract_status": "resolved_unique_user_preference",
            "selected_speaker": "user",
            "candidate_count": 1,
            "planner_path": "speaker_qualified_selected_fact_p3",
            "retrieved_trace_id": "stored:episode:abc",
            "retrieved_memory_id": "abc",
            "retrieved_source_predates_new_session": True,
            "graph_node_visible": "speaker_qualified_fact_p3",
            "product_planner_model_call_count": 0,
        },
        "vrm_restart_boundary": {
            "stage_after_new_page_load": "waiting_for_local_vrm",
            "server_persisted_previous_local_file": False,
        },
        "accounting": deepcopy(contract["execution_ceiling"]),
    }


def test_frozen_contract_has_answer_absent_recall_and_real_restart_requirements():
    contract = gate.load_contract()
    assert "herbal" not in contract["session_2"]["input"].casefold()
    assert contract["session_2"]["maximum_product_planner_model_calls"] == 0
    assert contract["restart"]["new_pid_required"] is True
    assert contract["restart"]["same_runtime_root_required"] is True
    assert contract["restart"]["production_memory_access_allowed"] is False


def test_exact_passing_evidence_passes_without_interpretation():
    contract = gate.load_contract()
    result = gate.evaluate_evidence(contract, _passing_evidence(contract))
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


@pytest.mark.parametrize(
    ("path", "value", "failed_gate"),
    [
        (("restart", "new_pid"), 101, "pid_not_changed"),
        (("restart", "runtime_root_after"), "/tmp/other", "runtime_root_changed"),
        (("session_2_turn", "visible_output"), "ブラックコーヒー。", "recall_visible_output_mismatch"),
        (("session_2_turn", "selected_speaker"), "colleague_Rina", "selected_speaker_mismatch"),
        (("session_2_turn", "retrieved_memory_id"), None, "retrieved_memory_id_missing"),
        (("session_2_turn", "product_planner_model_call_count"), 1, "recall_product_planner_model_call_nonzero"),
        (("vrm_restart_boundary", "stage_after_new_page_load"), "rendering_vrm", "vrm_stage_persisted_across_restart"),
        (("accounting", "retry_count"), 1, "accounting_mismatch:retry_count"),
    ],
)
def test_fail_closed_counterexamples(path, value, failed_gate):
    contract = gate.load_contract()
    evidence = _passing_evidence(contract)
    evidence[path[0]][path[1]] = value
    result = gate.evaluate_evidence(contract, evidence)
    assert result["status"] == "fail"
    assert failed_gate in result["failed_gates"]


def test_contract_rejects_answer_leak_and_post_turn_seed_permission():
    contract = gate.load_contract()
    leaked = deepcopy(contract)
    leaked["session_2"]["input"] += " herbal"
    with pytest.raises(gate.P4ECrossRestartMemoryError, match="recall_prompt_contains_answer_value"):
        gate.validate_contract(leaked)
    seeded = deepcopy(contract)
    seeded["restart"]["server_side_injection_or_seed_after_session_1_allowed"] = True
    with pytest.raises(gate.P4ECrossRestartMemoryError, match="post_turn_seed_not_forbidden"):
        gate.validate_contract(seeded)
