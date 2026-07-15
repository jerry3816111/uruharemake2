#!/usr/bin/env python3
"""Analyze the preregistered V40 development experiment."""

import argparse
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "domain_separated_action_contract_v40_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
CONTROL_PATH = ROOT / "reports" / "grounded_frame_isolation_v39_development_analysis.json"
DEFAULT_RAW = ROOT / "reports" / "domain_separated_action_contract_v40_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "domain_separated_action_contract_v40_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "domain_separated_action_contract_v40_development_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def summarize_candidate(rows, cases_by_id):
    results = [row["result"] for row in rows]
    actions = [result["action_score"] for result in results]
    no_action = [
        result
        for row, result in zip(rows, results)
        if cases_by_id[row["case_id"]]["expected_no_action"]
    ]
    required_tp = sum(score["required_action_true_positive"] for score in actions)
    required_fn = sum(score["required_action_false_negative"] for score in actions)
    accepted = sum(result["accepted_call_count"] for result in results)
    anchored = sum(result["accepted_call_anchor_count"] for result in results)
    latencies = [result["response_metrics"]["wall_seconds"] for result in results]
    failures = []
    warning_cases = []
    fatal_cases = []
    for row, result in zip(rows, results):
        parsed = result["parsed"]
        if parsed["warnings"]:
            warning_cases.append(
                {"case_id": row["case_id"], "warnings": parsed["warnings"]}
            )
        if parsed["errors"]:
            fatal_cases.append(
                {"case_id": row["case_id"], "errors": parsed["errors"]}
            )
        if not result["action_score"]["exact_match"]:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "user_input": row["user_input"],
                    "expected_calls": cases_by_id[row["case_id"]]["expected_calls"],
                    "actual_calls": result["action_score"]["actual_calls"],
                }
            )
    return {
        "case_count": len(results),
        "compiled_call_exact_accuracy": _rate(
            sum(score["exact_match"] for score in actions), len(actions)
        ),
        "no_action_specificity": _rate(
            sum(result["action_score"]["no_action_correct"] for result in no_action),
            len(no_action),
        ),
        "required_action_recall": _rate(required_tp, required_tp + required_fn),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in actions), len(actions)
        ),
        "negation_violation_count": sum(
            score["negation_violation"] for score in actions
        ),
        "unsupported_execution_count": sum(
            result["unsupported_execution"] for result in results
        ),
        "execution_parse_success_rate": _rate(
            sum(result["parsed"]["execution_parse_success"] for result in results),
            len(results),
        ),
        "trace_wellformed_rate": _rate(
            sum(result["parsed"]["trace_wellformed"] for result in results),
            len(results),
        ),
        "accepted_call_anchor_coverage": _rate(anchored, accepted) if accepted else 1.0,
        "ungrounded_execution_count": sum(
            result["compilation"]["ungrounded_execution_count"] for result in results
        ),
        "model_passes_per_case": 1.0,
        "median_latency_seconds": round(statistics.median(latencies), 4),
        "p95_latency_seconds": _percentile(latencies, 0.95),
        "failure_count": len(failures),
        "failures": failures,
        "trace_warning_case_count": len(warning_cases),
        "trace_warning_cases": warning_cases,
        "fatal_parse_case_count": len(fatal_cases),
        "fatal_parse_cases": fatal_cases,
    }


