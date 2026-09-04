#!/usr/bin/env python3
"""M57.6 participant-secret-bound encrypted recovery for M57.5 collectors.

The public collector command never accepts a secret as an argument.  It reads the
secret from a TTY, keeps it in process memory, and persists only an Scrypt +
AES-GCM protected role capability.  This is a bounded local reliability overlay;
it does not create participant identity or scientific evidence.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import getpass
from hashlib import sha256
import hmac
import html
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any
import urllib.parse

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_5_participant_capability_issuance as capability_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_6_crash_recoverable_participant_capability_v1.json"
RESULT_PATH = ROOT / "analysis/m57_6_crash_recoverable_participant_capability_rehearsal_2026-09-05.json"
LIVE_AUDIT_PATH = ROOT / "analysis/m57_6_crash_recoverable_participant_capability_live_audit_2026-09-05.json"

INTENT_SCHEMA = "uruha_m57_6_recovery_intent_v1"
VAULT_SCHEMA = "uruha_m57_6_encrypted_role_capability_v1"
ACTIVATION_SCHEMA = "uruha_m57_6_recovery_activation_commitment_v1"
REHEARSAL_SCHEMA = "uruha_m57_6_crash_recovery_rehearsal_v1"
COOKIE_NAME = "m57_6_local_session"


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
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _hashless(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != field}


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: Any, *, expected_length: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise ValueError("invalid base64 field")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid base64 field") from exc
    if expected_length is not None and len(decoded) != expected_length:
        raise ValueError("invalid decoded length")
    return decoded


def _mode_bits(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _cookie_value(header: str | None) -> str:
    jar = cookies.SimpleCookie()
    try:
        jar.load(header or "")
    except cookies.CookieError:
        return ""
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel else ""


def _load_crypto_classes() -> tuple[type[Any], type[Any], type[BaseException]]:
    contract = load_contract()
    expected = contract["accepted_crypto_backend"]["exact_version"]
    try:
        actual = importlib_metadata.version("cryptography")
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except (ImportError, importlib_metadata.PackageNotFoundError) as exc:
        raise RuntimeError("M57.6 requires the prospectively frozen cryptography backend") from exc
    if actual != expected:
        raise RuntimeError(f"M57.6 cryptography version drift: expected {expected}, got {actual}")
    return AESGCM, Scrypt, InvalidTag


def audit_crypto_backend() -> dict[str, Any]:
    """Report whether the current interpreter can execute the frozen crypto path."""
    expected = load_contract()["accepted_crypto_backend"]["exact_version"]
    try:
        actual = importlib_metadata.version("cryptography")
        _load_crypto_classes()
    except (RuntimeError, importlib_metadata.PackageNotFoundError) as exc:
        return {
            "available": False,
            "expected_cryptography_version": expected,
            "actual_cryptography_version": None,
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "error": str(exc),
        }
    return {
        "available": True,
        "expected_cryptography_version": expected,
        "actual_cryptography_version": actual,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "kdf": "Scrypt",
        "aead": "AESGCM",
        "error": None,
    }


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    value = contract or load_contract()
    errors: list[str] = []
    expected_top = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "accepted_crypto_backend", "recovery_secret", "vault", "state_machine",
        "browser_session", "public_functions", "preserved_boundaries", "claim_boundary",
    }
    if set(value) != expected_top:
        errors.append("contract.fields")
    if value.get("schema") != "uruha_m57_6_crash_recoverable_participant_capability_contract_v1":
        errors.append("contract.schema")
    if value.get("version") != "1.0.0":
        errors.append("contract.version")
    if value.get("single_changed_variable") != "participant_owned_encrypted_post_claim_restart_recovery":
        errors.append("contract.single_changed_variable")
    for relative, expected_hash in value.get("frozen_dependencies", {}).items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"frozen_dependency:{relative}")
    crypto = value.get("accepted_crypto_backend", {})
    exact_crypto = {
        "distribution": "cryptography", "exact_version": "50.0.1", "kdf": "Scrypt",
        "kdf_n": 32768, "kdf_r": 8, "kdf_p": 1, "derived_key_bytes": 32,
        "salt_bytes": 16, "aead": "AESGCM", "aead_key_bits": 256, "nonce_bytes": 12,
        "ciphertext_includes_authentication_tag": True,
        "missing_or_version_drift_fails_closed": True,
        "dependency_installed_by_this_milestone": False,
    }
    if crypto != exact_crypto:
        errors.append("contract.crypto")
    secret = value.get("recovery_secret", {})
    required_secret = {
        "public_cli_uses_tty_getpass": True,
        "first_activation_requires_confirmation": True,
        "minimum_utf8_bytes": 20,
        "maximum_utf8_bytes": 1024,
        "accepted_from_argv": False,
        "accepted_from_environment": False,
        "accepted_from_browser": False,
        "persisted_in_file_or_log": False,
        "raw_secret_returned_in_public_metadata": False,
        "python_memory_zeroization_guaranteed": False,
    }
    if secret != required_secret:
        errors.append("contract.recovery_secret")
    expected_sections = {
        "vault": {
            "one_encrypted_vault_per_claimed_role": True,
            "vault_file_mode": "0600",
            "vault_binds_run_role_participant_m57_5_commitment_token_hash_and_envelope_hash": True,
            "vault_full_sync_precedes_m57_5_claim": True,
            "raw_role_token_in_vault_json": False,
            "raw_recovery_secret_in_vault_json": False,
            "wrong_secret_or_tamper_error_is_indistinguishable": True,
        },
        "state_machine": {
            "full_sync_intent_precedes_vault": True,
            "vault_before_claim_restart_supported": True,
            "claim_before_activation_commit_restart_supported": True,
            "claim_receipt_before_envelope_scrub_repair_supported": True,
            "identical_active_restart_supported": True,
            "changed_run_role_path_or_crypto_parameters_allowed": False,
            "spent_envelope_without_valid_vault_allowed": False,
            "outcome_state_absence_revalidated_before_every_recovery": True,
        },
        "browser_session": {
            "uses_independent_m57_5_style_cookie_and_csrf": True,
            "role_token_in_argv": False,
            "role_token_in_url_or_query": False,
            "role_token_in_html_or_form": False,
            "role_token_in_cookie": False,
            "recovery_secret_in_argv": False,
            "recovery_secret_in_url_or_query": False,
            "recovery_secret_in_html_or_form": False,
            "recovery_secret_in_cookie": False,
            "loopback_plain_http_claims_tls": False,
        },
        "preserved_boundaries": {
            "m57_5_frozen_files_changed": False,
            "m57_4_or_m57_5_evidence_semantics_changed": False,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "production_memory_write": False,
            "external_deployment": False,
            "synthetic_fixture_may_become_formal": False,
            "m58_authorized": False,
        },
    }
    for section, expected in expected_sections.items():
        if value.get(section) != expected:
            errors.append(f"contract.{section}")
    public = value.get("public_functions", {})
    if public != {
        "audit_crypto_backend": [],
        "validate_recoverable_capability": ["run_id", "role_slot"],
        "serve_recoverable_collection": ["run_id", "role_slot", "envelope_path", "port"],
    }:
        errors.append("contract.public_functions")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(value),
        "binding_count": len(value.get("frozen_dependencies", {})),
    }


def _paths(run_id: str, role_slot: str) -> dict[str, Path]:
    upstream = capability_m57._paths(run_id)
    return {
        **upstream,
        "m57_6_intent": upstream["commitments"] / f"m57_6_{role_slot}_recovery_intent.json",
        "m57_6_activation": upstream["commitments"] / f"m57_6_{role_slot}_recovery_activation.json",
    }


def _load_upstream(run_id: str, role_slot: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Path], Path]:
    if role_slot not in capability_m57.ROLE_SLOTS:
        raise ValueError("unknown M57.6 role slot")
    single_writer_m56._validate_permitted_run(run_id)
    mode, context, paths = capability_m57._load_m57_4_mode(run_id)
    del context
    capability_m57.collection_m57._no_outcome(paths, "M57.6 capability recovery")
    if not paths["m57_5_intent"].is_file() or not paths["m57_5_commitment"].is_file():
        raise FileNotFoundError("complete M57.5 issuance is required")
    m57_5_intent = load_json(paths["m57_5_intent"])
    commitment = load_json(paths["m57_5_commitment"])
    errors = capability_m57._validate_intent(m57_5_intent, run_id)
    errors.extend(capability_m57._validate_commitment(commitment, run_id, mode, m57_5_intent))
    if errors:
        raise PermissionError("invalid M57.5 issuance for M57.6: " + "; ".join(errors))
    row = commitment["roles"][role_slot]
    envelope_path = Path(row["envelope_path"])
    if not envelope_path.is_file() or envelope_path.is_symlink():
        raise PermissionError("M57.6 role envelope must be a regular file")
    if _mode_bits(envelope_path) != 0o600 or _mode_bits(envelope_path.parent) != 0o700:
        raise PermissionError("M57.6 role envelope permissions drifted")
    return mode, commitment, row, _paths(run_id, role_slot), envelope_path


def _validate_secret(secret: str) -> bytes:
    if not isinstance(secret, str):
        raise TypeError("M57.6 recovery secret must be text")
    encoded = secret.encode("utf-8")
    policy = load_contract()["recovery_secret"]
    if len(encoded) < policy["minimum_utf8_bytes"] or len(encoded) > policy["maximum_utf8_bytes"]:
        raise ValueError("M57.6 recovery secret does not satisfy frozen byte-length policy")
    if "\x00" in secret or "\n" in secret or "\r" in secret:
        raise ValueError("M57.6 recovery secret contains a forbidden control character")
    return encoded


def _aad_payload(
    run_id: str, role_slot: str, row: dict[str, Any], commitment: dict[str, Any], intent: dict[str, Any],
) -> dict[str, Any]:
    crypto = load_contract()["accepted_crypto_backend"]
    return {
        "schema": "uruha_m57_6_role_capability_aad_v1",
        "version": "1.0.0",
        "run_id": run_id,
        "role_slot": role_slot,
        "participant_pseudonym": row["participant_pseudonym"],
        "m57_5_contract_hash": load_contract()["frozen_dependencies"]["configs/m57_5_participant_capability_issuance_v1.json"],
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "session_token_sha256": row["session_token_sha256"],
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "kdf": {
            "name": crypto["kdf"], "n": crypto["kdf_n"], "r": crypto["kdf_r"],
            "p": crypto["kdf_p"], "length": crypto["derived_key_bytes"],
            "salt_b64": intent["salt_b64"],
        },
        "aead": {"name": crypto["aead"], "nonce_b64": intent["nonce_b64"]},
    }


def _derive_key(secret_bytes: bytes, salt: bytes) -> bytes:
    _AESGCM, Scrypt, _InvalidTag = _load_crypto_classes()
    crypto = load_contract()["accepted_crypto_backend"]
    return Scrypt(
        salt=salt, length=crypto["derived_key_bytes"], n=crypto["kdf_n"],
        r=crypto["kdf_r"], p=crypto["kdf_p"],
    ).derive(secret_bytes)


def _validate_intent(
    value: dict[str, Any], run_id: str, role_slot: str, row: dict[str, Any], commitment: dict[str, Any], envelope_path: Path,
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "contract_hash",
        "m57_5_commitment_hash", "session_token_sha256", "initial_envelope_sha256",
        "envelope_path", "kdf", "aead", "salt_b64", "nonce_b64", "created_at_utc",
        "target_outcome_access_count", "model_call_count", "formal_evidence_created",
        "m58_authorized", "intent_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["intent.fields"]
    errors: list[str] = []
    contract = load_contract()
    crypto = contract["accepted_crypto_backend"]
    expected = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "recovery_parameters_full_sync_before_m57_5_claim",
        "run_id": run_id,
        "role_slot": role_slot,
        "contract_hash": digest(contract),
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "session_token_sha256": row["session_token_sha256"],
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "envelope_path": str(envelope_path),
        "kdf": {"name": "Scrypt", "n": 32768, "r": 8, "p": 1, "length": 32},
        "aead": {"name": "AESGCM", "key_bits": 256},
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    del crypto
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"intent.{name}")
    try:
        _b64decode(value.get("salt_b64"), expected_length=16)
        _b64decode(value.get("nonce_b64"), expected_length=12)
    except ValueError:
        errors.append("intent.randomness")
    if not _valid_timestamp(value.get("created_at_utc")):
        errors.append("intent.timestamp")
    if value.get("intent_hash") != digest(_hashless(value, "intent_hash")):
        errors.append("intent.hash")
    return errors


def _validate_vault(
    value: dict[str, Any], run_id: str, role_slot: str, row: dict[str, Any], commitment: dict[str, Any], intent: dict[str, Any],
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "contract_hash",
        "intent_hash", "m57_5_commitment_hash", "session_token_sha256",
        "initial_envelope_sha256", "kdf", "aead", "salt_b64", "nonce_b64",
        "aad_sha256", "ciphertext_b64", "created_at_utc", "raw_role_token_present",
        "raw_recovery_secret_present", "vault_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["vault.fields"]
    errors: list[str] = []
    expected = {
        "schema": VAULT_SCHEMA,
        "version": "1.0.0",
        "status": "encrypted_role_capability_full_sync_before_claim",
        "run_id": run_id,
        "role_slot": role_slot,
        "contract_hash": digest(load_contract()),
        "intent_hash": intent.get("intent_hash"),
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "session_token_sha256": row["session_token_sha256"],
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "kdf": intent.get("kdf"),
        "aead": intent.get("aead"),
        "salt_b64": intent.get("salt_b64"),
        "nonce_b64": intent.get("nonce_b64"),
        "raw_role_token_present": False,
        "raw_recovery_secret_present": False,
    }
    for name, child in expected.items():
        if value.get(name) != child:
            errors.append(f"vault.{name}")
    try:
        aad = canonical(_aad_payload(run_id, role_slot, row, commitment, intent)).encode("utf-8")
    except (KeyError, TypeError, ValueError):
        errors.append("vault.aad_inputs")
    else:
        if value.get("aad_sha256") != sha256(aad).hexdigest():
            errors.append("vault.aad")
    try:
        ciphertext = _b64decode(value.get("ciphertext_b64"))
        if len(ciphertext) < 17:
            errors.append("vault.ciphertext_length")
    except ValueError:
        errors.append("vault.ciphertext")
    if not _valid_timestamp(value.get("created_at_utc")):
        errors.append("vault.timestamp")
    if value.get("vault_hash") != digest(_hashless(value, "vault_hash")):
        errors.append("vault.hash")
    if capability_m57._contains_raw_role_token(value):
        errors.append("vault.raw_token_field")
    return errors


def _validate_activation(
    value: dict[str, Any], run_id: str, role_slot: str, commitment: dict[str, Any],
    intent: dict[str, Any], vault: dict[str, Any], vault_path: Path, claim: dict[str, Any],
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "role_slot", "contract_hash",
        "m57_5_commitment_hash", "m57_5_claim_hash", "intent_hash", "vault_hash",
        "vault_file_sha256", "spent_envelope_sha256", "activated_at_utc",
        "target_outcome_access_count", "model_call_count", "formal_evidence_created",
        "m58_authorized", "activation_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["activation.fields"]
    expected = {
        "schema": ACTIVATION_SCHEMA,
        "version": "1.0.0",
        "status": "participant_secret_bound_capability_restartable",
        "run_id": run_id,
        "role_slot": role_slot,
        "contract_hash": digest(load_contract()),
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "m57_5_claim_hash": claim.get("claim_hash"),
        "intent_hash": intent.get("intent_hash"),
        "vault_hash": vault.get("vault_hash"),
        "vault_file_sha256": sha256_file(vault_path),
        "spent_envelope_sha256": claim.get("spent_envelope_sha256"),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    errors = [f"activation.{name}" for name, child in expected.items() if value.get(name) != child]
    if not _valid_timestamp(value.get("activated_at_utc")):
        errors.append("activation.timestamp")
    if value.get("activation_hash") != digest(_hashless(value, "activation_hash")):
        errors.append("activation.hash")
    if capability_m57._contains_raw_role_token(value):
        errors.append("activation.raw_token_field")
    return errors


def _new_or_existing_intent(
    run_id: str, role_slot: str, row: dict[str, Any], commitment: dict[str, Any], paths: dict[str, Path], envelope_path: Path,
) -> dict[str, Any]:
    if paths["m57_6_intent"].exists():
        intent = load_json(paths["m57_6_intent"])
        errors = _validate_intent(intent, run_id, role_slot, row, commitment, envelope_path)
        if errors:
            raise PermissionError("invalid existing M57.6 recovery intent: " + "; ".join(errors))
        return intent
    crypto = load_contract()["accepted_crypto_backend"]
    intent = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "recovery_parameters_full_sync_before_m57_5_claim",
        "run_id": run_id,
        "role_slot": role_slot,
        "contract_hash": digest(load_contract()),
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "session_token_sha256": row["session_token_sha256"],
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "envelope_path": str(envelope_path),
        "kdf": {"name": crypto["kdf"], "n": crypto["kdf_n"], "r": crypto["kdf_r"], "p": crypto["kdf_p"], "length": crypto["derived_key_bytes"]},
        "aead": {"name": crypto["aead"], "key_bits": crypto["aead_key_bits"]},
        "salt_b64": _b64encode(secrets.token_bytes(crypto["salt_bytes"])),
        "nonce_b64": _b64encode(secrets.token_bytes(crypto["nonce_bytes"])),
        "created_at_utc": _utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    intent["intent_hash"] = digest(intent)
    durable_m56._durable_atomic_write_json(paths["m57_6_intent"], intent, exclusive=True)
    return intent


def _vault_path(envelope_path: Path) -> Path:
    return envelope_path.parent / "capability-vault-m57-6.json"


def _encrypt_or_open_vault(
    run_id: str, role_slot: str, secret: str, mode: dict[str, Any], commitment: dict[str, Any],
    row: dict[str, Any], paths: dict[str, Path], envelope_path: Path,
) -> tuple[str, dict[str, Any], dict[str, Any], Path, bool]:
    del mode
    secret_bytes = _validate_secret(secret)
    intent = _new_or_existing_intent(run_id, role_slot, row, commitment, paths, envelope_path)
    vault_path = _vault_path(envelope_path)
    created = False
    if vault_path.exists():
        if not vault_path.is_file() or vault_path.is_symlink() or _mode_bits(vault_path) != 0o600:
            raise PermissionError("M57.6 encrypted vault path or permissions are invalid")
        vault = load_json(vault_path)
        errors = _validate_vault(vault, run_id, role_slot, row, commitment, intent)
        if errors:
            raise PermissionError("invalid M57.6 encrypted vault: " + "; ".join(errors))
    else:
        envelope = load_json(envelope_path)
        envelope_errors = capability_m57._validate_envelope(envelope, role_slot, capability_m57._load_m57_4_mode(run_id)[0])
        if envelope_errors or sha256_file(envelope_path) != row["initial_envelope_sha256"]:
            raise PermissionError("M57.6 cannot create a missing vault after the plaintext envelope is unavailable")
        role_token = envelope["role_session_token"]
        salt = _b64decode(intent["salt_b64"], expected_length=16)
        nonce = _b64decode(intent["nonce_b64"], expected_length=12)
        aad = canonical(_aad_payload(run_id, role_slot, row, commitment, intent)).encode("utf-8")
        AESGCM, _Scrypt, _InvalidTag = _load_crypto_classes()
        key = _derive_key(secret_bytes, salt)
        ciphertext = AESGCM(key).encrypt(nonce, role_token.encode("utf-8"), aad)
        vault = {
            "schema": VAULT_SCHEMA,
            "version": "1.0.0",
            "status": "encrypted_role_capability_full_sync_before_claim",
            "run_id": run_id,
            "role_slot": role_slot,
            "contract_hash": digest(load_contract()),
            "intent_hash": intent["intent_hash"],
            "m57_5_commitment_hash": commitment["commitment_hash"],
            "session_token_sha256": row["session_token_sha256"],
            "initial_envelope_sha256": row["initial_envelope_sha256"],
            "kdf": intent["kdf"],
            "aead": intent["aead"],
            "salt_b64": intent["salt_b64"],
            "nonce_b64": intent["nonce_b64"],
            "aad_sha256": sha256(aad).hexdigest(),
            "ciphertext_b64": _b64encode(ciphertext),
            "created_at_utc": _utc_now(),
            "raw_role_token_present": False,
            "raw_recovery_secret_present": False,
        }
        vault["vault_hash"] = digest(vault)
        durable_m56._durable_atomic_write_json(vault_path, vault, exclusive=True)
        os.chmod(vault_path, 0o600)
        created = True
    salt = _b64decode(vault["salt_b64"], expected_length=16)
    nonce = _b64decode(vault["nonce_b64"], expected_length=12)
    aad = canonical(_aad_payload(run_id, role_slot, row, commitment, intent)).encode("utf-8")
    AESGCM, _Scrypt, InvalidTag = _load_crypto_classes()
    key = _derive_key(secret_bytes, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, _b64decode(vault["ciphertext_b64"]), aad)
        role_token = plaintext.decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise PermissionError("incorrect M57.6 recovery secret or tampered encrypted vault") from exc
    if sha256(role_token.encode("utf-8")).hexdigest() != row["session_token_sha256"]:
        raise PermissionError("incorrect M57.6 recovery secret or tampered encrypted vault")
    return role_token, intent, vault, vault_path, created


def _repair_claim_before_scrub(
    run_id: str, role_slot: str, role_token: str, row: dict[str, Any], paths: dict[str, Path], envelope_path: Path,
) -> dict[str, Any]:
    claim_path = paths[f"m57_5_claim_{role_slot}"]
    if not claim_path.is_file():
        raise FileNotFoundError("M57.5 claim is absent")
    claim = load_json(claim_path)
    errors = capability_m57._validate_claim(claim, role_slot, row)
    if claim.get("run_id") != run_id:
        errors.append("claim.run_id")
    if errors:
        raise PermissionError("invalid M57.5 claim during M57.6 recovery: " + "; ".join(errors))
    envelope = load_json(envelope_path)
    spent_errors = capability_m57._validate_spent_envelope(
        envelope, role_slot, run_id, row["initial_envelope_sha256"]
    )
    if not spent_errors and sha256_file(envelope_path) == claim["spent_envelope_sha256"]:
        return claim
    mode = capability_m57._load_m57_4_mode(run_id)[0]
    raw_errors = capability_m57._validate_envelope(envelope, role_slot, mode)
    if raw_errors or sha256_file(envelope_path) != row["initial_envelope_sha256"]:
        raise PermissionError("M57.6 found neither the committed spent envelope nor the exact initial envelope")
    if not hmac.compare_digest(envelope["role_session_token"], role_token):
        raise PermissionError("M57.6 recovered token does not match the initial envelope")
    spent = {
        "schema": capability_m57.SPENT_ENVELOPE_SCHEMA,
        "version": "1.0.0",
        "status": "claimed_and_raw_role_token_removed",
        "run_id": run_id,
        "role_slot": role_slot,
        "initial_envelope_sha256": row["initial_envelope_sha256"],
        "claimed_at_utc": claim["claimed_at_utc"],
        "raw_role_token_present": False,
    }
    spent["spent_hash"] = digest(spent)
    spent_bytes = (json.dumps(spent, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if sha256(spent_bytes).hexdigest() != claim["spent_envelope_sha256"]:
        raise PermissionError("M57.6 cannot reproduce the already committed spent envelope")
    durable_m56._durable_atomic_write_json(envelope_path, spent)
    os.chmod(envelope_path, 0o600)
    return claim


def _write_or_validate_activation(
    run_id: str, role_slot: str, commitment: dict[str, Any], intent: dict[str, Any], vault: dict[str, Any],
    vault_path: Path, claim: dict[str, Any], paths: dict[str, Path],
) -> tuple[dict[str, Any], bool]:
    if paths["m57_6_activation"].exists():
        activation = load_json(paths["m57_6_activation"])
        errors = _validate_activation(
            activation, run_id, role_slot, commitment, intent, vault, vault_path, claim
        )
        if errors:
            raise PermissionError("invalid existing M57.6 activation: " + "; ".join(errors))
        return activation, False
    activation = {
        "schema": ACTIVATION_SCHEMA,
        "version": "1.0.0",
        "status": "participant_secret_bound_capability_restartable",
        "run_id": run_id,
        "role_slot": role_slot,
        "contract_hash": digest(load_contract()),
        "m57_5_commitment_hash": commitment["commitment_hash"],
        "m57_5_claim_hash": claim["claim_hash"],
        "intent_hash": intent["intent_hash"],
        "vault_hash": vault["vault_hash"],
        "vault_file_sha256": sha256_file(vault_path),
        "spent_envelope_sha256": claim["spent_envelope_sha256"],
        "activated_at_utc": _utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    activation["activation_hash"] = digest(activation)
    durable_m56._durable_atomic_write_json(paths["m57_6_activation"], activation, exclusive=True)
    return activation, True


def _activate_or_recover(
    run_id: str, role_slot: str, envelope_path: str, recovery_secret: str,
) -> tuple[str, dict[str, Any]]:
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise PermissionError("invalid M57.6 contract: " + "; ".join(contract_report["errors"]))
    backend = audit_crypto_backend()
    if not backend["available"]:
        raise RuntimeError(backend["error"])
    supplied = Path(envelope_path).resolve(strict=False)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        mode, commitment, row, paths, expected_envelope = _load_upstream(run_id, role_slot)
        if supplied != expected_envelope:
            raise PermissionError("M57.6 envelope does not belong to requested run and role")
        role_token, intent, vault, vault_path, vault_created = _encrypt_or_open_vault(
            run_id, role_slot, recovery_secret, mode, commitment, row, paths, expected_envelope
        )
    claim_path = paths[f"m57_5_claim_{role_slot}"]
    claim_created = False
    if not claim_path.exists():
        try:
            claimed_token, claim = capability_m57._claim_capability(
                run_id, role_slot, str(expected_envelope)
            )
            claim_created = True
            if not hmac.compare_digest(claimed_token, role_token):
                raise PermissionError("M57.6 vault token and M57.5 claim token disagree")
        except PermissionError as exc:
            if "already claimed" not in str(exc):
                raise
            claim = _repair_claim_before_scrub(
                run_id, role_slot, role_token, row, paths, expected_envelope
            )
    else:
        claim = _repair_claim_before_scrub(
            run_id, role_slot, role_token, row, paths, expected_envelope
        )
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        capability_m57.collection_m57._no_outcome(paths, "M57.6 activation commitment")
        upstream_report = capability_m57.validate_participant_capability_issuance(run_id)
        if not upstream_report["valid"]:
            raise PermissionError("invalid M57.5 issuance after M57.6 claim: " + "; ".join(upstream_report["errors"]))
        activation, activation_created = _write_or_validate_activation(
            run_id, role_slot, commitment, intent, vault, vault_path, claim, paths
        )
    validation = validate_recoverable_capability(run_id, role_slot)
    if not validation["valid"]:
        raise AssertionError("completed M57.6 recovery state invalid: " + "; ".join(validation["errors"]))
    return role_token, {
        "run_id": run_id,
        "role_slot": role_slot,
        "status": "m57_6_participant_capability_active",
        "vault_created": vault_created,
        "claim_created": claim_created,
        "activation_created": activation_created,
        "activation_hash": activation["activation_hash"],
        "raw_role_token_returned": False,
        "raw_recovery_secret_returned": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def validate_recoverable_capability(run_id: str, role_slot: str) -> dict[str, Any]:
    """Validate durable recovery state without accepting a secret or decrypting the capability."""
    errors: list[str] = []
    try:
        _mode, commitment, row, paths, envelope_path = _load_upstream(run_id, role_slot)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        return {"valid": False, "errors": [f"upstream:{exc}"], "run_id": run_id, "role_slot": role_slot}
    intent_path = paths["m57_6_intent"]
    activation_path = paths["m57_6_activation"]
    vault_path = _vault_path(envelope_path)
    for name, path in (("intent", intent_path), ("vault", vault_path), ("activation", activation_path)):
        if not path.is_file() or path.is_symlink():
            errors.append(f"{name}.absent_or_symlink")
    if errors:
        return {"valid": False, "errors": errors, "run_id": run_id, "role_slot": role_slot}
    if _mode_bits(vault_path) != 0o600:
        errors.append("vault.permissions")
    try:
        intent = load_json(intent_path)
        vault = load_json(vault_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "valid": False,
            "errors": [f"recovery_state_json:{exc}"],
            "run_id": run_id,
            "role_slot": role_slot,
        }
    errors.extend(_validate_intent(intent, run_id, role_slot, row, commitment, envelope_path))
    errors.extend(_validate_vault(vault, run_id, role_slot, row, commitment, intent))
    claim_path = paths[f"m57_5_claim_{role_slot}"]
    if not claim_path.is_file():
        errors.append("claim.absent")
        claim = {}
    else:
        try:
            claim = load_json(claim_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "valid": False,
                "errors": [f"claim_json:{exc}"],
                "run_id": run_id,
                "role_slot": role_slot,
            }
        errors.extend(capability_m57._validate_claim(claim, role_slot, row))
        if claim.get("run_id") != run_id:
            errors.append("claim.run_id")
    upstream_report = capability_m57.validate_participant_capability_issuance(run_id)
    if not upstream_report["valid"]:
        errors.extend(f"upstream:{child}" for child in upstream_report["errors"])
    try:
        activation = load_json(activation_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "valid": False,
            "errors": [f"activation_json:{exc}"],
            "run_id": run_id,
            "role_slot": role_slot,
        }
    if claim:
        errors.extend(_validate_activation(
            activation, run_id, role_slot, commitment, intent, vault, vault_path, claim
        ))
    durable_state = {"intent": intent, "vault": vault, "activation": activation}
    return {
        "valid": not errors,
        "errors": errors,
        "run_id": run_id,
        "role_slot": role_slot,
        "vault_file_sha256": sha256_file(vault_path),
        "activation_hash": activation.get("activation_hash"),
        "durable_state_contains_raw_role_token_field": capability_m57._contains_raw_role_token(durable_state),
        "durable_state_contains_recovery_secret_field": any(
            isinstance(child, dict) and "recovery_secret" in child
            for child in durable_state.values()
        ),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def _interactive_recovery_secret(run_id: str, role_slot: str) -> str:
    if not sys.stdin.isatty():
        raise PermissionError("M57.6 recovery secret requires an interactive TTY")
    _mode, _commitment, _row, _paths_value, envelope_path = _load_upstream(run_id, role_slot)
    is_new = not _vault_path(envelope_path).exists()
    first = getpass.getpass("M57.6 participant recovery secret: ")
    _validate_secret(first)
    if is_new:
        second = getpass.getpass("Confirm M57.6 participant recovery secret: ")
        if not hmac.compare_digest(first, second):
            raise PermissionError("M57.6 recovery-secret confirmation did not match")
    return first


def _make_recoverable_collection_server(
    run_id: str, role_slot: str, envelope_path: str, port: int, recovery_secret: str,
) -> tuple[ThreadingHTTPServer, dict[str, Any]]:
    role_token, recovery = _activate_or_recover(run_id, role_slot, envelope_path, recovery_secret)
    context = capability_m57.collection_m57._context(run_id)
    order = capability_m57.collection_m57._sample_order(context)
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
                self._headers(303, location=f"/?sample={urllib.parse.quote(sample_id)}", set_cookie=True)
                return
            try:
                body = capability_m57._render_secure_page(
                    run_id, role_slot, role_token, sample_id, csrf_token
                ).encode("utf-8")
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
            if "token" in form or any("secret" in key.lower() for key in form):
                self._send_text("role token and recovery secret form fields forbidden", 400)
                return
            try:
                view = capability_m57.collection_m57.record_component_source_view(
                    run_id, role_slot, role_token, sample_id
                )
                payload = capability_m57.collection_m57._entry_form_payload(role_slot, form, view)
                capability_m57.collection_m57.save_component_evidence_entry(
                    run_id, role_slot, role_token, sample_id, payload
                )
                next_index = min(len(order) - 1, order.index(sample_id) + 1)
                self._headers(303, location=f"/?sample={urllib.parse.quote(order[next_index])}")
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                try:
                    body = capability_m57._render_secure_page(
                        run_id, role_slot, role_token, sample_id, csrf_token, str(exc)
                    ).encode("utf-8")
                    self._headers(400, body)
                except (ValueError, PermissionError, FileNotFoundError):
                    self._send_text(str(exc), 400)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, {
        "run_id": run_id,
        "role_slot": role_slot,
        "port": server.server_address[1],
        "activation_hash": recovery["activation_hash"],
        "restarted_from_encrypted_vault": not recovery["vault_created"],
        "cookie_name": COOKIE_NAME,
        "raw_role_token_returned": False,
        "raw_recovery_secret_returned": False,
    }


def serve_recoverable_collection(run_id: str, role_slot: str, envelope_path: str, port: int) -> None:
    """Start a recoverable local collector; the participant secret is read only from a TTY."""
    recovery_secret = _interactive_recovery_secret(run_id, role_slot)
    server, metadata = _make_recoverable_collection_server(
        run_id, role_slot, envelope_path, port, recovery_secret
    )
    del metadata, recovery_secret
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _synthetic_setup(root: Path, run_id: str) -> tuple[Path, str]:
    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
    import m57_1_preoutcome_diagnostic_commitment as commitment_m57

    materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    delivery = root.resolve() / f"{run_id}-delivery"
    capability_m57._initialize_separated(
        run_id, capability_m57._synthetic_roster(), str(delivery), synthetic=True
    )
    return delivery / "coder_a" / "capability-envelope.json", secrets.token_urlsafe(30)


def build_engineering_rehearsal() -> dict[str, Any]:
    from tempfile import TemporaryDirectory
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
        root = Path(temp)
        run_id = "m576-forged-no-human-recovery"
        envelope, recovery_secret = _synthetic_setup(root, run_id)
        raw_token = load_json(envelope)["role_session_token"]
        first_server, first_metadata = _make_recoverable_collection_server(
            run_id, "coder_a", str(envelope), 0, recovery_secret
        )
        first_server.server_close()
        paths = _paths(run_id, "coder_a")
        vault_path = _vault_path(envelope)
        first_hashes = {
            "intent": sha256_file(paths["m57_6_intent"]),
            "vault": sha256_file(vault_path),
            "claim": sha256_file(paths["m57_5_claim_coder_a"]),
            "activation": sha256_file(paths["m57_6_activation"]),
        }
        second_server, second_metadata = _make_recoverable_collection_server(
            run_id, "coder_a", str(envelope), 0, recovery_secret
        )
        exchange = capability_m57._http_exchange(second_server, raw_token)
        second_hashes = {
            "intent": sha256_file(paths["m57_6_intent"]),
            "vault": sha256_file(vault_path),
            "claim": sha256_file(paths["m57_5_claim_coder_a"]),
            "activation": sha256_file(paths["m57_6_activation"]),
        }
        m57_6_artifacts = [
            paths["m57_6_intent"], vault_path, paths["m57_6_activation"],
        ]
        affected_artifacts = [
            *m57_6_artifacts, paths["m57_5_claim_coder_a"], envelope,
        ]
        validation = validate_recoverable_capability(run_id, "coder_a")
        durable_text = canonical({
            "intent": load_json(paths["m57_6_intent"]),
            "vault": load_json(vault_path),
            "claim": load_json(paths["m57_5_claim_coder_a"]),
            "activation": load_json(paths["m57_6_activation"]),
            "spent": load_json(envelope),
        })
        ledger = load_json(paths["ledger_coder_a"])
        result = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "synthetic_crash_recovery_mechanics_only",
            "run_id": run_id,
            "data_kind": capability_m57.collection_m57.SYNTHETIC_KIND,
            "crypto_backend": {"distribution": "cryptography", "version": "50.0.1", "kdf": "Scrypt", "aead": "AESGCM"},
            "first_start": {
                "vault_created": not first_metadata["restarted_from_encrypted_vault"],
                "activation_hash_present": bool(first_metadata["activation_hash"]),
            },
            "post_process_restart": {
                "accepted_with_same_secret": second_metadata["restarted_from_encrypted_vault"],
                "durable_hashes_unchanged": first_hashes == second_hashes,
                "browser_post_status": exchange["post_status"],
                "redirect_is_token_free": "token" not in exchange["post_location"].lower(),
            },
            "durable_state": {
                "intent_count": 1,
                "encrypted_vault_count": 1,
                "m57_5_claim_count": 1,
                "activation_commitment_count": 1,
                "raw_role_token_occurrences": durable_text.count(raw_token),
                "raw_recovery_secret_occurrences": durable_text.count(recovery_secret),
                "vault_mode": oct(_mode_bits(vault_path)),
            },
            "browser": {
                "first_status": exchange["first_status"],
                "post_status": exchange["post_status"],
                "raw_role_token_surface_occurrences": exchange["raw_role_token_surface_occurrences"],
                "role_token_equals_cookie_or_csrf": exchange["role_token_equals_cookie_or_csrf"],
                "recovery_secret_surface_occurrences": sum(
                    recovery_secret in value for value in (
                        exchange["location"], exchange["post_location"], exchange["body"],
                        exchange["set_cookie"],
                    )
                ),
            },
            "m57_4_ledger": {
                "revision_count": ledger["revision_count"],
                "source_view_count": len(ledger["source_views"]),
            },
            "artifact_accounting": {
                "m57_6_new_durable_artifact_count": len(m57_6_artifacts),
                "m57_6_new_durable_bytes": sum(path.stat().st_size for path in m57_6_artifacts),
                "claim_or_scrub_affected_artifact_count": len(affected_artifacts),
                "claim_or_scrub_affected_bytes": sum(path.stat().st_size for path in affected_artifacts),
            },
            "validation": validation,
            "real_participant_count": 0,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
        result["rehearsal_hash"] = digest(result)
        return result


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("version") != "1.0.0":
        errors.append("rehearsal.schema")
    if value.get("status") != "synthetic_crash_recovery_mechanics_only":
        errors.append("rehearsal.status")
    expected = {
        ("first_start", "vault_created"): True,
        ("first_start", "activation_hash_present"): True,
        ("post_process_restart", "accepted_with_same_secret"): True,
        ("post_process_restart", "durable_hashes_unchanged"): True,
        ("post_process_restart", "browser_post_status"): 303,
        ("post_process_restart", "redirect_is_token_free"): True,
        ("durable_state", "intent_count"): 1,
        ("durable_state", "encrypted_vault_count"): 1,
        ("durable_state", "m57_5_claim_count"): 1,
        ("durable_state", "activation_commitment_count"): 1,
        ("durable_state", "raw_role_token_occurrences"): 0,
        ("durable_state", "raw_recovery_secret_occurrences"): 0,
        ("durable_state", "vault_mode"): "0o600",
        ("browser", "first_status"): 303,
        ("browser", "post_status"): 303,
        ("browser", "raw_role_token_surface_occurrences"): 0,
        ("browser", "role_token_equals_cookie_or_csrf"): False,
        ("browser", "recovery_secret_surface_occurrences"): 0,
        ("m57_4_ledger", "revision_count"): 1,
        ("m57_4_ledger", "source_view_count"): 1,
        ("artifact_accounting", "m57_6_new_durable_artifact_count"): 3,
        ("artifact_accounting", "claim_or_scrub_affected_artifact_count"): 5,
    }
    for path, child in expected.items():
        current: Any = value
        for key in path:
            current = current.get(key) if isinstance(current, dict) else None
        if current != child:
            errors.append("rehearsal." + ".".join(path))
    accounting = value.get("artifact_accounting", {})
    if not isinstance(accounting.get("m57_6_new_durable_bytes"), int) or accounting.get("m57_6_new_durable_bytes", 0) <= 0:
        errors.append("rehearsal.artifact_accounting.m57_6_new_durable_bytes")
    if not isinstance(accounting.get("claim_or_scrub_affected_bytes"), int) or accounting.get("claim_or_scrub_affected_bytes", 0) <= 0:
        errors.append("rehearsal.artifact_accounting.claim_or_scrub_affected_bytes")
    if not value.get("validation", {}).get("valid"):
        errors.append("rehearsal.validation")
    for name, child in {
        "real_participant_count": 0, "target_outcome_access_count": 0,
        "model_call_count": 0, "formal_evidence_created": False, "m58_authorized": False,
    }.items():
        if value.get(name) != child:
            errors.append(f"rehearsal.{name}")
    if value.get("rehearsal_hash") != digest(_hashless(value, "rehearsal_hash")):
        errors.append("rehearsal.hash")
    return {"valid": not errors, "errors": errors}


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.6 rehearsal: " + "; ".join(report["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    upstream = capability_m57.build_live_audit()
    counts = upstream["counts"]
    return {
        "schema": "uruha_m57_6_crash_recovery_live_audit_v1",
        "version": "1.0.0",
        "status": "live_external_evidence_unchanged_after_m57_6_engineering",
        "crypto_backend_current_interpreter": audit_crypto_backend(),
        "v7_actual_qualified_coder_slots": counts["v7_slots_by_ledger"][0],
        "v7_required_coder_slots": 18,
        "v7_actual_qualified_evaluator_slots": counts["v7_slots_by_ledger"][1],
        "v7_required_evaluator_slots": 18,
        "real_temporal_rows_available": counts["real_temporal_rows"],
        "real_temporal_rows_required": 30,
        "real_component_rows_available": upstream["real_component_rows"],
        "real_component_rows_required": 30,
        "real_participant_capabilities_issued": 0,
        "real_recovery_vaults_created": 0,
        "formal_m56_results": 0,
        "formal_m57_results": int(upstream["formal_m57_result_created"]),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "m58_authorized": False,
        "boundary": "M57.6 recovery mechanics do not create humans, component labels, target outcomes, model calls, a formal M57 result or M58 authority.",
    }


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None,
) -> str:
    rehearsal = rehearsal or load_saved_rehearsal()
    audit = audit or (load_json(LIVE_AUDIT_PATH) if LIVE_AUDIT_PATH.exists() else build_live_audit())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.6 Crash Recovery</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#06151a;color:#eefcff;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}main{{max-width:1240px;margin:auto;padding:24px}}h1{{font-size:38px;margin:8px 0}}.sub{{color:#a6c8d0}}.status{{display:inline-block;background:#6d2e3d;color:#ffdce3;padding:8px 12px;border-radius:999px;font-weight:800}}.flow{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:22px 0}}.node,.card{{background:#10272e;border:1px solid #3c6470;border-radius:16px;padding:16px}}.node b{{display:block;color:#77e0bc;margin-bottom:8px}}.arrow{{text-align:center;color:#8aaeb7;font-size:20px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric{{font-size:30px;font-weight:850}}.ok{{color:#77e0bc}}.bad{{color:#ff96aa}}.wide{{grid-column:span 2}}code{{color:#ffe68c}}@media(max-width:900px){{.flow,.grid{{grid-template-columns:1fr}}.wide{{grid-column:auto}}}}</style></head><body><main>
<span class="status">REAL RECOVERY VAULTS {audit['real_recovery_vaults_created']} · FORMAL M57 DENIED</span><h1>M57.6 · 程序中斷後，角色能力仍可安全恢復</h1><p class="sub">單一變因：participant secret + Scrypt + AES-GCM。M57.4/M57.5 的證據語意完全不變。</p>
<div class="flow"><div class="node"><b>1 · TTY SECRET</b>只在終端隱藏輸入<br>不進 argv/env/browser</div><div class="node"><b>2 · SCRYPT</b>N=32768 · r=8 · p=1<br>memory-hard key</div><div class="node"><b>3 · AES-GCM VAULT</b>token 加密＋AAD綁 run/role/hash<br>0600 full-sync</div><div class="node"><b>4 · M57.5 CLAIM</b>原 envelope scrub<br>原 claim 不變</div><div class="node"><b>5 · PROCESS RESTART</b>同一 secret 解密<br>wrong/tamper fail closed</div><div class="node"><b>6 · M57.4 LEDGER</b>cookie + CSRF<br>原 coder save</div></div>
<section class="grid"><div class="card"><div class="metric bad">0 → 1</div><b>修改前／後 restart</b><p>M57.5 post-claim restart 被拒；M57.6 synthetic same-secret restart 可進入。</p></div><div class="card"><div class="metric ok">{str(rehearsal['post_process_restart']['durable_hashes_unchanged']).upper()}</div><b>restart state unchanged</b><p>intent、vault、claim、activation 四個 durable hashes 不變。</p></div><div class="card"><div class="metric ok">0 / 0</div><b>secret surfaces</b><p>durable raw token {rehearsal['durable_state']['raw_role_token_occurrences']}；durable secret {rehearsal['durable_state']['raw_recovery_secret_occurrences']}。</p></div><div class="card"><div class="metric">{rehearsal['m57_4_ledger']['revision_count']} revision</div><b>functional save after restart</b><p>HTTP {rehearsal['browser']['post_status']}；原 M57.4 ledger 仍可寫入。</p></div><div class="card"><div class="metric bad">{audit['v7_actual_qualified_coder_slots']}/{audit['v7_required_coder_slots']} + {audit['v7_actual_qualified_evaluator_slots']}/{audit['v7_required_evaluator_slots']}</div><b>真人 gate</b><p>兩類 V7 真人資格仍完全未完成。</p></div><div class="card"><div class="metric bad">{audit['real_component_rows_available']}/{audit['real_component_rows_required']}</div><b>real component rows</b><p>加密恢復不會自動產生任何真人標註。</p></div><div class="card wide"><h2>能主張</h2><p>在綁定的本機 <code>cryptography 50.0.1</code> 環境，合成角色能力可在完整 claim 後停止程序，再以同一 participant secret 解密並繼續寫原 ledger；wrong secret/tamper 應被拒絕。</p></div><div class="card"><h2>不能主張</h2><p>不是身份證明、惡意同帳號隔離、TLS、一般部署可攜性、真人 evidence、Equation V1、人類方程式或 M58 授權。</p></div></section>
</main></body></html>"""


def serve_dashboard(port: int) -> None:
    payload = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if urllib.parse.urlparse(self.path).path != "/dashboard":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

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
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--audit-crypto", action="store_true")
    actions.add_argument("--rehearse", action="store_true")
    actions.add_argument("--dashboard", type=int, metavar="PORT")
    actions.add_argument("--serve-recoverable", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    args = parser.parse_args()
    if args.audit_crypto:
        print(json.dumps(audit_crypto_backend(), ensure_ascii=False, indent=2))
    elif args.rehearse:
        print(json.dumps(build_engineering_rehearsal(), ensure_ascii=False, indent=2))
    elif args.dashboard is not None:
        serve_dashboard(args.dashboard)
    else:
        run_id, role, envelope_path, port_text = args.serve_recoverable
        if not re.fullmatch(r"\d{1,5}", port_text) or not (0 <= int(port_text) <= 65535):
            parser.error("PORT must be between 0 and 65535")
        serve_recoverable_collection(run_id, role, envelope_path, int(port_text))


if __name__ == "__main__":
    main()
