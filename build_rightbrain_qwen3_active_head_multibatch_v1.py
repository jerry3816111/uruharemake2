#!/usr/bin/env python3
"""Freeze a source-separated active-head Qwen3 multi-batch learning probe."""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

import build_rightbrain_qwen3_active_head_short_trajectory_v1 as parent_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_multibatch_v1"
REPEATS = (1, 2, 3)
ALLOCATED_TOKENS = 512
TRAIN_ROW_INDICES = (
    0,
    2,
    20,
    22,
    40,
    42,
    60,
    62,
    1,
    3,
    21,
    23,
    41,
    43,
    61,
    63,
)
HOLDOUT_ROW_INDICES = tuple(range(64, 80))
TRAIN_SCHEDULE = TRAIN_ROW_INDICES + TRAIN_ROW_INDICES
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_multibatch_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_multibatch_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_multibatch_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_multibatch_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_multibatch_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_multibatch_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_active_head_multibatch_v1_result.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_short_trajectory_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_short_trajectory_v1_result_lock.json"
)
DATASET_PATH = ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json"
DATASET_RESULT_LOCK = (
    ROOT / "configs/rightbrain_role_specialization_curriculum_v1_result_lock.json"
)
MODEL_SOURCE_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_4b_trainability_v1_preregistration.json"
)
MLX_OPTIMIZERS_PATH = parent_common.MLX_OPTIMIZERS_PATH

load_json = parent_common.load_json
sha256_file = parent_common.sha256_file
atomic_json = parent_common.atomic_json
atomic_text = parent_common.atomic_text
file_binding = parent_common.file_binding


def _position_contract(labels):
    positions = [index for index, value in enumerate(labels[1:]) if value != -100]
    encoded = ",".join(str(value) for value in positions).encode("ascii")
    return {
        "positions": positions,
        "count": len(positions),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def canonical_batches(tokenizer, rows):
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    selected = tuple(dict.fromkeys(TRAIN_ROW_INDICES + HOLDOUT_ROW_INDICES))
    batches = {}
    details = []
    combined = hashlib.sha256()
    for index in selected:
        row = rows[index]
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1], tokenize=False, add_generation_prompt=True
        )
        answer = f"{str(row['messages'][-1]['content']).strip()}<|im_end|>"
        prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
        answer_ids = tokenizer.encode(answer, add_special_tokens=False)
        full_ids = prompt_ids + answer_ids
        full_labels = [-100] * len(prompt_ids) + answer_ids
        slice_start = max(0, len(full_ids) - ALLOCATED_TOKENS)
        input_ids = full_ids[slice_start:]
        labels = full_labels[slice_start:]
        padding = ALLOCATED_TOKENS - len(input_ids)
        if padding < 0:
            raise RuntimeError(f"Truncation failed for row {row['id']}")
        input_ids = np.asarray(
            input_ids + [pad_id] * padding,
            dtype=np.int32,
        )
        labels = np.asarray(labels + [-100] * padding, dtype=np.int32)
        positions = _position_contract(labels)
        if positions["count"] != len(answer_ids):
            raise RuntimeError(f"Answer labels were truncated for row {row['id']}")
        digest = hashlib.sha256()
        digest.update(struct.pack("<I", index))
        digest.update(input_ids.tobytes())
        digest.update(labels.tobytes())
        row_hash = digest.hexdigest()
        combined.update(bytes.fromhex(row_hash))
        batches[index] = {
            "input_ids": input_ids,
            "labels": labels,
            "positions": positions,
        }
        details.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "full_tokens": len(full_ids),
                "left_truncated_tokens": slice_start,
                "retained_prompt_tokens": len(prompt_ids) - slice_start,
                "answer_tokens": len(answer_ids),
                "allocated_tokens": ALLOCATED_TOKENS,
                "sha256": row_hash,
                "active_position_contract": positions,
            }
        )
    return batches, details, combined.hexdigest()


