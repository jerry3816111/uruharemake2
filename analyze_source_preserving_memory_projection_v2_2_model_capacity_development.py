#!/usr/bin/env python3
"""Analyze the frozen V2.2 9B evidence-extractor capacity screen."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_source_preserving_memory_projection_v2_1_development import (
    audit_cases_against_source,
    percentile,
    rate,
)
from run_source_preserving_memory_projection_v2_1_development import ROOT, file_sha256, load_json
from run_source_preserving_memory_projection_v2_2_model_capacity_development import (
    CONTRACT,
    DEFAULT_METADATA,
    DEFAULT_RAW,
    load_frozen_configuration,
)


DEFAULT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_development.json"
DEFAULT_MD = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_development.md"


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def row_key(row):
    return (row["case_id"], row["condition"], row["representation"])


def expected_keys(cases, prereg):
    return [
        (case["case_id"], condition, representation)
        for case in cases
        for condition in prereg["controlled_variables"]["conditions"]
        for representation in prereg["controlled_variables"]["representations"]
    ]


def selected(rows, condition, representation):
    return [
        row
        for row in rows
        if row["condition"] == condition and row["representation"] == representation
    ]


def summarize(rows, metadata, contract, prereg, cases_payload, raw_hash_match):
    cases = cases_payload["cases"]
    source_audit = audit_cases_against_source(cases_payload)
    target_complete = selected(rows, "remove_exact_hard_negative", "complete_session")
    target_projected = selected(rows, "remove_exact_hard_negative", "source_projection")
    removed_complete = selected(rows, "remove_exact_target", "complete_session")
    removed_projected = selected(rows, "remove_exact_target", "source_projection")
    structured = sum(row["evidence_validation"].get("valid", False) for row in rows)
    grounded = sum(row["evidence_validation"].get("all_spans_grounded", False) for row in rows)
    actual = [row_key(row) for row in rows]
    expected = expected_keys(cases, prereg)
    control = prereg["frozen_control"]
    target_projected_count = sum(row["target_supported"] for row in target_projected)
    target_complete_count = sum(row["target_supported"] for row in target_complete)
    projected_false_count = sum(row["hard_negative_supported"] for row in removed_projected)
    complete_false_count = sum(row["hard_negative_supported"] for row in removed_complete)
    latencies = {
        representation: [
            row["latency_seconds"] for row in rows if row["representation"] == representation
        ]
        for representation in ("complete_session", "source_projection")
    }
    characters = {
        representation: sum(
            row["visible_character_count"]
            for row in rows
            if row["representation"] == representation
        )
        for representation in ("complete_session", "source_projection")
    }
    metrics = {
        "frozen_4b_projected_target_support_count": control["projected_target_support_count"],
        "intervention_9b_complete_target_support_count": target_complete_count,
        "intervention_9b_projected_target_support_count": target_projected_count,
        "projected_9b_minus_frozen_4b_support_count": target_projected_count
        - control["projected_target_support_count"],
        "intervention_9b_complete_false_support_count": complete_false_count,
        "intervention_9b_projected_false_support_count": projected_false_count,
        "structured_contract_rate": rate(structured, len(rows)),
        "exact_span_grounding_rate": rate(grounded, len(rows)),
        "source_projection_exactness_rate": rate(
            sum(case["source_projection_exact"] for case in source_audit["cases"]),
            len(source_audit["cases"]),
        ),
        "transport_error_count": sum(row["transport_error_count"] for row in rows),
        "mean_latency_seconds_by_representation": {
            key: round(sum(values) / len(values), 6) if values else 0.0
            for key, values in latencies.items()
        },
        "p95_latency_seconds_by_representation": {
            key: percentile(values, 0.95) for key, values in latencies.items()
        },
        "total_visible_characters_by_representation": characters,
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    intervention = prereg["independent_variable"]["intervention"]
    integrity = {
        "all_frozen_artifact_hashes_match": all(
            file_sha256(ROOT / artifact["path"]) == artifact["sha256"]
            for artifact in contract["artifacts"].values()
        ),
        "raw_hash_match": raw_hash_match,
        "official_source_hash_match": source_audit["official_source_hash_match"],
        "metadata_experiment_id_match": metadata.get("experiment_id") == prereg["experiment_id"],
        "metadata_row_count_match": metadata.get("row_count") == len(rows),
        "exact_expected_row_key_set": Counter(actual) == Counter(expected),
        "no_duplicate_row_keys": len(actual) == len(set(actual)),
        "model_digest_match": metadata.get("model_digest") == intervention["digest"],
        "endpoint_match": metadata.get("endpoint") == prereg["controlled_variables"]["endpoint"],
    }
    success = prereg["success_gates"]
    gates = {
        **{f"integrity_{key}": value for key, value in integrity.items()},
        "all_32_decisions_present": len(rows) == prereg["controlled_variables"]["call_count"]
        and integrity["exact_expected_row_key_set"],
        "projected_target_support_count_at_least": target_projected_count
        >= success["projected_target_support_count_at_least"],
        "projected_minus_frozen_4b_target_support_count_at_least": metrics[
            "projected_9b_minus_frozen_4b_support_count"
        ]
        >= success["projected_minus_frozen_4b_target_support_count_at_least"],
        "projected_hard_negative_false_support_count_equals_zero": projected_false_count
        == success["projected_hard_negative_false_support_count_equals"],
        "structured_contract_rate_equals_one": metrics["structured_contract_rate"]
        == success["structured_contract_rate_equals"],
        "exact_span_grounding_rate_equals_one": metrics["exact_span_grounding_rate"]
        == success["exact_span_grounding_rate_equals"],
        "transport_error_count_equals_zero": metrics["transport_error_count"]
        == success["transport_error_count_equals"],
        "source_projection_exactness_rate_equals_one": metrics[
            "source_projection_exactness_rate"
        ]
        == success["source_projection_exactness_rate_equals"],
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
        "schema": "uruha_source_preserving_memory_projection_model_capacity_report_v2_2",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_scope": "exposed_official_dataset_development_only",
        "integrity": integrity,
        "metrics": metrics,
        "gates": gates,
        "invalid_rows": [
            {
                "case_id": row["case_id"],
                "condition": row["condition"],
                "representation": row["representation"],
                "errors": row["evidence_validation"].get("errors", []),
            }
            for row in rows
            if not row["evidence_validation"].get("valid")
        ],
        "authorization": {
            "runtime_change": False,
            "production_enablement": False,
            "fresh_external_holdout": decision
            == "development_pass_requires_external_fresh_holdout",
        },
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown(report):
    metrics = report["metrics"]
    failed = [name for name, passed in report["gates"].items() if not passed]
    return "\n".join(
        [
            "# V2.2 Local Evidence Extractor Capacity Screen",
            "",
            f"**Decision: {report['decision']}**",
            "",
            "| Measure | Frozen 4B | 9B intervention | Difference |",
            "|---|---:|---:|---:|",
            f"| Projected target support | {metrics['frozen_4b_projected_target_support_count']}/8 | {metrics['intervention_9b_projected_target_support_count']}/8 | {metrics['projected_9b_minus_frozen_4b_support_count']:+d} |",
            f"| Structured contract | 87.5% | {metrics['structured_contract_rate']:.1%} | {metrics['structured_contract_rate'] - 0.875:+.1%} |",
            f"| Exact span grounding | 87.5% | {metrics['exact_span_grounding_rate']:.1%} | {metrics['exact_span_grounding_rate'] - 0.875:+.1%} |",
            "",
            f"- 9B complete-session target support: {metrics['intervention_9b_complete_target_support_count']}/8",
            f"- 9B projected hard-negative false support: {metrics['intervention_9b_projected_false_support_count']}/8",
            f"- 9B mean latency (complete / projection): {metrics['mean_latency_seconds_by_representation']['complete_session']:.2f}s / {metrics['mean_latency_seconds_by_representation']['source_projection']:.2f}s",
            "",
            "## Failed gates",
            "",
            *([f"- `{name}`" for name in failed] or ["- None"]),
            "",
            "This paired exposed-development screen does not authorize runtime or production use.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    contract, prereg, _runtime = load_frozen_configuration()
    rows = load_jsonl(args.raw)
    metadata = load_json(args.metadata)
    raw_hash_match = metadata.get("raw_sha256") == file_sha256(args.raw)
    if not raw_hash_match:
        raise ValueError("raw output hash mismatch")
    cases_payload = load_json(ROOT / contract["artifacts"]["cases"]["path"])
    report = summarize(rows, metadata, contract, prereg, cases_payload, raw_hash_match)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "metrics": report["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
