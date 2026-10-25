"""No-network contracts for the first P4 B private constructor binding seam."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

import pytest

import uruha_p4_b_private_endpoint_binding as binding_module
from uruha_compute_ledger import ComputeLedger
from uruha_p4_b_resource_gate import P4BResourceGate

_REAL_INSPECT_LIVE_IDENTITY = binding_module._inspect_live_identity


def _write_receipt(path: Path, data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    path.chmod(0o600)
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path, monkeypatch):
    root = (tmp_path / "private").resolve()
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    daemon = root / "ollama"
    runner = root / "llama-server"
    run_id = "p4-b-private-test"
    port = 11455
    receipt_path = root / "p4_b_private_endpoint_launch_receipt.json"
    issued = time.time() - 1
    fields = {
        "schema": "p4_b_private_endpoint_launch_receipt_v2",
        "issuer": "p4_b_private_controller", "run_id": run_id,
        "private_root": str(root), "models_path": str(root / "models"),
        "shared_models": str(tmp_path / "shared/models"),
        "runtime_root": str(tmp_path / "runtime"),
        "launch_env_sha256": "1" * 64,
        "entrypoint_sha256": "2" * 64,
        "bootstrap_sha256": "3" * 64,
        "binding_source_sha256": "4" * 64,
        "web_source_sha256": "6" * 64,
        "ledger_source_sha256": "7" * 64,
        "expected_final_argv_sha256": "5" * 64,
        "base_url": f"http://127.0.0.1:{port}/v1",
        "daemon_pid": 101, "runner_pid": 102,
        "daemon_port": port, "runner_port": 55132,
        "daemon_process_start": "Sat Oct 24 12:00:00 2026",
        "runner_process_start": "Sat Oct 24 12:00:01 2026",
        "ollama_models": str(root / "models"), "ollama_no_cloud": "1",
        "daemon_binary": str(daemon), "runner_binary": str(runner),
        "daemon_binary_sha256": binding_module.FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": binding_module.FROZEN_RUNNER_SHA256,
        "manifest_sha256": binding_module.FROZEN_MANIFEST_SHA256,
        "gguf_sha256": binding_module.GGUF_SHA256,
        "template_sha256": binding_module.TEMPLATE_SHA256,
        "system_sha256": binding_module.SYSTEM_SHA256,
        "issued_at_epoch": issued, "expires_at_epoch": issued + 30,
    }
    digest = _write_receipt(receipt_path, fields)
    binding = binding_module.PrivateEndpointBinding(
        run_id=run_id, private_root=root, shared_models=tmp_path / "shared/models",
        receipt_path=receipt_path, receipt_sha256=digest,
        base_url=f"http://127.0.0.1:{port}/v1",
        daemon_pid=101, runner_pid=102, daemon_port=port, runner_port=55132,
        daemon_process_start=fields["daemon_process_start"],
        runner_process_start=fields["runner_process_start"],
        daemon_binary=daemon, runner_binary=runner,
    )
    calls = []
    monkeypatch.setattr(binding_module, "_inspect_live_identity", lambda value: calls.append(value))
    ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    return binding, ledger, fields, calls


def test_private_binding_validates_without_network_and_gate_remains_closed(tmp_path, monkeypatch):
    binding, ledger, _fields, calls = _fixture(tmp_path, monkeypatch)
    target = binding_module.validate_private_endpoint_binding(
        binding, compute_ledger=ledger, run_id=binding.run_id)
    assert target == binding_module.PrivateEndpointTarget(
        base_url="http://127.0.0.1:11455/v1",
        native_url="http://127.0.0.1:11455/api/chat",
    )
    assert calls == [binding]
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0
    assert ledger.p4_b_resource_gate._prompt_token_upper_bound is None


@pytest.mark.parametrize("bad_url", [
    "http://localhost:11455/v1", "http://127.0.0.1:11434/v1",
    "https://127.0.0.1:11455/v1", "http://u@127.0.0.1:11455/v1",
    "http://127.0.0.1:11455/v1?x=1", "http://127.0.0.1:11455/v1#x",
    "http://[::1]:11455/v1", "http://127.0.0.1:11455/v1/extra",
])
def test_private_binding_rejects_nonexact_url_before_live_inspection(
        tmp_path, monkeypatch, bad_url):
    binding, ledger, _fields, calls = _fixture(tmp_path, monkeypatch)
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        binding_module.validate_private_endpoint_binding(
            replace(binding, base_url=bad_url), compute_ledger=ledger,
            run_id=binding.run_id)
    assert calls == []


@pytest.mark.parametrize("mutation", [
    "wrong_run", "bare_ledger", "open_gate", "used_gate", "expired", "tamper",
    "receipt_mode", "wrong_root", "changed_generation", "changed_model",
])
def test_private_binding_fails_closed_before_live_inspection(
        tmp_path, monkeypatch, mutation):
    binding, ledger, fields, calls = _fixture(tmp_path, monkeypatch)
    expected_run_id = binding.run_id
    if mutation == "wrong_run":
        expected_run_id = "other-run"
    elif mutation == "bare_ledger":
        ledger = ComputeLedger()
    elif mutation == "open_gate":
        ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate(
            prompt_token_upper_bound=lambda request: 1))
    elif mutation == "used_gate":
        ledger.p4_b_resource_gate._attempted_provider_calls = 1
    elif mutation == "expired":
        fields["expires_at_epoch"] = time.time() - 1
        binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    elif mutation == "tamper":
        binding.receipt_path.write_bytes(b"wrong")
    elif mutation == "receipt_mode":
        binding.receipt_path.chmod(0o644)
    elif mutation == "wrong_root":
        fields["models_path"] = "/tmp/shared/models"
        binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    elif mutation == "changed_generation":
        fields["daemon_process_start"] = "Sat Oct 24 12:00:07 2026"
        binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    else:
        fields["manifest_sha256"] = "0" * 64
        binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        binding_module.validate_private_endpoint_binding(
            binding, compute_ledger=ledger, run_id=expected_run_id)
    assert calls == []


def test_live_identity_exception_fails_closed(tmp_path, monkeypatch):
    binding, ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(binding_module, "_inspect_live_identity", lambda _: 1 / 0)
    with pytest.raises(binding_module.PrivateEndpointBindingError,
                       match="private_ollama_identity_unavailable"):
        binding_module.validate_private_endpoint_binding(
            binding, compute_ledger=ledger, run_id=binding.run_id)


def test_live_inspector_checks_generations_and_daemon_environment_first(
        tmp_path, monkeypatch):
    binding, _ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    starts = iter([binding.daemon_process_start, binding.runner_process_start,
                   binding.daemon_process_start, binding.runner_process_start])
    calls = []
    monkeypatch.setattr(binding_module, "_process_start", lambda pid: next(starts))
    monkeypatch.setattr(binding_module, "_daemon_environment",
                        lambda pid, models: calls.append((pid, models)))
    store_calls = []
    process_calls = []
    def store(*args):
        store_calls.append(args)
        return binding.private_root / "models", {"manifest": (1, 2, 3)}
    def process(**kwargs):
        process_calls.append(kwargs)
        return {
            "daemon_binary_sha256": binding_module.FROZEN_DAEMON_SHA256,
            "runner_binary_sha256": binding_module.FROZEN_RUNNER_SHA256,
        }
    monkeypatch.setattr(binding_module, "_model_store", store)
    monkeypatch.setattr(binding_module, "_process_identity", process)
    import p4_b_isolated_ollama_identity_probe as old_probe
    monkeypatch.setattr(old_probe, "probe", lambda **_: pytest.fail("provider-shaped probe called"))
    _REAL_INSPECT_LIVE_IDENTITY(binding)
    assert calls == [(101, str(binding.private_root / "models"))]
    assert len(store_calls) == 2
    assert len(process_calls) == 1
    assert process_calls[0]["model_blob"] == (
        binding.private_root / "models/blobs" / f"sha256-{binding_module.GGUF_SHA256}"
    )


@pytest.mark.parametrize("drift", ["process_generation", "daemon_environment", "model_store"])
def test_live_inspector_refuses_generation_env_or_model_drift(
        tmp_path, monkeypatch, drift):
    binding, _ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    starts = iter(["wrong" if drift == "process_generation" else binding.daemon_process_start,
                   binding.runner_process_start, binding.daemon_process_start,
                   binding.runner_process_start])
    monkeypatch.setattr(binding_module, "_process_start", lambda pid: next(starts))
    if drift == "daemon_environment":
        monkeypatch.setattr(binding_module, "_daemon_environment",
                            lambda pid, models: binding_module._fail("daemon_environment_drift"))
    else:
        monkeypatch.setattr(binding_module, "_daemon_environment", lambda pid, models: None)
    if drift == "model_store":
        monkeypatch.setattr(binding_module, "_model_store",
                            lambda *args: (_ for _ in ()).throw(
                                binding_module.ProbeError("manifest_digest_drift")))
    else:
        monkeypatch.setattr(binding_module, "_model_store",
                            lambda *args: (binding.private_root / "models", {"file": (1, 2, 3)}))
    monkeypatch.setattr(binding_module, "_process_identity", lambda **kwargs: {
        "daemon_binary_sha256": binding_module.FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": binding_module.FROZEN_RUNNER_SHA256,
    })
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        _REAL_INSPECT_LIVE_IDENTITY(binding)


def test_daemon_environment_needs_exact_private_models_and_no_cloud(
        tmp_path, monkeypatch):
    models = str((tmp_path / "private/models").resolve())

    class Result:
        stdout = f"/usr/local/bin/ollama serve OLLAMA_MODELS={models} OLLAMA_NO_CLOUD=1"

    monkeypatch.setattr(binding_module.subprocess, "run", lambda *a, **k: Result())
    binding_module._daemon_environment(101, models)
    with pytest.raises(binding_module.PrivateEndpointBindingError,
                       match="daemon_environment_drift"):
        binding_module._daemon_environment(101, str(tmp_path / "shared/models"))


def test_receipt_expiring_during_live_inspection_fails_closed(tmp_path, monkeypatch):
    binding, ledger, fields, _calls = _fixture(tmp_path, monkeypatch)
    fields["issued_at_epoch"] = 100.0
    fields["expires_at_epoch"] = 110.0
    binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    times = iter([101.0, 111.0])
    monkeypatch.setattr(binding_module.time, "time", lambda: next(times))
    with pytest.raises(binding_module.PrivateEndpointBindingError,
                       match="receipt_expired_during_validation"):
        binding_module.validate_private_endpoint_binding(
            binding, compute_ledger=ledger, run_id=binding.run_id)


@pytest.mark.parametrize("mutation", ["removed", "mode_drift", "content_drift"])
def test_receipt_revocation_during_live_inspection_fails_closed(
        tmp_path, monkeypatch, mutation):
    binding, ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    def mutate(_binding):
        if mutation == "removed":
            binding.receipt_path.unlink()
        elif mutation == "mode_drift":
            binding.receipt_path.chmod(0o644)
        else:
            binding.receipt_path.write_bytes(b"revoked")
    monkeypatch.setattr(binding_module, "_inspect_live_identity", mutate)
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        binding_module.validate_private_endpoint_binding(
            binding, compute_ledger=ledger, run_id=binding.run_id)
