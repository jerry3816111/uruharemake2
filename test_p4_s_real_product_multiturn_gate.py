import copy
import json

import p4_s_real_product_multiturn_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    dataset = json.loads((gate.ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    turns = []
    for row in dataset["turns"]:
        recall = row["role"] in {"pre_correction_recall", "post_correction_recall"}
        expected_act = row.get("expected_act")
        turns.append(
            {
                "turn": row["turn"],
                "input": row["input"],
                "visible_output": row.get("expected_exact_surface") or "うん、そうなんだ。",
                "visible_output_language": "Japanese",
                "episode_id": f"episode-{row['turn']}",
                "graph_visible": True,
                "end_to_end_seconds": 1.0,
                "p4_i_selected": bool(expected_act),
                "p4_i_act": expected_act,
                "recall": recall,
            }
        )
    metrics = copy.deepcopy(contract["gates"])
    metrics["maximum_turn_latency_seconds"] = 1.0
    metrics["maximum_total_latency_seconds"] = 12.0
    accounting = copy.deepcopy(contract["accounting"])
    accounting["local_product_planner_model_calls_maximum"] = 7
    return {
        "schema": "uruha_p4_s_real_product_multiturn_evidence_v1",
        "case_id": contract["dataset"]["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": metrics,
        "restart": {
            "old_process_exit_observed": True,
            "old_listener_closed_before_new_process": True,
            "old_pid": 1,
            "new_pid": 2,
            "old_session_id": "old",
            "new_session_id": "new",
            "runtime_root_before": "/tmp/isolated",
            "runtime_root_after": "/tmp/isolated",
            "memory_db_before": "/tmp/isolated/memory_db",
            "memory_db_after": "/tmp/isolated/memory_db",
            "process_2_start_drink_active_values": ["松葉茶"],
            "process_2_start_game_active_values": ["ストラテジーゲーム"],
        },
        "final_state": {
            "drink_active_values": ["なた豆茶"],
            "drink_historical_values": ["松葉茶"],
            "drink_explicit_negative_values": ["松葉茶"],
            "game_active_values": ["ストラテジーゲーム"],
            "correction_previous_link_valid": True,
            "negative_correction_link_valid": True,
        },
        "accounting": accounting,
        "safari": {
            "actual_two_process_twelve_turn_acceptance": True,
            "closed_tab_count": 0,
        },
    }


def test_contract_binds_twelve_turn_two_process_novel_dataset():
    contract = gate.load_contract()
    assert contract["dataset"]["turn_count"] == 12
    assert contract["dataset"]["restart_after_turn"] == 6
    assert contract["runtime"]["listener"] == "127.0.0.1:7869"
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_passing_fixture_passes_all_frozen_gates():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_non_japanese_or_distractor_write_fails_closed():
    evidence = _passing_evidence()
    evidence["turns"][1]["visible_output_language"] = "Chinese"
    evidence["turns"][2]["p4_i_selected"] = True
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "turn_2_not_japanese" in result["failed_gates"]
    assert "turn_3_distractor_typed_write" in result["failed_gates"]


def test_restart_and_final_lineage_fail_closed():
    evidence = _passing_evidence()
    evidence["restart"]["new_pid"] = 1
    evidence["final_state"]["drink_active_values"] = ["松葉茶"]
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "pid_not_changed" in result["failed_gates"]
    assert "final_active_value_invalid" in result["failed_gates"]


def test_latency_and_model_call_ceilings_fail_closed():
    evidence = _passing_evidence()
    evidence["turns"][0]["end_to_end_seconds"] = 20.1
    evidence["metrics"]["maximum_turn_latency_seconds"] = 20.1
    evidence["accounting"]["local_product_planner_model_calls_maximum"] = 8
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "turn_1_latency_target_missed" in result["failed_gates"]
    assert "metric_ceiling_exceeded:maximum_turn_latency_seconds" in result["failed_gates"]
    assert "accounting_ceiling_exceeded:local_product_planner_model_calls_maximum" in result["failed_gates"]
