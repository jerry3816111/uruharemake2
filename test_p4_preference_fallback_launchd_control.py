"""Inert launchd controller contract tests; no product or model is started."""

from __future__ import annotations

from pathlib import Path
import socket
import subprocess

import pytest

import p4_preference_fallback_launchd_control as control


DOMAIN = "gui/501"
LABEL = control.LABEL_PREFIX + "0123456789abcdef"
META = {"label": LABEL, "mode": "product", "port": 7894}


def _result(rc: int, *, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout, stderr)


def test_job_status_only_accepts_exact_confirmed_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = f'Could not find service "{LABEL}" in domain for user gui: 501\n'
    monkeypatch.setattr(control.os, "getuid", lambda: 501)
    monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: _result(113, stderr=missing))
    status = control._job_status(DOMAIN, META)
    assert status["loaded"] is False
    assert status["confirmed_not_found"] is True
    for result in (
        _result(113, stderr="Could not find service \"different\" in domain for user gui: 501\n"),
        _result(5, stderr=missing),
        _result(113, stderr="launchctl domain unavailable\n"),
    ):
        monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: result)
        with pytest.raises(control.ControllerError, match="launchctl_status_unknown"):
            control._job_status(DOMAIN, META)


def test_product_port_must_be_vacant() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((control.base.HOST, 0))
        port = listener.getsockname()[1]
        with pytest.raises(control.ControllerError, match="product_port_not_vacant"):
            control._require_vacant_port(port)
    assert control._port_vacant(port)


def test_transient_other_uid_pid_is_present_but_not_ours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(control.os, "getuid", lambda: 501)
    monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: _result(0, stdout=" 123   0 S\n"))
    assert control._pid_alive(123) is True
    assert control._pid_owned_alive(123) is False


def test_start_reports_bootstrap_not_http_readiness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout = {"runtime_root": tmp_path}
    checks = []
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_new_root", lambda: (tmp_path, layout))
    monkeypatch.setattr(control, "_isolated_env", lambda *a, **k: {})
    monkeypatch.setattr(control.sandbox, "write_sandbox_profile", lambda *a, **k: tmp_path / "profile")
    monkeypatch.setattr(control, "_snapshot_profile", lambda *a, **k: tmp_path / "profile.frozen")
    monkeypatch.setattr(control.sandbox, "sandbox_command", lambda profile, cmd: cmd)
    monkeypatch.setattr(control, "_write_job", lambda *a, **k: {
        "label": LABEL, "preflight_import_scope": "none", "plist_file": "test.plist"
    })
    monkeypatch.setattr(control, "_record_observed_pid", lambda root, metadata, pid: metadata)
    monkeypatch.setattr(control, "_publish_current", lambda root, metadata: None)
    monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: _result(0))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {"loaded": True, "pid": 9999})
    monkeypatch.setattr(control, "_pid_owned_alive", lambda pid: checks.append(pid) or True)
    result = control.start(mode="dry-run", seconds=10, port=7894, python=None)
    assert result["ok"] is True and result["bootstrap_succeeded"] is True
    assert result["process_verified_live"] is True and checks == [9999]
    assert result["ready"] is False and result["http_ready_verified"] is False
    assert result["lifecycle_status"] == "dry_run_bootstrapped"
    assert result["candidate_url"] is None


