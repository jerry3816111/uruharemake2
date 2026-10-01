from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_case03_proxy_grade as grade
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case03_proxy_grade_v1.json"


def test_build_items_is_exact_blind_ab_ba_for_four_locked_turns():
    config = grade.load_config(CONFIG)
    items = grade.build_items(config)
    assert len(items) == 8
    assert [x["order"] for x in items] == ["AB", "BA"] * 4
    for ab, ba in zip(items[::2], items[1::2]):
        assert ab["turn_id"] == ba["turn_id"]
        assert ab["anonymous_replies"]["A"] == ba["anonymous_replies"]["B"]
        assert ab["anonymous_replies"]["B"] == ba["anonymous_replies"]["A"]
        assert "product_system" not in json.dumps(grade.build_messages(ab), ensure_ascii=False)
        assert "full_history_direct" not in json.dumps(grade.build_messages(ab), ensure_ascii=False)


def _valid(item):
    correction = 2 if item["annotation"]["correction_eligible"] else None
    visible = item["currently_visible_turn_ids"][-1]
    return {
        "scores": [
            {"reply_slot": slot, "attunement": 2, "grounding": 2, "correction": correction,
             "continuity": 2, "unsupported_assertion": False, "japanese_issue": False,
             "identity_issue": False, "evidence_turn_ids": [visible],
             "reply_quote": item["anonymous_replies"][slot][:2]}
            for slot in ("A", "B")
        ],
        "preference": "tie",
    }


def test_validator_accepts_frozen_shape_and_rejects_nonexact_quote():
    item = grade.build_items(grade.load_config(CONFIG))[0]
    value = _valid(item)
    assert grade.validate_judgment(json.dumps(value, ensure_ascii=False), item)["preference"] == "tie"
    value["scores"][0]["reply_quote"] = "not in locked reply"
    with pytest.raises(P3ContractError, match="p3_b17_quote_invalid"):
        grade.validate_judgment(json.dumps(value, ensure_ascii=False), item)


def test_correction_is_null_only_when_not_eligible():
    items = grade.build_items(grade.load_config(CONFIG))
    ineligible = items[0]
    value = _valid(ineligible)
    value["scores"][0]["correction"] = 1
    with pytest.raises(P3ContractError, match="p3_b17_correction_applicability_invalid"):
        grade.validate_judgment(json.dumps(value, ensure_ascii=False), ineligible)
    eligible = next(x for x in items if x["annotation"]["correction_eligible"])
    value = _valid(eligible)
    value["scores"][0]["correction"] = None
    with pytest.raises(P3ContractError, match="p3_b17_correction_applicability_invalid"):
        grade.validate_judgment(json.dumps(value, ensure_ascii=False), eligible)


def test_summary_maps_reversed_slots_back_to_conditions():
    config = grade.load_config(CONFIG)
    items = grade.build_items(config)[:2]
    rows = []
    for item in items:
        value = _valid(item)
        product_slot = next(k for k, v in item["slot_to_condition"].items() if v == "product_system")
        value["preference"] = product_slot
        for score in value["scores"]:
            score["attunement"] = 2 if score["reply_slot"] == product_slot else 0
        rows.append({"turn_id": item["turn_id"], "slot_to_condition": item["slot_to_condition"], "judgment": value})
    summary = grade.summarize(rows, config)
    assert summary["mean_scores"]["product_system"]["attunement"] == 2
    assert summary["mean_scores"]["full_history_direct"]["attunement"] == 0
    assert summary["mapped_preference_counts"]["product_system"] == 2
    assert summary["order_agreement_rate"] == 1


def test_locked_output_hash_drift_is_fail_closed():
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    expected = dict(raw["locked_outputs"])
    drifted = dict(expected)
    drifted["sha256"] = "0" * 64
    with pytest.raises(P3ContractError, match="p3_b17_lock_mismatch"):
        grade._ref(ROOT, drifted, expected, "p3_b17_lock_mismatch")


def test_preflight_is_zero_generation_and_one_case_only(monkeypatch):
    monkeypatch.setattr(grade, "_ollama_model_metadata", lambda model: {
        "model": model, "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "template_present": True, "modelfile_sha256": "fake", "metadata_command_calls": 1,
        "generation_calls": 0,
    })
    result = grade.build_preflight(CONFIG)
    assert result["status"] == "ready_for_case03_proxy_grade_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["case03_annotation_turns_used"] == 4
    assert result["other_case_annotations_used"] == 0


def test_post_transport_validation_failure_retains_usage_and_response_hash(tmp_path):
    response = {
        "content": '{"truncated":', "prompt_tokens": 620,
        "completion_tokens": 384, "wall_seconds": 23.6,
        "real_model_calls": 1, "network_calls": 1,
        "finish_reason": "length", "model": "qwen3.5:9b",
    }
    exc = P3ContractError("p3_b17_judge_json_invalid")
    record = grade.build_failure_record("synthetic:AB", exc, response)
    grade._write_checkpoint(tmp_path / "failure.json", record)
    evidence = grade.summarize_checkpoint_evidence(tmp_path)
    assert record["response_received"] is True
    assert record["raw_content_sha256"]
    assert record["finish_reason"] == "length"
    assert evidence["post_transport_failures"] == 1
    assert evidence["provider_call_evidence"] == 1
    assert evidence["network_call_evidence"] == 1
    assert evidence["provider_prompt_tokens_observed"] == 620
    assert evidence["provider_completion_tokens_observed"] == 384
