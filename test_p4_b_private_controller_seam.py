"""Zero-provider controller contract for the opt-in P4 B private child."""

from __future__ import annotations

import builtins
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
from unittest.mock import patch

import pytest

import p4_preference_fallback_detached_control as control
import p4_b_isolated_ollama_identity_probe as model_identity
import uruha_p4_b_child_local_identity as child_identity
import uruha_p4_b_private_endpoint_binding as private


def test_b_calibration_captures_both_identities_from_one_bounded_line(
    tmp_path, monkeypatch,
):
    inprocess = str(Path(sys.executable).resolve(strict=True))
    os_python = str(Path("/bin/sleep").resolve(strict=True))
    assert os_python != inprocess

    class Process:
        pid = 41234
        stdout = io.BytesIO(f"python-calibrated={inprocess}\n".encode())

        def poll(self):
            return 0

    seen = []
    monkeypatch.setattr(control.sandbox, "sandbox_command",
                        lambda profile, argv: seen.append(argv) or argv)
    monkeypatch.setattr(control.subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr(control.select, "select", lambda *args: ([Process.stdout], [], []))
    monkeypatch.setattr(control, "_identity", lambda pid: {
        "uid": os.getuid(), "pgid": pid,
        "command": f"{os_python} -c {control.CALIBRATION_CODE_B}",
    })
    result = control._calibrate_python_command(
        inprocess, {}, tmp_path / "profile.sb", capture_inprocess=True,
    )
    assert result["python_ps_executable"] == os_python
    assert result["python_sys_executable"] == inprocess
    assert seen == [[inprocess, "-c", control.CALIBRATION_CODE_B]]


def _descriptor(tmp_path: Path) -> Path:
    root = (tmp_path / "private-model").resolve()
    root.mkdir(mode=0o700)
    path = root / control.B_DESCRIPTOR_NAME
    path.write_text(json.dumps({
        "schema": "p4_b_private_endpoint_descriptor_v2",
        "private_root": str(root), "shared_models": str(root / "shared"),
        "daemon_pid": 32001, "runner_pid": 32002,
        "daemon_port": 11455, "runner_port": 55132,
        "daemon_process_start": "Sun Oct 25 01:02:03 2026",
        "runner_process_start": "Sun Oct 25 01:02:04 2026",
        "daemon_raw_generation": [32001, 31000, 1729818123, 111111],
        "runner_raw_generation": [32002, 32001, 1729818124, 222222],
        "daemon_argv_sha256": "b" * 64,
        "runner_argv_sha256": "c" * 64,
        "operator_source_sha256": "a" * 64,
        "daemon_binary": str(root / "ollama"),
        "runner_binary": str(root / "runner"),
    }), encoding="utf-8")
    path.chmod(0o600)
    return path


@pytest.mark.parametrize("kwargs, reason", [
    ({"mode": "inert", "p4_b_private": True,
      "p4_b_private_descriptor": "/tmp/descriptor"}, "fresh_prepared"),
    ({"mode": "product", "p4_b_private": True,
      "prepared_runtime_root": "/tmp/fresh"}, "descriptor_required"),
    ({"mode": "product", "p4_b_private": True,
      "prepared_runtime_root": "/tmp/fresh",
      "p4_b_private_descriptor": 123}, "descriptor_required"),
    ({"mode": "product", "p4_b_private": False,
      "p4_b_private_descriptor": "/tmp/descriptor"}, "without_explicit"),
    ({"mode": "product", "p4_b_private": True,
      "p4_b_private_descriptor": "/tmp/descriptor",
      "reuse_runtime_root": "/tmp/old"}, "fresh_prepared"),
])
def test_b_requires_explicit_fresh_prepared_product_root(kwargs, reason):
    with patch.object(control.subprocess, "Popen") as popen:
        with pytest.raises(control.ControllerError, match=reason):
            control.start(python="unused", **kwargs)
        popen.assert_not_called()


def test_parent_environment_marker_does_not_implicitly_enable_b(monkeypatch):
    monkeypatch.setenv("URUHA_P4_B_PRIVATE_CHILD", "1")
    assert control.start.__kwdefaults__["p4_b_private"] is False
    with patch.object(control.subprocess, "Popen") as popen:
        with pytest.raises(control.ControllerError, match="explicit_product_python_required"):
            control.start(mode="product", python=None)
        popen.assert_not_called()


def test_static_source_snapshot_rejects_uncommitted_drift(monkeypatch):
    monkeypatch.setattr(control, "B_COMMITTED_SOURCES", (
        "p4_preference_fallback_detached_control.py",
    ))
    monkeypatch.setattr(control.product_sources, "product_source_paths", lambda root: ())
    name = "p4_preference_fallback_detached_control.py"
    fake = io.BytesIO()
    with tarfile.open(fileobj=fake, mode="w") as stream:
        member = tarfile.TarInfo(name)
        member.size = len(b"different committed bytes")
        stream.addfile(member, io.BytesIO(b"different committed bytes"))
    monkeypatch.setattr(control, "_b_git_archive_bytes", lambda names: fake.getvalue())
    with pytest.raises(control.ControllerError, match="not_committed_or_drifted"):
        control._b_committed_source_snapshot()


@pytest.mark.parametrize("invalid", ["missing", "extra", "symlink", "duplicate"])
def test_static_source_archive_rejects_invalid_members(monkeypatch, invalid):
    name = "p4_preference_fallback_detached_control.py"
    source = (control.ROOT / name).read_bytes()
    monkeypatch.setattr(control, "B_COMMITTED_SOURCES", (name,))
    monkeypatch.setattr(control.product_sources, "product_source_paths", lambda root: ())
    fake = io.BytesIO()
    with tarfile.open(fileobj=fake, mode="w") as stream:
        if invalid != "missing":
            member = tarfile.TarInfo(name)
            member.size = len(source)
            if invalid == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = name
                member.size = 0
            stream.addfile(member, io.BytesIO(source) if member.isfile() else None)
            if invalid == "duplicate":
                stream.addfile(member, io.BytesIO(source))
        if invalid == "extra":
            member = tarfile.TarInfo("unexpected.py")
            member.size = 1
            stream.addfile(member, io.BytesIO(b"x"))
    monkeypatch.setattr(control, "_b_git_archive_bytes", lambda names: fake.getvalue())
    with pytest.raises(control.ControllerError, match="p4_b_"):
        control._b_committed_source_snapshot()


def test_static_source_archive_allows_only_expected_parent_dir(monkeypatch):
    name = "configs/p4_c_read_only_function_calling_contract_v1.json"
    source = (control.ROOT / name).read_bytes()
    monkeypatch.setattr(control, "B_COMMITTED_SOURCES", ())
    monkeypatch.setattr(control.product_sources, "product_source_paths", lambda root: (name,))
    fake = io.BytesIO()
    with tarfile.open(fileobj=fake, mode="w") as stream:
        directory = tarfile.TarInfo("configs/")
        directory.type = tarfile.DIRTYPE
        stream.addfile(directory)
        member = tarfile.TarInfo(name)
        member.size = len(source)
        stream.addfile(member, io.BytesIO(source))
    monkeypatch.setattr(control, "_b_git_archive_bytes", lambda names: fake.getvalue())
    assert control._b_committed_source_snapshot() == {
        name: control.hashlib.sha256(source).hexdigest(),
    }


@pytest.mark.parametrize("failure", ["oversize", "timeout"])
def test_git_archive_budget_kills_and_reaps_worker(monkeypatch, failure):
    real_popen = subprocess.Popen
    processes = []
    code = (
        "import sys; sys.stdout.buffer.write(b'x' * (16 * 1024 * 1024 + 1))"
        if failure == "oversize" else "import time; time.sleep(2)"
    )

    def fake_popen(_command, **kwargs):
        process = real_popen([sys.executable, "-c", code], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)
    if failure == "timeout":
        monkeypatch.setattr(control, "B_ARCHIVE_TIMEOUT_SECONDS", 0.05)
    with pytest.raises(control.ControllerError, match=(
        "oversize" if failure == "oversize" else "timeout"
    )):
        control._b_git_archive_bytes(("test.py",))
    assert len(processes) == 1
    assert processes[0].poll() is not None


def test_b_source_lock_covers_zero_turn_identity_and_gate_code():
    assert set(control.B_COMMITTED_SOURCES) == {
        "p4_preference_fallback_detached_control.py",
        "uruha_web_ui_product_p4_preference_fallback.py",
        "uruha_p4_b_private_child_bootstrap.py",
        "uruha_p4_b_private_endpoint_binding.py", "uruha_web_ui.py",
        "uruha_compute_ledger.py", "p4_b_private_zero_turn_operator.py",
        "p4_b_safe_isolated_product_launcher.py",
        "p4_b_safe_isolated_product_launcher_v2.py",
        "p4_exec_detached_lifecycle_probe.py",
        "p4_preference_fallback_launchd_control.py",
        "p4_b_isolated_ollama_identity_probe.py",
        "uruha_p4_b_resource_gate.py", "uruha_p4_b_child_local_identity.py",
        "p4_stateful_private_evidence.py", "uruha_compact_planner_p2.py",
    }


def test_controller_witness_binds_initial_raw_tuple_and_rejects_same_second_change(
    tmp_path, monkeypatch,
):
    daemon_raw = (32001, 31000, 1729818123, 111111)
    runner_raw = (32002, 32001, 1729818124, 222222)
    daemon_argv = (str(tmp_path / "ollama"), "serve")
    runner_argv = (str(tmp_path / "runner"), "--offline")
    daemon = child_identity.ProcessSnapshot(
        *daemon_raw, str(tmp_path / "ollama"), daemon_argv,
        {"OLLAMA_MODELS": True, "OLLAMA_NO_CLOUD": True},
    )
    runner = child_identity.ProcessSnapshot(
        *runner_raw, str(tmp_path / "runner"), runner_argv, {},
    )
    binding = private.PrivateEndpointBinding(
        run_id="0123456789abcdef", private_root=tmp_path,
        shared_models=tmp_path / "shared", receipt_path=tmp_path / "receipt",
        receipt_sha256="0" * 64, base_url="http://127.0.0.1:11455/v1",
        daemon_pid=32001, runner_pid=32002, daemon_port=11455, runner_port=55132,
        daemon_process_start="Sun Oct 25 01:02:03 2026",
        runner_process_start="Sun Oct 25 01:02:04 2026",
        daemon_raw_generation=daemon_raw, runner_raw_generation=runner_raw,
        daemon_argv_sha256=child_identity.argv_digest(daemon),
        runner_argv_sha256=child_identity.argv_digest(runner),
        operator_source_sha256="a" * 64,
        daemon_binary=tmp_path / "ollama", runner_binary=tmp_path / "runner",
    )
    monkeypatch.setattr(control, "_b_ps_start", lambda pid: (
        binding.daemon_process_start if pid == 32001 else binding.runner_process_start))
    monkeypatch.setattr(control, "_b_ps_daemon_environment", lambda *args: None)
    monkeypatch.setattr(model_identity, "_process", lambda pid: (
        daemon_raw[1], list(daemon_argv)) if pid == 32001
        else (runner_raw[1], list(runner_argv)))
    monkeypatch.setattr(model_identity, "_process_identity", lambda **kwargs: {
        "daemon_binary_sha256": "a" * 64, "runner_binary_sha256": "b" * 64,
    })
    monkeypatch.setattr(child_identity, "observe_process", lambda pid, *args: (
        daemon if pid == 32001 else runner))
    monkeypatch.setattr(child_identity, "owns_loopback_listener", lambda pid, port: True)
    monkeypatch.setattr(child_identity, "raw_generation", lambda pid: (
        daemon_raw if pid == 32001 else runner_raw))
    control._b_controller_witness(binding)
    reads = {32001: 0, 32002: 0}

    def changed_on_second_observation(pid):
        reads[pid] += 1
        if pid == 32002 and reads[pid] == 2:
            return (32002, 32001, 1729818124, 333333)
        return daemon_raw if pid == 32001 else runner_raw

    monkeypatch.setattr(child_identity, "raw_generation", changed_on_second_observation)
    with pytest.raises(control.ControllerError, match="controller_raw_generation_drift"):
        control._b_controller_witness(binding)


def test_bad_descriptor_or_cli_opt_in_is_fixed_error_before_popen(tmp_path, capsys):
    path = _descriptor(tmp_path)
    path.chmod(0o644)
    with pytest.raises(control.ControllerError, match="descriptor_not_private"):
        control._b_descriptor(str(path), run_id="0123456789abcdef")
    with patch.object(control.subprocess, "Popen") as popen:
        code = control.main(["start", "--mode", "inert", "--python", "unused",
                             "--p4-b-private", "--p4-b-private-descriptor", str(path)])
        popen.assert_not_called()
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"] == (
        "p4_b_requires_fresh_prepared_product_root"
    )


