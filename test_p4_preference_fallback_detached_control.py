"""No-product contract checks for the detached P4 lifecycle controller."""

from __future__ import annotations

import os
from pathlib import Path
import json
import signal
import stat
import sys
import time
from unittest.mock import patch

import pytest

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_preference_fallback_detached_control as control
import p4_preference_fallback_launchd_control as launchd


def _identity(command: str = "framework-python /tmp/product.py") -> dict:
    return {
        "pid": 4242, "uid": os.getuid(), "lstart": "Sat Oct 17 01:02:03 2026",
        "command": command, "pgid": 4242,
    }


def _metadata() -> dict:
    first = _identity("sandbox-exec -f /tmp/private.sb venv-python /tmp/product.py")
    return {
        "schema": control.SCHEMA,
        "run_id": "0123456789abcdef", "uid": os.getuid(), "mode": "product",
        "runtime_root": "/tmp/mock-root", "port": control.PORT,
        "pid": 4242, "start_identity": first,
        "wrapper_expected_command": first["command"],
        "pre_main_command": "venv-python /tmp/product.py",
        "final_command": "framework-python /tmp/product.py",
    }


def test_only_exact_wrapper_to_final_command_is_allowed():
    metadata = _metadata()
    first = metadata["start_identity"]
    assert control._validated_stage(first, metadata) == "wrapper"
    assert control._validated_stage(_identity("venv-python /tmp/product.py"), metadata) == "pre_main_python"
    assert control._validated_stage(_identity(), metadata) == "final_python"
    with pytest.raises(control.ControllerError, match="unapproved"):
        control._validated_stage(_identity("other-program /tmp/product.py"), metadata)
    with pytest.raises(control.ControllerError, match="origin_mismatch"):
        control._validated_stage({**_identity(), "lstart": "new process"}, metadata)


def test_ready_requires_same_final_pid_listener_before_and_after_http(tmp_path, monkeypatch):
    metadata = _metadata()
    metadata["runtime_root"] = str(tmp_path)
    final = _identity()
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    checked = []
    monkeypatch.setattr(control, "_identity", lambda pid: final)
    monkeypatch.setattr(control, "_listener_owned_by_pid",
                        lambda pid: checked.append((pid, control.PORT)) or True)

    class Response:
        status = 200

        def read(self, size):
            return b"x"

    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == (base.HOST, control.PORT, 2)

        def request(self, method, path):
            assert (method, path) == ("GET", "/")

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(control.http.client, "HTTPConnection", Connection)
    result = control.verify_ready("ignored")
    assert result["ready"] is True
    assert result["final_identity"] == final
    assert checked == [(4242, control.PORT), (4242, control.PORT)]
    ready = tmp_path / control._name(metadata["run_id"], "ready.json")
    assert ready.is_file()
    assert stat.S_IMODE(ready.stat().st_mode) == 0o600


def test_ready_rejects_listener_or_after_http_identity_change(tmp_path, monkeypatch):
    metadata = _metadata()
    metadata["runtime_root"] = str(tmp_path)
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    monkeypatch.setattr(control, "_identity", lambda pid: _identity())
    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid: False)
    with pytest.raises(control.ControllerError, match="listener_not_same_pid"):
        control.verify_ready("ignored")
    assert not (tmp_path / control._name(metadata["run_id"], "ready.json")).exists()

    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid: True)
    observations = iter([_identity(), {**_identity(), "lstart": "other"}])
    monkeypatch.setattr(control, "_identity", lambda pid: next(observations))

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
    with pytest.raises(control.ControllerError, match="not_attributable"):
        control.verify_ready("ignored")
    assert not (tmp_path / control._name(metadata["run_id"], "ready.json")).exists()


def test_stop_identity_mismatch_sends_no_signal(tmp_path, monkeypatch):
    metadata = _metadata()
    metadata["runtime_root"] = str(tmp_path)
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    monkeypatch.setattr(control, "_identity", lambda pid: {**_identity(), "lstart": "new process"})
    with patch.object(control.os, "killpg") as kill:
        with pytest.raises(control.ControllerError, match="origin_mismatch"):
            control.stop("ignored")
        kill.assert_not_called()


