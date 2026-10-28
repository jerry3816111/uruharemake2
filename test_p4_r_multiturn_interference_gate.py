import copy

import p4_r_multiturn_interference_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    return {
        "schema": "uruha_p4_r_multiturn_interference_evidence_v1",
        "case_id": contract["dataset"]["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turn_count": 12,
        "conditions": {
            "baseline": {
                "recalls": [
                    {"turn": 6, "selected_value": "紫蘇茶"},
                    {"turn": 12, "selected_value": "紫蘇茶"},
                ]
            },
            "system": {
                "recalls": [
                    {
                        "turn": 6,
                        "selected_value": "月桃茶",
                        "visible_surface": "今の飲み物の好みは月桃茶。前のじゃなくて、今の方ね。",
                        "status": "resolved_unique_active_typed_current_preference",
                        "answer_use_authorized": True,
                    },
                    {
                        "turn": 12,
                        "selected_value": "よもぎ茶",
                        "visible_surface": "今の飲み物の好みはよもぎ茶。前のじゃなくて、今の方ね。",
                        "status": "resolved_unique_active_typed_current_preference",
                        "answer_use_authorized": True,
                    },
                ]
            },
        },
        "metrics": copy.deepcopy(contract["gates"]),
        "final_state": {
            "drink_active_values": ["よもぎ茶"],
            "drink_historical_values": ["月桃茶"],
            "drink_explicit_negative_values": ["月桃茶"],
            "game_active_values": ["cooperative games"],
            "correction_previous_link_valid": True,
            "negative_correction_link_valid": True,
        },
        "accounting": copy.deepcopy(contract["execution"]),
    }


def test_contract_is_bound_to_ordered_novel_twelve_turn_dataset():
    contract = gate.load_contract()
    assert contract["dataset"]["turn_count"] == 12
    assert contract["dataset"]["recall_turns"] == [6, 12]
    assert contract["conditions"]["same_transcript"] is True
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_passing_fixture_passes_all_frozen_gates():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_wrong_system_value_fails_closed():
    evidence = _passing_evidence()
    evidence["conditions"]["system"]["recalls"][1]["selected_value"] = "月桃茶"
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert "system_turn_12_value_mismatch" in result["failed_gates"]


def test_cross_scope_leakage_fails_closed():
    evidence = _passing_evidence()
    evidence["final_state"]["game_active_values"] = []
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert "cross_scope_state_invalid" in result["failed_gates"]


def test_result_cannot_hide_baseline_or_accounting_drift():
    evidence = _passing_evidence()
    evidence["metrics"]["baseline_exact_recall_count"] = 1
    evidence["accounting"]["retry_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "metric_mismatch:baseline_exact_recall_count" in result["failed_gates"]
    assert "accounting_mismatch:retry_count" in result["failed_gates"]
