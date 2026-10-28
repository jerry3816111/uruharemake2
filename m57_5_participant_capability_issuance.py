#!/usr/bin/env python3
"""M57.5 separated capability issuance and token-free browser transport.

This module wraps, but does not modify, the frozen M57.4 evidence semantics.
The coordinator-facing result contains no raw role tokens.  Each role receives
one private envelope; the secure collector consumes it once and keeps the M57.4
token only in process memory while the browser uses an independent session
cookie and CSRF token.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import html
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import os
from pathlib import Path
import re
import secrets
import stat
from tempfile import TemporaryDirectory
from threading import Thread
from time import perf_counter
from typing import Any
import urllib.parse
import urllib.request

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_4_component_evidence_collection as collection_m57
from test_m56_10_crash_safe_outcome_join import m5610_private_roots
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
import m57_1_preoutcome_diagnostic_commitment as commitment_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_5_participant_capability_issuance_v1.json"
RESULT_PATH = ROOT / "analysis/m57_5_participant_capability_issuance_rehearsal_2026-09-04.json"

ROLE_SLOTS = collection_m57.ROLE_SLOTS
CODER_SLOTS = collection_m57.CODER_SLOTS
COOKIE_NAME = "m57_5_session"

INTENT_FILENAME = "m57_5_participant_capability_issuance_intent.json"
COMMITMENT_FILENAME = "m57_5_participant_capability_issuance_commitment.json"

INTENT_SCHEMA = "uruha_m57_5_participant_capability_issuance_intent_v1"
ENVELOPE_SCHEMA = "uruha_m57_5_participant_capability_envelope_v1"
SPENT_ENVELOPE_SCHEMA = "uruha_m57_5_spent_participant_capability_envelope_v1"
COMMITMENT_SCHEMA = "uruha_m57_5_participant_capability_issuance_commitment_v1"
CLAIM_SCHEMA = "uruha_m57_5_participant_capability_claim_receipt_v1"
REHEARSAL_SCHEMA = "uruha_m57_5_participant_capability_issuance_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_5_participant_capability_issuance_live_audit_v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _hashless(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {name: child for name, child in value.items() if name != field}


def _contains_raw_role_token(value: Any) -> bool:
    if isinstance(value, dict):
        if "role_session_token" in value:
            return True
        return any(_contains_raw_role_token(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_raw_role_token(child) for child in value)
    return False


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    fields = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "issuance", "claim", "browser_session", "preserved_boundaries", "public_functions",
        "claim_boundary",
    }
    if set(contract) != fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_5_participant_capability_issuance_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_before_any_real_capability_issuance":
        errors.append("contract.status")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 3:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    issuance = contract.get("issuance") or {}
    if issuance.get("role_slots") != list(ROLE_SLOTS):
        errors.append("issuance.roles")
    for name in (
        "delivery_root_must_be_new_absolute_local_directory", "one_envelope_per_role",
        "pre_initialization_full_sync_intent_required", "completed_identical_replay_allowed",
    ):
        if issuance.get(name) is not True:
            errors.append(f"issuance.{name}")
    for name in (
        "public_initialization_result_contains_raw_role_token", "central_commitment_contains_raw_role_token",
        "partial_or_intent_only_retry_allowed",
    ):
        if issuance.get(name) is not False:
            errors.append(f"issuance.{name}")
    if issuance.get("delivery_root_mode") != "0700" or issuance.get("role_directory_mode") != "0700" or issuance.get("envelope_file_mode") != "0600":
        errors.append("issuance.modes")
    claim = contract.get("claim") or {}
    for name in (
        "correct_run_role_path_and_hash_required", "outcome_state_absence_revalidated",
        "one_time_claim_receipt_required", "raw_role_token_removed_from_claimed_envelope",
        "server_holds_role_token_in_memory_only_after_claim",
    ):
        if claim.get(name) is not True:
            errors.append(f"claim.{name}")
    for name in ("second_claim_allowed", "server_restart_after_claim_supported"):
        if claim.get(name) is not False:
            errors.append(f"claim.{name}")
    browser = contract.get("browser_session") or {}
    for name in (
        "host_only_session_cookie", "http_only_cookie", "same_site_strict_cookie",
        "per_server_random_session_id", "per_server_random_csrf_token", "csrf_required_for_post",
        "cache_control_no_store", "referrer_policy_no_referrer", "content_security_policy_restrictive",
    ):
        if browser.get(name) is not True:
            errors.append(f"browser.{name}")
    for name in (
        "role_token_in_argv", "role_token_in_url_or_query", "role_token_in_html_or_form",
        "role_token_in_cookie", "secure_cookie_flag_on_plain_loopback_http",
    ):
        if browser.get(name) is not False:
            errors.append(f"browser.{name}")
    preserved = contract.get("preserved_boundaries") or {}
    expected_zero = {"target_outcome_access_count": 0, "model_call_count": 0}
    for name, expected in expected_zero.items():
        if preserved.get(name) != expected:
            errors.append(f"preserved.{name}")
    for name in (
        "m57_4_frozen_files_changed", "m57_4_ledger_or_manifest_semantics_changed",
        "production_memory_write", "external_deployment", "synthetic_fixture_may_become_formal",
        "m58_authorized",
    ):
        if preserved.get(name) is not False:
            errors.append(f"preserved.{name}")
    functions = {
        "initialize_separated_participant_capabilities": initialize_separated_participant_capabilities,
        "validate_participant_capability_issuance": validate_participant_capability_issuance,
        "serve_secure_collection": serve_secure_collection,
    }
    signatures = contract.get("public_functions") or {}
    if set(signatures) != set(functions):
        errors.append("public_functions.names")
    for name, function in functions.items():
        if list(inspect.signature(function).parameters) != signatures.get(name):
            errors.append(f"public_functions.{name}")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = collection_m57._paths(run_id)
    return {
        **paths,
        "m57_5_intent": paths["commitments"] / INTENT_FILENAME,
        "m57_5_commitment": paths["commitments"] / COMMITMENT_FILENAME,
        **{
            f"m57_5_claim_{role}": paths["commitments"] / f"m57_5_{role}_capability_claim.json"
            for role in ROLE_SLOTS
        },
    }


def _normalize_delivery_root(delivery_root: str) -> Path:
    if not isinstance(delivery_root, str) or not delivery_root.strip():
        raise ValueError("M57.5 delivery root must be a non-empty absolute path")
    supplied = Path(delivery_root)
    if not supplied.is_absolute():
        raise ValueError("M57.5 delivery root must be absolute")
    resolved = supplied.resolve(strict=False)
    if resolved == Path(resolved.anchor) or resolved.parent == resolved:
        raise PermissionError("M57.5 refuses a filesystem root as delivery root")
    parent = resolved.parent
    if not parent.exists() or parent.is_symlink() or not parent.is_dir():
        raise PermissionError("M57.5 delivery parent must be an existing real directory")
    return resolved


def _mode_bits(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _validate_envelope(value: dict[str, Any], role: str, mode: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "participant_pseudonym",
        "role_session_token", "session_token_sha256", "issued_at_utc", "envelope_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["envelope.fields"]
    errors: list[str] = []
    expected = {
        "schema": ENVELOPE_SCHEMA,
        "version": "1.0.0",
        "status": "unclaimed_private_role_capability",
        "run_id": mode["run_id"],
        "role_slot": role,
        "participant_pseudonym": mode["participants"][role]["pseudonym"],
        "session_token_sha256": mode["participants"][role]["session_token_sha256"],
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"envelope.{name}")
    token = value.get("role_session_token")
    if not isinstance(token, str) or sha256(token.encode("utf-8")).hexdigest() != expected["session_token_sha256"]:
        errors.append("envelope.token")
    if not _valid_timestamp(value.get("issued_at_utc")):
        errors.append("envelope.timestamp")
    if value.get("envelope_hash") != digest(_hashless(value, "envelope_hash")):
        errors.append("envelope.hash")
    return errors


def _validate_spent_envelope(value: dict[str, Any], role: str, run_id: str, initial_hash: str) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "initial_envelope_sha256",
        "claimed_at_utc", "raw_role_token_present", "spent_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["spent.fields"]
    errors: list[str] = []
    expected = {
        "schema": SPENT_ENVELOPE_SCHEMA,
        "version": "1.0.0",
        "status": "claimed_and_raw_role_token_removed",
        "run_id": run_id,
        "role_slot": role,
        "initial_envelope_sha256": initial_hash,
        "raw_role_token_present": False,
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"spent.{name}")
    if not _valid_timestamp(value.get("claimed_at_utc")):
        errors.append("spent.timestamp")
    if value.get("spent_hash") != digest(_hashless(value, "spent_hash")):
        errors.append("spent.hash")
    if _contains_raw_role_token(value):
        errors.append("spent.raw_token")
    return errors


def _validate_intent(value: dict[str, Any], run_id: str) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "contract_hash", "roster_hash",
        "delivery_root", "created_at_utc", "target_outcome_access_count", "model_call_count",
        "formal_evidence_created", "m58_authorized", "intent_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["intent.fields"]
    errors: list[str] = []
    expected = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "capability_issuance_intent_full_sync_before_m57_4_initialization",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"intent.{name}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("roster_hash", ""))):
        errors.append("intent.roster_hash")
    if not isinstance(value.get("delivery_root"), str) or not Path(value["delivery_root"]).is_absolute():
        errors.append("intent.delivery_root")
    if not _valid_timestamp(value.get("created_at_utc")):
        errors.append("intent.timestamp")
    if value.get("intent_hash") != digest(_hashless(value, "intent_hash")):
        errors.append("intent.hash")
    return errors


def _load_m57_4_mode(run_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    context = collection_m57._context(run_id)
    paths = _paths(run_id)
    mode = collection_m57._load_mode(run_id, context, paths)
    return mode, context, paths


def _validate_commitment(value: dict[str, Any], run_id: str, mode: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "contract_hash", "intent_hash",
        "m57_4_mode_hash", "data_kind", "delivery_root", "roles", "created_at_utc",
        "target_outcome_access_count", "model_call_count", "formal_evidence_created",
        "m58_authorized", "commitment_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["commitment.fields"]
    errors: list[str] = []
    expected = {
        "schema": COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "three_separate_capability_envelopes_full_sync_committed",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "intent_hash": intent["intent_hash"],
        "m57_4_mode_hash": mode["mode_hash"],
        "data_kind": mode["data_kind"],
        "delivery_root": intent["delivery_root"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"commitment.{name}")
    if not _valid_timestamp(value.get("created_at_utc")):
        errors.append("commitment.timestamp")
    roles = value.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(ROLE_SLOTS):
        errors.append("commitment.roles")
    else:
        for role in ROLE_SLOTS:
            row = roles[role]
            row_fields = {
                "role_slot", "participant_pseudonym", "session_token_sha256",
                "envelope_path", "initial_envelope_sha256",
            }
            if not isinstance(row, dict) or set(row) != row_fields:
                errors.append(f"commitment.roles.{role}.fields")
                continue
            if row.get("role_slot") != role:
                errors.append(f"commitment.roles.{role}.slot")
            participant = mode["participants"][role]
            if row.get("participant_pseudonym") != participant["pseudonym"] or row.get("session_token_sha256") != participant["session_token_sha256"]:
                errors.append(f"commitment.roles.{role}.participant")
            expected_path = str(Path(intent["delivery_root"]) / role / "capability-envelope.json")
            if row.get("envelope_path") != expected_path:
                errors.append(f"commitment.roles.{role}.path")
            if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("initial_envelope_sha256", ""))):
                errors.append(f"commitment.roles.{role}.hash")
    if _contains_raw_role_token(value):
        errors.append("commitment.raw_token")
    if value.get("commitment_hash") != digest(_hashless(value, "commitment_hash")):
        errors.append("commitment.hash")
    return errors


def _validate_claim(value: dict[str, Any], role: str, row: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "participant_pseudonym",
        "session_token_sha256", "initial_envelope_sha256", "spent_envelope_sha256",
        "claimed_at_utc", "target_outcome_access_count", "model_call_count",
        "formal_evidence_created", "m58_authorized", "claim_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["claim.fields"]
    errors: list[str] = []
    expected = {
        "schema": CLAIM_SCHEMA,
        "version": "1.0.0",
        "status": "one_time_role_capability_claimed_and_envelope_scrubbed",
        "role_slot": role,
        "participant_pseudonym": row["participant_pseudonym"],
        "session_token_sha256": row["session_token_sha256"],
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"claim.{name}")
    if not _valid_timestamp(value.get("claimed_at_utc")):
        errors.append("claim.timestamp")
    if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("spent_envelope_sha256", ""))):
        errors.append("claim.spent_hash")
    if _contains_raw_role_token(value):
        errors.append("claim.raw_token")
    if value.get("claim_hash") != digest(_hashless(value, "claim_hash")):
        errors.append("claim.hash")
    return errors


def validate_participant_capability_issuance(run_id: str) -> dict[str, Any]:
    """Validate one complete M57.5 issuance without returning any raw token."""
    errors: list[str] = []
    try:
        single_writer_m56._validate_permitted_run(run_id)
        mode, context, paths = _load_m57_4_mode(run_id)
        del context
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        return {"valid": False, "errors": [f"upstream:{exc}"], "run_id": run_id}
    if not paths["m57_5_intent"].is_file():
        return {"valid": False, "errors": ["intent.absent"], "run_id": run_id}
    intent = load_json(paths["m57_5_intent"])
    errors.extend(_validate_intent(intent, run_id))
    if not paths["m57_5_commitment"].is_file():
        errors.append("commitment.absent")
        return {"valid": False, "errors": errors, "run_id": run_id}
    commitment = load_json(paths["m57_5_commitment"])
    errors.extend(_validate_commitment(commitment, run_id, mode, intent))
    if errors:
        return {"valid": False, "errors": errors, "run_id": run_id}
    for role in ROLE_SLOTS:
        row = commitment["roles"][role]
        envelope_path = Path(row["envelope_path"])
        if not envelope_path.is_file() or envelope_path.is_symlink():
            errors.append(f"{role}.envelope.absent_or_symlink")
            continue
        if _mode_bits(envelope_path) != 0o600 or _mode_bits(envelope_path.parent) != 0o700:
            errors.append(f"{role}.permissions")
        claim_path = paths[f"m57_5_claim_{role}"]
        envelope = load_json(envelope_path)
        if claim_path.exists():
            claim = load_json(claim_path)
            errors.extend(f"{role}:{name}" for name in _validate_claim(claim, role, row))
            errors.extend(
                f"{role}:{name}"
                for name in _validate_spent_envelope(envelope, role, run_id, row["initial_envelope_sha256"])
            )
            if claim.get("run_id") != run_id or claim.get("spent_envelope_sha256") != sha256_file(envelope_path):
                errors.append(f"{role}.claim_binding")
        else:
            if sha256_file(envelope_path) != row["initial_envelope_sha256"]:
                errors.append(f"{role}.envelope_hash")
            errors.extend(f"{role}:{name}" for name in _validate_envelope(envelope, role, mode))
    return {
        "valid": not errors,
        "errors": errors,
        "run_id": run_id,
        "data_kind": mode["data_kind"],
        "delivery_root": commitment["delivery_root"],
        "role_count": len(ROLE_SLOTS),
        "claimed_role_count": sum(paths[f"m57_5_claim_{role}"].exists() for role in ROLE_SLOTS),
        "raw_role_tokens_returned": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def _public_issuance_receipt(commitment: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    return {
        "status": "m57_5_existing_issuance_revalidated" if replay else "m57_5_separate_capabilities_issued",
        "run_id": commitment["run_id"],
        "data_kind": commitment["data_kind"],
        "delivery_root": commitment["delivery_root"],
        "role_envelopes": {
            role: {
                "role_slot": role,
                "participant_pseudonym": row["participant_pseudonym"],
                "envelope_path": row["envelope_path"],
                "initial_envelope_sha256": row["initial_envelope_sha256"],
            }
            for role, row in commitment["roles"].items()
        },
        "raw_role_tokens_returned": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def _initialize_separated(
    run_id: str, participant_roster: dict[str, Any], delivery_root: str, *, synthetic: bool,
) -> dict[str, Any]:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("invalid M57.5 contract: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    roster_errors = collection_m57._validate_roster(participant_roster, synthetic=synthetic)
    if roster_errors:
        raise ValueError("invalid M57.5 participant roster: " + "; ".join(roster_errors))
    root = _normalize_delivery_root(delivery_root)
    paths = _paths(run_id)
    roster_hash = digest(participant_roster)
    if paths["m57_5_commitment"].exists():
        report = validate_participant_capability_issuance(run_id)
        if not report["valid"]:
            raise PermissionError("invalid existing M57.5 issuance: " + "; ".join(report["errors"]))
        commitment = load_json(paths["m57_5_commitment"])
        intent = load_json(paths["m57_5_intent"])
        if intent["delivery_root"] != str(root) or intent["roster_hash"] != roster_hash:
            raise FileExistsError("M57.5 issuance already exists with different inputs")
        return _public_issuance_receipt(commitment, replay=True)
    if paths["m57_5_intent"].exists():
        raise PermissionError("M57.5 intent without complete commitment is terminal; use a new run ID")
    if root.exists() or root.is_symlink():
        raise FileExistsError("M57.5 delivery root must not already exist")
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = collection_m57._context(run_id)
        del context
        collection_m57._no_outcome(paths, "capability issuance intent")
        if paths["m57_5_intent"].exists() or paths["m57_5_commitment"].exists():
            raise FileExistsError("M57.5 issuance state appeared concurrently")
        intent = {
            "schema": INTENT_SCHEMA,
            "version": "1.0.0",
            "status": "capability_issuance_intent_full_sync_before_m57_4_initialization",
            "run_id": run_id,
            "contract_hash": contract["contract_hash"],
            "roster_hash": roster_hash,
            "delivery_root": str(root),
            "created_at_utc": _utc_now(),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
        intent["intent_hash"] = digest(intent)
        durable_m56._durable_atomic_write_json(paths["m57_5_intent"], intent, exclusive=True)
    initialized = (
        collection_m57._initialize(run_id, participant_roster, synthetic=True)
        if synthetic
        else collection_m57.initialize_component_evidence_collection(run_id, participant_roster)
    )
    tokens = initialized["role_session_tokens"]
    durable_m56._ensure_durable_directory(root)
    os.chmod(root, 0o700)
    envelope_rows: dict[str, dict[str, Any]] = {}
    for role in ROLE_SLOTS:
        role_dir = root / role
        durable_m56._ensure_durable_directory(role_dir)
        os.chmod(role_dir, 0o700)
        envelope_path = role_dir / "capability-envelope.json"
        envelope = {
            "schema": ENVELOPE_SCHEMA,
            "version": "1.0.0",
            "status": "unclaimed_private_role_capability",
            "run_id": run_id,
            "role_slot": role,
            "participant_pseudonym": participant_roster[role]["pseudonym"],
            "role_session_token": tokens[role],
            "session_token_sha256": sha256(tokens[role].encode("utf-8")).hexdigest(),
            "issued_at_utc": _utc_now(),
        }
        envelope["envelope_hash"] = digest(envelope)
        durable_m56._durable_atomic_write_json(envelope_path, envelope, exclusive=True)
        os.chmod(envelope_path, 0o600)
        envelope_rows[role] = {
            "role_slot": role,
            "participant_pseudonym": participant_roster[role]["pseudonym"],
            "session_token_sha256": envelope["session_token_sha256"],
            "envelope_path": str(envelope_path),
            "initial_envelope_sha256": sha256_file(envelope_path),
        }
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        mode, context, paths = _load_m57_4_mode(run_id)
        del context
        collection_m57._no_outcome(paths, "capability issuance commitment")
        if mode["data_kind"] != (collection_m57.SYNTHETIC_KIND if synthetic else collection_m57.REAL_KIND):
            raise PermissionError("M57.5/M57.4 data-kind mismatch")
        commitment = {
            "schema": COMMITMENT_SCHEMA,
            "version": "1.0.0",
            "status": "three_separate_capability_envelopes_full_sync_committed",
            "run_id": run_id,
            "contract_hash": contract["contract_hash"],
            "intent_hash": intent["intent_hash"],
            "m57_4_mode_hash": mode["mode_hash"],
            "data_kind": mode["data_kind"],
            "delivery_root": str(root),
            "roles": envelope_rows,
            "created_at_utc": _utc_now(),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
        commitment["commitment_hash"] = digest(commitment)
        errors = _validate_commitment(commitment, run_id, mode, intent)
        if errors:
            raise AssertionError("constructed M57.5 commitment invalid: " + "; ".join(errors))
        durable_m56._durable_atomic_write_json(paths["m57_5_commitment"], commitment, exclusive=True)
    report = validate_participant_capability_issuance(run_id)
    if not report["valid"]:
        raise AssertionError("completed M57.5 issuance invalid: " + "; ".join(report["errors"]))
    return _public_issuance_receipt(commitment, replay=False)


def initialize_separated_participant_capabilities(
    run_id: str, participant_roster: dict[str, Any], delivery_root: str,
) -> dict[str, Any]:
    """Issue a real collection's role envelopes without returning any raw role token."""
    return _initialize_separated(run_id, participant_roster, delivery_root, synthetic=False)


