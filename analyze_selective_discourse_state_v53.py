#!/usr/bin/env python3
"""Analyze V53 deterministic-only and selective-fallback development results."""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_target_event_map_v51 import compare, summarize_condition


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "selective_discourse_state_v53_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "selective_discourse_state_v53_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "selective_discourse_state_v53_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "selective_discourse_state_v53_development_analysis.md"
CONTROL = "frozen_v51_model_control"
DETERMINISTIC = "deterministic_state_machine_only"
HYBRID = "selective_state_machine_with_v51_fallback"


def _pct(value):
    return f"{100 * value:.2f}%"


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
    gold = {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }
    resolved = [row for row in raw["target_rows"] if row["state_machine"]["resolved"]]
    fallback = [row for row in raw["target_rows"] if not row["state_machine"]["resolved"]]
    resolved_correct = sum(
        row["state_machine"]["commitment"] == gold[(row["case_id"], row["target_id"])]
        for row in resolved
    )
    fallback_correct = sum(
        row["frozen_v51_commitment"] == gold[(row["case_id"], row["target_id"])]
        for row in fallback
    )
    rule_results = {}
    for rule in sorted({row["state_machine"]["resolution_rule"] for row in resolved}):
        rows = [row for row in resolved if row["state_machine"]["resolution_rule"] == rule]
        correct = sum(
            row["state_machine"]["commitment"]
            == gold[(row["case_id"], row["target_id"])]
            for row in rows
        )
        rule_results[rule] = {
            "count": len(rows),
            "correct": correct,
            "accuracy": round(correct / len(rows), 4),
        }
    return {
        "coverage": round(len(resolved) / len(raw["target_rows"]), 4),
        "resolved_count": len(resolved),
        "resolved_correct_count": resolved_correct,
        "resolved_accuracy": round(resolved_correct / len(resolved), 4)
        if resolved
        else 0.0,
        "fallback_count": len(fallback),
        "fallback_correct_count": fallback_correct,
        "fallback_accuracy": round(fallback_correct / len(fallback), 4)
        if fallback
        else 0.0,
        "rule_results": rule_results,
    }


