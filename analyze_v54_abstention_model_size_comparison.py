#!/usr/bin/env python3
"""Analyze local model size on the frozen V54 abstention subset."""

import argparse
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "v54_abstention_model_size_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "v54_abstention_model_size_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "v54_abstention_model_size_raw.json"
DEFAULT_JSON = ROOT / "reports" / "v54_abstention_model_size_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "v54_abstention_model_size_analysis.md"
CONTROL = "qwen35_4b_frozen_control"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, percentile):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 4)


def _exact_mcnemar_p(regressions, fixes):
    discordant = regressions + fixes
    if not discordant:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(regressions, fixes) + 1)
    ) / (2**discordant)
    return round(min(1.0, 2 * tail), 6)


def _summarize(raw, dataset, condition):
    gold = {
        (item["case_id"], item["target_id"]): item["expected_commitment"]
        for item in dataset["items"]
    }
    rows = [row for row in raw["judgment_rows"] if row["condition"] == condition]
    predictions = []
    parse_success = 0
    correct = 0
    requested_tp = requested_fp = requested_fn = 0
    latencies = []
    for row in rows:
        parsed = row["result"]["parsed"]
        valid = bool(parsed.get("parse_success"))
        predicted = parsed.get("commitment") if valid else None
        expected = gold[(row["case_id"], row["target_id"])]
        is_correct = valid and predicted == expected
        expected_requested = expected == "requested"
        predicted_requested = predicted == "requested"
        parse_success += int(valid)
        correct += int(is_correct)
        requested_tp += int(expected_requested and predicted_requested)
        requested_fp += int(not expected_requested and predicted_requested)
        requested_fn += int(expected_requested and not predicted_requested)
        latencies.append(row["result"]["response_metrics"]["wall_seconds"])
        predictions.append(
            {
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "expected_commitment": expected,
                "predicted_commitment": predicted,
                "parse_success": valid,
                "correct": is_correct,
            }
        )
    return {
        "item_count": len(rows),
        "parse_success_count": parse_success,
        "parse_success_rate": _rate(parse_success, len(rows)),
        "correct_count": correct,
        "accuracy": _rate(correct, len(rows)),
        "requested_true_positive": requested_tp,
        "requested_false_positive": requested_fp,
        "requested_false_negative": requested_fn,
        "requested_precision": _rate(requested_tp, requested_tp + requested_fp),
        "requested_recall": _rate(requested_tp, requested_tp + requested_fn),
        "median_latency_seconds": round(statistics.median(latencies), 4),
        "p95_latency_seconds": _percentile(latencies, 0.95),
        "predictions": predictions,
    }


def _compare(control, candidate):
    before = {
        (row["case_id"], row["target_id"]): row for row in control["predictions"]
    }
    after = {
        (row["case_id"], row["target_id"]): row for row in candidate["predictions"]
    }
    fixes = []
    regressions = []
    for key in sorted(before):
        detail = {
            "case_id": key[0],
            "target_id": key[1],
            "expected_commitment": before[key]["expected_commitment"],
            "control": before[key]["predicted_commitment"],
            "candidate": after[key]["predicted_commitment"],
        }
        if not before[key]["correct"] and after[key]["correct"]:
            fixes.append(detail)
        if before[key]["correct"] and not after[key]["correct"]:
            regressions.append(detail)
    return {
        "correct_count_delta": candidate["correct_count"] - control["correct_count"],
        "fixed_count": len(fixes),
        "fixed": fixes,
        "regression_count": len(regressions),
        "regressions": regressions,
        "exact_mcnemar_p": _exact_mcnemar_p(len(regressions), len(fixes)),
    }


