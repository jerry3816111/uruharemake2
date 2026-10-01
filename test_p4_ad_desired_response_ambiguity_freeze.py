import copy
import hashlib
from pathlib import Path

import p4_ad_desired_response_ambiguity_gate as gate


ROOT = Path(__file__).resolve().parent


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for partition in ("development_cases", "holdout_ambiguity_cases", "literal_controls"):
        for frozen in dataset[partition]:
            control = partition == "literal_controls"
            modes = list(frozen.get("required_candidate_modes") or [])
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": frozen["expected_status"],
                    "selected_action_mode": frozen.get("expected_selected_action_mode"),
                    "candidate_modes": modes,
                    "candidate_count": 0 if control else max(4, len(modes)),
                    "candidate_contract_passed": False if control else True,
                    "private_reason_status": None if control else "unknown_not_observed",
                    "selected_action_is_private_truth_commitment": False,
                    "trace_contains_raw_input": False,
                    "visible_reply_changed": False,
                    "new_model_call_count": 0,
                    "fact_write_count": 0,
                    "profile_write_count": 0,
                    "episode_write_count": 0,
                }
            )
    return {
        "schema": "uruha_p4_ad_desired_response_ambiguity_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "cases": cases,
        "metrics": copy.deepcopy(contract["gates"]),
        "integration": copy.deepcopy(contract["integration_gates"]),
    }


def test_contract_binds_dataset_predecessors_languages_and_shadow_boundary():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    assert {row["language"] for row in dataset["holdout_ambiguity_cases"]} == {"zh", "en", "ja"}
    assert len(dataset["holdout_ambiguity_cases"]) == 9
    assert len(dataset["literal_controls"]) == 6
    assert contract["implementation_boundary"]["mode"] == "additive_shadow_only"
    assert contract["implementation_boundary"]["visible_reply_change_allowed"] is False
    assert contract["failure_policy"]["real_product_or_safari_execution_authorized_by_this_contract"] is False


def test_passing_fixture_passes_frozen_gate():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_fixture())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_missing_alternative_private_truth_and_control_false_positive():
    evidence = _passing_fixture()
    evidence["cases"][0]["candidate_modes"] = ["practical_help"]
    evidence["cases"][1]["selected_action_is_private_truth_commitment"] = True
    evidence["cases"][-1]["candidate_count"] = 1
    failures = gate.evaluate_evidence(gate.load_contract(), evidence)["failed_gates"]
    assert "dev_user_counterexample_zh_01:required_candidate_modes_missing" in failures
    assert "dev_explicit_solution_zh_01:private_truth_committed" in failures
    assert "control_literal_ja_02:literal_control_false_positive" in failures


def test_gate_rejects_raw_input_reply_mutation_model_and_memory_side_effects():
    evidence = _passing_fixture()
    evidence["cases"][3]["trace_contains_raw_input"] = True
    evidence["cases"][4]["visible_reply_changed"] = True
    evidence["cases"][5]["new_model_call_count"] = 1
    evidence["cases"][6]["episode_write_count"] = 1
    failures = gate.evaluate_evidence(gate.load_contract(), evidence)["failed_gates"]
    assert "holdout_ambiguity_zh_01:raw_input_persisted" in failures
    assert "holdout_ambiguity_zh_02:visible_reply_changed" in failures
    assert "holdout_ambiguity_zh_03:model_call_added" in failures
    assert "holdout_ambiguity_en_01:memory_write_added" in failures


def test_dataset_case_ids_are_unique_and_no_holdout_input_reuses_development():
    dataset = gate.load_dataset(gate.load_contract())
    rows = [
        row
        for partition in ("development_cases", "holdout_ambiguity_cases", "literal_controls")
        for row in dataset[partition]
    ]
    assert len({row["case_id"] for row in rows}) == len(rows)
    development_inputs = {row["input"] for row in dataset["development_cases"]}
    assert not development_inputs.intersection(row["input"] for row in dataset["holdout_ambiguity_cases"])
