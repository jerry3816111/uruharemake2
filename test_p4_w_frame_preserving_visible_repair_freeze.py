import hashlib
from pathlib import Path

import p4_w_frame_preserving_visible_repair_gate as gate
import uruha_utterance_frame_shadow_extension_p4 as p4v


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_frozen_contract_binds_new_dataset_and_immutable_predecessors():
    contract = gate.load_contract()
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    predecessor = contract["predecessor"]
    assert _sha256(ROOT / predecessor["module"]) == predecessor["module_sha256"]
    assert _sha256(ROOT / predecessor["entry"]) == predecessor["entry_sha256"]
    assert _sha256(ROOT / predecessor["released_product_entry"]) == predecessor["released_product_entry_sha256"]


def test_frozen_partitions_are_unique_and_record_prospective_novelty():
    dataset = gate.load_dataset(gate.load_contract())
    assert len(dataset["development_failures"]) == 4
    assert len(dataset["holdout_failures"]) == 12
    assert len(dataset["faithful_controls"]) == 8
    ids = [
        row["case_id"]
        for partition in ("development_failures", "holdout_failures", "faithful_controls")
        for row in dataset[partition]
    ]
    assert len(ids) == len(set(ids)) == 24
    assert dataset["novelty"]["holdout_source_occurrences_before_dataset_creation"] == 0


def test_frozen_p4_v_preconditions_match_before_repair():
    dataset = gate.load_dataset(gate.load_contract())
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            trace = p4v.inspect_utterance_frame_coverage_extension_p4(frozen["source"], frozen["candidate"])
            assert trace["violations"] == frozen["expected_before_violations"], frozen["case_id"]


def test_contract_forbids_reclassification_case_routes_and_safari_without_new_freeze():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    policy = contract["failure_policy"]
    assert boundary["frame_classifier_change_allowed"] is False
    assert boundary["p4_t_or_p4_v_change_allowed"] is False
    assert boundary["faithful_candidate_change_allowed"] is False
    assert boundary["case_id_or_source_exact_match_routing_allowed"] is False
    assert policy["p4_u_or_p4_v_exposed_cases_may_be_called_holdout"] is False
    assert policy["safari_execution_requires_separate_frozen_real_turn_contract"] is True


def test_gate_fails_closed_for_missing_future_evidence():
    result = gate.evaluate_evidence(gate.load_contract(), {})
    assert result["status"] == "fail"
    assert result["failed_gates"]
