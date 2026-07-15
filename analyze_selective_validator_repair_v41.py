#!/usr/bin/env python3
"""Analyze V41 selective validator-guided repair and select a local specialist."""

import argparse
import json
import math
import statistics
from pathlib import Path

from action_selective_deliberation_v37 import score_action_calls, score_observable_frames


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "selective_validator_repair_v41_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_RAW = ROOT / "reports" / "selective_validator_repair_v41_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "selective_validator_repair_v41_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "selective_validator_repair_v41_development_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def _selected_rows(report, condition):
    repairs = {
        row["case_id"]: row["result"]
        for row in report["repair_rows"]
        if row["condition"] == condition
    }
    selected = []
    for primary in report["primary_rows"]:
        repair = repairs.get(primary["case_id"])
        if repair is None:
            selected.append(
                {
                    "case_id": primary["case_id"],
                    "user_input": primary["user_input"],
                    "source": "valid_primary_unchanged",
                    "parsed": primary["parsed"],
                    "compilation": primary["compilation"],
                    "primary": primary,
                    "repair": None,
                }
            )
            continue
        choice = repair["selection"]
        selected.append(
            {
                "case_id": primary["case_id"],
                "user_input": primary["user_input"],
                "source": choice["source"],
                "parsed": choice["parsed"],
                "compilation": choice["compilation"],
                "primary": primary,
                "repair": repair,
            }
        )
    return selected


def summarize_condition(report, dataset, condition):
    cases = {case["id"]: case for case in dataset["cases"]}
    rows = _selected_rows(report, condition)
    action_scores = []
    frame_scores = []
    effective_latencies = []
    warning_cases = []
    failures = []
    accepted = 0
    anchored = 0
    repair_attempts = 0
    repair_accepts = 0
    preserved_accepts = 0
    valid_unchanged = 0
    matched_evidence = 0
    matched_frames = 0
    for row in rows:
        case = cases[row["case_id"]]
        compilation = row["compilation"]
        parsed = row["parsed"]
        action = score_action_calls(case, compilation["accepted_calls"])
        frame = score_observable_frames(
            case, parsed["frames"], parse_success=parsed["execution_parse_success"]
        )
        action_scores.append(action)
        frame_scores.append(frame)
        primary_latency = row["primary"]["response_metrics"]["wall_seconds"]
        repair_latency = 0.0
        if row["repair"] is not None:
            repair_attempts += 1
            repair_latency = row["repair"]["response_metrics"]["wall_seconds"]
            policy = row["repair"]["selection"]["repair_policy"]
            if policy["accepted"]:
                repair_accepts += 1
                preserved_accepts += policy["grounded_calls_preserved"]
        if row["source"] == "valid_primary_unchanged":
            valid_unchanged += 1
        effective_latencies.append(primary_latency + repair_latency)
        accepted_frames = compilation.get("accepted_frames") or []
        accepted += len(accepted_frames)
        anchored += sum(bool(frame_row.get("matched_anchor")) for frame_row in accepted_frames)
        matched_evidence += frame["matched_frame_evidence_supported"]
        matched_frames += frame["matched_frame_count"]
        if not parsed["trace_wellformed"]:
            warning_cases.append(
                {
                    "case_id": row["case_id"],
                    "source": row["source"],
                    "errors": parsed["errors"],
                    "warnings": parsed["warnings"],
                }
            )
        if not action["exact_match"]:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "expected_calls": case["expected_calls"],
                    "actual_calls": action["actual_calls"],
                }
            )
    no_action = [
        score
        for score, row in zip(action_scores, rows)
        if cases[row["case_id"]]["expected_no_action"]
    ]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    return {
        "case_count": len(rows),
        "compiled_call_exact_accuracy": _rate(
            sum(score["exact_match"] for score in action_scores), len(action_scores)
        ),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _rate(required_tp, required_tp + required_fn),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in action_scores), len(action_scores)
        ),
        "negation_violation_count": sum(
            score["negation_violation"] for score in action_scores
        ),
        "unsupported_execution_count": sum(
            bool(
                cases[row["case_id"]]["expected_derived_state"]
                == "unsupported_or_unsafe"
                and row["compilation"]["accepted_calls"]
            )
            for row in rows
        ),
        "execution_parse_success_rate": _rate(
            sum(row["parsed"]["execution_parse_success"] for row in rows), len(rows)
        ),
        "trace_wellformed_rate": _rate(
            sum(row["parsed"]["trace_wellformed"] for row in rows), len(rows)
        ),
        "joint_frame_exact_rate": _rate(
            sum(score["joint_frame_exact"] for score in frame_scores), len(frame_scores)
        ),
        "matched_frame_evidence_support_rate": _rate(
            matched_evidence, matched_frames
        ) if matched_frames else 1.0,
        "accepted_call_anchor_coverage": _rate(anchored, accepted) if accepted else 1.0,
        "ungrounded_execution_count": sum(
            row["compilation"]["ungrounded_execution_count"] for row in rows
        ),
        "repair_attempt_count": repair_attempts,
        "repair_acceptance_rate": _rate(repair_accepts, repair_attempts),
        "valid_primary_unchanged_count": valid_unchanged,
        "accepted_repair_call_preservation_rate": _rate(
            preserved_accepts, repair_accepts
        ) if repair_accepts else 0.0,
        "mean_repair_model_calls_per_case": _rate(repair_attempts, len(rows)),
        "effective_median_latency_seconds": round(
            statistics.median(effective_latencies), 4
        ),
        "effective_p95_latency_seconds": _percentile(effective_latencies, 0.95),
        "failure_count": len(failures),
        "failures": failures,
        "trace_warning_case_count": len(warning_cases),
        "trace_warning_cases": warning_cases,
    }


