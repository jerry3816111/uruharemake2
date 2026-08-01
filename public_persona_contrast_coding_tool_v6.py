#!/usr/bin/env python3
"""Local, isolated two-coder tool for the frozen V5 contrast event protocol."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import secrets
import tempfile
import urllib.parse
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_contrast_coding_tool_v6_preregistration.json"
)
DEFAULT_CODEBOOK = (
    ROOT / "configs/public_persona_contrast_coding_codebook_v6.json"
)
DEFAULT_V5_RESULT = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_result_lock.json"
)
DEFAULT_FRAME = (
    ROOT / "datasets/public_persona_contrast_event_sampling_frame_v5.json"
)
DEFAULT_EVENT_SCHEMA = ROOT / "configs/public_persona_event_coding_schema_v1.json"
DEFAULT_SOURCE_MANIFEST = (
    ROOT / "datasets/public_persona_contrast_source_manifest_v4.json"
)
DEFAULT_GITIGNORE = ROOT / ".gitignore"
DEFAULT_PRIVATE_ROOT = (
    ROOT / "analysis/local_public_persona_contrast_coding_v5"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/public_persona_contrast_coding_tool_v6_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/public_persona_contrast_coding_tool_v6_construction.md"
)

EXPERIMENT_ID = "public_persona_contrast_coding_tool_v6"
PASS_DECISION = (
    "authorize_local_two_coder_tool_use_for_v5_bounded_manual_coding_only"
)
FAIL_DECISION = "repair_local_coding_tool_before_any_contrast_behavior_review"
PRIVATE_ROOT_RELATIVE = "analysis/local_public_persona_contrast_coding_v5/"
CODER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
VIDEO_PARTITION_PATTERN = re.compile(r"^youtube_archive_([A-Za-z0-9_-]{6,32})$")
FORBIDDEN_ENTRY_KEYS = {
    "raw_text",
    "raw_media",
    "audio",
    "image",
    "caption",
    "captions",
    "comment",
    "comments",
    "transcript",
    "verbatim_transcript",
    "quote_text",
    "target_reply",
    "expected_reply",
    "reference_answer",
    "answer_key",
    "model_output",
    "training_text",
    "persona_score",
}
COMMON_ENTRY_FIELDS = {
    "sampling_slot_id",
    "source_id",
    "source_partition_key",
    "coder_pseudonym",
    "slot_status",
    "first_eligible_event_attestation",
    "updated_at",
}
SELECTED_ENTRY_FIELDS = COMMON_ENTRY_FIELDS | {
    "timestamp_locator_start_seconds",
    "timestamp_locator_end_seconds",
    "context_family",
    "observable_context_paraphrase",
    "observable_behavior_paraphrase",
    "primary_dimension",
    "secondary_dimensions",
    "dialogue_act_or_action_label",
    "observable_audience_relation",
    "evidence_strength",
    "ambiguity_notes",
    "alternative_interpretations",
    "paraphrase_and_no_quote_attestation",
}
EXPECTED_DEPENDENCIES = {
    "v5_result_lock": "configs/public_persona_contrast_event_coding_v5_result_lock.json",
    "sampling_frame": "datasets/public_persona_contrast_event_sampling_frame_v5.json",
    "shared_event_schema": "configs/public_persona_event_coding_schema_v1.json",
    "contrast_source_manifest": "datasets/public_persona_contrast_source_manifest_v4.json",
    "codebook": "configs/public_persona_contrast_coding_codebook_v6.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _display_path(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _binding(path):
    path = Path(path)
    return {"path": _display_path(path), "sha256": sha256_file(path)}


def _binding_valid(binding, root=ROOT):
    if not isinstance(binding, dict):
        return False
    path_text = str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    path = Path(path_text)
    if not path.is_absolute():
        path = Path(root) / path
    return (
        bool(path_text)
        and len(expected) == 64
        and path.is_file()
        and sha256_file(path) == expected
    )


def _is_nonnegative_integer(value):
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _is_positive_integer(value):
    return _is_nonnegative_integer(value) and value > 0


def validate_coder_pseudonym(value):
    value = str(value or "")
    if not CODER_PATTERN.fullmatch(value):
        raise ValueError("coder pseudonym must match [A-Za-z0-9_-]{3,32}")
    return value


def resolve_private_path(path, private_root=DEFAULT_PRIVATE_ROOT):
    private_root = Path(private_root).resolve()
    path = Path(path)
    if not path.is_absolute():
        path = private_root / path
    path = path.resolve()
    try:
        path.relative_to(private_root)
    except ValueError as error:
        raise ValueError("ledger path must resolve under the restricted private root") from error
    return path


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def frame_slots_by_id(frame):
    return {
        row["sampling_slot_id"]: row for row in frame.get("sampling_slots") or []
    }


def source_rows_by_id(source_manifest):
    return {row["source_id"]: row for row in source_manifest.get("sources") or []}


def build_official_watch_url(slot):
    match = VIDEO_PARTITION_PATTERN.fullmatch(str(slot["source_partition_key"]))
    if not match:
        raise ValueError("source partition is not a frozen YouTube archive locator")
    video_id = match.group(1)
    search_start = int(slot["search_start_seconds"])
    return f"https://www.youtube.com/watch?v={video_id}&t={search_start}s"


def initialize_ledger(
    coder_pseudonym,
    ledger_path,
    frame_path=DEFAULT_FRAME,
    codebook_path=DEFAULT_CODEBOOK,
    private_root=DEFAULT_PRIVATE_ROOT,
    overwrite=False,
):
    coder_pseudonym = validate_coder_pseudonym(coder_pseudonym)
    ledger_path = resolve_private_path(ledger_path, private_root)
    if ledger_path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {ledger_path}")
    payload = {
        "schema": "uruha_public_persona_contrast_independent_coder_ledger_v6",
        "experiment_id": EXPERIMENT_ID,
        "status": "private_independent_coding_ledger",
        "coder_pseudonym": coder_pseudonym,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "frame_binding": _binding(frame_path),
        "codebook_binding": _binding(codebook_path),
        "entries": {},
        "data_boundary": {
            "private_gitignored_storage_required": True,
            "other_coder_ledger_visible": False,
            "model_output_or_persona_score_visible": False,
            "raw_or_verbatim_content_allowed": False,
            "prompt_memory_retrieval_training_or_model_selection_use": False,
        },
    }
    _atomic_write_json(ledger_path, payload)
    return ledger_path, payload


def load_ledger(path, private_root=DEFAULT_PRIVATE_ROOT):
    path = resolve_private_path(path, private_root)
    return path, load_json(path)


def _validate_text(value, name, maximum, required):
    if not isinstance(value, str):
        return [f"{name}:must_be_string"]
    value = value.strip()
    errors = []
    if required and not value:
        errors.append(f"{name}:required")
    if len(value) > maximum:
        errors.append(f"{name}:too_long")
    return errors


def validate_entry(entry, slot, codebook, coder_pseudonym):
    errors = []
    status = entry.get("slot_status")
    expected_fields = (
        SELECTED_ENTRY_FIELDS if status == "selected_event" else COMMON_ENTRY_FIELDS
    )
    extra_fields = set(entry) - expected_fields
    missing_fields = expected_fields - set(entry)
    if extra_fields:
        errors.append("unexpected_fields:" + ",".join(sorted(extra_fields)))
    if missing_fields:
        errors.append("missing_fields:" + ",".join(sorted(missing_fields)))
    if set(entry) & FORBIDDEN_ENTRY_KEYS:
        errors.append("forbidden_payload_field")
    if entry.get("sampling_slot_id") != slot.get("sampling_slot_id"):
        errors.append("sampling_slot_id:mismatch")
    if entry.get("source_id") != slot.get("source_id"):
        errors.append("source_id:mismatch")
    if entry.get("source_partition_key") != slot.get("source_partition_key"):
        errors.append("source_partition_key:mismatch")
    if entry.get("coder_pseudonym") != coder_pseudonym:
        errors.append("coder_pseudonym:mismatch")
    if status not in set(codebook.get("terminal_slot_statuses") or []):
        errors.append("slot_status:not_allowed")
    if entry.get("first_eligible_event_attestation") is not True:
        errors.append("first_eligible_event_attestation:required")
    if not isinstance(entry.get("updated_at"), str) or not entry.get("updated_at"):
        errors.append("updated_at:required")
    if status != "selected_event":
        return errors

    if entry.get("paraphrase_and_no_quote_attestation") is not True:
        errors.append("paraphrase_and_no_quote_attestation:required")
    start = entry.get("timestamp_locator_start_seconds")
    end = entry.get("timestamp_locator_end_seconds")
    if not _is_nonnegative_integer(start):
        errors.append("timestamp_locator_start_seconds:nonnegative_integer_required")
    if not _is_positive_integer(end):
        errors.append("timestamp_locator_end_seconds:positive_integer_required")
    if _is_nonnegative_integer(start) and _is_positive_integer(end):
        if start < slot["search_start_seconds"]:
            errors.append("timestamp_locator_start_seconds:before_search_start")
        if start >= slot["stratum_end_exclusive_seconds"]:
            errors.append("timestamp_locator_start_seconds:outside_stratum")
        if end <= start:
            errors.append("timestamp_locator_end_seconds:not_after_start")
        if end > slot["source_duration_seconds"]:
            errors.append("timestamp_locator_end_seconds:after_source_end")

    text_contract = codebook.get("text_contract") or {}
    for field, maximum, required in (
        (
            "observable_context_paraphrase",
            text_contract.get("context_paraphrase_max_characters"),
            True,
        ),
        (
            "observable_behavior_paraphrase",
            text_contract.get("behavior_paraphrase_max_characters"),
            True,
        ),
        (
            "ambiguity_notes",
            text_contract.get("ambiguity_notes_max_characters"),
            False,
        ),
        (
            "alternative_interpretations",
            text_contract.get("alternative_interpretations_max_characters"),
            False,
        ),
    ):
        errors.extend(_validate_text(entry.get(field), field, maximum, required))

    allowed_fields = {
        "context_family": set(codebook.get("context_families") or []),
        "primary_dimension": set(codebook.get("dimensions") or []),
        "dialogue_act_or_action_label": set(
            codebook.get("dialogue_act_or_action_labels") or []
        ),
        "observable_audience_relation": set(
            codebook.get("audience_relations") or []
        ),
        "evidence_strength": set(codebook.get("evidence_strengths") or []),
    }
    for field, allowed in allowed_fields.items():
        if entry.get(field) not in allowed:
            errors.append(f"{field}:not_allowed")
    secondary = entry.get("secondary_dimensions")
    if not isinstance(secondary, list):
        errors.append("secondary_dimensions:list_required")
    else:
        if len(secondary) != len(set(secondary)):
            errors.append("secondary_dimensions:duplicate")
        if not set(secondary).issubset(set(codebook.get("dimensions") or [])):
            errors.append("secondary_dimensions:not_allowed")
        if entry.get("primary_dimension") in secondary:
            errors.append("secondary_dimensions:contains_primary")
    return errors


def validate_ledger(
    ledger,
    frame,
    codebook,
    expected_coder=None,
    require_complete=False,
):
    errors = []
    if ledger.get("schema") != (
        "uruha_public_persona_contrast_independent_coder_ledger_v6"
    ):
        errors.append("ledger_schema")
    if ledger.get("experiment_id") != EXPERIMENT_ID:
        errors.append("experiment_id")
    try:
        coder = validate_coder_pseudonym(ledger.get("coder_pseudonym"))
    except ValueError:
        coder = ""
        errors.append("coder_pseudonym")
    if expected_coder is not None and coder != expected_coder:
        errors.append("expected_coder_mismatch")
    if ledger.get("frame_binding") != _binding(DEFAULT_FRAME):
        errors.append("frame_binding")
    if ledger.get("codebook_binding") != _binding(DEFAULT_CODEBOOK):
        errors.append("codebook_binding")
    boundary = ledger.get("data_boundary") or {}
    expected_boundary = {
        "private_gitignored_storage_required": True,
        "other_coder_ledger_visible": False,
        "model_output_or_persona_score_visible": False,
        "raw_or_verbatim_content_allowed": False,
        "prompt_memory_retrieval_training_or_model_selection_use": False,
    }
    if boundary != expected_boundary:
        errors.append("data_boundary")
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return errors + ["entries:object_required"]
    slots = frame_slots_by_id(frame)
    unknown = set(entries) - set(slots)
    if unknown:
        errors.append("unknown_sampling_slots:" + ",".join(sorted(unknown)))
    if require_complete and set(entries) != set(slots):
        errors.append("ledger_incomplete")
    for slot_id, entry in entries.items():
        if slot_id not in slots or not isinstance(entry, dict):
            continue
        for error in validate_entry(entry, slots[slot_id], codebook, coder):
            errors.append(f"{slot_id}:{error}")
    selected_by_source = {}
    for slot_id, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("slot_status") != "selected_event":
            continue
        source_id = entry.get("source_id")
        interval = (
            entry.get("timestamp_locator_start_seconds"),
            entry.get("timestamp_locator_end_seconds"),
            slot_id,
        )
        selected_by_source.setdefault(source_id, []).append(interval)
    for source_id, intervals in selected_by_source.items():
        valid = [
            row
            for row in intervals
            if _is_nonnegative_integer(row[0]) and _is_positive_integer(row[1])
        ]
        valid.sort()
        for previous, current in zip(valid, valid[1:]):
            if current[0] < previous[1]:
                errors.append(
                    f"overlap:{source_id}:{previous[2]}:{current[2]}"
                )
    return errors


def normalize_entry(payload, slot, codebook, coder_pseudonym):
    status = str(payload.get("slot_status") or "")
    entry = {
        "sampling_slot_id": slot["sampling_slot_id"],
        "source_id": slot["source_id"],
        "source_partition_key": slot["source_partition_key"],
        "coder_pseudonym": coder_pseudonym,
        "slot_status": status,
        "first_eligible_event_attestation": (
            payload.get("first_eligible_event_attestation") is True
        ),
        "updated_at": utc_now(),
    }
    if status == "selected_event":
        entry.update(
            {
                "timestamp_locator_start_seconds": payload.get(
                    "timestamp_locator_start_seconds"
                ),
                "timestamp_locator_end_seconds": payload.get(
                    "timestamp_locator_end_seconds"
                ),
                "context_family": str(payload.get("context_family") or ""),
                "observable_context_paraphrase": str(
                    payload.get("observable_context_paraphrase") or ""
                ).strip(),
                "observable_behavior_paraphrase": str(
                    payload.get("observable_behavior_paraphrase") or ""
                ).strip(),
                "primary_dimension": str(payload.get("primary_dimension") or ""),
                "secondary_dimensions": list(
                    payload.get("secondary_dimensions") or []
                ),
                "dialogue_act_or_action_label": str(
                    payload.get("dialogue_act_or_action_label") or ""
                ),
                "observable_audience_relation": str(
                    payload.get("observable_audience_relation") or ""
                ),
                "evidence_strength": str(payload.get("evidence_strength") or ""),
                "ambiguity_notes": str(payload.get("ambiguity_notes") or "").strip(),
                "alternative_interpretations": str(
                    payload.get("alternative_interpretations") or ""
                ).strip(),
                "paraphrase_and_no_quote_attestation": (
                    payload.get("paraphrase_and_no_quote_attestation") is True
                ),
            }
        )
    return entry


def save_entry(
    ledger_path,
    payload,
    frame=None,
    codebook=None,
    private_root=DEFAULT_PRIVATE_ROOT,
):
    frame = frame or load_json(DEFAULT_FRAME)
    codebook = codebook or load_json(DEFAULT_CODEBOOK)
    ledger_path, ledger = load_ledger(ledger_path, private_root)
    existing_errors = validate_ledger(ledger, frame, codebook)
    if existing_errors:
        raise ValueError("invalid ledger: " + "; ".join(existing_errors))
    slots = frame_slots_by_id(frame)
    slot_id = str(payload.get("sampling_slot_id") or "")
    if slot_id not in slots:
        raise ValueError("unknown sampling slot")
    entry = normalize_entry(payload, slots[slot_id], codebook, ledger["coder_pseudonym"])
    entry_errors = validate_entry(
        entry, slots[slot_id], codebook, ledger["coder_pseudonym"]
    )
    if entry_errors:
        raise ValueError("invalid entry: " + "; ".join(entry_errors))
    candidate = json.loads(json.dumps(ledger))
    candidate["entries"][slot_id] = entry
    candidate["updated_at"] = utc_now()
    candidate_errors = validate_ledger(candidate, frame, codebook)
    if candidate_errors:
        raise ValueError("invalid ledger update: " + "; ".join(candidate_errors))
    _atomic_write_json(ledger_path, candidate)
    return candidate


def temporal_iou(start_a, end_a, start_b, end_b):
    intersection = max(0, min(end_a, end_b) - max(start_a, start_b))
    union = max(end_a, end_b) - min(start_a, start_b)
    return intersection / union if union > 0 else None


def nominal_krippendorff_alpha(pairs):
    comparable = [(a, b) for a, b in pairs if a is not None and b is not None]
    if len(comparable) < 2:
        return None
    observed_disagreement = sum(a != b for a, b in comparable) / len(comparable)
    counts = Counter(value for pair in comparable for value in pair)
    total = sum(counts.values())
    if total < 2:
        return None
    expected_agreement = sum(
        count * (count - 1) for count in counts.values()
    ) / (total * (total - 1))
    expected_disagreement = 1.0 - expected_agreement
    if math.isclose(expected_disagreement, 0.0):
        return None
    return 1.0 - (observed_disagreement / expected_disagreement)


def _mean(values):
    return sum(values) / len(values) if values else None


def _round_optional(value):
    return None if value is None else round(value, 6)


def build_reliability_report(ledger_a, ledger_b, frame, codebook):
    errors_a = validate_ledger(ledger_a, frame, codebook, require_complete=True)
    errors_b = validate_ledger(ledger_b, frame, codebook, require_complete=True)
    distinct = ledger_a.get("coder_pseudonym") != ledger_b.get("coder_pseudonym")
    slots = frame_slots_by_id(frame)
    entries_a = ledger_a.get("entries")
    entries_b = ledger_b.get("entries")
    entries_a = entries_a if isinstance(entries_a, dict) else {}
    entries_b = entries_b if isinstance(entries_b, dict) else {}
    complete_a = len(entries_a) / len(slots) if slots else 0.0
    complete_b = len(entries_b) / len(slots) if slots else 0.0
    paired_slot_ids = sorted(set(entries_a) & set(entries_b))
    status_pairs = [
        (entries_a[slot_id].get("slot_status"), entries_b[slot_id].get("slot_status"))
        for slot_id in paired_slot_ids
    ]
    status_agreement = _mean([a == b for a, b in status_pairs])
    jointly_selected = [
        slot_id
        for slot_id in paired_slot_ids
        if entries_a[slot_id].get("slot_status") == "selected_event"
        and entries_b[slot_id].get("slot_status") == "selected_event"
    ]
    ious = []
    for slot_id in jointly_selected:
        values = (
            entries_a[slot_id].get("timestamp_locator_start_seconds"),
            entries_a[slot_id].get("timestamp_locator_end_seconds"),
            entries_b[slot_id].get("timestamp_locator_start_seconds"),
            entries_b[slot_id].get("timestamp_locator_end_seconds"),
        )
        if all(_is_nonnegative_integer(value) for value in values):
            ious.append(temporal_iou(*values))
    ious = [value for value in ious if value is not None]
    reliability = codebook["reliability_contract"]
    nominal_fields = reliability["nominal_krippendorff_alpha_fields"]
    nominal_alpha = {}
    for field in nominal_fields:
        pairs = [
            (entries_a[slot_id].get(field), entries_b[slot_id].get(field))
            for slot_id in jointly_selected
        ]
        nominal_alpha[field] = _round_optional(nominal_krippendorff_alpha(pairs))
    secondary_alpha = {}
    for dimension in codebook["dimensions"]:
        pairs = [
            (
                dimension in entries_a[slot_id].get("secondary_dimensions", []),
                dimension in entries_b[slot_id].get("secondary_dimensions", []),
            )
            for slot_id in jointly_selected
        ]
        secondary_alpha[dimension] = _round_optional(
            nominal_krippendorff_alpha(pairs)
        )
    tentative = reliability["nominal_alpha_tentative_min"]
    required_alpha_values = list(nominal_alpha.values())
    alpha_gate = bool(required_alpha_values) and all(
        value is not None and value >= tentative for value in required_alpha_values
    )
    mean_iou = _mean(ious)
    iou_gate = mean_iou is not None and mean_iou >= reliability[
        "temporal_iou_project_gate_min"
    ]
    complete_gate = (
        math.isclose(complete_a, 1.0)
        and math.isclose(complete_b, 1.0)
        and not errors_a
        and not errors_b
    )
    reliability_passed = complete_gate and distinct and iou_gate and alpha_gate
    return {
        "schema": "uruha_public_persona_contrast_coding_reliability_v6",
        "experiment_id": EXPERIMENT_ID,
        "contains_event_text": False,
        "contains_model_output": False,
        "persona_score_computed": False,
        "coder_identity": {
            "pseudonyms_distinct": distinct,
            "coder_a_pseudonym_sha256": hashlib.sha256(
                str(ledger_a.get("coder_pseudonym") or "").encode("utf-8")
            ).hexdigest(),
            "coder_b_pseudonym_sha256": hashlib.sha256(
                str(ledger_b.get("coder_pseudonym") or "").encode("utf-8")
            ).hexdigest(),
        },
        "completion": {
            "expected_slot_count_per_coder": len(slots),
            "coder_a_entry_count": len(entries_a),
            "coder_b_entry_count": len(entries_b),
            "coder_a_fraction": round(complete_a, 6),
            "coder_b_fraction": round(complete_b, 6),
            "paired_slot_count": len(paired_slot_ids),
            "jointly_selected_event_count": len(jointly_selected),
        },
        "unitizing_reliability": {
            "slot_status_percent_agreement": _round_optional(status_agreement),
            "joint_selected_temporal_iou_mean": _round_optional(mean_iou),
            "joint_selected_temporal_iou_count": len(ious),
        },
        "nominal_reliability": {
            "krippendorff_alpha": nominal_alpha,
            "secondary_dimension_binary_krippendorff_alpha": secondary_alpha,
        },
        "gates": {
            "both_ledgers_complete_and_valid": complete_gate,
            "coder_pseudonyms_distinct": distinct,
            "temporal_iou_gate_passed": iou_gate,
            "all_primary_nominal_alpha_at_least_tentative": alpha_gate,
            "reliability_passed": reliability_passed,
            "aggregate_behavior_profile_authorized": reliability_passed,
            "persona_similarity_comparison_authorized": False,
            "model_execution_authorized": False,
        },
        "validation": {
            "coder_a_error_count": len(errors_a),
            "coder_b_error_count": len(errors_b),
            "coder_a_errors": errors_a,
            "coder_b_errors": errors_b,
        },
        "evidence_boundary": (
            "Reliability pass would authorize only a contrast aggregate behavior profile. "
            "It is not a persona-similarity score and does not authorize model execution, "
            "target holdout review, training, or a public-persona fidelity claim."
        ),
    }


def build_construction_audit(
    preregistration,
    codebook,
    v5_result,
    frame,
    event_schema,
    source_manifest,
    gitignore_text,
):
    violations = []
    if preregistration.get("schema") != (
        "uruha_public_persona_contrast_coding_tool_preregistration_v6"
    ):
        violations.append("preregistration_schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations.append("experiment_id")
    for name, expected_path in EXPECTED_DEPENDENCIES.items():
        binding = (preregistration.get("depends_on") or {}).get(name)
        if not _binding_valid(binding):
            violations.append(f"dependency:{name}:hash")
        if (binding or {}).get("path") != expected_path:
            violations.append(f"dependency:{name}:path")
    if v5_result.get("decision") != (
        "authorize_bounded_manual_contrast_event_coding_only"
    ):
        violations.append("v5_decision")
    if codebook.get("status") != "frozen_before_contrast_behavior_review":
        violations.append("codebook_status")
    if codebook.get("category_origin") != (
        "project_specific_observation_codebook_not_official_personality_labels_or_target_answers"
    ):
        violations.append("codebook:category_origin")
    if codebook.get("categories_define_target_answers") is not False:
        violations.append("codebook:target_answers")
    dimensions = (event_schema.get("construct") or {}).get("dimensions") or []
    if codebook.get("dimensions") != dimensions or len(dimensions) != 6:
        violations.append("shared_dimensions")
    expected_statuses = {"selected_event", "no_eligible_event", "overlap_blocked"}
    if set(codebook.get("terminal_slot_statuses") or []) != expected_statuses:
        violations.append("terminal_statuses")
    for field in (
        "context_families",
        "dialogue_act_or_action_labels",
        "audience_relations",
        "evidence_strengths",
    ):
        values = codebook.get(field)
        if not isinstance(values, list) or len(values) < 3 or len(values) != len(set(values)):
            violations.append(f"codebook:{field}")
    labels = codebook.get("display_labels_zh_hant") or {}
    labeled_values = set(codebook.get("dimensions") or [])
    for field in (
        "terminal_slot_statuses",
        "context_families",
        "dialogue_act_or_action_labels",
        "audience_relations",
        "evidence_strengths",
    ):
        labeled_values.update(codebook.get(field) or [])
    if set(labels) != labeled_values or any(not str(value).strip() for value in labels.values()):
        violations.append("codebook:display_labels")
    text_contract = codebook.get("text_contract") or {}
    for field in (
        "researcher_paraphrase_only",
        "first_eligible_event_attestation_required",
        "paraphrase_and_no_quote_attestation_required",
    ):
        if text_contract.get(field) is not True:
            violations.append(f"text_contract:{field}")
    for field in ("copied_quote_allowed", "private_motive_inference_allowed"):
        if text_contract.get(field) is not False:
            violations.append(f"text_contract:{field}")
    reliability = codebook.get("reliability_contract") or {}
    if reliability.get("nominal_alpha_reliable_min") != 0.8:
        violations.append("reliability:alpha_reliable")
    if reliability.get("nominal_alpha_tentative_min") != 0.667:
        violations.append("reliability:alpha_tentative")
    if reliability.get("temporal_iou_project_gate_min") != 0.5:
        violations.append("reliability:iou_gate")
    slots = frame.get("sampling_slots") or []
    if len(slots) != 90 or len({row.get("source_id") for row in slots}) != 9:
        violations.append("sampling_frame")
    if len(source_manifest.get("sources") or []) != 9:
        violations.append("source_manifest")
    if PRIVATE_ROOT_RELATIVE not in gitignore_text.splitlines():
        violations.append("private_root_not_gitignored")
    ledger = preregistration.get("ledger_contract") or {}
    if ledger.get("private_root") != PRIVATE_ROOT_RELATIVE:
        violations.append("private_root")
    for field in (
        "one_coder_pseudonym_per_ledger",
        "coder_pseudonyms_must_be_distinct_for_comparison",
        "one_entry_per_sampling_slot",
        "ledger_paths_must_resolve_under_private_root",
        "atomic_write_required",
    ):
        if ledger.get(field) is not True:
            violations.append(f"ledger:{field}")
    for field in (
        "other_coder_ledger_visible_during_entry",
        "model_output_or_persona_score_visible_during_entry",
        "raw_media_caption_comment_transcript_or_quote_storage",
        "prompt_memory_retrieval_training_or_model_selection_use",
    ):
        if ledger.get(field) is not False:
            violations.append(f"ledger:{field}")
    ui = preregistration.get("ui_contract") or {}
    expected_ui = {
        "bind_host_exact": "127.0.0.1",
        "random_session_token_required": True,
        "external_javascript_or_analytics_allowed": False,
        "source_access_mode": "manual_official_youtube_watch_link_only",
        "video_embedding_or_download": False,
        "first_eligible_event_attestation_required": True,
        "paraphrase_and_no_quote_attestation_required": True,
        "cross_coder_comparison_visible_before_both_ledgers_complete": False,
    }
    if ui != expected_ui:
        violations.append("ui_contract")
    preregistered_reliability = preregistration.get("reliability_contract") or {}
    expected_reliability = {
        "slot_status_agreement_reported": True,
        "joint_selected_temporal_iou_reported": True,
        "nominal_krippendorff_alpha_reported": True,
        "secondary_dimension_binary_alpha_reported": True,
        "independent_review_fraction_required": 1.0,
        "temporal_iou_project_gate_min": 0.5,
        "nominal_alpha_reliable_min": 0.8,
        "nominal_alpha_tentative_min": 0.667,
        "below_tentative_alpha_blocks_aggregate_profile": True,
        "adjudication_does_not_replace_original_independent_records": True,
        "reliability_pass_does_not_authorize_persona_similarity_claim": True,
    }
    if preregistered_reliability != expected_reliability:
        violations.append("preregistered_reliability_contract")
    policy = preregistration.get("decision_policy") or {}
    if policy.get("construction_pass") != PASS_DECISION:
        violations.append("decision_pass")
    if policy.get("construction_fail") != FAIL_DECISION:
        violations.append("decision_fail")
    if policy.get("maximum_coder_count") != 2:
        violations.append("decision:maximum_coder_count")
    if policy.get("maximum_sampling_slot_count_per_coder") != 90:
        violations.append("decision:maximum_sampling_slot_count_per_coder")
    if policy.get("restricted_local_ledger_creation") is not True:
        violations.append("decision:restricted_local_ledger_creation")
    for field in (
        "model_execution",
        "runtime_change",
        "prompt_change",
        "memory_change",
        "model_training",
        "target_calibration_behavior_coding",
        "sealed_holdout_unsealing",
        "rater_recruitment",
        "formal_persona_scoring",
        "public_persona_fidelity_claim",
        "private_person_copy_claim",
    ):
        if policy.get(field) is not False:
            violations.append(f"decision:{field}")
    expected_counts = {
        "private_ledger_count": 0,
        "content_reviewed_source_count": 0,
        "selected_event_count": 0,
        "coded_event_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
        "model_call_count": 0,
    }
    if preregistration.get("expected_counts_after_construction") != expected_counts:
        violations.append("construction_counts")
    checks = {
        "v5_authorization_and_all_dependencies_are_hash_bound": not any(
            value.startswith(("dependency:", "v5_")) for value in violations
        ),
        "six_shared_public_observable_dimensions_are_preserved": (
            "shared_dimensions" not in violations
        ),
        "closed_codebook_and_terminal_slot_statuses_are_frozen": not any(
            value.startswith(("codebook:", "terminal_statuses", "codebook_status"))
            for value in violations
        ),
        "paraphrase_attestations_and_no_private_inference_are_required": not any(
            value.startswith("text_contract:") for value in violations
        ),
        "ninety_slots_and_nine_sources_remain_frozen": not any(
            value in {"sampling_frame", "source_manifest"} for value in violations
        ),
        "private_atomic_single_coder_ledgers_are_required": not any(
            value.startswith(("private_root", "ledger:")) for value in violations
        ),
        "localhost_tokenized_no_download_ui_is_required": (
            "ui_contract" not in violations
        ),
        "unitizing_iou_and_chance_corrected_reliability_are_frozen": not any(
            value.startswith(("reliability:", "preregistered_reliability"))
            for value in violations
        ),
        "model_runtime_training_holdout_rating_and_claims_remain_forbidden": not any(
            value.startswith("decision:") for value in violations
        ),
        "all_construction_data_counts_remain_zero": (
            "construction_counts" not in violations
        ),
    }
    passed = all(checks.values()) and not violations
    return {
        "schema": "uruha_public_persona_contrast_coding_tool_construction_v6",
        "experiment_id": EXPERIMENT_ID,
        "construction_passed": passed,
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "summary": {
            "check_count": len(checks),
            "check_pass_count": sum(checks.values()),
            "sampling_slot_count": len(slots),
            "source_count": len(source_manifest.get("sources") or []),
            "dimension_count": len(codebook.get("dimensions") or []),
            "private_ledger_count": 0,
            "content_reviewed_source_count": 0,
            "selected_event_count": 0,
            "coded_event_count": 0,
            "model_output_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "model_call_count": 0,
        },
        "checks": checks,
        "violations": violations,
        "authorizations": {
            "restricted_local_two_coder_tool_use": passed,
            "maximum_coder_count": 2 if passed else 0,
            "maximum_sampling_slot_count_per_coder": 90 if passed else 0,
            "behavior_content_review_outside_private_ledger": False,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "memory_change": False,
            "model_training": False,
            "target_calibration_behavior_coding": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
        },
        "limitations": {
            "copied_quote_detection_is_automatic": False,
            "paraphrase_boundary_depends_on_coder_attestation": True,
            "actor_identity_blinding_is_feasible": False,
            "reliability_pass_is_persona_similarity": False,
        },
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_construction_audit_from_paths():
    paths = {
        "preregistration": DEFAULT_PREREGISTRATION,
        "codebook": DEFAULT_CODEBOOK,
        "v5_result_lock": DEFAULT_V5_RESULT,
        "sampling_frame": DEFAULT_FRAME,
        "shared_event_schema": DEFAULT_EVENT_SCHEMA,
        "contrast_source_manifest": DEFAULT_SOURCE_MANIFEST,
    }
    report = build_construction_audit(
        load_json(paths["preregistration"]),
        load_json(paths["codebook"]),
        load_json(paths["v5_result_lock"]),
        load_json(paths["sampling_frame"]),
        load_json(paths["shared_event_schema"]),
        load_json(paths["contrast_source_manifest"]),
        DEFAULT_GITIGNORE.read_text(encoding="utf-8"),
    )
    report["inputs"] = {name: _binding(path) for name, path in paths.items()}
    return report


def build_construction_markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 公開人格對照事件編碼工具 V6",
            "",
            f"- 建構通過：`{report['construction_passed']}` ({summary['check_pass_count']}/{summary['check_count']})",
            f"- 決策：`{report['decision']}`",
            "",
            "## 這一輪新增什麼",
            "",
            "`官方頁面人工觀看 -> 編碼者 A 私有帳本`",
            "",
            "`官方頁面人工觀看 -> 編碼者 B 私有帳本`",
            "",
            "`兩份完整帳本 -> 只含聚合數字的可靠度報告`",
            "",
            "兩位編碼者在輸入時看不到彼此答案，也看不到模型輸出或人格分數。網頁只提供官方 YouTube 時間點連結，不嵌入、不下載、不保存原影音或原句。",
            "工具會限制欄位並要求改寫聲明，但無法自動判斷文字是否偷偷照抄原句；這一項仍需編碼者遵守研究規則。",
            "",
            "## 目前仍是零資料",
            "",
            "| 搜尋槽 | 私有帳本 | 已觀看來源 | 已選事件 | 模型輸出 | 人格分數 |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {summary['sampling_slot_count']} | {summary['private_ledger_count']} | {summary['content_reviewed_source_count']} | {summary['selected_event_count']} | {summary['model_output_count']} | {summary['persona_score_count']} |",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def _option_tags(values, selected, labels=None):
    labels = labels or {}
    return "".join(
        f'<option value="{html.escape(value)}"'
        + (" selected" if value == selected else "")
        + f">{html.escape(labels.get(value, value))}</option>"
        for value in values
    )


def _checked(value):
    return " checked" if value else ""


def render_coding_page(ledger, frame, source_manifest, codebook, token, slot_order, error=""):
    slots = sorted(frame["sampling_slots"], key=lambda row: row["global_review_order"])
    slot_order = min(max(int(slot_order), 1), len(slots))
    slot = slots[slot_order - 1]
    entry = (ledger.get("entries") or {}).get(slot["sampling_slot_id"], {})
    status = entry.get("slot_status", "selected_event")
    dimensions = codebook["dimensions"]
    labels = codebook.get("display_labels_zh_hant") or {}
    progress = len(ledger.get("entries") or {})
    watch_url = build_official_watch_url(slot)
    secondary = set(entry.get("secondary_dimensions") or [])
    secondary_boxes = "".join(
        '<label class="check"><input type="checkbox" name="secondary_dimensions" '
        f'value="{html.escape(value)}"{_checked(value in secondary)}> '
        f"{html.escape(labels.get(value, value))}</label>"
        for value in dimensions
    )
    selected_display = "block" if status == "selected_event" else "none"
    message = f'<div class="error">{html.escape(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contrast Coding V6</title><style>
:root{{--paper:#f4efe4;--ink:#20302c;--red:#a33b2f;--line:#c9bca8;--soft:#e7ddcc;--green:#315f4d}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(135deg,#efe5d4,#f8f4eb);color:var(--ink);font-family:"Yu Mincho","Hiragino Mincho ProN",serif}}
main{{max-width:1040px;margin:24px auto;padding:0 18px 60px}} header{{display:flex;justify-content:space-between;gap:20px;align-items:end;border-bottom:3px solid var(--ink);padding:18px 0}}
h1{{font-size:clamp(28px,5vw,56px);line-height:.95;margin:0;letter-spacing:-.04em}} .meta{{text-align:right;font-size:14px}} .card{{background:rgba(255,255,255,.72);border:1px solid var(--line);box-shadow:8px 8px 0 var(--soft);padding:22px;margin-top:24px}}
.slot{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}} .slot div{{background:var(--ink);color:white;padding:12px}} label{{display:block;margin:14px 0 6px;font-weight:700}} input,select,textarea{{width:100%;padding:10px;border:1px solid var(--line);background:#fffdf8;color:var(--ink);font:inherit}} textarea{{min-height:84px;resize:vertical}}
.check{{display:block;font-weight:400;margin:7px 0}} .check input{{width:auto}} .attest{{background:#fff1d6;padding:12px;border-left:5px solid var(--red)}}
.actions{{display:flex;gap:12px;justify-content:space-between;margin-top:20px}} button,.button{{border:0;background:var(--ink);color:white;padding:12px 18px;text-decoration:none;font:inherit;cursor:pointer}} button{{background:var(--red)}} .watch{{background:var(--green);display:inline-block;margin-top:14px}}
.error{{background:#ffd8d2;border:1px solid var(--red);padding:12px;margin-top:18px}} small{{color:#5d6965}} @media(max-width:720px){{.slot{{grid-template-columns:1fr}} header{{display:block}} .meta{{text-align:left;margin-top:12px}}}}
</style></head><body><main><header><h1>Observable<br>Event Coding</h1><div class="meta">Coder: {html.escape(ledger['coder_pseudonym'])}<br>Progress: {progress}/90<br>Slot: {slot_order}/90</div></header>
{message}<section class="card"><div class="slot"><div>{html.escape(slot['actor_id'])}</div><div>{html.escape(slot['topic_cell'])}</div><div>{html.escape(slot['match_granularity'])}</div></div>
<p>搜尋起點 <strong>{slot['search_start_seconds']} 秒</strong>。只選這個時間點之後第一個符合 V5 規則的完整事件。</p>
<a class="button watch" target="_blank" rel="noreferrer" href="{html.escape(watch_url)}">在官方 YouTube 開啟時間點</a>
<form method="post" action="/save"><input type="hidden" name="token" value="{html.escape(token)}"><input type="hidden" name="sampling_slot_id" value="{html.escape(slot['sampling_slot_id'])}"><input type="hidden" name="slot_order" value="{slot_order}">
<label>槽位結果</label><select id="slot_status" name="slot_status" onchange="toggleSelected()">{_option_tags(codebook['terminal_slot_statuses'], status, labels)}</select>
<div id="selected_fields" style="display:{selected_display}"><label>事件開始秒數</label><input type="number" name="timestamp_locator_start_seconds" value="{html.escape(str(entry.get('timestamp_locator_start_seconds', slot['search_start_seconds'])))}">
<label>事件結束秒數</label><input type="number" name="timestamp_locator_end_seconds" value="{html.escape(str(entry.get('timestamp_locator_end_seconds', '')))}">
<label>情境類別</label><select name="context_family">{_option_tags(codebook['context_families'], entry.get('context_family'), labels)}</select>
<label>情境改寫</label><textarea name="observable_context_paraphrase" maxlength="500">{html.escape(entry.get('observable_context_paraphrase',''))}</textarea>
<label>行為改寫</label><textarea name="observable_behavior_paraphrase" maxlength="500">{html.escape(entry.get('observable_behavior_paraphrase',''))}</textarea>
<label>主要面向</label><select name="primary_dimension">{_option_tags(dimensions, entry.get('primary_dimension'), labels)}</select>
<label>次要面向</label>{secondary_boxes}
<label>對話行為／行動</label><select name="dialogue_act_or_action_label">{_option_tags(codebook['dialogue_act_or_action_labels'], entry.get('dialogue_act_or_action_label'), labels)}</select>
<label>可觀察對象關係</label><select name="observable_audience_relation">{_option_tags(codebook['audience_relations'], entry.get('observable_audience_relation'), labels)}</select>
<label>證據強度</label><select name="evidence_strength">{_option_tags(codebook['evidence_strengths'], entry.get('evidence_strength'), labels)}</select>
<label>歧義備註</label><textarea name="ambiguity_notes" maxlength="500">{html.escape(entry.get('ambiguity_notes',''))}</textarea>
<label>其他合理解釋</label><textarea name="alternative_interpretations" maxlength="500">{html.escape(entry.get('alternative_interpretations',''))}</textarea>
<label class="check attest"><input type="checkbox" name="paraphrase_and_no_quote_attestation" value="true"{_checked(entry.get('paraphrase_and_no_quote_attestation'))}> 我只寫研究者改寫，沒有複製原句、逐字稿或私人心理推測。</label></div>
<label class="check attest"><input type="checkbox" name="first_eligible_event_attestation" value="true"{_checked(entry.get('first_eligible_event_attestation'))}> 我從凍結搜尋起點往後檢查，沒有跳過較早事件來挑較好看的樣本。</label>
<div class="actions"><a class="button" href="/?token={urllib.parse.quote(token)}&slot={max(1,slot_order-1)}">上一格</a><button type="submit">儲存並前往下一格</button><a class="button" href="/?token={urllib.parse.quote(token)}&slot={min(90,slot_order+1)}">下一格</a></div></form></section>
<p><small>資料只寫入本機受限帳本；此頁不載入外部 JavaScript、分析器、模型輸出或另一位編碼者答案。</small></p></main>
<script>function toggleSelected(){{document.getElementById('selected_fields').style.display=document.getElementById('slot_status').value==='selected_event'?'block':'none';}}</script></body></html>"""


