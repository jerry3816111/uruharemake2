#!/usr/bin/env python3
"""Analyze the frozen staged answer-span local-model capacity screen."""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_answer_bearing_memory_span_v1_development import (
    file_sha256,
    percentile,
    rate,
    raw_span_grounding,
)
from run_answer_bearing_memory_span_model_capacity_v1 import (
    DEFAULT_METADATA,
    DEFAULT_RAW,
    PREREG_PATH,
    ROOT,
    load_json,
    phase_1_summary,
)


DEFAULT_JSON = ROOT / "reports/answer_bearing_memory_span_model_capacity_v1.json"
DEFAULT_MD = ROOT / "reports/answer_bearing_memory_span_model_capacity_v1.md"


def load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line
    ]


def condition_summary(rows, condition):
    selected = [row for row in rows if row["condition"] == condition]
    return {
        "count": len(selected),
        "safe_count": sum(row["safe_outcome"] for row in selected),
        "safe_rate": rate(sum(row["safe_outcome"] for row in selected), len(selected)),
        "selected_count": sum(row["selected"] for row in selected),
        "wrong_trace_selection_count": sum(
            row["wrong_trace_selected"] for row in selected
        ),
        "status_counts": dict(Counter(row["status"] for row in selected)),
    }


def model_summary(model, rows, cases, v1_prereg):
    conditions = {row["id"]: row for row in v1_prereg["conditions"]}
    cases_by_id = {case["case_id"]: case for case in cases}
    phase_1_names = [
        "n1_remove_exact_hard_negative",
        "t1_remove_exact_target",
    ]
    phase_rows = [row for row in rows if row["condition"] in phase_1_names]
    phase = phase_1_summary(phase_rows)
    spans = raw_span_grounding(rows, cases_by_id, conditions)
    by_condition = {
        condition: condition_summary(rows, condition)
        for condition in conditions
    }
    latencies = [row["latency_seconds"] for row in rows if not row["reused_prior_result"]]
    structured_rate = rate(
        sum(row["evidence_validation"].get("valid", False) for row in rows), len(rows)
    )
    wrong_trace_count = sum(row["wrong_trace_selected"] for row in rows)
    target_removed_count = by_condition["t1_remove_exact_target"]["selected_count"]
    complete = len(rows) == 32 and all(row["count"] == 8 for row in by_condition.values())
    final_gates = {
        "all_32_decisions_present": complete,
        "structured_parse_rate_equals_one": structured_rate == 1.0,
        "exact_span_grounding_rate_equals_one": spans["exact_span_grounding_rate"]
        == 1.0,
        "wrong_trace_selection_count_strictly_lower_than_lexical_v1_9": wrong_trace_count
        < 9,
        "target_removed_selection_count_equals_zero": target_removed_count == 0,
        "intact_safe_outcome_rate_at_least": by_condition[
            "c0_intact_target_and_hard_negative"
        ]["safe_rate"]
        >= 0.875,
        "replacement_safe_outcome_rate_strictly_higher_than": by_condition[
            "t2_replace_exact_target"
        ]["safe_rate"]
        > 0.375,
        "target_only_safe_outcome_rate_at_least": by_condition[
            "n1_remove_exact_hard_negative"
        ]["safe_rate"]
        >= 0.75,
        "transport_error_count_equals_zero": sum(
            row["transport_error_count"] for row in rows
        )
        == 0,
        "production_memory_write_count_equals_zero": sum(
            row["production_memory_write_count"] for row in rows
        )
        == 0,
        "physical_vrm_action_count_equals_zero": sum(
            row["physical_vrm_action_count"] for row in rows
        )
        == 0,
    }
    return {
        "model": model["tag"],
        "model_digest": model["digest"],
        "size_bytes": model["size_bytes"],
        "reused_prior_result": bool(model.get("reuse_prior_result")),
        "decision_count": len(rows),
        "phase_1": phase,
        "phase_2_run": complete,
        "structured_parse_rate": structured_rate,
        **spans,
        "wrong_trace_selection_count": wrong_trace_count,
        "target_removed_selection_count": target_removed_count,
        "intact_safe_outcome_rate": by_condition[
            "c0_intact_target_and_hard_negative"
        ]["safe_rate"],
        "replacement_safe_outcome_rate": by_condition[
            "t2_replace_exact_target"
        ]["safe_rate"],
        "target_only_safe_outcome_rate": by_condition[
            "n1_remove_exact_hard_negative"
        ]["safe_rate"],
        "mean_new_call_latency_seconds": round(sum(latencies) / len(latencies), 6)
        if latencies
        else None,
        "p95_new_call_latency_seconds": percentile(latencies, 0.95)
        if latencies
        else None,
        "by_condition": by_condition,
        "final_gates": final_gates,
        "eligible": all(final_gates.values()),
    }


