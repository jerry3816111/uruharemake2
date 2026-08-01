#!/usr/bin/env python3
"""Freeze a matched 512 versus 640 token full-Qwen3 backward experiment."""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_length_boundary_v1 as batch_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_compact_length_repro_v1"
LENGTH_LEVELS = (512, 640)
REPEATS = tuple(range(1, 21))
EXECUTION_SCHEDULE = [
    {
        "repeat": repeat,
        "condition_order": [640, 512] if repeat % 2 else [512, 640],
    }
    for repeat in REPEATS
]
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_compact_length_repro_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_compact_length_repro_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_compact_length_repro_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_compact_length_repro_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_compact_length_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_compact_length_repro_v1.py"
PARENT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_cache_repro_v1_preregistration.json"
)
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_cache_repro_v1_result.json"
BOUNDARY_RESULT = ROOT / "reports/rightbrain_qwen3_length_boundary_v1_result.json"
COMPACT_RESULT = ROOT / "reports/rightbrain_compact_japanese_payload_v1_result.json"

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batches(tokenizer, parent_preregistration):
    batches, source = batch_common.canonical_batches(tokenizer, parent_preregistration)
    return {str(length): batches[str(length)] for length in LENGTH_LEVELS}, source


def _metric_excerpt(result, length):
    metrics = result["measurements"][str(length)]
    return {
        "repetitions": len(metrics["gradient_norms"]),
        "gradient_norm_coefficient_of_variation": metrics[
            "gradient_norm_coefficient_of_variation"
        ],
        "gradient_norm_max_to_min_ratio": metrics[
            "gradient_norm_max_to_min_ratio"
        ],
        "gradient_hashes_identical": metrics["gradient_hashes_identical"],
    }


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        BOUNDARY_RESULT,
        COMPACT_RESULT,
        RUNNER_PATH,
        TEST_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    boundary_result = load_json(BOUNDARY_RESULT)
    compact_result = load_json(COMPACT_RESULT)
    if (
        parent_result["decision"]["outcome"]
        != "disabling_metal_free_cache_does_not_eliminate_drift"
    ):
        raise RuntimeError("Unexpected cache-localization parent result")
    if parent_result["stability_by_cache_mode"]["default_cache"] is not False:
        raise RuntimeError("Parent did not reproduce default-cache drift")
    historical_512 = boundary_result["measurements"]["512"]
    if not all(historical_512["checks"].values()) or not historical_512[
        "gradient_hashes_identical"
    ]:
        raise RuntimeError("Historical 512-token anchor was not stable")
    if compact_result["decision"] != "revert_compact_serializer_experiment":
        raise RuntimeError("Compact serializer evidence boundary changed")

    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch_parent = load_json(batch_common.PARENT_PREREGISTRATION)
    batches, source = canonical_batches(tokenizer, batch_parent)
    batch_contracts = {
        length: {
            key: value
            for key, value in row.items()
            if key not in ("input_ids", "labels")
        }
        for length, row in batches.items()
    }
    limits = {
        "gradient_norm_coefficient_of_variation_maximum": 0.005,
        "gradient_norm_max_to_min_ratio_maximum": 1.02,
        "minimum_pairwise_group_profile_cosine": 0.9999,
        "gradient_hashes_must_be_identical": True,
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_compact_length_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "With identical synthetic content, labels, model, LoRA initialization, "
            "dtype, and backward path, does reducing allocated sequence length from "
            "640 to 512 eliminate the observed cross-process gradient drift?"
        ),
        "causal_variable": {
            "name": "allocated_sequence_length",
            "levels": list(LENGTH_LEVELS),
            "control": 640,
            "treatment": 512,
            "only_intended_change": True,
        },
        "evidence_parent": {
            "cache_result": {
                "path": str(PARENT_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(PARENT_RESULT),
                "outcome": parent_result["decision"]["outcome"],
                "default_cache": parent_result["measurements"]["default_cache"],
            },
            "historical_length_result": {
                "path": str(BOUNDARY_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(BOUNDARY_RESULT),
                "length_512": _metric_excerpt(boundary_result, 512),
                "length_640": _metric_excerpt(boundary_result, 640),
                "limitation": (
                    "The historical five-repeat sweep is directional evidence only; "
                    "the later ten-repeat 640-token control found intermittent drift."
                ),
            },
            "compact_payload_result": {
                "path": str(COMPACT_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(COMPACT_RESULT),
                "observed_active_prompt_token_range": [369, 408],
                "decision": compact_result["decision"],
                "limitation": (
                    "The old Qwen2.5 compact serializer reduced token count but regressed "
                    "quality. It is feasibility evidence only and is not authorized for reuse."
                ),
            },
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent[
            "adapter_initialization_contract"
        ],
        "batch_contracts": batch_contracts,
        "batch_source": {
            **source,
            "dataset": batch_parent["exact_probe"]["dataset"],
            "dataset_sha256": sha256_file(
                ROOT / batch_parent["exact_probe"]["dataset"]
            ),
            "synthetic_source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
            "same_labelled_prefix_across_both_levels": True,
            "suffix_labels": -100,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": "bfloat16",
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "full_language_model_path": [
                "token_embedding",
                "36_transformer_layers",
                "final_rms_norm",
                "tied_lm_head",
                "masked_cross_entropy",
            ],
            "isolated_repetitions_per_level": list(REPEATS),
            "balanced_interleaved_execution_schedule": EXECUTION_SCHEDULE,
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": limits,
            "classifications": {
                "control_unstable_treatment_stable": (
                    "compact_length_512_eliminates_observed_drift"
                ),
                "both_unstable": "compact_length_512_does_not_eliminate_drift",
                "both_stable": "parent_640_drift_not_reproduced",
                "control_stable_treatment_unstable": (
                    "nonmonotonic_compact_length_instability"
                ),
                "execution_failure": "compact_length_repro_execution_failed",
            },
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_semantic_equivalent_512_token_contract_construction"
            ),
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
            "safe_training_length_claim": False,
            "compact_serializer_adoption": False,
            "scope": "full_lm_512_vs_640_allocated_length_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_compact_length_repro_v1_",
            "aggregate_json": (
                "reports/rightbrain_qwen3_compact_length_repro_v1_result.json"
            ),
            "aggregate_markdown": (
                "reports/rightbrain_qwen3_compact_length_repro_v1_result.md"
            ),
            "result_lock": (
                "configs/rightbrain_qwen3_compact_length_repro_v1_result_lock.json"
            ),
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_compact_length_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "tested_lengths": list(LENGTH_LEVELS),
        "repetitions_each": list(REPEATS),
        "batch_contracts": batch_contracts,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 512 / 640 token 梯度重現實驗",
                "",
                "- 唯一變因：allocated sequence length 為 512 或 640。",
                "- 兩組共享同一 64-token 有效前綴與 16 個 labels。",
                "- 每組 20 個獨立程序，各執行一次 backward。",
                "- 舊 compact serializer 曾降低 tokens 但品質退步，本輪不採用它。",
                "- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_compact_length_repro_execution_lock_v1",
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
            file_binding(BOUNDARY_RESULT),
            file_binding(COMPACT_RESULT),
            file_binding(batch_common.PARENT_PREREGISTRATION),
            file_binding(ROOT / batch_parent["exact_probe"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)[
                    "bindings"
                ]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "allocated_sequence_lengths": list(LENGTH_LEVELS),
            "fixed_shared_prefix_tokens": 64,
            "base_compute_dtype": "bfloat16",
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "full_language_model_path": True,
            "device": "gpu",
            "repetitions_each": list(REPEATS),
            "balanced_interleaved_execution_schedule": EXECUTION_SCHEDULE,
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
