#!/usr/bin/env python3
"""Run isolated full-Qwen3 loss-component backward probes."""

from __future__ import annotations

import argparse
import functools
import json
import math
import resource
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load

import build_rightbrain_qwen3_loss_decomposition_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as full_runner
import run_rightbrain_qwen3_compact_length_repro_v1 as parent_runner


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
        and authorization["loss_modes"] == list(construction.LOSS_MODES)
        and authorization["allocated_sequence_length"] == 512
        and authorization["fixed_shared_prefix_tokens"] == 64
        and authorization["base_compute_dtype"] == "bfloat16"
        and authorization["adapter_dtype"] == "mlx.core.float32"
        and authorization["full_language_model_forward_path"] is True
        and authorization["device"] == "gpu"
        and authorization["repetitions_each"] == list(construction.REPEATS)
        and authorization["fully_counterbalanced_execution_schedule"]
        == construction.EXECUTION_SCHEDULE
        and authorization["optimizer_steps"] == 0
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, loss_mode, repeat):
    prefix = prereg["result_paths"]["repeat_prefix"]
    return ROOT / f"{prefix}{loss_mode}_repeat_{repeat}.json"


def _decomposed_loss(model, batch, labels, *, loss_mode):
    inputs = batch[:, :-1]
    targets = batch[:, 1:]
    active_labels = labels[:, 1:]
    mask = active_labels != -100
    safe_targets = mx.where(mask, targets, mx.zeros_like(targets))
    logits = model(inputs)
    if loss_mode == "masked_cross_entropy":
        per_token = nn.losses.cross_entropy(logits, safe_targets)
    elif loss_mode == "target_score_only":
        target_score = mx.take_along_axis(
            logits, mx.expand_dims(safe_targets, -1), -1
        ).squeeze(-1)
        per_token = -target_score
    elif loss_mode == "logsumexp_only":
        per_token = mx.logsumexp(logits, axis=-1)
    else:
        raise ValueError(f"Unsupported loss mode: {loss_mode}")
    token_count = mask.sum()
    loss = (per_token * mask).astype(mx.float32).sum() / token_count
    return loss, token_count


