#!/usr/bin/env python3
"""M57.4 role-separated, pre-outcome component-evidence collection.

The module records source views and append-only revisions in three private role
ledgers.  Only after both coder ledgers are sealed can the adjudicator work.
The final export is the exact frozen M57.2 evidence manifest; raw ledgers stay
private and no outcome or model endpoint is used here.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
from pathlib import Path
import re
import secrets
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
import urllib.parse

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_2_component_prediction_capsule as component_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_4_component_evidence_collection_v1.json"
RESULT_PATH = ROOT / "analysis/m57_4_component_evidence_collection_rehearsal_2026-09-04.json"

MODE_FILENAME = "m57_4_component_evidence_collection_mode.json"
EXPORT_COMMITMENT_FILENAME = "m57_4_component_evidence_export_commitment.json"
PRIVATE_DIRNAME = "m57_4_private_component_evidence"
ROLE_SLOTS = ("coder_a", "coder_b", "adjudicator")
CODER_SLOTS = ("coder_a", "coder_b")
REAL_KIND = "real_independent_human_collection"
SYNTHETIC_KIND = "synthetic_engineering_rehearsal"
M57_ENGINEERING_KIND = "author_constructed_engineering_only"
PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")

MODE_SCHEMA = "uruha_m57_4_component_evidence_collection_mode_v1"
LEDGER_SCHEMA = "uruha_m57_4_private_component_evidence_ledger_v1"
VIEW_SCHEMA = "uruha_m57_4_component_source_view_receipt_v1"
REVISION_SCHEMA = "uruha_m57_4_component_evidence_revision_v1"
SEAL_SCHEMA = "uruha_m57_4_component_evidence_ledger_seal_v1"
EXPORT_SCHEMA = "uruha_m57_4_component_evidence_export_commitment_v1"
REHEARSAL_SCHEMA = "uruha_m57_4_component_evidence_collection_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_4_component_evidence_collection_live_audit_v1"


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


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "participants", "collection_order", "quarantine", "evidence_boundary",
        "public_functions", "formal_boundary", "claim_boundary",
    }
    if set(contract) != expected:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_4_component_evidence_collection_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_before_any_real_component_source_view":
        errors.append("contract.status")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    participants = contract.get("participants") or {}
    if participants.get("role_slots") != list(ROLE_SLOTS):
        errors.append("participants.roles")
    for name in (
        "distinct_pseudonyms_required",
        "consenting_human_self_attestation_required_for_real_collection",
        "not_model_or_synthetic_self_attestation_required_for_real_collection",
        "different_person_self_attestation_required_for_real_collection",
        "adjudicator_also_builds_observable_state_proxy",
    ):
        if participants.get(name) is not True:
            errors.append(f"participants.{name}")
    if participants.get("pseudonym_is_cryptographic_identity_proof") is not False:
        errors.append("participants.identity_claim")
    quarantine = contract.get("quarantine") or {}
    for name in (
        "separate_private_role_ledgers", "source_view_receipt_required_before_entry",
        "server_generated_utc_timestamps_required", "all_revisions_preserved",
    ):
        if quarantine.get(name) is not True:
            errors.append(f"quarantine.{name}")
    for name in (
        "coder_cross_ledger_surface_before_seal", "adjudicator_access_before_both_coder_seals",
        "sealed_ledger_mutation_allowed", "raw_ledgers_exported_publicly",
        "same_user_filesystem_isolation_is_adversarial_security",
    ):
        if quarantine.get(name) is not False:
            errors.append(f"quarantine.{name}")
    boundary = contract.get("evidence_boundary") or {}
    expected_counts = {
        "sample_count": 30, "coder_entry_count": 60, "adjudicator_entry_count": 30,
        "perception_contribution_count": 60, "retrieval_contribution_count": 60,
        "state_proxy_contribution_count": 30, "adjudication_count": 60,
        "target_outcome_access_count": 0, "model_call_count": 0,
    }
    for name, expected_value in expected_counts.items():
        if boundary.get(name) != expected_value:
            errors.append(f"evidence_boundary.{name}")
    for name in (
        "post_cutoff_history_allowed", "private_mental_truth_allowed",
        "production_memory_write", "external_deployment",
    ):
        if boundary.get(name) is not False:
            errors.append(f"evidence_boundary.{name}")
    functions = {
        "initialize_component_evidence_collection": initialize_component_evidence_collection,
        "record_component_source_view": record_component_source_view,
        "save_component_evidence_entry": save_component_evidence_entry,
        "seal_component_evidence_ledger": seal_component_evidence_ledger,
        "export_component_evidence_manifest": export_component_evidence_manifest,
    }
    frozen_signatures = contract.get("public_functions") or {}
    if set(frozen_signatures) != set(functions):
        errors.append("public_functions.names")
    for name, function in functions.items():
        if list(inspect.signature(function).parameters) != frozen_signatures.get(name):
            errors.append(f"public_functions.{name}")
    formal = contract.get("formal_boundary") or {}
    for name in (
        "synthetic_rehearsal_may_export_formal_manifest",
        "self_attestation_alone_proves_three_distinct_humans",
        "m57_2_prediction_execution_automatic", "m58_authorized",
    ):
        if formal.get(name) is not False:
            errors.append(f"formal_boundary.{name}")
    for name in (
        "synthetic_rehearsal_may_export_engineering_manifest",
        "formal_manifest_requires_real_mode_and_complete_valid_ledgers",
        "external_operator_identity_audit_still_required",
    ):
        if formal.get(name) is not True:
            errors.append(f"formal_boundary.{name}")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = component_m57._paths(run_id)
    private = paths["generation"].parent / PRIVATE_DIRNAME
    return {
        **paths,
        "m57_4_private": private,
        "m57_4_mode": paths["commitments"] / MODE_FILENAME,
        "m57_4_export": paths["commitments"] / EXPORT_COMMITMENT_FILENAME,
        **{f"ledger_{role}": private / f"{role}_ledger.json" for role in ROLE_SLOTS},
        **{f"seal_{role}": paths["commitments"] / f"m57_4_{role}_ledger_seal.json" for role in ROLE_SLOTS},
    }


def _context(run_id: str) -> dict[str, Any]:
    return component_m57._load_preoutcome_context(run_id)


def _no_outcome(paths: dict[str, Path], action: str) -> None:
    present = commitment_m57._present_outcome_state(paths)
    if present:
        raise PermissionError(f"M57.4 {action} denied after outcome state: " + ", ".join(present))


def _validate_roster(roster: Any, *, synthetic: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(roster, dict) or set(roster) != set(ROLE_SLOTS):
        return ["roster.roles"]
    pseudonyms = []
    fields = {
        "pseudonym", "consenting_human_attested", "not_model_or_synthetic_attested",
        "different_person_from_other_slots_attested",
    }
    for role in ROLE_SLOTS:
        row = roster.get(role)
        if not isinstance(row, dict) or set(row) != fields:
            errors.append(f"roster.{role}.fields")
            continue
        pseudonym = row.get("pseudonym")
        if not isinstance(pseudonym, str) or not PSEUDONYM_RE.fullmatch(pseudonym):
            errors.append(f"roster.{role}.pseudonym")
        else:
            pseudonyms.append(pseudonym)
        attestations = (
            row.get("consenting_human_attested"),
            row.get("not_model_or_synthetic_attested"),
            row.get("different_person_from_other_slots_attested"),
        )
        expected = False if synthetic else True
        if any(value is not expected for value in attestations):
            errors.append(f"roster.{role}.attestations")
    if len(pseudonyms) != 3 or len(set(pseudonyms)) != 3:
        errors.append("roster.distinct_pseudonyms")
    return errors


def _mode_hashless(value: dict[str, Any]) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != "mode_hash"}


def _validate_mode(mode: dict[str, Any], run_id: str, context: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "contract_hash", "data_kind",
        "dataset_hash", "prediction_packet_hash", "m57_1_mode_commitment_hash",
        "sample_count", "participants", "created_at_utc", "target_outcome_access_count",
        "model_call_count", "formal_manifest_possible", "mode_hash",
    }
    errors: list[str] = []
    if not isinstance(mode, dict) or set(mode) != fields:
        return ["mode.fields"]
    if mode.get("mode_hash") != digest(_mode_hashless(mode)):
        errors.append("mode.hash")
    if mode.get("schema") != MODE_SCHEMA or mode.get("version") != "1.0.0":
        errors.append("mode.schema")
    if mode.get("status") != "role_roster_and_preoutcome_source_contract_full_sync_committed":
        errors.append("mode.status")
    if mode.get("run_id") != run_id or mode.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("mode.binding")
    expected = {
        "dataset_hash": context["mode"]["dataset_hash"],
        "prediction_packet_hash": context["mode"]["prediction_packet_hash"],
        "m57_1_mode_commitment_hash": context["mode"]["mode_commitment_hash"],
        "sample_count": 30,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
    }
    for name, value in expected.items():
        if mode.get(name) != value:
            errors.append(f"mode.{name}")
    kind = mode.get("data_kind")
    if kind not in {REAL_KIND, SYNTHETIC_KIND}:
        errors.append("mode.data_kind")
    if mode.get("formal_manifest_possible") is not (kind == REAL_KIND):
        errors.append("mode.formal")
    participants = mode.get("participants")
    if not isinstance(participants, dict) or set(participants) != set(ROLE_SLOTS):
        errors.append("mode.participants")
    else:
        roster = {}
        for role in ROLE_SLOTS:
            row = participants.get(role) or {}
            expected_fields = {
                "pseudonym", "consenting_human_attested", "not_model_or_synthetic_attested",
                "different_person_from_other_slots_attested", "session_token_sha256",
            }
            if set(row) != expected_fields or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("session_token_sha256", ""))):
                errors.append(f"mode.participants.{role}")
                continue
            roster[role] = {key: row[key] for key in expected_fields if key != "session_token_sha256"}
        if len(roster) == 3:
            errors.extend(_validate_roster(roster, synthetic=(kind == SYNTHETIC_KIND)))
    if not _valid_timestamp(mode.get("created_at_utc")):
        errors.append("mode.timestamp")
    return errors


def _initialize(run_id: str, participant_roster: dict[str, Any], *, synthetic: bool) -> dict[str, Any]:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.4 contract invalid: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    roster_errors = _validate_roster(participant_roster, synthetic=synthetic)
    if roster_errors:
        raise ValueError("invalid M57.4 participant roster: " + "; ".join(roster_errors))
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = _context(run_id)
        paths = _paths(run_id)
        _no_outcome(paths, "initialization")
        if paths["evidence"].exists() or paths["m57_4_mode"].exists():
            raise FileExistsError("M57.4 collection or M57.2 evidence already exists")
        tokens = {role: secrets.token_urlsafe(32) for role in ROLE_SLOTS}
        participants = {}
        for role in ROLE_SLOTS:
            participants[role] = {
                **deepcopy(participant_roster[role]),
                "session_token_sha256": sha256(tokens[role].encode("utf-8")).hexdigest(),
            }
        mode = {
            "schema": MODE_SCHEMA,
            "version": "1.0.0",
            "status": "role_roster_and_preoutcome_source_contract_full_sync_committed",
            "run_id": run_id,
            "contract_hash": contract["contract_hash"],
            "data_kind": SYNTHETIC_KIND if synthetic else REAL_KIND,
            "dataset_hash": context["mode"]["dataset_hash"],
            "prediction_packet_hash": context["mode"]["prediction_packet_hash"],
            "m57_1_mode_commitment_hash": context["mode"]["mode_commitment_hash"],
            "sample_count": 30,
            "participants": participants,
            "created_at_utc": _utc_now(),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "formal_manifest_possible": not synthetic,
        }
        mode["mode_hash"] = digest(mode)
        if _validate_mode(mode, run_id, context):
            raise AssertionError("constructed M57.4 mode is invalid")
        durable_m56._durable_atomic_write_json(paths["m57_4_mode"], mode, exclusive=True)
        for role in ROLE_SLOTS:
            ledger = {
                "schema": LEDGER_SCHEMA,
                "version": "1.0.0",
                "status": "open_private_role_ledger",
                "run_id": run_id,
                "mode_hash": mode["mode_hash"],
                "data_kind": mode["data_kind"],
                "role_slot": role,
                "participant_pseudonym": participants[role]["pseudonym"],
                "created_at_utc": mode["created_at_utc"],
                "sealed_at_utc": None,
                "source_views": {},
                "entries": {},
                "revision_count": 0,
                "target_outcome_access_count": 0,
                "model_call_count": 0,
            }
            ledger["ledger_hash"] = digest(ledger)
            durable_m56._durable_atomic_write_json(paths[f"ledger_{role}"], ledger, exclusive=True)
    return {
        "status": "m57_4_collection_initialized",
        "run_id": run_id,
        "data_kind": mode["data_kind"],
        "role_session_tokens": tokens,
        "session_tokens_persisted_in_artifacts": False,
        "sample_count": 30,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_manifest_created": False,
        "m58_authorized": False,
    }


def initialize_component_evidence_collection(run_id: str, participant_roster: dict[str, Any]) -> dict[str, Any]:
    """Initialize a real-human collection; tokens are returned once and stored only as hashes."""
    return _initialize(run_id, participant_roster, synthetic=False)


def _load_mode(run_id: str, context: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    if not paths["m57_4_mode"].exists():
        raise FileNotFoundError("M57.4 collection mode is absent")
    mode = load_json(paths["m57_4_mode"])
    errors = _validate_mode(mode, run_id, context)
    if errors:
        raise ValueError("invalid M57.4 mode: " + "; ".join(errors))
    return mode


def _authorize(mode: dict[str, Any], role_slot: str, session_token: str) -> None:
    if role_slot not in ROLE_SLOTS:
        raise ValueError("unknown M57.4 role slot")
    expected = mode["participants"][role_slot]["session_token_sha256"]
    actual = sha256(str(session_token).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(expected, actual):
        raise PermissionError("invalid M57.4 role session token")


def _task_map(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return component_m57._ours_task_map(context["rows"])


def _sample_order(context: dict[str, Any]) -> list[str]:
    return component_m57._sample_order(context["rows"])


def _source(context: dict[str, Any], sample_id: str) -> tuple[dict[str, Any], str]:
    task = _task_map(context).get(sample_id)
    if task is None:
        raise ValueError("sample is not in the frozen M57.4 packet")
    return deepcopy(task["view"]["source_information"]), task["view"]["source_information_hash"]


def _ledger_hashless(value: dict[str, Any]) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != "ledger_hash"}


def _final_revision(ledger: dict[str, Any], sample_id: str) -> dict[str, Any]:
    row = (ledger.get("entries") or {}).get(sample_id) or {}
    revisions = row.get("revisions") or []
    if not revisions:
        raise ValueError(f"no M57.4 final revision for {sample_id}")
    return revisions[-1]


def _load_sealed_coders(
    run_id: str, mode: dict[str, Any], context: dict[str, Any], paths: dict[str, Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    ledgers: dict[str, dict[str, Any]] = {}
    seals: dict[str, dict[str, Any]] = {}
    for role in CODER_SLOTS:
        ledger = load_json(paths[f"ledger_{role}"])
        ledger_errors = _validate_ledger(ledger, mode, context, require_complete=True)
        if ledger_errors or ledger.get("status") != "sealed_private_role_ledger":
            raise PermissionError(f"M57.4 {role} ledger is not valid and sealed: " + "; ".join(ledger_errors))
        if not paths[f"seal_{role}"].exists():
            raise PermissionError(f"M57.4 {role} seal is absent")
        seal = load_json(paths[f"seal_{role}"])
        seal_errors = _validate_seal(seal, ledger, mode)
        if seal_errors:
            raise ValueError(f"invalid M57.4 {role} seal: " + "; ".join(seal_errors))
        ledgers[role] = ledger
        seals[role] = seal
    return ledgers, seals


def _validate_view(value: Any, sample_id: str, source_hash: str) -> list[str]:
    fields = {"schema", "sample_id", "source_information_hash", "first_viewed_at_utc", "view_hash"}
    if not isinstance(value, dict) or set(value) != fields:
        return ["view.fields"]
    errors: list[str] = []
    if value.get("schema") != VIEW_SCHEMA or value.get("sample_id") != sample_id:
        errors.append("view.identity")
    if value.get("source_information_hash") != source_hash:
        errors.append("view.source")
    if not _valid_timestamp(value.get("first_viewed_at_utc")):
        errors.append("view.timestamp")
    if value.get("view_hash") != digest({key: child for key, child in value.items() if key != "view_hash"}):
        errors.append("view.hash")
    return errors


def _validate_revision(
    revision: Any, *, role: str, sample_id: str, source: dict[str, Any], source_hash: str,
    view: dict[str, Any], coder_ledgers: dict[str, dict[str, Any]] | None = None,
    coder_seals: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    common = {
        "schema", "revision_number", "sample_id", "source_information_hash", "source_view_hash",
        "saved_at_utc", "payload", "target_outcome_access_count", "model_call_count", "revision_hash",
    }
    fields = common | ({"coder_seal_hashes", "computed_disagreement"} if role == "adjudicator" else set())
    if not isinstance(revision, dict) or set(revision) != fields:
        return ["revision.fields"]
    errors: list[str] = []
    if revision.get("schema") != REVISION_SCHEMA or revision.get("sample_id") != sample_id:
        errors.append("revision.identity")
    if revision.get("source_information_hash") != source_hash or revision.get("source_view_hash") != view.get("view_hash"):
        errors.append("revision.source")
    if not _valid_timestamp(revision.get("saved_at_utc")) or str(revision.get("saved_at_utc")) < str(view.get("first_viewed_at_utc")):
        errors.append("revision.timestamp")
    if revision.get("target_outcome_access_count") != 0 or revision.get("model_call_count") != 0:
        errors.append("revision.forbidden_access")
    if revision.get("revision_hash") != digest({key: child for key, child in revision.items() if key != "revision_hash"}):
        errors.append("revision.hash")
    payload = revision.get("payload")
    if not isinstance(payload, dict):
        return errors + ["revision.payload"]
    forbidden = component_m57._find_keys(payload)
    errors.extend(f"revision.forbidden:{name}" for name in forbidden)
    if role in CODER_SLOTS:
        if set(payload) != {"perception", "retrieval"}:
            errors.append("revision.coder.fields")
        else:
            errors.extend(component_m57._validate_resolved_payload("perception", payload["perception"], source, "revision.perception"))
            errors.extend(component_m57._validate_resolved_payload("retrieval", payload["retrieval"], source, "revision.retrieval"))
    else:
        expected_payload = {
            "resolved_perception", "perception_resolution_basis", "resolved_retrieval",
            "retrieval_resolution_basis", "observable_state_proxy",
        }
        if set(payload) != expected_payload:
            errors.append("revision.adjudicator.fields")
        else:
            errors.extend(component_m57._validate_resolved_payload("perception", payload["resolved_perception"], source, "revision.resolved_perception"))
            errors.extend(component_m57._validate_resolved_payload("retrieval", payload["resolved_retrieval"], source, "revision.resolved_retrieval"))
            errors.extend(component_m57._validate_resolved_payload("state", payload["observable_state_proxy"], source, "revision.state"))
            for name in ("perception_resolution_basis", "retrieval_resolution_basis"):
                if not isinstance(payload.get(name), str) or not payload[name].strip():
                    errors.append(f"revision.{name}")
        if coder_ledgers is None or coder_seals is None:
            errors.append("revision.coder_context")
        else:
            finals = {slot: _final_revision(coder_ledgers[slot], sample_id)["payload"] for slot in CODER_SLOTS}
            expected_disagreement = {
                "perception": finals["coder_a"]["perception"] != finals["coder_b"]["perception"],
                "retrieval": finals["coder_a"]["retrieval"] != finals["coder_b"]["retrieval"],
            }
            expected_seals = {slot: coder_seals[slot]["seal_hash"] for slot in CODER_SLOTS}
            if revision.get("computed_disagreement") != expected_disagreement:
                errors.append("revision.disagreement")
            if revision.get("coder_seal_hashes") != expected_seals:
                errors.append("revision.coder_seals")
    return errors


def _validate_ledger(
    ledger: dict[str, Any], mode: dict[str, Any], context: dict[str, Any], *, require_complete: bool,
    coder_ledgers: dict[str, dict[str, Any]] | None = None,
    coder_seals: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "data_kind", "role_slot",
        "participant_pseudonym", "created_at_utc", "sealed_at_utc", "source_views", "entries",
        "revision_count", "target_outcome_access_count", "model_call_count", "ledger_hash",
    }
    if not isinstance(ledger, dict) or set(ledger) != fields:
        return ["ledger.fields"]
    errors: list[str] = []
    role = ledger.get("role_slot")
    if ledger.get("schema") != LEDGER_SCHEMA or ledger.get("version") != "1.0.0":
        errors.append("ledger.schema")
    if role not in ROLE_SLOTS:
        return errors + ["ledger.role"]
    if ledger.get("run_id") != mode["run_id"] or ledger.get("mode_hash") != mode["mode_hash"]:
        errors.append("ledger.binding")
    if ledger.get("data_kind") != mode["data_kind"] or ledger.get("participant_pseudonym") != mode["participants"][role]["pseudonym"]:
        errors.append("ledger.participant")
    if ledger.get("status") not in {"open_private_role_ledger", "sealed_private_role_ledger"}:
        errors.append("ledger.status")
    if not _valid_timestamp(ledger.get("created_at_utc")):
        errors.append("ledger.created_at")
    if ledger.get("status") == "sealed_private_role_ledger":
        if not _valid_timestamp(ledger.get("sealed_at_utc")):
            errors.append("ledger.sealed_at")
    elif ledger.get("sealed_at_utc") is not None:
        errors.append("ledger.open_sealed_at")
    if ledger.get("target_outcome_access_count") != 0 or ledger.get("model_call_count") != 0:
        errors.append("ledger.forbidden_access")
    if ledger.get("ledger_hash") != digest(_ledger_hashless(ledger)):
        errors.append("ledger.hash")
    order = _sample_order(context)
    allowed = set(order)
    views = ledger.get("source_views")
    entries = ledger.get("entries")
    if not isinstance(views, dict) or set(views) - allowed:
        errors.append("ledger.views")
        views = {}
    if not isinstance(entries, dict) or set(entries) - allowed:
        errors.append("ledger.entries")
        entries = {}
    counted = 0
    for sample_id, view in views.items():
        source, source_hash = _source(context, sample_id)
        errors.extend(f"{sample_id}:{name}" for name in _validate_view(view, sample_id, source_hash))
    for sample_id, row in entries.items():
        if not isinstance(row, dict) or set(row) != {"sample_id", "revisions"} or row.get("sample_id") != sample_id:
            errors.append(f"{sample_id}:entry.fields")
            continue
        revisions = row.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            errors.append(f"{sample_id}:entry.revisions")
            continue
        if sample_id not in views:
            errors.append(f"{sample_id}:entry.no_view")
            continue
        source, source_hash = _source(context, sample_id)
        for index, revision in enumerate(revisions, 1):
            counted += 1
            if revision.get("revision_number") != index:
                errors.append(f"{sample_id}:revision.order")
            errors.extend(
                f"{sample_id}:r{index}:{name}"
                for name in _validate_revision(
                    revision, role=role, sample_id=sample_id, source=source,
                    source_hash=source_hash, view=views[sample_id],
                    coder_ledgers=coder_ledgers, coder_seals=coder_seals,
                )
            )
    if ledger.get("revision_count") != counted:
        errors.append("ledger.revision_count")
    if require_complete:
        if set(views) != allowed or set(entries) != allowed:
            errors.append("ledger.incomplete")
        if [sample for sample in order if sample in entries] != order:
            errors.append("ledger.order")
    return errors


def _validate_seal(seal: dict[str, Any], ledger: dict[str, Any], mode: dict[str, Any]) -> list[str]:
    fields = {
        "schema", "version", "status", "run_id", "mode_hash", "role_slot",
        "participant_pseudonym", "ledger_hash", "entry_count", "source_view_count",
        "revision_count", "sealed_at_utc", "target_outcome_access_count", "model_call_count", "seal_hash",
    }
    if not isinstance(seal, dict) or set(seal) != fields:
        return ["seal.fields"]
    errors: list[str] = []
    expected = {
        "schema": SEAL_SCHEMA, "version": "1.0.0", "status": "complete_private_role_ledger_sha256_sealed",
        "run_id": mode["run_id"], "mode_hash": mode["mode_hash"], "role_slot": ledger["role_slot"],
        "participant_pseudonym": ledger["participant_pseudonym"], "ledger_hash": ledger["ledger_hash"],
        "entry_count": 30, "source_view_count": 30, "revision_count": ledger["revision_count"],
        "sealed_at_utc": ledger["sealed_at_utc"], "target_outcome_access_count": 0, "model_call_count": 0,
    }
    for name, value in expected.items():
        if seal.get(name) != value:
            errors.append(f"seal.{name}")
    if seal.get("seal_hash") != digest({key: child for key, child in seal.items() if key != "seal_hash"}):
        errors.append("seal.hash")
    return errors


def _load_role_ledger(
    role: str, mode: dict[str, Any], context: dict[str, Any], paths: dict[str, Path],
    *, require_complete: bool = False, coder_ledgers: dict[str, dict[str, Any]] | None = None,
    coder_seals: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ledger = load_json(paths[f"ledger_{role}"])
    errors = _validate_ledger(
        ledger, mode, context, require_complete=require_complete,
        coder_ledgers=coder_ledgers, coder_seals=coder_seals,
    )
    if errors:
        raise ValueError(f"invalid M57.4 {role} ledger: " + "; ".join(errors))
    return ledger


def _adjudication_context(
    sample_id: str, coder_ledgers: dict[str, dict[str, Any]], coder_seals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    finals = {role: deepcopy(_final_revision(coder_ledgers[role], sample_id)) for role in CODER_SLOTS}
    return {
        "coder_contributions": {role: row["payload"] for role, row in finals.items()},
        "coder_revision_hashes": {role: row["revision_hash"] for role, row in finals.items()},
        "coder_seal_hashes": {role: coder_seals[role]["seal_hash"] for role in CODER_SLOTS},
        "computed_disagreement": {
            "perception": finals["coder_a"]["payload"]["perception"] != finals["coder_b"]["payload"]["perception"],
            "retrieval": finals["coder_a"]["payload"]["retrieval"] != finals["coder_b"]["payload"]["retrieval"],
        },
    }


def record_component_source_view(run_id: str, role_slot: str, session_token: str, sample_id: str) -> dict[str, Any]:
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = _context(run_id)
        paths = _paths(run_id)
        _no_outcome(paths, "source view")
        mode = _load_mode(run_id, context, paths)
        _authorize(mode, role_slot, session_token)
        source, source_hash = _source(context, sample_id)
        coder_ledgers = coder_seals = None
        adjudication = None
        if role_slot == "adjudicator":
            coder_ledgers, coder_seals = _load_sealed_coders(run_id, mode, context, paths)
            adjudication = _adjudication_context(sample_id, coder_ledgers, coder_seals)
        ledger = _load_role_ledger(
            role_slot, mode, context, paths,
            coder_ledgers=coder_ledgers, coder_seals=coder_seals,
        )
        if ledger["status"] != "open_private_role_ledger":
            raise PermissionError("sealed M57.4 ledger cannot record a source view")
        if sample_id not in ledger["source_views"]:
            receipt = {
                "schema": VIEW_SCHEMA,
                "sample_id": sample_id,
                "source_information_hash": source_hash,
                "first_viewed_at_utc": _utc_now(),
            }
            receipt["view_hash"] = digest(receipt)
            ledger["source_views"][sample_id] = receipt
            ledger["ledger_hash"] = digest(_ledger_hashless(ledger))
            durable_m56._durable_atomic_write_json(paths[f"ledger_{role_slot}"], ledger)
        return {
            "status": "m57_4_source_view_recorded",
            "role_slot": role_slot,
            "sample_id": sample_id,
            "source_information": source,
            "source_information_hash": source_hash,
            "source_view_receipt": deepcopy(ledger["source_views"][sample_id]),
            "other_coder_ledger_visible": False if role_slot in CODER_SLOTS else True,
            "adjudication_context": adjudication,
            "target_outcome_visible": False,
        }


def save_component_evidence_entry(
    run_id: str, role_slot: str, session_token: str, sample_id: str, entry_payload: dict[str, Any],
) -> dict[str, Any]:
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = _context(run_id)
        paths = _paths(run_id)
        _no_outcome(paths, "entry save")
        mode = _load_mode(run_id, context, paths)
        _authorize(mode, role_slot, session_token)
        source, source_hash = _source(context, sample_id)
        coder_ledgers = coder_seals = None
        if role_slot == "adjudicator":
            coder_ledgers, coder_seals = _load_sealed_coders(run_id, mode, context, paths)
        ledger = _load_role_ledger(
            role_slot, mode, context, paths,
            coder_ledgers=coder_ledgers, coder_seals=coder_seals,
        )
        if ledger["status"] != "open_private_role_ledger":
            raise PermissionError("sealed M57.4 ledger cannot be changed")
        if sample_id not in ledger["source_views"]:
            raise PermissionError("M57.4 entry requires a server-recorded source view")
        revisions = (ledger["entries"].get(sample_id) or {"sample_id": sample_id, "revisions": []})["revisions"]
        revision = {
            "schema": REVISION_SCHEMA,
            "revision_number": len(revisions) + 1,
            "sample_id": sample_id,
            "source_information_hash": source_hash,
            "source_view_hash": ledger["source_views"][sample_id]["view_hash"],
            "saved_at_utc": _utc_now(),
            "payload": deepcopy(entry_payload),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
        }
        if role_slot == "adjudicator":
            context_for_adj = _adjudication_context(sample_id, coder_ledgers or {}, coder_seals or {})
            revision["coder_seal_hashes"] = context_for_adj["coder_seal_hashes"]
            revision["computed_disagreement"] = context_for_adj["computed_disagreement"]
        revision["revision_hash"] = digest(revision)
        errors = _validate_revision(
            revision, role=role_slot, sample_id=sample_id, source=source,
            source_hash=source_hash, view=ledger["source_views"][sample_id],
            coder_ledgers=coder_ledgers, coder_seals=coder_seals,
        )
        if errors:
            raise ValueError("invalid M57.4 entry: " + "; ".join(errors))
        revisions.append(revision)
        ledger["entries"][sample_id] = {"sample_id": sample_id, "revisions": revisions}
        ledger["revision_count"] += 1
        ledger["ledger_hash"] = digest(_ledger_hashless(ledger))
        durable_m56._durable_atomic_write_json(paths[f"ledger_{role_slot}"], ledger)
        return {
            "status": "m57_4_private_entry_full_sync_saved",
            "role_slot": role_slot,
            "sample_id": sample_id,
            "revision_number": revision["revision_number"],
            "revision_hash": revision["revision_hash"],
            "completed_sample_count": len(ledger["entries"]),
            "target_outcome_access_count": 0,
            "model_call_count": 0,
        }


def seal_component_evidence_ledger(run_id: str, role_slot: str, session_token: str) -> dict[str, Any]:
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = _context(run_id)
        paths = _paths(run_id)
        _no_outcome(paths, "ledger seal")
        mode = _load_mode(run_id, context, paths)
        _authorize(mode, role_slot, session_token)
        coder_ledgers = coder_seals = None
        if role_slot == "adjudicator":
            coder_ledgers, coder_seals = _load_sealed_coders(run_id, mode, context, paths)
        ledger = _load_role_ledger(
            role_slot, mode, context, paths, require_complete=True,
            coder_ledgers=coder_ledgers, coder_seals=coder_seals,
        )
        seal_path = paths[f"seal_{role_slot}"]
        if ledger["status"] == "open_private_role_ledger":
            ledger["status"] = "sealed_private_role_ledger"
            ledger["sealed_at_utc"] = _utc_now()
            ledger["ledger_hash"] = digest(_ledger_hashless(ledger))
            durable_m56._durable_atomic_write_json(paths[f"ledger_{role_slot}"], ledger)
        if seal_path.exists():
            seal = load_json(seal_path)
            errors = _validate_seal(seal, ledger, mode)
            if errors:
                raise ValueError("existing M57.4 seal differs: " + "; ".join(errors))
            write_status = "validated_existing_identical"
        else:
            seal = {
                "schema": SEAL_SCHEMA,
                "version": "1.0.0",
                "status": "complete_private_role_ledger_sha256_sealed",
                "run_id": run_id,
                "mode_hash": mode["mode_hash"],
                "role_slot": role_slot,
                "participant_pseudonym": ledger["participant_pseudonym"],
                "ledger_hash": ledger["ledger_hash"],
                "entry_count": 30,
                "source_view_count": 30,
                "revision_count": ledger["revision_count"],
                "sealed_at_utc": ledger["sealed_at_utc"],
                "target_outcome_access_count": 0,
                "model_call_count": 0,
            }
            seal["seal_hash"] = digest(seal)
            durable_m56._durable_atomic_write_json(seal_path, seal, exclusive=True)
            write_status = "created_full_sync"
        return {
            "status": "m57_4_private_role_ledger_sealed",
            "role_slot": role_slot,
            "ledger_hash": ledger["ledger_hash"],
            "seal_hash": seal["seal_hash"],
            "entry_count": 30,
            "revision_count": ledger["revision_count"],
            "seal_write": write_status,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
        }


def _build_manifest(
    run_id: str, mode: dict[str, Any], context: dict[str, Any],
    ledgers: dict[str, dict[str, Any]], seals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = []
    for index, sample_id in enumerate(_sample_order(context)):
        source, source_hash = _source(context, sample_id)
        coder_final = {role: _final_revision(ledgers[role], sample_id) for role in CODER_SLOTS}
        adj_final = _final_revision(ledgers["adjudicator"], sample_id)
        adj_payload = adj_final["payload"]
        perception = [
            component_m57._contribution(
                mode["participants"][role]["pseudonym"], "independent_coder",
                f"m57-4-p-{index:02d}-{role}", source_hash,
                coder_final[role]["payload"]["perception"],
            ) for role in CODER_SLOTS
        ]
        retrieval = [
            component_m57._contribution(
                mode["participants"][role]["pseudonym"], "independent_coder",
                f"m57-4-r-{index:02d}-{role}", source_hash,
                coder_final[role]["payload"]["retrieval"],
            ) for role in CODER_SLOTS
        ]
        perception_adjudication = {
            "adjudicator_id": mode["participants"]["adjudicator"]["pseudonym"],
            "selected_contribution_ids": [row["contribution_id"] for row in perception],
            "replacement_payload": deepcopy(adj_payload["resolved_perception"]),
            "created_before_outcome": True,
        }
        perception_adjudication["adjudication_hash"] = digest(perception_adjudication)
        retrieval_adjudication = {
            "adjudicator_id": mode["participants"]["adjudicator"]["pseudonym"],
            "selected_contribution_ids": [row["contribution_id"] for row in retrieval],
            "replacement_payload": deepcopy(adj_payload["resolved_retrieval"]),
            "created_before_outcome": True,
        }
        retrieval_adjudication["adjudication_hash"] = digest(retrieval_adjudication)
        state = [component_m57._contribution(
            mode["participants"]["adjudicator"]["pseudonym"], "observable_proxy_builder",
            f"m57-4-s-{index:02d}-adjudicator", source_hash,
            adj_payload["observable_state_proxy"],
        )]
        stages = {
            "perception": component_m57._available_stage(
                "perception", source_hash, adj_payload["resolved_perception"], perception,
                perception_adjudication,
            ),
            "retrieval": component_m57._available_stage(
                "retrieval", source_hash, adj_payload["resolved_retrieval"], retrieval,
                retrieval_adjudication,
            ),
            "state": component_m57._available_stage(
                "state", source_hash, adj_payload["observable_state_proxy"], state, None,
            ),
            "decision": component_m57._unavailable_stage(
                "decision", source_hash, "withheld behavior is post-outcome only",
            ),
            "realization": component_m57._unavailable_stage(
                "realization", source_hash, "independent blind human surface ratings are absent",
            ),
        }
        row = {
            "sample_id": sample_id,
            "source_information_hash": source_hash,
            "stage_evidence": stages,
        }
        row["row_hash"] = digest(row)
        rows.append(row)
    real = mode["data_kind"] == REAL_KIND
    manifest = {
        "schema": component_m57.EVIDENCE_SCHEMA,
        "version": "1.0.0",
        "status": "all_component_evidence_resolved_or_unavailable_before_outcome",
        "data_kind": "real_independent_preoutcome_component_evidence" if real else M57_ENGINEERING_KIND,
        "run_id": run_id,
        "dataset_hash": mode["dataset_hash"],
        "prediction_packet_hash": mode["prediction_packet_hash"],
        "m57_1_mode_commitment_hash": mode["m57_1_mode_commitment_hash"],
        "sample_count": 30,
        "stage_order": list(component_m57.STAGE_IDS),
        "rows": rows,
        "evidence_created_before_outcome": True,
        "private_state_fact_created": False,
        "post_cutoff_evidence_used": False,
        "formal_authorization": real,
    }
    manifest["manifest_hash"] = digest(manifest)
    validation = component_m57.validate_evidence_manifest(
        manifest, run_id, context, allow_forged=not real,
    )
    if not validation["valid"]:
        raise ValueError("M57.4 export does not satisfy frozen M57.2: " + "; ".join(validation["errors"]))
    return manifest


def _build_export_commitment(
    run_id: str, mode: dict[str, Any], manifest: dict[str, Any],
    ledgers: dict[str, dict[str, Any]], seals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    disagreements = {"perception": 0, "retrieval": 0}
    for sample_id in ledgers["adjudicator"]["entries"]:
        flags = _final_revision(ledgers["adjudicator"], sample_id)["computed_disagreement"]
        for stage in disagreements:
            disagreements[stage] += int(flags[stage])
    value = {
        "schema": EXPORT_SCHEMA,
        "version": "1.0.0",
        "status": "complete_role_separated_manifest_exported_before_outcome",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_hash": mode["mode_hash"],
        "data_kind": mode["data_kind"],
        "participant_pseudonyms": {role: mode["participants"][role]["pseudonym"] for role in ROLE_SLOTS},
        "ledger_hashes": {role: ledgers[role]["ledger_hash"] for role in ROLE_SLOTS},
        "seal_hashes": {role: seals[role]["seal_hash"] for role in ROLE_SLOTS},
        "manifest_hash": manifest["manifest_hash"],
        "sample_count": 30,
        "coder_entry_count": 60,
        "adjudicator_entry_count": 30,
        "source_view_count": 90,
        "disagreement_counts": disagreements,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_manifest_exported": mode["data_kind"] == REAL_KIND,
        "external_identity_audit_completed": False,
        "m57_2_prediction_execution_started": False,
        "m58_authorized": False,
        "exported_at_utc": _utc_now(),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["export_commitment_hash"] = digest(value)
    return value


def _validate_export_commitment(
    value: dict[str, Any], run_id: str, mode: dict[str, Any], manifest: dict[str, Any],
    ledgers: dict[str, dict[str, Any]], seals: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "run_id", "contract_hash", "mode_hash", "data_kind",
        "participant_pseudonyms", "ledger_hashes", "seal_hashes", "manifest_hash", "sample_count",
        "coder_entry_count", "adjudicator_entry_count", "source_view_count", "disagreement_counts",
        "target_outcome_access_count", "model_call_count", "formal_manifest_exported",
        "external_identity_audit_completed", "m57_2_prediction_execution_started", "m58_authorized",
        "exported_at_utc", "claim_boundary", "export_commitment_hash",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        return ["export.fields"]
    if value.get("export_commitment_hash") != digest(
        {key: child for key, child in value.items() if key != "export_commitment_hash"}
    ):
        return ["export.hash"]
    static = _build_export_commitment(run_id, mode, manifest, ledgers, seals)
    for name in static:
        if name in {"exported_at_utc", "export_commitment_hash"}:
            continue
        if value.get(name) != static[name]:
            errors.append(f"export.{name}")
    if not _valid_timestamp(value.get("exported_at_utc")):
        errors.append("export.timestamp")
    return errors


def export_component_evidence_manifest(run_id: str, adjudicator_session_token: str) -> dict[str, Any]:
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        context = _context(run_id)
        paths = _paths(run_id)
        _no_outcome(paths, "manifest export")
        mode = _load_mode(run_id, context, paths)
        _authorize(mode, "adjudicator", adjudicator_session_token)
        coder_ledgers, coder_seals = _load_sealed_coders(run_id, mode, context, paths)
        adjudicator = _load_role_ledger(
            "adjudicator", mode, context, paths, require_complete=True,
            coder_ledgers=coder_ledgers, coder_seals=coder_seals,
        )
        if adjudicator["status"] != "sealed_private_role_ledger":
            raise PermissionError("M57.4 adjudicator ledger is not sealed")
        adj_seal = load_json(paths["seal_adjudicator"])
        adj_errors = _validate_seal(adj_seal, adjudicator, mode)
        if adj_errors:
            raise ValueError("invalid M57.4 adjudicator seal: " + "; ".join(adj_errors))
        ledgers = {**coder_ledgers, "adjudicator": adjudicator}
        seals = {**coder_seals, "adjudicator": adj_seal}
        manifest = _build_manifest(run_id, mode, context, ledgers, seals)
        if paths["evidence"].exists():
            if load_json(paths["evidence"]) != manifest:
                raise FileExistsError("existing M57.2 evidence manifest differs; overwrite forbidden")
            manifest_write = "validated_existing_identical"
        else:
            durable_m56._durable_atomic_write_json(paths["evidence"], manifest, exclusive=True)
            manifest_write = "created_full_sync"
        if paths["m57_4_export"].exists():
            export = load_json(paths["m57_4_export"])
            errors = _validate_export_commitment(export, run_id, mode, manifest, ledgers, seals)
            if errors:
                raise ValueError("existing M57.4 export commitment differs: " + "; ".join(errors))
            export_write = "validated_existing_identical"
        else:
            export = _build_export_commitment(run_id, mode, manifest, ledgers, seals)
            durable_m56._durable_atomic_write_json(paths["m57_4_export"], export, exclusive=True)
            export_write = "created_full_sync"
        return {
            "status": "m57_4_component_evidence_manifest_exported_before_outcome",
            "data_kind": manifest["data_kind"],
            "formal_manifest_exported": export["formal_manifest_exported"],
            "manifest_hash": manifest["manifest_hash"],
            "export_commitment_hash": export["export_commitment_hash"],
            "coder_entry_count": 60,
            "adjudicator_entry_count": 30,
            "source_view_count": 90,
            "disagreement_counts": export["disagreement_counts"],
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "m57_2_prediction_execution_started": False,
            "m58_authorized": False,
            "manifest_write": manifest_write,
            "export_write": export_write,
        }


def _synthetic_roster() -> dict[str, Any]:
    return {
        role: {
            "pseudonym": f"synthetic-{role.replace('_', '-')}",
            "consenting_human_attested": False,
            "not_model_or_synthetic_attested": False,
            "different_person_from_other_slots_attested": False,
        }
        for role in ROLE_SLOTS
    }


def _synthetic_coder_payload(source: dict[str, Any], *, variant: str, index: int) -> dict[str, Any]:
    features = [
        f"visible_character_count:{len(source['current_pre_cutoff_event'])}",
        "input_modality:text_paraphrase",
    ]
    if variant == "b" and index % 5 == 0:
        features.append("synthetic_visible_punctuation_reviewed:true")
    history = [row["history_id"] for row in source["all_pre_cutoff_history"]]
    take = 3 if variant == "a" or index % 4 else 2
    return {
        "perception": {
            "observable_features": features,
            "representation_note": "Synthetic observable-only mechanics entry.",
        },
        "retrieval": {
            "selected_history_ids": history[-take:],
            "selection_rule": f"Synthetic selected the last {take} permitted history rows.",
        },
    }


def _synthetic_state_payload(context: dict[str, Any], sample_id: str, source: dict[str, Any]) -> dict[str, Any]:
    artifacts = component_m57._artifact_map(context["rows"])
    variables = {
        row["id"]: deepcopy(row["value"])
        for row in artifacts[sample_id]["state_snapshot"]["variables"]
        if row["id"] in component_m57.OBSERVABLE_STATE_IDS
    }
    refs = ["source_information.current_pre_cutoff_event"]
    histories = source["all_pre_cutoff_history"]
    if histories:
        refs.append(f"history:{histories[-1]['history_id']}")
    return {"observable_proxy_variables": variables, "source_refs": refs}


def build_engineering_rehearsal() -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots
    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run

    with TemporaryDirectory(prefix="uruha-m57-4-collection-") as temp:
        root = Path(temp)
        run_id = "m57-4-synthetic-role-separated-rehearsal"
        start = perf_counter()
        with m5610_private_roots(root):
            materialize_scoring_run(root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            initialized = _initialize(run_id, _synthetic_roster(), synthetic=True)
            tokens = initialized["role_session_tokens"]
            context = _context(run_id)
            for index, sample_id in enumerate(_sample_order(context)):
                for role, variant in (("coder_a", "a"), ("coder_b", "b")):
                    view = record_component_source_view(run_id, role, tokens[role], sample_id)
                    payload = _synthetic_coder_payload(view["source_information"], variant=variant, index=index)
                    save_component_evidence_entry(run_id, role, tokens[role], sample_id, payload)
            coder_seals = {
                role: seal_component_evidence_ledger(run_id, role, tokens[role])
                for role in CODER_SLOTS
            }
            for sample_id in _sample_order(context):
                view = record_component_source_view(run_id, "adjudicator", tokens["adjudicator"], sample_id)
                contributions = view["adjudication_context"]["coder_contributions"]
                payload = {
                    "resolved_perception": deepcopy(contributions["coder_a"]["perception"]),
                    "perception_resolution_basis": "Synthetic mechanics: choose coder A while preserving disagreement.",
                    "resolved_retrieval": deepcopy(contributions["coder_a"]["retrieval"]),
                    "retrieval_resolution_basis": "Synthetic mechanics: choose coder A while preserving disagreement.",
                    "observable_state_proxy": _synthetic_state_payload(context, sample_id, view["source_information"]),
                }
                save_component_evidence_entry(run_id, "adjudicator", tokens["adjudicator"], sample_id, payload)
            adjudicator_seal = seal_component_evidence_ledger(
                run_id, "adjudicator", tokens["adjudicator"]
            )
            exported = export_component_evidence_manifest(run_id, tokens["adjudicator"])
            replay = export_component_evidence_manifest(run_id, tokens["adjudicator"])
            paths = _paths(run_id)
            manifest = load_json(paths["evidence"])
            internal = component_m57.validate_evidence_manifest(manifest, run_id, context, allow_forged=True)
            public = component_m57.validate_evidence_manifest(manifest, run_id, context, allow_forged=False)
            artifact_paths = [
                paths["m57_4_mode"], *(paths[f"ledger_{role}"] for role in ROLE_SLOTS),
                *(paths[f"seal_{role}"] for role in ROLE_SLOTS), paths["evidence"], paths["m57_4_export"],
            ]
            artifact_bytes = {path.name: path.stat().st_size for path in artifact_paths}
        value = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "synthetic_role_separated_collection_exported_without_formal_authority",
            "run_id": run_id,
            "contract_hash": validate_contract()["contract_hash"],
            "data_kind": SYNTHETIC_KIND,
            "participant_role_count": 3,
            "coder_entry_count": exported["coder_entry_count"],
            "adjudicator_entry_count": exported["adjudicator_entry_count"],
            "source_view_count": exported["source_view_count"],
            "perception_contribution_count": 60,
            "retrieval_contribution_count": 60,
            "state_proxy_contribution_count": 30,
            "adjudication_count": 60,
            "disagreement_counts": exported["disagreement_counts"],
            "coder_seal_count": len(coder_seals),
            "adjudicator_seal_count": int(bool(adjudicator_seal)),
            "internal_m57_2_manifest_valid": internal["valid"],
            "public_m57_2_formal_validator_accepts": public["valid"],
            "formal_manifest_exported": exported["formal_manifest_exported"],
            "export_replay_manifest_write": replay["manifest_write"],
            "export_replay_commitment_write": replay["export_write"],
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "m57_2_prediction_execution_started": False,
            "m58_authorized": False,
            "elapsed_seconds": perf_counter() - start,
            "artifact_utf8_bytes": artifact_bytes,
            "claim_boundary": load_contract()["claim_boundary"],
        }
        value["rehearsal_hash"] = digest(value)
        return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "synthetic_role_separated_collection_exported_without_formal_authority":
        errors.append("rehearsal.schema_or_status")
    if value.get("rehearsal_hash") != digest({key: child for key, child in value.items() if key != "rehearsal_hash"}):
        errors.append("rehearsal.hash")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    counts = {
        "participant_role_count": 3, "coder_entry_count": 60, "adjudicator_entry_count": 30,
        "source_view_count": 90, "perception_contribution_count": 60,
        "retrieval_contribution_count": 60, "state_proxy_contribution_count": 30,
        "adjudication_count": 60, "coder_seal_count": 2, "adjudicator_seal_count": 1,
        "target_outcome_access_count": 0, "model_call_count": 0,
    }
    for name, expected in counts.items():
        if value.get(name) != expected:
            errors.append(f"rehearsal.{name}")
    if value.get("internal_m57_2_manifest_valid") is not True:
        errors.append("rehearsal.internal_validation")
    for name in (
        "public_m57_2_formal_validator_accepts", "formal_manifest_exported",
        "m57_2_prediction_execution_started", "m58_authorized",
    ):
        if value.get(name) is not False:
            errors.append(f"rehearsal.{name}")
    if value.get("export_replay_manifest_write") != "validated_existing_identical" or value.get("export_replay_commitment_write") != "validated_existing_identical":
        errors.append("rehearsal.replay")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    upstream = component_m57.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "collection_instrument_ready_but_no_real_component_human_ledgers",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "real_collection_modes": 0,
        "real_private_role_ledgers": 0,
        "real_sealed_role_ledgers": 0,
        "real_exported_component_manifests": 0,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.4 rehearsal: " + "; ".join(report["errors"]))
    return value


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None,
) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.4 rehearsal cannot be rendered")
    counts = audit["counts"]
    total_bytes = sum(rehearsal["artifact_utf8_bytes"].values())
    p_dis = rehearsal["disagreement_counts"]["perception"]
    r_dis = rehearsal["disagreement_counts"]["retrieval"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M57.4 獨立元件證據收集</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07141a;color:#f5fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #335c69;border-radius:20px;background:#0d2027;padding:24px;margin-bottom:18px;overflow:hidden}}.hero{{background:linear-gradient(135deg,#123e48,#432d50)}}h1{{font-size:clamp(30px,5vw,47px);margin:12px 0}}p{{color:#c7dbe3;line-height:1.65}}.deny{{display:inline-block;background:#742b3a;color:#ffe7ec;padding:8px 12px;border-radius:999px;font-weight:850}}.flow{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}}.card{{min-width:0;border:1px solid #466b78;border-radius:15px;background:#08191f;padding:15px}}.card b,.card span{{display:block;overflow-wrap:anywhere}}.card b{{color:#80e6c4}}.card span{{color:#bdd3dc;margin-top:7px;line-height:1.45}}.locked{{border-color:#d49a56}}.private{{border-color:#b9687c}}.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}.metric{{text-align:center}}.metric strong{{display:block;font-size:29px;color:#83e5c5}}.boundary{{border-left:6px solid #dfa752;background:#292116}}@media(max-width:950px){{.flow,.metrics{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:630px){{.flow,.metrics{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="deny">REAL HUMAN EVIDENCE 0 · FORMAL M57 DENIED</span><h1>M57.4 · 不是把答案寫進標註</h1><p>兩位標註者先各自看同一份允許來源，封存後第三位才看見分歧並裁決；每一步都在答案出現前留下時間與雜湊。</p></section>
<section><h2>三個角色，一條不能倒走的路</h2><div class="flow"><div class="card private"><b>① Coder A</b><span>30題私有ledger<br>看不到Coder B</span></div><div class="card private"><b>② Coder B</b><span>30題私有ledger<br>看不到Coder A</span></div><div class="card locked"><b>③ 雙重封存</b><span>兩份30/30才開放裁決</span></div><div class="card"><b>④ Adjudicator</b><span>保留分歧、決定perception/retrieval、建立observable state proxy</span></div><div class="card"><b>⑤ M57.2 manifest</b><span>只在outcome=0時export；不自動跑模型</span></div></div></section>
<section><h2>隔離rehearsal真正走過的量</h2><div class="metrics"><div class="card metric"><strong>60</strong><span>coder entries</span></div><div class="card metric"><strong>30</strong><span>adjudications</span></div><div class="card metric"><strong>90</strong><span>source views</span></div><div class="card metric"><strong>{p_dis}</strong><span>perception分歧</span></div><div class="card metric"><strong>{r_dis}</strong><span>retrieval分歧</span></div><div class="card metric"><strong>0</strong><span>outcome/model calls</span></div></div><p>九個durable artifacts共 {total_bytes:,} bytes，整條synthetic collection為 {rehearsal['elapsed_seconds']:.3f}s。這些數字只證明收集流程，不是三位真人，也不是模型表現。</p></section>
<section class="boundary"><h2>這一頁的證據邊界</h2><p>現在能證明：角色token隔離、先看來源再填、兩位coder封存後才裁決、revision保留、outcome出現就拒絕、輸出符合凍結M57.2 schema。仍不能證明：三個pseudonym就是三位真人、私人心理正確、Uruha元件因果、Equation V1或全面勝LLM。V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18，real rows {counts['real_temporal_rows']}/30，M58 denied。</p></section></main></body></html>"""


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


