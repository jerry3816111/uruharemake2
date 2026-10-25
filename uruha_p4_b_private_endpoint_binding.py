"""Read-only, opt-in private Ollama identity check for the P4 B constructor.

This is a cooperative same-user identity check, not a capability issuer, a
pre-send token bound, a provider-call interceptor, or B Send authorization.
The controller/child and pre-create revalidation are separate future gates.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import Mapping, Sequence

from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256,
    FROZEN_MANIFEST_SHA256,
    FROZEN_MODEL,
    FROZEN_RUNNER_SHA256,
    GGUF_SHA256,
    SYSTEM_SHA256,
    TEMPLATE_SHA256,
    ProbeError,
    _model_store,
    _regular_single_link,
    _sha256_file as _model_sha256_file,
)
import uruha_p4_b_child_local_identity as child_identity
from uruha_compute_ledger import ComputeLedger
from uruha_p4_b_resource_gate import P4BResourceGate


_HEX = re.compile(r"[0-9a-f]{64}\Z")
_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
_RECEIPT_NAME = "p4_b_private_endpoint_launch_receipt.json"
_RECEIPT_SCHEMA = "p4_b_private_endpoint_launch_receipt_v4"
_RECEIPT_FIELDS = frozenset({
    "schema", "issuer", "run_id", "private_root", "models_path", "base_url",
    "shared_models", "runtime_root", "launch_env_sha256",
    "entrypoint_sha256", "bootstrap_sha256", "binding_source_sha256",
    "controller_source_sha256",
    "web_source_sha256", "ledger_source_sha256",
    "expected_final_argv_sha256", "expected_os_final_argv",
    "expected_inprocess_python_argv_sha256",
    "daemon_pid", "runner_pid", "daemon_port", "runner_port",
    "daemon_process_start", "runner_process_start", "ollama_models",
    "daemon_raw_generation", "runner_raw_generation",
    "daemon_argv_sha256", "runner_argv_sha256", "operator_source_sha256",
    "launcher_source_sha256", "sandbox_source_sha256",
    "lifecycle_source_sha256", "launchd_source_sha256",
    "private_evidence_source_sha256",
    "compact_planner_source_sha256",
    "identity_probe_source_sha256", "resource_gate_source_sha256",
    "child_observer_source_sha256",
    "ollama_no_cloud", "daemon_binary", "runner_binary",
    "daemon_binary_sha256", "runner_binary_sha256", "manifest_sha256",
    "gguf_sha256", "template_sha256", "system_sha256",
    "issued_at_epoch", "expires_at_epoch",
})
_B_ENV_KEYS = (
    "URUHA_P4_B_PRIVATE_CHILD", "URUHA_P4_B_RUN_ID", "URUHA_P4_B_MODEL_ROOT",
    "URUHA_P4_B_RECEIPT", "URUHA_WEB_COMPUTE_LEDGER",
    "URUHA_P4_COMPACT_JSON_SCHEMA", "OLLAMA_NO_CLOUD", "HOME", "TMPDIR",
    "URUHA_MEMORY_DB_PATH", "URUHA_WEB_SESSION_DB_PATH",
    "URUHA_WEB_LOG_JSONL_PATH", "URUHA_WEB_LOG_TXT_PATH",
    "URUHA_WEB_HOST", "URUHA_WEB_PORT",
)
_ENTRYPOINT_NAME = "uruha_web_ui_product_p4_preference_fallback.py"
_BOOTSTRAP_NAME = "uruha_p4_b_private_child_bootstrap.py"


class PrivateEndpointBindingError(RuntimeError):
    """Fixed reason only; never include process environment or response text."""


@dataclass(frozen=True)
class PrivateEndpointBinding:
    run_id: str
    private_root: Path
    shared_models: Path
    receipt_path: Path
    receipt_sha256: str
    base_url: str
    daemon_pid: int
    runner_pid: int
    daemon_port: int
    runner_port: int
    daemon_process_start: str
    runner_process_start: str
    daemon_raw_generation: tuple[int, int, int, int]
    runner_raw_generation: tuple[int, int, int, int]
    daemon_argv_sha256: str
    runner_argv_sha256: str
    operator_source_sha256: str
    daemon_binary: Path
    runner_binary: Path


@dataclass(frozen=True)
class PrivateEndpointTarget:
    base_url: str
    native_url: str


def _fail(reason: str) -> None:
    raise PrivateEndpointBindingError(reason)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or path.resolve(strict=True) != path):
            _fail("private_child_source_not_regular")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        _fail("private_child_source_unavailable")


def canonical_b_env_digest(environ: Mapping[str, str]) -> str:
    """Hash only the frozen B and isolation keys; refuse ambient proxy overrides."""
    if not isinstance(environ, Mapping):
        _fail("private_child_environment_invalid")
    if any(type(key) is not str or key.lower().endswith("_proxy")
           for key in environ):
        _fail("private_child_proxy_or_environment_invalid")
    if any(key.upper().startswith("URUHA_P4_B_") and key not in _B_ENV_KEYS
           for key in environ):
        _fail("private_child_unknown_b_environment_key")
    frozen = {}
    for key in _B_ENV_KEYS:
        value = environ.get(key)
        if type(value) is not str or not value:
            _fail("private_child_environment_incomplete")
        frozen[key] = value
    if (frozen["URUHA_P4_B_PRIVATE_CHILD"] != "1"
            or frozen["URUHA_WEB_COMPUTE_LEDGER"] != "1"
            or frozen["URUHA_P4_COMPACT_JSON_SCHEMA"] != "1"
            or frozen["OLLAMA_NO_CLOUD"] != "1"):
        _fail("private_child_environment_invalid")
    return _sha256_json(frozen)


def private_child_source_digests(entrypoint: Path) -> dict[str, str]:
    root = Path(__file__).resolve().parent
    if not isinstance(entrypoint, Path) or entrypoint != root / _ENTRYPOINT_NAME:
        _fail("private_child_entrypoint_invalid")
    return {
        "entrypoint_sha256": _sha256_file(entrypoint),
        "bootstrap_sha256": _sha256_file(root / _BOOTSTRAP_NAME),
        "binding_source_sha256": _sha256_file(root / Path(__file__).name),
        "controller_source_sha256": _sha256_file(
            root / "p4_preference_fallback_detached_control.py"),
        "web_source_sha256": _sha256_file(root / "uruha_web_ui.py"),
        "ledger_source_sha256": _sha256_file(root / "uruha_compute_ledger.py"),
        "operator_source_sha256": _sha256_file(root / "p4_b_private_zero_turn_operator.py"),
        "private_evidence_source_sha256": _sha256_file(
            root / "p4_stateful_private_evidence.py"),
        "compact_planner_source_sha256": _sha256_file(
            root / "uruha_compact_planner_p2.py"),
        "launcher_source_sha256": _sha256_file(root / "p4_b_safe_isolated_product_launcher.py"),
        "sandbox_source_sha256": _sha256_file(root / "p4_b_safe_isolated_product_launcher_v2.py"),
        "lifecycle_source_sha256": _sha256_file(root / "p4_exec_detached_lifecycle_probe.py"),
        "launchd_source_sha256": _sha256_file(root / "p4_preference_fallback_launchd_control.py"),
        "identity_probe_source_sha256": _sha256_file(root / "p4_b_isolated_ollama_identity_probe.py"),
        "resource_gate_source_sha256": _sha256_file(root / "uruha_p4_b_resource_gate.py"),
        "child_observer_source_sha256": _sha256_file(root / "uruha_p4_b_child_local_identity.py"),
    }


def _final_argv_digest(argv: Sequence[str]) -> str:
    if (type(argv) not in (list, tuple) or len(argv) != 2
            or any(type(part) is not str or not part for part in argv)):
        _fail("private_child_final_argv_invalid")
    try:
        canonical = [str(Path(part).resolve(strict=True)) for part in argv]
    except (OSError, ValueError):
        _fail("private_child_final_argv_invalid")
    if canonical[1] != str(Path(__file__).resolve().with_name(_ENTRYPOINT_NAME)):
        _fail("private_child_final_argv_invalid")
    return _sha256_json(canonical)


def _exact_os_final_argv(argv: object) -> list[str]:
    """Validate the unambiguous two-path representation of macOS ps' flat command."""
    if type(argv) is not list or len(argv) != 2 or any(type(part) is not str
            or not part or not Path(part).is_absolute()
            or any(character.isspace() for character in part) for part in argv):
        _fail("private_child_os_argv_invalid")
    try:
        if (any(Path(part).resolve(strict=True) != Path(part) for part in argv)
                or not Path(argv[0]).is_file()
                or not os.access(argv[0], os.X_OK)
                or argv[1] != str(Path(__file__).resolve().with_name(_ENTRYPOINT_NAME))):
            _fail("private_child_os_argv_invalid")
    except (OSError, ValueError):
        _fail("private_child_os_argv_invalid")
    return argv


