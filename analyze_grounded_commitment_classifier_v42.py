#!/usr/bin/env python3
"""Analyze V42 grounded commitment classification and select a local model."""

import argparse
import json
import math
import statistics
from pathlib import Path

from action_selective_deliberation_v37 import score_action_calls
from grounded_commitment_classifier_v42 import assemble_supported_case
from grounded_frame_isolation_v39 import (
    compile_v39,
    load_v39_anchor_ontology,
    parse_frames_with_isolation,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "grounded_commitment_classifier_v42_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
AUDIT_PATH = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
CONTROL_PATH = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
DEFAULT_RAW = ROOT / "reports" / "grounded_commitment_classifier_v42_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "grounded_commitment_classifier_v42_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "grounded_commitment_classifier_v42_development_analysis.md"


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


def summarize_v39_control(dataset, control_report):
    source_by_id = {row["case_id"]: row for row in control_report["rows"]}
    ontology = load_v39_anchor_ontology()
    target_total = 0
    commitment_correct = 0
    requested_true_positive = 0
    requested_false_positive = 0
    requested_false_negative = 0
    evidence_supported = 0
    frame_exact_cases = 0
    trace_wellformed = 0
    action_scores = []
    latencies = []
    for case in dataset["cases"]:
        source = source_by_id[case["id"]]["judgments"][0]
        parsed = parse_frames_with_isolation(case["user_input"], source["raw_reply"])
        compilation = compile_v39(case["user_input"], parsed, ontology)
        gold = _gold_supported(case)
        predicted_supported = [
            frame for frame in parsed["frames"] if frame["value"] != "unsupported"
        ]
        for key, gold_frame in gold.items():
            target_total += 1
            matches = [
                frame
                for frame in predicted_supported
                if (frame["domain"], frame["value"]) == key
            ]
            commitments = {frame["commitment"] for frame in matches}
            if commitments == {gold_frame["commitment"]}:
                commitment_correct += 1
            predicts_requested = "requested" in commitments
            gold_requested = gold_frame["commitment"] == "requested"
            if predicts_requested and gold_requested:
                requested_true_positive += 1
            elif predicts_requested:
                requested_false_positive += 1
            elif gold_requested:
                requested_false_negative += 1
            if any(
                frame["commitment"] == gold_frame["commitment"]
                and any(
                    frame["evidence"] in option or option in frame["evidence"]
                    for option in gold_frame["evidence_options"]
                )
                for frame in matches
            ):
                evidence_supported += 1
        gold_keys = {
            (domain, value, frame["commitment"])
            for (domain, value), frame in gold.items()
        }
        predicted_keys = {_frame_key(frame) for frame in predicted_supported}
        if parsed["execution_parse_success"] and predicted_keys == gold_keys:
            frame_exact_cases += 1
        trace_wellformed += parsed["trace_wellformed"]
        action_scores.append(score_action_calls(case, compilation["accepted_calls"]))
        latencies.append(source["response_metrics"]["wall_seconds"])
    no_action = [score for score in action_scores if score["expected_call_count"] == 0]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    return {
        "case_count": len(dataset["cases"]),
        "target_count": target_total,
        "trace_wellformed_rate": _rate(trace_wellformed, len(dataset["cases"])),
        "commitment_accuracy": _rate(commitment_correct, target_total),
        "requested_commitment_precision": _rate(
            requested_true_positive,
            requested_true_positive + requested_false_positive,
        ),
        "requested_commitment_recall": _rate(
            requested_true_positive,
            requested_true_positive + requested_false_negative,
        ),
        "supported_frame_case_exact_rate": _rate(
            frame_exact_cases, len(dataset["cases"])
        ),
        "selected_evidence_support_rate": _rate(evidence_supported, target_total),
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
        "median_case_latency_seconds": round(statistics.median(latencies), 4),
        "p95_case_latency_seconds": _percentile(latencies, 0.95),
    }


def summarize_condition(report, dataset, audit, condition):
    cases = {case["id"]: case for case in dataset["cases"]}
    candidates_by_case = {
        row["case_id"]: row for row in report["candidate_rows"]
    }
    judgments = {
        (row["case_id"], row["target_id"]): row["result"]
        for row in report["judgment_rows"]
        if row["condition"] == condition
    }
    ontology = load_v39_anchor_ontology()
    classifier_total = 0
    classifier_valid = 0
    commitment_correct = 0
    requested_true_positive = 0
    requested_false_positive = 0
    requested_false_negative = 0
    evidence_supported = 0
    frame_exact_cases = 0
    action_scores = []
    case_latencies = []
    accepted = 0
    anchored = 0
    ungrounded = 0
    parse_failure_targets = []
    commitment_failures = []
    frame_failures = []
    for case_id, case in cases.items():
        candidate_row = candidates_by_case[case_id]
        case_judgments = {}
        latency = 0.0
        gold = _gold_supported(case)
        for candidate in candidate_row["candidates"]:
            result = judgments[(case_id, candidate["target_id"])]
            parsed = result["parsed"]
            classifier_total += 1
            classifier_valid += parsed["parse_success"]
            latency += result["response_metrics"]["wall_seconds"]
            case_judgments[candidate["target_id"]] = parsed
            key = (candidate["domain"], candidate["value"])
            gold_commitment = gold[key]["commitment"]
            predicted = parsed.get("commitment") if parsed["parse_success"] else None
            if predicted == gold_commitment:
                commitment_correct += 1
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
                requested_true_positive += 1
            elif predicted == "requested":
                requested_false_positive += 1
            elif gold_commitment == "requested":
                requested_false_negative += 1
            if parsed["parse_success"]:
                anchor = candidate["anchors"][parsed["evidence_index"]]
                if any(
                    anchor["text"] in option or option in anchor["text"]
                    for option in gold[key]["evidence_options"]
                ):
                    evidence_supported += 1
            else:
                parse_failure_targets.append(
                    {
                        "case_id": case_id,
                        "target_id": candidate["target_id"],
                        "errors": parsed["errors"],
                    }
                )
        assembled = assemble_supported_case(
            candidate_row["candidates"], case_judgments
        )
        compilation = compile_v39(case["user_input"], assembled, ontology)
        predicted_frame_keys = {_frame_key(frame) for frame in assembled["frames"]}
        gold_frame_keys = {
            (domain, value, frame["commitment"])
            for (domain, value), frame in gold.items()
        }
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
        action_scores.append(score_action_calls(case, compilation["accepted_calls"]))
        accepted_frames = compilation.get("accepted_frames") or []
        accepted += len(accepted_frames)
        anchored += sum(bool(frame.get("matched_anchor")) for frame in accepted_frames)
        ungrounded += compilation["ungrounded_execution_count"]
        case_latencies.append(latency)
    no_action = [
        score for score in action_scores if score["expected_call_count"] == 0
    ]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    audit_summary = audit["summary"]
    return {
        "case_count": len(cases),
        "candidate_target_recall": audit_summary["supported_target_recall"],
        "candidate_precision": audit_summary["candidate_precision"],
        "classifier_target_count": classifier_total,
        "classifier_parse_success_rate": _rate(classifier_valid, classifier_total),
        "commitment_accuracy": _rate(commitment_correct, classifier_total),
        "requested_commitment_precision": _rate(
            requested_true_positive,
            requested_true_positive + requested_false_positive,
        ),
        "requested_commitment_recall": _rate(
            requested_true_positive,
            requested_true_positive + requested_false_negative,
        ),
        "supported_frame_case_exact_rate": _rate(frame_exact_cases, len(cases)),
        "selected_evidence_support_rate": _rate(evidence_supported, classifier_total),
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
        "mean_classifier_calls_per_case": _rate(classifier_total, len(cases)),
        "median_case_latency_seconds": round(statistics.median(case_latencies), 4),
        "p95_case_latency_seconds": _percentile(case_latencies, 0.95),
        "parse_failure_target_count": len(parse_failure_targets),
        "parse_failure_targets": parse_failure_targets,
        "commitment_failure_count": len(commitment_failures),
        "commitment_failures": commitment_failures,
        "frame_failure_case_count": len(frame_failures),
        "frame_failures": frame_failures,
    }


def evaluate_gate(summary, targets):
    checks = {
        "candidate_target_recall": summary["candidate_target_recall"]
        == targets["candidate_target_recall"],
        "candidate_precision": summary["candidate_precision"]
        == targets["candidate_precision"],
        "classifier_parse_success_rate": summary["classifier_parse_success_rate"]
        >= targets["classifier_parse_success_rate_at_least"],
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


def analyze_report(report, dataset, audit, config, control_report):
    conditions = {}
    gates = {}
    for condition in config["model_conditions"]:
        summary = summarize_condition(report, dataset, audit, condition)
        conditions[condition] = summary
        gates[condition] = evaluate_gate(summary, config["development_gates"])
    eligible = [condition for condition, gate in gates.items() if gate["passed"]]
    selected = min(
        eligible,
        key=lambda condition: (
            config["model_conditions"][condition]["blob_bytes"],
            conditions[condition]["p95_case_latency_seconds"],
        ),
        default=None,
    )
    return {
        "schema": "uruha_grounded_commitment_classifier_development_analysis_v42",
        "evidence_status": report["evidence_status"],
        "v39_primary_control": summarize_v39_control(dataset, control_report),
        "conditions": conditions,
        "condition_gates": gates,
        "eligible_conditions": eligible,
        "selected_smallest_passing_condition": selected,
        "development_model_selected": selected is not None,
        "fresh_holdout_authorized": selected is not None,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "unsupported_action_discovery_status": "out_of_scope_separate_open_set_task",
        "decision": (
            f"authorize_fresh_v42_holdout_for_{selected}"
            if selected is not None
            else "do_not_advance_v42_grounded_commitment_classifier"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V42 grounded commitment-classifier development result",
        "",
        "The ontology fixed each supported domain-value target and exact evidence candidates. Each local model classified only the final commitment and evidence index.",
        "",
        "| model | parse | commitment | requested P/R | frame exact | call exact | false action | p95 | passed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    control = analysis["v39_primary_control"]
    lines.append(
        f"| V39 full-frame control | {_pct(control['trace_wellformed_rate'])} | "
        f"{_pct(control['commitment_accuracy'])} | "
        f"{_pct(control['requested_commitment_precision'])} / "
        f"{_pct(control['requested_commitment_recall'])} | "
        f"{_pct(control['supported_frame_case_exact_rate'])} | "
        f"{_pct(control['compiled_call_exact_accuracy'])} | "
        f"{_pct(control['false_action_rate'])} | "
        f"{control['p95_case_latency_seconds']:.2f}s | control |"
    )
    for condition, summary in analysis["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(summary['classifier_parse_success_rate'])} | "
            f"{_pct(summary['commitment_accuracy'])} | "
            f"{_pct(summary['requested_commitment_precision'])} / "
            f"{_pct(summary['requested_commitment_recall'])} | "
            f"{_pct(summary['supported_frame_case_exact_rate'])} | "
            f"{_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_pct(summary['false_action_rate'])} | "
            f"{summary['p95_case_latency_seconds']:.2f}s | "
            f"{analysis['condition_gates'][condition]['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Eligible: `{analysis['eligible_conditions']}`",
            f"- Selected: `{analysis['selected_smallest_passing_condition']}`",
            f"- Decision: `{analysis['decision']}`",
            "- Unsupported-action discovery remains a separate open-set task.",
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
    control_report = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    analysis = analyze_report(report, dataset, audit, config, control_report)
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
