#!/usr/bin/env python3
"""Audit whether the promoted RightBrain was trained on its active contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import run_rightbrain_carrier_model_screen_v1 as carrier_screen


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_current_contract_curriculum_audit_v1"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_current_contract_curriculum_audit_v1_preregistration.json"
)
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_current_contract_curriculum_audit_v1.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_current_contract_curriculum_audit_v1.md"


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalized_text(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return "".join(character for character in text if character.isalnum())


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob(revision, path):
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT
    )


def flatten_contract(value, path=""):
    """Return container paths and scalar/list-item values for a JSON contract."""

    paths = set()
    values = defaultdict(set)
    if path:
        paths.add(path)
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            child_paths, child_values = flatten_contract(item, child)
            paths.update(child_paths)
            for value_path, entries in child_values.items():
                values[value_path].update(entries)
    elif isinstance(value, list):
        list_path = f"{path}[]"
        paths.add(list_path)
        for item in value:
            if isinstance(item, (dict, list)):
                child_paths, child_values = flatten_contract(item, list_path)
                paths.update(child_paths)
                for value_path, entries in child_values.items():
                    values[value_path].update(entries)
            else:
                values[list_path].add(canonical_json(item))
    else:
        values[path].add(canonical_json(value))
    return paths, values


def merge_contract_profiles(payloads):
    all_paths = set()
    all_values = defaultdict(set)
    row_path_counts = Counter()
    for payload in payloads:
        paths, values = flatten_contract(payload)
        all_paths.update(paths)
        row_path_counts.update(paths)
        for path, entries in values.items():
            all_values[path].update(entries)
    return {
        "paths": all_paths,
        "values": all_values,
        "row_path_counts": row_path_counts,
    }


def parse_training_rows(raw_bytes, source):
    rows = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"training source is not a row list: {source['stage']}")
    parsed = []
    for row in rows:
        messages = row.get("messages") or []
        user_messages = [message for message in messages if message.get("role") == "user"]
        assistant_messages = [message for message in messages if message.get("role") == "assistant"]
        system_messages = [message for message in messages if message.get("role") == "system"]
        if len(system_messages) != 1 or len(user_messages) != 1 or len(assistant_messages) != 1:
            raise ValueError(f"invalid message roles in {source['stage']}:{row.get('id')}")
        parsed.append(
            {
                "stage": source["stage"],
                "row": row,
                "system_instruction": str(system_messages[0]["content"] or ""),
                "payload": json.loads(user_messages[0]["content"]),
                "target": str(assistant_messages[0]["content"] or "").strip(),
            }
        )
    return parsed


def reconstruct_training_sources(preregistration):
    parsed_rows = []
    source_reports = []
    for source in preregistration["frozen_inputs"]["contract_training_sources"]:
        raw = git_blob(source["git_revision"], source["path"])
        actual_hash = sha256_bytes(raw)
        rows = parse_training_rows(raw, source)
        current_path = ROOT / source["path"]
        current_hash = sha256_file(current_path) if current_path.is_file() else None
        source_reports.append(
            {
                **source,
                "actual_sha256": actual_hash,
                "actual_rows": len(rows),
                "hash_match": actual_hash == source["sha256"],
                "row_count_match": len(rows) == source["rows"],
                "current_path_sha256": current_hash,
                "current_path_matches_historical_source": current_hash == source["sha256"],
            }
        )
        parsed_rows.extend(rows)
    return parsed_rows, source_reports


def validate_file_bindings(preregistration):
    reports = {}
    for key, binding in preregistration["frozen_inputs"].items():
        if not isinstance(binding, dict) or "path" not in binding or "sha256" not in binding:
            continue
        path = ROOT / binding["path"]
        actual = sha256_file(path) if path.is_file() else None
        reports[key] = {
            "path": binding["path"],
            "expected_sha256": binding["sha256"],
            "actual_sha256": actual,
            "match": actual == binding["sha256"],
        }
    return reports


def current_reference_payloads(preregistration):
    bundle = load_json(ROOT / preregistration["frozen_inputs"]["current_reference_cases"]["path"])
    rows = []
    for case in bundle["cases"]:
        for provider_id in case["condition_order"]:
            _, _, _, payload_text, system_instruction = carrier_screen.build_case_input(
                case, provider_id
            )
            rows.append(
                {
                    "case_id": case["case_id"],
                    "provider_id": provider_id,
                    "payload": json.loads(payload_text),
                    "payload_sha256": sha256_bytes(payload_text.encode("utf-8")),
                    "system_instruction": system_instruction,
                }
            )
    return bundle, rows


def path_coverage(current_profile, training_profile, prefix=None):
    current_paths = {
        path for path in current_profile["paths"] if prefix is None or path.startswith(prefix)
    }
    covered = current_paths & training_profile["paths"]
    missing = current_paths - training_profile["paths"]
    return {
        "current_path_count": len(current_paths),
        "covered_path_count": len(covered),
        "coverage": round(len(covered) / len(current_paths), 6) if current_paths else 1.0,
        "covered_paths": sorted(covered),
        "missing_paths": sorted(missing),
    }


def value_coverage(current_profile, training_profile, prefix):
    expected = set()
    covered = set()
    for path, values in current_profile["values"].items():
        if not path.startswith(prefix):
            continue
        for value in values:
            pair = (path, value)
            expected.add(pair)
            if value in training_profile["values"].get(path, set()):
                covered.add(pair)
    missing = expected - covered
    encode = lambda pair: {"path": pair[0], "value": json.loads(pair[1])}
    return {
        "current_value_count": len(expected),
        "covered_value_count": len(covered),
        "coverage": round(len(covered) / len(expected), 6) if expected else 1.0,
        "missing_values": [encode(pair) for pair in sorted(missing)],
    }


def has_joint_contract(payload):
    context = payload.get("context") or {}
    memory = context.get("audited_memory_brief") or {}
    persona = context.get("persona_expression_brief") or {}
    expression = persona.get("expression_policy") or {}
    return all(
        (
            bool(payload.get("required_marker_groups")),
            "policy" in memory,
            "forbidden" in memory,
            bool(persona.get("conditional_context")),
            bool(expression.get("operations")),
            bool(expression.get("avoid")),
            "forbidden_markers" in payload,
            "procedural_guidance" in context,
        )
    )


def is_static_persona_row(payload):
    persona = (payload.get("context") or {}).get("persona_expression_brief") or {}
    return bool(persona) and not persona.get("conditional_context") and not persona.get("expression_policy")


def normalized_failure_family(reason, family_rules):
    reason = str(reason or "")
    for family, markers in family_rules.items():
        if any(reason == marker or reason.startswith(f"{marker}:") for marker in markers):
            return family
    return None


def failure_coverage(training_rows, observed_report, family_rules):
    training_counts = Counter()
    for item in training_rows:
        for reason in item["row"].get("failure_reasons") or []:
            family = normalized_failure_family(reason, family_rules)
            if family:
                training_counts[family] += 1
    observed = observed_report["summary"].get("rejection_families") or {}
    rows = []
    for family, count in sorted(observed.items()):
        rows.append(
            {
                "family": family,
                "observed_failure_count": int(count),
                "documented_training_row_count": training_counts[family],
                "covered": training_counts[family] > 0,
            }
        )
    return {
        "observed_family_count": len(rows),
        "covered_family_count": sum(row["covered"] for row in rows),
        "families": rows,
    }


def contains_key(value, forbidden_keys):
    if isinstance(value, dict):
        return any(
            key in forbidden_keys or contains_key(item, forbidden_keys)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_key(item, forbidden_keys) for item in value)
    return False


def separation_audit(bundle, current_rows, training_rows, observed_report):
    current_inputs = {row["payload"].get("user_input", "") for row in current_rows}
    training_inputs = {item["payload"].get("user_input", "") for item in training_rows}
    current_normalized = {normalized_text(value) for value in current_inputs if value}
    training_normalized = {normalized_text(value) for value in training_inputs if value}
    current_payloads = {canonical_json(row["payload"]) for row in current_rows}
    training_payloads = {canonical_json(item["payload"]) for item in training_rows}
    generated = {
        str(row.get("raw_generation") or "").strip()
        for row in observed_report.get("generations") or []
        if str(row.get("raw_generation") or "").strip()
    }
    targets = {item["target"] for item in training_rows if item["target"]}
    forbidden_case_keys = {"expected_reply", "correct_answer", "gold_answer", "answer_key"}
    checks = {
        "exact_user_input_overlap_count": len(current_inputs & training_inputs),
        "normalized_user_input_overlap_count": len(current_normalized & training_normalized),
        "exact_payload_overlap_count": len(current_payloads & training_payloads),
        "exact_generated_output_to_training_target_overlap_count": len(generated & targets),
        "contains_expected_answer_field": contains_key(bundle, forbidden_case_keys),
        "contains_benchmark_items": bool(bundle.get("contains_benchmark_items")),
        "contains_target_utterances": bool(bundle.get("contains_target_utterances")),
        "contains_expected_replies": bool(bundle.get("contains_expected_replies")),
    }
    passed = all(
        value == 0 for key, value in checks.items() if key.endswith("_count")
    ) and not any(value for key, value in checks.items() if not key.endswith("_count"))
    return {"passed": passed, "checks": checks}


def provenance_audit(training_rows):
    required = {"source_url", "source_date", "source_timestamp", "data_split"}
    complete = 0
    for item in training_rows:
        row = item["row"]
        if required.issubset(row) and all(row.get(key) for key in required):
            complete += 1
    target_count = len({item["target"] for item in training_rows if item["target"]})
    return {
        "training_row_count": len(training_rows),
        "rows_with_complete_public_source_provenance": complete,
        "public_source_provenance_coverage": round(complete / len(training_rows), 6),
        "unique_target_count": target_count,
        "persona_evidence_interpretation": (
            "The curriculum can be audited as generic surface training, but it cannot serve as "
            "evidence of target-person public-persona similarity."
        ),
    }


def source_unit_key(item):
    row = item["row"]
    if row.get("source_id"):
        source = ["source_id", row["source_id"]]
    elif row.get("source_case_id"):
        source = [
            "source_case",
            row["source_case_id"],
            row.get("target_variant_index"),
        ]
    else:
        source = ["row_id", row.get("id")]
    return canonical_json([source, item["target"]])


def instruction_contract_audit(current_rows, training_rows):
    current_system = {row["system_instruction"] for row in current_rows}
    training_system = {item["system_instruction"] for item in training_rows}
    current_requirements = {
        canonical_json(value)
        for row in current_rows
        for value in row["payload"].get("reply_requirements") or []
    }
    training_requirements = {
        canonical_json(value)
        for item in training_rows
        for value in item["payload"].get("reply_requirements") or []
    }
    retired = training_requirements - current_requirements
    return {
        "current_unique_system_instruction_count": len(current_system),
        "training_unique_system_instruction_count": len(training_system),
        "current_system_instruction_seen_in_training": bool(current_system & training_system),
        "training_rows_with_current_system_instruction": sum(
            item["system_instruction"] in current_system for item in training_rows
        ),
        "current_reply_requirement_count": len(current_requirements),
        "current_reply_requirements_covered_count": len(
            current_requirements & training_requirements
        ),
        "retired_training_only_reply_requirements": [
            json.loads(value) for value in sorted(retired)
        ],
        "rows_still_teaching_no_first_person_private": sum(
            "no first person 私" in (item["payload"].get("reply_requirements") or [])
            for item in training_rows
        ),
    }


def verify_training_run_lineage(preregistration, source_reports):
    v8 = load_json(ROOT / preregistration["frozen_inputs"]["v8_training_run"]["path"])
    v10 = load_json(ROOT / preregistration["frozen_inputs"]["v10_training_run"]["path"])
    by_stage = {row["stage"]: row for row in source_reports}
    v10_sources = {row["role"]: row for row in v10.get("dataset_sources") or []}
    checks = {
        "v8_output_adapter": v8.get("output_adapter_ref")
        == "uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5",
        "v8_dataset_hash": v8.get("dataset_sha256") == by_stage["v8_primary"]["sha256"],
        "v10_init_is_v8": v10.get("init_adapter_ref") == v8.get("output_adapter_ref"),
        "v10_output_adapter": v10.get("output_adapter_ref")
        == preregistration["promoted_adapter"]["adapter_ref"],
        "v10_primary_hash": (v10_sources.get("primary") or {}).get("sha256")
        == by_stage["v10_primary"]["sha256"],
        "v10_supplemental_hash": (v10_sources.get("supplemental") or {}).get("sha256")
        == by_stage["v10_supplemental"]["sha256"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "documented_contract_stage_rows": sum(row["actual_rows"] for row in source_reports),
        "pre_contract_ancestor": v8.get("init_adapter_ref"),
        "pre_contract_ancestor_curriculum_reconstructable": False,
    }


def build_report(preregistration_path=DEFAULT_PREREGISTRATION):
    preregistration = load_json(preregistration_path)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("wrong preregistration experiment")
    bindings = validate_file_bindings(preregistration)
    training_rows, source_reports = reconstruct_training_sources(preregistration)
    bundle, current_rows = current_reference_payloads(preregistration)
    training_payloads = [item["payload"] for item in training_rows]
    current_payloads = [row["payload"] for row in current_rows]
    current_profile = merge_contract_profiles(current_payloads)
    training_profile = merge_contract_profiles(training_payloads)
    overall_paths = path_coverage(current_profile, training_profile)
    persona_paths = path_coverage(
        current_profile, training_profile, "context.persona_expression_brief"
    )
    memory_paths = path_coverage(
        current_profile, training_profile, "context.audited_memory_brief"
    )
    persona_values = value_coverage(
        current_profile, training_profile, "context.persona_expression_brief"
    )
    memory_values = value_coverage(
        current_profile, training_profile, "context.audited_memory_brief"
    )
    observed_report = load_json(
        ROOT / preregistration["frozen_inputs"]["observed_failure_evidence"]["path"]
    )
    lineage = verify_training_run_lineage(preregistration, source_reports)
    source_reconstruction_pass = all(
        row["hash_match"] and row["row_count_match"] for row in source_reports
    ) and lineage["passed"] and all(row["match"] for row in bindings.values())
    joint_training_rows = sum(has_joint_contract(payload) for payload in training_payloads)
    joint_current_rows = sum(has_joint_contract(payload) for payload in current_payloads)
    static_persona_rows = sum(is_static_persona_row(payload) for payload in training_payloads)
    failure = failure_coverage(
        training_rows,
        observed_report,
        preregistration["audit_design"]["failure_family_normalization"],
    )
    separation = separation_audit(bundle, current_rows, training_rows, observed_report)
    instruction_contract = instruction_contract_audit(current_rows, training_rows)
    unique_source_units = len({source_unit_key(item) for item in training_rows})
    measurable_gap = bool(persona_paths["missing_paths"] or joint_training_rows == 0)
    observed_strict = observed_report["summary"]["strict_valid_generation_count"]
    observed_total = observed_report["summary"]["generation_count"]
    authorize = all(
        (
            source_reconstruction_pass,
            observed_strict < 9,
            measurable_gap,
            separation["passed"],
        )
    )
    if not source_reconstruction_pass or not separation["passed"]:
        decision = "insufficient_evidence"
    elif authorize:
        decision = "authorize_person_independent_role_specialization_curriculum_construction_only"
    else:
        decision = "reject_role_specialization_curriculum_direction"

    report = {
        "schema": "uruha_rightbrain_current_contract_curriculum_audit_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "completed",
        "preregistration": {
            "path": str(Path(preregistration_path).relative_to(ROOT)),
            "sha256": sha256_file(preregistration_path),
            "status": preregistration["status"],
        },
        "accounting": {
            "actual_model_generation_call_count": 0,
            "model_training_run_count": 0,
            "production_memory_write_count": 0,
            "current_reference_payload_count": len(current_rows),
            "documented_contract_stage_exposure_count": len(training_rows),
            "unique_underlying_training_unit_count": unique_source_units,
        },
        "bindings": bindings,
        "source_reconstruction": {
            "passed": source_reconstruction_pass,
            "sources": source_reports,
            "lineage": lineage,
        },
        "coverage": {
            "overall_active_path_coverage": overall_paths,
            "persona_policy_path_coverage": persona_paths,
            "audited_memory_path_coverage": memory_paths,
            "persona_policy_value_coverage": persona_values,
            "audited_memory_value_coverage": memory_values,
            "current_joint_contract_row_count": joint_current_rows,
            "documented_training_joint_contract_row_count": joint_training_rows,
            "documented_static_persona_row_count": static_persona_rows,
            "optional_inactive_fields_excluded": [
                "output_budget",
                "surface_failure_watchlist",
                "compact_payload",
            ],
        },
        "instruction_contract": instruction_contract,
        "observed_failure_alignment": {
            "strict_valid_count": observed_strict,
            "generation_count": observed_total,
            "strict_valid_rate": round(observed_strict / observed_total, 6),
            **failure,
        },
        "development_separation": separation,
        "training_provenance": provenance_audit(training_rows),
        "decision": {
            "outcome": decision,
            "measurable_current_contract_gap": measurable_gap,
            "authorize_curriculum_construction": authorize,
            "authorize_model_training": False,
            "authorize_production_change": False,
            "authorize_persona_similarity_claim": False,
            "causal_claim_supported": False,
            "next_authorized_step": (
                "Construct and audit a source-separated, person-independent role-specialization "
                "curriculum that teaches the missing current contract fields without using these "
                "five development cases, target-person utterances, benchmark items, or fixed replies."
                if authorize
                else "Do not construct a new curriculum from this evidence."
            ),
        },
    }
    return report


def markdown_report(report):
    coverage = report["coverage"]
    decision = report["decision"]
    failure = report["observed_failure_alignment"]
    lines = [
        "# 現行右腦契約與正式訓練教材覆蓋率稽核 V1",
        "",
        "## 結論",
        "",
        "正式載入的 v10 右腦確實學過基本的語意契約、記憶可說性與輸出禁則，",
        "但沒有學過現行條件式人格政策的完整結構，也沒有任何一筆教材同時包含",
        "人格政策、語意義務、記憶政策、禁用詞與程序指引。這是可量化的教材／介面落差，",
        "但尚未證明它就是生成失敗的因果來源。",
        "",
        "| 檢查 | 結果 |",
        "|---|---:|",
        f"| 可重建的契約階段訓練曝光 | {report['accounting']['documented_contract_stage_exposure_count']} 次 |",
        f"| 去除 v8／v10 重複後的底層單元 | {report['accounting']['unique_underlying_training_unit_count']} 筆 |",
        f"| 現行 payload | {report['accounting']['current_reference_payload_count']} 筆 |",
        f"| 全部現行路徑覆蓋 | {coverage['overall_active_path_coverage']['coverage']:.1%} |",
        f"| 人格政策路徑覆蓋 | {coverage['persona_policy_path_coverage']['coverage']:.1%} |",
        f"| 人格政策值覆蓋 | {coverage['persona_policy_value_coverage']['coverage']:.1%} |",
        f"| 現行完整聯合契約 payload | {coverage['current_joint_contract_row_count']} 筆 |",
        f"| 教材中的完整聯合契約 | {coverage['documented_training_joint_contract_row_count']} 筆 |",
        f"| 舊式靜態人格教材 | {coverage['documented_static_persona_row_count']} 筆 |",
        f"| 與現行完全相同的 system prompt 教材 | {report['instruction_contract']['training_rows_with_current_system_instruction']} 筆 |",
        f"| 仍教『不得使用私』的舊教材 | {report['instruction_contract']['rows_still_teaching_no_first_person_private']} 筆 |",
        f"| 目前本機模型嚴格通過 | {failure['strict_valid_count']}/{failure['generation_count']} ({failure['strict_valid_rate']:.1%}) |",
        "",
        "## 缺少的主要教學內容",
        "",
    ]
    for path in coverage["persona_policy_path_coverage"]["missing_paths"]:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "這表示模型過去看到的主要是固定的 `lazy_short / slightly_bratty` 靜態標籤，",
            "而不是現行系統依情境給出的語氣、能量、社交距離、表達操作與避免規則。",
            "此外，現行 structured provider 已不再禁止第一人稱，但舊教材仍全部包含 `no first person 私`，",
            "所以模型學到的輸出限制也與現在的 system prompt 不完全一致。",
            "",
            "## 已教過但仍會失敗的部分",
            "",
            "| 失敗類型 | 實際失敗 | 有標註教材 |",
            "|---|---:|---:|",
        ]
    )
    for row in failure["families"]:
        lines.append(
            f"| {row['family']} | {row['observed_failure_count']} | "
            f"{row['documented_training_row_count']} |"
        )
    lines.extend(
        [
            "",
            "語言污染、敬語漂移與必要語意遺失都有早期修復教材，但模型仍會失敗。",
            "因此下一輪不能只是重複增加同類句子，而要教它理解現行結構中每個角色欄位。",
            "",
            "## 研究可信度",
            "",
            f"- Git 歷史來源與訓練紀錄可重建：{'通過' if report['source_reconstruction']['passed'] else '未通過'}。",
            f"- 五個開發情境與訓練教材重疊檢查：{'通過' if report['development_separation']['passed'] else '未通過'}。",
            "- v8 的前一代 v5 教材已無完整可重建紀錄，因此不能宣稱整條模型血統都具完整資料來源。",
            "- 這些教材沒有完整的公開人物來源、日期、時間戳與 split；它們只能算通用右腦教材，不能作為一ノ瀬うるは人格相似度證據。",
            "",
            "## 本輪授權",
            "",
            f"- 決策：`{decision['outcome']}`",
            "- 可以：建立並稽核不含目標人物原句、考題及固定答案的通用角色專門化教材。",
            "- 不可以：直接訓練、切換正式模型、宣稱人格更像或上線正式聊天。",
            "- 下一輪必須使用全新且來源分離的例子，之後再以 matched control 驗證教材是否真的改善生成。",
        ]
    )
    return "\n".join(lines) + "\n"


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--output-json", default=DEFAULT_RESULT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_RESULT_MD)
    args = parser.parse_args()
    report = build_report(Path(args.preregistration))
    atomic_write(args.output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    atomic_write(args.output_md, markdown_report(report))
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
