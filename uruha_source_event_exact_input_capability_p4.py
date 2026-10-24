"""One-use, exact-input authority for a bounded P4 source-surface trial.

This does not classify benign acts.  It only admits the two pre-reviewed full
messages frozen in the approved-input manifest.  No gold or reply text is read.
Callers must claim before cognition, provider work, memory lookup, or a pending
Web bubble, then scope the returned private handle around the synchronous turn.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import threading
from typing import Iterator


SCHEMA = "uruha_source_event_exact_input_capability_p4_v1"
MANIFEST = Path(__file__).resolve().parent / "research/p4_source_event_surface_approved_input_manifest_2026-10-24.json"
PROBE = Path(__file__).resolve().parent / "datasets/p4_source_event_surface_exact_input_capability_probe_2026-10-24.json"
MANIFEST_SHA256 = "881006636dbe0c18ef04ab719aa038b28edcae978350a8ae082c158ab35f9f00"
PROBE_SHA256 = "15d24270fba014b99d4c3670d48d089232313adabb16106ee15424c96d4fa36e"
CAPABILITY_DIRECTORY = "p4_source_event_exact_input_capability"
PERMIT_NAME = "permit.json"
SPENT_NAME = "spent.json"
_RUN_ID = re.compile(r"[0-9a-f]{16}\Z")
_SLOT = re.compile(r"[0-9a-f]{32}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ACTIVE_CLAIM: ContextVar[ExactInputClaim | None] = ContextVar(
    "p4_source_event_exact_input_claim", default=None
)


class ExactInputCapabilityError(RuntimeError):
    """Only a stable reason code is exposed; never the input or private path."""

    def __init__(self, reason: str, *, pre_turn_safe: bool = False) -> None:
        self.reason = reason
        self.pre_turn_safe = pre_turn_safe
        super().__init__(reason)


CapabilityDenied = ExactInputCapabilityError


class ExactInputClaim:
    """Server-private handle; never put it in client-visible UI or trace state."""

    __slots__ = (
        "_root", "_run_id", "_case_id", "_arm", "_input_sha256", "_slot",
        "_closed", "_entered", "_reserved", "_abandoned", "_lock",
    )

    def __init__(self, root: Path, run_id: str, case_id: str, arm: str,
                 input_sha256: str, slot: str) -> None:
        self._root = root
        self._run_id = run_id
        self._case_id = case_id
        self._arm = arm
        self._input_sha256 = input_sha256
        self._slot = slot
        self._closed = False
        self._entered = False
        self._reserved = False
        self._abandoned = False
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return "<ExactInputClaim private>"

    def __deepcopy__(self, memo: dict) -> ExactInputClaim:
        # A server-side Gradio State relay must not mint a fresh reusable copy.
        return self


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _private_stat(path: Path, *, directory: bool) -> os.stat_result:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise CapabilityDenied("private_path_unavailable") from exc
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        not kind(info.st_mode) or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
        or (not directory and info.st_nlink != 1)
    ):
        raise CapabilityDenied("private_path_invalid")
    return info


def _read_private_json(path: Path) -> dict:
    info = _private_stat(path, directory=False)
    if info.st_size <= 0 or info.st_size > 64 * 1024:
        raise CapabilityDenied("private_file_size_invalid")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if opened.st_dev != info.st_dev or opened.st_ino != info.st_ino:
                raise CapabilityDenied("private_file_changed")
            raw = stream.read(64 * 1024 + 1)
        data = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CapabilityDenied("private_file_unreadable") from exc
    if not isinstance(data, dict):
        raise CapabilityDenied("private_file_invalid")
    return data


def _root_and_run(root: str | Path) -> tuple[Path, str]:
    """Verify the prepared product root and current controller run, read-only.

    The controller's own start/ready identity checks remain separate gates.
    Its PORT and ENTRYPOINT globals are wrapper-scoped in the launcher process,
    so importing them in the Web child would falsely reject non-default ports.
    """
    try:
        given = Path(root)
    except (TypeError, ValueError) as exc:
        raise CapabilityDenied("runtime_root_invalid") from exc
    if not given.is_absolute() or given.is_symlink():
        raise CapabilityDenied("runtime_root_invalid")
    try:
        resolved = given.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CapabilityDenied("runtime_root_invalid") from exc
    if resolved != given or not resolved.name.startswith("uruha-product-"):
        raise CapabilityDenied("runtime_root_invalid")
    if resolved.parent != Path(tempfile.gettempdir()).resolve(strict=True):
        raise CapabilityDenied("runtime_root_not_immediate_temp_child")
    _private_stat(resolved, directory=True)
    manifest = _read_private_json(resolved / "uruha_product_launcher_manifest.json")
    if (manifest.get("schema") != "uruha_p4_b_runtime_root_v1"
            or manifest.get("created_by_launcher") is not True):
        raise CapabilityDenied("launcher_root_unverified")
    prepared = _read_private_json(resolved / "p4_preference_fallback_detached.prepared.json")
    claimed = _read_private_json(resolved / "p4_preference_fallback_detached.prepared-claim.json")
    entrypoint = str(Path(__file__).resolve().parent / "uruha_web_ui_product_p4_direct_reply_act_m29_priority.py")
    if any((
        prepared.get("schema") != "uruha_p4_preference_fallback_detached_control_v1",
        prepared.get("kind") != "prepared_first_start",
        prepared.get("runtime_root") != str(resolved),
        prepared.get("uid") != os.getuid(),
        prepared.get("mode") != "product",
        prepared.get("entrypoint") != entrypoint,
        not isinstance(prepared.get("port"), int),
        claimed.get("schema") != prepared.get("schema"),
        claimed.get("runtime_root") != str(resolved),
        claimed.get("uid") != os.getuid(),
        claimed.get("entrypoint") != entrypoint,
    )):
        raise CapabilityDenied("prepared_product_root_unverified")
    current = _read_private_json(resolved / "p4_preference_fallback_detached.current.json")
    run_id = current.get("run_id")
    if (current.get("schema") != prepared["schema"] or current.get("uid") != os.getuid()
            or not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id)):
        raise CapabilityDenied("current_run_unverified")
    metadata = _read_private_json(resolved / f"p4_preference_fallback_detached.{run_id}.json")
    if any((
        metadata.get("schema") != prepared["schema"],
        metadata.get("runtime_root") != str(resolved),
        metadata.get("run_id") != run_id,
        metadata.get("uid") != os.getuid(),
        metadata.get("mode") != "product",
        metadata.get("port") != prepared["port"],
        not isinstance(metadata.get("pid"), int) or metadata["pid"] <= 0,
        not isinstance(metadata.get("pre_main_command"), str)
        or not metadata["pre_main_command"].endswith(f" {entrypoint}"),
    )):
        raise CapabilityDenied("current_product_run_unverified")
    return resolved, run_id


def _require_attested_child_arm(root: Path, run_id: str, arm: str) -> None:
    """Never issue or use a diagnostic permit for an unattested product child."""
    metadata = _read_private_json(root / f"p4_preference_fallback_detached.{run_id}.json")
    expected_flags = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": arm,
        "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT": str(root),
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
    }
    try:
        receipt = _read_private_json(root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json")
    except CapabilityDenied as exc:
        raise CapabilityDenied("child_arm_not_attested") from exc
    keys = metadata.get("env_keys")
    if (not isinstance(keys, list) or not set(expected_flags).issubset(set(keys))
            or "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT" in keys
            or set(receipt) != {
                "schema", "runtime_root", "run_id", "pid", "port", "flags", "candidate_prompt_absent",
            }
            or receipt.get("schema") != "uruha_p4_source_surface_child_flags_v1"
            or receipt.get("runtime_root") != str(root)
            or receipt.get("run_id") != run_id
            or receipt.get("pid") != metadata.get("pid")
            or receipt.get("port") != metadata.get("port")
            or receipt.get("flags") != expected_flags
            or receipt.get("candidate_prompt_absent") is not True):
        raise CapabilityDenied("child_arm_not_attested")


def current_exact_input_run_id(root: str | Path) -> str:
    """Read the current run ID only after private prepared-run validation."""
    return _root_and_run(root)[1]


def _approved_inputs() -> dict[str, str]:
    try:
        manifest_bytes = MANIFEST.read_bytes()
        probe_bytes = PROBE.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CapabilityDenied("approved_source_unavailable") from exc
    if (_sha(manifest_bytes) != MANIFEST_SHA256 or _sha(probe_bytes) != PROBE_SHA256
            or not isinstance(manifest, dict)
            or manifest.get("schema") != "p4_source_event_surface_approved_input_manifest_v1"
            or manifest.get("probe_sha256") != PROBE_SHA256):
        raise CapabilityDenied("approved_source_changed")
    approved = manifest.get("approved")
    if not isinstance(approved, list) or len(approved) != 2:
        raise CapabilityDenied("approved_source_invalid")
    result = {}
    for row in approved:
        if not isinstance(row, dict) or set(row) != {"case_id", "input_sha256"}:
            raise CapabilityDenied("approved_source_invalid")
        case_id, digest = row["case_id"], row["input_sha256"]
        if (not isinstance(case_id, str) or not isinstance(digest, str)
                or not _SHA256.fullmatch(digest) or case_id in result):
            raise CapabilityDenied("approved_source_invalid")
        result[case_id] = digest
    if set(result) != {"cap_fixed_envelope", "cap_conditional_safari_soup"}:
        raise CapabilityDenied("approved_source_invalid")
    return result


def _capability_dir(root: Path, *, create: bool) -> Path:
    cache = root / ".cache"
    _private_stat(cache, directory=True)
    directory = cache / CAPABILITY_DIRECTORY
    if create:
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise CapabilityDenied("capability_directory_unavailable") from exc
    _private_stat(directory, directory=True)
    return directory


def _write_exclusive_json(path: Path, payload: dict) -> None:
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise CapabilityDenied("capability_already_used_or_issued") from exc
    except OSError as exc:
        raise CapabilityDenied("capability_write_unavailable") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _private_stat(path, directory=False)
        dirfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except OSError as exc:
        # Leave a partial marker in place: retries must remain fail-closed.
        raise CapabilityDenied("capability_write_unavailable") from exc


def issue_exact_input_permit(root: str | Path, case_id: str, arm: str) -> dict:
    """Issue once, after prepared product start publishes its current run ID."""
    if not isinstance(arm, str) or arm not in {"off", "on"}:
        raise CapabilityDenied("invalid_arm")
    approved = _approved_inputs()
    if not isinstance(case_id, str) or case_id not in approved:
        raise CapabilityDenied("case_not_approved")
    runtime_root, run_id = _root_and_run(root)
    _require_attested_child_arm(runtime_root, run_id, arm)
    directory = _capability_dir(runtime_root, create=True)
    if (directory / SPENT_NAME).exists() or (directory / SPENT_NAME).is_symlink():
        raise CapabilityDenied("capability_already_used_or_issued")
    slot = secrets.token_hex(16)
    _write_exclusive_json(directory / PERMIT_NAME, {
        "schema": SCHEMA,
        "manifest_sha256": MANIFEST_SHA256,
        "probe_sha256": PROBE_SHA256,
        "runtime_root": str(runtime_root),
        "run_id": run_id,
        "case_id": case_id,
        "input_sha256": approved[case_id],
        "arm": arm,
        "slot": slot,
    })
    return {
        "schema": SCHEMA, "status": "issued", "case_id": case_id,
        "input_sha256": approved[case_id], "run_id": run_id, "arm": arm,
        "raw_input_in_receipt": False, "secret_in_receipt": False,
    }


def claim_exact_input_permit(root: str | Path, user_text: str, arm: str) -> ExactInputClaim:
    """Consume a matching permit before turn side effects; one OS winner only."""
    if not isinstance(arm, str) or arm not in {"off", "on"}:
        raise CapabilityDenied("invalid_arm")
    if not isinstance(user_text, str):
        raise CapabilityDenied("invalid_raw_input")
    approved = _approved_inputs()
    try:
        input_sha256 = _sha(user_text.encode("utf-8"))
    except UnicodeError as exc:
        raise CapabilityDenied("invalid_raw_input") from exc
    runtime_root, run_id = _root_and_run(root)
    directory = _capability_dir(runtime_root, create=False)
    permit = _read_private_json(directory / PERMIT_NAME)
    case_id = permit.get("case_id")
    slot = permit.get("slot")
    if not isinstance(case_id, str) or case_id not in approved:
        raise CapabilityDenied("permit_does_not_authorize_input")
    if any((
        permit.get("schema") != SCHEMA,
        permit.get("manifest_sha256") != MANIFEST_SHA256,
        permit.get("probe_sha256") != PROBE_SHA256,
        permit.get("runtime_root") != str(runtime_root),
        permit.get("run_id") != run_id,
        permit.get("input_sha256") != approved.get(case_id),
        permit.get("input_sha256") != input_sha256,
        permit.get("arm") != arm,
        not isinstance(slot, str) or not _SLOT.fullmatch(slot),
    )):
        raise CapabilityDenied("permit_does_not_authorize_input")
    _require_attested_child_arm(runtime_root, run_id, arm)
    _write_exclusive_json(directory / SPENT_NAME, {
        "schema": SCHEMA, "status": "claimed", "run_id": run_id,
        "case_id": case_id, "input_sha256": input_sha256,
        "arm": arm, "slot_sha256": _sha(slot.encode("ascii")),
    })
    return ExactInputClaim(runtime_root, run_id, case_id, arm, input_sha256, slot)


def public_claim_receipt(claim: ExactInputClaim) -> dict:
    """Expose only the frozen trace allowlist, never the private claim handle."""
    if not isinstance(claim, ExactInputClaim):
        raise CapabilityDenied("claim_handle_invalid")
    return {
        "reason": "exact_input_permit_consumed",
        "input_sha256": claim._input_sha256,
    }


def close_exact_input_claim(claim: ExactInputClaim | None) -> None:
    """Invalidate an in-process handle, including when a queued turn aborts."""
    if claim is None:
        return
    if not isinstance(claim, ExactInputClaim):
        raise CapabilityDenied("claim_handle_invalid")
    with claim._lock:
        claim._closed = True


def abandon_unreserved_exact_input_claim(claim: ExactInputClaim | None) -> bool:
    """Close a failed queued claim only if no handler already owns it.

    A second Gradio event may reuse the same server-side State with changed
    text.  It must not invalidate the first event after that event reserves
    the claim and begins cognition.
    """
    if claim is None:
        # No handle means this handler cannot prove ownership of an admission.
        return False
    if not isinstance(claim, ExactInputClaim):
        return False
    with claim._lock:
        if claim._reserved or claim._entered or claim._abandoned:
            return False
        claim._closed = True
        claim._abandoned = True
        return True


@contextmanager
def scoped_exact_input_claim(claim: ExactInputClaim | None) -> Iterator[None]:
    if claim is None:
        token = _ACTIVE_CLAIM.set(None)
        try:
            yield
        finally:
            _ACTIVE_CLAIM.reset(token)
        return
    if not isinstance(claim, ExactInputClaim) or _ACTIVE_CLAIM.get() is not None:
        raise CapabilityDenied("claim_scope_invalid")
    with claim._lock:
        if claim._closed or claim._entered:
            raise CapabilityDenied("claim_scope_already_used")
        claim._entered = True
    token = _ACTIVE_CLAIM.set(claim)
    try:
        yield
    finally:
        _ACTIVE_CLAIM.reset(token)
        close_exact_input_claim(claim)


def validate_exact_input_claim(
    claim: ExactInputClaim | None, root: str | Path, user_text: str, arm: str,
) -> ExactInputClaim:
    """Check a claimed permit without setting context or consuming a scope.

    Suitable before Gradio's first yield; the synchronous Brain call later
    enters ``scoped_exact_input_claim`` exactly once.
    """
    if not isinstance(claim, ExactInputClaim) or not isinstance(user_text, str):
        raise CapabilityDenied("same_turn_claim_missing")
    with claim._lock:
        if claim._closed:
            raise CapabilityDenied("same_turn_claim_closed")
    runtime_root, run_id = _root_and_run(root)
    try:
        raw_sha256 = _sha(user_text.encode("utf-8"))
    except UnicodeError as exc:
        raise CapabilityDenied("invalid_raw_input") from exc
    if (runtime_root != claim._root or run_id != claim._run_id or arm != claim._arm
            or raw_sha256 != claim._input_sha256):
        raise CapabilityDenied("same_turn_claim_mismatch")
    spent = _read_private_json(_capability_dir(runtime_root, create=False) / SPENT_NAME)
    if any((
        spent.get("schema") != SCHEMA,
        spent.get("status") != "claimed",
        spent.get("run_id") != run_id,
        spent.get("case_id") != claim._case_id,
        spent.get("input_sha256") != claim._input_sha256,
        spent.get("arm") != arm,
        spent.get("slot_sha256") != _sha(claim._slot.encode("ascii")),
    )):
        raise CapabilityDenied("same_turn_spent_marker_mismatch")
    _require_attested_child_arm(runtime_root, run_id, arm)
    return claim


def reserve_exact_input_claim(
    claim: ExactInputClaim | None, root: str | Path, user_text: str, arm: str,
) -> ExactInputClaim:
    """Allow only one queued Web handler to pass the pre-bubble boundary."""
    validated = validate_exact_input_claim(claim, root, user_text, arm)
    with validated._lock:
        if validated._closed or validated._entered or validated._reserved:
            raise CapabilityDenied("same_turn_claim_already_reserved")
        validated._reserved = True
    return validated


def require_exact_input_claim(root: str | Path, user_text: str, arm: str) -> ExactInputClaim:
    """Recheck the scoped same-turn claim before ingestion or surface work."""
    claim = _ACTIVE_CLAIM.get()
    if not isinstance(claim, ExactInputClaim):
        raise CapabilityDenied("same_turn_claim_missing")
    with claim._lock:
        if not claim._entered:
            raise CapabilityDenied("same_turn_claim_closed")
    return validate_exact_input_claim(claim, root, user_text, arm)


__all__ = [
    "SCHEMA", "CapabilityDenied", "ExactInputCapabilityError", "ExactInputClaim", "current_exact_input_run_id",
    "issue_exact_input_permit", "claim_exact_input_permit", "public_claim_receipt",
    "close_exact_input_claim", "abandon_unreserved_exact_input_claim",
    "scoped_exact_input_claim", "validate_exact_input_claim", "require_exact_input_claim",
    "reserve_exact_input_claim",
]
