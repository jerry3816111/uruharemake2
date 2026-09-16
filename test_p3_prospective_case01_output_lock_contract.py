from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import p3_case05_dual_condition_output_lock as helper
import p3_prospective_case01_output_lock_contract as contract
from p3_case03_dual_condition_output_lock import append_product_prefix, build_views
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_case01_output_lock_v1.json"


def test_case01_projection_is_first_frozen_source_case_and_annotation_free():
    config = contract.load_config(CONFIG)
    source = config["_source"]
    assert source["case_id"] == contract.CASE_ID
    assert source["family"] == "solution_rejection_and_co-regulated_complaint"
    assert source["language"] == "zh"
    assert source["annotations_included"] is False
    assert source["generation_executed"] is False
    assert config["selection"] == {
        "rule": "first_case_in_immutable_source_order",
        "case_index_zero_based": 0,
        "quality_based_selection": False,
    }
    assert [turn["turn_id"] for turn in source["turns"]] == contract.TURN_IDS


def test_paired_views_share_source_and_do_not_leak_current_product_reply_or_future_turns():
    config = contract.load_config(CONFIG)
    prefix = []
    turns = config["_source"]["turns"]
    for index, turn in enumerate(turns):
        views = build_views(prefix, turn)
        product, direct = views["product_system"], views["full_history_direct"]
        assert product["source_history_sha256"] == direct["source_history_sha256"]
        assert product["input_sha256"] == direct["input_sha256"]
        assert len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        serialized = json.dumps(views, ensure_ascii=False)
        assert "annotation" not in serialized.lower()
        for future in turns[index + 1 :]:
            assert future["content"] not in serialized
        append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")


def test_preflight_is_zero_call_and_binds_b33_b32(monkeypatch):
    monkeypatch.setattr(contract, "_ollama_model_metadata", lambda model: {
        "model": model,
        "digest": contract.MODEL_DIGEST,
        "template_present": True,
        "modelfile_sha256": "fake",
        "metadata_command_calls": 1,
        "generation_calls": 0,
    })
    result = contract.build_preflight(CONFIG)
    assert result["status"] == "ready_for_prospective_case01_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["source_freeze_sha256"] == "c9fb2f5289913e2b460ff01c3650e773c8df0bdd8ff3e03194aab14872e90b90"
    assert result["judge_transport_sha256"] == "8d610c380ed96c3f73075f4042a92a75da292418d8d5338da23a4fd6505e975b"
    assert all(result["checks"].values())


def test_config_rejects_quality_based_selection_and_self_authorized_calls(tmp_path, monkeypatch):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["selection"]["quality_based_selection"] = True
    path = tmp_path / "selection" / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(helper, "_ref", lambda repo, value, expected, code: ROOT / expected["path"])
    with pytest.raises(P3ContractError) as exc:
        contract.load_config(path)
    assert exc.value.code == "p3_b34_selection_drift"

    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["execution_boundary"]["real_model_calls_authorized_by_this_config"] = True
    path = tmp_path / "calls" / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(P3ContractError) as exc:
        contract.load_config(path)
    assert exc.value.code == "p3_b34_boundary_drift"


def test_projection_mutation_is_rejected(tmp_path, monkeypatch):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    path = tmp_path / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    projection = json.loads(
        (ROOT / "datasets/p3_prospective_case01_generation_source_v1.json").read_text(encoding="utf-8")
    )
    projection["turns"][0]["content"] = "changed after freeze"
    projection_path = tmp_path / "datasets/p3_prospective_case01_generation_source_v1.json"
    projection_path.parent.mkdir(parents=True)
    projection_path.write_text(json.dumps(projection, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(
        ROOT / "datasets/p3_prospective_developer_source_v2.json",
        tmp_path / "datasets/p3_prospective_developer_source_v2.json",
    )

    def fake_ref(repo, value, expected, code):
        if expected["path"] == "datasets/p3_prospective_case01_generation_source_v1.json":
            return projection_path
        return ROOT / expected["path"]

    monkeypatch.setattr(helper, "_ref", fake_ref)
    with pytest.raises(P3ContractError) as exc:
        contract.load_config(path)
    assert exc.value.code in {"p3_b34_source_projection_mismatch", "p3_b34_turns_invalid"}
