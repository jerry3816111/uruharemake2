import json
from pathlib import Path

import p4_au_source_bound_current_action_delivery_gate as gate


ROOT = Path(__file__).resolve().parent


def test_p4_au_dataset_and_predecessors_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_p4_au_implementation"
    assert dataset["status"] == "prospectively_frozen_before_p4_au_implementation"
    assert gate.assert_predecessors_unchanged(contract) is True
    assert sum(
        len(dataset[key])
        for key in (
            "development_sequences",
            "fresh_positive_sequences",
            "fresh_control_sequences",
        )
    ) == contract["dataset"]["case_count"] == 16


def test_p4_au_freezes_new_crosslingual_cases_and_exposed_case_is_development_only():
    dataset = gate.load_dataset()

    assert len(dataset["development_sequences"]) == 1
    assert len(dataset["fresh_positive_sequences"]) == 6
    assert len(dataset["fresh_control_sequences"]) == 9
    assert {row["language"] for row in dataset["fresh_positive_sequences"]} == {"zh", "en", "ja"}
    assert dataset["development_sequences"][0]["case_id"].startswith("p4-at-real-exposed")


def test_p4_au_contract_separates_source_authority_from_action_quality():
    contract = gate.load_contract()
    source = gate.load_dataset()["source_contract"]

    assert source["required_receipt_identity"] == "exact_product_p1_plus_m44_next_turn_receipt"
    assert source["required_prior_ownership"] == "direct_user_first_person"
    assert source["required_prior_observable_trigger"] == "cognitive_overactivity"
    assert source["assistant_text_is_source"] is False
    assert source["private_state_inference_is_source"] is False
    assert contract["failure_policy"]["timeout_may_count_as_action_delivery"] is False
    assert contract["failure_policy"]["generic_promise_may_count_as_action_delivery"] is False


def test_p4_au_controls_cover_each_causal_block_boundary():
    controls = gate.load_dataset()["fresh_control_sequences"]
    statuses = {row["expected_bridge_status"] for row in controls}

    assert statuses == {
        "blocked_prior_source_role",
        "blocked_prior_trigger",
        "blocked_current_task_replacement",
        "blocked_exact_action_identity",
        "blocked_no_decisive_action_feedback",
        "blocked_current_policy",
        "blocked_prior_source_budget",
    }
    assert sum(row["expected_prior_source_added"] for row in controls) == 0


def test_p4_au_does_not_authorize_mutating_existing_gates_or_prompts():
    contract = gate.load_contract()
    forbidden = set(contract["forbidden_changes"])

    assert "p4_at_outcome_classifier" in forbidden
    assert "p1_or_m44_identity_rules" in forbidden
    assert "m39_or_m45_action_act_gate" in forbidden
    assert "model_prompt_or_model_parameters" in forbidden
    assert contract["resource_limits"]["offline_new_model_calls"] == 0
    assert contract["resource_limits"]["implementation_correction_batches"] == 2


def test_p4_au_evidence_gate_fails_closed_when_any_metric_is_missing():
    contract = gate.load_contract()
    empty = gate.evaluate_offline_evidence(contract, {"metrics": {}})

    assert empty["status"] == "fail"
    assert set(empty["failed_gates"]) == set(contract["offline_gates"])


def test_p4_au_frozen_files_are_valid_json():
    for relative in (
        "datasets/p4_au_source_bound_current_action_delivery_v1.json",
        "configs/p4_au_source_bound_current_action_delivery_v1.json",
    ):
        json.loads((ROOT / relative).read_text(encoding="utf-8"))
