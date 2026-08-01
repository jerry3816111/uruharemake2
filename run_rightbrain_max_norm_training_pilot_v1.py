#!/usr/bin/env python3
"""Run the frozen condition-isolated RightBrain max-norm training pilot."""

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
from safetensors import safe_open
from torch.utils.data import DataLoader

import build_rightbrain_max_norm_training_pilot_v1 as construction
import build_rightbrain_role_curriculum_training_pilot_v1 as prior_construction
import run_rightbrain_role_curriculum_training_pilot_v1 as prior_runner
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK
CONDITIONS = construction.CONDITIONS


def _training_report_path(preregistration, condition):
    return ROOT / f"{preregistration['result_paths']['training_prefix']}{condition}.json"


def _evaluation_report_path(preregistration, condition):
    return ROOT / f"{preregistration['result_paths']['evaluation_prefix']}{condition}.json"


def _adapter_path(preregistration, condition):
    return ROOT / preregistration["conditions"][condition]["output_directory"]


def _aggregate_paths(preregistration):
    paths = preregistration["result_paths"]
    return ROOT / paths["aggregate_json"], ROOT / paths["aggregate_markdown"]


def _evaluation_contract(preregistration):
    schedule = preregistration["controlled_training_schedule"]
    return {
        "local_model_contract": preregistration["local_model_contract"],
        "training_schedule": {
            "maximum_sequence_length": schedule["maximum_sequence_length"],
            "adapter_dropout": schedule["adapter_dropout"],
        },
        "fresh_generation_evaluation": preregistration["fresh_generation_evaluation"],
    }


def validate_execution_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    rows = []
    for binding in lock["repo_bindings"]:
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
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(row["match"] for row in rows)
        and authorization["exact_condition_isolated_training"]
        and tuple(authorization["conditions"]) == CONDITIONS
        and authorization["micro_steps_per_condition"] == 80
        and authorization["optimizer_updates_per_condition"] == 10
        and not authorization["production_runtime_change"]
        and not authorization["production_adapter_replacement"]
        and not authorization["persona_similarity_claim"]
        and not authorization["public_impersonation"]
    )
    return {"passed": passed, "bindings": rows, "lock": lock}


def _require_offline_mode():
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Pilot execution requires HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1")


def _release_model(model):
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


def _adapter_delta(initial_path, trained_path):
    initial_path = Path(initial_path)
    trained_path = Path(trained_path)
    initial_sq = delta_sq = dot = trained_sq = 0.0
    tensor_count = element_count = 0
    all_finite = True
    with safe_open(initial_path, framework="pt", device="cpu") as initial, safe_open(
        trained_path, framework="pt", device="cpu"
    ) as trained:
        initial_keys = tuple(initial.keys())
        trained_keys = tuple(trained.keys())
        if initial_keys != trained_keys:
            raise RuntimeError("Initial and trained adapter tensor keys differ")
        for key in initial_keys:
            before = initial.get_tensor(key).float()
            after = trained.get_tensor(key).float()
            if before.shape != after.shape:
                raise RuntimeError(f"Adapter tensor shape mismatch: {key}")
            difference = after - before
            all_finite = all_finite and bool(torch.isfinite(after).all())
            initial_sq += float(torch.sum(before * before, dtype=torch.float64))
            trained_sq += float(torch.sum(after * after, dtype=torch.float64))
            delta_sq += float(torch.sum(difference * difference, dtype=torch.float64))
            dot += float(torch.sum(before * after, dtype=torch.float64))
            tensor_count += 1
            element_count += before.numel()
    initial_l2 = math.sqrt(initial_sq)
    trained_l2 = math.sqrt(trained_sq)
    delta_l2 = math.sqrt(delta_sq)
    return {
        "tensor_count": tensor_count,
        "element_count": element_count,
        "all_finite": all_finite,
        "initial_adapter_l2": initial_l2,
        "trained_adapter_l2": trained_l2,
        "adapter_delta_l2": delta_l2,
        "adapter_relative_l2_change": delta_l2 / max(initial_l2, 1e-30),
        "initial_trained_cosine_similarity": dot / max(initial_l2 * trained_l2, 1e-30),
    }


