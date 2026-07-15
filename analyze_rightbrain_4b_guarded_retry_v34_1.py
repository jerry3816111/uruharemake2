#!/usr/bin/env python3
"""Analyze the V34.1 development-only guarded retry."""

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_4b_guarded_retry_v34_1_preregistration.json"
DEFAULT_RAW = ROOT / "reports" / "rightbrain_4b_guarded_retry_v34_1_raw.json"
DEFAULT_JSON = ROOT / "reports" / "rightbrain_4b_guarded_retry_v34_1_analysis.json"
DEFAULT_MD = ROOT / "reports" / "rightbrain_4b_guarded_retry_v34_1_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _p95(values):
    values = sorted(float(value) for value in values)
    return round(values[max(0, math.ceil(0.95 * len(values)) - 1)], 4) if values else None


def analyze(raw_path=DEFAULT_RAW):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    rows = raw["rows"]
    expected = config["known_result"]["row_count"]
    if len(rows) != expected or raw.get("completed_at") is None:
        raise ValueError(f"Incomplete V34.1 guarded retry report: {len(rows)}/{expected}")
    selected_scores = [row["selected_score"] for row in rows]
    retries = [row for row in rows if row["retry"] is not None]
    recovered = [
        row
        for row in retries
        if not row["first"]["score"]["current_gate_raw_pass"]
        and row["selected_score"]["current_gate_raw_pass"]
    ]
    reason_counts = Counter(
        reason
        for score in selected_scores
        for reason in score["current_gate_rejection_reasons"]
    )
    metrics = {
        "row_count": len(rows),
        "retry_count": len(retries),
        "retry_rate": _rate(len(retries), len(rows)),
        "retry_recovery_rate": _rate(len(recovered), len(retries)),
        "effective_semantic_contract_pass_rate": _rate(
            sum(score["semantic_contract_pass"] for score in selected_scores), len(rows)
        ),
        "effective_raw_surface_gate_pass_rate": _rate(
            sum(score["current_gate_raw_pass"] for score in selected_scores), len(rows)
        ),
        "private_memory_intrusion_count": sum(
            score["private_memory_intrusion"] for score in selected_scores
        ),
        "total_latency_median_seconds": round(
            statistics.median(row["total_wall_seconds"] for row in rows), 4
        ),
        "total_latency_p95_seconds": _p95(row["total_wall_seconds"] for row in rows),
        "selected_rejection_reason_counts": dict(reason_counts),
    }
    gate = config["development_gate"]
    checks = {
        "effective_semantic_contract_pass_rate": metrics["effective_semantic_contract_pass_rate"]
        >= gate["effective_semantic_contract_pass_rate_at_least"],
        "effective_raw_surface_gate_pass_rate": metrics["effective_raw_surface_gate_pass_rate"]
        >= gate["effective_raw_surface_gate_pass_rate_at_least"],
        "private_memory_intrusion_count": metrics["private_memory_intrusion_count"]
        == gate["private_memory_intrusion_count"],
        "retry_rate": metrics["retry_rate"] <= gate["retry_rate_at_most"],
        "total_latency_median_seconds": metrics["total_latency_median_seconds"]
        <= gate["total_latency_median_seconds_at_most"],
        "total_latency_p95_seconds": metrics["total_latency_p95_seconds"]
        <= gate["total_latency_p95_seconds_at_most"],
    }
    passed = all(checks.values())
    failed_rows = [
        {
            "case_id": row["case_id"],
            "seed": row["seed"],
            "selected_source": row["selected_source"],
            "reply": row["selected_raw_reply"],
            "reasons": row["selected_score"]["current_gate_rejection_reasons"],
        }
        for row in rows
        if not row["selected_score"]["current_gate_raw_pass"]
    ]
    return {
        "schema": "uruha_rightbrain_4b_guarded_retry_analysis_v34_1",
        "evidence_status": "post_pilot_development_not_confirmation",
        "metrics": metrics,
        "gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, value in checks.items() if not value],
        },
        "failed_rows": failed_rows,
        "decision": (
            "freeze_4b_guarded_retry_and_author_fresh_confirmation_holdout"
            if passed
            else "reject_4b_guarded_retry_for_confirmation"
        ),
        "runtime_change_authorized": False,
    }


def _markdown(report):
    metrics = report["metrics"]
    return "\n".join(
        [
            "# V34.1 guarded 4B retry development result",
            "",
            "> Development evidence only; no runtime change is authorized.",
            "",
            f"- Retry rate: {100 * metrics['retry_rate']:.1f}% ({metrics['retry_count']}/{metrics['row_count']})",
            f"- Retry recovery: {100 * metrics['retry_recovery_rate']:.1f}%",
            f"- Effective semantic contract: {100 * metrics['effective_semantic_contract_pass_rate']:.1f}%",
            f"- Effective raw surface gate: {100 * metrics['effective_raw_surface_gate_pass_rate']:.1f}%",
            f"- Total latency p50/p95: {metrics['total_latency_median_seconds']:.2f}s / {metrics['total_latency_p95_seconds']:.2f}s",
            f"- Development gate: {'PASS' if report['gate']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = analyze(args.raw)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "gate": report["gate"]}, indent=2))


if __name__ == "__main__":
    main()