def analyze(raw, dataset, config):
    if not raw.get("completed_at") or len(raw["judgment_rows"]) != 40:
        raise ValueError("V54 model-size raw report is incomplete")
    if raw.get("new_model_calls_made") != 30 or raw["paid_api_used"]:
        raise ValueError("V54 model-size model-call accounting mismatch")

    summaries = {
        condition: _summarize(raw, dataset, condition)
        for condition in config["condition_order"]
    }
    comparisons = {
        condition: _compare(summaries[CONTROL], summaries[condition])
        for condition in config["condition_order"]
        if condition != CONTROL
    }
    gates = config["candidate_gates"]
    candidate_gates = {}
    for condition, comparison in comparisons.items():
        summary = summaries[condition]
        checks = {
            "parse_success": summary["parse_success_rate"]
            == gates["parse_success_rate"],
            "accuracy": summary["accuracy"] >= gates["accuracy_at_least"],
            "requested_false_positive": summary["requested_false_positive"]
            == gates["requested_false_positive_count"],
            "fixes": comparison["fixed_count"] >= gates["fixed_count_at_least"],
            "regressions": comparison["regression_count"]
            <= gates["regression_count_at_most"],
        }
        candidate_gates[condition] = {
            "passed": all(checks.values()),
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        }

    passing = [
        condition
        for condition in config["smallest_first_candidate_order"]
        if candidate_gates.get(condition, {}).get("passed")
    ]
    selected = passing[0] if passing else None
    smaller_passes = [
        condition
        for condition in passing
        if config["model_conditions"][condition]["parameter_rank"] < 4.7
    ]
    if smaller_passes:
        decision = "authorize_fresh_fallback_holdout_for_smallest_passing_model"
        interpretation = (
            "A smaller local model passed every locked diagnostic gate on the consumed frozen "
            "abstentions. This supports, but does not prove, that a narrower fallback can be "
            "better matched to this role. Only a new larger fallback holdout is authorized."
        )
    elif selected == "qwen35_9b":
        decision = "reject_smaller_is_better_support_9b_upper_control"
        interpretation = (
            "Only the 9B upper control passed. The hypothesis that a smaller model better fits "
            "this fallback role is not supported by this diagnostic."
        )
    else:
        decision = "reject_model_size_substitution_for_v54_fallback"
        interpretation = (
            "No alternative model met the locked accuracy, false-request, fix, and zero-regression "
            "boundary. Keep model size out of the next architecture change."
        )

    ranking = sorted(
        config["condition_order"],
        key=lambda condition: (
            -summaries[condition]["correct_count"],
            summaries[condition]["requested_false_positive"],
            config["model_conditions"][condition]["parameter_rank"],
        ),
    )
    return {
        "schema": "uruha_v54_abstention_model_size_analysis",
        "evidence_status": raw["evidence_status"],
        "scope_warning": (
            "This is a diagnostic on 10 consumed V54 abstentions, not an independent model "
            "benchmark, right-brain evaluation, or full-system result."
        ),
        "conditions": summaries,
        "comparisons_vs_frozen_4b": comparisons,
        "candidate_gates": candidate_gates,
        "ranking": ranking,
        "selected_candidate": selected,
        "decision": decision,
        "interpretation": interpretation,
        "structural_v54_errors_remaining": 4,
        "perfect_fallback_full_v54_ceiling": "72/76 (94.74%)",
        "fallback_replacement_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def render_markdown(report):
    lines = [
        "# V54 abstention model-size diagnostic",
        "",
        report["scope_warning"],
        "",
        "| model condition | correct | requested false positives | median / p95 | gate |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, row in report["conditions"].items():
        gate = report["candidate_gates"].get(condition)
        lines.append(
            f"| {condition} | {row['correct_count']}/10 ({100 * row['accuracy']:.1f}%) | "
            f"{row['requested_false_positive']} | {row['median_latency_seconds']:.2f}s / "
            f"{row['p95_latency_seconds']:.2f}s | "
            f"{'control' if gate is None else gate['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Selected candidate: `{report['selected_candidate']}`.",
            f"- Decision: `{report['decision']}`.",
            f"- Interpretation: {report['interpretation']}",
            f"- Even a perfect fallback leaves four structural V54 errors; full-set ceiling: "
            f"`{report['perfect_fallback_full_v54_ceiling']}`.",
            "- No paid API, runtime replacement, shadow actuation, or physical VRM action was used.",
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
                "selected_candidate": report["selected_candidate"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
