from __future__ import annotations

from pathlib import Path

import pytest

import p3_prospective_case01_output_lock as lock
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_case01_output_lock_v1.json"


def _call():
    return {
        "real_model_calls": 1,
        "network_calls": 1,
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }


def _product_row(call_count):
    calls = [_call() for _ in range(call_count)]
    return {
        "calls": calls,
        "real_model_calls": call_count,
        "network_calls": call_count,
        "budget": {"attempts": call_count, "completed_calls": call_count},
    }


def _direct_row():
    return {"calls": [_call()], "budget": {"attempts": 1, "completed_calls": 1}}


def _evidence(provider_calls):
    return {
        "declared_invocation_intents": 8,
        "completed_calls": 8,
        "terminal_failures": 0,
        "post_transport_failures": 0,
        "provider_call_evidence": provider_calls,
        "network_call_evidence": provider_calls,
    }


def test_transform_uses_actual_zero_call_aware_accounting_without_weakening_gates():
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
    result = lock.transform_result(raw, _evidence(7))
    assert result["status"] == "prospective_case01_outputs_locked"
    assert result["phase"] == "P3-B35"
    assert result["case_id"] == "p3-prospective-v2-overwhelm-company-zh"
    assert result["product_provider_calls"] == 3
    assert result["direct_provider_calls"] == 4
    assert result["annotations_accessed"] == 0
    assert result["quality_result"] == "not_evaluated_until_later_annotation_and_blind_grade"
    assert result["checks"]["all_actual_provider_and_network_calls_accounted"] is True
    assert result["checks"]["all_eight_turn_intents_and_completions_accounted"] is True
    assert "all_provider_calls_accounted" not in result["checks"]
    raw["checks"]["some_other_gate"] = False
    assert lock.transform_result(raw, _evidence(7))["status"] == "prospective_case01_output_lock_failed_retained"


def test_run_case_rejects_wrong_result_path_before_engine_call(monkeypatch, tmp_path):
    monkeypatch.setattr(lock, "validate_release", lambda _path, _config: {
        "authorization": {"result_path": "analysis/expected.json"}
    })
    called = []
    monkeypatch.setattr(lock.engine, "run_case", lambda *_args: called.append(True))
    with pytest.raises(P3ContractError) as exc:
        lock.run_case(
            CONFIG,
            ROOT / "research/fake-release.json",
            tmp_path / "checkpoints",
            tmp_path / "wrong.json",
        )
    assert exc.value.code == "p3_b35_result_path_mismatch"
    assert called == []


def test_run_case_delegates_once_and_restores_engine_hooks(monkeypatch, tmp_path):
    release_path = ROOT / "research/fake-release.json"
    expected_result = ROOT / "analysis/expected.json"
    monkeypatch.setattr(lock, "validate_release", lambda _path, _config: {
        "authorization": {"result_path": "analysis/expected.json"}
    })
    raw = {
        "checks": {"all_eight_visible_outputs_nonempty": True},
        "product_turns": [_product_row(0) for _ in range(4)],
        "direct_turns": [_direct_row() for _ in range(4)],
    }
    evidence = _evidence(4)
    original_load = lock.engine.load_config
    original_validate = lock.engine.validate_release

    def fake_run(*_args):
        assert lock.engine.load_config is not original_load
        assert lock.engine.validate_release is not original_validate
        return raw

    monkeypatch.setattr(lock.engine, "run_case", fake_run)
    monkeypatch.setattr(lock, "summarize_checkpoint_evidence", lambda _root: evidence)
    result = lock.run_case(
        CONFIG,
        release_path,
        tmp_path / "checkpoints",
        expected_result,
    )
    assert result["status"] == "prospective_case01_outputs_locked"
    assert lock.engine.load_config is original_load
    assert lock.engine.validate_release is original_validate


def test_existing_failed_checkpoint_accounting_cannot_be_reported_as_pass():
    raw = {
        "checks": {"all_eight_visible_outputs_nonempty": True},
        "product_turns": [_product_row(0) for _ in range(4)],
        "direct_turns": [_direct_row() for _ in range(4)],
    }
    evidence = _evidence(4)
    evidence["completed_calls"] = 7
    evidence["terminal_failures"] = 1
    result = lock.transform_result(raw, evidence)
    assert result["status"] == "prospective_case01_output_lock_failed_retained"
    assert result["checks"]["all_eight_turn_intents_and_completions_accounted"] is False
