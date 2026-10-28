"""B-only macOS process-observation primitives, without sandboxed ``ps``.

These functions do not authorize a provider call or validate an Ollama model.
Callers must separately bind the observed values to a controller descriptor,
receipt, binary/model digests, resource gate, and before/after observations.
Environment entries and full argv are returned only in-process; callers must
not log a ``ProcessSnapshot`` or include it in public traces.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
import json
import re
import struct
import subprocess
import sys


_MAX_PROCARGS_BYTES = 1 << 20
_MAX_ARGC = 64
_ENV_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class ProbeError(RuntimeError):
    """A fixed failure code; never interpolate argv, environment, or ps text."""


@dataclass(frozen=True, repr=False)
class ProcessSnapshot:
    pid: int
    ppid: int
    start_sec: int
    start_usec: int
    executable: str
    argv: tuple[str, ...]
    env_exact: dict[str, bool]


def _fail(reason: str) -> None:
    raise ProbeError(reason)


# Local macOS SDK sys/proc_info.h: struct proc_bsdinfo, MAXCOMLEN=16,
# PROC_PIDTBSDINFO=3. Reject an unexpected layout rather than reading offsets.
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
    ] + [
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


def _pid(pid: int) -> int:
    if type(pid) is not int or pid <= 0:
        _fail("process_pid_invalid")
    return pid


def raw_generation(pid: int) -> tuple[int, int, int, int]:
    """Return kernel PID, parent PID and exact start sec/usec for one live PID."""
    _pid(pid)
    if sys.platform != "darwin" or ctypes.sizeof(_BsdInfo) != 136:
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
        _fail("process_generation_unavailable")
    if (count != ctypes.sizeof(info) or info.pbi_pid != pid
            or info.pbi_ppid <= 0 or info.pbi_start_tvsec == 0
            or info.pbi_start_tvusec >= 1_000_000):
        _fail("bsd_info_invalid")
    return (info.pbi_pid, info.pbi_ppid,
            info.pbi_start_tvsec, info.pbi_start_tvusec)


def _expected_env(expected_env: dict[str, str] | None) -> dict[str, str]:
    if expected_env is None:
        return {}
    if type(expected_env) is not dict:
        _fail("expected_environment_invalid")
    for key, value in expected_env.items():
        if (type(key) is not str or not _ENV_KEY.fullmatch(key)
                or type(value) is not str or "\0" in value):
            _fail("expected_environment_invalid")
    return expected_env


def _parse_procargs(
    raw: bytes, expected_env: dict[str, str] | None = None,
) -> tuple[str, tuple[str, ...], dict[str, bool]]:
    """Parse argc/exec/argv, then count exact env entries after argv only."""
    expected = _expected_env(expected_env)
    if type(raw) is not bytes or not (8 <= len(raw) <= _MAX_PROCARGS_BYTES):
        _fail("procargs_invalid")
    argc = struct.unpack_from("=i", raw)[0]
    if not (1 <= argc <= _MAX_ARGC):
        _fail("procargs_invalid")
    position = 4

    def take() -> str:
        nonlocal position
        end = raw.find(b"\0", position)
        if end <= position:
            _fail("procargs_invalid")
        try:
            item = raw[position:end].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("procargs_invalid")
        position = end + 1
        return item

    executable = take()
    while position < len(raw) and raw[position] == 0:
        position += 1
    argv = tuple(take() for _ in range(argc))
    # Executable and argv[0] can differ on macOS. Preserve both exact strings.
    if raw[-1] != 0:
        _fail("procargs_invalid")
    seen: set[str] = set()
    exact = {key: False for key in expected}
    for entry in raw[position:].split(b"\0"):
        if not entry:
            continue
        try:
            item = entry.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("procargs_invalid")
        key, separator, value = item.partition("=")
        if not separator or not _ENV_KEY.fullmatch(key) or key in seen:
            _fail("procargs_invalid")
        seen.add(key)
        if key in expected:
            exact[key] = value == expected[key]
    return executable, argv, exact


def _procargs(
    pid: int, expected_env: dict[str, str] | None,
) -> tuple[str, tuple[str, ...], dict[str, bool]]:
    _pid(pid)
    if sys.platform != "darwin" or ctypes.sizeof(ctypes.c_int) != 4:
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
        if not (8 <= capacity <= _MAX_PROCARGS_BYTES):
            _fail("procargs_unavailable")
        buffer = ctypes.create_string_buffer(capacity)
        if fn(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
            _fail("procargs_unavailable")
        if not (8 <= size.value <= capacity):
            _fail("procargs_unavailable")
    except (OSError, AttributeError, TypeError, ValueError, OverflowError):
        _fail("procargs_unavailable")
    return _parse_procargs(buffer.raw[:size.value], expected_env)


def observe_process(
    pid: int, expected_env: dict[str, str] | None = None,
) -> ProcessSnapshot:
    """Observe one process and reject a PID generation change during the read."""
    expected = _expected_env(expected_env)
    before = raw_generation(pid)
    executable, argv, env_exact = _procargs(pid, expected)
    after = raw_generation(pid)
    if before != after:
        _fail("process_generation_drift")
    return ProcessSnapshot(*before, executable, argv, env_exact)


def _run_lsof(argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, check=False, timeout=1.5,
            env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError):
        _fail("listener_observer_unavailable")


def owns_loopback_listener(pid: int, port: int) -> bool:
    """Require one exact PID to own a 127.0.0.1 TCP LISTEN socket."""
    _pid(pid)
    if type(port) is not int or not (1 <= port <= 65535):
        _fail("listener_port_invalid")
    try:
        owners = _run_lsof(
            ["/usr/sbin/lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
        )
        if owners.returncode != 0:
            return False
        if [int(row) for row in owners.stdout.splitlines()] != [pid]:
            return False
        detail = _run_lsof(
            ["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid),
             f"-iTCP:{port}", "-sTCP:LISTEN"],
        )
    except (ProbeError, ValueError):
        return False
    return detail.returncode == 0 and bool(re.search(
        rf"\bTCP 127\.0\.0\.1:{port} \(LISTEN\)(?:\s|$)", detail.stdout,
    ))


def argv_digest(snapshot: ProcessSnapshot) -> str:
    """Digest exact OS executable and argv strings, not resolved path aliases."""
    if (type(snapshot) is not ProcessSnapshot
            or type(snapshot.executable) is not str
            or type(snapshot.argv) is not tuple
            or not snapshot.executable or not snapshot.argv
            or any(type(part) is not str or not part for part in snapshot.argv)):
        _fail("process_argv_invalid")
    raw = json.dumps(
        {"executable": snapshot.executable, "argv": list(snapshot.argv)},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
