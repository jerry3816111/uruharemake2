#!/usr/bin/env python3
"""Analyze the preregistered zero-model V58 safety-state replay."""

import json
from collections import Counter
from pathlib import Path

from run_relation_safety_state_v58_development import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_preregistration.json"
LOCK_PATH = ROOT / "configs" / "relation_safety_state_v58_replay_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "relation_authorized_action_compiler_v57_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "relation_safety_state_v58_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relation_safety_state_v58_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relation_safety_state_v58_development_analysis.md"


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _canonical(call):
    return json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _counter(calls):
    return Counter(_canonical(call) for call in calls)


def _expected_targets(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def summarize_state(raw, dataset, prefix):
    expected = _expected_targets(dataset)
    rows = [
        row
        for row in raw["target_rows"]
        if (row["case_id"], row["target_id"]) in expected
    ]
    field = f"{prefix}_commitment"
    correct = {
        (row["case_id"], row["target_id"])
        for row in rows
        if row[field] == expected[(row["case_id"], row["target_id"])]
    }
    predicted_requested = sum(row[field] == "requested" for row in rows)
    gold_requested = sum(value == "requested" for value in expected.values())
    true_requested = sum(
        row[field] == "requested"
        and expected[(row["case_id"], row["target_id"])] == "requested"
        for row in rows
    )
    return {
        "target_count": len(rows),
        "correct_count": len(correct),
        "commitment_accuracy": _ratio(len(correct), len(rows)),
        "requested_precision": _ratio(true_requested, predicted_requested),
        "requested_recall": _ratio(true_requested, gold_requested),
        "correct_target_keys": sorted([list(key) for key in correct]),
        "failure_rows": [
            {
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "expected": expected[(row["case_id"], row["target_id"])],
                "actual": row[field],
            }
            for row in rows
            if (row["case_id"], row["target_id"]) not in correct
        ],
    }


def summarize_compiler(raw, dataset, prefix):
    cases = {case["id"]: case for case in dataset["cases"]}
    key = f"{prefix}_compilation"
    rows = []
    expected_call_count = 0
    matched_call_count = 0
    accepted_call_count = 0
    authorization_sum = 0.0
    for raw_row in raw["case_rows"]:
        case = cases[raw_row["case_id"]]
        compilation = raw_row[key]
        expected = case["expected_calls"]
        actual = compilation.get("accepted_calls") or []
        expected_counter = _counter(expected)
        actual_counter = _counter(actual)
        matched = expected_counter & actual_counter
        unexpected = actual_counter - expected_counter
        ordered_exact = list(map(_canonical, expected)) == list(map(_canonical, actual))
        rows.append(
            {
                "case_id": case["id"],
                "ordered_exact": ordered_exact,
                "expected_action": bool(expected),
                "false_action": bool(unexpected),
                "correct_restraint": not expected and not actual,
            }
        )
        expected_call_count += sum(expected_counter.values())
        matched_call_count += sum(matched.values())
        accepted_call_count += len(actual)
        authorization_sum += (
            compilation.get("authorization_provenance_coverage", 0.0) * len(actual)
        )
    no_action_rows = [row for row in rows if not row["expected_action"]]
    return {
        "case_count": len(rows),
        "ordered_exact_count": sum(row["ordered_exact"] for row in rows),
        "ordered_exact_accuracy": _ratio(sum(row["ordered_exact"] for row in rows), len(rows)),
        "false_action_case_count": sum(row["false_action"] for row in rows),
        "no_action_specificity": _ratio(
            sum(row["correct_restraint"] for row in no_action_rows), len(no_action_rows)
        ),
        "required_call_recall": _ratio(matched_call_count, expected_call_count),
        "matched_required_call_count": matched_call_count,
        "expected_call_count": expected_call_count,
        "authorization_provenance_coverage": _ratio(
            authorization_sum, accepted_call_count
        ),
        "ungrounded_execution_count": sum(
            raw_row[key].get("ungrounded_execution_count", 0)
            for raw_row in raw["case_rows"]
        ),
        "commitment_mutation_count": sum(
            raw_row[key].get("commitment_mutation_count", 0)
            for raw_row in raw["case_rows"]
        ),
        "correct_case_ids": sorted(
            row["case_id"] for row in rows if row["ordered_exact"]
        ),
        "failure_case_ids": sorted(
            row["case_id"] for row in rows if not row["ordered_exact"]
        ),
        "false_action_case_ids": sorted(
            row["case_id"] for row in rows if row["false_action"]
        ),
    }


def analyze(raw, dataset, config, lock):
    frozen = config["frozen_inputs"]
    if len(raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V58 target replay incomplete")
    if len(raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V58 case replay incomplete")
    if raw["model_calls"] != 0 or raw["paid_api_used"]:
        raise ValueError("V58 replay violated zero-cost model policy")
    if tuple(raw["conditions"]) != tuple(config["conditions"]):
        raise ValueError("V58 condition order drift")

    control_state = summarize_state(raw, dataset, "control")
    candidate_state = summarize_state(raw, dataset, "candidate")
    control_compiler = summarize_compiler(raw, dataset, "control")
    candidate_compiler = summarize_compiler(raw, dataset, "candidate")
    control_correct_targets = {
        tuple(row) for row in control_state["correct_target_keys"]
    }
    candidate_correct_targets = {
        tuple(row) for row in candidate_state["correct_target_keys"]
    }
    control_correct_cases = set(control_compiler["correct_case_ids"])
    candidate_correct_cases = set(candidate_compiler["correct_case_ids"])

    raw_targets = {
        (row["case_id"], row["target_id"]): row for row in raw["target_rows"]
    }
    target_fix_results = []
    for expected in config["prespecified_target_fixes"]:
        key = (expected["case_id"], expected["target_id"])
        row = raw_targets[key]
        relation_types = set(
            (row["candidate_state"].get("v58_relation_graph") or {}).get(
                "relation_types"
            )
            or []
        )
        passed = (
            row["control_commitment"] == expected["from"]
            and row["candidate_commitment"] == expected["to"]
            and expected["relation_type"] in relation_types
        )
        target_fix_results.append({**expected, "passed": passed})

    case_fix_results = [
        {
            "case_id": case_id,
            "control_correct": case_id in control_correct_cases,
            "candidate_correct": case_id in candidate_correct_cases,
            "passed": (
                case_id not in control_correct_cases
                and case_id in candidate_correct_cases
            ),
        }
        for case_id in config["prespecified_case_fixes"]
    ]
    comparison = {
        "state_correct_count_delta": (
            candidate_state["correct_count"] - control_state["correct_count"]
        ),
        "state_fix_count": len(candidate_correct_targets - control_correct_targets),
        "state_regression_count": len(control_correct_targets - candidate_correct_targets),
        "state_regression_target_keys": sorted(
            [list(key) for key in control_correct_targets - candidate_correct_targets]
        ),
        "ordered_exact_count_delta": (
            candidate_compiler["ordered_exact_count"]
            - control_compiler["ordered_exact_count"]
        ),
        "call_fix_count": len(candidate_correct_cases - control_correct_cases),
        "call_fix_case_ids": sorted(candidate_correct_cases - control_correct_cases),
        "call_regression_count": len(control_correct_cases - candidate_correct_cases),
        "call_regression_case_ids": sorted(control_correct_cases - candidate_correct_cases),
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
        >= gates["requested_precision_at_least"],
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
        "ungrounded_execution": candidate_compiler["ungrounded_execution_count"]
        == gates["ungrounded_execution_count"],
        "compiler_commitment_mutation": candidate_compiler[
            "commitment_mutation_count"
        ]
        == gates["commitment_mutation_by_compiler_count"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_relation_safety_state_development_analysis_v58",
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
            "authorize_independent_v58_safety_holdout"
            if passed
            else "reject_v58_development_and_diagnose_failed_relation"
        ),
        "replay_harness_lock": lock["schema"],
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
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
            "# V58 relation safety state development replay",
            "",
            "This replay reused all frozen V57 model outputs and made zero model calls.",
            "",
            "| Metric | V56 + V57 control | V58 + V57 candidate |",
            "|---|---:|---:|",
            f"| State commitments | {control_state['correct_count']}/85 ({_pct(control_state['commitment_accuracy'])}) | {candidate_state['correct_count']}/85 ({_pct(candidate_state['commitment_accuracy'])}) |",
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
                "ordered_exact": report["candidate_compiler"]["ordered_exact_count"],
                "false_actions": report["candidate_compiler"][
                    "false_action_case_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
