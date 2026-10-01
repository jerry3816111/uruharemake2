import hashlib
import json
from pathlib import Path

import p4_am_real_runtime_temporal_graph_gate as gate


ROOT = Path(__file__).resolve().parent


def test_contract_binds_three_new_turns_and_unchanged_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_frozen_turns_are_exactly_new_and_preserve_strict_temporal_order():
    dataset = gate.load_dataset(gate.load_contract())
    assert [row["expected_past_record_count"] for row in dataset["turns"]] == [0, 0, 1]
    assert [row["expected_previous_outcome"] for row in dataset["turns"]] == [None, "supported", "supported"]
    prior_turns = set()
    for path in (
        ROOT / "datasets/p4_ag_multiturn_ambiguity_outcome_v1.json",
        ROOT / "datasets/p4_ai_fresh_ambiguity_learning_chain_v1.json",
        ROOT / "datasets/p4_ak_post_morphology_learning_chain_v1.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for section in payload.values():
            if isinstance(section, list):
                for row in section:
                    if isinstance(row, dict):
                        prior_turns.update(str(row[key]) for key in ("turn_1", "turn_2") if row.get(key))
    assert {row["input"] for row in dataset["turns"]}.isdisjoint(prior_turns)


def test_contract_allows_only_additive_files_and_one_pre_runtime_correction():
    contract = gate.load_contract()
    assert contract["implementation_boundary"]["predecessor_change_allowed"] is False
    assert contract["implementation_boundary"]["raw_dialogue_in_graph_allowed"] is False
    assert contract["failure_policy"]["maximum_informed_correction_batches_before_real_execution"] == 1
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False


def test_real_gate_requires_safari_and_refuses_fixture_substitution():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = []
    for frozen in dataset["turns"]:
        turns.append({
            "turn": frozen["turn"],
            "past_record_count": frozen["expected_past_record_count"],
            "present_candidate_count": 6,
            "current_future_status": "committed_outcome_locked",
            "previous_outcome": frozen["expected_previous_outcome"],
            "graph_summary": "｜".join(frozen["required_summary_fragments"]),
            "node_before_utterance": True,
            "logic_graph_payload_exact": True,
            "raw_or_private_payload_leak": False
        })
    evidence = {
        "schema": "uruha_p4_am_real_runtime_temporal_graph_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": {**contract["real_gates"], "maximum_turn_latency_seconds": 1.0, "maximum_total_latency_seconds": 2.0},
        "safari": {"actual_three_turn_acceptance": False, "temporal_node_visually_observed_each_turn": False}
    }
    failures = gate.evaluate_real_evidence(contract, evidence)["failed_gates"]
    assert failures == ["safari_three_turn_missing", "safari_temporal_node_missing"]
