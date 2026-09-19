from copy import deepcopy
import json

import pytest

import p3_b65_bounded_joint_prediction_interface as b65


def artifact():
    return {
        "cues": [
            {"start_seconds": 3001.0, "end_seconds": 3002.0, "text": "今日はどうしようかな。"},
            {"start_seconds": 3175.0, "end_seconds": 3176.0, "text": "じゃ、次いくか。"},
        ]
    }


def joint_value(condition="BASELINE_LITERAL"):
    labels = b65.load_contract()["target"]["candidate_behavior_labels"]
    probabilities = {label: 0.1 for label in labels}
    probabilities["acknowledge_then_continue"] = 0.5
    return {
        "state": {
            "observed_literal": "次へ進むと発言した。",
            "interpretation": "話題を続ける。" if condition == "BASELINE_LITERAL" else "迷いを切り替えて次へ進む。",
            "alternative": "不明。",
            "confidence": 0.7,
        },
        "probabilities": probabilities,
        "predicted_next_content": "次の話題を始めると思う。",
        "brief_evidence": "直前に次へ進むと発言している。",
    }


class FakeProvider:
    def __init__(self):
        self.records = []

    def __call__(self, *, model, prompt, options):
        condition = json.loads(prompt)["condition"]
        self.records.append(
            {
                "call_index": len(self.records) + 1,
                "status": "completed",
                "prompt_sha256": b65.sha256_bytes(prompt.encode("utf-8")),
                "response_sha256": "b" * 64,
                "model_requested": model,
                "model_reported": model,
                "num_predict": options["num_predict"],
                "prompt_tokens": 120,
                "completion_tokens": 90,
                "latency_seconds": 0.25,
            }
        )
        return {"text": json.dumps(joint_value(condition), ensure_ascii=False)}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.body, ensure_ascii=False).encode("utf-8")


def test_contract_freezes_new_interface_and_future_boundary():
    assert b65.validate_contract() == {"valid": True, "errors": []}
    contract = b65.load_contract()
    assert contract["fairness"]["model_call_count_exact"] == 2
    assert contract["fairness"]["completion_token_ceiling_each_condition"] == 512
    assert contract["joint_output_contract"]["same_json_schema_both_conditions"] is True
    assert contract["execution"]["retry_or_condition_fallback_allowed"] is False
    assert contract["input"]["future_outcome_access_before_complete_prediction_pair_required"] == 0
    assert all(contract["denied_actions"].values())


def test_prompts_change_condition_rules_but_keep_context_labels_and_output_contract():
    contract = b65.load_contract()
    baseline = json.loads(b65.joint_prompt("BASELINE_LITERAL", artifact(), contract))
    system = json.loads(b65.joint_prompt("SYSTEM_PRAGMATIC_STATE", artifact(), contract))
    assert baseline["observable_context"] == system["observable_context"]
    assert baseline["candidate_behavior_labels"] == system["candidate_behavior_labels"]
    assert baseline["output_contract"] == system["output_contract"]
    assert baseline["condition"] != system["condition"]
    assert "must not infer" in baseline["state_rule"]
    assert "falsifiable pragmatic" in system["state_rule"]


def test_joint_schema_is_bounded_and_condition_independent():
    labels = b65.load_contract()["target"]["candidate_behavior_labels"]
    schema = b65.joint_schema(labels)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["state"]["properties"]["interpretation"]["maxLength"] == 120
    assert schema["properties"]["predicted_next_content"]["maxLength"] == 160
    probability_schema = schema["properties"]["probabilities"]
    assert probability_schema["required"] == labels
    assert probability_schema["additionalProperties"] is False


