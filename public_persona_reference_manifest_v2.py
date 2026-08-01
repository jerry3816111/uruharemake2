#!/usr/bin/env python3
"""Audit metadata-only public-persona references and blind-rating governance."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_reference_manifest_v2_preregistration.json"
)
DEFAULT_MANIFEST = (
    ROOT / "datasets/public_persona_reference_source_manifest_v2.json"
)
DEFAULT_RATER_PROTOCOL = (
    ROOT / "configs/public_persona_blind_rater_protocol_v1.json"
)
DEFAULT_READINESS = (
    ROOT / "datasets/public_persona_fidelity_eval_v2_readiness_inventory.json"
)
DEFAULT_V1_RESULT = ROOT / "configs/public_persona_fidelity_eval_v1_result_lock.json"
DEFAULT_V1_PREREGISTRATION = (
    ROOT / "configs/public_persona_fidelity_eval_v1_preregistration.json"
)
DEFAULT_V2_SOURCE_REGISTRY = (
    ROOT / "datasets/public_persona_observation_source_registry_v2.json"
)
DEFAULT_OUTPUT_JSON = ROOT / "reports/public_persona_reference_manifest_v2_audit.json"
DEFAULT_OUTPUT_MD = ROOT / "reports/public_persona_reference_manifest_v2_audit.md"

PREREGISTRATION_SCHEMA = "uruha_public_persona_reference_manifest_preregistration_v2"
MANIFEST_SCHEMA = "uruha_public_persona_reference_source_manifest_v2"
RATER_SCHEMA = "uruha_public_persona_blind_rater_protocol_v1"
READINESS_SCHEMA = "uruha_public_persona_fidelity_readiness_inventory_v2"
EXPERIMENT_ID = "public_persona_reference_manifest_v2"
TARGET_ID = "ichinose_uruha_public_persona"
V1_REQUIRED_DECISION = (
    "authorize_provenance_only_reference_manifest_and_consented_rater_protocol_construction"
)
PASS_DECISION = (
    "authorize_metadata_only_event_coding_preregistration_and_consent_form_review"
)
FAIL_DECISION = "repair_reference_manifest_before_any_content_coding_or_rater_contact"

EXPECTED_ACTORS = {
    "ichinose_uruha_public_persona": {
        "role": "target",
        "public_name": "一ノ瀬うるは",
        "profile_source_id": "vspo_profile_ichinose_uruha_20260801",
        "channel_source_id": "youtube_channel_ichinose_uruha_20260801",
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "channel_url": "https://www.youtube.com/channel/UC5LyYg6cCA4yHEYvtUsir3g",
    },
    "tachibana_hinano_public_persona": {
        "role": "matched_contrast",
        "public_name": "橘ひなの",
        "profile_source_id": "vspo_profile_tachibana_hinano_20260801",
        "channel_source_id": "youtube_channel_tachibana_hinano_20260801",
        "channel_id": "UCvUc0m317LWTTPZoBQV479A",
        "channel_url": "https://www.youtube.com/channel/UCvUc0m317LWTTPZoBQV479A",
    },
    "kurumi_noa_public_persona": {
        "role": "matched_contrast",
        "public_name": "胡桃のあ",
        "profile_source_id": "vspo_profile_kurumi_noa_20260801",
        "channel_source_id": "youtube_channel_kurumi_noa_20260801",
        "channel_id": "UCIcAj6WkJ8vZ7DeJVgmeqKw",
        "channel_url": "https://www.youtube.com/channel/UCIcAj6WkJ8vZ7DeJVgmeqKw",
    },
    "tosaki_mimi_public_persona": {
        "role": "matched_contrast",
        "public_name": "兎咲ミミ",
        "profile_source_id": "vspo_profile_tosaki_mimi_20260801",
        "channel_source_id": "youtube_channel_tosaki_mimi_20260801",
        "channel_id": "UCnvVG9RbOW3J6Ifqo-zKLiw",
        "channel_url": "https://www.youtube.com/channel/UCnvVG9RbOW3J6Ifqo-zKLiw",
    },
}

EXPECTED_CALIBRATION = {
    "uruha_calibration_youtube_valorant_20260318": {
        "url": "https://www.youtube.com/watch?v=cssf0abPOPw",
        "video_id": "cssf0abPOPw",
        "published_at": "2026-03-18",
        "context_family": "competitive_fps_solo_stream",
        "partition": "youtube_archive_cssf0abPOPw",
    },
    "uruha_calibration_youtube_street_fighter_20250317": {
        "url": "https://www.youtube.com/watch?v=M37jBhQWK_0",
        "video_id": "M37jBhQWK_0",
        "published_at": "2025-03-17",
        "context_family": "fighting_game_solo_stream",
        "partition": "youtube_archive_M37jBhQWK_0",
    },
    "uruha_calibration_youtube_farming_20250308": {
        "url": "https://www.youtube.com/watch?v=6mpZwCihM0Q",
        "video_id": "6mpZwCihM0Q",
        "published_at": "2025-03-08",
        "context_family": "simulation_game_solo_stream",
        "partition": "youtube_archive_6mpZwCihM0Q",
    },
}

EXPECTED_FINAL_HOLDOUT = {
    "uruha_youtube_forza_holdout_v2": {
        "url": "https://www.youtube.com/watch?v=K_bNKL3iA_Q",
        "video_id": "K_bNKL3iA_Q",
        "published_at": "2026-07-24",
        "context_family": "unfamiliar_driving_game_solo_stream",
        "partition": "youtube_archive_K_bNKL3iA_Q",
        "inherited": True,
    },
    "uruha_youtube_apex_team_holdout_v2": {
        "url": "https://www.youtube.com/watch?v=WRc8lofZ4Uc",
        "video_id": "WRc8lofZ4Uc",
        "published_at": "2026-07-29",
        "context_family": "familiar_team_competitive_stream",
        "partition": "youtube_archive_WRc8lofZ4Uc",
        "inherited": True,
    },
    "uruha_final_holdout_youtube_apex_collab_20250206": {
        "url": "https://www.youtube.com/watch?v=ArPfOH8UVU0",
        "video_id": "ArPfOH8UVU0",
        "published_at": "2025-02-06",
        "context_family": "small_group_competitive_collaboration",
        "partition": "youtube_archive_ArPfOH8UVU0",
        "inherited": False,
    },
    "uruha_final_holdout_youtube_social_deduction_20210404": {
        "url": "https://www.youtube.com/watch?v=zGZODytOoUg",
        "video_id": "zGZODytOoUg",
        "published_at": "2021-04-04",
        "context_family": "large_group_social_deduction_collaboration",
        "partition": "youtube_archive_zGZODytOoUg",
        "inherited": False,
    },
}

EXPECTED_POLICY_SOURCES = {
    "youtube_terms_reference_v2_20260801": {
        "url": "https://www.youtube.com/static?template=terms",
        "authority": "platform_official",
    },
    "vspo_guideline_reference_v2_20260801": {
        "url": "https://vspo.jp/guide/",
        "authority": "agency_official",
    },
}

READINESS_COUNT_MAP = {
    "target_development_observation_count_min": "target_development_observation_count",
    "target_calibration_source_count_min": "target_calibration_source_count",
    "target_calibration_event_count_min": "target_calibration_event_count",
    "target_final_holdout_source_count_min": "target_final_holdout_source_count",
    "target_final_holdout_event_count_min": "target_final_holdout_event_count",
    "matched_contrast_person_count_min": "matched_contrast_person_count",
    "contrast_event_count_per_person_min": "contrast_event_count_per_person_min",
    "same_topic_reference_pair_count_min": "same_topic_reference_pair_count",
    "counterfactual_final_scenario_count_min": "counterfactual_final_scenario_count",
    "dynamic_multi_turn_episode_count_min": "dynamic_multi_turn_episode_count",
    "target_familiar_final_rater_count_min": "target_familiar_final_rater_count",
    "general_japanese_final_rater_count_min": "general_japanese_final_rater_count",
    "ratings_per_item_min": "ratings_per_item_min",
}
READINESS_FLAG_MAP = {
    "pilot_completed_required": "pilot_completed",
    "power_plan_frozen_required": "power_plan_frozen",
    "runtime_manifest_frozen_required": "runtime_manifest_frozen",
    "source_rights_review_complete_required": (
        "source_rights_review_complete_for_formal_corpus"
    ),
    "holdout_access_log_ready_required": "holdout_access_log_ready",
}
EXPECTED_READINESS_FLAGS = {
    "pilot_completed",
    "power_plan_frozen",
    "runtime_manifest_frozen",
    "source_rights_review_complete_for_formal_corpus",
    "holdout_access_log_ready",
    "formal_execution_ready",
    "persona_fidelity_claim_available",
}
EVIDENCE_BINDING_REQUIREMENTS = {
    "target_calibration_source_count": "target_calibration_manifest",
    "target_calibration_event_count": "target_calibration_manifest",
    "target_final_holdout_source_count": "target_final_holdout_manifest",
    "target_final_holdout_event_count": "target_final_holdout_manifest",
    "matched_contrast_person_count": "contrast_reference_manifest",
    "contrast_event_count_per_person_min": "contrast_reference_manifest",
    "same_topic_reference_pair_count": "same_topic_reference_manifest",
    "counterfactual_final_scenario_count": "counterfactual_scenario_manifest",
    "dynamic_multi_turn_episode_count": "dynamic_episode_manifest",
    "target_familiar_final_rater_count": "rater_manifest",
    "general_japanese_final_rater_count": "rater_manifest",
    "ratings_per_item_min": "rater_manifest",
}
PROHIBITED_PAYLOAD_KEYS = {
    "raw_text",
    "raw_source_text",
    "raw_media",
    "transcript",
    "verbatim_transcript",
    "quote_text",
    "target_reply",
    "expected_reply",
    "reference_answer",
    "answer_key",
    "target_continuation",
    "model_output",
    "training_text",
}
EXPECTED_EVENT_METADATA_FIELDS = {
    "video_id",
    "publisher_channel_id",
    "published_at",
    "context_family",
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


def _validate_binding(binding, root):
    if not isinstance(binding, dict):
        return False
    path_value = str(binding.get("path") or "")
    expected_hash = str(binding.get("sha256") or "")
    if not path_value or len(expected_hash) != 64:
        return False
    path = Path(root) / path_value
    return path.is_file() and sha256_file(path) == expected_hash


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


def _source_index(manifest, violations):
    sources = list(manifest.get("sources") or [])
    source_ids = [str(row.get("source_id") or "") for row in sources]
    partitions = [str(row.get("source_partition_key") or "") for row in sources]
    if not all(source_ids) or len(source_ids) != len(set(source_ids)):
        violations["source_identity"].append("source_ids_unique_nonempty")
    if not all(partitions) or len(partitions) != len(set(partitions)):
        violations["partition"].append("source_partition_keys_unique_nonempty")
    return {str(row.get("source_id") or ""): row for row in sources}


def _validate_actor_sources(manifest, sources, violations):
    actors = list(manifest.get("actors") or [])
    actor_ids = [str(row.get("actor_id") or "") for row in actors]
    if set(actor_ids) != set(EXPECTED_ACTORS) or len(actor_ids) != len(set(actor_ids)):
        violations["actors"].append("actor_set")
        return
    for actor in actors:
        actor_id = actor["actor_id"]
        expected = EXPECTED_ACTORS[actor_id]
        if actor.get("role") != expected["role"]:
            violations["actors"].append(f"{actor_id}:role")
        if actor.get("public_name") != expected["public_name"]:
            violations["actors"].append(f"{actor_id}:public_name")
        if actor.get("selected_from_model_outputs_or_similarity_scores") is not False:
            violations["actors"].append(f"{actor_id}:posthoc_selection")
        for field, expected_field in (
            ("official_profile_source_id", "profile_source_id"),
            ("official_channel_source_id", "channel_source_id"),
        ):
            if actor.get(field) != expected[expected_field]:
                violations["actors"].append(f"{actor_id}:{field}")

        profile = sources.get(expected["profile_source_id"], {})
        if (
            profile.get("actor_id") != actor_id
            or profile.get("source_role") != "identity_provenance"
            or profile.get("dataset_role") != "identity"
            or profile.get("authority") != "agency_official"
            or profile.get("source_type") != "official_member_profile"
            or profile.get("url") != "https://vspo.jp/"
            or profile.get("content_reviewed_for_behavior") is not False
        ):
            violations["official_identity"].append(f"{actor_id}:profile")

        channel = sources.get(expected["channel_source_id"], {})
        if (
            channel.get("actor_id") != actor_id
            or channel.get("source_role") != "identity_provenance"
            or channel.get("dataset_role") != "identity"
            or channel.get("source_type") != "official_youtube_channel"
            or channel.get("url") != expected["channel_url"]
            or channel.get("channel_id") != expected["channel_id"]
            or channel.get("content_reviewed_for_behavior") is not False
        ):
            violations["official_identity"].append(f"{actor_id}:channel")


def _validate_event_source(source_id, row, expected, final_holdout, violations):
    expected_role = "final_holdout_reservation" if final_holdout else "calibration_reservation"
    expected_dataset = "final_holdout" if final_holdout else "calibration"
    for field, expected_value in (
        ("actor_id", TARGET_ID),
        ("source_role", expected_role),
        ("dataset_role", expected_dataset),
        ("authority", "target_official"),
        ("source_type", "official_public_stream_archive"),
        ("url", expected["url"]),
        ("video_id", expected["video_id"]),
        ("publisher_channel_id", EXPECTED_ACTORS[TARGET_ID]["channel_id"]),
        ("published_at", expected["published_at"]),
        ("context_family", expected["context_family"]),
        ("source_partition_key", expected["partition"]),
    ):
        if row.get(field) != expected_value:
            violations["event_sources"].append(f"{source_id}:{field}")
    if set(row.get("metadata_fields_reviewed") or []) != EXPECTED_EVENT_METADATA_FIELDS:
        violations["event_sources"].append(f"{source_id}:metadata_fields_reviewed")
    for field in (
        "content_reviewed_for_behavior",
        "labels_available",
        "raw_media_stored",
        "raw_transcript_stored",
        "candidate_answer_available",
    ):
        if row.get(field) is not False:
            violations["content_boundary"].append(f"{source_id}:{field}")
    expected_flag = bool(final_holdout)
    for field in (
        "sealed",
        "candidate_freeze_required_before_behavior_review",
        "holdout_access_log_required",
    ):
        if row.get(field) is not expected_flag:
            violations["holdout_seal"].append(f"{source_id}:{field}")


def audit(
    preregistration,
    manifest,
    rater_protocol,
    readiness,
    v1_result,
    v1_preregistration,
    v2_source_registry,
    root=ROOT,
):
    violations = defaultdict(list)

    if preregistration.get("schema") != PREREGISTRATION_SCHEMA:
        violations["preregistration"].append("schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations["preregistration"].append("experiment_id")
    if preregistration.get("target_id") != TARGET_ID:
        violations["preregistration"].append("target_id")
    if not str(preregistration.get("falsifiable_hypothesis") or "").strip():
        violations["preregistration"].append("falsifiable_hypothesis")
    if not str(preregistration.get("single_changed_variable") or "").strip():
        violations["preregistration"].append("single_changed_variable")

    dependency = preregistration.get("depends_on") or {}
    if dependency.get("path") != "configs/public_persona_fidelity_eval_v1_result_lock.json":
        violations["dependency"].append("path")
    if dependency.get("experiment_id") != "public_persona_fidelity_eval_v1":
        violations["dependency"].append("experiment_id")
    if dependency.get("required_decision") != V1_REQUIRED_DECISION:
        violations["dependency"].append("required_decision")
    if v1_result.get("experiment_id") != "public_persona_fidelity_eval_v1":
        violations["dependency"].append("result_experiment_id")
    if v1_result.get("decision") != V1_REQUIRED_DECISION:
        violations["dependency"].append("result_decision")
    if v1_result.get("protocol_passed") is not True:
        violations["dependency"].append("result_protocol_passed")
    if preregistration.get("readiness_contract_source") != (
        "configs/public_persona_fidelity_eval_v1_preregistration.json"
    ):
        violations["dependency"].append("readiness_contract_source")

    source_requirements = preregistration.get("source_requirements") or {}
    expected_requirements = {
        "target_calibration_source_count_exact": 3,
        "target_final_holdout_source_count_exact": 4,
        "inherited_v2_holdout_source_count_exact": 2,
        "event_content_reviewed_for_behavior_count_exact": 0,
        "event_label_available_count_exact": 0,
        "raw_or_verbatim_record_count_exact": 0,
        "contrast_behavior_event_count_exact": 0,
        "human_rater_count_exact": 0,
        "model_response_count_exact": 0,
        "persona_score_count_exact": 0,
    }
    for field, expected in expected_requirements.items():
        if source_requirements.get(field) != expected:
            violations["preregistration"].append(f"source_requirements:{field}")

    if manifest.get("schema") != MANIFEST_SCHEMA:
        violations["manifest"].append("schema")
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        violations["manifest"].append("experiment_id")
    if manifest.get("target_id") != TARGET_ID:
        violations["manifest"].append("target_id")
    if manifest.get("actor_selection_frozen_before_behavior_coding") is not True:
        violations["actors"].append("selection_not_frozen")
    expected_axes = {
        "same_official_agency_ecosystem",
        "japanese_language_public_activity",
        "gaming_and_esports_livestream_medium",
    }
    if set(manifest.get("matched_axes") or []) != expected_axes:
        violations["actors"].append("matched_axes")

    policy = manifest.get("project_policy") or {}
    if policy.get("public_access_is_not_training_permission") is not True:
        violations["rights_policy"].append("public_access_is_not_training_permission")
    if policy.get("store_official_metadata_only") is not True:
        violations["rights_policy"].append("store_official_metadata_only")
    for field in (
        "store_raw_media",
        "store_verbatim_transcripts",
        "store_target_replies_or_reference_answers",
        "automated_bulk_collection",
        "model_training_authorized",
        "prompt_or_memory_injection_authorized",
        "runtime_persona_activation_authorized",
        "public_impersonation_authorized",
    ):
        if policy.get(field) is not False:
            violations["rights_policy"].append(field)

    prohibited = _find_prohibited_keys(manifest)
    if prohibited:
        violations["content_boundary"].extend(prohibited)

    sources = _source_index(manifest, violations)
    _validate_actor_sources(manifest, sources, violations)

    for source_id, expected in EXPECTED_POLICY_SOURCES.items():
        row = sources.get(source_id, {})
        if (
            row.get("source_role") != "rights_policy"
            or row.get("dataset_role") != "policy"
            or row.get("url") != expected["url"]
            or row.get("authority") != expected["authority"]
            or row.get("content_reviewed_for_behavior") is not False
        ):
            violations["rights_policy"].append(source_id)
    for source_id, row in sources.items():
        if row.get("source_role") == "rights_policy":
            continue
        basis = set(row.get("policy_basis_source_ids") or [])
        if not basis or not basis.issubset(EXPECTED_POLICY_SOURCES):
            violations["rights_policy"].append(f"{source_id}:policy_basis")

    calibration_ids = {
        source_id
        for source_id, row in sources.items()
        if row.get("source_role") == "calibration_reservation"
    }
    final_ids = {
        source_id
        for source_id, row in sources.items()
        if row.get("source_role") == "final_holdout_reservation"
    }
    if calibration_ids != set(EXPECTED_CALIBRATION):
        violations["event_sources"].append("calibration_source_set")
    if final_ids != set(EXPECTED_FINAL_HOLDOUT):
        violations["event_sources"].append("final_holdout_source_set")
    for source_id, expected in EXPECTED_CALIBRATION.items():
        _validate_event_source(
            source_id, sources.get(source_id, {}), expected, False, violations
        )
    for source_id, expected in EXPECTED_FINAL_HOLDOUT.items():
        _validate_event_source(
            source_id, sources.get(source_id, {}), expected, True, violations
        )
        inherited_value = sources.get(source_id, {}).get("inherited_from_source_id")
        if expected["inherited"] and inherited_value != source_id:
            violations["inherited_holdout"].append(f"{source_id}:inherited_from")
        if not expected["inherited"] and inherited_value is not None:
            violations["inherited_holdout"].append(f"{source_id}:unexpected_inheritance")

    calibration_partitions = {
        sources[source_id].get("source_partition_key")
        for source_id in calibration_ids
        if source_id in sources
    }
    final_partitions = {
        sources[source_id].get("source_partition_key")
        for source_id in final_ids
        if source_id in sources
    }
    if calibration_partitions & final_partitions:
        violations["partition"].append("calibration_final_overlap")

    old_sources = {
        str(row.get("source_id") or ""): row
        for row in v2_source_registry.get("sources") or []
    }
    for source_id, expected in EXPECTED_FINAL_HOLDOUT.items():
        if not expected["inherited"]:
            continue
        old = old_sources.get(source_id, {})
        new = sources.get(source_id, {})
        if (
            old.get("source_role") != "sealed_holdout"
            or old.get("dataset_role") != "holdout"
            or old.get("url") != new.get("url")
            or old.get("source_partition_key") != new.get("source_partition_key")
            or old.get("content_review_scope") != "metadata_only_unreviewed_for_behavior"
        ):
            violations["inherited_holdout"].append(source_id)
    old_development_urls = {
        row.get("url")
        for row in old_sources.values()
        if row.get("dataset_role") == "development"
    }
    event_urls = {
        sources[source_id].get("url")
        for source_id in calibration_ids | final_ids
        if source_id in sources
    }
    if old_development_urls & event_urls:
        violations["partition"].append("development_event_url_overlap")

    for actor_id, expected in EXPECTED_ACTORS.items():
        if expected["role"] != "matched_contrast":
            continue
        non_identity = [
            row
            for row in sources.values()
            if row.get("actor_id") == actor_id
            and row.get("source_role") != "identity_provenance"
        ]
        if non_identity:
            violations["content_boundary"].append(f"{actor_id}:contrast_behavior_content")

    derived_manifest_counts = {
        "target_calibration_source_reservation_count": len(calibration_ids),
        "target_final_holdout_source_reservation_count": len(final_ids),
        "matched_contrast_person_count": sum(
            actor.get("role") == "matched_contrast"
            for actor in manifest.get("actors") or []
        ),
        "target_behavior_event_count": 0,
        "contrast_behavior_event_count": 0,
        "human_rater_count": 0,
        "model_response_count": 0,
        "persona_score_count": 0,
        "holdout_content_reviewed_count": 0,
        "raw_or_verbatim_record_count": 0,
        "training_authorized_record_count": 0,
    }
    for field, value in (manifest.get("current_counts") or {}).items():
        if not _is_nonnegative_integer(value):
            violations["count_honesty"].append(
                f"manifest_current_counts:{field}:non_negative_integer"
            )
    if manifest.get("current_counts") != derived_manifest_counts:
        violations["count_honesty"].append("manifest_current_counts")

    if rater_protocol.get("schema") != RATER_SCHEMA:
        violations["rater_protocol"].append("schema")
    if rater_protocol.get("target_id") != TARGET_ID:
        violations["rater_protocol"].append("target_id")
    if rater_protocol.get("setting") != "closed_consented_anonymous_evaluation":
        violations["rater_protocol"].append("setting")
    if set(rater_protocol.get("rater_groups") or {}) != {
        "target_familiar",
        "general_japanese",
    }:
        violations["rater_protocol"].append("rater_groups")
    assignment = rater_protocol.get("assignment_and_blinding") or {}
    for field in (
        "condition_labels_hidden",
        "system_architecture_hidden",
        "research_hypothesis_hidden_until_debrief",
        "response_order_randomized",
        "randomization_seed_frozen_before_collection",
        "same_item_compared_pairwise",
    ):
        if assignment.get(field) is not True:
            violations["rater_protocol"].append(field)
    if assignment.get("minimum_independent_ratings_per_item") != 3:
        violations["rater_protocol"].append("minimum_independent_ratings_per_item")
    consent = rater_protocol.get("consent") or {}
    for field in (
        "written_consent_required",
        "consent_version_hash_required",
        "voluntary_participation",
        "withdrawal_before_anonymized_lock_allowed",
        "debrief_required",
        "disclose_ai_simulation_and_non_affiliation_at_debrief",
        "no_public_impersonation",
    ):
        if consent.get(field) is not True:
            violations["rater_protocol"].append(f"consent:{field}")
    minimization = rater_protocol.get("data_minimization") or {}
    prohibited_fields = set(minimization.get("prohibited_fields") or [])
    for field in ("name", "email", "ip_address", "device_fingerprint", "social_account"):
        if field not in prohibited_fields:
            violations["rater_protocol"].append(f"missing_prohibited_field:{field}")
    if minimization.get("raw_identity_linkage_stored_with_ratings") is not False:
        violations["rater_protocol"].append("raw_identity_linkage")
    quality = rater_protocol.get("quality_and_exclusion") or {}
    if quality.get("rules_frozen_before_collection") is not True:
        violations["rater_protocol"].append("exclusion_rules_not_frozen")
    if quality.get("exclude_for_unfavorable_rating") is not False:
        violations["rater_protocol"].append("unfavorable_rating_exclusion")
    if "do not delete unfavorable raters" not in str(
        quality.get("low_agreement_handling") or ""
    ):
        violations["rater_protocol"].append("low_agreement_handling")
    if float(quality.get("minimum_usable_agreement") or 0) != 0.667:
        violations["rater_protocol"].append("minimum_usable_agreement")
    for field, value in (rater_protocol.get("current_counts") or {}).items():
        if not _is_nonnegative_integer(value):
            violations["count_honesty"].append(
                f"rater_protocol:{field}:non_negative_integer"
            )
    if any((rater_protocol.get("current_counts") or {}).values()):
        violations["count_honesty"].append("rater_protocol_nonzero_counts")
    rater_authorizations = rater_protocol.get("authorizations") or {}
    if rater_authorizations.get("consent_form_review") is not True:
        violations["rater_protocol"].append("consent_form_review")
    for field in ("rater_recruitment", "rating_collection", "public_persona_claim"):
        if rater_authorizations.get(field) is not False:
            violations["rater_protocol"].append(f"authorization:{field}")

    if readiness.get("schema") != READINESS_SCHEMA:
        violations["readiness"].append("schema")
    if readiness.get("target_id") != TARGET_ID:
        violations["readiness"].append("target_id")
    bindings = readiness.get("evidence_bindings") or {}
    for binding_name in (
        "target_calibration_manifest",
        "target_final_holdout_manifest",
        "contrast_reference_manifest",
        "blind_rater_protocol",
    ):
        if not _validate_binding(bindings.get(binding_name), Path(root)):
            violations["readiness_evidence"].append(binding_name)

    v1_formal = v1_result.get("formal_result") or {}
    expected_readiness_counts = {
        "target_development_observation_count": v1_formal.get(
            "development_observation_count"
        ),
        "sealed_target_source_reservation_count": len(final_ids),
        "target_calibration_source_count": len(calibration_ids),
        "target_calibration_event_count": 0,
        "target_final_holdout_source_count": len(final_ids),
        "target_final_holdout_event_count": 0,
        "matched_contrast_person_count": derived_manifest_counts[
            "matched_contrast_person_count"
        ],
        "contrast_event_count_per_person_min": 0,
        "same_topic_reference_pair_count": 0,
        "counterfactual_final_scenario_count": 0,
        "dynamic_multi_turn_episode_count": 0,
        "target_familiar_final_rater_count": 0,
        "general_japanese_final_rater_count": 0,
        "ratings_per_item_min": 0,
        "formal_agent_response_count": 0,
        "formal_persona_score_count": 0,
        "holdout_content_reviewed_count": 0,
        "holdout_label_available_count": 0,
        "raw_or_verbatim_record_count": 0,
        "training_authorized_record_count": 0,
    }
    counts = readiness.get("counts") or {}
    for field, value in counts.items():
        if not _is_nonnegative_integer(value):
            violations["count_honesty"].append(
                f"readiness_counts:{field}:non_negative_integer"
            )
    if counts != expected_readiness_counts:
        violations["count_honesty"].append("readiness_counts")
    flags = readiness.get("flags") or {}
    if set(flags) != EXPECTED_READINESS_FLAGS:
        violations["readiness"].append("flag_set")
    for field, value in flags.items():
        if not isinstance(value, bool):
            violations["readiness"].append(f"{field}:boolean")
    for field, value in (readiness.get("data_boundary") or {}).items():
        if value is not False:
            violations["content_boundary"].append(f"readiness:{field}")

    for count_name, binding_name in EVIDENCE_BINDING_REQUIREMENTS.items():
        if int(counts.get(count_name) or 0) > 0 and not _validate_binding(
            bindings.get(binding_name), Path(root)
        ):
            violations["readiness_evidence"].append(
                f"{count_name}:{binding_name}"
            )

    formal_minimum = v1_preregistration.get(
        "formal_execution_readiness_minimum"
    ) or {}
    if set(READINESS_COUNT_MAP) - set(formal_minimum):
        violations["readiness"].append("count_threshold_contract")
    if set(READINESS_FLAG_MAP) - set(formal_minimum):
        violations["readiness"].append("flag_threshold_contract")
    readiness_checks = {}
    for threshold_name, count_name in READINESS_COUNT_MAP.items():
        readiness_checks[count_name] = int(counts.get(count_name) or 0) >= int(
            formal_minimum.get(threshold_name) or 0
        )
    for threshold_name, flag_name in READINESS_FLAG_MAP.items():
        readiness_checks[flag_name] = (
            flags.get(flag_name) is True
            and bool(formal_minimum.get(threshold_name)) is True
        )
    readiness_checks["all_nonzero_claims_hash_bound"] = not violations[
        "readiness_evidence"
    ]
    readiness_derived = all(readiness_checks.values())
    if flags.get("formal_execution_ready") is not readiness_derived:
        violations["readiness"].append("formal_execution_ready:derived_mismatch")
    if flags.get("persona_fidelity_claim_available") is not False:
        violations["readiness"].append("persona_fidelity_claim_available")

    decision_policy = preregistration.get("decision_policy") or {}
    if decision_policy.get("protocol_pass") != PASS_DECISION:
        violations["authorization"].append("protocol_pass")
    if decision_policy.get("protocol_fail") != FAIL_DECISION:
        violations["authorization"].append("protocol_fail")
    for field in (
        "model_execution",
        "runtime_change",
        "prompt_change",
        "model_training",
        "behavior_content_coding",
        "rater_recruitment",
        "rating_collection",
        "sealed_holdout_unsealing",
        "formal_persona_scoring",
        "public_persona_fidelity_claim",
        "private_person_copy_claim",
    ):
        if decision_policy.get(field) is not False:
            violations["authorization"].append(field)

    protocol_checks = {
        "preregistration_is_falsifiable_and_narrow": not violations[
            "preregistration"
        ],
        "v1_authorization_dependency_matches": not violations["dependency"],
        "actors_selected_before_behavior_coding": not violations["actors"],
        "official_profile_and_channel_bound_for_each_actor": not violations[
            "official_identity"
        ],
        "target_source_reservations_exact": not violations["event_sources"],
        "development_calibration_holdout_are_disjoint": not violations[
            "partition"
        ],
        "inherited_v2_holdouts_preserved": not violations["inherited_holdout"],
        "official_rights_sources_and_conservative_use_bound": not violations[
            "rights_policy"
        ],
        "no_behavior_content_answers_or_training_payload": not violations[
            "content_boundary"
        ],
        "closed_consented_blind_rater_protocol_complete": not violations[
            "rater_protocol"
        ],
        "all_nonzero_readiness_claims_hash_bound": not violations[
            "readiness_evidence"
        ],
        "source_event_rater_model_score_counts_are_honest": not violations[
            "count_honesty"
        ]
        and not violations["readiness"],
        "authorization_remains_non_executing": not violations["authorization"],
    }
    protocol_passed = all(protocol_checks.values())
    formal_execution_ready = protocol_passed and readiness_derived
    decision = PASS_DECISION if protocol_passed else FAIL_DECISION
    compact_violations = {
        key: values for key, values in sorted(violations.items()) if values
    }
    return {
        "schema": "uruha_public_persona_reference_manifest_audit_v2",
        "experiment_id": EXPERIMENT_ID,
        "target_id": TARGET_ID,
        "protocol_passed": protocol_passed,
        "formal_execution_ready": formal_execution_ready,
        "persona_score_computed": False,
        "decision": decision,
        "summary": {
            "protocol_check_count": len(protocol_checks),
            "protocol_check_pass_count": sum(protocol_checks.values()),
            "readiness_check_count": len(readiness_checks),
            "readiness_check_pass_count": sum(readiness_checks.values()),
            "actor_count": len(manifest.get("actors") or []),
            "matched_contrast_person_count": counts.get(
                "matched_contrast_person_count", 0
            ),
            "official_identity_source_count": sum(
                row.get("source_role") == "identity_provenance"
                for row in manifest.get("sources") or []
            ),
            "target_calibration_source_count": counts.get(
                "target_calibration_source_count", 0
            ),
            "target_final_holdout_source_count": counts.get(
                "target_final_holdout_source_count", 0
            ),
            "target_behavior_event_count": 0,
            "contrast_behavior_event_count": 0,
            "human_rater_count": 0,
            "model_response_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "runtime_change_count": 0,
            "model_call_count": 0,
        },
        "protocol_checks": protocol_checks,
        "readiness_checks": readiness_checks,
        "readiness_current": counts,
        "readiness_required": formal_minimum,
        "violations": compact_violations,
        "actors": manifest.get("actors"),
        "source_reservations": {
            "calibration": [
                {
                    "source_id": source_id,
                    "published_at": sources[source_id].get("published_at"),
                    "context_family": sources[source_id].get("context_family"),
                    "behavior_reviewed": False,
                }
                for source_id in sorted(calibration_ids)
            ],
            "final_holdout": [
                {
                    "source_id": source_id,
                    "published_at": sources[source_id].get("published_at"),
                    "context_family": sources[source_id].get("context_family"),
                    "sealed": True,
                    "behavior_reviewed": False,
                }
                for source_id in sorted(final_ids)
            ],
        },
        "authorizations": {
            "metadata_only_event_coding_preregistration": protocol_passed,
            "consent_form_review": protocol_passed,
            "behavior_content_coding": False,
            "rater_recruitment": False,
            "rating_collection": False,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
        "next_required_evidence": (
            "先凍結 metadata-only 事件編碼表、來源權利逐筆審查表與知情同意書；"
            "仍不得執行模型、接觸評分者或打開最終 holdout。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格參考來源 V2 稽核",
        "",
        f"- 協定通過：`{report['protocol_passed']}` ({summary['protocol_check_pass_count']}/{summary['protocol_check_count']})",
        f"- 正式執行就緒：`{report['formal_execution_ready']}` ({summary['readiness_check_pass_count']}/{summary['readiness_check_count']})",
        f"- 人格分數已計算：`{report['persona_score_computed']}`",
        f"- 決策：`{report['decision']}`",
        "",
        "## 本輪新增的證據",
        "",
        "| 項目 | 已登記 | 已分析 |",
        "|---|---:|---:|",
        f"| 官方身份來源 | {summary['official_identity_source_count']} | 0 個人格事件 |",
        f"| 目標校準來源 | {summary['target_calibration_source_count']} | {summary['target_behavior_event_count']} 個事件 |",
        f"| 最終封存來源 | {summary['target_final_holdout_source_count']} | {summary['holdout_content_review_count']} 個內容 |",
        f"| 相近人物 | {summary['matched_contrast_person_count']} | {summary['contrast_behavior_event_count']} 個事件 |",
        f"| 真人評分者 | 0 | {summary['human_rater_count']} 份資料 |",
        f"| 模型回答／人格分數 | 0 | {summary['model_response_count']}／{summary['persona_score_count']} |",
        "",
        "**來源不是事件。** 登記影片網址與日期，只代表知道資料在哪裡；尚未觀看、編碼或建立目標答案，因此不能產生人格相似分數。",
        "",
        "## 公平對照人物",
        "",
        "| 角色 | 官方身份綁定 | 行為內容 |",
        "|---|---|---|",
    ]
    for actor in report["actors"]:
        lines.append(
            f"| {actor['public_name']} (`{actor['role']}`) | 官方成員頁 + 官方 YouTube | 未收集 |"
        )
    lines.extend(
        [
            "",
            "三位相近人物只控制同公司、日語、遊戲直播媒介；目前不主張她們與目標人物心理等價。",
            "",
            "## 盲評分工",
            "",
            "| 評分者 | 只評什麼 | 不評什麼 |",
            "|---|---|---|",
            "| 熟悉目標人物 | 公開人格相似、情境行為、信心 | 私人身分、一般語言分數冒充人格證據 |",
            "| 一般日語評分者 | 自然度、語意完整、模板重複、語言品質 | 目標人格相似度 |",
            "",
            "目前只完成規則；未招募、未評分，也不保存姓名、email、IP 或裝置指紋。",
            "",
            "## 本輪授權邊界",
            "",
            "可進行下一份 metadata-only 事件編碼預註冊與知情同意書審查。",
            "仍禁止內容編碼、評分者招募、模型執行、Prompt 修改、訓練、holdout 解封及人格主張。",
            "",
            "## 下一個缺口",
            "",
            report["next_required_evidence"],
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_audit_from_paths(
    preregistration_path=DEFAULT_PREREGISTRATION,
    manifest_path=DEFAULT_MANIFEST,
    rater_protocol_path=DEFAULT_RATER_PROTOCOL,
    readiness_path=DEFAULT_READINESS,
    v1_result_path=DEFAULT_V1_RESULT,
    v1_preregistration_path=DEFAULT_V1_PREREGISTRATION,
    v2_source_registry_path=DEFAULT_V2_SOURCE_REGISTRY,
):
    paths = {
        "preregistration": Path(preregistration_path),
        "source_manifest": Path(manifest_path),
        "blind_rater_protocol": Path(rater_protocol_path),
        "readiness_inventory": Path(readiness_path),
        "v1_result_lock": Path(v1_result_path),
        "v1_preregistration": Path(v1_preregistration_path),
        "v2_source_registry": Path(v2_source_registry_path),
    }
    report = audit(
        load_json(paths["preregistration"]),
        load_json(paths["source_manifest"]),
        load_json(paths["blind_rater_protocol"]),
        load_json(paths["readiness_inventory"]),
        load_json(paths["v1_result_lock"]),
        load_json(paths["v1_preregistration"]),
        load_json(paths["v2_source_registry"]),
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
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--rater-protocol", default=str(DEFAULT_RATER_PROTOCOL))
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS))
    parser.add_argument("--v1-result", default=str(DEFAULT_V1_RESULT))
    parser.add_argument("--v1-preregistration", default=str(DEFAULT_V1_PREREGISTRATION))
    parser.add_argument("--v2-source-registry", default=str(DEFAULT_V2_SOURCE_REGISTRY))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-protocol-pass", action="store_true")
    parser.add_argument("--require-execution-ready", action="store_true")
    args = parser.parse_args()

    report = build_audit_from_paths(
        args.preregistration,
        args.manifest,
        args.rater_protocol,
        args.readiness,
        args.v1_result,
        args.v1_preregistration,
        args.v2_source_registry,
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
                    f"{report['summary']['readiness_check_pass_count']}/"
                    f"{report['summary']['readiness_check_count']}"
                ),
                "persona_score_computed": report["persona_score_computed"],
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
