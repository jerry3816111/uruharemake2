#!/usr/bin/env python3
"""Analyze the V83 deterministic outcome-evaluator calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_outcome_evaluator_v83 as v83


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "configs/planner_outcome_evaluator_v83_contract.json"
DEFAULT_RAW = ROOT / "reports/planner_outcome_evaluator_v83_raw.json"
DEFAULT_JSON = ROOT / "reports/planner_outcome_evaluator_v83.json"
DEFAULT_MD = ROOT / "reports/planner_outcome_evaluator_v83.md"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze(contract, raw, *, contract_sha256="", dataset_sha256="", expected_rows=None):
    metrics = v83.summarize_calibration(raw["rows"])
    gates = contract["advance_gates"]
    checks = {
        "artifact_checks_pass": all(raw["artifact_checks"].values()),
        "raw_contract_binding": bool(contract_sha256) and raw["contract_sha256"] == contract_sha256,
        "raw_dataset_binding": bool(dataset_sha256) and raw["dataset_sha256"] == dataset_sha256,
        "raw_rows_match_frozen_recalculation": expected_rows is not None and raw["rows"] == expected_rows,
        "valid_accept_rate": metrics["valid_accept_rate"] >= gates["valid_accept_rate_min"],
        "mutation_reject_rate": metrics["mutation_reject_rate"] >= gates["mutation_reject_rate_min"],
        "target_failure_recall": metrics["target_failure_recall"] >= gates["target_failure_recall_min"],
        "isolated_failure_rate": metrics["isolated_failure_rate"] >= gates["isolated_failure_rate_min"],
        "deterministic_rerun_match": (
            raw["deterministic_rerun_match"] is True
            if gates["deterministic_rerun_match_required"]
            else True
        ),
        "no_benchmark_items_or_answers": (
            raw["dataset_metadata"]["official_benchmark_items"] is False
            and raw["dataset_metadata"]["benchmark_answers_present"] is False
        ),
        "no_runtime_or_side_effects": (
            raw["production_runtime_changed"] is False
            and raw["production_memory_write_count"] == 0
            and raw["physical_vrm_action_count"] == 0
        ),
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_planner_outcome_evaluator_analysis_v83",
        "experiment_id": contract["experiment_id"],
        "decision": (
            contract["authorization"]["on_pass"]
            if passed
            else "stop_and_repair_outcome_evaluator_before_causal_use"
        ),
        "calibration_passed": passed,
        "metrics": metrics,
        "gate_checks": checks,
        "training_data_authorized": False,
        "production_runtime_change_authorized": False,
        "next_experiment": (
            "Apply the frozen evaluator to matched original-versus-known-defect planner interventions "
            "through the same frozen surface realization path."
            if passed
            else "Repair the failed deterministic check and repeat calibration."
        ),
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    metrics = report["metrics"]
    status = "PASS" if report["calibration_passed"] else "FAIL"
    lines = [
        "# V83 Outcome-Grounded Evaluator Calibration",
        "",
        f"- Status: **{status}**",
        f"- Decision: `{report['decision']}`",
        f"- Valid outcomes accepted: {metrics['valid_accept_count']}/{metrics['valid_case_count']} ({metrics['valid_accept_rate']:.1%})",
        f"- Known defects rejected: {metrics['mutation_reject_count']}/{metrics['mutation_count']} ({metrics['mutation_reject_rate']:.1%})",
        f"- Target defect recall: {metrics['target_failure_hit_count']}/{metrics['mutation_count']} ({metrics['target_failure_recall']:.1%})",
        f"- Isolated defect classification: {metrics['isolated_failure_count']}/{metrics['mutation_count']} ({metrics['isolated_failure_rate']:.1%})",
        "",
        "## What This Authorizes",
        "",
        "The scorer may be used only in a bounded causal planner pilot. It does not authorize training or a production runtime change.",
        "",
        "## Boundary",
        "",
        report["evidence_boundary"],
        "",
    ]
    return "\n".join(lines)


def write_report(contract_path=DEFAULT_CONTRACT, raw_path=DEFAULT_RAW, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    contract_path = Path(contract_path)
    contract = load_json(contract_path)
    dataset_path = contract_path.resolve().parents[1] / contract["artifacts"]["dataset"]
    dataset = load_json(dataset_path)
    report = analyze(
        contract,
        load_json(raw_path),
        contract_sha256=v83.file_sha256(contract_path),
        dataset_sha256=v83.file_sha256(dataset_path),
        expected_rows=v83.evaluate_calibration(dataset),
    )
    Path(json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(md_path).write_text(render_markdown(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = write_report(args.contract, args.raw, args.json, args.md)
    print(json.dumps({"decision": report["decision"], "passed": report["calibration_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
