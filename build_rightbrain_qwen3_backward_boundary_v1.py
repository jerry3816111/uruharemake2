#!/usr/bin/env python3
"""Freeze a full-Qwen3 backward-boundary localization experiment."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

import build_rightbrain_qwen3_loss_decomposition_v1 as parent_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_backward_boundary_v1"
CONDITIONS = (
    "full_chain_control",
    "head_boundary_vjp",
    "transformer_boundary_vjp",
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
    ROOT / "configs/rightbrain_qwen3_backward_boundary_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_backward_boundary_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_backward_boundary_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_backward_boundary_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_backward_boundary_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_backward_boundary_v1.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_loss_decomposition_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_loss_decomposition_v1_result_lock.json"
)
QWEN3_SOURCE_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx_lm/models/qwen3.py"
)
MLX_LOSSES_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx/nn/losses.py"
)

load_json = parent_common.load_json
sha256_file = parent_common.sha256_file
atomic_json = parent_common.atomic_json
atomic_text = parent_common.atomic_text
file_binding = parent_common.file_binding


def canonical_cotangent(shape, seed):
    rng = np.random.Generator(np.random.PCG64(seed))
    scale = 1.0 / math.sqrt(math.prod(shape))
    array = rng.standard_normal(shape, dtype=np.float32) * np.float32(scale)
    array = np.ascontiguousarray(array, dtype=np.float32)
    return array, hashlib.sha256(array.tobytes()).hexdigest()


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
        QWEN3_SOURCE_PATH,
        MLX_LOSSES_PATH,
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
        != "drift_precedes_loss_decomposition_or_is_in_shared_model_backward"
    ):
        raise RuntimeError("Unexpected loss-decomposition parent outcome")
    if (
        parent_result["decision"]["authorized_next_step"]
        != "localize_tied_lm_head_or_shared_transformer_backward"
    ):
        raise RuntimeError("Parent does not authorize backward-boundary localization")
    if parent_lock["authorization"]["training"] is not False:
        raise RuntimeError("Parent unexpectedly authorizes training")

    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = parent_common.canonical_batch(tokenizer)
    batch_contract = {
        key: value for key, value in batch.items() if key not in ("input_ids", "labels")
    }
    model_config_path = (
        Path(parent["local_model_contract"]["snapshot_root"]) / "config.json"
    )
    model_config = load_json(model_config_path)
    hidden_shape = [
        1,
        int(batch_contract["allocated_tokens"]) - 1,
        int(model_config["hidden_size"]),
    ]
    cotangent_seed = 20260803
    cotangent, cotangent_hash = canonical_cotangent(hidden_shape, cotangent_seed)
    limits = {
        "gradient_norm_coefficient_of_variation_maximum": 0.005,
        "gradient_norm_max_to_min_ratio_maximum": 1.02,
        "minimum_pairwise_group_profile_cosine": 0.9999,
        "gradient_hashes_must_be_identical": True,
    }

    preregistration = {
        "schema": "uruha_rightbrain_qwen3_backward_boundary_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "With the full Qwen3 forward graph fixed, does cross-process gradient "
            "drift arise before the final hidden-state boundary in Transformer "
            "backward, after that boundary in tied-LM-head backward, or only when "
            "both paths are composed?"
        ),
        "causal_variable": {
            "name": "backward_path",
            "levels": list(CONDITIONS),
            "full_chain_control": (
                "masked cross entropy through tied LM head and all Transformer layers"
            ),
            "head_boundary_vjp": (
                "masked cross entropy through tied LM head to detached final hidden state"
            ),
            "transformer_boundary_vjp": (
                "fixed source-independent cotangent through final norm and all Transformer layers"
            ),
            "only_intended_change": True,
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
            "local_qwen3_source": file_binding(QWEN3_SOURCE_PATH),
            "local_loss_source": file_binding(MLX_LOSSES_PATH),
            "model_config": file_binding(model_config_path),
            "implementation_note": (
                "The installed Qwen3 implementation applies model.embed_tokens.as_linear "
                "as its tied LM head; this exact local source is hash-bound."
            ),
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
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
        "boundary_contract": {
            "name": "final_normalized_hidden_state",
            "shape": hidden_shape,
            "tied_lm_head": "model.model.embed_tokens.as_linear",
            "transformer_cotangent": {
                "source": "numpy_pcg64_normalized_source_independent",
                "seed": cotangent_seed,
                "dtype": str(cotangent.dtype),
                "shape": list(cotangent.shape),
                "sha256": cotangent_hash,
                "l2_norm_target": 1.0,
            },
        },
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": 512,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "conditions": list(CONDITIONS),
            "isolated_repetitions_per_level": list(REPEATS),
            "fully_counterbalanced_execution_schedule": EXECUTION_SCHEDULE,
            "position_counts_by_condition": _balanced_position_counts(),
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": limits,
            "control_requirement": "full_chain_control_must_be_unstable",
            "classifications": {
                "head_unstable_transformer_stable": (
                    "tied_lm_head_backward_is_sufficient_to_reproduce_drift"
                ),
                "head_stable_transformer_unstable": (
                    "shared_transformer_backward_is_sufficient_to_reproduce_drift"
                ),
                "head_unstable_transformer_unstable": (
                    "both_backward_regions_independently_reproduce_drift"
                ),
                "head_stable_transformer_stable": (
                    "composed_head_transformer_backward_is_required_to_reproduce_drift"
                ),
                "control_stable": "full_chain_parent_drift_not_reproduced",
                "execution_failure": "backward_boundary_execution_failed",
            },
        },
        "success_authorization": {
            "maximum_positive_next_step": "localize_the_identified_backward_region_only",
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
            "scope": "full_qwen3_backward_boundary_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_backward_boundary_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_backward_boundary_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_backward_boundary_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_backward_boundary_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_backward_boundary_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "conditions": list(CONDITIONS),
        "repetitions_each": list(REPEATS),
        "execution_schedule": EXECUTION_SCHEDULE,
        "batch_contract": batch_contract,
        "boundary_contract": preregistration["boundary_contract"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 反向傳播邊界定位實驗",
                "",
                "- 唯一變因：完整鏈、LM head 到 hidden、hidden 到 Transformer。",
                "- 三組共享模型、LoRA、512 tokens、seed 與裝置。",
                "- 每組 18 個隔離程序；六種執行順序各重複三次。",
                "- Transformer 邊界使用固定、來源獨立且 hash 鎖定的上游梯度。",
                "- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_backward_boundary_execution_lock_v1",
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
            file_binding(QWEN3_SOURCE_PATH),
            file_binding(MLX_LOSSES_PATH),
            file_binding(model_config_path),
            file_binding(ROOT / parent["batch_source"]["dataset"]),
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "allocated_sequence_length": 512,
            "base_compute_dtype": "bfloat16",
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
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
