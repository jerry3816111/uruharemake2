"""Fake-only checks for the one-use v2 macOS fixture oracle.

No test invokes --execute, starts a listener/sandbox, or sends model/Web I/O.
"""

import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import struct
import subprocess
from types import SimpleNamespace

import pytest

import p4_b_child_local_identity_fixture_v2_preflight as probe
import uruha_p4_b_child_local_identity as identity


def _subject(role="a"):
    return {
        "pid": 21, "port": 54321, "parent": 20,
        "raw": [21, 20, 100, 7], "argv_sha256": "d" * 64, "role": role,
    }


def test_matrix_uses_adapter_snapshot_generation_digest_env_and_listener(monkeypatch):
    subject = _subject()
    snapshot = identity.ProcessSnapshot(
        21, 20, 100, 7, "/opt/python",
        ("/opt/python", "/tmp/new-probe.py", "--listen-a"),
        {probe.ENV_KEY: True},
    )
    monkeypatch.setattr(identity, "observe_process", lambda pid, env: snapshot)
    monkeypatch.setattr(identity, "argv_digest", lambda snap: "d" * 64)
    monkeypatch.setattr(identity, "owns_loopback_listener", lambda pid, port: True)
    assert probe._measure_one(subject, "a") == {
        "a_raw": True, "a_argv": True, "a_env": True,
        "a_listener": True, "a_parent": True,
    }


@pytest.mark.parametrize("change,field", [
    ("microsecond", "a_raw"), ("parent", "a_parent"),
    ("digest", "a_argv"), ("environment", "a_env"),
    ("listener", "a_listener"),
])
def test_each_field_has_independent_negative(monkeypatch, change, field):
    subject = _subject()
    snapshot = identity.ProcessSnapshot(
        21, 20 if change != "parent" else 19,
        100, 8 if change == "microsecond" else 7,
        "/opt/python", ("/opt/python",), {probe.ENV_KEY: change != "environment"},
    )
    monkeypatch.setattr(identity, "observe_process", lambda pid, env: snapshot)
    monkeypatch.setattr(identity, "argv_digest",
                        lambda snap: "e" * 64 if change == "digest" else "d" * 64)
    monkeypatch.setattr(identity, "owns_loopback_listener",
                        lambda pid, port: change != "listener")
    result = probe._measure_one(subject, "a")
    assert result[field] is False


def test_dead_process_is_rejected_without_listener_fallback(monkeypatch):
    def dead(_pid, _env):
        raise identity.ProbeError("process_generation_unavailable")
    monkeypatch.setattr(identity, "observe_process", dead)
    monkeypatch.setattr(identity, "owns_loopback_listener", lambda pid, port: False)
    assert probe._measure_one(_subject(), "b") == {
        "b_raw": False, "b_argv": False, "b_env": False,
        "b_listener": False, "b_parent": False,
    }


def _good_result():
    return {
        "schema": probe.SCHEMA, "status": "adapter_visibility_feasible",
        "positive": {key: True for key in probe.FIELDS},
        "negative": {
            key: key in probe.A_FIELDS for key in probe.FIELDS
        },
        "negative_rejected": True, "same_observer": True,
        "cleanup_verified": True,
        "a_exit_code": -signal.SIGTERM, "b_exit_code": -signal.SIGTERM,
        "observer_exit_code": 0, "active_wall_s": 0.25, "total_wall_s": 0.4,
        "source_sha256": probe._sha(probe.SCRIPT),
        "adapter_sha256": probe._sha(probe.ADAPTER),
        "profile_sha256": probe.PROFILE_SHA256,
        "model_calls": 0, "web_sends": 0, "b_sends": 0,
        "fixture_checks": {role: {
            key: key != "legacy_symlink_exact"
            for key in probe.FIXTURE_FIELDS
        } for role in ("a", "b")},
    }


def test_go_result_requires_full_positive_negative_and_zero_calls():
    result = _good_result()
    assert probe._valid_result(result, {"active_wall_s": 0.25})
    for mutation in ("missing_field", "stale_b", "other_observer", "provider_call",
                     "source_drift", "adapter_drift", "cleanup_failed"):
        changed = json.loads(json.dumps(result))
        if mutation == "missing_field":
            changed["positive"].pop("a_env")
        elif mutation == "stale_b":
            changed["negative"]["b_raw"] = True
        elif mutation == "other_observer":
            changed["same_observer"] = False
        elif mutation == "provider_call":
            changed["model_calls"] = 1
        elif mutation == "source_drift":
            changed["source_sha256"] = "0" * 64
        elif mutation == "adapter_drift":
            changed["adapter_sha256"] = "0" * 64
        else:
            changed["cleanup_verified"] = False
        assert not probe._valid_result(changed, {"active_wall_s": 0.25}), mutation


