#!/usr/bin/env python3
"""Explicit, private adjudication and M55 temporal-record assembly.

This tool is intentionally downstream of two complete independent V9 ledgers
and their two complete M55 boundary ledgers.  It never creates an adjudicated
entry automatically: each slot requires a human submit that accepts coder A,
accepts coder B, or records a manual resolution.  Real initialization and
serving remain gated by the frozen V7 reliability authorization.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import secrets
from typing import Any
import urllib.parse

import m55_boundary_extension_tool as boundary_m55
import m55_temporal_row_contract as temporal_m55
import public_persona_target_calibration_coding_v9 as v9
from public_persona_contrast_coding_tool_v6 import (
    _atomic_write_json,
    resolve_private_path,
    validate_coder_pseudonym,
)


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m55_boundary_adjudication_tool_v1.json"
DEFAULT_PRIVATE_ROOT = ROOT / "analysis/local_m55_boundary_adjudication_v1"
LEDGER_SCHEMA = "uruha_m55_private_boundary_adjudication_ledger_v1"
REAL_KIND = temporal_m55.REAL_KIND
SYNTHETIC_KIND = temporal_m55.SYNTHETIC_KIND
DECISIONS = {
    "accept_coder_a_complete_record",
    "accept_coder_b_complete_record",
    "manual_resolution",
}
ENTRY_FIELDS = {
    "sampling_slot_id",
    "source_id",
    "adjudicator_pseudonym",
    "coder_a_pseudonym",
    "coder_b_pseudonym",
    "source_v9_entry_a_hash",
    "source_v9_entry_b_hash",
    "boundary_entry_a_hash",
    "boundary_entry_b_hash",
    "decision",
    "resolution_record",
    "adjudication_reason",
    "adjudication_confidence",
    "both_independent_records_reviewed_attestation",
    "no_automatic_merge_attestation",
    "paraphrase_and_no_quote_attestation",
    "updated_at",
}
LEDGER_FIELDS = {
    "schema",
    "version",
    "status",
    "data_kind",
    "adjudicator_pseudonym",
    "coder_a_pseudonym",
    "coder_b_pseudonym",
    "source_v9_a_hash",
    "source_v9_b_hash",
    "boundary_ledger_a_hash",
    "boundary_ledger_b_hash",
    "contract_hash",
    "created_at",
    "updated_at",
    "entries",
    "data_boundary",
}
DATA_BOUNDARY = {
    "private_gitignored_storage_required": True,
    "independent_source_ledgers_preserved": True,
    "source_ledgers_bound_by_hash": True,
    "explicit_human_submit_required_per_slot": True,
    "exact_pairs_auto_accepted": False,
    "automatic_timestamp_average_allowed": False,
    "automatic_text_merge_allowed": False,
    "automatic_behavior_label_choice_allowed": False,
    "raw_or_verbatim_content_allowed": False,
    "private_mental_fact_allowed": False,
    "model_execution_allowed": False,
    "production_memory_write_allowed": False,
}
FORBIDDEN_KEYS = {
    "raw_text",
    "raw_media",
    "audio",
    "image",
    "caption",
    "captions",
    "transcript",
    "verbatim_transcript",
    "quote_text",
    "target_reply",
    "expected_reply",
    "reference_answer",
    "answer_key",
    "model_output",
    "training_text",
    "private_motive",
    "private_emotion",
    "automatic_average",
    "automatic_timestamp_average",
    "automatic_text_merge",
    "merged_text",
}
MANUAL_FIELDS = {
    "event_start_seconds",
    "observable_input_start_seconds",
    "prediction_cutoff_seconds",
    "observable_behavior_start_seconds",
    "observable_behavior_end_seconds",
    "event_end_seconds",
    "observable_input_paraphrase",
    "completed_event_summary",
    "behavior_label",
    "acceptable_behavior_labels",
    "context_family",
    "observable_audience_relation",
}
SUBMIT_FIELDS = {
    "sampling_slot_id",
    "decision",
    "adjudication_reason",
    "adjudication_confidence",
    "both_independent_records_reviewed_attestation",
    "no_automatic_merge_attestation",
    "paraphrase_and_no_quote_attestation",
} | MANUAL_FIELDS


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0 <= float(value)
    )


def _parse_number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if math.isfinite(float(value)) else None
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _find_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_KEYS:
                found.append(path)
            found.extend(_find_forbidden_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def _binding_valid(binding: Any) -> bool:
    if not isinstance(binding, dict):
        return False
    path_text = str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return bool(path_text) and len(expected) == 64 and path.is_file() and sha256_file(path) == expected


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m55_boundary_adjudication_tool_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 7:
        errors.append("bindings")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding:{name}")
    ledger = contract.get("ledger") or {}
    if ledger.get("schema") != LEDGER_SCHEMA:
        errors.append("ledger.schema")
    if ledger.get("status") != "private_explicit_boundary_adjudication_ledger":
        errors.append("ledger.status")
    if ledger.get("canonical_coder_order") != "lexicographic_pseudonym":
        errors.append("ledger.canonical_coder_order")
    if ledger.get("initial_entry_count") != 0:
        errors.append("ledger.initial_entry_count")
    if set(ledger.get("required_entry_fields") or []) != ENTRY_FIELDS:
        errors.append("ledger.required_entry_fields")
    if set(contract.get("decisions") or []) != DECISIONS:
        errors.append("decisions")
    adjudication = contract.get("adjudication") or {}
    for field in (
        "every_paired_slot_requires_explicit_human_submit",
        "original_independent_entries_preserved",
        "manual_resolution_must_name_reason",
        "entry_hashes_revalidated_on_every_page_load",
        "manual_resolution_requires_no_automatic_merge_attestation",
        "manual_resolution_payload_may_not_request_automatic_average_or_text_merge",
    ):
        if adjudication.get(field) is not True:
            errors.append(f"adjudication:{field}")
    for field in (
        "exact_pairs_auto_accepted",
        "automatic_timestamp_average_allowed",
        "automatic_text_merge_allowed",
        "automatic_behavior_label_choice_allowed",
    ):
        if adjudication.get(field) is not False:
            errors.append(f"adjudication:{field}")
    pack = contract.get("record_pack") or {}
    if pack.get("schema") != temporal_m55.SCHEMA:
        errors.append("record_pack.schema")
    if pack.get("required_record_field_count") != 22:
        errors.append("record_pack.required_record_field_count")
    if pack.get("synthetic_independent_coder_count") != 0:
        errors.append("record_pack.synthetic_coder_count")
    if pack.get("real_independent_coder_count") != 2:
        errors.append("record_pack.real_coder_count")
    authorization = contract.get("authorization") or {}
    for field in (
        "synthetic_demo_authorizes_human_reliability",
        "synthetic_demo_authorizes_target_coding",
        "synthetic_demo_authorizes_m55_completion",
        "adjudication_or_pack_alone_authorizes_m56",
        "sealed_holdout_access",
        "model_execution",
        "production_memory_write",
    ):
        if authorization.get(field) is not False:
            errors.append(f"authorization:{field}")
    for field in (
        "real_initialization_requires_v7_reliability_pass",
        "real_serving_requires_v7_reliability_pass",
    ):
        if authorization.get(field) is not True:
            errors.append(f"authorization:{field}")
    private_root = str((contract.get("private_storage") or {}).get("root") or "")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if private_root != "analysis/local_m55_boundary_adjudication_v1/" or private_root not in gitignore:
        errors.append("private_root_gitignore")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
        "required_entry_field_count": len(ledger.get("required_entry_fields") or []),
    }


def _source_metadata() -> dict[str, dict[str, Any]]:
    payload = load_json(v9.DEFAULT_SOURCE_METADATA)
    return {row["source_id"]: row for row in payload["sources"]}


def _frame_and_codebook() -> tuple[dict[str, Any], dict[str, Any]]:
    return load_json(v9.DEFAULT_FRAME), load_json(v9.DEFAULT_CODEBOOK)


def _selected(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return boundary_m55._selected_v9_entries(ledger)


def _canonical_pair(
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    left = (source_v9_a, boundary_a)
    right = (source_v9_b, boundary_b)
    if str(boundary_a.get("coder_pseudonym")) <= str(boundary_b.get("coder_pseudonym")):
        return left[0], left[1], right[0], right[1]
    return right[0], right[1], left[0], left[1]


def _validate_pair(
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_v9_a, boundary_a, source_v9_b, boundary_b = _canonical_pair(
        source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    boundary_m55.build_boundary_comparison(
        boundary_a, source_v9_a, boundary_b, source_v9_b, require_complete=True
    )
    data_kind = boundary_a["data_kind"]
    if data_kind == REAL_KIND:
        frame, codebook = _frame_and_codebook()
        errors_a = v9.validate_target_ledger(
            source_v9_a, frame, codebook, expected_coder=boundary_a["coder_pseudonym"], require_complete=True
        )
        errors_b = v9.validate_target_ledger(
            source_v9_b, frame, codebook, expected_coder=boundary_b["coder_pseudonym"], require_complete=True
        )
        if errors_a or errors_b:
            raise ValueError(
                "real V9 ledgers must be complete: "
                + "; ".join([f"A:{error}" for error in errors_a] + [f"B:{error}" for error in errors_b])
            )
    slots_a = set(boundary_a["entries"])
    slots_b = set(boundary_b["entries"])
    if not slots_a or slots_a != slots_b:
        raise ValueError("paired boundary ledgers must contain the same nonempty slots")
    return source_v9_a, boundary_a, source_v9_b, boundary_b


def initialize_adjudication_ledger(
    adjudicator_pseudonym: str,
    ledger_path: str | Path,
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
    *,
    authorization_lock: str | Path = v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
    overwrite: bool = False,
) -> tuple[Path, dict[str, Any]]:
    adjudicator = validate_coder_pseudonym(adjudicator_pseudonym)
    source_v9_a, boundary_a, source_v9_b, boundary_b = _validate_pair(
        source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    data_kind = boundary_a["data_kind"]
    if data_kind == REAL_KIND:
        authorized, reason = v9.human_use_authorized(authorization_lock)
        if not authorized:
            raise PermissionError(reason)
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise ValueError("invalid M55 adjudication contract: " + "; ".join(contract_report["errors"]))
    path = resolve_private_path(ledger_path, private_root)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}")
    now = utc_now()
    ledger = {
        "schema": LEDGER_SCHEMA,
        "version": "1.0.0",
        "status": "private_explicit_boundary_adjudication_ledger",
        "data_kind": data_kind,
        "adjudicator_pseudonym": adjudicator,
        "coder_a_pseudonym": boundary_a["coder_pseudonym"],
        "coder_b_pseudonym": boundary_b["coder_pseudonym"],
        "source_v9_a_hash": digest(source_v9_a),
        "source_v9_b_hash": digest(source_v9_b),
        "boundary_ledger_a_hash": digest(boundary_a),
        "boundary_ledger_b_hash": digest(boundary_b),
        "contract_hash": contract_report["contract_hash"],
        "created_at": now,
        "updated_at": now,
        "entries": {},
        "data_boundary": deepcopy(DATA_BOUNDARY),
    }
    _atomic_write_json(path, ledger)
    return path, ledger


def _record_status(data_kind: str) -> tuple[str, int]:
    if data_kind == SYNTHETIC_KIND:
        return temporal_m55.SYNTHETIC_REVIEW, 0
    return "adjudicated_after_retained_disagreement", 2


def _published_at(source_id: str) -> str:
    source = _source_metadata().get(source_id)
    if source is None:
        raise ValueError(f"source metadata unavailable: {source_id}")
    return str(source["published_at"])


def _accepted_record(
    source_entry: dict[str, Any], boundary_entry: dict[str, Any], data_kind: str
) -> dict[str, Any]:
    review_status, coder_count = _record_status(data_kind)
    label = source_entry["dialogue_act_or_action_label"]
    return {
        "sample_id": f"m55::{source_entry['sampling_slot_id']}",
        "sampling_slot_id": source_entry["sampling_slot_id"],
        "source_id": source_entry["source_id"],
        "source_published_at": _published_at(source_entry["source_id"]),
        "event_start_seconds": boundary_entry["event_start_seconds"],
        "observable_input_start_seconds": boundary_entry["observable_input_start_seconds"],
        "prediction_cutoff_seconds": boundary_entry["prediction_cutoff_seconds"],
        "observable_behavior_start_seconds": boundary_entry["observable_behavior_start_seconds"],
        "observable_behavior_end_seconds": boundary_entry["observable_behavior_end_seconds"],
        "event_end_seconds": boundary_entry["event_end_seconds"],
        "observable_input_paraphrase": boundary_entry["observable_input_paraphrase"],
        "completed_event_summary": boundary_entry["completed_event_summary"],
        "behavior_label": label,
        "acceptable_behavior_labels": [label],
        "annotation_confidence": boundary_entry["annotation_confidence"],
        "context_family": source_entry["context_family"],
        "observable_audience_relation": source_entry["observable_audience_relation"],
        "independent_coder_count": coder_count,
        "review_status": review_status,
        "prediction_boundary_attestation": boundary_entry["prediction_boundary_attestation"],
        "outcome_excluded_from_input_attestation": boundary_entry["outcome_excluded_from_input_attestation"],
        "paraphrase_and_no_quote_attestation": boundary_entry["paraphrase_and_no_quote_attestation"],
    }


def _manual_record(
    payload: dict[str, Any], source_entry: dict[str, Any], data_kind: str
) -> dict[str, Any]:
    review_status, coder_count = _record_status(data_kind)
    acceptable = payload.get("acceptable_behavior_labels")
    if isinstance(acceptable, str):
        acceptable = [item.strip() for item in acceptable.split(",") if item.strip()]
    elif isinstance(acceptable, list):
        acceptable = [str(item).strip() for item in acceptable if str(item).strip()]
    else:
        acceptable = []
    return {
        "sample_id": f"m55::{source_entry['sampling_slot_id']}",
        "sampling_slot_id": source_entry["sampling_slot_id"],
        "source_id": source_entry["source_id"],
        "source_published_at": _published_at(source_entry["source_id"]),
        "event_start_seconds": _parse_number(payload.get("event_start_seconds")),
        "observable_input_start_seconds": _parse_number(payload.get("observable_input_start_seconds")),
        "prediction_cutoff_seconds": _parse_number(payload.get("prediction_cutoff_seconds")),
        "observable_behavior_start_seconds": _parse_number(payload.get("observable_behavior_start_seconds")),
        "observable_behavior_end_seconds": _parse_number(payload.get("observable_behavior_end_seconds")),
        "event_end_seconds": _parse_number(payload.get("event_end_seconds")),
        "observable_input_paraphrase": str(payload.get("observable_input_paraphrase") or "").strip(),
        "completed_event_summary": str(payload.get("completed_event_summary") or "").strip(),
        "behavior_label": str(payload.get("behavior_label") or "").strip(),
        "acceptable_behavior_labels": acceptable,
        "annotation_confidence": _parse_number(payload.get("adjudication_confidence")),
        "context_family": str(payload.get("context_family") or "").strip(),
        "observable_audience_relation": str(payload.get("observable_audience_relation") or "").strip(),
        "independent_coder_count": coder_count,
        "review_status": review_status,
        "prediction_boundary_attestation": payload.get("both_independent_records_reviewed_attestation") is True,
        "outcome_excluded_from_input_attestation": payload.get("no_automatic_merge_attestation") is True,
        "paraphrase_and_no_quote_attestation": payload.get("paraphrase_and_no_quote_attestation") is True,
    }


def _pack_for_records(records: list[dict[str, Any]], data_kind: str) -> dict[str, Any]:
    contract_hash = temporal_m55.validate_contract_m55()["contract_hash"]
    return {
        "schema": temporal_m55.SCHEMA,
        "version": "1.0.0",
        "data_kind": data_kind,
        "status": (
            "synthetic_explicit_adjudication_contract_only"
            if data_kind == SYNTHETIC_KIND
            else "private_real_adjudicated_record_pack_pending_m55_gate"
        ),
        "dataset_id": (
            "synthetic-m55-adjudication-v1"
            if data_kind == SYNTHETIC_KIND
            else "uruha-m55-private-adjudicated-temporal-records-v1"
        ),
        "target_id": (
            "synthetic_m55_contract_subject"
            if data_kind == SYNTHETIC_KIND
            else "ichinose_uruha_public_persona"
        ),
        "contract_hash": contract_hash,
        "records": records,
    }


def _pair_entries(
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
    slot_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected_a = _selected(source_v9_a)
    selected_b = _selected(source_v9_b)
    if slot_id not in selected_a or slot_id not in selected_b:
        raise ValueError("slot is not selected by both coders")
    if slot_id not in boundary_a["entries"] or slot_id not in boundary_b["entries"]:
        raise ValueError("slot boundary is incomplete")
    source_a = selected_a[slot_id]
    source_b = selected_b[slot_id]
    if source_a.get("source_id") != source_b.get("source_id"):
        raise ValueError("paired source id mismatch")
    return source_a, boundary_a["entries"][slot_id], source_b, boundary_b["entries"][slot_id]


def _expected_entry_hashes(
    source_a: dict[str, Any], boundary_entry_a: dict[str, Any], source_b: dict[str, Any], boundary_entry_b: dict[str, Any]
) -> dict[str, str]:
    return {
        "source_v9_entry_a_hash": digest(source_a),
        "source_v9_entry_b_hash": digest(source_b),
        "boundary_entry_a_hash": digest(boundary_entry_a),
        "boundary_entry_b_hash": digest(boundary_entry_b),
    }


def normalize_adjudication_entry(
    payload: dict[str, Any],
    ledger: dict[str, Any],
    source_a: dict[str, Any],
    boundary_entry_a: dict[str, Any],
    source_b: dict[str, Any],
    boundary_entry_b: dict[str, Any],
) -> dict[str, Any]:
    decision = str(payload.get("decision") or "")
    if decision == "accept_coder_a_complete_record":
        record = _accepted_record(source_a, boundary_entry_a, ledger["data_kind"])
    elif decision == "accept_coder_b_complete_record":
        record = _accepted_record(source_b, boundary_entry_b, ledger["data_kind"])
    else:
        record = _manual_record(payload, source_a, ledger["data_kind"])
    return {
        "sampling_slot_id": source_a["sampling_slot_id"],
        "source_id": source_a["source_id"],
        "adjudicator_pseudonym": ledger["adjudicator_pseudonym"],
        "coder_a_pseudonym": ledger["coder_a_pseudonym"],
        "coder_b_pseudonym": ledger["coder_b_pseudonym"],
        **_expected_entry_hashes(source_a, boundary_entry_a, source_b, boundary_entry_b),
        "decision": decision,
        "resolution_record": record,
        "adjudication_reason": str(payload.get("adjudication_reason") or "").strip(),
        "adjudication_confidence": _parse_number(payload.get("adjudication_confidence")),
        "both_independent_records_reviewed_attestation": payload.get("both_independent_records_reviewed_attestation") is True,
        "no_automatic_merge_attestation": payload.get("no_automatic_merge_attestation") is True,
        "paraphrase_and_no_quote_attestation": payload.get("paraphrase_and_no_quote_attestation") is True,
        "updated_at": utc_now(),
    }


def validate_adjudication_entry(
    entry: dict[str, Any],
    ledger: dict[str, Any],
    source_a: dict[str, Any],
    boundary_entry_a: dict[str, Any],
    source_b: dict[str, Any],
    boundary_entry_b: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return ["entry:object_required"]
    extra = set(entry) - ENTRY_FIELDS
    missing = ENTRY_FIELDS - set(entry)
    if extra:
        errors.append("unexpected_fields:" + ",".join(sorted(extra)))
    if missing:
        errors.append("missing_fields:" + ",".join(sorted(missing)))
    errors.extend(f"forbidden_content_key:{path}" for path in _find_forbidden_keys(entry))
    expected_literals = {
        "sampling_slot_id": source_a.get("sampling_slot_id"),
        "source_id": source_a.get("source_id"),
        "adjudicator_pseudonym": ledger.get("adjudicator_pseudonym"),
        "coder_a_pseudonym": ledger.get("coder_a_pseudonym"),
        "coder_b_pseudonym": ledger.get("coder_b_pseudonym"),
        **_expected_entry_hashes(source_a, boundary_entry_a, source_b, boundary_entry_b),
    }
    for field, expected in expected_literals.items():
        if entry.get(field) != expected:
            errors.append(f"{field}:stale_or_mismatch")
    decision = entry.get("decision")
    if decision not in DECISIONS:
        errors.append("decision:not_allowed")
    reason = entry.get("adjudication_reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("adjudication_reason:required")
    elif len(reason.strip()) > 500:
        errors.append("adjudication_reason:too_long")
    confidence = entry.get("adjudication_confidence")
    if not _is_number(confidence) or float(confidence) > 1:
        errors.append("adjudication_confidence:range")
    for field in (
        "both_independent_records_reviewed_attestation",
        "no_automatic_merge_attestation",
        "paraphrase_and_no_quote_attestation",
    ):
        if entry.get(field) is not True:
            errors.append(f"{field}:required")
    if not _valid_timestamp(entry.get("updated_at")):
        errors.append("updated_at:invalid")
    record = entry.get("resolution_record")
    if decision == "accept_coder_a_complete_record":
        if record != _accepted_record(source_a, boundary_entry_a, ledger["data_kind"]):
            errors.append("resolution_record:must_exactly_copy_coder_a")
    elif decision == "accept_coder_b_complete_record":
        if record != _accepted_record(source_b, boundary_entry_b, ledger["data_kind"]):
            errors.append("resolution_record:must_exactly_copy_coder_b")
    if isinstance(record, dict):
        validation = temporal_m55.validate_record_pack_m55(
            _pack_for_records([record], ledger.get("data_kind"))
        )
        errors.extend(f"resolution_record:{error}" for error in validation["errors"])
    else:
        errors.append("resolution_record:object_required")
    return errors


def validate_adjudication_ledger(
    ledger: dict[str, Any],
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
    *,
    require_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(ledger, dict):
        return ["ledger:object_required"]
    extra = set(ledger) - LEDGER_FIELDS
    missing = LEDGER_FIELDS - set(ledger)
    if extra:
        errors.append("ledger:unexpected_fields:" + ",".join(sorted(extra)))
    if missing:
        errors.append("ledger:missing_fields:" + ",".join(sorted(missing)))
    try:
        source_v9_a, boundary_a, source_v9_b, boundary_b = _validate_pair(
            source_v9_a, boundary_a, source_v9_b, boundary_b
        )
    except (ValueError, KeyError) as exc:
        return errors + [f"source_pair:{exc}"]
    expected = {
        "schema": LEDGER_SCHEMA,
        "version": "1.0.0",
        "status": "private_explicit_boundary_adjudication_ledger",
        "data_kind": boundary_a["data_kind"],
        "coder_a_pseudonym": boundary_a["coder_pseudonym"],
        "coder_b_pseudonym": boundary_b["coder_pseudonym"],
        "source_v9_a_hash": digest(source_v9_a),
        "source_v9_b_hash": digest(source_v9_b),
        "boundary_ledger_a_hash": digest(boundary_a),
        "boundary_ledger_b_hash": digest(boundary_b),
        "contract_hash": validate_contract()["contract_hash"],
        "data_boundary": DATA_BOUNDARY,
    }
    for field, expected_value in expected.items():
        if ledger.get(field) != expected_value:
            errors.append(f"{field}:stale_or_mismatch")
    try:
        validate_coder_pseudonym(ledger.get("adjudicator_pseudonym"))
    except ValueError:
        errors.append("adjudicator_pseudonym")
    if not _valid_timestamp(ledger.get("created_at")) or not _valid_timestamp(ledger.get("updated_at")):
        errors.append("ledger_timestamp")
    errors.extend(f"forbidden_content_key:{path}" for path in _find_forbidden_keys(ledger))
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return errors + ["entries:object_required"]
    paired_slots = set(boundary_a["entries"])
    if set(entries) - paired_slots:
        errors.append("entries:unknown_slot")
    if require_complete and set(entries) != paired_slots:
        errors.append("entries:incomplete")
    for slot_id, entry in entries.items():
        if slot_id not in paired_slots:
            continue
        source_a, bound_a, source_b, bound_b = _pair_entries(
            source_v9_a, boundary_a, source_v9_b, boundary_b, slot_id
        )
        errors.extend(
            f"{slot_id}:{error}"
            for error in validate_adjudication_entry(
                entry, ledger, source_a, bound_a, source_b, bound_b
            )
        )
    return errors


def save_adjudication_entry(
    ledger_path: str | Path,
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
    payload: dict[str, Any],
    *,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
) -> dict[str, Any]:
    forbidden = _find_forbidden_keys(payload)
    if forbidden:
        raise ValueError("forbidden adjudication payload: " + ",".join(forbidden))
    unexpected = set(payload) - SUBMIT_FIELDS
    if unexpected:
        raise ValueError("unexpected adjudication payload: " + ",".join(sorted(unexpected)))
    path = resolve_private_path(ledger_path, private_root)
    ledger = load_json(path)
    existing_errors = validate_adjudication_ledger(
        ledger, source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    if existing_errors:
        raise ValueError("invalid adjudication ledger: " + "; ".join(existing_errors))
    source_v9_a, boundary_a, source_v9_b, boundary_b = _canonical_pair(
        source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    slot_id = str(payload.get("sampling_slot_id") or "")
    source_a, bound_a, source_b, bound_b = _pair_entries(
        source_v9_a, boundary_a, source_v9_b, boundary_b, slot_id
    )
    entry = normalize_adjudication_entry(
        payload, ledger, source_a, bound_a, source_b, bound_b
    )
    entry_errors = validate_adjudication_entry(
        entry, ledger, source_a, bound_a, source_b, bound_b
    )
    if entry_errors:
        raise ValueError("invalid adjudication entry: " + "; ".join(entry_errors))
    candidate = deepcopy(ledger)
    candidate["entries"][slot_id] = entry
    candidate["updated_at"] = utc_now()
    candidate_errors = validate_adjudication_ledger(
        candidate, source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    if candidate_errors:
        raise ValueError("invalid adjudication ledger update: " + "; ".join(candidate_errors))
    _atomic_write_json(path, candidate)
    return candidate


def assemble_record_pack(
    ledger: dict[str, Any],
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_adjudication_ledger(
        ledger, source_v9_a, boundary_a, source_v9_b, boundary_b, require_complete=True
    )
    if errors:
        raise ValueError("adjudication ledger is not exportable: " + "; ".join(errors))
    records = [
        deepcopy(ledger["entries"][slot_id]["resolution_record"])
        for slot_id in sorted(ledger["entries"])
    ]
    pack = _pack_for_records(records, ledger["data_kind"])
    validation = temporal_m55.validate_record_pack_m55(pack)
    if not validation["valid"]:
        raise ValueError("assembled record pack invalid: " + "; ".join(validation["errors"]))
    return pack


def build_export_report(
    ledger: dict[str, Any],
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
) -> dict[str, Any]:
    pack = assemble_record_pack(
        ledger, source_v9_a, boundary_a, source_v9_b, boundary_b
    )
    validation = temporal_m55.validate_record_pack_m55(pack)
    return {
        "schema": "uruha_m55_boundary_adjudication_export_report_v1",
        "status": "synthetic_engineering_only" if ledger["data_kind"] == SYNTHETIC_KIND else "private_real_pack_assembled_pending_m55_gate",
        "data_kind": ledger["data_kind"],
        "record_count": len(pack["records"]),
        "record_pack_hash": digest(pack),
        "temporal_contract_valid": validation["valid"],
        "human_coder_count_claimed": 0 if ledger["data_kind"] == SYNTHETIC_KIND else 2,
        "model_call_count": 0,
        "sealed_holdout_accessed": False,
        "automatic_average_or_merge_performed": False,
        "m55_complete": False,
        "m56_authorized": False,
        "claim_boundary": "explicit adjudication and private record assembly only; no Equation V1 validation or model comparison authorization",
    }


def _checked(value: bool) -> str:
    return " checked" if value else ""


def _options(values: list[str], selected: str = "") -> str:
    tags = []
    for value in values:
        mark = " selected" if value == selected else ""
        tags.append(f'<option value="{html.escape(value)}"{mark}>{html.escape(value)}</option>')
    return "".join(tags)


def _record_card(title: str, source: dict[str, Any], boundary: dict[str, Any]) -> str:
    return f"""
    <article class="lane">
      <div class="lane-title">{html.escape(title)}</div>
      <div class="pill">{html.escape(str(source['context_family']))}</div>
      <div class="pill">{html.escape(str(source['dialogue_act_or_action_label']))}</div>
      <div class="pill">{html.escape(str(source['observable_audience_relation']))}</div>
      <div class="timeline"><span>X</span><b>{boundary['observable_input_start_seconds']}</b><i>→</i><span>cutoff</span><b>{boundary['prediction_cutoff_seconds']}</b><i>→</i><span>Y</span><b>{boundary['observable_behavior_start_seconds']}–{boundary['observable_behavior_end_seconds']}</b></div>
      <dl><dt>cutoff 前輸入</dt><dd>{html.escape(str(boundary['observable_input_paraphrase']))}</dd><dt>完成後摘要</dt><dd>{html.escape(str(boundary['completed_event_summary']))}</dd></dl>
    </article>"""


def render_adjudication_page(
    ledger: dict[str, Any],
    source_v9_a: dict[str, Any],
    boundary_a: dict[str, Any],
    source_v9_b: dict[str, Any],
    boundary_b: dict[str, Any],
    token: str,
    slot_order: list[str],
    slot_index: int,
    error: str = "",
) -> str:
    slot_index = max(0, min(slot_index, len(slot_order) - 1))
    slot_id = slot_order[slot_index]
    source_a, bound_a, source_b, bound_b = _pair_entries(
        source_v9_a, boundary_a, source_v9_b, boundary_b, slot_id
    )
    current = ledger["entries"].get(slot_id) or {}
    record = current.get("resolution_record") or {}
    _, codebook = _frame_and_codebook()
    done = len(ledger["entries"])
    prev_link = f"/?token={urllib.parse.quote(token)}&slot={slot_index}" if slot_index else ""
    next_link = f"/?token={urllib.parse.quote(token)}&slot={slot_index + 2}" if slot_index + 1 < len(slot_order) else ""
    nav = " ".join(
        item for item in (
            f'<a href="{prev_link}">← 上一筆</a>' if prev_link else "",
            f'<a href="{next_link}">下一筆 →</a>' if next_link else "",
        ) if item
    )
    message = f'<div class="error">{html.escape(error)}</div>' if error else ""
    decisions = [
        ("accept_coder_a_complete_record", "明確接受 Coder A 的完整紀錄"),
        ("accept_coder_b_complete_record", "明確接受 Coder B 的完整紀錄"),
        ("manual_resolution", "手動建立裁決紀錄"),
    ]
    decision_html = "".join(
        f'<label class="choice"><input type="radio" name="decision" value="{value}"{_checked(current.get("decision") == value)} required>{label}</label>'
        for value, label in decisions
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M55 人工裁決</title>
<style>body{{margin:0;background:#0a1020;color:#edf3ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}.hero,.card,.lane{{background:#121c32;border:1px solid #2b3b5f;border-radius:18px;padding:20px;box-shadow:0 14px 40px #0005}}.hero{{background:linear-gradient(135deg,#18294b,#171a35)}}h1{{margin:.2em 0}}.warning{{color:#ffd58a}}.progress{{height:12px;background:#27344f;border-radius:9px;overflow:hidden}}.progress i{{display:block;height:100%;background:#66d9c6;width:{100*done/max(1,len(slot_order)):.1f}%}}.lanes{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}}.lane-title{{font-size:20px;font-weight:800;margin-bottom:12px}}.pill{{display:inline-block;border:1px solid #516487;border-radius:999px;padding:5px 9px;margin:2px;color:#bcd5ff}}.timeline{{display:flex;align-items:center;gap:8px;background:#091120;border-radius:12px;padding:14px;margin:14px 0;flex-wrap:wrap}}.timeline span{{color:#6fe0cd;font-weight:800}}dl{{display:grid;grid-template-columns:120px 1fr;gap:8px}}dt{{color:#8da6cf}}dd{{margin:0}}.card{{margin-top:18px}}.choice{{display:block;background:#0d1628;padding:11px;border-radius:10px;margin:8px 0}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}label{{color:#c7d6ef}}input,select,textarea{{box-sizing:border-box;width:100%;margin-top:5px;padding:10px;border-radius:9px;border:1px solid #405273;background:#081120;color:#fff}}input[type=checkbox],input[type=radio]{{width:auto;margin-right:8px}}textarea{{min-height:74px}}button{{background:#68dbc9;color:#07101e;border:0;border-radius:12px;padding:13px 20px;font-weight:800;cursor:pointer}}a{{color:#79c9ff}}.error{{background:#4b1d28;border:1px solid #a54c61;padding:12px;border-radius:10px}}small{{color:#91a5c7}}@media(max-width:800px){{.lanes,.grid{{grid-template-columns:1fr}}}}</style></head><body><main>
<section class="hero"><small>M55 · explicit human adjudication</small><h1>兩份獨立觀察，逐筆做一個可追溯決定</h1><p class="warning">這裡不平均時間、不挑標籤、不合併文字。即使兩份完全一致，也必須由人明確提交。</p><p>Adjudicator: <b>{html.escape(ledger['adjudicator_pseudonym'])}</b> · {done}/{len(slot_order)} 已裁決 · 第 {slot_index+1} 筆</p><div class="progress"><i></i></div><p>{nav}</p></section>{message}
<section class="lanes">{_record_card('Coder A · ' + ledger['coder_a_pseudonym'], source_a, bound_a)}{_record_card('Coder B · ' + ledger['coder_b_pseudonym'], source_b, bound_b)}</section>
<form method="post" class="card"><input type="hidden" name="token" value="{html.escape(token)}"><input type="hidden" name="sampling_slot_id" value="{html.escape(slot_id)}"><h2>人工作決定</h2>{decision_html}
<label>裁決理由<textarea name="adjudication_reason" maxlength="500" required>{html.escape(str(current.get('adjudication_reason') or ''))}</textarea></label>
<label>裁決信心 0–1<input name="adjudication_confidence" type="number" min="0" max="1" step="0.01" value="{html.escape(str(current.get('adjudication_confidence') if current else ''))}" required></label>
<h3>手動裁決時填寫</h3><div class="grid">{''.join(f'<label>{field}<input name="{field}" value="{html.escape(str(record.get(field) or ""))}"></label>' for field in ('event_start_seconds','observable_input_start_seconds','prediction_cutoff_seconds','observable_behavior_start_seconds','observable_behavior_end_seconds','event_end_seconds'))}</div>
<label>cutoff 前輸入改寫<textarea name="observable_input_paraphrase">{html.escape(str(record.get('observable_input_paraphrase') or ''))}</textarea></label><label>完成事件摘要<textarea name="completed_event_summary">{html.escape(str(record.get('completed_event_summary') or ''))}</textarea></label>
<div class="grid"><label>行為標籤<select name="behavior_label"><option value=""></option>{_options(codebook['dialogue_act_or_action_labels'], str(record.get('behavior_label') or ''))}</select></label><label>可接受行為標籤（逗號分隔）<input name="acceptable_behavior_labels" value="{html.escape(','.join(record.get('acceptable_behavior_labels') or []))}"></label><label>情境<select name="context_family"><option value=""></option>{_options(codebook['context_families'], str(record.get('context_family') or ''))}</select></label><label>關係<select name="observable_audience_relation"><option value=""></option>{_options(codebook['audience_relations'], str(record.get('observable_audience_relation') or ''))}</select></label></div>
<label class="choice"><input type="checkbox" name="both_independent_records_reviewed_attestation"{_checked(current.get('both_independent_records_reviewed_attestation') is True)} required>我已逐一查看兩份獨立紀錄</label><label class="choice"><input type="checkbox" name="no_automatic_merge_attestation"{_checked(current.get('no_automatic_merge_attestation') is True)} required>這是我的明確判斷，沒有要求軟體平均或合併</label><label class="choice"><input type="checkbox" name="paraphrase_and_no_quote_attestation"{_checked(current.get('paraphrase_and_no_quote_attestation') is True)} required>所有文字均為改寫，沒有逐字引文</label><button type="submit">儲存這一筆人工作決定</button></form>
<section class="card"><h2>證據邊界</h2><p>完成此頁只會建立 private temporal record pack。M55 不會因此自動完成，M56 仍禁止，模型呼叫為 0。</p></section></main></body></html>"""


