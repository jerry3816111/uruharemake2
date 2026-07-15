#!/usr/bin/env python3
"""Analyze the V51 matched target-event-map development comparison."""

import argparse
import json
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from analyze_binary_execution_gate_v49 import summarize_source


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "target_event_map_v51_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "target_event_map_v51_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "target_event_map_v51_development_analysis.md"
CONTROL = "v48_six_way_control"
CANDIDATE = "target_event_map_candidate"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _gold_by_target(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): {
            "commitment": frame["commitment"],
            "family": case["family"],
            "user_input": case["user_input"],
        }
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _source(raw, condition):
    source = {}
    for row in raw["judgment_rows"]:
        if row["condition"] != condition:
            continue
        parsed = row["result"]["parsed"]
        commitment = parsed.get("commitment") if parsed.get("parse_success") else None
        source[(row["case_id"], row["target_id"])] = {
            "parsed": {
                "parse_success": bool(parsed.get("parse_success")),
                "errors": parsed.get("errors") or [],
                "execute_now": commitment == "requested" if commitment else None,
            },
            "wall_seconds": row["result"]["response_metrics"]["wall_seconds"],
            "source_commitment": commitment,
        }
    return source


def summarize_condition(raw, dataset, condition):
    source = _source(raw, condition)
    gold = _gold_by_target(dataset)
    predictions = []
    correct = 0
    parse_success = 0
    requested_tp = 0
    requested_fp = 0
    requested_fn = 0
    failures = []
    for key, expected in gold.items():
        row = source[key]
        valid = row["parsed"]["parse_success"]
        predicted = row["source_commitment"] if valid else None
        is_correct = valid and predicted == expected["commitment"]
        parse_success += int(valid)
        correct += int(is_correct)
        expected_requested = expected["commitment"] == "requested"
        predicted_requested = predicted == "requested"
        requested_tp += int(expected_requested and predicted_requested)
        requested_fp += int(not expected_requested and predicted_requested)
        requested_fn += int(expected_requested and not predicted_requested)
        prediction = {
            "case_id": key[0],
            "target_id": key[1],
            **expected,
            "predicted_commitment": predicted,
            "parse_success": valid,
            "correct": is_correct,
        }
        predictions.append(prediction)
        if not is_correct:
            failures.append(prediction)

    calls = summarize_source(
        source,
        dataset,
        load_v47_anchor_ontology(),
        binary_contract=False,
    )
    return {
        "case_count": len(dataset["cases"]),
        "target_count": len(gold),
        "parse_success_count": parse_success,
        "parse_success_rate": _rate(parse_success, len(gold)),
        "commitment_correct_count": correct,
        "commitment_accuracy": _rate(correct, len(gold)),
        "requested_true_positive": requested_tp,
        "requested_false_positive": requested_fp,
        "requested_false_negative": requested_fn,
        "requested_commitment_precision": _rate(
            requested_tp, requested_tp + requested_fp
        ),
        "requested_commitment_recall": _rate(
            requested_tp, requested_tp + requested_fn
        ),
        "commitment_failure_count": len(failures),
        "commitment_failures": failures,
        "target_predictions": predictions,
        "compiled_call_exact_count": calls["compiled_call_exact_count"],
        "compiled_call_exact_accuracy": calls["compiled_call_exact_accuracy"],
        "compiled_call_failure_case_count": calls[
            "compiled_call_failure_case_count"
        ],
        "compiled_call_failures": calls["compiled_call_failures"],
        "no_action_specificity": calls["no_action_specificity"],
        "required_action_recall": calls["required_action_recall"],
        "false_action_count": calls["false_action_count"],
        "false_action_rate": calls["false_action_rate"],
        "negation_violation_count": calls["negation_violation_count"],
        "accepted_call_anchor_coverage": calls["accepted_call_anchor_coverage"],
        "ungrounded_execution_count": calls["ungrounded_execution_count"],
        "median_case_latency_seconds": calls["median_case_latency_seconds"],
        "p95_case_latency_seconds": calls["p95_case_latency_seconds"],
    }


