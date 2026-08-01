#!/usr/bin/env python3
"""Recover the locked pilot evaluation without rerunning completed training."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import run_rightbrain_role_curriculum_training_pilot_v1 as original


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = original.EXPERIMENT_ID
DEFAULT_AMENDMENT = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_recovery_amendment_01.json"
DEFAULT_RECOVERY_LOCK = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_recovery_lock.json"
CONDITION_RESULTS = {
    condition: ROOT / "reports" / f"rightbrain_role_curriculum_training_pilot_v1_eval_{condition}.json"
    for condition in original.CONDITIONS
}


def _training_paths(preregistration):
    schedule = preregistration["training_schedule"]["output_directories"]
    return {
        "policy_permuted_control": ROOT / schedule["policy_permuted_control"],
        "policy_aligned_treatment": ROOT / schedule["policy_aligned_treatment"],
    }


def _adapter_paths(preregistration):
    paths = _training_paths(preregistration)
    return {
        "initial_v10_reference": ROOT
        / preregistration["local_model_contract"]["initial_adapter"]["path"],
        **paths,
    }


def validate_recovery_lock(lock_path=DEFAULT_RECOVERY_LOCK):
    lock = construction.load_json(lock_path)
    rows = []
    for binding in lock["repo_bindings"]:
        path = ROOT / binding["path"]
        actual = construction.sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "actual_sha256": actual,
                "match": actual == binding["sha256"],
            }
        )
    preregistration = construction.load_json(original.DEFAULT_PREREGISTRATION)
    adapter_rows = []
    for condition, adapter_path in _adapter_paths(preregistration).items():
        expected = lock["adapter_bindings"][condition]
        config_path = adapter_path / "adapter_config.json"
        model_path = adapter_path / "adapter_model.safetensors"
        training_report_path = adapter_path / "training_run.json"
        actual_config = construction.sha256_file(config_path) if config_path.is_file() else None
        actual_model = construction.sha256_file(model_path) if model_path.is_file() else None
        actual_training_report = (
            construction.sha256_file(training_report_path)
            if training_report_path.is_file()
            else None
        )
        expected_training_report = expected.get("training_report_sha256")
        adapter_rows.append(
            {
                "condition": condition,
                "config_match": actual_config == expected["adapter_config_sha256"],
                "model_match": actual_model == expected["adapter_model_sha256"],
                "training_report_match": expected_training_report is None
                or actual_training_report == expected_training_report,
                "actual_config_sha256": actual_config,
                "actual_model_sha256": actual_model,
                "actual_training_report_sha256": actual_training_report,
            }
        )
    original_lock = original.validate_lock()
    return {
        "passed": all(row["match"] for row in rows)
        and all(
            row["config_match"]
            and row["model_match"]
            and row["training_report_match"]
            for row in adapter_rows
        )
        and original_lock["passed"]
        and lock["authorization"]["condition_isolated_evaluation_recovery"],
        "repo_bindings": rows,
        "adapter_bindings": adapter_rows,
        "original_execution_lock": original_lock,
        "lock": lock,
    }


def load_completed_training(preregistration):
    reports = {}
    for condition, path in _training_paths(preregistration).items():
        report = construction.load_json(path / "training_run.json")
        expected_model_hash = construction.sha256_file(path / "adapter_model.safetensors")
        if report["condition"] != condition:
            raise RuntimeError(f"Training report condition mismatch: {condition}")
        if report["micro_steps"] != 80 or report["optimizer_updates"] != 10:
            raise RuntimeError(f"Incomplete training schedule: {condition}")
        if report["nonfinite_events"] != 0:
            raise RuntimeError(f"Non-finite training event: {condition}")
        if report["output_adapter_model_sha256"] != expected_model_hash:
            raise RuntimeError(f"Training adapter hash mismatch: {condition}")
        reports[condition] = report
    return reports


def evaluate_one(condition, lock_path=DEFAULT_RECOVERY_LOCK):
    if condition not in original.CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Recovery evaluation requires offline local-model mode")
    validation = validate_recovery_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Recovery lock validation failed")
    output_path = CONDITION_RESULTS[condition]
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite condition result: {output_path}")
    preregistration = construction.load_json(original.DEFAULT_PREREGISTRATION)
    load_completed_training(preregistration)
    tokenizer = original.load_tokenizer(preregistration)
    holdout = construction.load_json(original.DEFAULT_HOLDOUT)
    adapter_path = _adapter_paths(preregistration)[condition]
    evaluation = original.evaluate_adapter(
        condition,
        adapter_path,
        preregistration,
        tokenizer,
        holdout,
    )
    result = {
        "schema": "uruha_rightbrain_role_curriculum_training_pilot_condition_evaluation_v1",
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "execution_mode": "fresh_python_process_after_monolithic_runner_exit",
        "inputs": {
            "recovery_amendment": construction.file_binding(DEFAULT_AMENDMENT),
            "recovery_lock": construction.file_binding(lock_path),
            "holdout": construction.file_binding(original.DEFAULT_HOLDOUT),
        },
        "evaluation": evaluation,
        "boundaries": {
            "model_training": False,
            "production_memory_access": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(output_path, result)
    return result


def aggregate(lock_path=DEFAULT_RECOVERY_LOCK):
    validation = validate_recovery_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Recovery lock validation failed")
    if original.DEFAULT_RESULT_JSON.exists() or original.DEFAULT_RESULT_MD.exists():
        raise RuntimeError("Refusing to overwrite an existing aggregate result")
    preregistration = construction.load_json(original.DEFAULT_PREREGISTRATION)
    training = load_completed_training(preregistration)
    evaluations = {}
    condition_bindings = {}
    for condition in original.CONDITIONS:
        path = CONDITION_RESULTS[condition]
        result = construction.load_json(path)
        if result["condition"] != condition:
            raise RuntimeError(f"Condition result mismatch: {condition}")
        if result["evaluation"]["fresh_generation"]["generation_count"] != 80:
            raise RuntimeError(f"Incomplete fresh generation result: {condition}")
        if result["evaluation"]["policy_discrimination"]["comparison_count"] != 40:
            raise RuntimeError(f"Incomplete policy discrimination result: {condition}")
        evaluations[condition] = result["evaluation"]
        condition_bindings[condition] = construction.file_binding(path)
    decision = original.decide(preregistration, training, evaluations)
    result = {
        "schema": "uruha_rightbrain_role_curriculum_training_pilot_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "execution_mode": "condition_isolated_evaluation_recovery_after_monolithic_exit",
        "recovery": {
            "amendment": construction.file_binding(DEFAULT_AMENDMENT),
            "lock_validation": validation,
            "condition_results": condition_bindings,
            "original_monolithic_result_written": False,
            "training_reused_without_additional_updates": True,
        },
        "training": training,
        "evaluations": evaluations,
        "decision": decision,
    }
    construction.atomic_json(original.DEFAULT_RESULT_JSON, result)
    construction.atomic_text(original.DEFAULT_RESULT_MD, original.render_result_markdown(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=original.CONDITIONS)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--recovery-lock", default=str(DEFAULT_RECOVERY_LOCK))
    args = parser.parse_args()
    if bool(args.condition) == bool(args.aggregate):
        parser.error("Choose exactly one of --condition or --aggregate")
    if args.condition:
        result = evaluate_one(args.condition, args.recovery_lock)
        metrics = result["evaluation"]
        print(
            json.dumps(
                {
                    "condition": args.condition,
                    "policy_discrimination_accuracy": metrics["policy_discrimination"][
                        "bidirectional_policy_discrimination_accuracy"
                    ],
                    "strict_candidate_gate_pass_rate": metrics["fresh_generation"][
                        "strict_candidate_gate_pass_rate"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        result = aggregate(args.recovery_lock)
        print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
