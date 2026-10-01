from copy import deepcopy

import pytest

import p4_f_preference_supersession_gate as gate


def _passing_evidence(contract):
    old_id = "old-episode"
    correction_id = "correction-episode"
    return {
        "runtime": {"production_memory_access_count": 0},
        "session_1_old_turn": {
            "input": contract["session_1"]["old_preference_input"],
            "visible_output_language": "Japanese",
            "episode_id": old_id,
            "durable_episode_write_count": 1,
        },
        "session_1_correction_turn": {
            "input": contract["session_1"]["correction_input"],
            "visible_output_language": "Japanese",
            "episode_id": correction_id,
            "durable_episode_write_count": 1,
        },
        "restart": {
            "old_process_exit_observed": True,
            "old_pid": 101,
            "new_pid": 202,
            "old_session_id": "old-session",
            "new_session_id": "new-session",
            "runtime_root_before": "/tmp/isolated",
            "runtime_root_after": "/tmp/isolated",
            "memory_db_before": "/tmp/isolated/memory_db",
            "memory_db_after": "/tmp/isolated/memory_db",
            "post_turn_memory_injection_count": 0,
        },
        "session_2_recall_turn": {
            "input": contract["session_2"]["recall_input"],
            "visible_output": contract["session_2"]["expected_visible_output"],
            "visible_output_language": "Japanese",
            "contract_status": "resolved_explicit_preference_supersession",
            "selected_speaker": "user",
            "candidate_count": 1,
            "current_value_jp": "紅茶",
            "revoked_value_jp": "ハーブティー",
            "current_value_digest": "current-digest",
            "revoked_value_digest": "revoked-digest",
            "planner_path": "speaker_qualified_selected_fact_p3",
            "graph_node_visible": "speaker_qualified_fact_p3",
            "product_planner_model_call_count": 0,
            "fact_memory_write_count": 0,
            "database_rewrite_count": 0,
            "raw_dialogue_persisted_in_trace": False,
            "visible_surface_matches_contract": True,
        },
        "history_integrity": {
            "old_episode_present_after_restart": True,
            "correction_episode_present_after_restart": True,
            "historical_memory_id": old_id,
            "correction_memory_id": correction_id,
            "historical_trace_id": f"stored:episode:{old_id}",
            "correction_trace_id": f"stored:episode:{correction_id}",
            "both_sources_predate_new_process": True,
            "history_preserved": True,
        },
        "accounting": {
            **deepcopy(contract["execution_ceiling"]),
            "local_product_planner_model_calls": 2,
        },
    }


def test_contract_freezes_exact_three_turn_no_answer_leak_restart_case():
    contract = gate.load_contract()
    assert contract["session_1"]["correction_input"] == (
        "Correction: I do not prefer herbal tea anymore. I prefer black tea now."
    )
    assert "black tea" not in contract["session_2"]["recall_input"].casefold()
    assert contract["execution_ceiling"]["real_product_turns"] == 3
    assert contract["execution_ceiling"]["retry_count"] == 0
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_exact_passing_evidence_passes():
    contract = gate.load_contract()
    result = gate.evaluate_evidence(contract, _passing_evidence(contract))
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


@pytest.mark.parametrize(
    ("path", "value", "failed_gate"),
    [
        (("session_2_recall_turn", "visible_output"), "ハーブティー。", "recall_mismatch:visible_output"),
        (("session_2_recall_turn", "contract_status"), "ambiguous_multiple_user_preferences", "recall_mismatch:contract_status"),
        (("session_2_recall_turn", "current_value_digest"), "revoked-digest", "current_and_revoked_digests_not_distinct"),
        (("history_integrity", "old_episode_present_after_restart"), False, "old_episode_not_preserved"),
        (("history_integrity", "historical_memory_id"), "correction-episode", "historical_memory_id_not_old_episode"),
        (("restart", "new_pid"), 101, "pid_not_changed"),
        (("restart", "runtime_root_after"), "/tmp/other", "runtime_root_changed"),
        (("accounting", "retry_count"), 1, "accounting_mismatch:retry_count"),
        (("accounting", "local_product_planner_model_calls"), 3, "accounting_model_call_ceiling_exceeded"),
    ],
)
def test_fail_closed_counterexamples(path, value, failed_gate):
    contract = gate.load_contract()
    evidence = _passing_evidence(contract)
    evidence[path[0]][path[1]] = value
    result = gate.evaluate_evidence(contract, evidence)
    assert result["status"] == "fail"
    assert failed_gate in result["failed_gates"]


def test_contract_rejects_answer_leak_post_turn_seed_and_missing_history_requirement():
    contract = gate.load_contract()
    leaked = deepcopy(contract)
    leaked["session_2"]["recall_input"] += " black tea"
    with pytest.raises(gate.P4FPreferenceSupersessionError, match="recall_prompt_contains_answer_value"):
        gate.validate_contract(leaked)
    seeded = deepcopy(contract)
    seeded["restart"]["server_side_injection_or_seed_after_session_1_allowed"] = True
    with pytest.raises(gate.P4FPreferenceSupersessionError, match="post_turn_seed_not_forbidden"):
        gate.validate_contract(seeded)
    missing = deepcopy(contract)
    missing["history_integrity"]["old_episode_present_after_restart"] = False
    with pytest.raises(gate.P4FPreferenceSupersessionError, match="history_integrity_requirement_missing"):
        gate.validate_contract(missing)
