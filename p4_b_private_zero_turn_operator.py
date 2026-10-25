#!/usr/bin/env python3
"""One-use, non-B, zero-turn private P4 product qualification.

Explicit ``--execute`` is required. This script never sends a chat turn or
authorizes P4 B. It prepares a new isolated model service and product root,
checks one real child through the existing controller, and stops only process
identities captured in this invocation. Its time targets are observed stop
lines, not hard watchdog guarantees for synchronous controller calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable

import p4_b_isolated_ollama_identity_probe as probe
import p4_preference_fallback_detached_control as control
import uruha_p4_b_private_endpoint_binding as binding


ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv/product_checks/bin/python"
ONNX_ARCHIVE = Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz"
SHARED_MODELS = Path.home() / ".ollama/models"
DAEMON_BINARY = Path("/Applications/Ollama.app/Contents/Resources/ollama")
RUNNER_BINARY = Path("/Applications/Ollama.app/Contents/Resources/llama-server")
DAEMON_PORT = 11455
PRODUCT_PORT = control.PORT
MIN_FREE_BYTES = 20 * 1024**3
MAX_CLONE_DISK_DELTA = 1 * 1024**3
MAX_DAEMON_WALL_S = 480.0  # Observed stop line, not a hard synchronous timeout.
MAX_CHILD_READY_S = 240.0
RESULT_NAME = "p4_b_private_zero_turn_result.json"
DESCRIPTOR_FIELDS = frozenset({
    "schema", "private_root", "shared_models", "daemon_pid", "runner_pid",
    "daemon_port", "runner_port", "daemon_process_start", "runner_process_start",
    "daemon_binary", "runner_binary",
})


class OperatorError(RuntimeError):
    """Fixed reason code only; never include environment, prompt, or log text."""


def _fail(reason: str) -> None:
    raise OperatorError(reason)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _private_file(path: Path, value: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def _private_directory(path: Path) -> None:
    path.mkdir(mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
        _fail("private_directory_invalid")


def _listener_pids(port: int) -> frozenset[int]:
    try:
        completed = subprocess.run(
            ["/usr/sbin/lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OperatorError("listener_inspection_unavailable") from exc
    if completed.returncode == 1 and not completed.stdout.strip():
        return frozenset()
    if completed.returncode != 0:
        _fail("listener_inspection_unavailable")
    try:
        return frozenset(int(row) for row in completed.stdout.splitlines())
    except ValueError as exc:
        raise OperatorError("listener_inspection_invalid") from exc


def _generation(pid: int) -> str | None:
    try:
        return binding._process_start(pid)
    except binding.PrivateEndpointBindingError:
        return None


def _process_argv(pid: int) -> tuple[int, list[str]] | None:
    try:
        return probe._process(pid)
    except probe.ProbeError:
        return None


def _same_process(pid: int, generation: str, binary: Path, *, daemon: bool,
                  expected_parent: int | None = None,
                  expected_argv: tuple[str, ...] | None = None) -> bool:
    if _generation(pid) != generation:
        return False
    seen = _process_argv(pid)
    if seen is None:
        return False
    parent, argv = seen
    if not argv or (expected_parent is not None and parent != expected_parent):
        return False
    try:
        if Path(argv[0]).resolve(strict=True) != binary.resolve(strict=True):
            return False
    except OSError:
        return False
    if expected_argv is not None and tuple(argv) != expected_argv:
        return False
    return argv[1:2] == ["serve"] if daemon else "--offline" in argv


def _stop_exact(pid: int, generation: str, binary: Path, *, daemon: bool,
                expected_parent: int | None = None,
                expected_argv: tuple[str, ...] | None = None) -> str:
    if _generation(pid) is None:
        return "already_absent"
    if not _same_process(pid, generation, binary, daemon=daemon,
                         expected_parent=expected_parent, expected_argv=expected_argv):
        return "identity_drift_no_signal"
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return "already_absent"
    except OSError:
        return "exact_term_failed_review_required"
    for _ in range(50):
        if _generation(pid) is None:
            return "terminated"
        time.sleep(0.1)
    if not _same_process(pid, generation, binary, daemon=daemon,
                         expected_parent=expected_parent, expected_argv=expected_argv):
        return "identity_drift_no_kill"
    # This is still only the exact captured process, never a process group.
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return "terminated"
    except OSError:
        return "exact_kill_failed_review_required"
    for _ in range(20):
        if _generation(pid) is None:
            return "killed_exact"
        time.sleep(0.1)
    return "still_alive"


def _available_bytes() -> int:
    return shutil.disk_usage(tempfile.gettempdir()).free


def _static_preflight() -> dict:
    if Path(sys.prefix).resolve() != PYTHON.parent.parent.resolve():
        _fail("wrong_product_python")
    control._b_committed_source_snapshot()
    if _listener_pids(DAEMON_PORT) or _listener_pids(PRODUCT_PORT):
        _fail("private_or_product_port_occupied")
    shared = _listener_pids(11434)
    if not shared:
        _fail("shared_port_identity_unavailable")
    shared_generations = {pid: _generation(pid) for pid in shared}
    if any(value is None for value in shared_generations.values()):
        _fail("shared_process_identity_unavailable")
    for path, digest in ((DAEMON_BINARY, probe.FROZEN_DAEMON_SHA256),
                         (RUNNER_BINARY, probe.FROZEN_RUNNER_SHA256)):
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or path.resolve(strict=True) != path or _sha256(path) != digest):
            _fail("ollama_binary_unverified")
    if _available_bytes() < MIN_FREE_BYTES:
        _fail("insufficient_private_disk")
    if (not ONNX_ARCHIVE.is_file() or ONNX_ARCHIVE.is_symlink()
            or ONNX_ARCHIVE.stat().st_size != control.ONNX_ARCHIVE_SIZE
            or _sha256(ONNX_ARCHIVE) != control.ONNX_ARCHIVE_SHA256):
        _fail("host_onnx_archive_unverified")
    return {"shared_listener_pids": sorted(shared),
            "shared_process_generations": shared_generations,
            "free_bytes_before": _available_bytes()}


def _prepare_product_root(on_created: Callable[[Path], None] | None = None) -> Path:
    root = Path(control.prepare()["runtime_root"])
    if on_created is not None:
        on_created(root)
    evidence = ROOT / "p4_stateful_private_evidence.py"
    for action in ("cache", "warm"):
        command = [str(PYTHON), str(evidence), action, "--runtime-root", str(root)]
        if action == "cache":
            command.extend(["--source-archive", str(ONNX_ARCHIVE)])
        try:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       timeout=120, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise OperatorError(f"private_onnx_{action}_unavailable") from exc
        if completed.returncode != 0:
            _fail(f"private_onnx_{action}_failed")
        try:
            result = json.loads(completed.stdout)
        except ValueError as exc:
            raise OperatorError(f"private_onnx_{action}_result_invalid") from exc
        if action == "cache" and result.get("sha256") != control.ONNX_ARCHIVE_SHA256:
            _fail("private_onnx_cache_drift")
        if action == "warm" and (result.get("offline_embedding_ready") is not True
                                  or result.get("httpx_stream_download_attempts") != 0
                                  or result.get("dimensions") != 384):
            _fail("private_onnx_warm_invalid")
    return root


def _clone_private_model(on_created: Callable[[Path], None] | None = None) -> tuple[Path, int]:
    root = Path(tempfile.mkdtemp(prefix="uruha-p4-b-zero-"))
    root.chmod(0o700)
    if on_created is not None:
        on_created(root)
    models = root / "models"
    manifest_rel = Path("manifests/registry.ollama.ai/library/qwen2.5/7b")
    for relative in ("models", "models/blobs", "models/manifests",
                     "models/manifests/registry.ollama.ai",
                     "models/manifests/registry.ollama.ai/library",
                     "models/manifests/registry.ollama.ai/library/qwen2.5"):
        _private_directory(root / relative)
    targets = [manifest_rel, *(Path("blobs") / f"sha256-{sha}"
                               for sha in probe.FROZEN_BLOBS)]
    for relative in targets:
        source, target = SHARED_MODELS / relative, models / relative
        if source.is_symlink() or not source.is_file() or target.exists() or target.is_symlink():
            _fail("shared_model_source_or_target_invalid")
        try:
            subprocess.run(["/bin/cp", "-c", str(source), str(target)],
                           capture_output=True, timeout=120, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise OperatorError("cow_clone_failed") from exc
        target.chmod(0o600)
    probe._model_store(root, SHARED_MODELS, probe.FROZEN_MODEL)
    logical_bytes = sum((models / relative).stat().st_size for relative in targets)
    return root, logical_bytes


def _daemon_environment(private_root: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.lower().endswith("_proxy") and not key.upper().startswith("OLLAMA_")}
    env.update({
        "HOME": str(private_root), "TMPDIR": str(private_root),
        "OLLAMA_HOST": f"127.0.0.1:{DAEMON_PORT}",
        "OLLAMA_MODELS": str(private_root / "models"),
        "OLLAMA_NO_CLOUD": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_QUEUE": "0",
    })
    return env


def _launch_daemon(private_root: Path) -> subprocess.Popen:
    stdout = private_root / "ollama.stdout.log"
    stderr = private_root / "ollama.stderr.log"
    out_fd = os.open(stdout, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        err_fd = os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except BaseException:
        os.close(out_fd)
        raise
    try:
        with os.fdopen(out_fd, "wb") as out, os.fdopen(err_fd, "wb") as err:
            return subprocess.Popen(
                [str(DAEMON_BINARY), "serve"], cwd=ROOT,
                env=_daemon_environment(private_root), stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, close_fds=True, start_new_session=True,
                umask=0o077,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OperatorError("private_daemon_start_failed") from exc


def _wait_daemon(pid: int, counts: dict[str, object]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if _listener_pids(DAEMON_PORT) == frozenset({pid}):
            counts["daemon_ready_version_http_count"] = 1
            try:
                version = probe._http_json(f"http://127.0.0.1:{DAEMON_PORT}/api/version")
            except probe.ProbeError as exc:
                raise OperatorError("private_daemon_version_unavailable") from exc
            if version.get("version") != probe.VERSION:
                _fail("private_daemon_version_drift")
            return
        time.sleep(0.25)
    _fail("private_daemon_not_ready")


def _owned_runner_snapshots(
    daemon_pid: int, private_root: Path,
) -> tuple[list[tuple[int, int, str, str, tuple[str, ...]]], bool]:
    """Observe exact daemon children; never return an unverified PID to cleanup."""
    try:
        result = subprocess.run(["/usr/bin/pgrep", "-P", str(daemon_pid)],
                                capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise OperatorError("private_runner_listing_unavailable") from exc
    if result.returncode == 1 and not result.stdout.strip():
        return [], False
    if result.returncode != 0:
        _fail("private_runner_listing_unavailable")
    try:
        pids = [int(row) for row in result.stdout.splitlines()]
    except ValueError as exc:
        raise OperatorError("private_runner_pid_invalid") from exc
    verified = []
    unknown = False
    for pid in pids:
        seen = _process_argv(pid)
        if seen is None:
            unknown = True
            continue
        parent, args = seen
        try:
            port = int(probe._arg_value(args, "--port") or "")
            binary_matches = Path(args[0]).resolve(strict=True) == RUNNER_BINARY.resolve(strict=True)
            model_matches = Path(probe._arg_value(args, "--model") or "").resolve(strict=True) == (
                private_root / "models/blobs" / f"sha256-{probe.GGUF_SHA256}"
            ).resolve(strict=True)
        except (OSError, ValueError, IndexError):
            port = 0
            binary_matches = model_matches = False
        if (parent != daemon_pid or not binary_matches or not model_matches
                or not (1024 <= port <= 65535)
                or port in (DAEMON_PORT, PRODUCT_PORT, 11434)
                or probe._arg_value(args, "--host") != "127.0.0.1"
                or probe._arg_value(args, "--chat-template") != "chatml"
                or "--offline" not in args or "--no-jinja" not in args):
            unknown = True
            continue
        daemon_start, runner_start = _generation(daemon_pid), _generation(pid)
        if daemon_start is None or runner_start is None:
            unknown = True
            continue
        verified.append((pid, port, daemon_start, runner_start, tuple(args)))
    return verified, unknown


def _load_runner_and_identify(
    daemon_pid: int, private_root: Path, counts: dict[str, object],
    on_identified: Callable[[int, int, str, tuple[str, ...]], None] | None = None,
) -> tuple[int, int, str, str, tuple[str, ...]]:
    counts["operator_diagnostic_http_count"] = int(
        counts.get("operator_diagnostic_http_count", 0)) + 1
    response = None
    response_error = None
    try:
        response = probe._http_json(
            f"http://127.0.0.1:{DAEMON_PORT}/v1/chat/completions", probe._fixed_request(),
        )
    except probe.ProbeError:
        response_error = "render_only_http_failed"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        found, unknown = _owned_runner_snapshots(daemon_pid, private_root)
        if len(found) > 1 or unknown:
            _fail("multiple_private_runners")
        if len(found) == 1:
            runner_pid, port, daemon_start, runner_start, argv = found[0]
            if on_identified is not None:
                on_identified(runner_pid, port, runner_start, argv)
            if _listener_pids(port) == frozenset({runner_pid}):
                if response_error is not None:
                    _fail(response_error)
                try:
                    usage = response["usage"]
                    if (response.get("model") != probe.MODEL
                            or response["choices"][0]["message"]["content"] != ""
                            or {key: usage.get(key) for key in (
                                "prompt_tokens", "completion_tokens", "total_tokens",
                            )} != {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                            or not isinstance(response["_debug_info"]["rendered_template"], str)
                            or f"User Input: {probe.FIXTURE}" not in response["_debug_info"]["rendered_template"]):
                        _fail("render_only_not_zero_completion")
                except (KeyError, IndexError, TypeError) as exc:
                    raise OperatorError("render_only_response_invalid") from exc
                return found[0]
        time.sleep(0.25)
    _fail(response_error or "private_runner_not_ready")


def _write_descriptor(private_root: Path, runner_pid: int, runner_port: int,
                      daemon_pid: int, daemon_start: str, runner_start: str) -> Path:
    value = {
        "schema": "p4_b_private_endpoint_descriptor_v1",
        "private_root": str(private_root), "shared_models": str(SHARED_MODELS),
        "daemon_pid": daemon_pid, "runner_pid": runner_pid,
        "daemon_port": DAEMON_PORT, "runner_port": runner_port,
        "daemon_process_start": daemon_start, "runner_process_start": runner_start,
        "daemon_binary": str(DAEMON_BINARY), "runner_binary": str(RUNNER_BINARY),
    }
    if set(value) != DESCRIPTOR_FIELDS:
        _fail("private_descriptor_shape_invalid")
    path = private_root / control.B_DESCRIPTOR_NAME
    _private_file(path, (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return path


def _sample_pid(pid: int) -> dict | None:
    try:
        completed = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "%cpu=", "-o", "rss=", "-o", "time="],
            capture_output=True, text=True, timeout=3, check=False,
        )
        fields = completed.stdout.strip().split()
        if completed.returncode != 0 or len(fields) != 3:
            return None
        return {"cpu_percent_sample": float(fields[0]), "rss_kib_sample": int(fields[1]),
                "cpu_time_sample": fields[2]}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class _ProcessSampler:
    """Best-effort 250 ms generation-bound samples, not absolute peaks."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._pids: dict[str, tuple[int, str | None]] = {"operator": (os.getpid(), None)}
        self._observed: dict[str, dict] = {}
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def add(self, label: str, pid: int, generation: str | None) -> None:
        with self._lock:
            self._pids[label] = (pid, generation)

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                targets = dict(self._pids)
            for label, (pid, generation) in targets.items():
                if generation is not None and _generation(pid) != generation:
                    continue
                sample = _sample_pid(pid)
                if sample is None:
                    continue
                with self._lock:
                    row = self._observed.setdefault(label, {
                        "pid": pid, "sample_count": 0,
                        "max_observed_rss_kib": 0,
                        "max_observed_cpu_percent": 0.0,
                        "last_observed_cpu_time": None,
                    })
                    row["sample_count"] += 1
                    row["max_observed_rss_kib"] = max(
                        row["max_observed_rss_kib"], sample["rss_kib_sample"])
                    row["max_observed_cpu_percent"] = max(
                        row["max_observed_cpu_percent"], sample["cpu_percent_sample"])
                    row["last_observed_cpu_time"] = sample["cpu_time_sample"]
            self._stop.wait(0.25)

    def close(self) -> dict[str, dict]:
        self._stop.set()
        self._thread.join(timeout=5)
        with self._lock:
            return {label: dict(row) for label, row in self._observed.items()}


