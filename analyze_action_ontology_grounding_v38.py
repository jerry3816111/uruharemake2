#!/usr/bin/env python3
"""Analyze V38 ontology-grounding compiler ablations."""

import argparse
import json
import statistics
from pathlib import Path

from replay_action_ontology_grounding_v38 import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_REPLAY = ROOT / "reports" / "action_ontology_grounding_v38_development_replay.json"
DEFAULT_JSON = ROOT / "reports" / "action_ontology_grounding_v38_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "action_ontology_grounding_v38_development_analysis.md"
CANDIDATE = "full_v38_candidate"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _summarize(rows, cases_by_id, condition):
    results = [row["conditions"][condition] for row in rows]
    actions = [result["action_score"] for result in results]
    frames = [result["frame_score"] for result in results]
    no_action_results = [
        result
        for row, result in zip(rows, results)
        if cases_by_id[row["case_id"]]["expected_no_action"]
    ]
    required_tp = sum(score["required_action_true_positive"] for score in actions)
    required_fn = sum(score["required_action_false_negative"] for score in actions)
    frame_tp = sum(score["frame_true_positive"] for score in frames)
    frame_fp = sum(score["frame_false_positive"] for score in frames)
    frame_fn = sum(score["frame_false_negative"] for score in frames)
    frame_denominator = 2 * frame_tp + frame_fp + frame_fn
    accepted = sum(result["accepted_call_count"] for result in results)
    anchored = sum(result["accepted_call_anchor_count"] for result in results)
    failures = []
    for row, result in zip(rows, results):
        if not result["action_score"]["exact_match"]:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "family": row["family"],
                    "user_input": row["user_input"],
                    "expected_calls": cases_by_id[row["case_id"]]["expected_calls"],
                    "actual_calls": result["action_score"]["actual_calls"],
                    "parse_errors": result["parse_errors"],
                    "parse_warnings": result["parse_warnings"],
                }
            )
    return {
        "case_count": len(results),
        "compiled_call_exact_accuracy": _rate(sum(score["exact_match"] for score in actions), len(actions)),
        "no_action_specificity": _rate(
            sum(result["action_score"]["no_action_correct"] for result in no_action_results),
            len(no_action_results),
        ),
        "required_action_recall": _rate(required_tp, required_tp + required_fn),
        "false_action_rate": _rate(sum(score["false_action"] for score in actions), len(actions)),
        "negation_violation_count": sum(score["negation_violation"] for score in actions),
        "unsupported_execution_count": sum(result["unsupported_execution"] for result in results),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in actions), len(actions)
        ),
        "parse_success_rate": _rate(sum(result["parse_success"] for result in results), len(results)),
        "commitment_frame_micro_f1": round(2 * frame_tp / frame_denominator, 4)
        if frame_denominator
        else 0.0,
        "accepted_call_anchor_coverage": _rate(anchored, accepted) if accepted else 1.0,
        "ungrounded_execution_count": sum(result["ungrounded_execution_count"] for result in results),
        "model_passes_per_case": round(
            sum(result["model_passes_used"] for result in results) / len(results), 4
        ),
        "median_latency_seconds": round(
            statistics.median(result["wall_seconds"] for result in results), 4
        ),
        "accepted_call_count": accepted,
        "grounded_accepted_call_count": anchored,
        "failure_count": len(failures),
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
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == targets["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == targets["ungrounded_execution_count"],
        "model_passes_per_case": summary["model_passes_per_case"]
        == targets["model_passes_per_case"],
        "median_latency_seconds": summary["median_latency_seconds"]
        <= targets["median_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze_report(report, dataset, config):
    cases_by_id = {case["id"]: case for case in dataset["cases"]}
    summaries = {
        condition: _summarize(report["rows"], cases_by_id, condition)
        for condition in CONDITIONS
    }
    control_results = {
        row["case_id"]: row["conditions"]["v37_single_control"]["action_score"]["exact_match"]
        for row in report["rows"]
    }
    attribution = {}
    for condition in CONDITIONS[1:]:
        fixed = []
        regressed = []
        for row in report["rows"]:
            case_id = row["case_id"]
            exact = row["conditions"][condition]["action_score"]["exact_match"]
            if not control_results[case_id] and exact:
                fixed.append(case_id)
            if control_results[case_id] and not exact:
                regressed.append(case_id)
        attribution[condition] = {"fixed_control_failures": fixed, "regressed_control_passes": regressed}

    gate = _evaluate_gate(summaries[CANDIDATE], config["development_gates"])
    return {
        "schema": "uruha_action_ontology_grounding_development_analysis_v38",
        "evidence_status": report["evidence_status"],
        "model_inference_performed": report["model_inference_performed"],
        "conditions": summaries,
        "causal_attribution": attribution,
        "candidate_gate": gate,
        "development_gate_passed": gate["passed"],
        "fresh_holdout_authorized": gate["passed"],
        "runtime_change_authorized": False,
        "decision": "authorize_fresh_v38_holdout_freeze"
        if gate["passed"]
        else "do_not_advance_v38_action_ontology_grounding",
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V38 action ontology grounding development replay",
        "",
        "This is a zero-inference replay of the frozen V37 primary outputs. It can authorize only a fresh holdout, not runtime integration.",
        "",
        "| condition | exact | no-action | recall | false action | parse | anchor coverage | failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        summary = analysis["conditions"][condition]
        lines.append(
            f"| {condition} | {_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['no_action_specificity'])} | "
            f"{_pct(summary['required_action_recall'])} | "
            f"{_pct(summary['false_action_rate'])} | "
            f"{_pct(summary['parse_success_rate'])} | "
            f"{_pct(summary['accepted_call_anchor_coverage'])} | "
            f"{summary['failure_count']} |"
        )
    lines.extend(
        [
            "",
            "## Causal attribution relative to V37 single pass",
            "",
        ]
    )
    for condition, attribution in analysis["causal_attribution"].items():
        lines.append(
            f"- `{condition}` fixed `{attribution['fixed_control_failures']}` and regressed "
            f"`{attribution['regressed_control_passes']}`."
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
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    report = json.loads(args.replay.read_text(encoding="utf-8"))
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