def _entry_form_payload(role: str, form: dict[str, list[str]], view: dict[str, Any]) -> dict[str, Any]:
    if role in CODER_SLOTS:
        return {
            "perception": {
                "observable_features": [line.strip() for line in form.get("observable_features", [""])[0].splitlines() if line.strip()],
                "representation_note": form.get("representation_note", [""])[0].strip(),
            },
            "retrieval": {
                "selected_history_ids": form.get("history_id", []),
                "selection_rule": form.get("selection_rule", [""])[0].strip(),
            },
        }
    contributions = view["adjudication_context"]["coder_contributions"]
    p_choice = form.get("perception_choice", ["coder_a"])[0]
    r_choice = form.get("retrieval_choice", ["coder_a"])[0]
    if p_choice not in CODER_SLOTS or r_choice not in CODER_SLOTS:
        raise ValueError("invalid adjudication choice")
    state = json.loads(form.get("observable_state_proxy", ["{}"])[0])
    return {
        "resolved_perception": deepcopy(contributions[p_choice]["perception"]),
        "perception_resolution_basis": form.get("perception_resolution_basis", [""])[0].strip(),
        "resolved_retrieval": deepcopy(contributions[r_choice]["retrieval"]),
        "retrieval_resolution_basis": form.get("retrieval_resolution_basis", [""])[0].strip(),
        "observable_state_proxy": state,
    }


