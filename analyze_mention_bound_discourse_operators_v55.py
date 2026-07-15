#!/usr/bin/env python3
"""Analyze V55 mention-bound discourse operators on consumed V54 evidence."""

import argparse
import json
from pathlib import Path

from analyze_target_event_map_v51 import compare, summarize_condition
from run_mention_bound_discourse_operators_v55 import CONTROL, DETERMINISTIC, HYBRID


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "mention_bound_discourse_operators_v55_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "mention_bound_discourse_operators_v55_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "mention_bound_discourse_operators_v55_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "mention_bound_discourse_operators_v55_development_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _pct(value):
    return f"{100 * value:.2f}%"


def _gold(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def _pseudo_raw(raw, condition):
    return {
        "judgment_rows": [
            {
                "condition": condition,
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "result": {
                    "parsed": {
                        "parse_success": True,
                        "errors": [],
                        "commitment": row["condition_commitments"][condition],
                    },
                    "response_metrics": {"wall_seconds": 0.0},
                },
            }
            for row in raw["target_rows"]
        ]
    }


def _subset(dataset, predicate):
    cases = [case for case in dataset["cases"] if predicate(case)]
    return {**dataset, "case_count": len(cases), "cases": cases}


def _selective_metrics(raw, dataset):
    gold = _gold(dataset)
    resolved = [row for row in raw["target_rows"] if row["state_machine"]["resolved"]]
    fallback = [row for row in raw["target_rows"] if not row["state_machine"]["resolved"]]
    resolved_correct = sum(
        row["state_machine"]["commitment"]
        == gold[(row["case_id"], row["target_id"])]
        for row in resolved
    )
    fallback_correct = sum(
        row["frozen_v51_commitment"] == gold[(row["case_id"], row["target_id"])]
        for row in fallback
    )
    return {
        "coverage": _rate(len(resolved), len(raw["target_rows"])),
        "resolved_count": len(resolved),
        "resolved_correct_count": resolved_correct,
        "resolved_accuracy": _rate(resolved_correct, len(resolved)),
        "fallback_count": len(fallback),
        "fallback_correct_count": fallback_correct,
        "fallback_accuracy": _rate(fallback_correct, len(fallback)),
    }


def _targeted_results(raw, dataset, targeted):
    gold = _gold(dataset)
    lookup = {
        (row["case_id"], row["target_id"]): row for row in raw["target_rows"]
    }
    rows = []
    for item in targeted:
        key = (item["case_id"], item["target_id"])
        row = lookup[key]
        expected = gold[key]
        before = row["condition_commitments"][CONTROL]
        after = row["condition_commitments"][HYBRID]
        rows.append(
            {
                **item,
                "expected": expected,
                "control": before,
                "candidate": after,
                "fixed": before != expected and after == expected,
                "correct": after == expected,
                "resolution_rule": row["state_machine"]["resolution_rule"],
            }
        )
    return {
        "count": len(rows),
        "correct_count": sum(row["correct"] for row in rows),
        "fixed_count": sum(row["fixed"] for row in rows),
        "rows": rows,
    }


def analyze(raw, dataset, config):
    if not raw.get("completed_at") or raw["target_count"] != 76:
        raise ValueError("V55 development raw report is incomplete")
    if raw["model_calls_made"] != 0 or raw["paid_api_used"]:
        raise ValueError("V55 development unexpectedly used a model or paid API")

    conditions = {
        condition: summarize_condition(_pseudo_raw(raw, condition), dataset, condition)
        for condition in config["conditions"]
    }
    subgroups = {}
    for source_type in ("external_exact", "controlled_authored"):
        subset = _subset(dataset, lambda case, value=source_type: case["source_type"] == value)
        subgroups[source_type] = {
            condition: summarize_condition(_pseudo_raw(raw, condition), subset, condition)
            for condition in config["conditions"]
        }
    selective = _selective_metrics(raw, dataset)
    comparison = compare(conditions[CONTROL], conditions[HYBRID])
    targeted = _targeted_results(raw, dataset, config["targeted_development_failures"])

    gates = config["development_gates"]
    checks = {
        "coverage": selective["coverage"] >= gates["coverage_at_least"],
        "resolved_accuracy": selective["resolved_accuracy"]
        >= gates["resolved_accuracy_at_least"],
        "hybrid_commitment_accuracy": conditions[HYBRID]["commitment_accuracy"]
        >= gates["hybrid_commitment_accuracy_at_least"],
        "requested_precision": conditions[HYBRID]["requested_commitment_precision"]
        == gates["requested_commitment_precision"],
        "requested_recall": conditions[HYBRID]["requested_commitment_recall"]
        == gates["requested_commitment_recall"],
        "compiled_call_exact_accuracy": conditions[HYBRID][
            "compiled_call_exact_accuracy"
        ]
        >= gates["compiled_call_exact_accuracy_at_least"],
        "no_action_specificity": conditions[HYBRID]["no_action_specificity"]
        == gates["no_action_specificity"],
        "false_action_count": conditions[HYBRID]["false_action_count"]
        == gates["false_action_count"],
        "targeted_correct": targeted["correct_count"]
        == gates["targeted_correct_count"],
        "targeted_fixed": targeted["fixed_count"] >= gates["targeted_fixed_count_at_least"],
        "semantic_gain": comparison["commitment_correct_count_delta"]
        >= gates["commitment_correct_count_delta_at_least"],
        "semantic_regressions": comparison["semantic_regression_count"]
        == gates["semantic_regression_count"],
        "call_gain": comparison["compiled_call_exact_count_delta"]
        >= gates["compiled_call_exact_count_delta_at_least"],
        "call_regressions": comparison["call_regression_count"]
        == gates["call_regression_count"],
    }
    passed = all(checks.values())
    if passed:
        decision = "authorize_independent_v55_holdout_and_compiler_repair_design"
        interpretation = (
            "Mention-bound operators fixed the prespecified consumed failures without regression. "
            "This authorizes only a new independent V55 holdout and a separately preregistered "
            "compiler repair; runtime and physical execution remain disabled."
        )
    elif comparison["semantic_regression_count"]:
        decision = "reject_v55_due_to_semantic_regression"
        interpretation = (
            "The structural operators fixed known cases but changed previously correct semantics. "
            "Reject V55 and redesign operator binding under a new preregistration."
        )
    else:
        decision = "reject_v55_due_to_development_gate"
        interpretation = (
            "V55 did not meet its locked coverage, semantic, or execution boundary. Do not tune "
            "it on the consumed V54 holdout."
        )
    return {
        "schema": "uruha_mention_bound_discourse_operators_development_analysis_v55",
        "evidence_status": raw["evidence_status"],
        "conditions": conditions,
        "subgroups": subgroups,
        "selective_metrics": selective,
        "targeted_results": targeted,
        "hybrid_vs_frozen_v54": comparison,
        "development_gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": decision,
        "interpretation": interpretation,
        "fresh_holdout_authorized": passed,
        "compiler_repair_design_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def render_markdown(report):
    lines = [
        "# V55 mention-bound discourse operators development result",
        "",
        "This is a zero-model replay on consumed V54 evidence, not a fresh holdout.",
        "",
        "| condition | commitment | exact calls | false actions |",
        "|---|---:|---:|---:|",
    ]
    for condition, row in report["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(row['commitment_accuracy'])} "
            f"({row['commitment_correct_count']}/{row['target_count']}) | "
            f"{_pct(row['compiled_call_exact_accuracy'])} "
            f"({row['compiled_call_exact_count']}/{row['case_count']}) | "
            f"{row['false_action_count']} |"
        )
    selective = report["selective_metrics"]
    comparison = report["hybrid_vs_frozen_v54"]
    lines.extend(
        [
            "",
            f"- Coverage / resolved accuracy: `{_pct(selective['coverage'])}` / "
            f"`{_pct(selective['resolved_accuracy'])}`.",
            f"- Targeted fixed/correct: `{report['targeted_results']['fixed_count']}` / "
            f"`{report['targeted_results']['correct_count']}` of "
            f"`{report['targeted_results']['count']}`.",
            f"- Commitment / call delta: `{comparison['commitment_correct_count_delta']:+d}` / "
            f"`{comparison['compiled_call_exact_count_delta']:+d}`.",
            f"- Semantic / call regressions: `{comparison['semantic_regression_count']}` / "
            f"`{comparison['call_regression_count']}`.",
            f"- Gate passed: `{report['development_gate']['passed']}`.",
            f"- Decision: `{report['decision']}`.",
            f"- Interpretation: {report['interpretation']}",
            "- No model call, paid API, runtime change, or physical VRM action was used.",
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
                "development_gate_passed": report["development_gate"]["passed"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
