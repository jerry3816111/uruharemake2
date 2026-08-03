#!/usr/bin/env python3
"""Freeze a 64-update follow-up to the Qwen3 active-head multi-batch probe."""

from __future__ import annotations

import copy
import json
import statistics
from pathlib import Path

import build_rightbrain_qwen3_active_head_multibatch_v1 as parent


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_64step_v1"
REPEATS = (1, 2, 3)
ALLOCATED_TOKENS = parent.ALLOCATED_TOKENS
TRAIN_ROW_INDICES = parent.TRAIN_ROW_INDICES
HOLDOUT_ROW_INDICES = parent.HOLDOUT_ROW_INDICES
TRAIN_SCHEDULE = TRAIN_ROW_INDICES * 4
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_64step_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_64step_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_64step_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_64step_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_64step_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_64step_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_active_head_64step_v1_result.py"
PARENT_BUILDER = ROOT / "build_rightbrain_qwen3_active_head_multibatch_v1.py"
PARENT_RUNNER = ROOT / "run_rightbrain_qwen3_active_head_multibatch_v1.py"
PARENT_PREREGISTRATION = parent.DEFAULT_PREREGISTRATION
PARENT_EXECUTION_LOCK = parent.DEFAULT_EXECUTION_LOCK
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_multibatch_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_multibatch_v1_result_lock.json"
)
PARENT_REPEAT = ROOT / "reports/rightbrain_qwen3_active_head_multibatch_v1_repeat_1.json"

load_json = parent.load_json
sha256_file = parent.sha256_file
atomic_json = parent.atomic_json
atomic_text = parent.atomic_text
file_binding = parent.file_binding
canonical_batches = parent.canonical_batches


def _trajectory_diagnosis(parent_repeat):
    by_row = {}
    for step in parent_repeat["train_steps"]:
        by_row.setdefault(step["row_id"], {})[step["epoch"]] = step[
            "loss_before_update"
        ]
    if len(by_row) != len(TRAIN_ROW_INDICES) or any(
        set(losses) != {1, 2} for losses in by_row.values()
    ):
        raise RuntimeError("Unexpected parent epoch coverage")
    row_decreases = {
        row_id: losses[1] - losses[2] for row_id, losses in sorted(by_row.items())
    }
    raw_norms = [step["raw_norm_from_clip_operator"] for step in parent_repeat["train_steps"]]
    return {
        "epoch_1_mean_loss_before_update": statistics.fmean(
            losses[1] for losses in by_row.values()
        ),
        "epoch_2_mean_loss_before_update": statistics.fmean(
            losses[2] for losses in by_row.values()
        ),
        "paired_epoch_mean_loss_decrease": statistics.fmean(
            row_decreases.values()
        ),
        "paired_epoch_improved_rows": sum(value > 0 for value in row_decreases.values()),
        "paired_epoch_row_count": len(row_decreases),
        "row_loss_decreases": row_decreases,
        "all_parent_steps_gradient_clipped": all(value > 0.3 for value in raw_norms),
        "raw_gradient_norm_minimum": min(raw_norms),
        "raw_gradient_norm_maximum": max(raw_norms),
    }


