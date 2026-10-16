#!/usr/bin/env python3
"""One-shot launchd lifecycle for an isolated P4 Safari product probe.

The job belongs to the interactive user's GUI launchd domain, not to a Codex
exec session.  It never restarts on failure and never deletes the evidence root.
"""

from __future__ import annotations

import argparse
import errno
import http.client
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import time

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox


ROOT = Path(__file__).resolve().parent
LAUNCHCTL = Path("/bin/launchctl")
PS = Path("/bin/ps")
LSOF = Path("/usr/sbin/lsof")
CURRENT_NAME = "p4_preference_fallback_launchd.current.json"
RUN_PREFIX = "p4_preference_fallback_launchd."
LABEL_PREFIX = "org.uruhabrain.p4.preference."
SCHEMA = "uruha_p4_preference_fallback_launchd_v1"
PREFLIGHT_IMPORT_SCOPE = "legacy_base_import_unsandboxed_later_probes_sandboxed"
PYTHON_PROBE_SNIPPET = 'print("python-ready", flush=True)'


class ControllerError(RuntimeError):
    pass


def gui_domain() -> str:
    if sys.platform != "darwin" or not LAUNCHCTL.is_file():
        raise ControllerError("macos_launchctl_required")
    domain = f"gui/{os.getuid()}"
    result = subprocess.run(
        [str(LAUNCHCTL), "print", domain], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ControllerError(f"gui_launchd_domain_unavailable:{domain}")
    return domain


def _private_file(path: Path, content: bytes = b"") -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _isolated_env(layout: dict[str, Path], *, port: int | None) -> dict[str, str]:
    """Pass only documented runtime paths and inert process settings to launchd."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(layout["runtime_root"]),
        "TMPDIR": str(layout["runtime_root"]),
        "LANG": "en_US.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if port is None:
        return env
    scoped = base.child_environment(env, layout, port=port, prewarm=False)
    scoped["URUHA_PRODUCT_WRITE_SANDBOX"] = "1"
    return scoped


def _port_vacant(port: int) -> bool:
    """A bind check, not a reservation; repeat immediately before bootstrap."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((base.HOST, base.validate_port(port)))
        except OSError as exc:
            if exc.errno in (errno.EADDRINUSE, errno.EACCES):
                return False
            raise ControllerError(f"port_vacancy_check_failed:{port}:{exc.errno}") from exc
    return True


def _require_vacant_port(port: int) -> None:
    if not _port_vacant(port):
        raise ControllerError(f"product_port_not_vacant:{port}")


def _pid_owner(pid: int) -> int | None:
    # kill(pid, 0) may return EPERM for a same-UID launchd sandbox child on
    # macOS.  Read-only ps is the observable PID/UID check; unknown output is
    # never interpreted as a dead process.
    result = subprocess.run(
        [str(PS), "-p", str(pid), "-o", "pid=", "-o", "uid=", "-o", "stat="],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return None
    if result.returncode != 0:
        raise ControllerError(f"pid_inspection_unknown:{pid}:rc={result.returncode}")
    fields = result.stdout.split()
    if len(fields) != 3 or fields[0] != str(pid) or not fields[1].isdigit():
        raise ControllerError(f"pid_inspection_invalid:{pid}")
    return int(fields[1])


def _pid_alive(pid: int) -> bool:
    """Stop/reuse need the PID to be absent, regardless of transient UID."""
    return _pid_owner(pid) is not None


def _pid_owned_alive(pid: int) -> bool:
    """Start/readiness additionally require the launchd PID to be our user."""
    return _pid_owner(pid) == os.getuid()


def _new_root() -> tuple[Path, dict[str, Path]]:
    runtime_root, created = base.prepare_runtime_root(None, reuse=False)
    if not created:
        raise ControllerError("new_runtime_root_not_created")
    return runtime_root, base.build_runtime_layout(runtime_root)


def _run_file(label: str, extension: str) -> str:
    token = label.removeprefix(LABEL_PREFIX)
    if not re.fullmatch(r"[0-9a-f]{16}", token):
        raise ControllerError("invalid_launchd_label_for_run_file")
    return f"{RUN_PREFIX}{token}.{extension}"


def _publish_current(runtime_root: Path, metadata: dict) -> None:
    """Point at a successfully bootstrapped run; older run files stay intact."""
    current = runtime_root / CURRENT_NAME
    pending = runtime_root / f"{CURRENT_NAME}.{secrets.token_hex(8)}.pending"
    payload = {
        "schema": SCHEMA,
        "label": metadata["label"],
        "uid": os.getuid(),
    }
    _private_file(pending, (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(pending, current)


def _record_observed_pid(runtime_root: Path, metadata: dict, pid: int) -> dict:
    updated = dict(metadata, observed_pid=pid)
    path = runtime_root / _run_file(metadata["label"], "json")
    pending = runtime_root / f"{path.name}.{secrets.token_hex(8)}.pending"
    _private_file(pending, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(pending, path)
    return updated


def _record_stop(runtime_root: Path, metadata: dict, before: dict, after: dict) -> None:
    path = runtime_root / _run_file(metadata["label"], "stop.json")
    if path.exists():
        return
    payload = {
        "schema": SCHEMA,
        "label": metadata["label"],
        "stopped_at_unix": time.time(),
        "before": before,
        "after": after,
    }
    _private_file(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _snapshot_profile(profile: Path, runtime_root: Path, label: str) -> Path:
    """Preserve the sandbox policy referenced by each run's plist."""
    frozen = runtime_root / _run_file(label, "sandbox.sb")
    _private_file(frozen, profile.read_bytes())
    return frozen


def _probe_stdout_marker(runtime_root: Path, metadata: dict) -> bool:
    path = runtime_root / metadata["stdout_file"]
    if path.is_symlink() or not path.is_file():
        raise ControllerError("probe_stdout_missing_or_symlink")
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ControllerError("probe_stdout_not_private")
    with path.open("rb") as stream:
        output = stream.read(4097)
    return output == b"python-ready\n"


def _probe_outcome(runtime_root: Path, metadata: dict, job: dict) -> dict:
    marker = _probe_stdout_marker(runtime_root, metadata)
    termination_signal = job.get("last_terminating_signal") or ""
    if job["pid"] is not None:
        outcome = "running"
    elif termination_signal.rsplit(":", 1)[-1].strip() == "14":
        outcome = "timed_out"
    elif marker and job["last_exit_code"] == "0":
        outcome = "passed"
    elif job.get("state") == "not running":
        outcome = "marker_observed_exit_unrecorded" if marker else "failed"
    elif job["last_exit_code"] in (None, "(never exited)"):
        outcome = "pending"
    else:
        outcome = "failed"
    return {
        "probe_stdout_marker": marker,
        "probe_limit_seconds": metadata["probe_limit_seconds"],
        "probe_outcome": outcome,
        "python_path": metadata["python_path"],
    }


def _probe_status_evidence(runtime_root: Path, metadata: dict, job: dict) -> dict:
    if job["loaded"]:
        return {**_probe_outcome(runtime_root, metadata, job), "probe_outcome_source": "launchctl"}
    record = runtime_root / _run_file(metadata["label"], "stop.json")
    if record.is_symlink() or not record.is_file():
        return {
            "probe_outcome": "unverified_after_unload",
            "probe_outcome_source": "none",
            "probe_stdout_marker": _probe_stdout_marker(runtime_root, metadata),
            "probe_limit_seconds": metadata["probe_limit_seconds"],
            "python_path": metadata["python_path"],
        }
    if record.stat().st_uid != os.getuid() or stat.S_IMODE(record.stat().st_mode) != 0o600:
        raise ControllerError("probe_stop_record_not_private")
    try:
        saved = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControllerError("probe_stop_record_invalid") from exc
    if saved.get("schema") != SCHEMA or saved.get("label") != metadata["label"] or not isinstance(saved.get("before"), dict):
        raise ControllerError("probe_stop_record_mismatch")
    return {
        **_probe_outcome(runtime_root, metadata, saved["before"]),
        "probe_outcome_source": "stop_record",
    }


def _plist(
    *, label: str, command: list[str], env: dict[str, str], layout: dict[str, Path],
    stdout_name: str, stderr_name: str,
) -> bytes:
    return plistlib.dumps(
        {
            "Label": label,
            "ProgramArguments": command,
            "WorkingDirectory": str(ROOT),
            "EnvironmentVariables": env,
            "RunAtLoad": True,
            "KeepAlive": False,
            "AbandonProcessGroup": False,
            "StandardOutPath": str(layout["runtime_root"] / stdout_name),
            "StandardErrorPath": str(layout["runtime_root"] / stderr_name),
            "Umask": 0o077,
        },
        fmt=plistlib.FMT_XML,
    )


def _write_job(
    layout: dict[str, Path], *, label: str, command: list[str], env: dict[str, str], mode: str,
    port: int | None, python_path: str | None = None, probe_limit_seconds: int | None = None,
) -> dict:
    runtime_root = layout["runtime_root"]
    plist_name = _run_file(label, "plist")
    stdout_name = _run_file(label, "stdout.log")
    stderr_name = _run_file(label, "stderr.log")
    metadata = {
        "schema": SCHEMA,
        "runtime_root": str(runtime_root),
        "label": label,
        "uid": os.getuid(),
        "mode": mode,
        "port": port,
        "created_at_unix": time.time(),
        "keep_alive": False,
        "preflight_import_scope": PREFLIGHT_IMPORT_SCOPE if mode == "product" else "none",
        "env_keys": sorted(env),
        "command_executable": command[0],
        "plist_file": plist_name,
        "stdout_file": stdout_name,
        "stderr_file": stderr_name,
        "sandbox_profile_file": _run_file(label, "sandbox.sb"),
        "python_path": python_path,
        "probe_limit_seconds": probe_limit_seconds,
    }
    _private_file(runtime_root / stdout_name)
    _private_file(runtime_root / stderr_name)
    _private_file(
        runtime_root / plist_name,
        _plist(label=label, command=command, env=env, layout=layout,
               stdout_name=stdout_name, stderr_name=stderr_name),
    )
    _private_file(
        runtime_root / _run_file(label, "json"),
        (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return metadata


def _root_with_metadata(requested: str) -> tuple[Path, dict]:
    given = Path(requested).expanduser()
    if given.is_symlink():
        raise ControllerError("symlink_runtime_root_rejected")
    root = given.resolve(strict=True)
    temporary_parent = Path(tempfile.gettempdir()).resolve()
    try:
        root.relative_to(temporary_parent)
    except ValueError as exc:
        raise ControllerError("runtime_root_outside_temp_parent") from exc
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ControllerError("runtime_root_not_owned_by_user")
    if stat.S_IMODE(root.stat().st_mode) != 0o700 or not base._valid_launcher_root(root):
        raise ControllerError("runtime_root_not_private_launcher_owned")
    current_path = root / CURRENT_NAME
    if current_path.is_symlink() or not current_path.is_file():
        raise ControllerError("controller_current_pointer_missing")
    if current_path.stat().st_uid != os.getuid() or stat.S_IMODE(current_path.stat().st_mode) != 0o600:
        raise ControllerError("controller_current_pointer_not_private")
    try:
        pointer = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControllerError("controller_current_pointer_invalid") from exc
    current_label = pointer.get("label")
    if (
        pointer.get("schema") != SCHEMA
        or pointer.get("uid") != os.getuid()
        or not isinstance(current_label, str)
        or not re.fullmatch(re.escape(LABEL_PREFIX) + r"[0-9a-f]{16}", current_label)
    ):
        raise ControllerError("controller_current_pointer_not_this_job")
    metadata_path = root / _run_file(current_label, "json")
    if metadata_path.is_symlink() or not metadata_path.is_file():
        raise ControllerError("controller_metadata_missing")
    if metadata_path.stat().st_uid != os.getuid() or stat.S_IMODE(metadata_path.stat().st_mode) != 0o600:
        raise ControllerError("controller_metadata_not_private")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControllerError("controller_metadata_invalid") from exc
    label = metadata.get("label")
    if (
        metadata.get("schema") != SCHEMA
        or metadata.get("runtime_root") != str(root)
        or metadata.get("uid") != os.getuid()
        or not isinstance(label, str)
        or label != current_label
        or metadata.get("keep_alive") is not False
        or metadata.get("mode") not in ("dry-run", "product", "python-probe")
        or (metadata.get("mode") in ("product", "python-probe") and (
            not isinstance(metadata.get("port"), int)
            or not 1024 <= metadata["port"] <= 65535
        ))
        or (metadata.get("mode") == "python-probe" and (
            not isinstance(metadata.get("python_path"), str)
            or not isinstance(metadata.get("probe_limit_seconds"), int)
            or not 2 <= metadata["probe_limit_seconds"] <= 120
        ))
        or metadata.get("plist_file") != _run_file(label, "plist")
        or metadata.get("stdout_file") != _run_file(label, "stdout.log")
        or metadata.get("stderr_file") != _run_file(label, "stderr.log")
        or metadata.get("sandbox_profile_file") != _run_file(label, "sandbox.sb")
    ):
        raise ControllerError("controller_metadata_not_this_job")
    plist_path = root / _run_file(label, "plist")
    if plist_path.is_symlink() or not plist_path.is_file():
        raise ControllerError("controller_plist_missing")
    if plist_path.stat().st_uid != os.getuid() or stat.S_IMODE(plist_path.stat().st_mode) != 0o600:
        raise ControllerError("controller_plist_not_private")
    try:
        job = plistlib.loads(plist_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ControllerError("controller_plist_invalid") from exc
    if (
        job.get("Label") != label
        or job.get("KeepAlive") is not False
        or job.get("StandardOutPath") != str(root / metadata["stdout_file"])
        or job.get("StandardErrorPath") != str(root / metadata["stderr_file"])
    ):
        raise ControllerError("controller_plist_not_this_job")
    if metadata["mode"] in ("product", "python-probe"):
        env = job.get("EnvironmentVariables")
        if not isinstance(env, dict) or any((
            env.get("URUHA_MEMORY_DB_PATH") != str(root / "memory_db"),
            env.get("URUHA_WEB_SESSION_DB_PATH") != str(root / "session_db"),
            env.get("URUHA_WEB_LOG_JSONL_PATH") != str(root / "web_logs" / "conversation.jsonl"),
            env.get("URUHA_WEB_PORT") != str(metadata["port"]),
            env.get("URUHA_WEB_HOST") != base.HOST,
        )):
            raise ControllerError("controller_plist_isolation_mismatch")
    if metadata["mode"] == "python-probe":
        args = job.get("ProgramArguments")
        if not isinstance(args, list) or args[-3:] != [
            metadata["python_path"], "-c", PYTHON_PROBE_SNIPPET
        ]:
            raise ControllerError("controller_python_probe_command_mismatch")
    return root, metadata


def _target(domain: str, metadata: dict) -> str:
    return f"{domain}/{metadata['label']}"


def _job_status(domain: str, metadata: dict) -> dict:
    target = _target(domain, metadata)
    result = subprocess.run(
        [str(LAUNCHCTL), "print", target], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        # launchctl may also fail because its domain is unavailable or because
        # inspection was denied.  Only the exact service-not-found diagnostic
        # for our validated label is evidence that this job is unloaded.
        expected = (
            f'Could not find service "{metadata["label"]}" '
            f'in domain for user gui: {os.getuid()}'
        )
        if result.returncode != 113 or expected not in (result.stderr + "\n" + result.stdout).splitlines():
            raise ControllerError(
                f"launchctl_status_unknown:rc={result.returncode}:"
                f"{(result.stderr or result.stdout).strip()[:500]}"
            )
    output = result.stdout if result.returncode == 0 else ""
    def field(name: str) -> str | None:
        match = re.search(rf"(?m)^\s*{re.escape(name)} = ([^\n]+)$", output)
        return match.group(1).strip() if match else None
    pid_text = field("pid")
    pid = int(pid_text) if pid_text and pid_text.isdigit() else None
    return {
        "target": target,
        "loaded": result.returncode == 0,
        "state": field("state"),
        "pid": pid,
        "last_exit_code": field("last exit code"),
        "last_exit_status": field("last exit status"),
        "last_terminating_signal": field("last terminating signal"),
        "launchctl_returncode": result.returncode,
        "confirmed_not_found": result.returncode != 0,
    }


def _listener_owned_by_pid(pid: int, port: int) -> bool:
    """Require the exact launchd PID to own the loopback LISTEN socket."""
    if not LSOF.is_file():
        raise ControllerError("lsof_required_for_http_attribution")
    result = subprocess.run(
        [str(LSOF), "-nP", "-a", "-p", str(pid), f"-iTCP:{port}",
         "-sTCP:LISTEN", "-Fpn"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return False
    if result.returncode != 0:
        raise ControllerError(f"listener_inspection_unknown:{pid}:{port}:rc={result.returncode}")
    lines = result.stdout.splitlines()
    owners = {line[1:] for line in lines if line.startswith("p") and line[1:].isdigit()}
    names = {line[1:] for line in lines if line.startswith("n")}
    if owners != {str(pid)}:
        raise ControllerError(f"listener_pid_attribution_invalid:{pid}:{port}")
    return f"{base.HOST}:{port}" in names


def verify_ready(requested: str) -> dict:
    """Read-only product gate: exact job PID owns port before/after HTTP 200."""
    domain = gui_domain()
    root, metadata = _root_with_metadata(requested)
    if metadata["mode"] != "product":
        raise ControllerError("http_readiness_product_only")
    job = _job_status(domain, metadata)
    pid = job["pid"]
    port = metadata["port"]
    if (
        not job["loaded"] or pid is None or pid != metadata.get("observed_pid")
        or not _pid_owned_alive(pid) or not _listener_owned_by_pid(pid, port)
    ):
        raise ControllerError("product_not_ready_or_not_own_listener")
    connection = http.client.HTTPConnection(base.HOST, port, timeout=2)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        status_code = response.status
        response.read(1)
    except (OSError, http.client.HTTPException) as exc:
        raise ControllerError(f"product_http_not_ready:{type(exc).__name__}") from exc
    finally:
        connection.close()
    after = _job_status(domain, metadata)
    if (
        status_code != 200 or not after["loaded"] or after["pid"] != pid
        or not _pid_owned_alive(pid) or not _listener_owned_by_pid(pid, port)
    ):
        raise ControllerError("product_http_readiness_not_attributable")
    return {
        "ok": True,
        "ready": True,
        "http_ready_verified": True,
        "http_status": status_code,
        "runtime_root": str(root),
        "target": _target(domain, metadata),
        "pid": pid,
        "port": port,
        "url": f"http://{base.HOST}:{port}/",
        "listener_owned_by_job_pid": True,
        "preflight_import_scope": metadata["preflight_import_scope"],
    }


def start(
    *, mode: str, seconds: int, port: int, python: str | None,
    reuse_runtime_root: str | None = None,
) -> dict:
    domain = gui_domain()
    if mode not in ("dry-run", "product", "python-probe"):
        raise ControllerError("invalid_mode")
    if mode == "dry-run" and not 2 <= seconds <= 1800:
        raise ControllerError("dry_run_seconds_out_of_range")
    if mode == "python-probe" and not 2 <= seconds <= 120:
        raise ControllerError("python_probe_seconds_out_of_range")
    if mode == "product" and not python:
        raise ControllerError("product_requires_explicit_python")
    if mode == "python-probe" and not python:
        raise ControllerError("python_probe_requires_explicit_python")
    if mode == "python-probe" and reuse_runtime_root is not None:
        raise ControllerError("python_probe_requires_new_root")
    if mode == "product":
        base.validate_port(port)
        _require_vacant_port(port)
    if reuse_runtime_root is None:
        runtime_root, layout = _new_root()
        prior_label = None
    else:
        runtime_root, prior_metadata = _root_with_metadata(reuse_runtime_root)
        if prior_metadata["mode"] != mode:
            raise ControllerError("reuse_mode_mismatch")
        prior_status = _job_status(domain, prior_metadata)
        if prior_status["loaded"]:
            raise ControllerError("reuse_previous_job_still_loaded")
        prior_pid = prior_metadata.get("observed_pid")
        if not isinstance(prior_pid, int) or prior_pid <= 0:
            raise ControllerError("reuse_previous_pid_not_recorded")
        if _pid_alive(prior_pid):
            raise ControllerError("reuse_previous_pid_still_alive")
        if mode == "product":
            _require_vacant_port(prior_metadata["port"])
        layout = base.build_runtime_layout(runtime_root)
        prior_label = prior_metadata["label"]
    label = LABEL_PREFIX + secrets.token_hex(8)
    if label == prior_label:
        raise ControllerError("launchd_label_collision")
    if mode == "product":
        # The inherited base preflight still imports its entry outside the write
        # sandbox.  Later probes and the launched product are sandboxed.  Do not
        # describe the entire preflight as sandboxed until that chain changes.
        import p4_preference_fallback_safe_isolated_product_launcher as launcher

        env_base = _isolated_env(layout, port=None)
        summary, env, _, _, profile = launcher.preflight_preference_fallback(
            python_arg=python,
            runtime_root_arg=str(runtime_root),
            reuse_runtime=True,
            port=port,
            prewarm=False,
            environ=env_base,
        )
        frozen_profile = _snapshot_profile(profile, runtime_root, label)
        command = sandbox.sandbox_command(frozen_profile, [summary["python"], str(launcher.ENTRYPOINT)])
        env = {key: value for key, value in env.items() if key in set(_isolated_env(layout, port=port))}
        _require_vacant_port(port)
    elif mode == "python-probe":
        # Diagnose interpreter/TCC startup without importing Web or model.
        # The OS alarm survives exec and bounds a pre-main Python hang.
        env = _isolated_env(layout, port=port)
        resolved = base.resolve_python(python, env)
        expected = Path(os.path.abspath(os.fspath(Path(python).expanduser())))
        if resolved != expected:
            raise ControllerError("python_probe_explicit_python_not_resolved")
        profile = sandbox.write_sandbox_profile(runtime_root)
        frozen_profile = _snapshot_profile(profile, runtime_root, label)
        command = sandbox.sandbox_command(
            frozen_profile,
            ["/usr/bin/perl", "-e", f"alarm({seconds}); exec @ARGV",
             str(resolved), "-c", PYTHON_PROBE_SNIPPET],
        )
    else:
        profile = sandbox.write_sandbox_profile(runtime_root)
        frozen_profile = _snapshot_profile(profile, runtime_root, label)
        env = _isolated_env(layout, port=None)
        # Integer seconds were validated above; no untrusted shell text is interpolated.
        command = sandbox.sandbox_command(
            frozen_profile, ["/bin/sh", "-c", f"printf 'launchd-dry-run-ready\\n'; exec /bin/sleep {seconds}"],
        )
    metadata = _write_job(
        layout, label=label, command=command, env=env, mode=mode,
        port=port if mode in ("product", "python-probe") else None,
        python_path=str(resolved) if mode == "python-probe" else None,
        probe_limit_seconds=seconds if mode == "python-probe" else None,
    )
    if mode == "product":
        _require_vacant_port(port)
    result = subprocess.run(
        [str(LAUNCHCTL), "bootstrap", domain, str(runtime_root / metadata["plist_file"])],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise ControllerError(
            f"launchd_bootstrap_failed:rc={result.returncode}:runtime_root={runtime_root}:"
            f"{(result.stderr or result.stdout).strip()[:500]}"
        )
    status = _job_status(domain, metadata)
    pid = status["pid"]
    process_verified_live = bool(status["loaded"] and pid is not None and _pid_owned_alive(pid))
    if status["loaded"] and not process_verified_live:
        # A just-bootstrapped launchd job can be queued or transitioning UID.
        # This observes the exact label only; it does not claim HTTP readiness.
        for _ in range(20):
            time.sleep(0.1)
            status = _job_status(domain, metadata)
            pid = status["pid"]
            process_verified_live = bool(status["loaded"] and pid is not None and _pid_owned_alive(pid))
            if (
                not status["loaded"] or process_verified_live
                or (mode == "python-probe" and status["last_exit_code"] not in (None, "(never exited)"))
            ):
                break
    if process_verified_live:
        metadata = _record_observed_pid(runtime_root, metadata, pid)
    _publish_current(runtime_root, metadata)
    return {
        "ok": True,
        "bootstrap_succeeded": True,
        "lifecycle_status": (
            "bootstrapped_http_unverified" if mode == "product"
            else "python_probe_bootstrapped" if mode == "python-probe"
            else "dry_run_bootstrapped"
        ),
        "process_verified_live": process_verified_live,
        "http_ready_verified": False,
        "ready": False,
        "preflight_import_scope": metadata["preflight_import_scope"],
        "runtime_root": str(runtime_root),
        "reused_runtime_root": reuse_runtime_root is not None,
        "previous_label": prior_label,
        "mode": mode,
        "python_path": metadata.get("python_path"),
        "probe_limit_seconds": metadata.get("probe_limit_seconds"),
        "candidate_url": f"http://{base.HOST}:{port}/" if mode == "product" else None,
        **(_probe_outcome(runtime_root, metadata, status) if mode == "python-probe" else {}),
        **status,
    }


def status(requested: str) -> dict:
    domain = gui_domain()
    root, metadata = _root_with_metadata(requested)
    job = _job_status(domain, metadata)
    pid = job["pid"]
    return {
        "ok": True,
        "runtime_root": str(root),
        "mode": metadata["mode"],
        "process_verified_live": bool(job["loaded"] and pid is not None and _pid_owned_alive(pid)),
        "http_ready_verified": False,
        "ready": False,
        "preflight_import_scope": metadata.get("preflight_import_scope", "unknown"),
        "candidate_url": (
            f"http://{base.HOST}:{metadata['port']}/"
            if metadata["mode"] == "product" else None
        ),
        **(_probe_status_evidence(root, metadata, job) if metadata["mode"] == "python-probe" else {}),
        **job,
    }


def stop(requested: str) -> dict:
    domain = gui_domain()
    root, metadata = _root_with_metadata(requested)
    before = _job_status(domain, metadata)
    original_pid = before["pid"] or metadata.get("observed_pid")
    pid_observed = isinstance(original_pid, int) and original_pid > 0
    if not pid_observed and metadata["mode"] != "python-probe":
        raise ControllerError("stop_original_pid_not_recorded")
    if before["loaded"]:
        result = subprocess.run(
            [str(LAUNCHCTL), "bootout", _target(domain, metadata)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise ControllerError(f"launchd_bootout_failed:rc={result.returncode}:{result.stderr.strip()[:500]}")
    deadline = time.monotonic() + 10
    while True:
        after = _job_status(domain, metadata)
        pid_exited = not _pid_alive(original_pid) if pid_observed else None
        port_vacant = (
            metadata["mode"] != "product" or _port_vacant(metadata["port"])
        )
        if not after["loaded"] and (pid_exited is True or not pid_observed) and port_vacant:
            break
        if time.monotonic() >= deadline:
            raise ControllerError(
                "launchd_stop_unverified:"
                f"loaded={after['loaded']}:pid_exited={pid_exited}:port_vacant={port_vacant}:"
                f"runtime_root={root}"
            )
        time.sleep(0.2)
    _record_stop(root, metadata, before, after)
    return {
        "ok": True,
        "runtime_root": str(root),
        "stopped_exact_target": _target(domain, metadata),
        "before": before,
        "after": after,
        "original_pid_exited": pid_exited,
        "original_pid_observed": pid_observed,
        "port_vacant": port_vacant,
        "stop_record": str(root / _run_file(metadata["label"], "stop.json")),
        "probe_outcome_before_stop": (
            _probe_outcome(root, metadata, before)["probe_outcome"]
            if metadata["mode"] == "python-probe" else None
        ),
        "evidence_preserved": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    begin = sub.add_parser("start")
    begin.add_argument("--mode", choices=("dry-run", "product", "python-probe"), required=True)
    begin.add_argument("--seconds", type=int, default=90, help="dry-run 2..1800; python-probe 2..120")
    begin.add_argument("--port", type=int, default=7894, help="product / python-probe environment")
    begin.add_argument("--python", help="explicit product venv Python")
    begin.add_argument("--reuse-runtime-root", help="restart a verified stopped job in the same isolated root")
    for action in ("status", "stop", "verify-ready"):
        sub.add_parser(action).add_argument("--runtime-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.action == "start":
            payload = start(
                mode=args.mode, seconds=args.seconds, port=args.port, python=args.python,
                reuse_runtime_root=args.reuse_runtime_root,
            )
        elif args.action == "status":
            payload = status(args.runtime_root)
        elif args.action == "verify-ready":
            payload = verify_ready(args.runtime_root)
        else:
            payload = stop(args.runtime_root)
    except (ControllerError, base.LauncherError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
