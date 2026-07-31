#!/usr/bin/env python3
"""Audit V5 carrier construction without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_contract_v3 as v3
from run_public_persona_operational_carrier_v5 import CONDITIONS, build_payload, without_persona
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_operational_carrier_v5_preregistration.json"
V4_RESULT_LOCK = ROOT / "configs/public_persona_scorer_contract_v4_result_lock.json"
V3_RESULT_LOCK = ROOT / "configs/public_persona_contract_v3_model_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_operational_carrier_v5_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_operational_carrier_v5_construction.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_report(dataset, preregistration, v4_lock, v3_lock):
    right_brain = RightBrain(load_model=False)
    rows = []
    for case in dataset["cases"]:
        packets = {condition: build_payload(right_brain, case, condition) for condition in CONDITIONS}
        payloads = {condition: packets[condition][2] for condition in CONDITIONS}
        nonpersona_identity = len({canonical(without_persona(payload)) for payload in payloads.values()}) == 1
        active = case["context"] in v3.POLICIES
        full_identity = len({packets[condition][1] for condition in CONDITIONS}) == 1
        treatment_brief = payloads[CONDITIONS[2]]["context"]["persona_expression_brief"]
        rows.append(
            {
                "case_id": case["case_id"],
                "context": case["context"],
                "active": active,
                "nonpersona_identity": nonpersona_identity,
                "inactive_full_identity": (not active and full_identity) or active,
                "operational_carrier_active": "expression_policy" in treatment_brief,
                "scorer_contract_exposed": "required_groups" in canonical(treatment_brief)
                or "ordered_pairs" in canonical(treatment_brief),
            }
        )
    summary = {
        "case_count": len(rows),
        "active_case_count": sum(row["active"] for row in rows),
        "inactive_case_count": sum(not row["active"] for row in rows),
        "nonpersona_identity_count": sum(row["nonpersona_identity"] for row in rows),
        "inactive_full_identity_count": sum(
            row["inactive_full_identity"] for row in rows if not row["active"]
        ),
        "active_operational_carrier_count": sum(
            row["operational_carrier_active"] for row in rows if row["active"]
        ),
        "scorer_contract_exposed_count": sum(row["scorer_contract_exposed"] for row in rows),
        "model_call_count": 0,
        "holdout_content_review_count": 0,
        "training_authorized_count": 0,
    }
    checks = {
        "v4_dependency": v4_lock["passed"] is True
        and v4_lock["decision"] == preregistration["depends_on"]["required_scorer_decision"],
        "v3_dependency": v3_lock["passed"] is False
        and v3_lock["decision"] == preregistration["depends_on"]["required_carrier_decision"],
        "case_accounting": summary["case_count"] == 20
        and summary["active_case_count"] == 15
        and summary["inactive_case_count"] == 5,
        "nonpersona_identity": summary["nonpersona_identity_count"] == 20,
        "inactive_identity": summary["inactive_full_identity_count"] == 5,
        "active_carrier": summary["active_operational_carrier_count"] == 15,
        "scorer_not_exposed": summary["scorer_contract_exposed_count"] == 0,
        "no_model_holdout_or_training": summary["model_call_count"] == 0
        and summary["holdout_content_review_count"] == 0
        and summary["training_authorized_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_operational_carrier_construction_v5",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_v5_model_screen_only" if passed else "repair_v5_construction",
        "summary": summary,
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "merged_main_model_screen": passed,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "dataset": {"sha256": sha(DATASET)},
            "preregistration": {"sha256": sha(PREREGISTRATION)},
            "v4_result_lock": {"sha256": sha(V4_RESULT_LOCK)},
            "v3_result_lock": {"sha256": sha(V3_RESULT_LOCK)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# Operational Carrier V5 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- 非人格 payload 相同：{summary['nonpersona_identity_count']}/20",
            f"- 非適用情境完整相同：{summary['inactive_full_identity_count']}/5",
            f"- 適用情境自然日文 carrier：{summary['active_operational_carrier_count']}/15",
            f"- scorer contract 暴露：{summary['scorer_contract_exposed_count']}",
            "- 模型呼叫、holdout 檢視、訓練授權：全部 0。",
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
    report = build_report(load(DATASET), load(PREREGISTRATION), load(V4_RESULT_LOCK), load(V3_RESULT_LOCK))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
