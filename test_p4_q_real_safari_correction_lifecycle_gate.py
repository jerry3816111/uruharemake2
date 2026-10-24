from copy import deepcopy

import p4_q_real_safari_correction_lifecycle_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    write = contract["session_1_write_turn"]
    correction = contract["session_1_correction_turn"]
    recall = contract["session_2_recall_turn"]
    runtime = contract["runtime_requirements"]
    return {
        "session_1_write_turn": {
            "input": write["input"], "visible_output": write["expected_visible_output"],
            "visible_output_language": "Japanese", "act": "write", "input_language": "zh",
            "scope": "drink", "scope_source": "canonical_alias_projection",
            "current_value": write["expected_current_value"], "p4_l_alias_id": write["expected_alias_id"],
            "p4_i_status": "typed_current_preference_written", "p4_l_status": "canonical_scope_projected",
            "durable_episode_write_count": 1, "product_planner_model_call_count": 0, "fallback_count": 0,
            "episode_id": "episode-write", "current_memory_id": "old", "end_to_end_seconds": 1.0,
        },
        "session_1_correction_turn": {
            "input": correction["input"], "visible_output": correction["expected_visible_output"],
            "visible_output_language": "Japanese", "act": "correction", "input_language": "ja",
            "scope": "drink", "scope_source": "canonical_alias_projection",
            "previous_value": correction["expected_previous_value"], "current_value": correction["expected_current_value"],
            "p4_l_alias_id": correction["expected_alias_id"], "profile_likes": ["びわ茶"],
            "profile_dislikes": ["蓮花茶"], "profile_write_count": 2, "active_current_count": 1,
            "historical_current_count": 1, "explicit_negative_count": 1, "history_preserved": True,
            "p4_i_status": "typed_current_preference_written", "p4_l_status": "canonical_scope_projected",
            "durable_episode_write_count": 1, "product_planner_model_call_count": 0, "fallback_count": 0,
            "episode_id": "episode-correction", "current_memory_id": "new",
            "previous_current_memory_id": "old", "negative_old_memory_id": "negative",
            "active_current_ids": ["new"], "historical_current_ids": ["old"], "end_to_end_seconds": 1.0,
        },
        "session_2_recall_turn": {
            "input": recall["input"], "visible_output": recall["expected_visible_output"],
            "visible_output_language": "Japanese", "p4_j_status": recall["expected_contract_status"],
            "p4_j_answer_use_authorized": True, "query_language": "en", "scope": "drink",
            "localized_value_jp": "びわ茶", "value_surface_strategy": "bounded_japanese_identity",
            "identity_localization_applied": True, "p4_n_status": "bounded_japanese_identity_authorized",
            "p4_j_graph_label": "typed_current_preference_recall_p4", "p4_j_graph_stage": "select",
            "p4_j_final_surface_exact": True, "p4_j_raw_dialogue_persisted": False,
            "p4_i_typed_write_count": 0, "p4_l_canonicalization_count": 0, "profile_write_count": 0,
            "historical_answer_use_count": 0, "explicit_negative_answer_use_count": 0,
            "episode_answer_use_count": 0, "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0, "fallback_count": 0, "episode_id": "episode-recall",
            "active_memory_id": "new", "answer_memory_ids": ["new"], "end_to_end_seconds": 1.0,
        },
        "restart": {
            "old_process_exit_observed": True, "old_listener_closed_before_new_process": True,
            "old_pid": 1, "new_pid": 2, "old_session_id": "one", "new_session_id": "two",
            "runtime_root_before": "/tmp/root", "runtime_root_after": "/tmp/root",
            "memory_db_before": "/tmp/root/db", "memory_db_after": "/tmp/root/db",
            "process_2_start_active_id": "new", "process_2_start_historical_ids": ["old"],
            "process_2_start_negative_ids": ["negative"],
        },
        "persistent_state": dict(contract["persistent_state_requirements"]),
        "runtime": {
            "fresh_isolated_root": True, "runtime_root_mode": "0700", "listener": runtime["listener"],
            "product_entry": runtime["product_entry"], "installed_builder_module": runtime["installed_builder_module"],
        },
        "accounting": {key: runtime[key] for key in (
            "process_starts", "process_restart_count", "real_product_turns", "retry_count", "fallback_count",
            "paid_api_call_count", "external_deployment_count", "production_memory_access_count",
            "function_tool_execution_count", "vrm_action_execution_count",
        )} | {"local_product_planner_model_calls": 0},
        "safari": {
            "actual_two_process_three_turn_acceptance": True, "closed_tab_count": 0,
            "p4_l_graph_node_visible_on_write_and_correction": True,
            "p4_j_graph_node_visible_on_recall": True, "bounded_japanese_identity_visible_in_graph": True,
        },
    }


def test_gate_accepts_complete_three_turn_two_process_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_wrong_lineage_old_value_leak_and_retry():
    evidence = _passing_evidence()
    evidence["session_1_correction_turn"]["previous_current_memory_id"] = "wrong"
    evidence["session_2_recall_turn"]["visible_output"] += " 蓮花茶"
    evidence["accounting"]["retry_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert "correction_not_linked_to_write" in result["failed_gates"]
    assert "historical_value_leaked_to_surface" in result["failed_gates"]
    assert "accounting_mismatch:retry_count" in result["failed_gates"]


def test_contract_rejects_answer_leak_and_second_execution_shape():
    contract = gate.load_contract()
    leaked = deepcopy(contract)
    leaked["session_2_recall_turn"]["input"] += " びわ茶"
    wrong = deepcopy(contract)
    wrong["runtime_requirements"]["real_product_turns"] = 2
    for candidate, expected in ((leaked, "recall_answer_leak"), (wrong, "execution_count_invalid")):
        try:
            gate.validate_contract(candidate)
        except gate.P4QRealGateError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(expected)
