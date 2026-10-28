from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_prospective_case03_output_lock_contract as contract
from p3_case03_dual_condition_output_lock import append_product_prefix, build_views
from p3_product_comparison import P3ContractError
from p3_strict_visible_surface_v2 import strict_japanese_visible_surface_contract


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_case03_output_lock_v1.json"


def test_case03_is_exact_third_frozen_case_without_annotations():
    config = contract.load_config(CONFIG)
    source = config["_source"]
    parent = json.loads((ROOT / "datasets/p3_prospective_developer_source_v2.json").read_text(encoding="utf-8"))
    assert source["turns"] == parent["cases"][2]["turns"]
    assert source["sessions"] == parent["cases"][2]["sessions"]
    assert source["case_id"] == contract.CASE_ID
    assert source["annotations_included"] is False
    assert source["generation_executed"] is False
    assert config["selection"] == contract.SELECTION


def test_all_views_are_paired_and_future_turns_hidden():
    turns = contract.load_config(CONFIG)["_source"]["turns"]
    prefix = []
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


def test_preflight_is_zero_call_and_quotation_aware(monkeypatch):
    monkeypatch.setattr(contract, "_ollama_model_metadata", lambda model: {
        "model": model, "digest": contract.MODEL_DIGEST, "template_present": True,
        "modelfile_sha256": "fake", "metadata_command_calls": 1, "generation_calls": 0,
    })
    result = contract.build_preflight(CONFIG)
    assert result["status"] == "ready_for_prospective_case03_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["checks"]["quotation_aware_surface_contract_frozen"] is True
    assert result["checks"]["prior_cases_not_regenerated"] is True
    assert all(result["checks"].values())


def test_inline_quote_passes_but_whole_wrapper_fails():
    inline = strict_japanese_visible_surface_contract(
        "先輩の『また今度』は、今はまだ保留って見るのが自然だろ。"
    )
    wrapped = strict_japanese_visible_surface_contract(
        "「今はまだ保留って見るのが自然だろ。」"
    )
    assert all(inline.values())
    assert wrapped["no_quote_or_translation_wrapper"] is False


def test_selection_and_surface_version_drift_are_rejected():
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["selection"]["quality_based_selection"] = True
    with pytest.raises(P3ContractError) as exc:
        contract.validate_selection(raw["selection"])
    assert exc.value.code == "p3_b41_selection_drift"
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["strict_surface_contract"]["sha256"] = "0" * 64
    with pytest.raises(P3ContractError) as exc:
        contract.validate_strict_reference(raw["strict_surface_contract"])
    assert exc.value.code == "p3_b41_strict_surface_reference_mismatch"

