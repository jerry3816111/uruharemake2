#!/usr/bin/env python3
"""Audit exact accumulated-gradient reproducibility across isolated processes."""

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

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_gradient_reproducibility_v1"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_gradient_reproducibility_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_gradient_reproducibility_v1_execution_lock.json"
)
DEFAULT_SUMMARY_JSON = ROOT / "reports/rightbrain_gradient_reproducibility_v1_summary.json"
DEFAULT_SUMMARY_MD = ROOT / "reports/rightbrain_gradient_reproducibility_v1_summary.md"


def repeat_path(repeat_id):
    return ROOT / f"reports/rightbrain_gradient_reproducibility_v1_repeat_{repeat_id}.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_bindings(bindings):
    rows = []
    for binding in bindings:
        path = ROOT / binding["path"]
        actual = construction.sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "actual_sha256": actual,
                "match": actual == binding["sha256"],
            }
        )
    return rows


def preflight_repeat(
    repeat_id,
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    preregistration = load_json(preregistration_path)
    lock = load_json(lock_path)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    order = source_telemetry.exact_row_order(treatment, int(probe["random_seed"]))
    actual_indices = order[: int(probe["micro_steps_per_repeat"])]
    actual_ids = [treatment[index]["id"] for index in actual_indices]
    frozen_rows = validate_bindings(preregistration["frozen_inputs"])
    lock_rows = validate_bindings(lock["repo_bindings"])
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "repeat_id_authorized": repeat_id in probe["repeat_ids"],
        "frozen_inputs": all(row["match"] for row in frozen_rows),
        "execution_lock": all(row["match"] for row in lock_rows),
        "execution_authorized": lock["authorization"]["gradient_only_repeats"],
        "exact_row_indices": actual_indices == probe["row_indices"],
        "exact_row_ids": actual_ids == probe["row_ids"],
        "eight_micro_steps": (
            probe["micro_steps_per_repeat"] == probe["gradient_accumulation"] == 8
        ),
        "zero_optimizer_steps": probe["optimizer_steps"] == 0,
        "repeat_result_absent": not repeat_path(repeat_id).exists(),
        "summary_absent": not DEFAULT_SUMMARY_JSON.exists() and not DEFAULT_SUMMARY_MD.exists(),
    }
    return {
        "schema": "uruha_rightbrain_gradient_reproducibility_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat_id": repeat_id,
        "passed": all(checks.values()),
        "checks": checks,
        "frozen_input_bindings": frozen_rows,
        "execution_lock_bindings": lock_rows,
        "actual_row_indices": actual_indices,
        "actual_row_ids": actual_ids,
    }


