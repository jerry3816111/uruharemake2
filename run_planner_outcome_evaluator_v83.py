#!/usr/bin/env python3
"""Run the frozen V83 deterministic evaluator calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_outcome_evaluator_v83 as v83


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "configs/planner_outcome_evaluator_v83_contract.json"
DEFAULT_OUTPUT = ROOT / "reports/planner_outcome_evaluator_v83_raw.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_artifacts(contract, root=ROOT):
    artifacts = contract["artifacts"]
    dataset_path = Path(root) / artifacts["dataset"]
    evaluator_path = Path(root) / artifacts["evaluator"]
    checks = {
        "dataset_sha256_match": v83.file_sha256(dataset_path) == artifacts["dataset_sha256"],
        "evaluator_sha256_match": v83.file_sha256(evaluator_path) == artifacts["evaluator_sha256"],
    }
    if not all(checks.values()):
        raise ValueError(f"V83 frozen artifact mismatch: {checks}")
    return dataset_path, checks


def run_calibration(contract_path=DEFAULT_CONTRACT, output_path=DEFAULT_OUTPUT, root=ROOT):
    contract_path = Path(contract_path)
    contract = load_json(contract_path)
    dataset_path, artifact_checks = validate_artifacts(contract, root=root)
    dataset = load_json(dataset_path)
    rows = v83.evaluate_calibration(dataset)
    rerun_rows = v83.evaluate_calibration(dataset)
    raw = {
        "schema": "uruha_planner_outcome_evaluator_raw_v83",
        "experiment_id": contract["experiment_id"],
        "contract_sha256": v83.file_sha256(contract_path),
        "dataset_sha256": v83.file_sha256(dataset_path),
        "artifact_checks": artifact_checks,
        "dataset_metadata": {
            "schema": dataset["schema"],
            "source_type": dataset["source_type"],
            "official_benchmark_items": dataset["official_benchmark_items"],
            "benchmark_answers_present": dataset["benchmark_answers_present"],
        },
        "rows": rows,
        "deterministic_rerun_match": rows == rerun_rows,
        "production_runtime_changed": False,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw = run_calibration(args.contract, args.output)
    print(json.dumps({"rows": len(raw["rows"]), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
