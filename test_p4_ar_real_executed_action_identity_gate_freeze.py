import hashlib
import json
from pathlib import Path

import p4_ar_executed_action_identity_gate as offline_gate
import p4_ar_real_executed_action_identity_gate as gate
import uruha_adaptive_person_model as adaptive
import uruha_executed_action_identity_gate_p4 as action_gate
import uruha_multilingual_observable_trigger_p4 as trigger


ROOT = Path(__file__).resolve().parent


def test_real_contract_binds_runtime_inputs_and_implementation():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_real_input_is_new_and_requires_the_late_extension():
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
        if payload.get("input"):
            prior_inputs.add(payload["input"])
    assert dataset["input"] not in prior_inputs
    base = adaptive.extract_observable_trigger_predicates_m37(dataset["input"])
    extended = trigger.extend_observable_trigger_p4(dataset["input"], base)
    assert base["status"] == dataset["expected_base_trigger_status"]
    assert (extended["coverage_extension"] or {})["status"] == dataset["expected_extended_trigger_status"]


def test_offline_contract_passes_before_real_execution_is_authorized():
    contract = offline_gate.load_contract()
    evidence = action_gate.build_offline_evidence_p4_ar(
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
