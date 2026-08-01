#!/usr/bin/env python3
"""Measure one frozen accumulated LoRA gradient without updating the model."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path

import psutil
import torch
from torch.utils.data import RandomSampler

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_training_signal_telemetry_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_training_signal_telemetry_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_training_signal_telemetry_v1_execution_lock.json"
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_training_signal_telemetry_v1_result.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_training_signal_telemetry_v1_result.md"


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


def exact_row_order(rows, seed):
    generator = torch.Generator().manual_seed(seed)
    return list(RandomSampler(range(len(rows)), generator=generator))


def preflight(preregistration_path=DEFAULT_PREREGISTRATION, lock_path=DEFAULT_EXECUTION_LOCK):
    preregistration = load_json(preregistration_path)
    lock = load_json(lock_path)
    frozen_rows = validate_bindings(preregistration["frozen_inputs"])
    lock_rows = validate_bindings(lock["repo_bindings"])
    prior_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    prior_inputs = construction.validate_frozen_inputs(prior_preregistration)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    order = exact_row_order(treatment, int(probe["random_seed"]))
    actual_indices = order[: int(probe["micro_steps"])]
    actual_ids = [treatment[index]["id"] for index in actual_indices]
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_inputs": all(row["match"] for row in frozen_rows),
        "execution_lock": all(row["match"] for row in lock_rows),
        "execution_authorized": lock["authorization"]["exact_zero_update_telemetry"],
        "prior_model_inputs": prior_inputs["passed"],
        "exact_row_indices": actual_indices == probe["row_indices"],
        "exact_row_ids": actual_ids == probe["row_ids"],
        "eight_micro_steps": probe["micro_steps"] == probe["gradient_accumulation"] == 8,
        "zero_optimizer_updates": probe["optimizer_updates"] == 0,
        "result_absent": not DEFAULT_RESULT_JSON.exists() and not DEFAULT_RESULT_MD.exists(),
    }
    return {
        "schema": "uruha_rightbrain_training_signal_telemetry_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "frozen_input_bindings": frozen_rows,
        "execution_lock_bindings": lock_rows,
        "prior_model_input_validation": prior_inputs,
        "actual_row_indices": actual_indices,
        "actual_row_ids": actual_ids,
    }


def parameter_sha256(parameters):
    digest = hashlib.sha256()
    for name, parameter in parameters:
        tensor = parameter.detach().float().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def projection_group(name):
    for projection in ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"):
        if f".{projection}." in name:
            return projection
    return "other"


def lora_side(name):
    if ".lora_A." in name:
        return "lora_A"
    if ".lora_B." in name:
        return "lora_B"
    return "other"


def layer_group(name):
    match = re.search(r"\.layers\.(\d+)\.", name)
    return int(match.group(1)) if match else -1


def gradient_telemetry(parameters):
    gradients = [parameter.grad for _, parameter in parameters if parameter.grad is not None]
    total_norm = torch.nn.utils.get_total_norm(
        gradients,
        norm_type=2.0,
        error_if_nonfinite=True,
        foreach=False,
    )
    parameter_rows = []
    group_squares = defaultdict(float)
    layer_squares = defaultdict(float)
    finite_elements = total_elements = 0
    for name, parameter in parameters:
        gradient = parameter.grad
        if gradient is None:
            continue
        gradient_float = gradient.detach().float()
        finite_elements += int(torch.isfinite(gradient_float).sum().item())
        total_elements += gradient_float.numel()
        norm = float(torch.linalg.vector_norm(gradient_float).cpu())
        maximum = float(torch.max(torch.abs(gradient_float)).cpu())
        row = {
            "name": name,
            "elements": gradient_float.numel(),
            "norm": norm,
            "maximum_absolute_gradient": maximum,
            "projection": projection_group(name),
            "lora_side": lora_side(name),
            "layer": layer_group(name),
        }
        parameter_rows.append(row)
        group_squares[(row["projection"], row["lora_side"])] += norm * norm
        layer_squares[row["layer"]] += norm * norm
    total_norm_value = float(total_norm.detach().float().cpu())
    return {
        "total_gradient_norm": total_norm_value,
        "gradient_element_count": total_elements,
        "finite_gradient_element_count": finite_elements,
        "all_gradient_elements_finite": finite_elements == total_elements,
        "gradient_rms": total_norm_value / math.sqrt(max(total_elements, 1)),
        "missing_gradient_parameter_count": sum(
            parameter.grad is None for _, parameter in parameters
        ),
        "top_parameter_gradient_norms": sorted(
            parameter_rows,
            key=lambda row: row["norm"],
            reverse=True,
        )[:20],
        "norm_by_projection_and_lora_side": [
            {
                "projection": projection,
                "lora_side": side,
                "norm": math.sqrt(square),
            }
            for (projection, side), square in sorted(group_squares.items())
        ],
        "norm_by_layer": [
            {"layer": layer, "norm": math.sqrt(square)}
            for layer, square in sorted(layer_squares.items())
        ],
    }


def render_markdown(result):
    telemetry = result["telemetry"]
    decision = result["decision"]
    lines = [
        "# RightBrain 訓練信號尺度診斷",
        "",
        f"- 判定：`{decision['outcome']}`",
        f"- 8 筆平均 loss：`{statistics.fmean(result['losses']):.6f}`",
        f"- 裁切前總梯度 norm：`{telemetry['total_gradient_norm']:.6f}`",
        f"- 相對 0.3 門檻倍率：`{decision['gradient_norm_to_threshold_ratio']:.2f}x`",
        f"- 理論裁切係數：`{decision['theoretical_clip_coefficient']:.10f}`",
        f"- 權重前後一致：`{result['parameter_integrity']['unchanged']}`",
        "- optimizer step：`0`",
        "- 正式 runtime 修改：`0`",
        "",
        "本診斷只量測第一次累積梯度，不訓練或儲存模型。",
    ]
    return "\n".join(lines) + "\n"


def execute(preregistration_path=DEFAULT_PREREGISTRATION, lock_path=DEFAULT_EXECUTION_LOCK):
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Telemetry execution requires offline local-model mode")
    validation = preflight(preregistration_path, lock_path)
    if not validation["passed"]:
        raise RuntimeError("Telemetry preflight failed")
    preregistration = load_json(preregistration_path)
    prior_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    tokenizer = pilot.load_tokenizer(prior_preregistration)
    dataset = pilot.FixedLengthContractDataset(
        treatment,
        tokenizer,
        int(probe["fixed_allocated_sequence_length"]),
    )
    started = time.perf_counter()
    pilot._seed_everything(int(probe["random_seed"]))
    model_contract = prior_preregistration["local_model_contract"]
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=32,
        lora_alpha=24,
        lora_dropout=0.08,
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
    before_hash = parameter_sha256(parameters)
    losses = []
    for index in probe["row_indices"]:
        batch = {key: value.unsqueeze(0) for key, value in dataset[index].items()}
        loss = model(**pilot._move(batch, device)).loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss at treatment row index {index}")
        losses.append(float(loss.detach().cpu()))
        (loss / int(probe["gradient_accumulation"])).backward()
    telemetry = gradient_telemetry(parameters)
    after_hash = parameter_sha256(parameters)
    threshold = float(preregistration["falsifiable_hypothesis"]["configured_maximum_gradient_norm"])
    ratio = telemetry["total_gradient_norm"] / threshold
    clip_coefficient = min(1.0, threshold / (telemetry["total_gradient_norm"] + 1e-6))
    unchanged = before_hash == after_hash
    finite_losses = all(math.isfinite(loss) for loss in losses)
    valid = finite_losses and telemetry["all_gradient_elements_finite"] and unchanged
    severe = (
        valid
        and ratio
        >= float(preregistration["falsifiable_hypothesis"]["severe_clipping_ratio_minimum"])
        and clip_coefficient <= 0.01
    )
    decision = {
        "valid": valid,
        "hypothesis_confirmed": severe,
        "gradient_norm_to_threshold_ratio": ratio,
        "theoretical_clip_coefficient": clip_coefficient,
        "outcome": (
            "authorize_preregistration_of_one_training_signal_scale_repair_pilot_only"
            if severe
            else "do_not_authorize_training_scale_repair_without_new_evidence"
        ),
        "authorize_model_training": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }
    result = {
        "schema": "uruha_rightbrain_training_signal_telemetry_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "preflight": validation,
        "probe": probe,
        "runtime": {
            "torch_version": torch.__version__,
            "device": str(device),
            "trainable_parameter_count": sum(parameter.numel() for _, parameter in parameters),
            "trainable_parameter_dtype_counts": dict(
                sorted(
                    {
                        str(dtype): sum(
                            parameter.numel()
                            for _, parameter in parameters
                            if parameter.dtype == dtype
                        )
                        for dtype in {parameter.dtype for _, parameter in parameters}
                    }.items()
                )
            ),
            "duration_seconds": time.perf_counter() - started,
            "peak_process_resident_memory_bytes": psutil.Process().memory_info().rss,
        },
        "losses": losses,
        "telemetry": telemetry,
        "parameter_integrity": {
            "sha256_before_backward": before_hash,
            "sha256_after_backward": after_hash,
            "unchanged": unchanged,
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