def summarize(rows, prereg, metadata):
    v1_prereg = load_json(
        ROOT / prereg["frozen_artifacts"]["v1_preregistration"]["path"]
    )
    cases = load_json(ROOT / v1_prereg["development_data"]["cases_path"])["cases"]
    model_results = []
    for model in prereg["models"]:
        model_rows = [row for row in rows if row["screen_model"] == model["tag"]]
        model_results.append(model_summary(model, model_rows, cases, v1_prereg))
    eligible = sorted(
        [row for row in model_results if row["eligible"]],
        key=lambda row: (
            row["size_bytes"],
            row["mean_new_call_latency_seconds"]
            if row["mean_new_call_latency_seconds"] is not None
            else float("inf"),
            row["model"],
        ),
    )
    selected = eligible[0]["model"] if eligible else None
    decision = (
        "model_selected_requires_fresh_holdout"
        if selected
        else "model_capacity_not_sufficient"
    )
    integrity = {
        "raw_hash_match": metadata.get("raw_sha256")
        == file_sha256(ROOT / metadata["raw_path"]),
        "metadata_row_count_match": metadata.get("row_count") == len(rows),
        "frozen_artifacts_match": all(
            file_sha256(ROOT / artifact["path"]) == artifact["sha256"]
            for artifact in prereg["frozen_artifacts"].values()
        ),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(
            row["physical_vrm_action_count"] for row in rows
        ),
    }
    return {
        "schema": "uruha_answer_bearing_memory_span_model_capacity_report_v1",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "selected_model": selected,
        "eligible_models": [row["model"] for row in eligible],
        "integrity": integrity,
        "model_results": model_results,
        "new_model_call_count": metadata["new_model_call_count"],
        "evidence_scope": "consumed_exposed_development_only",
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown_report(report):
    lines = [
        "# Answer-bearing memory span model-capacity V1 result",
        "",
        "## Decision",
        "",
        f"**{report['decision']}**",
        "",
        f"Selected model: `{report['selected_model'] or 'none'}`.",
        "",
        "This is consumed development evidence only. It cannot authorize runtime.",
        "",
        "## Staged comparison",
        "",
        "| Model | Phase 1 target-only | Removed-target selections | Full run | Intact | Replacement | Target-only | Wrong traces | Contract | Grounding | Mean new-call latency | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["model_results"]:
        latency = (
            f"{row['mean_new_call_latency_seconds']:.3f}s"
            if row["mean_new_call_latency_seconds"] is not None
            else "reused"
        )
        lines.append(
            f"| {row['model']} | {row['phase_1']['target_only_safe_count']}/8 | {row['target_removed_selection_count']} | {row['decision_count']}/32 | {row['intact_safe_outcome_rate']:.1%} | {row['replacement_safe_outcome_rate']:.1%} | {row['target_only_safe_outcome_rate']:.1%} | {row['wrong_trace_selection_count']} | {row['structured_parse_rate']:.1%} | {row['exact_span_grounding_rate']:.1%} | {latency} | {'yes' if row['eligible'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "The screen isolates model size under one frozen contract. If no model passes, increasing model capacity is not a sufficient repair on this slice. If one passes, only a new disjoint holdout is authorized; runtime remains unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    prereg = load_json(PREREG_PATH)
    rows = load_jsonl(args.raw)
    metadata = load_json(args.metadata)
    if metadata.get("raw_sha256") != file_sha256(args.raw):
        raise ValueError("raw output hash mismatch")
    report = summarize(rows, prereg, metadata)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "selected_model": report["selected_model"],
                "model_results": [
                    {
                        "model": row["model"],
                        "phase_1_passed": row["phase_1"]["passed"],
                        "decision_count": row["decision_count"],
                        "eligible": row["eligible"],
                    }
                    for row in report["model_results"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
