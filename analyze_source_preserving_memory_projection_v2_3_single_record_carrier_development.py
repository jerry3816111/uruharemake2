#!/usr/bin/env python3
"""Analyze the frozen V2.3 single-record evidence carrier experiment."""

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
from run_source_preserving_memory_projection_v2_3_single_record_carrier_development import (
    CONTRACT,
    DEFAULT_METADATA,
    DEFAULT_RAW,
    load_frozen_configuration,
)


DEFAULT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_development.json"
DEFAULT_MD = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_development.md"


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def row_key(row):
    return (row["case_id"], row["condition"], row["representation"])


def selected(rows, condition, representation):
    return [
        row
        for row in rows
        if row["condition"] == condition and row["representation"] == representation
    ]


def expected_keys(cases, prereg):
    controlled = prereg["controlled_variables"]
    return [
        (case["case_id"], condition, representation)
        for case in cases
        for condition in controlled["conditions"]
        for representation in controlled["representations"]
    ]


def summarize(rows, metadata, contract, prereg, cases_payload, raw_hash_match):
    cases = cases_payload["cases"]
    source_audit = audit_cases_against_source(cases_payload)
    complete_target_rows = selected(rows, "remove_exact_hard_negative", "complete_session")
    projected_target_rows = selected(rows, "remove_exact_hard_negative", "source_projection")
    projected_removed_rows = selected(rows, "remove_exact_target", "source_projection")
    complete_target_count = sum(row["target_supported"] for row in complete_target_rows)
    projected_target_count = sum(row["target_supported"] for row in projected_target_rows)
    projected_false_count = sum(row["hard_negative_supported"] for row in projected_removed_rows)
    structured = sum(row["evidence_validation"].get("valid", False) for row in rows)
    grounded = sum(row["evidence_validation"].get("all_spans_grounded", False) for row in rows)
    nonexistent_index_errors = sum(
        error == "source_indices_not_complete_and_unique"
        for row in rows
        for error in row["evidence_validation"].get("errors", [])
    )
    actual = [row_key(row) for row in rows]
    expected = expected_keys(cases, prereg)
    latencies = {
        representation: [
            row["latency_seconds"] for row in rows if row["representation"] == representation
        ]
        for representation in ("complete_session", "source_projection")
    }
    metrics = {
        "frozen_9b_indexed_complete_target_support_count": prereg["frozen_control"][
            "complete_target_support_count"
        ],
        "single_record_complete_target_support_count": complete_target_count,
        "frozen_9b_indexed_projected_target_support_count": prereg["frozen_control"][
            "projected_target_support_count"
        ],
        "single_record_projected_target_support_count": projected_target_count,
        "single_record_projected_false_support_count": projected_false_count,
        "structured_contract_rate": rate(structured, len(rows)),
        "exact_span_grounding_rate": rate(grounded, len(rows)),
        "nonexistent_source_index_error_count": nonexistent_index_errors,
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
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    controlled = prereg["controlled_variables"]
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
        "model_digest_match": metadata.get("model_digest") == controlled["model_digest"],
        "endpoint_match": metadata.get("endpoint") == controlled["endpoint"],
    }
    success = prereg["success_gates"]
    gates = {
        **{f"integrity_{key}": value for key, value in integrity.items()},
        "all_32_decisions_present": len(rows) == controlled["call_count"]
        and integrity["exact_expected_row_key_set"],
        "complete_target_support_count_at_least": complete_target_count
        >= success["complete_target_support_count_at_least"],
        "projected_target_support_count_at_least": projected_target_count
        >= success["projected_target_support_count_at_least"],
        "projected_target_support_not_lower_than_frozen_9b": projected_target_count
        >= prereg["frozen_control"]["projected_target_support_count"],
        "projected_hard_negative_false_support_count_equals_zero": projected_false_count
        == success["projected_hard_negative_false_support_count_equals"],
        "structured_contract_rate_equals_one": metrics["structured_contract_rate"]
        == success["structured_contract_rate_equals"],
        "exact_span_grounding_rate_equals_one": metrics["exact_span_grounding_rate"]
        == success["exact_span_grounding_rate_equals"],
        "nonexistent_source_index_error_count_equals_zero": nonexistent_index_errors
        == success["nonexistent_source_index_error_count_equals"],
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
        "schema": "uruha_source_preserving_memory_projection_single_record_report_v2_3",
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
            "# V2.3 Single-record Evidence Carrier Result",
            "",
            f"**Decision: {report['decision']}**",
            "",
            "| Measure | Indexed 9B control | Single-record carrier |",
            "|---|---:|---:|",
            f"| Complete target support | {metrics['frozen_9b_indexed_complete_target_support_count']}/8 | {metrics['single_record_complete_target_support_count']}/8 |",
            f"| Projected target support | {metrics['frozen_9b_indexed_projected_target_support_count']}/8 | {metrics['single_record_projected_target_support_count']}/8 |",
            f"| Structured contract | 81.25% | {metrics['structured_contract_rate']:.1%} |",
            f"| Exact span grounding | 81.25% | {metrics['exact_span_grounding_rate']:.1%} |",
            f"| Nonexistent source-index errors | 6 | {metrics['nonexistent_source_index_error_count']} |",
            "",
            "## Failed gates",
            "",
            *([f"- `{name}`" for name in failed] or ["- None"]),
            "",
            "This exposed development result does not directly authorize runtime use.",
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
    contract, prereg, _conditions = load_frozen_configuration()
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