def evaluate_gate(summary, targets):
    checks = {
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        == targets["compiled_call_exact_accuracy"],
        "no_action_specificity": summary["no_action_specificity"]
        == targets["no_action_specificity"],
        "required_action_recall": summary["required_action_recall"]
        == targets["required_action_recall"],
        "false_action_rate": summary["false_action_rate"] == targets["false_action_rate"],
        "negation_violation_count": summary["negation_violation_count"]
        == targets["negation_violation_count"],
        "unsupported_execution_count": summary["unsupported_execution_count"]
        == targets["unsupported_execution_count"],
        "execution_parse_success_rate": summary["execution_parse_success_rate"]
        == targets["execution_parse_success_rate"],
        "trace_wellformed_rate": summary["trace_wellformed_rate"]
        >= targets["trace_wellformed_rate_at_least"],
        "joint_frame_exact_rate": summary["joint_frame_exact_rate"]
        >= targets["joint_frame_exact_rate_at_least"],
        "matched_frame_evidence_support_rate": summary[
            "matched_frame_evidence_support_rate"
        ] >= targets["matched_frame_evidence_support_rate_at_least"],
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == targets["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == targets["ungrounded_execution_count"],
        "repair_attempt_count": summary["repair_attempt_count"]
        == targets["repair_attempt_count"],
        "repair_acceptance_rate": summary["repair_acceptance_rate"]
        >= targets["repair_acceptance_rate_at_least"],
        "valid_primary_unchanged_count": summary["valid_primary_unchanged_count"]
        == targets["valid_primary_unchanged_count"],
        "accepted_repair_call_preservation_rate": summary[
            "accepted_repair_call_preservation_rate"
        ] == targets["accepted_repair_call_preservation_rate"],
        "mean_repair_model_calls_per_case": summary[
            "mean_repair_model_calls_per_case"
        ] <= targets["mean_repair_model_calls_per_case_at_most"],
        "effective_median_latency_seconds": summary[
            "effective_median_latency_seconds"
        ] <= targets["effective_median_latency_seconds_at_most"],
        "effective_p95_latency_seconds": summary["effective_p95_latency_seconds"]
        <= targets["effective_p95_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze_report(report, dataset, config):
    conditions = {}
    gates = {}
    for condition in config["repair_model_conditions"]:
        summary = summarize_condition(report, dataset, condition)
        conditions[condition] = summary
        gates[condition] = evaluate_gate(summary, config["development_gates"])
    eligible = [
        condition for condition, gate in gates.items() if gate["passed"]
    ]
    selected = min(
        eligible,
        key=lambda condition: (
            config["repair_model_conditions"][condition]["blob_bytes"],
            conditions[condition]["effective_p95_latency_seconds"],
        ),
        default=None,
    )
    return {
        "schema": "uruha_selective_validator_repair_development_analysis_v41",
        "evidence_status": report["evidence_status"],
        "primary_model_inference_performed": False,
        "repair_model_inference_performed": True,
        "conditions": conditions,
        "condition_gates": gates,
        "eligible_conditions": eligible,
        "selected_smallest_passing_condition": selected,
        "development_model_selected": selected is not None,
        "fresh_holdout_authorized": selected is not None,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "decision": (
            f"authorize_fresh_v41_holdout_for_{selected}"
            if selected is not None
            else "do_not_advance_v41_selective_validator_repair"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V41 selective validator-repair development result",
        "",
        "The V39 4B primary outputs were frozen. Only four validator-flagged traces were sent to each local repair specialist.",
        "",
        "| repair specialist | exact calls | trace wellformed | frame exact | repair accepted | calls/case | median | p95 | passed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, summary in analysis["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['trace_wellformed_rate'])} | "
            f"{_pct(summary['joint_frame_exact_rate'])} | "
            f"{_pct(summary['repair_acceptance_rate'])} | "
            f"{summary['mean_repair_model_calls_per_case']:.3f} | "
            f"{summary['effective_median_latency_seconds']:.2f}s | "
            f"{summary['effective_p95_latency_seconds']:.2f}s | "
            f"{analysis['condition_gates'][condition]['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Eligible: `{analysis['eligible_conditions']}`",
            f"- Selected: `{analysis['selected_smallest_passing_condition']}`",
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
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    analysis = analyze_report(report, dataset, config)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({
        "selected": analysis["selected_smallest_passing_condition"],
        "fresh_holdout_authorized": analysis["fresh_holdout_authorized"],
        "decision": analysis["decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
