from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_prospective_case02_output_lock_contract as contract
from p3_case03_dual_condition_output_lock import append_product_prefix, build_views
from p3_product_comparison import P3ContractError
from p3_strict_visible_surface import strict_japanese_visible_surface_contract


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_case02_output_lock_v1.json"


def test_case02_is_exact_second_frozen_source_case_and_annotation_free():
    config = contract.load_config(CONFIG)
    source = config["_source"]
    parent = json.loads(
        (ROOT / "datasets/p3_prospective_developer_source_v2.json").read_text(encoding="utf-8")
    )
    assert source["turns"] == parent["cases"][1]["turns"]
    assert source["sessions"] == parent["cases"][1]["sessions"]
    assert source["case_id"] == contract.CASE_ID
    assert source["family"] == "positive_arousal_not_anxiety"
    assert source["language"] == "en"
    assert source["annotations_included"] is False
    assert source["generation_executed"] is False
    assert config["selection"] == {
        "rule": "second_case_in_immutable_source_order_after_first_case_retained",
        "case_index_zero_based": 1,
        "quality_based_selection": False,
        "prior_case_regeneration": False,
    }


def test_case02_pairs_share_prefix_and_hide_current_product_and_future_turns():
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
        for future in turns[index + 1:]:
            assert future["content"] not in serialized
        append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")


def test_preflight_is_zero_call_and_binds_strict_gate(monkeypatch):
    monkeypatch.setattr(contract, "_ollama_model_metadata", lambda model: {
        "model": model,
        "digest": contract.MODEL_DIGEST,
        "template_present": True,
        "modelfile_sha256": "fake",
        "metadata_command_calls": 1,
        "generation_calls": 0,
    })
    result = contract.build_preflight(CONFIG)
    assert result["status"] == "ready_for_prospective_case02_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["strict_surface_sha256"] == (
        "90b2b4ee0ad1e4f4d990c0497f08a0841bbdad48cbafa65c1690777d775e3d9f"
    )
    assert result["checks"]["prior_failed_case_not_regenerated"] is True
    assert result["checks"]["strict_surface_contract_frozen"] is True
    assert all(result["checks"].values())


def test_strict_gate_rejects_b35_chinese_false_positive_and_accepts_japanese():
    failed = strict_japanese_visible_surface_contract(
        "可能是整理房间累了，坐下来休息一下了。继续整理的话，要注意休息哦。"
    )
    passed = strict_japanese_visible_surface_contract("届くの楽しみすぎだろ。朝からそわそわするやつ。")
    assert failed["has_japanese"] is True
    assert failed["has_japanese_kana"] is False
    assert failed["no_known_foreign_language_leak"] is False
    assert all(passed.values())


def test_config_rejects_strict_gate_or_selection_drift():
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["strict_surface_contract"]["sha256"] = "0" * 64
    with pytest.raises(P3ContractError) as exc:
        contract.validate_strict_reference(raw["strict_surface_contract"])
    assert exc.value.code == "p3_b37_strict_surface_reference_mismatch"

    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["selection"]["quality_based_selection"] = True
    with pytest.raises(P3ContractError) as exc:
        contract.validate_selection(raw["selection"])
    assert exc.value.code == "p3_b37_selection_drift"
