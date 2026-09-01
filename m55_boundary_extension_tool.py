#!/usr/bin/env python3
"""Private two-coder prediction-boundary companion tool for M55.

The collection server reads exactly one coder's V9 ledger and one separate M55
boundary ledger.  It never loads the other coder's ledger.  Real initialization
and serving remain gated by the frozen V7 reliability authorization.
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

import m55_temporal_row_contract as temporal_m55
import public_persona_target_calibration_coding_v9 as v9
from public_persona_contrast_coding_tool_v6 import (
    _atomic_write_json,
    resolve_private_path,
    temporal_iou,
    validate_coder_pseudonym,
)


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m55_boundary_extension_tool_v1.json"
DEFAULT_PRIVATE_ROOT = ROOT / "analysis/local_m55_boundary_extension_v1"
DEFAULT_V9_PRIVATE_ROOT = v9.DEFAULT_PRIVATE_ROOT
LEDGER_SCHEMA = "uruha_m55_private_boundary_extension_ledger_v1"
REAL_KIND = temporal_m55.REAL_KIND
SYNTHETIC_KIND = temporal_m55.SYNTHETIC_KIND
ENTRY_FIELDS = {
    "sampling_slot_id",
    "source_id",
    "coder_pseudonym",
    "source_v9_entry_hash",
    "event_start_seconds",
    "observable_input_start_seconds",
    "prediction_cutoff_seconds",
    "observable_behavior_start_seconds",
    "observable_behavior_end_seconds",
    "event_end_seconds",
    "observable_input_paraphrase",
    "completed_event_summary",
    "annotation_confidence",
    "prediction_boundary_attestation",
    "outcome_excluded_from_input_attestation",
    "paraphrase_and_no_quote_attestation",
    "updated_at",
}
LEDGER_FIELDS = {
    "schema",
    "version",
    "status",
    "data_kind",
    "coder_pseudonym",
    "contract_hash",
    "created_at",
    "updated_at",
    "entries",
    "data_boundary",
}
DATA_BOUNDARY = {
    "private_gitignored_storage_required": True,
    "other_coder_ledger_visible": False,
    "source_v9_entry_bound_by_hash": True,
    "whole_event_context_prefill_allowed": False,
    "model_output_visible": False,
    "raw_or_verbatim_content_allowed": False,
    "private_mental_fact_allowed": False,
    "automatic_cross_coder_merge_allowed": False,
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
    "other_coder_entry",
    "other_coder_ledger",
}


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


def _binding_valid(binding: Any) -> bool:
    if not isinstance(binding, dict):
        return False
    path_text = str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return bool(path_text) and len(expected) == 64 and path.is_file() and sha256_file(path) == expected


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


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m55_boundary_extension_tool_contract_v1":
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
    entry_contract = contract.get("individual_entry") or {}
    if entry_contract.get("schema") != LEDGER_SCHEMA:
        errors.append("individual_entry.schema")
    if set(entry_contract.get("required_fields") or []) != ENTRY_FIELDS:
        errors.append("individual_entry.required_fields")
    if entry_contract.get("whole_event_context_reuse_as_input_forbidden") is not True:
        errors.append("whole_event_context_reuse")
    comparison = contract.get("comparison") or {}
    for field in (
        "both_ledgers_complete_before_cross_coder_visibility",
        "distinct_coder_pseudonyms_required",
        "report_contains_only_hashes_counts_and_temporal_differences",
        "original_independent_entries_preserved",
        "explicit_human_adjudication_required_for_formal_record_pack",
    ):
        if comparison.get(field) is not True:
            errors.append(f"comparison:{field}")
    for field in (
        "report_contains_text_or_paraphrase",
        "automatic_average_or_merge_forbidden",
    ):
        expected = False if field == "report_contains_text_or_paraphrase" else True
        if comparison.get(field) is not expected:
            errors.append(f"comparison:{field}")
    authorization = contract.get("authorization") or {}
    for field in (
        "synthetic_demo_authorizes_human_reliability",
        "synthetic_demo_authorizes_target_coding",
        "synthetic_demo_authorizes_m55_completion",
        "tool_or_comparison_alone_authorizes_m56",
        "sealed_holdout_access",
        "model_execution",
        "production_memory_write",
    ):
        if authorization.get(field) is not False:
            errors.append(f"authorization:{field}")
    if authorization.get("real_initialization_requires_v7_reliability_pass") is not True:
        errors.append("authorization:real_initialization")
    if authorization.get("real_serving_requires_v7_reliability_pass") is not True:
        errors.append("authorization:real_serving")
    private_root = str((contract.get("private_storage") or {}).get("root") or "")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if private_root != "analysis/local_m55_boundary_extension_v1/" or private_root not in gitignore:
        errors.append("private_root_gitignore")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
        "required_entry_field_count": len(entry_contract.get("required_fields") or []),
    }


def _load_frame_and_codebook() -> tuple[dict[str, Any], dict[str, Any]]:
    return load_json(v9.DEFAULT_FRAME), load_json(v9.DEFAULT_CODEBOOK)


def _selected_v9_entries(source_v9_ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = source_v9_ledger.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        slot_id: entry
        for slot_id, entry in entries.items()
        if isinstance(entry, dict) and entry.get("slot_status") == "selected_event"
    }


def _validate_source_v9_ledger(
    source_v9_ledger: dict[str, Any],
    *,
    expected_coder: str | None = None,
) -> list[str]:
    frame, codebook = _load_frame_and_codebook()
    return v9.validate_target_ledger(
        source_v9_ledger,
        frame,
        codebook,
        expected_coder=expected_coder,
    )


def initialize_boundary_ledger(
    coder_pseudonym: str,
    ledger_path: str | Path,
    source_v9_ledger: dict[str, Any],
    *,
    authorization_lock: str | Path = v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
    data_kind: str = REAL_KIND,
    overwrite: bool = False,
) -> tuple[Path, dict[str, Any]]:
    coder = validate_coder_pseudonym(coder_pseudonym)
    if data_kind not in (REAL_KIND, SYNTHETIC_KIND):
        raise ValueError("unsupported data kind")
    if data_kind == REAL_KIND:
        authorized, reason = v9.human_use_authorized(authorization_lock)
        if not authorized:
            raise PermissionError(reason)
    source_errors = _validate_source_v9_ledger(source_v9_ledger, expected_coder=coder)
    if source_errors:
        raise ValueError("invalid source V9 ledger: " + "; ".join(source_errors))
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise ValueError("invalid M55 boundary contract: " + "; ".join(contract_report["errors"]))
    path = resolve_private_path(ledger_path, private_root)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}")
    now = utc_now()
    ledger = {
        "schema": LEDGER_SCHEMA,
        "version": "1.0.0",
        "status": "private_independent_boundary_extension_ledger",
        "data_kind": data_kind,
        "coder_pseudonym": coder,
        "contract_hash": contract_report["contract_hash"],
        "created_at": now,
        "updated_at": now,
        "entries": {},
        "data_boundary": deepcopy(DATA_BOUNDARY),
    }
    _atomic_write_json(path, ledger)
    return path, ledger


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
        and float(value) >= 0
    )


def _validate_text(value: Any, field: str, errors: list[str], maximum: int = 500) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}:nonempty_text_required")
        return
    if len(value.strip()) > maximum:
        errors.append(f"{field}:too_long")


def validate_boundary_entry(
    entry: dict[str, Any],
    source_v9_entry: dict[str, Any],
    coder_pseudonym: str,
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
    for field in ("sampling_slot_id", "source_id", "coder_pseudonym"):
        expected = (
            coder_pseudonym if field == "coder_pseudonym" else source_v9_entry.get(field)
        )
        if entry.get(field) != expected:
            errors.append(f"{field}:mismatch")
    if entry.get("source_v9_entry_hash") != digest(source_v9_entry):
        errors.append("source_v9_entry_hash:stale_or_mismatch")
    source_start = source_v9_entry.get("timestamp_locator_start_seconds")
    source_end = source_v9_entry.get("timestamp_locator_end_seconds")
    if entry.get("event_start_seconds") != source_start:
        errors.append("event_start_seconds:must_copy_v9")
    if entry.get("event_end_seconds") != source_end:
        errors.append("event_end_seconds:must_copy_v9")
    time_fields = (
        "event_start_seconds",
        "observable_input_start_seconds",
        "prediction_cutoff_seconds",
        "observable_behavior_start_seconds",
        "observable_behavior_end_seconds",
        "event_end_seconds",
    )
    values = {field: entry.get(field) for field in time_fields}
    for field, value in values.items():
        if not _is_number(value):
            errors.append(f"{field}:finite_nonnegative_number_required")
    if all(_is_number(value) for value in values.values()):
        if not (
            values["event_start_seconds"] <= values["observable_input_start_seconds"]
            < values["prediction_cutoff_seconds"]
            < values["observable_behavior_start_seconds"]
            < values["observable_behavior_end_seconds"]
            <= values["event_end_seconds"]
        ):
            errors.append("prediction_boundary_order_invalid")
    _validate_text(entry.get("observable_input_paraphrase"), "observable_input_paraphrase", errors)
    _validate_text(entry.get("completed_event_summary"), "completed_event_summary", errors)
    source_whole_context = str(source_v9_entry.get("observable_context_paraphrase") or "").strip()
    input_paraphrase = str(entry.get("observable_input_paraphrase") or "").strip()
    if source_whole_context and input_paraphrase == source_whole_context:
        errors.append("observable_input_paraphrase:whole_event_context_reuse_forbidden")
    confidence = entry.get("annotation_confidence")
    if not _is_number(confidence) or float(confidence) > 1:
        errors.append("annotation_confidence:range")
    for field in (
        "prediction_boundary_attestation",
        "outcome_excluded_from_input_attestation",
        "paraphrase_and_no_quote_attestation",
    ):
        if entry.get(field) is not True:
            errors.append(f"{field}:required")
    if not _valid_timestamp(entry.get("updated_at")):
        errors.append("updated_at:invalid")
    return errors


def validate_boundary_ledger(
    ledger: dict[str, Any],
    source_v9_ledger: dict[str, Any],
    *,
    expected_coder: str | None = None,
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
    if ledger.get("schema") != LEDGER_SCHEMA:
        errors.append("ledger_schema")
    if ledger.get("version") != "1.0.0":
        errors.append("ledger_version")
    if ledger.get("status") != "private_independent_boundary_extension_ledger":
        errors.append("ledger_status")
    if ledger.get("data_kind") not in (REAL_KIND, SYNTHETIC_KIND):
        errors.append("data_kind")
    try:
        coder = validate_coder_pseudonym(ledger.get("coder_pseudonym"))
    except ValueError:
        coder = ""
        errors.append("coder_pseudonym")
    if expected_coder is not None and coder != expected_coder:
        errors.append("expected_coder_mismatch")
    contract_report = validate_contract()
    if ledger.get("contract_hash") != contract_report["contract_hash"]:
        errors.append("contract_hash")
    if ledger.get("data_boundary") != DATA_BOUNDARY:
        errors.append("data_boundary")
    if not _valid_timestamp(ledger.get("created_at")) or not _valid_timestamp(ledger.get("updated_at")):
        errors.append("ledger_timestamp")
    errors.extend(f"forbidden_content_key:{path}" for path in _find_forbidden_keys(ledger))
    source_errors = _validate_source_v9_ledger(source_v9_ledger, expected_coder=coder or None)
    errors.extend(f"source_v9:{error}" for error in source_errors)
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return errors + ["entries:object_required"]
    selected = _selected_v9_entries(source_v9_ledger)
    if set(entries) - set(selected):
        errors.append("entries:unknown_or_nonselected_v9_slot")
    if require_complete and set(entries) != set(selected):
        errors.append("entries:incomplete")
    for slot_id, entry in entries.items():
        if slot_id in selected:
            errors.extend(
                f"{slot_id}:{error}"
                for error in validate_boundary_entry(entry, selected[slot_id], coder)
            )
    return errors


def _parse_number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def normalize_boundary_entry(
    payload: dict[str, Any],
    source_v9_entry: dict[str, Any],
    coder_pseudonym: str,
) -> dict[str, Any]:
    return {
        "sampling_slot_id": source_v9_entry["sampling_slot_id"],
        "source_id": source_v9_entry["source_id"],
        "coder_pseudonym": coder_pseudonym,
        "source_v9_entry_hash": digest(source_v9_entry),
        "event_start_seconds": source_v9_entry["timestamp_locator_start_seconds"],
        "observable_input_start_seconds": _parse_number(payload.get("observable_input_start_seconds")),
        "prediction_cutoff_seconds": _parse_number(payload.get("prediction_cutoff_seconds")),
        "observable_behavior_start_seconds": _parse_number(payload.get("observable_behavior_start_seconds")),
        "observable_behavior_end_seconds": _parse_number(payload.get("observable_behavior_end_seconds")),
        "event_end_seconds": source_v9_entry["timestamp_locator_end_seconds"],
        "observable_input_paraphrase": str(payload.get("observable_input_paraphrase") or "").strip(),
        "completed_event_summary": str(payload.get("completed_event_summary") or "").strip(),
        "annotation_confidence": _parse_number(payload.get("annotation_confidence")),
        "prediction_boundary_attestation": payload.get("prediction_boundary_attestation") is True,
        "outcome_excluded_from_input_attestation": payload.get("outcome_excluded_from_input_attestation") is True,
        "paraphrase_and_no_quote_attestation": payload.get("paraphrase_and_no_quote_attestation") is True,
        "updated_at": utc_now(),
    }


def save_boundary_entry(
    ledger_path: str | Path,
    source_v9_ledger: dict[str, Any],
    payload: dict[str, Any],
    *,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
) -> dict[str, Any]:
    path = resolve_private_path(ledger_path, private_root)
    ledger = load_json(path)
    existing_errors = validate_boundary_ledger(ledger, source_v9_ledger)
    if existing_errors:
        raise ValueError("invalid boundary ledger: " + "; ".join(existing_errors))
    selected = _selected_v9_entries(source_v9_ledger)
    slot_id = str(payload.get("sampling_slot_id") or "")
    if slot_id not in selected:
        raise ValueError("unknown or nonselected V9 slot")
    entry = normalize_boundary_entry(payload, selected[slot_id], ledger["coder_pseudonym"])
    entry_errors = validate_boundary_entry(entry, selected[slot_id], ledger["coder_pseudonym"])
    if entry_errors:
        raise ValueError("invalid boundary entry: " + "; ".join(entry_errors))
    candidate = deepcopy(ledger)
    candidate["entries"][slot_id] = entry
    candidate["updated_at"] = utc_now()
    candidate_errors = validate_boundary_ledger(candidate, source_v9_ledger)
    if candidate_errors:
        raise ValueError("invalid boundary ledger update: " + "; ".join(candidate_errors))
    _atomic_write_json(path, candidate)
    return candidate


def build_boundary_comparison(
    ledger_a: dict[str, Any],
    source_v9_a: dict[str, Any],
    ledger_b: dict[str, Any],
    source_v9_b: dict[str, Any],
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    errors_a = validate_boundary_ledger(
        ledger_a, source_v9_a, require_complete=require_complete
    )
    errors_b = validate_boundary_ledger(
        ledger_b, source_v9_b, require_complete=require_complete
    )
    if errors_a or errors_b:
        raise ValueError(
            "invalid independent ledgers: "
            + "; ".join([f"A:{error}" for error in errors_a] + [f"B:{error}" for error in errors_b])
        )
    if ledger_a["coder_pseudonym"] == ledger_b["coder_pseudonym"]:
        raise ValueError("two distinct coder pseudonyms are required")
    if ledger_a["data_kind"] != ledger_b["data_kind"]:
        raise ValueError("two boundary ledgers must use the same data kind")
    entries_a = ledger_a["entries"]
    entries_b = ledger_b["entries"]
    paired = sorted(set(entries_a) & set(entries_b))
    if require_complete and set(entries_a) != set(entries_b):
        raise ValueError("complete ledgers must cover the same selected slots")
    rows = []
    exact_count = 0
    for slot_id in paired:
        left = entries_a[slot_id]
        right = entries_b[slot_id]
        boundary_fields = (
            "observable_input_start_seconds",
            "prediction_cutoff_seconds",
            "observable_behavior_start_seconds",
            "observable_behavior_end_seconds",
        )
        exact = all(left[field] == right[field] for field in boundary_fields)
        exact_count += int(exact)
        rows.append(
            {
                "slot_digest": digest(slot_id)[:16],
                "exact_four_boundary_match": exact,
                "input_interval_iou": round(
                    temporal_iou(
                        left["observable_input_start_seconds"],
                        left["prediction_cutoff_seconds"],
                        right["observable_input_start_seconds"],
                        right["prediction_cutoff_seconds"],
                    ),
                    6,
                ),
                "behavior_interval_iou": round(
                    temporal_iou(
                        left["observable_behavior_start_seconds"],
                        left["observable_behavior_end_seconds"],
                        right["observable_behavior_start_seconds"],
                        right["observable_behavior_end_seconds"],
                    ),
                    6,
                ),
                "cutoff_absolute_difference_seconds": abs(
                    float(left["prediction_cutoff_seconds"])
                    - float(right["prediction_cutoff_seconds"])
                ),
                "input_paraphrase_digest_equal": digest(left["observable_input_paraphrase"])
                == digest(right["observable_input_paraphrase"]),
                "completed_summary_digest_equal": digest(left["completed_event_summary"])
                == digest(right["completed_event_summary"]),
                "human_adjudication_required": True,
            }
        )
    report = {
        "schema": "uruha_m55_boundary_extension_comparison_v1",
        "status": "comparison_only_pending_explicit_human_adjudication",
        "contract_hash": validate_contract()["contract_hash"],
        "coder_pseudonyms_distinct": True,
        "both_ledgers_complete_and_valid": require_complete,
        "paired_slot_count": len(paired),
        "exact_four_boundary_match_count": exact_count,
        "divergent_boundary_count": len(paired) - exact_count,
        "rows": rows,
        "contains_text_or_paraphrase": False,
        "contains_raw_or_verbatim_content": False,
        "automatic_average_or_merge_performed": False,
        "automatic_record_pack_authorized": False,
        "explicit_human_adjudication_required_count": len(paired),
        "m55_complete": False,
        "m56_authorized": False,
        "claim_boundary": "private two-coder boundary comparison only; no human adjudication, real-person prediction, Equation V1 validity, or M56 result",
    }
    report["report_hash"] = digest(report)
    return report


def _checked(value: bool) -> str:
    return " checked" if value else ""


def render_boundary_page(
    ledger: dict[str, Any],
    source_v9_ledger: dict[str, Any],
    token: str,
    slot_order: int,
    error: str = "",
) -> str:
    frame, _ = _load_frame_and_codebook()
    order = {row["sampling_slot_id"]: row["global_review_order"] for row in frame["sampling_slots"]}
    selected = _selected_v9_entries(source_v9_ledger)
    slots = sorted(selected, key=lambda slot_id: order.get(slot_id, 10**9))
    if not slots:
        return (
            "<!doctype html><html lang='zh-Hant'><meta charset='utf-8'><title>M55 Boundary Extension</title>"
            "<body><h1>M55 預測邊界標註</h1><p>你的 V9 帳本目前沒有可延伸的 selected event。"
            "請先獨立完成 V9；本頁不會載入另一位 coder 的答案。</p></body></html>"
        )
    slot_order = min(max(int(slot_order), 1), len(slots))
    slot_id = slots[slot_order - 1]
    source_entry = selected[slot_id]
    frame_slot = next(
        row for row in frame["sampling_slots"] if row["sampling_slot_id"] == slot_id
    )
    watch_slot = dict(frame_slot)
    watch_slot["search_start_seconds"] = source_entry["timestamp_locator_start_seconds"]
    official_watch_url = v9._official_watch_url(watch_slot)
    current = (ledger.get("entries") or {}).get(slot_id, {})
    message = f'<div class="error">{html.escape(error)}</div>' if error else ""
    event_start = source_entry["timestamp_locator_start_seconds"]
    event_end = source_entry["timestamp_locator_end_seconds"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M55 Boundary Extension</title><style>
:root{{--bg:#07111f;--card:#112038;--ink:#e8f3ff;--muted:#9fb3c8;--cyan:#38bdf8;--amber:#f59e0b;--pink:#fb7185;--green:#2dd4bf}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang TC",sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 18px 60px}}
.head,.flow,.times,.actions{{display:flex;gap:12px}}.head{{justify-content:space-between;align-items:end}}.flow{{margin:22px 0}}.node{{flex:1;background:var(--card);border:1px solid var(--cyan);border-radius:16px;padding:16px}}.lock{{border-color:var(--amber)}}.future{{border-color:var(--pink)}}
.card{{background:var(--card);padding:20px;border-radius:16px;margin-top:18px}}.times>label{{flex:1}}label{{display:block;margin:12px 0 6px;font-weight:700}}input,textarea{{width:100%;background:#07111f;color:var(--ink);border:1px solid #38506a;border-radius:8px;padding:10px}}textarea{{min-height:86px}}.check input{{width:auto}}.check{{font-weight:400;background:#182c42;padding:10px;border-radius:8px}}.actions{{justify-content:space-between;margin-top:18px}}a,button{{background:#1d4ed8;color:white;border:0;border-radius:8px;padding:11px 15px;text-decoration:none}}button{{background:#be123c}}.error{{background:#4c1728;padding:12px;border-left:4px solid var(--pink)}}small,.muted{{color:var(--muted)}}@media(max-width:760px){{.flow,.times,.head{{display:block}}}}
</style></head><body><main><div class="head"><div><h1>M55 · 預測邊界標註</h1><p class="muted">只讀你的 V9 entry；不載入另一位 coder。</p></div><div>Coder: {html.escape(ledger['coder_pseudonym'])}<br>Progress: {len(ledger.get('entries') or {{}})}/{len(slots)}<br>Entry: {slot_order}/{len(slots)}</div></div>
{message}<div class="flow"><div class="node"><b>可觀察輸入 X</b><p>重新改寫，只能寫 cutoff 前看得到的內容。</p></div><div class="node lock"><b>🔒 cutoff</b><p>先鎖資料，再預測。</p></div><div class="node future"><b>未見行為 Y</b><p>行為開始後才解封。</p></div></div>
<section class="card"><p>自己的 V9 事件範圍：<strong>{event_start}–{event_end} 秒</strong> · 自己的行為類別：<strong>{html.escape(str(source_entry.get('dialogue_act_or_action_label') or ''))}</strong></p>
<p><a target="_blank" rel="noreferrer" href="{html.escape(official_watch_url)}">在官方 YouTube 開啟自己的事件時間點</a></p>
<p class="muted">禁止把原本整段事件的情境改寫直接複製成輸入。這裡必須只描述 cutoff 以前。</p>
<form method="post" action="/save"><input type="hidden" name="token" value="{html.escape(token)}"><input type="hidden" name="sampling_slot_id" value="{html.escape(slot_id)}"><input type="hidden" name="slot_order" value="{slot_order}">
<div class="times"><label>輸入開始<input type="number" step="any" name="observable_input_start_seconds" value="{html.escape(str(current.get('observable_input_start_seconds',event_start)))}"></label><label>預測 cutoff<input type="number" step="any" name="prediction_cutoff_seconds" value="{html.escape(str(current.get('prediction_cutoff_seconds','')))}"></label><label>行為開始<input type="number" step="any" name="observable_behavior_start_seconds" value="{html.escape(str(current.get('observable_behavior_start_seconds','')))}"></label><label>行為結束<input type="number" step="any" name="observable_behavior_end_seconds" value="{html.escape(str(current.get('observable_behavior_end_seconds',event_end)))}"></label></div>
<label>cutoff 前可觀察輸入改寫</label><textarea maxlength="500" name="observable_input_paraphrase">{html.escape(str(current.get('observable_input_paraphrase','')))}</textarea>
<label>事件完成後的歷史摘要（只會在事件結束後對後續列可見）</label><textarea maxlength="500" name="completed_event_summary">{html.escape(str(current.get('completed_event_summary','')))}</textarea>
<label>標註信心 0–1<input type="number" min="0" max="1" step="0.01" name="annotation_confidence" value="{html.escape(str(current.get('annotation_confidence','')))}"></label>
<label class="check"><input type="checkbox" name="prediction_boundary_attestation" value="true"{_checked(current.get('prediction_boundary_attestation') is True)}> 我確認 cutoff 在目標行為開始以前。</label>
<label class="check"><input type="checkbox" name="outcome_excluded_from_input_attestation" value="true"{_checked(current.get('outcome_excluded_from_input_attestation') is True)}> 輸入改寫沒有包含 cutoff 後結果或暗示答案。</label>
<label class="check"><input type="checkbox" name="paraphrase_and_no_quote_attestation" value="true"{_checked(current.get('paraphrase_and_no_quote_attestation') is True)}> 我只寫研究者改寫，沒有原句、逐字稿或私人心理推測。</label>
<div class="actions"><a href="/?token={urllib.parse.quote(token)}&slot={max(1,slot_order-1)}">上一筆</a><button type="submit">儲存並前往下一筆</button><a href="/?token={urllib.parse.quote(token)}&slot={min(len(slots),slot_order+1)}">下一筆</a></div></form></section>
<p><small>資料只寫入本機 gitignored 私人帳本；不執行模型、不寫正式記憶、不解鎖 M56。</small></p></main></body></html>"""