def test_parse_joint_output_hashes_then_discards_state_text():
    contract = b65.load_contract()
    parsed = b65.parse_joint_output(
        json.dumps(joint_value(), ensure_ascii=False), "BASELINE_LITERAL", contract
    )
    assert parsed["condition"] == "BASELINE_LITERAL"
    assert parsed["selected_behavior"] == "acknowledge_then_continue"
    assert parsed["state_persisted"] is False
    assert parsed["raw_prompt_or_response_persisted"] is False
    assert "state" not in parsed
    assert len(parsed["state_sha256"]) == 64


def test_parse_joint_output_rejects_probability_and_length_drift():
    contract = b65.load_contract()
    invalid = joint_value()
    invalid["probabilities"]["acknowledge_then_continue"] = 0.6
    with pytest.raises(Exception, match="probability sum"):
        b65.parse_joint_output(json.dumps(invalid, ensure_ascii=False), "BASELINE_LITERAL", contract)
    invalid = joint_value()
    invalid["state"]["interpretation"] = "長" * 121
    with pytest.raises(Exception, match="state interpretation"):
        b65.parse_joint_output(json.dumps(invalid, ensure_ascii=False), "BASELINE_LITERAL", contract)


def test_provider_sends_same_schema_think_false_and_accounts_at_boundary():
    captured = []

    def opener(http_request, timeout):
        captured.append(json.loads(http_request.data.decode("utf-8")))
        return FakeResponse(
            {
                "response": json.dumps(joint_value(), ensure_ascii=False),
                "prompt_eval_count": 111,
                "eval_count": 88,
                "model": "qwen3.5:9b",
            }
        )

    contract = b65.load_contract()
    provider = b65.JointSchemaOllamaProvider(
        endpoint="http://local.invalid",
        timeout=10,
        labels=contract["target"]["candidate_behavior_labels"],
        opener=opener,
    )
    prompt = b65.joint_prompt("BASELINE_LITERAL", artifact(), contract)
    response = provider(model="qwen3.5:9b", prompt=prompt, options=contract["model"]["options"])
    assert response["text"]
    assert captured[0]["think"] is False
    assert captured[0]["format"] == b65.joint_schema(contract["target"]["candidate_behavior_labels"])
    assert captured[0]["options"]["num_predict"] == 512
    assert provider.records[0]["status"] == "completed"
    assert provider.records[0]["prompt_tokens"] == 111
    assert provider.records[0]["completion_tokens"] == 88


def test_two_fake_calls_freeze_pair_without_future_or_state_text(monkeypatch, tmp_path):
    monkeypatch.setattr(b65, "ROOT", tmp_path)
    monkeypatch.setattr(b65, "validate_implementation_freeze", lambda: {"valid": True})
    monkeypatch.setattr(b65, "validate_contract", lambda: {"valid": True, "errors": []})
    monkeypatch.setattr(b65.b62, "load_public_context", lambda _: artifact())
    provider = FakeProvider()
    result = b65.execute_joint_predictions(provider)
    assert b65.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_pair_frozen"
    assert result["model_call_count"] == 2
    assert result["future_outcome_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert all("state" not in row for row in result["predictions"])
    assert [row["condition"] for row in result["predictions"]] == [
        "BASELINE_LITERAL",
        "SYSTEM_PRAGMATIC_STATE",
    ]


def test_contract_drift_in_model_budget_schema_or_future_fails():
    contract = b65.load_contract()
    drifted = deepcopy(contract)
    drifted["model"]["name"] = "qwen3.5:27b"
    assert "model" in b65.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["model"]["options"]["num_predict"] = 768
    assert "model" in b65.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["joint_output_contract"]["interpretation_max_characters"] = 240
    assert "output_contract" in b65.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["input"]["future_outcome_access_before_complete_prediction_pair_required"] = 1
    assert "input_boundary" in b65.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(b65, "ROOT", tmp_path)
    contract = b65.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(Exception, match="already consumed"):
        b65._fresh_state_root(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b65.validate_implementation_freeze() == {
        "valid": True,
        "model_call_count_at_freeze": 0,
        "future_outcome_access_count_at_freeze": 0,
    }
