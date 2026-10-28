#!/usr/bin/env python3
"""Run B4/B5 and combine them with the frozen M1 B0-B3 artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from longitudinal_human_model.baselines import OllamaProvider, ProviderError
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from longitudinal_human_model.strong_baselines import (
    STRONG_BASELINES,
    history_signature,
    predict_strong_baseline,
    summarize_full_history,
)
from longitudinal_human_model.temporal import build_model_input, load_dataset, validate_temporal_dataset


REPO_ROOT = Path(__file__).resolve().parent


def _prediction_resources(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> dict[str, Any]:
    prediction_prompt = sum(row["runtime"]["prompt_tokens"] for row in rows)
    prediction_completion = sum(row["runtime"]["completion_tokens"] for row in rows)
    summary_prompt = sum(row["runtime"]["prompt_tokens"] for row in summaries)
    summary_completion = sum(row["runtime"]["completion_tokens"] for row in summaries)
    return {
        "prediction_calls": len(rows),
        "summary_calls": len(summaries),
        "model_calls": len(rows) + len(summaries),
        "prompt_tokens": prediction_prompt + summary_prompt,
        "completion_tokens": prediction_completion + summary_completion,
        "latency_seconds": sum(row["runtime"]["latency_seconds"] for row in rows)
        + sum(row["runtime"]["latency_seconds"] for row in summaries),
        "summary_runtime": {
            "calls": len(summaries),
            "prompt_tokens": summary_prompt,
            "completion_tokens": summary_completion,
            "latency_seconds": sum(row["runtime"]["latency_seconds"] for row in summaries),
        },
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
            for baseline in STRONG_BASELINES
        },
    }


def run_strong_baselines(
    dataset: dict[str, Any],
    config: dict[str, Any],
    *,
    provider,
    inherited_result: dict[str, Any],
) -> dict[str, Any]:
    if not dataset["authorizations"]["model_execution"]:
        raise PermissionError("dataset contract does not authorize model execution")
    if dataset["authorizations"]["formal_target_claim"]:
        raise PermissionError("M2 synthetic runner cannot produce a formal target-person claim")
    if tuple(config["baselines"]) != STRONG_BASELINES:
        raise ValueError(f"M2 requires exactly {STRONG_BASELINES}")
    if inherited_result.get("status") != "complete_fixture_run" or len(inherited_result.get("rows") or []) != 48:
        raise ValueError("inherited M1 artifact is not a complete 48-row fixture run")

    model = config["model"]["name"]
    options = dict(config["model"]["options"])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    summary_cache: dict[str, dict[str, Any]] = {}

    for sample in dataset["samples"]:
        model_input = build_model_input(dataset, sample)
        signature = history_signature(model_input)
        if signature not in summary_cache:
            try:
                summary_cache[signature] = summarize_full_history(
                    model_input, model=model, provider=provider, options=options
                )
            except (ProviderError, ValueError) as exc:
                failures.append(
                    {
                        "sample_id": sample["sample_id"],
                        "baseline": "B4_SUMMARY_BUILD",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        for baseline in STRONG_BASELINES:
            summary = summary_cache.get(signature)
            if baseline == "B4_FULL_HISTORY_SUMMARY" and summary is None:
                continue
            try:
                prediction = predict_strong_baseline(
                    baseline,
                    model_input,
                    summary_artifact=summary,
                    model=model,
                    provider=provider,
                    options=options,
                )
            except (ProviderError, ValueError) as exc:
                failures.append(
                    {
                        "sample_id": sample["sample_id"],
                        "baseline": baseline,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
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
                    "evidence_history_ids": prediction["evidence_history_ids"],
                    "summary_signature": signature if baseline == "B4_FULL_HISTORY_SUMMARY" else None,
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

    labels = list(dataset["taxonomy"]["labels"])
    expected = len(dataset["samples"]) * len(STRONG_BASELINES)
    new_metrics = {}
    for baseline in STRONG_BASELINES:
        baseline_rows = [row for row in rows if row["baseline"] == baseline]
        if len(baseline_rows) == len(dataset["samples"]):
            new_metrics[baseline] = evaluate_predictions(
                baseline_rows,
                labels,
                top_k=int(config["metrics"]["top_k"]),
                ece_bins=int(config["metrics"]["ece_bins"]),
            )
    combined_metrics = dict(inherited_result["metrics"])
    combined_metrics.update(new_metrics)
    summaries = list(summary_cache.values())
    status = "complete_fixture_run" if len(rows) == expected and not failures else "invalid_incomplete_run"
    return {
        "schema": "ilhdt_m2_result_v1",
        "status": status,
        "claim_level": "nonfresh_synthetic_strong_baseline_engineering_evidence_only",
        "formal_target_claim": False,
        "limitations": [
            "The target, history, and outcomes are synthetic fixtures.",
            "The samples were already processed by M1 and are not a fresh holdout.",
            "B4/B5 completion does not establish Uruha or real-person prediction.",
            "The single shared summary cache is data-dependent and its cost is reported separately.",
        ],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "model": model,
        "rows": rows,
        "summaries": summaries,
        "failures": failures,
        "metrics": new_metrics,
        "combined_b0_b5_metrics": combined_metrics,
        "resources": _prediction_resources(rows, summaries),
        "expected_prediction_rows": expected,
        "observed_prediction_rows": len(rows),
        "inherited_m1": {
            "experiment_id": config["inherited_m1"]["experiment_id"],
            "path": config["inherited_m1"]["path"],
            "sha256": config["inherited_m1"]["sha256"],
            "row_count": len(inherited_result["rows"]),
        },
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
    inherited_path = (REPO_ROOT / config["inherited_m1"]["path"]).resolve()
    inherited = load_json(inherited_path)
    leakage_report = validate_temporal_dataset(dataset)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    inherited_sha = sha256_file(inherited_path)
    if inherited_sha != config["inherited_m1"]["sha256"]:
        lock_errors.append(
            f"inherited M1 hash mismatch: expected {config['inherited_m1']['sha256']}, got {inherited_sha}"
        )
    validation = {
        "schema": "ilhdt_m2_validation_v1",
        "valid": not lock_errors,
        "leakage_report": leakage_report,
        "lock_errors": lock_errors,
        "dataset_sha256": sha256_file(dataset_path),
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
        "inherited_m1_sha256": inherited_sha,
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if lock_errors:
        raise SystemExit("frozen experiment lock failed: " + "; ".join(lock_errors))
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_strong_baselines(
        dataset,
        config,
        provider=OllamaProvider(
            endpoint=args.ollama_endpoint, timeout=int(config["model"]["timeout_seconds"])
        ),
        inherited_result=inherited,
    )
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["git"] = git_snapshot(REPO_ROOT)
    result["runtime_environment"] = runtime_snapshot()
    write_json_atomic(REPO_ROOT / args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": args.output,
                "rows": result["observed_prediction_rows"],
                "summaries": len(result["summaries"]),
                "failures": len(result["failures"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "complete_fixture_run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
