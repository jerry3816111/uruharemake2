from __future__ import annotations

from pathlib import Path

import pytest

import p3_prospective_case03_output_lock as lock
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_case03_output_lock_v1.json"


def _call(): return {"real_model_calls": 1, "network_calls": 1, "usage": {"prompt_tokens": 10, "completion_tokens": 2}}
def _row(count=1): return {"calls": [_call() for _ in range(count)], "real_model_calls": count, "network_calls": count, "budget": {"attempts": count, "completed_calls": count}}
def _evidence(count=8): return {"declared_invocation_intents": 8, "completed_calls": 8, "terminal_failures": 0, "post_transport_failures": 0, "provider_call_evidence": count, "network_call_evidence": count}


def test_transform_requires_quotation_aware_surface_and_actual_accounting():
    raw = {
        "checks": {"all_eight_visible_outputs_nonempty": True, "all_eight_shared_surface_pass": True, "all_provider_calls_accounted": True},
        "product_turns": [_row() for _ in range(4)], "direct_turns": [_row() for _ in range(4)],
    }
    result = lock.transform_result(raw, _evidence())
    assert result["status"] == "prospective_case03_outputs_locked"
    assert result["checks"]["all_eight_quotation_aware_japanese_surface_pass"] is True
    assert "all_eight_shared_surface_pass" not in result["checks"]
    raw["checks"]["all_eight_shared_surface_pass"] = False
    assert lock.transform_result(raw, _evidence())["status"] == "prospective_case03_output_lock_failed_retained"


def test_wrong_result_path_refuses_before_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(lock, "validate_release", lambda _path, _config: {"authorization": {"result_path": "analysis/expected.json"}})
    called = []
    monkeypatch.setattr(lock.engine, "run_case", lambda *_args: called.append(True))
    with pytest.raises(P3ContractError) as exc:
        lock.run_case(CONFIG, ROOT / "research/fake.json", tmp_path / "cp", tmp_path / "wrong.json")
    assert exc.value.code == "p3_b42_result_path_mismatch"
    assert called == []


def test_engine_hooks_restore_after_delegation(monkeypatch, tmp_path):
    release = ROOT / "research/fake.json"
    expected = ROOT / "analysis/expected.json"
    monkeypatch.setattr(lock, "validate_release", lambda _path, _config: {"authorization": {"result_path": "analysis/expected.json"}})
    original_load, original_validate = lock.engine.load_config, lock.engine.validate_release
    raw = {"checks": {"all_eight_visible_outputs_nonempty": True, "all_eight_shared_surface_pass": True}, "product_turns": [_row(0) for _ in range(4)], "direct_turns": [_row() for _ in range(4)]}
    monkeypatch.setattr(lock.engine, "run_case", lambda *_args: raw)
    monkeypatch.setattr(lock, "summarize_checkpoint_evidence", lambda _root: _evidence(4))
    assert lock.run_case(CONFIG, release, tmp_path / "cp", expected)["status"] == "prospective_case03_outputs_locked"
    assert lock.engine.load_config is original_load
    assert lock.engine.validate_release is original_validate


def test_incomplete_checkpoint_accounting_fails():
    raw = {"checks": {"all_eight_visible_outputs_nonempty": True, "all_eight_shared_surface_pass": True}, "product_turns": [_row(0) for _ in range(4)], "direct_turns": [_row() for _ in range(4)]}
    evidence = _evidence(4)
    evidence["completed_calls"] = 7
    evidence["terminal_failures"] = 1
    assert lock.transform_result(raw, evidence)["status"] == "prospective_case03_output_lock_failed_retained"