def run_repeat(loss_mode, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if loss_mode not in construction.LOSS_MODES:
        raise ValueError("loss mode outside preregistered values")
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 loss-decomposition execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, loss_mode, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {loss_mode} repeat {repeat}")
    probe = prereg["exact_probe"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
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
        adapter = full_runner._initialize_adapter(model, prereg)
        if not adapter["exact"]:
            raise RuntimeError(f"Adapter contract mismatch: {adapter}")
        parent = construction.load_json(construction.PARENT_PREREGISTRATION)
        batch, source = construction.canonical_batch(tokenizer)
        expected = prereg["batch_contract"]
        for key, value in expected.items():
            if batch[key] != value:
                raise RuntimeError(
                    f"Batch contract mismatch {key}: {batch[key]} != {value}"
                )
        input_ids = mx.array(batch["input_ids"][None, :])
        labels = mx.array(batch["labels"][None, :])
        before_hash = common._parameter_sha256(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        objective = functools.partial(_decomposed_loss, loss_mode=loss_mode)
        loss_and_grad = nn.value_and_grad(model, objective)
        (loss, token_count), gradients = loss_and_grad(model, input_ids, labels)
        mx.eval(loss, token_count, gradients)
        loss_value = float(loss.item())
        if not math.isfinite(loss_value):
            raise RuntimeError(f"Non-finite {loss_mode} loss")
        gradient = common._gradient_measurements(gradients)
        if not gradient["all_elements_finite"]:
            raise RuntimeError(f"Non-finite {loss_mode} gradient")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_loss_decomposition_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "loss_mode": loss_mode,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "base_compute_dtype": "bfloat16",
                "full_language_model_forward_path": True,
                "gradient_checkpointing_enabled": False,
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "base_contract": base,
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
            "schema": "uruha_rightbrain_qwen3_loss_decomposition_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "loss_mode": loss_mode,
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


def _classify(stability):
    ce = stability["masked_cross_entropy"]
    target = stability["target_score_only"]
    lse = stability["logsumexp_only"]
    if ce:
        return "cross_entropy_parent_drift_not_reproduced"
    if not target and not lse:
        return "drift_precedes_loss_decomposition_or_is_in_shared_model_backward"
    if target and not lse:
        return "logsumexp_branch_is_sufficient_to_reproduce_drift"
    if not target and lse:
        return "target_score_branch_is_sufficient_to_reproduce_drift"
    return "combined_cross_entropy_graph_is_required_to_reproduce_drift"


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 loss-decomposition execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite Qwen3 loss-decomposition aggregate")
    rows = {
        mode: [
            construction.load_json(_result_path(prereg, mode, repeat))
            for repeat in construction.REPEATS
        ]
        for mode in construction.LOSS_MODES
    }
    completed = all(
        row.get("execution_success") is True
        for mode_rows in rows.values()
        for row in mode_rows
    )
    metrics = {}
    stability = {mode: False for mode in construction.LOSS_MODES}
    checks = {"all_repetitions_complete": completed}
    if completed:
        limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        for mode in construction.LOSS_MODES:
            metrics[mode], stability[mode] = parent_runner._measure(
                rows[mode], limits
            )
            checks[f"{mode}_contracts_exact"] = all(
                row["base_contract"]["exact"]
                and row["adapter_contract"]["exact"]
                and row["parameter_integrity"]["unchanged"]
                and row["gradient"]["all_elements_finite"]
                and row["batch_contract"]["sha256"]
                == prereg["batch_contract"]["sha256"]
                for row in rows[mode]
            )
            checks[f"{mode}_reproducible"] = stability[mode]
    else:
        metrics["failures"] = [
            row.get("failure")
            for mode_rows in rows.values()
            for row in mode_rows
            if not row.get("execution_success")
        ]
    outcome = _classify(stability) if completed else "loss_decomposition_execution_failed"
    next_steps = {
        "drift_precedes_loss_decomposition_or_is_in_shared_model_backward": (
            "localize_tied_lm_head_or_shared_transformer_backward"
        ),
        "logsumexp_branch_is_sufficient_to_reproduce_drift": (
            "localize_logsumexp_backward_only"
        ),
        "target_score_branch_is_sufficient_to_reproduce_drift": (
            "localize_take_along_axis_backward_only"
        ),
        "combined_cross_entropy_graph_is_required_to_reproduce_drift": (
            "localize_gradient_accumulation_between_loss_branches"
        ),
        "cross_entropy_parent_drift_not_reproduced": (
            "increase_cross_entropy_control_repetitions_before_loss_claim"
        ),
        "loss_decomposition_execution_failed": (
            "repair_execution_without_changing_hypothesis"
        ),
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_loss_decomposition_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": metrics,
        "stability_by_loss_mode": stability,
        "checks": checks,
        "decision": {
            "experiment_complete": completed,
            "outcome": outcome,
            "authorized_next_step": next_steps[outcome],
            "authorize_training": False,
            "authorize_persona_training": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, mode, repeat))
                for mode in construction.LOSS_MODES
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
    }
    construction.atomic_json(output_json, result)
    rows_md = [
        f"| {mode} | {'穩定' if stability[mode] else '不穩定'} | "
        f"{metrics.get(mode, {}).get('gradient_norm_coefficient_of_variation', 'NA')} | "
        f"{metrics.get(mode, {}).get('gradient_norm_max_to_min_ratio', 'NA')} | "
        f"{metrics.get(mode, {}).get('gradient_hashes_identical', 'NA')} |"
        for mode in construction.LOSS_MODES
    ]
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 loss 分解梯度定位結果",
                "",
                f"- 判定：`{outcome}`",
                "",
                "| loss mode | 18 次判定 | gradient CV | max/min | hash 相同 |",
                "|:---|:---:|---:|---:|:---:|",
                *rows_md,
                "",
                "- 正式訓練／人格訓練／上線授權：`False`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_loss_decomposition_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "training": False,
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loss-mode", choices=construction.LOSS_MODES)
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.loss_mode is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with a repeat")
        output = aggregate()["decision"]
    else:
        if args.loss_mode is None or args.repeat is None:
            parser.error("--loss-mode and --repeat are required")
        row = run_repeat(args.loss_mode, args.repeat)
        output = {
            "loss_mode": args.loss_mode,
            "repeat": args.repeat,
            "execution_success": row["execution_success"],
            "loss": row.get("loss"),
            "gradient_norm": row.get("gradient", {}).get("norm"),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
