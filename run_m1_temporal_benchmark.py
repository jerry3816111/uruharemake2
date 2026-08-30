#!/usr/bin/env python3
"""Validate or run the frozen M1 temporal behavior benchmark."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

from longitudinal_human_model.baselines import BASELINES, OllamaProvider, ProviderError, predict_baseline
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from longitudinal_human_model.temporal import build_model_input, load_dataset, validate_temporal_dataset


REPO_ROOT = Path(__file__).resolve().parent


def _resource_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "prediction_calls": len(rows),
        "model_calls": sum(row["baseline"] != "B0_PRIOR" for row in rows),
        "prompt_tokens": sum(row["runtime"]["prompt_tokens"] for row in rows),
        "completion_tokens": sum(row["runtime"]["completion_tokens"] for row in rows),
        "latency_seconds": sum(row["runtime"]["latency_seconds"] for row in rows),
        "by_baseline": {
            baseline: {
                "calls": sum(row["baseline"] == baseline for row in rows),
                "prompt_tokens": sum(
                    row["runtime"]["prompt_tokens"] for row in rows if row["baseline"] == baseline
                ),
                "completion_tokens": sum(
                    row["runtime"]["completion_tokens"] for row in rows if row["baseline"] == baseline
                ),
                "latency_seconds": sum(
                    row["runtime"]["latency_seconds"] for row in rows if row["baseline"] == baseline
                ),
            }
            for baseline in BASELINES
        },
    }


def run_benchmark(
    dataset: dict[str, Any], config: dict[str, Any], *, provider: OllamaProvider
) -> dict[str, Any]:
    if not dataset["authorizations"]["model_execution"]:
        raise PermissionError("dataset contract does not authorize model execution")
    if dataset["authorizations"]["formal_target_claim"]:
        raise PermissionError("M1 fixture runner cannot produce a formal target-person claim")
    configured = tuple(config["baselines"])
    if configured != BASELINES:
        raise ValueError(f"M1 requires exactly {BASELINES}, got {configured}")

    model_config = config["model"]
    model_name = model_config["name"]
    options = dict(model_config["options"])
    labels = list(dataset["taxonomy"]["labels"])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for sample in dataset["samples"]:
        model_input = build_model_input(dataset, sample)
        for baseline in BASELINES:
            started = time.perf_counter()
            try:
                prediction = predict_baseline(
                    baseline,
                    model_input,
                    model=model_name,
                    provider=provider,
                    options=options,
                    prior_smoothing=float(config["prior_smoothing"]),
                    rag_top_n=int(config["rag_top_n"]),
                )
            except (ProviderError, ValueError) as exc:
                failures.append(
                    {
                        "sample_id": sample["sample_id"],
                        "baseline": baseline,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                )
                continue
            rows.append(
                {
                    "sample_id": sample["sample_id"],
                    "baseline": baseline,
                    "prediction_time": sample["prediction_time"],
                    "available_history_cutoff": sample["available_history_cutoff"],
                    "actual_observed_at": sample["actual_observed_at"],
                    "actual_observed_behavior": sample["actual_observed_behavior"],
                    "acceptable_behavior_labels": sample["acceptable_behavior_labels"],
                    "annotation_confidence": sample["annotation_confidence"],
                    "probabilities": prediction["probabilities"],
                    "brief_evidence": prediction["brief_evidence"],
                    "retrieved_history_ids": prediction["retrieved_history_ids"],
                    "runtime": {
                        "prompt_sha256": prediction["prompt_sha256"],
                        "prompt_tokens": prediction["prompt_tokens"],
                        "completion_tokens": prediction["completion_tokens"],
                        "latency_seconds": prediction["latency_seconds"],
                        "total_duration_ns": prediction["total_duration_ns"],
                        "model_reported": prediction["model_reported"],
                    },
                }
            )

    expected_rows = len(dataset["samples"]) * len(BASELINES)
    status = "complete_fixture_run" if len(rows) == expected_rows and not failures else "invalid_incomplete_run"
    metrics = {}
    for baseline in BASELINES:
        baseline_rows = [row for row in rows if row["baseline"] == baseline]
        if len(baseline_rows) == len(dataset["samples"]):
            metrics[baseline] = evaluate_predictions(
                baseline_rows,
                labels,
                top_k=int(config["metrics"]["top_k"]),
                ece_bins=int(config["metrics"]["ece_bins"]),
            )
    return {
        "schema": "ilhdt_m1_result_v1",
        "status": status,
        "claim_level": "synthetic_fixture_engineering_evidence_only",
        "formal_target_claim": False,
        "limitations": [
            "The target, history, and future outcomes are synthetic fixtures.",
            "These scores do not establish prediction of Uruha or any real person.",
            "No human preference or target-person validity claim is supported.",
        ],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "model": model_name,
        "rows": rows,
        "failures": failures,
        "metrics": metrics,
        "resources": _resource_summary(rows),
        "expected_prediction_rows": expected_rows,
        "observed_prediction_rows": len(rows),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434/api/generate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dataset_path = (REPO_ROOT / args.dataset).resolve()
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    dataset = load_dataset(dataset_path)
    config = load_json(config_path)
    lock = load_json(lock_path)
    leakage_report = validate_temporal_dataset(dataset)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    validation = {
        "schema": "ilhdt_m1_validation_v1",
        "valid": not lock_errors,
        "leakage_report": leakage_report,
        "lock_errors": lock_errors,
        "dataset_sha256": sha256_file(dataset_path),
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if lock_errors:
        raise SystemExit("frozen experiment lock failed: " + "; ".join(lock_errors))
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_benchmark(
        dataset,
        config,
        provider=OllamaProvider(endpoint=args.ollama_endpoint, timeout=int(config["model"]["timeout_seconds"])),
    )
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["git"] = git_snapshot(REPO_ROOT)
    result["runtime_environment"] = runtime_snapshot()
    write_json_atomic(REPO_ROOT / args.output, result)
    print(json.dumps({
        "status": result["status"],
        "output": args.output,
        "rows": result["observed_prediction_rows"],
        "failures": len(result["failures"]),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "complete_fixture_run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
