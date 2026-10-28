import hashlib
import json
from pathlib import Path
import subprocess

import p4_as_real_selected_action_surface_execution as gate
import p4_as_selected_action_surface_execution_gate as offline_gate
import uruha_adaptive_person_model as adaptive
import uruha_multilingual_observable_trigger_p4 as trigger
import uruha_selected_action_surface_execution_p4 as execution


ROOT = Path(__file__).resolve().parent


def test_real_contract_binds_dataset_and_implementation():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_real_input_was_absent_at_the_frozen_preimplementation_commit():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    reference = contract["novelty_reference"]["repository_commit"]
    completed = subprocess.run(
        ["git", "grep", "-F", "--", dataset["input"], reference],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1, completed.stdout
    assert contract["novelty_reference"]["input_absent_at_commit"] is True


def test_real_input_requires_the_frozen_additive_trigger_path():
    dataset = gate.load_dataset(gate.load_contract())
    base = adaptive.extract_observable_trigger_predicates_m37(dataset["input"])
    extended = trigger.extend_observable_trigger_p4(dataset["input"], base)
    assert base["status"] == dataset["expected_base_trigger_status"]
    assert (extended["coverage_extension"] or {})["status"] == dataset["expected_extended_trigger_status"]
    promoted, trace = execution.promote_selected_action_state_p4(dataset["input"], {})
    assert promoted[execution.LABEL]["status"] == execution.EARLY_STATUS
    assert trace["source_speaker_role"] == "user_first_person"
    assert trace["third_party_present"] is False


def test_offline_contract_passes_before_real_execution_is_authorized():
    contract = offline_gate.load_contract()
    evidence = execution.build_dataset_evidence_p4_as(ROOT / contract["dataset"]["path"])
    assert offline_gate.evaluate_offline_evidence(contract, evidence)["status"] == "pass"


def test_real_contract_is_one_shot_private_safari_only():
    contract = gate.load_contract()
    assert contract["frozen_runtime"]["private_runtime_required"] is True
    assert contract["frozen_runtime"]["browser"] == "Safari"
    assert contract["frozen_runtime"]["same_case_execution_limit"] == 1
    assert contract["failure_policy"]["same_real_case_rerun_allowed"] is False
    assert contract["failure_policy"]["gate_change_after_real_result_allowed"] is False
