#!/usr/bin/env python3
"""Analyze V36 frame parsing, deterministic compilation, and matched controls."""

import argparse
import json
import math
import statistics
from pathlib import Path

from run_rightbrain_qwen35_migration_v33 import score_action_output
from vrm_action_policy_v34 import validate_model_tool_calls


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_intent_frame_v36_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_intent_frame_v36_development.json"
SOURCE_RAW_PATH = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_raw.json"
DEFAULT_RAW = ROOT / "reports" / "action_intent_frame_v36_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "action_intent_frame_v36_development_analysis.json"
DEFAULT_MD = ROOT / "reports" / "action_intent_frame_v36_development_analysis.md"


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


def _f1(true_positive, false_positive, false_negative):
    denominator = 2 * true_positive + false_positive + false_negative
    return round(2 * true_positive / denominator, 4) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _action_summary(scores):
    no_action = [score for score in scores if score["expected_call_count"] == 0]
    return {
        "case_count": len(scores),
        "compiled_call_exact_accuracy": _rate(
            sum(score["exact_match"] for score in scores), len(scores)
        ),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _mean(
            score["required_action_recall"] for score in scores
        ),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in scores), len(scores)
        ),
        "negation_violation_count": sum(
            score["negation_violation"] for score in scores
        ),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in scores), len(scores)
        ),
    }


