#!/usr/bin/env python3
"""One-use, zero-model sandbox preflight for the NEW B child-local observer.

This observes two controlled Python listeners.  It is not an Ollama, Web,
provider, token, or product-ready test.  The public entry requires --execute;
source/profile/input/oracle review and a frozen PR head must precede that call.
Only fixed booleans, reason codes, exit codes, and timing leave the worker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import socket
import subprocess
import sys
import time
from typing import BinaryIO

import uruha_p4_b_child_local_identity as identity


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent
PYTHON = ROOT / ".venv/product_checks/bin/python"
ADAPTER = ROOT / "uruha_p4_b_child_local_identity.py"
PROFILE = Path(
    "/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/"
    "uruha-product-xremdzdp/"
    "p4_preference_fallback_detached.6a0185bb8bc10e98.sandbox.sb"
)
PROFILE_SHA256 = "5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110"
ACTIVE_LIMIT_S = 30.0
CLEANUP_LIMIT_S = 10.0
MAX_LINE = 4096
SCHEMA = "p4_b_child_local_adapter_sandbox_preflight_v1"
ENV_KEY = "URUHA_B_IDENTITY_SYNTHETIC_ROLE"
FIELDS = frozenset({
    "a_raw", "b_raw", "a_argv", "b_argv", "a_env", "b_env",
    "a_listener", "b_listener", "a_parent", "b_parent",
})
A_FIELDS = frozenset({"a_raw", "a_argv", "a_env", "a_listener", "a_parent"})
B_FIELDS = FIELDS - A_FIELDS
RESULT_FIELDS = frozenset({
    "schema", "status", "positive", "negative", "negative_rejected",
    "same_observer", "cleanup_verified", "a_exit_code", "b_exit_code",
    "observer_exit_code", "active_wall_s", "total_wall_s", "source_sha256",
    "adapter_sha256", "profile_sha256", "model_calls", "web_sends", "b_sends",
})


class PreflightError(RuntimeError):
    """Fixed reason code; never render process argv or environment."""


def _fail(reason: str) -> None:
    raise PreflightError(reason)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _remaining(deadline: float, cap: float | None = None) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        _fail("deadline_exceeded")
    return left if cap is None else min(left, cap)


def _write(stream: BinaryIO, value: dict) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_LINE:
        _fail("protocol_oversize")
    try:
        stream.write(raw)
        stream.flush()
    except OSError:
        _fail("protocol_unavailable")


class _Reader:
    def __init__(self, stream: BinaryIO):
        self.fd = stream.fileno()
        self.pending = b""

    def read(self, deadline: float) -> dict:
        while b"\n" not in self.pending:
            if len(self.pending) > MAX_LINE:
                _fail("protocol_oversize")
            readable, _, _ = select.select([self.fd], [], [], _remaining(deadline))
            if not readable:
                _fail("protocol_timeout")
            chunk = os.read(self.fd, 4096)
            if not chunk:
                _fail("protocol_eof")
            self.pending += chunk
        line, self.pending = self.pending.split(b"\n", 1)
        if len(line) > MAX_LINE:
            _fail("protocol_oversize")
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError):
            _fail("protocol_invalid")
        if type(value) is not dict:
            _fail("protocol_invalid")
        return value


def _listen(role: str) -> int:
    if role not in ("a", "b") or os.environ.get(ENV_KEY) != role:
        return 2
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.set_inheritable(False)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        _write(sys.stdout.buffer, {"pid": os.getpid(), "port": server.getsockname()[1]})
        while True:
            time.sleep(0.2)
    finally:
        server.close()


def _subject(pid: int, port: int, role: str, parent: int) -> dict:
    """External oracle on an unreaped direct child; no raw data in result."""
    snap = identity.observe_process(pid, {ENV_KEY: role})
    raw = (snap.pid, snap.ppid, snap.start_sec, snap.start_usec)
    if (raw != identity.raw_generation(pid) or snap.ppid != parent
            or snap.argv != (str(PYTHON), str(SCRIPT), f"--listen-{role}")
            or snap.env_exact != {ENV_KEY: True}
            or not identity.owns_loopback_listener(pid, port)):
        _fail("fixture_invalid")
    return {
        "pid": pid, "port": port, "parent": parent, "raw": list(raw),
        "argv_sha256": identity.argv_digest(snap), "role": role,
    }


def _measure_one(subject: dict, prefix: str) -> dict[str, bool]:
    try:
        snap = identity.observe_process(subject["pid"], {ENV_KEY: subject["role"]})
        raw = [snap.pid, snap.ppid, snap.start_sec, snap.start_usec]
        generation = raw == subject["raw"]
        argv = identity.argv_digest(snap) == subject["argv_sha256"]
        env = snap.env_exact == {ENV_KEY: True}
        parent = snap.ppid == subject["parent"]
    except identity.ProbeError:
        generation = argv = env = parent = False
    try:
        listener = identity.owns_loopback_listener(subject["pid"], subject["port"])
    except identity.ProbeError:
        listener = False
    return {
        f"{prefix}_raw": generation, f"{prefix}_argv": argv,
        f"{prefix}_env": env, f"{prefix}_listener": listener,
        f"{prefix}_parent": parent,
    }


def _matrix(descriptor: dict) -> dict[str, bool]:
    return {
        **_measure_one(descriptor["a"], "a"),
        **_measure_one(descriptor["b"], "b"),
    }


def _observe() -> int:
    try:
        first = json.loads(sys.stdin.buffer.readline(MAX_LINE + 1))
        if (type(first) is not dict or set(first) != {"a", "b"}
                or any(type(value) is not dict for value in first.values())):
            _fail("observer_input_invalid")
        positive = _matrix(first)
        _write(sys.stdout.buffer, {
            "phase": "before", "pid": os.getpid(), "matrix": positive,
        })
        phase = json.loads(sys.stdin.buffer.readline(MAX_LINE + 1))
        if phase != {"phase": "after_b_reaped"}:
            _fail("observer_phase_invalid")
        negative = _matrix(first)
        _write(sys.stdout.buffer, {
            "phase": "after", "pid": os.getpid(), "matrix": negative,
        })
        return 0
    except (OSError, ValueError, KeyError, TypeError, PreflightError):
        return 2


def _stop_exact(proc: subprocess.Popen, raw: tuple[int, int, int, int] | None,
                deadline: float) -> bool:
    """Signal only a still-unreaped direct child with the captured raw tuple."""
    if proc is None or raw is None:
        return False
    if proc.returncode is not None:
        return True
    for signum in (signal.SIGTERM, signal.SIGKILL):
        if time.monotonic() >= deadline:
            return False
        try:
            if identity.raw_generation(proc.pid) != raw:
                return False
            os.kill(proc.pid, signum)
            proc.wait(timeout=min(0.8, _remaining(deadline)))
            return True
        except subprocess.TimeoutExpired:
            continue
        except identity.ProbeError:
            # A terminated but unreaped direct Popen child cannot have a reused
            # PID.  Reap it rather than misclassifying expected SIGTERM as drift.
            try:
                proc.wait(timeout=min(0.1, _remaining(deadline)))
                return True
            except (OSError, subprocess.TimeoutExpired, PreflightError):
                return False
        except (OSError, PreflightError):
            return False
    return False


def _alarm(_number, _frame):
    _fail("deadline_exceeded")


def _worker() -> dict:
    began = time.monotonic()
    deadline = began + ACTIVE_LIMIT_S
    a = b = observer = None
    a_raw = b_raw = observer_raw = None
    a_subject = b_subject = None
    positive: dict[str, bool] = {}
    negative: dict[str, bool] = {}
    status = "preflight_error"
    negative_rejected = same_observer = False
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, ACTIVE_LIMIT_S)
    try:
        if (sys.platform != "darwin" or not PYTHON.is_file()
                or not SCRIPT.is_file() or not ADAPTER.is_file()
                or not PROFILE.is_file() or _sha(PROFILE) != PROFILE_SHA256):
            _fail("platform_source_or_profile_unavailable")
        subjects = []
        for role in ("a", "b"):
            env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
                   ENV_KEY: role}
            proc = subprocess.Popen(
                [str(PYTHON), str(SCRIPT), f"--listen-{role}"], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, close_fds=True,
            )
            if role == "a":
                a = proc
                a_raw = identity.raw_generation(proc.pid)
            else:
                b = proc
                b_raw = identity.raw_generation(proc.pid)
            ready = _Reader(proc.stdout).read(deadline)
            if (set(ready) != {"pid", "port"} or ready["pid"] != proc.pid
                    or type(ready["port"]) is not int
                    or not (1024 <= ready["port"] <= 65535)):
                _fail("fixture_ready_invalid")
            subjects.append(_subject(proc.pid, ready["port"], role, os.getpid()))
        a_subject, b_subject = subjects
        if a_subject["port"] == b_subject["port"]:
            _fail("fixture_port_collision")
        descriptor = {"a": a_subject, "b": b_subject}
        observer = subprocess.Popen(
            ["/usr/bin/sandbox-exec", "-f", str(PROFILE),
             str(PYTHON), str(SCRIPT), "--observe"],
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        observer_raw = identity.raw_generation(observer.pid)
        reader = _Reader(observer.stdout)
        _write(observer.stdin, descriptor)
        before = reader.read(deadline)
        positive = before.get("matrix", {})
        if (set(before) != {"phase", "pid", "matrix"}
                or before["phase"] != "before" or before["pid"] != observer.pid
                or type(positive) is not dict or set(positive) != FIELDS
                or any(type(value) is not bool for value in positive.values())):
            _fail("observer_before_invalid")
        if not all(positive.values()):
            status = "no_go_missing_identity_field"
        else:
            if identity.raw_generation(b.pid) != b_raw:
                _fail("b_generation_drift_before_stop")
            b.terminate()  # direct unreaped child; PID cannot be reused
            if b.wait(timeout=_remaining(deadline, 2.0)) != -signal.SIGTERM:
                _fail("b_exit_unexpected")
            if identity.owns_loopback_listener(b.pid, b_subject["port"]):
                _fail("b_listener_not_gone")
            _write(observer.stdin, {"phase": "after_b_reaped"})
            after = reader.read(deadline)
            negative = after.get("matrix", {})
            if (set(after) != {"phase", "pid", "matrix"}
                    or after["phase"] != "after"
                    or after["pid"] != before["pid"]
                    or type(negative) is not dict or set(negative) != FIELDS
                    or any(type(value) is not bool for value in negative.values())):
                _fail("observer_after_invalid")
            same_observer = True
            negative_rejected = (all(negative[key] for key in A_FIELDS)
                                 and all(negative[key] is False for key in B_FIELDS))
            status = ("adapter_visibility_feasible" if negative_rejected
                      else "no_go_stale_observer")
    except PreflightError as exc:
        status = str(exc)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError,
            identity.ProbeError):
        status = "preflight_error"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        active_wall = time.monotonic() - began
        try:
            _write(sys.stdout.buffer, {
                "phase": "cleanup_started", "active_wall_s": round(active_wall, 6),
            })
        except PreflightError:
            # A closed supervisor pipe cannot disable exact own-PID cleanup.
            status = "cleanup_notice_unavailable"
        cleanup_deadline = time.monotonic() + CLEANUP_LIMIT_S
        stopped = [
            _stop_exact(proc, raw, cleanup_deadline)
            for proc, raw in ((observer, observer_raw), (b, b_raw), (a, a_raw))
            if proc is not None
        ]
        listener_gone = True
        for subject in (a_subject, b_subject):
            if subject is not None:
                try:
                    listener_gone &= not identity.owns_loopback_listener(
                        subject["pid"], subject["port"])
                except identity.ProbeError:
                    listener_gone = False
        cleanup_verified = all(stopped) and listener_gone
        for proc in (observer, b, a):
            if proc is not None and proc.stdout is not None:
                proc.stdout.close()
            if proc is not None and proc.stdin is not None:
                proc.stdin.close()
        if not cleanup_verified:
            status = "cleanup_review_required"
    return {
        "schema": SCHEMA, "status": status, "positive": positive,
        "negative": negative, "negative_rejected": negative_rejected,
        "same_observer": same_observer, "cleanup_verified": cleanup_verified,
        "a_exit_code": None if a is None else a.returncode,
        "b_exit_code": None if b is None else b.returncode,
        "observer_exit_code": None if observer is None else observer.returncode,
        "active_wall_s": round(active_wall, 6),
        "total_wall_s": round(time.monotonic() - began, 6),
        "source_sha256": _sha(SCRIPT), "adapter_sha256": _sha(ADAPTER),
        "profile_sha256": PROFILE_SHA256,
        "model_calls": 0, "web_sends": 0, "b_sends": 0,
    }


def _group_gone(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def _stop_owned_group(
    worker: subprocess.Popen, raw: tuple[int, int, int, int] | None,
    pgid: int | None, deadline: float,
) -> bool:
    """Signal the frozen new-session group *before* reaping its direct leader."""
    if worker.pid <= 0 or raw is None or pgid != worker.pid or raw[0] != worker.pid:
        return False
    for signum in (signal.SIGTERM, signal.SIGKILL):
        if time.monotonic() >= deadline:
            return False
        try:
            if (identity.raw_generation(worker.pid) != raw
                    or os.getpgid(worker.pid) != pgid):
                return False
            os.killpg(pgid, signum)
        except (OSError, identity.ProbeError):
            return False
        # Do not call poll()/wait() yet: reaping would release the PID/PGID
        # and make a later group signal ambiguous.  If TERM already ended the
        # leader, the next raw check fails closed rather than killing a new
        # owner.  The normal Python worker exits on TERM.
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
        if signum == signal.SIGTERM:
            try:
                identity.raw_generation(worker.pid)
            except identity.ProbeError:
                break
    try:
        worker.wait(timeout=_remaining(deadline))
    except subprocess.TimeoutExpired:
        return False
    except PreflightError:
        return False
    # Read-only group check after reap; never signal the old PGID again.
    return _group_gone(pgid)


def _valid_result(result: dict, notice: dict) -> bool:
    if type(result) is not dict or set(result) != RESULT_FIELDS:
        return False
    if (result["schema"] != SCHEMA
            or type(result["status"]) is not str
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", result["status"])
            or any(type(result[key]) is not bool for key in
                   ("negative_rejected", "same_observer", "cleanup_verified"))
            or any(type(result[key]) is not dict or set(result[key]) not in (set(), FIELDS)
                   or any(type(v) is not bool for v in result[key].values())
                   for key in ("positive", "negative"))
            or any(type(result[key]) is not int or result[key] != 0
                   for key in ("model_calls", "web_sends", "b_sends"))
            or result["source_sha256"] != _sha(SCRIPT)
            or result["adapter_sha256"] != _sha(ADAPTER)
            or result["profile_sha256"] != PROFILE_SHA256):
        return False
    for key in ("a_exit_code", "b_exit_code", "observer_exit_code"):
        if result[key] is not None and type(result[key]) is not int:
            return False
    for key in ("active_wall_s", "total_wall_s"):
        if (type(result[key]) not in (float, int)
                or not math.isfinite(result[key]) or result[key] < 0):
            return False
    if (result["active_wall_s"] != notice.get("active_wall_s")
            or result["active_wall_s"] > ACTIVE_LIMIT_S
            or result["total_wall_s"] < result["active_wall_s"]
            or result["total_wall_s"] > result["active_wall_s"] + CLEANUP_LIMIT_S + 0.1):
        return False
    if result["status"] == "adapter_visibility_feasible":
        return (result["cleanup_verified"] and result["negative_rejected"]
                and result["same_observer"] and set(result["positive"]) == FIELDS
                and all(result["positive"].values())
                and set(result["negative"]) == FIELDS
                and all(result["negative"][key] for key in A_FIELDS)
                and all(result["negative"][key] is False for key in B_FIELDS)
                and result["b_exit_code"] == -signal.SIGTERM
                and result["observer_exit_code"] in (0, -signal.SIGTERM))
    return result["negative_rejected"] is False


def _supervise() -> dict:
    began = time.monotonic()
    worker = None
    worker_raw = None
    worker_pgid = None
    cleanup_deadline = None
    status = "preflight_error"
    cleanup_verified = False
    active_wall = 0.0
    try:
        worker = subprocess.Popen(
            [str(PYTHON), str(SCRIPT), "--worker"],
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
        )
        worker_raw = identity.raw_generation(worker.pid)
        worker_pgid = os.getpgid(worker.pid)
        if worker_raw[0] != worker.pid or worker_pgid != worker.pid:
            _fail("worker_group_invalid")
        reader = _Reader(worker.stdout)
        notice = reader.read(began + ACTIVE_LIMIT_S)
        if (set(notice) != {"phase", "active_wall_s"}
                or notice["phase"] != "cleanup_started"
                or type(notice["active_wall_s"]) not in (float, int)
                or not (0 <= notice["active_wall_s"] <= ACTIVE_LIMIT_S)):
            _fail("worker_phase_invalid")
        active_wall = notice["active_wall_s"]
        cleanup_deadline = time.monotonic() + CLEANUP_LIMIT_S
        result = reader.read(cleanup_deadline)
        if not _valid_result(result, notice):
            _fail("worker_result_invalid")
        if not result["cleanup_verified"]:
            _fail("worker_cleanup_review_required")
        # Keep the direct child unreaped until its frozen group is stopped.
        # The worker has already attested that A/B/observer were reaped.
        cleanup_verified = _stop_owned_group(
            worker, worker_raw, worker_pgid, cleanup_deadline)
        if not cleanup_verified:
            _fail("worker_exit_or_group_invalid")
        result["worker_exit_code"] = worker.returncode
        return result
    except PreflightError as exc:
        status = str(exc)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        status = "worker_unavailable"
    finally:
        if worker is not None:
            if cleanup_deadline is None:
                cleanup_deadline = time.monotonic() + CLEANUP_LIMIT_S
            if not cleanup_verified and worker.returncode is None:
                if worker_raw is not None and worker_pgid == worker.pid:
                    cleanup_verified = _stop_owned_group(
                        worker, worker_raw, worker_pgid, cleanup_deadline)
                else:
                    # If the initial raw witness was unavailable, never infer
                    # PGID ownership.  Popen's direct child can be stopped,
                    # but the full group remains unverified/review-required.
                    try:
                        worker.terminate()
                        worker.wait(timeout=_remaining(cleanup_deadline))
                    except (OSError, subprocess.SubprocessError, PreflightError):
                        pass
            if worker.stdout is not None:
                worker.stdout.close()
            if worker.stdin is not None and not worker.stdin.closed:
                worker.stdin.close()
    return {
        "schema": SCHEMA,
        "status": status if cleanup_verified else "cleanup_review_required",
        "positive": {}, "negative": {},
        "negative_rejected": False, "same_observer": False,
        "cleanup_verified": cleanup_verified,
        "worker_exit_code": None if worker is None else worker.returncode,
        "active_wall_s": round(active_wall or min(time.monotonic() - began,
                                                  ACTIVE_LIMIT_S), 6),
        "total_wall_s": round(time.monotonic() - began, 6),
        "source_sha256": _sha(SCRIPT), "adapter_sha256": _sha(ADAPTER),
        "profile_sha256": PROFILE_SHA256,
        "model_calls": 0, "web_sends": 0, "b_sends": 0,
    }


def _worker_mode() -> int:
    result = _worker()
    _write(sys.stdout.buffer, result)
    readable, _, _ = select.select([sys.stdin.buffer], [], [], CLEANUP_LIMIT_S)
    if not readable:
        return 2
    try:
        ack = json.loads(sys.stdin.buffer.readline(MAX_LINE + 1))
    except (OSError, ValueError):
        return 2
    return 0 if ack == {"finish": True} else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--listen-a", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--listen-b", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--observe", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    if options.listen_a:
        return _listen("a")
    if options.listen_b:
        return _listen("b")
    if options.observe:
        return _observe()
    if options.worker:
        return _worker_mode()
    if not options.execute:
        print(json.dumps({"ok": False, "reason": "explicit_execute_required"}))
        return 2
    result = _supervise()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "adapter_visibility_feasible" else 2


if __name__ == "__main__":
    raise SystemExit(main())