def _form_payload(form: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "sampling_slot_id": form.get("sampling_slot_id", [""])[0],
        "observable_input_start_seconds": form.get("observable_input_start_seconds", [""])[0],
        "prediction_cutoff_seconds": form.get("prediction_cutoff_seconds", [""])[0],
        "observable_behavior_start_seconds": form.get("observable_behavior_start_seconds", [""])[0],
        "observable_behavior_end_seconds": form.get("observable_behavior_end_seconds", [""])[0],
        "observable_input_paraphrase": form.get("observable_input_paraphrase", [""])[0],
        "completed_event_summary": form.get("completed_event_summary", [""])[0],
        "annotation_confidence": form.get("annotation_confidence", [""])[0],
        "prediction_boundary_attestation": form.get("prediction_boundary_attestation", [""])[0] == "true",
        "outcome_excluded_from_input_attestation": form.get("outcome_excluded_from_input_attestation", [""])[0] == "true",
        "paraphrase_and_no_quote_attestation": form.get("paraphrase_and_no_quote_attestation", [""])[0] == "true",
    }


def make_boundary_handler(
    ledger_path: str | Path,
    private_root: str | Path,
    token: str,
    source_v9_ledger_path: str | Path,
):
    class BoundaryHandler(BaseHTTPRequestHandler):
        def _send(self, body: str, status: int = 200) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _redirect(self, location: str) -> None:
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/health":
                self._send("ok")
                return
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("token", [""])[0] != token:
                self._send("invalid session token", 403)
                return
            try:
                slot_order = int(query.get("slot", ["1"])[0])
            except ValueError:
                slot_order = 1
            ledger = load_json(resolve_private_path(ledger_path, private_root))
            source = load_json(source_v9_ledger_path)
            errors = validate_boundary_ledger(ledger, source)
            if errors:
                self._send(
                    "<!doctype html><html lang='zh-Hant'><meta charset='utf-8'>"
                    "<title>M55 Boundary Extension</title><body><h1>資料已失效</h1>"
                    "<p>來源 V9 entry 或私人 boundary ledger 已變更；請停止標註並重新驗證。</p>"
                    "</body></html>",
                    409,
                )
                return
            self._send(render_boundary_page(ledger, source, token, slot_order))

        def do_POST(self) -> None:
            if self.path != "/save":
                self._send("not found", 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 65536:
                self._send("invalid form size", 400)
                return
            form = urllib.parse.parse_qs(
                self.rfile.read(length).decode("utf-8"), keep_blank_values=True
            )
            if form.get("token", [""])[0] != token:
                self._send("invalid session token", 403)
                return
            try:
                slot_order = int(form.get("slot_order", ["1"])[0])
            except ValueError:
                slot_order = 1
            source = load_json(source_v9_ledger_path)
            try:
                ledger = save_boundary_entry(
                    ledger_path,
                    source,
                    _form_payload(form),
                    private_root=private_root,
                )
            except ValueError as error:
                ledger = load_json(resolve_private_path(ledger_path, private_root))
                self._send(render_boundary_page(ledger, source, token, slot_order, str(error)), 400)
                return
            selected_count = len(_selected_v9_entries(source))
            next_slot = min(selected_count, slot_order + 1)
            self._redirect(f"/?token={urllib.parse.quote(token)}&slot={next_slot}")

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return BoundaryHandler


def serve_boundary(
    coder_pseudonym: str,
    ledger_path: str | Path,
    source_v9_ledger_path: str | Path,
    port: int,
    *,
    authorization_lock: str | Path = v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK,
    private_root: str | Path = DEFAULT_PRIVATE_ROOT,
    v9_private_root: str | Path = DEFAULT_V9_PRIVATE_ROOT,
) -> None:
    authorized, reason = v9.human_use_authorized(authorization_lock)
    if not authorized:
        raise PermissionError(reason)
    source_path = resolve_private_path(source_v9_ledger_path, v9_private_root)
    source = load_json(source_path)
    path = resolve_private_path(ledger_path, private_root)
    if not path.exists():
        initialize_boundary_ledger(
            coder_pseudonym,
            ledger_path,
            source,
            authorization_lock=authorization_lock,
            private_root=private_root,
            data_kind=REAL_KIND,
        )
    ledger = load_json(path)
    if ledger.get("data_kind") != REAL_KIND:
        raise ValueError("real collection server requires a real-human boundary ledger")
    errors = validate_boundary_ledger(
        ledger,
        source,
        expected_coder=validate_coder_pseudonym(coder_pseudonym),
    )
    if errors:
        raise ValueError("invalid boundary ledger: " + "; ".join(errors))
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(
        ("127.0.0.1", int(port)),
        make_boundary_handler(path, private_root, token, source_path),
    )
    url = f"http://127.0.0.1:{server.server_port}/?token={urllib.parse.quote(token)}&slot=1"
    print(json.dumps({"url": url, "coder": coder_pseudonym}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def render_demo_dashboard() -> str:
    return """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M55 Two-Coder Boundary Lab</title><style>
body{margin:0;background:#07111f;color:#e8f3ff;font-family:-apple-system,"PingFang TC",sans-serif}main{max-width:1180px;margin:auto;padding:34px 20px}.banner{border:1px solid #fb7185;background:#2a1725;padding:15px;border-radius:14px}.lanes{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:22px 0}.lane{background:#102038;border:1px solid #38bdf8;border-radius:18px;padding:18px}.b{border-color:#a78bfa}.timeline{display:grid;grid-template-columns:1fr 80px 1fr;gap:8px;margin-top:20px}.x,.cut,.y{padding:16px;border-radius:12px;background:#18283e}.x{border:1px solid #38bdf8}.cut{border:1px solid #f59e0b;text-align:center}.y{border:1px solid #fb7185}.join{margin:26px 0;padding:18px;border-radius:18px;background:#13253a;border:1px solid #2dd4bf}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.metric{background:#0c1a2b;padding:14px;border-radius:12px}.gate{background:#351827;border-left:5px solid #fb7185;padding:16px;margin-top:22px}@media(max-width:780px){.lanes,.metrics{grid-template-columns:1fr}.timeline{grid-template-columns:1fr}}</style></head><body><main>
<h1>M55 · 兩位真人如何切出「預測以前」</h1><div class="banner"><b>合成工具示範，不是真人結果</b><br>目前 V7 仍未通過，Uruha boundary rows = 0，M56 禁止。</div>
<div class="lanes"><section class="lane"><h2>Coder A · 私人帳本</h2><p>只看自己的 V9 entry，另一人的答案不可見。</p><div class="timeline"><div class="x">X: 1–10s</div><div class="cut">🔒 10s</div><div class="y">Y: 12–18s</div></div></section><section class="lane b"><h2>Coder B · 私人帳本</h2><p>獨立重看同一凍結槽，不能複製 A。</p><div class="timeline"><div class="x">X: 2–11s</div><div class="cut">🔒 11s</div><div class="y">Y: 13–18s</div></div></section></div>
<section class="join"><h2>雙方都完成後才比較</h2><div class="metrics"><div class="metric"><b>輸入 IoU</b><br>0.80</div><div class="metric"><b>行為 IoU</b><br>0.83</div><div class="metric"><b>cutoff 差</b><br>1 秒</div><div class="metric"><b>自動合併</b><br>禁止</div></div><p>工具只顯示時間差與 digest，不顯示兩人的文字。即使四個時間完全一致，最後文字與標籤仍需明確真人裁決。</p></section>
<div class="gate"><b>證據閘門</b><br>V7 兩人可靠度 → V9 兩人獨立事件 → M55 兩人 boundary → 明確裁決 → 30 筆無洩漏 temporal rows。任何程式或合成資料都不能跳過這條線。</div>
<p>這證明的是工具可隔離、可比較、可保留分歧；不證明已預測真人、解出人腦或勝過一般 LLM。</p></main></body></html>"""


def serve_demo(port: int) -> None:
    page = render_demo_dashboard()

    class DemoHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                body, status, content_type = "ok", 200, "text/plain; charset=utf-8"
            elif self.path in ("/", "/dashboard"):
                body, status, content_type = page, 200, "text/html; charset=utf-8"
            else:
                body, status, content_type = "not found", 404, "text/plain; charset=utf-8"
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", int(port)), DemoHandler)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/dashboard"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--coder", required=True)
    init_parser.add_argument("--ledger", required=True)
    init_parser.add_argument("--source-v9-ledger", required=True)
    init_parser.add_argument("--authorization-lock", default=str(v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK))
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--coder", required=True)
    serve_parser.add_argument("--ledger", required=True)
    serve_parser.add_argument("--source-v9-ledger", required=True)
    serve_parser.add_argument("--authorization-lock", default=str(v9.DEFAULT_FUTURE_V7_RELIABILITY_LOCK))
    serve_parser.add_argument("--port", type=int, default=7904)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--ledger-a", required=True)
    compare_parser.add_argument("--source-v9-a", required=True)
    compare_parser.add_argument("--ledger-b", required=True)
    compare_parser.add_argument("--source-v9-b", required=True)
    compare_parser.add_argument("--output", required=True)
    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--serve", action="store_true")
    demo_parser.add_argument("--port", type=int, default=7904)
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(validate_contract(), ensure_ascii=False, indent=2))
        return
    if args.command == "init":
        source_path = resolve_private_path(args.source_v9_ledger, DEFAULT_V9_PRIVATE_ROOT)
        path, ledger = initialize_boundary_ledger(
            args.coder,
            args.ledger,
            load_json(source_path),
            authorization_lock=args.authorization_lock,
        )
        print(json.dumps({"ledger": str(path), "coder": ledger["coder_pseudonym"]}))
        return
    if args.command == "serve":
        serve_boundary(
            args.coder,
            args.ledger,
            args.source_v9_ledger,
            args.port,
            authorization_lock=args.authorization_lock,
        )
        return
    if args.command == "compare":
        ledger_a_path = resolve_private_path(args.ledger_a, DEFAULT_PRIVATE_ROOT)
        ledger_b_path = resolve_private_path(args.ledger_b, DEFAULT_PRIVATE_ROOT)
        v9_a_path = resolve_private_path(args.source_v9_a, DEFAULT_V9_PRIVATE_ROOT)
        v9_b_path = resolve_private_path(args.source_v9_b, DEFAULT_V9_PRIVATE_ROOT)
        report = build_boundary_comparison(
            load_json(ledger_a_path),
            load_json(v9_a_path),
            load_json(ledger_b_path),
            load_json(v9_b_path),
        )
        output = resolve_private_path(args.output, DEFAULT_PRIVATE_ROOT)
        if output.exists():
            raise FileExistsError(f"refusing to overwrite {output}")
        _atomic_write_json(output, report)
        print(json.dumps({"output": str(output), "m56_authorized": False}))
        return
    if args.command == "demo":
        if args.serve:
            serve_demo(args.port)
        else:
            print(render_demo_dashboard())


if __name__ == "__main__":
    main()
