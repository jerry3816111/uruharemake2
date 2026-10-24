import hashlib
import json
from pathlib import Path

import p4_ao_reachable_temporal_graph_gate as gate
import uruha_adaptive_person_model as adaptive


ROOT = Path(__file__).resolve().parent


def test_contract_binds_unchanged_p4_an_product_and_fresh_case():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest
    prior = set()
    for filename in (
        "p4_am_real_runtime_temporal_graph_v1.json",
        "p4_an_post_turn_temporal_graph_v1.json",
    ):
        payload = json.loads((ROOT / "datasets" / filename).read_text(encoding="utf-8"))
        prior.update(row["input"] for row in payload["turns"])
    dataset = gate.load_dataset(contract)
    assert {row["input"] for row in dataset["turns"]}.isdisjoint(prior)


def test_frozen_reachability_uses_released_paths_without_model_or_outcome_probe():
    dataset = gate.load_dataset(gate.load_contract())
    first = adaptive.extract_observable_trigger_predicates_m37(dataset["turns"][0]["input"])
    assert first["predicates"] == ["cognitive_overactivity"]
    for row in dataset["turns"][1:]:
        explicit = adaptive.classify_explicit_desired_response_m25(row["input"])
        assert explicit["selected_policy"] == "calibrate_need"
        assert explicit["authority"] == "current_explicit_desired_response"


def test_contract_forbids_all_product_changes_and_same_case_rerun():
    contract = gate.load_contract()
    assert not any(contract["implementation_boundary"].values())
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False


def test_real_gate_refuses_fixture_substitution():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = []
    for frozen in dataset["turns"]:
        turns.append(
            {
                "turn": frozen["turn"],
                "past_record_count": frozen["expected_past_record_count"],
                "present_candidate_count": frozen["expected_present_candidate_count"],
                "current_future_status": frozen["expected_current_future_status"],
                "previous_outcome": frozen["expected_previous_outcome"],
                "trigger_path": frozen["expected_trigger_path"],
                "graph_summary": "｜".join(frozen["required_summary_fragments"]),
                "node_before_utterance": True,
                "logic_graph_payload_exact": True,
                "final_blackboard_contains_node": True,
                "safari_node_visually_observed": True,
                "raw_or_private_payload_leak": False,
            }
        )
    evidence = {
        "schema": "uruha_p4_ao_real_reachable_temporal_graph_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": {
            **contract["real_gates"],
            "maximum_turn_latency_seconds": 1.0,
            "maximum_total_latency_seconds": 3.0,
        },
        "safari": {
            "actual_three_turn_acceptance": False,
            "temporal_node_visually_observed_each_turn": False,
        },
    }
    failures = gate.evaluate_real_evidence(contract, evidence)["failed_gates"]
    assert failures == ["safari_three_turn_missing", "safari_temporal_node_missing"]
