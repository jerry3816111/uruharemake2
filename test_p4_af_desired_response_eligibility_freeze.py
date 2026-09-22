import copy
import hashlib
from pathlib import Path

import p4_af_desired_response_eligibility_gate as gate


ROOT = Path(__file__).resolve().parent


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for partition in ("development_cases", "fresh_positive_cases", "fresh_negative_cases"):
        for frozen in dataset[partition]:
            eligible = frozen.get("expected_selected_action_mode") is not None
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": frozen["expected_status"],
                    "eligibility_authority": frozen["expected_authority"],
                    "selected_action_mode": frozen.get("expected_selected_action_mode"),
                    "candidate_count": 6 if eligible else 0,
                    "candidate_ranking_unchanged": eligible,
                    "topic_only_authorized": False,
                    "visible_reply_changed": False,
                    "new_model_call_count": 0,
                    "fact_write_count": 0,
                    "profile_write_count": 0,
                    "episode_write_count": 0,
                }
            )
    return {
        "schema": "uruha_p4_af_desired_response_eligibility_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "cases": cases,
        "metrics": copy.deepcopy(contract["gates"]),
        "integration": copy.deepcopy(contract["integration_gates"]),
    }


def test_contract_binds_predecessor_dataset_languages_and_single_variable_boundary():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    assert {row["language"] for row in dataset["fresh_positive_cases"]} == {"zh", "en", "ja"}
    assert {row["language"] for row in dataset["fresh_negative_cases"]} == {"zh", "en", "ja"}
    assert contract["implementation_boundary"]["mode"] == "additive_eligibility_guard"
    assert contract["implementation_boundary"]["candidate_score_or_order_change_allowed"] is False
    assert contract["implementation_boundary"]["topic_word_as_solo_authority_allowed"] is False


def test_passing_fixture_passes_frozen_gate():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_fixture())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_rejects_topic_authority_candidate_rerank_and_visible_or_memory_side_effect():
    evidence = _passing_fixture()
    evidence["cases"][0]["topic_only_authorized"] = True
    evidence["cases"][2]["candidate_ranking_unchanged"] = False
    evidence["cases"][3]["visible_reply_changed"] = True
    evidence["cases"][4]["episode_write_count"] = 1
    failures = gate.evaluate_evidence(gate.load_contract(), evidence)["failed_gates"]
    assert "af_dev_ae_false_positive_zh:topic_only_authorized" in failures
    assert "af_dev_explicit_solution_zh:candidate_ranking_changed" in failures
    assert "af_dev_cognitive_ambiguity_zh:visible_or_model_side_effect" in failures
    assert "af_positive_cognitive_zh:memory_write_added" in failures


def test_case_ids_and_inputs_are_unique():
    dataset = gate.load_dataset(gate.load_contract())
    rows = [
        row
        for partition in ("development_cases", "fresh_positive_cases", "fresh_negative_cases")
        for row in dataset[partition]
    ]
    assert len({row["case_id"] for row in rows}) == len(rows)
    assert len({row["input"] for row in rows}) == len(rows)
