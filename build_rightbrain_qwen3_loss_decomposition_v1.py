#!/usr/bin/env python3
"""Freeze a matched full-Qwen3 loss-component localization experiment."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_compact_length_repro_v1 as parent_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_loss_decomposition_v1"
LOSS_MODES = ("masked_cross_entropy", "target_score_only", "logsumexp_only")
REPEATS = tuple(range(1, 19))
ORDER_PERMUTATIONS = tuple(itertools.permutations(LOSS_MODES))
EXECUTION_SCHEDULE = [
    {
        "repeat": repeat,
        "condition_order": list(ORDER_PERMUTATIONS[(repeat - 1) % 6]),
    }
    for repeat in REPEATS
]
ALLOCATED_LENGTH = 512
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_loss_decomposition_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_loss_decomposition_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_loss_decomposition_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_loss_decomposition_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_loss_decomposition_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_loss_decomposition_v1.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_compact_length_repro_v1_result.json"
REDUCED_RESULT = ROOT / "reports/rightbrain_qwen3_lora_span_repro_v1_result.json"
MLX_LOSSES_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx/nn/losses.py"
)

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batch(tokenizer):
    batch_parent = load_json(parent_common.batch_common.PARENT_PREREGISTRATION)
    batches, source = parent_common.canonical_batches(
        tokenizer,
        batch_parent,
    )
    return batches[str(ALLOCATED_LENGTH)], source


def _balanced_position_counts():
    return {
        mode: [
            sum(row["condition_order"][position] == mode for row in EXECUTION_SCHEDULE)
            for position in range(3)
        ]
        for mode in LOSS_MODES
    }


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        REDUCED_RESULT,
        MLX_LOSSES_PATH,
        RUNNER_PATH,
        TEST_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    reduced_result = load_json(REDUCED_RESULT)
    if (
        parent_result["decision"]["outcome"]
        != "compact_length_512_does_not_eliminate_drift"
    ):
        raise RuntimeError("Unexpected compact-length parent result")
    if parent_result["stability_by_length"]["512"] is not False:
        raise RuntimeError("Parent did not reproduce 512-token drift")
    if (
        reduced_result["decision"]["outcome"]
        != "lora_span_alone_does_not_reproduce_full_model_drift"
    ):
        raise RuntimeError("Unexpected reduced-path result")

    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = canonical_batch(tokenizer)
    batch_contract = {
        key: value
        for key, value in batch.items()
        if key not in ("input_ids", "labels")
    }
    limits = {
        "gradient_norm_coefficient_of_variation_maximum": 0.005,
        "gradient_norm_max_to_min_ratio_maximum": 1.02,
        "minimum_pairwise_group_profile_cosine": 0.9999,
        "gradient_hashes_must_be_identical": True,
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_loss_decomposition_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "With the full 36-layer Qwen3 graph fixed at 512 allocated tokens, "
            "which MLX cross-entropy component is sufficient to reproduce the "
            "observed cross-process LoRA gradient drift?"
        ),
        "causal_variable": {
            "name": "loss_component",
            "levels": list(LOSS_MODES),
            "masked_cross_entropy": "logsumexp(logits) - target_score",
            "target_score_only": "negative_target_score",
            "logsumexp_only": "logsumexp(logits)",
            "only_intended_change": True,
        },
        "evidence_parent": {
            "full_lm_512_result": {
                "path": str(PARENT_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(PARENT_RESULT),
                "outcome": parent_result["decision"]["outcome"],
                "metrics": parent_result["measurements"]["512"],
            },
            "transformer_without_lm_head_or_loss_result": {
                "path": str(REDUCED_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(REDUCED_RESULT),
                "outcome": reduced_result["decision"]["outcome"],
                "thirty_six_layer_stable": reduced_result["measurements"]["36"][
                    "gradient_hashes_identical"
                ],
            },
        },
        "upstream_implementation": {
            "mlx_version": "0.32.0",
            "losses_source": {
                **file_binding(MLX_LOSSES_PATH),
                "implementation": "logsumexp_logits - score",
            },
            "scope_note": (
                "The local installed MLX 0.32.0 source is bound so the decomposition "
                "matches the exact cross_entropy implementation used by the control."
            ),
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent[
            "adapter_initialization_contract"
        ],
        "batch_contract": batch_contract,
        "batch_source": {
            **source,
            "dataset": parent["batch_source"]["dataset"],
            "dataset_sha256": parent["batch_source"]["dataset_sha256"],
            "synthetic_source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
            "suffix_labels": -100,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": ALLOCATED_LENGTH,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "shared_forward_path": [
                "token_embedding",
                "36_transformer_layers",
                "final_rms_norm",
                "tied_lm_head",
            ],
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
            "control_requirement": "masked_cross_entropy_must_be_unstable",
            "classifications": {
                "all_three_unstable": (
                    "drift_precedes_loss_decomposition_or_is_in_shared_model_backward"
                ),
                "ce_and_logsumexp_unstable_target_stable": (
                    "logsumexp_branch_is_sufficient_to_reproduce_drift"
                ),
                "ce_and_target_unstable_logsumexp_stable": (
                    "target_score_branch_is_sufficient_to_reproduce_drift"
                ),
                "ce_unstable_both_components_stable": (
                    "combined_cross_entropy_graph_is_required_to_reproduce_drift"
                ),
                "ce_stable": "cross_entropy_parent_drift_not_reproduced",
                "execution_failure": "loss_decomposition_execution_failed",
            },
        },
        "success_authorization": {
            "maximum_positive_next_step": "localize_the_identified_loss_branch_only",
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
            "scope": "full_qwen3_loss_component_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_loss_decomposition_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_loss_decomposition_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_loss_decomposition_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_loss_decomposition_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_loss_decomposition_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "loss_modes": list(LOSS_MODES),
        "repetitions_each": list(REPEATS),
        "execution_schedule": EXECUTION_SCHEDULE,
        "batch_contract": batch_contract,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 loss 分解梯度定位實驗",
                "",
                "- 唯一變因：完整 cross-entropy、target score、logsumexp。",
                "- 三組共享完整 36 層模型、LoRA、512 tokens、labels 與 seed。",
                "- 每組 18 個隔離程序；六種條件順序各重複三次。",
                "- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_loss_decomposition_execution_lock_v1",
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
            file_binding(REDUCED_RESULT),
            file_binding(MLX_LOSSES_PATH),
            file_binding(ROOT / parent["batch_source"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)[
                    "bindings"
                ]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "loss_modes": list(LOSS_MODES),
            "allocated_sequence_length": ALLOCATED_LENGTH,
            "fixed_shared_prefix_tokens": 64,
            "base_compute_dtype": "bfloat16",
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "full_language_model_forward_path": True,
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