def _exact_private_directory(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError:
        _fail("private_root_unavailable")
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
            or path.resolve(strict=True) != path):
        _fail("private_root_not_canonical_or_private")


def _receipt(binding: PrivateEndpointBinding) -> dict:
    path = binding.receipt_path
    if path != binding.private_root / _RECEIPT_NAME:
        _fail("receipt_path_mismatch")
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            _fail("receipt_not_private_regular_file")
        raw = path.read_bytes()
    except OSError:
        _fail("receipt_unavailable")
    if len(raw) > 8192 or hashlib.sha256(raw).hexdigest() != binding.receipt_sha256:
        _fail("receipt_digest_drift")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        _fail("receipt_shape_invalid")
    if not isinstance(value, dict) or set(value) != _RECEIPT_FIELDS:
        _fail("receipt_shape_invalid")
    return value


def _one_arg(args: tuple[str, ...], flag: str) -> str:
    if args.count(flag) != 1:
        _fail("private_runner_flag_drift")
    index = args.index(flag)
    if index + 1 >= len(args) or args[index + 1].startswith("--"):
        _fail("private_runner_flag_drift")
    return args[index + 1]


def _same_binary_observation(observed: child_identity.ProcessSnapshot, binary: Path) -> bool:
    if not observed.argv:
        return False
    try:
        canonical = binary.resolve(strict=True)
        return (Path(observed.executable).resolve(strict=True) == canonical
                and Path(observed.argv[0]).resolve(strict=True) == canonical)
    except (OSError, ValueError):
        return False


