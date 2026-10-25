"""Zero-provider controller contract for the opt-in P4 B private child."""

from __future__ import annotations

import builtins
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import stat
from unittest.mock import patch

import pytest

import p4_preference_fallback_detached_control as control
import uruha_p4_b_private_endpoint_binding as private


def _descriptor(tmp_path: Path) -> Path:
    root = (tmp_path / "private-model").resolve()
    root.mkdir(mode=0o700)
    path = root / control.B_DESCRIPTOR_NAME
    path.write_text(json.dumps({
        "schema": "p4_b_private_endpoint_descriptor_v1",
        "private_root": str(root), "shared_models": str(root / "shared"),
        "daemon_pid": 32001, "runner_pid": 32002,
        "daemon_port": 11455, "runner_port": 55132,
        "daemon_process_start": "Sun Oct 25 01:02:03 2026",
        "runner_process_start": "Sun Oct 25 01:02:04 2026",
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

    class Result:
        returncode = 0
        stdout = b"different committed bytes"

    with patch.object(control.subprocess, "run", return_value=Result()) as run:
        with pytest.raises(control.ControllerError, match="not_committed_or_drifted"):
            control._b_committed_source_snapshot()
        assert run.call_args.args[0][-1] == (
            "HEAD:p4_preference_fallback_detached_control.py"
        )


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
        assert (descriptor.parent / control.B_MODEL_CLAIM_NAME).is_file()
    finally:
        shutil.rmtree(prepared)


def test_b_ready_rejects_descriptor_drift_without_ready_record(tmp_path, monkeypatch):
    descriptor = _descriptor(tmp_path)
    run_id = "0123456789abcdef"
    final = {
        "pid": 4242, "uid": os.getuid(), "pgid": 4242,
        "lstart": "Sun Oct 25 01:00:00 2026",
        "command": f"/bin/sleep {control.ENTRYPOINT}",
    }
    source = {name: "a" * 64 for name in control.B_COMMITTED_SOURCES}
    values = json.loads(descriptor.read_text(encoding="utf-8"))
    launch = {
        "schema": "p4_b_private_product_child_launch_v1",
        "run_id": run_id, "private_root": str(descriptor.parent),
        "child_pid": 4242, "receipt_sha256": "a" * 64,
        "environment_sha256": "b" * 64, "source_sha256": source,
        "expected_final_argv": ["/bin/sleep", str(control.ENTRYPOINT)],
        "daemon_pid": values["daemon_pid"], "runner_pid": values["runner_pid"],
        "daemon_port": values["daemon_port"], "runner_port": values["runner_port"],
    }
    metadata = {
        "run_id": run_id, "mode": "product", "pid": 4242,
        "start_identity": final, "final_command": final["command"],
        "calibration": {"python_ps_executable": "/bin/sleep"},
        "p4_b_private_launch": launch,
    }
    receipt = {
        "schema": "p4_b_private_endpoint_launch_receipt_v2",
        "issuer": "p4_b_private_controller",
        "run_id": run_id, "private_root": str(descriptor.parent),
        "models_path": str(descriptor.parent / "models"),
        "ollama_models": str(descriptor.parent / "models"),
        "ollama_no_cloud": "1",
        "shared_models": values["shared_models"],
        "base_url": "http://127.0.0.1:11455/v1",
        "runtime_root": str(tmp_path), "launch_env_sha256": "b" * 64,
        **{key: values[key] for key in (
            "daemon_pid", "runner_pid", "daemon_port", "runner_port",
            "daemon_process_start", "runner_process_start", "daemon_binary", "runner_binary",
        )},
    }
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    monkeypatch.setattr(control, "_identity", lambda pid: final)
    monkeypatch.setattr(control, "_validated_stage", lambda *args: "final_python")
    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid: True)
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: source)
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
        "expected_final_argv": ["/bin/sleep", str(control.ENTRYPOINT)],
        "final_identity": final, "same_private_endpoint_at_ready": True,
        "b_send_authorized": False,
    }
    ready_path.unlink()
    changed = {**values, "runner_pid": 32999}
    descriptor.write_text(json.dumps(changed), encoding="utf-8")
    descriptor.chmod(0o600)
    with pytest.raises(control.ControllerError, match="receipt_identity_mismatch"):
        control.verify_ready("ignored")
    assert not ready_path.exists()


def test_b_fake_child_keeps_exact_env_and_never_imports_web_or_shared_preflight(
    tmp_path, monkeypatch,
):
    descriptor = _descriptor(tmp_path)
    first = Path(control.prepare()["runtime_root"])
    second = None
    popen_env = []
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

    def issue(*, binding, runtime_root, environ, entrypoint, expected_final_argv):
        assert runtime_root == first
        assert entrypoint == control.ENTRYPOINT
        assert expected_final_argv == ["/bin/sleep", str(control.ENTRYPOINT)]
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
        popen_env.append(kwargs["env"].copy())
        return FakeProcess()

    source = {name: "a" * 64 for name in control.B_COMMITTED_SOURCES}
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: source.copy())
    monkeypatch.setattr(control, "_validate_prepared_cache", lambda root: None)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control.sandbox, "write_sandbox_profile", profile)
    monkeypatch.setattr(control, "_calibrate_python_command", lambda *args: {
        "python_ps_executable": "/bin/sleep", "identity": {"synthetic": True},
    })
    monkeypatch.setattr(control, "_identity", lambda pid: {
        "pid": 4242, "uid": os.getuid(), "pgid": 4242,
        "lstart": "Sun Oct 25 01:00:00 2026",
        "command": f"/bin/sleep {control.ENTRYPOINT}",
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
        assert len(popen_env) == 1
        env = popen_env[0]
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
