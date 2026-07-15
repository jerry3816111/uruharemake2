#!/usr/bin/env python3
"""Analyze fresh V56 holdout and separate perception from compilation."""

import argparse
import json
from pathlib import Path

from analyze_target_event_map_v51 import compare, summarize_condition
from run_relation_bound_event_graph_v56_holdout import (
    CONDITIONS,
    CONTROL,
    V54_HYBRID,
    V56_DETERMINISTIC,
    V56_HYBRID,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_analysis.md"


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
            if condition == V56_HYBRID and row["v56_selection_source"] == "frozen_model_fallback":
                wall_seconds = row["fresh_v51_result"]["response_metrics"]["wall_seconds"]
            if condition == V54_HYBRID and row["v54_selection_source"] == "frozen_model_fallback":
                wall_seconds = row["fresh_v51_result"]["response_metrics"]["wall_seconds"]
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


def _selective_metrics(raw, dataset, state_key, selection_key, control_condition):
    gold = _gold(dataset)
    resolved = [row for row in raw["target_rows"] if row[state_key]["resolved"]]
    fallback = [row for row in raw["target_rows"] if not row[state_key]["resolved"]]
    resolved_correct = sum(
        row[state_key]["commitment"] == gold[(row["case_id"], row["target_id"])]
        for row in resolved
    )
    fallback_correct = sum(
        row["condition_commitments"][control_condition]
        == gold[(row["case_id"], row["target_id"])]
        for row in fallback
    )
    return {
        "coverage": _rate(len(resolved), len(raw["target_rows"])),
        "resolved_count": len(resolved),
        "resolved_correct_count": resolved_correct,
        "resolved_accuracy": _rate(resolved_correct, len(resolved)),
        "fallback_count": len(fallback),
        "fallback_correct_count": fallback_correct,
        "fallback_accuracy": _rate(fallback_correct, len(fallback)),
        "selection_source_counts": {
            source: sum(row[selection_key] == source for row in raw["target_rows"])
            for source in ("deterministic_state_machine", "frozen_model_fallback")
        },
    }


def _failure_attribution(raw, dataset, summary):
    gold = _gold(dataset)
    semantic_failure_cases = set()
    resolved_state_errors = []
    fallback_errors = []
    for row in raw["target_rows"]:
        key = (row["case_id"], row["target_id"])
        expected = gold[key]
        predicted = row["condition_commitments"][V56_HYBRID]
        if predicted == expected:
            continue
        semantic_failure_cases.add(row["case_id"])
        detail = {
            "case_id": row["case_id"],
            "target_id": row["target_id"],
            "expected": expected,
            "predicted": predicted,
            "rule": row["v56_state_machine"]["resolution_rule"],
        }
        if row["v56_state_machine"]["resolved"]:
            resolved_state_errors.append(detail)
        else:
            fallback_errors.append(detail)
    call_failure_cases = {row["case_id"] for row in summary["compiled_call_failures"]}
    return {
        "resolved_state_errors": resolved_state_errors,
        "fallback_model_errors": fallback_errors,
        "compiler_only_failure_case_ids": sorted(call_failure_cases - semantic_failure_cases),
        "mixed_semantic_and_compiler_failure_case_ids": sorted(
            call_failure_cases & semantic_failure_cases
        ),
        "semantic_without_call_failure_case_ids": sorted(
            semantic_failure_cases - call_failure_cases
        ),
    }


def analyze(raw, dataset, config):
    expected_targets = config["frozen_inputs"]["grounded_target_count"]
    if not raw.get("completed_at") or len(raw["target_rows"]) != expected_targets:
        raise ValueError("V56 holdout raw report is incomplete")
    if raw.get("model_calls_made") != expected_targets or raw["paid_api_used"]:
        raise ValueError("V56 holdout model accounting mismatch")
    if tuple(raw["conditions"]) != CONDITIONS:
        raise ValueError("V56 holdout condition order drift")

    conditions = {
        condition: summarize_condition(_pseudo_raw(raw, condition), dataset, condition)
        for condition in config["conditions"]
    }
    subsets = {
        "external_exact": _subset(dataset, lambda case: case["source_type"] == "external_exact"),
        "controlled_compositional": _subset(
            dataset, lambda case: case["source_type"] == "controlled_compositional"
        ),
    }
    subgroups = {
        name: {
            condition: summarize_condition(_pseudo_raw(raw, condition), subset, condition)
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
    v54_selective = _selective_metrics(
        raw, dataset, "v54_state_machine", "v54_selection_source", CONTROL
    )
    v56_selective = _selective_metrics(
        raw, dataset, "v56_state_machine", "v56_selection_source", CONTROL
    )
    matched = compare(conditions[V54_HYBRID], conditions[V56_HYBRID])
    vs_model = compare(conditions[CONTROL], conditions[V56_HYBRID])
    attribution = _failure_attribution(raw, dataset, conditions[V56_HYBRID])

    state_gates = config["state_component_gates"]
    family_floor = min(
        row[V56_HYBRID]["commitment_accuracy"]
        for family, row in family_results.items()
        if family.startswith("controlled_")
    )
    state_checks = {
        "coverage": v56_selective["coverage"] >= state_gates["coverage_at_least"],
        "resolved_accuracy": v56_selective["resolved_accuracy"]
        >= state_gates["resolved_accuracy_at_least"],
        "hybrid_commitment_accuracy": conditions[V56_HYBRID]["commitment_accuracy"]
        >= state_gates["hybrid_commitment_accuracy_at_least"],
        "requested_precision": conditions[V56_HYBRID]["requested_commitment_precision"]
        >= state_gates["requested_commitment_precision_at_least"],
        "requested_recall": conditions[V56_HYBRID]["requested_commitment_recall"]
        >= state_gates["requested_commitment_recall_at_least"],
        "external_commitment_accuracy": subgroups["external_exact"][V56_HYBRID][
            "commitment_accuracy"
        ]
        >= state_gates["external_commitment_accuracy_at_least"],
        "controlled_commitment_accuracy": subgroups["controlled_compositional"][
            V56_HYBRID
        ]["commitment_accuracy"]
        >= state_gates["controlled_commitment_accuracy_at_least"],
        "controlled_family_floor": family_floor
        >= state_gates["controlled_family_accuracy_at_least"],
    }
    matched_gates = config["matched_comparison_gates"]
    matched_checks = {
        "commitment_delta": matched["commitment_correct_count_delta"]
        >= matched_gates["commitment_correct_count_delta_at_least"],
        "semantic_regressions": matched["semantic_regression_count"]
        <= matched_gates["semantic_regression_count_at_most"],
        "false_action_delta": matched["false_action_count_delta"]
        <= matched_gates["false_action_count_delta_at_most"],
    }
    end_gates = config["end_to_end_gates"]
    end_checks = {
        "compiled_call_exact_accuracy": conditions[V56_HYBRID][
            "compiled_call_exact_accuracy"
        ]
        >= end_gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": conditions[V56_HYBRID]["no_action_specificity"]
        >= end_gates["no_action_specificity_at_least"],
        "false_action_count": conditions[V56_HYBRID]["false_action_count"]
        == end_gates["false_action_count"],
        "negation_violation_count": conditions[V56_HYBRID]["negation_violation_count"]
        == end_gates["negation_violation_count"],
        "accepted_call_anchor_coverage": conditions[V56_HYBRID][
            "accepted_call_anchor_coverage"
        ]
        == end_gates["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": conditions[V56_HYBRID][
            "ungrounded_execution_count"
        ]
        == end_gates["ungrounded_execution_count"],
        "call_regressions": matched["call_regression_count"]
        <= end_gates["call_regression_count_at_most"],
    }
    gates = {
        "state": {
            "passed": all(state_checks.values()),
            "checks": state_checks,
            "failed_checks": [name for name, ok in state_checks.items() if not ok],
        },
        "matched": {
            "passed": all(matched_checks.values()),
            "checks": matched_checks,
            "failed_checks": [name for name, ok in matched_checks.items() if not ok],
        },
        "end_to_end": {
            "passed": all(end_checks.values()),
            "checks": end_checks,
            "failed_checks": [name for name, ok in end_checks.items() if not ok],
        },
    }
    if all(row["passed"] for row in gates.values()):
        decision = "authorize_no_actuation_shadow_design_after_compiler_review"
    elif gates["state"]["passed"] and gates["matched"]["passed"]:
        decision = "freeze_v56_state_preregister_compiler_repair"
    elif matched["semantic_regression_count"]:
        decision = "reject_v56_generalization_due_to_semantic_regression"
    elif attribution["fallback_model_errors"]:
        decision = "preregister_frozen_fallback_diagnostic"
    else:
        decision = "reject_v56_generalization_preregister_relation_revision"
    return {
        "schema": "uruha_relation_bound_event_graph_fresh_holdout_analysis_v56",
        "evidence_status": raw["evidence_status"],
        "conditions": conditions,
        "subgroups": subgroups,
        "family_results": family_results,
        "v54_selective_metrics": v54_selective,
        "v56_selective_metrics": v56_selective,
        "v56_vs_v54_matched": matched,
        "v56_vs_fresh_model": vs_model,
        "failure_attribution": attribution,
        "gates": gates,
        "decision": decision,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "broad_human_likeness_claim_authorized": False,
    }


def render_markdown(report):
    lines = [
        "# V56 fresh holdout result",
        "",
        "External exact and controlled compositional results are reported separately.",
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
    lines.extend(
        [
            "",
            f"- External exact V56 commitment: "
            f"`{_pct(report['subgroups']['external_exact'][V56_HYBRID]['commitment_accuracy'])}`.",
            f"- Controlled compositional V56 commitment: "
            f"`{_pct(report['subgroups']['controlled_compositional'][V56_HYBRID]['commitment_accuracy'])}`.",
            f"- V56 coverage / resolved accuracy: "
            f"`{_pct(report['v56_selective_metrics']['coverage'])}` / "
            f"`{_pct(report['v56_selective_metrics']['resolved_accuracy'])}`.",
            f"- Semantic fixes / regressions vs V54: "
            f"`{report['v56_vs_v54_matched']['fixed_semantic_count']}` / "
            f"`{report['v56_vs_v54_matched']['semantic_regression_count']}`.",
            f"- State / matched / end-to-end gates: "
            f"`{report['gates']['state']['passed']}` / "
            f"`{report['gates']['matched']['passed']}` / "
            f"`{report['gates']['end_to_end']['passed']}`.",
            f"- Decision: `{report['decision']}`.",
            "- No runtime, shadow, or physical VRM execution is authorized by this report.",
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
                "state_gate": report["gates"]["state"]["passed"],
                "matched_gate": report["gates"]["matched"]["passed"],
                "end_to_end_gate": report["gates"]["end_to_end"]["passed"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