def evaluate_gate(summary, targets):
    checks = {
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= targets["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == targets["no_action_specificity"],
        "required_action_recall": summary["required_action_recall"]
        >= targets["required_action_recall_at_least"],
        "false_action_rate": summary["false_action_rate"]
        == targets["false_action_rate"],
        "negation_violation_count": summary["negation_violation_count"]
        == targets["negation_violation_count"],
        "unsupported_execution_count": summary["unsupported_execution_count"]
        == targets["unsupported_execution_count"],
        "execution_parse_success_rate": summary["execution_parse_success_rate"]
        == targets["execution_parse_success_rate"],
        "trace_wellformed_rate": summary["trace_wellformed_rate"]
        >= targets["trace_wellformed_rate_at_least"],
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == targets["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == targets["ungrounded_execution_count"],
        "model_passes_per_case": summary["model_passes_per_case"]
        == targets["model_passes_per_case"],
        "median_latency_seconds": summary["median_latency_seconds"]
        <= targets["median_latency_seconds_at_most"],
        "p95_latency_seconds": summary["p95_latency_seconds"]
        <= targets["p95_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze_report(report, dataset, control, config):
    cases_by_id = {case["id"]: case for case in dataset["cases"]}
    candidate = summarize_candidate(report["rows"], cases_by_id)
    control_summary = dict(control["conditions"]["full_v39_candidate"])
    control_warnings = {
        row["case_id"] for row in control_summary["trace_warning_cases"]
    }
    candidate_warnings = {
        row["case_id"] for row in candidate["trace_warning_cases"]
    }
    gate = evaluate_gate(candidate, config["development_gates"])
    return {
        "schema": "uruha_domain_separated_action_contract_development_analysis_v40",
        "evidence_status": report["evidence_status"],
        "model_inference_performed": True,
        "single_changed_factor": config["causal_scope"]["single_changed_factor"],
        "conditions": {
            "v39_replay_control": control_summary,
            "v40_domain_separated_candidate": candidate,
        },
        "trace_attribution": {
            "fixed_v39_warning_cases": sorted(control_warnings - candidate_warnings),
            "persistent_warning_cases": sorted(control_warnings & candidate_warnings),
            "new_warning_cases": sorted(candidate_warnings - control_warnings),
            "action_regressions_from_perfect_v39": [
                row["case_id"] for row in candidate["failures"]
            ],
        },
        "candidate_gate": gate,
        "development_gate_passed": gate["passed"],
        "fresh_holdout_authorized": gate["passed"],
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "decision": (
            "authorize_fresh_v40_holdout_freeze"
            if gate["passed"]
            else "do_not_advance_v40_domain_separated_contract"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V40 domain-separated action-contract development result",
        "",
        "Only the model-facing output contract changed. The 4B model, retired cases, generation settings, action ontology, and V39 compiler stayed fixed.",
        "",
        "| condition | exact calls | no-action | recall | false action | execution parse | trace wellformed | median | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, summary in analysis["conditions"].items():
        p95 = summary.get("p95_latency_seconds")
        lines.append(
            f"| {name} | {_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['no_action_specificity'])} | "
            f"{_pct(summary['required_action_recall'])} | "
            f"{_pct(summary['false_action_rate'])} | "
            f"{_pct(summary['execution_parse_success_rate'])} | "
            f"{_pct(summary['trace_wellformed_rate'])} | "
            f"{summary['median_latency_seconds']:.2f}s | "
            f"{'n/a' if p95 is None else f'{p95:.2f}s'} |"
        )
    lines.extend(
        [
            "",
            f"- Fixed prior warning cases: `{analysis['trace_attribution']['fixed_v39_warning_cases']}`",
            f"- Persistent warning cases: `{analysis['trace_attribution']['persistent_warning_cases']}`",
            f"- New warning cases: `{analysis['trace_attribution']['new_warning_cases']}`",
            f"- Action regressions: `{analysis['trace_attribution']['action_regressions_from_perfect_v39']}`",
            f"- Candidate passed: `{analysis['candidate_gate']['passed']}`",
            f"- Failed checks: `{analysis['candidate_gate']['failed_checks']}`",
            f"- Decision: `{analysis['decision']}`",
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
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    analysis = analyze_report(report, dataset, control, config)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({
        "development_gate_passed": analysis["development_gate_passed"],
        "fresh_holdout_authorized": analysis["fresh_holdout_authorized"],
        "decision": analysis["decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