def _live_os_identity(binding: PrivateEndpointBinding, model_blob: Path) -> None:
    daemon = child_identity.observe_process(binding.daemon_pid, {
        "OLLAMA_MODELS": str(binding.private_root / "models"),
        "OLLAMA_NO_CLOUD": "1",
    })
    runner = child_identity.observe_process(binding.runner_pid)
    if (tuple((daemon.pid, daemon.ppid, daemon.start_sec, daemon.start_usec))
            != binding.daemon_raw_generation
            or tuple((runner.pid, runner.ppid, runner.start_sec, runner.start_usec))
            != binding.runner_raw_generation
            or runner.ppid != daemon.pid
            or child_identity.argv_digest(daemon) != binding.daemon_argv_sha256
            or child_identity.argv_digest(runner) != binding.runner_argv_sha256
            or not all(daemon.env_exact.get(key) is True for key in (
                "OLLAMA_MODELS", "OLLAMA_NO_CLOUD"))
            or not _same_binary_observation(daemon, binding.daemon_binary)
            or not _same_binary_observation(runner, binding.runner_binary)
            or daemon.argv[1:2] != ("serve",)
            or _one_arg(runner.argv, "--host") != "127.0.0.1"
            or _one_arg(runner.argv, "--port") != str(binding.runner_port)
            or _one_arg(runner.argv, "--chat-template") != "chatml"
            or runner.argv.count("--offline") != 1
            or runner.argv.count("--no-jinja") != 1
            or not child_identity.owns_loopback_listener(binding.daemon_pid, binding.daemon_port)
            or not child_identity.owns_loopback_listener(binding.runner_pid, binding.runner_port)):
        _fail("private_ollama_identity_drift")
    try:
        if Path(_one_arg(runner.argv, "--model")).resolve(strict=True) != model_blob.resolve(strict=True):
            _fail("private_ollama_identity_drift")
        _regular_single_link(binding.daemon_binary, code="daemon_binary_invalid")
        _regular_single_link(binding.runner_binary, code="runner_binary_invalid")
        if (_model_sha256_file(binding.daemon_binary) != FROZEN_DAEMON_SHA256
                or _model_sha256_file(binding.runner_binary) != FROZEN_RUNNER_SHA256):
            _fail("private_ollama_identity_drift")
    except (OSError, ProbeError, ValueError):
        _fail("private_ollama_identity_drift")


