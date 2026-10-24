from copy import deepcopy

import p4_l_cross_language_scope_delivery_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    first = contract["process_1"]
    second = contract["process_2"]
    common = contract["per_turn_requirements"]
    state = contract["persistent_state_requirements"]
    runtime = contract["runtime_requirements"]
    return {
        "runtime": {"fresh_isolated_root": True, "listener": runtime["listener"]},
        "process_1_turn": {
            "input": first["input"],
            "visible_output": first["expected_visible_output"],
            "visible_output_language": common["visible_output_language"],
            "act": first["expected_act"],
            "input_language": first["expected_language"],
            "scope": first["expected_scope"],
            "scope_source": first["expected_scope_source"],
            "current_value": first["expected_current_value"],
            "profile_likes": first["expected_profile_likes"],
            "profile_dislikes": first["expected_profile_dislikes"],
            "profile_write_count": first["expected_profile_write_count"],
            "p4_h_status": "explicit_preference_memory_act_committed",
            "p4_i_status": "typed_current_preference_written",
            "p4_l_status": first["expected_p4_l_status"],
            "p4_l_alias_id": first["expected_alias_id"],
            "p4_l_source_scope_alias_sha256": first["expected_source_scope_alias_sha256"],
            "p4_l_graph_label": "preference_scope_canonicalization_p4",
            "p4_l_graph_stage": "memory",
            "canonical_predicate": first["expected_canonical_predicate"],
            "p4_j_selected": False,
            "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0,
            "fallback_count": 0,
            "episode_id": "episode-1",
            "current_memory_id": "typed-1",
            "end_to_end_seconds": 1.0,
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 10,
            "new_pid": 11,
            "old_session_id": "session-1",
            "new_session_id": "session-2",
            "runtime_root_before": "/tmp/root",
            "runtime_root_after": "/tmp/root",
            "memory_db_before": "/tmp/root/memory_db",
            "memory_db_after": "/tmp/root/memory_db",
            "process_2_start_observed_first_active_id": "typed-1",
            "post_turn_memory_injection_count": 0,
        },
        "process_2_turn": {
            "input": second["input"],
            "visible_output": second["expected_visible_output"],
            "visible_output_language": common["visible_output_language"],
            "p4_j_status": second["expected_contract_status"],
            "p4_j_answer_use_authorized": second["expected_answer_use_authorized"],
            "query_language": second["expected_query_language"],
            "scope": second["expected_scope"],
            "localized_value_jp": second["expected_localized_value_jp"],
            "p4_j_graph_label": second["expected_p4_j_graph_label"],
            "p4_j_graph_stage": second["expected_p4_j_graph_stage"],
            "p4_j_final_surface_exact": True,
            "p4_j_raw_dialogue_persisted": False,
            "p4_h_selected": False,
            "p4_i_typed_write_count": 0,
            "p4_l_canonicalization_count": 0,
            "profile_write_count": 0,
            "historical_answer_use_count": 0,
            "explicit_negative_answer_use_count": 0,
            "episode_answer_use_count": 0,
            "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0,
            "fallback_count": 0,
            "episode_id": "episode-2",
            "active_memory_id": "typed-1",
            "end_to_end_seconds": 1.0,
        },
        "persistent_state": dict(state),
        "accounting": {
            key: runtime[key]
            for key in (
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
            )
        }
        | {"local_product_planner_model_calls": 0},
        "safari": {
            "actual_two_process_two_turn_acceptance": True,
            "closed_tab_count": 0,
            "p4_l_graph_node_visible_on_write": True,
            "p4_j_graph_node_visible_on_recall": True,
        },
    }


def test_gate_accepts_only_complete_frozen_evidence():
    contract = gate.load_contract()
    result = gate.evaluate_evidence(contract, _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_surface_graph_alias_and_profile_mutation_failures():
    contract = gate.load_contract()
    evidence = _passing_evidence()
    evidence["process_1_turn"]["p4_l_alias_id"] = "wrong"
    evidence["process_2_turn"]["visible_output"] = "wrong"
    evidence["persistent_state"]["typed_record_content_hash_unchanged"] = False
    evidence["safari"]["p4_l_graph_node_visible_on_write"] = False
    result = gate.evaluate_evidence(contract, evidence)
    assert result["status"] == "fail"
    assert "process_1_mismatch:p4_l_alias_id" in result["failed_gates"]
    assert "process_2_mismatch:visible_output" in result["failed_gates"]
    assert "persistent_state_mismatch:typed_record_content_hash_unchanged" in result["failed_gates"]
    assert "safari_p4_l_graph_missing" in result["failed_gates"]


def test_gate_rejects_retry_model_call_or_wrong_restart_identity():
    contract = gate.load_contract()
    evidence = _passing_evidence()
    evidence["accounting"]["retry_count"] = 1
    evidence["accounting"]["local_product_planner_model_calls"] = 1
    evidence["restart"]["new_pid"] = evidence["restart"]["old_pid"]
    evidence["restart"]["process_2_start_observed_first_active_id"] = "wrong"
    result = gate.evaluate_evidence(contract, evidence)
    assert result["status"] == "fail"
    assert "accounting_mismatch:retry_count" in result["failed_gates"]
    assert "accounting_model_call_ceiling_exceeded" in result["failed_gates"]
    assert "pid_not_changed" in result["failed_gates"]
    assert "process_2_start_did_not_observe_first_active_record" in result["failed_gates"]


def test_contract_forbids_answer_leak_and_old_case_reuse():
    contract = gate.load_contract()
    broken = deepcopy(contract)
    broken["process_2"]["input"] += " 麦茶"
    try:
        gate.validate_contract(broken)
    except gate.P4LScopeDeliveryGateError as exc:
        assert str(exc) == "recall_input_contains_answer"
    else:
        raise AssertionError("answer leakage must fail closed")
