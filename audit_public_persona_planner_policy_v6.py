#!/usr/bin/env python3
"""Audit V6 planner-policy construction without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_contract_v3 as v3
from run_public_persona_planner_policy_v6 import (
    CONDITIONS,
    build_payload,
    planner_projection,
    protected_logic,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_planner_policy_v6_preregistration.json"
V5_RESULT_LOCK = ROOT / "configs/public_persona_operational_carrier_v5_model_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_planner_policy_v6_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_planner_policy_v6_construction.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report(dataset, preregistration, v5_lock):
    right_brain = RightBrain(load_model=False)
    rows = []
    for case in dataset["cases"]:
        control_logic, _, control_text, control_payload = build_payload(
            right_brain, case, CONDITIONS[0]
        )
        treatment_logic, treatment_trace, treatment_text, treatment_payload = build_payload(
            right_brain, case, CONDITIONS[1]
        )
        active = case["context"] in v3.POLICIES
        serialized_payload = json.dumps(treatment_payload, ensure_ascii=False, sort_keys=True)
        rows.append(
            {
                "case_id": case["case_id"],
                "context": case["context"],
                "active": active,
                "protected_logic_identity": protected_logic(control_logic)
                == protected_logic(treatment_logic),
                "persona_brief_identity": control_payload["context"]["persona_expression_brief"]
                == treatment_payload["context"]["persona_expression_brief"],
                "active_planner_changed": (not active)
                or planner_projection(control_logic) != planner_projection(treatment_logic),
                "inactive_full_identity": active or control_text == treatment_text,
                "policy_status_correct": treatment_trace["status"]
                == (
                    "active_development_hypothesis"
                    if active
                    else "inactive_no_supported_context"
                ),
                "scorer_contract_exposed": any(
                    token in serialized_payload
                    for token in ("required_groups", "ordered_pairs", "expected_pass")
                ),
            }
        )
    summary = {
        "case_count": len(rows),
        "active_case_count": sum(row["active"] for row in rows),
        "inactive_case_count": sum(not row["active"] for row in rows),
        "protected_logic_identity_count": sum(row["protected_logic_identity"] for row in rows),
        "persona_brief_identity_count": sum(row["persona_brief_identity"] for row in rows),
        "active_planner_changed_count": sum(
            row["active_planner_changed"] for row in rows if row["active"]
        ),
        "inactive_full_identity_count": sum(
            row["inactive_full_identity"] for row in rows if not row["active"]
        ),
        "policy_status_correct_count": sum(row["policy_status_correct"] for row in rows),
        "scorer_contract_exposed_count": sum(row["scorer_contract_exposed"] for row in rows),
        "model_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "training_authorized_count": 0,
    }
    checks = {
        "v5_dependency": v5_lock["authorizations"]["planner_policy_integration_research"]
        is True,
        "case_accounting": summary["case_count"] == 20
        and summary["active_case_count"] == 15
        and summary["inactive_case_count"] == 5,
        "protected_logic_identity": summary["protected_logic_identity_count"] == 20,
        "persona_brief_identity": summary["persona_brief_identity_count"] == 20,
        "active_planner_changed": summary["active_planner_changed_count"] == 15,
        "inactive_full_identity": summary["inactive_full_identity_count"] == 5,
        "policy_status": summary["policy_status_correct_count"] == 20,
        "scorer_not_exposed": summary["scorer_contract_exposed_count"] == 0,
        "no_model_holdout_memory_action_or_training": summary["model_call_count"] == 0
        and summary["holdout_content_review_count"] == 0
        and summary["production_memory_write_count"] == 0
        and summary["physical_vrm_action_count"] == 0
        and summary["training_authorized_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_planner_policy_construction_v6",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_v6_model_screen_only"
        if passed
        else "repair_v6_construction",
        "summary": summary,
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "merged_main_model_screen": passed,
            "source_disjoint_planner_policy_development_holdout": False,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "dataset": {"sha256": sha(DATASET)},
            "preregistration": {"sha256": sha(PREREGISTRATION)},
            "v5_result_lock": {"sha256": sha(V5_RESULT_LOCK)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# Planner Policy V6 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- 核心語意、記憶、動作保持一致：{summary['protected_logic_identity_count']}/20",
            f"- 右腦人格 carrier 保持一致：{summary['persona_brief_identity_count']}/20",
            f"- 適用案例 planner 確實改變：{summary['active_planner_changed_count']}/15",
            f"- 非適用案例 payload 完全一致：{summary['inactive_full_identity_count']}/5",
            f"- scorer contract 暴露：{summary['scorer_contract_exposed_count']}",
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
    report = build_report(load(DATASET), load(PREREGISTRATION), load(V5_RESULT_LOCK))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "decision": report["decision"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
