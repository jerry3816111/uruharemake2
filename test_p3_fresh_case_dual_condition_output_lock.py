from __future__ import annotations

from pathlib import Path

import p3_fresh_case_dual_condition_output_lock as lock
from p3_case03_dual_condition_output_lock import build_views, append_product_prefix


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case04_dual_condition_output_lock_v1.json"


def test_case04_source_projection_is_exact_and_annotation_free():
    config = lock.load_config(CONFIG)
    source = config["_source"]
    assert source["case_id"] == "p3-smoke-humor-boundary-zh"
    assert source["language"] == "zh"
    assert source["annotations_included"] is False
    assert [x["turn_id"] for x in source["turns"]] == [f"p3-smoke-04-u{i}" for i in range(1, 5)]
    assert [x["session_id"] for x in source["sessions"]] == ["p3-smoke-04-s1", "p3-smoke-04-s2"]


def test_case04_paired_views_share_source_and_hide_current_product_reply():
    config = lock.load_config(CONFIG)
    prefix = []
    for turn in config["_source"]["turns"]:
        views = build_views(prefix, turn)
        assert views["product_system"]["source_history_sha256"] == views["full_history_direct"]["source_history_sha256"]
        assert views["product_system"]["input_sha256"] == views["full_history_direct"]["input_sha256"]
        assert "annotation" not in str(views).lower()
        append_product_prefix(prefix, turn, "未生成product")


def test_preflight_is_zero_call_and_restart_bound(monkeypatch):
    monkeypatch.setattr(lock, "_ollama_model_metadata", lambda model: {
        "model": model, "digest": lock.MODEL_DIGEST, "template_present": True,
        "modelfile_sha256": "fake", "metadata_command_calls": 1, "generation_calls": 0,
    })
    result = lock.build_preflight(CONFIG)
    assert result["status"] == "ready_for_fresh_case04_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["turn_ids"][2] == "p3-smoke-04-u3"


def test_result_transform_does_not_claim_grade_or_reuse():
    value = lock.transform_result({"status": "case03_outputs_locked", "b15_calls_reused_or_counted": False})
    assert value["status"] == "case04_outputs_locked"
    assert value["phase"] == "P3-B20"
    assert value["prior_case_calls_reused_or_counted"] is False
    assert "generation evidence only" in value["claim_boundary"]
