#!/usr/bin/env python3
"""Analyze the V52 matched precise-target-mention development comparison."""

import argparse
import json
from pathlib import Path

from analyze_target_event_map_v51 import (
    _pct,
    compare,
    evaluate_absolute,
    evaluate_comparison,
    summarize_condition,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "precise_target_mentions_v52_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "precise_target_mentions_v52_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "precise_target_mentions_v52_development_analysis.md"
CONTROL = "v51_event_map_control"
CANDIDATE = "precise_target_mentions_candidate"


def analyze(raw, dataset, config):
    if not raw.get("completed_at"):
        raise ValueError("V52 development raw report is incomplete")
    if len(raw["judgment_rows"]) != config["expected_judgment_count"]:
        raise ValueError("V52 development judgment count mismatch")
    if not raw.get("representation_gate", {}).get("passed"):
        raise ValueError("V52 representation gate was not passed before inference")

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
    representation_passed = raw["representation_gate"]["passed"]
    passed = representation_passed and absolute_gate["passed"] and comparison_gate[
        "passed"
    ]

    if passed:
        decision = "authorize_fresh_v52_holdout_construction"
        interpretation = (
            "Separating exact target mentions from broad predicate evidence passed every locked "
            "development gate without encoding a commitment answer. The result authorizes only a "
            "separately frozen external or human-authored holdout."
        )
    elif comparison["semantic_regression_count"] or comparison[
        "call_regression_count"
    ]:
        decision = "reject_v52_due_to_regression"
        interpretation = (
            "The revised representation introduced at least one new error. Retain V48 as the "
            "candidate execution boundary and do not tune V52 on these consumed examples."
        )
    elif comparison["commitment_correct_count_delta"] <= 0 or comparison[
        "compiled_call_exact_count_delta"
    ] <= 0:
        decision = "reject_v52_preregister_explicit_state_machine"
        interpretation = (
            "Precise target mentions did not produce the preregistered matched gain. Further prompt "
            "representation tuning is rejected; the next experiment should make per-target state "
            "updates deterministic and reserve the model for unresolved cases."
        )
    else:
        decision = "reject_v52_due_to_absolute_or_safety_gate"
        interpretation = (
            "The representation changed behavior but failed an absolute quality or safety boundary. "
            "It cannot advance to holdout or runtime."
        )
    return {
        "schema": "uruha_precise_target_mentions_development_analysis_v52",
        "evidence_status": raw["evidence_status"],
        "representation_audit": raw["representation_audit"],
        "representation_gate": raw["representation_gate"],
        "conditions": summaries,
        "matched_comparison": comparison,
        "candidate_absolute_gate": absolute_gate,
        "matched_comparison_gate": comparison_gate,
        "development_gate_passed": passed,
        "decision": decision,
        "interpretation": interpretation,
        "fresh_holdout_construction_authorized": passed,
        "fresh_holdout_claim_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "human_likeness_claim_authorized": False,
    }


def render_markdown(analysis):
    lines = [
        "# V52 precise target-mention development result",
        "",
        "This is a matched comparison on consumed development data, not fresh generalization evidence.",
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
    audit = analysis["representation_audit"]
    comparison = analysis["matched_comparison"]
    lines.extend(
        [
            "",
            f"- Mention coverage/fallback/overlap: "
            f"`{audit['covered_occurrence_count']}/{audit['grounded_occurrence_count']}` / "
            f"`{audit['fallback_occurrence_count']}` / "
            f"`{audit['cross_target_mention_overlap_count']}`.",
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
            "- Runtime and physical VRM execution remain unchanged.",
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
