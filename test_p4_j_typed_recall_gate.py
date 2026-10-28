from copy import deepcopy

import p4_j_typed_recall_gate as gate


def _valid_evidence():
    contract = gate.load_contract()
    first = contract["process_1"]
    second = contract["process_2"]
    first_trace = contract["process_1_trace_requirements"]
    second_trace = contract["process_2_trace_requirements"]
    evidence = {
        "runtime": {"fresh_isolated_root": True, "listener": "127.0.0.1:7862"},
        "process_1_turn": {
            "input": first["input"],
            "visible_output": first["expected_visible_output"],
            "visible_output_language": "Japanese",
            "act": first["expected_act"],
            "input_language": first["expected_language"],
            "scope": first["expected_scope"],
            "current_value": first["expected_current_value"],
            "profile_likes": first["expected_profile_likes"],
            "profile_dislikes": first["expected_profile_dislikes"],
            "profile_write_count": first["expected_profile_write_count"],
            "p4_h_status": first_trace["p4_h_status"],
            "p4_h_graph_label": first_trace["p4_h_graph_label"],
            "p4_h_graph_stage": first_trace["p4_h_graph_stage"],
            "p4_i_status": first_trace["p4_i_status"],
            "p4_i_graph_label": first_trace["p4_i_graph_label"],
            "p4_i_graph_stage": first_trace["p4_i_graph_stage"],
            "p4_j_selected": first_trace["p4_j_selected"],
            "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0,
            "fallback_count": 0,
            "episode_id": "episode-1",
            "current_memory_id": "current-1",
            "end_to_end_seconds": 1.0,
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 1,
            "new_pid": 2,
            "old_session_id": "session-1",
            "new_session_id": "session-2",
            "runtime_root_before": "/isolated",
            "runtime_root_after": "/isolated",
            "memory_db_before": "/isolated/db",
            "memory_db_after": "/isolated/db",
            "process_2_start_observed_first_active_id": "current-1",
            "post_turn_memory_injection_count": 0,
        },
        "process_2_turn": {
            "input": second["input"],
            "visible_output": second["expected_visible_output"],
            "visible_output_language": "Japanese",
            "p4_j_status": second["expected_contract_status"],
            "p4_j_answer_use_authorized": second["expected_answer_use_authorized"],
            "query_language": second["expected_query_language"],
            "scope": second["expected_scope"],
            "localized_value_jp": second["expected_localized_value_jp"],
            "p4_j_graph_label": second_trace["p4_j_graph_label"],
            "p4_j_graph_stage": second_trace["p4_j_graph_stage"],
            "p4_j_final_surface_exact": second_trace["p4_j_final_surface_exact"],
            "p4_j_raw_dialogue_persisted": second_trace["p4_j_raw_dialogue_persisted"],
            "p4_h_selected": second_trace["p4_h_selected"],
            "p4_i_typed_write_count": second_trace["p4_i_typed_write_count"],
            "profile_write_count": second["profile_write_count"],
            "historical_answer_use_count": second["historical_answer_use_count"],
            "explicit_negative_answer_use_count": second[
                "explicit_negative_answer_use_count"
            ],
            "episode_answer_use_count": second["episode_answer_use_count"],
            "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0,
            "fallback_count": 0,
            "episode_id": "episode-2",
            "active_memory_id": "current-1",
            "end_to_end_seconds": 1.0,
        },
        "persistent_state": deepcopy(contract["persistent_state_requirements"]),
        "accounting": {
            **{
                key: value
                for key, value in contract["runtime_requirements"].items()
                if key
                in {
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
                }
            },
            "local_product_planner_model_calls": 0,
        },
        "safari": {
            "actual_two_process_two_turn_acceptance": True,
            "closed_tab_count": 0,
            "p4_j_graph_node_visible_on_recall": True,
        },
    }
    return contract, evidence


def test_valid_evidence_passes_the_frozen_gate():
    contract, evidence = _valid_evidence()
    result = gate.evaluate_evidence(contract, evidence)
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_each_causal_failure_is_visible():
    mutations = (
        (lambda row: row["process_2_turn"].update(active_memory_id="wrong"), "process_2_did_not_use_process_1_typed_record"),
        (lambda row: row["process_2_turn"].update(profile_write_count=1), "process_2_mismatch:profile_write_count"),
        (lambda row: row["persistent_state"].update(typed_record_content_hash_unchanged=False), "persistent_state_mismatch:typed_record_content_hash_unchanged"),
        (lambda row: row["restart"].update(new_pid=1), "pid_not_changed"),
        (lambda row: row["accounting"].update(retry_count=1), "accounting_mismatch:retry_count"),
        (lambda row: row["safari"].update(p4_j_graph_node_visible_on_recall=False), "safari_p4_j_graph_missing"),
    )
    contract, base = _valid_evidence()
    for mutate, expected in mutations:
        evidence = deepcopy(base)
        mutate(evidence)
        result = gate.evaluate_evidence(contract, evidence)
        assert result["status"] == "fail"
        assert expected in result["failed_gates"]


def test_contract_rejects_answer_leak_and_retry_permission():
    contract = gate.load_contract()
    leaked = deepcopy(contract)
    leaked["process_2"]["input"] = "我現在喜歡ルイボスティー嗎？"
    try:
        gate.validate_contract(leaked)
    except gate.P4JTypedRecallGateError as exc:
        assert str(exc) == "recall_input_contains_answer"
    else:
        raise AssertionError("answer-bearing recall input must fail")

    retry = deepcopy(contract)
    retry["runtime_requirements"]["retry_count"] = 1
    try:
        gate.validate_contract(retry)
    except gate.P4JTypedRecallGateError as exc:
        assert str(exc) == "retry_not_forbidden"
    else:
        raise AssertionError("retry permission must fail")