def test_listener_rejects_non_loopback_or_other_owner(monkeypatch):
    class Completed:
        returncode = 0
        stderr = ""

        def __init__(self, text):
            self.stdout = text

    with patch.object(control.subprocess, "run", return_value=Completed(
        f"p4242\nn{base.HOST}:{control.PORT}\n"
    )):
        assert control._listener_owned_by_pid(4242) is True
    with patch.object(control.subprocess, "run", return_value=Completed(
        f"p4242\nn{base.HOST}:{control.PORT}\nn*:{control.PORT}\n"
    )):
        with pytest.raises(control.ControllerError, match="loopback_scope"):
            control._listener_owned_by_pid(4242)
    with patch.object(control.subprocess, "run", return_value=Completed(
        f"p9999\nn{base.HOST}:{control.PORT}\n"
    )):
        with pytest.raises(control.ControllerError, match="loopback_scope"):
            control._listener_owned_by_pid(4242)
    with patch.object(control.subprocess, "run", return_value=Completed(
        f"p4242\nn{base.HOST}:{control.PORT}\np9999\nn*:{control.PORT}\n"
    )) as inspected:
        with pytest.raises(control.ControllerError, match="loopback_scope"):
            control._listener_owned_by_pid(4242)
        argv = inspected.call_args.args[0]
        assert "-p" not in argv and "-a" not in argv


def test_unready_product_stop_is_cleanup_not_planned_stop(tmp_path, monkeypatch):
    metadata = _metadata()
    metadata["runtime_root"] = str(tmp_path)
    current = _identity()
    observations = iter([current, current, None])
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, metadata))
    monkeypatch.setattr(control, "_identity", lambda pid: next(observations))
    monkeypatch.setattr(control, "_ready_identity", lambda *args: None)
    monkeypatch.setattr(control.identity, "_vacant", lambda port: True)
    with patch.object(control.os, "killpg") as kill:
        result = control.stop("ignored")
    kill.assert_called_once_with(4242, signal.SIGTERM)
    assert result["ok"] is False
    assert result["planned_stop"] is False
    assert result["failure_reason"] == "product_not_ready_at_stop"
    assert not (tmp_path / control._name(metadata["run_id"], "stop.json")).exists()
    assert list(tmp_path.glob("*stop-attempt-*.json"))


def test_product_reuse_requires_ready_exact_planned_stop(tmp_path, monkeypatch):
    prior = _metadata()
    prior["runtime_root"] = str(tmp_path)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control, "_root", lambda _: (tmp_path, prior))
    monkeypatch.setattr(control, "_validate_reuse_tree", lambda root: None)
    monkeypatch.setattr(control, "_identity", lambda pid: None)
    final = _identity()
    stopped = {
        "schema": control.SCHEMA, "run_id": prior["run_id"], "pid": prior["pid"],
        "planned_stop": True, "signalled": True,
        "before_identity": final, "before_stage": "final_python",
        "ready_identity": final, "original_pid_exited": True,
        "port_vacant": True,
    }
    monkeypatch.setattr(control, "_read_private_json", lambda path: stopped)
    monkeypatch.setattr(control, "_ready_identity", lambda *args: None)
    with pytest.raises(control.ControllerError, match="previous_run_not_exactly_stopped"):
        control.start(mode="product", python="dummy", reuse_runtime_root=str(tmp_path))
    monkeypatch.setattr(control, "_ready_identity", lambda *args: final)
    stopped["signalled"] = False
    with pytest.raises(control.ControllerError, match="previous_run_not_exactly_stopped"):
        control.start(mode="product", python="dummy", reuse_runtime_root=str(tmp_path))
    stopped["signalled"] = True
    stopped["before_identity"] = None
    with pytest.raises(control.ControllerError, match="previous_run_not_exactly_stopped"):
        control.start(mode="product", python="dummy", reuse_runtime_root=str(tmp_path))


