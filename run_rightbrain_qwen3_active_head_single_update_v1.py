#!/usr/bin/env python3
"""Run the active-head Qwen3 single-update optimizer canary."""

from __future__ import annotations

import argparse
import functools
import json
import math
import resource
import statistics
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
from mlx.utils import tree_flatten

import build_rightbrain_qwen3_active_head_single_update_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_active_head_full_chain_v1 as parent_runner


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
    authorization = lock["authorization"]
    environment = common._environment()
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == prereg["local_environment"]
        and authorization["repetitions"] == list(construction.REPEATS)
        and authorization["allocated_sequence_length"] == 512
        and authorization["active_head_position_count"] == 16
        and authorization["full_transformer_layers"] == 36
        and authorization["lora_enabled_layers"] == 36
        and authorization["device"] == "gpu"
        and authorization["optimizer_contract"] == prereg["optimizer_contract"]
        and authorization["micro_steps_each"] == 1
        and authorization["optimizer_updates_each"] == 1
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def _host_parameter_snapshot(parameters):
    return {
        name: np.array(value.astype(mx.float32), copy=True)
        for name, value in tree_flatten(parameters)
    }


def _parameter_delta(before, parameters):
    square_sum = 0.0
    parameter_square_sum = 0.0
    finite_elements = 0
    total_elements = 0
    changed_elements = 0
    changed_tensors = 0
    maximum_absolute_delta = 0.0
    for name, value in tree_flatten(parameters):
        after = np.asarray(value.astype(mx.float32))
        previous = before[name]
        delta = after.astype(np.float64) - previous.astype(np.float64)
        absolute = np.abs(delta)
        square_sum += float(np.sum(delta * delta))
        previous64 = previous.astype(np.float64)
        parameter_square_sum += float(np.sum(previous64 * previous64))
        finite_elements += int(np.isfinite(delta).sum())
        total_elements += int(delta.size)
        changed = int(np.count_nonzero(delta))
        changed_elements += changed
        changed_tensors += int(changed > 0)
        if delta.size:
            maximum_absolute_delta = max(
                maximum_absolute_delta, float(np.max(absolute))
            )
    norm = math.sqrt(square_sum)
    parameter_norm = math.sqrt(parameter_square_sum)
    return {
        "l2_norm": norm,
        "pre_update_parameter_l2_norm": parameter_norm,
        "relative_l2_norm": norm / max(parameter_norm, 1e-300),
        "maximum_absolute_delta": maximum_absolute_delta,
        "changed_elements": changed_elements,
        "changed_tensors": changed_tensors,
        "finite_elements": finite_elements,
        "total_elements": total_elements,
        "all_elements_finite": finite_elements == total_elements,
    }


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 single-update execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    probe = prereg["exact_probe"]
    optimizer_contract = prereg["optimizer_contract"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, batch, source, base, adapter, position_contract = (
            parent_runner._load_contracts(prereg)
        )
        input_ids = mx.array(batch["input_ids"][None, :])
        labels = mx.array(batch["labels"][None, :])
        positions = mx.array(position_contract["positions"], dtype=mx.int32)
        objective = functools.partial(
            parent_runner._active_full_chain_loss,
            positions=positions,
        )
        before_hash = common._parameter_sha256(model.trainable_parameters())
        before_parameters = _host_parameter_snapshot(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, objective)
        pre_loss, raw_gradients = loss_and_grad(model, input_ids, labels)
        mx.eval(pre_loss, raw_gradients)
        raw_gradient = common._gradient_measurements(raw_gradients)
        clipped_gradients, raw_norm = optim.clip_grad_norm(
            raw_gradients,
            float(optimizer_contract["maximum_gradient_norm"]),
        )
        mx.eval(clipped_gradients, raw_norm)
        clipped_gradient = common._gradient_measurements(clipped_gradients)
        optimizer = optim.AdamW(
            learning_rate=float(optimizer_contract["learning_rate"]),
            betas=optimizer_contract["betas"],
            eps=float(optimizer_contract["epsilon"]),
            weight_decay=float(optimizer_contract["weight_decay"]),
            bias_correction=bool(optimizer_contract["bias_correction"]),
        )
        optimizer.update(model, clipped_gradients)
        mx.eval(model.trainable_parameters(), optimizer.state)
        post_hash = common._parameter_sha256(model.trainable_parameters())
        optimizer_state_hash = common._parameter_sha256(optimizer.state)
        delta = _parameter_delta(before_parameters, model.trainable_parameters())
        post_loss = objective(model, input_ids, labels)
        mx.eval(post_loss)
        pre_loss_value = float(pre_loss.item())
        post_loss_value = float(post_loss.item())
        optimizer_step = int(optimizer.step.item())
        if not all(math.isfinite(value) for value in (pre_loss_value, post_loss_value)):
            raise RuntimeError("Non-finite single-update loss")
        if not raw_gradient["all_elements_finite"]:
            raise RuntimeError("Non-finite raw gradient")
        if not clipped_gradient["all_elements_finite"]:
            raise RuntimeError("Non-finite clipped gradient")
        if not delta["all_elements_finite"]:
            raise RuntimeError("Non-finite parameter delta")
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_active_head_single_update_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "full_transformer_layers": 36,
                "lora_enabled_layers": 36,
                "active_head_position_count": 16,
                "optimizer": optimizer_contract,
                "optimizer_updates": optimizer_step,
                "gradient_checkpointing_enabled": False,
                "adapter_or_model_saved": False,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "batch_contract": {**prereg["batch_contract"], "source": source},
            "active_position_contract": position_contract,
            "pre_update_loss": pre_loss_value,
            "post_update_loss": post_loss_value,
            "loss_delta": post_loss_value - pre_loss_value,
            "raw_gradient": raw_gradient,
            "gradient_clipping": {
                "maximum_norm": optimizer_contract["maximum_gradient_norm"],
                "raw_norm_from_clip_operator": float(raw_norm.item()),
                "applied_scale": min(
                    1.0,
                    float(optimizer_contract["maximum_gradient_norm"])
                    / (float(raw_norm.item()) + 1e-6),
                ),
                "clipped_gradient": clipped_gradient,
            },
            "parameter_update": {
                "before_sha256": before_hash,
                "after_sha256": post_hash,
                "hash_changed": before_hash != post_hash,
                **delta,
            },
            "optimizer_state": {
                "step": optimizer_step,
                "sha256": optimizer_state_hash,
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
            "schema": "uruha_rightbrain_qwen3_active_head_single_update_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": False,
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


def _classify(checks, completed=True):
    if not completed:
        return "single_update_execution_failed"
    if not checks["all_values_finite"]:
        return "single_update_nonfinite"
    if not checks["parameter_hash_changed_and_delta_nonzero"]:
        return "single_update_did_not_mutate_parameters"
    if not checks["update_reproducible"]:
        return "single_update_not_reproducible"
    if not checks["mutation_within_bounds"]:
        return "single_update_exceeded_mutation_bounds"
    if not checks["loss_within_bound"]:
        return "single_update_loss_regressed"
    return "active_head_single_update_canary_passed"


def _measure(rows, prereg):
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    deltas = [row["parameter_update"]["l2_norm"] for row in rows]
    mean_delta = statistics.fmean(deltas)
    delta_cv = statistics.pstdev(deltas) / max(mean_delta, 1e-300)
    all_values_finite = all(
        math.isfinite(row["pre_update_loss"])
        and math.isfinite(row["post_update_loss"])
        and row["raw_gradient"]["all_elements_finite"]
        and row["gradient_clipping"]["clipped_gradient"]["all_elements_finite"]
        and row["parameter_update"]["all_elements_finite"]
        for row in rows
    )
    parameter_hash_changed = all(
        row["parameter_update"]["hash_changed"] for row in rows
    )
    delta_nonzero = min(deltas) > confirm["parameter_delta_l2_minimum_exclusive"]
    update_reproducible = (
        len({row["raw_gradient"]["sha256"] for row in rows}) == 1
        and len(
            {
                row["gradient_clipping"]["clipped_gradient"]["sha256"]
                for row in rows
            }
        )
        == 1
        and len({row["parameter_update"]["after_sha256"] for row in rows}) == 1
        and len({row["optimizer_state"]["sha256"] for row in rows}) == 1
        and delta_cv <= confirm["parameter_delta_cv_maximum"]
    )
    mutation_within_bounds = (
        max(deltas) <= confirm["parameter_delta_l2_maximum"]
        and max(row["parameter_update"]["relative_l2_norm"] for row in rows)
        <= confirm["parameter_relative_delta_maximum"]
        and max(
            row["parameter_update"]["maximum_absolute_delta"] for row in rows
        )
        <= confirm["parameter_max_absolute_delta_maximum"]
        and max(
            row["gradient_clipping"]["clipped_gradient"]["norm"] for row in rows
        )
        <= confirm["clipped_gradient_norm_maximum"]
        and all(
            row["optimizer_state"]["step"] == confirm["optimizer_step_exact"]
            for row in rows
        )
    )
    loss_within_bound = max(row["loss_delta"] for row in rows) <= confirm[
        "post_update_loss_increase_maximum"
    ]
    checks = {
        "all_values_finite": all_values_finite,
        "parameter_hash_changed_and_delta_nonzero": (
            parameter_hash_changed and delta_nonzero
        ),
        "update_reproducible": update_reproducible,
        "mutation_within_bounds": mutation_within_bounds,
        "loss_within_bound": loss_within_bound,
        "all_contracts_exact": all(
            row["base_contract"]["exact"]
            and row["adapter_contract"]["exact"]
            and row["active_position_contract"]["sha256"]
            == prereg["active_position_contract"]["sha256"]
            and row["runtime_contract"]["optimizer_updates"] == 1
            and row["runtime_contract"]["adapter_or_model_saved"] is False
            for row in rows
        ),
    }
    measurements = {
        "pre_update_losses": [row["pre_update_loss"] for row in rows],
        "post_update_losses": [row["post_update_loss"] for row in rows],
        "loss_deltas": [row["loss_delta"] for row in rows],
        "raw_gradient_norms": [row["raw_gradient"]["norm"] for row in rows],
        "clipped_gradient_norms": [
            row["gradient_clipping"]["clipped_gradient"]["norm"] for row in rows
        ],
        "clip_scales": [row["gradient_clipping"]["applied_scale"] for row in rows],
        "parameter_delta_l2_norms": deltas,
        "parameter_delta_mean": mean_delta,
        "parameter_delta_cv": delta_cv,
        "parameter_relative_l2_norms": [
            row["parameter_update"]["relative_l2_norm"] for row in rows
        ],
        "parameter_max_absolute_deltas": [
            row["parameter_update"]["maximum_absolute_delta"] for row in rows
        ],
        "changed_elements": [
            row["parameter_update"]["changed_elements"] for row in rows
        ],
        "changed_tensors": [
            row["parameter_update"]["changed_tensors"] for row in rows
        ],
        "before_parameter_hashes": [
            row["parameter_update"]["before_sha256"] for row in rows
        ],
        "after_parameter_hashes": [
            row["parameter_update"]["after_sha256"] for row in rows
        ],
        "optimizer_state_hashes": [row["optimizer_state"]["sha256"] for row in rows],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in rows],
        "durations_seconds": [row["resource"]["duration_seconds"] for row in rows],
    }
    return measurements, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 single-update execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite single-update aggregate")
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
        checks = {
            "all_values_finite": False,
            "parameter_hash_changed_and_delta_nonzero": False,
            "update_reproducible": False,
            "mutation_within_bounds": False,
            "loss_within_bound": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    result = {
        "schema": "uruha_rightbrain_qwen3_active_head_single_update_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": {
            "experiment_complete": completed,
            "passed": passed,
            "outcome": outcome,
            "short_trajectory_probe_authorized": passed,
            "authorized_next_step": (
                "preregister_short_active_head_training_trajectory_probe"
                if passed
                else "do_not_advance_active_head_training"
            ),
            "authorize_persistent_training": False,
            "authorize_persona_training": False,
            "authorize_adapter_save": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, repeat))
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 active-head 單次 optimizer update 結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 9 次全部通過：`{passed}`",
                f"- raw gradient norm：`{measurements.get('raw_gradient_norms', ['NA'])[0]}`",
                f"- clipped gradient norm：`{measurements.get('clipped_gradient_norms', ['NA'])[0]}`",
                f"- parameter delta L2：`{measurements.get('parameter_delta_l2_norms', ['NA'])[0]}`",
                f"- loss delta：`{measurements.get('loss_deltas', ['NA'])[0]}`",
                "- adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_single_update_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
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
            "pre_update_loss": row.get("pre_update_loss"),
            "post_update_loss": row.get("post_update_loss"),
            "parameter_delta_l2": row.get("parameter_update", {}).get("l2_norm"),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
