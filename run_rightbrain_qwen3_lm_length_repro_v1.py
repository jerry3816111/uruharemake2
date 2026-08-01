#!/usr/bin/env python3
"""Run isolated full-Qwen3 64-token and 800-token backward probes."""

from __future__ import annotations

import argparse
import json
import math
import resource
import statistics
import time
from itertools import combinations
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load

import build_rightbrain_qwen3_lm_length_repro_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as full_runner


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
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    environment = common._environment()
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == prereg["local_environment"]
        and authorization["allocated_sequence_lengths"] == [64, 800]
        and authorization["fixed_shared_prefix_tokens"] == 64
        and authorization["full_language_model_path"] is True
        and authorization["device"] == "gpu"
        and authorization["repetitions_each"] == [1, 2, 3]
        and authorization["optimizer_steps"] == 0
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, length, repeat):
    prefix = prereg["result_paths"]["repeat_prefix"]
    return ROOT / f"{prefix}{length}_tokens_repeat_{repeat}.json"


def run_repeat(length, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if length not in (64, 800) or repeat not in (1, 2, 3):
        raise ValueError("length/repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 LM-length execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, length, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite length {length} repeat {repeat}")
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
        batches, source = construction.canonical_batches(tokenizer, parent)
        batch = batches[str(length)]
        expected = prereg["batch_contracts"][str(length)]
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
            raise RuntimeError(f"Non-finite length-{length} loss")
        gradient = common._gradient_measurements(gradients)
        if not gradient["all_elements_finite"]:
            raise RuntimeError(f"Non-finite length-{length} gradient")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_lm_length_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "allocated_sequence_length": length,
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
                "process_peak_resident_memory_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            "boundaries": prereg["boundaries"],
        }
    except Exception as error:
        message = str(error)
        result = {
            "schema": "uruha_rightbrain_qwen3_lm_length_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "allocated_sequence_length": length,
            "repeat": repeat,
            "execution_success": False,
            "failure": {
                "error_type": type(error).__name__,
                "message": message,
                "out_of_memory": "memory" in message.lower() or "alloc" in message.lower(),
                "nonfinite": "non-finite" in message.lower() or "nonfinite" in message.lower(),
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_peak_memory_bytes": mx.get_peak_memory(),
            },
            "boundaries": prereg["boundaries"],
        }
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


def _measure(rows, limits):
    norms = [row["gradient"]["norm"] for row in rows]
    mean = statistics.fmean(norms)
    cosines = [
        _cosine(left["gradient"]["profile"], right["gradient"]["profile"])
        for left, right in combinations(rows, 2)
    ]
    metrics = {
        "gradient_norms": norms,
        "mean_gradient_norm": mean,
        "gradient_norm_coefficient_of_variation": statistics.pstdev(norms) / max(mean, 1e-300),
        "gradient_norm_max_to_min_ratio": max(norms) / max(min(norms), 1e-300),
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
    metrics["checks"] = checks
    return metrics, all(checks.values())


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 LM-length execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite Qwen3 LM-length aggregate")
    rows = {
        str(length): [
            construction.load_json(_result_path(prereg, length, repeat))
            for repeat in (1, 2, 3)
        ]
        for length in (64, 800)
    }
    completed = all(
        row.get("execution_success") is True
        for length_rows in rows.values()
        for row in length_rows
    )
    metrics = {}
    stable = {"64": False, "800": False}
    checks = {"all_six_repetitions_complete": completed}
    if completed:
        limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        for length in ("64", "800"):
            metrics[length], stable[length] = _measure(rows[length], limits)
            checks[f"length_{length}_contracts_exact"] = all(
                row["base_contract"]["exact"]
                and row["adapter_contract"]["exact"]
                and row["parameter_integrity"]["unchanged"]
                and row["gradient"]["all_elements_finite"]
                and row["batch_contract"]["sha256"] == prereg["batch_contracts"][length]["sha256"]
                for row in rows[length]
            )
            checks[f"length_{length}_reproducible"] = stable[length]
    else:
        metrics["failures"] = [
            row.get("failure")
            for length_rows in rows.values()
            for row in length_rows
            if not row.get("execution_success")
        ]
    if not completed:
        outcome = "lm_length_localization_execution_failed"
    elif not stable["64"] and not stable["800"]:
        outcome = "full_lm_objective_unstable_even_at_short_length"
    elif not stable["64"]:
        outcome = "short_length_control_invalid"
    elif not stable["800"]:
        outcome = "ignored_padding_length_reproduces_gradient_drift"
    else:
        outcome = "ignored_padding_length_alone_does_not_reproduce_parent_drift"
    next_steps = {
        "full_lm_objective_unstable_even_at_short_length": "localize_lm_head_norm_or_cross_entropy",
        "ignored_padding_length_reproduces_gradient_drift": "binary_search_allocated_sequence_length",
        "ignored_padding_length_alone_does_not_reproduce_parent_drift": "preregister_active_context_and_label_position_localization",
        "short_length_control_invalid": "repair_short_control_before_length_claim",
        "lm_length_localization_execution_failed": "repair_execution_without_changing_hypothesis",
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_lm_length_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": metrics,
        "checks": checks,
        "decision": {
            "localization_complete": completed,
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
                construction.file_binding(_result_path(prereg, length, repeat))
                for length in (64, 800)
                for repeat in (1, 2, 3)
            ],
        },
        "boundaries": prereg["boundaries"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 完整 LM 64 / 800 token 定位結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 64 token 穩定：`{stable['64']}`",
                f"- 800 token 穩定：`{stable['800']}`",
                f"- 量測：`{json.dumps(metrics, ensure_ascii=False)}`",
                "- 人格訓練授權：`False`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_lm_length_repro_result_lock_v1",
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
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, choices=(64, 800))
    parser.add_argument("--repeat", type=int, choices=(1, 2, 3))
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.length is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with --length/--repeat")
        result = aggregate()
        output = result["decision"] | result["measurements"]
    else:
        if args.length is None or args.repeat is None:
            parser.error("--length and --repeat are required")
        result = run_repeat(args.length, args.repeat)
        output = (
            {
                "length": args.length,
                "repeat": args.repeat,
                "execution_success": True,
                "loss": result["loss"],
                "gradient_norm": result["gradient"]["norm"],
                "duration_seconds": result["resource"]["duration_seconds"],
                "peak_memory_bytes": result["resource"]["mlx_peak_memory_bytes"],
            }
            if result["execution_success"]
            else {
                "length": args.length,
                "repeat": args.repeat,
                "execution_success": False,
                "failure": result["failure"],
            }
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
