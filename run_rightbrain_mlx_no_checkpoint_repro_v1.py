#!/usr/bin/env python3
"""Run the isolated MLX no-checkpoint gradient reproducibility probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_mlx_no_checkpoint_repro_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _resolve_binding(binding):
    path = Path(binding["path"])
    return path if binding.get("scope") == "external_local" or path.is_absolute() else ROOT / path


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    expected_environment = preregistration["local_environment"]
    environment = common._environment()
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment["python_executable"] == expected_environment["python_executable"]
        and environment["python_version"] == expected_environment["python_version"]
        and environment["packages"] == expected_environment["packages"]
        and environment["pip_freeze_sha256"] == expected_environment["pip_freeze_sha256"]
        and authorization["exact_zero_update_repetitions"] == [1, 2, 3]
        and authorization["micro_steps_each"] == 1
        and authorization["gradient_accumulation"] == 1
        and authorization["optimizer_steps"] == 0
        and authorization["training_backend"] == "mlx"
        and authorization["gradient_checkpointing"] is False
        and authorization["adapter_conversion_exact"] is True
        and authorization["adapter_dropout"] == 0.0
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {
        "passed": passed,
        "bindings": bindings,
        "environment": environment,
        "lock": lock,
    }


def _disable_checkpoint(_layer):
    return None


def _configure_common():
    common.EXPERIMENT_ID = EXPERIMENT_ID
    common.DEFAULT_PREREGISTRATION = DEFAULT_PREREGISTRATION
    common.DEFAULT_EXECUTION_LOCK = DEFAULT_EXECUTION_LOCK
    common.construction = construction
    common.validate_lock = validate_lock
    common.grad_checkpoint = _disable_checkpoint


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    _configure_common()
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("MLX no-checkpoint execution lock validation failed")
    result = common.run_repeat(repeat, lock_path)
    result["execution_mode"] = "isolated_mlx_zero_update_no_checkpoint"
    if result.get("execution_success"):
        result["runtime_contract"]["gradient_checkpointing_enabled"] = False
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    construction.atomic_json(common._result_path(preregistration, repeat), result)
    return result


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    _configure_common()
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("MLX no-checkpoint execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite MLX no-checkpoint aggregate")
    repeats = [
        construction.load_json(common._result_path(preregistration, repeat))
        for repeat in range(1, 4)
    ]
    completed = all(row.get("execution_success") is True for row in repeats)
    any_oom = any(row.get("failure", {}).get("out_of_memory") is True for row in repeats)
    if completed:
        measurements, checks = common._successful_measurements(repeats, preregistration)
    else:
        measurements = {
            "successful_repeat_count": sum(
                row.get("execution_success") is True for row in repeats
            ),
            "failures": [
                row.get("failure") for row in repeats if not row.get("execution_success")
            ],
            "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in repeats],
        }
        checks = {"all_three_repetitions_complete": False}
    passed = all(checks.values())
    if passed:
        outcome = "no_checkpoint_restores_reproducible_single_step_gradients"
        next_step = "preregister_one_small_matched_no_checkpoint_mlx_training_pilot"
    elif any_oom:
        outcome = "no_checkpoint_exceeds_local_memory_budget"
        next_step = "test_selective_checkpointing_or_smaller_trainable_backend"
    else:
        outcome = "no_checkpoint_does_not_restore_reproducible_gradients"
        next_step = "isolate_mlx_kernel_buffer_or_dtype_without_checkpoint"
    result = {
        "schema": "uruha_rightbrain_mlx_no_checkpoint_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(common._result_path(preregistration, repeat))
                for repeat in range(1, 4)
            ],
        },
        "measurements": measurements,
        "checks": checks,
        "decision": {
            "passed": passed,
            "outcome": outcome,
            "mechanism_supported": passed,
            "localized_next_step": next_step,
            "authorize_training_now": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(result_json, result)
    construction.atomic_text(
        result_md,
        "\n".join(
            [
                "# RightBrain MLX 無 checkpoint 梯度結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 下一定位：`{next_step}`",
                f"- 三次執行完成：`{completed}`",
                f"- 量測：`{json.dumps(measurements, ensure_ascii=False)}`",
                "- optimizer step：`0`",
                "- production 修改：`0`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_mlx_no_checkpoint_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            result["inputs"]["preregistration"],
            result["inputs"]["execution_lock"],
            *result["inputs"]["repeats"],
            construction.file_binding(result_json),
            construction.file_binding(result_md),
        ],
        "authorization": {
            "localized_next_step": next_step,
            "model_training_in_this_experiment": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, result_lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--repeat", type=int, choices=(1, 2, 3))
    action.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    result = run_repeat(args.repeat) if args.repeat else aggregate()
    if args.repeat:
        summary = {
            "repeat": args.repeat,
            "execution_success": result["execution_success"],
        }
        if result["execution_success"]:
            summary["gradient_norm"] = result["gradient"]["norm"]
            summary["peak_memory_bytes"] = result["resource"]["mlx_peak_memory_bytes"]
        else:
            summary["failure"] = result["failure"]
    else:
        summary = {**result["decision"], **result["measurements"]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
