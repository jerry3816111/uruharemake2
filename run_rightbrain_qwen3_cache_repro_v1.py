#!/usr/bin/env python3
"""Run isolated default and disabled Metal free-cache Qwen3 probes."""

from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load

import build_rightbrain_qwen3_cache_repro_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as full_runner
import run_rightbrain_qwen3_dtype_repro_v1 as dtype_runner
import run_rightbrain_qwen3_length_boundary_v1 as boundary_runner


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    environment = common._environment()
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == prereg["local_environment"]
        and authorization["cache_modes"] == list(construction.CACHE_MODES)
        and authorization["base_compute_dtype"] == construction.BASE_COMPUTE_DTYPE
        and authorization["adapter_dtype"] == "mlx.core.float32"
        and authorization["allocated_sequence_length"] == construction.ALLOCATED_LENGTH
        and authorization["full_language_model_path"] is True
        and authorization["device"] == "gpu"
        and authorization["repetitions_each"] == list(construction.REPEATS)
        and authorization["optimizer_steps"] == 0
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, cache_mode, repeat):
    prefix = prereg["result_paths"]["repeat_prefix"]
    return ROOT / f"{prefix}{cache_mode}_repeat_{repeat}.json"


def _configure_cache(cache_mode):
    original_limit = int(mx.set_cache_limit(0))
    target_limit = original_limit if cache_mode == "default_cache" else 0
    replaced_limit = int(mx.set_cache_limit(target_limit))
    return {
        "mode": cache_mode,
        "original_limit_bytes": original_limit,
        "target_limit_bytes": target_limit,
        "intermediate_limit_before_target_bytes": replaced_limit,
        "configured_before_model_load": True,
        "disabled": target_limit == 0,
    }


