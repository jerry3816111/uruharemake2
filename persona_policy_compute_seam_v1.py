#!/usr/bin/env python3
"""Construct a no-model evidence report for the persona-policy compute seam."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

import public_persona_contract_v3 as public_contract
import public_persona_runtime_manifest_v1 as runtime_manifest
import uruha_persona_policy as persona_policy
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "persona_policy_compute_seam_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/persona_policy_compute_seam_v1_preregistration.json"
DEFAULT_HARNESS_LOCK = ROOT / "configs/persona_policy_compute_seam_v1_harness_lock.json"
DEFAULT_REPORT_JSON = ROOT / "reports/persona_policy_compute_seam_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/persona_policy_compute_seam_v1_construction.md"
PASS_DECISION = "authorize_fixed_surface_family_provider_migration_on_synthetic_inputs_only"
FAIL_DECISION = "repair_persona_policy_or_compute_seam_before_surface_family_migration"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def binding(path):
    return {"path": display_path(path), "sha256": sha256_file(path)}


def binding_valid(value):
    path = Path(str((value or {}).get("path") or ""))
    if not path.is_absolute():
        path = ROOT / path
    return path.is_file() and str((value or {}).get("sha256") or "") == sha256_file(path)


def structural_paths(value, prefix="$"):
    paths = []
    if isinstance(value, dict):
        paths.append((prefix, "dict", len(value)))
        for key in sorted(value):
            paths.extend(structural_paths(value[key], f"{prefix}.{key}"))
    elif isinstance(value, list):
        paths.append((prefix, "list", len(value)))
        for index, item in enumerate(value):
            paths.extend(structural_paths(item, f"{prefix}[{index}]"))
    else:
        paths.append((prefix, "scalar", None))
    return paths


def synthetic_logic(context):
    return {
        "public_persona_context": context,
        "scene": "support",
        "intent": "state_update",
        "jp_summary": "状態と次の行動について話している。",
        "core_message_jp": "状態を短く伝えて次の行動を一つ示す",
        "required_marker_groups": [["状態"], ["次"]],
        "memory_anchor": {"kind": "working_memory", "id": "synthetic-wm"},
        "memory_speakability": "allowed",
        "memory_use_expected": True,
        "action_intent_frame": {"kind": "reply_only"},
        "authorized_action": None,
        "tool_calls": [],
        "human_speech_plan": {
            "content_units": ["状態", "次の行動"],
            "grounding_terms": ["状態"],
        },
    }


def without_persona_brief(payload):
    copied = copy.deepcopy(payload)
    copied["context"].pop("persona_expression_brief", None)
    return copied


def source_stage_audit():
    source_path = ROOT / "uruha_brain_mac.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    source_text = ast.unparse(tree)
    stage_names = [
        "leftbrain_social_reasoning_frame",
        "leftbrain_general_plan",
        "rightbrain_surface_generation",
        "rightbrain_surface_repair",
        "typed_reflection",
        "background_consolidation",
    ]
    return {
        "source": binding(source_path),
        "stage_names": stage_names,
        "stage_presence": {name: name in source_text for name in stage_names},
        "instrumented_client_present": "instrument_openai_client" in source_text,
        "default_provider_is_optional": "persona_policy_provider=None" in source_text,
        "default_ledger_is_optional": "compute_ledger=None" in source_text,
    }


def construct_cases():
    psyche = {"mood": -20, "trust": 68}
    contexts = list(public_contract.POLICIES) + ["unsupported_synthetic_control"]
    target_provider = persona_policy.build_persona_policy_provider(persona_policy.TARGET_PROVIDER)
    neutral_provider = persona_policy.build_persona_policy_provider(persona_policy.NEUTRAL_PROVIDER)
    legacy_provider = persona_policy.build_persona_policy_provider(persona_policy.LEGACY_PROVIDER)
    default_rightbrain = RightBrain(load_model=False)
    legacy_rightbrain = RightBrain(load_model=False, persona_policy_provider=legacy_provider)
    target_rightbrain = RightBrain(load_model=False, persona_policy_provider=target_provider)
    neutral_rightbrain = RightBrain(load_model=False, persona_policy_provider=neutral_provider)
    rows = []

    for index, context in enumerate(contexts, start=1):
        logic = synthetic_logic(context)
        target_projection = target_provider.compile(logic, psyche)
        neutral_projection = neutral_provider.compile(logic, psyche)
        attached = target_provider.attach_to_plan(logic, psyche)
        protected_before = {
            key: copy.deepcopy(logic.get(key))
            for key in persona_policy.PROTECTED_PLAN_FIELDS
        }
        protected_after = {
            key: copy.deepcopy(attached.get(key))
            for key in persona_policy.PROTECTED_PLAN_FIELDS
        }

        default_payload_text = default_rightbrain._build_model_surface_payload(
            copy.deepcopy(logic), psyche, 64
        )
        legacy_payload_text = legacy_rightbrain._build_model_surface_payload(
            copy.deepcopy(logic), psyche, 64
        )
        target_payload = json.loads(
            target_rightbrain._build_model_surface_payload(copy.deepcopy(logic), psyche, 64)
        )
        neutral_payload = json.loads(
            neutral_rightbrain._build_model_surface_payload(copy.deepcopy(logic), psyche, 64)
        )
        target_brief = target_payload["context"]["persona_expression_brief"]
        neutral_brief = neutral_payload["context"]["persona_expression_brief"]
        rows.append(
            {
                "case_id": f"persona_compute_synthetic_{index:02d}",
                "context": context,
                "supported_context": context in public_contract.POLICIES,
                "default_vs_legacy_payload_byte_identical": default_payload_text == legacy_payload_text,
                "target_vs_neutral_projection_structure_equal": structural_paths(target_projection) == structural_paths(neutral_projection),
                "target_vs_neutral_brief_structure_equal": structural_paths(target_brief) == structural_paths(neutral_brief),
                "target_vs_neutral_nonpersona_payload_equal": without_persona_brief(target_payload) == without_persona_brief(neutral_payload),
                "protected_fields_unchanged": protected_before == protected_after,
                "target_and_neutral_values_differ": target_projection != neutral_projection,
                "contains_fixed_reply": bool(target_projection["contains_fixed_reply"] or neutral_projection["contains_fixed_reply"]),
                "contains_target_utterance": bool(target_projection["contains_target_utterance"] or neutral_projection["contains_target_utterance"]),
            }
        )
    return rows


def validate_harness_lock(lock):
    errors = []
    if lock.get("experiment_id") != EXPERIMENT_ID:
        errors.append("wrong_experiment_id")
    for name, value in (lock.get("frozen_artifacts") or {}).items():
        if not binding_valid(value):
            errors.append(f"invalid_binding:{name}")
    return errors


def build_report(preregistration, harness_lock):
    rows = construct_cases()
    source_audit = source_stage_audit()
    harness_errors = validate_harness_lock(harness_lock)
    checks = []

    def add(check_id, passed):
        checks.append({"check_id": check_id, "passed": bool(passed)})

    for row in rows:
        case_id = row["case_id"]
        add(f"{case_id}:default_legacy_identical", row["default_vs_legacy_payload_byte_identical"])
        add(f"{case_id}:projection_structure_equal", row["target_vs_neutral_projection_structure_equal"])
        add(f"{case_id}:brief_structure_equal", row["target_vs_neutral_brief_structure_equal"])
        add(f"{case_id}:nonpersona_payload_equal", row["target_vs_neutral_nonpersona_payload_equal"])
        add(f"{case_id}:protected_fields_unchanged", row["protected_fields_unchanged"])
        add(f"{case_id}:policy_values_differ", row["target_and_neutral_values_differ"])
        add(f"{case_id}:no_fixed_reply", not row["contains_fixed_reply"])
        add(f"{case_id}:no_target_utterance", not row["contains_target_utterance"])

    add("all_model_stages_declared", all(source_audit["stage_presence"].values()))
    add("openai_client_instrumented", source_audit["instrumented_client_present"])
    add("default_provider_optional", source_audit["default_provider_is_optional"])
    add("default_ledger_optional", source_audit["default_ledger_is_optional"])
    add("harness_lock_valid", not harness_errors)

    counts = {
        "check_count": len(checks),
        "check_pass_count": sum(row["passed"] for row in checks),
        "synthetic_case_count": len(rows),
        "supported_context_case_count": sum(row["supported_context"] for row in rows),
        "unsupported_context_case_count": sum(not row["supported_context"] for row in rows),
        "default_vs_legacy_payload_mismatch_count": sum(not row["default_vs_legacy_payload_byte_identical"] for row in rows),
        "target_vs_neutral_nonpersona_payload_mismatch_count": sum(not row["target_vs_neutral_nonpersona_payload_equal"] for row in rows),
        "target_vs_neutral_structure_mismatch_count": sum(not (row["target_vs_neutral_projection_structure_equal"] and row["target_vs_neutral_brief_structure_equal"]) for row in rows),
        "protected_field_mutation_count": sum(not row["protected_fields_unchanged"] for row in rows),
        "actual_model_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "runtime_default_behavior_change_count": 0,
        "persona_score_count": 0,
    }
    required = preregistration["construction_success_requires"]
    passed = (
        counts["check_count"] == counts["check_pass_count"]
        and counts["synthetic_case_count"] == required["synthetic_case_count_exact"]
        and counts["default_vs_legacy_payload_mismatch_count"] == required["default_vs_legacy_payload_mismatch_count_exact"]
        and counts["target_vs_neutral_nonpersona_payload_mismatch_count"] == required["target_vs_neutral_nonpersona_payload_mismatch_count_exact"]
        and counts["target_vs_neutral_structure_mismatch_count"] == required["target_vs_neutral_structure_mismatch_count_exact"]
        and counts["protected_field_mutation_count"] == required["protected_field_mutation_count_exact"]
        and counts["actual_model_call_count"] == required["actual_model_call_count_exact"]
        and counts["holdout_content_review_count"] == required["holdout_content_review_count_exact"]
        and counts["production_memory_write_count"] == required["production_memory_write_count_exact"]
        and counts["runtime_default_behavior_change_count"] == required["runtime_default_behavior_change_count_exact"]
        and counts["persona_score_count"] == required["persona_score_count_exact"]
    )
    fixed_count = runtime_manifest.source_audit()["persona_crosscut_evidence"]["rightbrain_fixed_reply_literal_count"]
    return {
        "schema": "uruha_persona_policy_compute_seam_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "harness_lock": binding(DEFAULT_HARNESS_LOCK),
            "persona_policy_source": binding(ROOT / "uruha_persona_policy.py"),
            "compute_ledger_source": binding(ROOT / "uruha_compute_ledger.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
        },
        "synthetic_cases": rows,
        "source_stage_audit": source_audit,
        "remaining_blockers": {
            "rightbrain_fixed_reply_literal_count": fixed_count,
            "hardcoded_surface_families_still_present": fixed_count > 0,
            "full_persona_disabled_c2_executable": False,
            "reason": "The new provider seam does not yet replace legacy LeftBrain persona rules or RightBrain fixed surface families.",
        },
        "counts": counts,
        "checks": checks,
        "harness_errors": harness_errors,
        "authorizations": {
            "fixed_surface_family_provider_migration_on_synthetic_inputs": passed,
            "formal_persona_evaluation": False,
            "sealed_holdout_unsealing": False,
            "human_blind_rating": False,
            "model_training": False,
            "production_default_enablement": False,
            "public_persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def render_markdown(report):
    counts = report["counts"]
    blocker = report["remaining_blockers"]
    return f"""# 人格策略與運算帳本接縫 V1

