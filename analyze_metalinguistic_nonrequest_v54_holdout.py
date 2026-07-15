#!/usr/bin/env python3
"""Analyze the frozen independent V54 holdout and attribute failures."""

import argparse
import json
from pathlib import Path

from analyze_target_event_map_v51 import compare, summarize_condition
from run_metalinguistic_nonrequest_v54_holdout import (
    CONTROL,
    DETERMINISTIC,
    HYBRID,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _pct(value):
    return f"{100 * value:.2f}%"


def _gold(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def _pseudo_raw(raw, condition):
    rows = []
    for row in raw["target_rows"]:
        if condition == CONTROL:
            parsed = row["fresh_v51_result"]["parsed"]
            parse_success = bool(parsed.get("parse_success"))
            errors = parsed.get("errors") or []
            wall_seconds = row["fresh_v51_result"]["response_metrics"]["wall_seconds"]
        else:
            parse_success = True
            errors = []
            wall_seconds = 0.0
            if condition == HYBRID and row["hybrid_selection_source"] == "frozen_model_fallback":
                wall_seconds = row["fresh_v51_result"]["response_metrics"][
                    "wall_seconds"
                ]
        rows.append(
            {
                "condition": condition,
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "result": {
                    "parsed": {
                        "parse_success": parse_success,
                        "errors": errors,
                        "commitment": row["condition_commitments"][condition],
                    },
                    "response_metrics": {"wall_seconds": wall_seconds},
                },
            }
        )
    return {"judgment_rows": rows}


def _subset(dataset, predicate):
    cases = [case for case in dataset["cases"] if predicate(case)]
    return {**dataset, "case_count": len(cases), "cases": cases}


def _target_accuracy(raw, dataset, condition, predicate):
    gold = _gold(dataset)
    rows = [row for row in raw["target_rows"] if predicate(row)]
    correct = sum(
        row["condition_commitments"][condition]
        == gold[(row["case_id"], row["target_id"])]
        for row in rows
    )
    return {
        "count": len(rows),
        "correct": correct,
        "accuracy": _rate(correct, len(rows)),
    }


def _selective_metrics(raw, dataset):
    gold = _gold(dataset)
    resolved = [row for row in raw["target_rows"] if row["state_machine"]["resolved"]]
    fallback = [row for row in raw["target_rows"] if not row["state_machine"]["resolved"]]
    resolved_correct = sum(
        row["state_machine"]["commitment"]
        == gold[(row["case_id"], row["target_id"])]
        for row in resolved
    )
    fallback_correct = sum(
        row["condition_commitments"][CONTROL]
        == gold[(row["case_id"], row["target_id"])]
        for row in fallback
    )
    rule_results = {}
    for rule in sorted({row["state_machine"]["resolution_rule"] for row in resolved}):
        rows = [
            row
            for row in resolved
            if row["state_machine"]["resolution_rule"] == rule
        ]
        correct = sum(
            row["state_machine"]["commitment"]
            == gold[(row["case_id"], row["target_id"])]
            for row in rows
        )
        rule_results[rule] = {
            "count": len(rows),
            "correct": correct,
            "accuracy": _rate(correct, len(rows)),
        }
    return {
        "coverage": _rate(len(resolved), len(raw["target_rows"])),
        "resolved_count": len(resolved),
        "resolved_correct_count": resolved_correct,
        "resolved_accuracy": _rate(resolved_correct, len(resolved)),
        "fallback_count": len(fallback),
        "fallback_correct_count": fallback_correct,
        "fallback_accuracy": _rate(fallback_correct, len(fallback)),
        "rule_results": rule_results,
    }


def _failure_attribution(raw, dataset, hybrid_summary):
    gold = _gold(dataset)
    semantic_failure_cases = set()
    resolved_state_errors = []
    fallback_errors = []
    for row in raw["target_rows"]:
        key = (row["case_id"], row["target_id"])
        expected = gold[key]
        predicted = row["condition_commitments"][HYBRID]
        if predicted == expected:
            continue
        semantic_failure_cases.add(row["case_id"])
        detail = {
            "case_id": row["case_id"],
            "target_id": row["target_id"],
            "expected": expected,
            "predicted": predicted,
            "rule": row["state_machine"]["resolution_rule"],
        }
        if row["state_machine"]["resolved"]:
            resolved_state_errors.append(detail)
        else:
            fallback_errors.append(detail)

    call_failure_cases = {
        row["case_id"] for row in hybrid_summary["compiled_call_failures"]
    }
    compiler_only = sorted(call_failure_cases - semantic_failure_cases)
    mixed = sorted(call_failure_cases & semantic_failure_cases)
    semantic_without_call = sorted(semantic_failure_cases - call_failure_cases)
    return {
        "representation_failure_count": 0,
        "resolved_state_error_count": len(resolved_state_errors),
        "resolved_state_errors": resolved_state_errors,
        "fallback_model_error_count": len(fallback_errors),
        "fallback_model_errors": fallback_errors,
        "compiler_only_failure_count": len(compiler_only),
        "compiler_only_failure_case_ids": compiler_only,
        "mixed_semantic_and_compiler_failure_count": len(mixed),
        "mixed_semantic_and_compiler_failure_case_ids": mixed,
        "semantic_without_call_failure_count": len(semantic_without_call),
        "semantic_without_call_failure_case_ids": semantic_without_call,
    }


def analyze(raw, dataset, config):
    expected_targets = config["frozen_inputs"]["grounded_target_count"]
    if not raw.get("completed_at") or len(raw["target_rows"]) != expected_targets:
        raise ValueError("V54 independent holdout raw report is incomplete")
    if raw.get("model_calls_made") != expected_targets or raw["paid_api_used"]:
        raise ValueError("V54 independent holdout model-call accounting mismatch")

    conditions = {
        condition: summarize_condition(_pseudo_raw(raw, condition), dataset, condition)
        for condition in config["conditions"]
    }
    subsets = {
        "external_exact": _subset(
            dataset, lambda case: case["source_type"] == "external_exact"
        ),
        "controlled_authored": _subset(
            dataset, lambda case: case["source_type"] == "controlled_authored"
        ),
        "metalinguistic_nonrequest": _subset(
            dataset,
            lambda case: "metalinguistic_nonrequest" in case["evaluation_tags"],
        ),
        "execution_prohibition": _subset(
            dataset, lambda case: "execution_prohibition" in case["evaluation_tags"]
        ),
        "positive_idle_request": _subset(
            dataset,
            lambda case: any(
                frame["domain"] == "motion"
                and frame["value"] == "idle"
                and frame["commitment"] == "requested"
                for frame in case["expected_frames"]
            ),
        ),
    }
    subgroups = {
        name: {
            condition: summarize_condition(
                _pseudo_raw(raw, condition), subset, condition
            )
            for condition in config["conditions"]
        }
        for name, subset in subsets.items()
    }
    family_results = {
        family: {
            condition: summarize_condition(
                _pseudo_raw(raw, condition),
                _subset(dataset, lambda case, family=family: case["family"] == family),
                condition,
            )
            for condition in config["conditions"]
        }
        for family in sorted(dataset["family_counts"])
    }

    selective = _selective_metrics(raw, dataset)
    comparison = compare(conditions[CONTROL], conditions[HYBRID])
    deterministic_comparison = compare(conditions[CONTROL], conditions[DETERMINISTIC])
    meta_ids = {
        case["id"]
        for case in subsets["metalinguistic_nonrequest"]["cases"]
    }
    prohibition_ids = {
        case["id"] for case in subsets["execution_prohibition"]["cases"]
    }
    idle_ids = {case["id"] for case in subsets["positive_idle_request"]["cases"]}
    metalinguistic_target = _target_accuracy(
        raw, dataset, HYBRID, lambda row: row["case_id"] in meta_ids
    )
    prohibition_target = _target_accuracy(
        raw, dataset, HYBRID, lambda row: row["case_id"] in prohibition_ids
    )
    idle_target = _target_accuracy(
        raw,
        dataset,
        HYBRID,
        lambda row: row["case_id"] in idle_ids and row["target_id"] == "motion.idle",
    )
    attribution = _failure_attribution(raw, dataset, conditions[HYBRID])

    state_gates = config["state_component_gates"]
    state_checks = {
        "coverage": selective["coverage"] >= state_gates["coverage_at_least"],
        "resolved_accuracy": selective["resolved_accuracy"]
        >= state_gates["resolved_accuracy_at_least"],
        "hybrid_commitment_accuracy": conditions[HYBRID]["commitment_accuracy"]
        >= state_gates["hybrid_commitment_accuracy_at_least"],
        "requested_precision": conditions[HYBRID]["requested_commitment_precision"]
        == state_gates["requested_commitment_precision"],
        "requested_recall": conditions[HYBRID]["requested_commitment_recall"]
        >= state_gates["requested_commitment_recall_at_least"],
        "external_commitment_accuracy": subgroups["external_exact"][HYBRID][
            "commitment_accuracy"
        ]
        >= state_gates["external_commitment_accuracy_at_least"],
        "controlled_commitment_accuracy": subgroups["controlled_authored"][HYBRID][
            "commitment_accuracy"
        ]
        >= state_gates["controlled_commitment_accuracy_at_least"],
        "metalinguistic_target_accuracy": metalinguistic_target["accuracy"]
        == state_gates["metalinguistic_target_accuracy"],
        "execution_prohibition_target_accuracy": prohibition_target["accuracy"]
        == state_gates["execution_prohibition_target_accuracy"],
        "positive_idle_state_accuracy": idle_target["accuracy"]
        == state_gates["positive_idle_state_accuracy"],
    }
    state_gate = {
        "passed": all(state_checks.values()),
        "checks": state_checks,
        "failed_checks": [name for name, ok in state_checks.items() if not ok],
    }

    matched_gates = config["matched_comparison_gates"]
    matched_checks = {
        "commitment_gain": comparison["commitment_correct_count_delta"]
        >= matched_gates["commitment_correct_count_delta_at_least"],
        "semantic_regressions": comparison["semantic_regression_count"]
        <= matched_gates["semantic_regression_count_at_most"],
        "false_action_delta": comparison["false_action_count_delta"]
        <= matched_gates["false_action_count_delta_at_most"],
    }
    matched_gate = {
        "passed": all(matched_checks.values()),
        "checks": matched_checks,
        "failed_checks": [name for name, ok in matched_checks.items() if not ok],
    }

    end_gates = config["end_to_end_gates"]
    end_checks = {
        "compiled_call_exact_accuracy": conditions[HYBRID][
            "compiled_call_exact_accuracy"
        ]
        >= end_gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": conditions[HYBRID]["no_action_specificity"]
        == end_gates["no_action_specificity"],
        "false_action_count": conditions[HYBRID]["false_action_count"]
        == end_gates["false_action_count"],
        "negation_violation_count": conditions[HYBRID]["negation_violation_count"]
        == end_gates["negation_violation_count"],
        "accepted_call_anchor_coverage": conditions[HYBRID][
            "accepted_call_anchor_coverage"
        ]
        == end_gates["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": conditions[HYBRID][
            "ungrounded_execution_count"
        ]
        == end_gates["ungrounded_execution_count"],
        "compiled_call_gain": comparison["compiled_call_exact_count_delta"]
        >= end_gates["compiled_call_exact_count_delta_at_least"],
        "call_regressions": comparison["call_regression_count"]
        <= end_gates["call_regression_count_at_most"],
    }
    end_gate = {
        "passed": all(end_checks.values()),
        "checks": end_checks,
        "failed_checks": [name for name, ok in end_checks.items() if not ok],
    }

    if state_gate["passed"] and matched_gate["passed"] and end_gate["passed"]:
        decision = "authorize_no_actuation_shadow_integration_design"
        interpretation = (
            "V54 generalized on the independent holdout and improved the fresh V51 control "
            "without a locked state or execution regression. Only a no-actuation shadow design "
            "is authorized; runtime and physical VRM execution remain disabled."
        )
    elif state_gate["passed"] and attribution["compiler_only_failure_count"]:
        decision = "freeze_v54_state_preregister_compiler_repair"
        interpretation = (
            "The V54 discourse-state component passed, but correct requested states were lost in "
            "the action compiler. Keep V54 frozen and repair the compiler in a separate matched "
            "experiment before any shadow integration."
        )
    elif (
        selective["fallback_count"] >= config["model_escalation_rule"][
            "minimum_fallback_targets"
        ]
        and selective["fallback_accuracy"]
        < config["model_escalation_rule"]["fallback_accuracy_below"]
    ):
        decision = "preregister_local_model_size_comparison_on_frozen_abstentions"
        interpretation = (
            "Errors concentrate in cases where the state machine abstains. Compare smaller and "
            "larger free local models only on this frozen unresolved subset; do not change rules "
            "or examples first."
        )
    else:
        decision = "reject_v54_generalization_preregister_structural_state_revision"
        interpretation = (
            "V54 did not satisfy its independent state or matched-control boundary. Do not patch "
            "individual test sentences. Use the attributed failure class to redesign the state "
            "representation under a new preregistration."
        )

    return {
        "schema": "uruha_metalinguistic_nonrequest_independent_holdout_analysis_v54",
        "evidence_status": raw["evidence_status"],
        "conditions": conditions,
        "subgroups": subgroups,
        "family_results": family_results,
        "selective_metrics": selective,
        "targeted_metrics": {
            "metalinguistic_nonrequest": metalinguistic_target,
            "execution_prohibition": prohibition_target,
            "positive_idle_state": idle_target,
        },
        "hybrid_vs_fresh_v51": comparison,
        "deterministic_vs_fresh_v51": deterministic_comparison,
        "failure_attribution": attribution,
        "state_component_gate": state_gate,
        "matched_comparison_gate": matched_gate,
        "end_to_end_gate": end_gate,
        "decision": decision,
        "interpretation": interpretation,
        "smaller_model_experiment_triggered": decision
        == "preregister_local_model_size_comparison_on_frozen_abstentions",
        "post_run_tuning_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "human_likeness_claim_authorized": False,
    }


def render_markdown(report):
    lines = [
        "# V54 independent holdout result",
        "",
        "The dataset and gates were frozen before any model inference.",
        "",
        "| condition | commitment | exact calls | false actions |",
        "|---|---:|---:|---:|",
    ]
    for condition, row in report["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(row['commitment_accuracy'])} "
            f"({row['commitment_correct_count']}/{row['target_count']}) | "
            f"{_pct(row['compiled_call_exact_accuracy'])} "
            f"({row['compiled_call_exact_count']}/{row['case_count']}) | "
            f"{row['false_action_count']} |"
        )
    selective = report["selective_metrics"]
    comparison = report["hybrid_vs_fresh_v51"]
    attribution = report["failure_attribution"]
    lines.extend(
        [
            "",
            f"- Deterministic coverage / resolved accuracy: "
            f"`{_pct(selective['coverage'])}` / `{_pct(selective['resolved_accuracy'])}`.",
            f"- Fallback targets / accuracy: `{selective['fallback_count']}` / "
            f"`{_pct(selective['fallback_accuracy'])}`.",
            f"- Commitment / exact-call delta vs fresh V51: "
            f"`{comparison['commitment_correct_count_delta']:+d}` / "
            f"`{comparison['compiled_call_exact_count_delta']:+d}`.",
            f"- Semantic / call regressions: `{comparison['semantic_regression_count']}` / "
            f"`{comparison['call_regression_count']}`.",
            f"- Resolved-state / fallback-model / compiler-only failures: "
            f"`{attribution['resolved_state_error_count']}` / "
            f"`{attribution['fallback_model_error_count']}` / "
            f"`{attribution['compiler_only_failure_count']}`.",
            f"- State / matched / end-to-end gates: "
            f"`{report['state_component_gate']['passed']}` / "
            f"`{report['matched_comparison_gate']['passed']}` / "
            f"`{report['end_to_end_gate']['passed']}`.",
            f"- Decision: `{report['decision']}`.",
            f"- Interpretation: {report['interpretation']}",
            "- No paid API, runtime change, shadow actuation, or physical VRM action was used.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(load(args.raw), load(DATASET_PATH), load(CONFIG_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "state_component_gate_passed": report["state_component_gate"][
                    "passed"
                ],
                "matched_comparison_gate_passed": report["matched_comparison_gate"][
                    "passed"
                ],
                "end_to_end_gate_passed": report["end_to_end_gate"]["passed"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
