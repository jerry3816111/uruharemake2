import hashlib
import json
from pathlib import Path

import p4_v_utterance_frame_coverage_extension_gate as gate
import uruha_utterance_frame_shadow_p4 as p4t


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
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert len(dataset["development_failures"]) == 7
    assert len(dataset["holdout_failures"]) == 9
    assert len(dataset["faithful_controls"]) == 9
    ids = [
        row["case_id"]
        for partition in ("development_failures", "holdout_failures", "faithful_controls")
        for row in dataset[partition]
    ]
    assert len(ids) == len(set(ids)) == 25
    assert dataset["novelty"]["holdout_source_occurrences_before_dataset_creation"] == 0


def test_released_p4_t_base_observations_are_frozen_before_extension():
    dataset = gate.load_dataset(gate.load_contract())
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            trace = p4t.inspect_utterance_frame_shadow_p4(frozen["source"], frozen["candidate"])
            assert trace["violations"] == frozen["expected_base_violations"], frozen["case_id"]


def test_contract_forbids_visible_changes_case_routes_and_future_holdout_reuse():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    policy = contract["failure_policy"]
    assert boundary["visible_reply_change_allowed"] is False
    assert boundary["p4_t_module_or_entry_change_allowed"] is False
    assert boundary["case_id_or_source_exact_match_routing_allowed"] is False
    assert policy["p4_u_exposed_cases_may_be_called_holdout"] is False
    assert policy["later_surface_repair_requires_another_fresh_holdout"] is True


def test_gate_fails_closed_for_missing_future_evidence():
    contract = gate.load_contract()
    result = gate.evaluate_evidence(contract, {})
    assert result["status"] == "fail"
    assert result["failed_gates"]
