#!/usr/bin/env python3
"""Add independent preference/habit variables and close M7 ablation coverage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from longitudinal_human_model.component_features import (
    PREFERENCE_FEATURES,
    augment_component_features,
    augmented_feature_names,
    fit_habit_centroids,
)
from longitudinal_human_model.interventions import MASTER_ABLATIONS, ablate_component
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.predictor import mean_nll, predict_behavior, select_temperature
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from run_m5_state_transitions import expand_fixture
from run_m6_behavior_predictor import build_behavior_rows, select_predictor_model


REPO_ROOT = Path(__file__).resolve().parent


def validate_inputs(
    config: Mapping[str, Any],
    m6: Mapping[str, Any],
    m7_first: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
    m5_result: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    errors = []
    if config.get("formal_target_claim") is not False or config.get("predictive_lift_claim_authorized") is not False:
        errors.append("M7.1 must refuse formal and predictive-lift claims")
    if m6.get("status") != "complete_hypothesis_run":
        errors.append("M6 result is not complete")
    if m7_first.get("status") != "complete_diagnostic_run" or m7_first.get("component_coverage_complete") is not False:
        errors.append("M7.1 requires the frozen incomplete-coverage M7 diagnostic")
    if m5_result.get("status") != "complete_mechanism_run":
        errors.append("M5 transition result is not complete")
    if tuple(config.get("engineering_contract", {}).keys()) == ():
        errors.append("engineering contract is missing")
    behavior_rows, base_names = build_behavior_rows(overlay, m5_dataset, m5_result)
    labels = list(overlay["taxonomy"]["labels"])
    augmented_names = augmented_feature_names(base_names, labels)
    contract = config["engineering_contract"]
    counts = {split: sum(row["split"] == split for row in behavior_rows) for split in ("train", "dev", "holdout")}
    if counts != {"train": int(contract["train_count"]), "dev": int(contract["dev_count"]), "holdout": int(contract["holdout_count"])}:
        errors.append(f"split counts differ from contract: {counts}")
    if len(base_names) != int(contract["base_feature_count"]):
        errors.append("base feature count differs")
    if len(PREFERENCE_FEATURES) != int(contract["preference_feature_count"]):
        errors.append("preference feature count differs")
    if len(labels) != int(contract["habit_feature_count"]):
        errors.append("habit feature count differs")
    if len(augmented_names) != int(contract["augmented_feature_count"]):
        errors.append("augmented feature count differs")
    return {
        "valid": not errors,
        "errors": errors,
        "split_counts": counts,
        "base_feature_count": len(base_names),
        "preference_feature_count": len(PREFERENCE_FEATURES),
        "habit_feature_count": len(labels),
        "augmented_feature_count": len(augmented_names),
    }


def _evaluate(
    rows: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    temperature: float,
    labels: Sequence[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    output = []
    for row in rows:
        prediction = predict_behavior(model, row["features"], temperature=temperature, evidence={})
        output.append({
            "sample_id": row["example_id"],
            "actual_observed_behavior": row["behavior_label"],
            "acceptable_behavior_labels": [row["behavior_label"]],
            "probabilities": prediction["probabilities"],
            "selected_behavior": prediction["selected_behavior"],
            "explanation": prediction["explanation"],
            "language_realization_performed": False,
        })
    return evaluate_predictions(output, list(labels), top_k=3, ece_bins=5), output


def run_remediation(
    config: Mapping[str, Any],
    m6: Mapping[str, Any],
    m7_first: Mapping[str, Any],
    m5_dataset: Mapping[str, Any],
    m5_result: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    validation = validate_inputs(config, m6, m7_first, m5_dataset, m5_result, overlay)
    if not validation["valid"]:
        raise ValueError("invalid M7.1 inputs: " + "; ".join(validation["errors"]))
    base_rows, base_names = build_behavior_rows(overlay, m5_dataset, m5_result)
    groups = {split: [dict(row) for row in base_rows if row["split"] == split] for split in ("train", "dev", "holdout")}
    labels = list(overlay["taxonomy"]["labels"])
    event_names = list(m5_dataset["event_feature_names"])
    centroids = fit_habit_centroids(groups["train"], labels, event_names)
    for rows in groups.values():
        for row in rows:
            row["features"] = augment_component_features(row["features"], centroids, event_names)
    feature_names = augmented_feature_names(base_names, labels)
    predictor_config = {
        **config["predictor"],
        "model_selection": "lowest_dev_nll_then_smallest_alpha",
        "calibration_selection": "lowest_dev_nll_then_lowest_temperature",
    }
    model, selection = select_predictor_model(
        groups["train"], groups["dev"], labels, feature_names, predictor_config
    )
    calibration = select_temperature(groups["dev"], model, predictor_config["temperature_grid"])
    temperature = calibration["selected_temperature"]
    full_metrics, full_rows = _evaluate(groups["holdout"], model, temperature, labels)
    examples = {item.example_id: item for item in expand_fixture(m5_dataset)}
    transition_model = m5_result["selected_models"]["T3_HYBRID"]
    state_dimensions = list(m5_dataset["state_dimensions"])
    ablations = {}
    changed_count = 0
    for component in MASTER_ABLATIONS:
        changed_rows = []
        for row in groups["holdout"]:
            features = dict(row["features"])
            if component == "preference":
                for name in PREFERENCE_FEATURES:
                    features[name] = 0.0
            elif component == "habit":
                for name in labels:
                    features[f"habit.similarity.{name}"] = 0.0
            else:
                features = ablate_component(
                    component,
                    features,
                    example=examples[row["example_id"]],
                    transition_model=transition_model,
                    state_dimensions=state_dimensions,
                )
                features = augment_component_features(features, centroids, event_names)
            changed_rows.append({**row, "features": features})
        metrics, rows = _evaluate(changed_rows, model, temperature, labels)
        metric_changed = any(
            abs(metrics[name] - full_metrics[name]) > 1e-12
            for name in ("top1_accuracy", "brier_score", "negative_log_likelihood", "expected_calibration_error")
        )
        changed_count += int(metric_changed)
        ablations[component] = {
            "status": "evaluated",
            "metrics": metrics,
            "delta_vs_full": {
                name: metrics[name] - full_metrics[name]
                for name in ("top1_accuracy", "brier_score", "negative_log_likelihood", "expected_calibration_error")
            },
            "metric_changed": metric_changed,
            "rows": rows,
        }
    diagnostics = config["diagnostic_hypotheses"]
    diagnostic_checks = {
        "preference_ablation_changes_probability_metrics": ablations["preference"]["metric_changed"],
        "habit_ablation_changes_probability_metrics": ablations["habit"]["metric_changed"],
        "at_least_eight_of_ten_ablation_metrics_change": changed_count >= 8,
    }
    contract = config["engineering_contract"]
    uncalibrated_dev = mean_nll(groups["dev"], model, 1.0)
    calibrated_dev = mean_nll(groups["dev"], model, temperature)
    engineering = {
        "train_count": len(groups["train"]) == int(contract["train_count"]),
        "dev_count": len(groups["dev"]) == int(contract["dev_count"]),
        "holdout_count": len(groups["holdout"]) == int(contract["holdout_count"]),
        "augmented_feature_count": len(feature_names) == int(contract["augmented_feature_count"]),
        "evaluated_ablation_count": len(ablations) == int(contract["evaluated_ablation_count"]),
        "not_identifiable_count": 0 == int(contract["not_identifiable_count"]),
        "model_calls": int(contract["model_calls"]) == 0,
        "language_realization_performed": not any(row["language_realization_performed"] for row in full_rows),
        "calibrated_dev_nll_not_worse_than_uncalibrated": calibrated_dev <= uncalibrated_dev + 1e-12,
    }
    return {
        "schema": "ilhdt_m7_1_component_coverage_result_v1",
        "status": "complete_component_coverage_remediation" if all(engineering.values()) else "failed_engineering_gate",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "predictive_lift_claim_authorized": False,
        "validation": validation,
        "habit_centroids": centroids,
        "preference_features": list(PREFERENCE_FEATURES),
        "habit_features": [f"habit.similarity.{label}" for label in labels],
        "feature_names": feature_names,
        "selected_predictor_model": model,
        "model_selection": selection,
        "calibration": {**calibration, "uncalibrated_dev_nll": uncalibrated_dev, "calibrated_dev_nll": calibrated_dev},
        "full_metrics": full_metrics,
        "full_rows": full_rows,
        "frozen_m6_metrics_for_context_only": m6["metrics"]["OURS_HYBRID"],
        "ablations": ablations,
        "evaluated_ablation_metric_change_count": changed_count,
        "diagnostic_hypothesis_checks": diagnostic_checks,
        "diagnostic_hypotheses_supported": all(diagnostic_checks.values()),
        "engineering_gate_checks": engineering,
        "engineering_gate_pass": all(engineering.values()),
        "component_coverage_complete": len(ablations) == len(MASTER_ABLATIONS),
        "model_calls": 0,
        "language_realization_performed": False,
        "limitations": list(config["non_claims"]),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    config = load_json(config_path)
    lock = load_json(lock_path)
    loaded = {name: load_json(REPO_ROOT / config[name]["path"]) for name in ("m6_result", "m7_first_result", "m5_dataset", "m5_result", "overlay")}
    input_validation = validate_inputs(config, loaded["m6_result"], loaded["m7_first_result"], loaded["m5_dataset"], loaded["m5_result"], loaded["overlay"])
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    for name in loaded:
        path = REPO_ROOT / config[name]["path"]
        actual = sha256_file(path)
        if actual != config[name]["sha256"]:
            lock_errors.append(f"{name} hash mismatch")
    validation = {
        "schema": "ilhdt_m7_1_validation_v1",
        "valid": input_validation["valid"] and not lock_errors,
        "inputs": input_validation,
        "lock_errors": lock_errors,
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M7.1 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_remediation(config, loaded["m6_result"], loaded["m7_first_result"], loaded["m5_dataset"], loaded["m5_result"], loaded["overlay"])
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    output_path = REPO_ROOT / args.output
    write_json_atomic(output_path, result)
    print(json.dumps({"output": str(output_path), "status": result["status"], "component_coverage_complete": result["component_coverage_complete"], "diagnostic_hypotheses_supported": result["diagnostic_hypotheses_supported"]}, indent=2))
    return 0 if result["engineering_gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
