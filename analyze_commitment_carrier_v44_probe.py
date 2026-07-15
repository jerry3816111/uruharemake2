#!/usr/bin/env python3
"""Analyze and mechanically select the V44 carrier probe winner."""

import argparse
import json
import math
import statistics
from pathlib import Path

from commitment_carrier_v44 import CARRIERS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "commitment_carrier_target_isolation_v44_preregistration.json"
DEFAULT_RAW = ROOT / "reports" / "commitment_carrier_v44_probe_raw.json"
DEFAULT_JSON = ROOT / "reports" / "commitment_carrier_v44_probe_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "commitment_carrier_v44_probe_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 4)


def summarize_carrier(raw_report, carrier):
    rows = [row for row in raw_report["probe_rows"] if row["carrier"] == carrier]
    total = len(rows)
    parse = sum(row["result"]["parsed"]["parse_success"] for row in rows)
    faithful = sum(
        row["result"]["parsed"]["parse_success"]
        and row["result"]["parsed"]["commitment"] == row["source_label"]
        for row in rows
    )
    single = sum(row["result"]["parsed"]["single_result"] for row in rows)
    unexpected = sum(row["result"]["parsed"]["unexpected_content"] for row in rows)
    latencies = [row["result"]["response_metrics"]["wall_seconds"] for row in rows]
    return {
        "case_count": total,
        "parse_success_rate": _rate(parse, total),
        "source_label_fidelity": _rate(faithful, total),
        "single_result_rate": _rate(single, total),
        "unexpected_content_rate": _rate(unexpected, total),
        "median_latency_seconds": round(statistics.median(latencies), 4),
        "p95_latency_seconds": _percentile(latencies, 0.95),
        "failure_rows": [
            {
                "case_id": row["case_id"],
                "source_label": row["source_label"],
                "parsed": row["result"]["parsed"],
                "response_message": row["result"]["response_message"],
            }
            for row in rows
            if not (
                row["result"]["parsed"]["parse_success"]
                and row["result"]["parsed"]["commitment"] == row["source_label"]
                and row["result"]["parsed"]["single_result"]
                and not row["result"]["parsed"]["unexpected_content"]
            )
        ],
    }


def evaluate_gate(summary, targets):
    checks = {
        "parse_success_rate": summary["parse_success_rate"] == targets["parse_success_rate"],
        "source_label_fidelity": summary["source_label_fidelity"] == targets["source_label_fidelity"],
        "single_result_rate": summary["single_result_rate"] == targets["single_result_rate"],
        "unexpected_content_rate": summary["unexpected_content_rate"] == targets["unexpected_content_rate"],
        "p95_latency_seconds": summary["p95_latency_seconds"] <= targets["p95_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
    }


def analyze(raw_report, config):
    targets = config["stage_1_format_probe"]["gates"]
    summaries = {carrier: summarize_carrier(raw_report, carrier) for carrier in CARRIERS}
    gates = {carrier: evaluate_gate(summary, targets) for carrier, summary in summaries.items()}
    eligible = [carrier for carrier in CARRIERS if gates[carrier]["passed"]]
    selected = min(
        eligible,
        key=lambda carrier: (summaries[carrier]["median_latency_seconds"], carrier),
        default=None,
    )
    return {
        "schema": "uruha_commitment_carrier_probe_analysis_v44",
        "evidence_status": raw_report["evidence_status"],
        "selection_rule": config["stage_1_format_probe"]["selection_rule"],
        "carriers": summaries,
        "carrier_gates": gates,
        "eligible_carriers": eligible,
        "selected_carrier": selected,
        "semantic_development_authorized": selected is not None,
        "decision": "run_v44_semantic_development" if selected else "stop_before_v44_semantic_development",
        "runtime_change_authorized": False,
        "physical_vrm_execution_enabled": False,
    }


def render_markdown(analysis):
    lines = [
        "# V44 non-semantic carrier probe",
        "",
        "| carrier | parse | label fidelity | single result | unexpected | median | p95 | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for carrier, row in analysis["carriers"].items():
        lines.append(
            f"| {carrier} | {100*row['parse_success_rate']:.1f}% | "
            f"{100*row['source_label_fidelity']:.1f}% | {100*row['single_result_rate']:.1f}% | "
            f"{100*row['unexpected_content_rate']:.1f}% | {row['median_latency_seconds']:.2f}s | "
            f"{row['p95_latency_seconds']:.2f}s | {analysis['carrier_gates'][carrier]['passed']} |"
        )
    lines.extend(
        [
            "",
            f"- Selected carrier: `{analysis['selected_carrier']}`",
            f"- Decision: `{analysis['decision']}`",
            "- This probe contains no benchmark utterance and authorizes no runtime or physical action.",
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
    raw_report = json.loads(args.raw.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    analysis = analyze(raw_report, config)
    args.json_output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({"selected_carrier": analysis["selected_carrier"], "decision": analysis["decision"]}, indent=2))


if __name__ == "__main__":
    main()