def _inspect_live_identity(binding: PrivateEndpointBinding) -> None:
    """B-only child-local process/file/listener check; no provider request."""
    expected = (binding.daemon_raw_generation, binding.runner_raw_generation)
    try:
        if (child_identity.raw_generation(binding.daemon_pid),
                child_identity.raw_generation(binding.runner_pid)) != expected:
            _fail("process_generation_drift")
        models, before = _model_store(
            binding.private_root, binding.shared_models, FROZEN_MODEL,
        )
        _live_os_identity(
            binding, models / "blobs" / f"sha256-{GGUF_SHA256}",
        )
        if _model_store(binding.private_root, binding.shared_models, FROZEN_MODEL)[1] != before:
            _fail("private_model_store_changed_during_inspection")
        if (child_identity.raw_generation(binding.daemon_pid),
                child_identity.raw_generation(binding.runner_pid)) != expected:
            _fail("process_generation_drift")
    except (child_identity.ProbeError, ProbeError):
        _fail("private_ollama_identity_drift")


def _binding_shape(binding: PrivateEndpointBinding, *, require_digest: bool) -> str:
    if type(binding) is not PrivateEndpointBinding:
        _fail("binding_missing_or_wrong_type")
    if type(binding.run_id) is not str or not _RUN.fullmatch(binding.run_id):
        _fail("run_id_mismatch")
    if (not isinstance(binding.private_root, Path)
            or not isinstance(binding.shared_models, Path)
            or not isinstance(binding.receipt_path, Path)
            or not isinstance(binding.daemon_binary, Path)
            or not isinstance(binding.runner_binary, Path)):
        _fail("binding_path_shape_invalid")
    _exact_private_directory(binding.private_root)
    if binding.receipt_path != binding.private_root / _RECEIPT_NAME:
        _fail("receipt_path_mismatch")
    if (require_digest and (type(binding.receipt_sha256) is not str
                            or not _HEX.fullmatch(binding.receipt_sha256))):
        _fail("receipt_digest_invalid")
    if (type(binding.daemon_pid) is not int or type(binding.runner_pid) is not int
            or binding.daemon_pid <= 0 or binding.runner_pid <= 0
            or binding.daemon_pid == binding.runner_pid
            or type(binding.daemon_port) is not int or type(binding.runner_port) is not int
            or not (1024 <= binding.daemon_port <= 65535)
            or not (1024 <= binding.runner_port <= 65535)
            or len({binding.daemon_port, binding.runner_port, 11434}) != 3):
        _fail("private_endpoint_invalid")
    expected_base = f"http://127.0.0.1:{binding.daemon_port}/v1"
    if type(binding.base_url) is not str or binding.base_url != expected_base:
        _fail("private_endpoint_url_invalid")
    if (type(binding.daemon_process_start) is not str
            or type(binding.runner_process_start) is not str
            or not binding.daemon_process_start or not binding.runner_process_start):
        _fail("process_generation_missing")
    for generation, pid in ((binding.daemon_raw_generation, binding.daemon_pid),
                            (binding.runner_raw_generation, binding.runner_pid)):
        if (type(generation) is not tuple or len(generation) != 4
                or any(type(value) is not int for value in generation)
                or generation[0] != pid or generation[1] <= 0
                or generation[2] <= 0 or not (0 <= generation[3] < 1_000_000)):
            _fail("process_raw_generation_invalid")
    if binding.runner_raw_generation[1] != binding.daemon_pid:
        _fail("private_runner_parent_drift")
    if any(type(value) is not str or not _HEX.fullmatch(value) for value in (
            binding.daemon_argv_sha256, binding.runner_argv_sha256,
            binding.operator_source_sha256)):
        _fail("private_identity_digest_invalid")
    if (binding.shared_models != binding.shared_models.resolve(strict=False)
            or binding.daemon_binary != binding.daemon_binary.resolve(strict=False)
            or binding.runner_binary != binding.runner_binary.resolve(strict=False)):
        _fail("private_identity_paths_not_canonical")
    return expected_base


def preflight_private_endpoint_identity(binding: PrivateEndpointBinding) -> None:
    """No receipt/gate/HTTP: inspect exact file/process/listener identity before child launch."""
    _binding_shape(binding, require_digest=False)
    try:
        _inspect_live_identity(binding)
    except PrivateEndpointBindingError:
        raise
    except Exception:
        _fail("private_ollama_identity_unavailable")


