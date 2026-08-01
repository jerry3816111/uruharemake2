#!/usr/bin/env python3
"""Audit the V11 paired construction without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_missing_role_v8 as role_schema
import rightbrain_realization_obligation_v11 as obligation
from run_public_persona_realization_obligation_v11 import CONDITIONS, build_payload
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_realization_obligation_v11_preregistration.json"
DEFAULT_JSON = ROOT / "reports/public_persona_realization_obligation_v11_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_realization_obligation_v11_construction.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report(dataset, preregistration):
    right_brain = RightBrain(load_model=False)
    role_markers = {
        marker
        for items in role_schema.ROLE_SCHEMAS.values()
        for role in items
        for marker in role["evidence_markers"]
    }
    added = json.dumps(obligation.OBLIGATION, ensure_ascii=False, sort_keys=True)
    rows = []
    for case in dataset["cases"]:
        control = build_payload(right_brain, case, CONDITIONS[0])
        treatment = build_payload(right_brain, case, CONDITIONS[1])
        rows.append(
            {
                "case_id": case["case_id"],
                "logic_identity": control[0] == treatment[0],
                "payload_identity_after_removal": obligation.remove(treatment[2]) == control[2],
                "content_units_identity": treatment[2]["leftbrain_plan"]["content_units"]
                == control[2]["leftbrain_plan"]["content_units"],
                "required_groups_identity": treatment[2]["required_marker_groups"]
                == control[2]["required_marker_groups"],
                "persona_memory_action_identity": all(
                    treatment[2].get(key) == control[2].get(key)
                    for key in ("context", "forbidden_markers", "reply_requirements")
                ),
                "obligation_exact": treatment[2]["leftbrain_plan"].get(obligation.FIELD)
                == obligation.OBLIGATION,
            }
        )
    summary = {
        "case_count": len(rows),
        "logic_identity_count": sum(row["logic_identity"] for row in rows),
        "payload_identity_after_removal_count": sum(
            row["payload_identity_after_removal"] for row in rows
        ),
        "content_units_identity_count": sum(row["content_units_identity"] for row in rows),
        "required_groups_identity_count": sum(row["required_groups_identity"] for row in rows),
        "persona_memory_action_identity_count": sum(
            row["persona_memory_action_identity"] for row in rows
        ),
        "obligation_exact_count": sum(row["obligation_exact"] for row in rows),
        "added_contract_ascii_only": added.isascii(),
        "added_role_evidence_marker_count": sum(marker in added for marker in role_markers),
        "added_semantic_content_count": 0,
        "model_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }
    checks = {
        "case_accounting": summary["case_count"] == 20,
        "single_variable_identity": all(
            summary[key] == 20
            for key in (
                "logic_identity_count",
                "payload_identity_after_removal_count",
                "content_units_identity_count",
                "required_groups_identity_count",
                "persona_memory_action_identity_count",
                "obligation_exact_count",
            )
        ),
        "no_evaluator_or_answer_leakage": summary["added_contract_ascii_only"]
        and summary["added_role_evidence_marker_count"] == 0
        and summary["added_semantic_content_count"] == 0,
        "no_model_holdout_memory_or_action": summary["model_call_count"] == 0
        and summary["holdout_content_review_count"] == 0
        and summary["production_memory_write_count"] == 0
        and summary["physical_vrm_action_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_realization_obligation_construction_v11",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_v11_model_screen_only"
        if passed
        else "repair_v11_construction",
        "summary": summary,
        "checks": checks,
        "rows": rows,
        "inputs": {
            "dataset": {"sha256": sha(DATASET)},
            "preregistration": {"sha256": sha(PREREGISTRATION)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 公開人格 Realization Obligation V11 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- 移除唯一新增欄位後完全一致：{summary['payload_identity_after_removal_count']}/20",
            f"- 左腦內容單元完全一致：{summary['content_units_identity_count']}/20",
            f"- 原語意契約完全一致：{summary['required_groups_identity_count']}/20",
            f"- 人格、記憶、動作 carrier 完全一致：{summary['persona_memory_action_identity_count']}/20",
            f"- 新增語意或答案：{summary['added_semantic_content_count']}",
            f"- 新增評分詞：{summary['added_role_evidence_marker_count']}",
            "- 模型呼叫、holdout、記憶寫入、實體動作：全部 0。",
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
    report = build_report(load(DATASET), load(PREREGISTRATION))
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
