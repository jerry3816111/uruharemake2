#!/usr/bin/env python3
"""Analyze the frozen V34 RightBrain and VRM confirmation run."""

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from run_rightbrain_4b_guarded_retry_v34_1 import _select_attempt
from run_rightbrain_qwen35_migration_v33 import score_action_output
from vrm_action_policy_v34 import validate_model_tool_calls


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_confirmation_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
POLICY_PATH = ROOT / "vrm_action_policy_v34.py"
DEFAULT_RAW = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_raw.json"
DEFAULT_JSON = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_analysis.json"
DEFAULT_MD = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _mean(values):
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else None


def _percentile(values, quantile):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    index = max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))
    return round(values[index], 4)


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _rightbrain_summary(rows, *, latency_field="response_metrics"):
    scores = [row["score"] for row in rows]
    semantic_hits = sum(group["hit"] for score in scores for group in score["semantic_groups"])
    semantic_total = sum(len(score["semantic_groups"]) for score in scores)
    if latency_field == "total_wall_seconds":
        wall = [row["total_wall_seconds"] for row in rows]
    else:
        wall = [row["response_metrics"]["wall_seconds"] for row in rows]
    by_category = {}
    for category in sorted({row["category"] for row in rows}):
        category_rows = [row for row in rows if row["category"] == category]
        by_category[category] = {
            "row_count": len(category_rows),
            "semantic_contract_pass_rate": _rate(
                sum(row["score"]["semantic_contract_pass"] for row in category_rows),
                len(category_rows),
            ),
            "raw_surface_gate_pass_rate": _rate(
                sum(row["score"]["current_gate_raw_pass"] for row in category_rows),
                len(category_rows),
            ),
        }
    return {
        "row_count": len(rows),
        "semantic_contract_pass_rate": _rate(
            sum(score["semantic_contract_pass"] for score in scores), len(scores)
        ),
        "semantic_group_recall": _rate(semantic_hits, semantic_total),
        "raw_surface_gate_pass_rate": _rate(
            sum(score["current_gate_raw_pass"] for score in scores), len(scores)
        ),
        "hard_surface_failure_rate": _rate(
            sum(score["hard_surface_failure"] for score in scores), len(scores)
        ),
        "polite_or_service_register_rate": _rate(
            sum(score["polite_or_service_register"] for score in scores), len(scores)
        ),
        "private_memory_intrusion_count": sum(
            score["private_memory_intrusion"] for score in scores
        ),
        "latency_median_seconds": round(statistics.median(wall), 4),
        "latency_p95_seconds": _percentile(wall, 0.95),
        "category_metrics": by_category,
    }


def _guarded_rows(raw):
    first_rows = [
        row
        for row in raw["rightbrain_first_rows"]
        if row["condition"] == "qwen3_5_4b_single_ablation"
    ]
    retry_map = {
        (row["case_id"], row["seed"]): row for row in raw["rightbrain_retry_rows"]
    }
    rows = []
    for first in first_rows:
        retry = retry_map.get((first["case_id"], first["seed"]))
        selected_source, selected = _select_attempt(first, retry)
        rows.append(
            {
                "condition": "qwen3_5_4b_guarded_candidate",
                "case_id": first["case_id"],
                "category": first["category"],
                "seed": first["seed"],
                "raw_reply": selected["raw_reply"],
                "score": selected["score"],
                "selected_source": selected_source,
                "first_passed": first["score"]["current_gate_raw_pass"],
                "retry_present": retry is not None,
                "retry_passed": retry["score"]["current_gate_raw_pass"] if retry else None,
                "total_wall_seconds": round(
                    first["response_metrics"]["wall_seconds"]
                    + (retry["response_metrics"]["wall_seconds"] if retry else 0.0),
                    6,
                ),
            }
        )
    return rows


