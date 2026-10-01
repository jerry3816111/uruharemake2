from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_private_scratch_carrier_probe as probe_module
from p3_private_scratch_carrier_probe import (
    _messages,
    build_preflight,
    load_probe,
)
from p3_product_comparison import P3ContractError, canonical_sha256


ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "configs/p3_private_scratch_carrier_probe_v1.json"


def test_carrier_probe_binds_locked_control_and_is_non_authorizing():
    probe = load_probe(PROBE)
    result = json.loads(
        (ROOT / "analysis/p3_b11_instruction_language_probe_result_2026-09-15.json").read_text(
            encoding="utf-8"
        )
    )
    control = result["arms"]["japanese_instructions"]["conditions"][
        "full_history_deliberate"
    ]

    assert probe["locked_control"]["draft"] == control["calls"][0]["content"]
    assert probe["locked_control"]["critique"] == control["calls"][1]["content"] == ""
    assert probe["locked_control"]["final"] == control["final"]["content"]
    assert probe["locked_control"]["draft_sha256"] == canonical_sha256(
        control["calls"][0]["content"]
    )
    assert probe["execution_boundary"]["provider_calls_exact"] == 2
    assert probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_carrier_probe_source_is_synthetic_and_not_in_developer_manifest():
    probe = load_probe(PROBE)
    developer = json.loads(
        (ROOT / "datasets/p3_developer_smoke_source_v1.json").read_text(encoding="utf-8")
    )
    source_hashes = {
        turn["content_sha256"]
        for case in developer["cases"]
        for turn in case["turns"]
    }

    assert probe["source"]["content_sha256"] not in source_hashes
    assert probe["source"]["developer_case_source"] is False
    assert probe["source"]["annotations_exist"] is False


def test_carrier_probe_uses_labeled_user_scratch_for_both_new_stages():
    probe = load_probe(PROBE)
    critique_messages = _messages(probe, "critique")
    revise_messages = _messages(probe, "revise", "語調を自然に直す。")

    assert [message["role"] for message in critique_messages] == ["system", "user", "user"]
    assert [message["role"] for message in revise_messages] == ["system", "user", "user"]
    assert critique_messages[-1]["content"].startswith("内部の返答案:\n")
    assert "内部の修正点:\n語調を自然に直す。" in revise_messages[-1]["content"]
    assert probe["source"]["content"] == critique_messages[1]["content"]
    assert probe["source"]["content"] == revise_messages[1]["content"]


def test_carrier_probe_rejects_locked_control_drift(tmp_path, monkeypatch):
    raw = json.loads(PROBE.read_text(encoding="utf-8"))
    raw["locked_control"]["final"] = "別の結果"
    path = tmp_path / "configs" / PROBE.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        probe_module,
        "_ref",
        lambda _repo, _value, expected, _code: ROOT / expected["path"],
    )

    with pytest.raises(P3ContractError) as error:
        load_probe(path)

    assert error.value.code == "p3_b13_locked_control_mismatch"


def test_carrier_probe_preflight_is_ready_without_calls():
    result = build_preflight(PROBE)

    assert result["phase"] == "P3-B13"
    assert result["status"] == "ready_for_private_scratch_carrier_review"
    assert result["critique_offline_prompt_tokens"] > 0
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["developer_case_accessed"] == result["annotations_accessed"] == 0
    assert all(result["checks"].values())