def test_reuse_tree_rejects_nested_symlink_before_layout_mutation(tmp_path, monkeypatch):
    root, _ = base.prepare_runtime_root(None, reuse=False)
    base.build_runtime_layout(root)
    target = tmp_path / "outside.txt"
    target.write_text("sentinel", encoding="utf-8")
    (root / "memory_db" / "escape").symlink_to(target)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control, "_root", lambda _: (root, {"mode": "inert"}))
    with patch.object(control.base, "build_runtime_layout") as build:
        with pytest.raises(control.ControllerError, match="runtime_tree_symlink"):
            control.start(mode="inert", python=None, reuse_runtime_root=str(root))
        build.assert_not_called()
    assert target.read_text(encoding="utf-8") == "sentinel"


def test_failed_start_cleanup_refuses_unknown_group_and_preserves_evidence(tmp_path, monkeypatch):
    class FakeProcess:
        pid = 4242

    unknown = _identity("unexpected-program")
    monkeypatch.setattr(control, "_identity", lambda pid: unknown)
    monkeypatch.setattr(control, "_group_members", lambda pgid: [{"pid": 4242, "uid": os.getuid()}])
    monkeypatch.setattr(control.identity, "_vacant", lambda port: True)
    with patch.object(control.os, "killpg") as kill:
        result = control._cleanup_failed_start(
            FakeProcess(), tmp_path, "0123456789abcdef",
            {"/bin/sleep 30"}, RuntimeError("synthetic_start_failure"),
        )
    kill.assert_not_called()
    assert result["cleanup_verified"] is False
    assert result["remaining_group_members"][0]["pid"] == 4242
    evidence = tmp_path / control._name("0123456789abcdef", "start-failure.json")
    assert json.loads(evidence.read_text(encoding="utf-8"))["cleanup_verified"] is False
    assert stat.S_IMODE(evidence.stat().st_mode) == 0o600


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS detached lifecycle")
def test_inert_unexpected_death_cannot_be_recorded_as_planned_stop():
    started = control.start(mode="inert", python=None, seconds=30)
    root = started["runtime_root"]
    pid = started["pid"]
    live = control._identity(pid)
    assert live == started["start_identity"]
    os.killpg(pid, signal.SIGTERM)
    for _ in range(50):
        if control._identity(pid) is None:
            break
        time.sleep(0.1)
    assert control._identity(pid) is None
    stopped = control.stop(root)
    assert stopped["ok"] is False
    assert stopped["planned_stop"] is False
    assert stopped["signalled"] is False
    assert stopped["failure_reason"] == "unexpected_process_absent_before_stop"
    assert not (Path(root) / control._name(started["run_id"], "stop.json")).exists()
    with pytest.raises(control.ControllerError, match="missing_or_symlink"):
        control.start(mode="inert", python=None, seconds=30, reuse_runtime_root=root)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS detached lifecycle")
def test_failed_inert_start_exact_group_cleanup_is_observed(monkeypatch):
    created = []
    original_prepare = base.prepare_runtime_root

    def capture_root(*args, **kwargs):
        root, made = original_prepare(*args, **kwargs)
        created.append(root)
        return root, made

    monkeypatch.setattr(control.base, "prepare_runtime_root", capture_root)
    monkeypatch.setattr(control, "_atomic_current", lambda *args: (_ for _ in ()).throw(
        RuntimeError("synthetic_pointer_failure")
    ))
    with pytest.raises(control.ControllerError, match="cleanup_verified=True"):
        control.start(mode="inert", python=None, seconds=30)
    root = created[0]
    failures = list(root.glob("*start-failure.json"))
    assert len(failures) == 1
    result = json.loads(failures[0].read_text(encoding="utf-8"))
    assert result["allowed_identity"] is True
    assert result["signalled_verified_group"] is True
    assert result["remaining_group_members"] == []
    assert result["port_vacant"] is True
    assert result["cleanup_verified"] is True
    assert control._identity(result["pid"]) is None