def _result_file(private_root: Path, result: dict) -> Path:
    path = private_root / RESULT_NAME
    _private_file(path, (json.dumps(result, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")) + "\n").encode())
    return path


def run_once() -> dict:
    started = time.monotonic()
    sampler = _ProcessSampler()
    sampler.start()
    phases: dict[str, float] = {}
    state: dict[str, object] = {
        "schema": "p4_b_private_zero_turn_operator_result_v1",
        "status": "fail_closed", "b_send_authorized": False,
        "helper_intended_generated_completions": 0,
        "global_provider_completion_count_proven": False,
        "operator_diagnostic_http_count": 0,
        "operator_diagnostic_http_count_basis": "1 render-only load + 5 identity probe; one daemon-ready version GET separately",
        "safari_sends": 0, "formal_db_writes": 0,
        "time_caps_hard_enforced": False,
        "rss_cpu_peak_scope": "250ms generation-bound observed samples, not absolute peak",
        "full_cost_instrumented": False,
        "copy_on_write_allocation_proven": False,
        "brain_constructor_observed": False,
        "sdk_models_list_observed": False,
        "provider_network_completion_count_proven": False,
    }
    private_root: Path | None = None
    product_root: Path | None = None
    daemon_proc: subprocess.Popen | None = None
    daemon_start: str | None = None
    runner_pid: int | None = None
    runner_start: str | None = None
    runner_argv: tuple[str, ...] | None = None
    logical_bytes = 0
    child_started = False
    child_stop: dict | None = None
    error: str | None = None
    try:
        preflight = _static_preflight()
        state.update(preflight)
        phases["static_preflight_s"] = time.monotonic() - started
        product_root = _prepare_product_root(
            lambda path: state.__setitem__("product_runtime_root", str(path)))
        state["product_runtime_root"] = str(product_root)
        phases["prepared_warm_s"] = time.monotonic() - started
        state["free_bytes_before_clone"] = _available_bytes()
        if state["free_bytes_before_clone"] < MIN_FREE_BYTES:
            _fail("insufficient_private_disk_before_clone")
        private_root, logical_bytes = _clone_private_model(
            lambda path: state.__setitem__("private_model_root", str(path)))
        state["private_model_root"] = str(private_root)
        state["clone_logical_bytes"] = logical_bytes
        state["helper_model_store_validations"] = 1
        phases["clone_verified_s"] = time.monotonic() - started
        state["free_bytes_after_clone"] = _available_bytes()
        if (state["free_bytes_before_clone"] - state["free_bytes_after_clone"] > MAX_CLONE_DISK_DELTA
                or state["free_bytes_after_clone"] < MIN_FREE_BYTES):
            _fail("private_clone_disk_budget_exceeded")
        if _listener_pids(DAEMON_PORT) or _listener_pids(PRODUCT_PORT):
            _fail("private_or_product_port_occupied_before_daemon")
        daemon_proc = _launch_daemon(private_root)
        daemon_start = _generation(daemon_proc.pid)
        if daemon_start is None or not _same_process(daemon_proc.pid, daemon_start,
                                                      DAEMON_BINARY, daemon=True):
            _fail("private_daemon_identity_unavailable")
        sampler.add("daemon", daemon_proc.pid, daemon_start)
        _wait_daemon(daemon_proc.pid, state)
        def capture_runner(pid: int, port: int, generation: str, argv: tuple[str, ...]) -> None:
            nonlocal runner_pid, runner_start, runner_argv
            runner_pid, runner_start, runner_argv = pid, generation, argv
            state["runner_port"] = port
            sampler.add("runner", pid, generation)

        runner_pid, runner_port, daemon_start_seen, runner_start, runner_argv = _load_runner_and_identify(
            daemon_proc.pid, private_root, state, capture_runner)
        if daemon_start_seen != daemon_start:
            _fail("private_daemon_generation_drift")
        phases["runner_loaded_s"] = time.monotonic() - started
        original_http = probe._http_json
        original_store = probe._model_store
        probe_calls = 0
        probe_store_checks = 0

        def counted_http(*args, **kwargs):
            nonlocal probe_calls
            probe_calls += 1
            return original_http(*args, **kwargs)

        def counted_store(*args, **kwargs):
            nonlocal probe_store_checks
            probe_store_checks += 1
            return original_store(*args, **kwargs)

        probe._http_json = counted_http
        probe._model_store = counted_store
        try:
            identity_report = probe.probe(
                private_root=private_root, shared_models=SHARED_MODELS,
                daemon_pid=daemon_proc.pid, runner_pid=runner_pid,
                daemon_port=DAEMON_PORT, runner_port=runner_port,
                daemon_binary=DAEMON_BINARY, runner_binary=RUNNER_BINARY,
            )
        finally:
            probe._http_json = original_http
            probe._model_store = original_store
            state["operator_diagnostic_http_count"] += probe_calls
            state["helper_model_store_validations"] += probe_store_checks
        if probe_calls != 5 or identity_report["diagnostic_http_calls"] != 5:
            _fail("private_probe_diagnostic_count_drift")
        state["probe_result_sha256"] = hashlib.sha256(json.dumps(
            identity_report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        descriptor = _write_descriptor(private_root, runner_pid, runner_port,
                                       daemon_proc.pid, daemon_start, runner_start)
        state.update({"daemon_pid": daemon_proc.pid, "runner_pid": runner_pid,
                      "runner_port": runner_port, "daemon_port": DAEMON_PORT,
                      "descriptor_sha256": _sha256(descriptor),
                      "daemon_sample_before_child": _sample_pid(daemon_proc.pid),
                      "runner_sample_before_child": _sample_pid(runner_pid)})
        phases["descriptor_ready_s"] = time.monotonic() - started
        child_started_at = time.monotonic()
        child = control.start(
            mode="product", python=str(PYTHON), prepared_runtime_root=str(product_root),
            p4_b_private=True, p4_b_private_descriptor=str(descriptor),
        )
        child_started = True
        state["child_run_id"] = child["run_id"]
        state["child_pid"] = child["pid"]
        child_generation = child.get("start_identity", {}).get("lstart")
        if type(child_generation) is not str or not child_generation:
            _fail("child_start_generation_missing")
        sampler.add("child", child["pid"], child_generation)
        phases["child_start_s"] = time.monotonic() - child_started_at
        if time.monotonic() - child_started_at > MAX_CHILD_READY_S:
            _fail("child_ready_observed_deadline_exceeded")
        ready: dict | None = None
        while time.monotonic() - child_started_at <= MAX_CHILD_READY_S:
            try:
                ready = control.verify_ready(str(product_root))
                break
            except control.ControllerError as exc:
                if str(exc) not in ("product_not_final_python", "product_listener_not_same_pid",
                                    "product_http_not_ready:ConnectionRefusedError"):
                    raise
                time.sleep(0.5)
        if ready is None or ready.get("ready") is not True or ready.get("pid") != child["pid"]:
            _fail("child_not_same_pid_ready")
        if time.monotonic() - child_started_at > MAX_CHILD_READY_S:
            _fail("child_ready_observed_deadline_exceeded")
        phases["child_ready_s"] = time.monotonic() - child_started_at
        state["child_bootstrap_http_ready"] = True
        state["child_sample_at_ready"] = _sample_pid(child["pid"])
        state["daemon_sample_at_ready"] = _sample_pid(daemon_proc.pid)
        state["runner_sample_at_ready"] = _sample_pid(runner_pid)
        child_stop = control.stop(str(product_root))
        child_started = False
        state["child_stop"] = {key: child_stop.get(key) for key in (
            "ok", "planned_stop", "original_pid_exited", "port_vacant",
        )}
        if (child_stop.get("ok") is not True or child_stop.get("planned_stop") is not True
                or child_stop.get("original_pid_exited") is not True
                or child_stop.get("port_vacant") is not True):
            if child_stop.get("original_pid_exited") is not True:
                state["child_cleanup"] = "stop_did_not_prove_pid_exit_review_required"
            _fail("child_exact_planned_stop_failed")
        phases["child_stopped_s"] = time.monotonic() - started
        state["status"] = "real_zero_turn_identity_pass_pending_private_cleanup"
    except Exception as exc:
        error = str(exc) if isinstance(exc, OperatorError) else type(exc).__name__
    finally:
        if private_root is None and isinstance(state.get("private_model_root"), str):
            private_root = Path(state["private_model_root"])
        if product_root is None and isinstance(state.get("product_runtime_root"), str):
            product_root = Path(state["product_runtime_root"])
        if child_started and product_root is not None:
            try:
                child_stop = control.stop(str(product_root))
                state["child_stop_after_failure"] = {key: child_stop.get(key) for key in (
                    "ok", "planned_stop", "original_pid_exited", "port_vacant",
                )}
                if (child_stop.get("original_pid_exited") is not True
                        or child_stop.get("port_vacant") is not True):
                    state["child_cleanup"] = "stop_did_not_prove_pid_exit_review_required"
            except Exception:
                state["child_cleanup"] = "unverified_review_required"
        if daemon_proc is not None:
            if runner_pid is not None and runner_start is not None:
                state["runner_cleanup"] = _stop_exact(
                    runner_pid, runner_start, RUNNER_BINARY, daemon=False,
                    expected_parent=daemon_proc.pid, expected_argv=runner_argv,
                )
            else:
                try:
                    recovered, unknown_child = _owned_runner_snapshots(daemon_proc.pid, private_root)
                except Exception:
                    recovered, unknown_child = [], True
                recovered_results = []
                for pid, port, seen_daemon_start, seen_runner_start, seen_argv in recovered:
                    if daemon_start is None or seen_daemon_start != daemon_start:
                        unknown_child = True
                        continue
                    recovered_results.append({
                        "pid": pid, "port": port,
                        "cleanup": _stop_exact(
                            pid, seen_runner_start, RUNNER_BINARY, daemon=False,
                            expected_parent=daemon_proc.pid, expected_argv=seen_argv,
                        ),
                    })
                state["recovered_runner_cleanup"] = recovered_results
                state["unknown_daemon_child_at_cleanup"] = unknown_child
                state["runner_cleanup"] = "identity_not_captured_review_required"
            if daemon_start is not None:
                state["daemon_cleanup"] = _stop_exact(
                    daemon_proc.pid, daemon_start, DAEMON_BINARY, daemon=True,
                )
            elif daemon_proc.poll() is None:
                # An unreaped direct Popen child cannot have its PID reused.
                # This fallback only covers the interval before ps lstart was
                # captured; it never signals an arbitrary discovered process.
                try:
                    daemon_proc.terminate()
                    daemon_proc.wait(timeout=5)
                    state["daemon_cleanup"] = "owned_popen_terminated_without_generation"
                except subprocess.TimeoutExpired:
                    if daemon_proc.poll() is None:
                        daemon_proc.kill()
                        daemon_proc.wait(timeout=5)
                        state["daemon_cleanup"] = "owned_popen_killed_without_generation"
                except Exception:
                    state["daemon_cleanup"] = "owned_popen_cleanup_unverified_review_required"
            try:
                daemon_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        state["process_samples"] = sampler.close()
        state["wall_s"] = time.monotonic() - started
        state["phase_elapsed_s"] = phases
        if logical_bytes and isinstance(state.get("helper_model_store_validations"), int):
            state["helper_model_store_logical_read_lower_bound_bytes"] = (
                state["helper_model_store_validations"] * logical_bytes)
        state["controller_and_web_model_store_validations"] = "not_instrumented"
        try:
            state["free_bytes_after"] = _available_bytes()
        except Exception:
            state["free_bytes_after"] = None
        state["operator_cpu_user_s"] = resource.getrusage(resource.RUSAGE_SELF).ru_utime
        state["operator_cpu_system_s"] = resource.getrusage(resource.RUSAGE_SELF).ru_stime
        state["operator_max_rss_raw"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        state["direct_child_cpu_user_s"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
        state["direct_child_cpu_system_s"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime
        state["direct_child_max_rss_raw"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        try:
            state["private_listener_vacant"] = not _listener_pids(DAEMON_PORT)
            state["product_listener_vacant"] = not _listener_pids(PRODUCT_PORT)
            state["shared_listener_unchanged"] = bool(
                state.get("shared_listener_pids") == sorted(_listener_pids(11434))
                and all(_generation(int(pid)) == generation for pid, generation in
                        state.get("shared_process_generations", {}).items())
            )
            if runner_pid is not None and state.get("runner_port") is not None:
                state["runner_listener_vacant"] = not _listener_pids(int(state["runner_port"]))
            if state.get("recovered_runner_cleanup"):
                state["recovered_runner_listeners_vacant"] = all(
                    not _listener_pids(int(row["port"]))
                    for row in state["recovered_runner_cleanup"])
        except Exception:
            state["listener_final_inspection"] = "unavailable_review_required"
        if state["wall_s"] > MAX_DAEMON_WALL_S:
            error = error or "daemon_observed_deadline_exceeded"
        if state["status"] == "real_zero_turn_identity_pass_pending_private_cleanup":
            if (state.get("runner_cleanup") not in ("terminated", "killed_exact", "already_absent")
                    or state.get("daemon_cleanup") not in ("terminated", "killed_exact", "already_absent")
                    or state.get("private_listener_vacant") is not True
                    or state.get("product_listener_vacant") is not True
                    or state.get("runner_listener_vacant") is not True
                    or state.get("shared_listener_unchanged") is not True
                    or error):
                state["status"] = "fail_closed"
            else:
                state["status"] = "real_zero_turn_identity_pass"
        if error:
            state["failure_reason"] = error
        if (state.get("child_cleanup") in (
                    "unverified_review_required", "stop_did_not_prove_pid_exit_review_required")
                or state.get("daemon_cleanup") in (
                    "identity_drift_no_signal", "identity_drift_no_kill",
                    "still_alive", "owned_popen_cleanup_unverified_review_required",
                    "exact_term_failed_review_required", "exact_kill_failed_review_required")
                or state.get("runner_cleanup") in (
                    "identity_drift_no_signal", "identity_drift_no_kill", "still_alive",
                    "identity_not_captured_review_required", "exact_term_failed_review_required",
                    "exact_kill_failed_review_required")
                or state.get("unknown_daemon_child_at_cleanup") is True
                or state.get("recovered_runner_listeners_vacant") is False
                or state.get("listener_final_inspection") == "unavailable_review_required"):
            state["cleanup_review_required"] = True
        samples = state.get("process_samples", {})
        state["resource_sampling_complete"] = bool(
            all(samples.get(label, {}).get("sample_count", 0) > 0
                for label in ("operator", "daemon", "runner", "child")))
        if (state["status"] == "real_zero_turn_identity_pass"
                and not state["resource_sampling_complete"]):
            state["status"] = "fail_closed"
            state["failure_reason"] = "resource_sampling_incomplete"
        if private_root is not None:
            try:
                state["result_file"] = str(_result_file(private_root, state))
            except Exception:
                state["result_persistence"] = "failed_review_required"
                state["status"] = "fail_closed"
                state["failure_reason"] = "result_persistence_failed"
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Run exactly one non-B private zero-turn; never send a chat turn")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"ok": False, "reason": "explicit_execute_required",
                          "b_send_authorized": False}))
        return 2
    result = run_once()
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") == "real_zero_turn_identity_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