def test_old_result_cannot_be_mislabeled_as_new_adapter_pass():
    changed = _good_result()
    changed["schema"] = "p4_b_ps_free_identity_feasibility_v1"
    assert not probe._valid_result(changed, {"active_wall_s": 0.25})


def test_cleanup_never_signals_reused_pid(monkeypatch):
    class Proc:
        pid = 21
        returncode = None
    monkeypatch.setattr(identity, "raw_generation", lambda pid: (21, 20, 100, 8))
    signaled = []
    monkeypatch.setattr(probe.os, "kill", lambda pid, signum: signaled.append((pid, signum)))
    assert not probe._stop_exact(Proc(), (21, 20, 100, 7), probe.time.monotonic() + 1)
    assert signaled == []


def test_cleanup_never_signals_unowned_group(monkeypatch):
    class Proc:
        pid = 21
        returncode = None
    monkeypatch.setattr(probe, "_group_gone", lambda _pgid: False)
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: (21, 20, 100, 7))
    monkeypatch.setattr(probe.os, "getpgid", lambda _pid: 20)
    signaled = []
    monkeypatch.setattr(probe.os, "killpg",
                        lambda pgid, signum: signaled.append((pgid, signum)))
    assert not probe._stop_owned_group(
        Proc(), (21, 20, 100, 7), 21, probe.time.monotonic() + 1)
    assert signaled == []


def test_group_cleanup_rejects_same_second_pid_reuse_before_signal(monkeypatch):
    class Proc:
        pid = 21
        returncode = None
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: (21, 20, 100, 8))
    monkeypatch.setattr(probe.os, "getpgid", lambda _pid: 21)
    signaled = []
    monkeypatch.setattr(probe.os, "killpg",
                        lambda pgid, signum: signaled.append((pgid, signum)))
    assert not probe._stop_owned_group(
        Proc(), (21, 20, 100, 7), 21, probe.time.monotonic() + 1)
    assert signaled == []


def test_group_cleanup_refuses_missing_initial_raw_witness(monkeypatch):
    class Proc:
        pid = 21
        returncode = None
    signaled = []
    monkeypatch.setattr(probe.os, "killpg",
                        lambda pgid, signum: signaled.append((pgid, signum)))
    assert not probe._stop_owned_group(
        Proc(), None, 21, probe.time.monotonic() + 1)
    assert signaled == []


def test_public_default_requires_explicit_execute(capsys):
    assert probe.main([]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "ok": False, "reason": "explicit_execute_required",
    }


def test_public_result_fields_do_not_include_raw_argv_or_environment():
    result = _good_result()
    assert set(result) == probe.RESULT_FIELDS
    assert not any("argv" in key or "env" in key for key in result)
    assert hashlib.sha256(probe.SCRIPT.read_bytes()).hexdigest() == result["source_sha256"]


def _fixture_snapshot(*, executable=None, argv=None, ppid=20, usec=7, env=True):
    return identity.ProcessSnapshot(
        21, ppid, 100, usec, executable or str(probe.APP_BINARY),
        tuple(argv or (str(probe.APP_BINARY), str(probe.SCRIPT), "--listen-a")),
        {probe.ENV_KEY: env},
    )


def _stub_fixture(monkeypatch, snapshot, *, raw=(21, 20, 100, 7), listener=True,
                  app_sha=None):
    monkeypatch.setattr(identity, "observe_process", lambda _pid, _env: snapshot)
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: raw)
    monkeypatch.setattr(identity, "owns_loopback_listener", lambda _pid, _port: listener)
    monkeypatch.setattr(probe, "_sha", lambda _path: app_sha or probe.APP_SHA256)