def _form_payload(form: dict[str, list[str]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, values in form.items():
        if key == "token" or not values:
            continue
        payload[key] = values[-1]
    for key in (
        "both_independent_records_reviewed_attestation",
        "no_automatic_merge_attestation",
        "paraphrase_and_no_quote_attestation",
    ):
        payload[key] = key in form
    return payload


def make_adjudication_handler(
    ledger_path: str | Path,
    private_root: str | Path,
    token: str,
    source_v9_a_path: str | Path,
    boundary_a_path: str | Path,
    source_v9_b_path: str | Path,
    boundary_b_path: str | Path,
) -> type[BaseHTTPRequestHandler]:
    ledger_path = resolve_private_path(ledger_path, private_root)
    source_paths = tuple(Path(path).resolve() for path in (source_v9_a_path, source_v9_b_path))
    boundary_paths = tuple(Path(path).resolve() for path in (boundary_a_path, boundary_b_path))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _authorized(self, query: dict[str, list[str]]) -> bool:
            supplied = (query.get("token") or [""])[-1]
            return secrets.compare_digest(supplied, token)

        def _load_all(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
            ledger = load_json(ledger_path)
            source_a, source_b = (load_json(path) for path in source_paths)
            bound_a, bound_b = (load_json(path) for path in boundary_paths)
            errors = validate_adjudication_ledger(ledger, source_a, bound_a, source_b, bound_b)
            if errors:
                raise ValueError("; ".join(errors))
            source_a, bound_a, source_b, bound_b = _canonical_pair(source_a, bound_a, source_b, bound_b)
            return ledger, source_a, bound_a, source_b, bound_b

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/health":
                self._send(200, "ok", "text/plain; charset=utf-8")
                return
            query = urllib.parse.parse_qs(parsed.query)
            if not self._authorized(query):
                self._send(403, "forbidden", "text/plain; charset=utf-8")
                return
            try:
                ledger, source_a, bound_a, source_b, bound_b = self._load_all()
                slots = sorted(bound_a["entries"])
                slot_index = max(0, min(int((query.get("slot") or ["1"])[-1]) - 1, len(slots) - 1))
                page = render_adjudication_page(
                    ledger, source_a, bound_a, source_b, bound_b, token, slots, slot_index
                )
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                self._send(409, "<h1>資料已失效，停止裁決</h1><p>" + html.escape(str(exc)) + "</p>")
                return
            self._send(200, page)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            if not self._authorized(form):
                self._send(403, "forbidden", "text/plain; charset=utf-8")
                return
            try:
                ledger, source_a, bound_a, source_b, bound_b = self._load_all()
                payload = _form_payload(form)
                ledger = save_adjudication_entry(
                    ledger_path, source_a, bound_a, source_b, bound_b, payload, private_root=private_root
                )
                slots = sorted(bound_a["entries"])
                slot_index = slots.index(payload["sampling_slot_id"])
                page = render_adjudication_page(
                    ledger, source_a, bound_a, source_b, bound_b, token, slots, slot_index
                )
                self._send(200, page)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                try:
                    ledger, source_a, bound_a, source_b, bound_b = self._load_all()
                    slots = sorted(bound_a["entries"])
                    slot_id = str((form.get("sampling_slot_id") or [""])[-1])
                    slot_index = slots.index(slot_id) if slot_id in slots else 0
                    page = render_adjudication_page(
                        ledger, source_a, bound_a, source_b, bound_b, token, slots, slot_index, str(exc)
                    )
                    self._send(400, page)
                except Exception:
                    self._send(409, "<h1>資料已失效，停止裁決</h1><p>" + html.escape(str(exc)) + "</p>")

    return Handler


def serve_adjudication(
    adjudicator_pseudonym: str,
    ledger_path: str | Path,
    source_v9_a_path: str | Path,
    boundary_a_path: str | Path,
    source_v9_b_path: str | Path,
    boundary_b_path: str | Path,
    port: int,
    *,
    authorization_lock: str | Path = v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
) -> None:
    authorized, reason = v9.human_use_authorized(authorization_lock)
    if not authorized:
        raise PermissionError(reason)
    path = resolve_private_path(ledger_path, private_root)
    source_a, source_b = load_json(source_v9_a_path), load_json(source_v9_b_path)
    bound_a, bound_b = load_json(boundary_a_path), load_json(boundary_b_path)
    if not path.exists():
        initialize_adjudication_ledger(
            adjudicator_pseudonym, path, source_a, bound_a, source_b, bound_b,
            authorization_lock=authorization_lock, private_root=private_root
        )
    ledger = load_json(path)
    if ledger.get("data_kind") != REAL_KIND:
        raise PermissionError("real server requires a real-human adjudication ledger")
    errors = validate_adjudication_ledger(ledger, source_a, bound_a, source_b, bound_b)
    if errors:
        raise ValueError("invalid adjudication ledger: " + "; ".join(errors))
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(
        ("127.0.0.1", port),
        make_adjudication_handler(path, private_root, token, source_v9_a_path, boundary_a_path, source_v9_b_path, boundary_b_path),
    )
    print(f"M55 private adjudication: http://127.0.0.1:{server.server_port}/?token={token}", flush=True)
    server.serve_forever()


def render_demo_dashboard() -> str:
    return """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M55 裁決流程示範</title><style>body{margin:0;background:#091020;color:#eef4ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1280px;margin:auto;padding:34px}.hero,.card{background:#121d33;border:1px solid #2c4166;border-radius:20px;padding:24px;margin-bottom:18px}.hero{background:linear-gradient(135deg,#17284b,#201932)}h1{font-size:34px;margin:.2em 0}.warning{color:#ffd284}.flow{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:14px}.research-flow{display:grid;grid-template-columns:repeat(7,minmax(105px,1fr));gap:8px}.node,.stage{background:#0a1428;border:1px solid #38547f;border-radius:16px;padding:18px;text-align:center}.stage{padding:14px 8px;min-height:92px}.stage b,.stage span{display:block}.stage span{margin-top:8px;font-size:13px}.stage.pass{border-color:#3aa88f}.stage.blocked{border-color:#a54f66}.arrow{font-size:28px;color:#6fe0cd}.choice{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.choice div{background:#0c1629;border-radius:14px;padding:16px;border:1px solid #344b72}.no{color:#ff9aa8;font-weight:800}.yes{color:#72e2cd;font-weight:800}@media(max-width:900px){.flow,.choice,.research-flow{grid-template-columns:1fr}.arrow{transform:rotate(90deg);text-align:center}}</style></head><body><main><section class="hero"><small>M55 engineering view</small><h1>兩個人的獨立觀察，不能由程式偷偷變成一個答案</h1><p class="warning">合成工具示範，不是真人結果；不顯示任何私人標註文字。</p></section><section class="card"><h2>整個研究證據鏈</h2><div class="research-flow"><div class="stage pass"><b>M54 方程式契約</b><span class="yes">PASS</span></div><div class="stage blocked"><b>V7 兩人分類可靠度</b><span class="no">0/18 + 0/18</span></div><div class="stage blocked"><b>V9 Uruha 事件</b><span class="no">0/30</span></div><div class="stage blocked"><b>X/cutoff/Y</b><span class="no">0/30</span></div><div class="stage pass"><b>裁決工具</b><span class="yes">工程 PASS</span></div><div class="stage blocked"><b>M55 真實資料</b><span class="no">0/30</span></div><div class="stage blocked"><b>M56 模型比較</b><span class="no">禁止</span></div></div></section><section class="card"><div class="flow"><div class="node"><b>Coder A + Coder B</b><br>兩份 V9 + X/cutoff/Y<br><span class="yes">來源各自保留</span></div><div class="arrow">→</div><div class="node"><b>逐筆真人裁決</b><br>接受 A／接受 B／手動決定<br><span class="no">沒有自動平均</span></div><div class="arrow">→</div><div class="node"><b>Temporal record pack</b><br>22 欄契約檢查<br><span class="yes">來源雜湊保留</span></div></div></section><section class="card"><h2>每一筆都只有三條合法路</h2><div class="choice"><div><b>接受 Coder A</b><p>完整複製 A 的事件、行為與切點；不混入 B。</p></div><div><b>接受 Coder B</b><p>完整複製 B 的事件、行為與切點；不混入 A。</p></div><div><b>手動裁決</b><p>人重新做出一個可說明的判斷，並留下理由與 attestations。</p></div></div></section><section class="card"><h2>目前真實進度</h2><p>V7 真人可靠度：<b>0/18 + 0/18</b>　→　V9：<b>0/30</b>　→　M55 真實 temporal rows：<b>0/30</b></p><p class="no">M55 未完成；M56 禁止。這個頁面只證明裁決工具與資料組裝規則可運作。</p></section></main></body></html>"""


def serve_demo(port: int) -> None:
    page = render_demo_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                body, content_type = b"ok", "text/plain; charset=utf-8"
            else:
                body, content_type = page, "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-contract")
    demo = subparsers.add_parser("serve-demo")
    demo.add_argument("--port", type=int, default=7905)
    init = subparsers.add_parser("init")
    serve = subparsers.add_parser("serve")
    export = subparsers.add_parser("export")
    for subparser in (init, serve, export):
        subparser.add_argument("--ledger", required=True)
        subparser.add_argument("--source-v9-a", required=True)
        subparser.add_argument("--boundary-a", required=True)
        subparser.add_argument("--source-v9-b", required=True)
        subparser.add_argument("--boundary-b", required=True)
        subparser.add_argument("--private-root", default=str(DEFAULT_PRIVATE_ROOT))
    for subparser in (init, serve):
        subparser.add_argument("--adjudicator", required=True)
        subparser.add_argument("--authorization-lock", default=str(v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK))
    init.add_argument("--overwrite", action="store_true")
    serve.add_argument("--port", type=int, default=7905)
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "validate-contract":
        print(json.dumps(validate_contract(), ensure_ascii=False, indent=2))
    elif args.command == "serve-demo":
        serve_demo(args.port)
    else:
        source_a = load_json(args.source_v9_a)
        bound_a = load_json(args.boundary_a)
        source_b = load_json(args.source_v9_b)
        bound_b = load_json(args.boundary_b)
        if args.command == "init":
            path, ledger = initialize_adjudication_ledger(
                args.adjudicator, args.ledger, source_a, bound_a, source_b, bound_b,
                authorization_lock=args.authorization_lock, private_root=args.private_root, overwrite=args.overwrite
            )
            print(json.dumps({"path": str(path), "entry_count": len(ledger["entries"]), "data_kind": ledger["data_kind"]}, ensure_ascii=False, indent=2))
        elif args.command == "serve":
            serve_adjudication(
                args.adjudicator, args.ledger, args.source_v9_a, args.boundary_a,
                args.source_v9_b, args.boundary_b, args.port,
                authorization_lock=args.authorization_lock, private_root=args.private_root
            )
        elif args.command == "export":
            path = resolve_private_path(args.ledger, args.private_root)
            ledger = load_json(path)
            pack = assemble_record_pack(ledger, source_a, bound_a, source_b, bound_b)
            output = resolve_private_path(args.output, args.private_root)
            _atomic_write_json(output, pack)
            print(json.dumps(build_export_report(ledger, source_a, bound_a, source_b, bound_b), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
