#!/usr/bin/env python3
"""Freeze an active-token Qwen3 full-chain zero-update experiment."""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_active_head_vjp_v1 as parent_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_active_head_full_chain_v1"
CONDITIONS = ("dense_full_chain_control", "active_head_full_chain")
REPEATS = tuple(range(1, 19))
EXECUTION_SCHEDULE = [
    {
        "repeat": repeat,
        "condition_order": list(CONDITIONS if repeat % 2 else reversed(CONDITIONS)),
    }
    for repeat in REPEATS
]
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_active_head_full_chain_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_full_chain_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_active_head_full_chain_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_active_head_full_chain_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_active_head_full_chain_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_active_head_full_chain_v1.py"
PARENT_PREREGISTRATION = parent_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_vjp_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_vjp_v1_result_lock.json"
)

load_json = parent_common.load_json
sha256_file = parent_common.sha256_file
atomic_json = parent_common.atomic_json
atomic_text = parent_common.atomic_text
file_binding = parent_common.file_binding


def _balanced_position_counts():
    return {
        condition: [
            sum(
                row["condition_order"][position] == condition
                for row in EXECUTION_SCHEDULE
            )
            for position in range(2)
        ]
        for condition in CONDITIONS
    }


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
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
        != "projecting_ignored_positions_is_sufficient_to_reproduce_drift"
    ):
        raise RuntimeError("Unexpected active-head VJP parent outcome")
    if (
        parent_result["decision"]["authorized_next_step"]
        != "preregister_zero_update_active_head_training_path_probe"
    ):
        raise RuntimeError("Parent does not authorize the full-chain probe")
    if any(
        parent_lock["authorization"][key]
        for key in (
            "training",
            "persona_training",
            "production_runtime_change",
            "persona_similarity_claim",
        )
    ):
        raise RuntimeError("Parent unexpectedly authorizes training or production")

    model_contract = parent["local_model_contract"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_contract["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = parent_common.parent_common.parent_common.canonical_batch(tokenizer)
    batch_contract = {
        key: value for key, value in batch.items() if key not in ("input_ids", "labels")
    }
    positions = parent_common.active_position_contract(batch)
    if positions != {
        key: parent["active_position_contract"][key]
        for key in ("positions", "count", "sha256")
    }:
        raise RuntimeError("Active-position contract drifted from parent")

    limits = parent["falsifiable_outcomes"]["within_level_reproducibility"]
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_active_head_full_chain_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does gathering the 16 supervised final hidden states before the tied "
            "Qwen3 LM head stabilize the complete 36-layer LoRA backward graph while "
            "preserving the same completion-token cross-entropy objective?"
        ),
        "causal_variable": {
            "name": "full_chain_lm_head_position_set",
            "levels": list(CONDITIONS),
            "dense_full_chain_control": (
                "run the full Transformer and project all 511 final hidden positions"
            ),
            "active_head_full_chain": (
                "run the same full Transformer, gather 16 supervised hidden states, "
                "then apply the tied LM head"
            ),
            "only_intended_change": True,
        },
        "semantic_equivalence_contract": {
            "same_input_and_label_hash": True,
            "same_active_position_indices": True,
            "same_active_target_ids": True,
            "same_transformer_and_lora_graph": True,
            "same_tied_embedding_weight": True,
            "same_cross_entropy_definition": True,
            "same_mean_denominator": positions["count"],
            "maximum_absolute_loss_delta_across_conditions": 0.05,
        },
        "evidence_parent": {
            "preregistration": file_binding(PARENT_PREREGISTRATION),
            "result": file_binding(PARENT_RESULT),
            "result_lock": file_binding(PARENT_RESULT_LOCK),
            "outcome": parent_result["decision"]["outcome"],
            "authorized_next_step": parent_result["decision"]["authorized_next_step"],
        },
        "official_upstream_evidence": parent["official_upstream_evidence"],
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
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "allocated_sequence_length": 512,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "dense_head_position_count": 511,
            "active_head_position_count": positions["count"],
            "conditions": list(CONDITIONS),
            "isolated_repetitions_per_level": list(REPEATS),
            "balanced_execution_schedule": EXECUTION_SCHEDULE,
            "position_counts_by_condition": _balanced_position_counts(),
            "micro_steps_each": 1,
            "optimizer_instantiated": False,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": limits,
            "control_requirement": "dense_full_chain_control_must_be_unstable",
            "classifications": {
                "control_unstable_candidate_stable": (
                    "active_head_full_chain_stabilizes_zero_update_backward"
                ),
                "control_unstable_candidate_unstable": (
                    "active_head_is_insufficient_for_full_chain_stability"
                ),
                "control_stable_candidate_stable": (
                    "dense_full_chain_parent_drift_not_reproduced"
                ),
                "control_stable_candidate_unstable": (
                    "active_head_full_chain_introduces_drift"
                ),
                "semantic_mismatch": "full_chain_conditions_not_semantically_equivalent",
                "execution_failure": "active_head_full_chain_execution_failed",
            },
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_single_update_active_head_optimizer_canary"
            ),
            "training": False,
            "persona_training": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "optimizer_instantiation": False,
            "optimizer_update": False,
            "parameter_mutation": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "training_authorization": False,
            "scope": "qwen3_active_head_full_chain_zero_update_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_active_head_full_chain_v1_",
            "aggregate_json": (
                "reports/rightbrain_qwen3_active_head_full_chain_v1_result.json"
            ),
            "aggregate_markdown": (
                "reports/rightbrain_qwen3_active_head_full_chain_v1_result.md"
            ),
            "result_lock": (
                "configs/rightbrain_qwen3_active_head_full_chain_v1_result_lock.json"
            ),
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_active_head_full_chain_construction_v1",
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
                "# Qwen3 active-token 完整反向鏈零更新實驗",
                "",
                "- 唯一變因：tied LM head 接收 511 個或 16 個 hidden positions。",
                "- 兩組共享完整 36 層 Transformer、全層 LoRA、batch、seed 與 loss。",
                "- 每組 18 個隔離程序；AB 與 BA 執行順序各 9 次。",
                "- 不建立 optimizer、不更新參數、不儲存、不生成、不修改 production。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_full_chain_execution_lock_v1",
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
            file_binding(ROOT / parent["batch_source"]["dataset"]),
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "allocated_sequence_length": 512,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "base_compute_dtype": "bfloat16",
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "device": "gpu",
            "repetitions_each": list(REPEATS),
            "balanced_execution_schedule": EXECUTION_SCHEDULE,
            "optimizer_instantiated": False,
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