def _form_payload(form):
    def integer(name):
        value = form.get(name, [""])[0]
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    return {
        "sampling_slot_id": form.get("sampling_slot_id", [""])[0],
        "slot_status": form.get("slot_status", [""])[0],
        "timestamp_locator_start_seconds": integer(
            "timestamp_locator_start_seconds"
        ),
        "timestamp_locator_end_seconds": integer("timestamp_locator_end_seconds"),
        "context_family": form.get("context_family", [""])[0],
        "observable_context_paraphrase": form.get(
            "observable_context_paraphrase", [""]
        )[0],
        "observable_behavior_paraphrase": form.get(
            "observable_behavior_paraphrase", [""]
        )[0],
        "primary_dimension": form.get("primary_dimension", [""])[0],
        "secondary_dimensions": form.get("secondary_dimensions", []),
        "dialogue_act_or_action_label": form.get(
            "dialogue_act_or_action_label", [""]
        )[0],
        "observable_audience_relation": form.get(
            "observable_audience_relation", [""]
        )[0],
        "evidence_strength": form.get("evidence_strength", [""])[0],
        "ambiguity_notes": form.get("ambiguity_notes", [""])[0],
        "alternative_interpretations": form.get(
            "alternative_interpretations", [""]
        )[0],
        "first_eligible_event_attestation": (
            form.get("first_eligible_event_attestation", [""])[0] == "true"
        ),
        "paraphrase_and_no_quote_attestation": (
            form.get("paraphrase_and_no_quote_attestation", [""])[0] == "true"
        ),
    }


