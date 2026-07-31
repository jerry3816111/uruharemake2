#!/usr/bin/env python3
"""Audit the V8 missing-role construction without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_contract_v3 as v3
from run_public_persona_missing_role_v8 import (
    CONDITIONS,
    build_payload,
    without_missing_roles,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_missing_role_v8_preregistration.json"
V7_RESULT_LOCK = ROOT / "configs/public_persona_incremental_planner_v7_model_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_missing_role_v8_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_missing_role_v8_construction.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report(dataset, preregistration, v7_lock):
    right_brain = RightBrain(load_model=False)
    rows = []
    for case in dataset["cases"]:
        control_logic, control_contract, control_text, control_payload = build_payload(
            right_brain, case, CONDITIONS[0]
        )
        treatment_logic, treatment_contract, treatment_text, treatment_payload = build_payload(
            right_brain, case, CONDITIONS[1]
        )
        missing_roles = list(treatment_contract["missing_roles"])
        projection_active = bool(missing_roles)
        serialized_treatment = json.dumps(treatment_payload, ensure_ascii=False, sort_keys=True)
        original_plan_fields = (
            "scene",
            "intent",
            "surface_act",
            "dialogue_act",
            "meaning",
            "content_units",
            "style_operators",
            "grounding_terms",
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "context": case["context"],
                "active": case["context"] in v3.POLICIES,
                "projection_active": projection_active,
                "missing_roles": missing_roles,
                "logic_identity": control_logic == treatment_logic,
                "contract_identity": control_contract == treatment_contract,
                "baseline_payload_identity": without_missing_roles(treatment_payload)
                == control_payload,
                "original_plan_identity": all(
                    treatment_payload["leftbrain_plan"].get(field)
                    == control_payload["leftbrain_plan"].get(field)
                    for field in original_plan_fields
                ),
                "carrier_identity": all(
                    treatment_payload.get(field) == control_payload.get(field)
                    for field in (
                        "context",
                        "required_marker_groups",
                        "audited_memory_policy",
                        "authorized_action",
                        "tool_calls",
                    )
                ),
                "complete_full_identity": projection_active or control_text == treatment_text,
                "projected_field_exact": (not projection_active)
                or treatment_payload["leftbrain_plan"].get("missing_dialogue_roles")
                == missing_roles,
                "scorer_or_role_evidence_exposed": any(
                    token in serialized_treatment
                    for token in (
                        '"required_groups"',
                        '"ordered_pairs"',
                        '"unsupported_concrete_markers"',
                        '"expected_pass"',
                        '"evidence_markers"',
                    )
                ),
            }
        )
    projected = [row for row in rows if row["projection_active"]]
    summary = {
        "case_count": len(rows),
        "active_case_count": sum(row["active"] for row in rows),
        "inactive_case_count": sum(not row["active"] for row in rows),
        "projected_case_count": len(projected),
        "projected_role_count": sum(len(row["missing_roles"]) for row in projected),
        "projected_roles": sorted(
            role for row in projected for role in row["missing_roles"]
        ),
        "logic_identity_count": sum(row["logic_identity"] for row in rows),
        "contract_identity_count": sum(row["contract_identity"] for row in rows),
        "baseline_payload_identity_count": sum(row["baseline_payload_identity"] for row in rows),
        "original_plan_identity_count": sum(row["original_plan_identity"] for row in rows),
        "carrier_identity_count": sum(row["carrier_identity"] for row in rows),
        "complete_full_identity_count": sum(
            row["complete_full_identity"] for row in rows if not row["projection_active"]
        ),
        "projected_field_exact_count": sum(
            row["projected_field_exact"] for row in projected
        ),
        "scorer_or_role_evidence_exposed_count": sum(
            row["scorer_or_role_evidence_exposed"] for row in rows
        ),
        "model_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "training_authorized_count": 0,
    }
    checks = {
        "v7_dependency": v7_lock["authorizations"]["missing_role_token_projection_research"]
        is True,
        "case_accounting": summary["case_count"] == 20
        and summary["active_case_count"] == 15
        and summary["inactive_case_count"] == 5,
        "single_missing_role": summary["projected_case_count"] == 1
        and summary["projected_role_count"] == 1
        and summary["projected_roles"] == ["entry_point"],
        "logic_identity": summary["logic_identity_count"] == 20,
        "contract_identity": summary["contract_identity_count"] == 20,
        "baseline_payload_identity": summary["baseline_payload_identity_count"] == 20,
        "original_plan_identity": summary["original_plan_identity_count"] == 20,
        "carrier_identity": summary["carrier_identity_count"] == 20,
        "complete_case_identity": summary["complete_full_identity_count"] == 19,
        "projected_field_exact": summary["projected_field_exact_count"] == 1,
        "scorers_and_role_evidence_not_exposed": summary[
            "scorer_or_role_evidence_exposed_count"
        ]
        == 0,
        "no_model_holdout_memory_action_or_training": summary["model_call_count"] == 0
        and summary["holdout_content_review_count"] == 0
        and summary["production_memory_write_count"] == 0
        and summary["physical_vrm_action_count"] == 0
        and summary["training_authorized_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_missing_role_construction_v8",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_v8_model_screen_only"
        if passed
        else "repair_v8_construction",
        "summary": summary,
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "merged_main_model_screen": passed,
            "source_disjoint_missing_role_holdout": False,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "dataset": {"sha256": sha(DATASET)},
            "preregistration": {"sha256": sha(PREREGISTRATION)},
            "v7_result_lock": {"sha256": sha(V7_RESULT_LOCK)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# Missing Role V8 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- role schema 判定需補欄位：{summary['projected_case_count']}/20 題、{summary['projected_roles']}",
            f"- 移除 V8 欄位後 payload 完全一致：{summary['baseline_payload_identity_count']}/20",
            f"- 原有思考計畫與語意完全一致：{summary['original_plan_identity_count']}/20",
            f"- 人格、記憶、動作 carrier 完全一致：{summary['carrier_identity_count']}/20",
            f"- 無缺失角色題完整 payload 一致：{summary['complete_full_identity_count']}/19",
            f"- 評分器或 role evidence 暴露：{summary['scorer_or_role_evidence_exposed_count']}",
            "- 模型呼叫、holdout、記憶寫入、實體動作、訓練授權：全部 0。",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    for path in (args.output_json, args.output_md):
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {path}")
    report = build_report(load(DATASET), load(PREREGISTRATION), load(V7_RESULT_LOCK))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
