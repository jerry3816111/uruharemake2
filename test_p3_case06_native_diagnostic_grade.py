from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_case06_native_diagnostic_grade as grade
from p3_case03_proxy_grade import build_messages
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case06_native_diagnostic_grade_v1.json"


def _valid(item):
    correction = 2 if item["annotation"]["correction_eligible"] else None
    return {
        "scores": [
            {
                "reply_slot": slot, "attunement": 2, "grounding": 2,
                "correction": correction, "continuity": 2,
                "unsupported_assertion": False, "japanese_issue": False,
                "identity_issue": False,
                "evidence_turn_ids": [item["currently_visible_turn_ids"][-1]],
                "reply_quote": item["anonymous_replies"][slot][:2],
            }
            for slot in ("A", "B")
        ],
        "preference": "tie",
    }


def test_load_accepts_only_immutable_successful_case06_lock():
    config = grade.load_config(CONFIG)
    assert config["_locked"]["status"] == "case06_outputs_locked"
    assert all(config["_locked"]["checks"].values())
    assert sum(len(row["calls"]) for row in config["_locked"]["product_turns"]) == 1
    assert sum(len(row["calls"]) for row in config["_locked"]["direct_turns"]) == 4


def test_builds_exact_blind_ab_ba_items_from_immutable_replies():
    items = grade.build_items(grade.load_config(CONFIG))
    assert len(items) == 8
    assert [item["order"] for item in items] == ["AB", "BA"] * 4
    for ab, ba in zip(items[::2], items[1::2]):
        assert ab["turn_id"] == ba["turn_id"]
        assert ab["anonymous_replies"]["A"] == ba["anonymous_replies"]["B"]
        assert ab["anonymous_replies"]["B"] == ba["anonymous_replies"]["A"]
        prompt = json.dumps(build_messages(ab), ensure_ascii=False)
        assert "product_system" not in prompt and "full_history_direct" not in prompt


def test_per_item_schema_tracks_case06_correction_eligibility():
    items = grade.build_items(grade.load_config(CONFIG))
    assert [item["annotation"]["correction_eligible"] for item in items[::2]] == [False, True, True, True]
    for item in items:
        correction = grade.judgment_schema(item)["properties"]["scores"]["items"]["properties"]["correction"]
        expected = {"type": "integer", "enum": [0, 1, 2]} if item["annotation"]["correction_eligible"] else {"type": "null"}
        assert correction == expected


def test_native_body_keeps_frozen_schema_and_options():
    config = grade.load_config(CONFIG)
    item = grade.build_items(config)[0]
    body = grade.native_body(config, item, build_messages(item))
    assert body["format"] == grade.judgment_schema(item)
    assert body["options"] == {
        "temperature": 0, "seed": 20260909, "top_p": 1,
        "num_ctx": 8192, "num_predict": 384,
    }
    assert body["stream"] is False and body["think"] is False


def test_preflight_is_zero_call_and_single_case_only(monkeypatch):
    monkeypatch.setattr(grade, "_ollama_model_metadata", lambda model: {
        "model": model,
        "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "template_present": True, "modelfile_sha256": "fake",
        "metadata_command_calls": 1, "generation_calls": 0,
    })
    monkeypatch.setattr(grade, "ollama_version", lambda: "0.33.3")
    result = grade.build_preflight(CONFIG)
    assert result["status"] == "ready_for_case06_native_diagnostic_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["case06_annotation_turns_used"] == 4
    assert result["other_case_annotations_used"] == 0
    assert result["checks"]["single_case_cannot_pass_formal_gate"] is True


def test_run_loop_completes_eight_mocked_native_judgments(monkeypatch, tmp_path):
    release = tmp_path / "release.json"
    preflight = tmp_path / "preflight.json"
    release.write_text("{}", encoding="utf-8")
    preflight.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(grade, "verify_release", lambda *args: None)

    def transport(config, item, messages):
        return {
            "content": json.dumps(_valid(item), ensure_ascii=False),
            "prompt_tokens": 10, "completion_tokens": 20,
            "wall_seconds": 0.25, "model": "qwen3.5:9b",
            "finish_reason": "stop", "real_model_calls": 1, "network_calls": 1,
        }

    result = grade.run_grade(CONFIG, release, preflight, tmp_path / "checkpoints", transport)
    assert result["status"] == "case06_native_diagnostic_grade_complete"
    assert result["judge_calls"] == 8
    assert result["judge_prompt_tokens"] == 80
    assert result["judge_completion_tokens"] == 160
    assert result["summary"]["order_agreement_rate"] == 1
    assert result["formal_quality_gate"] == "not_evaluable_single_developer_case"


def test_run_loop_stops_after_first_invalid_received_response(monkeypatch, tmp_path):
    release = tmp_path / "release.json"
    preflight = tmp_path / "preflight.json"
    release.write_text("{}", encoding="utf-8")
    preflight.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(grade, "verify_release", lambda *args: None)
    calls = 0

    def transport(config, item, messages):
        nonlocal calls
        calls += 1
        return {
            "content": "{", "prompt_tokens": 10, "completion_tokens": 1,
            "wall_seconds": 0.25, "model": "qwen3.5:9b",
            "finish_reason": "stop", "real_model_calls": 1, "network_calls": 1,
        }

    result = grade.run_grade(CONFIG, release, preflight, tmp_path / "checkpoints", transport)
    assert calls == 1
    assert result["status"] == "case06_native_diagnostic_inconclusive_retained"
    assert result["judge_calls"] == 1
    assert result["checkpoint_evidence"]["post_transport_failures"] == 1
    assert result["checks"]["no_retry"] is True


def test_locked_output_hash_drift_fails_closed(tmp_path):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["locked_outputs"]["sha256"] = "0" * 64
    drifted = tmp_path / "configs" / CONFIG.name
    drifted.parent.mkdir()
    drifted.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(P3ContractError):
        grade.load_config(drifted)
