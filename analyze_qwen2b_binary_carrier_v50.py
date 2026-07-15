#!/usr/bin/env python3
"""Analyze and select the V50 Qwen2B binary transport carrier."""

import argparse
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json"
DEFAULT_RAW = ROOT / "reports" / "qwen2b_binary_carrier_v50_probe_raw.json"
DEFAULT_JSON = ROOT / "reports" / "qwen2b_binary_carrier_v50_probe_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "qwen2b_binary_carrier_v50_probe_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def summarize_carrier(raw, carrier):
    rows = [row for row in raw["probe_rows"] if row["carrier"] == carrier]
    total = len(rows)
    parsed = sum(row["result"]["parsed"]["parse_success"] for row in rows)
    faithful = sum(
        row["result"]["parsed"]["parse_success"]
        and row["result"]["parsed"]["decision"] == row["source_decision"]
        for row in rows
    )
    single = sum(row["result"]["parsed"]["single_result"] for row in rows)
    unexpected = sum(
        row["result"]["parsed"]["unexpected_content"] for row in rows
    )
    latencies = [row["result"]["response_metrics"]["wall_seconds"] for row in rows]
    return {
        "case_count": total,
        "parse_success_rate": _rate(parsed, total),
        "source_decision_fidelity": _rate(faithful, total),
        "single_result_rate": _rate(single, total),
        "unexpected_content_rate": _rate(unexpected, total),
        "median_latency_seconds": round(statistics.median(latencies), 4),
        "p95_latency_seconds": _percentile(latencies, 0.95),
        "failure_rows": [
            {
                "case_id": row["case_id"],
                "source_decision": row["source_decision"],
                "parsed": row["result"]["parsed"],
                "response_message": row["result"]["response_message"],
            }
            for row in rows
            if not (
                row["result"]["parsed"]["parse_success"]
                and row["result"]["parsed"]["decision"] == row["source_decision"]
                and row["result"]["parsed"]["single_result"]
                and not row["result"]["parsed"]["unexpected_content"]
            )
        ],
    }


def evaluate_gate(summary, gates):
    checks = {
        "parse_success_rate": summary["parse_success_rate"]
        == gates["parse_success_rate"],
        "source_decision_fidelity": summary["source_decision_fidelity"]
        == gates["source_decision_fidelity"],
        "single_result_rate": summary["single_result_rate"]
        == gates["single_result_rate"],
        "unexpected_content_rate": summary["unexpected_content_rate"]
        == gates["unexpected_content_rate"],
        "p95_latency_seconds": summary["p95_latency_seconds"]
        <= gates["p95_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw, config):
    if not raw.get("completed_at"):
        raise ValueError("V50 probe report is incomplete")
    if len(raw["probe_rows"]) != config["expected_scored_call_count"]:
        raise ValueError("V50 scored row count mismatch")
    summaries = {
        carrier: summarize_carrier(raw, carrier)
        for carrier in config["carrier_order"]
    }
    gates = {
        carrier: evaluate_gate(summary, config["gates"])
        for carrier, summary in summaries.items()
    }
    eligible = [
        carrier
        for carrier in config["selection_priority"]
        if gates[carrier]["passed"]
    ]
    selected = eligible[0] if eligible else None
    return {
        "schema": "uruha_qwen2b_binary_carrier_probe_analysis_v50",
        "evidence_status": raw["evidence_status"],
        "carriers": summaries,
        "carrier_gates": gates,
        "eligible_selection_candidates": eligible,
        "selected_carrier": selected,
        "v51_fresh_holdout_construction_authorized": selected is not None,
        "decision": (
            "authorize_v51_fresh_holdout_construction"
            if selected
            else "retire_qwen35_2b_from_binary_gate_role"
        ),
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def render_markdown(analysis):
    lines = [
        "# V50 Qwen2B non-semantic carrier probe",
        "",
        "| carrier | parse | fidelity | single | unexpected | median | p95 | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for carrier, row in analysis["carriers"].items():
        lines.append(
            f"| {carrier} | {100*row['parse_success_rate']:.1f}% | "
            f"{100*row['source_decision_fidelity']:.1f}% | "
            f"{100*row['single_result_rate']:.1f}% | "
            f"{100*row['unexpected_content_rate']:.1f}% | "
            f"{row['median_latency_seconds']:.2f}s | {row['p95_latency_seconds']:.2f}s | "
            f"{analysis['carrier_gates'][carrier]['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Selected carrier: `{analysis['selected_carrier']}`",
            f"- Decision: `{analysis['decision']}`",
            "- This result measures transport compatibility only, not semantic ability or runtime safety.",
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
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    analysis = analyze(raw, config)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "selected_carrier": analysis["selected_carrier"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