def test_fixture_accepts_app_identity_and_treats_legacy_symlink_as_diagnostic(monkeypatch):
    _stub_fixture(monkeypatch, _fixture_snapshot())
    subject, bits = probe._fixture_subject(21, 54321, "a", 20, (21, 20, 100, 7))
    assert subject is not None
    assert all(bits[key] for key in probe.FIXTURE_AUTHORITY)
    assert bits["legacy_symlink_exact"] is False
    assert subject["argv_sha256"] == identity.argv_digest(_fixture_snapshot())


@pytest.mark.parametrize("mutation,field", [
    ("wrong_app_path", "app_path_sha_exact"),
    ("wrong_argv0", "app_path_sha_exact"),
    ("wrong_app_hash", "app_path_sha_exact"),
    ("wrong_tail", "argv_tail_exact"),
    ("extra_arg", "argv_tail_exact"),
    ("new_usec", "raw"),
    ("wrong_ppid", "parent"),
    ("missing_env", "env"),
    ("listener", "listener"),
])
def test_each_fixture_authority_bit_fails_closed(monkeypatch, mutation, field):
    kwargs = {}
    if mutation == "wrong_app_path":
        kwargs["executable"] = "/other/Python"
    elif mutation == "wrong_argv0":
        kwargs["argv"] = ("/other/Python", str(probe.SCRIPT), "--listen-a")
    elif mutation == "wrong_tail":
        kwargs["argv"] = (str(probe.APP_BINARY), str(probe.SCRIPT), "--listen-b")
    elif mutation == "extra_arg":
        kwargs["argv"] = (str(probe.APP_BINARY), str(probe.SCRIPT), "--listen-a", "--extra")
    elif mutation == "wrong_ppid":
        kwargs["ppid"] = 19
    elif mutation == "missing_env":
        kwargs["env"] = False
    _stub_fixture(
        monkeypatch, _fixture_snapshot(**kwargs),
        raw=(21, 20, 100, 8) if mutation == "new_usec" else (21, 20, 100, 7),
        listener=mutation != "listener",
        app_sha="0" * 64 if mutation == "wrong_app_hash" else None,
    )
    subject, bits = probe._fixture_subject(21, 54321, "a", 20, (21, 20, 100, 7))
    assert subject is None
    assert bits[field] is False
    assert set(bits) == probe.FIXTURE_FIELDS


def test_initial_raw_generation_is_authoritative_and_other_bits_survive_probe_error(
    monkeypatch,
):
    _stub_fixture(monkeypatch, _fixture_snapshot())
    _, stale = probe._fixture_subject(21, 54321, "a", 20, (21, 20, 100, 8))
    assert stale["raw"] is False
    assert stale["app_path_sha_exact"] is True
    assert stale["argv_tail_exact"] is True
    def unavailable(_pid):
        raise identity.ProbeError("process_generation_unavailable")
    monkeypatch.setattr(identity, "raw_generation", unavailable)
    _, bits = probe._fixture_subject(21, 54321, "a", 20, (21, 20, 100, 7))
    assert bits["raw"] is False
    assert bits["parent"] is True
    assert bits["env"] is True
    assert bits["listener"] is True
    assert bits["app_path_sha_exact"] is True
    assert bits["argv_tail_exact"] is True


def test_adapter_procargs_missing_duplicate_and_bad_utf8_are_not_env_proof():
    prefix = (struct.pack("=i", 3) + str(probe.APP_BINARY).encode() + b"\0\0"
              + str(probe.APP_BINARY).encode() + b"\0"
              + str(probe.SCRIPT).encode() + b"\0--listen-a\0")
    _, _, missing = identity._parse_procargs(prefix, {probe.ENV_KEY: "a"})
    assert missing == {probe.ENV_KEY: False}
    for suffix in (
        f"{probe.ENV_KEY}=a\0{probe.ENV_KEY}=a\0".encode(),
        f"{probe.ENV_KEY}=a\0".encode() + b"OTHER=\xff\0",
    ):
        with pytest.raises(identity.ProbeError, match="^procargs_invalid$"):
            identity._parse_procargs(prefix + suffix, {probe.ENV_KEY: "a"})


@pytest.mark.parametrize("owner_rows,detail", [
    ("21\n22\n", ""),
    ("21\n", "python 21 u 5u IPv4 TCP *:54321 (LISTEN)\n"),
])
def test_fixture_listener_rejects_nonunique_or_nonloopback(monkeypatch, owner_rows, detail):
    replies = iter([
        subprocess.CompletedProcess([], 0, owner_rows, ""),
        subprocess.CompletedProcess([], 0, detail, ""),
    ])
    monkeypatch.setattr(identity, "_run_lsof", lambda _argv: next(replies))
    assert not identity.owns_loopback_listener(21, 54321)


