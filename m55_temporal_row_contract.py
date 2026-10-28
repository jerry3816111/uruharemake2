"""M55 cutoff-to-future row contract and fail-closed compiler.

The module does not read public media or private human ledgers by default.  It
can compile an explicitly supplied, independently reviewed private record pack
into the existing temporal-dataset shape, while keeping the current outcome on
the future side of a declared prediction boundary.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from typing import Any

from longitudinal_human_model.temporal import build_model_input, validate_temporal_dataset
import uruha_human_response_equation_m54 as m54


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m55_temporal_row_contract_v1.json"
SCHEMA = "uruha_m55_private_temporal_record_pack_v1"
SYNTHETIC_KIND = "synthetic_engineering_fixture"
REAL_KIND = "real_public_observation"
SYNTHETIC_REVIEW = "synthetic_engineering_only"
REAL_REVIEW_STATUSES = {
    "agreed_independent_codes",
    "adjudicated_after_retained_disagreement",
}
BOUNDARY_EXTENSION_FIELDS = (
    "observable_input_start_seconds",
    "prediction_cutoff_seconds",
    "observable_behavior_start_seconds",
    "observable_behavior_end_seconds",
)
FORBIDDEN_CONTENT_KEYS = {
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
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    return bool(path_text) and len(expected) == 64 and path.is_file() and file_sha256(path) == expected


def _find_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_CONTENT_KEYS:
                found.append(path)
            found.extend(_find_forbidden_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def validate_contract_m55(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m55_temporal_row_contract_v1":
        errors.append("invalid_schema")
    if contract.get("version") != "1.0.0":
        errors.append("invalid_version")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or not bindings:
        errors.append("bindings_missing")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding_invalid:{name}")
    record_pack = contract.get("record_pack") or {}
    if record_pack.get("schema") != SCHEMA:
        errors.append("record_pack_schema_mismatch")
    required_fields = record_pack.get("required_record_fields") or []
    if len(required_fields) != len(set(required_fields)):
        errors.append("duplicate_required_record_field")
    for field in BOUNDARY_EXTENSION_FIELDS:
        if field not in required_fields:
            errors.append(f"missing_boundary_field:{field}")
    temporal = contract.get("temporal_boundary") or {}
    if temporal.get("wall_clock_precision_claimed") is not False:
        errors.append("false_wall_clock_precision_claim")
    if temporal.get("whole_event_start_may_substitute_for_prediction_cutoff") is not False:
        errors.append("whole_event_cutoff_substitution_must_be_forbidden")
    if temporal.get("current_outcome_may_enter_model_input") is not False:
        errors.append("current_outcome_input_leak_must_be_forbidden")
    crosswalk = contract.get("equation_variable_crosswalk") or []
    variable_ids = [str(row.get("variable_id") or "") for row in crosswalk if isinstance(row, dict)]
    if tuple(variable_ids) != m54.EXPECTED_VARIABLE_IDS:
        errors.append("equation_variable_crosswalk_mismatch")
    if len(variable_ids) != len(set(variable_ids)):
        errors.append("duplicate_equation_variable")
    codebook = None
    if isinstance(bindings, dict) and _binding_valid(bindings.get("behavior_codebook")):
        codebook_path = Path(bindings["behavior_codebook"]["path"])
        if not codebook_path.is_absolute():
            codebook_path = ROOT / codebook_path
        codebook = load_json(codebook_path)
    taxonomy = contract.get("behavior_taxonomy") or {}
    if codebook is None or taxonomy.get("label_field") not in codebook:
        errors.append("behavior_taxonomy_binding_invalid")
    privacy = contract.get("privacy") or {}
    if privacy.get("formal_record_pack_git_tracked") is not False:
        errors.append("formal_record_pack_must_remain_private")
    if privacy.get("raw_or_verbatim_content_allowed") is not False:
        errors.append("raw_or_verbatim_content_must_be_forbidden")
    authorization = contract.get("authorization") or {}
    for field in (
        "synthetic_fixture_authorizes_human_reliability",
        "synthetic_fixture_authorizes_m56",
        "m55_compiler_alone_authorizes_m56",
    ):
        if authorization.get(field) is not False:
            errors.append(f"authorization_must_be_false:{field}")
    if authorization.get("separate_m56_protocol_required") is not True:
        errors.append("separate_m56_protocol_must_be_required")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "variable_count": len(crosswalk),
        "required_record_field_count": len(required_fields),
        "binding_count": len(bindings or {}),
    }


def audit_current_v9_boundary_gap(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    event_schema_binding = (contract.get("bindings") or {}).get("event_schema") or {}
    event_schema_path = Path(str(event_schema_binding.get("path") or ""))
    if not event_schema_path.is_absolute():
        event_schema_path = ROOT / event_schema_path
    event_schema = load_json(event_schema_path)
    current_fields = set((event_schema.get("record_contract") or {}).get("required_fields") or [])
    missing = [field for field in BOUNDARY_EXTENSION_FIELDS if field not in current_fields]
    return {
        "schema": "uruha_m55_current_v9_prediction_boundary_gap_audit",
        "current_v9_event_start_available": "timestamp_locator_start_seconds" in current_fields,
        "current_v9_event_end_available": "timestamp_locator_end_seconds" in current_fields,
        "required_boundary_extension_fields": list(BOUNDARY_EXTENSION_FIELDS),
        "missing_boundary_extension_fields": missing,
        "current_v9_alone_compilable": not missing,
        "boundary_extension_required_before_target_temporal_compilation": bool(missing),
        "unsafe_substitution_forbidden": "whole-event start/end cannot be relabeled as prediction/outcome boundaries",
    }


def _number(value: Any, field: str, errors: list[str], scope: str) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{scope}.{field}:finite_nonnegative_number_required")
        return None
    number = float(value)
    if number < 0 or number != number or number in (float("inf"), float("-inf")):
        errors.append(f"{scope}.{field}:finite_nonnegative_number_required")
        return None
    return number


def _text(value: Any, field: str, errors: list[str], scope: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{scope}.{field}:nonempty_text_required")
        return ""
    text = value.strip()
    if len(text) > maximum:
        errors.append(f"{scope}.{field}:too_long")
    return text


def _source_maps(contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bindings = contract["bindings"]
    paths = {}
    for name in ("target_source_metadata", "target_sampling_frame", "behavior_codebook"):
        path = Path(bindings[name]["path"])
        paths[name] = path if path.is_absolute() else ROOT / path
    sources = {row["source_id"]: row for row in load_json(paths["target_source_metadata"])["sources"]}
    slots = {row["sampling_slot_id"]: row for row in load_json(paths["target_sampling_frame"])["sampling_slots"]}
    codebook = load_json(paths["behavior_codebook"])
    return sources, slots, codebook


def validate_record_pack_m55(
    pack: dict[str, Any], contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_validation = validate_contract_m55(contract)
    errors = [f"contract:{error}" for error in contract_validation["errors"]]
    if not isinstance(pack, dict):
        return {"valid": False, "errors": errors + ["pack:object_required"]}
    if pack.get("schema") != SCHEMA:
        errors.append("pack.schema:mismatch")
    allowed_pack_fields = {
        "schema",
        "version",
        "data_kind",
        "status",
        "dataset_id",
        "target_id",
        "contract_hash",
        "records",
    }
    extra_pack_fields = set(pack) - allowed_pack_fields
    if extra_pack_fields:
        errors.append("pack:unexpected_fields:" + ",".join(sorted(extra_pack_fields)))
    if pack.get("version") != "1.0.0":
        errors.append("pack.version:mismatch")
    data_kind = str(pack.get("data_kind") or "")
    if data_kind not in (contract.get("record_pack") or {}).get("allowed_data_kinds", []):
        errors.append("pack.data_kind:not_allowed")
    if pack.get("contract_hash") != contract_validation["contract_hash"]:
        errors.append("pack.contract_hash:mismatch")
    if data_kind == REAL_KIND and pack.get("target_id") != contract.get("target_id"):
        errors.append("pack.target_id:mismatch")
    forbidden = _find_forbidden_keys(pack)
    errors.extend(f"forbidden_content_key:{path}" for path in forbidden)
    records = pack.get("records")
    if not isinstance(records, list) or not records:
        errors.append("pack.records:nonempty_array_required")
        records = []
    required_fields = set((contract.get("record_pack") or {}).get("required_record_fields") or [])
    sources, slots, codebook = _source_maps(contract)
    labels = set(codebook.get((contract.get("behavior_taxonomy") or {}).get("label_field")) or [])
    context_families = set(codebook.get("context_families") or [])
    audience_relations = set(codebook.get("audience_relations") or [])
    seen_ids: set[str] = set()
    seen_slots: set[str] = set()
    intervals_by_source: dict[str, list[tuple[float, float, str]]] = {}
    for index, record in enumerate(records):
        scope = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{scope}:object_required")
            continue
        missing = required_fields - set(record)
        if missing:
            errors.append(f"{scope}:missing_fields:{','.join(sorted(missing))}")
        extra = set(record) - required_fields
        if extra:
            errors.append(f"{scope}:unexpected_fields:{','.join(sorted(extra))}")
        sample_id = _text(record.get("sample_id"), "sample_id", errors, scope, maximum=128)
        slot_id = _text(record.get("sampling_slot_id"), "sampling_slot_id", errors, scope, maximum=160)
        source_id = _text(record.get("source_id"), "source_id", errors, scope, maximum=160)
        if sample_id in seen_ids:
            errors.append(f"{scope}.sample_id:duplicate")
        if slot_id in seen_slots:
            errors.append(f"{scope}.sampling_slot_id:duplicate")
        seen_ids.add(sample_id)
        seen_slots.add(slot_id)
        try:
            published_at = date.fromisoformat(str(record.get("source_published_at") or ""))
        except ValueError:
            published_at = None
            errors.append(f"{scope}.source_published_at:invalid_date")
        slot = None
        if data_kind == REAL_KIND:
            source = sources.get(source_id)
            slot = slots.get(slot_id)
            if source is None:
                errors.append(f"{scope}.source_id:not_authorized")
            elif published_at is not None and source.get("published_at") != published_at.isoformat():
                errors.append(f"{scope}.source_published_at:mismatch")
            if slot is None:
                errors.append(f"{scope}.sampling_slot_id:not_frozen")
            elif slot.get("source_id") != source_id:
                errors.append(f"{scope}.sampling_slot_id:source_mismatch")
        values = {
            field: _number(record.get(field), field, errors, scope)
            for field in (
                "event_start_seconds",
                "observable_input_start_seconds",
                "prediction_cutoff_seconds",
                "observable_behavior_start_seconds",
                "observable_behavior_end_seconds",
                "event_end_seconds",
            )
        }
        if all(value is not None for value in values.values()):
            if not (
                values["event_start_seconds"] <= values["observable_input_start_seconds"]
                < values["prediction_cutoff_seconds"]
                < values["observable_behavior_start_seconds"]
                < values["observable_behavior_end_seconds"]
                <= values["event_end_seconds"]
            ):
                errors.append(f"{scope}:prediction_boundary_order_invalid")
            if slot is not None:
                if values["event_start_seconds"] < float(slot["search_start_seconds"]):
                    errors.append(f"{scope}.event_start_seconds:before_frozen_search_start")
                if values["event_start_seconds"] >= float(slot["stratum_end_exclusive_seconds"]):
                    errors.append(f"{scope}.event_start_seconds:outside_frozen_stratum")
                if values["event_end_seconds"] > float(slot["source_duration_seconds"]):
                    errors.append(f"{scope}.event_end_seconds:after_source_end")
            intervals_by_source.setdefault(source_id, []).append(
                (values["event_start_seconds"], values["event_end_seconds"], sample_id)
            )
        _text(record.get("observable_input_paraphrase"), "observable_input_paraphrase", errors, scope)
        _text(record.get("completed_event_summary"), "completed_event_summary", errors, scope)
        label = str(record.get("behavior_label") or "")
        if label not in labels:
            errors.append(f"{scope}.behavior_label:not_allowed")
        acceptable = record.get("acceptable_behavior_labels")
        if not isinstance(acceptable, list) or not acceptable:
            errors.append(f"{scope}.acceptable_behavior_labels:nonempty_array_required")
        else:
            if len(acceptable) != len(set(acceptable)):
                errors.append(f"{scope}.acceptable_behavior_labels:duplicate")
            if label not in acceptable:
                errors.append(f"{scope}.acceptable_behavior_labels:must_include_actual")
            if not set(acceptable).issubset(labels):
                errors.append(f"{scope}.acceptable_behavior_labels:not_allowed")
        confidence = record.get("annotation_confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"{scope}.annotation_confidence:range")
        if record.get("context_family") not in context_families:
            errors.append(f"{scope}.context_family:not_allowed")
        if record.get("observable_audience_relation") not in audience_relations:
            errors.append(f"{scope}.observable_audience_relation:not_allowed")
        review_status = record.get("review_status")
        coder_count = record.get("independent_coder_count")
        if data_kind == SYNTHETIC_KIND:
            if review_status != SYNTHETIC_REVIEW or coder_count != 0:
                errors.append(f"{scope}:synthetic_must_not_impersonate_human_review")
        elif data_kind == REAL_KIND:
            if review_status not in REAL_REVIEW_STATUSES:
                errors.append(f"{scope}.review_status:independent_review_required")
            if isinstance(coder_count, bool) or not isinstance(coder_count, int) or coder_count < 2:
                errors.append(f"{scope}.independent_coder_count:at_least_two_required")
        for field in (
            "prediction_boundary_attestation",
            "outcome_excluded_from_input_attestation",
            "paraphrase_and_no_quote_attestation",
        ):
            if record.get(field) is not True:
                errors.append(f"{scope}.{field}:required")
    for source_id, intervals in intervals_by_source.items():
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            if current[0] < previous[1]:
                errors.append(
                    f"records:overlap:{source_id}:{previous[2]}:{current[2]}"
                )
    return {
        "valid": not errors,
        "errors": errors,
        "data_kind": data_kind,
        "record_count": len(records),
        "forbidden_content_key_count": len(forbidden),
        "contract_hash": contract_validation["contract_hash"],
    }


def _ordering_time(date_text: str, seconds: float) -> str:
    base = datetime.combine(date.fromisoformat(date_text), time.min, tzinfo=timezone.utc)
    return (base + timedelta(seconds=float(seconds))).isoformat()


def _precedes(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_date = date.fromisoformat(left["source_published_at"])
    right_date = date.fromisoformat(right["source_published_at"])
    if left_date < right_date:
        return True
    if left_date > right_date or left["source_id"] != right["source_id"]:
        return False
    return float(left["observable_behavior_end_seconds"]) <= float(right["prediction_cutoff_seconds"])


def _real_pack_authorized(readiness: dict[str, Any] | None) -> bool:
    if not isinstance(readiness, dict):
        return False
    gates = readiness.get("gates") or {}
    return (
        gates.get("equation_contract_valid") is True
        and gates.get("temporal_row_contract_valid") is True
        and gates.get("v7_reliability_passed") is True
        and gates.get("target_events_independently_coded") is True
        and gates.get("target_human_coder_count_is_two") is True
    )


def compile_temporal_dataset_m55(
    pack: dict[str, Any],
    *,
    readiness: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    validation = validate_record_pack_m55(pack, contract)
    if not validation["valid"]:
        raise ValueError("invalid M55 record pack: " + "; ".join(validation["errors"]))
    data_kind = validation["data_kind"]
    if data_kind == REAL_KIND and not _real_pack_authorized(readiness):
        raise PermissionError("M55 human reliability and target coding gates must pass before real-row compilation")
    _, _, codebook = _source_maps(contract)
    label_field = (contract.get("behavior_taxonomy") or {})["label_field"]
    labels = list(codebook[label_field])
    ordered = sorted(
        deepcopy(pack["records"]),
        key=lambda row: (
            row["source_published_at"],
            row["source_id"],
            float(row["prediction_cutoff_seconds"]),
            row["sample_id"],
        ),
    )
    history = []
    for record in ordered:
        history.append(
            {
                "history_id": f"m55-history::{record['sample_id']}",
                "event_time": _ordering_time(record["source_published_at"], record["observable_input_start_seconds"]),
                "available_at": _ordering_time(record["source_published_at"], record["observable_behavior_end_seconds"]),
                "source_id": record["source_id"],
                "observable_summary": record["completed_event_summary"],
                "behavior_label": record["behavior_label"],
                "evidence_type": "synthetic_engineering_only" if data_kind == SYNTHETIC_KIND else "independently_reviewed_public_observation",
            }
        )
    samples = []
    for record in ordered:
        prior_ids = [
            f"m55-history::{candidate['sample_id']}"
            for candidate in ordered
            if candidate["sample_id"] != record["sample_id"] and _precedes(candidate, record)
        ]
        samples.append(
            {
                "sample_id": record["sample_id"],
                "prediction_time": _ordering_time(record["source_published_at"], record["prediction_cutoff_seconds"]),
                "available_history_cutoff": _ordering_time(record["source_published_at"], record["prediction_cutoff_seconds"]),
                "event_context": record["observable_input_paraphrase"],
                "participants": [],
                "available_history_ids": prior_ids,
                "actual_observed_at": _ordering_time(record["source_published_at"], record["observable_behavior_start_seconds"]),
                "source_timestamp": _ordering_time(record["source_published_at"], record["observable_behavior_end_seconds"]),
                "source_id": record["source_id"],
                "actual_observed_behavior": record["behavior_label"],
                "acceptable_behavior_labels": list(record["acceptable_behavior_labels"]),
                "annotation_confidence": float(record["annotation_confidence"]),
            }
        )
    target_id = pack.get("target_id") or (
        contract["target_id"] if data_kind == REAL_KIND else "synthetic_m55_contract_subject"
    )
    dataset = {
        "schema": "ilhdt_temporal_dataset_v1",
        "dataset_id": str(pack.get("dataset_id") or "m55-temporal-contract-engineering"),
        "dataset_version": "1.0.0",
        "status": (
            "synthetic_engineering_m55_temporal_contract"
            if data_kind == SYNTHETIC_KIND
            else "real_public_observation_m55_pending_separate_m56_protocol"
        ),
        "authorizations": {
            "model_execution": False,
            "formal_target_claim": False,
        },
        "target": {
            "target_id": target_id,
            "display_name": "Synthetic M55 contract subject" if data_kind == SYNTHETIC_KIND else "Uruha public-observation case",
            "persona_summary": "Persona information is supplied only by a separately frozen comparison condition.",
        },
        "taxonomy": {
            "labels": labels,
            "origin": "frozen public-observable action codebook; not private-state labels",
        },
        "history": history,
        "samples": samples,
        "m55_contract_hash": validation["contract_hash"],
        "equation_variable_crosswalk": deepcopy(contract["equation_variable_crosswalk"]),
        "privacy": {
            "raw_or_verbatim_content": False,
            "current_outcome_in_model_input": False,
            "private_mental_fact": False,
        },
    }
    leakage_report = validate_temporal_dataset(dataset)
    leaked_current_outcomes = []
    for record, sample in zip(ordered, samples):
        model_view = build_model_input(dataset, sample)
        serialized = _canonical(model_view)
        if record["completed_event_summary"] in serialized:
            leaked_current_outcomes.append(record["sample_id"])
    if leaked_current_outcomes:
        raise ValueError("current outcome summary leaked into model input: " + ",".join(leaked_current_outcomes))
    audit = {
        "schema": "uruha_m55_temporal_compilation_audit_v1",
        "data_kind": data_kind,
        "record_count": len(ordered),
        "record_pack_hash": digest(pack),
        "contract_hash": validation["contract_hash"],
        "history_record_count": len(history),
        "prediction_sample_count": len(samples),
        "checked_history_references": leakage_report["checked_history_references"],
        "future_leakage_violations": leakage_report["future_leakage_violations"],
        "current_outcome_summary_leak_count": 0,
        "raw_or_verbatim_content_count": 0,
        "independent_human_reviewed_record_count": (
            len(ordered) if data_kind == REAL_KIND else 0
        ),
        "minimum_independent_coder_count": (
            min(int(row["independent_coder_count"]) for row in ordered)
            if data_kind == REAL_KIND
            else 0
        ),
        "real_human_evidence_created_by_compiler": False,
        "m56_authorized_by_compiler": False,
        "model_execution_authorized": False,
        "formal_target_claim": False,
        "coordinate_semantics": contract["temporal_boundary"]["coordinate"],
        "wall_clock_precision_claimed": False,
        "claim_boundary": "compiler and leakage-contract evidence only; no real-person validity or M56 result",
    }
    audit["audit_hash"] = digest(audit)
    dataset["dataset_hash"] = digest({key: value for key, value in dataset.items() if key != "dataset_hash"})
    return {"dataset": dataset, "audit": audit}


def render_temporal_contract_m55(
    *,
    contract: dict[str, Any] | None = None,
    human_row_count: int = 0,
) -> str:
    contract = deepcopy(contract or load_contract())
    validation = validate_contract_m55(contract)
    gap = audit_current_v9_boundary_gap(contract)
    crosswalk = contract.get("equation_variable_crosswalk") or []
    variable_cards = "".join(
        f"<li><b>{escape(row['variable_id'])}</b><span>{escape(row['status'])}</span></li>"
        for row in crosswalk
    )
    missing = "、".join(gap["missing_boundary_extension_fields"]) or "無"
    return (
        "<!doctype html><html lang='zh-Hant'><meta charset='utf-8'><title>M55 時間因果資料契約</title>"
        "<style>body{font-family:-apple-system,sans-serif;background:#07111f;color:#e8f3ff;margin:0;padding:32px}"
        "main{max-width:1180px;margin:auto}.flow{display:grid;grid-template-columns:1fr 140px 1fr;gap:14px;align-items:stretch}"
        ".node{border:1px solid #38bdf8;border-radius:18px;padding:20px;background:#102038}.lock{border-color:#f59e0b;text-align:center}"
        ".future{border-color:#fb7185}.tag{display:inline-block;border-radius:999px;background:#1e293b;padding:5px 9px;margin-top:8px}"
        "ul{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;list-style:none;padding:0}li{padding:10px;background:#111d31;border-radius:10px}"
        "li b,li span{display:block}li span{color:#9fb3c8;font-size:12px;margin-top:5px}.warning{margin-top:18px;padding:16px;border-left:5px solid #fb7185;background:#261827}"
        "</style><main><h1>M55 · 看得見的預測切點</h1><p>系統只能看左邊；右邊是之後才揭曉的可觀察行為。</p>"
        "<div class='flow'><div class='node'><h2>可觀察輸入 X</h2><p>只含角色反應開始前的情境改寫與已完成歷史。</p><span class='tag'>pre-cutoff only</span></div>"
        "<div class='node lock'><h2>🔒 cutoff</h2><p>先鎖輸入<br>再預測</p></div>"
        "<div class='node future'><h2>未見行為 Y</h2><p>行為開始後才可作為 outcome 解封；不能回填 X、state 或 memory。</p><span class='tag'>future outcome</span></div></div>"
        f"<div class='warning'><b>目前正式真人列：{int(human_row_count)}</b><br>契約：{'PASS' if validation['valid'] else 'FAIL'}；"
        f"現有 V9 單獨可編譯：{'是' if gap['current_v9_alone_compilable'] else '否'}。缺少：{escape(missing)}。M56 仍禁止。</div>"
        f"<h2>Equation V1 九個欄位怎麼處理</h2><ul>{variable_cards}</ul>"
        "<p>未知欄位保持 unknown；這張圖證明資料邊界可檢查，不證明已預測真人或解出人腦。</p></main></html>"
    )
