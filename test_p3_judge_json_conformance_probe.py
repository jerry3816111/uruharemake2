from __future__ import annotations

import json
from pathlib import Path

import p3_judge_json_conformance_probe as probe


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_judge_json_conformance_probe_v1.json"


def test_probe_has_one_synthetic_prompt_and_only_format_changes():
    config = probe.load_config(CONFIG)
    item = probe.synthetic_item(config)
    assert item["visible_history"] == []
    assert item["turn_id"] == "synthetic-u1"
    assert config["response_formats"]["json_object"] == {"type": "json_object"}
    assert config["response_formats"]["json_schema"]["type"] == "json_schema"
    assert "p3-smoke" not in json.dumps(item, ensure_ascii=False)


def test_post_transport_failure_is_fully_accountable(tmp_path):
    response = {
        "content": "truncated", "prompt_tokens": 620, "completion_tokens": 384,
        "wall_seconds": 23.6, "real_model_calls": 1, "network_calls": 1,
        "finish_reason": "length",
    }
    record = probe.failure_record("json_object", ValueError("invalid"), response)
    probe._write_checkpoint(tmp_path / "failure.json", record)
    evidence = probe.summarize_checkpoint_evidence(tmp_path)
    assert record["response_received"] is True
    assert record["raw_content_sha256"]
    assert evidence["post_transport_failures"] == 1
    assert evidence["provider_call_evidence"] == 1
    assert evidence["network_call_evidence"] == 1
    assert evidence["provider_prompt_tokens_observed"] == 620
    assert evidence["provider_completion_tokens_observed"] == 384


def test_preflight_has_zero_generation_and_no_case_data(monkeypatch):
    monkeypatch.setattr(probe, "_ollama_model_metadata", lambda model: {
        "model": model, "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "template_present": True, "modelfile_sha256": "fake",
        "metadata_command_calls": 1, "generation_calls": 0,
    })
    result = probe.build_preflight(CONFIG)
    assert result["status"] == "ready_for_judge_conformance_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["developer_case_accessed"] == result["annotation_turns_accessed"] == 0
