#!/usr/bin/env python3
"""Run frozen M7 component ablations and probability-level interventions."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from longitudinal_human_model.interventions import (
    IDENTIFIABLE_ABLATIONS,
    MASTER_ABLATIONS,
    NOT_IDENTIFIABLE_ABLATIONS,
    ablate_component,
    intervene_feature,
    intervention_effect,
    reconstruct_features,
    top_contributing_features,
)
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.predictor import predict_behavior
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from run_m5_state_transitions import expand_fixture


REPO_ROOT = Path(__file__).resolve().parent


def validate_inputs(config: Mapping[str, Any], m6: Mapping[str, Any], m5_dataset: Mapping[str, Any], m5_result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if config.get("formal_target_claim") is not False or config.get("full_m7_component_coverage_claim") is not False:
        errors.append("M7 diagnostic must refuse formal and full-component-coverage claims")
    if m6.get("status") != "complete_hypothesis_run" or not m6.get("engineering_gate_pass"):
        errors.append("inherited M6 result must be a complete engineering run")
    if tuple(config.get("master_ablation_components") or ()) != MASTER_ABLATIONS:
        errors.append("master ablation list differs from the frozen implementation contract")
    if tuple(config.get("expected_identifiable_components") or ()) != IDENTIFIABLE_ABLATIONS:
        errors.append("identifiable ablation list differs from implementation")
    if set(config.get("expected_not_identifiable_components") or ()) != set(NOT_IDENTIFIABLE_ABLATIONS):
        errors.append("not-identifiable list differs from implementation")
    if set(m6.get("predictor_features") or ()) != set(m6.get("selected_predictor_model", {}).get("feature_names") or ()):
        errors.append("M6 result predictor feature contract is inconsistent")
    examples = {item.example_id: item for item in expand_fixture(m5_dataset)}
    ours_rows = [row for row in m6.get("rows") or [] if row.get("condition") == "OURS_HYBRID"]
    if set(row["sample_id"] for row in ours_rows) - set(examples):
        errors.append("M6 contains an Ours sample absent from M5 fixture")
    if m5_result.get("status") != "complete_mechanism_run":
        errors.append("M5 transition result is not complete")
    return {
        "valid": not errors,
        "errors": errors,
        "ours_holdout_count": len(ours_rows),
        "predictor_feature_count": len(m6.get("predictor_features") or []),
        "master_component_count": len(MASTER_ABLATIONS),
        "identifiable_component_count": len(IDENTIFIABLE_ABLATIONS),
        "not_identifiable_component_count": len(NOT_IDENTIFIABLE_ABLATIONS),
    }


def _metric_row(sample_id: str, actual: str, prediction: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "actual_observed_behavior": actual,
        "acceptable_behavior_labels": [actual],
        "probabilities": dict(prediction["probabilities"]),
    }


def run_diagnostic(config: Mapping[str, Any], m6: Mapping[str, Any], m5_dataset: Mapping[str, Any], m5_result: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_inputs(config, m6, m5_dataset, m5_result)
    if not validation["valid"]:
        raise ValueError("invalid M7 inputs: " + "; ".join(validation["errors"]))
    model = m6["selected_predictor_model"]
    temperature = float(m6["calibration"]["selected_temperature"])
    labels = list(model["labels"])
    examples = {item.example_id: item for item in expand_fixture(m5_dataset)}
    state_dimensions = list(m5_dataset["state_dimensions"])
    transition_model = m5_result["selected_models"]["T3_HYBRID"]
    ours_rows = [row for row in m6["rows"] if row["condition"] == "OURS_HYBRID"]
    base = {row["sample_id"]: reconstruct_features(row) for row in ours_rows}

    replay_exact = True
    full_rows = []
    for row in ours_rows:
        prediction = predict_behavior(model, base[row["sample_id"]], temperature=temperature, evidence={})
        replay_exact = replay_exact and all(
            abs(prediction["probabilities"][label] - row["probabilities"][label]) < 1e-12
            for label in labels
        )
        full_rows.append(_metric_row(row["sample_id"], row["actual_observed_behavior"], prediction))
    full_metrics = evaluate_predictions(full_rows, labels, top_k=3, ece_bins=5)

    ablations: dict[str, Any] = {
        component: {"status": "not_identifiable", "reason": reason}
        for component, reason in NOT_IDENTIFIABLE_ABLATIONS.items()
    }
    changed_metric_count = 0
    for component in IDENTIFIABLE_ABLATIONS:
        rows = []
        traces = []
        for source in ours_rows:
            sample_id = source["sample_id"]
            changed = ablate_component(
                component,
                base[sample_id],
                example=examples[sample_id],
                transition_model=transition_model,
                state_dimensions=state_dimensions,
            )
            prediction = predict_behavior(model, changed, temperature=temperature, evidence={})
            rows.append(_metric_row(sample_id, source["actual_observed_behavior"], prediction))
            effect = intervention_effect(
                model,
                base[sample_id],
                changed,
                temperature=temperature,
                actual_label=source["actual_observed_behavior"],
            )
            traces.append({"sample_id": sample_id, **effect})
        metrics = evaluate_predictions(rows, labels, top_k=3, ece_bins=5)
        metric_changed = any(
            abs(metrics[name] - full_metrics[name]) > 1e-12
            for name in ("top1_accuracy", "brier_score", "negative_log_likelihood", "expected_calibration_error")
        )
        changed_metric_count += int(metric_changed)
        ablations[component] = {
            "status": "evaluated",
            "removal_semantics": (
                "upstream values set to zero and T3 state recomputed" if component in {"memory", "personality", "llm_semantic_interpretation"}
                else "T0 previous state replaces transitioned state" if component == "temporal_dynamics"
                else "explicit transitioned-state feature group set to zero" if component == "explicit_state_transition"
                else "named state subvector set to zero"
            ),
            "metrics": metrics,
            "delta_vs_full": {
                name: metrics[name] - full_metrics[name]
                for name in ("top1_accuracy", "brier_score", "negative_log_likelihood", "expected_calibration_error")
            },
            "metric_changed": metric_changed,
            "traces": traces,
        }

    named_rows = []
    for source in ours_rows:
        sample_id = source["sample_id"]
        for intervention in config["named_interventions"]:
            changed = intervene_feature(
                base[sample_id],
                intervention["feature"],
                float(intervention["value"]),
                example=examples[sample_id],
                transition_model=transition_model,
                state_dimensions=state_dimensions,
            )
            named_rows.append({
                "sample_id": sample_id,
                "actual_observed_behavior": source["actual_observed_behavior"],
                **dict(intervention),
                **intervention_effect(
                    model, base[sample_id], changed,
                    temperature=temperature,
                    actual_label=source["actual_observed_behavior"],
                ),
            })

    faithfulness_rows = []
    for source in ours_rows:
        sample_id = source["sample_id"]
        selected = source["selected_behavior"]
        for rank, item in enumerate(top_contributing_features(
            model,
            base[sample_id],
            selected,
            count=int(config["faithfulness_top_feature_count"]),
        ), 1):
            original_value = base[sample_id][item["feature"]]
            target_value = 0.0 if original_value > 0 else 1.0
            changed = intervene_feature(
                base[sample_id], item["feature"], target_value,
                example=examples[sample_id],
                transition_model=transition_model,
                state_dimensions=state_dimensions,
            )
            effect = intervention_effect(
                model, base[sample_id], changed,
                temperature=temperature,
                actual_label=source["actual_observed_behavior"],
            )
            faithfulness_rows.append({
                "sample_id": sample_id,
                "selected_behavior": selected,
                "rank": rank,
                "feature": item["feature"],
                "model_contribution": item["contribution"],
                "original_value": original_value,
                "intervened_value": target_value,
                "absolute_selected_probability_effect": abs(effect["delta_original_selected_probability"]),
                **effect,
            })
    nonzero_rate = sum(row["absolute_selected_probability_effect"] > 1e-8 for row in faithfulness_rows) / len(faithfulness_rows)
    quiet_rows = [row for row in named_rows if row["sample_id"] == "quiet_success::holdout"]
    best_quiet = max(quiet_rows, key=lambda row: row["delta_actual_probability"])
    diagnostic_contract = config["diagnostic_hypotheses"]
    diagnostic_checks = {
        "at_least_seven_evaluated_ablation_metrics_change": changed_metric_count >= 7,
        "faithfulness_nonzero_effect_rate_at_least": nonzero_rate >= float(diagnostic_contract["faithfulness_nonzero_effect_rate_at_least"]),
        "quiet_success_has_intervention_increasing_correct_probability_by_at_least": best_quiet["delta_actual_probability"] >= float(diagnostic_contract["quiet_success_has_intervention_increasing_correct_probability_by_at_least"]),
    }
    contract = config["engineering_contract"]
    engineering = {
        "holdout_count": len(ours_rows) == int(contract["holdout_count"]),
        "master_component_count": len(ablations) == int(contract["master_component_count"]),
        "evaluated_ablation_count": sum(row["status"] == "evaluated" for row in ablations.values()) == int(contract["evaluated_ablation_count"]),
        "not_identifiable_count": sum(row["status"] == "not_identifiable" for row in ablations.values()) == int(contract["not_identifiable_count"]),
        "named_intervention_row_count": len(named_rows) == int(contract["named_intervention_row_count"]),
        "faithfulness_intervention_row_count": len(faithfulness_rows) == int(contract["faithfulness_intervention_row_count"]),
        "model_calls": int(contract["model_calls"]) == 0,
        "language_realization_performed": contract["language_realization_performed"] is False,
        "full_prediction_replay_exact": replay_exact is bool(contract["full_prediction_replay_exact"]),
    }
    return {
        "schema": "ilhdt_m7_ablation_intervention_result_v1",
        "status": "complete_diagnostic_run" if all(engineering.values()) else "failed_engineering_gate",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "full_m7_component_coverage_claim": False,
        "validation": validation,
        "full_metrics": full_metrics,
        "ablations": ablations,
        "evaluated_ablation_metric_change_count": changed_metric_count,
        "named_interventions": named_rows,
        "explanation_faithfulness": {
            "top_feature_count_per_sample": int(config["faithfulness_top_feature_count"]),
            "rows": faithfulness_rows,
            "nonzero_probability_effect_rate": nonzero_rate,
        },
        "quiet_success_diagnostic": {
            "best_named_intervention": best_quiet,
            "all_named_interventions": quiet_rows,
        },
        "diagnostic_hypothesis_checks": diagnostic_checks,
        "diagnostic_hypotheses_supported": all(diagnostic_checks.values()),
        "engineering_gate_checks": engineering,
        "engineering_gate_pass": all(engineering.values()),
        "component_coverage_complete": False,
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
    m6_path = (REPO_ROOT / config["m6_result"]["path"]).resolve()
    m5_dataset_path = (REPO_ROOT / config["m5_dataset"]["path"]).resolve()
    m5_result_path = REPO_ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json"
    m6 = load_json(m6_path)
    m5_dataset = load_json(m5_dataset_path)
    m5_result = load_json(m5_result_path)
    input_validation = validate_inputs(config, m6, m5_dataset, m5_result)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    for name, path in (("m6_result", m6_path), ("m5_dataset", m5_dataset_path)):
        actual = sha256_file(path)
        expected = config[name]["sha256"]
        if actual != expected:
            lock_errors.append(f"{name} hash mismatch: expected {expected}, got {actual}")
    validation = {
        "schema": "ilhdt_m7_validation_v1",
        "valid": input_validation["valid"] and not lock_errors,
        "inputs": input_validation,
        "lock_errors": lock_errors,
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
        "m6_result_sha256": sha256_file(m6_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M7 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_diagnostic(config, m6, m5_dataset, m5_result)
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    output_path = (REPO_ROOT / args.output).resolve()
    write_json_atomic(output_path, result)
    print(json.dumps({
        "output": str(output_path),
        "status": result["status"],
        "diagnostic_hypotheses_supported": result["diagnostic_hypotheses_supported"],
        "component_coverage_complete": result["component_coverage_complete"],
    }, indent=2))
    return 0 if result["engineering_gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
