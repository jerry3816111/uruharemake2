from copy import deepcopy
import json

import pytest

import p3_b62_real_context_prediction_freeze as b62


class FakeProvider:
    def __init__(self):
        self.calls = []

    def __call__(self, *, model, prompt, options):
        payload = json.loads(prompt)
        self.calls.append({"model": model, "prompt": prompt, "options": dict(options)})
        output = payload["output_contract"]
        if "literal_summary" in output:
            value = {
                "literal_summary": "配信中の話題を続けている。",
                "current_topic": "現在の話題",
                "explicit_actions": ["話を続ける"],
            }
        elif "observed_literal" in output:
            value = {
                "observed_literal": "配信中の話題を続けている。",
                "primary_hypothesis": "このまま話を展開する可能性が高い。",
                "evidence": ["直前まで連続して説明している"],
                "confidence": 0.62,
                "alternative_hypothesis": "一度確認を挟む可能性もある。",
                "stance_or_emotion": "落ち着いている可能性",
                "relationship_signal": "視聴者へ話を続けている",
                "implicit_need": "話題を共有したい可能性",
                "next_action_tendency": "説明を続ける",
            }
        else:
            labels = list(payload["candidate_behavior_labels"])
            probabilities = {label: 0.1 for label in labels}
            probabilities["acknowledge_then_continue"] = 0.5
            value = {
                "probabilities": probabilities,
                "predicted_next_content": "そのまま話を続けると思う。",
                "brief_evidence": "直前の流れが継続しているため。",
            }
        return {
            "text": json.dumps(value, ensure_ascii=False),
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "latency_seconds": 0.5,
            "model_reported": model,
        }


def _artifact():
    return {
        "schema": "uruha_p3_b60_caption_context_v1",
        "source_id": "youtube_4y5GiQpgJgo",
        "context_seconds": [3000.0, 3180.0],
        "cues": [
            {"start_seconds": 3002.76, "end_seconds": 3003.5, "text": "テスト文脈"},
            {"start_seconds": 3175.0, "end_seconds": 3176.079, "text": "続き"},
        ],
    }


def test_contract_binds_real_context_same_model_budget_and_future_lock():
    assert b62.validate_contract() == {"valid": True, "errors": []}
    contract = b62.load_contract()
    assert contract["input"]["artifact_sha256"] == "7a690e386e0945785f0dbe8d5573a2eda6f7ed6be64c28e01ee9e4cbbd5d0537"
    assert contract["input"]["future_outcome_access_before_prediction_freeze_required"] == 0
    assert contract["model"]["name"] == "qwen3.5:9b"
    assert contract["fairness"]["same_two_call_graph"] is True
    assert contract["fairness"]["same_completion_token_ceiling_per_condition"] == 512
    assert contract["execution"]["model_call_count_exact"] == 4
    assert all(contract["denied_actions"].values())


def test_prompts_keep_same_context_and_different_single_representation_variable():
    contract = b62.load_contract()
    baseline = json.loads(b62.representation_prompt("BASELINE_LITERAL", _artifact(), contract))
    system = json.loads(b62.representation_prompt("SYSTEM_PRAGMATIC_STATE", _artifact(), contract))
    assert baseline["observable_context"] == system["observable_context"]
    assert baseline["target"] == system["target"]
    assert "literal_summary" in baseline["output_contract"]
    assert "primary_hypothesis" in system["output_contract"]
    assert "confidence" in system["output_contract"]
    assert "alternative_hypothesis" in system["output_contract"]