def run_repeat(cache_mode, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if cache_mode not in construction.CACHE_MODES:
        raise ValueError("cache mode outside preregistered values")
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 cache execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, cache_mode, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {cache_mode} repeat {repeat}")
    probe = prereg["exact_probe"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    cache_contract = _configure_cache(cache_mode)
    mx.reset_peak_memory()
    try:
        model, tokenizer = load(
            prereg["local_model_contract"]["snapshot_root"],
            tokenizer_config={"trust_remote_code": True},
        )
        mx.eval(model.parameters())
        base = full_runner._base_contract(model, prereg)
        if not base["exact"]:
            raise RuntimeError(f"Base contract mismatch: {base}")
        compute_dtype = dtype_runner._dtype_contract(
            model, construction.BASE_COMPUTE_DTYPE
        )
        if not compute_dtype["exact"]:
            raise RuntimeError(f"Compute dtype contract mismatch: {compute_dtype}")
        adapter = full_runner._initialize_adapter(model, prereg)
        if not adapter["exact"]:
            raise RuntimeError(f"Adapter contract mismatch: {adapter}")
        batch_parent = construction.load_json(
            construction.BATCH_PARENT_PREREGISTRATION
        )
        batch, source = construction.canonical_batch(tokenizer, batch_parent)
        expected = prereg["batch_contract"]
        for key, value in expected.items():
            if batch[key] != value:
                raise RuntimeError(f"Batch contract mismatch {key}: {batch[key]} != {value}")
        input_ids = mx.array(batch["input_ids"][None, :])
        labels = mx.array(batch["labels"][None, :])
        before_hash = common._parameter_sha256(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, common._completion_loss)
        (loss, token_count), gradients = loss_and_grad(model, input_ids, labels)
        mx.eval(loss, token_count, gradients)
        loss_value = float(loss.item())
        if not math.isfinite(loss_value):
            raise RuntimeError(f"Non-finite {cache_mode} loss")
        gradient = common._gradient_measurements(gradients)
        if not gradient["all_elements_finite"]:
            raise RuntimeError(f"Non-finite {cache_mode} gradient")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_cache_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "cache_mode": cache_mode,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "full_language_model_path": True,
                "gradient_checkpointing_enabled": False,
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "cache_contract": cache_contract,
            "base_contract": base,
            "compute_dtype_contract": compute_dtype,
            "adapter_contract": adapter,
            "batch_contract": {
                **expected,
                "source": source,
                "token_count_from_loss": int(token_count.item()),
            },
            "loss": loss_value,
            "gradient": gradient,
            "parameter_integrity": {
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "unchanged": before_hash == after_hash,
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_active_memory_bytes": mx.get_active_memory(),
                "mlx_cache_memory_bytes": mx.get_cache_memory(),
                "mlx_peak_memory_bytes": peak,
                "process_peak_resident_memory_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            },
            "boundaries": prereg["boundaries"],
        }
    except Exception as error:
        message = str(error)
        result = {
            "schema": "uruha_rightbrain_qwen3_cache_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "cache_mode": cache_mode,
            "repeat": repeat,
            "execution_success": False,
            "cache_contract": cache_contract,
            "failure": {
                "error_type": type(error).__name__,
                "message": message,
                "out_of_memory": "memory" in message.lower()
                or "alloc" in message.lower(),
                "nonfinite": "non-finite" in message.lower()
                or "nonfinite" in message.lower(),
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_peak_memory_bytes": mx.get_peak_memory(),
            },
            "boundaries": prereg["boundaries"],
        }
    construction.atomic_json(output_path, result)
    return result


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 cache execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite Qwen3 cache aggregate")
    rows = {
        cache_mode: [
            construction.load_json(_result_path(prereg, cache_mode, repeat))
            for repeat in construction.REPEATS
        ]
        for cache_mode in construction.CACHE_MODES
    }
    completed = all(
        row.get("execution_success") is True
        for mode_rows in rows.values()
        for row in mode_rows
    )
    metrics = {}
    stability = {cache_mode: False for cache_mode in construction.CACHE_MODES}
    checks = {"all_repetitions_complete": completed}
    if completed:
        limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        for cache_mode in construction.CACHE_MODES:
            metrics[cache_mode], stability[cache_mode] = boundary_runner._measure(
                rows[cache_mode], limits
            )
            checks[f"{cache_mode}_contracts_exact"] = all(
                row["base_contract"]["exact"]
                and row["compute_dtype_contract"]["exact"]
                and row["adapter_contract"]["exact"]
                and row["parameter_integrity"]["unchanged"]
                and row["gradient"]["all_elements_finite"]
                and row["batch_contract"]["sha256"] == prereg["batch_contract"]["sha256"]
                and row["cache_contract"]["disabled"]
                == (cache_mode == "disabled_cache")
                for row in rows[cache_mode]
            )
            checks[f"{cache_mode}_reproducible"] = stability[cache_mode]
    if not completed:
        outcome = "cache_repro_execution_failed"
        metrics["failures"] = [
            row.get("failure")
            for mode_rows in rows.values()
            for row in mode_rows
            if not row.get("execution_success")
        ]
    elif not stability["default_cache"] and stability["disabled_cache"]:
        outcome = "disabling_metal_free_cache_eliminates_observed_drift"
    elif not stability["default_cache"] and not stability["disabled_cache"]:
        outcome = "disabling_metal_free_cache_does_not_eliminate_drift"
    elif stability["default_cache"] and stability["disabled_cache"]:
        outcome = "default_cache_parent_drift_not_reproduced"
    else:
        outcome = "disabling_metal_free_cache_introduces_instability"
    next_steps = {
        "disabling_metal_free_cache_eliminates_observed_drift": (
            "preregister_cache_disabled_real_active_batch_zero_update_holdout"
        ),
        "disabling_metal_free_cache_does_not_eliminate_drift": (
            "localize_command_buffer_or_kernel_dispatch_path"
        ),
        "default_cache_parent_drift_not_reproduced": (
            "increase_default_cache_repetitions_before_allocator_claim"
        ),
        "disabling_metal_free_cache_introduces_instability": (
            "reject_cache_disable_and_localize_command_buffer_path"
        ),
        "cache_repro_execution_failed": "repair_execution_without_changing_hypothesis",
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_cache_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": metrics,
        "stability_by_cache_mode": stability,
        "checks": checks,
        "decision": {
            "experiment_complete": completed,
            "outcome": outcome,
            "authorized_next_step": next_steps[outcome],
            "authorize_cache_disabled_training": False,
            "authorize_persona_training": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, cache_mode, repeat))
                for cache_mode in construction.CACHE_MODES
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
    }
    construction.atomic_json(output_json, result)
    rows_md = [
        f"| {cache_mode} | {'穩定' if stability[cache_mode] else '不穩定'} | "
        f"{metrics.get(cache_mode, {}).get('gradient_norm_coefficient_of_variation', 'NA')} | "
        f"{metrics.get(cache_mode, {}).get('gradient_norm_max_to_min_ratio', 'NA')} |"
        for cache_mode in construction.CACHE_MODES
    ]
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 Metal free-cache 梯度重現結果",
                "",
                f"- 判定：`{outcome}`",
                "",
                "| cache mode | 十次重複判定 | gradient CV | max/min |",
                "|:---|:---:|---:|---:|",
                *rows_md,
                "",
                "- cache-disabled 正式訓練授權：`False`",
                "- 人格訓練授權：`False`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_cache_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "cache_disabled_training": False,
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-mode", choices=construction.CACHE_MODES)
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.cache_mode is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with repeat options")
        result = aggregate()
        output = result["decision"] | {"stability": result["stability_by_cache_mode"]}
    else:
        if args.cache_mode is None or args.repeat is None:
            parser.error("--cache-mode and --repeat are required")
        result = run_repeat(args.cache_mode, args.repeat)
        output = (
            {
                "cache_mode": args.cache_mode,
                "repeat": args.repeat,
                "execution_success": True,
                "loss": result["loss"],
                "gradient_norm": result["gradient"]["norm"],
                "cache_limit_bytes": result["cache_contract"]["target_limit_bytes"],
                "cache_memory_bytes": result["resource"]["mlx_cache_memory_bytes"],
                "duration_seconds": result["resource"]["duration_seconds"],
                "peak_memory_bytes": result["resource"]["mlx_peak_memory_bytes"],
            }
            if result["execution_success"]
            else {
                "cache_mode": args.cache_mode,
                "repeat": args.repeat,
                "execution_success": False,
                "failure": result["failure"],
            }
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
