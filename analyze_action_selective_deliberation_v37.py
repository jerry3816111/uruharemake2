#!/usr/bin/env python3
"""Analyze preregistered V37 matched selective-deliberation policies."""

import argparse
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_selective_deliberation_v37_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_RAW = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "action_selective_deliberation_v37_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "action_selective_deliberation_v37_development_analysis.md"

POLICIES = (
    "single_pass_v37_control",
    "selective_three_pass_v37_candidate",
    "always_three_pass_v37_cost_reference",
)
CANDIDATE = "selective_three_pass_v37_candidate"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _quantile(values, probability):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * probability + 0.999999)))
    return round(ordered[index], 4)


def _summarize_policy(rows, cases_by_id, policy):
    results = [row["policy_results"][policy] for row in rows]
    action_scores = [result["action_score"] for result in results]
    frame_scores = [result["frame_score"] for result in results]
    expected_no_action = [
        (row, result)
        for row, result in zip(rows, results)
        if cases_by_id[row["case_id"]]["expected_no_action"]
    ]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    frame_tp = sum(score["frame_true_positive"] for score in frame_scores)
    frame_fp = sum(score["frame_false_positive"] for score in frame_scores)
    frame_fn = sum(score["frame_false_negative"] for score in frame_scores)
    frame_denominator = 2 * frame_tp + frame_fp + frame_fn
    compiled_frames = sum(result["compiled_frame_count"] for result in results)
    compiled_valid = sum(result["compiled_evidence_valid_count"] for result in results)
    escalated_latencies = [
        result["estimated_sequential_wall_seconds"]
        for result in results
        if result["escalated"]
    ]
    primary_latencies = [row["judgments"][0]["response_metrics"]["wall_seconds"] for row in rows]

    risk_tp = risk_fp = risk_fn = risk_tn = 0
    failures = []
    for row, result in zip(rows, results):
        expected_risk = row["expected_deliberation"]
        predicted_risk = result["risk"]["escalate"]
        if expected_risk and predicted_risk:
            risk_tp += 1
        elif not expected_risk and predicted_risk:
            risk_fp += 1
        elif expected_risk and not predicted_risk:
            risk_fn += 1
        else:
            risk_tn += 1
        if not result["action_score"]["exact_match"]:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "family": row["family"],
                    "user_input": row["user_input"],
                    "risk": result["risk"],
                    "escalated": result["escalated"],
                    "actual_calls": result["action_score"]["actual_calls"],
                    "expected_calls": cases_by_id[row["case_id"]]["expected_calls"],
                }
            )

    return {
        "case_count": len(rows),
        "compiled_call_exact_accuracy": _rate(
            sum(score["exact_match"] for score in action_scores), len(action_scores)
        ),
        "no_action_specificity": _rate(
            sum(result["action_score"]["no_action_correct"] for _, result in expected_no_action),
            len(expected_no_action),
        ),
        "required_action_recall": _rate(required_tp, required_tp + required_fn),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in action_scores), len(action_scores)
        ),
        "negation_violation_count": sum(score["negation_violation"] for score in action_scores),
        "unsupported_execution_count": sum(result["unsupported_execution"] for result in results),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in action_scores), len(action_scores)
        ),
        "parse_success_rate": _rate(sum(result["parse_success"] for result in results), len(results)),
        "derived_state_accuracy": _rate(
            sum(score["derived_state_correct"] for score in frame_scores), len(frame_scores)
        ),
        "joint_frame_exact_accuracy": _rate(
            sum(score["joint_frame_exact"] for score in frame_scores), len(frame_scores)
        ),
        "commitment_frame_micro_f1": round(2 * frame_tp / frame_denominator, 4)
        if frame_denominator
        else 0.0,
        "compiled_evidence_validity_rate": _rate(compiled_valid, compiled_frames)
        if compiled_frames
        else 1.0,
        "escalation_rate": _rate(sum(result["escalated"] for result in results), len(results)),
        "mean_model_passes_per_case": round(
            sum(result["passes_used"] for result in results) / len(results), 4
        ),
        "primary_pass_median_latency_seconds": round(statistics.median(primary_latencies), 4),
        "escalated_total_p95_latency_seconds": _quantile(escalated_latencies, 0.95),
        "mean_estimated_sequential_latency_seconds": round(
            statistics.mean(result["estimated_sequential_wall_seconds"] for result in results),
            4,
        ),
        "risk_router": {
            "true_positive": risk_tp,
            "false_positive": risk_fp,
            "false_negative": risk_fn,
            "true_negative": risk_tn,
            "precision": _rate(risk_tp, risk_tp + risk_fp),
            "recall": _rate(risk_tp, risk_tp + risk_fn),
        },
        "failures": failures,
    }


