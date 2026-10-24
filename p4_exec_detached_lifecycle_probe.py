#!/usr/bin/env python3
"""Zero-product feasibility probe for a detached exec-context local process.

This is not a product launcher.  It only runs /bin/sleep or the precise
sandboxed Python -c marker used to diagnose the launchd interpreter stall.
Evidence stays in a new private launcher-owned temporary root.  A stop signal
is sent only when PID, UID, start time, command and process group still match.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import tempfile
import time

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_preference_fallback_launchd_control as launchd


ROOT = Path(__file__).resolve().parent
SCHEMA = "uruha_p4_exec_detached_probe_v1"
META = "detached-probe.json"
PORT = 7894
PS = "/bin/ps"
PYTHON_MARKER = launchd.PYTHON_PROBE_SNIPPET


class ProbeError(RuntimeError):
    pass


def _private_write(path: Path, payload: dict) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded)


def _ps_field(pid: int, field: str) -> str | None:
    result = subprocess.run(
        [PS, "-p", str(pid), "-o", f"{field}="],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return None
    if result.returncode != 0:
        raise ProbeError(f"ps_unknown:{field}:rc={result.returncode}")
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1 or not lines[0].strip():
        raise ProbeError(f"ps_invalid:{field}")
    return lines[0].strip()


def _identity(pid: int) -> dict | None:
    pid_text = _ps_field(pid, "pid")
    if pid_text is None:
        return None
    uid = _ps_field(pid, "uid")
    start = _ps_field(pid, "lstart")
    command = _ps_field(pid, "command")
    pgrp = _ps_field(pid, "pgid")
    state = _ps_field(pid, "stat")
    if None in (uid, start, command, pgrp, state):
        if _ps_field(pid, "pid") is None:
            return None
        raise ProbeError("pid_changed_during_inspection")
    if pid_text != str(pid):
        raise ProbeError("pid_changed_during_inspection")
    if not uid.isdigit() or not pgrp.isdigit():
        raise ProbeError("pid_identity_invalid")
    if state.startswith("Z"):
        # A defunct process cannot execute or own a port; never signal its
        # recycled process group on the strength of a zombie snapshot.
        return None
    return {
        "pid": pid, "uid": int(uid), "lstart": start,
        "command": command, "pgid": int(pgrp),
    }


def _vacant(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((base.HOST, port))
        except OSError:
            return False
    return True


def _read_root(requested: str) -> tuple[Path, dict]:
    given = Path(requested)
    if given.is_symlink():
        raise ProbeError("root_symlink")
    root = given.resolve(strict=True)
    try:
        root.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError as exc:
        raise ProbeError("root_outside_temp") from exc
    if (
        not root.is_dir() or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or not base._valid_launcher_root(root)
    ):
        raise ProbeError("root_not_private_launcher_owned")
    path = root / META
    if path.is_symlink() or not path.is_file():
        raise ProbeError("metadata_missing_or_symlink")
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ProbeError("metadata_not_private")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        data.get("schema") != SCHEMA or data.get("runtime_root") != str(root)
        or data.get("uid") != os.getuid()
        or not re.fullmatch(r"[0-9a-f]{32}", str(data.get("token", "")))
        or data.get("mode") not in ("sleep", "python")
        or not isinstance(data.get("pid"), int) or data["pid"] <= 0
        or data.get("port") != PORT
    ):
        raise ProbeError("metadata_mismatch")
    for name in ("stdout.log", "stderr.log"):
        log = root / name
        if log.is_symlink() or not log.is_file():
            raise ProbeError(f"log_missing_or_symlink:{name}")
        if log.stat().st_uid != os.getuid() or stat.S_IMODE(log.stat().st_mode) != 0o600:
            raise ProbeError(f"log_not_private:{name}")
    return root, data


def _matches(current: dict | None, expected: dict | None) -> bool:
    return bool(
        current and expected and all(current.get(key) == expected.get(key)
        for key in ("pid", "uid", "lstart", "command", "pgid"))
        and current["uid"] == os.getuid()
        and current["pgid"] == current["pid"]
    )


def start(mode: str, python: str | None, seconds: int) -> dict:
    if mode not in ("sleep", "python"):
        raise ProbeError("bad_mode")
    if not 2 <= seconds <= 180:
        raise ProbeError("bad_limit")
    if mode == "python" and not python:
        raise ProbeError("python_required")
    if not _vacant(PORT):
        raise ProbeError("inert_probe_port_not_vacant")
    root, created = base.prepare_runtime_root(None, reuse=False)
    if not created:
        raise ProbeError("new_root_required")
    layout = base.build_runtime_layout(root)
    token = os.urandom(16).hex()
    env = launchd._isolated_env(layout, port=PORT)
    profile = sandbox.write_sandbox_profile(root)
    if mode == "sleep":
        # Test detachment independently of Python or sandbox-exec first.
        command = ["/bin/sleep", str(seconds)]
    else:
        resolved = base.resolve_python(python, env)
        command = sandbox.sandbox_command(profile, [
            "/usr/bin/perl", "-e", f"alarm({seconds}); exec @ARGV",
            str(resolved), "-c", PYTHON_MARKER,
        ])
    with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
        os.chmod(root / "stdout.log", 0o600)
        os.chmod(root / "stderr.log", 0o600)
        process = subprocess.Popen(
            command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, close_fds=True,
            start_new_session=True,
        )
    try:
        observed = None
        # A fast Python marker may exit before an identity can be sampled.
        for _ in range(5):
            candidate = _identity(process.pid)
            if candidate is None:
                break
            if observed is not None and candidate == observed:
                break
            observed = candidate
            time.sleep(0.1)
        if mode == "sleep" and (
            observed is None or observed["uid"] != os.getuid()
            or observed["pgid"] != process.pid
            or observed["command"] != f"/bin/sleep {seconds}"
        ):
            raise ProbeError("sleep_start_identity_not_verified")
        data = {
            "schema": SCHEMA, "runtime_root": str(root), "token": token,
            "uid": os.getuid(), "mode": mode, "port": PORT,
            "pid": process.pid, "start_identity": observed,
            "env_keys": sorted(env),
            "expected_argv": command, "python_path": str(resolved) if mode == "python" else None,
            "limit_seconds": seconds, "started_at_unix": time.time(),
            "start_port_vacant": _vacant(PORT),
        }
        _private_write(root / META, data)
    except BaseException:
        # Do not leave an untracked detached process if identity collection or
        # the durable manifest fails after Popen succeeds.
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        raise
    return {"runtime_root": str(root), "token": token, "pid": process.pid,
            "identity_observed": observed is not None, "port_vacant": data["start_port_vacant"],
            "mode": mode}


def status(requested: str) -> dict:
    root, data = _read_root(requested)
    current = _identity(data["pid"])
    return {
        "runtime_root": str(root), "mode": data["mode"], "pid": data["pid"],
        "same_process_alive": _matches(current, data["start_identity"]),
        "pid_present": current is not None,
        "identity_mismatch": current is not None and not _matches(current, data["start_identity"]),
        "port_vacant": _vacant(PORT),
        "stdout": (root / "stdout.log").read_text(encoding="utf-8", errors="replace"),
        "stderr": (root / "stderr.log").read_text(encoding="utf-8", errors="replace"),
        "exit_recorded": (root / "stop.json").is_file(),
    }


def stop(requested: str) -> dict:
    root, data = _read_root(requested)
    current = _identity(data["pid"])
    if current is not None and not _matches(current, data["start_identity"]):
        raise ProbeError("stop_refused_pid_identity_mismatch")
    signalled = False
    if current is not None:
        # Recheck identity immediately before signaling the exact new session.
        if not _matches(_identity(data["pid"]), data["start_identity"]):
            raise ProbeError("stop_refused_identity_changed")
        os.killpg(data["pid"], signal.SIGTERM)
        signalled = True
    after = _identity(data["pid"])
    for _ in range(40):
        if after is None:
            break
        time.sleep(0.1)
        after = _identity(data["pid"])
    result = {
        "runtime_root": str(root), "pid": data["pid"], "signalled": signalled,
        "original_pid_exited": after is None,
        "port_vacant": _vacant(PORT),
        "stdout": (root / "stdout.log").read_text(encoding="utf-8", errors="replace"),
        "stderr": (root / "stderr.log").read_text(encoding="utf-8", errors="replace"),
        "exit_code": "unavailable_after_detach",
        "observed_at_unix": time.time(),
    }
    _private_write(root / "stop.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("start", "status", "stop"))
    parser.add_argument("--mode", choices=("sleep", "python"), default="sleep")
    parser.add_argument("--python")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--runtime-root")
    args = parser.parse_args()
    try:
        if args.action == "start":
            result = start(args.mode, args.python, args.seconds)
        else:
            if not args.runtime_root:
                raise ProbeError("runtime_root_required")
            result = status(args.runtime_root) if args.action == "status" else stop(args.runtime_root)
    except (ProbeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
