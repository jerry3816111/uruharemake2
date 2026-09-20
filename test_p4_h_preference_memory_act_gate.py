from copy import deepcopy

import pytest

import p4_h_preference_memory_act_gate as gate


def _passing_evidence():
    contract = gate.load_contract()
    common = contract["per_turn_requirements"]
    turns = []
    for index, expected in enumerate(contract["turns"], start=1):
        turns.append(
            {
                "turn_index": index,
                "input": expected["input"],
                "visible_output": expected["expected_visible_output"],
                "visible_output_language": common["visible_output_language"],
                "p4_h_status": common["p4_h_status"],
                "act": expected["expected_act"],
                "input_language": expected["expected_language"],
                "selected_intent": expected["expected_intent"],
                "plan_authority": True,
                "surface_authority": True,
                "planner_path": common["planner_path"],
                "planner_route": common["planner_route"],
                "product_planner_model_call_count": 0,
                "fallback_count": 0,
                "graph_node_visible": common["graph_node_visible"],
                "graph_node_stage": common["graph_node_stage"],
                "final_visible_surface_matches_contract": True,
                "durable_episode_write_count": 1,
                "episode_id": f"episode-{index}",
                "raw_dialogue_persisted_in_p4_h_trace": False,
                "end_to_end_seconds": 3.5,
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
            "local_product_planner_model_calls": 0,
            "fallback_count": 0,
            "paid_api_call_count": 0,
            "external_deployment_count": 0,
            "production_memory_access_count": 0,
            "function_tool_execution_count": 0,
            "vrm_action_execution_count": 0,
        },
        "safari": {"actual_two_turn_acceptance": True, "closed_tab_count": 0},
    }


def test_contract_is_new_and_not_the_p4_g_real_case():
    contract = gate.load_contract()
    inputs = [row["input"] for row in contract["turns"]]
    assert all("茉莉花茶" not in value and "ジャスミンティー" not in value for value in inputs)
    assert [(row["expected_language"], row["expected_act"]) for row in contract["turns"]] == [
        ("en", "write"),
        ("zh", "correction"),
    ]
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_gate_accepts_complete_bounded_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_evidence())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        (lambda row: row["turns"][0].update(visible_output="了解しました。"), "turn1_mismatch:visible_output"),
        (lambda row: row["turns"][1].update(selected_intent="ask_like_me"), "turn2_mismatch:selected_intent"),
        (lambda row: row["turns"][0].update(plan_authority=False), "turn1_mismatch:plan_authority"),
        (lambda row: row["turns"][1].update(graph_node_stage="surface"), "turn2_mismatch:graph_node_stage"),
        (lambda row: row["turns"][0].update(final_visible_surface_matches_contract=False), "turn1_mismatch:final_visible_surface_matches_contract"),
        (lambda row: row["turns"][1].update(end_to_end_seconds=20.1), "turn2_latency_target_missed"),
        (lambda row: row["accounting"].update(local_product_planner_model_calls=1), "model_call_ceiling_exceeded"),
        (lambda row: row["turns"][1].update(episode_id=row["turns"][0]["episode_id"]), "episode_ids_not_distinct"),
        (lambda row: row["safari"].update(closed_tab_count=1), "safari_tab_closed"),
    ],
)
def test_gate_fails_closed_for_missing_or_invalid_evidence(mutation, failure):
    evidence = deepcopy(_passing_evidence())
    mutation(evidence)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert failure in result["failed_gates"]
