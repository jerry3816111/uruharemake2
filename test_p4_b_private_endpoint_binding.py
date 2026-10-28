"""No-network contracts for the first P4 B private constructor binding seam."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
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
    daemon.write_bytes(b"fake-daemon")
    runner.write_bytes(b"fake-runner")
    model_blob = root / "models" / "blobs" / f"sha256-{binding_module.GGUF_SHA256}"
    model_blob.parent.mkdir(parents=True)
    model_blob.write_bytes(b"fake-model")
    run_id = "p4-b-private-test"
    port = 11455
    receipt_path = root / "p4_b_private_endpoint_launch_receipt.json"
    issued = time.time() - 1
    entrypoint = Path(binding_module.__file__).resolve().with_name(
        "uruha_web_ui_product_p4_preference_fallback.py"
    )
    os_argv = [str(Path("/bin/sleep").resolve(strict=True)), str(entrypoint)]
    inprocess_argv = [str(Path(sys.executable).resolve(strict=True)), str(entrypoint)]
    assert os_argv[0] != inprocess_argv[0]
    fields = {
        "schema": "p4_b_private_endpoint_launch_receipt_v5",
        "issuer": "p4_b_private_controller", "run_id": run_id,
        "private_root": str(root), "models_path": str(root / "models"),
        "shared_models": str(tmp_path / "shared/models"),
        "runtime_root": str(tmp_path / "runtime"),
        "launch_env_sha256": "1" * 64,
        "entrypoint_sha256": "2" * 64,
        "bootstrap_sha256": "3" * 64,
        "binding_source_sha256": "4" * 64,
        "controller_source_sha256": "5" * 64,
        "web_source_sha256": "6" * 64,
        "ledger_source_sha256": "7" * 64,
        "operator_source_sha256": "8" * 64,
        "private_evidence_source_sha256": "0" * 64,
        "compact_planner_source_sha256": "0" * 64,
        "launcher_source_sha256": "9" * 64,
        "sandbox_source_sha256": "a" * 64,
        "lifecycle_source_sha256": "b" * 64,
        "launchd_source_sha256": "c" * 64,
        "identity_probe_source_sha256": "d" * 64,
        "resource_gate_source_sha256": "e" * 64,
        "child_observer_source_sha256": "f" * 64,
        "product_source_manifest_sha256": "a" * 64,
        "product_manifest_module_sha256": "b" * 64,
        "expected_os_final_argv": os_argv,
        "expected_final_argv_sha256": binding_module._final_argv_digest(os_argv),
        "expected_inprocess_python_argv_sha256": binding_module._final_argv_digest(
            inprocess_argv
        ),
        "base_url": f"http://127.0.0.1:{port}/v1",
        "daemon_pid": 101, "runner_pid": 102,
        "daemon_port": port, "runner_port": 55132,
        "daemon_process_start": "Sat Oct 24 12:00:00 2026",
        "runner_process_start": "Sat Oct 24 12:00:01 2026",
        "daemon_raw_generation": [101, 1, 1792843200, 123456],
        "runner_raw_generation": [102, 101, 1792843201, 654321],
        "daemon_argv_sha256": "1" * 64,
        "runner_argv_sha256": "2" * 64,
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
        daemon_raw_generation=tuple(fields["daemon_raw_generation"]),
        runner_raw_generation=tuple(fields["runner_raw_generation"]),
        daemon_argv_sha256=fields["daemon_argv_sha256"],
        runner_argv_sha256=fields["runner_argv_sha256"],
        operator_source_sha256=fields["operator_source_sha256"],
        daemon_binary=daemon, runner_binary=runner,
    )
    calls = []
    monkeypatch.setattr(binding_module, "_inspect_live_identity", lambda value: calls.append(value))
    ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    return binding, ledger, fields, calls


def test_private_binding_validates_without_network_and_gate_remains_closed(tmp_path, monkeypatch):
    binding, ledger, fields, calls = _fixture(tmp_path, monkeypatch)
    assert fields["schema"] == "p4_b_private_endpoint_launch_receipt_v5"
    assert set(fields) == binding_module._RECEIPT_FIELDS
    assert fields["expected_final_argv_sha256"] == binding_module._final_argv_digest(
        fields["expected_os_final_argv"]
    )
    target = binding_module.validate_private_endpoint_binding(
        binding, compute_ledger=ledger, run_id=binding.run_id)
    assert target == binding_module.PrivateEndpointTarget(
        base_url="http://127.0.0.1:11455/v1",
        native_url="http://127.0.0.1:11455/api/chat",
    )
    assert calls == [binding]
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0
    assert ledger.p4_b_resource_gate._prompt_token_upper_bound is None


@pytest.mark.parametrize("mutation", [
    "old_v2", "old_v3", "old_v4", "missing_os_argv", "missing_inprocess_sha", "extra_field",
    "missing_raw", "malformed_raw", "missing_observer_source", "malformed_operator_source",
    "missing_product_manifest", "malformed_product_manifest", "missing_manifest_module",
    "malformed_manifest_module",
    "os_argv_one_element", "os_argv_extra_argument", "os_argv_relative",
    "os_argv_symlink", "os_argv_nul", "os_digest_mismatch",
    "inprocess_digest_not_hex",
])
def test_v5_receipt_rejects_missing_ambiguous_or_noncanonical_identity_fields(
        tmp_path, monkeypatch, mutation):
    binding, ledger, fields, calls = _fixture(tmp_path, monkeypatch)
    if mutation == "old_v2":
        fields["schema"] = "p4_b_private_endpoint_launch_receipt_v2"
        fields.pop("expected_os_final_argv")
        fields.pop("expected_inprocess_python_argv_sha256")
    elif mutation == "old_v3":
        fields["schema"] = "p4_b_private_endpoint_launch_receipt_v3"
    elif mutation == "old_v4":
        fields["schema"] = "p4_b_private_endpoint_launch_receipt_v4"
        fields.pop("product_source_manifest_sha256")
        fields.pop("product_manifest_module_sha256")
    elif mutation == "missing_raw":
        fields.pop("daemon_raw_generation")
    elif mutation == "malformed_raw":
        fields["daemon_raw_generation"] = [101, 1, 1792843200, True]
    elif mutation == "missing_observer_source":
        fields.pop("child_observer_source_sha256")
    elif mutation == "malformed_operator_source":
        fields["operator_source_sha256"] = "not-a-digest"
    elif mutation == "missing_product_manifest":
        fields.pop("product_source_manifest_sha256")
    elif mutation == "malformed_product_manifest":
        fields["product_source_manifest_sha256"] = "not-a-digest"
    elif mutation == "missing_manifest_module":
        fields.pop("product_manifest_module_sha256")
    elif mutation == "malformed_manifest_module":
        fields["product_manifest_module_sha256"] = "not-a-digest"
    elif mutation == "missing_os_argv":
        fields.pop("expected_os_final_argv")
    elif mutation == "missing_inprocess_sha":
        fields.pop("expected_inprocess_python_argv_sha256")
    elif mutation == "extra_field":
        fields["unexpected_argv_fallback"] = True
    elif mutation == "os_argv_one_element":
        fields["expected_os_final_argv"] = fields["expected_os_final_argv"][:1]
    elif mutation == "os_argv_extra_argument":
        fields["expected_os_final_argv"] = [*fields["expected_os_final_argv"], "--extra"]
    elif mutation == "os_argv_relative":
        fields["expected_os_final_argv"] = ["bin/sleep", fields["expected_os_final_argv"][1]]
    elif mutation == "os_argv_symlink":
        alias = tmp_path / "sleep-alias"
        alias.symlink_to(fields["expected_os_final_argv"][0])
        fields["expected_os_final_argv"] = [str(alias), fields["expected_os_final_argv"][1]]
    elif mutation == "os_argv_nul":
        fields["expected_os_final_argv"] = [
            fields["expected_os_final_argv"][0] + "\x00", fields["expected_os_final_argv"][1],
        ]
    elif mutation == "os_digest_mismatch":
        fields["expected_final_argv_sha256"] = "0" * 64
    else:
        fields["expected_inprocess_python_argv_sha256"] = "not-a-digest"
    binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        binding_module.validate_private_endpoint_binding(
            binding, compute_ledger=ledger, run_id=binding.run_id)
    assert calls == []


@pytest.mark.parametrize("invalid", [None, 12, "/bin/sleep", ["/bin/sleep\x00", "/tmp/x"]])
def test_final_argv_digest_rejects_invalid_type_or_nul_as_domain_error(invalid):
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        binding_module._final_argv_digest(invalid)


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
    "receipt_mode", "wrong_root", "changed_generation", "changed_raw_generation",
    "changed_argv_digest", "changed_model",
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
    elif mutation == "changed_raw_generation":
        # Same second and PID, different microsecond: an old ps lstart still matches.
        fields["daemon_raw_generation"][3] += 1
        binding = replace(binding, receipt_sha256=_write_receipt(binding.receipt_path, fields))
    elif mutation == "changed_argv_digest":
        fields["runner_argv_sha256"] = "0" * 64
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


def test_receipt_issuance_refuses_operator_source_not_matching_loaded_binding(
        tmp_path, monkeypatch):
    binding, ledger, fields, _calls = _fixture(tmp_path, monkeypatch)
    runtime = (tmp_path / "runtime").resolve()
    runtime.mkdir(mode=0o700)
    runtime.chmod(0o700)
    entry = Path(binding_module.__file__).resolve().with_name(
        "uruha_web_ui_product_p4_preference_fallback.py")
    environment = {key: "test-value" for key in binding_module._B_ENV_KEYS}
    environment.update({
        "URUHA_P4_B_PRIVATE_CHILD": "1",
        "URUHA_P4_B_RUN_ID": binding.run_id,
        "URUHA_P4_B_MODEL_ROOT": str(binding.private_root),
        "URUHA_P4_B_RECEIPT": str(binding.receipt_path),
        "URUHA_WEB_COMPUTE_LEDGER": "1",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "OLLAMA_NO_CLOUD": "1",
        "HOME": str(runtime), "TMPDIR": str(runtime),
    })
    with pytest.raises(binding_module.PrivateEndpointBindingError,
                       match="operator_source_drift_before_receipt"):
        binding_module.issue_private_child_receipt(
            binding=binding, runtime_root=runtime, environ=environment,
            entrypoint=entry,
            expected_final_argv=[str(Path("/bin/sleep").resolve()), str(entry)],
            expected_inprocess_python_argv=[str(Path(sys.executable).resolve()), str(entry)],
        )
    assert binding.receipt_path.exists()
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0


def _live_fake(binding, monkeypatch):
    observer = binding_module.child_identity
    model = binding.private_root / "models" / "blobs" / f"sha256-{binding_module.GGUF_SHA256}"
    daemon = observer.ProcessSnapshot(
        *binding.daemon_raw_generation, str(binding.daemon_binary),
        (str(binding.daemon_binary), "serve"),
        {"OLLAMA_MODELS": True, "OLLAMA_NO_CLOUD": True},
    )
    runner = observer.ProcessSnapshot(
        *binding.runner_raw_generation, str(binding.runner_binary),
        (str(binding.runner_binary), "--model", str(model),
         "--host", "127.0.0.1", "--port", str(binding.runner_port),
         "--chat-template", "chatml", "--offline", "--no-jinja"), {},
    )
    binding = replace(binding, daemon_argv_sha256=observer.argv_digest(daemon),
                      runner_argv_sha256=observer.argv_digest(runner))
    calls = {"raw": [], "observe": [], "listener": [], "store": [], "binary": []}

    def raw(pid):
        calls["raw"].append(pid)
        return (binding.daemon_raw_generation if pid == binding.daemon_pid
                else binding.runner_raw_generation)

    def observe(pid, expected_env=None):
        calls["observe"].append((pid, expected_env))
        return daemon if pid == binding.daemon_pid else runner

    def store(*args):
        calls["store"].append(args)
        return binding.private_root / "models", {"manifest": (1, 2, 3)}

    monkeypatch.setattr(observer, "raw_generation", raw)
    monkeypatch.setattr(observer, "observe_process", observe)
    monkeypatch.setattr(observer, "owns_loopback_listener",
                        lambda pid, port: calls["listener"].append((pid, port)) or True)
    monkeypatch.setattr(binding_module, "_model_store", store)
    monkeypatch.setattr(binding_module, "_model_sha256_file", lambda path: (
        calls["binary"].append(path) or (
            binding_module.FROZEN_DAEMON_SHA256 if path == binding.daemon_binary
            else binding_module.FROZEN_RUNNER_SHA256)))
    return binding, daemon, runner, calls


def test_live_inspector_uses_raw_brackets_and_full_identity_without_ps_or_provider(
        tmp_path, monkeypatch):
    binding, ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    binding, _daemon, _runner, calls = _live_fake(binding, monkeypatch)
    import p4_b_isolated_ollama_identity_probe as old_probe
    monkeypatch.setattr(old_probe, "probe", lambda **_: pytest.fail("provider-shaped probe called"))
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail(
        "sandboxed ps/lsof subprocess must not be needed by this fake observer"))
    _REAL_INSPECT_LIVE_IDENTITY(binding)
    assert calls["raw"] == [101, 102, 101, 102]
    assert calls["observe"] == [
        (101, {"OLLAMA_MODELS": str(binding.private_root / "models"),
               "OLLAMA_NO_CLOUD": "1"}), (102, None),
    ]
    assert calls["listener"] == [(101, 11455), (102, 55132)]
    assert len(calls["store"]) == 2
    assert calls["binary"] == [binding.daemon_binary, binding.runner_binary]
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0


@pytest.mark.parametrize("drift", [
    "same_second_replacement", "late_replacement", "daemon_environment",
    "duplicate_daemon_environment", "daemon_argv", "runner_argv",
    "runner_flag", "runner_model_missing", "runner_model_wrong",
    "runner_parent", "runner_executable", "listener_owner",
    "binary_sha", "model_store", "model_store_during_inspection",
])
def test_live_inspector_refuses_raw_env_argv_listener_binary_or_model_drift(
        tmp_path, monkeypatch, drift):
    binding, ledger, _fields, _calls = _fixture(tmp_path, monkeypatch)
    binding, daemon, runner, calls = _live_fake(binding, monkeypatch)
    observer = binding_module.child_identity
    if drift in ("same_second_replacement", "late_replacement"):
        original = observer.raw_generation
        count = {"n": 0}
        def replaced(pid):
            count["n"] += 1
            generation = original(pid)
            if pid == binding.daemon_pid and (drift == "same_second_replacement"
                                              or count["n"] >= 3):
                return (*generation[:3], generation[3] + 1)
            return generation
        monkeypatch.setattr(observer, "raw_generation", replaced)
    elif drift == "daemon_environment":
        daemon = replace(daemon, env_exact={"OLLAMA_MODELS": False,
                                            "OLLAMA_NO_CLOUD": True})
    elif drift == "duplicate_daemon_environment":
        daemon = replace(daemon, env_exact={"OLLAMA_MODELS": True,
                                            "OLLAMA_NO_CLOUD": False})
    elif drift == "daemon_argv":
        daemon = replace(daemon, argv=(str(binding.daemon_binary), "wrong"))
    elif drift == "runner_argv":
        runner = replace(runner, argv=(*runner.argv, "--extra"))
    elif drift == "runner_flag":
        argv = list(runner.argv)
        argv[argv.index("--host") + 1] = "0.0.0.0"
        runner = replace(runner, argv=tuple(argv))
        binding = replace(binding, runner_argv_sha256=observer.argv_digest(runner))
    elif drift == "runner_model_missing":
        argv = list(runner.argv)
        index = argv.index("--model")
        del argv[index:index + 2]
        runner = replace(runner, argv=tuple(argv))
        binding = replace(binding, runner_argv_sha256=observer.argv_digest(runner))
    elif drift == "runner_model_wrong":
        argv = list(runner.argv)
        argv[argv.index("--model") + 1] = str(binding.private_root / "wrong-model")
        runner = replace(runner, argv=tuple(argv))
        binding = replace(binding, runner_argv_sha256=observer.argv_digest(runner))
    elif drift == "runner_parent":
        runner = replace(runner, ppid=999)
    elif drift == "runner_executable":
        runner = replace(runner, executable=str(binding.daemon_binary))
        binding = replace(binding, runner_argv_sha256=observer.argv_digest(runner))
    elif drift == "listener_owner":
        monkeypatch.setattr(observer, "owns_loopback_listener", lambda *_: False)
    elif drift == "binary_sha":
        monkeypatch.setattr(binding_module, "_model_sha256_file", lambda *_: "0" * 64)
    elif drift == "model_store":
        monkeypatch.setattr(binding_module, "_model_store", lambda *_: (
            _ for _ in ()).throw(binding_module.ProbeError("manifest_digest_drift")))
    else:
        sequence = iter([{"manifest": (1, 2, 3)}, {"manifest": (1, 2, 4)}])
        monkeypatch.setattr(binding_module, "_model_store",
                            lambda *_: (binding.private_root / "models", next(sequence)))
    if drift in {"daemon_environment", "duplicate_daemon_environment", "daemon_argv",
                 "runner_argv", "runner_flag", "runner_model_missing", "runner_model_wrong",
                 "runner_parent", "runner_executable"}:
        monkeypatch.setattr(observer, "observe_process",
                            lambda pid, expected_env=None: daemon if pid == 101 else runner)
    with pytest.raises(binding_module.PrivateEndpointBindingError):
        _REAL_INSPECT_LIVE_IDENTITY(binding)
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0


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