def test_stop_checks_original_pid_and_port_after_exact_bootout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []
    states = iter((
        {"loaded": True, "pid": 77},
        {"loaded": False, "pid": None},
    ))
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, META))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: next(states))
    monkeypatch.setattr(control.subprocess, "run", lambda args, **k: calls.append(args) or _result(0))
    monkeypatch.setattr(control, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(control, "_port_vacant", lambda port: port == 7894)
    monkeypatch.setattr(control, "_record_stop", lambda *a: None)
    result = control.stop(str(tmp_path))
    assert calls == [[str(control.LAUNCHCTL), "bootout", f"{DOMAIN}/{LABEL}"]]
    assert result["original_pid_exited"] is True and result["port_vacant"] is True
    assert result["evidence_preserved"] is True


def test_stop_fails_closed_if_pid_or_port_remains(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, META))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {"loaded": False, "pid": 77})
    monkeypatch.setattr(control, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(control, "_port_vacant", lambda port: False)
    ticks = iter((100.0, 111.0))
    monkeypatch.setattr(control.time, "monotonic", lambda: next(ticks))
    with pytest.raises(control.ControllerError, match="launchd_stop_unverified"):
        control.stop(str(tmp_path))


def test_reuse_keeps_same_root_and_requires_prior_pid_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    old = {**META, "observed_pid": 77}
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, old))
    monkeypatch.setattr(control, "_require_vacant_port", lambda port: None)
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {"loaded": False, "pid": None})
    monkeypatch.setattr(control, "_pid_alive", lambda pid: True)
    with pytest.raises(control.ControllerError, match="reuse_previous_pid_still_alive"):
        control.start(
            mode="product", seconds=10, port=7894, python="/fake/python",
            reuse_runtime_root=str(tmp_path),
        )


def test_run_files_are_unique_per_label() -> None:
    assert control._run_file(LABEL, "stdout.log") != control._run_file(
        control.LABEL_PREFIX + "fedcba9876543210", "stdout.log"
    )


def test_second_run_preserves_first_run_files(tmp_path: Path) -> None:
    layout = control.base.build_runtime_layout(tmp_path)
    source_profile = tmp_path / "source.sb"
    source_profile.write_text("(version 1)\n", encoding="utf-8")
    first = LABEL
    second = control.LABEL_PREFIX + "fedcba9876543210"
    for label in (first, second):
        profile = control._snapshot_profile(source_profile, tmp_path, label)
        control._write_job(
            layout, label=label, command=["/usr/bin/sandbox-exec", "-f", str(profile), "/bin/true"],
            env={}, mode="dry-run", port=None,
        )
    first_metadata = tmp_path / control._run_file(first, "json")
    first_log = tmp_path / control._run_file(first, "stdout.log")
    first_plist = tmp_path / control._run_file(first, "plist")
    first_profile = tmp_path / control._run_file(first, "sandbox.sb")
    assert first_metadata.is_file() and first_plist.is_file() and first_profile.is_file()
    assert first_log.read_bytes() == b""
    assert first_profile.read_text(encoding="utf-8") == "(version 1)\n"
    assert (tmp_path / control._run_file(second, "json")).is_file()


def test_verify_ready_requires_exact_pid_port_and_http_200(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata = {**META, "observed_pid": 88, "preflight_import_scope": control.PREFLIGHT_IMPORT_SCOPE}
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, metadata))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {"loaded": True, "pid": 88})
    monkeypatch.setattr(control, "_pid_alive", lambda pid: pid == 88)
    monkeypatch.setattr(control, "_pid_owned_alive", lambda pid: pid == 88)
    checks = []
    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid, port: checks.append((pid, port)) or True)

    class Response:
        status = 200

        def read(self, size):
            return b"<"

    class Connection:
        def __init__(self, host, port, timeout):
            checks.append((host, port, timeout))

        def request(self, method, path):
            checks.append((method, path))

        def getresponse(self):
            return Response()

        def close(self):
            checks.append("closed")

    monkeypatch.setattr(control.http.client, "HTTPConnection", Connection)
    result = control.verify_ready(str(tmp_path))
    assert result["ready"] is True and result["http_status"] == 200
    assert checks.count((88, 7894)) == 2
    assert ("GET", "/") in checks


