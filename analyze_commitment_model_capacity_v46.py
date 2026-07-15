#!/usr/bin/env python3
"""Analyze the V46 local-model capacity development sweep."""

import argparse
import json
from pathlib import Path

from analyze_discourse_state_perception_v45_holdout import summarize_condition


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "commitment_model_capacity_v46_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
AUDIT_PATH = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.json"
V45_ANALYSIS_PATH = ROOT / "reports" / "discourse_state_perception_v45_holdout_analysis.json"
DEFAULT_RAW = ROOT / "reports" / "commitment_model_capacity_v46_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "commitment_model_capacity_v46_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "commitment_model_capacity_v46_development_analysis.md"


def evaluate_model_eligibility(summary, gates):
    checks = {
        "classifier_parse_success_rate": summary["classifier_parse_success_rate"]
        >= gates["classifier_parse_success_rate_at_least"],
        "commitment_accuracy": summary["commitment_accuracy"]
        >= gates["commitment_accuracy_at_least"],
        "requested_commitment_precision": summary["requested_commitment_precision"]
        == gates["requested_commitment_precision"],
        "requested_commitment_recall": summary["requested_commitment_recall"]
        >= gates["requested_commitment_recall_at_least"],
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


def select_model(summaries, config):
    models = {row["condition"]: row for row in config["model_conditions"]}
    eligibility = {
        condition: evaluate_model_eligibility(
            summary, config["eligibility_gates"]
        )
        for condition, summary in summaries.items()
    }
    eligible = [name for name, gate in eligibility.items() if gate["passed"]]
    if not eligible:
        return {
            "selected_condition": None,
            "eligible_conditions": [],
            "near_best_conditions": [],
            "eligibility": eligibility,
            "decision": "reject_model_capacity_only_hypothesis",
            "architecture_decomposition_development_authorized": True,
            "fresh_v46_holdout_authorized": False,
        }
    best_correct = max(summaries[name]["commitment_correct_count"] for name in eligible)
    near_best = [
        name
        for name in eligible
        if summaries[name]["commitment_correct_count"] >= best_correct - 1
    ]
    selected = min(
        near_best,
        key=lambda name: (
            summaries[name]["median_case_latency_seconds"],
            models[name]["blob_bytes"],
            name,
        ),
    )
    return {
        "selected_condition": selected,
        "eligible_conditions": eligible,
        "near_best_conditions": near_best,
        "best_eligible_commitment_correct_count": best_correct,
        "eligibility": eligibility,
        "decision": "authorize_selected_model_for_fresh_v46_holdout",
        "architecture_decomposition_development_authorized": False,
        "fresh_v46_holdout_authorized": True,
    }


def _reference_deltas(summaries, reference_name):
    reference = summaries[reference_name]
    return {
        name: {
            "commitment_correct_count_delta": row["commitment_correct_count"]
            - reference["commitment_correct_count"],
            "compiled_call_exact_count_delta": row["compiled_call_exact_count"]
            - reference["compiled_call_exact_count"],
            "median_latency_seconds_delta": round(
                row["median_case_latency_seconds"]
                - reference["median_case_latency_seconds"],
                4,
            ),
        }
        for name, row in summaries.items()
    }


def analyze(raw, dataset, audit, config, v45_analysis):
    if not raw.get("completed_at"):
        raise ValueError("V46 development report is incomplete")
    if len(raw["judgment_rows"]) != config["expected_judgment_count"]:
        raise ValueError("V46 development judgment count mismatch")
    conditions = [row["condition"] for row in config["model_conditions"]]
    summaries = {
        condition: summarize_condition(
            raw,
            dataset,
            audit,
            condition,
            config["taxonomy_boundary_tags"],
        )
        for condition in conditions
    }
    selection = select_model(summaries, config)
    reference_name = "qwen35_4b_reference"
    old_reference = v45_analysis["conditions"]["v45_discourse_candidate"]
    new_reference = summaries[reference_name]
    reference_reproduction = {
        "old_seed": 20260745,
        "new_seed": config["fixed_generation"]["seed"],
        "old_commitment_correct_count": old_reference["commitment_correct_count"],
        "new_commitment_correct_count": new_reference["commitment_correct_count"],
        "old_compiled_call_exact_count": old_reference["compiled_call_exact_count"],
        "new_compiled_call_exact_count": new_reference["compiled_call_exact_count"],
        "exact_semantic_reproduction": old_reference["target_predictions"]
        == new_reference["target_predictions"],
    }
    selected = selection["selected_condition"]
    if selected is None:
        interpretation = (
            "No installed model satisfied the fixed safety and semantic contract. "
            "Model capacity alone is not an adequate correction; the next experiment must split "
            "candidate grounding, deterministic scope perception, and uncertain semantic judgment."
        )
    elif selected.startswith("qwen35_0_8b") or selected.startswith("qwen35_2b"):
        interpretation = (
            "A smaller model met the same narrow contract within one correct target of the best "
            "eligible model. This supports task-capacity matching for development, not runtime use."
        )
    elif selected == "qwen25_7b_historical":
        interpretation = (
            "The historical model family was selected. The result concerns operational instruction "
            "following and cannot be attributed to parameter count alone."
        )
    else:
        interpretation = (
            "A larger Qwen3.5 model was selected, indicating that this fixed classifier currently "
            "benefits from capacity, subject to a fresh holdout and local latency constraints."
        )
    return {
        "schema": "uruha_commitment_model_capacity_development_analysis_v46",
        "evidence_status": raw["evidence_status"],
        "conditions": summaries,
        "deltas_vs_qwen35_4b_reference": _reference_deltas(summaries, reference_name),
        "qwen35_4b_reference_reproduction": reference_reproduction,
        "selection": selection,
        "interpretation": interpretation,
        "development_only": True,
        "fresh_holdout_claim_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis, config):
    model_meta = {row["condition"]: row for row in config["model_conditions"]}
    lines = [
        "# V46 local model-capacity development result",
        "",
        "This uses the consumed V45 holdout as retired development data. It is not a new holdout result.",
        "",
        "| model | size | parse | commitment | requested P/R | call exact | false action | extra requested | median / p95 | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in config["model_conditions"]:
        name = model["condition"]
        row = analysis["conditions"][name]
        gate = analysis["selection"]["eligibility"][name]
        lines.append(
            f"| {name} | {model_meta[name]['parameter_size']} | "
            f"{_pct(row['classifier_parse_success_rate'])} | "
            f"{_pct(row['commitment_accuracy'])} ({row['commitment_correct_count']}/61) | "
            f"{_pct(row['requested_commitment_precision'])} / {_pct(row['requested_commitment_recall'])} | "
            f"{_pct(row['compiled_call_exact_accuracy'])} ({row['compiled_call_exact_count']}/48) | "
            f"{_pct(row['false_action_rate'])} | {row['extra_candidate_requested_count']} | "
            f"{row['median_case_latency_seconds']:.2f}s / {row['p95_case_latency_seconds']:.2f}s | "
            f"{gate['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Selected model: `{analysis['selection']['selected_condition']}`",
            f"- Decision: `{analysis['selection']['decision']}`",
            f"- Interpretation: {analysis['interpretation']}",
            "- Runtime remains unchanged; physical VRM execution remains disabled.",
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
    analysis = analyze(
        load(args.raw), load(DATASET_PATH), load(AUDIT_PATH), config, load(V45_ANALYSIS_PATH)
    )
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
