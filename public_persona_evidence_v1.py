#!/usr/bin/env python3
"""Audit provenance and claim boundaries for public-persona evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_JSON_PATH,
    PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_MD_PATH,
    PUBLIC_PERSONA_EVIDENCE_V1_PATH,
    PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = ROOT / "configs/public_persona_evidence_v1_preregistration.json"
REGISTRY_SCHEMA = "uruha_public_persona_source_registry_v1"
EVIDENCE_SCHEMA = "uruha_public_persona_evidence_v1"
TARGET_ID = "ichinose_uruha_public_persona"
PERSONA_AUTHORITIES = {"agency_official", "target_official"}
SOURCE_ROLES = {"persona_evidence", "rights_policy"}
DATASET_ROLES = {"development", "calibration", "holdout"}
INFERENCE_LEVELS = {
    "official_description",
    "official_channel_description",
    "direct_observation",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
PROHIBITED_CONTENT_KEYS = {
    "raw_media",
    "raw_audio",
    "raw_video",
    "transcript",
    "verbatim_text",
    "source_text",
    "target_reply",
    "expected_reply",
    "fixed_response",
    "private_identity",
    "performer_identity",
}
PRIVATE_INFERENCE_TERMS = ("中之人", "本名", "私人住址", "未公開經歷", "演者身分")
REQUIRED_SOURCE_POLICY = {
    "metadata_storage": "allowed",
    "researcher_paraphrase_storage": "allowed",
    "verbatim_transcript_storage": "not_authorized",
    "automated_collection": "not_authorized",
    "model_training_from_source_content": "not_authorized",
}


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
    policy = source.get("project_use_policy") or {}
    violations = []
    for field, expected in REQUIRED_SOURCE_POLICY.items():
        if policy.get(field) != expected:
            violations.append(f"{source.get('source_id')}:{field}")
    raw_status = policy.get("raw_media_storage")
    if raw_status not in {"not_authorized", "not_applicable"}:
        violations.append(f"{source.get('source_id')}:raw_media_storage")
    return violations


def audit(registry, evidence_dataset, preregistration):
    violations = defaultdict(list)
    sources = list(registry.get("sources") or [])
    evidence_rows = list(evidence_dataset.get("evidence") or [])
    source_ids = [str(row.get("source_id") or "") for row in sources]
    source_by_id = {str(row.get("source_id") or ""): row for row in sources}

    if registry.get("schema") != REGISTRY_SCHEMA:
        violations["schema"].append("source_registry_schema")
    if evidence_dataset.get("schema") != EVIDENCE_SCHEMA:
        violations["schema"].append("evidence_dataset_schema")
    if registry.get("target_id") != TARGET_ID or evidence_dataset.get("target_id") != TARGET_ID:
        violations["schema"].append("target_id")
    if len(source_ids) != len(set(source_ids)) or not all(source_ids):
        violations["source_identity"].append("duplicate_or_empty_source_id")

    for source in sources:
        source_id = str(source.get("source_id") or "")
        role = source.get("source_role")
        authority = source.get("authority")
        if role not in SOURCE_ROLES:
            violations["source_contract"].append(f"{source_id}:source_role")
        if role == "persona_evidence" and authority not in PERSONA_AUTHORITIES:
            violations["source_contract"].append(f"{source_id}:persona_authority")
        if not str(source.get("url") or "").startswith("https://"):
            violations["source_contract"].append(f"{source_id}:https_url")
        if not source.get("source_partition_key"):
            violations["source_contract"].append(f"{source_id}:source_partition_key")
        if source.get("public_access_confirmed") is not True:
            violations["source_contract"].append(f"{source_id}:public_access")
        if source.get("acquisition_method") != "manual_public_review":
            violations["source_contract"].append(f"{source_id}:acquisition_method")
        violations["source_policy"].extend(_source_policy_violations(source))
        for policy_source_id in source.get("policy_basis_source_ids") or []:
            policy_source = source_by_id.get(str(policy_source_id))
            if not policy_source or policy_source.get("source_role") != "rights_policy":
                violations["source_policy"].append(f"{source_id}:invalid_policy_basis")

    construction = evidence_dataset.get("construction") or {}
    expected_false = (
        "contains_raw_media",
        "contains_verbatim_transcript",
        "contains_fixed_or_expected_replies",
        "training_authorized",
        "holdout_evaluation_authorized",
    )
    for field in expected_false:
        if construction.get(field) is not False:
            violations["dataset_boundary"].append(f"construction:{field}")
    if construction.get("observation_form") != "researcher_paraphrase":
        violations["dataset_boundary"].append("construction:observation_form")

    prohibited_paths = _find_prohibited_keys(evidence_dataset)
    violations["prohibited_content_key"].extend(prohibited_paths)
    evidence_ids = []
    partition_roles = defaultdict(set)
    for row in evidence_rows:
        evidence_id = str(row.get("evidence_id") or "")
        evidence_ids.append(evidence_id)
        source_id = str(row.get("source_id") or "")
        source = source_by_id.get(source_id)
        if not source or source.get("source_role") != "persona_evidence":
            violations["evidence_source"].append(f"{evidence_id}:persona_source")
        elif row.get("source_partition_key") != source.get("source_partition_key"):
            violations["evidence_source"].append(f"{evidence_id}:partition_binding")
        role = row.get("dataset_role")
        if role not in DATASET_ROLES:
            violations["evidence_contract"].append(f"{evidence_id}:dataset_role")
        partition_roles[str(row.get("source_partition_key") or "")].add(str(role or ""))
        if row.get("inference_level") not in INFERENCE_LEVELS:
            violations["evidence_contract"].append(f"{evidence_id}:inference_level")
        if row.get("confidence") not in CONFIDENCE_LEVELS:
            violations["evidence_contract"].append(f"{evidence_id}:confidence")
        if row.get("claim_use") != "development_hypothesis_only":
            violations["evidence_contract"].append(f"{evidence_id}:claim_use")
        for field in (
            "evidence_id",
            "dimension",
            "trait_key",
            "observable_behavior",
            "conditional_context",
            "generalization_limit",
        ):
            if not str(row.get(field) or "").strip():
                violations["evidence_contract"].append(f"{evidence_id}:{field}")
        if len(str(row.get("observable_behavior") or "")) > 180:
            violations["evidence_contract"].append(f"{evidence_id}:paraphrase_too_long")
        private_claim_surface = {
            "trait_key": row.get("trait_key"),
            "observable_behavior": row.get("observable_behavior"),
            "conditional_context": row.get("conditional_context"),
        }
        violations["private_inference"].extend(
            f"{evidence_id}:{term}" for term in _private_inference_hits(private_claim_surface)
        )
        for flag in (
            "contains_verbatim_source_text",
            "contains_target_reply",
            "private_person_inference",
            "training_authorized",
        ):
            if row.get(flag) is not False:
                violations["dataset_boundary"].append(f"{evidence_id}:{flag}")

    if len(evidence_ids) != len(set(evidence_ids)) or not all(evidence_ids):
        violations["evidence_identity"].append("duplicate_or_empty_evidence_id")
    role_overlap_partitions = sorted(
        partition for partition, roles in partition_roles.items() if len(roles) > 1
    )
    violations["partition_role_overlap"].extend(role_overlap_partitions)

    source_role_counts = Counter(str(row.get("source_role") or "") for row in sources)
    authority_counts = Counter(str(row.get("authority") or "") for row in sources)
    dimension_counts = Counter(str(row.get("dimension") or "") for row in evidence_rows)
    source_evidence_counts = Counter(str(row.get("source_id") or "") for row in evidence_rows)
    dataset_role_counts = Counter(str(row.get("dataset_role") or "") for row in evidence_rows)
    training_authorized_count = sum(row.get("training_authorized") is not False for row in evidence_rows)
    verbatim_count = sum(row.get("contains_verbatim_source_text") is not False for row in evidence_rows)
    target_reply_count = sum(row.get("contains_target_reply") is not False for row in evidence_rows)
    private_count = sum(row.get("private_person_inference") is not False for row in evidence_rows)

    thresholds = preregistration.get("minimum_seed_contract") or {}
    threshold_checks = {
        "source_count": len(sources) >= int(thresholds.get("source_count") or 0),
        "persona_evidence_source_count": source_role_counts["persona_evidence"]
        >= int(thresholds.get("persona_evidence_source_count") or 0),
        "rights_policy_source_count": source_role_counts["rights_policy"]
        >= int(thresholds.get("rights_policy_source_count") or 0),
        "evidence_count": len(evidence_rows) >= int(thresholds.get("evidence_count") or 0),
        "distinct_dimension_count": len(dimension_counts)
        >= int(thresholds.get("distinct_dimension_count") or 0),
        "allowed_dataset_roles": set(dataset_role_counts)
        <= set(thresholds.get("allowed_dataset_roles") or []),
        "partition_role_overlap_count": len(role_overlap_partitions)
        <= int(thresholds.get("source_partition_role_overlap_count_max") or 0),
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
        "unique_source_ids": not violations["source_identity"],
        "official_persona_sources_only": not violations["source_contract"],
        "complete_conservative_source_policy": not violations["source_policy"],
        "dataset_boundary_is_development_only": not violations["dataset_boundary"],
        "no_prohibited_content_fields": not violations["prohibited_content_key"],
        "no_private_identity_inference": not violations["private_inference"],
        "evidence_references_persona_sources": not violations["evidence_source"],
        "evidence_contract_complete": not violations["evidence_contract"],
        "unique_evidence_ids": not violations["evidence_identity"],
        "source_partitions_do_not_cross_roles": not violations["partition_role_overlap"],
    }
    passed = all(contract_checks.values()) and all(threshold_checks.values())
    compact_violations = {
        key: values for key, values in sorted(violations.items()) if values
    }
    return {
        "schema": "uruha_public_persona_evidence_audit_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_id": TARGET_ID,
        "passed": passed,
        "decision": (
            "authorize_public_persona_development_hypotheses_only"
            if passed
            else "stop_public_persona_evidence_contract"
        ),
        "summary": {
            "source_count": len(sources),
            "source_role_counts": dict(sorted(source_role_counts.items())),
            "authority_counts": dict(sorted(authority_counts.items())),
            "evidence_count": len(evidence_rows),
            "dimension_counts": dict(sorted(dimension_counts.items())),
            "trait_keys": sorted(str(row.get("trait_key") or "") for row in evidence_rows),
            "source_evidence_counts": dict(sorted(source_evidence_counts.items())),
            "dataset_role_counts": dict(sorted(dataset_role_counts.items())),
            "source_partition_role_overlap_count": len(role_overlap_partitions),
            "verbatim_record_count": verbatim_count,
            "target_reply_count": target_reply_count,
            "private_identity_inference_count": private_count,
            "training_authorized_count": training_authorized_count,
        },
        "contract_checks": contract_checks,
        "threshold_checks": threshold_checks,
        "violations": compact_violations,
        "source_inventory": [
            {
                "source_id": row.get("source_id"),
                "source_role": row.get("source_role"),
                "authority": row.get("authority"),
                "url": row.get("url"),
            }
            for row in sources
        ],
        "evidence_inventory": [
            {
                "evidence_id": row.get("evidence_id"),
                "source_id": row.get("source_id"),
                "dataset_role": row.get("dataset_role"),
                "dimension": row.get("dimension"),
                "trait_key": row.get("trait_key"),
            }
            for row in evidence_rows
        ],
        "authorizations": {
            "development_hypothesis_use": passed,
            "runtime_persona_activation": False,
            "model_training": False,
            "holdout_evaluation": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
        "next_required_evidence": (
            "在任何人格重現評測前，加入經權利邊界檢查、人工轉述標記，且開發集與 "
            "holdout 來源互斥的公開直播觀察。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格證據層 V1 稽核",
        "",
        f"- 結果：`{report['decision']}`",
        f"- 契約通過：`{report['passed']}`",
        "- 允許用途：建立可追溯的開發假設。",
        "- 不允許用途：模型訓練、正式人格啟用、holdout 分數或本人完整人格主張。",
        "- 權利說明：這是保守的專案政策，不是法律判定；沒有明確許可前不抓逐字稿、不拿原文訓練。",
        "",
        "| 項目 | 數量 |",
        "|---|---:|",
        f"| 官方/本人來源與政策來源 | {summary['source_count']} |",
        f"| 人格證據 | {summary['evidence_count']} |",
        f"| 能力維度 | {len(summary['dimension_counts'])} |",
        f"| 逐字資料 | {summary['verbatim_record_count']} |",
        f"| 固定答案 | {summary['target_reply_count']} |",
        f"| 私人身分推測 | {summary['private_identity_inference_count']} |",
        f"| 訓練授權資料 | {summary['training_authorized_count']} |",
        "",
        "## 六個發展假設",
        "",
        "| 證據 | 維度 | 假設 | 來源 |",
        "|---|---|---|---|",
    ]
    for row in report["evidence_inventory"]:
        lines.append(
            f"| {row['evidence_id']} | `{row['dimension']}` | `{row['trait_key']}` | {row['source_id']} |"
        )
    lines.extend(["", "## 來源", "", "| 來源 | 身分 | URL |", "|---|---|---|"])
    for row in report["source_inventory"]:
        lines.append(
            f"| {row['source_id']} | {row['authority']} / {row['source_role']} | {row['url']} |"
        )
    lines.extend(
        [
            "",
            "## 邊界",
            "",
            str(report["evidence_boundary"]),
            "",
            "下一步：" + report["next_required_evidence"],
        ]
    )
    return "\n".join(lines)


def build_audit_from_paths(registry_path, evidence_path, preregistration_path):
    registry = load_json(registry_path)
    evidence_dataset = load_json(evidence_path)
    preregistration = load_json(preregistration_path)
    report = audit(registry, evidence_dataset, preregistration)
    report["inputs"] = {
        "source_registry": {
            "path": Path(registry_path).name,
            "sha256": sha256_file(registry_path),
        },
        "evidence_dataset": {
            "path": Path(evidence_path).name,
            "sha256": sha256_file(evidence_path),
        },
        "preregistration": {
            "path": Path(preregistration_path).name,
            "sha256": sha256_file(preregistration_path),
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH)
    parser.add_argument("--evidence", default=PUBLIC_PERSONA_EVIDENCE_V1_PATH)
    parser.add_argument("--preregistration", default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--output-json", default=PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_JSON_PATH)
    parser.add_argument("--output-md", default=PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_MD_PATH)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    if not args.overwrite and (output_json.exists() or output_md.exists()):
        raise FileExistsError("refusing to overwrite persona evidence audit without --overwrite")
    report = build_audit_from_paths(args.registry, args.evidence, args.preregistration)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
