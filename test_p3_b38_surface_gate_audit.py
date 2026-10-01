from __future__ import annotations

import json
from pathlib import Path

import pytest

from p3_b38_surface_gate_audit import SurfaceAuditError, build_audit
from p3_strict_visible_surface_v2 import strict_japanese_visible_surface_contract


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/p3_b38_prospective_case02_output_lock_result_2026-09-17.json"


def test_in_sentence_japanese_quote_is_not_a_wrapper():
    result = strict_japanese_visible_surface_contract(
        "今朝ようやく「配達中」になったね。楽しみだね。"
    )
    assert all(result.values())


@pytest.mark.parametrize("text", [
    "「今日は休め。」",
    "『今日は休め。』",
    "日本語版：今日は休め。",
    "中国語版: 今日は休め。",
])
def test_whole_reply_or_translation_wrapper_remains_rejected(text):
    result = strict_japanese_visible_surface_contract(text)
    assert result["no_quote_or_translation_wrapper"] is False


def test_actual_b38_audit_preserves_failed_status_but_identifies_false_positive():
    audit = build_audit(RESULT)
    assert audit["status"] == "b38_quote_gate_false_positive_retained"
    assert audit["original_surface_failure_count"] == 1
    assert audit["quotation_aware_pass_count"] == 8
    assert audit["quotation_aware_failure_count"] == 0
    assert audit["original_runner_status_preserved"] == (
        "prospective_case02_output_lock_failed_retained"
    )
    assert audit["comparison_quality_ready"] is False
    assert audit["real_model_calls"] == audit["network_calls"] == 0
    assert audit["annotations_accessed"] == 0
    assert all(audit["checks"].values())


def test_b38_audit_rejects_any_result_byte_change(tmp_path):
    value = json.loads(RESULT.read_text(encoding="utf-8"))
    value["direct_turns"][2]["final"]["content"] = "引用を消した。"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SurfaceAuditError, match="b38_result_hash_mismatch"):
        build_audit(changed)