def _candidate_summary(rows):
    action = _action_summary([row["action_score"] for row in rows])
    frame_scores = [row["frame_score"] for row in rows]
    frame_tp = sum(score["frame_true_positive"] for score in frame_scores)
    frame_fp = sum(score["frame_false_positive"] for score in frame_scores)
    frame_fn = sum(score["frame_false_negative"] for score in frame_scores)
    requested_tp = sum(score["requested_true_positive"] for score in frame_scores)
    requested_fp = sum(score["requested_false_positive"] for score in frame_scores)
    requested_fn = sum(score["requested_false_negative"] for score in frame_scores)
    compiled_count = sum(score["compiled_frame_count"] for score in frame_scores)
    compiled_evidence = sum(
        score["compiled_evidence_valid_count"] for score in frame_scores
    )
    matched_count = sum(score["matched_frame_count"] for score in frame_scores)
    matched_evidence = sum(
        score["matched_frame_evidence_supported"] for score in frame_scores
    )
    latencies = [row["response_metrics"]["wall_seconds"] for row in rows]
    family_metrics = {}
    for family in sorted({row["family"] for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        family_metrics[family] = {
            "case_count": len(family_rows),
            "compiled_call_exact_accuracy": _rate(
                sum(row["action_score"]["exact_match"] for row in family_rows),
                len(family_rows),
            ),
            "joint_frame_exact_accuracy": _rate(
                sum(row["frame_score"]["joint_frame_exact"] for row in family_rows),
                len(family_rows),
            ),
        }
    action.update(
        {
            "unsupported_execution_count": sum(
                row["unsupported_execution"] for row in rows
            ),
            "utterance_state_accuracy": _rate(
                sum(score["state_correct"] for score in frame_scores), len(frame_scores)
            ),
            "joint_frame_exact_accuracy": _rate(
                sum(score["joint_frame_exact"] for score in frame_scores),
                len(frame_scores),
            ),
            "requested_frame_precision": _rate(
                requested_tp, requested_tp + requested_fp
            ),
            "requested_frame_recall": _rate(
                requested_tp, requested_tp + requested_fn
            ),
            "commitment_frame_micro_f1": _f1(frame_tp, frame_fp, frame_fn),
            "parse_success_rate": _rate(
                sum(row["parsed_frame"]["parse_success"] for row in rows), len(rows)
            ),
            "compiled_evidence_validity_rate": _rate(
                compiled_evidence, compiled_count
            ),
            "matched_frame_evidence_support_rate": _rate(
                matched_evidence, matched_count
            ),
            "median_latency_seconds": round(statistics.median(latencies), 4),
            "p95_latency_seconds": _percentile(latencies, 0.95),
            "transport_error_count": sum(
                bool(row["prior_transport_errors"]) for row in rows
            ),
            "family_metrics": family_metrics,
        }
    )
    return action


def _at_least(value, target):
    return value is not None and value >= target


def _at_most(value, target):
    return value is not None and value <= target


def _gate(summary, target):
    checks = {
        "compiled_call_exact_accuracy": _at_least(
            summary["compiled_call_exact_accuracy"],
            target["compiled_call_exact_accuracy_at_least"],
        ),
        "no_action_specificity": _at_least(
            summary["no_action_specificity"], target["no_action_specificity_at_least"]
        ),
        "required_action_recall": _at_least(
            summary["required_action_recall"],
            target["required_action_recall_at_least"],
        ),
        "false_action_rate": summary["false_action_rate"]
        == target["false_action_rate"],
        "negation_violation_count": summary["negation_violation_count"]
        == target["negation_violation_count"],
        "unsupported_execution_count": summary["unsupported_execution_count"]
        == target["unsupported_execution_count"],
        "invalid_tool_or_argument_rate": summary["invalid_tool_or_argument_rate"]
        == target["invalid_tool_or_argument_rate"],
        "utterance_state_accuracy": _at_least(
            summary["utterance_state_accuracy"],
            target["utterance_state_accuracy_at_least"],
        ),
        "joint_frame_exact_accuracy": _at_least(
            summary["joint_frame_exact_accuracy"],
            target["joint_frame_exact_accuracy_at_least"],
        ),
        "requested_frame_precision": _at_least(
            summary["requested_frame_precision"],
            target["requested_frame_precision_at_least"],
        ),
        "requested_frame_recall": _at_least(
            summary["requested_frame_recall"],
            target["requested_frame_recall_at_least"],
        ),
        "commitment_frame_micro_f1": _at_least(
            summary["commitment_frame_micro_f1"],
            target["commitment_frame_micro_f1_at_least"],
        ),
        "parse_success_rate": _at_least(
            summary["parse_success_rate"], target["parse_success_rate_at_least"]
        ),
        "compiled_evidence_validity_rate": summary[
            "compiled_evidence_validity_rate"
        ]
        == target["compiled_evidence_validity_rate"],
        "median_latency_seconds": _at_most(
            summary["median_latency_seconds"],
            target["median_latency_seconds_at_most"],
        ),
        "p95_latency_seconds": _at_most(
            summary["p95_latency_seconds"], target["p95_latency_seconds_at_most"]
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def _baseline_summary(dataset, source_raw, condition, lexical=False):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = []
    for row in source_raw["action_rows"]:
        if row["condition"] != condition:
            continue
        case = cases[row["case_id"]]
        calls = row["score"]["actual_calls"]
        if lexical:
            calls = validate_model_tool_calls(case["user_input"], calls)["accepted_calls"]
        scores.append(score_action_output(case, calls))
    if len(scores) != len(cases):
        raise ValueError(f"Incomplete matched baseline: {condition}")
    return _action_summary(scores)


def analyze(raw_path=DEFAULT_RAW):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    source_raw = json.loads(SOURCE_RAW_PATH.read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset["cases"]}

    baselines = {}
    for source in ("qwen2_5_7b", "qwen3_5_9b"):
        baselines[source] = {
            "v34_direct_function_call": _baseline_summary(
                dataset, source_raw, source, lexical=False
            ),
            "v34_lexical_validator": _baseline_summary(
                dataset, source_raw, source, lexical=True
            ),
        }

    candidates = {}
    target = config["development_gates_per_model"]
    for condition in config["model_conditions"]:
        rows = [row for row in raw["rows"] if row["condition"] == condition]
        if len(rows) != len(cases):
            raise ValueError(f"Incomplete V36 condition: {condition}")
        summary = _candidate_summary(rows)
        gate = _gate(summary, target)
        failures = []
        for row in rows:
            if row["action_score"]["exact_match"] and row["frame_score"][
                "joint_frame_exact"
            ]:
                continue
            case = cases[row["case_id"]]
            failures.append(
                {
                    "case_id": case["id"],
                    "family": case["family"],
                    "user_input": case["user_input"],
                    "expected_state": case["expected_state"],
                    "expected_frames": case["expected_frames"],
                    "expected_calls": case["expected_calls"],
                    "parsed_frame": row["parsed_frame"],
                    "accepted_calls": row["compilation"]["accepted_calls"],
                    "action_exact": row["action_score"]["exact_match"],
                    "frame_exact": row["frame_score"]["joint_frame_exact"],
                }
            )
        candidates[condition] = {
            "summary": summary,
            "gate": gate,
            "failures": failures,
        }

    matched_map = {
        "qwen2_5_7b_matched_reference": "qwen2_5_7b",
        "qwen3_5_9b_matched_upper_reference": "qwen3_5_9b",
    }
    matched_comparisons = {}
    for candidate, baseline_name in matched_map.items():
        candidate_summary = candidates[candidate]["summary"]
        baseline = baselines[baseline_name]["v34_direct_function_call"]
        matched_comparisons[candidate] = {
            "baseline": baseline_name,
            "delta": {
                metric: round(candidate_summary[metric] - baseline[metric], 4)
                for metric in (
                    "compiled_call_exact_accuracy",
                    "no_action_specificity",
                    "required_action_recall",
                    "false_action_rate",
                )
            },
        }

    passing = [
        condition
        for condition in config["model_conditions"]
        if candidates[condition]["gate"]["passed"]
    ]
    selected = passing[0] if passing else None
    decision = (
        f"advance_{selected}_to_fresh_v36_holdout"
        if selected
        else "do_not_advance_v36_action_intent_frame"
    )
    return {
        "schema": "uruha_action_intent_frame_development_analysis_v36",
        "evidence_status": "development_only_not_confirmation",
        "source_report": str(Path(raw_path).resolve().relative_to(ROOT)),
        "baselines": baselines,
        "candidates": candidates,
        "matched_comparisons": matched_comparisons,
        "passing_candidates": passing,
        "selected_candidate": selected,
        "development_gate_passed": bool(passing),
        "decision": decision,
        "runtime_change_authorized": False,
        "fresh_holdout_authorized": bool(passing),
    }


def _markdown(analysis):
    lines = [
        "# V36 action-intent frame development result",
        "",
        "> Retired V34 cases are used for development only. Runtime and VRM execution remain disabled.",
        "",
        "## Direct-call baselines",
        "",
        "| model | path | exact | no-action | recall | false action |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for model, paths in analysis["baselines"].items():
        for path, summary in paths.items():
            lines.append(
                f"| {model} | {path} | {_fmt_pct(summary['compiled_call_exact_accuracy'])} | "
                f"{_fmt_pct(summary['no_action_specificity'])} | "
                f"{_fmt_pct(summary['required_action_recall'])} | "
                f"{_fmt_pct(summary['false_action_rate'])} |"
            )
    lines.extend(
        [
            "",
            "## V36 frame parsers",
            "",
            "| condition | call exact | no-action | call recall | state | frame exact | frame F1 | parse | p50 | gate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for condition, result in analysis["candidates"].items():
        summary = result["summary"]
        lines.append(
            f"| {condition} | {_fmt_pct(summary['compiled_call_exact_accuracy'])} | "
            f"{_fmt_pct(summary['no_action_specificity'])} | "
            f"{_fmt_pct(summary['required_action_recall'])} | "
            f"{_fmt_pct(summary['utterance_state_accuracy'])} | "
            f"{_fmt_pct(summary['joint_frame_exact_accuracy'])} | "
            f"{_fmt_pct(summary['commitment_frame_micro_f1'])} | "
            f"{_fmt_pct(summary['parse_success_rate'])} | "
            f"{summary['median_latency_seconds']:.2f}s | "
            f"{'PASS' if result['gate']['passed'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Matched representation deltas",
            "",
            "| V36 condition | same-model V34 baseline | exact delta | no-action delta | recall delta | false-action delta |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for condition, result in analysis["matched_comparisons"].items():
        delta = result["delta"]
        lines.append(
            f"| {condition} | {result['baseline']} | "
            f"{100 * delta['compiled_call_exact_accuracy']:+.1f} pp | "
            f"{100 * delta['no_action_specificity']:+.1f} pp | "
            f"{100 * delta['required_action_recall']:+.1f} pp | "
            f"{100 * delta['false_action_rate']:+.1f} pp |"
        )
    lines.extend(
        [
            "",
            f"- Passing candidates: `{analysis['passing_candidates']}`",
            f"- Selected candidate: `{analysis['selected_candidate']}`",
            f"- Decision: `{analysis['decision']}`",
            "- Passing development permits only a new frozen holdout, never direct runtime integration.",
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
    analysis = analyze(args.raw)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "selected_candidate": analysis["selected_candidate"],
                "passing_candidates": analysis["passing_candidates"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
