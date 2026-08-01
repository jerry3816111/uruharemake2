#!/usr/bin/env python3
"""Freeze target-calibration slots and provide a gated local two-coder tool."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import secrets
import urllib.parse
import webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from public_persona_contrast_coding_tool_v6 import (
    _atomic_write_json,
    _checked,
    _form_payload,
    _option_tags,
    _write_text,
    nominal_krippendorff_alpha,
    normalize_entry,
    resolve_private_path,
    temporal_iou,
    utc_now,
    validate_coder_pseudonym,
    validate_entry,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_target_calibration_coding_v9_preregistration.json"
)
DEFAULT_HARNESS_LOCK = (
    ROOT / "configs/public_persona_target_calibration_coding_v9_harness_lock.json"
)
DEFAULT_V3_RESULT = (
    ROOT / "configs/public_persona_precontent_governance_v3_result_lock.json"
)
DEFAULT_V8_RESULT_LOCK = (
    ROOT / "configs/public_persona_source_availability_v8_result_lock.json"
)
DEFAULT_V8_RESULT = ROOT / "reports/public_persona_source_availability_v8_result.json"
DEFAULT_REFERENCE_MANIFEST = (
    ROOT / "datasets/public_persona_reference_source_manifest_v2.json"
)
DEFAULT_SOURCE_METADATA = (
    ROOT / "datasets/public_persona_target_calibration_source_metadata_v9.json"
)
DEFAULT_EVENT_SCHEMA = ROOT / "configs/public_persona_event_coding_schema_v1.json"
DEFAULT_CODEBOOK = ROOT / "configs/public_persona_contrast_coding_codebook_v6.json"
DEFAULT_CODER_MANUAL = (
    ROOT / "configs/public_persona_contrast_coding_manual_v7.json"
)
DEFAULT_METHOD_REGISTRY = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_method_registry.json"
)
DEFAULT_FRAME = (
    ROOT / "datasets/public_persona_target_calibration_sampling_frame_v9.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/public_persona_target_calibration_coding_v9_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/public_persona_target_calibration_coding_v9_construction.md"
)
DEFAULT_PRIVATE_ROOT = (
    ROOT / "analysis/local_public_persona_target_calibration_v9"
)
DEFAULT_FUTURE_V7_RELIABILITY_LOCK = (
    ROOT / "configs/public_persona_contrast_coding_pilot_v7_reliability_lock.json"
)
DEFAULT_GITIGNORE = ROOT / ".gitignore"

EXPERIMENT_ID = "public_persona_target_calibration_coding_v9"
TARGET_ID = "ichinose_uruha_public_persona"
LEDGER_SCHEMA = "uruha_public_persona_target_calibration_independent_coder_ledger_v9"
PRIVATE_ROOT_RELATIVE = "analysis/local_public_persona_target_calibration_v9/"
PASS_DECISION = (
    "authorize_frozen_target_calibration_frame_and_local_tool_installation_"
    "pending_v7_reliability_only"
)
FAIL_DECISION = "repair_target_calibration_protocol_before_any_target_behavior_review"
REQUIRED_V3_DECISION = (
    "authorize_bounded_calibration_event_coding_and_consent_usability_review_only"
)
REQUIRED_V7_DECISION = (
    "authorize_full_v5_contrast_coding_with_unchanged_v6_codebook_only"
)
AUTHORIZED_SOURCE_IDS = {
    "uruha_calibration_youtube_valorant_20260318",
    "uruha_calibration_youtube_street_fighter_20250317",
    "uruha_calibration_youtube_farming_20250308",
}
FORBIDDEN_HOLDOUT_SOURCE_IDS = {
    "uruha_youtube_forza_holdout_v2",
    "uruha_youtube_apex_team_holdout_v2",
    "uruha_final_holdout_youtube_apex_collab_20250206",
    "uruha_final_holdout_youtube_social_deduction_20210404",
}
PROHIBITED_CONTENT_KEYS = {
    "title",
    "description",
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
    "observable_context_paraphrase",
    "observable_behavior_paraphrase",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    return bool(path_text) and path.is_file() and sha256_file(path) == expected


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _uint64_from_digest(digest):
    return int.from_bytes(bytes.fromhex(digest[:16]), byteorder="big")


def _find_prohibited_keys(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in PROHIBITED_CONTENT_KEYS:
                found.append(path)
            found.extend(_find_prohibited_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_prohibited_keys(child, f"{prefix}[{index}]"))
    return found


def build_sampling_frame(preregistration, source_metadata):
    slots = []
    for source in sorted(source_metadata["sources"], key=lambda row: row["source_id"]):
        duration = int(source["duration_seconds"])
        for slot_index in range(1, 11):
            start = duration * (slot_index - 1) // 10
            end = duration * slot_index // 10
            width = end - start
            seed = _digest(
                f"{EXPERIMENT_ID}|{source['source_partition_key']}|{slot_index}"
            )
            search_start = start + (_uint64_from_digest(seed) % width)
            slot_id = f"{source['source_id']}_slot_{slot_index:02d}"
            review_hash = _digest(f"{EXPERIMENT_ID}|{slot_id}|global_review_order")
            slots.append(
                {
                    "sampling_slot_id": slot_id,
                    "source_id": source["source_id"],
                    "actor_id": source["actor_id"],
                    "source_partition_key": source["source_partition_key"],
                    "topic_cell": source["topic_cell"],
                    "dataset_role": "target_calibration",
                    "source_duration_seconds": duration,
                    "slot_index": slot_index,
                    "stratum_start_seconds": start,
                    "stratum_end_exclusive_seconds": end,
                    "search_start_seconds": search_start,
                    "selection_seed_sha256": seed,
                    "review_order_sha256": review_hash,
                    "global_review_order": None,
                    "slot_status": "unreviewed_no_content_access",
                }
            )
    for order, slot in enumerate(
        sorted(slots, key=lambda row: row["review_order_sha256"]), start=1
    ):
        slot["global_review_order"] = order
    slots.sort(key=lambda row: row["global_review_order"])
    return {
        "schema": "uruha_public_persona_target_calibration_sampling_frame_v9",
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen_empty_30_slot_frame_before_behavior_review",
        "generated_at": "2026-08-01",
        "target_id": TARGET_ID,
        "preregistration_binding": _binding(DEFAULT_PREREGISTRATION),
        "source_metadata_binding": _binding(DEFAULT_SOURCE_METADATA),
        "sampling_algorithm": {
            "temporal_strata_per_source": 10,
            "strata_are_search_regions_not_behavior_units": True,
            "event_selection_rule": (
                "first eligible complete event at or after search_start_seconds"
            ),
            "no_eligible_event_replacement_allowed": False,
            "overlap_blocked_slot_replacement_allowed": False,
            "fixed_duration_event_chunking": False,
            "behavior_content_used": False,
        },
        "sampling_slots": slots,
        "current_counts": {
            "sampling_slot_count": len(slots),
            "private_ledger_count": 0,
            "content_reviewed_source_count": 0,
            "selected_event_count": 0,
            "coded_event_count": 0,
            "independently_reviewed_event_count": 0,
            "human_coder_count": 0,
            "raw_or_verbatim_record_count": 0,
            "model_output_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "model_call_count": 0,
            "production_memory_write_count": 0,
        },
        "content_boundary": {
            "behavior_content_reviewed": False,
            "event_boundaries_selected": False,
            "event_codes_available": False,
            "researcher_paraphrase_available": False,
            "raw_or_verbatim_content_available": False,
            "model_output_available": False,
            "persona_score_available": False,
            "final_holdout_source_included": False,
            "private_event_registry_git_tracked": False,
        },
    }


def _rows_by_id(payload):
    return {row["source_id"]: row for row in payload.get("sources") or []}


def validate_sampling_frame(frame, preregistration, source_metadata):
    errors = []
    if frame.get("schema") != "uruha_public_persona_target_calibration_sampling_frame_v9":
        errors.append("schema")
    if frame.get("experiment_id") != EXPERIMENT_ID:
        errors.append("experiment_id")
    if frame.get("target_id") != TARGET_ID:
        errors.append("target_id")
    if frame.get("preregistration_binding") != _binding(DEFAULT_PREREGISTRATION):
        errors.append("preregistration_binding")
    if frame.get("source_metadata_binding") != _binding(DEFAULT_SOURCE_METADATA):
        errors.append("source_metadata_binding")
    expected = build_sampling_frame(preregistration, source_metadata)
    if frame != expected:
        errors.append("frame_does_not_match_deterministic_rebuild")
    slots = frame.get("sampling_slots") or []
    if len(slots) != 30:
        errors.append("slot_count")
    source_counts = Counter(row.get("source_id") for row in slots)
    if source_counts != Counter({source_id: 10 for source_id in AUTHORIZED_SOURCE_IDS}):
        errors.append("source_balance")
    if {row.get("global_review_order") for row in slots} != set(range(1, 31)):
        errors.append("review_order")
    for row in slots:
        if not (
            row.get("stratum_start_seconds")
            <= row.get("search_start_seconds", -1)
            < row.get("stratum_end_exclusive_seconds", -1)
            <= row.get("source_duration_seconds", -1)
        ):
            errors.append(f"slot_bounds:{row.get('sampling_slot_id')}")
        if row.get("source_id") in FORBIDDEN_HOLDOUT_SOURCE_IDS:
            errors.append(f"holdout_source:{row.get('source_id')}")
    if _find_prohibited_keys(frame):
        errors.append("prohibited_content_key")
    return errors


def human_use_authorized(path=DEFAULT_FUTURE_V7_RELIABILITY_LOCK):
    path = Path(path)
    if not path.is_file():
        return False, "V7 reliability result lock is absent"
    payload = load_json(path)
    if payload.get("decision") != REQUIRED_V7_DECISION:
        return False, "V7 reliability decision does not authorize unchanged codebook use"
    if payload.get("reliability_passed") is not True:
        return False, "V7 reliability gate did not pass"
    if payload.get("persona_score_computed") is not False:
        return False, "authorization lock must not contain a persona score"
    codebook_binding = (payload.get("frozen_artifacts") or {}).get("codebook")
    if codebook_binding != _binding(DEFAULT_CODEBOOK):
        return False, "V7 reliability lock is not bound to the shared V6 codebook"
    return True, "authorized"


def build_construction_audit(
    preregistration,
    harness_lock,
    v3_result,
    v8_result_lock,
    v8_result,
    reference_manifest,
    source_metadata,
    event_schema,
    codebook,
    coder_manual,
    method_registry,
    frame,
    gitignore_text,
):
    violations = []
    if preregistration.get("schema") != (
        "uruha_public_persona_target_calibration_coding_preregistration_v9"
    ):
        violations.append("preregistration_schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations.append("experiment_id")
    for name, binding in (preregistration.get("depends_on") or {}).items():
        if not _binding_valid(binding):
            violations.append(f"dependency:{name}")
    if v3_result.get("decision") != REQUIRED_V3_DECISION:
        violations.append("v3_decision")
    if (v3_result.get("authorizations") or {}).get(
        "bounded_calibration_event_coding"
    ) is not True:
        violations.append("v3_calibration_authorization")
    if v8_result_lock.get("decision") != (
        "authorize_existing_v7_human_coding_source_access_only"
    ):
        violations.append("v8_result_lock_decision")
    if not _binding_valid(
        (v8_result_lock.get("frozen_artifacts") or {}).get("result_json")
    ):
        violations.append("v8_result_binding")
    if v8_result.get("passed") is not True:
        violations.append("v8_source_availability")
    v8_rows = {
        row["source_id"]: row
        for row in v8_result.get("rows") or []
        if row.get("source_group") == "target_calibration"
    }
    metadata_rows = _rows_by_id(source_metadata)
    reference_rows = _rows_by_id(reference_manifest)
    if set(metadata_rows) != AUTHORIZED_SOURCE_IDS:
        violations.append("metadata_source_ids")
    if set(v8_rows) != AUTHORIZED_SOURCE_IDS:
        violations.append("v8_target_source_ids")
    if not AUTHORIZED_SOURCE_IDS.issubset(reference_rows):
        violations.append("reference_manifest_source_ids")
    for source_id, metadata in metadata_rows.items():
        reference = reference_rows.get(source_id) or {}
        available = v8_rows.get(source_id) or {}
        expected = {
            "actor_id": reference.get("actor_id"),
            "source_partition_key": reference.get("source_partition_key"),
            "video_id": reference.get("video_id"),
            "publisher_channel_id": reference.get("publisher_channel_id"),
            "published_at": reference.get("published_at"),
        }
        if any(metadata.get(field) != value for field, value in expected.items()):
            violations.append(f"metadata_reference_mismatch:{source_id}")
        if not all(
            available.get(field) is True
            for field in (
                "channel_match",
                "published_date_match",
                "oembed_resolved",
                "watch_metadata_resolved",
            )
        ):
            violations.append(f"v8_availability_mismatch:{source_id}")
        duration = metadata.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            violations.append(f"duration:{source_id}")
    if _find_prohibited_keys(source_metadata):
        violations.append("metadata_prohibited_content_key")
    if (event_schema.get("construct") or {}).get("dimensions") != codebook.get(
        "dimensions"
    ):
        violations.append("shared_dimensions")
    if coder_manual.get("category_origin") != (
        "project_specific_observation_manual_not_official_personality_labels_or_target_answers"
    ):
        violations.append("coder_manual_origin")
    if method_registry.get("method_commitments", {}).get(
        "selection_frame_frozen_before_behavior_review"
    ) is not True:
        violations.append("method_registry")
    violations.extend(f"frame:{error}" for error in validate_sampling_frame(
        frame, preregistration, source_metadata
    ))
    expected_counts = preregistration.get("expected_counts_after_construction")
    if frame.get("current_counts") != expected_counts:
        violations.append("construction_counts")
    if PRIVATE_ROOT_RELATIVE not in gitignore_text.splitlines():
        violations.append("private_root_not_gitignored")
    policy = preregistration.get("decision_policy") or {}
    if policy.get("construction_pass") != PASS_DECISION:
        violations.append("decision_pass")
    for field in (
        "target_human_coding_now",
        "model_execution",
        "runtime_change",
        "prompt_change",
        "memory_change",
        "model_training",
        "sealed_holdout_unsealing",
        "rater_recruitment",
        "formal_persona_scoring",
        "public_persona_fidelity_claim",
        "private_person_copy_claim",
    ):
        if policy.get(field) is not False:
            violations.append(f"decision:{field}")
    if harness_lock.get("experiment_id") != EXPERIMENT_ID:
        violations.append("harness_experiment")
    for binding in (harness_lock.get("frozen_artifacts") or {}).values():
        if not _binding_valid(binding):
            violations.append("harness_binding")
    human_authorized, _ = human_use_authorized()
    if human_authorized:
        violations.append("unexpected_human_authorization_during_construction")
    checks = {
        "governance_and_all_existing_dependencies_are_hash_bound": not any(
            value.startswith(("dependency:", "v3_", "harness_"))
            for value in violations
        ),
        "three_official_target_calibration_sources_match_v8_metadata": not any(
            value.startswith((
                "metadata_",
                "v8_",
                "reference_",
                "duration:",
            ))
            for value in violations
        ),
        "thirty_content_free_slots_rebuild_exactly": not any(
            value.startswith("frame:") for value in violations
        ),
        "all_four_final_holdouts_and_all_answer_payloads_are_excluded": (
            not (set(metadata_rows) & FORBIDDEN_HOLDOUT_SOURCE_IDS)
            and not _find_prohibited_keys(source_metadata)
            and not _find_prohibited_keys(frame)
        ),
        "shared_six_dimension_codebook_manual_and_method_are_unchanged": not any(
            value in {"shared_dimensions", "coder_manual_origin", "method_registry"}
            for value in violations
        ),
        "private_two_coder_storage_is_declared_and_gitignored": (
            "private_root_not_gitignored" not in violations
        ),
        "v7_reliability_is_required_and_target_human_use_remains_blocked": (
            not human_authorized
            and preregistration.get("human_use_gate", {}).get(
                "v7_reliability_result_required_before_target_coding"
            )
            is True
        ),
        "model_runtime_prompt_memory_training_rating_and_claims_remain_forbidden": not any(
            value.startswith("decision:") for value in violations
        ),
        "all_behavior_human_model_score_holdout_and_runtime_counts_remain_zero": (
            "construction_counts" not in violations
        ),
    }
    passed = all(checks.values()) and not violations
    return {
        "schema": "uruha_public_persona_target_calibration_coding_construction_v9",
        "experiment_id": EXPERIMENT_ID,
        "construction_passed": passed,
        "human_coding_completed": False,
        "reliability_computed": False,
        "persona_score_computed": False,
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "summary": {
            "check_count": len(checks),
            "check_pass_count": sum(checks.values()),
            "source_count": len(metadata_rows),
            **(frame.get("current_counts") or {}),
        },
        "checks": checks,
        "violations": violations,
        "authorizations": {
            "frozen_target_calibration_sampling_frame": passed,
            "local_two_coder_tool_installed": passed,
            "target_human_coding_now": False,
            "maximum_future_coder_count_after_v7_pass": 2 if passed else 0,
            "maximum_future_slot_count_per_coder_after_v7_pass": 30 if passed else 0,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "memory_change": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
        },
        "next_required_evidence": (
            "Complete V7 with two distinct humans and pass its frozen reliability gate. "
            "Only then may the same unchanged codebook be used for the thirty target "
            "calibration slots in two isolated private ledgers."
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_construction_audit_from_paths():
    paths = {
        "preregistration": DEFAULT_PREREGISTRATION,
        "harness_lock": DEFAULT_HARNESS_LOCK,
        "v3_result": DEFAULT_V3_RESULT,
        "v8_result_lock": DEFAULT_V8_RESULT_LOCK,
        "v8_result": DEFAULT_V8_RESULT,
        "reference_manifest": DEFAULT_REFERENCE_MANIFEST,
        "source_metadata": DEFAULT_SOURCE_METADATA,
        "event_schema": DEFAULT_EVENT_SCHEMA,
        "codebook": DEFAULT_CODEBOOK,
        "coder_manual": DEFAULT_CODER_MANUAL,
        "method_registry": DEFAULT_METHOD_REGISTRY,
        "frame": DEFAULT_FRAME,
    }
    report = build_construction_audit(
        *(load_json(paths[name]) for name in paths),
        DEFAULT_GITIGNORE.read_text(encoding="utf-8"),
    )
    report["inputs"] = {name: _binding(path) for name, path in paths.items()}
    return report


def build_construction_markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 目標人物校準事件框架 V9",
            "",
            f"- 建構通過：`{report['construction_passed']}` ({summary['check_pass_count']}/{summary['check_count']})",
            f"- 決策：`{report['decision']}`",
            "",
            "## 本輪實際完成",
            "",
            "`3 個官方校準來源 -> 每來源 10 個時間分層 -> 30 個內容無關搜尋起點`",
            "",
            "搜尋起點由凍結雜湊決定，人工之後只能選起點後第一個合格完整事件，不能跳到比較像目標人物或比較有趣的片段。四個最終 holdout 全部不在框架內。",
            "",
            "| 來源 | 搜尋槽 | 行為內容 | 真人標註 | 模型輸出 | 人格分數 |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {summary['source_count']} | {summary['sampling_slot_count']} | {summary['content_reviewed_source_count']} | {summary['human_coder_count']} | {summary['model_output_count']} | {summary['persona_score_count']} |",
            "",
            "## 為什麼現在不要求人工繼續",
            "",
            "V7 共用 codebook 的雙人 pilot 仍是零資料。若現在先做目標人物 30 格，兩位人類要增加 60 次判斷，而且 codebook 若在 V7 失敗後修訂，資料不能直接合併。因此 V9 已把框架與工具準備好，但人工作業保持關閉。",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def _frame_slots_by_id(frame):
    return {row["sampling_slot_id"]: row for row in frame.get("sampling_slots") or []}


def _target_ledger_binding(frame_path=DEFAULT_FRAME, codebook_path=DEFAULT_CODEBOOK):
    return {"frame_binding": _binding(frame_path), "codebook_binding": _binding(codebook_path)}


def initialize_target_ledger(
    coder_pseudonym,
    ledger_path,
    authorization_lock=DEFAULT_FUTURE_V7_RELIABILITY_LOCK,
    private_root=DEFAULT_PRIVATE_ROOT,
    overwrite=False,
):
    authorized, reason = human_use_authorized(authorization_lock)
    if not authorized:
        raise PermissionError(reason)
    coder_pseudonym = validate_coder_pseudonym(coder_pseudonym)
    ledger_path = resolve_private_path(ledger_path, private_root)
    if ledger_path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {ledger_path}")
    payload = {
        "schema": LEDGER_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "status": "private_independent_target_calibration_ledger",
        "coder_pseudonym": coder_pseudonym,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        **_target_ledger_binding(),
        "authorization_lock_binding": _binding(authorization_lock),
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


def validate_target_ledger(
    ledger,
    frame,
    codebook,
    expected_coder=None,
    require_complete=False,
):
    errors = []
    if ledger.get("schema") != LEDGER_SCHEMA:
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
    for field, expected in _target_ledger_binding().items():
        if ledger.get(field) != expected:
            errors.append(field)
    if not _binding_valid(ledger.get("authorization_lock_binding")):
        errors.append("authorization_lock_binding")
    boundary = ledger.get("data_boundary") or {}
    if boundary != {
        "private_gitignored_storage_required": True,
        "other_coder_ledger_visible": False,
        "model_output_or_persona_score_visible": False,
        "raw_or_verbatim_content_allowed": False,
        "prompt_memory_retrieval_training_or_model_selection_use": False,
    }:
        errors.append("data_boundary")
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return errors + ["entries:object_required"]
    slots = _frame_slots_by_id(frame)
    if set(entries) - set(slots):
        errors.append("unknown_sampling_slots")
    if require_complete and set(entries) != set(slots):
        errors.append("ledger_incomplete")
    for slot_id, entry in entries.items():
        if slot_id not in slots or not isinstance(entry, dict):
            continue
        errors.extend(
            f"{slot_id}:{error}"
            for error in validate_entry(entry, slots[slot_id], codebook, coder)
        )
    selected_by_source = {}
    for slot_id, entry in entries.items():
        if isinstance(entry, dict) and entry.get("slot_status") == "selected_event":
            selected_by_source.setdefault(entry.get("source_id"), []).append(
                (
                    entry.get("timestamp_locator_start_seconds"),
                    entry.get("timestamp_locator_end_seconds"),
                    slot_id,
                )
            )
    for source_id, intervals in selected_by_source.items():
        valid = [
            row
            for row in intervals
            if isinstance(row[0], int)
            and not isinstance(row[0], bool)
            and isinstance(row[1], int)
            and not isinstance(row[1], bool)
        ]
        valid.sort()
        for previous, current in zip(valid, valid[1:]):
            if current[0] < previous[1]:
                errors.append(f"overlap:{source_id}:{previous[2]}:{current[2]}")
    return errors


def save_target_entry(ledger_path, payload, private_root=DEFAULT_PRIVATE_ROOT):
    frame = load_json(DEFAULT_FRAME)
    codebook = load_json(DEFAULT_CODEBOOK)
    ledger_path = resolve_private_path(ledger_path, private_root)
    ledger = load_json(ledger_path)
    existing_errors = validate_target_ledger(ledger, frame, codebook)
    if existing_errors:
        raise ValueError("invalid ledger: " + "; ".join(existing_errors))
    slots = _frame_slots_by_id(frame)
    slot_id = str(payload.get("sampling_slot_id") or "")
    if slot_id not in slots:
        raise ValueError("unknown sampling slot")
    entry = normalize_entry(payload, slots[slot_id], codebook, ledger["coder_pseudonym"])
    entry_errors = validate_entry(entry, slots[slot_id], codebook, ledger["coder_pseudonym"])
    if entry_errors:
        raise ValueError("invalid entry: " + "; ".join(entry_errors))
    candidate = json.loads(json.dumps(ledger))
    candidate["entries"][slot_id] = entry
    candidate["updated_at"] = utc_now()
    candidate_errors = validate_target_ledger(candidate, frame, codebook)
    if candidate_errors:
        raise ValueError("invalid ledger update: " + "; ".join(candidate_errors))
    _atomic_write_json(ledger_path, candidate)
    return candidate


def _official_watch_url(slot):
    partition = str(slot["source_partition_key"])
    prefix = "youtube_archive_"
    if not partition.startswith(prefix):
        raise ValueError("invalid YouTube source partition")
    video_id = partition[len(prefix) :]
    if not video_id or not all(character.isalnum() or character in "_-" for character in video_id):
        raise ValueError("invalid YouTube video id")
    return (
        f"https://www.youtube.com/watch?v={video_id}"
        f"&t={int(slot['search_start_seconds'])}s"
    )


def render_target_page(ledger, frame, codebook, token, slot_order, error=""):
    slots = sorted(frame["sampling_slots"], key=lambda row: row["global_review_order"])
    total = len(slots)
    slot_order = min(max(int(slot_order), 1), total)
    slot = slots[slot_order - 1]
    entry = (ledger.get("entries") or {}).get(slot["sampling_slot_id"], {})
    status = entry.get("slot_status", "selected_event")
    labels = codebook["display_labels_zh_hant"]
    secondary = set(entry.get("secondary_dimensions") or [])
    secondary_boxes = "".join(
        '<label class="check"><input type="checkbox" name="secondary_dimensions" '
        f'value="{html.escape(value)}"{_checked(value in secondary)}> '
        f"{html.escape(labels[value])}</label>"
        for value in codebook["dimensions"]
    )
    message = f'<div class="error">{html.escape(error)}</div>' if error else ""
    selected_display = "block" if status == "selected_event" else "none"
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Target Calibration Coding V9</title><style>
:root{{--paper:#f5f0e5;--ink:#20302c;--red:#a33b2f;--line:#c9bca8;--soft:#e7ddcc;--green:#315f4d}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(135deg,#efe5d4,#f8f4eb);color:var(--ink);font-family:"Yu Mincho","Hiragino Mincho ProN",serif}}
main{{max-width:1040px;margin:24px auto;padding:0 18px 60px}}header{{display:flex;justify-content:space-between;gap:20px;align-items:end;border-bottom:3px solid var(--ink);padding:18px 0}}
h1{{font-size:clamp(28px,5vw,54px);line-height:.95;margin:0}}.meta{{text-align:right}}.card{{background:rgba(255,255,255,.76);border:1px solid var(--line);box-shadow:8px 8px 0 var(--soft);padding:22px;margin-top:24px}}
.slot{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}.slot div{{background:var(--ink);color:white;padding:12px}}label{{display:block;margin:14px 0 6px;font-weight:700}}input,select,textarea{{width:100%;padding:10px;border:1px solid var(--line);background:#fffdf8;font:inherit}}textarea{{min-height:84px;resize:vertical}}
.check{{font-weight:400;margin:7px 0}}.check input{{width:auto}}.attest{{background:#fff1d6;padding:12px;border-left:5px solid var(--red)}}.actions{{display:flex;gap:12px;justify-content:space-between;margin-top:20px}}button,.button{{border:0;background:var(--ink);color:white;padding:12px 18px;text-decoration:none;font:inherit;cursor:pointer}}button{{background:var(--red)}}.watch{{background:var(--green);display:inline-block;margin-top:14px}}.error{{background:#ffd8d2;border:1px solid var(--red);padding:12px;margin-top:18px}}small{{color:#5d6965}}@media(max-width:720px){{.slot{{grid-template-columns:1fr}}header{{display:block}}.meta{{text-align:left;margin-top:12px}}}}
</style></head><body><main><header><h1>Target Calibration<br>Event Coding</h1><div class="meta">Coder: {html.escape(ledger['coder_pseudonym'])}<br>Progress: {len(ledger.get('entries') or {})}/{total}<br>Slot: {slot_order}/{total}</div></header>
{message}<section class="card"><div class="slot"><div>{html.escape(slot['actor_id'])}</div><div>{html.escape(slot['topic_cell'])}</div><div>target calibration</div></div>
<p>搜尋起點 <strong>{slot['search_start_seconds']} 秒</strong>。只選此時間點後第一個符合凍結規則的完整事件，不得跳到較有特色的片段。</p>
<a class="button watch" target="_blank" rel="noreferrer" href="{html.escape(_official_watch_url(slot))}">在官方 YouTube 開啟時間點</a>
<form method="post" action="/save"><input type="hidden" name="token" value="{html.escape(token)}"><input type="hidden" name="sampling_slot_id" value="{html.escape(slot['sampling_slot_id'])}"><input type="hidden" name="slot_order" value="{slot_order}">
<label>槽位結果</label><select id="slot_status" name="slot_status" onchange="toggleSelected()">{_option_tags(codebook['terminal_slot_statuses'],status,labels)}</select>
<div id="selected_fields" style="display:{selected_display}"><label>事件開始秒數</label><input type="number" name="timestamp_locator_start_seconds" value="{html.escape(str(entry.get('timestamp_locator_start_seconds',slot['search_start_seconds'])))}">
<label>事件結束秒數</label><input type="number" name="timestamp_locator_end_seconds" value="{html.escape(str(entry.get('timestamp_locator_end_seconds','')))}">
<label>情境類別</label><select name="context_family">{_option_tags(codebook['context_families'],entry.get('context_family'),labels)}</select>
<label>情境改寫</label><textarea name="observable_context_paraphrase" maxlength="500">{html.escape(entry.get('observable_context_paraphrase',''))}</textarea>
<label>行為改寫</label><textarea name="observable_behavior_paraphrase" maxlength="500">{html.escape(entry.get('observable_behavior_paraphrase',''))}</textarea>
<label>主要面向</label><select name="primary_dimension">{_option_tags(codebook['dimensions'],entry.get('primary_dimension'),labels)}</select>
<label>次要面向</label>{secondary_boxes}
<label>對話行為／行動</label><select name="dialogue_act_or_action_label">{_option_tags(codebook['dialogue_act_or_action_labels'],entry.get('dialogue_act_or_action_label'),labels)}</select>
<label>可觀察對象關係</label><select name="observable_audience_relation">{_option_tags(codebook['audience_relations'],entry.get('observable_audience_relation'),labels)}</select>
<label>證據強度</label><select name="evidence_strength">{_option_tags(codebook['evidence_strengths'],entry.get('evidence_strength'),labels)}</select>
<label>歧義備註</label><textarea name="ambiguity_notes" maxlength="500">{html.escape(entry.get('ambiguity_notes',''))}</textarea>
<label>其他合理解釋</label><textarea name="alternative_interpretations" maxlength="500">{html.escape(entry.get('alternative_interpretations',''))}</textarea>
<label class="check attest"><input type="checkbox" name="paraphrase_and_no_quote_attestation" value="true"{_checked(entry.get('paraphrase_and_no_quote_attestation'))}> 我只寫研究者改寫，沒有複製原句、逐字稿或推測私人心理。</label></div>
<label class="check attest"><input type="checkbox" name="first_eligible_event_attestation" value="true"{_checked(entry.get('first_eligible_event_attestation'))}> 我沒有跳過更早的合格事件來挑選較像目標人物的樣本。</label>
<div class="actions"><a class="button" href="/?token={urllib.parse.quote(token)}&slot={max(1,slot_order-1)}">上一格</a><button type="submit">儲存並前往下一格</button><a class="button" href="/?token={urllib.parse.quote(token)}&slot={min(total,slot_order+1)}">下一格</a></div></form></section>
<p><small>資料只寫入本機隔離帳本；頁面不載入分析器、模型輸出、最終 holdout 或另一位編碼者答案。</small></p></main>
<script>function toggleSelected(){{document.getElementById('selected_fields').style.display=document.getElementById('slot_status').value==='selected_event'?'block':'none';}}</script></body></html>"""


