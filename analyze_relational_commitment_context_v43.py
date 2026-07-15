#!/usr/bin/env python3
"""Analyze V43 commitment-only and relational-context ablations."""

import argparse
import json
import math
import statistics
from pathlib import Path

from action_selective_deliberation_v37 import score_action_calls
from grounded_frame_isolation_v39 import compile_v39, load_v39_anchor_ontology
from relational_commitment_context_v43 import assemble_commitment_only_case
from run_relational_commitment_context_v43 import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relational_commitment_context_v43_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
AUDIT_PATH = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
CONTROL_PATH = ROOT / "reports" / "grounded_commitment_classifier_v42_development_analysis.json"
DEFAULT_RAW = ROOT / "reports" / "relational_commitment_context_v43_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relational_commitment_context_v43_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relational_commitment_context_v43_development_analysis.md"
CANDIDATE = "relational_context_candidate"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def _gold_supported(case):
    return {
        (frame["domain"], frame["value"]): frame
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _frame_key(frame):
    return (frame["domain"], frame["value"], frame["commitment"])


def summarize_condition(report, dataset, audit, condition):
    cases = {case["id"]: case for case in dataset["cases"]}
    candidate_rows = {row["case_id"]: row for row in report["candidate_rows"]}
    judgments = {
        (row["case_id"], row["target_id"]): row["result"]
        for row in report["judgment_rows"]
        if row["condition"] == condition
    }
    ontology = load_v39_anchor_ontology()
    total = 0
    valid = 0
    correct = 0
    requested_tp = 0
    requested_fp = 0
    requested_fn = 0
    evidence_supported = 0
    frame_exact_cases = 0
    action_scores = []
    latencies = []
    accepted = 0
    anchored = 0
    ungrounded = 0
    commitment_failures = []
    frame_failures = []
    parse_failures = []
    target_predictions = {}
    for case_id, case in cases.items():
        candidate_row = candidate_rows[case_id]
        case_judgments = {}
        latency = 0.0
        gold = _gold_supported(case)
        for candidate in candidate_row["candidates"]:
            result = judgments[(case_id, candidate["target_id"])]
            parsed = result["parsed"]
            total += 1
            valid += parsed["parse_success"]
            latency += result["response_metrics"]["wall_seconds"]
            case_judgments[candidate["target_id"]] = parsed
            key = (candidate["domain"], candidate["value"])
            gold_commitment = gold[key]["commitment"]
            predicted = parsed.get("commitment") if parsed["parse_success"] else None
            target_predictions[(case_id, candidate["target_id"])] = predicted
            if predicted == gold_commitment:
                correct += 1
            else:
                commitment_failures.append(
                    {
                        "case_id": case_id,
                        "target_id": candidate["target_id"],
                        "gold_commitment": gold_commitment,
                        "predicted_commitment": predicted,
                        "parse_errors": parsed["errors"],
                    }
                )
            if predicted == "requested" and gold_commitment == "requested":
                requested_tp += 1
            elif predicted == "requested":
                requested_fp += 1
            elif gold_commitment == "requested":
                requested_fn += 1
            if not parsed["parse_success"]:
                parse_failures.append(
                    {
                        "case_id": case_id,
                        "target_id": candidate["target_id"],
                        "errors": parsed["errors"],
                    }
                )
        assembled = assemble_commitment_only_case(
            case["user_input"], candidate_row["candidates"], case_judgments
        )
        compilation = compile_v39(case["user_input"], assembled, ontology)
        gold_frame_keys = {
            (domain, value, frame["commitment"])
            for (domain, value), frame in gold.items()
        }
        predicted_frame_keys = {_frame_key(frame) for frame in assembled["frames"]}
        if assembled["parse_success"] and predicted_frame_keys == gold_frame_keys:
            frame_exact_cases += 1
        else:
            frame_failures.append(
                {
                    "case_id": case_id,
                    "expected": [list(key) for key in sorted(gold_frame_keys)],
                    "actual": [list(key) for key in sorted(predicted_frame_keys)],
                    "parse_errors": assembled["errors"],
                }
            )
        for frame in assembled["frames"]:
            gold_frame = gold[(frame["domain"], frame["value"])]
            if any(
                frame["evidence"] in option or option in frame["evidence"]
                for option in gold_frame["evidence_options"]
            ):
                evidence_supported += 1
        action_scores.append(score_action_calls(case, compilation["accepted_calls"]))
        accepted_frames = compilation.get("accepted_frames") or []
        accepted += len(accepted_frames)
        anchored += sum(bool(frame.get("matched_anchor")) for frame in accepted_frames)
        ungrounded += compilation["ungrounded_execution_count"]
        latencies.append(latency)
    no_action = [score for score in action_scores if score["expected_call_count"] == 0]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    audit_summary = audit["summary"]
    return {
        "case_count": len(cases),
        "candidate_target_recall": audit_summary["supported_target_recall"],
        "candidate_precision": audit_summary["candidate_precision"],
        "classifier_target_count": total,
        "classifier_parse_success_rate": _rate(valid, total),
        "commitment_accuracy": _rate(correct, total),
        "requested_commitment_precision": _rate(
            requested_tp, requested_tp + requested_fp
        ),
        "requested_commitment_recall": _rate(
            requested_tp, requested_tp + requested_fn
        ),
        "supported_frame_case_exact_rate": _rate(frame_exact_cases, len(cases)),
        "selected_evidence_support_rate": _rate(evidence_supported, total),
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
                case["expected_derived_state"] == "unsupported_or_unsafe"
                and score["actual_calls"]
            )
            for case, score in zip(dataset["cases"], action_scores)
        ),
        "accepted_call_anchor_coverage": _rate(anchored, accepted) if accepted else 1.0,
        "ungrounded_execution_count": ungrounded,
        "mean_classifier_calls_per_case": _rate(total, len(cases)),
        "median_case_latency_seconds": round(statistics.median(latencies), 4),
        "p95_case_latency_seconds": _percentile(latencies, 0.95),
        "parse_failure_target_count": len(parse_failures),
        "parse_failure_targets": parse_failures,
        "commitment_failure_count": len(commitment_failures),
        "commitment_failures": commitment_failures,
        "frame_failure_case_count": len(frame_failures),
        "frame_failures": frame_failures,
        "target_predictions": [
            {
                "case_id": case_id,
                "target_id": target_id,
                "commitment": commitment,
            }
            for (case_id, target_id), commitment in sorted(target_predictions.items())
        ],
    }


