import io
import json
from urllib.error import URLError

import pytest

import p3_b62_real_context_prediction_freeze as b62
import p3_b63_schema_enforced_real_context_predictions as b63


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload, ensure_ascii=False).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def model_value(prompt):
    payload = json.loads(prompt)
    output = payload["output_contract"]
    if "literal_summary" in output:
        return {"literal_summary": "話を続けている。", "current_topic": "配信の話題", "explicit_actions": ["説明する"]}
    if "observed_literal" in output:
        return {
            "observed_literal": "話を続けている。",
            "primary_hypothesis": "説明を続ける可能性が高い。",
            "evidence": ["直前まで連続して話している"],
            "confidence": 0.6,
            "alternative_hypothesis": "確認を挟む可能性もある。",
            "stance_or_emotion": "不明",
            "relationship_signal": "視聴者へ話している",
            "implicit_need": "共有したい可能性",
            "next_action_tendency": "続けて説明する",
        }
    labels = payload["candidate_behavior_labels"]
    probabilities = {label: 0.1 for label in labels}
    probabilities["acknowledge_then_continue"] = 0.5
    return {
        "probabilities": probabilities,
        "predicted_next_content": "そのまま話を続けると思う。",
        "brief_evidence": "直前の流れが続いているため。",
    }


def opener_from_prompt(http_request, timeout):
    payload = json.loads(http_request.data)
    assert isinstance(payload["format"], dict)
    assert payload["format"]["additionalProperties"] is False
    value = model_value(payload["prompt"])
    return Response(
        {
            "response": json.dumps(value, ensure_ascii=False),
            "prompt_eval_count": 100,
            "eval_count": 40,
            "model": payload["model"],
        }
    )


def artifact():
    return {
        "cues": [
            {"start_seconds": 3002.76, "end_seconds": 3003.5, "text": "テスト文脈"},
            {"start_seconds": 3175.0, "end_seconds": 3176.079, "text": "続き"},
        ]
    }


def test_contract_preserves_b62_experiment_and_future_lock():
    assert b63.validate_contract() == {"valid": True, "errors": []}
    contract = b63.load_contract()
    inherited = contract["inherited_experiment"]
    assert inherited["condition_order"] == ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]
    assert inherited["model"] == "qwen3.5:9b"
    assert inherited["completion_token_ceiling_each_condition"] == 512
    assert inherited["future_outcome_access_before_complete_result_required"] == 0
    assert contract["schema_enforcement"]["same_field_names_and_types_as_b62"] is True
    assert all(contract["denied_actions"].values())


def test_json_schemas_are_exact_for_literal_pragmatic_and_prediction():
    inherited = b62.load_contract()
    labels = inherited["target"]["candidate_behavior_labels"]
    for condition in inherited["execution"]["condition_order"]:
        rep_prompt = b62.representation_prompt(condition, artifact(), inherited)
        schema = b63.schema_for_prompt(rep_prompt, labels)
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        pred_prompt = b62.prediction_prompt(condition, model_value(rep_prompt), inherited)
        pred_schema = b63.schema_for_prompt(pred_prompt, labels)
        assert pred_schema["properties"]["probabilities"]["additionalProperties"] is False
        assert pred_schema["properties"]["probabilities"]["required"] == labels


@pytest.mark.parametrize("condition", ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"])
def test_schema_provider_completes_two_call_condition_with_boundary_records(condition):
    inherited = b62.load_contract()
    provider = b63.SchemaOllamaProvider(
        endpoint="http://local.invalid",
        timeout=10,
        labels=inherited["target"]["candidate_behavior_labels"],
        opener=opener_from_prompt,
    )
    prediction, _ = b62.run_condition(condition, artifact(), inherited, provider)
    assert prediction["condition"] == condition
    assert prediction["selected_behavior"] == "acknowledge_then_continue"
    assert len(provider.records) == 2
    assert all(record["status"] == "completed" for record in provider.records)
    assert all(record["prompt_tokens"] == 100 for record in provider.records)
    assert all(record["completion_tokens"] == 40 for record in provider.records)


def test_failed_provider_call_is_counted_and_unavailable_tokens_are_not_zero():
    inherited = b62.load_contract()

    def failing(*_, **__):
        raise URLError("offline")

    provider = b63.SchemaOllamaProvider(
        endpoint="http://local.invalid",
        timeout=10,
        labels=inherited["target"]["candidate_behavior_labels"],
        opener=failing,
    )
    prompt = b62.representation_prompt("BASELINE_LITERAL", artifact(), inherited)
    with pytest.raises(Exception):
        provider(model="qwen3.5:9b", prompt=prompt, options={"num_predict": 256})
    assert len(provider.records) == 1
    assert provider.records[0]["status"] == "failed"
    assert provider.records[0]["prompt_tokens"] == "unavailable"
    assert provider.records[0]["completion_tokens"] == "unavailable"


def test_result_validator_accepts_complete_predictions_and_exact_call_accounting():
    inherited = b62.load_contract()
    provider = b63.SchemaOllamaProvider(
        endpoint="http://local.invalid",
        timeout=10,
        labels=inherited["target"]["candidate_behavior_labels"],
        opener=opener_from_prompt,
    )
    predictions = []
    for condition in inherited["execution"]["condition_order"]:
        prediction, _ = b62.run_condition(condition, artifact(), inherited, provider)
        predictions.append(prediction)
    result = {
        "schema": "uruha_p3_b63_schema_enforced_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_frozen",
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "predictions": predictions,
        "call_records": provider.records,
        "model_call_count": 4,
    }
    b63._finalize_result(result)
    assert b63.validate_result(result) == {"valid": True, "errors": []}


def test_contract_drift_to_model_budget_or_future_fails():
    contract = b63.load_contract()
    drifted = json.loads(json.dumps(contract))
    drifted["inherited_experiment"]["model"] = "qwen3.5:27b"
    assert "inherited_experiment" in b63.validate_contract(drifted)["errors"]
    drifted = json.loads(json.dumps(contract))
    drifted["inherited_experiment"]["prediction_num_predict"] = 512
    assert "inherited_experiment" in b63.validate_contract(drifted)["errors"]
    drifted = json.loads(json.dumps(contract))
    drifted["inherited_experiment"]["future_outcome_access_before_complete_result_required"] = 1
    assert "inherited_experiment" in b63.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(b63, "ROOT", tmp_path)
    contract = b63.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(b62.B62ExecutionError, match="already consumed"):
        b63._fresh_state_root(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b63.validate_implementation_freeze() == {
        "valid": True,
        "model_call_count_at_freeze": 0,
        "future_outcome_access_count_at_freeze": 0,
    }
