#!/usr/bin/env python3
"""Run the active-head Qwen3 short training-trajectory probe."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import resource
import statistics
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim

import build_rightbrain_qwen3_active_head_short_trajectory_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_active_head_full_chain_v1 as full_chain
import run_rightbrain_qwen3_active_head_single_update_v1 as single_update


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
        and authorization["micro_steps_each"] == construction.OPTIMIZER_UPDATES
        and authorization["optimizer_updates_each"]
        == construction.OPTIMIZER_UPDATES
        and authorization["loss_observations_each"]
        == construction.OPTIMIZER_UPDATES + 1
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["persona_training"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def _trajectory_sha256(steps, final_loss):
    payload = {
        "steps": [
            {
                "update": row["update"],
                "loss_before_update": row["loss_before_update"],
                "raw_gradient_sha256": row["raw_gradient"]["sha256"],
                "clipped_gradient_sha256": row["clipped_gradient"]["sha256"],
                "optimizer_step_after_update": row["optimizer_step_after_update"],
            }
            for row in steps
        ],
        "final_loss": final_loss,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 short-trajectory execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    probe = prereg["exact_probe"]
    optimizer_contract = prereg["optimizer_contract"]
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, batch, source, base, adapter, position_contract = (
            full_chain._load_contracts(prereg)
        )
        input_ids = mx.array(batch["input_ids"][None, :])
        labels = mx.array(batch["labels"][None, :])
        positions = mx.array(position_contract["positions"], dtype=mx.int32)
        objective = functools.partial(
            full_chain._active_full_chain_loss,
            positions=positions,
        )
        before_hash = common._parameter_sha256(model.trainable_parameters())
        before_parameters = single_update._host_parameter_snapshot(
            model.trainable_parameters()
        )
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, objective)
        optimizer = optim.AdamW(
            learning_rate=float(optimizer_contract["learning_rate"]),
            betas=optimizer_contract["betas"],
            eps=float(optimizer_contract["epsilon"]),
            weight_decay=float(optimizer_contract["weight_decay"]),
            bias_correction=bool(optimizer_contract["bias_correction"]),
        )
        steps = []
        for update in range(1, construction.OPTIMIZER_UPDATES + 1):
            loss, raw_gradients = loss_and_grad(model, input_ids, labels)
            mx.eval(loss, raw_gradients)
            loss_value = float(loss.item())
            raw_gradient = common._gradient_measurements(raw_gradients)
            clipped_gradients, raw_norm = optim.clip_grad_norm(
                raw_gradients,
                float(optimizer_contract["maximum_gradient_norm"]),
            )
            mx.eval(clipped_gradients, raw_norm)
            clipped_gradient = common._gradient_measurements(clipped_gradients)
            if not math.isfinite(loss_value):
                raise RuntimeError(f"Non-finite loss before update {update}")
            if not raw_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite raw gradient at update {update}")
            if not clipped_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite clipped gradient at update {update}")
            optimizer.update(model, clipped_gradients)
            mx.eval(model.trainable_parameters(), optimizer.state)
            optimizer_step = int(optimizer.step.item())
            if optimizer_step != update:
                raise RuntimeError(
                    f"Optimizer step drifted: expected {update}, got {optimizer_step}"
                )
            raw_norm_value = float(raw_norm.item())
            steps.append(
                {
                    "update": update,
                    "loss_before_update": loss_value,
                    "raw_gradient": raw_gradient,
                    "raw_norm_from_clip_operator": raw_norm_value,
                    "clip_scale": min(
                        1.0,
                        float(optimizer_contract["maximum_gradient_norm"])
                        / (raw_norm_value + 1e-6),
                    ),
                    "clipped_gradient": clipped_gradient,
                    "optimizer_step_after_update": optimizer_step,
                }
            )

        final_loss_array = objective(model, input_ids, labels)
        mx.eval(final_loss_array)
        final_loss = float(final_loss_array.item())
        if not math.isfinite(final_loss):
            raise RuntimeError("Non-finite final trajectory loss")
        final_hash = common._parameter_sha256(model.trainable_parameters())
        optimizer_state_hash = common._parameter_sha256(optimizer.state)
        delta = single_update._parameter_delta(
            before_parameters, model.trainable_parameters()
        )
        if not delta["all_elements_finite"]:
            raise RuntimeError("Non-finite short-trajectory parameter delta")

        losses = [row["loss_before_update"] for row in steps] + [final_loss]
        head_count = int(confirm["head_window_observations"])
        tail_count = int(confirm["tail_window_observations"])
        initial_loss = losses[0]
        head_median = float(statistics.median(losses[:head_count]))
        tail_median = float(statistics.median(losses[-tail_count:]))
        best_loss = min(losses)
        trajectory_hash = _trajectory_sha256(steps, final_loss)
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_repeat_v1",
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
                "optimizer_updates": int(optimizer.step.item()),
                "loss_observations": len(losses),
                "gradient_checkpointing_enabled": False,
                "adapter_or_model_saved": False,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "batch_contract": {**prereg["batch_contract"], "source": source},
            "active_position_contract": position_contract,
            "steps": steps,
            "loss_trajectory": [
                {"updates_completed": index, "loss": loss}
                for index, loss in enumerate(losses)
            ],
            "trajectory_summary": {
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "best_loss": best_loss,
                "final_loss_decrease": initial_loss - final_loss,
                "best_loss_decrease": initial_loss - best_loss,
                "head_median_loss": head_median,
                "tail_median_loss": tail_median,
                "tail_median_vs_head_median_decrease": head_median - tail_median,
                "sha256": trajectory_hash,
            },
            "parameter_update": {
                "before_sha256": before_hash,
                "after_sha256": final_hash,
                "hash_changed": before_hash != final_hash,
                **delta,
            },
            "optimizer_state": {
                "step": int(optimizer.step.item()),
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
            "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_repeat_v1",
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
        return "short_trajectory_execution_failed"
    if not checks["all_values_finite"]:
        return "short_trajectory_nonfinite"
    if not checks["parameter_hash_changed_and_delta_nonzero"]:
        return "short_trajectory_did_not_mutate_parameters"
    if not checks["trajectory_reproducible"]:
        return "short_trajectory_not_reproducible"
    if not checks["mutation_within_bounds"]:
        return "short_trajectory_exceeded_mutation_bounds"
    if not checks["loss_converged"]:
        return "short_trajectory_did_not_converge"
    return "active_head_short_trajectory_converged"


def _measure(rows, prereg):
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    deltas = [row["parameter_update"]["l2_norm"] for row in rows]
    mean_delta = statistics.fmean(deltas)
    delta_cv = statistics.pstdev(deltas) / max(mean_delta, 1e-300)
    all_values_finite = all(
        all(math.isfinite(point["loss"]) for point in row["loss_trajectory"])
        and all(
            step["raw_gradient"]["all_elements_finite"]
            and step["clipped_gradient"]["all_elements_finite"]
            for step in row["steps"]
        )
        and row["parameter_update"]["all_elements_finite"]
        for row in rows
    )
    parameter_changed = all(
        row["parameter_update"]["hash_changed"] for row in rows
    ) and min(deltas) > confirm["parameter_delta_l2_minimum_exclusive"]
    trajectory_reproducible = (
        len({row["trajectory_summary"]["sha256"] for row in rows}) == 1
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
            step["clipped_gradient"]["norm"]
            for row in rows
            for step in row["steps"]
        )
        <= confirm["clipped_gradient_norm_maximum"]
        and all(
            row["optimizer_state"]["step"] == confirm["optimizer_step_exact"]
            for row in rows
        )
    )
    loss_converged = all(
        row["trajectory_summary"]["initial_loss"] == confirm["initial_loss_exact"]
        and row["trajectory_summary"]["final_loss_decrease"]
        >= confirm["final_loss_decrease_minimum"]
        and row["trajectory_summary"]["best_loss_decrease"]
        >= confirm["best_loss_decrease_minimum"]
        and row["trajectory_summary"]["tail_median_vs_head_median_decrease"]
        >= confirm["tail_median_vs_head_median_decrease_minimum"]
        for row in rows
    )
    all_contracts_exact = all(
        row["base_contract"]["exact"]
        and row["adapter_contract"]["exact"]
        and row["active_position_contract"]["sha256"]
        == prereg["active_position_contract"]["sha256"]
        and row["runtime_contract"]["optimizer_updates"]
        == construction.OPTIMIZER_UPDATES
        and row["runtime_contract"]["loss_observations"]
        == construction.OPTIMIZER_UPDATES + 1
        and row["runtime_contract"]["adapter_or_model_saved"] is False
        for row in rows
    )
    checks = {
        "all_values_finite": all_values_finite,
        "parameter_hash_changed_and_delta_nonzero": parameter_changed,
        "trajectory_reproducible": trajectory_reproducible,
        "mutation_within_bounds": mutation_within_bounds,
        "loss_converged": loss_converged,
        "all_contracts_exact": all_contracts_exact,
    }
    measurements = {
        "loss_trajectories": [row["loss_trajectory"] for row in rows],
        "initial_losses": [
            row["trajectory_summary"]["initial_loss"] for row in rows
        ],
        "final_losses": [row["trajectory_summary"]["final_loss"] for row in rows],
        "best_losses": [row["trajectory_summary"]["best_loss"] for row in rows],
        "final_loss_decreases": [
            row["trajectory_summary"]["final_loss_decrease"] for row in rows
        ],
        "best_loss_decreases": [
            row["trajectory_summary"]["best_loss_decrease"] for row in rows
        ],
        "head_median_losses": [
            row["trajectory_summary"]["head_median_loss"] for row in rows
        ],
        "tail_median_losses": [
            row["trajectory_summary"]["tail_median_loss"] for row in rows
        ],
        "tail_vs_head_decreases": [
            row["trajectory_summary"]["tail_median_vs_head_median_decrease"]
            for row in rows
        ],
        "trajectory_hashes": [
            row["trajectory_summary"]["sha256"] for row in rows
        ],
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
        "after_parameter_hashes": [
            row["parameter_update"]["after_sha256"] for row in rows
        ],
        "optimizer_state_hashes": [row["optimizer_state"]["sha256"] for row in rows],
        "maximum_raw_gradient_norms": [
            max(step["raw_gradient"]["norm"] for step in row["steps"])
            for row in rows
        ],
        "maximum_clipped_gradient_norms": [
            max(step["clipped_gradient"]["norm"] for step in row["steps"])
            for row in rows
        ],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in rows],
        "durations_seconds": [row["resource"]["duration_seconds"] for row in rows],
    }
    return measurements, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 short-trajectory execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite short-trajectory aggregate")
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
            "trajectory_reproducible": False,
            "mutation_within_bounds": False,
            "loss_converged": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    result = {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": {
            "experiment_complete": completed,
            "passed": passed,
            "outcome": outcome,
            "multibatch_learning_probe_authorized": passed,
            "authorized_next_step": (
                "preregister_source_independent_multibatch_active_head_learning_probe"
                if passed
                else "diagnose_active_head_short_trajectory_nonconvergence"
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
        "interpretation_limits": prereg["interpretation_limits"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 active-head 短程收斂軌跡結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 3 次全部完成且通過：`{passed}`",
                f"- initial loss：`{measurements.get('initial_losses', ['NA'])[0]}`",
                f"- final loss：`{measurements.get('final_losses', ['NA'])[0]}`",
                f"- final loss decrease：`{measurements.get('final_loss_decreases', ['NA'])[0]}`",
                f"- tail vs head median decrease：`{measurements.get('tail_vs_head_decreases', ['NA'])[0]}`",
                f"- parameter delta L2：`{measurements.get('parameter_delta_l2_norms', ['NA'])[0]}`",
                "- 僅代表單一 micro-batch 的訓練路徑可學習性。",
                "- adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_result_lock_v1",
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
            "initial_loss": row.get("trajectory_summary", {}).get("initial_loss"),
            "final_loss": row.get("trajectory_summary", {}).get("final_loss"),
            "final_loss_decrease": row.get("trajectory_summary", {}).get(
                "final_loss_decrease"
            ),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
