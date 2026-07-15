#!/usr/bin/env python3
"""Analyze the frozen V51-vs-V52 fresh holdout comparison."""

import argparse
import json
import math
from pathlib import Path

from analyze_target_event_map_v51 import compare, summarize_condition


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "precise_target_mentions_v52_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "precise_target_mentions_v52_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "precise_target_mentions_v52_holdout_analysis.md"
CONTROL = "v51_event_map_control"
CANDIDATE = "precise_target_mentions_candidate"


def _pct(value):
    return f"{100 * value:.2f}%"


def _subset_dataset(dataset, predicate):
    cases = [case for case in dataset["cases"] if predicate(case)]
    return {**dataset, "case_count": len(cases), "cases": cases}


def _exact_mcnemar(control_rows, candidate_rows, key_fields):
    before = {tuple(row[key] for key in key_fields): bool(row["correct"]) for row in control_rows}
    after = {tuple(row[key] for key in key_fields): bool(row["correct"]) for row in candidate_rows}
    improved = sum(not before[key] and after[key] for key in before)
    regressed = sum(before[key] and not after[key] for key in before)
    discordant = improved + regressed
    if not discordant:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, k) for k in range(0, min(improved, regressed) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "improved": improved,
        "regressed": regressed,
        "discordant": discordant,
        "two_sided_exact_p_value": round(p_value, 6),
    }