def _paired_binary(left_rows, right_rows, field):
    left = {(row["case_id"], row["seed"]): bool(row["score"][field]) for row in left_rows}
    right = {(row["case_id"], row["seed"]): bool(row["score"][field]) for row in right_rows}
    if set(left) != set(right):
        raise ValueError("Paired RightBrain keys differ")
    left_only = sum(left[key] and not right[key] for key in left)
    right_only = sum(right[key] and not left[key] for key in left)
    both = sum(left[key] and right[key] for key in left)
    neither = len(left) - left_only - right_only - both
    return {
        "left_only": left_only,
        "right_only": right_only,
        "both": both,
        "neither": neither,
    }


def _action_summary(scores, rows):
    no_action = [score for score in scores if score["expected_call_count"] == 0]
    family_metrics = {}
    for family in sorted({row["family"] for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        family_metrics[family] = {
            "case_count": len(family_rows),
            "exact_accuracy": _rate(
                sum(row["score"]["exact_match"] for row in family_rows), len(family_rows)
            ),
        }
    return {
        "case_count": len(scores),
        "exact_accuracy": _rate(sum(score["exact_match"] for score in scores), len(scores)),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _mean(score["required_action_recall"] for score in scores),
        "false_action_rate": _rate(sum(score["false_action"] for score in scores), len(scores)),
        "negation_violation_count": sum(score["negation_violation"] for score in scores),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in scores), len(scores)
        ),
        "family_metrics": family_metrics,
    }


def _analyze_actions(config, dataset, raw):
    cases = {case["id"]: case for case in dataset["action_cases"]}
    conditions = {}
    target = config["action_confirmation_gate_per_model"]
    for condition in config["action_conditions"]:
        source_rows = [row for row in raw["action_rows"] if row["condition"] == condition]
        if len(source_rows) != len(cases):
            raise ValueError(f"Incomplete action condition {condition}")
        raw_rows = []
        validated_rows = []
        failures = []
        for source in source_rows:
            case = cases[source["case_id"]]
            raw_rows.append({**source, "score": source["score"]})
            validation = validate_model_tool_calls(
                case["user_input"], source["score"]["actual_calls"]
            )
            score = score_action_output(case, validation["accepted_calls"])
            validated = {**source, "score": score, "validation": validation}
            validated_rows.append(validated)
            if not score["exact_match"]:
                failures.append(
                    {
                        "case_id": case["id"],
                        "family": case["family"],
                        "user_input": case["user_input"],
                        "expected_calls": case["expected_calls"],
                        "raw_calls": source["score"]["actual_calls"],
                        "accepted_calls": validation["accepted_calls"],
                        "policy": validation["policy"],
                    }
                )
        raw_summary = _action_summary([row["score"] for row in raw_rows], raw_rows)
        validated_summary = _action_summary(
            [row["score"] for row in validated_rows], validated_rows
        )
        checks = {
            "validated_exact_accuracy": validated_summary["exact_accuracy"]
            >= target["validated_exact_accuracy_at_least"],
            "validated_no_action_specificity": validated_summary["no_action_specificity"]
            >= target["validated_no_action_specificity_at_least"],
            "validated_false_action_rate": validated_summary["false_action_rate"]
            <= target["validated_false_action_rate_at_most"],
            "validated_negation_violation_count": validated_summary["negation_violation_count"]
            == target["validated_negation_violation_count"],
            "validated_invalid_tool_or_argument_rate": validated_summary[
                "invalid_tool_or_argument_rate"
            ]
            == target["validated_invalid_tool_or_argument_rate"],
            "required_action_recall_delta": (
                validated_summary["required_action_recall"] - raw_summary["required_action_recall"]
                >= target["required_action_recall_delta_vs_raw_at_least"]
            ),
        }
        conditions[condition] = {
            "raw": raw_summary,
            "validated": validated_summary,
            "delta": {
                key: round(validated_summary[key] - raw_summary[key], 4)
                for key in [
                    "exact_accuracy",
                    "no_action_specificity",
                    "required_action_recall",
                    "false_action_rate",
                    "invalid_tool_or_argument_rate",
                ]
            },
            "gate": {
                "passed": all(checks.values()),
                "checks": checks,
                "failed_checks": [name for name, passed in checks.items() if not passed],
            },
            "failures": failures,
        }
    passed = all(result["gate"]["passed"] for result in conditions.values())
    return {
        "conditions": conditions,
        "gate_passed_for_all_models": passed,
        "decision": (
            "authorize_environment_disabled_runtime_validator_integration"
            if passed
            else "do_not_integrate_action_validator_from_v34"
        ),
    }


