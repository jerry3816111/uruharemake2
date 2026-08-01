#!/usr/bin/env python3
"""Run the AdamW first-step clipping diagnostic against the valid gradient control."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import statistics
import time
from pathlib import Path

import torch

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_adamw_clipping_effect_v1 as v1
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_adamw_clipping_effect_v2"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_adamw_clipping_effect_v2_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_adamw_clipping_effect_v2_execution_lock.json"
)
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_adamw_clipping_effect_v2_result.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_adamw_clipping_effect_v2_result.md"


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


def relative_error(left, right):
    return abs(float(left) - float(right)) / max(abs(float(right)), 1e-300)


def preflight(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    preregistration = load_json(preregistration_path)
    lock = load_json(lock_path)
    crosscheck = load_json(
        ROOT / "reports/rightbrain_gradient_norm_crosscheck_v1_result.json"
    )
    treatment = load_json(construction.DEFAULT_TREATMENT)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    optimizer = preregistration["optimizer_contract"]
    schedule = training_preregistration["training_schedule"]
    order = source_telemetry.exact_row_order(treatment, int(probe["random_seed"]))
    actual_indices = order[: int(probe["micro_steps"])]
    actual_ids = [treatment[index]["id"] for index in actual_indices]
    frozen_rows = validate_bindings(preregistration["frozen_inputs"])
    lock_rows = validate_bindings(lock["repo_bindings"])
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_inputs": all(row["match"] for row in frozen_rows),
        "execution_lock": all(row["match"] for row in lock_rows),
        "execution_authorized": lock["authorization"]["zero_update_adamw_simulation"],
        "crosscheck_valid": crosscheck["decision"]["valid"],
        "control_norm_bound": (
            crosscheck["measurements"]["mps_official_mean"]
            == preregistration["problem"]["valid_control_gradient_norm"]
        ),
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
        "effect_thresholds_unchanged": (
            preregistration["falsifiable_hypothesis"]["near_equivalent_if_all"]
            == load_json(v1.DEFAULT_PREREGISTRATION)["falsifiable_hypothesis"][
                "near_equivalent_if_all"
            ]
            and preregistration["falsifiable_hypothesis"]["material_effect_if_any"]
            == load_json(v1.DEFAULT_PREREGISTRATION)["falsifiable_hypothesis"][
                "material_effect_if_any"
            ]
        ),
        "result_absent": not DEFAULT_RESULT_JSON.exists() and not DEFAULT_RESULT_MD.exists(),
    }
    return {
        "schema": "uruha_rightbrain_adamw_clipping_effect_preflight_v2",
        "experiment_id": EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "frozen_input_bindings": frozen_rows,
        "execution_lock_bindings": lock_rows,
        "actual_row_indices": actual_indices,
        "actual_row_ids": actual_ids,
    }


def render_markdown(result):
    metrics = result["simulation"]["overall"]
    return "\n".join(
        [
            "# RightBrain AdamW 首步裁切效果診斷 v2",
            "",
            f"- 判定：`{result['decision']['outcome']}`",
            f"- 有效 raw gradient norm：`{result['gradient']['total_norm']:.10f}`",
            f"- 裁切係數：`{result['simulation']['clip_coefficient']:.10f}`",
            f"- 未裁切更新 L2：`{metrics['total_update_l2_unclipped']:.10f}`",
            f"- 裁切更新 L2：`{metrics['total_update_l2_clipped']:.10f}`",
            f"- 更新 L2 比率：`{metrics['clipped_to_unclipped_l2_ratio']:.10f}`",
            f"- 相對更新差：`{metrics['relative_l2_difference']:.10f}`",
            f"- 更新方向 cosine：`{metrics['cosine_similarity']:.10f}`",
            f"- 權重前後一致：`{result['parameter_integrity']['unchanged']}`",
            "- optimizer step：`0`",
            "",
            "本結果只判斷第一步理論效果，不代表小型訓練 pilot 一定會改善模型。",
        ]
    ) + "\n"


def execute(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("AdamW v2 execution requires offline mode")
    validation = preflight(preregistration_path, lock_path)
    if not validation["passed"]:
        raise RuntimeError("AdamW v2 preflight failed")
    preregistration = load_json(preregistration_path)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    stable_repeat = load_json(
        ROOT / "reports/rightbrain_gradient_reproducibility_v1_repeat_1.json"
    )
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
    gradients = [parameter.grad for _, parameter in parameters if parameter.grad is not None]
    total_norm = float(
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
    simulation = v1.simulate_updates(
        parameters,
        total_gradient_norm=total_norm,
        contract=preregistration["optimizer_contract"],
    )
    after_hash = source_telemetry.parameter_sha256(parameters)
    unchanged = before_hash == after_hash
    control_norm = float(preregistration["problem"]["valid_control_gradient_norm"])
    expected_coefficient = float(preregistration["problem"]["expected_clip_coefficient"])
    norm_error = relative_error(total_norm, control_norm)
    coefficient_error = relative_error(
        simulation["clip_coefficient"],
        expected_coefficient,
    )
    valid = (
        losses == stable_repeat["losses"]
        and len(gradients) == len(parameters)
        and norm_error
        <= preregistration["integrity_tolerances"][
            "gradient_norm_relative_error_maximum"
        ]
        and coefficient_error
        <= preregistration["integrity_tolerances"][
            "clip_coefficient_relative_error_maximum"
        ]
        and unchanged
    )
    decision = v1.classify(simulation, preregistration["falsifiable_hypothesis"])
    decision["valid"] = valid
    if not valid:
        decision.update(
            {
                "outcome": "invalid_adamw_clipping_effect_v2",
                "hypothesis_confirmed": False,
                "material_effect": False,
                "maximum_positive_authorization": "none",
            }
        )
    result = {
        "schema": "uruha_rightbrain_adamw_clipping_effect_result_v2",
        "experiment_id": EXPERIMENT_ID,
        "preflight": validation,
        "probe": probe,
        "optimizer_contract": preregistration["optimizer_contract"],
        "losses": losses,
        "mean_loss": statistics.fmean(losses),
        "gradient": {
            "total_norm": total_norm,
            "control_norm": control_norm,
            "relative_error_vs_control": norm_error,
            "parameter_count_with_gradient": len(gradients),
            "trainable_parameter_tensor_count": len(parameters),
        },
        "simulation": simulation,
        "clip_coefficient_relative_error": coefficient_error,
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
        parser.error("Choose exactly one action")
    result = preflight() if args.preflight else execute()["decision"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