def execute_repeat(
    repeat_id,
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Gradient reproducibility execution requires offline mode")
    validation = preflight_repeat(repeat_id, preregistration_path, lock_path)
    if not validation["passed"]:
        raise RuntimeError(f"Gradient reproducibility preflight failed for repeat {repeat_id}")
    preregistration = load_json(preregistration_path)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    source_result = load_json(source_telemetry.DEFAULT_RESULT_JSON)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    tokenizer = pilot.load_tokenizer(training_preregistration)
    dataset = pilot.FixedLengthContractDataset(
        treatment,
        tokenizer,
        int(probe["fixed_allocated_sequence_length"]),
    )
    process = psutil.Process()
    started = time.perf_counter()
    pilot._seed_everything(int(probe["random_seed"]))
    model_contract = training_preregistration["local_model_contract"]
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=32,
        lora_alpha=24,
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
    before_hash = source_telemetry.parameter_sha256(parameters)
    losses = []
    for index in probe["row_indices"]:
        batch = {key: value.unsqueeze(0) for key, value in dataset[index].items()}
        loss = model(**pilot._move(batch, device)).loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss at treatment row index {index}")
        losses.append(float(loss.detach().cpu()))
        (loss / int(probe["gradient_accumulation"])).backward()
    telemetry = source_telemetry.gradient_telemetry(parameters)
    after_hash = source_telemetry.parameter_sha256(parameters)
    unchanged = before_hash == after_hash
    source_losses_equal = losses == source_result["losses"]
    valid = (
        source_losses_equal
        and telemetry["all_gradient_elements_finite"]
        and telemetry["missing_gradient_parameter_count"] == 0
        and unchanged
    )
    result = {
        "schema": "uruha_rightbrain_gradient_reproducibility_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat_id": repeat_id,
        "preflight": validation,
        "probe": probe,
        "losses": losses,
        "source_losses_equal": source_losses_equal,
        "telemetry": telemetry,
        "parameter_integrity": {
            "sha256_before_backward": before_hash,
            "sha256_after_backward": after_hash,
            "unchanged": unchanged,
        },
        "process": {
            "pid": process.pid,
            "create_time": process.create_time(),
            "torch_version": torch.__version__,
            "device": str(device),
            "duration_seconds": time.perf_counter() - started,
        },
        "decision": {
            "valid": valid,
            "authorize_optimizer_or_training_change": False,
            "authorize_production": False,
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(repeat_path(repeat_id), result)
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return result


def group_vector(result, keys):
    by_key = {
        (row["projection"], row["lora_side"]): float(row["norm"])
        for row in result["telemetry"]["norm_by_projection_and_lora_side"]
    }
    return [by_key.get(key, 0.0) for key in keys]


def cosine(left, right):
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / max(left_norm * right_norm, 1e-300)


def classify_summary(norms, pairwise_cosines, preregistration):
    hypothesis = preregistration["falsifiable_hypothesis"]
    mean = statistics.fmean(norms)
    coefficient_of_variation = statistics.pstdev(norms) / mean
    max_to_min_ratio = max(norms) / min(norms)
    minimum_cosine = min(pairwise_cosines)
    stable_gate = hypothesis["stable_if_all"]
    unstable_gate = hypothesis["unstable_if_any"]
    stable = (
        coefficient_of_variation
        <= stable_gate["total_norm_coefficient_of_variation_maximum"]
        and max_to_min_ratio <= stable_gate["total_norm_max_to_min_ratio_maximum"]
        and minimum_cosine >= stable_gate["minimum_pairwise_group_profile_cosine"]
    )
    unstable = (
        coefficient_of_variation
        >= unstable_gate["total_norm_coefficient_of_variation_minimum"]
        or max_to_min_ratio >= unstable_gate["total_norm_max_to_min_ratio_minimum"]
        or minimum_cosine
        < unstable_gate["minimum_pairwise_group_profile_cosine_below"]
    )
    median = statistics.median(norms)
    historical_a = float(preregistration["problem"]["historical_norm_a"])
    historical_b = float(preregistration["problem"]["historical_norm_b"])
    error_a = abs(median - historical_a) / historical_a
    error_b = abs(median - historical_b) / historical_b
    match_max = float(hypothesis["historical_match_relative_error_maximum"])
    if stable and error_a <= match_max:
        outcome = "stable_matches_historical_403_728"
        next_step = "audit_the_2_878972_execution_path_only"
    elif stable and error_b <= match_max:
        outcome = "stable_matches_historical_2_878972"
        next_step = "audit_the_403_728180_execution_path_only"
    elif stable:
        outcome = "stable_matches_neither_historical_scale"
        next_step = "audit_both_historical_execution_paths"
    elif unstable:
        outcome = "gradient_reconstruction_unstable_across_processes"
        next_step = "isolate_checkpointing_dropout_and_device_determinism"
    else:
        outcome = "gradient_reproducibility_inconclusive"
        next_step = "design_stronger_zero_update_reproducibility_audit"
    return {
        "outcome": outcome,
        "hypothesis_confirmed": stable,
        "unstable": unstable,
        "mean_total_norm": mean,
        "median_total_norm": median,
        "coefficient_of_variation": coefficient_of_variation,
        "max_to_min_ratio": max_to_min_ratio,
        "minimum_pairwise_group_profile_cosine": minimum_cosine,
        "median_relative_error_vs_403_728": error_a,
        "median_relative_error_vs_2_878972": error_b,
        "maximum_positive_authorization": next_step,
        "authorize_optimizer_or_training_change": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }


def render_summary(summary):
    decision = summary["decision"]
    lines = [
        "# RightBrain 梯度重現性稽核",
        "",
        f"- 判定：`{decision['outcome']}`",
        f"- 三次 norm：`{summary['total_gradient_norms']}`",
        f"- 變異係數：`{decision['coefficient_of_variation']:.8f}`",
        f"- 最大／最小：`{decision['max_to_min_ratio']:.8f}`",
        f"- 最低群組 cosine：`{decision['minimum_pairwise_group_profile_cosine']:.8f}`",
        f"- 三個獨立 process：`{summary['process_isolation']['passed']}`",
        "- optimizer step：`0`",
        "- 正式 runtime 修改：`0`",
        "",
        "本稽核只判斷 backward 梯度是否可重現，不評估人格或聊天品質。",
    ]
    return "\n".join(lines) + "\n"


def aggregate(preregistration_path=DEFAULT_PREREGISTRATION):
    if DEFAULT_SUMMARY_JSON.exists() or DEFAULT_SUMMARY_MD.exists():
        raise RuntimeError("Gradient reproducibility summary already exists")
    preregistration = load_json(preregistration_path)
    repeat_ids = preregistration["exact_probe"]["repeat_ids"]
    results = [load_json(repeat_path(repeat_id)) for repeat_id in repeat_ids]
    valid = all(result["decision"]["valid"] for result in results)
    identities = {
        (result["process"]["pid"], result["process"]["create_time"])
        for result in results
    }
    process_isolation = len(identities) == len(results)
    keys = sorted(
        {
            (row["projection"], row["lora_side"])
            for result in results
            for row in result["telemetry"]["norm_by_projection_and_lora_side"]
        }
    )
    vectors = [group_vector(result, keys) for result in results]
    pairwise = [
        {
            "left_repeat": repeat_ids[left],
            "right_repeat": repeat_ids[right],
            "cosine": cosine(vectors[left], vectors[right]),
        }
        for left, right in combinations(range(len(results)), 2)
    ]
    norms = [float(result["telemetry"]["total_gradient_norm"]) for result in results]
    decision = classify_summary(
        norms,
        [row["cosine"] for row in pairwise],
        preregistration,
    )
    decision["valid"] = valid and process_isolation
    if not decision["valid"]:
        decision.update(
            {
                "outcome": "invalid_reproducibility_audit",
                "hypothesis_confirmed": False,
                "unstable": False,
                "maximum_positive_authorization": "none",
            }
        )
    summary = {
        "schema": "uruha_rightbrain_gradient_reproducibility_summary_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat_ids": repeat_ids,
        "repeat_paths": [str(repeat_path(repeat_id).relative_to(ROOT)) for repeat_id in repeat_ids],
        "total_gradient_norms": norms,
        "pairwise_group_profile_cosines": pairwise,
        "process_isolation": {
            "identities": [
                {
                    "repeat_id": result["repeat_id"],
                    "pid": result["process"]["pid"],
                    "create_time": result["process"]["create_time"],
                }
                for result in results
            ],
            "passed": process_isolation,
        },
        "all_repeat_validity_passed": valid,
        "decision": decision,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(DEFAULT_SUMMARY_JSON, summary)
    construction.atomic_text(DEFAULT_SUMMARY_MD, render_summary(summary))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-repeat", type=int)
    parser.add_argument("--execute-repeat", type=int)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    selected = sum(
        value is not None and value is not False
        for value in (args.preflight_repeat, args.execute_repeat, args.aggregate)
    )
    if selected != 1:
        parser.error("Choose exactly one action")
    if args.preflight_repeat is not None:
        result = preflight_repeat(args.preflight_repeat)
    elif args.execute_repeat is not None:
        result = execute_repeat(args.execute_repeat)["decision"]
    else:
        result = aggregate()["decision"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
