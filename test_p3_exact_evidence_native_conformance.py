from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_exact_evidence_native_conformance as probe
import p3_exact_evidence_judge_contract as exact
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_exact_evidence_native_conformance_v1.json"


def response_for(item):
    value = exact._valid(item)
    if not item["annotation"]["correction_eligible"]:
        value["scores"]["A"]["correction"] = None
        value["scores"]["B"]["correction"] = None
    value["scores"]["A"]["evidence_turn_ids"] = [item["turn_id"]]
    value["scores"]["B"]["evidence_turn_ids"] = [item["turn_id"]]
    return {
        "content": json.dumps(value, ensure_ascii=False),
        "prompt_tokens": 220,
        "completion_tokens": 120,
        "wall_seconds": 1.25,
        "model": "qwen3.5:9b",
        "finish_reason": "stop",
        "real_model_calls": 1,
        "network_calls": 1,
    }


def test_config_builds_synthetic_ab_ba_with_exact_slot_swaps():
    config = probe.load_config(CONFIG)
    items = probe.build_items(config)
    assert [item["order"] for item in items] == ["AB", "BA"]
    assert items[0]["anonymous_replies"]["A"] == items[1]["anonymous_replies"]["B"]
    assert items[0]["anonymous_replies"]["B"] == items[1]["anonymous_replies"]["A"]
    assert all(item["visible_history"] == [] for item in items)
    assert all(item["turn_id"] == "p3-b32-synthetic-u1" for item in items)


def test_native_body_uses_frozen_keyed_exact_evidence_schema():
    config = probe.load_config(CONFIG)
    for item in probe.build_items(config):
        body = exact.native_body(config, item)
        schema = body["format"]
        assert schema["properties"]["scores"]["required"] == ["A", "B"]
        assert "oneOf" not in json.dumps(schema)
        for slot in ("A", "B"):
            properties = schema["properties"]["scores"]["properties"][slot]["properties"]
            assert properties["reply_slot"]["enum"] == [slot]
            assert properties["reply_quote"]["enum"] == [item["anonymous_replies"][slot]]
        assert body["options"] == {
            "temperature": 0,
            "seed": 20260909,
            "top_p": 1,
            "num_ctx": 8192,
            "num_predict": 384,
        }


def test_preflight_is_zero_call_and_never_opens_case_or_annotation(monkeypatch):
    monkeypatch.setattr(probe, "_ollama_model_metadata", lambda model: {
        "model": model,
        "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "template_present": True,
        "modelfile_sha256": "fake",
        "metadata_command_calls": 1,
        "generation_calls": 0,
    })
    monkeypatch.setattr(probe, "ollama_version", lambda: "0.33.3")
    result = probe.build_preflight(CONFIG)
    assert result["status"] == "ready_for_exact_evidence_native_conformance_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["developer_case_accessed"] == result["annotation_files_accessed"] == 0
    assert result["b29_regraded"] is False
    assert all(result["checks"].values())


def test_two_call_fake_run_is_exact_accounted_and_not_a_quality_result(monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "verify_release", lambda *_args: None)
    release = tmp_path / "release.json"
    preflight = tmp_path / "preflight.json"
    release.write_text("{}", encoding="utf-8")
    preflight.write_text("{}", encoding="utf-8")
    result = probe.run_probe(
        CONFIG,
        release,
        preflight,
        tmp_path / "checkpoints",
        transport=lambda _config, item: response_for(item),
    )
    assert result["status"] == "exact_evidence_native_conformance_pass"
    assert result["judge_calls"] == 2
    assert result["judge_prompt_tokens"] == 440
    assert result["judge_completion_tokens"] == 240
    assert result["checkpoint_evidence"]["declared_invocation_intents"] == 2
    assert result["checkpoint_evidence"]["completed_calls"] == 2
    assert result["quality_result"] == "not_evaluated"
    assert result["b29_regraded"] is False
    assert all(result["checks"].values())


def test_validation_failure_stops_without_retry_and_retains_provider_usage(monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "verify_release", lambda *_args: None)
    release = tmp_path / "release.json"
    preflight = tmp_path / "preflight.json"
    release.write_text("{}", encoding="utf-8")
    preflight.write_text("{}", encoding="utf-8")
    calls = []

    def bad(_config, item):
        calls.append(item["item_id"])
        response = response_for(item)
        value = json.loads(response["content"])
        value["scores"]["A"]["reply_quote"] = "shortened"
        response["content"] = json.dumps(value, ensure_ascii=False)
        return response

    result = probe.run_probe(
        CONFIG,
        release,
        preflight,
        tmp_path / "checkpoints",
        transport=bad,
    )
    assert result["status"] == "exact_evidence_native_conformance_failed_retained"
    assert len(calls) == 1
    assert result["failure"]["contract_code"] == "p3_b30_exact_reply_evidence_invalid"
    assert result["failure"]["retry_performed"] is False
    assert result["checkpoint_evidence"]["declared_invocation_intents"] == 1
    assert result["checkpoint_evidence"]["post_transport_failures"] == 1
    assert result["judge_calls"] == 1


def test_existing_checkpoint_root_refuses_before_any_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "verify_release", lambda *_args: None)
    root = tmp_path / "checkpoints"
    root.mkdir()
    with pytest.raises(P3ContractError) as exc:
        probe.run_probe(
            CONFIG,
            tmp_path / "release.json",
            tmp_path / "preflight.json",
            root,
            transport=lambda _config, item: response_for(item),
        )
    assert exc.value.code == "p3_b32_checkpoint_root_exists"
