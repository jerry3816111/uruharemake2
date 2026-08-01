#!/usr/bin/env python3
"""Audit public-persona governance before behavior content is reviewed."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from public_persona_reference_manifest_v2 import (
    build_audit_from_paths as build_reference_audit_from_paths,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_precontent_governance_v3_preregistration.json"
)
DEFAULT_EVENT_SCHEMA = ROOT / "configs/public_persona_event_coding_schema_v1.json"
DEFAULT_RIGHTS_REVIEW = (
    ROOT / "datasets/public_persona_source_rights_review_v1.json"
)
DEFAULT_CONSENT = ROOT / "configs/public_persona_informed_consent_v1.json"
DEFAULT_METHOD_REGISTRY = (
    ROOT / "configs/public_persona_precontent_governance_v3_method_registry.json"
)
DEFAULT_SOURCE_MANIFEST = (
    ROOT / "datasets/public_persona_reference_source_manifest_v2.json"
)
DEFAULT_BLIND_PROTOCOL = (
    ROOT / "configs/public_persona_blind_rater_protocol_v1.json"
)
DEFAULT_READINESS = (
    ROOT / "datasets/public_persona_fidelity_eval_v2_readiness_inventory.json"
)
DEFAULT_V1_PREREGISTRATION = (
    ROOT / "configs/public_persona_fidelity_eval_v1_preregistration.json"
)
DEFAULT_V2_RESULT = (
    ROOT / "configs/public_persona_reference_manifest_v2_result_lock.json"
)
DEFAULT_OUTPUT_JSON = (
    ROOT / "reports/public_persona_precontent_governance_v3_audit.json"
)
DEFAULT_OUTPUT_MD = (
    ROOT / "reports/public_persona_precontent_governance_v3_audit.md"
)

EXPERIMENT_ID = "public_persona_precontent_governance_v3"
TARGET_ID = "ichinose_uruha_public_persona"
PASS_DECISION = (
    "authorize_bounded_calibration_event_coding_and_consent_usability_review_only"
)
FAIL_DECISION = (
    "repair_precontent_governance_before_any_behavior_coding_or_rater_contact"
)
V2_REQUIRED_DECISION = (
    "authorize_metadata_only_event_coding_preregistration_and_consent_form_review"
)

EXPECTED_CALIBRATION_IDS = {
    "uruha_calibration_youtube_valorant_20260318",
    "uruha_calibration_youtube_street_fighter_20250317",
    "uruha_calibration_youtube_farming_20250308",
}
EXPECTED_FINAL_IDS = {
    "uruha_youtube_forza_holdout_v2",
    "uruha_youtube_apex_team_holdout_v2",
    "uruha_final_holdout_youtube_apex_collab_20250206",
    "uruha_final_holdout_youtube_social_deduction_20210404",
}
EXPECTED_DIMENSIONS = {
    "situation_interpretation_and_response_stance",
    "dialogue_act_social_distance_and_relationship_response",
    "wording_rhythm_directness_humor_and_affect",
    "publicly_observable_preferences_values_and_action_choices",
    "memory_selection_experience_update_and_reflection",
    "uncertainty_private_information_and_unsupported_claim_restraint",
}
EXPECTED_STORED_RATER_FIELDS = {
    "pseudonymous_rater_id",
    "consent_version_hash",
    "eligibility_group",
    "familiarity_bracket",
    "item_id",
    "randomized_left_right_assignment",
    "rating_values",
    "optional_nonidentifying_reason_code",
}
EXPECTED_PROHIBITED_RATER_FIELDS = {
    "name",
    "email",
    "ip_address",
    "device_fingerprint",
    "social_account",
    "free_text_personal_history",
}
EXPECTED_RECORD_FIELDS = {
    "event_id",
    "source_id",
    "source_partition_key",
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
    "coder_pseudonym",
    "reviewer_pseudonym",
    "review_status",
    "coding_protocol_version_hash",
}
EXPECTED_FORBIDDEN_EVENT_FIELDS = {
    "raw_text",
    "raw_media",
    "transcript",
    "verbatim_transcript",
    "quote_text",
    "target_reply",
    "expected_reply",
    "reference_answer",
    "answer_key",
    "model_output",
    "training_text",
}
EXPECTED_METHOD_IDS = {
    "hhs_ohrp_informed_consent_faq_20260801",
    "hhs_ohrp_electronic_consent_qa_20260801",
    "japan_ppc_privacy_awareness_2026",
    "japan_ppc_public_information_warning_2024",
    "youtube_copyright_help_20260801",
    "youtube_terms_reference_v2_20260801",
    "vspo_guideline_reference_v2_20260801",
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


def _all_zero_nonnegative_integers(mapping):
    return bool(mapping) and all(
        not isinstance(value, bool) and isinstance(value, int) and value == 0
        for value in mapping.values()
    )


def _validate_dependency(preregistration, v2_result, root, violations):
    dependency = preregistration.get("depends_on") or {}
    if dependency.get("path") != (
        "configs/public_persona_reference_manifest_v2_result_lock.json"
    ):
        violations["dependency"].append("path")
    if not _binding_valid(dependency, root):
        violations["dependency"].append("hash_binding")
    if dependency.get("experiment_id") != "public_persona_reference_manifest_v2":
        violations["dependency"].append("experiment_id")
    if dependency.get("required_decision") != V2_REQUIRED_DECISION:
        violations["dependency"].append("required_decision")
    if v2_result.get("experiment_id") != "public_persona_reference_manifest_v2":
        violations["dependency"].append("result_experiment_id")
    if v2_result.get("decision") != V2_REQUIRED_DECISION:
        violations["dependency"].append("result_decision")
    if v2_result.get("protocol_passed") is not True:
        violations["dependency"].append("result_protocol_passed")


def _validate_goal(preregistration, violations):
    goal = preregistration.get("long_term_goal") or {}
    axes = set(goal.get("independent_evidence_axes") or [])
    if axes != {
        "general_cognitive_capability",
        "public_observable_persona_fidelity",
        "local_pc_latency_and_resource_feasibility",
        "Function_Calling_voice_and_VRM_action_safety",
    }:
        violations["goal"].append("independent_evidence_axes")
    exclusions = set(goal.get("success_is_not") or [])
    for required in (
        "private_person_identity_copy",
        "public_deception_or_impersonation",
        "benchmark_answer_memorization",
    ):
        if required not in exclusions:
            violations["goal"].append(f"missing_exclusion:{required}")
    if not str(goal.get("engineering_target") or "").strip():
        violations["goal"].append("engineering_target")
    if not str(goal.get("case_study_target") or "").strip():
        violations["goal"].append("case_study_target")


def _validate_event_schema(event_schema, source_manifest, v1_preregistration, root, violations):
    if event_schema.get("schema") != "uruha_public_persona_event_coding_schema_v1":
        violations["event_schema"].append("schema")
    if event_schema.get("target_id") != TARGET_ID:
        violations["event_schema"].append("target_id")
    if not _binding_valid(event_schema.get("source_manifest_binding"), root):
        violations["event_schema"].append("source_manifest_binding")

    sources = {row["source_id"]: row for row in source_manifest.get("sources") or []}
    derived_calibration = {
        source_id
        for source_id, row in sources.items()
        if row.get("source_role") == "calibration_reservation"
    }
    derived_final = {
        source_id
        for source_id, row in sources.items()
        if row.get("source_role") == "final_holdout_reservation"
    }
    phase = event_schema.get("initial_phase") or {}
    if set(phase.get("authorized_source_ids") or []) != EXPECTED_CALIBRATION_IDS:
        violations["event_schema"].append("authorized_source_ids")
    if derived_calibration != EXPECTED_CALIBRATION_IDS:
        violations["event_schema"].append("manifest_calibration_ids")
    if set(phase.get("forbidden_source_ids") or []) != EXPECTED_FINAL_IDS:
        violations["event_schema"].append("forbidden_source_ids")
    if derived_final != EXPECTED_FINAL_IDS:
        violations["event_schema"].append("manifest_final_ids")
    if phase.get("contrast_actor_content_coding_authorized") is not False:
        violations["event_schema"].append("contrast_actor_content_coding")
    if phase.get("final_holdout_content_review_authorized") is not False:
        violations["event_schema"].append("final_holdout_content_review")
    if phase.get("maximum_events_before_separate_pilot_freeze") != 30:
        violations["event_schema"].append("maximum_events")

    dimensions = set((event_schema.get("construct") or {}).get("dimensions") or [])
    v1_dimensions = set(
        (v1_preregistration.get("target_construct") or {}).get("dimensions") or []
    )
    if dimensions != EXPECTED_DIMENSIONS or dimensions != v1_dimensions:
        violations["event_schema"].append("construct_dimensions")
    excluded = set(
        (event_schema.get("construct") or {}).get("excluded_constructs") or []
    )
    if not {"private_inner_state", "performer_identity"} <= excluded:
        violations["event_schema"].append("excluded_constructs")

    unit = event_schema.get("observation_unit") or {}
    for field in (
        "same_event_alias_forbidden",
        "overlapping_timestamp_records_forbidden",
        "fixed_duration_chunking_forbidden",
        "non_observation_is_not_negative_evidence",
        "private_motive_inference_forbidden",
    ):
        if unit.get(field) is not True:
            violations["event_schema"].append(f"observation_unit:{field}")
    record = event_schema.get("record_contract") or {}
    if set(record.get("required_fields") or []) != EXPECTED_RECORD_FIELDS:
        violations["event_schema"].append("required_fields")
    if not EXPECTED_FORBIDDEN_EVENT_FIELDS <= set(
        record.get("forbidden_payload_field_names") or []
    ):
        violations["event_schema"].append("forbidden_payload_field_names")
    for field in ("researcher_paraphrase_only",):
        if record.get(field) is not True:
            violations["event_schema"].append(field)
    for field in ("copied_quote_allowed", "target_wording_template_allowed"):
        if record.get(field) is not False:
            violations["event_schema"].append(field)

    workflow = event_schema.get("coding_workflow") or []
    if [stage.get("stage") for stage in workflow] != [
        "primary_observation",
        "independent_review",
        "agreement_and_adjudication",
    ]:
        violations["event_schema"].append("workflow_stages")
    if any(stage.get("system_outputs_visible") is not False for stage in workflow[:2]):
        violations["event_schema"].append("system_outputs_visible")
    if workflow and workflow[-1].get(
        "unfavorable_or_ambiguous_records_deleted_to_raise_score"
    ) is not False:
        violations["event_schema"].append("posthoc_record_deletion")

    anti_leakage = event_schema.get("anti_leakage") or {}
    forbidden_true = (
        "event_records_may_enter_prompt",
        "event_records_may_enter_memory",
        "event_records_may_enter_retrieval",
        "event_records_may_enter_training",
        "event_records_may_define_fixed_target_answer",
        "event_records_may_select_final_holdout",
        "candidate_or_model_output_visible_during_coding",
    )
    for field in forbidden_true:
        if anti_leakage.get(field) is not False:
            violations["leakage"].append(field)
    for field in (
        "final_holdout_requires_candidate_and_harness_freeze",
        "final_holdout_requires_access_log",
    ):
        if anti_leakage.get(field) is not True:
            violations["leakage"].append(field)
    if not _all_zero_nonnegative_integers(event_schema.get("current_counts") or {}):
        violations["count_honesty"].append("event_schema_counts")


def _validate_rights_review(rights_review, source_manifest, root, violations):
    if rights_review.get("schema") != "uruha_public_persona_source_rights_review_v1":
        violations["rights"].append("schema")
    if not _binding_valid(rights_review.get("source_manifest_binding"), root):
        violations["rights"].append("source_manifest_binding")
    policy = rights_review.get("review_policy") or {}
    for field in (
        "public_access_is_not_training_permission",
        "public_access_is_not_a_rights_holder_license",
        "public_personal_information_still_requires_purpose_limitation",
        "store_source_locator_and_researcher_paraphrase_only",
    ):
        if policy.get(field) is not True:
            violations["rights"].append(field)
    for field in (
        "store_raw_media",
        "store_verbatim_transcript",
        "automated_bulk_collection",
        "model_training",
        "prompt_memory_or_retrieval_use",
        "public_source_content_redistribution",
        "legal_opinion_claimed",
        "rights_holder_permission_claimed",
    ):
        if policy.get(field) is not False:
            violations["rights"].append(field)

    source_roles = {
        row["source_id"]: row.get("source_role")
        for row in source_manifest.get("sources") or []
    }
    reviews = rights_review.get("source_reviews") or []
    review_index = {row.get("source_id"): row for row in reviews}
    if len(reviews) != 17 or set(review_index) != set(source_roles):
        violations["rights"].append("source_review_set")
    if len(review_index) != len(reviews):
        violations["rights"].append("duplicate_source_review")

    profiles = rights_review.get("permission_profiles") or {}
    expected_profile_by_role = {
        "identity_provenance": "identity_metadata_only",
        "calibration_reservation": "calibration_manual_observation_project_policy",
        "final_holdout_reservation": "sealed_final_metadata_only",
        "rights_policy": "policy_summary_only",
    }
    prohibited_profile_permissions = {
        "raw_media_storage",
        "verbatim_transcript_storage",
        "automated_bulk_collection",
        "model_training",
        "prompt_memory_or_retrieval_use",
        "runtime_persona_activation",
        "public_source_content_redistribution",
    }
    for source_id, source_role in source_roles.items():
        review = review_index.get(source_id) or {}
        if review.get("source_role") != source_role:
            violations["rights"].append(f"{source_id}:source_role")
        if review.get("public_access_verified") is not True:
            violations["rights"].append(f"{source_id}:public_access_verified")
        expected_profile = expected_profile_by_role.get(source_role)
        if review.get("profile_id") != expected_profile:
            violations["rights"].append(f"{source_id}:profile_id")
        profile = profiles.get(expected_profile) or {}
        if profile.get("metadata_locator_storage") is not True:
            violations["rights"].append(f"{source_id}:metadata_locator_storage")
        for field in prohibited_profile_permissions:
            if profile.get(field) is not False:
                violations["rights"].append(f"{source_id}:{field}")
        if source_role == "calibration_reservation":
            if profile.get("bounded_manual_behavior_observation") is not True:
                violations["rights"].append(f"{source_id}:manual_observation")
            if profile.get("researcher_behavior_paraphrase") is not True:
                violations["rights"].append(f"{source_id}:paraphrase")
        elif profile.get("bounded_manual_behavior_observation") is not False:
            violations["rights"].append(f"{source_id}:unexpected_observation")

    completion = rights_review.get("review_completion") or {}
    if completion.get("registered_source_locator_count") != 17:
        violations["rights"].append("registered_source_locator_count")
    if completion.get("registered_source_locator_reviewed_count") != 17:
        violations["rights"].append("registered_source_locator_reviewed_count")
    if completion.get("calibration_locator_conditionally_reviewed_count") != 3:
        violations["rights"].append("calibration_review_count")
    if completion.get("final_holdout_content_reviewed_count") != 0:
        violations["rights"].append("holdout_content_review_count")
    if completion.get("formal_corpus_rights_review_complete") is not False:
        violations["rights"].append("formal_corpus_rights_review_complete")
    if not _all_zero_nonnegative_integers(rights_review.get("current_counts") or {}):
        violations["count_honesty"].append("rights_review_counts")


def _validate_method_registry(method_registry, violations):
    if method_registry.get("schema") != (
        "uruha_public_persona_precontent_governance_method_registry_v3"
    ):
        violations["methods"].append("schema")
    rows = method_registry.get("sources") or []
    ids = {row.get("source_id") for row in rows}
    if len(rows) != len(ids) or ids != EXPECTED_METHOD_IDS:
        violations["methods"].append("source_set")
    for row in rows:
        if row.get("authority") not in {
            "government_official",
            "platform_official",
            "agency_official",
        }:
            violations["methods"].append(f"{row.get('source_id')}:authority")
        if not str(row.get("url") or "").startswith("https://"):
            violations["methods"].append(f"{row.get('source_id')}:url")
        if not str(row.get("applicability_boundary") or "").strip():
            violations["methods"].append(
                f"{row.get('source_id')}:applicability_boundary"
            )


def _validate_consent(consent, blind_protocol, root, violations):
    if consent.get("schema") != "uruha_public_persona_informed_consent_v1":
        violations["consent"].append("schema")
    if consent.get("language") != "zh-Hant":
        violations["consent"].append("language")
    if not _binding_valid(consent.get("document"), root):
        violations["consent"].append("document_binding")
        document = ""
    else:
        document = (Path(root) / consent["document"]["path"]).read_text(
            encoding="utf-8"
        )
    participant = consent.get("participant_population") or {}
    if participant.get("minimum_age") != 18:
        violations["consent"].append("minimum_age")
    if set(participant.get("groups") or []) != {
        "target_familiar",
        "general_japanese",
    }:
        violations["consent"].append("participant_groups")
    disclosures = consent.get("required_disclosures") or {}
    if not disclosures or any(value is not True for value in disclosures.values()):
        violations["consent"].append("required_disclosures")

    data = consent.get("data_handling") or {}
    blind_data = blind_protocol.get("data_minimization") or {}
    if set(data.get("stored_fields") or []) != EXPECTED_STORED_RATER_FIELDS:
        violations["consent"].append("stored_fields")
    if set(data.get("stored_fields") or []) != set(
        blind_data.get("stored_fields") or []
    ):
        violations["consent"].append("blind_protocol_stored_fields")
    if not EXPECTED_PROHIBITED_RATER_FIELDS <= set(
        data.get("prohibited_fields") or []
    ):
        violations["consent"].append("prohibited_fields")
    if set(data.get("prohibited_fields") or []) != set(
        blind_data.get("prohibited_fields") or []
    ):
        violations["consent"].append("blind_protocol_prohibited_fields")
    if data.get("raw_identity_linkage") is not False:
        violations["consent"].append("raw_identity_linkage")
    if data.get("individual_record_retention_months_after_study_close") != 12:
        violations["consent"].append("retention_months")

    withdrawal = consent.get("withdrawal") or {}
    for field in (
        "allowed_before_anonymized_lock",
        "pseudonymous_code_required",
        "no_penalty",
    ):
        if withdrawal.get(field) is not True:
            violations["consent"].append(f"withdrawal:{field}")
    if withdrawal.get("possible_after_irreversible_aggregation") is not False:
        violations["consent"].append("withdrawal_after_aggregation")

    blockers = consent.get("recruitment_blockers") or {}
    if not blockers or any(value is not False for value in blockers.values()):
        violations["consent"].append("recruitment_blockers_must_remain_unresolved")
    if not _all_zero_nonnegative_integers(consent.get("current_counts") or {}):
        violations["count_honesty"].append("consent_counts")
    auth = consent.get("authorizations") or {}
    if auth.get("consent_form_usability_review") is not True:
        violations["consent"].append("consent_form_usability_review")
    for field in ("rater_recruitment", "rating_collection", "persona_claim"):
        if auth.get(field) is not False:
            violations["consent"].append(f"authorization:{field}")

    required_phrases = (
        "全部由 AI 產生",
        "參加完全自願",
        "不保存：姓名",
        "研究聯絡窗口尚未填入",
        "不得招募或收集評分",
        "不會被描述成「AI 就是本人」",
    )
    for phrase in required_phrases:
        if phrase not in document:
            violations["consent"].append(f"document_phrase:{phrase}")


def _validate_authorization(preregistration, violations):
    policy = preregistration.get("decision_policy") or {}
    if policy.get("protocol_pass") != PASS_DECISION:
        violations["authorization"].append("protocol_pass")
    if policy.get("protocol_fail") != FAIL_DECISION:
        violations["authorization"].append("protocol_fail")
    for field in (
        "bounded_calibration_event_coding",
        "consent_usability_review",
        "contrast_event_source_registration",
    ):
        if policy.get(field) is not True:
            violations["authorization"].append(field)
    for field in (
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


def audit(
    preregistration,
    event_schema,
    rights_review,
    consent,
    method_registry,
    source_manifest,
    blind_protocol,
    readiness,
    v1_preregistration,
    v2_result,
    root=ROOT,
):
    violations = defaultdict(list)
    if preregistration.get("schema") != (
        "uruha_public_persona_precontent_governance_preregistration_v3"
    ):
        violations["preregistration"].append("schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations["preregistration"].append("experiment_id")
    if preregistration.get("target_id") != TARGET_ID:
        violations["preregistration"].append("target_id")
    if not str(preregistration.get("falsifiable_hypothesis") or "").strip():
        violations["preregistration"].append("falsifiable_hypothesis")
    if not str(preregistration.get("single_changed_variable") or "").strip():
        violations["preregistration"].append("single_changed_variable")

    _validate_dependency(preregistration, v2_result, root, violations)
    _validate_goal(preregistration, violations)
    _validate_event_schema(
        event_schema, source_manifest, v1_preregistration, root, violations
    )
    _validate_rights_review(rights_review, source_manifest, root, violations)
    _validate_method_registry(method_registry, violations)
    _validate_consent(consent, blind_protocol, root, violations)
    _validate_authorization(preregistration, violations)

    prior_report = build_reference_audit_from_paths()
    if prior_report.get("protocol_passed") is not True:
        violations["readiness"].append("prior_protocol_no_longer_passes")
    summary = prior_report.get("summary") or {}
    if summary.get("readiness_check_pass_count") != 4:
        violations["readiness"].append("readiness_pass_count")
    if summary.get("readiness_check_count") != 19:
        violations["readiness"].append("readiness_check_count")
    if prior_report.get("formal_execution_ready") is not False:
        violations["readiness"].append("formal_execution_ready")
    if (readiness.get("flags") or {}).get(
        "source_rights_review_complete_for_formal_corpus"
    ) is not False:
        violations["readiness"].append("formal_corpus_rights_flag")

    expected_counts = preregistration.get("expected_counts_after_pass") or {}
    if not _all_zero_nonnegative_integers(expected_counts):
        violations["count_honesty"].append("preregistered_expected_counts")
    v2_formal = v2_result.get("formal_result") or {}
    for field in (
        "target_behavior_event_count",
        "contrast_behavior_event_count",
        "human_rater_count",
        "model_response_count",
        "persona_score_count",
        "holdout_content_review_count",
        "runtime_change_count",
        "model_call_count",
    ):
        if v2_formal.get(field) != 0:
            violations["count_honesty"].append(f"v2_result:{field}")

    protocol_checks = {
        "preregistration_is_falsifiable_and_single_variable": not violations[
            "preregistration"
        ],
        "v2_authorization_dependency_is_hash_bound": not violations["dependency"],
        "long_term_goal_separates_four_evidence_axes": not violations["goal"],
        "event_unit_and_six_dimensions_are_frozen": not violations["event_schema"],
        "calibration_only_and_final_holdout_is_forbidden": not violations[
            "event_schema"
        ]
        and not violations["leakage"],
        "two_stage_observation_is_blind_to_system_outputs": not violations[
            "event_schema"
        ],
        "event_data_cannot_enter_prompt_memory_training_or_answers": not violations[
            "leakage"
        ],
        "all_17_registered_sources_have_role_matched_review": not violations[
            "rights"
        ],
        "public_access_is_not_treated_as_license": not violations["rights"],
        "official_governance_methods_have_scope_boundaries": not violations[
            "methods"
        ],
        "participant_facing_consent_contains_required_elements": not violations[
            "consent"
        ],
        "consent_data_fields_match_blind_protocol": not violations["consent"],
        "recruitment_remains_blocked_until_contacts_and_review_exist": not violations[
            "consent"
        ],
        "events_raters_outputs_scores_and_holdout_access_remain_zero": not violations[
            "count_honesty"
        ],
        "formal_readiness_remains_4_of_19": not violations["readiness"],
        "authorization_is_bounded_to_calibration_coding_and_review": not violations[
            "authorization"
        ],
    }
    protocol_passed = all(protocol_checks.values())
    decision = PASS_DECISION if protocol_passed else FAIL_DECISION
    compact_violations = {
        key: value for key, value in sorted(violations.items()) if value
    }
    rights_completion = rights_review.get("review_completion") or {}
    return {
        "schema": "uruha_public_persona_precontent_governance_audit_v3",
        "experiment_id": EXPERIMENT_ID,
        "target_id": TARGET_ID,
        "protocol_passed": protocol_passed,
        "formal_execution_ready": False,
        "persona_score_computed": False,
        "decision": decision,
        "summary": {
            "protocol_check_count": len(protocol_checks),
            "protocol_check_pass_count": sum(protocol_checks.values()),
            "formal_readiness_check_count": summary.get(
                "readiness_check_count", 0
            ),
            "formal_readiness_pass_count": summary.get(
                "readiness_check_pass_count", 0
            ),
            "registered_source_review_count": rights_completion.get(
                "registered_source_locator_reviewed_count", 0
            ),
            "calibration_source_authorized_count": len(EXPECTED_CALIBRATION_IDS),
            "sealed_final_source_count": len(EXPECTED_FINAL_IDS),
            "behavior_event_count": 0,
            "human_rater_count": 0,
            "model_response_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "runtime_change_count": 0,
            "model_call_count": 0,
        },
        "protocol_checks": protocol_checks,
        "prior_formal_readiness_checks": prior_report.get("readiness_checks"),
        "violations": compact_violations,
        "authorization_scope": {
            "authorized_calibration_source_ids": sorted(EXPECTED_CALIBRATION_IDS),
            "forbidden_final_holdout_source_ids": sorted(EXPECTED_FINAL_IDS),
            "maximum_calibration_events_before_separate_pilot_freeze": 30,
        },
        "recruitment_blockers": consent.get("recruitment_blockers"),
        "authorizations": {
            "bounded_calibration_event_coding": protocol_passed,
            "consent_form_usability_review": protocol_passed,
            "contrast_event_source_registration": protocol_passed,
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
            "依 V1 schema 只編碼 3 個 calibration 來源、最多 30 個事件並保留獨立覆核；"
            "同時登記相近人物行為來源。真人招募前仍須填入聯絡窗口、完成資料安全與倫理審查。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格內容前治理 V3 稽核",
        "",
        f"- 協定通過：`{report['protocol_passed']}` ({summary['protocol_check_pass_count']}/{summary['protocol_check_count']})",
        f"- 正式評測就緒：`{report['formal_execution_ready']}` ({summary['formal_readiness_pass_count']}/{summary['formal_readiness_check_count']})",
        f"- 決策：`{report['decision']}`",
        "",
        "## 長期目標現在怎麼定義",
        "",
        "完整目標不再是模糊的『像人』單一分數，而是四條分開驗證的證據線：通用認知、公開人格相似、本機可部署、Function Calling／語音／VRM 安全。",
        "一ノ瀬うるは是公開人格案例，不是私人身分複製，也不能用公開欺騙當成功標準。",
        "",
        "## 本輪真正完成什麼",
        "",
        "| 治理層 | 結果 | 現在可做 |",
        "|---|---:|---|",
        f"| 來源逐筆用途 | {summary['registered_source_review_count']}/17 | 只依角色使用 metadata 或有限研究摘要 |",
        "| 事件編碼規則 | 6 個公開行為維度 | 校準來源可進行兩階段人工編碼 |",
        "| 知情同意書 | 參與者版已建立 | 只做可用性審查，尚不可招募 |",
        f"| 正式 readiness | {summary['formal_readiness_pass_count']}/{summary['formal_readiness_check_count']} | 不變，不能正式評分 |",
        "",
        "## 內容邊界",
        "",
        f"- 可編碼：{summary['calibration_source_authorized_count']} 個預先登記 calibration 來源，最多 30 個事件。",
        f"- 仍封存：{summary['sealed_final_source_count']} 個 final holdout，內容查看次數為 {summary['holdout_content_review_count']}。",
        "- 只存時間定位與研究者改寫的可觀察行為；不存影片、逐字稿、原句或目標答案。",
        "- 事件不得進 Prompt、記憶、檢索、訓練或測驗答案規則。",
        "",
        "## 數據誠實性",
        "",
        "| 事件 | 真人評分者 | 模型回答 | 人格分數 | 模型呼叫 |",
        "|---:|---:|---:|---:|---:|",
        f"| {summary['behavior_event_count']} | {summary['human_rater_count']} | {summary['model_response_count']} | {summary['persona_score_count']} | {summary['model_call_count']} |",
        "",
        "本輪建立的是可靠量測的前置條件，不是人格能力提升，也沒有產生任何新分數。",
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
    event_schema_path=DEFAULT_EVENT_SCHEMA,
    rights_review_path=DEFAULT_RIGHTS_REVIEW,
    consent_path=DEFAULT_CONSENT,
    method_registry_path=DEFAULT_METHOD_REGISTRY,
    source_manifest_path=DEFAULT_SOURCE_MANIFEST,
    blind_protocol_path=DEFAULT_BLIND_PROTOCOL,
    readiness_path=DEFAULT_READINESS,
    v1_preregistration_path=DEFAULT_V1_PREREGISTRATION,
    v2_result_path=DEFAULT_V2_RESULT,
):
    paths = {
        "preregistration": Path(preregistration_path),
        "event_schema": Path(event_schema_path),
        "rights_review": Path(rights_review_path),
        "consent": Path(consent_path),
        "method_registry": Path(method_registry_path),
        "source_manifest": Path(source_manifest_path),
        "blind_protocol": Path(blind_protocol_path),
        "readiness_inventory": Path(readiness_path),
        "v1_preregistration": Path(v1_preregistration_path),
        "v2_result_lock": Path(v2_result_path),
    }
    report = audit(
        load_json(paths["preregistration"]),
        load_json(paths["event_schema"]),
        load_json(paths["rights_review"]),
        load_json(paths["consent"]),
        load_json(paths["method_registry"]),
        load_json(paths["source_manifest"]),
        load_json(paths["blind_protocol"]),
        load_json(paths["readiness_inventory"]),
        load_json(paths["v1_preregistration"]),
        load_json(paths["v2_result_lock"]),
        root=ROOT,
    )
    report["inputs"] = {
        key: {"path": _display_path(path), "sha256": sha256_file(path)}
        for key, path in paths.items()
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
    parser.add_argument("--event-schema", default=str(DEFAULT_EVENT_SCHEMA))
    parser.add_argument("--rights-review", default=str(DEFAULT_RIGHTS_REVIEW))
    parser.add_argument("--consent", default=str(DEFAULT_CONSENT))
    parser.add_argument("--method-registry", default=str(DEFAULT_METHOD_REGISTRY))
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST))
    parser.add_argument("--blind-protocol", default=str(DEFAULT_BLIND_PROTOCOL))
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS))
    parser.add_argument("--v1-preregistration", default=str(DEFAULT_V1_PREREGISTRATION))
    parser.add_argument("--v2-result", default=str(DEFAULT_V2_RESULT))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-protocol-pass", action="store_true")
    parser.add_argument("--require-execution-ready", action="store_true")
    args = parser.parse_args()

    report = build_audit_from_paths(
        args.preregistration,
        args.event_schema,
        args.rights_review,
        args.consent,
        args.method_registry,
        args.source_manifest,
        args.blind_protocol,
        args.readiness,
        args.v1_preregistration,
        args.v2_result,
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
