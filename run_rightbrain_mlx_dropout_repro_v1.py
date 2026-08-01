#!/usr/bin/env python3
"""Run the isolated MLX dropout-zero gradient probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_mlx_dropout_repro_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _configure_common():
    common.EXPERIMENT_ID = EXPERIMENT_ID
    common.DEFAULT_PREREGISTRATION = DEFAULT_PREREGISTRATION
    common.DEFAULT_EXECUTION_LOCK = DEFAULT_EXECUTION_LOCK


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    _configure_common()
    validation = common.validate_lock(lock_path)
    authorization = validation["lock"]["authorization"]
    validation["passed"] = (
        validation["passed"]
        and authorization["adapter_dropout"] == 0.0
        and authorization["gradient_checkpointing"] is True
    )
    return validation


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("MLX dropout-zero execution lock validation failed")
    _configure_common()
    return common.run_repeat(repeat, lock_path)


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("MLX dropout-zero execution lock validation failed")
    _configure_common()
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite MLX dropout-zero aggregate")
    repeats = [
        construction.load_json(common._result_path(preregistration, repeat))
        for repeat in range(1, 4)
    ]
    completed = all(row.get("execution_success") is True for row in repeats)
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
    result = {
        "schema": "uruha_rightbrain_mlx_dropout_repro_result_v1",
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
            "outcome": (
                "mlx_dropout_zero_restores_gradient_reproducibility"
                if passed
                else "mlx_dropout_zero_does_not_restore_gradient_reproducibility"
            ),
            "mechanism_supported": passed,
            "authorized_next_step": (
                "preregister_one_small_matched_mlx_dropout_zero_training_pilot"
                if passed
                else "reject_dropout_rng_as_sufficient_and_stop_without_new_evidence"
            ),
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
                "# RightBrain MLX dropout=0 梯度結果",
                "",
                f"- 判定：`{result['decision']['outcome']}`",
                f"- 三次執行完成：`{completed}`",
                f"- 量測：`{json.dumps(measurements, ensure_ascii=False)}`",
                "- optimizer step：`0`",
                "- production 修改：`0`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_mlx_dropout_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(result_json),
            construction.file_binding(result_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "preregister_one_small_matched_mlx_dropout_zero_training_pilot": passed,
            "model_training_in_this_experiment": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--repeat", type=int, choices=(1, 2, 3))
    action.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    result = run_repeat(args.repeat) if args.repeat else aggregate()
    if args.repeat:
        output = (
            {
                "repeat": args.repeat,
                "execution_success": True,
                "gradient_norm": result["gradient"]["norm"],
                "peak_memory_bytes": result["resource"]["mlx_peak_memory_bytes"],
            }
            if result["execution_success"]
            else {
                "repeat": args.repeat,
                "execution_success": False,
                "failure": result["failure"],
                "resource": result["resource"],
            }
        )
    else:
        output = result["decision"] | result["measurements"]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
