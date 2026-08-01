#!/usr/bin/env python3
"""Compare one official Qwen3 LoRA block backward on MLX CPU and Metal."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import statistics
import time
from itertools import combinations, product
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm.models.base import create_attention_mask

import build_rightbrain_qwen3_block_backend_repro_v1 as construction
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
        bindings.append({**binding, "actual_sha256": actual, "match": actual == binding["sha256"]})
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    environment = common._environment()
    expected = preregistration["local_environment"]
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == expected
        and authorization["devices"] == ["cpu", "gpu"]
        and authorization["exact_zero_update_repetitions_each"] == [1, 2, 3]
        and authorization["micro_steps_each"] == 1
        and authorization["optimizer_steps"] == 0
        and authorization["gradient_checkpointing"] is False
        and authorization["one_official_qwen3_block"] is True
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment, "lock": lock}


def _result_path(preregistration, device, repeat):
    prefix = preregistration["result_paths"]["repeat_prefix"]
    return ROOT / f"{prefix}{device}_repeat_{repeat}.json"


def _load_model(preregistration, device):
    mx.set_default_device(mx.cpu if device == "cpu" else mx.gpu)
    model, args, selected = construction._load_official_block(
        mx.cpu if device == "cpu" else mx.gpu
    )
    expected = preregistration["block_contract"]
    actual = {
        "layer_index": 0,
        "selected_weight_tensor_count": selected,
        "parameter_count": sum(value.size for _, value in common.tree_flatten(model.parameters())),
        "dtypes": sorted({str(value.dtype) for _, value in common.tree_flatten(model.parameters())}),
        "sha256": common._parameter_sha256(model.parameters()),
    }
    actual["exact"] = all(actual[key] == expected[key] for key in expected)
    return model, args, actual


def _initialize_adapter(model, preregistration):
    contract = preregistration["adapter_contract"]
    actual = construction.initialize_adapter(
        model,
        int(contract["initialization_seed"]),
        int(contract["rank"]),
        float(contract["scale"]),
        float(contract["dropout"]),
    )
    actual["exact"] = all(actual[key] == contract[key] for key in actual)
    return actual


def _block_loss(model, hidden, mask):
    output = model(hidden, mask).astype(mx.float32)
    return mx.mean(mx.square(output))


def _failure_result(preregistration, device, repeat, started, error):
    message = str(error)
    return {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "device": device,
        "repeat": repeat,
        "execution_success": False,
        "failure": {
            "error_type": type(error).__name__,
            "message": message,
            "out_of_memory": "memory" in message.lower() or "alloc" in message.lower(),
            "nonfinite": "non-finite" in message.lower() or "nonfinite" in message.lower(),
            "contract_mismatch": "contract" in message.lower() or "hash" in message.lower(),
        },
        "resource": {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "mlx_active_memory_bytes": mx.get_active_memory(),
            "mlx_cache_memory_bytes": mx.get_cache_memory(),
            "mlx_peak_memory_bytes": mx.get_peak_memory(),
            "process_peak_resident_memory_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "boundaries": preregistration["boundaries"],
    }


def run_repeat(device, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if device not in ("cpu", "gpu"):
        raise ValueError("device must be cpu or gpu")
    if repeat not in (1, 2, 3):
        raise ValueError("repeat must be 1, 2, or 3")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 block backend execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(preregistration, device, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {device} repeat {repeat}")

    started = time.perf_counter()
    probe = preregistration["exact_probe"]
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, args, base = _load_model(preregistration, device)
        if not base["exact"]:
            raise RuntimeError(f"Block contract mismatch: {base}")
        adapter = _initialize_adapter(model, preregistration)
        if not adapter["exact"]:
            raise RuntimeError(f"Adapter contract mismatch: {adapter}")
        input_contract = preregistration["input_contract"]
        host_input, input_hash = construction.canonical_input(
            int(input_contract["shape"][1]),
            int(input_contract["shape"][2]),
            int(input_contract["seed"]),
            float(input_contract["standard_deviation"]),
        )
        if input_hash != input_contract["sha256"]:
            raise RuntimeError(f"Input contract hash mismatch: {input_hash}")
        hidden = mx.array(host_input).astype(mx.bfloat16)
        mask = create_attention_mask(hidden)
        before_hash = common._parameter_sha256(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, _block_loss)
        loss, gradients = loss_and_grad(model, hidden, mask)
        mx.eval(loss, gradients)
        loss_value = float(loss.item())
        if not math.isfinite(loss_value):
            raise RuntimeError(f"Non-finite {device} block loss at repeat {repeat}")
        gradient = common._gradient_measurements(gradients)
        if not gradient["all_elements_finite"]:
            raise RuntimeError(f"Non-finite {device} gradient elements")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_block_backend_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "device": device,
            "repeat": repeat,
            "execution_success": True,
            "runtime_contract": {
                "backend": "mlx",
                "device": str(mx.default_device()),
                "gradient_checkpointing_enabled": False,
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "environment": validation["environment"],
            "base_contract": base,
            "adapter_contract": adapter,
            "input_contract": {"sha256": input_hash, "shape": list(host_input.shape)},
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
                "process_peak_resident_memory_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            "boundaries": preregistration["boundaries"],
        }
    except Exception as error:
        result = _failure_result(preregistration, device, repeat, started, error)
    construction.atomic_json(output_path, result)
    return result


def _cosine(left, right):
    keys = sorted(set(left) | set(right))
    a = [float(left.get(key, 0.0)) for key in keys]
    b = [float(right.get(key, 0.0)) for key in keys]
    dot = sum(x * y for x, y in zip(a, b))
    return dot / max(
        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)),
        1e-300,
    )


def _device_measurements(rows, preregistration):
    norms = [row["gradient"]["norm"] for row in rows]
    cosines = [
        _cosine(left["gradient"]["profile"], right["gradient"]["profile"])
        for left, right in combinations(rows, 2)
    ]
    mean = statistics.fmean(norms)
    limits = preregistration["falsifiable_outcomes"]["within_device_reproducibility"]
    metrics = {
        "gradient_norms": norms,
        "mean_gradient_norm": mean,
        "gradient_norm_coefficient_of_variation": statistics.pstdev(norms) / max(mean, 1e-300),
        "gradient_norm_max_to_min_ratio": max(norms) / max(min(norms), 1e-300),
        "pairwise_group_profile_cosines": cosines,
        "minimum_pairwise_group_profile_cosine": min(cosines),
        "gradient_hashes": [row["gradient"]["sha256"] for row in rows],
        "gradient_hashes_identical": len({row["gradient"]["sha256"] for row in rows}) == 1,
        "losses": [row["loss"] for row in rows],
        "durations_seconds": [row["resource"]["duration_seconds"] for row in rows],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in rows],
    }
    checks = {
        "cv": metrics["gradient_norm_coefficient_of_variation"]
        <= limits["gradient_norm_coefficient_of_variation_maximum"],
        "ratio": metrics["gradient_norm_max_to_min_ratio"]
        <= limits["gradient_norm_max_to_min_ratio_maximum"],
        "profile_cosine": metrics["minimum_pairwise_group_profile_cosine"]
        >= limits["minimum_pairwise_group_profile_cosine"],
    }
    return metrics, checks, all(checks.values())


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 block backend execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite Qwen3 block backend aggregate")

    rows = {
        device: [
            construction.load_json(_result_path(preregistration, device, repeat))
            for repeat in (1, 2, 3)
        ]
        for device in ("cpu", "gpu")
    }
    completed = all(
        row.get("execution_success") is True
        for device_rows in rows.values()
        for row in device_rows
    )
    metrics = {}
    checks = {"all_six_repetitions_complete": completed}
    stable = {"cpu": False, "gpu": False}
    if completed:
        for device in ("cpu", "gpu"):
            metrics[device], device_checks, stable[device] = _device_measurements(
                rows[device], preregistration
            )
            checks[f"{device}_contracts_exact"] = all(
                row["base_contract"]["exact"]
                and row["adapter_contract"]["exact"]
                and row["input_contract"]["sha256"] == preregistration["input_contract"]["sha256"]
                and row["parameter_integrity"]["unchanged"]
                and row["gradient"]["all_elements_finite"]
                for row in rows[device]
            )
            checks[f"{device}_within_device_reproducible"] = stable[device]
            metrics[device]["checks"] = device_checks
        cross_cosines = [
            _cosine(cpu["gradient"]["profile"], gpu["gradient"]["profile"])
            for cpu, gpu in product(rows["cpu"], rows["gpu"])
        ]
        metrics["cross_device"] = {
            "mean_gradient_norm_ratio_gpu_over_cpu": metrics["gpu"]["mean_gradient_norm"]
            / max(metrics["cpu"]["mean_gradient_norm"], 1e-300),
            "minimum_group_profile_cosine": min(cross_cosines),
            "maximum_group_profile_cosine": max(cross_cosines),
        }
    else:
        metrics["failures"] = [
            row.get("failure")
            for device_rows in rows.values()
            for row in device_rows
            if not row.get("execution_success")
        ]

    key = f"{'stable' if stable['cpu'] else 'unstable'}_{'stable' if stable['gpu'] else 'unstable'}"
    classification_key = {
        "stable_unstable": "cpu_stable_gpu_unstable",
        "unstable_unstable": "cpu_unstable_gpu_unstable",
        "stable_stable": "cpu_stable_gpu_stable",
        "unstable_stable": "cpu_unstable_gpu_stable",
    }[key]
    outcome = (
        preregistration["falsifiable_outcomes"]["classifications"][classification_key]
        if completed
        else "backend_localization_execution_failed"
    )
    next_steps = {
        "metal_backend_implicated": "prepare_minimal_upstream_mlx_reproducer_before_training",
        "framework_or_probe_still_unstable": "audit_probe_and_cpu_autodiff_before_training",
        "reduced_block_does_not_reproduce_full_graph_drift": "preregister_layer_count_scaling_localization",
        "cpu_reference_invalid_or_cpu_specific_failure": "repair_cpu_reference_before_backend_claim",
        "backend_localization_execution_failed": "repair_execution_without_changing_hypothesis",
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": metrics,
        "checks": checks,
        "decision": {
            "localization_complete": completed and checks.get("cpu_contracts_exact", False) and checks.get("gpu_contracts_exact", False),
            "outcome": outcome,
            "authorized_next_step": next_steps[outcome],
            "authorize_persona_training": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(preregistration, device, repeat))
                for device in ("cpu", "gpu")
                for repeat in (1, 2, 3)
            ],
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 單層 CPU / Metal 後向定位結果",
                "",
                f"- 判定：`{outcome}`",
                f"- CPU 穩定：`{stable['cpu']}`",
                f"- Metal 穩定：`{stable['gpu']}`",
                f"- 量測：`{json.dumps(metrics, ensure_ascii=False)}`",
                "- 人格訓練授權：`False`",
                "- production 修改：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, result_lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "gpu"))
    parser.add_argument("--repeat", type=int, choices=(1, 2, 3))
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.device is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with --device/--repeat")
        result = aggregate()
        output = result["decision"] | result["measurements"]
    else:
        if args.device is None or args.repeat is None:
            parser.error("--device and --repeat are required unless --aggregate is used")
        result = run_repeat(args.device, args.repeat)
        output = (
            {
                "device": args.device,
                "repeat": args.repeat,
                "execution_success": True,
                "loss": result["loss"],
                "gradient_norm": result["gradient"]["norm"],
                "duration_seconds": result["resource"]["duration_seconds"],
            }
            if result["execution_success"]
            else {
                "device": args.device,
                "repeat": args.repeat,
                "execution_success": False,
                "failure": result["failure"],
            }
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
