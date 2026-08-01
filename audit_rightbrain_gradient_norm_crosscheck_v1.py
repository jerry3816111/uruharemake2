#!/usr/bin/env python3
"""Cross-check one frozen gradient norm across MPS, CPU, and decompositions."""

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
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry
import run_rightbrain_role_curriculum_training_pilot_v1 as pilot
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_gradient_norm_crosscheck_v1"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_gradient_norm_crosscheck_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_gradient_norm_crosscheck_v1_execution_lock.json"
)
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_gradient_norm_crosscheck_v1_result.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_gradient_norm_crosscheck_v1_result.md"


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


def recompose_norm(rows):
    return math.sqrt(sum(float(row["norm"]) ** 2 for row in rows))


def relative_error(left, right):
    return abs(float(left) - float(right)) / max(abs(float(right)), 1e-300)


def preflight(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    preregistration = load_json(preregistration_path)
    lock = load_json(lock_path)
    treatment = load_json(construction.DEFAULT_TREATMENT)
    probe = preregistration["exact_probe"]
    order = source_telemetry.exact_row_order(treatment, int(probe["random_seed"]))
    actual_indices = order[: int(probe["micro_steps"])]
    actual_ids = [treatment[index]["id"] for index in actual_indices]
    frozen_rows = validate_bindings(preregistration["frozen_inputs"])
    lock_rows = validate_bindings(lock["repo_bindings"])
    stable_summary = load_json(
        ROOT / "reports/rightbrain_gradient_reproducibility_v1_summary.json"
    )
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_inputs": all(row["match"] for row in frozen_rows),
        "execution_lock": all(row["match"] for row in lock_rows),
        "execution_authorized": lock["authorization"]["zero_update_norm_crosscheck"],
        "stable_control_valid": stable_summary["decision"]["valid"],
        "stable_control_exact": stable_summary["total_gradient_norms"] == [
            preregistration["problem"]["reproducible_control_norm"]
        ] * 3,
        "exact_row_indices": actual_indices == probe["row_indices"],
        "exact_row_ids": actual_ids == probe["row_ids"],
        "eight_micro_steps": probe["micro_steps"] == probe["gradient_accumulation"] == 8,
        "zero_optimizer_steps": probe["optimizer_steps"] == 0,
        "five_mps_measurements": probe["mps_official_norm_repetitions"] == 5,
        "result_absent": not DEFAULT_RESULT_JSON.exists() and not DEFAULT_RESULT_MD.exists(),
    }
    return {
        "schema": "uruha_rightbrain_gradient_norm_crosscheck_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "frozen_input_bindings": frozen_rows,
        "execution_lock_bindings": lock_rows,
        "actual_row_indices": actual_indices,
        "actual_row_ids": actual_ids,
    }


def independent_norms(parameters, repetitions):
    gradients = [parameter.grad for _, parameter in parameters if parameter.grad is not None]
    if torch.backends.mps.is_available():
        torch.mps.synchronize()
    mps_official = [
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
        for _ in range(repetitions)
    ]
    mps_parameter_square_sum = 0.0
    cpu_float64_square_sum = 0.0
    finite_elements = total_elements = 0
    for _, parameter in parameters:
        gradient = parameter.grad
        if gradient is None:
            continue
        gradient_float = gradient.detach().float()
        mps_norm = float(torch.linalg.vector_norm(gradient_float).cpu())
        mps_parameter_square_sum += mps_norm * mps_norm
        gradient_cpu = gradient_float.cpu().double()
        cpu_float64_square_sum += float(torch.sum(gradient_cpu.square()))
        finite_elements += int(torch.isfinite(gradient_cpu).sum())
        total_elements += gradient_cpu.numel()
    return {
        "mps_official_repeated": mps_official,
        "mps_official_mean": statistics.fmean(mps_official),
        "mps_official_relative_spread": (
            (max(mps_official) - min(mps_official))
            / max(statistics.fmean(mps_official), 1e-300)
        ),
        "mps_per_parameter_recomposition": math.sqrt(mps_parameter_square_sum),
        "cpu_float64_concatenated_equivalent": math.sqrt(cpu_float64_square_sum),
        "finite_gradient_elements": finite_elements,
        "total_gradient_elements": total_elements,
        "all_gradient_elements_finite": finite_elements == total_elements,
    }


