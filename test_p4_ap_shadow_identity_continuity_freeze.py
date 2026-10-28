import hashlib
import json
from pathlib import Path

import pytest

import p4_ap_shadow_identity_continuity_gate as gate
import uruha_adaptive_person_model as adaptive
import uruha_desired_response_outcome_binding_p4 as outcome
import uruha_prediction_identity_p1 as identity


ROOT = Path(__file__).resolve().parent


def test_contract_binds_new_case_and_unchanged_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest
    previous_inputs = set()
    for path in (ROOT / "datasets").glob("p4_a*.json"):
        if path.name == dataset_path.name:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        previous_inputs.update(row.get("input") for row in payload.get("turns", []))
    dataset = gate.load_dataset(contract)
    assert {row["input"] for row in dataset["turns"]}.isdisjoint(previous_inputs)


def test_preflight_reachability_and_expected_identity_progression_only():
    dataset = gate.load_dataset(gate.load_contract())
    first = adaptive.extract_observable_trigger_predicates_m37(dataset["turns"][0]["input"])
    assert first["predicates"] == ["cognitive_overactivity"]
    for row in dataset["turns"][1:]:
        explicit = adaptive.classify_explicit_desired_response_m25(row["input"])
        assert explicit["selected_policy"] == "calibrate_need"
    assert [row["expected_prediction_sequence"] for row in dataset["turns"]] == [1, 2, 3]
    assert [row["expected_shadow_identity_floor"] for row in dataset["turns"]] == [0, 1, 2]


def test_before_failure_reproduces_when_sequence_two_enters_empty_shadow():
    identity.install_prediction_identity_p1()
    binding = {
        "status": "pending",
        "prediction_id": "p1-2-0123456789abcdef",
        "turn_index": 2,
        "input_digest": "0" * 16,
        "selected_policy": "calibrate_need",
        "candidate_snapshots": [
            {"policy_id": "calibrate_need", "operational_action_score": 0.8}
        ],
    }
    with pytest.raises(ValueError, match="prediction sequence skipped"):
        outcome.build_shadow_feedback_model_p4(binding, {"state": {}})


def test_contract_forbids_guard_bypass_and_same_case_rerun():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    assert boundary["sequence_guard_bypass_allowed"] is False
    assert boundary["feedback_classifier_change_allowed"] is False
    assert boundary["predecessor_change_allowed"] is False
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False
