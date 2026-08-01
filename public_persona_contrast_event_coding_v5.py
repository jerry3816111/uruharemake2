#!/usr/bin/env python3
"""Freeze and audit contrast-persona event-sampling slots before content review."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_preregistration.json"
)
DEFAULT_METHOD_REGISTRY = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_method_registry.json"
)
DEFAULT_V4_RESULT = (
    ROOT / "configs/public_persona_contrast_source_manifest_v4_result_lock.json"
)
DEFAULT_CONTRAST_MANIFEST = (
    ROOT / "datasets/public_persona_contrast_source_manifest_v4.json"
)
DEFAULT_EVENT_SCHEMA = ROOT / "configs/public_persona_event_coding_schema_v1.json"
DEFAULT_RIGHTS_V1 = (
    ROOT / "datasets/public_persona_contrast_source_rights_review_v1.json"
)
DEFAULT_RIGHTS_V2 = (
    ROOT / "datasets/public_persona_contrast_source_rights_review_v2.json"
)
DEFAULT_READINESS = (
    ROOT / "datasets/public_persona_fidelity_eval_v2_readiness_inventory.json"
)
DEFAULT_FRAME = (
    ROOT / "datasets/public_persona_contrast_event_sampling_frame_v5.json"
)
DEFAULT_OUTPUT_JSON = (
    ROOT / "reports/public_persona_contrast_event_coding_v5_audit.json"
)
DEFAULT_OUTPUT_MD = (
    ROOT / "reports/public_persona_contrast_event_coding_v5_audit.md"
)
DEFAULT_GITIGNORE = ROOT / ".gitignore"

EXPERIMENT_ID = "public_persona_contrast_event_coding_v5"
TARGET_ID = "ichinose_uruha_public_persona"
V4_REQUIRED_DECISION = "authorize_contrast_event_coding_preregistration_only"
PASS_DECISION = "authorize_bounded_manual_contrast_event_coding_only"
FAIL_DECISION = (
    "repair_contrast_event_coding_protocol_before_any_behavior_content_review"
)
PRIVATE_EVENT_DIRECTORY = "analysis/local_public_persona_contrast_coding_v5/"
EXPECTED_DIMENSIONS = [
    "situation_interpretation_and_response_stance",
    "dialogue_act_social_distance_and_relationship_response",
    "wording_rhythm_directness_humor_and_affect",
    "publicly_observable_preferences_values_and_action_choices",
    "memory_selection_experience_update_and_reflection",
    "uncertainty_private_information_and_unsupported_claim_restraint",
]
EXPECTED_METHOD_SOURCE_IDS = {
    "youtube_terms_contrast_coding_v5_20260801",
    "youtube_copyright_contrast_coding_v5_20260801",
    "vspo_guideline_contrast_coding_v5_20260801",
    "krippendorff_unitizing_1995",
    "lombard_intercoder_reliability_2002",
    "hayes_krippendorff_alpha_2007",
    "riffe_stratified_sampling_1996",
}
PROHIBITED_PAYLOAD_KEYS = {
    "title",
    "description",
    "raw_text",
    "raw_source_text",
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


def _resolve_input_path(path, root):
    path = Path(path)
    return path if path.is_absolute() else Path(root) / path


def _binding_valid(binding, root):
    if not isinstance(binding, dict):
        return False
    relative_path = str(binding.get("path") or "")
    expected_hash = str(binding.get("sha256") or "")
    path = Path(root) / relative_path
    return (
        bool(relative_path)
        and len(expected_hash) == 64
        and path.is_file()
        and sha256_file(path) == expected_hash
    )


def _is_nonnegative_integer(value):
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _find_prohibited_keys(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in PROHIBITED_PAYLOAD_KEYS:
                found.append(path)
            found.extend(_find_prohibited_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_prohibited_keys(child, f"{prefix}[{index}]"))
    return found


def _sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _uint64_from_digest(digest):
    return int.from_bytes(bytes.fromhex(digest[:16]), byteorder="big")


def build_sampling_frame(
    preregistration,
    contrast_manifest,
    root=ROOT,
    preregistration_path=DEFAULT_PREREGISTRATION,
    contrast_manifest_path=DEFAULT_CONTRAST_MANIFEST,
):
    preregistration_path = _resolve_input_path(preregistration_path, root)
    contrast_manifest_path = _resolve_input_path(contrast_manifest_path, root)
    slots = []
    for source in sorted(
        contrast_manifest.get("sources") or [], key=lambda row: row["source_id"]
    ):
        duration = int(source["duration_seconds"])
        for slot_index in range(1, 11):
            start = duration * (slot_index - 1) // 10
            end = duration * slot_index // 10
            width = end - start
            seed_material = (
                f"{EXPERIMENT_ID}|{source['source_partition_key']}|{slot_index}"
            )
            seed_sha256 = _sha256_text(seed_material)
            search_start = start + (_uint64_from_digest(seed_sha256) % width)
            slot_id = f"{source['source_id']}_slot_{slot_index:02d}"
            review_order_sha256 = _sha256_text(
                f"{EXPERIMENT_ID}|{slot_id}|global_review_order"
            )
            slots.append(
                {
                    "sampling_slot_id": slot_id,
                    "source_id": source["source_id"],
                    "actor_id": source["actor_id"],
                    "source_partition_key": source["source_partition_key"],
                    "topic_cell": source["topic_cell"],
                    "match_granularity": source["match_granularity"],
                    "source_duration_seconds": duration,
                    "slot_index": slot_index,
                    "stratum_start_seconds": start,
                    "stratum_end_exclusive_seconds": end,
                    "search_start_seconds": search_start,
                    "selection_seed_sha256": seed_sha256,
                    "review_order_sha256": review_order_sha256,
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
        "schema": "uruha_public_persona_contrast_event_sampling_frame_v5",
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen_empty_sampling_frame_before_behavior_content_review",
        "generated_at": "2026-08-01",
        "target_id": TARGET_ID,
        "preregistration_binding": {
            "path": _display_path(preregistration_path),
            "sha256": sha256_file(preregistration_path),
        },
        "contrast_manifest_binding": {
            "path": _display_path(contrast_manifest_path),
            "sha256": sha256_file(contrast_manifest_path),
        },
        "sampling_algorithm": {
            "temporal_strata_per_source": 10,
            "strata_are_search_regions_not_event_units": True,
            "event_selection_rule": "first eligible complete event at or after search_start_seconds",
            "no_eligible_event_replacement_allowed": False,
            "overlap_blocked_slot_replacement_allowed": False,
            "fixed_duration_event_chunking": False,
        },
        "sampling_slots": slots,
        "current_counts": {
            "sampling_slot_count": len(slots),
            "content_reviewed_source_count": 0,
            "selected_event_count": 0,
            "coded_event_count": 0,
            "independently_reviewed_event_count": 0,
            "same_topic_reference_pair_count": 0,
            "raw_or_verbatim_record_count": 0,
            "model_output_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "model_call_count": 0,
        },
        "content_boundary": {
            "behavior_content_reviewed": False,
            "event_boundaries_selected": False,
            "event_codes_available": False,
            "researcher_paraphrase_available": False,
            "raw_or_verbatim_content_available": False,
            "model_output_available": False,
            "persona_score_available": False,
            "private_event_registry_git_tracked": False,
        },
    }


def _validate_dependencies(
    preregistration,
    method_registry,
    v4_result,
    contrast_manifest,
    event_schema,
    rights_v1,
    root,
    violations,
):
    dependencies = preregistration.get("depends_on") or {}
    expected_paths = {
        "v4_result_lock": "configs/public_persona_contrast_source_manifest_v4_result_lock.json",
        "contrast_source_manifest": "datasets/public_persona_contrast_source_manifest_v4.json",
        "shared_event_schema": "configs/public_persona_event_coding_schema_v1.json",
        "v4_rights_review": "datasets/public_persona_contrast_source_rights_review_v1.json",
        "method_registry": "configs/public_persona_contrast_event_coding_v5_method_registry.json",
    }
    for name, path in expected_paths.items():
        binding = dependencies.get(name)
        if not _binding_valid(binding, root):
            violations["dependency"].append(f"{name}:binding")
        if (binding or {}).get("path") != path:
            violations["dependency"].append(f"{name}:path")
    if (dependencies.get("v4_result_lock") or {}).get(
        "required_decision"
    ) != V4_REQUIRED_DECISION:
        violations["dependency"].append("v4_required_decision")
    if v4_result.get("decision") != V4_REQUIRED_DECISION:
        violations["dependency"].append("v4_result_decision")
    if v4_result.get("protocol_passed") is not True:
        violations["dependency"].append("v4_protocol_passed")
    if (v4_result.get("authorizations") or {}).get(
        "contrast_event_coding_preregistration"
    ) is not True:
        violations["dependency"].append("v4_authorization")
    if contrast_manifest.get("status") != (
        "metadata_only_contrast_source_reservations_no_behavior_labels"
    ):
        violations["dependency"].append("contrast_manifest_status")
    if event_schema.get("status") != "protocol_only_no_behavior_events_reviewed":
        violations["dependency"].append("event_schema_status")
    if event_schema.get("construct", {}).get("dimensions") != EXPECTED_DIMENSIONS:
        violations["dependency"].append("shared_dimensions")
    if rights_v1.get("status") != (
        "metadata_locators_reviewed_behavior_use_not_authorized"
    ):
        violations["dependency"].append("rights_v1_status")
    source_ids = {row.get("source_id") for row in method_registry.get("sources") or []}
    if source_ids != EXPECTED_METHOD_SOURCE_IDS:
        violations["method"].append("source_ids")


def _validate_preregistration(preregistration, violations):
    if preregistration.get("schema") != (
        "uruha_public_persona_contrast_event_coding_preregistration_v5"
    ):
        violations["preregistration"].append("schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations["preregistration"].append("experiment_id")
    if preregistration.get("target_id") != TARGET_ID:
        violations["preregistration"].append("target_id")
    for field in ("current_problem", "falsifiable_hypothesis", "single_changed_variable"):
        if not str(preregistration.get(field) or "").strip():
            violations["preregistration"].append(field)
    sampling = preregistration.get("sampling_contract") or {}
    expected_values = {
        "source_count_exact": 9,
        "temporal_strata_per_source_exact": 10,
        "sampling_slot_count_exact": 90,
        "one_search_start_per_stratum": True,
        "first_eligible_event_at_or_after_search_start_required": True,
        "event_start_must_fall_inside_assigned_stratum": True,
        "event_end_may_cross_stratum_boundary_to_preserve_complete_unit": True,
        "overlap_with_prior_selected_event_blocks_slot_without_replacement": True,
        "no_eligible_event_is_retained_not_replaced": True,
        "fixed_duration_strata_are_search_regions_not_event_units": True,
        "convenience_sampling_forbidden": True,
        "selection_by_expected_similarity_or_difference_forbidden": True,
        "selection_by_memorable_quote_or_language_style_forbidden": True,
        "source_or_slot_replacement_after_content_review_forbidden": True,
        "exact_game_and_broad_family_results_separate": True,
        "stratum_boundary_algorithm": "floor(duration_seconds * boundary_index / 10)",
        "search_start_algorithm": "stratum_start + uint64_be(sha256(experiment_id|source_partition_key|slot_index)[0:8]) mod stratum_width",
        "global_review_order_algorithm": "ascending sha256(experiment_id|sampling_slot_id|global_review_order)",
    }
    for field, expected in expected_values.items():
        if sampling.get(field) != expected:
            violations["sampling_contract"].append(field)
    eligibility = preregistration.get("event_eligibility_contract") or {}
    expected_eligibility_fields = {
        "shared_observation_unit_schema_required",
        "focal_actor_has_publicly_observable_speech_or_action",
        "observable_trigger_context_and_completed_response_required",
        "enough_context_to_code_without_private_motive_inference_required",
        "same_reaction_may_not_be_split_into_multiple_events",
        "non_observation_is_not_negative_evidence",
        "private_or_sensitive_information_event_is_policy_excluded_without_paraphrase",
        "unclear_focal_speaker_is_ineligible",
        "pure_waiting_screen_or_technical_interruption_is_ineligible",
        "scripted_or_verbatim_reading_without_spontaneous_response_is_ineligible",
        "event_can_be_rejected_only_by_frozen_eligibility_rule",
    }
    if set(eligibility) != expected_eligibility_fields:
        violations["eligibility"].append("field_set")
    for field in sorted(expected_eligibility_fields):
        if eligibility.get(field) is not True:
            violations["eligibility"].append(field)
    coding = preregistration.get("coding_contract") or {}
    if coding.get("construct") != "public_observable_persona_fidelity":
        violations["coding"].append("construct")
    if coding.get("shared_dimension_count_exact") != 6:
        violations["coding"].append("dimension_count")
    for field in (
        "shared_schema_hash_required",
        "researcher_paraphrase_only",
        "actor_identity_nonblinding_must_be_reported",
        "coder_and_reviewer_pseudonyms_distinct",
        "both_roles_independently_select_event_boundaries_and_codes_before_comparison",
    ):
        if coding.get(field) is not True:
            violations["coding"].append(field)
    for field in (
        "copied_quote_allowed",
        "raw_media_audio_image_caption_comment_or_transcript_allowed",
        "private_state_or_performer_identity_inference_allowed",
        "actor_identity_blinding_feasible",
        "system_output_persona_score_and_target_hypothesis_visible_to_coders",
        "unfavorable_ambiguous_or_disagreeing_records_may_be_deleted_to_raise_similarity",
        "adjudication_may_not_replace_pre_adjudication_reliability_data",
    ):
        expected = field == "adjudication_may_not_replace_pre_adjudication_reliability_data"
        if coding.get(field) is not expected:
            violations["coding"].append(field)
    reliability = preregistration.get("reliability_contract") or {}
    if reliability.get("independent_review_fraction_required") != 1.0:
        violations["reliability"].append("independent_review_fraction")
    if reliability.get("nominal_alpha_reliable_min") != 0.8:
        violations["reliability"].append("alpha_reliable_min")
    if reliability.get("nominal_alpha_tentative_min") != 0.667:
        violations["reliability"].append("alpha_tentative_min")
    if reliability.get("temporal_iou_project_gate_min") != 0.5:
        violations["reliability"].append("temporal_iou_gate")
    for field in (
        "slot_selection_agreement_reported",
        "temporal_intersection_over_union_reported",
        "unitizing_reliability_reported_separately",
        "nominal_code_krippendorff_alpha_primary",
        "percent_agreement_secondary_only",
        "below_tentative_alpha_blocks_persona_comparison",
        "failed_reliability_requires_codebook_revision_with_original_labels_preserved",
        "adjudicated_labels_excluded_from_reliability_estimate",
    ):
        if reliability.get(field) is not True:
            violations["reliability"].append(field)


def _validate_data_and_authorization(preregistration, gitignore_text, violations):
    handling = preregistration.get("data_handling_contract") or {}
    if handling.get("event_level_registry_path") != (
        PRIVATE_EVENT_DIRECTORY + "contrast_events.jsonl"
    ):
        violations["data_boundary"].append("private_registry_path")
    if PRIVATE_EVENT_DIRECTORY not in gitignore_text.splitlines():
        violations["data_boundary"].append("private_registry_not_gitignored")
    for field in (
        "manual_in_service_viewing_only",
        "timestamp_locator_and_codes_stored_in_restricted_local_registry",
    ):
        if handling.get(field) is not True:
            violations["data_boundary"].append(field)
    for field in (
        "automated_collection_or_download",
        "event_level_registry_git_tracked",
        "event_level_paraphrase_publication",
        "prompt_memory_retrieval_training_or_model_selection_use",
        "raw_content_redistribution",
        "rights_holder_license_claimed",
        "legal_opinion_claimed",
        "public_impersonation_or_official_affiliation_claimed",
    ):
        if handling.get(field) is not False:
            violations["data_boundary"].append(field)
    if handling.get("public_outputs") != [
        "empty_sampling_frame",
        "protocol_and_codebook",
        "source_level_counts",
        "aggregate_reliability",
        "aggregate_behavior_profile",
    ]:
        violations["data_boundary"].append("public_outputs")
    if preregistration.get("expected_counts_after_protocol_pass") != {
        "sampling_slot_count": 90,
        "content_reviewed_source_count": 0,
        "selected_event_count": 0,
        "coded_event_count": 0,
        "independently_reviewed_event_count": 0,
        "same_topic_reference_pair_count": 0,
        "raw_or_verbatim_record_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
        "model_call_count": 0,
    }:
        violations["count_honesty"].append("preregistered_expected_counts")
    if preregistration.get("expected_formal_readiness") != {
        "pass_count": 4,
        "check_count": 19,
        "formal_execution_ready": False,
    }:
        violations["readiness"].append("preregistered_expected_readiness")
    policy = preregistration.get("decision_policy") or {}
    if policy.get("protocol_pass") != PASS_DECISION:
        violations["authorization"].append("protocol_pass")
    if policy.get("protocol_fail") != FAIL_DECISION:
        violations["authorization"].append("protocol_fail")
    if policy.get("manual_contrast_behavior_observation") is not True:
        violations["authorization"].append("manual_observation")
    if policy.get("restricted_researcher_paraphrase_storage") is not True:
        violations["authorization"].append("restricted_paraphrase")
    for field, expected in (
        ("maximum_source_count", 9),
        ("maximum_sampling_slot_count", 90),
        ("maximum_accepted_event_count", 90),
    ):
        if policy.get(field) != expected:
            violations["authorization"].append(field)
    for field in (
        "public_event_level_content_storage",
        "target_calibration_behavior_coding",
        "rater_recruitment",
        "rating_collection",
        "model_execution",
        "runtime_change",
        "prompt_change",
        "memory_change",
        "model_training",
        "sealed_holdout_unsealing",
        "formal_persona_scoring",
        "public_persona_fidelity_claim",
        "private_person_copy_claim",
    ):
        if policy.get(field) is not False:
            violations["authorization"].append(field)


def _validate_method_registry(method_registry, violations):
    if method_registry.get("schema") != (
        "uruha_public_persona_contrast_event_coding_method_registry_v5"
    ):
        violations["method"].append("schema")
    if method_registry.get("experiment_id") != EXPERIMENT_ID:
        violations["method"].append("experiment_id")
    commitments = method_registry.get("method_commitments") or {}
    if not commitments or any(value is not True for value in commitments.values()):
        violations["method"].append("method_commitments")
    sources = method_registry.get("sources") or []
    if len(sources) != 7:
        violations["method"].append("source_count")
    for row in sources:
        if row.get("authority") not in {
            "platform_official",
            "agency_official",
            "primary_research_paper",
        }:
            violations["method"].append(f"{row.get('source_id')}:authority")
        if not str(row.get("url") or "").startswith("https://"):
            violations["method"].append(f"{row.get('source_id')}:url")


def _validate_rights_v2(rights_v2, rights_v1, preregistration, root, violations):
    if rights_v2.get("schema") != (
        "uruha_public_persona_contrast_source_rights_review_v2"
    ):
        violations["rights"].append("schema")
    if not _binding_valid(rights_v2.get("prior_review_binding"), root):
        violations["rights"].append("prior_review_binding")
    if not _binding_valid(rights_v2.get("coding_preregistration_binding"), root):
        violations["rights"].append("preregistration_binding")
    reviews = rights_v2.get("source_reviews") or []
    v1_ids = {row.get("source_id") for row in rights_v1.get("source_reviews") or []}
    review_ids = {row.get("source_id") for row in reviews}
    if len(reviews) != 9 or review_ids != v1_ids:
        violations["rights"].append("source_review_set")
    if any(
        row.get("conditional_disposition")
        != "bounded_manual_observation_after_v5_protocol_pass"
        for row in reviews
    ):
        violations["rights"].append("conditional_disposition")
    policy = rights_v2.get("review_policy") or {}
    for field in (
        "public_access_is_not_training_permission",
        "public_access_is_not_a_rights_holder_license",
        "in_service_manual_viewing_after_protocol_pass",
        "bounded_researcher_behavior_paraphrase_in_restricted_local_registry",
        "timestamp_locator_and_categorical_code_in_restricted_local_registry",
        "metadata_locator_storage",
    ):
        if policy.get(field) is not True:
            violations["rights"].append(field)
    for field in (
        "public_event_level_paraphrase_or_quote_storage",
        "raw_media_audio_image_storage",
        "caption_comment_or_transcript_storage",
        "automated_bulk_collection_or_download",
        "model_training",
        "prompt_memory_retrieval_or_model_selection_use",
        "runtime_persona_activation",
        "public_source_content_redistribution",
        "official_affiliation_or_impersonation_claim",
        "legal_opinion_claimed",
        "rights_holder_permission_claimed",
    ):
        if policy.get(field) is not False:
            violations["rights"].append(field)
    completion = rights_v2.get("review_completion") or {}
    expected_zero = (
        "behavior_content_reviewed_count",
        "raw_or_verbatim_record_count",
    )
    if any(completion.get(field) != 0 for field in expected_zero):
        violations["rights"].append("review_completion_counts")
    if completion.get("formal_corpus_rights_review_complete") is not False:
        violations["rights"].append("formal_rights_completion")


def _validate_frame(frame, expected_frame, violations):
    if frame != expected_frame:
        violations["sampling_frame"].append("does_not_match_rebuilt_frame")
    slots = frame.get("sampling_slots") or []
    if len(slots) != 90:
        violations["sampling_frame"].append("slot_count")
    source_counts = Counter(row.get("source_id") for row in slots)
    if source_counts and set(source_counts.values()) != {10}:
        violations["sampling_frame"].append("slots_per_source")
    orders = [row.get("global_review_order") for row in slots]
    if sorted(orders) != list(range(1, 91)):
        violations["sampling_frame"].append("global_review_order")
    for row in slots:
        start = row.get("stratum_start_seconds")
        end = row.get("stratum_end_exclusive_seconds")
        search = row.get("search_start_seconds")
        if not all(isinstance(value, int) for value in (start, end, search)):
            violations["sampling_frame"].append("noninteger_time")
            continue
        if not (start <= search < end):
            violations["sampling_frame"].append(
                f"{row.get('sampling_slot_id')}:search_bounds"
            )
        if row.get("slot_status") != "unreviewed_no_content_access":
            violations["content_boundary"].append(
                f"{row.get('sampling_slot_id')}:slot_status"
            )
    counts = frame.get("current_counts") or {}
    expected_counts = {
        "sampling_slot_count": 90,
        "content_reviewed_source_count": 0,
        "selected_event_count": 0,
        "coded_event_count": 0,
        "independently_reviewed_event_count": 0,
        "same_topic_reference_pair_count": 0,
        "raw_or_verbatim_record_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
        "model_call_count": 0,
    }
    if counts != expected_counts:
        violations["count_honesty"].append("frame_current_counts")
    if any(not _is_nonnegative_integer(value) for value in counts.values()):
        violations["count_honesty"].append("nonnegative_integer_counts")
    content = frame.get("content_boundary") or {}
    if not content or any(value is not False for value in content.values()):
        violations["content_boundary"].append("frame_content_boundary")
    prohibited = _find_prohibited_keys(frame)
    if prohibited:
        violations["content_boundary"].extend(prohibited)


def audit(
    preregistration,
    method_registry,
    v4_result,
    contrast_manifest,
    event_schema,
    rights_v1,
    rights_v2,
    readiness,
    frame,
    gitignore_text,
    root=ROOT,
    preregistration_path=DEFAULT_PREREGISTRATION,
    contrast_manifest_path=DEFAULT_CONTRAST_MANIFEST,
):
    violations = defaultdict(list)
    _validate_dependencies(
        preregistration,
        method_registry,
        v4_result,
        contrast_manifest,
        event_schema,
        rights_v1,
        root,
        violations,
    )
    _validate_preregistration(preregistration, violations)
    _validate_data_and_authorization(preregistration, gitignore_text, violations)
    _validate_method_registry(method_registry, violations)
    _validate_rights_v2(rights_v2, rights_v1, preregistration, root, violations)
    expected_frame = build_sampling_frame(
        preregistration,
        contrast_manifest,
        root=root,
        preregistration_path=preregistration_path,
        contrast_manifest_path=contrast_manifest_path,
    )
    _validate_frame(frame, expected_frame, violations)
    readiness_counts = readiness.get("counts") or {}
    if readiness_counts.get("contrast_event_count_per_person_min") != 0:
        violations["readiness"].append("contrast_event_count")
    if readiness_counts.get("same_topic_reference_pair_count") != 0:
        violations["readiness"].append("same_topic_reference_pair_count")
    if (readiness.get("flags") or {}).get("formal_execution_ready") is not False:
        violations["readiness"].append("formal_execution_ready")
    protocol_checks = {
        "v4_authorization_and_dependencies_are_hash_bound": not violations[
            "dependency"
        ],
        "preregistration_is_falsifiable_and_single_variable": not violations[
            "preregistration"
        ],
        "nine_sources_have_ten_frozen_search_slots_each": not violations[
            "sampling_frame"
        ],
        "search_starts_and_global_order_rebuild_exactly": not violations[
            "sampling_frame"
        ],
        "strata_are_not_mislabeled_as_behavior_events": not violations[
            "sampling_contract"
        ],
        "convenience_similarity_and_quote_selection_are_forbidden": not violations[
            "sampling_contract"
        ],
        "event_eligibility_and_complete_unit_rules_are_frozen": not violations[
            "eligibility"
        ],
        "shared_six_dimension_coding_and_nonblinding_are_explicit": not violations[
            "coding"
        ],
        "independent_unitizing_and_chance_corrected_reliability_are_required": not violations[
            "reliability"
        ],
        "seven_official_or_primary_method_sources_are_registered": not violations[
            "method"
        ],
        "nine_sources_have_conditional_conservative_rights_review": not violations[
            "rights"
        ],
        "event_level_records_are_restricted_and_gitignored": not violations[
            "data_boundary"
        ],
        "no_content_event_output_score_or_model_call_exists": not violations[
            "content_boundary"
        ]
        and not violations["count_honesty"],
        "formal_readiness_remains_four_of_nineteen": not violations["readiness"],
        "authorization_is_limited_to_bounded_manual_contrast_coding": not violations[
            "authorization"
        ],
    }
    protocol_passed = all(protocol_checks.values())
    decision = PASS_DECISION if protocol_passed else FAIL_DECISION
    compact_violations = {
        key: values for key, values in sorted(violations.items()) if values
    }
    slots = frame.get("sampling_slots") or []
    counts = frame.get("current_counts") or {}
    match_counts = Counter(row.get("match_granularity") for row in slots)
    return {
        "schema": "uruha_public_persona_contrast_event_coding_audit_v5",
        "experiment_id": EXPERIMENT_ID,
        "target_id": TARGET_ID,
        "protocol_passed": protocol_passed,
        "formal_execution_ready": False,
        "persona_score_computed": False,
        "decision": decision,
        "summary": {
            "protocol_check_count": len(protocol_checks),
            "protocol_check_pass_count": sum(protocol_checks.values()),
            "formal_readiness_check_count": 19,
            "formal_readiness_pass_count": 4,
            "method_source_count": len(method_registry.get("sources") or []),
            "contrast_source_count": len(
                {row.get("source_id") for row in slots if row.get("source_id")}
            ),
            "sampling_slot_count": len(slots),
            "exact_game_sampling_slot_count": match_counts["exact_game"],
            "broad_family_sampling_slot_count": match_counts[
                "broad_family_only"
            ],
            "content_reviewed_source_count": counts.get(
                "content_reviewed_source_count"
            ),
            "selected_event_count": counts.get("selected_event_count"),
            "coded_event_count": counts.get("coded_event_count"),
            "independently_reviewed_event_count": counts.get(
                "independently_reviewed_event_count"
            ),
            "same_topic_reference_pair_count": counts.get(
                "same_topic_reference_pair_count"
            ),
            "raw_or_verbatim_record_count": counts.get(
                "raw_or_verbatim_record_count"
            ),
            "model_output_count": counts.get("model_output_count"),
            "persona_score_count": counts.get("persona_score_count"),
            "holdout_content_review_count": counts.get(
                "holdout_content_review_count"
            ),
            "model_call_count": counts.get("model_call_count"),
        },
        "protocol_checks": protocol_checks,
        "violations": compact_violations,
        "sampling_design": {
            "source_count": 9,
            "strata_per_source": 10,
            "slot_count": 90,
            "selection_rule": "first eligible complete event at or after each frozen search start",
            "replacement_after_no_eligible_or_overlap_blocked_allowed": False,
            "event_is_fixed_duration_chunk": False,
            "actor_identity_blinding_feasible": False,
            "system_output_and_persona_score_visible_to_coders": False,
        },
        "reliability_gates": preregistration.get("reliability_contract"),
        "authorizations": {
            "bounded_manual_contrast_event_coding": protocol_passed,
            "maximum_source_count": 9 if protocol_passed else 0,
            "maximum_sampling_slot_count": 90 if protocol_passed else 0,
            "maximum_accepted_event_count": 90 if protocol_passed else 0,
            "restricted_local_researcher_paraphrase_storage": protocol_passed,
            "public_event_level_content_storage": False,
            "target_calibration_behavior_coding": False,
            "rater_recruitment": False,
            "rating_collection": False,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "memory_change": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
        "next_required_evidence": (
            "依 global_review_order 在受限本機帳本中進行雙人獨立事件選擇與編碼，保留 no-eligible、"
            "overlap-blocked、歧義與不利紀錄；在可靠度通過前不得建立人物距離或執行模型。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    design = report["sampling_design"]
    lines = [
        "# 公開人格相近人物事件編碼 V5 稽核",
        "",
        f"- 協定通過：`{report['protocol_passed']}` ({summary['protocol_check_pass_count']}/{summary['protocol_check_count']})",
        f"- 正式評測就緒：`{report['formal_execution_ready']}` ({summary['formal_readiness_pass_count']}/{summary['formal_readiness_check_count']})",
        f"- 決策：`{report['decision']}`",
        "",
        "## 先固定去哪裡找事件",
        "",
        "| 官方來源 | 每來源搜尋層 | 凍結搜尋槽 | 已觀看內容 | 已選事件 |",
        "|---:|---:|---:|---:|---:|",
        f"| {summary['contrast_source_count']} | {design['strata_per_source']} | {summary['sampling_slot_count']} | {summary['content_reviewed_source_count']} | {summary['selected_event_count']} |",
        "",
        "每個時間層只有一個由 SHA-256 決定的搜尋起點。編碼者只能選起點後第一個合格的完整事件；找不到、被前一事件重疊或結果不利，都不得換片段。",
        "",
        "## 搜尋層不是事件",
        "",
        "`十等分時間層 -> 雜湊搜尋起點 -> 第一個合格互動開始 -> 完整反應結束`",
        "",
        "時間層只決定從哪裡開始找；事件仍按情境、對象與完整反應切分，不能把固定秒數當成行為樣本。",
        "",
        "## 公平比較與可靠度",
        "",
        "| 同遊戲搜尋槽 | 同類型搜尋槽 | 雙人獨立覆核 | 人物身分盲化 | 系統輸出盲化 |",
        "|---:|---:|---|---|---|",
        f"| {summary['exact_game_sampling_slot_count']} | {summary['broad_family_sampling_slot_count']} | 全部事件 | 不可行，必須揭露 | 必須 |",
        "",
        "事件邊界與類別可靠度分開報告；名目類別以 Krippendorff's alpha 為主，單純百分比一致率只能當輔助。",
        "",
        "## 內容仍是零",
        "",
        "| 編碼事件 | 獨立覆核 | 模型回答 | 人格分數 | holdout 查看 | 模型呼叫 |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {summary['coded_event_count']} | {summary['independently_reviewed_event_count']} | {summary['model_output_count']} | {summary['persona_score_count']} | {summary['holdout_content_review_count']} | {summary['model_call_count']} |",
        "",
        "事件級時間戳、研究者摘要與類別只能放在已加入 `.gitignore` 的本機受限帳本，不進 Git；原影音、字幕、留言、逐字稿與原句一律不保存。",
        "",
        "## 下一步",
        "",
        report["next_required_evidence"],
        "",
        "## 證據邊界",
        "",
        report["evidence_boundary"],
        "",
    ]
    return "\n".join(lines)


def build_audit_from_paths(
    preregistration_path=DEFAULT_PREREGISTRATION,
    method_registry_path=DEFAULT_METHOD_REGISTRY,
    v4_result_path=DEFAULT_V4_RESULT,
    contrast_manifest_path=DEFAULT_CONTRAST_MANIFEST,
    event_schema_path=DEFAULT_EVENT_SCHEMA,
    rights_v1_path=DEFAULT_RIGHTS_V1,
    rights_v2_path=DEFAULT_RIGHTS_V2,
    readiness_path=DEFAULT_READINESS,
    frame_path=DEFAULT_FRAME,
    gitignore_path=DEFAULT_GITIGNORE,
):
    paths = {
        "preregistration": Path(preregistration_path),
        "method_registry": Path(method_registry_path),
        "v4_result_lock": Path(v4_result_path),
        "contrast_manifest": Path(contrast_manifest_path),
        "shared_event_schema": Path(event_schema_path),
        "rights_review_v1": Path(rights_v1_path),
        "rights_review_v2": Path(rights_v2_path),
        "readiness_inventory": Path(readiness_path),
        "sampling_frame": Path(frame_path),
    }
    gitignore = Path(gitignore_path)
    report = audit(
        load_json(paths["preregistration"]),
        load_json(paths["method_registry"]),
        load_json(paths["v4_result_lock"]),
        load_json(paths["contrast_manifest"]),
        load_json(paths["shared_event_schema"]),
        load_json(paths["rights_review_v1"]),
        load_json(paths["rights_review_v2"]),
        load_json(paths["readiness_inventory"]),
        load_json(paths["sampling_frame"]),
        gitignore.read_text(encoding="utf-8"),
        root=ROOT,
        preregistration_path=paths["preregistration"],
        contrast_manifest_path=paths["contrast_manifest"],
    )
    report["inputs"] = {
        key: {"path": _display_path(path), "sha256": sha256_file(path)}
        for key, path in paths.items()
    }
    report["workspace_guards"] = {
        "gitignore_path": _display_path(gitignore),
        "private_event_directory": PRIVATE_EVENT_DIRECTORY,
        "private_event_directory_is_gitignored": (
            PRIVATE_EVENT_DIRECTORY in gitignore.read_text(encoding="utf-8").splitlines()
        ),
    }
    return report


def _write_output(path, content, overwrite):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--method-registry", default=str(DEFAULT_METHOD_REGISTRY))
    parser.add_argument("--v4-result", default=str(DEFAULT_V4_RESULT))
    parser.add_argument("--contrast-manifest", default=str(DEFAULT_CONTRAST_MANIFEST))
    parser.add_argument("--event-schema", default=str(DEFAULT_EVENT_SCHEMA))
    parser.add_argument("--rights-v1", default=str(DEFAULT_RIGHTS_V1))
    parser.add_argument("--rights-v2", default=str(DEFAULT_RIGHTS_V2))
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS))
    parser.add_argument("--frame", default=str(DEFAULT_FRAME))
    parser.add_argument("--gitignore", default=str(DEFAULT_GITIGNORE))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--initialize-frame", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-protocol-pass", action="store_true")
    parser.add_argument("--require-execution-ready", action="store_true")
    args = parser.parse_args()
    if args.initialize_frame:
        frame = build_sampling_frame(
            load_json(args.preregistration),
            load_json(args.contrast_manifest),
            root=ROOT,
            preregistration_path=args.preregistration,
            contrast_manifest_path=args.contrast_manifest,
        )
        _write_output(
            args.frame,
            json.dumps(frame, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
    report = build_audit_from_paths(
        args.preregistration,
        args.method_registry,
        args.v4_result,
        args.contrast_manifest,
        args.event_schema,
        args.rights_v1,
        args.rights_v2,
        args.readiness,
        args.frame,
        args.gitignore,
    )
    _write_output(
        args.output_json,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        args.overwrite,
    )
    _write_output(args.output_md, build_markdown(report), args.overwrite)
    print(
        json.dumps(
            {
                "protocol_passed": report["protocol_passed"],
                "formal_execution_ready": report["formal_execution_ready"],
                "readiness": (
                    f"{report['summary']['formal_readiness_pass_count']}/"
                    f"{report['summary']['formal_readiness_check_count']}"
                ),
                "sampling_slots": report["summary"]["sampling_slot_count"],
                "decision": report["decision"],
            },
            ensure_ascii=False,
        )
    )
    if args.require_protocol_pass and not report["protocol_passed"]:
        raise SystemExit(1)
    if args.require_execution_ready and not report["formal_execution_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