def test_verify_ready_rejects_wrong_port_owner_without_http(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata = {**META, "observed_pid": 88}
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, metadata))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {"loaded": True, "pid": 88})
    monkeypatch.setattr(control, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(control, "_pid_owned_alive", lambda pid: True)
    monkeypatch.setattr(control, "_listener_owned_by_pid", lambda pid, port: False)
    with pytest.raises(control.ControllerError, match="product_not_ready_or_not_own_listener"):
        control.verify_ready(str(tmp_path))


def test_python_probe_uses_explicit_python_curated_env_sandbox_alarm_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    layout = {"runtime_root": tmp_path}
    python = "/test/venv/bin/python"
    captured = {}
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_new_root", lambda: (tmp_path, layout))
    monkeypatch.setattr(control, "_isolated_env", lambda layout, port: {"URUHA_WEB_PORT": str(port)})
    monkeypatch.setattr(control.base, "resolve_python", lambda explicit, env: Path(explicit))
    monkeypatch.setattr(control.sandbox, "write_sandbox_profile", lambda root: tmp_path / "source.sb")
    monkeypatch.setattr(control, "_snapshot_profile", lambda *a: tmp_path / "frozen.sb")
    monkeypatch.setattr(control.sandbox, "sandbox_command", lambda profile, cmd: ["sandbox-exec", *cmd])

    def write_job(layout, **kwargs):
        captured.update(kwargs)
        return {
            "label": LABEL, "plist_file": "test.plist", "preflight_import_scope": "none",
            "python_path": python, "probe_limit_seconds": 12,
        }

    monkeypatch.setattr(control, "_write_job", write_job)
    monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: _result(0))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: {
        "loaded": True, "pid": 9999, "last_exit_code": "(never exited)",
    })
    monkeypatch.setattr(control, "_pid_owned_alive", lambda pid: True)
    monkeypatch.setattr(control, "_record_observed_pid", lambda root, metadata, pid: metadata)
    monkeypatch.setattr(control, "_publish_current", lambda root, metadata: None)
    monkeypatch.setattr(control, "_probe_outcome", lambda *a: {"probe_outcome": "running"})
    result = control.start(mode="python-probe", seconds=12, port=7894, python=python)
    assert captured["mode"] == "python-probe"
    assert captured["env"] == {"URUHA_WEB_PORT": "7894"}
    assert captured["command"][-6:] == [
        "/usr/bin/perl", "-e", "alarm(12); exec @ARGV",
        python, "-c", control.PYTHON_PROBE_SNIPPET,
    ]
    assert result["probe_outcome"] == "running" and result["ready"] is False
    assert result["lifecycle_status"] == "python_probe_bootstrapped"


def test_python_probe_outcome_requires_marker_and_zero_exit(tmp_path: Path) -> None:
    stdout = tmp_path / "probe.stdout.log"
    stdout.write_bytes(b"python-ready\n")
    stdout.chmod(0o600)
    metadata = {
        "stdout_file": stdout.name, "python_path": "/test/python", "probe_limit_seconds": 12,
    }
    assert control._probe_outcome(tmp_path, metadata, {"pid": None, "last_exit_code": "0"})["probe_outcome"] == "passed"
    assert control._probe_outcome(tmp_path, metadata, {"pid": None, "last_exit_code": "142"})["probe_outcome"] == "failed"
    stdout.write_bytes(b"almost-python-ready\n")
    assert control._probe_outcome(tmp_path, metadata, {"pid": None, "last_exit_code": "0"})["probe_outcome"] == "failed"
    assert control._probe_outcome(tmp_path, metadata, {
        "pid": None, "state": "not running", "last_exit_code": None,
        "last_terminating_signal": "Alarm clock: 14",
    })["probe_outcome"] == "timed_out"


def test_python_probe_stop_allows_unobserved_completed_pid_without_claim(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata = {"label": LABEL, "mode": "python-probe"}
    states = iter(({"loaded": True, "pid": None}, {"loaded": False, "pid": None}))
    monkeypatch.setattr(control, "gui_domain", lambda: DOMAIN)
    monkeypatch.setattr(control, "_root_with_metadata", lambda requested: (tmp_path, metadata))
    monkeypatch.setattr(control, "_job_status", lambda *a, **k: next(states))
    monkeypatch.setattr(control.subprocess, "run", lambda *a, **k: _result(0))
    monkeypatch.setattr(control, "_record_stop", lambda *a: None)
    monkeypatch.setattr(control, "_probe_outcome", lambda *a: {"probe_outcome": "failed"})
    result = control.stop(str(tmp_path))
    assert result["original_pid_observed"] is False
    assert result["original_pid_exited"] is None
    assert result["after"]["loaded"] is False