def make_handler(ledger_path, private_root, token, frame, source_manifest, codebook):
    class CodingHandler(BaseHTTPRequestHandler):
        def _send_html(self, body, status=200):
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _redirect(self, location):
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/health":
                self._send_html("ok")
                return
            if query.get("token", [""])[0] != token:
                self._send_html("invalid session token", status=403)
                return
            try:
                slot_order = int(query.get("slot", ["1"])[0])
            except ValueError:
                slot_order = 1
            _, ledger = load_ledger(ledger_path, private_root)
            self._send_html(
                render_coding_page(
                    ledger, frame, source_manifest, codebook, token, slot_order
                )
            )

        def do_POST(self):
            if self.path != "/save":
                self._send_html("not found", status=404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 65536:
                self._send_html("invalid form size", status=400)
                return
            form = urllib.parse.parse_qs(
                self.rfile.read(length).decode("utf-8"), keep_blank_values=True
            )
            if form.get("token", [""])[0] != token:
                self._send_html("invalid session token", status=403)
                return
            try:
                slot_order = int(form.get("slot_order", ["1"])[0])
            except ValueError:
                slot_order = 1
            try:
                save_entry(
                    ledger_path,
                    _form_payload(form),
                    frame=frame,
                    codebook=codebook,
                    private_root=private_root,
                )
            except ValueError as error:
                _, ledger = load_ledger(ledger_path, private_root)
                self._send_html(
                    render_coding_page(
                        ledger,
                        frame,
                        source_manifest,
                        codebook,
                        token,
                        slot_order,
                        error=str(error),
                    ),
                    status=400,
                )
                return
            next_slot = min(len(frame["sampling_slots"]), slot_order + 1)
            self._redirect(
                f"/?token={urllib.parse.quote(token)}&slot={next_slot}"
            )

        def log_message(self, format_string, *args):
            return

    return CodingHandler


def serve_coder(ledger_path, coder_pseudonym, port, open_browser, private_root):
    frame = load_json(DEFAULT_FRAME)
    source_manifest = load_json(DEFAULT_SOURCE_MANIFEST)
    codebook = load_json(DEFAULT_CODEBOOK)
    ledger_path = resolve_private_path(ledger_path, private_root)
    if not ledger_path.exists():
        initialize_ledger(
            coder_pseudonym,
            ledger_path,
            private_root=private_root,
        )
    _, ledger = load_ledger(ledger_path, private_root)
    errors = validate_ledger(
        ledger, frame, codebook, expected_coder=validate_coder_pseudonym(coder_pseudonym)
    )
    if errors:
        raise ValueError("invalid ledger: " + "; ".join(errors))
    token = secrets.token_urlsafe(24)
    handler = make_handler(
        ledger_path, private_root, token, frame, source_manifest, codebook
    )
    server = ThreadingHTTPServer(("127.0.0.1", int(port)), handler)
    url = f"http://127.0.0.1:{server.server_port}/?token={urllib.parse.quote(token)}&slot=1"
    print(json.dumps({"url": url, "coder": coder_pseudonym}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _write_text(path, text, overwrite):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("construction-audit")
    audit_parser.add_argument("--output-json", default=str(DEFAULT_CONSTRUCTION_JSON))
    audit_parser.add_argument("--output-md", default=str(DEFAULT_CONSTRUCTION_MD))
    audit_parser.add_argument("--overwrite", action="store_true")
    audit_parser.add_argument("--require-pass", action="store_true")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--coder", required=True)
    init_parser.add_argument("--ledger", required=True)
    init_parser.add_argument("--overwrite", action="store_true")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--coder", required=True)
    serve_parser.add_argument("--ledger", required=True)
    serve_parser.add_argument("--port", type=int, default=7865)
    serve_parser.add_argument("--open-browser", action="store_true")

    reliability_parser = subparsers.add_parser("reliability")
    reliability_parser.add_argument("--ledger-a", required=True)
    reliability_parser.add_argument("--ledger-b", required=True)
    reliability_parser.add_argument("--output", required=True)
    reliability_parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    if args.command == "construction-audit":
        report = build_construction_audit_from_paths()
        _write_text(
            args.output_json,
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
        _write_text(
            args.output_md, build_construction_markdown(report), args.overwrite
        )
        print(
            json.dumps(
                {
                    "construction_passed": report["construction_passed"],
                    "checks": (
                        f"{report['summary']['check_pass_count']}/"
                        f"{report['summary']['check_count']}"
                    ),
                    "decision": report["decision"],
                },
                ensure_ascii=False,
            )
        )
        if args.require_pass and not report["construction_passed"]:
            raise SystemExit(1)
        return
    if args.command == "init":
        path, ledger = initialize_ledger(
            args.coder,
            args.ledger,
            overwrite=args.overwrite,
        )
        print(
            json.dumps(
                {"ledger": str(path), "coder": ledger["coder_pseudonym"]},
                ensure_ascii=False,
            )
        )
        return
    if args.command == "serve":
        serve_coder(
            args.ledger,
            args.coder,
            args.port,
            args.open_browser,
            DEFAULT_PRIVATE_ROOT,
        )
        return
    if args.command == "reliability":
        _, ledger_a = load_ledger(args.ledger_a)
        _, ledger_b = load_ledger(args.ledger_b)
        report = build_reliability_report(
            ledger_a,
            ledger_b,
            load_json(DEFAULT_FRAME),
            load_json(DEFAULT_CODEBOOK),
        )
        output = resolve_private_path(args.output)
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {output}")
        _atomic_write_json(output, report)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "reliability_passed": report["gates"]["reliability_passed"],
                    "persona_score_computed": False,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
