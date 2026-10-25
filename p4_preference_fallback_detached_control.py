#!/usr/bin/env python3
"""Exact-identity, one-shot detached controller for isolated P4 product probes.

Start never means ready.  Only verify-ready checks that the same final Python
PID owns the localhost listener before and after HTTP 200.  No auto-restart,
model invocation, or Safari operation is performed by this controller.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import secrets
import select
import signal
import stat
import subprocess
import tarfile
import tempfile
import time

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_exec_detached_lifecycle_probe as identity
import p4_preference_fallback_launchd_control as launchd
import p4_b_product_source_manifest as product_sources


ROOT = Path(__file__).resolve().parent
SCHEMA = "uruha_p4_preference_fallback_detached_control_v1"
CURRENT = "p4_preference_fallback_detached.current.json"
PREFIX = "p4_preference_fallback_detached."
PREPARED = "p4_preference_fallback_detached.prepared.json"
PREPARED_CLAIM = "p4_preference_fallback_detached.prepared-claim.json"
ONNX_ARCHIVE_SIZE = 83_178_821
ONNX_ARCHIVE_SHA256 = "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
ONNX_FILES = frozenset({
    "config.json", "model.onnx", "special_tokens_map.json",
    "tokenizer_config.json", "tokenizer.json", "vocab.txt",
})
PORT = 7894
CALIBRATION_CODE = 'print("python-calibrated",flush=True);import time;time.sleep(4)'
CALIBRATION_CODE_B = ('import sys;print("python-calibrated="+sys.executable,flush=True);'
                      'import time;time.sleep(4)')
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_preference_fallback.py"
B_DESCRIPTOR_NAME = "p4_b_private_endpoint_descriptor.json"
B_MODEL_CLAIM_NAME = "p4_b_private_model_root.claim.json"
B_COMMITTED_SOURCES = (
    "p4_preference_fallback_detached_control.py",
    "uruha_web_ui_product_p4_preference_fallback.py",
    "uruha_p4_b_private_child_bootstrap.py",
    "uruha_p4_b_private_endpoint_binding.py",
    "uruha_web_ui.py",
    "uruha_compute_ledger.py",
    "p4_b_private_zero_turn_operator.py",
    "p4_stateful_private_evidence.py",
    "uruha_compact_planner_p2.py",
    "p4_b_safe_isolated_product_launcher.py",
    "p4_b_safe_isolated_product_launcher_v2.py",
    "p4_exec_detached_lifecycle_probe.py",
    "p4_preference_fallback_launchd_control.py",
    "p4_b_isolated_ollama_identity_probe.py",
    "uruha_p4_b_resource_gate.py",
    "uruha_p4_b_child_local_identity.py",
)
B_ARCHIVE_MAX_BYTES = 16 * 1024 * 1024
B_ARCHIVE_TIMEOUT_SECONDS = 15
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


def _private_stat(path: Path, *, directory: bool) -> os.stat_result:
    info = os.lstat(path)
    wanted = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        not wanted(info.st_mode) or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
        or (not directory and info.st_nlink != 1)
    ):
        raise ControllerError(f"prepared_path_not_private:{path}")
    return info


def prepare() -> dict:
    """Create a controller-owned root without starting Python or touching models."""
    root, created = base.prepare_runtime_root(None, reuse=False)
    if not created:
        raise ControllerError("new_runtime_root_required")
    base.build_runtime_layout(root)
    _private_stat(root, directory=True)
    _private_stat(root / base.MANIFEST_NAME, directory=False)
    _validate_reuse_tree(root)
    _private_json(root / PREPARED, {
        "schema": SCHEMA, "kind": "prepared_first_start", "runtime_root": str(root),
        "uid": os.getuid(), "mode": "product", "entrypoint": str(ENTRYPOINT),
        "port": PORT, "prepared_at_unix": time.time(),
    })
    return {"ok": True, "runtime_root": str(root), "prepared": True,
            "started": False, "entrypoint": str(ENTRYPOINT)}


def _prepared_root(requested: str) -> Path:
    given = Path(requested)
    if given.is_symlink():
        raise ControllerError("prepared_root_symlink")
    root = given.resolve(strict=True)
    temporary_parent = Path(tempfile.gettempdir()).resolve(strict=True)
    if root.parent != temporary_parent or not root.name.startswith("uruha-product-"):
        raise ControllerError("prepared_root_not_immediate_temp_child")
    _private_stat(root, directory=True)
    _private_stat(root / base.MANIFEST_NAME, directory=False)
    if not base._valid_launcher_root(root):
        raise ControllerError("prepared_root_not_launcher_owned")
    receipt_path = root / PREPARED
    _private_stat(receipt_path, directory=False)
    receipt = _read_private_json(receipt_path)
    if any((
        receipt.get("schema") != SCHEMA,
        receipt.get("kind") != "prepared_first_start",
        receipt.get("runtime_root") != str(root),
        receipt.get("uid") != os.getuid(),
        receipt.get("mode") != "product",
        receipt.get("entrypoint") != str(ENTRYPOINT),
        receipt.get("port") != PORT,
    )):
        raise ControllerError("prepared_receipt_mismatch")
    if (root / PREPARED_CLAIM).exists() or (root / PREPARED_CLAIM).is_symlink():
        raise ControllerError("prepared_root_already_claimed")
    allowed = {base.MANIFEST_NAME, PREPARED, "memory_db", "session_db", "web_logs", ".cache"}
    if {entry.name for entry in root.iterdir()} - allowed:
        raise ControllerError("prepared_root_stale_artifacts")
    for name in ("memory_db", "session_db", "web_logs"):
        directory = root / name
        _private_stat(directory, directory=True)
        if any(directory.iterdir()):
            raise ControllerError(f"prepared_root_nonempty:{name}")
    return root


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _b_git_archive_bytes(names: tuple[str, ...]) -> bytes:
    """Read bounded committed source without per-file Git processes."""
    command = ["/usr/bin/git", "-C", str(ROOT), "archive", "--format=tar",
               "HEAD", "--", *names]
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, close_fds=True,
        )
    except OSError as exc:
        raise ControllerError("p4_b_committed_source_unavailable") from exc
    chunks = []
    total = 0
    deadline = time.monotonic() + B_ARCHIVE_TIMEOUT_SECONDS
    try:
        if process.stdout is None:
            raise ControllerError("p4_b_committed_source_unavailable")
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ControllerError("p4_b_committed_source_timeout")
            readable, _, _ = select.select([process.stdout], [], [], remaining)
            if not readable:
                raise ControllerError("p4_b_committed_source_timeout")
            chunk = os.read(process.stdout.fileno(), min(65536, B_ARCHIVE_MAX_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > B_ARCHIVE_MAX_BYTES:
                raise ControllerError("p4_b_committed_source_oversize")
        remaining = deadline - time.monotonic()
        if remaining <= 0 or process.wait(timeout=remaining) != 0:
            raise ControllerError("p4_b_committed_source_unavailable")
        return b"".join(chunks)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ControllerError("p4_b_committed_source_unavailable") from exc
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()


def _b_committed_source_snapshot() -> dict[str, str]:
    """B starts only from committed critical sources, never a mutable WIP tree.

    This is a cooperative local source boundary, not a code-signing authority.
    The child separately compares current source hashes to its launch receipt.
    """
    try:
        names = tuple(sorted(set(B_COMMITTED_SOURCES) | set(
            product_sources.product_source_paths(ROOT))))
    except (OSError, ValueError, product_sources.ProductSourceManifestError) as exc:
        raise ControllerError("p4_b_product_source_manifest_invalid") from exc
    expected_dirs = {str(Path(name).parent) for name in names if "/" in name}
    archive = _b_git_archive_bytes(names)
    snapshot = {}
    seen = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as stream:
            for member in stream:
                name = member.name
                if name in seen:
                    raise ControllerError("p4_b_committed_source_duplicate")
                seen.add(name)
                if member.isdir():
                    if name not in expected_dirs or member.size != 0:
                        raise ControllerError("p4_b_committed_source_unexpected_member")
                    continue
                if not member.isfile() or name not in names:
                    raise ControllerError("p4_b_committed_source_unexpected_member")
                source = stream.extractfile(member)
                committed = source.read() if source is not None else None
                live = product_sources._regular_bytes(ROOT, name)
                if committed is None or len(committed) != member.size or live != committed:
                    raise ControllerError("p4_b_source_not_committed_or_drifted")
                snapshot[name] = hashlib.sha256(live).hexdigest()
    except (OSError, ValueError, tarfile.TarError,
            product_sources.ProductSourceManifestError) as exc:
        raise ControllerError("p4_b_committed_source_unavailable") from exc
    if set(snapshot) != set(names) or seen != set(names) | expected_dirs:
        raise ControllerError("p4_b_committed_source_incomplete")
    return snapshot


def _b_descriptor(path_arg: str, *, run_id: str):
    """Load an explicit 0600 model-root descriptor, with no Web import."""
    from uruha_p4_b_private_endpoint_binding import (
        PrivateEndpointBinding, PrivateEndpointBindingError,
        _exact_private_directory,
    )

    path = Path(path_arg)
    if path.name != B_DESCRIPTOR_NAME or not path.is_absolute():
        raise ControllerError("p4_b_descriptor_path_invalid")
    private_root = path.parent
    try:
        _exact_private_directory(private_root)
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            raise ControllerError("p4_b_descriptor_not_private")
        descriptor = json.loads(path.read_bytes())
    except (OSError, ValueError, PrivateEndpointBindingError) as exc:
        raise ControllerError("p4_b_descriptor_unavailable_or_invalid") from exc
    if not isinstance(descriptor, dict) or set(descriptor) != {
        "schema", "private_root", "shared_models", "daemon_pid", "runner_pid",
        "daemon_port", "runner_port", "daemon_process_start", "runner_process_start",
        "daemon_binary", "runner_binary",
        "daemon_raw_generation", "runner_raw_generation",
        "daemon_argv_sha256", "runner_argv_sha256", "operator_source_sha256",
    } or descriptor["schema"] != "p4_b_private_endpoint_descriptor_v2":
        raise ControllerError("p4_b_descriptor_shape_invalid")
    if descriptor["private_root"] != str(private_root):
        raise ControllerError("p4_b_descriptor_root_mismatch")
    if any(type(descriptor[key]) is not int for key in (
        "daemon_pid", "runner_pid", "daemon_port", "runner_port",
    )) or any(type(descriptor[key]) is not str for key in (
        "shared_models", "daemon_process_start", "runner_process_start",
        "daemon_binary", "runner_binary", "daemon_argv_sha256",
        "runner_argv_sha256", "operator_source_sha256",
    )):
        raise ControllerError("p4_b_descriptor_value_type_invalid")
    for field, pid in (("daemon_raw_generation", descriptor["daemon_pid"]),
                       ("runner_raw_generation", descriptor["runner_pid"])):
        value = descriptor[field]
        if (type(value) is not list or len(value) != 4
                or any(type(part) is not int for part in value)
                or value[0] != pid or value[1] <= 0 or value[2] <= 0
                or not (0 <= value[3] < 1_000_000)):
            raise ControllerError("p4_b_descriptor_raw_generation_invalid")
    if descriptor["runner_raw_generation"][1] != descriptor["daemon_pid"]:
        raise ControllerError("p4_b_descriptor_runner_parent_invalid")
    if any(not re.fullmatch(r"[0-9a-f]{64}", descriptor[key]) for key in (
        "daemon_argv_sha256", "runner_argv_sha256", "operator_source_sha256",
    )):
        raise ControllerError("p4_b_descriptor_digest_invalid")
    if (_b_committed_source_snapshot()["p4_b_private_zero_turn_operator.py"]
            != descriptor["operator_source_sha256"]):
        raise ControllerError("p4_b_descriptor_operator_source_drift")
    binding = PrivateEndpointBinding(
        run_id=run_id, private_root=private_root,
        shared_models=Path(descriptor["shared_models"]),
        receipt_path=private_root / "p4_b_private_endpoint_launch_receipt.json",
        receipt_sha256="0" * 64,
        base_url=f"http://127.0.0.1:{descriptor['daemon_port']}/v1",
        daemon_pid=descriptor["daemon_pid"], runner_pid=descriptor["runner_pid"],
        daemon_port=descriptor["daemon_port"], runner_port=descriptor["runner_port"],
        daemon_process_start=descriptor["daemon_process_start"],
        runner_process_start=descriptor["runner_process_start"],
        daemon_raw_generation=tuple(descriptor["daemon_raw_generation"]),
        runner_raw_generation=tuple(descriptor["runner_raw_generation"]),
        daemon_argv_sha256=descriptor["daemon_argv_sha256"],
        runner_argv_sha256=descriptor["runner_argv_sha256"],
        operator_source_sha256=descriptor["operator_source_sha256"],
        daemon_binary=Path(descriptor["daemon_binary"]),
        runner_binary=Path(descriptor["runner_binary"]),
    )
    return binding


def _b_ps_start(pid: int) -> str:
    """External audit witness; this seconds-level value is not raw generation."""
    try:
        result = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True, text=True, timeout=3, check=True,
        )
        value = result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ControllerError("p4_b_ps_generation_unavailable") from exc
    if not re.fullmatch(r"[A-Za-z]{3} [A-Za-z]{3} +\d{1,2} \d\d:\d\d:\d\d \d{4}", value):
        raise ControllerError("p4_b_ps_generation_unavailable")
    return value


def _b_ps_daemon_environment(pid: int, expected_models: str) -> None:
    """Retain the operator's external environment witness without logging it."""
    if any(character.isspace() for character in expected_models):
        raise ControllerError("p4_b_daemon_environment_ambiguous")
    try:
        result = subprocess.run(
            ["/bin/ps", "-wwE", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=3, check=True,
        )
        command = result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ControllerError("p4_b_daemon_environment_unavailable") from exc
    if (re.findall(r"(?:^|\s)OLLAMA_MODELS=(\S+)", command) != [expected_models]
            or re.findall(r"(?:^|\s)OLLAMA_NO_CLOUD=(\S+)", command) != ["1"]):
        raise ControllerError("p4_b_daemon_environment_drift")


def _b_controller_witness(binding) -> None:
    """Compare descriptor identity with fresh raw, ps, listener and argv witnesses.

    This runs outside the sandbox; the child independently uses the B-only OS
    observer without ps. No full argv or environment enters logs or receipts.
    """
    import p4_b_isolated_ollama_identity_probe as model_identity
    import uruha_p4_b_child_local_identity as child_identity

    try:
        before = (child_identity.raw_generation(binding.daemon_pid),
                  child_identity.raw_generation(binding.runner_pid))
        if before != (binding.daemon_raw_generation, binding.runner_raw_generation):
            raise ControllerError("p4_b_controller_raw_generation_drift")
        if (_b_ps_start(binding.daemon_pid) != binding.daemon_process_start
                or _b_ps_start(binding.runner_pid) != binding.runner_process_start):
            raise ControllerError("p4_b_controller_ps_generation_drift")
        _b_ps_daemon_environment(binding.daemon_pid,
                                 str(binding.private_root / "models"))
        daemon_ps = model_identity._process(binding.daemon_pid)
        runner_ps = model_identity._process(binding.runner_pid)
        model_identity._process_identity(
            daemon_pid=binding.daemon_pid, runner_pid=binding.runner_pid,
            daemon_port=binding.daemon_port, runner_port=binding.runner_port,
            daemon_binary=binding.daemon_binary, runner_binary=binding.runner_binary,
            model_blob=binding.private_root / "models" / "blobs"
                       / f"sha256-{model_identity.GGUF_SHA256}",
            expected=model_identity.FROZEN_MODEL,
        )
        daemon = child_identity.observe_process(binding.daemon_pid, {
            "OLLAMA_MODELS": str(binding.private_root / "models"),
            "OLLAMA_NO_CLOUD": "1",
        })
        runner = child_identity.observe_process(binding.runner_pid)
        if (daemon_ps != (daemon.ppid, list(daemon.argv))
                or runner_ps != (runner.ppid, list(runner.argv))
                or (daemon.pid, daemon.ppid, daemon.start_sec, daemon.start_usec)
                   != binding.daemon_raw_generation
                or (runner.pid, runner.ppid, runner.start_sec, runner.start_usec)
                   != binding.runner_raw_generation
                or runner.ppid != daemon.pid
                or daemon.env_exact != {"OLLAMA_MODELS": True, "OLLAMA_NO_CLOUD": True}
                or child_identity.argv_digest(daemon) != binding.daemon_argv_sha256
                or child_identity.argv_digest(runner) != binding.runner_argv_sha256
                or not child_identity.owns_loopback_listener(
                    binding.daemon_pid, binding.daemon_port)
                or not child_identity.owns_loopback_listener(
                    binding.runner_pid, binding.runner_port)):
            raise ControllerError("p4_b_controller_identity_drift")
        after = (child_identity.raw_generation(binding.daemon_pid),
                 child_identity.raw_generation(binding.runner_pid))
        if after != before:
            raise ControllerError("p4_b_controller_raw_generation_drift")
    except (OSError, ValueError, child_identity.ProbeError,
            model_identity.ProbeError) as exc:
        raise ControllerError("p4_b_controller_identity_unavailable") from exc


def _b_claim_model_root(binding) -> None:
    # A rejected/failed run must not silently reuse its model root. This
    # exclusive marker is issued before static preflight or a Web import.
    try:
        _private_json(binding.private_root / B_MODEL_CLAIM_NAME, {
            "schema": "p4_b_private_model_root_claim_v1", "run_id": binding.run_id,
            "private_root": str(binding.private_root), "uid": os.getuid(),
            "claimed_at_unix": time.time(),
        })
    except FileExistsError as exc:
        raise ControllerError("p4_b_model_root_already_claimed") from exc


def _b_static_preflight(root: Path, layout: dict, python: str,
                        base_env: dict, binding) -> tuple[str, dict, Path, dict]:
    """No product entry/Web import, model HTTP request, or provider call."""
    from uruha_p4_b_private_endpoint_binding import (
        canonical_b_env_digest, preflight_private_endpoint_identity,
    )

    _validate_prepared_cache(root)
    _validate_reuse_tree(root)
    snapshot = _b_committed_source_snapshot()
    resolved = str(base.resolve_python(python, base_env))
    env = launchd._isolated_env(layout, port=PORT)
    env.update({
        "URUHA_P4_B_PRIVATE_CHILD": "1",
        "URUHA_P4_B_RUN_ID": binding.run_id,
        "URUHA_P4_B_MODEL_ROOT": str(binding.private_root),
        "URUHA_P4_B_RECEIPT": str(binding.receipt_path),
        "URUHA_WEB_COMPUTE_LEDGER": "1",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "OLLAMA_NO_CLOUD": "1",
    })
    if any(key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}
           for key in env):
        raise ControllerError("p4_b_proxy_environment_forbidden")
    try:
        canonical_b_env_digest(env)
        _b_controller_witness(binding)
        preflight_private_endpoint_identity(binding)
    except Exception as exc:
        raise ControllerError(f"p4_b_private_identity_preflight_failed:{type(exc).__name__}") from exc
    profile = sandbox.write_sandbox_profile(root)
    return resolved, env, profile, snapshot


