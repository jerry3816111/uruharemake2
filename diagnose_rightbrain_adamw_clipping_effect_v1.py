#!/usr/bin/env python3
"""Compare clipped and unclipped first-step AdamW deltas without model updates."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path

import torch

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_adamw_clipping_effect_v1"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_adamw_clipping_effect_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_adamw_clipping_effect_v1_execution_lock.json"
)
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_adamw_clipping_effect_v1_result.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_adamw_clipping_effect_v1_result.md"


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


def preflight(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    preregistration = load_json(preregistration_path)
    lock = load_json(lock_path)
    source_result = load_json(source_telemetry.DEFAULT_RESULT_JSON)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    optimizer = preregistration["optimizer_contract"]
    schedule = training_preregistration["training_schedule"]
    order = source_telemetry.exact_row_order(treatment, int(probe["random_seed"]))
    actual_indices = order[: int(probe["micro_steps"])]
    actual_ids = [treatment[index]["id"] for index in actual_indices]
    frozen_rows = validate_bindings(preregistration["frozen_inputs"])
    lock_rows = validate_bindings(lock["repo_bindings"])
    prior_norm = float(source_result["telemetry"]["total_gradient_norm"])
    expected_norm = float(preregistration["problem"]["prior_total_gradient_norm"])
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_inputs": all(row["match"] for row in frozen_rows),
        "execution_lock": all(row["match"] for row in lock_rows),
        "execution_authorized": lock["authorization"]["zero_update_adamw_simulation"],
        "source_telemetry_valid": source_result["decision"]["valid"],
        "source_norm_bound": prior_norm == expected_norm,
        "exact_row_indices": actual_indices == probe["row_indices"],
        "exact_row_ids": actual_ids == probe["row_ids"],
        "eight_micro_steps": probe["micro_steps"] == probe["gradient_accumulation"] == 8,
        "zero_optimizer_steps": probe["optimizer_steps"] == 0,
        "learning_rate": float(schedule["learning_rate"]) == optimizer["learning_rate"],
        "weight_decay": float(schedule["weight_decay"]) == optimizer["weight_decay"],
        "optimizer_epsilon": float(schedule["optimizer_epsilon"]) == optimizer["epsilon"],
        "maximum_gradient_norm": (
            float(schedule["maximum_gradient_norm"])
            == optimizer["maximum_gradient_norm"]
        ),
        "result_absent": not DEFAULT_RESULT_JSON.exists() and not DEFAULT_RESULT_MD.exists(),
    }
    return {
        "schema": "uruha_rightbrain_adamw_clipping_effect_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "frozen_input_bindings": frozen_rows,
        "execution_lock_bindings": lock_rows,
        "actual_row_indices": actual_indices,
        "actual_row_ids": actual_ids,
    }


def adamw_first_step_delta(parameter, gradient, *, scale, learning_rate, weight_decay, epsilon):
    scaled_gradient = gradient * scale
    adaptive = scaled_gradient / (torch.abs(scaled_gradient) + epsilon)
    return -learning_rate * (weight_decay * parameter + adaptive)


def _empty_accumulator():
    return {
        "elements": 0,
        "parameter_sq": 0.0,
        "unclipped_sq": 0.0,
        "clipped_sq": 0.0,
        "difference_sq": 0.0,
        "dot": 0.0,
        "adaptive_unclipped_sq": 0.0,
        "adaptive_clipped_sq": 0.0,
        "adaptive_difference_sq": 0.0,
        "weight_decay_sq": 0.0,
        "more_than_1pct_difference": 0,
    }


def _accumulate(target, parameter, gradient, *, clip_coefficient, contract):
    learning_rate = float(contract["learning_rate"])
    weight_decay = float(contract["weight_decay"])
    epsilon = float(contract["epsilon"])
    unclipped = adamw_first_step_delta(
        parameter,
        gradient,
        scale=1.0,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        epsilon=epsilon,
    )
    clipped = adamw_first_step_delta(
        parameter,
        gradient,
        scale=clip_coefficient,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        epsilon=epsilon,
    )
    adaptive_unclipped = adamw_first_step_delta(
        torch.zeros_like(parameter),
        gradient,
        scale=1.0,
        learning_rate=learning_rate,
        weight_decay=0.0,
        epsilon=epsilon,
    )
    adaptive_clipped = adamw_first_step_delta(
        torch.zeros_like(parameter),
        gradient,
        scale=clip_coefficient,
        learning_rate=learning_rate,
        weight_decay=0.0,
        epsilon=epsilon,
    )
    decay = -learning_rate * weight_decay * parameter
    difference = clipped - unclipped
    adaptive_difference = adaptive_clipped - adaptive_unclipped
    denominator = torch.clamp(torch.abs(unclipped), min=torch.finfo(unclipped.dtype).tiny)
    target["elements"] += parameter.numel()
    target["parameter_sq"] += float(torch.sum(parameter.double().square()))
    target["unclipped_sq"] += float(torch.sum(unclipped.double().square()))
    target["clipped_sq"] += float(torch.sum(clipped.double().square()))
    target["difference_sq"] += float(torch.sum(difference.double().square()))
    target["dot"] += float(torch.sum(unclipped.double() * clipped.double()))
    target["adaptive_unclipped_sq"] += float(
        torch.sum(adaptive_unclipped.double().square())
    )
    target["adaptive_clipped_sq"] += float(
        torch.sum(adaptive_clipped.double().square())
    )
    target["adaptive_difference_sq"] += float(
        torch.sum(adaptive_difference.double().square())
    )
    target["weight_decay_sq"] += float(torch.sum(decay.double().square()))
    target["more_than_1pct_difference"] += int(
        torch.sum(torch.abs(difference) / denominator > 0.01)
    )


def _finalize(accumulator):
    unclipped_l2 = math.sqrt(accumulator["unclipped_sq"])
    clipped_l2 = math.sqrt(accumulator["clipped_sq"])
    difference_l2 = math.sqrt(accumulator["difference_sq"])
    parameter_l2 = math.sqrt(accumulator["parameter_sq"])
    adaptive_unclipped_l2 = math.sqrt(accumulator["adaptive_unclipped_sq"])
    adaptive_clipped_l2 = math.sqrt(accumulator["adaptive_clipped_sq"])
    adaptive_difference_l2 = math.sqrt(accumulator["adaptive_difference_sq"])
    cosine = accumulator["dot"] / max(unclipped_l2 * clipped_l2, 1e-300)
    elements = accumulator["elements"]
    return {
        "elements": elements,
        "parameter_l2": parameter_l2,
        "total_update_l2_unclipped": unclipped_l2,
        "total_update_l2_clipped": clipped_l2,
        "clipped_to_unclipped_l2_ratio": clipped_l2 / max(unclipped_l2, 1e-300),
        "difference_l2": difference_l2,
        "relative_l2_difference": difference_l2 / max(unclipped_l2, 1e-300),
        "cosine_similarity": cosine,
        "relative_parameter_l2_change_unclipped": unclipped_l2 / max(parameter_l2, 1e-300),
        "relative_parameter_l2_change_clipped": clipped_l2 / max(parameter_l2, 1e-300),
        "adaptive_update_l2_unclipped": adaptive_unclipped_l2,
        "adaptive_update_l2_clipped": adaptive_clipped_l2,
        "adaptive_relative_l2_difference": (
            adaptive_difference_l2 / max(adaptive_unclipped_l2, 1e-300)
        ),
        "weight_decay_update_l2": math.sqrt(accumulator["weight_decay_sq"]),
        "elements_with_more_than_1pct_relative_update_difference": accumulator[
            "more_than_1pct_difference"
        ],
        "fraction_with_more_than_1pct_relative_update_difference": (
            accumulator["more_than_1pct_difference"] / max(elements, 1)
        ),
    }


def simulate_updates(parameters, *, total_gradient_norm, contract):
    maximum_gradient_norm = float(contract["maximum_gradient_norm"])
    clip_coefficient = min(
        1.0,
        maximum_gradient_norm / (float(total_gradient_norm) + 1e-6),
    )
    total = _empty_accumulator()
    groups = defaultdict(_empty_accumulator)
    for name, parameter in parameters:
        if parameter.grad is None:
            continue
        parameter_cpu = parameter.detach().float().cpu()
        gradient_cpu = parameter.grad.detach().float().cpu()
        _accumulate(
            total,
            parameter_cpu,
            gradient_cpu,
            clip_coefficient=clip_coefficient,
            contract=contract,
        )
        group = (
            source_telemetry.projection_group(name),
            source_telemetry.lora_side(name),
        )
        _accumulate(
            groups[group],
            parameter_cpu,
            gradient_cpu,
            clip_coefficient=clip_coefficient,
            contract=contract,
        )
    return {
        "clip_coefficient": clip_coefficient,
        "overall": _finalize(total),
        "by_projection_and_lora_side": [
            {
                "projection": projection,
                "lora_side": side,
                **_finalize(accumulator),
            }
            for (projection, side), accumulator in sorted(groups.items())
        ],
    }


def classify(metrics, hypothesis):
    overall = metrics["overall"]
    equivalent = hypothesis["near_equivalent_if_all"]
    material = hypothesis["material_effect_if_any"]
    near_equivalent = (
        overall["relative_l2_difference"]
        <= equivalent["relative_l2_difference_maximum"]
        and overall["cosine_similarity"] >= equivalent["cosine_similarity_minimum"]
        and equivalent["clipped_to_unclipped_l2_ratio_minimum"]
        <= overall["clipped_to_unclipped_l2_ratio"]
        <= equivalent["clipped_to_unclipped_l2_ratio_maximum"]
    )
    material_effect = (
        overall["relative_l2_difference"]
        >= material["relative_l2_difference_minimum"]
        or overall["cosine_similarity"] < material["cosine_similarity_below"]
        or overall["clipped_to_unclipped_l2_ratio"]
        < material["clipped_to_unclipped_l2_ratio_below"]
        or overall["clipped_to_unclipped_l2_ratio"]
        > material["clipped_to_unclipped_l2_ratio_above"]
    )
    if near_equivalent:
        outcome = "first_step_updates_near_equivalent"
        authorization = "authorize_one_learning_rate_step_scale_diagnostic_only"
    elif material_effect:
        outcome = "first_step_clipping_has_material_effect"
        authorization = "authorize_preregistration_of_one_matched_small_training_pilot_only"
    else:
        outcome = "first_step_clipping_effect_inconclusive"
        authorization = "authorize_stronger_zero_update_diagnostic_only"
    return {
        "outcome": outcome,
        "hypothesis_confirmed": near_equivalent,
        "material_effect": material_effect,
        "maximum_positive_authorization": authorization,
        "authorize_model_training": False,
        "authorize_training_parameter_change": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }


def render_markdown(result):
    metrics = result["simulation"]["overall"]
    decision = result["decision"]
    return "\n".join(
        [
            "# RightBrain AdamW 首步裁切效果診斷",
            "",
            f"- 判定：`{decision['outcome']}`",
            f"- raw gradient norm：`{result['gradient']['total_norm']:.6f}`",
            f"- 裁切係數：`{result['simulation']['clip_coefficient']:.10f}`",
            f"- 未裁切更新 L2：`{metrics['total_update_l2_unclipped']:.10f}`",
            f"- 裁切更新 L2：`{metrics['total_update_l2_clipped']:.10f}`",
            f"- L2 比率：`{metrics['clipped_to_unclipped_l2_ratio']:.10f}`",
            f"- 相對更新差：`{metrics['relative_l2_difference']:.10f}`",
            f"- 更新方向 cosine：`{metrics['cosine_similarity']:.10f}`",
            f"- 權重前後一致：`{result['parameter_integrity']['unchanged']}`",
            "- optimizer step：`0`",
            "- 正式 runtime 修改：`0`",
            "",
            "本結果只比較第一個 AdamW 步驟的理論更新，不訓練或儲存模型。",
        ]
    ) + "\n"


def execute(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("AdamW effect execution requires offline local-model mode")
    validation = preflight(preregistration_path, lock_path)
    if not validation["passed"]:
        raise RuntimeError("AdamW effect preflight failed")
    preregistration = load_json(preregistration_path)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    tokenizer = pilot.load_tokenizer(training_preregistration)
    dataset = pilot.FixedLengthContractDataset(
        treatment,
        tokenizer,
        int(probe["fixed_allocated_sequence_length"]),
    )
    started = time.perf_counter()
    pilot._seed_everything(int(probe["random_seed"]))
    model_contract = training_preregistration["local_model_contract"]
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=32,
        lora_alpha=24,
        lora_dropout=float(training_preregistration["training_schedule"]["adapter_dropout"]),
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
    gradients = [parameter.grad for _, parameter in parameters if parameter.grad is not None]
    total_norm_tensor = torch.nn.utils.get_total_norm(
        gradients,
        norm_type=2.0,
        error_if_nonfinite=True,
        foreach=False,
    )
    total_norm = float(total_norm_tensor.detach().float().cpu())
    simulation = simulate_updates(
        parameters,
        total_gradient_norm=total_norm,
        contract=preregistration["optimizer_contract"],
    )
    after_hash = source_telemetry.parameter_sha256(parameters)
    unchanged = before_hash == after_hash
    prior_norm = float(preregistration["problem"]["prior_total_gradient_norm"])
    norm_relative_error = abs(total_norm - prior_norm) / prior_norm
    tolerance = float(preregistration["integrity_tolerances"]["gradient_norm_relative_error_maximum"])
    valid = (
        all(math.isfinite(loss) for loss in losses)
        and len(gradients) == len(parameters)
        and math.isfinite(total_norm)
        and norm_relative_error <= tolerance
        and unchanged
    )
    decision = classify(simulation, preregistration["falsifiable_hypothesis"])
    decision["valid"] = valid
    if not valid:
        decision.update(
            {
                "outcome": "invalid_diagnostic",
                "hypothesis_confirmed": False,
                "material_effect": False,
                "maximum_positive_authorization": "none",
            }
        )
    result = {
        "schema": "uruha_rightbrain_adamw_clipping_effect_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "preflight": validation,
        "probe": probe,
        "optimizer_contract": preregistration["optimizer_contract"],
        "losses": losses,
        "mean_loss": statistics.fmean(losses),
        "gradient": {
            "total_norm": total_norm,
            "prior_total_norm": prior_norm,
            "relative_error_vs_prior": norm_relative_error,
            "parameter_count_with_gradient": len(gradients),
            "trainable_parameter_tensor_count": len(parameters),
        },
        "simulation": simulation,
        "parameter_integrity": {
            "sha256_before_backward": before_hash,
            "sha256_after_simulation": after_hash,
            "unchanged": unchanged,
        },
        "runtime": {
            "torch_version": torch.__version__,
            "device": str(device),
            "duration_seconds": time.perf_counter() - started,
        },
        "decision": decision,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(DEFAULT_RESULT_JSON, result)
    construction.atomic_text(DEFAULT_RESULT_MD, render_markdown(result))
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.preflight == args.execute:
        parser.error("Choose exactly one of --preflight or --execute")
    result = preflight() if args.preflight else execute()
    print(json.dumps(result if args.preflight else result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
