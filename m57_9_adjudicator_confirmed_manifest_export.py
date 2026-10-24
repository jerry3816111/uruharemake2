#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M57.9 explicit adjudicator confirmation for exact pre-outcome manifest export.

M57.8 keeps the role token and recovery secret inside the local process.  This
layer lets only the adjudicator preview the exact frozen M57.2 manifest hash and
explicitly authorize the unchanged M57.4 export without exposing either secret.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import hmac
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import os
from pathlib import Path
import re
import secrets
from tempfile import TemporaryDirectory
from threading import Thread
from time import perf_counter
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_2_component_prediction_capsule as component_m57
import m57_4_component_evidence_collection as collection_m57
import m57_5_participant_capability_issuance as capability_m57
import m57_6_crash_recoverable_participant_capability as recovery_m57
import m57_8_participant_confirmed_ledger_completion as completion_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs" / "m57_9_adjudicator_confirmed_manifest_export_v1.json"
RESULT_PATH = ROOT / "analysis" / "m57_9_adjudicator_confirmed_manifest_export_rehearsal_2026-09-06.json"
LIVE_AUDIT_PATH = ROOT / "analysis" / "m57_9_adjudicator_confirmed_manifest_export_live_audit_2026-09-06.json"
COST_PATH = ROOT / "analysis" / "m57_9_adjudicator_confirmed_manifest_export_fixture_cost_2026-09-06.json"
M57_8_LIVE_AUDIT_PATH = ROOT / "analysis" / "m57_8_participant_confirmed_ledger_completion_live_audit_2026-09-05.json"

CONFIRMATION_VALUE = "confirm_exact_preoutcome_manifest_and_export"
INTENT_SCHEMA = "uruha_m57_9_adjudicator_manifest_export_intent_v1"
RECEIPT_SCHEMA = "uruha_m57_9_adjudicator_manifest_export_receipt_v1"
REHEARSAL_SCHEMA = "uruha_m57_9_adjudicator_confirmed_manifest_export_rehearsal_v1"
LIVE_AUDIT_SCHEMA = "uruha_m57_9_adjudicator_confirmed_manifest_export_live_audit_v1"
COST_SCHEMA = "uruha_m57_9_adjudicator_confirmed_manifest_export_fixture_cost_v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _hashless(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != field}


def load_contract() -> dict[str, Any]:
    return load_json(CONTRACT_PATH)


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "eligibility", "transaction", "browser", "runtime_launch", "public_functions",
        "formal_boundary", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_9_adjudicator_confirmed_manifest_export_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_before_any_real_participant_export":
        errors.append("contract.status")
    if contract.get("single_changed_variable") != "adjudicator_confirmed_token_free_preoutcome_manifest_export":
        errors.append("contract.variable")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 7:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    eligibility = contract.get("eligibility") or {}
    for name in (
        "all_three_m57_4_ledgers_complete_and_sealed", "adjudicator_m57_8_completion_receipt_required",
        "outcome_absence_revalidated", "exact_manifest_preview_hash_required", "explicit_checkbox_required",
    ):
        if eligibility.get(name) is not True:
            errors.append(f"eligibility.{name}")
    if eligibility.get("role_slot") != "adjudicator" or eligibility.get("confirmation_value") != CONFIRMATION_VALUE:
        errors.append("eligibility.identity_or_confirmation")
    if eligibility.get("automatic_export_after_seal") is not False:
        errors.append("eligibility.automatic_export")
    transaction = contract.get("transaction") or {}
    for name in (
        "existing_single_writer_lock_required_for_each_validation_phase", "durable_intent_before_m57_4_export",
        "unchanged_m57_4_export_function_delegated",
        "final_receipt_binds_intent_three_seals_manifest_and_export_commitment",
        "identical_interrupted_or_completed_replay_allowed",
    ):
        if transaction.get(name) is not True:
            errors.append(f"transaction.{name}")
    for name in ("preexisting_export_without_m57_9_intent_attributable", "nonidentical_replay_allowed"):
        if transaction.get(name) is not False:
            errors.append(f"transaction.{name}")
    browser = contract.get("browser") or {}
    for name in ("loopback_only", "http_only_same_site_cookie_reused", "csrf_required_for_save_seal_and_export"):
        if browser.get(name) is not True:
            errors.append(f"browser.{name}")
    for name in (
        "coder_export_control_visible", "raw_private_ledgers_visible",
        "role_token_or_recovery_secret_in_url_form_html_cookie_receipt", "post_export_form_visible",
    ):
        if browser.get(name) is not False:
            errors.append(f"browser.{name}")
    if browser.get("export_post_fields") != ["csrf", "expected_manifest_hash", "confirmation"]:
        errors.append("browser.fields")
    launch = contract.get("runtime_launch") or {}
    if launch.get("m57_7_full_audit_precedes_exec") is not True:
        errors.append("runtime.audit")
    if launch.get("public_arguments") != ["run_id", "role_slot", "envelope_path", "port"]:
        errors.append("runtime.args")
    if launch.get("collection_time_download_install_or_repair_calls") != 0 or launch.get("role_token_or_recovery_secret_argument") is not False:
        errors.append("runtime.boundary")
    expected_public = {
        "inspect_adjudicator_manifest_export": ["run_id", "adjudicator_session_token"],
        "confirm_and_export_adjudicator_manifest": [
            "run_id", "adjudicator_session_token", "expected_manifest_hash", "confirmation",
        ],
    }
    if contract.get("public_functions") != expected_public:
        errors.append("public_functions")
    actual_public = {
        "inspect_adjudicator_manifest_export": list(inspect.signature(inspect_adjudicator_manifest_export).parameters),
        "confirm_and_export_adjudicator_manifest": list(inspect.signature(confirm_and_export_adjudicator_manifest).parameters),
    }
    if actual_public != expected_public:
        errors.append("public_signatures")
    formal = contract.get("formal_boundary") or {}
    if formal.get("target_outcome_access_count") != 0 or formal.get("model_call_count") != 0:
        errors.append("formal.access")
    for name in (
        "synthetic_rehearsal_is_real_human_evidence",
        "adjudicator_confirmation_proves_identity_or_label_correctness",
        "m57_2_prediction_execution_automatic", "m58_authorized",
    ):
        if formal.get(name) is not False:
            errors.append(f"formal.{name}")
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
        "m57_8_adjudicator_intent": paths["commitments"] / "m57_8_adjudicator_participant_seal_intent.json",
        "m57_8_adjudicator_receipt": paths["commitments"] / "m57_8_adjudicator_participant_completion_receipt.json",
        "m57_9_intent": paths["commitments"] / "m57_9_adjudicator_manifest_export_intent.json",
        "m57_9_receipt": paths["commitments"] / "m57_9_adjudicator_manifest_export_receipt.json",
    }


