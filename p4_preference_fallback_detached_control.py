#!/usr/bin/env python3
"""Exact-identity, one-shot detached controller for isolated P4 product probes.

Start never means ready.  Only verify-ready checks that the same final Python
PID owns the localhost listener before and after HTTP 200.  No auto-restart,
model invocation, or Safari operation is performed by this controller.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import select
import signal
import stat
import subprocess
import tempfile
import time

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_exec_detached_lifecycle_probe as identity
import p4_preference_fallback_launchd_control as launchd


ROOT = Path(__file__).resolve().parent
SCHEMA = "uruha_p4_preference_fallback_detached_control_v1"
CURRENT = "p4_preference_fallback_detached.current.json"
PREFIX = "p4_preference_fallback_detached."
PORT = 7894
CALIBRATION_CODE = 'print("python-calibrated",flush=True);import time;time.sleep(4)'
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_preference_fallback.py"
ISOLATION_KEYS = (
    "HOME", "TMPDIR", "URUHA_MEMORY_DB_PATH", "URUHA_WEB_SESSION_DB_PATH",
    "URUHA_WEB_LOG_JSONL_PATH", "URUHA_WEB_LOG_TXT_PATH",
    "URUHA_WEB_HOST", "URUHA_WEB_PORT", "URUHA_PRODUCT_WRITE_SANDBOX",
    "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED",
)


class ControllerError(RuntimeError):
    pass


def _name(run_id: str, suffix: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise ControllerError("invalid_run_id")
    return f"{PREFIX}{run_id}.{suffix}"


def _private_bytes(path: Path, value: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)


def _private_json(path: Path, value: dict) -> None:
    _private_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def _read_private_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ControllerError(f"missing_or_symlink:{path.name}")
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ControllerError(f"not_private:{path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ControllerError(f"invalid_json:{path.name}")
    return data


def _atomic_current(root: Path, run_id: str) -> None:
    pending = root / f"{CURRENT}.{secrets.token_hex(8)}.pending"
    _private_json(pending, {"schema": SCHEMA, "run_id": run_id, "uid": os.getuid()})
    os.replace(pending, root / CURRENT)


def _expected_isolation(root: Path) -> dict[str, str]:
    layout = {
        "runtime_root": root,
        "memory_db": root / "memory_db",
        "session_db": root / "session_db",
        "web_logs": root / "web_logs",
        "jsonl_log": root / "web_logs" / "conversation.jsonl",
        "text_log": root / "web_logs" / "conversation.txt",
    }
    env = launchd._isolated_env(layout, port=PORT)
    return {key: env[key] for key in ISOLATION_KEYS}


def _validate_reuse_tree(root: Path) -> None:
    """Never follow a reused runtime symlink before base.build_runtime_layout."""
    for name in ("memory_db", "session_db", "web_logs"):
        top = root / name
        info = os.lstat(top)
        if (
            not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ControllerError(f"runtime_tree_not_private_directory:{name}")
        stack = [top]
        while stack:
            directory = stack.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    child = Path(entry.path)
                    child_info = entry.stat(follow_symlinks=False)
                    if child_info.st_uid != os.getuid():
                        raise ControllerError(f"runtime_tree_foreign_owner:{child}")
                    if stat.S_ISLNK(child_info.st_mode):
                        raise ControllerError(f"runtime_tree_symlink:{child}")
                    if stat.S_ISDIR(child_info.st_mode):
                        stack.append(child)
                    elif stat.S_ISREG(child_info.st_mode):
                        if child_info.st_nlink != 1:
                            raise ControllerError(f"runtime_tree_file_hardlinked:{child}")
                        if child.parent == root / "web_logs" and child.name in (
                            "conversation.jsonl", "conversation.txt"
                        ) and stat.S_IMODE(child_info.st_mode) != 0o600:
                            raise ControllerError(f"runtime_log_not_private:{child}")
                    else:
                        raise ControllerError(f"runtime_tree_special_file:{child}")


def _root(requested: str) -> tuple[Path, dict]:
    given = Path(requested)
    if given.is_symlink():
        raise ControllerError("runtime_root_symlink")
    root = given.resolve(strict=True)
    try:
        root.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError as exc:
        raise ControllerError("runtime_root_outside_temp") from exc
    if (
        not root.is_dir() or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or not base._valid_launcher_root(root)
    ):
        raise ControllerError("runtime_root_not_private_launcher_owned")
    current = _read_private_json(root / CURRENT)
    run_id = current.get("run_id")
    if (
        current.get("schema") != SCHEMA or current.get("uid") != os.getuid()
        or not isinstance(run_id, str)
    ):
        raise ControllerError("current_pointer_mismatch")
    metadata = _read_private_json(root / _name(run_id, "json"))
    if (
        metadata.get("schema") != SCHEMA or metadata.get("run_id") != run_id
        or metadata.get("runtime_root") != str(root)
        or metadata.get("uid") != os.getuid()
        or metadata.get("mode") not in ("product", "inert")
        or metadata.get("port") != PORT
        or not isinstance(metadata.get("pid"), int) or metadata["pid"] <= 0
        or not isinstance(metadata.get("start_identity"), dict)
        or metadata["start_identity"].get("pid") != metadata["pid"]
        or metadata["start_identity"].get("uid") != os.getuid()
        or metadata["start_identity"].get("pgid") != metadata["pid"]
        or metadata.get("isolation") != _expected_isolation(root)
    ):
        raise ControllerError("run_metadata_mismatch")
    if metadata["mode"] == "product":
        python_path = metadata.get("python_path")
        calibration = metadata.get("calibration")
        if (
            not isinstance(python_path, str) or not Path(python_path).is_file()
            or not isinstance(calibration, dict)
            or not isinstance(calibration.get("python_ps_executable"), str)
            or metadata.get("expected_argv") != sandbox.sandbox_command(
                root / _name(run_id, "sandbox.sb"), [python_path, str(ENTRYPOINT)]
            )
            or metadata.get("wrapper_expected_command") != " ".join(metadata["expected_argv"])
            or metadata.get("pre_main_command") != f"{python_path} {ENTRYPOINT}"
            or metadata.get("final_command") != (
                f"{calibration['python_ps_executable']} {ENTRYPOINT}"
            )
        ):
            raise ControllerError("product_command_or_root_mismatch")
    for suffix in ("stdout.log", "stderr.log", "sandbox.sb"):
        path = root / _name(run_id, suffix)
        if path.is_symlink() or not path.is_file():
            raise ControllerError(f"run_file_missing_or_symlink:{suffix}")
        info = path.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ControllerError(f"run_file_not_private:{suffix}")
    return root, metadata


def _identity(pid: int) -> dict | None:
    return identity._identity(pid)


def _same_origin(current: dict, metadata: dict) -> bool:
    original = metadata["start_identity"]
    return bool(
        current["pid"] == metadata["pid"]
        and current["uid"] == metadata["uid"]
        and current["lstart"] == original.get("lstart")
        and current["pgid"] == metadata["pid"] == original.get("pgid")
        and original.get("pid") == metadata["pid"]
        and original.get("uid") == metadata["uid"]
    )


def _validated_stage(current: dict | None, metadata: dict) -> str:
    if current is None:
        return "exited"
    if not _same_origin(current, metadata):
        raise ControllerError("pid_origin_mismatch")
    if metadata["mode"] == "inert":
        if current["command"] != metadata["start_identity"].get("command"):
            raise ControllerError("inert_command_changed")
        return "inert"
    if current["command"] == metadata["final_command"]:
        return "final_python"
    if current["command"] == metadata["pre_main_command"]:
        return "pre_main_python"
    if current["command"] == metadata["wrapper_expected_command"]:
        return "wrapper"
    raise ControllerError("unapproved_wrapper_to_python_command_change")


def _require_vacant() -> None:
    if not identity._vacant(PORT):
        raise ControllerError(f"localhost_port_not_vacant:{PORT}")


def _listener_owned_by_pid(pid: int) -> bool:
    result = subprocess.run(
        [str(launchd.LSOF), "-nP", f"-iTCP:{PORT}",
         "-sTCP:LISTEN", "-Fpn"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return False
    if result.returncode != 0:
        raise ControllerError(f"listener_inspection_unknown:rc={result.returncode}")
    owner = None
    listeners: set[tuple[str, str]] = set()
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            owner = line[1:]
            if not owner.isdigit():
                raise ControllerError("listener_owner_invalid")
        elif line.startswith("n"):
            if owner is None:
                raise ControllerError("listener_missing_owner")
            listeners.add((owner, line[1:]))
    # Query the *entire* port, not merely the expected PID: reject a second
    # owner or an additional wildcard/non-loopback listener on this port.
    if listeners != {(str(pid), f"{base.HOST}:{PORT}")}:
        raise ControllerError("listener_owner_or_loopback_scope_mismatch")
    return True


def _calibrate_python_command(python: str, env: dict[str, str], profile: Path) -> dict:
    """Discover the macOS Framework argv0 using the same sandboxed venv."""
    command = sandbox.sandbox_command(profile, [python, "-c", CALIBRATION_CODE])
    process = subprocess.Popen(
        command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True, umask=0o077,
    )
    observed = None
    try:
        readable, _, _ = select.select([process.stdout], [], [], 10)
        if not readable or process.stdout.readline() != b"python-calibrated\n":
            raise ControllerError("python_calibration_marker_unavailable")
        for _ in range(10):
            seen = _identity(process.pid)
            if seen is None:
                raise ControllerError("python_calibration_exited_before_identity")
            if (
                seen["uid"] == os.getuid() and seen["pgid"] == process.pid
                and seen["command"].endswith(f" -c {CALIBRATION_CODE}")
            ):
                observed = seen
                break
            time.sleep(0.1)
        if observed is None:
            raise ControllerError("python_calibration_no_final_command")
        executable = observed["command"][: -len(f" -c {CALIBRATION_CODE}")]
        if (
            not executable.startswith("/") or " " in executable
            or not Path(executable).is_file() or not os.access(executable, os.X_OK)
        ):
            raise ControllerError("python_calibration_executable_invalid")
        return {"python_ps_executable": executable, "identity": observed}
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _group_members(pgid: int) -> list[dict]:
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,uid=,pgid=,command="],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise ControllerError(f"process_group_inspection_unknown:rc={result.returncode}")
    members = []
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=3)
        if len(fields) >= 3 and all(value.isdigit() for value in fields[:3]):
            if int(fields[2]) == pgid:
                members.append({"pid": int(fields[0]), "uid": int(fields[1]),
                                "command": fields[3] if len(fields) == 4 else ""})
    return members


def _cleanup_failed_start(
    process: subprocess.Popen, root: Path, run_id: str,
    allowed_commands: set[str], cause: BaseException,
) -> dict:
    """Signal only our verified new group; preserve uncertainty, never name-kill."""
    inspection_errors = []
    try:
        before = _identity(process.pid)
    except (identity.ProbeError, OSError) as exc:
        before = None
        inspection_errors.append(f"before:{type(exc).__name__}")
    allowed = bool(
        before and before["pid"] == process.pid
        and before["uid"] == os.getuid() and before["pgid"] == process.pid
        and before["command"] in allowed_commands
    )
    signalled = False
    if allowed:
        try:
            again = _identity(process.pid)
        except (identity.ProbeError, OSError) as exc:
            again = None
            inspection_errors.append(f"recheck:{type(exc).__name__}")
        if again == before:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                signalled = True
            except ProcessLookupError:
                pass
    if signalled:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    try:
        after = _identity(process.pid)
    except (identity.ProbeError, OSError) as exc:
        after = None
        inspection_errors.append(f"after:{type(exc).__name__}")
    try:
        members = _group_members(process.pid)
    except (ControllerError, OSError) as exc:
        members = None
        inspection_errors.append(f"group:{type(exc).__name__}")
    try:
        port_vacant = identity._vacant(PORT)
    except OSError as exc:
        port_vacant = None
        inspection_errors.append(f"port:{type(exc).__name__}")
    evidence = {
        "schema": SCHEMA, "runtime_root": str(root), "run_id": run_id,
        "pid": process.pid, "failure_type": type(cause).__name__,
        "failure_message": str(cause)[:300],
        "before_identity": before, "allowed_identity": allowed,
        "signalled_verified_group": signalled, "after_identity": after,
        "remaining_group_members": members, "port_vacant": port_vacant,
        "inspection_errors": inspection_errors,
        "cleanup_verified": (
            not inspection_errors and after is None and members == []
            and port_vacant is True
        ),
        "observed_at_unix": time.time(),
    }
    _private_json(root / _name(run_id, "start-failure.json"), evidence)
    return evidence


def start(*, mode: str, python: str | None, reuse_runtime_root: str | None = None,
          seconds: int = 60) -> dict:
    if mode not in ("product", "inert"):
        raise ControllerError("invalid_mode")
    if mode == "product" and not python:
        raise ControllerError("explicit_product_python_required")
    if mode == "inert" and not 2 <= seconds <= 180:
        raise ControllerError("inert_seconds_out_of_range")
    _require_vacant()
    if reuse_runtime_root is None:
        root, created = base.prepare_runtime_root(None, reuse=False)
        if not created:
            raise ControllerError("new_runtime_root_required")
        previous_run = None
    else:
        root, prior = _root(reuse_runtime_root)
        _validate_reuse_tree(root)
        if prior["mode"] != mode:
            raise ControllerError("reuse_mode_mismatch")
        stopped = _read_private_json(root / _name(prior["run_id"], "stop.json"))
        prior_ready = _ready_identity(root, prior)
        planned_prior_identity = (
            prior["start_identity"] if mode == "inert" else prior_ready
        )
        planned_prior_stage = "inert" if mode == "inert" else "final_python"
        if (
            stopped.get("schema") != SCHEMA or stopped.get("run_id") != prior["run_id"]
            or stopped.get("pid") != prior["pid"]
            or stopped.get("planned_stop") is not True
            or stopped.get("signalled") is not True
            or planned_prior_identity is None
            or stopped.get("before_identity") != planned_prior_identity
            or stopped.get("before_stage") != planned_prior_stage
            or stopped.get("ready_identity") != prior_ready
            or stopped.get("original_pid_exited") is not True
            or stopped.get("port_vacant") is not True
            or _identity(prior["pid"]) is not None
        ):
            raise ControllerError("previous_run_not_exactly_stopped")
        previous_run = prior["run_id"]
    layout = base.build_runtime_layout(root)
    _validate_reuse_tree(root)
    run_id = secrets.token_hex(8)
    if run_id == previous_run:
        raise ControllerError("run_id_collision")
    base_env = launchd._isolated_env(layout, port=None)
    if mode == "product":
        import p4_preference_fallback_safe_isolated_product_launcher as launcher

        summary, launcher_env, _, _, profile = launcher.preflight_preference_fallback(
            python_arg=python, runtime_root_arg=str(root), reuse_runtime=True,
            port=PORT, prewarm=False, environ=base_env,
        )
        env = {key: value for key, value in launcher_env.items()
               if key in set(launchd._isolated_env(layout, port=PORT))}
        resolved = str(summary["python"])
        if resolved != str(base.resolve_python(python, env)):
            raise ControllerError("preflight_python_changed")
        if launcher.ENTRYPOINT != ENTRYPOINT:
            raise ControllerError("product_entrypoint_changed")
    else:
        profile = sandbox.write_sandbox_profile(root)
        env = launchd._isolated_env(layout, port=PORT)
        resolved = None
    _validate_reuse_tree(root)
    frozen = root / _name(run_id, "sandbox.sb")
    _private_bytes(frozen, profile.read_bytes())
    if mode == "product":
        calibration = _calibrate_python_command(resolved, env, frozen)
        final_command = f"{calibration['python_ps_executable']} {launcher.ENTRYPOINT}"
        command = sandbox.sandbox_command(frozen, [resolved, str(launcher.ENTRYPOINT)])
    else:
        calibration = None
        final_command = None
        command = ["/bin/sleep", str(seconds)]
    _require_vacant()
    stdout_path = root / _name(run_id, "stdout.log")
    stderr_path = root / _name(run_id, "stderr.log")
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        os.chmod(stdout_path, 0o600)
        os.chmod(stderr_path, 0o600)
        process = subprocess.Popen(
            command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, close_fds=True,
            start_new_session=True, umask=0o077,
        )
    try:
        original = None
        for _ in range(20):
            seen = _identity(process.pid)
            if seen is None:
                raise ControllerError("detached_child_exited_before_identity")
            if seen["uid"] != os.getuid() or seen["pgid"] != process.pid:
                raise ControllerError("detached_child_uid_or_group_mismatch")
            if mode == "inert":
                if seen["command"] == f"/bin/sleep {seconds}":
                    original = seen
                    break
            elif seen["command"] in (
                " ".join(command), f"{resolved} {ENTRYPOINT}", final_command
            ):
                original = seen
                break
            time.sleep(0.1)
        if original is None:
            raise ControllerError("detached_child_command_not_expected")
        metadata = {
            "schema": SCHEMA, "runtime_root": str(root), "run_id": run_id,
            "previous_run_id": previous_run, "uid": os.getuid(),
            "mode": mode, "port": PORT, "pid": process.pid,
            "start_identity": original, "expected_argv": command,
            "wrapper_expected_command": " ".join(command),
            "pre_main_command": f"{resolved} {ENTRYPOINT}" if mode == "product" else None,
            "wrapper_identity_observed": (
                original if mode == "product" and original["command"] == " ".join(command)
                else None
            ),
            "final_command": final_command, "python_path": resolved,
            "calibration": calibration, "env_keys": sorted(env),
            "isolation": {key: env[key] for key in ISOLATION_KEYS},
            "preflight_import_scope": (
                launchd.PREFLIGHT_IMPORT_SCOPE if mode == "product" else "none"
            ),
            "started_at_unix": time.time(), "auto_restart": False,
        }
        _private_json(root / _name(run_id, "json"), metadata)
        _atomic_current(root, run_id)
    except BaseException as exc:
        allowed_commands = (
            {f"/bin/sleep {seconds}"} if mode == "inert"
            else {" ".join(command), f"{resolved} {ENTRYPOINT}", final_command}
        )
        failure = _cleanup_failed_start(process, root, run_id, allowed_commands, exc)
        raise ControllerError(
            f"detached_start_failed:runtime_root={root}:run_id={run_id}:"
            f"cleanup_verified={failure['cleanup_verified']}:cause={type(exc).__name__}"
        ) from exc
    return {
        "ok": True, "runtime_root": str(root), "run_id": run_id,
        "previous_run_id": previous_run, "mode": mode, "pid": process.pid,
        "start_identity": original, "ready": False,
        "http_ready_verified": False, "candidate_url": f"http://{base.HOST}:{PORT}/"
        if mode == "product" else None,
    }


def _ready_identity(root: Path, metadata: dict) -> dict | None:
    path = root / _name(metadata["run_id"], "ready.json")
    if not path.exists():
        return None
    data = _read_private_json(path)
    if (
        data.get("schema") != SCHEMA or data.get("run_id") != metadata["run_id"]
        or data.get("pid") != metadata["pid"]
        or data.get("runtime_root") != str(root)
        or not isinstance(data.get("final_identity"), dict)
    ):
        raise ControllerError("ready_record_mismatch")
    return data["final_identity"]


def status(requested: str) -> dict:
    root, metadata = _root(requested)
    current = _identity(metadata["pid"])
    stage = _validated_stage(current, metadata)
    ready_identity = _ready_identity(root, metadata)
    if ready_identity is not None and current is not None and current != ready_identity:
        raise ControllerError("ready_final_identity_changed")
    return {
        "ok": True, "runtime_root": str(root), "run_id": metadata["run_id"],
        "mode": metadata["mode"], "pid": metadata["pid"], "stage": stage,
        "same_origin_alive": current is not None,
        "ready_recorded": ready_identity is not None,
        "port_vacant": identity._vacant(PORT),
        "http_ready_verified": False, "ready": False,
        "stdout_file": str(root / _name(metadata["run_id"], "stdout.log")),
        "stderr_file": str(root / _name(metadata["run_id"], "stderr.log")),
    }


def verify_ready(requested: str) -> dict:
    root, metadata = _root(requested)
    if metadata["mode"] != "product":
        raise ControllerError("http_readiness_product_only")
    before = _identity(metadata["pid"])
    if _validated_stage(before, metadata) != "final_python":
        raise ControllerError("product_not_final_python")
    recorded = _ready_identity(root, metadata)
    if recorded is not None and before != recorded:
        raise ControllerError("ready_final_identity_changed")
    if not _listener_owned_by_pid(metadata["pid"]):
        raise ControllerError("product_listener_not_same_pid")
    connection = http.client.HTTPConnection(base.HOST, PORT, timeout=2)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        code = response.status
        response.read(1)
    except (OSError, http.client.HTTPException) as exc:
        raise ControllerError(f"product_http_not_ready:{type(exc).__name__}") from exc
    finally:
        connection.close()
    after = _identity(metadata["pid"])
    if (
        code != 200 or after != before
        or _validated_stage(after, metadata) != "final_python"
        or not _listener_owned_by_pid(metadata["pid"])
    ):
        raise ControllerError("product_http_ready_not_attributable")
    if recorded is None:
        _private_json(root / _name(metadata["run_id"], "ready.json"), {
            "schema": SCHEMA, "runtime_root": str(root),
            "run_id": metadata["run_id"], "pid": metadata["pid"],
            "start_identity": metadata["start_identity"],
            "final_identity": after, "http_status": code,
            "listener_same_pid_before_after": True,
            "verified_at_unix": time.time(),
        })
    return {
        "ok": True, "ready": True, "http_ready_verified": True,
        "runtime_root": str(root), "run_id": metadata["run_id"],
        "pid": metadata["pid"], "port": PORT,
        "url": f"http://{base.HOST}:{PORT}/", "final_identity": after,
        "listener_same_pid_before_after": True,
    }


def stop(requested: str) -> dict:
    root, metadata = _root(requested)
    path = root / _name(metadata["run_id"], "stop.json")
    if path.exists():
        raise ControllerError("run_already_has_stop_record")
    current = _identity(metadata["pid"])
    stage = _validated_stage(current, metadata)
    ready_identity = _ready_identity(root, metadata)
    if ready_identity is not None and current is not None and current != ready_identity:
        raise ControllerError("stop_refused_final_identity_changed")
    planned_candidate = bool(
        current is not None and (
            (metadata["mode"] == "inert" and stage == "inert")
            or (metadata["mode"] == "product" and ready_identity is not None
                and stage == "final_python" and current == ready_identity)
        )
    )
    signalled = False
    if current is not None:
        # Only three predeclared command forms are accepted across wrapper,
        # venv pre-main and calibrated final Python exec stages.
        if stage not in ("inert", "wrapper", "pre_main_python", "final_python"):
            raise ControllerError("stop_refused_unknown_stage")
        again = _identity(metadata["pid"])
        if again != current or _validated_stage(again, metadata) != stage:
            raise ControllerError("stop_refused_identity_changed_before_term")
        try:
            os.killpg(metadata["pid"], signal.SIGTERM)
            signalled = True
        except ProcessLookupError:
            # It died between the last identity observation and TERM.  This
            # is not a successful planned stop or restart authorization.
            pass
    after = _identity(metadata["pid"])
    for _ in range(100):
        if after is None:
            break
        time.sleep(0.1)
        after = _identity(metadata["pid"])
    result = {
        "schema": SCHEMA, "runtime_root": str(root),
        "run_id": metadata["run_id"], "pid": metadata["pid"],
        "before_identity": current, "before_stage": stage,
        "ready_identity": ready_identity,
        "signalled": signalled, "original_pid_exited": after is None,
        "port_vacant": identity._vacant(PORT),
        "exit_code": "unavailable_after_detach",
        "observed_at_unix": time.time(),
    }
    result["planned_stop"] = bool(
        planned_candidate and signalled
        and result["original_pid_exited"] and result["port_vacant"]
    )
    if not result["planned_stop"]:
        result["failure_reason"] = (
            "unexpected_process_absent_before_stop" if current is None
            else "product_not_ready_at_stop" if metadata["mode"] == "product" and not planned_candidate
            else "process_or_port_not_clean_after_term"
        )
        attempt = root / _name(metadata["run_id"], f"stop-attempt-{secrets.token_hex(4)}.json")
        _private_json(attempt, result)
        return {"ok": False, "stop_attempt_file": str(attempt), **result}
    _private_json(path, result)
    return {"ok": True, **result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("start", "status", "verify-ready", "stop"))
    parser.add_argument("--mode", choices=("product", "inert"), default="product")
    parser.add_argument("--python")
    parser.add_argument("--runtime-root")
    parser.add_argument("--reuse-runtime-root")
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        if args.action == "start":
            result = start(mode=args.mode, python=args.python,
                           reuse_runtime_root=args.reuse_runtime_root,
                           seconds=args.seconds)
        else:
            if not args.runtime_root:
                raise ControllerError("runtime_root_required")
            action = {"status": status, "verify-ready": verify_ready, "stop": stop}[args.action]
            result = action(args.runtime_root)
    except (ControllerError, identity.ProbeError, base.LauncherError,
            OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
