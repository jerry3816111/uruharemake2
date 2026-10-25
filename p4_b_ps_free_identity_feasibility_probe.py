#!/usr/bin/env python3
"""One-use, zero-model visibility probe; never authorizes a P4 B Send.

The public ``--execute`` mode supervises two synthetic loopback listeners and
one sandboxed observer. Other modes are internal child processes. Only fixed
booleans/reason codes/timing leave the supervisor; procargs' environment tail
is inspected in memory, never logged or returned.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import socket
import struct
import subprocess
import sys
import time
from typing import BinaryIO


ROOT = Path(__file__).resolve().parent
SCRIPT = Path(__file__).resolve()
PYTHON = ROOT / ".venv/product_checks/bin/python"
PROFILE = Path(
    "/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/"
    "uruha-product-xremdzdp/"
    "p4_preference_fallback_detached.6a0185bb8bc10e98.sandbox.sb"
)
PROFILE_SHA256 = "5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110"
MODEL_SENTINEL = "/private/tmp/uruha-p4-b-identity-surrogate-no-model"
EXPECTED_ENV = {"OLLAMA_MODELS": MODEL_SENTINEL, "OLLAMA_NO_CLOUD": "1"}
PHASE_LIMIT_S = 30.0
PROCARGS_LIMIT = 1 << 20
_MAX_LINE = 4096
_CLEANUP_LIMIT_S = 5.0
_MATRIX_KEYS = frozenset({
    "daemon_start", "runner_start", "daemon_argv", "runner_argv",
    "daemon_env", "runner_env", "runner_parent", "daemon_listener",
    "runner_listener",
})
_RESULT_KEYS = frozenset({
    "schema", "status", "matrix", "negative_rejected", "cleanup_verified",
    "daemon_exit_code", "runner_exit_code", "observer_exit_code",
    "active_wall_s", "total_wall_s", "source_sha256", "model_calls",
    "b_sends", "web_sends",
})


class ProbeError(RuntimeError):
    """A fixed reason code, never raw process data."""


def _fail(reason: str) -> None:
    raise ProbeError(reason)


def _remaining(deadline: float, cap: float | None = None) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        _fail("deadline_exceeded")
    return left if cap is None else min(left, cap)


class _LineReader:
    def __init__(self, stream: BinaryIO):
        self.fd = stream.fileno()
        self.pending = b""

    def read(self, deadline: float) -> dict:
        while b"\n" not in self.pending:
            if len(self.pending) > _MAX_LINE:
                _fail("child_protocol_oversize")
            readable, _, _ = select.select([self.fd], [], [], _remaining(deadline))
            if not readable:
                _fail("child_protocol_timeout")
            chunk = os.read(self.fd, 4096)
            if not chunk:
                _fail("child_protocol_eof")
            self.pending += chunk
        line, self.pending = self.pending.split(b"\n", 1)
        if len(line) > _MAX_LINE:
            _fail("child_protocol_oversize")
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError):
            _fail("child_protocol_invalid")
        if type(value) is not dict:
            _fail("child_protocol_invalid")
        return value


def _write_line(stream: BinaryIO, value: dict) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > _MAX_LINE:
        _fail("child_protocol_oversize")
    try:
        stream.write(raw)
        stream.flush()
    except (BrokenPipeError, OSError):
        _fail("child_protocol_unavailable")


# Local macOS SDK sys/proc_info.h struct proc_bsdinfo, MAXCOMLEN=16,
# PROC_PIDTBSDINFO=3. The expected 136-byte layout is checked before use.
class _BsdInfo(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_uint32) for name in (
            "pbi_flags", "pbi_status", "pbi_xstatus", "pbi_pid", "pbi_ppid",
            "pbi_uid", "pbi_gid", "pbi_ruid", "pbi_rgid", "pbi_svuid",
            "pbi_svgid", "rfu_1",
        )
    ] + [
        ("pbi_comm", ctypes.c_char * 16), ("pbi_name", ctypes.c_char * 32),
    ] + [
        (name, ctypes.c_uint32) for name in (
            "pbi_nfiles", "pbi_pgid", "pbi_pjobc", "e_tdev", "e_tpgid",
            "pbi_nice",
        )
    ] + [("pbi_start_tvsec", ctypes.c_uint64),
         ("pbi_start_tvusec", ctypes.c_uint64)]


def _bsd_info(pid: int) -> tuple[int, int, int, int] | None:
    if sys.platform != "darwin" or ctypes.sizeof(_BsdInfo) != 136 or pid <= 0:
        _fail("bsd_info_unavailable")
    try:
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        fn = lib.proc_pidinfo
        fn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                       ctypes.c_void_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        info = _BsdInfo()
        count = fn(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
    except (OSError, AttributeError, TypeError, ValueError):
        _fail("bsd_info_unavailable")
    if count <= 0:
        return None
    if (count != ctypes.sizeof(info) or info.pbi_pid != pid
            or info.pbi_start_tvsec == 0 or info.pbi_start_tvusec >= 1_000_000):
        _fail("bsd_info_invalid")
    return (info.pbi_pid, info.pbi_ppid,
            info.pbi_start_tvsec, info.pbi_start_tvusec)


def _parse_procargs(raw: bytes, expected_env: dict[str, str]) -> tuple[str, list[str], dict[str, int]]:
    """Parse only argc/exec/argv and count two fixed values *after* argv."""
    if type(raw) is not bytes or not (8 <= len(raw) <= PROCARGS_LIMIT):
        _fail("procargs_invalid")
    argc = struct.unpack_from("=i", raw)[0]
    if not (2 <= argc <= 8):
        _fail("procargs_invalid")
    position = 4

    def take() -> str:
        nonlocal position
        end = raw.find(b"\0", position)
        if end <= position:
            _fail("procargs_invalid")
        try:
            value = raw[position:end].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("procargs_invalid")
        position = end + 1
        return value

    executable = take()
    while position < len(raw) and raw[position] == 0:
        position += 1
    argv = [take() for _ in range(argc)]
    if executable != argv[0]:
        _fail("procargs_invalid")
    # A complete assignment in argv would invalidate the environment oracle.
    # Do not reject a one-character value such as "1" in a Python 3.12 path.
    for key, value in expected_env.items():
        marker = f"{key}={value}"
        if any(key in part or marker in part for part in argv):
            _fail("env_oracle_in_argv")
    seen = {key: 0 for key in expected_env}
    exact = {key: 0 for key in expected_env}
    for entry in raw[position:].split(b"\0"):
        if not entry:
            continue
        for key, value in expected_env.items():
            if entry.startswith(f"{key}=".encode("utf-8")):
                seen[key] += 1
                if entry == f"{key}={value}".encode("utf-8"):
                    exact[key] += 1
    return executable, argv, {
        key: int(seen[key] == 1 and exact[key] == 1)
        for key in expected_env
    }


def _procargs(pid: int, expected_env: dict[str, str]) -> tuple[str, list[str], dict[str, int]]:
    if sys.platform != "darwin" or ctypes.sizeof(ctypes.c_int) != 4 or pid <= 0:
        _fail("procargs_unavailable")
    try:
        libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        fn = libc.sysctl
        fn.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint,
                       ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                       ctypes.c_void_p, ctypes.c_size_t]
        fn.restype = ctypes.c_int
        mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2, PID
        size = ctypes.c_size_t(0)
        if fn(mib, 3, None, ctypes.byref(size), None, 0) != 0:
            _fail("procargs_unavailable")
        capacity = size.value
        if not (8 <= capacity <= PROCARGS_LIMIT):
            _fail("procargs_unavailable")
        buffer = ctypes.create_string_buffer(capacity)
        if fn(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
            _fail("procargs_unavailable")
        if not (8 <= size.value <= capacity):
            _fail("procargs_unavailable")
    except (OSError, AttributeError, TypeError, ValueError, OverflowError):
        _fail("procargs_unavailable")
    return _parse_procargs(buffer.raw[:size.value], expected_env)


def _run_fixed(argv: list[str], deadline: float, *, timeout: float = 1.5) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, check=False,
            timeout=_remaining(deadline, timeout), env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError):
        _fail("process_observer_unavailable")


def _listener_owner(pid: int, port: int, deadline: float) -> bool:
    if not (1 <= port <= 65535):
        return False
    try:
        owners = _run_fixed(
            ["/usr/sbin/lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"], deadline,
        )
    except ProbeError:
        return False
    if owners.returncode != 0:
        return False
    try:
        if [int(row) for row in owners.stdout.splitlines()] != [pid]:
            return False
    except ValueError:
        return False
    try:
        detail = _run_fixed(
            ["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid),
             f"-iTCP:{port}", "-sTCP:LISTEN"], deadline,
        )
    except ProbeError:
        return False
    return (detail.returncode == 0 and bool(re.search(
        rf"\bTCP 127\.0\.0\.1:{port} \(LISTEN\)(?:\s|$)", detail.stdout)))


def _expected_process(pid: int, port: int, mode: str, deadline: float) -> dict:
    try:
        info = _bsd_info(pid)
        if info is None:
            _fail("invalid_surrogate")
        executable, argv, _ = _procargs(pid, EXPECTED_ENV)
    except ProbeError:
        # A failed *external* oracle does not say the sandbox lacks access.
        _fail("invalid_surrogate")
    if argv != [executable, str(SCRIPT), f"--{mode}"]:
        _fail("surrogate_argv_invalid")
    command = _run_fixed(
        ["/bin/ps", "-ww", "-p", str(pid), "-o", "ppid=", "-o", "command="],
        deadline,
    )
    if command.returncode != 0 or command.stdout.strip() != f"{info[1]} {' '.join(argv)}":
        _fail("invalid_surrogate")
    if not _listener_owner(pid, port, deadline):
        _fail("invalid_surrogate")
    return {"pid": pid, "port": port, "start": [info[2], info[3]],
            "ppid": info[1], "executable": executable, "argv": argv}


def _outside_env_valid(pid: int, deadline: float) -> bool:
    observed = _run_fixed(
        ["/bin/ps", "-wwE", "-p", str(pid), "-o", "command="], deadline,
    )
    if observed.returncode != 0:
        return False
    words = observed.stdout.split()
    return all(
        [word for word in words if word.startswith(f"{key}=")] == [f"{key}={value}"]
        for key, value in EXPECTED_ENV.items()
    )


def _observe_one(expected: dict, deadline: float) -> tuple[bool, bool, bool, bool]:
    try:
        info = _bsd_info(expected["pid"])
    except ProbeError:
        info = None
    raw_start = bool(info and list(info[2:4]) == expected["start"])
    try:
        executable, argv, env_counts = _procargs(expected["pid"], EXPECTED_ENV)
        argv_match = executable == expected["executable"] and argv == expected["argv"]
        env_match = all(env_counts[key] == 1 for key in EXPECTED_ENV)
    except ProbeError:
        argv_match = False
        env_match = False
    listener_match = _listener_owner(expected["pid"], expected["port"], deadline)
    return raw_start, argv_match, listener_match if info else False, env_match


def _observe(descriptor: dict, deadline: float) -> dict[str, bool]:
    daemon = descriptor["daemon"]
    runner = descriptor["runner"]
    daemon_start, daemon_argv, daemon_listener, daemon_env = _observe_one(daemon, deadline)
    runner_start, runner_argv, runner_listener, runner_env = _observe_one(runner, deadline)
    try:
        runner_info = _bsd_info(runner["pid"])
    except ProbeError:
        runner_info = None
    return {
        "daemon_start": daemon_start,
        "runner_start": runner_start,
        "daemon_argv": daemon_argv,
        "runner_argv": runner_argv,
        "daemon_env": daemon_env,
        "runner_env": runner_env,
        "runner_parent": bool(runner_info and runner_info[1] == daemon["pid"]),
        "daemon_listener": daemon_listener,
        "runner_listener": runner_listener,
    }


def _listener() -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.set_inheritable(False)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


def _runner_mode() -> int:
    with _listener() as server:
        _write_line(sys.stdout.buffer, {"pid": os.getpid(), "port": server.getsockname()[1]})
        while True:
            time.sleep(0.2)


def _daemon_mode() -> int:
    runner = None
    def stop_on_signal(_number, _frame):
        raise SystemExit(1)
    signal.signal(signal.SIGTERM, stop_on_signal)
    try:
        with _listener() as server:
            runner = subprocess.Popen(
                [str(PYTHON), str(SCRIPT), "--runner"], env=dict(os.environ),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, close_fds=True,
            )
            ready = _LineReader(runner.stdout).read(time.monotonic() + 5.0)
            if ready.get("pid") != runner.pid or type(ready.get("port")) is not int:
                _fail("runner_ready_invalid")
            _write_line(sys.stdout.buffer, {
                "pid": os.getpid(), "port": server.getsockname()[1],
                "runner_pid": runner.pid, "runner_port": ready["port"],
            })
            line = sys.stdin.buffer.readline(_MAX_LINE + 1)
            if line:
                if len(line) > _MAX_LINE:
                    _fail("daemon_phase_invalid")
                try:
                    command = json.loads(line)
                except (ValueError, UnicodeError):
                    _fail("daemon_phase_invalid")
                if (type(command) is not dict
                        or set(command) != {"phase", "pid", "start"}
                        or command["phase"] != "stop_runner"
                        or command["pid"] != runner.pid
                        or type(command["start"]) is not list
                        or len(command["start"]) != 2
                        or any(type(value) is not int for value in command["start"])
                        or runner.poll() is not None):
                    _fail("daemon_phase_invalid")
                info = _bsd_info(runner.pid)
                if info is None or list(info[2:4]) != command["start"]:
                    _fail("runner_generation_drift")
                # A direct, unreaped Popen child cannot have a reused PID.
                # Keep this daemon listener open until the same observer has
                # re-read the stopped runner's identity.
                runner.terminate()
                runner_exit_code = runner.wait(timeout=2)
                if runner_exit_code != -signal.SIGTERM:
                    _fail("runner_exit_unexpected")
                _write_line(sys.stdout.buffer, {
                    "phase": "runner_reaped", "pid": runner.pid,
                    "exit_code": runner_exit_code,
                })
                if sys.stdin.buffer.read(1):
                    _fail("daemon_phase_invalid")
    finally:
        if runner is not None:
            if runner.poll() is None:
                runner.terminate()  # Direct Popen child, never process-name kill.
                try:
                    runner.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if runner.poll() is None:
                        runner.kill()
                        runner.wait(timeout=2)
            if runner.stdout is not None:
                runner.stdout.close()
    return 0


def _observer_mode() -> int:
    try:
        descriptor = json.loads(sys.stdin.buffer.readline(_MAX_LINE + 1))
        if (type(descriptor) is not dict or set(descriptor) != {"daemon", "runner"}):
            _fail("observer_input_invalid")
        deadline = time.monotonic() + 20.0
        before = _observe(descriptor, deadline)
        _write_line(sys.stdout.buffer, {
            "phase": "before", "observer_pid": os.getpid(), "matrix": before,
        })
        phase = json.loads(sys.stdin.buffer.readline(_MAX_LINE + 1))
        if phase != {"phase": "after_runner_exit"}:
            _fail("observer_phase_invalid")
        after = _observe(descriptor, deadline)
        _write_line(sys.stdout.buffer, {
            "phase": "after", "observer_pid": os.getpid(), "matrix": after,
        })
        return 0
    except (OSError, ValueError, ProbeError):
        return 2


def _exact_signal(pid: int, start: list[int], signum: int) -> bool:
    try:
        info = _bsd_info(pid)
        if info is None or list(info[2:4]) != start:
            return False  # Positive test requires a live, exact-generation target.
        os.kill(pid, signum)
        return True
    except (OSError, ProbeError):
        return False


def _wait_gone(pid: int, start: list[int], deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            info = _bsd_info(pid)
        except ProbeError:
            return False
        if info is None or list(info[2:4]) != start:
            return True
        time.sleep(0.05)
    return False


def _active_deadline(_number, _frame):
    _fail("deadline_exceeded")


def _execute(*, notify_cleanup: bool = False) -> dict:
    began = time.monotonic()
    deadline = began + PHASE_LIMIT_S
    daemon = observer = None
    daemon_reader = None
    daemon_expected = runner_expected = None
    status = "probe_error"
    matrix: dict[str, bool] = {}
    negative_rejected = False
    cleanup_verified = False
    runner_exit_code = observer_exit_code = daemon_exit_code = None
    signal.signal(signal.SIGALRM, _active_deadline)
    signal.setitimer(signal.ITIMER_REAL, PHASE_LIMIT_S)
    try:
        if sys.platform != "darwin" or not PYTHON.is_file() or not SCRIPT.is_file():
            _fail("platform_or_source_unavailable")
        if (not PROFILE.is_file() or
                hashlib.sha256(PROFILE.read_bytes()).hexdigest() != PROFILE_SHA256):
            _fail("sandbox_profile_drift")
        daemon_env = {
            "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
            **EXPECTED_ENV,
        }
        daemon = subprocess.Popen(
            [str(PYTHON), str(SCRIPT), "--daemon"], env=daemon_env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        daemon_reader = _LineReader(daemon.stdout)
        ready = daemon_reader.read(deadline)
        if (ready.get("pid") != daemon.pid or type(ready.get("port")) is not int
                or type(ready.get("runner_pid")) is not int
                or type(ready.get("runner_port")) is not int
                or ready["port"] == ready["runner_port"]):
            _fail("surrogate_ready_invalid")
        daemon_expected = _expected_process(daemon.pid, ready["port"], "daemon", deadline)
        runner_expected = _expected_process(
            ready["runner_pid"], ready["runner_port"], "runner", deadline,
        )
        if (runner_expected["ppid"] != daemon.pid
                or not _outside_env_valid(daemon.pid, deadline)
                or not _outside_env_valid(runner_expected["pid"], deadline)):
            _fail("invalid_surrogate")
        descriptor = {"daemon": daemon_expected, "runner": runner_expected}
        observer = subprocess.Popen(
            ["/usr/bin/sandbox-exec", "-f", str(PROFILE), str(PYTHON),
             str(SCRIPT), "--observe"],
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        reader = _LineReader(observer.stdout)
        _write_line(observer.stdin, descriptor)
        before = reader.read(deadline)
        if (before.get("phase") != "before"
                or type(before.get("observer_pid")) is not int
                or before["observer_pid"] != observer.pid
                or type(before.get("matrix")) is not dict):
            _fail("observer_before_invalid")
        matrix = before["matrix"]
        if set(matrix) != _MATRIX_KEYS or any(type(value) is not bool for value in matrix.values()):
            _fail("observer_matrix_invalid")
        if not all(matrix.values()):
            status = "no_go_missing_identity_field"
        else:
            _write_line(daemon.stdin, {
                "phase": "stop_runner", "pid": runner_expected["pid"],
                "start": runner_expected["start"],
            })
            reaped = daemon_reader.read(deadline)
            if (set(reaped) != {"phase", "pid", "exit_code"}
                    or reaped.get("phase") != "runner_reaped"
                    or reaped.get("pid") != runner_expected["pid"]
                    or reaped.get("exit_code") != -signal.SIGTERM
                    or type(reaped.get("exit_code")) is not int):
                _fail("runner_reap_unconfirmed")
            runner_exit_code = reaped["exit_code"]
            if not _wait_gone(runner_expected["pid"], runner_expected["start"], deadline):
                _fail("runner_not_gone_for_negative")
            _write_line(observer.stdin, {"phase": "after_runner_exit"})
            after = reader.read(deadline)
            if (after.get("phase") != "after"
                    or after.get("observer_pid") != before["observer_pid"]
                    or type(after.get("matrix")) is not dict
                    or set(after["matrix"]) != _MATRIX_KEYS):
                _fail("observer_after_invalid")
            if any(type(value) is not bool for value in after["matrix"].values()):
                _fail("observer_after_invalid")
            daemon_fields = ("daemon_start", "daemon_argv", "daemon_env", "daemon_listener")
            runner_fields = (
                "runner_start", "runner_argv", "runner_env",
                "runner_parent", "runner_listener",
            )
            negative_rejected = (all(after["matrix"][key] for key in daemon_fields)
                                 and all(after["matrix"][key] is False for key in runner_fields))
            status = "feasible_observability" if negative_rejected else "no_go_stale_observer"
    except ProbeError as exc:
        status = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        status = "probe_error"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        active_wall = time.monotonic() - began
        if notify_cleanup:
            try:
                _write_line(sys.stdout.buffer, {
                    "phase": "cleanup_started", "active_wall_s": round(active_wall, 6),
                })
            except ProbeError:
                status = "cleanup_notice_unavailable"
        cleanup_deadline = time.monotonic() + _CLEANUP_LIMIT_S
        observer_ok = True
        if observer is not None:
            if observer.stdin is not None:
                observer.stdin.close()
            if observer.poll() is None:
                observer.terminate()  # Direct child Popen identity only.
            try:
                observer.wait(timeout=max(0.1, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                if observer.poll() is None:
                    observer.kill()
                    try:
                        observer.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        observer_ok = False
            if observer.stdout is not None:
                observer.stdout.close()
            observer_exit_code = observer.returncode
        daemon_ok = True
        if daemon is not None:
            # The daemon owns/reaps runner. Close its command pipe first; a
            # parent-side wait on the live grandchild can otherwise stall on
            # its zombie state until the entire cleanup budget is consumed.
            if daemon.stdin is not None:
                daemon.stdin.close()
            if daemon.poll() is None:
                try:
                    daemon.wait(timeout=max(0.1, cleanup_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    if daemon_expected is not None and _exact_signal(
                        daemon_expected["pid"], daemon_expected["start"], signal.SIGTERM,
                    ):
                        try:
                            daemon.wait(timeout=0.5)
                        except subprocess.TimeoutExpired:
                            daemon_ok = False
                    else:
                        daemon_ok = False
            if daemon.stdout is not None:
                daemon.stdout.close()
            daemon_exit_code = daemon.returncode
            # A nonzero daemon exit cannot certify that its direct runner
            # child was reaped when the external runner oracle never finished.
            # Keep the outer process group available for emergency cleanup.
            daemon_ok = daemon_ok and daemon_exit_code == 0
        runner_ok = True
        if runner_expected is not None:
            runner_ok = _wait_gone(
                runner_expected["pid"], runner_expected["start"], time.monotonic() + 0.1,
            )
        cleanup_verified = observer_ok and runner_ok and daemon_ok
        if not cleanup_verified:
            status = "cleanup_review_required"
    return {
        "schema": "p4_b_ps_free_identity_feasibility_v1",
        "status": status,
        "matrix": matrix,
        "negative_rejected": negative_rejected,
        "cleanup_verified": cleanup_verified,
        "daemon_exit_code": daemon_exit_code,
        "runner_exit_code": runner_exit_code,
        "observer_exit_code": observer_exit_code,
        "active_wall_s": round(active_wall, 6),
        "total_wall_s": round(time.monotonic() - began, 6),
        "source_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "model_calls": 0,
        "b_sends": 0,
        "web_sends": 0,
    }


def _owned_group_gone(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def _stop_owned_group(worker: subprocess.Popen, deadline: float) -> bool:
    """Stop only the group whose leader is our still-unreaped direct child."""
    if worker.pid <= 0:
        return False
    try:
        # The direct child cannot have a reused PID before wait/reap. It was
        # launched as a new session; daemon, runner and observer inherit it.
        pgid = os.getpgid(worker.pid)
        if pgid != worker.pid:
            return False
    except ProcessLookupError:
        pgid = worker.pid
    except OSError:
        return False
    for signum in (signal.SIGTERM, signal.SIGKILL):
        if _owned_group_gone(pgid):
            break
        try:
            os.killpg(pgid, signum)
        except ProcessLookupError:
            break
        except OSError:
            return False
        until = min(deadline, time.monotonic() + 0.5)
        while time.monotonic() < until and not _owned_group_gone(pgid):
            time.sleep(0.025)
    try:
        worker.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return False
    return _owned_group_gone(pgid)


def _valid_worker_result(result: dict, cleanup_notice: dict) -> bool:
    """The outer watchdog must not forward an inconsistent worker GO claim."""
    if set(result) != _RESULT_KEYS:
        return False
    if (result.get("schema") != "p4_b_ps_free_identity_feasibility_v1"
            or type(result.get("status")) is not str
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", result["status"])
            or type(result.get("cleanup_verified")) is not bool
            or type(result.get("negative_rejected")) is not bool
            or type(result.get("matrix")) is not dict
            or set(result["matrix"]) not in (set(), _MATRIX_KEYS)
            or any(type(value) is not bool for value in result["matrix"].values())
            or any(result.get(key) != 0 or type(result.get(key)) is not int
                   for key in ("model_calls", "b_sends", "web_sends"))
            or result.get("source_sha256") != hashlib.sha256(SCRIPT.read_bytes()).hexdigest()):
        return False
    if any(value is not None and type(value) is not int for value in (
            result.get("daemon_exit_code"), result.get("runner_exit_code"),
            result.get("observer_exit_code"))):
        return False
    for key in ("active_wall_s", "total_wall_s"):
        value = result.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            return False
    if (result["active_wall_s"] != cleanup_notice["active_wall_s"]
            or result["active_wall_s"] > PHASE_LIMIT_S
            or result["total_wall_s"] < result["active_wall_s"]):
        return False
    if result["status"] == "feasible_observability":
        return (result["cleanup_verified"] is True
                and result["negative_rejected"] is True
                and set(result["matrix"]) == _MATRIX_KEYS
                and all(result["matrix"].values())
                and result["runner_exit_code"] == -signal.SIGTERM
                and result["daemon_exit_code"] == 0
                and result["observer_exit_code"] in (0, -signal.SIGTERM))
    return result["negative_rejected"] is False


def _execute_supervised() -> dict:
    """Independent monotonic watchdog around the one-use synthetic worker."""
    began = time.monotonic()
    active_deadline = began + PHASE_LIMIT_S
    worker = None
    result = None
    status = "probe_error"
    cleanup_verified = False
    active_wall = 0.0
    worker_reaped = False
    try:
        worker = subprocess.Popen(
            [str(PYTHON), str(SCRIPT), "--worker"],
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
        )
        reader = _LineReader(worker.stdout)
        cleanup = reader.read(active_deadline)
        if (set(cleanup) != {"phase", "active_wall_s"}
                or cleanup["phase"] != "cleanup_started"
                or type(cleanup["active_wall_s"]) not in (int, float)
                or not (0 <= cleanup["active_wall_s"] <= PHASE_LIMIT_S)):
            _fail("worker_phase_invalid")
        active_wall = cleanup["active_wall_s"]
        cleanup_deadline = time.monotonic() + _CLEANUP_LIMIT_S
        result = reader.read(cleanup_deadline)
        if not _valid_worker_result(result, cleanup):
            _fail("worker_result_invalid")
        if not result["cleanup_verified"]:
            _fail("worker_cleanup_review_required")
        worker.wait(timeout=_remaining(cleanup_deadline))
        worker_reaped = True
        if worker.returncode != 0:
            _fail("worker_exit_invalid")
        result["worker_exit_code"] = worker.returncode
        return result
    except ProbeError as exc:
        status = str(exc)
    except (OSError, subprocess.SubprocessError):
        status = "worker_unavailable"
    finally:
        if worker is not None:
            if result is not None and result.get("cleanup_verified") is True and worker_reaped:
                cleanup_verified = True
            elif not worker_reaped:
                cleanup_verified = _stop_owned_group(
                    worker, time.monotonic() + _CLEANUP_LIMIT_S,
                )
            if worker.stdout is not None:
                worker.stdout.close()
    return {
        "schema": "p4_b_ps_free_identity_feasibility_v1",
        "status": status if cleanup_verified else "cleanup_review_required",
        "matrix": {}, "negative_rejected": False,
        "cleanup_verified": cleanup_verified,
        "worker_exit_code": worker.returncode if worker_reaped else None,
        "active_wall_s": round(active_wall or min(time.monotonic() - began, PHASE_LIMIT_S), 6),
        "total_wall_s": round(time.monotonic() - began, 6),
        "source_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "model_calls": 0, "b_sends": 0, "web_sends": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--execute", action="store_true")
    group.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--runner", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--observe", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    if options.daemon:
        return _daemon_mode()
    if options.runner:
        return _runner_mode()
    if options.observe:
        return _observer_mode()
    if options.worker:
        result = _execute(notify_cleanup=True)
        _write_line(sys.stdout.buffer, result)
        return 0
    if not options.execute:
        print(json.dumps({"ok": False, "reason": "explicit_execute_required"}))
        return 2
    result = _execute_supervised()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "feasible_observability" else 2


if __name__ == "__main__":
    raise SystemExit(main())
