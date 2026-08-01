#!/usr/bin/env python3
"""Run deterministic foreach=False max-norm training pilot v2."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

import build_rightbrain_max_norm_training_pilot_v2 as construction
import run_rightbrain_max_norm_training_pilot_v1 as common
import run_rightbrain_role_curriculum_training_pilot_v1 as prior_runner
from train_uruha_rightbrain_contract_v1 import build_model


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK
CONDITIONS = construction.CONDITIONS


def _training_report_path(preregistration, condition):
    return common._training_report_path(preregistration, condition)


def _evaluation_report_path(preregistration, condition):
    return common._evaluation_report_path(preregistration, condition)


def _adapter_path(preregistration, condition):
    return common._adapter_path(preregistration, condition)


def _evaluation_contract(preregistration):
    return common._evaluation_contract(preregistration)


def validate_execution_lock(lock_path=DEFAULT_EXECUTION_LOCK):
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
        and authorization["condition_isolated_training"]
        and tuple(authorization["conditions"]) == CONDITIONS
        and authorization["micro_steps_per_condition"] == 80
        and authorization["optimizer_updates_per_condition"] == 10
        and authorization["clip_grad_norm_foreach"] is False
        and authorization["evaluation_requires_separate_pair_integrity_lock"]
        and not authorization["production_runtime_change"]
        and not authorization["production_adapter_replacement"]
        and not authorization["persona_similarity_claim"]
    )
    return {"passed": passed, "bindings": rows, "lock": lock}


def train_one(condition, lock_path=DEFAULT_EXECUTION_LOCK):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    common._require_offline_mode()
    validation = validate_execution_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("v2 execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    schedule = preregistration["controlled_training_schedule"]
    output_dir = _adapter_path(preregistration, condition)
    report_path = _training_report_path(preregistration, condition)
    if output_dir.exists() or report_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing v2 output: {condition}")
    rows = construction.load_json(ROOT / schedule["dataset"])
    contract = _evaluation_contract(preregistration)
    tokenizer = prior_runner.load_tokenizer(contract)
    dataset = prior_runner.FixedLengthContractDataset(
        rows, tokenizer, int(schedule["fixed_allocated_sequence_length"])
    )
    seed = int(schedule["random_seed"])
    prior_runner._seed_everything(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(schedule["batch_size"]),
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
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
            raise RuntimeError(f"Non-finite v2 loss in {condition} at micro-step {micro_steps}")
        (loss / grad_accum).backward()
        losses.append(float(loss.detach().float().cpu()))
        if micro_steps % grad_accum == 0:
            norm_tensor = torch.nn.utils.clip_grad_norm_(
                trainable,
                max_norm=max_norm,
                foreach=False,
            )
            preclip_norm = float(norm_tensor.detach().float().cpu())
            if not math.isfinite(preclip_norm):
                nonfinite_events += 1
                raise RuntimeError(f"Non-finite v2 gradient in {condition} at update {updates + 1}")
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
                    "norm_and_clipping_foreach": False,
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
        raise RuntimeError(f"v2 schedule mismatch: {condition}")
    output_dir.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(output_dir)
    adapter_model = output_dir / "adapter_model.safetensors"
    adapter_config = output_dir / "adapter_config.json"
    delta = common._adapter_delta(
        ROOT / model_contract["initial_adapter"]["path"] / "adapter_model.safetensors",
        adapter_model,
    )
    report = {
        "schema": "uruha_rightbrain_max_norm_training_condition_v2",
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "only_changed_variable": {"name": "maximum_gradient_norm", "value": max_norm},
        "common_methodological_control": {"clip_grad_norm_foreach": False},
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
    common._release_model(model)
    return report


def _load_training_report(preregistration, condition):
    return common._load_training_report(preregistration, condition)


def validate_training_pair(write_lock=False, lock_path=DEFAULT_EXECUTION_LOCK):
    execution_validation = validate_execution_lock(lock_path)
    if not execution_validation["passed"]:
        raise RuntimeError("v2 execution lock validation failed")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    reports = {
        condition: _load_training_report(preregistration, condition) for condition in CONDITIONS
    }
    control = reports["control_0_3"]
    treatment = reports["treatment_3_0"]
    requirements = preregistration["falsifiable_hypothesis"]["pair_integrity_requirements"]
    control_norm = control["updates"][0]["preclip_gradient_norm"]
    treatment_norm = treatment["updates"][0]["preclip_gradient_norm"]
    norm_error = abs(control_norm - treatment_norm) / max(abs(control_norm), abs(treatment_norm), 1e-300)
    checks = {
        "first_eight_losses_exact_match": control["micro_step_losses"][:8]
        == treatment["micro_step_losses"][:8]
        == control["micro_step_losses"][:8],
        "first_preclip_norm_reproducible": norm_error
        <= requirements["first_preclip_gradient_norm_relative_error_maximum"],
        "both_80_micro_steps": all(
            row["micro_steps"] == requirements["both_runs_micro_steps_exact"]
            for row in reports.values()
        ),
        "both_10_updates": all(
            row["optimizer_updates"] == requirements["both_runs_optimizer_updates_exact"]
            for row in reports.values()
        ),
        "zero_nonfinite_events": all(
            row["nonfinite_events"] <= requirements["nonfinite_events_maximum"]
            for row in reports.values()
        ),
        "all_adapter_values_finite": all(
            row["adapter_change"]["all_finite"] for row in reports.values()
        ),
        "foreach_false_recorded_every_update": all(
            all(update["norm_and_clipping_foreach"] is False for update in row["updates"])
            for row in reports.values()
        ),
    }
    result = {
        "schema": "uruha_rightbrain_max_norm_training_pair_integrity_v2",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "first_eight_micro_step_losses": control["micro_step_losses"][:8],
        "control_first_preclip_gradient_norm": control_norm,
        "treatment_first_preclip_gradient_norm": treatment_norm,
        "preclip_norm_relative_error": norm_error,
        "required_relative_error_maximum": requirements[
            "first_preclip_gradient_norm_relative_error_maximum"
        ],
        "training_reports": {
            condition: construction.file_binding(_training_report_path(preregistration, condition))
            for condition in CONDITIONS
        },
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_condition_isolated_holdout_evaluation"
                if all(checks.values())
                else "invalidate_v2_before_holdout_evaluation"
            ),
        },
    }
    if write_lock:
        pair_path = ROOT / preregistration["result_paths"]["training_pair_integrity_json"]
        evaluation_lock_path = ROOT / preregistration["result_paths"]["evaluation_lock"]
        if pair_path.exists() or evaluation_lock_path.exists():
            raise RuntimeError("Refusing to overwrite v2 pair-integrity artifacts")
        construction.atomic_json(pair_path, result)
        evaluation_lock = {
            "schema": "uruha_rightbrain_max_norm_training_pilot_evaluation_lock_v2",
            "experiment_id": EXPERIMENT_ID,
            "repo_bindings": [
                construction.file_binding(DEFAULT_PREREGISTRATION),
                construction.file_binding(lock_path),
                construction.file_binding(Path(__file__)),
                construction.file_binding(pair_path),
                *[
                    construction.file_binding(_training_report_path(preregistration, condition))
                    for condition in CONDITIONS
                ],
                *[
                    construction.file_binding(
                        _adapter_path(preregistration, condition) / "adapter_model.safetensors"
                    )
                    for condition in CONDITIONS
                ],
            ],
            "authorization": {
                "condition_isolated_holdout_evaluation": all(checks.values()),
                "conditions": list(CONDITIONS),
                "policy_comparisons_per_condition": 40,
                "fresh_generations_per_condition": 80,
                "additional_training": False,
                "production_runtime_change": False,
                "production_adapter_replacement": False,
                "persona_similarity_claim": False,
            },
        }
        construction.atomic_json(evaluation_lock_path, evaluation_lock)
    return result


def validate_evaluation_lock(preregistration):
    path = ROOT / preregistration["result_paths"]["evaluation_lock"]
    lock = construction.load_json(path)
    rows = []
    for binding in lock["repo_bindings"]:
        bound_path = ROOT / binding["path"]
        actual = construction.sha256_file(bound_path) if bound_path.is_file() else None
        rows.append({**binding, "actual_sha256": actual, "match": actual == binding["sha256"]})
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(row["match"] for row in rows)
        and authorization["condition_isolated_holdout_evaluation"]
        and tuple(authorization["conditions"]) == CONDITIONS
        and not authorization["additional_training"]
        and not authorization["production_runtime_change"]
        and not authorization["production_adapter_replacement"]
        and not authorization["persona_similarity_claim"]
    )
    return {"passed": passed, "path": path, "bindings": rows, "lock": lock}


def evaluate_one(condition):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    common._require_offline_mode()
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    validation = validate_evaluation_lock(preregistration)
    if not validation["passed"]:
        raise RuntimeError("v2 evaluation lock validation failed")
    training = _load_training_report(preregistration, condition)
    output_path = _evaluation_report_path(preregistration, condition)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite v2 evaluation: {condition}")
    contract = _evaluation_contract(preregistration)
    tokenizer = prior_runner.load_tokenizer(contract)
    holdout_path = ROOT / preregistration["policy_discrimination_evaluation"]["holdout"]
    evaluation = prior_runner.evaluate_adapter(
        condition,
        _adapter_path(preregistration, condition),
        contract,
        tokenizer,
        construction.load_json(holdout_path),
    )
    result = {
        "schema": "uruha_rightbrain_max_norm_training_condition_evaluation_v2",
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "execution_mode": "condition_isolated_after_pair_integrity_lock",
        "inputs": {
            "evaluation_lock": construction.file_binding(validation["path"]),
            "training_report": construction.file_binding(_training_report_path(preregistration, condition)),
            "holdout": construction.file_binding(holdout_path),
            "adapter_model_sha256": training["output_adapter"]["adapter_model_sha256"],
        },
        "evaluation": evaluation,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(output_path, result)
    return result


def render_result_markdown(result):
    base = common.render_result_markdown(result).replace(
        "# RightBrain max_norm 公平訓練試驗結果",
        "# RightBrain max_norm 公平訓練試驗 v2 結果",
        1,
    )
    integrity = result["training_pair_integrity"]
    prefix = "\n".join(
        [
            "## 因果完整性",
            "",
            f"- 第一批 control raw norm：`{integrity['control_first_preclip_gradient_norm']:.10f}`",
            f"- 第一批 treatment raw norm：`{integrity['treatment_first_preclip_gradient_norm']:.10f}`",
            f"- 相對誤差：`{integrity['preclip_norm_relative_error']:.3e}`",
            "- `foreach=False`：兩組全部更新皆成立",
            "",
        ]
    )
    return base.replace("## 訓練行為", prefix + "## 訓練行為", 1)


def aggregate():
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    evaluation_validation = validate_evaluation_lock(preregistration)
    if not evaluation_validation["passed"]:
        raise RuntimeError("v2 evaluation lock validation failed")
    result_json = ROOT / preregistration["result_paths"]["aggregate_json"]
    result_md = ROOT / preregistration["result_paths"]["aggregate_markdown"]
    result_lock_path = ROOT / preregistration["result_paths"]["result_lock"]
    if result_json.exists() or result_md.exists() or result_lock_path.exists():
        raise RuntimeError("Refusing to overwrite v2 aggregate artifacts")
    training = {
        condition: _load_training_report(preregistration, condition) for condition in CONDITIONS
    }
    evaluations = {}
    evaluation_bindings = {}
    for condition in CONDITIONS:
        path = _evaluation_report_path(preregistration, condition)
        wrapper = construction.load_json(path)
        if wrapper["condition"] != condition:
            raise RuntimeError(f"v2 evaluation condition mismatch: {condition}")
        evaluations[condition] = wrapper["evaluation"]
        evaluation_bindings[condition] = construction.file_binding(path)
    pair_path = ROOT / preregistration["result_paths"]["training_pair_integrity_json"]
    pair_integrity = construction.load_json(pair_path)
    paired_statistics = {
        "policy_discrimination": common._exact_mcnemar(
            evaluations["control_0_3"]["policy_discrimination"]["rows"],
            evaluations["treatment_3_0"]["policy_discrimination"]["rows"],
            ("case_id", "provider_id"),
            "correct",
        ),
        "strict_candidate_gate": common._exact_mcnemar(
            evaluations["control_0_3"]["fresh_generation"]["rows"],
            evaluations["treatment_3_0"]["fresh_generation"]["rows"],
            ("case_id", "provider_id", "seed"),
            "strict_candidate_gate_pass",
        ),
    }
    decision = common.decide(preregistration, training, evaluations)
    decision["training_pair_integrity_passed"] = pair_integrity["decision"]["passed"]
    decision["passed"] = decision["passed"] and pair_integrity["decision"]["passed"]
    if not decision["passed"]:
        decision["outcome"] = "reject_max_norm_3_0_as_next_training_default"
    result = {
        "schema": "uruha_rightbrain_max_norm_training_pilot_result_v2",
        "experiment_id": EXPERIMENT_ID,
        "execution_mode": "foreach_false_condition_isolated_training_and_evaluation",
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(DEFAULT_EXECUTION_LOCK),
            "evaluation_lock": construction.file_binding(evaluation_validation["path"]),
            "evaluation_results": evaluation_bindings,
        },
        "training_pair_integrity": pair_integrity,
        "training": training,
        "evaluations": evaluations,
        "paired_statistics": paired_statistics,
        "decision": decision,
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(result_json, result)
    construction.atomic_text(result_md, render_result_markdown(result))
    result_lock = {
        "schema": "uruha_rightbrain_max_norm_training_pilot_result_lock_v2",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(result_json),
            construction.file_binding(result_md),
            construction.file_binding(pair_path),
            construction.file_binding(evaluation_validation["path"]),
            *evaluation_bindings.values(),
        ],
        "decision": decision,
        "authorization": {
            "larger_source_independent_training_holdout": decision["passed"],
            "production_runtime_change": False,
            "production_adapter_replacement": False,
            "persona_similarity_claim": False,
            "public_impersonation": False,
        },
    }
    construction.atomic_json(result_lock_path, result_lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--train", choices=CONDITIONS)
    action.add_argument("--validate-training-pair", action="store_true")
    action.add_argument("--evaluate", choices=CONDITIONS)
    action.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.train:
        result = train_one(args.train)
        output = {
            "condition": args.train,
            "first_preclip_gradient_norm": result["updates"][0]["preclip_gradient_norm"],
            "clipped_update_count": result["clipped_update_count"],
            "adapter_relative_l2_change": result["adapter_change"][
                "adapter_relative_l2_change"
            ],
        }
    elif args.validate_training_pair:
        result = validate_training_pair(write_lock=True)
        output = result["decision"] | {
            "preclip_norm_relative_error": result["preclip_norm_relative_error"]
        }
    elif args.evaluate:
        result = evaluate_one(args.evaluate)
        metrics = result["evaluation"]
        output = {
            "condition": args.evaluate,
            "policy_discrimination_accuracy": metrics["policy_discrimination"][
                "bidirectional_policy_discrimination_accuracy"
            ],
            "strict_candidate_gate_pass_rate": metrics["fresh_generation"][
                "strict_candidate_gate_pass_rate"
            ],
        }
    else:
        result = aggregate()
        output = result["decision"]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
