#!/usr/bin/env python3
"""Run isolated Qwen3-4B RightBrain zero-update trainability probes."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import statistics
import time
from itertools import combinations
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm import load
from mlx_lm.tuner.utils import linear_to_lora_layers

import build_rightbrain_qwen3_4b_trainability_v1 as construction
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
        and authorization["base_model"]
        == preregistration["local_model_contract"]["base_model"]
        and authorization["fresh_adapter_initialization_exact"] is True
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


def _result_path(preregistration, repeat):
    return ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"


def _initialize_adapter(model, preregistration):
    contract = preregistration["adapter_initialization_contract"]
    model.freeze()
    mx.random.seed(int(contract["initialization_seed"]))
    linear_to_lora_layers(
        model,
        int(contract["converted_layers"]),
        {
            "rank": int(contract["rank"]),
            "dropout": float(contract["dropout"]),
            "scale": float(contract["scale"]),
        },
    )
    mx.eval(model.trainable_parameters())
    flat = tree_flatten(model.trainable_parameters())
    tensor_count = len(flat)
    parameter_count = sum(value.size for _, value in flat)
    dtypes = sorted({str(value.dtype) for _, value in flat})
    digest = common._parameter_sha256(model.trainable_parameters())
    exact = (
        tensor_count == int(contract["trainable_tensor_count"])
        and parameter_count == int(contract["trainable_parameter_count"])
        and dtypes == [contract["trainable_dtype"]]
        and digest == contract["initial_trainable_sha256"]
    )
    return {
        "tensor_count": tensor_count,
        "parameter_count": parameter_count,
        "dtypes": dtypes,
        "sha256": digest,
        "exact": exact,
    }


def _base_contract(model, preregistration):
    contract = preregistration["local_model_contract"]
    flat = tree_flatten(model.parameters())
    parameter_count = sum(value.size for _, value in flat)
    dtypes = sorted({str(value.dtype) for _, value in flat})
    return {
        "parameter_count": parameter_count,
        "dtypes": dtypes,
        "exact": parameter_count == int(contract["base_parameter_count"])
        and dtypes == [contract["base_dtype"]],
    }


def _failure_result(preregistration, repeat, started, error):
    message = str(error)
    return {
        "schema": "uruha_rightbrain_qwen3_4b_trainability_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat": repeat,
        "execution_success": False,
        "execution_mode": "isolated_qwen3_4b_zero_update_no_checkpoint",
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
        "probe": preregistration["exact_probe"],
        "boundaries": preregistration["boundaries"],
    }


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in (1, 2, 3):
        raise ValueError("repeat must be 1, 2, or 3")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Qwen3-4B probe requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3-4B execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    output_path = _result_path(preregistration, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite Qwen3-4B repeat {repeat}")
    started = time.perf_counter()
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, tokenizer = load(
            preregistration["local_model_contract"]["snapshot_root"],
            tokenizer_config={"trust_remote_code": True},
        )
        mx.eval(model.parameters())
        base = _base_contract(model, preregistration)
        if not base["exact"]:
            raise RuntimeError(f"Base model contract mismatch: {base}")
        adapter = _initialize_adapter(model, preregistration)
        if not adapter["exact"]:
            raise RuntimeError(f"Adapter initialization contract mismatch: {adapter}")
        batches, token_details, token_hash = common._tokenize_exact_batch(
            preregistration, tokenizer
        )
        if token_hash != probe["canonical_token_and_label_sha256"]:
            raise RuntimeError(f"Token contract hash mismatch: {token_hash}")
        before_hash = common._parameter_sha256(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, common._completion_loss)
        input_ids, labels = batches[0]
        (loss, token_count), gradients = loss_and_grad(
            model,
            mx.array(input_ids[None, :]),
            mx.array(labels[None, :]),
        )
        mx.eval(loss, token_count, gradients)
        loss_value = float(loss.item())
        if not math.isfinite(loss_value):
            raise RuntimeError(f"Non-finite Qwen3-4B loss at repeat {repeat}")
        gradient = common._gradient_measurements(gradients)
        if not gradient["all_elements_finite"]:
            raise RuntimeError("Non-finite Qwen3-4B gradient elements")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Qwen3-4B peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_4b_trainability_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "execution_mode": "isolated_qwen3_4b_zero_update_no_checkpoint",
            "environment": validation["environment"],
            "runtime_contract": {
                "backend": "mlx",
                "base_model": preregistration["local_model_contract"]["base_model"],
                "gradient_checkpointing_enabled": False,
                "base_dtype": preregistration["local_model_contract"]["base_dtype"],
                "adapter_dtype": probe["trainable_adapter_dtype"],
                "adapter_dropout": preregistration["adapter_initialization_contract"]["dropout"],
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "base_model_contract": base,
            "adapter_initialization": adapter,
            "token_contract": {"sha256": token_hash, "details": token_details},
            "losses": [loss_value],
            "mean_loss": loss_value,
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
            "probe": probe,
            "boundaries": preregistration["boundaries"],
        }
    except Exception as error:
        result = _failure_result(preregistration, repeat, started, error)
    construction.atomic_json(output_path, result)
    return result


def _successful_measurements(repeats, preregistration):
    norms = [row["gradient"]["norm"] for row in repeats]
    pair_cosines = [
        common._cosine(left["gradient"]["profile"], right["gradient"]["profile"])
        for left, right in combinations(repeats, 2)
    ]
    mean_norm = statistics.fmean(norms)
    cv = statistics.pstdev(norms) / max(mean_norm, 1e-300)
    ratio = max(norms) / max(min(norms), 1e-300)
    confirm = preregistration["falsifiable_hypothesis"]["confirm_if_all"]
    probe = preregistration["exact_probe"]
    adapter_hash = preregistration["adapter_initialization_contract"][
        "initial_trainable_sha256"
    ]
    token_hash = probe["canonical_token_and_label_sha256"]
    checks = {
        "all_three_repetitions_complete": True,
        "model_and_adapter_contract_exact_each": all(
            row["base_model_contract"]["exact"]
            and row["adapter_initialization"]["exact"]
            and row["adapter_initialization"]["sha256"] == adapter_hash
            for row in repeats
        ),
        "token_and_label_hash_exact_each": all(
            row["token_contract"]["sha256"] == token_hash for row in repeats
        ),
        "loss_vectors_exact_across_repetitions": all(
            row["losses"] == repeats[0]["losses"] for row in repeats
        ),
        "gradient_norm_coefficient_of_variation": cv
        <= confirm["gradient_norm_coefficient_of_variation_maximum"],
        "gradient_norm_max_to_min_ratio": ratio
        <= confirm["gradient_norm_max_to_min_ratio_maximum"],
        "minimum_pairwise_group_profile_cosine": min(pair_cosines)
        >= confirm["minimum_pairwise_group_profile_cosine"],
        "all_losses_and_gradients_finite": all(
            all(math.isfinite(loss) for loss in row["losses"])
            and row["gradient"]["all_elements_finite"]
            for row in repeats
        ),
        "trainable_parameters_unchanged": all(
            row["parameter_integrity"]["unchanged"] for row in repeats
        ),
        "peak_memory_within_limit": all(
            row["resource"]["mlx_peak_memory_bytes"] <= probe["memory_limit_bytes"]
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
        "gradient_hashes": [row["gradient"]["sha256"] for row in repeats],
        "gradient_hashes_identical": len({row["gradient"]["sha256"] for row in repeats})
        == 1,
        "losses": repeats[0]["losses"],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in repeats],
        "duration_seconds": [row["resource"]["duration_seconds"] for row in repeats],
    }, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3-4B execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite Qwen3-4B aggregate")
    repeats = [construction.load_json(_result_path(preregistration, i)) for i in (1, 2, 3)]
    completed = all(row.get("execution_success") is True for row in repeats)
    if completed:
        measurements, checks = _successful_measurements(repeats, preregistration)
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
        "schema": "uruha_rightbrain_qwen3_4b_trainability_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(preregistration, i)) for i in (1, 2, 3)
            ],
        },
        "measurements": measurements,
        "checks": checks,
        "decision": {
            "passed": passed,
            "outcome": (
                "qwen3_4b_has_finite_reproducible_local_lora_gradients"
                if passed
                else "qwen3_4b_candidate_trainability_gate_failed"
            ),
            "authorized_next_step": (
                "preregister_one_small_matched_qwen3_4b_rightbrain_sft_pilot"
                if passed
                else "reject_qwen3_4b_persona_training_without_new_evidence"
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
                "# RightBrain Qwen3-4B 可訓練性結果",
                "",
                f"- 判定：`{result['decision']['outcome']}`",
                f"- 下一步：`{result['decision']['authorized_next_step']}`",
                f"- 三次執行完成：`{completed}`",
                f"- 量測：`{json.dumps(measurements, ensure_ascii=False)}`",
                "- optimizer step：`0`",
                "- production 修改：`0`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_4b_trainability_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            result["inputs"]["preregistration"],
            result["inputs"]["execution_lock"],
            *result["inputs"]["repeats"],
            construction.file_binding(result_json),
            construction.file_binding(result_md),
        ],
        "authorization": {
            "authorized_next_step": result["decision"]["authorized_next_step"],
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
        summary = {"repeat": args.repeat, "execution_success": result["execution_success"]}
        if result["execution_success"]:
            summary["loss"] = result["mean_loss"]
            summary["gradient_norm"] = result["gradient"]["norm"]
            summary["peak_memory_bytes"] = result["resource"]["mlx_peak_memory_bytes"]
        else:
            summary["failure"] = result["failure"]
    else:
        summary = {**result["decision"], **result["measurements"]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