def analyze(raw, dataset, config):
    if not raw.get("completed_at") or raw["target_count"] != 85:
        raise ValueError("V53 development raw report is incomplete")
    if raw["model_calls_made"] != 0 or raw["paid_api_used"]:
        raise ValueError("V53 replay unexpectedly used a model or paid API")
    conditions = {
        condition: summarize_condition(_pseudo_raw(raw, condition), dataset, condition)
        for condition in config["conditions"]
    }
    external_dataset = _subset(
        dataset, lambda case: case["source_type"] == "external_exact"
    )
    controlled_dataset = _subset(
        dataset, lambda case: case["source_type"] == "controlled_authored"
    )
    subgroups = {
        "external_exact": {
            condition: summarize_condition(
                _pseudo_raw(raw, condition), external_dataset, condition
            )
            for condition in config["conditions"]
        },
        "controlled_authored": {
            condition: summarize_condition(
                _pseudo_raw(raw, condition), controlled_dataset, condition
            )
            for condition in config["conditions"]
        },
    }
    selective = _selective_metrics(raw, dataset)
    comparison = compare(conditions[CONTROL], conditions[HYBRID])
    gates = config["development_gates"]
    checks = {
        "coverage": selective["coverage"] >= gates["coverage_at_least"],
        "resolved_accuracy": selective["resolved_accuracy"]
        >= gates["resolved_accuracy_at_least"],
        "hybrid_commitment_accuracy": conditions[HYBRID]["commitment_accuracy"]
        >= gates["hybrid_commitment_accuracy_at_least"],
        "hybrid_call_exact_accuracy": conditions[HYBRID]["compiled_call_exact_accuracy"]
        >= gates["hybrid_call_exact_accuracy_at_least"],
        "hybrid_no_action_specificity": conditions[HYBRID]["no_action_specificity"]
        == gates["hybrid_no_action_specificity"],
        "hybrid_false_action_count": conditions[HYBRID]["false_action_count"]
        == gates["hybrid_false_action_count"],
        "hybrid_negation_violation_count": conditions[HYBRID][
            "negation_violation_count"
        ]
        == gates["hybrid_negation_violation_count"],
        "commitment_gain": comparison["commitment_correct_count_delta"]
        >= gates["commitment_correct_count_delta_at_least"],
        "call_gain": comparison["compiled_call_exact_count_delta"]
        >= gates["compiled_call_exact_count_delta_at_least"],
        "semantic_regressions": comparison["semantic_regression_count"]
        <= gates["semantic_regression_count_at_most"],
        "call_regressions": comparison["call_regression_count"]
        <= gates["call_regression_count_at_most"],
        "external_call_accuracy": subgroups["external_exact"][HYBRID][
            "compiled_call_exact_accuracy"
        ]
        >= gates["external_call_accuracy_at_least"],
        "controlled_call_accuracy": subgroups["controlled_authored"][HYBRID][
            "compiled_call_exact_accuracy"
        ]
        >= gates["controlled_call_accuracy_at_least"],
    }
    passed = all(checks.values())
    if passed:
        decision = "authorize_independent_v53_holdout_construction"
        interpretation = (
            "The explicit state machine improved the consumed development set while preserving its "
            "locked selective-risk and safety gates. This authorizes only construction of a new "
            "independent holdout, not runtime or shadow integration."
        )
    elif conditions[HYBRID]["false_action_count"] > 0:
        decision = "reject_v53_due_to_false_action"
        interpretation = (
            "The selective hybrid still emitted an unsafe false action. Keep V53 out of runtime and "
            "revise the deterministic execution boundary in a separately preregistered version."
        )
    elif comparison["call_regression_count"] > gates["call_regression_count_at_most"]:
        decision = "reject_v53_due_to_call_regression"
        interpretation = (
            "The state machine fixed some cases but introduced too many complete-call regressions. "
            "Do not hide them with aggregate accuracy and do not advance."
        )
    else:
        decision = "reject_v53_due_to_development_gate"
        interpretation = (
            "The architecture did not meet its locked development threshold. It cannot justify the "
            "cost of a new independent holdout or any runtime change."
        )
    return {
        "schema": "uruha_selective_discourse_state_development_analysis_v53",
        "evidence_status": raw["evidence_status"],
        "conditions": conditions,
        "subgroups": subgroups,
        "selective_metrics": selective,
        "hybrid_vs_control": comparison,
        "development_gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": decision,
        "interpretation": interpretation,
        "fresh_holdout_construction_authorized": passed,
        "fresh_generalization_claim_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "human_likeness_claim_authorized": False,
    }


def render_markdown(report):
    lines = [
        "# V53 selective discourse-state development result",
        "",
        "This reuses the consumed V52 holdout and frozen V51 predictions. It is development evidence only.",
        "",
        "| condition | commitment | exact calls | false actions | no-action specificity |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, row in report["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(row['commitment_accuracy'])} "
            f"({row['commitment_correct_count']}/{row['target_count']}) | "
            f"{_pct(row['compiled_call_exact_accuracy'])} "
            f"({row['compiled_call_exact_count']}/{row['case_count']}) | "
            f"{row['false_action_count']} | {_pct(row['no_action_specificity'])} |"
        )
    selective = report["selective_metrics"]
    comparison = report["hybrid_vs_control"]
    lines.extend(
        [
            "",
            f"- Deterministic coverage: `{_pct(selective['coverage'])}` "
            f"({selective['resolved_count']}/85).",
            f"- Accuracy on resolved targets: `{_pct(selective['resolved_accuracy'])}`.",
            f"- Hybrid commitment/call delta vs frozen V51: "
            f"`{comparison['commitment_correct_count_delta']:+d}` / "
            f"`{comparison['compiled_call_exact_count_delta']:+d}`.",
            f"- Semantic/call regressions: `{comparison['semantic_regression_count']}` / "
            f"`{comparison['call_regression_count']}`.",
            f"- Development gate passed: `{report['development_gate']['passed']}`.",
            f"- Decision: `{report['decision']}`.",
            f"- Interpretation: {report['interpretation']}",
            "- No model was called during V53 replay; runtime and physical VRM execution remain unchanged.",
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
