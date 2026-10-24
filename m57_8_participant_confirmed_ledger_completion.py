#!/usr/bin/env python3
"""M57.8 explicit participant confirmation for one complete M57.4 ledger.

The browser keeps the M57.4 bearer token and M57.6 recovery secret in process
memory only.  A participant sees a completion digest and must explicitly POST a
CSRF-bound confirmation before the exact M57.4 ledger/seal schema is created.
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
import m57_4_component_evidence_collection as collection_m57
import m57_5_participant_capability_issuance as capability_m57
import m57_6_crash_recoverable_participant_capability as recovery_m57
import m57_7_auditable_participant_runtime_launcher as runtime_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs" / "m57_8_participant_confirmed_ledger_completion_v1.json"
RESULT_PATH = ROOT / "analysis" / "m57_8_participant_confirmed_ledger_completion_rehearsal_2026-09-05.json"
LIVE_AUDIT_PATH = ROOT / "analysis" / "m57_8_participant_confirmed_ledger_completion_live_audit_2026-09-05.json"
COST_PATH = ROOT / "analysis" / "m57_8_participant_confirmed_ledger_completion_fixture_cost_2026-09-05.json"
M57_7_LIVE_AUDIT_PATH = ROOT / "analysis" / "m57_7_auditable_participant_runtime_launcher_live_audit_2026-09-05.json"

CONFIRMATION_VALUE = "confirm_exact_complete_ledger_and_seal"
INTENT_SCHEMA = "uruha_m57_8_participant_ledger_seal_intent_v1"
RECEIPT_SCHEMA = "uruha_m57_8_participant_ledger_completion_receipt_v1"
REHEARSAL_SCHEMA = "uruha_m57_8_participant_confirmed_ledger_completion_rehearsal_v1"
LIVE_AUDIT_SCHEMA = "uruha_m57_8_participant_confirmed_ledger_completion_live_audit_v1"
COST_SCHEMA = "uruha_m57_8_participant_confirmed_ledger_completion_fixture_cost_v1"


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
        "participant_confirmation", "transaction", "browser", "runtime_launch", "public_functions",
        "formal_boundary", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_8_participant_confirmed_ledger_completion_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_before_any_real_participant_collection":
        errors.append("contract.status")
    if contract.get("single_changed_variable") != "participant_confirmed_token_free_complete_ledger_seal":
        errors.append("contract.variable")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 8:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    participant = contract.get("participant_confirmation") or {}
    if participant.get("required_unique_sample_count") != 30 or participant.get("required_source_view_count") != 30:
        errors.append("participant.counts")
    if participant.get("confirmation_value") != CONFIRMATION_VALUE:
        errors.append("participant.confirmation")
    for name in ("explicit_checkbox_required", "displayed_draft_ledger_hash_must_match_post"):
        if participant.get(name) is not True:
            errors.append(f"participant.{name}")
    if participant.get("automatic_seal_after_last_save") is not False or participant.get("other_private_coder_ledger_visible") is not False:
        errors.append("participant.boundary")
    transaction = contract.get("transaction") or {}
    for name in (
        "existing_single_writer_lock_required", "outcome_absence_revalidated_under_lock",
        "complete_ledger_revalidated_under_lock", "expected_draft_hash_revalidated_under_lock",
        "durable_intent_before_ledger_mutation", "unchanged_m57_4_ledger_and_seal_schema",
        "completion_receipt_binds_intent_ledger_and_seal", "identical_interrupted_or_completed_replay_allowed",
    ):
        if transaction.get(name) is not True:
            errors.append(f"transaction.{name}")
    if transaction.get("nonidentical_replay_allowed") is not False or transaction.get("sealed_ledger_mutation_allowed") is not False:
        errors.append("transaction.fail_closed")
    browser = contract.get("browser") or {}
    if browser.get("seal_post_fields") != ["csrf", "expected_ledger_hash", "confirmation"]:
        errors.append("browser.fields")
    for name in ("loopback_only", "http_only_same_site_cookie_reused", "csrf_required_for_save_and_seal", "post_seal_save_or_seal_form_visible"):
        expected = False if name == "post_seal_save_or_seal_form_visible" else True
        if browser.get(name) is not expected:
            errors.append(f"browser.{name}")
    if browser.get("role_token_or_recovery_secret_in_url_form_html_cookie_receipt") is not False:
        errors.append("browser.secret_surface")
    runtime = contract.get("runtime_launch") or {}
    if runtime.get("m57_7_full_audit_precedes_exec") is not True:
        errors.append("runtime.audit")
    if runtime.get("public_arguments") != ["run_id", "role_slot", "envelope_path", "port"]:
        errors.append("runtime.arguments")
    if runtime.get("collection_time_download_install_or_repair_calls") != 0 or runtime.get("role_token_or_recovery_secret_argument") is not False:
        errors.append("runtime.boundary")
    expected_public = {
        "inspect_participant_ledger_completion": ["run_id", "role_slot", "session_token"],
        "confirm_and_seal_participant_ledger": [
            "run_id", "role_slot", "session_token", "expected_ledger_hash", "confirmation"
        ],
    }
    if contract.get("public_functions") != expected_public:
        errors.append("public_functions")
    actual_public = {
        "inspect_participant_ledger_completion": list(inspect.signature(inspect_participant_ledger_completion).parameters),
        "confirm_and_seal_participant_ledger": list(inspect.signature(confirm_and_seal_participant_ledger).parameters),
    }
    if actual_public != expected_public:
        errors.append("public_signatures")
    formal = contract.get("formal_boundary") or {}
    if formal.get("target_outcome_access_count") != 0 or formal.get("model_call_count") != 0:
        errors.append("formal.access")
    if formal.get("synthetic_rehearsal_is_real_human_evidence") is not False or formal.get("participant_confirmation_proves_identity_or_label_correctness") is not False or formal.get("m58_authorized") is not False:
        errors.append("formal.claim")
    return {"valid": not errors, "errors": errors, "contract_hash": digest(contract), "binding_count": len(dependencies)}


def _completion_paths(run_id: str, role_slot: str) -> dict[str, Path]:
    if role_slot not in collection_m57.ROLE_SLOTS:
        raise ValueError("unknown M57.8 role slot")
    paths = collection_m57._paths(run_id)
    return {
        **paths,
        "m57_8_intent": paths["commitments"] / f"m57_8_{role_slot}_participant_seal_intent.json",
        "m57_8_receipt": paths["commitments"] / f"m57_8_{role_slot}_participant_completion_receipt.json",
    }


def _role_context_under_lock(run_id: str, role_slot: str, session_token: str, *, require_complete: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], dict[str, Any], dict[str, dict[str, Any]] | None, dict[str, dict[str, Any]] | None]:
    context = collection_m57._context(run_id)
    paths = _completion_paths(run_id, role_slot)
    collection_m57._no_outcome(paths, "participant completion")
    mode = collection_m57._load_mode(run_id, context, paths)
    collection_m57._authorize(mode, role_slot, session_token)
    coder_ledgers = coder_seals = None
    if role_slot == "adjudicator":
        coder_ledgers, coder_seals = collection_m57._load_sealed_coders(run_id, mode, context, paths)
    ledger = collection_m57._load_role_ledger(
        role_slot, mode, context, paths, require_complete=require_complete,
        coder_ledgers=coder_ledgers, coder_seals=coder_seals,
    )
    return context, mode, paths, ledger, coder_ledgers, coder_seals


def _intent_errors(value: dict[str, Any], mode: dict[str, Any], role_slot: str) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "role_slot", "participant_pseudonym",
        "confirmation_value", "expected_draft_ledger_hash", "expected_entry_count", "expected_source_view_count",
        "created_at_utc", "target_outcome_access_count", "model_call_count", "intent_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["intent.fields"]
    errors: list[str] = []
    expected = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "participant_confirmed_exact_complete_ledger_before_seal",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "role_slot": role_slot,
        "participant_pseudonym": mode["participants"][role_slot]["pseudonym"],
        "confirmation_value": CONFIRMATION_VALUE,
        "expected_entry_count": 30,
        "expected_source_view_count": 30,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    for name, expected_value in expected.items():
        if value.get(name) != expected_value:
            errors.append(f"intent.{name}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("expected_draft_ledger_hash", ""))):
        errors.append("intent.draft_hash")
    if not collection_m57._valid_timestamp(value.get("created_at_utc")):
        errors.append("intent.timestamp")
    if value.get("intent_hash") != digest(_hashless(value, "intent_hash")):
        errors.append("intent.hash")
    return errors


def _receipt_errors(value: dict[str, Any], mode: dict[str, Any], ledger: dict[str, Any], seal: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "role_slot", "participant_pseudonym",
        "intent_hash", "expected_draft_ledger_hash", "final_ledger_hash", "m57_4_seal_hash", "sealed_at_utc",
        "completed_at_utc", "target_outcome_access_count", "model_call_count", "formal_evidence_created",
        "m58_authorized", "receipt_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return ["receipt.fields"]
    role_slot = ledger["role_slot"]
    expected = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "participant_confirmation_and_m57_4_seal_full_sync_completed",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "role_slot": role_slot,
        "participant_pseudonym": mode["participants"][role_slot]["pseudonym"],
        "intent_hash": intent["intent_hash"],
        "expected_draft_ledger_hash": intent["expected_draft_ledger_hash"],
        "final_ledger_hash": ledger["ledger_hash"],
        "m57_4_seal_hash": seal["seal_hash"],
        "sealed_at_utc": ledger["sealed_at_utc"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    errors: list[str] = []
    for name, expected_value in expected.items():
        if value.get(name) != expected_value:
            errors.append(f"receipt.{name}")
    if not collection_m57._valid_timestamp(value.get("completed_at_utc")):
        errors.append("receipt.timestamp")
    if value.get("receipt_hash") != digest(_hashless(value, "receipt_hash")):
        errors.append("receipt.hash")
    return errors


def _inspect_under_lock(run_id: str, role_slot: str, session_token: str) -> dict[str, Any]:
    context, mode, paths, ledger, _coder_ledgers, _coder_seals = _role_context_under_lock(
        run_id, role_slot, session_token, require_complete=False
    )
    order = collection_m57._sample_order(context)
    entries = ledger["entries"]
    views = ledger["source_views"]
    missing = [sample_id for sample_id in order if sample_id not in entries]
    complete = not missing and set(views) == set(order)
    intent = receipt = seal = None
    intent_errors: list[str] = []
    receipt_errors: list[str] = []
    seal_errors: list[str] = []
    if paths["m57_8_intent"].exists():
        intent = load_json(paths["m57_8_intent"])
        intent_errors = _intent_errors(intent, mode, role_slot)
    if paths[f"seal_{role_slot}"].exists():
        seal = load_json(paths[f"seal_{role_slot}"])
        seal_errors = collection_m57._validate_seal(seal, ledger, mode)
    if paths["m57_8_receipt"].exists():
        receipt = load_json(paths["m57_8_receipt"])
        if intent is None or seal is None:
            receipt_errors = ["receipt.missing_dependency"]
        else:
            receipt_errors = _receipt_errors(receipt, mode, ledger, seal, intent)
    errors = [*intent_errors, *seal_errors, *receipt_errors]
    if ledger["status"] == "sealed_private_role_ledger" and intent is None:
        errors.append("sealed_without_m57_8_participant_intent")
    if ledger["status"] == "open_private_role_ledger" and seal is not None:
        errors.append("open_ledger_has_seal")
    if errors:
        raise ValueError("invalid M57.8 completion state: " + "; ".join(errors))
    completed = receipt is not None
    pending = intent is not None and not completed
    return {
        "status": "participant_confirmed_ledger_sealed" if completed else (
            "participant_seal_transaction_pending" if pending else "participant_ledger_open"
        ),
        "run_id": run_id,
        "role_slot": role_slot,
        "participant_pseudonym": ledger["participant_pseudonym"],
        "ledger_status": ledger["status"],
        "completed_unique_sample_count": len(entries),
        "source_view_count": len(views),
        "revision_count": ledger["revision_count"],
        "required_sample_count": 30,
        "missing_sample_ids": missing,
        "complete": complete,
        "can_confirm_and_seal": complete and ledger["status"] == "open_private_role_ledger" and intent is None,
        "can_resume_identical_confirmation": pending,
        "displayed_expected_ledger_hash": intent["expected_draft_ledger_hash"] if intent else ledger["ledger_hash"],
        "final_ledger_hash": ledger["ledger_hash"] if ledger["status"] == "sealed_private_role_ledger" else None,
        "seal_hash": seal["seal_hash"] if seal else None,
        "receipt_hash": receipt["receipt_hash"] if receipt else None,
        "other_private_coder_ledger_visible": role_slot == "adjudicator",
        "raw_role_token_returned": False,
        "raw_recovery_secret_returned": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def inspect_participant_ledger_completion(run_id: str, role_slot: str, session_token: str) -> dict[str, Any]:
    """Return a token-free completion projection while holding the upstream lock."""
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.8 contract invalid: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        return _inspect_under_lock(run_id, role_slot, session_token)


def _new_intent(mode: dict[str, Any], ledger: dict[str, Any], expected_ledger_hash: str) -> dict[str, Any]:
    value = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "participant_confirmed_exact_complete_ledger_before_seal",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "role_slot": ledger["role_slot"],
        "participant_pseudonym": ledger["participant_pseudonym"],
        "confirmation_value": CONFIRMATION_VALUE,
        "expected_draft_ledger_hash": expected_ledger_hash,
        "expected_entry_count": 30,
        "expected_source_view_count": 30,
        "created_at_utc": collection_m57._utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    value["intent_hash"] = digest(value)
    return value


def _new_seal(mode: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": collection_m57.SEAL_SCHEMA,
        "version": "1.0.0",
        "status": "complete_private_role_ledger_sha256_sealed",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "role_slot": ledger["role_slot"],
        "participant_pseudonym": ledger["participant_pseudonym"],
        "ledger_hash": ledger["ledger_hash"],
        "entry_count": 30,
        "source_view_count": 30,
        "revision_count": ledger["revision_count"],
        "sealed_at_utc": ledger["sealed_at_utc"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    value["seal_hash"] = collection_m57.digest(value)
    return value


def _new_receipt(mode: dict[str, Any], ledger: dict[str, Any], seal: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "participant_confirmation_and_m57_4_seal_full_sync_completed",
        "run_id": mode["run_id"],
        "mode_hash": mode["mode_hash"],
        "role_slot": ledger["role_slot"],
        "participant_pseudonym": ledger["participant_pseudonym"],
        "intent_hash": intent["intent_hash"],
        "expected_draft_ledger_hash": intent["expected_draft_ledger_hash"],
        "final_ledger_hash": ledger["ledger_hash"],
        "m57_4_seal_hash": seal["seal_hash"],
        "sealed_at_utc": ledger["sealed_at_utc"],
        "completed_at_utc": collection_m57._utc_now(),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    value["receipt_hash"] = digest(value)
    return value


def confirm_and_seal_participant_ledger(run_id: str, role_slot: str, session_token: str, expected_ledger_hash: str, confirmation: str) -> dict[str, Any]:
    """Atomically bind explicit confirmation to one exact complete M57.4 ledger."""
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.8 contract invalid: " + "; ".join(contract["errors"]))
    if confirmation != CONFIRMATION_VALUE:
        raise PermissionError("M57.8 explicit participant confirmation is required")
    if not isinstance(expected_ledger_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_ledger_hash):
        raise ValueError("M57.8 expected ledger hash must be one SHA-256 value")
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        _context, mode, paths, ledger, coder_ledgers, coder_seals = _role_context_under_lock(
            run_id, role_slot, session_token, require_complete=True
        )
        intent_path = paths["m57_8_intent"]
        receipt_path = paths["m57_8_receipt"]
        seal_path = paths[f"seal_{role_slot}"]
        if intent_path.exists():
            intent = load_json(intent_path)
            errors = _intent_errors(intent, mode, role_slot)
            if errors:
                raise ValueError("invalid M57.8 participant intent: " + "; ".join(errors))
            if not hmac.compare_digest(intent["expected_draft_ledger_hash"], expected_ledger_hash):
                raise PermissionError("M57.8 nonidentical participant confirmation replay denied")
            intent_write = "validated_existing_identical"
        else:
            if ledger["status"] != "open_private_role_ledger":
                raise PermissionError("M57.8 cannot attribute an already sealed ledger to a missing participant intent")
            if not hmac.compare_digest(ledger["ledger_hash"], expected_ledger_hash):
                raise PermissionError("M57.8 displayed ledger hash is stale")
            intent = _new_intent(mode, ledger, expected_ledger_hash)
            durable_m56._durable_atomic_write_json(intent_path, intent, exclusive=True)
            intent_write = "created_full_sync_before_ledger_mutation"
        if ledger["status"] == "open_private_role_ledger":
            if not hmac.compare_digest(ledger["ledger_hash"], intent["expected_draft_ledger_hash"]):
                raise PermissionError("M57.8 ledger changed after participant confirmation")
            ledger["status"] = "sealed_private_role_ledger"
            ledger["sealed_at_utc"] = collection_m57._utc_now()
            ledger["ledger_hash"] = collection_m57.digest(collection_m57._ledger_hashless(ledger))
            errors = collection_m57._validate_ledger(
                ledger, mode, _context, require_complete=True,
                coder_ledgers=coder_ledgers, coder_seals=coder_seals,
            )
            if errors:
                raise AssertionError("constructed M57.4 sealed ledger invalid: " + "; ".join(errors))
            durable_m56._durable_atomic_write_json(paths[f"ledger_{role_slot}"], ledger)
            ledger_write = "sealed_full_sync"
        else:
            ledger_write = "validated_existing_sealed"
        if seal_path.exists():
            seal = load_json(seal_path)
            errors = collection_m57._validate_seal(seal, ledger, mode)
            if errors:
                raise ValueError("invalid existing M57.4 seal: " + "; ".join(errors))
            seal_write = "validated_existing_identical"
        else:
            seal = _new_seal(mode, ledger)
            errors = collection_m57._validate_seal(seal, ledger, mode)
            if errors:
                raise AssertionError("constructed M57.4 seal invalid: " + "; ".join(errors))
            durable_m56._durable_atomic_write_json(seal_path, seal, exclusive=True)
            seal_write = "created_exact_m57_4_seal_full_sync"
        if receipt_path.exists():
            receipt = load_json(receipt_path)
            errors = _receipt_errors(receipt, mode, ledger, seal, intent)
            if errors:
                raise ValueError("invalid existing M57.8 receipt: " + "; ".join(errors))
            receipt_write = "validated_existing_identical"
        else:
            receipt = _new_receipt(mode, ledger, seal, intent)
            errors = _receipt_errors(receipt, mode, ledger, seal, intent)
            if errors:
                raise AssertionError("constructed M57.8 receipt invalid: " + "; ".join(errors))
            durable_m56._durable_atomic_write_json(receipt_path, receipt, exclusive=True)
            receipt_write = "created_full_sync"
        return {
            "status": "m57_8_participant_confirmation_and_ledger_seal_completed",
            "run_id": run_id,
            "role_slot": role_slot,
            "intent_write": intent_write,
            "ledger_write": ledger_write,
            "seal_write": seal_write,
            "receipt_write": receipt_write,
            "expected_draft_ledger_hash": intent["expected_draft_ledger_hash"],
            "final_ledger_hash": ledger["ledger_hash"],
            "m57_4_seal_hash": seal["seal_hash"],
            "completion_receipt_hash": receipt["receipt_hash"],
            "raw_role_token_returned": False,
            "raw_recovery_secret_returned": False,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }


def _progress_html(progress: dict[str, Any], csrf_token: str, error: str = "") -> str:
    complete = progress["complete"]
    sealed = progress["receipt_hash"] is not None
    pending = progress["can_resume_identical_confirmation"]
    error_html = f'<p class="m578-error">{html.escape(error)}</p>' if error else ""
    missing_text = "、".join(progress["missing_sample_ids"][:5])
    if len(progress["missing_sample_ids"]) > 5:
        missing_text += "…"
    if not missing_text:
        missing_text = "0"
    form = ""
    if progress["can_confirm_and_seal"] or pending:
        label = "恢復同一筆封存" if pending else "確認這 30 題並封存"
        form = f'''<form method="post" action="/seal" class="m578-seal-form">
<input type="hidden" name="csrf" value="{html.escape(csrf_token)}">
<input type="hidden" name="expected_ledger_hash" value="{html.escape(progress['displayed_expected_ledger_hash'])}">
<label><input type="checkbox" name="confirmation" value="{CONFIRMATION_VALUE}" required> 我確認這 30 題與上方雜湊是我要封存的版本；封存後不能再修改。</label>
<button class="m578-seal">{label}</button></form>'''
    state = "已由參與者確認並封存" if sealed else ("確認已落盤，等待完成封存" if pending else ("30/30，可確認封存" if complete else "尚未完成"))
    return f'''<section class="m578-panel"><b>M57.8 · PARTICIPANT CONFIRMATION</b><h2>{state}</h2>{error_html}
<div class="m578-grid"><div><strong>{progress['completed_unique_sample_count']}/30</strong><span>已完成題目</span></div><div><strong>{progress['source_view_count']}/30</strong><span>來源已看</span></div><div><strong>{progress['revision_count']}</strong><span>revision</span></div><div><strong>{len(progress['missing_sample_ids'])}</strong><span>尚缺</span></div></div>
<p>缺少題目：{html.escape(missing_text)}</p><p>你正在確認的ledger hash：</p><code>{html.escape(progress['displayed_expected_ledger_hash'])}</code>
{('<p>最終 M57.4 seal：</p><code>' + html.escape(progress['seal_hash'] or '') + '</code><p>M57.8 completion receipt：</p><code>' + html.escape(progress['receipt_hash'] or '') + '</code>') if sealed else ''}{form}
<p class="m578-boundary">這只封存你自己的 pre-outcome ledger；不會顯示另一位 coder 的內容，也不代表標註正確或正式 M57 已成立。</p></section>'''


def _render_participant_page(run_id: str, role_slot: str, role_token: str, sample_id: str, csrf_token: str, error: str = "") -> str:
    before = inspect_participant_ledger_completion(run_id, role_slot, role_token)
    if before["ledger_status"] == "open_private_role_ledger" and not before["can_resume_identical_confirmation"]:
        page = capability_m57._render_secure_page(run_id, role_slot, role_token, sample_id, csrf_token)
        page = page.replace(
            f"<title>M57.5 {html.escape(role_slot)}</title>",
            f"<title>M57.8 {html.escape(role_slot)} participant completion</title>",
        ).replace(
            f"<b>M57.5 · {html.escape(role_slot)}</b>",
            f"<b>M57.8 · {html.escape(role_slot)} · PRE-OUTCOME COLLECTION</b>",
        )
        progress = inspect_participant_ledger_completion(run_id, role_slot, role_token)
        panel = _progress_html(progress, csrf_token, error)
        style = """<style>.m578-panel{background:#10242b;border:2px solid #65d2af;border-radius:18px;padding:20px;margin-bottom:16px}.m578-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.m578-grid div{background:#07181e;padding:12px;border-radius:10px}.m578-grid strong,.m578-grid span{display:block}.m578-grid strong{font-size:24px;color:#76dfba}.m578-panel code{display:block;overflow-wrap:anywhere;background:#061216;padding:10px}.m578-seal-form{margin-top:16px;padding:14px;border:1px solid #d9a85c}.m578-seal{background:#e5ae57}.m578-error{color:#ffabb8}.m578-boundary{color:#a9bdc5}@media(max-width:650px){.m578-grid{grid-template-columns:repeat(2,1fr)}}</style>"""
        return page.replace("</head>", style + "</head>").replace("</section>", "</section>" + panel, 1)
    progress = before
    panel = _progress_html(progress, csrf_token, error)
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.8 參與者封存確認</title><style>body{{font-family:-apple-system,sans-serif;background:#07151a;color:#eefbff;margin:0}}main{{max-width:900px;margin:auto;padding:24px}}.m578-panel{{background:#10242b;border:2px solid #65d2af;border-radius:18px;padding:20px}}.m578-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}.m578-grid div{{background:#07181e;padding:12px;border-radius:10px}}.m578-grid strong,.m578-grid span{{display:block}}code{{display:block;overflow-wrap:anywhere;background:#061216;padding:10px}}button{{padding:12px 18px}}.m578-error{{color:#ffabb8}}@media(max-width:650px){{.m578-grid{{grid-template-columns:repeat(2,1fr)}}}}</style></head><body><main>{panel}</main></body></html>'''


def _make_completion_server(run_id: str, role_slot: str, envelope_path: str, port: int, recovery_secret: str) -> tuple[ThreadingHTTPServer, dict[str, Any]]:
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

        def _send_text(self, text: str, status: int) -> None:
            self._headers(status, html.escape(text).encode("utf-8"))

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
            if self.path not in {"/save", "/seal"}:
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
                if set(form) != {"expected_ledger_hash", "confirmation"} or any(len(values) != 1 for values in form.values()):
                    raise ValueError("M57.8 seal form fields differ from the frozen contract")
                confirm_and_seal_participant_ledger(
                    run_id, role_slot, role_token,
                    form["expected_ledger_hash"][0], form["confirmation"][0],
                )
                self._headers(303, location="/")
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                try:
                    body = _render_participant_page(run_id, role_slot, role_token, sample_id, csrf_token, str(exc)).encode("utf-8")
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


def serve_completable_collection(run_id: str, role_slot: str, envelope_path: str, port: int) -> None:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.8 contract invalid before secret input: " + "; ".join(contract["errors"]))
    recovery_secret = recovery_m57._interactive_recovery_secret(run_id, role_slot)
    server, metadata = _make_completion_server(run_id, role_slot, envelope_path, port, recovery_secret)
    del metadata, recovery_secret
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_launch_spec(run_id: str, role_slot: str, envelope_path: str | Path, port: int) -> dict[str, Any]:
    spec = runtime_m57.build_launch_spec(run_id, role_slot, envelope_path, port)
    argv = list(spec["argv"])
    argv[3] = str(ROOT / "m57_8_participant_confirmed_ledger_completion.py")
    argv[4] = "--serve-completable"
    return {
        **spec,
        "argv": argv,
        "m57_7_full_audit_ready_before_exec": spec["audit"]["ready"],
        "m57_8_entrypoint": True,
    }


def launch_completion_runtime(run_id: str, role_slot: str, envelope_path: str | Path, port: int) -> None:
    spec = build_launch_spec(run_id, role_slot, envelope_path, port)
    os.execve(spec["executable"], spec["argv"], spec["environment"])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        del request, fp, code, msg, headers, newurl
        return None


def _fill_synthetic_coder(run_id: str, role_slot: str, token: str, count: int = 30) -> None:
    context = collection_m57._context(run_id)
    for index, sample_id in enumerate(collection_m57._sample_order(context)[:count], 1):
        view = collection_m57.record_component_source_view(run_id, role_slot, token, sample_id)
        payload = collection_m57._synthetic_coder_payload(
            view["source_information"], variant="a" if role_slot == "coder_a" else "b", index=index
        )
        collection_m57.save_component_evidence_entry(run_id, role_slot, token, sample_id, payload)


def _http_seal_exchange(server: ThreadingHTTPServer, raw_token: str, recovery_secret: str) -> dict[str, Any]:
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
        hash_match = re.search(r'name="expected_ledger_hash" value="([0-9a-f]{64})"', page)
        if not csrf_match or not hash_match or CONFIRMATION_VALUE not in page:
            raise AssertionError("explicit completion form absent")
        encoded = urllib.parse.urlencode({
            "csrf": csrf_match.group(1),
            "expected_ledger_hash": hash_match.group(1),
            "confirmation": CONFIRMATION_VALUE,
        }).encode("utf-8")
        try:
            opener.open(urllib.request.Request(
                base + "/seal", data=encoded,
                headers={"Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            ))
            raise AssertionError("expected seal redirect")
        except urllib.error.HTTPError as response:
            seal_status = response.code
            seal_location = response.headers.get("Location", "")
        final_response = opener.open(urllib.request.Request(base + seal_location, headers={"Cookie": cookie}, method="GET"))
        final_page = final_response.read().decode("utf-8")
        surfaces = [base, location, set_cookie, cookie, page, seal_location, final_page]
        return {
            "first_status": first_status,
            "page_status": page_response.status,
            "seal_status": seal_status,
            "final_status": final_response.status,
            "draft_hash": hash_match.group(1),
            "explicit_confirmation_form_visible": True,
            "sealed_receipt_visible": "已由參與者確認並封存" in final_page,
            "save_or_seal_form_visible_after_completion": '<form method="post"' in final_page.lower(),
            "raw_role_token_surface_occurrences": sum(raw_token in item for item in surfaces),
            "recovery_secret_surface_occurrences": sum(recovery_secret in item for item in surfaces),
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def build_engineering_rehearsal() -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    with TemporaryDirectory(prefix="uruha-m57-8-completion-") as temp, m5610_private_roots(Path(temp)):
        run_id = "m578-forged-no-human-completion"
        envelope, recovery_secret = recovery_m57._synthetic_setup(Path(temp), run_id)
        raw_token = load_json(envelope)["role_session_token"]
        before = inspect_participant_ledger_completion(run_id, "coder_a", raw_token)
        _fill_synthetic_coder(run_id, "coder_a", raw_token, 30)
        complete_open = inspect_participant_ledger_completion(run_id, "coder_a", raw_token)
        server, metadata = _make_completion_server(run_id, "coder_a", str(envelope), 0, recovery_secret)
        exchange = _http_seal_exchange(server, raw_token, recovery_secret)
        after = inspect_participant_ledger_completion(run_id, "coder_a", raw_token)
        paths = _completion_paths(run_id, "coder_a")
        intent = load_json(paths["m57_8_intent"])
        receipt = load_json(paths["m57_8_receipt"])
        ledger = load_json(paths["ledger_coder_a"])
        seal = load_json(paths["seal_coder_a"])
        durable_text = canonical_json({"intent": intent, "receipt": receipt})
        value = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "synthetic_explicit_participant_completion_mechanics_only",
            "run_id": run_id,
            "data_kind": collection_m57.SYNTHETIC_KIND,
            "contract_hash": validate_contract()["contract_hash"],
            "before": {
                "completed_unique_sample_count": before["completed_unique_sample_count"],
                "can_confirm_and_seal": before["can_confirm_and_seal"],
            },
            "after_last_save_before_confirmation": {
                "completed_unique_sample_count": complete_open["completed_unique_sample_count"],
                "ledger_status": complete_open["ledger_status"],
                "can_confirm_and_seal": complete_open["can_confirm_and_seal"],
                "automatic_seal_count": int(complete_open["seal_hash"] is not None),
            },
            "browser": exchange,
            "completion": {
                "ledger_status": after["ledger_status"],
                "participant_receipt_present": bool(after["receipt_hash"]),
                "intent_precedes_seal": intent["created_at_utc"] <= ledger["sealed_at_utc"],
                "draft_hash_matches_display": intent["expected_draft_ledger_hash"] == exchange["draft_hash"],
                "final_ledger_hash_matches_seal": ledger["ledger_hash"] == seal["ledger_hash"],
                "seal_hash_matches_receipt": seal["seal_hash"] == receipt["m57_4_seal_hash"],
                "raw_role_token_occurrences_in_m57_8_durable_state": durable_text.count(raw_token),
                "raw_recovery_secret_occurrences_in_m57_8_durable_state": durable_text.count(recovery_secret),
            },
            "runtime": {
                "m57_7_project_runtime_ready": runtime_m57.audit_runtime()["ready"],
                "collection_time_download_install_or_repair_calls": 0,
            },
            "server_metadata_contains_raw_role_token": raw_token in canonical_json(metadata),
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
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "synthetic_explicit_participant_completion_mechanics_only":
        errors.append("rehearsal.schema_or_status")
    if value.get("rehearsal_hash") != digest(_hashless(value, "rehearsal_hash")):
        errors.append("rehearsal.hash")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    expected = {
        ("before", "completed_unique_sample_count"): 0,
        ("before", "can_confirm_and_seal"): False,
        ("after_last_save_before_confirmation", "completed_unique_sample_count"): 30,
        ("after_last_save_before_confirmation", "ledger_status"): "open_private_role_ledger",
        ("after_last_save_before_confirmation", "can_confirm_and_seal"): True,
        ("after_last_save_before_confirmation", "automatic_seal_count"): 0,
        ("browser", "first_status"): 303,
        ("browser", "page_status"): 200,
        ("browser", "seal_status"): 303,
        ("browser", "final_status"): 200,
        ("browser", "explicit_confirmation_form_visible"): True,
        ("browser", "sealed_receipt_visible"): True,
        ("browser", "save_or_seal_form_visible_after_completion"): False,
        ("browser", "raw_role_token_surface_occurrences"): 0,
        ("browser", "recovery_secret_surface_occurrences"): 0,
        ("completion", "ledger_status"): "sealed_private_role_ledger",
        ("completion", "participant_receipt_present"): True,
        ("completion", "intent_precedes_seal"): True,
        ("completion", "draft_hash_matches_display"): True,
        ("completion", "final_ledger_hash_matches_seal"): True,
        ("completion", "seal_hash_matches_receipt"): True,
        ("completion", "raw_role_token_occurrences_in_m57_8_durable_state"): 0,
        ("completion", "raw_recovery_secret_occurrences_in_m57_8_durable_state"): 0,
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
        raise PermissionError("invalid saved M57.8 rehearsal: " + "; ".join(report["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    upstream = load_json(M57_7_LIVE_AUDIT_PATH)
    value = {
        "schema": LIVE_AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "live_external_evidence_unchanged_after_m57_8_engineering",
        "m57_7_project_runtime_ready": upstream["project_runtime_ready"],
        "real_participant_completion_receipts": 0,
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
        "boundary": "M57.8 engineering may create only isolated synthetic confirmation receipts. It cannot create humans, real component rows, outcomes, model calls, formal M57 results or M58 authority.",
    }
    return value


def measure_fixture_cost(iterations: int = 3) -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    if iterations < 1:
        raise ValueError("iterations must be positive")
    durations: list[float] = []
    artifact_bytes: list[int] = []
    setup_durations: list[float] = []
    for index in range(iterations):
        with TemporaryDirectory(prefix="uruha-m57-8-cost-") as temp, m5610_private_roots(Path(temp)):
            run_id = f"m578-cost-{index}"
            setup_start = perf_counter()
            envelope, _secret = recovery_m57._synthetic_setup(Path(temp), run_id)
            token = load_json(envelope)["role_session_token"]
            _fill_synthetic_coder(run_id, "coder_a", token, 30)
            progress = inspect_participant_ledger_completion(run_id, "coder_a", token)
            setup_durations.append(perf_counter() - setup_start)
            start = perf_counter()
            confirm_and_seal_participant_ledger(
                run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], CONFIRMATION_VALUE
            )
            durations.append(perf_counter() - start)
            paths = _completion_paths(run_id, "coder_a")
            artifact_bytes.append(sum(paths[name].stat().st_size for name in ("m57_8_intent", "m57_8_receipt")))
    ordered = sorted(durations)
    value = {
        "schema": COST_SCHEMA,
        "version": "1.0.0",
        "status": "isolated_synthetic_completion_transaction_cost_not_human_or_production_cost",
        "iterations": iterations,
        "completion_transaction_seconds": durations,
        "completion_transaction_seconds_min": min(durations),
        "completion_transaction_seconds_median": ordered[len(ordered) // 2],
        "completion_transaction_seconds_max": max(durations),
        "fixture_setup_and_30_entry_seconds": setup_durations,
        "m57_8_intent_and_receipt_bytes": artifact_bytes,
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
    return value


def render_dashboard(rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None, cost: dict[str, Any] | None = None) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or (load_json(LIVE_AUDIT_PATH) if LIVE_AUDIT_PATH.exists() else build_live_audit()))
    cost = deepcopy(cost or load_json(COST_PATH))
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.8 rehearsal cannot be rendered")
    median = cost["completion_transaction_seconds_median"]
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.8 參與者完成封存</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#07141a;color:#f5fbff;font-family:-apple-system,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #335c69;border-radius:20px;background:#0d2027;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#123e48,#4d304f)}}h1{{font-size:44px}}p{{color:#c7dbe3;line-height:1.6}}.flow,.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}.node,.card{{border:1px solid #466b78;border-radius:15px;background:#08191f;padding:15px;overflow-wrap:anywhere}}.node b,.card strong,.card span{{display:block}}.node b,.card strong{{color:#80e6c4}}.card strong{{font-size:28px}}.danger{{color:#ffb8c4}}.boundary{{border-left:6px solid #dfa752;background:#292116}}@media(max-width:900px){{.flow,.grid{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:560px){{.flow,.grid{{grid-template-columns:1fr}}}}</style></head><body><main><section class="hero"><b>M57.8 · EXPLICIT HUMAN ACTION</b><h1>30 題填完，不等於參與者已經同意封存</h1><p>系統先顯示完成數與精確雜湊；參與者再用獨立的一次確認，把「這就是我要交付的版本」寫成可追溯證據。</p></section><section><h2>最後一步現在真的走得完</h2><div class="flow"><div class="node"><b>1 · SAVE</b>每題append-only<br>不自動seal</div><div class="node"><b>2 · 30/30</b>完整性重驗<br>仍可修改</div><div class="node"><b>3 · HASH PREVIEW</b>顯示draft hash<br>沒有token</div><div class="node"><b>4 · CONFIRM</b>cookie＋CSRF<br>participant click</div><div class="node"><b>5 · INTENT</b>先full-sync<br>再改ledger</div><div class="node"><b>6 · SEAL</b>原M57.4 schema<br>receipt綁定</div></div></section><section class="grid"><div class="card"><strong>0 → 30/30</strong><span>synthetic unique entries</span></div><div class="card"><strong>0 → 1</strong><span>explicit participant receipt</span></div><div class="card"><strong>0</strong><span>automatic seals</span></div><div class="card"><strong>0 / 0</strong><span>token / secret surfaces</span></div><div class="card"><strong>{median:.4f}s</strong><span>median seal transaction</span></div><div class="card"><strong class="danger">{audit['real_component_rows_available']}/{audit['real_component_rows_required']}</strong><span>real component rows</span></div></section><section class="boundary"><h2>證據邊界</h2><p>這頁證明：一個已授權participant capability可以在token-free browser看見30/30與draft hash，明確確認，並留下intent → exact M57.4 seal → receipt；incomplete/stale/nonidentical狀態拒絕。它不證明參與者是誰、標註正確、Equation V1、LLM優勢或M58。現在real participants仍0，formal M57仍0。</p></section></main></body></html>'''


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
    actions.add_argument("--write-rehearsal", action="store_true")
    actions.add_argument("--write-live-audit", action="store_true")
    actions.add_argument("--measure-cost", action="store_true")
    actions.add_argument("--dashboard", type=int, metavar="PORT")
    actions.add_argument("--launch", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    actions.add_argument("--serve-completable", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    args = parser.parse_args()
    if args.write_rehearsal:
        value = build_engineering_rehearsal()
        runtime_m57.atomic_write_json(RESULT_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.write_live_audit:
        value = build_live_audit()
        runtime_m57.atomic_write_json(LIVE_AUDIT_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.measure_cost:
        value = measure_fixture_cost()
        runtime_m57.atomic_write_json(COST_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.dashboard is not None:
        serve_dashboard(args.dashboard)
    else:
        run_id, role_slot, envelope_path, port_text = args.launch or args.serve_completable
        if not re.fullmatch(r"\d{1,5}", port_text) or not (0 <= int(port_text) <= 65535):
            parser.error("PORT must be between 0 and 65535")
        if args.launch:
            launch_completion_runtime(run_id, role_slot, envelope_path, int(port_text))
        else:
            serve_completable_collection(run_id, role_slot, envelope_path, int(port_text))


if __name__ == "__main__":
    main()
