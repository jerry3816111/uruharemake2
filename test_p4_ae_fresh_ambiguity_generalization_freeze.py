import copy
import hashlib
from pathlib import Path

import p4_ae_fresh_ambiguity_generalization_gate as gate


ROOT = Path(__file__).resolve().parent


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for partition in ("ambiguity_cases", "near_miss_controls"):
        for frozen in dataset[partition]:
            control = partition == "near_miss_controls"
            modes = list(frozen.get("required_candidate_modes") or [])
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": frozen["expected_status"],
                    "selected_action_mode": frozen.get("expected_selected_action_mode"),
                    "candidate_modes": modes,
                    "candidate_count": 0 if control else len(modes),
                    "candidate_contract_passed": False if control else True,
                    "private_reason_status": "not_applicable" if control else "unknown_not_observed",
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
        "schema": "uruha_p4_ae_fresh_ambiguity_generalization_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "execution_count": 1,
        "cases": cases,
        "metrics": copy.deepcopy(contract["gates"]),
        "accounting": {"retry_count": 0, "fallback_count": 0},
    }


def test_contract_binds_fresh_dataset_frozen_implementation_and_one_execution():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    assert dataset["novelty"]["p4_ad_exact_inputs_reused"] is False
    assert dataset["novelty"]["implementation_execution_before_seal"] is False
    assert dataset["novelty"]["independent_human_sample"] is False
    assert {row["language"] for row in dataset["ambiguity_cases"]} == {"zh", "en", "ja"}
    assert contract["execution"]["maximum_executions"] == 1
    assert contract["execution"]["implementation_change_after_result_allowed"] is False


def test_passing_fixture_passes_frozen_gate():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_fixture())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_missed_generalization_false_positive_or_second_execution():
    evidence = _passing_fixture()
    evidence["cases"][0]["status"] = "not_applicable"
    evidence["cases"][-1]["candidate_count"] = 1
    evidence["execution_count"] = 2
    failures = gate.evaluate_evidence(gate.load_contract(), evidence)["failed_gates"]
    assert "ae_ambiguity_zh_01:status_mismatch" in failures
    assert "ae_control_ja_02:near_miss_false_positive" in failures
    assert "execution_count_mismatch" in failures


def test_case_ids_and_inputs_are_unique():
    dataset = gate.load_dataset(gate.load_contract())
    rows = [*dataset["ambiguity_cases"], *dataset["near_miss_controls"]]
    assert len({row["case_id"] for row in rows}) == len(rows)
    assert len({row["input"] for row in rows}) == len(rows)