def build():
    required = (
        RUNNER_PATH,
        TEST_PATH,
        VERIFIER_PATH,
        PARENT_BUILDER,
        PARENT_RUNNER,
        PARENT_PREREGISTRATION,
        PARENT_EXECUTION_LOCK,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        PARENT_REPEAT,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent_prereg = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_result_lock = load_json(PARENT_RESULT_LOCK)
    parent_repeat = load_json(PARENT_REPEAT)
    decision = parent_result["decision"]
    if decision["outcome"] != "multibatch_train_learning_failed":
        raise RuntimeError("Unexpected parent outcome")
    if decision["authorized_next_step"] != (
        "diagnose_active_head_multibatch_or_holdout_failure"
    ):
        raise RuntimeError("Parent does not authorize diagnosis")
    if any(parent_result_lock["authorization"].values()):
        raise RuntimeError("Parent unexpectedly grants persistent authorization")

    diagnosis = _trajectory_diagnosis(parent_repeat)
    if diagnosis["paired_epoch_mean_loss_decrease"] <= 0:
        raise RuntimeError("Parent trajectory does not support a longer schedule")
    if diagnosis["paired_epoch_improved_rows"] < 9:
        raise RuntimeError("Parent trajectory improvement is too narrow")

    parent_measurements = parent_result["measurements"]
    parent_train_decrease = parent_measurements["train_mean_loss_decreases"][0]
    parent_holdout_decrease = parent_measurements["holdout_mean_loss_decreases"][0]
    parent_holdout_improved = parent_measurements["holdout_improved_row_counts"][0]
    parent_holdout_worst = parent_measurements[
        "holdout_worst_row_loss_increases"
    ][0]

    prereg = copy.deepcopy(parent_prereg)
    prereg.update(
        {
            "schema": "uruha_rightbrain_qwen3_active_head_64step_preregistration_v1",
            "experiment_id": EXPERIMENT_ID,
            "research_question": (
                "With every model, data, objective, optimizer, and holdout condition fixed, "
                "does extending the balanced schedule from 32 to 64 updates clear the train "
                "learning gate without losing the parent holdout transfer?"
            ),
            "causal_scope": {
                "name": "optimizer_update_count_32_to_64",
                "predecessor": "source_separated_multibatch_32_update_probe",
                "only_new_operation": (
                    "repeat_the_identical_16_row_schedule_for_four_epochs_instead_of_two"
                ),
                "unchanged": [
                    "base_model",
                    "lora_initialization",
                    "train_and_holdout_rows",
                    "train_row_order_within_each_epoch",
                    "active_head_objective",
                    "learning_rate_and_optimizer_hyperparameters",
                    "gradient_clipping",
                    "allocated_sequence_length_512",
                    "pre_and_post_holdout_evaluation",
                    "device_and_environment",
                ],
                "persistent_artifact_written": False,
            },
            "evidence_parent": {
                "preregistration": file_binding(PARENT_PREREGISTRATION),
                "execution_lock": file_binding(PARENT_EXECUTION_LOCK),
                "result": file_binding(PARENT_RESULT),
                "result_lock": file_binding(PARENT_RESULT_LOCK),
                "repeat_used_for_step_diagnosis": file_binding(PARENT_REPEAT),
                "outcome": decision["outcome"],
                "authorized_next_step": decision["authorized_next_step"],
                "trajectory_diagnosis": diagnosis,
            },
        }
    )
    prereg["source_split_contract"] = copy.deepcopy(
        parent_prereg["source_split_contract"]
    )
    prereg["source_split_contract"].update(
        {"train_schedule": list(TRAIN_SCHEDULE), "epochs_exact": 4}
    )
    prereg["optimizer_contract"] = {
        **parent_prereg["optimizer_contract"],
        "optimizer_updates_exact": len(TRAIN_SCHEDULE),
    }
    prereg["exact_probe"] = {
        **parent_prereg["exact_probe"],
        "epochs": 4,
        "micro_steps_each": len(TRAIN_SCHEDULE),
        "optimizer_updates_each": len(TRAIN_SCHEDULE),
    }
    confirm = copy.deepcopy(
        parent_prereg["falsifiable_hypothesis"]["confirm_if_all"]
    )
    confirm.update(
        {
            "optimizer_step_exact": len(TRAIN_SCHEDULE),
            "train_mean_loss_decrease_minimum": 0.05,
            "holdout_mean_loss_decrease_minimum": parent_holdout_decrease - 0.005,
            "holdout_improved_row_count_minimum": parent_holdout_improved - 1,
            "holdout_worst_row_loss_increase_maximum": parent_holdout_worst + 0.015,
            "train_gain_over_32step_minimum": 0.015,
            "holdout_noninferiority_margin_vs_32step": 0.005,
        }
    )
    prereg["falsifiable_hypothesis"] = {
        "confirm_if_all": confirm,
        "parent_reference": {
            "train_mean_loss_decrease": parent_train_decrease,
            "holdout_mean_loss_decrease": parent_holdout_decrease,
            "holdout_improved_row_count": parent_holdout_improved,
            "holdout_worst_row_loss_increase": parent_holdout_worst,
        },
        "success_outcome": "active_head_64step_holdout_learning_confirmed",
        "failure_outcomes": [
            "extended_execution_failed",
            "extended_nonfinite",
            "extended_did_not_mutate_parameters",
            "extended_not_reproducible",
            "extended_exceeded_mutation_bounds",
            "extended_train_learning_failed",
            "extended_holdout_generalization_failed",
            "extended_parent_gain_failed",
        ],
    }
    prereg["success_authorization"] = {
        **parent_prereg["success_authorization"],
        "maximum_positive_next_step": (
            "preregister_ephemeral_multibatch_fresh_generation_probe"
        ),
    }
    prereg["boundaries"] = {
        **parent_prereg["boundaries"],
        "ephemeral_optimizer_updates_exact": len(TRAIN_SCHEDULE),
        "scope": "qwen3_active_head_source_separated_64step_loss_probe_only",
    }
    prereg["interpretation_limits"] = [
        "A pass shows that update count was the cause of the 32-step train-gate failure while preserving in-family holdout loss transfer.",
        "It does not prove fresh-generation quality, out-of-distribution generalization, target-person fidelity, or production readiness.",
        "The holdout remains source-group separated but belongs to the same synthetic curriculum family.",
    ]
    prereg["result_paths"] = {
        "repeat_prefix": "reports/rightbrain_qwen3_active_head_64step_v1_repeat_",
        "aggregate_json": "reports/rightbrain_qwen3_active_head_64step_v1_result.json",
        "aggregate_markdown": "reports/rightbrain_qwen3_active_head_64step_v1_result.md",
        "result_lock": "configs/rightbrain_qwen3_active_head_64step_v1_result_lock.json",
    }
    atomic_json(DEFAULT_PREREGISTRATION, prereg)

    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_64step_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "only_changed_variable": "optimizer_updates_32_to_64",
        "parent_trajectory_diagnosis": diagnosis,
        "parent_reference": prereg["falsifiable_hypothesis"]["parent_reference"],
        "train_schedule": list(TRAIN_SCHEDULE),
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 active-head 64-step 延長探針",
                "",
                "- 唯一變因：相同 16 筆排程從 32 更新延長到 64 更新。",
                f"- 32-step 的逐輪平均 loss 再下降：`{diagnosis['paired_epoch_mean_loss_decrease']}`。",
                "- 模型、資料、learning rate、gradient clipping、holdout 與門檻不變。",
                "- 不儲存 adapter、不生成、不使用本人原句或 benchmark。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_64step_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(VERIFIER_PATH),
            file_binding(PARENT_BUILDER),
            file_binding(PARENT_RUNNER),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_EXECUTION_LOCK),
            file_binding(PARENT_RESULT),
            file_binding(PARENT_RESULT_LOCK),
            file_binding(PARENT_REPEAT),
            file_binding(parent.DATASET_PATH),
            file_binding(parent.DATASET_RESULT_LOCK),
            file_binding(parent.MODEL_SOURCE_PREREGISTRATION),
            file_binding(parent.MLX_OPTIMIZERS_PATH),
        ],
        "authorization": {
            "repetitions": list(REPEATS),
            "train_row_indices": list(TRAIN_ROW_INDICES),
            "holdout_row_indices": list(HOLDOUT_ROW_INDICES),
            "train_schedule": list(TRAIN_SCHEDULE),
            "source_id_overlap_exact": 0,
            "target_overlap_exact": 0,
            "allocated_sequence_length": ALLOCATED_TOKENS,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "device": "gpu",
            "optimizer_contract": prereg["optimizer_contract"],
            "micro_steps_each": len(TRAIN_SCHEDULE),
            "optimizer_updates_each": len(TRAIN_SCHEDULE),
            "gradient_checkpointing": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
