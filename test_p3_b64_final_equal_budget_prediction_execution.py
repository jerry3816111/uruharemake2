from copy import deepcopy

import pytest

import p3_b62_real_context_prediction_freeze as b62
import p3_b64_final_equal_budget_prediction_execution as b64


def prediction(condition):
    labels = b62.load_contract()["target"]["candidate_behavior_labels"]
    probabilities = {label: 0.1 for label in labels}
    probabilities["acknowledge_then_continue"] = 0.5
    return {
        "condition": condition,
        "probabilities": probabilities,
        "selected_behavior": "acknowledge_then_continue",
        "predicted_next_content": "そのまま話を続けると思う。",
        "brief_evidence": "直前の流れが続いているため。",
        "representation_sha256": "a" * 64,
        "representation_persisted": False,
        "raw_prompt_or_response_persisted": False,
    }


def completed_records():
    budgets = [320, 192, 320, 192]
    return [
        {
            "call_index": index + 1,
            "status": "completed",
            "num_predict": budget,
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "latency_seconds": 0.5,
        }
        for index, budget in enumerate(budgets)
    ]


def test_contract_is_final_same_experiment_equal_total_budget_reallocation():
    assert b64.validate_contract() == {"valid": True, "errors": []}
    contract = b64.load_contract()
    assert contract["reallocated_budget"] == {
        "representation_num_predict": 320,
        "prediction_num_predict": 192,
        "sum_each_condition": 512,
        "same_for_both_conditions": True,
        "total_budget_increase": 0,
    }
    assert contract["execution"]["final_prediction_execution_correction"] is True
    assert contract["execution"]["retry_or_condition_fallback_allowed"] is False
    assert contract["unchanged_experiment"]["future_outcome_access_before_complete_result_required"] == 0
    assert all(contract["denied_actions"].values())


def test_adjusted_b62_contract_changes_only_call_allocation_and_keeps_total():
    original = b62.load_contract()
    adjusted = b64.adjusted_b62_contract()
    assert adjusted["fairness"]["representation_call_num_predict"] == 320
    assert adjusted["fairness"]["prediction_call_num_predict"] == 192
    assert 320 + 192 == original["fairness"]["same_completion_token_ceiling_per_condition"]
    normalized = deepcopy(adjusted)
    normalized["fairness"]["representation_call_num_predict"] = original["fairness"]["representation_call_num_predict"]
    normalized["fairness"]["prediction_call_num_predict"] = original["fairness"]["prediction_call_num_predict"]
    assert normalized == original


def test_result_validator_accepts_complete_equal_budget_predictions():
    result = {
        "schema": "uruha_p3_b64_final_equal_budget_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_frozen",
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 4,
        "call_records": completed_records(),
        "predictions": [prediction("BASELINE_LITERAL"), prediction("SYSTEM_PRAGMATIC_STATE")],
        "completion_token_ceiling_by_condition": {"BASELINE_LITERAL": 512, "SYSTEM_PRAGMATIC_STATE": 512},
    }
    b64._finalize_result(result)
    assert b64.validate_result(result) == {"valid": True, "errors": []}


def test_result_validator_rejects_budget_drift_and_future_access():
    result = {
        "schema": "uruha_p3_b64_final_equal_budget_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_failed",
        "failure_stage": "model",
        "failure_category": "provider_or_schema",
        "future_outcome_access_count": 1,
        "outcome_score_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 1,
        "call_records": [{"call_index": 1, "status": "completed", "num_predict": 256}],
    }
    b64._finalize_result(result)
    report = b64.validate_result(result)
    assert "future_boundary" in report["errors"]
    assert "call_budgets" in report["errors"]


def test_contract_drift_to_total_budget_retry_or_model_fails():
    contract = b64.load_contract()
    drifted = deepcopy(contract)
    drifted["reallocated_budget"]["prediction_num_predict"] = 256
    assert "budget" in b64.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["execution"]["retry_or_condition_fallback_allowed"] = True
    assert "execution" in b64.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["unchanged_experiment"]["model"] = "qwen3.5:27b"
    assert "unchanged_experiment" in b64.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(b64, "ROOT", tmp_path)
    contract = b64.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(b62.B62ExecutionError, match="already consumed"):
        b64._fresh_state_root(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b64.validate_implementation_freeze() == {
        "valid": True,
        "model_call_count_at_freeze": 0,
        "future_outcome_access_count_at_freeze": 0,
    }