def train_one(condition, lock_path=DEFAULT_EXECUTION_LOCK):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    _require_offline_mode()
    validation = validate_execution_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    schedule = preregistration["controlled_training_schedule"]
    output_dir = _adapter_path(preregistration, condition)
    report_path = _training_report_path(preregistration, condition)
    if output_dir.exists() or report_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing condition output: {condition}")
    rows = construction.load_json(ROOT / schedule["dataset"])
    if len(rows) != schedule["dataset_rows"]:
        raise RuntimeError("Frozen training row count mismatch")
    eval_contract = _evaluation_contract(preregistration)
    tokenizer = prior_runner.load_tokenizer(eval_contract)
    dataset = prior_runner.FixedLengthContractDataset(
        rows, tokenizer, int(schedule["fixed_allocated_sequence_length"])
    )
    seed = int(schedule["random_seed"])
    prior_runner._seed_everything(seed)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(schedule["batch_size"]),
        shuffle=True,
        generator=generator,
    )
    model_contract = preregistration["local_model_contract"]
    started = time.perf_counter()
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=int(schedule["adapter_rank"]),
        lora_alpha=int(schedule["adapter_alpha"]),
        lora_dropout=float(schedule["adapter_dropout"]),
        dtype_name="bfloat16",
    )
    device = prior_runner._device(model)
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(
        trainable,
        lr=float(schedule["learning_rate"]),
        betas=tuple(float(value) for value in schedule["adam_betas"]),
        weight_decay=float(schedule["weight_decay"]),
        eps=float(schedule["optimizer_epsilon"]),
    )
    max_norm = float(preregistration["conditions"][condition]["maximum_gradient_norm"])
    grad_accum = int(schedule["gradient_accumulation"])
    model.train()
    optimizer.zero_grad(set_to_none=True)
    losses = []
    update_rows = []
    micro_steps = updates = nonfinite_events = 0
    for batch in loader:
        micro_steps += 1
        loss = model(**prior_runner._move(batch, device)).loss
        if not torch.isfinite(loss):
            nonfinite_events += 1
            raise RuntimeError(f"Non-finite loss in {condition} at micro-step {micro_steps}")
        (loss / grad_accum).backward()
        losses.append(float(loss.detach().float().cpu()))
        if micro_steps % grad_accum == 0:
            norm_tensor = torch.nn.utils.clip_grad_norm_(trainable, max_norm=max_norm)
            preclip_norm = float(norm_tensor.detach().float().cpu())
            if not math.isfinite(preclip_norm):
                nonfinite_events += 1
                raise RuntimeError(f"Non-finite gradient in {condition} at update {updates + 1}")
            clip_coefficient = min(1.0, max_norm / (preclip_norm + 1e-6))
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            updates += 1
            update_rows.append(
                {
                    "optimizer_update": updates,
                    "ending_micro_step": micro_steps,
                    "preclip_gradient_norm": preclip_norm,
                    "maximum_gradient_norm": max_norm,
                    "effective_clip_coefficient": clip_coefficient,
                    "clipped": clip_coefficient < 1.0,
                    "mean_loss_for_accumulation_window": statistics.fmean(losses[-grad_accum:]),
                }
            )
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    if micro_steps != int(schedule["micro_steps_exact"]) or updates != int(
        schedule["optimizer_updates_exact"]
    ):
        raise RuntimeError(
            f"Schedule mismatch for {condition}: micro_steps={micro_steps}, updates={updates}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(output_dir)
    adapter_config = output_dir / "adapter_config.json"
    adapter_model = output_dir / "adapter_model.safetensors"
    delta = _adapter_delta(
        ROOT / model_contract["initial_adapter"]["path"] / "adapter_model.safetensors",
        adapter_model,
    )
    report = {
        "schema": "uruha_rightbrain_max_norm_training_condition_v1",
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "only_changed_variable": {
            "name": "maximum_gradient_norm",
            "value": max_norm,
        },
        "dataset": construction.file_binding(ROOT / schedule["dataset"]),
        "rows": len(dataset),
        "micro_steps": micro_steps,
        "optimizer_updates": updates,
        "nonfinite_events": nonfinite_events,
        "mean_training_loss": statistics.fmean(losses),
        "final_training_loss": losses[-1],
        "micro_step_losses": losses,
        "updates": update_rows,
        "clipped_update_count": sum(row["clipped"] for row in update_rows),
        "minimum_effective_clip_coefficient": min(
            row["effective_clip_coefficient"] for row in update_rows
        ),
        "maximum_observed_gradient_norm_before_clipping": max(
            row["preclip_gradient_norm"] for row in update_rows
        ),
        "adapter_change": delta,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "output_adapter": {
            "path": str(output_dir.relative_to(ROOT)),
            "adapter_config_sha256": construction.sha256_file(adapter_config),
            "adapter_model_sha256": construction.sha256_file(adapter_model),
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(output_dir / "training_run.json", report)
    construction.atomic_json(report_path, report)
    _release_model(model)
    return report


def _load_training_report(preregistration, condition):
    report_path = _training_report_path(preregistration, condition)
    report = construction.load_json(report_path)
    adapter_path = _adapter_path(preregistration, condition)
    if report["condition"] != condition:
        raise RuntimeError(f"Training report condition mismatch: {condition}")
    if report["micro_steps"] != 80 or report["optimizer_updates"] != 10:
        raise RuntimeError(f"Incomplete training schedule: {condition}")
    if report["nonfinite_events"] != 0 or not report["adapter_change"]["all_finite"]:
        raise RuntimeError(f"Invalid training numerics: {condition}")
    actual_hash = construction.sha256_file(adapter_path / "adapter_model.safetensors")
    if actual_hash != report["output_adapter"]["adapter_model_sha256"]:
        raise RuntimeError(f"Trained adapter hash mismatch: {condition}")
    return report


def evaluate_one(condition, lock_path=DEFAULT_EXECUTION_LOCK):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    _require_offline_mode()
    validation = validate_execution_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    training = _load_training_report(preregistration, condition)
    output_path = _evaluation_report_path(preregistration, condition)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite evaluation result: {condition}")
    contract = _evaluation_contract(preregistration)
    tokenizer = prior_runner.load_tokenizer(contract)
    holdout_path = ROOT / preregistration["policy_discrimination_evaluation"]["holdout"]
    holdout = construction.load_json(holdout_path)
    evaluation = prior_runner.evaluate_adapter(
        condition,
        _adapter_path(preregistration, condition),
        contract,
        tokenizer,
        holdout,
    )
    result = {
        "schema": "uruha_rightbrain_max_norm_training_condition_evaluation_v1",
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "execution_mode": "fresh_python_process_after_condition_training_exit",
        "inputs": {
            "execution_lock": construction.file_binding(lock_path),
            "training_report": construction.file_binding(_training_report_path(preregistration, condition)),
            "holdout": construction.file_binding(holdout_path),
            "adapter_model_sha256": training["output_adapter"]["adapter_model_sha256"],
        },
        "evaluation": evaluation,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(output_path, result)
    return result


def _exact_mcnemar(control_rows, treatment_rows, key_fields, metric):
    def keyed(rows):
        return {tuple(row[field] for field in key_fields): bool(row[metric]) for row in rows}

    control = keyed(control_rows)
    treatment = keyed(treatment_rows)
    if control.keys() != treatment.keys():
        raise RuntimeError(f"Paired rows differ for {metric}")
    control_only = sum(control[key] and not treatment[key] for key in control)
    treatment_only = sum(treatment[key] and not control[key] for key in control)
    discordant = control_only + treatment_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, value) for value in range(min(control_only, treatment_only) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {
        "control_only_correct": control_only,
        "treatment_only_correct": treatment_only,
        "discordant_pairs": discordant,
        "two_sided_exact_p_value": p_value,
    }


def decide(preregistration, training, evaluations):
    control = evaluations["control_0_3"]
    treatment = evaluations["treatment_3_0"]
    cp = control["policy_discrimination"]
    tp = treatment["policy_discrimination"]
    cg = control["fresh_generation"]
    tg = treatment["fresh_generation"]
    primary = preregistration["falsifiable_hypothesis"]["primary_pass_if_all"]
    generation = preregistration["falsifiable_hypothesis"]["generation_noninferiority"]
    integrity = {
        "both_training_runs_complete": all(
            row["micro_steps"] == 80 and row["optimizer_updates"] == 10
            for row in training.values()
        ),
        "zero_nonfinite_events": all(row["nonfinite_events"] == 0 for row in training.values()),
        "all_adapter_values_finite": all(
            row["adapter_change"]["all_finite"] for row in training.values()
        ),
        "all_policy_comparisons_accounted": all(
            row["policy_discrimination"]["comparison_count"] == 40
            for row in evaluations.values()
        ),
        "all_fresh_generations_accounted": all(
            row["fresh_generation"]["generation_count"] == 80
            for row in evaluations.values()
        ),
    }
    primary_checks = {
        "treatment_accuracy_minimum": tp["bidirectional_policy_discrimination_accuracy"]
        >= primary["treatment_bidirectional_policy_discrimination_accuracy_minimum"],
        "accuracy_delta_vs_control": tp["bidirectional_policy_discrimination_accuracy"]
        - cp["bidirectional_policy_discrimination_accuracy"]
        >= primary["treatment_delta_vs_control_minimum"],
        "margin_delta_vs_control": tp["mean_signed_policy_margin"]
        - cp["mean_signed_policy_margin"]
        >= primary["treatment_mean_signed_policy_margin_delta_vs_control_minimum"],
        "target_provider_minimum": tp["target_provider_discrimination_accuracy"]
        >= primary["treatment_target_provider_discrimination_accuracy_minimum"],
    }
    generation_checks = {
        "strict_noninferiority": tg["strict_candidate_gate_pass_rate"]
        - cg["strict_candidate_gate_pass_rate"]
        >= generation["strict_candidate_gate_delta_vs_control_minimum"],
        "semantic_noninferiority": tg["semantic_contract_pass_rate"]
        - cg["semantic_contract_pass_rate"]
        >= generation["semantic_contract_delta_vs_control_minimum"],
        "memory_noninferiority": tg["memory_policy_pass_rate"]
        - cg["memory_policy_pass_rate"]
        >= generation["memory_policy_delta_vs_control_minimum"],
        "pollution_noninferiority": tg["language_or_script_pollution_rate"]
        - cg["language_or_script_pollution_rate"]
        <= generation["language_or_script_pollution_delta_vs_control_maximum"],
        "polite_drift_noninferiority": tg["polite_register_drift_rate"]
        - cg["polite_register_drift_rate"]
        <= generation["polite_register_drift_delta_vs_control_maximum"],
        "private_memory_intrusion_maximum": tg["private_memory_intrusion_count"]
        <= generation["private_memory_intrusion_count_maximum"],
        "latency_ratio": tg["median_generation_latency_seconds"]
        / max(cg["median_generation_latency_seconds"], 1e-9)
        <= generation["median_latency_ratio_vs_control_maximum"],
        "peak_rss": tg["peak_process_resident_memory_bytes"]
        <= generation["peak_process_resident_memory_bytes_maximum"],
    }
    passed = all(integrity.values()) and all(primary_checks.values()) and all(
        generation_checks.values()
    )
    return {
        "passed": passed,
        "outcome": (
            "authorize_one_larger_source_independent_training_holdout_only"
            if passed
            else "reject_max_norm_3_0_as_next_training_default"
        ),
        "integrity_checks": integrity,
        "primary_checks": primary_checks,
        "generation_checks": generation_checks,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
        "authorize_public_impersonation": False,
    }


def render_result_markdown(result):
    training = result["training"]
    evaluations = result["evaluations"]
    lines = [
        "# RightBrain max_norm 公平訓練試驗結果",
        "",
        f"- 決策：`{result['decision']['outcome']}`",
        "- 唯一變因：`max_norm=0.3` 對 `max_norm=3.0`",
        "- 正式 runtime 修改：`0`",
        "",
        "## 訓練行為",
        "",
        "| 條件 | 裁切更新 | 最大更新前梯度 | 最小裁切係數 | adapter 相對改變 |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        row = training[condition]
        lines.append(
            f"| {condition} | {row['clipped_update_count']}/10 | "
            f"{row['maximum_observed_gradient_norm_before_clipping']:.6g} | "
            f"{row['minimum_effective_clip_coefficient']:.6g} | "
            f"{row['adapter_change']['adapter_relative_l2_change']:.6%} |"
        )
    lines.extend(
        [
            "",
            "## 政策方向判別",
            "",
            "| 條件 | 雙向正確率 | target 方向 | neutral 方向 | 平均 margin |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        row = evaluations[condition]["policy_discrimination"]
        lines.append(
            f"| {condition} | {row['bidirectional_policy_discrimination_accuracy']:.1%} | "
            f"{row['target_provider_discrimination_accuracy']:.1%} | "
            f"{row['neutral_provider_discrimination_accuracy']:.1%} | "
            f"{row['mean_signed_policy_margin']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## 全新生成品質",
            "",
            "| 條件 | 嚴格閘門 | 語意 | 記憶政策 | 語言污染 | 唯一輸出 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        row = evaluations[condition]["fresh_generation"]
        lines.append(
            f"| {condition} | {row['strict_candidate_gate_pass_rate']:.1%} | "
            f"{row['semantic_contract_pass_rate']:.1%} | "
            f"{row['memory_policy_pass_rate']:.1%} | "
            f"{row['language_or_script_pollution_rate']:.1%} | "
            f"{row['normalized_output_unique_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 配對統計",
            "",
            f"- 政策判別 exact McNemar p：`{result['paired_statistics']['policy_discrimination']['two_sided_exact_p_value']:.6g}`",
            f"- 嚴格生成閘門 exact McNemar p：`{result['paired_statistics']['strict_candidate_gate']['two_sided_exact_p_value']:.6g}`",
            "",
            "## 證據邊界",
            "",
            "本試驗只檢驗梯度裁切對一般人格政策訊號學習的影響。即使通過，也不證明一ノ瀬うるは相似度或正式聊天可上線。",
        ]
    )
    return "\n".join(lines) + "\n"


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_execution_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    result_json, result_md = _aggregate_paths(preregistration)
    if result_json.exists() or result_md.exists():
        raise RuntimeError("Refusing to overwrite aggregate result")
    training = {condition: _load_training_report(preregistration, condition) for condition in CONDITIONS}
    evaluations = {}
    evaluation_bindings = {}
    for condition in CONDITIONS:
        path = _evaluation_report_path(preregistration, condition)
        wrapper = construction.load_json(path)
        if wrapper["condition"] != condition:
            raise RuntimeError(f"Evaluation condition mismatch: {condition}")
        evaluations[condition] = wrapper["evaluation"]
        evaluation_bindings[condition] = construction.file_binding(path)
    paired_statistics = {
        "policy_discrimination": _exact_mcnemar(
            evaluations["control_0_3"]["policy_discrimination"]["rows"],
            evaluations["treatment_3_0"]["policy_discrimination"]["rows"],
            ("case_id", "provider_id"),
            "correct",
        ),
        "strict_candidate_gate": _exact_mcnemar(
            evaluations["control_0_3"]["fresh_generation"]["rows"],
            evaluations["treatment_3_0"]["fresh_generation"]["rows"],
            ("case_id", "provider_id", "seed"),
            "strict_candidate_gate_pass",
        ),
    }
    decision = decide(preregistration, training, evaluations)
    result = {
        "schema": "uruha_rightbrain_max_norm_training_pilot_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "execution_mode": "condition_isolated_training_and_evaluation",
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "evaluation_results": evaluation_bindings,
        },
        "training": training,
        "evaluations": evaluations,
        "paired_statistics": paired_statistics,
        "decision": decision,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(result_json, result)
    construction.atomic_text(result_md, render_result_markdown(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--train", choices=CONDITIONS)
    action.add_argument("--evaluate", choices=CONDITIONS)
    action.add_argument("--aggregate", action="store_true")
    parser.add_argument("--execution-lock", default=str(DEFAULT_EXECUTION_LOCK))
    args = parser.parse_args()
    if args.train:
        result = train_one(args.train, args.execution_lock)
        print(
            json.dumps(
                {
                    "condition": args.train,
                    "clipped_update_count": result["clipped_update_count"],
                    "maximum_observed_gradient_norm_before_clipping": result[
                        "maximum_observed_gradient_norm_before_clipping"
                    ],
                    "adapter_relative_l2_change": result["adapter_change"][
                        "adapter_relative_l2_change"
                    ],
                },
                indent=2,
            )
        )
    elif args.evaluate:
        result = evaluate_one(args.evaluate, args.execution_lock)
        metrics = result["evaluation"]
        print(
            json.dumps(
                {
                    "condition": args.evaluate,
                    "policy_discrimination_accuracy": metrics["policy_discrimination"][
                        "bidirectional_policy_discrimination_accuracy"
                    ],
                    "strict_candidate_gate_pass_rate": metrics["fresh_generation"][
                        "strict_candidate_gate_pass_rate"
                    ],
                },
                indent=2,
            )
        )
    else:
        result = aggregate(args.execution_lock)
        print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