@pytest.mark.parametrize("change,reason", [
    ({"operator_source_sha256": "b" * 64}, "operator_source_drift"),
    ({"daemon_raw_generation": [32001, 31000, 1729818123, -1]},
     "raw_generation_invalid"),
    ({"runner_raw_generation": [32002, 31999, 1729818124, 222222]},
     "runner_parent_invalid"),
    ({"daemon_argv_sha256": "wrong"}, "digest_invalid"),
])
def test_descriptor_v2_rejects_source_and_raw_field_drift(
    tmp_path, monkeypatch, change, reason,
):
    descriptor = _descriptor(tmp_path)
    value = json.loads(descriptor.read_text())
    value.update(change)
    descriptor.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: {
        "p4_b_private_zero_turn_operator.py": "a" * 64,
    })
    with pytest.raises(control.ControllerError, match=reason):
        control._b_descriptor(str(descriptor), run_id="0123456789abcdef")


def test_b_source_failure_refuses_before_web_import_and_popen(tmp_path, monkeypatch):
    descriptor = _descriptor(tmp_path)
    prepared = Path(control.prepare()["runtime_root"])
    monkeypatch.setattr(control, "_validate_prepared_cache", lambda root: None)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: (
        (_ for _ in ()).throw(control.ControllerError("p4_b_source_not_committed_or_drifted"))
    ))
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("uruha_web_ui"):
            raise AssertionError("Web import before static source preflight")
        return original_import(name, *args, **kwargs)

    try:
        with patch.object(control.subprocess, "Popen") as popen:
            with patch.object(builtins, "__import__", side_effect=guarded_import):
                with pytest.raises(control.ControllerError, match="not_committed_or_drifted"):
                    control.start(
                        mode="product", python="unused",
                        prepared_runtime_root=str(prepared), p4_b_private=True,
                        p4_b_private_descriptor=str(descriptor),
                    )
            popen.assert_not_called()
        assert not list(prepared.glob("*stdout.log"))
        assert not list(prepared.glob("*stderr.log"))
        assert not (descriptor.parent / control.B_MODEL_CLAIM_NAME).exists()
    finally:
        shutil.rmtree(prepared)


