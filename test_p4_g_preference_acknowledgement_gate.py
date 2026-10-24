from copy import deepcopy

import pytest

import p4_g_preference_acknowledgement_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    turns = []
    for index, expected in enumerate(contract["turns"], start=1):
        turns.append(
            {
                "turn_index": index,
                "input": expected["input"],
                "visible_output": expected["expected_visible_output"],
                "visible_output_language": "Japanese",
                "p4_g_status": "casual_acknowledgement_committed",
                "act": expected["expected_act"],
                "input_language": expected["expected_language"],
                "surface_authority": True,
                "surface_changed": True,
                "language_guard_repair_action": "explicit_preference_acknowledgement_p4",
                "graph_node_visible": "explicit_preference_acknowledgement_p4",
                "durable_episode_write_count": 1,
                "episode_id": f"episode-{index}",
                "product_planner_model_call_count": 1,
                "fallback_count": 0,
                "raw_dialogue_persisted_in_p4_g_trace": False,
            }
        )
    return {
        "runtime": {
            "fresh_isolated_root": True,
            "listener": "127.0.0.1:7860",
            "production_memory_access_count": 0,
        },
        "turns": turns,
        "accounting": {
            "real_product_turns": 2,
            "process_starts": 1,
            "retry_count": 0,
            "local_product_planner_model_calls": 2,
            "fallback_count": 0,
            "paid_api_call_count": 0,
            "external_deployment_count": 0,
            "production_memory_access_count": 0,
            "function_tool_execution_count": 0,
            "vrm_action_execution_count": 0,
        },
        "safari": {
            "actual_two_turn_acceptance": True,
            "closed_tab_count": 0,
        },
    }


def test_contract_is_new_multilingual_case_and_not_p4_f_replay():
    contract = gate.load_contract()
    assert [(row["expected_language"], row["expected_act"]) for row in contract["turns"]] == [
        ("zh", "write"),
        ("ja", "correction"),
    ]
    assert all("herbal tea" not in row["input"].casefold() for row in contract["turns"])
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_gate_accepts_complete_bounded_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        (lambda row: row["turns"][0].update(visible_output="了解しました。"), "turn1_mismatch:visible_output"),
        (lambda row: row["turns"][1].update(surface_authority=False), "turn2_mismatch:surface_authority"),
        (lambda row: row["turns"][1].update(episode_id=row["turns"][0]["episode_id"]), "episode_ids_not_distinct"),
        (lambda row: row["accounting"].update(retry_count=1), "accounting_mismatch:retry_count"),
        (lambda row: row["safari"].update(closed_tab_count=1), "safari_tab_closed"),
    ],
)
def test_gate_fails_closed_for_missing_or_invalid_evidence(mutation, failure):
    evidence = deepcopy(_passing_evidence())
    mutation(evidence)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert failure in result["failed_gates"]
