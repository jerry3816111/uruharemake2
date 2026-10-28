from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import p3_case05_dual_condition_output_lock as case05
import p3_case06_dual_condition_output_lock as lock
from p3_case03_dual_condition_output_lock import append_product_prefix, build_views
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case06_dual_condition_output_lock_v1.json"


def _call() -> dict:
    return {
        "real_model_calls": 1,
        "network_calls": 1,
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }


def _product_row(call_count: int) -> dict:
    calls = [_call() for _ in range(call_count)]
    return {
        "calls": calls,
        "real_model_calls": call_count,
        "network_calls": call_count,
        "budget": {"attempts": call_count, "completed_calls": call_count},
    }


def _direct_row() -> dict:
    return {"calls": [_call()], "budget": {"attempts": 1, "completed_calls": 1}}


def _evidence(provider_calls: int) -> dict:
    return {
        "declared_invocation_intents": 8,
        "completed_calls": 8,
        "terminal_failures": 0,
        "post_transport_failures": 0,
        "provider_call_evidence": provider_calls,
        "network_call_evidence": provider_calls,
    }


def test_case06_source_projection_is_exact_and_annotation_free():
    source = lock.load_config(CONFIG)["_source"]
    assert source["case_id"] == "p3-smoke-unknown-topic-ja"
    assert source["family"] == "unknown_and_topic_change"
    assert source["language"] == "ja"
    assert source["annotations_included"] is False
    assert [turn["turn_id"] for turn in source["turns"]] == [f"p3-smoke-06-u{i}" for i in range(1, 5)]
    assert [session["session_id"] for session in source["sessions"]] == ["p3-smoke-06-s1", "p3-smoke-06-s2"]


def test_case06_paired_views_share_source_and_hide_current_product_reply():
    config = lock.load_config(CONFIG)
    prefix = []
    for index, turn in enumerate(config["_source"]["turns"]):
        views = build_views(prefix, turn)
        product, direct = views["product_system"], views["full_history_direct"]
        assert product["source_history_sha256"] == direct["source_history_sha256"]
        assert product["input_sha256"] == direct["input_sha256"]
        assert len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        assert "annotation" not in str(views).lower()
        append_product_prefix(prefix, turn, "未生成product")


def test_preflight_is_zero_call_restart_bound_and_keeps_direct_exact(monkeypatch):
    monkeypatch.setattr(lock, "_ollama_model_metadata", lambda model: {
        "model": model,
        "digest": lock.MODEL_DIGEST,
        "template_present": True,
        "modelfile_sha256": "fake",
        "metadata_command_calls": 1,
        "generation_calls": 0,
    })
    result = lock.build_preflight(CONFIG)
    assert result["status"] == "ready_for_case06_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["checks"]["zero_call_product_turns_allowed_but_not_required"] is True
    assert result["checks"]["direct_calls_remain_exactly_four"] is True
    assert result["turn_ids"][2] == "p3-smoke-06-u3"


def test_case06_transform_reuses_zero_call_accounting_without_weakening_other_gates():
    rows = [_product_row(0), _product_row(1), _product_row(2), _product_row(0)]
    raw = {
        "status": "case03_output_lock_failed_retained",
        "checks": {
            "all_eight_visible_outputs_nonempty": True,
            "all_provider_calls_accounted": False,
            "some_other_gate": True,
        },
        "product_turns": rows,
        "direct_turns": [_direct_row() for _ in range(4)],
        "b15_calls_reused_or_counted": False,
    }
    transformed = lock.transform_result(raw, _evidence(provider_calls=7))
    assert transformed["status"] == "case06_outputs_locked"
    assert transformed["phase"] == "P3-B28"
    assert transformed["product_provider_calls"] == 3
    assert transformed["direct_provider_calls"] == 4
    assert transformed["checks"]["all_actual_provider_and_network_calls_accounted"] is True
    assert transformed["checks"]["all_eight_turn_intents_and_completions_accounted"] is True
    assert "all_provider_calls_accounted" not in transformed["checks"]
    raw["checks"]["some_other_gate"] = False
    assert lock.transform_result(raw, _evidence(provider_calls=7))["status"] == "case06_output_lock_failed_retained"


def test_case06_config_rejects_restoring_arbitrary_four_call_product_minimum(tmp_path, monkeypatch):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["execution_boundary"]["product_provider_calls_min"] = 4
    path = tmp_path / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    parent = tmp_path / "datasets" / "p3_developer_smoke_source_v1.json"
    parent.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "datasets/p3_developer_smoke_source_v1.json", parent)
    monkeypatch.setattr(case05, "_ref", lambda repo, value, expected, code: ROOT / expected["path"])
    with pytest.raises(P3ContractError) as error:
        lock.load_config(path)
    assert error.value.code == "p3_b27_boundary_drift"
