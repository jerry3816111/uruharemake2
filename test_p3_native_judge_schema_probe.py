from __future__ import annotations

from pathlib import Path

import p3_native_judge_schema_probe as probe
from p3_case03_proxy_grade import build_messages
from p3_judge_json_conformance_probe import synthetic_item


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_native_judge_schema_probe_v1.json"


def test_native_body_uses_direct_schema_and_frozen_generation_options():
    config = probe.load_config(CONFIG)
    item = synthetic_item(config["_parent"])
    body = probe.native_body(config, build_messages(item))
    assert body["format"] == probe.schema(config)
    assert "type" in body["format"] and "json_schema" not in body["format"]
    assert body["options"] == {
        "temperature": 0, "seed": 20260909, "top_p": 1,
        "num_ctx": 8192, "num_predict": 384,
    }
    assert body["stream"] is False and body["think"] is False


def test_preflight_is_zero_call_and_same_synthetic_prompt(monkeypatch):
    monkeypatch.setattr(probe, "_ollama_model_metadata", lambda model: {
        "model": model, "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "template_present": True, "modelfile_sha256": "fake",
        "metadata_command_calls": 1, "generation_calls": 0,
    })
    monkeypatch.setattr(probe, "ollama_version", lambda: "0.33.3")
    result = probe.build_preflight(CONFIG)
    assert result["status"] == "ready_for_native_schema_review"
    assert result["prompt_sha256"] == "671b1cc82c129f3c6f0b35905631c6083c2d8f8ceaf137826ae51d59923ad8d3"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["developer_case_accessed"] == result["annotation_turns_accessed"] == 0


def test_failure_record_remains_accountable(tmp_path):
    response = {
        "content": "bad", "prompt_tokens": 555, "completion_tokens": 384,
        "wall_seconds": 20.0, "real_model_calls": 1, "network_calls": 1,
        "finish_reason": "length",
    }
    probe._write_checkpoint(tmp_path / "failure.json", probe.failure_record(ValueError("bad"), response))
    evidence = probe.summarize_checkpoint_evidence(tmp_path)
    assert evidence["post_transport_failures"] == 1
    assert evidence["provider_call_evidence"] == evidence["network_call_evidence"] == 1
