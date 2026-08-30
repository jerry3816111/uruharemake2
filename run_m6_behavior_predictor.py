#!/usr/bin/env python3
"""Run M6 behavior logits, calibration, and B0-B5 comparison."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from longitudinal_human_model.baselines import BASELINES, OllamaProvider, ProviderError
from longitudinal_human_model.baselines_v1_1 import predict_baseline
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.predictor import (
    fit_softmax_classifier,
    mean_nll,
    predict_behavior,
    select_temperature,
)
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
    predict_strong_baseline,
    summarize_full_history,
)
from longitudinal_human_model.temporal import build_model_input, validate_temporal_dataset
from longitudinal_human_model.transitions import learned_transition
from run_m5_state_transitions import expand_fixture


REPO_ROOT = Path(__file__).resolve().parent
ALL_CONDITIONS = (*BASELINES, *STRONG_BASELINES, "OURS_HYBRID")


def _iso(value: datetime) -> str:
    return value.isoformat()


def _scenario_id(example_id: str) -> str:
    return example_id.split("::", 1)[0]


def materialize_temporal_dataset(
    overlay: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
) -> dict[str, Any]:
    examples = expand_fixture(m5_dataset)
    mapping = overlay["scenario_behavior_labels"]
    history_examples = [item for item in examples if item.split in {"train", "dev"}]
    holdout_examples = [item for item in examples if item.split == "holdout"]
    time_contract = overlay["time_contract"]
    history_start = datetime.fromisoformat(time_contract["history_start"])
    holdout_start = datetime.fromisoformat(time_contract["holdout_start"])
    history = []
    for index, example in enumerate(history_examples):
        event_time = history_start + timedelta(days=index * int(time_contract["history_interval_days"]))
        available_at = event_time + timedelta(minutes=int(time_contract["availability_delay_minutes"]))
        history.append({
            "history_id": f"history::{example.example_id}",
            "event_time": _iso(event_time),
            "available_at": _iso(available_at),
            "source_id": f"synthetic_source::{example.example_id}",
            "evidence_type": "synthetic_m5_overlay",
            "observable_summary": example.event_text,
            "behavior_label": mapping[_scenario_id(example.example_id)],
        })
    history_ids = [row["history_id"] for row in history]
    samples = []
    for index, example in enumerate(holdout_examples):
        prediction_time = holdout_start + timedelta(days=index * int(time_contract["holdout_interval_days"]))
        observed_at = prediction_time + timedelta(minutes=int(time_contract["outcome_delay_minutes"]))
        source_time = prediction_time + timedelta(minutes=int(time_contract["source_delay_minutes"]))
        label = mapping[_scenario_id(example.example_id)]
        samples.append({
            "sample_id": example.example_id,
            "prediction_time": _iso(prediction_time),
            "available_history_cutoff": _iso(prediction_time - timedelta(seconds=1)),
            "event_context": example.event_text,
            "participants": list(overlay["participants"][_scenario_id(example.example_id)]),
            "available_history_ids": history_ids,
            "actual_observed_behavior": label,
            "acceptable_behavior_labels": [label],
            "actual_observed_at": _iso(observed_at),
            "source_id": f"synthetic_future::{example.example_id}",
            "source_timestamp": _iso(source_time),
            "annotation_confidence": 1.0,
            "evidence_type": "synthetic_m5_overlay",
        })
    return {
        "schema": "ilhdt_temporal_dataset_v1",
        "dataset_id": overlay["dataset_id"],
        "dataset_version": overlay["dataset_version"],
        "status": "synthetic_fixture_only_not_person_evidence",
        "authorizations": {
            "model_execution": bool(overlay["model_execution_authorized"]),
            "formal_target_claim": bool(overlay["formal_target_claim"]),
        },
        "target": dict(overlay["target"]),
        "taxonomy": dict(overlay["taxonomy"]),
        "history": history,
        "samples": samples,
    }


def validate_inputs(
    overlay: Mapping[str, Any],
    config: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
    m5_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if overlay.get("formal_target_claim") is not False or config.get("formal_target_claim") is not False:
        errors.append("M6 synthetic inputs must refuse formal target claims")
    if tuple(config.get("baselines") or ()) != (*BASELINES, *STRONG_BASELINES):
        errors.append("M6 requires B0-B5 exactly once in frozen order")
    if config.get("retry_policy") != "no_retry_no_condition_fallback":
        errors.append("M6 must retain no-retry/no-fallback policy")
    scenario_ids = {_scenario_id(f"{row['scenario_id']}::x") for row in m5_dataset.get("scenarios") or []}
    if set(overlay.get("scenario_behavior_labels") or {}) != scenario_ids:
        errors.append("behavior overlay must label every M5 scenario exactly once")
    if set(overlay.get("participants") or {}) != scenario_ids:
        errors.append("behavior overlay must define participants for every scenario")
    labels = set((overlay.get("taxonomy") or {}).get("labels") or [])
    if set((overlay.get("scenario_behavior_labels") or {}).values()) != labels:
        errors.append("every behavior label must appear in scenario mapping")
    if m5_result.get("status") != "complete_mechanism_run" or not m5_result.get("gate_pass"):
        errors.append("inherited M5 result must be a complete passing mechanism run")
    try:
        temporal = materialize_temporal_dataset(overlay, m5_dataset)
        leakage = validate_temporal_dataset(temporal)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"temporal materialization failed: {exc}")
        temporal = {}
        leakage = {"valid": False}
    contract = config.get("engineering_contract") or {}
    if len(temporal.get("history") or []) != int(contract.get("history_count") or -1):
        errors.append("materialized history count differs from preregistration")
    if len(temporal.get("samples") or []) != int(contract.get("holdout_count") or -1):
        errors.append("materialized holdout count differs from preregistration")
    if leakage.get("future_leakage_violations") != int(contract.get("future_leakage_violations", -1)):
        errors.append("temporal leakage contract failed")
    return {
        "valid": not errors,
        "errors": errors,
        "history_count": len(temporal.get("history") or []),
        "holdout_count": len(temporal.get("samples") or []),
        "leakage_report": leakage,
        "materialized_dataset_sha256": hashlib.sha256(
            json.dumps(temporal, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest() if temporal else None,
    }


def _m5_feature_table(m5_result: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    return {
        str(row["example_id"]): {str(name): float(value) for name, value in row["features"].items()}
        for row in m5_result["feature_extraction"]["records"]
    }


def build_behavior_rows(
    overlay: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
    m5_result: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    extracted = _m5_feature_table(m5_result)
    transition_model = m5_result["selected_models"]["T3_HYBRID"]
    labels = overlay["scenario_behavior_labels"]
    state_dimensions = list(m5_dataset["state_dimensions"])
    predictor_features = [
        *(f"state.{name}" for name in state_dimensions),
        *(f"event.{name}" for name in m5_dataset["event_feature_names"]),
        *(f"memory.{name}" for name in m5_dataset["memory_signal_names"]),
        *(f"person.{name}" for name in m5_dataset["person_parameter_names"]),
    ]
    all_examples = expand_fixture(m5_dataset)
    prior_by_scenario = {
        scenario: [item.example_id for item in all_examples if _scenario_id(item.example_id) == scenario and item.split in {"train", "dev"}]
        for scenario in labels
    }
    rows = []
    for example in all_examples:
        transition = learned_transition(
            "T3_HYBRID",
            example,
            transition_model,
            state_dimensions,
            event_features=extracted[example.example_id],
            feature_source="frozen_m5_qwen_event_extractor",
        )
        features = {}
        features.update({f"state.{name}": value for name, value in transition["next_state"].items()})
        features.update({f"event.{name}": value for name, value in extracted[example.example_id].items()})
        features.update({f"memory.{name}": value for name, value in example.memory_signals.items()})
        features.update({f"person.{name}": value for name, value in example.person_parameters.items()})
        scenario = _scenario_id(example.example_id)
        rows.append({
            "example_id": example.example_id,
            "split": example.split,
            "behavior_label": labels[scenario],
            "features": features,
            "evidence": {
                "memory_ids": prior_by_scenario[scenario],
                "state_features": dict(transition["next_state"]),
                "event_features": dict(extracted[example.example_id]),
                "memory_signals": dict(example.memory_signals),
                "person_parameters": dict(example.person_parameters),
                "transition_family": "T3_HYBRID",
                "transition_example_id": example.example_id,
            },
        })
    return rows, predictor_features


def select_predictor_model(
    train: Sequence[Mapping[str, Any]],
    dev: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    feature_names: Sequence[str],
    predictor_config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = []
    for alpha in predictor_config["l2_alpha_grid"]:
        model = fit_softmax_classifier(
            train,
            labels,
            feature_names,
            l2_alpha=float(alpha),
            learning_rate=float(predictor_config["learning_rate"]),
            epochs=int(predictor_config["epochs"]),
        )
        candidates.append({
            "l2_alpha": float(alpha),
            "dev_negative_log_likelihood": mean_nll(dev, model, 1.0),
            "model": model,
        })
    candidates.sort(key=lambda item: (item["dev_negative_log_likelihood"], item["l2_alpha"]))
    return candidates[0]["model"], candidates


class RecordingProvider:
    def __init__(self, provider: Callable[..., dict[str, Any]]):
        self.provider = provider
        self.records: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        result = self.provider(**kwargs)
        self.records.append({
            "call_index": len(self.records) + 1,
            "prompt_sha256": hashlib.sha256(kwargs["prompt"].encode("utf-8")).hexdigest(),
            "raw_response": str(result["text"]),
            "raw_response_sha256": hashlib.sha256(str(result["text"]).encode("utf-8")).hexdigest(),
            "prompt_tokens": int(result.get("prompt_tokens") or 0),
            "completion_tokens": int(result.get("completion_tokens") or 0),
            "latency_seconds": float(result.get("latency_seconds") or 0.0),
            "model_reported": result.get("model_reported") or kwargs["model"],
        })
        return result


class BaselineExecutionFailure(RuntimeError):
    def __init__(self, sample_id: str, condition: str, records: list[dict[str, Any]], cause: Exception):
        super().__init__(f"baseline failed at {sample_id}/{condition}: {cause}")
        self.sample_id = sample_id
        self.condition = condition
        self.records = records
        self.cause = cause


def run_baselines(
    temporal: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    provider: RecordingProvider,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    model_inputs = [build_model_input(temporal, sample) for sample in temporal["samples"]]
    try:
        summary = summarize_full_history(
            model_inputs[0],
            model=config["model"],
            provider=provider,
            options=dict(config["provider_options"]),
        )
    except (ProviderError, ValueError) as exc:
        raise BaselineExecutionFailure("shared", "B4_SUMMARY", provider.records, exc) from exc
    rows = []
    sample_by_id = {sample["sample_id"]: sample for sample in temporal["samples"]}
    for model_input in model_inputs:
        sample = sample_by_id[model_input["sample_id"]]
        for condition in (*BASELINES, *STRONG_BASELINES):
            try:
                if condition in BASELINES:
                    prediction = predict_baseline(
                        condition,
                        model_input,
                        model=config["model"],
                        provider=(None if condition == "B0_PRIOR" else provider),
                        options=dict(config["provider_options"]),
                        rag_top_n=4,
                    )
                    evidence_ids = prediction.get("retrieved_history_ids") or []
                else:
                    prediction = predict_strong_baseline(
                        condition,
                        model_input,
                        summary_artifact=(summary if condition == "B4_FULL_HISTORY_SUMMARY" else None),
                        model=config["model"],
                        provider=provider,
                        options=dict(config["provider_options"]),
                    )
                    evidence_ids = prediction["evidence_history_ids"]
            except (ProviderError, ValueError) as exc:
                raise BaselineExecutionFailure(sample["sample_id"], condition, provider.records, exc) from exc
            rows.append({
                "sample_id": sample["sample_id"],
                "condition": condition,
                "prediction_time": sample["prediction_time"],
                "available_history_cutoff": sample["available_history_cutoff"],
                "actual_observed_behavior": sample["actual_observed_behavior"],
                "acceptable_behavior_labels": sample["acceptable_behavior_labels"],
                "probabilities": prediction["probabilities"],
                "brief_evidence": prediction.get("brief_evidence") or "",
                "evidence_history_ids": evidence_ids,
                "runtime": {
                    "prompt_sha256": prediction.get("prompt_sha256"),
                    "prompt_tokens": int(prediction.get("prompt_tokens") or 0),
                    "completion_tokens": int(prediction.get("completion_tokens") or 0),
                    "latency_seconds": float(prediction.get("latency_seconds") or 0.0),
                    "model_reported": prediction.get("model_reported"),
                },
                "language_realization_performed": False,
            })
    return rows, summary


def _ours_rows(
    holdout: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    temperature: float,
) -> list[dict[str, Any]]:
    rows = []
    for item in holdout:
        prediction = predict_behavior(
            model,
            item["features"],
            temperature=temperature,
            evidence=item["evidence"],
        )
        rows.append({
            "sample_id": item["example_id"],
            "condition": "OURS_HYBRID",
            "actual_observed_behavior": item["behavior_label"],
            "acceptable_behavior_labels": [item["behavior_label"]],
            "probabilities": prediction["probabilities"],
            "selected_behavior": prediction["selected_behavior"],
            "uncertainty": prediction["uncertainty"],
            "behavior_candidates": prediction["behavior_candidates"],
            "explanation": prediction["explanation"],
            "language_realization_performed": prediction["language_realization_performed"],
        })
    return rows


def _resources(
    baseline_rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    provider_records: Sequence[Mapping[str, Any]],
    m5_result: Mapping[str, Any],
    ours_cpu_seconds: float,
) -> dict[str, Any]:
    baseline_model = {
        "model_calls": len(provider_records),
        "prompt_tokens": sum(row["prompt_tokens"] for row in provider_records),
        "completion_tokens": sum(row["completion_tokens"] for row in provider_records),
        "latency_seconds": sum(row["latency_seconds"] for row in provider_records),
        "summary_calls": 1,
        "by_condition": {
            condition: {
                "prediction_calls": sum(row["condition"] == condition and row["runtime"]["prompt_sha256"] is not None for row in baseline_rows),
                "prompt_tokens": sum(row["runtime"]["prompt_tokens"] for row in baseline_rows if row["condition"] == condition),
                "completion_tokens": sum(row["runtime"]["completion_tokens"] for row in baseline_rows if row["condition"] == condition),
                "latency_seconds": sum(row["runtime"]["latency_seconds"] for row in baseline_rows if row["condition"] == condition),
            }
            for condition in (*BASELINES, *STRONG_BASELINES)
        },
        "summary_runtime": summary["runtime"],
    }
    inherited = m5_result["resource_accounting"]
    ours = {
        "m6_incremental_model_calls": 0,
        "m6_cpu_fit_and_predict_seconds": ours_cpu_seconds,
        "inclusive_inherited_m5_feature_calls": inherited["model_call_count"],
        "inclusive_prompt_tokens": inherited["prompt_tokens"],
        "inclusive_completion_tokens": inherited["completion_tokens"],
        "inclusive_feature_latency_seconds": inherited["latency_seconds"],
        "accounting_note": "Ours includes all frozen M5 Qwen feature-extraction cost; transition, classifier, calibration, and selection are local numeric computation.",
    }
    return {"fresh_b0_b5": baseline_model, "ours_inclusive": ours}


def run_experiment(
    overlay: Mapping[str, Any],
    config: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
    m5_result: Mapping[str, Any],
    *,
    provider: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    validation = validate_inputs(overlay, config, m5_dataset, m5_result)
    if not validation["valid"]:
        raise ValueError("invalid M6 inputs: " + "; ".join(validation["errors"]))
    temporal = materialize_temporal_dataset(overlay, m5_dataset)
    behavior_rows, feature_names = build_behavior_rows(overlay, m5_dataset, m5_result)
    split = {name: [row for row in behavior_rows if row["split"] == name] for name in ("train", "dev", "holdout")}
    labels = list(overlay["taxonomy"]["labels"])
    started = time.perf_counter()
    model, selection = select_predictor_model(
        split["train"], split["dev"], labels, feature_names, config["predictor"]
    )
    calibration = select_temperature(split["dev"], model, config["predictor"]["temperature_grid"])
    temperature = calibration["selected_temperature"]
    ours_rows = _ours_rows(split["holdout"], model, temperature)
    ours_cpu_seconds = time.perf_counter() - started
    recording = RecordingProvider(provider)
    baseline_rows, summary = run_baselines(temporal, config, provider=recording)
    all_rows = [*baseline_rows, *ours_rows]
    metrics = {
        condition: evaluate_predictions(
            [row for row in all_rows if row["condition"] == condition],
            labels,
            top_k=int(config["metrics"]["top_k"]),
            ece_bins=int(config["metrics"]["ece_bins"]),
        )
        for condition in ALL_CONDITIONS
    }
    baseline_names = (*BASELINES, *STRONG_BASELINES)
    best = {
        "top1_accuracy": max(metrics[name]["top1_accuracy"] for name in baseline_names),
        "brier_score": min(metrics[name]["brier_score"] for name in baseline_names),
        "negative_log_likelihood": min(metrics[name]["negative_log_likelihood"] for name in baseline_names),
    }
    lift_checks = {
        "ours_top1_at_least_best_b0_b5": metrics["OURS_HYBRID"]["top1_accuracy"] >= best["top1_accuracy"],
        "ours_brier_below_best_b0_b5": metrics["OURS_HYBRID"]["brier_score"] < best["brier_score"],
        "ours_nll_below_best_b0_b5": metrics["OURS_HYBRID"]["negative_log_likelihood"] < best["negative_log_likelihood"],
    }
    uncalibrated_dev = mean_nll(split["dev"], model, 1.0)
    calibrated_dev = mean_nll(split["dev"], model, temperature)
    contract = config["engineering_contract"]
    engineering = {
        "history_count": len(temporal["history"]) == int(contract["history_count"]),
        "holdout_count": len(temporal["samples"]) == int(contract["holdout_count"]),
        "condition_count": len(metrics) == int(contract["condition_count"]),
        "prediction_row_count": len(all_rows) == int(contract["prediction_row_count"]),
        "future_leakage_violations": validation["leakage_report"]["future_leakage_violations"] == int(contract["future_leakage_violations"]),
        "ours_probabilities_normalized": all(abs(sum(row["probabilities"].values()) - 1.0) < 1e-9 for row in ours_rows),
        "ours_explanations_are_direct_contributions": all(row["explanation"]["kind"] == "direct_model_contributions_not_posthoc_llm" for row in ours_rows),
        "language_realization_performed": not any(row["language_realization_performed"] for row in all_rows),
        "calibrated_dev_nll_not_worse_than_uncalibrated": calibrated_dev <= uncalibrated_dev + 1e-12,
    }
    return {
        "schema": "ilhdt_m6_behavior_result_v1",
        "status": "complete_hypothesis_run" if all(engineering.values()) else "failed_engineering_gate",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "dataset_id": overlay["dataset_id"],
        "validation": validation,
        "pipeline": ["transitioned_state_plus_event_memory_person", "behavior_logits", "softmax_probabilities", "temperature_calibration", "behavior_selection"],
        "predictor_features": feature_names,
        "model_selection": selection,
        "selected_predictor_model": model,
        "calibration": {
            **calibration,
            "uncalibrated_dev_nll": uncalibrated_dev,
            "calibrated_dev_nll": calibrated_dev,
        },
        "rows": all_rows,
        "metrics": metrics,
        "best_b0_b5": best,
        "predictive_lift_checks": lift_checks,
        "predictive_lift_supported": all(lift_checks.values()),
        "engineering_gate_checks": engineering,
        "engineering_gate_pass": all(engineering.values()),
        "baseline_summary": summary,
        "provider_records": recording.records,
        "resources": _resources(baseline_rows, summary, recording.records, m5_result, ours_cpu_seconds),
        "limitations": list(config["non_claims"]),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    overlay_path = (REPO_ROOT / args.overlay).resolve()
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    overlay = load_json(overlay_path)
    config = load_json(config_path)
    lock = load_json(lock_path)
    m5_dataset_path = (REPO_ROOT / overlay["references"]["m5_dataset"]["path"]).resolve()
    m5_result_path = (REPO_ROOT / overlay["references"]["m5_result"]["path"]).resolve()
    m5_dataset = load_json(m5_dataset_path)
    m5_result = load_json(m5_result_path)
    input_validation = validate_inputs(overlay, config, m5_dataset, m5_result)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    for name, path in (("m5_dataset", m5_dataset_path), ("m5_result", m5_result_path)):
        expected = overlay["references"][name]["sha256"]
        actual = sha256_file(path)
        if expected != actual:
            lock_errors.append(f"{name} hash mismatch: expected {expected}, got {actual}")
    validation = {
        "schema": "ilhdt_m6_validation_v1",
        "valid": input_validation["valid"] and not lock_errors,
        "inputs": input_validation,
        "lock_errors": lock_errors,
        "overlay_sha256": sha256_file(overlay_path),
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M6 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    output_path = (REPO_ROOT / args.output).resolve()
    try:
        result = run_experiment(
            overlay, config, m5_dataset, m5_result,
            provider=OllamaProvider(timeout=int(config["provider_timeout_seconds"])),
        )
    except BaselineExecutionFailure as exc:
        failure = {
            "schema": "ilhdt_m6_behavior_result_v1",
            "status": "provider_failed_no_retry",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "failed_sample_id": exc.sample_id,
            "failed_condition": exc.condition,
            "error": str(exc.cause),
            "completed_provider_records": exc.records,
            "engineering_gate_pass": False,
            "predictive_lift_supported": False,
            "experiment_lock": lock,
            "environment": runtime_snapshot(),
            "git": git_snapshot(REPO_ROOT),
        }
        write_json_atomic(output_path, failure)
        print(json.dumps({"output": str(output_path), "status": failure["status"]}, indent=2))
        return 3
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    write_json_atomic(output_path, result)
    print(json.dumps({"output": str(output_path), "status": result["status"], "predictive_lift_supported": result["predictive_lift_supported"]}, indent=2))
    return 0 if result["engineering_gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
