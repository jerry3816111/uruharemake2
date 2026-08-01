#!/usr/bin/env python3
"""Audit metadata-only matched-contrast public-persona sources."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_contrast_source_manifest_v4_preregistration.json"
)
DEFAULT_MANIFEST = (
    ROOT / "datasets/public_persona_contrast_source_manifest_v4.json"
)
DEFAULT_RIGHTS_REVIEW = (
    ROOT / "datasets/public_persona_contrast_source_rights_review_v1.json"
)
DEFAULT_V3_RESULT = (
    ROOT / "configs/public_persona_precontent_governance_v3_result_lock.json"
)
DEFAULT_REFERENCE_MANIFEST = (
    ROOT / "datasets/public_persona_reference_source_manifest_v2.json"
)
DEFAULT_EVENT_SCHEMA = ROOT / "configs/public_persona_event_coding_schema_v1.json"
DEFAULT_READINESS = (
    ROOT / "datasets/public_persona_fidelity_eval_v2_readiness_inventory.json"
)
DEFAULT_OUTPUT_JSON = (
    ROOT / "reports/public_persona_contrast_source_manifest_v4_audit.json"
)
DEFAULT_OUTPUT_MD = (
    ROOT / "reports/public_persona_contrast_source_manifest_v4_audit.md"
)

EXPERIMENT_ID = "public_persona_contrast_source_manifest_v4"
TARGET_ID = "ichinose_uruha_public_persona"
V3_REQUIRED_DECISION = (
    "authorize_bounded_calibration_event_coding_and_consent_usability_review_only"
)
PASS_DECISION = "authorize_contrast_event_coding_preregistration_only"
FAIL_DECISION = "repair_contrast_source_manifest_before_any_contrast_content_review"

EXPECTED_ACTORS = {
    "tachibana_hinano_public_persona": {
        "public_name": "橘ひなの",
        "channel_id": "UCvUc0m317LWTTPZoBQV479A",
        "channel_source_id": "youtube_channel_tachibana_hinano_20260801",
    },
    "kurumi_noa_public_persona": {
        "public_name": "胡桃のあ",
        "channel_id": "UCIcAj6WkJ8vZ7DeJVgmeqKw",
        "channel_source_id": "youtube_channel_kurumi_noa_20260801",
    },
    "tosaki_mimi_public_persona": {
        "public_name": "兎咲ミミ",
        "channel_id": "UCnvVG9RbOW3J6Ifqo-zKLiw",
        "channel_source_id": "youtube_channel_tosaki_mimi_20260801",
    },
}
EXPECTED_ANCHORS = {
    "competitive_fps": {
        "target_source_id": "uruha_calibration_youtube_valorant_20260318",
        "target_video_id": "cssf0abPOPw",
        "target_game_family": "valorant",
        "match_granularity": "exact_game",
    },
    "fighting_game": {
        "target_source_id": "uruha_calibration_youtube_street_fighter_20250317",
        "target_video_id": "M37jBhQWK_0",
        "target_game_family": "street_fighter_6",
        "match_granularity": "exact_game",
    },
    "simulation_game": {
        "target_source_id": "uruha_calibration_youtube_farming_20250308",
        "target_video_id": "6mpZwCihM0Q",
        "target_game_family": "farming_simulator_25",
        "match_granularity": "broad_family_only",
    },
}
EXPECTED_SOURCES = {
    "hinano_contrast_youtube_valorant_20220124": {
        "actor_id": "tachibana_hinano_public_persona",
        "video_id": "5cMCLipnycQ",
        "published_at": "2022-01-24",
        "duration_seconds": 5881,
        "topic_cell": "competitive_fps",
        "game_family": "valorant",
    },
    "hinano_contrast_youtube_sf6_20250331": {
        "actor_id": "tachibana_hinano_public_persona",
        "video_id": "xG7ssABsOiw",
        "published_at": "2025-03-31",
        "duration_seconds": 21859,
        "topic_cell": "fighting_game",
        "game_family": "street_fighter_6",
    },
    "hinano_contrast_youtube_supermarket_20240316": {
        "actor_id": "tachibana_hinano_public_persona",
        "video_id": "SvuHH_gLpQ0",
        "published_at": "2024-03-16",
        "duration_seconds": 19858,
        "topic_cell": "simulation_game",
        "game_family": "supermarket_simulator",
    },
    "noa_contrast_youtube_valorant_20220205": {
        "actor_id": "kurumi_noa_public_persona",
        "video_id": "Gve7tvDuPo4",
        "published_at": "2022-02-05",
        "duration_seconds": 14094,
        "topic_cell": "competitive_fps",
        "game_family": "valorant",
    },
    "noa_contrast_youtube_sf6_20250304": {
        "actor_id": "kurumi_noa_public_persona",
        "video_id": "8UDhvA1rJCY",
        "published_at": "2025-03-04",
        "duration_seconds": 5753,
        "topic_cell": "fighting_game",
        "game_family": "street_fighter_6",
    },
    "noa_contrast_youtube_supermarket_20240401": {
        "actor_id": "kurumi_noa_public_persona",
        "video_id": "BhnaGpqQ22k",
        "published_at": "2024-04-01",
        "duration_seconds": 13502,
        "topic_cell": "simulation_game",
        "game_family": "supermarket_simulator",
    },
    "mimi_contrast_youtube_valorant_20220120": {
        "actor_id": "tosaki_mimi_public_persona",
        "video_id": "dTKKsqZ1jH4",
        "published_at": "2022-01-20",
        "duration_seconds": 11320,
        "topic_cell": "competitive_fps",
        "game_family": "valorant",
    },
    "mimi_contrast_youtube_sf6_20241217": {
        "actor_id": "tosaki_mimi_public_persona",
        "video_id": "G0pouOLULwc",
        "published_at": "2024-12-17",
        "duration_seconds": 8559,
        "topic_cell": "fighting_game",
        "game_family": "street_fighter_6",
    },
    "mimi_contrast_youtube_supermarket_20240326": {
        "actor_id": "tosaki_mimi_public_persona",
        "video_id": "iADaCBk6HK4",
        "published_at": "2024-03-26",
        "duration_seconds": 16242,
        "topic_cell": "simulation_game",
        "game_family": "supermarket_simulator",
    },
}
EXPECTED_METADATA_FIELDS = {
    "video_id",
    "publisher_channel_id",
    "published_at",
    "duration_seconds",
    "live_status",
    "availability",
    "topic_cell",
    "game_family",
    "match_granularity",
}
PROHIBITED_PAYLOAD_KEYS = {
    "title",
    "description",
    "raw_text",
    "raw_source_text",
    "raw_media",
    "caption",
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


def _validate_dependency(preregistration, v3_result, root, violations):
    dependency = preregistration.get("depends_on") or {}
    if dependency.get("path") != (
        "configs/public_persona_precontent_governance_v3_result_lock.json"
    ):
        violations["dependency"].append("path")
    if not _binding_valid(dependency, root):
        violations["dependency"].append("hash_binding")
    if dependency.get("experiment_id") != "public_persona_precontent_governance_v3":
        violations["dependency"].append("experiment_id")
    if dependency.get("required_decision") != V3_REQUIRED_DECISION:
        violations["dependency"].append("required_decision")
    if dependency.get("required_authorization") != "contrast_event_source_registration":
        violations["dependency"].append("required_authorization")
    if v3_result.get("decision") != V3_REQUIRED_DECISION:
        violations["dependency"].append("result_decision")
    if v3_result.get("protocol_passed") is not True:
        violations["dependency"].append("result_protocol_passed")
    if (v3_result.get("authorizations") or {}).get(
        "contrast_event_source_registration"
    ) is not True:
        violations["dependency"].append("result_authorization")


def _validate_preregistration(preregistration, violations):
    if preregistration.get("schema") != (
        "uruha_public_persona_contrast_source_manifest_preregistration_v4"
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
    actor = preregistration.get("actor_contract") or {}
    for field, expected in (
        ("matched_contrast_actor_count_exact", 3),
        ("source_count_per_actor_exact", 3),
        ("topic_cell_count_per_actor_exact", 3),
    ):
        if actor.get(field) != expected:
            violations["preregistration"].append(f"actor_contract:{field}")
    topic = preregistration.get("topic_match_contract") or {}
    if set(topic.get("topic_cells") or []) != set(EXPECTED_ANCHORS):
        violations["preregistration"].append("topic_cells")
    if topic.get("exact_game_match_cells_per_actor") != 2:
        violations["preregistration"].append("exact_game_match_cells_per_actor")
    if topic.get("broad_family_match_cells_per_actor") != 1:
        violations["preregistration"].append("broad_family_match_cells_per_actor")
    for field in (
        "exact_and_broad_results_must_be_reported_separately",
        "broad_family_result_may_not_be_labeled_exact_topic",
    ):
        if topic.get(field) is not True:
            violations["preregistration"].append(field)
    if topic.get("same_topic_reference_pair_count_before_event_coding_exact") != 0:
        violations["preregistration"].append("same_topic_reference_pair_count")
    future = preregistration.get("future_event_sampling_contract") or {}
    if future.get("event_cap_per_source") != 10:
        violations["preregistration"].append("event_cap_per_source")
    if future.get("event_cap_per_actor") != 30:
        violations["preregistration"].append("event_cap_per_actor")
    for field in (
        "fixed_duration_chunking_forbidden",
        "overlapping_event_timestamps_forbidden",
        "independent_review_required",
        "separate_contrast_coding_preregistration_required",
    ):
        if future.get(field) is not True:
            violations["preregistration"].append(field)
    if future.get("current_contrast_event_coding_authorized") is not False:
        violations["preregistration"].append("current_coding_authorization")


def _validate_actors_and_anchors(manifest, reference_manifest, violations):
    actors = manifest.get("actors") or []
    actor_ids = [row.get("actor_id") for row in actors]
    if len(actors) != 3 or set(actor_ids) != set(EXPECTED_ACTORS):
        violations["actors"].append("actor_set")
    reference_sources = {
        row.get("source_id"): row for row in reference_manifest.get("sources") or []
    }
    for row in actors:
        actor_id = row.get("actor_id")
        expected = EXPECTED_ACTORS.get(actor_id) or {}
        if row.get("public_name") != expected.get("public_name"):
            violations["actors"].append(f"{actor_id}:public_name")
        if row.get("official_channel_id") != expected.get("channel_id"):
            violations["actors"].append(f"{actor_id}:channel_id")
        if row.get("official_channel_source_id") != expected.get("channel_source_id"):
            violations["actors"].append(f"{actor_id}:channel_source_id")
        channel = reference_sources.get(expected.get("channel_source_id")) or {}
        if channel.get("channel_id") != expected.get("channel_id"):
            violations["actors"].append(f"{actor_id}:reference_channel_binding")

    anchors = manifest.get("target_topic_anchors") or []
    anchor_index = {row.get("topic_cell"): row for row in anchors}
    if len(anchors) != 3 or set(anchor_index) != set(EXPECTED_ANCHORS):
        violations["anchors"].append("anchor_set")
    for topic_cell, expected in EXPECTED_ANCHORS.items():
        row = anchor_index.get(topic_cell) or {}
        for field, expected_value in (
            ("target_source_id", expected["target_source_id"]),
            ("target_video_id", expected["target_video_id"]),
            ("target_game_family", expected["target_game_family"]),
            ("allowed_match_granularity", expected["match_granularity"]),
        ):
            if row.get(field) != expected_value:
                violations["anchors"].append(f"{topic_cell}:{field}")
        source = reference_sources.get(expected["target_source_id"]) or {}
        if source.get("video_id") != expected["target_video_id"]:
            violations["anchors"].append(f"{topic_cell}:reference_source_binding")


def _validate_sources(manifest, reference_manifest, violations):
    sources = manifest.get("sources") or []
    source_ids = [row.get("source_id") for row in sources]
    video_ids = [row.get("video_id") for row in sources]
    partitions = [row.get("source_partition_key") for row in sources]
    urls = [row.get("url") for row in sources]
    if len(sources) != 9 or set(source_ids) != set(EXPECTED_SOURCES):
        violations["sources"].append("source_set")
    for label, values in (
        ("source_id", source_ids),
        ("video_id", video_ids),
        ("partition", partitions),
        ("url", urls),
    ):
        if not all(values) or len(values) != len(set(values)):
            violations["partition"].append(f"unique_{label}")

    reference_urls = {
        row.get("url") for row in reference_manifest.get("sources") or []
    }
    reference_partitions = {
        row.get("source_partition_key")
        for row in reference_manifest.get("sources") or []
    }
    if set(urls) & reference_urls:
        violations["partition"].append("reference_url_overlap")
    if set(partitions) & reference_partitions:
        violations["partition"].append("reference_partition_overlap")

    actor_topics = defaultdict(set)
    actor_counts = Counter()
    match_counts = Counter()
    for row in sources:
        source_id = row.get("source_id")
        expected = EXPECTED_SOURCES.get(source_id) or {}
        actor_id = expected.get("actor_id")
        actor = EXPECTED_ACTORS.get(actor_id) or {}
        topic = expected.get("topic_cell")
        anchor = EXPECTED_ANCHORS.get(topic) or {}
        for field, expected_value in (
            ("actor_id", actor_id),
            ("source_role", "contrast_calibration_reservation"),
            ("dataset_role", "contrast_calibration"),
            ("authority", "actor_official"),
            ("source_type", "official_public_stream_archive"),
            ("url", f"https://www.youtube.com/watch?v={expected.get('video_id')}"),
            ("video_id", expected.get("video_id")),
            ("publisher_channel_id", actor.get("channel_id")),
            ("published_at", expected.get("published_at")),
            ("duration_seconds", expected.get("duration_seconds")),
            ("live_status", "was_live"),
            ("availability", "public"),
            ("topic_cell", topic),
            ("game_family", expected.get("game_family")),
            ("target_anchor_source_id", anchor.get("target_source_id")),
            ("target_anchor_game_family", anchor.get("target_game_family")),
            ("match_granularity", anchor.get("match_granularity")),
            ("source_partition_key", f"youtube_archive_{expected.get('video_id')}"),
            ("content_review_scope", "metadata_only_unreviewed_for_behavior"),
            ("planned_event_cap", 10),
        ):
            if row.get(field) != expected_value:
                violations["sources"].append(f"{source_id}:{field}")
        if set(row.get("policy_basis_source_ids") or []) != {
            "youtube_terms_reference_v2_20260801",
            "vspo_guideline_reference_v2_20260801",
        }:
            violations["rights"].append(f"{source_id}:policy_basis")
        actor_topics[actor_id].add(topic)
        actor_counts[actor_id] += 1
        match_counts[row.get("match_granularity")] += 1

    for actor_id in EXPECTED_ACTORS:
        if actor_counts[actor_id] != 3:
            violations["matrix"].append(f"{actor_id}:source_count")
        if actor_topics[actor_id] != set(EXPECTED_ANCHORS):
            violations["matrix"].append(f"{actor_id}:topic_cells")
    if match_counts != Counter({"exact_game": 6, "broad_family_only": 3}):
        violations["matrix"].append("match_granularity_counts")

    common = manifest.get("common_source_flags") or {}
    if set(common.get("metadata_fields_reviewed") or []) != EXPECTED_METADATA_FIELDS:
        violations["content_boundary"].append("metadata_fields_reviewed")
    for field in (
        "content_reviewed_for_behavior",
        "labels_available",
        "raw_media_stored",
        "raw_transcript_stored",
        "candidate_answer_available",
        "model_output_available",
        "title_stored",
        "selected_from_behavior_content",
        "selected_from_model_outputs_or_similarity_scores",
    ):
        if common.get(field) is not False:
            violations["content_boundary"].append(field)
    prohibited = _find_prohibited_keys(manifest)
    if prohibited:
        violations["content_boundary"].extend(prohibited)


def _validate_counts_and_authorization(manifest, preregistration, violations):
    expected_counts = {
        "contrast_source_reservation_count": 9,
        "contrast_actor_count": 3,
        "topic_cell_count": 9,
        "exact_game_match_source_count": 6,
        "broad_family_match_source_count": 3,
        "contrast_behavior_event_count": 0,
        "independently_reviewed_event_count": 0,
        "same_topic_reference_pair_count": 0,
        "raw_or_verbatim_record_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
    }
    counts = manifest.get("current_counts") or {}
    if counts != expected_counts:
        violations["count_honesty"].append("manifest_current_counts")
    if any(not _is_nonnegative_integer(value) for value in counts.values()):
        violations["count_honesty"].append("nonnegative_integer_counts")
    auth = manifest.get("authorizations") or {}
    for field in (
        "metadata_only_source_registration",
        "contrast_event_coding_preregistration",
    ):
        if auth.get(field) is not True:
            violations["authorization"].append(f"manifest:{field}")
    for field in (
        "contrast_behavior_content_review",
        "model_execution",
        "prompt_memory_retrieval_or_training_use",
        "persona_scoring",
        "sealed_holdout_access",
    ):
        if auth.get(field) is not False:
            violations["authorization"].append(f"manifest:{field}")

    policy = preregistration.get("decision_policy") or {}
    if policy.get("protocol_pass") != PASS_DECISION:
        violations["authorization"].append("protocol_pass")
    if policy.get("protocol_fail") != FAIL_DECISION:
        violations["authorization"].append("protocol_fail")
    if policy.get("contrast_event_coding_preregistration") is not True:
        violations["authorization"].append("contrast_event_coding_preregistration")
    for field in (
        "contrast_behavior_content_review",
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


def _validate_rights_review(rights_review, manifest, root, violations):
    if rights_review.get("schema") != (
        "uruha_public_persona_contrast_source_rights_review_v1"
    ):
        violations["rights"].append("schema")
    if not _binding_valid(rights_review.get("contrast_manifest_binding"), root):
        violations["rights"].append("manifest_binding")
    policy = rights_review.get("review_policy") or {}
    for field in (
        "public_access_is_not_training_permission",
        "public_access_is_not_a_rights_holder_license",
        "metadata_locator_storage",
    ):
        if policy.get(field) is not True:
            violations["rights"].append(field)
    for field in (
        "bounded_manual_behavior_observation",
        "researcher_behavior_paraphrase",
        "timestamp_locator_storage",
        "raw_media_storage",
        "verbatim_transcript_storage",
        "automated_bulk_collection",
        "model_training",
        "prompt_memory_or_retrieval_use",
        "runtime_persona_activation",
        "public_source_content_redistribution",
        "legal_opinion_claimed",
        "rights_holder_permission_claimed",
    ):
        if policy.get(field) is not False:
            violations["rights"].append(field)

    manifest_index = {
        row.get("source_id"): row for row in manifest.get("sources") or []
    }
    reviews = rights_review.get("source_reviews") or []
    review_index = {row.get("source_id"): row for row in reviews}
    if len(reviews) != 9 or set(review_index) != set(manifest_index):
        violations["rights"].append("source_review_set")
    if len(review_index) != len(reviews):
        violations["rights"].append("duplicate_review")
    for source_id, source in manifest_index.items():
        review = review_index.get(source_id) or {}
        if review.get("actor_id") != source.get("actor_id"):
            violations["rights"].append(f"{source_id}:actor_id")
        if review.get("current_disposition") != (
            "metadata_only_pending_contrast_coding_preregistration"
        ):
            violations["rights"].append(f"{source_id}:disposition")
        for field in ("public_access_verified", "official_channel_verified"):
            if review.get(field) is not True:
                violations["rights"].append(f"{source_id}:{field}")
    completion = rights_review.get("review_completion") or {}
    if completion.get("registered_source_locator_count") != 9:
        violations["rights"].append("registered_source_locator_count")
    if completion.get("registered_source_locator_reviewed_count") != 9:
        violations["rights"].append("reviewed_count")
    if completion.get("behavior_content_reviewed_count") != 0:
        violations["rights"].append("behavior_content_reviewed_count")
    if completion.get("contrast_behavior_use_authorized") is not False:
        violations["rights"].append("contrast_behavior_use_authorized")
    if completion.get("formal_corpus_rights_review_complete") is not False:
        violations["rights"].append("formal_corpus_rights_review_complete")
    counts = rights_review.get("current_counts") or {}
    if not counts or any(value != 0 for value in counts.values()):
        violations["count_honesty"].append("rights_review_counts")


def audit(
    preregistration,
    manifest,
    rights_review,
    v3_result,
    reference_manifest,
    event_schema,
    readiness,
    root=ROOT,
):
    violations = defaultdict(list)
    _validate_preregistration(preregistration, violations)
    _validate_dependency(preregistration, v3_result, root, violations)
    if manifest.get("schema") != "uruha_public_persona_contrast_source_manifest_v4":
        violations["manifest"].append("schema")
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        violations["manifest"].append("experiment_id")
    if manifest.get("target_id") != TARGET_ID:
        violations["manifest"].append("target_id")
    if not _binding_valid(manifest.get("source_manifest_binding"), root):
        violations["manifest"].append("source_manifest_binding")
    if not _binding_valid(manifest.get("event_schema_binding"), root):
        violations["manifest"].append("event_schema_binding")
    _validate_actors_and_anchors(manifest, reference_manifest, violations)
    _validate_sources(manifest, reference_manifest, violations)
    _validate_counts_and_authorization(manifest, preregistration, violations)
    _validate_rights_review(rights_review, manifest, root, violations)

    if event_schema.get("status") != "protocol_only_no_behavior_events_reviewed":
        violations["dependency"].append("event_schema_status")
    if any((event_schema.get("current_counts") or {}).values()):
        violations["count_honesty"].append("event_schema_counts")
    v3_formal = v3_result.get("formal_result") or {}
    if v3_formal.get("formal_readiness_pass_count") != 4:
        violations["readiness"].append("formal_readiness_pass_count")
    if v3_formal.get("formal_readiness_check_count") != 19:
        violations["readiness"].append("formal_readiness_check_count")
    if v3_result.get("formal_execution_ready") is not False:
        violations["readiness"].append("formal_execution_ready")
    counts = readiness.get("counts") or {}
    if counts.get("contrast_event_count_per_person_min") != 0:
        violations["readiness"].append("contrast_event_count")
    if counts.get("same_topic_reference_pair_count") != 0:
        violations["readiness"].append("same_topic_reference_pair_count")

    protocol_checks = {
        "preregistration_is_falsifiable_and_metadata_only": not violations[
            "preregistration"
        ],
        "v3_dependency_and_authorization_are_hash_bound": not violations[
            "dependency"
        ],
        "manifest_and_event_schema_bindings_match": not violations["manifest"],
        "three_preselected_contrast_actors_match_official_channels": not violations[
            "actors"
        ],
        "three_target_topic_anchors_match_registered_calibration_sources": not violations[
            "anchors"
        ],
        "nine_official_source_reservations_match_frozen_metadata": not violations[
            "sources"
        ],
        "three_by_three_actor_topic_matrix_is_complete": not violations["matrix"],
        "source_partitions_are_unique_and_disjoint_from_target": not violations[
            "partition"
        ],
        "six_exact_game_and_three_broad_family_matches_are_separate": not violations[
            "matrix"
        ]
        and not violations["preregistration"],
        "no_titles_behavior_content_transcripts_answers_or_outputs_stored": not violations[
            "content_boundary"
        ],
        "all_nine_sources_have_conservative_metadata_only_rights_review": not violations[
            "rights"
        ],
        "source_event_pair_output_score_and_holdout_counts_are_honest": not violations[
            "count_honesty"
        ],
        "formal_readiness_remains_four_of_nineteen": not violations["readiness"],
        "authorization_is_limited_to_next_contrast_coding_preregistration": not violations[
            "authorization"
        ],
    }
    protocol_passed = all(protocol_checks.values())
    decision = PASS_DECISION if protocol_passed else FAIL_DECISION
    compact_violations = {
        key: value for key, value in sorted(violations.items()) if value
    }
    source_rows = manifest.get("sources") or []
    manifest_counts = manifest.get("current_counts") or {}
    actor_ids = {row.get("actor_id") for row in source_rows if row.get("actor_id")}
    actor_topic_pairs = {
        (row.get("actor_id"), row.get("topic_cell"))
        for row in source_rows
        if row.get("actor_id") and row.get("topic_cell")
    }
    match_counts = Counter(row.get("match_granularity") for row in source_rows)
    match_topics = defaultdict(set)
    for row in source_rows:
        if row.get("match_granularity") and row.get("topic_cell"):
            match_topics[row["match_granularity"]].add(row["topic_cell"])

    def observed_count(field):
        value = manifest_counts.get(field)
        return value if _is_nonnegative_integer(value) else None

    return {
        "schema": "uruha_public_persona_contrast_source_manifest_audit_v4",
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
            "contrast_actor_count": len(actor_ids),
            "contrast_source_reservation_count": len(source_rows),
            "topic_cell_count": len(actor_topic_pairs),
            "exact_game_match_source_count": match_counts["exact_game"],
            "broad_family_match_source_count": match_counts["broad_family_only"],
            "contrast_behavior_event_count": observed_count(
                "contrast_behavior_event_count"
            ),
            "independently_reviewed_event_count": observed_count(
                "independently_reviewed_event_count"
            ),
            "same_topic_reference_pair_count": observed_count(
                "same_topic_reference_pair_count"
            ),
            "model_response_count": observed_count("model_output_count"),
            "persona_score_count": observed_count("persona_score_count"),
            "holdout_content_review_count": observed_count(
                "holdout_content_review_count"
            ),
            "runtime_change_count": 0,
            "model_call_count": 0,
        },
        "protocol_checks": protocol_checks,
        "violations": compact_violations,
        "actor_topic_matrix": [
            {
                "actor_id": actor_id,
                "public_name": expected["public_name"],
                "source_count": sum(
                    row.get("actor_id") == actor_id
                    for row in manifest.get("sources") or []
                ),
                "topic_cells": sorted(
                    row.get("topic_cell")
                    for row in manifest.get("sources") or []
                    if row.get("actor_id") == actor_id
                ),
            }
            for actor_id, expected in EXPECTED_ACTORS.items()
        ],
        "match_strength": {
            "exact_game": {
                "source_count": match_counts["exact_game"],
                "topic_cells": sorted(match_topics["exact_game"]),
                "claim_boundary": "same game family, but behavior events are not yet coded",
            },
            "broad_family_only": {
                "source_count": match_counts["broad_family_only"],
                "topic_cells": sorted(match_topics["broad_family_only"]),
                "claim_boundary": "same simulation-game family but different games; cannot be labeled exact-topic evidence",
            },
        },
        "authorizations": {
            "contrast_event_coding_preregistration": protocol_passed,
            "contrast_behavior_content_review": False,
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
            "先凍結 contrast-only 事件編碼預註冊，將每個來源上限固定為 10 個非重疊事件，"
            "再進行獨立覆核；目前仍不得觀看或編碼對照內容。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格相近人物來源 V4 稽核",
        "",
        f"- 協定通過：`{report['protocol_passed']}` ({summary['protocol_check_pass_count']}/{summary['protocol_check_count']})",
        f"- 正式評測就緒：`{report['formal_execution_ready']}` ({summary['formal_readiness_pass_count']}/{summary['formal_readiness_check_count']})",
        f"- 決策：`{report['decision']}`",
        "",
        "## 公平對照現在補了什麼",
        "",
        "| 相近人物 | VALORANT | Street Fighter 6 | 模擬遊戲 |",
        "|---|---|---|---|",
    ]
    for row in report["actor_topic_matrix"]:
        lines.append(
            f"| {row['public_name']} | 官方來源 1 | 官方來源 1 | 官方來源 1 |"
        )
    lines.extend(
        [
            "",
            f"共 {summary['contrast_actor_count']} 人、{summary['contrast_source_reservation_count']} 個官方來源、{summary['topic_cell_count']} 個人物 x 主題格。",
            "",
            "## 匹配強度不能混在一起",
            "",
            "| 匹配層級 | 來源數 | 可說什麼 |",
            "|---|---:|---|",
            f"| 同遊戲 | {summary['exact_game_match_source_count']} | VALORANT、Street Fighter 6 可作 exact-game 對照 |",
            f"| 同類型 | {summary['broad_family_match_source_count']} | 模擬遊戲不同款，只能作 broad-family 對照 |",
            "",
            "模擬遊戲的三筆資料不得被寫成『同一遊戲』，後續結果也不能與 exact-game 分數合併成單一結論。",
            "",
            "## 來源仍不是行為事件",
            "",
            "| 行為事件 | 獨立覆核 | 同主題配對 | 模型回答 | 人格分數 | holdout 查看 |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {summary['contrast_behavior_event_count']} | {summary['independently_reviewed_event_count']} | {summary['same_topic_reference_pair_count']} | {summary['model_response_count']} | {summary['persona_score_count']} | {summary['holdout_content_review_count']} |",
            "",
            "本輪只保存官方 URL、頻道、影片 ID、日期、長度、公開狀態與主題格；沒有保存標題、字幕、留言、逐字稿、原句或影片內容。",
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
    )
    return "\n".join(lines)


def build_audit_from_paths(
    preregistration_path=DEFAULT_PREREGISTRATION,
    manifest_path=DEFAULT_MANIFEST,
    rights_review_path=DEFAULT_RIGHTS_REVIEW,
    v3_result_path=DEFAULT_V3_RESULT,
    reference_manifest_path=DEFAULT_REFERENCE_MANIFEST,
    event_schema_path=DEFAULT_EVENT_SCHEMA,
    readiness_path=DEFAULT_READINESS,
):
    paths = {
        "preregistration": Path(preregistration_path),
        "contrast_manifest": Path(manifest_path),
        "rights_review": Path(rights_review_path),
        "v3_result_lock": Path(v3_result_path),
        "reference_manifest": Path(reference_manifest_path),
        "event_schema": Path(event_schema_path),
        "readiness_inventory": Path(readiness_path),
    }
    report = audit(
        load_json(paths["preregistration"]),
        load_json(paths["contrast_manifest"]),
        load_json(paths["rights_review"]),
        load_json(paths["v3_result_lock"]),
        load_json(paths["reference_manifest"]),
        load_json(paths["event_schema"]),
        load_json(paths["readiness_inventory"]),
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
    parser.add_argument("--rights-review", default=str(DEFAULT_RIGHTS_REVIEW))
    parser.add_argument("--v3-result", default=str(DEFAULT_V3_RESULT))
    parser.add_argument("--reference-manifest", default=str(DEFAULT_REFERENCE_MANIFEST))
    parser.add_argument("--event-schema", default=str(DEFAULT_EVENT_SCHEMA))
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-protocol-pass", action="store_true")
    parser.add_argument("--require-execution-ready", action="store_true")
    args = parser.parse_args()

    report = build_audit_from_paths(
        args.preregistration,
        args.manifest,
        args.rights_review,
        args.v3_result,
        args.reference_manifest,
        args.event_schema,
        args.readiness,
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
