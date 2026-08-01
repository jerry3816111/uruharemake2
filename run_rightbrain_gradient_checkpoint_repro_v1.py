#!/usr/bin/env python3
"""Run checkpoint-off zero-update gradient probes in isolated processes."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import statistics
import time
from itertools import combinations
from pathlib import Path

import psutil
import torch

import build_rightbrain_gradient_checkpoint_repro_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as telemetry_tools
import run_rightbrain_gradient_dropout_repro_v1 as common
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    rows = []
    for binding in lock["repo_bindings"]:
        path = ROOT / binding["path"]
        actual = construction.sha256_file(path) if path.is_file() else None
        rows.append({**binding, "actual_sha256": actual, "match": actual == binding["sha256"]})
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(row["match"] for row in rows)
        and authorization["exact_zero_update_repetitions"] == [1, 2, 3]
        and authorization["micro_steps_each"] == 8
        and authorization["optimizer_steps"] == 0
        and authorization["adapter_dropout"] == 0.08
        and authorization["gradient_checkpointing"] is False
        and authorization["driver_allocated_memory_bytes_maximum"] == 30 * 1024**3
        and not authorization["model_or_adapter_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": rows, "lock": lock}


def _result_path(preregistration, repeat):
    return ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"


def _mps_driver_memory():
    if not torch.backends.mps.is_available():
        return 0
    if hasattr(torch.mps, "driver_allocated_memory"):
        return int(torch.mps.driver_allocated_memory())
    return int(torch.mps.current_allocated_memory())


def _failure_result(preregistration, repeat, started, error, peak_rss, peak_driver):
    text = str(error)
    return {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat": repeat,
        "execution_mode": "isolated_python_process_zero_update_checkpointing_disabled",
        "execution_success": False,
        "failure": {
            "error_type": type(error).__name__,
            "message": text,
            "out_of_memory": "out of memory" in text.lower() or "memory" in text.lower(),
        },
        "resource": {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "peak_process_resident_memory_bytes": peak_rss,
            "peak_mps_driver_allocated_memory_bytes": peak_driver,
        },
        "probe": preregistration["exact_probe"],
        "boundaries": preregistration["boundaries"],
    }


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in (1, 2, 3):
        raise ValueError("repeat must be 1, 2, or 3")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Checkpoint probe requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Checkpoint probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    output_path = _result_path(preregistration, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite checkpoint repeat {repeat}")
    started = time.perf_counter()
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    peak_driver = _mps_driver_memory()
    model = None
    try:
        rows = construction.load_json(ROOT / probe["dataset"])
        tokenizer = pilot.load_tokenizer(
            {
                "local_model_contract": preregistration["local_model_contract"],
                "training_schedule": {"adapter_dropout": probe["adapter_dropout"]},
            }
        )
        dataset = pilot.FixedLengthContractDataset(
            rows, tokenizer, int(probe["fixed_allocated_sequence_length"])
        )
        pilot._seed_everything(int(probe["random_seed"]))
        model_contract = preregistration["local_model_contract"]
        model = build_model(
            model_contract["snapshot_root"],
            str(ROOT / model_contract["initial_adapter"]["path"]),
            lora_r=int(probe["adapter_rank"]),
            lora_alpha=int(probe["adapter_alpha"]),
            lora_dropout=float(probe["adapter_dropout"]),
            dtype_name="bfloat16",
        )
        model.gradient_checkpointing_disable()
        if bool(getattr(model, "is_gradient_checkpointing", False)):
            raise RuntimeError("gradient_checkpointing_disable did not take effect")
        device = pilot._device(model)
        model.train()
        model.zero_grad(set_to_none=True)
        parameters = sorted(
            (
                (name, parameter)
                for name, parameter in model.named_parameters()
                if parameter.requires_grad
            ),
            key=lambda row: row[0],
        )
        before_hash = telemetry_tools.parameter_sha256(parameters)
        losses = []
        memory_rows = []
        for micro_step, index in enumerate(probe["row_indices"], start=1):
            batch = {key: value.unsqueeze(0) for key, value in dataset[index].items()}
            loss = model(**pilot._move(batch, device)).loss
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite checkpoint-off loss at repeat {repeat} row {index}")
            losses.append(float(loss.detach().float().cpu()))
            (loss / int(probe["gradient_accumulation"])).backward()
            rss = process.memory_info().rss
            driver = _mps_driver_memory()
            peak_rss = max(peak_rss, rss)
            peak_driver = max(peak_driver, driver)
            memory_rows.append(
                {
                    "micro_step": micro_step,
                    "process_resident_memory_bytes": rss,
                    "mps_driver_allocated_memory_bytes": driver,
                }
            )
            if driver > int(probe["driver_allocated_memory_bytes_maximum"]):
                raise RuntimeError(
                    f"MPS driver memory exceeded local limit: {driver}>"
                    f"{probe['driver_allocated_memory_bytes_maximum']}"
                )
        gradients = [parameter.grad for _, parameter in parameters if parameter.grad is not None]
        mps_norms = [
            float(
                torch.nn.utils.get_total_norm(
                    gradients,
                    norm_type=2.0,
                    error_if_nonfinite=True,
                    foreach=False,
                )
                .detach()
                .float()
                .cpu()
            )
            for _ in range(3)
        ]
        cpu_norm, finite, total = common._cpu_float64_norm(parameters)
        telemetry = telemetry_tools.gradient_telemetry(parameters)
        after_hash = telemetry_tools.parameter_sha256(parameters)
        result = {
            "schema": "uruha_rightbrain_gradient_checkpoint_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_mode": "isolated_python_process_zero_update_checkpointing_disabled",
            "execution_success": True,
            "probe": probe,
            "runtime_contract": {
                "gradient_checkpointing_enabled": bool(
                    getattr(model, "is_gradient_checkpointing", False)
                ),
                "adapter_dropout": probe["adapter_dropout"],
            },
            "losses": losses,
            "mean_loss": statistics.fmean(losses),
            "gradient": {
                "mps_foreach_false_repeated_norms": mps_norms,
                "mps_foreach_false_mean_norm": statistics.fmean(mps_norms),
                "cpu_float64_norm": cpu_norm,
                "mps_vs_cpu_relative_error": abs(statistics.fmean(mps_norms) - cpu_norm)
                / max(cpu_norm, 1e-300),
                "gradient_sha256": common._gradient_sha256(parameters),
                "finite_gradient_elements": finite,
                "total_gradient_elements": total,
                "all_gradient_elements_finite": finite == total,
                "profile": telemetry["norm_by_projection_and_lora_side"],
            },
            "parameter_integrity": {
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "unchanged": before_hash == after_hash,
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "peak_process_resident_memory_bytes": peak_rss,
                "peak_mps_driver_allocated_memory_bytes": peak_driver,
                "memory_by_micro_step": memory_rows,
            },
            "boundaries": preregistration["boundaries"],
        }
    except RuntimeError as error:
        result = _failure_result(preregistration, repeat, started, error, peak_rss, peak_driver)
    construction.atomic_json(output_path, result)
    if model is not None:
        del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return result


def _successful_measurements(repeats, preregistration):
    norms = [row["gradient"]["mps_foreach_false_mean_norm"] for row in repeats]
    pair_cosines = [
        common._cosine(common._profile_vector(left), common._profile_vector(right))
        for left, right in combinations(repeats, 2)
    ]
    mean_norm = statistics.fmean(norms)
    cv = statistics.pstdev(norms) / max(mean_norm, 1e-300)
    ratio = max(norms) / max(min(norms), 1e-300)
    confirm = preregistration["falsifiable_hypothesis"]["confirm_if_all"]
    memory_limit = preregistration["exact_probe"]["driver_allocated_memory_bytes_maximum"]
    checks = {
        "all_repeats_completed": True,
        "loss_vectors_exact": all(row["losses"] == repeats[0]["losses"] for row in repeats),
        "gradient_norm_cv": cv <= confirm["gradient_norm_coefficient_of_variation_maximum"],
        "gradient_norm_ratio": ratio <= confirm["gradient_norm_max_to_min_ratio_maximum"],
        "group_profile_cosine": min(pair_cosines)
        >= confirm["minimum_pairwise_group_profile_cosine"],
        "mps_matches_cpu": all(
            row["gradient"]["mps_vs_cpu_relative_error"]
            <= confirm["mps_vs_cpu_float64_relative_error_maximum_each"]
            for row in repeats
        ),
        "all_gradients_finite": all(
            row["gradient"]["all_gradient_elements_finite"] for row in repeats
        ),
        "parameters_unchanged": all(
            row["parameter_integrity"]["unchanged"] for row in repeats
        ),
        "checkpointing_disabled": all(
            row["runtime_contract"]["gradient_checkpointing_enabled"] is False
            for row in repeats
        ),
        "driver_memory_within_local_limit": all(
            row["resource"]["peak_mps_driver_allocated_memory_bytes"] <= memory_limit
            for row in repeats
        ),
    }
    return {
        "gradient_norms": norms,
        "mean_gradient_norm": mean_norm,
        "gradient_norm_coefficient_of_variation": cv,
        "gradient_norm_max_to_min_ratio": ratio,
        "pairwise_group_profile_cosines": pair_cosines,
        "minimum_pairwise_group_profile_cosine": min(pair_cosines),
        "peak_mps_driver_allocated_memory_bytes": [
            row["resource"]["peak_mps_driver_allocated_memory_bytes"] for row in repeats
        ],
        "gradient_hashes": [row["gradient"]["gradient_sha256"] for row in repeats],
        "losses": repeats[0]["losses"],
    }, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Checkpoint probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite checkpoint aggregate")
    repeats = [
        construction.load_json(_result_path(preregistration, repeat))
        for repeat in range(1, 4)
    ]
    completed = all(row.get("execution_success") is True for row in repeats)
    if completed:
        measurements, checks = _successful_measurements(repeats, preregistration)
    else:
        measurements = {
            "successful_repeat_count": sum(row.get("execution_success") is True for row in repeats),
            "failures": [row.get("failure") for row in repeats if not row.get("execution_success")],
            "peak_mps_driver_allocated_memory_bytes": [
                row["resource"]["peak_mps_driver_allocated_memory_bytes"] for row in repeats
            ],
        }
        checks = {
            "all_repeats_completed": False,
            "no_out_of_memory_failure": not any(
                row.get("failure", {}).get("out_of_memory", False) for row in repeats
            ),
        }
    passed = all(checks.values())
    result = {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(preregistration, repeat))
                for repeat in range(1, 4)
            ],
        },
        "measurements": measurements,
        "checks": checks,
        "decision": {
            "passed": passed,
            "outcome": (
                "checkpointing_off_restores_gradient_reproducibility_within_local_limit"
                if passed
                else "checkpointing_off_does_not_provide_a_usable_reproducible_path"
            ),
            "authorized_next_step": (
                "preregister_max_norm_pilot_v3_with_checkpointing_disabled"
                if passed
                else "zero_update_dtype_or_microbatch_contract_probe_only"
            ),
            "authorize_model_training_now": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(result_json, result)
    lines = [
        "# RightBrain checkpointing=off 梯度重現結果",
        "",
        f"- 判定：`{result['decision']['outcome']}`",
        f"- 三次執行完成：`{completed}`",
        f"- 量測：`{json.dumps(measurements, ensure_ascii=False)}`",
        "- optimizer step：`0`",
        "- 正式 runtime 修改：`0`",
    ]
    construction.atomic_text(result_md, "\n".join(lines) + "\n")
    lock = {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(result_json),
            construction.file_binding(result_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "preregister_max_norm_pilot_v3_with_checkpointing_disabled": passed,
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
                "gradient_norm": result["gradient"]["mps_foreach_false_mean_norm"],
                "peak_mps_driver_allocated_memory_bytes": result["resource"][
                    "peak_mps_driver_allocated_memory_bytes"
                ],
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