def test_mocked_product_start_records_bounded_commands_without_running_product(tmp_path, monkeypatch):
    python = str(Path(".venv/product_checks/bin/python").resolve())
    original_prepare = base.prepare_runtime_root
    monkeypatch.setattr(control.base, "prepare_runtime_root", lambda *args, **kwargs:
                        original_prepare(str(tmp_path / "runtime"), reuse=False))
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control.base, "resolve_python", lambda requested, env: Path(python))

    def fake_preflight(**kwargs):
        root = Path(kwargs["runtime_root_arg"])
        layout = base.build_runtime_layout(root)
        profile = sandbox.write_sandbox_profile(root)
        env = launchd._isolated_env(layout, port=control.PORT)
        return {"python": python}, env, layout, False, profile

    import p4_preference_fallback_safe_isolated_product_launcher as launcher

    monkeypatch.setattr(launcher, "preflight_preference_fallback", fake_preflight)
    monkeypatch.setattr(control, "_calibrate_python_command", lambda *args: {
        "python_ps_executable": "/bin/sleep", "identity": _identity("calibration-only")
    })
    final = _identity(f"/bin/sleep {control.ENTRYPOINT}")
    monkeypatch.setattr(control, "_identity", lambda pid: final)

    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

        def terminate(self):
            raise AssertionError("valid start must not terminate")

    monkeypatch.setattr(control.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    result = control.start(mode="product", python=python)
    root, metadata = control._root(result["runtime_root"])
    assert root == Path(result["runtime_root"])
    assert metadata["run_id"] == result["run_id"]
    assert metadata["final_command"] == final["command"]
    assert metadata["pre_main_command"] == f"{python} {control.ENTRYPOINT}"
    assert metadata["expected_argv"][-2:] == [python, str(control.ENTRYPOINT)]
    assert metadata["auto_restart"] is False
    assert result["ready"] is False


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS ps/sandbox lifecycle")
def test_sandboxed_python_calibration_reaches_final_interpreter_without_model():
    root, _ = base.prepare_runtime_root(None, reuse=False)
    layout = base.build_runtime_layout(root)
    env = launchd._isolated_env(layout, port=control.PORT)
    profile = sandbox.write_sandbox_profile(root)
    python = str(base.resolve_python(".venv/product_checks/bin/python", env))
    result = control._calibrate_python_command(python, env, profile)
    assert result["identity"]["command"] == (
        f"{result['python_ps_executable']} -c {control.CALIBRATION_CODE}"
    )
    assert result["identity"]["uid"] == os.getuid()
    assert result["identity"]["pgid"] == result["identity"]["pid"]


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS detached lifecycle")
def test_inert_cross_call_restart_preserves_per_run_evidence():
    first = control.start(mode="inert", python=None, seconds=30)
    root = first["runtime_root"]
    latest_active = True
    try:
        assert first["ready"] is False
        assert stat.S_IMODE(Path(root).stat().st_mode) == 0o700
        _, metadata = control._root(root)
        assert metadata["isolation"] == control._expected_isolation(Path(root))
        status = control.status(root)
        assert status["same_origin_alive"] is True
        assert status["stage"] == "inert"
        with pytest.raises(control.ControllerError, match="product_only"):
            control.verify_ready(root)
        stopped = control.stop(root)
        latest_active = False
        assert stopped["original_pid_exited"] is True
        assert stopped["port_vacant"] is True
        old_log = Path(status["stdout_file"])
        old_meta = Path(root) / control._name(first["run_id"], "json")
        old_stop = Path(root) / control._name(first["run_id"], "stop.json")
        assert all(path.is_file() and stat.S_IMODE(path.stat().st_mode) == 0o600
                   for path in (old_log, old_meta, old_stop))
        second = control.start(mode="inert", python=None, seconds=30,
                               reuse_runtime_root=root)
        latest_active = True
        assert second["run_id"] != first["run_id"]
        assert second["pid"] != first["pid"]
        assert second["previous_run_id"] == first["run_id"]
        assert old_log.is_file() and old_meta.is_file() and old_stop.is_file()
        assert control.stop(root)["original_pid_exited"] is True
        latest_active = False
    finally:
        if latest_active:
            try:
                control.stop(root)
            except control.ControllerError:
                pass
