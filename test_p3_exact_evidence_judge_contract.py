from __future__ import annotations

import json

import jsonschema
import pytest

import p3_exact_evidence_judge_contract as contract
from p3_product_comparison import P3ContractError


def _item(order="AB", correction=True):
    first = "その話は置いておこう。猫のことを思って。"
    second = "猫が箱を落としたの、想像したらちょっと笑う。"
    replies = {"A": first, "B": second} if order == "AB" else {"A": second, "B": first}
    return {
        "item_id": f"test:{order}", "turn_id": "u1", "order": order,
        "visible_history": [], "current_input": "ただ笑ってほしかっただけ。",
        "annotation": {"correction_eligible": correction},
        "slot_to_condition": {"A": "one", "B": "two"},
        "anonymous_replies": replies,
        "currently_visible_turn_ids": ["u1"],
    }


def _valid(item):
    return {
        "scores": {
            slot: {
                "reply_slot": slot, "attunement": 2, "grounding": 2,
                "correction": 2 if item["annotation"]["correction_eligible"] else None,
                "continuity": 2, "unsupported_assertion": False,
                "japanese_issue": False, "identity_issue": False,
                "evidence_turn_ids": ["u1"],
                "reply_quote": item["anonymous_replies"][slot],
            }
            for slot in ("A", "B")
        },
        "preference": "tie",
    }


def test_schema_binds_each_slot_to_its_entire_reply_without_oneof():
    item = _item()
    schema = contract.judgment_schema(item)
    encoded = json.dumps(schema)
    assert "oneOf" not in encoded
    for slot in ("A", "B"):
        score = schema["properties"]["scores"]["properties"][slot]
        assert score["properties"]["reply_slot"]["enum"] == [slot]
        assert score["properties"]["reply_quote"]["enum"] == [item["anonymous_replies"][slot]]
    jsonschema.validate(_valid(item), schema)


@pytest.mark.parametrize("mutation", ["invented", "other_slot", "shortened", "wrong_slot"])
def test_schema_and_validator_reject_invented_or_misattributed_evidence(mutation):
    item = _item()
    value = _valid(item)
    if mutation == "invented":
        value["scores"]["A"]["reply_quote"] = "存在しない引用"
    elif mutation == "other_slot":
        value["scores"]["A"]["reply_quote"] = item["anonymous_replies"]["B"]
    elif mutation == "shortened":
        value["scores"]["A"]["reply_quote"] = item["anonymous_replies"]["A"][:4]
    else:
        value["scores"]["A"]["reply_slot"] = "B"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, contract.judgment_schema(item))
    with pytest.raises(P3ContractError):
        contract.validate_exact_evidence_judgment(json.dumps(value, ensure_ascii=False), item)


def test_ab_ba_swaps_exact_reply_binding_without_changing_content():
    ab, ba = _item("AB"), _item("BA")
    ab_schema, ba_schema = contract.judgment_schema(ab), contract.judgment_schema(ba)
    ab_a = ab_schema["properties"]["scores"]["properties"]["A"]["properties"]["reply_quote"]["enum"]
    ba_b = ba_schema["properties"]["scores"]["properties"]["B"]["properties"]["reply_quote"]["enum"]
    assert ab_a == ba_b
    assert ab["anonymous_replies"]["A"] == ba["anonymous_replies"]["B"]


def test_correction_eligibility_and_frozen_validator_semantics_remain():
    eligible, ineligible = _item(correction=True), _item(correction=False)
    assert contract.judgment_schema(eligible)["properties"]["scores"]["properties"]["A"]["properties"]["correction"] == {
        "type": "integer", "enum": [0, 1, 2]
    }
    assert contract.judgment_schema(ineligible)["properties"]["scores"]["properties"]["A"]["properties"]["correction"] == {"type": "null"}
    normalized = contract.validate_exact_evidence_judgment(json.dumps(_valid(eligible), ensure_ascii=False), eligible)
    assert [score["reply_slot"] for score in normalized["scores"]] == ["A", "B"]
    assert all(score["correction"] == 2 for score in normalized["scores"])


def test_prompt_and_native_body_request_exact_keyed_evidence():
    item = _item()
    messages = contract.build_exact_evidence_messages(item)
    assert "entire anonymous reply exactly" in messages[0]["content"]
    required = json.loads(messages[1]["content"])["required_schema"]["scores"]
    assert set(required) == {"A", "B"}
    config = {"judge": {
        "model": "qwen3.5:9b", "think": False, "temperature": 0,
        "seed": 20260909, "top_p": 1, "num_ctx": 8192,
        "max_completion_tokens": 384,
    }}
    body = contract.native_body(config, item)
    assert body["messages"] == messages
    assert body["format"] == contract.judgment_schema(item)
    assert body["options"]["num_predict"] == 384


def test_preflight_is_offline_prospective_and_does_not_reopen_b29():
    result = contract.build_preflight()
    assert result["status"] == "ready_for_prospective_exact_evidence_freeze"
    assert all(result["checks"].values())
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["b29_retried_or_modified"] is False