def make_target_handler(ledger_path, private_root, token, frame, codebook):
    class TargetCodingHandler(BaseHTTPRequestHandler):
        def _send(self, body, status=200):
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
            self._send(render_target_page(ledger, frame, codebook, token, slot_order))

        def do_POST(self):
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
            try:
                save_target_entry(ledger_path, _form_payload(form), private_root)
            except ValueError as error:
                ledger = load_json(resolve_private_path(ledger_path, private_root))
                self._send(
                    render_target_page(
                        ledger, frame, codebook, token, slot_order, str(error)
                    ),
                    400,
                )
                return
            next_slot = min(len(frame["sampling_slots"]), slot_order + 1)
            self._redirect(f"/?token={urllib.parse.quote(token)}&slot={next_slot}")

        def log_message(self, format_string, *args):
            return

    return TargetCodingHandler


def serve_target(
    ledger_path,
    coder_pseudonym,
    port,
    open_browser,
    authorization_lock,
    private_root=DEFAULT_PRIVATE_ROOT,
):
    authorized, reason = human_use_authorized(authorization_lock)
    if not authorized:
        raise PermissionError(reason)
    frame = load_json(DEFAULT_FRAME)
    codebook = load_json(DEFAULT_CODEBOOK)
    ledger_path = resolve_private_path(ledger_path, private_root)
    if not ledger_path.exists():
        initialize_target_ledger(
            coder_pseudonym,
            ledger_path,
            authorization_lock,
            private_root,
        )
    ledger = load_json(ledger_path)
    errors = validate_target_ledger(
        ledger,
        frame,
        codebook,
        expected_coder=validate_coder_pseudonym(coder_pseudonym),
    )
    if errors:
        raise ValueError("invalid target ledger: " + "; ".join(errors))
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(
        ("127.0.0.1", int(port)),
        make_target_handler(ledger_path, private_root, token, frame, codebook),
    )
    url = f"http://127.0.0.1:{server.server_port}/?token={urllib.parse.quote(token)}&slot=1"
    print(
        json.dumps(
            {"url": url, "coder": coder_pseudonym, "target_slots": 30},
            ensure_ascii=False,
        ),
        flush=True,
    )
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _mean(values):
    return sum(values) / len(values) if values else None