def classify(measurements, old_consistency, preregistration, unchanged):
    hypothesis = preregistration["falsifiable_hypothesis"]
    confirm = hypothesis["confirm_if_all"]
    reject = hypothesis["reject_if_any"]
    mps = measurements["mps_official_mean"]
    errors = {
        "mps_vs_cpu_float64": relative_error(
            mps,
            measurements["cpu_float64_concatenated_equivalent"],
        ),
        "mps_vs_per_parameter_recomposition": relative_error(
            mps,
            measurements["mps_per_parameter_recomposition"],
        ),
        "mps_vs_group_recomposition": relative_error(
            mps,
            measurements["group_recomposition"],
        ),
        "mps_vs_layer_recomposition": relative_error(
            mps,
            measurements["layer_recomposition"],
        ),
        "new_norm_vs_reproducible_control": relative_error(
            mps,
            preregistration["problem"]["reproducible_control_norm"],
        ),
        "old_total_vs_old_group_recomposition": relative_error(
            old_consistency["total"],
            old_consistency["group_recomposition"],
        ),
        "old_total_vs_old_layer_recomposition": relative_error(
            old_consistency["total"],
            old_consistency["layer_recomposition"],
        ),
    }
    confirmed = (
        measurements["mps_official_relative_spread"]
        <= confirm["mps_repeated_call_relative_spread_maximum"]
        and errors["mps_vs_cpu_float64"]
        <= confirm["mps_vs_cpu_float64_relative_error_maximum"]
        and errors["mps_vs_group_recomposition"]
        <= confirm["mps_vs_group_recomposition_relative_error_maximum"]
        and errors["mps_vs_layer_recomposition"]
        <= confirm["mps_vs_layer_recomposition_relative_error_maximum"]
        and errors["new_norm_vs_reproducible_control"]
        <= confirm["new_norm_vs_reproducible_control_relative_error_maximum"]
        and errors["old_total_vs_old_group_recomposition"]
        <= confirm["old_total_vs_old_group_recomposition_relative_error_maximum"]
        and errors["old_total_vs_old_layer_recomposition"]
        <= confirm["old_total_vs_old_layer_recomposition_relative_error_maximum"]
        and unchanged
    )
    rejected = (
        errors["mps_vs_cpu_float64"]
        >= reject["mps_vs_cpu_float64_relative_error_minimum"]
        or errors["new_norm_vs_reproducible_control"]
        >= reject["new_norm_vs_reproducible_control_relative_error_minimum"]
        or not measurements["all_gradient_elements_finite"]
        or not unchanged
    )
    if confirmed:
        outcome = "crosscheck_confirms_2_878972_and_supersedes_403_728_for_decisions"
        authorization = "authorize_fresh_adamw_effect_diagnostic_with_2_878972_control_only"
    elif rejected:
        outcome = "gradient_norm_crosscheck_rejected"
        authorization = "none"
    else:
        outcome = "gradient_norm_crosscheck_inconclusive"
        authorization = "authorize_stronger_zero_update_crosscheck_only"
    return {
        "outcome": outcome,
        "hypothesis_confirmed": confirmed,
        "hypothesis_rejected": rejected,
        "errors": errors,
        "maximum_positive_authorization": authorization,
        "authorize_model_training": False,
        "authorize_training_parameter_change": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }


def render_markdown(result):
    measurements = result["measurements"]
    decision = result["decision"]
    return "\n".join(
        [
            "# RightBrain 梯度 norm 交叉驗證",
            "",
            f"- 判定：`{decision['outcome']}`",
            f"- MPS 官方 norm：`{measurements['mps_official_mean']:.10f}`",
            f"- CPU float64 norm：`{measurements['cpu_float64_concatenated_equivalent']:.10f}`",
            f"- group 合成 norm：`{measurements['group_recomposition']:.10f}`",
            f"- layer 合成 norm：`{measurements['layer_recomposition']:.10f}`",
            f"- 目前控制值：`{result['reproducible_control_norm']:.10f}`",
            f"- 舊值：`{result['old_consistency']['total']:.10f}`",
            f"- 權重前後一致：`{result['parameter_integrity']['unchanged']}`",
            "- optimizer step：`0`",
            "",
            "本交叉驗證只校正訓練量測，不代表模型能力或人格提升。",
        ]
    ) + "\n"


def execute(
    preregistration_path=DEFAULT_PREREGISTRATION,
    lock_path=DEFAULT_EXECUTION_LOCK,
):
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Gradient norm crosscheck requires offline mode")
    validation = preflight(preregistration_path, lock_path)
    if not validation["passed"]:
        raise RuntimeError("Gradient norm crosscheck preflight failed")
    preregistration = load_json(preregistration_path)
    training_preregistration = load_json(pilot.DEFAULT_PREREGISTRATION)
    old_result = load_json(source_telemetry.DEFAULT_RESULT_JSON)
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
    measurements = independent_norms(
        parameters,
        int(probe["mps_official_norm_repetitions"]),
    )
    telemetry = source_telemetry.gradient_telemetry(parameters)
    measurements.update(
        {
            "group_recomposition": recompose_norm(
                telemetry["norm_by_projection_and_lora_side"]
            ),
            "layer_recomposition": recompose_norm(telemetry["norm_by_layer"]),
            "source_telemetry_total": telemetry["total_gradient_norm"],
        }
    )
    old_consistency = {
        "total": old_result["telemetry"]["total_gradient_norm"],
        "group_recomposition": recompose_norm(
            old_result["telemetry"]["norm_by_projection_and_lora_side"]
        ),
        "layer_recomposition": recompose_norm(
            old_result["telemetry"]["norm_by_layer"]
        ),
    }
    after_hash = source_telemetry.parameter_sha256(parameters)
    unchanged = before_hash == after_hash
    decision = classify(measurements, old_consistency, preregistration, unchanged)
    valid = (
        losses == stable_repeat["losses"]
        and measurements["all_gradient_elements_finite"]
        and telemetry["missing_gradient_parameter_count"] == 0
        and unchanged
    )
    decision["valid"] = valid
    if not valid:
        decision.update(
            {
                "outcome": "invalid_gradient_norm_crosscheck",
                "hypothesis_confirmed": False,
                "hypothesis_rejected": False,
                "maximum_positive_authorization": "none",
            }
        )
    result = {
        "schema": "uruha_rightbrain_gradient_norm_crosscheck_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "preflight": validation,
        "probe": probe,
        "losses": losses,
        "measurements": measurements,
        "reproducible_control_norm": preregistration["problem"]["reproducible_control_norm"],
        "old_consistency": old_consistency,
        "parameter_integrity": {
            "sha256_before_backward": before_hash,
            "sha256_after_crosscheck": after_hash,
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
