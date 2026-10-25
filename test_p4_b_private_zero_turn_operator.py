"""Isolated, zero-service contracts for the one-use private P4 operator."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import p4_b_private_zero_turn_operator as operator


def test_cli_without_explicit_execute_never_calls_runtime(monkeypatch, capsys):
    monkeypatch.setattr(operator, "run_once", lambda: pytest.fail("runtime must remain inert"))
    assert operator.main([]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "ok": False, "reason": "explicit_execute_required", "b_send_authorized": False,
    }


def test_prepared_cache_and_warm_use_child_python_without_mutating_home(tmp_path, monkeypatch):
    root = tmp_path / "uruha-product-test"
    original_home = os.environ.get("HOME")
    original_tmpdir = os.environ.get("TMPDIR")
    calls = []
    monkeypatch.setattr(operator.control, "prepare", lambda: {"runtime_root": str(root)})

    def fake_run(command, **kwargs):
        calls.append(command)
        if "cache" in command:
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "sha256": operator.control.ONNX_ARCHIVE_SHA256,
            }))
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "offline_embedding_ready": True, "httpx_stream_download_attempts": 0,
            "dimensions": 384,
        }))

    monkeypatch.setattr(operator.subprocess, "run", fake_run)
    assert operator._prepare_product_root() == root
    assert [command[2] for command in calls] == ["cache", "warm"]
    assert all(command[0] == str(operator.PYTHON) for command in calls)
    assert all(command[4] == str(root) for command in calls)
    assert os.environ.get("HOME") == original_home
    assert os.environ.get("TMPDIR") == original_tmpdir


def test_warm_failure_does_not_start_daemon_or_mutate_parent_environment(tmp_path, monkeypatch):
    root = tmp_path / "prepared"
    monkeypatch.setattr(operator.control, "prepare", lambda: {"runtime_root": str(root)})
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command[2])
        if command[2] == "cache":
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "sha256": operator.control.ONNX_ARCHIVE_SHA256,
            }))
        return SimpleNamespace(returncode=2, stdout="", stderr="private error")

    monkeypatch.setattr(operator.subprocess, "run", fake_run)
    with pytest.raises(operator.OperatorError, match="private_onnx_warm_failed"):
        operator._prepare_product_root()
    assert calls == ["cache", "warm"]


def test_warm_failure_still_reports_created_one_use_root(tmp_path, monkeypatch):
    root = tmp_path / "prepared"
    observed = []
    monkeypatch.setattr(operator.control, "prepare", lambda: {"runtime_root": str(root)})
    monkeypatch.setattr(operator.subprocess, "run", lambda command, **kwargs: SimpleNamespace(
        returncode=2, stdout="", stderr="ignored private error"))
    with pytest.raises(operator.OperatorError, match="private_onnx_cache_failed"):
        operator._prepare_product_root(observed.append)
    assert observed == [root]


def test_clone_only_six_explicit_files_with_distinct_inodes(tmp_path, monkeypatch):
    shared = tmp_path / "shared/models"
    manifest_rel = Path("manifests/registry.ollama.ai/library/qwen2.5/7b")
    (shared / manifest_rel.parent).mkdir(parents=True)
    (shared / "blobs").mkdir()
    payloads = [b"config", b"gguf", b"system", b"license", b"template"]
    hashes = tuple(hashlib.sha256(payload).hexdigest() for payload in payloads)
    entries = [{"digest": f"sha256:{digest}", "size": len(payload)}
               for digest, payload in zip(hashes, payloads, strict=True)]
    manifest = json.dumps({"config": entries[0], "layers": entries[1:]},
                          separators=(",", ":")).encode()
    (shared / manifest_rel).write_bytes(manifest)
    for digest, payload in zip(hashes, payloads, strict=True):
        (shared / "blobs" / f"sha256-{digest}").write_bytes(payload)
    expected = operator.probe.ExpectedModel(
        manifest_sha256=hashlib.sha256(manifest).hexdigest(), blob_sha256s=hashes,
        gguf_sha256=hashes[1], template_sha256=hashes[4], system_sha256=hashes[2],
    )
    original_mkdtemp = operator.tempfile.mkdtemp
    monkeypatch.setattr(operator.tempfile, "mkdtemp", lambda prefix: original_mkdtemp(
        prefix=prefix, dir=tmp_path))
    monkeypatch.setattr(operator, "SHARED_MODELS", shared)
    monkeypatch.setattr(operator.probe, "FROZEN_BLOBS", hashes)
    monkeypatch.setattr(operator.probe, "FROZEN_MODEL", expected)
    observed = []
    root, logical_bytes = operator._clone_private_model(observed.append)
    assert observed == [root]
    assert root.parent == tmp_path
    assert root.stat().st_mode & 0o777 == 0o700
    assert logical_bytes == len(manifest) + sum(map(len, payloads))
    for relative in (manifest_rel, *(Path("blobs") / f"sha256-{digest}" for digest in hashes)):
        private = root / "models" / relative
        source = shared / relative
        assert private.read_bytes() == source.read_bytes()
        assert private.stat().st_ino != source.stat().st_ino
        assert private.stat().st_nlink == 1
        assert private.stat().st_mode & 0o777 == 0o600


def test_descriptor_is_exact_single_link_0600_and_exclusive(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    path = operator._write_descriptor(root, 401, 51234, 400, "daemon-start", "runner-start")
    data = json.loads(path.read_text())
    assert set(data) == operator.DESCRIPTOR_FIELDS
    assert data["daemon_port"] == operator.DAEMON_PORT
    assert data["runner_port"] == 51234
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.stat().st_nlink == 1
    with pytest.raises(FileExistsError):
        operator._write_descriptor(root, 401, 51234, 400, "daemon-start", "runner-start")


def test_daemon_readiness_uses_one_version_http_without_retry(monkeypatch):
    listener = iter([frozenset(), frozenset({400})])
    calls = []
    monkeypatch.setattr(operator, "_listener_pids", lambda port: next(listener))
    monkeypatch.setattr(operator.probe, "_http_json", lambda url: (
        calls.append(url), {"version": operator.probe.VERSION})[1])
    monkeypatch.setattr(operator.time, "sleep", lambda _: None)
    counts = {}
    operator._wait_daemon(400, counts)
    assert counts == {"daemon_ready_version_http_count": 1}
    assert calls == ["http://127.0.0.1:11455/api/version"]


def test_daemon_wrong_version_is_terminal_no_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(operator, "_listener_pids", lambda port: frozenset({400}))
    monkeypatch.setattr(operator.probe, "_http_json", lambda url: (
        calls.append(url), {"version": "wrong"})[1])
    with pytest.raises(operator.OperatorError, match="private_daemon_version_drift"):
        operator._wait_daemon(400, {})
    assert len(calls) == 1


def test_render_only_nonempty_reply_captures_exact_runner_then_refuses(monkeypatch):
    calls = []
    monkeypatch.setattr(operator.probe, "_http_json", lambda *args: {
        "model": operator.probe.MODEL,
        "usage": {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1},
        "choices": [{"message": {"content": "unexpected"}}],
        "_debug_info": {"rendered_template": f"User Input: {operator.probe.FIXTURE}"},
    })
    monkeypatch.setattr(operator, "_owned_runner_snapshots", lambda *args: (
        [(401, 51234, "daemon", "runner", (str(operator.RUNNER_BINARY), "--offline"))], False))
    monkeypatch.setattr(operator, "_listener_pids", lambda port: frozenset({401}))
    counts = {}
    with pytest.raises(operator.OperatorError, match="render_only_not_zero_completion"):
        operator._load_runner_and_identify(
            400, Path("/tmp/private"), counts,
            lambda pid, port, generation, argv: calls.append((pid, port, generation, argv)))
    assert counts["operator_diagnostic_http_count"] == 1
    assert calls == [(401, 51234, "runner", (str(operator.RUNNER_BINARY), "--offline"))]


def test_cleanup_refuses_pid_generation_drift_before_any_signal(monkeypatch):
    signals = []
    monkeypatch.setattr(operator, "_generation", lambda pid: "replacement")
    monkeypatch.setattr(operator.os, "kill", lambda pid, sig: signals.append((pid, sig)))
    assert operator._stop_exact(401, "original", operator.RUNNER_BINARY,
                                daemon=False, expected_parent=400) == "identity_drift_no_signal"
    assert signals == []


def test_cleanup_refuses_argv_drift_even_with_same_pid_generation(monkeypatch):
    signals = []
    monkeypatch.setattr(operator, "_generation", lambda pid: "same-generation")
    monkeypatch.setattr(operator, "_process_argv", lambda pid: (
        400, [str(operator.RUNNER_BINARY), "--offline", "--model", "wrong.gguf"]))
    monkeypatch.setattr(operator.os, "kill", lambda pid, sig: signals.append((pid, sig)))
    result = operator._stop_exact(
        401, "same-generation", operator.RUNNER_BINARY, daemon=False,
        expected_parent=400,
        expected_argv=(str(operator.RUNNER_BINARY), "--offline", "--model", "expected.gguf"),
    )
    assert result == "identity_drift_no_signal"
    assert signals == []


def test_cleanup_signals_only_exact_captured_pid(monkeypatch):
    calls = []
    generations = iter(["original", None])
    monkeypatch.setattr(operator, "_generation", lambda pid: next(generations))
    monkeypatch.setattr(operator, "_same_process", lambda *args, **kwargs: True)
    monkeypatch.setattr(operator.os, "kill", lambda pid, sig: calls.append((pid, sig)))
    assert operator._stop_exact(401, "original", operator.RUNNER_BINARY,
                                daemon=False, expected_parent=400) == "terminated"
    assert calls == [(401, operator.signal.SIGTERM)]


@pytest.mark.parametrize("pids, expected", [([], "private_runner_not_ready"),
                                             ([401, 402], "multiple_private_runners")])
def test_runner_discovery_rejects_missing_or_multiple_daemon_children(monkeypatch, pids, expected):
    monkeypatch.setattr(operator.probe, "_http_json", lambda *args: {
        "model": operator.probe.MODEL,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "choices": [{"message": {"content": ""}}],
        "_debug_info": {"rendered_template": f"User Input: {operator.probe.FIXTURE}"},
    })
    monkeypatch.setattr(operator, "_owned_runner_snapshots", lambda *args: (
        [(pid, 51234 + index, "daemon", "runner", ("runner",))
         for index, pid in enumerate(pids)], False))
    monotonic = iter([0, 0, 11] if not pids else [0, 0])
    monkeypatch.setattr(operator.time, "monotonic", lambda: next(monotonic))
    with pytest.raises(operator.OperatorError, match=expected):
        operator._load_runner_and_identify(400, Path("/tmp/private"), {})


def _fake_run_env(monkeypatch, tmp_path, *, ready_error=False, disk_overrun=False):
    events = []
    class FakeSampler:
        def __init__(self):
            self.pids = {"operator": os.getpid()}

        def start(self):
            pass

        def add(self, label, pid, generation):
            self.pids[label] = pid

        def close(self):
            return {label: {"sample_count": 1} for label in self.pids}

    monkeypatch.setattr(operator, "_ProcessSampler", FakeSampler)
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    product = tmp_path / "product"
    product.mkdir(mode=0o700)
    class FakeDaemon:
        pid = 400
        terminated = False

        def poll(self):
            return 0 if self.terminated else None

        def terminate(self):
            events.append("owned-popen-terminate")
            self.terminated = True

        def kill(self):
            events.append("owned-popen-kill")
            self.terminated = True

        def wait(self, timeout):
            return 0

    daemon = FakeDaemon()
    free = 100 * 1024**3
    monkeypatch.setattr(operator, "_static_preflight", lambda: {
        "shared_listener_pids": [1529], "shared_process_generations": {1529: "shared"},
        "free_bytes_before": free,
    })
    monkeypatch.setattr(operator, "_prepare_product_root", lambda callback: (
        callback(product), events.append("warm"), product)[2])
    monkeypatch.setattr(operator, "_clone_private_model", lambda callback: (
        callback(private), events.append("clone"), (private, 4_683_073_952))[2])
    if disk_overrun:
        free_reads = iter((free, free - 4_683_073_952, free - 4_683_073_952))
        monkeypatch.setattr(operator, "_available_bytes", lambda: next(free_reads))
    else:
        monkeypatch.setattr(operator, "_available_bytes", lambda: free)
    monkeypatch.setattr(operator, "_listener_pids", lambda port: frozenset({1529}) if port == 11434 else frozenset())
    monkeypatch.setattr(operator, "_launch_daemon", lambda root: events.append("daemon") or daemon)
    monkeypatch.setattr(operator, "_generation", lambda pid: {400: "daemon", 401: "runner", 1529: "shared"}.get(pid))
    monkeypatch.setattr(operator, "_same_process", lambda *args, **kwargs: True)
    monkeypatch.setattr(operator, "_wait_daemon", lambda pid, state: state.__setitem__(
        "daemon_ready_version_http_count", 1))

    def fake_runner(pid, private_root, state, callback):
        state["operator_diagnostic_http_count"] += 1
        callback(401, 51234, "runner", (str(operator.RUNNER_BINARY), "--offline"))
        return 401, 51234, "daemon", "runner", (str(operator.RUNNER_BINARY), "--offline")

    monkeypatch.setattr(operator, "_load_runner_and_identify", fake_runner)
    monkeypatch.setattr(operator, "_owned_runner_snapshots", lambda *args: ([], False))
    monkeypatch.setattr(operator.probe, "_http_json", lambda *args, **kwargs: {})
    monkeypatch.setattr(operator.probe, "_model_store", lambda *args, **kwargs: (None, {}))

    def fake_probe(**kwargs):
        events.append("probe")
        operator.probe._model_store(None, None, None)
        operator.probe._model_store(None, None, None)
        for _ in range(5):
            operator.probe._http_json("http://127.0.0.1:11455/api/version")
        return {"diagnostic_http_calls": 5, "generated_completions": 0}

    monkeypatch.setattr(operator.probe, "probe", fake_probe)
    monkeypatch.setattr(operator, "_write_descriptor", lambda *args: events.append("descriptor") or
                        private / "descriptor")
    monkeypatch.setattr(operator, "_sha256", lambda path: "0" * 64)
    monkeypatch.setattr(operator, "_sample_pid", lambda pid: None)
    monkeypatch.setattr(operator, "_result_file", lambda root, report: private / "report")
    monkeypatch.setattr(operator, "_stop_exact", lambda *args, **kwargs: "terminated")

    def start(**kwargs):
        events.append("start")
        assert kwargs["p4_b_private"] is True
        assert kwargs["prepared_runtime_root"] == str(product)
        return {"run_id": "0123456789abcdef", "pid": 500,
                "start_identity": {"lstart": "child-start"}}

    def ready(root):
        events.append("verify-ready")
        if ready_error:
            raise operator.control.ControllerError("identity_drift")
        return {"ready": True, "pid": 500}

    def stop(root):
        events.append("stop")
        return {"ok": not ready_error, "planned_stop": not ready_error,
                "original_pid_exited": True, "port_vacant": True}

    monkeypatch.setattr(operator.control, "start", start)
    monkeypatch.setattr(operator.control, "verify_ready", ready)
    monkeypatch.setattr(operator.control, "stop", stop)
    return events


def test_one_true_zero_turn_path_orders_warm_before_daemon_and_verifies_ready(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path)
    result = operator.run_once()
    assert result["status"] == "real_zero_turn_identity_pass"
    assert events == ["warm", "clone", "daemon", "probe", "descriptor",
                      "start", "verify-ready", "stop"]
    assert result["operator_diagnostic_http_count"] == 6
    assert result["daemon_ready_version_http_count"] == 1
    assert result["helper_model_store_validations"] == 3
    assert result["resource_sampling_complete"] is True
    assert result["brain_constructor_observed"] is False
    assert result["provider_network_completion_count_proven"] is False
    assert result["safari_sends"] == 0


def test_ready_identity_failure_stops_once_and_cannot_become_pass(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path, ready_error=True)
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "ControllerError"
    assert events.count("start") == events.count("stop") == 1
    assert events[-2:] == ["verify-ready", "stop"]


def test_disk_budget_denial_never_launches_daemon_or_claims_product(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path, disk_overrun=True)
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "private_clone_disk_budget_exceeded"
    assert events == ["warm", "clone"]


def test_source_preflight_denial_has_zero_root_or_process_side_effects(monkeypatch):
    calls = []
    monkeypatch.setattr(operator, "_static_preflight", lambda: (
        _ for _ in ()).throw(operator.OperatorError("source_drift")))
    monkeypatch.setattr(operator, "_prepare_product_root", lambda *args: calls.append("root"))
    monkeypatch.setattr(operator, "_clone_private_model", lambda *args: calls.append("clone"))
    monkeypatch.setattr(operator, "_launch_daemon", lambda *args: calls.append("daemon"))
    monkeypatch.setattr(operator, "_listener_pids", lambda port: frozenset())
    monkeypatch.setattr(operator, "_available_bytes", lambda: 100 * 1024**3)
    monkeypatch.setattr(operator, "_ProcessSampler", lambda: SimpleNamespace(
        start=lambda: None, close=lambda: {}, add=lambda *args: None))
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "source_drift"
    assert calls == []


def test_render_only_failure_after_runner_capture_exactly_cleans_both(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path)
    cleanup = []

    def fail_after_capture(pid, private_root, state, callback):
        state["operator_diagnostic_http_count"] += 1
        callback(401, 51234, "runner", (str(operator.RUNNER_BINARY), "--offline"))
        raise operator.OperatorError("render_only_not_zero_completion")

    monkeypatch.setattr(operator, "_load_runner_and_identify", fail_after_capture)
    monkeypatch.setattr(operator, "_stop_exact", lambda pid, *args, **kwargs: (
        cleanup.append(pid), "terminated")[1])
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "render_only_not_zero_completion"
    assert cleanup == [401, 400]
    assert "start" not in events


def test_owned_popen_fallback_terminates_when_daemon_generation_unavailable(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path)
    monkeypatch.setattr(operator, "_generation", lambda pid: None if pid == 400 else "shared")
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "private_daemon_identity_unavailable"
    assert result["daemon_cleanup"] == "owned_popen_terminated_without_generation"
    assert result["cleanup_review_required"] is True
    assert "owned-popen-terminate" in events
    assert "start" not in events


def test_final_listener_inspection_failure_retains_result_not_exception(monkeypatch, tmp_path):
    events = _fake_run_env(monkeypatch, tmp_path)

    def listener(port):
        if "stop" in events:
            raise operator.OperatorError("lsof_unavailable")
        return frozenset({1529}) if port == 11434 else frozenset()

    monkeypatch.setattr(operator, "_listener_pids", listener)
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["listener_final_inspection"] == "unavailable_review_required"
    assert result["cleanup_review_required"] is True


def test_result_persistence_failure_cannot_report_pass(monkeypatch, tmp_path):
    _fake_run_env(monkeypatch, tmp_path)
    monkeypatch.setattr(operator, "_result_file", lambda *args: (
        _ for _ in ()).throw(OSError("inaccessible")))
    result = operator.run_once()
    assert result["status"] == "fail_closed"
    assert result["failure_reason"] == "result_persistence_failed"
