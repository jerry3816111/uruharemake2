#!/usr/bin/env python3
"""Analyze the frozen V2.1 source-preserving memory projection run."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import build_source_preserving_memory_projection_v2_development as case_builder
from audit_semantic_memory_recall_support_v1_evidence_contract import load_dataset
from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH
from run_source_preserving_memory_projection_v2_1_development import (
    CONTRACT,
    ROOT,
    file_sha256,
    load_effective_contract,
    load_json,
    phase_1_passes,
)


DEFAULT_RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/run_metadata.json"
DEFAULT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_1_development.json"
DEFAULT_MD = ROOT / "reports/source_preserving_memory_projection_v2_1_development.md"


def load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line
    ]


def rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else 0.0


def percentile(values, quantile):
    values = sorted(float(value) for value in values)
    if not values:
        return 0.0
    position = (len(values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(values[lower], 6)
    weight = position - lower
    return round(values[lower] * (1 - weight) + values[upper] * weight, 6)


def rows_for(rows, condition, representation):
    return [
        row
        for row in rows
        if row["condition"] == condition and row["representation"] == representation
    ]


def support_count(rows, role):
    field = "target_supported" if role == "target" else "hard_negative_supported"
    return sum(row[field] for row in rows)


def row_key(row):
    return (row["case_id"], row["condition"], row["representation"])


def expected_row_keys(cases, prereg, phase_1_passed):
    stage = prereg["staged_execution"]
    phases = [
        (stage["phase_1_conditions"], stage["phase_1_representations"]),
    ]
    if phase_1_passed:
        phases.append((stage["phase_2_conditions"], stage["phase_2_representations"]))
    return [
        (case["case_id"], condition, representation)
        for case in cases
        for conditions, representations in phases
        for condition in conditions
        for representation in representations
    ]


def paired_support_changes(complete_rows, projected_rows):
    complete_by_case = {row["case_id"]: row for row in complete_rows}
    projected_by_case = {row["case_id"]: row for row in projected_rows}
    paired_ids = sorted(set(complete_by_case) & set(projected_by_case))
    gains = sum(
        (not complete_by_case[case_id]["target_supported"])
        and projected_by_case[case_id]["target_supported"]
        for case_id in paired_ids
    )
    losses = sum(
        complete_by_case[case_id]["target_supported"]
        and (not projected_by_case[case_id]["target_supported"])
        for case_id in paired_ids
    )
    return gains, losses


def audit_cases_against_source(cases_payload):
    data, source_evidence = load_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    rows = {row["question_id"]: row for row in data}
    audited = []
    for case in cases_payload["cases"]:
        row = rows.get(case["official_question_id"])
        complete_exact = row is not None
        projection_exact = row is not None
        if row is not None:
            for role in ("target", "hard_negative"):
                record = case[role]
                source = case_builder.source_session(row, record["official_session_id"])
                complete_exact = complete_exact and record["complete_session"] == (
                    case_builder.complete_representation(source["session"], source["timestamp"])
                )
                projection_exact = projection_exact and record["source_projection"] == (
                    case_builder.projection_representation(
                        source["session"], source["timestamp"], row["question"]
                    )
                )
        audited.append(
            {
                "case_id": case["case_id"],
                "complete_session_exact": complete_exact,
                "source_projection_exact": projection_exact,
                "answer_boundary_valid": case_audit(case)["postconstruction_valid"],
            }
        )
    return {
        "official_source_hash_match": source_evidence["sha256"]
        == cases_payload["source"]["sha256"],
        "cases": audited,
    }


def summarize(rows, metadata, contract, prereg, cases_payload, raw_hash_verified):
    source_audit = audit_cases_against_source(cases_payload)
    cases = source_audit["cases"]
    complete_target_only = rows_for(rows, "remove_exact_hard_negative", "complete_session")
    projected_target_only = rows_for(rows, "remove_exact_hard_negative", "source_projection")
    complete_removed = rows_for(rows, "remove_exact_target", "complete_session")
    projected_removed = rows_for(rows, "remove_exact_target", "source_projection")
    complete_intact = rows_for(rows, "intact_target_and_hard_negative", "complete_session")
    projected_intact = rows_for(rows, "intact_target_and_hard_negative", "source_projection")
    structured_count = sum(row["evidence_validation"].get("valid", False) for row in rows)
    grounded_count = sum(
        row["evidence_validation"].get("all_spans_grounded", False) for row in rows
    )
    transport_errors = sum(row["transport_error_count"] for row in rows)
    complete_target_count = support_count(complete_target_only, "target")
    projected_target_count = support_count(projected_target_only, "target")
    complete_intact_count = support_count(complete_intact, "target")
    projected_intact_count = support_count(projected_intact, "target")
    projected_removed_false = support_count(projected_removed, "hard_negative")
    complete_removed_false = support_count(complete_removed, "hard_negative")
    paired_gains, paired_losses = paired_support_changes(
        complete_target_only, projected_target_only
    )
    complete_chars = [row["visible_character_count"] for row in rows if row["representation"] == "complete_session"]
    projected_chars = [row["visible_character_count"] for row in rows if row["representation"] == "source_projection"]
    character_reduction = (
        1 - (sum(projected_chars) / sum(complete_chars))
        if complete_chars and projected_chars
        else 0.0
    )
    latencies = {
        representation: [
            row["latency_seconds"] for row in rows if row["representation"] == representation
        ]
        for representation in ("complete_session", "source_projection")
    }
    metrics = {
        "complete_target_only_answer_support_count": complete_target_count,
        "projected_target_only_answer_support_count": projected_target_count,
        "projected_minus_complete_target_only_support_count": projected_target_count
        - complete_target_count,
        "paired_target_only_support_gain_count": paired_gains,
        "paired_target_only_support_loss_count": paired_losses,
        "complete_target_removed_false_support_count": complete_removed_false,
        "projected_target_removed_false_support_count": projected_removed_false,
        "complete_intact_target_support_count": complete_intact_count,
        "projected_intact_target_support_count": projected_intact_count,
        "projected_minus_complete_intact_support_count": projected_intact_count
        - complete_intact_count,
        "source_projection_exactness_rate": rate(
            sum(case["source_projection_exact"] for case in cases), len(cases)
        ),
        "structured_contract_rate": rate(structured_count, len(rows)),
        "exact_span_grounding_rate": rate(grounded_count, len(rows)),
        "mean_prompt_character_reduction_rate": round(character_reduction, 6),
        "mean_latency_seconds_by_representation": {
            key: round(sum(values) / len(values), 6) if values else 0.0
            for key, values in latencies.items()
        },
        "p95_latency_seconds_by_representation": {
            key: percentile(values, 0.95) for key, values in latencies.items()
        },
        "transport_error_count": transport_errors,
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    actual_keys = [row_key(row) for row in rows]
    expected_keys = expected_row_keys(cases, prereg, bool(metadata.get("phase_1_passed")))
    duplicate_keys = sorted(key for key, count in Counter(actual_keys).items() if count > 1)
    missing_keys = sorted(set(expected_keys) - set(actual_keys))
    extra_keys = sorted(set(actual_keys) - set(expected_keys))
    phase_1_rows = [
        row
        for row in rows
        if row["condition"] in prereg["staged_execution"]["phase_1_conditions"]
    ]
    integrity = {
        "all_frozen_artifact_hashes_match": all(
            file_sha256(ROOT / artifact["path"]) == artifact["sha256"]
            for artifact in contract["artifacts"].values()
        ),
        "raw_hash_match": raw_hash_verified,
        "official_source_hash_match": source_audit["official_source_hash_match"],
        "metadata_experiment_id_match": metadata.get("experiment_id")
        == prereg["experiment_id"],
        "metadata_row_count_match": metadata.get("row_count") == len(rows),
        "exact_expected_row_key_set": Counter(actual_keys) == Counter(expected_keys),
        "no_duplicate_row_keys": not duplicate_keys,
        "model_digest_match": metadata.get("model_digest")
        == prereg["span_gate"]["model_digest"],
        "endpoint_match": metadata.get("endpoint") == prereg["span_gate"]["endpoint"],
        "phase_1_metadata_match": bool(metadata.get("phase_1_passed"))
        == phase_1_passes(phase_1_rows, prereg),
    }
    integrity_gates = {
        f"integrity_{name}": value == expected
        for name, expected in contract["integrity_gate"].items()
        for value in [integrity[name]]
    }
    success = prereg["success_gates"]
    full_count = prereg["staged_execution"]["maximum_total_model_calls"]
    gates = {
        **integrity_gates,
        "all_source_preflight_checks_pass": source_audit["official_source_hash_match"]
        and all(
            case["complete_session_exact"]
            and case["source_projection_exact"]
            and case["answer_boundary_valid"]
            for case in cases
        ),
        "all_48_decisions_present": len(rows) == full_count
        and integrity["exact_expected_row_key_set"],
        "projected_target_only_answer_support_count_at_least": projected_target_count
        >= success["projected_target_only_answer_support_count_at_least"],
        "projected_minus_complete_target_only_support_count_at_least": projected_target_count
        - complete_target_count
        >= success["projected_minus_complete_target_only_support_count_at_least"],
        "projected_target_removed_false_support_count_equals_zero": projected_removed_false
        == success["projected_target_removed_false_support_count_equals"],
        "projected_intact_target_support_count_at_least": projected_intact_count
        >= success["projected_intact_target_support_count_at_least"],
        "projected_intact_target_support_not_lower_than_complete": projected_intact_count
        >= complete_intact_count,
        "source_projection_exactness_rate_equals_one": metrics[
            "source_projection_exactness_rate"
        ]
        == success["source_projection_exactness_rate_equals"],
        "structured_contract_rate_equals_one": metrics["structured_contract_rate"]
        == success["structured_contract_rate_equals"],
        "exact_span_grounding_rate_equals_one": metrics["exact_span_grounding_rate"]
        == success["exact_span_grounding_rate_equals"],
        "transport_error_count_equals_zero": transport_errors
        == success["transport_error_count_equals"],
        "production_memory_write_count_equals_zero": metrics[
            "production_memory_write_count"
        ]
        == success["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals_zero": metrics["physical_vrm_action_count"]
        == success["physical_vrm_action_count_equals"],
    }
    decision = (
        "development_pass_requires_external_fresh_holdout"
        if all(gates.values())
        else "development_reject_or_inconclusive"
    )
    return {
        "schema": "uruha_source_preserving_memory_projection_report_v2_1",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_scope": "exposed_official_dataset_development_only",
        "integrity": {
            **integrity,
            "phase_1_passed": metadata.get("phase_1_passed"),
            "row_count": len(rows),
            "expected_row_count": len(expected_keys),
            "duplicate_row_keys": [list(key) for key in duplicate_keys],
            "missing_row_keys": [list(key) for key in missing_keys],
            "extra_row_keys": [list(key) for key in extra_keys],
        },
        "metrics": metrics,
        "gates": gates,
        "status_counts": dict(Counter("safe" if row["safe_outcome"] else "unsafe" for row in rows)),
        "authorization": {
            "runtime_change": False,
            "production_enablement": False,
            "fresh_holdout": decision == "development_pass_requires_external_fresh_holdout",
        },
        "evidence_boundary": "This exposed development comparison can test the projection mechanism but cannot establish generalization, official LongMemEval accuracy, persona similarity, or human-memory equivalence.",
    }


def markdown_report(report):
    metrics = report["metrics"]
    failed = [name for name, passed in report["gates"].items() if not passed]
    return "\n".join(
        [
            "# Source-preserving Memory Projection V2.1 Development Result",
            "",
            f"**Decision: {report['decision']}**",
            "",
            "| Metric | Complete session | Source projection | Difference |",
            "|---|---:|---:|---:|",
            f"| Target-only support | {metrics['complete_target_only_answer_support_count']}/8 | {metrics['projected_target_only_answer_support_count']}/8 | {metrics['projected_minus_complete_target_only_support_count']:+d} |",
            f"| Target-removed false support | {metrics['complete_target_removed_false_support_count']}/8 | {metrics['projected_target_removed_false_support_count']}/8 | {metrics['projected_target_removed_false_support_count'] - metrics['complete_target_removed_false_support_count']:+d} |",
            f"| Intact target support | {metrics['complete_intact_target_support_count']}/8 | {metrics['projected_intact_target_support_count']}/8 | {metrics['projected_minus_complete_intact_support_count']:+d} |",
            "",
            f"- Exact source projection: {metrics['source_projection_exactness_rate']:.1%}",
            f"- Structured contract: {metrics['structured_contract_rate']:.1%}",
            f"- Exact span grounding: {metrics['exact_span_grounding_rate']:.1%}",
            f"- Mean prompt character reduction: {metrics['mean_prompt_character_reduction_rate']:.1%}",
            "",
            "## Failed gates",
            "",
            *([f"- `{name}`" for name in failed] or ["- None"]),
            "",
            "This is exposed development evidence only. Runtime and production remain disabled.",
            "",
        ]
    )


def case_audit(case):
    answer = str(case["official_answer"]).casefold()
    return {
        **case,
        "postconstruction_valid": answer
        in case["target"]["source_projection"]["text"].casefold()
        and answer not in case["hard_negative"]["source_projection"]["text"].casefold(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    contract, prereg = load_effective_contract()
    rows = load_jsonl(args.raw)
    metadata = load_json(args.metadata)
    raw_hash_verified = metadata.get("raw_sha256") == file_sha256(args.raw)
    if not raw_hash_verified:
        raise ValueError("raw output hash mismatch")
    cases_payload = load_json(ROOT / contract["artifacts"]["cases"]["path"])
    report = summarize(
        rows, metadata, contract, prereg, cases_payload, raw_hash_verified
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "metrics": report["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
