from copy import deepcopy
import json

import pytest

import p3_c1_controlled_context_flip_lane as c1
import p3_c2_controlled_context_flip_execution as c2


class MockProvider:
    def __init__(self, *, invalid_at=None):
        self.calls = []
        self.invalid_at = invalid_at

    def invoke(self, *, call, model, prompt, schema, options):
        self.calls.append(deepcopy(call))
        payload = json.loads(prompt)
        item = payload["common_observable_input"]
        literal = item["variant_id"] == "literal_control"
        probabilities = (
            {"LITERAL_READING": 9, "PRAGMATIC_READING": 0.5, "UNCERTAIN": 0.5}
            if literal
            else {"LITERAL_READING": 0.5, "PRAGMATIC_READING": 8, "UNCERTAIN": 1.5}
        )
        value = {
            "probabilities": probabilities,
            "visible_reply_ja": (
                "それなら、そのまま受け取ってよさそうだな。"
                if literal
                else "その言い方だと、少し引っかかってることもありそうだな。"
            ),
            "brief_evidence_anchor_ids": [item["evidence_anchors"][0]["id"]],
        }
        if call["condition"] == "SYSTEM_PRAGMATIC_STATE":
            value["pragmatic_state"] = {
                "literal_content": "表面の発話内容を保持する。",
                "communicative_intent": "文脈に沿う候補を仮置きする。",
                "affect_or_stance": "確認できる姿勢だけを扱う。",
                "relationship_signal": "関係上の合図は断定しない。",
                "implicit_need_or_action_tendency": "必要なら低圧に応じる。",
                "alternative_hypothesis": "別の読みも残す。",
                "unknowns": "音声特徴は利用できない。",
                "confidence": 0.7,
            }
        if self.invalid_at == call["call_index"]:
            value["visible_reply_ja"] = "not Japanese"
        text = json.dumps(value, ensure_ascii=False)
        return {
            "text": text,
            "record": {
                "call_index": call["call_index"],
                "stage": call["stage"],
                "pair_id": call["pair_id"],
                "variant_id": call["variant_id"],
                "condition": call["condition"],
                "status": "completed",
                "model_requested": model,
                "model_reported": model,
                "prompt_sha256": c2.sha256_bytes(prompt.encode()),
                "schema_sha256": c2.sha256_bytes(c2.canonical_json(schema).encode()),
                "input_sha256": call["input_sha256"],
                "num_predict": options["num_predict"],
                "prompt_tokens": 100,
                "completion_tokens": 80,
                "latency_seconds": 0.01,
                "raw_prompt_or_response_persisted": False,
            },
        }


@pytest.fixture(autouse=True)
def _freeze_is_assumed_valid_for_runner_unit_tests(monkeypatch, tmp_path):
    freeze_path = tmp_path / "synthetic_freeze.json"
    freeze_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(c2, "FREEZE_PATH", freeze_path)
    monkeypatch.setattr(
        c2,
        "validate_implementation_freeze",
        lambda **kwargs: {"valid": True, "p3_c_model_calls_at_freeze": 0},
    )


def test_contract_keeps_holdout_locked_and_baseline_strong():
    assert c2.validate_contract() == {"valid": True, "errors": []}
    contract = c2.load_contract()
    assert contract["execution_plan"]["holdout_item_or_target_access_allowed"] is False
    assert contract["execution_plan"]["retry_or_fallback_allowed"] is False
    assert contract["execution_plan"]["total_model_call_ceiling"] == 32
    assert all(contract["denied_actions"].values())
    assert c1.load_contract()["fairness"]["baseline_may_reason_normally"] is True


def test_execution_plan_is_balanced_and_smoke_precedes_dev():
    plan = c2.build_execution_plan()
    assert len(plan) == 32
    assert [row["call_index"] for row in plan] == list(range(1, 33))
    assert [row["stage"] for row in plan[:8]] == ["train_format_smoke"] * 8
    assert [row["stage"] for row in plan[8:]] == ["dev_complete"] * 24
    assert {row["pair_id"] for row in plan[:8]} == {"train_zh_01", "train_en_02"}
    assert all(not row["pair_id"].startswith("holdout") for row in plan)
    for stage in ("train_format_smoke", "dev_complete"):
        conditions = [row["condition"] for row in plan if row["stage"] == stage]
        assert conditions.count("BASELINE_DIRECT") == conditions.count(
            "SYSTEM_PRAGMATIC_STATE"
        )