def _fake_frozen_anchors(monkeypatch, *, mutation=None):
    first = probe.PYTHON
    second = first.parent / "python3.12"
    target = probe.VENV_TARGET
    app = probe.APP_BINARY
    links = {
        first: "python3.12", second: str(target),
    }
    hashes = {
        probe.PROFILE: probe.PROFILE_SHA256,
        app: probe.APP_SHA256,
        target: probe.VENV_TARGET_SHA256,
    }
    facts = {
        first: SimpleNamespace(st_mode=stat.S_IFLNK, st_uid=501, st_ino=37200054),
        second: SimpleNamespace(st_mode=stat.S_IFLNK, st_uid=501, st_ino=37200053),
        target: SimpleNamespace(st_mode=stat.S_IFREG, st_uid=0, st_nlink=1,
                                st_ino=889709),
        app: SimpleNamespace(st_mode=stat.S_IFREG, st_uid=0, st_nlink=1,
                             st_ino=889937),
        probe.PROFILE: SimpleNamespace(st_mode=stat.S_IFREG),
        probe.SCRIPT: SimpleNamespace(st_mode=stat.S_IFREG),
        probe.ADAPTER: SimpleNamespace(st_mode=stat.S_IFREG),
    }
    if mutation == "first_link":
        links[first] = "other"
    elif mutation == "second_link":
        links[second] = "/other/Python"
    elif mutation == "first_owner":
        facts[first].st_uid = 502
    elif mutation == "second_owner":
        facts[second].st_uid = 502
    elif mutation == "app_inode":
        facts[app].st_ino = 1
    elif mutation == "app_symlink":
        facts[app].st_mode = stat.S_IFLNK
    elif mutation == "venv_target_symlink":
        facts[target].st_mode = stat.S_IFLNK
    elif mutation == "app_hash":
        hashes[app] = "0" * 64
    elif mutation == "venv_target_hash":
        hashes[target] = "0" * 64
    elif mutation == "profile_hash":
        hashes[probe.PROFILE] = "0" * 64
    original_stat = Path.stat
    original_lstat = Path.lstat
    original_readlink = os.readlink
    monkeypatch.setattr(
        Path, "stat", lambda path, *a, **kw: facts.get(path) or original_stat(path, *a, **kw))
    monkeypatch.setattr(
        Path, "lstat", lambda path, *a, **kw: facts.get(path) or original_lstat(path, *a, **kw))
    monkeypatch.setattr(
        os, "readlink", lambda path: links.get(Path(path)) or original_readlink(path))
    monkeypatch.setattr(probe, "_sha", lambda path: hashes.get(path, "0" * 64))


@pytest.mark.parametrize("mutation", [
    None, "first_link", "second_link", "first_owner", "second_owner",
    "app_inode", "app_symlink", "venv_target_symlink",
    "app_hash", "venv_target_hash", "profile_hash",
])
def test_exact_prelaunch_anchors(monkeypatch, mutation):
    _fake_frozen_anchors(monkeypatch, mutation=mutation)
    assert probe._frozen_anchors_valid() is (mutation is None)


def test_supervisor_rejects_anchor_drift_before_worker(monkeypatch):
    monkeypatch.setattr(probe, "_frozen_anchors_valid", lambda: False)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **kw:
                        pytest.fail("worker must not start"))
    result = probe._supervise()
    assert result["status"] == "platform_source_or_profile_unavailable"
    assert result["cleanup_verified"] is True
    assert result["fixture_checks"] == {}


def test_worker_rechecks_anchor_before_listener(monkeypatch):
    monkeypatch.setattr(probe, "_frozen_anchors_valid", lambda: False)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **kw:
                        pytest.fail("listener must not start"))
    monkeypatch.setattr(probe, "_write", lambda _stream, _value: None)
    result = probe._worker()
    assert result["status"] == "platform_source_or_profile_unavailable"
    assert result["fixture_checks"] == {}


