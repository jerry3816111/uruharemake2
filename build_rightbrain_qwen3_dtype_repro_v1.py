#!/usr/bin/env python3
"""Freeze a bfloat16 versus float16 full-Qwen3 backward experiment."""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_length_boundary_refine_v1 as refine_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_dtype_repro_v1"
DTYPE_LEVELS = ("bfloat16", "float16")
REPEATS = tuple(range(1, 11))
ALLOCATED_LENGTH = 640
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_dtype_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_dtype_repro_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_dtype_repro_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_dtype_repro_v1_construction.md"
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_dtype_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_dtype_repro_v1.py"
PARENT_PREREGISTRATION = full_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_length_boundary_refine_v1_result.json"

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batch(tokenizer, parent_preregistration):
    batches, source = refine_common.canonical_batches(tokenizer, parent_preregistration)
    return batches[str(ALLOCATED_LENGTH)], source


def build():
    for path in (PARENT_PREREGISTRATION, PARENT_RESULT, RUNNER_PATH, TEST_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    if parent_result["decision"]["outcome"] != "refined_length_boundary_anchor_not_reproduced":
        raise RuntimeError("Unexpected parent refinement result")
    if parent_result["stability_by_length"][str(ALLOCATED_LENGTH)] is not False:
        raise RuntimeError("Parent did not reproduce bfloat16 drift at 640 tokens")
    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batch, source = canonical_batch(tokenizer, parent)
    batch_contract = {
        key: value
        for key, value in batch.items()
        if key not in ("input_ids", "labels")
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_dtype_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "At the same 640-token full-Qwen3 graph, does casting the base model "
            "from bfloat16 to float16 eliminate cross-process gradient drift?"
        ),
        "causal_variable": {
            "name": "base_compute_dtype",
            "levels": list(DTYPE_LEVELS),
            "only_intended_change": True,
        },
        "evidence_parent": {
            "path": str(PARENT_RESULT.relative_to(ROOT)),
            "sha256": sha256_file(PARENT_RESULT),
            "outcome": parent_result["decision"]["outcome"],
            "observed_bfloat16_640_stable": parent_result["stability_by_length"]["640"],
        },
        "upstream_evidence": {
            "mlx_version": "0.32.0",
            "mlx_release_url": "https://github.com/ml-explore/mlx/releases/tag/v0.32.0",
            "module_set_dtype_docs": (
                "https://ml-explore.github.io/mlx/build/html/python/nn/"
                "_autosummary/mlx.nn.Module.set_dtype.html"
            ),
            "metal_war_fix_pr": "https://github.com/ml-explore/mlx/pull/3630",
            "war_fix_scope_note": (
                "The official issue proves scheduler-dependent intermittent Metal "
                "gradient races are possible, but its direct failing primitive was "
                "LayerNorm bias; this experiment does not assume the same root cause."
            ),
        },
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "batch_contract": batch_contract,
        "batch_source": {
            **source,
            "dataset": parent["exact_probe"]["dataset"],
            "dataset_sha256": sha256_file(ROOT / parent["exact_probe"]["dataset"]),
            "synthetic_source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
            "suffix_labels": -100,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "allocated_sequence_length": ALLOCATED_LENGTH,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "adapter_dtype": parent["adapter_initialization_contract"]["trainable_dtype"],
            "full_language_model_path": [
                "token_embedding",
                "36_transformer_layers",
                "final_rms_norm",
                "tied_lm_head",
                "masked_cross_entropy",
            ],
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
                "bfloat16_unstable_float16_stable": "float16_eliminates_observed_bfloat16_gradient_drift",
                "both_unstable": "float16_does_not_eliminate_gradient_drift",
                "both_stable": "bfloat16_parent_drift_not_reproduced_in_dtype_control",
                "bfloat16_stable_float16_unstable": "float16_introduces_gradient_instability",
                "execution_failure": "dtype_repro_execution_failed",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "float16_training_authorization": False,
            "scope": "full_lm_base_compute_dtype_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_dtype_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_dtype_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_dtype_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_dtype_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_dtype_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "dtype_levels": list(DTYPE_LEVELS),
        "repetitions_each": list(REPEATS),
        "allocated_sequence_length": ALLOCATED_LENGTH,
        "batch_contract": batch_contract,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 bfloat16 / float16 梯度重現實驗",
                "",
                "- 唯一變因：base model compute dtype。",
                "- 兩組皆固定 640 tokens、36 層、全 LoRA、相同 labels 與 loss。",
                "- 每種 dtype 十個獨立程序，各執行一次 backward。",
                "- LoRA trainable parameters 維持 float32。",
                "- 不執行 optimizer、儲存、生成或人格訓練。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_dtype_repro_execution_lock_v1",
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
            file_binding(ROOT / parent["exact_probe"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)["bindings"]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "base_compute_dtypes": list(DTYPE_LEVELS),
            "adapter_dtype": parent["adapter_initialization_contract"]["trainable_dtype"],
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