def render_collection_page(run_id: str, role: str, token: str, sample_id: str, error: str = "") -> str:
    view = record_component_source_view(run_id, role, token, sample_id)
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
        context = view["adjudication_context"]
        coder_text = html.escape(json.dumps(context["coder_contributions"], ensure_ascii=False, indent=2))
        state_example = html.escape(json.dumps({
            "observable_proxy_variables": {"observable_context": "只寫來源可見內容"},
            "source_refs": ["source_information.current_pre_cutoff_event"],
        }, ensure_ascii=False, indent=2))
        form_body = f"""<pre>{coder_text}</pre><label>Perception採用<select name="perception_choice"><option>coder_a</option><option>coder_b</option></select></label>
<label>Perception裁決理由<textarea name="perception_resolution_basis" required></textarea></label>
<label>Retrieval採用<select name="retrieval_choice"><option>coder_a</option><option>coder_b</option></select></label>
<label>Retrieval裁決理由<textarea name="retrieval_resolution_basis" required></textarea></label>
<label>Observable state proxy JSON<textarea name="observable_state_proxy" required>{state_example}</textarea></label>"""
        independence = f"兩位coder都已封存；系統計算的分歧為 {html.escape(str(context['computed_disagreement']))}。"
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.4 {html.escape(role)}</title><style>
body{{font-family:-apple-system,sans-serif;background:#07151a;color:#eefbff;margin:0}}main{{max-width:900px;margin:auto;padding:24px}}section{{background:#10242b;border:1px solid #3d6470;border-radius:18px;padding:20px;margin-bottom:16px}}label{{display:block;margin:14px 0}}textarea,select{{width:100%;padding:10px;margin-top:6px}}fieldset label{{padding:6px}}pre{{white-space:pre-wrap;background:#07181e;padding:14px;border-radius:12px}}button{{padding:12px 18px;background:#65d2af;border:0;border-radius:10px;font-weight:800}}.error{{color:#ffabb8}}</style></head><body><main><section><b>M57.4 · {html.escape(role)}</b><h1>{html.escape(sample_id)}</h1><p>{html.escape(independence)}</p><p>現在可見輸入：{current}</p></section>{error_html}<section><form method="post" action="/save"><input type="hidden" name="token" value="{html.escape(token)}"><input type="hidden" name="sample_id" value="{html.escape(sample_id)}">{form_body}<button>保存這一題</button></form></section></main></body></html>"""


def serve_collection(run_id: str, role: str, session_token: str, port: int) -> None:
    context = _context(run_id)
    order = _sample_order(context)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: str, status: int = 200) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            token = query.get("token", [""])[0]
            sample_id = query.get("sample", [order[0]])[0]
            if token != session_token:
                self._send("invalid session token", 403)
                return
            try:
                self._send(render_collection_page(run_id, role, token, sample_id))
            except (ValueError, PermissionError, FileNotFoundError) as exc:
                self._send(html.escape(str(exc)), 400)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self._send("not found", 404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 131072:
                self._send("invalid form size", 400)
                return
            form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            token = form.get("token", [""])[0]
            sample_id = form.get("sample_id", [""])[0]
            if token != session_token:
                self._send("invalid session token", 403)
                return
            try:
                view = record_component_source_view(run_id, role, token, sample_id)
                payload = _entry_form_payload(role, form, view)
                result = save_component_evidence_entry(run_id, role, token, sample_id, payload)
                next_index = min(len(order) - 1, order.index(sample_id) + 1)
                next_url = f"/?token={urllib.parse.quote(token)}&sample={urllib.parse.quote(order[next_index])}"
                self.send_response(303)
                self.send_header("Location", next_url)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                del result
            except (ValueError, PermissionError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._send(render_collection_page(run_id, role, token, sample_id, str(exc)), 400)

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
    parser = argparse.ArgumentParser(description="M57.4 component-evidence collection")
    sub = parser.add_subparsers(dest="command", required=True)
    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--port", type=int, default=7926)
    collect = sub.add_parser("collect")
    collect.add_argument("--run-id", required=True)
    collect.add_argument("--role", choices=ROLE_SLOTS, required=True)
    collect.add_argument("--token", required=True)
    collect.add_argument("--port", type=int, required=True)
    sub.add_parser("rehearsal")
    sub.add_parser("audit")
    args = parser.parse_args()
    if args.command == "dashboard":
        serve_dashboard(args.port)
    elif args.command == "collect":
        serve_collection(args.run_id, args.role, args.token, args.port)
    elif args.command == "rehearsal":
        print(json.dumps(build_engineering_rehearsal(), ensure_ascii=False, indent=2))
    elif args.command == "audit":
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
