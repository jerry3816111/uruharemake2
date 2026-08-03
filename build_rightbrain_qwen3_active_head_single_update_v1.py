#!/usr/bin/env python3
"""Freeze a single-update active-head Qwen3 optimizer canary."""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_active_head_full_chain_v1 as parent_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_single_update_v1"
REPEATS = tuple(range(1, 10))
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_single_update_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_single_update_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_single_update_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_single_update_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_single_update_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_single_update_v1.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_full_chain_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_full_chain_v1_result_lock.json"
)
MLX_OPTIMIZERS_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx/optimizers/optimizers.py"
)

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
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_lock = load_json(PARENT_RESULT_LOCK)
    decision = parent_result["decision"]
    if decision["outcome"] != "active_head_full_chain_stabilizes_zero_update_backward":
        raise RuntimeError("Unexpected active-head full-chain parent outcome")
    if decision["authorized_next_step"] != (
        "preregister_single_update_active_head_optimizer_canary"
    ):
        raise RuntimeError("Parent does not authorize a single update canary")
    if decision["single_update_canary_authorized"] is not True:
        raise RuntimeError("Parent canary authorization is false")
    if any(
        parent_lock["authorization"][key]
        for key in (
            "optimizer_update",
            "training",
            "persona_training",
            "production_runtime_change",
            "persona_similarity_claim",
        )
    ):
        raise RuntimeError("Parent unexpectedly authorizes persistent training")

    model_contract = parent["local_model_contract"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_contract["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = (
        parent_common.parent_common.parent_common.parent_common.canonical_batch(
            tokenizer
        )
    )
    batch_contract = {
        key: value for key, value in batch.items() if key not in ("input_ids", "labels")
    }
    positions = parent_common.parent_common.active_position_contract(batch)
    if positions != {
        key: parent["active_position_contract"][key]
        for key in ("positions", "count", "sha256")
    }:
        raise RuntimeError("Active-position contract drifted from parent")

    optimizer = {
        "name": "mlx.optimizers.AdamW",
        "learning_rate": 3e-7,
        "betas": [0.9, 0.999],
        "epsilon": 1e-6,
        "weight_decay": 0.02,
        "bias_correction": False,
        "maximum_gradient_norm": 0.3,
        "optimizer_updates_exact": 1,
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_active_head_single_update_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Can the stable active-token Qwen3 full backward graph perform exactly "
            "one bounded and reproducible AdamW update without saving or authorizing "
            "a training run?"
        ),
        "causal_scope": {
            "name": "ephemeral_single_optimizer_update",
            "predecessor": "stable_active_head_full_chain_zero_update",
            "only_new_operation": "one_clipped_mlx_adamw_update",
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
                "MLX clip_grad_norm followed by exactly one MLX AdamW.update"
            ),
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": model_contract,
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "batch_contract": batch_contract,
        "batch_source": {
            **source,
            "dataset": parent["batch_source"]["dataset"],
            "dataset_sha256": parent["batch_source"]["dataset_sha256"],
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
            "active_head_position_count": positions["count"],
            "isolated_repetitions": list(REPEATS),
            "micro_steps_each": 1,
            "optimizer_updates_each": 1,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_hypothesis": {
            "confirm_if_all": {
                "all_repetitions_successful": True,
                "raw_gradient_hashes_identical": True,
                "clipped_gradient_hashes_identical": True,
                "post_update_parameter_hashes_identical": True,
                "optimizer_state_hashes_identical": True,
                "parameter_hash_must_change": True,
                "parameter_delta_l2_minimum_exclusive": 0.0,
                "parameter_delta_l2_maximum": 0.1,
                "parameter_relative_delta_maximum": 0.01,
                "parameter_max_absolute_delta_maximum": 0.0001,
                "clipped_gradient_norm_maximum": 0.300001,
                "post_update_loss_increase_maximum": 0.05,
                "parameter_delta_cv_maximum": 1e-12,
                "optimizer_step_exact": 1,
                "all_values_finite": True,
            },
            "success_outcome": "active_head_single_update_canary_passed",
            "failure_outcomes": [
                "single_update_execution_failed",
                "single_update_nonfinite",
                "single_update_did_not_mutate_parameters",
                "single_update_not_reproducible",
                "single_update_exceeded_mutation_bounds",
                "single_update_loss_regressed",
            ],
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_short_active_head_training_trajectory_probe"
            ),
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "ephemeral_optimizer_instantiation": True,
            "ephemeral_optimizer_updates_exact": 1,
            "parameter_mutation_in_process": True,
            "adapter_or_model_save": False,
            "text_generation": False,
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "persistent_training_authorization": False,
            "scope": "qwen3_active_head_single_update_canary_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_active_head_single_update_v1_repeat_",
            "aggregate_json": (
                "reports/rightbrain_qwen3_active_head_single_update_v1_result.json"
            ),
            "aggregate_markdown": (
                "reports/rightbrain_qwen3_active_head_single_update_v1_result.md"
            ),
            "result_lock": (
                "configs/rightbrain_qwen3_active_head_single_update_v1_result_lock.json"
            ),
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_single_update_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "repetitions": list(REPEATS),
        "optimizer_contract": optimizer,
        "batch_contract": batch_contract,
        "active_position_contract": preregistration["active_position_contract"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 active-head 單次 optimizer update canary",
                "",
                "- 固定 active-token 完整反向路徑，只新增一次 clipped AdamW update。",
                "- 9 個隔離程序；每次從相同 base 與 fresh LoRA 開始。",
                "- 更新只存在記憶體；不儲存、不生成、不修改 production。",
                "- 只有非零、有限、受限且跨程序一致的更新才可通過。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_single_update_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_RESULT),
            file_binding(PARENT_RESULT_LOCK),
            file_binding(MLX_OPTIMIZERS_PATH),
            file_binding(ROOT / parent["batch_source"]["dataset"]),
        ],
        "authorization": {
            "repetitions": list(REPEATS),
            "allocated_sequence_length": 512,
            "active_head_position_count": positions["count"],
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "device": "gpu",
            "optimizer_contract": optimizer,
            "micro_steps_each": 1,
            "optimizer_updates_each": 1,
            "gradient_checkpointing": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