def _claim_capability(run_id: str, role_slot: str, envelope_path: str) -> tuple[str, dict[str, Any]]:
    if role_slot not in ROLE_SLOTS:
        raise ValueError("unknown M57.5 role slot")
    supplied_path = Path(envelope_path).resolve(strict=False)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        mode, context, paths = _load_m57_4_mode(run_id)
        del context
        collection_m57._no_outcome(paths, "capability claim")
        report = validate_participant_capability_issuance(run_id)
        if not report["valid"]:
            raise PermissionError("invalid M57.5 issuance before claim: " + "; ".join(report["errors"]))
        commitment = load_json(paths["m57_5_commitment"])
        row = commitment["roles"][role_slot]
        expected_path = Path(row["envelope_path"])
        if supplied_path != expected_path:
            raise PermissionError("M57.5 envelope does not belong to requested run and role")
        claim_path = paths[f"m57_5_claim_{role_slot}"]
        if claim_path.exists():
            raise PermissionError("M57.5 role capability was already claimed; restart is unsupported")
        envelope = load_json(expected_path)
        errors = _validate_envelope(envelope, role_slot, mode)
        if errors or sha256_file(expected_path) != row["initial_envelope_sha256"]:
            raise PermissionError("invalid M57.5 role envelope: " + "; ".join(errors or ["file_hash"]))
        role_token = envelope["role_session_token"]
        claimed_at = _utc_now()
        spent = {
            "schema": SPENT_ENVELOPE_SCHEMA,
            "version": "1.0.0",
            "status": "claimed_and_raw_role_token_removed",
            "run_id": run_id,
            "role_slot": role_slot,
            "initial_envelope_sha256": row["initial_envelope_sha256"],
            "claimed_at_utc": claimed_at,
            "raw_role_token_present": False,
        }
        spent["spent_hash"] = digest(spent)
        spent_bytes = (json.dumps(spent, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        spent_file_hash = sha256(spent_bytes).hexdigest()
        claim = {
            "schema": CLAIM_SCHEMA,
            "version": "1.0.0",
            "status": "one_time_role_capability_claimed_and_envelope_scrubbed",
            "run_id": run_id,
            "role_slot": role_slot,
            "participant_pseudonym": row["participant_pseudonym"],
            "session_token_sha256": row["session_token_sha256"],
            "initial_envelope_sha256": row["initial_envelope_sha256"],
            "spent_envelope_sha256": spent_file_hash,
            "claimed_at_utc": claimed_at,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
        claim["claim_hash"] = digest(claim)
        durable_m56._durable_atomic_write_json(claim_path, claim, exclusive=True)
        durable_m56._durable_atomic_write_json(expected_path, spent)
        os.chmod(expected_path, 0o600)
        if sha256_file(expected_path) != spent_file_hash:
            raise OSError("M57.5 spent envelope durable hash mismatch")
    final_report = validate_participant_capability_issuance(run_id)
    if not final_report["valid"]:
        raise AssertionError("M57.5 issuance invalid after claim: " + "; ".join(final_report["errors"]))
    return role_token, claim


def _cookie_value(header: str | None) -> str:
    jar = cookies.SimpleCookie()
    try:
        jar.load(header or "")
    except cookies.CookieError:
        return ""
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel else ""


def _render_secure_page(
    run_id: str, role: str, role_token: str, sample_id: str, csrf_token: str, error: str = "",
) -> str:
    view = collection_m57.record_component_source_view(run_id, role, role_token, sample_id)
    source = view["source_information"]
    current = html.escape(str(source["current_pre_cutoff_event"]))
    histories = source["all_pre_cutoff_history"]
    history_html = "".join(
        f'<label><input type="checkbox" name="history_id" value="{html.escape(row["history_id"])}"> '
        f'{html.escape(row["history_id"])} · {html.escape(str(row.get("content", row)))}</label>'
        for row in histories
    ) or "<p>這一題沒有cutoff前history。</p>"
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    if role in CODER_SLOTS:
        form_body = f"""<label>可直接看見的特徵（每行一項）<textarea name="observable_features" required></textarea></label>
<label>表徵說明<textarea name="representation_note" required></textarea></label><fieldset><legend>可使用的過去記憶</legend>{history_html}</fieldset>
<label>為何選這些記憶<textarea name="selection_rule" required></textarea></label>"""
        independence = "你只會看到自己的ledger；另一位coder的內容不會出現在此頁。"
    else:
        adjudication = view["adjudication_context"]
        coder_text = html.escape(json.dumps(adjudication["coder_contributions"], ensure_ascii=False, indent=2))
        state_example = html.escape(json.dumps({
            "observable_proxy_variables": {"observable_context": "只寫來源可見內容"},
            "source_refs": ["source_information.current_pre_cutoff_event"],
        }, ensure_ascii=False, indent=2))
        form_body = f"""<pre>{coder_text}</pre><label>Perception採用<select name="perception_choice"><option>coder_a</option><option>coder_b</option></select></label>
<label>Perception裁決理由<textarea name="perception_resolution_basis" required></textarea></label>
<label>Retrieval採用<select name="retrieval_choice"><option>coder_a</option><option>coder_b</option></select></label>
<label>Retrieval裁決理由<textarea name="retrieval_resolution_basis" required></textarea></label>
<label>Observable state proxy JSON<textarea name="observable_state_proxy" required>{state_example}</textarea></label>"""
        independence = f"兩位coder都已封存；系統計算的分歧為 {html.escape(str(adjudication['computed_disagreement']))}。"
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.5 {html.escape(role)}</title><style>
body{{font-family:-apple-system,sans-serif;background:#07151a;color:#eefbff;margin:0}}main{{max-width:900px;margin:auto;padding:24px}}section{{background:#10242b;border:1px solid #3d6470;border-radius:18px;padding:20px;margin-bottom:16px}}label{{display:block;margin:14px 0}}textarea,select{{width:100%;padding:10px;margin-top:6px}}fieldset label{{padding:6px}}pre{{white-space:pre-wrap;background:#07181e;padding:14px;border-radius:12px}}button{{padding:12px 18px;background:#65d2af;border:0;border-radius:10px;font-weight:800}}.error{{color:#ffabb8}}.safe{{color:#76dfba}}</style></head><body><main><section><b>M57.5 · {html.escape(role)}</b><h1>{html.escape(sample_id)}</h1><p class="safe">角色憑證只留在本機服務記憶體；網址與表單沒有M57.4 bearer token。</p><p>{html.escape(independence)}</p><p>現在可見輸入：{current}</p></section>{error_html}<section><form method="post" action="/save"><input type="hidden" name="csrf" value="{html.escape(csrf_token)}"><input type="hidden" name="sample_id" value="{html.escape(sample_id)}">{form_body}<button>保存這一題</button></form></section></main></body></html>"""


def _make_secure_collection_server(
    run_id: str, role_slot: str, envelope_path: str, port: int,
) -> tuple[ThreadingHTTPServer, dict[str, Any]]:
    role_token, claim = _claim_capability(run_id, role_slot, envelope_path)
    context = collection_m57._context(run_id)
    order = collection_m57._sample_order(context)
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def _headers(self, status: int, body: bytes = b"", *, location: str | None = None, set_cookie: bool = False) -> None:
            self.send_response(status)
            if body:
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
            if location is not None:
                self.send_header("Location", location)
            if set_cookie:
                self.send_header("Set-Cookie", f"{COOKIE_NAME}={session_id}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _cookie_ok(self) -> bool:
            return hmac.compare_digest(_cookie_value(self.headers.get("Cookie")), session_id)

        def _send_text(self, text: str, status: int) -> None:
            self._headers(status, html.escape(text).encode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/":
                self._send_text("not found", 404)
                return
            query = urllib.parse.parse_qs(parsed.query)
            if set(query) - {"sample"}:
                self._send_text("unexpected query field", 400)
                return
            sample_id = query.get("sample", [order[0]])[0]
            if not self._cookie_ok():
                location = f"/?sample={urllib.parse.quote(sample_id)}"
                self._headers(303, location=location, set_cookie=True)
                return
            try:
                body = _render_secure_page(run_id, role_slot, role_token, sample_id, csrf_token).encode("utf-8")
                self._headers(200, body)
            except (ValueError, PermissionError, FileNotFoundError) as exc:
                self._send_text(str(exc), 400)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self._send_text("not found", 404)
                return
            if not self._cookie_ok():
                self._send_text("invalid browser session", 403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 131072:
                self._send_text("invalid form size", 400)
                return
            form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            submitted_csrf = form.pop("csrf", [""])[0]
            sample_id = form.get("sample_id", [""])[0]
            if not hmac.compare_digest(submitted_csrf, csrf_token):
                self._send_text("invalid CSRF token", 403)
                return
            if "token" in form:
                self._send_text("raw role token form field forbidden", 400)
                return
            try:
                view = collection_m57.record_component_source_view(run_id, role_slot, role_token, sample_id)
                payload = collection_m57._entry_form_payload(role_slot, form, view)
                collection_m57.save_component_evidence_entry(run_id, role_slot, role_token, sample_id, payload)
                next_index = min(len(order) - 1, order.index(sample_id) + 1)
                self._headers(303, location=f"/?sample={urllib.parse.quote(order[next_index])}")
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                try:
                    body = _render_secure_page(
                        run_id, role_slot, role_token, sample_id, csrf_token, str(exc)
                    ).encode("utf-8")
                    self._headers(400, body)
                except (ValueError, PermissionError, FileNotFoundError):
                    self._send_text(str(exc), 400)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    public_metadata = {
        "run_id": run_id,
        "role_slot": role_slot,
        "port": server.server_address[1],
        "claim_hash": claim["claim_hash"],
        "cookie_name": COOKIE_NAME,
        "role_token_in_metadata": False,
    }
    return server, public_metadata


def serve_secure_collection(run_id: str, role_slot: str, envelope_path: str, port: int) -> None:
    """Consume one role envelope and serve a token-free loopback browser session."""
    server, metadata = _make_secure_collection_server(run_id, role_slot, envelope_path, port)
    del metadata
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _synthetic_roster() -> dict[str, dict[str, Any]]:
    return collection_m57._synthetic_roster()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        del request, fp, code, msg, headers, newurl
        return None


def _http_exchange(server: ThreadingHTTPServer, role_token: str) -> dict[str, Any]:
    """Exercise a claimed server. Kept separate so tests can inspect raw-token absence."""
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    opener = urllib.request.build_opener(_NoRedirect())
    base = f"http://127.0.0.1:{port}"
    try:
        try:
            opener.open(urllib.request.Request(base + "/", method="GET"))
            raise AssertionError("expected first GET redirect")
        except urllib.error.HTTPError as response:
            first_status = response.code
            location = response.headers.get("Location", "")
            set_cookie = response.headers.get("Set-Cookie", "")
        cookie_header = set_cookie.split(";", 1)[0]
        second = opener.open(urllib.request.Request(base + location, headers={"Cookie": cookie_header}, method="GET"))
        body = second.read().decode("utf-8")
        csrf_match = re.search(r'name="csrf" value="([^"]+)"', body)
        sample_match = re.search(r'name="sample_id" value="([^"]+)"', body)
        if not csrf_match or not sample_match:
            raise AssertionError("secure form fields missing")
        csrf = csrf_match.group(1)
        sample_id = sample_match.group(1)
        encoded = urllib.parse.urlencode({
            "csrf": csrf,
            "sample_id": sample_id,
            "observable_features": "input_modality:text_paraphrase\nvisible_event_present:true",
            "representation_note": "Synthetic M57.5 secure-session rehearsal.",
            "selection_rule": "No cutoff history was available, so none was selected.",
        }).encode("utf-8")
        try:
            opener.open(urllib.request.Request(
                base + "/save", data=encoded, headers={
                    "Cookie": cookie_header,
                    "Content-Type": "application/x-www-form-urlencoded",
                }, method="POST"
            ))
            raise AssertionError("expected POST redirect")
        except urllib.error.HTTPError as response:
            post_status = response.code
            post_location = response.headers.get("Location", "")
        surfaces = [base + "/", location, set_cookie, body, post_location, cookie_header, csrf]
        return {
            "first_status": first_status,
            "location": location,
            "set_cookie": set_cookie,
            "body": body,
            "post_status": post_status,
            "post_location": post_location,
            "sample_id": sample_id,
            "raw_role_token_surface_occurrences": sum(role_token in surface for surface in surfaces),
            "role_token_equals_cookie_or_csrf": role_token in {cookie_header.split("=", 1)[-1], csrf},
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def build_engineering_rehearsal() -> dict[str, Any]:
    start = perf_counter()
    run_id = "m57-5-synthetic-separated-capability-rehearsal"
    with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
        root = Path(temp)
        root_resolved = root.resolve()
        materialize_scoring_run(root, run_id)
        commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
        delivery = root_resolved / "participant-delivery"
        receipt = _initialize_separated(run_id, _synthetic_roster(), str(delivery), synthetic=True)
        replay = _initialize_separated(run_id, _synthetic_roster(), str(delivery), synthetic=True)
        paths = _paths(run_id)
        initial_envelope = load_json(delivery / "coder_a" / "capability-envelope.json")
        raw_token = initial_envelope["role_session_token"]
        server, server_metadata = _make_secure_collection_server(
            run_id, "coder_a", str(delivery / "coder_a" / "capability-envelope.json"), 0
        )
        exchange = _http_exchange(server, raw_token)
        spent = load_json(delivery / "coder_a" / "capability-envelope.json")
        ledger = load_json(paths["ledger_coder_a"])
        issuance = validate_participant_capability_issuance(run_id)
        files = [
            paths["m57_5_intent"], paths["m57_5_commitment"], paths["m57_5_claim_coder_a"],
            *(delivery / role / "capability-envelope.json" for role in ROLE_SLOTS),
        ]
        artifact_bytes = {
            path.name if path.parent == delivery else str(path.resolve().relative_to(root_resolved)): path.stat().st_size
            for path in files
        }
        public_text = canonical(receipt) + canonical(replay) + canonical(server_metadata)
        value = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "synthetic_separate_capability_and_token_free_browser_round_trip_completed",
            "run_id": run_id,
            "contract_hash": validate_contract()["contract_hash"],
            "data_kind": collection_m57.SYNTHETIC_KIND,
            "role_envelope_count": 3,
            "delivery_root_mode": format(_mode_bits(delivery), "04o"),
            "role_directory_modes": [format(_mode_bits(delivery / role), "04o") for role in ROLE_SLOTS],
            "unclaimed_envelope_file_modes": [
                format(_mode_bits(delivery / role / "capability-envelope.json"), "04o") for role in ROLE_SLOTS
            ],
            "raw_role_tokens_returned_by_public_receipt": _contains_raw_role_token(receipt),
            "raw_role_token_occurrences_in_public_receipt": public_text.count(raw_token),
            "completed_replay_status": replay["status"],
            "claimed_role_count": issuance["claimed_role_count"],
            "claim_receipt_count": int(paths["m57_5_claim_coder_a"].exists()),
            "spent_envelope_raw_role_token_present": _contains_raw_role_token(spent),
            "browser_first_status": exchange["first_status"],
            "browser_post_status": exchange["post_status"],
            "http_only_cookie_present": "HttpOnly" in exchange["set_cookie"],
            "same_site_strict_cookie_present": "SameSite=Strict" in exchange["set_cookie"],
            "secure_cookie_flag_present": "; Secure" in exchange["set_cookie"],
            "raw_role_token_surface_occurrences": exchange["raw_role_token_surface_occurrences"],
            "role_token_equals_cookie_or_csrf": exchange["role_token_equals_cookie_or_csrf"],
            "redirect_locations_token_free": "token" not in exchange["location"].lower() and "token" not in exchange["post_location"].lower(),
            "html_contains_role_token_field": 'name="token"' in exchange["body"],
            "coder_revision_count": ledger["revision_count"],
            "coder_source_view_count": len(ledger["source_views"]),
            "issuance_valid_after_claim_and_save": issuance["valid"],
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
            "elapsed_seconds": perf_counter() - start,
            "artifact_utf8_bytes": artifact_bytes,
            "claim_boundary": load_contract()["claim_boundary"],
        }
        value["rehearsal_hash"] = digest(value)
        return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "synthetic_separate_capability_and_token_free_browser_round_trip_completed":
        errors.append("rehearsal.schema_or_status")
    if value.get("rehearsal_hash") != digest(_hashless(value, "rehearsal_hash")):
        errors.append("rehearsal.hash")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    expected = {
        "role_envelope_count": 3,
        "delivery_root_mode": "0700",
        "role_directory_modes": ["0700", "0700", "0700"],
        "unclaimed_envelope_file_modes": ["0600", "0600", "0600"],
        "raw_role_tokens_returned_by_public_receipt": False,
        "raw_role_token_occurrences_in_public_receipt": 0,
        "completed_replay_status": "m57_5_existing_issuance_revalidated",
        "claimed_role_count": 1,
        "claim_receipt_count": 1,
        "spent_envelope_raw_role_token_present": False,
        "browser_first_status": 303,
        "browser_post_status": 303,
        "http_only_cookie_present": True,
        "same_site_strict_cookie_present": True,
        "secure_cookie_flag_present": False,
        "raw_role_token_surface_occurrences": 0,
        "role_token_equals_cookie_or_csrf": False,
        "redirect_locations_token_free": True,
        "html_contains_role_token_field": False,
        "coder_revision_count": 1,
        "coder_source_view_count": 1,
        "issuance_valid_after_claim_and_save": True,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    for name, expected_value in expected.items():
        if value.get(name) != expected_value:
            errors.append(f"rehearsal.{name}")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.5 rehearsal: " + "; ".join(report["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    upstream = collection_m57.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "capability_wrapper_ready_but_no_real_participant_capability_issued",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "real_m57_5_issuance_commitments": 0,
        "real_m57_5_claim_receipts": 0,
        "real_component_rows": 0,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def render_dashboard(rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    report = validate_rehearsal(rehearsal)
    if not report["valid"]:
        raise PermissionError("invalid M57.5 rehearsal cannot be rendered")
    counts = audit["counts"]
    total_bytes = sum(rehearsal["artifact_utf8_bytes"].values())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.5 角色憑證分流</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131a;color:#f4fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1160px;margin:auto;padding:26px}}section{{border:1px solid #335f6d;border-radius:20px;background:#0d222a;padding:22px;margin-bottom:17px;overflow:hidden}}.hero{{background:linear-gradient(135deg,#123b47,#493251)}}h1{{font-size:clamp(30px,5vw,46px);margin:10px 0}}p{{color:#c7dbe3;line-height:1.62}}.deny{{display:inline-block;background:#742b3a;color:#ffe6eb;padding:8px 12px;border-radius:999px;font-weight:850}}.flow{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}}.card{{min-width:0;border:1px solid #456b78;border-radius:15px;background:#08191f;padding:14px}}.card b,.card span{{display:block;overflow-wrap:anywhere}}.card b{{color:#80e5c3}}.card span{{color:#bdd2db;margin-top:7px;line-height:1.42}}.danger{{border-color:#c36b78}}.safe{{border-color:#58bd9d}}.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}.metric{{text-align:center}}.metric strong{{display:block;font-size:28px;color:#82e4c3}}.boundary{{border-left:6px solid #dfa652;background:#292016}}@media(max-width:950px){{.flow,.metrics{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:620px){{.flow,.metrics{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="deny">REAL PARTICIPANT CAPABILITIES 0 · FORMAL M57 DENIED</span><h1>M57.5 · 三個角色，不共用一把鑰匙</h1><p>M57.4 的證據規則完全不變；這一層只把三個角色憑證分開交付，並讓瀏覽器永遠看不到真正的 M57.4 bearer token。</p></section>
<section><h2>修改前後</h2><div class="flow"><div class="card danger"><b>舊入口</b><span>同一caller拿到3個tokens<br>token進argv/URL/form</span></div><div class="card safe"><b>① 分開信封</b><span>3個0700 role dirs<br>0600 envelope</span></div><div class="card safe"><b>② 一次claim</b><span>receipt後scrub raw token<br>restart刻意fail closed</span></div><div class="card safe"><b>③ 本機session</b><span>HttpOnly + SameSite=Strict<br>獨立CSRF</span></div><div class="card"><b>④ 原M57.4 ledger</b><span>source/view/save規則不變<br>outcome仍為0</span></div></div></section>
<section><h2>隔離rehearsal真的做了什麼</h2><div class="metrics"><div class="card metric"><strong>3</strong><span>separate envelopes</span></div><div class="card metric"><strong>1</strong><span>one-time claim</span></div><div class="card metric"><strong>303</strong><span>cookie handshake</span></div><div class="card metric"><strong>1</strong><span>saved coder row</span></div><div class="card metric"><strong>0</strong><span>token surface hits</span></div><div class="card metric"><strong>0</strong><span>outcome/model</span></div></div><p>本機full-sync artifacts共 {total_bytes:,} bytes；一次synthetic issuance→claim→browser POST為 {rehearsal['elapsed_seconds']:.3f}s。這不是三位真人，也不是網路TLS或正式研究結果。</p></section>
<section class="boundary"><h2>這一頁沒有偷偷升級證據</h2><p>現在能證明：public receipt沒有raw token、三份信封權限分開、claim一次後scrub、URL／HTML／cookie沒有M57.4 token、cookie/CSRF gate可完成原ledger的一筆save。仍不能證明：三個路徑是三位physical humans、同macOS user下可抵抗惡意讀檔、component label正確或Equation V1成立。V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18，real rows 0/30，M58 denied。</p></section></main></body></html>"""


def serve_dashboard(port: int) -> None:
    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/dashboard"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="M57.5 separated participant capabilities")
    sub = parser.add_subparsers(dest="command", required=True)
    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--port", type=int, default=7928)
    collect = sub.add_parser("collect-secure")
    collect.add_argument("--run-id", required=True)
    collect.add_argument("--role", choices=ROLE_SLOTS, required=True)
    collect.add_argument("--envelope", required=True)
    collect.add_argument("--port", type=int, required=True)
    sub.add_parser("rehearsal")
    sub.add_parser("audit")
    args = parser.parse_args()
    if args.command == "dashboard":
        serve_dashboard(args.port)
    elif args.command == "collect-secure":
        serve_secure_collection(args.run_id, args.role, args.envelope, args.port)
    elif args.command == "rehearsal":
        print(json.dumps(build_engineering_rehearsal(), ensure_ascii=False, indent=2))
    elif args.command == "audit":
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
