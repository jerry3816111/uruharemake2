import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_multilingual_observable_trigger_p4 as trigger
import uruha_live_extended_trigger_ordering_p4 as ordering
import p4_aq_live_extended_trigger_ordering_gate as offline_gate
import p4_aq_real_live_extended_trigger_ordering_gate as gate


ROOT = Path(__file__).resolve().parent


def test_real_contract_binds_runtime_inputs_and_implementation():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_real_turns_are_new_and_preflight_only_matches_frozen_paths():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    dataset = gate.load_dataset(contract)
    prior_inputs = set()
    for path in (ROOT / "datasets").glob("p4_a*.json"):
        if path == dataset_path:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for partition in (
            "development_cases",
            "fresh_positive_cases",
            "fresh_control_cases",
            "turns",
        ):
            prior_inputs.update(
                row.get("input") for row in payload.get(partition, []) if row.get("input")
            )
    assert {row["input"] for row in dataset["turns"]}.isdisjoint(prior_inputs)
    first = dataset["turns"][0]
    base = adaptive.extract_observable_trigger_predicates_m37(first["input"])
    extended = trigger.extend_observable_trigger_p4(first["input"], base)
    assert base["predicates"] == []
    assert ordering._extension_is_actionable(extended) is True
    for row in dataset["turns"][1:]:
        explicit = adaptive.classify_explicit_desired_response_m25(row["input"])
        assert explicit["selected_policy"] == "calibrate_need"
    assert [row["expected_prediction_sequence"] for row in dataset["turns"]] == [1, 2, 3]
    assert [row["expected_shadow_identity_floor"] for row in dataset["turns"]] == [0, 1, 2]


def test_offline_contract_passes_before_real_execution_is_authorized():
    contract = offline_gate.load_contract()
    evidence = ordering.build_dataset_evidence_p4_aq(
        ROOT / contract["dataset"]["path"]
    )
    assert offline_gate.evaluate_offline_evidence(contract, evidence)["status"] == "pass"


def test_real_contract_is_one_shot_private_safari_only():
    contract = gate.load_contract()
    assert contract["frozen_runtime"]["private_runtime_required"] is True
    assert contract["frozen_runtime"]["browser"] == "Safari"
    assert contract["frozen_runtime"]["same_case_execution_limit"] == 1
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False
    assert contract["failure_policy"]["gate_change_after_real_result_allowed"] is False
