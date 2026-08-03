#!/usr/bin/env python3
"""Freeze a Qwen3 active-token tied-head VJP localization experiment."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_backward_boundary_v1 as parent_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_vjp_v1"
CONDITIONS = (
    "dense_mask_after_loss",
    "dense_gather_before_loss",
    "active_gather_before_head",
)
REPEATS = tuple(range(1, 19))
ORDER_PERMUTATIONS = tuple(itertools.permutations(CONDITIONS))
EXECUTION_SCHEDULE = [
    {
        "repeat": repeat,
        "condition_order": list(ORDER_PERMUTATIONS[(repeat - 1) % 6]),
    }
    for repeat in REPEATS
]
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_vjp_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_vjp_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_vjp_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_vjp_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_vjp_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_vjp_v1.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_backward_boundary_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_backward_boundary_v1_result_lock.json"
)
EMBEDDING_SOURCE_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx/nn/layers/embedding.py"
)
LINEAR_SOURCE_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx/nn/layers/linear.py"
)

load_json = parent_common.load_json
sha256_file = parent_common.sha256_file
atomic_json = parent_common.atomic_json
atomic_text = parent_common.atomic_text
file_binding = parent_common.file_binding


def active_position_contract(batch):
    labels = batch["labels"][1:]
    positions = [index for index, label in enumerate(labels) if label != -100]
    encoded = ",".join(str(value) for value in positions).encode("ascii")
    return {
        "positions": positions,
        "count": len(positions),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _balanced_position_counts():
    return {
        condition: [
            sum(
                row["condition_order"][position] == condition
                for row in EXECUTION_SCHEDULE
            )
            for position in range(3)
        ]
        for condition in CONDITIONS
    }


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        EMBEDDING_SOURCE_PATH,
        LINEAR_SOURCE_PATH,
        RUNNER_PATH,
        TEST_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_lock = load_json(PARENT_RESULT_LOCK)
    if (
        parent_result["decision"]["outcome"]
        != "tied_lm_head_backward_is_sufficient_to_reproduce_drift"
    ):
        raise RuntimeError("Unexpected backward-boundary parent outcome")
    if (
        parent_result["decision"]["authorized_next_step"]
        != "localize_tied_embedding_linear_vjp_only"
    ):
        raise RuntimeError("Parent does not authorize tied-head VJP localization")
    if parent_lock["authorization"]["training"] is not False:
        raise RuntimeError("Parent unexpectedly authorizes training")

    model_contract = parent["local_model_contract"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_contract["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = parent_common.parent_common.canonical_batch(tokenizer)
    batch_contract = {
        key: value for key, value in batch.items() if key not in ("input_ids", "labels")
    }
    positions = active_position_contract(batch)
    if positions["count"] != batch_contract["labelled_tokens"]:
        raise RuntimeError("Active-position count does not match labelled-token contract")
    ignored_count = int(batch_contract["allocated_tokens"]) - 1 - positions["count"]
    limits = {
        "gradient_norm_coefficient_of_variation_maximum": 0.005,
        "gradient_norm_max_to_min_ratio_maximum": 1.02,
        "minimum_pairwise_group_profile_cosine": 0.9999,
        "gradient_hashes_must_be_identical": True,
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_active_head_vjp_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does moving the completion-label mask before the tied Qwen3 LM head "
            "eliminate intermittent Metal VJP drift while preserving the same 16 "
            "supervised tokens and cross-entropy objective?"
        ),
        "causal_variable": {
            "name": "completion_mask_placement",
            "levels": list(CONDITIONS),
            "dense_mask_after_loss": (
                "project all 511 hidden positions, compute all token losses, then mask"
            ),
            "dense_gather_before_loss": (
                "project all 511 positions, gather 16 active logits, then compute loss"
            ),
            "active_gather_before_head": (
                "gather 16 active hidden states, project only those, then compute loss"
            ),
            "only_intended_change": True,
        },
        "semantic_equivalence_contract": {
            "same_active_position_indices": True,
            "same_active_target_ids": True,
            "same_tied_embedding_weight": True,
            "same_cross_entropy_definition": True,
            "same_mean_denominator": positions["count"],
            "maximum_absolute_loss_delta_across_conditions": 0.05,
            "note": (
                "BF16 matmul shape changes may alter rounding while preserving the "
                "same supervised-token objective."
            ),
        },
        "evidence_parent": {
            "result": file_binding(PARENT_RESULT),
            "result_lock": file_binding(PARENT_RESULT_LOCK),
            "outcome": parent_result["decision"]["outcome"],
            "authorized_next_step": parent_result["decision"]["authorized_next_step"],
        },
        "official_upstream_evidence": {
            "mlx_repository": "https://github.com/ml-explore/mlx",
            "mlx_lm_repository": "https://github.com/ml-explore/mlx-lm",
            "embedding_source": file_binding(EMBEDDING_SOURCE_PATH),
            "linear_source": file_binding(LINEAR_SOURCE_PATH),
            "implementation": "Embedding.as_linear returns x @ self.weight.T",
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
        "active_position_contract": {
            **positions,
            "dense_position_count": int(batch_contract["allocated_tokens"]) - 1,
            "ignored_position_count": ignored_count,
        },
        "boundary_contract": parent["boundary_contract"],
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": 512,
            "vocabulary_size": 151936,
            "dense_head_position_count": 511,
            "active_head_position_count": positions["count"],
            "conditions": list(CONDITIONS),
            "isolated_repetitions_per_level": list(REPEATS),
            "fully_counterbalanced_execution_schedule": EXECUTION_SCHEDULE,
            "position_counts_by_condition": _balanced_position_counts(),
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": limits,
            "control_requirement": "dense_mask_after_loss_must_be_unstable",
            "classifications": {
                "dense_gather_stable_active_stable": (
                    "post_head_masking_path_is_sufficient_to_reproduce_drift"
                ),
                "dense_gather_unstable_active_stable": (
                    "projecting_ignored_positions_is_sufficient_to_reproduce_drift"
                ),
                "dense_gather_unstable_active_unstable": (
                    "active_head_projection_still_reproduces_drift"
                ),
                "dense_gather_stable_active_unstable": (
                    "active_gather_path_introduces_drift"
                ),
                "control_stable": "dense_parent_drift_not_reproduced",
                "semantic_mismatch": "head_conditions_not_semantically_equivalent",
                "execution_failure": "active_head_vjp_execution_failed",
            },
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_zero_update_active_head_training_path_probe"
            ),
            "training": False,
            "persona_training": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "training_authorization": False,
            "scope": "qwen3_tied_head_active_position_vjp_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_active_head_vjp_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_active_head_vjp_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_active_head_vjp_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_active_head_vjp_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_vjp_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "conditions": list(CONDITIONS),
        "repetitions_each": list(REPEATS),
        "execution_schedule": EXECUTION_SCHEDULE,
        "batch_contract": batch_contract,
        "active_position_contract": preregistration["active_position_contract"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 有效 token LM head VJP 實驗",
                "",
                "- 唯一變因：completion mask 放在 tied LM head 前或後。",
                f"- 511 個位置中只有 {positions['count']} 個需要計分。",
                f"- 其餘 {ignored_count} 個位置不改答案，只增加無效投影。",
                "- 三組共享 hidden、embedding 權重、targets、loss、seed 與裝置。",
                "- 每組 18 個隔離程序；不訓練、不儲存、不修改 production。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_vjp_execution_lock_v1",
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
            file_binding(EMBEDDING_SOURCE_PATH),
            file_binding(LINEAR_SOURCE_PATH),
            file_binding(ROOT / parent["batch_source"]["dataset"]),
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "allocated_sequence_length": 512,
            "active_position_count": positions["count"],
            "vocabulary_size": 151936,
            "base_compute_dtype": "bfloat16",
            "device": "gpu",
            "repetitions_each": list(REPEATS),
            "fully_counterbalanced_execution_schedule": EXECUTION_SCHEDULE,
            "optimizer_steps": 0,
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