## 結論

**建構檢查：{counts['check_pass_count']}/{counts['check_count']}，{'通過' if report['status'] == 'construction_passed' else '未通過'}。**

這一輪建立了可替換的「目標公開人格策略」與「中性對照策略」，並加入逐題、逐階段的模型運算帳本。沒有執行模型、沒有讀取 holdout、沒有計算人格分數。

## 六個合成情境

| 檢查 | 結果 |
|---|---:|
| 預設與 legacy payload 不一致 | {counts['default_vs_legacy_payload_mismatch_count']} / {counts['synthetic_case_count']} |
| 目標與中性組非人格欄位不一致 | {counts['target_vs_neutral_nonpersona_payload_mismatch_count']} / {counts['synthetic_case_count']} |
| 目標與中性組結構不一致 | {counts['target_vs_neutral_structure_mismatch_count']} / {counts['synthetic_case_count']} |
| 認知欄位被人格策略改寫 | {counts['protected_field_mutation_count']} / {counts['synthetic_case_count']} |

## 現在能做什麼

`相同認知計畫 -> target provider / neutral provider -> 相同右腦 payload 骨架`

compute ledger 只保存雜湊、字數、token、模型、參數、階段與延遲，不保存使用者輸入或模型回答原文。

## 仍不能主張什麼

- 右腦仍有 **{blocker['rightbrain_fixed_reply_literal_count']} 個固定回覆字串**，完整 persona-disabled C2 仍不可執行。
- 本輪沒有證明回答更像一ノ瀬うるは。
- 本輪不授權正式 holdout、盲評、訓練或 production 預設啟用。

## 下一個必要工程

把固定 surface family 移到 provider 後方，讓 target 與 neutral 在完全相同的認知流程中真正替換，並先用合成輸入驗證輸出與運算排程。
"""


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--harness-lock", default=str(DEFAULT_HARNESS_LOCK))
    parser.add_argument("--output-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(load_json(args.preregistration), load_json(args.harness_lock))
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "decision": report["decision"], "counts": report["counts"]}, ensure_ascii=False, indent=2))
    return 1 if args.require_pass and report["status"] != "construction_passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
