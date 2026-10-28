from copy import deepcopy

import pytest

import p4_i_current_preference_gate as gate


def _turn(expected, common, *, episode_id, current_id):
    row = {
        "input": expected["input"],
        "visible_output": expected["expected_visible_output"],
        "visible_output_language": common["visible_output_language"],
        "p4_h_status": common["p4_h_status"],
        "p4_h_plan_authority": True,
        "p4_h_surface_authority": True,
        "p4_h_graph_label": common["p4_h_graph_label"],
        "p4_h_graph_stage": common["p4_h_graph_stage"],
        "p4_h_final_surface_exact": True,
        "p4_i_status": common["p4_i_status"],
        "p4_i_graph_label": common["p4_i_graph_label"],
        "p4_i_graph_stage": common["p4_i_graph_stage"],
        "p4_i_raw_dialogue_persisted": False,
        "p4_i_answer_use_authorized": False,
        "act": expected["expected_act"],
        "input_language": expected["expected_language"],
        "scope": expected["expected_scope"],
        "current_value": expected["expected_current_value"],
        "profile_likes": expected["expected_profile_likes"],
        "profile_dislikes": expected["expected_profile_dislikes"],
        "profile_write_count": expected["expected_profile_write_count"],
        "durable_episode_write_count": 1,
        "product_planner_model_call_count": 0,
        "fallback_count": 0,
        "episode_id": episode_id,
        "current_memory_id": current_id,
        "active_current_ids": [current_id],
        "historical_current_ids": [],
        "end_to_end_seconds": 3.0,
    }
    return row


def _passing_evidence():
    contract = gate.load_contract()
    common = contract["per_turn_requirements"]
    first = _turn(contract["process_1"], common, episode_id="episode-1", current_id="current-1")
    second = _turn(contract["process_2"], common, episode_id="episode-2", current_id="current-2")
    second.update(
        previous_value=contract["process_2"]["expected_previous_value"],
        scope_source=contract["process_2"]["expected_scope_source"],
        previous_current_memory_id="current-1",
        negative_old_memory_id="negative-1",
        historical_current_ids=["current-1"],
        history_preserved=True,
    )
    return {
        "runtime": {"fresh_isolated_root": True, "listener": "127.0.0.1:7861"},
        "process_1_turn": first,
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 100,
            "new_pid": 200,
            "old_session_id": "session-1",
            "new_session_id": "session-2",
            "runtime_root_before": "/tmp/p4i",
            "runtime_root_after": "/tmp/p4i",
            "memory_db_before": "/tmp/p4i/memory_db",
            "memory_db_after": "/tmp/p4i/memory_db",
            "process_2_start_observed_first_active_id": "current-1",
            "post_turn_memory_injection_count": 0,
        },
        "process_2_turn": second,
        "persistent_state": {
            "total_profile_record_count": 3,
            "total_episode_record_count": 2,
            "old_positive_record_present": True,
            "old_positive_state": "historical",
            "new_positive_state": "active",
            "negative_old_record_present": True,
            "negative_old_record_state": "active",
            "old_and_new_positive_predicate_match": True,
            "old_records_deleted_or_rewritten": False,
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
            "p4_i_graph_node_visible_both_turns": True,
        },
    }


def test_frozen_contract_is_new_multilingual_cross_restart_case():
    contract = gate.load_contract()
    assert contract["process_1"]["expected_language"] == "en"
    assert contract["process_2"]["expected_language"] == "zh"
    assert "sparkling water" not in contract["process_1"]["input"].casefold()
    assert "氣泡水" not in contract["process_2"]["input"]
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_gate_accepts_complete_cross_restart_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        (lambda row: row["process_1_turn"].update(current_value="wrong"), "process_1_mismatch:current_value"),
        (lambda row: row["restart"].update(new_pid=100), "pid_not_changed"),
        (lambda row: row["restart"].update(process_2_start_observed_first_active_id=None), "process_2_did_not_observe_first_active_record"),
        (lambda row: row["process_2_turn"].update(previous_current_memory_id="wrong"), "correction_link_not_first_current_memory"),
        (lambda row: row["process_2_turn"].update(historical_current_ids=[]), "process_2_historical_current_count_mismatch"),
        (lambda row: row["persistent_state"].update(old_positive_state="active"), "persistent_state_mismatch:old_positive_state"),
        (lambda row: row["accounting"].update(local_product_planner_model_calls=1), "accounting_model_call_ceiling_exceeded"),
        (lambda row: row["safari"].update(closed_tab_count=1), "safari_tab_closed"),
    ],
)
def test_gate_fails_closed_for_invalid_evidence(mutation, failure):
    evidence = deepcopy(_passing_evidence())
    mutation(evidence)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert failure in result["failed_gates"]
