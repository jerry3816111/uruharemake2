from copy import deepcopy

import p4_o_real_persisted_reference_time_delivery_gate as gate


def _passing():
    contract = gate.load_contract()
    return {
        "runtime": {
            "fresh_isolated_root": True,
            "runtime_root_mode": "0700",
            "listener": "127.0.0.1:7867",
            "product_entry": "uruha_web_ui_product_p4_o.py",
            "installed_builder_module": "uruha_persisted_reference_time_p4",
        },
        "process_1_turn": {
            "input": contract["process_1"]["input"],
            "visible_output": contract["process_1"]["expected_visible_output"],
            "visible_output_language": "Japanese",
            "act": "write",
            "input_language": "ja",
            "scope": "drink",
            "scope_source": "canonical_alias_projection",
            "current_value": "たんぽぽ茶",
            "profile_likes": ["たんぽぽ茶"],
            "profile_dislikes": [],
            "profile_write_count": 1,
            "p4_i_status": "typed_current_preference_written",
            "p4_l_status": "canonical_scope_projected",
            "p4_l_alias_id": "drink:ja:v1",
            "durable_episode_write_count": 1,
            "product_planner_model_call_count": 0,
            "fallback_count": 0,
            "episode_id": "episode-1",
            "current_memory_id": "current-1",
            "end_to_end_seconds": 1.0,
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_listener_closed_before_new_process": True,
            "old_pid": 1,
            "new_pid": 2,
            "old_session_id": "session-1",
            "new_session_id": "session-2",
            "runtime_root_before": "/tmp/root",
            "runtime_root_after": "/tmp/root",
            "memory_db_before": "/tmp/root/db",
            "memory_db_after": "/tmp/root/db",
            "process_2_start_observed_first_active_id": "current-1",
            "post_turn_memory_injection_count": 0,
        },
        "process_2_turn": {
            "input": contract["process_2"]["input"],
            "visible_output": contract["process_2"]["expected_visible_output"],
            "visible_output_language": "Japanese",
            "p4_j_status": "resolved_unique_active_typed_current_preference",
            "p4_j_answer_use_authorized": True,
            "query_language": "en",
            "scope": "drink",
            "localized_value_jp": "たんぽぽ茶",
            "value_surface_strategy": "bounded_japanese_identity",
            "identity_localization_applied": True,
            "p4_n_status": "bounded_japanese_identity_authorized",
            "p4_j_graph_label": "typed_current_preference_recall_p4",
            "p4_j_graph_stage": "select",
            "p4_j_final_surface_exact": True,
            "p4_j_raw_dialogue_persisted": False,
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
            "active_memory_id": "current-1",
            "end_to_end_seconds": 1.0,
        },
        "persistent_state": {
            "profile_record_count_before_recall": 1,
            "profile_record_count_after_recall": 1,
            "episode_record_count_before_recall": 1,
            "episode_record_count_after_recall": 2,
            "active_current_count_before_recall": 1,
            "active_current_count_after_recall": 1,
            "historical_current_count_after_recall": 0,
            "current_memory_id_unchanged": True,
            "typed_record_content_hash_unchanged": True,
            "source_language_persisted_as_ja": True,
            "source_provenance_hashes_unchanged": True,
        },
        "accounting": {
            "process_starts": 2,
            "process_restart_count": 1,
            "real_product_turns": 2,
            "retry_count": 0,
            "fallback_count": 0,
            "local_product_planner_model_calls": 0,
            "paid_api_call_count": 0,
            "external_deployment_count": 0,
            "production_memory_access_count": 0,
            "function_tool_execution_count": 0,
            "vrm_action_execution_count": 0,
        },
        "safari": {
            "actual_two_process_two_turn_acceptance": True,
            "closed_tab_count": 0,
            "p4_j_graph_node_visible_on_recall": True,
            "bounded_japanese_identity_visible_in_graph": True,
        },
    }


def test_contract_freezes_new_answer_absent_value_and_p4_o_entry():
    contract = gate.load_contract()
    assert contract["novelty_requirements"]["repository_occurrences_before_freeze"] == 0
    assert "たんぽぽ茶" in contract["process_1"]["input"]
    assert "たんぽぽ茶" not in contract["process_2"]["input"]
    assert contract["runtime_requirements"]["product_entry"] == "uruha_web_ui_product_p4_o.py"
    assert contract["runtime_requirements"]["retry_count"] == 0


def test_complete_evidence_passes():
    result = gate.evaluate_evidence(gate.load_contract(), _passing())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_wrong_entry_builder_strategy_provenance_or_retry_fails_closed():
    evidence = deepcopy(_passing())
    evidence["runtime"]["product_entry"] = "uruha_web_ui_product.py"
    evidence["runtime"]["installed_builder_module"] = "uruha_source_bound_japanese_value_surface_p4"
    evidence["process_2_turn"]["value_surface_strategy"] = "finite_localization_map"
    evidence["persistent_state"]["source_provenance_hashes_unchanged"] = False
    evidence["accounting"]["retry_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert "runtime_mismatch:product_entry" in result["failed_gates"]
    assert "runtime_mismatch:installed_builder_module" in result["failed_gates"]
    assert "process_2_mismatch:value_surface_strategy" in result["failed_gates"]
    assert "persistent_state_mismatch:source_provenance_hashes_unchanged" in result["failed_gates"]
    assert "accounting_mismatch:retry_count" in result["failed_gates"]
