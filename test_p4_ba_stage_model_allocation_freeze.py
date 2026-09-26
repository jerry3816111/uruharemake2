import hashlib
import json
from pathlib import Path

import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ba_stage_model_allocation_v1.json"
DATASET = ROOT / "datasets" / "p4_ba_stage_model_allocation_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    return (
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(DATASET.read_text(encoding="utf-8")),
    )


def test_p4_ba_dataset_is_sealed_hash_bound_and_development_only():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_model_execution"
    assert dataset["status"] == "sealed_before_model_execution"
    assert dataset["development_only"] is True
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert len(dataset["generation_cases"]) == 2
    assert len(dataset["review_fixtures"]) == 4
    assert dataset["reuse_policy"]["same_model_call_may_be_retried"] is False


def test_p4_ba_freezes_the_complete_two_by_two_model_allocation():
    contract, _dataset = _load()
    observed = {
        (row["generator"], row["reviewer"])
        for row in contract["arms"]
    }

    assert observed == {
        ("qwen3.5:9b", "qwen3.5:9b"),
        ("qwen3.5:9b", "qwen3.5:0.8b"),
        ("qwen3.5:4b", "qwen3.5:9b"),
        ("qwen3.5:4b", "qwen3.5:0.8b"),
    }
    assert contract["controlled_constants"]["generation_reuse_across_reviewer_arms"] is True
    assert contract["controlled_constants"]["prewarm_models_once_in_fixed_order"] == [
        "qwen3.5:9b", "qwen3.5:4b", "qwen3.5:0.8b"
    ]
    assert contract["controlled_constants"]["prewarm_scored_as_case_latency"] is False
    assert contract["controlled_constants"]["keep_alive"] == "30m"
    assert contract["execution"]["record_prewarm_wall_seconds_separately"] is True
    assert contract["controlled_constants"]["retry_count"] == 0


def test_p4_ba_review_fixtures_cannot_be_passed_by_an_always_true_reviewer():
    _contract, dataset = _load()
    expected = [row["expected_accepted"] for row in dataset["review_fixtures"]]

    assert expected.count(True) == 2
    assert expected.count(False) == 2


def test_p4_ba_review_fixtures_are_structurally_valid_so_semantic_review_is_required():
    _contract, dataset = _load()

    for row in dataset["review_fixtures"]:
        assert m46.structural_plan_violations(row["plan"], [row["source"]]) == []


def test_p4_ba_product_eligibility_requires_quality_cost_and_complete_accounting():
    contract, _dataset = _load()
    gates = contract["formal_gates"]

    assert gates["generation_json_parse_success_count"] == 2
    assert gates["generation_structurally_valid_count"] == 2
    assert gates["review_fixture_correct_count"] == 4
    assert gates["full_pipeline_accepted_count"] == 2
    assert gates["full_pipeline_source_exact_count"] == 2
    assert gates["full_pipeline_natural_japanese_count"] == 2
    assert gates["maximum_two_stage_seconds"] == 20
    assert gates["token_accounting_complete"] is True


def test_p4_ba_contract_binds_the_frozen_candidate_review_and_transport_code():
    contract, _dataset = _load()

    for _name, (relative, expected) in contract["implementation"].items():
        assert _sha(ROOT / relative) == expected


def test_p4_ba_failure_policy_forbids_retries_gate_changes_and_runtime_mutation():
    contract, _dataset = _load()
    failure = contract["failure_policy"]

    assert failure["same_call_retry_allowed"] is False
    assert failure["post_result_dataset_prompt_schema_or_threshold_change_allowed"] is False
    assert failure["structural_generation_pass_may_replace_review_pass"] is False
    assert failure["reviewer_always_true_may_count_as_correct"] is False
    assert failure["timeout_or_json_failure_may_count_as_pass"] is False
    assert failure["failed_arm_may_be_hidden_by_another_arm"] is False
    assert failure["runtime_model_change_before_result_allowed"] is False