def _absolute_checks(summary, gates):
    checks = {
        "parse_success_rate": summary["parse_success_rate"] == gates["parse_success_rate"],
        "commitment_accuracy": summary["commitment_accuracy"]
        >= gates["commitment_accuracy_at_least"],
        "requested_commitment_precision": summary["requested_commitment_precision"]
        == gates["requested_commitment_precision"],
        "requested_commitment_recall": summary["requested_commitment_recall"]
        >= gates["requested_commitment_recall_at_least"],
        "compiled_call_exact_count": summary["compiled_call_exact_count"]
        >= gates["compiled_call_exact_count_at_least"],
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == gates["no_action_specificity"],
        "false_action_count": summary["false_action_count"] == gates["false_action_count"],
        "negation_violation_count": summary["negation_violation_count"]
        == gates["negation_violation_count"],
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == gates["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == gates["ungrounded_execution_count"],
        "median_case_latency_seconds": summary["median_case_latency_seconds"]
        <= gates["median_case_latency_seconds_at_most"],
        "p95_case_latency_seconds": summary["p95_case_latency_seconds"]
        <= gates["p95_case_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw, dataset, config):
    if not raw.get("completed_at"):
        raise ValueError("V52 holdout raw report is incomplete")
    if len(raw["judgment_rows"]) != config["expected_judgment_count"]:
        raise ValueError("V52 holdout judgment count mismatch")
    if not raw["construction_audit"]["passed"] or not raw["representation_audit"]["passed"]:
        raise ValueError("V52 holdout pre-inference gate was not passed")

    subsets = {
        "all": dataset,
        "external_exact": _subset_dataset(
            dataset, lambda case: case["source_type"] == "external_exact"
        ),
        "controlled_authored": _subset_dataset(
            dataset, lambda case: case["source_type"] == "controlled_authored"
        ),
        "controlled_cross_target_precision": _subset_dataset(
            dataset, lambda case: case["family"] == "controlled_cross_target_precision"
        ),
    }
    summaries = {
        subset: {
            condition: summarize_condition(raw, subset_dataset, condition)
            for condition in config["conditions"]
        }
        for subset, subset_dataset in subsets.items()
    }
    comparisons = {
        subset: compare(rows[CONTROL], rows[CANDIDATE])
        for subset, rows in summaries.items()
    }
    candidate = summaries["all"][CANDIDATE]
    absolute_gate = _absolute_checks(candidate, config["candidate_absolute_gates"])
    subgroup_gates = config["subgroup_gates"]
    subgroup_checks = {
        "external_exact_call_accuracy": summaries["external_exact"][CANDIDATE][
            "compiled_call_exact_accuracy"
        ]
        >= subgroup_gates["external_exact_call_accuracy_at_least"],
        "external_exact_false_actions": summaries["external_exact"][CANDIDATE][
            "false_action_count"
        ]
        == 0,
        "external_exact_no_action_specificity": summaries["external_exact"][CANDIDATE][
            "no_action_specificity"
        ]
        == 1.0,
        "controlled_authored_call_accuracy": summaries["controlled_authored"][CANDIDATE][
            "compiled_call_exact_accuracy"
        ]
        >= subgroup_gates["controlled_authored_call_accuracy_at_least"],
        "cross_target_call_accuracy": summaries["controlled_cross_target_precision"][
            CANDIDATE
        ]["compiled_call_exact_accuracy"]
        >= subgroup_gates["cross_target_call_accuracy_at_least"],
    }
    subgroup_gate = {
        "passed": all(subgroup_checks.values()),
        "checks": subgroup_checks,
        "failed_checks": [name for name, passed in subgroup_checks.items() if not passed],
    }
    total_comparison = comparisons["all"]
    targeted_comparison = comparisons["controlled_cross_target_precision"]
    matched_checks = {
        "semantic_regression_count": total_comparison["semantic_regression_count"] == 0,
        "call_regression_count": total_comparison["call_regression_count"] == 0,
        "false_action_count_delta": total_comparison["false_action_count_delta"] <= 0,
        "targeted_commitment_gain": targeted_comparison[
            "commitment_correct_count_delta"
        ]
        >= config["matched_comparison_gates"][
            "targeted_commitment_correct_count_delta_at_least"
        ],
        "targeted_call_gain": targeted_comparison["compiled_call_exact_count_delta"]
        >= config["matched_comparison_gates"][
            "targeted_compiled_call_exact_count_delta_at_least"
        ],
    }
    matched_gate = {
        "passed": all(matched_checks.values()),
        "checks": matched_checks,
        "failed_checks": [name for name, passed in matched_checks.items() if not passed],
    }
    passed = absolute_gate["passed"] and subgroup_gate["passed"] and matched_gate["passed"]

    if passed:
        decision = "confirm_v52_project_fresh_generalization_authorize_shadow_design"
        interpretation = (
            "V52 passed the frozen project-fresh external and controlled holdout, improved the "
            "prespecified cross-target family, and introduced no semantic, call, or safety regression. "
            "This authorizes only a separately reviewed shadow-integration design."
        )
    elif total_comparison["semantic_regression_count"] or total_comparison[
        "call_regression_count"
    ]:
        decision = "reject_v52_due_to_fresh_regression_preregister_state_machine"
        interpretation = (
            "V52 caused a new error on frozen data. Reject runtime advancement and preregister an "
            "explicit per-target discourse-state machine instead of tuning on this consumed holdout."
        )
    elif not matched_checks["targeted_commitment_gain"] or not matched_checks[
        "targeted_call_gain"
    ]:
        decision = "reject_v52_incremental_claim_preregister_state_machine"
        interpretation = (
            "V52 did not reproduce its targeted causal gain on frozen data. Its added representation "
            "is not justified; do not tune on these cases and move to an explicit state machine."
        )
    else:
        decision = "reject_v52_due_to_absolute_or_subgroup_gate"
        interpretation = (
            "V52 changed behavior but did not meet the locked safety or subgroup quality boundary. "
            "It cannot advance to shadow integration or runtime."
        )

    target_test = _exact_mcnemar(
        summaries["all"][CONTROL]["target_predictions"],
        summaries["all"][CANDIDATE]["target_predictions"],
        ("case_id", "target_id"),
    )
    return {
        "schema": "uruha_precise_target_mentions_fresh_holdout_analysis_v52",
        "evidence_status": raw["evidence_status"],
        "base_model_pretraining_exclusion_guaranteed": False,
        "subsets": summaries,
        "comparisons": comparisons,
        "candidate_absolute_gate": absolute_gate,
        "subgroup_gate": subgroup_gate,
        "matched_comparison_gate": matched_gate,
        "paired_target_mcnemar": target_test,
        "fresh_holdout_gate_passed": passed,
        "decision": decision,
        "interpretation": interpretation,
        "fresh_project_generalization_claim_authorized": passed,
        "shadow_integration_design_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "human_likeness_claim_authorized": False,
    }


def render_markdown(report):
    lines = [
        "# V52 frozen fresh-holdout result",
        "",
        "This is project-fresh evidence with an external exact-text subset. It cannot prove that "
        "the base model never encountered Tatoeba during pretraining.",
        "",
        "| subset | condition | commitment | call exact | false actions | no-action specificity |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for subset, rows in report["subsets"].items():
        for condition, row in rows.items():
            lines.append(
                f"| {subset} | {condition} | {_pct(row['commitment_accuracy'])} "
                f"({row['commitment_correct_count']}/{row['target_count']}) | "
                f"{_pct(row['compiled_call_exact_accuracy'])} "
                f"({row['compiled_call_exact_count']}/{row['case_count']}) | "
                f"{row['false_action_count']} | {_pct(row['no_action_specificity'])} |"
            )
    comparison = report["comparisons"]["all"]
    targeted = report["comparisons"]["controlled_cross_target_precision"]
    lines.extend(
        [
            "",
            f"- Overall commitment/call delta: `{comparison['commitment_correct_count_delta']:+d}` / "
            f"`{comparison['compiled_call_exact_count_delta']:+d}`.",
            f"- Cross-target commitment/call delta: "
            f"`{targeted['commitment_correct_count_delta']:+d}` / "
            f"`{targeted['compiled_call_exact_count_delta']:+d}`.",
            f"- Semantic/call regressions: `{comparison['semantic_regression_count']}` / "
            f"`{comparison['call_regression_count']}`.",
            f"- Exact paired target McNemar p-value: "
            f"`{report['paired_target_mcnemar']['two_sided_exact_p_value']}`.",
            f"- Fresh holdout gate passed: `{report['fresh_holdout_gate_passed']}`.",
            f"- Decision: `{report['decision']}`.",
            f"- Interpretation: {report['interpretation']}",
            "- Runtime and physical VRM execution remain unchanged.",
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
                "fresh_holdout_gate_passed": report["fresh_holdout_gate_passed"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
