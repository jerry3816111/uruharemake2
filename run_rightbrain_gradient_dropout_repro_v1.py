#!/usr/bin/env python3
"""Run isolated zero-update dropout-zero gradient probes and aggregate them."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import statistics
import time
from itertools import combinations
from pathlib import Path

import psutil
import torch

import build_rightbrain_gradient_dropout_repro_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as telemetry_tools
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
        and authorization["adapter_dropout"] == 0.0
        and authorization["gradient_checkpointing"]
        and not authorization["model_or_adapter_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": rows, "lock": lock}


def _result_path(preregistration, repeat):
    return ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"


def _gradient_sha256(parameters):
    digest = hashlib.sha256()
    for name, parameter in parameters:
        if parameter.grad is None:
            continue
        tensor = parameter.grad.detach().float().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _cpu_float64_norm(parameters):
    square_sum = 0.0
    finite = total = 0
    for _, parameter in parameters:
        if parameter.grad is None:
            continue
        gradient = parameter.grad.detach().float().cpu().double()
        square_sum += float(torch.sum(gradient.square()))
        finite += int(torch.isfinite(gradient).sum())
        total += gradient.numel()
    return math.sqrt(square_sum), finite, total


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in (1, 2, 3):
        raise ValueError("repeat must be 1, 2, or 3")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Dropout probe requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Dropout probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    output_path = _result_path(preregistration, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    rows = construction.load_json(ROOT / probe["dataset"])
    training_contract = {
        "local_model_contract": preregistration["local_model_contract"],
        "training_schedule": {"adapter_dropout": probe["adapter_dropout"]},
    }
    tokenizer = pilot.load_tokenizer(training_contract)
    dataset = pilot.FixedLengthContractDataset(
        rows, tokenizer, int(probe["fixed_allocated_sequence_length"])
    )
    pilot._seed_everything(int(probe["random_seed"]))
    started = time.perf_counter()
    process = psutil.Process()
    model_contract = preregistration["local_model_contract"]
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=int(probe["adapter_rank"]),
        lora_alpha=int(probe["adapter_alpha"]),
        lora_dropout=float(probe["adapter_dropout"]),
        dtype_name="bfloat16",
    )
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
    for index in probe["row_indices"]:
        batch = {key: value.unsqueeze(0) for key, value in dataset[index].items()}
        loss = model(**pilot._move(batch, device)).loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss in repeat {repeat} row {index}")
        losses.append(float(loss.detach().float().cpu()))
        (loss / int(probe["gradient_accumulation"])).backward()
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
    cpu_norm, finite, total = _cpu_float64_norm(parameters)
    telemetry = telemetry_tools.gradient_telemetry(parameters)
    after_hash = telemetry_tools.parameter_sha256(parameters)
    result = {
        "schema": "uruha_rightbrain_gradient_dropout_repro_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat": repeat,
        "execution_mode": "isolated_python_process_zero_update",
        "probe": probe,
        "losses": losses,
        "mean_loss": statistics.fmean(losses),
        "gradient": {
            "mps_foreach_false_repeated_norms": mps_norms,
            "mps_foreach_false_mean_norm": statistics.fmean(mps_norms),
            "cpu_float64_norm": cpu_norm,
            "mps_vs_cpu_relative_error": abs(statistics.fmean(mps_norms) - cpu_norm)
            / max(cpu_norm, 1e-300),
            "gradient_sha256": _gradient_sha256(parameters),
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
            "process_resident_memory_bytes": process.memory_info().rss,
            "mps_current_allocated_memory_bytes": (
                torch.mps.current_allocated_memory() if torch.backends.mps.is_available() else 0
            ),
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(output_path, result)
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return result


def _profile_vector(result):
    return [float(row["norm"]) for row in result["gradient"]["profile"]]


def _cosine(left, right):
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / max(left_norm * right_norm, 1e-300)


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Dropout probe execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = preregistration["result_paths"]
    result_json = ROOT / paths["aggregate_json"]
    result_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite dropout aggregate")
    repeats = [
        construction.load_json(_result_path(preregistration, repeat))
        for repeat in range(1, 4)
    ]
    norms = [row["gradient"]["mps_foreach_false_mean_norm"] for row in repeats]
    pair_cosines = [
        _cosine(_profile_vector(left), _profile_vector(right))
        for left, right in combinations(repeats, 2)
    ]
    mean_norm = statistics.fmean(norms)
    cv = statistics.pstdev(norms) / max(mean_norm, 1e-300)
    ratio = max(norms) / max(min(norms), 1e-300)
    hypothesis = preregistration["falsifiable_hypothesis"]
    confirm = hypothesis["confirm_if_all"]
    checks = {
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
    }
    passed = all(checks.values())
    result = {
        "schema": "uruha_rightbrain_gradient_dropout_repro_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(preregistration, repeat))
                for repeat in range(1, 4)
            ],
        },
        "measurements": {
            "gradient_norms": norms,
            "mean_gradient_norm": mean_norm,
            "gradient_norm_coefficient_of_variation": cv,
            "gradient_norm_max_to_min_ratio": ratio,
            "pairwise_group_profile_cosines": pair_cosines,
            "minimum_pairwise_group_profile_cosine": min(pair_cosines),
            "gradient_hashes": [row["gradient"]["gradient_sha256"] for row in repeats],
            "losses": repeats[0]["losses"],
        },
        "checks": checks,
        "decision": {
            "passed": passed,
            "outcome": (
                "dropout_zero_restores_gradient_reproducibility"
                if passed
                else "dropout_zero_does_not_restore_gradient_reproducibility"
            ),
            "authorized_next_step": (
                "preregister_max_norm_pilot_v3_with_dropout_zero"
                if passed
                else "zero_update_checkpointing_or_dtype_probe_only"
            ),
            "authorize_model_training_now": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(result_json, result)
    lines = [
        "# RightBrain dropout=0 梯度重現結果",
        "",
        f"- 判定：`{result['decision']['outcome']}`",
        f"- 三次 gradient norm：`{norms}`",
        f"- CV：`{cv:.6g}`",
        f"- max/min：`{ratio:.6g}`",
        f"- 最低 profile cosine：`{min(pair_cosines):.10f}`",
        "- optimizer step：`0`",
        "- 正式 runtime 修改：`0`",
    ]
    construction.atomic_text(result_md, "\n".join(lines) + "\n")
    lock = {
        "schema": "uruha_rightbrain_gradient_dropout_repro_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(result_json),
            construction.file_binding(result_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "preregister_max_norm_pilot_v3_with_dropout_zero": passed,
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
    output = (
        {
            "repeat": args.repeat,
            "gradient_norm": result["gradient"]["mps_foreach_false_mean_norm"],
            "mps_vs_cpu_relative_error": result["gradient"]["mps_vs_cpu_relative_error"],
            "parameters_unchanged": result["parameter_integrity"]["unchanged"],
        }
        if args.repeat
        else result["decision"] | result["measurements"]
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
