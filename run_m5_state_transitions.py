#!/usr/bin/env python3
"""Run frozen M5 T0-T3 state-transition comparison on a synthetic fixture."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

from longitudinal_human_model.baselines import OllamaProvider, ProviderError
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from longitudinal_human_model.transitions import (
    TRANSITION_FAMILIES,
    TransitionExample,
    design_feature_names,
    extract_event_features,
    feature_metrics,
    fit_ridge_transition,
    learned_transition,
    static_transition,
    transition_metrics,
    weighted_transition,
)


REPO_ROOT = Path(__file__).resolve().parent
GROUP_PREFIX = {
    "previous_state": "previous",
    "event_features": "event",
    "memory_signals": "memory",
    "person_parameters": "person",
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def _stable_sign(key: str) -> float:
    return 1.0 if hashlib.sha256(key.encode("utf-8")).digest()[0] % 2 else -1.0


def _perturb(
    values: Mapping[str, float],
    *,
    scenario_id: str,
    variant_id: str,
    group: str,
    magnitude: float,
) -> dict[str, float]:
    return {
        name: _clip(float(value) + magnitude * _stable_sign(f"{scenario_id}|{variant_id}|{group}|{name}"))
        for name, value in values.items()
    }


def _oracle_next_state(
    previous: Mapping[str, float],
    event: Mapping[str, float],
    memory: Mapping[str, float],
    person: Mapping[str, float],
    oracle: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    values = {"bias": 1.0}
    values.update({f"previous.{name}": value for name, value in previous.items()})
    values.update({f"event.{name}": value for name, value in event.items()})
    values.update({f"memory.{name}": value for name, value in memory.items()})
    values.update({f"person.{name}": value for name, value in person.items()})
    return {
        dimension: _clip(sum(float(weight) * float(values[name]) for name, weight in weights.items()))
        for dimension, weights in oracle.items()
    }


def expand_fixture(dataset: Mapping[str, Any]) -> list[TransitionExample]:
    examples: list[TransitionExample] = []
    oracle = dataset["synthetic_oracle"]
    deltas = dataset["variant_numeric_delta"]
    for scenario in dataset["scenarios"]:
        variants = [
            *( (f"train_{index}", "train", text) for index, text in enumerate(scenario["train_texts"], 1) ),
            ("dev", "dev", scenario["dev_text"]),
            ("holdout", "holdout", scenario["holdout_text"]),
        ]
        for variant_id, split, text in variants:
            magnitude = float(deltas[variant_id])
            values = {
                group: _perturb(
                    scenario[group],
                    scenario_id=scenario["scenario_id"],
                    variant_id=variant_id,
                    group=group,
                    magnitude=magnitude,
                )
                for group in GROUP_PREFIX
            }
            next_state = _oracle_next_state(
                values["previous_state"],
                values["event_features"],
                values["memory_signals"],
                values["person_parameters"],
                oracle,
            )
            examples.append(TransitionExample(
                example_id=f"{scenario['scenario_id']}::{variant_id}",
                split=split,
                event_text=str(text),
                previous_state=values["previous_state"],
                event_features=values["event_features"],
                memory_signals=values["memory_signals"],
                person_parameters=values["person_parameters"],
                next_state=next_state,
            ))
    return examples


def validate_inputs(dataset: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if dataset.get("formal_target_claim") is not False or config.get("formal_target_claim") is not False:
        errors.append("M5 inputs must explicitly refuse formal target claims")
    if config.get("retry_policy") != "no_retry_no_row_fallback":
        errors.append("M5 retry policy must remain frozen as no retry/no fallback")
    dimensions = dataset.get("state_dimensions") or []
    feature_names = dataset.get("event_feature_names") or []
    memory_names = dataset.get("memory_signal_names") or []
    person_names = dataset.get("person_parameter_names") or []
    if set(dataset.get("synthetic_oracle") or {}) != set(dimensions):
        errors.append("synthetic oracle must define every state dimension exactly once")
    if set(dataset.get("t1_hand_designed_coefficients") or {}) != set(dimensions):
        errors.append("T1 coefficients must define every state dimension exactly once")
    try:
        examples = expand_fixture(dataset)
        for item in examples:
            item.validate(
                state_dimensions=dimensions,
                event_feature_names=feature_names,
                memory_signal_names=memory_names,
                person_parameter_names=person_names,
            )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"fixture expansion failed: {exc}")
        examples = []
    ids = [item.example_id for item in examples]
    texts = [item.event_text for item in examples]
    if len(ids) != len(set(ids)):
        errors.append("expanded example IDs are not unique")
    if len(texts) != len(set(texts)):
        errors.append("event text overlaps across train/dev/holdout")
    counts = Counter(item.split for item in examples)
    contract = config.get("success_contract") or {}
    expected_counts = {
        "train": int(contract.get("train_count") or -1),
        "dev": int(contract.get("dev_count") or -1),
        "holdout": int(contract.get("holdout_count") or -1),
    }
    if len(examples) != int(contract.get("expanded_example_count") or -1):
        errors.append("expanded example count differs from preregistration")
    if dict(counts) != expected_counts:
        errors.append(f"split counts differ: actual={dict(counts)}, expected={expected_counts}")
    return {
        "valid": not errors,
        "errors": errors,
        "example_count": len(examples),
        "split_counts": dict(counts),
        "event_text_overlap_count": len(texts) - len(set(texts)),
    }


def _metric_row(trace: Mapping[str, Any], example: TransitionExample) -> dict[str, Any]:
    return {
        "example_id": example.example_id,
        "previous_state": dict(example.previous_state),
        "prediction": dict(trace["next_state"]),
        "actual_next_state": dict(example.next_state),
    }


def _evaluate_family(
    family: str,
    examples: Sequence[TransitionExample],
    state_dimensions: Sequence[str],
    *,
    t1_coefficients: Mapping[str, Mapping[str, float]] | None = None,
    fitted_model: Mapping[str, Any] | None = None,
    extracted_features: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    traces = []
    metric_rows = []
    for example in examples:
        if family == "T0_STATIC":
            trace = static_transition(example, state_dimensions)
        elif family == "T1_WEIGHTED":
            trace = weighted_transition(example, state_dimensions, t1_coefficients or {})
        else:
            trace = learned_transition(
                family,
                example,
                fitted_model or {},
                state_dimensions,
                event_features=(extracted_features or {}).get(example.example_id),
                feature_source=("gold_structured_fixture" if family == "T2_LINEAR" else "qwen_event_extractor"),
            )
        traces.append(trace)
        metric_rows.append(_metric_row(trace, example))
    return {"metrics": transition_metrics(metric_rows, state_dimensions), "traces": traces}


def _select_model(
    train: Sequence[TransitionExample],
    dev: Sequence[TransitionExample],
    state_dimensions: Sequence[str],
    feature_names: Sequence[str],
    alpha_grid: Sequence[float],
    *,
    extracted_features: Mapping[str, Mapping[str, float]] | None,
    family: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = []
    for alpha in alpha_grid:
        model = fit_ridge_transition(
            train,
            state_dimensions,
            feature_names,
            ridge_alpha=float(alpha),
            extracted_features=extracted_features,
        )
        evaluation = _evaluate_family(
            family,
            dev,
            state_dimensions,
            fitted_model=model,
            extracted_features=extracted_features,
        )
        candidates.append({"alpha": float(alpha), "dev_metrics": evaluation["metrics"], "model": model})
    candidates.sort(key=lambda item: (item["dev_metrics"]["rmse"], item["alpha"]))
    return candidates[0]["model"], candidates


class FeatureExtractionFailure(RuntimeError):
    def __init__(self, example_id: str, completed: list[dict[str, Any]], cause: Exception):
        super().__init__(f"feature extraction failed at {example_id}: {cause}")
        self.example_id = example_id
        self.completed = completed
        self.cause = cause


def _extract_all(
    examples: Sequence[TransitionExample],
    feature_names: Sequence[str],
    *,
    model: str,
    provider: Callable[..., dict[str, Any]],
    options: Mapping[str, Any],
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
    table: dict[str, dict[str, float]] = {}
    records: list[dict[str, Any]] = []
    for example in examples:
        try:
            result = extract_event_features(
                example.event_text,
                feature_names,
                model=model,
                provider=provider,
                options=options,
            )
        except (ProviderError, KeyError, TypeError, ValueError) as exc:
            raise FeatureExtractionFailure(example.example_id, records, exc) from exc
        table[example.example_id] = result["features"]
        records.append({"example_id": example.example_id, "split": example.split, **result})
    return table, records


def run_experiment(
    dataset: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    provider: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    validation = validate_inputs(dataset, config)
    if not validation["valid"]:
        raise ValueError("invalid M5 inputs: " + "; ".join(validation["errors"]))
    examples = expand_fixture(dataset)
    groups = {split: [item for item in examples if item.split == split] for split in ("train", "dev", "holdout")}
    state_dimensions = dataset["state_dimensions"]
    feature_names = design_feature_names(
        state_dimensions,
        dataset["event_feature_names"],
        dataset["memory_signal_names"],
        dataset["person_parameter_names"],
    )
    extracted, extraction_records = _extract_all(
        examples,
        dataset["event_feature_names"],
        model=config["model"],
        provider=provider,
        options=config["provider_options"],
    )
    t2_model, t2_selection = _select_model(
        groups["train"], groups["dev"], state_dimensions, feature_names,
        config["ridge_alpha_grid"], extracted_features=None, family="T2_LINEAR",
    )
    t3_model, t3_selection = _select_model(
        groups["train"], groups["dev"], state_dimensions, feature_names,
        config["ridge_alpha_grid"], extracted_features=extracted, family="T3_HYBRID",
    )
    families = {
        "T0_STATIC": _evaluate_family("T0_STATIC", groups["holdout"], state_dimensions),
        "T1_WEIGHTED": _evaluate_family(
            "T1_WEIGHTED", groups["holdout"], state_dimensions,
            t1_coefficients=dataset["t1_hand_designed_coefficients"],
        ),
        "T2_LINEAR": _evaluate_family(
            "T2_LINEAR", groups["holdout"], state_dimensions, fitted_model=t2_model,
        ),
        "T3_HYBRID": _evaluate_family(
            "T3_HYBRID", groups["holdout"], state_dimensions,
            fitted_model=t3_model, extracted_features=extracted,
        ),
    }
    feature_quality = {
        split: feature_metrics(extracted, rows, dataset["event_feature_names"])
        for split, rows in groups.items()
    }
    contract = config["success_contract"]
    gates = {
        "expanded_example_count": len(examples) == int(contract["expanded_example_count"]),
        "all_holdout_rows_complete": all(
            result["metrics"]["example_count"] == len(groups["holdout"])
            for result in families.values()
        ),
        "transition_family_count": len(families) == int(contract["transition_family_count"]),
        "behavior_prediction_performed": not any(
            trace["behavior_prediction_performed"]
            for result in families.values() for trace in result["traces"]
        ),
        "language_generation_performed": not any(
            trace["language_generation_performed"]
            for result in families.values() for trace in result["traces"]
        ),
        "t2_holdout_rmse_below_t0": families["T2_LINEAR"]["metrics"]["rmse"] < families["T0_STATIC"]["metrics"]["rmse"],
        "t2_holdout_rmse_below_t1": families["T2_LINEAR"]["metrics"]["rmse"] < families["T1_WEIGHTED"]["metrics"]["rmse"],
        "t3_feature_mae_at_most": feature_quality["holdout"]["mae"] <= float(contract["t3_feature_mae_at_most"]),
        "t3_holdout_rmse_below_t0": families["T3_HYBRID"]["metrics"]["rmse"] < families["T0_STATIC"]["metrics"]["rmse"],
    }
    resource = {
        "model_call_count": len(extraction_records),
        "prompt_tokens": sum(row["prompt_tokens"] for row in extraction_records),
        "completion_tokens": sum(row["completion_tokens"] for row in extraction_records),
        "latency_seconds": sum(row["latency_seconds"] for row in extraction_records),
    }
    return {
        "schema": "ilhdt_m5_transition_result_v1",
        "status": "complete_mechanism_run" if all(gates.values()) else "failed_mechanism_gate",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "dataset_id": dataset["dataset_id"],
        "transition_contract": config["transition_contract"],
        "validation": validation,
        "split_example_ids": {split: [item.example_id for item in rows] for split, rows in groups.items()},
        "feature_extraction": {"quality": feature_quality, "records": extraction_records},
        "model_selection": {"T2_LINEAR": t2_selection, "T3_HYBRID": t3_selection},
        "selected_models": {"T2_LINEAR": t2_model, "T3_HYBRID": t3_model},
        "families": families,
        "resource_accounting": resource,
        "gate_checks": gates,
        "gate_pass": all(gates.values()),
        "limitations": list(config["non_claims"]),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dataset_path = (REPO_ROOT / args.dataset).resolve()
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    dataset = load_json(dataset_path)
    config = load_json(config_path)
    lock = load_json(lock_path)
    input_validation = validate_inputs(dataset, config)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    validation = {
        "schema": "ilhdt_m5_validation_v1",
        "valid": input_validation["valid"] and not lock_errors,
        "inputs": input_validation,
        "lock_errors": lock_errors,
        "dataset_sha256": sha256_file(dataset_path),
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M5 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    output_path = (REPO_ROOT / args.output).resolve()
    try:
        result = run_experiment(dataset, config, provider=OllamaProvider())
    except FeatureExtractionFailure as exc:
        failure = {
            "schema": "ilhdt_m5_transition_result_v1",
            "status": "provider_failed_no_retry",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "failed_example_id": exc.example_id,
            "error": str(exc.cause),
            "completed_feature_extractions": exc.completed,
            "gate_pass": False,
            "experiment_lock": lock,
            "environment": runtime_snapshot(),
            "git": git_snapshot(REPO_ROOT),
        }
        write_json_atomic(output_path, failure)
        print(json.dumps({"output": str(output_path), "status": failure["status"]}, indent=2))
        return 3
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    write_json_atomic(output_path, result)
    print(json.dumps({"output": str(output_path), "status": result["status"]}, indent=2))
    return 0 if result["gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