def _counts(rows, indices, key):
    return dict(sorted(Counter(rows[index][key] for index in indices).items()))


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        DATASET_PATH,
        DATASET_RESULT_LOCK,
        MODEL_SOURCE_PREREGISTRATION,
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
    if decision["outcome"] != "active_head_short_trajectory_converged":
        raise RuntimeError("Unexpected short-trajectory parent outcome")
    if decision["authorized_next_step"] != (
        "preregister_source_independent_multibatch_active_head_learning_probe"
    ):
        raise RuntimeError("Parent does not authorize the multi-batch probe")
    if decision["multibatch_learning_probe_authorized"] is not True:
        raise RuntimeError("Parent multi-batch authorization is false")
    if any(parent_lock["authorization"].values()):
        raise RuntimeError("Parent unexpectedly grants persistent authorization")

    rows = load_json(DATASET_PATH)
    if len(rows) != 80:
        raise RuntimeError("Unexpected curriculum row count")
    train_sources = {rows[index]["source_id"] for index in TRAIN_ROW_INDICES}
    holdout_sources = {rows[index]["source_id"] for index in HOLDOUT_ROW_INDICES}
    if train_sources & holdout_sources:
        raise RuntimeError("Train and holdout source_id groups overlap")
    train_targets = {
        rows[index]["messages"][-1]["content"].strip()
        for index in TRAIN_ROW_INDICES
    }
    holdout_targets = {
        rows[index]["messages"][-1]["content"].strip()
        for index in HOLDOUT_ROW_INDICES
    }
    if train_targets & holdout_targets:
        raise RuntimeError("Train and holdout target replies overlap")
    selected_rows = [rows[index] for index in TRAIN_ROW_INDICES + HOLDOUT_ROW_INDICES]
    if not all(
        row["provenance"]["synthetic"] is True
        and row["provenance"]["source_independent"] is True
        and row["provenance"]["contains_target_utterance"] is False
        and row["provenance"]["contains_benchmark_item"] is False
        for row in selected_rows
    ):
        raise RuntimeError("Selected rows violate source-independent provenance")

    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    _, token_details, token_hash = canonical_batches(tokenizer, rows)
    details_by_index = {row["row_index"]: row for row in token_details}
    optimizer = {
        **parent["optimizer_contract"],
        "optimizer_updates_exact": len(TRAIN_SCHEDULE),
    }
    source_split = {
        "train_row_indices": list(TRAIN_ROW_INDICES),
        "holdout_row_indices": list(HOLDOUT_ROW_INDICES),
        "train_row_ids": [rows[index]["id"] for index in TRAIN_ROW_INDICES],
        "holdout_row_ids": [rows[index]["id"] for index in HOLDOUT_ROW_INDICES],
        "train_source_ids": sorted(train_sources),
        "holdout_source_ids": sorted(holdout_sources),
        "source_id_overlap_count": 0,
        "exact_target_overlap_count": 0,
        "train_provider_counts": _counts(rows, TRAIN_ROW_INDICES, "provider_id"),
        "holdout_provider_counts": _counts(rows, HOLDOUT_ROW_INDICES, "provider_id"),
        "train_memory_mode_counts": _counts(rows, TRAIN_ROW_INDICES, "memory_mode"),
        "holdout_memory_mode_counts": _counts(rows, HOLDOUT_ROW_INDICES, "memory_mode"),
        "train_schedule": list(TRAIN_SCHEDULE),
        "epochs_exact": 2,
    }

    preregistration = {
        "schema": "uruha_rightbrain_qwen3_active_head_multibatch_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "With the active-head optimizer path and 32 updates fixed, does replacing "
            "one repeated micro-batch with a balanced 16-row source-separated schedule "
            "reduce both train loss and loss on 16 unseen-source holdout rows?"
        ),
        "causal_scope": {
            "name": "source_separated_multibatch_schedule",
            "predecessor": "single_micro_batch_32_update_convergence",
            "only_new_operation": (
                "replace_32_repeats_of_one_row_with_two_epochs_over_16_rows_and_add_read_only_holdout_evaluation"
            ),
            "unchanged": [
                "base_model",
                "lora_initialization",
                "active_head_objective",
                "optimizer_hyperparameters",
                "gradient_clipping",
                "optimizer_update_count_32",
                "allocated_sequence_length_512",
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
        "upstream_evidence": {
            "mlx_repository": "https://github.com/ml-explore/mlx",
            "mlx_lm_repository": "https://github.com/ml-explore/mlx-lm",
            "optimizer_source": file_binding(MLX_OPTIMIZERS_PATH),
            "curriculum_result_lock": file_binding(DATASET_RESULT_LOCK),
            "model_source_preregistration": file_binding(
                MODEL_SOURCE_PREREGISTRATION
            ),
        },
        "local_environment": parent["local_environment"],
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "dataset_contract": {
            "path": str(DATASET_PATH.relative_to(ROOT)),
            "sha256": sha256_file(DATASET_PATH),
            "row_count": len(rows),
            "synthetic_source_independent": True,
            "contains_target_utterances": False,
            "contains_benchmark_items_or_answers": False,
            "persistent_training_authorized_by_dataset": False,
        },
        "source_split_contract": source_split,
        "token_contract": {
            "sha256": token_hash,
            "allocated_tokens": ALLOCATED_TOKENS,
            "selected_row_count": len(token_details),
            "details": token_details,
            "train_details": [details_by_index[index] for index in TRAIN_ROW_INDICES],
            "holdout_details": [
                details_by_index[index] for index in HOLDOUT_ROW_INDICES
            ],
            "all_answer_tokens_retained": True,
        },
        "optimizer_contract": optimizer,
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": ALLOCATED_TOKENS,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "isolated_repetitions": list(REPEATS),
            "train_rows": len(TRAIN_ROW_INDICES),
            "holdout_rows": len(HOLDOUT_ROW_INDICES),
            "epochs": 2,
            "micro_steps_each": len(TRAIN_SCHEDULE),
            "optimizer_updates_each": len(TRAIN_SCHEDULE),
            "pre_and_post_evaluation_rows_each": (
                len(TRAIN_ROW_INDICES) + len(HOLDOUT_ROW_INDICES)
            ),
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
                "train_mean_loss_decrease_minimum": 0.05,
                "holdout_mean_loss_decrease_minimum": 0.005,
                "holdout_improved_row_count_minimum": 9,
                "holdout_worst_row_loss_increase_maximum": 0.25,
                "holdout_each_provider_mean_loss_decrease_minimum": 0.0,
                "holdout_each_memory_mode_mean_loss_increase_maximum": 0.05,
                "parameter_delta_cv_maximum": 1e-12,
                "optimizer_step_exact": len(TRAIN_SCHEDULE),
                "all_values_finite": True,
                "source_id_overlap_exact": 0,
                "target_overlap_exact": 0,
            },
            "success_outcome": "active_head_multibatch_holdout_learning_confirmed",
            "failure_outcomes": [
                "multibatch_execution_failed",
                "multibatch_nonfinite",
                "multibatch_did_not_mutate_parameters",
                "multibatch_not_reproducible",
                "multibatch_exceeded_mutation_bounds",
                "multibatch_train_learning_failed",
                "multibatch_holdout_generalization_failed",
            ],
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_ephemeral_multibatch_fresh_generation_probe"
            ),
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "ephemeral_optimizer_instantiation": True,
            "ephemeral_optimizer_updates_exact": len(TRAIN_SCHEDULE),
            "parameter_mutation_in_process": True,
            "adapter_or_model_save": False,
            "text_generation": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "persistent_training_authorization": False,
            "scope": "qwen3_active_head_source_separated_multibatch_loss_probe_only",
        },
        "interpretation_limits": [
            "A pass shows in-distribution loss transfer to unseen source_id groups within one synthetic curriculum.",
            "It does not prove fresh-generation quality, out-of-distribution generalization, target-person fidelity, or production readiness.",
            "The holdout is source-group separated but shares the same synthetic curriculum generator and contract family.",
        ],
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_active_head_multibatch_v1_repeat_",
            "aggregate_json": "reports/rightbrain_qwen3_active_head_multibatch_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_active_head_multibatch_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_active_head_multibatch_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_multibatch_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "repetitions": list(REPEATS),
        "source_split_contract": source_split,
        "token_contract_sha256": token_hash,
        "optimizer_contract": optimizer,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 active-head 多批次 train／holdout 探針",
                "",
                "- 固定 32 次更新；從單一重複 batch 改成 16 筆來源分組資料的兩輪訓練。",
                "- Holdout 16 筆使用完全不同 source_id，更新前後只讀評估。",
                "- Train、holdout、target policy、neutral policy 必須同時符合門檻。",
                "- 不儲存 adapter、不生成、不使用本人原句或 benchmark。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_multibatch_execution_lock_v1",
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
            file_binding(DATASET_PATH),
            file_binding(DATASET_RESULT_LOCK),
            file_binding(MODEL_SOURCE_PREREGISTRATION),
            file_binding(MLX_OPTIMIZERS_PATH),
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
            "optimizer_contract": optimizer,
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
