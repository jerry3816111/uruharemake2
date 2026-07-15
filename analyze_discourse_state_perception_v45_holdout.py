#!/usr/bin/env python3
"""Analyze the frozen V45 matched holdout without tuning on its outcomes."""

import argparse
import json
import math
import statistics
from pathlib import Path

from action_selective_deliberation_v37 import score_action_calls
from grounded_frame_isolation_v39 import compile_v39, load_v39_anchor_ontology
from relational_commitment_context_v43 import (
    assemble_commitment_only_case,
    frame_from_commitment,
)
from run_discourse_state_perception_v45_holdout import CONDITIONS


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "discourse_state_perception_v45_holdout_lock.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
AUDIT_PATH = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.json"
DEFAULT_RAW = ROOT / "reports" / "discourse_state_perception_v45_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "discourse_state_perception_v45_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "discourse_state_perception_v45_holdout_analysis.md"
CONTROL = "v44_scope_control"
CANDIDATE = "v45_discourse_candidate"


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


def _evidence_supported(frame, gold_frame):
    evidence = frame.get("evidence") or ""
    return any(
        evidence in option or option in evidence
        for option in gold_frame["evidence_options"]
    )


def summarize_condition(report, dataset, audit, condition, taxonomy_tags):
    cases = {case["id"]: case for case in dataset["cases"]}
    candidate_rows = {row["case_id"]: row for row in report["candidate_rows"]}
    judgments = {
        (row["case_id"], row["target_id"]): row["result"]
        for row in report["judgment_rows"]
        if row["condition"] == condition
    }
    ontology = load_v39_anchor_ontology()
    candidate_total = 0
    candidate_valid = 0
    supported_total = 0
    supported_correct = 0
    taxonomy_total = 0
    taxonomy_correct = 0
    requested_tp = 0
    requested_fp = 0
    requested_fn = 0
    evidence_supported = 0
    frame_exact_cases = 0
    extra_candidate_count = 0
    extra_candidate_requested_count = 0
    action_scores = []
    latencies = []
    accepted = 0
    anchored = 0
    ungrounded = 0
    parse_failures = []
    commitment_failures = []
    frame_failures = []
    call_failures = []
    extra_candidate_predictions = []
    target_predictions = []

    for case_id, case in cases.items():
        candidate_row = candidate_rows[case_id]
        gold = _gold_supported(case)
        case_judgments = {}
        case_latency = 0.0
        case_is_taxonomy_boundary = bool(
            set(case.get("evaluation_tags") or []) & set(taxonomy_tags)
        )
        for candidate in candidate_row["candidates"]:
            target_id = candidate["target_id"]
            result = judgments[(case_id, target_id)]
            parsed = result["parsed"]
            predicted = parsed.get("commitment") if parsed["parse_success"] else None
            key = (candidate["domain"], candidate["value"])
            expected = gold.get(key)
            is_expected = expected is not None
            candidate_total += 1
            candidate_valid += int(bool(parsed["parse_success"]))
            case_latency += result["response_metrics"]["wall_seconds"]
            case_judgments[target_id] = parsed
            prediction_row = {
                "case_id": case_id,
                "target_id": target_id,
                "commitment": predicted,
                "is_expected_supported_target": is_expected,
            }
            target_predictions.append(prediction_row)
            if not parsed["parse_success"]:
                parse_failures.append(
                    {
                        "case_id": case_id,
                        "target_id": target_id,
                        "is_expected_supported_target": is_expected,
                        "errors": parsed["errors"],
                    }
                )
            if not is_expected:
                extra_candidate_count += 1
                extra_candidate_predictions.append(prediction_row)
                if predicted == "requested":
                    extra_candidate_requested_count += 1
                    requested_fp += 1
                continue

            supported_total += 1
            gold_commitment = expected["commitment"]
            correct = predicted == gold_commitment
            supported_correct += int(correct)
            if case_is_taxonomy_boundary:
                taxonomy_total += 1
                taxonomy_correct += int(correct)
            if not correct:
                commitment_failures.append(
                    {
                        "case_id": case_id,
                        "family": case["family"],
                        "evaluation_tags": case.get("evaluation_tags") or [],
                        "user_input": case["user_input"],
                        "target_id": target_id,
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
            if parsed["parse_success"]:
                frame = frame_from_commitment(case["user_input"], candidate, parsed)
                evidence_supported += int(_evidence_supported(frame, expected))

        assembled = assemble_commitment_only_case(
            case["user_input"], candidate_row["candidates"], case_judgments
        )
        compilation = compile_v39(case["user_input"], assembled, ontology)
        gold_frame_keys = {
            (domain, value, frame["commitment"])
            for (domain, value), frame in gold.items()
        }
        predicted_frame_keys = {_frame_key(frame) for frame in assembled["frames"]}
        frame_exact = bool(
            assembled["parse_success"] and predicted_frame_keys == gold_frame_keys
        )
        frame_exact_cases += int(frame_exact)
        if not frame_exact:
            frame_failures.append(
                {
                    "case_id": case_id,
                    "expected": [list(key) for key in sorted(gold_frame_keys)],
                    "actual": [list(key) for key in sorted(predicted_frame_keys)],
                    "parse_errors": assembled["errors"],
                }
            )
        score = score_action_calls(case, compilation["accepted_calls"])
        action_scores.append(score)
        if not score["exact_match"]:
            call_failures.append(
                {
                    "case_id": case_id,
                    "user_input": case["user_input"],
                    "expected_calls": case["expected_calls"],
                    "actual_calls": score["actual_calls"],
                }
            )
        accepted_frames = compilation.get("accepted_frames") or []
        accepted += len(accepted_frames)
        anchored += sum(bool(frame.get("matched_anchor")) for frame in accepted_frames)
        ungrounded += compilation["ungrounded_execution_count"]
        latencies.append(case_latency)

    no_action = [score for score in action_scores if score["expected_call_count"] == 0]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    return {
        "case_count": len(cases),
        "candidate_target_recall": audit["candidate_target_recall"],
        "candidate_precision": audit["candidate_precision"],
        "candidate_target_count": candidate_total,
        "supported_target_count": supported_total,
        "extra_candidate_count": extra_candidate_count,
        "classifier_parse_success_count": candidate_valid,
        "classifier_parse_success_rate": _rate(candidate_valid, candidate_total),
        "commitment_correct_count": supported_correct,
        "commitment_accuracy": _rate(supported_correct, supported_total),
        "taxonomy_boundary_correct_count": taxonomy_correct,
        "taxonomy_boundary_target_count": taxonomy_total,
        "taxonomy_boundary_accuracy": _rate(taxonomy_correct, taxonomy_total),
        "requested_commitment_true_positive": requested_tp,
        "requested_commitment_false_positive": requested_fp,
        "requested_commitment_false_negative": requested_fn,
        "requested_commitment_precision": _rate(
            requested_tp, requested_tp + requested_fp
        ),
        "requested_commitment_recall": _rate(
            requested_tp, requested_tp + requested_fn
        ),
        "supported_frame_exact_case_count": frame_exact_cases,
        "supported_frame_case_exact_rate": _rate(frame_exact_cases, len(cases)),
        "selected_evidence_support_count": evidence_supported,
        "selected_evidence_support_rate": _rate(evidence_supported, supported_total),
        "compiled_call_exact_count": sum(score["exact_match"] for score in action_scores),
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
        "extra_candidate_requested_count": extra_candidate_requested_count,
        "median_case_latency_seconds": round(statistics.median(latencies), 4),
        "p95_case_latency_seconds": _percentile(latencies, 0.95),
        "parse_failure_target_count": len(parse_failures),
        "parse_failure_targets": parse_failures,
        "commitment_failure_count": len(commitment_failures),
        "commitment_failures": commitment_failures,
        "frame_failure_case_count": len(frame_failures),
        "frame_failures": frame_failures,
        "compiled_call_failure_case_count": len(call_failures),
        "compiled_call_failures": call_failures,
        "extra_candidate_predictions": extra_candidate_predictions,
        "target_predictions": target_predictions,
    }


def evaluate_absolute_gates(summary, gates):
    checks = {
        "candidate_target_recall": summary["candidate_target_recall"]
        >= gates["candidate_target_recall_at_least"],
        "candidate_precision": summary["candidate_precision"]
        >= gates["candidate_precision_at_least"],
        "classifier_parse_success_rate": summary["classifier_parse_success_rate"]
        >= gates["classifier_parse_success_rate_at_least"],
        "commitment_accuracy": summary["commitment_accuracy"]
        >= gates["commitment_accuracy_at_least"],
        "requested_commitment_precision": summary["requested_commitment_precision"]
        == gates["requested_commitment_precision"],
        "requested_commitment_recall": summary["requested_commitment_recall"]
        >= gates["requested_commitment_recall_at_least"],
        "supported_frame_case_exact_rate": summary["supported_frame_case_exact_rate"]
        >= gates["supported_frame_case_exact_rate_at_least"],
        "selected_evidence_support_rate": summary["selected_evidence_support_rate"]
        >= gates["selected_evidence_support_rate_at_least"],
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == gates["no_action_specificity"],
        "false_action_rate": summary["false_action_rate"] == gates["false_action_rate"],
        "negation_violation_count": summary["negation_violation_count"]
        == gates["negation_violation_count"],
        "unsupported_execution_count": summary["unsupported_execution_count"]
        == gates["unsupported_execution_count"],
        "accepted_call_anchor_coverage": summary["accepted_call_anchor_coverage"]
        == gates["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": summary["ungrounded_execution_count"]
        == gates["ungrounded_execution_count"],
        "extra_candidate_requested_count": summary["extra_candidate_requested_count"]
        == gates["extra_candidate_requested_count"],
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


def _prediction_map(summary):
    return {
        (row["case_id"], row["target_id"]): row["commitment"]
        for row in summary["target_predictions"]
        if row["is_expected_supported_target"]
    }


def compare_conditions(control, candidate, dataset, taxonomy_tags):
    control_predictions = _prediction_map(control)
    candidate_predictions = _prediction_map(candidate)
    gold = {
        (case["id"], f"{frame['domain']}.{frame['value']}"): {
            "commitment": frame["commitment"],
            "user_input": case["user_input"],
            "family": case["family"],
            "evaluation_tags": case.get("evaluation_tags") or [],
        }
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }
    fixed = []
    regressed = []
    for key, expected in gold.items():
        before = control_predictions.get(key)
        after = candidate_predictions.get(key)
        row = {
            "case_id": key[0],
            "target_id": key[1],
            **expected,
            "control": before,
            "candidate": after,
        }
        if before != expected["commitment"] and after == expected["commitment"]:
            fixed.append(row)
        if before == expected["commitment"] and after != expected["commitment"]:
            regressed.append(row)
    denominator = candidate["supported_target_count"]
    return {
        "commitment_accuracy_delta_vs_control": round(
            (candidate["commitment_correct_count"] - control["commitment_correct_count"])
            / denominator,
            4,
        ),
        "commitment_correct_count_delta": candidate["commitment_correct_count"]
        - control["commitment_correct_count"],
        "taxonomy_boundary_correct_count_delta": candidate[
            "taxonomy_boundary_correct_count"
        ]
        - control["taxonomy_boundary_correct_count"],
        "taxonomy_boundary_tags": list(taxonomy_tags),
        "fixed_count": len(fixed),
        "fixed": fixed,
        "semantic_regression_count": len(regressed),
        "regressed": regressed,
    }


def evaluate_comparison_gates(comparison, gates):
    checks = {
        "commitment_accuracy_delta_vs_control": comparison[
            "commitment_accuracy_delta_vs_control"
        ]
        >= gates["commitment_accuracy_delta_vs_control_at_least"],
        "taxonomy_boundary_correct_count_delta": comparison[
            "taxonomy_boundary_correct_count_delta"
        ]
        >= gates["taxonomy_boundary_correct_count_delta_at_least"],
        "semantic_regression_count": comparison["semantic_regression_count"]
        <= gates["semantic_regression_count_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw, dataset, audit, lock):
    if not raw.get("completed_at"):
        raise ValueError("V45 holdout raw report is incomplete")
    expected_rows = len(CONDITIONS) * audit["candidate_target_count"]
    if len(raw["judgment_rows"]) != expected_rows:
        raise ValueError("V45 holdout judgment row count mismatch")
    taxonomy_tags = lock["taxonomy_boundary_tags"]
    summaries = {
        condition: summarize_condition(raw, dataset, audit, condition, taxonomy_tags)
        for condition in CONDITIONS
    }
    comparison = compare_conditions(
        summaries[CONTROL], summaries[CANDIDATE], dataset, taxonomy_tags
    )
    absolute_gate = evaluate_absolute_gates(
        summaries[CANDIDATE], lock["candidate_absolute_gates"]
    )
    comparison_gate = evaluate_comparison_gates(
        comparison, lock["matched_comparison_gates"]
    )
    passed = bool(absolute_gate["passed"] and comparison_gate["passed"])
    return {
        "schema": "uruha_discourse_state_perception_holdout_analysis_v45",
        "evidence_status": raw["evidence_status"],
        "holdout_consumed": True,
        "conditions": summaries,
        "matched_comparison": comparison,
        "candidate_absolute_gate": absolute_gate,
        "matched_comparison_gate": comparison_gate,
        "holdout_gate_passed": passed,
        "new_shadow_integration_change_authorized": passed,
        "runtime_change_authorized": False,
        "physical_vrm_execution_enabled": False,
        "post_holdout_tuning_on_this_dataset_authorized": False,
        "decision": (
            "authorize_separate_v45_shadow_integration_change"
            if passed
            else "stop_v45_without_tuning_on_consumed_holdout"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V45 fresh matched holdout result",
        "",
        "The 48-case internal holdout was frozen before either model condition saw it. It is now consumed and cannot be used for tuning.",
        "",
        "| condition | parse | commitment | boundary | requested P/R | frame exact | call exact | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CONDITIONS:
        row = analysis["conditions"][name]
        lines.append(
            f"| {name} | {_pct(row['classifier_parse_success_rate'])} "
            f"({row['classifier_parse_success_count']}/{row['candidate_target_count']}) | "
            f"{_pct(row['commitment_accuracy'])} "
            f"({row['commitment_correct_count']}/{row['supported_target_count']}) | "
            f"{_pct(row['taxonomy_boundary_accuracy'])} "
            f"({row['taxonomy_boundary_correct_count']}/{row['taxonomy_boundary_target_count']}) | "
            f"{_pct(row['requested_commitment_precision'])} / "
            f"{_pct(row['requested_commitment_recall'])} | "
            f"{_pct(row['supported_frame_case_exact_rate'])} | "
            f"{_pct(row['compiled_call_exact_accuracy'])} | "
            f"{row['p95_case_latency_seconds']:.2f}s |"
        )
    comparison = analysis["matched_comparison"]
    lines.extend(
        [
            "",
            "## Frozen comparison",
            "",
            f"- Commitment delta: `{100 * comparison['commitment_accuracy_delta_vs_control']:+.2f} pp` "
            f"({comparison['commitment_correct_count_delta']:+d} correct targets).",
            f"- Taxonomy-boundary correct-count delta: `{comparison['taxonomy_boundary_correct_count_delta']:+d}`.",
            f"- Fixed targets: `{comparison['fixed_count']}`; regressed targets: `{comparison['semantic_regression_count']}`.",
            f"- Extra candidates classified as requested: `{analysis['conditions'][CANDIDATE]['extra_candidate_requested_count']}`.",
            "",
            "## Gate",
            "",
            f"- Absolute gate passed: `{analysis['candidate_absolute_gate']['passed']}`; failures: `{analysis['candidate_absolute_gate']['failed_checks']}`.",
            f"- Matched comparison passed: `{analysis['matched_comparison_gate']['passed']}`; failures: `{analysis['matched_comparison_gate']['failed_checks']}`.",
            f"- Decision: `{analysis['decision']}`.",
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
    analysis = analyze(load(args.raw), load(DATASET_PATH), load(AUDIT_PATH), load(LOCK_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "holdout_gate_passed": analysis["holdout_gate_passed"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
