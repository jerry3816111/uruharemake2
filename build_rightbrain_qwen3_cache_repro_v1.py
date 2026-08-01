#!/usr/bin/env python3
"""Freeze a default versus disabled Metal free-cache backward experiment."""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_dtype_repro_v1 as dtype_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_cache_repro_v1"
CACHE_MODES = ("default_cache", "disabled_cache")
REPEATS = tuple(range(1, 11))
ALLOCATED_LENGTH = 640
BASE_COMPUTE_DTYPE = "bfloat16"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_cache_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_cache_repro_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_cache_repro_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_cache_repro_v1_construction.md"
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_cache_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_cache_repro_v1.py"
PARENT_PREREGISTRATION = dtype_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_dtype_repro_v1_result.json"
BATCH_PARENT_PREREGISTRATION = dtype_common.PARENT_PREREGISTRATION

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batch(tokenizer, parent_preregistration):
    return dtype_common.canonical_batch(tokenizer, parent_preregistration)


def build():
    for path in (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        BATCH_PARENT_PREREGISTRATION,
        RUNNER_PATH,
        TEST_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    parent = load_json(PARENT_PREREGISTRATION)
    batch_parent = load_json(BATCH_PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    if parent_result["decision"]["outcome"] != "float16_does_not_eliminate_gradient_drift":
        raise RuntimeError("Unexpected dtype parent result")
    if parent_result["stability_by_dtype"][BASE_COMPUTE_DTYPE] is not False:
        raise RuntimeError("Parent did not reproduce bfloat16 drift")
    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = canonical_batch(tokenizer, batch_parent)
    batch_contract = {
        key: value
        for key, value in batch.items()
        if key not in ("input_ids", "labels")
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_cache_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "At the same 640-token bfloat16 full-Qwen3 graph, does disabling "
            "the Metal free-buffer cache eliminate cross-process gradient drift?"
        ),
        "causal_variable": {
            "name": "metal_free_cache_mode",
            "levels": list(CACHE_MODES),
            "default_cache": "retain_process_default_cache_limit",
            "disabled_cache": "set_cache_limit_zero_before_model_load",
            "only_intended_change": True,
        },
        "evidence_parent": {
            "path": str(PARENT_RESULT.relative_to(ROOT)),
            "sha256": sha256_file(PARENT_RESULT),
            "outcome": parent_result["decision"]["outcome"],
            "observed_bfloat16_stable": parent_result["stability_by_dtype"][
                BASE_COMPUTE_DTYPE
            ],
        },
        "upstream_evidence": {
            "mlx_version": "0.32.0",
            "set_cache_limit_docs": (
                "https://ml-explore.github.io/mlx/build/html/python/"
                "_autosummary/mlx.core.set_cache_limit.html"
            ),
            "metal_war_fix_pr": "https://github.com/ml-explore/mlx/pull/3630",
            "scope_note": (
                "MLX documents that a zero cache limit disables the free cache. "
                "The official WAR fix establishes that intermittent Metal gradient "
                "races are possible, but does not establish the present root cause."
            ),
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "batch_contract": batch_contract,
        "batch_source": {
            **source,
            "dataset": batch_parent["exact_probe"]["dataset"],
            "dataset_sha256": sha256_file(
                ROOT / batch_parent["exact_probe"]["dataset"]
            ),
            "synthetic_source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
            "suffix_labels": -100,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "base_compute_dtype": BASE_COMPUTE_DTYPE,
            "allocated_sequence_length": ALLOCATED_LENGTH,
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
            "cache_configuration_time": "before_model_load_and_any_large_allocation",
            "isolated_repetitions_per_level": list(REPEATS),
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": {
                "gradient_norm_coefficient_of_variation_maximum": 0.005,
                "gradient_norm_max_to_min_ratio_maximum": 1.02,
                "minimum_pairwise_group_profile_cosine": 0.9999,
                "gradient_hashes_must_be_identical": True,
            },
            "classifications": {
                "default_unstable_disabled_stable": (
                    "disabling_metal_free_cache_eliminates_observed_drift"
                ),
                "both_unstable": "disabling_metal_free_cache_does_not_eliminate_drift",
                "both_stable": "default_cache_parent_drift_not_reproduced",
                "default_stable_disabled_unstable": (
                    "disabling_metal_free_cache_introduces_instability"
                ),
                "execution_failure": "cache_repro_execution_failed",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "cache_disabled_training_authorization": False,
            "scope": "full_lm_metal_free_cache_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_cache_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_cache_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_cache_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_cache_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_cache_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "cache_modes": list(CACHE_MODES),
        "repetitions_each": list(REPEATS),
        "base_compute_dtype": BASE_COMPUTE_DTYPE,
        "allocated_sequence_length": ALLOCATED_LENGTH,
        "batch_contract": batch_contract,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 Metal free-cache 梯度重現實驗",
                "",
                "- 唯一變因：Metal free-buffer cache 保持預設或設為 0。",
                "- 兩組皆固定 BF16、640 tokens、36 層、全 LoRA、相同 loss。",
                "- 每種 cache mode 十個獨立程序，各執行一次 backward。",
                "- 不執行 optimizer、儲存、生成或人格訓練。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_cache_repro_execution_lock_v1",
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
            file_binding(BATCH_PARENT_PREREGISTRATION),
            file_binding(ROOT / batch_parent["exact_probe"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)["bindings"]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "cache_modes": list(CACHE_MODES),
            "base_compute_dtype": BASE_COMPUTE_DTYPE,
            "adapter_dtype": parent["adapter_initialization_contract"][
                "trainable_dtype"
            ],
            "allocated_sequence_length": ALLOCATED_LENGTH,
            "full_language_model_path": True,
            "device": "gpu",
            "repetitions_each": list(REPEATS),
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