def test_prompt_keeps_common_input_equal_and_never_contains_targets():
    item = c1.build_prediction_packet("dev")["items"][0]
    baseline = json.loads(c2.prompt_for("BASELINE_DIRECT", item))
    system = json.loads(c2.prompt_for("SYSTEM_PRAGMATIC_STATE", item))
    assert baseline["common_observable_input"] == system["common_observable_input"]
    serialized = json.dumps([baseline, system], ensure_ascii=False)
    assert "expected_distribution" not in serialized
    assert "expected_top1" not in serialized
    assert "Acoustic evidence is unavailable" in serialized
    assert "pragmatic_state" not in baseline["output_contract"]
    assert "pragmatic_state" in system["output_contract"]


def test_provider_schemas_share_outputs_and_only_system_adds_state():
    anchors = ["a1", "a2"]
    baseline = c2.output_schema("BASELINE_DIRECT", anchors)
    system = c2.output_schema("SYSTEM_PRAGMATIC_STATE", anchors)
    assert baseline["required"] == [
        "probabilities",
        "visible_reply_ja",
        "brief_evidence_anchor_ids",
    ]
    assert system["required"] == baseline["required"] + ["pragmatic_state"]
    assert baseline["properties"]["brief_evidence_anchor_ids"]["items"]["enum"] == anchors
    assert system["properties"]["pragmatic_state"]["additionalProperties"] is False


def test_parser_uses_same_b70_normalization_and_rejects_non_japanese():
    item = c1.build_prediction_packet("dev")["items"][0]
    provider = MockProvider()
    call = c2.build_execution_plan()[8]
    response = provider.invoke(
        call=call,
        model="qwen3.5:9b",
        prompt=c2.prompt_for(call["condition"], item),
        schema=c2.output_schema(call["condition"], ["a1", "a2"]),
        options=c2.load_contract()["provider"]["options"],
    )
    prediction, normalization = c2.parse_output(
        response["text"], call["condition"], item
    )
    assert sum(prediction["probabilities"].values()) == pytest.approx(1.0)
    assert normalization["normalization_applied"] is True
    broken = json.loads(response["text"])
    broken["visible_reply_ja"] = "I understand."
    with pytest.raises(c2.C2ContractError, match="language"):
        c2.parse_output(json.dumps(broken), call["condition"], item)


def test_mock_full_execution_completes_32_calls_scores_dev_and_reuses_result(
    tmp_path,
):
    provider = MockProvider()
    result = c2.execute_once(provider, state_root=tmp_path / "state")
    assert result["status"] == "dev_batch_complete"
    assert result["model_call_count"] == 32
    assert result["validated_prediction_count"] == 32
    assert result["smoke_prediction_count"] == 8
    assert result["dev_prediction_count"] == 24
    assert result["actual_prompt_tokens_total"] == 3200
    assert result["actual_completion_tokens_total"] == 2560
    assert result["holdout_input_access_count"] == 0
    assert result["holdout_target_access_count"] == 0
    assert result["retry_count"] == 0
    assert result["dev_score"]["conditions"]["BASELINE_DIRECT"][
        "paired_context_flip_top1_accuracy"
    ] == 1.0
    assert c2._result_validation(result, c2.load_contract()) == []
    second = MockProvider()
    reused = c2.execute_once(second, state_root=tmp_path / "state")
    assert reused == result
    assert second.calls == []


def test_invalid_second_response_is_terminal_and_never_retried(tmp_path):
    provider = MockProvider(invalid_at=2)
    result = c2.execute_once(provider, state_root=tmp_path / "state")
    assert result["status"] == "terminal_incomplete"
    assert result["failure_category"] == "language"
    assert result["model_call_count"] == 2
    assert result["validated_prediction_count"] == 1
    assert len(provider.calls) == 2
    assert result["retry_count"] == 0
    assert result["holdout_input_access_count"] == 0
    second = MockProvider()
    reused = c2.execute_once(second, state_root=tmp_path / "state")
    assert reused == result
    assert second.calls == []


def test_state_files_never_persist_raw_prompt_or_response(tmp_path):
    result = c2.execute_once(MockProvider(), state_root=tmp_path / "state")
    assert result["status"] == "dev_batch_complete"
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "state").rglob("*.json")
    )
    assert "common_observable_input" not in persisted
    assert '"raw_prompt"' not in persisted
    assert '"raw_response"' not in persisted
    assert '"raw_prompt_or_response_persisted": true' not in persisted
