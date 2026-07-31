#!/usr/bin/env python3
"""Audit the V3 persona contract carrier before any model inference."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import public_persona_contract_v3 as contract
from project_paths import (
    PUBLIC_PERSONA_CONTRACT_V3_CONSTRUCTION_JSON_PATH,
    PUBLIC_PERSONA_CONTRACT_V3_CONSTRUCTION_MD_PATH,
    PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_contract_v3_preregistration.json"
V2_DATASET = ROOT / "datasets/public_persona_observations_v2.json"
V2_RESULT_LOCK = ROOT / "configs/public_persona_observation_v2_result_lock.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected(logic):
    speech = logic.get("human_speech_plan") or {}
    return {
        "core_message_jp": logic.get("core_message_jp"),
        "required_marker_groups": logic.get("required_marker_groups"),
        "memory_anchor": logic.get("memory_anchor"),
        "memory_speakability": logic.get("memory_speakability"),
        "memory_use_expected": logic.get("memory_use_expected"),
        "action_intent_frame": logic.get("action_intent_frame"),
        "authorized_action": logic.get("authorized_action"),
        "tool_calls": logic.get("tool_calls"),
        "speech_content_units": speech.get("content_units"),
        "speech_grounding_terms": speech.get("grounding_terms"),
    }


def without_persona(payload):
    copied = copy.deepcopy(payload)
    copied["context"].pop("persona_expression_brief", None)
    return copied


def prohibited_key_count(value):
    prohibited = {"target_reply", "expected_reply", "fixed_response", "verbatim_text"}
    if isinstance(value, dict):
        return sum(
            int(key in prohibited) + prohibited_key_count(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return sum(prohibited_key_count(child) for child in value)
    return 0


def audit(dataset, preregistration, v2_dataset, v2_result):
    right_brain = RightBrain(load_model=False)
    rows = []
    fixed_key_count = 0
    training_count = 0
    active_count = 0
    inactive_count = 0
    protected_identity_count = 0
    nonpersona_identity_count = 0
    inactive_full_identity_count = 0
    planning_exposed_count = 0

    for source in dataset["cases"]:
        control_logic = copy.deepcopy(source["logic"])
        treatment_logic = copy.deepcopy(source["logic"])
        protected_before = protected(treatment_logic)
        compiled = contract.compile_persona_contract(treatment_logic)
        if compiled["status"] == "active_development_hypothesis":
            active_count += 1
        else:
            inactive_count += 1
        fixed_key_count += prohibited_key_count(source)
        training_count += int(source.get("training_authorized") is not False)

        right_brain.public_persona_conditional_brief_enabled = False
        control_payload = json.loads(
            right_brain._build_model_surface_payload(
                control_logic,
                source["psyche"],
                source["persona_evaluation"]["maximum_characters"],
            )
        )
        right_brain.public_persona_conditional_brief_enabled = True
        treatment_payload = json.loads(
            right_brain._build_model_surface_payload(
                treatment_logic,
                source["psyche"],
                source["persona_evaluation"]["maximum_characters"],
            )
        )
        right_brain.public_persona_conditional_brief_enabled = False
        protected_identity = protected(treatment_logic) == protected_before
        nonpersona_identity = without_persona(control_payload) == without_persona(
            treatment_payload
        )
        full_identity = control_payload == treatment_payload
        treatment_brief = treatment_payload["context"]["persona_expression_brief"]
        planning_exposed = "planning_policy" in treatment_brief
        protected_identity_count += int(protected_identity)
        nonpersona_identity_count += int(nonpersona_identity)
        if compiled["status"] != "active_development_hypothesis":
            inactive_full_identity_count += int(full_identity)
        planning_exposed_count += int(planning_exposed)
        rows.append(
            {
                "case_id": source["case_id"],
                "context": source["context"],
                "contract_status": compiled["status"],
                "protected_logic_identity": protected_identity,
                "nonpersona_payload_identity": nonpersona_identity,
                "full_payload_identity": full_identity,
                "planning_policy_exposed_to_rightbrain": planning_exposed,
            }
        )

    holdouts = v2_dataset["sealed_holdout_reservations"]
    holdout_content_count = sum(
        row["content_reviewed_for_behavior"] is not False for row in holdouts
    )
    holdout_label_count = sum(row["labels_available"] is not False for row in holdouts)
    gates = preregistration["construction_gates"]
    checks = {
        "v2_dependency": v2_result["decision"]
        == preregistration["depends_on"]["required_decision"],
        "case_count": len(rows) == gates["case_count_exact"],
        "active_contracts": active_count == gates["active_contract_exact_count"],
        "inactive_contracts": inactive_count == gates["inactive_contract_exact_count"],
        "protected_logic": protected_identity_count
        == gates["protected_logic_identity_count"],
        "nonpersona_payload": nonpersona_identity_count
        == gates["target_payload_nonpersona_identity_count"],
        "inactive_payload": inactive_full_identity_count
        == gates["inactive_full_payload_identity_count"],
        "planning_not_exposed": planning_exposed_count
        <= gates["planning_policy_exposed_to_rightbrain_count_max"],
        "no_fixed_reply": fixed_key_count
        <= gates["fixed_or_expected_reply_count_max"],
        "holdout_still_sealed": holdout_content_count
        <= gates["holdout_content_count_max"]
        and holdout_label_count == 0,
        "no_training": training_count <= gates["training_authorized_count_max"],
        "runtime_default_off": preregistration["decision_policy"][
            "runtime_default_enable"
        ]
        is False,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_contract_construction_audit_v3",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": (
            "authorize_merged_main_v3_development_model_screen_only"
            if passed
            else "stop_v3_persona_contract_carrier"
        ),
        "summary": {
            "case_count": len(rows),
            "active_contract_count": active_count,
            "inactive_contract_count": inactive_count,
            "protected_logic_identity_count": protected_identity_count,
            "nonpersona_payload_identity_count": nonpersona_identity_count,
            "inactive_full_payload_identity_count": inactive_full_identity_count,
            "planning_policy_exposed_to_rightbrain_count": planning_exposed_count,
            "fixed_or_expected_reply_count": fixed_key_count,
            "holdout_content_reviewed_count": holdout_content_count,
            "holdout_label_available_count": holdout_label_count,
            "training_authorized_count": training_count,
        },
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "merged_main_development_model_screen": passed,
            "context_perception_experiment": False,
            "holdout_unsealing": False,
            "runtime_default_enable": False,
            "training": False,
            "persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def build_report():
    report = audit(
        load(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH),
        load(PREREGISTRATION),
        load(V2_DATASET),
        load(V2_RESULT_LOCK),
    )
    report["inputs"] = {
        "dataset": {"path": Path(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH).name, "sha256": sha(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH)},
        "preregistration": {"path": PREREGISTRATION.name, "sha256": sha(PREREGISTRATION)},
        "v2_dataset": {"path": V2_DATASET.name, "sha256": sha(V2_DATASET)},
        "v2_result_lock": {"path": V2_RESULT_LOCK.name, "sha256": sha(V2_RESULT_LOCK)},
    }
    return report


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 公開人格條件契約 V3 建構稽核",
            "",
            f"- 結果：`{report['decision']}`",
            "- 唯一變因：右腦人格 brief 從固定三標籤改為條件式 surface policy。",
            "- planning policy 只留在 trace，沒有交給右腦。",
            "",
            "| 檢查 | 結果 |",
            "|---|---:|",
            f"| development cases | {summary['case_count']} |",
            f"| 條件契約正確啟用 | {summary['active_contract_count']}/15 |",
            f"| 非適用情境維持關閉 | {summary['inactive_contract_count']}/5 |",
            f"| 語意、記憶與動作欄位不變 | {summary['protected_logic_identity_count']}/20 |",
            f"| persona 以外 payload 不變 | {summary['nonpersona_payload_identity_count']}/20 |",
            f"| 非適用完整 payload 相同 | {summary['inactive_full_payload_identity_count']}/5 |",
            f"| planning policy 洩入右腦 | {summary['planning_policy_exposed_to_rightbrain_count']} |",
            f"| 固定回答 | {summary['fixed_or_expected_reply_count']} |",
            f"| holdout 已看內容 / 已標註 | {summary['holdout_content_reviewed_count']} / {summary['holdout_label_available_count']} |",
            f"| 訓練授權 | {summary['training_authorized_count']} |",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_CONSTRUCTION_JSON_PATH)
    parser.add_argument("--output-md", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_CONSTRUCTION_MD_PATH)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    if not args.overwrite and (args.output_json.exists() or args.output_md.exists()):
        raise FileExistsError("refusing to overwrite V3 construction report")
    report = build_report()
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    return 1 if args.require_pass and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