@pytest.mark.parametrize("condition", ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"])
def test_run_condition_uses_two_calls_same_model_and_256_each(condition):
    contract = b62.load_contract()
    provider = FakeProvider()
    prediction, records = b62.run_condition(condition, _artifact(), contract, provider)
    assert prediction["condition"] == condition
    assert prediction["selected_behavior"] == "acknowledge_then_continue"
    assert prediction["predicted_next_content"] == "そのまま話を続けると思う。"
    assert prediction["representation_persisted"] is False
    assert prediction["raw_prompt_or_response_persisted"] is False
    assert len(records) == 2
    assert [call["options"]["num_predict"] for call in provider.calls] == [256, 256]
    assert all(call["model"] == "qwen3.5:9b" for call in provider.calls)


def test_representation_schema_rejects_missing_uncertainty_or_inference_in_literal():
    with pytest.raises(b62.B62ExecutionError, match="pragmatic schema"):
        b62._validate_representation(
            "SYSTEM_PRAGMATIC_STATE",
            {"observed_literal": "不足"},
        )
    with pytest.raises(b62.B62ExecutionError, match="literal schema"):
        b62._validate_representation(
            "BASELINE_LITERAL",
            {
                "literal_summary": "要約",
                "current_topic": "話題",
                "explicit_actions": [],
                "emotion": "推測",
            },
        )


def test_prediction_parser_requires_exact_normalized_labels_and_japanese():
    labels = b62.load_contract()["target"]["candidate_behavior_labels"]
    valid = {
        "probabilities": {label: (0.5 if index == 0 else 0.1) for index, label in enumerate(labels)},
        "predicted_next_content": "このまま話を続ける。",
        "brief_evidence": "流れが続いている。",
    }
    parsed = b62._parse_prediction(json.dumps(valid, ensure_ascii=False), labels, 160)
    assert parsed["selected_behavior"] == labels[0]
    invalid = deepcopy(valid)
    invalid["predicted_next_content"] = "continue"
    with pytest.raises(b62.B62ExecutionError, match="not Japanese"):
        b62._parse_prediction(json.dumps(invalid), labels, 160)
    invalid = deepcopy(valid)
    invalid["probabilities"][labels[-1]] = 0.2
    with pytest.raises(b62.B62ExecutionError, match="probability sum"):
        b62._parse_prediction(json.dumps(invalid, ensure_ascii=False), labels, 160)


def test_result_validator_accepts_frozen_predictions_and_rejects_future():
    contract = b62.load_contract()
    provider = FakeProvider()
    predictions = []
    records = []
    for condition in contract["execution"]["condition_order"]:
        prediction, condition_records = b62.run_condition(condition, _artifact(), contract, provider)
        predictions.append(prediction)
        records.extend(condition_records)
    result = {
        "schema": "uruha_p3_b62_real_context_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_frozen",
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "model_call_count": 4,
        "predictions": predictions,
        "call_records": records,
        "completion_token_ceiling_by_condition": {
            "BASELINE_LITERAL": 512,
            "SYSTEM_PRAGMATIC_STATE": 512,
        },
    }
    b62._finalize_result(result)
    assert b62.validate_result(result, contract) == {"valid": True, "errors": []}
    leaked = deepcopy(result)
    leaked["future"] = "FUTURE-SENTINEL"
    b62._finalize_result(leaked)
    report = b62.validate_result(leaked, contract)
    assert "forbidden_key:future" in report["errors"]


def test_contract_drift_to_future_model_budget_or_fallback_fails():
    contract = b62.load_contract()
    drifted = deepcopy(contract)
    drifted["input"]["future_outcome_access_before_prediction_freeze_required"] = 1
    assert "input_boundary" in b62.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["model"]["name"] = "qwen3.5:27b"
    assert "model" in b62.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["fairness"]["prediction_call_num_predict"] = 512
    assert "call_budget" in b62.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["execution"]["retry_or_condition_fallback_allowed"] = True
    assert "execution" in b62.validate_contract(drifted)["errors"]


def test_preexisting_prediction_state_fails_before_model_call(monkeypatch, tmp_path):
    monkeypatch.setattr(b62, "ROOT", tmp_path)
    contract = b62.load_contract()
    state = tmp_path / contract["execution"]["result_state_root"]
    state.mkdir(parents=True)
    with pytest.raises(b62.B62ExecutionError, match="already consumed"):
        b62._fresh_state_root(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b62.validate_implementation_freeze() == {
        "valid": True,
        "model_call_count_at_freeze": 0,
        "future_outcome_access_count_at_freeze": 0,
    }