def _validated_context_under_lock(run_id: str, adjudicator_session_token: str) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Path], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]
]:
    context = collection_m57._context(run_id)
    paths = _paths(run_id)
    collection_m57._no_outcome(paths, "adjudicator manifest export")
    mode = collection_m57._load_mode(run_id, context, paths)
    collection_m57._authorize(mode, "adjudicator", adjudicator_session_token)
    coder_ledgers, coder_seals = collection_m57._load_sealed_coders(run_id, mode, context, paths)
    adjudicator = collection_m57._load_role_ledger(
        "adjudicator", mode, context, paths, require_complete=True,
        coder_ledgers=coder_ledgers, coder_seals=coder_seals,
    )
    if adjudicator["status"] != "sealed_private_role_ledger":
        raise PermissionError("M57.9 requires the adjudicator ledger to be sealed")
    adj_seal = load_json(paths["seal_adjudicator"])
    seal_errors = collection_m57._validate_seal(adj_seal, adjudicator, mode)
    if seal_errors:
        raise ValueError("invalid M57.4 adjudicator seal: " + "; ".join(seal_errors))
    if not paths["m57_8_adjudicator_intent"].is_file() or not paths["m57_8_adjudicator_receipt"].is_file():
        raise PermissionError("M57.9 requires an explicit M57.8 adjudicator completion receipt")
    m578_intent = load_json(paths["m57_8_adjudicator_intent"])
    m578_receipt = load_json(paths["m57_8_adjudicator_receipt"])
    errors = completion_m57._intent_errors(m578_intent, mode, "adjudicator")
    errors.extend(completion_m57._receipt_errors(m578_receipt, mode, adjudicator, adj_seal, m578_intent))
    if errors:
        raise ValueError("invalid M57.8 adjudicator completion: " + "; ".join(errors))
    ledgers = {**coder_ledgers, "adjudicator": adjudicator}
    seals = {**coder_seals, "adjudicator": adj_seal}
    manifest = collection_m57._build_manifest(run_id, mode, context, ledgers, seals)
    return context, mode, paths, ledgers, seals, manifest