def _round(value):
    return None if value is None else round(value, 6)


def build_target_reliability_report(ledger_a, ledger_b):
    frame = load_json(DEFAULT_FRAME)
    codebook = load_json(DEFAULT_CODEBOOK)
    errors_a = validate_target_ledger(ledger_a, frame, codebook, require_complete=True)
    errors_b = validate_target_ledger(ledger_b, frame, codebook, require_complete=True)
    distinct = ledger_a.get("coder_pseudonym") != ledger_b.get("coder_pseudonym")
    slots = _frame_slots_by_id(frame)
    entries_a = ledger_a.get("entries") if isinstance(ledger_a.get("entries"), dict) else {}
    entries_b = ledger_b.get("entries") if isinstance(ledger_b.get("entries"), dict) else {}
    paired = sorted(set(entries_a) & set(entries_b))
    status_pairs = [
        (entries_a[slot]["slot_status"], entries_b[slot]["slot_status"])
        for slot in paired
    ]
    jointly_selected = [
        slot
        for slot in paired
        if entries_a[slot]["slot_status"] == "selected_event"
        and entries_b[slot]["slot_status"] == "selected_event"
    ]
    ious = [
        temporal_iou(
            entries_a[slot]["timestamp_locator_start_seconds"],
            entries_a[slot]["timestamp_locator_end_seconds"],
            entries_b[slot]["timestamp_locator_start_seconds"],
            entries_b[slot]["timestamp_locator_end_seconds"],
        )
        for slot in jointly_selected
    ]
    nominal_alpha = {}
    for field in codebook["reliability_contract"]["nominal_krippendorff_alpha_fields"]:
        nominal_alpha[field] = _round(
            nominal_krippendorff_alpha(
                [(entries_a[slot].get(field), entries_b[slot].get(field)) for slot in jointly_selected]
            )
        )
    secondary_alpha = {}
    for dimension in codebook["dimensions"]:
        secondary_alpha[dimension] = _round(
            nominal_krippendorff_alpha(
                [
                    (
                        dimension in entries_a[slot].get("secondary_dimensions", []),
                        dimension in entries_b[slot].get("secondary_dimensions", []),
                    )
                    for slot in jointly_selected
                ]
            )
        )
    complete = not errors_a and not errors_b and len(entries_a) == len(slots) == len(entries_b)
    alpha_gate = bool(nominal_alpha) and all(
        value is not None
        and value >= codebook["reliability_contract"]["nominal_alpha_tentative_min"]
        for value in nominal_alpha.values()
    )
    mean_iou = _mean([value for value in ious if value is not None])
    iou_gate = (
        mean_iou is not None
        and mean_iou >= codebook["reliability_contract"]["temporal_iou_project_gate_min"]
    )
    passed = complete and distinct and alpha_gate and iou_gate
    return {
        "schema": "uruha_public_persona_target_calibration_coding_reliability_v9",
        "experiment_id": EXPERIMENT_ID,
        "contains_event_text": False,
        "contains_model_output": False,
        "persona_score_computed": False,
        "completion": {
            "expected_slot_count_per_coder": len(slots),
            "coder_a_entry_count": len(entries_a),
            "coder_b_entry_count": len(entries_b),
            "paired_slot_count": len(paired),
            "jointly_selected_event_count": len(jointly_selected),
        },
        "unitizing_reliability": {
            "slot_status_percent_agreement": _round(
                _mean([left == right for left, right in status_pairs])
            ),
            "joint_selected_temporal_iou_mean": _round(mean_iou),
            "joint_selected_temporal_iou_count": len(ious),
        },
        "nominal_reliability": {
            "krippendorff_alpha": nominal_alpha,
            "secondary_dimension_binary_krippendorff_alpha": secondary_alpha,
        },
        "gates": {
            "both_ledgers_complete_and_valid": complete,
            "coder_pseudonyms_distinct": distinct,
            "temporal_iou_gate_passed": iou_gate,
            "all_primary_nominal_alpha_at_least_tentative": alpha_gate,
            "target_calibration_reliability_passed": passed,
            "aggregate_target_profile_authorized": passed,
            "persona_similarity_comparison_authorized": False,
            "model_execution_authorized": False,
        },
        "validation": {
            "coder_a_errors": errors_a,
            "coder_b_errors": errors_b,
        },
        "evidence_boundary": (
            "A pass would authorize only an aggregate target calibration behavior profile. "
            "It would not be a persona-similarity result and would not authorize model "
            "execution, final holdout review, training, or a public-persona claim."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--overwrite", action="store_true")
    build_parser.add_argument("--require-pass", action="store_true")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--coder", required=True)
    init_parser.add_argument("--ledger", required=True)
    init_parser.add_argument(
        "--authorization-lock", default=str(DEFAULT_FUTURE_V7_RELIABILITY_LOCK)
    )
    init_parser.add_argument("--overwrite", action="store_true")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--coder", required=True)
    serve_parser.add_argument("--ledger", required=True)
    serve_parser.add_argument("--port", type=int, default=7867)
    serve_parser.add_argument(
        "--authorization-lock", default=str(DEFAULT_FUTURE_V7_RELIABILITY_LOCK)
    )
    serve_parser.add_argument("--open-browser", action="store_true")

    reliability_parser = subparsers.add_parser("reliability")
    reliability_parser.add_argument("--ledger-a", required=True)
    reliability_parser.add_argument("--ledger-b", required=True)
    reliability_parser.add_argument("--output", required=True)
    reliability_parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    if args.command == "build":
        frame = build_sampling_frame(
            load_json(DEFAULT_PREREGISTRATION), load_json(DEFAULT_SOURCE_METADATA)
        )
        _write_text(
            DEFAULT_FRAME,
            json.dumps(frame, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
        report = build_construction_audit_from_paths()
        _write_text(
            DEFAULT_CONSTRUCTION_JSON,
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
        _write_text(
            DEFAULT_CONSTRUCTION_MD,
            build_construction_markdown(report),
            args.overwrite,
        )
        print(
            json.dumps(
                {
                    "construction_passed": report["construction_passed"],
                    "checks": f"{report['summary']['check_pass_count']}/{report['summary']['check_count']}",
                    "sampling_slots": report["summary"]["sampling_slot_count"],
                    "target_human_coding_now": report["authorizations"]["target_human_coding_now"],
                    "decision": report["decision"],
                },
                ensure_ascii=False,
            )
        )
        if args.require_pass and not report["construction_passed"]:
            raise SystemExit(1)
        return
    if args.command == "init":
        path, ledger = initialize_target_ledger(
            args.coder,
            args.ledger,
            args.authorization_lock,
            overwrite=args.overwrite,
        )
        print(json.dumps({"ledger": str(path), "coder": ledger["coder_pseudonym"]}))
        return
    if args.command == "serve":
        serve_target(
            args.ledger,
            args.coder,
            args.port,
            args.open_browser,
            args.authorization_lock,
        )
        return
    if args.command == "reliability":
        ledger_a = load_json(resolve_private_path(args.ledger_a, DEFAULT_PRIVATE_ROOT))
        ledger_b = load_json(resolve_private_path(args.ledger_b, DEFAULT_PRIVATE_ROOT))
        report = build_target_reliability_report(ledger_a, ledger_b)
        output = resolve_private_path(args.output, DEFAULT_PRIVATE_ROOT)
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {output}")
        _atomic_write_json(output, report)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "target_calibration_reliability_passed": report["gates"][
                        "target_calibration_reliability_passed"
                    ],
                }
            )
        )


if __name__ == "__main__":
    main()