def evaluate_gate(summary, targets):
    checks = {
        "candidate_target_recall": summary["candidate_target_recall"]
        == targets["candidate_target_recall"],
        "candidate_precision": summary["candidate_precision"]
        == targets["candidate_precision"],
        "classifier_parse_success_rate": summary["classifier_parse_success_rate"]
        == targets["classifier_parse_success_rate"],
        "commitment_accuracy": summary["commitment_accuracy"]
        >= targets["commitment_accuracy_at_least"],
        "requested_commitment_precision": summary["requested_commitment_precision"]
        == targets["requested_commitment_precision"],
        "requested_commitment_recall": summary["requested_commitment_recall"]
        >= targets["requested_commitment_recall_at_least"],
        "supported_frame_case_exact_rate": summary["supported_frame_case_exact_rate"]
        >= targets["supported_frame_case_exact_rate_at_least"],
        "selected_evidence_support_rate": summary["selected_evidence_support_rate"]
        >= targets["selected_evidence_support_rate_at_least"],
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
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == targets["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == targets["ungrounded_execution_count"],
        "mean_classifier_calls_per_case": summary["mean_classifier_calls_per_case"]
        <= targets["mean_classifier_calls_per_case_at_most"],
        "median_case_latency_seconds": summary["median_case_latency_seconds"]
        <= targets["median_case_latency_seconds_at_most"],
        "p95_case_latency_seconds": summary["p95_case_latency_seconds"]
        <= targets["p95_case_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze_report(report, dataset, audit, config, control):
    conditions = {
        condition: summarize_condition(report, dataset, audit, condition)
        for condition in CONDITIONS
    }
    gate = evaluate_gate(conditions[CANDIDATE], config["development_gates"])
    base_predictions = {
        (row["case_id"], row["target_id"]): row["commitment"]
        for row in conditions["commitment_only_candidate"]["target_predictions"]
    }
    relational_predictions = {
        (row["case_id"], row["target_id"]): row["commitment"]
        for row in conditions[CANDIDATE]["target_predictions"]
    }
    gold = {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }
    fixed = []
    regressed = []
    for key, gold_commitment in gold.items():
        base_correct = base_predictions.get(key) == gold_commitment
        relational_correct = relational_predictions.get(key) == gold_commitment
        row = {"case_id": key[0], "target_id": key[1]}
        if not base_correct and relational_correct:
            fixed.append(row)
        if base_correct and not relational_correct:
            regressed.append(row)
    return {
        "schema": "uruha_relational_commitment_context_development_analysis_v43",
        "evidence_status": report["evidence_status"],
        "v42_evidence_index_control": control["conditions"][
            "commitment_qwen3_5_4b"
        ],
        "conditions": conditions,
        "relational_attribution": {
            "fixed_commitments_vs_commitment_only": fixed,
            "regressed_commitments_vs_commitment_only": regressed,
        },
        "candidate_gate": gate,
        "development_gate_passed": gate["passed"],
        "fresh_holdout_authorized": gate["passed"],
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "decision": (
            "authorize_fresh_v43_relational_holdout_freeze"
            if gate["passed"]
            else "do_not_advance_v43_relational_commitment_context"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V43 relational commitment-context development result",
        "",
        "| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows = {
        "v42_evidence_index_control": analysis["v42_evidence_index_control"],
        **analysis["conditions"],
    }
    for name, summary in rows.items():
        lines.append(
            f"| {name} | {_pct(summary['classifier_parse_success_rate'])} | "
            f"{_pct(summary['commitment_accuracy'])} | "
            f"{_pct(summary['requested_commitment_precision'])} / "
            f"{_pct(summary['requested_commitment_recall'])} | "
            f"{_pct(summary['supported_frame_case_exact_rate'])} | "
            f"{_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['selected_evidence_support_rate'])} | "
            f"{summary['p95_case_latency_seconds']:.2f}s |"
        )
    lines.extend(
        [
            "",
            f"- Relational candidate passed: `{analysis['candidate_gate']['passed']}`",
            f"- Failed checks: `{analysis['candidate_gate']['failed_checks']}`",
            f"- Fixed commitments: `{analysis['relational_attribution']['fixed_commitments_vs_commitment_only']}`",
            f"- Regressed commitments: `{analysis['relational_attribution']['regressed_commitments_vs_commitment_only']}`",
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
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    analysis = analyze_report(report, dataset, audit, config, control)
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
