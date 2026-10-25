"""Pre-Web, B-only cooperative launch binding for an isolated product child.

This never authorizes a B Send. It has no provider HTTP, DB, Web import, or
network-side effects; it checks a controller receipt and a closed resource gate.
The controller separately attests committed source and final child PID/ready.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Mapping

import uruha_p4_b_private_endpoint_binding as binding_module
from uruha_compute_ledger import ComputeLedger
from uruha_p4_b_resource_gate import P4BResourceGate


_MARKER = "URUHA_P4_B_PRIVATE_CHILD"
_RECEIPT_NAME = "p4_b_private_endpoint_launch_receipt.json"
_ENTRYPOINT = Path(__file__).resolve().with_name(
    "uruha_web_ui_product_p4_preference_fallback.py")
_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")


@dataclass(frozen=True)
class PrivateChildBootState:
    binding: binding_module.PrivateEndpointBinding
    run_id: str
    compute_ledger: ComputeLedger
    resource_gate: P4BResourceGate
    runtime_root: Path


_BOOT_STATE: PrivateChildBootState | None = None


def _fail(reason: str) -> None:
    raise binding_module.PrivateEndpointBindingError(reason)


def _b_intent(environ: Mapping[str, str]) -> bool:
    return any(type(key) is str and key.upper().startswith("URUHA_P4_B_")
               for key in environ)


def _strict_private_root(path: Path) -> None:
    try:
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700
                or path.resolve(strict=True) != path):
            _fail("private_child_root_not_private")
    except OSError:
        _fail("private_child_root_unavailable")


def _read_seed_receipt(root: Path, path: Path) -> tuple[dict, str]:
    if path != root / _RECEIPT_NAME:
        _fail("private_child_receipt_path_mismatch")
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            _fail("private_child_receipt_not_private")
        raw = path.read_bytes()
    except OSError:
        _fail("private_child_receipt_unavailable")
    if len(raw) > 8192:
        _fail("private_child_receipt_oversize")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        _fail("private_child_receipt_invalid")
    if (not isinstance(value, dict)
            or set(value) != binding_module._RECEIPT_FIELDS
            or value.get("schema") != binding_module._RECEIPT_SCHEMA):
        _fail("private_child_receipt_invalid")
    return value, hashlib.sha256(raw).hexdigest()


def _exact_layout(environ: Mapping[str, str], runtime_root: Path) -> None:
    expected = {
        "HOME": str(runtime_root), "TMPDIR": str(runtime_root),
        "URUHA_MEMORY_DB_PATH": str(runtime_root / "memory_db"),
        "URUHA_WEB_SESSION_DB_PATH": str(runtime_root / "session_db"),
        "URUHA_WEB_LOG_JSONL_PATH": str(runtime_root / "web_logs/conversation.jsonl"),
        "URUHA_WEB_LOG_TXT_PATH": str(runtime_root / "web_logs/conversation.txt"),
        "URUHA_WEB_HOST": "127.0.0.1", "URUHA_WEB_PORT": "7894",
    }
    if any(environ.get(key) != value for key, value in expected.items()):
        _fail("private_child_runtime_layout_mismatch")
    for name in ("memory_db", "session_db", "web_logs"):
        _strict_private_root(runtime_root / name)


def _child_context(
    *, binding: binding_module.PrivateEndpointBinding,
    runtime_root: Path, environ: Mapping[str, str], receipt: dict,
) -> None:
    if (environ.get(_MARKER) != "1"
            or environ.get("URUHA_P4_B_RUN_ID") != binding.run_id
            or environ.get("URUHA_P4_B_MODEL_ROOT") != str(binding.private_root)
            or environ.get("URUHA_P4_B_RECEIPT") != str(binding.receipt_path)
            or receipt["runtime_root"] != str(runtime_root)):
        _fail("private_child_launch_identity_mismatch")
    _strict_private_root(runtime_root)
    _exact_layout(environ, runtime_root)
    if (receipt["launch_env_sha256"]
            != binding_module.canonical_b_env_digest(environ)):
        _fail("private_child_environment_drift")
    source = binding_module.private_child_source_digests(_ENTRYPOINT)
    if any(receipt.get(key) != value for key, value in source.items()):
        _fail("private_child_source_drift")
    if len(sys.argv) != 1 or receipt["expected_final_argv_sha256"] != (
        binding_module._final_argv_digest([sys.executable, sys.argv[0]])
    ):
        _fail("private_child_argv_drift")


def _binding_from_receipt(
    *, root: Path, path: Path, receipt: dict, digest: str,
) -> binding_module.PrivateEndpointBinding:
    try:
        binding = binding_module.PrivateEndpointBinding(
            run_id=receipt["run_id"], private_root=root,
            shared_models=Path(receipt["shared_models"]),
            receipt_path=path, receipt_sha256=digest,
            base_url=receipt["base_url"],
            daemon_pid=receipt["daemon_pid"], runner_pid=receipt["runner_pid"],
            daemon_port=receipt["daemon_port"], runner_port=receipt["runner_port"],
            daemon_process_start=receipt["daemon_process_start"],
            runner_process_start=receipt["runner_process_start"],
            daemon_binary=Path(receipt["daemon_binary"]),
            runner_binary=Path(receipt["runner_binary"]),
        )
    except (KeyError, TypeError, ValueError):
        _fail("private_child_receipt_invalid")
    return binding


def bootstrap_private_child(
    environ: Mapping[str, str] | None = None,
) -> PrivateChildBootState | None:
    """Must run as the fixed entry's first operation, before any Web import."""
    global _BOOT_STATE
    environ = os.environ if environ is None else environ
    if not _b_intent(environ):
        if _BOOT_STATE is not None:
            _fail("private_child_environment_disappeared")
        return None
    if _BOOT_STATE is not None:
        _fail("private_child_bootstrap_repeated")
    # Any partial/false B marker is terminal rather than a default-mode hint.
    env_digest = binding_module.canonical_b_env_digest(environ)
    if environ.get(_MARKER) != "1":
        _fail("private_child_marker_invalid")
    run_id = environ.get("URUHA_P4_B_RUN_ID")
    if type(run_id) is not str or not _RUN.fullmatch(run_id):
        _fail("private_child_run_invalid")
    try:
        root = Path(environ["URUHA_P4_B_MODEL_ROOT"])
        receipt_path = Path(environ["URUHA_P4_B_RECEIPT"])
    except (KeyError, TypeError, ValueError):
        _fail("private_child_paths_invalid")
    _strict_private_root(root)
    receipt, digest = _read_seed_receipt(root, receipt_path)
    if (receipt["run_id"] != run_id or receipt["private_root"] != str(root)
            or receipt["launch_env_sha256"] != env_digest):
        _fail("private_child_receipt_identity_mismatch")
    runtime_root = Path(receipt["runtime_root"])
    _strict_private_root(runtime_root)
    binding = _binding_from_receipt(root=root, path=receipt_path,
                                    receipt=receipt, digest=digest)
    _child_context(binding=binding, runtime_root=runtime_root,
                   environ=environ, receipt=receipt)
    gate = P4BResourceGate()
    ledger = ComputeLedger(p4_b_resource_gate=gate)
    binding_module.validate_private_endpoint_binding(
        binding, compute_ledger=ledger, run_id=run_id,
    )
    if binding_module._receipt(binding) != receipt:
        _fail("private_child_receipt_changed_during_bootstrap")
    _child_context(binding=binding, runtime_root=runtime_root,
                   environ=environ, receipt=receipt)
    state = PrivateChildBootState(
        binding=binding, run_id=run_id, compute_ledger=ledger,
        resource_gate=gate,
        runtime_root=runtime_root,
    )
    _BOOT_STATE = state
    return state


