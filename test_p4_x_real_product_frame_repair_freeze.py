import copy
import hashlib
from pathlib import Path

import p4_x_real_product_frame_repair_gate as gate


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = []
    for row in dataset["turns"]:
        repaired = row["turn"] == 1
        turns.append(
            {
                "turn": row["turn"],
                "input": row["input"],
                "visible_output": "そういう話ね。",
                "visible_output_language": "Japanese",
                "episode_id": f"episode-{row['turn']}",
                "graph_visible": True,
                "p4_t_present": True,
                "p4_v_present": True,
                "p4_v_violations": ["quoted_content_promoted_to_assertion"] if repaired else [],
                "p4_w_present": True,
                "p4_w_changed": repaired,
                "p4_w_after_violations": [],
                "branch_consistent": True,
                "visible_matches_after_digest": True,
                "p4_i_selected": False,
                "end_to_end_seconds": 1.0,
            }
        )
    return {
        "schema": "uruha_p4_x_real_product_frame_repair_evidence_v1",
        "case_id": contract["dataset"]["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": {
            **contract["gates"],
            "minimum_natural_repair_trigger_count": 1,
            "maximum_turn_latency_seconds": 1.0,
            "maximum_total_latency_seconds": 4.0,
        },
        "accounting": {**contract["accounting"], "local_semantic_authorization_model_calls_maximum": 4},
        "safari": {
            "actual_four_turn_acceptance": True,
            "runtime_node_graph_observed_after_every_turn": True,
            "closed_tab_count": 0,
        },
    }


def test_contract_binds_new_prompts_entries_and_isolated_port():
    contract = gate.load_contract()
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    assert contract["runtime"]["listener"] == "127.0.0.1:7870"
    assert contract["runtime"]["product_entry"] == "uruha_web_ui_product_p4_w.py"
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False
    assert contract["failure_policy"]["manual_candidate_injection_allowed"] is False


def test_dataset_has_four_fresh_non_memory_prompts_and_fixed_branch_contract():
    dataset = gate.load_dataset(gate.load_contract())
    assert [row["turn"] for row in dataset["turns"]] == [1, 2, 3, 4]
    assert sorted({row["input_language"] for row in dataset["turns"]}) == ["en", "ja", "zh"]
    assert len({row["target_frame_family"] for row in dataset["turns"]}) == 4
    assert dataset["novelty"]["input_occurrences_before_dataset_creation"] == 0
    assert dataset["branch_contract"]["no_effective_violation"]["p4_w_changed"] is False
    assert dataset["branch_contract"]["effective_violation_detected"]["p4_w_changed"] is True


def test_passing_fixture_passes_and_zero_natural_trigger_fails_closed():
    contract = gate.load_contract()
    fixture = _passing_fixture()
    assert gate.evaluate_evidence(contract, fixture)["status"] == "pass"
    negative = copy.deepcopy(fixture)
    negative["turns"][0]["p4_v_violations"] = []
    negative["turns"][0]["p4_w_changed"] = False
    negative["metrics"]["minimum_natural_repair_trigger_count"] = 0
    result = gate.evaluate_evidence(contract, negative)
    assert "metric_floor_missed:minimum_natural_repair_trigger_count" in result["failed_gates"]


def test_branch_digest_and_tab_failures_are_rejected():
    evidence = _passing_fixture()
    evidence["turns"][0]["p4_w_changed"] = False
    evidence["turns"][1]["visible_matches_after_digest"] = False
    evidence["accounting"]["closed_user_tab_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "turn_1_branch_inconsistent" in result["failed_gates"]
    assert "turn_2_visible_digest_mismatch" in result["failed_gates"]
    assert "accounting_mismatch:closed_user_tab_count" in result["failed_gates"]
