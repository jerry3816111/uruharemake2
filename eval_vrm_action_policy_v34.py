#!/usr/bin/env python3
"""Apply the V34 action validator to already-observed V33 model calls."""

import argparse
import json
from collections import Counter
from pathlib import Path

from run_rightbrain_qwen35_migration_v33 import score_action_output
from vrm_action_policy_v34 import validate_model_tool_calls


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
RAW_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_raw.json"
DEFAULT_JSON = ROOT / "reports" / "vrm_action_policy_v34_development.json"
DEFAULT_MD = ROOT / "reports" / "vrm_action_policy_v34_development.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _mean(values):
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _summarize(scores, rows):
    no_action = [score for score in scores if score["expected_call_count"] == 0]
    blocked_reasons = Counter(
        reason
        for row in rows
        for blocked in row.get("validation", {}).get("blocked_calls", [])
        for reason in blocked["reasons"]
    )
    return {
        "case_count": len(scores),
        "exact_tool_call_set_and_argument_accuracy": _rate(
            sum(score["exact_match"] for score in scores), len(scores)
        ),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _mean(score["required_action_recall"] for score in scores),
        "false_action_rate": _rate(sum(score["false_action"] for score in scores), len(scores)),
        "negation_violation_count": sum(score["negation_violation"] for score in scores),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in scores), len(scores)
        ),
        "blocked_reason_counts": dict(blocked_reasons),
    }


def evaluate():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset["action_cases"]}
    conditions = sorted({row["condition"] for row in raw["action_rows"]})
    targets = config["action_isolation_development"]["development_targets"]
    condition_reports = {}

    for condition in conditions:
        source_rows = [row for row in raw["action_rows"] if row["condition"] == condition]
        rows = []
        for source in source_rows:
            case = cases[source["case_id"]]
            raw_calls = source["score"]["actual_calls"]
            validation = validate_model_tool_calls(case["user_input"], raw_calls)
            filtered_score = score_action_output(case, validation["accepted_calls"])
            rows.append(
                {
                    "case_id": case["id"],
                    "family": case["family"],
                    "user_input": case["user_input"],
                    "validation": validation,
                    "raw_score": source["score"],
                    "validated_score": filtered_score,
                }
            )

        raw_summary = _summarize([row["raw_score"] for row in rows], rows=[])
        validated_summary = _summarize([row["validated_score"] for row in rows], rows=rows)
        checks = {
            "no_action_specificity": validated_summary["no_action_specificity"]
            >= targets["no_action_specificity_at_least"],
            "negation_violation_count": validated_summary["negation_violation_count"]
            == targets["negation_violation_count"],
            "required_action_recall_delta": (
                validated_summary["required_action_recall"] - raw_summary["required_action_recall"]
                >= targets["required_action_recall_delta_at_least"]
            ),
            "invalid_tool_or_argument_rate": validated_summary["invalid_tool_or_argument_rate"]
            == targets["invalid_tool_or_argument_rate"],
        }
        condition_reports[condition] = {
            "raw": raw_summary,
            "validated": validated_summary,
            "delta": {
                metric: round(validated_summary[metric] - raw_summary[metric], 4)
                for metric in [
                    "exact_tool_call_set_and_argument_accuracy",
                    "no_action_specificity",
                    "required_action_recall",
                    "false_action_rate",
                    "invalid_tool_or_argument_rate",
                ]
            },
            "development_gate": {
                "passed": all(checks.values()),
                "checks": checks,
                "failed_checks": [name for name, passed in checks.items() if not passed],
            },
            "rows": rows,
        }

    all_pass = bool(condition_reports) and all(
        report["development_gate"]["passed"] for report in condition_reports.values()
    )
    return {
        "schema": "uruha_vrm_action_policy_development_v34",
        "evidence_status": "development_only_reuses_observed_v33_cases_and_calls",
        "policy_scope": "The validator can deny or remove model calls but cannot invent a positive call.",
        "conditions": condition_reports,
        "decision": (
            "freeze_policy_and_author_fresh_action_confirmation_holdout"
            if all_pass
            else "revise_policy_before_any_runtime_integration"
        ),
        "runtime_change_authorized": False,
    }


def _markdown(report):
    lines = [
        "# V34 VRM action isolation development result",
        "",
        "> Development evidence only. The 120 V33 cases and model calls were already observed.",
        "",
        "| condition | path | exact | no-action | required recall | false action | negation violations |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for condition, result in report["conditions"].items():
        for label in ("raw", "validated"):
            summary = result[label]
            lines.append(
                f"| {condition} | {label} | "
                f"{_fmt_pct(summary['exact_tool_call_set_and_argument_accuracy'])} | "
                f"{_fmt_pct(summary['no_action_specificity'])} | "
                f"{_fmt_pct(summary['required_action_recall'])} | "
                f"{_fmt_pct(summary['false_action_rate'])} | "
                f"{summary['negation_violation_count']} |"
            )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- `{report['decision']}`",
            "- The validator never creates a positive action; it only enforces authorization and grounding.",
            "- Runtime remains unchanged until a fresh frozen holdout passes.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = evaluate()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "output": str(args.json_output)}, indent=2))


if __name__ == "__main__":
    main()
