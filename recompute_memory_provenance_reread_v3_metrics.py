#!/usr/bin/env python3
"""Recompute V3 metrics from frozen generations without making model calls."""

import argparse
import copy
import json
from pathlib import Path

from run_longmemeval_retrieval_benchmark import atomic_write_json, canonical_sha256, file_sha256
from run_memory_provenance_reread_v3 import (
    CONDITIONS,
    DEFAULT_REPORT_JSON,
    DEFAULT_REPORT_MD,
    ROOT,
    build_report,
    implementation_evidence,
    load_protocol,
    render_markdown,
    score_condition,
)


DEFAULT_SOURCE = ROOT / "reports" / "memory_provenance_reread_v3_report_raw_metric_v1.json"
DEFAULT_SOURCE_SHA256 = "0e4c560fda5f9d881184f2d0cadbdc48ead0ecaac36a4580ab9c9d3b31a9661b"
RESOURCE_METRICS = ("latency_seconds", "prompt_tokens", "completion_tokens")


def response_projection(results):
    return [
        {
            "case_id": row["case_id"],
            "responses": {
                condition: row["conditions"][condition]["response"]
                for condition in CONDITIONS
            },
        }
        for row in results
    ]


def recompute(source_report, dataset, fixed_abstention):
    cases = {case["case_id"]: case for case in dataset["cases"]}
    results = copy.deepcopy(source_report["results"])
    before_projection = response_projection(results)
    for row in results:
        case = cases.get(row["case_id"])
        if case is None:
            raise ValueError(f"Source report contains an unknown case: {row['case_id']}")
        for condition in CONDITIONS:
            artifact = row["conditions"][condition]
            old_metrics = artifact.get("metrics") or {}
            resources = {key: old_metrics.get(key) for key in RESOURCE_METRICS}
            metrics = score_condition(case, artifact, fixed_abstention)
            metrics.update(resources)
            artifact["metrics"] = metrics
    after_projection = response_projection(results)
    if before_projection != after_projection:
        raise AssertionError("Metric recomputation changed a model response")
    return results, canonical_sha256(before_projection)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--expected-source-sha256", default=DEFAULT_SOURCE_SHA256)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source_hash = file_sha256(args.source_report)
    if source_hash != args.expected_source_sha256:
        raise ValueError(
            f"Frozen source report hash mismatch: {source_hash} != "
            f"{args.expected_source_sha256}"
        )
    if not args.overwrite and (args.output_json.exists() or args.output_md.exists()):
        raise FileExistsError("Output exists; pass --overwrite after preserving the raw report")

    protocol, dataset, dataset_path = load_protocol()
    source = json.loads(args.source_report.read_text(encoding="utf-8"))
    if source.get("protocol") != protocol:
        raise ValueError("Source report protocol mismatch")
    if not source.get("complete") or len(source.get("results") or []) != len(dataset["cases"]):
        raise ValueError("Source report is not a complete frozen run")

    results, response_hash = recompute(
        source,
        dataset,
        protocol["inference"]["explicit_abstention"],
    )
    implementation = implementation_evidence(dataset_path)
    implementation["metric_recompute_runner_sha256"] = file_sha256(Path(__file__))
    report = build_report(
        protocol,
        dataset_path,
        source["model_evidence"],
        implementation,
        results,
    )
    report["metric_recompute"] = {
        "source_report": str(args.source_report.relative_to(ROOT)),
        "source_report_sha256": source_hash,
        "source_results_sha256": source["results_sha256"],
        "response_projection_sha256": response_hash,
        "model_calls_made": 0,
        "dataset_changed": False,
        "prompts_changed": False,
        "responses_changed": False,
        "corrections": [
            "compound number words are equivalent to their digit form",
            "frequency values preserve number and cadence even when word order changes",
        ],
        "source_decision": source["decision"],
        "recomputed_decision": report["decision"],
    }
    atomic_write_json(args.output_json, report)
    markdown = render_markdown(report)
    markdown += (
        "\n## Metric recomputation audit\n\n"
        f"- Frozen source report SHA-256: `{source_hash}`.\n"
        f"- Response projection SHA-256: `{response_hash}`.\n"
        "- Model calls: `0`; dataset, prompts, and responses changed: `false`.\n"
        "- Only compound-number equivalence and frequency word-order equivalence were "
        "recomputed. The runtime decision remains evidence-gated.\n"
    )
    args.output_md.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "source_report_sha256": source_hash,
                "response_projection_sha256": response_hash,
                "results_sha256": report["results_sha256"],
                "decision": report["decision"],
                "all_gates_pass": report["all_gates_pass"],
                "model_calls_made": 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
