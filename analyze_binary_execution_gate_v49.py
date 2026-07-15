#!/usr/bin/env python3
"""Analyze V49 binary execution gates against matched six-way model baselines."""

import argparse
import json
import math
import statistics
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_selective_deliberation_v37 import score_action_calls
from binary_execution_gate_v49 import binary_result_to_judgment
from grounded_commitment_classifier_v42 import ground_supported_targets
from relational_commitment_context_v43 import assemble_commitment_only_case
from target_relative_scope_v48 import compile_target_relative_v48


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "binary_execution_gate_v49_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
V46_RAW_PATH = ROOT / "reports" / "commitment_model_capacity_v46_development_raw.json"
DEFAULT_RAW = ROOT / "reports" / "binary_execution_gate_v49_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "binary_execution_gate_v49_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "binary_execution_gate_v49_development_analysis.md"


MATCHED_BASELINES = {
    "qwen35_0_8b_binary": "qwen35_0_8b",
    "qwen35_2b_binary": "qwen35_2b",
    "qwen35_4b_binary": "qwen35_4b_reference",
}


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def _gold_by_target(case):
    return {
        f"{frame['domain']}.{frame['value']}": frame
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _binary_results(raw, condition):
    return {
        (row["case_id"], row["target_id"]): {
            "parsed": row["result"]["parsed"],
            "wall_seconds": row["result"]["response_metrics"]["wall_seconds"],
            "source_commitment": None,
        }
        for row in raw["judgment_rows"]
        if row["condition"] == condition
    }


def _six_way_results(raw, condition):
    results = {}
    for row in raw["judgment_rows"]:
        if row["condition"] != condition:
            continue
        parsed = row["result"]["parsed"]
        commitment = parsed.get("commitment") if parsed.get("parse_success") else None
        results[(row["case_id"], row["target_id"])] = {
            "parsed": {
                "parse_success": bool(parsed.get("parse_success")),
                "errors": parsed.get("errors") or [],
                "execute_now": commitment == "requested" if commitment else None,
            },
            "wall_seconds": row["result"]["response_metrics"]["wall_seconds"],
            "source_commitment": commitment,
        }
    return results


def summarize_source(source, dataset, ontology, *, binary_contract):
    parse_success = 0
    decision_correct = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    action_scores = []
    latencies = []
    accepted = 0
    anchored = 0
    ungrounded = 0
    target_predictions = []
    target_failures = []
    call_failures = []

    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        gold = _gold_by_target(case)
        judgments = {}
        case_latency = 0.0
        for candidate in candidates:
            key = (case["id"], candidate["target_id"])
            result = source[key]
            parsed = result["parsed"]
            valid = bool(parsed.get("parse_success"))
            predicted = parsed.get("execute_now") if valid else None
            expected = gold[candidate["target_id"]]["commitment"] == "requested"
            parse_success += int(valid)
            decision_correct += int(valid and predicted == expected)
            true_positive += int(valid and predicted is True and expected)
            false_positive += int(valid and predicted is True and not expected)
            false_negative += int((not valid or predicted is not True) and expected)
            true_negative += int(valid and predicted is False and not expected)
            case_latency += result["wall_seconds"]
            if binary_contract:
                judgment = binary_result_to_judgment(parsed)
            else:
                judgment = {
                    "parse_success": valid,
                    "errors": parsed.get("errors") or [],
                    "commitment": result["source_commitment"],
                }
            judgments[candidate["target_id"]] = judgment
            row = {
                "case_id": case["id"],
                "family": case["family"],
                "user_input": case["user_input"],
                "target_id": candidate["target_id"],
                "expected_execute_now": expected,
                "predicted_execute_now": predicted,
                "parse_success": valid,
                "parse_errors": parsed.get("errors") or [],
            }
            target_predictions.append(row)
            if not valid or predicted != expected:
                target_failures.append(row)

        assembled = assemble_commitment_only_case(
            case["user_input"], candidates, judgments
        )
        compilation = compile_target_relative_v48(
            case["user_input"], assembled, ontology
        )
        score = score_action_calls(case, compilation["accepted_calls"])
        action_scores.append(score)
        if not score["exact_match"]:
            call_failures.append(
                {
                    "case_id": case["id"],
                    "family": case["family"],
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

    total = len(target_predictions)
    no_action = [score for score in action_scores if score["expected_call_count"] == 0]
    required_tp = sum(score["required_action_true_positive"] for score in action_scores)
    required_fn = sum(score["required_action_false_negative"] for score in action_scores)
    precision = _rate(true_positive, true_positive + false_positive)
    recall = _rate(true_positive, true_positive + false_negative)
    return {
        "case_count": len(dataset["cases"]),
        "target_count": total,
        "parse_success_count": parse_success,
        "parse_success_rate": _rate(parse_success, total),
        "binary_correct_count": decision_correct,
        "binary_accuracy": _rate(decision_correct, total),
        "execute_true_positive": true_positive,
        "execute_false_positive": false_positive,
        "execute_false_negative": false_negative,
        "execute_true_negative": true_negative,
        "execute_precision": precision,
        "execute_recall": recall,
        "execute_f1": _rate(2 * precision * recall, precision + recall),
        "compiled_call_exact_count": sum(score["exact_match"] for score in action_scores),
        "compiled_call_exact_accuracy": _rate(
            sum(score["exact_match"] for score in action_scores), len(action_scores)
        ),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_true_positive": required_tp,
        "required_action_false_negative": required_fn,
        "required_action_recall": _rate(required_tp, required_tp + required_fn),
        "false_action_count": sum(score["false_action"] for score in action_scores),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in action_scores), len(action_scores)
        ),
        "negation_violation_count": sum(
            score["negation_violation"] for score in action_scores
        ),
        "accepted_call_anchor_coverage": _rate(anchored, accepted)
        if accepted
        else 1.0,
        "ungrounded_execution_count": ungrounded,
        "median_case_latency_seconds": round(statistics.median(latencies), 4),
        "p95_case_latency_seconds": _percentile(latencies, 0.95),
        "target_failure_count": len(target_failures),
        "target_failures": target_failures,
        "compiled_call_failure_case_count": len(call_failures),
        "compiled_call_failures": call_failures,
        "target_predictions": target_predictions,
    }


def evaluate_eligibility(summary, gates):
    checks = {
        "parse_success_rate": summary["parse_success_rate"]
        == gates["parse_success_rate"],
        "binary_accuracy": summary["binary_accuracy"]
        >= gates["binary_accuracy_at_least"],
        "execute_precision": summary["execute_precision"]
        == gates["execute_precision"],
        "execute_recall": summary["execute_recall"]
        >= gates["execute_recall_at_least"],
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == gates["no_action_specificity"],
        "false_action_rate": summary["false_action_rate"]
        == gates["false_action_rate"],
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


def select_model(summaries, config):
    models = {row["condition"]: row for row in config["model_conditions"]}
    eligibility = {
        name: evaluate_eligibility(summary, config["eligibility_gates"])
        for name, summary in summaries.items()
    }
    eligible = [name for name, gate in eligibility.items() if gate["passed"]]
    if not eligible:
        return {
            "selected_condition": None,
            "eligible_conditions": [],
            "eligibility": eligibility,
            "decision": "reject_binary_gate_only_hypothesis",
            "fresh_holdout_authorized": False,
            "architecture_decomposition_v50_authorized": True,
        }
    selected = min(
        eligible,
        key=lambda name: (
            models[name]["blob_bytes"],
            summaries[name]["median_case_latency_seconds"],
            name,
        ),
    )
    return {
        "selected_condition": selected,
        "eligible_conditions": eligible,
        "eligibility": eligibility,
        "decision": "authorize_selected_binary_gate_for_fresh_holdout",
        "fresh_holdout_authorized": True,
        "architecture_decomposition_v50_authorized": False,
    }


def analyze(raw, dataset, v46_raw, config):
    if not raw.get("completed_at"):
        raise ValueError("V49 development report is incomplete")
    if len(raw["judgment_rows"]) != config["expected_judgment_count"]:
        raise ValueError("V49 development judgment count mismatch")
    ontology = load_v47_anchor_ontology()
    binary_summaries = {
        row["condition"]: summarize_source(
            _binary_results(raw, row["condition"]),
            dataset,
            ontology,
            binary_contract=True,
        )
        for row in config["model_conditions"]
    }
    baselines = {
        binary_name: summarize_source(
            _six_way_results(v46_raw, baseline_name),
            dataset,
            ontology,
            binary_contract=False,
        )
        for binary_name, baseline_name in MATCHED_BASELINES.items()
    }
    deltas = {
        name: {
            "compiled_call_exact_count_delta": summary[
                "compiled_call_exact_count"
            ]
            - baselines[name]["compiled_call_exact_count"],
            "false_action_count_delta": summary["false_action_count"]
            - baselines[name]["false_action_count"],
            "required_action_true_positive_delta": summary[
                "required_action_true_positive"
            ]
            - baselines[name]["required_action_true_positive"],
            "median_case_latency_seconds_delta": round(
                summary["median_case_latency_seconds"]
                - baselines[name]["median_case_latency_seconds"],
                4,
            ),
        }
        for name, summary in binary_summaries.items()
    }
    selection = select_model(binary_summaries, config)
    selected = selection["selected_condition"]
    if selected is None:
        interpretation = config["interpretation_rules"]["no_model_selected"]
    elif selected == "qwen35_4b_binary":
        interpretation = config["interpretation_rules"]["four_b_selected"]
    else:
        interpretation = config["interpretation_rules"]["small_model_selected"]
    return {
        "schema": "uruha_binary_execution_gate_development_analysis_v49",
        "evidence_status": raw["evidence_status"],
        "binary_conditions": binary_summaries,
        "matched_six_way_baselines_with_v48_compiler": baselines,
        "binary_minus_matched_baseline": deltas,
        "selection": selection,
        "interpretation": interpretation,
        "development_only": True,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis, config):
    meta = {row["condition"]: row for row in config["model_conditions"]}
    lines = [
        "# V49 binary immediate-execution gate result",
        "",
        "Retired V45 data are used for development only. V47 candidate perception and V48 compilation are fixed.",
        "",
        "| model | size | parse | binary | execute P/R | calls | false | median / p95 | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in config["model_conditions"]:
        name = model["condition"]
        row = analysis["binary_conditions"][name]
        eligible = analysis["selection"]["eligibility"][name]["passed"]
        lines.append(
            f"| {name} | {meta[name]['parameter_size']} | "
            f"{_pct(row['parse_success_rate'])} | "
            f"{_pct(row['binary_accuracy'])} ({row['binary_correct_count']}/61) | "
            f"{_pct(row['execute_precision'])} / {_pct(row['execute_recall'])} | "
            f"{_pct(row['compiled_call_exact_accuracy'])} ({row['compiled_call_exact_count']}/48) | "
            f"{row['false_action_count']} | "
            f"{row['median_case_latency_seconds']:.2f}s / {row['p95_case_latency_seconds']:.2f}s | "
            f"{eligible} |"
        )
    lines.extend(
        [
            "",
            f"- Selected: `{analysis['selection']['selected_condition']}`",
            f"- Decision: `{analysis['selection']['decision']}`",
            f"- Interpretation: {analysis['interpretation']}",
            "- No result in this development run authorizes runtime or physical VRM execution.",
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
    config = load(CONFIG_PATH)
    analysis = analyze(load(args.raw), load(DATASET_PATH), load(V46_RAW_PATH), config)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis, config), encoding="utf-8")
    print(
        json.dumps(
            {
                "selected_condition": analysis["selection"]["selected_condition"],
                "decision": analysis["selection"]["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