def _valid_receipt_time(receipt: dict) -> float:
    issued = receipt["issued_at_epoch"]
    expires = receipt["expires_at_epoch"]
    now = time.time()
    try:
        finite = math.isfinite(issued) and math.isfinite(expires)
    except (TypeError, ValueError, OverflowError):
        finite = False
    if (type(issued) not in (int, float) or type(expires) not in (int, float)
            or not finite
            or not (now - 300 <= issued <= now + 2
                    and issued < expires <= issued + 300 and now < expires)):
        _fail("receipt_expired_or_invalid")
    return expires


def issue_private_child_receipt(
    *, binding: PrivateEndpointBinding, runtime_root: Path,
    environ: Mapping[str, str], entrypoint: Path,
    expected_final_argv: Sequence[str],
    expected_inprocess_python_argv: Sequence[str],
) -> PrivateEndpointBinding:
    """Controller-only cooperative 0600 launch artifact, not B Send authorization."""
    expected_base = _binding_shape(binding, require_digest=False)
    if not isinstance(runtime_root, Path):
        _fail("runtime_root_invalid")
    _exact_private_directory(runtime_root)
    if (environ.get("URUHA_P4_B_RUN_ID") != binding.run_id
            or environ.get("URUHA_P4_B_MODEL_ROOT") != str(binding.private_root)
            or environ.get("URUHA_P4_B_RECEIPT") != str(binding.receipt_path)
            or environ.get("HOME") != str(runtime_root)
            or environ.get("TMPDIR") != str(runtime_root)):
        _fail("private_child_environment_identity_mismatch")
    if type(expected_final_argv) not in (list, tuple):
        _fail("private_child_os_argv_invalid")
    os_argv = _exact_os_final_argv(list(expected_final_argv))
    if (type(expected_inprocess_python_argv) not in (list, tuple)
            or len(expected_inprocess_python_argv) != 2
            or expected_inprocess_python_argv[1] != str(entrypoint)):
        _fail("private_child_inprocess_argv_invalid")
    inprocess_digest = _final_argv_digest(expected_inprocess_python_argv)
    now = time.time()
    source_digests = private_child_source_digests(entrypoint)
    if binding.operator_source_sha256 != source_digests["operator_source_sha256"]:
        _fail("operator_source_drift_before_receipt")
    receipt = {
        "schema": _RECEIPT_SCHEMA, "issuer": "p4_b_private_controller",
        "run_id": binding.run_id, "private_root": str(binding.private_root),
        "models_path": str(binding.private_root / "models"),
        "shared_models": str(binding.shared_models), "base_url": expected_base,
        "runtime_root": str(runtime_root),
        "launch_env_sha256": canonical_b_env_digest(environ),
        **source_digests,
        "expected_final_argv_sha256": _final_argv_digest(os_argv),
        "expected_os_final_argv": os_argv,
        "expected_inprocess_python_argv_sha256": inprocess_digest,
        "daemon_pid": binding.daemon_pid, "runner_pid": binding.runner_pid,
        "daemon_port": binding.daemon_port, "runner_port": binding.runner_port,
        "daemon_process_start": binding.daemon_process_start,
        "runner_process_start": binding.runner_process_start,
        "daemon_raw_generation": list(binding.daemon_raw_generation),
        "runner_raw_generation": list(binding.runner_raw_generation),
        "daemon_argv_sha256": binding.daemon_argv_sha256,
        "runner_argv_sha256": binding.runner_argv_sha256,
        "ollama_models": str(binding.private_root / "models"),
        "ollama_no_cloud": "1", "daemon_binary": str(binding.daemon_binary),
        "runner_binary": str(binding.runner_binary),
        "daemon_binary_sha256": FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": FROZEN_RUNNER_SHA256,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "gguf_sha256": GGUF_SHA256, "template_sha256": TEMPLATE_SHA256,
        "system_sha256": SYSTEM_SHA256,
        "issued_at_epoch": now, "expires_at_epoch": now + 300,
    }
    raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > 8192:
        _fail("receipt_too_large")
    fd = os.open(binding.receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return replace(binding, receipt_sha256=hashlib.sha256(raw).hexdigest())


def validate_private_endpoint_binding(
    binding: PrivateEndpointBinding, *, compute_ledger: ComputeLedger, run_id: str,
    require_unused_gate: bool = True,
) -> PrivateEndpointTarget:
    """Validate before constructing any OpenAI client, models.list, or DB.

    A matching receipt is a cooperative controller artifact, not a signature or
    proof that the current Web child was started by that controller. That gate
    remains required before the private target can be used by a product child.
    """
    expected_base = _binding_shape(binding, require_digest=True)
    if type(run_id) is not str or run_id != binding.run_id:
        _fail("run_id_mismatch")
    if (type(compute_ledger) is not ComputeLedger
            or type(compute_ledger.p4_b_resource_gate) is not P4BResourceGate):
        _fail("p4_b_gate_missing_or_wrong_ledger")
    gate = compute_ledger.p4_b_resource_gate
    state = gate.snapshot()
    if (require_unused_gate and (state.get("attempted_provider_calls") != 0
                                 or state.get("denied_attempt_count") != 0
                                 or state.get("terminal_reason") != ""
                                 or gate._prompt_token_upper_bound is not None)):
        _fail("p4_b_gate_not_closed_and_unused")
    receipt = _receipt(binding)
    expected = {
        "schema": _RECEIPT_SCHEMA, "issuer": "p4_b_private_controller",
        "run_id": run_id, "private_root": str(binding.private_root),
        "models_path": str(binding.private_root / "models"),
        "shared_models": str(binding.shared_models), "base_url": expected_base,
        "daemon_pid": binding.daemon_pid, "runner_pid": binding.runner_pid,
        "daemon_port": binding.daemon_port, "runner_port": binding.runner_port,
        "daemon_process_start": binding.daemon_process_start,
        "runner_process_start": binding.runner_process_start,
        "daemon_raw_generation": list(binding.daemon_raw_generation),
        "runner_raw_generation": list(binding.runner_raw_generation),
        "daemon_argv_sha256": binding.daemon_argv_sha256,
        "runner_argv_sha256": binding.runner_argv_sha256,
        "operator_source_sha256": binding.operator_source_sha256,
        "ollama_models": str(binding.private_root / "models"),
        "ollama_no_cloud": "1",
        "daemon_binary": str(binding.daemon_binary),
        "runner_binary": str(binding.runner_binary),
        "daemon_binary_sha256": FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": FROZEN_RUNNER_SHA256,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "gguf_sha256": GGUF_SHA256,
        "template_sha256": TEMPLATE_SHA256,
        "system_sha256": SYSTEM_SHA256,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        _fail("receipt_identity_mismatch")
    if (type(receipt.get("runtime_root")) is not str
            or not receipt["runtime_root"].startswith("/")
            or any(type(receipt.get(key)) is not str or not _HEX.fullmatch(receipt[key])
                   for key in ("launch_env_sha256", "entrypoint_sha256",
                               "bootstrap_sha256", "binding_source_sha256",
                               "controller_source_sha256",
                               "web_source_sha256", "ledger_source_sha256",
                               "launcher_source_sha256", "sandbox_source_sha256",
                               "lifecycle_source_sha256", "launchd_source_sha256",
                               "private_evidence_source_sha256",
                               "compact_planner_source_sha256",
                               "identity_probe_source_sha256", "resource_gate_source_sha256",
                               "child_observer_source_sha256",
                               "expected_final_argv_sha256",
                               "expected_inprocess_python_argv_sha256"))):
        _fail("receipt_child_binding_invalid")
    os_argv = _exact_os_final_argv(receipt.get("expected_os_final_argv"))
    if _final_argv_digest(os_argv) != receipt["expected_final_argv_sha256"]:
        _fail("receipt_child_os_argv_digest_mismatch")
    expires = _valid_receipt_time(receipt)
    try:
        _inspect_live_identity(binding)
    except PrivateEndpointBindingError:
        raise
    except Exception:
        _fail("private_ollama_identity_unavailable")
    # Constructor is never an authorization to send B: the sole allowed gate
    # remains closed until a separate, actual transformed-request token oracle.
    final_state = gate.snapshot()
    if (require_unused_gate and (gate._prompt_token_upper_bound is not None
                                 or final_state.get("attempted_provider_calls") != 0
                                 or final_state.get("denied_attempt_count") != 0
                                 or final_state.get("terminal_reason"))):
        _fail("p4_b_gate_changed_during_validation")
    if _receipt(binding) != receipt:
        _fail("receipt_changed_during_validation")
    _exact_private_directory(binding.private_root)
    if not (time.time() < expires):
        _fail("receipt_expired_during_validation")
    return PrivateEndpointTarget(
        base_url=expected_base,
        native_url=f"http://127.0.0.1:{binding.daemon_port}/api/chat",
    )