def _cache_walk_error(error: OSError) -> None:
    raise ControllerError("prepared_cache_walk_failed") from error


def _validate_prepared_cache(root: Path) -> None:
    cache = root / ".cache"
    _private_stat(cache, directory=True)
    for parent in (cache / "chroma", cache / "chroma" / "onnx_models",
                   cache / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"):
        _private_stat(parent, directory=True)
    model = cache / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
    extracted = model / "onnx"
    _private_stat(extracted, directory=True)
    # Every cache entry is private and a real inode; no traversal through
    # aliases, hardlinks, foreign files, or special device nodes is accepted.
    for directory, dirs, files in os.walk(
        cache, followlinks=False, onerror=_cache_walk_error
    ):
        _private_stat(Path(directory), directory=True)
        for name in dirs:
            _private_stat(Path(directory) / name, directory=True)
        for name in files:
            _private_stat(Path(directory) / name, directory=False)
    archive = model / "onnx.tar.gz"
    private_archive = _private_stat(archive, directory=False)
    if private_archive.st_size != ONNX_ARCHIVE_SIZE or _sha256(archive) != ONNX_ARCHIVE_SHA256:
        raise ControllerError("prepared_onnx_archive_size_or_sha_mismatch")
    host_archive = Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz"
    if host_archive.exists():
        host = os.stat(host_archive)
        if (host.st_dev, host.st_ino) == (private_archive.st_dev, private_archive.st_ino):
            raise ControllerError("prepared_onnx_archive_not_independent_inode")
    if {entry.name for entry in extracted.iterdir()} != ONNX_FILES:
        raise ControllerError("prepared_onnx_extracted_file_set_mismatch")
    try:
        with tarfile.open(archive, "r:gz") as stream:
            members = stream.getmembers()
            actual = {member.name for member in members if member.isfile()}
            if actual != {f"onnx/{name}" for name in ONNX_FILES} or any(
                not (member.isfile() or member.name == "onnx" and member.isdir())
                for member in members
            ):
                raise ControllerError("prepared_onnx_archive_members_mismatch")
            for name in ONNX_FILES:
                target = extracted / name
                _private_stat(target, directory=False)
                member = stream.getmember(f"onnx/{name}")
                source = stream.extractfile(member)
                if source is None:
                    raise ControllerError("prepared_onnx_archive_member_unreadable")
                digest = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                if target.stat().st_size != member.size or _sha256(target) != digest.hexdigest():
                    raise ControllerError(f"prepared_onnx_extracted_content_mismatch:{name}")
    except tarfile.TarError as exc:
        raise ControllerError("prepared_onnx_archive_unreadable") from exc


def _claim_prepared_root(root: Path) -> None:
    try:
        _private_json(root / PREPARED_CLAIM, {
            "schema": SCHEMA, "runtime_root": str(root), "uid": os.getuid(),
            "entrypoint": str(ENTRYPOINT), "claimed_at_unix": time.time(),
        })
    except FileExistsError as exc:
        raise ControllerError("prepared_root_already_claimed") from exc


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
            or (metadata.get("p4_b_private_launch") is not None
                and calibration.get("python_sys_executable") != python_path)
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
    if _port_listeners():
        raise ControllerError(f"localhost_port_not_vacant:{PORT}")


def _port_listeners() -> set[tuple[str, str]]:
    """Inspect all live TCP listeners; a post-close TIME_WAIT is not a listener.

    A failed/ambiguous lsof inspection is never evidence of vacancy.  Start
    checks this both before and after preflight, and verify-ready still checks
    the exact final PID and loopback scope before and after HTTP 200.
    """
    result = subprocess.run(
        [str(launchd.LSOF), "-nP", f"-iTCP:{PORT}",
         "-sTCP:LISTEN", "-Fpn"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return set()
    if result.returncode != 0 or result.stderr.strip():
        raise ControllerError(f"listener_inspection_unknown:rc={result.returncode}")
    owner = None
    owner_has_address = False
    file_pending = False
    listeners: set[tuple[str, str]] = set()
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            if owner is not None and (not owner_has_address or file_pending):
                raise ControllerError("listener_record_incomplete")
            owner = line[1:]
            owner_has_address = False
            if not owner.isdigit():
                raise ControllerError("listener_owner_invalid")
        elif line.startswith("f"):
            # macOS lsof includes a file-descriptor record even for -Fpn.
            if owner is None or not line[1:] or file_pending:
                raise ControllerError("listener_file_record_invalid")
            file_pending = True
        elif line.startswith("n"):
            if owner is None:
                raise ControllerError("listener_missing_owner")
            if not line[1:]:
                raise ControllerError("listener_address_invalid")
            listeners.add((owner, line[1:]))
            owner_has_address = True
            file_pending = False
        else:
            raise ControllerError("listener_record_invalid")
    if owner is not None and (not owner_has_address or file_pending):
        raise ControllerError("listener_record_incomplete")
    if not listeners:
        raise ControllerError("listener_inspection_empty_success")
    return listeners


def _listener_owned_by_pid(pid: int) -> bool:
    # Query the *entire* port, not merely the expected PID: reject a second
    # owner or an additional wildcard/non-loopback listener on this port.
    listeners = _port_listeners()
    if not listeners:
        return False
    if listeners != {(str(pid), f"{base.HOST}:{PORT}")}:
        raise ControllerError("listener_owner_or_loopback_scope_mismatch")
    return True


def _calibrate_python_command(python: str, env: dict[str, str], profile: Path,
                              *, capture_inprocess: bool = False) -> dict:
    """Discover the macOS Framework argv0 using the same sandboxed venv."""
    code = CALIBRATION_CODE_B if capture_inprocess else CALIBRATION_CODE
    command = sandbox.sandbox_command(profile, [python, "-c", code])
    process = subprocess.Popen(
        command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True, umask=0o077,
    )
    observed = None
    try:
        readable, _, _ = select.select([process.stdout], [], [], 10)
        marker = process.stdout.readline() if readable else b""
        inprocess_python = None
        if capture_inprocess:
            prefix = b"python-calibrated="
            if not marker.startswith(prefix) or not marker.endswith(b"\n"):
                raise ControllerError("python_inprocess_calibration_unavailable")
            try:
                inprocess_python = marker[len(prefix):-1].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ControllerError("python_inprocess_calibration_invalid") from exc
            if inprocess_python != python:
                raise ControllerError("python_inprocess_calibration_drift")
        elif marker != b"python-calibrated\n":
            raise ControllerError("python_calibration_marker_unavailable")
        for _ in range(10):
            seen = _identity(process.pid)
            if seen is None:
                raise ControllerError("python_calibration_exited_before_identity")
            if (
                seen["uid"] == os.getuid() and seen["pgid"] == process.pid
                and seen["command"].endswith(f" -c {code}")
            ):
                observed = seen
                break
            time.sleep(0.1)
        if observed is None:
            raise ControllerError("python_calibration_no_final_command")
        executable = observed["command"][: -len(f" -c {code}")]
        if (
            not executable.startswith("/") or " " in executable
            or not Path(executable).is_file() or not os.access(executable, os.X_OK)
        ):
            raise ControllerError("python_calibration_executable_invalid")
        result = {"python_ps_executable": executable, "identity": observed}
        if capture_inprocess:
            result["python_sys_executable"] = inprocess_python
        return result
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
        port_vacant = not _port_listeners()
    except (ControllerError, OSError) as exc:
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
          prepared_runtime_root: str | None = None, seconds: int = 60,
          p4_b_private: bool = False,
          p4_b_private_descriptor: str | None = None) -> dict:
    if mode not in ("product", "inert"):
        raise ControllerError("invalid_mode")
    if type(p4_b_private) is not bool:
        raise ControllerError("p4_b_private_opt_in_invalid")
    if p4_b_private:
        if (mode != "product" or prepared_runtime_root is None
                or reuse_runtime_root is not None):
            raise ControllerError("p4_b_requires_fresh_prepared_product_root")
        if type(p4_b_private_descriptor) is not str or not p4_b_private_descriptor:
            raise ControllerError("p4_b_private_descriptor_required")
    elif p4_b_private_descriptor is not None:
        raise ControllerError("p4_b_descriptor_without_explicit_opt_in")
    if prepared_runtime_root is not None and (
        mode != "product" or reuse_runtime_root is not None
    ):
        raise ControllerError("prepared_start_product_only_and_exclusive")
    if mode == "product" and not python:
        raise ControllerError("explicit_product_python_required")
    if mode == "inert" and not 2 <= seconds <= 180:
        raise ControllerError("inert_seconds_out_of_range")
    if prepared_runtime_root is None:
        _require_vacant()
    if prepared_runtime_root is not None:
        root = _prepared_root(prepared_runtime_root)
        # One-use claim is recorded before any model import/preflight process.
        # Failure after this point requires a new prepared root.
        _claim_prepared_root(root)
        _validate_prepared_cache(root)
        _require_vacant()
        previous_run = None
    elif reuse_runtime_root is None:
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
        if p4_b_private:
            binding = _b_descriptor(p4_b_private_descriptor, run_id=run_id)
            _b_claim_model_root(binding)
            resolved, env, profile, source_snapshot = _b_static_preflight(
                root, layout, python, base_env, binding,
            )
        else:
            import p4_preference_fallback_safe_isolated_product_launcher as launcher

            binding = None
            source_snapshot = None
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
            if prepared_runtime_root is not None:
                _validate_prepared_cache(root)
    else:
        profile = sandbox.write_sandbox_profile(root)
        env = launchd._isolated_env(layout, port=PORT)
        resolved = None
    _validate_reuse_tree(root)
    frozen = root / _name(run_id, "sandbox.sb")
    _private_bytes(frozen, profile.read_bytes())
    if mode == "product":
        calibration = (_calibrate_python_command(
            resolved, env, frozen, capture_inprocess=True)
            if p4_b_private else _calibrate_python_command(resolved, env, frozen))
        product_entrypoint = ENTRYPOINT if p4_b_private else launcher.ENTRYPOINT
        final_command = f"{calibration['python_ps_executable']} {product_entrypoint}"
        command = sandbox.sandbox_command(frozen, [resolved, str(product_entrypoint)])
    else:
        calibration = None
        final_command = None
        command = ["/bin/sleep", str(seconds)]
    _require_vacant()
    stdout_path = root / _name(run_id, "stdout.log")
    stderr_path = root / _name(run_id, "stderr.log")
    if p4_b_private:
        from uruha_p4_b_private_endpoint_binding import (
            canonical_b_env_digest, issue_private_child_receipt,
            preflight_private_endpoint_identity,
        )

        if _b_committed_source_snapshot() != source_snapshot:
            raise ControllerError("p4_b_source_changed_before_child_start")
        try:
            _b_controller_witness(binding)
            binding = issue_private_child_receipt(
                binding=binding, runtime_root=root, environ=env,
                entrypoint=ENTRYPOINT,
                expected_final_argv=[calibration["python_ps_executable"], str(ENTRYPOINT)],
                expected_inprocess_python_argv=[
                    calibration["python_sys_executable"], str(ENTRYPOINT)],
            )
            preflight_private_endpoint_identity(binding)
            b_env_sha256 = canonical_b_env_digest(env)
        except Exception as exc:
            raise ControllerError(f"p4_b_private_receipt_or_identity_failed:{type(exc).__name__}") from exc
        if _b_committed_source_snapshot() != source_snapshot:
            raise ControllerError("p4_b_source_changed_before_child_start")
        if _sha256(binding.receipt_path) != binding.receipt_sha256:
            raise ControllerError("p4_b_private_receipt_changed_before_child_start")
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        os.chmod(stdout_path, 0o600)
        os.chmod(stderr_path, 0o600)
        if prepared_runtime_root is not None:
            _validate_prepared_cache(root)
        if p4_b_private:
            if (_b_committed_source_snapshot() != source_snapshot
                    or _sha256(binding.receipt_path) != binding.receipt_sha256
                    or canonical_b_env_digest(env) != b_env_sha256):
                raise ControllerError("p4_b_child_launch_binding_drift")
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
                "none_b_static" if p4_b_private else
                launchd.PREFLIGHT_IMPORT_SCOPE if mode == "product" else "none"
            ),
            "started_at_unix": time.time(), "auto_restart": False,
        }
        if p4_b_private:
            metadata["p4_b_private_launch"] = {
                "schema": "p4_b_private_product_child_launch_v2",
                "run_id": run_id, "private_root": str(binding.private_root),
                "receipt_sha256": binding.receipt_sha256,
                "environment_sha256": b_env_sha256,
                "source_sha256": source_snapshot,
                "daemon_pid": binding.daemon_pid, "runner_pid": binding.runner_pid,
                "daemon_port": binding.daemon_port, "runner_port": binding.runner_port,
                "expected_final_argv": [calibration["python_ps_executable"], str(ENTRYPOINT)],
                "expected_inprocess_python_argv": [
                    calibration["python_sys_executable"], str(ENTRYPOINT)],
                "child_pid": process.pid,
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
    launch = metadata.get("p4_b_private_launch")
    if launch is None:
        if data.get("p4_b_private_ready") is not None:
            raise ControllerError("unexpected_p4_b_ready_record")
    else:
        ready = data.get("p4_b_private_ready")
        if (not isinstance(ready, dict)
                or ready.get("run_id") != metadata["run_id"]
                or ready.get("child_pid") != metadata["pid"]
                or ready.get("receipt_sha256") != launch.get("receipt_sha256")
                or ready.get("expected_final_argv") != launch.get("expected_final_argv")
                or ready.get("final_identity") != data["final_identity"]):
            raise ControllerError("p4_b_ready_record_mismatch")
    return data["final_identity"]


def _b_ready_launch_record(root: Path, metadata: dict, final_identity: dict) -> dict | None:
    """Tie HTTP-ready child PID/argv to the same private launch artifact.

    This is still only cooperative zero-provider identity, not B Send approval.
    """
    launch = metadata.get("p4_b_private_launch")
    if launch is None:
        return None
    expected_os = [metadata["calibration"]["python_ps_executable"], str(ENTRYPOINT)]
    expected_inprocess = [metadata["calibration"].get("python_sys_executable"),
                          str(ENTRYPOINT)]
    if (not isinstance(launch, dict)
            or launch.get("schema") != "p4_b_private_product_child_launch_v2"
            or launch.get("run_id") != metadata["run_id"]
            or launch.get("child_pid") != metadata["pid"]
            or launch.get("expected_final_argv") != expected_os
            or launch.get("expected_inprocess_python_argv") != expected_inprocess
            or final_identity.get("command") != metadata.get("final_command")):
        raise ControllerError("p4_b_ready_launch_identity_mismatch")
    if _b_committed_source_snapshot() != launch.get("source_sha256"):
        raise ControllerError("p4_b_ready_source_drift")
    from uruha_p4_b_private_endpoint_binding import (
        PrivateEndpointBindingError, _exact_os_final_argv, _final_argv_digest,
        _receipt, _valid_receipt_time,
        preflight_private_endpoint_identity, private_child_source_digests,
    )

    descriptor = Path(launch["private_root"]) / B_DESCRIPTOR_NAME
    try:
        binding = _b_descriptor(str(descriptor), run_id=metadata["run_id"])
        binding = replace(binding, receipt_sha256=launch["receipt_sha256"])
        receipt = _receipt(binding)
        _valid_receipt_time(receipt)
        _exact_os_final_argv(expected_os)
        if (receipt.get("expected_os_final_argv") != expected_os
                or receipt.get("expected_final_argv_sha256")
                != _final_argv_digest(expected_os)
                or receipt.get("expected_inprocess_python_argv_sha256")
                != _final_argv_digest(expected_inprocess)
                or final_identity.get("command") != " ".join(expected_os)):
            raise ControllerError("p4_b_ready_dual_argv_identity_mismatch")
        expected_receipt_identity = {
            "schema": "p4_b_private_endpoint_launch_receipt_v5",
            "issuer": "p4_b_private_controller",
            "run_id": binding.run_id,
            "private_root": str(binding.private_root),
            "models_path": str(binding.private_root / "models"),
            "ollama_models": str(binding.private_root / "models"),
            "ollama_no_cloud": "1",
            "shared_models": str(binding.shared_models),
            "base_url": binding.base_url,
            "daemon_pid": binding.daemon_pid,
            "runner_pid": binding.runner_pid,
            "daemon_port": binding.daemon_port,
            "runner_port": binding.runner_port,
            "daemon_process_start": binding.daemon_process_start,
            "runner_process_start": binding.runner_process_start,
            "daemon_raw_generation": list(binding.daemon_raw_generation),
            "runner_raw_generation": list(binding.runner_raw_generation),
            "daemon_argv_sha256": binding.daemon_argv_sha256,
            "runner_argv_sha256": binding.runner_argv_sha256,
            "operator_source_sha256": binding.operator_source_sha256,
            "daemon_binary": str(binding.daemon_binary),
            "runner_binary": str(binding.runner_binary),
            **private_child_source_digests(ENTRYPOINT),
        }
        if (any(receipt.get(key) != value
                for key, value in expected_receipt_identity.items())
                or receipt.get("runtime_root") != str(root)
                or receipt.get("launch_env_sha256") != launch["environment_sha256"]
                or binding.daemon_pid != launch["daemon_pid"]
                or binding.runner_pid != launch["runner_pid"]
                or binding.daemon_port != launch["daemon_port"]
                or binding.runner_port != launch["runner_port"]):
            raise ControllerError("p4_b_ready_receipt_identity_mismatch")
        _b_controller_witness(binding)
        preflight_private_endpoint_identity(binding)
    except (OSError, KeyError, PrivateEndpointBindingError) as exc:
        raise ControllerError("p4_b_ready_private_identity_unavailable") from exc
    return {
        "schema": "p4_b_private_product_child_ready_v1",
        "run_id": metadata["run_id"], "child_pid": metadata["pid"],
        "receipt_sha256": launch["receipt_sha256"],
        "expected_final_argv": launch["expected_final_argv"],
        "final_identity": final_identity,
        "same_private_endpoint_at_ready": True,
        "b_send_authorized": False,
    }


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
        "port_vacant": not _port_listeners(),
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
    b_ready = _b_ready_launch_record(root, metadata, after)
    if recorded is None:
        record = {
            "schema": SCHEMA, "runtime_root": str(root),
            "run_id": metadata["run_id"], "pid": metadata["pid"],
            "start_identity": metadata["start_identity"],
            "final_identity": after, "http_status": code,
            "listener_same_pid_before_after": True,
            "verified_at_unix": time.time(),
        }
        if b_ready is not None:
            record["p4_b_private_ready"] = b_ready
        _private_json(root / _name(metadata["run_id"], "ready.json"), record)
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
    try:
        port_vacant = not _port_listeners()
        port_inspection_error = None
    except (ControllerError, OSError) as exc:
        port_vacant = None
        port_inspection_error = f"{type(exc).__name__}:{exc}"
    result = {
        "schema": SCHEMA, "runtime_root": str(root),
        "run_id": metadata["run_id"], "pid": metadata["pid"],
        "before_identity": current, "before_stage": stage,
        "ready_identity": ready_identity,
        "signalled": signalled, "original_pid_exited": after is None,
        # This means no live TCP LISTEN socket on the entire port, not that a
        # plain bind succeeds while recently closed sockets are in TIME_WAIT.
        "port_vacant": port_vacant,
        "port_vacancy_basis": "no_tcp_listener_all_owners_lsof",
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
            else "listener_inspection_unknown" if port_inspection_error is not None
            else "process_or_port_not_clean_after_term"
        )
        if port_inspection_error is not None:
            result["port_inspection_error"] = port_inspection_error
        attempt = root / _name(metadata["run_id"], f"stop-attempt-{secrets.token_hex(4)}.json")
        _private_json(attempt, result)
        return {"ok": False, "stop_attempt_file": str(attempt), **result}
    _private_json(path, result)
    return {"ok": True, **result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "start", "status", "verify-ready", "stop"))
    parser.add_argument("--mode", choices=("product", "inert"), default="product")
    parser.add_argument("--python")
    parser.add_argument("--runtime-root")
    parser.add_argument("--reuse-runtime-root")
    parser.add_argument("--prepared-runtime-root")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--p4-b-private", action="store_true")
    parser.add_argument("--p4-b-private-descriptor")
    args = parser.parse_args(argv)
    try:
        if args.action != "start" and (
            args.p4_b_private or args.p4_b_private_descriptor is not None
        ):
            raise ControllerError("p4_b_private_options_start_only")
        if args.action == "prepare":
            result = prepare()
        elif args.action == "start":
            result = start(mode=args.mode, python=args.python,
                           reuse_runtime_root=args.reuse_runtime_root,
                           prepared_runtime_root=args.prepared_runtime_root,
                           seconds=args.seconds,
                           p4_b_private=args.p4_b_private,
                           p4_b_private_descriptor=args.p4_b_private_descriptor)
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