def analyze(raw_path=DEFAULT_RAW):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    if raw.get("completed_at") is None:
        raise ValueError("V34 confirmation run is incomplete")
    if hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest() != config[
        "known_development_results"
    ]["action_validator"]["policy_sha256"]:
        raise ValueError("Frozen V34 action policy changed before confirmation analysis")

    expected_rows = len(dataset["rightbrain_cases"]) * len(
        config["rightbrain_generation"]["seeds"]
    )
    rightbrain_rows = {}
    rightbrain_summaries = {}
    for condition in BASE_CONDITIONS:
        rows = [row for row in raw["rightbrain_first_rows"] if row["condition"] == condition]
        if len(rows) != expected_rows:
            raise ValueError(f"Incomplete RightBrain condition {condition}: {len(rows)}")
        rightbrain_rows[condition] = rows
        rightbrain_summaries[condition] = _rightbrain_summary(rows)
    guarded = _guarded_rows(raw)
    if len(guarded) != expected_rows:
        raise ValueError("Incomplete guarded 4B rows")
    rightbrain_rows["qwen3_5_4b_guarded_candidate"] = guarded
    guarded_summary = _rightbrain_summary(guarded, latency_field="total_wall_seconds")
    guarded_summary["retry_count"] = sum(row["retry_present"] for row in guarded)
    guarded_summary["retry_rate"] = _rate(guarded_summary["retry_count"], len(guarded))
    guarded_summary["retry_recovery_rate"] = _rate(
        sum(row["retry_present"] and row["retry_passed"] for row in guarded),
        guarded_summary["retry_count"],
    )
    rightbrain_summaries["qwen3_5_4b_guarded_candidate"] = guarded_summary

    single = rightbrain_summaries["qwen3_5_4b_single_ablation"]
    upper = rightbrain_summaries["qwen3_5_9b_single_upper_reference"]
    gate = config["rightbrain_confirmation_gate"]
    checks = {
        "guarded_semantic_contract_pass_rate": guarded_summary["semantic_contract_pass_rate"]
        >= gate["guarded_semantic_contract_pass_rate_at_least"],
        "guarded_raw_surface_gate_pass_rate": guarded_summary["raw_surface_gate_pass_rate"]
        >= gate["guarded_raw_surface_gate_pass_rate_at_least"],
        "guarded_private_memory_intrusion_count": guarded_summary[
            "private_memory_intrusion_count"
        ]
        == gate["guarded_private_memory_intrusion_count"],
        "guarded_retry_rate": guarded_summary["retry_rate"] <= gate["guarded_retry_rate_at_most"],
        "guarded_total_latency_median_seconds": guarded_summary["latency_median_seconds"]
        <= gate["guarded_total_latency_median_seconds_at_most"],
        "guarded_total_latency_p95_seconds": guarded_summary["latency_p95_seconds"]
        <= gate["guarded_total_latency_p95_seconds_at_most"],
        "guarded_semantic_contract_delta_vs_9b": (
            guarded_summary["semantic_contract_pass_rate"] - upper["semantic_contract_pass_rate"]
            >= gate["guarded_semantic_contract_delta_vs_9b_at_least"]
        ),
        "guarded_median_latency_ratio_vs_9b": (
            guarded_summary["latency_median_seconds"] / upper["latency_median_seconds"]
            <= gate["guarded_median_latency_ratio_vs_9b_at_most"]
        ),
        "guarded_semantic_contract_delta_vs_4b_single": (
            guarded_summary["semantic_contract_pass_rate"] - single["semantic_contract_pass_rate"]
            >= gate["guarded_semantic_contract_delta_vs_4b_single_at_least"]
        ),
        "guarded_raw_gate_delta_vs_4b_single": (
            guarded_summary["raw_surface_gate_pass_rate"] - single["raw_surface_gate_pass_rate"]
            >= gate["guarded_raw_gate_delta_vs_4b_single_at_least"]
        ),
    }
    rightbrain_passed = all(checks.values())
    rightbrain_failures = [
        {
            "case_id": row["case_id"],
            "category": row["category"],
            "seed": row["seed"],
            "selected_source": row["selected_source"],
            "reply": row["raw_reply"],
            "reasons": row["score"]["current_gate_rejection_reasons"],
        }
        for row in guarded
        if not row["score"]["current_gate_raw_pass"]
    ]
    rightbrain = {
        "condition_summaries": rightbrain_summaries,
        "guarded_vs_single_semantic_pairs": _paired_binary(
            rightbrain_rows["qwen3_5_4b_single_ablation"], guarded, "semantic_contract_pass"
        ),
        "guarded_vs_9b_semantic_pairs": _paired_binary(
            rightbrain_rows["qwen3_5_9b_single_upper_reference"], guarded, "semantic_contract_pass"
        ),
        "gate": {
            "passed": rightbrain_passed,
            "checks": checks,
            "failed_checks": [name for name, passed in checks.items() if not passed],
        },
        "failures": rightbrain_failures,
        "decision": (
            "authorize_opt_in_4b_guarded_shadow_runtime"
            if rightbrain_passed
            else "do_not_integrate_4b_guarded_rightbrain_from_v34"
        ),
    }
    actions = _analyze_actions(config, dataset, raw)
    return {
        "schema": "uruha_rightbrain_role_specialization_confirmation_analysis_v34",
        "evidence_status": "fresh_frozen_confirmation",
        "source_dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
        "rightbrain": rightbrain,
        "actions": actions,
        "authorizations": {
            "rightbrain_opt_in_shadow_runtime": rightbrain_passed,
            "environment_disabled_action_validator_integration": actions[
                "gate_passed_for_all_models"
            ],
            "production_rightbrain_replacement": False,
            "persona_adapter_training": False,
            "human_likeness_claim": False,
        },
    }


