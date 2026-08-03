#!/usr/bin/env python3
"""Run the frozen 64-update Qwen3 active-head follow-up probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_qwen3_active_head_64step_v1 as construction
import run_rightbrain_qwen3_active_head_multibatch_v1 as engine


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _configure_engine():
    engine.construction = construction
    engine.EXPERIMENT_ID = EXPERIMENT_ID
    engine.DEFAULT_PREREGISTRATION = DEFAULT_PREREGISTRATION
    engine.DEFAULT_EXECUTION_LOCK = DEFAULT_EXECUTION_LOCK


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    _configure_engine()
    return engine.validate_lock(lock_path)


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    _configure_engine()
    result = engine.run_repeat(repeat, lock_path)
    if result.get("execution_success") is True:
        result["runtime_contract"]["epochs"] = 4
        construction.atomic_json(_result_path(construction.load_json(DEFAULT_PREREGISTRATION), repeat), result)
    return result


_paired_summary = engine._paired_summary


def _measure(rows, prereg):
    _configure_engine()
    measurements, checks = engine._measure(rows, prereg)
    reference = prereg["falsifiable_hypothesis"]["parent_reference"]
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    train_gains = [
        value - reference["train_mean_loss_decrease"]
        for value in measurements["train_mean_loss_decreases"]
    ]
    holdout_deltas = [
        value - reference["holdout_mean_loss_decrease"]
        for value in measurements["holdout_mean_loss_decreases"]
    ]
    parent_comparison = all(
        gain >= confirm["train_gain_over_32step_minimum"]
        and delta >= -confirm["holdout_noninferiority_margin_vs_32step"]
        for gain, delta in zip(train_gains, holdout_deltas, strict=True)
    )
    measurements.update(
        {
            "parent_32step_reference": reference,
            "train_loss_decrease_gains_vs_32step": train_gains,
            "holdout_loss_decrease_deltas_vs_32step": holdout_deltas,
        }
    )
    checks["parent_32step_gain_and_holdout_noninferiority"] = parent_comparison
    return measurements, checks


def _classify(checks, completed=True):
    base_keys = (
        "all_values_finite",
        "parameter_hash_changed_and_delta_nonzero",
        "trajectory_reproducible",
        "mutation_within_bounds",
        "train_loss_learned",
        "holdout_loss_generalized",
        "all_contracts_exact",
    )
    base = {key: checks[key] for key in base_keys}
    outcome = engine._classify(base, completed)
    remap = {
        "multibatch_execution_failed": "extended_execution_failed",
        "multibatch_nonfinite": "extended_nonfinite",
        "multibatch_did_not_mutate_parameters": "extended_did_not_mutate_parameters",
        "multibatch_not_reproducible": "extended_not_reproducible",
        "multibatch_exceeded_mutation_bounds": "extended_exceeded_mutation_bounds",
        "multibatch_train_learning_failed": "extended_train_learning_failed",
        "multibatch_holdout_generalization_failed": "extended_holdout_generalization_failed",
    }
    if outcome != "active_head_multibatch_holdout_learning_confirmed":
        return remap[outcome]
    if not checks["parent_32step_gain_and_holdout_noninferiority"]:
        return "extended_parent_gain_failed"
    return "active_head_64step_holdout_learning_confirmed"


def _failure_checks():
    return {
        "all_values_finite": False,
        "parameter_hash_changed_and_delta_nonzero": False,
        "trajectory_reproducible": False,
        "mutation_within_bounds": False,
        "train_loss_learned": False,
        "holdout_loss_generalized": False,
        "all_contracts_exact": False,
        "parent_32step_gain_and_holdout_noninferiority": False,
    }


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 64-step execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite 64-step aggregate")
    rows = [
        construction.load_json(_result_path(prereg, repeat))
        for repeat in construction.REPEATS
    ]
    completed = all(row.get("execution_success") is True for row in rows)
    if completed:
        measurements, checks = _measure(rows, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure") for row in rows if not row.get("execution_success")
            ]
        }
        checks = _failure_checks()
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    decision = {
        "experiment_complete": completed,
        "passed": passed,
        "outcome": outcome,
        "fresh_generation_probe_authorized": passed,
        "authorized_next_step": (
            "preregister_ephemeral_multibatch_fresh_generation_probe"
            if passed
            else "diagnose_active_head_64step_or_holdout_failure"
        ),
        "authorize_persistent_training": False,
        "authorize_persona_training": False,
        "authorize_adapter_save": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_active_head_64step_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": decision,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, repeat))
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
        "interpretation_limits": prereg["interpretation_limits"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 active-head 64-step 結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 3 次全部完成且通過：`{passed}`",
                f"- train mean loss decrease：`{measurements.get('train_mean_loss_decreases', ['NA'])[0]}`",
                f"- 相對 32-step train 增益：`{measurements.get('train_loss_decrease_gains_vs_32step', ['NA'])[0]}`",
                f"- holdout mean loss decrease：`{measurements.get('holdout_mean_loss_decreases', ['NA'])[0]}`",
                f"- 相對 32-step holdout 差值：`{measurements.get('holdout_loss_decrease_deltas_vs_32step', ['NA'])[0]}`",
                "- adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_64step_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": decision,
        "authorization": {
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, result_lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.repeat is not None:
            parser.error("--aggregate cannot be combined with --repeat")
        output = aggregate()["decision"]
    else:
        if args.repeat is None:
            parser.error("--repeat is required")
        row = run_repeat(args.repeat)
        output = {
            "repeat": args.repeat,
            "execution_success": row["execution_success"],
            "train_mean_loss_decrease": row.get("train_summary", {}).get(
                "mean_loss_decrease"
            ),
            "holdout_mean_loss_decrease": row.get("holdout_summary", {}).get(
                "mean_loss_decrease"
            ),
            "holdout_improved_rows": row.get("holdout_summary", {}).get(
                "improved_row_count"
            ),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