def evaluate_absolute(summary, gates):
    checks = {
        "parse_success_rate": summary["parse_success_rate"]
        == gates["parse_success_rate"],
        "commitment_accuracy": summary["commitment_accuracy"]
        >= gates["commitment_accuracy_at_least"],
        "requested_commitment_precision": summary[
            "requested_commitment_precision"
        ]
        == gates["requested_commitment_precision"],
        "requested_commitment_recall": summary["requested_commitment_recall"]
        >= gates["requested_commitment_recall_at_least"],
        "compiled_call_exact_count": summary["compiled_call_exact_count"]
        >= gates["compiled_call_exact_count_at_least"],
        "compiled_call_exact_accuracy": summary["compiled_call_exact_accuracy"]
        >= gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        == gates["no_action_specificity"],
        "false_action_count": summary["false_action_count"]
        == gates["false_action_count"],
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


def compare(control, candidate):
    before = {
        (row["case_id"], row["target_id"]): row
        for row in control["target_predictions"]
    }
    after = {
        (row["case_id"], row["target_id"]): row
        for row in candidate["target_predictions"]
    }
    fixed = []
    regressed = []
    for key in sorted(before):
        row = {
            "case_id": key[0],
            "target_id": key[1],
            "user_input": before[key]["user_input"],
            "gold_commitment": before[key]["commitment"],
            "control": before[key]["predicted_commitment"],
            "candidate": after[key]["predicted_commitment"],
        }
        if not before[key]["correct"] and after[key]["correct"]:
            fixed.append(row)
        if before[key]["correct"] and not after[key]["correct"]:
            regressed.append(row)

    control_failures = {
        row["case_id"] for row in control["compiled_call_failures"]
    }
    candidate_failures = {
        row["case_id"] for row in candidate["compiled_call_failures"]
    }
    return {
        "commitment_correct_count_delta": candidate["commitment_correct_count"]
        - control["commitment_correct_count"],
        "compiled_call_exact_count_delta": candidate["compiled_call_exact_count"]
        - control["compiled_call_exact_count"],
        "false_action_count_delta": candidate["false_action_count"]
        - control["false_action_count"],
        "fixed_semantic_count": len(fixed),
        "fixed_semantics": fixed,
        "semantic_regression_count": len(regressed),
        "semantic_regressions": regressed,
        "fixed_call_count": len(control_failures - candidate_failures),
        "fixed_call_case_ids": sorted(control_failures - candidate_failures),
        "call_regression_count": len(candidate_failures - control_failures),
        "call_regression_case_ids": sorted(candidate_failures - control_failures),
    }


def evaluate_comparison(comparison, gates):
    checks = {
        "commitment_correct_count_delta": comparison[
            "commitment_correct_count_delta"
        ]
        >= gates["commitment_correct_count_delta_at_least"],
        "compiled_call_exact_count_delta": comparison[
            "compiled_call_exact_count_delta"
        ]
        >= gates["compiled_call_exact_count_delta_at_least"],
        "false_action_count_delta": comparison["false_action_count_delta"]
        <= gates["false_action_count_delta_at_most"],
        "semantic_regression_count": comparison["semantic_regression_count"]
        == gates["semantic_regression_count"],
        "call_regression_count": comparison["call_regression_count"]
        == gates["call_regression_count"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw, dataset, config):
    if not raw.get("completed_at"):
        raise ValueError("V51 development raw report is incomplete")
    if len(raw["judgment_rows"]) != config["expected_judgment_count"]:
        raise ValueError("V51 development judgment count mismatch")
    summaries = {
        condition: summarize_condition(raw, dataset, condition)
        for condition in config["conditions"]
    }
    comparison = compare(summaries[CONTROL], summaries[CANDIDATE])
    absolute_gate = evaluate_absolute(
        summaries[CANDIDATE], config["candidate_absolute_gates"]
    )
    comparison_gate = evaluate_comparison(
        comparison, config["matched_comparison_gates"]
    )
    passed = absolute_gate["passed"] and comparison_gate["passed"]
    candidate = summaries[CANDIDATE]
    if passed:
        decision = "authorize_fresh_v51_holdout"
        interpretation = (
            "The answer-free event representation passed every preregistered development gate. "
            "It remains a candidate until a separately frozen holdout confirms the effect."
        )
    elif comparison["commitment_correct_count_delta"] > 0 and candidate[
        "false_action_count"
    ]:
        decision = "reject_runtime_preregister_input_trust_boundary"
        interpretation = (
            "The event representation improved target-local semantics but did not eliminate unsafe "
            "execution. Keep the representation as development evidence only and isolate input-data "
            "trust handling in the next preregistered experiment."
        )
    elif comparison["commitment_correct_count_delta"] <= 0:
        decision = "reject_event_map_preregister_state_machine_fallback"
        interpretation = (
            "Making occurrence order observable did not improve the fixed model. The next experiment "
            "must move target-state updates into a deterministic state machine with model fallback."
        )
    else:
        decision = "reject_v51_due_to_regression_or_gate_failure"
        interpretation = (
            "The candidate changed behavior but failed the preregistered safety, regression, or "
            "quality boundary. Retain V48 and do not tune V51 on these consumed examples."
        )
    return {
        "schema": "uruha_target_event_map_development_analysis_v51",
        "evidence_status": raw["evidence_status"],
        "conditions": summaries,
        "matched_comparison": comparison,
        "candidate_absolute_gate": absolute_gate,
        "matched_comparison_gate": comparison_gate,
        "development_gate_passed": passed,
        "decision": decision,
        "interpretation": interpretation,
        "fresh_holdout_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V51 target-event-map development result",
        "",
        "This is a matched comparison on retired development data, not a fresh holdout.",
        "",
        "| condition | parse | commitment | requested P/R | call exact | false actions | median / p95 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, row in analysis["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(row['parse_success_rate'])} | "
            f"{_pct(row['commitment_accuracy'])} ({row['commitment_correct_count']}/61) | "
            f"{_pct(row['requested_commitment_precision'])} / "
            f"{_pct(row['requested_commitment_recall'])} | "
            f"{_pct(row['compiled_call_exact_accuracy'])} "
            f"({row['compiled_call_exact_count']}/48) | "
            f"{row['false_action_count']} | "
            f"{row['median_case_latency_seconds']:.2f}s / "
            f"{row['p95_case_latency_seconds']:.2f}s |"
        )
    comparison = analysis["matched_comparison"]
    lines.extend(
        [
            "",
            f"- Commitment delta: `{comparison['commitment_correct_count_delta']:+d}` targets.",
            f"- Exact-call delta: `{comparison['compiled_call_exact_count_delta']:+d}` cases.",
            f"- False-action delta: `{comparison['false_action_count_delta']:+d}` cases.",
            f"- Semantic fixes/regressions: `{comparison['fixed_semantic_count']}` / "
            f"`{comparison['semantic_regression_count']}`.",
            f"- Call fixes/regressions: `{comparison['fixed_call_count']}` / "
            f"`{comparison['call_regression_count']}`.",
            f"- Development gate passed: `{analysis['development_gate_passed']}`.",
            f"- Decision: `{analysis['decision']}`.",
            f"- Interpretation: {analysis['interpretation']}",
            "- Runtime remains unchanged and physical VRM execution remains disabled.",
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
    analysis = analyze(load(args.raw), load(DATASET_PATH), load(CONFIG_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "development_gate_passed": analysis["development_gate_passed"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