def test_b_ready_rejects_descriptor_drift_without_ready_record(tmp_path, monkeypatch):
    descriptor = _descriptor(tmp_path)
    run_id = "0123456789abcdef"
    os_python = str(Path("/bin/sleep").resolve(strict=True))
    inprocess_python = str(Path(sys.executable).resolve(strict=True))
    assert os_python != inprocess_python
    os_argv = [os_python, str(control.ENTRYPOINT)]
    inprocess_argv = [inprocess_python, str(control.ENTRYPOINT)]
    final = {
        "pid": 4242, "uid": os.getuid(), "pgid": 4242,
        "lstart": "Sun Oct 25 01:00:00 2026",
        "command": " ".join(os_argv),
    }
    source = {name: "a" * 64 for name in control.B_COMMITTED_SOURCES}
    values = json.loads(descriptor.read_text(encoding="utf-8"))
    launch = {
        "schema": "p4_b_private_product_child_launch_v2",
        "run_id": run_id, "private_root": str(descriptor.parent),
        "child_pid": 4242, "receipt_sha256": "a" * 64,
        "environment_sha256": "b" * 64, "source_sha256": source,
        "expected_final_argv": os_argv,
        "expected_inprocess_python_argv": inprocess_argv,
        "daemon_pid": values["daemon_pid"], "runner_pid": values["runner_pid"],
        "daemon_port": values["daemon_port"], "runner_port": values["runner_port"],
    }
    metadata = {
        "run_id": run_id, "mode": "product", "pid": 4242,
        "start_identity": final, "final_command": final["command"],
        "calibration": {
            "python_ps_executable": os_python,
            "python_sys_executable": inprocess_python,
        },
        "p4_b_private_launch": launch,
    }
    receipt = {
        "schema": "p4_b_private_endpoint_launch_receipt_v5",
        "issuer": "p4_b_private_controller",
        "run_id": run_id, "private_root": str(descriptor.parent),
        "models_path": str(descriptor.parent / "models"),
        "ollama_models": str(descriptor.parent / "models"),
        "ollama_no_cloud": "1",
        "shared_models": values["shared_models"],
        "base_url": "http://127.0.0.1:11455/v1",
        "runtime_root": str(tmp_path), "launch_env_sha256": "b" * 64,
        "expected_os_final_argv": os_argv,
        "expected_final_argv_sha256": private._final_argv_digest(os_argv),
        "expected_inprocess_python_argv_sha256": private._final_argv_digest(inprocess_argv),
        **{key: values[key] for key in (
            "daemon_pid", "runner_pid", "daemon_port", "runner_port",
            "daemon_process_start", "runner_process_start", "daemon_binary", "runner_binary",
            "daemon_raw_generation", "runner_raw_generation",
            "daemon_argv_sha256", "runner_argv_sha256", "operator_source_sha256",
        )},
    }
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    monkeypatch.setattr(control, "_identity", lambda pid: final)
    monkeypatch.setattr(control, "_validated_stage", lambda *args: "final_python")
    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid: True)
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: source)
    monkeypatch.setattr(control, "_b_controller_witness", lambda binding: None)
    monkeypatch.setattr(private, "_receipt", lambda binding: receipt)
    monkeypatch.setattr(private, "_valid_receipt_time", lambda receipt: 9999999999)
    monkeypatch.setattr(private, "private_child_source_digests", lambda entrypoint: {})
    monkeypatch.setattr(private, "preflight_private_endpoint_identity", lambda binding: None)

    class Response:
        status = 200

        def read(self, size):
            return b"x"

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(control.http.client, "HTTPConnection", Connection)
    accepted = control.verify_ready("ignored")
    assert accepted["ready"] is True
    ready_path = tmp_path / control._name(run_id, "ready.json")
    ready_record = json.loads(ready_path.read_text(encoding="utf-8"))
    assert ready_record["p4_b_private_ready"] == {
        "schema": "p4_b_private_product_child_ready_v1",
        "run_id": run_id, "child_pid": 4242,
        "receipt_sha256": "a" * 64,
        "expected_final_argv": os_argv,
        "final_identity": final, "same_private_endpoint_at_ready": True,
        "b_send_authorized": False,
    }
    with patch.object(control, "_identity", return_value={
        **final, "command": f"{final['command']} --extra",
    }):
        with patch.object(control.os, "killpg") as killpg:
            with pytest.raises(control.ControllerError,
                               match="stop_refused_final_identity_changed"):
                control.stop("ignored")
            killpg.assert_not_called()
    ready_path.unlink()
    with patch.object(control, "_identity", return_value={
        **final, "command": f"{final['command']} --extra",
    }):
        with pytest.raises(control.ControllerError):
            control.verify_ready("ignored")
    assert not ready_path.exists()
    receipt["schema"] = "p4_b_private_endpoint_launch_receipt_v2"
    with pytest.raises(control.ControllerError):
        control.verify_ready("ignored")
    assert not ready_path.exists()
    receipt["schema"] = "p4_b_private_endpoint_launch_receipt_v4"
    with pytest.raises(control.ControllerError):
        control.verify_ready("ignored")
    assert not ready_path.exists()
    receipt["schema"] = "p4_b_private_endpoint_launch_receipt_v5"
    receipt["expected_os_final_argv"] = [
        str(Path("/bin/echo").resolve(strict=True)), str(control.ENTRYPOINT),
    ]
    receipt["expected_final_argv_sha256"] = private._final_argv_digest(
        receipt["expected_os_final_argv"]
    )
    with pytest.raises(control.ControllerError):
        control.verify_ready("ignored")
    assert not ready_path.exists()
    receipt["expected_os_final_argv"] = os_argv
    receipt["expected_final_argv_sha256"] = private._final_argv_digest(os_argv)
    receipt["expected_inprocess_python_argv_sha256"] = private._final_argv_digest([
        str(Path("/bin/echo").resolve(strict=True)), str(control.ENTRYPOINT),
    ])
    with pytest.raises(control.ControllerError):
        control.verify_ready("ignored")
    assert not ready_path.exists()
    receipt["expected_inprocess_python_argv_sha256"] = private._final_argv_digest(
        inprocess_argv
    )
    changed = {**values, "runner_pid": 32999}
    descriptor.write_text(json.dumps(changed), encoding="utf-8")
    descriptor.chmod(0o600)
    with pytest.raises(control.ControllerError, match="descriptor_raw_generation_invalid"):
        control.verify_ready("ignored")
    assert not ready_path.exists()


