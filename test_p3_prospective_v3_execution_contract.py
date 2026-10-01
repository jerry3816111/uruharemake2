from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import p3_prospective_v3_execution_contract as contract
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_v3_execution_contract_v1.json"


class SimulatedPowerLoss(BaseException):
    pass


class FakeTransport:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        return {
            "content": f"fake-result-{request['logical_step_index']}",
            "model": "qwen2.5:7b",
            "backend": "fake_local_no_network",
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "wall_seconds": 0.001},
            "real_model_calls": 0,
            "network_calls": 0,
        }


def test_actual_contract_preflight_binds_source_rubric_and_product_without_generation(monkeypatch):
    original = Path.read_text

    def guarded_read_text(path, *args, **kwargs):
        if path.name == "p3_prospective_developer_annotations_v3.json":
            raise AssertionError("generation contract must not read annotation file")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    result = contract.build_preflight(CONFIG)
    assert result["status"] == "ready_for_fake_checkpoint_rehearsal"
    assert result["logical_steps"] == 24
    assert result["product_reachable_root_python_files"] >= 100
    assert result["annotations_accessed"] == 0
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert all(result["checks"].values())


def test_schedule_is_case_turn_condition_order_with_locked_future_turns():
    loaded = contract.load_config(CONFIG)
    schedule = contract.build_schedule(loaded)
    assert len(schedule["steps"]) == 24
    for index in range(0, 24, 2):
        product, direct = schedule["steps"][index : index + 2]
        assert product["condition"] == "product_system"
        assert direct["condition"] == "full_history_direct"
        assert product["case_id"] == direct["case_id"]
        assert product["turn_id"] == direct["turn_id"]
        assert product["visible_source_turn_ids"] == direct["visible_source_turn_ids"]
        assert product["locked_future_turn_ids"] == direct["locked_future_turn_ids"]
    assert sum(step["restart_product_before_step"] for step in schedule["steps"]) == 3


def test_fresh_rehearsal_then_identical_resume_reuses_every_complete_checkpoint(tmp_path):
    transport = FakeTransport()
    first = contract.run_mechanical_rehearsal(CONFIG, tmp_path / "checkpoints", transport)
    second = contract.run_mechanical_rehearsal(CONFIG, tmp_path / "checkpoints", transport)
    assert first["new_fake_transport_calls"] == 24
    assert first["reused_complete_checkpoints"] == 0
    assert second["new_fake_transport_calls"] == 0
    assert second["reused_complete_checkpoints"] == 24
    assert transport.calls == 24


def test_intent_without_complete_is_terminal_and_never_recalled(tmp_path):
    transport = FakeTransport()

    def stop_after_intent(index):
        if index == 4:
            raise SimulatedPowerLoss()

    root = tmp_path / "intent-only"
    with pytest.raises(SimulatedPowerLoss):
        contract.run_mechanical_rehearsal(
            CONFIG, root, transport, after_intent_hook=stop_after_intent
        )
    assert transport.calls == 4
    with pytest.raises(P3ContractError, match="p3_b45_intent_without_complete_no_retry"):
        contract.run_mechanical_rehearsal(CONFIG, root, transport)
    assert transport.calls == 4
    terminal = json.loads((root / "terminal_failure.json").read_text(encoding="utf-8"))
    assert terminal["retry_authorized"] is False


def test_complete_checkpoint_after_power_loss_is_reused_without_recall(tmp_path):
    transport = FakeTransport()

    def stop_after_complete(index):
        if index == 4:
            raise SimulatedPowerLoss()

    root = tmp_path / "complete"
    with pytest.raises(SimulatedPowerLoss):
        contract.run_mechanical_rehearsal(
            CONFIG, root, transport, after_complete_hook=stop_after_complete
        )
    assert transport.calls == 5
    result = contract.run_mechanical_rehearsal(CONFIG, root, transport)
    assert result["reused_complete_checkpoints"] == 5
    assert result["new_fake_transport_calls"] == 19
    assert transport.calls == 24


def test_transport_failure_is_terminal_and_not_retried(tmp_path):
    calls = {"count": 0}

    def failed_transport(_request):
        calls["count"] += 1
        raise RuntimeError("simulated transport failure")

    root = tmp_path / "failed"
    with pytest.raises(P3ContractError, match="p3_b45_transport_failure_no_retry"):
        contract.run_mechanical_rehearsal(CONFIG, root, failed_transport)
    with pytest.raises(P3ContractError, match="p3_b45_terminal_failure_no_retry"):
        contract.run_mechanical_rehearsal(CONFIG, root, failed_transport)
    assert calls["count"] == 1


def test_out_of_order_or_mutated_checkpoint_fails_closed(tmp_path):
    loaded = contract.load_config(CONFIG)
    schedule = contract.build_schedule(loaded)
    plan = contract.build_mechanical_call_plan(schedule)
    root = tmp_path / "out-of-order"
    (root / "calls" / "0003").mkdir(parents=True)
    (root / "calls" / "0003" / "intent.json").write_text("{}\n", encoding="utf-8")
    transport = FakeTransport()
    with pytest.raises(P3ContractError, match="p3_b45_out_of_order_checkpoint"):
        contract.run_mechanical_rehearsal(CONFIG, root, transport)
    assert transport.calls == 0

    root = tmp_path / "mutated"
    contract.run_mechanical_rehearsal(CONFIG, root, transport)
    complete = root / "calls" / "0000" / "complete.json"
    changed = json.loads(complete.read_text(encoding="utf-8"))
    changed["result"]["content"] = "mutated after completion"
    complete.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(P3ContractError, match="p3_b45_complete_record_drift"):
        contract.run_mechanical_rehearsal(CONFIG, root, transport)
    assert (root / "terminal_failure.json").is_file()


def test_source_product_and_config_drift_are_rejected_before_transport(tmp_path, monkeypatch):
    original_sha = contract._sha

    def bad_source_sha(path):
        if Path(path).name == "p3_prospective_developer_source_v3.json":
            return "0" * 64
        return original_sha(path)

    monkeypatch.setattr(contract, "_sha", bad_source_sha)
    with pytest.raises(P3ContractError, match="p3_b45_source_drift"):
        contract.load_config(CONFIG)
    monkeypatch.setattr(contract, "_sha", original_sha)

    original_current = contract._current_file_bytes

    def changed_product(repo, relative):
        value = original_current(repo, relative)
        return value + b"\n# drift" if relative == "uruha_web_ui_product.py" else value

    monkeypatch.setattr(contract, "_current_file_bytes", changed_product)
    with pytest.raises(P3ContractError, match="p3_b45_product_snapshot_file_drift"):
        contract.load_config(CONFIG)
    monkeypatch.setattr(contract, "_current_file_bytes", original_current)

    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    value["generation"]["seed"] += 1
    changed = tmp_path / "changed-config.json"
    changed.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(P3ContractError, match="p3_b45_generation_drift"):
        contract.load_config(changed)


def test_aggregate_mechanical_audit_covers_all_recovery_boundaries():
    result = contract.build_mechanical_audit(CONFIG)
    assert result["status"] == "checkpoint_mechanical_audit_pass"
    assert all(result["checks"].values())
    assert result["evidence"]["complete_reuse"]["transport_calls_total"] == 24
    assert result["evidence"]["intent_only"]["transport_calls_before_crash"] == 4
    assert result["evidence"]["post_complete_crash"]["transport_calls_total"] == 24
    assert result["evidence"]["transport_failure"]["transport_calls_total"] == 1
    assert result["real_model_calls"] == result["network_calls"] == 0
