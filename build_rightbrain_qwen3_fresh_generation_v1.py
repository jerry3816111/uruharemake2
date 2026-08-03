#!/usr/bin/env python3
"""Freeze a disjoint pre/post fresh-generation probe for the 64-step adapter."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import build_rightbrain_qwen3_active_head_64step_v1 as parent
import build_rightbrain_qwen3_active_head_multibatch_v1 as data_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_fresh_generation_v1"
REPEATS = (1, 2, 3)
TRAIN_ROW_INDICES = parent.TRAIN_ROW_INDICES
LOSS_HOLDOUT_ROW_INDICES = parent.HOLDOUT_ROW_INDICES
TRAIN_SCHEDULE = parent.TRAIN_SCHEDULE
FRESH_GENERATION_ROW_INDICES = (4, 6, 24, 26, 44, 46, 48, 50)
FRESH_REFERENCE_ALT_ROW_INDICES = (5, 7, 25, 27, 45, 47, 49, 51)
MAX_GENERATION_TOKENS = 80
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_fresh_generation_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_fresh_generation_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_fresh_generation_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_fresh_generation_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_fresh_generation_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_fresh_generation_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_fresh_generation_v1_result.py"
PARENT_BUILDER = ROOT / "build_rightbrain_qwen3_active_head_64step_v1.py"
PARENT_RUNNER = ROOT / "run_rightbrain_qwen3_active_head_64step_v1.py"
PARENT_PREREGISTRATION = parent.DEFAULT_PREREGISTRATION
PARENT_EXECUTION_LOCK = parent.DEFAULT_EXECUTION_LOCK
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_active_head_64step_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_active_head_64step_v1_result_lock.json"
)
DATASET_PATH = data_common.DATASET_PATH
DATASET_RESULT_LOCK = data_common.DATASET_RESULT_LOCK
MODEL_SOURCE_PREREGISTRATION = data_common.MODEL_SOURCE_PREREGISTRATION
MLX_OPTIMIZERS_PATH = data_common.MLX_OPTIMIZERS_PATH

load_json = parent.load_json
sha256_file = parent.sha256_file
atomic_json = parent.atomic_json
atomic_text = parent.atomic_text
file_binding = parent.file_binding
canonical_batches = parent.canonical_batches


def canonical_json_sha256(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fresh_generation_contract(rows):
    train_and_loss = TRAIN_ROW_INDICES + LOSS_HOLDOUT_ROW_INDICES
    fresh = [rows[index] for index in FRESH_GENERATION_ROW_INDICES]
    alternatives = [rows[index] for index in FRESH_REFERENCE_ALT_ROW_INDICES]
    train_sources = {rows[index]["source_id"] for index in train_and_loss}
    fresh_sources = {row["source_id"] for row in fresh}
    if fresh_sources & train_sources:
        raise RuntimeError("Fresh generation source_id overlaps train/loss holdout")
    for primary, alternate in zip(fresh, alternatives, strict=True):
        if primary["messages"][:2] != alternate["messages"][:2]:
            raise RuntimeError("Reference variants do not share an exact prompt")
        if primary["messages"][-1]["content"] == alternate["messages"][-1]["content"]:
            raise RuntimeError("Reference variants are not distinct")
    train_targets = {
        rows[index]["messages"][-1]["content"].strip() for index in train_and_loss
    }
    fresh_targets = {
        rows[index]["messages"][-1]["content"].strip()
        for index in FRESH_GENERATION_ROW_INDICES
        + FRESH_REFERENCE_ALT_ROW_INDICES
    }
    if train_targets & fresh_targets:
        raise RuntimeError("Fresh reference answer overlaps train/loss holdout")
    selected = fresh + alternatives
    if not all(
        row["provenance"]["synthetic"] is True
        and row["provenance"]["source_independent"] is True
        and row["provenance"]["contains_target_utterance"] is False
        and row["provenance"]["contains_benchmark_item"] is False
        for row in selected
    ):
        raise RuntimeError("Fresh rows violate source-independent provenance")
    prompts = [row["messages"][:2] for row in fresh]
    references = [
        [primary["messages"][-1]["content"], alternate["messages"][-1]["content"]]
        for primary, alternate in zip(fresh, alternatives, strict=True)
    ]
    return {
        "fresh_row_indices": list(FRESH_GENERATION_ROW_INDICES),
        "alternate_reference_row_indices": list(FRESH_REFERENCE_ALT_ROW_INDICES),
        "fresh_row_ids": [row["id"] for row in fresh],
        "fresh_source_ids": sorted(fresh_sources),
        "source_id_overlap_with_train_and_loss_holdout": 0,
        "exact_reference_overlap_with_train_and_loss_holdout": 0,
        "provider_counts": dict(
            sorted(Counter(row["provider_id"] for row in fresh).items())
        ),
        "memory_mode_counts": dict(
            sorted(Counter(row["memory_mode"] for row in fresh).items())
        ),
        "unique_prompt_count": len(
            {canonical_json_sha256(row["messages"][:2]) for row in fresh}
        ),
        "prompt_only_sha256": canonical_json_sha256(prompts),
        "reference_only_sha256": canonical_json_sha256(references),
        "assistant_reference_in_generation_prompt": False,
        "references_loaded_after_pre_and_post_generation": True,
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
        DATASET_PATH,
        DATASET_RESULT_LOCK,
        MODEL_SOURCE_PREREGISTRATION,
        MLX_OPTIMIZERS_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    parent_prereg = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_result_lock = load_json(PARENT_RESULT_LOCK)
    decision = parent_result["decision"]
    if decision["outcome"] != "active_head_64step_holdout_learning_confirmed":
        raise RuntimeError("Unexpected 64-step parent outcome")
    if decision["authorized_next_step"] != (
        "preregister_ephemeral_multibatch_fresh_generation_probe"
    ):
        raise RuntimeError("Parent does not authorize fresh generation")
    if decision["fresh_generation_probe_authorized"] is not True:
        raise RuntimeError("Parent fresh generation authorization is false")
    if any(parent_result_lock["authorization"].values()):
        raise RuntimeError("Parent unexpectedly grants persistent authorization")

    rows = load_json(DATASET_PATH)
    fresh_contract = fresh_generation_contract(rows)
    if fresh_contract["unique_prompt_count"] != 8:
        raise RuntimeError("Fresh generation prompts are not unique")
    if fresh_contract["provider_counts"] != {
        "structured_neutral_dialogue": 4,
        "structured_target_public_persona": 4,
    }:
        raise RuntimeError("Fresh provider split is not balanced")
    if set(fresh_contract["memory_mode_counts"].values()) != {2}:
        raise RuntimeError("Fresh memory split is not balanced")

    prereg = copy.deepcopy(parent_prereg)
    prereg.update(
        {
            "schema": "uruha_rightbrain_qwen3_fresh_generation_preregistration_v1",
            "experiment_id": EXPERIMENT_ID,
            "research_question": (
                "Does the already-confirmed ephemeral 64-step update change greedy outputs "
                "on eight source-disjoint prompts and improve semantic, memory-speakability, "
                "and surface-contract behavior without using their references during generation?"
            ),
            "causal_scope": {
                "name": "pre_vs_post_64step_fresh_generation",
                "predecessor": "confirmed_64step_loss_transfer",
                "only_new_operation": (
                    "greedy_generate_the_same_eight_never_evaluated_prompts_before_and_after_the_identical_64step_update"
                ),
                "unchanged": [
                    "base_model",
                    "lora_initialization",
                    "64step_train_rows_and_order",
                    "active_head_objective",
                    "optimizer_and_gradient_clipping",
                    "prompt_contract",
                    "generation_prompts_between_pre_and_post",
                    "greedy_decoding_parameters",
                    "device_and_environment",
                ],
                "persistent_artifact_written": False,
            },
            "evidence_parent": {
                "preregistration": file_binding(PARENT_PREREGISTRATION),
                "execution_lock": file_binding(PARENT_EXECUTION_LOCK),
                "result": file_binding(PARENT_RESULT),
                "result_lock": file_binding(PARENT_RESULT_LOCK),
                "outcome": decision["outcome"],
                "authorized_next_step": decision["authorized_next_step"],
            },
            "fresh_generation_contract": fresh_contract,
            "generation_contract": {
                "decode_mode": "greedy",
                "temperature": 0.0,
                "top_p": 0.0,
                "maximum_new_tokens": MAX_GENERATION_TOKENS,
                "pre_and_post_prompt_order": list(FRESH_GENERATION_ROW_INDICES),
                "assistant_reference_passed_to_model": False,
                "reference_scoring_timing": "after_both_generation_phases",
            },
        }
    )
    prereg["exact_probe"] = {
        **parent_prereg["exact_probe"],
        "fresh_generation_rows": len(FRESH_GENERATION_ROW_INDICES),
        "pre_generation_calls": len(FRESH_GENERATION_ROW_INDICES),
        "post_generation_calls": len(FRESH_GENERATION_ROW_INDICES),
        "total_generation_calls": 2 * len(FRESH_GENERATION_ROW_INDICES),
        "maximum_generation_tokens_each": MAX_GENERATION_TOKENS,
    }
    prereg["falsifiable_hypothesis"] = {
        "confirm_if_all": {
            "all_repetitions_successful": True,
            "training_trajectory_matches_64step_parent": True,
            "pre_generation_parameter_hash_unchanged": True,
            "post_generation_parameter_hash_unchanged": True,
            "pre_outputs_reproducible": True,
            "post_outputs_reproducible": True,
            "changed_output_count_minimum": 2,
            "post_semantic_complete_rate_minimum": 0.75,
            "post_marker_group_coverage_rate_minimum": 0.8,
            "post_forbidden_pass_rate_minimum": 0.875,
            "post_length_pass_rate_minimum": 0.875,
            "post_casual_japanese_pass_rate_minimum": 0.75,
            "post_memory_policy_pass_rate_minimum": 0.75,
            "post_joint_contract_pass_rate_minimum": 0.5,
            "semantic_complete_rate_regression_maximum": 0.0,
            "joint_contract_required_gain_below_pre_ceiling": 0.125,
            "pre_joint_contract_ceiling_threshold": 0.75,
            "joint_contract_regression_count_maximum": 1,
            "joint_contract_improvements_must_exceed_regressions": True,
            "post_provider_pair_difference_rate_minimum": 0.75,
            "provider_pair_difference_rate_regression_maximum": 0.0,
            "reference_similarity_regression_maximum": 0.05,
            "parameter_delta_l2_maximum": 0.5,
            "parameter_relative_delta_maximum": 0.02,
            "parameter_max_absolute_delta_maximum": 0.001,
            "clipped_gradient_norm_maximum": 0.300001,
            "optimizer_step_exact": len(TRAIN_SCHEDULE),
            "all_values_finite": True,
            "source_id_overlap_exact": 0,
            "reference_overlap_exact": 0,
        },
        "success_outcome": "fresh_generation_behavior_improved",
        "failure_outcomes": [
            "fresh_generation_execution_failed",
            "fresh_generation_training_drifted",
            "fresh_generation_not_reproducible",
            "fresh_generation_outputs_unchanged",
            "fresh_generation_contract_not_improved",
            "fresh_generation_mutation_out_of_bounds",
        ],
    }
    prereg["success_authorization"] = {
        "maximum_positive_next_step": (
            "preregister_adapter_save_reload_equivalence_probe"
        ),
        "persistent_training": False,
        "persona_training": False,
        "adapter_save": False,
        "runtime_activation": False,
        "persona_similarity_claim": False,
    }
    prereg["boundaries"] = {
        **parent_prereg["boundaries"],
        "text_generation": True,
        "generation_is_ephemeral": True,
        "assistant_reference_in_model_context": False,
        "reference_loaded_after_generation": True,
        "adapter_or_model_save": False,
        "production_runtime_change": False,
        "scope": "qwen3_ephemeral_64step_pre_post_fresh_generation_only",
    }
    prereg["interpretation_limits"] = [
        "A pass shows deterministic behavioral improvement on eight source-disjoint synthetic prompts after the already-confirmed 64-step update.",
        "It does not prove target-person fidelity, broad naturalness, out-of-family generalization, persistent save/reload equivalence, or production readiness.",
        "The references are synthetic acceptable examples and are used only for post-generation diagnostics, not as model inputs or training targets.",
    ]
    prereg["result_paths"] = {
        "repeat_prefix": "reports/rightbrain_qwen3_fresh_generation_v1_repeat_",
        "aggregate_json": "reports/rightbrain_qwen3_fresh_generation_v1_result.json",
        "aggregate_markdown": "reports/rightbrain_qwen3_fresh_generation_v1_result.md",
        "result_lock": "configs/rightbrain_qwen3_fresh_generation_v1_result_lock.json",
    }
    atomic_json(DEFAULT_PREREGISTRATION, prereg)
    construction = {
        "schema": "uruha_rightbrain_qwen3_fresh_generation_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "fresh_generation_contract": fresh_contract,
        "generation_contract": prereg["generation_contract"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 fresh-generation pre／post 探針",
                "",
                "- 8 個 prompt 從未用於 train、32/64-step loss holdout。",
                "- 同一全新 LoRA 在 64-step 前後各 greedy 生成一次。",
                "- 參考回答在兩階段生成後才載入，只用於評分。",
                "- 不存 adapter、不使用本人原句或 benchmark。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_fresh_generation_execution_lock_v1",
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
            file_binding(DATASET_PATH),
            file_binding(DATASET_RESULT_LOCK),
            file_binding(MODEL_SOURCE_PREREGISTRATION),
            file_binding(MLX_OPTIMIZERS_PATH),
        ],
        "authorization": {
            "repetitions": list(REPEATS),
            "train_row_indices": list(TRAIN_ROW_INDICES),
            "loss_holdout_row_indices": list(LOSS_HOLDOUT_ROW_INDICES),
            "train_schedule": list(TRAIN_SCHEDULE),
            "fresh_generation_row_indices": list(FRESH_GENERATION_ROW_INDICES),
            "fresh_reference_alt_row_indices": list(
                FRESH_REFERENCE_ALT_ROW_INDICES
            ),
            "source_id_overlap_exact": 0,
            "reference_overlap_exact": 0,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "device": "gpu",
            "optimizer_contract": prereg["optimizer_contract"],
            "optimizer_updates_each": len(TRAIN_SCHEDULE),
            "generation_contract": prereg["generation_contract"],
            "adapter_or_model_save": False,
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