def get_private_child_boot_state() -> PrivateChildBootState | None:
    if _b_intent(os.environ) and _BOOT_STATE is None:
        _fail("private_child_bootstrap_missing")
    if _BOOT_STATE is not None and not _b_intent(os.environ):
        _fail("private_child_environment_disappeared")
    if (_BOOT_STATE is not None and
            _BOOT_STATE.compute_ledger.p4_b_resource_gate is not _BOOT_STATE.resource_gate):
        _fail("private_child_resource_gate_changed")
    if _BOOT_STATE is not None:
        # Import-time Web will create log directories and RuntimeManager, so
        # reject any post-boot launch drift before handing it the ledger.
        receipt = binding_module._receipt(_BOOT_STATE.binding)
        binding_module._valid_receipt_time(receipt)
        _child_context(binding=_BOOT_STATE.binding,
                       runtime_root=_BOOT_STATE.runtime_root,
                       environ=os.environ, receipt=receipt)
        if binding_module._receipt(_BOOT_STATE.binding) != receipt:
            _fail("private_child_receipt_changed_before_web_import")
        binding_module._valid_receipt_time(receipt)
    return _BOOT_STATE


def revalidate_private_child_before_create(state: PrivateChildBootState) -> None:
    """Read-only identity check at the inner completion chokepoint; no Send permit."""
    if state is None or state is not _BOOT_STATE:
        _fail("private_child_boot_state_mismatch")
    if state.compute_ledger.p4_b_resource_gate is not state.resource_gate:
        _fail("private_child_resource_gate_changed")
    environ = os.environ
    if not _b_intent(environ):
        _fail("private_child_environment_disappeared")
    receipt = binding_module._receipt(state.binding)
    _child_context(binding=state.binding, runtime_root=state.runtime_root,
                   environ=environ, receipt=receipt)
    binding_module.validate_private_endpoint_binding(
        state.binding, compute_ledger=state.compute_ledger,
        run_id=state.run_id, require_unused_gate=False,
    )
    if binding_module._receipt(state.binding) != receipt:
        _fail("private_child_receipt_changed_during_revalidation")
    _child_context(binding=state.binding, runtime_root=state.runtime_root,
                   environ=environ, receipt=receipt)