BASE_CONDITIONS = (
    "qwen2_5_7b_single_reference",
    "qwen3_5_9b_single_upper_reference",
    "qwen3_5_4b_single_ablation",
)


def _markdown(report):
    lines = [
        "# V34 fresh role-specialization confirmation",
        "",
        "## RightBrain",
        "",
        "| condition | semantic contract | raw gate | private leaks | p50 | p95 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition, summary in report["rightbrain"]["condition_summaries"].items():
        lines.append(
            f"| {condition} | {_fmt_pct(summary['semantic_contract_pass_rate'])} | "
            f"{_fmt_pct(summary['raw_surface_gate_pass_rate'])} | "
            f"{summary['private_memory_intrusion_count']} | "
            f"{summary['latency_median_seconds']:.2f}s | {summary['latency_p95_seconds']:.2f}s |"
        )
    lines.extend(
        [
            "",
            f"- RightBrain gate: {'PASS' if report['rightbrain']['gate']['passed'] else 'FAIL'}",
            f"- RightBrain decision: `{report['rightbrain']['decision']}`",
            "",
            "## VRM action validation",
            "",
            "| condition | path | exact | no-action | recall | false action |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for condition, result in report["actions"]["conditions"].items():
        for path in ("raw", "validated"):
            summary = result[path]
            lines.append(
                f"| {condition} | {path} | {_fmt_pct(summary['exact_accuracy'])} | "
                f"{_fmt_pct(summary['no_action_specificity'])} | "
                f"{_fmt_pct(summary['required_action_recall'])} | "
                f"{_fmt_pct(summary['false_action_rate'])} |"
            )
    lines.extend(
        [
            "",
            f"- Action gate: {'PASS' if report['actions']['gate_passed_for_all_models'] else 'FAIL'}",
            f"- Action decision: `{report['actions']['decision']}`",
            "",
            "No production replacement, persona claim, or human-likeness claim is authorized by this test.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = analyze(args.raw)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "rightbrain_decision": report["rightbrain"]["decision"],
                "action_decision": report["actions"]["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
