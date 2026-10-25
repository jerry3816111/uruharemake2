"""Fake-only checks for the one-use NEW-adapter sandbox harness.

No test invokes --execute, starts a listener/sandbox, or sends model/Web I/O.
"""

import hashlib
import json
import signal

import pytest

import p4_b_child_local_identity_sandbox_preflight as probe
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