def _new_intent(mode: dict[str, Any], ledgers: dict[str, dict[str, Any]], seals: dict[str, dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "adjudicator_confirmed_exact_preoutcome_manifest_before_export",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "participant_pseudonym": mode["participants"]["adjudicator"]["pseudonym"],
        "confirmation_value": CONFIRMATION_VALUE,
        "expected_manifest_hash": manifest["manifest_hash"],
        "expected_ledger_hashes": {role: ledgers[role]["ledger_hash"] for role in collection_m57.ROLE_SLOTS},
        "expected_seal_hashes": {role: seals[role]["seal_hash"] for role in collection_m57.ROLE_SLOTS},
        "created_at_utc": collection_m57._utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    value["intent_hash"] = digest(value)
    return value


def _intent_errors(
    value: dict[str, Any], mode: dict[str, Any], ledgers: dict[str, dict[str, Any]],
    seals: dict[str, dict[str, Any]], manifest: dict[str, Any],
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "participant_pseudonym",
        "confirmation_value", "expected_manifest_hash", "expected_ledger_hashes", "expected_seal_hashes",
        "created_at_utc", "target_outcome_access_count", "model_call_count", "intent_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["intent.fields"]
    expected = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "adjudicator_confirmed_exact_preoutcome_manifest_before_export",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "participant_pseudonym": mode["participants"]["adjudicator"]["pseudonym"],
        "confirmation_value": CONFIRMATION_VALUE,
        "expected_manifest_hash": manifest["manifest_hash"],
        "expected_ledger_hashes": {role: ledgers[role]["ledger_hash"] for role in collection_m57.ROLE_SLOTS},
        "expected_seal_hashes": {role: seals[role]["seal_hash"] for role in collection_m57.ROLE_SLOTS},
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    errors = [f"intent.{name}" for name, expected_value in expected.items() if value.get(name) != expected_value]
    if not collection_m57._valid_timestamp(value.get("created_at_utc")):
        errors.append("intent.timestamp")
    if value.get("intent_hash") != digest(_hashless(value, "intent_hash")):
        errors.append("intent.hash")
    return errors


def _load_export_artifacts(
    run_id: str, mode: dict[str, Any], paths: dict[str, Path], manifest: dict[str, Any],
    ledgers: dict[str, dict[str, Any]], seals: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    evidence = export = None
    if paths["evidence"].exists():
        evidence = load_json(paths["evidence"])
        if evidence != manifest:
            raise ValueError("existing M57.2 evidence manifest differs from current sealed ledgers")
        validation = component_m57.validate_evidence_manifest(
            evidence, run_id, collection_m57._context(run_id),
            allow_forged=mode["data_kind"] != collection_m57.REAL_KIND,
        )
        if not validation["valid"]:
            raise ValueError("invalid existing M57.2 evidence manifest: " + "; ".join(validation["errors"]))
    if paths["m57_4_export"].exists():
        if evidence is None:
            raise ValueError("M57.4 export commitment exists without evidence manifest")
        export = load_json(paths["m57_4_export"])
        errors = collection_m57._validate_export_commitment(export, run_id, mode, manifest, ledgers, seals)
        if errors:
            raise ValueError("invalid existing M57.4 export commitment: " + "; ".join(errors))
    return evidence, export


def _new_receipt(
    mode: dict[str, Any], intent: dict[str, Any], manifest: dict[str, Any], export: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "adjudicator_confirmation_and_m57_4_manifest_export_full_sync_completed",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "participant_pseudonym": mode["participants"]["adjudicator"]["pseudonym"],
        "intent_hash": intent["intent_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "expected_ledger_hashes": intent["expected_ledger_hashes"],
        "expected_seal_hashes": intent["expected_seal_hashes"],
        "m57_4_export_commitment_hash": export["export_commitment_hash"],
        "formal_manifest_exported": export["formal_manifest_exported"],
        "completed_at_utc": collection_m57._utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "m57_2_prediction_execution_started": False,
        "m58_authorized": False,
    }
    value["receipt_hash"] = digest(value)
    return value


def _receipt_errors(
    value: dict[str, Any], mode: dict[str, Any], intent: dict[str, Any], manifest: dict[str, Any], export: dict[str, Any],
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "participant_pseudonym", "intent_hash",
        "manifest_hash", "expected_ledger_hashes", "expected_seal_hashes", "m57_4_export_commitment_hash",
        "formal_manifest_exported", "completed_at_utc", "target_outcome_access_count", "model_call_count",
        "m57_2_prediction_execution_started", "m58_authorized", "receipt_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["receipt.fields"]
    expected = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "adjudicator_confirmation_and_m57_4_manifest_export_full_sync_completed",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "participant_pseudonym": mode["participants"]["adjudicator"]["pseudonym"],
        "intent_hash": intent["intent_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "expected_ledger_hashes": intent["expected_ledger_hashes"],
        "expected_seal_hashes": intent["expected_seal_hashes"],
        "m57_4_export_commitment_hash": export["export_commitment_hash"],
        "formal_manifest_exported": export["formal_manifest_exported"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "m57_2_prediction_execution_started": False,
        "m58_authorized": False,
    }
    errors = [f"receipt.{name}" for name, expected_value in expected.items() if value.get(name) != expected_value]
    if not collection_m57._valid_timestamp(value.get("completed_at_utc")):
        errors.append("receipt.timestamp")
    if value.get("receipt_hash") != digest(_hashless(value, "receipt_hash")):
        errors.append("receipt.hash")
    return errors


def _inspect_under_lock(run_id: str, adjudicator_session_token: str) -> dict[str, Any]:
    _context, mode, paths, ledgers, seals, manifest = _validated_context_under_lock(
        run_id, adjudicator_session_token
    )
    intent = receipt = None
    if paths["m57_9_intent"].exists():
        intent = load_json(paths["m57_9_intent"])
        errors = _intent_errors(intent, mode, ledgers, seals, manifest)
        if errors:
            raise ValueError("invalid M57.9 export intent: " + "; ".join(errors))
    evidence, export = _load_export_artifacts(run_id, mode, paths, manifest, ledgers, seals)
    if (evidence is not None or export is not None) and intent is None:
        status = "preexisting_unattributed_manifest_export"
    elif intent is not None and export is None:
        status = "adjudicator_export_transaction_pending"
    elif intent is not None and export is not None:
        status = "adjudicator_export_completed_or_receipt_pending"
    else:
        status = "adjudicator_sealed_ready_to_confirm_export"
    if paths["m57_9_receipt"].exists():
        if intent is None or export is None:
            raise ValueError("M57.9 receipt exists without intent and complete M57.4 export")
        receipt = load_json(paths["m57_9_receipt"])
        errors = _receipt_errors(receipt, mode, intent, manifest, export)
        if errors:
            raise ValueError("invalid M57.9 export receipt: " + "; ".join(errors))
        status = "adjudicator_confirmed_manifest_export_completed"
    unattributed = (evidence is not None or export is not None) and intent is None
    return {
        "status": status,
        "run_id": run_id,
        "role_slot": "adjudicator",
        "participant_pseudonym": mode["participants"]["adjudicator"]["pseudonym"],
        "data_kind": mode["data_kind"],
        "sample_count": 30,
        "coder_entry_count": 60,
        "adjudicator_entry_count": 30,
        "source_view_count": 90,
        "displayed_expected_manifest_hash": intent["expected_manifest_hash"] if intent else manifest["manifest_hash"],
        "ledger_hashes": {role: ledgers[role]["ledger_hash"] for role in collection_m57.ROLE_SLOTS},
        "seal_hashes": {role: seals[role]["seal_hash"] for role in collection_m57.ROLE_SLOTS},
        "can_confirm_and_export": intent is None and not unattributed,
        "can_resume_identical_export": intent is not None and receipt is None,
        "preexisting_unattributed_export": unattributed,
        "manifest_hash": manifest["manifest_hash"] if evidence is not None else None,
        "m57_4_export_commitment_hash": export["export_commitment_hash"] if export else None,
        "m57_9_receipt_hash": receipt["receipt_hash"] if receipt else None,
        "formal_manifest_exported": export["formal_manifest_exported"] if export else False,
        "raw_role_token_returned": False,
        "raw_recovery_secret_returned": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "m57_2_prediction_execution_started": False,
        "m58_authorized": False,
    }


def inspect_adjudicator_manifest_export(run_id: str, adjudicator_session_token: str) -> dict[str, Any]:
    """Return the exact adjudicator export preview without exposing capability material."""
    report = validate_contract()
    if not report["valid"]:
        raise PermissionError("M57.9 contract invalid: " + "; ".join(report["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        return _inspect_under_lock(run_id, adjudicator_session_token)


def confirm_and_export_adjudicator_manifest(
    run_id: str, adjudicator_session_token: str, expected_manifest_hash: str, confirmation: str,
) -> dict[str, Any]:
    """Bind adjudicator confirmation to the unchanged M57.4 manifest export."""
    report = validate_contract()
    if not report["valid"]:
        raise PermissionError("M57.9 contract invalid: " + "; ".join(report["errors"]))
    if confirmation != CONFIRMATION_VALUE:
        raise PermissionError("M57.9 explicit adjudicator confirmation is required")
    if not isinstance(expected_manifest_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_hash):
        raise ValueError("M57.9 expected manifest hash must be one SHA-256 value")
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        _context, mode, paths, ledgers, seals, manifest = _validated_context_under_lock(
            run_id, adjudicator_session_token
        )
        if paths["m57_9_intent"].exists():
            intent = load_json(paths["m57_9_intent"])
            errors = _intent_errors(intent, mode, ledgers, seals, manifest)
            if errors:
                raise ValueError("invalid existing M57.9 export intent: " + "; ".join(errors))
            if not hmac.compare_digest(intent["expected_manifest_hash"], expected_manifest_hash):
                raise PermissionError("M57.9 nonidentical adjudicator export replay denied")
            intent_write = "validated_existing_identical"
        else:
            if paths["evidence"].exists() or paths["m57_4_export"].exists():
                raise PermissionError("M57.9 cannot attribute a preexisting manifest export to a missing adjudicator intent")
            if not hmac.compare_digest(manifest["manifest_hash"], expected_manifest_hash):
                raise PermissionError("M57.9 displayed manifest hash is stale")
            intent = _new_intent(mode, ledgers, seals, manifest)
            durable_m56._durable_atomic_write_json(paths["m57_9_intent"], intent, exclusive=True)
            intent_write = "created_full_sync_before_m57_4_export"

    export_result = collection_m57.export_component_evidence_manifest(run_id, adjudicator_session_token)

    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        _context, mode, paths, ledgers, seals, manifest = _validated_context_under_lock(
            run_id, adjudicator_session_token
        )
        intent = load_json(paths["m57_9_intent"])
        errors = _intent_errors(intent, mode, ledgers, seals, manifest)
        if errors or not hmac.compare_digest(intent["expected_manifest_hash"], expected_manifest_hash):
            raise PermissionError("M57.9 export state changed after adjudicator confirmation")
        evidence, export = _load_export_artifacts(run_id, mode, paths, manifest, ledgers, seals)
        if evidence is None or export is None:
            raise AssertionError("unchanged M57.4 export did not produce complete artifacts")
        if paths["m57_9_receipt"].exists():
            receipt = load_json(paths["m57_9_receipt"])
            errors = _receipt_errors(receipt, mode, intent, manifest, export)
            if errors:
                raise ValueError("invalid existing M57.9 export receipt: " + "; ".join(errors))
            receipt_write = "validated_existing_identical"
        else:
            receipt = _new_receipt(mode, intent, manifest, export)
            errors = _receipt_errors(receipt, mode, intent, manifest, export)
            if errors:
                raise AssertionError("constructed M57.9 export receipt invalid: " + "; ".join(errors))
            durable_m56._durable_atomic_write_json(paths["m57_9_receipt"], receipt, exclusive=True)
            receipt_write = "created_full_sync"
        return {
            "status": "m57_9_adjudicator_confirmation_and_manifest_export_completed",
            "run_id": run_id,
            "role_slot": "adjudicator",
            "intent_write": intent_write,
            "manifest_write": export_result["manifest_write"],
            "m57_4_export_write": export_result["export_write"],
            "receipt_write": receipt_write,
            "manifest_hash": manifest["manifest_hash"],
            "m57_4_export_commitment_hash": export["export_commitment_hash"],
            "m57_9_receipt_hash": receipt["receipt_hash"],
            "formal_manifest_exported": export["formal_manifest_exported"],
            "raw_role_token_returned": False,
            "raw_recovery_secret_returned": False,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "m57_2_prediction_execution_started": False,
            "m58_authorized": False,
        }


def _export_panel(progress: dict[str, Any], csrf_token: str, error: str = "") -> str:
    completed = progress["m57_9_receipt_hash"] is not None
    pending = progress["can_resume_identical_export"]
    error_html = f'<p class="m579-error">{html.escape(error)}</p>' if error else ""
    form = ""
    if progress["can_confirm_and_export"] or pending:
        label = "恢復同一筆匯出" if pending else "確認並匯出這份 manifest"
        form = f'''<form method="post" action="/export" class="m579-export-form">
<input type="hidden" name="csrf" value="{html.escape(csrf_token)}">
<input type="hidden" name="expected_manifest_hash" value="{html.escape(progress['displayed_expected_manifest_hash'])}">
<label><input type="checkbox" name="confirmation" value="{CONFIRMATION_VALUE}" required> 我確認三份封存帳本會產生上方這個 pre-outcome manifest；匯出後不能換成別份資料。</label>
<button class="m579-export">{label}</button></form>'''
    if completed:
        state = "已由 adjudicator 確認並匯出"
    elif progress["preexisting_unattributed_export"]:
        state = "已有無法歸因給本次確認的舊匯出，停止"
    elif pending:
        state = "確認已落盤，等待完成同一筆匯出"
    else:
        state = "三份帳本已封存，可確認匯出"
    seals = "".join(
        f"<p>{html.escape(role)} seal</p><code>{html.escape(value)}</code>"
        for role, value in progress["seal_hashes"].items()
    )
    final = ""
    if completed:
        final = (
            '<p>M57.4 export commitment</p><code>' + html.escape(progress["m57_4_export_commitment_hash"] or "")
            + '</code><p>M57.9 receipt</p><code>' + html.escape(progress["m57_9_receipt_hash"] or "") + "</code>"
        )
    return f'''<section class="m579-panel"><b>M57.9 · ADJUDICATOR EXPORT CONFIRMATION</b><h2>{state}</h2>{error_html}
<div class="m579-grid"><div><strong>30</strong><span>samples</span></div><div><strong>60</strong><span>coder entries</span></div><div><strong>30</strong><span>adjudicator entries</span></div><div><strong>90</strong><span>source views</span></div></div>
<p>即將匯出的 exact M57.2 manifest hash：</p><code>{html.escape(progress['displayed_expected_manifest_hash'])}</code>{final}{form}{seals}
<p class="m579-boundary">這只把三份已封存的 pre-outcome evidence 轉成凍結 M57.2 manifest；不會讀取答案、不會自動執行模型，也不代表標註正確或 M58 已授權。</p></section>'''


def _render_participant_page(
    run_id: str, role_slot: str, role_token: str, sample_id: str, csrf_token: str, error: str = "",
) -> str:
    page = completion_m57._render_participant_page(run_id, role_slot, role_token, sample_id, csrf_token)
    page = page.replace("<title>M57.8", "<title>M57.9").replace("<b>M57.8", "<b>M57.9")
    completion = completion_m57.inspect_participant_ledger_completion(run_id, role_slot, role_token)
    if role_slot != "adjudicator" or completion["receipt_hash"] is None:
        return page
    progress = inspect_adjudicator_manifest_export(run_id, role_token)
    panel = _export_panel(progress, csrf_token, error)
    style = """<style>.m579-panel{background:#171d36;border:2px solid #9b8cff;border-radius:18px;padding:20px;margin:16px 0}.m579-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.m579-grid div{background:#0b1026;padding:12px;border-radius:10px}.m579-grid strong,.m579-grid span{display:block}.m579-grid strong{font-size:24px;color:#b8adff}.m579-panel code{display:block;overflow-wrap:anywhere;background:#080b19;padding:10px}.m579-export-form{margin-top:16px;padding:14px;border:1px solid #d9a85c}.m579-export{background:#e5ae57}.m579-error{color:#ffabb8}.m579-boundary{color:#bdc4db}@media(max-width:650px){.m579-grid{grid-template-columns:repeat(2,1fr)}}</style>"""
    return page.replace("</head>", style + "</head>").replace("</main>", panel + "</main>")


def _make_export_server(
    run_id: str, role_slot: str, envelope_path: str, port: int, recovery_secret: str,
) -> tuple[ThreadingHTTPServer, dict[str, Any]]:
    role_token, recovery = recovery_m57._activate_or_recover(run_id, role_slot, envelope_path, recovery_secret)
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
                self.send_header("Set-Cookie", f"{recovery_m57.COOKIE_NAME}={session_id}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _cookie_ok(self) -> bool:
            return hmac.compare_digest(recovery_m57._cookie_value(self.headers.get("Cookie")), session_id)

        def _send_text(self, value: str, status: int) -> None:
            self._headers(status, html.escape(value).encode("utf-8"))

        def _read_form(self) -> dict[str, list[str]]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 131072:
                raise ValueError("invalid form size")
            return urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)

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
            if sample_id not in order:
                self._send_text("unknown sample", 400)
                return
            if not self._cookie_ok():
                self._headers(303, location=f"/?sample={urllib.parse.quote(sample_id)}", set_cookie=True)
                return
            try:
                body = _render_participant_page(run_id, role_slot, role_token, sample_id, csrf_token).encode("utf-8")
                self._headers(200, body)
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._send_text(str(exc), 400)

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/save", "/seal", "/export"}:
                self._send_text("not found", 404)
                return
            if not self._cookie_ok():
                self._send_text("invalid browser session", 403)
                return
            try:
                form = self._read_form()
            except (ValueError, UnicodeDecodeError) as exc:
                self._send_text(str(exc), 400)
                return
            submitted_csrf = form.pop("csrf", [""])[0]
            if not hmac.compare_digest(submitted_csrf, csrf_token):
                self._send_text("invalid CSRF token", 403)
                return
            if "token" in form or any("secret" in key.lower() for key in form):
                self._send_text("role token and recovery secret form fields forbidden", 400)
                return
            sample_id = form.get("sample_id", [order[-1]])[0]
            try:
                if self.path == "/save":
                    view = collection_m57.record_component_source_view(run_id, role_slot, role_token, sample_id)
                    payload = collection_m57._entry_form_payload(role_slot, form, view)
                    collection_m57.save_component_evidence_entry(run_id, role_slot, role_token, sample_id, payload)
                    next_index = min(len(order) - 1, order.index(sample_id) + 1)
                    self._headers(303, location=f"/?sample={urllib.parse.quote(order[next_index])}")
                    return
                if self.path == "/seal":
                    if set(form) != {"expected_ledger_hash", "confirmation"} or any(len(values) != 1 for values in form.values()):
                        raise ValueError("M57.8 seal form fields differ from the frozen contract")
                    completion_m57.confirm_and_seal_participant_ledger(
                        run_id, role_slot, role_token,
                        form["expected_ledger_hash"][0], form["confirmation"][0],
                    )
                    self._headers(303, location="/")
                    return
                if role_slot != "adjudicator":
                    raise PermissionError("M57.9 export is adjudicator-only")
                if set(form) != {"expected_manifest_hash", "confirmation"} or any(len(values) != 1 for values in form.values()):
                    raise ValueError("M57.9 export form fields differ from the frozen contract")
                confirm_and_export_adjudicator_manifest(
                    run_id, role_token, form["expected_manifest_hash"][0], form["confirmation"][0],
                )
                self._headers(303, location="/")
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                try:
                    body = _render_participant_page(
                        run_id, role_slot, role_token, sample_id, csrf_token, str(exc)
                    ).encode("utf-8")
                    self._headers(400, body)
                except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError):
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
        "cookie_name": recovery_m57.COOKIE_NAME,
        "raw_role_token_returned": False,
        "raw_recovery_secret_returned": False,
    }


def serve_exportable_collection(run_id: str, role_slot: str, envelope_path: str, port: int) -> None:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.9 contract invalid before secret input: " + "; ".join(contract["errors"]))
    recovery_secret = recovery_m57._interactive_recovery_secret(run_id, role_slot)
    server, metadata = _make_export_server(run_id, role_slot, envelope_path, port, recovery_secret)
    del metadata, recovery_secret
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_launch_spec(run_id: str, role_slot: str, envelope_path: str | Path, port: int) -> dict[str, Any]:
    spec = completion_m57.build_launch_spec(run_id, role_slot, envelope_path, port)
    argv = list(spec["argv"])
    argv[3] = str(ROOT / "m57_9_adjudicator_confirmed_manifest_export.py")
    argv[4] = "--serve-exportable"
    return {
        **spec,
        "argv": argv,
        "m57_7_full_audit_ready_before_exec": spec["m57_7_full_audit_ready_before_exec"],
        "m57_9_entrypoint": True,
    }


def launch_export_runtime(run_id: str, role_slot: str, envelope_path: str | Path, port: int) -> None:
    spec = build_launch_spec(run_id, role_slot, envelope_path, port)
    os.execve(spec["executable"], spec["argv"], spec["environment"])


def _fill_synthetic_adjudicator(run_id: str, token: str) -> None:
    context = collection_m57._context(run_id)
    for sample_id in collection_m57._sample_order(context):
        view = collection_m57.record_component_source_view(run_id, "adjudicator", token, sample_id)
        source = view["source_information"]
        form = {
            "perception_choice": ["coder_a"],
            "perception_resolution_basis": ["Synthetic pre-outcome mechanics basis."],
            "retrieval_choice": ["coder_a"],
            "retrieval_resolution_basis": ["Synthetic pre-outcome mechanics basis."],
            "observable_state_proxy": [json.dumps(
                collection_m57._synthetic_state_payload(context, sample_id, source), ensure_ascii=False
            )],
        }
        payload = collection_m57._entry_form_payload("adjudicator", form, view)
        collection_m57.save_component_evidence_entry(run_id, "adjudicator", token, sample_id, payload)


def _confirm_synthetic_ledger(run_id: str, role_slot: str, token: str) -> dict[str, Any]:
    progress = completion_m57.inspect_participant_ledger_completion(run_id, role_slot, token)
    return completion_m57.confirm_and_seal_participant_ledger(
        run_id, role_slot, token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
    )


def _complete_synthetic_three_role_ledgers(run_id: str, tokens: dict[str, str]) -> None:
    completion_m57._fill_synthetic_coder(run_id, "coder_a", tokens["coder_a"])
    completion_m57._fill_synthetic_coder(run_id, "coder_b", tokens["coder_b"])
    _confirm_synthetic_ledger(run_id, "coder_a", tokens["coder_a"])
    _confirm_synthetic_ledger(run_id, "coder_b", tokens["coder_b"])
    _fill_synthetic_adjudicator(run_id, tokens["adjudicator"])
    _confirm_synthetic_ledger(run_id, "adjudicator", tokens["adjudicator"])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        del request, fp, code, msg, headers, newurl
        return None


def _http_export_exchange(server: ThreadingHTTPServer, raw_token: str, recovery_secret: str) -> dict[str, Any]:
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        try:
            opener.open(urllib.request.Request(base + "/", method="GET"))
            raise AssertionError("expected cookie redirect")
        except urllib.error.HTTPError as response:
            first_status = response.code
            location = response.headers.get("Location", "")
            set_cookie = response.headers.get("Set-Cookie", "")
        cookie = set_cookie.split(";", 1)[0]
        page_response = opener.open(urllib.request.Request(base + location, headers={"Cookie": cookie}, method="GET"))
        page = page_response.read().decode("utf-8")
        csrf_match = re.search(r'name="csrf" value="([^"]+)"', page)
        hash_match = re.search(r'name="expected_manifest_hash" value="([0-9a-f]{64})"', page)
        if not csrf_match or not hash_match or CONFIRMATION_VALUE not in page:
            raise AssertionError("explicit adjudicator export form absent")
        encoded = urllib.parse.urlencode({
            "csrf": csrf_match.group(1),
            "expected_manifest_hash": hash_match.group(1),
            "confirmation": CONFIRMATION_VALUE,
        }).encode("utf-8")
        try:
            opener.open(urllib.request.Request(
                base + "/export", data=encoded,
                headers={"Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            ))
            raise AssertionError("expected export redirect")
        except urllib.error.HTTPError as response:
            export_status = response.code
            export_location = response.headers.get("Location", "")
        final_response = opener.open(urllib.request.Request(
            base + export_location, headers={"Cookie": cookie}, method="GET"
        ))
        final_page = final_response.read().decode("utf-8")
        surfaces = [base, location, set_cookie, cookie, page, export_location, final_page]
        return {
            "first_status": first_status,
            "page_status": page_response.status,
            "export_status": export_status,
            "final_status": final_response.status,
            "preview_manifest_hash": hash_match.group(1),
            "explicit_export_form_visible": True,
            "export_receipt_visible": "已由 adjudicator 確認並匯出" in final_page,
            "export_form_visible_after_completion": 'action="/export"' in final_page,
            "raw_role_token_surface_occurrences": sum(raw_token in item for item in surfaces),
            "recovery_secret_surface_occurrences": sum(recovery_secret in item for item in surfaces),
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def build_engineering_rehearsal() -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    with TemporaryDirectory(prefix="uruha-m57-9-export-") as temp, m5610_private_roots(Path(temp)):
        run_id = "m579-forged-no-human-export"
        first_envelope, recovery_secret = recovery_m57._synthetic_setup(Path(temp), run_id)
        delivery = first_envelope.parent.parent
        envelopes = {
            role: delivery / role / "capability-envelope.json" for role in collection_m57.ROLE_SLOTS
        }
        tokens = {
            role: load_json(envelopes[role])["role_session_token"] for role in collection_m57.ROLE_SLOTS
        }
        _complete_synthetic_three_role_ledgers(run_id, tokens)
        before = inspect_adjudicator_manifest_export(run_id, tokens["adjudicator"])
        server, metadata = _make_export_server(
            run_id, "adjudicator", str(envelopes["adjudicator"]), 0, recovery_secret
        )
        exchange = _http_export_exchange(server, tokens["adjudicator"], recovery_secret)
        after = inspect_adjudicator_manifest_export(run_id, tokens["adjudicator"])
        paths = _paths(run_id)
        intent = load_json(paths["m57_9_intent"])
        manifest = load_json(paths["evidence"])
        export = load_json(paths["m57_4_export"])
        receipt = load_json(paths["m57_9_receipt"])
        durable_text = canonical_json({"intent": intent, "receipt": receipt})
        manifest_validation = component_m57.validate_evidence_manifest(
            manifest, run_id, collection_m57._context(run_id), allow_forged=True
        )
        value = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "synthetic_explicit_adjudicator_export_mechanics_only",
            "run_id": run_id,
            "data_kind": collection_m57.SYNTHETIC_KIND,
            "contract_hash": validate_contract()["contract_hash"],
            "after_all_three_seals_before_confirmation": {
                "all_three_seals_present": len(before["seal_hashes"]) == 3,
                "can_confirm_and_export": before["can_confirm_and_export"],
                "automatic_manifest_export_count": int(before["manifest_hash"] is not None),
                "preview_manifest_hash": before["displayed_expected_manifest_hash"],
            },
            "browser": exchange,
            "completion": {
                "status": after["status"],
                "intent_precedes_export": intent["created_at_utc"] <= export["exported_at_utc"],
                "preview_hash_matches_manifest": exchange["preview_manifest_hash"] == manifest["manifest_hash"],
                "manifest_passes_unchanged_m57_2_validator": manifest_validation["valid"],
                "manifest_validator_errors": manifest_validation["errors"],
                "manifest_hash_matches_m57_4_export": manifest["manifest_hash"] == export["manifest_hash"],
                "m57_4_export_hash_matches_receipt": export["export_commitment_hash"] == receipt["m57_4_export_commitment_hash"],
                "m57_9_receipt_present": after["m57_9_receipt_hash"] == receipt["receipt_hash"],
                "raw_role_token_occurrences_in_m57_9_durable_state": durable_text.count(tokens["adjudicator"]),
                "raw_recovery_secret_occurrences_in_m57_9_durable_state": durable_text.count(recovery_secret),
            },
            "runtime": {
                "m57_7_project_runtime_ready": completion_m57.runtime_m57.audit_runtime()["ready"],
                "collection_time_download_install_or_repair_calls": 0,
            },
            "server_metadata_contains_raw_role_token": tokens["adjudicator"] in canonical_json(metadata),
            "server_metadata_contains_recovery_secret": recovery_secret in canonical_json(metadata),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "real_participant_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
        value["rehearsal_hash"] = digest(value)
        return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "synthetic_explicit_adjudicator_export_mechanics_only":
        errors.append("rehearsal.schema_or_status")
    if value.get("rehearsal_hash") != digest(_hashless(value, "rehearsal_hash")):
        errors.append("rehearsal.hash")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    expected = {
        ("after_all_three_seals_before_confirmation", "all_three_seals_present"): True,
        ("after_all_three_seals_before_confirmation", "can_confirm_and_export"): True,
        ("after_all_three_seals_before_confirmation", "automatic_manifest_export_count"): 0,
        ("browser", "first_status"): 303,
        ("browser", "page_status"): 200,
        ("browser", "export_status"): 303,
        ("browser", "final_status"): 200,
        ("browser", "explicit_export_form_visible"): True,
        ("browser", "export_receipt_visible"): True,
        ("browser", "export_form_visible_after_completion"): False,
        ("browser", "raw_role_token_surface_occurrences"): 0,
        ("browser", "recovery_secret_surface_occurrences"): 0,
        ("completion", "status"): "adjudicator_confirmed_manifest_export_completed",
        ("completion", "intent_precedes_export"): True,
        ("completion", "preview_hash_matches_manifest"): True,
        ("completion", "manifest_passes_unchanged_m57_2_validator"): True,
        ("completion", "manifest_validator_errors"): [],
        ("completion", "manifest_hash_matches_m57_4_export"): True,
        ("completion", "m57_4_export_hash_matches_receipt"): True,
        ("completion", "m57_9_receipt_present"): True,
        ("completion", "raw_role_token_occurrences_in_m57_9_durable_state"): 0,
        ("completion", "raw_recovery_secret_occurrences_in_m57_9_durable_state"): 0,
        ("runtime", "m57_7_project_runtime_ready"): True,
        ("runtime", "collection_time_download_install_or_repair_calls"): 0,
        ("server_metadata_contains_raw_role_token",): False,
        ("server_metadata_contains_recovery_secret",): False,
        ("target_outcome_access_count",): 0,
        ("model_call_count",): 0,
        ("real_participant_count",): 0,
        ("formal_evidence_created",): False,
        ("m58_authorized",): False,
    }
    for path, expected_value in expected.items():
        cursor: Any = value
        for part in path:
            cursor = cursor.get(part) if isinstance(cursor, dict) else None
        if cursor != expected_value:
            errors.append("rehearsal." + ".".join(path))
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def load_saved_rehearsal() -> dict[str, Any]:
    value = load_json(RESULT_PATH)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.9 rehearsal: " + "; ".join(report["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    upstream = load_json(M57_8_LIVE_AUDIT_PATH)
    return {
        "schema": LIVE_AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "live_external_evidence_unchanged_after_m57_9_engineering",
        "m57_7_project_runtime_ready": upstream["m57_7_project_runtime_ready"],
        "real_participant_completion_receipts": upstream["real_participant_completion_receipts"],
        "real_participant_manifest_export_receipts": 0,
        "v7_actual_qualified_evaluator_slots": upstream["v7_actual_qualified_evaluator_slots"],
        "v7_required_evaluator_slots": upstream["v7_required_evaluator_slots"],
        "v7_actual_qualified_coder_slots": upstream["v7_actual_qualified_coder_slots"],
        "v7_required_coder_slots": upstream["v7_required_coder_slots"],
        "real_temporal_rows_available": upstream["real_temporal_rows_available"],
        "real_temporal_rows_required": upstream["real_temporal_rows_required"],
        "real_component_rows_available": upstream["real_component_rows_available"],
        "real_component_rows_required": upstream["real_component_rows_required"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_m56_results": 0,
        "formal_m57_results": 0,
        "m58_authorized": False,
        "boundary": "M57.9 engineering may create only isolated synthetic export receipts. It cannot create humans, real component rows, outcomes, model calls, formal M57 results or M58 authority.",
    }


def measure_fixture_cost(iterations: int = 3) -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    if iterations < 1:
        raise ValueError("iterations must be positive")
    durations: list[float] = []
    artifact_bytes: list[int] = []
    setup_durations: list[float] = []
    for index in range(iterations):
        with TemporaryDirectory(prefix="uruha-m57-9-cost-") as temp, m5610_private_roots(Path(temp)):
            run_id = f"m579-cost-{index}"
            setup_start = perf_counter()
            first_envelope, _secret = recovery_m57._synthetic_setup(Path(temp), run_id)
            delivery = first_envelope.parent.parent
            tokens = {
                role: load_json(delivery / role / "capability-envelope.json")["role_session_token"]
                for role in collection_m57.ROLE_SLOTS
            }
            _complete_synthetic_three_role_ledgers(run_id, tokens)
            preview = inspect_adjudicator_manifest_export(run_id, tokens["adjudicator"])
            setup_durations.append(perf_counter() - setup_start)
            start = perf_counter()
            confirm_and_export_adjudicator_manifest(
                run_id, tokens["adjudicator"], preview["displayed_expected_manifest_hash"], CONFIRMATION_VALUE
            )
            durations.append(perf_counter() - start)
            paths = _paths(run_id)
            artifact_bytes.append(sum(paths[name].stat().st_size for name in ("m57_9_intent", "m57_9_receipt")))
    ordered = sorted(durations)
    return {
        "schema": COST_SCHEMA,
        "version": "1.0.0",
        "status": "isolated_synthetic_export_transaction_cost_not_human_or_production_cost",
        "iterations": iterations,
        "export_transaction_seconds": durations,
        "export_transaction_seconds_min": min(durations),
        "export_transaction_seconds_median": ordered[len(ordered) // 2],
        "export_transaction_seconds_max": max(durations),
        "fixture_setup_and_three_sealed_ledgers_seconds": setup_durations,
        "m57_9_intent_and_receipt_bytes": artifact_bytes,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
        "excludes": [
            "human completion time", "90 real component entries", "participant identity verification",
            "model execution", "target outcomes", "energy", "TLS", "production throughput",
        ],
    }


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or (load_json(LIVE_AUDIT_PATH) if LIVE_AUDIT_PATH.exists() else build_live_audit()))
    cost = deepcopy(cost or load_json(COST_PATH))
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.9 rehearsal cannot be rendered")
    median = cost["export_transaction_seconds_median"]
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.9 adjudicator manifest export</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#080d1b;color:#f6f7ff;font-family:-apple-system,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #414b75;border-radius:20px;background:#11172b;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#192b57,#503558)}}h1{{font-size:42px}}p{{color:#cbd0e5;line-height:1.6}}.flow,.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}.node,.card{{border:1px solid #505d8a;border-radius:15px;background:#0a1022;padding:15px;overflow-wrap:anywhere}}.node b,.card strong,.card span{{display:block}}.node b,.card strong{{color:#b8adff}}.card strong{{font-size:27px}}.danger{{color:#ffb8c4}}.boundary{{border-left:6px solid #dfa752;background:#292116}}@media(max-width:900px){{.flow,.grid{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:560px){{.flow,.grid{{grid-template-columns:1fr}}}}</style></head><body><main><section class="hero"><b>M57.9 · EXPLICIT ADJUDICATOR ACTION</b><h1>三份帳本封存，不等於 manifest 已被授權匯出</h1><p>系統先從三份不可修改的帳本算出 exact manifest hash；adjudicator 再確認「就是這份」，才交給原本的 M57.4 exporter。</p></section><section><h2>從人類標註到模型輸入的最後一道門</h2><div class="flow"><div class="node"><b>1 · 3 SEALS</b>兩位coder<br>一位adjudicator</div><div class="node"><b>2 · MANIFEST PREVIEW</b>30 samples<br>exact hash</div><div class="node"><b>3 · CONFIRM</b>cookie＋CSRF<br>adjudicator click</div><div class="node"><b>4 · INTENT</b>先full-sync<br>不可事後補</div><div class="node"><b>5 · M57.4 EXPORT</b>原validator<br>再次重驗</div><div class="node"><b>6 · RECEIPT</b>manifest＋export<br>完整綁定</div></div></section><section class="grid"><div class="card"><strong>3/3</strong><span>synthetic sealed ledgers</span></div><div class="card"><strong>30 / 60 / 30</strong><span>samples / coder / adjudicator</span></div><div class="card"><strong>0 → 1</strong><span>explicit export receipt</span></div><div class="card"><strong>0</strong><span>automatic exports</span></div><div class="card"><strong>{median:.4f}s</strong><span>median export transaction</span></div><div class="card"><strong class="danger">{audit['real_component_rows_available']}/{audit['real_component_rows_required']}</strong><span>real component rows</span></div></section><section class="boundary"><h2>證據邊界</h2><p>這頁證明：一個已授權adjudicator capability可以在token-free browser看見exact pre-outcome manifest hash，明確確認，並留下intent → unchanged M57.4 export → receipt。它不證明三個人是誰、標註正確、模型預測更好、Equation V1成立或M58已授權；現在real export receipts仍0。</p></section></main></body></html>'''


def serve_dashboard(port: int) -> None:
    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if urllib.parse.urlparse(self.path).path not in {"/", "/dashboard"}:
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
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--serve-exportable", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    actions.add_argument("--launch", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    actions.add_argument("--write-rehearsal", action="store_true")
    actions.add_argument("--write-live-audit", action="store_true")
    actions.add_argument("--measure-cost", action="store_true")
    actions.add_argument("--dashboard", type=int, metavar="PORT")
    args = parser.parse_args()
    if args.serve_exportable:
        run_id, role, envelope, port_text = args.serve_exportable
        if role not in collection_m57.ROLE_SLOTS:
            raise SystemExit("invalid role")
        serve_exportable_collection(run_id, role, envelope, int(port_text))
    elif args.launch:
        run_id, role, envelope, port_text = args.launch
        if role not in collection_m57.ROLE_SLOTS:
            raise SystemExit("invalid role")
        launch_export_runtime(run_id, role, envelope, int(port_text))
    elif args.write_rehearsal:
        value = build_engineering_rehearsal()
        RESULT_PATH.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.write_live_audit:
        value = build_live_audit()
        LIVE_AUDIT_PATH.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.measure_cost:
        value = measure_fixture_cost()
        COST_PATH.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.dashboard is not None:
        serve_dashboard(args.dashboard)


if __name__ == "__main__":
    main()
