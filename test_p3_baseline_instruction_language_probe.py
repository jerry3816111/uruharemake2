from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_baseline_instruction_language_probe as probe_module
from p3_product_comparison import P3ContractError
from p3_baseline_instruction_language_probe import (
    ARMS,
    _arm_config,
    build_preflight,
    load_probe,
)


ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "configs/p3_baseline_instruction_language_probe_v1.json"


def test_probe_changes_only_instruction_text_and_is_non_authorizing():
    probe = load_probe(PROBE)
    english = _arm_config(probe, "english_instructions")
    japanese = _arm_config(probe, "japanese_instructions")
    assert tuple(probe["arms"]) == ARMS
    assert english["_design"]["baselines"] != japanese["_design"]["baselines"]
    for key in english["_design"]:
        if key != "baselines":
            assert english["_design"][key] == japanese["_design"][key]
    assert english["generation"] == japanese["generation"]
    assert english["transport"] == japanese["transport"]
    assert english["_canary"] == japanese["_canary"]
    assert probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_probe_source_is_not_present_in_developer_manifest():
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


def test_probe_rejects_english_arm_drift(tmp_path, monkeypatch):
    raw = json.loads(PROBE.read_text(encoding="utf-8"))
    raw["arms"]["english_instructions"]["direct_instruction"] += " changed"
    path = tmp_path / "configs" / PROBE.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        probe_module,
        "_verify_ref",
        lambda _repo, _value, expected, _code: ROOT / expected["path"],
    )
    with pytest.raises(P3ContractError) as error:
        load_probe(path)
    assert error.value.code == "p3_b11_english_arm_drift"


def test_probe_preflight_is_zero_call_and_ready():
    preflight = build_preflight(PROBE)
    assert preflight["phase"] == "P3-B11"
    assert preflight["status"] == "ready_for_instruction_language_probe_review"
    assert preflight["real_model_calls"] == preflight["network_calls"] == 0
    assert preflight["developer_case_accessed"] == 0
    assert preflight["annotations_accessed"] == 0
    assert all(preflight["checks"].values())
