#!/usr/bin/env python3
"""Freeze a short active-head Qwen3 training-trajectory probe."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_active_head_single_update_v1 as parent_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_short_trajectory_v1"
REPEATS = tuple(range(1, 4))
OPTIMIZER_UPDATES = 32
LOSS_QUANTUM = 0.0078125
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_short_trajectory_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_short_trajectory_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_short_trajectory_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_short_trajectory_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_short_trajectory_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_short_trajectory_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_active_head_short_trajectory_v1_result.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_single_update_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_single_update_v1_result_lock.json"
)
MLX_OPTIMIZERS_PATH = parent_common.MLX_OPTIMIZERS_PATH

load_json = parent_common.load_json
sha256_file = parent_common.sha256_file
atomic_json = parent_common.atomic_json
atomic_text = parent_common.atomic_text
file_binding = parent_common.file_binding


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        MLX_OPTIMIZERS_PATH,
        RUNNER_PATH,
        TEST_PATH,
        VERIFIER_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_lock = load_json(PARENT_RESULT_LOCK)
    decision = parent_result["decision"]
    if decision["outcome"] != "active_head_single_update_canary_passed":
        raise RuntimeError("Unexpected single-update parent outcome")
    if decision["authorized_next_step"] != (
        "preregister_short_active_head_training_trajectory_probe"
    ):
        raise RuntimeError("Parent does not authorize the short trajectory probe")
    if decision["short_trajectory_probe_authorized"] is not True:
        raise RuntimeError("Parent short-trajectory authorization is false")
    if any(parent_lock["authorization"].values()):
        raise RuntimeError("Parent unexpectedly grants a persistent authorization")

    parent_optimizer = parent["optimizer_contract"]
    optimizer = {
        **parent_optimizer,
        "optimizer_updates_exact": OPTIMIZER_UPDATES,
    }
    expected_initial_loss = parent_result["measurements"]["pre_update_losses"][0]
    if expected_initial_loss != 5.05078125:
        raise RuntimeError("Parent initial loss drifted")

    dataset_path = ROOT / parent["batch_source"]["dataset"]
    if sha256_file(dataset_path) != parent["batch_source"]["dataset_sha256"]:
        raise RuntimeError("Source-independent dataset drifted")

    preregistration = {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does the stable active-head Qwen3 training path produce a finite, "
            "bounded, exactly reproducible, and measurably descending loss trajectory "
            "over 32 ephemeral updates on the same source-independent micro-batch?"
        ),
        "causal_scope": {
            "name": "ephemeral_short_optimizer_trajectory",
            "predecessor": "bounded_reproducible_single_optimizer_update",
            "only_new_operation": "increase_optimizer_updates_from_1_to_32",
            "unchanged": [
                "base_model",
                "lora_initialization",
                "source_independent_batch",
                "active_head_objective",
                "optimizer_hyperparameters",
                "gradient_clipping",
                "device_and_environment",
            ],
            "persistent_artifact_written": False,
        },
        "evidence_parent": {
            "preregistration": file_binding(PARENT_PREREGISTRATION),
            "result": file_binding(PARENT_RESULT),
            "result_lock": file_binding(PARENT_RESULT_LOCK),
            "outcome": decision["outcome"],
            "authorized_next_step": decision["authorized_next_step"],
        },
        "official_upstream_evidence": {
            "mlx_repository": "https://github.com/ml-explore/mlx",
            "mlx_lm_repository": "https://github.com/ml-explore/mlx-lm",
            "optimizer_source": file_binding(MLX_OPTIMIZERS_PATH),
            "implementation": (
                "The parent MLX clip_grad_norm + AdamW path is repeated without "
                "changing optimizer hyperparameters."
            ),
        },
        "local_environment": parent["local_environment"],
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "batch_contract": parent["batch_contract"],
        "batch_source": {
            **parent["batch_source"],
            "source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
        },
        "active_position_contract": parent["active_position_contract"],
        "optimizer_contract": optimizer,
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": 512,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "active_head_position_count": parent["active_position_contract"]["count"],
            "isolated_repetitions": list(REPEATS),
            "micro_steps_each": OPTIMIZER_UPDATES,
            "optimizer_updates_each": OPTIMIZER_UPDATES,
            "loss_observations_each": OPTIMIZER_UPDATES + 1,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_hypothesis": {
            "confirm_if_all": {
                "all_repetitions_successful": True,
                "trajectory_hashes_identical": True,
                "post_update_parameter_hashes_identical": True,
                "optimizer_state_hashes_identical": True,
                "parameter_hash_must_change": True,
                "parameter_delta_l2_minimum_exclusive": 0.0,
                "parameter_delta_l2_maximum": 0.5,
                "parameter_relative_delta_maximum": 0.02,
                "parameter_max_absolute_delta_maximum": 0.001,
                "clipped_gradient_norm_maximum": 0.300001,
                "final_loss_decrease_minimum": LOSS_QUANTUM,
                "best_loss_decrease_minimum": LOSS_QUANTUM,
                "tail_median_vs_head_median_decrease_minimum": LOSS_QUANTUM,
                "head_window_observations": 8,
                "tail_window_observations": 8,
                "parameter_delta_cv_maximum": 1e-12,
                "optimizer_step_exact": OPTIMIZER_UPDATES,
                "initial_loss_exact": expected_initial_loss,
                "all_values_finite": True,
            },
            "success_outcome": "active_head_short_trajectory_converged",
            "failure_outcomes": [
                "short_trajectory_execution_failed",
                "short_trajectory_nonfinite",
                "short_trajectory_did_not_mutate_parameters",
                "short_trajectory_not_reproducible",
                "short_trajectory_exceeded_mutation_bounds",
                "short_trajectory_did_not_converge",
            ],
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_source_independent_multibatch_active_head_learning_probe"
            ),
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "ephemeral_optimizer_instantiation": True,
            "ephemeral_optimizer_updates_exact": OPTIMIZER_UPDATES,
            "parameter_mutation_in_process": True,
            "adapter_or_model_save": False,
            "text_generation": False,
            "persona_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "persistent_training_authorization": False,
            "scope": "qwen3_active_head_short_micro_overfit_trajectory_only",
        },
        "interpretation_limits": [
            "A pass proves local optimizer-path learnability on one frozen micro-batch only.",
            "It does not prove multi-batch learning, holdout generalization, persona fidelity, or production readiness.",
            "A failure is evidence to diagnose objective precision or optimizer scale before using persona data.",
        ],
        "result_paths": {
            "repeat_prefix": (
                "reports/rightbrain_qwen3_active_head_short_trajectory_v1_repeat_"
            ),
            "aggregate_json": (
                "reports/rightbrain_qwen3_active_head_short_trajectory_v1_result.json"
            ),
            "aggregate_markdown": (
                "reports/rightbrain_qwen3_active_head_short_trajectory_v1_result.md"
            ),
            "result_lock": (
                "configs/rightbrain_qwen3_active_head_short_trajectory_v1_result_lock.json"
            ),
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "repetitions": list(REPEATS),
        "optimizer_updates_each": OPTIMIZER_UPDATES,
        "optimizer_contract": optimizer,
        "batch_contract": parent["batch_contract"],
        "active_position_contract": parent["active_position_contract"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 active-head 短程收斂軌跡探針",
                "",
                "- 唯一變因：相同 optimizer 路徑從 1 次更新增加為 32 次。",
                "- 3 個隔離程序；每次從相同 base 與 fresh LoRA 開始。",
                "- 必須同時有限、受限、逐程序完全一致，而且 loss 明確下降。",
                "- 只做單一 micro-batch 的可學習性檢查；不儲存、不生成、不修改 production。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(VERIFIER_PATH),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_RESULT),
            file_binding(PARENT_RESULT_LOCK),
            file_binding(MLX_OPTIMIZERS_PATH),
            file_binding(dataset_path),
        ],
        "authorization": {
            "repetitions": list(REPEATS),
            "allocated_sequence_length": 512,
            "active_head_position_count": parent["active_position_contract"]["count"],
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "device": "gpu",
            "optimizer_contract": optimizer,
            "micro_steps_each": OPTIMIZER_UPDATES,
            "optimizer_updates_each": OPTIMIZER_UPDATES,
            "loss_observations_each": OPTIMIZER_UPDATES + 1,
            "gradient_checkpointing": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "persona_training": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
