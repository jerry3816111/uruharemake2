"""Fake-only contract tests; no process, sandbox, model or Web is started."""

import hashlib
import json
import struct
import subprocess

import pytest

import uruha_p4_b_child_local_identity as identity


def _raw(*, executable="/opt/FrameworkPython", argv=None, env=(), argc=None):
    arguments = ["/opt/venv/python3.12", "/tmp/observer.py", "--runner"] if argv is None else argv
    count = len(arguments) if argc is None else argc
    return (struct.pack("=i", count) + executable.encode() + b"\0\0" +
            b"\0".join(part.encode() for part in [*arguments, *env]) + b"\0")


def test_procargs_preserves_different_exec_and_argv_zero():
    executable, argv, exact = identity._parse_procargs(_raw(env=(
        "OLLAMA_MODELS=/private/models", "OLLAMA_NO_CLOUD=1",
    )), {"OLLAMA_MODELS": "/private/models", "OLLAMA_NO_CLOUD": "1"})
    assert executable == "/opt/FrameworkPython"
    assert argv[0] == "/opt/venv/python3.12"
    assert exact == {"OLLAMA_MODELS": True, "OLLAMA_NO_CLOUD": True}


@pytest.mark.parametrize("env", [
    ("OLLAMA_MODELS=/other",),
    (),
])
def test_environment_requires_one_exact_assignment_after_argv(env):
    _, _, exact = identity._parse_procargs(
        _raw(argv=["/opt/venv/python3.12", "OLLAMA_MODELS=/private/models"], env=env),
        {"OLLAMA_MODELS": "/private/models"},
    )
    assert exact == {"OLLAMA_MODELS": False}


@pytest.mark.parametrize("raw", [
    _raw(env=("OLLAMA_MODELS=/private/models", "OLLAMA_MODELS=/private/models")),
    _raw(env=("OLLAMA_MODELS=/private/models", "OLLAMA_MODELS=/other")),
    _raw(env=("OLLAMA_MODELS=/private/models",)) + b"OTHER=\xff\0",
    _raw(env=("OLLAMA_MODELS=/private/models", "INVALID-KEY=value")),
    _raw(env=("OLLAMA_MODELS=/private/models", "NO_EQUALS")),
])
def test_duplicate_or_malformed_environment_fails_closed(raw):
    with pytest.raises(identity.ProbeError, match="^procargs_invalid$"):
        identity._parse_procargs(raw, {"OLLAMA_MODELS": "/private/models"})


def test_environment_key_in_argv_cannot_satisfy_oracle():
    _, argv, exact = identity._parse_procargs(
        _raw(argv=["/opt/venv/python3.12", "OLLAMA_NO_CLOUD=1"]),
        {"OLLAMA_NO_CLOUD": "1"},
    )
    assert argv[1] == "OLLAMA_NO_CLOUD=1"
    assert exact == {"OLLAMA_NO_CLOUD": False}


@pytest.mark.parametrize("raw", [
    b"short",
    _raw(argc=0),
    _raw(argc=65),
    _raw(argc=4),
    _raw()[:-1],
    struct.pack("=i", 1) + b"/opt/python\0\0\xff\0",
])
def test_malformed_procargs_rejected(raw):
    with pytest.raises(identity.ProbeError, match="^procargs_invalid$"):
        identity._parse_procargs(raw)


def test_expected_environment_shape_rejected_without_echoing_value():
    with pytest.raises(identity.ProbeError, match="^expected_environment_invalid$") as caught:
        identity._parse_procargs(_raw(), {"OLLAMA-MODELS": "private-secret"})
    assert "private-secret" not in str(caught.value)


def test_observe_rejects_same_pid_new_microsecond_generation(monkeypatch):
    observations = iter([(18, 17, 100, 7), (18, 17, 100, 8)])
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: next(observations))
    monkeypatch.setattr(identity, "_procargs", lambda _pid, _env: (
        "/opt/python", ("/opt/python", "--runner"), {},
    ))
    with pytest.raises(identity.ProbeError, match="^process_generation_drift$"):
        identity.observe_process(18)


def test_observe_preserves_one_exact_generation_and_env_booleans(monkeypatch):
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: (18, 17, 100, 7))
    monkeypatch.setattr(identity, "_procargs", lambda _pid, _env: (
        "/opt/FrameworkPython", ("/opt/venv/python", "--runner"),
        {"OLLAMA_MODELS": True},
    ))
    result = identity.observe_process(18, {"OLLAMA_MODELS": "/private/models"})
    assert result == identity.ProcessSnapshot(
        18, 17, 100, 7, "/opt/FrameworkPython",
        ("/opt/venv/python", "--runner"), {"OLLAMA_MODELS": True},
    )


def test_listener_owner_must_be_unique_exact_loopback(monkeypatch):
    calls = []
    output = iter([
        subprocess.CompletedProcess([], 0, "18\n", ""),
        subprocess.CompletedProcess([], 0, "python 18 user 5u IPv4 0 TCP 127.0.0.1:55555 (LISTEN)\n", ""),
    ])

    def run(argv):
        calls.append(argv)
        return next(output)

    monkeypatch.setattr(identity, "_run_lsof", run)
    assert identity.owns_loopback_listener(18, 55555)
    assert all(argv[0] == "/usr/sbin/lsof" for argv in calls)


@pytest.mark.parametrize("owner_rows", ["18\n19\n", "19\n", "", "not-a-pid\n"])
def test_listener_rejects_nonunique_or_wrong_owner(monkeypatch, owner_rows):
    monkeypatch.setattr(identity, "_run_lsof", lambda _argv: (
        subprocess.CompletedProcess([], 0, owner_rows, "")))
    assert not identity.owns_loopback_listener(18, 55555)


def test_listener_rejects_nonloopback_detail(monkeypatch):
    output = iter([
        subprocess.CompletedProcess([], 0, "18\n", ""),
        subprocess.CompletedProcess([], 0, "python 18 user 5u IPv4 0 TCP *:55555 (LISTEN)\n", ""),
    ])
    monkeypatch.setattr(identity, "_run_lsof", lambda _argv: next(output))
    assert not identity.owns_loopback_listener(18, 55555)


def test_listener_failure_is_false_not_exception_or_fallback(monkeypatch):
    def unavailable(_argv):
        raise identity.ProbeError("listener_observer_unavailable")
    monkeypatch.setattr(identity, "_run_lsof", unavailable)
    assert not identity.owns_loopback_listener(18, 55555)


def test_exact_exec_and_argv_digest_contract():
    snap = identity.ProcessSnapshot(18, 17, 100, 7, "/opt/FrameworkPython",
                                    ("/opt/venv/python", "--runner"), {})
    expected_raw = json.dumps(
        {"executable": snap.executable, "argv": list(snap.argv)},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()
    assert identity.argv_digest(snap) == hashlib.sha256(expected_raw).hexdigest()
    other = identity.ProcessSnapshot(18, 17, 100, 7, "/opt/python",
                                     snap.argv, {})
    assert identity.argv_digest(other) != identity.argv_digest(snap)
    assert "/opt/venv/python" not in repr(snap)


def test_invalid_pid_fails_before_os_access():
    with pytest.raises(identity.ProbeError, match="^process_pid_invalid$"):
        identity.raw_generation(0)
