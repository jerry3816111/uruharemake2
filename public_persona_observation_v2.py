#!/usr/bin/env python3
"""Audit conditional public-persona observations and sealed source holdouts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH,
    PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_JSON_PATH,
    PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_MD_PATH,
    PUBLIC_PERSONA_OBSERVATIONS_V2_PATH,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_observation_v2_preregistration.json"
)
REGISTRY_SCHEMA = "uruha_public_persona_observation_source_registry_v2"
OBSERVATION_SCHEMA = "uruha_public_persona_observations_v2"
PREREGISTRATION_SCHEMA = "uruha_public_persona_observation_preregistration_v2"
EXPERIMENT_ID = "public_persona_observation_protocol_v2"
TARGET_ID = "ichinose_uruha_public_persona"
SOURCE_ROLES = {"behavior_observation", "sealed_holdout", "rights_policy"}
SOURCE_AUTHORITIES = {"target_official", "agency_official", "platform_official"}
SOURCE_ROLE_DATASET_ROLE = {
    "behavior_observation": "development",
    "sealed_holdout": "holdout",
    "rights_policy": "policy",
}
SOURCE_ROLE_METHOD = {
    "behavior_observation": "single_page_published_interface_review",
    "sealed_holdout": "metadata_only_reservation",
    "rights_policy": "official_policy_review",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
PROHIBITED_CONTENT_KEYS = {
    "raw_source_text",
    "raw_post_text",
    "source_excerpt",
    "verbatim_text",
    "transcript",
    "chat_replay",
    "raw_media",
    "raw_audio",
    "raw_video",
    "target_reply",
    "expected_reply",
    "fixed_response",
    "private_identity",
    "performer_identity",
}
PRIVATE_INFERENCE_TERMS = (
    "中之人",
    "本名",
    "私人住址",
    "未公開經歷",
    "演者身分",
)
COMMON_POLICY = {
    "metadata_storage": "allowed",
    "raw_source_text_storage": "not_authorized",
    "automated_bulk_collection": "not_authorized",
    "model_training_from_source_content": "not_authorized",
}
ROLE_PARAPHRASE_POLICY = {
    "behavior_observation": "development_only",
    "sealed_holdout": "not_authorized_before_candidate_freeze",
    "rights_policy": "policy_summary_only",
}
REQUIRED_DEPENDENCY = {
    "experiment_id": "public_persona_evidence_contract_v1",
    "required_decision": "authorize_public_persona_development_hypotheses_only",
}
PASS_DECISION = (
    "authorize_conditional_persona_development_hypotheses_and_sealed_holdout_protocol_only"
)
FORBIDDEN_PREREGISTRATION_AUTHORIZATIONS = (
    "runtime_persona_activation",
    "prompt_injection",
    "model_training",
    "holdout_unsealing",
    "holdout_evaluation_claim",
    "public_persona_fidelity_claim",
    "private_person_copy_claim",
)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _find_prohibited_keys(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in PROHIBITED_CONTENT_KEYS:
                found.append(child_path)
            found.extend(_find_prohibited_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_prohibited_keys(child, f"{prefix}[{index}]"))
    return found


def _private_inference_hits(value):
    serialized = json.dumps(value, ensure_ascii=False)
    return [term for term in PRIVATE_INFERENCE_TERMS if term in serialized]


def _source_policy_violations(source):
    source_id = str(source.get("source_id") or "")
    source_role = source.get("source_role")
    policy = source.get("project_use_policy") or {}
    violations = []
    for field, expected in COMMON_POLICY.items():
        if policy.get(field) != expected:
            violations.append(f"{source_id}:{field}")
    if policy.get("researcher_paraphrase_storage") != ROLE_PARAPHRASE_POLICY.get(
        source_role
    ):
        violations.append(f"{source_id}:researcher_paraphrase_storage")
    if policy.get("raw_media_storage") not in {"not_authorized", "not_applicable"}:
        violations.append(f"{source_id}:raw_media_storage")
    if policy.get("transcript_or_chat_replay_storage") not in {
        "not_authorized",
        "not_applicable",
    }:
        violations.append(f"{source_id}:transcript_or_chat_replay_storage")
    return violations


def audit(registry, dataset, preregistration):
    violations = defaultdict(list)
    sources = list(registry.get("sources") or [])
    observations = list(dataset.get("observations") or [])
    reservations = list(dataset.get("sealed_holdout_reservations") or [])
    source_ids = [str(row.get("source_id") or "") for row in sources]
    source_by_id = {str(row.get("source_id") or ""): row for row in sources}

    if registry.get("schema") != REGISTRY_SCHEMA:
        violations["schema"].append("source_registry_schema")
    if dataset.get("schema") != OBSERVATION_SCHEMA:
        violations["schema"].append("observation_dataset_schema")
    if preregistration.get("schema") != PREREGISTRATION_SCHEMA:
        violations["preregistration"].append("schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations["preregistration"].append("experiment_id")
    if preregistration.get("depends_on") != REQUIRED_DEPENDENCY:
        violations["preregistration"].append("dependency")
    preregistration_authorizations = preregistration.get("authorizations") or {}
    if preregistration_authorizations.get("on_pass") != PASS_DECISION:
        violations["preregistration"].append("on_pass")
    for authorization in FORBIDDEN_PREREGISTRATION_AUTHORIZATIONS:
        if preregistration_authorizations.get(authorization) is not False:
            violations["preregistration"].append(authorization)
    if not str(preregistration.get("single_changed_variable") or "").strip():
        violations["preregistration"].append("single_changed_variable")
    if not str(preregistration.get("evidence_boundary") or "").strip():
        violations["preregistration"].append("evidence_boundary")
    if registry.get("target_id") != TARGET_ID or dataset.get("target_id") != TARGET_ID:
        violations["schema"].append("target_id")
    if len(source_ids) != len(set(source_ids)) or not all(source_ids):
        violations["source_identity"].append("duplicate_or_empty_source_id")

    source_partition_roles = defaultdict(set)
    for source in sources:
        source_id = str(source.get("source_id") or "")
        source_role = source.get("source_role")
        dataset_role = source.get("dataset_role")
        authority = source.get("authority")
        partition = str(source.get("source_partition_key") or "")
        source_partition_roles[partition].add(str(dataset_role or ""))
        if source_role not in SOURCE_ROLES:
            violations["source_contract"].append(f"{source_id}:source_role")
        if authority not in SOURCE_AUTHORITIES:
            violations["source_contract"].append(f"{source_id}:authority")
        if dataset_role != SOURCE_ROLE_DATASET_ROLE.get(source_role):
            violations["source_contract"].append(f"{source_id}:dataset_role")
        if source.get("acquisition_method") != SOURCE_ROLE_METHOD.get(source_role):
            violations["source_contract"].append(f"{source_id}:acquisition_method")
        if not str(source.get("url") or "").startswith("https://"):
            violations["source_contract"].append(f"{source_id}:https_url")
        if not partition:
            violations["source_contract"].append(f"{source_id}:source_partition_key")
        if source.get("public_access_confirmed") is not True:
            violations["source_contract"].append(f"{source_id}:public_access")
        violations["source_policy"].extend(_source_policy_violations(source))
        if source_role != "rights_policy":
            policy_ids = list(source.get("policy_basis_source_ids") or [])
            if not policy_ids:
                violations["source_policy"].append(f"{source_id}:policy_basis_missing")
            for policy_id in policy_ids:
                policy_source = source_by_id.get(str(policy_id))
                if not policy_source or policy_source.get("source_role") != "rights_policy":
                    violations["source_policy"].append(
                        f"{source_id}:invalid_policy_basis:{policy_id}"
                    )

    construction = dataset.get("construction") or {}
    for field in (
        "contains_raw_source_text",
        "contains_raw_media",
        "contains_transcript_or_chat_replay",
        "contains_fixed_or_expected_replies",
        "training_authorized",
        "runtime_activation_authorized",
        "holdout_unsealing_authorized",
    ):
        if construction.get(field) is not False:
            violations["dataset_boundary"].append(f"construction:{field}")
    if construction.get("observation_form") != "researcher_paraphrase":
        violations["dataset_boundary"].append("construction:observation_form")

    violations["prohibited_content_key"].extend(_find_prohibited_keys(dataset))

    observation_ids = []
    observation_partitions = set()
    for row in observations:
        observation_id = str(row.get("observation_id") or "")
        observation_ids.append(observation_id)
        source_id = str(row.get("source_id") or "")
        source = source_by_id.get(source_id)
        partition = str(row.get("source_partition_key") or "")
        observation_partitions.add(partition)
        if not source or source.get("source_role") != "behavior_observation":
            violations["observation_source"].append(
                f"{observation_id}:behavior_source"
            )
        elif partition != source.get("source_partition_key"):
            violations["observation_source"].append(
                f"{observation_id}:partition_binding"
            )
        if row.get("dataset_role") != "development":
            violations["observation_contract"].append(
                f"{observation_id}:dataset_role"
            )
        if row.get("observation_method") != "single_page_published_interface_review":
            violations["observation_contract"].append(
                f"{observation_id}:observation_method"
            )
        if row.get("confidence") not in CONFIDENCE_LEVELS:
            violations["observation_contract"].append(
                f"{observation_id}:confidence"
            )
        for field in (
            "observation_id",
            "observed_modality",
            "context_type",
            "dimension",
            "observable_trigger",
            "behavior_paraphrase",
            "dialogue_act",
            "stance",
            "affect",
            "social_distance",
            "conditional_rule",
            "counterevidence_or_boundary",
        ):
            if not str(row.get(field) or "").strip():
                violations["observation_contract"].append(
                    f"{observation_id}:{field}"
                )
        for field in (
            "observable_trigger",
            "behavior_paraphrase",
            "conditional_rule",
            "counterevidence_or_boundary",
        ):
            if len(str(row.get(field) or "")) > 240:
                violations["observation_contract"].append(
                    f"{observation_id}:{field}_too_long"
                )
        private_claim_surface = {
            "observable_trigger": row.get("observable_trigger"),
            "behavior_paraphrase": row.get("behavior_paraphrase"),
            "conditional_rule": row.get("conditional_rule"),
        }
        violations["private_inference"].extend(
            f"{observation_id}:{term}"
            for term in _private_inference_hits(private_claim_surface)
        )
        for flag in (
            "contains_verbatim_source_text",
            "contains_target_reply",
            "private_person_inference",
            "training_authorized",
        ):
            if row.get(flag) is not False:
                violations["dataset_boundary"].append(
                    f"{observation_id}:{flag}"
                )

    if len(observation_ids) != len(set(observation_ids)) or not all(observation_ids):
        violations["observation_identity"].append(
            "duplicate_or_empty_observation_id"
        )

    reservation_ids = []
    reservation_partitions = set()
    for row in reservations:
        reservation_id = str(row.get("reservation_id") or "")
        reservation_ids.append(reservation_id)
        source_id = str(row.get("source_id") or "")
        source = source_by_id.get(source_id)
        partition = str(row.get("source_partition_key") or "")
        reservation_partitions.add(partition)
        if not source or source.get("source_role") != "sealed_holdout":
            violations["holdout_source"].append(
                f"{reservation_id}:sealed_source"
            )
        elif partition != source.get("source_partition_key"):
            violations["holdout_source"].append(
                f"{reservation_id}:partition_binding"
            )
        for field in ("reservation_id", "context_family", "evaluation_use"):
            if not str(row.get(field) or "").strip():
                violations["holdout_contract"].append(
                    f"{reservation_id}:{field}"
                )
        if row.get("dataset_role") != "holdout":
            violations["holdout_contract"].append(
                f"{reservation_id}:dataset_role"
            )
        expected_true = (
            "source_metadata_visible_only",
            "sealed",
            "candidate_freeze_required_before_unsealing",
        )
        for flag in expected_true:
            if row.get(flag) is not True:
                violations["holdout_contract"].append(
                    f"{reservation_id}:{flag}"
                )
        for flag in (
            "content_reviewed_for_behavior",
            "labels_available",
            "training_authorized",
        ):
            if row.get(flag) is not False:
                violations["holdout_contract"].append(
                    f"{reservation_id}:{flag}"
                )

    if len(reservation_ids) != len(set(reservation_ids)) or not all(reservation_ids):
        violations["holdout_identity"].append(
            "duplicate_or_empty_reservation_id"
        )

    source_role_overlap = sorted(
        partition
        for partition, roles in source_partition_roles.items()
        if not partition or len(roles) > 1
    )
    violations["source_partition_role_overlap"].extend(source_role_overlap)
    development_holdout_overlap = sorted(
        observation_partitions & reservation_partitions
    )
    violations["development_holdout_overlap"].extend(
        development_holdout_overlap
    )

    source_role_counts = Counter(
        str(row.get("source_role") or "") for row in sources
    )
    dimension_counts = Counter(
        str(row.get("dimension") or "") for row in observations
    )
    context_counts = Counter(
        str(row.get("context_type") or "") for row in observations
    )
    conditional_rule_count = sum(
        bool(str(row.get("conditional_rule") or "").strip()) for row in observations
    )
    counterevidence_count = sum(
        bool(str(row.get("counterevidence_or_boundary") or "").strip())
        for row in observations
    )
    holdout_content_reviewed_count = sum(
        row.get("content_reviewed_for_behavior") is not False
        for row in reservations
    )
    holdout_label_available_count = sum(
        row.get("labels_available") is not False for row in reservations
    )
    verbatim_count = sum(
        row.get("contains_verbatim_source_text") is not False
        for row in observations
    )
    target_reply_count = sum(
        row.get("contains_target_reply") is not False for row in observations
    )
    private_count = sum(
        row.get("private_person_inference") is not False for row in observations
    )
    training_authorized_count = sum(
        row.get("training_authorized") is not False
        for row in observations + reservations
    )

    thresholds = preregistration.get("minimum_contract") or {}
    threshold_checks = {
        "source_count": len(sources) >= int(thresholds.get("source_count") or 0),
        "development_source_count": source_role_counts["behavior_observation"]
        >= int(thresholds.get("development_source_count") or 0),
        "sealed_holdout_source_count": source_role_counts["sealed_holdout"]
        >= int(thresholds.get("sealed_holdout_source_count") or 0),
        "rights_policy_source_count": source_role_counts["rights_policy"]
        >= int(thresholds.get("rights_policy_source_count") or 0),
        "development_observation_count": len(observations)
        >= int(thresholds.get("development_observation_count") or 0),
        "distinct_dimension_count": len(dimension_counts)
        >= int(thresholds.get("distinct_dimension_count") or 0),
        "distinct_context_count": len(context_counts)
        >= int(thresholds.get("distinct_context_count") or 0),
        "conditional_rule_count": conditional_rule_count
        >= int(thresholds.get("conditional_rule_count") or 0),
        "counterevidence_or_boundary_count": counterevidence_count
        >= int(thresholds.get("counterevidence_or_boundary_count") or 0),
        "sealed_holdout_reservation_count": len(reservations)
        >= int(thresholds.get("sealed_holdout_reservation_count") or 0),
        "source_partition_role_overlap_count": len(source_role_overlap)
        <= int(thresholds.get("source_partition_role_overlap_count_max") or 0),
        "holdout_content_reviewed_count": holdout_content_reviewed_count
        <= int(thresholds.get("holdout_content_reviewed_count_max") or 0),
        "holdout_label_available_count": holdout_label_available_count
        <= int(thresholds.get("holdout_label_available_count_max") or 0),
        "verbatim_record_count": verbatim_count
        <= int(thresholds.get("verbatim_record_count_max") or 0),
        "target_reply_count": target_reply_count
        <= int(thresholds.get("target_reply_count_max") or 0),
        "private_identity_inference_count": private_count
        <= int(thresholds.get("private_identity_inference_count_max") or 0),
        "training_authorized_count": training_authorized_count
        <= int(thresholds.get("training_authorized_count_max") or 0),
    }
    contract_checks = {
        "schemas_and_target_match": not violations["schema"],
        "preregistration_is_narrow_and_dependency_bound": not violations[
            "preregistration"
        ],
        "unique_source_ids": not violations["source_identity"],
        "official_sources_and_roles": not violations["source_contract"],
        "conservative_source_policy": not violations["source_policy"],
        "dataset_boundary_is_non_training": not violations["dataset_boundary"],
        "no_prohibited_content_fields": not violations["prohibited_content_key"],
        "observations_bind_development_sources": not violations["observation_source"],
        "conditional_observation_contract_complete": not violations[
            "observation_contract"
        ],
        "unique_observation_ids": not violations["observation_identity"],
        "no_private_identity_inference": not violations["private_inference"],
        "holdouts_bind_sealed_sources": not violations["holdout_source"],
        "holdouts_remain_unreviewed_and_unlabeled": not violations[
            "holdout_contract"
        ],
        "unique_holdout_ids": not violations["holdout_identity"],
        "source_partitions_do_not_cross_roles": not violations[
            "source_partition_role_overlap"
        ],
        "development_and_holdout_are_source_disjoint": not violations[
            "development_holdout_overlap"
        ],
    }
    passed = all(contract_checks.values()) and all(threshold_checks.values())
    compact_violations = {
        key: values for key, values in sorted(violations.items()) if values
    }
    return {
        "schema": "uruha_public_persona_observation_audit_v2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_id": TARGET_ID,
        "passed": passed,
        "decision": (
            PASS_DECISION
            if passed
            else "stop_public_persona_observation_protocol"
        ),
        "summary": {
            "source_count": len(sources),
            "source_role_counts": dict(sorted(source_role_counts.items())),
            "development_observation_count": len(observations),
            "dimension_counts": dict(sorted(dimension_counts.items())),
            "context_counts": dict(sorted(context_counts.items())),
            "conditional_rule_count": conditional_rule_count,
            "counterevidence_or_boundary_count": counterevidence_count,
            "sealed_holdout_reservation_count": len(reservations),
            "source_partition_role_overlap_count": len(source_role_overlap),
            "development_holdout_overlap_count": len(development_holdout_overlap),
            "holdout_content_reviewed_count": holdout_content_reviewed_count,
            "holdout_label_available_count": holdout_label_available_count,
            "verbatim_record_count": verbatim_count,
            "target_reply_count": target_reply_count,
            "private_identity_inference_count": private_count,
            "training_authorized_count": training_authorized_count,
        },
        "contract_checks": contract_checks,
        "threshold_checks": threshold_checks,
        "violations": compact_violations,
        "observation_inventory": [
            {
                "observation_id": row.get("observation_id"),
                "source_id": row.get("source_id"),
                "context_type": row.get("context_type"),
                "dimension": row.get("dimension"),
                "conditional_rule": row.get("conditional_rule"),
                "counterevidence_or_boundary": row.get(
                    "counterevidence_or_boundary"
                ),
            }
            for row in observations
        ],
        "holdout_inventory": [
            {
                "reservation_id": row.get("reservation_id"),
                "source_id": row.get("source_id"),
                "context_family": row.get("context_family"),
                "sealed": row.get("sealed"),
                "content_reviewed_for_behavior": row.get(
                    "content_reviewed_for_behavior"
                ),
                "labels_available": row.get("labels_available"),
            }
            for row in reservations
        ],
        "source_inventory": [
            {
                "source_id": row.get("source_id"),
                "source_role": row.get("source_role"),
                "dataset_role": row.get("dataset_role"),
                "authority": row.get("authority"),
                "url": row.get("url"),
            }
            for row in sources
        ],
        "authorizations": {
            "conditional_development_hypothesis_use": passed,
            "sealed_holdout_protocol_ready": passed,
            "runtime_persona_activation": False,
            "prompt_injection": False,
            "model_training": False,
            "holdout_unsealing": False,
            "holdout_evaluation_claim": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
        "next_required_evidence": (
            "先凍結不含 holdout 內容的情境式人格行為契約與候選系統，再依預先定義的 "
            "程序打開 sealed holdout、獨立標註並比較完整系統與 matched control。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格情境觀察 V2 稽核",
        "",
        f"- 結果：`{report['decision']}`",
        f"- 契約通過：`{report['passed']}`",
        "- 允許：把條件式觀察當作開發假設，並保留 sealed holdout 來源。",
        "- 不允許：加入 Prompt、模型訓練、正式人格啟用、打開 holdout 或宣稱人格重現。",
        "",
        "| 項目 | 數量 |",
        "|---|---:|",
        f"| 官方與政策來源 | {summary['source_count']} |",
        f"| 開發觀察 | {summary['development_observation_count']} |",
        f"| 情境 | {len(summary['context_counts'])} |",
        f"| 人格維度 | {len(summary['dimension_counts'])} |",
        f"| 條件規則 | {summary['conditional_rule_count']} |",
        f"| 反例或邊界 | {summary['counterevidence_or_boundary_count']} |",
        f"| Sealed holdout | {summary['sealed_holdout_reservation_count']} |",
        f"| Holdout 已看內容 | {summary['holdout_content_reviewed_count']} |",
        f"| 逐字資料 | {summary['verbatim_record_count']} |",
        f"| 固定答案 | {summary['target_reply_count']} |",
        f"| 訓練授權 | {summary['training_authorized_count']} |",
        "",
        "## 條件式開發觀察",
        "",
        "| 觀察 | 情境 | 維度 | 條件規則 | 反例或邊界 |",
        "|---|---|---|---|---|",
    ]
    for row in report["observation_inventory"]:
        lines.append(
            f"| {row['observation_id']} | `{row['context_type']}` | `{row['dimension']}` | "
            f"{row['conditional_rule']} | {row['counterevidence_or_boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Sealed holdout",
            "",
            "| 預留 | 情境族 | 封存 | 已看內容 | 已有標籤 |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in report["holdout_inventory"]:
        lines.append(
            f"| {row['reservation_id']} | `{row['context_family']}` | "
            f"{row['sealed']} | {row['content_reviewed_for_behavior']} | "
            f"{row['labels_available']} |"
        )
    lines.extend(
        [
            "",
            "## 來源",
            "",
            "| 來源 | 角色 | URL |",
            "|---|---|---|",
        ]
    )
    for row in report["source_inventory"]:
        lines.append(
            f"| {row['source_id']} | {row['source_role']} / {row['dataset_role']} | "
            f"{row['url']} |"
        )
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            str(report["evidence_boundary"]),
            "",
            "下一步：" + report["next_required_evidence"],
        ]
    )
    return "\n".join(lines)


def build_audit_from_paths(registry_path, dataset_path, preregistration_path):
    registry = load_json(registry_path)
    dataset = load_json(dataset_path)
    preregistration = load_json(preregistration_path)
    report = audit(registry, dataset, preregistration)
    report["inputs"] = {
        "source_registry": {
            "path": Path(registry_path).name,
            "sha256": sha256_file(registry_path),
        },
        "observation_dataset": {
            "path": Path(dataset_path).name,
            "sha256": sha256_file(dataset_path),
        },
        "preregistration": {
            "path": Path(preregistration_path).name,
            "sha256": sha256_file(preregistration_path),
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry", default=PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH
    )
    parser.add_argument("--dataset", default=PUBLIC_PERSONA_OBSERVATIONS_V2_PATH)
    parser.add_argument("--preregistration", default=DEFAULT_PREREGISTRATION)
    parser.add_argument(
        "--output-json", default=PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_JSON_PATH
    )
    parser.add_argument(
        "--output-md", default=PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_MD_PATH
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    if not args.overwrite and (output_json.exists() or output_md.exists()):
        raise FileExistsError(
            "refusing to overwrite persona observation audit without --overwrite"
        )
    report = build_audit_from_paths(
        args.registry,
        args.dataset,
        args.preregistration,
    )
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "decision": report["decision"],
                "summary": report["summary"],
                "violations": report["violations"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if args.require_pass and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
