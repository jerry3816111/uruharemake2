#!/usr/bin/env python3
"""Run isolated Apple MLX zero-update RightBrain gradient probes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import resource
import statistics
import struct
import subprocess
import time
from collections import defaultdict
from importlib.metadata import version
from itertools import combinations
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import numpy as np
from mlx.utils import tree_flatten, tree_map
from mlx_lm import load
from mlx_lm.tuner.trainer import grad_checkpoint
from mlx_lm.tuner.utils import linear_to_lora_layers
from safetensors import safe_open
from transformers import AutoTokenizer

import build_rightbrain_mlx_gradient_repro_v1 as construction


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK
ADAPTER_MODEL = (
    ROOT
    / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_model.safetensors"
)
PROJECTION_RE = re.compile(
    r"\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)\.lora_([ab])$"
)


def _resolve_binding(binding):
    path = Path(binding["path"])
    return path if binding.get("scope") == "external_local" or path.is_absolute() else ROOT / path


def _environment():
    packages = ("mlx", "mlx-lm", "mlx-metal", "numpy", "safetensors", "transformers")
    freeze = subprocess.run(
        [os.sys.executable, "-m", "pip", "freeze"],
        check=True,
        capture_output=True,
    ).stdout
    return {
        "python_executable": os.sys.executable,
        "python_version": platform.python_version(),
        "packages": {name: version(name) for name in packages},
        "pip_freeze_sha256": hashlib.sha256(freeze).hexdigest(),
    }


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
    environment = _environment()
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment["python_executable"] == expected_environment["python_executable"]
        and environment["python_version"] == expected_environment["python_version"]
        and environment["packages"] == expected_environment["packages"]
        and environment["pip_freeze_sha256"] == expected_environment["pip_freeze_sha256"]
        and authorization["exact_zero_update_repetitions"] == [1, 2, 3]
        and authorization["micro_steps_each"] == 8
        and authorization["optimizer_steps"] == 0
        and authorization["training_backend"] == "mlx"
        and authorization["gradient_checkpointing"] is True
        and authorization["adapter_conversion_exact"] is True
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


def _tokenize_exact_batch(preregistration, tokenizer):
    probe = preregistration["exact_probe"]
    rows = construction.load_json(ROOT / probe["dataset"])
    allocated = int(probe["fixed_allocated_sequence_length"])
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    digest = hashlib.sha256()
    batches = []
    details = []
    for index in probe["row_indices"]:
        row = rows[index]
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1], tokenize=False, add_generation_prompt=True
        )
        answer = f"{str(row['messages'][-1]['content']).strip()}<|im_end|>"
        prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
        answer_ids = tokenizer(answer, add_special_tokens=False).input_ids
        active_ids = prompt_ids + answer_ids
        if len(active_ids) > allocated:
            raise RuntimeError(f"Token contract exceeds {allocated}: {row['id']}")
        padding = allocated - len(active_ids)
        input_ids = np.asarray(active_ids + [pad_id] * padding, dtype=np.int32)
        labels = np.asarray(
            [-100] * len(prompt_ids) + answer_ids + [-100] * padding,
            dtype=np.int32,
        )
        digest.update(struct.pack("<I", index))
        digest.update(input_ids.tobytes())
        digest.update(labels.tobytes())
        batches.append((input_ids, labels))
        details.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "prompt_tokens": len(prompt_ids),
                "answer_tokens": len(answer_ids),
                "active_tokens": len(active_ids),
            }
        )
    return batches, details, digest.hexdigest()


def _convert_adapter(model, preregistration):
    contract = preregistration["adapter_conversion_contract"]
    model.freeze()
    linear_to_lora_layers(
        model,
        int(contract["converted_layers"]),
        {
            "rank": int(contract["rank"]),
            "dropout": float(contract["dropout"]),
            "scale": float(contract["scale"]),
        },
    )
    mapped = []
    expected = {}
    with safe_open(ADAPTER_MODEL, framework="numpy") as handle:
        for source_name in handle.keys():
            match = re.fullmatch(
                r"base_model\.model\.model\.(layers\.\d+\..+)\.lora_([AB])\.weight",
                source_name,
            )
            if match is None:
                raise RuntimeError(f"Unmapped PEFT adapter key: {source_name}")
            target_name = "model." + match.group(1) + (
                ".lora_a" if match.group(2) == "A" else ".lora_b"
            )
            array = np.ascontiguousarray(handle.get_tensor(source_name).T)
            mapped.append((target_name, mx.array(array)))
            expected[target_name] = array
    model.load_weights(mapped, strict=False)
    mx.eval(model.trainable_parameters())
    actual = dict(tree_flatten(model.trainable_parameters()))
    mismatches = []
    digest = hashlib.sha256()
    for name in sorted(expected):
        if name not in actual:
            mismatches.append({"name": name, "reason": "missing"})
            continue
        value = np.asarray(actual[name])
        if value.shape != expected[name].shape or not np.array_equal(value, expected[name]):
            mismatches.append({"name": name, "reason": "shape_or_value"})
        digest.update(name.encode("utf-8"))
        digest.update(value.tobytes())
    unexpected = sorted(set(actual) - set(expected))
    return {
        "source_tensor_count": len(mapped),
        "target_tensor_count": len(actual),
        "trainable_parameter_count": sum(value.size for value in actual.values()),
        "missing_or_mismatched": mismatches,
        "unexpected": unexpected,
        "canonical_mapped_sha256": digest.hexdigest(),
        "exact": not mismatches
        and not unexpected
        and len(mapped) == len(actual) == int(contract["target_tensor_count"])
        and digest.hexdigest() == contract["canonical_mapped_sha256"],
    }


def _parameter_sha256(parameters):
    digest = hashlib.sha256()
    for name, value in sorted(tree_flatten(parameters), key=lambda row: row[0]):
        array = np.asarray(value.astype(mx.float32))
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _completion_loss(model, batch, labels):
    inputs = batch[:, :-1]
    targets = batch[:, 1:]
    active_labels = labels[:, 1:]
    mask = active_labels != -100
    safe_targets = mx.where(mask, targets, mx.zeros_like(targets))
    logits = model(inputs)
    losses = nn.losses.cross_entropy(logits, safe_targets) * mask
    token_count = mask.sum()
    return losses.astype(mx.float32).sum() / token_count, token_count


def _gradient_measurements(gradients):
    square_sum = 0.0
    finite_elements = 0
    total_elements = 0
    digest = hashlib.sha256()
    group_squares = defaultdict(float)
    for name, value in sorted(tree_flatten(gradients), key=lambda row: row[0]):
        array = np.asarray(value.astype(mx.float32))
        finite_elements += int(np.isfinite(array).sum())
        total_elements += int(array.size)
        array64 = array.astype(np.float64)
        square = float(np.sum(array64 * array64))
        square_sum += square
        match = PROJECTION_RE.search(name)
        group = f"{match.group(1)}.lora_{match.group(2)}" if match else "other"
        group_squares[group] += square
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes())
    return {
        "norm": math.sqrt(square_sum),
        "finite_elements": finite_elements,
        "total_elements": total_elements,
        "all_elements_finite": finite_elements == total_elements,
        "sha256": digest.hexdigest(),
        "profile": {name: math.sqrt(value) for name, value in sorted(group_squares.items())},
    }


def _failure_result(preregistration, repeat, started, error):
    message = str(error)
    return {
        "schema": "uruha_rightbrain_mlx_gradient_repro_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat": repeat,
        "execution_success": False,
        "execution_mode": "isolated_mlx_zero_update_checkpointed",
        "failure": {
            "error_type": type(error).__name__,
            "message": message,
            "out_of_memory": "memory" in message.lower() or "alloc" in message.lower(),
            "nonfinite": "non-finite" in message.lower() or "nonfinite" in message.lower(),
            "mapping_or_token_contract": "adapter" in message.lower()
            or "token" in message.lower(),
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
        raise RuntimeError("MLX probe requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("MLX probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    output_path = _result_path(preregistration, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite MLX repeat {repeat}")
    started = time.perf_counter()
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, tokenizer = load(
            preregistration["local_model_contract"]["snapshot_root"],
            tokenizer_config={"trust_remote_code": True},
        )
        conversion = _convert_adapter(model, preregistration)
        if not conversion["exact"]:
            raise RuntimeError(f"Adapter conversion mismatch: {conversion}")
        batches, token_details, token_hash = _tokenize_exact_batch(
            preregistration, tokenizer
        )
        if token_hash != probe["canonical_token_and_label_sha256"]:
            raise RuntimeError(f"Token contract hash mismatch: {token_hash}")
        before_hash = _parameter_sha256(model.trainable_parameters())
        grad_checkpoint(model.layers[0])
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        loss_and_grad = nn.value_and_grad(model, _completion_loss)
        accumulated = None
        losses = []
        memory_rows = []
        for micro_step, (input_ids, labels) in enumerate(batches, start=1):
            (loss, token_count), gradients = loss_and_grad(
                model,
                mx.array(input_ids[None, :]),
                mx.array(labels[None, :]),
            )
            gradients = tree_map(
                lambda value: value / int(probe["gradient_accumulation"]),
                gradients,
            )
            accumulated = (
                gradients
                if accumulated is None
                else tree_map(lambda left, right: left + right, accumulated, gradients)
            )
            mx.eval(loss, token_count, accumulated)
            loss_value = float(loss.item())
            if not math.isfinite(loss_value):
                raise RuntimeError(
                    f"Non-finite MLX loss at repeat {repeat} micro-step {micro_step}"
                )
            losses.append(loss_value)
            peak = mx.get_peak_memory()
            memory_rows.append(
                {
                    "micro_step": micro_step,
                    "active_memory_bytes": mx.get_active_memory(),
                    "cache_memory_bytes": mx.get_cache_memory(),
                    "peak_memory_bytes": peak,
                }
            )
            if peak > int(probe["memory_limit_bytes"]):
                raise RuntimeError(
                    f"MLX peak memory exceeded limit: {peak}>{probe['memory_limit_bytes']}"
                )
        gradient = _gradient_measurements(accumulated)
        if not gradient["all_elements_finite"]:
            raise RuntimeError("Non-finite MLX gradient elements")
        after_hash = _parameter_sha256(model.trainable_parameters())
        result = {
            "schema": "uruha_rightbrain_mlx_gradient_repro_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "execution_mode": "isolated_mlx_zero_update_checkpointed",
            "environment": validation["environment"],
            "probe": probe,
            "runtime_contract": {
                "backend": "mlx",
                "gradient_checkpointing_enabled": True,
                "base_dtype": preregistration["local_model_contract"]["base_dtype"],
                "adapter_dtype": probe["trainable_adapter_dtype"],
                "adapter_dropout": preregistration["adapter_conversion_contract"]["dropout"],
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "adapter_conversion": conversion,
            "token_contract": {
                "sha256": token_hash,
                "details": token_details,
            },
            "losses": losses,
            "mean_loss": statistics.fmean(losses),
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
                "mlx_peak_memory_bytes": mx.get_peak_memory(),
                "process_peak_resident_memory_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
                "memory_by_micro_step": memory_rows,
            },
            "boundaries": preregistration["boundaries"],
        }
    except Exception as error:
        result = _failure_result(preregistration, repeat, started, error)
    construction.atomic_json(output_path, result)
    return result


def _cosine(left, right):
    keys = sorted(set(left) | set(right))
    left_values = [float(left.get(key, 0.0)) for key in keys]
    right_values = [float(right.get(key, 0.0)) for key in keys]
    dot = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    return dot / max(left_norm * right_norm, 1e-300)


def _successful_measurements(repeats, preregistration):
    norms = [row["gradient"]["norm"] for row in repeats]
    pair_cosines = [
        _cosine(left["gradient"]["profile"], right["gradient"]["profile"])
        for left, right in combinations(repeats, 2)
    ]
    mean_norm = statistics.fmean(norms)
    cv = statistics.pstdev(norms) / max(mean_norm, 1e-300)
    ratio = max(norms) / max(min(norms), 1e-300)
    confirm = preregistration["falsifiable_hypothesis"]["confirm_if_all"]
    probe = preregistration["exact_probe"]
    conversion_hash = preregistration["adapter_conversion_contract"][
        "canonical_mapped_sha256"
    ]
    token_hash = probe["canonical_token_and_label_sha256"]
    checks = {
        "all_three_repetitions_complete": True,
        "adapter_conversion_exact_each": all(
            row["adapter_conversion"]["exact"]
            and row["adapter_conversion"]["canonical_mapped_sha256"] == conversion_hash
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
        raise RuntimeError("MLX probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite MLX aggregate")
    repeats = [
        construction.load_json(_result_path(preregistration, repeat))
        for repeat in range(1, 4)
    ]
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
        "schema": "uruha_rightbrain_mlx_gradient_repro_result_v1",
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
                "mlx_restores_finite_reproducible_zero_update_gradients"
                if passed
                else "mlx_does_not_provide_a_usable_reproducible_gradient_path"
            ),
            "authorized_next_step": (
                "preregister_one_small_matched_mlx_training_pilot"
                if passed
                else "isolate_mlx_conversion_objective_shape_or_memory_failure"
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
                "# RightBrain MLX 梯度重現結果",
                "",
                f"- 判定：`{result['decision']['outcome']}`",
                f"- 三次執行完成：`{completed}`",
                f"- 量測：`{json.dumps(measurements, ensure_ascii=False)}`",
                "- optimizer step：`0`",
                "- 正式 runtime 修改：`0`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_mlx_gradient_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(result_json),
            construction.file_binding(result_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "preregister_one_small_matched_mlx_training_pilot": passed,
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
