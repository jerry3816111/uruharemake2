from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import p3_case05_dual_condition_output_lock as lock
from p3_case03_dual_condition_output_lock import append_product_prefix, build_views
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case05_dual_condition_output_lock_v1.json"


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
    return {
        "calls": [_call()],
        "budget": {"attempts": 1, "completed_calls": 1},
    }


def _evidence(provider_calls: int) -> dict:
    return {
        "declared_invocation_intents": 8,
        "completed_calls": 8,
        "terminal_failures": 0,
        "post_transport_failures": 0,
        "provider_call_evidence": provider_calls,
        "network_call_evidence": provider_calls,
    }


def test_case05_source_projection_is_exact_and_annotation_free():
    config = lock.load_config(CONFIG)
    source = config["_source"]
    assert source["case_id"] == "p3-smoke-speaker-memory-en"
    assert source["family"] == "speaker_qualified_memory"
    assert source["language"] == "en"
    assert source["annotations_included"] is False
    assert [x["turn_id"] for x in source["turns"]] == [f"p3-smoke-05-u{i}" for i in range(1, 5)]
    assert [x["session_id"] for x in source["sessions"]] == ["p3-smoke-05-s1", "p3-smoke-05-s2"]


def test_case05_paired_views_share_source_and_hide_current_product_reply():
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
    assert result["status"] == "ready_for_fresh_case05_output_lock_review"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["checks"]["zero_call_product_turns_allowed_but_not_required"] is True
    assert result["checks"]["direct_calls_remain_exactly_four"] is True
    assert result["turn_ids"][2] == "p3-smoke-05-u3"


def test_zero_call_product_turn_is_valid_when_every_actual_call_and_turn_record_is_accounted():
    product_rows = [_product_row(0), _product_row(1), _product_row(2), _product_row(0)]
    direct_rows = [_direct_row() for _ in range(4)]
    calls_accounted, records_accounted, product_count, direct_count = lock._actual_call_accounting(
        {"product_turns": product_rows, "direct_turns": direct_rows},
        _evidence(provider_calls=7),
    )
    assert calls_accounted is True
    assert records_accounted is True
    assert product_count == 3 and direct_count == 4


@pytest.mark.parametrize(
    ("mutate", "provider_calls"),
    [
        (lambda product, direct: product[0]["budget"].update(attempts=1), 7),
        (lambda product, direct: direct[0]["calls"].clear(), 6),
        (lambda product, direct: None, 8),
    ],
)
def test_zero_call_aware_accounting_rejects_budget_direct_or_checkpoint_mismatch(mutate, provider_calls):
    product_rows = [_product_row(0), _product_row(1), _product_row(2), _product_row(0)]
    direct_rows = [_direct_row() for _ in range(4)]
    mutate(product_rows, direct_rows)
    calls_accounted, _, _, _ = lock._actual_call_accounting(
        {"product_turns": product_rows, "direct_turns": direct_rows},
        _evidence(provider_calls=provider_calls),
    )
    assert calls_accounted is False


def test_transform_only_overrides_obsolete_minimum_and_keeps_other_failed_checks():
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
    assert transformed["status"] == "case05_outputs_locked"
    assert "all_provider_calls_accounted" not in transformed["checks"]
    assert transformed["checks"]["all_actual_provider_and_network_calls_accounted"] is True
    assert transformed["checks"]["all_eight_turn_intents_and_completions_accounted"] is True
    raw["checks"]["some_other_gate"] = False
    assert lock.transform_result(raw, _evidence(provider_calls=7))["status"] == "case05_output_lock_failed_retained"


def test_config_rejects_restoring_arbitrary_four_call_product_minimum(tmp_path, monkeypatch):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["execution_boundary"]["product_provider_calls_min"] = 4
    path = tmp_path / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    parent = tmp_path / "datasets" / "p3_developer_smoke_source_v1.json"
    parent.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "datasets/p3_developer_smoke_source_v1.json", parent)
    monkeypatch.setattr(lock, "_ref", lambda repo, value, expected, code: ROOT / expected["path"])
    with pytest.raises(P3ContractError) as error:
        lock.load_config(path)
    assert error.value.code == "p3_b23_boundary_drift"
