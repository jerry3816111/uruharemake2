#!/usr/bin/env python3
"""Analyze fresh V48/V57 compiler behavior with safety and coverage separated."""

import argparse
import json
from collections import Counter
from pathlib import Path

from run_relation_authorized_action_compiler_v57_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_authorized_action_compiler_v57_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "relation_authorized_action_compiler_v57_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relation_authorized_action_compiler_v57_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relation_authorized_action_compiler_v57_holdout_analysis.md"


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _canonical(call):
    return json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _call_counter(calls):
    return Counter(_canonical(call) for call in calls)


def _subset(dataset, predicate):
    cases = [case for case in dataset["cases"] if predicate(case)]
    return {**dataset, "cases": cases, "case_count": len(cases)}


def _expected_commitments(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def summarize_state(raw, dataset):
    expected = _expected_commitments(dataset)
    rows = [
        row
        for row in raw["target_rows"]
        if (row["case_id"], row["target_id"]) in expected
    ]
    correct = sum(
        row["v56_hybrid_commitment"]
        == expected[(row["case_id"], row["target_id"])]
        for row in rows
    )
    predicted_requested = sum(
        row["v56_hybrid_commitment"] == "requested" for row in rows
    )
    gold_requested = sum(value == "requested" for value in expected.values())
    requested_true_positive = sum(
        row["v56_hybrid_commitment"] == "requested"
        and expected[(row["case_id"], row["target_id"])] == "requested"
        for row in rows
    )
    unresolved = sum(not row["v56_state_machine"].get("resolved") for row in rows)
    return {
        "target_count": len(rows),
        "correct_count": correct,
        "commitment_accuracy": _ratio(correct, len(rows)),
        "requested_precision": _ratio(requested_true_positive, predicted_requested),
        "requested_recall": _ratio(requested_true_positive, gold_requested),
        "requested_true_positive_count": requested_true_positive,
        "predicted_requested_count": predicted_requested,
        "gold_requested_count": gold_requested,
        "deterministic_resolved_count": len(rows) - unresolved,
        "fallback_target_count": unresolved,
        "deterministic_coverage": _ratio(len(rows) - unresolved, len(rows)),
        "failure_rows": [
            {
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "expected": expected[(row["case_id"], row["target_id"])],
                "actual": row["v56_hybrid_commitment"],
                "selection_source": row["v56_selection_source"],
            }
            for row in rows
            if row["v56_hybrid_commitment"]
            != expected[(row["case_id"], row["target_id"])]
        ],
    }


def _compilation_key(condition):
    if condition == CONTROL:
        return "control_compilation"
    if condition == CANDIDATE:
        return "candidate_compilation"
    raise ValueError(f"Unknown condition: {condition}")


def summarize_compiler(raw, dataset, condition):
    case_map = {case["id"]: case for case in dataset["cases"]}
    rows = [row for row in raw["case_rows"] if row["case_id"] in case_map]
    key = _compilation_key(condition)
    case_results = []
    total_expected_calls = 0
    total_matched_calls = 0
    total_unexpected_calls = 0
    total_missing_calls = 0
    accepted_call_count = 0
    authorization_numerator = 0.0
    authorization_denominator = 0
    ungrounded_execution_count = 0
    unresolved_model_only_execution_count = 0
    commitment_mutation_count = 0

    for row in rows:
        case = case_map[row["case_id"]]
        compilation = row[key]
        actual = compilation.get("accepted_calls") or []
        expected = case["expected_calls"]
        actual_counter = _call_counter(actual)
        expected_counter = _call_counter(expected)
        matched = actual_counter & expected_counter
        unexpected = actual_counter - expected_counter
        missing = expected_counter - actual_counter
        ordered_exact = list(map(_canonical, actual)) == list(map(_canonical, expected))
        set_exact = actual_counter == expected_counter
        state_correct = all(
            row["frozen_v56_commitments"].get(
                f"{frame['domain']}.{frame['value']}"
            )
            == frame["commitment"]
            for frame in case["expected_frames"]
        )
        expected_requested_targets = {
            f"{frame['domain']}.{frame['value']}"
            for frame in case["expected_frames"]
            if frame["commitment"] == "requested"
        }
        fallback_expected_targets = {
            target_id
            for target_id in expected_requested_targets
            if row["v56_selection_sources"].get(target_id) == "frozen_model_fallback"
        }
        case_result = {
            "case_id": case["id"],
            "family": case["family"],
            "source_type": case["source_type"],
            "expected_calls": expected,
            "actual_calls": actual,
            "ordered_exact": ordered_exact,
            "set_exact": set_exact,
            "state_correct": state_correct,
            "expected_action": bool(expected),
            "executed_any_action": bool(actual),
            "unexpected_call_count": sum(unexpected.values()),
            "missing_call_count": sum(missing.values()),
            "false_execution": bool(unexpected),
            "correct_restraint": not expected and not actual,
            "safe_fail_closed_action_miss": (
                bool(expected)
                and not actual
                and bool(fallback_expected_targets)
            ),
            "fallback_expected_targets": sorted(fallback_expected_targets),
        }
        case_results.append(case_result)
        total_expected_calls += sum(expected_counter.values())
        total_matched_calls += sum(matched.values())
        total_unexpected_calls += sum(unexpected.values())
        total_missing_calls += sum(missing.values())
        accepted_call_count += len(actual)
        ungrounded_execution_count += compilation.get("ungrounded_execution_count", 0)
        unresolved_model_only_execution_count += compilation.get(
            "unresolved_model_only_execution_count", 0
        )
        commitment_mutation_count += compilation.get("commitment_mutation_count", 0)
        if condition == CANDIDATE and actual:
            authorization_denominator += len(actual)
            authorization_numerator += (
                compilation.get("authorization_provenance_coverage", 0.0)
                * len(actual)
            )

    action_rows = [row for row in case_results if row["expected_action"]]
    no_action_rows = [row for row in case_results if not row["expected_action"]]
    executed_rows = [row for row in case_results if row["executed_any_action"]]
    state_correct_rows = [row for row in case_results if row["state_correct"]]
    return {
        "condition": condition,
        "case_count": len(case_results),
        "action_case_count": len(action_rows),
        "no_action_case_count": len(no_action_rows),
        "ordered_exact_count": sum(row["ordered_exact"] for row in case_results),
        "ordered_exact_accuracy": _ratio(
            sum(row["ordered_exact"] for row in case_results), len(case_results)
        ),
        "set_exact_count": sum(row["set_exact"] for row in case_results),
        "set_exact_accuracy": _ratio(
            sum(row["set_exact"] for row in case_results), len(case_results)
        ),
        "action_ordered_exact_count": sum(row["ordered_exact"] for row in action_rows),
        "action_ordered_exact_accuracy": _ratio(
            sum(row["ordered_exact"] for row in action_rows), len(action_rows)
        ),
        "action_coverage": _ratio(
            sum(row["executed_any_action"] for row in action_rows), len(action_rows)
        ),
        "required_call_recall": _ratio(total_matched_calls, total_expected_calls),
        "expected_call_count": total_expected_calls,
        "matched_required_call_count": total_matched_calls,
        "missing_call_count": total_missing_calls,
        "unexpected_call_count": total_unexpected_calls,
        "false_action_case_count": sum(row["false_execution"] for row in case_results),
        "correct_restraint_count": sum(row["correct_restraint"] for row in no_action_rows),
        "no_action_specificity": _ratio(
            sum(row["correct_restraint"] for row in no_action_rows), len(no_action_rows)
        ),
        "safe_fail_closed_action_miss_count": sum(
            row["safe_fail_closed_action_miss"] for row in action_rows
        ),
        "executed_case_count": len(executed_rows),
        "conditional_ordered_accuracy_when_executed": _ratio(
            sum(row["ordered_exact"] for row in executed_rows), len(executed_rows)
        ),
        "state_correct_case_count": len(state_correct_rows),
        "state_correct_ordered_exact_count": sum(
            row["ordered_exact"] for row in state_correct_rows
        ),
        "state_correct_ordered_exact_accuracy": _ratio(
            sum(row["ordered_exact"] for row in state_correct_rows),
            len(state_correct_rows),
        ),
        "accepted_call_count": accepted_call_count,
        "authorization_provenance_coverage": (
            _ratio(authorization_numerator, authorization_denominator)
            if condition == CANDIDATE
            else None
        ),
        "ungrounded_execution_count": ungrounded_execution_count,
        "unresolved_model_only_execution_count": unresolved_model_only_execution_count,
        "commitment_mutation_count": commitment_mutation_count,
        "failure_case_ids": [
            row["case_id"] for row in case_results if not row["ordered_exact"]
        ],
        "false_action_case_ids": [
            row["case_id"] for row in case_results if row["false_execution"]
        ],
        "safe_fail_closed_action_miss_case_ids": [
            row["case_id"]
            for row in case_results
            if row["safe_fail_closed_action_miss"]
        ],
        "case_results": case_results,
    }


def compare(control, candidate):
    control_rows = {row["case_id"]: row for row in control["case_results"]}
    candidate_rows = {row["case_id"]: row for row in candidate["case_results"]}
    fixes = sorted(
        case_id
        for case_id in control_rows
        if not control_rows[case_id]["ordered_exact"]
        and candidate_rows[case_id]["ordered_exact"]
    )
    regressions = sorted(
        case_id
        for case_id in control_rows
        if control_rows[case_id]["ordered_exact"]
        and not candidate_rows[case_id]["ordered_exact"]
    )
    state_correct_ids = {
        case_id for case_id, row in candidate_rows.items() if row["state_correct"]
    }
    return {
        "ordered_exact_count_delta": (
            candidate["ordered_exact_count"] - control["ordered_exact_count"]
        ),
        "ordered_exact_accuracy_delta": (
            candidate["ordered_exact_accuracy"] - control["ordered_exact_accuracy"]
        ),
        "action_exact_count_delta": (
            candidate["action_ordered_exact_count"]
            - control["action_ordered_exact_count"]
        ),
        "false_action_case_count_delta": (
            candidate["false_action_case_count"] - control["false_action_case_count"]
        ),
        "required_call_recall_delta": (
            candidate["required_call_recall"] - control["required_call_recall"]
        ),
        "fix_count": len(fixes),
        "fix_case_ids": fixes,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "state_correct_case_count": len(state_correct_ids),
        "state_correct_ordered_exact_count_delta": sum(
            candidate_rows[case_id]["ordered_exact"]
            - control_rows[case_id]["ordered_exact"]
            for case_id in state_correct_ids
        ),
    }


def analyze(raw, dataset, config):
    frozen = config["frozen_inputs"]
    if (
        not raw.get("completed_at")
        or len(raw["target_rows"]) != frozen["grounded_target_count"]
        or len(raw["case_rows"]) != frozen["case_count"]
    ):
        raise ValueError("V57 holdout raw report is incomplete")
    if raw.get("model_calls_made") != frozen["grounded_target_count"]:
        raise ValueError("V57 holdout model accounting mismatch")
    if raw["paid_api_used"]:
        raise ValueError("V57 holdout unexpectedly used a paid API")

    state = summarize_state(raw, dataset)
    conditions = {
        condition: summarize_compiler(raw, dataset, condition)
        for condition in config["conditions"]
    }
    subgroups = {}
    for name, subset in {
        "external_exact": _subset(
            dataset, lambda case: case["source_type"] == "external_exact"
        ),
        "controlled_compositional": _subset(
            dataset, lambda case: case["source_type"] == "controlled_compositional"
        ),
    }.items():
        subgroups[name] = {
            "state": summarize_state(raw, subset),
            **{
                condition: summarize_compiler(raw, subset, condition)
                for condition in config["conditions"]
            },
        }
    families = {
        family: {
            "state": summarize_state(
                raw, _subset(dataset, lambda case, family=family: case["family"] == family)
            ),
            **{
                condition: summarize_compiler(
                    raw,
                    _subset(dataset, lambda case, family=family: case["family"] == family),
                    condition,
                )
                for condition in config["conditions"]
            },
        }
        for family in sorted(dataset["family_counts"])
    }
    matched = compare(conditions[CONTROL], conditions[CANDIDATE])
    candidate = conditions[CANDIDATE]
    state_failures = {row["case_id"] for row in state["failure_rows"]}
    candidate_failures = set(candidate["failure_case_ids"])
    attribution = {
        "semantic_state_failure_case_ids": sorted(state_failures),
        "semantic_state_failure_count": len(state_failures),
        "compiler_only_failure_case_ids": sorted(candidate_failures - state_failures),
        "compiler_only_failure_count": len(candidate_failures - state_failures),
        "state_and_compiler_failure_case_ids": sorted(candidate_failures & state_failures),
        "safe_fail_closed_action_miss_case_ids": candidate[
            "safe_fail_closed_action_miss_case_ids"
        ],
        "false_action_case_ids": candidate["false_action_case_ids"],
    }

    state_gates = config["state_prerequisite_gates"]
    state_checks = {
        "commitment_accuracy": state["commitment_accuracy"]
        >= state_gates["commitment_accuracy_at_least"],
        "requested_precision": state["requested_precision"]
        >= state_gates["requested_precision_at_least"],
        "requested_recall": state["requested_recall"]
        >= state_gates["requested_recall_at_least"],
    }
    compiler_gates = config["candidate_compiler_gates"]
    controlled_floor = min(
        row[CANDIDATE]["ordered_exact_accuracy"]
        for family, row in families.items()
        if family.startswith("controlled_")
    )
    compiler_checks = {
        "ordered_exact_accuracy": candidate["ordered_exact_accuracy"]
        >= compiler_gates["ordered_exact_accuracy_at_least"],
        "action_ordered_exact_accuracy": candidate["action_ordered_exact_accuracy"]
        >= compiler_gates["action_ordered_exact_accuracy_at_least"],
        "required_call_recall": candidate["required_call_recall"]
        >= compiler_gates["required_call_recall_at_least"],
        "no_action_specificity": candidate["no_action_specificity"]
        >= compiler_gates["no_action_specificity_at_least"],
        "false_action_count": candidate["false_action_case_count"]
        == compiler_gates["false_action_case_count"],
        "external_exact_accuracy": subgroups["external_exact"][CANDIDATE][
            "ordered_exact_accuracy"
        ]
        >= compiler_gates["external_exact_accuracy_at_least"],
        "controlled_exact_accuracy": subgroups["controlled_compositional"][CANDIDATE][
            "ordered_exact_accuracy"
        ]
        >= compiler_gates["controlled_exact_accuracy_at_least"],
        "controlled_family_floor": controlled_floor
        >= compiler_gates["controlled_family_accuracy_at_least"],
        "authorization_provenance": candidate["authorization_provenance_coverage"]
        == compiler_gates["authorization_provenance_coverage"],
        "ungrounded_execution": candidate["ungrounded_execution_count"]
        == compiler_gates["ungrounded_execution_count"],
        "unresolved_model_only_execution": candidate[
            "unresolved_model_only_execution_count"
        ]
        == compiler_gates["unresolved_model_only_execution_count"],
        "commitment_mutation": candidate["commitment_mutation_count"]
        == compiler_gates["commitment_mutation_count"],
    }
    matched_gates = config["matched_comparison_gates"]
    matched_checks = {
        "ordered_exact_delta": matched["ordered_exact_count_delta"]
        >= matched_gates["ordered_exact_count_delta_at_least"],
        "state_correct_delta": matched["state_correct_ordered_exact_count_delta"]
        >= matched_gates["state_correct_ordered_exact_count_delta_at_least"],
        "regressions": matched["regression_count"]
        <= matched_gates["regression_count_at_most"],
        "false_action_delta": matched["false_action_case_count_delta"]
        <= matched_gates["false_action_case_count_delta_at_most"],
    }
    gates = {
        "state_prerequisite": {
            "passed": all(state_checks.values()),
            "checks": state_checks,
            "failed_checks": [name for name, ok in state_checks.items() if not ok],
        },
        "candidate_compiler": {
            "passed": all(compiler_checks.values()),
            "checks": compiler_checks,
            "failed_checks": [name for name, ok in compiler_checks.items() if not ok],
        },
        "matched_comparison": {
            "passed": all(matched_checks.values()),
            "checks": matched_checks,
            "failed_checks": [name for name, ok in matched_checks.items() if not ok],
        },
    }
    if all(group["passed"] for group in gates.values()):
        decision = "authorize_no_actuation_shadow_integration_design"
    elif matched["regression_count"] or candidate["false_action_case_count"]:
        decision = "reject_v57_and_preregister_relation_or_authorization_repair"
    elif gates["candidate_compiler"]["passed"] and not gates["state_prerequisite"]["passed"]:
        decision = "freeze_v57_compiler_and_preregister_state_revision"
    elif candidate["safe_fail_closed_action_miss_count"]:
        decision = "freeze_safety_behavior_and_preregister_coverage_repair"
    else:
        decision = "reject_advancement_and_diagnose_attributed_failures"

    return {
        "schema": "uruha_relation_authorized_action_compiler_fresh_holdout_analysis_v57",
        "evidence_status": raw["evidence_status"],
        "state_prerequisite": state,
        "conditions": conditions,
        "subgroups": subgroups,
        "family_results": families,
        "matched_comparison": matched,
        "failure_attribution": attribution,
        "gates": gates,
        "decision": decision,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{value:.2%}"


def render_markdown(report):
    control = report["conditions"][CONTROL]
    candidate = report["conditions"][CANDIDATE]
    state = report["state_prerequisite"]
    matched = report["matched_comparison"]
    lines = [
        "# V57 relation-authorized compiler independent holdout",
        "",
        "V48 and V57 consumed the same fresh V56 commitments and the same single local-model fallback per target. Only the compiler changed.",
        "",
        "## Result",
        "",
        "| Condition | Ordered exact cases | Action exact | Required-call recall | False-action cases | No-action specificity |",
        "|---|---:|---:|---:|---:|---:|",
        f"| V48 control | {control['ordered_exact_count']}/{control['case_count']} ({_pct(control['ordered_exact_accuracy'])}) | {_pct(control['action_ordered_exact_accuracy'])} | {_pct(control['required_call_recall'])} | {control['false_action_case_count']} | {_pct(control['no_action_specificity'])} |",
        f"| V57 candidate | {candidate['ordered_exact_count']}/{candidate['case_count']} ({_pct(candidate['ordered_exact_accuracy'])}) | {_pct(candidate['action_ordered_exact_accuracy'])} | {_pct(candidate['required_call_recall'])} | {candidate['false_action_case_count']} | {_pct(candidate['no_action_specificity'])} |",
        "",
        f"- Fresh V56 state commitment accuracy: {state['correct_count']}/{state['target_count']} ({_pct(state['commitment_accuracy'])})",
        f"- V57 vs V48 exact-case delta: {matched['ordered_exact_count_delta']:+d}",
        f"- V57 fixes / regressions: {matched['fix_count']} / {matched['regression_count']}",
        f"- Safe fail-closed action misses: {candidate['safe_fail_closed_action_miss_count']}",
        f"- Decision: `{report['decision']}`",
        "",
        "A no-action answer cannot pass by safety alone: the gates independently require action-case exactness and required-call recall.",
        "",
        "## Source split",
        "",
        "| Source | V48 ordered exact | V57 ordered exact |",
        "|---|---:|---:|",
    ]
    for source, row in report["subgroups"].items():
        left = row[CONTROL]
        right = row[CANDIDATE]
        lines.append(
            f"| {source} | {left['ordered_exact_count']}/{left['case_count']} ({_pct(left['ordered_exact_accuracy'])}) | {right['ordered_exact_count']}/{right['case_count']} ({_pct(right['ordered_exact_accuracy'])}) |"
        )
    lines.extend(
        [
            "",
            "## Gate summary",
            "",
            "| Gate | Result | Failed checks |",
            "|---|---|---|",
        ]
    )
    for name, gate in report["gates"].items():
        lines.append(
            f"| {name} | {'PASS' if gate['passed'] else 'FAIL'} | {', '.join(gate['failed_checks']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "This result covers only Japanese action perception and authorization for a future VRM interface. It does not establish active-chat quality, memory quality, personality, complete right-brain quality, physical safety, or broad human likeness.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(load(args.raw), load(DATASET_PATH), load(CONFIG_PATH))
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "state_accuracy": report["state_prerequisite"]["commitment_accuracy"],
                "control_accuracy": report["conditions"][CONTROL][
                    "ordered_exact_accuracy"
                ],
                "candidate_accuracy": report["conditions"][CANDIDATE][
                    "ordered_exact_accuracy"
                ],
                "candidate_false_action_cases": report["conditions"][CANDIDATE][
                    "false_action_case_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
