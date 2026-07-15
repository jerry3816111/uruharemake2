#!/usr/bin/env python3
"""Analyze the preregistered zero-model V58/V59 matched replay."""

import json
from pathlib import Path

from analyze_relation_safety_state_v58_holdout import (
    summarize_compiler,
    summarize_state,
)
from run_event_role_governor_v59_development import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_preregistration.json"
LOCK_PATH = ROOT / "configs" / "event_role_governor_v59_replay_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "event_role_governor_v59_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "event_role_governor_v59_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "event_role_governor_v59_development_analysis.md"


def _target_rows(raw):
    return {
        (row["case_id"], row["target_id"]): row for row in raw["target_rows"]
    }


def analyze(raw, dataset, config, lock):
    frozen = config["frozen_inputs"]
    if len(raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V59 target replay incomplete")
    if len(raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V59 case replay incomplete")
    if raw["model_calls"] != 0 or raw["paid_api_used"]:
        raise ValueError("V59 replay violated zero-model policy")
    if raw["physical_vrm_actions_executed"] != 0:
        raise ValueError("V59 replay executed a physical VRM action")
    if tuple(raw["conditions"]) != tuple(config["conditions"]):
        raise ValueError("V59 replay condition order drift")
    if tuple(lock["conditions"]) != (CONTROL, CANDIDATE):
        raise ValueError("V59 replay lock condition order drift")

    control_state = summarize_state(raw, dataset, "control")
    candidate_state = summarize_state(raw, dataset, "candidate")
    control_compiler = summarize_compiler(raw, dataset, "control")
    candidate_compiler = summarize_compiler(raw, dataset, "candidate")
    control_targets = {tuple(row) for row in control_state["correct_target_keys"]}
    candidate_targets = {
        tuple(row) for row in candidate_state["correct_target_keys"]
    }
    control_cases = set(control_compiler["correct_case_ids"])
    candidate_cases = set(candidate_compiler["correct_case_ids"])
    cases = {case["id"]: case for case in dataset["cases"]}
    rows = _target_rows(raw)

    target_fix_results = []
    for expected in config["prespecified_target_fixes"]:
        row = rows[(expected["case_id"], expected["target_id"])]
        graph = row["candidate_state"].get("v59_event_role_graph") or {}
        slot_checks = {
            key: graph.get(key) == value
            for key, value in expected.items()
            if key in {"event_owner", "directive_governor", "event_time"}
        }
        passed = (
            row["control_commitment"] == expected["from"]
            and row["candidate_commitment"] == expected["to"]
            and expected["relation_type"] in set(graph.get("relation_types") or [])
            and all(slot_checks.values())
        )
        target_fix_results.append(
            {**expected, "slot_checks": slot_checks, "passed": passed}
        )

    case_fix_results = [
        {
            "case_id": case_id,
            "control_correct": case_id in control_cases,
            "candidate_correct": case_id in candidate_cases,
            "passed": case_id not in control_cases and case_id in candidate_cases,
        }
        for case_id in config["prespecified_case_fixes"]
    ]
    contrast_control_correct = {
        case_id
        for case_id in control_cases
        if cases[case_id]["family"] == "controlled_relation_contrast"
    }
    contrast_regressions = sorted(contrast_control_correct - candidate_cases)
    comparison = {
        "state_correct_count_delta": candidate_state["correct_count"]
        - control_state["correct_count"],
        "state_fix_count": len(candidate_targets - control_targets),
        "state_fix_target_keys": sorted(
            [list(key) for key in candidate_targets - control_targets]
        ),
        "state_regression_count": len(control_targets - candidate_targets),
        "state_regression_target_keys": sorted(
            [list(key) for key in control_targets - candidate_targets]
        ),
        "ordered_exact_count_delta": candidate_compiler["ordered_exact_count"]
        - control_compiler["ordered_exact_count"],
        "call_fix_count": len(candidate_cases - control_cases),
        "call_fix_case_ids": sorted(candidate_cases - control_cases),
        "call_regression_count": len(control_cases - candidate_cases),
        "call_regression_case_ids": sorted(control_cases - candidate_cases),
        "contrast_regression_count": len(contrast_regressions),
        "contrast_regression_case_ids": contrast_regressions,
    }

    gates = config["development_gates"]
    checks = {
        "state_correct_count": candidate_state["correct_count"]
        >= gates["state_correct_count_at_least"],
        "ordered_exact_count": candidate_compiler["ordered_exact_count"]
        >= gates["ordered_exact_count_at_least"],
        "false_action_case_count": candidate_compiler["false_action_case_count"]
        == gates["false_action_case_count"],
        "no_action_specificity": candidate_compiler["no_action_specificity"]
        == gates["no_action_specificity"],
        "requested_precision": candidate_state["requested_precision"]
        == gates["requested_precision"],
        "requested_recall": candidate_state["requested_recall"]
        >= gates["requested_recall_at_least"],
        "required_call_recall": candidate_compiler["required_call_recall"]
        >= gates["required_call_recall_at_least"],
        "all_target_fixes": all(row["passed"] for row in target_fix_results),
        "all_case_fixes": all(row["passed"] for row in case_fix_results),
        "state_regressions": comparison["state_regression_count"]
        == gates["state_regression_count"],
        "call_regressions": comparison["call_regression_count"]
        == gates["call_regression_count"],
        "contrast_regressions": comparison["contrast_regression_count"]
        == gates["contrast_regression_count"],
        "ungrounded_execution": candidate_compiler["ungrounded_execution_count"]
        == gates["ungrounded_execution_count"],
        "compiler_commitment_mutation": candidate_compiler[
            "commitment_mutation_count"
        ]
        == gates["commitment_mutation_by_compiler_count"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_event_role_governor_development_analysis_v59",
        "evidence_status": raw["evidence_status"],
        "control_state": control_state,
        "candidate_state": candidate_state,
        "control_compiler": control_compiler,
        "candidate_compiler": candidate_compiler,
        "comparison": comparison,
        "target_fix_results": target_fix_results,
        "case_fix_results": case_fix_results,
        "gates": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": (
            "authorize_independent_v59_event_role_holdout"
            if passed
            else "reject_v59_development_and_diagnose_event_role_failure"
        ),
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "complete_rightbrain_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{value:.2%}"


def render_markdown(report):
    control_state = report["control_state"]
    candidate_state = report["candidate_state"]
    control = report["control_compiler"]
    candidate = report["candidate_compiler"]
    comparison = report["comparison"]
    return "\n".join(
        [
            "# V59 event-role governor development replay",
            "",
            "This matched replay reused frozen V58 model outputs and made zero model calls.",
            "",
            "| Metric | V58 + V57 control | V59 + V57 candidate |",
            "|---|---:|---:|",
            f"| State commitments | {control_state['correct_count']}/87 ({_pct(control_state['commitment_accuracy'])}) | {candidate_state['correct_count']}/87 ({_pct(candidate_state['commitment_accuracy'])}) |",
            f"| Ordered exact cases | {control['ordered_exact_count']}/64 ({_pct(control['ordered_exact_accuracy'])}) | {candidate['ordered_exact_count']}/64 ({_pct(candidate['ordered_exact_accuracy'])}) |",
            f"| False-action cases | {control['false_action_case_count']} | {candidate['false_action_case_count']} |",
            f"| No-action specificity | {_pct(control['no_action_specificity'])} | {_pct(candidate['no_action_specificity'])} |",
            f"| Required-call recall | {_pct(control['required_call_recall'])} | {_pct(candidate['required_call_recall'])} |",
            "",
            f"- Target fixes / regressions: {comparison['state_fix_count']} / {comparison['state_regression_count']}",
            f"- Case fixes / regressions: {comparison['call_fix_count']} / {comparison['call_regression_count']}",
            f"- Gate: {'PASS' if report['gates']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            "",
            "This is consumed-data development evidence only. It cannot authorize runtime or broad cognition claims.",
            "",
        ]
    )


def main():
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(
        load(DEFAULT_RAW),
        load(DATASET_PATH),
        load(CONFIG_PATH),
        load(LOCK_PATH),
    )
    DEFAULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DEFAULT_MARKDOWN.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "gate_passed": report["gates"]["passed"],
                "state_correct": report["candidate_state"]["correct_count"],
                "ordered_exact": report["candidate_compiler"][
                    "ordered_exact_count"
                ],
                "false_actions": report["candidate_compiler"][
                    "false_action_case_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