def test_b_fake_child_keeps_exact_env_and_never_imports_web_or_shared_preflight(
    tmp_path, monkeypatch,
):
    descriptor = _descriptor(tmp_path)
    first = Path(control.prepare()["runtime_root"])
    second = None
    popen_calls = []
    imported_forbidden = []
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if (name.startswith("uruha_web_ui")
                or name == "p4_preference_fallback_safe_isolated_product_launcher"):
            imported_forbidden.append(name)
            raise AssertionError(f"B static path imported {name}")
        return original_import(name, *args, **kwargs)

    def profile(root):
        path = root / "product-write-isolation.sb"
        path.write_text("(version 1)\n(allow default)\n", encoding="utf-8")
        path.chmod(0o600)
        return path

    os_python = str(Path("/bin/sleep").resolve(strict=True))
    inprocess_python = str(Path(sys.executable).resolve(strict=True))
    assert os_python != inprocess_python

    def issue(*, binding, runtime_root, environ, entrypoint,
              expected_final_argv, expected_inprocess_python_argv):
        assert runtime_root == first
        assert entrypoint == control.ENTRYPOINT
        assert expected_final_argv == [os_python, str(control.ENTRYPOINT)]
        assert expected_inprocess_python_argv == [
            inprocess_python, str(control.ENTRYPOINT),
        ]
        assert environ["URUHA_P4_B_PRIVATE_CHILD"] == "1"
        assert environ["URUHA_P4_COMPACT_JSON_SCHEMA"] == "1"
        assert environ["URUHA_WEB_COMPUTE_LEDGER"] == "1"
        assert environ["URUHA_P4_B_RECEIPT"] == str(binding.receipt_path)
        binding.receipt_path.write_bytes(b"synthetic zero-provider receipt")
        binding.receipt_path.chmod(0o600)
        return replace(binding, receipt_sha256=control._sha256(binding.receipt_path))

    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

    def fake_popen(*args, **kwargs):
        popen_calls.append((args[0], kwargs["env"].copy()))
        return FakeProcess()

    source = {name: "a" * 64 for name in control.B_COMMITTED_SOURCES}
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: source.copy())
    monkeypatch.setattr(control, "_b_controller_witness", lambda binding: None)
    monkeypatch.setattr(control, "_validate_prepared_cache", lambda root: None)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control.sandbox, "write_sandbox_profile", profile)
    monkeypatch.setattr(control, "_calibrate_python_command", lambda *args, **kwargs: {
        "python_ps_executable": os_python,
        "python_sys_executable": inprocess_python,
        "identity": {"synthetic": True},
    })
    monkeypatch.setattr(control, "_identity", lambda pid: {
        "pid": 4242, "uid": os.getuid(), "pgid": 4242,
        "lstart": "Sun Oct 25 01:00:00 2026",
        "command": f"{os_python} {control.ENTRYPOINT}",
    })
    monkeypatch.setattr(private, "preflight_private_endpoint_identity", lambda binding: None)
    monkeypatch.setattr(private, "issue_private_child_receipt", issue)
    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)
    try:
        with patch.object(builtins, "__import__", side_effect=guarded_import):
            result = control.start(
                mode="product", python=str(Path(".venv/product_checks/bin/python").resolve()),
                prepared_runtime_root=str(first), p4_b_private=True,
                p4_b_private_descriptor=str(descriptor),
            )
        assert imported_forbidden == []
        assert result["ready"] is False
        assert len(popen_calls) == 1
        command, env = popen_calls[0]
        assert inprocess_python in command
        assert command[-2:] == [inprocess_python, str(control.ENTRYPOINT)]
        assert env["URUHA_P4_B_RUN_ID"] == result["run_id"]
        assert env["URUHA_P4_B_MODEL_ROOT"] == str(descriptor.parent)
        assert env["URUHA_P4_B_RECEIPT"] == str(descriptor.parent / private._RECEIPT_NAME)
        assert env["OLLAMA_NO_CLOUD"] == "1"
        assert "OLLAMA_HOST" not in env
        assert not any(key.lower().endswith("_proxy") for key in env)
        assert env["URUHA_MEMORY_DB_PATH"] == str(first / "memory_db")
        assert env["URUHA_WEB_SESSION_DB_PATH"] == str(first / "session_db")
        _, metadata = control._root(str(first))
        assert metadata["preflight_import_scope"] == "none_b_static"
        assert metadata["final_command"] == f"{os_python} {control.ENTRYPOINT}"
        assert metadata["calibration"]["python_sys_executable"] == inprocess_python
        assert metadata["p4_b_private_launch"]["expected_final_argv"] == [
            os_python, str(control.ENTRYPOINT),
        ]
        assert metadata["p4_b_private_launch"]["child_pid"] == 4242
        assert metadata["p4_b_private_launch"]["receipt_sha256"] == (
            control._sha256(descriptor.parent / private._RECEIPT_NAME)
        )
        claim = descriptor.parent / control.B_MODEL_CLAIM_NAME
        assert stat.S_IMODE(claim.stat().st_mode) == 0o600

        second = Path(control.prepare()["runtime_root"])
        with patch.object(control.subprocess, "Popen") as no_second_popen:
            with pytest.raises(control.ControllerError, match="model_root_already_claimed"):
                control.start(
                    mode="product", python="unused", prepared_runtime_root=str(second),
                    p4_b_private=True, p4_b_private_descriptor=str(descriptor),
                )
            no_second_popen.assert_not_called()
    finally:
        shutil.rmtree(first)
        if second is not None:
            shutil.rmtree(second)