def test_a_fixture_failure_keeps_bits_and_verifies_ready_listener_cleanup(monkeypatch):
    class Proc:
        pid = 21
        returncode = -signal.SIGTERM
        stdout = io.BytesIO()
        stdin = None

    starts = []
    def start(*_args, **_kwargs):
        starts.append(True)
        return Proc()
    bits = {key: True for key in probe.FIXTURE_FIELDS}
    bits["argv_tail_exact"] = False
    checked = []
    monkeypatch.setattr(probe, "_frozen_anchors_valid", lambda: True)
    monkeypatch.setattr(probe.subprocess, "Popen", start)
    monkeypatch.setattr(identity, "raw_generation", lambda pid:
                        (pid, os.getpid(), 100, 7))
    monkeypatch.setattr(probe, "_Reader", lambda _stream: SimpleNamespace(
        read=lambda _deadline: {"pid": 21, "port": 54321}))
    monkeypatch.setattr(probe, "_fixture_subject", lambda *_args:
                        (None, dict(bits)))
    monkeypatch.setattr(probe, "_stop_exact", lambda *_args: True)
    monkeypatch.setattr(identity, "owns_loopback_listener", lambda pid, port:
                        checked.append((pid, port)) or False)
    monkeypatch.setattr(probe, "_write", lambda _stream, _value: None)
    result = probe._worker()
    assert result["status"] == "fixture_invalid"
    assert result["fixture_checks"] == {"a": bits}
    assert result["cleanup_verified"] is True
    assert starts == [True]
    assert checked == [(21, 54321)]


def test_fixture_failure_keeps_a_only_bits_for_supervisor():
    result = _good_result()
    result.update({
        "status": "fixture_invalid", "positive": {}, "negative": {},
        "negative_rejected": False, "same_observer": False,
        "b_exit_code": None, "observer_exit_code": None,
    })
    result["fixture_checks"] = {"a": dict(result["fixture_checks"]["a"])}
    result["fixture_checks"]["a"]["argv_tail_exact"] = False
    assert probe._valid_result(result, {"active_wall_s": 0.25})
    result["fixture_checks"]["a"]["argv_tail_exact"] = True
    assert not probe._valid_result(result, {"active_wall_s": 0.25})


@pytest.mark.parametrize("worker_exit,expected", [
    (-signal.SIGTERM, "adapter_visibility_feasible"),
    (0, "worker_exit_unexpected"),
])
def test_supervisor_requires_expected_worker_exit(monkeypatch, worker_exit, expected):
    class Worker:
        pid = 21
        returncode = None
        stdout = io.BytesIO()
        stdin = io.BytesIO()
    worker = Worker()
    messages = iter([
        {"phase": "cleanup_started", "active_wall_s": 0.25},
        _good_result(),
    ])
    monkeypatch.setattr(probe, "_frozen_anchors_valid", lambda: True)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *_a, **_kw: worker)
    monkeypatch.setattr(identity, "raw_generation", lambda _pid: (21, 20, 100, 7))
    monkeypatch.setattr(probe.os, "getpgid", lambda _pid: 21)
    monkeypatch.setattr(probe, "_Reader", lambda _stream: SimpleNamespace(
        read=lambda _deadline: next(messages)))
    def stop(_worker, _raw, _pgid, _deadline):
        worker.returncode = worker_exit
        return True
    monkeypatch.setattr(probe, "_stop_owned_group", stop)
    result = probe._supervise()
    assert result["status"] == expected
    assert result["worker_exit_code"] == worker_exit


def test_result_rejects_forged_or_missing_fixture_bits():
    for mutation in ("missing_role", "missing_bit", "authority_false", "nonbool"):
        result = _good_result()
        if mutation == "missing_role":
            result["fixture_checks"].pop("b")
        elif mutation == "missing_bit":
            result["fixture_checks"]["a"].pop("raw")
        elif mutation == "authority_false":
            result["fixture_checks"]["a"]["env"] = False
        else:
            result["fixture_checks"]["a"]["raw"] = 1
        assert not probe._valid_result(result, {"active_wall_s": 0.25})


def test_reaped_direct_child_never_signaled(monkeypatch):
    class Proc:
        pid = 21
        returncode = -signal.SIGTERM
    monkeypatch.setattr(probe.os, "kill", lambda _pid, _sig:
                        pytest.fail("reaped child must not be signaled"))
    assert probe._stop_exact(Proc(), (21, 20, 100, 7), probe.time.monotonic() + 1)