def _evaluate_gate(summary, targets):
    checks = {
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= targets["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == targets["no_action_specificity"],
        "required_action_recall": summary["required_action_recall"]
        >= targets["required_action_recall_at_least"],
        "false_action_rate": summary["false_action_rate"] == targets["false_action_rate"],
        "negation_violation_count": summary["negation_violation_count"]
        == targets["negation_violation_count"],
        "unsupported_execution_count": summary["unsupported_execution_count"]
        == targets["unsupported_execution_count"],
        "invalid_tool_or_argument_rate": summary["invalid_tool_or_argument_rate"]
        == targets["invalid_tool_or_argument_rate"],
        "parse_success_rate": summary["parse_success_rate"]
        >= targets["parse_success_rate_at_least"],
        "commitment_frame_micro_f1": summary["commitment_frame_micro_f1"]
        >= targets["commitment_frame_micro_f1_at_least"],
        "compiled_evidence_validity_rate": summary["compiled_evidence_validity_rate"]
        == targets["compiled_evidence_validity_rate"],
        "escalation_rate": summary["escalation_rate"] <= targets["escalation_rate_at_most"],
        "mean_model_passes_per_case": summary["mean_model_passes_per_case"]
        <= targets["mean_model_passes_per_case_at_most"],
        "primary_pass_median_latency_seconds": summary["primary_pass_median_latency_seconds"]
        <= targets["primary_pass_median_latency_seconds_at_most"],
        "escalated_total_p95_latency_seconds": summary["escalated_total_p95_latency_seconds"]
        <= targets["escalated_total_p95_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze_report(report, dataset, config):
    cases_by_id = {case["id"]: case for case in dataset["cases"]}
    summaries = {
        policy: _summarize_policy(report["rows"], cases_by_id, policy) for policy in POLICIES
    }
    gate = _evaluate_gate(summaries[CANDIDATE], config["development_gates"])
    single = summaries["single_pass_v37_control"]
    selective = summaries[CANDIDATE]
    always = summaries["always_three_pass_v37_cost_reference"]

    def delta(left, right, metric):
        return round(left[metric] - right[metric], 4)

    return {
        "schema": "uruha_action_selective_deliberation_development_analysis_v37",
        "source_report": str(DEFAULT_RAW.relative_to(ROOT)),
        "evidence_status": report["evidence_status"],
        "policies": summaries,
        "candidate_gate": gate,
        "matched_deltas": {
            "selective_minus_single": {
                metric: delta(selective, single, metric)
                for metric in (
                    "compiled_call_exact_accuracy",
                    "no_action_specificity",
                    "required_action_recall",
                    "false_action_rate",
                    "mean_model_passes_per_case",
                    "mean_estimated_sequential_latency_seconds",
                )
            },
            "always_minus_selective": {
                metric: delta(always, selective, metric)
                for metric in (
                    "compiled_call_exact_accuracy",
                    "no_action_specificity",
                    "required_action_recall",
                    "false_action_rate",
                    "mean_model_passes_per_case",
                    "mean_estimated_sequential_latency_seconds",
                )
            },
        },
        "development_gate_passed": gate["passed"],
        "fresh_holdout_authorized": gate["passed"],
        "runtime_change_authorized": False,
        "decision": "authorize_fresh_v37_holdout_freeze"
        if gate["passed"]
        else "do_not_advance_v37_selective_deliberation",
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V37 selective action deliberation development analysis",
        "",
        "All 36 items are retired V36 development cases. These results can authorize only the creation of a frozen fresh holdout, never runtime integration.",
        "",
        "| policy | exact | no-action | recall | false action | frame F1 | escalated | mean passes | mean latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in POLICIES:
        summary = analysis["policies"][policy]
        lines.append(
            f"| {policy} | {_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['no_action_specificity'])} | "
            f"{_pct(summary['required_action_recall'])} | "
            f"{_pct(summary['false_action_rate'])} | "
            f"{_pct(summary['commitment_frame_micro_f1'])} | "
            f"{_pct(summary['escalation_rate'])} | "
            f"{summary['mean_model_passes_per_case']:.2f} | "
            f"{summary['mean_estimated_sequential_latency_seconds']:.2f}s |"
        )
    lines.extend(
        [
            "",
            "## Candidate gate",
            "",
            f"- Passed: `{analysis['candidate_gate']['passed']}`",
            f"- Failed checks: `{analysis['candidate_gate']['failed_checks']}`",
            f"- Decision: `{analysis['decision']}`",
            "",
            "## Selective candidate action failures",
            "",
        ]
    )
    failures = analysis["policies"][CANDIDATE]["failures"]
    if not failures:
        lines.append("- None on the retired development set.")
    else:
        for failure in failures:
            lines.append(
                f"- `{failure['case_id']}`: expected `{failure['expected_calls']}`, "
                f"got `{failure['actual_calls']}`; risk={failure['risk']}."
            )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "A passing development gate means only that a new holdout may be authored, frozen, and run. It does not prove generalization or authorize VRM execution.",
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
    report = json.loads(args.raw.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    analysis = analyze_report(report, dataset, config)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "development_gate_passed": analysis["development_gate_passed"],
                "fresh_holdout_authorized": analysis["fresh_holdout_authorized"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
