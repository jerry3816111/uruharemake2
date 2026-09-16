from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_case03_dual_condition_output_lock as output_engine
from p3_b35_surface_gate_audit import (
    SurfaceAuditError,
    build_audit,
)
from p3_product_comparison import shared_visible_surface_contract
from p3_strict_visible_surface import strict_japanese_visible_surface_contract


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/p3_b35_prospective_case01_output_lock_result_2026-09-17.json"


def test_strict_contract_closes_han_only_false_positive():
    text = "可能是整理房间累了，坐下来休息一下了。继续整理的话，要注意休息哦。"
    assert all(shared_visible_surface_contract(text).values())
    strict = strict_japanese_visible_surface_contract(text)
    assert strict["has_japanese"] is True
    assert strict["has_japanese_kana"] is False
    assert strict["no_known_foreign_language_leak"] is False


def test_strict_contract_accepts_machine_clean_japanese_surface():
    strict = strict_japanese_visible_surface_contract(
        "あー、物多すぎだろ。片付けても片付けても終わんないやつ。"
    )
    assert all(strict.values())


def test_future_dual_condition_engine_is_bound_to_strict_surface_contract():
    assert (
        output_engine.strict_japanese_visible_surface_contract
        is strict_japanese_visible_surface_contract
    )


def test_actual_b35_audit_retains_exact_failure_without_opening_annotations():
    audit = build_audit(RESULT)
    assert audit["status"] == "b35_surface_gate_false_positive_retained"
    assert audit["strict_pass_count"] == 7
    assert audit["strict_failure_count"] == 1
    assert audit["comparison_quality_ready"] is False
    assert audit["failed_outputs"] == [{
        "condition": "full_history_direct",
        "turn_id": "p3-prospective-v2-01-u1",
        "failure_reasons": [
            "has_japanese_kana",
            "no_known_foreign_language_leak",
        ],
    }]
    assert audit["real_model_calls"] == audit["network_calls"] == 0
    assert audit["annotations_accessed"] == 0
    assert all(audit["checks"].values())


def test_audit_fails_closed_if_locked_result_bytes_change(tmp_path):
    value = json.loads(RESULT.read_text(encoding="utf-8"))
    value["direct_turns"][0]["final"]["content"] = "日本語に差し替えた。"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SurfaceAuditError, match="b35_result_hash_mismatch"):
        build_audit(changed)
