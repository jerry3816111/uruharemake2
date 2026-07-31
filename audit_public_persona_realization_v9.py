#!/usr/bin/env python3
"""Run the deterministic V9 planner-versus-realization attribution audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_realization_audit_v9 as v9


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_realization_audit_v9_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
V8_ANALYSIS = ROOT / "reports/public_persona_missing_role_v8_analysis.json"
V8_RESULT_LOCK = ROOT / "configs/public_persona_missing_role_v8_model_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_realization_audit_v9.json"
DEFAULT_MD = ROOT / "reports/public_persona_realization_audit_v9.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _control_scores(v8_analysis):
    return {
        row["case_id"]: row
        for row in v8_analysis["scores"]
        if row["condition"] == "c0_existing_speech_plan"
    }


def build_report(preregistration, dataset, v8_analysis, v8_lock):
    cases = {case["case_id"]: case for case in dataset["cases"]}
    control_scores = _control_scores(v8_analysis)
    rows = []
    failure_rows = []
    for case in dataset["cases"]:
        coverage = v9.compile_plan_coverage(case["logic"])
        v8_missing = []
        for score in v8_analysis["scores"]:
            if score["case_id"] == case["case_id"] and score["condition"] == "t1_missing_role_tokens":
                v8_missing = list(score["missing_roles"])
                break
        row = {
            "case_id": case["case_id"],
            "context": case["context"],
            "status": coverage["status"],
            "v8_required_marker_only_missing_roles": v8_missing,
            "v9_plan_covered_roles": coverage["covered_roles"],
            "v9_plan_missing_roles": coverage["missing_roles"],
            "v8_roles_reclassified_as_planned": sorted(
                set(v8_missing) & set(coverage["covered_roles"])
            ),
        }
        rows.append(row)
        score = control_scores[case["case_id"]]
        for role in v9.missing_required_roles(score["v4_persona_reasons"]):
            failure_rows.append(
                {
                    "case_id": case["case_id"],
                    "context": case["context"],
                    **v9.classify_missing_role(case["logic"], score["raw_reply"], role),
                    "frozen_reply": score["raw_reply"],
                }
            )
    active = [row for row in rows if row["status"] == "active_development_hypothesis"]
    inactive = [row for row in rows if row["status"] != "active_development_hypothesis"]
    v8_targets = [row for row in rows if row["v8_required_marker_only_missing_roles"]]
    v8_target_failures = [
        failure
        for failure in failure_rows
        if failure["case_id"] in {row["case_id"] for row in v8_targets}
        and failure["role"]
        in {
            role
            for row in v8_targets
            for role in row["v8_required_marker_only_missing_roles"]
        }
    ]
    classifications = {
        name: sum(item["classification"] == name for item in failure_rows)
        for name in ("planner_role_missing", "lexical_scorer_gap", "planned_but_unrealized")
    }
    if v8_target_failures and all(
        item["classification"] == "planned_but_unrealized" for item in v8_target_failures
    ):
        decision = preregistration["decision_policy"]["v8_target_planned_and_unrealized"]
        next_authorization = "planned_role_realization_research"
    elif v8_target_failures and all(
        item["classification"] == "planner_role_missing" for item in v8_target_failures
    ):
        decision = preregistration["decision_policy"]["v8_target_not_planned"]
        next_authorization = "planner_role_completion_research"
    else:
        decision = preregistration["decision_policy"]["v8_target_ambiguous"]
        next_authorization = "independent_human_adjudication"
    integrity = {
        "v8_dependency_authorized": v8_lock["authorizations"][
            "model_readable_missing_role_semantics_research"
        ]
        is True,
        "v8_analysis_integrity": v8_analysis["integrity"]["passed"] is True,
        "case_accounting": len(rows) == 20 and len(active) == 15 and len(inactive) == 5,
        "control_reply_accounting": len(control_scores) == 20,
        "v8_target_accounting": len(v8_targets) == preregistration["scope"][
            "expected_v8_projected_case_count"
        ],
        "classification_accounting": sum(classifications.values()) == len(failure_rows),
        "no_model_holdout_memory_or_action": True,
    }
    passed = all(integrity.values())
    return {
        "schema": "uruha_public_persona_realization_audit_result_v9",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": decision if passed else "repair_v9_audit",
        "summary": {
            "case_count": len(rows),
            "active_case_count": len(active),
            "inactive_case_count": len(inactive),
            "v8_target_case_count": len(v8_targets),
            "v8_target_roles_reclassified_as_planned_count": sum(
                len(row["v8_roles_reclassified_as_planned"]) for row in v8_targets
            ),
            "v4_missing_required_failure_count": len(failure_rows),
            **{f"{name}_count": count for name, count in classifications.items()},
            "model_call_count": 0,
            "holdout_content_review_count": 0,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
        },
        "integrity": {"passed": passed, "checks": integrity},
        "rows": rows,
        "failure_attribution": failure_rows,
        "v8_target_failure_attribution": v8_target_failures,
        "authorizations": {
            next_authorization: passed,
            "runtime_default_enable": False,
            "model_change": False,
            "scorer_rewrite": False,
            "training": False,
            "holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "preregistration": {"sha256": sha(PREREGISTRATION)},
            "dataset": {"sha256": sha(DATASET)},
            "v8_analysis": {"sha256": sha(V8_ANALYSIS)},
            "v8_result_lock": {"sha256": sha(V8_RESULT_LOCK)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格 V9：規劃與表達歸因稽核",
        "",
        f"- 決策：`{report['decision']}`",
        f"- V8 誤判為 planner 缺失、但計畫中已有的角色：{summary['v8_target_roles_reclassified_as_planned_count']}",
        f"- V4 missing-required：{summary['v4_missing_required_failure_count']}",
        f"- 詞彙評分器漏判：{summary['lexical_scorer_gap_count']}",
        f"- 已規劃但未表達：{summary['planned_but_unrealized_count']}",
        f"- 真正 planner 缺失：{summary['planner_role_missing_count']}",
        "- 模型呼叫、holdout、記憶寫入、實體動作：全部 0。",
        "",
        "| 案例 | 角色 | 分類 | 計畫證據 | 回覆概念證據 |",
        "|---|---|---|---|---|",
    ]
    for item in report["failure_attribution"]:
        lines.append(
            f"| {item['case_id']} | {item['role']} | {item['classification']} | "
            f"{', '.join(item['plan_marker_hits']) or '-'} | "
            f"{', '.join(item['reply_concept_hits']) or '-'} |"
        )
    lines.extend(["", "## 證據邊界", "", report["evidence_boundary"]])
    return "\n".join(lines)


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
    report = build_report(
        load(PREREGISTRATION), load(DATASET), load(V8_ANALYSIS), load(V8_RESULT_LOCK)
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
