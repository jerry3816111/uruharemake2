import hashlib
import json
from pathlib import Path

import p4_an_post_turn_temporal_graph_gate as gate


ROOT = Path(__file__).resolve().parent


def test_contract_binds_fresh_three_turn_case_and_failed_predecessor_unchanged():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_frozen_case_is_new_and_retains_strict_three_turn_order():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert [row["expected_past_record_count"] for row in dataset["turns"]] == [0, 0, 1]
    assert [row["expected_previous_outcome"] for row in dataset["turns"]] == [None, "supported", "supported"]
    p4_am = json.loads((ROOT / "datasets/p4_am_real_runtime_temporal_graph_v1.json").read_text(encoding="utf-8"))
    assert {row["input"] for row in dataset["turns"]}.isdisjoint(
        {row["input"] for row in p4_am["turns"]}
    )


def test_only_post_turn_delivery_files_are_allowed():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    assert boundary["predecessor_change_allowed"] is False
    assert boundary["temporal_state_machine_change_allowed"] is False
    assert boundary["p4_am_status_rewrite_allowed"] is False
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False


def test_real_gate_requires_new_safari_three_turn_acceptance():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = [
        {
            "turn": frozen["turn"],
            "past_record_count": frozen["expected_past_record_count"],
            "present_candidate_count": frozen["expected_present_candidate_count"],
            "current_future_status": frozen["expected_current_future_status"],
            "previous_outcome": frozen["expected_previous_outcome"],
            "graph_summary": "｜".join(frozen["required_summary_fragments"]),
            "node_before_utterance": True,
            "logic_graph_payload_exact": True,
            "raw_or_private_payload_leak": False,
        }
        for frozen in dataset["turns"]
    ]
    evidence = {
        "schema": "uruha_p4_an_real_post_turn_temporal_graph_evidence_v1",
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
